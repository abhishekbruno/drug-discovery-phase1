"""Parse Vina's result REMARKS, never substitute an absent score."""
import math


def parse_poses(text: str) -> list[dict]:
    poses = []
    for line in text.splitlines():
        if line.startswith('REMARK VINA RESULT:'):
            try:
                score, lower, upper = map(float, line.split(':', 1)[1].split())
            except ValueError as exc:
                raise ValueError('Malformed Vina result') from exc
            if not all(map(math.isfinite, (score, lower, upper))) or lower < 0 or upper < lower:
                raise ValueError('Invalid Vina energy/RMSD')
            poses.append({'pose_number': len(poses)+1, 'score_kcal_mol': score,
                          'vina_rmsd_lower_angstrom': lower, 'vina_rmsd_upper_angstrom': upper})
    if not poses:
        raise ValueError('No Vina result records found')
    return poses
