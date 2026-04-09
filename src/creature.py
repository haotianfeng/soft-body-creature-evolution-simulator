from __future__ import annotations

from dataclasses import dataclass
from math import sin
from typing import Iterable, Sequence

import pymunk

from config import GeneBounds, SimulationConfig


@dataclass(slots=True)
class MuscleParameters:
    amplitude_ratio: float
    omega: float
    phase: float


@dataclass(slots=True)
class MuscleSpring:
    spring: pymunk.DampedSpring
    base_length: float
    params: MuscleParameters

    def update(self, time_seconds: float) -> None:
        self.spring.rest_length = self.base_length + self.base_length * self.params.amplitude_ratio * sin(
            self.params.omega * time_seconds + self.params.phase
        )

    @property
    def normalized_state(self) -> float:
        amplitude = self.base_length * self.params.amplitude_ratio
        if amplitude == 0:
            return 0.0
        return (self.spring.rest_length - self.base_length) / amplitude


class Creature:
    DEFAULT_GENE_TRIPLETS = [
        (0.18, 5.2, 0.0),
        (0.14, 4.4, 2.1),
        (0.16, 5.8, 4.0),
    ]

    def __init__(
        self,
        space: pymunk.Space,
        config: SimulationConfig,
        origin: tuple[float, float] | None = None,
        genes: Sequence[float] | None = None,
    ) -> None:
        self.space = space
        self.config = config
        self.origin = origin or config.spawn_origin
        self.bodies: list[pymunk.Body] = []
        self.shapes: list[pymunk.Circle] = []
        self.muscles: list[MuscleSpring] = []
        self._gene_bounds = GeneBounds()
        self._build_triangle_body(self._decode_genes(genes))

    @classmethod
    def gene_count(cls) -> int:
        return len(cls.DEFAULT_GENE_TRIPLETS) * 3

    def _decode_genes(self, genes: Sequence[float] | None) -> list[MuscleParameters]:
        if genes is None:
            return [MuscleParameters(*triple) for triple in self.DEFAULT_GENE_TRIPLETS]
        if len(genes) != self.gene_count():
            raise ValueError(f"Creature genes length must be {self.gene_count()}, got {len(genes)}")

        bounds = self._gene_bounds
        decoded: list[MuscleParameters] = []
        for i in range(0, len(genes), 3):
            a = min(max(float(genes[i]), bounds.amplitude_ratio[0]), bounds.amplitude_ratio[1])
            w = min(max(float(genes[i + 1]), bounds.omega[0]), bounds.omega[1])
            p = float(genes[i + 2]) % bounds.phase[1]
            decoded.append(MuscleParameters(a, w, p))
        return decoded

    def _build_triangle_body(self, muscle_params: list[MuscleParameters]) -> None:
        x0, y0 = self.origin
        vertices = [
            (x0 - 55.0, y0 + 35.0),
            (x0 + 55.0, y0 + 35.0),
            (x0, y0 - 55.0),
        ]

        for x, y in vertices:
            moment = pymunk.moment_for_circle(self.config.mass_value, 0, self.config.mass_radius)
            body = pymunk.Body(self.config.mass_value, moment)
            body.position = x, y
            shape = pymunk.Circle(body, self.config.mass_radius)
            shape.friction = self.config.point_friction
            shape.elasticity = 0.0
            self.space.add(body, shape)
            self.bodies.append(body)
            self.shapes.append(shape)

        for (a, b), params in zip([(0, 1), (1, 2), (2, 0)], muscle_params):
            body_a = self.bodies[a]
            body_b = self.bodies[b]
            base_length = body_a.position.get_distance(body_b.position)
            spring = pymunk.DampedSpring(
                body_a,
                body_b,
                (0, 0),
                (0, 0),
                rest_length=base_length,
                stiffness=self.config.spring_stiffness,
                damping=self.config.spring_damping,
            )
            self.space.add(spring)
            self.muscles.append(MuscleSpring(spring=spring, base_length=base_length, params=params))

    def update(self, time_seconds: float) -> None:
        for muscle in self.muscles:
            muscle.update(time_seconds)

    def centroid(self) -> pymunk.Vec2d:
        center = pymunk.Vec2d.zero()
        for body in self.bodies:
            center += body.position
        return center / len(self.bodies)

    def spring_segments(self) -> Iterable[tuple[pymunk.Vec2d, pymunk.Vec2d, float]]:
        for muscle in self.muscles:
            yield muscle.spring.a.position, muscle.spring.b.position, muscle.normalized_state
