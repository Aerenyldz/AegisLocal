"""FFT-based micro-tremor feature extraction from mouse trajectories."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.fft import rfft, rfftfreq


@dataclass(frozen=True)
class FFTFeatureResult:
    sampling_hz: float
    tremor_band_energy: float
    total_energy: float
    tremor_ratio: float
    spectral_centroid_hz: float
    peak_frequency_hz: float
    velocity_cv: float
    jerk_mean: float
    path_smoothness: float
    feature_vector: list[float]


def _as_array(points: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(points) < 8:
        raise ValueError("At least 8 mouse points required for FFT analysis")

    t = np.asarray([p["t"] for p in points], dtype=np.float64)
    x = np.asarray([p["x"] for p in points], dtype=np.float64)
    y = np.asarray([p["y"] for p in points], dtype=np.float64)

    # Ensure strictly increasing time (ms → s)
    order = np.argsort(t)
    t, x, y = t[order], x[order], y[order]
    t = (t - t[0]) / 1000.0
    # Deduplicate identical timestamps
    mask = np.concatenate([[True], np.diff(t) > 1e-6])
    return t[mask], x[mask], y[mask]


def extract_fft_features(points: list[dict]) -> FFTFeatureResult:
    """
    Convert pointer trajectory to frequency-domain features.

    Humans exhibit low-amplitude physiological micro-tremor (~8–12 Hz).
    Scripted Bézier bots tend to produce overly smooth paths with weak
    energy in that band and unnatural velocity regularity.
    """
    t, x, y = _as_array(points)
    if len(t) < 8:
        raise ValueError("Insufficient unique timestamps after dedupe")

    dt = np.diff(t)
    sampling_hz = float(1.0 / np.median(dt)) if np.median(dt) > 0 else 0.0

    dx = np.diff(x)
    dy = np.diff(y)
    vel = np.hypot(dx, dy) / np.maximum(dt, 1e-6)
    acc = np.diff(vel) / np.maximum(dt[1:], 1e-6)
    jerk = np.diff(acc) / np.maximum(dt[2:], 1e-6) if len(acc) > 1 else np.array([0.0])

    # Micro-tremor is clearest on velocity residuals (not gross path shape).
    # Detrend velocity with a moving mean, then FFT the residual.
    t_vel = t[1:]
    window = max(5, min(15, len(vel) // 4 * 2 + 1))
    kernel = np.ones(window) / window
    vel_smooth = np.convolve(vel, kernel, mode="same")
    residual = vel - vel_smooth

    n = min(256, max(32, len(residual)))
    t_uniform = np.linspace(t_vel[0], t_vel[-1], n)
    residual_u = np.interp(t_uniform, t_vel, residual)
    residual_u = residual_u - np.mean(residual_u)

    spectrum = np.abs(rfft(residual_u))
    freqs = rfftfreq(n, d=(t_uniform[1] - t_uniform[0]))
    power = spectrum**2
    total_energy = float(np.sum(power) + 1e-12)

    tremor_mask = (freqs >= 7.0) & (freqs <= 15.0)
    tremor_energy = float(np.sum(power[tremor_mask]))
    tremor_ratio = tremor_energy / total_energy

    spectral_centroid = float(np.sum(freqs * power) / total_energy)
    peak_frequency = float(freqs[int(np.argmax(power))]) if len(power) else 0.0

    vel_mean = float(np.mean(vel) + 1e-12)
    velocity_cv = float(np.std(vel) / vel_mean)
    jerk_mean = float(np.mean(np.abs(jerk)))
    # Lower curvature variance ⇒ smoother (more bot-like) path
    curvature = np.abs(np.diff(np.arctan2(dy, dx + 1e-12)))
    path_smoothness = float(1.0 / (1.0 + np.std(curvature)))

    feature_vector = [
        tremor_ratio,
        tremor_energy,
        spectral_centroid,
        peak_frequency,
        velocity_cv,
        jerk_mean,
        path_smoothness,
        sampling_hz,
    ]

    return FFTFeatureResult(
        sampling_hz=sampling_hz,
        tremor_band_energy=tremor_energy,
        total_energy=total_energy,
        tremor_ratio=tremor_ratio,
        spectral_centroid_hz=spectral_centroid,
        peak_frequency_hz=peak_frequency,
        velocity_cv=velocity_cv,
        jerk_mean=jerk_mean,
        path_smoothness=path_smoothness,
        feature_vector=feature_vector,
    )
