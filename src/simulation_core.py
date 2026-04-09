from __future__ import annotations

import pymunk

from config import SimulationConfig


def build_space(config: SimulationConfig) -> tuple[pymunk.Space, pymunk.Segment]:
    space = pymunk.Space()
    space.gravity = (config.gravity_x, config.gravity_y)
    ground = pymunk.Segment(
        space.static_body,
        (0, config.ground_y),
        (5000, config.ground_y),
        8.0,
    )
    ground.friction = config.ground_friction
    ground.elasticity = 0.0
    space.add(ground)
    return space, ground
