"""Single-request commercial ModelArk qualification canary — never production routing.

Owner: Shared AI Provider Control. This is an operator-only observation
helper over the incumbent metered call path; not an issuer/capacity/Worker
credential or admission plane. The shipped source remains SHADOW_OFF.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from engine import provider_production_modes as pm

SCHEMA = "mastermind.modelark_commercial_canary/v1"
ARM_ENV = "MM_MODELARK_COMMERCIAL_CANARY_MODE"
MAX_TOKENS = 32
MAX_ESTIMATED_USD = 0.01
EXPECTED_TEXT = "CANARY_OK"
_SYSTEM = "Return exactly CANARY_OK and nothing else."
_USER = "Say CANARY_OK and nothing else."
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class CanaryRefusal(ValueError):
    """Closed, secret-free rejection before any provider traffic."""


def source_preflight(
    *,
    source_path: Path | None = None,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate exact shadow-off source identity and canonical model pins."""
    path = Path(source_path) if source_path is not None else pm.DEFAULT_PATH
    if not isinstance(expected_source_sha256, str) or _SHA.fullmatch(expected_source_sha256) is None:
        raise CanaryRefusal("CANARY_SOURCE_PIN_REQUIRED")
    try:
        raw = path.read_bytes()
        modes = pm.load_modes(path)
    except (OSError, ValueError, pm.ProductionModeConfigError):
        raise CanaryRefusal("CANARY_SOURCE_INVALID") from None
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_source_sha256:
        raise CanaryRefusal("CANARY_SOURCE_DIGEST_DRIFT")
    expected = {"minimax_payg_api", "glm_general_api", *pm.MODELARK_MODELS}
    if set(modes) != expected:
        raise CanaryRefusal("CANARY_SOURCE_MODE_SET_DRIFT")
    if any(mode.enabled is not False for mode in modes.values()):
        raise CanaryRefusal("CANARY_REQUIRES_ALL_MODES_OFF")
    for name, model_id in pm.MODELARK_MODELS.items():
        mode = modes[name]
        profile = pm.MODELARK_RESPONSES_PROFILES.get(name)
        if (
            type(profile) is not pm.ResponsesProfile
            or profile.model != model_id
            or profile.qualification != pm.PROFILE_UNQUALIFIED_PENDING_CANARY
            or profile.max_output_tokens != 512
            or mode.default_model != model_id
            or mode.protocol != pm.PROTOCOL_RESPONSES
            or mode.secret_ref != "BYTEPLUS_MODELARK_API_KEY"
            or mode.base_url != "https://ark.ap-southeast.bytepluses.com/api/v3"
            or mode.cost_identity != "byteplus/metered"
            or mode.cap_id != "prod_api:byteplus"
            or mode.subscription_fallback_allowed is not False
        ):
            raise CanaryRefusal("CANARY_SOURCE_IDENTITY_DRIFT")
    return {
        "schema": SCHEMA,
        "source_sha256": digest,
        "all_modes_off": True,
        "pinned_model_count": len(pm.MODELARK_MODELS),
        "credentials_read": False,
        "provider_calls": 0,
        "qualified_model_count": 0,
        "production_activation": False,
    }


def run_canary(
    *,
    mode_id: str,
    armed_mode: str | None,
    expected_source_sha256: str,
    execute: bool = False,
    env: Mapping[str, str] | None = None,
    transport: pm.Transport | None = None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """One controlled probe, not an account-entitlement or release approval.

    Preflight and pricing checks run *before* the one credential boundary.
    A source-local, process-only candidate is used to keep the checked-in
    commercial modes disabled. The runner refuses inside multithreaded apps
    because the incumbent transport's config/profile globals are temporarily
    rebound, and must only be launched as a separate operator CLI.
    """
    if mode_id not in pm.MODELARK_MODELS or armed_mode != mode_id:
        raise CanaryRefusal("CANARY_MODE_NOT_ARMED")
    if execute is not True:
        raise CanaryRefusal("CANARY_EXECUTE_FLAG_REQUIRED")
    if threading.active_count() != 1:
        raise CanaryRefusal("CANARY_EXCLUSIVE_PROCESS_REQUIRED")
    source_path = Path(source_path) if source_path is not None else pm.DEFAULT_PATH
    proof = source_preflight(
        source_path=source_path,
        expected_source_sha256=expected_source_sha256,
    )
    model_id = pm.MODELARK_MODELS[mode_id]
    # Pricing rows must be reviewed and known before commercial spend.
    # This bounded estimate is a preflight guard, NOT an issuer-enforced cap.
    try:
        estimate = pm.ai_costs.estimate_cost_usd(
            model_id, 256, MAX_TOKENS, as_of_utc=datetime.now(timezone.utc)
        )
    except Exception:
        estimate = None
    if (
        isinstance(estimate, bool)
        or not isinstance(estimate, (int, float))
        or not math.isfinite(estimate)
        or not 0 <= estimate <= MAX_ESTIMATED_USD
    ):
        raise CanaryRefusal("CANARY_PRICING_NOT_QUALIFIED")
    # Use only a process-local config copy. Never rewrite a source/provider
    # configuration or grant production eligibility.
    current_raw = source_path.read_bytes()
    if hashlib.sha256(current_raw).hexdigest() != proof["source_sha256"]:
        raise CanaryRefusal("CANARY_SOURCE_CHANGED_DURING_PREFLIGHT")
    source = json.loads(current_raw.decode("utf-8"))
    source["modes"][mode_id]["enabled"] = True
    with tempfile.TemporaryDirectory(prefix="mm-modelark-canary-") as td:
        candidate_path = Path(td) / "source-canary.json"
        candidate_path.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
        candidate_path.chmod(0o600)
        old_path = pm.DEFAULT_PATH
        old_profiles = pm.MODELARK_RESPONSES_PROFILES
        approved_profile = dataclasses.replace(
            old_profiles[mode_id], qualification=pm.PROFILE_QUALIFIED_CANARY
        )
        pm.DEFAULT_PATH = candidate_path
        pm.MODELARK_RESPONSES_PROFILES = MappingProxyType(
            {**old_profiles, mode_id: approved_profile}
        )
        try:
            receipt = pm.call_mode(
                mode_id, _SYSTEM, _USER, max_tokens=MAX_TOKENS,
                env=env, transport=transport,
            )
        finally:
            pm.MODELARK_RESPONSES_PROFILES = old_profiles
            pm.DEFAULT_PATH = old_path

    response_match = (
        receipt.ok is True
        and isinstance(receipt.text, str)
        and receipt.text.strip() == EXPECTED_TEXT
    )
    identity_match = (
        receipt.provider_id == "byteplus"
        and receipt.model == model_id
        and receipt.mode_id == mode_id
        and receipt.cap_id == "prod_api:byteplus"
        and receipt.fallback == "none"
    )
    accounting_known = (
        receipt.price_state == "known"
        and receipt.input_tokens is not None
        and receipt.output_tokens is not None
    )
    rehearsal_passed = bool(response_match and identity_match and accounting_known)
    # A fake/test transport is NEVER an issuer canary acceptance receipt.
    observation_passed = rehearsal_passed and transport is None
    return {
        "schema": SCHEMA,
        "mode_id": mode_id,
        "model": model_id,
        "source_sha256": proof["source_sha256"],
        "canary_observation_passed": observation_passed,
        "injected_transport_rehearsal_passed": rehearsal_passed if transport is not None else None,
        "provider_error_class": receipt.error_class,
        "response_match": response_match,
        "identity_match": identity_match,
        "accounting_known": accounting_known,
        "input_tokens": receipt.input_tokens,
        "output_tokens": receipt.output_tokens,
        "price_state": receipt.price_state,
        "one_request_ceiling": 1,
        "max_output_tokens": MAX_TOKENS,
        "preflight_cost_estimate_usd": round(float(estimate), 8),
        "estimated_cost_is_not_provider_cap": True,
        "automatic_retry_allowed": False,
        "same_operation_replay_allowed": False,
        "source_mode_enabled": False,
        "provider_registration_effect": False,
        "capacity_or_worker_granted": False,
        "production_activation": False,
        "qualification_effect": False,
        "issuer_entitlement_verified": False,
        "provider_billing_debit_verified": False,
        # Caller-provided transport is untrusted and may itself make a network
        # call. Only the *actual fixture* can prove it did not; never assert
        # NO_EFFECT from the mere fact that a transport was injected.
        "effect_state": (
            "INJECTED_TRANSPORT_UNVERIFIED" if transport is not None
            else "PROVIDER_EFFECT_POSSIBLE"
        ),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Single controlled ModelArk commercial canary")
    parser.add_argument("--mode", choices=sorted(pm.MODELARK_MODELS), required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"schema": SCHEMA, "canary_observation_passed": False,
                          "reason": "CANARY_EXECUTE_FLAG_REQUIRED"}, sort_keys=True))
        return 64
    try:
        result = run_canary(
            mode_id=args.mode,
            armed_mode=os.environ.get(ARM_ENV),
            expected_source_sha256=args.source_sha256,
            execute=args.execute,
        )
    except CanaryRefusal as exc:
        print(json.dumps({"schema": SCHEMA, "canary_observation_passed": False,
                          "reason": str(exc)}, sort_keys=True))
        return 65
    print(json.dumps(result, sort_keys=True))
    return 0 if result["canary_observation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())
