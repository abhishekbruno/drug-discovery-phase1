from pathlib import Path
import json
import shutil
from threading import Lock
from docking_pipeline.config import ExperimentConfig
from docking_pipeline.utils.dependencies import check_environment
from docking_pipeline.utils.logging import write_json, sha256, digest, now
from docking_pipeline.utils.locking import experiment_lock
from docking_pipeline.protein.preparation import prepare_receptor
from docking_pipeline.ligand.loader import load_ligands
from docking_pipeline.docking.grid import make_grid
from docking_pipeline.docking.batch_runner import run_batch, artifact_hashes, verify_artifacts, verify_attempt_history
from docking_pipeline.analysis.ranking import rank_candidates
from docking_pipeline.reporting.report_generator import generate_report


def run_experiment(config: ExperimentConfig, resume: bool = False, progress=None, retry_failed: bool = False) -> dict:
    environment = check_environment(config.docking.executable)
    if not environment['ready']: raise RuntimeError('Environment not ready: '+ '; '.join(environment['errors']))
    records = load_ligands(config.ligands)
    configuration = config.model_dump(mode='json')
    identity = digest({'config':configuration,'protein':sha256(config.protein.input),'ligands':sha256(config.ligands),
                       'packages':environment['packages'],'vina':environment['vina']['sha256'],'python':environment['python'], 'pipeline':'0.1.0'})
    root = config.output_dir.resolve()/config.experiment_id
    if root.exists() and not resume: raise FileExistsError(f'Experiment exists: {root}; use --resume or a new experiment_id')
    root.mkdir(parents=True,exist_ok=True)
    with experiment_lock(root/'.lock'):
        state_path=root/'experiment.json'
        if state_path.exists():
            state=json.loads(state_path.read_text())
            if state['identity'] != identity: raise ValueError('Experiment identity mismatch: configuration, inputs or software changed')
            verify_artifacts(root/'inputs',state['input_hashes'])
            for compound, checkpoint in state.get('retry_checkpoints', {}).items():
                verify_attempt_history(root/'ligands'/compound, checkpoint['artifact_hashes'])
            for compound,expected in state.get('ligand_status_hashes',{}).items():
                status_file=root/'ligands'/compound/'status.json'
                if not status_file.exists() or sha256(status_file)!=expected:
                    raise ValueError(f'Cached ligand status integrity failure: {compound}')
        else:
            inputs=root/'inputs'; inputs.mkdir(exist_ok=False)
            shutil.copy2(config.protein.input,inputs/('protein'+config.protein.input.suffix))
            shutil.copy2(config.ligands,inputs/('ligands'+config.ligands.suffix))
            state={'identity':identity,'started_at':now(),'input_hashes':artifact_hashes(inputs),'configuration':configuration}
            write_json(state_path,state)
            write_json(root/'config.resolved.json',configuration)
            write_json(root/'environment.json',environment)
        state.update(status='running', stage='preparing_receptor', updated_at=now(),
                     progress={'total': len(records), 'completed': 0, 'succeeded': 0, 'failed': 0})
        state.pop('error', None)
        write_json(state_path, state)
        state_guard = Lock()
        try:
            if state.get('receptor'):
                receptor_dir=root/state['receptor']
                verify_artifacts(receptor_dir,state['receptor_hashes'])
                receptor=json.loads((receptor_dir/'manifest.json').read_text())
            else:
                attempts=list(root.glob('receptor-*'))
                receptor_dir=root/f'receptor-{len(attempts)+1:03d}'
                receptor=prepare_receptor(config.protein,receptor_dir)
                state.update(receptor=receptor_dir.name,receptor_hashes=artifact_hashes(receptor_dir))
                write_json(state_path,state)
            grid=make_grid(config.grid,receptor['reference_coordinates'])
            write_json(root/'grid.json',grid)
            state.update(stage='docking', updated_at=now())
            write_json(state_path, state)
            def record_retry_started(compound, hashes):
                with state_guard:
                    state.setdefault('retry_checkpoints', {})[compound] = {'artifact_hashes': hashes}
                    state.setdefault('ligand_status_hashes', {}).pop(compound, None)
                    write_json(state_path, state)
            def record_progress(done,total,compound,status):
                with state_guard:
                    state.setdefault('ligand_status_hashes',{})[compound]=sha256(root/'ligands'/compound/'status.json')
                    state.get('retry_checkpoints', {}).pop(compound, None)
                    state['progress']['completed'] = done
                    state['progress']['succeeded' if status == 'success' else 'failed'] += 1
                    state['updated_at'] = now()
                    write_json(state_path,state)
                if progress: progress(done,total,compound,status)
            results=run_batch(records,Path(receptor['pdbqt']),grid,config,root/'ligands',record_progress,retry_failed,record_retry_started)
            successful=sum(r['status']=='success' for r in results)
            status='completed' if successful==len(results) else ('completed_with_failures' if successful else 'failed')
            report={'experiment_id':config.experiment_id,'status':status,'started_at':state['started_at'],'updated_at':now(),
                    'environment':environment,'configuration':configuration,'identity':identity,'receptor':receptor,
                    'grid':grid,'ligands':results,'ranking':rank_candidates(results)}
            validation=root/'validation.json'
            if validation.exists():
                if sha256(validation)!=state.get('validation_sha256'):
                    raise ValueError('Crystallographic validation integrity failure')
                report['validation']=json.loads(validation.read_text())
            state.update(stage='reporting', updated_at=now()); write_json(state_path, state)
            generate_report(report,root)
            state.update(status=status,stage='finished',updated_at=now()); write_json(state_path,state)
            return report
        except KeyboardInterrupt:
            state.update(status='interrupted', error='Execution interrupted; resume to continue in a new attempt', updated_at=now())
            write_json(state_path, state)
            raise
        except Exception as exc:
            state.update(status='failed',error=f'{type(exc).__name__}: {exc}',updated_at=now()); write_json(state_path,state)
            raise
