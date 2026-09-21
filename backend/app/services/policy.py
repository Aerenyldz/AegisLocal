"""Endpoint policy and enforcement decisions for the local gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings

PolicyMode = Literal["live", "shadow"]
Enforcement = Literal["allow", "challenge", "throttle", "deny"]


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    challenge_action: Enforcement
    deny_action: Enforcement


@dataclass(frozen=True)
class PolicyDecision:
    policy: str
    mode: PolicyMode
    enforcement: Enforcement


_POLICIES = {
    "default": PolicyProfile(
        name="default",
        challenge_action="challenge",
        deny_action="deny",
    ),
    "login_protection": PolicyProfile(
        name="login_protection",
        challenge_action="challenge",
        deny_action="throttle",
    ),
    "high_assurance": PolicyProfile(
        name="high_assurance",
        challenge_action="challenge",
        deny_action="deny",
    ),
}


def get_policy(name: str) -> PolicyProfile:
    try:
        return _POLICIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown policy: {name}") from exc


def evaluate_policy(
    risk_score: float,
    *,
    policy_name: str = "default",
    mode: PolicyMode = "live",
) -> PolicyDecision:
    """Translate a risk class into an endpoint action.

    Shadow mode deliberately preserves the observed risk class in the caller
    while forcing the effective action to allow.
    """
    policy = get_policy(policy_name)
    settings = get_settings()

    if risk_score <= settings.allow_threshold:
        action: Enforcement = "allow"
    elif risk_score <= settings.challenge_threshold:
        action = policy.challenge_action
    else:
        action = policy.deny_action

    if mode == "shadow":
        action = "allow"

    return PolicyDecision(policy=policy.name, mode=mode, enforcement=action)
