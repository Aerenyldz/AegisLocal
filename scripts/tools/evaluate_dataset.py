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
import sys
from typing import Any

import numpy as np

# Allow the documented repository-root invocation to import the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

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


def _quality_report(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts = {
        label: sum(session["label"] == label for session in sessions)
        for label in ("human", "bot")
    }
    event_ids = [session.get("event_id") for session in sessions if session.get("event_id")]
    duplicate_event_ids = len(event_ids) - len(set(event_ids))
    bot_families = sorted(
        {
            str(session["bot_family"])
            for session in sessions
            if session["label"] == "bot" and session.get("bot_family")
        }
    )
    metadata_coverage = sum(
        bool(session.get("collection_context"))
        for session in sessions
    ) / len(sessions)
    return {
        "duplicate_event_ids": duplicate_event_ids,
        "bot_families": bot_families,
        "metadata_coverage": metadata_coverage,
        "minimum_samples_per_class_met": min(class_counts.values()) >= 10,
    }


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


def _release_allowed(
    *,
    samples: int,
    class_counts: dict[str, int],
    roc_auc: float | None,
    operating_point: dict[str, float | None],
) -> bool:
    fpr = operating_point["fpr"]
    tpr = operating_point["tpr"]
    return bool(
        samples >= 20
        and class_counts["human"] >= 10
        and class_counts["bot"] >= 10
        and roc_auc is not None
        and roc_auc >= 0.85
        and fpr is not None
        and fpr <= 0.02
        and tpr is not None
        and tpr >= 0.85
    )


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
    quality = _quality_report(sessions)
    sufficient_data = (
        len(sessions) >= 20
        and quality["minimum_samples_per_class_met"]
        and quality["duplicate_event_ids"] == 0
    )
    human_scores = [s for s, y in zip(scores, labels) if y == 0]
    bot_scores = [s for s, y in zip(scores, labels) if y == 1]
    operating_point = {
        key: _optional_metric(value)
        for key, value in _metrics(labels, scores, args.threshold).items()
    }
    auc = _optional_metric(_roc_auc(labels, scores))
    result = {
        "dataset": str(args.dataset),
        "samples": len(sessions),
        "class_counts": class_counts,
        "status": "ready_for_comparison" if sufficient_data else "insufficient_classes",
        "model_release_allowed": _release_allowed(
            samples=len(sessions),
            class_counts=class_counts,
            roc_auc=auc,
            operating_point=operating_point,
        ),
        "data_quality": quality,
        "risk": {
            "human_mean": _optional_metric(float(np.mean(human_scores))) if human_scores else None,
            "bot_mean": _optional_metric(float(np.mean(bot_scores))) if bot_scores else None,
        },
        "roc_auc": auc,
        "operating_point": operating_point,
    }
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
