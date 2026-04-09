from __future__ import annotations

import random
from dataclasses import dataclass

from config import EvaluationConfig, EvolutionConfig, GeneBounds, SimulationConfig
from creature import Creature
from simulation_core import build_space


@dataclass(slots=True)
class GAIndividual:
    genes: list[float]
    fitness: float | None = None

    def clone(self) -> "GAIndividual":
        return GAIndividual(self.genes[:], self.fitness)


class CreatureEvaluator:
    def __init__(self, simulation_config: SimulationConfig, evaluation_config: EvaluationConfig) -> None:
        self.simulation_config = simulation_config
        self.evaluation_config = evaluation_config

    def evaluate(self, genes: list[float]) -> float:
        space, _ground = build_space(self.simulation_config)
        creature = Creature(space, self.simulation_config, genes=genes)
        start_x = creature.centroid().x
        elapsed = 0.0
        while elapsed < self.evaluation_config.duration_seconds:
            creature.update(elapsed)
            space.step(self.simulation_config.physics_dt)
            elapsed += self.simulation_config.physics_dt
        return creature.centroid().x - start_x


class GeneticAlgorithmEngine:
    def __init__(
        self,
        evolution_config: EvolutionConfig,
        simulation_config: SimulationConfig,
        evaluation_config: EvaluationConfig,
    ) -> None:
        self.evolution_config = evolution_config
        self.simulation_config = simulation_config
        self.evaluation_config = evaluation_config
        self.bounds = GeneBounds()
        self.rng = random.Random(evolution_config.seed)
        self.evaluator = CreatureEvaluator(simulation_config, evaluation_config)
        self.population: list[GAIndividual] = []

    def initialize_population(self) -> None:
        self.population = [GAIndividual(self._random_genes()) for _ in range(self.evolution_config.population_size)]

    def evaluate_population(self) -> None:
        for individual in self.population:
            if individual.fitness is None:
                individual.fitness = self.evaluator.evaluate(individual.genes)
        self.population.sort(key=lambda ind: ind.fitness if ind.fitness is not None else float("-inf"), reverse=True)

    def best_individual(self) -> GAIndividual:
        return self.population[0]

    def average_fitness(self) -> float:
        return sum(ind.fitness or 0.0 for ind in self.population) / len(self.population)

    def evolve_one_generation(self) -> None:
        self.evaluate_population()
        next_population = [ind.clone() for ind in self.population[: self.evolution_config.elite_count]]
        while len(next_population) < self.evolution_config.population_size:
            parent_a = self._tournament_select()
            parent_b = self._tournament_select()
            child_a_genes, child_b_genes = self._simulated_binary_crossover(parent_a.genes, parent_b.genes)
            child_a_genes = self._polynomial_mutation(child_a_genes)
            child_b_genes = self._polynomial_mutation(child_b_genes)
            next_population.append(GAIndividual(child_a_genes))
            if len(next_population) < self.evolution_config.population_size:
                next_population.append(GAIndividual(child_b_genes))
        self.population = next_population

    def _random_genes(self) -> list[float]:
        genes: list[float] = []
        for _ in range(Creature.gene_count() // 3):
            genes.append(self.rng.uniform(*self.bounds.amplitude_ratio))
            genes.append(self.rng.uniform(*self.bounds.omega))
            genes.append(self.rng.uniform(*self.bounds.phase))
        return genes

    def _tournament_select(self) -> GAIndividual:
        contenders = self.rng.sample(self.population, self.evolution_config.tournament_size)
        contenders.sort(key=lambda ind: ind.fitness if ind.fitness is not None else float("-inf"), reverse=True)
        return contenders[0]

    def _simulated_binary_crossover(self, a: list[float], b: list[float]) -> tuple[list[float], list[float]]:
        child1 = a[:]
        child2 = b[:]
        eta = self.evolution_config.sbx_eta
        bounds = self._gene_bounds_per_index()
        for i, (x1, x2) in enumerate(zip(a, b)):
            if self.rng.random() > 0.5 or abs(x1 - x2) < 1e-12:
                continue
            lower, upper = bounds[i]
            u = self.rng.random()
            beta = (2 * u) ** (1.0 / (eta + 1.0)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1.0 / (eta + 1.0))
            c1 = 0.5 * ((1 + beta) * x1 + (1 - beta) * x2)
            c2 = 0.5 * ((1 - beta) * x1 + (1 + beta) * x2)
            child1[i] = min(max(c1, lower), upper)
            child2[i] = min(max(c2, lower), upper)
        return child1, child2

    def _polynomial_mutation(self, genes: list[float]) -> list[float]:
        mutated = genes[:]
        eta = self.evolution_config.mutation_eta
        bounds = self._gene_bounds_per_index()
        for i, value in enumerate(mutated):
            if self.rng.random() > self.evolution_config.mutation_probability:
                continue
            lower, upper = bounds[i]
            if upper - lower < 1e-12:
                continue
            delta1 = (value - lower) / (upper - lower)
            delta2 = (upper - value) / (upper - lower)
            rand = self.rng.random()
            mut_pow = 1.0 / (eta + 1.0)
            if rand < 0.5:
                xy = 1.0 - delta1
                val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1.0))
                delta_q = val ** mut_pow - 1.0
            else:
                xy = 1.0 - delta2
                val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1.0))
                delta_q = 1.0 - val ** mut_pow
            value = value + delta_q * (upper - lower)
            mutated[i] = min(max(value, lower), upper)
        return mutated

    def _gene_bounds_per_index(self) -> list[tuple[float, float]]:
        bounds: list[tuple[float, float]] = []
        for _ in range(Creature.gene_count() // 3):
            bounds.extend([self.bounds.amplitude_ratio, self.bounds.omega, self.bounds.phase])
        return bounds
