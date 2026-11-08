"""Literal selected build-site calculations from published c18e840; tests bind acquisition."""
from __future__ import annotations
import calendar
import json
import logging
from pathlib import Path
import pandas as pd
from engine.i18n import t as T
from lib import config, store
from lib.pages import write_page
from tests.fixtures.base_sector_action_board_b168 import US_SECTOR_PAGE
log = logging.getLogger(__name__)
def _dollar_context(*args):
    raise AssertionError("Fixture page-only dependency must be explicitly bound")

STATE_STYLES = {
    "FRESH BUY": ("#1d4a2c", "#7fe0a0"), "TURN SIGNALED": ("#1d3a4a", "#8fd0f0"),
    "RALLY ON": ("#1d3326", "#6fce8f"), "BOTTOM WATCH": ("#2b3340", "#9fc0e8"),
    "TOP WATCH": ("#38301a", "#d8b75a"), "ROLLING OVER": ("#4a2c1a", "#e0a070"),
    "DECLINE": ("#3a2020", "#e08080"),
    "COUNTERTREND BOUNCE": ("#3a2e1a", "#e0b070"),
}


BUY_ZONE_STATES = ("FRESH BUY", "TURN SIGNALED")


ETF_GICS = {                       # SPDR sector fund -> GICS sector (residual-alpha leaders)
    "XLK": "Information Technology", "XLF": "Financials", "XLV": "Health Care",
    "XLY": "Consumer Discretionary", "XLP": "Consumer Staples", "XLE": "Energy",
    "XLI": "Industrials", "XLB": "Materials", "XLU": "Utilities",
    "XLRE": "Real Estate", "XLC": "Communication Services",
}


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


def sector_setup_view(latest: dict, timing: dict | None = None) -> dict | None:
    """The Sector Confluence board — the PRIMARY buy/sell setup engine
    (engine.sector_signals): a confluence of MACD + StochRSI crossovers on the
    3-day chart, daily-triggered and 200-day-gated, with extended = avoid. Replaces
    the old "leaders/avoid" scorecard + heat board (research/SECTOR_CONFLUENCE.md).

    Reads the sector + SPY closes from the parquet store, runs the engine, refreshes
    the per-state base rates live (the honesty layer), and folds in the still-useful
    columns (seasonality, 3-mo RS, trend) — seasonality reuses the existing rich
    tooltip already computed on the playbook stages. Display strings are composed
    here so the template stays attribute-safe. Additive; None on any shortfall."""
    from engine import sector_signals as ssig
    from engine.playbook import SECTOR_NAMES
    try:
        sectors = config.load()["yahoo"]["tickers"]["sectors"]
        ydir = config.data_dir() / "yahoo"
        cols = {}
        for t in sectors + ["SPY"]:
            p = ydir / f"{t}.parquet"
            if p.exists():
                cols[t] = pd.read_parquet(p)["close"]
        if "SPY" not in cols:
            return None
        closes = pd.DataFrame(cols).sort_index()
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
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("sector setup view failed: %s", e)
        return None


def build_sector_pages(env: Environment, site: Path, generated: str,
                       alpha: dict | None = None, put_absent: bool = False,
                       rate_infl: dict | None = None) -> dict:
    """Render sectors/<FUND>.html drill-downs; return per-fund timing summary
    for the heat board. ``rate_infl`` maps fund -> the display-only per-sector
    rate/inflation transmission read (engine.sector_rate_inflation), reused from the
    already-computed playbook stages so it is the single source of truth."""
    import json as _json

    from collectors.sector_holdings import latest_fundamentals, latest_top10
    from engine.conditions import sector_macro_beta
    from engine import ticker_alerts
    from engine.cycles import LADDER, STATE_DISPLAY, analyze
    from engine.holdings_signals import accumulation_signals
    from engine.playbook import SECTOR_NAMES
    from engine.setups import US_ALPHA_WEIGHT, sue_confirmer, timing_tilt
    from scripts.build_stock_library import current_liquidity, current_macro

    # per-ticker sector-neutral residual alpha (already computed by build_alpha_data
    # and passed in) — used to enrich the front-page "Standout individual stocks"
    # cards with an alpha sector rank + reversal overlay and an alpha-aware setup
    # score (selection × timing). Absent => cards fall back to pure cycle timing.
    alpha_pt = (alpha or {}).get("per_ticker", {})
    # confirmer legs on those same cards: a distinct-insider Form-4 BUY cluster
    # (insider_signals.json, written by build_insider_data just above), the cross-
    # sectional factor composite (factors.json table) as a light tiebreaker, and the
    # validated SUE earnings-momentum z (factors.json table 'sue') as an earnings-
    # drift confirmer. All additive + graceful — absent => the card omits that chip.
    # None of these enter the setup score; they are displayed risk/conviction context.
    insider_map: dict[str, dict] = {}
    factor_z: dict[str, float] = {}
    sue_z: dict[str, float] = {}
    try:
        _ip = site / "factordata" / "insider_signals.json"
        if _ip.exists():
            insider_map = json.loads(_ip.read_text()) or {}
        _fp = site / "factordata" / "factors.json"
        if _fp.exists():
            for _r in (json.loads(_fp.read_text()) or {}).get("table", []):
                if not _r.get("ticker"):
                    continue
                # audit #25: tiebreak on the scorecard-passing rank composite, not the blind
                # equal-weight composite (which its own scorecard grades anti-predictive).
                _cz = _r.get("composite_rank")
                if _cz is None:
                    _cz = _r.get("composite")
                if _cz is not None:
                    factor_z[_r["ticker"]] = _cz
                if _r.get("sue") is not None:
                    sue_z[_r["ticker"]] = _r["sue"]
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("standout confirmer maps unavailable (%s)", e)

    cal_path = config.data_dir() / "regime" / "ladder_calibration.json"
    calibration = _json.loads(cal_path.read_text()) if cal_path.exists() else None
    # live US net-liquidity regime + aggregate macro-risk score — the orthogonal
    # macro conviction modifiers threaded into every per-sector / per-stock ladder
    # read AND the accumulation overlay (so the overlay ladder matches the card).
    liq = current_liquidity()
    drag = current_macro()
    # benchmark + feed window for each ETF's alert timeline (the ladder log itself
    # is written by build_stock_library, where these ETFs also live — no re-write)
    _spy = store.read("yahoo", "SPY")
    _bench = _spy["close"] if _spy is not None else None
    _acfg = config.load().get("alerts", {})
    _adays = int(_acfg.get("ticker_timeline_days", 120))
    _amax = int(_acfg.get("ticker_max_events", 50))
    tpl = env.get_template("sector.html.j2")
    outdir = site / "sectors"
    outdir.mkdir(parents=True, exist_ok=True)
    # Policy-shock de-escalation state (PS-R3: display de-escalation only — no sizing/reordering)
    _shock_path = site / "live" / "shock_state.json"
    _shock_state: dict | None = None
    try:
        if _shock_path.exists():
            import json as _jsss
            _shock_state = _jsss.loads(_shock_path.read_text())
    except Exception as _sse:  # noqa: BLE001 — additive, never fatal
        log.warning("shock_state unavailable for sector pages (%s)", _sse)

    import json as _json2
    summaries: dict[str, dict] = {}
    notable: list[dict] = []
    for fund in config.load()["sponsors"]["sector_funds"]:
        etf = store.read("yahoo", fund)
        if etf is None:
            continue
        beta = sector_macro_beta(fund)
        res = analyze(etf["close"], liquidity=liq, macro_drag=drag, macro_beta=beta)
        if not res.get("ladder"):
            continue
        holdings = []
        t10 = latest_top10(fund)
        if t10 is not None:
            for _, r in t10.iterrows():
                tick = str(r["ticker"]).replace(".", "-")
                df = store.read("stocks", tick)
                if df is None or len(df) < 300:
                    continue
                h = analyze(df["close"], df.get("high"), liquidity=liq,
                            macro_drag=drag, macro_beta=beta)
                if not h.get("ladder"):
                    continue
                h["mtf_json"] = _json2.dumps(h.get("mtf", {}))
                holdings.append({"ticker": tick,
                                 "name": str(r.get("name", "")).title(),
                                 "weight_pct": r["weight_pct"], **h,
                                 "fundamentals": latest_fundamentals(tick)})
                # collect decisive individual-stock signals for the front page
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
                    notable.append({"ticker": tick, "name": str(r.get("name", "")).title(),
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
                                    "eq_tip": lad.get("eq_tip")})
        buy_zone = sum(1 for h in holdings if h["ladder"]["state"] in BUY_ZONE_STATES)
        s = {"fund": fund, "name": SECTOR_NAMES.get(fund, fund),
             "mtf_json": _json2.dumps(res.get("mtf", {})), **res,
             "holdings": holdings,
             "rate_infl": (rate_infl or {}).get(fund),  # display-only macro overlay
             "dollar_ctx": _dollar_context(site, fund),  # W3-C4b display-only dollar-lean chip
             "accumulation": accumulation_signals(fund, liquidity=liq,
                                                  macro_drag=drag, macro_beta=beta)}
        if alpha and fund in ETF_GICS:                 # within-sector residual-alpha leaders
            _sa = (alpha.get("by_sector") or {}).get(ETF_GICS[fund])
            if _sa:
                s["alpha_leaders"] = _sa.get("leaders")
        ec = etf["close"].dropna()
        # technical snapshot for the at-a-glance signal-chip strip (same shape the
        # stock analyzer reads from its JSON, so both pages render identical chips)
        from engine.technicals import snapshot as _snap
        s["tech"] = _snap(ec)
        # validated confluence verdict (the same engine that drives the main-dashboard
        # Sector buy/sell setups board) — engine/sector_signals
        try:
            from engine import sector_signals as _ssig
            sig = _ssig.sector_signal(ec, SECTOR_NAMES.get(fund, fund), spy_close=_bench,
                                      ticker=fund, put_absent=put_absent)
            if sig.get("ok"):
                sig["signal_en"] = _ssig.signal_line(sig)
                sig["signal_zh"] = _ssig.signal_line(sig, zh=True)
            s["confluence"] = sig
        except Exception as _e:  # noqa: BLE001 — additive, never fatal
            log.error("sector confluence (%s) failed: %s", fund, _e)
            s["confluence"] = None
        feed = ticker_alerts.build_feed(
            fund, ec, etf.get("high"), _bench, res.get("ladder"),
            str(ec.index.max().date()), days=_adays, max_events=_amax)
        html = tpl.render(s=s, state_styles=STATE_STYLES, calibration=calibration,
                          ladder_order=LADDER, state_display=STATE_DISPLAY,
                          alerts=feed, generated_utc=generated,
                          shock_state=_shock_state)
        write_page(outdir / f"{fund}.html", html)
        summaries[fund] = {"state": res["ladder"]["state"],
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
    log.info("wrote %d sector drill-down pages", len(summaries))
    return summaries, notable
