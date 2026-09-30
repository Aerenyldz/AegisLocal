"""Generate a deterministic letter-like bot trajectory and call the analyze API."""

from __future__ import annotations

import argparse
import hashlib
import os

import httpx

API = os.environ.get("AEGIS_API", "http://127.0.0.1:8000")


def letter_path(letter: str, n: int = 120) -> list[dict[str, float]]:
    points = []
    for i in range(n):
        u = i / (n - 1)
        points.append({"x": u, "y": (0.25 + 0.5 * u) if letter == "A" else u, "t": i * 1000 / 60})
    return points


def solve_pow(client: httpx.Client) -> dict[str, int | str]:
    response = client.post("/v1/pow/challenge?difficulty=8")
    response.raise_for_status()
    challenge = response.json()
    for counter in range(5_000_000):
        digest = hashlib.sha256(
            f"{challenge['nonce_prefix']}:{challenge['challenge_id']}:{counter}".encode()
        ).hexdigest()
        raw = bytes.fromhex(digest)
        full, rem = divmod(challenge["difficulty"], 8)
        if raw[:full] == b"\0" * full and (
            not rem or raw[full] & (0xFF << (8 - rem) & 0xFF) == 0
        ):
            return {"challenge_id": challenge["challenge_id"], "counter": counter, "digest": digest}
    raise RuntimeError("PoW limit exceeded")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--letter", default="A")
    args = parser.parse_args()
    with httpx.Client(base_url=API, timeout=30) as client:
        response = client.post("/v1/analyze/mouse", json={
            "session_id": "letter-bot-probe",
            "points": letter_path(args.letter.upper()),
            "webdriver": True,
            "fingerprint": {"source": "letter-bot-probe", "letter": args.letter.upper()},
            "pow": solve_pow(client),
        })
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    main()
