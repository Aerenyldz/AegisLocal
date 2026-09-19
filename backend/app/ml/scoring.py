"""Heuristic + XAI risk scoring for MVP (pre-ONNX Isolation Forest)."""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.fft_features import FFTFeatureResult


@dataclass(frozen=True)
class ScoreBreakdown:
    risk_score: float
    label: str  # human_likely | gray | bot_likely
    xai: dict[str, float]
    reasons: list[str]


def score_features(
    features: FFTFeatureResult,
    *,
    webdriver: bool = False,
    pow_ok: bool = True,
) -> ScoreBreakdown:
    """
    Transparent weighted rules for MVP.

    Higher risk ⇒ more bot-like.
    Weights are intentionally documented for XAI matrix export.
    """
    xai: dict[str, float] = {}
    reasons: list[str] = []

    # Weak physiological tremor band → bot-like
    # Expected human tremor_ratio roughly 0.05–0.35 depending on device
    if features.tremor_ratio < 0.04:
        xai["low_tremor_energy"] = 0.28
        reasons.append("Tremor-band (7–15 Hz) energy unusually low")
    elif features.tremor_ratio > 0.45:
        xai["excess_high_freq_noise"] = 0.08
        reasons.append("Excess high-frequency energy (possible synthetic noise)")
    else:
        xai["tremor_present"] = -0.12
        reasons.append("Physiological tremor band energy present")

    # Overly smooth path
    if features.path_smoothness > 0.72:
        xai["path_too_smooth"] = 0.22
        reasons.append("Path curvature variance too low (Bezier-like)")
    else:
        xai["path_natural"] = -0.08

    # Velocity coefficient of variation: humans are irregular
    if features.velocity_cv < 0.25:
        xai["velocity_too_regular"] = 0.18
        reasons.append("Velocity profile overly regular")
    elif features.velocity_cv > 1.8:
        xai["velocity_erratic"] = 0.06
        reasons.append("Velocity highly erratic")
    else:
        xai["velocity_natural"] = -0.06

    # Near-zero jerk often indicates interpolated curves
    if features.jerk_mean < 50:
        xai["low_jerk"] = 0.12
        reasons.append("Mean jerk near-zero (scripted interpolation)")
    else:
        xai["jerk_present"] = -0.05

    if webdriver:
        xai["navigator_webdriver"] = 0.35
        reasons.append("navigator.webdriver asserted true")

    if not pow_ok:
        xai["pow_failed"] = 0.40
        reasons.append("Proof-of-Work verification failed")

    raw = 0.42 + sum(xai.values())  # baseline prior
    risk = float(max(0.0, min(1.0, raw)))

    if risk < 0.36:
        label = "human_likely"
    elif risk < 0.66:
        label = "gray"
    else:
        label = "bot_likely"

    return ScoreBreakdown(risk_score=risk, label=label, xai=xai, reasons=reasons)
