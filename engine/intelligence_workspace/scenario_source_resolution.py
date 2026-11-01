"""Protected source resolution for one saved Investigation exposure scenario.

Pure in-process orchestration only. This module is not a network endpoint, it
serializes no generic projection, it creates no policy, entitlement, signing
secret, receipt or rights record, and it reimplements no math: the scenario
evaluation itself stays with its own owner.

Contract, all fail-closed and ordered:

1. The descriptor pins, explicitly and typed: the retained GEX reference (and
   an optional retained moves reference), the canonical lowercase Investigation
   UUID, the exact positive native revision integer, the recipient grant UUID
   (or ``None`` in owner context), the exact native model version
   ``exposure-scenario/v1``, the captured lens object and canonical comma-joined
   ``expiry|economic_expiry_at`` selection key (never re-evaluated on the
   current clock; the one/zero lenses constrain the captured expiry SET, while
   multiple economic instants for one expiry stay valid), the explicit source
   clock — a canonical date or a strict aware instant, preserved verbatim, or
   ``None`` when unknown — the protected basis digest as a reference
   binding, and the captured timezone-aware evaluation instant.
2. The current authorization clock is read from its own seam and is distinct
   from the captured evaluation instant; a capture from "after" the current
   authorization instant refuses.
3. Two fresh trusted server callbacks must qualify the exact bound viewer,
   resource, revision, source references, model version and selection BEFORE
   any retained byte is read: a current resource-access callback and a native
   viewer/action source-use callback. A false resource answer is a typed
   denial; ``None``, unknown, malformed or exceptional answers are typed
   unavailable, never a fabricated denial. Absent callbacks fail typed with
   zero protected reads.
4. A trusted SERVER destination qualification seam must qualify this bucket
   and all affected refs before any protected IO, and every protected read
   then goes through the same seam inside
   :mod:`engine.options_hub_retention`; there is no internal unqualified read
   path. Absent, exceptional, unknown, refusing or mismatched qualification is
   a typed unavailable/denied refusal with zero protected reads.
5. Only then are the exact retained objects read. A supplied moves reference
   that cannot be resolved is an explicit refusal, never a silent substitution.
6. Resource authorization is re-checked after the protected IO to catch a
   concurrent revoke, and the current viewer binding is re-read when a seam is
   supplied. Any change refuses and no result is produced.
7. The result carries verified payloads for in-process use only; the
   persistable boundary (:meth:`ResolvedScenarioSource.boundary`) aligns with
   the frozen reference-only capture interface — owner, root, session,
   ``source_as_of``, ``evaluated_at``, the strict lens object (``{kind}`` or
   ``{kind: "one", exp}`` exactly as the capture contract stores it), selection
   key, basis digest and the gex/moves sha256 plus byte lengths (moves
   ``None`` when absent) — and never exposes source or derived values, grant
   identities, decision metadata or payload contents. Every boundary call
   rebuilds fresh containers: it never aliases descriptor or request state.

No real rights backend is configured: the default for every callback is a typed
unavailable refusal. Successful callback tests establish orchestration only and
are not evidence of real rights qualification. Historical owner entitlements,
grant or reference digests, caller browser claims, public URLs and defaults
authorize nothing here.
"""
from __future__ import annotations

import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, replace, field
from types import MappingProxyType
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from engine.options_hub_retention import (
    DestinationDenied,
    MissingRetainedObject,
    RetentionUnavailable,
    SnapshotReference,
    load_verified,
    qualify_destination,
    validate_reference,
    validate_root,
)

__all__ = [
    "MODEL_VERSION",
    "ResolvedScenarioSource",
    "ScenarioSourceDescriptor",
    "ScenarioSourceRefused",
    "ScenarioSourceRequest",
    "ViewerIdentity",
    "resolve_scenario_source",
]

MODEL_VERSION = "exposure-scenario/v1"
RESOURCE_OWNER = "options_hub"
_GEX_KIND = "gex"
_MOVES_KIND = "moves"
_ACTIONS = ("evaluate", "display", "export")
_LENSES = frozenset({"all", "zero", "one", "next-live", "week"})
_MAX_SELECTION_PAIRS = 128
_MAX_SELECTION_BYTES = 16 * 1024
_MAX_REVISION = 2147483647
_MAX_SCALAR_BYTES = 256

_REQUEST_FIELDS = (
    "request_id",
    "viewer_id",
    "viewer_issuer",
    "auth_epoch",
    "resource_owner",
    "resource_kind",
    "root",
    "sha256",
    "byte_length",
    "session",
    "moves_ref",
    "model_version",
    "lens",
    "selection_key",
    "source_as_of",
    "basis_sha256",
    "action",
    "investigation_id",
    "investigation_revision",
    "grant_id",
    "evaluated_at",
)

_DECISION_KEYS = frozenset(
    {"status", "binding", "policy_id", "policy_revision", "registry_revision", "decided_at"}
)

# Strict aware instant: RFC3339/ISO-8601 with a "T"/"t" separator and "Z"/"z"
# or a numeric offset, 1-9 fraction digits (the current capture parser's
# grammar). Naive, date-only, compact-offset and leap-second forms refuse.
_INSTANT = re.compile(
    r"\A(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))"
    r"?(?:[Zz]|([+-])(\d{2}):(\d{2}))\Z"
)
_ISO_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
_UUID = re.compile(
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
_SHA = re.compile(r"\A[0-9a-f]{64}\Z")


class ScenarioSourceRefused(ValueError):
    """Raised for every refusal.

    ``code`` is a stable machine-readable string that distinguishes denied from
    authorization/source/destination unavailable. Refusals never carry
    protected payload contents, callback exception details or validated values.
    """

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class ViewerIdentity:
    """The current authenticated viewer, as asserted by the calling server."""

    viewer_id: str
    viewer_issuer: str
    auth_epoch: str


@dataclass(frozen=True)
class ScenarioSourceDescriptor:
    """Typed, deliberately pinned source request for one saved scenario.

    ``gex`` must be a retained ``gex`` reference and ``moves`` either ``None``
    or a retained ``moves`` reference. ``investigation_id`` is the canonical
    lowercase Investigation UUID, ``investigation_revision`` is the exact
    positive native revision integer and ``grant_id`` is the recipient grant
    UUID or ``None`` in owner context (where a genuine current resource
    callback proves the owner) — binding context for the callbacks only,
    neither authorizes anything here. ``lens`` with ``selection_key`` pins the
    exact captured expiry selection (the ``one``/``zero`` lens kinds constrain
    the captured expiry SET; several economic instants for one expiry remain
    valid); ``source_as_of`` is the explicit source clock — a canonical date
    or a strict aware instant, preserved verbatim — or ``None`` when unknown;
    ``evaluated_at`` is the captured timezone-aware evaluation instant;
    ``basis_sha256`` is a digest reference binding, not an assertion that any
    math was re-verified here. :meth:`ResolvedScenarioSource.boundary` emits
    the same strict frozen lens object, never an inferred or bare kind string.
    """

    root: str
    gex: SnapshotReference
    moves: SnapshotReference | None
    investigation_id: str
    investigation_revision: int
    grant_id: str | None
    model_version: str
    lens: Mapping[str, str]
    selection_key: str
    source_as_of: str | None
    basis_sha256: str
    evaluated_at: str
    action: str


@dataclass(frozen=True, slots=True)
class ScenarioSourceRequest:
    """Immutable bound request; callbacks cannot mutate its fields."""

    request_id: str
    viewer_id: str
    viewer_issuer: str
    auth_epoch: str
    resource_owner: str
    resource_kind: str
    root: str
    sha256: str
    byte_length: int
    session: str
    moves_ref: str | None
    model_version: str
    lens: Mapping[str, str]
    selection_key: str
    source_as_of: str | None
    basis_sha256: str
    action: str
    investigation_id: str
    investigation_revision: int
    grant_id: str | None
    evaluated_at: str

    def as_dict(self) -> dict[str, Any]:
        """Return a fresh plain wire object, including a detached lens object."""
        return {field: dict(self.lens) if field == "lens" else getattr(self, field) for field in _REQUEST_FIELDS}


@dataclass(frozen=True)
class ResolvedScenarioSource:
    """In-process resolution of one protected scenario source.

    ``gex`` and ``moves`` are exact verified payloads for internal use only.
    They are not a serialized projection, not an RPC response and not a
    manifest; only :meth:`boundary` may leave the process boundary.
    """

    descriptor: ScenarioSourceDescriptor
    request: ScenarioSourceRequest
    gex: dict = field(repr=False)
    moves: dict | None = field(repr=False)
    gex_bytes: bytes = field(repr=False)
    moves_bytes: bytes | None = field(repr=False)
    moves_status: str  # "resolved" | "not_supplied"
    policy_id: str
    policy_revision: str
    registry_revision: str
    decided_at: datetime
    evaluated_at: datetime

    def boundary(self) -> dict[str, Any]:
        """Persistable source identity aligned with the frozen reference-only
        capture interface: native model version, immutable source references
        and digests, the captured lens/selection and clock. The lens is the
        strict frozen reference object — ``{"kind": ...}``, or
        ``{"kind": "one", "exp": ...}`` with the exact deliberately captured expiry — never the bare kind string. ``source_as_of``
        stays the exact captured date-or-aware-instant verbatim, or ``None``.
        Never source or derived values, never payload contents, never grant or
        decision metadata, never a generic projection. Every call rebuilds
        fresh containers and nothing aliases descriptor or request state."""
        moves = self.descriptor.moves
        lens = dict(self.request.lens)
        return {
            "model_version": self.request.model_version,
            "action": self.request.action,
            "investigation_id": self.request.investigation_id,
            "investigation_revision": self.request.investigation_revision,
            "moves_status": self.moves_status,
            "source": {
                "owner": self.request.resource_owner,
                "root": self.request.root,
                "session": self.request.session,
                "source_as_of": self.descriptor.source_as_of,
                "evaluated_at": self.descriptor.evaluated_at,
                "lens": lens,
                "selection_key": self.descriptor.selection_key,
                "basis_sha256": self.descriptor.basis_sha256,
                "gex": {"sha256": self.descriptor.gex.sha256,
                        "byte_length": self.descriptor.gex.byte_length},
                "moves": None if moves is None else {
                    "sha256": moves.sha256, "byte_length": moves.byte_length},
            },
        }


def _is_valid_scalar(value: object) -> bool:
    if type(value) is not str or not value:
        return False
    try:
        if len(value.encode("utf-8")) > _MAX_SCALAR_BYTES:
            return False
    except UnicodeError:
        return False
    return value == value.strip() and value.isprintable()


def _parse_instant(value: object) -> datetime | None:
    """Parse a strict aware instant and normalize it to UTC; never corrects.

    ``t``/``z`` lowercase is accepted (RFC 3339 permits it) and 1-9 fraction
    digits, matching the current capture parser's clock grammar; the original
    string is never altered and no other form is coerced into an instant.
    """
    if type(value) is not str:
        return None
    match = _INSTANT.match(value)
    if match is None:
        return None
    try:
        moment = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                          int(match.group(4)), int(match.group(5)), int(match.group(6)),
                          tzinfo=timezone.utc)
    except ValueError:
        return None
    if match.group(8) is not None:
        if int(match.group(9)) > 23 or int(match.group(10)) > 59:
            return None
        offset = timedelta(hours=int(match.group(9)), minutes=int(match.group(10)))
        moment = moment.replace(tzinfo=timezone(-offset if match.group(8) == "-" else offset))
    fraction = match.group(7) or ""
    try:
        return moment.replace(microsecond=int(fraction[:6].ljust(6, "0"))).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _instant_order(value: object) -> tuple[datetime, str] | None:
    """Exact ordering key for a strict aware instant: the UTC moment plus the
    fraction zero-padded to nine digits, so two declared instants compare
    exactly via the offsets and fractions they carry — never a timezone
    database and never a textual date comparison."""
    if type(value) is not str or _INSTANT.match(value) is None:
        return None
    moment = _parse_instant(value)
    if moment is None:
        return None
    return moment, (_INSTANT.match(value).group(7) or "").ljust(9, "0")


def _iso_date(value: object) -> str | None:
    if type(value) is not str or _ISO_DATE.match(value) is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _parse_selection(selection_key: object) -> list[tuple[str, str]]:
    """Parse the canonical comma-joined ``expiry|economic_expiry_at`` pairs.

    This is the exact captured native read selection: unique, strictly sorted,
    bounded, with a real ISO date and a strict aware instant per pair. It is
    preserved verbatim and never re-evaluated on the current clock.
    """
    if type(selection_key) is not str or not selection_key:
        raise ScenarioSourceRefused("request_invalid", "selection key is not a captured canonical selection")
    try:
        encoded = selection_key.encode("utf-8")
    except UnicodeError:
        raise ScenarioSourceRefused("request_invalid", "selection key is not encodable") from None
    if len(encoded) > _MAX_SELECTION_BYTES:
        raise ScenarioSourceRefused("request_invalid", "selection key exceeds the captured byte bound")
    parts = selection_key.split(",")
    if len(parts) > _MAX_SELECTION_PAIRS:
        raise ScenarioSourceRefused("request_invalid", "selection key exceeds the captured pair bound")
    pairs = []
    for part in parts:
        if part.count("|") != 1:
            raise ScenarioSourceRefused("request_invalid", "selection pair is not expiry|economic_expiry_at")
        expiry, economic = part.split("|")
        if _iso_date(expiry) is None or _parse_instant(economic) is None:
            raise ScenarioSourceRefused("request_invalid", "selection pair is not expiry|economic_expiry_at")
        pairs.append((expiry, economic))
    if len(set(pairs)) != len(pairs) or pairs != sorted(pairs):
        raise ScenarioSourceRefused("request_invalid", "selection pairs are not unique and strictly sorted")
    return pairs


def _clock_moment(clock: Callable[[], datetime], label: str) -> datetime:
    try:
        moment = clock()
    except Exception:
        raise ScenarioSourceRefused("clock_invalid", f"{label} clock raised") from None
    if not isinstance(moment, datetime):
        raise ScenarioSourceRefused("clock_invalid", f"{label} clock returned a non-datetime")
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ScenarioSourceRefused("clock_invalid", f"{label} clock returned a naive datetime")
    return moment


def _check_source_clocks(descriptor: ScenarioSourceDescriptor, pairs, evaluated: datetime) -> None:
    """Order the captured clocks; an unknown source clock stays explicit null.

    ``source_as_of`` may be a canonical date or a strict aware instant. A date
    is ordered by its calendar date; an instant is ordered exactly against the
    captured evaluation via the offsets both strings carry.
    """
    cap_date = date.fromisoformat(descriptor.evaluated_at[:10])
    session_date = date.fromisoformat(descriptor.gex.session)
    if cap_date < session_date:
        raise ScenarioSourceRefused("request_invalid", "evaluated_at precedes the captured source session")
    if descriptor.source_as_of is not None:
        as_of_date = _iso_date(descriptor.source_as_of)
        if as_of_date is not None:
            if date.fromisoformat(as_of_date) > cap_date:
                raise ScenarioSourceRefused("request_invalid", "source_as_of is after the captured evaluation")
        else:
            src = _instant_order(descriptor.source_as_of)
            ev = _instant_order(descriptor.evaluated_at)
            if src is None or ev is None or src > ev:
                raise ScenarioSourceRefused("request_invalid", "source_as_of is after the captured evaluation")
    for expiry, _economic in pairs:
        if date.fromisoformat(expiry) < session_date:
            raise ScenarioSourceRefused("request_invalid", "selection expiry precedes the captured source session")


def _validate_descriptor(descriptor: ScenarioSourceDescriptor) -> datetime:
    """Validate every pinned field; returns the captured evaluation instant."""
    if not isinstance(descriptor, ScenarioSourceDescriptor):
        raise ScenarioSourceRefused("request_invalid", "descriptor is not a typed descriptor")
    validate_root(descriptor.root)
    if len(descriptor.root) > 12 or re.fullmatch(r"[A-Z0-9]{1,10}(?:[.-][A-Z0-9]{1,4})?", descriptor.root) is None:
        raise ScenarioSourceRefused("request_invalid", "root does not match the native reference wire")
    if not isinstance(descriptor.gex, SnapshotReference) or descriptor.gex.kind != _GEX_KIND:
        raise ScenarioSourceRefused("request_invalid", "gex reference is not a retained gex reference")
    validate_reference(descriptor.gex)
    if descriptor.gex.root != descriptor.root:
        raise ScenarioSourceRefused("request_invalid", "gex reference root mismatch")
    if descriptor.moves is not None:
        if not isinstance(descriptor.moves, SnapshotReference) or descriptor.moves.kind != _MOVES_KIND:
            raise ScenarioSourceRefused("request_invalid", "moves reference is not a retained moves reference")
        validate_reference(descriptor.moves)
        if descriptor.moves.root != descriptor.root:
            raise ScenarioSourceRefused("request_invalid", "moves reference root mismatch")
    if type(descriptor.investigation_id) is not str or not _UUID.match(descriptor.investigation_id):
        raise ScenarioSourceRefused("request_invalid", "investigation id is not a canonical uuid")
    revision = descriptor.investigation_revision
    if type(revision) is not int or revision < 1 or revision > _MAX_REVISION:
        raise ScenarioSourceRefused("request_invalid", "investigation revision is not a positive native integer")
    if descriptor.grant_id is not None and not (
        type(descriptor.grant_id) is str and _UUID.match(descriptor.grant_id)
    ):
        raise ScenarioSourceRefused("request_invalid", "grant id is not a canonical recipient uuid")
    if descriptor.model_version != MODEL_VERSION:
        raise ScenarioSourceRefused("model_version_unsupported", "native model version is not pinned")
    lens = descriptor.lens
    if type(lens) is not dict or type(lens.get("kind")) is not str or lens["kind"] not in _LENSES:
        raise ScenarioSourceRefused("request_invalid", "lens is not the closed native wire object")
    kind = lens["kind"]
    if set(lens) != ({"kind", "exp"} if kind == "one" else {"kind"}):
        raise ScenarioSourceRefused("request_invalid", "lens keys do not match the native wire object")
    if kind == "one" and _iso_date(lens["exp"]) is None:
        raise ScenarioSourceRefused("request_invalid", "one lens has no exact captured expiry")
    pairs = _parse_selection(descriptor.selection_key)
    # The one/zero lens kinds constrain the captured expiry SET exactly as the
    # frozen capture contract does: `one` selects a single expiry (several
    # economic instants for it stay valid), `zero` selects only the source
    # session. Neither is ever flattened from, or re-evaluated against, the
    # selection on the current clock.
    expiries = {expiry for expiry, _economic in pairs}
    if kind == "one" and expiries != {lens["exp"]}:
        raise ScenarioSourceRefused("request_invalid", "one-expiry lens must select exactly one expiry")
    if kind == "zero" and expiries != {descriptor.gex.session}:
        raise ScenarioSourceRefused("request_invalid", "zero lens captured selection is not the source session only")
    if type(descriptor.basis_sha256) is not str or _SHA.match(descriptor.basis_sha256) is None:
        raise ScenarioSourceRefused("request_invalid", "basis digest is not a sha256 reference binding")
    if descriptor.source_as_of is not None and _iso_date(descriptor.source_as_of) is None \
            and _instant_order(descriptor.source_as_of) is None:
        raise ScenarioSourceRefused("request_invalid", "source_as_of is not an exact source clock")
    evaluated = _parse_instant(descriptor.evaluated_at)
    if evaluated is None:
        raise ScenarioSourceRefused("request_invalid", "evaluated_at is not an exact aware instant")
    _check_source_clocks(descriptor, pairs, evaluated)
    if descriptor.action not in _ACTIONS:
        raise ScenarioSourceRefused("request_invalid", "action is not a known scenario action")
    return evaluated


def resolve_scenario_source(
    descriptor: ScenarioSourceDescriptor,
    viewer: ViewerIdentity,
    *,
    s3,
    bucket: str,
    destination=None,
    resource_access: Callable[[dict], Any] | None = None,
    source_use_decision: Callable[[dict], Any] | None = None,
    clock: Callable[[], datetime] | None = None,
    current_viewer: Callable[[], ViewerIdentity] | None = None,
) -> ResolvedScenarioSource:
    """Resolve the retained source of one saved scenario behind fresh callbacks.

    Every refusal raises :class:`ScenarioSourceRefused` with a typed code and
    releases no protected content. Zero protected reads happen before the
    callbacks have qualified this exact binding AND the trusted server
    destination seam has qualified this bucket and ref set.
    """
    evaluated = _validate_descriptor(descriptor)
    # Detach and freeze the accepted wire lens before any trusted callback can run.
    descriptor = replace(descriptor, lens=MappingProxyType(dict(descriptor.lens)))
    if not isinstance(viewer, ViewerIdentity):
        raise ScenarioSourceRefused("request_invalid", "viewer is not a typed current viewer")
    for name, value in (("viewer_id", viewer.viewer_id),
                        ("viewer_issuer", viewer.viewer_issuer),
                        ("auth_epoch", viewer.auth_epoch)):
        if not _is_valid_scalar(value):
            raise ScenarioSourceRefused("request_invalid", f"{name} is not a bounded record")

    # No configured backend exists: the default for every callback is a typed
    # unavailable refusal, and nothing below runs without both callbacks.
    if not callable(resource_access) or not callable(source_use_decision):
        raise ScenarioSourceRefused("authorization_unavailable", "no current source authorization backend")

    if clock is None:
        clock = lambda: datetime.now(timezone.utc)  # noqa: E731

    t0 = _clock_moment(clock, "authorization")
    # The captured evaluation clock and the current authorization clock are
    # distinct; a capture recorded after the current authorization instant
    # refuses rather than being silently corrected.
    if _instant_order(descriptor.evaluated_at) > _instant_order(t0.isoformat()):
        raise ScenarioSourceRefused("clock_invalid", "captured instant is after the authorization clock")

    request = ScenarioSourceRequest(
        request_id=uuid.uuid4().hex,
        viewer_id=viewer.viewer_id,
        viewer_issuer=viewer.viewer_issuer,
        auth_epoch=viewer.auth_epoch,
        resource_owner=RESOURCE_OWNER,
        resource_kind=_GEX_KIND,
        root=descriptor.gex.root,
        sha256=descriptor.gex.sha256,
        byte_length=descriptor.gex.byte_length,
        session=descriptor.gex.session,
        moves_ref=None if descriptor.moves is None else descriptor.moves.version_ref,
        model_version=descriptor.model_version,
        lens=descriptor.lens,
        selection_key=descriptor.selection_key,
        source_as_of=descriptor.source_as_of,
        basis_sha256=descriptor.basis_sha256,
        action=descriptor.action,
        investigation_id=descriptor.investigation_id,
        investigation_revision=descriptor.investigation_revision,
        grant_id=descriptor.grant_id,
        evaluated_at=descriptor.evaluated_at,
    )
    binding = request.as_dict()

    # --- authorization boundary: both callbacks before any protected read ----
    try:
        accessible = resource_access(deepcopy(binding))
    except Exception:
        raise ScenarioSourceRefused("resource_unavailable", "resource access callback failed") from None
    if accessible is True:
        pass
    elif accessible is False:
        raise ScenarioSourceRefused("resource_denied", "current resource access is not granted")
    else:
        # None, unknown or malformed answers are typed unavailable, never a
        # fabricated denial.
        raise ScenarioSourceRefused("resource_unavailable", "resource access callback returned no decision")

    t1 = _clock_moment(clock, "use")
    if t1 < t0:
        raise ScenarioSourceRefused("clock_invalid", "use clock moved backwards")

    try:
        decision = source_use_decision(deepcopy(binding))
    except Exception:
        raise ScenarioSourceRefused("source_unavailable", "source-use callback failed") from None

    t2 = _clock_moment(clock, "decision")
    if t2 < t1:
        raise ScenarioSourceRefused("clock_invalid", "decision clock moved backwards")

    if type(decision) is not dict:
        raise ScenarioSourceRefused("source_decision_invalid", "source decision is not a plain dict")
    if set(decision) != _DECISION_KEYS:
        raise ScenarioSourceRefused("source_decision_invalid", "source decision keys are not the closed set")
    status = decision["status"]
    if type(status) is not str:
        raise ScenarioSourceRefused("source_decision_invalid", "status is not a string")
    for field in ("policy_id", "policy_revision", "registry_revision"):
        if not _is_valid_scalar(decision[field]):
            raise ScenarioSourceRefused("source_decision_invalid", f"{field} metadata is invalid")
    decided_at = _parse_instant(decision["decided_at"])
    if decided_at is None:
        raise ScenarioSourceRefused("source_decision_invalid", "decided_at is not a strict aware instant")

    decision_binding = decision["binding"]
    if type(decision_binding) is not dict:
        raise ScenarioSourceRefused("source_decision_invalid", "source decision binding is not a plain dict")
    if set(decision_binding) != set(binding):
        raise ScenarioSourceRefused("source_decision_invalid", "source decision binding keys do not match")
    for field, want in binding.items():
        got = decision_binding[field]
        if type(got) is not type(want) or got != want:
            raise ScenarioSourceRefused("source_decision_invalid", "source decision binding does not match")

    if status == "denied":
        raise ScenarioSourceRefused("source_denied", "source-use decision denied the action")
    if status == "unavailable":
        raise ScenarioSourceRefused("source_unavailable", "source-use decision is unavailable")
    if status != "allowed":
        raise ScenarioSourceRefused("source_decision_invalid", "status is not a known decision value")
    if decided_at < t1 or decided_at > t2:
        raise ScenarioSourceRefused("source_decision_invalid", "decided_at is outside the observed window")

    # --- trusted SERVER destination gate: before any protected IO ------------
    refs = [descriptor.gex] if descriptor.moves is None else [descriptor.gex, descriptor.moves]
    try:
        qualify_destination(destination, bucket, "read", refs)
    except DestinationDenied as exc:
        raise ScenarioSourceRefused(
            "destination_denied", "trusted destination qualification refused the protected read") from exc
    except RetentionUnavailable as exc:
        raise ScenarioSourceRefused(
            "destination_unavailable", "no qualified trusted server destination for the protected read") from exc

    # --- protected IO: every read re-enters the same destination seam --------
    try:
        gex_bytes, gex_payload = load_verified(s3, bucket, descriptor.gex, destination=destination)
    except MissingRetainedObject as exc:
        raise ScenarioSourceRefused("retained_missing", "retained gex object is absent") from exc
    except RetentionUnavailable as exc:
        raise ScenarioSourceRefused("retained_unavailable", "retained gex object failed verification") from exc

    moves_payload = None
    moves_bytes = None
    moves_status = "not_supplied"
    if descriptor.moves is not None:
        # An explicitly supplied moves reference must resolve exactly; absence
        # is a typed refusal, never a silent substitution or a null basis.
        try:
            moves_bytes, moves_payload = load_verified(s3, bucket, descriptor.moves, destination=destination)
        except MissingRetainedObject as exc:
            raise ScenarioSourceRefused("retained_missing", "retained moves object is absent") from exc
        except RetentionUnavailable as exc:
            raise ScenarioSourceRefused("retained_unavailable", "retained moves object failed verification") from exc
        moves_status = "resolved"

    # --- concurrent-revoke and current-actor re-checks -----------------------
    try:
        still_accessible = resource_access(deepcopy(binding))
    except Exception:
        raise ScenarioSourceRefused("resource_unavailable", "resource access recheck failed") from None
    if still_accessible is True:
        pass
    elif still_accessible is False:
        raise ScenarioSourceRefused("resource_revoked", "resource access was revoked during the read")
    else:
        raise ScenarioSourceRefused("resource_unavailable", "resource access recheck returned no decision")

    if current_viewer is not None:
        try:
            now_viewer = current_viewer()
        except Exception:
            raise ScenarioSourceRefused("resource_unavailable", "current viewer seam failed") from None
        if not isinstance(now_viewer, ViewerIdentity) or (
            now_viewer.viewer_id != viewer.viewer_id
            or now_viewer.viewer_issuer != viewer.viewer_issuer
            or now_viewer.auth_epoch != viewer.auth_epoch
        ):
            raise ScenarioSourceRefused("current_actor_changed", "current viewer binding changed during the read")

    return ResolvedScenarioSource(
        descriptor=descriptor,
        request=request,
        gex=gex_payload,
        moves=moves_payload,
        gex_bytes=gex_bytes,
        moves_bytes=moves_bytes,
        moves_status=moves_status,
        policy_id=decision["policy_id"],
        policy_revision=decision["policy_revision"],
        registry_revision=decision["registry_revision"],
        decided_at=decided_at,
        evaluated_at=evaluated,
    )
