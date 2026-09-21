from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import PlainTextResponse
import json

from app.services.audit import evaluation, label_event, recent_events, summary

router = APIRouter(prefix="/v1/audit", tags=["audit"])


class LabelRequest(BaseModel):
    operator_label: str = Field(..., pattern="^(human|bot|uncertain)$")


@router.get("/recent")
async def get_recent_events(
    limit: int = Query(default=50, ge=1, le=100),
    policy: str | None = Query(default=None, min_length=1, max_length=64),
    enforcement: str | None = Query(default=None, min_length=1, max_length=32),
) -> dict[str, object]:
    return {
        "events": recent_events(
            limit,
            policy=policy,
            enforcement=enforcement,
        )
    }


@router.get("/summary")
async def get_summary() -> dict[str, object]:
    return summary()


@router.get("/evaluation")
async def get_evaluation(
    threshold: float = Query(default=0.66, ge=0, le=1),
) -> dict[str, object]:
    return evaluation(threshold)


@router.post("/{event_id}/label")
async def set_label(event_id: str, body: LabelRequest) -> dict[str, object]:
    try:
        result = label_event(event_id, body.operator_label)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return result


@router.get("/export", response_class=PlainTextResponse)
async def export_labeled_dataset() -> str:
    rows = [
        event
        for event in recent_events(10000)
        if event["operator_label"] in {"human", "bot"}
    ]
    return "\n".join(
        json.dumps(
            {
                "event_id": event["event_id"],
                "label": event["operator_label"],
                "risk_score": event["risk_score"],
                "features": event["features"],
                "webdriver": "navigator_webdriver" in event["reasons"],
                "policy": event["policy"],
                "model_version": event["model_version"],
            },
            ensure_ascii=False,
        )
        for event in rows
    )
