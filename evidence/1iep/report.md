# Docking experiment 1iep-local-validation

Status: **completed**
Started (UTC): 2026-11-13T08:28:42.126142+00:00
Updated (UTC): 2026-11-13T08:38:08.241575+00:00

## Reproducibility

```json
{
  "software": {
    "python": "3.12.10",
    "platform": "Windows-11-10.0.26300-SP0",
    "packages": {
      "rdkit": "2025.3.6",
      "meeko": "0.7.1",
      "biopython": "1.85",
      "gemmi": "0.7.3",
      "numpy": "2.2.6",
      "pandas": "2.2.3",
      "scipy": "1.15.3",
      "pydantic": "2.11.7",
      "PyYAML": "6.0.2"
    },
    "errors": [],
    "vina": {
      "path": "E:\\project D1\\tools\\vina.exe",
      "version": "AutoDock Vina v1.2.7",
      "sha256": "e0c4b2715e0c1a74f6e92d0f3be0328ac97542eafbc111e6b1efad897a73cce5"
    },
    "ready": true
  },
  "configuration": {
    "experiment_id": "1iep-local-validation",
    "protein": {
      "input": "E:\\project D1\\data\\benchmarks\\1iep\\1iep.pdb",
      "chains": [
        "A"
      ],
      "reference_residue": "A:201:STI",
      "water_policy": "remove",
      "heterogen_policy": "error",
      "remove_residues": [
        "A:1:CL",
        "A:2:CL",
        "A:4:CL",
        "A:5:CL"
      ],
      "altloc": null,
      "residue_templates": {}
    },
    "ligands": "E:\\project D1\\data\\benchmarks\\1iep\\reference.sdf",
    "output_dir": "E:\\project D1\\results",
    "grid": {
      "mode": "manual",
      "center": [
        15.19,
        53.903,
        16.917
      ],
      "size": [
        20.0,
        20.0,
        20.0
      ],
      "padding": 5.0
    },
    "docking": {
      "executable": "E:\\project D1\\tools\\vina.exe",
      "scoring": "vina",
      "seed": 20261113,
      "cpu": 2,
      "workers": 1,
      "exhaustiveness": 32,
      "num_modes": 9,
      "energy_range": 4.0,
      "timeout_seconds": 1800
    },
    "ligand_seed": 17,
    "preserve_sdf_coordinates": false
  },
  "grid": {
    "center": [
      15.19,
      53.903,
      16.917
    ],
    "size": [
      20.0,
      20.0,
      20.0
    ],
    "source": "user-specified",
    "units": "angstrom"
  }
}
```

## Receptor preparation

Meeko 0.7.1 residue templates add/match hydrogens; default residue states unless residue_templates supplied. No pKa calculation, pH optimization, or missing-heavy-atom repair.
Selected chains: A. Removed residues: 454; each is listed in receptor-001/manifest.json.
Unresolved sequence residues are reported, not rebuilt. Existing residues must pass strict Meeko matching; no allow_bad_res.

## Candidate ranking

| Rank | Compound | Vina score (kcal/mol) |
|---:|---|---:|
| 1 | imatinib | -12.770 |

## Ligand preparation and failures

- **imatinib**: success. ETKDGv3 + MMFF94 (2000 iteration ceiling). Input formal charges and tautomer preserved; explicit Hs from RDKit valence. No pH prediction or tautomer enumeration.
  - 9 poses; see poses.csv and ligands/imatinib/attempt-001/docking/poses.sdf.

## Crystallographic validation

```json
{
  "status": "passed",
  "criterion": "Top-scoring pose symmetry-aware heavy atom RMSD <= threshold in the original receptor frame; no superposition",
  "threshold_angstrom": 2.0,
  "top_scoring_pose": {
    "pose_number": 1,
    "heavy_atom_rmsd_angstrom": 0.8932053878391383,
    "score_kcal_mol": -12.77
  },
  "lowest_rmsd_pose": {
    "pose_number": 1,
    "heavy_atom_rmsd_angstrom": 0.8932053878391383,
    "score_kcal_mol": -12.77
  },
  "poses": [
    {
      "pose_number": 1,
      "heavy_atom_rmsd_angstrom": 0.8932053878391383,
      "score_kcal_mol": -12.77
    },
    {
      "pose_number": 2,
      "heavy_atom_rmsd_angstrom": 2.0983824980465573,
      "score_kcal_mol": -10.829
    },
    {
      "pose_number": 3,
      "heavy_atom_rmsd_angstrom": 12.416363973576336,
      "score_kcal_mol": -10.571
    },
    {
      "pose_number": 4,
      "heavy_atom_rmsd_angstrom": 1.6701851896025086,
      "score_kcal_mol": -10.382
    },
    {
      "pose_number": 5,
      "heavy_atom_rmsd_angstrom": 13.2277445402314,
      "score_kcal_mol": -10.31
    },
    {
      "pose_number": 6,
      "heavy_atom_rmsd_angstrom": 11.916378790827627,
      "score_kcal_mol": -9.873
    },
    {
      "pose_number": 7,
      "heavy_atom_rmsd_angstrom": 12.231018110812649,
      "score_kcal_mol": -9.74
    },
    {
      "pose_number": 8,
      "heavy_atom_rmsd_angstrom": 12.652658596815435,
      "score_kcal_mol": -9.695
    },
    {
      "pose_number": 9,
      "heavy_atom_rmsd_angstrom": 6.650751579150101,
      "score_kcal_mol": -9.641
    }
  ],
  "reference": "PDB 1IEP chain A residue STI 201; CCD bond orders, original experimental coordinates",
  "reference_sha256": "c83a6cb14e36100d24729dd69fb3e210726638a3291b94c2c245e64e0854063c",
  "method": "All chirality-aware identical-graph mappings; minimum in-place heavy atom RMSD",
  "caveat": "Passing one redocking case is not general validation of affinity ranking or prospective screening.",
  "protocol": "Official Vina tutorial box; raw 1IEP chain A prepared strictly with Meeko; chloride and water removal recorded; de novo ETKDG ligand conformer"
}
```

## Scientific limitations

- Vina scores are computed docking scores in kcal/mol, not experimentally measured binding affinities. They do not establish efficacy, toxicity, pharmacokinetics, or clinical usefulness.
- Rigid receptor, implicit solvent, one input protonation/tautomer state and limited ligand sampling. No induced fit, free-energy calculation or pKa prediction.
- Vina pose-relative RMSD lower/upper bounds compare docked poses to the best docked pose; they are distinct from crystallographic heavy-atom RMSD.
- Only scores from this consistent Vina protocol are ranked. Cross-target, cross-grid or cross-protocol comparisons are not validated.
- Missing residues are reported but not reconstructed. Unsupported residues, incomplete heavy atoms and unsupported chemistry fail explicitly.
- Approximately 2 A reference RMSD is a useful redocking criterion, not universal proof of screening accuracy. One benchmark is not broad validation.
- Exact repeatability is verified on the same executable/platform/CPU count; cross-platform floating-point and search differences can occur.
