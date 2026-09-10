"""Release Radar per-item diagnostics: display-only truth labels (A1, macro#6868).

Why this exists
---------------
The Release Radar cards and the ``latest.json`` machine artifact let distinct
facts pose as one another:

* feature AVAILABILITY (a leg is present) was painted as FRESHNESS; the
  producer's ``fresh_proxy_coverage`` is a present-leg approximation unless the
  PIT provenance records an explicit ``fresh_legs`` receipt;
* ``cutoff_label`` ("T-1"/"early") is a QUEUE POSITION -- the nearest upcoming
  release of a type is "T-1" even 35 days out -- yet it rendered as a data
  cutoff ("Data through T-1");
* the champion model's standardized attribution sat beside a blended primary
  it does not explain, and a null attribution (PPI) was synthesized from
  coverage flags into an attribution-shaped bar;
* ``confidence`` (a band-width rank x input completeness) read as a probability.

This module derives, per upcoming item, an additive ``diagnostics`` subtree
(schema ``release_forecast.item_diagnostics.v1``) that names each of those
facts separately and says, in a machine-readable ``status``/``reason``, when one
is unavailable.

Contract
--------
* PURE: :func:`build_item_diagnostics` reads its arguments and returns a NEW
  dict.  It never mutates the item, never reads the clock or the network, and
  performs no file IO -- the input-snapshot receipt is injected by the caller.
* ADDITIVE / DISPLAY-ONLY: the producer attaches the subtree after every ledger,
  scoring and scoreboard consumer has run.  No projection, interval, weight,
  score, ledger row or epoch reads it back, and it selects nothing: the primary
  forecast is the one the existing selection policy already chose.
* FAIL-EXPLICIT: nulls, NaN/inf, booleans, strings posing as numbers, reversed
  bands, absent manifests and mismatched identities become an explicit status
  and reason -- never a zero, never a silent omission.

Field semantics (derived from source, not from labels)
------------------------------------------------------
* Legacy ``confidence`` = ``interval_rank x input_completeness``
  (``engine/release_forecast.py``): the share of the champion's expanding-window
  residual band widths that are WIDER than its current width, scaled by input
  completeness.  A width comparison -- not a probability of being right.
* ``confidence_v2`` / ``confidence_components_v2`` (``engine/release_components_cpi``):
  ``c_raw = sum(|contrib_i| / sum|contrib|) x block_weight_i``.  ``w_known`` is the
  energy (direct price) share, ``w_proxy`` the shelter + pipeline (leading proxy)
  share, ``w_residual`` EXACTLY the core-persistence (lagged inflation) share.
  All-zero contributions make every share 0/0: an undefined denominator, not 0%.
* Champion ``components`` are standardized ridge contributions (beta x z) in
  percentage points, aggregated by block, EXCLUDING the intercept/baseline.  The
  baseline is never reported and must never be inferred as point - sum(parts).
* p10-p90 is a nominal 80% band and p25-p75 a nominal 50% band; neither has
  established calibration.
* Scored lanes grade the frozen day-before-release (T-1) projection only, keyed
  by exact model and target epochs (``scoreboard.by_shadow_epoch``).
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "release_forecast.item_diagnostics.v1"
DIAGNOSTICS_KEY = "diagnostics"

BLEND_BASIS = "combined_v1_benchmark_augmented"
QUANTILE_KEYS = ("p10", "p25", "p50", "p75", "p90")
# Nominal (target) coverage of each band.  Stated, never implied calibrated.
NOMINAL_COVERAGE = {"p10_p90": 0.8, "p25_p75": 0.5}

# Target code -> unit semantics.  Levels carry the target's unit; differences
# between two levels (and additive contributions) are percentage points.
UNITS: dict[str, dict[str, str]] = {
    "mom_sa_pct": {
        "level": "percent_mom_sa",
        "difference": "percentage_points",
    },
}

# Block -> provenance role.  Mirrors the frozen block confidence weights in
# engine.release_components_cpi (_BLOCK_CONFIDENCE_WEIGHT: 1.0 direct price,
# 0.6 proxy, 0.0 persistence); tests pin the two tables together.
BLOCK_ROLE: dict[str, str] = {
    "energy": "direct_price",
    "shelter": "leading_proxy",
    "pipeline": "leading_proxy",
    "core_persistence": "persistence",
}

# Only the CPI champion decomposition is documented as standardized ridge
# attribution excluding the intercept (engine/release_components_cpi.py).
STANDARDIZED_ATTRIBUTION_RELEASES = ("cpi_headline", "cpi_core")

# Releases the coherent-target ridge challenger serves; tests pin this against
# scripts/build_release_forecast._SHADOW_COHERENT_RIDGE_TARGETS.
COHERENT_TARGETS = ("cpi_headline", "cpi_core")

MARKET_SOURCES = ("kalshi", "polymarket")


# ---------------------------------------------------------------------------
# Value classification
# ---------------------------------------------------------------------------

def _num(value: Any) -> float | None:
    """A finite real number, else None.  ``bool`` is not a number here
    (``True - False == 1`` would draw a band), and neither is a string such as
    ``"0.2%"``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def _kind(value: Any) -> str:
    """``ok`` | ``missing`` | ``nonfinite`` | ``malformed``."""
    if value is None:
        return "missing"
    if isinstance(value, bool):
        return "malformed"
    if isinstance(value, (int, float)):
        return "ok" if math.isfinite(float(value)) else "nonfinite"
    return "malformed"


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _iso_date(value: Any) -> str | None:
    """Strict ``YYYY-MM-DD`` (date precision only: no time, no timezone)."""
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _mapping(value: Any) -> Mapping | None:
    return value if isinstance(value, Mapping) else None


def _str_list(value: Any) -> list[str] | None:
    """A list of non-empty strings, ``[]`` for an empty list, None if absent
    or malformed (callers distinguish with ``key in pit``)."""
    if not isinstance(value, list):
        return None
    if not all(isinstance(x, str) and x for x in value):
        return None
    return list(value)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def assess_bands(source: Mapping | None) -> dict:
    """Validate a quantile set without recentring or repairing it.

    The 80% band (p10-p90) and 50% band (p25-p75) are available only when both
    bounds are finite numbers, the lower bound is strictly below the upper, and
    every present finite quantile is non-decreasing p10 <= p25 <= p50 <= p75 <= p90.
    """
    src = source if isinstance(source, Mapping) else {}
    kinds = {k: _kind(src.get(k)) for k in QUANTILE_KEYS}
    vals = {k: _num(src.get(k)) for k in QUANTILE_KEYS}
    present = [vals[k] for k in QUANTILE_KEYS if vals[k] is not None]
    ordered = all(a <= b for a, b in zip(present, present[1:]))

    def band(lo: str, hi: str) -> dict:
        out: dict[str, Any] = {}
        for key in (lo, hi):
            if kinds[key] != "ok":
                out.update(status="unavailable",
                           reason="missing" if kinds[key] == "missing" else "invalid_value")
                return out
        if not ordered:
            out.update(status="unavailable", reason="quantiles_out_of_order")
        elif vals[lo] > vals[hi]:
            out.update(status="unavailable", reason="reversed")
        elif vals[lo] == vals[hi]:
            out.update(status="unavailable", reason="zero_width")
        else:
            out.update(status="available", reason=None)
        return out

    return {
        "band_80": band("p10", "p90"),
        "band_50": band("p25", "p75"),
        "median_p50": "available" if kinds["p50"] == "ok" and ordered else (
            "unavailable" if kinds["p50"] != "ok" else "out_of_order"),
    }


def uses_benchmark_augmented_primary(item: Mapping) -> bool:
    """Mirror of the renderer's ``_usesBenchmarkAugmentedPrimary`` -- the
    existing selection policy, preserved verbatim (presence, not validity)."""
    comb = _mapping(item.get("combined"))
    return bool(item.get("primary_forecast_basis") == BLEND_BASIS
                and comb is not None and comb.get("combined_point") is not None)


def context_metrics_match_primary(item: Mapping) -> bool:
    """Mirror of the renderer's ``_contextMetricsMatchPrimary``."""
    primary_basis = item.get("primary_forecast_basis")
    context_basis = item.get("context_metrics_basis")
    if not primary_basis:
        return True
    if not context_basis:
        return primary_basis != BLEND_BASIS
    return context_basis == primary_basis


def _primary(item: Mapping) -> dict:
    proj = _mapping(item.get("projection")) or {}
    if proj.get("mode") == "benchmark_only":
        return {"basis": "benchmark_only", "model": None,
                "status": "no_model_forecast", "calibration": "not_applicable"}
    if uses_benchmark_augmented_primary(item):
        comb = _mapping(item.get("combined")) or {}
        source: Mapping = {"point": comb.get("combined_point"),
                           **{k: comb.get(k) for k in QUANTILE_KEYS}}
        out: dict[str, Any] = {
            "basis": BLEND_BASIS,
            "model": "combined_v1",
            "model_epoch": _text(comb.get("model_epoch")),
            "target_epoch": _text(comb.get("target_epoch")),
            "values_from": "combined",
            "interval_kind": "combined_v1_blend_interval",
        }
    else:
        source = proj
        out = {
            "basis": "champion",
            "model": "champion",
            "model_epoch": _text(item.get("model_epoch")),
            "target_epoch": _text(item.get("target_epoch")),
            "values_from": "projection",
            "interval_kind": "legacy_walk_forward_residual_quantiles",
        }
    point_kind = _kind(source.get("point"))
    point = _num(source.get("point"))
    median = _num(source.get("p50"))
    bands = assess_bands(source)
    if point is None:
        relation = "point_unavailable"
    elif median is None or bands["median_p50"] != "available":
        relation = "median_unavailable"
    else:
        relation = "equal" if round(point, 6) == round(median, 6) else "differs"
    out.update(
        status="available" if point_kind == "ok" else "unavailable",
        point_reason=None if point_kind == "ok" else point_kind,
        point_vs_median=relation,
        band_80=bands["band_80"],
        band_50=bands["band_50"],
        nominal_coverage=dict(NOMINAL_COVERAGE),
        interval_status="experimental_uncalibrated",
        calibration="not_established",
        context_metrics_basis=_text(item.get("context_metrics_basis")),
        context_metrics_aligned=context_metrics_match_primary(item),
    )
    return out


def _unit(item: Mapping) -> dict:
    target = item.get("target")
    if isinstance(target, str) and target in UNITS:
        return {"status": "mapped", "target": target, **UNITS[target]}
    return {"status": "not_mapped", "target": _text(target)}


def _expected_prediction_id(item: Mapping, asof: str) -> str | None:
    release_type = _text(item.get("release_type"))
    period = _text(item.get("period"))
    if not release_type or not period:
        return None
    try:
        from engine.release_forecast import make_prediction_id, make_release_id
    except Exception:  # noqa: BLE001 - identity check degrades, never guesses
        return None
    return make_prediction_id(make_release_id(release_type, period), asof)


def _cutoff(item: Mapping, snapshot: Any) -> dict:
    legacy = item.get("cutoff_label")
    out: dict[str, Any] = {
        "legacy_label": legacy if isinstance(legacy, str) else None,
        "legacy_label_kind": "queue_position_not_a_data_cutoff",
        "precision": None,
        "inputs_asof": None,
    }
    ref = item.get("input_snapshot_ref")
    if not isinstance(ref, str) or not ref:
        return {**out, "status": "unavailable", "reason": "snapshot_ref_missing"}
    if snapshot is None:
        return {**out, "status": "unavailable", "reason": "snapshot_unreadable"}
    if not isinstance(snapshot, Mapping):
        return {**out, "status": "unavailable", "reason": "snapshot_malformed"}
    asof = _iso_date(snapshot.get("asof"))
    if asof is None:
        return {**out, "status": "unavailable", "reason": "snapshot_date_invalid"}
    if not _text(item.get("release_type")) or not _text(item.get("period")):
        return {**out, "status": "unavailable", "reason": "identity_incomplete"}
    expected = _expected_prediction_id(item, asof)
    if expected is None:
        return {**out, "status": "unavailable", "reason": "identity_check_unavailable"}
    if snapshot.get("prediction_id") != expected:
        return {**out, "status": "unavailable", "reason": "snapshot_identity_mismatch"}
    inputs_hash = _text(item.get("inputs_hash"))
    if inputs_hash is None:
        return {**out, "status": "unavailable", "reason": "inputs_hash_missing"}
    if snapshot.get("inputs_hash") != inputs_hash:
        return {**out, "status": "unavailable", "reason": "inputs_hash_mismatch"}
    return {**out, "status": "verified", "reason": None, "inputs_asof": asof,
            "precision": "date", "basis": "input_snapshot"}


def _inputs(item: Mapping) -> dict:
    pit = _mapping(item.get("pit"))
    manifest = _mapping(item.get("input_manifest"))
    economic = {"status": "not_measured"}
    if manifest is None:
        return {"status": "unavailable", "reason": "no_input_manifest",
                "freshness": {"status": "not_verified", "reason": "no_input_manifest"},
                "vintage": {"status": "not_recorded"}, "economic_coverage": economic}
    if pit is None:
        return {"status": "unavailable", "reason": "no_pit_provenance",
                "freshness": {"status": "not_verified", "reason": "no_pit_provenance"},
                "vintage": {"status": "not_recorded"}, "economic_coverage": economic}
    lists: dict[str, list[str] | None] = {}
    for key in ("vintaged_legs", "revision_optimistic_legs", "unrevised_legs",
                "absent_legs", "fresh_legs"):
        if key in pit:
            parsed = _str_list(pit.get(key))
            if parsed is None:
                return {"status": "malformed", "reason": f"{key}_not_a_list_of_names",
                        "freshness": {"status": "not_verified", "reason": "malformed_provenance"},
                        "vintage": {"status": "malformed"}, "economic_coverage": economic}
            lists[key] = parsed
        else:
            lists[key] = None
    declared = {k for k in manifest.keys() if isinstance(k, str) and k}
    for key in ("vintaged_legs", "revision_optimistic_legs", "unrevised_legs", "absent_legs"):
        declared.update(lists[key] or [])
    if not declared:
        return {"status": "unavailable", "reason": "no_declared_inputs",
                "freshness": {"status": "not_verified", "reason": "no_declared_inputs"},
                "vintage": {"status": "not_recorded"}, "economic_coverage": economic}
    absent = set(lists["absent_legs"] or []) & declared
    present = declared - absent
    rev_opt = set(lists["revision_optimistic_legs"] or []) & present
    unrev = set(lists["unrevised_legs"] or []) & present
    if lists["vintaged_legs"] is None:
        vintage: dict[str, Any] = {"status": "not_recorded",
                                   "revision_optimistic": len(rev_opt),
                                   "unrevised": len(unrev)}
    else:
        pit_legs = set(lists["vintaged_legs"]) & present
        vintage = {"status": "recorded", "point_in_time": len(pit_legs),
                   "revision_optimistic": len(rev_opt), "unrevised": len(unrev),
                   "unclassified": len(present - pit_legs - rev_opt - unrev)}
    if lists["fresh_legs"] is None:
        freshness: dict[str, Any] = {"status": "not_verified",
                                     "reason": "no_fresh_leg_receipt"}
    else:
        freshness = {"status": "verified", "fresh": len(set(lists["fresh_legs"]) & present),
                     "of_present": len(present)}
    return {"status": "available", "reason": None, "declared": len(declared),
            "present": len(present), "absent": len(absent), "vintage": vintage,
            "freshness": freshness, "economic_coverage": economic}


def _component_rows(components: Iterable[Any]) -> tuple[list[dict], bool]:
    rows: list[dict] = []
    malformed = False
    for comp in components:
        if not isinstance(comp, Mapping):
            malformed = True
            continue
        name = _text(comp.get("block")) or _text(comp.get("name"))
        raw = comp.get("contribution_pp") if "contribution_pp" in comp else comp.get("contrib_pp")
        kind = _kind(raw)
        if name is None or kind != "ok":
            malformed = True
        rows.append({"name": name, "role": BLOCK_ROLE.get(name or ""),
                     "value_status": kind})
        if kind == "ok":
            rows[-1]["value"] = float(raw)
    return rows, malformed


def _provenance_mix(item: Mapping) -> dict:
    cv = item.get("confidence_components_v2")
    if cv is None:
        return {"status": "not_recorded"}
    if not isinstance(cv, Mapping):
        return {"status": "malformed"}
    shares = {k: _num(cv.get(k)) for k in ("w_known", "w_proxy", "w_residual")}
    if any(v is None for v in shares.values()) or any(v < 0 for v in shares.values()):  # type: ignore[operator]
        return {"status": "malformed"}
    total = sum(shares.values())  # type: ignore[arg-type]
    if total == 0:
        return {"status": "undefined_denominator"}
    return {"status": "recorded",
            "direct_price_share": shares["w_known"],
            "leading_proxy_share": shares["w_proxy"],
            "persistence_share": shares["w_residual"]}


def _attribution(item: Mapping, primary: Mapping) -> dict:
    release_type = _text(item.get("release_type"))
    standardized = release_type in STANDARDIZED_ATTRIBUTION_RELEASES
    proj = _mapping(item.get("projection")) or {}
    out: dict[str, Any] = {
        "forecast_model": "champion",
        "forecast_model_epoch": _text(item.get("model_epoch")),
        "forecast_point_status": "available" if _kind(proj.get("point")) == "ok" else "unavailable",
        "applies_to_primary": primary.get("model") == "champion",
        "method": ("standardized_model_attribution_excluding_intercept"
                   if standardized else "not_documented"),
        "unit": "percentage_points",
        "baseline": "not_reported",
    }
    if primary.get("basis") == "benchmark_only":
        return {**out, "status": "not_applicable", "reason": "benchmark_only",
                "applies_to_primary": False, "blocks": [],
                "provenance_mix": {"status": "not_applicable"}}
    comps = item.get("components")
    if isinstance(comps, Mapping):
        notes = _mapping(comps.get("method_notes")) or {}
        return {**out, "status": "unavailable",
                "reason": _text(notes.get("reason")) or "not_recorded_as_rows",
                "blocks": [], "provenance_mix": _provenance_mix(item)}
    if not isinstance(comps, list) or not comps:
        return {**out, "status": "unavailable", "reason": "not_recorded",
                "blocks": [], "provenance_mix": _provenance_mix(item)}
    rows, malformed = _component_rows(comps)
    if malformed:
        status, reason = "malformed", "invalid_rows"
    elif all(r.get("value") == 0 for r in rows):
        status, reason = "undefined_denominator", "all_contributions_zero"
    else:
        status, reason = "available", None
    mix = _provenance_mix(item)
    if status == "undefined_denominator" and mix.get("status") == "recorded":
        mix = {"status": "malformed", "reason": "shares_recorded_for_zero_contributions"}
    return {**out, "status": status, "reason": reason,
            "blocks": [{k: v for k, v in r.items() if k != "value"} for r in rows],
            "provenance_mix": mix}


def _scores() -> dict:
    return {
        "confidence": {"name": "legacy_band_width_rank_x_input_completeness",
                       "model": "champion", "is_probability": False},
        "confidence_v2": {"name": "attribution_provenance_score",
                          "model": "champion", "is_probability": False},
        "calibration": "not_established",
    }


def _blend(item: Mapping) -> dict:
    comb = _mapping(item.get("combined"))
    if comb is None:
        return {"status": "not_recorded"}
    cc = _mapping(comb.get("combined_components"))
    is_primary = uses_benchmark_augmented_primary(item)
    if cc is None:
        return {"status": "malformed", "reason": "no_components", "is_primary": is_primary}
    inputs = _str_list(cc.get("inputs_used"))
    weights = _mapping(cc.get("weights"))
    points = _mapping(cc.get("points"))
    if not inputs or weights is None or points is None:
        return {"status": "malformed", "reason": "inputs_weights_or_points_missing",
                "is_primary": is_primary}
    w = [_num(weights.get(i)) for i in inputs]
    p = [_num(points.get(i)) for i in inputs]
    if any(v is None for v in w) or any(v is None for v in p):
        return {"status": "malformed", "reason": "nonfinite_weight_or_point",
                "is_primary": is_primary}
    n_i = _mapping(cc.get("n_i")) or {}
    counts = [_int(n_i.get(i)) for i in inputs]
    cold = cc.get("cold_start")
    return {
        "status": "recorded",
        "is_primary": is_primary,
        "n_inputs": len(inputs),
        "weights_sum": round(sum(w), 6),  # type: ignore[arg-type]
        "equal_weights": (max(w) - min(w)) <= 1e-9,  # type: ignore[type-var,operator]
        "cold_start": cold if isinstance(cold, bool) else None,
        "no_input_scored": (all(c == 0 for c in counts) if all(c is not None for c in counts)
                            else None),
        "decomposition": "recorded_weights_and_points_only",
    }


def _market(item: Mapping) -> dict:
    bench = _mapping(item.get("benchmark_set")) or {}
    raw_ref = "benchmark_set.market_implied"
    mi = bench.get("market_implied")
    if mi is None:
        mi, raw_ref = item.get("market_implied"), "market_implied"
    if mi is None:
        return {"status": "absent"}
    if not isinstance(mi, Mapping):
        return {"status": "malformed", "raw_ref": raw_ref}
    out = {"source": _text(mi.get("source")), "raw_ref": raw_ref}
    period, target = mi.get("period"), mi.get("target")
    if period is None and target is None:
        return {**out, "status": "unverified_identity",
                "reason": "no_structured_target_period_or_unit"}
    if period != item.get("period"):
        return {**out, "status": "incompatible", "reason": "period_mismatch"}
    if target != item.get("target"):
        return {**out, "status": "incompatible", "reason": "target_mismatch"}
    if _num(mi.get("implied_median")) is None:
        return {**out, "status": "unverified_value", "reason": "no_numeric_value"}
    return {**out, "status": "verified", "reason": None}


def _coherent(item: Mapping) -> dict | None:
    release_type = _text(item.get("release_type"))
    if release_type not in COHERENT_TARGETS:
        return None
    shadows = _mapping(item.get("shadows")) or {}
    co = shadows.get("coherent_ridge_v1")
    if co is not None:
        if not isinstance(co, Mapping):
            return {"status": "malformed"}
        for key in ("release", "period", "release_date"):
            mine = release_type if key == "release" else item.get(key)
            if co.get(key) != mine:
                return {"status": "identity_mismatch", "reason": f"{key}_mismatch"}
        if _num(co.get("point")) is None:
            return {"status": "unavailable", "reason": "point_invalid"}
        bands = assess_bands(co)
        return {"status": "projected", "display_only": True,
                "model_epoch": _text(co.get("model_epoch")),
                "target_epoch": _text(co.get("target_epoch")),
                "band_80": bands["band_80"], "band_50": bands["band_50"]}
    days_to = _int(item.get("days_to"))
    if days_to is None:
        return {"status": "unavailable", "reason": "horizon_unknown"}
    if days_to != 1:
        return {"status": "not_scheduled_at_horizon", "days_to_release": days_to,
                "rule": "decision_asof_must_equal_release_date_minus_one_day"}
    return {"status": "withheld", "reason": "not_projected_at_its_scheduled_horizon"}


def _performance(item: Mapping, primary: Mapping, scoreboard: Any) -> dict:
    if primary.get("basis") == "benchmark_only":
        return {"status": "not_applicable", "reason": "benchmark_only"}
    if not isinstance(scoreboard, Mapping):
        return {"status": "unavailable", "reason": "scoreboard_unavailable"}
    scored_horizon = "t_minus_1_frozen_projection"
    days_to = _int(item.get("days_to"))
    if days_to != 1:
        return {"status": "unavailable", "reason": "horizon_not_scored",
                "scored_horizon": scored_horizon}
    model = primary.get("model")
    if model == "champion":
        return {"status": "unavailable", "reason": "no_exact_epoch_lane_for_champion",
                "scored_horizon": scored_horizon}
    release_type = _text(item.get("release_type"))
    lane = f"{release_type}:{model}:{primary.get('model_epoch')}:{primary.get('target_epoch')}"
    lanes = _mapping(scoreboard.get("by_shadow_epoch")) or {}
    entry = _mapping(lanes.get(lane))
    at_horizon = _mapping((_mapping(entry.get("by_cutoff")) or {}).get("T-1")) if entry else None
    n = _int(at_horizon.get("n")) if at_horizon else None
    mae = _num(at_horizon.get("mae_ours")) if at_horizon else None
    if not n or mae is None:
        return {"status": "unavailable", "reason": "no_scored_releases_in_exact_lane",
                "lane": lane, "scored_horizon": scored_horizon}
    return {"status": "available", "lane": lane, "scored_horizon": scored_horizon,
            "n": n, "mae_pp": mae,
            "evaluation_basis": _text(scoreboard.get("evaluation_basis"))}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_item_diagnostics(
    item: Mapping,
    *,
    scoreboard: Mapping | None = None,
    snapshot: Mapping | None = None,
) -> dict:
    """Return the diagnostics subtree for one upcoming item (pure; no IO)."""
    primary = _primary(item)
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "display_only": True,
        "authority": False,
        "primary": primary,
        "unit": _unit(item),
        "cutoff": _cutoff(item, snapshot),
        "inputs": _inputs(item),
        "attribution": _attribution(item, primary),
        "scores": _scores(),
        "blend": _blend(item),
        "benchmarks": {
            "street_consensus": {"status": "unavailable",
                                 "reason": "no_street_consensus_source_collected"},
            "market_implied": _market(item),
        },
        "performance": _performance(item, primary, scoreboard),
    }
    coherent = _coherent(item)
    if coherent is not None:
        out["challengers"] = {"coherent_ridge_v1": coherent}
    return out


def snapshot_loader(root: Any) -> Callable[[str], Mapping | None]:
    """IO seam for the producer: read an input snapshot named by an item's
    ``input_snapshot_ref``, confined to ``<root>/data/release_forecast/
    input_snapshots/``.  Anything unreadable, outside that directory or not a
    JSON object reads as None (-> cutoff ``unavailable``)."""
    import json
    from pathlib import Path

    base = (Path(root) / "data" / "release_forecast" / "input_snapshots").resolve()

    def load(ref: str) -> Mapping | None:
        try:
            path = (Path(root) / ref).resolve()
            if path.parent != base or path.suffix != ".json":
                return None
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001 - an unreadable receipt is "unavailable"
            return None
        return data if isinstance(data, Mapping) else None

    return load


def attach_release_diagnostics(
    upcoming: list,
    *,
    scoreboard: Mapping | None = None,
    load_snapshot: Callable[[str], Mapping | None] | None = None,
) -> int:
    """Attach ``item["diagnostics"]`` to every dict item; return how many.

    The ONE producer call.  It adds a single namespaced key per item and touches
    nothing else; a failure on one item records an explicit error status for
    that item (and an Actions annotation) instead of breaking the nightly.
    """
    attached = 0
    for item in upcoming or []:
        if not isinstance(item, dict):
            continue
        ref = item.get("input_snapshot_ref")
        snapshot = None
        if load_snapshot is not None and isinstance(ref, str) and ref:
            try:
                snapshot = load_snapshot(ref)
            except Exception:  # noqa: BLE001
                snapshot = None
        try:
            item[DIAGNOSTICS_KEY] = build_item_diagnostics(
                item, scoreboard=scoreboard, snapshot=snapshot)
        except Exception as exc:  # noqa: BLE001 - display-only lane fails explicit
            print(
                "::warning title=release-diagnostics::"
                f"{item.get('release_type')}/{item.get('period')} diagnostics failed: "
                f"{type(exc).__name__}",
                flush=True,
            )
            item[DIAGNOSTICS_KEY] = {"schema": SCHEMA, "display_only": True,
                                     "authority": False, "status": "error"}
        attached += 1
    return attached
