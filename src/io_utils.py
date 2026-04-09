from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt

from creature import Creature


@dataclass(slots=True)
class EvolutionRecord:
    generation: int
    max_fitness: float
    average_fitness: float


def ensure_results_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_best_genome(path: Path, generation: int, genes: list[float], fitness: float) -> None:
    payload = {
        "generation": generation,
        "fitness": fitness,
        "gene_count": Creature.gene_count(),
        "genes": [round(float(g), 6) for g in genes],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_genome(path: Path) -> tuple[int, float, list[float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return int(payload.get("generation", 0)), float(payload.get("fitness", 0.0)), [float(x) for x in payload["genes"]]


def save_history(path: Path, history: list[EvolutionRecord]) -> None:
    payload = [asdict(item) for item in history]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_fitness_curve(path: Path, history: list[EvolutionRecord]) -> None:
    if not history:
        return
    generations = [item.generation for item in history]
    max_values = [item.max_fitness for item in history]
    avg_values = [item.average_fitness for item in history]

    plt.figure(figsize=(10, 6))
    plt.plot(generations, max_values, color="#d7263d", linewidth=2.2, label="Max Fitness")
    plt.plot(generations, avg_values, color="#1b998b", linewidth=2.0, label="Average Fitness")
    plt.title("Soft-Body Evolution Fitness Curve")
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
