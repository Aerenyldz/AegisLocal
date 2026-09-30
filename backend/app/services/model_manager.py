"""Active and shadow scorer coordination.

The heuristic scorer remains the active model until an ONNX model is explicitly
configured and promoted. An available ONNX model can run in shadow mode so its
output is measurable without changing enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.ml.onnx_runtime import OnnxScorer
from app.ml.scoring import ScoreBreakdown, score_features
from app.ml.fft_features import FFTFeatureResult


@dataclass(frozen=True)
class ModelScores:
    active: ScoreBreakdown
    shadow_risk_score: float | None
    active_model_version: str
    shadow_model_version: str | None


def _vector(features: FFTFeatureResult) -> list[float]:
    return [
        features.tremor_ratio,
        features.tremor_band_energy,
        features.spectral_centroid_hz,
        features.peak_frequency_hz,
        features.velocity_cv,
        features.jerk_mean,
        features.path_smoothness,
        features.sampling_hz,
    ]


def score_with_shadow(
    features: FFTFeatureResult,
    *,
    webdriver: bool,
    pow_ok: bool,
) -> ModelScores:
    settings = get_settings()
    active = score_features(features, webdriver=webdriver, pow_ok=pow_ok)
    shadow = OnnxScorer(settings.onnx_model_path)
    if not settings.onnx_shadow_enabled or not shadow.load():
        return ModelScores(
            active=active,
            shadow_risk_score=None,
            active_model_version="heuristic-0.1.0",
            shadow_model_version=None,
        )
    return ModelScores(
        active=active,
        shadow_risk_score=shadow.predict_anomaly(_vector(features)),
        active_model_version="heuristic-0.1.0",
        shadow_model_version=settings.onnx_model_version,
    )
