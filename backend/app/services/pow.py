"""PoW challenge issue + verify (mirrors Rust/WASM client algorithm)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.redis_client import get_store


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def meets_difficulty(digest_hex: str, difficulty_bits: int) -> bool:
    """Require `difficulty_bits` leading zero bits in the SHA-256 digest."""
    if difficulty_bits <= 0:
        return True
    full_bytes, rem = divmod(difficulty_bits, 8)
    digest = bytes.fromhex(digest_hex)
    if any(b != 0 for b in digest[:full_bytes]):
        return False
    if rem == 0:
        return True
    mask = 0xFF << (8 - rem) & 0xFF
    return (digest[full_bytes] & mask) == 0


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    nonce_prefix: str
    difficulty: int
    issued_at: int
    expires_at: int


def issue_challenge(difficulty: int | None = None) -> Challenge:
    settings = get_settings()
    diff = difficulty if difficulty is not None else settings.pow_default_difficulty
    challenge_id = secrets.token_hex(16)
    nonce_prefix = secrets.token_hex(8)
    now = int(time.time())
    expires = now + settings.pow_ttl_seconds

    store = get_store()
    store.setex(
        f"pow:{challenge_id}",
        settings.pow_ttl_seconds,
        f"{nonce_prefix}|{diff}|{expires}",
    )
    return Challenge(
        challenge_id=challenge_id,
        nonce_prefix=nonce_prefix,
        difficulty=diff,
        issued_at=now,
        expires_at=expires,
    )


def verify_proof(challenge_id: str, counter: int, digest_hex: str) -> bool:
    store = get_store()
    raw = store.get(f"pow:{challenge_id}")
    if raw is None:
        return False

    nonce_prefix, diff_s, expires_s = str(raw).split("|")
    difficulty = int(diff_s)
    expires = int(expires_s)
    if time.time() > expires:
        store.delete(f"pow:{challenge_id}")
        return False

    payload = f"{nonce_prefix}:{challenge_id}:{counter}".encode()
    expected = _sha256_hex(payload)
    if not hmac.compare_digest(expected, digest_hex.lower()):
        return False
    if not meets_difficulty(digest_hex, difficulty):
        return False

    # Single-use
    store.delete(f"pow:{challenge_id}")
    return True
