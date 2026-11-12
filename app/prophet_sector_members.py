"""Authenticated, read-only transport for the Prophet × Sector member join.

``GET /api/prophet/sector-members/v1`` — the first vertical slice joining ONE
captured Sector generation's full member population to the Prophet index by
US listing ticker.  Sibling of ``app/prophet_daily_brief.py``:

* Auth is the one canonical site-full dependency
  (``app.prophet_lab.require_site_full_user``); every denial inherits the
  mandatory private headers.
* The Sector generation is captured ONCE per response through the same
  primitives ``GET /api/sector-generation/population`` uses —
  ``scripts.vps_live_orchestrator.read_selected_generation`` (the verified
  snapshot facade) plus ``lib.sector_generation_contract.population_from_bundle``
  (the population projection).  Nothing here re-implements generation reading;
  the parsed member documents for group context come from the SAME captured
  bytes, never a second pointer read.
* The Prophet index is read ONCE (bytes → sha256 → strict parse).  The path is
  the Lab's existing convention (``PROPHET_LAB_PROPHET_INDEX_PATH`` override,
  default ``<repo>/site/prophet/index.json``).  A corrupt/NaN index fails
  closed to ``prophet_unavailable`` — never a partially joined book.
* Early observations are optional: one read of the B03 projection through
  ``app.prophet_observations.read_current_observations`` (request-scoped
  import, like the daily brief's owner read).  An unavailable observation
  source degrades members to their plan state; it never fails the response.
* The join itself is ``engine.prophet_sector_members`` — pure, descriptive,
  never a rank/score/gate.  Non-interference (P3): this route and its engine
  module are imported by nothing in ``scripts/build_prophet.py``'s decision
  path, and the index bytes/order are returned unchanged by every read.

Fail-closed envelope: when either side is unavailable the route still answers
200 with the envelope, the unavailable ref ``null``, the matching
``compatibility.status`` and members carrying ``prophet.state:"unavailable"``
(or an empty member list when the sector side is missing).  401/403 auth;
404 ``unknown_group``; 422 malformed query.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user

router = APIRouter()
log = logging.getLogger("macro.prophet_sector_members")

_REPO_ROOT = Path(os.environ.get("MACRO_REPO") or Path(__file__).resolve().parents[1])
_INDEX_PATH = Path(os.environ.get("PROPHET_LAB_PROPHET_INDEX_PATH")
                   or _REPO_ROOT / "site" / "prophet" / "index.json")

_GROUP_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}\Z")
_SYMBOL = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,15}\Z")
_QUERY = re.compile(r"[\w .&'\-]{1,64}\Z")
_PARAMS = frozenset({"group", "symbol", "offset", "limit", "q", "state"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --- the Sector reader: an optional owner until Sector lane 1 lands on main -----

#: The Sector programme's selected-generation reader (lane 1). Its two halves
#: are ``lib/sector_generation_contract.py`` and
#: ``scripts.vps_live_orchestrator.read_selected_generation``; until both are on
#: this tree the sector side is NOT INSTALLED, which the route answers with the
#: contract's fail-closed ``sector_unavailable`` envelope. The lookup is an
#: explicit presence check — never an ImportError caught and ignored.
_SECTOR_CONTRACT_MODULE = "lib.sector_generation_contract"
_SECTOR_READER_MODULE = "scripts.vps_live_orchestrator"
_SECTOR_CONTRACT_NAMES = ("SECTOR_GENERATION_DOMAIN", "SECTOR_GENERATION_MEMBERS",
                          "_decode_member", "population_from_bundle")


class SectorReaderNotInstalled(RuntimeError):
    """The Sector reader is not on this tree (lane 1 not landed)."""


def sector_reader():
    """``(contract module, read_selected_generation)`` or ``None`` when absent."""
    import importlib
    import importlib.util

    if importlib.util.find_spec(_SECTOR_CONTRACT_MODULE) is None:
        return None
    contract = importlib.import_module(_SECTOR_CONTRACT_MODULE)
    reader = getattr(importlib.import_module(_SECTOR_READER_MODULE),
                     "read_selected_generation", None)
    if reader is None or not all(hasattr(contract, n) for n in _SECTOR_CONTRACT_NAMES):
        return None
    return contract, reader


# --- one-shot capture helpers -----------------------------------------------------


def capture_sector_join(generations_root: Path | None) -> tuple[Any, Mapping[str, Any], Mapping[str, Any] | None, Mapping[str, Any] | None]:
    """ONE snapshot read → (population, capture facts, baskets doc, central doc).

    Raises on any capture failure; the caller decides the fail-closed answer.
    The member documents for group context are decoded from the SAME captured
    bytes the population was built from (no second pointer read, no fallback).
    """
    reader = sector_reader()
    if reader is None:
        raise SectorReaderNotInstalled("sector_reader_not_installed")
    contract, read_selected_generation = reader
    SECTOR_GENERATION_DOMAIN = contract.SECTOR_GENERATION_DOMAIN
    SECTOR_GENERATION_MEMBERS = contract.SECTOR_GENERATION_MEMBERS
    _decode_member = contract._decode_member
    population_from_bundle = contract.population_from_bundle

    snapshot = read_selected_generation(
        generations_root=Path(generations_root), domain=SECTOR_GENERATION_DOMAIN,
        members=SECTOR_GENERATION_MEMBERS)
    now = datetime.now(timezone.utc)
    receipt, population = population_from_bundle(
        member_bytes=snapshot.members,
        input_identity=snapshot.manifest.get("input_identity"),
        generation_id=snapshot.generation_id, published_at=snapshot.published_at,
        now=now)
    import hashlib
    capture = {
        "generation_id": snapshot.generation_id, "content_id": snapshot.content_id,
        "published_at": receipt.published_at, "source_session": receipt.source_session,
        "qualification": receipt.qualification, "read_captured_at": now.isoformat(),
        "member_sha256": {name: hashlib.sha256(raw).hexdigest()
                          for name, raw in sorted(snapshot.members.items())},
    }
    baskets = _decode_member(snapshot.members["basketdata/baskets.json"])
    central = _decode_member(snapshot.members["sectordata/sector_central.json"])
    return population, capture, baskets, central


def read_prophet_index() -> tuple[Mapping[str, Any] | None, str | None]:
    """One read of the index bytes: (parsed index | None, sha256 | None)."""
    def refuse(value: str):  # NaN/Infinity literals fail closed
        raise ValueError("non-finite literal")
    try:
        raw = _INDEX_PATH.read_bytes()
        document = json.loads(raw.decode("utf-8"), parse_constant=refuse)
        if not isinstance(document, dict):
            return None, None
        import hashlib
        return document, hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, UnicodeError):
        return None, None


def read_observations() -> Mapping[str, Mapping[str, Any]] | None:
    """Optional B03 early observations, digested to one block per ticker."""
    try:
        from app.prophet_observations import read_current_observations
        projection = read_current_observations()
    except Exception as exc:  # noqa: BLE001 — optional input, never fatal
        log.info("sector members: observations unavailable (%s)", type(exc).__name__)
        return None
    if not isinstance(projection, dict) or projection.get("status") == "UNAVAILABLE":
        return None
    asof = ((projection.get("clocks") or {}).get("source_session"))
    observations: dict[str, Mapping[str, Any]] = {}
    for row in projection.get("rows") or ():
        if isinstance(row, dict) and isinstance(row.get("ticker"), str):
            observations[row["ticker"].strip().upper()] = {
                "kind": "turn_watch", "asof": asof if isinstance(asof, str) else None}
    return observations


def build_join(generations_root: Path | None):
    """Capture both owners once and return the pure join (or raise)."""
    from engine.prophet_sector_members import SectorMembersJoin

    population, capture, baskets, central = capture_sector_join(generations_root)
    index, index_sha = read_prophet_index()
    return SectorMembersJoin(
        population=population, capture=capture, index=index, index_sha256=index_sha,
        baskets=baskets, central=central, observations=read_observations(),
        captured_at=_utc_now())


# --- query grammar -------------------------------------------------------------


class QueryError(ValueError):
    """Malformed query — 422 before any owner read."""


def _parse_query(request: Request) -> dict[str, Any]:
    params = request.query_params
    if any(key not in _PARAMS or len(params.getlist(key)) != 1 for key in params):
        raise QueryError("INVALID_QUERY")
    values = {key: params[key] for key in params}
    group, symbol = values.get("group"), values.get("symbol")
    if group is not None and symbol is not None:
        raise QueryError("INVALID_QUERY")
    if group is not None and not _GROUP_ID.fullmatch(group):
        raise QueryError("INVALID_QUERY")
    if symbol is not None and not _SYMBOL.fullmatch(symbol):
        raise QueryError("INVALID_QUERY")
    offset = values.get("offset", "0")
    limit = values.get("limit", "100")
    if not re.fullmatch(r"[0-9]{1,9}", offset) or not re.fullmatch(r"[0-9]{1,3}", limit):
        raise QueryError("INVALID_PAGE")
    offset_value, limit_value = int(offset), int(limit)
    if not 1 <= limit_value <= 200:
        raise QueryError("INVALID_PAGE")
    query, state = values.get("q"), values.get("state")
    if query is not None and not _QUERY.fullmatch(query.strip()):
        raise QueryError("INVALID_QUERY")
    from engine.prophet_sector_members import STATES
    if state is not None and state not in STATES:
        raise QueryError("INVALID_QUERY")
    return {"group": group, "symbol": symbol, "offset": offset_value,
            "limit": limit_value, "q": query.strip() if query else None, "state": state}


def _json(body: Mapping[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(dict(body), status_code=status_code, headers=_PRIVATE_HEADERS)


@router.get("/api/prophet/sector-members/v1")
def sector_members_v1(
    request: Request, _user: dict = Depends(require_site_full_user)
) -> JSONResponse:
    from engine import prophet_sector_members as join_engine

    try:
        query = _parse_query(request)
    except QueryError as exc:
        return _json({"error": str(exc)}, status_code=422)

    generations_root = os.environ.get("MACRO_SECTOR_GENERATIONS_ROOT")
    join = None
    if generations_root:
        try:
            join = build_join(Path(generations_root))
        except Exception as exc:  # noqa: BLE001 — fail-closed envelope, no path disclosure
            log.warning("sector members: sector capture failed (%s)", type(exc).__name__)
    else:
        log.warning("sector members: no sector generations root configured")

    if join is None:
        # Sector side unavailable: still the honest envelope, never 503.
        from engine.prophet_sector_members import SectorMembersJoin

        index, index_sha = read_prophet_index()
        join = SectorMembersJoin(population=_EmptyPopulation(), capture={},
                                 index=index, index_sha256=index_sha,
                                 observations=None, captured_at=_utc_now())

    try:
        if query["symbol"] is not None:
            return _json(join.symbol_view(query["symbol"]))
        if query["group"] is not None:
            view = join.group_view(query["group"], offset=query["offset"],
                                   limit=query["limit"], query=query["q"],
                                   state=query["state"])
            if view is None:
                # ``code`` is the key the Terminal BFF reads to tell this
                # refusal from an absent endpoint (amendment A3-2); ``error``
                # stays for every other Macro client.
                return _json({"error": "unknown_group", "code": "unknown_group"},
                             status_code=404)
            return _json(view)
        return _json(join.index_view())
    except join_engine.SectorMembersError as exc:
        return _json({"error": str(exc)}, status_code=422)
    except Exception as exc:  # noqa: BLE001 — private boundary
        log.warning("sector members: view failed (%s)", type(exc).__name__)
        return _json({"error": "SECTOR_MEMBERS_UNAVAILABLE"}, status_code=503)


class _EmptyPopulation:
    """The sector-unavailable shape: no groups, no rows, no unserved."""

    groups = ()
    rows = ()
    unserved = ()
    configured_current = None
    served = 0
    unaccounted = 0
    industry_classification = {"status": "unavailable", "reason": "not_produced"}
    sub_industry_classification = {"status": "unavailable", "reason": "not_produced"}
