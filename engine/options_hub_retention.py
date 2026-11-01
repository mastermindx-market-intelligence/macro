"""Exact-byte retention for typed Options Hub GEX and moves artifacts.

This module adapts the incumbent matrix exact-byte retention semantics to the
existing ``options_hub`` owner namespace. It is PRIVATE server IO only: it is
never a network endpoint, never a rights authority, and never a wiring of the
nightly publisher. It establishes artifact identity only and grants neither
source-use rights nor any deployment readiness.

Core rules, all fail-closed:

* Every exact IO surface (:func:`load_snapshot`, :func:`load_verified`,
  :func:`retain_snapshot`, :func:`retain_before_publish`) requires a trusted
  SERVER destination qualification seam before any get or put. The default
  (no qualification backend) is a typed ``destination_unavailable`` refusal:
  no bucket string, caller-constructed record or boolean flag can unblock IO.
  The seam is one small closed request/response binding callback that binds
  the ``options_hub`` owner, the exact target bucket, the operation and every
  affected exact artifact reference. A successful controlled callback proves
  orchestration only; the genuine server wiring and a genuinely qualified
  destination receipt are configured elsewhere. Nothing here performs ACL
  verification or claims private-bucket proof.
* Retention-before-dependent-publication additionally requires a fresh
  trusted native retention decision callback bound to the exact action,
  principal, purpose, target and refs. The :class:`RetentionAction` record is
  caller context only and never authorizes alone; without a fresh decision
  backend nothing is read, written or published, and no rights receipt is
  minted here.
* Only the exact ``sha256`` keyed object is ever read. The mutable dated
  ``gex_history/{ROOT}/{date}.json`` objects and the mutable ``moves`` head are
  never read as substitutes, so date-corrected or stale data cannot be
  substituted for a saved replay.
* Retained payloads bind the exact native schema (``options_hub.gex/v1`` or
  ``options_hub.moves/v1``), the exact producer root and the exact source
  session. A matrix payload, a wrong-kind payload or a foreign root is never
  accepted as the other kind.
* JSON duplicate keys, nonfinite numbers, oversize bodies, malformed bytes and
  future-dated sessions are refused. Every reference and every artifact body
  is validated BEFORE any effect, so a malformed second artifact can never
  leave a partial first effect. No sufficient-statistics reconstruction and no
  Greek model live here.
* A conditional create reconciles this same key once after an uncertain put,
  without overwrite and without choosing a new key; a genuinely unresolved
  effect stays typed as :class:`RetentionUncertain`.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

GEX_SCHEMA = "options_hub.gex/v1"
MOVES_SCHEMA = "options_hub.moves/v1"
R2_PREFIX = "options_hub/"
OWNER = "options_hub"
MAX_GEX_BYTES = 8 * 1024 * 1024
MAX_MOVES_BYTES = 1 * 1024 * 1024

_KINDS = {"gex": GEX_SCHEMA, "moves": MOVES_SCHEMA}
_LIMITS = {"gex": MAX_GEX_BYTES, "moves": MAX_MOVES_BYTES}
_MAX_SCALAR_BYTES = 256
_OPERATIONS = ("read", "retain")

_ROOT = re.compile(r"[A-Z0-9](?:[A-Z0-9.-]{0,13}[A-Z0-9])?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_SHA = re.compile(r"[0-9a-f]{64}")
# Strict typed reference grammar: the artifact kind is part of the reference, so
# an untyped or foreign reference (including a matrix one) can never parse.
_REF = re.compile(
    r"sha256:([0-9a-f]{64}):bytes:([1-9][0-9]*):kind:(gex|moves):session:([0-9]{4}-[0-9]{2}-[0-9]{2})"
)


class RetentionUnavailable(ValueError):
    """Exact history cannot be established; never substitute a mutable head."""


class MissingRetainedObject(RetentionUnavailable):
    """The exact immutable key is absent; no dated/head fallback exists."""


class RetentionUncertain(RetentionUnavailable):
    """A conditional create may or may not have committed; the effect is unresolved."""


class RetentionUnauthorized(RetentionUnavailable):
    """No explicit caller-authorized retention action was supplied; no IO is performed."""


class DestinationUnavailable(RetentionUnavailable):
    """No trusted server destination qualification exists; no IO is performed."""


class DestinationDenied(RetentionUnavailable):
    """The trusted server destination qualification refused this target."""


class RetentionDecisionUnavailable(RetentionUnavailable):
    """No fresh trusted native retention decision is available; no IO, no publication."""


class RetentionDenied(RetentionUnavailable):
    """The fresh trusted native retention decision refused; no IO, no publication."""


def validate_root(root: str) -> str:
    """Use the existing Options producer root grammar without normalization."""
    if not isinstance(root, str) or not _ROOT.fullmatch(root) or ".." in root:
        raise RetentionUnavailable("invalid canonical producer root")
    return root


def _is_valid_scalar(value: object) -> bool:
    """Bounded nonblank string: exactly ``str``, small, no surrounding
    whitespace and no control or unprintable characters."""
    if type(value) is not str or not value:
        return False
    try:
        if len(value.encode("utf-8")) > _MAX_SCALAR_BYTES:
            return False
    except UnicodeError:
        return False
    return value == value.strip() and value.isprintable()


def _session(value: object) -> str:
    """Strict source-session date; missing, naive and malformed forms refuse."""
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise RetentionUnavailable("invalid source session")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RetentionUnavailable("invalid source session") from exc
    return value


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RetentionUnavailable("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise RetentionUnavailable("nonfinite JSON number")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        _nonfinite(value)
    return result


def payload_session(payload: dict) -> str:
    """The exact source session of a retained payload; it is mandatory."""
    if not isinstance(payload, dict):
        raise RetentionUnavailable("retained payload is not an object")
    return _session(payload.get("asof"))


def _decode(root: str, kind: str, raw: bytes, *, today: date | None = None) -> dict:
    """Bind exact bytes to the typed schema, root and source session."""
    validate_root(root)
    if kind not in _KINDS:
        raise RetentionUnavailable("unknown retained artifact kind")
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _LIMITS[kind]:
        raise RetentionUnavailable("invalid retained bytes or byte limit exceeded")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                             parse_constant=_nonfinite, parse_float=_finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RetentionUnavailable("invalid retained JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != _KINDS[kind] or payload.get("root") != root:
        raise RetentionUnavailable("retained schema or root mismatch")
    session = payload_session(payload)
    if session > (today or _today()).isoformat():
        raise RetentionUnavailable("future source session")
    return payload


@dataclass(frozen=True)
class SnapshotReference:
    """Typed exact-byte reference for one retained options_hub artifact."""

    root: str
    kind: str
    sha256: str
    byte_length: int
    session: str

    @property
    def version_ref(self) -> str:
        return (
            f"sha256:{self.sha256}:bytes:{self.byte_length}"
            f":kind:{self.kind}:session:{self.session}"
        )

    @property
    def key(self) -> str:
        return f"{R2_PREFIX}{self.kind}_history/{self.root}/sha256/{self.sha256}.json"


def parse_reference(root: str, kind: str, version_ref: str, fingerprint: str) -> SnapshotReference:
    """Parse the strict typed reference grammar; every component must agree."""
    validate_root(root)
    if kind not in _KINDS:
        raise RetentionUnavailable("unknown retained artifact kind")
    if not isinstance(version_ref, str) or not version_ref or len(version_ref) > 256:
        raise RetentionUnavailable("invalid version reference")
    match = _REF.fullmatch(version_ref)
    if match is None or not isinstance(fingerprint, str) or not _SHA.fullmatch(fingerprint):
        raise RetentionUnavailable("invalid version reference or fingerprint")
    digest, count, ref_kind, session = match.groups()
    if ref_kind != kind or digest != fingerprint:
        raise RetentionUnavailable("version reference does not match the requested artifact")
    size = int(count)
    if not 0 < size <= min(_LIMITS[kind], 2**53 - 1):
        raise RetentionUnavailable("retained artifact exceeds byte limit")
    return SnapshotReference(root, kind, digest, size, _session(session))


def _checked_ref(ref: SnapshotReference) -> None:
    if not isinstance(ref, SnapshotReference) or type(ref.byte_length) is not int:
        raise RetentionUnavailable("invalid snapshot reference")
    if parse_reference(ref.root, ref.kind, ref.version_ref, ref.sha256) != ref:
        raise RetentionUnavailable("noncanonical snapshot reference")


def validate_reference(ref: SnapshotReference) -> SnapshotReference:
    """Public canonicality check used by consumers before any protected read."""
    _checked_ref(ref)
    return ref


def reference_for_bytes(root: str, kind: str, raw: bytes, *, today: date | None = None) -> SnapshotReference:
    """Bind exact bytes into a typed reference; refuses everything else."""
    payload = _decode(root, kind, raw, today=today)
    return SnapshotReference(root, kind, hashlib.sha256(raw).hexdigest(), len(raw),
                             payload_session(payload))


def verify_snapshot(ref: SnapshotReference, raw: bytes, *, today: date | None = None) -> dict:
    """Verify exact bytes against a typed reference and return the payload."""
    _checked_ref(ref)
    if not isinstance(raw, bytes) or len(raw) != ref.byte_length:
        raise RetentionUnavailable("retained byte length mismatch")
    if hashlib.sha256(raw).hexdigest() != ref.sha256:
        raise RetentionUnavailable("retained digest mismatch")
    payload = _decode(ref.root, ref.kind, raw, today=today)
    if payload_session(payload) != ref.session:
        raise RetentionUnavailable("retained source session mismatch")
    return payload


def qualify_destination(destination, bucket: str, operation: str, refs) -> None:
    """Run the trusted SERVER destination qualification seam; fail closed.

    One small closed request/response binding callback: the request binds the
    ``options_hub`` owner, the exact target bucket, the operation (``read`` or
    ``retain``) and every affected exact artifact reference; a ``qualified``
    response carrying the identical binding lets orchestration continue. A
    missing, non-callable, exceptional, unknown, refusing or mismatched
    response is a typed unavailable/denied refusal before any get or put. No
    bucket string, caller-constructed record or boolean flag alone can
    unblock IO, and there is no runtime factory, environment switch or setter
    that installs a permissive default.

    A successful callback proves orchestration only: the genuine server wiring
    and an actual qualified destination receipt for this owner, bucket and ref
    set still have to exist outside this module. Nothing here is an ACL
    verification and no private-bucket proof is claimed.
    """
    if not callable(destination):
        raise DestinationUnavailable(
            "destination_unavailable: no trusted server destination qualification backend is configured")
    if operation not in _OPERATIONS:
        raise DestinationUnavailable("destination_unavailable: unknown destination operation")
    if not _is_valid_scalar(bucket):
        raise DestinationUnavailable("destination_unavailable: invalid destination bucket")
    checked = []
    for ref in tuple(refs):
        _checked_ref(ref)
        checked.append(ref.version_ref)
    # The callback receives only shallow copies of these containers, and the
    # expected refs are frozen before it runs: a hostile seam can never mutate
    # a shared list into self-approving a different ref set.
    expected_refs = list(checked)
    request = {"owner": OWNER, "bucket": bucket, "operation": operation,
               "refs": list(expected_refs)}
    try:
        response = destination(dict(request))
    except Exception as exc:
        raise DestinationUnavailable(
            "destination_unavailable: destination qualification callback failed") from exc
    if type(response) is not dict or set(response) != {"status", "binding"}:
        raise DestinationUnavailable(
            "destination_unavailable: destination qualification response is malformed")
    status, binding = response["status"], response["binding"]
    if type(status) is not str or type(binding) is not dict or set(binding) != set(_DESTINATION_KEYS):
        raise DestinationUnavailable(
            "destination_unavailable: destination qualification response is malformed")
    for field, want in zip(_DESTINATION_KEYS, (OWNER, bucket, operation, expected_refs)):
        got = binding[field]
        if type(got) is not type(want) or got != want:
            raise DestinationUnavailable(
                "destination_unavailable: destination qualification binding mismatch")
    if status == "qualified":
        return
    if status == "denied":
        raise DestinationDenied(
            "destination_denied: trusted destination qualification refused this target")
    raise DestinationUnavailable(
        "destination_unavailable: destination qualification is not available")


_DESTINATION_KEYS = ("owner", "bucket", "operation", "refs")
_DECISION_BINDING_KEYS = ("owner", "bucket", "operation", "principal", "purpose", "refs")


def _require_retention_decision(decision, bucket: str, action: "RetentionAction", refs) -> None:
    """Require a fresh trusted native retention decision for this exact binding.

    The :class:`RetentionAction` record is caller context only and never
    authorizes retention by itself: without a fresh trusted backend decision
    bound to the exact action, principal, purpose, target bucket and refs, no
    IO and no dependent publication happens. No policy, rights or approval
    receipt is minted here; the genuine native decision backend is wired
    elsewhere.
    """
    if not callable(decision):
        raise RetentionDecisionUnavailable(
            "retention decision unavailable: no fresh trusted native retention decision backend")
    binding = {"owner": OWNER, "bucket": bucket, "operation": "retain",
               "principal": action.authority, "purpose": action.purpose,
               "refs": [ref.version_ref for ref in refs]}
    # Frozen before the callback runs: mutating the handed-down refs list can
    # never rewrite the binding the echo is judged against.
    expected = {**binding, "refs": list(binding["refs"])}
    try:
        response = decision(dict(binding))
    except Exception as exc:
        raise RetentionDecisionUnavailable(
            "retention decision unavailable: decision callback failed") from exc
    if type(response) is not dict or set(response) != {"status", "binding"}:
        raise RetentionDecisionUnavailable(
            "retention decision unavailable: decision response is malformed")
    status, echo = response["status"], response["binding"]
    if type(status) is not str or type(echo) is not dict or set(echo) != set(_DECISION_BINDING_KEYS):
        raise RetentionDecisionUnavailable(
            "retention decision unavailable: decision response is malformed")
    for field, want in expected.items():
        got = echo[field]
        if type(got) is not type(want) or got != want:
            raise RetentionDecisionUnavailable(
                "retention decision unavailable: decision binding mismatch")
    if status == "allowed":
        return
    if status == "denied":
        raise RetentionDenied("retention decision denied: the trusted native decision refused this action")
    raise RetentionDecisionUnavailable("retention decision unavailable: decision is not available")


def _extract(response: object, ref: SnapshotReference) -> bytes:
    """Read one bounded exact object, exposing no fallback and no partial body."""
    if not isinstance(response, dict):
        raise RetentionUnavailable("invalid retained response")
    body = response.get("Body")
    try:
        length = response.get("ContentLength")
        if type(length) is not int or length != ref.byte_length:
            raise RetentionUnavailable("retained ContentLength mismatch")
        raw = bytearray()
        # Read one byte beyond the declared length: a lying ContentLength cannot
        # hide a suffix. Short reads are not treated as EOF.
        while len(raw) <= length:
            chunk = body.read(min(64 * 1024, length + 1 - len(raw)))
            if not isinstance(chunk, bytes):
                raise RetentionUnavailable("invalid retained stream")
            if not chunk:
                break
            if len(chunk) > length + 1 - len(raw):
                raise RetentionUnavailable("retained stream exceeded read bound")
            raw.extend(chunk)
        return bytes(raw)
    except RetentionUnavailable:
        raise
    except Exception as exc:
        raise RetentionUnavailable("retained artifact stream failed") from exc
    finally:
        if body is not None:
            try:
                body.close()
            except Exception:
                pass


def _read_exact(s3, bucket: str, ref: SnapshotReference, *, today: date | None = None) -> bytes:
    """Read and verify only the exact immutable key; no destination logic here.

    Callers must already hold a qualified destination: this private helper is
    reachable only behind :func:`qualify_destination`.
    """
    try:
        response = s3.get_object(Bucket=bucket, Key=ref.key)
    except Exception as exc:
        error = getattr(exc, "response", {})
        detail = error.get("Error") if isinstance(error, dict) else None
        code = detail.get("Code") if isinstance(detail, dict) else None
        if code in {"NoSuchKey", "NotFound", "404"}:
            raise MissingRetainedObject("retained artifact missing") from exc
        raise RetentionUnavailable("retained artifact read failed") from exc
    raw = _extract(response, ref)
    verify_snapshot(ref, raw, today=today)
    return raw


def load_snapshot(s3, bucket: str, ref: SnapshotReference, *, destination=None,
                  today: date | None = None) -> bytes:
    """Read only the exact immutable key, behind a qualified destination."""
    _checked_ref(ref)
    qualify_destination(destination, bucket, "read", (ref,))
    return _read_exact(s3, bucket, ref, today=today)


def load_verified(s3, bucket: str, ref: SnapshotReference, *, destination=None,
                  today: date | None = None) -> tuple[bytes, dict]:
    """Exact verified bytes plus the bound payload, for in-process use only."""
    raw = load_snapshot(s3, bucket, ref, destination=destination, today=today)
    return raw, verify_snapshot(ref, raw, today=today)


def _create_once(s3, bucket: str, ref: SnapshotReference, raw: bytes, *,
                 today: date | None = None) -> None:
    """Conditional create, then reconcile this same key once on uncertainty."""
    try:
        s3.put_object(Bucket=bucket, Key=ref.key, Body=raw,
                      ContentType="application/json", IfNoneMatch="*")
    except Exception:
        # A timeout or conditional-create race may have committed. Reconcile
        # this same key and exact bytes once; never overwrite or choose a new key.
        try:
            reconciled = _read_exact(s3, bucket, ref, today=today)
        except RetentionUnavailable as exc:
            raise RetentionUncertain("retained create effect unresolved") from exc
        if reconciled != raw:
            raise RetentionUnavailable("retained byte collision")
        return


def retain_snapshot(s3, bucket: str, ref: SnapshotReference, raw: bytes, *,
                    destination=None, today: date | None = None) -> None:
    """Create once, then verify bytes; uncertainty never advances a mutable head."""
    verify_snapshot(ref, raw, today=today)
    qualify_destination(destination, bucket, "retain", (ref,))
    try:
        prior = _read_exact(s3, bucket, ref, today=today)
    except MissingRetainedObject:
        pass
    else:
        if prior != raw:
            raise RetentionUnavailable("retained byte collision")
        return
    _create_once(s3, bucket, ref, raw, today=today)


@dataclass(frozen=True)
class RetentionAction:
    """An explicit caller-authorized retention action, built by the caller.

    This record is context only, not a rights decision: it names the authority
    and purpose behind a retention so a fresh trusted native decision backend
    can be asked about exactly this binding. This module performs no rights
    check, mints no entitlement and approves nothing; with the action alone and
    no fresh decision, no IO happens at all.
    """

    authority: str
    purpose: str


@dataclass(frozen=True)
class RetentionOutcome:
    """What the composing utility did; carries references only, never payloads."""

    authority: str
    purpose: str
    retained: tuple[str, ...]
    published: bool


def retain_before_publish(s3, bucket: str, artifacts, publish, *, action=None,
                          retention_decision=None, destination=None,
                          today: date | None = None) -> RetentionOutcome:
    """Retain every exact artifact, then run the dependent publication once.

    Ordered fail-closed gates, all before the first effect: an explicit
    :class:`RetentionAction` is required; every reference and every artifact
    body is validated (so a malformed second artifact can never leave a
    partial first effect); the trusted SERVER destination qualification seam
    must qualify this bucket and all refs; and a fresh trusted native
    retention decision must allow this exact binding. Only then is each
    artifact retained and the publication run once. Any failure leaves the
    dependent publication unexecuted. This helper is not wired into any
    nightly publisher and authorizes nothing by itself.
    """
    if not isinstance(action, RetentionAction):
        raise RetentionUnauthorized("retention requires an explicit caller-authorized action")
    if not _is_valid_scalar(action.authority) or not _is_valid_scalar(action.purpose):
        raise RetentionUnauthorized("retention action record is not a bounded authorization")
    if not callable(publish):
        raise RetentionUnavailable("dependent publication is not callable")
    try:
        entries = tuple(artifacts)
    except TypeError as exc:
        raise RetentionUnavailable("invalid retention artifact set") from exc
    pairs = []
    for entry in entries:
        try:
            ref, raw = entry
        except (TypeError, ValueError) as exc:
            raise RetentionUnavailable("invalid retention artifact entry") from exc
        _checked_ref(ref)
        verify_snapshot(ref, raw, today=today)
        pairs.append((ref, raw))
    if not pairs:
        raise RetentionUnavailable("no retention artifacts supplied")
    refs = [ref for ref, _ in pairs]
    qualify_destination(destination, bucket, "retain", refs)
    _require_retention_decision(retention_decision, bucket, action, refs)
    retained = []
    for ref, raw in pairs:
        retain_snapshot(s3, bucket, ref, raw, destination=destination, today=today)
        retained.append(ref.version_ref)
    publish()
    return RetentionOutcome(authority=action.authority, purpose=action.purpose,
                            retained=tuple(retained), published=True)


_PRIVATE_SCENARIO_KEY = re.compile(r"options_hub/(?:gex|moves)_history/[A-Z0-9][A-Z0-9.-]{0,14}/sha256/[0-9a-f]{64}\.json\Z")


class PrivateScenarioObjects:
    """Constrain the incumbent store to immutable Options keys and create-only IO."""

    def __init__(self, store, capture_enabled):
        self.store, self.capture_enabled = store, capture_enabled

    def _target(self, bucket, key):
        if bucket != self.store.bucket or type(key) is not str or not _PRIVATE_SCENARIO_KEY.fullmatch(key):
            raise ValueError("scenario object target unavailable")

    def get_object(self, *, Bucket, Key):
        self._target(Bucket, Key)
        # Preserve the streaming body, ContentLength and original error codes.
        return self.store._s3.get_object(Bucket=Bucket, Key=Key)

    def put_object(self, *, Bucket, Key, Body, ContentType, IfNoneMatch):
        self._target(Bucket, Key)
        if not self.capture_enabled or IfNoneMatch != "*" or ContentType != "application/json":
            raise ValueError("scenario capture is not enabled")
        if not self.store.put_bytes_strict_conditional(
                Key, Body, expected_version=None, content_type=ContentType):
            # The retention layer reconciles only this original key after a
            # conditional race or uncertain response; never a second PUT.
            raise RuntimeError("scenario conditional create conflict")
