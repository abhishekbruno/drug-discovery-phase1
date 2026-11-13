from rdkit import Chem


def validate_ligand(molecule: Chem.Mol) -> list[str]:
    if molecule is None or not molecule.GetNumAtoms(): raise ValueError('Empty molecule')
    Chem.SanitizeMol(molecule)
    if len(Chem.GetMolFrags(molecule)) != 1:
        raise ValueError('Disconnected salts/mixtures require explicit researcher preprocessing')
    if molecule.GetNumHeavyAtoms() > 120: raise ValueError('Ligand exceeds 120 heavy atom resource limit')
    allowed = {1,6,7,8,9,15,16,17,35,53}
    if any(a.GetAtomicNum() not in allowed for a in molecule.GetAtoms()):
        raise ValueError('Unsupported ligand element for this Phase 1 protocol')
    if any(a.GetNumRadicalElectrons() for a in molecule.GetAtoms()): raise ValueError('Radical ligands unsupported')
    warnings = []
    if any(tag == '?' for _, tag in Chem.FindMolChiralCenters(molecule, includeUnassigned=True)):
        warnings.append('Unspecified stereocenters: generated conformer chooses a configuration; no stereoisomer enumeration')
    return warnings
