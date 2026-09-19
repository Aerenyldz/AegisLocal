"""Physics canvas challenge stub endpoints (Phase 4)."""

from __future__ import annotations

import secrets
import time
import hashlib
import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

from app.core.config import get_settings
from app.core.redis_client import get_store
from app.services.rate_limit import check_rate_limit

router = APIRouter(prefix="/v1/challenge", tags=["challenge"])


class PhysicsIssueResponse(BaseModel):
    challenge_id: str
    seed: str
    gravity: float
    wind: float
    expires_at: int


class PhysicsVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str
    trajectory_hash: str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    duration_ms: int = Field(..., ge=400, le=120_000)
    points: list["PhysicsPoint"] = Field(..., min_length=8, max_length=2000)


class PhysicsPoint(BaseModel):
    x: float = Field(..., ge=-100_000, le=100_000)
    y: float = Field(..., ge=-100_000, le=100_000)
    t: float = Field(..., ge=0, le=120_000)


class PhysicsVerifyResponse(BaseModel):
    valid: bool
    reason: str


@router.post("/physics", response_model=PhysicsIssueResponse)
async def issue_physics(request: Request) -> PhysicsIssueResponse:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = check_rate_limit(f"challenge:{client_ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
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
    seed, gravity_s, wind_s = str(raw).split("|")
    if body.points[-1].t - body.points[0].t < 400:
        return PhysicsVerifyResponse(valid=False, reason="too_fast")
    if abs((body.points[-1].t - body.points[0].t) - body.duration_ms) > 250:
        return PhysicsVerifyResponse(valid=False, reason="duration_mismatch")
    if any(left.t > right.t for left, right in zip(body.points, body.points[1:])):
        return PhysicsVerifyResponse(valid=False, reason="non_monotonic_time")
    canonical = json.dumps(
        {
            "challenge_id": body.challenge_id,
            "seed": seed,
            "gravity": float(gravity_s),
            "wind": float(wind_s),
            "points": [point.model_dump() for point in body.points],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    expected_hash = hashlib.sha256(canonical).hexdigest()
    if not secrets.compare_digest(expected_hash, body.trajectory_hash.lower()):
        return PhysicsVerifyResponse(valid=False, reason="hash_mismatch")
    store.delete(f"phys:{body.challenge_id}")
    return PhysicsVerifyResponse(valid=True, reason="accepted")
