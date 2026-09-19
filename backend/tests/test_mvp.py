"""Unit tests for FFT features and scoring."""

from __future__ import annotations

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.fft_features import extract_fft_features
from app.ml.scoring import score_features
from app.services.pow import issue_challenge, meets_difficulty, verify_proof
import hashlib
import json


client = TestClient(app)


def _traj(kind: str, n: int = 120, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    t0 = 0.0
    points = []
    x, y = 0.0, 0.0
    for i in range(n):
        t = t0 + i * (1000.0 / 60.0)  # ~60 Hz
        if kind == "human":
            # 10 Hz micro-tremor + irregular velocity
            tremor = 0.35 * math.sin(2 * math.pi * 10 * (t / 1000.0))
            tremor += 0.15 * math.sin(2 * math.pi * 8.5 * (t / 1000.0) + 0.3)
            speed = 180 + 90 * math.sin(i / 9) + float(rng.normal(0, 25))
            angle = 0.4 + 0.05 * math.sin(i / 7) + float(rng.normal(0, 0.05))
            x += (speed * math.cos(angle)) * (1 / 60) + tremor
            y += (speed * math.sin(angle)) * (1 / 60) + 0.7 * tremor
        else:
            # Smooth cubic-ish Bezier sampling — low tremor
            u = i / (n - 1)
            x = 300 * (3 * (1 - u) ** 2 * u + u**3)
            y = 200 * (3 * (1 - u) * u**2 + u**3)
        points.append({"x": x, "y": y, "t": t})
    return points


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_metrics():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "aegis_http_requests_total" in r.text


def test_fft_human_separable_from_bot():
    human = extract_fft_features(_traj("human", seed=1))
    bot = extract_fft_features(_traj("bot", seed=1))
    # Composite: humans show higher jerk + lower path smoothness;
    # tremor_ratio on velocity residual should also favor humans.
    assert human.jerk_mean > bot.jerk_mean
    assert bot.path_smoothness > human.path_smoothness
    assert human.tremor_ratio >= bot.tremor_ratio * 0.9


def test_scoring_bot_higher_risk():
    h = score_features(extract_fft_features(_traj("human", seed=2)), webdriver=False)
    b = score_features(extract_fft_features(_traj("bot", seed=2)), webdriver=True)
    assert b.risk_score > h.risk_score


def test_analyze_endpoint_human():
    body = {
        "session_id": "testsession01",
        "points": _traj("human", seed=3),
        "webdriver": False,
    }
    r = client.post("/v1/analyze/mouse", json=body)
    assert r.status_code == 200
    data = r.json()
    assert "risk_score" in data
    assert "xai" in data
    assert data["decision"] in {"allow", "soft_challenge", "deny"}
    assert "pow_failed" in data["xai"]


def test_pow_difficulty_is_bounded():
    assert client.post("/v1/pow/challenge?difficulty=0").status_code == 422
    assert client.post("/v1/pow/challenge?difficulty=33").status_code == 422


def test_pow_issue_and_verify():
    ch = issue_challenge(difficulty=8)
    counter = 0
    while True:
        payload = f"{ch.nonce_prefix}:{ch.challenge_id}:{counter}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        if meets_difficulty(digest, 8):
            break
        counter += 1
        assert counter < 100_000
    assert verify_proof(ch.challenge_id, counter, digest) is True
    # replay must fail
    assert verify_proof(ch.challenge_id, counter, digest) is False


def test_pow_api():
    r = client.post("/v1/pow/challenge?difficulty=4")
    assert r.status_code == 200
    ch = r.json()
    counter = 0
    while True:
        payload = f"{ch['nonce_prefix']}:{ch['challenge_id']}:{counter}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        if meets_difficulty(digest, ch["difficulty"]):
            break
        counter += 1
    v = client.post(
        "/v1/pow/verify",
        json={"challenge_id": ch["challenge_id"], "counter": counter, "digest": digest},
    )
    assert v.status_code == 200
    assert v.json()["valid"] is True


def test_physics_challenge_is_single_use():
    issue = client.post("/v1/challenge/physics")
    assert issue.status_code == 200
    challenge_id = issue.json()["challenge_id"]
    issue_data = issue.json()
    points = [{"x": i * 2.0, "y": i * 1.5, "t": i * 100.0} for i in range(8)]
    canonical = json.dumps(
        {
            "challenge_id": challenge_id,
            "seed": issue_data["seed"],
            "gravity": issue_data["gravity"],
            "wind": issue_data["wind"],
            "points": points,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    body = {
        "challenge_id": challenge_id,
        "trajectory_hash": hashlib.sha256(canonical).hexdigest(),
        "duration_ms": 700,
        "points": points,
    }
    first = client.post("/v1/challenge/physics/verify", json=body)
    assert first.status_code == 200
    assert first.json() == {"valid": True, "reason": "accepted"}
    replay = client.post("/v1/challenge/physics/verify", json=body)
    assert replay.status_code == 200
    assert replay.json() == {"valid": False, "reason": "expired_or_unknown"}


def test_physics_verify_validates_input():
    response = client.post(
        "/v1/challenge/physics/verify",
        json={
            "challenge_id": "unknown",
            "trajectory_hash": "not-a-hash",
            "duration_ms": 100,
            "points": [{"x": 0, "y": 0, "t": 0}] * 8,
        },
    )
    assert response.status_code == 422


def test_physics_verify_rejects_hash_mismatch():
    issue = client.post("/v1/challenge/physics")
    challenge_id = issue.json()["challenge_id"]
    response = client.post(
        "/v1/challenge/physics/verify",
        json={
            "challenge_id": challenge_id,
            "trajectory_hash": "a" * 64,
            "duration_ms": 700,
            "points": [{"x": i, "y": i, "t": i * 100} for i in range(8)],
        },
    )
    assert response.json() == {"valid": False, "reason": "hash_mismatch"}
