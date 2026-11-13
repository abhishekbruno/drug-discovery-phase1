from pathlib import Path
import pytest
from rdkit import Chem
from docking_pipeline.config import ProteinConfig
from docking_pipeline.protein.preparation import prepare_receptor

DATA = Path('data/benchmarks/1iep')


@pytest.mark.integration
def test_receptor_meeko_actual_and_reference_preserved(tmp_path):
    result = prepare_receptor(ProteinConfig(input=DATA/'1iep.pdb', chains=['A'], reference_residue='A:201:STI', remove_residues=['A:1:CL','A:2:CL','A:4:CL','A:5:CL']), tmp_path/'receptor')
    assert Path(result['pdbqt']).stat().st_size > 10000
    assert Path(result['reference_pdb']).is_file()
    assert len(result['reference_coordinates']) == 37
    assert 'STI' not in Path(result['selected_pdb']).read_text()
    assert result['removed_residues']


def test_missing_chain_fails(tmp_path):
    with pytest.raises(ValueError, match='chain'):
        prepare_receptor(ProteinConfig(input=DATA/'1iep.pdb', chains=['Z']), tmp_path/'bad')


def test_unapproved_heterogen_fails(tmp_path):
    with pytest.raises(ValueError, match='Heterogen'):
        prepare_receptor(ProteinConfig(input=DATA/'1iep.pdb', chains=['A']), tmp_path/'bad')


def test_protein_cannot_be_removed_as_reference(tmp_path):
    import gemmi
    structure=gemmi.read_structure(str(DATA/'1iep.pdb')); res=structure[0]['A'][0]
    with pytest.raises(ValueError,match='Reference must be a non-protein'):
        prepare_receptor(ProteinConfig(input=DATA/'1iep.pdb',chains=['A'],reference_residue=f'A:{res.seqid}:{res.name}'),tmp_path/'bad')


def test_ambiguous_reference_altloc_fails(tmp_path):
    import gemmi
    structure=gemmi.read_structure(str(DATA/'1iep.pdb'))
    residue=next(r for r in structure[0]['A'] if r.name=='STI')
    residue[0].altloc='A'; duplicate=residue[0].clone(); duplicate.altloc='B'; residue.add_atom(duplicate)
    path=tmp_path/'alt.pdb'; structure.write_pdb(str(path))
    with pytest.raises(ValueError,match='Alternate locations in reference'):
        prepare_receptor(ProteinConfig(input=path,chains=['A'],reference_residue='A:201:STI',
            remove_residues=['A:1:CL','A:2:CL','A:4:CL','A:5:CL']),tmp_path/'bad')


@pytest.mark.integration
def test_mmcif_receptor_preparation(tmp_path):
    import gemmi
    structure=gemmi.read_structure(str(DATA/'tutorial_receptorH.pdb'))
    path=tmp_path/'protein.cif'; structure.make_mmcif_document().write_file(str(path))
    result=prepare_receptor(ProteinConfig(input=path,chains=['A']),tmp_path/'prepared')
    assert Path(result['pdbqt']).stat().st_size>10000


@pytest.mark.integration
def test_missing_sidechain_atom_is_not_silently_deleted(tmp_path):
    import gemmi
    structure=gemmi.read_structure(str(DATA/'tutorial_receptorH.pdb'))
    residue=next(r for r in structure[0]['A'] if r.name=='LYS')
    residue.remove_atom('NZ','\x00')
    path=tmp_path/'incomplete.pdb'; structure.write_pdb(str(path))
    with pytest.raises(RuntimeError,match='Command failed'):
        prepare_receptor(ProteinConfig(input=path,chains=['A']),tmp_path/'prepared')
