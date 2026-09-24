"""Purpose/transport guard within the existing Shared AI Provider Control boundary.

This is not a router, credential store, quota claim or execution authority. Only
trusted server config selects profiles. Native agent work stays with the existing
Executive/native path; generic product inference cannot consume its subscriptions.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

SCHEMA = "mastermind.provider_workloads.v1"
DECISION_SCHEMA = "mastermind.provider_workload_decision.v1"
HOST_PROFILE_ENV = "MM_PROVIDER_WORKLOAD_PROFILE"
DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config/provider_workloads.v1.json"
MAX_POLICY_BYTES = 65536
_PROFILE_ID = re.compile(r"[a-z][a-z0-9_]{0,63}")
# These are the existing builder's transport adapters, not model rankings or
# entitlement claims. New transports require a reviewed adapter and this guard.
_INFERENCE_PROVIDERS = frozenset({"anthropic", "deepseek", "ollama"})
_KNOWN_PROVIDERS = _INFERENCE_PROVIDERS | {"oauth", "codex"}


class ProviderWorkloadPolicyError(ValueError):
    """Bounded configuration refusal; messages never echo document/input values."""


def _refuse(code: str) -> NoReturn:
    raise ProviderWorkloadPolicyError(code)


def _closed(value: Any, fields: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        _refuse("WORKLOAD_POLICY_FIELDS_INVALID")


def _profile_id(value: Any) -> str:
    if not isinstance(value, str) or _PROFILE_ID.fullmatch(value) is None:
        _refuse("WORKLOAD_PROFILE_INVALID")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _refuse("WORKLOAD_POLICY_DUPLICATE_KEY")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    _refuse("WORKLOAD_POLICY_JSON_INVALID")


def _bounded_integer(value: str) -> int:
    # Revisions are the only permitted integers and fit in signed 32 bits.
    # Bound before int(), independent of interpreter-wide digit-limit settings.
    if len(value.lstrip("-")) > 10:
        _refuse("WORKLOAD_POLICY_JSON_INVALID")
    return int(value)


def validate_policy(document: Any) -> None:
    """Validate a closed, credential-free, transport-only policy document."""
    _closed(document, {"schema", "revision", "owner_program", "profiles"})
    if document["schema"] != SCHEMA:
        _refuse("WORKLOAD_POLICY_SCHEMA_INVALID")
    if document["owner_program"] != "shared-ai-provider-control":
        _refuse("WORKLOAD_POLICY_OWNER_INVALID")
    revision = document["revision"]
    if type(revision) is not int or not 1 <= revision <= 2147483647:
        _refuse("WORKLOAD_POLICY_REVISION_INVALID")
    profiles = document["profiles"]
    if not isinstance(profiles, dict) or not 1 <= len(profiles) <= 64:
        _refuse("WORKLOAD_POLICY_PROFILES_INVALID")
    for name, row in profiles.items():
        _profile_id(name)
        _closed(row, {"execution_surface", "allowed_providers"})
        surface = row["execution_surface"]
        if surface not in ("inference", "native_agent"):
            _refuse("WORKLOAD_POLICY_SURFACE_INVALID")
        providers = row["allowed_providers"]
        if not isinstance(providers, list) or len(providers) > len(_INFERENCE_PROVIDERS):
            _refuse("WORKLOAD_POLICY_PROVIDERS_INVALID")
        if any(not isinstance(p, str) or p not in _INFERENCE_PROVIDERS for p in providers):
            _refuse("WORKLOAD_POLICY_PROVIDERS_INVALID")
        if len(set(providers)) != len(providers):
            _refuse("WORKLOAD_POLICY_PROVIDERS_INVALID")
        if surface == "native_agent" and providers:
            _refuse("WORKLOAD_POLICY_NATIVE_TRANSPORT_INVALID")


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict:
    """Read one bounded snapshot. No process cache can retain a retired policy."""
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(MAX_POLICY_BYTES + 1)
    except OSError:
        raise ProviderWorkloadPolicyError("WORKLOAD_POLICY_UNAVAILABLE") from None
    if len(raw) > MAX_POLICY_BYTES:
        _refuse("WORKLOAD_POLICY_TOO_LARGE")
    try:
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant, parse_int=_bounded_integer,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ProviderWorkloadPolicyError("WORKLOAD_POLICY_JSON_INVALID") from None
    validate_policy(document)
    return document


@dataclass(frozen=True)
class WorkloadDecision:
    policy_revision: int
    policy_hash: str
    profiles: tuple[str, ...]
    allowed_order: tuple[str, ...]
    denied_order: tuple[str, ...]

    def receipt(self) -> dict[str, Any]:
        """Content identity only: not authenticated freshness, entitlement or claim."""
        return {
            "schema": DECISION_SCHEMA,
            "policy_revision": self.policy_revision,
            "policy_hash": self.policy_hash,
            "profiles": list(self.profiles),
            "execution_surface": "inference",
            "allowed_order": list(self.allowed_order),
            "denied_order": list(self.denied_order),
        }


def decide_workload(
    cfg: Mapping[str, Any], *, host_profile: str | None = None,
    policy_path: Path | None = None,
) -> WorkloadDecision | None:
    """Intersect trusted host/caller profiles before any credential construction.

    None is the deliberate legacy migration state, only when both selectors are
    absent. `policy_path` is an internal/test dependency, never a caller-config key.
    This function does no provider/network/credential access or lifecycle mutation.
    """
    if "workload_profile" not in cfg and host_profile is None:
        return None
    names: list[str] = []
    if host_profile is not None:
        names.append(_profile_id(host_profile))
    if "workload_profile" in cfg:
        name = _profile_id(cfg["workload_profile"])
        if name not in names:
            names.append(name)
    policy = load_policy(DEFAULT_POLICY_PATH if policy_path is None else policy_path)
    allowed = set(_INFERENCE_PROVIDERS)
    for name in names:
        row = policy["profiles"].get(name)
        if row is None:
            _refuse("WORKLOAD_PROFILE_UNKNOWN")
        if row["execution_surface"] != "inference":
            _refuse("NATIVE_AGENT_PATH_REQUIRED")
        allowed.intersection_update(row["allowed_providers"])
    configured = cfg.get("provider_order")
    if not isinstance(configured, list) or len(configured) > len(_KNOWN_PROVIDERS):
        _refuse("WORKLOAD_PROVIDER_ORDER_REQUIRED")
    if any(not isinstance(p, str) or p not in _KNOWN_PROVIDERS for p in configured):
        _refuse("WORKLOAD_PROVIDER_ORDER_INVALID")
    if len(set(configured)) != len(configured):
        _refuse("WORKLOAD_PROVIDER_ORDER_INVALID")
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return WorkloadDecision(
        policy_revision=policy["revision"],
        policy_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        profiles=tuple(names),
        allowed_order=tuple(p for p in configured if p in allowed),
        denied_order=tuple(p for p in configured if p not in allowed),
    )
