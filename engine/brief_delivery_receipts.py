"""Owner readback observation for persisted Macro recurring-brief deliveries.

``observe_delivery_write`` performs the incumbent brief delivery write -- the
single original POST to ``brief_deliveries?on_conflict=subscription_id,
slot_asof`` with ``Prefer: resolution=ignore-duplicates,return=minimal`` --
and then confirms what actually persisted with exactly one bounded owner
readback GET on the same subscription/slot, inner-joined to the current
``brief_subscriptions`` row and filtered to the expected owner.

Scope, stated plainly: the receipt produced here is a raw owner readback
observation of one local persisted row.  It is NOT a qualified native
locator, NOT a 0048 content/effect digest and NOT an authorization of any
kind.  Runtime must establish actual producer invocation and the source
receipt owner independently before releasing any locator; externally authored
worker JSON is never proof.

The module logs nothing, reads no environment, holds no credentials, never
generates a delivery UUID, and raises nothing: outcomes are closed reason
codes, so provider error text, private identifiers and row bodies never
surface to the caller as strings.

``observation_sha256`` is the SHA-256 of the canonical JSON document (sorted
keys, compact separators, UTF-8, no NaN) over exactly these keys::

    schema, delivery_id, subscription_id, slot_asof, state, degraded_reason,
    artifact_asof, body, owner_user_id, observed_at

Instants (``artifact_asof``, ``observed_at``) are normalized to UTC ISO-8601
before hashing.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote

__all__ = [
    "CALL_TIMEOUT_SECONDS",
    "DeliveryWriteObservation",
    "MAX_BODY_BYTES",
    "ObservationReason",
    "PersistedDeliveryObservation",
    "POST_PATH",
    "POST_PREFER",
    "PostOutcome",
    "observe_delivery_write",
]

# Incumbent write shape; do not change -- the writer callsite relies on it.
POST_PATH = "brief_deliveries?on_conflict=subscription_id,slot_asof"
POST_PREFER = "resolution=ignore-duplicates,return=minimal"

CALL_TIMEOUT_SECONDS = 6
MAX_BODY_BYTES = 128 * 1024
READBACK_LIMIT = 2

_SELECT_FIELDS = (
    "delivery_id,subscription_id,slot_asof,state,degraded_reason,"
    "artifact_asof,body,brief_subscriptions!inner(user_id)"
)
_ROW_KEYS = frozenset(
    {
        "subscription_id",
        "slot_asof",
        "state",
        "degraded_reason",
        "artifact_asof",
        "body",
    }
)
_PERSISTED_KEYS = frozenset(
    {
        "delivery_id",
        "subscription_id",
        "slot_asof",
        "state",
        "degraded_reason",
        "artifact_asof",
        "body",
        "brief_subscriptions",
    }
)
_MAX_ERROR_TEXT_BYTES = 4096

_OBSERVATION_SCHEMA = "macro.brief_delivery.owner_readback.v1"


class PostOutcome(str, Enum):
    """What the original POST phase established."""

    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DUPLICATE = "DUPLICATE"
    AMBIGUOUS = "AMBIGUOUS"
    REFUSED = "REFUSED"


class ObservationReason(str, Enum):
    """Closed codes; no provider text, identifiers or bodies leak through."""

    DRY_RUN = "DRY_RUN"
    INPUT_NOT_READY = "INPUT_NOT_READY"
    INPUT_INVALID = "INPUT_INVALID"
    READBACK_MATCHED = "READBACK_MATCHED"
    READBACK_MISSING = "READBACK_MISSING"
    READBACK_AMBIGUOUS = "READBACK_AMBIGUOUS"
    READBACK_MISMATCH = "READBACK_MISMATCH"
    READBACK_UNAVAILABLE = "READBACK_UNAVAILABLE"
    PROVIDER_REFUSED = "PROVIDER_REFUSED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PROGRAMMER_ERROR = "PROGRAMMER_ERROR"
    HTTP_UNCONFIRMED = "HTTP_UNCONFIRMED"
    REQUEST_REJECTED = "REQUEST_REJECTED"


@dataclass(frozen=True)
class PersistedDeliveryObservation:
    """Raw owner readback of the one persisted ``brief_deliveries`` row."""

    delivery_id: str
    slot_asof: str
    observed_at: str
    observation_sha256: str


@dataclass(frozen=True)
class DeliveryWriteObservation:
    """Outcome of one delivery write plus its persisted-row readback."""

    post_outcome: PostOutcome
    receipt: PersistedDeliveryObservation | None
    reason: ObservationReason


def _utc_clock() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_uuid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return None
    # Canonical lowercase hyphenated form only; reject upper/braced/urn forms.
    return value if str(parsed) == value else None


def _canonical_slot(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed.isoformat() == value else None


def _aware_instant(value: Any) -> datetime | None:
    """Parse an instant and normalize to UTC; naive values are not usable."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return None
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _canonical_json(value: Any) -> bytes | None:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return None
    try:
        return text.encode("utf-8")
    except UnicodeError:
        return None


def _classify_input(row: Any, expected_owner_id: Any) -> tuple[dict[str, Any] | None, ObservationReason | None]:
    """Return (validated row, None) or (None, closed rejection reason)."""
    if _canonical_uuid(expected_owner_id) is None:
        return None, ObservationReason.INPUT_INVALID
    if not isinstance(row, dict) or set(row) != _ROW_KEYS:
        return None, ObservationReason.INPUT_INVALID
    if row["state"] != "ready" or row["degraded_reason"] is not None:
        return None, ObservationReason.INPUT_NOT_READY
    if _canonical_uuid(row["subscription_id"]) is None:
        return None, ObservationReason.INPUT_INVALID
    if _canonical_slot(row["slot_asof"]) is None:
        return None, ObservationReason.INPUT_INVALID
    if row["artifact_asof"] is not None and _aware_instant(row["artifact_asof"]) is None:
        return None, ObservationReason.INPUT_INVALID
    body_bytes = _canonical_json(row["body"])
    if body_bytes is None or len(body_bytes) > MAX_BODY_BYTES:
        return None, ObservationReason.INPUT_INVALID
    validated = dict(row)
    validated["body"] = json.loads(body_bytes)
    return validated, None


def _readback_path(subscription_id: str, slot_asof: str, expected_owner_id: str) -> str:
    return (
        "brief_deliveries"
        f"?select={_SELECT_FIELDS}"
        f"&subscription_id=eq.{quote(subscription_id, safe='')}"
        f"&slot_asof=eq.{quote(slot_asof, safe='')}"
        f"&brief_subscriptions.user_id=eq.{quote(expected_owner_id, safe='')}"
        f"&limit={READBACK_LIMIT}"
    )


def _bounded_error_text(exc: HTTPError) -> str:
    """Read a small prefix of the provider error body; never surfaced."""
    try:
        raw = exc.read(_MAX_ERROR_TEXT_BYTES + 1)
        if len(raw) > _MAX_ERROR_TEXT_BYTES:
            return ""
        return raw.decode("utf-8")
    except Exception:
        return ""


def _qualified_delivery_id(
    persisted: Any,
    row: dict[str, Any],
    expected_owner_id: str,
    artifact_utc: datetime | None,
) -> str | None:
    """Return the persisted delivery UUID only on an exact, owner-owned row."""
    if not isinstance(persisted, dict) or set(persisted) != _PERSISTED_KEYS:
        return None
    delivery_id = _canonical_uuid(persisted["delivery_id"])
    if delivery_id is None:
        return None
    if persisted["subscription_id"] != row["subscription_id"]:
        return None
    if persisted["slot_asof"] != row["slot_asof"]:
        return None
    if persisted["state"] != "ready" or persisted["degraded_reason"] is not None:
        return None
    body_bytes = _canonical_json(persisted["body"])
    if body_bytes is None or len(body_bytes) > MAX_BODY_BYTES:
        return None
    if body_bytes != _canonical_json(row["body"]):
        return None
    embedded = persisted["brief_subscriptions"]
    if not isinstance(embedded, dict) or embedded.get("user_id") != expected_owner_id:
        return None
    if artifact_utc is None:
        if persisted["artifact_asof"] is not None:
            return None
    else:
        persisted_utc = _aware_instant(persisted["artifact_asof"])
        if persisted_utc is None or persisted_utc != artifact_utc:
            return None
    return delivery_id


def _observed_at(clock: Callable[[], Any]) -> datetime | None:
    """Sample the clock and normalize; a naive clock is read as UTC."""
    try:
        sampled = clock()
    except Exception:
        return None
    if not isinstance(sampled, datetime):
        return None
    if sampled.tzinfo is None:
        return sampled.replace(tzinfo=timezone.utc)
    try:
        return sampled.astimezone(timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def observe_delivery_write(
    pg: Callable[..., Any],
    row: Any,
    expected_owner_id: Any,
    *,
    dry_run: bool = False,
    clock: Callable[[], datetime] = _utc_clock,
) -> DeliveryWriteObservation:
    """Write one ready delivery row as the incumbent producer would, then
    confirm the persisted row with a single owner readback.

    ``pg`` is the incumbent PostgREST transport (``_pg`` in the writer).
    Exactly one original POST is attempted; the single readback GET happens
    only after an acknowledged or duplicate (409 + 23505) write, or a
    transport-ambiguous one.  Any provider HTTP refusal, SQL permission code
    stops with ``REFUSED`` and no read recovery. An opaque programmer failure
    leaves an unconfirmed POST outcome and performs no automatic read recovery.
    Validation failures and dry runs touch no network at all.

    ``artifact_asof`` is matched by UTC instant, not by string, so equivalent
    offsets qualify.  The receipt claims only the locally observed row.
    """
    if dry_run:
        return DeliveryWriteObservation(PostOutcome.NOT_ATTEMPTED, None, ObservationReason.DRY_RUN)

    validated, input_reason = _classify_input(row, expected_owner_id)
    if validated is None or input_reason is not None:
        return DeliveryWriteObservation(PostOutcome.NOT_ATTEMPTED, None, input_reason or ObservationReason.INPUT_INVALID)

    artifact_utc = (
        None if validated["artifact_asof"] is None else _aware_instant(validated["artifact_asof"])
    )

    try:
        pg("POST", POST_PATH, body=copy.deepcopy(validated), prefer=POST_PREFER, timeout=CALL_TIMEOUT_SECONDS)
    except HTTPError as exc:
        text = _bounded_error_text(exc)
        # An actual refusal cannot become duplicate recovery because a detail
        # string happens to mention 23505. Require the structured owner code,
        # and give explicit permission evidence precedence over conflict text.
        status = getattr(exc, "code", None)
        permission_denied = status in {401, 403} or "42501" in text or "permission denied" in text.lower()
        try:
            error = json.loads(text)
        except (ValueError, TypeError):
            error = None
        if permission_denied:
            return DeliveryWriteObservation(PostOutcome.REFUSED, None, ObservationReason.PERMISSION_DENIED)
        if status == 409 and isinstance(error, dict) and error.get("code") == "23505":
            post_outcome = PostOutcome.DUPLICATE
        elif status in {429, 451}:
            return DeliveryWriteObservation(PostOutcome.REFUSED, None, ObservationReason.PROVIDER_REFUSED)
        elif status == 408 or isinstance(status, int) and 500 <= status <= 599:
            # A server/timeout error is not evidence of permission refusal or
            # absence of an effect. Keep it unconfirmed without automatic GET.
            return DeliveryWriteObservation(PostOutcome.AMBIGUOUS, None, ObservationReason.HTTP_UNCONFIRMED)
        else:
            return DeliveryWriteObservation(PostOutcome.REFUSED, None, ObservationReason.REQUEST_REJECTED)
    except (URLError, TimeoutError, ConnectionError):
        # Transport loss: the write may or may not have persisted.
        post_outcome = PostOutcome.AMBIGUOUS
    except Exception:
        return DeliveryWriteObservation(PostOutcome.AMBIGUOUS, None, ObservationReason.PROGRAMMER_ERROR)
    else:
        post_outcome = PostOutcome.ACKNOWLEDGED

    try:
        rows = pg(
            "GET",
            _readback_path(validated["subscription_id"], validated["slot_asof"], expected_owner_id),
            timeout=CALL_TIMEOUT_SECONDS,
        )
    except HTTPError as exc:
        text = _bounded_error_text(exc)
        status = getattr(exc, "code", None)
        reason = (ObservationReason.PERMISSION_DENIED if status in {401, 403} or "42501" in text or "permission denied" in text.lower()
                  else ObservationReason.PROVIDER_REFUSED if status in {429, 451}
                  else ObservationReason.READBACK_UNAVAILABLE)
        return DeliveryWriteObservation(post_outcome, None, reason)
    except Exception:
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.READBACK_UNAVAILABLE)
    if not isinstance(rows, list):
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.READBACK_UNAVAILABLE)
    if not rows:
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.READBACK_MISSING)
    if len(rows) > 1:
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.READBACK_AMBIGUOUS)

    delivery_id = _qualified_delivery_id(rows[0], validated, expected_owner_id, artifact_utc)
    if delivery_id is None:
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.READBACK_MISMATCH)

    observed_utc = _observed_at(clock)
    if observed_utc is None:
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.PROGRAMMER_ERROR)

    document = {
        "schema": _OBSERVATION_SCHEMA,
        "delivery_id": delivery_id,
        "subscription_id": validated["subscription_id"],
        "slot_asof": validated["slot_asof"],
        "state": "ready",
        "degraded_reason": None,
        "artifact_asof": None if artifact_utc is None else artifact_utc.isoformat(),
        "body": validated["body"],
        "owner_user_id": expected_owner_id,
        "observed_at": observed_utc.isoformat(),
    }
    encoded = _canonical_json(document)
    if encoded is None:
        return DeliveryWriteObservation(post_outcome, None, ObservationReason.READBACK_MISMATCH)

    receipt = PersistedDeliveryObservation(
        delivery_id=delivery_id,
        slot_asof=validated["slot_asof"],
        observed_at=observed_utc.isoformat(),
        observation_sha256=hashlib.sha256(encoded).hexdigest(),
    )
    return DeliveryWriteObservation(post_outcome, receipt, ObservationReason.READBACK_MATCHED)
