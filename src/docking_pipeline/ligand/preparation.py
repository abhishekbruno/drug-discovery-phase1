from pathlib import Path
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors
from meeko import MoleculePreparation, PDBQTWriterLegacy
from docking_pipeline.ligand.loader import LigandRecord
from docking_pipeline.ligand.validator import validate_ligand
from docking_pipeline.ligand.conformers import generate_conformer
from docking_pipeline.utils.logging import write_json, sha256


def validate_pdbqt(path: Path, ligand: bool) -> None:
    lines = path.read_text().splitlines()
    atoms = [line for line in lines if line.startswith(('ATOM  ', 'HETATM'))]
    if not atoms: raise ValueError(f'No atoms in PDBQT: {path}')
    import math
    for line in atoms:
        values = [float(line[30:38]), float(line[38:46]), float(line[46:54]), float(line[70:76])]
        if not all(map(math.isfinite, values)) or not line[77:].strip(): raise ValueError('Invalid PDBQT coordinates/charge/type')
    if ligand and not any(line.startswith('TORSDOF ') for line in lines): raise ValueError('Missing ligand torsion tree')


def prepare_ligand(record: LigandRecord, output: Path, seed: int = 17, preserve: bool = False) -> dict:
    if record.error: raise ValueError(record.error)
    warnings = validate_ligand(record.molecule)
    mol, method = generate_conformer(record.molecule, seed, preserve)
    setups = MoleculePreparation().prepare(mol)
    if len(setups) != 1: raise ValueError('Multiple Meeko setups require explicit protocol')
    pdbqt, success, message = PDBQTWriterLegacy.write_string(setups[0])
    if not success: raise ValueError(f'Meeko ligand preparation: {message}')
    output.mkdir(parents=True, exist_ok=False)
    sdf_path, qt_path = output/'ligand.sdf', output/'ligand.pdbqt'
    mol.SetProp('_Name', record.compound_id)
    with Chem.SDWriter(str(sdf_path)) as writer: writer.write(mol)
    qt_path.write_text(pdbqt, encoding='utf-8'); validate_pdbqt(qt_path, True)
    heavy = Chem.RemoveHs(mol)
    manifest = {'compound_id': record.compound_id, 'sdf': str(sdf_path.resolve()), 'pdbqt': str(qt_path.resolve()),
                'canonical_isomeric_smiles': Chem.MolToSmiles(heavy), 'seed': seed, 'conformer_method': method,
                'protonation': 'Input formal charges and tautomer preserved; explicit Hs from RDKit valence. No pH prediction or tautomer enumeration.',
                'charge_method': 'Meeko Gasteiger; Vina scoring uses atom types, not electrostatic partial charges',
                'warnings': warnings, 'sha256': {'sdf': sha256(sdf_path), 'pdbqt': sha256(qt_path)},
                'descriptors': {'molecular_weight': Descriptors.MolWt(heavy), 'logp': Crippen.MolLogP(heavy),
                                'hbond_donors': Lipinski.NumHDonors(heavy), 'hbond_acceptors': Lipinski.NumHAcceptors(heavy),
                                'rotatable_bonds': Lipinski.NumRotatableBonds(heavy), 'tpsa': rdMolDescriptors.CalcTPSA(heavy)}}
    write_json(output/'manifest.json', manifest)
    return manifest
