import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem


def generate_conformer(mol: Chem.Mol, seed: int, preserve: bool = False) -> tuple[Chem.Mol, str]:
    mol = Chem.AddHs(Chem.Mol(mol), addCoords=preserve)
    if preserve:
        if mol.GetNumConformers() != 1 or not mol.GetConformer().Is3D():
            raise ValueError('Preserve coordinates requires one 3D input conformer')
        method = 'Input coordinates preserved; hydrogens added geometrically; no optimization'
    else:
        mol.RemoveAllConformers()
        options = AllChem.ETKDGv3(); options.randomSeed = seed; options.numThreads = 1
        if AllChem.EmbedMolecule(mol, options) != 0: raise ValueError('ETKDGv3 embedding failed')
        if AllChem.MMFFHasAllMoleculeParams(mol):
            code = AllChem.MMFFOptimizeMolecule(mol, maxIters=2000)
            method = 'ETKDGv3 + MMFF94 (2000 iteration ceiling)'
        elif AllChem.UFFHasAllMoleculeParams(mol):
            code = AllChem.UFFOptimizeMolecule(mol, maxIters=2000)
            method = 'ETKDGv3 + UFF (2000 iteration ceiling)'
        else: raise ValueError('No complete MMFF/UFF parameterization')
        if code != 0: raise ValueError(f'Conformer optimization did not converge: {code}')
    if not np.isfinite(mol.GetConformer().GetPositions()).all(): raise ValueError('Invalid conformer coordinates')
    return mol, method
