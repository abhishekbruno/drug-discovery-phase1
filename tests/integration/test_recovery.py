"""Interrupt real batch retries; preserve sealed historical calculations."""
import json
import os
from pathlib import Path

import pytest

from docking_pipeline.config import ExperimentConfig, ProteinConfig, GridConfig, DockingConfig
from docking_pipeline.orchestrator import run_experiment
from docking_pipeline.docking import batch_runner


def configuration(tmp_path, workers=1):
    library = tmp_path / 'library.csv'
    library.write_text('compound_id,smiles\ninvalid,broken\nethanol,CCO\n' +
                       ('invalidtwo,broken\n' if workers == 2 else ''))
    return ExperimentConfig(
        experiment_id='recovery',
        protein=ProteinConfig(input=Path('data/benchmarks/1iep/tutorial_receptorH.pdb').resolve(), chains=['A']),
        ligands=library, output_dir=tmp_path,
        grid=GridConfig(mode='manual', center=(15.190, 53.903, 16.917), size=(20, 20, 20)),
        docking=DockingConfig(executable=os.environ.get('VINA_EXECUTABLE', 'vina'),
                             cpu=1, workers=workers, exhaustiveness=1, num_modes=2),
    )


def interrupt_retry(config, monkeypatch):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt('simulated process interruption before preparation')
    with monkeypatch.context() as patch:
        patch.setattr(batch_runner, 'prepare_ligand', interrupted)
        with pytest.raises(KeyboardInterrupt):
            run_experiment(config, resume=True, retry_failed=True)


@pytest.mark.integration
@pytest.mark.parametrize('workers', [1, 2])
def test_retry_resumes_after_interruption_without_losing_history(tmp_path, monkeypatch, workers):
    config = configuration(tmp_path, workers)
    original = run_experiment(config)
    assert original['ligands'][0]['status'] == 'failed'
    root = tmp_path / 'recovery'
    previous = root / 'ligands/invalid/attempt-001/completion.json'
    original_bytes = previous.read_bytes()
    pose = root / 'ligands/ethanol/attempt-001/docking/poses.pdbqt'
    pose_modified = pose.stat().st_mtime_ns
    interrupt_retry(config, monkeypatch)
    interrupted = json.loads((root / 'experiment.json').read_text())
    assert interrupted['status'] == 'interrupted'
    # A retry is incomplete, so resume must create a fresh attempt instead of
    # comparing its running status to the old failed result's checksum.
    resumed = run_experiment(config, resume=True, retry_failed=True)
    assert resumed['ligands'][0]['attempt'] == 'attempt-003'
    assert previous.read_bytes() == original_bytes
    state = json.loads((root / 'experiment.json').read_text())
    assert state['status'] == 'completed_with_failures'  # malformed chemistry stays isolated
    assert pose.stat().st_mtime_ns == pose_modified
    assert len(list(pose.parents[2].glob('attempt-*'))) == 1
    if workers == 2:
        assert resumed['ligands'][2]['attempt'] == 'attempt-003'
    assert not state.get('retry_checkpoints')
    assert 'error' not in state  # no stale fatal/interruption error


@pytest.mark.integration
@pytest.mark.parametrize('tamper', ['modify', 'add'])
def test_interrupted_retry_still_rejects_historical_artifact_tampering(tmp_path, monkeypatch, tamper):
    config = configuration(tmp_path)
    run_experiment(config)
    interrupt_retry(config, monkeypatch)
    attempt = tmp_path / 'recovery/ligands/invalid/attempt-001'
    if tamper == 'modify':
        (attempt / 'error.log').write_text('changed historical evidence')
    else:
        (attempt / 'unrecorded.txt').write_text('unexpected historical artifact')
    with pytest.raises(ValueError, match='integrity'):
        run_experiment(config, resume=True, retry_failed=True)


@pytest.mark.integration
@pytest.mark.parametrize('boundary', ['before_running_status', 'during_running_replace', 'after_terminal_status'])
def test_retry_checkpoint_survives_status_write_boundaries(tmp_path, monkeypatch, boundary):
    config = configuration(tmp_path)
    run_experiment(config)
    original_write = batch_runner.write_json
    original_replace = os.replace

    def interrupted_replace(source, destination):
        if (boundary == 'during_running_replace' and destination.name == 'status.json'
                and destination.parent.name == 'invalid'
                and json.loads(source.read_text())['status'] == 'running'):
            raise KeyboardInterrupt('interrupted after writing atomic temporary status')
        original_replace(source, destination)

    def interrupted_write(path, value):
        is_current = path.name == 'status.json' and path.parent.name == 'invalid'
        if is_current and value['status'] == 'running' and boundary == 'before_running_status':
            raise KeyboardInterrupt('interrupted before replacing current status')
        original_write(path, value)
        if is_current and value['status'] == 'failed' and boundary == 'after_terminal_status':
            raise KeyboardInterrupt('interrupted before notifying coordinator')

    with monkeypatch.context() as patch:
        patch.setattr(batch_runner, 'write_json', interrupted_write)
        patch.setattr(os, 'replace', interrupted_replace)
        with pytest.raises(KeyboardInterrupt):
            run_experiment(config, resume=True, retry_failed=True)
    retry = boundary != 'after_terminal_status'
    resumed = run_experiment(config, resume=True, retry_failed=retry)
    expected_attempt = 'attempt-003' if retry else 'attempt-002'
    assert resumed['ligands'][0]['attempt'] == expected_attempt
    state = json.loads((tmp_path / 'recovery/experiment.json').read_text())
    assert not state.get('retry_checkpoints')
    assert 'error' not in state
    assert not (tmp_path / 'recovery/ligands/invalid/status.json.tmp').exists()
