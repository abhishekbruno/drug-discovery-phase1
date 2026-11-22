# Experiment workspace implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make actual backend progress, incomplete experiments and recovery visible in the existing local UI.

**Architecture:** Persist stage and completed-compound counts in the existing atomic experiment manifest. Add a read-only experiment summary module and a periodically refreshed detail panel. Keep report views and scientific algorithms intact.

**Tech Stack:** Existing Python 3.12 / Streamlit 1.50 / pytest stack; no new dependencies.

**Spec:** `docs/request.md`, original frontend request, and the user's 15 November instruction to continue backend/UI work, consult other GitHub repositories and push at a specific milestone.

## Global constraints

- Work in `E:\project D1`; user has authorized a GitHub push at the tested milestone.
- All scores and poses remain real computed outputs. Progress means completed compounds, not estimated docking time.
- A persisted `running` state alone does not prove a process is alive.
- Corrupt metadata must not crash the whole workspace or fabricate a successful result.
- Preserve existing preparation/scoring pins and immutable attempt directories.

## Review focus

- First-run interruption without report: visible status and recovery controls.
- Stale running state after server/process restart: explicit uncertainty, backend locks remain authoritative.
- Invalid or partially written JSON: actionable message; other experiments still accessible.
- Parallel callbacks and retries: correct counts, serialized manifest updates, no double counting.
- Long names/narrow screens: readable labels and no page overflow.

## Tasks

- [x] Add failing tests for persistent progress and read-only experiment summaries, including malformed metadata and legacy records.
- [x] Record stage and actual completed/success/failed counts in orchestrator; add `experiment_status.py` without importing Streamlit or running scientific tools.
- [x] Extend UI tests for incomplete experiment selection, status/error visibility, filters and invalid reports; implement workspace overview and live selected-experiment panel with resume controls.
- [x] Verify real backend suite, UI interactions on desktop and mobile, and independent review.
- [x] Update verification/reference notes; commit and push the complete tested milestone to the current branch/PR.

Ruling: expose the same read-only summary through `dockpipe status --job` so backend users can inspect recovery without launching Streamlit. This uses the existing summary module and has a CLI regression test; it does not run or modify jobs.

Verification: 49 tests passed in 114.82 seconds. A real UI submission and retry preserved the successful pose hash/time and created a fresh failed attempt. Browser checks covered status filtering and a 390 px viewport. Review's nested malformed-report finding was reproduced and fixed. Detailed evidence is in `docs/verification.md` and `evidence/workspace/`.

## Reference decisions

Use ideas from reviewed upstream files, not copied code. Streamlit's version-pinned fragment example supports isolated timed refreshes; OdorSig's `code/app.py` exposes pipeline stages but its deletion of output directories and synchronous workflow do not fit Dockpipe's immutable, resumable jobs. Meeko v0.7.1 documents the preparation/export boundary already used here. See `docs/repository-references.md` for inspected URLs and blob identifiers.
