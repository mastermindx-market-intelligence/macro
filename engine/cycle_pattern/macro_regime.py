"""Monthly macro family in the existing historical-analogue research package.

This family does not replace HAR's frozen half-cycle fingerprints. It consumes
an owner-supplied monthly panel and returns a read-only study. Selection is
outcome-blind, and only completed forward windows can be candidates. No source,
episode, study, outcome, forecast or portfolio store is written here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math

import numpy as np

from engine.regime_transition_research import (
    AUTHORITY, MonthlyPanel, PanelError, month_after, month_number,
)

SCHEMA = "cycle_pattern.macro_regime_analogs.v1"


@dataclass(frozen=True)
class AssetPanel:
    """Supplied price/return-index series; no guessed total-return convention.

    Values are observations selected at closed month ends by their data owner.
    A price-only input remains price-only. End-point returns do not establish
    intra-month maximum drawdown. Currency and adjustment receipts are required.
    """
    periods: tuple[str, ...]
    values: np.ndarray
    assets: tuple[str, ...]
    basis: tuple[str, ...]
    currency: tuple[str, ...]
    source_receipts: tuple[str, ...]

    def __post_init__(self):
        periods, assets = tuple(self.periods), tuple(self.assets)
        months = np.array([month_number(p) for p in periods])
        raw = np.asarray(self.values, dtype=object)
        if raw.ndim != 2 or any(isinstance(v, (bool, np.bool_)) for v in raw.ravel()):
            raise PanelError("Asset values must be a numeric matrix, not booleans")
        try:
            values = np.array(self.values, dtype=float, copy=True)
        except (ValueError, TypeError, OverflowError) as exc:
            raise PanelError("Invalid asset value") from exc
        if not periods or np.any(np.diff(months) <= 0):
            raise PanelError("Asset month identities must be ordered and unique")
        if not assets or len(set(assets)) != len(assets) or not all(isinstance(a, str) and a for a in assets):
            raise PanelError("Unique owner asset identities required")
        if values.shape != (len(periods), len(assets)) or np.isinf(values).any() or (values[np.isfinite(values)] <= 0).any():
            raise PanelError("Asset levels must be positive or explicitly missing")
        if len(self.basis) != len(assets) or len(self.currency) != len(assets):
            raise PanelError("Per-asset return convention and currency required")
        if any(b not in ("TOTAL_RETURN_INDEX", "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY", "PRICE_ONLY") for b in self.basis):
            raise PanelError("Unknown asset return basis")
        if not all(isinstance(c, str) and c for c in self.currency) or not self.source_receipts:
            raise PanelError("Currency and source receipts required")
        values.setflags(write=False)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "periods", periods)
        object.__setattr__(self, "assets", assets)
        object.__setattr__(self, "basis", tuple(self.basis))
        object.__setattr__(self, "currency", tuple(self.currency))
        object.__setattr__(self, "source_receipts", tuple(self.source_receipts))


def _training_metric(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit once on historical candidates, never future outcomes or the query."""
    center = np.array([np.nanmedian(c) if np.isfinite(c).any() else 0. for c in values.T])
    scale = np.array([1.4826 * np.nanmedian(np.abs(c - m)) if np.isfinite(c).any() else 1.
                      for c, m in zip(values.T, center)])
    scale = np.where(scale > 1e-9, scale, 1.)
    z = (values - center) / scale
    # Estimation-only bounded influence; raw observations and their differences
    # remain in the result. This does not alter the source or grade outcomes.
    z = np.clip(np.where(np.isfinite(z), z, 0.), -6., 6.)
    covariance = np.atleast_2d(np.cov(z, rowvar=False, ddof=1))
    diagonal = np.maximum(np.diag(covariance), 1e-6)
    covariance = .75 * covariance + .25 * np.diag(diagonal)
    covariance += np.eye(values.shape[1]) * 1e-6
    return center, scale, covariance


def _distance(query: np.ndarray, candidate: np.ndarray, center: np.ndarray,
              scale: np.ndarray, covariance: np.ndarray, minimum_coverage: float) -> tuple[float, float] | None:
    both = np.isfinite(query) & np.isfinite(candidate)
    coverage = float(both.mean())
    if coverage < minimum_coverage or not both.any():
        return None
    # Correlated rate/credit/growth transformations are not independent votes.
    # Shrunk covariance reduces redundancy; this is a similarity metric, NOT
    # a probability or evidence-independence certificate.
    difference = (query[both] - candidate[both]) / scale[both]
    covariance_subset = covariance[np.ix_(both, both)]
    quadratic = float(difference @ np.linalg.solve(covariance_subset, difference))
    return math.sqrt(max(0., quadratic) / int(both.sum())) + (1 - coverage), coverage


def _asset_outcomes(asset_panel: AssetPanel | None, origin: str, horizon: int) -> dict:
    if asset_panel is None:
        return {}
    index = {p: i for i, p in enumerate(asset_panel.periods)}
    requested = [month_after(origin, h) for h in range(horizon + 1)]
    positions = [index.get(p) for p in requested]
    if positions[0] is None or positions[-1] is None:
        return {}
    out = {}
    for j, asset in enumerate(asset_panel.assets):
        first, final = asset_panel.values[positions[0], j], asset_panel.values[positions[-1], j]
        if not np.isfinite(first) or not np.isfinite(final):
            continue
        ret = float((final / first - 1) * 100)
        drawdown = None
        if all(p is not None for p in positions):
            path = asset_panel.values[np.array(positions, dtype=int), j]
            if np.isfinite(path).all():
                drawdown = float(np.min(path / np.maximum.accumulate(path) - 1) * 100)
        out[asset] = {"change_pct": ret, "basis": asset_panel.basis[j],
                      "currency": asset_panel.currency[j], "excess_over_cash_pct": None,
                      "cash_comparator_status": "not_supplied_by_owner",
                      "worst_closed_month_drawdown_pct": drawdown,
                      "intramonth_maximum_drawdown_available": False}
    return out


def retrieve_macro_analogs(panel: MonthlyPanel, *, query_index: int | None = None,
                          horizons: tuple[int, ...] = (1, 3, 6, 12), k: int = 12,
                          minimum_coverage: float = .60, minimum_neighbors: int = 5,
                          asset_panel: AssetPanel | None = None,
                          canonical_episode_ids: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Outcome-blind historical retrieval, then outcomes of the fixed shortlist.

    A query and its future may not leak into metric fitting. Candidates must
    have a fully completed maximum-horizon calendar window before the query.
    Neighbour windows may not overlap. Distinct windows are NOT automatically
    independent economic episodes; those counts need the existing episode owner.
    """
    if query_index is None:
        query_index = len(panel.periods) - 1
    if isinstance(query_index, bool) or not isinstance(query_index, int) or not 0 <= query_index < len(panel.periods):
        raise PanelError("Invalid analogue query index")
    if not horizons or tuple(sorted(set(horizons))) != horizons or any(isinstance(h, bool) or not isinstance(h, int) or h < 1 or h > 120 for h in horizons):
        raise PanelError("Invalid analogue outcome horizons")
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in (k, minimum_neighbors)) or k > 100:
        raise PanelError("Invalid bounded neighbour count")
    if isinstance(minimum_coverage, bool) or not 0 < minimum_coverage <= 1:
        raise PanelError("Invalid analogue coverage requirement")
    query_period = panel.periods[query_index]
    query_month = month_number(query_period)
    max_horizon = max(horizons)
    lookup = {p: i for i, p in enumerate(panel.periods)}
    candidates = [i for i, p in enumerate(panel.periods[:query_index])
                  if month_number(p) + max_horizon <= query_month
                  and all(month_after(p, h) in lookup for h in range(max_horizon + 1))]
    result = {"schema": SCHEMA, "method": "prior_only_shrunk_mahalanobis_nonoverlap_v1",
              "query_period": query_period, "query_label": panel.labels[query_index],
              "source_basis": panel.source_basis, "panel_sha256": panel.through(query_index).fingerprint,
              "selection_uses_outcomes": False, "candidate_count": len(candidates),
              "selection_parameters": {"k": k, "minimum_coverage": minimum_coverage,
                                       "covariance_diagonal_shrinkage": .25, "missing_coverage_penalty": 1.,
                                       "minimum_neighbors": minimum_neighbors, "separation_months": max_horizon},
              "neighbors": [], "horizons": [], "independent_episode_count": None,
              "authority": dict(AUTHORITY), "status": "INSUFFICIENT_COMPARABLE_HISTORY",
              "limitations": ["Historical similarity does not establish causality or an issued forecast.",
                              "Latest-revised source data cannot certify historical real-time information.",
                              "Nonoverlapping windows are not independent crises.",
                              "Outcome distributions are descriptive selected-sample evidence, not calibrated predictions."]}
    if len(candidates) < max(3, minimum_neighbors):
        return result
    query = panel.values[query_index]
    x = panel.values[candidates]
    center, scale, covariance = _training_metric(x)
    ranked = []
    for i in candidates:
        measured = _distance(query, panel.values[i], center, scale, covariance, minimum_coverage)
        if measured is not None:
            distance, coverage = measured
            ranked.append((distance, panel.periods[i], i, coverage))
    ranked.sort(key=lambda row: (row[0], row[1]))
    selected, used_episodes = [], set()
    for distance, period, i, coverage in ranked:
        month = month_number(period)
        # Shared boundary is permissible; overlapping return intervals are not.
        if any(abs(month - month_number(p)) < max_horizon for _, p, _, _ in selected):
            continue
        episode = (canonical_episode_ids or {}).get(period)
        if episode is not None and episode in used_episodes:
            continue
        selected.append((distance, period, i, coverage))
        if episode is not None:
            used_episodes.add(episode)
        if len(selected) == k:
            break
    result["comparable_candidates"] = len(ranked)
    result["selected_window_count"] = len(selected)
    result["metric_training_through"] = panel.periods[max(candidates)]
    for distance, period, i, coverage in selected:
        differences = {name: (float(panel.values[i, j] - query[j])
                              if np.isfinite(panel.values[i, j]) and np.isfinite(query[j]) else None)
                       for j, name in enumerate(panel.feature_names)}
        result["neighbors"].append({"origin": period, "origin_label": panel.labels[i],
            "distance": float(distance), "feature_coverage": coverage,
            "canonical_episode_id": (canonical_episode_ids or {}).get(period),
            "differences_in_source_units": differences,
            "outcomes": {str(h): {"target_period": month_after(period, h),
                         "target_label": panel.labels[lookup[month_after(period, h)]],
                         "feature_changes": {name: (float(panel.values[lookup[month_after(period, h)], j] - panel.values[i, j])
                                                  if np.isfinite(panel.values[lookup[month_after(period, h)], j]) and np.isfinite(panel.values[i, j]) else None)
                                             for j, name in enumerate(panel.feature_names)},
                         "asset_changes": _asset_outcomes(asset_panel, period, h)} for h in horizons}})
    ids = [n["canonical_episode_id"] for n in result["neighbors"]]
    if ids and all(isinstance(i, str) and i for i in ids):
        result["independent_episode_count"] = len(set(ids))
        result["episode_count_basis"] = "distinct_existing_owner_ids_not_statistical_independence"
    if len(selected) < minimum_neighbors:
        return result
    result["status"] = "EXPLORATORY_HISTORICAL_COMPARISON"
    for h in horizons:
        outcomes = [n["outcomes"][str(h)] for n in result["neighbors"]]
        known_labels = [o["target_label"] for o in outcomes if o["target_label"] is not None]
        counts = {s: known_labels.count(s) for s in panel.states}
        assets = {}
        for asset in sorted(set(a for o in outcomes for a in o["asset_changes"])):
            cells = [o["asset_changes"][asset] for o in outcomes if asset in o["asset_changes"]]
            changes = np.array([c["change_pct"] for c in cells])
            assets[asset] = {"n": len(changes), "basis": cells[0]["basis"], "currency": cells[0]["currency"],
                "p10": float(np.quantile(changes, .1)), "median": float(np.median(changes)),
                "p90": float(np.quantile(changes, .9)), "negative_count": int((changes < 0).sum()),
                "excess_over_cash_available": False, "predictive_interval_claimed": False}
        # All divergent outcomes are retained from the SAME preselected cohort.
        unchanged = [n["origin"] for n in result["neighbors"]
                     if n["outcomes"][str(h)]["target_label"] == result["query_label"]]
        changed = [n["origin"] for n in result["neighbors"]
                   if n["outcomes"][str(h)]["target_label"] is not None and
                   n["outcomes"][str(h)]["target_label"] != result["query_label"]]
        result["horizons"].append({"horizon_months": h, "n_known_target_windows": len(known_labels),
            "state_counts": counts, "state_frequencies": {s: counts[s] / len(known_labels) if known_labels else None for s in panel.states},
            "frequency_is_forecast_probability": False, "assets": assets,
            "same_as_query_label_origins": unchanged, "different_from_query_label_origins": changed})
    return result
