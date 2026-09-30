from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request

from app.core.config import get_settings


def require_service_key(
    request: Request,
    x_aegis_api_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.api_key_required:
        return
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="API key authentication is misconfigured")
    if not x_aegis_api_key or not hmac.compare_digest(x_aegis_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def client_ip(request: Request, forwarded_for: str | None) -> str:
    settings = get_settings()
    remote = request.client.host if request.client else "unknown"
    trusted = {item.strip() for item in settings.trusted_proxy_ips.split(",") if item.strip()}
    if (
        settings.trust_proxy_headers
        and remote in trusted
        and forwarded_for
    ):
        return forwarded_for.split(",", 1)[0].strip()
    return remote
