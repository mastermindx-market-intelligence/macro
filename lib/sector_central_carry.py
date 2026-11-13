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
import logging
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MAX_BLOCK_BYTES = 60 * 1024  # strictly under the reader's 64 KiB block cap
#: Row blocks (wire v1.1 §1) carry full group rows and members; measured on the real
#: artifacts they are 1.7-5.1x the 60 KiB cap, so they get their own measured cap.
#: The 4 MiB whole-document bound does not move.
MAX_ROW_BLOCK_BYTES = 512 * 1024
CONFLUENCE_UNIVERSES = (
    ("sp500", "marketdata/subsector_confluence.json"),
    ("nasdaq", "marketdata/subsector_confluence_nasdaq.json"),
    ("russell", "marketdata/subsector_confluence_russell.json"),
    ("china", "marketdata/subsector_confluence_china.board.json"),
)
#: The four confluence-universe row blocks (wire v1.1 §1): block name, source
#: artifact, required owner word, group arrays carried in this order. The mainland
#: China universe gets NO row block (no consumer tab mounts it; its rows carry no
#: members) - it stays in the existing ``confluence`` id-list block only.
CONFLUENCE_UNIVERSE_ROW_BLOCKS = (
    ("confluence_universe_sp500", "marketdata/subsector_confluence.json",
     "sp500_subsectors", ("subsectors", "sectors")),
    ("confluence_universe_nasdaq", "marketdata/subsector_confluence_nasdaq.json",
     "nasdaq_subsectors", ("subsectors", "sectors")),
    ("confluence_universe_russell", "marketdata/subsector_confluence_russell.json",
     "russell_subsectors", ("subsectors", "sectors")),
    ("confluence_universe_baskets", "marketdata/basket_confluence.json",
     "curated_baskets", ("baskets",)),
)
#: Closed allow-lists (wire v1.1 §2). A key present at the producer is copied
#: verbatim; a key absent at the producer stays absent; a null stays null. Nothing
#: is defaulted, renamed, recomputed or re-sorted.
_UNIVERSE_DATA_KEYS = ("ok", "universe", "weighting", "benchmark", "region", "as_of",
                      "generated_utc", "coverage", "entry_now", "forming", "headwind")
_UNIVERSE_COVERAGE_KEYS = ("n_subsectors", "n_baskets", "n_listed", "n_gateable",
                           "n_thin", "n_below_min_members", "n_unscored", "n_sectors",
                           "n_high", "n_med", "n_low_conf", "thin_share")
_UNIVERSE_ROW_KEYS = ("key", "kind", "label", "label_zh", "sector", "sector_zh",
                      "n_members", "n_priced", "reliability", "coverage_pct", "n_live",
                      "start", "as_of", "price_level", "class", "entry", "regime",
                      "members", "basket_id", "chart_key", "has_signals")
_UNIVERSE_ENTRY_KEYS = ("tier", "weight", "tier_sub", "ticks", "bars_to_cross",
                        "fresh_bars", "eligible", "buyable", "above200", "reason")
_UNIVERSE_REGIME_KEYS = ("state", "side", "label", "label_zh", "action", "action_zh",
                         "rs_60d")
_UNIVERSE_MEMBER_KEYS = ("ticker", "name_zh", "price", "ret_20d", "vs_basket",
                         "stock_tier", "stock_weight", "stock_ticks",
                         "stock_bars_to_cross", "stock_buyable", "stock_state")
#: Window labels the theme-row ``perf`` object may carry (wire v1.1 §3).
THEME_PERF_WINDOWS = ("1d", "5d", "10d", "20d", "60d", "mtd", "ytd", "full")
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


#: N-5 (review r1): the on-disk size above which a v1.1 row-block source file is
#: never parsed. The five row-block readers (the four confluence universes and
#: ``theme_rows``) refuse the file at the door and carry the small
#: ``block_too_large`` stub - undated, because the date lives inside the file we
#: refuse to open. The seven incumbent readers are untouched.
_ROW_SOURCE_MAX_BYTES = 64 * 1024 * 1024


def _read_capped(site: Path, relative: str) -> tuple[Mapping[str, Any] | None, bool]:
    """``_read`` behind the N-5 source-size guard: ``(document, over_ceiling)``.

    ``over_ceiling`` is True only when the file exists on disk larger than
    ``_ROW_SOURCE_MAX_BYTES`` - then it is not read at all and the caller
    carries its block stub. Every other failure stays the caller's ordinary
    fail-soft path (document None).
    """
    try:
        size = (site / relative).stat().st_size
    except OSError:
        size = 0
    if size > _ROW_SOURCE_MAX_BYTES:
        return None, True
    return _read(site, relative), False


def _row_source_stub(source: str) -> dict:
    """The N-5 stub: an over-ceiling source file is not parsed, so its block is
    carried as ``unavailable / block_too_large`` with no date and no rows."""
    return {"source": source, "status": "unavailable", "reason": "block_too_large"}


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


#: Trading-day length of each window label produced by ``collectors.sponsors``
#: (``FLOW_PERIODS``): 1D=1, 3D=3, 1W=5, 2W=10, 1M=21.
ETF_FLOW_WINDOWS = (("1D", 1), ("3D", 3), ("1W", 5), ("2W", 10), ("1M", 21))


def etf_flows(flows: Mapping[str, Any] | None) -> dict | None:
    """The sector-SPDR creation/redemption proxy over 1/3/5/10/21 trading days.

    ``flows`` is the output of ``collectors.sponsors.sector_flow_periods()`` - the same
    producer that renders the page's "Where sector-ETF money is flowing" board - passed
    in by the builder. The proxy is delta(shares outstanding) x NAV in $mn per fund.
    Each window sums the trailing N trading days that exist, so a window is only a
    full window once ``depth >= trading_days`` (stated per window, never assumed).
    """
    if not isinstance(flows, Mapping):
        return None
    rows, labels, depth = flows.get("rows"), flows.get("labels"), flows.get("depth")
    asof, net = flows.get("asof"), flows.get("net")
    if (not isinstance(rows, list) or not rows or not isinstance(asof, str)
            or not isinstance(depth, int) or isinstance(depth, bool)
            or labels != [label for label, _ in ETF_FLOW_WINDOWS]
            or not isinstance(net, Mapping)):
        return None
    funds = []
    for row in rows:
        # R3-N4: a non-mapping row must drop ONLY this block (return None), never raise
        # past build_carry - an exception there would strip every carried block.
        if not isinstance(row, Mapping):
            return None
        vals = row.get("vals")
        if not isinstance(row.get("ticker"), str) or not isinstance(vals, Mapping) \
                or set(vals) != set(labels):
            return None
        funds.append({"ticker": row["ticker"], "flow_mn": {k: vals[k] for k in labels}})
    return _bounded({
        "source": "collectors.sponsors.sector_flow_periods", "as_of": asof, "depth": depth,
        "unit": "usd_mn", "measure": "delta_shares_outstanding_x_nav_creation_redemption_proxy",
        "windows": [{"label": label, "trading_days": days, "full_window": depth >= days}
                    for label, days in ETF_FLOW_WINDOWS],
        "funds": funds, "net_flow_mn": {k: net.get(k) for k in labels},
    })


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
        # Dated per universe: ``as_of`` when the file has one, else its ``generated_utc``
        # (named in ``as_of_field``). An undated universe means no four-universe block.
        dated = next(((f, document[f]) for f in ("as_of", "generated_utc")
                      if isinstance(document.get(f), str) and document[f]), None)
        if dated is None:
            return None
        universes[key] = {
            "source": relative, "as_of": dated[1], "as_of_field": dated[0],
            "ok": document.get("ok"),
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


def _allowlisted(source: Mapping[str, Any], keys) -> dict:
    """The closed allow-list projection: present keys verbatim, absent keys absent."""
    return {key: source[key] for key in keys if key in source}


def _universe_row(row: Any) -> dict | None:
    """One group row under its closed allow-list, or ``None`` when it is hostile.

    ``members`` is carried only as produced: present means a list of mappings each
    with a non-empty string ``ticker``; ``entry`` / ``regime`` present means a
    mapping. There is no partial row set - the caller drops the whole block.
    """
    if not isinstance(row, Mapping):
        return None
    key = row.get("key")
    if not isinstance(key, str) or not key:
        return None
    if "members" in row:
        members = row["members"]
        if not isinstance(members, list):
            return None
        for member in members:
            if not isinstance(member, Mapping):
                return None
            ticker = member.get("ticker")
            if not isinstance(ticker, str) or not ticker:
                return None
    for nested in ("entry", "regime"):
        if nested in row and not isinstance(row[nested], Mapping):
            return None
    out = _allowlisted(row, _UNIVERSE_ROW_KEYS)
    if "entry" in out:
        out["entry"] = _allowlisted(out["entry"], _UNIVERSE_ENTRY_KEYS)
    if "regime" in out:
        out["regime"] = _allowlisted(out["regime"], _UNIVERSE_REGIME_KEYS)
    if "members" in out:
        out["members"] = [_allowlisted(m, _UNIVERSE_MEMBER_KEYS) for m in out["members"]]
    return out


def confluence_universe_rows(site: Path, relative: str, owner_word: str,
                             group_arrays) -> dict | None:
    """One confluence universe as a row block (wire v1.1 §2), or ``None``.

    The shared builder behind the four closed entries of
    ``CONFLUENCE_UNIVERSE_ROW_BLOCKS``. Each universe is independent: any failure
    here removes ONLY this block - never another universe, never the existing
    ``confluence`` id-list block. The envelope date is the existing ``confluence()``
    dating rule (the file's ``as_of`` when a non-empty string, else its
    ``generated_utc``, named in ``as_of_field``); ``data.as_of`` is the document's
    own value, verbatim - null stays null, and the envelope date is never copied
    into it. Over ``MAX_ROW_BLOCK_BYTES`` the small stub is carried, never a
    shortened row set.
    """
    document, over_ceiling = _read_capped(site, relative)
    if over_ceiling:  # N-5: never parse an over-ceiling source file
        return _row_source_stub(relative)
    if document is None or document.get("universe") != owner_word:
        return None
    if not isinstance(document.get("coverage"), Mapping):
        return None
    for name in ("entry_now", "forming", "headwind"):
        value = document.get(name)
        if not isinstance(value, list) or len(value) > _LIMIT_IDS \
                or not all(isinstance(i, str) for i in value):
            return None
    dated = next(((f, document[f]) for f in ("as_of", "generated_utc")
                  if isinstance(document.get(f), str) and document[f]), None)
    if dated is None:
        return None
    data = _allowlisted(document, _UNIVERSE_DATA_KEYS)
    data["coverage"] = _allowlisted(document["coverage"], _UNIVERSE_COVERAGE_KEYS)
    for array in group_arrays:
        rows = document.get(array)
        if not isinstance(rows, list):
            return None
        carried = []
        for row in rows:
            projected = _universe_row(row)
            if projected is None:
                return None
            carried.append(projected)
        data[array] = carried
    block = {"source": relative, "as_of": dated[1], "as_of_field": dated[0],
             "group_arrays": list(group_arrays), "data": data}
    raw = _encoded(block)
    if raw is None:
        return None  # not finite JSON: absent, exactly like every other carried block
    if len(raw) <= MAX_ROW_BLOCK_BYTES:
        return block
    return _bounded({"source": relative, "as_of": dated[1], "as_of_field": dated[0],
                     "status": "unavailable", "reason": "block_too_large"})


def _or_null(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def theme_rows(site: Path) -> dict | None:
    """The theme row array (wire v1.1 §3), or ``None``.

    One row per theme id of ``theme_context.themes`` in the mapping's own order as
    read. ``state`` is the theme's mapping verbatim. ``name`` / ``name_zh`` come from
    the ``baskets.json`` entry of that id (a string, else null; null also when
    ``baskets.json`` is unreadable or has no such entry). ``perf`` is carried only
    when ``baskets.json`` carries a non-empty string top-level ``as_of`` (that string
    is ``perf_as_of``), within the closed window set, keys ``ret`` / ``rel`` when
    present; a basket without ``perf`` has no ``perf`` key. ``chart_key`` comes from
    the ``basket_confluence.json`` basket of that id (a string, else null). No
    ``href`` is carried - the consumer composes its link from ``chart_key``.
    """
    handoff, over_ceiling = _read_capped(site, "basketdata/si_handoff.json")
    if over_ceiling:  # N-5: never parse an over-ceiling source file
        return _row_source_stub("basketdata/si_handoff.json#theme_context.themes")
    context = handoff.get("theme_context") if handoff else None
    themes = context.get("themes") if isinstance(context, Mapping) else None
    if not isinstance(themes, Mapping) or not themes:
        return None
    if not all(isinstance(state, Mapping) for state in themes.values()):
        return None
    as_of = context.get("as_of")
    if not isinstance(as_of, str) or not as_of:
        return None
    by_id: dict[str, Mapping[str, Any]] = {}
    perf_as_of = None
    baskets, over_ceiling = _read_capped(site, "basketdata/baskets.json")
    if over_ceiling:  # N-5: never parse an over-ceiling source file
        return _row_source_stub("basketdata/si_handoff.json#theme_context.themes")
    entries = baskets.get("baskets") if baskets else None
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, Mapping) and isinstance(entry.get("id"), str) \
                    and entry["id"] not in by_id:
                by_id[entry["id"]] = entry
        top = baskets.get("as_of")
        if isinstance(top, str) and top:
            perf_as_of = top
    chart_keys: dict[str, str | None] = {}
    universes, over_ceiling = _read_capped(site, "marketdata/basket_confluence.json")
    if over_ceiling:  # N-5: never parse an over-ceiling source file
        return _row_source_stub("basketdata/si_handoff.json#theme_context.themes")
    basket_rows = universes.get("baskets") if universes else None
    if isinstance(basket_rows, list):
        for row in basket_rows:
            if isinstance(row, Mapping) and isinstance(row.get("basket_id"), str) \
                    and row["basket_id"] not in chart_keys:
                chart_keys[row["basket_id"]] = _or_null(row.get("chart_key"))
    rows = []
    for theme_id, state in themes.items():
        entry = by_id.get(theme_id)
        row = {"id": theme_id,
               "name": _or_null(entry.get("name")) if entry is not None else None,
               "name_zh": _or_null(entry.get("name_zh")) if entry is not None else None,
               "chart_key": chart_keys.get(theme_id),
               "state": dict(state)}
        if perf_as_of is not None and entry is not None:
            perf = entry.get("perf")
            if isinstance(perf, Mapping):
                row["perf"] = {window: {k: perf[window][k] for k in ("ret", "rel")
                                        if k in perf[window]}
                               for window in THEME_PERF_WINDOWS
                               if window in perf and isinstance(perf[window], Mapping)}
        rows.append(row)
    block = {"source": "basketdata/si_handoff.json#theme_context.themes",
             "as_of": as_of,
             "name_source": "basketdata/baskets.json#baskets",
             "perf_source": "basketdata/baskets.json#baskets[].perf",
             "perf_as_of": perf_as_of,
             "chart_key_source": "marketdata/basket_confluence.json#baskets[].chart_key",
             "rows": rows}
    raw = _encoded(block)
    if raw is None:
        return None  # not finite JSON: absent, exactly like every other carried block
    if len(raw) <= MAX_ROW_BLOCK_BYTES:
        return block
    return _bounded({"source": "basketdata/si_handoff.json#theme_context.themes",
                     "as_of": as_of, "status": "unavailable", "reason": "block_too_large"})


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
    # R4-N1: a list-form roster with a non-mapping entry SKIPS that entry - it must
    # never raise past build_carry (an exception there strips every carried block).
    pairs = groups.items() if isinstance(groups, dict) else [
        (g.get("id"), g) for g in groups if isinstance(g, Mapping)]
    removed = []
    for gid, group in pairs:
        for member in (group.get("members") if isinstance(group, Mapping) else None) or ():
            when = member.get("removed") if isinstance(member, Mapping) else None
            if isinstance(when, str) and when <= as_of and isinstance(member.get("ticker"), str):
                removed.append({"group_id": gid, "symbol": member["ticker"], "removed_on": when})
    removed.sort(key=lambda r: (r["group_id"], r["symbol"]))
    return _bounded({"source": "data/baskets/membership.json", "version": membership.get("version"),
                     "as_of": as_of, "removed": removed})


def roster_baskets(membership: Mapping[str, Any] | None, as_of: Any) -> dict | None:
    """The owner's roster of basket ids with each basket's CURRENT members (R3-S1).

    The completeness denominator must be checkable against the owner's own roster
    (``data/baskets/membership.json``), so a basket that left the capture by ANY
    producer exit - not only the coverage refusal - can never silently leave the
    denominator. "Current" uses the owner's own rule - ``population_observation`` in
    ``lib/closes_panel.py`` (the same clock ``configured_members`` uses): the member
    key is ``ticker`` OR ``symbol``, a date field only applies when truthy, and the
    comparison is ``pd.Timestamp`` against ``pd.Timestamp(as_of)``, so an ISO stamp
    like ``"2026-11-06T00:00:00"`` is included exactly as the owner includes it.
    That owner function needs a price panel, so its rule is MIRRORED here, not
    called (R4-N2; stated per the brief) - and the mirror is differential-tested
    against the owner over shared member fixtures (N1), which is what makes
    "mirrored" a checked claim rather than a stated one. A roster date that cannot
    be parsed makes
    the WHOLE roster block absent - completeness then reads null, never a roster
    that silently included a member on an unreadable date. ``as_of`` is the owner's
    effective session, not the central date.
    """
    groups = membership.get("baskets") if isinstance(membership, Mapping) else None
    if not isinstance(groups, (dict, list)) or not isinstance(as_of, str) or not as_of:
        return None
    # R4-N1: a list-form roster with a non-mapping entry SKIPS that entry - it must
    # never raise past build_carry (an exception there strips every carried block).
    pairs = groups.items() if isinstance(groups, dict) else [
        (g.get("id"), g) for g in groups if isinstance(g, Mapping)]
    import pandas as pd  # lazy: the builder already holds pandas (engine.baskets);
    try:  # no import cost is added for callers that never cut a roster.
        when = pd.Timestamp(as_of)
    except (ValueError, TypeError, OverflowError):
        return None
    baskets: dict[str, list[str]] = {}
    for gid, group in pairs:
        if not isinstance(gid, str) or not isinstance(group, Mapping):
            return None
        current: list[str] = []
        seen: set[str] = set()
        for member in (group.get("members") or ()) if isinstance(group.get("members"), list) else ():
            if not isinstance(member, Mapping):
                continue
            ticker = member.get("ticker") or member.get("symbol")  # the owner's key rule
            if not ticker or ticker in seen:
                continue  # the owner's own de-duplication: first listing wins
            added, removed = member.get("added"), member.get("removed")
            try:
                if added and when < pd.Timestamp(added):
                    continue  # not yet a member at the effective session
                if removed and when >= pd.Timestamp(removed):
                    continue  # removed on/before the session (the removed_members cut)
            except (ValueError, TypeError, OverflowError):
                return None  # unparseable roster date: NO roster block, never a silent include
            seen.add(str(ticker))  # the owner str()s the key; so does the mirror (N1)
            current.append(str(ticker))
        baskets[gid] = current
    return _bounded({"source": "data/baskets/membership.json",
                     "version": membership.get("version"), "as_of": as_of,
                     "baskets": baskets})


PIT_STORE_SOURCE = "engine/basket_membership_pit.py:data/baskets/membership_history.parquet"
PIT_READER_SOURCE = "engine/basket_membership_pit.py:members_asof"
#: The first-known basis is a LOWER BOUND: the store begins 2026-08-13 and earlier
#: knowledge is not recorded anywhere, so the earliest date provable for a pair is
#: the earliest stored snapshot that already contains it.
FIRST_KNOWN_BASIS = "lower_bound_from_stored_snapshots"
ABSENT_PAIR_REASON = "no_stored_snapshot"


def _pit_module():
    """The PIT membership owner, imported lazily (lib must not load engine eagerly)."""
    from engine import basket_membership_pit
    return basket_membership_pit


def _pit_snapshot_dates(pit, frame) -> list[str]:
    if frame is None or frame.empty or "snapshot_date" not in frame.columns:
        return []
    return sorted({str(d) for d in frame["snapshot_date"].dropna().tolist()})


def _members_valid_at(intervals, basket_id: str, date: str) -> list[str]:
    """Members the owner's OWN intervals hold in force on ``date``: the interval
    consumer's contract (``valid_from <= date < valid_to``) over the owner's public
    ``membership_intervals_from_history`` output - never a re-derived rule."""
    return sorted({iv["ticker"] for iv in intervals
                   if iv["basket_id"] == basket_id and iv["valid_from"] <= date
                   and (iv["valid_to"] is None or iv["valid_to"] > date)})


def _pit_answers_at(pit, frame, date: str, ids) -> dict[str, tuple[Any, ...]] | None:
    """Per-group PIT answers at ``date`` from the ONE frame the builder already read.

    Each answer is ``(pit, basis, members, snapshot_date)`` and mirrors the owner's
    own dispatch in ``members_asof``: a covered frame holding ANY versioned row is
    answered - for every queried basket, exactly as the owner dispatches it - by the
    owner's interval interpretation (its PUBLIC ``membership_intervals_from_history``
    on the covered frame, the same call the owner's versioned path makes, so a MIXED
    legacy-plus-versioned covered frame resolves here exactly as the owner resolves
    it); an ALL-legacy covered frame is answered by the owner's PUBLIC per-call
    ``members_asof`` itself, called as it is (SF1) - the newest-snapshot selection
    and the active-at predicate stay the owner's, never re-implemented here, because
    an interval reading of legacy history answered differently from the owner on
    legacy-shaped stores (a revised ``added``, a future ``removed`` the query date
    passed, a dropped removal). ``None`` when ``date`` predates the store: the
    caller falls back to the owner's per-call reader for its look-ahead branch.
    Equality with the per-call reader is pinned store-free on synthetic stores (SF2)
    and against the real store (N4)."""
    if frame is None or frame.empty or "snapshot_date" not in frame.columns:
        return None
    covered = frame[frame["snapshot_date"].astype(str) <= date]
    if covered.empty:
        return None
    queried = list(ids)
    basket = covered["basket_id"].astype(str)
    if covered["record_kind"].notna().any():
        intervals = pit.membership_intervals_from_history(covered, suite=pit.SUITE_US)
        answers: dict[str, tuple[Any, ...]] = {}
        for gid in queried:
            rows = covered[basket == gid]
            if rows.empty:
                answers[gid] = (False, "unknown_basket", [], None)
                continue
            answers[gid] = (True, "pit_snapshot", _members_valid_at(intervals, gid, date),
                            str(rows["snapshot_date"].astype(str).max()))
        return answers
    owner_answers: dict[str, tuple[Any, ...]] = {}
    for gid in queried:
        owner = pit.members_asof(gid, date, suite=pit.SUITE_US)
        owner_answers[gid] = (owner.get("pit"), owner.get("basis"),
                              owner.get("members"), owner.get("snapshot_date"))
    return owner_answers


def membership_first_known(membership: Mapping[str, Any] | None, as_of: Any,
                           roster_cut: Mapping[str, list[str]] | None) -> dict | None:
    """Point-in-time ``membership_first_known`` per roster pair (Part B item 1).

    For each (group, member) the OWNER's PIT store already holds, the date of the
    EARLIEST stored snapshot in which that member is in that basket, computed from
    ONE store read plus the owner's own interpretation per stored snapshot date -
    its public interval construction for versioned history, its public per-call
    ``members_asof`` for an all-legacy covered frame (N4/SF1; each answer equals the
    owner's per-call answer, pinned store-free on synthetic stores and against the
    real store) - never the back-dated roster ``added``
    date, which the owner's interval logic already refuses to open earlier than its
    first observation. The value is a LOWER BOUND from stored snapshots (the store
    begins 2026-08-13); a pair no stored snapshot contains is ``None`` with the
    closed ``absent_pair_reason``. No roster cut, no block: the fact is scoped to
    the roster's current pairs.
    """
    if not isinstance(as_of, str) or not as_of or not isinstance(roster_cut, Mapping) \
            or not roster_cut:
        return None
    pit = _pit_module()
    suite = pit.SUITE_US
    try:
        frame = pit.read_history(suite, strict=True, include_collection_records=True)
    except pit.HistoryIntegrityError:
        return _bounded({"source": PIT_STORE_SOURCE, "as_of": as_of, "status": "unavailable",
                         "reason": "membership_unreadable",
                         "basis": FIRST_KNOWN_BASIS})
    dates = [d for d in _pit_snapshot_dates(pit, frame) if d <= as_of[:10]]
    # only snapshots at/before the capture's session may testify: a LATER snapshot
    # is future information relative to the capture (the look-ahead the owner's
    # ``pit`` flag exists to prevent), never a first-known date.
    if not dates:
        reason = ("no_stored_snapshots" if frame is None or frame.empty else
                  "no_stored_snapshots_at_or_before_as_of")
        return _bounded({"source": PIT_STORE_SOURCE, "as_of": as_of, "status": "unavailable",
                         "reason": reason, "basis": FIRST_KNOWN_BASIS})
    # N4/SF1: ONE store read (above) and the owner's own interpretation per stored
    # date, walking the dates in order and stopping per group once every roster
    # symbol is placed. Versioned dates take the owner's public interval construction
    # over that one read; ALL-LEGACY dates are answered by the owner's per-call
    # ``members_asof`` itself (SF1 - its legacy rule is never re-implemented here),
    # at the cost of that reader's own store read per still-unplaced group. Each
    # (group, date) answer equals the owner's per-call answer (pinned store-free on
    # synthetic stores and against the real store). A symbol not found by the LAST
    # stored date has no stored snapshot and reads None (``absent_pair_reason``).
    first_known: dict[str, dict[str, str | None]] = {gid: {} for gid in roster_cut}
    remaining = {gid: set(syms) for gid, syms in roster_cut.items()}
    for day in dates:
        for gid in [g for g, syms in remaining.items() if not syms]:
            del remaining[gid]  # every roster symbol of this group is already placed
        if not remaining:
            break
        answers = _pit_answers_at(pit, frame, day, remaining)
        for gid, syms in remaining.items():
            if answers is None or answers[gid][0] is not True:
                continue  # no basket-scoped observation at this date: keep looking
            present = syms & set(answers[gid][2] or ())
            for sym in present:
                first_known[gid][sym] = day
            remaining[gid] = syms - present
    for gid, syms in remaining.items():
        for sym in syms:
            first_known[gid][sym] = None
    block = {"source": PIT_STORE_SOURCE, "as_of": as_of,
             "status": "available", "basis": FIRST_KNOWN_BASIS,
             "basis_note": ("date of the earliest stored snapshot containing the "
                            "pair; the store begins {first}, earlier knowledge is "
                            "not recorded").format(first=dates[0]),
             "store_first": dates[0], "store_last": dates[-1],
             "absent_pair_reason": ABSENT_PAIR_REASON,
             "first_known": first_known}
    bounded = _bounded(block)
    if bounded is not None:
        return bounded
    if _encoded(block) is None:
        return None  # not finite JSON: absent, exactly like every other carried block
    # N2: over the cap the block is still not allowed to VANISH (the generation would
    # read not_produced and lose the fact) - a small stub served as unavailable.
    return _bounded({"source": PIT_STORE_SOURCE, "as_of": as_of, "status": "unavailable",
                     "reason": "block_too_large", "basis": FIRST_KNOWN_BASIS})


def membership_snapshots(membership: Mapping[str, Any] | None, as_of: Any,
                         roster_cut: Mapping[str, list[str]] | None) -> dict | None:
    """The stored PIT snapshot each group had at/before the effective session (item 2).

    Per group, from ONE store read plus the owner's own interpretation at the
    capture's effective session - its public interval construction for a covered
    frame with any versioned row, its public per-call ``members_asof`` for an
    all-legacy covered frame (N4/SF1; each answer equals the owner's per-call
    answer, pinned store-free on synthetic stores and against the real store): the
    stored snapshot
    date, its ``members_sha`` (the owner's own content-dedup sha, read as stamped on
    the stored rows - never recomputed), the member count, and one boolean saying
    whether that stored member set equals the carried roster's current members for
    the basket (``None`` when either side is unavailable). The member LIST is not
    carried a second time. ``pit=False`` answers carry as unavailable with the
    owner's own basis string, never guessed. A KNOWN basket with no row in its
    resolved stored snapshot (the owner's legacy path answers it pit=True with zero
    members) reads unavailable with ``basket_absent_from_snapshot`` - never
    ``available, member_count: 0`` (N8).
    """
    if not isinstance(as_of, str) or not as_of or membership is None:
        return None
    pit = _pit_module()
    suite = pit.SUITE_US
    groups = membership.get("baskets") if isinstance(membership, Mapping) else None
    if not isinstance(groups, (dict, list)):
        return None
    ids = list(groups) if isinstance(groups, dict) else [
        g.get("id") for g in groups if isinstance(g, Mapping)]
    if not ids or not all(isinstance(gid, str) and gid for gid in ids):
        return None
    sha_at: dict[tuple[str, str], str] = {}
    present_at: set[tuple[str, str]] = set()
    try:
        frame = pit.read_history(suite, strict=True, include_collection_records=True)
        if not frame.empty and {"snapshot_date", "basket_id", "members_sha"} <= set(frame.columns):
            for row in frame.to_dict("records"):
                sha = row.get("members_sha")
                key = (str(row.get("snapshot_date")), str(row.get("basket_id")))
                if isinstance(sha, str) and sha:
                    sha_at[key] = sha
                present_at.add(key)  # ANY row (member or collection marker) proves presence
    except pit.HistoryIntegrityError:
        frame = None  # members_asof answers per group with the unreadable basis itself
    # N4: one read (above), the owner's own interpretation at the session (its public
    # interval construction for versioned coverage, its public per-call reader for an
    # all-legacy covered frame - SF1; equality with the per-call reader is pinned
    # store-free on synthetic stores and against the real store); None means the
    # session predates the store, where the owner's own per-call reader below serves
    # its look-ahead branch unchanged.
    try:
        answers = _pit_answers_at(pit, frame, as_of, ids) if frame is not None else None
    except pit.HistoryIntegrityError:
        answers = None  # the per-call reader below carries the unreadable basis itself
    out: dict[str, dict[str, Any]] = {}
    for gid in ids:
        if answers is not None:
            pit_flag, basis, members, snapshot_date = answers[gid]
        else:
            answer = pit.members_asof(gid, as_of, suite=suite)
            pit_flag = answer.get("pit")
            basis = answer.get("basis")
            members = answer.get("members")
            snapshot_date = answer.get("snapshot_date")
        if pit_flag is not True:
            # the owner's own basis string (look-ahead fallback, unknown basket,
            # unreadable history) - carried as unavailable, never substituted
            out[gid] = {"status": "unavailable", "reason": _text_of(basis)}
            continue
        if not isinstance(snapshot_date, str) or not isinstance(members, list):
            out[gid] = {"status": "unavailable", "reason": "pit_answer_unreadable"}
            continue
        if (snapshot_date, gid) not in present_at:
            # N8: a KNOWN basket with no row in the resolved stored snapshot - the
            # owner answers it pit=True with zero members, which must never be served
            # as an empty basket. Presence is decided from the snapshot's own basket
            # set in the frame read above, never from the owner's free-text note.
            out[gid] = {"status": "unavailable", "reason": "basket_absent_from_snapshot"}
            continue
        equals = (set(members) == set(roster_cut.get(gid) or ())
                  if isinstance(roster_cut, Mapping) and gid in roster_cut else None)
        out[gid] = {"status": "available", "snapshot_date": snapshot_date,
                    "members_sha": sha_at.get((snapshot_date, gid)),
                    "member_count": len(members), "equals_current_roster": equals}
    block = {"source": PIT_READER_SOURCE, "as_of": as_of, "suite": suite,
             "groups": out}
    bounded = _bounded(block)
    if bounded is not None:
        return bounded
    if _encoded(block) is None:
        return None  # not finite JSON: absent, exactly like every other carried block
    # N2: over the cap the block is still not allowed to VANISH - a small stub.
    return _bounded({"source": PIT_READER_SOURCE, "as_of": as_of, "suite": suite,
                     "status": "unavailable", "reason": "block_too_large"})


def _text_of(value: Any, limit: int = 80) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= limit else None


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


def owner_effective_as_of(site: Path) -> str | None:
    """The single session the owner's basket observations were taken at, else ``None``.

    ``removed_members`` must use THIS date (the one ``configured_members`` uses), not the
    central ``as_of``, so a removal can never straddle the two clocks.
    """
    baskets = _read(site, "basketdata/baskets.json")
    groups = baskets.get("baskets") if baskets else None
    if not isinstance(groups, list):
        return None
    dates = {g["observation"].get("effective_as_of") for g in groups
             if isinstance(g, Mapping) and isinstance(g.get("observation"), Mapping)}
    return next(iter(dates)) if len(dates) == 1 and isinstance(next(iter(dates)), str) else None


#: Blocks that must carry their own string ``as_of`` (``confluence`` is dated per universe
#: instead). A block whose source has no date is NOT carried. R3-N5: the two
#: current-basis taxonomy blocks are dated blocks too - an undated classification is
#: never carried with ``as_of: null``.
_DATED_BLOCKS = ("sector_central_r1", "display_order", "etf_flows", "bottoming_watch",
                 "theme_table", "removed_members", "roster_baskets", "member_industry",
                 "member_sub_industry", "membership_first_known", "membership_snapshots",
                 "confluence_universe_sp500", "confluence_universe_nasdaq",
                 "confluence_universe_russell", "confluence_universe_baskets",
                 "theme_rows")


def build_carry(site: Path, central: Mapping[str, Any],
                membership: Mapping[str, Any] | None = None,
                flows: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Every block its source provides; absent keys mean ``not_produced``.

    ``membership`` is the owner's roster document (``engine.baskets._membership()``) and
    ``flows`` the output of ``collectors.sponsors.sector_flow_periods()``; both are
    supplied by the central builder. ``None`` carries no such block.
    """
    effective = owner_effective_as_of(site)
    roster = roster_baskets(membership, effective)
    roster_pairs = roster.get("baskets") if isinstance(roster, Mapping) else None
    # N5: ANY failure of the two PIT facts - including the engine module failing to
    # import or a non-mapping answer - degrades ONLY them (unavailable with the
    # closed ``membership_unreadable`` reason); every other carried block is still
    # served. KeyboardInterrupt/SystemExit are never swallowed.
    try:
        first_known_block = membership_first_known(membership, effective, roster_pairs)
        snapshots_block = membership_snapshots(membership, effective, roster_pairs)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:  # noqa: BLE001 — the PIT facts degrade; the carry does not
        # N2: the degradation is LOGGED with the exception type and message, so a
        # programming error is never shipped silently under the same closed reason
        # as store corruption.
        log.warning("sector_central_carry: PIT facts degraded (%s: %s)",
                    type(e).__name__, e)
        first_known_block = {"source": PIT_STORE_SOURCE, "as_of": effective,
                             "status": "unavailable", "reason": "membership_unreadable",
                             "basis": FIRST_KNOWN_BASIS}
        snapshots_block = {"source": PIT_READER_SOURCE, "as_of": effective,
                           "suite": "baskets", "status": "unavailable",
                           "reason": "membership_unreadable"}
    produced = {
        "removed_members": removed_members(membership, effective),
        "roster_baskets": roster,
        "membership_first_known": first_known_block,
        "membership_snapshots": snapshots_block,
        "sector_central_r1": rising_priced_share(central),
        "display_order": display_order(central),
        "etf_flows": etf_flows(flows),
        "confluence": confluence(site),
        "bottoming_watch": bottoming_watch(site),
        "theme_table": theme_table(site),
        "member_industry": member_industry(site),
        "member_sub_industry": member_sub_industry(site),
    }
    # The five lane-1 row blocks (wire v1.1 §1-3): the four closed universe entries
    # plus the theme row array, each independent of every other carried block.
    for name, relative, owner_word, arrays in CONFLUENCE_UNIVERSE_ROW_BLOCKS:
        produced[name] = confluence_universe_rows(site, relative, owner_word, arrays)
    produced["theme_rows"] = theme_rows(site)
    for name in _DATED_BLOCKS:
        block = produced.get(name)
        # N-5: a status stub (an over-ceiling source file) is exempt - its date
        # lives inside the file that was never parsed. It is carried by its
        # closed reason instead of being degraded to not_produced.
        if block is not None and "status" not in block \
                and not (isinstance(block.get("as_of"), str) and block["as_of"]):
            produced[name] = None  # undated: never carried with a null date
    return {name: block for name, block in produced.items() if block is not None}
