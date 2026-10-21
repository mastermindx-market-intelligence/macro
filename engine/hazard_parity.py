"""SIC-D-B12 — live-vs-training hazard feature parity harness (measurement only).

Measures whether the live Sector Cycles hazard input vector is the SAME vector the
admitted W4.2 scorer was trained on — feature by feature, plus missing-value policy,
direction, basis and epoch — and records a finite verdict (``PARITY_HOLDS`` /
``PARITY_FAILS``).  This module never repairs the live features, never refits,
never recalibrates and never touches the scorer; a FAIL is a recorded negative
finding, not a defect to fix here.

Method contract (frozen in the packet):
  * Training side = the row ``scripts/build_hazard_panel.py`` would produce at the
    as-of, computed by IMPORTING the panel/fit functions (importlib below).  The
    formulas are never copied — drift between this harness and the panel build
    breaks the harness, which is the point.
  * Live side = the exact ``hf``/direction/quad/liq_expanding that
    ``engine/sector_cycles._stamp_hazard`` passes to ``hazard_score.score``, read
    through the pure helper ``sector_cycles._live_hazard_inputs`` on a record built
    by the live builder (``build_sector``) on the same price series.
  * Comparison happens at the SCORER-VECTOR level: training row through
    ``fit_cycle_hazard.build_design`` versus ``hazard_score._build_feature_vector``,
    per ``_DESIGN`` feature, each difference expressed in units of that feature's
    training standard deviation (frozen below from the admitted model artifact).
    MATCH iff |diff| <= 0.05 sd; age dummies and 0/1 features require exact
    equality.  A feature classed SAME_DEFINITION that numerically mismatches is a
    harness failure, not a verdict.

``LIVE_HAZARD_PARITY`` holds the recorded verdict measured on the seeded synthetic
tape (input kind 1 of the packet) at base ``a038b3f35aafd3acc8879212a25373d4c94510c2``.
Real-tape repetition (input kind 2) was NOT run — no tracked price history for the
11 SPDR ETFs exists under ``data/`` at the base (GAP, see the B12 research doc).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PARITY_SCHEMA = "sector_cycles.hazard_parity.v1"
BASE_SHA = "a038b3f35aafd3acc8879212a25373d4c94510c2"

_REPO = Path(__file__).resolve().parent.parent

# Training standard deviations, frozen from the admitted model artifact
# data/hazard/model_price_c4414dcb.json (coefficients[direction].sd, read
# 2026-10-20 at BASE_SHA).  Frozen — not re-read at runtime — so the harness is
# deterministic and runs where data/ is not materialized.
_SD_SOURCE = "data/hazard/model_price_c4414dcb.json:coefficients[dir].sd (frozen at base)"
_MU_SD: dict[str, dict[str, dict[str, float]]] = {
    "up": {
        "mu": {"log_age_ratio": 0.72169, "amp_proxy": 0.42144, "pos_osc_s": 0.58430,
               "osc_slope_s": 0.15323, "mom_score": 0.07183, "rs_63d": 0.01269,
               "vol_pctile": 0.42145},
        "sd": {"log_age_ratio": 1.08277, "amp_proxy": 0.28588, "pos_osc_s": 0.25119,
               "osc_slope_s": 1.66980, "mom_score": 0.19894, "rs_63d": 0.08862,
               "vol_pctile": 0.29960},
    },
    "down": {
        "mu": {"log_age_ratio": 0.52551, "amp_proxy": 0.56323, "pos_osc_s": 0.25811,
               "osc_slope_s": -0.39017, "mom_score": -0.05482, "rs_63d": -0.01980,
               "vol_pctile": 0.54835},
        "sd": {"log_age_ratio": 0.85066, "amp_proxy": 0.28555, "pos_osc_s": 0.19597,
               "osc_slope_s": 1.57635, "mom_score": 0.15675, "rs_63d": 0.09074,
               "vol_pctile": 0.27447},
    },
}

# _DESIGN features compared with EXACT equality (dummies / 0-1 flags), not sd units.
_EXACT_FEATURES = frozenset({
    "age_b1", "age_b2", "age_b3", "age_b4", "age_b5",
    "trend_pass", "quad_Q2", "quad_Q3", "quad_Q4",
    "liq_expanding", "fam_country", "fam_cn",
})

_MATCH_SD = 0.05

# Static per-feature definition classes, from code reading at BASE_SHA.
# class ∈ SAME_DEFINITION | PROXY | IMPUTED_CONSTANT | DIFFERENT_DEFINITION | ABSENT_LIVE.
# A SAME_DEFINITION numeric mismatch would be a harness failure, not a verdict.
# Sources are terse file:function pointers; the full prose lives in the B12
# research doc's per-feature table.
_T = "scripts/build_hazard_panel.py"
_L = "engine/sector_cycles.py"
_H = "engine/hazard_score.py"
_O = "engine/cycle_ontology.py"
_F = "scripts/fit_cycle_hazard.py"
STATIC_CLASSES: dict[str, dict] = {
    "age_b1": {"class": "DIFFERENT_DEFINITION",
               "training": f"{_T}:_build_instrument_rows — age_m = days/30.44 since confirmed_at turn; _age_bucket ratio edges .5/.8/1.1/1.5",
               "live": f"{_L}:_live_hazard_inputs→{_H}:_age_buckets — bars = Δdecimal-yrs×252; cuts -.19/.45/.99/1.63"},
    "age_b2": {"class": "DIFFERENT_DEFINITION", "training": None, "live": None},
    "age_b3": {"class": "DIFFERENT_DEFINITION", "training": None, "live": None},
    "age_b4": {"class": "DIFFERENT_DEFINITION", "training": None, "live": None},
    "age_b5": {"class": "DIFFERENT_DEFINITION", "training": None, "live": None},
    "log_age_ratio": {"class": "DIFFERENT_DEFINITION",
                      "training": f"{_T}:_log_age_ratio — ln(age_m / k=6 blended median, months)",
                      "live": f"{_L}:_live_hazard_inputs — ln(bars/252×12 ÷ median_half_yrs×12), proj median/2"},
    "amp_proxy": {"class": "DIFFERENT_DEFINITION",
                  "training": f"{_T}:_amp_proxy — expanding pctile of 63d range/price (TR)",
                  "live": f"{_L}:_live_hazard_inputs — amp_leg_pct = last swing mag_pct/100 (open leg)"},
    "pos_osc_s": {"class": "DIFFERENT_DEFINITION",
                  "training": f"{_T}:_detrended_osc — SMA200 dev expanding pctile (TR) → {_F}:build_design /100",
                  "live": f"{_L}:_detrended_osc — EMA252 detrend, 252-stochastic (price) → /100"},
    "osc_slope_s": {"class": "DIFFERENT_DEFINITION",
                    "training": f"{_T}:_osc_slope — panel osc.diff(21) → /10",
                    "live": f"{_L}:_record_core — live osc 22-bar diff → /10"},
    "trend_pass": {"class": "DIFFERENT_DEFINITION",
                   "training": f"{_T}:_trend_pass — close>SMA200 min100 (TR)",
                   "live": f"{_L}:_record_core — struct[-1]>mean(struct[-200:]) (price)"},
    "mom_score": {"class": "PROXY",
                  "training": f"{_T}:_mom_score — 126d−21d own TR return (fraction)",
                  "live": f"{_L}:_live_hazard_inputs — mom_score = now.rs_63d (percent)"},
    "rs_63d": {"class": "DIFFERENT_DEFINITION",
               "training": f"{_T}:_rs_63d — rel. return vs bench (fraction)",
               "live": f"{_L}:_leadership — rs.pct_change(63)×100 (percent)"},
    "vol_pctile": {"class": "IMPUTED_CONSTANT",
                   "training": f"{_T}:_rolling_vol_pctile — expanding pctile of 63d realized vol",
                   "live": f"{_L}:_live_hazard_inputs — None → {_H}:_build_feature_vector 0.42"},
    "quad_Q2": {"class": "ABSENT_LIVE",
                "training": f"{_T}:_build_instrument_rows — regime_hist quad asof t",
                "live": f"{_L}:_live_hazard_inputs — nw.quad never set → 0"},
    "quad_Q3": {"class": "ABSENT_LIVE", "training": None, "live": None},
    "quad_Q4": {"class": "ABSENT_LIVE", "training": None, "live": None},
    "liq_expanding": {"class": "ABSENT_LIVE",
                      "training": f"{_T}:_build_instrument_rows — regime liquidity == 'expanding'",
                      "live": f"{_L}:_live_hazard_inputs — nw.liq_expanding never set → 0"},
    "fam_country": {"class": "SAME_DEFINITION",
                    "training": f"{_F}:build_design — family=='country'",
                    "live": f"{_H}:_FAM_DUMMIES — family 'sector' → 0"},
    "fam_cn": {"class": "SAME_DEFINITION",
               "training": f"{_F}:build_design — family=='cn_sector'",
               "live": f"{_H}:_FAM_DUMMIES — family 'sector' → 0"},
}
# b2..b5 share the b1 sources; quad_Q3/Q4 share quad_Q2's.
for _b in ("age_b2", "age_b3", "age_b4", "age_b5"):
    STATIC_CLASSES[_b]["training"] = STATIC_CLASSES["age_b1"]["training"]
    STATIC_CLASSES[_b]["live"] = STATIC_CLASSES["age_b1"]["live"]
for _q in ("quad_Q3", "quad_Q4"):
    STATIC_CLASSES[_q]["training"] = STATIC_CLASSES["quad_Q2"]["training"]
    STATIC_CLASSES[_q]["live"] = STATIC_CLASSES["quad_Q2"]["live"]
del _b, _q

# Missing-value policy per hf field: training (panel/build_design) vs live (stamp/scorer).
MISSING_VALUE_POLICY: list[dict[str, str]] = [
    {"field": "pos (pos_osc_s)", "training": "NaN → column median fill (build_design)",
     "live": "now.pos or 50.0 in _stamp_hazard; scorer refuses only on None"},
    {"field": "osc_slope (osc_slope_s)", "training": "NaN → column median fill (build_design)",
     "live": "now.osc_slope or 0.0 in _stamp_hazard"},
    {"field": "amp_leg_pct (amp_proxy)", "training": "NaN → column median fill (build_design)",
     "live": "None → scorer constant 0.42 (model mu)"},
    {"field": "mom_score", "training": "NaN → column median fill (build_design)",
     "live": "None → 0.0 (scorer `or 0.0`)"},
    {"field": "rs_63d", "training": "NaN → column median fill (build_design)",
     "live": "None → 0.0 (scorer `or 0.0`)"},
    {"field": "vol_pctile", "training": "NaN → column median fill (build_design)",
     "live": "always None live → constant 0.42 (IMPUTED_CONSTANT)"},
    {"field": "trend_pass", "training": "NaN → column median fill (build_design fill list)",
     "live": "now.above200d or 0.0 (scorer `or 0.0`)"},
    {"field": "age / median_half_yrs (age buckets, log_age_ratio)",
     "training": "log_age_ratio NaN → b_unknown (all dummies 0) + median fill of the ratio",
     "live": "age_since_turn_bars None or median_half_yrs ≤ 0 → scorer REFUSES to score (returns None)"},
    {"field": "quad / liquidity dummies", "training": "NaN regime → 0 via == comparison",
     "live": "None → 0 (ABSENT_LIVE)"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Script-side imports (importlib — the panel/fit formulas are never copied)
# ─────────────────────────────────────────────────────────────────────────────

_panel_mod = None
_fit_mod = None


def _load_script(rel: str, name: str):
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    spec = importlib.util.spec_from_file_location(name, _REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def panel_module():
    """scripts/build_hazard_panel.py, imported (cached) — the W4.2 panel contract."""
    global _panel_mod
    if _panel_mod is None:
        _panel_mod = _load_script("scripts/build_hazard_panel.py", "hazard_parity_panel")
    return _panel_mod


def fit_module():
    """scripts/fit_cycle_hazard.py, imported (cached) — build_design lives here."""
    global _fit_mod
    if _fit_mod is None:
        _fit_mod = _load_script("scripts/fit_cycle_hazard.py", "hazard_parity_fit")
    return _fit_mod


# ─────────────────────────────────────────────────────────────────────────────
# Input 1 — deterministic synthetic tape (seeded; ≥8y; several ≥14% swings)
# ─────────────────────────────────────────────────────────────────────────────

SYNTH_SEED = 12
SYNTH_START = "2015-06-01"
SYNTH_END = "2024-06-28"
SYNTH_WARMUP_MONTHS = 30   # both sides need ≥300 bars, ≥2 confirmed turns, 210 RS rows


def synthetic_tape(seed: int = SYNTH_SEED) -> dict:
    """Seeded daily tape: instrument price/TR + benchmark price/TR.

    Two superposed cycles (~1.7y, ~3.3y) plus noise so several ≥14% swings
    confirm on BOTH turn detectors.  TR = price × a 1.5%/yr accrual so the
    structure(price)-vs-TR feature-basis seam is exercised, not assumed away.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(SYNTH_START, SYNTH_END)
    n = len(idx)
    t = np.arange(n)
    cyc = (0.22 * np.sin(2 * np.pi * t / (252 * 1.7) + 0.5)
           + 0.10 * np.sin(2 * np.pi * t / (252 * 3.3) + 1.1))
    px = 100.0 * np.exp(cyc + np.cumsum(rng.normal(0.0002, 0.012, n)))
    bpx = 100.0 * np.exp(np.cumsum(rng.normal(0.00025, 0.010, n)))
    div = np.exp(np.arange(n) * (0.015 / 252.0))
    return {
        "seed": seed, "index": idx,
        "price": pd.Series(px, index=idx),                      # structure basis
        "tr": pd.Series(px * div, index=idx),                   # feature/RS basis
        "bench_px": pd.Series(bpx, index=idx),
        "bench_tr": pd.Series(bpx * np.exp(np.arange(n) * (0.013 / 252.0)), index=idx),
    }


def month_end_grid(tape: dict, warmup_months: int = SYNTH_WARMUP_MONTHS
                   ) -> pd.DatetimeIndex:
    """Every month-end after warm-up (both sides need the warm-up rows)."""
    idx = tape["index"]
    start = idx[min(int(warmup_months * 21), len(idx) - 1)]
    return pd.date_range(start=start.strftime("%Y-%m"), end=idx[-1].strftime("%Y-%m"),
                         freq="ME")


# ─────────────────────────────────────────────────────────────────────────────
# Training side — the W4.2 panel row at the as-of, via imported functions
# ─────────────────────────────────────────────────────────────────────────────

def training_side(tape: dict, month_ends: pd.DatetimeIndex, iid: str = "XTST"
                  ) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Panel rows + build_design vectors at each month-end (PIT by construction).

    Single-instrument panel: the family-median pool degenerates to the instrument's
    own median (disclosed in the report).  regime_hist is EMPTY so quad/liquidity
    read None exactly as the live sector record does (never stamped).
    Returns (design_frame, rows_index_of_asofs).
    """
    panel, fit = panel_module(), fit_module()
    turns = panel._detect_turns_for_instrument(tape["price"], iid, panel.ZZ_PCT_US)
    regime = pd.DataFrame({"quad": pd.Series(dtype=object),
                           "liquidity": pd.Series(dtype=object)},
                          index=pd.DatetimeIndex([]))
    rows: list[dict] = []
    kept: list[pd.Timestamp] = []
    for asof in month_ends:
        r = panel._build_instrument_rows(
            iid, "us_sector", tape["tr"], panel.ZZ_PCT_US,
            pd.DatetimeIndex([asof]), turns,
            per_id_medians_fn=lambda _iid, t: panel._compute_half_medians(
                {iid: turns}, t)[iid],
            family_median_fn=lambda direction, t: panel._family_half_medians(
                panel._compute_half_medians({iid: turns}, t), direction),
            regime_hist=regime, bench_close=tape["bench_tr"],
            turn_def_ver="price_c4414dcb", engine_fp="hazard_parity",
        )
        if r:
            rows.extend(r)
            kept.append(pd.Timestamp(asof))
    if not rows:
        return pd.DataFrame(), pd.DatetimeIndex([])
    design = fit.build_design(pd.DataFrame(rows))
    return design, pd.DatetimeIndex(kept)


# ─────────────────────────────────────────────────────────────────────────────
# Live side — the exact _stamp_hazard inputs on a record from the live builder
# ─────────────────────────────────────────────────────────────────────────────

_SYNTH_META = {"name": "Synthetic", "short": "Syn", "group": "Growth", "accent": "#38bdf8"}


def live_record(tape: dict, asof: pd.Timestamp, iid: str = "XTST",
                meta: dict | None = None) -> dict | None:
    """A real live record (build_sector) on the tape truncated at the as-of."""
    import engine.sector_cycles as sc
    tr = tape["tr"][tape["tr"].index <= asof]
    btr = tape["bench_tr"][tape["bench_tr"].index <= asof]
    px = tape["price"][tape["price"].index <= asof]
    bpx = tape["bench_px"][tape["bench_px"].index <= asof]
    closes = pd.DataFrame({iid: tr, "SPY": btr})
    closes_px = pd.DataFrame({iid: px, "SPY": bpx})
    return sc.build_sector(iid, meta or _SYNTH_META, closes,
                           closes.index[0] - pd.Timedelta(days=1),
                           closes_px=closes_px)


def live_inputs(rec: dict, family: str = "sector") -> tuple[dict, str, object, object]:
    """The exact (hf, direction, quad, liq_expanding) _stamp_hazard scores with."""
    import engine.sector_cycles as sc
    return sc._live_hazard_inputs(rec, family)


def live_side(tape: dict, month_ends: pd.DatetimeIndex, iid: str = "XTST"
              ) -> tuple[list[dict], list[pd.Timestamp], list[str]]:
    """Per-as-of {asof, vec, direction, phase, basis} from the live builder.

    vec = hazard_score._build_feature_vector on the exact live inputs (the same
    vector construction the scorer performs inside score()).
    """
    from engine.hazard_score import _build_feature_vector
    out: list[dict] = []
    kept: list[pd.Timestamp] = []
    bases: list[str] = []
    for asof in month_ends:
        rec = live_record(tape, pd.Timestamp(asof), iid=iid)
        if rec is None:
            continue
        hf, direction, quad, liq = live_inputs(rec, "sector")
        vec = _build_feature_vector(hf, direction, "sector", quad, liq)
        if vec is None:
            continue
        out.append({"asof": pd.Timestamp(asof), "vec": vec, "direction": direction,
                    "phase": (rec.get("now") or {}).get("phase"),
                    "hf": hf})
        kept.append(pd.Timestamp(asof))
        bases.append(rec.get("basis") or "unknown")
    return out, kept, bases


# ─────────────────────────────────────────────────────────────────────────────
# Comparison — pure functions
# ─────────────────────────────────────────────────────────────────────────────

def compare_vectors(train_vec: dict[str, float], live_vec: dict[str, float],
                    direction: str) -> dict[str, dict]:
    """Per-_DESIGN-feature comparison of ONE training vector vs ONE live vector.

    Returns {feature: {match, diff, diff_sd}} — diff_sd None for exact features.
    """
    from engine.hazard_score import _DESIGN
    sd = _MU_SD.get(direction, _MU_SD["up"])["sd"]
    out: dict[str, dict] = {}
    for feat in _DESIGN:
        tv, lv = float(train_vec.get(feat, 0.0)), float(live_vec.get(feat, 0.0))
        diff = tv - lv
        if feat in _EXACT_FEATURES:
            out[feat] = {"match": diff == 0.0, "diff": diff, "diff_sd": None}
        else:
            dsd = abs(diff) / max(sd.get(feat, 1.0), 1e-9)
            out[feat] = {"match": dsd <= _MATCH_SD, "diff": diff, "diff_sd": dsd}
    return out


def direction_check(pairs: list[tuple[str, str]]) -> dict:
    """Agreement count over (training_direction, live_direction) per as-of."""
    agree = sum(1 for t, l in pairs if t == l)
    return {"n": len(pairs), "agree": agree, "disagree": len(pairs) - agree,
            "agree_frac": round(agree / len(pairs), 4) if pairs else None}


def basis_epoch_checks(tape: dict, live_bases: list[str]) -> dict:
    """Turn-detection basis/threshold/version/epoch on each side vs the artifact."""
    from engine.hazard_score import _EPOCH
    import engine.cycle_ontology as onto
    panel = panel_module()
    train_epoch = onto.turn_epoch(basis="close_price", zz_params=float(panel.ZZ_PCT_US),
                                  detector_version=2)
    live = {
        "detector": f"{_L}:_detect_swings (zigzag v1 — no confirmed_at, NP-6 seed fix absent)",
        "pct": 14.0, "basis": (sorted(set(live_bases)) if live_bases else []),
        "feature_price_basis": "structure (price) for pos/osc_slope/trend_pass/amp; TR for rs_63d",
        "epoch_stamp": None,
    }
    train = {
        "detector": f"{_O}:detect_turns (zigzag v2, confirmed_at PIT)",
        "pct": float(panel.ZZ_PCT_US), "basis": "close_price",
        "feature_price_basis": "TR close for features; close_price for turns",
        "epoch_stamp": train_epoch,
    }
    artifact = {"turn_def_version": _EPOCH}
    return {
        "training": train, "live": live, "artifact": artifact,
        "training_epoch_matches_artifact": train_epoch == _EPOCH,
        # The live record carries NO turn epoch; the epoch on a stamped score block
        # is asserted by the scorer constant, never measured from the live turn set.
        "live_epoch_matches_artifact": False,
        "detector_version_agrees": False,   # v1 live vs v2 training
        "note": ("live turn set is produced by a different detector version with no "
                 "epoch stamp and no confirmed_at; the score block's epoch is the "
                 "scorer's own constant, so epoch parity cannot be established live"),
    }


def verdict_from(features_match: dict[str, bool], direction: dict,
                 basis_epoch: dict) -> tuple[str, list[str]]:
    """PARITY_HOLDS iff every feature MATCHes and direction, basis and epoch agree."""
    failing = [f for f, ok in features_match.items() if not ok]
    if direction.get("disagree"):
        failing.append("direction")
    if not (basis_epoch.get("live_epoch_matches_artifact")
            and basis_epoch.get("detector_version_agrees")):
        failing.append("basis_epoch")
    return ("PARITY_HOLDS" if not failing else "PARITY_FAILS", failing)


# ─────────────────────────────────────────────────────────────────────────────
# The report
# ─────────────────────────────────────────────────────────────────────────────

def parity_report(tape: dict | None = None, warmup_months: int = SYNTH_WARMUP_MONTHS,
                  iid: str = "XTST") -> dict:
    """Full parity report (schema sector_cycles.hazard_parity.v1) on one tape."""
    from engine.hazard_score import _DESIGN
    if tape is None:
        tape = synthetic_tape()
    mes = month_end_grid(tape, warmup_months)

    design, t_kept = training_side(tape, mes, iid=iid)
    lrows, l_kept, bases = live_side(tape, mes, iid=iid)

    t_by_asof = {pd.Timestamp(r["date"]).normalize(): r for _, r in design.iterrows()}
    l_by_asof = {r["asof"].normalize(): r for r in lrows}
    common = [a for a in mes if a in t_by_asof and a in l_by_asof]

    per: dict[str, list] = {f: [] for f in _DESIGN}
    dir_pairs: list[tuple[str, str]] = []
    for a in common:
        cmp_ = compare_vectors(dict(t_by_asof[a]), dict(l_by_asof[a]["vec"]),
                               l_by_asof[a]["direction"])
        for f, cell in cmp_.items():
            per[f].append(cell)
        dir_pairs.append((str(t_by_asof[a]["direction"]), l_by_asof[a]["direction"]))

    feats_out: list[dict] = []
    for f in _DESIGN:
        cells = per[f]
        n = len(cells)
        worst_sd = max((c["diff_sd"] for c in cells if c["diff_sd"] is not None),
                       default=None)
        worst_raw = max((abs(c["diff"]) for c in cells), default=None)
        match = bool(cells) and all(c["match"] for c in cells)
        sc_ = STATIC_CLASSES.get(f, {})
        feats_out.append({
            "feature": f, "static_class": sc_.get("class"),
            "match": match, "n_asof": n,
            "worst_abs_diff_sd": (round(worst_sd, 4) if worst_sd is not None else None),
            "worst_abs_diff": (round(worst_raw, 6) if worst_raw is not None else None),
            "training_source": sc_.get("training"), "live_source": sc_.get("live"),
        })

    dir_out = direction_check(dir_pairs)
    be = basis_epoch_checks(tape, bases)
    verdict, failing = verdict_from({r["feature"]: r["match"] for r in feats_out},
                                    dir_out, be)
    return {
        "schema": PARITY_SCHEMA,
        "version": 1,
        "measured_on": BASE_SHA,
        "input": {
            "kind": "seeded_synthetic_daily_monthly_asofs",
            "seed": tape.get("seed"), "iid": iid, "family": "us_sector",
            "span": [str(tape["index"][0].date()), str(tape["index"][-1].date())],
            "warmup_months": warmup_months,
            "n_month_ends": int(len(mes)),
            "n_both_sides": len(common),
            "training_rows": int(len(design)), "live_records": len(lrows),
            "sd_source": _SD_SOURCE,
            "family_median_note": ("single-instrument panel — the k=6 family-median "
                                   "pool degenerates to the own median"),
        },
        "features": feats_out,
        "missing_value_policy": MISSING_VALUE_POLICY,
        "direction": dir_out,
        "basis_epoch": be,
        "verdict": verdict,
        "failing": failing,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Recorded verdict (frozen from the measurement run at BASE_SHA — see doc)
# ─────────────────────────────────────────────────────────────────────────────

LIVE_HAZARD_PARITY: dict = {
    "verdict": "PARITY_FAILS",
    "failing": ["age_b1", "age_b2", "age_b3", "age_b4", "age_b5", "log_age_ratio", "amp_proxy", "pos_osc_s", "osc_slope_s", "trend_pass", "mom_score", "rs_63d", "vol_pctile", "direction", "basis_epoch"],
    "measured_on": "a038b3f35aafd3acc8879212a25373d4c94510c2",
    "report": {
        "schema": "sector_cycles.hazard_parity.v1",
        "version": 1,
        "measured_on": "a038b3f35aafd3acc8879212a25373d4c94510c2",
        "input": {
            "kind": "seeded_synthetic_daily_monthly_asofs",
            "seed": 12,
            "iid": "XTST",
            "family": "us_sector",
            "span": ["2015-06-01", "2024-06-28"],
            "warmup_months": 30,
            "n_month_ends": 80,
            "n_both_sides": 80,
            "training_rows": 80,
            "live_records": 80,
            "sd_source": "data/hazard/model_price_c4414dcb.json:coefficients[dir].sd (frozen at base)",
            "family_median_note": "single-instrument panel — the k=6 family-median pool degenerates to the own median"
        },
        "features": [
            {
                "feature": "age_b1",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 1.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — age_m = days/30.44 since confirmed_at turn; _age_bucket ratio edges .5/.8/1.1/1.5",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs→engine/hazard_score.py:_age_buckets — bars = Δdecimal-yrs×252; cuts -.19/.45/.99/1.63"
            },
            {
                "feature": "age_b2",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 1.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — age_m = days/30.44 since confirmed_at turn; _age_bucket ratio edges .5/.8/1.1/1.5",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs→engine/hazard_score.py:_age_buckets — bars = Δdecimal-yrs×252; cuts -.19/.45/.99/1.63"
            },
            {
                "feature": "age_b3",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 1.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — age_m = days/30.44 since confirmed_at turn; _age_bucket ratio edges .5/.8/1.1/1.5",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs→engine/hazard_score.py:_age_buckets — bars = Δdecimal-yrs×252; cuts -.19/.45/.99/1.63"
            },
            {
                "feature": "age_b4",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 1.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — age_m = days/30.44 since confirmed_at turn; _age_bucket ratio edges .5/.8/1.1/1.5",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs→engine/hazard_score.py:_age_buckets — bars = Δdecimal-yrs×252; cuts -.19/.45/.99/1.63"
            },
            {
                "feature": "age_b5",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 1.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — age_m = days/30.44 since confirmed_at turn; _age_bucket ratio edges .5/.8/1.1/1.5",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs→engine/hazard_score.py:_age_buckets — bars = Δdecimal-yrs×252; cuts -.19/.45/.99/1.63"
            },
            {
                "feature": "log_age_ratio",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 0.218,
                "worst_abs_diff": 0.205147,
                "training_source": "scripts/build_hazard_panel.py:_log_age_ratio — ln(age_m / k=6 blended median, months)",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — ln(bars/252×12 ÷ median_half_yrs×12), proj median/2"
            },
            {
                "feature": "amp_proxy",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 3.307,
                "worst_abs_diff": 0.9443,
                "training_source": "scripts/build_hazard_panel.py:_amp_proxy — expanding pctile of 63d range/price (TR)",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — amp_leg_pct = last swing mag_pct/100 (open leg)"
            },
            {
                "feature": "pos_osc_s",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 1.6994,
                "worst_abs_diff": 0.42687,
                "training_source": "scripts/build_hazard_panel.py:_detrended_osc — SMA200 dev expanding pctile (TR) → scripts/fit_cycle_hazard.py:build_design /100",
                "live_source": "engine/sector_cycles.py:_detrended_osc — EMA252 detrend, 252-stochastic (price) → /100"
            },
            {
                "feature": "osc_slope_s",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 1.6121,
                "worst_abs_diff": 2.69185,
                "training_source": "scripts/build_hazard_panel.py:_osc_slope — panel osc.diff(21) → /10",
                "live_source": "engine/sector_cycles.py:_record_core — live osc 22-bar diff → /10"
            },
            {
                "feature": "trend_pass",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 1.0,
                "training_source": "scripts/build_hazard_panel.py:_trend_pass — close>SMA200 min100 (TR)",
                "live_source": "engine/sector_cycles.py:_record_core — struct[-1]>mean(struct[-200:]) (price)"
            },
            {
                "feature": "mom_score",
                "static_class": "PROXY",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 169.714,
                "worst_abs_diff": 33.7629,
                "training_source": "scripts/build_hazard_panel.py:_mom_score — 126d−21d own TR return (fraction)",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — mom_score = now.rs_63d (percent)"
            },
            {
                "feature": "rs_63d",
                "static_class": "DIFFERENT_DEFINITION",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 379.8206,
                "worst_abs_diff": 33.6597,
                "training_source": "scripts/build_hazard_panel.py:_rs_63d — rel. return vs bench (fraction)",
                "live_source": "engine/sector_cycles.py:_leadership — rs.pct_change(63)×100 (percent)"
            },
            {
                "feature": "vol_pctile",
                "static_class": "IMPUTED_CONSTANT",
                "match": False,
                "n_asof": 80,
                "worst_abs_diff_sd": 1.9322,
                "worst_abs_diff": 0.5789,
                "training_source": "scripts/build_hazard_panel.py:_rolling_vol_pctile — expanding pctile of 63d realized vol",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — None → engine/hazard_score.py:_build_feature_vector 0.42"
            },
            {
                "feature": "quad_Q2",
                "static_class": "ABSENT_LIVE",
                "match": True,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 0.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — regime_hist quad asof t",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — nw.quad never set → 0"
            },
            {
                "feature": "quad_Q3",
                "static_class": "ABSENT_LIVE",
                "match": True,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 0.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — regime_hist quad asof t",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — nw.quad never set → 0"
            },
            {
                "feature": "quad_Q4",
                "static_class": "ABSENT_LIVE",
                "match": True,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 0.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — regime_hist quad asof t",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — nw.quad never set → 0"
            },
            {
                "feature": "liq_expanding",
                "static_class": "ABSENT_LIVE",
                "match": True,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 0.0,
                "training_source": "scripts/build_hazard_panel.py:_build_instrument_rows — regime liquidity == 'expanding'",
                "live_source": "engine/sector_cycles.py:_live_hazard_inputs — nw.liq_expanding never set → 0"
            },
            {
                "feature": "fam_country",
                "static_class": "SAME_DEFINITION",
                "match": True,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 0.0,
                "training_source": "scripts/fit_cycle_hazard.py:build_design — family=='country'",
                "live_source": "engine/hazard_score.py:_FAM_DUMMIES — family 'sector' → 0"
            },
            {
                "feature": "fam_cn",
                "static_class": "SAME_DEFINITION",
                "match": True,
                "n_asof": 80,
                "worst_abs_diff_sd": None,
                "worst_abs_diff": 0.0,
                "training_source": "scripts/fit_cycle_hazard.py:build_design — family=='cn_sector'",
                "live_source": "engine/hazard_score.py:_FAM_DUMMIES — family 'sector' → 0"
            }
        ],
        "missing_value_policy": [
            {
                "field": "pos (pos_osc_s)",
                "training": "NaN → column median fill (build_design)",
                "live": "now.pos or 50.0 in _stamp_hazard; scorer refuses only on None"
            },
            {
                "field": "osc_slope (osc_slope_s)",
                "training": "NaN → column median fill (build_design)",
                "live": "now.osc_slope or 0.0 in _stamp_hazard"
            },
            {
                "field": "amp_leg_pct (amp_proxy)",
                "training": "NaN → column median fill (build_design)",
                "live": "None → scorer constant 0.42 (model mu)"
            },
            {
                "field": "mom_score",
                "training": "NaN → column median fill (build_design)",
                "live": "None → 0.0 (scorer `or 0.0`)"
            },
            {
                "field": "rs_63d",
                "training": "NaN → column median fill (build_design)",
                "live": "None → 0.0 (scorer `or 0.0`)"
            },
            {
                "field": "vol_pctile",
                "training": "NaN → column median fill (build_design)",
                "live": "always None live → constant 0.42 (IMPUTED_CONSTANT)"
            },
            {
                "field": "trend_pass",
                "training": "NaN → column median fill (build_design fill list)",
                "live": "now.above200d or 0.0 (scorer `or 0.0`)"
            },
            {
                "field": "age / median_half_yrs (age buckets, log_age_ratio)",
                "training": "log_age_ratio NaN → b_unknown (all dummies 0) + median fill of the ratio",
                "live": "age_since_turn_bars None or median_half_yrs ≤ 0 → scorer REFUSES to score (returns None)"
            },
            {
                "field": "quad / liquidity dummies",
                "training": "NaN regime → 0 via == comparison",
                "live": "None → 0 (ABSENT_LIVE)"
            }
        ],
        "direction": {"n": 80, "agree": 36, "disagree": 44, "agree_frac": 0.45},
        "basis_epoch": {
            "training": {"detector": "engine/cycle_ontology.py:detect_turns (zigzag v2, confirmed_at PIT)", "pct": 14.0, "basis": "close_price", "feature_price_basis": "TR close for features; close_price for turns", "epoch_stamp": "price_c4414dcb"},
            "live": {
                "detector": "engine/sector_cycles.py:_detect_swings (zigzag v1 — no confirmed_at, NP-6 seed fix absent)",
                "pct": 14.0,
                "basis": ["price"],
                "feature_price_basis": "structure (price) for pos/osc_slope/trend_pass/amp; TR for rs_63d",
                "epoch_stamp": None
            },
            "artifact": {"turn_def_version": "price_c4414dcb"},
            "training_epoch_matches_artifact": True,
            "live_epoch_matches_artifact": False,
            "detector_version_agrees": False,
            "note": "live turn set is produced by a different detector version with no epoch stamp and no confirmed_at; the score block's epoch is the scorer's own constant, so epoch parity cannot be established live"
        },
        "verdict": "PARITY_FAILS",
        "failing": [
            "age_b1",
            "age_b2",
            "age_b3",
            "age_b4",
            "age_b5",
            "log_age_ratio",
            "amp_proxy",
            "pos_osc_s",
            "osc_slope_s",
            "trend_pass",
            "mom_score",
            "rs_63d",
            "vol_pctile",
            "direction",
            "basis_epoch"
        ]
    },
}
