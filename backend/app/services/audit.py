"""Local, bounded decision audit storage.

Only derived decision evidence is retained here; raw trajectories and form
values are intentionally excluded.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from secrets import token_hex
from typing import Any

from app.ml.scoring import ScoreBreakdown
from app.services.policy import PolicyDecision


_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "audit.sqlite3"

def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_events (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            session_id TEXT NOT NULL,
            policy TEXT NOT NULL,
            mode TEXT NOT NULL,
            risk_score REAL NOT NULL,
            label TEXT NOT NULL,
            enforcement TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            model_version TEXT NOT NULL,
            feature_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(decision_events)").fetchall()
    }
    if "operator_label" not in columns:
        connection.execute("ALTER TABLE decision_events ADD COLUMN operator_label TEXT")
    if "labeled_at" not in columns:
        connection.execute("ALTER TABLE decision_events ADD COLUMN labeled_at TEXT")
    if "feature_json" not in columns:
        connection.execute("ALTER TABLE decision_events ADD COLUMN feature_json TEXT NOT NULL DEFAULT '{}'")
    return connection


def record_decision(
    *,
    endpoint: str,
    session_id: str,
    scored: ScoreBreakdown,
    policy: PolicyDecision,
    features: dict[str, float] | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": token_hex(12),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "session_id": session_id,
        "policy": policy.policy,
        "mode": policy.mode,
        "risk_score": scored.risk_score,
        "label": scored.label,
        "enforcement": policy.enforcement,
        "reasons": list(scored.reasons),
        "model_version": "heuristic-0.1.0",
        "features": features or {},
    }
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO decision_events
            (event_id, timestamp, endpoint, session_id, policy, mode,
             risk_score, label, enforcement, reasons_json,              model_version, feature_json)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["timestamp"],
                event["endpoint"],
                event["session_id"],
                event["policy"],
                event["mode"],
                event["risk_score"],
                event["label"],
                event["enforcement"],
                json.dumps(event["reasons"]),
                event["model_version"],
                json.dumps(event["features"]),
            ),
        )
    return event


def recent_events(
    limit: int = 50,
    *,
    policy: str | None = None,
    enforcement: str | None = None,
) -> list[dict[str, Any]]:
    with _connect() as connection:
        clauses: list[str] = []
        params: list[Any] = []
        if policy:
            clauses.append("policy = ?")
            params.append(policy)
        if enforcement:
            clauses.append("enforcement = ?")
            params.append(enforcement)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = connection.execute(
            """
            SELECT event_id, timestamp, endpoint, session_id, policy, mode,
                   risk_score, label, enforcement, reasons_json, model_version,
                   operator_label, labeled_at, feature_json
            FROM decision_events
            """
            + where
            + """
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [
        {
            "event_id": row["event_id"],
            "timestamp": row["timestamp"],
            "endpoint": row["endpoint"],
            "session_id": row["session_id"],
            "policy": row["policy"],
            "mode": row["mode"],
            "risk_score": row["risk_score"],
            "label": row["label"],
            "enforcement": row["enforcement"],
            "reasons": json.loads(row["reasons_json"]),
            "model_version": row["model_version"],
            "operator_label": row["operator_label"],
            "labeled_at": row["labeled_at"],
            "features": json.loads(row["feature_json"]),
        }
        for row in rows
    ]


def clear_events() -> None:
    with _connect() as connection:
        connection.execute("DELETE FROM decision_events")


def summary() -> dict[str, Any]:
    with _connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM decision_events").fetchone()[0]
        rows = connection.execute(
            "SELECT enforcement, COUNT(*) AS count FROM decision_events GROUP BY enforcement"
        ).fetchall()
    return {
        "total_events": total,
        "by_enforcement": {row["enforcement"]: row["count"] for row in rows},
        "storage": "local_sqlite",
        "raw_trajectory_retained": False,
        "labeled_events": labeled_count(),
    }


def evaluation(threshold: float = 0.66) -> dict[str, Any]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT risk_score, operator_label
            FROM decision_events
            WHERE operator_label IN ('human', 'bot')
            """
        ).fetchall()
    labels = [int(row["operator_label"] == "bot") for row in rows]
    scores = [float(row["risk_score"]) for row in rows]
    humans = sum(1 for label in labels if label == 0)
    bots = sum(labels)
    predicted = [score >= threshold for score in scores]
    true_positive = sum(predicted_item and label for predicted_item, label in zip(predicted, labels))
    true_negative = sum(
        not predicted_item and not label
        for predicted_item, label in zip(predicted, labels)
    )
    positives = bots
    negatives = humans
    auc = None
    if positives and negatives:
        bot_scores = [score for score, label in zip(scores, labels) if label]
        human_scores = [score for score, label in zip(scores, labels) if not label]
        auc = sum(
            1 if bot > human else 0.5 if bot == human else 0
            for bot in bot_scores
            for human in human_scores
        ) / (positives * negatives)
    return {
        "samples": len(rows),
        "class_counts": {"human": humans, "bot": bots},
        "threshold": threshold,
        "roc_auc": auc,
        "tpr": true_positive / positives if positives else None,
        "fpr": (negatives - true_negative) / negatives if negatives else None,
        "status": "ready_for_comparison" if positives and negatives else "insufficient_classes",
        "model_release_allowed": bool(len(rows) >= 20 and positives and negatives),
    }


def label_event(event_id: str, operator_label: str) -> dict[str, Any] | None:
    if operator_label not in {"human", "bot", "uncertain"}:
        raise ValueError("operator_label must be human, bot, or uncertain")
    timestamp = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE decision_events
            SET operator_label = ?, labeled_at = ?
            WHERE event_id = ?
            """,
            (operator_label, timestamp, event_id),
        )
        if cursor.rowcount == 0:
            return None
    return {"event_id": event_id, "operator_label": operator_label, "labeled_at": timestamp}


def labeled_count() -> int:
    with _connect() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM decision_events WHERE operator_label IS NOT NULL"
        ).fetchone()[0]
