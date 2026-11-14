# Verification record

Verified on 13 November 2026 with Python 3.12.10 on Windows, in `E:\project D1`.

## Automated checks

**35 tests passed in 43.92 seconds.** The invocation included `VINA_EXECUTABLE=E:\project D1\tools\vina.exe` and `DOCKPIPE_BENCHMARK_JOB=E:\project D1\results\1iep-local-validation`. Full output: `work/final-tests.log`.

Coverage includes PDB/mmCIF preparation, malformed inputs, chain/cofactor policies, alternate locations, missing sidechain rejection, ligand validation/stereochemistry/conformers/descriptors/PDBQT, grids, real Vina execution, repeated docking, sequential and parallel batches, failure isolation, non-overwrite/resume/tampering, report exports, reference RMSD, and UI setup/empty/resume states.

Integration tests run actual scientific tools. The benchmark artifact test recomputes RMSD from the separately executed full CLI redocking run; without `DOCKPIPE_BENCHMARK_JOB` it explicitly skips. Parser unit tests use synthetic input records only; those never become production results. `pip check`, `dockpipe check` and source compilation pass.

## Fresh-checkout cross-platform verification

The [Scientific checks run](https://github.com/abhishekbruno/drug-discovery-phase1/actions/runs/43481093559) tests commit `77b11bb65aa1832beb09872e0fdbfebb3cafa98c`. Both Ubuntu 24.04 and Windows Server 2025 passed **34 tests, zero failures/errors/skips**, including actual Vina calculations and Streamlit checks. The separate benchmark artifact test is deliberately excluded from this matrix and runs after full redocking. Both runners use Python 3.12.10 and the pinned scientific package versions. Environment inspection and `pip check` passed.

The initial Windows CI run failed because preinstalled `pipx` required a newer `packaging` than the application's pinned environment. Creating a clean virtual environment for every CI job resolved that conflict without changing scientific dependencies. The initial Linux test job passed. This was an environment isolation issue, not a failed scientific result.

JUnit reports, environment records, resolved package lists and downloaded artifact SHA-256 digests are preserved in `evidence/cross-platform/`. The artifact hashes were checked against GitHub's metadata before extraction. Historical runner paths in these files are retained for provenance; they are not live paths on this machine. The local continuation baseline also passed **35 tests in 55.17 seconds**.

The full Linux benchmark also passed, with a top-scoring pose RMSD of **0.9683428726019104 Å**, Vina score **−12.749 kcal/mol**, and nine exported poses. Its separate artifact test passed on Linux. All nine RMSDs were independently recomputed again from the downloaded SDF coordinates on the local Windows environment and matched within 1e-10 Å. The Linux pose SHA-256 is `acd9b2762f46cc5ee5677b323faa2945bea8de347ea9f03cf0f5f1c67523caa8`. The difference from the Windows score/coordinates is retained, not normalized away: cross-platform bitwise equivalence is not claimed. The benchmark used the same Vina version, grid, seed, CPU count and exhaustiveness, with the official Linux binary.

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

## Backend recovery verification — 14 November 2026

Interrupted retries reproduced a stale status-checksum failure in both sequential and threaded execution: **2 failing regression tests** before the fix (`work/recovery-red.log`). Retry checkpoints now preserve sealed historical attempts before the current status changes. Manifest writes are serialized across workers; resume clears obsolete fatal errors and records the current lifecycle state.

The complete local suite passed **41 tests in 100.12 seconds**, including six new recovery cases (`work/backend-full-tests.log`). These exercise sequential and parallel retries, preservation of successful real Vina results, modified/added historical-artifact rejection, and interruption immediately before a running-status write or immediately after a terminal-status write. Fault injection simulates interruption only; receptor preparation and successful docking still execute the real tools. `pip check` also passed.

A focused independent review found an additional boundary: interruption after writing `status.json.tmp` but before replacing the previous current status. Its regression failed before the correction (`work/atomic-recovery-red.log`). Only the compound-root current-status file and its known atomic temporary file are excluded from scientific artifact inventories. Status-named files inside attempt directories remain protected, and the next running-status write replaces the interrupted temporary file.

Final verification after that fix: **42 tests passed in 121.57 seconds**, including seven recovery cases. Output is preserved in `evidence/cross-platform/backend-local-tests.txt`. Source compilation and `git diff --check` passed. The reviewer confirmed the corrected temporary-file handling and reported no remaining review blocker.

## Decisions and remaining limits

Native Windows and Ubuntu Linux have been verified. WSL itself remains untested because it is not installed locally. Cross-platform bitwise repeatability is not asserted. The frontend is a local Streamlit UI sharing the engine; it is not an authenticated public service. Receptor repair, pKa/pH prediction, protomer/tautomer ensembles, flexible receptors and broad prospective screening validation remain outside this Phase 1 protocol. Unsupported preparation fails with logs. A passing 1IEP redocking does not establish biological efficacy or experimental affinity.
