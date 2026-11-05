"""B1 — Finalize result.json, RESULT.md, universe_manifest.json.

Reads summary.json (drop counts + pre-warmup counts) + result_partial.json (statistics);
emits result.json (machine-readable, schema-faithful), RESULT.md (human), and
universe_manifest.json (per-name manifest for hashing). The orchestrator run_all.py
invokes hashes.py LAST so this file's hashes are stable.

F1: the headline is now the TRUE pooled Δ(pooled 3D.p* − 1D.M3) on H10 net with
its shared-month-bootstrap CI — NOT the pooled 3D mean (which was wrong in
round 1). The 3D and 1D.M3 pooled means are reported beside the delta.

F4: per-variant BEFORE/AFTER counts (pre_warmup, warmup, horizon21, outcomes_none)
are read from summary.json and reported both in result.json drops_per_variant and
in RESULT.md.

F12: "warm-up 100 sessions" → corrected to 400; "2,572,750 pre-filter" → that was
round 0's panel under OLD constants, not this run's; pytest count and 2D.p1
mean_mfe21_consumed_frac outlier are explained.

F13: tolerant Jaccard (events from different phases match within n-1 sessions)
is reported alongside the (mechanically 0) exact-date Jaccard.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import trim_mean

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
REPO = RESULTS_DIR.parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CODE_DIR))

import run as run_mod  # noqa: E402

# Per-variant panel_n from the preserved round-1 / round-2 records (L9).
# r3 is re-read from the frozen panel at finalize time.
ROUND_PANEL_N_R1 = {
    "1D": 296635, "2D.p0": 148790, "2D.p1": 148651,
    "3D.p0": 99912, "3D.p1": 99665, "3D.p2": 99702,
    "1D.M2": 151084, "1D.M3": 101575, "3D.K1": 260327,
}
ROUND_PANEL_N_R2 = {
    "1D": 296669, "2D.p0": 148802, "2D.p1": 148665,
    "3D.p0": 99919, "3D.p1": 99673, "3D.p2": 99710,
    "1D.M2": 151097, "1D.M3": 101582, "3D.K1": 260350,
}
VARIANT_ORDER = ["1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2", "1D.M2", "1D.M3", "3D.K1"]


# ---- shared strings (D6: identical gaps/deviations lists) ----
GAPS = [
    "no real-data basket input was read at finalize time — the panel was produced in run.py and is referenced by its sha256",
]
DEVIATIONS = [
    "spec amended by seat 2026-10-04 (round 1): k inverted — 1D.M2 = cascade(close_1D, k=1/2); 1D.M3 = cascade(close_1D, k=1/3); 3D.K1 = cascade(close_3D(p=0), k=3) (masterplan §5.2 items 4-5 superseded; cascade_lib.py docstring)",
    "spec amended by seat 2026-10-04 (round 2, F13): tolerant Jaccard across phases — events from different phases of the same grain are the same event when their 1D signal sessions lie within n-1 sessions; reported alongside the (mechanically 0) exact-date Jaccard",
    "warm-up measured from the name's FIRST inner-joined session, not from the absolute SPY position (D2/F4; run.py:_name_events)",
    "warm-up drops now COUNTED per variant (F4): drops[v][\"warmup\"] is incremented for each event whose signal session fell inside the first 400 sessions of the name's inner-joined series",
    "n-DAY buckets kept only when bucket size == n (D7; run.py:_build_n_day_bars)",
    "outcomes indexed on the SPY session calendar for BOTH arms of excess_H and MFE/MAE (F7; run.py:_outcomes_for_event)",
    "per-cell RNG derived from numpy SeedSequence.spawn(len(cells)) over a STABLE SORTED cell label list (F8/G7; stats.py:_build_cell_streams) — no encounter-order dependency, byte-identical result.json across processes",
    "verdict REAL requires same sign across the ≥ 2 qualifying phases AND both eras (D9/F10; stats.py:_compute_verdict); the 2-agree-1-dissent case now keeps details (F10)",
    "phase-0 bar equality test compares bucket CLOSES by aligned bucket index (bar_derive labels each bucket by the FIRST session; spec §VARIANTS labels by the LAST session — the bucket set and closes agree, the date labels differ by n-1 sessions)",
    "G1: horizon gate drops events whose entry + 21 SPY sessions exceeds the NAME's last available close (covers h21, and therefore h10, since h10_bad ⇒ h21_bad); `_name_close_at_spy_pos` carries `name_last_pos` and returns None past it; `c0` (entry close) is emitted on every panel row",
    "G5: run.py module-level K_1D_M2 = 1/2, K_1D_M3 = 1/3, K_3D_K1 = 3.0 — tests read these constants directly (no string search); variant_inputs reads them",
    "G6: 'no_entry' drop bucket counts two silent continues in `_name_events` (signal on the final SPY session → no next-session entry; name stopped trading → no later close for the entry)",
    "G3: tolerant Jaccard matched on SPY session POSITION with |Δpos| ≤ n−1, one-to-one greedy matching in date order within each name, union = |A| + |B| − matched (replaces calendar-day approximation; reference values: 3D p0-p1 0.5739, p0-p2 0.5761, p1-p2 0.5766; 2D p0-p1 0.5655)",
    "round 4 (2026-10-04): tests-and-record repair; events_panel.parquet and confirmation_pairs.parquet byte-frozen (sha256 209e2246… / d20cd405…); no panel number changed",
]


def _read_pytest_summary() -> str:
    """Counts-only pytest summary (no wall time). Written by the orchestrated pytest step."""
    p = CODE_DIR / "_test_summary.txt"
    if not p.exists():
        return ""
    raw = p.read_text().strip()
    for line in raw.splitlines()[::-1]:
        s = line.strip()
        if re.search(r"\b\d+\s+(passed|failed)\b", s):
            return re.sub(r"\s+in\s+[0-9.]+s$", "", s)
    return raw.splitlines()[-1] if raw else ""


def _provenance() -> dict:
    import pandas
    import numpy
    import pyarrow
    import scipy
    import pytest
    return {
        "host": "m2",
        "python": "/opt/homebrew/bin/python3",
        "python_version": "3.14.7",
        "pandas": pandas.__version__,
        "numpy": numpy.__version__,
        "pyarrow": pyarrow.__version__,
        "scipy": scipy.__version__,
        "pytest": pytest.__version__,
    }


def _compute_confirmation_mfe_notes(panel: pd.DataFrame) -> dict:
    """L9: MFE21_1D < 0.001 counts and 2D.p1 raw vs 5%-trimmed consumed means."""
    conf_path = RESULTS_DIR / "confirmation_pairs.parquet"
    conf = pd.read_parquet(conf_path)
    one = panel.loc[panel["variant"] == "1D", ["name", "signal_date", "mfe21"]].copy()
    one["signal_date"] = pd.to_datetime(one["signal_date"])
    conf["signal_session_1d"] = pd.to_datetime(conf["signal_session_1d"])
    mfe = one["mfe21"].to_numpy(dtype=np.float64)
    n_lt = int(np.sum(np.isfinite(mfe) & (mfe < 0.001)))
    n_le0 = int(np.sum(np.isfinite(mfe) & (mfe <= 0)))
    n_mid = int(np.sum(np.isfinite(mfe) & (mfe > 0) & (mfe < 0.001)))
    p1 = conf[conf["variant"] == "2D.p1"]
    cons = p1["mfe21_consumed_frac"].to_numpy(dtype=np.float64)
    cons_f = cons[np.isfinite(cons)]
    raw = float(cons_f.mean()) if len(cons_f) else float("nan")
    trimmed = float(trim_mean(cons_f, 0.05)) if len(cons_f) else float("nan")
    return {
        "n_1d_events_mfe_lt_0_001": n_lt,
        "n_1d_events_mfe_le_0": n_le0,
        "n_1d_events_mfe_between_0_and_0_001": n_mid,
        "p1_raw_mean_mfe_consumed": raw,
        "p1_trim05_mean_mfe_consumed": trimmed,
        "p1_n_finite_consumed": int(len(cons_f)),
    }


def _round_row_counts(panel: pd.DataFrame) -> dict:
    r3 = panel.groupby("variant").size().astype(int).to_dict()
    return {
        "r1": dict(ROUND_PANEL_N_R1),
        "r2": dict(ROUND_PANEL_N_R2),
        "r3": {v: int(r3.get(v, 0)) for v in VARIANT_ORDER},
    }


def _read_mutant_results() -> dict:
    p = CODE_DIR / "mutant_results.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_universe_manifest(used_names: list[str], ohlcv_dir: Path, out_path: Path) -> str:
    """Write universe_manifest.json: per-name n_rows, first/last date, sha256 of basket.
    Returns the manifest's sha256."""
    entries = []
    for name in used_names:
        p = ohlcv_dir / f"{name}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        rows = len(df)
        first = str(df.index[0])[:10] if rows else None
        last = str(df.index[-1])[:10] if rows else None
        entries.append({
            "name": name,
            "n_rows": int(rows),
            "first_date": first,
            "last_date": last,
            "path": str(p.relative_to(REPO)),
            "sha256": sha256_path(p),
        })
    payload = {
        "n_used": len(entries),
        "ohlcv_dir": str(ohlcv_dir.relative_to(REPO)),
        "entries": entries,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return sha256_path(out_path)


def get_used_names(panel: pd.DataFrame) -> list[str]:
    return sorted(panel["name"].unique().tolist())


def build_result(panel: pd.DataFrame) -> dict:
    partial = json.loads((RESULTS_DIR / "result_partial.json").read_text())
    summary = json.loads((RESULTS_DIR / "summary.json").read_text())
    repo_head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"]).decode().strip()

    panel_path = RESULTS_DIR / "events_panel.parquet"
    confirm_path = RESULTS_DIR / "confirmation_pairs.parquet"
    panel_sha = sha256_path(panel_path)
    confirm_sha = sha256_path(confirm_path)

    pytest_summary = _read_pytest_summary()

    # F1: pooled Δ(pooled 3D.p* − 1D.M3) on H10 net — the headline
    pooled_deltas = partial.get("pooled_deltas", {})
    headline_3d = pooled_deltas.get("3D_pool_minus_1D.M3", {})

    return {
        "lane": "B1",
        "status": "DELIVERED",
        "repo_head": repo_head,
        "data_class": {"vintage": "final", "universe": "survivor-selected baskets"},
        "n_names_in": summary["n_in"],
        "n_names_excluded_short": summary["n_short"],
        "n_names_excluded_gaps": summary["n_gaps"],
        "n_names_used": summary["n_used"],
        "warmup_sessions": summary.get("warmup_sessions", 400),
        "variants": partial["variants"],
        "phase_dispersion": partial["phase_dispersion"],
        "contrasts": partial["contrasts"],
        "confirmation": partial["confirmation"],
        "verdict": partial["verdict"],
        "pooled_deltas": pooled_deltas,
        "headline": {
            # F1: the headline is now the TRUE pooled Δ(pooled 3D.p* − 1D.M3)
            "pooled_across_phases_delta_h10_net": float(headline_3d.get("delta", float("nan"))),
            "pooled_across_phases_ci_h10_net": [float(x) for x in headline_3d.get("ci", [float("nan"), float("nan")])],
            "pooled_3d_mean_h10_net": float(headline_3d.get("a_mean", float("nan"))),
            "pooled_3d_ci_h10_net": [float(x) for x in headline_3d.get("a_ci", [float("nan"), float("nan")])],
            "pooled_1D_M3_mean_h10_net": float(headline_3d.get("b_mean", float("nan"))),
            "pooled_1D_M3_ci_h10_net": [float(x) for x in headline_3d.get("b_ci", [float("nan"), float("nan")])],
            "note": ("pooled Δ(3D.p* − 1D.M3) on H10 net with the SHARED month-cluster bootstrap. "
                     "3D.p* = [3D.p0, 3D.p1, 3D.p2] pooled; 1D.M3 is the matching 1D longer-memory arm. "
                     "3D and 1D.M3 pooled means reported beside the delta."),
        },
        "drops_per_variant": summary.get("drops_per_variant", {}),
        "pre_warmup_counts": summary.get("pre_warmup_counts", {}),
        "files": {
            "events_panel": str(panel_path.relative_to(REPO)),
            "confirmation_pairs": str(confirm_path.relative_to(REPO)),
            "events_panel_sha256": panel_sha,
            "confirmation_pairs_sha256": confirm_sha,
        },
        "tests": pytest_summary,
        "gaps": list(GAPS),
        "deviations": list(DEVIATIONS),
        "provenance": _provenance(),
        "half_life_sessions": {k: float(v) for k, v in run_mod.half_life_table().items()},
        "round_panel_n": _round_row_counts(panel),
        "confirmation_mfe_notes": _compute_confirmation_mfe_notes(panel),
        "mutant_tests": _read_mutant_results(),
    }


def write_result_md(result: dict, summary: dict) -> None:
    out = []
    verdict = result["verdict"]
    grain_3 = verdict["grain_effect_3d"]
    grain_2 = verdict["grain_effect_2d"]
    mem_3 = verdict["memory_effect_3"]
    head = result["headline"]
    pm = head["pooled_across_phases_delta_h10_net"]
    plo, phi = head["pooled_across_phases_ci_h10_net"]
    p3_mean = head["pooled_3d_mean_h10_net"]
    p3_lo, p3_hi = head["pooled_3d_ci_h10_net"]
    pm3_mean = head["pooled_1D_M3_mean_h10_net"]
    pm3_lo, pm3_hi = head["pooled_1D_M3_ci_h10_net"]
    warmup_sessions = result.get("warmup_sessions", 400)
    pre_warmup = result.get("pre_warmup_counts", {})

    # First paragraph: data class + ANSWER FIRST (F1 + F12 corrections)
    out.append("## Data class")
    out.append("")
    out.append(
        "Inputs are **final-vintage** (the price stores are as observed today, not "
        "point-in-time) and the universe is **survivor-selected** (current membership "
        "only). Every signal uses only closes at or before the signal session."
    )
    out.append("")

    out.append("## Answer first")
    out.append("")
    out.append(
        f"After matching elapsed memory (1D.M3 = k=1/3), the 3D grain effect is **{grain_3}**: "
        f"the **pooled-across-phases Δ(3D.p* − 1D.M3)** on cost-adjusted SPY-excess H10 is "
        f"{pm:+.4f} 95% CI [{plo:+.4f}, {phi:+.4f}]. The pooled 3D.p* mean is "
        f"{p3_mean:+.4f} [{p3_lo:+.4f}, {p3_hi:+.4f}]; the pooled 1D.M3 mean is "
        f"{pm3_mean:+.4f} [{pm3_lo:+.4f}, {pm3_hi:+.4f}]. Phase/era sign pattern follows below. "
        f"2D grain effect: **{grain_2}**; memory effect (1D.M3 − 1D): **{mem_3}**."
    )
    out.append("")

    # Universe / exclusions
    out.append("## Universe and exclusions")
    out.append("")
    out.append(f"- Names in (raw `data/baskets/ohlcv/*.parquet`): **{result['n_names_in']:,}**")
    out.append(f"- Excluded for <800 rows: **{result['n_names_excluded_short']:,}**")
    out.append(f"- Excluded for any internal gap > 5 SPY sessions: **{result['n_names_excluded_gaps']:,}**")
    out.append(f"- Names used: **{result['n_names_used']:,}**")
    out.append("")

    # Per-variant drop counts (F4)
    out.append("## Per-variant event counts (F4)")
    out.append("")
    out.append(
        f"Each event passes THREE drop gates. `pre_warmup` is the count of bullish-cross "
        f"candidates BEFORE the warm-up filter (events with both bars non-NaN and a valid "
        f"signal). `warmup` is the count of candidates whose signal session fell inside "
        f"the first {warmup_sessions} sessions of the name's inner-joined series (D2/F4: "
        f"warm-up measured from the name's first session, not from the absolute SPY "
        f"position). `horizon21` is the count of events whose entry_date + 21 sessions "
        f"would have overrun the data (F7: SPY-grid based). `outcomes_none` is the count "
        f"of events whose outcome row could not be computed (e.g. zero or negative closes "
        f"at entry or at the SPY grid position)."
    )
    out.append("")
    out.append("| variant | pre_warmup | warmup | horizon21 | no_entry | outcomes_none | after_warmup | panel_n |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    # Read the panel parquet to get per-variant counts (already on disk).
    panel_for_counts = pd.read_parquet(RESULTS_DIR / "events_panel.parquet")
    panel_counts = panel_for_counts.groupby("variant").size().to_dict()
    for v in ["1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2", "1D.M2", "1D.M3", "3D.K1"]:
        d = result["drops_per_variant"].get(v, {"warmup": 0, "horizon21": 0, "no_entry": 0, "outcomes_none": 0})
        pre = pre_warmup.get(v, 0)
        warmup = d.get("warmup", 0)
        h21 = d.get("horizon21", 0)
        no_e = d.get("no_entry", 0)
        none_o = d.get("outcomes_none", 0)
        after = pre - warmup
        pn = panel_counts.get(v, 0)
        out.append(f"| {v} | {pre:,} | {warmup:,} | {h21:,} | {no_e:,} | {none_o:,} | {after:,} | {pn:,} |")
    out.append("")

    # Per-variant stats
    out.append("## Per-variant statistics")
    out.append("")
    out.append(
        "Mean excess_h10_net, mean excess_h21_net, hit_rate_h10, plus month-cluster bootstrap "
        "95% CIs (1,000 resamples over distinct entry_months, SeedSequence-derived RNG). "
        "n_events, n_months, n_names."
    )
    out.append("")
    out.append("| variant | n_events | n_months | n_names | mean_h10_net | 95% CI h10 | mean_h21_net | 95% CI h21 | hit_h10 | median_mfe21 | median_mae21 |")
    out.append("|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|")
    for v in ["1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2", "1D.M2", "1D.M3", "3D.K1"]:
        ov = result["variants"][v]["overall"]
        lo10, hi10 = ov["ci_h10"]
        lo21, hi21 = ov["ci_h21"]
        out.append(
            f"| {v} | {ov['n_events']:,} | {ov['n_months']} | {ov['n_names']:,} | "
            f"{ov['mean_h10_net']:+.4f} | [{lo10:+.4f}, {hi10:+.4f}] | "
            f"{ov['mean_h21_net']:+.4f} | [{lo21:+.4f}, {hi21:+.4f}] | "
            f"{ov['hit_rate_h10']:.3f} | {ov['median_mfe21']:+.4f} | {ov['median_mae21']:+.4f} |"
        )
    out.append("")

    # Per-era H10 net
    out.append("### Per-era, per-variant H10 net")
    out.append("")
    out.append("| variant | 2014-2019 mean | 2014-2019 CI | 2020-2026 mean | 2020-2026 CI |")
    out.append("|---|---:|---|---:|---|")
    for v in ["1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2", "1D.M2", "1D.M3", "3D.K1"]:
        e1 = result["variants"][v]["by_era"]["2014-2019"]
        e2 = result["variants"][v]["by_era"]["2020-2026"]
        out.append(
            f"| {v} | {e1['mean_h10_net']:+.4f} | "
            f"[{e1['ci_h10'][0]:+.4f}, {e1['ci_h10'][1]:+.4f}] | "
            f"{e2['mean_h10_net']:+.4f} | "
            f"[{e2['ci_h10'][0]:+.4f}, {e2['ci_h10'][1]:+.4f}] |"
        )
    out.append("")

    # Phase dispersion
    out.append("## Phase dispersion")
    out.append("")
    out.append(
        "Range across phases of the H10_net mean; Jaccard of (name, signal_date) event sets "
        "(exact-date, mechanically 0 because phases' bar end-dates never coincide); "
        "tolerant Jaccard (events from different phases match when their 1D signal sessions "
        "lie within n−1 SPY sessions — F13 amendment); pooled-across-phases mean with its "
        "bootstrap CI; phase_fragile = range > pooled CI width."
    )
    out.append("")
    out.append("| grain | range_h10 | pooled_mean_h10 | pooled 95% CI | fragile | tol(sessions) | jaccard p0-p1 | jaccard p0-p2 | jaccard p1-p2 |")
    out.append("|---|---:|---:|---|:---:|---:|---:|---:|---:|")
    pd_2d = result["phase_dispersion"]["2D"]
    pd_3d = result["phase_dispersion"]["3D"]
    j2 = pd_2d["jaccard"]
    j3 = pd_3d["jaccard"]
    jt2 = pd_2d.get("jaccard_tolerant", {})
    jt3 = pd_3d.get("jaccard_tolerant", {})
    out.append(
        f"| 2D | {pd_2d['range_h10']:+.5f} | {pd_2d['pooled_mean_h10']:+.4f} | "
        f"[{pd_2d['pooled_ci'][0]:+.4f}, {pd_2d['pooled_ci'][1]:+.4f}] | "
        f"{'YES' if pd_2d['fragile'] else 'no'} | "
        f"{pd_2d.get('jaccard_tolerance_sessions', 1)} | "
        f"exact={j2.get('p0-p1', float('nan')):.3f} "
        f"tol={jt2.get('p0-p1', float('nan')):.3f} | — | — |"
    )
    out.append(
        f"| 3D | {pd_3d['range_h10']:+.5f} | {pd_3d['pooled_mean_h10']:+.4f} | "
        f"[{pd_3d['pooled_ci'][0]:+.4f}, {pd_3d['pooled_ci'][1]:+.4f}] | "
        f"{'YES' if pd_3d['fragile'] else 'no'} | "
        f"{pd_3d.get('jaccard_tolerance_sessions', 2)} | "
        f"exact={j3.get('p0-p1', float('nan')):.3f} "
        f"tol={jt3.get('p0-p1', float('nan')):.3f} | "
        f"exact={j3.get('p0-p2', float('nan')):.3f} "
        f"tol={jt3.get('p0-p2', float('nan')):.3f} | "
        f"exact={j3.get('p1-p2', float('nan')):.3f} "
        f"tol={jt3.get('p1-p2', float('nan')):.3f} |"
    )
    out.append("")

    # Contrasts (F9: every cell carries honest-N for BOTH arms)
    out.append("## Contrasts")
    out.append("")
    out.append(
        "Each contrast = Δ(A − B) of the H10_net mean. Same-month-cluster bootstrap "
        "(1,000 draws, SeedSequence-spawn-derived RNG) is used for both A and B. Overall and "
        "per-era. Every cell carries n_events, n_months, n_names for BOTH arms (F9)."
    )
    out.append("")
    out.append("| contrast | overall Δ | overall h10 CI | n_a/n_b events | n_a/n_b months | n_a/n_b names | 2014-2019 Δ | 2014-2019 CI | n_a/n_b events | 2020-2026 Δ | 2020-2026 CI | n_a/n_b events |")
    out.append("|---|---:|---|---:|---:|---:|---:|---|---:|---:|---|---:|")
    for name in ["3D.p0_minus_1D", "3D.p0_minus_1D.M3",
                  "3D.p1_minus_1D", "3D.p1_minus_1D.M3",
                  "3D.p2_minus_1D", "3D.p2_minus_1D.M3",
                  "2D.p0_minus_1D.M2", "2D.p1_minus_1D.M2",
                  "1D.M3_minus_1D", "1D.M2_minus_1D",
                  "3D.K1_minus_3D.p0"]:
        co = result["contrasts"][name]["overall"]
        e1 = result["contrasts"][name]["by_era"]["2014-2019"]
        e2 = result["contrasts"][name]["by_era"]["2020-2026"]
        out.append(
            f"| {name} | {co['delta_h10']:+.4f} | "
            f"[{co['ci_h10'][0]:+.4f}, {co['ci_h10'][1]:+.4f}] | "
            f"{co['n_a_events_overall']:,}/{co['n_b_events_overall']:,} | "
            f"{co.get('n_a_months_overall', 0)}/{co.get('n_b_months_overall', 0)} | "
            f"{co.get('n_a_names_overall', 0):,}/{co.get('n_b_names_overall', 0):,} | "
            f"{e1['delta_h10']:+.4f} | "
            f"[{e1['ci_h10'][0]:+.4f}, {e1['ci_h10'][1]:+.4f}] | "
            f"{e1['n_a_events']:,}/{e1['n_b_events']:,} | "
            f"{e2['delta_h10']:+.4f} | "
            f"[{e2['ci_h10'][0]:+.4f}, {e2['ci_h10'][1]:+.4f}] | "
            f"{e2['n_a_events']:,}/{e2['n_b_events']:,} |"
        )
    out.append("")

    # Confirmation pairs
    out.append("## Confirmation pairs (1D events)")
    out.append("")
    out.append(
        "For each 1D event (name, s), find the FIRST event of the variant on the same name with "
        "signal session s' in [s, s+10]. no_confirmation_share = share with no candidate; "
        "median_delay_sessions; mean_confirmation_cost_pct (C[s'+1]/C[s+1]−1); "
        "mean_mfe21_consumed_frac = (ln C[s'+1] − ln C[s+1]) / MFE21_1D."
    )
    out.append("")
    out.append("| variant | n | no_confirmation_share | median_delay | mean_cost_pct | mean_mfe_consumed |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for v in ["2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2"]:
        c = result["confirmation"][v]
        out.append(
            f"| {v} | {c['n']:,} | {c['no_confirmation_share']:.3f} | "
            f"{c['median_delay']:.2f} | {c['mean_cost_pct']:+.4f} | "
            f"{c['mean_mfe_consumed']:+.4f} |"
        )
    out.append("")

    # Verdict
    out.append("## Verdict")
    out.append("")
    out.append(f"**Rule**: {verdict['rule']}")
    out.append("")
    out.append("| effect | verdict |")
    out.append("|---|---|")
    out.append(f"| grain_effect_3d | **{verdict['grain_effect_3d']}** |")
    out.append(f"| grain_effect_2d | **{verdict['grain_effect_2d']}** |")
    out.append(f"| memory_effect_3 | **{verdict['memory_effect_3']}** |")
    out.append("")

    # Phase/era sign pattern
    out.append("### 3D grain effect: phase/era sign pattern (Δ(3D.p − 1D.M3))")
    out.append("")
    out.append("| phase | 2014-2019 Δ | 2014-2019 CI | 2020-2026 Δ | 2020-2026 CI | sign | excl-0 both |")
    out.append("|---|---:|---:|---:|---:|:---:|:---:|")
    for d in verdict["details"]["grain_effect_3d"]:
        e1 = d["era_results"]["2014-2019"]
        e2 = d["era_results"]["2020-2026"]
        e1d, e1lo, e1hi = e1["delta"], e1["ci"][0], e1["ci"][1]
        e2d, e2lo, e2hi = e2["delta"], e2["ci"][0], e2["ci"][1]
        if np.isfinite(e1d) and np.isfinite(e2d):
            same = (e1d > 0) == (e2d > 0)
            sign = "+" if e1d > 0 else "-" if e1d < 0 else "0"
            sign_cell = sign if same else "MIXED"
        else:
            sign_cell = "?"
        excl_both = ("YES" if (e1["excludes_zero"] and e2["excludes_zero"]) else "no")
        out.append(
            f"| {d['variant']} | {e1d:+.4f} | "
            f"[{e1lo:+.4f}, {e1hi:+.4f}] | "
            f"{e2d:+.4f} | "
            f"[{e2lo:+.4f}, {e2hi:+.4f}] | "
            f"{sign_cell} | {excl_both} |"
        )
    out.append("")

    out.append("### 2D grain effect: phase/era sign pattern (Δ(2D.p − 1D.M2))")
    out.append("")
    out.append("| phase | 2014-2019 Δ | 2014-2019 CI | 2020-2026 Δ | 2020-2026 CI | sign | excl-0 both |")
    out.append("|---|---:|---:|---:|---:|:---:|:---:|")
    for d in verdict["details"]["grain_effect_2d"]:
        e1 = d["era_results"]["2014-2019"]
        e2 = d["era_results"]["2020-2026"]
        e1d, e1lo, e1hi = e1["delta"], e1["ci"][0], e1["ci"][1]
        e2d, e2lo, e2hi = e2["delta"], e2["ci"][0], e2["ci"][1]
        if np.isfinite(e1d) and np.isfinite(e2d):
            same = (e1d > 0) == (e2d > 0)
            sign = "+" if e1d > 0 else "-" if e1d < 0 else "0"
            sign_cell = sign if same else "MIXED"
        else:
            sign_cell = "?"
        excl_both = ("YES" if (e1["excludes_zero"] and e2["excludes_zero"]) else "no")
        out.append(
            f"| {d['variant']} | {e1d:+.4f} | "
            f"[{e1lo:+.4f}, {e1hi:+.4f}] | "
            f"{e2d:+.4f} | "
            f"[{e2lo:+.4f}, {e2hi:+.4f}] | "
            f"{sign_cell} | {excl_both} |"
        )
    out.append("")

    out.append("### Memory effect: era sign pattern (Δ(1D.M3 − 1D))")
    out.append("")
    out.append("| era | Δ | CI | sign | excl-0 |")
    out.append("|---|---:|---:|:---:|:---:|")
    for d in verdict["details"]["memory_effect_3"]:
        for era in ("2014-2019", "2020-2026"):
            r = d["era_results"].get(era)
            if r is None:
                continue
            rd = r["delta"]; rlo, rhi = r["ci"][0], r["ci"][1]
            sign = "+" if rd > 0 else "-" if rd < 0 else "0"
            excl = "YES" if r["excludes_zero"] else "no"
            out.append(f"| {era} | {rd:+.4f} | [{rlo:+.4f}, {rhi:+.4f}] | {sign} | {excl} |")
    out.append(f"| **verdict** | — | — | — | **{verdict['memory_effect_3']}** |")
    out.append("")

    # L9: Notes with computed numbers (not instructions)
    notes = result.get("confirmation_mfe_notes", {})
    rpn = result.get("round_panel_n", {})
    r1 = rpn.get("r1", ROUND_PANEL_N_R1)
    r2 = rpn.get("r2", ROUND_PANEL_N_R2)
    r3 = rpn.get("r3", {})
    out.append("## Notes (F12/G8/L9)")
    out.append("")
    out.append(
        f"- Warm-up = **{warmup_sessions} sessions** (D2: measured from each name's "
        f"FIRST inner-joined session, NOT from absolute SPY position)."
    )
    out.append(
        "- Per-variant panel_n round 1 → round 2 → round 3 (r1/r2 from preserved "
        "round records; r3 from the frozen panel):"
    )
    out.append("")
    out.append("| variant | r1 | r2 | r3 | r1→r2 | r2→r3 |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for v in VARIANT_ORDER:
        a, b, c = int(r1[v]), int(r2[v]), int(r3.get(v, 0))
        out.append(f"| {v} | {a:,} | {b:,} | {c:,} | {b - a:+d} | {c - b:+d} |")
    out.append("")
    n_lt = notes.get("n_1d_events_mfe_lt_0_001", float("nan"))
    n_le0 = notes.get("n_1d_events_mfe_le_0", float("nan"))
    n_mid = notes.get("n_1d_events_mfe_between_0_and_0_001", float("nan"))
    raw = notes.get("p1_raw_mean_mfe_consumed", float("nan"))
    trim = notes.get("p1_trim05_mean_mfe_consumed", float("nan"))
    out.append(
        f"- Confirmation pairs with MFE21_1D < 0.001 (counted on 1D events, hence "
        f"on every variant's pair rows): **{n_lt:,}**, of which ≤ 0: **{n_le0:,}** "
        f"and 0 < mfe < 0.001: **{n_mid:,}**."
    )
    out.append(
        f"- 2D.p1 mean_mfe21_consumed_frac raw = **{raw:+.6f}**; 5%-trimmed mean = "
        f"**{trim:+.6f}**. The negative raw mean is a tail effect of the "
        f"{n_mid:,} near-zero positive MFE21_1D denominators (plus the "
        f"{n_le0:,} non-positive MFE rows, which are NaN and excluded from the mean)."
    )
    out.append(
        "- The 16 value-changed rows between round 1 and round 2 (FI 9 / NXXT 4 / "
        "NFE 3) are the F7 story: those 10 gap names had outcomes indexed on the "
        "name grid in r1 and were re-indexed onto the SPY calendar in r2, so the "
        "h10/h21 values changed even when the event survived. Round 2 → round 3 "
        "then dropped 123 stale rows (G1: e+21 past the name's last close)."
    )
    out.append(
        "- Jaccard = 0 explanation: exact-date Jaccard across phases is mechanically "
        "0 because phases' bar end-dates never coincide (phase-0 ends on session n-1 "
        "of every n-bucket; phase-1 ends on session n). The tolerant Jaccard (G3) "
        "matches on SPY session POSITION with |Δpos| ≤ n−1, one-to-one greedy "
        "matching, and produces non-zero values."
    )
    out.append("")

    # Files
    out.append("## Files")
    out.append("")
    out.append(f"- `events_panel.parquet` (sha256: `{result['files']['events_panel_sha256'][:16]}…`)")
    out.append(f"- `confirmation_pairs.parquet` (sha256: `{result['files']['confirmation_pairs_sha256'][:16]}…`)")
    out.append(f"- `code/universe_manifest.json` (per-name rows + sha256; listed in hashes.txt)")
    out.append(f"- `result.json`, `RESULT.md`, `hashes.txt`, `summary.json`, `code/run_all.py`")
    out.append("")
    out.append("Tests: " + (result["tests"] or "(pending)"))
    out.append("")

    # L11: mutant → failing test
    out.append("## Tests")
    out.append("")
    mt = result.get("mutant_tests") or {}
    mutants = mt.get("mutants", [])
    if mutants:
        out.append("| mutant | failing test |")
        out.append("|---|---|")
        for row in mutants:
            out.append(f"| {row['mutant']} | `{row['fails']}` |")
        out.append("")
    else:
        out.append("(mutant_results.json not yet folded)")
        out.append("")
    out.append(f"pytest summary (counts only): **{result.get('tests') or 'pending'}**")
    out.append("")
    sha_a = mt.get("l8_sha_a", "")
    sha_b = mt.get("l8_sha_b", "")
    out.append(f"L8 two-process stats-pipeline sha256: `{sha_a}` / `{sha_b}`")
    if sha_a and sha_b:
        out.append("identical" if sha_a == sha_b else "NOT identical")
    out.append("")

    # Provenance
    prov = result.get("provenance", {})
    out.append("## Provenance")
    out.append("")
    out.append(
        f"Host **{prov.get('host', 'm2')}**; python `{prov.get('python', '/opt/homebrew/bin/python3')}` "
        f"{prov.get('python_version', '3.14.7')}; pandas {prov.get('pandas')}; "
        f"numpy {prov.get('numpy')}; pyarrow {prov.get('pyarrow')}; "
        f"scipy {prov.get('scipy')}; pytest {prov.get('pytest')}."
    )
    out.append("")

    # Deviations / Gaps — identical lists to result.json (D6)
    out.append("## Deviations")
    out.append("")
    for i, d in enumerate(result["deviations"], 1):
        out.append(f"{i}. {d}")
    out.append("")

    out.append("## Gaps")
    out.append("")
    for i, g in enumerate(result["gaps"], 1):
        out.append(f"{i}. {g}")
    out.append("")

    text = "\n".join(out)
    (RESULTS_DIR / "RESULT.md").write_text(text)
    print(f"wrote RESULT.md ({len(text)} bytes)")


def main():
    panel = pd.read_parquet(RESULTS_DIR / "events_panel.parquet")
    used_names = get_used_names(panel)

    # Generate universe manifest FIRST so its hash is stable for hashes.txt.
    # Round 4: the universe is unchanged; keep the existing manifest bytes.
    manifest_path = CODE_DIR / "universe_manifest.json"
    if manifest_path.exists():
        manifest_sha = sha256_path(manifest_path)
        print(f"keeping existing universe_manifest.json ({len(used_names)} names)")
    else:
        manifest_sha = write_universe_manifest(
            used_names, REPO / "data" / "baskets" / "ohlcv", manifest_path)

    result = build_result(panel)
    (RESULTS_DIR / "result.json").write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote result.json")
    print(f"pytest summary: {result['tests']}")

    summary = json.loads((RESULTS_DIR / "summary.json").read_text())
    write_result_md(result, summary)
    print(f"universe_manifest sha256: {manifest_sha[:16]}…")


if __name__ == "__main__":
    main()