# Verification record

Verified on 13 November 2026 with Python 3.12.10 on Windows, in `E:\project D1`.

## Automated checks

**35 tests passed in 43.92 seconds.** The invocation included `VINA_EXECUTABLE=E:\project D1\tools\vina.exe` and `DOCKPIPE_BENCHMARK_JOB=E:\project D1\results\1iep-local-validation`. Full output: `work/final-tests.log`.

Coverage includes PDB/mmCIF preparation, malformed inputs, chain/cofactor policies, alternate locations, missing sidechain rejection, ligand validation/stereochemistry/conformers/descriptors/PDBQT, grids, real Vina execution, repeated docking, sequential and parallel batches, failure isolation, non-overwrite/resume/tampering, report exports, reference RMSD, and UI setup/empty/resume states.

Integration tests run actual scientific tools. The benchmark artifact test recomputes RMSD from the separately executed full CLI redocking run; without `DOCKPIPE_BENCHMARK_JOB` it explicitly skips. Parser unit tests use synthetic input records only; those never become production results. `pip check`, `dockpipe check` and source compilation pass.

## Full benchmark and repeatability

Two independent Vina calculations ran, first in the original C-drive workspace and then in E. Both used exhaustiveness 32, seed 20261113, CPU 2, and the official tutorial box. Both yielded nine poses and identical PDBQT bytes:

`524eb35f475a689fb89adc0b1aa9c3fba6cf18466c43ef4cd340d347ad77d71d`

Best Vina score: **−12.770 kcal/mol**. Top-pose symmetry-aware heavy-atom reference RMSD: **0.8932053878391383 Å**. The top-scoring pose passes the ≤2 Å criterion. Numerical evidence, real logs and molecular outputs are in `results/1iep-local-validation`; `docs/verification.json` records the measured values and environment.

The original run is preserved under `data/benchmarks/prior-workspace-evidence` with its original paths. The independent local run points to E-drive files and successfully resumes without rerunning completed docking. It started before validation-hash sealing was added; its validation was independently recomputed and compared field-by-field before recording its hash. See `work/finalize_evidence.py`.

## Frontend checks

Streamlit AppTest covers empty results, setup controls, missing upload guidance, and resume before the first completed result. Live browser checks confirmed real benchmark rankings, the molecular viewer, setup controls and actual submission.

The browser submitted `ui-smoke-test` with ethanol and an intentionally invalid SMILES. Ethanol docked at **−2.585 kcal/mol**; the invalid molecule failed separately. The UI displayed the real log and `completed_with_failures` outcome. Its records remain in `results/ui-smoke-test`. This deliberate failure demonstrates isolation.

## Failures found and fixed

- The original structure required an explicit chloride policy; all four chain-A chlorides are now named. No heterogens were silently stripped.
- Meeko's `--write_pdb` required an explicit filename; the real integration test verified the correction.
- Windows case-colliding/reserved IDs could collide on disk. Portable validation now prevents this.
- Cached scores and metadata needed integrity checks. Resume verifies complete artifact inventories, status hashes, completion metadata and validation hashes; older successful records are checked against their verified scientific files.
- Reference ligands bypassed alternate-location and protein-deletion checks. Those checks now run before extraction, and a complete selected alternate is preserved.
- First-run interruption hid the UI resume control. It now renders independently of completed reports.
- Browser inspection found a dark-theme contrast mismatch and a deprecated Plotly argument. Both were corrected.

The regression run recorded **8 failures before these fixes** (`work/review-red.log`), then passed (`work/review-green.log`). Initial development failures are documented here, not hidden as clean first-pass success. No substantive independent-review finding remains open. Minor report path references were corrected too.

## Decisions and remaining limits

Native Windows was verified because WSL was not installed. Linux/WSL setup is supplied but untested here. Cross-platform bitwise repeatability is not asserted. The frontend is a local Streamlit UI sharing the engine; it is not an authenticated public service. Receptor repair, pKa/pH prediction, protomer/tautomer ensembles, flexible receptors and broad prospective screening validation remain outside this Phase 1 protocol. Unsupported preparation fails with logs. A passing 1IEP redocking does not establish biological efficacy or experimental affinity.
