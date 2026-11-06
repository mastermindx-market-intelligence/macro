"""Risk Radar caution-persistence display study.

Descriptive research only. Frozen protocol:
research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_PREREG_2026-09-21.md
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.risk_radar import _calib, leading_signals, subscore_series
from engine.risk_radar_backtest import _ORDER, _spy, detect_events, state_accuracy, state_series
from lib import store

OUT = ROOT / "research/grey_deer/evidence/caution-persistence-20260921"
PROTOCOL_COMMIT = "1882492ee09ef9baefbf0412aed175388c23c631"
SOURCE_BASE = "1dc11fb3eb326393c803bc2eff408db89bb91bc1"
def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def native_forward_labels(spy: pd.Series, idx: pd.DatetimeIndex, horizon=21, depth=.05):
    """Complete native-price windows matching corrected state_accuracy semantics."""
    pxs = spy.copy()
    if not isinstance(pxs.index, pd.DatetimeIndex) or not pxs.index.is_unique or not pxs.index.is_monotonic_increasing:
        raise ValueError("SPY observations require a unique ordered DatetimeIndex")
    bools = pxs.map(lambda value: isinstance(value, (bool, np.bool_)))
    px = pd.to_numeric(pxs, errors="coerce").where(~bools).to_numpy(dtype=float)
    good = np.isfinite(px) & (px > 0)
    rows = []
    for day, loc in zip(idx, pxs.index.get_indexer(idx)):
        if loc < 0 or loc + horizon >= len(px) or not good[loc:loc + horizon + 1].all():
            continue
        loss = float(px[loc + 1:loc + horizon + 1].min() / px[loc] - 1.)
        rows.append({"date": day, "end": pxs.index[loc + horizon],
                     "loss": loss, "event": bool(loss <= -depth)})
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(columns=["end","loss","event"])
def persistent_caution(caution_plus: pd.Series, known: pd.Series, sessions: int = 5) -> tuple[pd.Series, pd.Series]:
    """Return (persistent flag, eligible flag) on exact consecutive index observations."""
    if type(sessions) is not int or sessions <= 0:
        raise ValueError("sessions must be a positive integer")
    c = caution_plus.astype(bool)
    k = known.astype(bool)
    known_window = k.rolling(sessions, min_periods=sessions).sum().eq(sessions)
    caution_window = c.rolling(sessions, min_periods=sessions).sum().eq(sessions)
    return (caution_window & known_window).astype(bool), known_window.astype(bool)


def _metrics(alert: pd.Series, outcome: pd.Series, base_rate: float) -> dict:
    idx = alert.index.intersection(outcome.index)
    a = alert.reindex(idx).astype(bool)
    y = outcome.reindex(idx).astype(bool)
    tp = int((a & y).sum()); fp = int((a & ~y).sum())
    fn = int((~a & y).sum()); tn = int((~a & ~y).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2*precision*recall/(precision+recall) if precision and recall else 0.0
    return {
        "n": int(len(idx)), "event_rate": precision,
        "precision": precision, "recall": recall,
        "f1": float(f1) if len(idx) else None,
        "fire_rate": float(a.mean()) if len(idx) else None,
        "lift_vs_base": (precision / base_rate) if precision is not None and base_rate else None,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }
def _fingerprint(labels: pd.DataFrame) -> str:
    rows = [[d.isoformat(), row.end.isoformat(), float(row.loss).hex(), bool(row.event)]
            for d, row in labels.iterrows()]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def daily_result(state: pd.Series, known: pd.Series, labels: pd.DataFrame, *, lo=None) -> dict:
    caution_i = _ORDER.index("caution")
    caution = state.map(lambda s: s in _ORDER and _ORDER.index(s) >= caution_i)
    persistent, eligible_history = persistent_caution(caution, known, 5)
    idx = labels.index.intersection(state.index)
    idx = idx[known.reindex(idx).fillna(False) & eligible_history.reindex(idx).fillna(False)]
    if lo is not None:
        idx = idx[idx >= pd.Timestamp(lo)]
    y = labels.loc[idx, "event"].astype(bool)
    base_rate = float(y.mean()) if len(y) else float("nan")
    always = pd.Series(True, index=idx)
    out = {
        "from": idx[0].isoformat() if len(idx) else None,
        "through": idx[-1].isoformat() if len(idx) else None,
        "n": int(len(idx)),
        "events": int(y.sum()),
        "base_rate": None if not len(idx) else base_rate,
        "population_sha256": _fingerprint(labels.loc[idx]),
        "all_sessions": _metrics(always, y, base_rate),
        "caution_plus": _metrics(caution.reindex(idx), y, base_rate),
        "persistent_caution_5": _metrics(persistent.reindex(idx), y, base_rate),
    }
    return out
def _first_true(series: pd.Series):
    hits = series[series.fillna(False).astype(bool)]
    return hits.index[0] if len(hits) else None


def _offset(idx: pd.DatetimeIndex, anchor: pd.Timestamp, day) -> int | None:
    if day is None or anchor not in idx or day not in idx:
        return None
    return int(idx.get_loc(day) - idx.get_loc(anchor))


def _first_breach(spy: pd.Series, anchor: pd.Timestamp, depth=.05, horizon=21):
    loc = spy.index.get_loc(anchor)
    base = float(spy.iloc[loc])
    tail = spy.iloc[loc+1:loc+horizon+1]
    hits = tail[tail <= base * (1-depth)]
    return hits.index[0] if len(hits) else None


def event_result(spy: pd.Series, idx: pd.DatetimeIndex, state: pd.Series, known: pd.Series) -> dict:
    caution_i = _ORDER.index("caution")
    caution = state.map(lambda s: s in _ORDER and _ORDER.index(s) >= caution_i)
    persistent, eligible = persistent_caution(caution, known, 5)
    anchors = detect_events(spy.dropna(), fwd=21, depth=.05, min_gap=21)
    rows = []
    for anchor in anchors:
        if anchor not in idx or anchor not in spy.index:
            continue
        pos = idx.get_loc(anchor)
        if pos < 21 or pos + 21 >= len(idx):
            continue
        pre = idx[pos-21:pos+1]
        c_first = _first_true(caution.reindex(pre) & known.reindex(pre).fillna(False))
        p_first = _first_true(persistent.reindex(pre) & eligible.reindex(pre).fillna(False))
        breach = _first_breach(spy, anchor)
        p_left_censored = bool(p_first is not None and p_first == pre[0])
        rows.append({
            "anchor": anchor.isoformat(),
            "caution_first": c_first.isoformat() if c_first is not None else None,
            "persistent_first": p_first.isoformat() if p_first is not None else None,
            "caution_offset": _offset(idx, anchor, c_first),
            "persistent_offset": _offset(idx, anchor, p_first),
            "persistent_left_censored": p_left_censored,
            "breach_5pct": breach.isoformat() if breach is not None else None,
            "persistent_before_breach": (
                None if p_first is None or breach is None else bool(p_first <= breach)
            ),
        })
    n = len(rows)
    caution_rows = [r for r in rows if r["caution_first"] is not None]
    persistent_rows = [r for r in rows if r["persistent_first"] is not None]
    leads = [-r["persistent_offset"] for r in persistent_rows if r["persistent_offset"] is not None]
    exact_leads = [-r["persistent_offset"] for r in persistent_rows
                   if r["persistent_offset"] is not None and not r["persistent_left_censored"]]
    return {
        "definition": "risk_radar_caution_persistence_event.v1",
        "event_params": {"fwd": 21, "depth": .05, "min_gap": 21},
        "n_events": n,
        "caution_by_t0": len(caution_rows),
        "persistent_by_t0": len(persistent_rows),
        "caution_event_recall": len(caution_rows)/n if n else None,
        "persistent_event_recall": len(persistent_rows)/n if n else None,
        "persistent_median_lead_sessions_window_bounded": float(np.median(leads)) if leads else None,
        "persistent_left_censored_n": sum(r["persistent_left_censored"] for r in persistent_rows),
        "persistent_exact_lead_n": len(exact_leads),
        "persistent_median_lead_uncensored_sessions": (
            float(np.median(exact_leads)) if exact_leads else None
        ),
        "persistent_before_breach_n": sum(r["persistent_before_breach"] is True for r in persistent_rows),
        "rows": rows,
    }
def _tracked_inputs():
    paths = [
        "data/yahoo/SPY.parquet", "data/fred/BAMLH0A0HYM2.parquet",
        "data/yahoo/HYG.parquet", "data/yahoo/TLT.parquet", "data/yahoo/_MOVE.parquet",
        "data/fred/DFII10.parquet", "data/yahoo/SMH.parquet", "data/yahoo/XLU.parquet",
        "data/yahoo/XLP.parquet", "data/yahoo/XLY.parquet", "data/yahoo/_VIX.parquet",
        "data/yahoo/_VIX3M.parquet", "data/yahoo/_VIX9D.parquet",
        "data/cboe/putcall.parquet", "data/cboe/gex.parquet",
        "data/fred/DEXJPUS.parquet", "data/breadth/breadth.parquet",
        "data/risk_radar/calibration.json",
    ]
    hashes, missing = {}, []
    for rel in paths:
        p = ROOT / rel
        if p.exists(): hashes[rel] = _hash(p)
        else: missing.append(rel)
    return hashes, missing


def build_result() -> dict:
    calib = _calib()
    sigs = leading_signals()
    subs = subscore_series(sigs, calib)
    idx = sigs.index
    known = subs.notna().any(axis=1)
    state = state_series(subs, calib, sigs=sigs).reindex(idx).where(known)
    spy = _spy(drop_missing=False)
    labels = native_forward_labels(spy, idx, 21, .05)
    canonical = {
        "full": state_accuracy(calib, H=21, dd=.05),
        "since_2020": state_accuracy(calib, H=21, dd=.05, lo="2020-01-01"),
    }
    # Cross-check our native labels and gated state against the canonical evaluator
    # before applying the five-session eligibility filter.
    common = idx.intersection(labels.index)
    common = common[known.reindex(common).fillna(False)]
    base_eval = canonical["full"].get("evaluation") or {}
    if _fingerprint(labels.loc[common]) != base_eval.get("outcomes_sha256"):
        raise RuntimeError("native outcome fingerprint differs from canonical evaluator")
    alert = state.reindex(common).isin(("elevated", "risk-off"))
    y = labels.loc[common, "event"].astype(bool)
    tp=int((alert&y).sum()); fp=int((alert&~y).sum()); fn=int((~alert&y).sum()); tn=int((~alert&~y).sum())
    if {"tp":tp,"fp":fp,"fn":fn,"tn":tn} != base_eval.get("confusion"):
        raise RuntimeError("gated state differs from canonical evaluator")

    full = daily_result(state, known, labels)
    modern = daily_result(state, known, labels, lo="2020-01-01")
    inputs, missing = _tracked_inputs()
    calibration_sha = hashlib.sha256(
        json.dumps(calib, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return {
        "schema": "risk_radar_caution_persistence_study.v1",
        "protocol_commit": PROTOCOL_COMMIT, "source_base": SOURCE_BASE,
        "target": {"depth": .05, "horizon_observations": 21, "persistence_sessions": 5},
        "calibration_sha256": calibration_sha,
        "input_hashes": inputs, "missing_optional_inputs": missing,
        "coverage": {"from": idx[0].isoformat(), "through": idx[-1].isoformat(),
                     "rows": len(idx), "signal_columns": list(sigs.columns),
                     "subscore_columns": list(subs.columns)},
        "daily": {"full": full, "since_2020": modern},
        "event_view": event_result(spy.dropna(), idx, state, known),
        "canonical_crosscheck": {
            k: {"n_days": v.get("n_days"),
                "confusion": (v.get("evaluation") or {}).get("confusion"),
                "outcomes_sha256": (v.get("evaluation") or {}).get("outcomes_sha256")}
            for k,v in canonical.items()
        },
        "authority": {"status": "descriptive_only", "live_model_changed": False,
                      "probability_changed": False, "gate_changed": False,
                      "policy_changed": False},
    }


def _pct(x):
    return "—" if x is None else f"{100*x:.1f}%"


def render_md(r: dict) -> str:
    lines = ["# Risk Radar Caution-Persistence Display Study — Results", "",
             f"Protocol commit: `{r['protocol_commit']}`.", "",
             "Descriptive display-tier research only; no live model or policy changed.", "",
             "## Daily 5% / 21-observation results", "",
             "| Window | Base rate | Caution+ event rate | Persistent-5 event rate | Caution+ lift | Persistent-5 lift | Caution+ recall | Persistent-5 recall | Persistent fire rate |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key,label in (("full","Full usable history"),("since_2020","2020+")):
        row=r["daily"][key]; c=row["caution_plus"]; p=row["persistent_caution_5"]
        lines.append(
            f"| {label} | {_pct(row['base_rate'])} | {_pct(c['event_rate'])} | {_pct(p['event_rate'])} "
            f"| {c['lift_vs_base']:.2f}× | {p['lift_vs_base']:.2f}× "
            f"| {_pct(c['recall'])} | {_pct(p['recall'])} | {_pct(p['fire_rate'])} |"
        )
    ev = r["event_view"]
    modern = r["daily"]["since_2020"]["persistent_caution_5"]
    full = r["daily"]["full"]["persistent_caution_5"]
    lines += ["", "Daily windows overlap and are not independent episodes.", "",
              "## Product implication", "",
              f"- Since 2020, persistent-five caution raises the event rate to **{_pct(modern['event_rate'])}** "
              f"from the {_pct(r['daily']['since_2020']['base_rate'])} base rate, but is active on **{_pct(modern['fire_rate'])}** of eligible sessions.",
              f"- Full history: lift **{full['lift_vs_base']:.2f}×**, fire rate **{_pct(full['fire_rate'])}**; this is context, not a sparse alert.",
              "- Therefore a five-session persistence fact is suitable only as neutral duration context inside Risk Radar; it is too common for a new prominent warning badge and carries no authority to escalate the state.",
              "",
              "## Distinct-event view", "",
              f"- Complete 5%/21 anchors: **{ev['n_events']}**.",
              f"- Caution-or-higher by T0: **{ev['caution_by_t0']}**.",
              f"- Persistent-five caution by T0: **{ev['persistent_by_t0']}**.",
              f"- Persistent-five appears by T0 in **{ev['persistent_by_t0']}** anchors; **{ev['persistent_left_censored_n']}** are already active at the T-21 window edge.",
              f"- Exact (non-left-censored) first-persistence lead is available for **{ev['persistent_exact_lead_n']}** anchors; median **{ev['persistent_median_lead_uncensored_sessions']} sessions**.",
              f"- The window-bounded median is **{ev['persistent_median_lead_sessions_window_bounded']} sessions** and must not be read as an exact lead because of left-censoring.",
              f"- Persistent-five appeared before the first 5% breach in **{ev['persistent_before_breach_n']}** event rows.", "",
              "## Evidence ceiling", "",
              "The five-session rule was frozen as one trading week before outcome inspection and was not swept. "
              "This is reconstructed historical display research, not genuinely issued forecast history. "
              "A favorable result can support duration copy only; it cannot escalate the state or alter odds, gates, or capital authority.", ""]
    return "\n".join(lines)
def main() -> int:
    result = build_result()
    OUT.mkdir(parents=True, exist_ok=True)
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result, indent=2, default=str) + "\n")
    report = ROOT / "research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_RESULTS_2026-09-21.md"
    report.write_text(render_md(result) + "\n")
    print(json.dumps({
        "full": result["daily"]["full"],
        "since_2020": result["daily"]["since_2020"],
        "event_view": {k:v for k,v in result["event_view"].items() if k != "rows"},
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
