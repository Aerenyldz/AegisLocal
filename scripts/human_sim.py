"""
Simulate human-like pointer trajectories with physiological micro-tremor.

Run (API up): python scripts/human_sim.py
"""

from __future__ import annotations

import math
import os

import httpx
import numpy as np

API = os.environ.get("AEGIS_API", "http://127.0.0.1:8000")


def human_trajectory(n: int = 140, seed: int = 42) -> list[dict]:
    rng = np.random.default_rng(seed)
    x, y = 80.0, 120.0
    pts = []
    for i in range(n):
        t = i * (1000.0 / 60.0)
        sec = t / 1000.0
        tremor = 0.4 * math.sin(2 * math.pi * 10 * sec)
        tremor += 0.2 * math.sin(2 * math.pi * 8.2 * sec + 0.7)
        tremor += float(rng.normal(0, 0.08))
        progress = i / (n - 1)
        speed = 220 * math.sin(math.pi * progress) + float(rng.normal(0, 18))
        angle = 0.55 + 0.08 * math.sin(i / 11) + float(rng.normal(0, 0.04))
        x += speed * math.cos(angle) / 60 + tremor
        y += speed * math.sin(angle) / 60 + 0.65 * tremor
        pts.append({"x": x, "y": y, "t": t})
    return pts


def main() -> None:
    payload = {
        "session_id": "humansim000001",
        "points": human_trajectory(),
        "webdriver": False,
        "fingerprint": {"source": "human-sim"},
    }
    with httpx.Client(base_url=API, timeout=30.0) as client:
        client.get("/health").raise_for_status()
        data = client.post("/v1/analyze/mouse", json=payload).json()

    print("decision:", data["decision"])
    print("risk_score:", data["risk_score"])
    print("label:", data["label"])
    print("features:", data["features"])
    print("reasons:")
    for r in data["reasons"]:
        print(" -", r)


if __name__ == "__main__":
    main()
