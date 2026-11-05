"""Risk Radar gate latency / suppression study.

Descriptive research only. Protocol:
research/grey_deer/RISK_RADAR_GATE_LATENCY_PREREG_2026-09-21.md

No collectors, ledgers, calibration or live engine state are written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.indicators import pct_rank_window
from engine.risk_radar import (
    _GATE_BREADTH_PCT,
    _PCT_WIN,
    _calib,
    leading_signals,
    subscore_series,
    _resolve_state_row,
)
from engine.risk_radar_backtest import _ORDER, _spy, detect_events, state_accuracy
from lib import store

OUT = ROOT / "research/grey_deer/evidence/gate-latency-20260921"
PROTOCOL = ROOT / "research/grey_deer/RISK_RADAR_GATE_LATENCY_PREREG_2026-09-21.md"


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pre_gate_state_series(
    subs: pd.DataFrame, calib: dict, sigs: pd.DataFrame | None = None
) -> pd.Series:
    """Exact production state through escalation, before the context-gate cap."""
    if sigs is None:
        sigs = leading_signals().reindex(subs.index)
    else:
        sigs = sigs.reindex(subs.index)
    out = []
    for day, subrow in subs.iterrows():
        sigrow = sigs.loc[day] if day in sigs.index else pd.Series(dtype=float)
        out.append(_resolve_state_row(subrow, sigrow, calib, gate_met=True)["state"])
    return pd.Series(out, index=subs.index, dtype=object)


def gate_components(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Current gate legs with unknownness preserved."""
    out = pd.DataFrame(index=idx)
    spy_df = store.read("yahoo", "SPY")
    breadth = store.read("breadth", "breadth")
    if spy_df is None or "close" not in spy_df:
        out["price_below_200"] = pd.Series(pd.NA, index=idx, dtype="boolean")
    else:
        spy = spy_df["close"].dropna().copy()
        spy.index = pd.to_datetime(spy.index)
        spy = spy.sort_index()
        ma = spy.rolling(200, min_periods=120).mean()
        below = (spy < ma).where(ma.notna()).reindex(idx)
        out["price_below_200"] = pd.array(below, dtype="boolean")
    if breadth is None or "pct_above_200" not in breadth.columns:
        out["breadth_weak"] = pd.Series(pd.NA, index=idx, dtype="boolean")
    else:
        b = breadth["pct_above_200"].astype(float).copy()
        b.index = pd.to_datetime(b.index)
        bp = pct_rank_window(b.sort_index(), _PCT_WIN).reindex(idx).ffill()
        weak = (bp <= _GATE_BREADTH_PCT).where(bp.notna())
        out["breadth_weak"] = pd.array(weak, dtype="boolean")
    known = out["price_below_200"].notna() & out["breadth_weak"].notna()
    gate = pd.Series(pd.NA, index=idx, dtype="boolean")
    gate.loc[known] = (
        out.loc[known, "price_below_200"].astype(bool)
        & out.loc[known, "breadth_weak"].astype(bool)
    )
    out["gate_open"] = gate
    return out


def native_forward_labels(
    spy: pd.Series, idx: pd.DatetimeIndex, *, horizon: int = 21, depth: float = 0.05
) -> pd.DataFrame:
    """Complete native-price windows matching corrected replay semantics."""
    if type(horizon) is not int or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if type(depth) not in (int, float) or not np.isfinite(depth) or not 0 < depth < 1:
        raise ValueError("depth must be a finite fraction in (0,1)")
    if not isinstance(spy.index, pd.DatetimeIndex) or not spy.index.is_unique or not spy.index.is_monotonic_increasing:
        raise ValueError("SPY observations require a unique ordered DatetimeIndex")
    bools = spy.map(lambda value: isinstance(value, (bool, np.bool_)))
    px = pd.to_numeric(spy, errors="coerce").where(~bools).to_numpy(dtype=float)
    good = np.isfinite(px) & (px > 0)
    rows: list[dict[str, Any]] = []
    for day, loc in zip(idx, spy.index.get_indexer(idx)):
        if loc < 0 or loc + horizon >= len(px) or not good[loc:loc + horizon + 1].all():
            continue
        loss = float(px[loc + 1:loc + horizon + 1].min() / px[loc] - 1.0)
        rows.append({
            "date": day,
            "end": spy.index[loc + horizon],
            "loss": loss,
            "event": bool(loss <= -depth),
        })
    if not rows:
        return pd.DataFrame(columns=["end", "loss", "event"])
    return pd.DataFrame(rows).set_index("date")


def _metrics(alert: pd.Series, outcome: pd.Series) -> dict:
    common = alert.index.intersection(outcome.index)
    a = alert.reindex(common).astype(bool)
    y = outcome.reindex(common).astype(bool)
    tp = int((a & y).sum())
    fp = int((a & ~y).sum())
    fn = int((~a & y).sum())
    tn = int((~a & ~y).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
    )
    return {
        "n": int(len(common)),
        "precision": None if precision is None else round(precision, 6),
        "recall": None if recall is None else round(recall, 6),
        "f1": round(float(f1), 6) if len(common) else None,
        "fire_rate": round(float(a.mean()), 6) if len(common) else None,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }
def _population_fingerprint(labels: pd.DataFrame) -> str:
    rows = [
        [d.isoformat(), row.end.isoformat(), float(row.loss).hex(), bool(row.event)]
        for d, row in labels.iterrows()
    ]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def daily_result(
    raw_state: pd.Series,
    gate: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    lo: str | None = None,
) -> dict:
    idx = labels.index
    if lo is not None:
        idx = idx[idx >= pd.Timestamp(lo)]
    known_gate = gate["gate_open"].reindex(idx).notna()
    known_state = raw_state.reindex(idx).isin(_ORDER)
    idx = idx[known_gate & known_state]
    y = labels.loc[idx, "event"].astype(bool)
    raw = raw_state.reindex(idx).isin(("elevated", "risk-off"))
    gated = raw & gate.loc[idx, "gate_open"].astype(bool)
    rm = _metrics(raw, y)
    gm = _metrics(gated, y)
    raw_tp = raw & y
    raw_fp = raw & ~y
    suppressed = raw & ~gated
    fp_removed = int((suppressed & raw_fp).sum())
    tp_lost = int((suppressed & raw_tp).sum())
    return {
        "from": idx[0].isoformat() if len(idx) else None,
        "through": idx[-1].isoformat() if len(idx) else None,
        "population_sha256": _population_fingerprint(labels.loc[idx]),
        "raw": rm,
        "gated": gm,
        "FP_removed": fp_removed,
        "TP_lost": tp_lost,
        "FP_removed_per_TP_lost": (
            round(fp_removed / tp_lost, 6) if tp_lost else None
        ),
    }
def suppression_attribution(raw_state: pd.Series, gate: pd.DataFrame) -> dict:
    raw = raw_state.isin(("elevated", "risk-off"))
    known = gate["gate_open"].notna()
    idx = raw.index[raw & known & ~gate["gate_open"].fillna(False)]
    counts = {"price_only": 0, "breadth_only": 0, "both_closed": 0}
    for day in idx:
        price = bool(gate.at[day, "price_below_200"])
        breadth = bool(gate.at[day, "breadth_weak"])
        if not price and not breadth:
            counts["both_closed"] += 1
        elif not price:
            counts["price_only"] += 1
        elif not breadth:
            counts["breadth_only"] += 1
    counts["unknown_gate_on_raw_loud"] = int(
        (raw & gate["gate_open"].isna()).sum()
    )
    counts["suppressed_known_total"] = int(len(idx))
    return counts


def _first_true(series: pd.Series) -> pd.Timestamp | None:
    hits = series[series.fillna(False).astype(bool)]
    return hits.index[0] if len(hits) else None


def _session_offset(idx: pd.DatetimeIndex, anchor: pd.Timestamp, day: pd.Timestamp | None) -> int | None:
    if day is None or anchor not in idx or day not in idx:
        return None
    return int(idx.get_loc(day) - idx.get_loc(anchor))


def _first_breach(spy: pd.Series, anchor: pd.Timestamp, depth: float = 0.05, horizon: int = 21) -> pd.Timestamp | None:
    if anchor not in spy.index:
        return None
    loc = spy.index.get_loc(anchor)
    base = float(spy.iloc[loc])
    tail = spy.iloc[loc + 1:loc + horizon + 1]
    hits = tail[tail <= base * (1.0 - depth)]
    return hits.index[0] if len(hits) else None
def event_latency_result(
    spy: pd.Series,
    idx: pd.DatetimeIndex,
    raw_state: pd.Series,
    gate: pd.DataFrame,
) -> dict:
    clean = spy.dropna()
    onsets = detect_events(clean, fwd=21, depth=0.05, min_gap=21)
    raw_loud = raw_state.isin(("elevated", "risk-off"))
    gated_loud = raw_loud & gate["gate_open"].fillna(False)
    rows = []
    for anchor in onsets:
        if anchor not in idx or anchor not in clean.index:
            continue
        pos = idx.get_loc(anchor)
        if pos < 21 or pos + 21 >= len(idx):
            continue
        pre = idx[pos - 21:pos + 1]
        post = idx[pos + 1:pos + 22]
        raw_first = _first_true(raw_loud.reindex(pre))
        gated_pre = _first_true(gated_loud.reindex(pre))
        gated_after = None if gated_pre is not None else _first_true(gated_loud.reindex(post))
        gated_first = gated_pre or gated_after
        breach = _first_breach(clean, anchor)
        timing = "no_raw_pre"
        if raw_first is not None:
            if gated_first is None:
                timing = "never_through_t21"
            elif gated_first <= anchor:
                timing = "by_t0"
            elif breach is not None and gated_first <= breach:
                timing = "after_t0_before_breach"
            else:
                timing = "after_breach"
        rows.append({
            "anchor": anchor.isoformat(),
            "raw_first": raw_first.isoformat() if raw_first is not None else None,
            "gated_first": gated_first.isoformat() if gated_first is not None else None,
            "breach_5pct": breach.isoformat() if breach is not None else None,
            "raw_offset": _session_offset(idx, anchor, raw_first),
            "gated_offset": _session_offset(idx, anchor, gated_first),
            "latency": (
                _session_offset(idx, raw_first, gated_first)
                if raw_first is not None and gated_first is not None else None
            ),
            "timing": timing,
        })
    raw_events = [r for r in rows if r["raw_first"] is not None]
    latencies = [r["latency"] for r in raw_events if r["latency"] is not None]
    timing_counts = {
        k: sum(r["timing"] == k for r in raw_events)
        for k in ("by_t0", "after_t0_before_breach", "after_breach", "never_through_t21")
    }
    raw_recall = len(raw_events) / len(rows) if rows else None
    gated_by_t0 = sum(r["timing"] == "by_t0" for r in raw_events)
    gated_recall_by_t0 = gated_by_t0 / len(rows) if rows else None
    return {
        "definition": "risk_radar_gate_event_latency.v1",
        "event_params": {"fwd": 21, "depth": 0.05, "min_gap": 21},
        "n_events": len(rows),
        "n_raw_pre_t0": len(raw_events),
        "raw_event_recall": None if raw_recall is None else round(raw_recall, 6),
        "gated_event_recall_by_t0": (
            None if gated_recall_by_t0 is None else round(gated_recall_by_t0, 6)
        ),
        "timing_counts_among_raw_pre_t0": timing_counts,
        "latency_median_sessions": (
            None if not latencies else round(float(np.median(latencies)), 3)
        ),
        "latency_p75_sessions": (
            None if not latencies else round(float(np.percentile(latencies, 75)), 3)
        ),
        "rows": rows,
    }


def _tracked_inputs() -> tuple[dict[str, str], list[str]]:
    paths = [
        "data/yahoo/SPY.parquet",
        "data/fred/BAMLH0A0HYM2.parquet",
        "data/yahoo/HYG.parquet",
        "data/yahoo/TLT.parquet",
        "data/yahoo/_MOVE.parquet",
        "data/fred/DFII10.parquet",
        "data/yahoo/SMH.parquet",
        "data/yahoo/XLU.parquet",
        "data/yahoo/XLP.parquet",
        "data/yahoo/XLY.parquet",
        "data/yahoo/_VIX.parquet",
        "data/yahoo/_VIX3M.parquet",
        "data/yahoo/_VIX9D.parquet",
        "data/cboe/putcall.parquet",
        "data/cboe/gex.parquet",
        "data/fred/DEXJPUS.parquet",
        "data/breadth/breadth.parquet",
        "data/risk_radar/calibration.json",
    ]
    hashes: dict[str, str] = {}
    missing: list[str] = []
    for rel in paths:
        path = ROOT / rel
        if path.exists():
            hashes[rel] = _hash(path)
        else:
            missing.append(rel)
    return hashes, missing


def build_result() -> dict:
    calib = _calib()
    sigs = leading_signals()
    if sigs is None or sigs.empty:
        raise RuntimeError("leading_signals returned no usable history")
    subs = subscore_series(sigs, calib)
    if subs is None or subs.empty:
        raise RuntimeError("subscore_series returned no usable history")
    idx = sigs.index
    # Match the canonical evaluator's knowability rule: an all-missing
    # subscore row is not a calm call and cannot enter the comparison population.
    known_state = subs.notna().any(axis=1)
    raw_state = pre_gate_state_series(subs, calib, sigs=sigs).reindex(idx).where(known_state)
    gate = gate_components(idx)
    spy = _spy(drop_missing=False)
    labels = native_forward_labels(spy, idx)
    full = daily_result(raw_state, gate, labels)
    modern = daily_result(raw_state, gate, labels, lo="2020-01-01")

    # Independent parity check against the canonical evaluator on the same target.
    canonical = {
        "full": state_accuracy(calib, H=21, dd=.05),
        "since_2020": state_accuracy(calib, H=21, dd=.05, lo="2020-01-01"),
    }
    for name, ours in (("full", full), ("since_2020", modern)):
        expected = canonical[name]
        if ours["gated"]["n"] != expected.get("n_days"):
            raise RuntimeError(f"canonical population mismatch for {name}")
        if ours["gated"]["confusion"] != (expected.get("evaluation") or {}).get("confusion"):
            raise RuntimeError(f"canonical gated-state mismatch for {name}")

    inputs, missing = _tracked_inputs()
    event = event_latency_result(spy.dropna(), idx, raw_state, gate)
    calibration_sha = hashlib.sha256(
        json.dumps(calib, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    source_paths = [
        "engine/risk_radar.py",
        "engine/risk_radar_backtest.py",
        "scripts/research/risk_radar_gate_latency.py",
        "research/grey_deer/RISK_RADAR_GATE_LATENCY_PREREG_2026-09-21.md",
    ]
    source_hashes = {rel: _hash(ROOT / rel) for rel in source_paths}
    return {
        "schema": "risk_radar_gate_latency_study.v1",
        "protocol_commit": "5c40f881e1e3195b9dd171e078d3d1f211da4015",
        "source_base": "4273786fa0c3a84efed2a793584f740fe110265a",
        "target": {"depth": 0.05, "horizon_observations": 21},
        "calibration_sha256": calibration_sha,
        "source_hashes": source_hashes,
        "input_hashes": inputs,
        "missing_optional_inputs": missing,
        "coverage": {
            "signals_from": idx[0].isoformat(),
            "signals_through": idx[-1].isoformat(),
            "signal_rows": len(idx),
            "signal_columns": list(sigs.columns),
            "subscore_columns": list(subs.columns),
        },
        "daily": {"full": full, "since_2020": modern},
        "canonical_gated_crosscheck": {
            k: {
                "n_days": v.get("n_days"),
                "confusion": (v.get("evaluation") or {}).get("confusion"),
                "outcomes_sha256": (v.get("evaluation") or {}).get("outcomes_sha256"),
            }
            for k, v in canonical.items()
        },
        "suppression_attribution": suppression_attribution(raw_state, gate),
        "event_latency": event,
        "authority": {
            "status": "descriptive_only",
            "live_model_changed": False,
            "gate_changed": False,
            "probability_changed": False,
            "policy_changed": False,
        },
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100.0 * value:.1f}%"


def render_markdown(result: dict) -> str:
    lines = [
        "# Risk Radar Gate Latency / Suppression Results — 2026-09-21",
        "",
        f"Protocol commit: `{result['protocol_commit']}`.",
        "",
        "Descriptive research only. No live gate, threshold, probability, policy or capital authority changed.",
        "",
        "## Daily 5% / 21-observation tradeoff",
        "",
        "| Window | Raw precision | Gated precision | Raw recall | Gated recall | Raw fire rate | Gated fire rate | FP removed | TP lost | FP removed / TP lost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in (("full", "Full usable history"), ("since_2020", "2020+")):
        row = result["daily"][key]
        raw, gated = row["raw"], row["gated"]
        ratio = row["FP_removed_per_TP_lost"]
        lines.append(
            f"| {label} | {_pct(raw['precision'])} | {_pct(gated['precision'])} "
            f"| {_pct(raw['recall'])} | {_pct(gated['recall'])} "
            f"| {_pct(raw['fire_rate'])} | {_pct(gated['fire_rate'])} "
            f"| {row['FP_removed']} | {row['TP_lost']} "
            f"| {('—' if ratio is None else f'{ratio:.2f}')} |"
        )
    lines += ["", "Daily windows overlap; these counts are not independent episodes.", ""]
    full = result["daily"]["full"]
    modern = result["daily"]["since_2020"]
    lines += [
        "## Paired interpretation",
        "",
        f"- Full history: precision {_pct(full['raw']['precision'])} → {_pct(full['gated']['precision'])}, "
        f"recall {_pct(full['raw']['recall'])} → {_pct(full['gated']['recall'])}, "
        f"fire rate {_pct(full['raw']['fire_rate'])} → {_pct(full['gated']['fire_rate'])}.",
        f"- 2020+: precision {_pct(modern['raw']['precision'])} → {_pct(modern['gated']['precision'])}, "
        f"recall {_pct(modern['raw']['recall'])} → {_pct(modern['gated']['recall'])}, "
        f"fire rate {_pct(modern['raw']['fire_rate'])} → {_pct(modern['gated']['fire_rate'])}.",
        "- The ungated state is too frequent to substitute for the loud gate. The relevant product "
        "question is how to preserve the quieter early-warning information while keeping loud "
        "confirmation selective; this study does not authorize a gate change.",
        "",
    ]
    ev = result["event_latency"]
    tc = ev["timing_counts_among_raw_pre_t0"]
    lines += [
        "## Distinct-event confirmation timing",
        "",
        f"- Complete 5%/21-observation event anchors: **{ev['n_events']}**.",
        f"- Events with a raw loud reading by T0: **{ev['n_raw_pre_t0']}** "
        f"({_pct(ev['raw_event_recall'])} of anchors).",
        f"- Events with gated loud confirmation by T0: **{tc['by_t0']}** "
        f"({_pct(ev['gated_event_recall_by_t0'])} of anchors).",
        f"- Among raw-pre-T0 events: after T0 but before 5% breach **{tc['after_t0_before_breach']}**; "
        f"after breach **{tc['after_breach']}**; never through T+21 **{tc['never_through_t21']}**.",
        f"- First-gated minus first-raw latency: median **{ev['latency_median_sessions']}** sessions; "
        f"75th percentile **{ev['latency_p75_sessions']}** sessions (where both exist).",
        "",
        "## Gate-leg attribution",
        "",
    ]
    attr = result["suppression_attribution"]
    lines.append(
        f"Suppressed known raw-loud days: **{attr['suppressed_known_total']}** — "
        f"price leg only closed {attr['price_only']}, breadth leg only closed "
        f"{attr['breadth_only']}, both closed {attr['both_closed']}. "
        f"Raw-loud days with unknown gate evidence: {attr['unknown_gate_on_raw_loud']}."
    )
    lines += [
        "",
        "## Evidence ceiling",
        "",
        "This is a current-code historical reconstruction, not genuinely issued forecast history. "
        "Daily observations overlap, event anchors are algorithmic labels, and the study is not "
        "a parameter search. Any gate/model change requires a separate preregistered candidate.",
        "",
        "Method correction before acceptance: the first successful run included all-missing "
        "subscore warmup rows in the full-history denominator. A canonical state_accuracy parity "
        "check exposed the mismatch. The accepted run masks those rows exactly as the canonical "
        "evaluator does; no threshold, target, horizon or gate rule changed. The 2020+ result was "
        "unchanged by this warmup-only correction.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    result = build_result()
    OUT.mkdir(parents=True, exist_ok=True)
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    md_path = ROOT / "research/grey_deer/RISK_RADAR_GATE_LATENCY_RESULTS_2026-09-21.md"
    md_path.write_text(render_markdown(result).rstrip() + "\n", encoding="utf-8")
    print(
        "GATE_LATENCY_COMPLETE",
        json.dumps({
            "full": result["daily"]["full"],
            "since_2020": result["daily"]["since_2020"],
            "event_summary": {
                k: v for k, v in result["event_latency"].items() if k != "rows"
            },
            "suppression_attribution": result["suppression_attribution"],
        }, sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
