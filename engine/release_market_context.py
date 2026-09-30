"""MRI PR-I — display-only enrichments for the release_forecast.v2 artifact.

Four pure functions called by scripts/build_release_forecast.py after projections
are built. All are fail-open: any exception → return None, caller logs and continues.

BINDINGS (MRI-R15 / MRI-R16 / MRI-R17 / MRI-R22):
  - display_only=True: no field here gates, scores, or sizes any position.
  - No LLM calls, no origination of values.
  - Market-implied read (R16) is NEVER fused into model math — context only.
  - Reaction-sensitivity (R17) is a pure lookup; no regression, no positioning inputs.
  - Expectation read (R22) is NEVER fused into model math — context only.

--------
1. compute_surprise_distribution (MRI-R15)
--------
Given a projection dict (containing quantile fields p10..p90 and surprise_skew.sigma)
and a benchmark median, compute the probability mass of the model's predictive
distribution that falls:
  - ABOVE the inline band top:  p_hot   (hotter than expected)
  - BELOW the inline band bottom: p_cold (cooler than expected)
  - WITHIN the ±0.35σ band:     p_inline

Approximation method (documented per §MRI-R15 spec):
  We model the CDF with a piecewise-linear interpolation through the five empirical
  quantile points:
      (p10, 0.10), (p25, 0.25), (p50, 0.50), (p75, 0.75), (p90, 0.90)
  Beyond the tails we EXTEND the outermost slope linearly, clamped so the CDF
  approaches 0.0 below and 1.0 above; we cap the extension at ±4σ from the
  benchmark median to avoid unbounded extrapolation on heavy-tail quantiles.

  P(X <= x) for x outside [p10, p90] is extrapolated as:
    lower tail: slope = (0.25 - 0.10) / (p25 - p10) applied leftward from p10
    upper tail: slope = (0.90 - 0.75) / (p90 - p75) applied rightward from p90
  Both are clamped to [0.0, 1.0].

  Integration of p_hot, p_cold, p_inline is performed by evaluating the CDF at the
  band boundaries (lo = bench - 0.35σ, hi = bench + 0.35σ):
    p_inline = CDF(hi) - CDF(lo)
    p_cold   = CDF(lo)
    p_hot    = 1.0 - CDF(hi)

  The three values are renormalized to sum exactly to 1.0.

Caveats / limitations:
  - Piecewise-linear CDF with 5 knots is a coarse approximation; the true
    distribution is unknown. Provides directional signal only.
  - Tail extrapolation is sensitive to the slope of the outermost quantile segment.
    If p10≈p25 or p75≈p90, slope can be very steep — the ±4σ cap prevents runaway.
  - The inline band width (±0.35σ) is fixed per §3.4 of the masterplan.

--------
2. get_market_implied_benchmark (MRI-R16)
--------
Reads data/prediction_markets/snapshots.parquet and finds the row(s) for the
configured event_key(s) for CPI / NFP, returning a structured implied-expectation
dict. Returns None if no matching rows exist (snapshots accrue nightly).

Context only — never fed into model math.

--------
3. get_reaction_sensitivity (MRI-R17)
--------
Pure lookup of research/release_playbook/results/playbook_v1.json.
Returns historical market-sensitivity means for h1 hot/cold buckets, 2021plus era.
Prefers regime-conditioned cell if current regime matches and n>=8.

--------
4. compute_expectation_read (MRI-R22)
--------
Given our point forecast, a subset of the benchmark_set that constitutes the
EXPECTATION SET (cleveland_nowcast + market-implied central value from Kalshi/
Polymarket), and sigma_scale_pp, compute whether we are above / below / aligned
with market+nowcast expectations.

Expectation set:
  - cleveland_nowcast (CPI family only)
  - Kalshi implied_median (preferred) or Polymarket 'implied' if numeric

Trend benchmarks (naive_prior, trailing_3m, ar_model) are NOT part of this set.

Read:
  expectation_median = median of available expectation values
  delta_pp           = point - expectation_median
  standardized       = delta_pp / sigma_scale_pp
  tag                = 'above_expectations' if standardized > +0.35
                       'below_expectations' if standardized < -0.35
                       'aligned' otherwise

Returns {tag, delta_pp (4dp), standardized (2dp), expectation_median, sources, n_sources}
or None when:
  - expectation set is empty (no expectation sources available)
  - point is None or sigma_scale_pp is None/zero
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────
_INLINE_HALF_WIDTH_SIGMA = 0.35   # ±σ band per MRI §3.4
_TAIL_SIGMA_CAP = 4.0             # cap tail extension beyond ±4σ from benchmark
_ERA_LABEL = "2021plus"           # exact string used in playbook_v1.json
_REGIME_MIN_N = 8                 # prefer regime cell only if n >= this

# MRI-R33 STALE-ENRICH-1/2: TTL staleness gates for enrichment sources.
# A stale source nulls the field with a stale reason; never silently extrapolates.
_KALSHI_TTL_DAYS = 5              # Kalshi / market-implied ≤5d old else null
_MARKET_IMPLIED_TTL_DAYS = 5      # same rule for Polymarket snapshots


def _check_parquet_staleness(path: Path, ttl_days: float, stamp_col: str) -> str | None:
    """Return a stale reason string if the parquet's newest `stamp_col` date is
    older than ttl_days, else None.

    Judged from the embedded stamp column (asof_date / snapshot_date), NEVER
    file mtime — on CI runners a checkout rewrites files with mtime = checkout
    time, so a dead collector's committed parquet always looked fresh by mtime
    and this guard was blind to exactly the frozen-source case MRI-R33 exists
    for (#2690 class). An unreadable/empty/missing stamp column reads as stale
    (the guard fires and the field nulls with a reason — the safe direction).
    Returns None if the file does not exist (caller handles absent file via
    empty result, not staleness).
    """
    if not path.exists():
        return None  # absence handled by caller (returns None result)
    try:
        s = pd.read_parquet(path, columns=[stamp_col])[stamp_col]
        newest = pd.to_datetime(s, errors="coerce").dropna().max()
    except Exception as e:  # noqa: BLE001
        return (
            f"stale: cannot read {stamp_col} from {path.name} ({e}) "
            f"(MRI-R33 STALE-ENRICH)"
        )
    if pd.isna(newest):
        return (
            f"stale: no readable {stamp_col} in {path.name} "
            f"(MRI-R33 STALE-ENRICH)"
        )
    age_days = (datetime.now(timezone.utc).date() - newest.date()).days
    if age_days > ttl_days:
        return (
            f"stale: newest {stamp_col} {newest.date()} is {age_days:.1f}d old "
            f"(TTL={ttl_days}d, MRI-R33 STALE-ENRICH)"
        )
    return None


# ── 1. Surprise distribution (MRI-R15) ────────────────────────────────────────

def _piecewise_cdf(x: float, knots: list[tuple[float, float]]) -> float:
    """Evaluate the piecewise-linear CDF at x.

    knots: sorted list of (value, prob) pairs. Extrapolation beyond the outer
    knots uses the slope of the nearest outer segment, clamped to [0, 1].
    """
    xs = [k[0] for k in knots]
    ps = [k[1] for k in knots]

    # Exact match
    if x <= xs[0]:
        # Left tail: extrapolate leftward using slope of first segment
        if len(xs) >= 2 and (xs[1] - xs[0]) != 0:
            slope = (ps[1] - ps[0]) / (xs[1] - xs[0])
        else:
            slope = 0.0
        return max(0.0, ps[0] + slope * (x - xs[0]))

    if x >= xs[-1]:
        # Right tail: extrapolate rightward using slope of last segment
        if len(xs) >= 2 and (xs[-1] - xs[-2]) != 0:
            slope = (ps[-1] - ps[-2]) / (xs[-1] - xs[-2])
        else:
            slope = 0.0
        return min(1.0, ps[-1] + slope * (x - xs[-1]))

    # Interior: find bracketing segment and interpolate
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            seg_w = xs[i + 1] - xs[i]
            if seg_w == 0:
                return ps[i]
            t = (x - xs[i]) / seg_w
            return ps[i] + t * (ps[i + 1] - ps[i])

    return 0.5  # fallback (should not reach)


def compute_surprise_distribution(
    projection: dict[str, Any],
    benchmark_median: float,
    sigma: float,
) -> dict[str, float] | None:
    """Compute p_hot / p_cold / p_inline from projection quantiles.

    Args:
        projection: dict with keys p10, p25, p50, p75, p90 (all numeric or None).
        benchmark_median: the benchmark median (e.g. median of naive_prior, trailing_3m, etc.)
        sigma: trailing-24-realized-surprise σ (from surprise_skew.sigma).

    Returns:
        {p_hot, p_cold, p_inline} rounded to 2dp, summing to 1.0 ±0.01,
        or None if any required input is missing / invalid.
    """
    try:
        p10 = projection.get("p10")
        p25 = projection.get("p25")
        p50 = projection.get("p50")
        p75 = projection.get("p75")
        p90 = projection.get("p90")

        # Require all five quantiles and sigma
        if any(v is None for v in [p10, p25, p50, p75, p90]):
            return None
        if sigma is None or sigma <= 0:
            return None

        p10, p25, p50, p75, p90 = float(p10), float(p25), float(p50), float(p75), float(p90)
        sigma = float(sigma)
        benchmark_median = float(benchmark_median)

        # Validate quantile ordering (allow small ties from rounding)
        quantiles = [p10, p25, p50, p75, p90]
        for i in range(len(quantiles) - 1):
            if quantiles[i] > quantiles[i + 1] + 1e-9:
                log.debug(
                    "compute_surprise_distribution: quantiles not monotone %s > %s",
                    quantiles[i], quantiles[i + 1],
                )
                return None

        # Build knots
        knots: list[tuple[float, float]] = [
            (p10, 0.10),
            (p25, 0.25),
            (p50, 0.50),
            (p75, 0.75),
            (p90, 0.90),
        ]

        # Inline band boundaries: ±0.35σ around benchmark median
        half = _INLINE_HALF_WIDTH_SIGMA * sigma
        lo = benchmark_median - half
        hi = benchmark_median + half

        # Cap tail evaluation at ±4σ from benchmark to avoid wild extrapolation
        lo_capped = max(lo, benchmark_median - _TAIL_SIGMA_CAP * sigma)
        hi_capped = min(hi, benchmark_median + _TAIL_SIGMA_CAP * sigma)
        # (lo/hi only reach beyond ±4σ if someone passes a very small sigma — unlikely)
        lo = lo_capped
        hi = hi_capped

        cdf_lo = _piecewise_cdf(lo, knots)
        cdf_hi = _piecewise_cdf(hi, knots)

        p_cold = float(np.clip(cdf_lo, 0.0, 1.0))
        p_inline_raw = float(np.clip(cdf_hi - cdf_lo, 0.0, 1.0))
        p_hot = float(np.clip(1.0 - cdf_hi, 0.0, 1.0))

        # Renormalize to sum to 1.0
        total = p_cold + p_inline_raw + p_hot
        if total <= 0:
            return None
        p_cold = round(p_cold / total, 2)
        p_inline = round(p_inline_raw / total, 2)
        p_hot = round(p_hot / total, 2)

        # Final clamp rounding residual so sum == 1.00
        residual = round(1.0 - (p_cold + p_inline + p_hot), 2)
        p_inline = round(p_inline + residual, 2)

        return {"p_hot": p_hot, "p_cold": p_cold, "p_inline": p_inline}

    except Exception as exc:
        log.debug("compute_surprise_distribution failed: %s", exc)
        return None


# ── 2. Market-implied benchmark (MRI-R16) ────────────────────────────────────

# event_key → (release family, pick strategy)
# These map to the new config.yml event keys (cpi_print, nfp_print).
_RELEASE_EVENT_KEYS: dict[str, str] = {
    "cpi_headline": "cpi_print",
    "cpi_core": "cpi_print",
    "nfp": "nfp_print",
}


def _market_title_matches_target(release_type: str, title: object) -> bool:
    """Prevent one CPI-family event from being attached to a different target.

    The legacy event-key taxonomy groups headline and core CPI under
    ``cpi_print``.  The human-readable title is therefore a required secondary
    identity check: a Core CPI contract must never become a headline benchmark,
    and a YoY or unit-ambiguous contract must never become a MoM benchmark.
    """
    if release_type not in {"cpi_headline", "cpi_core"}:
        return True
    normalized = str(title or "").strip().lower()
    is_mom = any(
        token in normalized
        for token in ("mom", "m/m", "month over month", "month-over-month", "monthly")
    )
    is_yoy = any(
        token in normalized
        for token in ("yoy", "y/y", "year over year", "year-over-year", "annual")
    )
    if "cpi" not in normalized or not is_mom or is_yoy:
        return False
    if release_type == "cpi_core":
        return "core" in normalized
    return "core" not in normalized


# Kalshi bracket-ladder store (collectors/kalshi_releases.py, #1876).
# Summary rows carry implied_median per (asof_date, release_type, period).
_KALSHI_RELEASE_MAP = {
    "cpi_headline": "cpi",   # Kalshi KXCPI tracks headline MoM only
    "nfp": "nfp",
    "claims": "claims",
}


def get_kalshi_implied(
    release_type: str,
    period: str | None,
    kalshi_path: Path,
) -> dict | None:
    """Return the latest Kalshi implied read for (release_type, period), or None.

    MRI-R33 STALE-ENRICH-1: if the Kalshi parquet is older than 5 days, returns a
    stale-annotated null dict ({source, stale_reason}) rather than a stale value.

    Reads summary rows (is_summary=True) from the first-seen snapshot store and
    returns the most recent asof_date's implied_median for the matching period.
    Context only — never fused into model math (MRI-R16). implied_mean is not
    stored upstream by design (open-ended ladder; tail assumption dishonest).
    """
    try:
        kalshi_type = _KALSHI_RELEASE_MAP.get(release_type)
        if kalshi_type is None or period is None or not kalshi_path.exists():
            return None
        # MRI-R33: TTL staleness gate — null with reason if > 5 days old
        stale_reason = _check_parquet_staleness(kalshi_path, _KALSHI_TTL_DAYS, "asof_date")
        if stale_reason:
            log.warning("get_kalshi_implied: %s", stale_reason)
            return {"source": "kalshi", "implied_median": None, "stale_reason": stale_reason}
        df = pd.read_parquet(kalshi_path)
        if df.empty or "is_summary" not in df.columns:
            return None
        sub = df[
            (df["is_summary"] == True)  # noqa: E712 — parquet bool column
            & (df["release_type"] == kalshi_type)
            & (df["period"] == str(period))
        ]
        sub = sub[sub["implied_median"].notna()]
        if sub.empty:
            return None
        row = sub.sort_values("asof_date").iloc[-1]
        return {
            "source": "kalshi",
            "event_ticker": row.get("event_ticker"),
            "implied_median": float(row["implied_median"]),
            "p_above_lowest_strike": (
                float(row["p_above_lowest_strike"])
                if pd.notna(row.get("p_above_lowest_strike")) else None
            ),
            "n_brackets": int(row["n_brackets"]) if pd.notna(row.get("n_brackets")) else None,
            "asof": str(row["asof_date"]),
        }
    except Exception:
        return None


def get_market_implied_benchmark(
    release_type: str,
    release_date_str: str | None,
    snapshots_path: Path,
) -> dict | None:
    """Return market-implied benchmark dict for a release, or None if absent.

    MRI-R33 STALE-ENRICH-2: if the snapshots parquet is older than 5 days, returns a
    stale-annotated null dict ({source, stale_reason}) rather than a stale value.

    Reads the latest snapshot for the matching event_key (cpi_print / nfp_print),
    picks the row with the end_date nearest to (and >= ) release_date_str, and
    derives an implied read from the highest-probability outcome.

    The result is context only — never fused into model math (MRI-R16).

    Returns:
        {source, event_key, event_title, implied, prob_top, asof} or None.
    """
    try:
        event_key = _RELEASE_EVENT_KEYS.get(release_type)
        if event_key is None:
            return None  # claims and unknown releases: no market event

        if not snapshots_path.exists():
            return None

        # MRI-R33: TTL staleness gate — null with reason if > 5 days old
        stale_reason = _check_parquet_staleness(snapshots_path, _MARKET_IMPLIED_TTL_DAYS,
                                                "snapshot_date")
        if stale_reason:
            log.warning("get_market_implied_benchmark: %s", stale_reason)
            return {"source": "market_implied", "implied": None, "stale_reason": stale_reason}

        df = pd.read_parquet(snapshots_path)
        if df.empty:
            return None

        # Filter to the target event_key
        mask = df["event_key"] == event_key
        sub = df[mask]
        if sub.empty:
            return None

        # ``cpi_print`` historically contains both headline and core markets.
        # Fail closed on title/target mismatch instead of silently borrowing the
        # other target's distribution.
        if release_type in {"cpi_headline", "cpi_core"}:
            sub = sub[
                sub["event_title"].map(
                    lambda title: _market_title_matches_target(release_type, title)
                )
            ]
            if sub.empty:
                return None

        # Latest snapshot_date
        latest_snapshot = str(sub["snapshot_date"].max())
        sub = sub[sub["snapshot_date"] == latest_snapshot]

        # If release_date is given, prefer end_date >= release_date (nearest)
        if release_date_str:
            fut = sub[sub["end_date"] >= release_date_str[:10]]
            if not fut.empty:
                nearest_end = str(fut["end_date"].min())
                sub = fut[fut["end_date"] == nearest_end]
            # Else fall through to all rows for this event_key / snapshot_date

        if sub.empty:
            return None

        # Top outcome by prob
        top_row = sub.loc[sub["prob"].idxmax()]
        event_title = str(top_row.get("event_title", ""))
        implied_outcome = str(top_row.get("outcome", ""))
        prob_top = float(top_row.get("prob", 0.0))
        source = str(top_row.get("source", "polymarket"))

        return {
            "source": source,
            "event_key": event_key,
            "event_title": event_title,
            "implied": implied_outcome,
            "prob_top": round(prob_top, 4),
            "asof": latest_snapshot,
        }

    except Exception as exc:
        log.debug("get_market_implied_benchmark(%s) failed: %s", release_type, exc)
        return None


# ── 3. Reaction-sensitivity chip (MRI-R17) ───────────────────────────────────

def get_reaction_sensitivity(
    release_type: str,
    playbook_path: Path,
    current_regime: str | None = None,
) -> dict | None:
    """Return h1 reaction-sensitivity means plus source-bound descriptive evidence.

    The four legacy compact mean fields remain unchanged for existing clients. The
    additive evidence block is built from the same selected cells so sample size,
    interval, regime, target and horizon metadata cannot drift from displayed means.

    h1 is the next trading-session close versus the pre-event prior close. It is not
    a one-hour horizon. CPI playbook surprises retain the frozen v1 legacy CPIAUCSL
    initial-print index-point-change construction; they are not relabelled as official
    MoM percentage surprises.

    Pure lookup -- no regression, no positioning inputs, no forecast/trade authority.
    """
    try:
        import hashlib
        import json
        import math

        release_family_map = {
            "cpi_headline": "cpi",
            "cpi_core": "cpi",
            "nfp": "nfp",
        }
        release_family = release_family_map.get(release_type)
        if release_family is None:
            return None

        if not playbook_path.exists():
            log.debug("get_reaction_sensitivity: playbook not found at %s", playbook_path)
            return None

        raw_bytes = playbook_path.read_bytes()
        source_digest = hashlib.sha256(raw_bytes).hexdigest()
        cells: list[dict] = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(cells, list):
            return None

        def _finite_number(value: object) -> bool:
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
            )

        def _valid_regime_n(value: object) -> bool:
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= _REGIME_MIN_N
            )

        def _unique_candidate(candidates: list[dict]) -> dict | None:
            # Duplicate cells are ambiguous evidence. Refuse the candidate
            # rather than selecting by file order.
            return candidates[0] if len(candidates) == 1 else None

        def _pick_cell(
            source_cells: list[dict],
            release: str,
            bucket: str,
            outcome: str,
            era: str,
            regime: str | None,
        ) -> dict | None:
            """Return one source cell; ambiguous/invalid candidates fail safely."""
            if regime is not None:
                conditioned = [
                    c for c in source_cells
                    if c.get("release") == release
                    and c.get("bucket") == bucket
                    and c.get("outcome") == outcome
                    and c.get("horizon") == "h1"
                    and c.get("era") == era
                    and c.get("regime") == regime
                    and _valid_regime_n(c.get("n"))
                    and _finite_number(c.get("mean"))
                ]
                selected = _unique_candidate(conditioned)
                if selected is not None:
                    return selected

            era_level = [
                c for c in source_cells
                if c.get("release") == release
                and c.get("bucket") == bucket
                and c.get("outcome") == outcome
                and c.get("horizon") == "h1"
                and c.get("era") == era
                and c.get("regime") is None
                and _finite_number(c.get("mean"))
            ]
            return _unique_candidate(era_level)

        if release_family == "cpi":
            target = {
                "release": "cpi",
                "observed_value": "cpi_initial_print_index_point_mom_change",
                "reference_benchmark": "prior_period_initial_print_index_point_mom_change",
                "standardization": "realized_surprise_divided_by_trailing_24_event_sigma",
                "bucket_definition": {
                    "hot": "standardized_surprise_gt_0.5",
                    "cold": "standardized_surprise_lt_-0.5",
                },
                "knowledge_basis": "initial_vintage_prints_prior_only",
            }
        else:
            target = {
                "release": "nfp",
                "observed_value": "nfp_initial_print_thousands_change",
                "reference_benchmark": "prior_period_initial_print_thousands_change",
                "standardization": "realized_surprise_divided_by_trailing_24_event_sigma",
                "bucket_definition": {
                    "hot": "standardized_surprise_gt_0.5",
                    "cold": "standardized_surprise_lt_-0.5",
                },
                "knowledge_basis": "initial_vintage_prints_prior_only",
            }

        source = {
            "version": "playbook_v1",
            "artifact": "research/release_playbook/results/playbook_v1.json",
            "sha256": source_digest,
        }
        outcome_metadata = {
            "dgs10_bp": {
                "unit": "basis_points",
                "reference_basis": "next_trading_session_close_vs_pre_event_prior_close",
            },
            "spy_pct": {
                "unit": "percent_return",
                "reference_basis": "next_trading_session_close_vs_pre_event_prior_close",
            },
        }

        regime_cells_used = False
        fields: dict[str, float | None] = {}
        evidence_cells: dict[str, dict] = {}

        for bucket in ("hot", "cold"):
            for outcome_key, field_prefix in [
                ("dgs10_bp", f"dgs10_h1_{bucket}"),
                ("spy_pct", f"spy_h1_{bucket}"),
            ]:
                legacy_field = (
                    f"{field_prefix}_bp"
                    if outcome_key == "dgs10_bp"
                    else f"{field_prefix}_pct"
                )
                cell = _pick_cell(
                    cells, release_family, bucket, outcome_key, _ERA_LABEL, current_regime
                )
                if cell is None:
                    fields[field_prefix] = None
                    continue

                cell_regime = cell.get("regime")
                if cell_regime is not None:
                    regime_cells_used = True

                # Mean and metadata intentionally come from this same selected cell.
                mean_value = round(float(cell["mean"]), 4)
                fields[field_prefix] = mean_value

                meta = outcome_metadata[outcome_key]
                cell_limitations = [
                    "descriptive_historical_context_only_no_forecast_or_trade_authority",
                    "effective_n_sample_span_and_cell_specific_exclusions_unknown",
                ]
                if release_family == "cpi":
                    cell_limitations.append(
                        "cpi_surprise_basis_is_legacy_index_point_difference_not_official_mom_percentage"
                    )
                if cell_regime is not None:
                    cell_limitations.append(
                        "regime_label_is_latest_revised_not_as_observed"
                    )

                detail: dict = {
                    "release": release_family,
                    "outcome": outcome_key,
                    "bucket": bucket,
                    "era": _ERA_LABEL,
                    "regime": cell_regime,
                    "horizon": "h1",
                    "mean": mean_value,
                    "unit": meta["unit"],
                    "reference_basis": meta["reference_basis"],
                    "selection_basis": (
                        "current_regime_conditioned_cell"
                        if cell_regime is not None
                        else "era_level_cell"
                    ),
                    "knowledge_status": {
                        "release_prints": "initial_vintage_as_observed",
                        "surprise_inputs": "point_in_time_prior_only",
                        "regime_labels": (
                            "latest_revised_not_as_observed"
                            if cell_regime is not None
                            else "not_used_for_this_cell"
                        ),
                    },
                    "source": dict(source),
                    "limitations": cell_limitations,
                    "unknowns": [
                        "effective_n",
                        "sample_span",
                        "cell_specific_exclusions",
                    ],
                }

                n_value = cell.get("n")
                if (
                    isinstance(n_value, int)
                    and not isinstance(n_value, bool)
                    and n_value >= 0
                ):
                    detail["n"] = n_value

                ci_lo = cell.get("ci_lo")
                ci_hi = cell.get("ci_hi")
                if (
                    _finite_number(ci_lo)
                    and _finite_number(ci_hi)
                    and float(ci_lo) <= float(ci_hi)
                ):
                    detail["interval"] = {
                        "kind": "event_level_bootstrap_95pct",
                        "draws": 800,
                        "seed": 7,
                        "lo": float(ci_lo),
                        "hi": float(ci_hi),
                    }

                evidence_cells[legacy_field] = detail

        note = (
            "Historical means from playbook_v1 2021plus era; regime-conditioned cells used."
            if regime_cells_used
            else "Historical means from playbook_v1 2021plus era; regime=null cells."
        )

        limitations = [
            "descriptive_historical_context_only_no_forecast_or_trade_authority",
            "h1_is_next_trading_session_close_vs_pre_event_prior_close",
            "effective_n_sample_span_and_cell_specific_exclusions_not_in_v1_cell_schema",
        ]
        if release_family == "cpi":
            limitations.append(
                "cpi_surprise_basis_is_legacy_index_point_difference_not_official_mom_percentage"
            )
        if regime_cells_used:
            limitations.append(
                "regime_conditioned_cells_use_latest_revised_labels_not_as_observed"
            )

        return {
            "dgs10_h1_hot_bp": fields.get("dgs10_h1_hot"),
            "dgs10_h1_cold_bp": fields.get("dgs10_h1_cold"),
            "spy_h1_hot_pct": fields.get("spy_h1_hot"),
            "spy_h1_cold_pct": fields.get("spy_h1_cold"),
            "era_basis": _ERA_LABEL,
            "regime_cells_used": regime_cells_used,
            "note": note,
            "evidence": {
                "schema": "reaction_evidence.v1",
                "display_only": True,
                "authority": False,
                "target": target,
                "cells": evidence_cells,
                "limitations": limitations,
            },
        }

    except Exception as exc:
        log.debug("get_reaction_sensitivity(%s) failed: %s", release_type, exc)
        return None


# ── 4. Expectation read (MRI-R22) ─────────────────────────────────────────────

# Band threshold matches the inline band in compute_surprise_distribution (MRI-R15 §3.4)
_EXPECTATION_BAND_THRESHOLD = 0.35  # ±σ


def compute_expectation_read(
    point: float | None,
    expectation_values: dict[str, float | None],
    sigma_scale_pp: float | None,
) -> dict | None:
    """Compute the expectation read for a projected release print (MRI-R22).

    Args:
        point: our point forecast value (pp units, same scale as expectation_values).
        expectation_values: dict mapping source name → value (float or None).
            Valid EXPECTATION SET members are:
              'cleveland_nowcast' — Cleveland Fed nowcast (CPI family only)
              'kalshi'            — Kalshi implied_median (preferred market source)
              'polymarket'        — Polymarket numeric implied value (fallback)
            Trend benchmark keys (naive_prior, trailing_3m, ar_model) are ignored.
        sigma_scale_pp: trailing realized-surprise standard deviation in pp units.
            Same as surprise_skew.sigma_scale_pp from the projection artifact.

    Returns:
        {
          'tag':                'above_expectations' | 'below_expectations' | 'aligned',
          'delta_pp':           float (4 dp), our point - expectation_median,
          'standardized':       float (2 dp), delta_pp / sigma_scale_pp,
          'expectation_median': float, median of available expectation values,
          'sources':            [str], names of sources used (in input order),
          'n_sources':          int,
        }
        or None when:
          - expectation set is empty (all values None or dict empty)
          - point is None
          - sigma_scale_pp is None or <= 0

    Display-only — must never be fused into model math (MRI-R22 binding).
    """
    try:
        if point is None:
            return None
        if sigma_scale_pp is None or sigma_scale_pp <= 0:
            return None

        point_f = float(point)
        sigma_f = float(sigma_scale_pp)

        # Only EXPECTATION SET sources are eligible; trend benchmarks are excluded.
        _EXPECTATION_KEYS = ("cleveland_nowcast", "kalshi", "polymarket")

        sources: list[str] = []
        values: list[float] = []
        for key in _EXPECTATION_KEYS:
            if key in expectation_values:
                v = expectation_values[key]
                if v is not None and np.isfinite(float(v)):
                    sources.append(key)
                    values.append(float(v))

        if not values:
            return None  # empty expectation set → null read

        expectation_median = float(np.median(values))
        delta_pp = point_f - expectation_median
        standardized = delta_pp / sigma_f

        if standardized > _EXPECTATION_BAND_THRESHOLD:
            tag = "above_expectations"
        elif standardized < -_EXPECTATION_BAND_THRESHOLD:
            tag = "below_expectations"
        else:
            tag = "aligned"

        return {
            "tag": tag,
            "delta_pp": round(delta_pp, 4),
            "standardized": round(standardized, 2),
            "expectation_median": round(expectation_median, 4),
            "sources": sources,
            "n_sources": len(sources),
        }

    except Exception as exc:
        log.debug("compute_expectation_read failed: %s", exc)
        return None
