"""Evaluate labeled mouse sessions or audit snapshots from JSONL.

Each line must contain:
{"label": "human"|"bot", "points": [{"x": 0, "y": 0, "t": 0}], "webdriver": false}

Audit exports contain derived features and the already-produced risk_score;
they intentionally do not contain raw points.
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
        if points is not None and (not isinstance(points, list) or len(points) < 8):
            raise ValueError(f"{path}:{line_number}: at least 8 points are required")
        if points is None and not isinstance(item.get("risk_score"), (int, float)):
            raise ValueError(
                f"{path}:{line_number}: expected points or a numeric risk_score"
            )
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


def _optional_metric(value: float) -> float | None:
    return None if not np.isfinite(value) else value


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
    scores = []
    for session in sessions:
        if "risk_score" in session and "points" not in session:
            scores.append(float(session["risk_score"]))
        else:
            scores.append(
                score_features(
                    extract_fft_features(session["points"]),
                    webdriver=bool(session.get("webdriver", False)),
                    pow_ok=bool(session.get("pow_ok", True)),
                ).risk_score
            )
    labels = [int(session["label"] == "bot") for session in sessions]
    class_counts = {"human": labels.count(0), "bot": labels.count(1)}
    sufficient_data = class_counts["human"] > 0 and class_counts["bot"] > 0
    human_scores = [s for s, y in zip(scores, labels) if y == 0]
    bot_scores = [s for s, y in zip(scores, labels) if y == 1]
    result = {
        "dataset": str(args.dataset),
        "samples": len(sessions),
        "class_counts": class_counts,
        "status": "ready_for_comparison" if sufficient_data else "insufficient_classes",
        "model_release_allowed": sufficient_data and len(sessions) >= 20,
        "risk": {
            "human_mean": _optional_metric(float(np.mean(human_scores))) if human_scores else None,
            "bot_mean": _optional_metric(float(np.mean(bot_scores))) if bot_scores else None,
        },
        "roc_auc": _optional_metric(_roc_auc(labels, scores)),
        "operating_point": {
            key: _optional_metric(value)
            for key, value in _metrics(labels, scores, args.threshold).items()
        },
    }
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
