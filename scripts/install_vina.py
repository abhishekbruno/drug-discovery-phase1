"""Download the official pinned CPU Vina executable; never overwrite a binary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import urllib.request

VERSION='1.2.7'
parser=argparse.ArgumentParser()
parser.add_argument('--directory',type=Path,default=Path('tools'))
args=parser.parse_args()
system=platform.system().lower(); machine=platform.machine().lower()
if system=='windows': asset=f'vina_{VERSION}_win.exe'; name='vina.exe'
elif system in ('linux','darwin'):
    architecture='aarch64' if machine in ('arm64','aarch64') else 'x86_64' if machine in ('amd64','x86_64') else None
    if architecture is None: raise SystemExit(f'Unsupported architecture: {machine}')
    asset=f"vina_{VERSION}_{'mac' if system=='darwin' else 'linux'}_{architecture}"; name='vina'
else: raise SystemExit(f'Unsupported OS: {system}')
args.directory.mkdir(parents=True,exist_ok=True)
destination=args.directory/name
if destination.exists(): raise SystemExit(f'Already exists; verify with dockpipe check: {destination}')
url=f'https://github.com/forlilab/AutoDock-Vina/releases/download/v{VERSION}/{asset}'
with urllib.request.urlopen(url,timeout=120) as response: payload=response.read(100_000_001)
if len(payload)>100_000_000: raise SystemExit('Unexpected binary size')
digest=hashlib.sha256(payload).hexdigest()
if system=='windows' and digest!='e0c4b2715e0c1a74f6e92d0f3be0328ac97542eafbc111e6b1efad897a73cce5':
    raise SystemExit('Windows binary differs from the verified build')
destination.write_bytes(payload)
if os.name!='nt': destination.chmod(0o755)
destination.with_suffix('.provenance.json').write_text(json.dumps({'version':VERSION,'url':url,'sha256':digest,
    'checksum_provenance':'Windows digest verified during development; other platform digest recorded after HTTPS download, not publisher-signed'},indent=2))
print(f'Installed {destination.resolve()}\nSHA256: {digest}')
