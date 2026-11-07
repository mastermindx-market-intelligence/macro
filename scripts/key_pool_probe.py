"""scripts/key_pool_probe.py — operator diagnostics: is each OAuth key ALIVE?

Makes ONE minimal real API call (max_tokens=1) per PRESENT key env among
CLAUDE_CODE_OAUTH_TOKEN_1/_2/_3/_4/_5/_6/_7 and the legacy CLAUDE_CODE_OAUTH_TOKEN, and
prints a per-key verdict:

    CLAUDE_CODE_OAUTH_TOKEN_1: OK
    CLAUDE_CODE_OAUTH_TOKEN_2: AUTH_FAILED (revoked/expired — rotate the secret)
    CLAUDE_CODE_OAUTH_TOKEN_3: ABSENT

REDLINE: this module NEVER reads a token value itself. All credential handling
goes through engine.llm_auth (the single sanctioned boundary): each env name is
probed via build_providers({"oauth_token_env": <name>}) + make_call. No cap_id
is attached. This live diagnostic spends inference; existing owners may record
usage and provider health. In selected Fabric mode it probes ONE qualified
service binding, not the availability of every account in its pool.

Exit code: 0 when every PRESENT key serves; 1 when any present key fails
(auth-dead / rate-limited / errored) so the workflow run shows a red X the
operator can see at a glance. ABSENT keys are informational only — the pool
degrades gracefully by design.

Usage:  python -m scripts.key_pool_probe [--model claude-sonnet-4-6]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

log = logging.getLogger("key_pool_probe")

_PROBE_ENVS = [
    "CLAUDE_CODE_OAUTH_TOKEN_1",
    "CLAUDE_CODE_OAUTH_TOKEN_2",
    "CLAUDE_CODE_OAUTH_TOKEN_3",
    "CLAUDE_CODE_OAUTH_TOKEN_4",
    "CLAUDE_CODE_OAUTH_TOKEN_5",
    "CLAUDE_CODE_OAUTH_TOKEN_6",
    "CLAUDE_CODE_OAUTH_TOKEN_7",
    "CLAUDE_CODE_OAUTH_TOKEN",   # legacy single key (waterfall fallback)
]


def probe_env(env_name: str, model: str) -> str:
    """Probe one key env. Returns 'OK' | 'ABSENT' | 'AUTH_FAILED' |
    'RATE_LIMITED' | 'ERROR:<type>'. Never raises, never logs values."""
    from engine import llm_auth

    try:
        if llm_auth.application_mode_id() is not None:
            return "NOT_APPLICABLE:FABRIC_SERVICE"
    except Exception:
        return "ERROR:fabric_selection_refused"
    # Fresh dead-registry per probe so one dead key never masks another
    llm_auth.clear_dead()

    providers = llm_auth.build_providers({
        "provider_order": ["oauth"],
        "oauth_token_env": env_name,
        "codex_provider": False,
        "client_max_retries": 0,
    }, opus_model=model)
    providers = [p for p in providers if p.get("name") == "oauth" and p.get("env_var") == env_name]
    if not providers:
        return "ABSENT"

    def call_fn(client, mdl):
        response = client.messages.create(
            model=mdl, max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return "ok", None, response

    try:
        text, reason, used = llm_auth.make_call(
            providers, call_fn, context=f"key_pool_probe:{env_name}")
    except Exception as exc:  # noqa: BLE001 — connection/5xx re-raised by design
        return f"ERROR:{type(exc).__name__}"

    if text == "ok" and used == "oauth":
        return "OK"
    if reason in ("auth_invalid_all",):
        return "AUTH_FAILED"
    if reason in ("rate_limited_all",):
        return "RATE_LIMITED"
    return f"ERROR:{reason or 'unknown'}"


def _probe_fabric(mode_id: str, requested_model: str | None, operation_id: str | None) -> int:
    """One explicit operator invocation; native custody owns its original ID."""
    from engine import llm_auth
    from engine.provider_production_modes import make_application_fabric_factory

    if (type(operation_id) is not str or len(operation_id) > 96
            or not llm_auth._FABRIC_ID.fullmatch(operation_id)):
        raise ValueError("fabric_operation_id_required")
    profile = os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE")
    if not profile:
        raise ValueError("fabric_probe_workload_required")
    cfg = {"provider_order": ["fabric"], "workload_profile": profile}
    factory = make_application_fabric_factory(mode_id=mode_id, lane="key-pool-probe",
        root=_ROOT, workload_cfg=cfg)
    identity = factory.inspect(cfg)
    if requested_model is not None and requested_model != identity["model"]:
        raise ValueError("fabric_probe_requested_model_mismatch")
    report = {"kind": "FABRIC_SERVICE", "operation_id": operation_id,
        "requested_model": requested_model, "bound_model": identity["model"],
        "workload_profile": profile, "input": {"message": "ping", "max_tokens": 1},
        "observed_model": None, "ok": False, "error": None}
    # Emit the original identity before credential/admission/request effects.
    print(json.dumps({**report, "phase": "intent"}, sort_keys=True), flush=True)
    provider = operation = None
    interrupted = None
    try:
        provider = llm_auth.build_fabric_provider(factory.with_inspection(identity),
            request_id=operation_id, workload_cfg=cfg)
        provider.update(usage_lane="key-pool-probe", usage_stage="diagnostic", usage_cycle_id=operation_id)
        operation = llm_auth.begin_operation([provider], operation_id=operation_id, context="key_pool_probe")
        def invoke(client, model):
            response = client.messages.create(model=model, max_tokens=1,
                messages=[{"role": "user", "content": "ping"}])
            return "ok", None, response
        answer, reason, used = llm_auth.make_call(operation.providers, invoke, context="key_pool_probe")
        report["ok"] = answer == "ok" and reason is None and used == "fabric"
        if not report["ok"]:
            report["error"] = "fabric_probe_incomplete"
    except BaseException as exc:
        report["error"] = "fabric_probe_failed" if isinstance(exc, Exception) else "fabric_probe_interrupted"
        interrupted = exc if not isinstance(exc, Exception) else None
    finally:
        try:
            if operation is not None:
                operation.close()
            elif provider is not None:
                llm_auth.close_fabric_provider(provider)
        except BaseException as exc:
            report["error"] = report["error"] or "fabric_close_unsettled"
            interrupted = interrupted or (exc if not isinstance(exc, Exception) else None)
        if provider is not None:
            report.update(usage=llm_auth.fabric_usage(provider), close=provider.get("_fabric_close"),
                observation=provider.get("_fabric_last_observation"))
            report["observed_model"] = (report["observation"] or {}).get("serving_model")
            if report["close"] != {"disposition": "closed", "closed": True,
                                    "effect_unknown": False, "attempted": True}:
                report["ok"] = False
                report["error"] = report["error"] or "fabric_close_unsettled"
        # Publication failure never re-enters the inference path.
        print(json.dumps({**report, "phase": "result"}, sort_keys=True), flush=True)
    if interrupted is not None:
        raise interrupted
    return 0 if report["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Probe each OAuth pool key with one minimal API call.")
    ap.add_argument("--model", default=None,
                    help="Model for the 1-token probe call (default: the build lane's model).")
    ap.add_argument("--fabric-operation-id", help="Original operator invocation ID; required in Fabric mode.")
    args = ap.parse_args(argv)

    from engine import llm_auth
    try:
        mode_id = llm_auth.application_mode_id()
        if mode_id is not None:
            return _probe_fabric(mode_id, args.model, args.fabric_operation_id)
    except Exception:
        log.error("FABRIC_SERVICE: selection, identity, qualification or output refused")
        return 1
    verdicts: dict[str, str] = {}
    for env_name in _PROBE_ENVS:
        verdicts[env_name] = probe_env(env_name, args.model or "claude-sonnet-4-6")

    hints = {
        "OK": "",
        "ABSENT": " (not set — pool degrades gracefully)",
        "AUTH_FAILED": " (revoked/expired — rotate the secret)",
        "RATE_LIMITED": " (key works but is quota-cooling right now)",
    }
    print("── OAuth key pool probe ──")
    failed = []
    for env_name, verdict in verdicts.items():
        print(f"  {env_name}: {verdict}{hints.get(verdict, '')}")
        if verdict not in ("OK", "ABSENT"):
            failed.append(env_name)

    present_ok = [e for e, v in verdicts.items() if v == "OK"]
    print(f"── {len(present_ok)} key(s) serving; "
          f"{len(failed)} present-but-failing; "
          f"{sum(1 for v in verdicts.values() if v == 'ABSENT')} absent ──")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
