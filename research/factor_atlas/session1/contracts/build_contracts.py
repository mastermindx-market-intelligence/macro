"""Generate the candidate research contracts, not a native owner schema."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
instant = {"type": "string", "format": "date-time", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"}
ref = {"type": "string", "minLength": 3, "maxLength": 2048,
       "description": "Existing owner-qualified reference; syntax alone does not authenticate it."}
refs = {"type": "array", "items": ref, "uniqueItems": True}
sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
nullable_instant = {"anyOf": [instant, {"type": "null"}]}
nullable_ref = {"anyOf": [ref, {"type": "null"}]}
ratio = {"type": ["number", "null"], "minimum": 0, "maximum": 1}

def obj(properties, required=None, **kwargs):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties) if required is None else required, **kwargs}

window = obj({"start": nullable_instant, "end": nullable_instant,
              "reference_sessions": {"type": ["integer", "null"], "minimum": 0},
              "alignment": {"enum": ["EXACT", "CALENDAR_PRECEDING_SESSION", "NOT_APPLICABLE"]}})
coverage = obj({"eligible_count": {"type": ["integer", "null"], "minimum": 0},
                "observed_count": {"type": ["integer", "null"], "minimum": 0},
                "count_fraction": ratio, "weight_fraction": ratio})
metric = obj({
    "value": {"type": ["number", "null"]},
    "unit": {"enum": ["return_fraction", "fraction", "index_level", "effective_count", "count",
                       "annualized_return_fraction", "return_difference_fraction", "log_return_per_session", "sessions", "calendar_days"]},
    "status": {"enum": ["READY", "PARTIAL", "UNAVAILABLE"]},
    "reasons": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
    "n_observations": {"type": "integer", "minimum": 0},
    "requested_window": {"$ref": "#/$defs/window"},
    "actual_window": {"$ref": "#/$defs/window"},
    "coverage": {"$ref": "#/$defs/coverage"},
    "method_ref": ref, "source_refs": refs,
}, allOf=[
    {"if": {"properties": {"status": {"const": "UNAVAILABLE"}}, "required": ["status"]},
     "then": {"properties": {"value": {"type": "null"}, "reasons": {"minItems": 1}}},
     "else": {"properties": {"value": {"type": "number"}, "source_refs": {"minItems": 1}}}},
    {"if": {"properties": {"status": {"const": "PARTIAL"}}, "required": ["status"]},
     "then": {"properties": {"reasons": {"minItems": 1}}}}
])
point = obj({"interval_start": instant, "interval_end": instant,
             "selection_cutoff": nullable_instant, "membership_revision_ref": nullable_ref,
             "return": {"allOf": [{"$ref": "#/$defs/metric"}, {"properties": {"unit": {"const": "return_fraction"}, "value": {"minimum": -1}}}]},
             "index_level": {"allOf": [{"$ref": "#/$defs/metric"}, {"properties": {"unit": {"const": "index_level"}, "value": {"minimum": 0}}}]}})
receipt_groups = obj({k: refs for k in ["membership", "identity", "prices", "actions", "rights", "calendar"]})
authority = obj({k: {"const": False} for k in ["may_rank", "may_gate", "may_size", "may_escalate", "may_write_portfolio", "may_write_theme_state"]})
schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:mastermind:research:factor-atlas:read-model:v0",
    "title": "Factor Atlas read model v0 — proposed research contract",
    "description": "NOT an accepted native interface or authority record. Validation proves shape only; owner receipt authenticity, temporal meaning, rights and actual consumer compatibility require separate gates. Nonfinite numbers must be rejected by strict JSON decoding/encoding.",
    **obj({
        "schema": {"const": "factor_atlas_read.v0"}, "contract_status": {"const": "PROPOSED"},
        "status": {"enum": ["READY", "PARTIAL", "UNAVAILABLE", "SEMANTIC_ONLY", "RETIRED"]},
        "reasons": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
        "descriptor": obj({"semantic_ref": ref, "cohort_ref": nullable_ref,
                           "factor_class": {"enum": ["economic_theme", "house_basket", "microtheme", "gics_group", "quantitative_style", "etf_proxy", "screened_cohort", "relative_value_spread", "leveraged_inverse_product", "user_snapshot", "academic_factor"]},
                           "relationship": {"enum": ["DIRECT", "PROXY", "ECONOMIC_EXPOSURE", "SEMANTIC_ONLY"]}}),
        "request": obj({"history_mode": {"enum": ["CURRENT_ROSTER", "PIT_AS_KNOWN", "PIT_LATEST_CORRECTED"]},
                        "window": {"$ref": "#/$defs/window"}, "measurement_cutoff": instant,
                        "current_roster_snapshot_ref": nullable_ref}),
        "series_spec": obj({"method_ref": ref, "measurement_kind": {"enum": ["portfolio_index", "instrument_return", "aggregate_snapshot", "academic_spread", "economic_observation"]},
                            "return_kind": {"enum": ["PRICE", "TOTAL", "GROSS_UNFUNDED_SPREAD", "NOT_APPLICABLE"]},
                            "price_basis": {"enum": ["raw", "sadj", "tradj", None]},
                            "currency": {"type": ["string", "null"], "pattern": "^[A-Z]{3}$"},
                            "calendar_ref": nullable_ref, "session_ref": nullable_ref, "venue_ref": nullable_ref,
                            "weighting": {"enum": ["equal", "market_cap", "float", "inverse_volatility", "explicit", "provider_defined", "none"]},
                            "rebalance": {"enum": ["monthly", "daily", "event", "none", "provider_defined"]},
                            "between_rebalances": {"enum": ["drift", "constant_target", "provider_defined", "not_applicable"]},
                            "dividend_reinvestment": {"enum": ["constituent_total_return", "index_level_reinvestment", "none", "provider_defined"]},
                            "costs_ref": nullable_ref, "gross_leverage": {"type": ["number", "null"], "minimum": 0},
                            "base_level": {"type": ["number", "null"], "exclusiveMinimum": 0}}),
        "owner_receipt_refs": {"$ref": "#/$defs/receipt_groups"},
        "calculation": obj({"input_manifest_sha256": sha, "result_core_sha256": sha,
                            "code_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                            "dependency_lock_sha256": sha, "metrics_policy_ref": ref,
                            "revision_ref": ref, "supersedes_ref": nullable_ref, "correction_reason": {"type": ["string", "null"]},
                            "materialized_at": instant}),
        "observations": {"type": "array", "maxItems": 10000, "items": {"$ref": "#/$defs/point"}},
        "metrics": {"type": "object", "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,79}$"}, "additionalProperties": {"$ref": "#/$defs/metric"}},
        "authority": {"$ref": "#/$defs/authority"}
    }),
    "$defs": {"window": window, "coverage": coverage, "metric": metric,
              "point": point, "receipt_groups": receipt_groups, "authority": authority},
    "allOf": [
        {"if": {"properties": {"status": {"enum": ["UNAVAILABLE", "SEMANTIC_ONLY", "RETIRED"]}}, "required": ["status"]},
         "then": {"properties": {"reasons": {"minItems": 1}, "observations": {"maxItems": 0},
                                  "metrics": {"additionalProperties": {"allOf": [{"$ref": "#/$defs/metric"}, {"properties": {"status": {"const": "UNAVAILABLE"}}}]}}}}},
        {"if": {"properties": {"status": {"const": "SEMANTIC_ONLY"}}, "required": ["status"]},
         "then": {"properties": {"descriptor": {"properties": {"cohort_ref": {"type": "null"}, "relationship": {"const": "SEMANTIC_ONLY"}}}}}},
        {"if": {"properties": {"status": {"const": "PARTIAL"}}, "required": ["status"]},
         "then": {"properties": {"reasons": {"minItems": 1}}}},
        {"if": {"properties": {"status": {"enum": ["READY", "PARTIAL"]}}, "required": ["status"]},
         "then": {"properties": {"owner_receipt_refs": {"properties": {k: {"minItems": 1} for k in ["identity", "rights", "calendar"]}}}}},
        {"if": {"properties": {"request": {"properties": {"history_mode": {"const": "CURRENT_ROSTER"}}},
                               "status": {"enum": ["READY", "PARTIAL"]}}, "required": ["request", "status"]},
         "then": {"properties": {"request": {"properties": {"current_roster_snapshot_ref": {"type": "string", "minLength": 3}}}}}}
    ]
}
policy = {
    "schema": "factor_atlas_metrics_policy.v0", "status": "PROPOSED_NOT_EMPIRICALLY_OPTIMIZED",
    "purpose": "Descriptive measurement admission, never ranking or investment permission",
    "units": {"returns": "fraction", "display_percent_multiplier": 100,
              "return_difference": "fraction; display multiplied by 100 and labeled percentage points"},
    "daily_pilot": {"currency": "USD", "frequency": "daily", "session": "owner-qualified completed regular session",
                    "annualization_sessions": 252, "base_level": 100,
                    "missing_held_weight_rule": "any unvalued positive held weight withholds portfolio return",
                    "minimum_weight_coverage": 1.0, "weight_sum_tolerance": 1e-12,
                    "rebalance": "monthly; owner-qualified exchange calendar and decision/execution clocks",
                    "between_rebalances": "drift", "net_costed_returns_supported": False},
    "returns": {"session_windows": [5, 10, 20, 60], "minimum_valid_returns": "exactly h adjacent returns",
                "calendar_windows": ["1W", "1M", "3M", "6M", "MTD", "YTD", "1Y"],
                "anchor": "preceding eligible exchange close; requested and actual instants retained",
                "missing_anchor": "unavailable; never slide to first later observation"},
    "breadth": {"kind": "advance", "minimum_eligible": 3, "minimum_count_coverage": 0.8,
                "minimum_weight_coverage": 0.8, "small_n_flag_below": 10, "partial_status_required": True,
                "missing_values": "excluded only from observed denominator; missing count and weight disclosed"},
    "concentration": {"complete_weights_required": True, "hhi": "sum(w_i**2)",
                      "effective_number": "1/hhi", "top_k": [1, 5, 10],
                      "issuer_mapping_incomplete": "issuer measure null; security measure may remain qualified"},
    "volatility": {"minimum_daily_observations": 60, "short_window_descriptive_observations": 20,
                   "ddof": 1, "missing_interval": "unavailable; no compressed-window substitution"},
    "downside_deviation": {"target_daily_return": 0.0, "denominator": "all valid returns", "annualize": True},
    "return_abnormality": {"target_prior_observations": 252, "minimum_prior_observations": 60,
                           "current_in_baseline": False, "ddof": 1,
                           "zero_variance": "unavailable", "percentile": "midrank ties"},
    "volume_abnormality": {"minimum_prior_sessions": 20, "intraday_same_time_only": True,
                           "half_days_separate": True, "no_volume_source": "unavailable"},
    "tail_loss": {"quantile_method": "linear/type7 for displayed quantile",
                  "es_method": "mean loss of exactly p*n lower-tail mass; fractional boundary observation",
                  "p05_minimum_daily_observations": 252, "p01_minimum_daily_observations": 1260,
                  "minimum_lower_tail_observation_mass": 12, "predictive_probability": False},
    "correlation": {"minimum_common_intervals": 60, "minimum_window_coverage": 0.8,
                    "matrix_default": "one common complete-case sample", "constant_series": "unavailable",
                    "pairwise_deletion_requires_cell_samples": True},
    "beta": {"default_estimation_sessions": 252, "minimum_common_intervals": 126,
             "minimum_window_coverage": 0.8, "out_of_sample_coefficient_cutoff": "strictly before return interval",
             "singular_design": "unavailable", "joint_market_sector_model_required": True},
    "seasonality": {"monthly_exploratory_minimum_per_month": 3, "monthly_descriptive_minimum_per_month": 10,
                    "weekday_minimum_observations": 30, "unfinished_month": "separate partial cell",
                    "event_minimum_distinct_events": 30, "event_minimum_issuers": 10,
                    "multiple_testing_and_dependence_disclosed": True},
    "valuation": {"minimum_valid_weight": 0.8, "negative_and_missing_denominators_separate": True,
                  "default": "declared aggregate earnings yield, not mean P/E"},
    "rounding": {"calculation": "unrounded binary64 with pinned implementation and math.fsum for reductions",
                 "serialization": "finite strict JSON; result core excludes run timestamp",
                 "cross_implementation_relative_tolerance": 1e-12,
                 "warning": "tolerance is a fixture conformance rule, not permission to hide source discrepancies"}
}
for name, value in [("factor_read_model.v0.schema.json", schema), ("metrics_policy.v0.json", policy)]:
    (ROOT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
print("Generated two proposed contracts.")
