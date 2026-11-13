from pathlib import Path
import re
import urllib.request
import gemmi
from docking_pipeline.utils.logging import sha256, write_json, now


def fetch_structure(pdb_id: str, output: Path) -> Path:
    if not re.fullmatch(r'[0-9][A-Za-z0-9]{3}', pdb_id): raise ValueError('PDB ID must be four alphanumeric characters, starting with a digit')
    output.mkdir(parents=True, exist_ok=True)
    target = output/f'{pdb_id.lower()}.pdb'
    if target.exists(): raise FileExistsError(target)
    url = f'https://files.rcsb.org/download/{pdb_id.upper()}.pdb'
    with urllib.request.urlopen(url, timeout=60) as response: data = response.read(25_000_001)
    if len(data)>25_000_000: raise ValueError('Structure exceeds 25 MB limit')
    target.write_bytes(data)
    load_structure(target)
    write_json(target.with_suffix('.provenance.json'), {'url': url, 'retrieved_at': now(), 'sha256': sha256(target)})
    return target


def load_structure(path: Path) -> gemmi.Structure:
    if path.suffix.lower() not in ('.pdb', '.cif', '.mmcif'): raise ValueError('Supported protein formats: PDB, mmCIF')
    if path.stat().st_size > 25_000_000: raise ValueError('Structure exceeds 25 MB limit')
    try:
        structure = gemmi.read_structure(str(path))
        if len(structure) != 1: raise ValueError('Exactly one structural model is required; select an ensemble model explicitly')
        if not any(len(res) for chain in structure[0] for res in chain): raise ValueError('No atoms in structure')
        import math
        if any(not all(map(math.isfinite, (a.pos.x,a.pos.y,a.pos.z))) for chain in structure[0] for res in chain for a in res):
            raise ValueError('Non-finite structure coordinates')
        return structure
    except (RuntimeError, IndexError) as exc:
        raise ValueError(f'Corrupt or unsupported structure: {path}: {exc}') from exc
