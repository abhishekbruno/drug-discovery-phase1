import numpy as np
from docking_pipeline.config import GridConfig


def make_grid(config: GridConfig, coordinates: np.ndarray | None = None) -> dict:
    if config.mode == 'manual':
        return {'center': list(config.center), 'size': list(config.size), 'source': 'user-specified', 'units': 'angstrom'}
    xyz = np.asarray(coordinates, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all():
        raise ValueError('Reference coordinates must be finite N x 3')
    low, high = xyz.min(axis=0), xyz.max(axis=0)
    center = (low + high) / 2
    size = np.asarray(config.size if config.size else (high-low+2*config.padding))
    if np.any(size < high-low+0.01):
        raise ValueError('Reference box does not enclose reference ligand')
    GridConfig(mode='manual', center=tuple(center), size=tuple(size))
    return {'center': center.tolist(), 'size': size.tolist(), 'source': 'crystallographic-reference', 'units': 'angstrom', 'padding_requested': config.padding}
