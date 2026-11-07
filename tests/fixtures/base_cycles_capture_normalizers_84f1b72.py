"""Literal original owner functions at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json, logging
from lib import config
log = logging.getLogger(__name__)

def acquire_calculation_inputs(*, evaluation_date: str,
                               markets: tuple[str, ...] = ("US",)) -> CycleCalculationInputs:
    """Legacy acquisition adapter; runtime may construct these same values itself.

    Calibration is captured afresh through its incumbent loaders. No process-global
    fitted/risk/reference cache is substituted for this capture.
    """
    from engine import vol_regime
    day = date.fromisoformat(normalize_evaluation_date(evaluation_date))
    settings = config.load().get("engine") or {}
    entry = settings.get("entry_gate") or {}
    return CycleCalculationInputs(
        evaluation_date=day.isoformat(),
        fitted_bands=_load_fitted_bands(), risk_calibration=_load_risk_calib(),
        macro_overlay=settings.get("macro_overlay") or {},
        vol_regime_overlay=settings.get("vol_regime_overlay") or {},
        vol_overlay_gate=vol_regime.load_overlay_gate() or {},
        entry_gate={
            "stoch_oversold": float(entry.get("stoch_oversold", _EG_STOCH_OS)),
            "stoch_overbought": float(entry.get("stoch_overbought", _EG_STOCH_OB)),
            "daily_rsi_extension_cap": float(entry.get("daily_rsi_extension_cap", _EG_DAILY_RSI_MAX)),
            "stretch_block_pct": float(entry.get("stretch_block_pct", _EG_STRETCH_BLOCK)),
            "approach_days": int(entry.get("approach_days", _EG_APPROACH_DAYS)),
            "overextended_osc_exempt_below_pct": float(entry.get(
                "overextended_osc_exempt_below_pct", _EG_OSC_EXEMPT_BELOW)),
        },
        reference_sessions={session_anchor._market_key(m):
            session_anchor.capture_reference_sessions(m, asof=day) for m in markets},
    )

def _load_risk_calib() -> dict:
    """Load ladder_risk_calibration.json -> {family: {state: mult}}. Returns {} on any
    error (fallback to all-1.0). Mirrors _load_fitted_bands (W2.8)."""
    try:
        p = config.data_dir() / "regime" / "ladder_risk_calibration.json"
        if not p.exists():
            return {}
        import json as _json
        d = _json.loads(p.read_text(encoding="utf-8"))
        rsm = d.get("risk_size_mult") or {}
        clamp = d.get("mult_clamp") or [0.5, 1.5]
        out: dict = {}
        for fam, states in rsm.items():
            out[fam] = {}
            for st, cell in states.items():
                m = cell.get("risk_size_mult", 1.0) if isinstance(cell, dict) else float(cell)
                out[fam][st] = float(min(max(m, clamp[0]), clamp[1]))
        log.info("cycles: loaded ladder risk calibration from %s (validated=%s, any_bound=%s)",
                 p, d.get("validated"), d.get("any_cell_bound"))
        return out
    except Exception as e:  # noqa: BLE001
        log.debug("cycles: ladder risk calibration unavailable (%s) — using 1.0 for all states", e)
        return {}

def risk_size_mult(state: str, family: str | None) -> float:
    """Fitted SIZE multiplier in [0.5,1.5] for (state, family). 1.0 when no artifact, no
    family, or the cell did not earn a weight (null-cell discipline). Additive to sizing,
    NEVER to the directional score. One-time log per non-1.0 (state,family)."""
    global _RISK_CALIB, _RISK_CALIB_LOADED  # noqa: PLW0603
    captured = _CALCULATION_INPUTS.get()
    if captured is not None:
        fam = _RISK_FAMILY_ALIAS.get(family or "", family)
        return captured.risk_calibration.get(fam, {}).get(state, 1.0)
    if not _RISK_CALIB_LOADED:
        _RISK_CALIB = _load_risk_calib()
        _RISK_CALIB_LOADED = True
    fam = _RISK_FAMILY_ALIAS.get(family or "", family)
    if not fam or fam not in _RISK_CALIB:
        return 1.0
    m = _RISK_CALIB[fam].get(state, 1.0)
    if m != 1.0 and (fam, state) not in _RISK_CALIB_LOGGED:
        log.info("cycles: %s/%s risk_size_mult override -> %.3fx (fitted, W4.6)", fam, state, m)
        _RISK_CALIB_LOGGED.add((fam, state))
    return m
