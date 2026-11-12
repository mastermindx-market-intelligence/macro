"""Grok Build subscription-usage acquisition for Shared AI Provider Control.

The installed Grok CLI owns authentication.  This adapter asks its ACP stdio
surface for the provider-reported billing snapshot and converts only the
SuperGrok weekly percentage/reset evidence into the canonical secret-free
subscription-usage observation.  It does not read auth files, send a model
prompt, create routing authority, or treat Grok Bot allowance as Build quota.
"""
from __future__ import annotations

import json
import select
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from engine.provider_subscription_usage import (
    SCHEMA,
    SubscriptionUsageError,
    SubscriptionUsageObservation,
    _closed_quota_row,
    _percent,
    _provider_time,
    _utc_iso,
)

GROK_BILLING_METHOD = "_x.ai/billing"
GROK_WEEKLY_SCOPE = "supergrok_shared"
GROK_WEEKLY_PERIOD_TYPE = "USAGE_PERIOD_TYPE_WEEKLY"
_DEFAULT_TIMEOUT_SECONDS = 8.0
_MAX_STDOUT_BYTES = 2 * 1024 * 1024

AcpBillingRunner = Callable[[str, float], Mapping[str, Any]]

_TIER_MAP = {
    "supergrok lite": "lite",
    "supergrok": "standard",
    "supergrok standard": "standard",
    "supergrok plus": "plus",
    "supergrok heavy": "heavy",
}


def _tier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _TIER_MAP.get(" ".join(value.strip().lower().split()))


def _billing_result(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise SubscriptionUsageError("GROK_BUILD_BILLING_NOT_MAPPING")
    result = payload.get("result", payload)
    if not isinstance(result, Mapping):
        raise SubscriptionUsageError("GROK_BUILD_BILLING_RESULT_INVALID")
    return result


def parse_grok_build_billing(
    payload: Mapping[str, Any], *, observed_at: datetime | str | None = None
) -> SubscriptionUsageObservation:
    """Normalize one Grok ACP billing response without inventing capacity."""

    observed = _utc_iso(observed_at)
    observed_instant = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    result = _billing_result(payload)
    config = result.get("config")
    tier = _tier(result.get("subscription_tier"))
    degraded: list[str] = []

    if not isinstance(config, Mapping):
        return SubscriptionUsageObservation(
            SCHEMA, "xai", observed, tier, "unknown", (),
            ("GROK_BUILD_WEEKLY_UNKNOWN",),
        )

    used_percent = _percent(config.get("creditUsagePercent"))
    current_period = config.get("currentPeriod")
    reset_at: str | None = None
    period_ok = False
    if isinstance(current_period, Mapping):
        period_ok = current_period.get("type") == GROK_WEEKLY_PERIOD_TYPE
        reset_at = _provider_time(current_period.get("end"))
    if reset_at is None:
        reset_at = _provider_time(config.get("billingPeriodEnd"))

    if used_percent is None:
        degraded.append("GROK_BUILD_USAGE_PERCENT_UNKNOWN")
    if not period_ok:
        degraded.append("GROK_BUILD_WEEKLY_PERIOD_UNKNOWN")
    if reset_at is None:
        degraded.append("GROK_BUILD_RESET_UNKNOWN")
    elif datetime.fromisoformat(reset_at.replace("Z", "+00:00")) <= observed_instant:
        degraded.append("GROK_BUILD_RESET_STALE")
    if tier is None:
        degraded.append("GROK_BUILD_TIER_UNKNOWN")

    # A partial weekly row is not emitted.  Unknown/stale dimensions must never
    # be interpreted downstream as spare quota.
    if degraded:
        return SubscriptionUsageObservation(
            SCHEMA, "xai", observed, tier, "unknown", (), tuple(degraded)
        )

    assert used_percent is not None and reset_at is not None
    row = _closed_quota_row(
        horizon="weekly",
        metric="provider_allocation",
        scope=GROK_WEEKLY_SCOPE,
        observed_at=observed,
        used_percent=used_percent,
        reported_remaining_percent=100.0 - used_percent,
        limit=None,
        used=None,
        remaining=None,
        reset_at=reset_at,
        status="exhausted" if used_percent >= 100.0 else "limited",
    )
    return SubscriptionUsageObservation(
        SCHEMA, "xai", observed, tier, "exact", (row,), ()
    )


def _bounded_binary(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024 or "\x00" in value:
        raise SubscriptionUsageError("GROK_BUILD_BINARY_INVALID")
    path = Path(value).expanduser() if "/" in value else None
    if path is not None and (not path.is_file() or not path.exists()):
        raise SubscriptionUsageError("GROK_BUILD_BINARY_UNAVAILABLE")
    return str(path) if path is not None else value


def _read_rpc_response(process: subprocess.Popen[str], request_id: int, deadline: float) -> Mapping[str, Any]:
    stdout = process.stdout
    if stdout is None:
        raise SubscriptionUsageError("GROK_BUILD_ACP_UNAVAILABLE")
    total_bytes = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SubscriptionUsageError("GROK_BUILD_ACP_TIMEOUT")
        ready, _, _ = select.select([stdout], [], [], remaining)
        if not ready:
            raise SubscriptionUsageError("GROK_BUILD_ACP_TIMEOUT")
        line = stdout.readline()
        if line == "":
            raise SubscriptionUsageError("GROK_BUILD_ACP_CLOSED")
        total_bytes += len(line.encode("utf-8", errors="ignore"))
        if total_bytes > _MAX_STDOUT_BYTES:
            raise SubscriptionUsageError("GROK_BUILD_ACP_RESPONSE_TOO_LARGE")
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, Mapping) or message.get("id") != request_id:
            continue
        if "error" in message:
            raise SubscriptionUsageError(
                "GROK_BUILD_BILLING_RPC_ERROR" if request_id == 2 else "GROK_BUILD_INITIALIZE_RPC_ERROR"
            )
        if not isinstance(message.get("result"), Mapping):
            raise SubscriptionUsageError("GROK_BUILD_BILLING_RESULT_INVALID")
        return message


def _send_rpc(process: subprocess.Popen[str], payload: Mapping[str, Any]) -> None:
    stdin = process.stdin
    if stdin is None:
        raise SubscriptionUsageError("GROK_BUILD_ACP_UNAVAILABLE")
    try:
        stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        raise SubscriptionUsageError("GROK_BUILD_ACP_CLOSED") from exc


def _run_grok_billing_acp(grok_binary: str, timeout_seconds: float) -> Mapping[str, Any]:
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
        raise SubscriptionUsageError("GROK_BUILD_TIMEOUT_INVALID")
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise SubscriptionUsageError("GROK_BUILD_TIMEOUT_INVALID")

    binary = _bounded_binary(grok_binary)
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": 1,
            "clientCapabilities": {},
            "clientInfo": {"name": "mastermind-provider-control", "version": "1.0"},
        },
    }
    billing = {"jsonrpc": "2.0", "id": 2, "method": GROK_BILLING_METHOD, "params": {}}
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            [binary, "--no-auto-update", "agent", "--no-leader", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        deadline = time.monotonic() + float(timeout_seconds)
        _send_rpc(process, initialize)
        _read_rpc_response(process, 1, deadline)
        _send_rpc(process, billing)
        return _read_rpc_response(process, 2, deadline)
    except SubscriptionUsageError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise SubscriptionUsageError("GROK_BUILD_ACP_UNAVAILABLE") from exc
    finally:
        if process is not None:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)


def observe_grok_build_usage(
    *,
    grok_binary: str = "grok",
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    observed_at: datetime | str | None = None,
    billing_runner: AcpBillingRunner = _run_grok_billing_acp,
) -> SubscriptionUsageObservation:
    """Read one authenticated, prompt-free SuperGrok weekly usage snapshot."""

    payload = billing_runner(grok_binary, timeout_seconds)
    return parse_grok_build_billing(payload, observed_at=observed_at)


__all__ = [
    "GROK_BILLING_METHOD",
    "GROK_WEEKLY_PERIOD_TYPE",
    "GROK_WEEKLY_SCOPE",
    "observe_grok_build_usage",
    "parse_grok_build_billing",
]
