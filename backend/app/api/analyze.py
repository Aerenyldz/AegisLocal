from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.ml.fft_features import extract_fft_features
from app.ml.scoring import score_features
from app.services.rate_limit import check_rate_limit
from app.services.policy import evaluate_policy
from app.services.audit import record_decision

router = APIRouter(prefix="/v1/analyze", tags=["analyze"])


class MousePoint(BaseModel):
    x: float
    y: float
    t: float = Field(..., description="Client timestamp in milliseconds")
    vx: float | None = None
    vy: float | None = None
    ax: float | None = None
    ay: float | None = None


class AnalyzeMouseRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=128)
    points: list[MousePoint] = Field(..., min_length=8, max_length=5000)
    webdriver: bool = False
    fingerprint: dict[str, Any] | None = None
    policy: str = Field(default="default", min_length=1, max_length=64)
    mode: Literal["live", "shadow"] = "live"
    pow: dict[str, Any] | None = Field(
        default=None,
        description="Optional {challenge_id, counter, digest}",
    )


class AnalyzeMouseResponse(BaseModel):
    decision: Literal["allow", "soft_challenge", "deny"]
    risk_score: float
    label: str
    xai: dict[str, float]
    reasons: list[str]
    features: dict[str, float]
    rate_limit_remaining: int
    policy: str
    mode: Literal["live", "shadow"]
    enforcement: Literal["allow", "challenge", "throttle", "deny"]
    model_version: str


class LoginAnalyzeRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=128)
    points: list[MousePoint] = Field(default_factory=list, max_length=5000)
    webdriver: bool = False
    policy: str = Field(default="login_protection", min_length=1, max_length=64)
    mode: Literal["live", "shadow"] = "live"


def _policy_response(
    scored,
    *,
    policy: str,
    mode: Literal["live", "shadow"],
    rate_limit_remaining: int,
) -> AnalyzeMouseResponse:
    settings = get_settings()
    policy_decision = evaluate_policy(scored.risk_score, policy_name=policy, mode=mode)
    if scored.risk_score <= settings.allow_threshold:
        decision: Literal["allow", "soft_challenge", "deny"] = "allow"
    elif scored.risk_score <= settings.challenge_threshold:
        decision = "soft_challenge"
    else:
        decision = "deny"
    return AnalyzeMouseResponse(
        decision=decision,
        risk_score=scored.risk_score,
        label=scored.label,
        xai=scored.xai,
        reasons=scored.reasons,
        features={},
        rate_limit_remaining=rate_limit_remaining,
        policy=policy_decision.policy,
        mode=policy_decision.mode,
        enforcement=policy_decision.enforcement,
        model_version="heuristic-0.1.0",
    )


@router.post("/mouse", response_model=AnalyzeMouseResponse)
async def analyze_mouse(
    body: AnalyzeMouseRequest,
    request: Request,
    x_forwarded_for: str | None = Header(default=None),
) -> AnalyzeMouseResponse:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    if settings.trust_proxy_headers and x_forwarded_for:
        client_ip = x_forwarded_for.split(",")[0].strip()
    allowed, remaining = check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    pow_ok = False
    if body.pow:
        from app.services.pow import verify_proof

        try:
            pow_ok = verify_proof(
                str(body.pow["challenge_id"]),
                int(body.pow["counter"]),
                str(body.pow["digest"]),
            )
        except (KeyError, TypeError, ValueError):
            pow_ok = False

    try:
        feats = extract_fft_features([p.model_dump() for p in body.points])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    scored = score_features(feats, webdriver=body.webdriver, pow_ok=pow_ok)
    try:
        policy_decision = evaluate_policy(
            scored.risk_score,
            policy_name=body.policy,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if scored.risk_score <= settings.allow_threshold:
        decision: Literal["allow", "soft_challenge", "deny"] = "allow"
    elif scored.risk_score <= settings.challenge_threshold:
        decision = "soft_challenge"
    else:
        decision = "deny"

    record_decision(
        endpoint="/v1/analyze/mouse",
        session_id=body.session_id,
        scored=scored,
        policy=policy_decision,
        features={
            "tremor_ratio": feats.tremor_ratio,
            "tremor_band_energy": feats.tremor_band_energy,
            "spectral_centroid_hz": feats.spectral_centroid_hz,
            "peak_frequency_hz": feats.peak_frequency_hz,
            "velocity_cv": feats.velocity_cv,
            "jerk_mean": feats.jerk_mean,
            "path_smoothness": feats.path_smoothness,
            "sampling_hz": feats.sampling_hz,
        },
    )
    return AnalyzeMouseResponse(
        decision=decision,
        risk_score=scored.risk_score,
        label=scored.label,
        xai=scored.xai,
        reasons=scored.reasons,
        features={
            "tremor_ratio": feats.tremor_ratio,
            "tremor_band_energy": feats.tremor_band_energy,
            "spectral_centroid_hz": feats.spectral_centroid_hz,
            "peak_frequency_hz": feats.peak_frequency_hz,
            "velocity_cv": feats.velocity_cv,
            "jerk_mean": feats.jerk_mean,
            "path_smoothness": feats.path_smoothness,
            "sampling_hz": feats.sampling_hz,
        },
        rate_limit_remaining=remaining,
        policy=policy_decision.policy,
        mode=policy_decision.mode,
        enforcement=policy_decision.enforcement,
        model_version="heuristic-0.1.0",
    )


@router.post("/login", response_model=AnalyzeMouseResponse)
async def analyze_login(body: LoginAnalyzeRequest, request: Request) -> AnalyzeMouseResponse:
    """Analyze a login interaction, including keyboard-only/no-pointer flows."""
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining = check_rate_limit(f"login:{client_ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if len(body.points) >= 8:
        try:
            feats = extract_fft_features([p.model_dump() for p in body.points])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        scored = score_features(feats, webdriver=body.webdriver, pow_ok=True)
        try:
            response = _policy_response(
                scored,
                policy=body.policy,
                mode=body.mode,
                rate_limit_remaining=remaining,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        response.features = {
            "tremor_ratio": feats.tremor_ratio,
            "velocity_cv": feats.velocity_cv,
            "path_smoothness": feats.path_smoothness,
        }
        record_decision(
            endpoint="/v1/analyze/login",
            session_id=body.session_id,
            scored=scored,
            policy=evaluate_policy(scored.risk_score, policy_name=body.policy, mode=body.mode),
        )
        return response

    # A login must remain usable with keyboard, screen reader, or touch input.
    # Absence of pointer data is evidence, not proof of automation.
    from app.ml.scoring import ScoreBreakdown

    xai = {"no_pointer_signal": 0.04}
    reasons = ["No pointer trajectory; keyboard/touch flow remains supported"]
    if body.webdriver:
        xai["navigator_webdriver"] = 0.35
        reasons.append("navigator.webdriver asserted true")
    raw = min(1.0, 0.30 + sum(xai.values()))
    scored = ScoreBreakdown(
        risk_score=raw,
        label="human_likely" if raw < 0.36 else ("gray" if raw < 0.66 else "bot_likely"),
        xai=xai,
        reasons=reasons,
    )
    try:
        response = _policy_response(
            scored,
            policy=body.policy,
            mode=body.mode,
            rate_limit_remaining=remaining,
        )
        record_decision(
            endpoint="/v1/analyze/login",
            session_id=body.session_id,
            scored=scored,
            policy=evaluate_policy(scored.risk_score, policy_name=body.policy, mode=body.mode),
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
