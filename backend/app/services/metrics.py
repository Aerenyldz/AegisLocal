from prometheus_client import Counter, Histogram


DECISIONS = Counter(
    "aegis_decisions_total",
    "Risk decisions returned by the analysis endpoints.",
    ("endpoint", "policy", "enforcement", "mode"),
)
DECISION_LATENCY = Histogram(
    "aegis_decision_duration_seconds",
    "Decision analysis duration in seconds.",
    ("endpoint",),
)
