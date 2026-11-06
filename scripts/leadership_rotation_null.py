"""Prereg V2 §2 Option A — the parametric δ = 0 surrogate null for H1.

Development harness only (the P0 synthetic grid and the gated P1 read). V1 drew
H1's p-values from a stationary bootstrap of the observed arms; T12 showed that
null centred on the wrong value, so the δ = 0 rows failed size (V2 §1). Option A
(V2 §2) keeps both H1 statistics and both margins and replaces only the null:

* T_a = A2 median delay − A1 median delay (A1's median-delay reduction vs A2);
* T_b = 1 − burden_A1 / burden_A0;
* K ≥ 1,000 null paths from generator G1 at δ = 0 (the planted-regime machinery
  switched off; the same arm code, the same clustering, the same within-pair
  merge), with σ, ρ and N matched to the read:
    σ = median over the group's registered pairs of sd(daily ΔR) over the
        partition's FORMATION window,
    ρ = median within-group pairwise correlation of daily ΔR, same window,
    N = the read's realised H1 honest-N cluster count;
* seed = 20261014 + crc32("partition|group"); null path j draws from
  ``SeedSequence(entropy=seed, spawn_key=(j,))``;
* p = (1 + #{null ≥ observed}) / (1 + K) per condition; H1's Holm entry is
  max(p_a, p_b). Outcomes (Y_h) play no part in matching (V2 §7 invalidator 8):
  only ΔR moments and the onset cluster count are read.

Precision clauses (pinned in prereg V2.1 because V2 does not spell them out):

1. ΔR uses t ∈ (s0, end] with R_t and R_{t−1} both finite; sd uses ddof = 1;
   ρ̂ is the median of the pairwise-complete Pearson correlations (≥ 2 pairs).
2. Matching is to G1's own parameters. G1's σ is sd(ΔR) by construction, so
   σ_b = σ̂ rounded to the 0.0005 grid. G1's ρ is the correlation of the
   idiosyncratic factor, not of ΔR: ΔR also carries the common market term
   (β_num − β_den)·m whose variance is MARKET_VAR = 0.09·SPY_SD² = 9e-6, so
   ρ_gen = (ρ̂·σ_b² − MARKET_VAR)/(σ_b² − MARKET_VAR), clipped to [0, 0.95] and
   rounded to the 0.05 grid. σ_b² ≤ MARKET_VAR is NOT_EXECUTABLE (p = 1).
3. Null pairs are fully measured from index 0, so every null pair's formation
   window opens at WARMUP. A null path is scanned forward and evaluated at e*_N,
   the FIRST index (after every onset admitted there) at which the honest-N
   cluster count reaches N; the count realised there (N_real ≥ N) is recorded.
   Honest-N is not monotone in e (a new onset can bridge two clusters), so this
   first-reach rule is the null's definition of "the window at which N is
   reached"; the P0 grid's ``window_for_target`` bisection may land elsewhere on
   the same path — a disclosed definitional difference, not an identity claim.
4. A null path that never reaches N inside 96 formation years, and a null
   statistic that is NaN, both count as ≥ observed (conservative). An observed
   statistic that is NaN gives p = 1.
5. Null alarms are classified with ``off_index=None`` — the off-index only sets
   the FALSE_START subtype, which never enters burden, delay or detection.
6. The null (1 − α) quantile is ``numpy.quantile(finite values, 0.975)``.

Null paths are generated in fixed 252-row chunks of standard normals, so a path
of any length is an exact prefix of every longer path from the same seed: every
H1 arm is past-only and the zig-zag state at e depends on R[≤ e], so the
statistic at e*_N does not depend on how far a path was simulated (the rung
ladder only changes compute; ``tests/test_leadership_rotation_null.py`` pins it).
"""

from __future__ import annotations

import bisect
import fcntl
import hashlib
import json
import math
import os
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
# Unconditional repo-root pin (tests/test_check_script_import_pinning.py).
sys.path.insert(0, str(_REPO_ROOT))

from scripts import leadership_rotation_episodes as ep
from scripts import leadership_rotation_inference as inf
from scripts import leadership_rotation_study as st
from scripts import leadership_rotation_run as run
from scripts import leadership_rotation_p0 as p0

__all__ = [
    "METHOD",
    "NULL_K_DEFAULT",
    "NULL_K_MIN",
    "MARKET_VAR",
    "SIGMA_GRID",
    "RHO_GRID",
    "RHO_MAX",
    "N_BLOCK",
    "SHARD_PATHS",
    "seed_entropy",
    "null_seed_sequence",
    "null_family",
    "zigzag_trace",
    "PairTrace",
    "trace_pair",
    "first_reach",
    "h1_stats_at",
    "read_moments",
    "match_params",
    "path_results",
    "bank_paths",
    "h1_null_p",
    "make_h1_null_provider",
]

METHOD = run.SIZE_GATE_H1_NULL_METHOD  # "V2_OPTION_A"
NULL_K_DEFAULT = 1000
NULL_K_MIN = run.SIZE_GATE_MIN_NULL_K  # prereg V2 §2: K ≥ 1,000 for any gated record
ALPHA = inf.ALPHA_ONE_SIDED
MARKET_VAR = (p0.BETA_NUM - p0.BETA_DEN) ** 2 * p0.SPY_SD ** 2  # 9e-6
SIGMA_GRID = 0.0005
RHO_GRID = 0.05
RHO_MAX = 0.95
CHUNK_ROWS = 252
N_BLOCK = 8  # null banks are computed for 8 consecutive N values at once
SHARD_PATHS = 125
_YEARS = tuple(int(y) for y in p0._FORMATION_YEARS)


# ---------------------------------------------------------------------------
# Seeds and the δ = 0 generator


def seed_entropy(partition: str, group: str) -> Tuple[int, int]:
    """(seed, crc) with seed = 20261014 + crc32("partition|group") (V2 §2)."""
    crc = zlib.crc32(f"{partition}|{group}".encode("utf-8")) & 0xFFFFFFFF
    return p0.PATH_SEED_ROOT + crc, crc


def null_seed_sequence(seed: int, j: int) -> np.random.SeedSequence:
    """Null path j. A size path is ``SeedSequence([20261014, cell_id, k])`` (three
    entropy words, no spawn key); this one is the padded entropy word(s) of ``seed``
    plus the spawn key ``(j,)``, so the two assembled pools never coincide."""
    return np.random.SeedSequence(entropy=int(seed), spawn_key=(int(j),))


def _null_normals(seed: int, j: int, n: int, width: int) -> np.ndarray:
    rng = np.random.default_rng(null_seed_sequence(seed, j))
    n_chunks = max(1, -(-int(n) // CHUNK_ROWS))
    z = np.concatenate([rng.standard_normal((CHUNK_ROWS, width)) for _ in range(n_chunks)])
    return z[: int(n)]


def null_family(
    n_pairs: int, sigma: float, rho: float, n: int, seed: int, j: int, group: str = "null"
) -> List[run.PairSeries]:
    """One δ = 0 G1 group of ``n_pairs`` pairs, ``n`` sessions long.

    Same algebra as ``leadership_rotation_p0.simulate_family`` with the drift term
    removed (δ = 0 ⇒ drift ≡ 0, so the regime draw is skipped); the normals come
    from one prefix-invariant chunked stream instead of per-series draws."""
    width = 2 + 2 * int(n_pairs)
    z = _null_normals(seed, j, n, width)
    m = p0.SPY_MU + p0.SPY_SD * z[:, 0]
    spy = 100.0 * np.exp(np.cumsum(m))
    sigma_u = p0._sigma_u(float(sigma))
    a = math.sqrt(float(rho))
    b = math.sqrt(1.0 - float(rho))
    f_t = z[:, 1]
    out: List[run.PairSeries] = []
    for i in range(int(n_pairs)):
        e_it = z[:, 2 + i]
        v_it = p0.LEG_NOISE_SD * z[:, 2 + int(n_pairs) + i]
        u = sigma_u * (a * f_t + b * e_it)
        r_num = p0.BETA_NUM * m + u / 2.0 + v_it
        r_den = p0.BETA_DEN * m - u / 2.0 + v_it
        out.append(
            run.PairSeries(
                pair_id=f"{group}_{i}",
                group=group,
                num_sym=f"NUM_{group}_{i}",
                den_sym=f"DEN_{group}_{i}",
                num=100.0 * np.exp(np.cumsum(r_num)),
                den=100.0 * np.exp(np.cumsum(r_den)),
                spy=spy,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Zig-zag with its per-step state recorded


def zigzag_trace(R, start: int, end: int, amplitude: float = ep.AMPLITUDE, min_up: int = ep.MIN_UP):
    """``ep.zigzag(R, start=start, end=end)`` with the state after every step kept.

    Returns ``(completed, count, mode, trough, rmax)``: ``completed`` is the list of
    confirmed (uncensored) phases; for every index i in [start, end) ``count[i]`` is
    how many were confirmed after step i and ``mode/trough/rmax[i]`` the state after
    step i. ``phases_at(e)`` rebuilds ``ep.zigzag(R, start=start, end=e + 1)``
    exactly from these. The arithmetic is ep.zigzag's, line for line."""
    R = np.asarray(R, dtype=float)
    n = int(R.shape[0])
    count = np.zeros(n, dtype=np.int64)
    mode_a = np.zeros(n, dtype=np.int8)
    trough_a = np.full(n, -1, dtype=np.int64)
    rmax_a = np.full(n, -1, dtype=np.int64)
    phases: List[ep.UpPhase] = []
    mode = 0
    run_min = None
    run_max = None
    trough = None
    for i in range(int(start), int(end)):
        x = R[i]
        if np.isfinite(x):
            if mode == 0:
                if run_min is None or x < run_min[0]:
                    run_min = (x, i)
                if run_max is None or x > run_max[0]:
                    run_max = (x, i)
                if x >= run_min[0] + amplitude:
                    trough = run_min[1]
                    mode = 1
                    run_max = ep._extreme(trough + 1, i + 1, R, want_max=True)
                elif x <= run_max[0] - amplitude:
                    peak0 = run_max[1]
                    mode = -1
                    run_min = ep._extreme(peak0 + 1, i + 1, R, want_max=False)
            elif mode == 1:
                if x > run_max[0]:
                    run_max = (x, i)
                elif x <= run_max[0] - amplitude:
                    peak = run_max[1]
                    phases.append(ep.UpPhase(trough, peak, float(R[peak] - R[trough]),
                                             False, (peak - trough) >= min_up))
                    mode = -1
                    run_min = ep._extreme(peak + 1, i + 1, R, want_max=False)
            else:
                if x < run_min[0]:
                    run_min = (x, i)
                elif x >= run_min[0] + amplitude:
                    trough = run_min[1]
                    mode = 1
                    run_max = ep._extreme(trough + 1, i + 1, R, want_max=True)
        count[i] = len(phases)
        mode_a[i] = mode
        if mode == 1:
            trough_a[i] = trough
            rmax_a[i] = run_max[1]
    return phases, count, mode_a, trough_a, rmax_a


@dataclass
class PairTrace:
    R: np.ndarray
    s0: int
    eligible: bool
    completed: List[ep.UpPhase]
    count: np.ndarray
    mode: np.ndarray
    trough: np.ndarray
    rmax: np.ndarray
    finite_cum: np.ndarray
    a1: List[int]
    a2: List[int]
    a0: List[int]
    scan_end: int

    def phases_at(self, e: int) -> List[ep.UpPhase]:
        """``ep.zigzag(R, start=s0, end=e + 1)`` for s0 ≤ e ≤ scan_end."""
        if not self.eligible or e < self.s0:
            return []
        if e > self.scan_end:
            raise ValueError(f"e={e} beyond the traced range (scan_end={self.scan_end})")
        out = list(self.completed[: int(self.count[e])])
        if int(self.mode[e]) == 1:
            T = int(self.trough[e])
            P = int(self.rmax[e])
            out.append(ep.UpPhase(T, P, float(self.R[P] - self.R[T]), True, (P - T) >= ep.MIN_UP))
        return out

    def measured(self, e: int) -> int:
        """# finite R in [s0, e] — this pair's share of evaluate_group's session weight."""
        if not self.eligible or e < self.s0:
            return 0
        lo = int(self.finite_cum[self.s0 - 1]) if self.s0 > 0 else 0
        return int(self.finite_cum[e]) - lo

    def onset_events(self) -> List[Tuple[int, int]]:
        """(first index at which onset T qualifies, T) for every qualifying onset.

        A qualifying phase is open (mode UP) with rmax − T ≥ MIN_UP before it is
        confirmed, rmax never retreats inside an up spell, and a confirmed phase keeps
        its T and P — so membership of T in the qualifying set is monotone in e."""
        if not self.eligible:
            return []
        lo, hi = self.s0, self.scan_end + 1
        mode = self.mode[lo:hi]
        tr = self.trough[lo:hi]
        rm = self.rmax[lo:hi]
        idx = np.flatnonzero((mode == 1) & (rm - tr >= ep.MIN_UP))
        if idx.size == 0:
            return []
        T = tr[idx]
        uT, first = np.unique(T, return_index=True)
        return [(int(lo + idx[f]), int(t)) for f, t in zip(first, uT)]


def trace_pair(ps: run.PairSeries, *, start: int, scan_end: int) -> PairTrace:
    R, _invalid = st.log_ratio(ps.num, ps.den)
    n = int(len(R))
    scan_end = min(int(scan_end), n - 1)
    fe = st.first_eligible(ps.num, ps.den)
    eligible = fe is not None and max(int(start), int(fe)) <= scan_end
    s0 = max(int(start), int(fe)) if fe is not None else scan_end + 1
    a1_state, a1_entries, _a1_exits = st.arm_a1(R)
    _a0_raw, a0_onsets = st.arm_a0(R)
    a2_alarms, _a2_pending = st.arm_a2(a1_state, a1_entries)
    if eligible:
        completed, count, mode, trough, rmax = zigzag_trace(R, s0, scan_end + 1)
    else:
        completed, count = [], np.zeros(n, dtype=np.int64)
        mode = np.zeros(n, dtype=np.int8)
        trough = np.full(n, -1, dtype=np.int64)
        rmax = np.full(n, -1, dtype=np.int64)
    return PairTrace(
        R=R, s0=s0, eligible=bool(eligible), completed=completed, count=count, mode=mode,
        trough=trough, rmax=rmax, finite_cum=np.cumsum(np.isfinite(R)),
        a1=[int(t) for t in a1_entries], a2=[int(t) for t in a2_alarms],
        a0=[int(t) for t in a0_onsets], scan_end=scan_end,
    )


def first_reach(traces: Sequence[PairTrace], Ns: Sequence[int]) -> Dict[int, Tuple[int, int]]:
    """{N: (e*_N, N_real)} — the first index, after every onset admitted there, at
    which the group's honest-N (single-linkage clusters of the qualifying onsets,
    radius CLUSTER_RADIUS) reaches N. Unreached N are absent."""
    radius = inf.CLUSTER_RADIUS
    events = sorted(ev for tr in traces for ev in tr.onset_events())
    pending = sorted(set(int(N) for N in Ns))
    out: Dict[int, Tuple[int, int]] = {}
    ts: List[int] = []
    gaps = 0  # count of consecutive gaps > radius
    i = 0
    while i < len(events) and pending:
        s = events[i][0]
        while i < len(events) and events[i][0] == s:
            x = events[i][1]
            pos = bisect.bisect_left(ts, x)
            a = ts[pos - 1] if pos > 0 else None
            b = ts[pos] if pos < len(ts) else None
            if a is not None and b is not None and b - a > radius:
                gaps -= 1
            if a is not None and x - a > radius:
                gaps += 1
            if b is not None and b - x > radius:
                gaps += 1
            ts.insert(pos, x)
            i += 1
        cnt = 1 + gaps
        while pending and pending[0] <= cnt:
            out[pending.pop(0)] = (int(s), int(cnt))
    return out


def h1_stats_at(traces: Sequence[PairTrace], e: int) -> Tuple[float, float]:
    """(T_a, T_b) of evaluate_group's H1 point estimates for window end ``e``."""
    recs: Dict[str, List[dict]] = {"a1": [], "a2": [], "a0": []}
    phases_all: List[ep.UpPhase] = []
    session_w = 0
    for tr in traces:
        ph = tr.phases_at(e)
        phases_all.extend(ph)
        if tr.eligible and tr.s0 <= e:
            for key, items in (("a1", tr.a1), ("a2", tr.a2), ("a0", tr.a0)):
                kept, _merged = ep.merge_within_pair(run._filter_window(items, tr.s0, e))
                recs[key].extend(ep.classify_alarms(kept, ph, off_index=None))
        session_w += tr.measured(e)
    sw = float(session_w)
    m1 = run._episode_metrics_unit(recs["a1"], phases_all, sw)
    m2 = run._episode_metrics_unit(recs["a2"], phases_all, sw)
    m0 = run._episode_metrics_unit(recs["a0"], phases_all, sw)
    t_a = float(m2["median_delay"] - m1["median_delay"])
    b0 = m0["burden"]
    t_b = (
        float(1.0 - m1["burden"] / b0)
        if b0 and np.isfinite(b0) and b0 != 0
        else float("nan")
    )
    return t_a, t_b


# ---------------------------------------------------------------------------
# Matching


def read_moments(cores: Sequence[dict], end: int) -> dict:
    """σ̂ and ρ̂ of daily ΔR over each pair's formation window (s0, end]."""
    sds: List[float] = []
    series: List[np.ndarray] = []
    for c in cores:
        fm = c.get("formation") or {}
        if not fm.get("eligible"):
            continue
        R = np.asarray(c["R"], dtype=float)
        s0 = int(fm["start"])
        hi = min(int(end), len(R) - 1)
        if hi <= s0:
            continue
        d = np.full(len(R), np.nan)
        t = np.arange(s0 + 1, hi + 1)
        d[t] = R[t] - R[t - 1]
        fin = np.isfinite(d)
        if int(fin.sum()) >= 2:
            sds.append(float(np.std(d[fin], ddof=1)))
            series.append(d)
    corrs: List[float] = []
    for i in range(len(series)):
        for k in range(i + 1, len(series)):
            both = np.isfinite(series[i]) & np.isfinite(series[k])
            if int(both.sum()) >= 3:
                x, y = series[i][both], series[k][both]
                if np.std(x) > 0 and np.std(y) > 0:
                    corrs.append(float(np.corrcoef(x, y)[0, 1]))
    return {
        "sigma_hat": float(np.median(sds)) if sds else float("nan"),
        "rho_hat": float(np.median(corrs)) if corrs else float("nan"),
        "n_pairs_measured": len(sds),
        "n_correlations": len(corrs),
    }


def match_params(sigma_hat: float, rho_hat: float) -> dict:
    """G1 parameters (σ_b, ρ_b) matched to the read, on the pinned grids."""
    out = {"sigma_gen": float("nan"), "rho_gen": float("nan"),
           "sigma_b": float("nan"), "rho_b": float("nan"),
           "status": "NOT_EXECUTABLE", "reason": None}
    if not (math.isfinite(sigma_hat) and math.isfinite(rho_hat)):
        out["reason"] = "sigma_hat or rho_hat unmeasured (fewer than 2 measured pairs)"
        return out
    sigma_b = round(round(sigma_hat / SIGMA_GRID) * SIGMA_GRID, 6)
    out["sigma_gen"] = float(sigma_hat)
    out["sigma_b"] = float(sigma_b)
    if sigma_b * sigma_b <= MARKET_VAR:
        out["reason"] = f"sigma_b={sigma_b} at or below the G1 market floor sqrt({MARKET_VAR})"
        return out
    rho_gen = (rho_hat * sigma_b * sigma_b - MARKET_VAR) / (sigma_b * sigma_b - MARKET_VAR)
    rho_c = min(max(rho_gen, 0.0), RHO_MAX)
    rho_b = round(min(max(round(rho_c / RHO_GRID) * RHO_GRID, 0.0), RHO_MAX), 6)
    out.update({"rho_gen": float(rho_gen), "rho_b": float(rho_b), "status": "OK"})
    return out


# ---------------------------------------------------------------------------
# Null paths and the shared bank


def path_results(
    n_pairs: int, sigma_b: float, rho_b: float, seed: int, j: int, Ns: Sequence[int],
    rung_hint: int = 0,
) -> Tuple[int, Dict[str, Optional[List[Optional[float]]]]]:
    """(rung index used, {str(N): [T_a, T_b, N_real, e*] or None if unreached})."""
    Ns = sorted(set(int(N) for N in Ns))
    last = len(_YEARS) - 1
    ri = min(max(int(rung_hint), 0), last)
    while True:
        n = st.WARMUP + 252 * _YEARS[ri]
        pairs = null_family(n_pairs, sigma_b, rho_b, n, seed, j)
        traces = [trace_pair(ps, start=st.WARMUP, scan_end=n - 1) for ps in pairs]
        reach = first_reach(traces, Ns)
        if len(reach) == len(Ns) or ri == last:
            break
        ri += 1
    cache: Dict[int, Tuple[float, float]] = {}
    res: Dict[str, Optional[List[Optional[float]]]] = {}
    for N in Ns:
        if N not in reach:
            res[str(N)] = None
            continue
        e, n_real = reach[N]
        if e not in cache:
            cache[e] = h1_stats_at(traces, e)
        t_a, t_b = cache[e]
        res[str(N)] = [
            t_a if math.isfinite(t_a) else None,
            t_b if math.isfinite(t_b) else None,
            int(n_real),
            int(e),
        ]
    return ri, res


_FINGERPRINT: Optional[str] = None


def code_fingerprint() -> str:
    """sha256 over the harness bytes (HARNESS_MODULES plus this module)."""
    global _FINGERPRINT
    if _FINGERPRINT is None:
        paths = sorted(set(run.HARNESS_MODULES) | {"scripts/leadership_rotation_null.py"})
        h = hashlib.sha256()
        for p in paths:
            data = Path(_REPO_ROOT, p).read_bytes()
            h.update(p.encode() + b"\0" + hashlib.sha256(data).hexdigest().encode() + b"\n")
        _FINGERPRINT = h.hexdigest()
    return _FINGERPRINT


_BANK_CACHE: Dict[str, List[dict]] = {}
_DEFAULT_BANK_DIR: Optional[Path] = None


def _default_bank_dir() -> Path:
    global _DEFAULT_BANK_DIR
    env = os.environ.get("LR_NULL_BANK_DIR")
    if env:
        return Path(env)
    if _DEFAULT_BANK_DIR is None:
        _DEFAULT_BANK_DIR = Path(tempfile.mkdtemp(prefix="lr_null_bank_"))
    return _DEFAULT_BANK_DIR


def bank_payload(partition: str, group: str, n_pairs: int, sigma_b: float, rho_b: float,
                 K: int, block: int) -> dict:
    seed, crc = seed_entropy(partition, group)
    return {
        "method": METHOD, "partition": partition, "group": group, "n_pairs": int(n_pairs),
        "sigma_b": f"{sigma_b:.4f}", "rho_b": f"{rho_b:.2f}", "K": int(K),
        "block": int(block), "n_block": N_BLOCK, "seed": int(seed), "crc32": int(crc),
        "chunk_rows": CHUNK_ROWS, "years": list(_YEARS), "code": code_fingerprint(),
    }


def _bank_key(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]


def _compute_shard(payload: dict, s: int) -> dict:
    K = payload["K"]
    lo, hi = s * SHARD_PATHS, min((s + 1) * SHARD_PATHS, K)
    b = payload["block"]
    Ns = [N for N in range(b * N_BLOCK, (b + 1) * N_BLOCK) if N >= 1]
    paths: List[dict] = []
    hint = 0
    for j in range(lo, hi):
        hint, res = path_results(payload["n_pairs"], float(payload["sigma_b"]),
                                 float(payload["rho_b"]), payload["seed"], j, Ns, hint)
        paths.append({"j": j, "years": _YEARS[hint], "res": res})
    return {"key": _bank_key(payload), "payload": payload, "shard": s, "paths": paths}


def _load_shard(f: Path, key: str, s: int, expect: int) -> Optional[dict]:
    try:
        obj = json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if obj.get("key") != key or obj.get("shard") != s or len(obj.get("paths", [])) != expect:
        return None
    return obj


def _atomic_write(f: Path, obj: dict) -> None:
    tmp = f.with_name(f"{f.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(obj, sort_keys=True))
    os.replace(tmp, f)


def bank_paths(payload: dict, bank_dir: Optional[Path] = None, on_miss: str = "compute") -> List[dict]:
    """The K null-path results of one bank, computed once and shared.

    Shards of SHARD_PATHS paths each carry their own ``fcntl`` lock, so concurrent
    grid processes split a bank instead of recomputing it: a process claims every
    free shard without blocking, computes those, then waits on the shards another
    process holds. Shard files land by tmp + ``os.replace``."""
    key = _bank_key(payload)
    if key in _BANK_CACHE:
        return _BANK_CACHE[key]
    d = Path(bank_dir) if bank_dir is not None else _default_bank_dir()
    d.mkdir(parents=True, exist_ok=True)
    K = payload["K"]
    n_shards = -(-K // SHARD_PATHS)
    shards: List[Optional[dict]] = [None] * n_shards

    def _expect(s: int) -> int:
        return min((s + 1) * SHARD_PATHS, K) - s * SHARD_PATHS

    def _fill(s: int) -> None:
        f = d / f"{key}.s{s}.json"
        got = _load_shard(f, key, s, _expect(s)) if f.is_file() else None
        if got is None:
            if on_miss != "compute":
                raise LookupError(f"null bank shard missing: {f}")
            got = _compute_shard(payload, s)
            _atomic_write(f, got)
        shards[s] = got

    held: List[Tuple[int, Any]] = []
    for s in range(n_shards):
        f = d / f"{key}.s{s}.json"
        got = _load_shard(f, key, s, _expect(s)) if f.is_file() else None
        if got is not None:
            shards[s] = got
            continue
        lock = open(d / f"{key}.s{s}.lock", "a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            held.append((s, lock))
            continue
        try:
            _fill(s)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
    for s, lock in held:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            _fill(s)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
    flat = [p for sh in shards for p in sh["paths"]]  # type: ignore[index]
    _BANK_CACHE[key] = flat
    return flat


# ---------------------------------------------------------------------------
# The p-values


def _tail(paths: Sequence[dict], N: int, obs: float, idx: int) -> dict:
    K = len(paths)
    vals: List[float] = []
    ge = n_unreached = n_nan = 0
    for p in paths:
        r = p["res"].get(str(N))
        if r is None:
            n_unreached += 1
            ge += 1
            continue
        v = r[idx]
        if v is None or not math.isfinite(float(v)):
            n_nan += 1
            ge += 1
            continue
        vals.append(float(v))
        if math.isfinite(obs) and float(v) >= obs:
            ge += 1
    p = (1.0 + ge) / (1.0 + K) if math.isfinite(obs) else 1.0
    q = float(np.quantile(np.asarray(vals), 1.0 - ALPHA)) if vals else float("nan")
    return {"p": float(p), "n_ge": int(ge), "q975": q, "n_finite": len(vals),
            "n_nan": int(n_nan), "n_unreached": int(n_unreached)}


def h1_null_p(
    *, partition: str, group: str, cores: Sequence[dict], end: int, t_a: float, t_b: float,
    honest_n: int, K: int = NULL_K_DEFAULT, bank_dir: Optional[Path] = None,
    on_miss: str = "compute",
) -> dict:
    seed, crc = seed_entropy(partition, group)
    out: Dict[str, Any] = {
        "method": METHOD, "K": int(K),
        "seed": {"root": p0.PATH_SEED_ROOT, "crc32": int(crc), "entropy": int(seed),
                 "key": f"{partition}|{group}", "spawn_key": "(j,) for j in [0, K)",
                 "chunk_rows": CHUNK_ROWS},
        "p_a": 1.0, "p_b": 1.0, "p_h1": 1.0, "status": "NOT_EXECUTABLE", "reason": None,
        "observed": {"T_a": float(t_a), "T_b": float(t_b)},
    }
    mom = read_moments(cores, end)
    n_obs = int(honest_n) if honest_n is not None else 0
    mp = match_params(mom["sigma_hat"], mom["rho_hat"])
    out["matched"] = {**mom, **{k: mp[k] for k in ("sigma_gen", "rho_gen", "sigma_b", "rho_b")},
                      "N": n_obs, "n_pairs": len(cores)}
    if n_obs < 1:
        out["reason"] = "honest_n < 1"
        return out
    if mp["status"] != "OK":
        out["reason"] = mp["reason"]
        return out
    block = n_obs // N_BLOCK
    payload = bank_payload(partition, group, len(cores), mp["sigma_b"], mp["rho_b"], K, block)
    paths = bank_paths(payload, bank_dir, on_miss)
    ta = _tail(paths, n_obs, float(t_a), 0)
    tb = _tail(paths, n_obs, float(t_b), 1)
    reached = [p["res"][str(n_obs)] for p in paths if p["res"].get(str(n_obs)) is not None]
    out.update({
        "status": "OK", "p_a": ta["p"], "p_b": tb["p"], "p_h1": max(ta["p"], tb["p"]),
        "quantiles": {"alpha": ALPHA, "T_a_q975": ta["q975"], "T_b_q975": tb["q975"],
                      "method": "numpy.quantile(finite, 1 - alpha), linear"},
        "tails": {"T_a": ta, "T_b": tb},
        "n_unreached": ta["n_unreached"], "n_nan_a": ta["n_nan"], "n_nan_b": tb["n_nan"],
        "n_real_over_N": int(sum(1 for r in reached if r[2] > n_obs)),
        "bank_key": _bank_key(payload),
    })
    return out


def make_h1_null_provider(
    K: int = NULL_K_DEFAULT, bank_dir: Optional[Path] = None, on_miss: str = "compute"
) -> Callable[..., dict]:
    """The ``h1_null`` callable evaluate_group/evaluate_family accept."""
    if isinstance(K, bool) or not isinstance(K, int) or K < 1:
        raise ValueError(f"K must be a positive int, got {K!r}")

    def provider(*, partition: str, group: str, pairs=None, cores: Sequence[dict],
                 start: int = 0, end: int, t_a: float, t_b: float, honest_n: int) -> dict:
        return h1_null_p(partition=partition, group=group, cores=cores, end=end, t_a=t_a,
                         t_b=t_b, honest_n=honest_n, K=K, bank_dir=bank_dir, on_miss=on_miss)

    provider.K = K  # type: ignore[attr-defined]
    provider.method = METHOD  # type: ignore[attr-defined]
    return provider
