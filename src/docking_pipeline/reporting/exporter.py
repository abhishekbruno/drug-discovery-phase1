from pathlib import Path
import pandas as pd
from docking_pipeline.utils.logging import write_json


def export_results(report: dict, output: Path) -> None:
    write_json(output/'report.json',report)
    pd.DataFrame(report['ranking'], columns=['rank','compound_id','best_score_kcal_mol','scoring_function','molecular_weight','logp','hbond_donors','hbond_acceptors','rotatable_bonds','tpsa']).to_csv(output/'ranking.csv',index=False)
    statuses = [{'compound_id':r['compound_id'],'docking_run_id':r['docking_run_id'],'status':r['status'],'error':r.get('error','')} for r in report['ligands']]
    pd.DataFrame(statuses).to_csv(output/'status.csv', index=False)
    poses = [{'compound_id':r['compound_id'],'docking_run_id':r['docking_run_id'],**p,
              'pdbqt':r['docking']['pdbqt'],'sdf':r['docking']['sdf']} for r in report['ligands'] if r['status']=='success' for p in r['docking']['poses']]
    pd.DataFrame(poses,columns=['compound_id','docking_run_id','pose_number','score_kcal_mol','vina_rmsd_lower_angstrom','vina_rmsd_upper_angstrom','pdbqt','sdf']).to_csv(output/'poses.csv',index=False)
