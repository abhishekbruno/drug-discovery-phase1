"""1IEP redocking with measured crystallographic accuracy."""
from pathlib import Path
import json
import urllib.request
import gemmi
import numpy as np
from rdkit import Chem
from docking_pipeline.config import ExperimentConfig, ProteinConfig, GridConfig, DockingConfig
from docking_pipeline.protein.loader import load_structure
from docking_pipeline.analysis.rmsd import symmetry_rmsd
from docking_pipeline.orchestrator import run_experiment
from docking_pipeline.reporting.report_generator import generate_report
from docking_pipeline.utils.logging import sha256, now, write_json

TUTORIAL_COMMIT='bb64e5e26b520569a86360d69248069b5e665b3f'
SOURCES={
    '1iep.pdb':'https://files.rcsb.org/download/1IEP.pdb',
    'STI.cif':'https://files.rcsb.org/ligands/download/STI.cif',
    'tutorial_receptorH.pdb':f'https://raw.githubusercontent.com/forlilab/AutoDock-Vina/{TUTORIAL_COMMIT}/example/basic_docking/data/1iep_receptorH.pdb',
    'tutorial_ligand.sdf':f'https://raw.githubusercontent.com/forlilab/AutoDock-Vina/{TUTORIAL_COMMIT}/example/basic_docking/data/1iep_ligand.sdf'
}


def acquire_benchmark(directory: Path) -> dict:
    directory.mkdir(parents=True,exist_ok=True)
    manifest_path=directory/'sources.json'
    existing=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest={}
    for name,url in SOURCES.items():
        path=directory/name
        if not path.exists():
            with urllib.request.urlopen(url,timeout=60) as response: data=response.read(25_000_001)
            if len(data)>25_000_000: raise ValueError('Download too large')
            path.write_bytes(data)
        hashed=sha256(path)
        if name in existing and existing[name]['sha256']!=hashed: raise ValueError(f'Benchmark source integrity failed: {name}')
        manifest[name]=existing.get(name,{'url':url,'retrieved_or_verified_at':now(),'sha256':hashed})
    write_json(manifest_path,manifest)
    return manifest


def extract_reference(pdb: Path, ccd: Path, output: Path) -> Path:
    """Create the STI graph from CCD bonds and map experimental atoms by CCD name."""
    structure=load_structure(pdb)
    residues=[r for c in structure[0] if c.name=='A' for r in c if str(r.seqid)=='201' and r.name=='STI']
    if len(residues)!=1: raise ValueError('Expected unique A:201:STI reference')
    coordinates={a.name:a.pos for a in residues[0] if a.element.name!='H'}
    block=gemmi.cif.read_file(str(ccd)).sole_block()
    atoms=block.find(['_chem_comp_atom.atom_id','_chem_comp_atom.type_symbol','_chem_comp_atom.charge'])
    molecule=Chem.RWMol(); mapping={}
    for row in atoms:
        name,element,charge=[str(v).strip('"') for v in row]
        if element=='H': continue
        if name not in coordinates: raise ValueError(f'Missing crystallographic ligand atom: {name}')
        atom=Chem.Atom(element); atom.SetFormalCharge(int(charge)); atom.SetProp('ccd_atom_name',name)
        mapping[name]=molecule.AddAtom(atom)
    if set(mapping)!=set(coordinates): raise ValueError('CCD/experimental ligand atom mismatch')
    orders={'SING':Chem.BondType.SINGLE,'DOUB':Chem.BondType.DOUBLE,'TRIP':Chem.BondType.TRIPLE,'AROM':Chem.BondType.AROMATIC}
    for row in block.find(['_chem_comp_bond.atom_id_1','_chem_comp_bond.atom_id_2','_chem_comp_bond.value_order']):
        a,b,order=[str(v).strip('"') for v in row]
        if a in mapping and b in mapping: molecule.AddBond(mapping[a],mapping[b],orders[order])
    mol=molecule.GetMol(); Chem.SanitizeMol(mol)
    conformer=Chem.Conformer(mol.GetNumAtoms()); conformer.Set3D(True)
    for name,idx in mapping.items():
        pos=coordinates[name]; conformer.SetAtomPosition(idx,(pos.x,pos.y,pos.z))
    mol.AddConformer(conformer)
    Chem.AssignStereochemistryFrom3D(mol)
    mol.SetProp('_Name','imatinib')
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        old=Chem.SDMolSupplier(str(output),removeHs=False)[0]
        if old is None or symmetry_rmsd(mol,old)>1e-6: raise ValueError('Existing reference differs; use new benchmark directory')
        return output
    with Chem.SDWriter(str(output)) as writer: writer.write(mol)
    return output


def validate_redocking(report: dict, reference: Path, threshold: float = 2.0) -> dict:
    ref=Chem.SDMolSupplier(str(reference),removeHs=False)[0]
    successful=[row for row in report['ligands'] if row['status']=='success']
    if not successful: return {'status':'failed','reason':'No successful reference docking','threshold_angstrom':threshold}
    row=successful[0]
    poses=list(Chem.SDMolSupplier(row['docking']['sdf'],removeHs=False))
    measurements=[{'pose_number':i+1,'heavy_atom_rmsd_angstrom':symmetry_rmsd(ref,mol),
                   'score_kcal_mol':row['docking']['poses'][i]['score_kcal_mol']} for i,mol in enumerate(poses)]
    top=min(measurements,key=lambda p:p['score_kcal_mol'])
    best=min(measurements,key=lambda p:p['heavy_atom_rmsd_angstrom'])
    return {'status':'passed' if top['heavy_atom_rmsd_angstrom']<=threshold else 'failed',
            'criterion':'Top-scoring pose symmetry-aware heavy atom RMSD <= threshold in the original receptor frame; no superposition',
            'threshold_angstrom':threshold,'top_scoring_pose':top,'lowest_rmsd_pose':best,'poses':measurements,
            'reference':'PDB 1IEP chain A residue STI 201; CCD bond orders, original experimental coordinates',
            'reference_sha256':sha256(reference), 'method':'All chirality-aware identical-graph mappings; minimum in-place heavy atom RMSD',
            'caveat':'Passing one redocking case is not general validation of affinity ranking or prospective screening.'}


def run_benchmark(data: Path, output: Path, executable: str, experiment_id: str='1iep-redocking',
                  exhaustiveness: int=32, cpu: int=2, seed: int=20261113, resume: bool=False, progress=None) -> dict:
    acquire_benchmark(data)
    reference=extract_reference(data/'1iep.pdb',data/'STI.cif',data/'reference.sdf')
    config=ExperimentConfig(experiment_id=experiment_id,
        protein=ProteinConfig(input=(data/'1iep.pdb').resolve(),chains=['A'],reference_residue='A:201:STI',
                              remove_residues=['A:1:CL','A:2:CL','A:4:CL','A:5:CL']),
        ligands=reference.resolve(),output_dir=output.resolve(),preserve_sdf_coordinates=False,
        grid=GridConfig(mode='manual',center=(15.190,53.903,16.917),size=(20,20,20)),
        docking=DockingConfig(executable=executable,cpu=cpu,exhaustiveness=exhaustiveness,num_modes=9,seed=seed))
    # Official tutorial box; prove it actually encloses this experimental ligand.
    mol=Chem.SDMolSupplier(str(reference))[0]
    if np.any(np.abs(mol.GetConformer().GetPositions()-np.array(config.grid.center))>np.array(config.grid.size)/2):
        raise ValueError('Tutorial box does not enclose crystal reference')
    report=run_experiment(config,resume=resume,progress=progress)
    validation=validate_redocking(report,reference)
    validation['protocol']='Official Vina tutorial box; raw 1IEP chain A prepared strictly with Meeko; chloride and water removal recorded; de novo ETKDG ligand conformer'
    report['validation']=validation
    root=output/experiment_id
    write_json(root/'validation.json',validation)
    state=json.loads((root/'experiment.json').read_text())
    state['validation_sha256']=sha256(root/'validation.json')
    write_json(root/'experiment.json',state)
    generate_report(report,root)
    return report
