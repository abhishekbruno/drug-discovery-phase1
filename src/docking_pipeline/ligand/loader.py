from dataclasses import dataclass
from pathlib import Path
import csv
from rdkit import Chem
from docking_pipeline.config import safe_id


@dataclass
class LigandRecord:
    compound_id: str
    molecule: Chem.Mol | None
    error: str | None = None


def load_ligands(path: Path) -> list[LigandRecord]:
    rows = []
    suffix = path.suffix.lower()
    if suffix == '.sdf':
        for i, mol in enumerate(Chem.SDMolSupplier(str(path), removeHs=False), 1):
            name = mol.GetProp('_Name').strip() if mol is not None and mol.HasProp('_Name') else ''
            rows.append(LigandRecord(name or f'compound_{i:05d}', mol, None if mol else 'Invalid SDF record'))
    elif suffix in ('.smi', '.smiles', '.txt', '.csv'):
        if suffix == '.csv':
            with path.open(encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                if not {'compound_id', 'smiles'} <= set(reader.fieldnames or []):
                    raise ValueError('CSV requires compound_id and smiles columns')
                pairs = [(r['compound_id'], r['smiles']) for r in reader]
        else:
            pairs = []
            for i, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
                if not line.strip() or line.lstrip().startswith('#'): continue
                values = line.split(maxsplit=1)
                pairs.append((values[1].strip() if len(values)>1 else f'compound_{i:05d}', values[0]))
        for name, smiles in pairs:
            mol = Chem.MolFromSmiles(smiles or '')
            rows.append(LigandRecord(name or '', mol, None if mol and mol.GetNumAtoms() else f'Invalid SMILES: {smiles}'))
    else:
        raise ValueError('Ligands must be SDF, CSV, or SMILES (.smi/.smiles/.txt)')
    if not rows: raise ValueError('Empty ligand library')
    seen = set()
    for row in rows:
        safe_id(row.compound_id)
        normalized = row.compound_id.casefold()
        if normalized in seen: raise ValueError(f'Duplicate/case-colliding compound identifier: {row.compound_id}')
        seen.add(normalized)
    return rows
