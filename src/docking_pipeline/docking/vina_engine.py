from pathlib import Path
import shutil
from rdkit import Chem
from meeko import PDBQTMolecule, RDKitMolCreate
from docking_pipeline.config import DockingConfig, GridConfig
from docking_pipeline.ligand.preparation import validate_pdbqt
from docking_pipeline.analysis.scoring import parse_poses
from docking_pipeline.utils.logging import run_logged, write_json, sha256


def resolve_executable(value: str) -> str:
    found = shutil.which(value)
    if not found: raise FileNotFoundError(f'AutoDock Vina executable unavailable: {value}. Run dockpipe check.')
    return str(Path(found).resolve())


def dock(receptor: Path, ligand: Path, grid: dict, config: DockingConfig, output: Path) -> dict:
    GridConfig(mode='manual', center=grid['center'], size=grid['size'])
    exe = resolve_executable(config.executable)
    validate_pdbqt(receptor, False); validate_pdbqt(ligand, True)
    output.mkdir(parents=True, exist_ok=False)
    pose_file = output/'poses.pdbqt'
    args = [exe, '--receptor',str(receptor.resolve()), '--ligand',str(ligand.resolve()), '--out',str(pose_file.resolve()),
            '--scoring',config.scoring, '--cpu',str(config.cpu), '--seed',str(config.seed),
            '--exhaustiveness',str(config.exhaustiveness), '--num_modes',str(config.num_modes), '--energy_range',str(config.energy_range)]
    for dimension, center, size in zip('xyz', grid['center'], grid['size']):
        args += [f'--center_{dimension}',str(center),f'--size_{dimension}',str(size)]
    run_logged(args, output/'vina.log', config.timeout_seconds)
    validate_pdbqt(pose_file, True)
    poses = parse_poses(pose_file.read_text())
    pdbqt_molecule = PDBQTMolecule.from_file(str(pose_file), skip_typing=True)
    sdf_text, failures = RDKitMolCreate.write_sd_string(pdbqt_molecule)
    if failures or not sdf_text: raise ValueError(f'Meeko pose export failed for records {failures}')
    sdf_file = output/'poses.sdf'; sdf_file.write_text(sdf_text, encoding='utf-8')
    molecules = list(Chem.SDMolSupplier(str(sdf_file), removeHs=False))
    if len(molecules) != len(poses) or any(m is None for m in molecules): raise ValueError('Pose count/SDF integrity mismatch')
    result = {'poses':poses, 'pdbqt':str(pose_file.resolve()), 'sdf':str(sdf_file.resolve()),
              'sha256':{'pdbqt':sha256(pose_file), 'sdf':sha256(sdf_file)},
              'execution_parameters':config.model_dump(mode='json'), 'grid':grid}
    write_json(output/'result.json',result)
    return result
