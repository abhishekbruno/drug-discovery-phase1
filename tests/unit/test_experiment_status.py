import json
from docking_pipeline.experiment_status import read_experiment, list_experiments


def test_incomplete_experiment_summary_uses_saved_progress(tmp_path):
    root = tmp_path / 'interrupted'; root.mkdir()
    (root / 'config.resolved.json').write_text('{}')
    (root / 'experiment.json').write_text(json.dumps({
        'status': 'interrupted', 'stage': 'docking', 'error': 'Interrupted; resume to continue',
        'progress': {'total': 3, 'completed': 1, 'succeeded': 1, 'failed': 0},
    }))
    row = read_experiment(root)
    assert row['status'] == 'interrupted' and not row['has_report']
    assert row['can_resume'] and row['progress']['completed'] == 1
    assert row['error'].startswith('Interrupted')


def test_corrupt_metadata_is_isolated_and_not_resumable(tmp_path):
    bad = tmp_path / 'bad'; bad.mkdir()
    (bad / 'experiment.json').write_text('{bad')
    (bad / 'config.resolved.json').write_text('{}')
    good = tmp_path / 'good'; good.mkdir()
    (good / 'config.resolved.json').write_text('{}')
    internal = tmp_path / '_uploads'; internal.mkdir()
    rows = {row['id']: row for row in list_experiments(tmp_path)}
    assert set(rows) == {'bad', 'good'}
    assert rows['bad']['status'] == 'unreadable' and not rows['bad']['can_resume']
    assert rows['bad']['warning']
    assert rows['good']['status'] == 'not_started' and rows['good']['can_resume']


def test_legacy_report_and_invalid_progress_do_not_invent_counts(tmp_path):
    (tmp_path / 'report.json').write_text(json.dumps({'status': 'completed', 'started_at': '2026-11-13'}))
    assert read_experiment(tmp_path)['status'] == 'completed'
    (tmp_path / 'experiment.json').write_text(json.dumps({'status': 'running', 'progress': {
        'total': 1, 'completed': 9, 'succeeded': 9, 'failed': 0}}))
    row = read_experiment(tmp_path)
    assert row['status'] == 'running'  # recorded state, not a claim of process liveness
    assert row['progress'] is None and row['warning']


def test_cli_status_reads_saved_job_without_running_tools(tmp_path, capsys):
    from docking_pipeline.cli import main
    (tmp_path/'experiment.json').write_text('{"status":"interrupted","stage":"docking"}')
    assert main(['status', '--job', str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'interrupted'
    assert main(['status', '--job', str(tmp_path/'missing')]) == 1
    assert 'not found' in capsys.readouterr().err
