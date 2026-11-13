from pathlib import Path
from rdkit import Chem
import pytest
from docking_pipeline.benchmark import extract_reference, validate_redocking
from docking_pipeline.analysis.rmsd import symmetry_rmsd


def test_crystal_extraction_uses_ccd_atom_names_and_coordinates(tmp_path):
    root=Path('data/benchmarks/1iep')
    path=extract_reference(root/'1iep.pdb',root/'STI.cif',tmp_path/'reference.sdf')
    mol=Chem.SDMolSupplier(str(path),removeHs=False)[0]
    assert mol.GetNumHeavyAtoms()==37
    assert mol.GetConformer().Is3D()
    assert symmetry_rmsd(mol,mol)==pytest.approx(0)
    assert len(Chem.GetMolFrags(mol))==1
