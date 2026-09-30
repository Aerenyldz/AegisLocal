"""Short-lived, single-use tokens issued after a verified challenge."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from app.core.config import get_settings
from app.core.redis_client import get_store


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_token(*, session_id: str, endpoint: str, policy: str) -> str:
    settings = get_settings()
    issued_at = int(time.time())
    payload = {
        "jti": secrets.token_hex(16),
        "session_id": session_id,
        "endpoint": endpoint,
        "policy": policy,
        "iat": issued_at,
        "exp": issued_at + settings.challenge_token_ttl_seconds,
    }
    encoded = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.challenge_token_secret.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded}.{_encode(signature)}"


def verify_and_consume(
    token: str,
    *,
    session_id: str,
    endpoint: str,
    policy: str,
) -> tuple[bool, str]:
    try:
        encoded, supplied_signature = token.split(".", 1)
        payload = json.loads(_decode(encoded))
        expected_signature = hmac.new(
            get_settings().challenge_token_secret.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        )
        if not hmac.compare_digest(
            expected_signature.digest(), _decode(supplied_signature)
        ):
            return False, "invalid_signature"
        if int(payload["exp"]) <= int(time.time()):
            return False, "expired"
        if (
            payload["session_id"] != session_id
            or payload["endpoint"] != endpoint
            or payload["policy"] != policy
        ):
            return False, "context_mismatch"
        jti = str(payload["jti"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, binascii.Error):
        return False, "malformed"

    store = get_store()
    replay_key = f"challenge-token-used:{jti}"
    if store.get(replay_key) is not None:
        return False, "already_used"
    remaining = max(1, int(payload["exp"]) - int(time.time()))
    store.setex(replay_key, remaining, "1")
    return True, "accepted"
