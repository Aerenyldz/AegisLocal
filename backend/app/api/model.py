from fastapi import APIRouter

from app.core.config import get_settings
from app.ml.onnx_runtime import OnnxScorer

router = APIRouter(prefix="/v1/model", tags=["model"])


@router.get("/status")
async def model_status() -> dict[str, object]:
    settings = get_settings()
    shadow = OnnxScorer(settings.onnx_model_path)
    available = shadow.load()
    return {
        "active_model": "heuristic-0.1.0",
        "active_model_mutable": False,
        "shadow_enabled": settings.onnx_shadow_enabled,
        "shadow_model": settings.onnx_model_version if available else None,
        "shadow_available": available,
        "shadow_model_hash": shadow.model_hash if available else None,
        "load_error": shadow.load_error,
        "promotion": "manual_only",
    }
