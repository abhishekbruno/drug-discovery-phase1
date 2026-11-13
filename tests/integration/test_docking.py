from pathlib import Path
import os
import pytest
from docking_pipeline.config import DockingConfig
from docking_pipeline.docking.vina_engine import dock
from docking_pipeline.ligand.loader import load_ligands
from docking_pipeline.ligand.preparation import prepare_ligand
from docking_pipeline.config import ProteinConfig
from docking_pipeline.protein.preparation import prepare_receptor


@pytest.mark.integration
def test_actual_vina_poses_and_repeatability(tmp_path):
    exe = os.environ.get('VINA_EXECUTABLE', 'vina')
    receptor = prepare_receptor(ProteinConfig(input=Path('data/benchmarks/1iep/tutorial_receptorH.pdb'), chains=['A']), tmp_path/'rec')
    p = tmp_path/'lig.smi'; p.write_text('CCO ethanol\n')
    ligand = prepare_ligand(load_ligands(p)[0], tmp_path/'lig')
    config = DockingConfig(executable=exe, cpu=1, exhaustiveness=1, num_modes=3)
    grid = {'center':[15.190,53.903,16.917], 'size':[20,20,20]}
    a = dock(Path(receptor['pdbqt']), Path(ligand['pdbqt']), grid, config, tmp_path/'dock1')
    b = dock(Path(receptor['pdbqt']), Path(ligand['pdbqt']), grid, config, tmp_path/'dock2')
    assert a['poses'] == b['poses']
    assert len(a['poses']) >= 1
    assert Path(a['sdf']).stat().st_size > 100
    assert Path(a['pdbqt']).read_bytes() == Path(b['pdbqt']).read_bytes()
    with pytest.raises(FileExistsError): dock(Path(receptor['pdbqt']),Path(ligand['pdbqt']),grid,config,tmp_path/'dock1')
