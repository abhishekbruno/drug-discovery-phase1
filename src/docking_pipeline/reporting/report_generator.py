from pathlib import Path
import json
from docking_pipeline.reporting.exporter import export_results

LIMITATIONS = [
    'Vina scores are computed docking scores in kcal/mol, not experimentally measured binding affinities. They do not establish efficacy, toxicity, pharmacokinetics, or clinical usefulness.',
    'Rigid receptor, implicit solvent, one input protonation/tautomer state and limited ligand sampling. No induced fit, free-energy calculation or pKa prediction.',
    'Vina pose-relative RMSD lower/upper bounds compare docked poses to the best docked pose; they are distinct from crystallographic heavy-atom RMSD.',
    'Only scores from this consistent Vina protocol are ranked. Cross-target, cross-grid or cross-protocol comparisons are not validated.',
    'Missing residues are reported but not reconstructed. Unsupported residues, incomplete heavy atoms and unsupported chemistry fail explicitly.',
    'Approximately 2 A reference RMSD is a useful redocking criterion, not universal proof of screening accuracy. One benchmark is not broad validation.',
    'Exact repeatability is verified on the same executable/platform/CPU count; cross-platform floating-point and search differences can occur.'
]


def generate_report(report: dict, output: Path) -> None:
    report['limitations'] = LIMITATIONS
    export_results(report,output)
    lines=[f"# Docking experiment {report['experiment_id']}", '', f"Status: **{report['status']}**", f"Started (UTC): {report['started_at']}",
           f"Updated (UTC): {report['updated_at']}", '', '## Reproducibility', '', '```json',
           json.dumps({'software':report['environment'],'configuration':report['configuration'],'grid':report['grid']},indent=2), '```',
           '', '## Receptor preparation', '', report['receptor']['hydrogen_protonation_method'],
           f"Selected chains: {', '.join(report['receptor']['chains'])}. Removed residues: {len(report['receptor']['removed_residues'])}; each is listed in {Path(report['receptor']['pdbqt']).parent.name}/manifest.json.",
           report['receptor']['missing_residues_policy'], '', '## Candidate ranking', '',
           '| Rank | Compound | Vina score (kcal/mol) |', '|---:|---|---:|']
    for row in report['ranking']: lines.append(f"| {row['rank']} | {row['compound_id']} | {row['best_score_kcal_mol']:.3f} |")
    lines += ['', '## Ligand preparation and failures', '']
    for row in report['ligands']:
        lines.append(f"- **{row['compound_id']}**: {row['status']}. " + (row.get('error','').replace('\n',' ') if row['status']=='failed' else row['preparation']['conformer_method']+'. '+row['preparation']['protonation']))
        if row['status']=='success':
            lines.extend(f"  - {w}" for w in row['preparation']['warnings'])
            lines.append(f"  - {len(row['docking']['poses'])} poses; see poses.csv and ligands/{row['compound_id']}/{row['attempt']}/docking/poses.sdf.")
    lines += ['', '## Crystallographic validation', '']
    if report.get('validation'): lines += ['```json',json.dumps(report['validation'],indent=2),'```']
    else: lines.append('Not performed for this experiment. Docking completion does not imply validation success.')
    lines += ['', '## Scientific limitations', ''] + [f'- {s}' for s in LIMITATIONS]
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
