"""Explicit receptor selection followed by strict Meeko residue matching."""
from pathlib import Path
import shutil
import sys
import gemmi
from Bio.PDB import parse_pdb_header
from docking_pipeline.config import ProteinConfig
from docking_pipeline.protein.loader import load_structure
from docking_pipeline.protein.validator import inspect_structure, residue_key
from docking_pipeline.ligand.preparation import validate_pdbqt
from docking_pipeline.utils.logging import write_json, sha256, run_logged


def prepare_receptor(config: ProteinConfig, output: Path) -> dict:
    structure = load_structure(config.input)
    inventory = inspect_structure(structure)
    available = {c.name for c in structure[0]}
    if not set(config.chains) <= available: raise ValueError(f'Unknown receptor chain; available: {sorted(available)}')
    if len(set(config.chains)) != len(config.chains): raise ValueError('Duplicate receptor chains')
    if any(len(c) > 1 for c in config.chains): raise ValueError('This Meeko PDB bridge supports one-character chain IDs only')
    selected = gemmi.Structure(); selected.add_model(gemmi.Model('1'))
    reference = gemmi.Structure(); reference.add_model(gemmi.Model('1'))
    removed, retained, coords = [], [], []
    seen_removals = set()
    for chain in structure[0]:
        if chain.name not in config.chains:
            removed.extend({'id': residue_key(chain.name,r), 'reason': 'chain not selected'} for r in chain)
            continue
        dest = gemmi.Chain(chain.name)
        for residue in chain:
            key = residue_key(chain.name, residue)
            if key == config.reference_residue:
                if gemmi.find_tabulated_residue(residue.name).is_amino_acid() or residue.is_water():
                    raise ValueError('Reference must be a non-protein, non-water ligand residue')
                if any(a.has_altloc() for a in residue) and config.altloc is None:
                    raise ValueError(f'Alternate locations in reference {key}; select altloc explicitly')
                chosen = gemmi.Residue(); chosen.name=residue.name; chosen.seqid=residue.seqid; chosen.het_flag=residue.het_flag
                for name in dict.fromkeys(a.name for a in residue):
                    candidates=[a for a in residue if a.name==name and (not a.has_altloc() or a.altloc==config.altloc)]
                    if len(candidates)!=1: raise ValueError(f'Reference alternate selection has missing/duplicate atom {name}')
                    atom=candidates[0].clone(); atom.altloc='\x00'; chosen.add_atom(atom)
                refchain = gemmi.Chain(chain.name); refchain.add_residue(chosen); reference[0].add_chain(refchain)
                for atom in chosen:
                    if atom.element.name != 'H': coords.append([atom.pos.x,atom.pos.y,atom.pos.z])
                removed.append({'id': key, 'reason': 'reference ligand preserved separately'}); continue
            if residue.is_water() and config.water_policy == 'remove':
                removed.append({'id':key, 'reason':'explicit water policy'}); continue
            if key in config.remove_residues:
                if gemmi.find_tabulated_residue(residue.name).is_amino_acid():
                    raise ValueError(f'Protein residue deletion is not supported: {key}; supply a reviewed structure')
                seen_removals.add(key)
                removed.append({'id':key, 'reason':'explicit remove_residues list'}); continue
            aa = gemmi.find_tabulated_residue(residue.name).is_amino_acid()
            if not aa and not residue.is_water() and config.heterogen_policy != 'retain':
                raise ValueError(f'Heterogen {key} requires retain or explicit remove_residues; review cofactors/metals')
            if any(a.has_altloc() for a in residue) and config.altloc is None:
                raise ValueError(f'Alternate locations in {key}; select altloc explicitly')
            if aa and {'N','CA','C','O'} - {a.name for a in residue}:
                raise ValueError(f'Missing backbone atoms in {key}; repair externally and document provenance')
            dest.add_residue(residue.clone()); retained.append(key)
        if len(dest): selected[0].add_chain(dest)
    if set(config.remove_residues) != seen_removals:
        raise ValueError(f'Removal identifiers not found in selected receptor: {set(config.remove_residues)-seen_removals}')
    if config.reference_residue and not coords: raise ValueError('Reference residue not found in selected chains')
    if not any(gemmi.find_tabulated_residue(r.name).is_amino_acid() for c in selected[0] for r in c):
        raise ValueError('No protein residues selected')
    output.mkdir(parents=True, exist_ok=False)
    original = output/('original' + config.input.suffix.lower()); shutil.copy2(config.input, original)
    selected_pdb = output/'selected.pdb'; selected.write_pdb(str(selected_pdb))
    reference_path = output/'reference.pdb'
    if coords: reference.write_pdb(str(reference_path))
    header = parse_pdb_header(str(config.input)) if config.input.suffix.lower()=='.pdb' else {}
    inventory['missing_residues_from_header'] = header.get('missing_residues', [])
    write_json(output/'inventory.json', inventory)
    args = [sys.executable, '-m', 'meeko.cli.mk_prepare_receptor', '--read_pdb', str(selected_pdb.resolve()),
            '-o', str((output/'receptor').resolve()), '-p', '-j', '--write_pdb', str((output/'prepared.pdb').resolve())]
    if config.altloc: args += ['--default_altloc', config.altloc]
    if config.residue_templates:
        args += ['--set_template', ','.join(f'{k}={v}' for k,v in config.residue_templates.items())]
    run_logged(args, output/'preparation.log', 300)
    qt = output/'receptor.pdbqt'; validate_pdbqt(qt, False)
    manifest = {'input_sha256': sha256(original), 'pdbqt':str(qt.resolve()), 'pdbqt_sha256':sha256(qt),
                'selected_pdb':str(selected_pdb.resolve()), 'reference_pdb':str(reference_path.resolve()) if coords else None,
                'reference_coordinates':coords, 'chains': config.chains, 'removed_residues':removed, 'retained_residues':retained,
                'policy':config.model_dump(mode='json'), 'inventory':inventory,
                'hydrogen_protonation_method':'Meeko 0.7.1 residue templates add/match hydrogens; default residue states unless residue_templates supplied. No pKa calculation, pH optimization, or missing-heavy-atom repair.',
                'missing_residues_policy':'Unresolved sequence residues are reported, not rebuilt. Existing residues must pass strict Meeko matching; no allow_bad_res.',
                'rigid_receptor':True}
    write_json(output/'manifest.json', manifest)
    return manifest
