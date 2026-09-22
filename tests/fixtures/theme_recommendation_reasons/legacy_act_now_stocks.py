# Frozen test-only incumbent from 4e01f20e2dc5ee66634ed51ec127ba8b8630b860; never imported by production.
def act_now_stocks(members: list, theme: dict) -> dict:
    """WHAT TO ACT ON NOW (stock level) — the member stocks with a genuine buy entry RIGHT
    NOW, GATED by theme health: if the theme is out of favour (deteriorating / fading /
    avoid / trim, or a NEUTRAL theme below its long-term trend) it recommends NOTHING.
    A label the engine has AFFIRMATIVELY called constructive (EMERGING / DOMINANT) is NOT
    vetoed by the slow 200d `in_bull` flag — such a theme is early / below-trend by
    construction, and theme_scoring._reco has already demoted its verb to HOLD; vetoing it
    again here just made the board self-contradict ("out of favour (emerging)"). Otherwise
    only members whose per-stock Conviction Profile is a buy/add, with the cycle NOT blocking
    and a decent entry-axis percentile (good price, not chasing). Honest: a focus list, never
    an order.

    `members` carry a plucked `conviction` block (score, verdict, cycle_blocked, entry_pct)."""
    label = (theme or {}).get("label")
    reco = (theme or {}).get("reco")
    tx = (theme or {}).get("textures") or {}
    in_bull = (tx.get("bull_age") or {}).get("in_bull", True)
    # "Out of favour" must mean the theme's OWN lifecycle read is risk-off — a fading /
    # deteriorating label or a trim / avoid reco. The raw 200d-SMA `in_bull` flag is a SLOW
    # filter: an EMERGING / DOMINANT theme freshly turning up off a base sits below its 200d
    # (in_bull False) BY CONSTRUCTION, so it must not override the engine's own constructive
    # call — that produced the self-contradicting "out of favour (emerging)" scoreboard while
    # suppressing members that DID have an open entry. Drawdown-control for an early /
    # below-trend theme is already applied upstream in theme_scoring._reco (it demotes the verb
    # to HOLD). So a False `in_bull` only counts as a downtrend veto when the label is NOT
    # constructive (i.e. neutral / missing).
    risk_label = label in ("deteriorating", "fading")
    risk_reco = reco in ("avoid", "trim")
    constructive = label in ("emerging", "dominant")
    downtrend = (in_bull is False) and not constructive
    theme_blocked = risk_label or risk_reco or downtrend

    def early_turn_watch(theme_reason: str | None = None,
                         theme_reason_zh: str | None = None) -> list[dict]:
        """Surface fast T1/T2 evidence that is not yet an actionable theme-gated buy."""
        out = []
        for m in members or []:
            c = m.get("conviction") or {}
            sig = c.get("signal") or {}
            tier = sig.get("tier")
            if tier not in ("T1", "T2"):
                continue
            entry = c.get("entry") or {}
            status = entry.get("status")
            clean = (status in ("buy_now", "partial") and not c.get("cycle_blocked")
                     and (c.get("score") or 0) >= 50)
            if clean and not theme_blocked:
                continue
            if theme_reason:
                blocker_en = f"theme gate: {theme_reason}"
                blocker_zh = f"主题门槛：{theme_reason_zh or theme_reason}"
            elif c.get("cycle_blocked"):
                blocker_en = "slow cycle has not confirmed the turn"
                blocker_zh = "慢周期尚未确认转折"
            elif status:
                blocker_en = entry.get("headline") or status.replace("_", " ")
                blocker_zh = entry.get("headline_zh") or blocker_en
            else:
                blocker_en = "fast turn has not opened a clean entry"
                blocker_zh = "快速转折尚未形成干净入场"
            out.append({
                "symbol": m.get("symbol"), "name": m.get("name"),
                "tier": tier, "provisional": bool(sig.get("provisional")),
                "score": c.get("score"), "cycle_blocked": bool(c.get("cycle_blocked")),
                "entry_status": status, "entry_headline": entry.get("headline"),
                "entry_headline_zh": entry.get("headline_zh"),
                "blocker_en": blocker_en, "blocker_zh": blocker_zh,
                "ret_5d": m.get("ret_5d"), "ret_20d": m.get("ret_20d"),
            })
        tier_rank = {"T2": 2, "T1": 1}
        out.sort(key=lambda x: (-tier_rank.get(x["tier"], 0), -(x.get("score") or 0),
                                x.get("symbol") or ""))
        return out[:12]

    # Members the ranker can NEVER surface — no conviction read (not in the per-stock
    # library, or a thin record without a score). Carried on every payload so the detail
    # page prints the gap explicitly: an all-uncovered basket must read as a coverage
    # gap, not a misleading "no clean entry".
    uncovered = [m.get("symbol") for m in members or []
                 if (m.get("conviction") or {}).get("score") is None]
    if theme_blocked:
        why = label if risk_label else reco if risk_reco else "downtrend"
        why_en = "in a downtrend" if why == "downtrend" else str(why)
        why_zh = {"deteriorating": "走弱", "fading": "退潮", "avoid": "建议回避",
                  "trim": "建议减持", "downtrend": "处于下行趋势"}.get(why, str(why))
        return {"status": "theme_out_of_favour", "buys": [], "uncovered": uncovered,
                "early_turn_watch": early_turn_watch(why_en, why_zh),
                "note_en": "Theme is out of favour (" + why_en + ") — no stock buys recommended here right now.",
                "note_zh": "主题暂不被青睐（" + why_zh + "）— 当前不建议买入该主题个股。"}
    buys = []
    for m in members or []:
        c = m.get("conviction")
        if not c or c.get("score") is None:
            continue
        # Two-gauge: a member is "act now" only when the ENTRY gauge says the window is
        # open (buy_now / partial), not when the conviction score is merely high — and
        # never when the cycle blocks. Falls back to the entry-axis percentile for any
        # older record that predates the entry_signal block.
        entry = c.get("entry") or {}
        status = entry.get("status")
        ep = c.get("entry_pct")
        if status:
            is_buy = status in ("buy_now", "partial") and not c.get("cycle_blocked")
        else:
            v = (c.get("verdict") or "").lower()
            is_buy = ("buy" in v or "add" in v or "leader" in v) and not c.get("cycle_blocked") \
                and (ep is None or ep >= 0.45)
        if is_buy and (c.get("score") or 0) >= 50:
            buys.append({"symbol": m.get("symbol"), "name": m.get("name"),
                         "score": c.get("score"), "verdict": c.get("verdict"),
                         "verdict_zh": c.get("verdict_zh"), "entry_pct": ep,
                         "entry_status": status, "act_level": entry.get("act_level"),
                         "zone_low": entry.get("zone_low"), "zone_high": entry.get("zone_high"),
                         "ret_5d": m.get("ret_5d"), "ret_20d": m.get("ret_20d"),
                         "ret_ytd": m.get("ret_ytd"),
                         "rationale": m.get("rationale")})
    buys.sort(key=lambda x: (-(x.get("act_level") or 0), -(x.get("entry_pct") or 0), -(x.get("score") or 0)))
    if not buys:
        return {"status": "no_clean_entries", "buys": [], "uncovered": uncovered,
                "early_turn_watch": early_turn_watch(),
                "note_en": "Theme is in favour, but no member has a clean entry right now — most are extended or mid-trend. Wait for a pullback.",
                "note_zh": "主题尚可，但当前无成分股具备干净入场点 — 多数已延展或处于趋势中段。等待回调。"}
    return {"status": "ok", "buys": buys[:12], "uncovered": uncovered,
            "early_turn_watch": early_turn_watch()}
