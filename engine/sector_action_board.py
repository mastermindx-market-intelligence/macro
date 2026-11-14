"""Canonical action-board value transformations; builders retain acquisition/publication."""
from __future__ import annotations
from copy import deepcopy
from datetime import date, datetime
from collections.abc import Mapping
import math
import hashlib
import calendar
import logging

import pandas as pd
from engine.i18n import t as T

log = logging.getLogger(__name__)
import json
from typing import Any

US_SECTOR_PAGE = {
    "XLK": "basket/us_sector_tech.html",
    "XLC": "basket/us_sector_comm.html",
    "XLY": "basket/us_sector_discretionary.html",
    "XLF": "basket/us_sector_financials.html",
    "XLI": "basket/us_sector_industrials.html",
    "XLB": "basket/us_sector_materials.html",
    "XLE": "basket/us_sector_energy.html",
    "XLV": "basket/us_sector_health.html",
    "XLP": "basket/us_sector_staples.html",
    "XLU": "basket/us_sector_utilities.html",
    "XLRE": "basket/us_sector_realestate.html",
}


def liquidity_from_document(document) -> str | None:
    """The existing persisted liquidity selection over captured values."""
    try:
        liq = document.get("liquidity_overlay")
    except Exception:  # noqa: BLE001 — same optional context fallback
        return None
    return liq if liq in ("expanding", "contracting", "neutral") else None


def macro_drag_from_document(document) -> float | None:
    """The persisted MRS value; this is not Central's recomputed macro context."""
    try:
        value = (document.get("macro_risk") or {}).get("score")
    except Exception:  # noqa: BLE001
        return None
    return float(value) if isinstance(value, (int, float)) else None


def factor_context_from_document(document, *, logger=None) -> dict:
    """Existing confirmer/tiebreak selection; no new factor or SUE calculation."""
    factor_z, sue_z, factor_legs, sectors = {}, {}, {}, {}
    try:
        for row in (document or {}).get("table", []):
            if not row.get("ticker"):
                continue
            composite = row.get("composite_rank")
            if composite is None:
                composite = row.get("composite")
            if composite is not None:
                factor_z[row["ticker"]] = composite
            if row.get("sue") is not None:
                sue_z[row["ticker"]] = row["sue"]
            factor_legs[row["ticker"]] = {k: row.get(k) for k in ("value", "quality", "profitability")}
            if row.get("sector"):
                sectors[row["ticker"]] = row["sector"]
    except Exception as exc:  # noqa: BLE001 — retain any preceding valid rows
        (logger or log).warning("factors.json unreadable (%s)", exc)
    return {"factor_z": factor_z, "sue_z": sue_z, "factor_legs": factor_legs, "sectors": sectors}


ACTION_LANES = (
    "buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid",
)


def basket_action_items_from_inputs(basket_payload: dict | None, allocation_payload: dict | None) -> dict:
    """Narrative-basket action items for the UNIFIED 'what to act on now' board, so the
    page acts on the narrative resolution (Memory/Storage vs Non-AI Software) and not just
    the 11 blurry GICS sectors. Sourced from the live theme-scoring recos
    (site/basketdata/baskets.json → theme_intel) and enriched with the allocation model's
    absolute-trend gate + durability + model-book weight (site/allocationdata/allocation.json).

    HONEST framing carried per item: the BUY side (enter/accumulate) is the descriptive
    leadership LENS (cross-sectional rank-IC ~0 on the clean sector backtest); the REDUCE
    side (trim/avoid) rides the backtested absolute-trend / fading-deteriorating drawdown gate
    (the one multi-decade-measured edge). `validated` flags which is which. Each item is
    badged kind='theme'. Graceful: empty buckets if the artifacts are absent.

    NEW — us_sector_* themes are separated out: they are returned in `sector_overlay` keyed
    by SPDR ticker (reverse-mapped from US_SECTOR_PAGE), not placed in narrative bucket rows.
    This prevents the board from double-listing each GICS sector (once as 🏛 cap-weighted
    cycle timing and once as 🧩 equal-weight basket).

    NEW — enter/accumulate routing now honours clean_entry from textures (or falls back to
    act_now membership). clean_entry.flag=True → buy_now (accumulate) / buy_soon (enter);
    flag absent/False → on_the_run bucket (in favour but no clean setup, don't chase)."""
    # Build reverse map: us_sector_<slug> → SPDR ticker from US_SECTOR_PAGE
    _slug_to_spdr: dict[str, str] = {}
    for _spdr, _href in US_SECTOR_PAGE.items():
        _slug = _href.replace("basket/", "").replace(".html", "")
        _slug_to_spdr[_slug] = _spdr

    buckets: dict = {"buy_now": [], "buy_soon": [], "on_the_run": [],
                     "take_profits": [], "hold": [], "avoid": [],
                     "sector_overlay": {},
                     "more": {"buy_now": 0, "buy_soon": 0, "on_the_run": 0,
                               "take_profits": 0, "hold": 0, "avoid": 0}}
    try:
        ti = (basket_payload or {}).get("theme_intel") or {}
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        return buckets
    themes = ti.get("themes") or []
    if not themes:
        return buckets

    # act_now lists provide a fallback when textures.clean_entry is absent
    act_now = ti.get("act_now") or {}
    act_now_buy_ids = {x["id"] for x in (act_now.get("buy") or [])}
    act_now_pullback_ids = {x["id"] for x in (act_now.get("add_on_pullback") or [])}

    # FIX 1 — build conflicted lookup: id -> item (carries reason_en/zh + demotion type)
    # Items in conflicted were demoted out of buy (sector-Reduce demotion or momentum cooling).
    # They must NOT route to buy_now/buy_soon; instead they go to on_the_run with conflict chips.
    _conflicted_items = act_now.get("conflicted") or []
    _conflicted_lookup: dict[str, dict] = {
        x["id"]: x for x in _conflicted_items if x.get("id")
    }

    def _conflict_chips(cf_item: dict) -> tuple[str, str, str, str]:
        """Return (chip_en, chip_zh, reason_en, reason_zh) for a conflicted act_now item."""
        if cf_item.get("cooling"):
            return (
                "momentum cooling",
                "动能降温",
                cf_item.get("reason_en") or "momentum cooling",
                cf_item.get("reason_zh") or "动能降温",
            )
        # default: sector-Reduce demotion (W2b)
        return (
            "sector says Reduce",
            "板块评级为减配",
            cf_item.get("reason_en") or "sector view is Reduce",
            cf_item.get("reason_zh") or "所属板块评级为减配",
        )

    alloc, book_wt = {}, {}
    try:
        aj = allocation_payload or {}
        alloc = {r["id"]: r for r in (aj.get("ranks") or [])}
        book_wt = {w["id"]: w.get("weight")
                   for w in ((aj.get("allocation") or {}).get("weights") or [])}
    except Exception as e:  # noqa: BLE001 — enrichment only
        pass

    # Lane mapping for non-buy recos — same as before
    reduce_bucket = {"hold": "hold", "trim": "take_profits", "avoid": "avoid"}

    for th in themes:
        tid = th.get("id") or ""
        reco = (th.get("reco") or "").lower()
        a = alloc.get(tid) or {}
        gate = a.get("gate") or {}
        tex = th.get("textures") or {}
        ce = tex.get("clean_entry") or {}
        # clean_entry: prefer textures.clean_entry.flag; fallback to act_now membership
        if ce:
            ce_flag = bool(ce.get("flag"))
            ce_quality = ce.get("quality")
        else:
            ce_flag = tid in act_now_buy_ids
            ce_quality = None

        _perf = th.get("perf") or {}
        _perf_20d = _perf.get("20d") or {}
        _brd = th.get("breadth") or {}
        _leader = th.get("leadership") or {}
        _top3 = [t.get("ticker") for t in (_leader.get("top") or [])[:3] if t.get("ticker")]
        _rr = (th.get("textures") or {}).get("rollover_risk") or {}
        _fd = th.get("flip_distance") or {}
        base_item = {
            "kind": "theme",
            "reco": reco,                            # raw reco; needed by action_board() reduce-side override
            "ticker": tid, "slug": tid,
            "href": "basket/" + tid + ".html",
            "name": th.get("name"), "name_zh": th.get("name_zh"),
            "label": th.get("reco_en") or reco.upper(),
            "label_zh": th.get("reco_zh") or reco,
            "score": th.get("score"),
            "alloc_rank": a.get("rank"),
            "above_trend": bool(gate.get("above_200dma")) if gate else None,
            "eligible": a.get("eligible"),
            "durability": (a.get("durability") or {}).get("bar"),
            "book_wt": book_wt.get(tid),
            "validated": reco in ("trim", "avoid"),   # the trend-gate / drawdown risk side
            "signal_grade": (th.get("signal_strength") or {}).get("grade"),
            "clean_entry": ce_flag,
            "clean_quality": ce_quality,
            # popover enrichment fields
            "perf_20d_rel": _perf_20d.get("rel"),
            "breadth_pct50": _brd.get("pct50"),
            "top_members": _top3,
            "rollover_band": _rr.get("band"),
            "rollover_band_zh": _rr.get("band_zh"),
            "reco_why_en": th.get("reco_why_en"),
            "reco_why_zh": th.get("reco_why_zh"),
            "rs_pctile": th.get("rs_pctile"),
            "flip_distance": _fd.get("route_b_pp"),
        }

        # --- us_sector_* go to sector_overlay, NOT into narrative rows ---
        if tid.startswith("us_sector_"):
            spdr = _slug_to_spdr.get(tid)
            if not spdr:
                continue   # unknown slug — skip gracefully
            # Determine which lane this reco WOULD have mapped to (used for ew_lane)
            if reco in ("accumulate", "enter"):
                ew_lane = "buy_now" if (reco == "accumulate" and ce_flag) else (
                          "buy_soon" if (reco == "enter" and ce_flag) else "on_the_run")
            else:
                ew_lane = reduce_bucket.get(reco, "avoid")
            sector_item = dict(base_item, ew_lane=ew_lane)
            # FIX 1 — carry conflict chips onto sector_overlay entry when conflicted
            _cf = _conflicted_lookup.get(tid)
            if _cf:
                _ce_n, _ce_zh, _cr_en, _cr_zh = _conflict_chips(_cf)
                sector_item["conflict_chip_en"] = _ce_n
                sector_item["conflict_chip_zh"] = _ce_zh
                sector_item["conflict_reason_en"] = _cr_en
                sector_item["conflict_reason_zh"] = _cr_zh
            buckets["sector_overlay"][spdr] = sector_item
            continue

        # --- Narrative (non-us_sector_*) themes: route by reco + clean_entry ---
        if reco in ("accumulate", "enter"):
            # FIX 1 — check conflicted BEFORE routing to buy lanes
            _cf = _conflicted_lookup.get(tid)
            if _cf:
                # Demoted theme: goes to on_the_run regardless of ce_flag
                bkt = "on_the_run"
                _ce_n, _ce_zh, _cr_en, _cr_zh = _conflict_chips(_cf)
                base_item["conflict_chip_en"] = _ce_n
                base_item["conflict_chip_zh"] = _ce_zh
                base_item["conflict_reason_en"] = _cr_en
                base_item["conflict_reason_zh"] = _cr_zh
                # Also set run_reason so the existing ⟳ glyph fires
                base_item["run_reason_en"] = _cr_en
                base_item["run_reason_zh"] = _cr_zh
            elif reco == "accumulate" and ce_flag:
                bkt = "buy_now"
            elif reco == "enter" and ce_flag:
                bkt = "buy_soon"
            else:
                # In favour but no clean-entry setup — don't chase, add on pullback
                bkt = "on_the_run"
                quality_pct = (
                    round(ce_quality * 100) if ce_quality is not None else None
                )
                # Carry a short reason for the template to surface
                base_item["run_reason_en"] = (
                    "In favour but no clean-entry setup — add on pullback"
                    + (f"; entry quality {quality_pct}%" if quality_pct is not None else "")
                )
                base_item["run_reason_zh"] = (
                    "顺势但无干净入场机会 — 等回调加仓"
                    + (f"；入场质量 {quality_pct}%" if quality_pct is not None else "")
                )
        else:
            bkt = reduce_bucket.get(reco)
            if not bkt:
                continue

        buckets[bkt].append(base_item)

    buckets["buy_now"].sort(key=lambda x: -(x.get("score") or 0))   # leaders first
    buckets["buy_soon"].sort(key=lambda x: -(x.get("score") or 0))
    buckets["on_the_run"].sort(key=lambda x: -(x.get("score") or 0))
    buckets["take_profits"].sort(key=lambda x: (x.get("score") or 0))  # weakest first
    buckets["avoid"].sort(key=lambda x: (x.get("score") or 0))
    # FIX 3 — raise per-bucket cap 8 → 12; record more_<bucket> counts for disclosure
    _CAP = 12
    more: dict[str, int] = {}
    for k in ("buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid"):
        full = buckets[k]
        more[k] = max(0, len(full) - _CAP)
        buckets[k] = full[:_CAP]
    buckets["more"] = more
    return buckets


def _action_board_stat_chip(lane: str, e: dict, item: dict) -> None:
    """Attach stat_en / stat_zh / chip_en / chip_zh / chip_tone to *item* in-place.

    Ruling: BOTTOMING·WAIT belongs in Almost ready — 2026-07-10 us_stocks scorecard
    adjudication. Conservative de-escalation-safe defaults throughout.
    All strings are QUALIFIER-FIRST so truncation never eats the honest half (<= 30 EN).
    """
    tag = e.get("tag", "")
    age_short = item.get("age_short") or ""
    age_short_zh = item.get("age_short_zh") or ""
    days = e.get("days_hi")
    gate_override = item.get("gate_override", False)
    urgency = e.get("urgency", "")

    # stat_en / stat_zh
    if lane == "buy_now":
        stat_en = f"clean entry · {age_short}" if age_short else "clean entry"
        stat_zh = f"入场干净 · {age_short_zh}" if age_short_zh else "入场干净"
    elif lane == "buy_soon":
        # lane_hint=buy_soon items are WAIT demotions (BOTTOMING·EXTENDED or UNCONFIRMED)
        if tag in ("BOTTOMING · EXTENDED — WAIT",):
            stat_en = "extended — wait"
            stat_zh = "已过热 — 等待"
        elif tag == "BOTTOMING · UNCONFIRMED — WAIT":
            stat_en = "unconfirmed — wait"
            stat_zh = "未确认 — 等待"
        elif days is not None:
            stat_en = f"trigger ~{days}d"
            stat_zh = f"触发约{days}日"
        else:
            stat_en = "unconfirmed — wait"
            stat_zh = "未确认 — 等待"
    elif lane == "on_the_run":
        stat_en = "extended · wait for pullback"
        stat_zh = "已延伸 · 等回调"
    elif lane == "take_profits":
        if gate_override:
            stat_en = "backtested gate: trim"
            stat_zh = "回测门槛：减仓"
        elif urgency == "exit":
            stat_en = "momentum rolled over"
            stat_zh = "动量掉头"
        else:
            stat_en = f"late cycle · {age_short}" if age_short else "late cycle"
            stat_zh = f"周期晚期 · {age_short_zh}" if age_short_zh else "周期晚期"
    elif lane == "hold":
        stat_en = "uptrend intact"
        stat_zh = "趋势完好"
    else:  # avoid
        if tag == "WAIT":
            stat_en = "wait for a new setup"
            stat_zh = "等待新形态"
        else:
            stat_en = "downtrend"
            stat_zh = "下跌趋势"

    item["stat_en"] = stat_en
    item["stat_zh"] = stat_zh

    # chip_en / chip_zh / chip_tone (at most one chip; gate ✓ added by template from gate_override)
    # Priority: WAIT demotions first, then HALF SIZE, then lane-specific, then days, then empty.
    if lane == "buy_soon" and tag in ("BOTTOMING · EXTENDED — WAIT",
                                      "BOTTOMING · UNCONFIRMED — WAIT"):
        chip_en, chip_zh, chip_tone = "WAIT", "等待", "warn"
    elif tag == "HALF SIZE":
        chip_en, chip_zh, chip_tone = "HALF SIZE", "半仓", "pos"
    elif lane == "hold":
        chip_en, chip_zh, chip_tone = "HOLD", "持有", "muted"
    elif lane == "avoid":
        if tag == "WAIT":
            chip_en, chip_zh, chip_tone = "WAIT", "等待", "warn"
        else:
            chip_en, chip_zh, chip_tone = "AVOID", "回避", "neg"
    elif lane == "buy_soon" and days is not None:
        chip_en, chip_zh, chip_tone = f"~{days}d", f"约{days}日", "info"
    else:
        chip_en, chip_zh, chip_tone = "", "", ""

    item["chip_en"] = chip_en
    item["chip_zh"] = chip_zh
    item["chip_tone"] = chip_tone

    # text_zh (additive alongside existing text)
    item["text_zh"] = e.get("text_zh", "")


def action_board(sector_timing: dict, notable: list[dict],
                 basket_items: dict | None = None,
                 sector_setup_lookup: dict | None = None) -> dict:
    """Bucket sector + narrative-basket + standout-stock cycle signals into an at-a-glance
    'what to act on now' board. Sectors and baskets are UNIFIED (each item carries
    kind='sector'|'theme' + an href) so the board acts on narrative resolution, not just the
    11 GICS sectors.

    Urgency routing (ratified — 2026-07-10 us_stocks scorecard adjudication):
      now → buy_now; imminent/soon → buy_soon; hold → hold; exit → take_profits;
      caution: lane_hint key consulted FIRST (engine/cycles.py sets it on every caution entry);
        lane_hint wins when it names a valid lane; fallback (no hint) by exact tag:
          "DON'T CHASE"            → on_the_run   (uptrend intact, extended)
          "UNCONFIRMED — HIGH RISK" → avoid        (bear-trend bounce)
          "TAKE PROFITS"            → take_profits
          unknown/missing           → hold         (conservative de-escalation-safe default)
      all other urgency values → avoid.

    EW overlay attach: if sector_overlay carries the SPDR ticker, attach item["ew"] + ew_lane.
    Reduce-side override (the one backtested drawdown-control edge): if overlay reco is
    trim/avoid and the cycle lane is buy_now/buy_soon/on_the_run/hold, the row is MOVED to
    take_profits or avoid respectively (gate_override=True so the template can badge ✓).

    sector_setup_lookup: optional dict keyed by SPDR ticker → sector_setup row dict.
    When provided, per-ticker setup fields (rs_60d, above200, above50, rsi_3d, stoch_3d,
    rate_str, rate_pos, season_str, season_tip) are merged onto each sector action_board item
    for the conditions popover. Additive; missing keys silently skipped."""
    from engine.playbook import SECTOR_NAMES
    buy_now, buy_soon, on_the_run, take_profits, hold, avoid = [], [], [], [], [], []

    # sector_overlay comes from basket_action_items(); keyed by SPDR ticker
    sector_overlay = (basket_items or {}).get("sector_overlay") or {}
    _setup_lk = sector_setup_lookup or {}

    _BUY_LANES = {"buy_now", "buy_soon", "on_the_run", "hold"}
    _VALID_LANES = {"buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid"}

    for fund, tm in sector_timing.items():
        e = tm.get("entry") or {}
        tag = e.get("tag", "")
        item = {"ticker": fund, "name": SECTOR_NAMES.get(fund, fund),
                "kind": "sector", "href": US_SECTOR_PAGE.get(fund, "sectors/" + fund + ".html"),
                "label": tm["label"], "tag": tag,
                "text": e.get("text", ""), "days": e.get("days_hi"),
                "age_short": tm.get("age_short"), "age_short_zh": tm.get("age_short_zh"),
                "eq_badge": tm.get("eq_badge"), "eq_dir": tm.get("eq_dir"),
                "eq_tip": tm.get("eq_tip"), "eq_tip_zh": tm.get("eq_tip_zh"), "style": tm.get("state_style"),
                # cycle position + holdings context for conditions popover
                "dc_day": tm.get("dc_day"),
                "buy_zone": tm.get("buy_zone"), "n_holdings": tm.get("n_holdings")}
        # Merge sector_setup confluence fields (rs_60d, oscillators, base rates, seasonality)
        _su = _setup_lk.get(fund)
        if _su:
            item["rs_60d"] = _su.get("rs_60d")
            item["above200"] = _su.get("above200")
            item["above50"] = _su.get("above50")
            item["rsi_3d"] = _su.get("rsi_3d")
            item["stoch_3d"] = _su.get("stoch_3d")
            item["rate_str"] = _su.get("rate_str")
            item["rate_pos"] = _su.get("rate_pos")
            item["season_str"] = _su.get("season_str")
            item["season_tip"] = _su.get("season_tip")
        u = e.get("urgency")
        # Determine the cycle-timing lane.
        # caution: lane_hint FIRST; fallback to exact-tag switch; unknown → hold (safe default).
        if u == "now":
            cycle_lane = "buy_now"
        elif u in ("imminent", "soon"):
            cycle_lane = "buy_soon"
        elif u == "hold":
            cycle_lane = "hold"
        elif u == "exit":
            cycle_lane = "take_profits"
        elif u == "caution":
            hint = e.get("lane_hint", "")
            if hint in _VALID_LANES:
                cycle_lane = hint
            elif tag == "DON'T CHASE":
                cycle_lane = "on_the_run"
            elif tag == "UNCONFIRMED — HIGH RISK":
                cycle_lane = "avoid"
            elif tag == "TAKE PROFITS":
                cycle_lane = "take_profits"
            else:
                cycle_lane = "hold"   # conservative de-escalation-safe default
        else:
            cycle_lane = "avoid"

        # Attach EW overlay when available
        ov = sector_overlay.get(fund)
        if ov:
            item["ew"] = ov
            item["ew_lane"] = ov.get("ew_lane")
            # W2b/W4 demotion receipts travel on the overlay item — lift them to
            # the rendered sector row so the sector-Reduce conflict is disclosed
            # on the board itself, not buried inside the ew dict (MLC-R7).
            for _ck in ("conflict_chip_en", "conflict_chip_zh",
                        "conflict_reason_en", "conflict_reason_zh"):
                if ov.get(_ck) and not item.get(_ck):
                    item[_ck] = ov[_ck]

        # Reduce-side override: the backtested drawdown-control edge may not be hidden
        # behind a constructive cycle read.
        final_lane = cycle_lane
        if ov:
            ov_reco = (ov.get("reco") or "").lower()
            if ov_reco == "trim" and cycle_lane in _BUY_LANES:
                final_lane = "take_profits"
                item["gate_override"] = True
            elif ov_reco == "avoid" and cycle_lane in _BUY_LANES:
                final_lane = "avoid"
                item["gate_override"] = True

        # FIX 2 — EW-vs-cycle disclosure chip (when gate_override did NOT fire).
        # Fires when EW lane direction and final cycle lane direction disagree
        # (buy-side vs reduce-side in either direction) and it's a pure disclosure
        # — the gate_override path already handles the reduce override.
        if ov and not item.get("gate_override"):
            _ew_ln = ov.get("ew_lane") or ""
            _BUY_SIDE = {"buy_now", "buy_soon", "on_the_run"}
            _RED_SIDE = {"take_profits", "avoid"}
            _cycle_buy = final_lane in _BUY_SIDE
            _cycle_red = final_lane in _RED_SIDE
            _ew_buy = _ew_ln in _BUY_SIDE
            _ew_red = _ew_ln in _RED_SIDE
            if (_cycle_buy and _ew_red) or (_cycle_red and _ew_buy):
                # Use the reco label already on the EW overlay item for EW side
                _ew_label_en = (ov.get("label") or _ew_ln.replace("_", " ")).upper()
                _ew_label_zh = ov.get("label_zh") or _ew_label_en
                # Cycle label: EN from the item; ZH via STATE_DISPLAY on the
                # ladder state (sector items carry no label_zh — same idiom as
                # the setup two_reads chip below; fail-open to EN).
                from engine.cycles import STATE_DISPLAY as _EWSD
                _cyc_label_en = (item.get("label")
                                 or final_lane.replace("_", " ")).upper()
                _cyc_label_zh = _EWSD.get(tm.get("state", ""), {}).get(
                    "label_zh") or _cyc_label_en
                item["ew_two_reads"] = {
                    "cycle_label_en": _cyc_label_en,
                    "cycle_label_zh": _cyc_label_zh,
                    "ew_label_en": _ew_label_en,
                    "ew_label_zh": _ew_label_zh,
                }

        # Attach stat/chip display fields and text_zh per contract
        _action_board_stat_chip(final_lane, e, item)

        if final_lane == "buy_now":
            buy_now.append(item)
        elif final_lane == "buy_soon":
            buy_soon.append(item)
        elif final_lane == "on_the_run":
            on_the_run.append(item)
        elif final_lane == "take_profits":
            take_profits.append(item)
        elif final_lane == "hold":
            hold.append(item)
        else:
            avoid.append(item)

    buy_soon.sort(key=lambda x: (x["days"] if x["days"] is not None else 99))
    # ----- standout-stock ranking ------------------------------------------------
    # Within each urgency tier, rank by the alpha-aware SETUP score (selection =
    # sector-neutral residual momentum × timing = the calibrated cycle entry +
    # reversal overlay; see engine/setups.py). This upgrades the old |eq_score|-only
    # order so a sector-neutral LEADER on a fresh, constructive entry outranks an
    # equally-timed laggard. setup_score is always set (timing-only fallback when a
    # name has no residual), so every card ranks on the same scale. Then prefer
    # fresher signals. A soft conviction floor still drops 'minimal' (|eq|<15) timing
    # setups, but only while enough genuine ones remain so the strip never starves.
    order = {"now": 0, "imminent": 1, "exit": 2}

    def _conv(n):
        return abs(n.get("eq_score") or 0)

    def _decis(n):
        # The urgency TIER is the cycle-timing read (risk placement). WITHIN a tier we
        # order buys by the validated selection leg — sector-neutral momentum α — not
        # the blended setup score: Phase-0 (reports/setup-score-phase0.md) showed the
        # timing blend does NOT improve forward-return ranking (it dilutes α). Sells
        # keep the cycle sell-conviction (α is not a sell signal). asc sort throughout.
        if n.get("urgency") == "exit":
            return n.get("eq_score") or 0               # most-negative (strongest sell) first
        az = n.get("alpha_z")
        if az is not None:
            return -az                                  # highest α (strongest leader) first
        return -(n.get("eq_score") or 0)                # no α: fall back to cycle conviction

    def _rank(n):
        # α (selection) leads within the cycle tier; the factor composite breaks
        # near-ties only (a crowded/decayed leg — settle ties, never drive the order).
        return (order.get(n["urgency"], 9), _decis(n),
                -(n.get("factor_z") or 0.0),
                n.get("age_days") if n.get("age_days") is not None else 999,
                n["days"] if n.get("days") is not None else 99)

    from engine.setups import norm_company

    # A soft per-sector cap keeps one hot sector (e.g. all of XLK in a tech rip) from
    # crowding out the board — the best names per sector fill first, then any spare
    # slots backfill from the overflow (already in rank order). Dual-class listings
    # (GOOG + GOOGL) are collapsed to the best-ranked variant.
    # CAP generous so the standout strip's "show more" can reveal a deep bench; the
    # per-sector cap still shapes the diverse top-of-list that's visible by default.
    CAP, FLOOR, PER_SECTOR = 60, 15, 5
    strong = [n for n in notable if _conv(n) >= FLOOR]
    pool = strong if len(strong) >= 6 else notable
    seen, seen_name, by_sec, picked, overflow = set(), set(), {}, [], []
    for n in sorted(pool, key=_rank):
        if n["ticker"] in seen:
            continue
        nm = norm_company(n.get("name"))
        if nm and nm in seen_name:                      # dual-class / multi-listing dupe
            continue
        seen.add(n["ticker"])
        if nm:
            seen_name.add(nm)
        sec = n.get("sector")
        if by_sec.get(sec, 0) < PER_SECTOR:
            by_sec[sec] = by_sec.get(sec, 0) + 1
            picked.append(n)
        else:
            overflow.append(n)
    notable_clean = (picked + overflow)[:CAP]
    # UNIFY: narrative baskets lead each lane (the resolution the user acts on), GICS
    # sectors follow. on_the_run: basket rows first (same 🧩-then-🏛 pattern), then sectors.
    bi = basket_items or {}
    # FIX 3 — pass more counts from basket_items through to the VM
    _bi_more = bi.get("more") or {}
    _ab_buy_now = (bi.get("buy_now") or []) + buy_now
    _ab_buy_soon = (bi.get("buy_soon") or []) + buy_soon
    _ab_on_the_run = (bi.get("on_the_run") or []) + on_the_run
    _ab_take_profits = (bi.get("take_profits") or []) + take_profits
    _ab_hold = (bi.get("hold") or []) + hold
    _ab_avoid = (bi.get("avoid") or []) + avoid
    return {"buy_now": _ab_buy_now,
            "buy_soon": _ab_buy_soon,
            "on_the_run": _ab_on_the_run,
            "take_profits": _ab_take_profits,
            "hold": _ab_hold,
            "avoid": _ab_avoid,
            "more": _bi_more,
            "notable": notable_clean[:CAP],
            # P-MP1-SHELL §8 "Groups header total" — a single published total across every
            # lane this board buckets rows into (the six urgency lanes the five rendered
            # .actcol columns fold from — take_profits/avoid share the "stand aside" column).
            # Computed ONCE here, at the same place the lanes themselves are assembled, so
            # the template quotes this field rather than re-deriving a count from row
            # iteration (the estate's count law — see lifecycle_counts for the sibling
            # device this mirrors).
            "total": (len(_ab_buy_now) + len(_ab_buy_soon) + len(_ab_on_the_run)
                      + len(_ab_take_profits) + len(_ab_hold) + len(_ab_avoid))}


class ActionBoardContractError(ValueError):
    """The canonical action-board contract cannot be satisfied for this input.

    The artifact MUST NOT be written when this is raised: the caller keeps the
    previous one. Publishing a board without its source date and basket
    binding is what strips a live consumer of the provenance it validates.
    """


def _basket_as_of(payload: dict[str, Any]) -> str:
    top = payload.get("as_of")
    theme = (payload.get("theme_intel") or {}).get("as_of") \
        if isinstance(payload.get("theme_intel"), dict) else None
    if not isinstance(top, str) or not top:
        raise ValueError("baskets.json carries no usable top-level as_of")
    if not isinstance(theme, str) or not theme:
        raise ValueError("baskets.json carries no usable theme_intel.as_of")
    if top != theme:
        raise ValueError(
            f"baskets.json vintage split: as_of={top}, theme_intel.as_of={theme}"
        )
    return top


def _board_has_rows(board: dict[str, Any]) -> bool:
    """True when the board carries at least one actionable row.

    Mirrors the emptiness rule of the freshness gate
    (``scripts/check_sector_intelligence_freshness.py``) exactly: the six
    lanes must hold a row AND the published total must be positive. A board
    that fails either test is a failed computation, not a generation, and must
    not overwrite the last accepted artifact.
    """
    lane_count = sum(
        len(board.get(lane) or [])
        for lane in ACTION_LANES
        if isinstance(board.get(lane) or [], list)
    )
    total = board.get("total")
    if not isinstance(total, int):
        total = lane_count
    return total > 0 and lane_count > 0


def action_board_envelope(*, basket_raw: bytes, action_board: dict[str, Any],
                          generated_utc: str) -> dict[str, Any]:
    """Bind to exact captured basket bytes; no reading, publication or clock."""
    if not isinstance(action_board, dict):
        raise ActionBoardContractError("action_board must be a dictionary")
    if not _board_has_rows(action_board):
        raise ActionBoardContractError("action_board carries no actionable rows")
    if type(basket_raw) is not bytes:
        raise ActionBoardContractError("basket source must be captured bytes")
    try:
        basket_payload = json.loads(basket_raw)
        if not isinstance(basket_payload, dict):
            raise ValueError("baskets.json must contain a JSON object")
        as_of = _basket_as_of(basket_payload)
        datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except (OSError, ValueError) as exc:
        raise ActionBoardContractError(f"basket source is unusable: {exc}") from exc
    return {"schema": "sector_intelligence_action_board.v1", "as_of": as_of,
        "generated_utc": generated_utc, "baskets_sha256": hashlib.sha256(basket_raw).hexdigest(),
        "action_board": deepcopy(action_board)}


def sector_setup_lookups(sector_setups, *, strict: bool = True):
    """Share valid-owner projection; preserve each legacy caller's malformed-input policy."""
    setup, two_reads = {}, {}
    if strict and not isinstance(sector_setups, dict):
        return setup, two_reads
    if sector_setups:
        for row in sector_setups.get("sectors") or []:
            if strict and not isinstance(row, dict):
                continue
            if not row.get("ticker"):
                continue
            setup[row["ticker"]] = row
            chip = row.get("two_reads_chip")
            if (isinstance(chip, dict) if strict else bool(chip)):
                two_reads[row["ticker"]] = chip
    return setup, two_reads


def attach_two_reads(board, lookup, *, strict: bool = True):
    """Apply setup disclosure to caller-owned sector rows, preserving original lanes."""
    if lookup:
        for lane in (*ACTION_LANES, "notable"):
            for item in board.get(lane) or []:
                if strict and not isinstance(item, dict):
                    continue
                ticker = item.get("ticker")
                if item.get("kind") == "sector" and ticker in lookup:
                    item["two_reads_chip"] = lookup[ticker]


def assemble_action_board_from_inputs(*, sector_timing: dict, notable: list[dict],
                                      baskets: dict | None, allocation: dict | None,
                                      sector_setups: dict | None) -> dict:
    """Detached shared reducer over explicitly prepared owner values."""
    timing, stock_rows, basket_data, allocation_data, setups = deepcopy(
        (sector_timing, notable, baskets, allocation, sector_setups))
    setup_lookup, two_reads = sector_setup_lookups(setups)
    board = action_board(timing, stock_rows,
        basket_action_items_from_inputs(basket_data, allocation_data), sector_setup_lookup=setup_lookup)
    attach_two_reads(board, two_reads)
    return board



STATE_STYLES = {
    "FRESH BUY": ("#1d4a2c", "#7fe0a0"), "TURN SIGNALED": ("#1d3a4a", "#8fd0f0"),
    "RALLY ON": ("#1d3326", "#6fce8f"), "BOTTOM WATCH": ("#2b3340", "#9fc0e8"),
    "TOP WATCH": ("#38301a", "#d8b75a"), "ROLLING OVER": ("#4a2c1a", "#e0a070"),
    "DECLINE": ("#3a2020", "#e08080"),
    "COUNTERTREND BOUNCE": ("#3a2e1a", "#e0b070"),
}


BUY_ZONE_STATES = ("FRESH BUY", "TURN SIGNALED")


def _compact_season(line: str | None) -> tuple[str, str]:
    """'Jun: -0.4% avg, up 46% of years (n=28)' -> ('-0.4% (46%)', full)"""
    if not line:
        return "—", T("Not enough history for a seasonal read.", "历史数据不足，无法做季节性判断。")
    try:
        avg = line.split(":")[1].split("avg")[0].strip()
        hit = line.split("up ")[1].split("%")[0]
        return f"{avg} ({hit}%)", line
    except (IndexError, ValueError):
        return line, line


def _b(en: str, zh: str) -> str:
    """Inline bilingual span (raw markup) for use inside composed tooltip HTML."""
    return f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'


def _season_tooltip(seas: dict | None, month: int | None):
    """Rich seasonality hover: a 12-month bar chart of average returns + a two-column
    table (avg / % positive / years), with the current calendar month highlighted.
    Colours use the theme's --up/--down vars so they follow the Asia red/green swap.
    Falls back to a short note when there isn't enough history."""
    from markupsafe import Markup
    if not seas:
        return T("Not enough history for a seasonal read.", "历史数据不足，无法做季节性判断。")
    # latest.json is a JSON round-trip, which stringifies the int month keys
    seas = {int(k): v for k, v in seas.items()}
    month = int(month) if month is not None else None
    months = range(1, 13)
    vmax = max((abs(seas[m]["avg_pct"]) for m in months if m in seas), default=1.0) or 1.0

    # --- bar chart: positive bars up (green), negative down (red) -------------
    W, H = 320, 86
    padL, padR, base_y, span, label_y = 8, 8, 40, 26, 80
    slot = (W - padL - padR) / 12
    bw = slot * 0.56
    svg = [f'<line x1="{padL}" y1="{base_y}" x2="{W - padR}" y2="{base_y}" '
           f'style="stroke:var(--line);stroke-width:1"/>']
    for i, m in enumerate(months):
        cx = padL + slot * (i + 0.5)
        cur = (m == month)
        if cur:                                    # faint full-height column tint
            svg.append(f'<rect x="{cx - slot / 2:.1f}" y="6" width="{slot:.1f}" '
                       f'height="{base_y + span:.1f}" rx="2" '
                       f'style="fill:var(--text);opacity:.07"/>')
        s = seas.get(m)
        if s:
            up = s["avg_pct"] >= 0
            h = max(abs(s["avg_pct"]) / vmax * span, 1.0)
            y = base_y - h if up else base_y
            col = "var(--up)" if up else "var(--down)"
            svg.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                       f'height="{h:.1f}" rx="1.5" '
                       f'style="fill:{col};opacity:{1 if cur else .55}"/>')
        svg.append(                                    # numeric labels read in both languages
            f'<text x="{cx:.1f}" y="{label_y}" text-anchor="middle" '
            f'style="font-size:9px;fill:{"var(--text)" if cur else "var(--muted)"};'
            f'font-weight:{700 if cur else 400}">{m}</text>')
    chart = (f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block;'
             f'margin:4px 0 6px;overflow:visible">{"".join(svg)}</svg>')

    # --- two stacked 6-month tables, current month row highlighted ------------
    def _col(rng) -> str:
        rows = ['<colgroup><col style="width:28%"><col style="width:28%">'
                '<col style="width:23%"><col style="width:21%"></colgroup>',
                f'<tr><th style="text-align:left">{_b("Month", "月份")}</th>'
                f'<th>{_b("Avg", "均值")}</th><th>{_b("Up", "收涨")}</th>'
                f'<th>{_b("Yrs", "年数")}</th></tr>']
        for m in rng:
            s, cur = seas.get(m), (m == month)
            tr = ' style="background:var(--panel2);font-weight:700"' if cur else ''
            name = _b(calendar.month_abbr[m], f"{m}月")
            if s:
                cls = "pos" if s["avg_pct"] >= 0 else "neg"
                rows.append(
                    f'<tr{tr}><td style="text-align:left">{name}</td>'
                    f'<td class="{cls}">{s["avg_pct"]:+.1f}%</td>'
                    f'<td>{s["hit_pct"]:.0f}%</td>'
                    f'<td class="muted">{s["n"]}</td></tr>')
            else:
                rows.append(f'<tr{tr}><td style="text-align:left">{name}</td>'
                            f'<td class="muted">—</td><td class="muted">—</td>'
                            f'<td class="muted">—</td></tr>')
        return ('<table style="margin:0;flex:1 1 0;min-width:0">'
                + "".join(rows) + "</table>")

    tables = (f'<div style="display:flex;gap:10px">'
              f'{_col(range(1, 7))}{_col(range(7, 13))}</div>')
    title = ('<b style="font-size:12px;display:block;margin-bottom:1px">'
             + _b("Seasonality — average return by month",
                  "季节性 — 各月平均回报") + '</b>')
    foot = ('<div class="muted" style="font-size:10.5px;margin-top:6px;line-height:1.4">'
            + _b("Each month’s average return across this instrument’s full history, and "
                 "how often it closed up. Weak evidence — background colour only, never a "
                 "signal on its own (and left out of the heat score).",
                 "该标的全部历史中每个月的平均回报及收涨频率。属于弱证据 — 仅作背景参考，"
                 "绝不单独作为信号（且已排除在热度分数之外）。") + '</div>')
    return Markup(f"{title}{chart}{tables}{foot}")


def _mini_svg(vals, color: str = "var(--link)", w: int = 260, h: int = 54,
              baseline=None, dot: bool = True,
              zone_lo: float | None = None, zone_hi: float | None = None,
              zone_state: str | None = None) -> str:
    """A tiny theme-aware inline sparkline (area + line + last-point marker),
    used both for the nowcast hover charts and the standout-stock cards. Pure
    SVG so it needs no client JS and works offline. `vals` should already be a
    clean numeric list. `baseline` draws a dashed reference line (0 = stall,
    2 = the Fed's inflation target, …). zone_lo/zone_hi/zone_state (all
    optional): the prophet-card buy-zone band, drawn on the same lo/hi/pad
    scale as the polyline — args absent -> output identical to before."""
    vals = [float(v) for v in vals if v is not None and v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    if baseline is not None:
        lo, hi = min(lo, float(baseline)), max(hi, float(baseline))
    rng = (hi - lo) or 1.0
    n = len(vals)
    pad = h * 0.10  # keep the line off the top/bottom edges

    def xy(i, v):
        return (i / (n - 1) * w, (h - pad) - ((v - lo) / rng) * (h - 2 * pad) + pad)

    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(i, v) for i, v in enumerate(vals)))
    out = [f'<svg class="nch" viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
           f'width="100%" height="{h}">']
    if baseline is not None:
        by = (h - pad) - ((float(baseline) - lo) / rng) * (h - 2 * pad) + pad
        out.append(f'<line x1="0" y1="{by:.1f}" x2="{w}" y2="{by:.1f}" '
                   f'stroke="var(--muted)" stroke-width="0.8" stroke-dasharray="3 3" '
                   f'opacity="0.55"/>')
    if zone_hi is not None or zone_lo is not None:
        # Buy-zone band (prophet-card E1): a horizontal price band over the right
        # 40% of the plot — filled low-opacity rect when the zone is ACTIVE, dashed
        # edge lines only when PENDING. Price-clamped into the plotted window; a
        # zone wholly outside it draws nothing. The edge lines carry no fill
        # attribute and the rect keeps fill-opacity, so the prophet-card hue
        # override (stroke on *, fill on [fill]:not([fill="none"])) recolors both
        # without flattening the band.
        try:
            zh = float(zone_hi if zone_hi is not None else zone_lo)
            zl = float(zone_lo if zone_lo is not None else zone_hi)
            zl, zh = min(zl, zh), max(zl, zh)
            if zh > 0 and zh >= lo and zl <= hi:
                yt = (h - pad) - ((min(zh, hi) - lo) / rng) * (h - 2 * pad) + pad
                yb = (h - pad) - ((max(zl, lo) - lo) / rng) * (h - 2 * pad) + pad
                x0 = w * 0.60
                if zone_state == "active":
                    out.append(f'<rect x="{x0:.1f}" y="{yt:.1f}" width="{w - x0:.1f}" '
                               f'height="{max(yb - yt, 0.0):.1f}" fill="{color}" '
                               f'fill-opacity="0.09" stroke="none"/>')
                out.append(f'<line x1="{x0:.1f}" y1="{yt:.1f}" x2="{w}" y2="{yt:.1f}" '
                           f'stroke="{color}" stroke-width="1" stroke-dasharray="4 3" '
                           f'stroke-opacity="0.65"/>'
                           f'<line x1="{x0:.1f}" y1="{yb:.1f}" x2="{w}" y2="{yb:.1f}" '
                           f'stroke="{color}" stroke-width="1" stroke-dasharray="4 3" '
                           f'stroke-opacity="0.65"/>')
        except (TypeError, ValueError):
            pass  # malformed zone — never a broken spark
    out.append(f'<polyline points="0,{h} {pts} {w},{h}" fill="{color}" '
               f'opacity="0.12" stroke="none"/>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
               f'stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>')
    if dot:
        lx, ly = xy(n - 1, vals[-1])
        out.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{color}"/>')
    out.append("</svg>")
    return "".join(out)


def notable_stock_from_inputs(fund, h, r, df, *, alpha_pt, insider_map, factor_z, sue_z):
    """The incumbent standout-stock projection over one analyzed holding."""
    from engine.playbook import SECTOR_NAMES
    from engine.setups import US_ALPHA_WEIGHT, sue_confirmer, timing_tilt
    tick = str(r["ticker"]).replace(".", "-")
    urg = h["ladder"]["entry"]["urgency"]
    if urg in ("now", "imminent", "exit"):
        lad = h["ladder"]
        closes = df["close"].dropna()
        px = float(closes.iloc[-1]) if len(closes) else None
        hi52 = float(closes.iloc[-252:].max()) if len(closes) else None
        off_high = (round((px / hi52 - 1) * 100, 1)
                    if px and hi52 else None)
        # ~3 months of daily closes, thinned for a compact card sparkline
        tail = closes.iloc[-66:]
        spark = list(tail.iloc[::2].round(3)) if len(tail) > 4 else []
        sdir = lad.get("dir")
        scolor = ("var(--up)" if sdir == "up"
                  else "var(--down)" if sdir == "down" else "var(--warn)")
        # alpha-aware setup score: selection (sector-neutral residual
        # momentum) × timing (cycle entry + reversal overlay). Falls back
        # to timing-only when the name has no residual, so EVERY card has
        # a setup_score on the same scale for ranking. NOT a new edge —
        # see engine/setups.py + research/US_STANDOUT_SETUP_SCORE.md.
        apt = alpha_pt.get(tick)
        az = apt.get("alpha") if apt else None
        a_entry = apt.get("entry") if apt else None
        tilt = timing_tilt(urg, lad.get("eq_dir"), a_entry)
        setup = round((US_ALPHA_WEIGHT * az + tilt) if az is not None
                      else tilt, 2)
        # confirmers: an insider BUY cluster (>=2 distinct insiders net
        # buying, Form-4 6mo) + the factor composite (light tiebreaker) +
        # the SUE earnings-momentum z (gated to a real positive tailwind).
        # All DISPLAY context — none touch the setup score above.
        ins = insider_map.get(tick) or {}
        ins_buy = ins.get("buyers", 0) >= 2 and (ins.get("net_mn") or 0) > 0
        return {"ticker": tick, "name": str(r.get("name", "")).title(),
                        "sector": SECTOR_NAMES.get(fund, fund),
                        "label": lad["label"], "action": lad.get("action"),
                        "tag": lad["entry"]["tag"], "urgency": urg,
                        "days": lad["entry"].get("days_hi"),
                        "dir": sdir,
                        "price": round(px, 2) if px is not None else None,
                        "off_high": off_high,
                        "eq_score": lad.get("eq_score"),
                        "eq_grade": lad.get("eq_grade"),
                        "eq_grade_zh": lad.get("eq_grade_zh"),
                        "score": lad.get("score"),
                        "setup_score": setup,
                        "alpha_z": az,
                        "alpha_sector_rank": apt.get("sector_rank") if apt else None,
                        "alpha_sector_n": apt.get("sector_n") if apt else None,
                        "alpha_entry": a_entry,
                        "factor_z": factor_z.get(tick),
                        "insider_buyers": ins.get("buyers") if ins_buy else None,
                        "insider_bps": ins.get("bps") if ins_buy else None,
                        "insider_net_mn": ins.get("net_mn") if ins_buy else None,
                        "sue_z": sue_confirmer(sue_z.get(tick)),
                        "signal_date": lad.get("signal_date"),
                        "age_days": lad.get("age_days"),
                        "spark_svg": _mini_svg(spark, color=scolor, w=240, h=42,
                                               dot=True),
                        "age_short": lad.get("age_short"),
                        "age_short_zh": lad.get("age_short_zh"),
                        "eq_badge": lad.get("eq_badge"),
                        "eq_dir": lad.get("eq_dir"),
                        "eq_tip": lad.get("eq_tip")}
    return None


def sector_timing_summary_from_inputs(fund, res, holdings):
    """The original fund timing/count projection, shared with the page adapter."""
    from engine.playbook import SECTOR_NAMES
    buy_zone = sum(1 for h in holdings if h["ladder"]["state"] in BUY_ZONE_STATES)
    return {"state": res["ladder"]["state"],
                       "label": res["ladder"]["label"],
                       "action": res["ladder"]["action"],
                       "entry": res["ladder"]["entry"],
                       "state_style": STATE_STYLES.get(res["ladder"]["state"]),
                       "dc_day": res["cycle"]["dc_day"],
                       "age_short": res["ladder"].get("age_short"),
                       "age_short_zh": res["ladder"].get("age_short_zh"),
                       "age_days": res["ladder"].get("age_days"),
                       "eq_badge": res["ladder"].get("eq_badge"),
                       "eq_dir": res["ladder"].get("eq_dir"),
                       "eq_tip": res["ladder"].get("eq_tip"),
                       "buy_zone": buy_zone, "n_holdings": len(holdings)}


def sector_setup_from_inputs(*, latest: dict, closes, sectors, timing: dict | None = None) -> dict | None:
    """Original setup/base-rate/display calculation over captured values only."""
    from engine import sector_signals as ssig
    from engine.playbook import SECTOR_NAMES
    try:
        latest, timing = deepcopy(latest), deepcopy(timing)
        sectors = list(sectors)
        if closes is None or "SPY" not in closes:
            return None
        closes = closes.copy(deep=True).sort_index()
        disl = latest.get("dislocation") or {}
        put_absent = disl.get("put_state") == "put-absent"
        bd = ssig.board(closes, SECTOR_NAMES, sectors, spy=closes["SPY"], put_absent=put_absent)
        if not bd.get("sectors"):
            return None
        # live-measured base rates (overrides the static defaults so the displayed
        # numbers always match the live rule); fall back to the engine's documented
        # rates on any shortfall.
        try:
            cal = ssig.calibrate(closes, sectors, closes["SPY"])
        except Exception:  # noqa: BLE001 — calibration is the honesty extra, never fatal
            cal = {}
        stages = {s["ticker"]: s for s in ((latest.get("playbook") or {}).get("stages") or [])}
        month = pd.Timestamp(latest["date"]).month if latest.get("date") else None
        for r in bd["sectors"]:
            r["href"] = US_SECTOR_PAGE.get(r["ticker"], "sectors/" + r["ticker"] + ".html")
            st = stages.get(r["ticker"], {})
            r["verdict"] = T(r["label"], r["label_zh"])
            r["action_txt"] = T(r["action"], r["action_zh"])
            r["signal_txt"] = T(ssig.signal_line(r), ssig.signal_line(r, zh=True))
            r["conv_dots"] = ("●" * max(1, min(r["conviction"], 3))) if r["side"] != "neutral" else "·"
            r["conv_txt"] = T(r["conviction_label"], r["conviction_label_zh"])
            r["tech_str"] = f"{'✓' if r['above200'] else '✗'}200d {'✓' if r['above50'] else '✗'}50d"
            r["tech_ok"] = bool(r["above200"] and r["above50"])
            r["osc_str"] = (f"RSI {r['rsi_3d']:.0f} · Stoch {r['stoch_3d']:.0f}"
                            if r.get("rsi_3d") is not None and r.get("stoch_3d") is not None else "—")
            r["rs_str"] = f"{r['rs_60d']:+.1f}%" if r.get("rs_60d") is not None else "—"
            br = cal.get(r["state"]) or r.get("base_rate") or {}
            if br and r["side"] == "tactical" and br.get("abs63") is not None:
                # tactical oversold-bounce: lead with the ABSOLUTE bounce (the reason
                # it's surfaced), show excess-vs-SPY beside it as the honest cost.
                n = br.get("n"); nbit = f" · n={n}" if n else ""
                r["rate_str"] = T(f"{br['abs63']:+.1f}% abs · {br['abs_hit']}% up | {br['exc63']:+.1f}% vs SPY{nbit}",
                                  f"绝对 {br['abs63']:+.1f}% · {br['abs_hit']}% 上涨 | 对SPY {br['exc63']:+.1f}%{nbit}")
                r["rate_pos"] = None     # mixed read — keep the cell neutral, not green
            elif br:
                n = br.get("n")
                nbit = f" · n={n}" if n else ""
                r["rate_str"] = T(f"{br['exc63']:+.1f}% vs SPY · {br['hit']}% up{nbit}",
                                  f"对SPY {br['exc63']:+.1f}% · {br['hit']}% 上涨{nbit}")
                r["rate_pos"] = br["exc63"] >= 0
            else:
                r["rate_str"], r["rate_pos"] = T("—", "—"), None
            r["rate_hit"] = br.get("hit") if br else None
            r["rate_n"] = br.get("n") if br else None
            r["rate_exc"] = br.get("exc63") if br else None
            r["season_str"], _ = _compact_season(st.get("season_this"))
            _sm = r["season_str"]
            r["season_magnitude"] = _sm.split(" (", 1)[0] if _sm and " (" in _sm else _sm
            r["season_tip"] = _season_tooltip(st.get("season_all"), st.get("season_month") or month)
            # TS-R6 two-reads reconciliation chip: when this ETF's setup-side verdict
            # (3D tactical) conflicts with the cycle timing action (slow, cap-weighted).
            # Fired when: setup side = BUY/SETUP/BUY_PARTIAL (entry-ready) AND cycle
            # timing maps to take_profits or avoid (TAKE PROFITS / exit urgency).
            r["two_reads_chip"] = None
            if timing and r.get("side") == "buy":
                tm = timing.get(r["ticker"]) or {}
                e = tm.get("entry") or {}
                u = e.get("urgency", "")
                tag = e.get("tag", "")
                cycle_label = tm.get("label", "")
                # Cycle is on the reduce side when urgency=exit, OR when caution routes
                # to take_profits (any caution tag except DON'T CHASE / UNCONFIRMED —
                # HIGH RISK, which route to on_the_run / avoid respectively).
                # Mirrors action_board routing exactly (A3 fix).
                _CAUTION_NON_REDUCE = {"DON'T CHASE", "UNCONFIRMED — HIGH RISK"}
                cycle_is_reduce = (u == "exit") or (
                    u == "caution" and tag not in _CAUTION_NON_REDUCE
                )
                if cycle_is_reduce:
                    from engine.cycles import STATE_DISPLAY as _SD
                    # ZH map mirrors ENTRY_STATUS_ZH in templates/dashboard.html.j2 ~6891-6896
                    # plus 'setup' and 'partial' keys used by the setup-side vocab.
                    _SETUP_ZH = {
                        "buy_now": "立即买入", "partial": "半仓",
                        "buy_soon": "即将买入", "setup": "构筑中",
                        "extended": "过热", "watch": "观察",
                        "avoid": "回避", "topping": "做顶",
                        "blocked": "封锁", "exit": "退出",
                    }
                    setup_label = r.get("label") or r.get("label_zh") or r["state"]
                    state_key = r.get("state", "")
                    cycle_label_zh = _SD.get(
                        tm.get("state", ""), {}
                    ).get("label_zh", cycle_label)
                    setup_label_zh = _SETUP_ZH.get(r.get("state", ""), setup_label)
                    r["two_reads_chip"] = {
                        "cycle_label_en": cycle_label,
                        "setup_label_en": setup_label,
                        "setup_state": state_key,
                        "cycle_label_zh": cycle_label_zh,
                        "setup_label_zh": setup_label_zh,
                    }
        return bd
    except Exception as e:  # noqa: BLE001 — preserve the additive view contract
        log.error("sector setup view failed: %s", e)
        return None
