"""Fail-closed source-rights and runtime-health receipts for qbus ticker news.

This module owns no license decision and no runtime lifecycle. A source-rights
owner may provide a machine-readable receipt saying which uses are permitted; the
API maps only those explicit capabilities into NewsReadRights. Missing, malformed,
wrong-audience, future or expired receipts do not grant access.

The runtime health receipt is observation evidence only. A connected socket is
not freshness: API-facing live requires a recent successful REST catch-up.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping

from engine.qbus_news_store import NewsReadRights

RIGHTS_SCHEMA = "qbus.news_rights_receipt.v1"
HEALTH_SCHEMA = "qbus.news_health.v1"
_SOURCE = "benzinga"
_HEALTH_STATES = frozenset({"live", "catching_up", "degraded", "unavailable"})


class NewsReceiptError(ValueError):
    """Sanitized fail-closed receipt error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"qbus_news_receipt:{code}")


@dataclass(frozen=True, slots=True)
class QualifiedNewsRights:
    receipt_id: str
    owner_ref: str
    source: str
    product_id: str
    audience: str
    effective_at: datetime
    expires_at: datetime
    rights: NewsReadRights
    provider: str | None = None


def _mapping(value: object, code: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NewsReceiptError(code)
    return value


def _text(
    value: object,
    code: str,
    *,
    maximum: int = 1024,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise NewsReceiptError(code)
    out = value.strip()
    if (not allow_empty and not out) or len(out) > maximum or "\x00" in out:
        raise NewsReceiptError(code)
    return out


def _aware_utc(value: object, code: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise NewsReceiptError(code)
    raw = value.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise NewsReceiptError(code) from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise NewsReceiptError(code)
    try:
        return dt.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise NewsReceiptError(code) from None


def _now_utc(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise NewsReceiptError("invalid_now")
    return now.astimezone(timezone.utc)


def _bool(
    payload: Mapping[str, object],
    name: str,
    *,
    default: bool | None = None,
) -> bool:
    if name not in payload:
        if default is None:
            raise NewsReceiptError(f"capability_{name}_missing")
        return default
    value = payload[name]
    if not isinstance(value, bool):
        raise NewsReceiptError(f"capability_{name}_invalid")
    return value


def _nonnegative_int(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NewsReceiptError(code)
    return value


def parse_rights_receipt(
    payload: object,
    *,
    now: datetime,
    audience: str = "site_full",
) -> QualifiedNewsRights:
    """Qualify an owner-issued source receipt for the current product use."""

    obj = _mapping(payload, "rights_not_object")
    if obj.get("schema") != RIGHTS_SCHEMA:
        raise NewsReceiptError("rights_schema")
    if _text(obj.get("status"), "rights_status", maximum=32).lower() != "approved":
        raise NewsReceiptError("rights_not_approved")
    if _text(obj.get("source"), "rights_source", maximum=64).lower() != _SOURCE:
        raise NewsReceiptError("rights_source")
    receipt_id = _text(obj.get("receipt_id"), "rights_receipt_id", maximum=256)
    owner_ref = _text(obj.get("owner_ref"), "rights_owner_ref", maximum=1024)
    product_id = _text(obj.get("product_id"), "rights_product_id", maximum=256)
    provider = None if obj.get("provider") is None else _text(obj.get("provider"), "rights_provider", maximum=64)
    requested_audience = _text(audience, "rights_audience_requested", maximum=128)

    audiences_raw = obj.get("audiences")
    if not isinstance(audiences_raw, list):
        raise NewsReceiptError("rights_audiences")
    audiences: list[str] = []
    for raw in audiences_raw:
        token = _text(raw, "rights_audience", maximum=128)
        if token not in audiences:
            audiences.append(token)
    if requested_audience not in audiences:
        raise NewsReceiptError("rights_audience_not_permitted")

    current = _now_utc(now)
    effective_at = _aware_utc(obj.get("effective_at"), "rights_effective_at")
    expires_at = _aware_utc(obj.get("expires_at"), "rights_expires_at")
    if expires_at <= effective_at:
        raise NewsReceiptError("rights_window")
    if current < effective_at:
        raise NewsReceiptError("rights_not_effective")
    if current >= expires_at:
        raise NewsReceiptError("rights_expired")

    caps = _mapping(obj.get("capabilities"), "rights_capabilities")
    for required in (
        "internal_ingestion",
        "historical_retention",
        "headline_display",
    ):
        if not _bool(caps, required):
            raise NewsReceiptError(f"capability_{required}_required")

    allow_url = _bool(caps, "source_link_display", default=False)
    allow_teaser = _bool(caps, "teaser_display", default=False)

    for optional in (
        "body_display",
        "image_display",
        "derivative_processing",
    ):
        _bool(caps, optional, default=False)

    return QualifiedNewsRights(
        receipt_id=receipt_id,
        owner_ref=owner_ref,
        source=_SOURCE,
        product_id=product_id,
        audience=requested_audience,
        effective_at=effective_at,
        expires_at=expires_at,
        rights=NewsReadRights(
            allowed_sources=frozenset({_SOURCE}),
            allow_title=True,
            allow_url=allow_url,
            allow_teaser=allow_teaser,
        ),
        provider=provider,
    )


def load_rights_receipt(
    path: Path | str,
    *,
    now: datetime,
    audience: str = "site_full",
) -> QualifiedNewsRights | None:
    """Read an owner-provided receipt; every read/parse/qualification fault denies."""

    receipt_path = Path(path)
    try:
        raw = json.loads(receipt_path.read_text(encoding="utf-8"))
        return parse_rights_receipt(raw, now=now, audience=audience)
    except (OSError, ValueError, TypeError, NewsReceiptError):
        return None


def _health_base(reason: str) -> dict[str, object]:
    return {
        "schema": HEALTH_SCHEMA,
        "source": _SOURCE,
        "state": "unavailable",
        "observed_at": None,
        "last_successful_catchup": None,
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 0,
        "disconnects": 0,
        "catchups_failed": 0,
        "reason": reason,
    }


def parse_health_receipt(
    payload: object,
    *,
    now: datetime,
    max_observation_age_seconds: float = 120.0,
    max_catchup_age_seconds: float = 120.0,
) -> dict[str, object]:
    """Validate and conservatively project one runtime health observation."""

    if max_observation_age_seconds <= 0 or max_catchup_age_seconds <= 0:
        raise NewsReceiptError("health_age_budget")
    obj = _mapping(payload, "health_not_object")
    if obj.get("schema") != HEALTH_SCHEMA:
        raise NewsReceiptError("health_schema")
    if _text(obj.get("source"), "health_source", maximum=64).lower() != _SOURCE:
        raise NewsReceiptError("health_source")

    raw_state = _text(obj.get("state"), "health_state", maximum=32).lower()
    if raw_state not in _HEALTH_STATES:
        raise NewsReceiptError("health_state")

    current = _now_utc(now)
    observed_at = _aware_utc(obj.get("observed_at"), "health_observed_at")
    if observed_at > current:
        raise NewsReceiptError("health_observed_future")

    def optional_time(name: str) -> datetime | None:
        value = obj.get(name)
        if value is None:
            return None
        dt = _aware_utc(value, f"health_{name}")
        if dt > observed_at:
            raise NewsReceiptError(f"health_{name}_future")
        return dt

    last_catchup = optional_time("last_successful_catchup")
    last_stream = optional_time("last_stream_event_at")
    gap = obj.get("gap_unresolved")
    if not isinstance(gap, bool):
        raise NewsReceiptError("health_gap_unresolved")

    connect_attempts = _nonnegative_int(
        obj.get("connect_attempts", 0), "health_connect_attempts"
    )
    disconnects = _nonnegative_int(
        obj.get("disconnects", 0), "health_disconnects"
    )
    catchups_failed = _nonnegative_int(
        obj.get("catchups_failed", 0), "health_catchups_failed"
    )

    observation_age = (current - observed_at).total_seconds()
    catchup_age = (
        None if last_catchup is None else (current - last_catchup).total_seconds()
    )

    if observation_age > max_observation_age_seconds:
        state, reason = "unavailable", "receipt_stale"
    elif raw_state == "unavailable":
        state, reason = "unavailable", "source_unavailable"
    elif gap:
        state, reason = "degraded", "gap_unresolved"
    elif last_catchup is None:
        state, reason = "catching_up", "catchup_pending"
    elif catchup_age is not None and catchup_age > max_catchup_age_seconds:
        state, reason = "degraded", "catchup_stale"
    elif raw_state == "catching_up":
        state, reason = "catching_up", "catching_up"
    elif raw_state == "degraded":
        state, reason = "degraded", "runtime_degraded"
    else:
        state, reason = "live", "fresh"

    return {
        "schema": HEALTH_SCHEMA,
        "source": _SOURCE,
        "state": state,
        "observed_at": observed_at.isoformat(),
        "last_successful_catchup": (
            None if last_catchup is None else last_catchup.isoformat()
        ),
        "last_stream_event_at": (
            None if last_stream is None else last_stream.isoformat()
        ),
        "gap_unresolved": gap,
        "connect_attempts": connect_attempts,
        "disconnects": disconnects,
        "catchups_failed": catchups_failed,
        "reason": reason,
    }


def load_health_receipt(
    path: Path | str,
    *,
    now: datetime,
    max_observation_age_seconds: float = 120.0,
    max_catchup_age_seconds: float = 120.0,
) -> dict[str, object]:
    """Load runtime health. Missing/malformed evidence is explicitly unavailable."""

    receipt_path = Path(path)
    try:
        raw = json.loads(receipt_path.read_text(encoding="utf-8"))
    except OSError:
        return _health_base("receipt_missing")
    except (ValueError, TypeError):
        return _health_base("receipt_invalid")
    try:
        return parse_health_receipt(
            raw,
            now=now,
            max_observation_age_seconds=max_observation_age_seconds,
            max_catchup_age_seconds=max_catchup_age_seconds,
        )
    except NewsReceiptError:
        return _health_base("receipt_invalid")


def write_health_receipt(path: Path | str, payload: object) -> None:
    """Atomically publish one private runtime-health receipt."""

    receipt_path = Path(path)
    obj = _mapping(payload, "health_write_not_object")
    if obj.get("schema") != HEALTH_SCHEMA:
        raise NewsReceiptError("health_write_schema")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=receipt_path.parent,
            prefix=f".{receipt_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            temp_name = fh.name
            os.chmod(temp_name, 0o600)
            json.dump(obj, fh, sort_keys=True, separators=(",", ":"))
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, receipt_path)
        temp_name = None
        os.chmod(receipt_path, 0o600)
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
