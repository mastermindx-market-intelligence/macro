"""OpenCode Go subscription-usage parser for Shared AI Provider Control.

The provider endpoint reports percentage/reset evidence for one subscribed
workspace/user across rolling, weekly and monthly windows. Absolute limits are
not invented here; callers preserve provider-native percentage semantics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from engine.provider_subscription_usage import (
    SCHEMA,
    SubscriptionUsageError,
    SubscriptionUsageObservation,
    _closed_quota_row,
    _percent,
    _provider_time,
    _utc_iso,
)

OPENCODE_GO_USAGE_ENDPOINT = "https://opencode.ai/zen/go/v1/usage"

_WINDOW_MAP = {
    "rolling": ("five_hour", "OPENCODE_GO_FIVE_HOUR_UNKNOWN"),
    "weekly": ("weekly", "OPENCODE_GO_WEEKLY_UNKNOWN"),
    "monthly": ("monthly", "OPENCODE_GO_MONTHLY_UNKNOWN"),
}


def parse_opencode_go_usage(
    payload: Mapping[str, Any], *, observed_at: datetime | str | None = None
) -> SubscriptionUsageObservation:
    if not isinstance(payload, Mapping):
        raise SubscriptionUsageError("OPENCODE_GO_USAGE_NOT_MAPPING")
    observed = _utc_iso(observed_at)
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        raise SubscriptionUsageError("OPENCODE_GO_USAGE_DATA_INVALID")

    rows: list[Mapping[str, Any]] = []
    degraded: list[str] = []
    for provider_name, (horizon, degraded_code) in _WINDOW_MAP.items():
        raw = usage.get(provider_name)
        if not isinstance(raw, Mapping):
            degraded.append(degraded_code)
            continue
        used_percent = _percent(raw.get("percent"))
        reset_at = _provider_time(raw.get("resetsAt"))
        status_raw = str(raw.get("status") or "").strip().lower()
        if used_percent is None or reset_at is None or status_raw not in {"ok", "rate-limited"}:
            degraded.append(degraded_code)
            continue
        status = "exhausted" if status_raw == "rate-limited" or used_percent >= 100 else "limited"
        rows.append(
            _closed_quota_row(
                horizon=horizon,
                metric="provider_allocation",
                scope="account_shared",
                observed_at=observed,
                used_percent=used_percent,
                reported_remaining_percent=100.0 - used_percent,
                limit=None,
                used=None,
                remaining=None,
                reset_at=reset_at,
                status=status,
            )
        )

    observability = "exact" if not degraded else ("partial" if rows else "unknown")
    return SubscriptionUsageObservation(
        SCHEMA,
        "opencode",
        observed,
        "go",
        observability,
        tuple(rows),
        tuple(degraded),
    )


__all__ = ["OPENCODE_GO_USAGE_ENDPOINT", "parse_opencode_go_usage"]
