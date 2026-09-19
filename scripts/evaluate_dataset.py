"""Evaluate labeled mouse sessions from a JSONL dataset.

Each line must contain:
{"label": "human"|"bot", "points": [{"x": 0, "y": 0, "t": 0}], "webdriver": false}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from app.ml.fft_features import extract_fft_features
from app.ml.scoring import score_features


def _load_sessions(path: Path) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        if item.get("label") not in {"human", "bot"}:
            raise ValueError(f"{path}:{line_number}: label must be human or bot")
        points = item.get("points")
        if not isinstance(points, list) or len(points) < 8:
            raise ValueError(f"{path}:{line_number}: at least 8 points are required")
        sessions.append(item)
    if not sessions:
        raise ValueError(f"{path}: dataset is empty")
    return sessions


def _roc_auc(labels: list[int], scores: list[float]) -> float:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return float("nan")
    wins = sum(1.0 if positive > negative else 0.5 if positive == negative else 0.0
               for positive in positives for negative in negatives)
    return wins / (len(positives) * len(negatives))


def _metrics(labels: list[int], scores: list[float], threshold: float) -> dict[str, float]:
    predicted = [score >= threshold for score in scores]
    tp = sum(p and y for p, y in zip(predicted, labels))
    tn = sum(not p and not y for p, y in zip(predicted, labels))
    positives = sum(labels)
    negatives = len(labels) - positives
    return {
        "threshold": threshold,
        "tpr": tp / positives if positives else float("nan"),
        "fpr": (negatives - tn) / negatives if negatives else float("nan"),
        "accuracy": (tp + tn) / len(labels),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--threshold", type=float, default=0.66)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")

    sessions = _load_sessions(args.dataset)
    scores = [
        score_features(
            extract_fft_features(session["points"]),
            webdriver=bool(session.get("webdriver", False)),
            pow_ok=bool(session.get("pow_ok", True)),
        ).risk_score
        for session in sessions
    ]
    labels = [int(session["label"] == "bot") for session in sessions]
    result = {
        "dataset": str(args.dataset),
        "samples": len(sessions),
        "class_counts": {
            "human": labels.count(0),
            "bot": labels.count(1),
        },
        "risk": {
            "human_mean": float(np.mean([s for s, y in zip(scores, labels) if y == 0])),
            "bot_mean": float(np.mean([s for s, y in zip(scores, labels) if y == 1])),
        },
        "roc_auc": _roc_auc(labels, scores),
        "operating_point": _metrics(labels, scores, args.threshold),
    }
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
