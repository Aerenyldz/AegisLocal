"""Optional IP reputation stub (AbuseIPDB / MaxMind — Phase 2/5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReputationResult:
    score: float  # 0 clean → 1 abusive
    source: str
    details: dict


def lookup_ip_reputation(ip: str) -> ReputationResult:
    """
    MVP stub: always clean. Wire AbuseIPDB/MaxMind behind feature flags later.
    Never call external APIs unless explicitly enabled (privacy / air-gap).
    """
    _ = ip
    return ReputationResult(score=0.0, source="disabled", details={})
