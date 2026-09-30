"""Generate a deterministic labeled dataset for MVP pipeline smoke tests.

This dataset is synthetic and must not be used as evidence for a production
release. Real pilot measurements require consented human sessions and a
representative bot corpus.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def human_trajectory(seed: int, n: int = 120) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    x, y = 0.0, 0.0
    points = []
    for i in range(n):
        t = i * (1000.0 / 60.0)
        sec = t / 1000.0
        tremor = 0.35 * math.sin(2 * math.pi * 10 * sec)
        tremor += 0.15 * math.sin(2 * math.pi * 8.5 * sec + 0.3)
        speed = 180 + 90 * math.sin(i / 9) + float(rng.normal(0, 25))
        angle = 0.4 + 0.05 * math.sin(i / 7) + float(rng.normal(0, 0.05))
        x += speed * math.cos(angle) / 60 + tremor
        y += speed * math.sin(angle) / 60 + 0.7 * tremor
        points.append({"x": x, "y": y, "t": t})
    return points


def bot_trajectory(kind: str, n: int = 120) -> list[dict[str, float]]:
    points = []
    for i in range(n):
        u = i / (n - 1)
        if kind == "line":
            x, y = 300 * u, 200 * u
        elif kind == "bezier":
            x = 300 * (3 * (1 - u) ** 2 * u + u**3)
            y = 200 * (3 * (1 - u) * u**2 + u**3)
        else:
            x, y = 300 * u, 100 + 90 * math.sin(u * math.pi * 2)
        points.append({"x": x, "y": y, "t": i * (1000.0 / 60.0)})
    return points


def records(samples_per_class: int) -> list[dict[str, object]]:
    result = []
    for index in range(samples_per_class):
        result.append(
            {
                "event_id": f"synthetic-human-{index:04d}",
                "label": "human",
                "webdriver": False,
                "pow_ok": True,
                "collection_context": {
                    "source": "synthetic",
                    "generator": "generate_mvp_dataset.py",
                    "seed": index,
                },
                "points": human_trajectory(index),
            }
        )
    families = ("line", "bezier", "sine")
    for index in range(samples_per_class):
        family = families[index % len(families)]
        result.append(
            {
                "event_id": f"synthetic-bot-{index:04d}",
                "label": "bot",
                "webdriver": True,
                "pow_ok": True,
                "bot_family": family,
                "collection_context": {
                    "source": "synthetic",
                    "generator": "generate_mvp_dataset.py",
                    "seed": index,
                },
                "points": bot_trajectory(family),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-class", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/raw/synthetic-mvp-v0.1.jsonl"),
    )
    args = parser.parse_args()
    if args.samples_per_class < 10:
        parser.error("--samples-per-class must be at least 10")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset = records(args.samples_per_class)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in dataset:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(f"Dataset written: {args.output} ({len(dataset)} sessions)")


if __name__ == "__main__":
    main()
