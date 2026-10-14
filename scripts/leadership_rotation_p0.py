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


def _summarize_cell(sims: List[dict]) -> dict:
    summary: Dict[str, Any] = {
        "n_sims": len(sims),
        "by_group_hypothesis": {},
    }
    for g in _GROUPS:
        for h in _HYPOTHESES:
            key = f"{g}/{h}"
            verdicts: Dict[str, int] = {}
            passes = 0
            honest_ns: List[float] = []
            years: List[float] = []
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
            n = len(sims)
            lo, hi = wilson_interval(passes, n)
            summary["by_group_hypothesis"][key] = {
                "pass_rate": passes / n if n else float("nan"),
                "wilson_95": {"lower": lo, "upper": hi},
                "median_honest_n": float(np.median(honest_ns)) if honest_ns else None,
                "median_window_years": float(np.median(years)) if years else None,
                "verdict_counts": verdicts,
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


def size_check(summaries: Sequence[dict], alpha: float = 0.025) -> dict:
    violations: List[dict] = []
    max_point = 0.0
    for cell in summaries:
        delta = cell.get("delta")
        if delta is None:
            continue
        if float(delta) != 0.0:
            continue
        summ = cell.get("summary", cell)
        by_gh = summ.get("by_group_hypothesis", {})
        for key, row in by_gh.items():
            if not isinstance(row, dict):
                continue
            pr = row.get("pass_rate", 0.0)
            if pr > max_point:
                max_point = pr
            wil = row.get("wilson_95", {})
            lo = wil.get("lower", float("nan"))
            if lo > alpha:
                violations.append(
                    {
                        "cell_id": cell.get("cell_id"),
                        "group_hypothesis": key,
                        "pass_rate": pr,
                        "wilson_lower": lo,
                        "flag": "SIZE_VIOLATION",
                    }
                )
    return {"violations": violations, "max_point_rate": max_point}


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


def _cmd_size(argv: Sequence[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", required=True)
    args = p.parse_args(list(argv))
    summaries: List[dict] = []
    with Path(args.in_path).open() as f:
        for line in f:
            line = line.strip()
            if line:
                summaries.append(json.loads(line))
    print(json.dumps(size_check(summaries), indent=2))
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
