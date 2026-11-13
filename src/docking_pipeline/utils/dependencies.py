import importlib
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess
from docking_pipeline.docking.vina_engine import resolve_executable
from docking_pipeline.utils.logging import sha256

PINS = {'rdkit':'2025.3.6','meeko':'0.7.1','biopython':'1.85','gemmi':'0.7.3','numpy':'2.2.6',
        'pandas':'2.2.3','scipy':'1.15.3','pydantic':'2.11.7','PyYAML':'6.0.2'}


def check_environment(executable: str = 'vina') -> dict:
    result = {'python':platform.python_version(), 'platform':platform.platform(), 'packages':{}, 'errors':[]}
    if not ((3,11) <= __import__('sys').version_info[:2] < (3,13)):
        result['errors'].append('Python 3.11 or 3.12 required')
    for name, expected in PINS.items():
        try:
            actual = version(name)
            importlib.import_module({'biopython':'Bio','PyYAML':'yaml'}.get(name,name))
            result['packages'][name] = actual
            if actual != expected: result['errors'].append(f'{name}: expected {expected}, found {actual}')
        except Exception as exc: result['errors'].append(f'{name}: {exc}')
    try:
        path = resolve_executable(executable)
        process = subprocess.run([path,'--version'],capture_output=True,text=True,timeout=15,check=True)
        output = (process.stdout + process.stderr).strip()
        result['vina'] = {'path':path,'version':output,'sha256':sha256(Path(path))}
        if output != 'AutoDock Vina v1.2.7': result['errors'].append('Vina 1.2.7 required for pinned protocol')
    except Exception as exc: result['errors'].append(f'vina: {exc}')
    result['ready'] = not result['errors']
    return result
