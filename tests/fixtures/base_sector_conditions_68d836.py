"""Literal original dict-MRS and beta owners at 68d836."""
import pandas as pd
from lib import config

def _mrs_weights() -> dict:
    w = (config.load()["engine"].get("macro_overlay") or {}).get("mrs_weights") or {}
    # The `liquidity` leg (contracting half only) is KEPT deliberately: net-liquidity
    # withdrawal is the single mechanism that most differentially hurts cyclicals,
    # and the B-1 sign-check (scripts/research_macro_sector.py) only clears the
    # split-half bar WITH it — removing it strips out the 2018/2022 QT episodes where
    # the cross-sectional signal lives. Net liquidity ALSO has a uniform per-name
    # ladder nudge (cycles.LIQ_HEADWIND); the MRS leg adds SECTOR differentiation on
    # top of that — a small, bounded (~1pt), intentional overlap, not a bug.
    return {"recession": w.get("recession", 1.0), "drawdown": w.get("drawdown", 1.0),
            "nfci": w.get("nfci", 0.5), "liquidity": w.get("liquidity", 0.5),
            "transition": w.get("transition", 0.25)}


def _mrs_label(score: float | None) -> str | None:
    if score is None:
        return None
    return ("severe" if score >= 0.75 else "elevated" if score >= 0.5
            else "moderate" if score >= 0.25 else "low")


def _mrs_transition_high() -> float:
    """MRS weight-value the 'transition' leg contributes when the regime is actively
    TRANSITIONING / NEW_REGIME. Config-driven for a calibration A/B: the default 1.0
    is the pre-existing behaviour — the leg pushes MRS risk-OFF hardest exactly as a
    regime is in flux, which is pro-cyclical INTO a turn (it leaned risk-off harder
    right before the snap-back). Clamping to 0.5 REMOVES that amplification (sign-
    preserving, subtract-only). NOT flipped live: default 1.0 => byte-identical.
    See reports/mrs-transition-clamp-spec.md for the A/B + validation plan."""
    return float((config.load().get("engine", {}).get("macro_overlay") or {})
                 .get("transition_high", 1.0))


def _mrs_transition_val(state) -> float:
    return (_mrs_transition_high() if state in ("TRANSITIONING", "NEW_REGIME")
            else 0.5 if state == "WEAKENING" else 0.0)


def _combine_legs(legs: dict, w: dict):
    """Weighted mean over AVAILABLE legs (renormalized), scalar or pandas. Each leg
    is (value, available); an unavailable leg drops out of BOTH numerator and
    denominator instead of poisoning the score."""
    is_series = any(isinstance(v, pd.Series) for v, _a in legs.values())
    if is_series:
        num = sum(v.fillna(0.0) * a.astype(float) * w.get(n, 0.0)
                  for n, (v, a) in legs.items())
        den = sum(a.astype(float) * w.get(n, 0.0) for n, (_v, a) in legs.items())
        return (num / den.replace(0, np.nan)).clip(0, 1)
    num = den = 0.0
    for n, (v, a) in legs.items():
        if not a or v is None:
            continue
        num += w.get(n, 0.0) * float(v)
        den += w.get(n, 0.0)
    return (num / den) if den > 0 else None


def macro_risk_score(latest: dict) -> dict:
    """Aggregate macro-risk score MRS in [0,1] from a latest.json-shaped dict (the
    dict-path helper). Higher => more macro risk. Pure function of already-lagged
    fields — no new data, no look-ahead. Renormalizes over available legs. Returns
    {score, label, components}.

    NOTE: the engine persists latest['macro_risk'] via macro_risk_snapshot(f,
    regime), NOT this function, because `latest` can mix legs across release dates
    on a cadence-lag day (quad stale while conditions update). This helper is exact
    for a date-coherent `latest` and is retained for dict-only consumers + tests."""
    w = _mrs_weights()
    cond = (latest or {}).get("conditions") or {}
    legs: dict[str, tuple[float | None, bool]] = {}
    rec = (cond.get("recession") or {}).get("score")
    legs["recession"] = (None if rec is None else min(max(rec / 100.0, 0.0), 1.0),
                         rec is not None)
    dd = (cond.get("drawdown_risk") or {}).get("score")
    legs["drawdown"] = (None if dd is None else min(max(dd / 100.0, 0.0), 1.0),
                        dd is not None)
    fc = cond.get("financial_conditions") or {}
    nfci, nfci_pct = fc.get("nfci"), fc.get("nfci_pctile")
    if nfci is not None and nfci_pct is not None:
        tightening = fc.get("trend") == "tightening" and nfci > 0
        legs["nfci"] = (min(max(nfci_pct if tightening else 0.0, 0.0), 1.0), True)
    else:
        legs["nfci"] = (None, False)
    liq = (latest or {}).get("liquidity_overlay")
    legs["liquidity"] = (1.0 if liq == "contracting" else 0.0, liq is not None)
    tr = (latest or {}).get("transition_state")
    legs["transition"] = (_mrs_transition_val(tr), tr is not None)

    score = _combine_legs(legs, w)
    comps = {n: (None if v is None else round(float(v), 3)) for n, (v, _a) in legs.items()}
    return {"score": None if score is None else round(float(score), 4),
            "label": _mrs_label(score), "components": comps}


def sector_macro_beta(key) -> float:
    """Per-sector sensitivity to a risk-OFF macro reading, in [-1, +1]. Keyed by
    SPDR ticker (sector pages) OR GICS / display sector name (stock library);
    0.0 for anything not in the table (ETFs, factors, unknowns). The lookup is
    case-insensitive on names so spelling variants still resolve."""
    if not key:
        return 0.0
    tbl = config.load()["engine"]["confluence"].get("sector_macro_beta") or {}
    if key in tbl:
        return float(tbl[key])
    lk = str(key).strip().lower()
    for k, v in tbl.items():
        if str(k).strip().lower() == lk:
            return float(v)
    return 0.0
