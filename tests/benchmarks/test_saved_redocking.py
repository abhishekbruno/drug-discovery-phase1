"""Validate actual CLI benchmark artifacts; set DOCKPIPE_BENCHMARK_JOB to include."""
import json
import os
from pathlib import Path
import pytest
from docking_pipeline.benchmark import validate_redocking


@pytest.mark.benchmark
def test_actual_saved_redocking_rmsd_and_outcome():
    job=os.environ.get('DOCKPIPE_BENCHMARK_JOB')
    if not job: pytest.skip('Run dockpipe benchmark, then set DOCKPIPE_BENCHMARK_JOB to its result directory')
    root=Path(job); report=json.loads((root/'report.json').read_text())
    measured=validate_redocking(report,Path(report['configuration']['ligands']))
    assert measured['top_scoring_pose']['heavy_atom_rmsd_angstrom']==pytest.approx(report['validation']['top_scoring_pose']['heavy_atom_rmsd_angstrom'],abs=1e-10)
    assert measured['status']==('passed' if measured['top_scoring_pose']['heavy_atom_rmsd_angstrom']<=2 else 'failed')
    assert measured['top_scoring_pose']['score_kcal_mol']==report['ranking'][0]['best_score_kcal_mol']
