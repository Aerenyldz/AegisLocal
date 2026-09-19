"""Evaluate the MVP scorer on deterministic synthetic human and bot trajectories."""

from __future__ import annotations

import argparse
import json
import math

import numpy as np

from app.ml.fft_features import extract_fft_features
from app.ml.scoring import score_features


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


def bot_trajectory(n: int = 120) -> list[dict[str, float]]:
    points = []
    for i in range(n):
        u = i / (n - 1)
        points.append(
            {
                "x": 300 * (3 * (1 - u) ** 2 * u + u**3),
                "y": 200 * (3 * (1 - u) * u**2 + u**3),
                "t": i * (1000.0 / 60.0),
            }
        )
    return points


def score(points: list[dict[str, float]], webdriver: bool) -> float:
    return score_features(
        extract_fft_features(points),
        webdriver=webdriver,
        pow_ok=True,
    ).risk_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")

    human_scores = [score(human_trajectory(seed), False) for seed in range(args.samples)]
    bot_scores = [score(bot_trajectory(), True) for _ in range(args.samples)]
    threshold = 0.66
    result = {
        "samples_per_class": args.samples,
        "human": {
            "mean_risk": float(np.mean(human_scores)),
            "max_risk": float(np.max(human_scores)),
            "false_positive_rate": float(np.mean(np.array(human_scores) >= threshold)),
        },
        "bot": {
            "mean_risk": float(np.mean(bot_scores)),
            "min_risk": float(np.min(bot_scores)),
            "true_positive_rate": float(np.mean(np.array(bot_scores) >= threshold)),
        },
        "threshold": threshold,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
