from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.pow import issue_challenge, verify_proof

router = APIRouter(prefix="/v1/pow", tags=["pow"])


class ChallengeResponse(BaseModel):
    challenge_id: str
    nonce_prefix: str
    difficulty: int
    issued_at: int
    expires_at: int
    algorithm: str = "sha256-leading-zero-bits"


class VerifyRequest(BaseModel):
    challenge_id: str
    counter: int = Field(..., ge=0)
    digest: str = Field(..., min_length=64, max_length=64)


class VerifyResponse(BaseModel):
    valid: bool


@router.post("/challenge", response_model=ChallengeResponse)
async def create_challenge(
    difficulty: int | None = Query(default=None, ge=1, le=32),
) -> ChallengeResponse:
    ch = issue_challenge(difficulty)
    return ChallengeResponse(
        challenge_id=ch.challenge_id,
        nonce_prefix=ch.nonce_prefix,
        difficulty=ch.difficulty,
        issued_at=ch.issued_at,
        expires_at=ch.expires_at,
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify(body: VerifyRequest) -> VerifyResponse:
    ok = verify_proof(body.challenge_id, body.counter, body.digest)
    return VerifyResponse(valid=ok)
