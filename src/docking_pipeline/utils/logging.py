"""Atomic JSON, content hashes, UTC timestamps, and subprocess logs."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def run_logged(args: list[str], log: Path, timeout: int) -> subprocess.CompletedProcess:
    log.parent.mkdir(parents=True, exist_ok=True)
    write_json(log.with_suffix('.command.json'), {'argv': args, 'started_at': now(), 'timeout_seconds': timeout})
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, env=env, shell=False)
    if result.returncode:
        raise RuntimeError(f'Command failed (exit {result.returncode}); see {log}:\n{log.read_text(encoding="utf-8")[-4000:]}')
    return result
