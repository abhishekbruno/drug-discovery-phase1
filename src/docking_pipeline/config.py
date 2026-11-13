"""Strict, portable experiment configuration; paths are relative to the YAML file."""
from pathlib import Path
from typing import Literal
import math
import os
import re
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


def safe_id(value: str) -> str:
    reserved = {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value) or '..' in value
            or value.endswith('.') or value.split('.')[0].upper() in reserved):
        raise ValueError(f'Unsafe identifier: {value!r}')
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class GridConfig(StrictModel):
    mode: Literal['manual', 'reference'] = 'reference'
    center: tuple[float, float, float] | None = None
    size: tuple[float, float, float] | None = None
    padding: float = Field(default=5.0, ge=2, le=15)

    @model_validator(mode='after')
    def check(self):
        if self.mode == 'manual' and (self.center is None or self.size is None):
            raise ValueError('Manual grid requires center and size')
        if self.mode == 'reference' and self.center is not None:
            raise ValueError('Reference mode derives center from reference coordinates')
        if self.size and (any(v <= 0 or v > 50 for v in self.size) or math.prod(self.size) > 64000):
            raise ValueError('Box sides must be >0 and <=50 A, volume <=64000 A^3')
        return self


class ProteinConfig(StrictModel):
    input: Path
    chains: list[str] = Field(min_length=1)
    reference_residue: str | None = None  # chain:sequence(insertion):name
    water_policy: Literal['remove', 'retain'] = 'remove'
    heterogen_policy: Literal['error', 'retain', 'remove_listed'] = 'error'
    remove_residues: list[str] = Field(default_factory=list)
    altloc: str | None = Field(default=None, min_length=1, max_length=1)
    residue_templates: dict[str, str] = Field(default_factory=dict)


class DockingConfig(StrictModel):
    executable: str = 'vina'
    scoring: Literal['vina'] = 'vina'
    seed: int = Field(default=20261113, ge=1, le=2147483647)
    cpu: int = Field(default=2, ge=1, le=8)
    workers: int = Field(default=1, ge=1, le=4)
    exhaustiveness: int = Field(default=8, ge=1, le=128)
    num_modes: int = Field(default=9, ge=1, le=50)
    energy_range: float = Field(default=4.0, gt=0, le=20)
    timeout_seconds: int = Field(default=1800, ge=1, le=86400)

    @model_validator(mode='after')
    def resources(self):
        if self.cpu * self.workers > min(8, os.cpu_count() or 1):
            raise ValueError('workers * cpu exceeds available CPU budget (maximum 8)')
        return self


class ExperimentConfig(StrictModel):
    experiment_id: str
    protein: ProteinConfig
    ligands: Path
    output_dir: Path = Path('../results')
    grid: GridConfig = Field(default_factory=GridConfig)
    docking: DockingConfig = Field(default_factory=DockingConfig)
    ligand_seed: int = Field(default=17, ge=1, le=2147483647)
    preserve_sdf_coordinates: bool = False

    _valid_id = field_validator('experiment_id')(safe_id)

    @model_validator(mode='after')
    def reference(self):
        if self.grid.mode == 'reference' and not self.protein.reference_residue:
            raise ValueError('Reference grid requires protein.reference_residue')
        return self


def load_config(path: Path) -> ExperimentConfig:
    path = path.resolve()
    cfg = ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding='utf-8')))
    cfg.protein.input = (path.parent / cfg.protein.input).resolve()
    cfg.ligands = (path.parent / cfg.ligands).resolve()
    cfg.output_dir = (path.parent / cfg.output_dir).resolve()
    exe = cfg.docking.executable
    if '/' in exe or '\\' in exe:
        cfg.docking.executable = str((path.parent / exe).resolve())
    return cfg
