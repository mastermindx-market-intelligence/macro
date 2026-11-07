"""Literal original macro projection at 68d836; shared unchanged display primitives."""
from engine.theme_scoring import (np, _read_json, _tanh, _enum_zh, _r,
    _FED_DIR_ZH, _NFCI_STATE_ZH, _NFCI_TREND_ZH, _BOND_CYCLE_ZH)

def _macro_context(region: str = "us") -> dict:
    """Fold the live cross-site snapshots (regime / bonds / forex / cross-asset) into one
    state read + a per-axis state vector for the macro leg. Display strings are bilingual;
    policy is shown as CONTEXT-only and never scored.

    Region-aware: US reads regime/bonds/forex; CN/HK/CA read their own <region>_regime
    snapshot. The US-specific Fed-path / NFCI / dollar signals don't apply abroad, so for
    non-US the macro leg stays near-neutral and the trend/breadth/impulse/crowding legs carry
    the score (a richer per-region macro overlay is a future enhancement)."""
    if region == "us":
        reg = _read_json("regime", "latest.json")
        bonds = _read_json("bonds", "latest.json")
        fx = _read_json("forex", "latest.json")
    else:
        reg = _read_json(f"{region}_regime", "latest.json")
        bonds, fx = {}, {}
    # B3 item 7: for all regions (incl. cn/hk/ca), read the global dollar regime + stance
    # word from forex/latest.json for the DISPLAY sub-dict only. The numeric scoring state
    # (state dict) is untouched — these fields never enter the composite score.
    # Fail-open: absent file → both stay None.
    _fx_display = _read_json("forex", "latest.json") if region != "us" else fx
    cond = reg.get("conditions") or {}
    fc = cond.get("financial_conditions") or {}
    ra = cond.get("risk_appetite") or {}
    rec = cond.get("recession") or {}
    dd = cond.get("drawdown_risk") or {}

    growth = float(reg.get("growth_score") or 0.0)
    inflation = float(reg.get("inflation_score") or 0.0)
    quad = reg.get("quad") or ""

    # rate direction from the implied Fed path (real data): m6 below now = easing priced.
    fp = (reg.get("fed_path") or {}).get("implied") or {}
    now_r, m6_r = fp.get("now"), fp.get("m6")
    if now_r is not None and m6_r is not None:
        dr = float(now_r) - float(m6_r)            # >0 => rates falling (easing)
        fed_dir = "easing" if dr > 0.05 else "hiking" if dr < -0.05 else "on hold"
    else:
        dr, fed_dir = 0.0, "unknown"
    # NFCI loosening reinforces an easing tailwind for rate-sensitive themes.
    nfci_trend = fc.get("trend") or ""
    rates_state = float(np.clip(_tanh(dr, 3.0)
                                + (0.3 if "loosen" in nfci_trend else -0.3 if "tighten" in nfci_trend else 0.0),
                                -1, 1))

    nfci_state = fc.get("state") or ""
    riskon = float(np.clip(
        (0.4 if nfci_state == "loose" else -0.4 if nfci_state == "tight" else 0.0)
        + (0.3 if (dd.get("band") == "low") else -0.3 if (dd.get("band") == "high") else 0.0)
        + (0.2 if (ra.get("vrp_state") in ("low", "normal")) else -0.2 if ra.get("vrp_state") == "high" else 0.0)
        + (0.1 if (rec.get("label") == "low") else -0.3 if rec.get("label") in ("elevated", "high") else 0.0),
        -1, 1))

    state = {
        "growth": float(np.clip(_tanh(growth, 0.6), -1, 1)),
        "rates": rates_state,
        "inflation": float(np.clip(_tanh(inflation, 0.6), -1, 1)),
        "riskon": riskon,
    }

    # per-sector live RS (real, already computed by the regime engine) for the confirmer
    sector_rs = {}
    for row in (reg.get("sector_rs") or []):
        t, pc = row.get("ticker"), row.get("pctile_252d")
        if t is not None and pc is not None:
            sector_rs[t] = float(pc) / 100.0   # pctile is 0..100 in the snapshot

    summary_en = (f"{reg.get('quad_name') or quad} · {reg.get('cycle_tag') or '—'}-cycle · "
                  f"Fed {fed_dir} · NFCI {nfci_state or '—'} ({nfci_trend or 'flat'}) · "
                  f"bonds {bonds.get('cycle_phase') or '—'} · USD {fx.get('regime') or '—'}")
    summary_zh = (f"{_enum_zh(reg.get('quad_name')) or quad} · "
                  f"{_enum_zh(reg.get('cycle_tag')) or '—'}周期 · "
                  f"美联储{_enum_zh(fed_dir, _FED_DIR_ZH)} · "
                  f"NFCI {_enum_zh(nfci_state, _NFCI_STATE_ZH) or '—'} · "
                  f"债券{_enum_zh(bonds.get('cycle_phase'), _BOND_CYCLE_ZH) or '—'}")
    # B3 item 7: dollar_regime + stance word from forex latest (display-only for all regions)
    _fx_stance = (_fx_display.get("stance") or {}) if _fx_display else {}
    _quad_name = reg.get("quad_name")
    _cycle = reg.get("cycle_tag")
    _bond_cycle = bonds.get("cycle_phase")
    _dollar_regime = (_fx_display.get("regime") if _fx_display else None) or fx.get("regime")
    # Every display VALUE ships with its Chinese twin: the backdrop strip on the China /
    # HK / Canada desks renders these verbatim, so an English-only value is an
    # untranslated stat in the glance tier. Absent readings stay None so the renderer's
    # em-dash placeholder still fires in both languages.
    return {
        "state": state, "sector_rs": sector_rs,
        "display": {
            "quad": quad, "quad_name": _quad_name, "cycle": _cycle,
            "quad_name_zh": _enum_zh(_quad_name),
            "cycle_zh": _enum_zh(_cycle),
            "growth_score": _r(growth, 2), "inflation_score": _r(inflation, 2),
            "fed_dir": fed_dir, "nfci_state": nfci_state, "nfci_trend": nfci_trend,
            "fed_dir_zh": _enum_zh(fed_dir, _FED_DIR_ZH),
            "nfci_state_zh": _enum_zh(nfci_state, _NFCI_STATE_ZH),
            "nfci_trend_zh": _enum_zh(nfci_trend, _NFCI_TREND_ZH),
            "dollar_regime": _dollar_regime,
            "dollar_regime_zh": _enum_zh(_dollar_regime),
            "dollar_stance_word_en": _fx_stance.get("word_en") or None,  # B3
            "dollar_stance_word_zh": _fx_stance.get("word_zh") or None,  # B3
            "bond_cycle": _bond_cycle,
            "bond_cycle_zh": _enum_zh(_bond_cycle, _BOND_CYCLE_ZH),
            "recession_band": rec.get("label"), "drawdown_band": dd.get("band"),
            "summary_en": summary_en, "summary_zh": summary_zh,
            "as_of": reg.get("date"),
        },
    }
