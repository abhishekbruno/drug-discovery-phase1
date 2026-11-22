from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import re
import traceback
from docking_pipeline.config import ExperimentConfig
from docking_pipeline.ligand.loader import LigandRecord
from docking_pipeline.ligand.preparation import prepare_ligand
from docking_pipeline.docking.vina_engine import dock
from docking_pipeline.utils.logging import write_json, now, sha256


def artifact_hashes(directory: Path) -> dict:
    # These two compound-root files are mutable current-state bookkeeping.
    # Status-named files inside attempt directories remain part of the evidence.
    mutable_status = {directory/'status.json', directory/'status.json.tmp'}
    return {str(p.relative_to(directory)): sha256(p) for p in sorted(directory.rglob('*')) if p.is_file() and p not in mutable_status}


def verify_artifacts(directory: Path, hashes: dict) -> None:
    if not hashes or artifact_hashes(directory) != hashes:
        raise ValueError(f'Artifact integrity failure (inventory/hash mismatch): {directory}')
    for name, expected in hashes.items():
        if Path(name).is_absolute() or '..' in Path(name).parts: raise ValueError('Artifact integrity failure: unsafe path')
        path = directory/name
        if not path.is_file() or sha256(path) != expected: raise ValueError(f'Artifact integrity failure: {path}')


def verify_attempt_history(directory: Path, hashes: dict) -> None:
    """Verify sealed older attempts while permitting new interrupted attempts."""
    if not hashes:
        raise ValueError('Retry history integrity failure: empty inventory')
    attempts = {}
    for name, expected in hashes.items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or len(path.parts) < 2 or not re.fullmatch(r'attempt-\d+', path.parts[0]):
            raise ValueError('Retry history integrity failure: unsafe artifact path')
        attempts.setdefault(path.parts[0], {})[str(Path(*path.parts[1:]))] = expected
    for attempt, expected in attempts.items():
        # All files inside a sealed attempt, including newly added files, matter.
        actual = {str(p.relative_to(directory/attempt)): sha256(p)
                  for p in sorted((directory/attempt).rglob('*')) if p.is_file()}
        if actual != expected:
            raise ValueError(f'Retry history artifact integrity failure: {directory/attempt}')


def run_batch(records: list[LigandRecord], receptor: Path, grid: dict, config: ExperimentConfig,
              root: Path, progress=None, retry_failed: bool = False, retry_started=None) -> list[dict]:
    def execute(record):
        directory = root/record.compound_id
        directory.mkdir(parents=True, exist_ok=True)
        status_path = directory/'status.json'
        previous = json.loads(status_path.read_text()) if status_path.exists() else None
        if previous and previous['status'] in ('success','failed'):
            verify_artifacts(directory, previous['artifact_hashes'])
            if previous['compound_id'] != record.compound_id:
                raise ValueError('Cached compound identity integrity failure')
            attempt_path=directory/previous['attempt']
            completion=attempt_path/'completion.json'
            if completion.exists():
                expected=json.loads(completion.read_text())
                if {k:v for k,v in previous.items() if k!='artifact_hashes'} != expected:
                    raise ValueError('Cached status metadata integrity failure')
            elif previous['status']=='success':
                # Verify pre-completion-manifest results against their hashed scientific artifacts.
                from docking_pipeline.analysis.scoring import parse_poses
                actual=json.loads((attempt_path/'docking/result.json').read_text())
                prepared=json.loads((attempt_path/'prepared/manifest.json').read_text())
                poses=parse_poses((attempt_path/'docking/poses.pdbqt').read_text())
                if (previous['docking']!=actual or previous['preparation']!=prepared or actual['poses']!=poses
                        or previous['best_score_kcal_mol']!=min(p['score_kcal_mol'] for p in poses)):
                    raise ValueError('Cached scientific metadata integrity failure')
            else:
                raise ValueError('Failed legacy result lacks a completion manifest; inspect it and use a new experiment')
            if previous['status']=='success' or not retry_failed: return previous
            # Persist the old immutable evidence before replacing its current status.
            if retry_started:
                retry_started(record.compound_id, previous['artifact_hashes'])
        numbers = [int(p.name.split('-')[1]) for p in directory.glob('attempt-*') if p.is_dir()]
        attempt = directory/f'attempt-{max(numbers,default=0)+1:03d}'; attempt.mkdir()
        result = {'compound_id':record.compound_id, 'docking_run_id':f'{config.experiment_id}/{record.compound_id}/{attempt.name}',
                  'status':'running', 'started_at':now(), 'scoring_function':'vina', 'attempt':attempt.name}
        write_json(status_path,result)
        try:
            prepared = prepare_ligand(record, attempt/'prepared',config.ligand_seed, config.preserve_sdf_coordinates)
            calculation = dock(receptor,Path(prepared['pdbqt']),grid,config.docking,attempt/'docking')
            result.update(status='success', preparation=prepared, docking=calculation,
                          best_score_kcal_mol=min(p['score_kcal_mol'] for p in calculation['poses']))
        except Exception as exc:
            (attempt/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
            result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        result['finished_at'] = now()
        write_json(attempt/'completion.json',result)
        result['artifact_hashes'] = artifact_hashes(directory)
        write_json(status_path,result)
        return result
    results = {}
    if config.docking.workers==1:
        for row in records:
            result=execute(row); results[row.compound_id]=result
            if progress: progress(len(results),len(records),row.compound_id,result['status'])
    else:
        with ThreadPoolExecutor(max_workers=config.docking.workers) as pool:
            futures={pool.submit(execute,r):r for r in records}
            for future in as_completed(futures):
                row=futures[future]; result=future.result(); results[row.compound_id]=result
                if progress: progress(len(results),len(records),row.compound_id,result['status'])
    return [results[r.compound_id] for r in records]
