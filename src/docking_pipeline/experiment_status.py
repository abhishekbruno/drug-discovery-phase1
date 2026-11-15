"""Read saved job metadata without importing UI code or running chemistry tools."""
import json
from pathlib import Path

STATUSES = {'running', 'interrupted', 'failed', 'completed', 'completed_with_failures'}
STAGES = {'preparing_receptor', 'docking', 'reporting', 'finished'}


def _text(value) -> str:
    return value if isinstance(value, str) else ''


def read_experiment(root: Path) -> dict:
    """Summarize persisted state; 'running' is not proof of a live process."""
    row = {'id': root.name, 'status': 'not_started', 'stage': '', 'updated_at': '',
           'error': '', 'warning': '', 'progress': None,
           'has_report': (root/'report.json').is_file(),
           'can_resume': (root/'config.resolved.json').is_file()}
    source = root/'experiment.json'
    if not source.exists():
        source = root/'report.json'
    if not source.exists():
        return row
    try:
        state = json.loads(source.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            raise ValueError('Expected a JSON object')
        status = state.get('status')
        row.update(status=status if isinstance(status, str) and status in STATUSES else 'unknown',
                   stage=state.get('stage') if isinstance(state.get('stage'), str) and state['stage'] in STAGES else '',
                   updated_at=_text(state.get('updated_at')) or _text(state.get('started_at')),
                   error=_text(state.get('error')))
        progress = state.get('progress')
        if progress is not None:
            fields = ('total', 'completed', 'succeeded', 'failed')
            valid = (isinstance(progress, dict) and
                     all(type(progress.get(k)) is int and progress[k] >= 0 for k in fields))
            if (valid and progress['succeeded'] + progress['failed'] == progress['completed']
                    and progress['completed'] <= progress['total']):
                row['progress'] = {k: progress[k] for k in fields}
            else:
                row['warning'] = 'Saved progress is invalid; counts are unavailable.'
    except (OSError, ValueError) as exc:
        row.update(status='unreadable', can_resume=False,
                   warning=f'Could not read {source.name}: {exc}')
    return row


def list_experiments(results: Path) -> list[dict]:
    if not results.exists():
        return []
    rows = [read_experiment(root) for root in results.iterdir()
            if root.is_dir() and not root.name.startswith('_')
            and any((root/name).is_file() for name in ('experiment.json', 'config.resolved.json', 'report.json'))]
    return sorted(rows, key=lambda row: (row['updated_at'], row['id']), reverse=True)
