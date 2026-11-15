from pathlib import Path
from streamlit.testing.v1 import AppTest
import json
import pytest


def test_ui_empty_state_and_new_experiment_controls(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKPIPE_RESULTS',str(tmp_path))
    app=AppTest.from_file(str(Path('src/docking_pipeline/ui.py').resolve()),default_timeout=30).run()
    assert not app.exception
    assert any('No experiments' in x.value for x in app.info)
    app.sidebar.radio[0].set_value('New experiment').run()
    assert not app.exception
    assert any(x.label=='Start docking' for x in app.button)
    assert any(x.label=='Grid method' for x in app.radio)


def test_ui_missing_input_is_actionable(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKPIPE_RESULTS',str(tmp_path))
    app=AppTest.from_file(str(Path('src/docking_pipeline/ui.py').resolve()),default_timeout=30).run()
    app.sidebar.radio[0].set_value('New experiment').run()
    next(x for x in app.checkbox if x.label=='Use bundled 1IEP example').uncheck().run()
    assert not app.exception
    assert any('Upload' in x.value for x in app.info)


def test_first_interrupted_job_has_resume_control(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKPIPE_RESULTS',str(tmp_path))
    job=tmp_path/'interrupted'; job.mkdir(); (job/'config.resolved.json').write_text('{}')
    app=AppTest.from_file(str(Path('src/docking_pipeline/ui.py').resolve()),default_timeout=30).run()
    assert not app.exception
    assert any(x.label=='Resume saved experiment' for x in app.button)


def test_workspace_shows_incomplete_job_error_and_progress(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKPIPE_RESULTS',str(tmp_path))
    job=tmp_path/'interrupted'; job.mkdir()
    (job/'config.resolved.json').write_text('{}')
    (job/'experiment.json').write_text(json.dumps({'status':'interrupted','stage':'docking',
        'error':'Execution interrupted; resume to continue',
        'progress':{'total':3,'completed':1,'succeeded':1,'failed':0}}))
    app=AppTest.from_file(str(Path('src/docking_pipeline/ui.py').resolve()),default_timeout=30).run()
    assert not app.exception
    assert any('Execution interrupted' in x.value for x in app.warning)
    assert any(x.label=='Compounds processed' and x.value=='1 / 3' for x in app.metric)
    assert next(x for x in app.selectbox if x.label=='Experiment').value=='interrupted'


@pytest.mark.parametrize('report_text', ['{invalid report', '{"ranking":[],"ligands":[],"validation":null}'])
def test_workspace_filters_and_bad_report_do_not_crash(tmp_path,monkeypatch,report_text):
    monkeypatch.setenv('DOCKPIPE_RESULTS',str(tmp_path))
    for name,status in [('finished','completed'),('needs-repair','failed')]:
        root=tmp_path/name; root.mkdir()
        (root/'experiment.json').write_text(json.dumps({'status':status}))
        (root/'report.json').write_text(report_text)
    app=AppTest.from_file(str(Path('src/docking_pipeline/ui.py').resolve()),default_timeout=30).run()
    assert not app.exception
    next(x for x in app.selectbox if x.label=='Status filter').set_value('Needs attention').run()
    assert next(x for x in app.selectbox if x.label=='Experiment').options==['needs-repair']
    assert any('report' in x.value.lower() for x in app.error)
