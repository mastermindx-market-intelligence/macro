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
# Unconditional repo-root pin (tests/test_check_script_import_pinning.py: a
# conditional insert is not a strong pin — a root already further down
# sys.path still loses to a foreign package ahead of it).
sys.path.insert(0, str(_REPO_ROOT))

from scripts import leadership_rotation_inference as inf
from scripts import leadership_rotation_study as st
from scripts.leadership_rotation_run import (
    HARNESS_MODULES,
    PairSeries,
    SIZE_GATE_H1_NULL_METHOD,
    SIZE_GATE_RULE,
    evaluate_family,
)

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
    "G2_SIGMA",
    "G2_RHO",
    "G2_DELTAS",
    "G2_N_TARGETS",
    "G2_CELL_ID_BASE",
    "G2_CELL_IDS",
    "simulate_family",
    "window_for_target",
    "run_cell",
    "grid",
    "size_check",
    "wilson_interval",
    "load_sim_records",
    "summarize_records",
    "harness_identity",
    "write_size_gate_artifact",
    "power_summary",
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
# Prereg V2 §3.3: a δ = 0 row is SIZED only if BOTH the Wilson 95 % lower
# bound of its pass rate is ≤ α AND its point pass rate is ≤ α + 2·√(α(1−α)/M).
# The former advisory label SIZE_EXCEEDS_POINT is retired by the same clause.
SIZE_RULE = "V2_SEC3_TWO_PART"

# prereg V2 §3 cell 2 (N80) must be reachable: H1 honest-N grows ~1.7/yr per
# group, so the V1-era 48-year ceiling left N80 mostly UNREACHED.  64/96 are
# appended (earlier entries unchanged, so every N20/N40 path that reached
# before reaches at the same formation length).
_FORMATION_YEARS = (4, 8, 12, 16, 24, 32, 48, 64, 96)
_HYPOTHESES = ("H1", "H2", "H3")
_GROUPS = ("defensive_sector", "broadening_proxy")

# Imports for the prereg V2 §3 size-gate artifact and the §4 power summary are kept
# in this block so the module header hunk stays free for sibling lanes.
import functools
import hashlib
import subprocess
from datetime import datetime, timezone

# prereg V2 §4 positive-control generator G2: G1 machinery with the planted-drift
# grid extended; ids 100–111 are disjoint from the 72 G1 ids, so the existing
# SeedSequence([PATH_SEED_ROOT, cell_id, k]) gives G2 its own seed streams
G2_SIGMA = 0.007
G2_RHO = 0.5
G2_DELTAS = (0.01, 0.02, 0.04, 0.08)
G2_N_TARGETS = (20, 40, 80)
G2_CELL_ID_BASE = 100


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


class _PairPre:
    """End-independent per-pair inputs to the honest-N search (speed only).

    ``_evaluate_pair_core`` recomputes the whole-series arms (A1 hysteresis on
    the 63-change z, betas, outcomes) for every candidate formation end, yet
    none of them depends on the end: only the window filter, the within-pair
    merge and the zigzag do.  Computing them once per path and re-windowing per
    end reproduces the slow path exactly (pinned by the fast == slow identity
    tests); it changes no arm, threshold, merge or clustering rule.
    """

    __slots__ = ("ps", "R", "invalid", "fe", "a1_entries", "_betas", "_log_spy", "_rec")

    def __init__(self, ps: PairSeries) -> None:
        self.ps = ps
        self.R, self.invalid = st.log_ratio(ps.num, ps.den)
        fe = st.first_eligible(ps.num, ps.den)
        self.fe = None if fe is None else int(fe)
        self.a1_entries: List[int] = []
        if self.fe is not None:
            _state, entries, _exits = st.arm_a1(self.R)
            self.a1_entries = [int(t) for t in entries]
        self._betas: Optional[Tuple[np.ndarray, np.ndarray]] = None
        self._log_spy: Optional[np.ndarray] = None
        self._rec: Dict[int, dict] = {}

    def s0(self, start: int, end: int) -> Optional[int]:
        if self.fe is None:
            return None
        s0 = max(int(start), self.fe)
        return None if s0 > end else s0

    def record(self, t: int) -> dict:
        rec = self._rec.get(t)
        if rec is None:
            from scripts.leadership_rotation_run import _log_returns, _outcome_record

            if self._betas is None:
                ps = self.ps
                lr_spy = _log_returns(ps.spy)
                with np.errstate(divide="ignore", invalid="ignore"):
                    self._log_spy = np.log(
                        np.where(np.isfinite(ps.spy) & (ps.spy > 0), ps.spy, np.nan)
                    )
                self._betas = (
                    st.rolling_beta(_log_returns(ps.num), lr_spy),
                    st.rolling_beta(_log_returns(ps.den), lr_spy),
                )
            bn, bd = self._betas
            rec = _outcome_record(
                self.R,
                self.invalid,
                t,
                st.H_PRIMARY,
                (float(bn[t]), float(bd[t])),
                self._log_spy,
            )
            self._rec[t] = rec
        return rec


def _family_pre(groups: Dict[str, List[PairSeries]]) -> Dict[str, List[_PairPre]]:
    return {g: [_PairPre(ps) for ps in plist] for g, plist in groups.items()}


def _fast_honest_n_group(
    pres: Sequence[_PairPre], hypothesis: str, start: int, end: int
) -> int:
    from scripts import leadership_rotation_episodes as ep
    from scripts.leadership_rotation_run import _cluster_n, _filter_window

    group = pres[0].ps.group
    items: List[inf.Item] = []
    if hypothesis == "H1":
        for pp in pres:
            s0 = pp.s0(start, end)
            if s0 is None:
                continue
            for ph in ep.zigzag(pp.R, start=s0, end=end + 1):
                if ph.qualifies:
                    items.append((group, pp.ps.pair_id, ph.T))
        return _cluster_n(items)
    fld = "y_res_20" if hypothesis == "H3" else "y20"
    for pp in pres:
        s0 = pp.s0(start, end)
        if s0 is None:
            continue
        kept, _merged = ep.merge_within_pair(_filter_window(pp.a1_entries, s0, end))
        for t in kept:
            r = pp.record(int(t))
            if r[fld]["state"] == "MATURED" and r[fld]["y"] is not None:
                items.append((group, pp.ps.pair_id, int(r["t"])))
    return _cluster_n(items)


def _honest_n_group(
    pairs: Sequence[PairSeries],
    hypothesis: str,
    start: int,
    end: int,
    pres: Optional[Sequence[_PairPre]] = None,
) -> int:
    if pres is not None:
        return _fast_honest_n_group(pres, hypothesis, start, end)
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
    groups: Dict[str, List[PairSeries]],
    hypothesis: str,
    end: int,
    n_target: int,
    pre: Optional[Dict[str, List[_PairPre]]] = None,
) -> bool:
    for g in _GROUPS:
        plist = groups.get(g, [])
        if not plist:
            return False
        pres = pre.get(g) if pre is not None else None
        if _honest_n_group(plist, hypothesis, st.WARMUP, end, pres=pres) < n_target:
            return False
    return True


def window_for_target(
    groups: Dict[str, List[PairSeries]],
    n_target: int,
    hypothesis: str,
    pre: Optional[Dict[str, List[_PairPre]]] = None,
) -> Optional[int]:
    """Smallest formation end e with both groups honest-N ≥ n_target (ORCH-SCI R10).

    ``pre`` (from ``_family_pre``) selects the exact cached search; omitted, the
    original per-end ``_evaluate_pair_core`` search runs."""
    if not groups:
        return None
    n = len(next(iter(groups.values()))[0].spy)
    last_e = n - TAIL - 1
    if last_e < st.WARMUP:
        return None
    lo, hi = st.WARMUP, last_e
    if not _both_groups_reach(groups, hypothesis, hi, n_target, pre):
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if _both_groups_reach(groups, hypothesis, mid, n_target, pre):
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


def _pick_formation(groups_fn, n_target: int):
    """First formation length at which every hypothesis reaches ``n_target``.

    Returns ``(n_formation, groups, truth, ends)`` or None.  The groups and ends
    found here are the ones the sim evaluates: re-simulating at the chosen
    length with the same seed is deterministic, so reusing them is identical
    to the former re-simulate-and-re-search."""
    for years in _FORMATION_YEARS:
        nf = 252 * years
        groups, truth = groups_fn(nf)
        pre = _family_pre(groups)
        ends: Dict[str, int] = {}
        for h in _HYPOTHESES:
            e = window_for_target(groups, n_target, h, pre)
            if e is None:
                break
            ends[h] = int(e)
        else:
            return nf, groups, truth, ends
    return None


def _pick_n_formation(groups_fn, n_target: int) -> Optional[int]:
    picked = _pick_formation(groups_fn, n_target)
    return None if picked is None else picked[0]


def _extract_sim_metrics(
    fam: dict, ends: Dict[str, int]
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    def _fin(v: Any) -> Optional[float]:
        """Finite float or None (prereg V2 §3.4 / §6: unmeasured ≠ zero)."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if math.isfinite(f) else None

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
                # prereg V2 §6: C2 strata carried VERBATIM; None when the producer
                # predates the §6 c2_strata key (unmeasured ≠ zero).
                "c2_strata": (gr.get("c2_strata") or {}).get(h),
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
                # prereg V2 §3.4: per-arm metrics; "A0_raw" is A0 before the
                # 5-quiet-session suppression, measured only (arms stay frozen).
                row["per_arm"] = {
                    "A0_raw_burden": _fin((h1.get("A0_raw") or {}).get("burden")),
                    "A0_burden": _fin((h1.get("A0") or {}).get("burden")),
                    "A1_burden": _fin((h1.get("A1") or {}).get("burden")),
                    "A1_median_delay": _fin((h1.get("A1") or {}).get("median_delay")),
                    "A1_detection": _fin((h1.get("A1") or {}).get("detection")),
                    "A2_median_delay": _fin((h1.get("A2") or {}).get("median_delay")),
                }
                # prereg V2 §2 / §8 item 11: the Option A null's K, seed, matched
                # values and (1 − α) quantiles, per (sim, group). Absent (None)
                # when H1 ran on the superseded V1 bootstrap.
                nul = h1.get("null")
                row["h1_null"] = (
                    {
                        k2: nul.get(k2)
                        for k2 in (
                            "method", "K", "status", "reason", "p_a", "p_b", "p_h1",
                            "seed", "matched", "quantiles", "n_unreached", "n_nan_a",
                            "n_nan_b", "n_real_over_N", "bank_key",
                        )
                    }
                    if isinstance(nul, dict)
                    else None
                )
                row["p_bootstrap_superseded"] = h1.get("p_bootstrap_superseded")
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
    null_k: Optional[int] = None,
) -> dict:
    """One δ-cell path. ``null_k`` (prereg V2 §2) evaluates H1 against the Option A
    surrogate null with K = ``null_k`` null paths; ``None`` keeps the superseded
    V1 bootstrap p-values (development only — the §3 size gate refuses those)."""
    seed = np.random.SeedSequence([PATH_SEED_ROOT, cell_id, k])
    h1_null = None
    stamp: Dict[str, Any] = {}
    if null_k is not None:
        from scripts.leadership_rotation_null import make_h1_null_provider

        h1_null = make_h1_null_provider(int(null_k))
        stamp = {"h1_null_method": SIZE_GATE_H1_NULL_METHOD, "h1_null_k": int(null_k)}

    def groups_fn(nf: int):
        return simulate_family(sigma, delta, rho, nf, seed)

    picked = _pick_formation(groups_fn, n_target)
    if picked is None:
        return {
            "cell_id": cell_id,
            "k": k,
            "status": "UNREACHED",
            "n_formation": None,
            **stamp,
        }

    n_formation, groups, truth, ends_i = picked
    cache: Dict[int, dict] = {}
    metrics: Dict[str, Any] = {}
    for h in _HYPOTHESES:
        e_h = ends_i[h]
        if e_h not in cache:
            cache[e_h] = evaluate_family(
                groups, start=st.WARMUP, end=e_h, partition="P0", h1_null=h1_null
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
        **stamp,
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
    # prereg V2 §3.4 per-arm keys and §6 C2 strata order (both fixed by spec).
    per_arm_keys = (
        "A0_raw_burden",
        "A0_burden",
        "A1_burden",
        "A1_median_delay",
        "A1_detection",
        "A2_median_delay",
    )
    c2_strata_order = ("both_up", "both_down", "mixed", "unmeasured")

    def _finite(v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if math.isfinite(f) else None

    def _c2_summary(strata_rows: List[dict], hyp: str) -> Optional[dict]:
        """Median C2 stratum summary over OK sims; None when no sim carries strata."""
        if not strata_rows:
            return None
        point_keys = ("delay_reduction", "burden_cut_b") if hyp == "H1" else ("point",)
        out: Dict[str, Any] = {}
        for stratum in c2_strata_order:
            entries = [
                sr[stratum] for sr in strata_rows if isinstance(sr.get(stratum), dict)
            ]
            if not entries:
                continue
            status_counts: Dict[str, int] = {}
            for e in entries:
                status = e.get("status")
                key_s = status if isinstance(status, str) else str(status)
                status_counts[key_s] = status_counts.get(key_s, 0) + 1
            block: Dict[str, Any] = {
                "status_counts": status_counts,
                "median_n": _finite_median(
                    [v for v in (_finite(e.get("n")) for e in entries) if v is not None]
                ),
            }
            for pk in point_keys:
                block[f"median_{pk}"] = _finite_median(
                    [v for v in (_finite(e.get(pk)) for e in entries) if v is not None]
                )
            block["n_sims"] = len(entries)
            out[stratum] = block
        return out or None

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
            per_arm_vals: Dict[str, List[float]] = {k: [] for k in per_arm_keys}
            per_arm_n = 0
            c2_rows: List[dict] = []
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
                    per_arm = row.get("per_arm")
                    if isinstance(per_arm, dict):
                        per_arm_n += 1
                        for pk in per_arm_keys:
                            pv = _finite(per_arm.get(pk))
                            if pv is not None:
                                per_arm_vals[pk].append(pv)
                c2s = row.get("c2_strata")
                if isinstance(c2s, dict):
                    c2_rows.append(c2s)
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
                row_out["per_arm_median"] = {
                    k: _finite_median(per_arm_vals.get(k, [])) for k in per_arm_keys
                }
                row_out["per_arm_n"] = per_arm_n
            row_out["c2_summary"] = _c2_summary(c2_rows, h)
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
    k_start: int = 0,
    null_k: Optional[int] = None,
) -> dict:
    """Simulate ``sims`` paths for one cell over the k-range ``[k_start, k_start + sims)``.

    ``k_start`` splits a cell's M paths across processes — prereg V2 §3.2 needs
    M ≥ 400 fresh δ = 0 paths per cell and cell 2 (N = 80) is slow. The k index is
    the seed component, so disjoint k-ranges are disjoint seed streams and their
    union is the same M-path sample one process would have drawn. Records read
    back from ``out`` and records returned are both restricted to this cell AND
    this k-range. Every newly written record carries the ``harness_id`` of the
    working-tree harness bytes that produced it, which is what allows the §3
    size-gate artifact to pin a simulation to the exact code that ran it.
    """
    if not isinstance(k_start, int) or isinstance(k_start, bool) or k_start < 0:
        raise ValueError(f"k_start must be an int >= 0, got {k_start!r}")
    out_path = Path(out) if out else None
    done = _load_done_sims(out_path, cell_id) if out_path else set()
    k_lo, k_hi = k_start, k_start + sims
    records: List[dict] = []
    if out_path and out_path.is_file():
        with out_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("cell_id") != cell_id:
                    continue
                k = rec.get("k")
                if isinstance(k, int) and k_lo <= k < k_hi:
                    records.append(rec)

    pending = [k for k in range(k_lo, k_hi) if k not in done]
    if null_k is not None and (isinstance(null_k, bool) or not isinstance(null_k, int) or null_k < 1):
        raise ValueError(f"null_k must be a positive int or None, got {null_k!r}")
    # null_k rides only when set, so the V1-shaped 6-tuple is unchanged.
    extra: Tuple = (null_k,) if null_k is not None else ()
    task_args = [
        (sigma, delta, rho, n_target, cell_id, k) + extra for k in pending
    ]

    if workers > 1 and task_args:
        import multiprocessing as mp

        ctx = mp.get_context("spawn")
        with ctx.Pool(workers) as pool:
            for rec, secs in pool.imap(_run_sim_timed, task_args):
                print(f"SIM cell={cell_id} k={rec['k']} secs={secs:.3f}", flush=True)
                rec["harness_id"] = _runtime_harness_id()
                records.append(rec)
                if out_path:
                    with out_path.open("a") as fh:
                        fh.write(json.dumps(rec) + "\n")
    else:
        for args in task_args:
            rec, secs = _run_sim_timed(args)
            print(f"SIM cell={cell_id} k={rec['k']} secs={secs:.3f}", flush=True)
            rec["harness_id"] = _runtime_harness_id()
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


def _iter_g2_cells() -> List[Tuple[int, float, float, float, int]]:
    """Prereg V2 §4 positive-control generator G2 (a binding addition to V1 §8).

    G1 with the planted drift grid extended to δ per 20 sessions ∈ {1, 2, 4, 8} %,
    at σ = 0.70 % and ρ = 0.5 for N ∈ {20, 40, 80} — the two cells where H1 failed
    plus the unreached cell 2. Ids 100–111 are disjoint from the 72 G1 ids, so the
    existing SeedSequence([PATH_SEED_ROOT, cell_id, k]) gives every G2 path its own
    seed stream. G2 makes no realism claim: it asks only whether the registered
    H2/H3 statistics can detect ANY planted rotation, because under G1 they sized
    but their power was unidentifiable.
    """
    cells: List[Tuple[int, float, float, float, int]] = []
    for d_idx, delta in enumerate(G2_DELTAS):
        for n_idx, n_target in enumerate(G2_N_TARGETS):
            cid = G2_CELL_ID_BASE + d_idx * len(G2_N_TARGETS) + n_idx
            cells.append((cid, G2_SIGMA, delta, G2_RHO, n_target))
    return cells


G2_CELL_IDS = tuple(c[0] for c in _iter_g2_cells())


def _catalog_map() -> Dict[int, Tuple[float, float, float, int]]:
    return {
        cid: (sigma, delta, rho, n_target)
        for cid, sigma, delta, rho, n_target in _iter_grid_cells() + _iter_g2_cells()
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
    if "harness_id" in rec:
        hid = rec["harness_id"]
        if (
            not isinstance(hid, str)
            or len(hid) != 64
            or any(c not in "0123456789abcdef" for c in hid)
        ):
            raise ValueError(f"invalid harness_id {hid!r}")
    if "h1_null_method" in rec:
        method = rec["h1_null_method"]
        if not isinstance(method, str) or not method:
            raise ValueError(f"invalid h1_null_method {method!r}")
    if "h1_null_k" in rec:
        nk = rec["h1_null_k"]
        if isinstance(nk, bool) or not isinstance(nk, int) or nk < 1:
            raise ValueError(f"invalid h1_null_k {nk!r}")


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
    k_start: int = 0,
    null_k: Optional[int] = None,
) -> List[dict]:
    """Run the selected cells in ascending cell-id order.

    ``cells`` is ``"all"`` (the 72 G1 cells, unchanged), ``"g2"`` (the 12 prereg
    V2 §4 positive-control cells), or an explicit sequence of catalog ids. An id
    outside the catalog is now an error rather than a silently skipped cell: a
    re-size or power run that quietly drops a required cell is worse than one that
    refuses to start. ``k_start`` is passed through to ``run_cell`` so one cell's
    M ≥ 400 paths can be split across processes (prereg V2 §3.2).
    """
    if cells == "all":
        selected = _iter_grid_cells()
    elif cells == "g2":
        selected = _iter_g2_cells()
    else:
        catalog = _catalog_map()
        wanted: List[int] = []
        for c in cells:
            cid = int(c)
            if cid not in catalog:
                raise ValueError(f"unknown cell id {cid}")
            if cid not in wanted:
                wanted.append(cid)
        selected = [(cid,) + catalog[cid] for cid in sorted(wanted)]
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
                k_start=k_start,
                null_k=null_k,
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


def size_check(
    cell_summaries: Sequence[dict],
    alpha: float = 0.025,
    min_m: Optional[int] = None,
    required_cells: Optional[Sequence[int]] = None,
) -> dict:
    """Prereg V2 §3.3 two-part size gate over the δ = 0 cells.

    A (hypothesis, group) row — and the ``family_any`` row — is SIZED only if BOTH
    (i) the Wilson 95 % lower bound of its pass rate is ≤ α AND (ii) its point pass
    rate is ≤ α + 2·√(α(1−α)/M), where M is the row's OK-simulation count. A row
    failing either part is ``SIZE_VIOLATION`` (``FAMILY_SIZE_VIOLATION`` for
    ``family_any``). The former advisory label ``SIZE_EXCEEDS_POINT`` is retired by
    the same clause: a point exceedance is gated, not merely printed. A row whose M
    is 0, or below ``min_m``, is ``SIZE_NOT_EXECUTABLE`` — an unmeasurable row is
    never a sized one.
    """

    def _finite(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        return v if math.isfinite(v) else None

    null_cells = [c for c in cell_summaries if float(c.get("delta", float("nan"))) == 0.0]
    if not null_cells:
        raise ValueError("no delta=0 cells")
    rows: List[dict] = []
    violations: List[dict] = []
    not_executable: List[dict] = []
    max_point_rate_ok = 0.0
    max_family_point_rate_ok = 0.0
    n_null_sims = 0
    n_null_ok = 0
    for cell in null_cells:
        n_sims = int(cell.get("n_sims", 0))
        n_null_sims += n_sims
        n_null_ok += int(cell.get("n_ok", 0))
        summ = cell.get("summary", {})
        for row_name, row in _size_row_entries(summ):
            passes = int(row.get("passes", 0))
            m = int(row.get("n_ok", 0))
            point = _finite(row.get("pass_rate_ok"))
            if point is None and m > 0:
                point = passes / m
            wil = row.get("wilson_95_ok")
            wilson_lower = _finite(wil.get("lower")) if isinstance(wil, dict) else None
            if wilson_lower is None and m > 0:
                wilson_lower = wilson_interval(passes, m)[0]
            envelope = (
                alpha + 2.0 * math.sqrt(alpha * (1.0 - alpha) / m) if m > 0 else None
            )
            part_i_ok = None if wilson_lower is None else bool(wilson_lower <= alpha)
            part_ii_ok = (
                None
                if point is None or envelope is None
                else bool(point <= envelope)
            )
            if point is not None:
                if row_name == "family_any":
                    if point > max_family_point_rate_ok:
                        max_family_point_rate_ok = point
                elif point > max_point_rate_ok:
                    max_point_rate_ok = point
            if m == 0 or (min_m is not None and m < min_m):
                flag = "SIZE_NOT_EXECUTABLE"
            elif part_i_ok and part_ii_ok:
                flag = "SIZED"
            elif row_name == "family_any":
                flag = "FAMILY_SIZE_VIOLATION"
            else:
                flag = "SIZE_VIOLATION"
            entry = {
                "cell_id": cell.get("cell_id"),
                "sigma": cell.get("sigma"),
                "rho": cell.get("rho"),
                "n_target": cell.get("n_target"),
                "n_sims": n_sims,
                "row": row_name,
                "passes": passes,
                "m": m,
                "pass_rate_ok": point,
                "wilson_lower": wilson_lower,
                "envelope": envelope,
                "part_i_ok": part_i_ok,
                "part_ii_ok": part_ii_ok,
                "flag": flag,
            }
            rows.append(entry)
            if flag == "SIZE_NOT_EXECUTABLE":
                not_executable.append(entry)
            elif flag != "SIZED":
                violations.append(entry)
    present_ids = {c.get("cell_id") for c in null_cells}
    if required_cells is None:
        req_sorted: Optional[List[int]] = None
        missing_cells: List[int] = []
    else:
        req_sorted = sorted({int(cid) for cid in required_cells})
        missing_cells = [cid for cid in req_sorted if cid not in present_ids]
    sized = (not violations) and (not not_executable) and (not missing_cells)
    return {
        "alpha": alpha,
        "rule": SIZE_RULE,
        "n_null_cells": len(null_cells),
        "n_null_sims": n_null_sims,
        "n_null_ok": n_null_ok,
        "rows": rows,
        "violations": violations,
        "not_executable": not_executable,
        "missing_cells": missing_cells,
        "min_m": min_m,
        "required_cells": req_sorted,
        "exceeds_point_retired": True,
        "max_point_rate_ok": max_point_rate_ok,
        "max_family_point_rate_ok": max_family_point_rate_ok,
        "sized": sized,
    }


def harness_identity(
    repo_root: Union[str, Path] = _REPO_ROOT,
    *,
    require_clean: bool = True,
) -> dict:
    """Fingerprint of the harness bytes in ``repo_root`` (prereg V2 §3.6 gate).

    ``blobs[p]`` is the ``git hash-object`` blob sha of the working-tree bytes of
    each module in ``HARNESS_MODULES`` and ``id`` is the sha256 over those blobs in
    path order. With ``require_clean`` every working blob must equal the committed
    ``HEAD:<p>`` blob, so an artifact can only be written from a checkout whose
    harness bytes are the bytes its own HEAD records — which is what lets the P1
    reader pin a live read to the exact code that produced the re-size.
    """
    root = Path(repo_root)

    def _git(*args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise ValueError(f"GIT_FAILED {' '.join(args)}: {proc.stderr.strip()}")
        return proc.stdout.strip()

    blobs: Dict[str, str] = {}
    for p in HARNESS_MODULES:
        data = Path(root, p).read_bytes()
        blobs[p] = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    head = _git("rev-parse", "HEAD")
    if require_clean:
        for p in HARNESS_MODULES:
            if _git("rev-parse", f"HEAD:{p}") != blobs[p]:
                raise ValueError(f"HARNESS_DIRTY {p}")
    ident = hashlib.sha256(
        "\n".join(f"{p} {blobs[p]}" for p in sorted(blobs)).encode()
    ).hexdigest()
    return {"head": head, "blobs": blobs, "id": ident}


@functools.lru_cache(maxsize=1)
def _runtime_harness_id() -> str:
    """``id`` of the working-tree harness bytes under ``_REPO_ROOT`` (no git call).

    Stamped on every simulated record so the record can later be matched against the
    checkout that produced it. Reads bytes only: a dirty tree still has an identity,
    it is simply not the identity of any commit, and ``harness_identity`` with
    ``require_clean`` is what refuses to write an artifact from it.
    """
    blobs: Dict[str, str] = {}
    for p in HARNESS_MODULES:
        data = Path(_REPO_ROOT, p).read_bytes()
        blobs[p] = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    return hashlib.sha256(
        "\n".join(f"{p} {blobs[p]}" for p in sorted(blobs)).encode()
    ).hexdigest()


def write_size_gate_artifact(
    size_result: dict,
    cell_summaries: Sequence[dict],
    *,
    by_cell: Dict[int, List[dict]],
    stats: dict,
    in_paths: Sequence[str],
    out: Union[str, Path],
    repo_root: Union[str, Path] = _REPO_ROOT,
) -> dict:
    """Write the prereg V2 §3 size-gate artifact that the P1 reader pins against.

    The artifact is the only bridge between "the re-size passed" and "a P1 read may
    run" (§3.6): it carries the two-part gate result, the δ = 0 cells and M behind
    it, the single H1 null method those simulations actually used, the three prereg
    blob pins, the sha256 of every input file, and the harness identity (HEAD +
    per-module blobs + digest) of the checkout that produced them.

    Every check runs before any byte is written, so a refused artifact leaves no
    partial file behind. A record whose ``harness_id`` is not this checkout's id is
    refused — a simulation produced by other code can never be pinned to this code —
    and so is a δ = 0 population mixing two H1 null methods, because then no single
    method describes the gate (the P1 reader requires
    ``SIZE_GATE_H1_NULL_METHOD``). A re-size that FAILED (``sized`` False) IS
    written: a failing gate is reported, never hidden.
    """
    ident = harness_identity(repo_root, require_clean=True)
    rule = size_result["rule"]
    if rule != SIZE_GATE_RULE:
        raise ValueError(f"SIZE_RULE_MISMATCH {rule} != {SIZE_GATE_RULE}")
    catalog = _catalog_map()
    null_records: List[Tuple[int, dict]] = [
        (cid, rec)
        for cid, recs in by_cell.items()
        if cid in catalog and float(catalog[cid][1]) == 0.0
        for rec in recs
    ]
    for cid, rec in null_records:
        if rec.get("harness_id") != ident["id"]:
            raise ValueError(f"HARNESS_MISMATCH cell={cid} k={rec.get('k')}")
    methods = {
        rec.get("h1_null_method", "V1_BOOTSTRAP_SUPERSEDED")
        for _, rec in null_records
    }
    if len(methods) != 1:
        raise ValueError(f"MIXED_H1_NULL_METHOD {sorted(methods)}")
    null_ks = {rec.get("h1_null_k") for _, rec in null_records}
    h1_null_k: Optional[int] = None
    if next(iter(methods)) == SIZE_GATE_H1_NULL_METHOD:
        from scripts.leadership_rotation_null import NULL_K_MIN

        bad_k = sorted(
            {repr(k) for k in null_ks if isinstance(k, bool) or not isinstance(k, int) or k < NULL_K_MIN}
        )
        if bad_k:
            raise ValueError(f"NULL_K_TOO_SMALL {bad_k} (prereg V2 §2: K >= {NULL_K_MIN})")
        h1_null_k = min(null_ks)
    null_summaries = sorted(
        (
            c
            for c in cell_summaries
            if float(c.get("delta", float("nan"))) == 0.0
        ),
        key=lambda c: int(c.get("cell_id")),
    )
    files: List[dict] = []
    for p in in_paths:
        data = Path(p).read_bytes()
        files.append(
            {
                "path": str(p),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    artifact = {
        "schema": "leadership_rotation.size_gate.v1",
        "rule": rule,
        "alpha": size_result["alpha"],
        "sized": bool(size_result["sized"]),
        "min_m": size_result["min_m"],
        "required_cells": size_result["required_cells"],
        "cells": [
            {
                "cell_id": int(c.get("cell_id")),
                "sigma": c.get("sigma"),
                "delta": c.get("delta"),
                "rho": c.get("rho"),
                "n_target": c.get("n_target"),
                "n_sims": int(c.get("n_sims", 0)),
                "n_ok": int(c.get("n_ok", 0)),
            }
            for c in null_summaries
        ],
        "rows": size_result["rows"],
        "violations": size_result["violations"],
        "not_executable": size_result["not_executable"],
        "missing_cells": size_result["missing_cells"],
        "h1_null_method": next(iter(methods)),
        "h1_null_k": h1_null_k,
        "prereg": {
            "v1_blob": st.PREREG_BLOB_SHA,
            "v2_blob": st.PREREG_V2_BLOB_SHA,
            "v2_1_blob": st.PREREG_V2_1_BLOB_SHA,
        },
        "harness": {"head": ident["head"], "blobs": ident["blobs"]},
        "inputs": {
            "files": files,
            "records": stats["records"],
            "duplicates": stats["duplicates"],
            "skipped_partial": stats["skipped_partial"],
        },
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return artifact


def power_summary(
    cell_summaries: Sequence[dict],
    *,
    threshold: float = 0.50,
    max_delta: float = 0.04,
    max_n: int = 40,
    min_m: int = 100,
) -> dict:
    """Prereg V2 §4.3/§4.4 power curve and POWERED_IN_PRINCIPLE disposition.

    H2 (resp. H3) is ``POWERED_IN_PRINCIPLE`` iff its pass rate reaches ≥ 0.50 at
    some δ ≤ 4.0 % in some G2 cell with N ≤ 40 and M ≥ 100; if every eligible slot
    is measured and none reaches the threshold it is ``NOT_EXECUTABLE`` at the
    registered margins — a RESULT to report, never a reason to lower a margin. If
    any eligible slot is missing or under M it is ``NOT_EVALUATED`` and the
    unmeasured slot ids are named, because a slot that was not measured is never
    counted as a failure. H1 is run through the same arithmetic for information
    only: the §4.3 rule is written for H2/H3.

    This function is reporting arithmetic. It never lowers a margin, a threshold or
    α, and it never widens the eligible slot set.
    """
    catalog = _catalog_map()
    curve: List[dict] = []
    by_slot: Dict[Tuple[str, str, int], dict] = {}
    for cell in cell_summaries:
        cid = int(cell["cell_id"])
        meta = catalog.get(cid)
        if meta is not None:
            sigma, delta, rho, n_target = meta
        else:
            sigma = cell.get("sigma")
            delta = float(cell.get("delta", float("nan")))
            rho = cell.get("rho")
            n_target = int(cell.get("n_target", 0))
        if not delta > 0.0:
            continue
        generator = "G2" if cid in G2_CELL_IDS else "G1"
        for row_name, row in _size_row_entries(cell.get("summary", {})):
            passes = int(row.get("passes", 0))
            m = int(row.get("n_ok", 0))
            lo: Optional[float] = None
            hi: Optional[float] = None
            if m > 0:
                lo, hi = wilson_interval(passes, m)
            entry = {
                "generator": generator,
                "cell_id": cid,
                "sigma": sigma,
                "delta": delta,
                "rho": rho,
                "n_target": n_target,
                "row": row_name,
                "passes": passes,
                "m": m,
                "pass_rate_ok": (passes / m) if m > 0 else None,
                "wilson_lower": lo,
                "wilson_upper": hi,
                "below_min_m": m < min_m,
            }
            curve.append(entry)
            if row_name == "family_any":
                continue
            g, _, h = row_name.partition("/")
            by_slot[(h, g, cid)] = entry
    curve.sort(
        key=lambda e: (
            e["generator"],
            e["n_target"],
            e["delta"],
            e["cell_id"],
            e["row"],
        )
    )
    eligible = [
        cid
        for cid in G2_CELL_IDS
        if catalog[cid][1] <= max_delta + 1e-12 and catalog[cid][3] <= max_n
    ]
    dispositions: Dict[str, Any] = {}
    for h in _HYPOTHESES:
        by_group: Dict[str, dict] = {}
        group_dispositions: List[str] = []
        for g in _GROUPS:
            measured: List[dict] = []
            unmeasured: List[int] = []
            for cid in eligible:
                entry = by_slot.get((h, g, cid))
                if entry is None or entry["m"] <= 0 or entry["below_min_m"]:
                    unmeasured.append(cid)
                else:
                    measured.append(entry)
            powered = [e for e in measured if e["pass_rate_ok"] >= threshold]
            if powered:
                disposition = "POWERED_IN_PRINCIPLE"
            elif not unmeasured:
                disposition = "NOT_EXECUTABLE"
            else:
                disposition = "NOT_EVALUATED"
            best: Optional[dict] = None
            if measured:
                top = max(
                    measured,
                    key=lambda e: (e["pass_rate_ok"], -e["delta"], -e["n_target"]),
                )
                best = {
                    "cell_id": top["cell_id"],
                    "delta": top["delta"],
                    "n_target": top["n_target"],
                    "pass_rate_ok": top["pass_rate_ok"],
                    "wilson_lower": top["wilson_lower"],
                    "wilson_upper": top["wilson_upper"],
                }
            by_group[g] = {
                "disposition": disposition,
                "best": best,
                "unmeasured_cells": unmeasured,
            }
            group_dispositions.append(disposition)
        if "POWERED_IN_PRINCIPLE" in group_dispositions:
            hyp_disposition = "POWERED_IN_PRINCIPLE"
        elif all(d == "NOT_EXECUTABLE" for d in group_dispositions):
            hyp_disposition = "NOT_EXECUTABLE"
        else:
            hyp_disposition = "NOT_EVALUATED"
        hyp_entry: Dict[str, Any] = {
            "disposition": hyp_disposition,
            "by_group": by_group,
        }
        if h == "H1":
            hyp_entry["label"] = (
                "H1: same arithmetic as V2 §4.3, reported for information; "
                "the §4.3 rule is written for H2/H3"
            )
        dispositions[h] = hyp_entry
    return {
        "rule": "V2_SEC4_POWERED_IN_PRINCIPLE",
        "threshold": threshold,
        "max_delta": max_delta,
        "max_n": max_n,
        "min_m": min_m,
        "curve": curve,
        "dispositions": dispositions,
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
    p.add_argument(
        "--cells",
        default="all",
        help=(
            "all (the 72 G1 cells) | g2 (the 12 prereg V2 §4 positive-control "
            "cells) | comma-separated catalog cell ids"
        ),
    )
    p.add_argument(
        "--k-start",
        dest="k_start",
        type=int,
        default=0,
        help=(
            "first k index of this process's slice of every selected cell "
            "(prereg V2 §3.2: M ≥ 400 per δ = 0 cell, split across processes)"
        ),
    )
    p.add_argument(
        "--null-k",
        dest="null_k",
        type=int,
        default=1000,
        help=(
            "prereg V2 §2 Option A: K null paths per H1 read (default 1000, the "
            "minimum the §3 size gate accepts); 0 = the superseded V1 bootstrap "
            "(development only — the size gate refuses those records)"
        ),
    )
    args = p.parse_args(list(argv))
    if args.null_k < 0:
        p.error("--null-k must be >= 0")
    if args.cells == "all":
        cell_sel: Union[str, List[int]] = "all"
    elif args.cells == "g2":
        cell_sel = "g2"
    else:
        cell_sel = [int(x) for x in args.cells.split(",") if x.strip()]
    grid(
        cells=cell_sel,
        sims_null=args.sims_null,
        sims_alt=args.sims_alt,
        workers=args.workers,
        out=args.out,
        k_start=args.k_start,
        null_k=(args.null_k or None),
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
    p.add_argument(
        "--min-m",
        dest="min_m",
        type=int,
        default=None,
        help="rows with fewer OK sims than this are SIZE_NOT_EXECUTABLE (prereg V2 §3.2)",
    )
    p.add_argument(
        "--require-cells",
        dest="require_cells",
        default=None,
        help="comma-separated δ = 0 cell ids that must be present (prereg V2 §3.1)",
    )
    p.add_argument(
        "--out",
        default=None,
        help=(
            "write the prereg V2 §3 size-gate artifact (schema "
            "leadership_rotation.size_gate.v1) that the P1 reader pins against; "
            f"that reader requires h1_null_method {SIZE_GATE_H1_NULL_METHOD}"
        ),
    )
    p.add_argument(
        "--repo-root",
        dest="repo_root",
        default=str(_REPO_ROOT),
        help="checkout whose harness bytes are pinned (tests/diagnostics)",
    )
    args = p.parse_args(list(argv))
    required_cells = (
        [int(x) for x in str(args.require_cells).split(",") if x.strip() != ""]
        if args.require_cells is not None
        else None
    )
    try:
        by_cell, stats = load_sim_records(args.in_paths)
        summaries = summarize_records(by_cell)
        result = size_check(
            summaries,
            alpha=args.alpha,
            min_m=args.min_m,
            required_cells=required_cells,
        )
        # Every gate runs before the first byte is written: a refused artifact
        # leaves no file behind, and a NOT SIZED result is still written because a
        # failing re-size is reported, never hidden (prereg V2 §3.6).
        if args.out:
            write_size_gate_artifact(
                result,
                summaries,
                by_cell=by_cell,
                stats=stats,
                in_paths=args.in_paths,
                out=args.out,
                repo_root=args.repo_root,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if not result["sized"]:
        return 1
    return 0


def _cmd_power(argv: Sequence[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_paths", action="append", required=True)
    p.add_argument(
        "--min-m",
        dest="min_m",
        type=int,
        default=100,
        help=(
            "a G2 slot with fewer OK sims than this is unmeasured, so its "
            "hypothesis is NOT_EVALUATED rather than NOT_EXECUTABLE (prereg V2 §4.2)"
        ),
    )
    p.add_argument(
        "--out",
        default=None,
        help="optional JSON path for the prereg V2 §4.4 power curve and dispositions",
    )
    args = p.parse_args(list(argv))
    try:
        by_cell, _stats = load_sim_records(args.in_paths)
        result = power_summary(summarize_records(by_cell), min_m=args.min_m)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        )
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


def _md_pts(x: Any) -> str:
    """Log-ratio value to study points (1 point = 0.01 log)."""
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(v):
        return "—"
    return f"{v * 100:.2f}"


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
    power: Optional[dict] = None,
) -> None:
    lines: List[str] = []
    lines.append("# P0 simulation summary")
    lines.append("")
    lines.append(f"Inputs: {', '.join(Path(p).name for p in in_paths)}")
    lines.append(
        f"Records kept: {stats.get('records', 0)}; duplicates: {stats.get('duplicates', 0)}; "
        f"skipped_partial: {stats.get('skipped_partial', 0)}"
    )
    import pandas as pd

    py_ver = ".".join(str(x) for x in sys.version_info[:3])
    lines.append(
        f"summary host: numpy {np.__version__}, pandas {pd.__version__}, python {py_ver}"
    )
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
            "| cell | σ | ρ | N | row | passes / M | point | Wilson lower | "
            "envelope | (i) lower ≤ α | (ii) point ≤ envelope | flag |"
        )
        n_cols = hdr.count("|") - 1
        lines.append(hdr)
        lines.append("|" + "|".join(["---"] * n_cols) + "|")
        for entry in size_result.get("rows") or []:
            part_cols = []
            for key in ("part_i_ok", "part_ii_ok"):
                val = entry.get(key)
                part_cols.append("—" if val is None else ("yes" if val else "no"))
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(entry.get("cell_id")),
                        _md_pts(entry.get("sigma")),
                        _md_rate(entry.get("rho")),
                        str(entry.get("n_target")),
                        str(entry.get("row")),
                        f"{entry.get('passes', 0)}/{entry.get('m', 0)}",
                        _md_rate(entry.get("pass_rate_ok")),
                        _md_rate(entry.get("wilson_lower")),
                        _md_rate(entry.get("envelope")),
                        part_cols[0],
                        part_cols[1],
                        str(entry.get("flag")),
                    ]
                )
                + " |"
            )
        lines.append(
            "Size rule: prereg V2 §3 two-part rule (i) Wilson 95 % lower ≤ α AND "
            "(ii) point ≤ α + 2·√(α(1−α)/M). The former advisory label "
            "SIZE_EXCEEDS_POINT is retired (V2 §3.3); a point exceedance is now "
            "gated."
        )
        if size_result.get("error"):
            lines.append(f"Size verdict: ERROR ({size_result['error']})")
        else:
            alpha = float(size_result.get("alpha", 0.025))
            alpha_s = _md_rate(alpha)
            violations = size_result.get("violations") or []
            not_exec = size_result.get("not_executable") or []
            missing = size_result.get("missing_cells") or []
            min_m = size_result.get("min_m")
            if size_result.get("sized"):
                lines.append(
                    f"Size verdict: SIZED (prereg V2 §3: every δ = 0 row satisfies "
                    f"both parts at α = {alpha_s})"
                )
            else:
                lines.append(
                    f"Size verdict: NOT SIZED (prereg V2 §3: every δ = 0 row must "
                    f"satisfy both parts at α = {alpha_s})"
                )
            for entry in violations + not_exec:
                m = int(entry.get("m", 0) or 0)
                note = ""
                if entry.get("flag") == "SIZE_NOT_EXECUTABLE":
                    note = (
                        " (no OK simulations)"
                        if m == 0
                        else f" (M {m} < min_m {min_m})"
                    )
                lines.append(
                    f"- cell {entry.get('cell_id')} "
                    f"(σ {_md_pts(entry.get('sigma'))}, "
                    f"ρ {_md_rate(entry.get('rho'))}, N {entry.get('n_target')}) "
                    f"{entry.get('row')}: {entry.get('passes', 0)}/{m}, "
                    f"point {_md_rate(entry.get('pass_rate_ok'))}, "
                    f"Wilson 95 % lower {_md_rate(entry.get('wilson_lower'))}, "
                    f"envelope {_md_rate(entry.get('envelope'))} — "
                    f"{entry.get('flag')}{note}"
                )
            for cell_id in missing:
                lines.append(
                    f"- missing cell {cell_id}: required for the §3 re-size but no "
                    f"δ = 0 record was loaded — row, passes/M, point, Wilson lower "
                    f"and envelope are all unavailable (NOT_EXECUTABLE; a field "
                    f"that cannot be truthfully filled is never filled with a "
                    f"substitute value)"
                )
    lines.append("")

    lines.append("## Table 2 Power (δ > 0)")
    if not alt_cells:
        lines.append("_No δ > 0 cells in input._")
    else:
        hdr = (
            "| cell | σ (pts) | δ (pts) | ρ | N | sims ok/unreached | "
            + " | ".join(row_keys)
            + " |"
        )
        n_cols = 6 + len(row_keys)
        lines.append(hdr)
        lines.append("|" + "|".join(["---"] * n_cols) + "|")
        for c in alt_cells:
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
                        _md_pts(c["sigma"]),
                        _md_pts(c["delta"]),
                        _md_rate(c["rho"]),
                        str(c["n_target"]),
                        f"{c['n_ok']}/{c['n_unreached']}",
                    ]
                    + cells_cols
                )
                + " |"
            )
    lines.append("")

    lines.append("## Table 2b Power curve and V2 §4 disposition")
    if not power or power.get("error"):
        lines.append("_No power summary._")
        if power and power.get("error"):
            lines.append(f"Power verdict: ERROR ({power['error']})")
    else:
        curve = power.get("curve") or []
        if not curve:
            lines.append("_No δ > 0 cells in input._")
        else:
            hdr = (
                "| generator | cell | δ (pts) | N | row | passes/M | point | "
                "Wilson 95 % |"
            )
            n_cols = hdr.count("|") - 1
            lines.append(hdr)
            lines.append("|" + "|".join(["---"] * n_cols) + "|")
            for entry in curve:
                lo = entry.get("wilson_lower")
                hi = entry.get("wilson_upper")
                wilson = (
                    "n/a"
                    if lo is None or hi is None
                    else f"[{_md_rate(lo)}, {_md_rate(hi)}]"
                )
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(entry.get("generator")),
                            str(entry.get("cell_id")),
                            _md_pts(entry.get("delta")),
                            str(entry.get("n_target")),
                            str(entry.get("row")),
                            f"{entry.get('passes', 0)}/{entry.get('m', 0)}",
                            _md_rate(entry.get("pass_rate_ok")),
                            wilson,
                        ]
                    )
                    + " |"
                )
        for h in _HYPOTHESES:
            hyp = (power.get("dispositions") or {}).get(h) or {}
            by_group = hyp.get("by_group") or {}
            parts = "; ".join(
                f"{g} {(by_group.get(g) or {}).get('disposition')}" for g in _GROUPS
            )
            line = f"- {h}: {hyp.get('disposition')} ({parts})"
            if hyp.get("label"):
                line = f"{line} — {hyp['label']}"
            lines.append(line)
        lines.append(
            "Disposition rule: prereg V2 §4.3 — POWERED_IN_PRINCIPLE iff the pass "
            "rate reaches ≥ 0.50 at some δ ≤ 4.0 % in some G2 cell with N ≤ 40 and "
            "M ≥ min_m; NOT_EXECUTABLE only when every eligible slot is measured "
            "and none reaches it; NOT_EVALUATED otherwise, naming the unmeasured "
            "slots. Margins are the practical-significance bar and are never "
            "lowered to make a generator pass."
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
    lines.append("")
    lines.append("## Table 5 Per-arm metrics (prereg V2 §3.4)")
    if not cells:
        lines.append("_No cells in input._")
    else:
        lines.append(
            "| cell | σ | δ | ρ | N | group | A0 raw burden | A0 burden | "
            "A1 burden | A1 median delay | A1 detection | A2 median delay | sims |"
        )
        lines.append("|" + "|".join(["---"] * 13) + "|")
        for c in cells:
            summ = c["summary"]["by_group_hypothesis"]
            for g in _GROUPS:
                row = summ.get(f"{g}/H1", {})
                per_arm = row.get("per_arm_median") or {}
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(c["cell_id"]),
                            _md_rate(c["sigma"]),
                            _md_rate(c["delta"]),
                            _md_rate(c["rho"]),
                            str(c["n_target"]),
                            g,
                            _md_rate(per_arm.get("A0_raw_burden")),
                            _md_rate(per_arm.get("A0_burden")),
                            _md_rate(per_arm.get("A1_burden")),
                            _md_rate(per_arm.get("A1_median_delay")),
                            _md_rate(per_arm.get("A1_detection")),
                            _md_rate(per_arm.get("A2_median_delay")),
                            str(row.get("per_arm_n", 0)),
                        ]
                    )
                    + " |"
                )
        lines.append(
            'Medians over OK sims. "A0 raw" = A0 fires before the 5-quiet-session '
            'suppression, through the same window filter, merge and classifier as A0 '
            '("suppressed"); burden = REPEATED + LATE + FALSE_START per measured '
            "pair-year."
        )

    lines.append("")
    lines.append("## Table 6 C2 direction strata (prereg V2 §6)")
    lines.append(
        "Prereg V2 §6 direction stratification (CHAL GATES #2); NOT the sealed "
        "Trend-Persistence-era study also called 'C2', which stays closed. Points "
        "only, no p-values; SOURCE_LIMITED where the stratum's clustered n < 5."
    )
    c2_row_keys = [f"{g}/{h}" for g in _GROUPS for h in _HYPOTHESES]
    c2_strata_order = ("both_up", "both_down", "mixed", "unmeasured")
    c2_present = any(
        (c["summary"]["by_group_hypothesis"].get(rk) or {}).get("c2_summary")
        for c in cells
        for rk in c2_row_keys
    )
    if not c2_present:
        lines.append(
            "_C2 strata absent from the input records (producer predates prereg V2 §6)._"
        )
    else:
        lines.append(
            "| cell | row | stratum | sims | status counts | median n | "
            "median point(s) |"
        )
        lines.append("|" + "|".join(["---"] * 7) + "|")
        for c in cells:
            summ = c["summary"]["by_group_hypothesis"]
            for rk in c2_row_keys:
                row = summ.get(rk) or {}
                c2_sum = row.get("c2_summary") or {}
                hyp = rk.split("/")[1]
                for stratum in c2_strata_order:
                    blk = c2_sum.get(stratum)
                    if not isinstance(blk, dict):
                        continue
                    counts = blk.get("status_counts") or {}
                    counts_s = (
                        ", ".join(f"{k}: {counts[k]}" for k in sorted(counts)) or "—"
                    )
                    if hyp == "H1":
                        points_s = (
                            f"{_md_rate(blk.get('median_delay_reduction'))} / "
                            f"{_md_rate(blk.get('median_burden_cut_b'))}"
                        )
                    else:
                        points_s = _md_rate(blk.get("median_point"))
                    lines.append(
                        "| "
                        + " | ".join(
                            [
                                str(c["cell_id"]),
                                rk,
                                stratum,
                                str(blk.get("n_sims", 0)),
                                counts_s,
                                _md_rate(blk.get("median_n")),
                                points_s,
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
    p.add_argument(
        "--min-m",
        dest="min_m",
        type=int,
        default=None,
        help="rows with fewer OK sims than this are SIZE_NOT_EXECUTABLE (prereg V2 §3.2)",
    )
    p.add_argument(
        "--require-cells",
        dest="require_cells",
        default=None,
        help="comma-separated δ = 0 cell ids that must be present (prereg V2 §3.1)",
    )
    args = p.parse_args(list(argv))
    required_cells = (
        [int(x) for x in str(args.require_cells).split(",") if x.strip() != ""]
        if args.require_cells is not None
        else None
    )
    try:
        by_cell, stats = load_sim_records(args.in_paths)
        cells = summarize_records(by_cell)
        try:
            size_result: dict = size_check(
                cells,
                alpha=args.alpha,
                min_m=args.min_m,
                required_cells=required_cells,
            )
        except ValueError as exc:
            size_result = {"error": str(exc)}
        try:
            power_result: dict = power_summary(cells)
        except ValueError as exc:
            power_result = {"error": str(exc)}
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = {
        "stats": stats,
        "cells": cells,
        "size": size_result,
        "power": power_result,
    }
    json_path = Path(args.json_out)
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    _write_summary_md(
        Path(args.md_out), stats, cells, size_result, args.in_paths, power=power_result
    )
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
    if cmd == "power":
        return _cmd_power(argv[1:])
    if cmd == "summary":
        return _cmd_summary(argv[1:])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
