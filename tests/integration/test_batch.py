import json
import os
from pathlib import Path
import pytest
from docking_pipeline.config import ExperimentConfig, ProteinConfig, GridConfig, DockingConfig
from docking_pipeline.orchestrator import run_experiment


@pytest.mark.integration
@pytest.mark.parametrize('workers',[1,2])
def test_batch_failure_isolation_resume_and_tamper(tmp_path,workers):
    library = tmp_path/'library.csv'
    library.write_text('compound_id,smiles\nethanol,CCO\ninvalid,broken\nacetate,CC(=O)O\n')
    config = ExperimentConfig(experiment_id='batch', protein=ProteinConfig(input=Path('data/benchmarks/1iep/tutorial_receptorH.pdb').resolve(), chains=['A']),
        ligands=library, output_dir=tmp_path, grid=GridConfig(mode='manual',center=(15.190,53.903,16.917),size=(20,20,20)),
        docking=DockingConfig(executable=os.environ.get('VINA_EXECUTABLE','vina'),cpu=1,workers=workers,exhaustiveness=1,num_modes=2))
    snapshots = []
    def capture_progress(done, total, compound, status):
        state = json.loads((tmp_path/'batch'/'experiment.json').read_text())
        snapshots.append(state['progress'])
        assert state['stage'] == 'docking'
        assert state['progress']['completed'] == done
    result = run_experiment(config, progress=capture_progress)
    assert snapshots[-1] == {'total': 3, 'completed': 3, 'succeeded': 2, 'failed': 1}
    state = json.loads((tmp_path/'batch'/'experiment.json').read_text())
    assert state['stage'] == 'finished'
    assert result['status'] == 'completed_with_failures'
    assert len(result['ranking']) == 2
    assert result['ligands'][1]['status'] == 'failed'
    assert (tmp_path/'batch'/'report.md').is_file()
    old = (tmp_path/'batch'/'ligands'/'ethanol'/'attempt-001'/'docking'/'poses.pdbqt').stat().st_mtime_ns
    resumed = run_experiment(config, resume=True)
    assert len(resumed['ranking']) == 2
    assert json.loads((tmp_path/'batch'/'experiment.json').read_text())['progress'] == snapshots[-1]
    assert old == (tmp_path/'batch'/'ligands'/'ethanol'/'attempt-001'/'docking'/'poses.pdbqt').stat().st_mtime_ns
    status_path=tmp_path/'batch'/'ligands'/'ethanol'/'status.json'
    original_status=status_path.read_text()
    for changes in [{'best_score_kcal_mol':-999.0},{'artifact_hashes':{}}]:
        status=json.loads(original_status); status.update(changes)
        status_path.write_text(json.dumps(status))
        with pytest.raises(ValueError,match='integrity'): run_experiment(config,resume=True)
        status_path.write_text(original_status)
    validation=tmp_path/'batch'/'validation.json'
    validation.write_text('{"status":"passed"}')
    with pytest.raises(ValueError,match='integrity'): run_experiment(config,resume=True)
    validation.unlink()
    with pytest.raises(FileExistsError): run_experiment(config)
    config.docking.seed += 1
    with pytest.raises(ValueError, match='identity'): run_experiment(config,resume=True)
    config.docking.seed -= 1
    pose = tmp_path/'batch'/'ligands'/'ethanol'/'attempt-001'/'docking'/'poses.pdbqt'
    pose.write_text('tampered')
    with pytest.raises(ValueError, match='integrity'): run_experiment(config,resume=True)
