"""Physics canvas challenge stub endpoints (Phase 4)."""

from __future__ import annotations

import secrets
import time

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.redis_client import get_store

router = APIRouter(prefix="/v1/challenge", tags=["challenge"])


class PhysicsIssueResponse(BaseModel):
    challenge_id: str
    seed: str
    gravity: float
    wind: float
    expires_at: int


class PhysicsVerifyRequest(BaseModel):
    challenge_id: str
    trajectory_hash: str
    duration_ms: int


class PhysicsVerifyResponse(BaseModel):
    valid: bool
    reason: str


@router.post("/physics", response_model=PhysicsIssueResponse)
async def issue_physics() -> PhysicsIssueResponse:
    settings = get_settings()
    challenge_id = secrets.token_hex(12)
    seed = secrets.token_hex(8)
    gravity = 9.81
    wind = (int(seed[:2], 16) / 255.0) * 2 - 1  # [-1, 1]
    expires = int(time.time()) + settings.pow_ttl_seconds
    store = get_store()
    store.setex(f"phys:{challenge_id}", settings.pow_ttl_seconds, f"{seed}|{gravity}|{wind}")
    return PhysicsIssueResponse(
        challenge_id=challenge_id,
        seed=seed,
        gravity=gravity,
        wind=wind,
        expires_at=expires,
    )


@router.post("/physics/verify", response_model=PhysicsVerifyResponse)
async def verify_physics(body: PhysicsVerifyRequest) -> PhysicsVerifyResponse:
    store = get_store()
    raw = store.get(f"phys:{body.challenge_id}")
    if raw is None:
        return PhysicsVerifyResponse(valid=False, reason="expired_or_unknown")
    if body.duration_ms < 400:
        return PhysicsVerifyResponse(valid=False, reason="too_fast")
    if len(body.trajectory_hash) < 16:
        return PhysicsVerifyResponse(valid=False, reason="invalid_hash")
    store.delete(f"phys:{body.challenge_id}")
    return PhysicsVerifyResponse(valid=True, reason="accepted_stub")
