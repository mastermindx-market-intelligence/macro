"""Literal pre-extraction board algorithms from b168ff4; loaders supplied by test scaffolding."""
from __future__ import annotations
import json
import logging
from datetime import datetime
import hashlib
from typing import Any
from pathlib import Path
log = logging.getLogger(__name__)

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


_ACTION_LANES = (
    "buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid",
)


def basket_action_items(site) -> dict:
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
        ti = (json.loads((site / "basketdata" / "baskets.json").read_text())
              .get("theme_intel") or {})
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("basket action: baskets.json unreadable (%s)", e)
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
        aj = json.loads((site / "allocationdata" / "allocation.json").read_text())
        alloc = {r["id"]: r for r in (aj.get("ranks") or [])}
        book_wt = {w["id"]: w.get("weight")
                   for w in ((aj.get("allocation") or {}).get("weights") or [])}
    except Exception as e:  # noqa: BLE001 — enrichment only
        log.warning("basket action: allocation.json unreadable (%s)", e)

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
        for lane in _ACTION_LANES
        if isinstance(board.get(lane) or [], list)
    )
    total = board.get("total")
    if not isinstance(total, int):
        total = lane_count
    return total > 0 and lane_count > 0


def _atomic_json_write(path, payload):
    raise AssertionError("test must install its publication capture")


def write_action_board(
    output: Path,
    *,
    baskets_path: Path,
    action_board: dict[str, Any],
    generated_utc: str,
) -> dict[str, Any]:
    """Bind the board to one observed basket byte snapshot and publish atomically.

    The basket date/hash identify the associated basket generation. They do not
    establish freshness or common provenance for every other board input.
    Invalid source/board content leaves the previous artifact untouched.
    """
    if not isinstance(action_board, dict):
        raise ActionBoardContractError("action_board must be a dictionary")
    if not _board_has_rows(action_board):
        raise ActionBoardContractError("action_board carries no actionable rows")
    try:
        basket_raw = baskets_path.read_bytes()
        basket_payload = json.loads(basket_raw)
        if not isinstance(basket_payload, dict):
            raise ValueError("baskets.json must contain a JSON object")
        as_of = _basket_as_of(basket_payload)
        datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except (OSError, ValueError) as exc:
        raise ActionBoardContractError(f"basket source is unusable: {exc}") from exc
    payload = {
        "schema": "sector_intelligence_action_board.v1",
        "as_of": as_of,
        "generated_utc": generated_utc,
        "baskets_sha256": hashlib.sha256(basket_raw).hexdigest(),
        "action_board": action_board,
    }
    _atomic_json_write(output, payload)
    return payload
