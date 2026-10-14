"""P0 synthetic simulator and prereg §8 power/size grid runner (T11 part 5).

Prereg: research/LEADERSHIP_ROTATION_PREREG_V1.md, frozen at commit
``fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb`` (blob
``9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe``).

DEVELOPMENT HARNESS — no verdict authority.  No market data; synthetic paths only.

Variance of the daily relative log return (num − den) in the null (δ = 0):

    r_num − r_den = (BETA_NUM − BETA_DEN)·m + u = −0.3·m + u

with independent market shock m ~ N(0, SPY_SD²).  Idiosyncratic u has Var(u) = σ_u²
where σ_u² = max(σ² − 0.09·SPY_SD², 1e−12), so

    Var(r_num − r_den) = 0.09·SPY_SD² + σ_u² ≈ σ².

Synthetic pairs do not share physical ETF legs (R13 shared-leg sensitivity uses pair
count only).
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts import leadership_rotation_inference as inf
from scripts import leadership_rotation_study as st
from scripts.leadership_rotation_run import PairSeries, evaluate_family

__all__ = [
    "SIGMAS",
    "DELTAS",
    "RHOS",
    "N_TARGETS",
    "ONSET_RATE",
    "REGIME_MIN",
    "REGIME_MAX",
    "SPY_MU",
    "SPY_SD",
    "BETA_NUM",
    "BETA_DEN",
    "LEG_NOISE_SD",
    "TAIL",
    "GROUP_SIZES",
    "DEFAULT_SIMS_NULL",
    "DEFAULT_SIMS_ALT",
    "PATH_SEED_ROOT",
    "simulate_family",
    "window_for_target",
    "run_cell",
    "grid",
    "size_check",
    "wilson_interval",
    "load_sim_records",
    "summarize_records",
]

SIGMAS = (0.007, 0.010, 0.014)
DELTAS = (0.0, 0.0025, 0.005, 0.010)
RHOS = (0.5, 0.8)
N_TARGETS = (20, 40, 80)
ONSET_RATE = 2 / 252
REGIME_MIN, REGIME_MAX = 40, 120
SPY_MU, SPY_SD = 0.0003, 0.010
BETA_NUM, BETA_DEN = 0.8, 1.1
LEG_NOISE_SD = 0.005
TAIL = 69  # 63 + C + 1 — every formation entry can mature
GROUP_SIZES = {"defensive_sector": 4, "broadening_proxy": 3}
DEFAULT_SIMS_NULL = 200
DEFAULT_SIMS_ALT = 100
PATH_SEED_ROOT = 20261014

_FORMATION_YEARS = (4, 8, 12, 16, 24, 32, 48)
_HYPOTHESES = ("H1", "H2", "H3")
_GROUPS = ("defensive_sector", "broadening_proxy")


def _sigma_u(sigma: float) -> float:
    return math.sqrt(max(sigma * sigma - 0.09 * SPY_SD * SPY_SD, 1e-12))


def _group_regime(
    n: int,
    warmup: int,
    n_formation: int,
    rng: np.random.Generator,
) -> Tuple[List[int], np.ndarray]:
    """Group-level onset process inside [warmup, warmup + n_formation)."""
    onsets: List[int] = []
    regime = np.zeros(n, dtype=bool)
    t = warmup
    end_form = warmup + n_formation
    active_until = -1
    while t < end_form:
        if t <= active_until:
            regime[t] = True
            t += 1
            continue
        if rng.random() < ONSET_RATE:
            length = int(rng.integers(REGIME_MIN, REGIME_MAX + 1))
            onsets.append(t)
            active_until = t + length - 1
            hi = min(active_until + 1, n)
            regime[t:hi] = True
        t += 1
    return onsets, regime


def simulate_family(
    sigma: float,
    delta: float,
    rho: float,
    n_formation: int,
    seed_seq: np.random.SeedSequence,
) -> Tuple[Dict[str, List[PairSeries]], dict]:
    rng = np.random.default_rng(seed_seq)
    n = st.WARMUP + n_formation + TAIL
    m = rng.normal(SPY_MU, SPY_SD, size=n)
    spy_close = 100.0 * np.exp(np.cumsum(m))

    sigma_u = _sigma_u(sigma)
    sqrt_rho = math.sqrt(rho)
    sqrt_1mr = math.sqrt(1.0 - rho)

    groups: Dict[str, List[PairSeries]] = {g: [] for g in GROUP_SIZES}
    truth_onsets: Dict[str, List[int]] = {}
    truth_regime: Dict[str, List[bool]] = {}

    for g, n_pairs in GROUP_SIZES.items():
        onsets, regime = _group_regime(n, st.WARMUP, n_formation, rng)
        truth_onsets[g] = onsets
        truth_regime[g] = regime.tolist()
        f_t = rng.standard_normal(n)
        drift = np.where(regime, delta / 20.0, 0.0)
        for i in range(n_pairs):
            e_it = rng.standard_normal(n)
            v_it = rng.normal(0.0, LEG_NOISE_SD, size=n)
            u = sigma_u * (sqrt_rho * f_t + sqrt_1mr * e_it) + drift
            r_num = BETA_NUM * m + u / 2.0 + v_it
            r_den = BETA_DEN * m - u / 2.0 + v_it
            num = 100.0 * np.exp(np.cumsum(r_num))
            den = 100.0 * np.exp(np.cumsum(r_den))
            groups[g].append(
                PairSeries(
                    pair_id=f"{g}_{i}",
                    group=g,
                    num_sym=f"NUM_{g}_{i}",
                    den_sym=f"DEN_{g}_{i}",
                    num=num,
                    den=den,
                    spy=spy_close,
                )
            )

    truth = {
        "onsets": truth_onsets,
        "regime_mask": truth_regime,
        "n": n,
    }
    return groups, truth


def _honest_n_group(
    pairs: Sequence[PairSeries], hypothesis: str, start: int, end: int
) -> int:
    from scripts.leadership_rotation_run import (
        _cluster_n,
        _evaluate_pair_core,
        _items_matured_a1,
    )

    group = pairs[0].group
    cores = [_evaluate_pair_core(ps, start=start, end=end) for ps in pairs]
    if hypothesis == "H1":
        onset_items: List[inf.Item] = []
        for ps, core in zip(pairs, cores):
            for ph in core["phases"]:
                if ph.qualifies:
                    onset_items.append((group, ps.pair_id, ph.T))
        return _cluster_n(onset_items)
    items, _coords, _values = _items_matured_a1(
        group, pairs, cores, residual=(hypothesis == "H3")
    )
    return _cluster_n(items)


def _both_groups_reach(
    groups: Dict[str, List[PairSeries]], hypothesis: str, end: int, n_target: int
) -> bool:
    for g in _GROUPS:
        plist = groups.get(g, [])
        if not plist:
            return False
        if _honest_n_group(plist, hypothesis, st.WARMUP, end) < n_target:
            return False
    return True


def window_for_target(
    groups: Dict[str, List[PairSeries]],
    n_target: int,
    hypothesis: str,
) -> Optional[int]:
    """Smallest formation end e with both groups honest-N ≥ n_target (ORCH-SCI R10)."""
    if not groups:
        return None
    n = len(next(iter(groups.values()))[0].spy)
    last_e = n - TAIL - 1
    if last_e < st.WARMUP:
        return None
    lo, hi = st.WARMUP, last_e
    if not _both_groups_reach(groups, hypothesis, hi, n_target):
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if _both_groups_reach(groups, hypothesis, mid, n_target):
            hi = mid
        else:
            lo = mid + 1
    return lo


def wilson_interval(
    successes: int, trials: int, alpha: float = 0.05
) -> Tuple[float, float]:
    """Wilson score interval; z = Φ^{-1}(1 − α/2) (default 95 %)."""
    if trials <= 0:
        return (float("nan"), float("nan"))
    z = 1.959963984540054
    phat = successes / trials
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = (phat + z2 / (2 * trials)) / denom
    margin = z * math.sqrt((phat * (1 - phat) / trials + z2 / (4 * trials * trials))) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return (lo, hi)


def _pick_n_formation(groups_fn, n_target: int) -> Optional[int]:
    for years in _FORMATION_YEARS:
        nf = 252 * years
        groups, _truth = groups_fn(nf)
        for h in _HYPOTHESES:
            if window_for_target(groups, n_target, h) is None:
                break
        else:
            return nf
    return None


def _extract_sim_metrics(
    fam: dict, ends: Dict[str, int]
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    holm_order = fam["holm"]["order"]
    raw = fam["holm"]["raw"]
    adj = fam["holm"]["adjusted"]
    raw_map = {(g, h): raw[i] for i, (g, h) in enumerate(holm_order)}
    adj_map = {(g, h): adj[i] for i, (g, h) in enumerate(holm_order)}
    for g in _GROUPS:
        gr = fam["groups"].get(g, {})
        verdicts = fam["verdicts"].get(g, {})
        out[g] = {}
        for h in _HYPOTHESES:
            row: Dict[str, Any] = {
                "verdict": verdicts.get(h),
                "honest_n": gr.get("honest_n", {}).get(h),
                "window_years": (ends[h] - st.WARMUP + 1) / 252.0,
            }
            if h == "H1":
                h1 = gr.get("H1", {})
                row["point"] = h1.get("delay_reduction")
                row["raw_p"] = h1.get("p")
                row["holm_p"] = adj_map.get((g, h))
                row["iut"] = {
                    "cond_a": h1.get("decision", {}).get("cond_a"),
                    "cond_b": h1.get("decision", {}).get("cond_b"),
                    "p_h1": h1.get("decision", {}).get("p_h1"),
                    "delay_reduction": h1.get("delay_reduction"),
                    "burden_cut_b": h1.get("burden_cut_b"),
                }
            elif h == "H2":
                h2 = gr.get("H2", {})
                row["point"] = h2.get("point")
                row["raw_p"] = h2.get("p")
                row["holm_p"] = adj_map.get((g, h))
            else:
                h3 = gr.get("H3", {})
                row["point"] = h3.get("point")
                row["raw_p"] = h3.get("p")
                row["holm_p"] = adj_map.get((g, h))
            out[g][h] = row
    return out


def _run_one_sim(
    sigma: float,
    delta: float,
    rho: float,
    n_target: int,
    cell_id: int,
    k: int,
) -> dict:
    seed = np.random.SeedSequence([PATH_SEED_ROOT, cell_id, k])

    def groups_fn(nf: int):
        return simulate_family(sigma, delta, rho, nf, seed)

    n_formation = _pick_n_formation(groups_fn, n_target)
    if n_formation is None:
        return {
            "cell_id": cell_id,
            "k": k,
            "status": "UNREACHED",
            "n_formation": None,
        }

    groups, truth = simulate_family(sigma, delta, rho, n_formation, seed)
    ends: Dict[str, Optional[int]] = {}
    for h in _HYPOTHESES:
        ends[h] = window_for_target(groups, n_target, h)
    if any(ends[h] is None for h in _HYPOTHESES):
        return {
            "cell_id": cell_id,
            "k": k,
            "status": "UNREACHED",
            "n_formation": n_formation,
        }

    ends_i: Dict[str, int] = {h: int(ends[h]) for h in _HYPOTHESES}
    cache: Dict[int, dict] = {}
    metrics: Dict[str, Any] = {}
    for h in _HYPOTHESES:
        e_h = ends_i[h]
        if e_h not in cache:
            cache[e_h] = evaluate_family(
                groups, start=st.WARMUP, end=e_h, partition="P0"
            )
        fam = cache[e_h]
        part = _extract_sim_metrics(fam, ends_i)
        for g in _GROUPS:
            metrics.setdefault(g, {})[h] = part[g][h]

    return {
        "cell_id": cell_id,
        "k": k,
        "status": "OK",
        "n_formation": n_formation,
        "truth_n": truth["n"],
        "ends": ends_i,
        "groups": metrics,
    }


def _load_done_sims(out: Path, cell_id: int) -> set:
    done: set = set()
    if not out.is_file():
        return done
    with out.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("cell_id") == cell_id and "k" in rec:
                done.add(int(rec["k"]))
    return done


def _finite_median(vals: List[float]) -> Optional[float]:
    finite = [v for v in vals if v is not None and math.isfinite(float(v))]
    if not finite:
        return None
    return float(np.median(finite))


def _summarize_cell(sims: List[dict]) -> dict:
    summary: Dict[str, Any] = {
        "n_sims": len(sims),
        "by_group_hypothesis": {},
    }
    n_ok = sum(1 for s in sims if s.get("status") == "OK")
    alpha_cal = 0.025
    family_passes = 0
    for g in _GROUPS:
        for h in _HYPOTHESES:
            key = f"{g}/{h}"
            verdicts: Dict[str, int] = {}
            passes = 0
            honest_ns: List[float] = []
            years: List[float] = []
            points: List[float] = []
            raw_ps: List[float] = []
            holm_ps: List[float] = []
            cond_a_true = 0
            cond_b_true = 0
            delay_reds: List[float] = []
            burden_cuts: List[float] = []
            for sim in sims:
                if sim.get("status") != "OK":
                    v = sim.get("status", "UNREACHED")
                    verdicts[v] = verdicts.get(v, 0) + 1
                    continue
                row = sim.get("groups", {}).get(g, {}).get(h, {})
                v = row.get("verdict", "UNKNOWN")
                verdicts[v] = verdicts.get(v, 0) + 1
                if v == "DEVELOPMENT_PASS":
                    passes += 1
                if row.get("honest_n") is not None:
                    honest_ns.append(float(row["honest_n"]))
                if row.get("window_years") is not None:
                    years.append(float(row["window_years"]))
                pt = row.get("point")
                if pt is not None and math.isfinite(float(pt)):
                    points.append(float(pt))
                rp = row.get("raw_p")
                if rp is not None and math.isfinite(float(rp)):
                    raw_ps.append(float(rp))
                hp = row.get("holm_p")
                if hp is not None and math.isfinite(float(hp)):
                    holm_ps.append(float(hp))
                if h == "H1":
                    iut = row.get("iut") or {}
                    if iut.get("cond_a") is True:
                        cond_a_true += 1
                    if iut.get("cond_b") is True:
                        cond_b_true += 1
                    dr = iut.get("delay_reduction")
                    if dr is not None and math.isfinite(float(dr)):
                        delay_reds.append(float(dr))
                    bc = iut.get("burden_cut_b")
                    if bc is not None and math.isfinite(float(bc)):
                        burden_cuts.append(float(bc))
            n = len(sims)
            lo, hi = wilson_interval(passes, n)
            # Size check uses pass_rate_ok / wilson_95_ok (OK sims only): UNREACHED
            # sims cannot pass, so all-sim pass_rate would dilute false-pass rate.
            lo_ok, hi_ok = wilson_interval(passes, n_ok)
            row_out: Dict[str, Any] = {
                "passes": passes,
                "n_ok": n_ok,
                "pass_rate": passes / n if n else float("nan"),
                "pass_rate_ok": passes / n_ok if n_ok else float("nan"),
                "wilson_95": {"lower": lo, "upper": hi},
                "wilson_95_ok": {"lower": lo_ok, "upper": hi_ok},
                "median_honest_n": float(np.median(honest_ns)) if honest_ns else None,
                "median_window_years": float(np.median(years)) if years else None,
                "median_point": _finite_median(points),
                "median_raw_p": _finite_median(raw_ps),
                "share_raw_p_lt_alpha": (
                    sum(1 for p in raw_ps if p < alpha_cal) / len(raw_ps) if raw_ps else None
                ),
                "share_holm_p_lt_alpha": (
                    sum(1 for p in holm_ps if p < alpha_cal) / len(holm_ps) if holm_ps else None
                ),
                "verdict_counts": verdicts,
            }
            if h == "H1":
                row_out["cond_a_true"] = cond_a_true
                row_out["cond_b_true"] = cond_b_true
                row_out["median_delay_reduction"] = _finite_median(delay_reds)
                row_out["median_burden_cut_b"] = _finite_median(burden_cuts)
            summary["by_group_hypothesis"][key] = row_out

    for sim in sims:
        if sim.get("status") != "OK":
            continue
        any_pass = False
        for g in _GROUPS:
            for h in _HYPOTHESES:
                row = sim.get("groups", {}).get(g, {}).get(h, {})
                if row.get("verdict") == "DEVELOPMENT_PASS":
                    any_pass = True
                    break
            if any_pass:
                break
        if any_pass:
            family_passes += 1
    n = len(sims)
    flo, fhi = wilson_interval(family_passes, n)
    flo_ok, fhi_ok = wilson_interval(family_passes, n_ok)
    summary["family_any"] = {
        "passes": family_passes,
        "pass_rate": family_passes / n if n else float("nan"),
        "wilson_95": {"lower": flo, "upper": fhi},
        "n_ok": n_ok,
        "pass_rate_ok": family_passes / n_ok if n_ok else float("nan"),
        "wilson_95_ok": {"lower": flo_ok, "upper": fhi_ok},
    }
    return summary


def _run_sim_timed(args: Tuple) -> Tuple[dict, float]:
    t0 = time.perf_counter()
    rec = _run_one_sim(*args)
    return rec, time.perf_counter() - t0


def run_cell(
    sigma: float,
    delta: float,
    rho: float,
    n_target: int,
    sims: int,
    *,
    cell_id: int,
    workers: int = 1,
    out: Optional[Union[str, Path]] = None,
) -> dict:
    out_path = Path(out) if out else None
    done = _load_done_sims(out_path, cell_id) if out_path else set()
    records: List[dict] = []
    if out_path and out_path.is_file():
        with out_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("cell_id") == cell_id:
                    records.append(rec)

    pending = [k for k in range(sims) if k not in done]
    task_args = [
        (sigma, delta, rho, n_target, cell_id, k) for k in pending
    ]

    if workers > 1 and task_args:
        import multiprocessing as mp

        ctx = mp.get_context("spawn")
        with ctx.Pool(workers) as pool:
            for rec, secs in pool.imap(_run_sim_timed, task_args):
                print(f"SIM cell={cell_id} k={rec['k']} secs={secs:.3f}", flush=True)
                records.append(rec)
                if out_path:
                    with out_path.open("a") as fh:
                        fh.write(json.dumps(rec) + "\n")
    else:
        for args in task_args:
            rec, secs = _run_sim_timed(args)
            print(f"SIM cell={cell_id} k={rec['k']} secs={secs:.3f}", flush=True)
            records.append(rec)
            if out_path:
                with out_path.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")

    records.sort(key=lambda r: r.get("k", 0))
    cell_summary = _summarize_cell(records)
    return {
        "cell_id": cell_id,
        "sigma": sigma,
        "delta": delta,
        "rho": rho,
        "n_target": n_target,
        "sims": sims,
        "summary": cell_summary,
        "sim_records": records,
    }


def _iter_grid_cells() -> List[Tuple[int, float, float, float, int]]:
    cells: List[Tuple[int, float, float, float, int]] = []
    cid = 0
    for sigma in SIGMAS:
        for delta in DELTAS:
            for rho in RHOS:
                for n_target in N_TARGETS:
                    cells.append((cid, sigma, delta, rho, n_target))
                    cid += 1
    return cells


def _catalog_map() -> Dict[int, Tuple[float, float, float, int]]:
    return {
        cid: (sigma, delta, rho, n_target)
        for cid, sigma, delta, rho, n_target in _iter_grid_cells()
    }


def _validate_sim_record(rec: dict, catalog: Dict[int, Tuple[float, float, float, int]]) -> None:
    if "cell_id" not in rec or not isinstance(rec["cell_id"], int):
        raise ValueError("record missing int cell_id")
    if rec["cell_id"] not in catalog:
        raise ValueError(f"unknown cell_id {rec['cell_id']}")
    if "k" not in rec or not isinstance(rec["k"], int) or rec["k"] < 0:
        raise ValueError("record missing int k >= 0")
    status = rec.get("status")
    if status not in ("OK", "UNREACHED"):
        raise ValueError(f"invalid status {status!r}")


def load_sim_records(
    paths: Sequence[Union[str, Path]],
) -> Tuple[Dict[int, List[dict]], dict]:
    catalog = _catalog_map()
    by_cell: Dict[int, List[dict]] = {}
    seen: Dict[Tuple[int, int], str] = {}
    stats: Dict[str, Any] = {
        "files": [str(Path(p)) for p in paths],
        "records": 0,
        "cells": 0,
        "duplicates": 0,
        "skipped_partial": 0,
    }
    for path in paths:
        p = Path(path)
        lines = p.read_text().splitlines()
        for lineno, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            is_last = lineno == len(lines)
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                if is_last:
                    stats["skipped_partial"] += 1
                    continue
                raise ValueError(f"{p}:{lineno}") from None
            _validate_sim_record(rec, catalog)
            key = (rec["cell_id"], rec["k"])
            canon = json.dumps(rec, sort_keys=True)
            if key in seen:
                if seen[key] != canon:
                    raise ValueError(f"conflicting duplicate cell_id={key[0]} k={key[1]}")
                stats["duplicates"] += 1
                continue
            seen[key] = canon
            by_cell.setdefault(rec["cell_id"], []).append(rec)
    for cid in by_cell:
        by_cell[cid].sort(key=lambda r: r["k"])
    stats["records"] = len(seen)
    stats["cells"] = len(by_cell)
    return by_cell, stats


def summarize_records(by_cell: Dict[int, List[dict]]) -> List[dict]:
    catalog = _catalog_map()
    out: List[dict] = []
    for cell_id in sorted(by_cell):
        records = by_cell[cell_id]
        sigma, delta, rho, n_target = catalog[cell_id]
        n_ok = sum(1 for r in records if r.get("status") == "OK")
        out.append(
            {
                "cell_id": cell_id,
                "sigma": sigma,
                "delta": delta,
                "rho": rho,
                "n_target": n_target,
                "n_sims": len(records),
                "n_ok": n_ok,
                "n_unreached": len(records) - n_ok,
                "summary": _summarize_cell(records),
            }
        )
    return out


def grid(
    cells: Union[str, Sequence[int]] = "all",
    sims_null: int = DEFAULT_SIMS_NULL,
    sims_alt: int = DEFAULT_SIMS_ALT,
    workers: int = 1,
    out: Optional[Union[str, Path]] = None,
) -> List[dict]:
    catalog = _iter_grid_cells()
    if cells == "all":
        selected = catalog
    else:
        idx = set(int(c) for c in cells)
        selected = [t for t in catalog if t[0] in idx]
    results: List[dict] = []
    for cell_id, sigma, delta, rho, n_target in selected:
        sims = sims_null if delta == 0.0 else sims_alt
        print(
            f"CELL id={cell_id} sigma={sigma} delta={delta} rho={rho} N={n_target} sims={sims}",
            flush=True,
        )
        results.append(
            run_cell(
                sigma,
                delta,
                rho,
                n_target,
                sims,
                cell_id=cell_id,
                workers=workers,
                out=out,
            )
        )
    return results


def _size_row_entries(summary: dict) -> List[Tuple[str, dict]]:
    rows: List[Tuple[str, dict]] = []
    by_gh = summary.get("by_group_hypothesis", {})
    for g in _GROUPS:
        for h in _HYPOTHESES:
            key = f"{g}/{h}"
            row = by_gh.get(key)
            if isinstance(row, dict):
                rows.append((key, row))
    fam = summary.get("family_any")
    if isinstance(fam, dict):
        rows.append(("family_any", fam))
    return rows


def size_check(cell_summaries: Sequence[dict], alpha: float = 0.025) -> dict:
    null_cells = [c for c in cell_summaries if float(c.get("delta", float("nan"))) == 0.0]
    if not null_cells:
        raise ValueError("no delta=0 cells")
    violations: List[dict] = []
    exceeds: List[dict] = []
    max_point_rate_ok = 0.0
    max_family_point_rate_ok = 0.0
    n_null_sims = 0
    n_null_ok = 0
    for cell in null_cells:
        n_null_sims += int(cell.get("n_sims", 0))
        n_null_ok += int(cell.get("n_ok", 0))
        summ = cell.get("summary", {})
        for row_name, row in _size_row_entries(summ):
            pr_ok = float(row.get("pass_rate_ok", 0.0) or 0.0)
            if row_name == "family_any":
                if pr_ok > max_family_point_rate_ok:
                    max_family_point_rate_ok = pr_ok
            elif pr_ok > max_point_rate_ok:
                max_point_rate_ok = pr_ok
            wil = row.get("wilson_95_ok", {})
            lo = float(wil.get("lower", float("nan")))
            passes = int(row.get("passes", 0))
            n_ok = int(row.get("n_ok", 0))
            base = {
                "cell_id": cell.get("cell_id"),
                "sigma": cell.get("sigma"),
                "rho": cell.get("rho"),
                "n_target": cell.get("n_target"),
                "row": row_name,
                "passes": passes,
                "n_ok": n_ok,
                "pass_rate_ok": pr_ok,
                "wilson_lower": lo,
            }
            if lo > alpha:
                flag = (
                    "FAMILY_SIZE_VIOLATION"
                    if row_name == "family_any"
                    else "SIZE_VIOLATION"
                )
                violations.append({**base, "flag": flag})
            elif pr_ok > alpha:
                flag = (
                    "FAMILY_SIZE_EXCEEDS_POINT"
                    if row_name == "family_any"
                    else "SIZE_EXCEEDS_POINT"
                )
                exceeds.append({**base, "flag": flag})
    sized = not violations
    return {
        "alpha": alpha,
        "n_null_cells": len(null_cells),
        "n_null_sims": n_null_sims,
        "n_null_ok": n_null_ok,
        "violations": violations,
        "exceeds_point": exceeds,
        "max_point_rate_ok": max_point_rate_ok,
        "max_family_point_rate_ok": max_family_point_rate_ok,
        "sized": sized,
    }


def _cmd_smoke() -> int:
    result = run_cell(
        0.010,
        0.005,
        0.5,
        20,
        2,
        cell_id=0,
        workers=1,
    )
    print(json.dumps(result["summary"], indent=2))
    return 0


def _cmd_grid(argv: Sequence[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--sims-null", type=int, default=DEFAULT_SIMS_NULL)
    p.add_argument("--sims-alt", type=int, default=DEFAULT_SIMS_ALT)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--out", required=True)
    p.add_argument("--cells", default="all")
    args = p.parse_args(list(argv))
    if args.cells == "all":
        cell_sel: Union[str, List[int]] = "all"
    else:
        cell_sel = [int(x) for x in args.cells.split(",") if x.strip()]
    grid(
        cells=cell_sel,
        sims_null=args.sims_null,
        sims_alt=args.sims_alt,
        workers=args.workers,
        out=args.out,
    )
    return 0


def _parse_in_paths(argv: Sequence[str]) -> Tuple[List[str], argparse.Namespace]:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_paths", action="append", required=True)
    p.add_argument("--alpha", type=float, default=0.025)
    args, rest = p.parse_known_args(list(argv))
    return rest, args


def _load_summaries_from_inputs(in_paths: Sequence[str]) -> Tuple[List[dict], dict]:
    by_cell, stats = load_sim_records(in_paths)
    return summarize_records(by_cell), stats


def _cmd_size(argv: Sequence[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_paths", action="append", required=True)
    p.add_argument("--alpha", type=float, default=0.025)
    args = p.parse_args(list(argv))
    try:
        summaries, _stats = _load_summaries_from_inputs(args.in_paths)
        result = size_check(summaries, alpha=args.alpha)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if not result["sized"]:
        return 1
    return 0


def _md_rate(x: Any) -> str:
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(v):
        return "—"
    return f"{v:.3f}"


def _summary_row_keys() -> List[str]:
    keys = [f"{g}/{h}" for g in _GROUPS for h in _HYPOTHESES]
    keys.append("family_any")
    return keys


def _write_summary_md(
    path: Path,
    stats: dict,
    cells: List[dict],
    size_result: dict,
    in_paths: Sequence[str],
) -> None:
    lines: List[str] = []
    lines.append("# P0 simulation summary")
    lines.append("")
    lines.append(f"Inputs: {', '.join(Path(p).name for p in in_paths)}")
    lines.append(
        f"Records kept: {stats.get('records', 0)}; duplicates: {stats.get('duplicates', 0)}; "
        f"skipped_partial: {stats.get('skipped_partial', 0)}"
    )
    lines.append(f"numpy {np.__version__}")
    lines.append("")
    lines.append("DEVELOPMENT HARNESS — no verdict authority")
    lines.append("")

    row_keys = _summary_row_keys()
    null_cells = [c for c in cells if float(c["delta"]) == 0.0]
    alt_cells = [c for c in cells if float(c["delta"]) > 0.0]

    lines.append("## Table 1 Size (δ = 0)")
    if not null_cells:
        lines.append("_No δ = 0 cells in input._")
    else:
        hdr = (
            "| cell | σ | ρ | N | sims ok/unreached | "
            + " | ".join(row_keys)
            + " |"
        )
        sep = "|---|" * (5 + len(row_keys))
        lines.append(hdr)
        lines.append(sep)
        for c in null_cells:
            summ = c["summary"]
            cells_cols = []
            for rk in row_keys:
                if rk == "family_any":
                    row = summ.get("family_any", {})
                else:
                    row = summ.get("by_group_hypothesis", {}).get(rk, {})
                p = row.get("passes", 0)
                n_ok = row.get("n_ok", c["n_ok"])
                rate = row.get("pass_rate_ok")
                cells_cols.append(f"{p}/{n_ok} ({_md_rate(rate)})")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(c["cell_id"]),
                        _md_rate(c["sigma"]),
                        _md_rate(c["rho"]),
                        str(c["n_target"]),
                        f"{c['n_ok']}/{c['n_unreached']}",
                    ]
                    + cells_cols
                )
                + " |"
            )
        if size_result.get("error"):
            lines.append(f"Size verdict: ERROR ({size_result['error']})")
        elif size_result.get("sized"):
            lines.append("Size verdict: SIZED")
        else:
            flags = [v["flag"] for v in size_result.get("violations", [])]
            lines.append("Size verdict: " + ", ".join(flags) if flags else "NOT SIZED")
    lines.append("")

    lines.append("## Table 2 Power (δ > 0)")
    if not alt_cells:
        lines.append("_No δ > 0 cells in input._")
    else:
        hdr = (
            "| cell | σ | δ | ρ | N | sims ok/unreached | "
            + " | ".join(row_keys)
            + " |"
        )
        sep = "|---|" * (6 + len(row_keys))
        lines.append(hdr)
        lines.append(sep)
        for c in alt_cells:
            summ = c["summary"]
            cells_cols = []
            for rk in row_keys:
                if rk == "family_any":
                    row = summ.get("family_any", {})
                else:
                    row = summ.get("by_group_hypothesis", {}).get(rk, {})
                cells_cols.append(_md_rate(row.get("pass_rate_ok")))
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(c["cell_id"]),
                        _md_rate(c["sigma"]),
                        _md_rate(c["delta"]),
                        _md_rate(c["rho"]),
                        str(c["n_target"]),
                        f"{c['n_ok']}/{c['n_unreached']}",
                    ]
                    + cells_cols
                )
                + " |"
            )
    lines.append("")

    lines.append("## Table 3 H1 intersection–union components")
    if not cells:
        lines.append("_No cells in input._")
    else:
        lines.append(
            "| cell | group | cond_a_true/n_ok | cond_b_true/n_ok | "
            "median delay_reduction | median burden_cut_b |"
        )
        lines.append("|---|---|---|---|---|---|")
        for c in cells:
            summ = c["summary"]["by_group_hypothesis"]
            for g in _GROUPS:
                row = summ.get(f"{g}/H1", {})
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(c["cell_id"]),
                            g,
                            f"{row.get('cond_a_true', 0)}/{c['n_ok']}",
                            f"{row.get('cond_b_true', 0)}/{c['n_ok']}",
                            _md_rate(row.get("median_delay_reduction")),
                            _md_rate(row.get("median_burden_cut_b")),
                        ]
                    )
                    + " |"
                )
    lines.append("")

    lines.append("## Table 4 Calibration (δ = 0)")
    if not null_cells:
        lines.append("_No δ = 0 cells in input._")
    else:
        lines.append(
            "| cell | row | median_raw_p | share_raw_p_lt_alpha | "
            "share_holm_p_lt_alpha | median_honest_n | median_window_years |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for c in null_cells:
            summ = c["summary"]["by_group_hypothesis"]
            for rk in [f"{g}/{h}" for g in _GROUPS for h in _HYPOTHESES]:
                row = summ.get(rk, {})
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(c["cell_id"]),
                            rk,
                            _md_rate(row.get("median_raw_p")),
                            _md_rate(row.get("share_raw_p_lt_alpha")),
                            _md_rate(row.get("share_holm_p_lt_alpha")),
                            _md_rate(row.get("median_honest_n")),
                            _md_rate(row.get("median_window_years")),
                        ]
                    )
                    + " |"
                )
    path.write_text("\n".join(lines) + "\n")


def _cmd_summary(argv: Sequence[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_paths", action="append", required=True)
    p.add_argument("--json", dest="json_out", required=True)
    p.add_argument("--md", dest="md_out", required=True)
    p.add_argument("--alpha", type=float, default=0.025)
    args = p.parse_args(list(argv))
    try:
        by_cell, stats = load_sim_records(args.in_paths)
        cells = summarize_records(by_cell)
        try:
            size_result: dict = size_check(cells, alpha=args.alpha)
        except ValueError as exc:
            size_result = {"error": str(exc)}
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = {"stats": stats, "cells": cells, "size": size_result}
    json_path = Path(args.json_out)
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    _write_summary_md(Path(args.md_out), stats, cells, size_result, args.in_paths)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return 2
    cmd = argv[0]
    if cmd == "smoke":
        return _cmd_smoke()
    if cmd == "grid":
        return _cmd_grid(argv[1:])
    if cmd == "size":
        return _cmd_size(argv[1:])
    if cmd == "summary":
        return _cmd_summary(argv[1:])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
