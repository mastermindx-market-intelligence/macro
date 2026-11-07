"""Literal original Central context owners at 68d836."""
from engine.sector_central import np, json, config, log, _aggregate_heat

def _regime_anchor(latest: dict | None = None) -> dict:
    """The validated US risk posture. There is NO engine.masterminds.regime_state() to call;
    the US analogue is data/regime/latest.json + engine.conditions.macro_risk_score (the
    validated risk-OFF scalar). Returns a normalized market read with a risk-on scalar in
    [-1,+1] and a [0,1] gate factor for bullish convictions.

    `latest`: an already-assembled latest.json dict (the coherence assert passes the IN-MEMORY
    latest for THIS run — before it is written to disk — so the gate is validated against the
    same-run risk read, not the previous run's persisted file). Default None → read from disk."""
    d = latest if isinstance(latest, dict) and latest else {}
    if not d:
        try:
            p = config.data_dir() / "regime" / "latest.json"
            if p.exists():
                d = json.loads(p.read_text()) or {}
        except Exception as e:  # noqa: BLE001
            log.warning("central: regime latest.json unreadable: %s", e)

    quad, quad_name = d.get("quad"), d.get("quad_name")
    liquidity = d.get("liquidity_overlay") or d.get("liquidity")
    g_score, i_score = d.get("growth_score"), d.get("inflation_score")
    rstate = d.get("risk_state") or {}

    # validated risk-OFF scalar: macro_risk_score MRS in [0,1], higher = more risk-OFF.
    mrs = None
    try:
        from engine.conditions import macro_risk_score
        mrs = macro_risk_score(d)
    except Exception as e:  # noqa: BLE001
        log.warning("central: macro_risk_score failed: %s", e)
    mrs = mrs or (d.get("macro_risk") if isinstance(d.get("macro_risk"), dict) else None) or {}
    derisk = mrs.get("score")                       # 0..1, higher = more risk-off
    # flip to a risk-on scalar in [-1,+1] (+1 risk-on … −1 risk-off)
    risk_on = round(-(2.0 * float(derisk) - 1.0), 2) if derisk is not None else None

    quad_lean = {"Q1": 1, "Q2": 1, "Q3": -1, "Q4": -1}.get(quad)
    liq_lean = {"expanding": 1, "contracting": -1, "neutral": 0, "unknown": None}.get(liquidity)

    # gate factor for BULLISH convictions in [0,1]: risk-off shrinks long tilts (gating, not a
    # switch). Driven by the validated MRS; quad/liquidity nudge — identical arithmetic to China.
    if risk_on is None:
        gate = 0.7
    else:
        gate = float(np.clip(0.5 + 0.5 * risk_on, 0.2, 1.0))
    if quad_lean == -1:
        gate *= 0.85
    if liq_lean == -1:
        gate *= 0.8
    elif liq_lean == 1:
        gate = min(1.0, gate * 1.1)
    # the validated LEADING risk-off tell (breadth divergence) one-way caps the gate
    caution = (((d.get("conditions") or {}).get("complacency") or {}).get("caution"))
    if caution:
        gate = min(gate, 0.85)
    gate = round(float(np.clip(gate, 0.2, 1.0)), 2)

    # the GATE posture (what actually drives the gate) is the validated MRS scalar — kept verbatim
    # as gate_state_* and surfaced as the banner sub-line. The gating arithmetic above is unchanged.
    r = risk_on or 0
    gate_state_en = "Risk-on" if r > 0.2 else "Risk-off" if r < -0.2 else "Neutral"
    gate_state_zh = "偏多" if r > 0.2 else "偏空" if r < -0.2 else "中性"

    # HEADLINE = the SAME radar-aware Market State verdict the macro page shows, so the two pages
    # can never disagree. The macro_risk leg above IGNORES the Risk Radar (that is exactly why this
    # page used to read "Risk-on" while macro.html read "Risk-off"); the Market State verdict does
    # not. Prefer the persisted nightly snapshot (byte-identical to macro.html); else recompute from
    # the same latest.json (radar-aware, sans the trend leg); else fall back to the gate label.
    state_en, state_zh = gate_state_en, gate_state_zh
    ms_verdict = ms_score = ms_color = radar_state = None
    try:
        from engine import market_state as _ms
        snap = _ms.load_persisted() or _ms.market_state_snapshot(d)
        if snap:
            state_en = snap.get("label_en") or state_en
            state_zh = snap.get("label_zh") or state_zh
            ms_verdict, ms_score, ms_color = snap.get("verdict"), snap.get("score"), snap.get("color")
            radar_state = (snap.get("radar") or {}).get("state")
    except Exception as e:  # noqa: BLE001
        log.warning("central: market_state unify failed: %s", e)

    return {
        "risk_on": risk_on, "gate_factor": gate,
        "state_en": state_en, "state_zh": state_zh,
        "gate_state_en": gate_state_en, "gate_state_zh": gate_state_zh,
        "ms_verdict": ms_verdict, "ms_score": ms_score, "ms_color": ms_color,
        "radar_state": radar_state,
        "tactical_label": rstate.get("label_en"), "tactical_label_zh": rstate.get("label_zh"),
        "risk_state_score": rstate.get("score"), "risk_state_state": rstate.get("state"),
        "headline_en": rstate.get("headline_en"), "headline_zh": rstate.get("headline_zh"),
        "derisk_blended": (round(float(derisk), 2) if derisk is not None else None),
        "mrs_label": mrs.get("label"), "mrs_components": mrs.get("components"),
        "quad": quad, "quad_name": quad_name, "liquidity": liquidity,
        "growth_score": g_score, "inflation_score": i_score,
        "caution": bool(caution),
        "validated": True,
    }


def _heat_table() -> dict:
    """Per-(Finviz)-sector cap-weighted heat + breadth from the Sector Heatmap feed
    (site/marketdata/sp500_heatmap.json). Display CONTEXT only — coincident color, never a lead.
    Python port of heatmap.js weightedPc/breadth (size_basis=='marketcap' → cap-weighted)."""
    try:
        site = config.ROOT / config.load()["storage"]["site_dir"]
        p = site / "marketdata" / "sp500_heatmap.json"
        if not p.exists():
            return {}
        return _aggregate_heat(json.loads(p.read_text()))
    except Exception as e:  # noqa: BLE001
        log.debug("central: heatmap aggregate failed: %s", e)
        return {}


def market_context() -> dict:
    anc = _regime_anchor()
    # crowding fragility map (per-ticker; display/size context only) — degrades to {}
    crowd = {}
    try:
        from engine.crowding import compute_fragility
        crowd = compute_fragility() or {}
    except Exception as e:  # noqa: BLE001
        log.debug("central: compute_fragility failed: %s", e)
    return {**anc, "heat": _heat_table(), "_crowd_by_ticker": crowd}
