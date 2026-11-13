# PHASE 1 — AUTOMATED MOLECULAR DOCKING PIPELINE
## Master Development Prompt for Antigravity

### ROLE

Act as a senior computational chemistry engineer, molecular docking researcher, scientific Python developer, software architect, and testing engineer.

Your responsibility is to build Phase 1 of an AI-assisted Drug Discovery Platform.

**Phase 1 has one primary objective: develop a fully functional, automated, reproducible molecular docking pipeline.**

Do not build an unrelated full-stack application. Concentrate on the scientific processing engine, automation, correctness, and reliability.

---

## 1. PROJECT OBJECTIVE

Create a system that automatically performs the following workflow:

Protein Structure Input
↓
Protein Validation
↓
Receptor Preparation
↓
Ligand Library Input
↓
Ligand Validation and Preparation
↓
Docking Grid Configuration
↓
AutoDock Vina Execution
↓
Docking Pose Extraction
↓
Binding Score Analysis
↓
Candidate Ranking
↓
Scientific Report Generation

A researcher should be able to provide a protein structure and one or more ligand molecules, start the pipeline, and receive real computational docking results.

All scientific computations must execute using actual molecular modeling tools.

No mocked calculations, fabricated scores, randomly generated binding energies, or hardcoded experimental outcomes are permitted.

## 2. DEVELOPMENT ENVIRONMENT

Target machine:

- Intel Core i5-11400H
- 16 GB RAM
- NVIDIA RTX 2050 with 4 GB VRAM
- Linux or Windows Subsystem for Linux

Use:

- Python 3.11 or another verified compatible version
- RDKit — molecular processing
- BioPython — structure analysis
- Meeko — PDBQT preparation
- AutoDock Vina — molecular docking
- NumPy — numerical operations
- Pandas — result processing
- SciPy — scientific utilities
- Gemmi — crystallographic structure handling where appropriate
- Pydantic — configuration validation
- Pytest — automated testing

Use CPU-based AutoDock Vina for Phase 1.

Do not assume that AutoDock Vina automatically uses the NVIDIA GPU.

Create a reproducible isolated environment using compatible, pinned dependencies.

## 3. PROJECT STRUCTURE

Create a clean Python repository:

drug-discovery/
- README.md
- pyproject.toml
- environment.yml
- config/
  - default.yaml
- data/
  - proteins/
  - ligands/
  - benchmarks/
- src/
  - docking_pipeline/
    - __init__.py
    - cli.py
    - config.py
    - orchestrator.py
    - protein/
      - loader.py
      - validator.py
      - preparation.py
    - ligand/
      - loader.py
      - validator.py
      - conformers.py
      - preparation.py
    - docking/
      - grid.py
      - vina_engine.py
      - batch_runner.py
    - analysis/
      - scoring.py
      - ranking.py
      - rmsd.py
    - reporting/
      - exporter.py
      - report_generator.py
    - utils/
      - logging.py
      - dependencies.py
- tests/
  - unit/
  - integration/
  - benchmarks/
- results/
- scripts/

Use modular, testable functions and typed interfaces.

Keep the core computation independent of any future web interface.

## 4. MODULE 1 — PROTEIN INPUT AND VALIDATION

Implement a protein structure loading system.

Requirements:

1. Accept PDB and supported mmCIF formats.
2. Allow fetching public experimental structures using a PDB identifier.
3. Validate structural input.
4. Identify chains, residues, atoms, bound ligands, and relevant cofactors.
5. Detect missing residues and incomplete atoms where possible.
6. Check for alternate atom locations.
7. Allow explicit receptor-chain selection.
8. Record structure provenance and relevant experimental metadata.
9. Reject corrupted or unsupported structures with meaningful errors.

Do not automatically treat every uploaded structure as docking-ready.

## 5. MODULE 2 — PROTEIN PREPARATION

Implement a receptor preparation pipeline.

Required operations:

- Select the intended protein chain.
- Remove the reference ligand only from the docking receptor, while preserving its original coordinates for validation.
- Apply an explicit solvent and water-handling policy.
- Identify relevant cofactors and metal ions.
- Detect missing atoms requiring repair.
- Handle hydrogens and protonation with a documented method.
- Prepare receptor coordinates and docking atom types.
- Convert the prepared receptor into PDBQT using verified Meeko functionality.
- Verify that the output file is valid.

Do not silently delete scientifically important cofactors, metals, or structural components.

If a receptor cannot be prepared correctly, stop with a detailed error.

Store the prepared receptor and a preparation manifest.

## 6. MODULE 3 — LIGAND INPUT AND PREPARATION

Support ligand input as:

- SMILES
- SDF
- CSV containing compound identifiers and SMILES

Use RDKit for chemical validation and molecular processing.

For every ligand:

1. Parse the molecular structure.
2. Validate atom types, chemical valence, and bonds.
3. Preserve stereochemical information.
4. Generate explicit hydrogens.
5. Generate a three-dimensional conformer.
6. Perform appropriate conformer optimization.
7. Record relevant protonation or tautomer assumptions.
8. Calculate molecular descriptors.
9. Export a prepared 3D SDF.
10. Use Meeko to generate the PDBQT representation.

Required descriptors:

- Molecular weight
- LogP
- Hydrogen-bond donors
- Hydrogen-bond acceptors
- Rotatable bond count
- Topological polar surface area

Implement a separate error state for molecules that cannot be prepared.

One failing ligand must not automatically terminate an entire multi-ligand job.

## 7. MODULE 4 — DOCKING GRID GENERATION

Develop a grid configuration service.

Support:

**Reference-ligand guided docking**
- Identify a known crystallographic ligand.
- Determine the binding-site location from its coordinates.
- Calculate the grid center.
- Use an appropriate configurable box size.
- Validate that the binding region is enclosed.

**Manual docking configuration**
- Allow researchers to enter grid center coordinates.
- Allow configuration of box dimensions in Ångströms.
- Validate coordinate values.

Store all grid parameters in a reproducible configuration file.

Do not invent active sites or use arbitrary docking box positions without identifying the configuration as user-specified.

## 8. MODULE 5 — AUTODOCK VINA ENGINE

This is the central component of Phase 1.

Develop a Python docking engine using the documented AutoDock Vina CLI or Python API.

The engine must:

1. Load the prepared receptor.
2. Load the prepared ligand.
3. Configure the docking grid.
4. Select the scoring function.
5. Configure the random seed.
6. Set CPU resource limits.
7. Configure exhaustiveness.
8. Configure the number of poses.
9. Execute a real docking calculation.
10. Save docking logs.
11. Save resulting molecular poses.
12. Parse the reported energies.
13. Report failure when the computation fails.

Support configurable parameters such as:

- Scoring function: Vina
- Exhaustiveness: 8 by default, configurable
- Number of poses: configurable
- CPU threads: bounded by available resources
- Random seed: explicitly recorded

The output must include:

- Compound identifier
- Docking run identifier
- Actual Vina score in kcal/mol
- Pose number
- Relevant pose RMSD values
- Docked structure location
- Execution parameters
- Execution status

Do not confuse Vina's pose-relative RMSD output with RMSD against a crystallographic reference.

Never label a Vina score as experimentally measured binding affinity.

## 9. MODULE 6 — BATCH DOCKING ENGINE

Create a batch processing system capable of docking multiple ligands against a selected receptor.

Features:

- Sequential execution as the default
- Optional bounded parallel execution
- Per-ligand execution logs
- Per-ligand completion status
- Failure isolation
- Configurable resource limits
- Resume support for interrupted experiments
- Progress reporting
- Detection of completed docking jobs

Use safe subprocess invocation when calling external scientific tools.

Prevent resource exhaustion on the target machine.

Never silently overwrite completed experimental results.

## 10. MODULE 7 — DOCKING RESULT ANALYSIS

Create a result analysis engine.

For each compound, collect:

- The best computed docking score
- Other available poses and scores
- Pose-relative RMSD reported by Vina
- Molecular descriptor values
- Successful or failed docking status

Rank successfully docked compounds according to the selected scoring function.

Within a consistent Vina scoring setup, more negative values generally represent more favorable predicted docking scores.

Explain that docking scores alone do not establish drug effectiveness, toxicity, binding affinity, or clinical usefulness.

Export structured rankings as CSV and JSON.

Do not combine scores produced by incompatible scoring functions into a single ranking without explicit normalization and scientific justification.

## 11. MODULE 8 — SCIENTIFIC VALIDATION

Create a reproducible benchmark using a documented protein–ligand crystal structure.

For the initial benchmark, use:

**PDB 1IEP — c-Abl kinase domain complexed with imatinib.**

Use the official AutoDock Vina docking tutorial as a reference for the workflow and setup.

Implement:

1. Reference structure acquisition.
2. Protein preparation.
3. Extraction of the crystallographic ligand.
4. Ligand preparation.
5. Binding-site grid configuration.
6. Redocking of the reference ligand.
7. Export of computed docking poses.
8. Comparison against the crystallographic pose.
9. Calculation of symmetry-aware heavy-atom RMSD where appropriate.
10. A report containing computed scores, RMSD, configuration, and validation outcome.

A heavy-atom RMSD of approximately 2 Å or lower may be used as a commonly applied redocking validation criterion, but it is not universally sufficient and must not be hardcoded as a guaranteed result.

The benchmark must execute using actual scientific software.

A failed benchmark is a legitimate result and must be investigated and documented.

## 12. MODULE 9 — REPORT GENERATION

Automatically generate a research report containing:

- Experiment identifier
- Date and software versions
- Protein structure identifier
- Ligand identifiers
- Receptor preparation summary
- Ligand preparation summary
- Grid parameters
- Docking parameters
- Candidate ranking
- Docking scores
- Pose information
- Validation results
- Failed calculations
- Scientific limitations

Supported formats:

- JSON
- CSV
- Markdown

Organize outputs by experiment identifier.

Preserve every relevant input, configuration, scientific result, and reproducibility log.

## 13. COMMAND-LINE INTERFACE

Provide a functional command-line interface.

Expected commands should follow a clear design, such as:

```bash
dockpipe check
dockpipe prepare-receptor --input protein.pdb
dockpipe prepare-ligands --input compounds.sdf
dockpipe run --config config/default.yaml
dockpipe benchmark --id 1iep
dockpipe report --job <job_id>
```

Implement these commands or a consistently documented equivalent.

`dockpipe check` must inspect actual dependencies, executable availability, compatible package versions, and the readiness of the environment.

Display clear progress and final job status.

## 14. TESTING REQUIREMENTS

Write and execute tests for:

- Protein loading
- Invalid PDB handling
- Chain selection
- Ligand validation
- SMILES parsing
- 3D conformer generation
- PDBQT preparation
- Grid definition
- Vina execution
- Docking output parsing
- Multi-ligand processing
- Resume behavior
- Scientific report generation
- Reference redocking RMSD

Create both unit and integration tests.

Mocking is acceptable for isolated software unit tests, but scientific validation and integration tests must run the actual tools.

Record test failures rather than hiding them.

## 15. IMPLEMENTATION SEQUENCE

**Stage 1: Environment and repository**
- Initialize Python project.
- Install and verify dependencies.
- Set up logging, configuration, and tests.

**Stage 2: Molecular preparation**
- Implement protein loading.
- Implement receptor preparation.
- Implement ligand processing.
- Validate generated molecular files.

**Stage 3: Core docking engine**
- Integrate AutoDock Vina.
- Execute a real docking job.
- Extract scores and poses.
- Verify result reproducibility.

**Stage 4: Batch processing**
- Accept multiple ligands.
- Add orchestration and failure isolation.
- Generate rankings and structured results.

**Stage 5: Scientific verification**
- Run the 1IEP reference benchmark.
- Compare predicted and experimental poses.
- Run automated tests.
- Fix implementation issues.
- Generate the final scientific report.

Do not skip scientific verification in order to polish the interface.

## 16. STRICT RESTRICTIONS

- Do not implement a React frontend in Phase 1.
- Do not add Evo 2.
- Do not add AlphaFold.
- Do not implement AI molecule generation.
- Do not implement virtual animal simulation.
- Do not implement pharmacokinetic simulation.
- Do not introduce a cloud infrastructure requirement.
- Do not generate fake docking results.
- Do not embed precomputed scores as live outputs.
- Do not claim that a scoring function proves biological efficacy.
- Do not hide unsupported molecular structures or preparation failures.
- Do not perform pathogen optimization or biological enhancement tasks.
- Do not create a visually impressive but scientifically nonfunctional application.

Focus entirely on making the molecular docking pipeline accurate, automated, modular, and reproducible.

## 17. COMPLETION CRITERIA

Phase 1 is complete only when:

- A protein structure can be loaded and validated.
- A receptor can be prepared.
- Multiple ligand molecules can be loaded and prepared.
- The docking grid can be configured correctly.
- AutoDock Vina performs actual docking calculations.
- The system saves real docking scores and poses.
- Compounds can be ranked using computed scores.
- A reference redocking benchmark can be executed.
- Reports and reproducibility files are generated.
- The CLI works.
- Automated tests have been run.
- All remaining scientific limitations are clearly documented.

**FINAL INSTRUCTION**

Start by checking the environment and creating the project architecture. Build the entire Phase 1 pipeline in the specified order.

Do not stop after planning or creating placeholder files.

Prioritize completing a working single-protein/single-ligand docking calculation, validate it, and then extend the same tested engine to multi-ligand batch docking.

At completion, provide the implemented modules, exact commands to run the pipeline, test results, successful benchmark evidence, and remaining limitations.