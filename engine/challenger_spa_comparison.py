"""RESEARCH REFERENCE — NOT WIRED. Dependence-aware challenger comparison (Q20).

Verdict (research/quant_assessment_2026_10/Q20_dependence_aware_model_comparison/VERDICT.md):
KEEP as a research-only diagnostic for the existing statistics owner — every pre-registered
method-control simulation gate passed (size near nominal under correlated nulls where the
naive best-candidate p-value over-rejects; power on a planted edge). In the single frozen
empirical comparison (VERDICT.md) the admitted ``vector`` allocation family's claim of
beating risk-matched buy-and-hold VANISHES under selection-aware SPA on a REUSED window
(p_c 0.28 at block 21, 0.24-0.28 across blocks 7-63); the incumbent algorithm is kept
unchanged and the negative is filed. This module grants no promotion, gate, rank, size or
alert authority.

What it is
----------
A pure, bounded reference implementation of:

* Hansen (2005) Superior Predictive Ability test (lower / consistent / upper p-values),
  studentised, with ONE common Politis-Romano stationary-bootstrap index matrix shared by
  every candidate so serial and cross-model dependence and the common calendar survive.
* Block-length sensitivity, honest-N (non-overlapping blocks) and a Newey-West effective
  sample size.
* A naive best-candidate p-value (ignores selection) kept only as a discriminator.
* Generation-time trial identity mapping using the trial ledger's own config-hash rule
  (re-derived as a pure function; the ledger is never imported, written or rebuilt), with
  refusal when a candidate is unmapped or a losing trial disappears.
* A trial-budget helper that can never return less than the original declared budget when
  correlated null candidates are added.
* A window-reuse disclosure that never labels a reused or underpowered window as fresh
  confirmation.
* CSCV probability of backtest overfitting, flagged supplementary and unable to set a
  verdict; the chronological holdout is never replaced by shuffled CV or PBO.

What it is not
--------------
Not the validation core (``engine/validation.py`` was not opened — its read was refused for
this assessment — and is not imported or replaced), not a second Deflated Sharpe, not a new
trial ledger, not a promotion service. Nothing imports this module; it registers nothing,
reads no files, takes no wall-clock reads and has no side effects at import.

Conventions: ``d[t, k] = loss_benchmark - loss_k`` (equivalently candidate return minus
benchmark return); positive means candidate k beats the benchmark; the family null is
``max_k E[d_k] <= 0``.
"""
from __future__ import annotations

import json
import hashlib
import math
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy import signal as _signal
from scipy import stats as _stats

RESEARCH_ONLY = True
PROMOTION_AUTHORITY = False
MODULE_VERSION = "q20-spa-ref-1"

# Same minimum as engine.calibration_hub._MIN_INDEPENDENT_BLOCKS (documented, not imported).
MIN_INDEPENDENT_BLOCKS = 10
DEFAULT_SENSITIVITY_BLOCKS = (7, 14, 21, 42, 63)

_MAX_N = 200_000
_MAX_K = 500
_MAX_B = 20_000
_CHUNK = 500


class UnmappedCandidateError(ValueError):
    """A compared candidate has no generation-time trial identity."""


class MissingTrialError(ValueError):
    """A generation-time trial of the family has no candidate panel (a losing trial vanished)."""


# ----------------------------------------------------------------------------- validation

def _as_panel(d: Any) -> np.ndarray:
    arr = np.asarray(d, dtype=float)
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2:
        raise ValueError("loss-differential panel must be 1-D or 2-D (time x candidates)")
    n, k = arr.shape
    if n < 30:
        raise ValueError(f"panel too short for a block bootstrap (n={n} < 30)")
    if n > _MAX_N or k > _MAX_K or k < 1:
        raise ValueError(f"panel shape out of bounds: {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("panel contains NaN/inf — unknown/excluded rows must be removed explicitly")
    return arr


def _check_time_order(time_index: Any, n: int) -> None:
    if time_index is None:
        return
    ti = np.asarray(time_index)
    if ti.shape[0] != n:
        raise ValueError("time_index length does not match the panel")
    if ti.shape[0] > 1 and not np.all(ti[1:] > ti[:-1]):
        raise ValueError("time_index must be strictly increasing: shuffled or duplicated "
                         "rows are refused (chronological evaluation only)")


def _check_b(B: int, mean_block: float, n: int) -> None:
    if not (10 <= int(B) <= _MAX_B):
        raise ValueError(f"B out of bounds: {B}")
    if not (1.0 <= float(mean_block) <= n / 2):
        raise ValueError(f"mean_block out of bounds for n={n}: {mean_block}")


# ----------------------------------------------------------------------------- bootstrap

def stationary_bootstrap_indices(n: int, B: int, mean_block: float,
                                 rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix of shape (B, n).

    Each row is one resample of the time axis: blocks start at uniform positions, have
    geometric length with mean ``mean_block`` and wrap circularly. The SAME row is applied
    to every candidate (common indices), which preserves cross-model dependence.
    """
    n = int(n)
    B = int(B)
    _check_b(B, mean_block, n)
    p = 1.0 / float(mean_block)
    new_block = rng.random((B, n)) < p
    new_block[:, 0] = True
    starts = rng.integers(0, n, size=(B, n))
    t = np.arange(n)
    last_start = np.maximum.accumulate(np.where(new_block, t[None, :], 0), axis=1)
    start_val = np.take_along_axis(starts, last_start, axis=1)
    return (start_val + (t[None, :] - last_start)) % n


def _bootstrap_means(d: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Means of ``d`` under each bootstrap row, via per-row index counts (B x K)."""
    n = d.shape[0]
    out = np.empty((idx.shape[0], d.shape[1]))
    for s in range(0, idx.shape[0], _CHUNK):
        rows = idx[s:s + _CHUNK]
        r = rows.shape[0]
        flat = (rows + (np.arange(r) * n)[:, None]).ravel()
        counts = np.bincount(flat, minlength=r * n).reshape(r, n).astype(float)
        out[s:s + r] = counts @ d / n
    return out


def spa_test(d: Any, B: int = 5000, mean_block: float = 21.0, seed: int = 7,
             time_index: Any = None, idx: np.ndarray | None = None) -> dict:
    """Hansen (2005) SPA test of ``H0: max_k E[d_k] <= 0``.

    Returns lower/consistent/upper p-values (p_l <= p_c <= p_u), the studentised statistic,
    per-candidate means and bootstrap scale ``omega``. ``p_u`` is the White Reality-Check
    style (fully recentred) p-value. p-values use ``#(T* >= T) / B`` so ``T = 0`` gives 1.
    """
    arr = _as_panel(d)
    n, k = arr.shape
    _check_time_order(time_index, n)
    if idx is None:
        idx = stationary_bootstrap_indices(n, B, mean_block, np.random.default_rng(seed))
    else:
        idx = np.asarray(idx)
        if idx.ndim != 2 or idx.shape[1] != n:
            raise ValueError("idx must be a (B, n) index matrix")
        _check_b(idx.shape[0], mean_block, n)
    dbar = arr.mean(axis=0)
    boot = _bootstrap_means(arr, idx)
    omega = np.sqrt(n * boot.var(axis=0))
    if np.any(omega <= 0) or not np.all(np.isfinite(omega)):
        raise ValueError("degenerate candidate (zero bootstrap variance) — exclude it explicitly")
    sq = math.sqrt(n)
    tstat = sq * dbar / omega
    T = max(0.0, float(tstat.max()))
    thresh = -math.sqrt(2.0 * math.log(math.log(n)))
    mu = {
        "l": np.maximum(dbar, 0.0),
        "c": dbar * (tstat >= thresh),
        "u": dbar,
    }
    out = {}
    for key, m in mu.items():
        Tb = np.maximum(0.0, (sq * (boot - m[None, :]) / omega[None, :]).max(axis=1))
        out[f"p_{key}"] = float(np.mean(Tb >= T))
    best = int(np.argmax(tstat))
    return {
        "p_l": out["p_l"], "p_c": out["p_c"], "p_u": out["p_u"],
        "stat": T, "n": n, "k": k, "B": int(idx.shape[0]), "mean_block": float(mean_block),
        "dbar": dbar.tolist(), "omega": omega.tolist(), "tstat": tstat.tolist(),
        "best_index": best, "common_indices": True,
    }


def block_length_sensitivity(d: Any, blocks: Sequence[float] = DEFAULT_SENSITIVITY_BLOCKS,
                             B: int = 5000, seed: int = 7, time_index: Any = None) -> dict:
    """SPA p-values across pre-specified mean block lengths (a sensitivity report, not a search)."""
    rows = {}
    for b in blocks:
        r = spa_test(d, B=B, mean_block=float(b), seed=seed, time_index=time_index)
        rows[str(int(b)) if float(b).is_integer() else str(b)] = {
            "p_l": r["p_l"], "p_c": r["p_c"], "p_u": r["p_u"], "stat": r["stat"]}
    return {"blocks": [float(b) for b in blocks], "rows": rows,
            "max_p_c": max(v["p_c"] for v in rows.values()),
            "min_p_c": min(v["p_c"] for v in rows.values())}


# ----------------------------------------------------------------------------- HAC / honest N

def newey_west_lag(n: int) -> int:
    return int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))


def newey_west_lrvar(x: Any, lag: int | None = None) -> float:
    """Bartlett-kernel long-run variance of a 1-D series."""
    v = np.asarray(x, dtype=float)
    if v.ndim != 1 or v.size < 3 or not np.all(np.isfinite(v)):
        raise ValueError("newey_west_lrvar needs a finite 1-D series of length >= 3")
    n = v.size
    L = newey_west_lag(n) if lag is None else int(lag)
    L = max(0, min(L, n - 1))
    e = v - v.mean()
    lr = float(e @ e) / n
    for j in range(1, L + 1):
        w = 1.0 - j / (L + 1.0)
        lr += 2.0 * w * float(e[j:] @ e[:-j]) / n
    return max(lr, 1e-300)


def effective_sample_size(x: Any, lag: int | None = None) -> float:
    v = np.asarray(x, dtype=float)
    var = float(np.var(v))
    return float(v.size * var / newey_west_lrvar(v, lag)) if var > 0 else 0.0


def honest_n_blocks(n: int, block: int = 21) -> int:
    if block < 1:
        raise ValueError("block must be >= 1")
    return int(n) // int(block)


def naive_best_pvalue(d: Any) -> dict:
    """One-sided HAC t p-value of the best-looking candidate, IGNORING selection.

    Kept only as a discriminator: under correlated nulls it oversizes, which is exactly the
    mistake the SPA guards against. Never a decision input.
    """
    arr = _as_panel(d)
    n = arr.shape[0]
    t = np.array([math.sqrt(n) * arr[:, j].mean() / math.sqrt(newey_west_lrvar(arr[:, j]))
                  for j in range(arr.shape[1])])
    best = int(np.argmax(t))
    return {"best_index": best, "t": float(t[best]),
            "p_naive": float(_stats.norm.sf(t[best])), "selection_ignored": True}


def budget_bonferroni(p: float, budget: int) -> float:
    return float(min(1.0, max(0.0, p) * max(1, int(budget))))


# ----------------------------------------------------------------------------- returns / losses

def strategy_net_returns(asset_returns: Any, alloc: Any, cost_one_way: float,
                         lag: int = 1) -> np.ndarray:
    """Net per-period return of an allocation path; first ``lag + 1`` rows are NaN.

    ``pos_t = alloc_{t-lag}``; cost is ``cost_one_way * |pos_t - pos_{t-1}|``.
    """
    r = np.asarray(asset_returns, dtype=float)
    a = np.asarray(alloc, dtype=float)
    if r.shape != a.shape or r.ndim != 1:
        raise ValueError("asset_returns and alloc must be aligned 1-D arrays")
    if lag < 0 or lag + 1 >= r.size:
        raise ValueError("bad lag")
    if not (0.0 <= cost_one_way < 0.1):
        raise ValueError("cost_one_way out of bounds")
    pos = np.full_like(a, np.nan)
    pos[lag:] = a[:a.size - lag]
    prev = np.full_like(a, np.nan)
    prev[1:] = pos[:-1]
    net = pos * r - cost_one_way * np.abs(pos - prev)
    net[:lag + 1] = np.nan
    return net


def risk_match_beta(train_strategy: Any, train_benchmark: Any) -> float:
    """Training-only volatility-match coefficient sd(strategy)/sd(benchmark)."""
    s = np.asarray(train_strategy, dtype=float)
    b = np.asarray(train_benchmark, dtype=float)
    if s.shape != b.shape or s.size < 30:
        raise ValueError("training series must be aligned with >= 30 observations")
    sb = float(np.std(b, ddof=1))
    if sb <= 0 or not np.isfinite(sb):
        raise ValueError("benchmark has zero training variance")
    return float(np.std(s, ddof=1) / sb)


def chronological_split(time_index: Any, split: Any) -> tuple[np.ndarray, np.ndarray]:
    """Boolean (train, test) masks; refuses a non-chronological index."""
    ti = np.asarray(time_index)
    _check_time_order(ti, ti.shape[0])
    train = ti < split
    test = ~train
    if not train.any() or not test.any():
        raise ValueError("split leaves an empty training or evaluation window")
    return train, test


# ----------------------------------------------------------------------------- trial identity

def trial_config_hash(family: str, config: Mapping[str, Any]) -> str:
    """Same rule as the trial ledger's config hash (re-derived; the ledger is not imported)."""
    canon = json.dumps(config, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha1(f"{family}\x00{canon}".encode("utf-8")).hexdigest()[:16]


def _itemized(rows: Iterable[Mapping[str, Any]], family: str,
              source: str | None = None) -> list[Mapping[str, Any]]:
    out = []
    for r in rows:
        if r.get("family") != family or r.get("kind") == "declared_budget":
            continue
        if not isinstance(r.get("config"), Mapping):
            continue
        if source is not None and r.get("source") != source:
            continue
        out.append(r)
    return out


def map_candidates_to_trials(candidates: Mapping[str, Mapping[str, Any]],
                             ledger_rows: Sequence[Mapping[str, Any]], family: str,
                             source: str | None = None,
                             excluded: Mapping[str, str] | None = None) -> list[dict]:
    """Map every candidate to a generation-time ledger trial; no losing trial may vanish.

    ``excluded`` maps a ledger config_hash to an explicit reason (the only way a family trial
    may be absent from the comparison). Raises ``UnmappedCandidateError`` or
    ``MissingTrialError``.

    Scope of the missing-trial check: when ``source`` is given, only itemized trials of that
    family AND source are checked. Budget trials of the same family from any other source
    (or carried only by a ``declared_budget`` row) are not "losing trials" of this mapping;
    they stay in ``original_trial_budget`` and must be reported by the caller as attrition
    (counted in the budget, never dropped). Pass ``source=None`` to check every itemized
    trial of the family.
    """
    excluded = dict(excluded or {})
    if any(not str(v).strip() for v in excluded.values()):
        raise ValueError("every exclusion needs a non-empty reason")
    items = _itemized(ledger_rows, family, source)
    by_hash: dict[str, Mapping[str, Any]] = {}
    for r in items:
        by_hash.setdefault(str(r.get("config_hash")), r)
    mapped = []
    seen = set()
    for name, cfg in candidates.items():
        h = trial_config_hash(family, cfg)
        if h not in by_hash:
            raise UnmappedCandidateError(f"candidate {name!r} (hash {h}) has no ledger trial in {family!r}")
        if h in excluded:
            raise ValueError(f"candidate {name!r} is both compared and excluded")
        seen.add(h)
        mapped.append({"candidate": name, "config_hash": h, "ledger_ts": by_hash[h].get("ts"),
                       "source": by_hash[h].get("source")})
    missing = sorted(set(by_hash) - seen - set(excluded))
    if missing:
        raise MissingTrialError(f"family {family!r} trials without a candidate panel: {missing}")
    return mapped


def original_trial_budget(ledger_rows: Sequence[Mapping[str, Any]], family: str) -> dict:
    """Budget = max(declared upper bounds, literal distinct itemized configs) for a family."""
    declared = [int(r.get("n", 0)) for r in ledger_rows
                if r.get("family") == family and r.get("kind") == "declared_budget"]
    literal = len({str(r.get("config_hash")) for r in _itemized(ledger_rows, family)})
    return {"declared_max": max(declared) if declared else 0, "literal_n": literal,
            "budget": max([literal] + declared)}


def trial_budget_after_adding(original_budget: int, literal_n: int, added: int,
                              rho: float) -> int:
    """Trial budget after adding ``added`` correlated (null) candidates.

    Correlation may earn a credit on the NEW total (``ceil(sqrt(lit))`` floor, the
    ledger-style floor), but the result is never below the original budget or the original
    literal count, and it is non-decreasing in ``added``.
    """
    if added < 0 or original_budget < 0 or literal_n < 0:
        raise ValueError("counts must be non-negative")
    if not (-1.0 <= rho <= 1.0):
        raise ValueError("rho out of range")
    lit = literal_n + added
    r = min(max(rho, 0.0), 1.0)
    credited = max(math.ceil(math.sqrt(lit)) if lit else 0,
                   math.ceil(lit * (1.0 - r) + r) if lit else 0)
    return int(max(original_budget, literal_n, credited))


# ----------------------------------------------------------------------------- window reuse

def window_reuse_disclosure(eval_start: Any, eval_end: Any, generated_at: Any,
                            prior_use_windows: Sequence[tuple[Any, Any]] = (),
                            n_blocks: int = 0,
                            min_blocks: int = MIN_INDEPENDENT_BLOCKS) -> dict:
    """Label an outcome window FRESH / FRESH_UNDERPOWERED / REUSED.

    FRESH requires the window to start strictly after trial generation, overlap no prior-use
    window, and hold at least ``min_blocks`` independent blocks. Only FRESH may be described
    as confirmation; REUSED and FRESH_UNDERPOWERED never are.
    """
    overlaps = [list(w) for w in prior_use_windows if w[0] <= eval_end and eval_start <= w[1]]
    after_gen = eval_start > generated_at
    if not after_gen or overlaps:
        label = "REUSED"
    elif n_blocks < min_blocks:
        label = "FRESH_UNDERPOWERED"
    else:
        label = "FRESH"
    return {"label": label, "starts_after_generation": bool(after_gen),
            "overlapping_prior_windows": len(overlaps), "n_blocks": int(n_blocks),
            "min_blocks": int(min_blocks),
            "fresh_confirmation_allowed": label == "FRESH",
            "statement": {"REUSED": "reused outcome window — not fresh confirmation",
                          "FRESH_UNDERPOWERED": "post-generation window below the block "
                                                "minimum — support only, not tested",
                          "FRESH": "untouched post-generation window"}[label]}


# ----------------------------------------------------------------------------- PBO (supplementary)

def cscv_pbo(returns: Any, S: int = 16) -> dict:
    """CSCV probability of backtest overfitting (Bailey et al.); SUPPLEMENTARY ONLY.

    Uses chronological groups and per-strategy Sharpe ranking. The result is flagged so it
    can never replace the chronological holdout or set a verdict.
    """
    M = np.asarray(returns, dtype=float)
    if M.ndim != 2 or M.shape[1] < 2 or not np.all(np.isfinite(M)):
        raise ValueError("cscv_pbo needs a finite (time x strategies) matrix with >= 2 strategies")
    if S % 2 or not (4 <= S <= 20) or M.shape[0] < 2 * S:
        raise ValueError("S must be even in [4, 20] with at least 2 rows per group")
    T, N = M.shape
    edges = np.linspace(0, T, S + 1).astype(int)
    cnt = np.array([edges[i + 1] - edges[i] for i in range(S)], dtype=float)
    s1 = np.array([M[edges[i]:edges[i + 1]].sum(axis=0) for i in range(S)])
    s2 = np.array([(M[edges[i]:edges[i + 1]] ** 2).sum(axis=0) for i in range(S)])

    def _sharpe(g: list[int]) -> np.ndarray:
        n = cnt[g].sum()
        m = s1[g].sum(axis=0) / n
        v = s2[g].sum(axis=0) / n - m ** 2
        return m / np.sqrt(np.maximum(v, 1e-300))

    lam = []
    for is_g in combinations(range(S), S // 2):
        oos_g = [i for i in range(S) if i not in is_g]
        sis, soos = _sharpe(list(is_g)), _sharpe(oos_g)
        star = int(np.argmax(sis))
        rank = float(_stats.rankdata(soos)[star])
        w = rank / (N + 1.0)
        lam.append(math.log(w / (1.0 - w)))
    lam_arr = np.array(lam)
    return {"pbo": float(np.mean(lam_arr <= 0)), "n_splits": int(lam_arr.size), "S": S,
            "role": "supplementary", "can_set_verdict": False,
            "replaces_chronological_holdout": False}


# ----------------------------------------------------------------------------- decisions

def claim_decision(primary_p_c: float, sensitivity_p_c: Mapping[str, float],
                   best_annualised_mean: float, alpha: float = 0.05,
                   sensitivity_alpha: float = 0.10, effect_bar: float = 0.02) -> dict:
    """Frozen SURVIVES/VANISHES rule. PBO and naive p are deliberately not inputs."""
    sens_ok = all(float(p) <= sensitivity_alpha for p in sensitivity_p_c.values())
    checks = {"primary_p_c_le_alpha": float(primary_p_c) <= alpha,
              "all_sensitivity_p_c_le_0.10": bool(sens_ok),
              "effect_bar_met": float(best_annualised_mean) >= effect_bar}
    return {"claim": "SURVIVES" if all(checks.values()) else "VANISHES", "checks": checks,
            "on_vanish": "keep the incumbent algorithm and file the negative comparison"}


def assemble_report(spa_primary: Mapping[str, Any], sensitivity: Mapping[str, Any],
                    best_annualised_mean: float, window: Mapping[str, Any],
                    pbo: Mapping[str, Any] | None = None,
                    naive: Mapping[str, Any] | None = None) -> dict:
    """Combine results; supplementary items are attached but never change the decision."""
    sens = {k: v["p_c"] for k, v in sensitivity["rows"].items()
            if float(k) != float(spa_primary["mean_block"])}
    decision = claim_decision(spa_primary["p_c"], sens, best_annualised_mean)
    return {"decision": decision,
            "window": dict(window),
            "fresh_confirmation": bool(window.get("fresh_confirmation_allowed", False)
                                       and decision["claim"] == "SURVIVES"),
            "supplementary": {"pbo": dict(pbo) if pbo else None,
                              "naive_best": dict(naive) if naive else None},
            "promotion_authority": PROMOTION_AUTHORITY, "research_only": RESEARCH_ONLY}


def study_verdict(method_gates: Mapping[str, bool], data_eligible: bool,
                  missing_input: str | None = None) -> dict:
    if not data_eligible:
        return {"verdict": "INSUFFICIENT_DATA", "missing_input": missing_input or "unspecified"}
    if not method_gates or not all(method_gates.values()):
        return {"verdict": "REJECT", "failed_gates": sorted(k for k, v in method_gates.items() if not v)}
    return {"verdict": "KEEP", "failed_gates": []}


# ----------------------------------------------------------------------------- simulation

def simulate_correlated_panel(n: int, k: int, rho: float, phi: float, means: Any,
                              rng: np.random.Generator, burn: int = 100) -> np.ndarray:
    """AR(1) candidates with unit marginal variance and equicorrelated innovations."""
    if not (30 <= n <= _MAX_N and 1 <= k <= _MAX_K and 0 <= rho < 1 and -1 < phi < 1):
        raise ValueError("simulation parameters out of bounds")
    mu = np.broadcast_to(np.asarray(means, dtype=float), (k,))
    common = rng.standard_normal((n + burn, 1))
    idio = rng.standard_normal((n + burn, k))
    e = math.sqrt(rho) * common + math.sqrt(1.0 - rho) * idio
    x = _signal.lfilter([math.sqrt(1.0 - phi * phi)], [1.0, -phi], e, axis=0)
    return x[burn:] + mu[None, :]


def simulate_rejection_rates(n: int, k: int, rho: float, phi: float, means: Any, reps: int,
                             B: int, mean_block: float, seed: int, alpha: float = 0.05) -> dict:
    """Monte Carlo rejection rates of SPA (l/c/u) and the naive best-candidate test."""
    if not (1 <= reps <= 5000):
        raise ValueError("reps out of bounds")
    rng = np.random.default_rng(seed)
    rej = {"p_l": 0, "p_c": 0, "p_u": 0, "naive": 0}
    for _ in range(int(reps)):
        d = simulate_correlated_panel(n, k, rho, phi, means, rng)
        idx = stationary_bootstrap_indices(n, B, mean_block, rng)
        r = spa_test(d, B=B, mean_block=mean_block, idx=idx)
        for key in ("p_l", "p_c", "p_u"):
            rej[key] += r[key] <= alpha
        rej["naive"] += naive_best_pvalue(d)["p_naive"] <= alpha
    rates = {k_: v / reps for k_, v in rej.items()}
    mc_se = {k_: math.sqrt(max(v * (1 - v), 1e-12) / reps) for k_, v in rates.items()}
    return {"rates": rates, "mc_se": mc_se, "reps": int(reps), "n": n, "k": k, "rho": rho,
            "phi": phi, "B": B, "mean_block": mean_block, "alpha": alpha}
