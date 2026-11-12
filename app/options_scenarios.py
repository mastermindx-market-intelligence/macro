"""Private canonical scenario resolve, prospective qualify and deliberate capture.

The exact bearer is freshly verified with existing auth/product readers. Resolve
uses owner RLS UUID/revision or an explicit immutable recipient grant. Qualify
reads exact retained bytes for prospective native TS math before canonical CAS.
Capture additionally composes the fixed-file Options Hub producer with separate
current Save/retention decisions and a qualified private destination; no source
bytes, paths, URLs, policy or destination are accepted from the browser.

Bindings default absent; app.options_scenario_bindings installs the existing
private-store wiring only under explicit server activation flags.
An acquired reference is expected byte identity only. Changed producer bytes
refuse before retention; no latest/public fallback. After any possible capture
effect, failures stay unavailable/UNKNOWN and recovery must qualify/read the
same immutable references, never repeat retention automatically. Canonical CAS
is separate; protected raw bytes are returned only through this current-viewer
private read boundary for exact native TS verification, never generic RPC.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urlsplit
import urllib.request
import math

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app import options_auth as _options_auth
from engine import options_hub_retention as _retention
from engine import options_scenario_capture as _producer
from engine.intelligence_workspace import scenario_source_resolution as _native

__all__ = ["ROUTE", "SourceScenarioBindings", "router", "scenario_bindings"]

ROUTE = "/api/options/scenario-source/resolve"

# The route serves the saved-scenario viewer, so the pinned native action is
# evaluate; there is deliberately no caller action override in the closed wire.
_SOURCE_ACTION = "evaluate"
_RESOURCE_OWNER = _native.RESOURCE_OWNER
_RESOURCE_KIND = "gex"
_MODEL_VERSION = _native.MODEL_VERSION

_CAPTURE_SCHEMA = "investigation_scenario_reference.v1"

_MAX_REVISION = 2147483647
_MAX_BODY_BYTES = 256 * 1024
_MAX_ROW_BYTES = 2 * 1024 * 1024
_MAX_RESPONSE_BYTES = 13 * 1024 * 1024
_RPC_TIMEOUT = 6
_AUTH_BEARER = "Bearer "

_UUID = re.compile(
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)

_RESOLVE_KEYS = frozenset({"mode", "investigation_id", "revision", "grant_id"})
_QUALIFY_KEYS = frozenset(
    {"mode", "investigation_id", "revision", "grant_id", "expected_revision",
     "operation_id", "capture"}
)


# Closed typed vocabulary. ``denied`` is only ever an explicit authority
# denial; everything else that is not success is ``unavailable`` with one of
# these allowlisted codes, and an unknown upstream failure stays inside the
# allowlist instead of leaking detail.
_DENIED_CODES = frozenset({
    "revision_conflict", "resource_denied", "resource_revoked",
    "current_actor_changed", "source_denied", "destination_denied",
})
_UNAVAILABLE_CODES = frozenset({
    "source_binding_unavailable", "binding_invalid", "authentication_unavailable", "product_unavailable",
    "rpc_unavailable", "capture_invalid", "request_invalid",
    "model_version_unsupported", "clock_invalid", "resource_unavailable",
    "source_unavailable", "source_decision_invalid", "destination_unavailable",
    "retained_missing", "retained_unavailable", "response_bound",
})

# Native refusal code -> typed endpoint body. Closed over the native module's
# documented refusal vocabulary.
_NATIVE_MAP = {
    "request_invalid": ("unavailable", "request_invalid"),
    "model_version_unsupported": ("unavailable", "model_version_unsupported"),
    "clock_invalid": ("unavailable", "clock_invalid"),
    "authorization_unavailable": ("unavailable", "source_binding_unavailable"),
    "resource_unavailable": ("unavailable", "resource_unavailable"),
    "resource_denied": ("denied", "resource_denied"),
    "resource_revoked": ("denied", "resource_revoked"),
    "current_actor_changed": ("denied", "current_actor_changed"),
    "source_unavailable": ("unavailable", "source_unavailable"),
    "source_denied": ("denied", "source_denied"),
    "source_decision_invalid": ("unavailable", "source_decision_invalid"),
    "destination_unavailable": ("unavailable", "destination_unavailable"),
    "destination_denied": ("denied", "destination_denied"),
    "retained_missing": ("unavailable", "retained_missing"),
    "retained_unavailable": ("unavailable", "retained_unavailable"),
}


class _Refused(ValueError):
    """Internal typed refusal; never carries upstream detail."""

    def __init__(self, status: str, reason: str | None = None) -> None:
        self.status = status
        self.reason = reason
        super().__init__(reason or status)


def _refuse_unavailable(reason: str) -> _Refused:
    if reason not in _UNAVAILABLE_CODES:
        raise AssertionError("untyped unavailable code")
    return _Refused("unavailable", reason)


def _refuse_denied(reason: str) -> _Refused:
    if reason not in _DENIED_CODES:
        raise AssertionError("untyped denied code")
    return _Refused("denied", reason)


# --------------------------------------------------------------------------
# Trusted app binding: the ONLY way this route reaches an S3 client, bucket,
# destination seam or native use callback. No setter exists in this module.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceScenarioBindings:
    """Genuine server wiring for one mounted Macro application.

    Every field is supplied by the parent application itself, directly on its
    own ``app.state``; this module exposes no setter, no host configuration
    fallback and no factory. The default instance is fully unbound and can authorize
    nothing. ``s3`` is the retained-object client, ``bucket`` the retention
    bucket, ``destination`` the trusted SERVER destination qualification seam,
    ``resource_access`` and ``source_use_decision`` the native authorization
    callbacks, and ``clock``/``current_viewer`` optional seams (native
    defaults apply when ``None``). Instances configured by tests are
    explicitly controlled doubles and prove orchestration, never authority.
    """

    s3: Any = None
    bucket: str | None = None
    destination: Any = None
    resource_access: Any = None
    source_use_decision: Any = None
    clock: Callable[[], datetime] | None = None
    current_viewer: Callable[[], Any] | None = None
    # Deliberate CAPTURE only. Neither product/evaluate rights nor a read binding
    # can supply Save/retention authority or a local producer directory.
    producer_out_dir: Any = None
    source_save_decision: Any = None
    retention_decision: Any = None


def _usable_bucket(bucket: Any) -> bool:
    if type(bucket) is not str or not 0 < len(bucket) <= 253:
        return False
    return bucket == bucket.strip() and bucket.isprintable()


def _bindings_usable(bindings: Any) -> bool:
    from app.options_scenario_bindings import ScenarioSourceRuntime
    if isinstance(bindings, ScenarioSourceRuntime):
        return True
    if not isinstance(bindings, SourceScenarioBindings):
        return False
    return (
        bindings.s3 is not None
        and _usable_bucket(bindings.bucket)
        and callable(bindings.destination)
        and callable(bindings.resource_access)
        and callable(bindings.source_use_decision)
    )


def bindings_from_app_state(request: Request):
    """Read the trusted binding the parent application put on its own state.

    Returns ``None`` unless the application itself configured a
    :class:`SourceScenarioBindings` instance. This is a read-only lookup: the
    route can never install, replace or synthesize a backend.
    """
    state = getattr(request.app.state, "options_scenario_source_bindings", None)
    from app.options_scenario_bindings import ScenarioSourceRuntime
    if not isinstance(state, (SourceScenarioBindings, ScenarioSourceRuntime)):
        return None
    return state


def scenario_bindings(request: Request):
    """FastAPI dependency: the trusted binding, or ``None`` (typed refusal)."""
    return bindings_from_app_state(request)


router = APIRouter()


# --------------------------------------------------------------------------
# Private strict capture validation: the closed reference-only wire contract.
# Deliberately bounded and self-contained (this adapter does not own the
# generic manifest module); it accepts exactly the shared capture schema and
# rebuilds a fresh canonical object. It proves shape only — never retention,
# rights or availability.
# --------------------------------------------------------------------------


_CAPTURE_KEYS = ("schema", "model_version", "inputs", "source")
_SOURCE_KEYS = ("owner", "root", "session", "source_as_of", "evaluated_at",
                "lens", "selection_key", "basis_sha256", "gex", "moves")
_INPUT_KEYS = ("targetSpot", "deltaSigmaPts", "days")
_DIGEST_KEYS = ("sha256", "byte_length")
_LENS_KINDS = ("all", "zero", "next-live", "week")

_CLOCK_MAX = 40
_SELECTION_PAIRS_MAX = 128
_SELECTION_KEY_MAX = 16 * 1024
_GEX_BYTES_MAX = _retention.MAX_GEX_BYTES
_MOVES_BYTES_MAX = _retention.MAX_MOVES_BYTES

_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DATETIME_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?"
    r"(?:[Zz]|([+-])(\d{2}):(\d{2}))"
)
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_NATIVE_ROOT_RE = re.compile(r"[A-Z0-9]{1,10}(?:[.-][A-Z0-9]{1,4})?")


def _plain_dict(raw: Any) -> bool:
    return type(raw) is dict


def _single_line(value: str) -> bool:
    # Control characters, DEL and the JSON-hostile Unicode line
    # separators (U+2028/U+2029) can never appear in a stored canonical
    # selection key.
    return not any(
        ord(ch) < 0x20 or ord(ch) == 0x7F or ch in (" ", " ") for ch in value
    )


def _days_in_month(year: int, month: int) -> int | None:
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    if month == 2:
        leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
        return 29 if leap else 28
    return None


def _calendar_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    match = _DATE_RE.fullmatch(value)
    if match is None:
        return False
    dim = _days_in_month(int(match.group(1)), int(match.group(2)))
    return dim is not None and 1 <= int(match.group(3)) <= dim


def _zone_instant(value: Any) -> bool:
    """Zone-bearing ISO instant, lowercase t/z allowed, 1-9 fraction digits.

    Validated and retained verbatim — never parsed into a datetime here and
    never normalized; ordering between declared instants uses only the offsets
    the strings carry.
    """
    if not isinstance(value, str):
        return False
    match = _DATETIME_RE.fullmatch(value)
    if match is None:
        return False
    if not _calendar_date(f"{match.group(1)}-{match.group(2)}-{match.group(3)}"):
        return False
    if int(match.group(4)) > 23 or int(match.group(5)) > 59 or int(match.group(6)) > 59:
        return False
    if match.group(9) is not None and (int(match.group(9)) > 23 or int(match.group(10)) > 59):
        return False
    return True


def _valid_source_clock(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not 1 <= len(value) <= _CLOCK_MAX:
        return False
    return _calendar_date(value) or _zone_instant(value)


def _instant_parts(value: str) -> tuple[int, str] | None:
    """(UTC seconds, zero-padded fraction) using only the declared offset."""
    match = _DATETIME_RE.fullmatch(value)
    if match is None:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    yy = year - 1 if month <= 2 else year
    era = yy // 400
    yoe = yy - era * 400
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    secs = days * 86400 + int(match.group(4)) * 3600 + int(match.group(5)) * 60 \
        + int(match.group(6))
    if match.group(8) is None:
        offset = 0
    else:
        offset = int(match.group(9)) * 3600 + int(match.group(10)) * 60
        offset = -offset if match.group(8) == "-" else offset
    return secs - offset, (match.group(7) or "").ljust(9, "0")


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _validate_inputs(raw: Any) -> dict | None:
    if not _plain_dict(raw) or set(raw.keys()) != set(_INPUT_KEYS):
        return None
    target = _finite_number(raw["targetSpot"])
    delta = _finite_number(raw["deltaSigmaPts"])
    days = _finite_number(raw["days"])
    if target is None or delta is None or days is None:
        return None
    if target <= 0 or not -5.0 <= delta <= 5.0 or not 0.0 <= days <= 5.0:
        return None
    return {"targetSpot": target, "deltaSigmaPts": delta, "days": days}


def _parse_digest(raw: Any, max_bytes: int) -> dict | None:
    if not _plain_dict(raw) or set(raw.keys()) != set(_DIGEST_KEYS):
        return None
    sha = raw["sha256"]
    if not isinstance(sha, str) or _HEX64_RE.fullmatch(sha) is None:
        return None
    # JSON has one numeric type across JS/SQL: normalize finite integral
    # numbers to the native integer reference; booleans still refuse.
    length = raw["byte_length"]
    if type(length) not in (int, float) or not math.isfinite(length) or not float(length).is_integer() or not 1 <= length <= max_bytes:
        return None
    return {"sha256": sha, "byte_length": int(length)}


def _parse_selection_key(raw: Any, session: str) -> list[str] | None:
    """Canonical ``expiry|economic_expiry_at`` pairs, unique and strictly
    sorted as full strings, each expiry a real date at/after the session and
    each economic expiry a zone-bearing instant. Never re-evaluated on any
    current clock."""
    if not isinstance(raw, str):
        return None
    if not 1 <= len(raw) <= _SELECTION_KEY_MAX or not _single_line(raw):
        return None
    try:
        if len(raw.encode("utf-8")) > _SELECTION_KEY_MAX:
            return None
    except UnicodeError:
        return None
    parts = raw.split(",")
    if len(parts) > _SELECTION_PAIRS_MAX:
        return None
    previous: str | None = None
    for part in parts:
        sep = part.find("|")
        if sep < 0:
            return None
        expiry, economic = part[:sep], part[sep + 1:]
        if not _calendar_date(expiry) or not _zone_instant(economic):
            return None
        if expiry < session:
            return None
        if previous is not None and not previous < part:
            return None
        previous = part
    return parts


def _parse_lens(raw: Any, session: str, expiries: frozenset[str]) -> dict | None:
    """Exactly all/zero/next-live/week (kind only) or one + its exact exp.

    The one/zero kinds constrain the captured expiry SET exactly as the frozen
    capture contract stores it; several economic instants for one expiry stay
    valid.
    """
    if not _plain_dict(raw):
        return None
    kind = raw.get("kind")
    if not isinstance(kind, str):
        return None
    if kind == "one":
        if len(raw) != 2 or "exp" not in raw:
            return None
        exp = raw["exp"]
        if not isinstance(exp, str) or not _calendar_date(exp):
            return None
        if expiries != frozenset((exp,)):
            return None
        return {"kind": "one", "exp": exp}
    if kind in _LENS_KINDS:
        if len(raw) != 1:
            return None
        if kind == "zero" and expiries != frozenset((session,)):
            return None
        return {"kind": kind}
    return None


def _native_root(root: Any) -> bool:
    if not isinstance(root, str) or not 0 < len(root) <= 12:
        return False
    return _NATIVE_ROOT_RE.fullmatch(root) is not None


def _parse_source(raw: Any) -> dict | None:
    if not _plain_dict(raw) or set(raw.keys()) != set(_SOURCE_KEYS):
        return None
    if raw["owner"] != _RESOURCE_OWNER:
        return None
    root = raw["root"]
    if not _native_root(root):
        return None
    session = raw["session"]
    if not isinstance(session, str) or not _calendar_date(session):
        return None
    source_as_of = raw["source_as_of"]
    if not _valid_source_clock(source_as_of):
        return None
    evaluated_at = raw["evaluated_at"]
    if not isinstance(evaluated_at, str) or not 1 <= len(evaluated_at) <= _CLOCK_MAX \
            or not _zone_instant(evaluated_at):
        return None
    # Clock ordering: a bare date compares by calendar date; two instants
    # compare exactly via the offsets they carry. Nothing is normalized.
    if evaluated_at[:10] < session:
        return None
    if isinstance(source_as_of, str):
        if _zone_instant(source_as_of):
            src = _instant_parts(source_as_of)
            ev = _instant_parts(evaluated_at)
            if src is None or ev is None or src > ev:
                return None
        elif source_as_of > evaluated_at[:10]:
            return None
    selection_key = _parse_selection_key(raw["selection_key"], session)
    if selection_key is None:
        return None
    basis_sha256 = raw["basis_sha256"]
    if not isinstance(basis_sha256, str) or _HEX64_RE.fullmatch(basis_sha256) is None:
        return None
    gex = _parse_digest(raw["gex"], _GEX_BYTES_MAX)
    if gex is None:
        return None
    if raw["moves"] is None:
        moves: dict | None = None
    else:
        moves = _parse_digest(raw["moves"], _MOVES_BYTES_MAX)
        if moves is None:
            return None
    expiries = frozenset(part[:part.find("|")] for part in selection_key)
    lens = _parse_lens(raw["lens"], session, expiries)
    if lens is None:
        return None
    return {
        "owner": _RESOURCE_OWNER,
        "root": root,
        "session": session,
        "source_as_of": source_as_of,
        "evaluated_at": evaluated_at,
        "lens": lens,
        "selection_key": raw["selection_key"],
        "basis_sha256": basis_sha256,
        "gex": gex,
        "moves": moves,
    }


def _parse_capture(raw: Any) -> dict | None:
    """Parse a stored reference-only scenario capture, or ``None``.

    Pure shape read: exact key sets at both levels, the frozen schema and
    native model version, strict input bounds and the full source reference
    rules. Anything extra — including any old full-value basis or result, any
    Matrix or OptionUseRequest shape, any inferred reference — is refused,
    never dropped or converted. This parser proves no rights.
    """
    if not _plain_dict(raw) or set(raw.keys()) != set(_CAPTURE_KEYS):
        return None
    if raw["schema"] != _CAPTURE_SCHEMA or raw["model_version"] != _MODEL_VERSION:
        return None
    inputs = _validate_inputs(raw["inputs"])
    if inputs is None:
        return None
    source = _parse_source(raw["source"])
    if source is None:
        return None
    return {
        "schema": _CAPTURE_SCHEMA,
        "model_version": _MODEL_VERSION,
        "inputs": inputs,
        "source": source,
    }


# --------------------------------------------------------------------------
# Exact caller-token Supabase RPC: fixed configured origin + public anon key.
# No service role, no caller-supplied URL, no redirect ever followed.
# --------------------------------------------------------------------------


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect: an auth header is never replayed elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _open_rpc(request: urllib.request.Request, timeout: int):
    """Transport seam (one no-redirect opener); tests may substitute only."""
    return _OPENER.open(request, timeout=timeout)


def _rest_origin() -> str:
    from app.main import SUPABASE_URL

    if type(SUPABASE_URL) is not str:
        raise ValueError("origin unavailable")
    root = SUPABASE_URL.rstrip("/")
    parsed = urlsplit(root)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path
            or any(c.isspace() for c in root) or not root.isprintable()
            or len(root) > 240):
        raise ValueError("origin unavailable")
    return root


def _anon_key() -> str:
    from app.main import SUPABASE_ANON_KEY

    if type(SUPABASE_ANON_KEY) is not str or not 1 <= len(SUPABASE_ANON_KEY) <= 4096:
        raise ValueError("anon key unavailable")
    return SUPABASE_ANON_KEY


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _nonfinite(_value):
    raise ValueError("nonfinite JSON number")


def _caller_rpc(function: str, payload: dict, access_token: str) -> Any:
    """One exact caller-token PostgREST RPC read; RLS sees only this caller.

    Returns the decoded JSON (row object, or list for set-returning
    functions). Any transport, status, redirect, oversize or parse failure is
    a typed ``rpc_unavailable`` refusal; no upstream detail ever escapes.
    """
    origin = _rest_origin()
    anon = _anon_key()
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    request = urllib.request.Request(
        f"{origin}/rest/v1/rpc/{function}",
        data=body,
        method="POST",
        headers={
            "Authorization": _AUTH_BEARER + access_token,
            "apikey": anon,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        response = _open_rpc(request, _RPC_TIMEOUT)
    except _Refused:
        raise
    except Exception:
        raise _refuse_unavailable("rpc_unavailable") from None
    try:
        with response:
            if getattr(response, "status", 200) != 200:
                raise _refuse_unavailable("rpc_unavailable")
            raw = response.read(_MAX_ROW_BYTES + 1)
            if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_ROW_BYTES:
                raise _refuse_unavailable("rpc_unavailable")
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=_nonfinite)
    except _Refused:
        raise
    except Exception:
        raise _refuse_unavailable("rpc_unavailable") from None
    return parsed


def _single_row(parsed: Any) -> dict | None:
    """Exactly the one canonical row, or ``None`` (honestly absent).

    A scalar RPC returning JSON ``null``, or a set-returning RPC returning an
    empty array, is the honest absent answer; anything ambiguous refuses.
    """
    if parsed is None:
        return None
    if type(parsed) is dict:
        return parsed
    if type(parsed) is list:
        if not parsed:
            return None
        if len(parsed) == 1 and type(parsed[0]) is dict:
            return parsed[0]
    raise _refuse_unavailable("rpc_unavailable")


def _canonical_row(row: dict | None, investigation_id: str, revision: int,
                   grant_id: str | None) -> dict | None:
    """Unwrap the actual caller-token canonical RPC contract only.

    Owner rows carry manifest/lifecycle; recipient rows carry the deliberately
    projected handoff, with no manifest access. A flattened or ambiguous shape
    cannot stand in for either canonical read.
    """
    if row is None:
        return None
    if type(row) is not dict:
        raise _refuse_unavailable("rpc_unavailable")
    if row.get("revoked_at") is not None:
        return None
    status = row.get("status")
    if status == "not_found":
        return None
    if status in ("unavailable", "unauthenticated"):
        raise _refuse_unavailable("rpc_unavailable")
    if status != "found":
        return None
    if grant_id is None:
        if (row.get("id") != investigation_id or type(row.get("revision")) is not int
                or row["revision"] != revision or row.get("lifecycle") != "active"
                or row.get("grant_id") is not None):
            return None
        manifest = row.get("manifest")
        if type(manifest) is not dict or manifest.get("schema") != "investigation_manifest.v2":
            raise _refuse_unavailable("rpc_unavailable")
        return {"capture": manifest.get("scenario_capture"),
                "current_revision": row.get("current_revision")}
    handoff = row.get("handoff")
    if type(handoff) is dict and handoff.get("revoked_at") is not None:
        return None
    if (type(handoff) is not dict or handoff.get("schema") != "mm.research_handoff.v1"
            or handoff.get("investigation_id") != investigation_id
            or type(handoff.get("revision")) is not int or handoff["revision"] != revision
            or handoff.get("grant_id") != grant_id):
        return None
    return {"capture": handoff.get("scenario_capture")}


def _row_capture(row: dict | None, investigation_id: str, revision: int,
                 grant_id: str | None) -> dict | None:
    row = _canonical_row(row, investigation_id, revision, grant_id)
    if row is None or row["capture"] is None:
        return None
    capture = _parse_capture(row["capture"])
    if capture is None:
        raise _refuse_unavailable("capture_invalid")
    return capture


# --------------------------------------------------------------------------
# Existing auth/product composition: fresh observations only, no cache.
# --------------------------------------------------------------------------


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if type(header) is not str or not header.startswith(_AUTH_BEARER):
        return None
    token = header[len(_AUTH_BEARER):]
    if not token or any(c.isspace() for c in token):
        return None
    return token


def _verified_principal(access_token: str):
    try:
        return _options_auth.resolve_options_principal(access_token)
    except Exception:
        raise _refuse_unavailable("authentication_unavailable") from None


def _product_allowed(principal, access_token: str) -> bool:
    """The exact existing product predicate: feature, unlimited tier, or the
    verified operator overlay — one uncached billing read, no grace, no UI
    profile, no entitlement cache."""
    try:
        observed, email = _options_auth._authenticate(access_token)
        if (observed.principal_id != principal.principal_id
                or observed.principal_issuer != principal.principal_issuer
                or observed.auth_epoch != principal.auth_epoch):
            raise _refuse_unavailable("product_unavailable")
        from app import billing, paywall

        entitlement = billing.read_entitlement(principal.principal_id)
        if type(entitlement) is not dict:
            raise _refuse_unavailable("product_unavailable")
        features = entitlement.get("features")
        tier = entitlement.get("tier")
        allowed = (
            (type(features) is list and "terminal_live_options" in features)
            or (type(tier) is str and tier.strip().lower() == "unlimited")
            or (type(email) is str and bool(email)
                and paywall._operator_unlimited(email) is True)
        )
        if not allowed or time.time() >= principal.expires_at:
            # read_entitlement's free default also represents unavailable table/key/network.
            # Its false predicate is not evidence of an explicit permission refusal.
            raise _refuse_unavailable("product_unavailable")
        return True
    except _Refused:
        raise
    except Exception:
        raise _refuse_unavailable("product_unavailable") from None


def _current_viewer_seam(access_token: str):
    """Native current-viewer seam: one fresh uncached auth observation."""
    def seam():
        fresh = _options_auth.resolve_options_principal(access_token)
        return _native.ViewerIdentity(fresh.principal_id, fresh.principal_issuer,
                                      fresh.auth_epoch)
    return seam


def _viewer_tuple(principal) -> tuple[str, str, str]:
    return (principal.principal_id, principal.principal_issuer, principal.auth_epoch)


# --------------------------------------------------------------------------
# Request wire (closed union) and mode logic.
# --------------------------------------------------------------------------


def _strict_json(raw: bytes) -> dict:
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=_nonfinite)
    except Exception:
        raise _refuse_unavailable("request_invalid") from None
    if type(parsed) is not dict:
        raise _refuse_unavailable("request_invalid")
    return parsed


def _uuid_field(value: Any) -> str:
    if type(value) is not str or _UUID.match(value) is None:
        raise _refuse_unavailable("request_invalid")
    return value


def _revision_field(value: Any, minimum: int) -> int:
    if type(value) is not int or not minimum <= value <= _MAX_REVISION:
        raise _refuse_unavailable("request_invalid")
    return value


def _parse_body(raw: bytes) -> tuple[str, str, int, str | None, int | None, str | None,
                                     dict | None]:
    """Closed request union; returns (mode, id, revision, grant_id,
    expected_revision, operation_id, capture). Qualify validates the
    UNTRUSTED browser capture shape here, before any authority is contacted."""
    if len(raw) > _MAX_BODY_BYTES:
        raise _refuse_unavailable("request_invalid")
    body = _strict_json(raw)
    mode = body.get("mode")
    if mode not in ("resolve", "qualify", "capture") or type(mode) is not str:
        raise _refuse_unavailable("request_invalid")
    investigation_id = _uuid_field(body.get("investigation_id"))
    revision = _revision_field(body.get("revision"), 1)
    grant = body.get("grant_id")
    if grant is not None:
        grant = _uuid_field(grant)
    if mode == "resolve":
        if set(body.keys()) != set(_RESOLVE_KEYS):
            raise _refuse_unavailable("request_invalid")
        return mode, investigation_id, revision, grant, None, None, None
    if set(body.keys()) != set(_QUALIFY_KEYS):
        raise _refuse_unavailable("request_invalid")
    # Deliberate pre-apply owner intent carries no grant authority at all.
    if grant is not None:
        raise _refuse_unavailable("request_invalid")
    expected = body.get("expected_revision")
    if type(expected) is not int or not 0 <= expected <= _MAX_REVISION - 1:
        raise _refuse_unavailable("request_invalid")
    if revision != expected + 1:
        raise _refuse_unavailable("request_invalid")
    # Canonical operation identity binds the deliberate intent. It is not an
    # authority or a new operation ledger; only capture may retain sources,
    # under separate current Save/retention and private-destination decisions.
    operation_id = _uuid_field(body.get("operation_id"))
    capture = _parse_capture(body.get("capture"))
    if capture is None:
        raise _refuse_unavailable("capture_invalid")
    return mode, investigation_id, revision, None, expected, operation_id, capture


def _read_canonical_row(investigation_id: str, revision: int,
                        grant_id: str | None, access_token: str) -> dict | None:
    """Exact caller-token RLS read of the canonical row (never request
    metadata). Owner context reads the exact owner revision; an explicit
    recipient grant reads the handoff view with the same token."""
    if grant_id is None:
        parsed = _caller_rpc("read_investigation_v2",
                             {"p_id": investigation_id, "p_revision": revision},
                             access_token)
    else:
        parsed = _caller_rpc("read_investigation_handoff_v1",
                             {"p_grant_id": grant_id}, access_token)
    return _row_capture(_single_row(parsed), investigation_id, revision, grant_id)


def _descriptor(capture: dict, investigation_id: str, revision: int,
                grant_id: str | None) -> _native.ScenarioSourceDescriptor:
    """Native typed descriptor built ONLY from the stored strict metadata.

    Digests and lengths are reference bindings, not rights; the native
    resolver revalidates every field before any callback or IO.
    """
    source = capture["source"]
    gex = _retention.SnapshotReference(source["root"], _RESOURCE_KIND,
                                       source["gex"]["sha256"],
                                       source["gex"]["byte_length"], source["session"])
    moves = None
    if source["moves"] is not None:
        moves = _retention.SnapshotReference(source["root"], "moves",
                                             source["moves"]["sha256"],
                                             source["moves"]["byte_length"],
                                             source["session"])
    return _native.ScenarioSourceDescriptor(
        root=source["root"], gex=gex, moves=moves,
        investigation_id=investigation_id, investigation_revision=revision,
        grant_id=grant_id, model_version=_MODEL_VERSION,
        lens=dict(source["lens"]),
        selection_key=source["selection_key"], source_as_of=source["source_as_of"],
        basis_sha256=source["basis_sha256"], evaluated_at=source["evaluated_at"],
        action=_SOURCE_ACTION)


def _qualified_response(payload: dict) -> Response:
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(body) > _MAX_RESPONSE_BYTES:
        raise _refuse_unavailable("response_bound")
    return Response(content=body, media_type="application/json", headers={
        "Cache-Control": "private, no-store",
        "Vary": "Authorization",
    })


def _typed_response(refusal: _Refused) -> Response:
    if refusal.status == "not_found":
        payload = {"status": "not_found"}
    elif refusal.status == "unavailable":
        payload = {"status": "unavailable", "reason": refusal.reason}
    else:
        payload = {"status": "denied", "reason": refusal.reason}
    return _qualified_response(payload)


def _verified_bytes(resolved, ref, raw: bytes) -> dict:
    """Exact verified bytes as the strict wire digest — recomputed here so a
    mismatch can never be emitted, and base64 is strict standard alphabet."""
    if type(raw) is not bytes or len(raw) != ref.byte_length \
            or hashlib.sha256(raw).hexdigest() != ref.sha256:
        raise _refuse_unavailable("retained_unavailable")
    return {"sha256": ref.sha256, "byte_length": len(raw),
            "base64": base64.b64encode(raw).decode("ascii")}


def _recheck_context(access_token: str, principal, investigation_id: str,
                     revision: int, grant_id: str | None, capture: dict | None) -> None:
    """Current actor/product/resource recheck around the read: a session,
    entitlement or canonical-row change refuses instead of emitting."""
    try:
        fresh = _options_auth.resolve_options_principal(access_token)
    except Exception:
        raise _refuse_unavailable("authentication_unavailable") from None
    if _viewer_tuple(fresh) != _viewer_tuple(principal):
        raise _refuse_denied("current_actor_changed")
    _product_allowed(principal, access_token)
    if capture is None:
        return
    # Re-read the canonical row through the same exact qualification and
    # require the same source binding; any change is a resource change,
    # not a hint to the viewer.
    try:
        fresh_capture = _read_canonical_row(investigation_id, revision, grant_id,
                                            access_token)
    except _Refused as exc:
        if exc.reason == "rpc_unavailable":
            raise
        raise _refuse_denied("resource_revoked") from None
    if fresh_capture is None:
        raise _refuse_denied("resource_revoked")
    if capture != fresh_capture:
        raise _refuse_denied("resource_revoked")


# --------------------------------------------------------------------------
# The one mounted route.
# --------------------------------------------------------------------------


@router.post(ROUTE)
async def resolve_scenario_source_route(
    request: Request,
    bindings=Depends(scenario_bindings),
) -> Response:
    """Resolve, qualify or initially capture exact protected source; fail closed."""
    try:
        # Zero-IO gate: no trusted binding means no auth call, no RPC, no S3.
        if not _bindings_usable(bindings):
            raise _refuse_unavailable("source_binding_unavailable")
        raw = await request.body()
        if type(raw) is not bytes:
            raise _refuse_unavailable("request_invalid")
        (mode, investigation_id, revision, grant_id, expected_revision,
         operation_id, capture) = _parse_body(raw)
        from app.options_scenario_bindings import ScenarioSourceRuntime
        runtime = isinstance(bindings, ScenarioSourceRuntime)
        if mode == "capture" and (bindings.producer_out_dir is None
                or (runtime and not bindings.capture_enabled)
                or (not runtime and (not callable(bindings.source_save_decision)
                                     or not callable(bindings.retention_decision)))):
            raise _refuse_unavailable("source_binding_unavailable")
        access_token = _bearer_token(request)
        if access_token is None:
            raise _refuse_unavailable("authentication_unavailable")
        principal = _verified_principal(access_token)
        _product_allowed(principal, access_token)

        if mode == "resolve":
            return _resolve_mode(bindings, access_token, principal, investigation_id,
                                 revision, grant_id)
        if mode == "capture":
            return _capture_mode(bindings, access_token, principal, investigation_id,
                                 revision, expected_revision, operation_id, capture)
        return _qualify_mode(bindings, access_token, principal, investigation_id,
                             revision, expected_revision, operation_id, capture)
    except _Refused as refusal:
        return _typed_response(refusal)
    except Exception:
        # Never an exception detail, a token, a paid value or a stack trace.
        return _typed_response(_refuse_unavailable("request_invalid"))


def _resolve_mode(bindings, access_token: str, principal, investigation_id: str,
                  revision: int, grant_id: str | None) -> Response:
    capture = _read_canonical_row(investigation_id, revision, grant_id,
                                  access_token)
    if capture is None:
        return _typed_response(_Refused("not_found"))
    return _resolve_capture(bindings, access_token, principal, investigation_id,
                            revision, grant_id, capture, "resolve")


def _resolve_capture(bindings, access_token, principal, investigation_id, revision,
                     grant_id, capture, mode, expected_revision=None):
    from app.options_scenario_bindings import ScenarioSourceRuntime
    if isinstance(bindings, ScenarioSourceRuntime):
        bindings = bindings.for_request(token=access_token, principal=principal,
            investigation_id=investigation_id, revision=revision, grant_id=grant_id,
            capture=capture, mode=mode, expected_revision=expected_revision)
    descriptor = _descriptor(capture, investigation_id, revision, grant_id)
    viewer = _native.ViewerIdentity(principal.principal_id,
                                    principal.principal_issuer, principal.auth_epoch)
    try:
        resolved = _native.resolve_scenario_source(
            descriptor, viewer,
            s3=bindings.s3,
            bucket=bindings.bucket,
            destination=bindings.destination,
            resource_access=bindings.resource_access,
            source_use_decision=bindings.source_use_decision,
            clock=bindings.clock,
            current_viewer=(_current_viewer_seam(access_token)
                            if bindings.current_viewer is None
                            else bindings.current_viewer),
        )
    except _native.ScenarioSourceRefused as exc:
        mapped = _NATIVE_MAP.get(exc.code)
        if mapped is None:
            raise _refuse_unavailable("request_invalid") from None
        status, reason = mapped
        if status == "denied":
            raise _refuse_denied(reason) from None
        raise _refuse_unavailable(reason) from None
    _recheck_context(access_token, principal, investigation_id, revision,
                     grant_id, capture if mode == "resolve" else None)
    if mode in ("qualify", "capture"):
        _check_prospective(access_token, investigation_id, expected_revision)
    gex = _verified_bytes(resolved, descriptor.gex, resolved.gex_bytes)
    moves = None
    if descriptor.moves is not None:
        if resolved.moves_bytes is None:
            raise _refuse_unavailable("retained_unavailable")
        moves = _verified_bytes(resolved, descriptor.moves, resolved.moves_bytes)
    payload = {
        "status": "resolved",
        "mode": mode,
        "investigation_id": investigation_id,
        "revision": revision,
        "grant_id": grant_id,
        "capture": capture,
        "gex": gex,
        "moves": moves,
    }
    return _qualified_response(payload)


def _check_prospective(access_token: str, investigation_id: str,
                       expected_revision: int) -> None:
    """Read-only owner intent, never a grant or canonical write authority.

    Create's RLS not-found can hide a foreign UUID; only actual CAS/RLS apply
    resolves that conflict. Revise requires the exact current owner head.
    """
    if expected_revision:
        parsed = _caller_rpc("read_investigation_v2",
                             {"p_id": investigation_id, "p_revision": expected_revision},
                             access_token)
        row = _canonical_row(_single_row(parsed), investigation_id, expected_revision, None)
        if row is None:
            raise _Refused("not_found")
        current = row.get("current_revision")
        if type(current) is not int or current != expected_revision:
            raise _refuse_denied("revision_conflict")
    nxt = _caller_rpc("read_investigation_v2",
                      {"p_id": investigation_id, "p_revision": expected_revision + 1},
                      access_token)
    if _canonical_row(_single_row(nxt), investigation_id, expected_revision + 1, None) is not None:
        raise _refuse_denied("revision_conflict")


def _qualify_mode(bindings, access_token: str, principal, investigation_id: str,
                  revision: int, expected_revision: int, operation_id: str,
                  capture: dict) -> Response:
    """Resolve exact protected bytes for prospective native-math verification.

    No writes/retention/grants occur. Current native source/action, genuine
    resource-access and private-destination callbacks still authorize the read;
    prospective canonical intent never creates source rights or write authority.
    """
    _check_prospective(access_token, investigation_id, expected_revision)
    return _resolve_capture(bindings, access_token, principal, investigation_id,
                            revision, None, capture, "qualify", expected_revision)


def _capture_mode(bindings, access_token, principal, investigation_id, revision,
                  expected_revision, operation_id, capture):
    """Initial deliberate capture, never an automatic/recovery replay.

    Fixed native producer files must STILL match acquired hashes/lengths. Both
    artifacts validate before the first retention write. Save, retention and
    evaluate are distinct current actions; canonical CAS remains separate.
    All failure after invoking retention is conservatively UNKNOWN: the caller
    retains the original operation and may only reconcile by read/qualify.
    """
    _check_prospective(access_token, investigation_id, expected_revision)
    from app.options_scenario_bindings import ScenarioSourceRuntime
    runtime = bindings
    if isinstance(bindings, ScenarioSourceRuntime):
        bindings = bindings.for_request(token=access_token, principal=principal,
            investigation_id=investigation_id, revision=revision, grant_id=None,
            capture=capture, mode="capture", expected_revision=expected_revision,
            operation_id=operation_id)
    descriptor = _descriptor(capture, investigation_id, revision, None)
    viewer = _native.ViewerIdentity(principal.principal_id,
                                    principal.principal_issuer, principal.auth_epoch)
    try:
        _producer.capture_built_scenario_sources(descriptor, viewer, operation_id=operation_id,
            out_dir=bindings.producer_out_dir, s3=bindings.s3, bucket=bindings.bucket,
            destination=bindings.destination, source_save_decision=bindings.source_save_decision,
            retention_decision=bindings.retention_decision,
            current_viewer=(_current_viewer_seam(access_token) if bindings.current_viewer is None
                            else bindings.current_viewer), clock=bindings.clock)
        _recheck_context(access_token, principal, investigation_id, revision, None, None)
        # Exact retained bytes + current evaluate/read authority + native TS math
        # still qualify before canonical CAS; metadata emission is not acceptance.
        return _resolve_capture(runtime, access_token, principal, investigation_id,
                                revision, None, capture, "capture", expected_revision)
    except Exception:
        # A failed/partial/lost retention response never means "nothing changed".
        # No provider errors, source paths or paid bytes escape this boundary.
        return _typed_response(_refuse_unavailable("source_unavailable"))
