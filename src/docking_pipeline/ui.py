"""Local researcher frontend for the same scientific engine used by dockpipe."""
from datetime import datetime
from pathlib import Path
import json
import os
import uuid
import pandas as pd
import streamlit as st
from docking_pipeline.config import ExperimentConfig, ProteinConfig, GridConfig, DockingConfig, safe_id
from docking_pipeline.utils.logging import write_json
from docking_pipeline.ui_jobs import JobManager
from docking_pipeline.experiment_status import read_experiment, list_experiments

PROJECT=Path(__file__).resolve().parents[2]
RESULTS=Path(os.environ.get('DOCKPIPE_RESULTS',str(PROJECT/'results'))).resolve()
DATA=PROJECT/'data/benchmarks/1iep'
LOCAL_VINA=PROJECT/'tools'/('vina.exe' if os.name=='nt' else 'vina')
VINA=os.environ.get('VINA_EXECUTABLE',str(LOCAL_VINA) if LOCAL_VINA.exists() else 'vina')

st.set_page_config(page_title='Dockpipe | Molecular docking',page_icon='⚗',layout='wide')
st.markdown('''<style>
:root { --ink:#183f32; --line:#d9e2da; }
.stApp { background:#f7f8f4; color:var(--ink); }
[data-testid="stSidebar"] { background:#e9efe7; border-right:1px solid var(--line); }
.block-container { max-width:1380px; padding-top:4rem; padding-bottom:3rem; }
h1,h2,h3 { letter-spacing:-.035em; color:#183f32; }
h1 { font-size:clamp(2rem,3vw,3rem)!important; font-weight:650!important; }
[data-testid="stMetricValue"] { color:#1b6048; font-size:2rem; }
[data-testid="stMetricLabel"] { color:#52675c; }
.eyebrow { font:600 .73rem monospace; letter-spacing:.16em; color:#577567; margin-bottom:.5rem; }
.stButton button[kind="primary"] { background:#21654c; border:1px solid #21654c; }
.stButton button, .stDownloadButton button { min-height:2.7rem; border-radius:6px; }
button:focus-visible { outline:3px solid #c39438!important; outline-offset:3px; }
[data-testid="stExpander"] { background:#fff; }
@media(max-width:700px) { .block-container { padding:1.3rem 1rem; } }
@media(prefers-reduced-motion:reduce) { * { animation:none!important; transition:none!important; } }
</style>''',unsafe_allow_html=True)


@st.cache_resource
def manager(): return JobManager()


@st.cache_data(ttl=120)
def readiness(executable):
    from docking_pipeline.utils.dependencies import check_environment
    return check_environment(executable)


def heading(kicker,title,description):
    st.markdown(f'<div class="eyebrow">{kicker}</div>',unsafe_allow_html=True)
    st.title(title); st.write(description)


@st.fragment(run_every=3)
def monitor():
    job=manager().snapshot()
    if not job: return
    code=job['returncode']
    if code is None: st.info(f"Running · {job['label']} — calculations continue while you explore the workspace.")
    elif code==0: st.success(f"Finished · {job['label']}. Open Experiments to inspect the results.")
    elif code==3: st.warning(f"Benchmark finished but did not meet the RMSD criterion. Inspect its measured validation result.")
    else: st.warning(f"Job finished with failures (exit {code}) · {job['label']}. Details are preserved below.")
    with st.expander('Execution log',expanded=code not in (None,0)):
        path=Path(job['log'])
        st.code(path.read_text(encoding='utf-8',errors='replace')[-12000:] if path.exists() else 'Starting…',language=None)
        if code is None:
            # Vina writes the numerical progress to its own per-ligand log.
            logs=sorted((RESULTS/job['label']).glob('ligands/*/attempt-*/docking/vina.log'),key=lambda p:p.stat().st_mtime)
            if logs: st.code(logs[-1].read_text(encoding='utf-8',errors='replace')[-3000:],language=None)


def show_report(root: Path):
    report=json.loads((root/'report.json').read_text(encoding='utf-8'))
    ranks=report['ranking']; successes=sum(r['status']=='success' for r in report['ligands'])
    a,b,c,d=st.columns(4)
    a.metric('Molecules tested',len(report['ligands'])); b.metric('Results available',successes)
    c.metric('Best Vina score',f"{ranks[0]['best_score_kcal_mol']:.2f}" if ranks else '—',help='Computed docking score in kcal/mol')
    validation=report.get('validation',{})
    d.metric('Reference RMSD',f"{validation['top_scoring_pose']['heavy_atom_rmsd_angstrom']:.2f} Å" if validation.get('top_scoring_pose') else 'Not measured',help='Distance from an experimentally observed molecular position. Lower is closer. Å means ångström, a unit of atomic-scale distance. This is measured only when a reference comparison is available.')
    st.caption(f"{report['experiment_id']} · {report['status']} · Vina · kcal/mol · started {report['started_at']}")
    if validation:
        (st.success if validation['status']=='passed' else st.warning)(f"Redocking validation: {validation['status']} · top-scoring pose criterion ≤ {validation['threshold_angstrom']:.1f} Å")
    st.info('How to read this result: the computer predicts how each small molecule may fit into the protein. A lower (more negative) score ranks better in this run. It does not prove that a molecule works as a medicine.')
    rank_tab,pose_tab,method_tab,files_tab=st.tabs(['Compare molecules','View 3D fit','Technical details','Download results'])
    with rank_tab:
        st.subheader('Which molecules scored best?')
        st.caption('More negative Vina scores are generally more favorable within this experiment. They are not measured binding affinities.')
        if ranks:
            table=pd.DataFrame(ranks)
            st.dataframe(table[['rank','compound_id','best_score_kcal_mol']].rename(columns={
                'rank':'Rank','compound_id':'Molecule','best_score_kcal_mol':'Predicted score (kcal/mol)'}),hide_index=True,width='stretch')
            with st.expander('More molecular properties (advanced)'):
                st.caption('These describe molecular size and chemistry; they are not measures of treatment effectiveness.')
                st.dataframe(table,hide_index=True,width='stretch')
        else: st.warning('No successful docking calculations to rank.')
        failed=[{'compound':r['compound_id'],'error':r.get('error','')} for r in report['ligands'] if r['status']=='failed']
        if failed:
            st.subheader('Calculations needing attention'); st.dataframe(pd.DataFrame(failed),hide_index=True,width='stretch')
    with pose_tab:
        successful=[r for r in report['ligands'] if r['status']=='success']
        if not successful: st.info('A successful docking calculation is needed to display poses.')
        else:
            left,right=st.columns([1,3])
            with left:
                compound=st.selectbox('Compound',[r['compound_id'] for r in successful])
                row=next(r for r in successful if r['compound_id']==compound)
                index=st.selectbox('Pose',list(range(len(row['docking']['poses']))),format_func=lambda i:f"Pose {i+1} · {row['docking']['poses'][i]['score_kcal_mol']:.2f} kcal/mol")
                st.write('Rotate by dragging. Scroll to zoom.')
                overlay=st.checkbox('Show crystal reference',value=True)
                backbone=st.checkbox('Show receptor backbone',value=True)
                st.caption('Green: carbon · blue: nitrogen · red: oxygen · gold: crystal reference. Coordinates stay in the receptor frame.')
                with st.expander('Pose measurements (advanced)'):
                    st.json(row['docking']['poses'][index])
            with right:
                from docking_pipeline.ui_viewer import pose_figure
                reference=report['receptor'].get('reference_pdb')
                try: st.plotly_chart(pose_figure(Path(row['docking']['sdf']),index,
                    Path(report['receptor']['selected_pdb']) if backbone else None,Path(reference) if overlay and reference else None),use_container_width=True)
                except Exception as exc: st.error(f'Pose file could not be displayed: {exc}')
            st.caption('Vina RMSD bounds above are relative to the best docked pose. Reference RMSD is reported separately under Method & validation.')
    with method_tab:
        st.subheader('Reproducible setup'); st.json({'grid':report['grid'],'docking':report['configuration']['docking']},expanded=True)
        st.write(report['receptor']['hydrogen_protonation_method'])
        with st.expander('Receptor selection and removed components'): st.json(report['receptor']['removed_residues'])
        with st.expander('Software versions'): st.json(report['environment'])
        if validation: st.json(validation)
        else: st.info('No crystallographic validation was performed for this experiment.')
        for text in report['limitations']: st.write('• '+text)
    with files_tab:
        st.subheader('Save your results')
        st.caption('Start with the readable report or ranking spreadsheet. JSON, SDF and PDBQT files are for further analysis in scientific software.')
        download_labels={'report.md':'Readable report (.md)','report.json':'Full data (.json)',
                         'ranking.csv':'Molecule rankings (.csv)','poses.csv':'3D fit measurements (.csv)','status.csv':'Processing status (.csv)'}
        for name,mime in [('report.md','text/markdown'),('report.json','application/json'),('ranking.csv','text/csv'),('poses.csv','text/csv'),('status.csv','text/csv')]:
            path=root/name
            if path.exists(): st.download_button(download_labels[name],path.read_bytes(),file_name=f'{root.name}-{name}',mime=mime,key=f'dl-{root.name}-{name}')
        for row in report['ligands']:
            if row['status']=='success':
                for kind in ['sdf','pdbqt']:
                    path=Path(row['docking'][kind])
                    if path.exists(): st.download_button(f"{row['compound_id']} · poses.{kind}",path.read_bytes(),file_name=f"{row['compound_id']}-poses.{kind}",key=f"pose-{root.name}-{row['compound_id']}-{kind}")
        st.caption(f'All inputs, manifests, logs and molecular files are stored in {root}')


STATUS_LABELS = {'running':'Recorded as running', 'interrupted':'Interrupted', 'failed':'Failed',
    'completed':'Completed', 'completed_with_failures':'Finished — some molecules need attention',
    'not_started':'Not started', 'unknown':'State unavailable', 'unreadable':'Metadata needs attention'}
ATTENTION = {'interrupted', 'failed', 'completed_with_failures', 'unreadable', 'unknown'}


@st.fragment(run_every=3)
def experiment_activity(root: Path):
    row=read_experiment(root)
    job=manager().snapshot()
    busy=bool(job and job['returncode'] is None)
    owned=busy and job['label']==root.name
    with st.container(border=True):
        st.caption('EXPERIMENT ACTIVITY · refreshes every 3 seconds')
        st.subheader('Running' if owned else STATUS_LABELS[row['status']])
        stage={'preparing_receptor':'Step 1 of 3 · Preparing the protein structure',
               'docking':'Step 2 of 3 · Preparing molecules and predicting their fit',
               'reporting':'Step 3 of 3 · Saving results', 'finished':'Processing finished · Review available results below'}.get(row['stage'])
        if stage: st.write(stage)
        if row['updated_at']: st.caption(f"Last saved update · {row['updated_at']}")
        if row['status']=='running' and not owned:
            st.warning('This is the last saved running state. The calculation may still be active in another process. If it has stopped, resume below; the backend prevents simultaneous runs of the same experiment.')
        if row['error']: st.warning(row['error'])
        if row['warning']: st.error(row['warning'])
        progress=row['progress']
        if progress:
            a,b,c=st.columns(3)
            a.metric('Compounds processed',f"{progress['completed']} / {progress['total']}")
            b.metric('Results available',progress['succeeded']); c.metric('Need attention',progress['failed'])
            st.progress(progress['completed']/progress['total'] if progress['total'] else 0.0,
                        text='Completed compounds · not an estimate of docking time')
        else:
            st.caption('Progress counts are unavailable for this saved run. Existing reports and logs remain accessible.')
        if row['has_report'] and st.button('Open latest report',key=f'open-report-{root.name}'):
            st.rerun()
        if (root/'config.resolved.json').is_file():
            with st.expander('Resume or retry this experiment',expanded=row['status'] in ATTENTION):
                st.caption('Continue where this run stopped. Completed molecules are kept. Select the checkbox below to also try molecules that previously failed; earlier files are preserved.')
                retry=st.checkbox('Retry failed ligands in new attempt folders',key=f'retry-{root.name}')
                if st.button('Resume saved experiment',key=f'resume-{root.name}',disabled=busy or not row['can_resume']):
                    try:
                        args=['run','--config',str(root/'config.resolved.json'),'--resume']
                        if retry: args.append('--retry-failed')
                        manager().launch(args,RESULTS/'_logs'/f'{uuid.uuid4().hex}.log',root.name); st.rerun()
                    except Exception as exc: st.error(str(exc))
                if busy: st.caption('Wait for the current UI calculation to finish before launching another.')


def experiments():
    heading('YOUR WORKSPACE','Explore how molecules fit','Molecular docking predicts how a small molecule may fit into a protein. Start a calculation, follow its progress, and compare the predicted results here.')
    rows=list_experiments(RESULTS)
    with st.expander('New here? Start with these 3 steps',expanded=not rows):
        st.markdown('**1. Set up a run** — Choose **New experiment** in the sidebar. The included example has a protein and two molecules ready to try.\n\n**2. Follow progress** — Return to **Experiments** to see how many molecules have finished. Calculations can take several minutes.\n\n**3. Explore results** — Compare scores, view the predicted 3D fit, or download a report. A prediction is a starting point for research, not a laboratory result.')
    monitor()
    if not rows:
        st.info('No experiments have been saved yet. Create a new experiment or run the 1IEP benchmark.')
        st.write('Every score and pose shown here comes from an actual AutoDock Vina calculation.')
        return
    a,b,c=st.columns(3)
    a.metric('Saved experiments',len(rows))
    b.metric('Reports available',sum(r['has_report'] for r in rows))
    c.metric('Need attention',sum(r['status'] in ATTENTION for r in rows))
    search,filters=st.columns([2,1])
    query=search.text_input('Search experiments',placeholder='Experiment identifier').strip().casefold()
    selected_filter=filters.selectbox('Status filter',['All experiments','Needs attention','Completed','Running or interrupted'])
    filtered=[r for r in rows if query in r['id'].casefold()
        and (selected_filter=='All experiments'
             or selected_filter=='Needs attention' and r['status'] in ATTENTION
             or selected_filter=='Completed' and r['status']=='completed'
             or selected_filter=='Running or interrupted' and r['status'] in ('running','interrupted'))]
    if not filtered:
        st.info('No experiments match these filters. Clear the search or choose All experiments.')
        return
    selected=st.selectbox('Experiment',[r['id'] for r in filtered])
    root=RESULTS/selected
    experiment_activity(root)
    if (root/'report.json').is_file():
        st.divider()
        st.caption('LAST SAVED REPORT · current activity and progress appear above')
        try: show_report(root)
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            st.error(f'The saved report could not be displayed: {exc}. Inspect the experiment files or select another experiment.')
    else:
        st.info('Use Open latest report above when processing finishes. Live progress and recovery controls remain available.')


def new_experiment():
    heading('NEW EXPERIMENT','Set up your first prediction','Choose a protein (the target) and small molecules (called ligands). The computer will try different ways each molecule could fit inside the selected part of the protein.')
    st.info('First time? Keep the bundled example selected and leave the settings below unchanged, then choose Start docking. This example compares ethanol and acetanilide; it is a practice run, not the validation benchmark.')
    monitor()
    bundled=st.checkbox('Use bundled 1IEP example',value=True)
    protein_file=ligand_file=None
    if not bundled:
        x,y=st.columns(2)
        protein_file=x.file_uploader('Protein structure',type=['pdb','cif','mmcif'])
        ligand_file=y.file_uploader('Ligand library (optional with SMILES below)',type=['sdf','csv','smi','smiles','txt'])
        if not protein_file: st.info('Upload a PDB or mmCIF protein structure to start.')
    a,b=st.columns([3,2],gap='large')
    with a:
        st.subheader('1. Choose your protein and molecules')
        st.session_state.setdefault('new_job_id','docking-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        identifier=st.text_input('Experiment identifier',key='new_job_id',help='A unique name for finding this run later. Use letters, numbers, hyphens or underscores.')
        chains=st.text_input('Receptor chains (comma separated)',value='A',help='Which protein chains to include. A chain is a labeled part of the protein structure. Keep A for the bundled example.')
        smiles=st.text_area('SMILES library',value='CCO ethanol\nCC(=O)Nc1ccccc1 acetanilide',help='SMILES is a text representation of a molecule. Enter one SMILES followed by a unique molecule name per line. An uploaded library replaces this text.')
        st.caption('For example, CCO ethanol means: test the molecule written as CCO and label it ethanol.')
        reference=st.text_input('Reference residue (chain:number:name)',value='A:201:STI' if bundled else '',help='Identifies a molecule already in the structure to locate the search area. It is removed from the protein before docking and saved separately. Keep A:201:STI for the bundled example.')
        removals=st.text_input('Explicitly remove other residues (comma separated)',value='A:1:CL,A:2:CL,A:4:CL,A:5:CL' if bundled else '')
        st.caption('Review cofactors and ions before removing them. The bundled benchmark lists four chloride ions explicitly.')
        if bundled:
            with st.expander('Inspect bundled protein components'):
                from docking_pipeline.protein.loader import load_structure
                from docking_pipeline.protein.validator import inspect_structure
                inventory=inspect_structure(load_structure(DATA/'1iep.pdb'))
                st.dataframe(pd.DataFrame([h for h in inventory['heterogens'] if not h['water']]),hide_index=True,width='stretch')
        with st.expander('Preparation policies'):
            water=st.selectbox('Water handling',['remove','retain'])
            heterogen=st.selectbox('Unlisted cofactors and ions',['error','retain'],help='Error requires an explicit decision before preparation.')
            altloc=st.text_input('Alternate location label (blank rejects ambiguity)',max_chars=1)
            preserve=st.checkbox('Preserve uploaded SDF coordinates',value=False)
            st.caption('Default: regenerate a 3D conformer with ETKDGv3 and optimize with MMFF94/UFF. Input charges, tautomer and specified stereochemistry are preserved; no pH calculation.')
    with b:
        st.subheader('2. Choose where to look')
        st.caption('The search box is the area of the protein to explore. Reference ligand uses the location of a molecule already present in the structure.')
        grid_method=st.radio('Grid method',['Reference ligand','Manual coordinates'])
        if grid_method=='Reference ligand':
            padding=st.number_input('Padding around reference (Å)',2.0,15.0,5.0,.5)
            grid=GridConfig(mode='reference',padding=padding)
        else:
            st.caption('Coordinates and dimensions are in Ångströms.')
            centers=st.columns(3); sizes=st.columns(3)
            center=[centers[i].number_input(f'Center {axis}',value=value,format='%.3f') for i,(axis,value) in enumerate(zip('XYZ',[15.190,53.903,16.917]))]
            size=[sizes[i].number_input(f'Size {axis}',1.0,50.0,20.0) for i,axis in enumerate('XYZ')]
            grid=None
        st.subheader('3. Set the search effort')
        exhaustiveness=st.select_slider('Exhaustiveness',options=[1,4,8,16,32,64,128],value=8,help='How thoroughly the computer searches. Higher values usually take longer; they do not guarantee a better prediction.')
        st.caption('The defaults are a useful starting point. A pose is one predicted 3D arrangement of a molecule.')
        modes=st.number_input('Maximum poses',1,50,9)
        budget=min(8,os.cpu_count() or 1)
        cpu=st.number_input('CPU threads per ligand',1,budget,min(2,budget))
        workers=st.number_input('Parallel ligands',1,4,1)
        seed=st.number_input('Random seed',1,2147483647,20261113)
        st.caption(f'CPU execution · maximum combined budget {budget} threads · sequential default')
    st.divider()
    st.caption('Docking scores are predictions. They do not establish biological efficacy, safety, or measured affinity.')
    if st.button('Start docking',type='primary',width='stretch'):
        try:
            safe_id(identifier)
            if not bundled and not protein_file: raise ValueError('Upload a protein structure first.')
            if (RESULTS/identifier).exists(): raise ValueError('That experiment already exists. Choose a new identifier or resume it.')
            if manager().snapshot() and manager().snapshot()['returncode'] is None: raise ValueError('A calculation is already running.')
            inputs=RESULTS/'_uploads'/uuid.uuid4().hex; inputs.mkdir(parents=True)
            if bundled: protein_path=DATA/'1iep.pdb'
            else:
                protein_path=inputs/('protein'+Path(protein_file.name).suffix.lower()); protein_path.write_bytes(protein_file.getvalue())
            ligand_path=inputs/('ligands'+Path(ligand_file.name).suffix.lower() if ligand_file else 'ligands.smi')
            ligand_path.write_bytes(ligand_file.getvalue() if ligand_file else smiles.encode('utf-8'))
            if grid is None: grid=GridConfig(mode='manual',center=center,size=size)
            cfg=ExperimentConfig(experiment_id=identifier,protein=ProteinConfig(input=protein_path.resolve(),
                chains=[v.strip() for v in chains.split(',') if v.strip()],reference_residue=reference.strip() or None,
                remove_residues=[v.strip() for v in removals.split(',') if v.strip()],water_policy=water,heterogen_policy=heterogen,altloc=altloc or None),
                ligands=ligand_path.resolve(),output_dir=RESULTS,grid=grid,preserve_sdf_coordinates=preserve,
                docking=DockingConfig(executable=VINA,cpu=cpu,workers=workers,seed=seed,exhaustiveness=exhaustiveness,num_modes=modes))
            path=inputs/'config.json'; write_json(path,cfg.model_dump(mode='json'))
            manager().launch(['run','--config',str(path)],RESULTS/'_logs'/f'{uuid.uuid4().hex}.log',identifier)
            st.success('Docking started. Open Experiments when the calculation finishes.'); st.rerun()
        except Exception as exc: st.error(str(exc))


def benchmark():
    heading('CHECK THE WORKFLOW','Compare a prediction with a known structure','This example checks whether the pipeline can reproduce the experimentally observed position of imatinib in the c-Abl protein (PDB 1IEP).')
    st.write('The check measures the distance between predicted and observed atom positions, called RMSD. Smaller is closer. Passing this check supports this example only; it does not validate every future prediction.')
    monitor()
    st.write('The benchmark prepares chain A, preserves the experimental STI ligand, generates a new ligand conformer, and runs real Vina docking in the official tutorial box.')
    st.info('Success is measured: top-scoring pose heavy-atom RMSD ≤ 2 Å, with symmetry-aware atom mapping and no alignment. A failed benchmark remains a reported result.')
    st.session_state.setdefault('benchmark_job_id','1iep-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    job=st.text_input('Benchmark identifier',key='benchmark_job_id')
    effort=st.select_slider('Benchmark exhaustiveness',options=[8,16,32,64],value=32)
    st.caption('This calculation may take several minutes. CPU only; no GPU or cloud service is required.')
    if st.button('Run 1IEP benchmark',type='primary'):
        try:
            safe_id(job)
            manager().launch(['benchmark','--id','1iep','--data',str(DATA),'--output',str(RESULTS),'--vina',VINA,
                '--job',job,'--exhaustiveness',str(effort)],RESULTS/'_logs'/f'{uuid.uuid4().hex}.log',job); st.rerun()
        except Exception as exc: st.error(str(exc))


with st.sidebar:
    st.markdown('## ◌ Dockpipe')
    st.caption('MOLECULAR RESEARCH / PHASE 1')
    st.caption('Experiments: view progress and results\n\nNew experiment: start a prediction\n\nBenchmark: check a known example\n\nEnvironment: check installed tools')
    page=st.radio('Workspace',['Experiments','New experiment','Benchmark','Environment'],label_visibility='collapsed')
    st.divider(); st.caption('Local workspace'); st.code(str(PROJECT),language=None)
    st.caption('CPU AutoDock Vina 1.2.7\n\nRDKit · Meeko · reproducible outputs')
    if st.button('Refresh results'): st.rerun()

if page=='Experiments': experiments()
elif page=='New experiment': new_experiment()
elif page=='Benchmark': benchmark()
else:
    heading('ENVIRONMENT','Scientific toolchain','Verify actual package versions and the installed Vina executable before starting a calculation.')
    if st.button('Recheck environment'): readiness.clear()
    state=readiness(VINA)
    (st.success if state['ready'] else st.error)('Ready for docking' if state['ready'] else 'Environment needs attention')
    for error in state['errors']: st.error(error)
    st.json(state)
