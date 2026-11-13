from pathlib import Path
from streamlit.testing.v1 import AppTest


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
