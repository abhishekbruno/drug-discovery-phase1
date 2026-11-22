# Backend retry recovery

Continue the original requirement for recoverable, auditable batches in the existing engine. A retry overwrites the failed ligand's current status while the experiment still seals the previous status hash. Interruption between those writes prevents a valid resume.

Before modifying a failed ligand, atomically checkpoint its existing artifact hashes in the experiment manifest and retire its current-status seal. Verify every sealed historical attempt (including its complete file inventory) on resume. Keep this checkpoint until a new terminal status has been sealed. Serialize manifest updates from parallel workers. Preserve all attempt directories, reject tampered completed evidence, and create a fresh attempt for interrupted work.

Also record running/interrupted experiment states and clear obsolete fatal errors on a valid resume. Infrastructure or integrity errors remain fatal rather than becoming misleading ligand chemistry failures.

Validation: reproduce interrupted retries in sequential and parallel modes; reject modified and added historical files; exercise the write boundary before running status is written; run the full real-tool suite and cross-platform CI. No scientific preparation, scoring, or RMSD algorithms change.

Implemented and locally verified: seven recovery tests, 42 passing tests overall. Independent review added a regression for interruption inside the atomic status replacement; only mutable current-status bookkeeping is excluded from scientific inventories. Cross-platform CI runs on the pushed branch.
