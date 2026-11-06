from __future__ import annotations

# The house rule puts the __future__ import first, so the module docstring is
# bound explicitly to __doc__.
__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Q09 — publication-vintage ATS / non-ATS venue concentration and venue-change
analysis (quant assessment 2026-10).

VERDICT: INSUFFICIENT_DATA for every publication-vintage / revision claim.
The licensed local FINRA OTC-transparency store (data/finra_ats,
data/finra_otc_nonats) carries no FINRA initial-publication or update
timestamp and holds exactly one stored vintage per reporting week, so no week
has a release identity and no revision can be observed. The one pre-registered
descriptive comparison (multi-week shrunk per-symbol ATS venue HHI versus the
incumbent single-latest-week snapshot) is reported as a sub-result in
research/quant_assessment_2026_10/Q09_released_ats_concentration/VERDICT.md.
Exact missing input: FINRA weekly-summary publication/update metadata per
(week, tier) plus retained multi-vintage snapshots.

Scope and restrictions (binding):
  * ATS / non-ATS is a venue / reporting category, never owner intent.
  * FINRA weekly volume is not short interest, not net buying, not a live print.
  * The reporting week is never an information-availability date.
  * Pure functions over bounded in-memory inputs; no I/O at import; nothing
    imports this module; RESEARCH_ONLY gates nothing and activates nothing.
"""

import copy
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

RESEARCH_ONLY = True
WIRED = False

# Interpretations this module must never emit (requirement 6).
FORBIDDEN_INTERPRETATION_TERMS: tuple[str, ...] = (
    "accumulat",
    "distribution by institutions",
    "institutional distribution",
    "institutional buying",
    "institutional selling",
    "institutional intent",
    "smart money",
    "net buying",
    "net selling",
    "net buy",
    "net sell",
    "net purchase",
    "buy pressure",
    "sell pressure",
    "buying pressure",
    "selling pressure",
    "whale",
    "short interest",
    "short squeeze",
    "live print",
    "live dark pool print",
    "real-time print",
    "dark pool print",
    "beneficial owner",
    "owner intent",
)

DEFAULT_REQUIRED_TIERS: tuple[str, ...] = ("T1", "T2")
UNKNOWN_VENUE_LABELS: frozenset[str] = frozenset({"", "DE MINIMIS FIRMS", "UNKNOWN", "UNMAPPED"})


# --------------------------------------------------------------------------
# Requirement 1 — availability clock, never the reporting week
# --------------------------------------------------------------------------

def admissible(query_at: Any, available_at: Any) -> bool:
    """True only when a KNOWN availability time is at or before query_at.

    There is deliberately no reporting-week argument: unknown availability is
    never replaced by the reporting period, so it is never admissible.
    """
    if available_at is None or query_at is None:
        return False
    if isinstance(available_at, float) and math.isnan(available_at):
        return False
    return available_at <= query_at


def admit_weeks(records: Iterable[Mapping[str, Any]], query_at: Any) -> dict[str, list]:
    """Split week records into admitted / withheld at ``query_at``.

    Each record needs ``week`` (reporting period; metadata only) and
    ``available_at`` (may be None). Reasons are explicit; the reporting week
    is copied through but never compared with query_at.
    """
    admitted: list[dict] = []
    withheld: list[dict] = []
    for r in records:
        rec = dict(r)
        av = rec.get("available_at")
        if av is None:
            rec["reason"] = "availability_unknown"
            withheld.append(rec)
        elif admissible(query_at, av):
            rec["reason"] = "available"
            admitted.append(rec)
        else:
            rec["reason"] = "not_yet_available"
            withheld.append(rec)
    return {"admitted": admitted, "withheld": withheld}


def qualify_release_identity(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Count weeks with a publisher release identity and with >=2 vintages.

    A record may carry ``publisher_available_at`` (publisher release time),
    ``store_first_seen_at`` (an upper bound on when OUR store held it — not a
    publisher release time) and ``n_vintages``.
    """
    rows = [dict(r) for r in records]
    n = len(rows)
    with_pub = sum(1 for r in rows if r.get("publisher_available_at") is not None)
    with_store = sum(1 for r in rows if r.get("store_first_seen_at") is not None)
    multi = sum(1 for r in rows if int(r.get("n_vintages") or 0) >= 2)
    return {
        "n_weeks": n,
        "n_with_publisher_release_identity": with_pub,
        "n_with_store_first_seen_upper_bound": with_store,
        "n_with_multiple_vintages": multi,
        "vintage_claims_supported": with_pub > 0,
        "revision_claims_supported": multi > 0,
    }


# --------------------------------------------------------------------------
# Requirement 2 — staggered tier coverage
# --------------------------------------------------------------------------

def coverage_snapshot(
    tier_available_at: Mapping[str, Any],
    query_at: Any,
    required: Sequence[str] = DEFAULT_REQUIRED_TIERS,
) -> dict[str, Any]:
    """Which tiers of one reporting week are admissible at ``query_at``.

    ``complete`` requires every required tier to be individually admissible;
    tiers published at different times are never treated as simultaneous.
    ``as_of`` is the latest availability among the admitted tiers.
    """
    admitted = sorted(t for t, av in tier_available_at.items() if admissible(query_at, av))
    missing = sorted(t for t in required if t not in admitted)
    as_of = None
    if admitted:
        as_of = max(tier_available_at[t] for t in admitted)
    return {
        "admitted_tiers": tuple(admitted),
        "missing_required_tiers": tuple(missing),
        "complete": not missing,
        "as_of": as_of,
        "label": "complete" if not missing else "partial:" + "+".join(admitted or ["none"]),
    }


def combine_tier_volumes(
    tier_volumes: Mapping[str, Mapping[str, float]],
    coverage: Mapping[str, Any],
    allow_partial: bool = False,
) -> dict[str, Any]:
    """Sum venue volumes across ADMITTED tiers only.

    Refuses (ValueError) to combine a partial coverage state unless
    ``allow_partial`` is set, in which case the result is labelled partial and
    is never marked complete.
    """
    if not coverage.get("complete") and not allow_partial:
        raise ValueError(
            "refusing to combine tiers as complete: missing "
            + ",".join(coverage.get("missing_required_tiers", ()))
        )
    out: dict[str, float] = {}
    for tier in coverage.get("admitted_tiers", ()):
        for venue, v in tier_volumes.get(tier, {}).items():
            out[venue] = out.get(venue, 0.0) + float(v)
    return {
        "volumes": out,
        "tiers": tuple(coverage.get("admitted_tiers", ())),
        "complete": bool(coverage.get("complete")),
        "label": coverage.get("label"),
    }


# --------------------------------------------------------------------------
# Requirement 3 — shares that conserve the reported denominator
# --------------------------------------------------------------------------

def is_unknown_venue(label: Any) -> bool:
    if label is None:
        return True
    if isinstance(label, float) and math.isnan(label):
        return True
    return str(label).strip().upper() in UNKNOWN_VENUE_LABELS


def venue_shares(
    volumes: Mapping[Any, float],
    reported_total: float | None = None,
    extra_unknown_mass: float = 0.0,
    tol: float = 1e-9,
) -> dict[str, Any]:
    """Venue shares with explicit unknown / unmapped mass.

    Unknown labels (empty, None, 'De Minimis Firms', ...) are moved to the
    unknown bucket instead of being dropped. If ``reported_total`` exceeds the
    sum of rows, the gap is unmapped mass; a reported total smaller than the
    rows is a contract violation and raises. Shares + unknown_share == 1.
    """
    known: dict[str, float] = {}
    unknown = float(extra_unknown_mass)
    if unknown < 0:
        raise ValueError("negative unknown mass")
    for k, v in volumes.items():
        v = float(v)
        if v < 0 or math.isnan(v):
            raise ValueError(f"invalid volume for {k!r}")
        if is_unknown_venue(k):
            unknown += v
        else:
            key = str(k)
            known[key] = known.get(key, 0.0) + v
    row_total = sum(known.values()) + unknown
    unmapped_gap = 0.0
    if reported_total is not None:
        rt = float(reported_total)
        if rt + tol * max(1.0, rt) < row_total:
            raise ValueError("reported total below the sum of reported rows")
        unmapped_gap = max(0.0, rt - row_total)
        unknown += unmapped_gap
        total = rt
    else:
        total = row_total
    if total <= 0:
        return {"total": 0.0, "shares": {}, "unknown_mass": unknown,
                "unknown_share": None, "unmapped_gap": unmapped_gap}
    shares = {k: v / total for k, v in known.items()}
    unknown_share = unknown / total
    if abs(sum(shares.values()) + unknown_share - 1.0) > 1e-9:
        raise AssertionError("share conservation failed")
    return {"total": total, "shares": shares, "unknown_mass": unknown,
            "unknown_share": unknown_share, "unmapped_gap": unmapped_gap}


# --------------------------------------------------------------------------
# Requirement 5 — concentration with unknown-mass bounds
# --------------------------------------------------------------------------

def hhi(shares: Iterable[float]) -> float:
    s = np.asarray(list(shares), dtype=float)
    if s.size == 0:
        return float("nan")
    tot = s.sum()
    if tot <= 0:
        return float("nan")
    s = s / tot
    return float(np.sum(s * s))


def entropy(shares: Iterable[float]) -> float:
    s = np.asarray(list(shares), dtype=float)
    s = s[s > 0]
    if s.size == 0:
        return float("nan")
    s = s / s.sum()
    return float(-np.sum(s * np.log(s)))


def effective_venue_count(shares: Iterable[float]) -> dict[str, float]:
    vals = list(shares)
    h = hhi(vals)
    e = entropy(vals)
    return {"inverse_hhi": (1.0 / h) if h and not math.isnan(h) else float("nan"),
            "exp_entropy": math.exp(e) if not math.isnan(e) else float("nan")}


def hhi_bounds(share_result: Mapping[str, Any], unknown_may_overlap_known: bool = True) -> dict[str, float]:
    """Lower/upper HHI bounds given unknown mass of unknown composition.

    lower: unknown mass spread over infinitely many infinitesimal venues.
    upper: unknown mass merged into the largest known venue when it may
    overlap known venues; otherwise counted as ONE separate venue.
    Shares here are fractions of the full (conserved) denominator.
    """
    shares = dict(share_result.get("shares", {}))
    u = float(share_result.get("unknown_share") or 0.0)
    known = np.asarray(list(shares.values()), dtype=float)
    lo = float(np.sum(known * known))
    if u <= 0:
        return {"lower": lo, "upper": lo, "point_known_only": hhi(known) if known.size else float("nan"),
                "unknown_share": 0.0}
    if unknown_may_overlap_known and known.size:
        i = int(np.argmax(known))
        merged = known.copy()
        merged[i] += u
        up = float(np.sum(merged * merged))
    else:
        up = lo + u * u
    return {"lower": lo, "upper": up,
            "point_known_only": hhi(known) if known.size else float("nan"),
            "unknown_share": u}


# --------------------------------------------------------------------------
# Venue-change decomposition (exact, additive)
# --------------------------------------------------------------------------

def decompose_hhi_change(prev: Mapping[str, float], curr: Mapping[str, float]) -> dict[str, float]:
    """Exact split of HHI(curr) - HHI(prev) on known-venue volumes.

    within_common = sum over venues in both of (s_curr^2 - s_prev^2)
    entry         = sum over venues only in curr of s_curr^2
    exit          = sum over venues only in prev of s_prev^2
    delta         = within_common + entry - exit
    Shares are normalised on each period's own known total.
    """
    def _norm(d: Mapping[str, float]) -> dict[str, float]:
        t = float(sum(d.values()))
        return {k: float(v) / t for k, v in d.items()} if t > 0 else {}
    p, c = _norm(prev), _norm(curr)
    common = set(p) & set(c)
    within = sum(c[k] ** 2 - p[k] ** 2 for k in common)
    entry = sum(c[k] ** 2 for k in set(c) - common)
    exit_ = sum(p[k] ** 2 for k in set(p) - common)
    delta = sum(v * v for v in c.values()) - sum(v * v for v in p.values())
    return {"delta": delta, "within_common": within, "entry": entry, "exit": exit_,
            "n_common": len(common), "n_entry": len(set(c) - common), "n_exit": len(set(p) - common)}


# --------------------------------------------------------------------------
# Requirement 4 — append-only result vintages
# --------------------------------------------------------------------------

@dataclass
class VintageLedger:
    """Append-only store of result vintages keyed by (subject key).

    A correction is a NEW vintage; earlier vintages are never mutated or
    removed. There is intentionally no delete / overwrite method.
    """
    _rows: dict[str, list[dict]] = field(default_factory=dict)

    def record(self, key: str, available_at: Any, payload: Mapping[str, Any], note: str = "") -> int:
        if available_at is None:
            raise ValueError("a result vintage needs a known availability time")
        hist = self._rows.setdefault(str(key), [])
        if hist and available_at < hist[-1]["available_at"]:
            raise ValueError("vintages must be appended in availability order")
        vid = len(hist)
        hist.append({"vintage": vid, "available_at": available_at,
                     "payload": copy.deepcopy(dict(payload)), "note": note,
                     "supersedes": vid - 1 if vid else None})
        return vid

    def history(self, key: str) -> list[dict]:
        return copy.deepcopy(self._rows.get(str(key), []))

    def as_of(self, key: str, query_at: Any) -> dict | None:
        best = None
        for row in self._rows.get(str(key), []):
            if admissible(query_at, row["available_at"]):
                best = row
        return copy.deepcopy(best) if best is not None else None


# --------------------------------------------------------------------------
# Requirement 6 — vocabulary guard
# --------------------------------------------------------------------------

_SEP_RE = re.compile(r"[\s\-_/]+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


def _spaced(text: str) -> str:
    return _SEP_RE.sub(" ", str(text).lower()).strip()


def _squashed(text: str) -> str:
    return _NON_ALNUM_RE.sub("", str(text).lower())


def forbidden_terms_in(text: str) -> list[str]:
    """Forbidden terms in ``text`` after separator normalisation.

    Matching is case-insensitive; hyphens, underscores, slashes and whitespace
    runs collapse to one space, and a separator-free form is checked too, so
    "Short-Interest", "short_interest" and "shortinterest" all match.
    """
    sp, sq = _spaced(text), _squashed(text)
    return [t for t in FORBIDDEN_INTERPRETATION_TERMS if _spaced(t) in sp or _squashed(t) in sq]


def assert_no_forbidden_interpretation(obj: Any) -> None:
    """Raise ValueError if any string inside ``obj`` (recursively) carries a
    forbidden accumulation / net-buying / live-print / short-interest term."""
    def _walk(x: Any):
        if isinstance(x, str):
            yield x
        elif isinstance(x, Mapping):
            for k, v in x.items():
                yield from _walk(k)
                yield from _walk(v)
        elif isinstance(x, (list, tuple, set, frozenset)):
            for v in x:
                yield from _walk(v)
    for s in _walk(obj):
        hits = forbidden_terms_in(s)
        if hits:
            raise ValueError(f"forbidden interpretation terms: {hits}")


def describe_concentration(label: str, bounds: Mapping[str, float], n_venues: int) -> dict[str, Any]:
    """Descriptive-only record; text is checked by the vocabulary guard."""
    rec = {
        "subject": label,
        "measure": "venue share concentration (HHI) of reported weekly volume",
        "hhi_lower": float(bounds["lower"]),
        "hhi_upper": float(bounds["upper"]),
        "n_known_venues": int(n_venues),
        "category_note": "ATS/non-ATS is a venue/reporting category only; it says nothing about who traded or why",
        "scope": "descriptive; research only; not a signal",
    }
    assert_no_forbidden_interpretation(rec)
    return rec


# --------------------------------------------------------------------------
# Dependence-aware comparison helpers (pure)
# --------------------------------------------------------------------------

def chronological_split(ordered_units: Sequence[Any], n_train: int) -> tuple[list, list]:
    units = list(ordered_units)
    if not 0 < n_train < len(units):
        raise ValueError("n_train must leave a non-empty holdout")
    if units != sorted(units):
        raise ValueError("units must be in chronological order")
    return units[:n_train], units[n_train:]


def split_respects_clock(train_available_at: Sequence[Any], holdout_available_at: Sequence[Any],
                         origin: Any) -> bool:
    """True only when every training unit is admissible at ``origin`` and every
    holdout unit has a KNOWN availability strictly after ``origin``."""
    if origin is None or not len(holdout_available_at):
        return False
    train_ok = all(admissible(origin, t) for t in train_available_at)
    hold_ok = all(t is not None and not admissible(origin, t) for t in holdout_available_at)
    return bool(train_ok and hold_ok)


def require_split_respects_clock(train_available_at: Sequence[Any], holdout_available_at: Sequence[Any],
                                 origin: Any) -> None:
    """Raise ValueError('REFUSING: ...') when the split violates the availability clock."""
    if not split_respects_clock(train_available_at, holdout_available_at, origin):
        raise ValueError("REFUSING: train/holdout split violates the availability clock at origin "
                         f"{origin!r}")


def shrunk_mean(symbol_mean: np.ndarray, pooled_mean: float, lam: float) -> np.ndarray:
    return lam * np.asarray(symbol_mean, dtype=float) + (1.0 - lam) * float(pooled_mean)


def moving_block_bootstrap_mean(
    series: Sequence[float], block_len: int, n_boot: int, seed: int
) -> dict[str, Any]:
    """Moving-block bootstrap of the mean of a time-ordered series.

    Honest N is the number of time units, with ~len/block_len effective
    blocks; rows inside a time unit are never resampled independently.
    """
    x = np.asarray(series, dtype=float)
    n = x.size
    if n == 0:
        raise ValueError("empty series")
    b = max(1, min(int(block_len), n))
    starts = np.arange(n - b + 1)
    rng = np.random.default_rng(seed)
    k = int(math.ceil(n / b))
    means = np.empty(n_boot)
    for i in range(n_boot):
        s = rng.choice(starts, size=k, replace=True)
        idx = (s[:, None] + np.arange(b)[None, :]).ravel()[:n]
        means[i] = x[idx].mean()
    return {"mean": float(x.mean()), "ci_lo": float(np.quantile(means, 0.025)),
            "ci_hi": float(np.quantile(means, 0.975)), "n_units": int(n),
            "block_len": b, "n_blocks_effective": int(math.ceil(n / b)), "n_boot": int(n_boot)}


def moving_block_bootstrap_ratio(
    numerator: Sequence[float], denominator: Sequence[float], block_len: int, n_boot: int, seed: int
) -> dict[str, Any]:
    """Moving-block bootstrap of mean(numerator) / mean(denominator).

    Both series share one time index and are resampled with the SAME blocks.
    With few time units (e.g. 7 units, block 2 -> ~4 effective blocks) the
    percentile interval is coarse and its coverage is not reliable; callers
    must report ``n_blocks_effective`` beside it.
    """
    num = np.asarray(numerator, dtype=float)
    den = np.asarray(denominator, dtype=float)
    if num.shape != den.shape or num.size == 0:
        raise ValueError("numerator and denominator must be equal-length, non-empty series")
    n = num.size
    b = max(1, min(int(block_len), n))
    starts = np.arange(n - b + 1)
    rng = np.random.default_rng(seed)
    k = int(math.ceil(n / b))
    ratios = np.empty(n_boot)
    for i in range(n_boot):
        s = rng.choice(starts, size=k, replace=True)
        idx = (s[:, None] + np.arange(b)[None, :]).ravel()[:n]
        ratios[i] = num[idx].mean() / den[idx].mean()
    return {"ratio": float(num.mean() / den.mean()), "ci_lo": float(np.quantile(ratios, 0.025)),
            "ci_hi": float(np.quantile(ratios, 0.975)), "n_units": int(n), "block_len": b,
            "n_blocks_effective": k, "n_boot": int(n_boot)}
