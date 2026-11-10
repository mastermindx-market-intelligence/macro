"""Carry existing producer outputs into ``sector_central.json`` for the Sector generation.

The Sector generation bundle is exactly five published members. Lane 7/8 depth and the
current-basis industry map already exist as separate nightly artifacts; this module
re-expresses them (never recomputes a signal, never builds a producer) as bounded,
finite, labelled blocks under CLOSED keys of ``sector_central.json`` - the only bundle
member written AFTER the parallel DAG band barrier, so every source below has been
written when it runs. Each carried block states its own source name and as-of date.

Anything a source does not provide is simply ABSENT from the result (the generation
then reads ``unavailable/not_produced``). Nothing is invented, repaired or defaulted.
``hazard_qualification`` is deliberately never produced here: its owner
(``hazard_score.qualify_current_model``) is not on this base and is not copied.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_BLOCK_BYTES = 60 * 1024  # strictly under the reader's 64 KiB block cap
CONFLUENCE_UNIVERSES = (
    ("sp500", "marketdata/subsector_confluence.json"),
    ("nasdaq", "marketdata/subsector_confluence_nasdaq.json"),
    ("russell", "marketdata/subsector_confluence_russell.json"),
    ("china", "marketdata/subsector_confluence_china.board.json"),
)
INDUSTRY_SOURCE = "marketdata/subsector_confluence.json"
INDUSTRY_BASIS = "current_sp500_membership_not_point_in_time"
INDUSTRY_GICS_SOURCE = "stagedata/screener.json"
INDUSTRY_GICS_BASIS = "current_gics_industry_not_point_in_time"
_LIMIT_IDS = 200


def _encoded(value: Any) -> bytes | None:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        return None


def _bounded(block: Any) -> Any | None:
    """The block, or ``None`` when it is not finite JSON or exceeds the cap."""
    raw = _encoded(block)
    return block if raw is not None and len(raw) <= MAX_BLOCK_BYTES else None


def _read(site: Path, relative: str) -> Mapping[str, Any] | None:
    """Fail-soft strict read: an absent, unreadable or non-finite artifact is None."""
    try:
        def refuse(_token):
            raise ValueError("non-finite")
        document = json.loads((site / relative).read_text(encoding="utf-8"),
                              parse_constant=refuse)
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None
    return document if isinstance(document, dict) else None


def rising_priced_share(central: Mapping[str, Any]) -> dict | None:
    """R1 from the per-sector heat census the central builder already measured.

    ``rising`` = tiles whose 1M move is up (``adv``); ``priced`` = tiles that carried a
    1M move (``n_priced_1M``, unchanged tiles included); ``missing`` = tiles with no 1M
    move (``n_tiles - n_priced_1M``). Shares are ``None`` when a denominator is zero.
    """
    rows = []
    for row in central.get("sectors") or ():
        heat = row.get("heat") if isinstance(row, Mapping) else None
        if not isinstance(heat, Mapping):
            continue
        n_tiles, priced, adv = (heat.get(k) for k in ("n_tiles", "n_priced_1M", "adv"))
        if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                   for v in (n_tiles, priced, adv)) or priced > n_tiles or adv > priced:
            continue
        rows.append({
            "id": row.get("id"), "ticker": row.get("ticker"), "n_tiles": n_tiles,
            "n_priced_1M": priced, "rising_1M": adv, "missing_1M": n_tiles - priced,
            "rising_share_of_priced": round(adv / priced, 4) if priced else None,
            "priced_share_of_tiles": round(priced / n_tiles, 4) if n_tiles else None,
        })
    if not rows:
        return None
    return _bounded({
        "source": "sector_central.sectors[].heat", "as_of": central.get("as_of"),
        "window": "1M", "basis": "feed_tile_counts_not_weights",
        "denominators": {"rising_share_of_priced": "n_priced_1M",
                         "priced_share_of_tiles": "n_tiles"},
        "sectors": rows,
    })


def display_order(central: Mapping[str, Any]) -> dict | None:
    """The producer's own board order, verbatim (list order IS the producer ordinal)."""
    meta = central.get("meta") if isinstance(central.get("meta"), Mapping) else {}
    basis = meta.get("board_order") or (central.get("market") or {}).get("rotation_board_order")
    out = {}
    for name in ("sectors", "baskets"):
        ids = [r.get("id") for r in (central.get(name) or ()) if isinstance(r, Mapping)]
        if ids and all(isinstance(i, str) for i in ids):
            out[name] = ids
    if not out or not isinstance(basis, str):
        return None
    return _bounded({"source": "sector_central.board_order", "as_of": central.get("as_of"),
                     "basis": basis, "ordinal": "list_position_zero_based", **out})


def etf_flows(site: Path) -> dict | None:
    document = _read(site, "flow_desk.json")
    tile = document.get("etf_tile") if document else None
    if not isinstance(tile, Mapping):
        return None
    return _bounded({"source": "flow_desk.json#etf_tile", "as_of": tile.get("asof"),
                     "tile": dict(tile)})


def confluence(site: Path) -> dict | None:
    """Exactly four universes, or nothing: a partial set is not a four-universe read."""
    universes = {}
    for key, relative in CONFLUENCE_UNIVERSES:
        document = _read(site, relative)
        if document is None or not isinstance(document.get("coverage"), Mapping):
            return None
        lists = {}
        for name in ("entry_now", "forming", "headwind"):
            value = document.get(name)
            if not isinstance(value, list) or len(value) > _LIMIT_IDS \
                    or not all(isinstance(i, str) for i in value):
                return None
            lists[name] = value
        universes[key] = {
            "source": relative, "as_of": document.get("as_of"), "ok": document.get("ok"),
            "universe": document.get("universe"), "benchmark": document.get("benchmark"),
            "coverage": dict(document["coverage"]), **lists,
        }
    return _bounded(universes)


def bottoming_watch(site: Path) -> dict | None:
    """The act-now bottoming slice the Sector page already renders (baskets.json)."""
    baskets = _read(site, "basketdata/baskets.json")
    intel = baskets.get("theme_intel") if baskets else None
    act = intel.get("act_now") if isinstance(intel, Mapping) else None
    if not isinstance(act, Mapping) or not isinstance(act.get("bottoming_watch"), list):
        return None
    return _bounded({
        "source": "basketdata/baskets.json#theme_intel.act_now",
        "as_of": intel.get("as_of"),
        "bottoming_watch": act["bottoming_watch"],
        "dual_read_ids": act.get("dual_read_ids"),
        "recovering_ids": act.get("recovering_ids"),
        "bottoming_authority": act.get("bottoming_authority"),
    })


def theme_table(site: Path) -> dict | None:
    handoff = _read(site, "basketdata/si_handoff.json")
    context = handoff.get("theme_context") if handoff else None
    themes = context.get("themes") if isinstance(context, Mapping) else None
    if not isinstance(themes, Mapping) or not themes:
        return None
    return _bounded({"source": "basketdata/si_handoff.json#theme_context.themes",
                     "as_of": context.get("as_of"), "themes": dict(themes)})


def _basket_symbols(site: Path) -> set[str] | None:
    baskets = _read(site, "basketdata/baskets.json")
    groups = baskets.get("baskets") if baskets else None
    if not isinstance(groups, list):
        return None
    return {m["symbol"] for g in groups if isinstance(g, Mapping)
            for m in (g.get("members") or ()) if isinstance(m, Mapping)
            and isinstance(m.get("symbol"), str)}


def member_industry(site: Path) -> dict | None:
    """Current GICS industry per basket member (stage screener). NOT point-in-time.

    Source ``stagedata/screener.json`` ``rows[].industry`` (producer
    ``engine/stage_analysis.py``). Only symbols that are basket members are carried.
    """
    document = _read(site, INDUSTRY_GICS_SOURCE)
    rows = document.get("rows") if document else None
    wanted = _basket_symbols(site)
    if not isinstance(rows, list) or wanted is None:
        return None
    symbols: dict[str, str] = {}
    for row in rows:
        symbol = row.get("ticker") if isinstance(row, Mapping) else None
        industry = row.get("industry") if isinstance(row, Mapping) else None
        if symbol in wanted and isinstance(industry, str) and industry.strip():
            if symbol in symbols and symbols[symbol] != industry:
                return None  # contradictory duplicate: carried as nothing, not guessed
            symbols[symbol] = industry
    if not symbols:
        return None
    block = {"source": INDUSTRY_GICS_SOURCE, "as_of": document.get("asof"),
             "basis": INDUSTRY_GICS_BASIS, "point_in_time": False, "taxonomy": "gics_industry",
             "symbols": symbols}
    raw = _encoded(block)
    return block if raw is not None and len(raw) <= 256 * 1024 else None


def removed_members(membership: Mapping[str, Any] | None, as_of: Any) -> dict | None:
    """Members the owner's roster stamped ``removed`` on or before the session.

    Reported SEPARATELY from the served/accounted population: a removed member is not
    a current member, so it is neither listed nor "missing". ``membership`` is the
    owner's own roster document (``engine.baskets._membership()``), read by the
    builder - never at request time.
    """
    groups = membership.get("baskets") if isinstance(membership, Mapping) else None
    if not isinstance(groups, (dict, list)) or not isinstance(as_of, str):
        return None
    pairs = groups.items() if isinstance(groups, dict) else [(g.get("id"), g) for g in groups]
    removed = []
    for gid, group in pairs:
        for member in (group.get("members") if isinstance(group, Mapping) else None) or ():
            when = member.get("removed") if isinstance(member, Mapping) else None
            if isinstance(when, str) and when <= as_of and isinstance(member.get("ticker"), str):
                removed.append({"group_id": gid, "symbol": member["ticker"], "removed_on": when})
    removed.sort(key=lambda r: (r["group_id"], r["symbol"]))
    return _bounded({"source": "data/baskets/membership.json", "version": membership.get("version"),
                     "as_of": as_of, "removed": removed})


def member_sub_industry(site: Path) -> dict | None:
    """Current-basis S&P 500 sub-industry per member symbol. EXPLICITLY not point-in-time."""
    document = _read(site, INDUSTRY_SOURCE)
    subsectors = document.get("subsectors") if document else None
    if not isinstance(subsectors, list) or not subsectors:
        return None
    labels, by_symbol = {}, {}
    for row in subsectors:
        if not isinstance(row, Mapping) or not isinstance(row.get("key"), str):
            return None
        labels[row["key"]] = {"label": row.get("label"), "label_zh": row.get("label_zh"),
                              "sector": row.get("sector"), "sector_zh": row.get("sector_zh")}
        for member in row.get("members") or ():
            symbol = member.get("ticker") if isinstance(member, Mapping) else None
            if not isinstance(symbol, str) or symbol in by_symbol:
                return None  # a symbol in two sub-industries is not carried, not guessed
            by_symbol[symbol] = row["key"]
    block = {"source": INDUSTRY_SOURCE, "as_of": document.get("as_of"),
             "basis": INDUSTRY_BASIS, "point_in_time": False,
             "universe": document.get("universe"), "subsectors": labels,
             "symbols": by_symbol}
    raw = _encoded(block)
    return block if raw is not None and len(raw) <= 256 * 1024 else None


def build_carry(site: Path, central: Mapping[str, Any],
                membership: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Every block its source provides; absent keys mean ``not_produced``.

    ``membership`` is the owner's roster document (``engine.baskets._membership()``),
    supplied by the central builder; ``None`` carries no ``removed_members``.
    """
    produced = {
        "removed_members": removed_members(membership, central.get("as_of")),
        "sector_central_r1": rising_priced_share(central),
        "display_order": display_order(central),
        "etf_flows": etf_flows(site),
        "confluence": confluence(site),
        "bottoming_watch": bottoming_watch(site),
        "theme_table": theme_table(site),
        "member_industry": member_industry(site),
        "member_sub_industry": member_sub_industry(site),
    }
    return {name: block for name, block in produced.items() if block is not None}
