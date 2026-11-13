import numpy as np
import pytest
from rdkit import Chem
from rdkit.Chem import AllChem
from docking_pipeline.config import GridConfig, DockingConfig, ExperimentConfig
from docking_pipeline.docking.grid import make_grid
from docking_pipeline.analysis.scoring import parse_poses
from docking_pipeline.analysis.rmsd import symmetry_rmsd
from docking_pipeline.ligand.loader import load_ligands
from docking_pipeline.ligand.preparation import prepare_ligand
from docking_pipeline.protein.loader import load_structure
from docking_pipeline.protein.validator import inspect_structure


@pytest.mark.parametrize('size', [(0,20,20), (-1,20,20), (float('nan'),20,20), (60,60,60)])
def test_invalid_grid_rejected(size):
    with pytest.raises(ValueError):
        GridConfig(mode='manual', center=(0,0,0), size=size)


def test_manual_grid_needs_center():
    with pytest.raises(ValueError):
        GridConfig(mode='manual')


def test_reference_grid_encloses_and_pads():
    grid = make_grid(GridConfig(mode='reference', padding=4), np.array([[1,2,3],[5,8,11]]))
    assert grid['center'] == [3,5,7]
    assert grid['size'] == [12,14,16]


def test_explicit_reference_box_cannot_crop():
    with pytest.raises(ValueError, match='enclos'):
        make_grid(GridConfig(mode='reference', size=(10,10,10)), np.array([[0,0,0],[15,0,0]]))


def test_cpu_limit_and_seed():
    with pytest.raises(ValueError):
        DockingConfig(cpu=0)
    with pytest.raises(ValueError):
        DockingConfig(seed=0)


@pytest.mark.parametrize('content',[
    'compound_id,smiles\nethanol,CCO\nEthanol,CCN\n',
    'compound_id,smiles\nNUL,CCO\n',
    'compound_id,smiles\nCOM1.sdf,CCO\n',
    'compound_id,smiles\nending.,CCO\n'])
def test_windows_colliding_or_reserved_ids_rejected(tmp_path,content):
    p=tmp_path/'library.csv'; p.write_text(content)
    with pytest.raises(ValueError): load_ligands(p)


def test_vina_pose_parsing_and_malformed_failure():
    text = 'MODEL 1\nREMARK VINA RESULT: -7.2 0.0 0.0\nENDMDL\nMODEL 2\nREMARK VINA RESULT: -6.9 1.2 2.3\nENDMDL\n'
    poses = parse_poses(text)
    assert poses[0]['score_kcal_mol'] == -7.2
    assert poses[1]['vina_rmsd_upper_angstrom'] == 2.3
    for bad in ['', 'REMARK VINA RESULT: NaN 0 0', 'MODEL 1\nREMARK VINA RESULT: broken\nENDMDL']:
        with pytest.raises(ValueError):
            parse_poses(bad)


def test_csv_preserves_failure_rows(tmp_path):
    p = tmp_path/'library.csv'
    p.write_text('compound_id,smiles\ngood,CCO\nbad,not_smiles\n', encoding='utf-8')
    rows = load_ligands(p)
    assert len(rows) == 2
    assert rows[0].compound_id == 'good'
    assert rows[1].error


def test_duplicate_and_path_ids_rejected(tmp_path):
    for content in ['compound_id,smiles\na,CC\na,CO\n', 'compound_id,smiles\n../escape,CC\n']:
        p = tmp_path/'bad.csv'; p.write_text(content)
        with pytest.raises(ValueError):
            load_ligands(p)


def test_real_ligand_preparation(tmp_path):
    p = tmp_path/'library.smi'; p.write_text('C[C@H](O)C(=O)O lactic\n')
    row = load_ligands(p)[0]
    result = prepare_ligand(row, tmp_path/'prepared', seed=17)
    mol = Chem.SDMolSupplier(result['sdf'], removeHs=False)[0]
    assert mol.GetConformer().Is3D()
    assert np.isfinite(mol.GetConformer().GetPositions()).all()
    assert '@' in Chem.MolToSmiles(Chem.RemoveHs(mol))
    assert result['descriptors']['molecular_weight'] == pytest.approx(90.078, abs=.02)
    assert 'ROOT' in __import__('pathlib').Path(result['pdbqt']).read_text()


def test_invalid_pdb_and_missing_chain(tmp_path):
    p = tmp_path/'bad.pdb'; p.write_text('this is not a structure\n')
    with pytest.raises(ValueError): load_structure(p)


def test_protein_inventory():
    from pathlib import Path
    structure = load_structure(Path('data/benchmarks/1iep/1iep.pdb'))
    info = inspect_structure(structure)
    assert 'A' in info['chains']
    assert any(r['name'] == 'STI' for r in info['heterogens'])
    assert info['atom_count'] > 1000


def test_rmsd_does_not_align_away_translation():
    mol = Chem.AddHs(Chem.MolFromSmiles('CCO'))
    AllChem.EmbedMolecule(mol, randomSeed=9)
    moved = Chem.Mol(mol)
    conf = moved.GetConformer()
    for i, p in enumerate(conf.GetPositions()): conf.SetAtomPosition(i, p + np.array([3.,0.,0.]))
    assert symmetry_rmsd(mol, moved) == pytest.approx(3., abs=1e-5)
    assert symmetry_rmsd(mol, mol) == pytest.approx(0.)


def test_rmsd_rejects_different_graph():
    a = Chem.AddHs(Chem.MolFromSmiles('CCO')); b = Chem.AddHs(Chem.MolFromSmiles('CCN'))
    AllChem.EmbedMolecule(a); AllChem.EmbedMolecule(b)
    with pytest.raises(ValueError): symmetry_rmsd(a, b)
