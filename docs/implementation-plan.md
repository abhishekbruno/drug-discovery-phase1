# Phase 1 molecular docking implementation plan

**Goal:** Run genuine CPU Vina docking, isolate ligand failures, preserve reproducibility, and measure 1IEP redocking accuracy.

**Architecture:** Typed configuration drives strict structure validation, Meeko preparation, safe Vina subprocesses, per-ligand immutable attempts, and atomic reports. Reference RMSD uses chemical graph symmetry in the receptor coordinate frame, without ligand superposition.

**Environment decision:** Python 3.12 is available on this Windows host; verify the portable scientific stack and official Vina 1.2.7 executable here. Provide pinned Linux/WSL environment instructions. Do not install WSL or change OS features.

**Spec:** `docs/request.md` (the supplied master development prompt).

## Tasks

- [x] 1. Environment/configuration: pin dependencies; reject invalid grids, unsafe IDs, and excessive CPU budgets; inspect real imports and Vina version.
- [x] 2. Molecular preparation: test malformed structures, chain/heterogen policies, alternate atoms, ligand parsing, stereochemistry, conformers, and actual Meeko PDBQT writing. Record assumptions and preserve original coordinates. Reject incomplete residues rather than silently repairing/deleting them.
- [x] 3. Single docking: test Vina output parsing and real executable integration; save all poses, scores, parameters, hashes, stdout, and stderr. Recover chemical graphs through Meeko export.
- [x] 4. Batch/reporting: test failure isolation, identity-checked resume, content hashes, non-overwrite, and rankings/JSON/CSV/Markdown. Sequential default; bounded parallel independent subprocesses.
- [x] 5. Benchmark: acquire 1IEP and pinned official tutorial inputs, extract crystallographic STI with CCD bond orders, prepare receptor/ligand, redock, calculate symmetry-aware in-place heavy atom RMSD, and report the observed outcome. Run full tests and a repeatability check.
- [x] 6. Independent review, fix substantive findings, package source and evidence with exact commands and limitations.

Each implementation task starts with failing behavior tests, then implementation and a passing verification. Integration and benchmark tests invoke genuine scientific tools. No generated energies or substituted expected outcomes.

## Review focus

1. Resume must reject changed inputs/configuration or tampered completed artifacts.
2. Unselected chains and heterogens must have explicit recorded policy.
3. RMSD must preserve receptor coordinates and enforce graph identity/stereochemistry.
4. A failed ligand must remain visible in reports and not prevent other ligands from running.
5. Unsupported chemistry, missing atoms, ambiguous alternate locations, and oversized grids must fail explicitly.


## Accepted scope updates
User requested a frontend UI and moved the active project to E:\project D1. Implemented local Streamlit controls, background CLI execution, real results/pose visualization, reports and environment checks. Completed independent review and regression fixes. See verification.md for evidence and explicit platform limitations.
