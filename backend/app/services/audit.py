"""Local, bounded decision audit storage.

Only derived decision evidence is retained here; raw trajectories and form
values are intentionally excluded.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from statistics import quantiles
from pathlib import Path
from secrets import token_hex
from typing import Any

from app.core.config import get_settings
from app.ml.scoring import ScoreBreakdown
from app.services.policy import PolicyDecision


def _db_path() -> Path:
    configured_path = Path(get_settings().audit_db_path)
    if configured_path.is_absolute():
        return configured_path
    return Path(__file__).resolve().parents[3] / configured_path

def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
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
            ,latency_ms REAL
            ,shadow_risk_score REAL
            ,shadow_model_version TEXT
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
    if "latency_ms" not in columns:
        connection.execute("ALTER TABLE decision_events ADD COLUMN latency_ms REAL")
    if "shadow_risk_score" not in columns:
        connection.execute("ALTER TABLE decision_events ADD COLUMN shadow_risk_score REAL")
    if "shadow_model_version" not in columns:
        connection.execute("ALTER TABLE decision_events ADD COLUMN shadow_model_version TEXT")
    return connection


def record_decision(
    *,
    endpoint: str,
    session_id: str,
    scored: ScoreBreakdown,
    policy: PolicyDecision,
    features: dict[str, float] | None = None,
    latency_ms: float | None = None,
    shadow_risk_score: float | None = None,
    shadow_model_version: str | None = None,
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
        "latency_ms": latency_ms,
        "shadow_risk_score": shadow_risk_score,
        "shadow_model_version": shadow_model_version,
    }
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO decision_events
            (event_id, timestamp, endpoint, session_id, policy, mode,
             risk_score, label, enforcement, reasons_json,                                        model_version, feature_json, latency_ms, shadow_risk_score,
             shadow_model_version)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                event["latency_ms"],
                event["shadow_risk_score"],
                event["shadow_model_version"],
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
                   operator_label, labeled_at, feature_json, latency_ms,
                   shadow_risk_score, shadow_model_version
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
            "latency_ms": row["latency_ms"],
            "shadow_risk_score": row["shadow_risk_score"],
            "shadow_model_version": row["shadow_model_version"],
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
        endpoint_rows = connection.execute(
            "SELECT endpoint, COUNT(*) AS count FROM decision_events GROUP BY endpoint"
        ).fetchall()
        policy_rows = connection.execute(
            "SELECT policy, COUNT(*) AS count FROM decision_events GROUP BY policy"
        ).fetchall()
        latency_rows = connection.execute(
            "SELECT latency_ms FROM decision_events WHERE latency_ms IS NOT NULL"
        ).fetchall()
        labeled = connection.execute(
            """
            SELECT operator_label, enforcement, COUNT(*) AS count
            FROM decision_events
            WHERE operator_label IN ('human', 'bot')
            GROUP BY operator_label, enforcement
            """
        ).fetchall()
        hourly_rows = connection.execute(
            """
            SELECT substr(timestamp, 1, 13) AS hour, COUNT(*) AS count
            FROM decision_events
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT 24
            """
        ).fetchall()
    latencies = sorted(float(row["latency_ms"]) for row in latency_rows)
    p95 = (
        quantiles(latencies, n=100, method="inclusive")[94]
        if len(latencies) >= 2
        else (latencies[0] if latencies else None)
    )
    false_positive = sum(
        row["count"]
        for row in labeled
        if row["operator_label"] == "human"
        and row["enforcement"] in {"challenge", "throttle", "deny"}
    )
    labeled_humans = sum(row["count"] for row in labeled if row["operator_label"] == "human")
    return {
        "total_events": total,
        "by_enforcement": {row["enforcement"]: row["count"] for row in rows},
        "storage": "local_sqlite",
        "raw_trajectory_retained": False,
        "labeled_events": labeled_count(),
        "by_endpoint": {row["endpoint"]: row["count"] for row in endpoint_rows},
        "by_policy": {row["policy"]: row["count"] for row in policy_rows},
        "latency_ms": {"count": len(latencies), "p95": p95},
        "human_false_positive_rate": (
            false_positive / labeled_humans if labeled_humans else None
        ),
        "hourly": [
            {"hour": row["hour"], "count": row["count"]}
            for row in reversed(hourly_rows)
        ],
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
        "status": (
            "ready_for_comparison"
            if len(rows) >= 20 and humans >= 10 and bots >= 10
            else "insufficient_classes"
        ),
        "model_release_allowed": bool(
            len(rows) >= 20
            and humans >= 10
            and bots >= 10
            and auc is not None
            and auc >= 0.85
            and (negatives - true_negative) / negatives <= 0.02
            and true_positive / positives >= 0.85
        ),
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
