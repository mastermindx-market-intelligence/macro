"""sni_inference.py — shared SNI-local DRAFT inference contract.

Stdlib-only (math, random, statistics, dataclasses, types). Descriptive
statistics only: a residual or stress interval describes the sample; it is
never causal. Authority flags are all false and stay false; this module
refuses any attempt to enable a rank, gate, size, signal, escalation, or
trade path.

This is not an owner re-implementation. It consumes caller-supplied opaque
values from Data OS identity, Company Event/Earnings, FIF, Capital Structure,
Stock Identity, Options, Research Vault, and qledger/Evaluation. Cluster keys
and identity ids are opaque strings owned by those systems; this library never
constructs, mints, or guesses canonical HK/US issuer or security identifiers.

min_episodes is always caller-supplied. Registration thresholds belong to the
prereg, not this library; the library ships no registered episode minimum.
An unestimable family abstains with a named reason token and never substitutes
an uninformative chance baseline.

Label law (the S2 mix-up this library exists to close):
  * ABSTAIN_NO_EPISODES — n_obs == 0
  * ABSTAIN_INSUFFICIENT_CLUSTERS — n_clusters < min_clusters (CI not estimable)
  * DESCRIPTIVE_ONLY — CI estimable (not abstained) and n_obs < min_episodes
  * TESTED — CI estimable and n_obs >= min_episodes
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Authority — frozen, all false, refuse any true assignment
# ---------------------------------------------------------------------------

_AUTHORITY_FLAG_KEYS: tuple[str, ...] = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AUTHORITY_FLAGS: dict[str, bool] = MappingProxyType(  # type: ignore[assignment]
    {key: False for key in _AUTHORITY_FLAG_KEYS}
)

# ---------------------------------------------------------------------------
# Label tokens (names are part of the contract)
# ---------------------------------------------------------------------------

TESTED = "TESTED"
DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
ABSTAIN_NO_EPISODES = "ABSTAIN_NO_EPISODES"
ABSTAIN_INSUFFICIENT_CLUSTERS = "ABSTAIN_INSUFFICIENT_CLUSTERS"

MIN_CLUSTERS = 2

_Z_ALPHA_0_05 = 1.959964
_Z_ALPHA_0_10 = 1.644854
_Z_ALPHA_0_01 = 2.575829

_PLAIN_ABSTAIN_NO_EPISODES = "This family abstains: no episodes."
_PLAIN_ABSTAIN_INSUFFICIENT_CLUSTERS = (
    "This family abstains: fewer than 2 independent date clusters, "
    "so no interval is estimable."
)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceResult:
    estimate: float | None
    ci_lo: float | None
    ci_hi: float | None
    n_obs: int
    n_clusters: int
    effective_n: float | None
    method: str
    abstained: bool
    reason: str | None
    alpha: float
    seed: int | None
    draws: int | None

    def to_dict(self) -> dict[str, object]:
        """Plain JSON-able values (int / float / str / bool / None)."""
        return {
            "estimate": self.estimate,
            "ci_lo": self.ci_lo,
            "ci_hi": self.ci_hi,
            "n_obs": int(self.n_obs),
            "n_clusters": int(self.n_clusters),
            "effective_n": self.effective_n,
            "method": self.method,
            "abstained": bool(self.abstained),
            "reason": self.reason,
            "alpha": self.alpha,
            "seed": self.seed,
            "draws": self.draws,
        }


# ---------------------------------------------------------------------------
# Input guards
# ---------------------------------------------------------------------------

def _reject_authority(kwargs: dict) -> None:
    """Refuse any attempt to set an authority flag true. False is ignored."""
    for key in _AUTHORITY_FLAG_KEYS:
        if key not in kwargs:
            continue
        val = kwargs.pop(key)
        if val:
            raise ValueError(
                f"{key} must remain false; SNI inference is descriptive only "
                "and does not feed a rank, gate, size, signal, escalation, "
                "or trade path"
            )
    for key, value in AUTHORITY_FLAGS.items():
        if value:
            raise ValueError(
                f"{key} must remain false; SNI inference is descriptive only "
                "and does not feed a rank, gate, size, signal, escalation, "
                "or trade path"
            )
    if kwargs:
        raise TypeError(
            "unexpected keyword arguments: " + ", ".join(sorted(kwargs))
        )


def _require_strict_int(name: str, value: object) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an int")
    return value


def _require_n_k(k: object, n: object) -> tuple[int, int]:
    k_i = _require_strict_int("k", k)
    n_i = _require_strict_int("n", n)
    if n_i < 0 or k_i < 0 or n_i < k_i:
        raise ValueError("require n >= k >= 0")
    return k_i, n_i


def _require_alpha(alpha: object) -> float:
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
        raise ValueError("alpha must be in (0, 1)")
    a = alpha + 0.0
    if not math.isfinite(a) or not (0.0 < a < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    return a


def _require_p0(p0: object) -> float:
    if isinstance(p0, bool) or not isinstance(p0, (int, float)):
        raise ValueError("p0 must be in [0, 1]")
    p = p0 + 0.0
    if not math.isfinite(p) or not (0.0 <= p <= 1.0):
        raise ValueError("p0 must be in [0, 1]")
    return p


def _require_finite_real(value: object) -> float:
    """Accept non-bool int/float only; reject bool, str, NaN, inf, others."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("values must be finite real numbers")
    if not math.isfinite(value):
        raise ValueError("values must be finite real numbers")
    return value + 0.0


def _require_min_episodes(min_episodes: object) -> int:
    m = _require_strict_int("min_episodes", min_episodes)
    if m < 0:
        raise ValueError("min_episodes must be >= 0")
    return m


def _z_for_alpha(alpha: float) -> float:
    if alpha == 0.05:
        return _Z_ALPHA_0_05
    if alpha == 0.1:
        return _Z_ALPHA_0_10
    if alpha == 0.01:
        return _Z_ALPHA_0_01
    raise ValueError("alpha must be one of 0.1, 0.05, 0.01")


def _percentile_linear(samples: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 1] (numpy default)."""
    xs = sorted(samples)
    n = len(xs)
    if n == 0:
        raise ValueError("percentile of empty sample")
    if n == 1:
        return xs[0] + 0.0
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    w = pos - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def _cluster_sort_key(key: object) -> tuple[str, str]:
    """Deterministic order for mixed hashable cluster-key types."""
    return (type(key).__name__, repr(key))


def _binom_tail_ge(k: int, n: int, p0: float) -> float:
    """Exact P[X >= k] for X ~ Bin(n, p0)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if p0 == 0.0:
        return 0.0
    if p0 == 1.0:
        return 1.0
    q = 1.0 - p0
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p0 ** i) * (q ** (n - i))
    return total + 0.0


def _binom_tail_le(k: int, n: int, p0: float) -> float:
    """Exact P[X <= k] for X ~ Bin(n, p0)."""
    if k >= n:
        return 1.0
    if k < 0:
        return 0.0
    if p0 == 0.0:
        return 1.0
    if p0 == 1.0:
        return 0.0
    q = 1.0 - p0
    total = 0.0
    for i in range(0, k + 1):
        total += math.comb(n, i) * (p0 ** i) * (q ** (n - i))
    return total + 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cluster_mean_ci(
    values: Iterable[float],
    cluster_keys: Iterable[object],
    *,
    draws: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
    min_clusters: int = MIN_CLUSTERS,
    **kwargs: object,
) -> InferenceResult:
    """Date-cluster (block) bootstrap of the mean.

    Observations are grouped by cluster key. Cluster order is deterministic
    for mixed hashable key types by sorting on ``(type(k).__name__, repr(k))``,
    so the result is invariant to input permutation. Clusters are then
    resampled with replacement ``draws`` times via ``random.Random(seed)``.
    The statistic is the mean of every observation in the sampled clusters.
    The CI is the percentile interval at (alpha/2, 1 - alpha/2).

    Empty input (no observations) abstains: ``abstained=True`` with
    ``reason=ABSTAIN_NO_EPISODES``. ``values`` and ``cluster_keys`` of
    different lengths raise ``ValueError`` naming both lengths.

    Each value is checked with ``isinstance(v, bool)`` first, then accepted
    only as a non-bool ``int`` or ``float``, then checked with
    ``math.isfinite`` before any arithmetic. Bool, str/bytes, and non-finite
    values raise ``ValueError("values must be finite real numbers")``.
    ``cluster_keys`` containing ``None`` raise
    ``ValueError("cluster_keys must not contain None")``.
    """
    _reject_authority(kwargs)
    alpha_f = _require_alpha(alpha)
    draws_i = _require_strict_int("draws", draws)
    seed_i = _require_strict_int("seed", seed)
    min_c = _require_strict_int("min_clusters", min_clusters)
    if draws_i < 1:
        raise ValueError("draws must be >= 1")
    if min_c < 1:
        raise ValueError("min_clusters must be >= 1")

    vals = list(values)
    keys = list(cluster_keys)
    n_vals = len(vals)
    n_keys = len(keys)
    if n_vals != n_keys:
        raise ValueError(
            f"len(values)={n_vals} must equal len(cluster_keys)={n_keys}"
        )

    n_obs = n_vals
    method = "cluster_bootstrap_mean"

    if n_obs == 0:
        return InferenceResult(
            estimate=None,
            ci_lo=None,
            ci_hi=None,
            n_obs=0,
            n_clusters=0,
            effective_n=0.0,
            method=method,
            abstained=True,
            reason=ABSTAIN_NO_EPISODES,
            alpha=alpha_f,
            seed=seed_i,
            draws=draws_i,
        )

    obs = [_require_finite_real(v) for v in vals]
    if any(key is None for key in keys):
        raise ValueError("cluster_keys must not contain None")

    grouped: dict[object, list[float]] = {}
    for value, key in zip(obs, keys):
        grouped.setdefault(key, []).append(value)
    ordered_keys = sorted(grouped, key=_cluster_sort_key)
    blocks = [grouped[key] for key in ordered_keys]
    n_clusters = len(blocks)
    estimate = statistics.fmean(obs)
    effective_n = n_clusters + 0.0

    if n_clusters < min_c:
        return InferenceResult(
            estimate=estimate,
            ci_lo=None,
            ci_hi=None,
            n_obs=n_obs,
            n_clusters=n_clusters,
            effective_n=effective_n,
            method=method,
            abstained=True,
            reason=ABSTAIN_INSUFFICIENT_CLUSTERS,
            alpha=alpha_f,
            seed=seed_i,
            draws=draws_i,
        )

    rng = random.Random(seed_i)
    boot: list[float] = []
    for _ in range(draws_i):
        sampled = rng.choices(blocks, k=n_clusters)
        total = 0.0
        count = 0
        for block in sampled:
            total += sum(block)
            count += len(block)
        boot.append(total / count)

    lo_q = alpha_f / 2.0
    hi_q = 1.0 - lo_q
    return InferenceResult(
        estimate=estimate,
        ci_lo=_percentile_linear(boot, lo_q),
        ci_hi=_percentile_linear(boot, hi_q),
        n_obs=n_obs,
        n_clusters=n_clusters,
        effective_n=effective_n,
        method=method,
        abstained=False,
        reason=None,
        alpha=alpha_f,
        seed=seed_i,
        draws=draws_i,
    )


def wilson_ci(k: int, n: int, *, alpha: float = 0.05, **kwargs: object) -> InferenceResult:
    """Wilson score interval for a binomial proportion k/n.

    z is a built-in inverse-normal approximation, hardcoded for alpha in
    {0.1, 0.05, 0.01} (accurate to 1e-6). Other alpha values raise ValueError.
    """
    _reject_authority(kwargs)
    k_i, n_i = _require_n_k(k, n)
    alpha_f = _require_alpha(alpha)
    z = _z_for_alpha(alpha_f)
    method = "wilson"

    if n_i == 0:
        return InferenceResult(
            estimate=None,
            ci_lo=None,
            ci_hi=None,
            n_obs=0,
            n_clusters=0,
            effective_n=0.0,
            method=method,
            abstained=True,
            reason=ABSTAIN_NO_EPISODES,
            alpha=alpha_f,
            seed=None,
            draws=None,
        )

    p = k_i / n_i
    z2 = z * z
    denom = 1.0 + z2 / n_i
    centre = (p + z2 / (2.0 * n_i)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n_i + z2 / (4.0 * n_i * n_i)) / denom
    lo = max(0.0, centre - half)
    hi = min(1.0, centre + half)
    if k_i == 0:
        lo = 0.0
    if k_i == n_i:
        hi = 1.0
    return InferenceResult(
        estimate=p + 0.0,
        ci_lo=lo + 0.0,
        ci_hi=hi + 0.0,
        n_obs=n_i,
        n_clusters=n_i,
        effective_n=n_i + 0.0,
        method=method,
        abstained=False,
        reason=None,
        alpha=alpha_f,
        seed=None,
        draws=None,
    )


def binom_p_one_sided_greater(
    k: int, n: int, p0: float = 0.5, **kwargs: object
) -> float:
    """Exact P[X >= k] for X ~ Bin(n, p0), via math.comb."""
    _reject_authority(kwargs)
    k_i, n_i = _require_n_k(k, n)
    p = _require_p0(p0)
    return _binom_tail_ge(k_i, n_i, p)


def binom_p_two_sided(k: int, n: int, p0: float = 0.5, **kwargs: object) -> float:
    """Exact two-sided binomial p-value: min(1, 2 * min(P[X>=k], P[X<=k]))."""
    _reject_authority(kwargs)
    k_i, n_i = _require_n_k(k, n)
    p = _require_p0(p0)
    upper = _binom_tail_ge(k_i, n_i, p)
    lower = _binom_tail_le(k_i, n_i, p)
    return min(1.0, 2.0 * min(upper, lower))


def sign_test_two_sided(pos: int, neg: int, **kwargs: object) -> float:
    """Exact two-sided sign test on (pos, neg) counts; ties excluded by caller."""
    _reject_authority(kwargs)
    pos_i = _require_strict_int("pos", pos)
    neg_i = _require_strict_int("neg", neg)
    if pos_i < 0 or neg_i < 0:
        raise ValueError("pos and neg must be >= 0")
    n = pos_i + neg_i
    if n == 0:
        return 1.0
    return binom_p_two_sided(pos_i, n, p0=0.5)


def label_for(result: InferenceResult, *, min_episodes: int, **kwargs: object) -> str:
    """Assign TESTED / DESCRIPTIVE_ONLY / abstain-reason from a result.

    min_episodes is caller-supplied: the prereg owns the registered floor,
    this library does not.
    """
    _reject_authority(kwargs)
    m = _require_min_episodes(min_episodes)
    if result.abstained:
        if result.reason is None:
            raise ValueError("abstained result must carry a reason token")
        return result.reason
    if result.n_obs >= m:
        return TESTED
    return DESCRIPTIVE_ONLY


def plain_word_null(
    label: str,
    result: InferenceResult,
    *,
    min_episodes: int,
    **kwargs: object,
) -> str:
    """Plain-language null/status sentence for a label token.

    Unknown labels raise KeyError. The four contract strings never describe
    an uninformative chance baseline or a projection.
    """
    _reject_authority(kwargs)
    m = _require_min_episodes(min_episodes)
    n_obs = int(result.n_obs)
    n_clusters = int(result.n_clusters)
    if label == TESTED:
        return f"Tested: {n_obs} episodes across {n_clusters} date clusters."
    if label == DESCRIPTIVE_ONLY:
        return (
            f"Descriptive only: {n_obs} episodes across {n_clusters} date "
            f"clusters, below the registered minimum of {m} episodes; "
            "no test is claimed."
        )
    if label == ABSTAIN_INSUFFICIENT_CLUSTERS:
        return _PLAIN_ABSTAIN_INSUFFICIENT_CLUSTERS
    if label == ABSTAIN_NO_EPISODES:
        return _PLAIN_ABSTAIN_NO_EPISODES
    raise KeyError(label)
