"""Read-only HTTP authorization envelope for the coherent Sector view.

Authority boundary
------------------
This module owns NO access decision of its own. It is a transport envelope over
the two incumbent site gates, in the same order Caddy uses them:

    1. ``app.regwall.regwall_check`` — a registered Supabase session;
    2. ``app.paywall.paywall_check``  — the ``site_full`` entitlement.

Both gates are reused AS THEY ARE. This module does not re-implement path
classification, does not read ``config/site_access.yml``, does not mint an
identity cache, and does not introduce a second auth/policy/proxy owner. A
``/sectordata`` or ``/basketdata`` path is unknown to the policy, so it keeps
reading ``premium`` by the incumbent default; nothing here relabels a path
``preview`` in order to make it free.

Why the gates need a controlled request view
---------------------------------------------
The gates are Caddy subrequests. Caddy hands them two server-owned facts that
the origin does not otherwise know: ``X-Original-Uri`` (the file being served)
and ``X-Original-Kind`` (``asset`` for a JSON/data artifact). A request that
reaches this route carries NEITHER, and whatever the caller put in those
headers is not a fact about a server-owned resource.

So each gate is evaluated against a controlled view of the caller's request:

* ``x-original-uri`` is OVERWRITTEN with the server-owned resource path whose
  access is being asserted;
* ``x-original-kind`` is OVERWRITTEN with ``asset``;
* every caller document-classification header (``sec-fetch-*``) is DROPPED, so
  a caller cannot turn an asset denial into a document redirect;
* the caller's Supabase session cookie is PRESERVED — it is the only carrier of
  identity the incumbent gates read (``_mm_supabase_access_token``), and it is
  the one piece of caller state that legitimately decides access;
* everything else the caller sent is dropped.

A caller therefore cannot name a path, a document kind, a root, a domain or a
generation and change the verdict. The only caller-controlled input that
reaches a gate is the session cookie, exactly as it reaches the static gate.

The reader contract
-------------------
The route is a FACTORY. It is built around ONE trusted, injected
``SelectedGenerationReader`` — the incumbent verified snapshot facade plus
the pure projection. The main application mounts this route; deployment binds
its private storage reader explicitly. This module never
parses a manifest, never reads a published file, never recomputes an
intelligence value, never grades, never collects, never publishes, never
changes watch state, and never serves a legacy or empty fallback when the
reader is unavailable.

The reader is called EXACTLY ONCE per allowed request, AFTER both gates have
answered affirmatively for every required resource. It receives a
``SectorGenerationRequest`` carrying one closed audience choice and nothing
else: no caller path, URL, domain, root or generation override is representable
in that object.

Readers are resolved in one rule, not two mechanisms: the reader injected into
the factory wins; when the factory was given none, the installed
``app.state.sector_generation_reader`` capability is used. Anything that is not
a usable reader is UNAVAILABLE (503), never permission to serve a public
fallback.

Honesty law
-----------
The response carries the source's own session date, publication timestamp and
qualification VERBATIM. This module never substitutes the poll time for the
source time, never re-derives a freshness verdict, and never relabels a stale
generation as current: a healthy but stale projection keeps its explicit,
truthful qualification. A date in this response is always the source's date.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.paywall import paywall_check
from app.regwall import regwall_check
from lib.sector_generation_wire import (
    MAX_ENCODED_BYTES, SCHEMA, SectorGenerationTooLarge, encode_sector_generation,
)

log = logging.getLogger("macro.sector_generation")

#: Response schema of every failure.
ERROR_SCHEMA = "sector_generation.error/v1"

#: The two audiences this route serves. The set is closed: a caller picks one
#: or gets a 400. There is no third audience and no default-but-hidden mode.
AUDIENCE_PREVIEW = "preview"
AUDIENCE_ENTITLED = "entitled"
AUDIENCES: tuple[str, ...] = (AUDIENCE_PREVIEW, AUDIENCE_ENTITLED)

#: The audience served when the caller names none. ``preview`` is the choice
#: that requires no paid board, so it is the conservative default — but it is
#: NOT free access: it is still gated by the incumbent policy, exactly like the
#: static artifacts it summarizes.
DEFAULT_AUDIENCE = AUDIENCE_PREVIEW

#: Server-owned resource paths whose access is asserted for each audience.
#:
#: These are the SAME files the static estate serves under the same two gates.
#: ``/sectordata/*`` and ``/basketdata/*`` are not named by
#: ``config/site_access.yml``, so they read ``premium`` under the incumbent
#: default-deny rule — which is why ``preview`` is not a free tier.
#: ``/premiumdata/sector_central.json`` is under the ``premiumdata/``
#: ``enforced_early`` prefix, so the entitled audience requires the entitlement
#: even while the global ``PAYWALL_ENABLED`` switch is off.
PREVIEW_RESOURCES: tuple[str, ...] = (
    "/sectordata/sector_central.json",
    "/sectordata/sector_cycles.json",
    "/basketdata/baskets.json",
    "/basketdata/si_handoff.json",
    "/basketdata/action_board.json",
)
ENTITLED_RESOURCES: tuple[str, ...] = PREVIEW_RESOURCES + (
    "/premiumdata/sector_central.json",
)
RESOURCES_BY_AUDIENCE: dict[str, tuple[str, ...]] = {
    AUDIENCE_PREVIEW: PREVIEW_RESOURCES,
    AUDIENCE_ENTITLED: ENTITLED_RESOURCES,
}

#: Hard ceiling on the encoded response body. A larger projection is refused
#: rather than truncated: a partially served generation is not a generation.

#: Every response — success and failure — is private, uncacheable and
#: cookie-varying. Nothing here may be cached by a shared proxy.
_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Cookie",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}

# Closed error vocabulary. Nothing else is ever emitted to a caller.
ERROR_REQUEST_INVALID = "REQUEST_INVALID"
ERROR_AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
ERROR_ENTITLEMENT_REQUIRED = "ENTITLEMENT_REQUIRED"
ERROR_RESOURCE_NOT_AVAILABLE = "RESOURCE_NOT_AVAILABLE"
ERROR_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERROR_GENERATION_UNAVAILABLE = "SECTOR_GENERATION_UNAVAILABLE"
ERROR_GENERATION_TOO_LARGE = "SECTOR_GENERATION_TOO_LARGE"

_SESSION_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_QUALIFICATIONS = frozenset(("accepted", "stale", "degraded"))


@dataclass(frozen=True)
class SectorGenerationRequest:
    """What the reader is asked for.

    Exactly one field, and it is a closed server-side audience constant — not a
    caller string that was merely validated. A caller cannot express a path, a
    URL, a domain, a root or a generation id here, so the reader cannot be
    steered off the coherent generation.
    """

    audience: str


@dataclass(frozen=True)
class SectorGeneration:
    """One already-verified, authorized coherent Sector projection.

    The reader MUST return the source's own facts alongside the payload:

    * ``payload`` — the authorized projection (a JSON object);
    * ``source_session`` — the market session the source describes, ``YYYY-MM-DD``;
    * ``published_at`` — when the source published it, ISO-8601;
    * ``qualification`` — the source's own freshness/state word.

    The envelope copies these verbatim. It never recomputes, re-derives or
    refreshes them, so a stale-but-truthful projection stays truthful.
    """

    payload: Mapping[str, Any]
    source_session: str
    published_at: str
    qualification: str


@runtime_checkable
class SelectedGenerationReader(Protocol):
    """The trusted server capability this route reads through."""

    def read_selected_generation(
        self, request: SectorGenerationRequest
    ) -> SectorGeneration:
        """Return the authorized projection for ``request.audience``.

        The implementation is the corrected publisher plus the pure projection.
        It must not raise for an ordinary business outcome; a failure that
        cannot be represented is an exception, which this envelope treats as
        unavailable.
        """
        ...  # pragma: no cover - protocol declaration


def _error(status: int, code: str) -> JSONResponse:
    """A closed, safe failure body.

    No stack, no path, no manifest, no row name, no hash, and no echo of the
    caller's own input.
    """
    return JSONResponse(
        {"schema": ERROR_SCHEMA, "code": code},
        status_code=status,
        headers=_HEADERS,
    )


def _controlled_request(request: Request, resource_path: str) -> Request:
    """Build the server-owned view of the caller's request for one gate.

    See the module docstring: the session cookie survives, the resource and
    asset semantics are overwritten, and every caller document-classification
    header is dropped.
    """
    raw_headers = [
        (b"cookie", request.headers.get("cookie", "").encode("latin-1")),
        (b"x-original-uri", resource_path.encode("latin-1")),
        (b"x-original-kind", b"asset"),
    ]
    scope = dict(request.scope)
    scope["type"] = "http"
    scope["method"] = "GET"
    scope["headers"] = raw_headers
    scope["query_string"] = b""
    return Request(scope)


def _gate_denial(gate: str, response: Response) -> JSONResponse | None:
    """Translate one incumbent gate answer into this route's closed classes.

    ``None`` means the gate allowed. The incumbent denial CLASS is preserved —
    an authentication failure stays an authentication failure and a locked
    entitlement stays a locked entitlement. No new distinction is invented
    between an identity provider and an entitlement store.
    """
    status = response.status_code
    if 200 <= status < 300:
        return None
    if gate == "regwall":
        # The asset class is 401. A 302 can only appear if document semantics
        # leaked in, which this module does not allow; it is still reported as
        # the authentication class rather than as a redirect out of a JSON API.
        if status in (401, 302):
            return _error(401, ERROR_AUTHENTICATION_REQUIRED)
        return _error(503, ERROR_SERVICE_UNAVAILABLE)
    if status == 403:
        return _error(403, ERROR_ENTITLEMENT_REQUIRED)
    if status == 404:
        return _error(404, ERROR_RESOURCE_NOT_AVAILABLE)
    if status == 401:
        return _error(401, ERROR_AUTHENTICATION_REQUIRED)
    return _error(503, ERROR_SERVICE_UNAVAILABLE)


def _authorize(request: Request, resources: Sequence[str]) -> JSONResponse | None:
    """Run both incumbent gates over every required resource.

    Every gate of every required resource must answer affirmatively before the
    reader is reached. Any exception fails closed.
    """
    for resource in resources:
        try:
            controlled = _controlled_request(request, resource)
        except Exception as exc:  # noqa: BLE001 — fail closed
            log.warning("sector_generation: request view failed (%s)", type(exc).__name__)
            return _error(503, ERROR_SERVICE_UNAVAILABLE)
        try:
            regwall = regwall_check(controlled)
        except Exception as exc:  # noqa: BLE001 — fail closed
            log.warning("sector_generation: regwall failed closed (%s)", type(exc).__name__)
            return _error(503, ERROR_SERVICE_UNAVAILABLE)
        denial = _gate_denial("regwall", regwall)
        if denial is not None:
            return denial
        try:
            paywall = paywall_check(controlled)
        except Exception as exc:  # noqa: BLE001 — fail closed
            log.warning("sector_generation: paywall failed closed (%s)", type(exc).__name__)
            return _error(503, ERROR_SERVICE_UNAVAILABLE)
        denial = _gate_denial("paywall", paywall)
        if denial is not None:
            return denial
    return None


def _parse_audience(request: Request) -> tuple[str | None, JSONResponse | None]:
    """Resolve the one closed audience choice, or refuse the request.

    ``audience`` is the only accepted query parameter. Any other parameter —
    and therefore every attempt to name a path, a URL, a domain, a root or a
    generation — is a 400, as is a repeated ``audience``.
    """
    items = request.query_params.multi_items()
    if len(items) > 1:
        return None, _error(400, ERROR_REQUEST_INVALID)
    if not items:
        return DEFAULT_AUDIENCE, None
    key, value = items[0]
    if key != "audience" or value not in AUDIENCES:
        return None, _error(400, ERROR_REQUEST_INVALID)
    return value, None


def _resolve_reader(
    request: Request, injected: SelectedGenerationReader | None
) -> SelectedGenerationReader | None:
    """One resolution rule: the injected reader wins, else the installed one."""
    candidate = injected
    if candidate is None:
        candidate = getattr(request.app.state, "sector_generation_reader", None)
    if candidate is None:
        return None
    if not isinstance(candidate, SelectedGenerationReader):
        return None
    if not callable(getattr(candidate, "read_selected_generation", None)):
        return None
    return candidate


def _coerce_generation(result: Any, *, audience: str) -> SectorGeneration | None:
    """Validate the reader's result against the typed contract.

    A structurally equivalent object is accepted so an upstream owner is not
    forced to import this module's dataclass, but every field is still checked:
    the payload must be a JSON object and the three source facts must have
    their documented shape. A result that fails is CORRUPT, not an empty
    success.
    """
    payload = getattr(result, "payload", None)
    source_session = getattr(result, "source_session", None)
    published_at = getattr(result, "published_at", None)
    qualification = getattr(result, "qualification", None)
    if payload is None or source_session is None:
        return None
    if published_at is None or qualification is None:
        return None
    if not isinstance(payload, Mapping):
        return None
    if not isinstance(source_session, str) or not _SESSION_DATE.fullmatch(source_session):
        return None
    try:
        date.fromisoformat(source_session)
        if not isinstance(published_at, str):
            return None
        publication = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if publication.tzinfo is None or publication.utcoffset() is None:
            return None
    except (TypeError, ValueError):
        return None
    if not isinstance(qualification, str) or qualification not in _QUALIFICATIONS:
        return None
    data, receipt = payload.get("data"), payload.get("receipt")
    if (not isinstance(data, Mapping)
            or data.get("schema") != "sector_native_view.v1"
            or data.get("audience") != audience):
        return None
    if (not isinstance(receipt, Mapping)
            or receipt.get("schema") != "sector_native_view.receipt.v1"):
        return None
    # The transport may not disagree with the actual projection receipt. An
    # older explicitly declared Brief baseline remains inside that projection;
    # it is not substituted for the cohort's source session here.
    for name, value in (
        ("source_session", source_session),
        ("published_at", published_at),
        ("qualification", qualification),
    ):
        if receipt.get(name) != value:
            return None
    return SectorGeneration(
        # This materializes only the outer mapping. Serialization below captures
        # the full response bytes; it is not a claim of deep immutability.
        payload=dict(payload),
        source_session=receipt["source_session"],
        published_at=receipt["published_at"],
        qualification=receipt["qualification"],
    )


def create_router(reader: SelectedGenerationReader | None = None) -> APIRouter:
    """Build the Sector generation read router around ONE trusted reader.

    The main application registers this router once. Its reader capability is
    configured separately from an explicit deployment-owned private root.
    Unconfigured/unavailable storage reports UNAVAILABLE, with no legacy fallback.
    """
    router = APIRouter()

    @router.get("/api/sector-generation")
    def sector_generation(request: Request) -> Response:
        audience, invalid = _parse_audience(request)
        if invalid is not None:
            return invalid

        denial = _authorize(request, RESOURCES_BY_AUDIENCE[audience])
        if denial is not None:
            return denial

        try:
            # Resolution, user-defined properties/mappings and serialization are
            # all within the same closed error boundary as the reader call.
            resolved = _resolve_reader(request, reader)
            if resolved is None:
                return _error(503, ERROR_GENERATION_UNAVAILABLE)
            result = resolved.read_selected_generation(
                SectorGenerationRequest(audience=audience)
            )
            generation = _coerce_generation(result, audience=audience)
            if generation is None:
                return _error(503, ERROR_GENERATION_UNAVAILABLE)
            encoded = encode_sector_generation(
                audience=audience, source_session=generation.source_session,
                published_at=generation.published_at,
                qualification=generation.qualification,
                projection=generation.payload, max_encoded_bytes=MAX_ENCODED_BYTES,
            )
        except SectorGenerationTooLarge:
            return _error(503, ERROR_GENERATION_TOO_LARGE)
        except Exception as exc:  # noqa: BLE001 — every malformed reader fails closed
            log.warning("sector_generation: reader envelope failed (%s)", type(exc).__name__)
            return _error(503, ERROR_GENERATION_UNAVAILABLE)
        return Response(content=encoded, media_type="application/json", headers=_HEADERS)

    return router
