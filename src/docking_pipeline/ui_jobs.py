"""Background local CLI jobs; UI reruns do not interrupt scientific calculations."""
from pathlib import Path
import os
import subprocess
import sys
import threading
from docking_pipeline.utils.logging import now


class JobManager:
    def __init__(self):
        self.process = None
        self.job = None
        self.guard = threading.Lock()

    def launch(self, args: list[str], log: Path, label: str) -> dict:
        with self.guard:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError('A UI calculation is already running. Wait for it to finish.')
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open('x', encoding='utf-8') as stream:
                self.process = subprocess.Popen([sys.executable, '-m', 'docking_pipeline.cli', *args],
                    stdout=stream, stderr=subprocess.STDOUT, shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.job={'label':label,'log':str(log),'started_at':now(),'pid':self.process.pid}
            return dict(self.job)

    def snapshot(self) -> dict | None:
        with self.guard:
            if self.job is None: return None
            return {**self.job,'returncode':self.process.poll()}
