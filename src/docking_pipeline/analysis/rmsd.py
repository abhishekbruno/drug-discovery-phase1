"""Symmetry-aware, in-place heavy atom RMSD: NO ligand alignment."""
import numpy as np
from rdkit import Chem


def symmetry_rmsd(reference: Chem.Mol, pose: Chem.Mol, max_matches: int = 100000) -> float:
    ref, probe = Chem.RemoveHs(reference), Chem.RemoveHs(pose)
    if Chem.MolToSmiles(ref, isomericSmiles=True) != Chem.MolToSmiles(probe, isomericSmiles=True):
        raise ValueError('Reference and pose must have identical chemical graphs, charges and stereochemistry')
    if not ref.GetNumConformers() or not probe.GetNumConformers():
        raise ValueError('RMSD needs 3D coordinates')
    matches = probe.GetSubstructMatches(ref, uniquify=False, useChirality=True, maxMatches=max_matches)
    if not matches or len(matches) >= max_matches:
        raise ValueError('No atom mapping or symmetry enumeration limit reached')
    a, b = ref.GetConformer().GetPositions(), probe.GetConformer().GetPositions()
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Non-finite RMSD coordinates')
    return float(min(np.sqrt(np.mean(np.sum((a-b[list(match)])**2, axis=1))) for match in matches))
