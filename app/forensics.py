"""Authenticated serving route for the private Filing Forensics state."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute

from engine.fundamental_forensics.health import evaluate_health
from engine.fundamental_forensics.latency import RECORDER, evaluate_slo, load_slo_config
from engine.fundamental_forensics.private_state import load_state_blob


class _TimedRoute(APIRoute):
    """FIF V0-a: time each real route's work and record the distribution.

    The timed span is the whole route handler — dependency solving included
    (FastAPI solves dependencies inside the handler), so an auth rejection is
    timed too. Only success responses (2xx/3xx) enter the percentile window:
    4xx responses raise the route template's ``client_error_n`` and 5xx
    responses its ``error_n``, both outside the window, so a burst of fast
    401/403/400 rejections can never drag p95 down to a stale green. The
    dedicated method-not-allowed handlers never reach real handler work and
    are not recorded at all. The ``Server-Timing`` header rides success
    responses only, and never the file exports: A54 pins identical export
    posts to byte-identical responses, headers included, so an export is
    recorded but carries no per-request duration. An ``HTTPException`` (the
    router's expected failure boundary) is counted under its own status and
    re-raised unchanged, any
    other exception is counted as a 500 and re-raised unchanged. Recording
    itself can never alter a status, body or existing header: it sits inside
    its own ``try/except Exception: pass``.
    """

    def get_route_handler(self):
        original = super().get_route_handler()

        async def timed_route_handler(request: Request) -> Response:
            if self.endpoint in _METHOD_NOT_ALLOWED_ENDPOINTS:
                # A private 405 answers before any real handler work runs:
                # not a latency sample, not a client-error count.
                return await original(request)
            t0 = time.perf_counter()
            try:
                response = await original(request)
            except HTTPException as exc:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                try:
                    RECORDER.record(self.path, duration_ms, exc.status_code)
                except Exception:  # noqa: BLE001 - timing must never fail a request
                    pass
                raise
            except Exception:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                try:
                    RECORDER.record(self.path, duration_ms, 500)
                except Exception:  # noqa: BLE001 - timing must never fail a request
                    pass
                raise
            duration_ms = (time.perf_counter() - t0) * 1000.0
            if self.path not in _BYTE_IDENTICAL_EXPORT_PATHS:
                response.headers["Server-Timing"] = f"fif;dur={duration_ms:.1f}"
            try:
                RECORDER.record(self.path, duration_ms, response.status_code)
            except Exception:  # noqa: BLE001 - timing must never fail a request
                pass
            return response

        return timed_route_handler


router = APIRouter(route_class=_TimedRoute)
log = logging.getLogger("fundamental_forensics.api")
REPO = Path(os.environ.get("MACRO_REPO", "/opt/macro"))

# ---------------------------------------------------------------------------
# FIF D3 dataset-mode selection: explicit, documented, deny-by-default.
#
# FIF_FINANCIAL_DATASET_MODE is unset or "golden" (the default) = exactly the
# pre-D3 wiring, byte for byte. "production" = the production providers over
# the immutable dataset store, with NO fallback to the golden corpus. Any
# other value is a configuration error: names-only log, typed refusal, and
# the private 503 — an invalid mode must never degrade into an undocumented
# selection. Documented in
# research/financial_intelligence_fabric/FIF_3A3_REUSE_MAP.md (D3 section).
# ---------------------------------------------------------------------------

FIF_FINANCIAL_DATASET_MODE_ENV = "FIF_FINANCIAL_DATASET_MODE"
_LAWFUL_FINANCIAL_DATASET_MODES = ("golden", "production")


def _financial_dataset_mode() -> str:
    raw = os.environ.get(FIF_FINANCIAL_DATASET_MODE_ENV)
    if raw is None or raw == "":
        return "golden"
    if raw in _LAWFUL_FINANCIAL_DATASET_MODES:
        return raw
    # NAMES ONLY — never the value it rejected.
    log.warning(
        "%s holds an unsupported mode; refusing to select any dataset corpus",
        FIF_FINANCIAL_DATASET_MODE_ENV,
    )
    from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
        ProductionDatasetModeError,
    )

    raise ProductionDatasetModeError(
        f"{FIF_FINANCIAL_DATASET_MODE_ENV} is not a supported dataset mode"
    )

# The receipt API is an authenticated, private research surface even when it is
# mounted by itself in a narrow test app (and therefore outside app.main's
# no-store middleware).  Keep the policy on both successful responses and the
# expected failure boundary: caches must never replay an entitlement or a
# receipt response across users.
_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}

_SNAPSHOT_ID_RE = re.compile(r"\Affqsv2_[a-f0-9]{64}\Z")
_ROOT_CELL_ID_RE = re.compile(r"\Ametric_cell_[a-f0-9]{64}\Z")
# FIF PF-3: the optional health ``entity_id`` query parameter names the issuer
# whose production generation headers are wanted. Only a full match may reach
# a store key; anything else answers with no generation headers, never an
# error and never the raw value in a log line.
# FIF PF r1 (R3): the code tail follows the canonical issuer grammar
# (lib/dataos/identity.py ``_CODE_RE`` — '.' and '-' are real US class
# suffixes, 'BRK-B' included) and the length is bounded separately.
_HEALTH_ENTITY_ID_RE = re.compile(r"ISS:[A-Z]{2}-[A-Z0-9]{4}-[A-Z0-9][A-Z0-9.\-]*")
_MAX_QUERY_VALUE_BYTES = 128
# Bounded receipt reads do not automatically bound response construction.  A
# valid sealed receipt can name many selected leaves; never turn it into a
# multi-megabyte roots page or detail waterfall at request time.
_MAX_LEAF_REFS_PER_ROOT = 1_024
_MAX_LEAF_REFS_PER_ROOT_RESPONSE = 3_072
_MAX_LEAF_REFS_PER_ROOTS_PAGE = 12_288
_MAX_ROOT_DETAIL_RESPONSE_BYTES = 4 * 1024 * 1024
_ROOT_DETAIL_WATERFALL_FIELD_BYTES = len(b',"waterfall":[]')
_B3_PROJECTION_FIELDS = frozenset(
    {
        "attestation_id",
        "authority_snapshot_id",
        "package_id",
        "extraction_id",
        "cik",
        "accession",
        "companyfacts_capture_id",
        "companyfacts_manifest_id",
        "companyfacts_response_sha256",
        "companyfacts_match_count",
        "attested_at",
    }
)
_STORE_LOCK = threading.Lock()
_STORE_CACHE: Any | None = None
_STORE_INITIALIZED = False
_PRIVATE_HEADER_NAMES = frozenset(name.lower() for name in _PRIVATE_HEADERS)
_CONVERSION_RECEIPT_CLOCK_FIELDS = (
    "acquisition_started_at",
    "captured_at",
    "recorded_at",
    "source_snapshot_at",
    "submissions_recorded_at",
)


def _private(response: Response) -> None:
    """Apply the private policy in standalone-router tests and production."""
    response.headers.update(_PRIVATE_HEADERS)


def _private_error(
    status_code: int,
    detail: Any,
    extra_headers: Mapping[str, str] | None = None,
) -> HTTPException:
    """Construct an expected failure which cannot be shared-cached."""
    # HTTP field names are case-insensitive.  Normalize only for comparison so
    # a hostile/lowercase upstream ``cache-control`` or mixed-case ``Vary``
    # cannot coexist with and weaken the route policy.  Unrelated safe headers
    # such as WWW-Authenticate remain intact.
    inherited = {
        str(name): str(value)
        for name, value in dict(extra_headers or {}).items()
        if str(name).lower() not in _PRIVATE_HEADER_NAMES
    }
    return HTTPException(
        status_code=status_code,
        detail=detail,
        # Inherited auth/paywall headers are informative only.  The private
        # policy is non-negotiable and must not be weakened by an upstream
        # exception's Cache-Control/Vary directive.
        headers={**inherited, **_PRIVATE_HEADERS},
    )


def _unavailable() -> HTTPException:
    """Do not distinguish missing, malformed, non-strict, or unavailable R2 state."""
    return _private_error(503, "attested query history temporarily unavailable")


def require_site_full_user(authorization: str | None = Header(default=None)) -> dict:
    """Lazy wrapper avoids importing partially initialized app.main at mount time."""
    from app.main import require_user as _require_user  # noqa: PLC0415
    from app.paywall import enforce_site_full  # noqa: PLC0415

    try:
        # Authentication must happen before the entitlement check.  More
        # importantly, store construction happens only in endpoint bodies, so
        # either denial returns before a private object can be opened.
        return enforce_site_full(_require_user(authorization), always=True)
    except HTTPException as exc:
        # app.main's API middleware adds only Cache-Control.  This wrapper also
        # runs under isolated router tests, so attach the full privacy policy at
        # the dependency boundary.
        raise _private_error(exc.status_code, exc.detail, exc.headers) from None


@router.get("/api/forensics/state")
def forensics_state(_user: dict = Depends(require_site_full_user)) -> Response:
    """Return the validated gzip object to an entitled user, never a public URL."""
    blob = load_state_blob(REPO)
    if blob is None:
        raise _private_error(503, "forensics state temporarily unavailable")
    return Response(
        content=blob,
        media_type="application/gzip",
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": 'inline; filename="forensics-state.json.gz"',
            "Vary": "Authorization",
            "X-Content-Type-Options": "nosniff",
            "X-Robots-Tag": "noindex, noarchive",
        },
    )


@router.get("/api/forensics/health")
def forensics_health(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    """Return operational/source freshness, never private rows or storage keys.

    FIF D3 adds names/ids-only dataset-mode reporting on the response HEADERS
    (the schema'd payload contract is frozen with ``additionalProperties:
    false``): ``X-FIF-Financial-Dataset-Mode`` always, plus
    ``X-FIF-Dataset-Generation-Id`` and ``X-FIF-Dataset-Admitted-At`` when a
    production generation exists. No object keys, no payloads, no values
    beyond the mode name and the generation id.

    FIF PF-3: the optional ``entity_id`` query parameter names the issuer the
    generation headers describe. Absent, the pre-PF-3 behaviour is unchanged
    byte for byte. Present and a full match of ``_HEALTH_ENTITY_ID_RE``, the
    summary is looked up for exactly that issuer. Present but malformed, or a
    matching issuer with no pointer: no generation headers, the same 200 body,
    never a 4xx/5xx — and the raw value is never logged or passed anywhere
    near a store key. Golden mode never emits generation headers.

    FIF PF r1 (R2): with exactly one well-formed ``entity_id`` in production
    mode the answer also carries ONE names-only pointer header,
    ``X-FIF-Dataset-Pointer``: ``admitted`` (a summary was returned, headers as
    today), ``none`` (the store was built, the lookup did not raise, and the
    pointer is absent) or ``unavailable`` (the store is None, or building it
    or reading the summary raised — the provider's own contract: a damaged
    store is temporarily unavailable, not "not published"). A malformed,
    repeated or over-length id gets no pointer header and no generation
    headers. The absent-parameter path and golden mode stay byte for byte
    unchanged; the JSON body is identical in every case.
    """
    headers = dict(_PRIVATE_HEADERS)
    # A15: an invalid dataset mode refuses health with the same private 503
    # the financial POSTs use — never a 500 and never a silent golden report.
    from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
        ProductionDatasetModeError,
    )

    try:
        mode = _financial_dataset_mode()
    except ProductionDatasetModeError:
        raise _private_error(503, "forensics health temporarily unavailable") from None
    headers["X-FIF-Financial-Dataset-Mode"] = mode
    if mode == "production":
        # PF-3: an absent parameter keeps the D3 default issuer; a present
        # parameter must be the ONLY value and full-match the entity grammar
        # (under the byte bound) before it may name a store key; anything
        # else simply reports no generation. R4: a repeated key is malformed
        # — the module's own rule refuses duplicates rather than choosing one
        # silently — and this route never raises because of the parameter.
        values = request.query_params.getlist("entity_id")
        summary_issuer: str | None = "ISS:US-XNAS-AAPL"
        pointer_reported = False
        if not values:
            pass
        elif len(values) == 1 and len(values[0].encode("utf-8")) <= _MAX_QUERY_VALUE_BYTES:
            if _HEALTH_ENTITY_ID_RE.fullmatch(values[0]):
                summary_issuer = values[0]
                pointer_reported = True
            else:
                summary_issuer = None
        else:
            summary_issuer = None
        if summary_issuer is not None:
            from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
                build_production_dataset_store,
                latest_generation_summary,
            )

            summary = None
            store_readable = False
            try:
                store = build_production_dataset_store()
                if store is not None:
                    summary = latest_generation_summary(store, summary_issuer)
                    store_readable = True
            except Exception as exc:  # noqa: BLE001 - names-only; never leak the cause
                log.warning(
                    "production dataset health summary unavailable (%s)", type(exc).__name__
                )
            if summary is not None:
                headers["X-FIF-Dataset-Generation-Id"] = summary["dataset_generation_id"]
                headers["X-FIF-Dataset-Admitted-At"] = summary["admitted_at"]
                if pointer_reported:
                    headers["X-FIF-Dataset-Pointer"] = "admitted"
            elif pointer_reported:
                headers["X-FIF-Dataset-Pointer"] = (
                    "none" if store_readable else "unavailable"
                )
    payload = evaluate_health(REPO, now=datetime.now(timezone.utc))
    return JSONResponse(payload, headers=headers)


# ---------------------------------------------------------------------------
# FIF V0-a: the entitled latency report — measured distributions judged
# against the DECLARED budgets in config/fundamental_forensics/slo.v1.json.
# ---------------------------------------------------------------------------

_SLO_CONFIG_LOCK = threading.Lock()
_SLO_CONFIG_CACHE: dict | None = None


@router.get("/api/forensics/slo")
def forensics_slo(_user: dict = Depends(require_site_full_user)) -> JSONResponse:
    """Report measured per-route latency distributions against the SLO config.

    Entitled exactly like health. The payload carries route templates and
    measured aggregates only — never an issuer, tenant, query or user
    identifier. The config is loaded once, at first use, from the repo path;
    a config that cannot be read or parsed is a 503, never a fabricated
    "within" — the report exists only against the real declared budgets. The
    reported ``window`` is the recorder's actual sample window, not the
    config's declared one, and the response carries the full private header
    set with ``Cache-Control: no-store``.
    """
    global _SLO_CONFIG_CACHE
    try:
        with _SLO_CONFIG_LOCK:
            if _SLO_CONFIG_CACHE is None:
                _SLO_CONFIG_CACHE = load_slo_config(
                    REPO / "config" / "fundamental_forensics" / "slo.v1.json"
                )
            config = _SLO_CONFIG_CACHE
    except Exception as exc:  # noqa: BLE001 - names-only; never leak the cause
        log.warning("forensics SLO config unavailable (%s)", type(exc).__name__)
        return JSONResponse(
            {"error": "slo_config_unavailable"},
            status_code=503,
            headers={**_PRIVATE_HEADERS, "Cache-Control": "no-store"},
        )
    evaluation = evaluate_slo(RECORDER.snapshot(), config)
    return JSONResponse(
        {
            "schema": "fif_slo_report.v1",
            "config_status": config["status"],
            "window": RECORDER.window,
            "routes": evaluation["routes"],
            "unbudgeted": evaluation["unbudgeted"],
        },
        headers={**_PRIVATE_HEADERS, "Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------
# Attested history: receipt-serving only, never a request-time verifier.
# ---------------------------------------------------------------------------

def _build_store():
    """Build the DEDICATED attested-history reader lazily, then reuse it.

    The sealed receipts live in their own bucket, addressed only by
    ``FF_ATTESTED_R2_READONLY_{ENDPOINT,ACCESS_KEY_ID,SECRET_ACCESS_KEY,BUCKET}``
    — never the Research Vault bucket and never a generic ``R2_*`` fallback.
    Reconstructing a boto3/R2 client on every request defeats the engine's
    bounded immutable-reader cache and can leak connection pools.  A missing
    store is cached too: it remains a bounded 503 until process restart or the
    explicit test/operator reset, never a fallback to a different bucket.

    A misconfigured value raises from the factory.  That is cached as an
    absent store rather than propagated: the route's contract is one bounded,
    private-header 503, not an unbounded exception or a stack trace.
    """
    global _STORE_CACHE, _STORE_INITIALIZED
    with _STORE_LOCK:
        if _STORE_INITIALIZED:
            return _STORE_CACHE
        store = None
        try:
            from engine.fundamental_forensics.attested_history_store import (  # noqa: PLC0415
                ATTESTED_HISTORY_ENV_NAMES,
                AttestedHistoryStoreError,
                build_attested_history_store,
            )

            store = build_attested_history_store()
            if store is None:
                # An absent store is cached below and becomes a permanent 503,
                # so a silent None would leave the operator nothing to act on.
                # NAMES only -- never a value.  A half-delivered credential set
                # is the realistic case: the deploy workflow strips all four
                # FF_ATTESTED_R2_READONLY_* lines and re-adds only the non-empty
                # ones, so one dispatch mid-rotation can leave a partial set.
                absent = [n for n in ATTESTED_HISTORY_ENV_NAMES if not os.environ.get(n)]
                log.warning(
                    "attested history store not configured (absent: %s)",
                    ",".join(absent) or "none - values present but rejected",
                )
        except AttestedHistoryStoreError as exc:
            # This class's messages are fixed literals that never interpolate a
            # configuration value, so the message itself is safe to log -- and
            # it is the only thing that distinguishes a bad endpoint from a bad
            # bucket, key, TTL, or refresh margin. Without it all five collapse
            # into one indistinguishable line behind a permanent 503.
            log.warning("attested history store unavailable: %s", exc)
            store = None
        except Exception as exc:  # noqa: BLE001 - fail closed, never leak the cause
            # Everything else (boto/botocore especially) records the TYPE only:
            # those messages can quote configuration values, and this bucket's
            # credentials must never reach a log line.
            log.warning("attested history store unavailable (%s)", type(exc).__name__)
            store = None
        _STORE_CACHE = store
        _STORE_INITIALIZED = True
        return _STORE_CACHE


def _reset_store_cache() -> None:
    """Resettable test seam; production does not refresh or swap private stores."""
    global _STORE_CACHE, _STORE_INITIALIZED
    with _STORE_LOCK:
        _STORE_CACHE = None
        _STORE_INITIALIZED = False


def load_attested_query_receipt_index(store: Any, *, snapshot_id: str | None = None) -> Any:
    """Late-bind the bounded engine reader so this router has no import-time cycle.

    The engine reader validates/digest-checks the pointer, manifest, coverage,
    bindings, and receipt projection.  It intentionally does not replay the
    v1 snapshot, fetch SEC sources, or write an object; this transport layer
    must not turn a read request into a 1.5 GB verification job.
    """
    from engine.fundamental_forensics.attested_query_snapshots import (  # noqa: PLC0415
        load_attested_query_receipt_index as _load,
    )

    return _load(store, snapshot_id=snapshot_id)


def _strict_snapshot_id(snapshot_id: str) -> str:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise _private_error(400, "invalid attested snapshot id")
    return snapshot_id


def _safe_cell_id(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _ROOT_CELL_ID_RE.fullmatch(value):
        raise _private_error(400, f"invalid {field}")
    return value


def _single_query_value(request: Request, name: str) -> str | None:
    """Bound query input and reject duplicate keys rather than choosing one silently."""
    values = request.query_params.getlist(name)
    if not values:
        return None
    if len(values) != 1:
        raise _private_error(400, f"invalid {name}")
    value = values[0]
    if len(value.encode("utf-8")) > _MAX_QUERY_VALUE_BYTES:
        raise _private_error(400, f"invalid {name}")
    return value


def _page_arguments(request: Request) -> tuple[str | None, int]:
    """Parse keyset controls ourselves so every invalid-input error stays private."""
    cursor = _single_query_value(request, "cursor")
    if cursor is not None:
        _safe_cell_id(cursor, field="cursor")

    raw_limit = _single_query_value(request, "limit")
    if raw_limit is None:
        return cursor, 25
    # ASCII decimal only: no whitespace, sign, float, or surprising coercion.
    if not raw_limit.isascii() or not raw_limit.isdecimal():
        raise _private_error(400, "invalid limit")
    limit = int(raw_limit)
    if not 1 <= limit <= 100:
        raise _private_error(400, "invalid limit")
    return cursor, limit


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} is not a mapping")
    return value


def _index_attr(index: Any, name: str) -> Any:
    value = getattr(index, name, None)
    if value is None:
        raise ValueError(f"receipt index missing {name}")
    return value


def _load_receipt_index(snapshot_id: str | None = None) -> Any:
    """Open the private store only after auth/entitlement, then fail closed."""
    try:
        store = _build_store()
        if store is None:
            raise RuntimeError("private store is not configured")
        index = load_attested_query_receipt_index(store, snapshot_id=snapshot_id)
        if index is None:
            raise RuntimeError("receipt index is unavailable")
        return index
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - private storage is a fail-closed boundary
        raise _unavailable() from exc


def _manifest(index: Any) -> Mapping[str, Any]:
    return _mapping(_index_attr(index, "manifest"), field="receipt manifest")


def _receipt_identity(index: Any) -> dict[str, Any]:
    """Return only safe identity fields, never manifest/object-store key material."""
    snapshot_id = _index_attr(index, "snapshot_id")
    base_snapshot_id = _index_attr(index, "base_snapshot_id")
    query_hash = _index_attr(index, "query_hash")
    published_at = _index_attr(index, "published_at")
    if (
        not isinstance(snapshot_id, str)
        or not _SNAPSHOT_ID_RE.fullmatch(snapshot_id)
        or not isinstance(base_snapshot_id, str)
        or not base_snapshot_id.startswith("ffqs_")
        or not isinstance(query_hash, str)
        or not re.fullmatch(r"[a-f0-9]{64}", query_hash)
    ):
        raise ValueError("receipt identity is invalid")
    # The engine emits a UTC datetime, while purpose-built test seams may emit
    # the canonical wire string.  Neither type is a private storage location.
    if hasattr(published_at, "isoformat"):
        published_at = published_at.isoformat().replace("+00:00", "Z")
    if not isinstance(published_at, str) or len(published_at) > 64:
        raise ValueError("receipt publication clock is invalid")
    return {
        "snapshot_id": snapshot_id,
        "base_snapshot_id": base_snapshot_id,
        "query_hash": query_hash,
        "published_at": published_at,
    }


def _authority(index: Any) -> dict[str, Any]:
    """The narrow positive claim is immutable; manifest nonclaims stay exact."""
    manifest = _manifest(index)
    nonclaims = _mapping(manifest.get("nonclaims"), field="receipt nonclaims")
    if any(value is not False for value in nonclaims.values()):
        raise ValueError("receipt nonclaims are invalid")
    return {
        "positive_claim": "B3_selected_member_companyfacts_row_correspondence_only",
        "coverage_scope": "selected_raw_fact_leaves_only",
        "claim_basis": "sealed_publication_receipt",
        "source_reverified_at_read": False,
        "match_body_replayed_at_read": False,
        "nonclaims": dict(nonclaims),
    }


def _coverage_components(row: Any) -> tuple[Mapping[str, Any], str, Sequence[str], Sequence[str], Sequence[str], str]:
    """Validate immutable coverage sizes before allocating response lists."""
    value = _mapping(row, field="root coverage")
    root_cell_id = value.get("root_cell_id")
    selected = value.get("selected_leaf_occurrence_ids")
    eligible = value.get("eligible_leaf_occurrence_ids")
    attested = value.get("attested_occurrence_ids")
    status = value.get("status")
    if (
        not isinstance(root_cell_id, str)
        or not _ROOT_CELL_ID_RE.fullmatch(root_cell_id)
        or not isinstance(selected, (list, tuple))
        or not isinstance(eligible, (list, tuple))
        or not isinstance(attested, (list, tuple))
        or status not in {"all_leaves_attested", "partially_attested", "not_attested", "not_evaluable"}
    ):
        raise ValueError("root coverage is invalid")
    if (
        len(selected) > _MAX_LEAF_REFS_PER_ROOT
        or len(eligible) > _MAX_LEAF_REFS_PER_ROOT
        or len(attested) > _MAX_LEAF_REFS_PER_ROOT
        or len(selected) + len(eligible) + len(attested) > _MAX_LEAF_REFS_PER_ROOT_RESPONSE
    ):
        raise ValueError("root coverage exceeds response budget")
    for collection in (selected, eligible, attested):
        if any(not isinstance(item, str) or len(item) > _MAX_QUERY_VALUE_BYTES for item in collection):
            raise ValueError("root coverage is invalid")
    return value, root_cell_id, selected, eligible, attested, status


def _coverage_row(row: Any) -> dict[str, Any]:
    """Limit list/detail coverage to the exact immutable coverage arrays."""
    _value, root_cell_id, selected, eligible, attested, status = _coverage_components(row)
    return {
        "root_cell_id": root_cell_id,
        "selected_leaf_occurrence_ids": list(selected),
        "eligible_leaf_occurrence_ids": list(eligible),
        "attested_occurrence_ids": list(attested),
        "status": status,
    }


def _root_ids(index: Any) -> Sequence[str]:
    """Read the engine's validated immutable root-id index without copying it."""
    root_ids = _index_attr(index, "root_ids")
    if not isinstance(root_ids, Sequence) or isinstance(root_ids, (str, bytes)):
        raise ValueError("receipt root index is invalid")
    # The engine validates order/uniqueness while digest-checking coverage.  Do
    # not rewalk up to 100k rows in HTTP just to reconstruct the same index.
    endpoints = (*root_ids[0:1], *root_ids[-1:])
    if any(not isinstance(value, str) or not _ROOT_CELL_ID_RE.fullmatch(value) for value in endpoints):
        raise ValueError("receipt root index endpoints are invalid")
    return root_ids


def _roots_by_id(index: Any) -> Mapping[str, Any]:
    return _mapping(_index_attr(index, "roots_by_id"), field="receipt root index")


def _minimal_conversion_receipt(index: Any) -> dict[str, Any]:
    """Expose receipt identity/counts, never conversion inputs, rows, or sources."""
    receipt = _mapping(_manifest(index).get("companyfacts_conversion_receipt"), field="conversion receipt")
    scalar_fields = (
        "receipt_id",
        "schema",
        "adapter_version",
        "capture_id",
        "manifest_id",
        "cik",
        "availability",
        "occurrence_count",
        "output_occurrence_count",
        "pit_eligible_count",
    )
    if any(name not in receipt for name in (*scalar_fields, "clocks")):
        raise ValueError("conversion receipt is incomplete")
    clocks = _mapping(receipt["clocks"], field="conversion receipt clocks")
    if set(clocks) != set(_CONVERSION_RECEIPT_CLOCK_FIELDS) or any(
        not isinstance(clocks[name], str) or not clocks[name] or len(clocks[name]) > 64
        for name in _CONVERSION_RECEIPT_CLOCK_FIELDS
    ):
        raise ValueError("conversion receipt clocks are invalid")
    if any(
        not isinstance(receipt[name], str) or not receipt[name]
        for name in scalar_fields[:6]
    ) or not isinstance(receipt["availability"], str):
        raise ValueError("conversion receipt identity is invalid")
    if any(
        isinstance(receipt[name], bool) or not isinstance(receipt[name], int) or receipt[name] < 0
        for name in scalar_fields[-3:]
    ):
        raise ValueError("conversion receipt counts are invalid")

    # Project each public scalar explicitly.  The engine index recursively
    # freezes its manifest with MappingProxyType, which is intentionally not
    # JSON serializable.  Do not generic-thaw the receipt: doing so would make a
    # future private source/object field one shallow edit away from HTTP.
    return {
        "receipt_id": receipt["receipt_id"],
        "schema": receipt["schema"],
        "adapter_version": receipt["adapter_version"],
        "capture_id": receipt["capture_id"],
        "manifest_id": receipt["manifest_id"],
        "cik": receipt["cik"],
        "clocks": {name: clocks[name] for name in _CONVERSION_RECEIPT_CLOCK_FIELDS},
        "availability": receipt["availability"],
        "occurrence_count": receipt["occurrence_count"],
        "output_occurrence_count": receipt["output_occurrence_count"],
        "pit_eligible_count": receipt["pit_eligible_count"],
    }


def _latest_payload(index: Any) -> dict[str, Any]:
    manifest = _manifest(index)
    policy = _mapping(manifest.get("policy"), field="receipt policy")
    clocks = _mapping(manifest.get("clocks"), field="receipt clocks")
    coverage_summary = _mapping(manifest.get("coverage_summary"), field="coverage summary")
    return _receipt_identity(index) | {
        "policy": dict(policy),
        "clocks": dict(clocks),
        "coverage_summary": dict(coverage_summary),
        "companyfacts_conversion_receipt": _minimal_conversion_receipt(index),
        "authority": _authority(index),
    }


def _page_root_ids(root_ids: Sequence[str], cursor: str | None, limit: int) -> tuple[Sequence[str], str | None, str | None]:
    """Bisect an immutable ID index, then read only the requested coverage rows."""
    start = 0
    if cursor is not None:
        start = bisect_right(root_ids, cursor)
        if start == 0 or root_ids[start - 1] != cursor:
            raise _private_error(400, "invalid cursor")
    page_ids = root_ids[start : start + limit]
    next_cursor = page_ids[-1] if start + len(page_ids) < len(root_ids) and page_ids else None
    return page_ids, cursor, next_cursor


def _page_coverage_rows(roots_by_id: Mapping[str, Any], page_ids: Sequence[str]) -> list[dict[str, Any]]:
    """Budget page leaves before serializing one row; no all-roots materialization."""
    raw_rows: list[tuple[str, Any]] = []
    leaf_refs = 0
    for root_id in page_ids:
        raw_root = roots_by_id.get(root_id)
        _value, covered_id, selected, eligible, attested, _status = _coverage_components(raw_root)
        if covered_id != root_id:
            raise ValueError("receipt root index binding is invalid")
        leaf_refs += len(selected) + len(eligible) + len(attested)
        if leaf_refs > _MAX_LEAF_REFS_PER_ROOTS_PAGE:
            raise ValueError("roots page exceeds response budget")
        raw_rows.append((root_id, raw_root))
    return [_coverage_row(raw_root) for _root_id, raw_root in raw_rows]


def _attestation_projections(index: Any) -> Mapping[str, Mapping[str, Any]]:
    """Use the engine's pre-indexed compact B3 projections, never raw B3 records."""
    records = _mapping(_index_attr(index, "attestations_by_id"), field="attestation index")
    # The receipt reader has already sealed the entire map.  Walk only entries
    # selected into this bounded waterfall rather than paying O(all B3 records)
    # per detail request.
    return records


def _json_wire_upper_bound(value: Any) -> int:
    """Conservatively size one JSON fragment without retaining its encoding.

    ``ensure_ascii=True`` is never smaller than the UTF-8 JSON emitted by
    Starlette for non-ASCII text.  Measuring one bounded row at a time keeps a
    legal but extremely long canonical decimal from accumulating into a large
    response before the aggregate ceiling is enforced.
    """
    try:
        payload = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("attested history response is not bounded JSON") from exc
    return len(payload)


def _waterfall(
    index: Any,
    root: Mapping[str, Any],
    response_prefix: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bindings = _mapping(_index_attr(index, "bindings_by_occurrence"), field="receipt bindings")
    projections = _attestation_projections(index)
    eligible = set(root["eligible_leaf_occurrence_ids"])
    attested = set(root["attested_occurrence_ids"])
    selected = root["selected_leaf_occurrence_ids"]
    if not attested.issubset(set(selected)) or not eligible.issubset(set(selected)):
        raise ValueError("root coverage membership is invalid")

    # Size every already-built response field, plus the exact punctuation for
    # adding an empty waterfall to that object.  Each emitted row is then sized
    # before retention.  One comma is charged for every row (including the
    # first, where it is a harmless one-byte overestimate), so this remains a
    # conservative bound without ever serializing the growing aggregate.
    wire_bytes = _json_wire_upper_bound(response_prefix) + _ROOT_DETAIL_WATERFALL_FIELD_BYTES
    if wire_bytes > _MAX_ROOT_DETAIL_RESPONSE_BYTES:
        raise ValueError("root detail exceeds serialized response budget")

    rows: list[dict[str, Any]] = []
    for occurrence_id in selected:
        row: dict[str, Any] = {
            "occurrence_id": occurrence_id,
            "eligible": occurrence_id in eligible,
            "attested": occurrence_id in attested,
        }
        if occurrence_id in attested:
            binding = _mapping(bindings.get(occurrence_id), field="occurrence binding")
            attestation_id = binding.get("attestation_id")
            match_id = binding.get("match_id")
            companyfacts = _mapping(binding.get("companyfacts"), field="binding Company Facts projection")
            projection = projections.get(attestation_id)
            if not isinstance(attestation_id, str) or not isinstance(match_id, str) or projection is None:
                raise ValueError("attested occurrence binding is invalid")
            projection = _mapping(projection, field="attestation projection")
            if (
                not attestation_id.startswith("ffatt_")
                or projection.get("attestation_id") != attestation_id
                or set(projection) != _B3_PROJECTION_FIELDS
            ):
                raise ValueError("attestation projection is invalid")
            fields = ("cik", "accession", "taxonomy", "concept", "unit", "start", "end", "value")
            if any(name not in companyfacts for name in fields):
                raise ValueError("binding Company Facts projection is incomplete")
            row.update(
                {
                    "attestation_id": attestation_id,
                    "match_id": match_id,
                    "companyfacts": {
                        "cik": companyfacts["cik"],
                        "accession": companyfacts["accession"],
                        "taxonomy": companyfacts["taxonomy"],
                        "concept": companyfacts["concept"],
                        "unit": companyfacts["unit"],
                        "period": {
                            "start": companyfacts["start"],
                            "end": companyfacts["end"],
                        },
                        "value": companyfacts["value"],
                    },
                    "stored_b3_projection": dict(projection),
                }
            )
        wire_bytes += _json_wire_upper_bound(row) + 1
        if wire_bytes > _MAX_ROOT_DETAIL_RESPONSE_BYTES:
            raise ValueError("root detail exceeds serialized response budget")
        rows.append(row)
    return rows


def _with_unavailable_boundary(callback):
    """Convert malformed index projections into the bounded public 503 contract."""
    try:
        return callback()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - no private parser/storage details over HTTP
        raise _unavailable() from exc


@router.get("/api/forensics/v1/attested-history/latest")
def attested_history_latest(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Return the latest compact immutable receipt; never reverify source at read."""
    _private(response)
    return _with_unavailable_boundary(lambda: _latest_payload(_load_receipt_index()))


@router.get("/api/forensics/v1/attested-history/snapshots/{snapshot_id}/roots")
def attested_history_roots(
    snapshot_id: str,
    request: Request,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Keyset-paginate compact root coverage by immutable root_cell_id."""
    _private(response)
    snapshot_id = _strict_snapshot_id(snapshot_id)
    cursor, limit = _page_arguments(request)

    def payload() -> dict[str, Any]:
        index = _load_receipt_index(snapshot_id)
        identity = _receipt_identity(index)
        if identity["snapshot_id"] != snapshot_id:
            raise ValueError("receipt index returned a different snapshot")
        root_ids = _root_ids(index)
        page_ids, requested_cursor, next_cursor = _page_root_ids(root_ids, cursor, limit)
        roots_by_id = _roots_by_id(index)
        page = _page_coverage_rows(roots_by_id, page_ids)
        return identity | {
            "authority": _authority(index),
            "page": {
                "cursor": requested_cursor,
                "next_cursor": next_cursor,
                "limit": limit,
                "returned": len(page),
                "total": len(root_ids),
            },
            "roots": page,
        }

    return _with_unavailable_boundary(payload)


@router.get("/api/forensics/v1/attested-history/snapshots/{snapshot_id}/roots/{root_cell_id}")
def attested_history_root_detail(
    snapshot_id: str,
    root_cell_id: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Return one selected-leaf waterfall and its compact B3 correspondence receipt."""
    _private(response)
    snapshot_id = _strict_snapshot_id(snapshot_id)
    root_cell_id = _safe_cell_id(root_cell_id, field="root_cell_id")

    def payload() -> dict[str, Any]:
        index = _load_receipt_index(snapshot_id)
        identity = _receipt_identity(index)
        if identity["snapshot_id"] != snapshot_id:
            raise ValueError("receipt index returned a different snapshot")
        raw_root = _roots_by_id(index).get(root_cell_id)
        if raw_root is None:
            raise _private_error(404, "root cell not covered")
        root = _coverage_row(raw_root)
        if root["root_cell_id"] != root_cell_id:
            raise ValueError("receipt root index binding is invalid")
        response_prefix = identity | {
            "authority": _authority(index),
            "root": root,
        }
        return response_prefix | {"waterfall": _waterfall(index, root, response_prefix)}

    return _with_unavailable_boundary(payload)


@router.get(
    "/api/forensics/v1/attested-history/{remainder:path}",
    include_in_schema=False,
)
def attested_history_private_not_found(
    remainder: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Hide malformed/extra history paths behind the same paid private boundary.

    Encoded slashes are decoded before route matching, so an otherwise valid
    root ID followed by ``%2F...`` lands here instead of receiving a framework
    404 without the full private/noindex policy.  Authentication and entitlement
    still run first, and this catchall never constructs or reads the store.
    """
    del remainder
    _private(response)
    raise _private_error(404, "attested history route not found")


# ---------------------------------------------------------------------------
# FIF-2A / FIF-2B / FIF-2C shared JSON admission
# ---------------------------------------------------------------------------

_PRODUCTION_PROVIDER_LOCK = threading.Lock()
_PRODUCTION_QUERY_PROVIDER_CACHE: Any | None = None
_PRODUCTION_PACKET_PROVIDER_CACHE: Any | None = None
_PRODUCTION_STATEMENT_PROVIDER_CACHE: Any | None = None


def _reset_production_provider_cache() -> None:
    """Test/operator hook: drop the singleton production providers + store."""
    global _PRODUCTION_QUERY_PROVIDER_CACHE
    global _PRODUCTION_PACKET_PROVIDER_CACHE
    global _PRODUCTION_STATEMENT_PROVIDER_CACHE
    with _PRODUCTION_PROVIDER_LOCK:
        _PRODUCTION_QUERY_PROVIDER_CACHE = None
        _PRODUCTION_PACKET_PROVIDER_CACHE = None
        _PRODUCTION_STATEMENT_PROVIDER_CACHE = None


def _production_query_provider():
    """Singleton production query provider (per-process store + dataset cache)."""
    global _PRODUCTION_QUERY_PROVIDER_CACHE
    from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
        build_production_dataset_store,
    )
    from engine.fundamental_forensics.production_provider import (  # noqa: PLC0415
        ProductionFinancialQueryProvider,
    )

    with _PRODUCTION_PROVIDER_LOCK:
        if _PRODUCTION_QUERY_PROVIDER_CACHE is None:
            _PRODUCTION_QUERY_PROVIDER_CACHE = ProductionFinancialQueryProvider(
                build_production_dataset_store()
            )
        return _PRODUCTION_QUERY_PROVIDER_CACHE


def _production_packet_provider():
    """Singleton production packet provider (revisions + packet share one)."""
    global _PRODUCTION_PACKET_PROVIDER_CACHE
    from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
        build_production_dataset_store,
    )
    from engine.fundamental_forensics.production_provider import (  # noqa: PLC0415
        ProductionFinancialPacketProvider,
    )

    with _PRODUCTION_PROVIDER_LOCK:
        if _PRODUCTION_PACKET_PROVIDER_CACHE is None:
            _PRODUCTION_PACKET_PROVIDER_CACHE = ProductionFinancialPacketProvider(
                build_production_dataset_store(),
                repo_root=REPO,
            )
        return _PRODUCTION_PACKET_PROVIDER_CACHE


def _production_statement_provider():
    """Singleton production statement provider."""
    global _PRODUCTION_STATEMENT_PROVIDER_CACHE
    from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
        build_production_dataset_store,
    )
    from engine.fundamental_forensics.production_provider import (  # noqa: PLC0415
        ProductionFinancialStatementProvider,
    )

    with _PRODUCTION_PROVIDER_LOCK:
        if _PRODUCTION_STATEMENT_PROVIDER_CACHE is None:
            _PRODUCTION_STATEMENT_PROVIDER_CACHE = ProductionFinancialStatementProvider(
                build_production_dataset_store()
            )
        return _PRODUCTION_STATEMENT_PROVIDER_CACHE


def _financial_query_provider():
    """Query provider under the explicit dataset-mode selection.

    ``golden`` (default) is exactly the pre-D3 wiring: the golden AAPL
    provider over the two committed accessions. ``production`` constructs the
    production provider over the immutable dataset store and NEVER falls back
    to the golden corpus — a missing store or damaged generation is the
    private 503.
    """
    if _financial_dataset_mode() == "production":
        return _production_query_provider()
    from engine.fundamental_forensics.ixbrl_raw_ledger import (  # noqa: PLC0415
        FIF3A4_LINEAGE_AVAILABLE_AT,
        GoldenAaplFinancialQueryProvider,
    )

    return GoldenAaplFinancialQueryProvider(
        repo_root=REPO,
        lineage_evidence_available_at=FIF3A4_LINEAGE_AVAILABLE_AT,
    )


def _financial_revision_provider():
    """Revision provider under the dataset-mode selection (no golden fallback)."""
    if _financial_dataset_mode() == "production":
        return _production_packet_provider()
    from engine.fundamental_forensics.revision_service import (  # noqa: PLC0415
        UnavailableFinancialPacketProvider,
    )

    return UnavailableFinancialPacketProvider()


def _financial_packet_provider():
    """Packet provider under the dataset-mode selection (no golden fallback)."""
    if _financial_dataset_mode() == "production":
        return _production_packet_provider()
    from engine.fundamental_forensics.revision_service import (  # noqa: PLC0415
        UnavailableFinancialPacketProvider,
    )

    return UnavailableFinancialPacketProvider()


def _financial_statement_provider():
    """Statement provider under the dataset-mode selection (no golden fallback)."""
    if _financial_dataset_mode() == "production":
        return _production_statement_provider()
    from engine.fundamental_forensics.statement_service import (  # noqa: PLC0415
        GoldenAaplStatementProvider,
    )

    return GoldenAaplStatementProvider(repo_root=REPO)


def _financial_query_max_request_bytes() -> int:
    from engine.fundamental_forensics.query_service import MAX_REQUEST_BYTES  # noqa: PLC0415

    return MAX_REQUEST_BYTES


async def _read_bounded_request_body(request: Request, max_bytes: int) -> bytes:
    """Read at most ``max_bytes + 1`` from the ASGI stream, then 413.

    Content-Length is an early cheap rejection only.  A missing or lying
    Content-Length cannot force a full-body buffer.
    """
    buf = bytearray()
    limit = max_bytes + 1
    async for chunk in request.stream():
        if not chunk:
            continue
        remaining = limit - len(buf)
        if remaining <= 0:
            raise _private_error(413, "request body exceeds bound")
        if len(chunk) > remaining:
            buf.extend(chunk[:remaining])
            raise _private_error(413, "request body exceeds bound")
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise _private_error(413, "request body exceeds bound")
    return bytes(buf)


async def _admit_json_post_body(request: Request) -> bytes:
    """Auth already ran. Bound Content-Type, Content-Length, and streamed body."""
    max_request_bytes = _financial_query_max_request_bytes()

    cl_header = request.headers.get("content-length")
    if cl_header is not None:
        try:
            cl_int = int(cl_header)
        except (ValueError, TypeError):
            raise _private_error(400, "malformed request")
        if cl_int < 0:
            raise _private_error(400, "malformed request")
        if cl_int > max_request_bytes:
            raise _private_error(413, "request body exceeds bound")

    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";")[0].strip().casefold()
    if media_type != "application/json":
        raise _private_error(400, "malformed request")

    return await _read_bounded_request_body(request, max_request_bytes)


@router.api_route(
    "/api/forensics/v1/financial/query",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"],
)
def financial_query_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/query")
async def financial_query(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Execute a bounded bitemporal metric query and return the governed MetricMatrix receipt."""
    from engine.fundamental_forensics.query_service import (  # noqa: PLC0415
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
        execute_financial_query,
    )

    body = await _admit_json_post_body(request)

    try:
        # Provider construction sits inside the boundary so a refused dataset
        # mode (typed error) is the same private 503 as any other unavailability.
        provider = _financial_query_provider()
        result = execute_financial_query(body=body, provider=provider)
    except FinancialQueryAdmissionError as exc:
        raise _private_error(exc.status_code, exc.detail) from None
    except FinancialQueryUnavailableError:
        raise _private_error(503, "financial query temporarily unavailable") from None
    except Exception:  # noqa: BLE001
        raise _private_error(503, "financial query temporarily unavailable") from None

    return Response(
        content=result.body,
        media_type="application/json",
        headers={
            **_PRIVATE_HEADERS,
            "X-FIF-Response-SHA256": result.sha256,
        },
    )


@router.api_route(
    "/api/forensics/v1/financial/query.xlsx",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD"],
)
def financial_query_xlsx_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/query.xlsx")
async def financial_query_xlsx(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Same admission as the JSON query; return a deterministic .xlsx attachment."""
    from engine.fundamental_forensics.excel_export import (  # noqa: PLC0415
        XLSX_MEDIA_TYPE,
        response_query_id,
        to_xlsx_bytes,
    )
    from engine.fundamental_forensics.query_service import (  # noqa: PLC0415
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
        execute_financial_query,
    )

    body = await _admit_json_post_body(request)

    try:
        provider = _financial_query_provider()
        result = execute_financial_query(body=body, provider=provider)
    except FinancialQueryAdmissionError as exc:
        raise _private_error(exc.status_code, exc.detail) from None
    except FinancialQueryUnavailableError:
        raise _private_error(503, "financial query temporarily unavailable") from None
    except Exception:  # noqa: BLE001
        raise _private_error(503, "financial query temporarily unavailable") from None

    envelope = dict(result.envelope)
    envelope["sha256"] = result.sha256
    payload = to_xlsx_bytes(envelope)
    filename = f"{response_query_id(envelope)}.xlsx"
    return Response(
        content=payload,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            **_PRIVATE_HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-FIF-Response-SHA256": hashlib.sha256(payload).hexdigest(),
            "X-FIF-Receipt-SHA256": result.sha256,
        },
    )


async def _financial_query_export(request: Request, fmt: str) -> Response:
    """Same admission as the JSON query; return a CSV or Parquet attachment."""
    from engine.fundamental_forensics.excel_export import (  # noqa: PLC0415
        response_query_id,
    )
    from engine.fundamental_forensics.query_exports import (  # noqa: PLC0415
        QueryExportError,
        export_query_envelope,
    )
    from engine.fundamental_forensics.query_service import (  # noqa: PLC0415
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
        execute_financial_query,
    )

    body = await _admit_json_post_body(request)
    try:
        provider = _financial_query_provider()
        result = execute_financial_query(body=body, provider=provider)
        export = export_query_envelope(result.envelope, fmt)
    except FinancialQueryAdmissionError as exc:
        raise _private_error(exc.status_code, exc.detail) from None
    except (FinancialQueryUnavailableError, QueryExportError):
        raise _private_error(503, "financial query temporarily unavailable") from None
    except Exception:  # noqa: BLE001
        raise _private_error(503, "financial query temporarily unavailable") from None

    envelope = dict(result.envelope)
    envelope["sha256"] = result.sha256
    filename = f"{response_query_id(envelope)}.{fmt}"
    return Response(
        content=export.payload,
        media_type=export.media_type,
        headers={
            **_PRIVATE_HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-FIF-Response-SHA256": export.sha256,
            "X-FIF-Receipt-SHA256": result.sha256,
        },
    )


@router.api_route(
    "/api/forensics/v1/financial/query.csv",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD"],
)
def financial_query_csv_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/query.csv")
async def financial_query_csv(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Same admission as the JSON query; return a deterministic CSV attachment."""
    return await _financial_query_export(request, "csv")


@router.api_route(
    "/api/forensics/v1/financial/query.parquet",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD"],
)
def financial_query_parquet_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/query.parquet")
async def financial_query_parquet(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Same admission as the JSON query; return a deterministic Parquet attachment."""
    return await _financial_query_export(request, "parquet")


@router.api_route(
    "/api/forensics/v1/financial/revisions",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"],
)
def financial_revisions_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/revisions")
async def financial_revisions(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Project cutoff-safe FIP revision records from the frozen packet assembler."""
    from engine.fundamental_forensics.query_service import (  # noqa: PLC0415
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
    )
    from engine.fundamental_forensics.revision_service import (  # noqa: PLC0415
        execute_financial_revisions,
    )

    body = await _admit_json_post_body(request)

    try:
        result = execute_financial_revisions(
            body=body,
            provider_factory=_financial_revision_provider,
        )
    except FinancialQueryAdmissionError as exc:
        raise _private_error(exc.status_code, exc.detail) from None
    except FinancialQueryUnavailableError:
        raise _private_error(503, "financial revisions temporarily unavailable") from None
    except Exception:  # noqa: BLE001
        raise _private_error(503, "financial revisions temporarily unavailable") from None

    return Response(
        content=result.body,
        media_type="application/json",
        headers={
            **_PRIVATE_HEADERS,
            "X-FIF-Response-SHA256": result.sha256,
        },
    )


@router.api_route(
    "/api/forensics/v1/financial/packet",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"],
)
def financial_packet_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/packet")
async def financial_packet(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Serve the exact canonical bytes of a validated financial_intelligence_packet.v1."""
    from engine.fundamental_forensics.packet_service import (  # noqa: PLC0415
        execute_financial_packet,
    )
    from engine.fundamental_forensics.query_service import (  # noqa: PLC0415
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
    )

    body = await _admit_json_post_body(request)

    try:
        result = execute_financial_packet(
            body=body,
            provider_factory=_financial_packet_provider,
        )
    except FinancialQueryAdmissionError as exc:
        raise _private_error(exc.status_code, exc.detail) from None
    except FinancialQueryUnavailableError:
        raise _private_error(503, "financial packet temporarily unavailable") from None
    except Exception:  # noqa: BLE001
        raise _private_error(503, "financial packet temporarily unavailable") from None

    return Response(
        content=result.body,
        media_type="application/json",
        headers={
            **_PRIVATE_HEADERS,
            "X-FIF-Response-SHA256": result.response_sha256,
        },
    )


@router.api_route(
    "/api/forensics/v1/financial/statements",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"],
)
def financial_statements_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, "method not allowed")


@router.post("/api/forensics/v1/financial/statements")
async def financial_statements(
    request: Request,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Serve filing-native as-reported primary statement trees for a named filing."""
    from engine.fundamental_forensics.query_service import (  # noqa: PLC0415
        FinancialQueryAdmissionError,
        FinancialQueryUnavailableError,
    )
    from engine.fundamental_forensics.statement_service import (  # noqa: PLC0415
        execute_financial_statements,
    )

    body = await _admit_json_post_body(request)

    try:
        result = execute_financial_statements(
            body=body,
            repo_root=REPO,
            provider_factory=_financial_statement_provider,
        )
    except FinancialQueryAdmissionError as exc:
        raise _private_error(exc.status_code, exc.detail) from None
    except FinancialQueryUnavailableError:
        raise _private_error(503, "financial statements temporarily unavailable") from None
    except Exception:  # noqa: BLE001
        raise _private_error(503, "financial statements temporarily unavailable") from None

    return Response(
        content=result.body,
        media_type="application/json",
        headers={
            **_PRIVATE_HEADERS,
            "X-FIF-Response-SHA256": result.sha256,
        },
    )


# FIF V0-a MAJOR-1 fix: these handlers answer with the private 405 before any
# real handler work runs, so the timed route does not record them at all — a
# 405 is neither a latency sample nor a client-error count on the real route
# template. (The alternative, keying the recorder by (method, path), would
# break the SLO config's path-template keys.)
_BYTE_IDENTICAL_EXPORT_PATHS = frozenset(
    {
        "/api/forensics/v1/financial/query.xlsx",
        "/api/forensics/v1/financial/query.csv",
        "/api/forensics/v1/financial/query.parquet",
    }
)

_METHOD_NOT_ALLOWED_ENDPOINTS = frozenset(
    {
        financial_query_method_not_allowed,
        financial_query_xlsx_method_not_allowed,
        financial_query_csv_method_not_allowed,
        financial_query_parquet_method_not_allowed,
        financial_revisions_method_not_allowed,
        financial_packet_method_not_allowed,
        financial_statements_method_not_allowed,
    }
)


__all__ = ["router", "require_site_full_user"]
