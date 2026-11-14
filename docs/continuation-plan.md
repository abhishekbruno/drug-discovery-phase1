# Continued verification work

The requested engine/UI and GitHub push are complete. The remaining original-platform gap is that native Windows was verified but Linux/WSL execution was not.

- Add automatic fresh-checkout Windows and Linux scientific checks with actual Vina integration tests, dependency inspection and recorded test artifacts. Keep all runtime operations local; hosted CI is optional verification, not a runtime dependency.
- Run full real 1IEP redocking on Linux, preserving observed outcomes, software versions and raw files even when validation fails. Do not reuse checked-in scores as live results.
- Fix issues exposed by those runs with focused regression tests, then record the outcome and push the verified changes.

Work stays in the user-specified `E:\project D1` checkout. Direct dependency pins and Vina 1.2.7 remain unchanged. Pin GitHub Actions by verified commit SHA. Keep per-job CPU budgets at two and use bounded job timeouts. Do not add unrelated scientific features or change system/WSL installation.

Completed: both platform test jobs passed (34 tests each) and full Linux 1IEP redocking passed at 0.968343 Å. Evidence is preserved under `evidence/cross-platform/`; the initial Windows runner dependency conflict and its isolated-environment fix are recorded in `docs/verification.md`. Backend interruption recovery is the next scoped task, documented in `docs/backend-recovery-plan.md`.
