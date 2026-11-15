"""CLI and local UI entry points."""
import argparse
import json
import os
from pathlib import Path
import sys
from docking_pipeline.config import load_config, ProteinConfig
from docking_pipeline.utils.logging import write_json, now


def progress(done, total, compound, status):
    print(f'[{done}/{total}] {compound}: {status}',flush=True)


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog='dockpipe',description='Reproducible real CPU AutoDock Vina docking')
    sub=parser.add_subparsers(dest='command',required=True)
    check=sub.add_parser('check'); check.add_argument('--vina',default=os.environ.get('VINA_EXECUTABLE','vina'))
    fetch=sub.add_parser('fetch'); fetch.add_argument('--id',required=True); fetch.add_argument('--output',type=Path,default=Path('data/proteins'))
    receptor=sub.add_parser('prepare-receptor'); receptor.add_argument('--input',type=Path,required=True); receptor.add_argument('--chains',nargs='+',required=True)
    receptor.add_argument('--reference'); receptor.add_argument('--remove-residues',nargs='*',default=[]); receptor.add_argument('--altloc')
    receptor.add_argument('--water-policy',choices=['remove','retain'],default='remove'); receptor.add_argument('--retain-heterogens',action='store_true')
    receptor.add_argument('--output',type=Path,required=True)
    ligand=sub.add_parser('prepare-ligands'); ligand.add_argument('--input',type=Path,required=True); ligand.add_argument('--output',type=Path,required=True)
    ligand.add_argument('--seed',type=int,default=17); ligand.add_argument('--preserve-coordinates',action='store_true')
    run=sub.add_parser('run'); run.add_argument('--config',type=Path,required=True); run.add_argument('--resume',action='store_true'); run.add_argument('--retry-failed',action='store_true')
    benchmark=sub.add_parser('benchmark'); benchmark.add_argument('--id',choices=['1iep','1IEP'],default='1iep')
    benchmark.add_argument('--data',type=Path,default=Path('data/benchmarks/1iep')); benchmark.add_argument('--output',type=Path,default=Path('results'))
    benchmark.add_argument('--job',default='1iep-redocking'); benchmark.add_argument('--vina',default=os.environ.get('VINA_EXECUTABLE','vina'))
    benchmark.add_argument('--exhaustiveness',type=int,default=32); benchmark.add_argument('--cpu',type=int,default=2)
    benchmark.add_argument('--seed',type=int,default=20261113); benchmark.add_argument('--resume',action='store_true')
    report=sub.add_parser('report'); report.add_argument('--job',type=Path,required=True)
    status=sub.add_parser('status'); status.add_argument('--job',type=Path,required=True)
    ui=sub.add_parser('ui'); ui.add_argument('--port',type=int,default=8501)
    args=parser.parse_args(argv)
    try:
        if args.command=='check':
            from docking_pipeline.utils.dependencies import check_environment
            result=check_environment(args.vina); print(json.dumps(result,indent=2)); return 0 if result['ready'] else 2
        if args.command=='fetch':
            from docking_pipeline.protein.loader import fetch_structure
            print(fetch_structure(args.id,args.output)); return 0
        if args.command=='prepare-receptor':
            from docking_pipeline.protein.preparation import prepare_receptor
            cfg=ProteinConfig(input=args.input,chains=args.chains,reference_residue=args.reference,remove_residues=args.remove_residues,
                              water_policy=args.water_policy,heterogen_policy='retain' if args.retain_heterogens else 'error',altloc=args.altloc)
            result=prepare_receptor(cfg,args.output); print(result['pdbqt']); return 0
        if args.command=='prepare-ligands':
            from docking_pipeline.ligand.loader import load_ligands
            from docking_pipeline.ligand.preparation import prepare_ligand
            rows=load_ligands(args.input); args.output.mkdir(parents=True,exist_ok=False); results=[]
            for row in rows:
                try: results.append({'status':'success',**prepare_ligand(row,args.output/row.compound_id,args.seed,args.preserve_coordinates)})
                except Exception as exc: results.append({'compound_id':row.compound_id,'status':'failed','error':str(exc)})
                progress(len(results),len(rows),row.compound_id,results[-1]['status'])
            write_json(args.output/'preparation.json',results); return 0 if all(r['status']=='success' for r in results) else 2
        if args.command=='run':
            from docking_pipeline.orchestrator import run_experiment
            cfg=load_config(args.config)
            result=run_experiment(cfg,args.resume,progress,args.retry_failed)
            print(f"{result['status']}: {cfg.output_dir/cfg.experiment_id/'report.md'}")
            return 0 if result['status']=='completed' else 2
        if args.command=='benchmark':
            from docking_pipeline.benchmark import run_benchmark
            result=run_benchmark(args.data,args.output,args.vina,args.job,args.exhaustiveness,args.cpu,args.seed,args.resume,progress)
            print(json.dumps(result['validation'],indent=2)); return 0 if result['validation']['status']=='passed' else 3
        if args.command=='report':
            from docking_pipeline.reporting.report_generator import generate_report
            root=args.job if args.job.is_dir() else Path('results')/args.job
            result=json.loads((root/'report.json').read_text()); generate_report(result,root); print(root/'report.md'); return 0
        if args.command=='status':
            from docking_pipeline.experiment_status import read_experiment
            root=args.job if args.job.is_dir() else Path('results')/args.job
            if not root.is_dir(): raise FileNotFoundError(f'Experiment not found: {args.job}')
            result=read_experiment(root); print(json.dumps(result,indent=2))
            return 1 if result['status']=='unreadable' else 0
        if args.command=='ui':
            import subprocess
            return subprocess.call([sys.executable,'-m','streamlit','run',str(Path(__file__).with_name('ui.py')),
                                    '--server.address','127.0.0.1','--server.port',str(args.port),'--server.headless','true','--browser.gatherUsageStats','false'])
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr); return 1
    return 0


if __name__=='__main__': raise SystemExit(main())
