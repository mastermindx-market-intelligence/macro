"""Authenticated, read-only API for the Prophet Operator Lab (LAB-0 / V4-B5A).

``GET /api/prophet/lab/v1`` is the projection plane the Chairman's
operator-only LIVE|LAB mode reads: it joins canonical Radar live output
against canonical Prophet plan data and existing board-read enrichment into
six frozen "Lab boards", all in one response (``research/prophet_v4/
LAB0_B5_RECUT_OPERATOR_LAB_2026-08-18.md`` §3-§5, ``DEC:PROPHET-LAB-B5A-RECUT``).

``GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence`` is the bounded
D5 detail read: it pins one atomic B1 generation and one exact episode, builds
the canonical current ``IssuerMaster`` reader, then delegates the Earnings
projection to the pure ``engine.prophet_lab.intelligence_vector`` adapter.

This router is a transport boundary only.  Every board is computed by
``engine/prophet_lab`` (a pure projection package — see its module docstrings)
from data read off injectable filesystem roots; this file's only job is
auth, the kill switch, bounded reader composition, path resolution, and
response framing.
It runs NO detector formula, reads NO forward outcome, and writes NO store —
LAB-0 §1's "read / filter / join / decorate only" law, and the reason this
module has no ``open(..., "w")`` anywhere in it.

Auth follows the exact BioCatalyst/site-full pattern (``app/biocatalyst.py``
``require_site_full_user``): ``require_user`` (app/main.py) authenticates
first, then ``enforce_site_full(..., always=True)`` (app/paywall.py) gates on
the paid entitlement even while the global paywall switch is in observe
mode — Lab candidates must never reach an unentitled caller, let alone
anonymous HTML (LAB-0 §5).

``GET /api/hub/prophet`` is a SEPARATE, INTERNAL-ONLY route (DEC:B1-PROPHET-
PUBLIC-SPLIT): it serves the raw bytes of the same canonical local index file
``_resolve_roots()`` above resolves, for the Terminal's server-side ``/api/flow``
route to read the full Prophet plan book without falling through to the public
R2 mirror that exposure closed. It carries NO paywall/user auth — its guard is
same-box-only (loopback TCP peer AND no ``X-MM-Peer`` header; see
``_hub_prophet_authorized``), which is a materially different trust boundary
than every other route in this file and must never be relaxed to a header or
token check a caller could supply from off-box.
"""
from __future__ import annotations

from io import BytesIO
import logging
import os
from pathlib import Path
from typing import Annotated, Any, Mapping

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from engine.prophet_lab import LabRoots, build_lab_response
from engine.prophet_lab.contracts import KILL_SWITCH_ENV
from engine.prophet_lab.intelligence_vector import (
    ALL_FALSE_AUTHORITY,
    IntelligenceVectorContractError,
    build_earnings_intelligence_vector,
    load_candidate_episode_store_snapshot,
)
from lib.dataos.identity import IssuerMaster

router = APIRouter()
log = logging.getLogger("macro.prophet_lab")

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CANDIDATE_EPISODE_STORE_ROOT = _REPO_ROOT / "data" / "us_prophet_rank" / "episodes"
_SECURITY_MASTER_PATH = _REPO_ROOT / "data" / "reference" / "security_master.parquet"
#: The Data OS alias spine the native OLI read consumes.  Same committed
#: artifact the Candidate Pool intake reads; ``PROPHET_LAB_VENDOR_ALIASES_PATH``
#: overrides it for a staged/test root exactly like the security-master ladder.
_VENDOR_ALIASES_PATH = _REPO_ROOT / "data" / "reference" / "vendor_aliases.parquet"

#: INTERNAL-ONLY loopback addresses. macro-api always sits behind Caddy on
#: 127.0.0.1 (app/main.py::_brain_identity docstring), so a bare TCP-peer check
#: alone cannot distinguish an edge-proxied request from a direct same-box call —
#: BOTH show up as 127.0.0.1. See ``_hub_prophet_guard`` below.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})

_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}


def require_site_full_user(authorization: str | None = Header(default=None)) -> dict:
    """Authenticate first and enforce the paid payload even while staging.

    Exact shape of ``app/biocatalyst.py::require_site_full_user`` (lines
    270-282 at authoring) — one canonical site-full dependency pattern, not a
    second one invented for this router.
    """
    from app.main import require_user as _require_user  # noqa: PLC0415
    from app.paywall import enforce_site_full  # noqa: PLC0415

    try:
        return enforce_site_full(_require_user(authorization), always=True)
    except HTTPException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers=_merged_private_headers(exc.headers),
        ) from exc


def _merged_private_headers(existing: dict[str, str] | None) -> dict[str, str]:
    mandatory = {name.casefold() for name in _PRIVATE_HEADERS}
    merged: dict[str, str] = {}
    vary_tokens: list[str] = []
    for name, value in (existing or {}).items():
        if name.casefold() == "vary":
            vary_tokens.extend(part.strip() for part in value.split(",") if part.strip())
        elif name.casefold() not in mandatory:
            merged[name] = value
    merged.update(_PRIVATE_HEADERS)
    if vary_tokens:
        seen = {token.casefold() for token in vary_tokens}
        if "authorization" not in seen:
            vary_tokens.append("Authorization")
        merged["Vary"] = ", ".join(vary_tokens)
    return merged


def _response(payload: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=payload, status_code=status_code, headers=_PRIVATE_HEADERS)


def _load_issuer_master(path: Path) -> IssuerMaster:
    """Build the canonical identity reader from one immutable parquet byte read."""
    import pandas as pd  # noqa: PLC0415 — optional API data dependency, request-scoped

    raw = Path(path).read_bytes()
    records = pd.read_parquet(BytesIO(raw)).to_dict("records")
    return IssuerMaster.from_records(records)


def _source_integrity_failed(payload: Mapping[str, Any]) -> bool:
    receipt = payload.get("assembly_receipt")
    if not isinstance(receipt, Mapping):
        return False
    errors = receipt.get("errors")
    return isinstance(errors, list) and any(
        isinstance(error, Mapping)
        and error.get("type") == "WorkspaceChainIntegrityError"
        for error in errors
    )


# Review N4: case-insensitive OFF set; anything NOT recognized as "off" is
# treated as the switch being ACTIVE (fail TOWARD disabled — an operator
# typo or an unexpected value takes the Lab down rather than silently
# leaving it up).
_KILL_SWITCH_OFF_VALUES = frozenset({"", "0", "false", "no", "off"})


def _kill_switch_active() -> bool:
    """``PROPHET_LAB_DISABLED`` — evaluated PER REQUEST, independent of Radar's
    own ``ENTRY_RADAR_LIVE_ENABLE``/``ENTRY_RADAR_LIVE_DISABLED`` (LAB-0 §5/§7).
    """
    raw = os.environ.get(KILL_SWITCH_ENV, "").strip().casefold()
    return raw not in _KILL_SWITCH_OFF_VALUES


def _env_path(name: str, default: Path | None) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if raw:
        return Path(raw)
    return default


def _env_path_labeled(
    primary_name: str, fallback_name: str | None, default: Path | None, default_label: str,
) -> tuple[Path | None, str]:
    """Same ladder as :func:`_env_path`, but also names WHICH source won.

    Review S2 (cheap half): the health block should say which env var/path
    resolved the Radar spool root, or "unconfigured" — not just a boolean.
    """
    raw = os.environ.get(primary_name, "").strip()
    if raw:
        return Path(raw), primary_name
    if fallback_name:
        raw = os.environ.get(fallback_name, "").strip()
        if raw:
            return Path(raw), fallback_name
    return default, default_label


def _resolve_roots() -> LabRoots:
    """Production path ladder for every injectable root.

    Every root is independently overridable via env var (test/staging), and
    falls back to a repo-relative default that matches the SAME directory the
    artifact's own producer already uses — never a second, invented location:

    * ``radar_spool_dir``   -> ``$PROPHET_LAB_RADAR_SPOOL_DIR``, else
      ``$ENTRY_RADAR_SPOOL_DIR`` (the exact env var Radar's own
      ``EventSpool``/``NominationSpool`` local fallback reads —
      ``engine/entry_radar/spool.py::local_spool_dir``), else unset (no
      repo-relative default: the production spool is never inside the repo
      checkout).
    * ``radar_state_dir``   -> ``$PROPHET_LAB_RADAR_STATE_DIR``, else unset
      (the live runtime state dir is an operator-provisioned path, e.g.
      ``/var/lib/macro-live/state/entry_radar`` per
      ``engine/entry_radar/live_ledger.py``'s own module docstring; this
      router never guesses at it).
    * ``prophet_index_path`` -> ``$PROPHET_LAB_PROPHET_INDEX_PATH``, else
      ``<repo>/site/prophet/index.json`` (``scripts/build_prophet.py``'s own
      ``INDEX_PATH``).
    * ``enrichment_library_root`` -> ``$PROPHET_LAB_ENRICHMENT_ROOT``, else
      ``<repo>/site/stockdata`` (``scripts/build_prophet.py``'s own
      ``STOCKDATA_DIR`` — the exact tree ``engine.prophet_board_read.LibraryIndex``
      already reads for name/sector/spark).  Absent on a host that does not
      mount ``site/`` next to the API process; every enrichment field then
      resolves ``None`` with a health-block note rather than raising.
    * ``observation_baseline_path`` -> ``$PROPHET_LAB_OBSERVATION_BASELINE_PATH``,
      else unset.  No repo-relative default exists on purpose: an absent
      baseline is the fail-honest starting state (LAB-0 §4) — every row is
      ``retrospective_seed`` until an operator provisions this marker.
    """
    radar_spool_dir, radar_spool_source_label = _env_path_labeled(
        "PROPHET_LAB_RADAR_SPOOL_DIR", "ENTRY_RADAR_SPOOL_DIR", None, "unconfigured",
    )
    return LabRoots(
        radar_spool_dir=radar_spool_dir,
        radar_spool_source_label=radar_spool_source_label,
        radar_state_dir=_env_path("PROPHET_LAB_RADAR_STATE_DIR", None),
        prophet_index_path=_env_path(
            "PROPHET_LAB_PROPHET_INDEX_PATH", _REPO_ROOT / "site" / "prophet" / "index.json",
        ),
        enrichment_library_root=_env_path(
            "PROPHET_LAB_ENRICHMENT_ROOT", _REPO_ROOT / "site" / "stockdata",
        ),
        observation_baseline_path=_env_path("PROPHET_LAB_OBSERVATION_BASELINE_PATH", None),
    )


def _episode_intelligence_response(
    episode_id: str,
    *,
    snapshot: Any | None = None,
) -> JSONResponse:
    """Build one D5 response from one already-frozen B1 snapshot.

    A pinned research-view preflight passes its validated snapshot here so the
    expensive D5 read cannot silently switch to a second B1 generation between
    the generation check and evidence assembly. The public intelligence route
    leaves ``snapshot`` unset and therefore retains its existing current-read
    behavior.
    """
    try:
        security_master_path = _env_path(
            "PROPHET_LAB_SECURITY_MASTER_PATH", _SECURITY_MASTER_PATH,
        )
        if security_master_path is None:
            raise IntelligenceVectorContractError("D5 security master must be configured")
        if snapshot is None:
            episode_store_root = _env_path(
                "PROPHET_LAB_EPISODE_STORE_ROOT", _CANDIDATE_EPISODE_STORE_ROOT,
            )
            if episode_store_root is None:
                raise IntelligenceVectorContractError("D5 episode store must be configured")
            snapshot = load_candidate_episode_store_snapshot(episode_store_root)

        matching_episodes = [
            episode
            for episode in snapshot.generation.episodes
            if episode.get("episode_id") == episode_id
        ]
        if not matching_episodes:
            return _response({"error": "prophet_episode_not_found"}, status_code=404)
        if len(matching_episodes) != 1:
            raise IntelligenceVectorContractError("B1 generation contains duplicate episode identity")

        opened_events = [
            event
            for event in snapshot.generation.events
            if event.get("episode_id") == episode_id and event.get("event_type") == "OPENED"
        ]
        if len(opened_events) != 1:
            raise IntelligenceVectorContractError("B1 episode must have exactly one OPENED event")
        episode_known_at = opened_events[0].get("known_at")
        if not isinstance(episode_known_at, str):
            raise IntelligenceVectorContractError("B1 OPENED event known_at is invalid")

        payload = build_earnings_intelligence_vector(
            episode=matching_episodes[0],
            episode_generation_id=snapshot.generation_id,
            episode_known_at=episode_known_at,
            issuer_master=_load_issuer_master(security_master_path),
        )
        if _source_integrity_failed(payload):
            raise IntelligenceVectorContractError("D5 source integrity receipt is not admissible")
    except Exception as exc:  # noqa: BLE001 — corrupt read chains must not 500 blind
        log.warning(
            "prophet_lab: episode intelligence failed (%s: %s)",
            type(exc).__name__,
            exc,
        )
        return _response(
            {
                "error": "prophet_episode_intelligence_unavailable",
                "detail": "Episode intelligence temporarily unavailable",
            },
            status_code=503,
        )
    return _response(payload)


@router.get("/api/prophet/lab/v1")
def lab_v1(_user: dict = Depends(require_site_full_user)) -> JSONResponse:
    if _kill_switch_active():
        return _response(
            {
                "error": "prophet_lab_disabled",
                "detail": f"the Prophet Operator Lab is stood down ({KILL_SWITCH_ENV}=1)",
            },
            status_code=503,
        )
    try:
        payload = build_lab_response(_resolve_roots())
    except Exception as exc:  # noqa: BLE001 — a projection failure must not 500 blind
        log.warning("prophet_lab: projection failed (%s: %s)", type(exc).__name__, exc)
        return _response(
            {"error": "prophet_lab_unavailable", "detail": "Lab projection temporarily unavailable"},
            status_code=503,
        )
    return _response(payload)


def _no_pinned_snapshot() -> None:
    """The public D5 route never pins a B1 generation.

    The research view pins ONE generation for the whole request and passes it
    in directly, so the D5 read and the OLI read describe the same
    generation and the candidate store is read once.  This dependency keeps
    the PUBLIC route's semantics exactly as they were: it always reads the
    current store itself, and the parameter is not request-bindable, so no
    caller can inject a snapshot.
    """
    return None


@router.get("/api/prophet/lab/v1/episodes/{episode_id}/intelligence")
def episode_intelligence_v1(
    episode_id: str,
    _user: dict = Depends(require_site_full_user),
    _pinned_snapshot: Annotated[Any | None, Depends(_no_pinned_snapshot)] = None,
) -> JSONResponse:
    """Project one exact B1 episode through the read-only D5 Earnings adapter."""
    if _kill_switch_active():
        return _response(
            {
                "error": "prophet_lab_disabled",
                "detail": f"the Prophet Operator Lab is stood down ({KILL_SWITCH_ENV}=1)",
            },
            status_code=503,
        )
    return _episode_intelligence_response(episode_id, snapshot=_pinned_snapshot)


@router.get("/api/prophet/lab/v1/episodes/{episode_id}/earnings")
def episode_earnings_v1(
    episode_id: str,
    _user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    """An earnings explanation over the SAME authenticated, PIT-selected D5 read.

    No second event/workspace read, no query-selected source file or permission
    bypass. The existing kill switch, B1 identity, source checks and private errors
    are consumed unchanged. Missing optional source fields keep research visible.
    """
    native = episode_intelligence_v1(episode_id, _user=_user)
    if native.status_code != 200:
        return native
    try:
        import json
        from engine.prophet_lab.earnings_dossier import (
            load_q06_source_field, project_earnings_detail,
        )
        source_field, source_state = load_q06_source_field(_REPO_ROOT)
        payload = project_earnings_detail(
            json.loads(native.body), source_field=source_field, source_state=source_state,
        )
    except Exception as exc:  # noqa: BLE001 — never expose internal roots/source bodies
        log.warning("prophet_lab: earnings detail failed (%s)", type(exc).__name__)
        return _response(
            {"error": "prophet_earnings_detail_unavailable",
             "detail": "Earnings detail temporarily unavailable"}, status_code=503,
        )
    return _response(payload)


def _hub_prophet_authorized(request: Request) -> bool:
    """INTERNAL-ONLY guard for ``/api/hub/prophet`` (DEC:B1-PROPHET-PUBLIC-SPLIT).

    This route exists so the Terminal's server-side ``/api/flow`` route
    (``terminal/app/api/flow/route.ts:83``, which already targets
    ``${FLOW_API_BASE:-http://127.0.0.1:8000}/api/hub/prophet`` as its canonical
    backend) can read the full Prophet plan book without ever touching public R2
    — the very exposure this closure exists to shut. It is NOT a public or even
    an authenticated-user endpoint: it hands back the raw premium plan book with
    no paywall check, so it must be provably unreachable from outside the box.

    Caddy's ``reverse_proxy /api/*`` block REPLACES any inbound ``X-MM-Peer``
    with the real TCP peer on every edge-proxied request (app/deploy/Caddyfile,
    the ``header_up X-MM-Peer {remote_host}`` line under that block) — so a
    request that arrived through the public edge ALWAYS carries the header. A
    direct same-box call to uvicorn (bypassing Caddy entirely, e.g. the
    co-located Terminal process hitting 127.0.0.1:8000 directly) carries no such
    header. Because macro-api always sits behind Caddy on 127.0.0.1, the TCP
    peer alone cannot tell the two apart — both read 127.0.0.1 (same "no
    source-IP check is enough behind Caddy" reasoning as
    ``app/main.py::_brain_identity``). The header's ABSENCE, combined with a
    loopback peer, is therefore the load-bearing half of this guard.
    """
    peer = request.client.host if request.client else None
    if peer not in _LOOPBACK_HOSTS:
        return False
    return request.headers.get("x-mm-peer") is None


@router.get("/api/hub/prophet")
def hub_prophet(request: Request) -> Response:
    if not _hub_prophet_authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    index_path = _resolve_roots().prophet_index_path
    if index_path is None or not index_path.is_file():
        return JSONResponse({"error": "prophet_index_unavailable"}, status_code=503)
    try:
        raw = index_path.read_bytes()
    except OSError as exc:
        log.warning("hub_prophet: index read failed (%s: %s)", type(exc).__name__, exc)
        return JSONResponse({"error": "prophet_index_unavailable"}, status_code=503)
    return Response(
        content=raw,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


__all__ = ["router", "require_site_full_user"]


def _candidate_state_for_snapshot(snapshot: Any, episode_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project B3 from the same immutable B1 snapshot used by the research view.

    This is request-scoped composition only: it writes no state, mints no episode,
    and cannot strengthen B4 or any trading authority.
    """
    from datetime import datetime, timezone
    from engine.prophet_candidate_state import project_candidate_states
    from engine.prophet_candidate_state_sources import (
        emergence_inputs, load_radar_fact_index,
    )
    from lib.nyse_calendar import expected_last_session

    receipt = getattr(snapshot.generation, "receipt", None)
    recorded_at = receipt.get("recorded_at") if isinstance(receipt, Mapping) else None
    if not isinstance(recorded_at, str) or not recorded_at.endswith("Z"):
        raise IntelligenceVectorContractError("B1 reconciliation clock unavailable for B3")
    try:
        recorded_clock = datetime.fromisoformat(recorded_at[:-1] + "+00:00")
    except ValueError as exc:
        raise IntelligenceVectorContractError("B1 reconciliation clock invalid for B3") from exc
    if recorded_clock.tzinfo is None or recorded_clock.utcoffset() != timezone.utc.utcoffset(recorded_clock):
        raise IntelligenceVectorContractError("B1 reconciliation clock is not UTC")

    radar_path = _env_path(
        "PROPHET_LAB_ENTRY_RADAR_FORWARD_PATH",
        _REPO_ROOT / "data" / "entry_radar" / "forward.parquet",
    )
    if radar_path is None:
        raise IntelligenceVectorContractError("Entry Radar forward source path unavailable")
    radar = load_radar_fact_index(radar_path)
    emergence, degraded = emergence_inputs(snapshot, radar=radar)
    projection = project_candidate_states(
        snapshot,
        market_session=expected_last_session(recorded_clock).isoformat(),
        generated_at=recorded_at,
        emergence_by_episode=emergence,
        maturity_stage_by_episode={},
    )
    matches = [row for row in projection["rows"] if row.get("episode_id") == episode_id]
    if len(matches) != 1:
        raise IntelligenceVectorContractError("B3 projection did not resolve exact B1 episode")
    context = {
        "state": "AVAILABLE",
        "reason": None,
        "candidate_generation_id": projection["candidate_generation_id"],
        "projection_id": projection["projection_id"],
        "market_session": projection["market_session"],
        "generated_at": projection["generated_at"],
        "definition_era": projection["definition_era"],
        "emergence_degraded_reasons": list(degraded.get(episode_id, ())),
        "authority": dict(projection["authority"]),
    }
    return dict(matches[0]), context


# ---------------------------------------------------------------------------
# Native Opportunity Lifecycle (OLI) context over the ALREADY-PINNED B1 read.
#
# The research view already pins ONE B1 generation for its D5 read.  This
# block reuses that SAME pinned snapshot to serve one zero-authority OLI
# context (native B3 + Data OS store alias) as an OPTIONAL SIBLING of the
# existing research payload.  It mounts no endpoint, reads no second B1
# generation, owns no store and no evaluator: the native owners in
# ``engine.prophet_candidate_state`` and ``engine.prophet_lab.opportunity_context``
# do every binding, and B4 stays UNREAD so a missing owner stays UNKNOWN
# (``entry_open`` is None, never False).
# ---------------------------------------------------------------------------

#: Versioned wrapper for the optional research-view sibling.  The closed
#: ``prophet.lab_opportunity_context/v1`` payload is carried NESTED and is
#: never widened; this wrapper is what makes the addition explicit.
OPPORTUNITY_CONTEXT_SCHEMA = "prophet.lab_research_opportunity_context/v1"

#: Closed typed refusal vocabulary.  A refusal is a NAMED state - never an
#: empty success, never an invented negative permission verdict.
OPPORTUNITY_UNAVAILABLE_REASONS = frozenset({
    "SOURCE_UNAVAILABLE",
    "SOURCE_RETRACTED",
    "SOURCE_RECEIPT_MISMATCH",
    "AMBIGUOUS_SOURCE",
    "ALIAS_UNAVAILABLE",
    "IDENTITY_UNAVAILABLE",
    "OWNER_UNAVAILABLE",
})


class OpportunityContextUnavailable(Exception):
    """One typed refusal to serve the optional OLI research sibling.

    The reason is a member of the closed vocabulary.  It never carries a
    source body, a filesystem path or an internal exception message into a
    response.
    """

    def __init__(self, reason: str) -> None:
        if reason not in OPPORTUNITY_UNAVAILABLE_REASONS:
            raise ValueError("opportunity refusal reason is not in the closed vocabulary")
        super().__init__(reason)
        self.reason = reason


def _opportunity_unavailable(reason: str) -> dict[str, Any]:
    """One typed UNAVAILABLE opportunity wrapper."""
    return {
        "schema": OPPORTUNITY_CONTEXT_SCHEMA,
        "status": "UNAVAILABLE",
        "reason": reason,
        "context": None,
        "identity_binding": None,
        "source_receipt": None,
    }


def _opportunity_owner_inputs_available(snapshot: Any) -> bool:
    """True when a native OLI read can actually be attempted against the owner.

    The native OLI read re-validates the pinned generation against its own
    on-disk B1 bytes before it uses any fact, so it needs a REAL on-disk
    generation.  When the pinned snapshot is not one - an absent or
    fabricated owner generation - there is no native read to attempt, and the
    optional sibling is omitted entirely so the incumbent payload is returned
    unchanged.
    """
    generation = getattr(snapshot, "generation", None)
    path = getattr(generation, "path", None)
    return isinstance(path, Path) and path.is_dir()


def _load_vendor_alias_table(path: Path) -> Any:
    """Build the canonical Data OS alias reader from one immutable parquet read.

    ``lib.dataos.identity`` keeps the alias table I/O-free by design ("reading
    a file is the caller's job"), so this is the router's own reader over the
    committed ``data/reference/vendor_aliases.parquet`` - the same Data OS
    spine the Candidate Pool intake reads.  No alias table is rebuilt here.
    """
    import pandas as pd  # noqa: PLC0415 — optional API data dependency, request-scoped

    from lib.dataos.identity import VendorAliasTable  # noqa: PLC0415

    raw = Path(path).read_bytes()
    records = pd.read_parquet(BytesIO(raw)).to_dict("records")
    return VendorAliasTable.from_records(records)


def _candidate_source_session(source_event_id: object) -> Any:
    """Read the session date the owner-issued candidate source key carries.

    This mirrors the native owner's own key grammar
    (``candidate:{YYYY-MM-DD}:...``).  The native owner independently
    re-validates that key and the market session it derives, so a drift here
    is refused downstream instead of being silently served.
    """
    from datetime import date  # noqa: PLC0415

    if not isinstance(source_event_id, str):
        raise OpportunityContextUnavailable("SOURCE_UNAVAILABLE")
    parts = source_event_id.split(":")
    if len(parts) < 3 or parts[0] != "candidate":
        raise OpportunityContextUnavailable("SOURCE_UNAVAILABLE")
    try:
        return date.fromisoformat(parts[1])
    except ValueError as exc:
        raise OpportunityContextUnavailable("SOURCE_UNAVAILABLE") from exc


def _bind_candidate_source_relation(snapshot: Any, episode_id: str) -> tuple[str, str, Any]:
    """Bind one episode to its latest unretracted owner candidate relation.

    The relation is read from the native B1 ledger for THIS episode.  A display
    ticker never selects a relation; a retracted relation is never selectable;
    and two relations at the same session are an explicit refusal rather than
    a guess.  The native owner re-validates the resulting binding itself.
    """
    events = getattr(snapshot.generation, "events", ()) or ()
    retracted: set[str] = set()
    for event in events:
        if isinstance(event, Mapping) and event.get("event_type") == "RETRACTED":
            target = event.get("correction_of")
            if isinstance(target, str) and target:
                retracted.add(target)
    relations = [
        event for event in events
        if isinstance(event, Mapping)
        and event.get("source_system") == "candidate"
        and event.get("source_schema") == "us_prophet_rank.candidates/v1"
        and event.get("event_type") in {"OPENED", "OBSERVED"}
        and event.get("episode_id") == episode_id
    ]
    if not relations:
        raise OpportunityContextUnavailable("SOURCE_UNAVAILABLE")
    live = [event for event in relations if event.get("event_id") not in retracted]
    if not live:
        raise OpportunityContextUnavailable("SOURCE_RETRACTED")
    keyed: list[tuple[Any, Mapping[str, Any]]] = []
    for event in live:
        try:
            session = _candidate_source_session(event.get("source_event_id"))
        except OpportunityContextUnavailable:
            continue
        keyed.append((session, event))
    if not keyed:
        raise OpportunityContextUnavailable("SOURCE_UNAVAILABLE")
    latest = max(session for session, _ in keyed)
    at_latest = [event for session, event in keyed if session == latest]
    if len(at_latest) != 1:
        raise OpportunityContextUnavailable("AMBIGUOUS_SOURCE")
    relation = at_latest[0]
    source_event_id = relation.get("source_event_id")
    source_receipt = relation.get("source_receipt")
    if not isinstance(source_event_id, str) or not isinstance(source_receipt, str):
        raise OpportunityContextUnavailable("SOURCE_UNAVAILABLE")
    return source_event_id, source_receipt, latest


#: The native owners' own refusal phrases, mapped onto this router's closed
#: typed vocabulary.  An unmapped native refusal is OWNER_UNAVAILABLE - never
#: an empty success and never a silent skip.
_OPPORTUNITY_NATIVE_REFUSALS = (
    ("candidate source key binding is ambiguous", "AMBIGUOUS_SOURCE"),
    ("candidate source relation is retracted", "SOURCE_RETRACTED"),
    ("candidate_source_receipt does not match", "SOURCE_RECEIPT_MISMATCH"),
    ("candidate source key is suppressed", "SOURCE_UNAVAILABLE"),
    ("no OPENED/OBSERVED relation", "SOURCE_UNAVAILABLE"),
    ("unmapped in the Data OS store alias space", "ALIAS_UNAVAILABLE"),
    ("reverse alias proof does not match", "ALIAS_UNAVAILABLE"),
    ("no ACTIVE B3 episode", "IDENTITY_UNAVAILABLE"),
    ("multiple ACTIVE B3 episodes", "IDENTITY_UNAVAILABLE"),
    ("alias and native B3 candidate source relation disagree", "IDENTITY_UNAVAILABLE"),
)


def _opportunity_reason_from_native(exc: Exception) -> str:
    """Map one native owner refusal onto the closed typed vocabulary."""
    message = str(exc)
    for marker, reason in _OPPORTUNITY_NATIVE_REFUSALS:
        if marker in message:
            return reason
    return "OWNER_UNAVAILABLE"


def _opportunity_context_for_snapshot(snapshot: Any, episode_id: str) -> dict[str, Any]:
    """Serve one truthful native OLI context over an already-pinned B1 snapshot.

    The pinned snapshot is the ONLY B1 read for this request.  The candidate
    source relation is bound from the native B1 ledger for THIS episode (never
    from a display ticker), the Data OS ``store`` alias is read at the B3
    source session, and the native owner re-validates the whole binding
    (uniqueness, retraction, receipt, suppression, chronology) inside
    ``build_native_oli_read``.  B4 is deliberately NOT read: a missing owner
    stays UNKNOWN, so ``fresh_entry.entry_open`` is None rather than False.
    """
    from engine.prophet_candidate_state import CandidateStateContractError
    from engine.prophet_lab.opportunity_context import (
        OpportunityContextContractError, build_native_oli_read,
    )

    try:
        source_event_id, source_receipt, session = _bind_candidate_source_relation(
            snapshot, episode_id,
        )
        episodes = [
            episode for episode in getattr(snapshot.generation, "episodes", ()) or ()
            if isinstance(episode, Mapping) and episode.get("episode_id") == episode_id
        ]
        if len(episodes) != 1:
            raise OpportunityContextUnavailable("IDENTITY_UNAVAILABLE")
        security_id = episodes[0].get("security_id")
        if not isinstance(security_id, str) or not security_id:
            raise OpportunityContextUnavailable("IDENTITY_UNAVAILABLE")

        alias_path = _env_path("PROPHET_LAB_VENDOR_ALIASES_PATH", _VENDOR_ALIASES_PATH)
        if alias_path is None or not Path(alias_path).is_file():
            raise OpportunityContextUnavailable("OWNER_UNAVAILABLE")
        aliases = _load_vendor_alias_table(alias_path)
        display_symbol = aliases.vendor_symbol_for("store", security_id, session)
        if not isinstance(display_symbol, str) or not display_symbol:
            raise OpportunityContextUnavailable("ALIAS_UNAVAILABLE")

        read = build_native_oli_read(
            snapshot,
            candidate_source_event_id=source_event_id,
            candidate_source_receipt=source_receipt,
            aliases=aliases,
            display_symbol=display_symbol,
        )
    except OpportunityContextUnavailable as exc:
        return _opportunity_unavailable(exc.reason)
    except (OpportunityContextContractError, CandidateStateContractError) as exc:
        return _opportunity_unavailable(_opportunity_reason_from_native(exc))
    except Exception as exc:  # noqa: BLE001 - a corrupt owner read must not 500 blind
        log.warning(
            "prophet_lab opportunity context unavailable (%s)", type(exc).__name__,
        )
        return _opportunity_unavailable("OWNER_UNAVAILABLE")
    return {
        "schema": OPPORTUNITY_CONTEXT_SCHEMA,
        "status": "AVAILABLE",
        "reason": None,
        "context": dict(read.context),
        "identity_binding": dict(read.identity_binding),
        "source_receipt": read.native_b3_source_receipt,
    }


# ---------------------------------------------------------------------------
# A DEGRADED research view: the read succeeded, the earnings owner did not.
#
# The route above serves the incumbent D5 earnings evidence.  When the D5
# owner is genuinely unavailable but the NATIVE OLI context is genuinely
# available, the composed envelope below answers 200: the READ succeeded.
# It is not an empty success and it is not a restated D5 success - it carries
# NO earnings payload at all, the earnings section is ABSENT rather than
# empty, and the typed ``earnings_source_state`` names the missing earnings
# owner out loud.
#
# The envelope is a NEW closed versioned document.  It is deliberately not
# ``earnings-detail/1``: that version means "a complete D5 earnings evidence
# view".  The incumbent validator is never relaxed to accept this version and
# this version never carries a D5 earnings field.
# ---------------------------------------------------------------------------

#: The client-visible version of a DEGRADED research view.
RESEARCH_OPPORTUNITY_VIEW_VERSION = "research-opportunity-context/1"

#: The ONE named envelope state of a composed-but-degraded research view and
#: the ONE reason that can produce it.  A degraded view is never an empty
#: success and never a D5 success restated.
RESEARCH_OPPORTUNITY_PARTIAL_STATE = "PARTIAL"
RESEARCH_OPPORTUNITY_PARTIAL_REASON = "EARNINGS_UNAVAILABLE"

#: The D5 failure code that may be answered with the degraded envelope.  It
#: is the earnings owner's OWN unavailability code and nothing else: the kill
#: switch, a missing episode and a generation conflict keep their own status
#: and their own body, and no other failure code can be answered with 200.
RESEARCH_OPPORTUNITY_EARNINGS_FAILURE = "prophet_episode_intelligence_unavailable"


def _research_opportunity_presentation(language: str) -> dict[str, Any]:
    """The closed EN/ZH presentation of the degraded research view.

    These are the only words the client renders for the degraded card, so the
    client never has to invent copy - and the wording itself cannot imply a
    ranking, a forecast, a plan, a portfolio, an entry, a size or a trade.
    A fresh copy is returned every call so no response can share state.
    """
    if language == "zh":
        return {
            "title": "生命周期上下文可用；财报证据不可用",
            "subtitle": "本条记录的财报证据来源未返回结果。",
            "state_label": "财报证据",
            "state_value": "不可用",
            "phase_label": "生命周期阶段",
            "emergence_label": "涌现阶段",
            "maturity_label": "成熟阶段",
            "entry_label": "入场状态",
            "source_label": "上下文来源",
            "time_label": "截至",
            "lineage_title": "来源与绑定明细",
            "scope_notes": [
                "本视图仅显示原生生命周期上下文，不包含排名、预测、计划、组合、入场许可或交易权限。",
                "入场状态为来源方给出的原始取值；未知状态既不是可开仓，也不是不可开仓的结论。",
            ],
        }
    return {
        "title": "Lifecycle context available; earnings evidence unavailable",
        "subtitle": "The earnings evidence owner did not answer for this episode.",
        "state_label": "Earnings evidence",
        "state_value": "Unavailable",
        "phase_label": "Lifecycle phase",
        "emergence_label": "Emergence",
        "maturity_label": "Maturity",
        "entry_label": "Entry state",
        "source_label": "Context source",
        "time_label": "As of",
        "lineage_title": "Source and binding details",
        "scope_notes": [
            "This view shows native lifecycle context only. It carries no ranking, no forecast, no plan, no portfolio, no entry permission and no trade authority.",
            "The entry state is the owner's own value. An unknown entry state is not an open or a closed verdict.",
        ],
    }


def _opportunity_partial(opportunity: Mapping[str, Any]) -> dict[str, Any]:
    """One typed PARTIAL wrapper: the native context serves, the earnings do not.

    The wrapper's own shape is unchanged - only its closed status vocabulary
    gains the one named ``PARTIAL`` state, and its reason names the missing
    earnings owner instead of a source refusal.  The native closed OLI
    document is carried through untouched and never widened.
    """
    return {
        "schema": OPPORTUNITY_CONTEXT_SCHEMA,
        "status": RESEARCH_OPPORTUNITY_PARTIAL_STATE,
        "reason": RESEARCH_OPPORTUNITY_PARTIAL_REASON,
        "context": dict(opportunity["context"]),
        "identity_binding": dict(opportunity["identity_binding"]),
        "source_receipt": opportunity["source_receipt"],
    }


def _research_opportunity_context_view(
    *,
    snapshot: Any,
    episode_id: str,
    opportunity: Mapping[str, Any],
    earnings_state: Mapping[str, Any],
    language: str,
) -> dict[str, Any]:
    """Compose one DEGRADED research-view envelope for a read that succeeded.

    Every value the client will render is either an owner-issued string or a
    closed presentation string; nothing here is derived, guessed, re-read or
    re-interpreted, and no owner state is promoted - the missing B4 owner
    stays UNKNOWN, and the plan, watchlist, portfolio, evidence and forecast
    owners stay unjoined and unqualified exactly as the native composer left
    them.
    """
    rows = [
        row for row in getattr(snapshot.generation, "episodes", ()) or ()
        if isinstance(row, Mapping) and row.get("episode_id") == episode_id
    ]
    if len(rows) != 1:
        raise IntelligenceVectorContractError(
            "B1 generation does not resolve exactly one episode"
        )
    row = rows[0]
    return {
        "view_version": RESEARCH_OPPORTUNITY_VIEW_VERSION,
        "state": RESEARCH_OPPORTUNITY_PARTIAL_STATE,
        "reason": RESEARCH_OPPORTUNITY_PARTIAL_REASON,
        "language": language,
        "episode_ref": {
            "schema": row["schema"],
            "episode_id": episode_id,
            "generation_id": snapshot.generation_id,
            "identity_ref": row["company_id"],
        },
        "authority": dict(ALL_FALSE_AUTHORITY),
        "earnings_source_state": dict(earnings_state),
        "opportunity_context": _opportunity_partial(opportunity),
        "presentation": _research_opportunity_presentation(language),
    }


@router.get("/api/prophet/lab/v1/episodes/{episode_id}/research-view")
def episode_research_view_v1(
    episode_id: str,
    format: str = "json",
    language: str = "en",
    expected_generation: str | None = None,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Present the incumbent D5 read; preserve auth, kill switch and errors.

    ONE pinned B1 generation serves BOTH the D5 read and the optional native
    OLI context, so a request reads the candidate store once and the two can
    never disagree about the generation they describe.  The OLI context is an
    OPTIONAL SIBLING of the existing JSON payload: the closed
    ``prophet.lab_opportunity_context/v1`` document is carried nested inside a
    versioned wrapper and is never widened.  The sibling appears only when the
    owner inputs for a native OLI read are actually available, so the
    incumbent payload is returned byte-identical whenever the new capability
    has nothing to add.  A D5 failure keeps its own status and its own body -
    it is never restated as a D5 success - and the typed earnings source
    state says so out loud.
    """
    from engine.prophet_lab.episode_directory import valid_generation_pin

    if (format not in {"json", "html"} or language not in {"en", "zh"}
            or not valid_generation_pin(expected_generation)):
        return _response({"error": "prophet_research_view_options_invalid"}, status_code=400)
    if _kill_switch_active():
        return _response(
            {
                "error": "prophet_lab_disabled",
                "detail": f"the Prophet Operator Lab is stood down ({KILL_SWITCH_ENV}=1)",
            },
            status_code=503,
        )

    # ONE B1 read for this request.  Auth and the kill switch already ran, so
    # this is the first source I/O of the request.
    try:
        episode_store_root = _env_path(
            "PROPHET_LAB_EPISODE_STORE_ROOT", _CANDIDATE_EPISODE_STORE_ROOT,
        )
        if episode_store_root is None:
            raise IntelligenceVectorContractError("B1 read root unavailable")
        snapshot = load_candidate_episode_store_snapshot(episode_store_root)
    except Exception as exc:
        log.warning(
            "prophet_lab research view generation preflight failed (%s)",
            type(exc).__name__,
        )
        return _response(
            {
                "error": "prophet_episode_intelligence_unavailable",
                "detail": "Episode intelligence temporarily unavailable",
            },
            status_code=503,
        )
    if expected_generation is not None and snapshot.generation_id != expected_generation:
        return _response({"error": "prophet_episode_generation_changed"}, status_code=409)

    source = episode_intelligence_v1(
        episode_id, _user=_user, _pinned_snapshot=snapshot,
    )
    if source.status_code == 404:
        # The episode is not in this B1 generation: there is no identity to
        # contextualize and the incumbent error is preserved verbatim.
        return source

    import json

    # The native OLI sibling reads the SAME pinned snapshot - no second B1 fetch.
    opportunity = None
    if _opportunity_owner_inputs_available(snapshot):
        opportunity = _opportunity_context_for_snapshot(snapshot, episode_id)
    earnings_state = {
        "state": "AVAILABLE" if source.status_code == 200 else "UNAVAILABLE",
        "reason": None if source.status_code == 200 else "EARNINGS_UNAVAILABLE",
    }
    if source.status_code != 200:
        # The D5 earnings owner did not answer.  When the native OLI context
        # IS available, the composed envelope answers 200: the READ succeeded
        # and the envelope is a named, versioned, explicitly partial view.  It
        # carries no earnings payload, so it is neither an empty success nor a
        # D5 success restated - the earnings section is absent and the typed
        # earnings state names the missing owner out loud.
        #
        # Only the earnings owner's OWN unavailability code qualifies.  The
        # kill switch, a missing episode and a generation conflict keep their
        # own status and their own body, and the HTML surface is untouched.
        if (format == "json" and opportunity is not None
                and opportunity.get("status") == "AVAILABLE"):
            try:
                failure_body = json.loads(source.body)
            except ValueError:
                failure_body = {}
            if (source.status_code == 503 and isinstance(failure_body, dict)
                    and failure_body.get("error")
                    == RESEARCH_OPPORTUNITY_EARNINGS_FAILURE):
                try:
                    view = _research_opportunity_context_view(
                        snapshot=snapshot, episode_id=episode_id,
                        opportunity=opportunity, earnings_state=earnings_state,
                        language=language,
                    )
                except Exception as exc:  # noqa: BLE001 - a corrupt read must not 500 blind
                    log.warning(
                        "prophet_lab research opportunity view unavailable (%s)",
                        type(exc).__name__,
                    )
                else:
                    return _response(view)
        # D5 stays unavailable: its own status and its own body are preserved
        # and the typed earnings state names the absence.  A D5 failure is
        # never restated as a D5 success.
        try:
            body = json.loads(source.body)
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        body.setdefault("error", "prophet_episode_intelligence_unavailable")
        body["earnings_source_state"] = earnings_state
        if opportunity is not None:
            body["opportunity_context"] = opportunity
        return _response(body, status_code=source.status_code)
    try:
        from hashlib import sha256
        from base64 import b64encode
        from engine.prophet_lab.earnings_view import (
            STYLE, build_earnings_view, render_earnings_fragment,
        )
        payload = json.loads(source.body)
        if (expected_generation is not None and
                payload["episode_ref"]["generation_id"] != expected_generation):
            return _response({"error": "prophet_episode_generation_changed"}, status_code=409)
        if format == "json":
            view = build_earnings_view(payload, language=language)
            if opportunity is not None:
                view["opportunity_context"] = opportunity
                view["earnings_source_state"] = earnings_state
            if expected_generation is not None:
                try:
                    candidate_state, candidate_state_context = (
                        _candidate_state_for_snapshot(snapshot, episode_id)
                    )
                except Exception as exc:  # noqa: BLE001 - B3 is additive to valid D5
                    log.warning(
                        "prophet_lab candidate state unavailable (%s)",
                        type(exc).__name__,
                    )
                    view["candidate_state_context"] = {
                        "state": "UNAVAILABLE_DATA",
                        "reason": "B3_PROJECTION_UNAVAILABLE",
                        "candidate_generation_id": snapshot.generation_id,
                        "projection_id": None,
                        "market_session": None,
                        "generated_at": None,
                        "definition_era": None,
                        "emergence_degraded_reasons": [
                            "B3_PROJECTION_UNAVAILABLE",
                        ],
                        "authority": {
                            "can_rank": False,
                            "can_gate": False,
                            "can_size": False,
                            "can_originate_signal": False,
                            "can_change_entry_open": False,
                            "can_change_execution": False,
                        },
                    }
                else:
                    view["candidate_state"] = candidate_state
                    view["candidate_state_context"] = candidate_state_context
            return _response(view)
        style_hash = b64encode(sha256(STYLE.encode("utf-8")).digest()).decode("ascii")
        headers = dict(_PRIVATE_HEADERS)
        headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'none'; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'self'; style-src 'sha256-" + style_hash + "'"
        )
        return Response(render_earnings_fragment(payload, language=language),
                        media_type="text/html", headers=headers)
    except Exception as exc:
        log.warning("prophet_lab research view failed (%s)", type(exc).__name__)
        return _response({"error": "prophet_research_view_unavailable",
                          "detail": "Research view temporarily unavailable"}, status_code=503)


@router.get("/api/prophet/lab/v1/episodes")
def episode_directory_v1(
    q: str = "", limit: str = "25", offset: str = "0",
    expected_generation: str | None = None,
    _user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    """Discover exact B1 episode links without reading or selecting earnings."""
    from engine.prophet_lab.episode_directory import (
        build_episode_directory, parse_directory_options,
    )

    try:
        query, size, start = parse_directory_options(q, limit, offset, expected_generation)
    except ValueError:
        return _response({"error": "prophet_episode_directory_options_invalid"}, status_code=400)
    if _kill_switch_active():
        return _response({"error": "prophet_lab_disabled"}, status_code=503)
    try:
        root = _env_path("PROPHET_LAB_EPISODE_STORE_ROOT", _CANDIDATE_EPISODE_STORE_ROOT)
        if root is None:
            raise IntelligenceVectorContractError("B1 read root unavailable")
        snapshot = load_candidate_episode_store_snapshot(root)
        if expected_generation is not None and snapshot.generation_id != expected_generation:
            return _response({"error": "prophet_episode_generation_changed"}, status_code=409)
        return _response(build_episode_directory(snapshot, query=query, limit=size, offset=start))
    except Exception as exc:
        log.warning("prophet_lab episode directory failed (%s)", type(exc).__name__)
        return _response({"error": "prophet_episode_directory_unavailable"}, status_code=503)
