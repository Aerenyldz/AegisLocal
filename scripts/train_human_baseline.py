"""Build a local human feature baseline from labeled JSONL sessions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_dataset import _load_sessions
from app.ml.fft_features import extract_fft_features


FEATURES = (
    "tremor_ratio",
    "tremor_band_energy",
    "spectral_centroid_hz",
    "peak_frequency_hz",
    "velocity_cv",
    "jerk_mean",
    "path_smoothness",
    "sampling_hz",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("datasets/processed/human_baseline.json"))
    args = parser.parse_args()
    sessions = [s for s in _load_sessions(args.dataset) if s["label"] == "human"]
    if not sessions:
        raise ValueError("dataset must contain at least one human session")
    rows = [extract_fft_features(s["points"]) for s in sessions]
    baseline = {
        "version": 1,
        "samples": len(rows),
        "features": {
            name: {
                "mean": float(np.mean([getattr(row, name) for row in rows])),
                "std": float(np.std([getattr(row, name) for row in rows])),
            }
            for name in FEATURES
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"Human baseline written: {args.output} ({len(rows)} sessions)")


if __name__ == "__main__":
    main()
