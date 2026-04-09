from __future__ import annotations

import argparse
from pathlib import Path

import pygame
import pymunk

from config import EvaluationConfig, EvolutionConfig, SimulationConfig
from creature import Creature
from ga_engine import GAIndividual, GeneticAlgorithmEngine
from io_utils import EvolutionRecord, ensure_results_dir, load_genome, save_best_genome, save_fitness_curve, save_history
from simulation_core import build_space

DEFAULT_DEMO_GENES = [0.18, 5.2, 0.0, 0.14, 4.4, 2.1, 0.16, 5.8, 4.0]


class OverlayStats:
    def __init__(
        self,
        mode_name: str,
        generation: int = 0,
        max_fitness: float = 0.0,
        average_fitness: float = 0.0,
    ) -> None:
        self.mode_name = mode_name
        self.generation = generation
        self.max_fitness = max_fitness
        self.average_fitness = average_fitness
        self.elapsed_time = 0.0
        self.physics_steps = 0


class DemoSimulation:
    def __init__(self, config: SimulationConfig, render: bool = True) -> None:
        self.config = config
        self.render = render
        self.space: pymunk.Space | None = None
        self.ground: pymunk.Segment | None = None
        self.creature: Creature | None = None
        self.overlay = OverlayStats(mode_name="Evolution Preview" if render else "Headless Eval")
        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.font: pygame.font.Font | None = None
        self.camera_x = 0.0
        self._pygame_ready = False

    def _init_pygame(self) -> None:
        if not self.render or self._pygame_ready:
            return
        pygame.init()
        pygame.display.set_caption("Soft-Body Evolution Simulator")
        self.screen = pygame.display.set_mode((self.config.width, self.config.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self._pygame_ready = True

    def reset_creature(
        self,
        genes: list[float],
        generation: int,
        max_fitness: float,
        average_fitness: float,
        mode_name: str,
    ) -> None:
        self.space, self.ground = build_space(self.config)
        self.creature = Creature(self.space, self.config, genes=genes)
        self.overlay = OverlayStats(
            mode_name=mode_name,
            generation=generation,
            max_fitness=max_fitness,
            average_fitness=average_fitness,
        )
        self.camera_x = 0.0

    def _spring_color(self, normalized_state: float) -> tuple[int, int, int]:
        t = max(-1.0, min(1.0, normalized_state))
        if t >= 0:
            red = 120 + int(135 * t)
            green = 190 - int(100 * t)
            blue = 255 - int(170 * t)
        else:
            amount = abs(t)
            red = 255 - int(170 * amount)
            green = 180 - int(70 * amount)
            blue = 120 + int(135 * amount)
        return red, green, blue

    def _world_to_screen(self, point: pymunk.Vec2d) -> tuple[int, int]:
        return int(point.x - self.camera_x), int(point.y)

    def _update_camera(self) -> None:
        assert self.creature is not None
        centroid = self.creature.centroid()
        target = centroid.x - self.config.width * 0.35
        self.camera_x += (target - self.camera_x) * 0.08

    def _draw(self) -> None:
        assert self.screen is not None and self.font is not None
        assert self.creature is not None and self.ground is not None
        self.screen.fill(self.config.background_color)
        self._update_camera()

        pygame.draw.line(
            self.screen,
            self.config.ground_color,
            self._world_to_screen(pymunk.Vec2d(self.ground.a.x, self.ground.a.y)),
            self._world_to_screen(pymunk.Vec2d(self.ground.b.x, self.ground.b.y)),
            10,
        )

        for start, end, state in self.creature.spring_segments():
            pygame.draw.line(
                self.screen,
                self._spring_color(state),
                self._world_to_screen(start),
                self._world_to_screen(end),
                6,
            )

        for body in self.creature.bodies:
            pygame.draw.circle(
                self.screen,
                self.config.body_fill,
                self._world_to_screen(body.position),
                int(self.config.mass_radius),
            )
            pygame.draw.circle(
                self.screen,
                self.config.body_outline,
                self._world_to_screen(body.position),
                int(self.config.mass_radius),
                2,
            )

        centroid = self.creature.centroid()
        lines = [
            f"Mode: {self.overlay.mode_name}",
            f"Generation: {self.overlay.generation}",
            f"Max Fitness: {self.overlay.max_fitness:8.3f}",
            f"Average Fitness: {self.overlay.average_fitness:8.3f}",
            f"Preview Time: {self.overlay.elapsed_time:5.2f}s",
            f"Centroid X: {centroid.x:8.2f}",
        ]
        for index, line in enumerate(lines):
            surface = self.font.render(line, True, (236, 242, 248))
            self.screen.blit(surface, (18, 18 + index * 28))

        pygame.display.flip()

    def run_preview(self, max_seconds: float | None = None) -> bool:
        assert self.space is not None and self.creature is not None
        self._init_pygame()
        running = True
        while running:
            if self.render:
                assert self.clock is not None
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return False
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        return False

            self.creature.update(self.overlay.elapsed_time)
            self.space.step(self.config.physics_dt)
            self.overlay.elapsed_time += self.config.physics_dt
            self.overlay.physics_steps += 1

            if self.render and self.overlay.physics_steps % 4 == 0:
                self._draw()
                self.clock.tick(self.config.render_fps)

            if max_seconds is not None and self.overlay.elapsed_time >= max_seconds:
                break
        return True

    def close(self) -> None:
        if self.render and self._pygame_ready:
            pygame.quit()
            self._pygame_ready = False


class EvolutionRunner:
    def __init__(
        self,
        simulation_config: SimulationConfig,
        evaluation_config: EvaluationConfig,
        evolution_config: EvolutionConfig,
        enable_demo: bool = True,
    ) -> None:
        self.simulation_config = simulation_config
        self.evaluation_config = evaluation_config
        self.evolution_config = evolution_config
        self.enable_demo = enable_demo
        self.engine = GeneticAlgorithmEngine(evolution_config, simulation_config, evaluation_config)
        self.history: list[EvolutionRecord] = []
        self.results_dir = ensure_results_dir(evolution_config.results_dir)
        self.global_best: GAIndividual | None = None
        self.global_best_generation = 0
        self.viewer = DemoSimulation(simulation_config, render=True) if enable_demo else None

    def run(self) -> None:
        self.engine.initialize_population()

        try:
            for generation in range(1, self.evolution_config.generations + 1):
                self.engine.evaluate_population()
                best = self.engine.best_individual().clone()
                avg = self.engine.average_fitness()
                self.history.append(EvolutionRecord(generation, best.fitness or 0.0, avg))
                self._update_global_best(best, generation)
                self._save_generation_artifacts(generation, best)
                print(
                    f"Generation {generation:03d} | max fitness = {(best.fitness or 0.0):8.3f} | avg fitness = {avg:8.3f}"
                )

                if self.enable_demo and generation % self.evolution_config.demo_interval == 0:
                    should_continue = self._run_demo(generation, best, avg)
                    if not should_continue:
                        break

                if generation < self.evolution_config.generations:
                    self.engine.evolve_one_generation()
        finally:
            if self.viewer is not None:
                self.viewer.close()

        if self.global_best is not None:
            save_best_genome(
                self.results_dir / "best_genome_overall.json",
                self.global_best_generation,
                self.global_best.genes,
                self.global_best.fitness or 0.0,
            )
        save_history(self.results_dir / "fitness_history.json", self.history)
        save_fitness_curve(self.results_dir / "fitness_curve.png", self.history)

    def _update_global_best(self, candidate: GAIndividual, generation: int) -> None:
        if self.global_best is None or (candidate.fitness or float("-inf")) > (self.global_best.fitness or float("-inf")):
            self.global_best = candidate.clone()
            self.global_best_generation = generation

    def _save_generation_artifacts(self, generation: int, best: GAIndividual) -> None:
        save_best_genome(
            self.results_dir / f"best_genome_gen_{generation:03d}.json",
            generation,
            best.genes,
            best.fitness or 0.0,
        )

    def _run_demo(self, generation: int, best: GAIndividual, avg: float) -> bool:
        assert self.viewer is not None
        self.viewer.reset_creature(
            genes=best.genes,
            generation=generation,
            max_fitness=best.fitness or 0.0,
            average_fitness=avg,
            mode_name="Evolution Preview",
        )
        return self.viewer.run_preview(max_seconds=self.evolution_config.demo_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Soft-body evolution simulator")
    parser.add_argument("--headless", action="store_true", help="Run replay without rendering")
    parser.add_argument("--seconds", type=float, default=8.0, help="Replay preview duration")
    parser.add_argument("--evolve", action="store_true", help="Legacy flag: evolution now runs by default")
    parser.add_argument("--generations", type=int, default=None, help="Override default generation count")
    parser.add_argument("--no-demo", action="store_true", help="Run evolution without visualization")
    parser.add_argument(
        "--replay",
        type=str,
        default=None,
        help="Replay a saved genome JSON such as results/best_genome_overall.json",
    )
    return parser.parse_args()


def run_replay(path: Path, headless: bool, seconds: float) -> None:
    generation, fitness, genes = load_genome(path)
    simulation = DemoSimulation(SimulationConfig(), render=not headless)
    simulation.reset_creature(
        genes=genes,
        generation=generation,
        max_fitness=fitness,
        average_fitness=fitness,
        mode_name="Replay",
    )
    try:
        simulation.run_preview(max_seconds=seconds)
    finally:
        simulation.close()


def main() -> None:
    args = parse_args()

    if args.replay is not None:
        replay_path = Path(args.replay)
        run_replay(replay_path, args.headless, args.seconds)
        return

    evolution_config = EvolutionConfig()
    if args.generations is not None:
        evolution_config.generations = args.generations

    print(
        f"[RUN] evolve mode | generations={evolution_config.generations}, "
        f"demo_interval={evolution_config.demo_interval}, "
        f"demo_seconds={evolution_config.demo_seconds}"
    )

    runner = EvolutionRunner(
        SimulationConfig(),
        EvaluationConfig(),
        evolution_config,
        enable_demo=not args.no_demo,
    )
    runner.run()


if __name__ == "__main__":
    main()
