"""Evidence gate for the Risk Radar — the STRICT bar, committed + reusable.

Re-implements the day-level forward-lift + frequency-matched permutation + era-split
methodology from research/RISK_ENGINE_V2_FINDINGS.md §8, on committed code (no /tmp).
Used by tests/test_risk_radar.py (a leg that stops leading FAILS CI) and by the Opus
self-correction loop (engine/risk_radar_review.py) to re-grade legs after a retune.

A signal column is a CAUSAL 0-1 risk-rising percentile (as produced by
risk_radar.leading_signals). 'elevated' = pctile >= thr. Lift = P(SPY drawdown-onset
within the next `fwd_bd` business days | elevated) / base rate. All leak-free.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from lib import store


def _spy(*, drop_missing: bool = True):
    df = store.read("yahoo", "SPY")
    if df is None or "close" not in df:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    s = df["close"].dropna() if drop_missing else df["close"].copy()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def detect_events(spy=None, fwd: int = 63, depth: float = 0.08, min_gap: int = 40) -> list:
    """Drawdown-onset dates: a local peak whose max drawdown over the next `fwd` trading
    days is >= `depth`. De-duplicated to one onset per decline (>= min_gap apart, keep the
    highest peak). Returns a list of pd.Timestamp onsets (forward-looking labels — fine)."""
    spy = _spy() if spy is None else spy
    px = spy.to_numpy()
    n = len(px)
    onsets = []
    for i in range(n - 1):
        window = px[i + 1: i + 1 + fwd]
        if len(window) == 0:
            continue
        if (window.min() / px[i] - 1.0) <= -depth:
            onsets.append(i)
    # de-dup: keep the highest peak within min_gap
    merged = []
    for i in onsets:
        if merged and (i - merged[-1]) < min_gap:
            if px[i] > px[merged[-1]]:
                merged[-1] = i
        else:
            merged.append(i)
    return [spy.index[i] for i in merged]


def _fwd_label(idx: pd.DatetimeIndex, onsets: list, fwd_bd: int) -> pd.Series:
    on = np.array([o.to_datetime64() for o in onsets])
    out = pd.Series(False, index=idx)
    vals = idx.values
    for k, d in enumerate(vals):
        hi = (pd.Timestamp(d) + pd.tseries.offsets.BDay(fwd_bd)).to_datetime64()
        if np.any((on > d) & (on <= hi)):
            out.iloc[k] = True
    return out


def lift(pct: pd.Series, onsets: list, *, thr: float = 0.90, fwd_bd: int = 15,
         lo=None, hi=None) -> dict:
    """Day-level forward lift of a causal percentile series at threshold `thr`, optionally
    restricted to an era [lo, hi). Returns {lift, fire_rate, n_elev, base, n_days}."""
    pct = pct.dropna()
    if lo is not None:
        pct = pct[pct.index >= pd.Timestamp(lo)]
    if hi is not None:
        pct = pct[pct.index < pd.Timestamp(hi)]
    if len(pct) < 200:
        return {"lift": None, "fire_rate": None, "n_elev": 0, "base": None, "n_days": len(pct)}
    fwd = _fwd_label(pct.index, onsets, fwd_bd)
    base = float(fwd.mean())
    elev = pct >= thr
    n_elev = int(elev.sum())
    if n_elev == 0 or base == 0:
        return {"lift": None, "fire_rate": float(elev.mean()), "n_elev": n_elev,
                "base": base, "n_days": len(pct)}
    p = float(fwd[elev].mean())
    return {"lift": round(p / base, 3), "fire_rate": round(float(elev.mean()), 4),
            "n_elev": n_elev, "base": round(base, 4), "n_days": len(pct)}


def perm_p(pct: pd.Series, onsets: list, *, thr: float = 0.90, fwd_bd: int = 15,
           n: int = 300, seed: int = 0) -> float | None:
    """Frequency-matched permutation p-value: random elevated days at the SAME fire-rate ->
    day-level lift null; p = fraction of random lifts >= the real lift. Low p = real edge."""
    real = lift(pct, onsets, thr=thr, fwd_bd=fwd_bd)
    if real["lift"] is None:
        return None
    pct = pct.dropna()
    fwd = _fwd_label(pct.index, onsets, fwd_bd).to_numpy().astype(float)
    base = fwd.mean()
    if base == 0:
        return None
    k = max(1, real["n_elev"])
    rng = np.random.default_rng(seed)
    null = np.empty(n)
    for j in range(n):
        sel = rng.choice(len(fwd), size=k, replace=False)
        null[j] = fwd[sel].mean() / base
    return float((null >= real["lift"]).mean())


_ORDER = ["calm", "watch", "caution", "elevated", "risk-off"]


def _band_idx(score: pd.Series, bands: dict) -> pd.Series:
    """Vectorized band index 0..4 (calm..risk-off) for a 0-100 sub-score series.

    Band cuts may be scalars or per-date Series. Calendar context is sizing-only and does not
    alter any of them."""
    idx = pd.Series(0, index=score.index)
    idx = idx.mask(score >= bands["watch"], 1)
    idx = idx.mask(score >= bands["caution"], 2)
    idx = idx.mask(score >= bands["elevated"], 3)
    idx = idx.mask(score >= bands["risk_off"], 4)
    return idx


def band_delta_series(idx) -> pd.Series:
    """Compatibility series for the retired election-cycle band nudge.

    The 2026-08-12 authority audit moved the weak seasonal prior to sizing-only, so this is
    intentionally zero on every date. Keeping the helper avoids breaking archived research code
    while ensuring replays and live computation share the same fixed measured bands."""
    index = pd.DatetimeIndex(idx)
    return pd.Series(0.0, index=index)


def state_series(subs: pd.DataFrame, calib: dict,
                 sigs: pd.DataFrame | None = None) -> pd.Series:
    """Daily engine state using the exact live transition owner.

    The armed+confirm conjunction and Tier-B eligibility depend on the raw
    causal leg percentiles, so sub-scores alone are not sufficient to reproduce
    production semantics. Canonical callers pass the same signal frame used to
    build the sub-scores. A compatibility fallback reloads leading_signals()
    only when older callers omit sigs.
    """
    from engine import risk_radar as rr

    if subs is None or subs.empty:
        return pd.Series(dtype=object, index=getattr(subs, "index", None))
    if sigs is None:
        try:
            sigs = rr.leading_signals().reindex(subs.index)
        except Exception:  # noqa: BLE001
            sigs = pd.DataFrame(index=subs.index)
    else:
        sigs = sigs.reindex(subs.index)

    try:
        gate = rr.context_gate_series(subs.index).reindex(subs.index)
    except Exception:  # noqa: BLE001
        gate = pd.Series(False, index=subs.index)

    states = []
    for day, subrow in subs.iterrows():
        sigrow = sigs.loc[day] if day in sigs.index else pd.Series(dtype=float)
        gate_value = gate.loc[day] if day in gate.index else False
        gate_met = False if pd.isna(gate_value) else bool(gate_value)
        states.append(
            rr._resolve_state_row(subrow, sigrow, calib, gate_met=gate_met)["state"]
        )
    return pd.Series(states, index=subs.index, dtype=object)


def state_accuracy(calib: dict, *, onsets=None, dd: float = 0.05, H: int = 21,
                   alert_from: str = "elevated", lo=None) -> dict:
    """State-replay accuracy on complete native SPY observation windows.

    The supplied price index is not an exchange-calendar completeness claim.
    Different forecast coverage must not resample prices or erase intervening losses.
    """
    if type(H) is not int or H <= 0:
        raise ValueError("H must be a positive integer number of future observations")
    if type(dd) not in (int, float) or not np.isfinite(dd) or not 0 < dd < 1:
        raise ValueError("dd must be a finite loss fraction strictly between zero and one")
    if alert_from not in _ORDER:
        raise ValueError("alert_from must name an existing Risk Radar state")
    from engine.risk_radar import subscore_series, leading_signals
    sigs = leading_signals()
    subs = subscore_series(sigs, calib)
    if subs is None or subs.empty:
        return {"f1": None}
    spy = _spy(drop_missing=False)
    for index in (spy.index, subs.index):
        if (not isinstance(index, pd.DatetimeIndex) or index.hasnans or
                not index.is_unique or not index.is_monotonic_increasing):
            raise ValueError("Replay inputs require unique ordered dated observations")
    # Preserve missing prices: neither forward-fill nor skip invalid observations.
    bools = spy.map(lambda value: isinstance(value, (bool, np.bool_)))
    px = pd.to_numeric(spy, errors="coerce").where(~bools).to_numpy(dtype=float)
    good = np.isfinite(px) & (px > 0)
    losses, ends = {}, {}
    for day, loc in zip(subs.index, spy.index.get_indexer(subs.index)):
        if loc < 0 or loc + H >= len(px) or not good[loc:loc + H + 1].all():
            continue
        loss = float(px[loc + 1:loc + H + 1].min() / px[loc] - 1.)
        if np.isfinite(loss):
            losses[day], ends[day] = loss, spy.index[loc + H]
    fdd = pd.Series(losses, dtype=float).reindex(subs.index)
    state = state_series(subs, calib, sigs=sigs).reindex(subs.index)
    known = state.isin(_ORDER) & subs.notna().any(axis=1)
    alert = state.map(lambda value: value in _ORDER and
                      _ORDER.index(value) >= _ORDER.index(alert_from))
    population = subs.index
    if lo is not None:
        population = population[population >= pd.Timestamp(lo)]
    common = population.intersection(fdd[known & fdd.notna()].index)
    a, y = alert.reindex(common), (fdd.reindex(common) <= -dd)
    tp, fp = int((a & y).sum()), int((a & ~y).sum())
    fn, tn = int((~a & y).sum()), int((~a & ~y).sum())
    rows = [[day.isoformat(), ends[day].isoformat(), float(fdd[day]).hex(), bool(y[day])]
            for day in common]
    evidence = {
        "definition": "risk_radar_state_replay.v2", "horizon_observations": H,
        "loss_threshold": float(dd), "alert_from": alert_from,
        "outcomes_sha256": hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest(),
        "from": common[0].isoformat() if len(common) else None,
        "through": common[-1].isoformat() if len(common) else None,
        "n_events": tp + fn, "n_nonevents": fp + tn,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else 0.
    return {"precision": None if prec is None else round(prec, 3),
            "recall": None if rec is None else round(rec, 3),
            "f1": round(f1, 3) if len(common) else None,
            "fire_rate": round(float(a.mean()), 4) if len(common) else None,
            "n_alert": int(a.sum()), "n_days": int(len(common)),
            "n_unscored": int(len(population) - len(common)), "evaluation": evidence}



def probability_quality_report(calib: dict, *, dd: float = 0.05,
                               horizons=(5, 10, 21)) -> dict:
    """Displayed-probability quality on complete native SPY windows.

    This is the probability-side do-no-harm evidence used by the self-correction
    loop. It evaluates the *actual displayed surface* (gated state + current
    Tier-A hot-count conjunction bump), never a state-only surrogate.

    The report is descriptive and read-only. It writes no calibration, ledger,
    policy, sizing or authority state.
    """
    if type(dd) not in (int, float) or not np.isfinite(dd) or not 0 < dd < 1:
        raise ValueError("dd must be a finite loss fraction strictly between zero and one")
    horizons = tuple(int(h) for h in horizons)
    if not horizons or any(h <= 0 for h in horizons):
        raise ValueError("horizons must contain positive observation counts")

    from engine import risk_radar as rr

    sigs = rr.leading_signals()
    subs = rr.subscore_series(sigs, calib)
    if sigs is None or sigs.empty or subs is None or subs.empty:
        return {"horizons": {}, "authority_partition_h21": {}, "ready": False}

    spy = _spy(drop_missing=False)
    for index in (spy.index, subs.index):
        if (not isinstance(index, pd.DatetimeIndex) or index.hasnans or
                not index.is_unique or not index.is_monotonic_increasing):
            raise ValueError("Replay inputs require unique ordered dated observations")

    state = state_series(subs, calib, sigs=sigs).reindex(subs.index)
    known = state.isin(_ORDER) & subs.notna().any(axis=1)

    tier_a = [
        scare for scare, spec in calib.get("scares", {}).items()
        if spec.get("tier") == "A" and scare in subs.columns
    ]
    if tier_a:
        hot_count = sum(
            (subs[scare] >= calib["bands"]["caution"]).astype(int)
            for scare in tier_a
        ).astype(int)
    else:
        hot_count = pd.Series(0, index=subs.index, dtype=int)

    bools = spy.map(lambda value: isinstance(value, (bool, np.bool_)))
    px = pd.to_numeric(spy, errors="coerce").where(~bools).to_numpy(dtype=float)
    good = np.isfinite(px) & (px > 0)

    prob_cal = calib.get("prob_cal") or rr._PROB_CAL
    h21 = prob_cal.get("h21", rr._PROB_CAL["h21"])
    authority_partition = {
        st: bool(float(h21.get(st, rr._PROB_CAL["h21"][st])) > rr._PROB_BASE["h21"])
        for st in _ORDER
    }

    result = {
        "horizons": {},
        "authority_partition_h21": authority_partition,
        "ready": True,
    }
    for H in horizons:
        losses, ends = {}, {}
        for day, loc in zip(subs.index, spy.index.get_indexer(subs.index)):
            if loc < 0 or loc + H >= len(px) or not good[loc:loc + H + 1].all():
                continue
            loss = float(px[loc + 1:loc + H + 1].min() / px[loc] - 1.)
            if np.isfinite(loss):
                losses[day], ends[day] = loss, spy.index[loc + H]
        fdd = pd.Series(losses, dtype=float).reindex(subs.index)
        hkey = f"h{H}"
        result["horizons"][hkey] = {}

        for window, lo in (("full", None), ("y2020", "2020-01-01")):
            population = subs.index
            if lo is not None:
                population = population[population >= pd.Timestamp(lo)]
            common = population.intersection(fdd[known & fdd.notna()].index)
            y = (fdd.reindex(common) <= -dd).astype(float)
            probs = pd.Series(
                [
                    float(rr._drawdown_prob(
                        str(state.loc[day]), int(hot_count.loc[day]), calib
                    )[hkey])
                    for day in common
                ],
                index=common,
                dtype=float,
            )
            brier = float(np.mean((probs - y) ** 2)) if len(common) else None
            base_rate = float(y.mean()) if len(common) else None
            base_brier = (
                float(np.mean((base_rate - y) ** 2))
                if len(common) and base_rate is not None else None
            )
            rows = [
                [day.isoformat(), ends[day].isoformat(), float(fdd[day]).hex(), bool(y[day])]
                for day in common
            ]
            evidence = {
                "definition": "risk_radar_probability_replay.v1",
                "horizon_observations": H,
                "loss_threshold": float(dd),
                "outcomes_sha256": hashlib.sha256(
                    json.dumps(rows, separators=(",", ":")).encode()
                ).hexdigest(),
                "from": common[0].isoformat() if len(common) else None,
                "through": common[-1].isoformat() if len(common) else None,
            }
            result["horizons"][hkey][window] = {
                "brier_score": brier,
                "base_rate_brier_score": base_brier,
                "mean_displayed_probability": float(probs.mean()) if len(common) else None,
                "base_rate": base_rate,
                "n_days": int(len(common)),
                "evaluation": evidence,
            }
            if brier is None or not np.isfinite(brier):
                result["ready"] = False
    return result


def _probability_do_no_harm(proposed: dict, base: dict, *, dd: float = 0.05,
                            evaluator=None) -> dict:
    """Guard prob_cal changes with paired Brier + authority-partition evidence."""
    if proposed.get("prob_cal") == base.get("prob_cal"):
        return {"required": False, "passes": True, "reason": "prob_cal_unchanged"}

    evaluator = evaluator or probability_quality_report
    before = evaluator(base, dd=dd)
    after = evaluator(proposed, dd=dd)
    rows = {}
    ready = bool(before.get("ready", True) and after.get("ready", True))
    populations_match = True
    brier_nonworse = True
    strict = False

    for hkey in ("h5", "h10", "h21"):
        rows[hkey] = {}
        for window in ("full", "y2020"):
            b = ((before.get("horizons") or {}).get(hkey) or {}).get(window) or {}
            p = ((after.get("horizons") or {}).get(hkey) or {}).get(window) or {}
            bb, pb = b.get("brier_score"), p.get("brier_score")
            be = b.get("evaluation") or {}
            pe = p.get("evaluation") or {}
            same_population = (
                b.get("n_days") == p.get("n_days")
                and be.get("outcomes_sha256")
                and be.get("outcomes_sha256") == pe.get("outcomes_sha256")
            )
            valid = all(
                type(v) in (int, float) and np.isfinite(v) and 0 <= float(v) <= 1
                for v in (bb, pb)
            )
            delta = float(pb - bb) if valid else None
            nonworse = bool(valid and delta <= 1e-12)
            improved = bool(valid and delta < -1e-12)
            ready = bool(ready and valid)
            populations_match = bool(populations_match and same_population)
            brier_nonworse = bool(brier_nonworse and nonworse)
            strict = bool(strict or improved)
            rows[hkey][window] = {
                "base_brier": bb,
                "proposed_brier": pb,
                "delta": delta,
                "same_population": bool(same_population),
                "nonworse": nonworse,
            }

    authority_before = before.get("authority_partition_h21") or {}
    authority_after = after.get("authority_partition_h21") or {}
    authority_ok = bool(authority_before and authority_before == authority_after)

    passes = bool(
        ready and populations_match and brier_nonworse and strict and authority_ok
    )
    if not ready:
        reason = "probability_evidence_unready"
    elif not populations_match:
        reason = "probability_population_mismatch"
    elif not brier_nonworse:
        reason = "probability_brier_worse"
    elif not strict:
        reason = "probability_no_strict_brier_gain"
    elif not authority_ok:
        reason = "probability_authority_partition_changed"
    else:
        reason = "probability_do_no_harm_passed"

    return {
        "required": True,
        "passes": passes,
        "reason": reason,
        "comparison_ready": ready,
        "populations_match": populations_match,
        "brier_nonworse": brier_nonworse,
        "strict_brier_improvement": strict,
        "authority_partition_ok": authority_ok,
        "authority_partition_before": authority_before,
        "authority_partition_after": authority_after,
        "windows": rows,
    }

def compare_calib(proposed: dict, base: dict | None = None, *, dd: float = 0.05, H: int = 21) -> dict:
    """Composite do-no-harm gate for the self-correction loop.

    Every proposal must preserve/improve full + 2020+ alert F1 and the validated-leg
    evidence gate. If `prob_cal` changes, it must ALSO pass the probability-specific
    gate: paired H5/H10/H21 Brier non-worsening on full + 2020+, at least one strict
    Brier improvement, identical scored populations, and an unchanged H21 authority
    partition. This prevents a probability change from piggybacking on a band/leg F1 win.
    """
    from engine.risk_radar import _calib
    base = base or _calib()
    onsets = detect_events()
    out = {}
    for label, c in (("base", base), ("proposed", proposed)):
        out[label] = {"full": state_accuracy(c, onsets=onsets, dd=dd, H=H),
                      "y2020": state_accuracy(c, onsets=onsets, dd=dd, H=H, lo="2020-01-01")}
    # validated legs must still lead under proposed (legs don't depend on bands, but thr_pct does)
    rep = gate_report(thr=0.90)
    legs_ok = all((rep.get(leg, {}).get("lift_2020") or 0) >= 1.0
                  for leg, lc in proposed.get("legs", {}).items()
                  if (lc.get("lift_2020") or 0) >= 1.2)
    scores = [out[label][window].get("f1")
              for label in ("base", "proposed") for window in ("full", "y2020")]
    ready = all(type(score) in (int, float) and np.isfinite(score) and 0 <= score <= 1
                for score in scores)
    bf = out["base"]["full"]["f1"] or 0; pf = out["proposed"]["full"]["f1"] or 0
    b20 = out["base"]["y2020"]["f1"] or 0; p20 = out["proposed"]["y2020"]["f1"] or 0
    alert_gate = bool(
        ready
        and (pf >= bf - 1e-9)
        and (p20 >= b20 - 1e-9)
        and legs_ok
        and (pf + p20) > (bf + b20)
    )
    probability_gate = _probability_do_no_harm(proposed, base, dd=dd)
    improves = bool(alert_gate and probability_gate.get("passes"))

    out["comparison_ready"] = bool(ready)
    out["legs_ok"] = legs_ok
    out["alert_gate"] = alert_gate
    out["probability_gate"] = probability_gate
    out["improves"] = improves
    return out


def gate_report(sigs=None, onsets=None, *, thr: float = 0.90) -> dict:
    """Per-leg lift (full + 2020+) for the gate. Returns {leg: {lift, lift_2020, fire_rate, ...}}."""
    from engine.risk_radar import leading_signals
    sigs = leading_signals() if sigs is None else sigs
    onsets = detect_events() if onsets is None else onsets
    out = {}
    for leg in sigs.columns:
        full = lift(sigs[leg], onsets, thr=thr)
        e20 = lift(sigs[leg], onsets, thr=thr, lo="2020-01-01", hi="2027-01-01")
        out[leg] = {"lift": full["lift"], "lift_2020": e20["lift"],
                    "fire_rate": full["fire_rate"], "n_elev_2020": e20["n_elev"]}
    return out
