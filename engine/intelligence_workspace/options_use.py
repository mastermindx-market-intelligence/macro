"""Short-lived source-use gate in front of an already-verified Options Matrix selection.

This module is source preparation, NOT a rights authority and NOT a grant:

* It creates no product entitlements, rights rules, registry contents, policy
  clocks, source-family enrollment or authentication records.
* It cannot authenticate the caller, the callback transport or the source
  family.  The caller must authenticate the principal and wire genuine, fresh
  server-side callbacks; nothing here can validate that trust.  No callback,
  token or decision that originates from a browser is treated as authority.
* Freshness checks (``t0 <= t1 <= t2`` and ``t1 <= decided_at <= t2``) prove
  only that one observed callback interval is internally consistent for this
  single call.  They do not create perpetual, replayable or atomic authority.
* The returned :class:`AuthorizedOptionSelection` is a short-lived in-process
  use result.  It is not a capability, not a replayable receipt and not a Save
  authorization; it must not be persisted or replayed.

The existing :func:`resolve_option_matrix_selection` remains the only validator
of immutable raw bytes, capture clocks, canonical current-record identity and
own-side membership; this module neither reimplements nor relaxes it and stays
separate from the shared entity/rights parsing (the selection-cohort-only
``rights_use`` module is deliberately not reused or adapted here).

There is no configured real Options rights backend yet: every refusal path
fails closed, and nothing in this module invents a policy or a permissive
default.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .entity import IdentityResolutionError
from .options_identity import resolve_option_matrix_selection

__all__ = [
    "AuthorizedOptionSelection",
    "OptionUseRefused",
    "OptionUseRequest",
    "resolve_authorized_option_selection",
]

OWNER = "options_structure.matrix"
SCHEMA = "options_structure.matrix/v1"

_MAX_SCALAR_BYTES = 256
_ACTIONS = ("display", "export")

# Closed response shape of a source-use decision.  Extra or missing keys are
# refused regardless of the claimed status.
_RESPONSE_KEYS = frozenset(
    {
        "status",
        "binding",
        "source_family",
        "policy_id",
        "policy_revision",
        "registry_revision",
        "decided_at",
    }
)

_REQUEST_FIELDS = (
    "request_id",
    "principal_id",
    "principal_issuer",
    "auth_epoch",
    "owner",
    "schema",
    "root",
    "sha256",
    "byte_length",
    "session",
    "vendor",
    "underlying_id",
    "selection_sha256",
    "action",
)

# Strict aware instant: RFC3339/ISO-8601 with a "T" separator and either "Z"
# or a numeric "+HH:MM"/"-HH:MM" offset.  Date-only, naive and compact-offset
# forms are deliberately rejected; no implicit timezone correction is applied.
_INSTANT_PATTERN = re.compile(
    r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])\Z"
)


class OptionUseRefused(ValueError):
    """Raised for every refusal.

    ``code`` is a stable machine-readable string.  Refusals never carry raw
    callback exception details and never release any validated value.
    """

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True, slots=True)
class OptionUseRequest:
    """Immutable use request bound to one verified selection snapshot.

    ``request_id`` is a fresh ``uuid4().hex`` per resolver invocation, so a
    source decision observed for an earlier call can never be replayed as the
    binding of a new call, even under a frozen clock.  ``root``/``sha256``/
    ``byte_length``/``session`` come only from the snapshot reference; callers
    cannot supply a replacement root, subject or digest.  ``underlying_id`` is
    the canonical ``security_id`` of the verified underlying binding.
    """

    request_id: str
    principal_id: str
    principal_issuer: str
    auth_epoch: str
    owner: str
    schema: str
    root: str
    sha256: str
    byte_length: int
    session: str | None
    vendor: str
    underlying_id: str
    selection_sha256: str
    action: str

    def as_dict(self) -> dict[str, Any]:
        """Return a fresh plain dict of exactly the request fields."""
        return {
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "principal_issuer": self.principal_issuer,
            "auth_epoch": self.auth_epoch,
            "owner": self.owner,
            "schema": self.schema,
            "root": self.root,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "session": self.session,
            "vendor": self.vendor,
            "underlying_id": self.underlying_id,
            "selection_sha256": self.selection_sha256,
            "action": self.action,
        }


@dataclass(frozen=True, slots=True)
class AuthorizedOptionSelection:
    """Short-lived in-process use result, not a replayable capability.

    ``selection`` is the already-verified existing selection result and
    ``decided_at`` is the source decision instant normalized to UTC.  This
    object authorizes nothing by existing; it is the record of one validated
    use decision and is not a Save authorization.
    """

    selection: Any
    request: OptionUseRequest
    source_family: str
    policy_id: str
    policy_revision: str
    registry_revision: str
    decided_at: datetime


def _is_valid_scalar(value: object) -> bool:
    """Bounded nonblank string: exactly ``str``, <=256 UTF-8 bytes, no
    leading/trailing whitespace and no control or unprintable characters."""
    if type(value) is not str:
        return False
    if not value:
        return False
    try:
        if len(value.encode("utf-8")) > _MAX_SCALAR_BYTES:
            return False
    except UnicodeError:
        return False
    if value != value.strip():
        return False
    if not value.isprintable():
        return False
    return True


def _parse_instant(value: object) -> datetime | None:
    """Parse a strict aware RFC3339/ISO instant and normalize it to UTC.

    Returns ``None`` for anything naive, date-only, malformed or out of range;
    no implicit timezone or clock correction is applied.
    """
    if type(value) is not str:
        return None
    if _INSTANT_PATTERN.match(value) is None:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _clock_moment(clock: Callable[[], datetime], label: str) -> datetime:
    """Read the clock seam and require an aware datetime; never correct it."""
    try:
        moment = clock()
    except Exception:
        raise OptionUseRefused("clock_invalid", f"{label} clock raised") from None
    if not isinstance(moment, datetime):
        raise OptionUseRefused("clock_invalid", f"{label} clock returned a non-datetime")
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise OptionUseRefused("clock_invalid", f"{label} clock returned a naive datetime")
    return moment


def resolve_authorized_option_selection(
    ref: Any,
    matrix: Any,
    selection: Any,
    *,
    vendor: str,
    principal_id: str,
    principal_issuer: str,
    auth_epoch: str,
    action: str,
    aliases: Any,
    security_master: Any,
    root_evidence: Any,
    fresh_entitlement: Callable[[OptionUseRequest], Any] | None = None,
    source_use_decision: Callable[[OptionUseRequest], Any] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> AuthorizedOptionSelection:
    """Re-release an already-verified Matrix selection behind fresh callbacks.

    Order of operations, all fail-closed:

    1. Validate the caller scalars and callback callables (no callback runs).
    2. ``t0 = clock()`` and run :func:`resolve_option_matrix_selection` -- the
       existing validator of raw bytes, capture clocks, canonical identity and
       membership.  Its failure is ``selection_unavailable`` with no values.
    3. Build the immutable :class:`OptionUseRequest` from the verified result
       and the exact selection bytes digest; callbacks cannot mutate bindings.
    4. ``fresh_entitlement(request)`` exactly once; only ``True`` (the bool)
       is accepted.  Exception -> ``entitlement_unavailable``; anything else ->
       ``entitlement_denied``.
    5. ``t1 = clock()``; require ``t1 >= t0``.
    6. ``source_use_decision(request)`` exactly once, on the fresh request of
       this invocation only.  Exception -> ``rights_unavailable``.
    7. ``t2 = clock()``; require ``t2 >= t1``.
    8. Validate the closed response shape, metadata and the ``t1 <=
       decided_at <= t2`` window, then return the use result.

    Any refusal raises :class:`OptionUseRefused` and releases no selection,
    binding or metadata value.
    """
    for name, value in (
        ("principal_id", principal_id),
        ("principal_issuer", principal_issuer),
        ("auth_epoch", auth_epoch),
        ("vendor", vendor),
    ):
        if not _is_valid_scalar(value):
            raise OptionUseRefused(
                "request_invalid", f"{name} must be a nonblank bounded string without control characters"
            )
    if type(action) is not str or action not in _ACTIONS:
        raise OptionUseRefused("request_invalid", "action must be 'display' or 'export'")

    if not callable(fresh_entitlement):
        raise OptionUseRefused("callback_invalid", "fresh_entitlement is missing or not callable")
    if not callable(source_use_decision):
        raise OptionUseRefused("callback_invalid", "source_use_decision is missing or not callable")

    if clock is None:
        clock = lambda: datetime.now(timezone.utc)
    t0 = _clock_moment(clock, "selection")

    try:
        verified = resolve_option_matrix_selection(
            ref,
            matrix,
            selection,
            vendor=vendor,
            decision_at=t0,
            aliases=aliases,
            security_master=security_master,
            root_evidence=root_evidence,
        )
        underlying_binding = verified.matrix.underlying.binding
        request = OptionUseRequest(
            request_id=uuid.uuid4().hex,
            principal_id=principal_id,
            principal_issuer=principal_issuer,
            auth_epoch=auth_epoch,
            owner=OWNER,
            schema=SCHEMA,
            root=ref.root,
            sha256=ref.sha256,
            byte_length=ref.byte_length,
            session=ref.session,
            vendor=vendor,
            underlying_id=underlying_binding.security_id,
            selection_sha256=hashlib.sha256(selection).hexdigest(),
            action=action,
        )
    except IdentityResolutionError:
        raise OptionUseRefused("selection_unavailable", "selection identity resolution failed") from None
    except Exception:
        raise OptionUseRefused("selection_unavailable", "selection identity resolution failed") from None

    try:
        entitled = fresh_entitlement(request)
    except Exception:
        raise OptionUseRefused("entitlement_unavailable", "entitlement callback failed") from None
    if entitled is not True:
        raise OptionUseRefused("entitlement_denied", "fresh product entitlement is not granted")

    t1 = _clock_moment(clock, "use")
    if t1 < t0:
        raise OptionUseRefused("clock_invalid", "use clock moved backwards")

    try:
        decision = source_use_decision(request)
    except Exception:
        raise OptionUseRefused("rights_unavailable", "source-use callback failed") from None

    t2 = _clock_moment(clock, "decision")
    if t2 < t1:
        raise OptionUseRefused("clock_invalid", "decision clock moved backwards")

    if type(decision) is not dict:
        raise OptionUseRefused("source_decision_invalid", "source decision is not a plain dict")
    if set(decision) != _RESPONSE_KEYS:
        raise OptionUseRefused("source_decision_invalid", "source decision keys are not the closed set")

    status = decision["status"]
    if type(status) is not str:
        raise OptionUseRefused("source_decision_invalid", "status is not a string")

    for field in ("source_family", "policy_id", "policy_revision", "registry_revision"):
        if not _is_valid_scalar(decision[field]):
            raise OptionUseRefused("source_decision_invalid", f"{field} metadata is invalid")

    decided_at = _parse_instant(decision["decided_at"])
    if decided_at is None:
        raise OptionUseRefused("source_decision_invalid", "decided_at is not a strict aware instant")

    binding = decision["binding"]
    if type(binding) is not dict:
        raise OptionUseRefused("source_decision_invalid", "binding is not a plain dict")
    expected = request.as_dict()
    if set(binding) != set(expected):
        raise OptionUseRefused("source_decision_invalid", "binding keys do not match the request fields")
    for field, want in expected.items():
        got = binding[field]
        if type(got) is not type(want) or got != want:
            raise OptionUseRefused("source_decision_invalid", f"binding field {field} does not match the request")

    if status == "denied":
        raise OptionUseRefused("source_denied", "source-use decision denied the action")
    if status == "unavailable":
        raise OptionUseRefused("source_unavailable", "source-use decision is unavailable")
    if status != "allowed":
        raise OptionUseRefused("source_decision_invalid", "status is not a known decision value")

    if decided_at < t1 or decided_at > t2:
        raise OptionUseRefused("source_decision_invalid", "decided_at is outside the observed callback window")

    return AuthorizedOptionSelection(
        selection=verified,
        request=request,
        source_family=decision["source_family"],
        policy_id=decision["policy_id"],
        policy_revision=decision["policy_revision"],
        registry_revision=decision["registry_revision"],
        decided_at=decided_at,
    )
