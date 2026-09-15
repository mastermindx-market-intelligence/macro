"""Secret-free usage observations for subscription-backed AI provider plans.

The parsers in this module preserve provider-native quota semantics. They do not
create routing authority, persist credentials, or mutate provider_capacity.v1.
Unknown/unsupported fields remain unknown rather than becoming free capacity.
"""
from __future__ import annotations

import dataclasses
import json
import math
import re
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "mastermind.provider_subscription_usage/v1"
GLM_QUOTA_ENDPOINT = "https://api.z.ai/api/monitor/usage/quota/limit"
MINIMAX_QUOTA_ENDPOINT = "https://www.minimax.io/v1/token_plan/remains"

_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class SubscriptionUsageError(ValueError):
    """A provider usage observation is malformed or unsafe."""


@dataclasses.dataclass(frozen=True)
class SubscriptionUsageObservation:
    schema: str
    provider: str
    observed_at: str
    plan_level: str | None
    observability: str
    quota_rows: tuple[Mapping[str, Any], ...]
    degraded_codes: tuple[str, ...]


HttpJsonGetter = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]
CredentialLoader = Callable[[], str]


def _utc_iso(value: datetime | str | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise SubscriptionUsageError("INVALID_TIMESTAMP") from exc
    else:
        raise SubscriptionUsageError("INVALID_TIMESTAMP")
    if parsed.tzinfo is None:
        raise SubscriptionUsageError("INVALID_TIMESTAMP")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _provider_time(value: Any) -> str | None:
    if value in (None, "", 0, "0"):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        raw = float(value)
        if raw <= 0:
            return None
        seconds = raw / 1000.0 if raw > 10_000_000_000 else raw
        try:
            return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return _utc_iso(value)
        except SubscriptionUsageError:
            return None
    return None


def _number(value: Any, *, positive: bool = False) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0 or (positive and parsed <= 0):
        return None
    return parsed


def _percent(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.strip().rstrip("%")
    parsed = _number(value)
    if parsed is None or parsed > 100:
        return None
    return parsed


def _safe_level(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if _ID_RE.fullmatch(text) else None


def _closed_quota_row(
    *,
    horizon: str,
    metric: str,
    observed_at: str,
    used_percent: float | None,
    reported_remaining_percent: float | None,
    limit: float | None,
    used: float | None,
    remaining: float | None,
    reset_at: str | None,
    status: str,
    scope: str | None = None,
) -> Mapping[str, Any]:
    return {
        "horizon": horizon,
        "metric": metric,
        "scope": scope,
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "used_percent": used_percent,
        "reported_remaining_percent": reported_remaining_percent,
        "reset_at": reset_at,
        "status": status,
        "observed_at": observed_at,
    }


def _glm_horizon(row: Mapping[str, Any], kind: str) -> str | None:
    unit = row.get("unit")
    normalized = str(unit).strip().lower() if unit is not None else ""
    if normalized in {"3", "five_hour", "5h", "5_hour"}:
        return "five_hour"
    if normalized in {"6", "weekly", "week", "7d", "7_day"}:
        return "weekly"
    explicit = str(row.get("horizon") or row.get("window") or "").strip().lower()
    if explicit in {"five_hour", "5h", "5_hour"}:
        return "five_hour"
    if explicit in {"weekly", "week", "7d", "7_day"}:
        return "weekly"
    # The provider's official legacy usage plugin treats a unit-less TOKENS_LIMIT
    # row as the five-hour model-compute allowance.
    if kind == "TOKENS_LIMIT" and unit is None:
        return "five_hour"
    return None


def parse_glm_quota(payload: Mapping[str, Any], *, observed_at: datetime | str | None = None) -> SubscriptionUsageObservation:
    if not isinstance(payload, Mapping):
        raise SubscriptionUsageError("GLM_USAGE_NOT_MAPPING")
    observed = _utc_iso(observed_at)
    data = payload.get("data", payload)
    if not isinstance(data, Mapping):
        raise SubscriptionUsageError("GLM_USAGE_DATA_INVALID")
    limits = data.get("limits")
    if not isinstance(limits, Sequence) or isinstance(limits, (str, bytes)):
        limits = ()
    rows: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in limits:
        if not isinstance(raw, Mapping):
            continue
        kind = str(raw.get("type") or "").strip().upper()
        if kind in {"CREDIT_LIMIT", "TOKENS_LIMIT"}:
            horizon = _glm_horizon(raw, kind)
            if horizon is None:
                continue
            metric = "credits" if kind == "CREDIT_LIMIT" else "tokens"
        elif kind == "TIME_LIMIT":
            horizon, metric = "monthly", "mcp_web_calls"
        else:
            continue
        key = (horizon, metric)
        if key in seen:
            continue
        seen.add(key)
        used_percent = _percent(raw.get("percentage"))
        limit = _number(raw.get("usage"), positive=True)
        used = _number(raw.get("currentValue"))
        remaining = _number(raw.get("remaining"))
        if remaining is None and limit is not None and used is not None and used <= limit:
            remaining = limit - used
        if used_percent is None and limit is not None and used is not None and used <= limit:
            used_percent = 100.0 * used / limit
        reported_remaining = None if used_percent is None else 100.0 - used_percent
        reset_at = _provider_time(raw.get("nextResetTime") or raw.get("resetAt") or raw.get("endTime"))
        status = "exhausted" if used_percent is not None and used_percent >= 100.0 else "limited"
        rows.append(_closed_quota_row(
            horizon=horizon, metric=metric, observed_at=observed,
            used_percent=used_percent, reported_remaining_percent=reported_remaining,
            limit=limit, used=used, remaining=remaining, reset_at=reset_at, status=status,
        ))
    present = {row["horizon"] for row in rows if row["metric"] in {"credits", "tokens"}}
    degraded: list[str] = []
    for horizon, code in (("five_hour", "GLM_FIVE_HOUR_UNKNOWN"), ("weekly", "GLM_WEEKLY_UNKNOWN")):
        if horizon not in present:
            degraded.append(code)
    observability = "exact" if not degraded else ("partial" if rows else "unknown")
    return SubscriptionUsageObservation(
        SCHEMA, "glm", observed, _safe_level(data.get("level")), observability,
        tuple(rows), tuple(degraded),
    )


def _minimax_row(
    raw: Mapping[str, Any], *, horizon: str, observed: str, model: str,
) -> Mapping[str, Any]:
    prefix = "current_interval" if horizon == "five_hour" else "current_weekly"
    status_code = raw.get(f"{prefix}_status")
    status = {1: "limited", 2: "exhausted", 3: "provider_unlimited"}.get(status_code, "unknown")
    remaining_percent = _percent(raw.get(f"{prefix}_remaining_percent"))
    used_percent: float | None
    if status == "provider_unlimited":
        # Preserve the provider state without turning it into infinite scheduler capacity.
        used_percent = None
    elif status == "exhausted":
        used_percent, remaining_percent = 100.0, 0.0
    else:
        used_percent = None if remaining_percent is None else 100.0 - remaining_percent
    total = _number(raw.get(f"{prefix}_total_count"), positive=True)
    used = _number(raw.get(f"{prefix}_usage_count")) if total is not None else None
    if total is not None and used is not None and used > total:
        total, used = None, None
    remaining = total - used if total is not None and used is not None else None
    reset_field = "end_time" if horizon == "five_hour" else "weekly_end_time"
    return _closed_quota_row(
        horizon=horizon, metric="provider_allocation", scope=model, observed_at=observed,
        used_percent=used_percent, reported_remaining_percent=remaining_percent,
        limit=total, used=used, remaining=remaining, reset_at=_provider_time(raw.get(reset_field)),
        status=status,
    )


def parse_minimax_quota(payload: Mapping[str, Any], *, observed_at: datetime | str | None = None) -> SubscriptionUsageObservation:
    if not isinstance(payload, Mapping):
        raise SubscriptionUsageError("MINIMAX_USAGE_NOT_MAPPING")
    observed = _utc_iso(observed_at)
    remains = payload.get("model_remains")
    if not isinstance(remains, Sequence) or isinstance(remains, (str, bytes)):
        remains = ()
    rows: list[Mapping[str, Any]] = []
    for raw in remains:
        if not isinstance(raw, Mapping):
            continue
        model = _safe_level(raw.get("model_name"))
        if model is None:
            continue
        rows.append(_minimax_row(raw, horizon="five_hour", observed=observed, model=model))
        rows.append(_minimax_row(raw, horizon="weekly", observed=observed, model=model))
    degraded: list[str] = []
    if not rows:
        degraded.append("MINIMAX_QUOTA_UNKNOWN")
    elif any(row["used_percent"] is None and row["status"] not in {"provider_unlimited"} for row in rows):
        degraded.append("MINIMAX_REMAINING_PERCENT_PARTIAL")
    return SubscriptionUsageObservation(
        SCHEMA, "minimax", observed, None, "exact" if not degraded else ("partial" if rows else "unknown"),
        tuple(rows), tuple(degraded),
    )


def parse_alibaba_usage(payload: Mapping[str, Any], *, observed_at: datetime | str | None = None) -> SubscriptionUsageObservation:
    """Preserve supported CLI usage evidence without inventing Token Plan window fields.

    Current public CLI JSON is useful for usage reconciliation, but its published
    schema does not yet establish stable machine-readable 5h/7d Token Plan window
    counters. Until that contract is explicit, quota rows remain empty.
    """
    if not isinstance(payload, Mapping):
        raise SubscriptionUsageError("ALIBABA_USAGE_NOT_MAPPING")
    observed = _utc_iso(observed_at)
    return SubscriptionUsageObservation(
        SCHEMA, "alibaba", observed, None, "partial", (),
        ("ALIBABA_TOKEN_PLAN_WINDOW_TELEMETRY_PARTIAL",),
    )


def _credential(loader: CredentialLoader) -> str:
    value = loader()
    if not isinstance(value, str):
        raise SubscriptionUsageError("PROVIDER_CREDENTIAL_UNAVAILABLE")
    secret = value.strip()
    if not secret or len(secret) > 4096 or any(ch in secret for ch in "\r\n\x00"):
        raise SubscriptionUsageError("PROVIDER_CREDENTIAL_UNAVAILABLE")
    return secret


def _https_get_json(url: str, headers: Mapping[str, str], timeout_seconds: float) -> Mapping[str, Any]:
    request = urllib.request.Request(url, method="GET", headers=dict(headers))
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        if getattr(response, "status", 200) != 200:
            raise SubscriptionUsageError("PROVIDER_USAGE_HTTP_ERROR")
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise SubscriptionUsageError("PROVIDER_USAGE_RESPONSE_TOO_LARGE")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SubscriptionUsageError("PROVIDER_USAGE_JSON_INVALID") from exc
    if not isinstance(decoded, Mapping):
        raise SubscriptionUsageError("PROVIDER_USAGE_JSON_INVALID")
    return decoded


def observe_glm_quota(
    credential_loader: CredentialLoader, *, http_get: HttpJsonGetter = _https_get_json,
    observed_at: datetime | str | None = None, timeout_seconds: float = 10.0,
) -> SubscriptionUsageObservation:
    token = _credential(credential_loader)
    payload = http_get(GLM_QUOTA_ENDPOINT, {
        "Authorization": token, "Accept-Language": "en-US,en", "Content-Type": "application/json",
    }, timeout_seconds)
    return parse_glm_quota(payload, observed_at=observed_at)


def observe_minimax_quota(
    credential_loader: CredentialLoader, *, http_get: HttpJsonGetter = _https_get_json,
    observed_at: datetime | str | None = None, timeout_seconds: float = 10.0,
) -> SubscriptionUsageObservation:
    token = _credential(credential_loader)
    payload = http_get(MINIMAX_QUOTA_ENDPOINT, {
        "Authorization": f"Bearer {token}", "Accept": "application/json",
    }, timeout_seconds)
    return parse_minimax_quota(payload, observed_at=observed_at)


__all__ = [
    "GLM_QUOTA_ENDPOINT", "MINIMAX_QUOTA_ENDPOINT", "SCHEMA",
    "SubscriptionUsageError", "SubscriptionUsageObservation",
    "observe_glm_quota", "observe_minimax_quota", "parse_alibaba_usage",
    "parse_glm_quota", "parse_minimax_quota",
]
