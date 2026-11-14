"""Risk Radar walk-forward refit harness — PREREG_WALKFORWARD_v1 (frozen 2026-11-12).

Research-only. Nothing here sizes, ranks, gates or executes. Implements the frozen prereg:

- §1 folds: expanding fit window from 2020-01-02, matured labels only, one continuous
  score stream (the resolver is memoryless per row).
- §2 two fitted quantities: the context-gate breadth cut ``g`` in {0.30, 0.40, 0.50, None}
  and one band offset ``delta`` applied to all four bands, chosen per ``g`` as the value whose
  loud share (elevated or risk-off) on the fit window is closest to 15% (ties -> smaller |delta|).
- §3 fit objective J = tops flagged + bottoms flagged - 0.5 x (false risk-off + premature
  all-clears) on the fit window; the shipped default (g=0.40, delta=0) is retained unless the
  fit window has >= 4 matured scored turns and J(best) - J(default) >= 1.
- §5 proofs are in tests/test_risk_radar_eval.py (label maturity, feature prefix invariance,
  parameter intervention, calendar, effective-state hash).
- §6 outputs under data/risk_radar/ and research/risk_radar/walkforward/.

The harness injects its own gate series; it never reads ``context_gate_series``. Signals are
injectable (``run(signals=...)``) so a corrected availability lag is a one-argument change.

Usage:
    python3 -m engine.risk_radar_eval.walkforward
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from engine import risk_radar as rr
from engine.risk_radar_eval import inputs as I
from engine.risk_radar_eval import labels as L
from engine.risk_radar_eval import pivots as P
from engine.risk_radar_eval import scorecard as S

ROOT = Path(__file__).resolve().parents[2]
WALK_DIR = ROOT / "research" / "risk_radar" / "walkforward"
PREREG_PATH = WALK_DIR / "PREREG_WALKFORWARD_v1.md"
PREREG_SHA_PATH = WALK_DIR / "PREREG_WALKFORWARD_v1.sha256"
OUT_DATA_DIR = ROOT / "data" / "risk_radar"
OUT_STATE_JSON = OUT_DATA_DIR / "walkforward_state_series.json"
OUT_ALERT_CSV = OUT_DATA_DIR / "walkforward_alert_series.csv"
OUT_FOLDS_JSON = WALK_DIR / "WALKFORWARD_FOLDS_v1.json"
OUT_SCORECARD_JSON = WALK_DIR / "WALKFORWARD_SCORECARD_OOS_v1.json"

FIT_START = pd.Timestamp("2020-01-02")
OOS_START = pd.Timestamp("2022-01-03")
SEEN_HISTORY_FROM = pd.Timestamp("2024-01-02")
LOUD = ("elevated", "risk-off")
DEPTH = 0.05                     # fit objective uses >=5% SPY total-return episodes
PRE, POST, MIN_OFF = 21, 10, 10  # frozen fit/pivot windows
GATES = (0.30, 0.40, 0.50, None)  # prereg §2 (the one outcome-fitted degree of freedom)
DELTAS = tuple(range(-10, 11, 2))  # prereg §2, outcome-free band offset
DEFAULT_G, DEFAULT_DELTA = 0.40, 0.0
TARGET_LOUD = 0.15
MIN_SCORED_TURNS = 4
MIN_J_GAIN = 1.0
DEPTHS_REPORT = (0.10, 0.07, 0.05)  # >=10 / >=7 / >=5% order (parent steer 2026-11-12)
POSTS = (5, 10, 21)

# §1. F26's score_end is the last common date of the inputs; None = resolve at run time.
FOLDS = (
    {"name": "F22", "fit_end": "2021-12-31", "score_start": "2022-01-03",
     "score_end": "2022-12-30"},
    {"name": "F23", "fit_end": "2022-12-30", "score_start": "2023-01-03",
     "score_end": "2023-12-29"},
    {"name": "F24", "fit_end": "2023-12-29", "score_start": "2024-01-02",
     "score_end": "2024-12-31"},
    {"name": "F25", "fit_end": "2024-12-31", "score_start": "2025-01-02",
     "score_end": "2025-12-31"},
    {"name": "F26", "fit_end": "2025-12-31", "score_start": "2026-01-02",
     "score_end": None},
)


# ---------------------------------------------------------------------------------------------
# hashes / metadata
# ---------------------------------------------------------------------------------------------
def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), check=True,
                              capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001 — metadata must never break a fit
        return "UNKNOWN"


def prereg_sha() -> dict:
    """Recorded prereg hash, plus whether the frozen file still matches it."""
    recorded = None
    if PREREG_SHA_PATH.exists():
        recorded = PREREG_SHA_PATH.read_text().split()[0].strip()
    actual = None
    if PREREG_PATH.exists():
        actual = hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest()
    return {"prereg_sha256": recorded, "actual_file_sha256": actual,
            "prereg_unmodified": bool(recorded and actual and recorded == actual)}


def _sha_payload(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str)
                          .encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------
# §2 parameter mechanics
# ---------------------------------------------------------------------------------------------
def bands_with_delta(calib: dict, delta: float) -> dict:
    """Copy the calibration and add ``delta`` to every band."""
    bands = {k: float(v) + float(delta) for k, v in calib["bands"].items()}
    return bands


def score_window_seen(fold: dict) -> bool:
    """A fold is seen history when its SCORE window reaches 2024-01-02 or later (an open
    score_end counts as reaching it). The fit end is not the test: F24 fits through 2023-12-29
    but scores 2024, which is the Radar's own seen history (#11137 review, 2026-11-12)."""
    end = fold.get("score_end")
    start = pd.Timestamp(fold["score_start"])
    return bool(end is None or pd.Timestamp(end) >= SEEN_HISTORY_FROM
                or start >= SEEN_HISTORY_FROM)


def effective_state(fold: str, g: float | None, delta: float, calib: dict) -> dict:
    """Effective-state hash record (prereg §5.6): g, delta, bands, code commit, prereg hash."""
    bands = bands_with_delta(calib, delta)
    core = {"fold": fold, "g": g, "delta": float(delta), "bands": bands,
            "code_commit": _git_commit(), **prereg_sha()}
    core["effective_state_sha256"] = _sha_payload(
        {k: core[k] for k in ("fold", "g", "delta", "bands", "code_commit", "prereg_sha256")})
    return core


def states_for(subs: pd.DataFrame, sigs: pd.DataFrame, calib: dict,
               gate: pd.Series | None, delta: float) -> pd.Series:
    """Daily state under an injected gate and band offset. Never reads the module gate constant.

    ``gate`` is a bool series indexed like ``subs``; None means the gate is always met. Each row
    is resolved by the live transition owner ``_resolve_state_row``.
    """
    calib2 = {k: (dict(v) if isinstance(v, dict) else v) for k, v in calib.items()}
    calib2["bands"] = bands_with_delta(calib, delta)
    sigs = sigs.reindex(subs.index)
    values = []
    for day, subrow in subs.iterrows():
        sigrow = sigs.loc[day] if day in sigs.index else pd.Series(dtype=float)
        gate_met = True if gate is None else bool(gate.get(day, False))
        values.append(rr._resolve_state_row(subrow, sigrow, calib2, gate_met=gate_met)["state"])
    return pd.Series(values, index=subs.index, dtype=object, name="state")


def loud_share(states: pd.Series) -> float:
    return float(states.isin(LOUD).mean()) if len(states) else float("nan")


def pick_delta(states_by_delta: dict[float, pd.Series]) -> tuple[float, dict]:
    """Closest loud share to 15%; ties -> smaller |delta| (then the smaller delta)."""
    shares = {d: loud_share(s) for d, s in states_by_delta.items()}
    chosen = min(shares, key=lambda d: (round(abs(shares[d] - TARGET_LOUD), 12), abs(d), d))
    return chosen, shares


# ---------------------------------------------------------------------------------------------
# §1/§3 matured fit labels and the J objective
# ---------------------------------------------------------------------------------------------
def fit_labels(px: pd.Series, fit_end, *, post: int = POST) -> tuple[list, list]:
    """Episodes (peaks >= 2020-01-02) and their MATURED turns at ``fit_end``.

    A top is used only if its window [top - pre, top + post] ends on or before the cutoff; a
    bottom only if its episode recovered on or before the cutoff and its window ends there too.
    Censored/open structures are refused, never scored as misses.
    """
    cut = pd.Timestamp(fit_end)
    episodes = L.drawdown_episodes(px, DEPTH, outcomes_through=cut)
    episodes = [e for e in episodes if e.peak >= FIT_START]
    idx = px.index
    pos = {d: i for i, d in enumerate(idx)}
    cut_pos = pos[idx[idx <= cut][-1]]
    turns = []
    for e in episodes:
        if pos[e.peak] + post <= cut_pos:
            turns.append(P.Turn("top", e.peak, e.depth, episode_onset=e.onset))
        if e.recovery is not None and e.recovery <= cut:
            if pos[e.trough] + post <= cut_pos:
                turns.append(P.Turn("bottom", e.trough, e.depth, episode_onset=e.onset))
    turns.sort(key=lambda t: t.date)
    return episodes, turns


def score_fit(alert: pd.Series, episodes: list, turns: list, fit_end) -> dict:
    """J on the fit window. ``alert`` must cover the fit window with no missing sessions."""
    r = P.score_pivots(alert, turns=turns, episodes=episodes, outcomes_through=fit_end,
                       pre=PRE, post=POST, min_off=MIN_OFF, sealed_from=None,
                       seen_history_ok=True, name="fit")
    tops, bots = r["top"]["flagged"], r["bottom"]["flagged"]
    j = (tops + bots) - 0.5 * (r["false_risk_off"] + r["premature_all_clear"])
    return {"J": float(j), "tops_flagged": int(tops), "bottoms_flagged": int(bots),
            "false_risk_off": int(r["false_risk_off"]),
            "premature_all_clear": int(r["premature_all_clear"]),
            "scored_turns": int(r["top"]["n_turns"] + r["bottom"]["n_turns"]),
            "censored_turns": int(r["top"]["censored"] + r["bottom"]["censored"])}


def _fit_index(subs: pd.DataFrame, fit_end) -> pd.DatetimeIndex:
    return subs.index[(subs.index >= FIT_START) & (subs.index <= pd.Timestamp(fit_end))]


def fit_fold(fold: dict, subs: pd.DataFrame, sigs: pd.DataFrame, calib: dict,
             gate_components: pd.DataFrame, px: pd.Series) -> dict:
    """Search the four §2 candidates on one fold and return the chosen parameters."""
    fit_end = pd.Timestamp(fold["fit_end"])
    idx = _fit_index(subs, fit_end)
    subfit = subs.loc[idx]
    episodes, turns = fit_labels(px, fit_end)

    states_by_g: dict = {}
    candidates = []
    for g in GATES:
        gate = None if g is None else I.gate_series(gate_components, g).reindex(subs.index) \
            .fillna(False).astype(bool)
        by_delta = {d: states_for(subfit, sigs, calib, gate, d) for d in DELTAS}
        dsel, shares = pick_delta(by_delta)
        st = by_delta[dsel]
        res = score_fit(st.isin(LOUD), episodes, turns, fit_end)
        states_by_g[g] = (gate, by_delta[dsel])
        candidates.append({"g": g, "delta": float(dsel), "loud_share": shares[dsel],
                           "shares_by_delta": {str(d): shares[d] for d in DELTAS}, **res})

    # the shipped default, evaluated as declared (g=0.40, delta=0), not via the delta search
    gate_default, _ = states_by_g[DEFAULT_G]
    default_states = states_for(subfit, sigs, calib, gate_default, DEFAULT_DELTA)
    default = {"g": DEFAULT_G, "delta": DEFAULT_DELTA,
               "loud_share": loud_share(default_states),
               **score_fit(default_states.isin(LOUD), episodes, turns, fit_end)}

    # best candidate: default first on ties, then the smaller loud share
    best = max(candidates, key=lambda c: (c["J"],
                                          c["g"] == DEFAULT_G and c["delta"] == DEFAULT_DELTA,
                                          -c["loud_share"]))

    gain = best["J"] - default["J"]
    if default["scored_turns"] < MIN_SCORED_TURNS:
        chosen = dict(default)
        reason = (f"retained default: fit window has {default['scored_turns']} matured scored "
                  f"turns < {MIN_SCORED_TURNS}")
    elif gain < MIN_J_GAIN:
        chosen = dict(default)
        reason = (f"retained default: J(best)-J(default)={gain:+.1f} < {MIN_J_GAIN:.0f} "
                  f"(best g={best['g']}, delta={best['delta']:+.0f})")
    else:
        chosen = {k: best[k] for k in ("g", "delta", "loud_share", "J", "tops_flagged",
                                       "bottoms_flagged", "false_risk_off",
                                       "premature_all_clear", "scored_turns", "censored_turns")}
        reason = (f"adopted g={best['g']}, delta={best['delta']:+.0f}: "
                  f"J={best['J']:.1f} vs default {default['J']:.1f} (gain {gain:+.1f})")

    return {
        "name": fold["name"],
        "fit_window": [FIT_START.date().isoformat(), fit_end.date().isoformat()],
        "fit_cutoff": fit_end.date().isoformat(),
        "score_window": [fold["score_start"], fold["score_end"]],
        "seen_history": score_window_seen(fold),
        "n_fit_sessions": int(len(idx)),
        "n_fit_episodes": len(episodes),
        "n_fit_labels": len(turns),
        "candidates": candidates,
        "default": default,
        "chosen": chosen,
        "reason": reason,
        "effective_state": effective_state(fold["name"], chosen["g"], chosen["delta"], calib),
    }


# ---------------------------------------------------------------------------------------------
# §6 outputs
# ---------------------------------------------------------------------------------------------
def build_header(fits: list[dict], input_last_dates: dict | None = None,
                 signals_note: str | None = None) -> dict:
    """Steps 6 header: prereg hash, code commit, per-fold effective state, input last dates."""
    return {
        "prereg": str(PREREG_PATH.relative_to(ROOT)),
        **prereg_sha(),
        "code_commit": _git_commit(),
        "generated_utc": pd.Timestamp.now("UTC").isoformat(),
        "signals": signals_note or "inputs.incumbent_signals() (availability lag applied)",
        "folds": [{k: f["effective_state"][k] for k in
                   ("fold", "g", "delta", "bands", "effective_state_sha256")}
                  | {"effective_state": f["effective_state"]} for f in fits],
        "input_last_dates": input_last_dates or {},
        "leg_availability_note": "per-session non-NaN legs are on each state row",
    }


def _fold_window(fold: dict, last_common: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(fold["score_start"])
    end = last_common if fold["score_end"] is None else min(pd.Timestamp(fold["score_end"]),
                                                           last_common)
    return start, end


def _slim(res: dict) -> dict:
    out = {k: v for k, v in res.items() if k not in ("turns", "by_regime")}
    if not out.get("by_regime"):
        out.pop("by_regime", None)
    return out


def _series_block(alerts: dict[str, pd.Series], episodes: list, cut, posts=POSTS,
                  ref_name: str = "base_mech_near_high_1pct") -> dict:
    """Score every series per post; keep the full results for beyond_reference, then slim."""
    turns = P.turns_from_episodes(episodes)
    block: dict = {}
    for post in posts:
        full = {name: P.score_pivots(a, turns=turns, episodes=episodes, outcomes_through=cut,
                                     pre=PRE, post=post, min_off=MIN_OFF, sealed_from=None,
                                     seen_history_ok=True, name=name)
                for name, a in alerts.items()}
        ref = full.get(ref_name)
        beyond = {}
        if ref is not None:
            for name, r in full.items():
                beyond[name] = {kind: P.beyond_reference(r, ref, kind=kind)
                                for kind in ("top", "bottom")}
        block[f"post{post}"] = {name: _slim(r) for name, r in full.items()}
        if beyond:
            block[f"post{post}"]["beyond_reference"] = {
                "reference": ref_name,
                "note": "early catches (delay<0) of each series beyond the mechanical reference; "
                        "secondary read, no significance claim",
                "by_series": beyond}
    return block


def _placebo_bundle(series: dict[str, pd.Series], *, px, episodes, cut, n_draws, seed,
                    tol=0.01) -> dict:
    turns = P.turns_from_episodes(episodes)
    out = {}
    for name, alert in series.items():
        out[name] = {}
        for near in ("high", "low"):
            out[name][near] = P.placebo(alert, px=px, turns=turns, episodes=episodes,
                                        outcomes_through=cut, near=near, tol=tol,
                                        n_draws=n_draws, seed=seed, pre=PRE, post=POST,
                                        min_off=MIN_OFF, sealed_from=None,
                                        seen_history_ok=True)
    return out


def _insurer_appendix(wf_loud: pd.Series, shipped_loud: pd.Series, px: pd.Series,
                      cut) -> dict:
    from engine.risk_radar_eval import insurer
    idx = wf_loud.index
    spy_ret = px.reindex(idx.union(px.index)).sort_index().pct_change().reindex(idx)
    bill = insurer.bill_returns(idx)
    wf_ret = insurer.sleeve_returns(wf_loud, spy_ret, bill)
    sh_ret = insurer.sleeve_returns(shipped_loud, spy_ret, bill)
    profiles = {
        "walkforward_loud": insurer.profile(wf_ret, spy_ret=spy_ret, bill_ret=bill, px=px,
                                            outcomes_through=cut, name="walkforward_loud"),
        "shipped_v2_loud": insurer.profile(sh_ret, spy_ret=spy_ret, bill_ret=bill, px=px,
                                           outcomes_through=cut, name="shipped_v2_loud"),
    }
    comps = insurer.comparators(idx, spy_ret=spy_ret, bill_ret=bill, match_vol_of=wf_ret)
    for name, ret in comps.items():
        profiles[name] = insurer.profile(ret, spy_ret=spy_ret, bill_ret=bill, px=px,
                                         outcomes_through=cut, name=name)
    return {"note": "descriptive appendix only; never a trading rule or sizing input",
            "exec_lag": 1, "profiles": profiles}


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.date().isoformat()
    return str(o)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, default=_json_default), encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------------------------
def run(out_dir: str | Path | None = None, signals=None, *,
        placebo_draws: int = 2000, placebo_seed: int = 0) -> dict:
    """Fit every fold, build the continuous walk-forward stream, score it out of sample.

    ``signals``: a DataFrame of leg percentiles or a callable returning one. Default is
    ``inputs.incumbent_signals()`` (current publication-lag treatment). Corrected availability
    lags drop in here without touching the harness.
    """
    out_dir = Path(out_dir) if out_dir is not None else OUT_DATA_DIR
    if callable(signals):
        sigs = signals()
    elif signals is None:
        sigs = I.incumbent_signals()
    else:
        sigs = signals
    sigs = sigs.copy()
    signals_note = ("injected signals" if signals is not None
                    else "inputs.incumbent_signals() (availability lag applied)")

    calib = rr._calib()
    subs = rr.subscore_series(sigs, calib)
    gate_components = I.gate_components()
    px = L.spy_total_return()
    last_common = min(subs.index.max(), sigs.index.max(), px.index.max(),
                      gate_components.index.max())
    last_common = min(last_common, pd.Timestamp.today().normalize())
    last_common = px.index[px.index <= last_common].max()

    folds = [dict(f) for f in FOLDS]
    fits = [fit_fold(f, subs, sigs, calib, gate_components, px) for f in folds]

    # ---- one continuous walk-forward stream, each score window on its own fold's parameters
    wf_states: dict[pd.Timestamp, str] = {}
    wf_meta: dict[pd.Timestamp, dict] = {}
    for f, fit in zip(folds, fits):
        start, end = _fold_window(f, last_common)
        fit["score_window"] = [start.date().isoformat(), end.date().isoformat()]
        idx = subs.index[(subs.index >= start) & (subs.index <= end)]
        if not len(idx):
            continue
        g, delta = fit["chosen"]["g"], fit["chosen"]["delta"]
        gate = None if g is None else I.gate_series(gate_components, g).reindex(subs.index) \
            .fillna(False).astype(bool)
        st = states_for(subs.loc[idx], sigs, calib, gate, delta)
        for day, state in st.items():
            wf_states[day] = state
            wf_meta[day] = {"fold": fit["name"], "g": g, "delta": delta,
                            "fit_cutoff": fit["fit_cutoff"]}
    oos_idx = pd.DatetimeIndex(sorted(d for d in wf_states if d >= OOS_START))
    wf_loud = pd.Series([wf_states[d] in LOUD for d in oos_idx], index=oos_idx, name="loud")

    # shipped v2 comparator: same injected-gate path, frozen constants
    gate_ship = I.gate_series(gate_components, DEFAULT_G).reindex(subs.index).fillna(False)
    ship_states = states_for(subs.loc[oos_idx], sigs, calib, gate_ship, DEFAULT_DELTA)
    ship_loud = ship_states.isin(LOUD).rename("loud")

    # ---- HY OAS budget-calibrated analogue: threshold per fold on its FIT window
    hy = I.baseline_scores()["hy_oas_chg21_pct"]
    hy_budget = pd.Series(False, index=oos_idx, dtype=bool)
    for f, fit in zip(folds, fits):
        start, end = _fold_window(f, last_common)
        fend = pd.Timestamp(f["fit_end"])
        fit_idx = _fit_index(subs, fend)
        thr = S.threshold_for_budget(hy.reindex(fit_idx), fit["chosen"]["loud_share"])
        win = hy_budget.index[(hy_budget.index >= start) & (hy_budget.index <= end)]
        hy_budget.loc[win] = (hy.reindex(win) >= thr).fillna(False).astype(bool)
        fit["hy_oas_budget"] = {"threshold": round(float(thr), 6),
                                "fit_budget_target": fit["chosen"]["loud_share"],
                                "score_window_budget": round(float(hy_budget.loc[win].mean()), 4)
                                if len(win) else None}

    # ---- state series output
    legs = sigs.reindex(oos_idx)
    avail = legs.notna()
    rows = []
    for d in oos_idx:
        meta = wf_meta[d]
        rows.append({
            "date": d.date().isoformat(),
            "fold": meta["fold"],
            "g": meta["g"],
            "delta": meta["delta"],
            "state": wf_states[d],
            "loud": bool(wf_states[d] in LOUD),
            "legs_available": [c for c in avail.columns if bool(avail.at[d, c])],
            "design_seen": True,
            "fit_cutoff": meta["fit_cutoff"],
            "seen_history": bool(d >= SEEN_HISTORY_FROM),
        })
    input_last_dates = {
        "spy_total_return": px.index.max().date().isoformat(),
        "signals": sigs.index.max().date().isoformat(),
        "gate_components": gate_components.index.max().date().isoformat(),
        "subscores": subs.index.max().date().isoformat(),
        "hy_oas_21d_pct": hy.dropna().index.max().date().isoformat() if hy.notna().any() else None,
        "last_common": last_common.date().isoformat(),
    }
    header = build_header(fits, input_last_dates=input_last_dates, signals_note=signals_note)
    header["state_stream"] = {"window": [oos_idx.min().date().isoformat(),
                                         oos_idx.max().date().isoformat()],
                              "n_rows": int(len(rows)),
                              "realized_budget": round(float(wf_loud.mean()), 4),
                              "shipped_v2_budget": round(float(ship_loud.mean()), 4)}
    _write_json(out_dir / OUT_STATE_JSON.name, {"header": header, "rows": rows})

    # ---- alert CSV with its realized budget in a header comment
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / OUT_ALERT_CSV.name).open("w", encoding="utf-8") as fh:
        fh.write(f"# realized_budget={float(wf_loud.mean()):.6f} "
                 f"n_sessions={len(wf_loud)} "
                 f"window={oos_idx.min().date().isoformat()}..{oos_idx.max().date().isoformat()} "
                 f"prereg={prereg_sha()['prereg_sha256']}\n")
        fh.write("date,loud\n")
        for d, v in wf_loud.items():
            fh.write(f"{d.date().isoformat()},{int(bool(v))}\n")

    # ---- fold search log
    _write_json(OUT_FOLDS_JSON, {
        **prereg_sha(), "code_commit": _git_commit(),
        "note": "every evaluated candidate is kept; the chosen row is repeated in `default` and "
                "`chosen` (default = shipped g=0.40, delta=0)",
        "folds": [dict({k: f[k] for k in ("name", "fit_window", "fit_cutoff", "score_window",
                                          "seen_history", "n_fit_sessions", "n_fit_episodes",
                                          "n_fit_labels", "candidates", "default", "chosen",
                                          "reason", "effective_state")},
                       hy_oas_budget=f.get("hy_oas_budget")) for f in fits]})

    # ---- out-of-sample scorecard: pivot read first
    flags = I.baseline_flags(I.baseline_scores()).reindex(oos_idx).fillna(False)
    oos_eps = [e for e in L.drawdown_episodes(px, DEPTH, outcomes_through=last_common)
               if e.peak >= OOS_START]
    pooled_alerts = {
        "walkforward_loud": wf_loud,
        "shipped_v2_loud": ship_loud.astype(bool),
        "hy_oas_budget_calibrated": hy_budget,
        **{f"base_{c}": flags[c].astype(bool) for c in
           ("hy_oas_chg21_top_decile", "spy_below_200", "vix_ge_20", "vix_ge_25",
            "mech_near_high_1pct", "mech_dd_ge_5pct")},
    }
    pivot_pooled: dict = {}
    for depth in DEPTHS_REPORT:
        eps = [e for e in L.drawdown_episodes(px, depth, outcomes_through=last_common)
               if e.peak >= OOS_START]
        pivot_pooled[f"dd{int(round(depth * 100))}"] = _series_block(pooled_alerts, eps,
                                                                     last_common)

    pivot_folds: dict = {}
    for f, fit in zip(folds, fits):
        start, end = _fold_window(f, last_common)
        win = oos_idx[(oos_idx >= start) & (oos_idx <= end)]
        if not len(win):
            continue
        fpx = px.loc[:end]
        alerts = {name: s.reindex(win) for name, s in pooled_alerts.items()}
        pivot_folds[f["name"]] = {
            f"dd{int(round(depth * 100))}": _series_block(
                alerts, [e for e in L.drawdown_episodes(fpx, depth, outcomes_through=end)
                         if start <= e.peak <= win.max()], end)
            for depth in DEPTHS_REPORT}

    # the ONLY out-of-sample line: 2022-01-03..2023-12-29 on its own (no 2024+ outcome)
    oos_end = min(SEEN_HISTORY_FROM - pd.Timedelta(days=1), last_common)
    oos_only_idx = oos_idx[oos_idx <= oos_end]
    oos_only_end = oos_only_idx.max()
    pivot_oos_only = {
        f"dd{int(round(depth * 100))}": _series_block(
            {name: s.reindex(oos_only_idx) for name, s in pooled_alerts.items()},
            [e for e in L.drawdown_episodes(px.loc[:oos_only_end], depth,
                                            outcomes_through=oos_only_end)
             if OOS_START <= e.peak <= oos_only_end], oos_only_end)
        for depth in DEPTHS_REPORT}

    placebo = _placebo_bundle({"walkforward_loud": wf_loud,
                               "shipped_v2_loud": ship_loud.astype(bool)},
                              px=px, episodes=oos_eps, cut=last_common,
                              n_draws=placebo_draws, seed=placebo_seed, tol=0.01)

    # secondary: paper scorecard of the two loud states (never chooses anything)
    secondary = {}
    for name, a in (("walkforward_loud", wf_loud), ("shipped_v2_loud", ship_loud.astype(bool))):
        try:
            secondary[name] = S.score(a, px=px, outcomes_through=last_common,
                                      seen_history_ok=True, name=name)
        except Exception as exc:  # noqa: BLE001 — secondary never blocks the primary read
            secondary[name] = {"error": str(exc)}

    try:
        appendix = _insurer_appendix(wf_loud, ship_loud.astype(bool), px, last_common)
    except Exception as exc:  # noqa: BLE001 — descriptive appendix only
        appendix = {"error": str(exc), "note": "descriptive appendix only"}

    scorecard = {
        "pivot_read": {
            "note": "PRIMARY read. Pivots of >=10/7/5% SPY total-return episodes; "
                    "2024+ is the Radar's own seen history; 2022-2023 is out of sample. "
                    "Turn denominators include left/right-censored turns in `censored`.",
            "turn_catalogue": {
                "pooled": [e.as_dict() for e in oos_eps],
                "by_fold": {f["name"]: [e.as_dict() for e in
                                        L.drawdown_episodes(px.loc[:_fold_window(f, last_common)[1]],
                                                            DEPTH,
                                                            outcomes_through=_fold_window(f, last_common)[1])
                                        if _fold_window(f, last_common)[0] <= e.peak
                                        <= _fold_window(f, last_common)[1]]
                            for f in folds}},
            "pooled": pivot_pooled,
            "pooled_note": "pools out-of-sample 2022-23 with seen 2024+; NOT out of sample",
            "oos_2022_2023": pivot_oos_only,
            "oos_2022_2023_note": "the only out-of-sample line: 2022-01-03..2023-12-29, "
                                  "outcomes through 2023-12-29",
            "by_fold": pivot_folds,
        },
        "placebo": {"tol": 0.01, "n_draws": placebo_draws, "seed": placebo_seed,
                    "note": "tops are meaningful above near=high; bottoms above near=low",
                    **placebo},
        "secondary_scorecard": secondary,
        "meta": {
            "window": [oos_idx.min().date().isoformat(), oos_idx.max().date().isoformat()],
            "outcomes_through": last_common.date().isoformat(),
            "oos_and_seen_history": "2022-01-03..2023-12-29 out of sample; 2024+ seen history",
            **prereg_sha(), "code_commit": _git_commit(),
            "signals": signals_note,
            "folds": [{k: f[k] for k in ("name", "score_window", "chosen", "reason",
                                         "hy_oas_budget")} for f in fits],
            "budgets": {name: r.get("budget")
                        for dep in pivot_pooled.values()
                        for post, by_name in dep.items()
                        for name, r in by_name.items()
                        if isinstance(r, dict) and "budget" in r},
        },
        "appendix_descriptive": appendix,
    }
    _write_json(OUT_SCORECARD_JSON, scorecard)

    return {"state_json": str(out_dir / OUT_STATE_JSON.name),
            "alert_csv": str(out_dir / OUT_ALERT_CSV.name),
            "folds_json": str(OUT_FOLDS_JSON), "scorecard_json": str(OUT_SCORECARD_JSON),
            "folds": fits, "header": header, "oos_index": oos_idx}


def main() -> None:
    import sys
    out = run()
    print(out["state_json"])
    print(out["alert_csv"])
    print(out["folds_json"])
    print(out["scorecard_json"])
    sys.stdout.flush()


if __name__ == "__main__":
    main()
