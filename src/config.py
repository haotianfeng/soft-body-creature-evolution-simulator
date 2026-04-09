from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SimulationConfig:
    width: int = 1280
    height: int = 720
    gravity_x: float = 0.0
    gravity_y: float = 980.0
    ground_y: float = 620.0
    ground_friction: float = 1.8
    mass_radius: float = 14.0
    mass_value: float = 1.0
    point_friction: float = 2.4
    spring_stiffness: float = 240.0
    spring_damping: float = 12.0
    physics_dt: float = 1.0 / 240.0
    render_fps: int = 60
    background_color: tuple[int, int, int] = (18, 22, 30)
    ground_color: tuple[int, int, int] = (120, 125, 138)
    body_fill: tuple[int, int, int] = (244, 234, 213)
    body_outline: tuple[int, int, int] = (40, 44, 52)
    spawn_origin: tuple[float, float] = (320.0, 420.0)


@dataclass(slots=True)
class GeneBounds:
    amplitude_ratio: tuple[float, float] = (0.05, 0.32)
    omega: tuple[float, float] = (1.5, 9.0)
    phase: tuple[float, float] = (0.0, 6.283185307179586)


@dataclass(slots=True)
class EvaluationConfig:
    duration_seconds: float = 10.0


@dataclass(slots=True)
class EvolutionConfig:
    population_size: int = 50
    generations: int = 50
    elite_count: int = 2
    tournament_size: int = 4
    sbx_eta: float = 12.0
    mutation_eta: float = 18.0
    mutation_probability: float = 0.18
    seed: int = 42
    demo_interval: int = 5
    demo_seconds: float = 5.0
    results_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "results")
