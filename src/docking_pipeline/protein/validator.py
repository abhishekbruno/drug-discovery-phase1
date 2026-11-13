import gemmi


def residue_key(chain: str, residue: gemmi.Residue) -> str:
    return f'{chain}:{residue.seqid}:{residue.name}'


def inspect_structure(structure: gemmi.Structure) -> dict:
    chains, heterogens, alternates, incomplete, gaps = {}, [], [], [], []
    count = 0
    for chain in structure[0]:
        chains[chain.name] = []
        last = None
        for res in chain:
            key = residue_key(chain.name, res)
            names = {a.name for a in res}
            count += len(res)
            aa = gemmi.find_tabulated_residue(res.name).is_amino_acid()
            chains[chain.name].append({'id': key, 'name': res.name, 'atoms': len(res), 'protein': aa})
            if aa:
                missing = sorted({'N','CA','C','O'} - names)
                if missing: incomplete.append({'id': key, 'missing_backbone_atoms': missing})
                if last is not None and res.seqid.num > last+1: gaps.append({'chain': chain.name, 'after': last, 'before': res.seqid.num})
                last = res.seqid.num
            else:
                heterogens.append({'id': key, 'name': res.name, 'water': res.is_water(),
                                   'elements': sorted({a.element.name for a in res}), 'atoms': len(res)})
            if any(a.has_altloc() for a in res): alternates.append({'id': key, 'labels': sorted({a.altloc for a in res if a.has_altloc()})})
    return {'name': structure.name, 'resolution_angstrom': structure.resolution or None,
            'experimental_metadata': dict(structure.info), 'chains': chains, 'heterogens': heterogens,
            'atom_count': count, 'alternate_locations': alternates, 'incomplete_backbones': incomplete,
            'sequence_number_gaps': gaps,
            'missing_atom_check': 'Backbone preflight; full residue-template matching by Meeko at preparation. Numbering gaps are indicators, not a sequence reconstruction.'}
