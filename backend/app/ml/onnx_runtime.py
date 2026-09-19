"""ONNX Runtime placeholder — wired in Phase 3."""

from __future__ import annotations

from pathlib import Path


class OnnxScorer:
    """Loads an IsolationForest/GRU ONNX model when present."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self._session = None

    @property
    def available(self) -> bool:
        return self._session is not None

    def load(self) -> bool:
        if self.model_path is None or not self.model_path.exists():
            return False
        try:
            import onnxruntime as ort  # optional dep in later phase

            self._session = ort.InferenceSession(
                str(self.model_path), providers=["CPUExecutionProvider"]
            )
            return True
        except Exception:
            self._session = None
            return False

    def predict_anomaly(self, feature_vector: list[float]) -> float | None:
        if self._session is None:
            return None
        import numpy as np

        inp = np.asarray([feature_vector], dtype=np.float32)
        input_name = self._session.get_inputs()[0].name
        out = self._session.run(None, {input_name: inp})[0]
        # Map model output to [0,1] risk — model-specific; placeholder
        return float(max(0.0, min(1.0, abs(out.flatten()[0]))))
