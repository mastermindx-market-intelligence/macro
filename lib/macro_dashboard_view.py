"""Public native Macro view, projected from the incumbent dashboard build.

No engines, network, clock, scoring, or private Prophet state. The allowlists are
the display contract; adding a VM field never implicitly publishes it. The old
page and the native consumer receive the same settled observations.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.numeric import finite_json_value

SCHEMA = "mastermind.macro_dashboard.v1"
MAX_BYTES = 1024 * 1024


def fields(names: str) -> dict:
    return dict.fromkeys(names.split())


PAIR = fields("en zh")
CLOCK = fields("asof as_of built produced_at source_event_time stale_after")
FRESHNESS = {
    **fields("data_asof expected_asof stale qualified any_input_stale worst_input_age_days max_stale_days"),
    "reasons": [None], "stale_inputs": [None], "owner": fields("stale"),
}
METRIC = fields("k_en k_zh v")
FACTOR = {**fields("key label_en label_zh score weight tone arrow read_en read_zh degraded"), "metrics": [METRIC]}
CAP = fields("key name source ceiling score reason reason_en reason_zh label_en label_zh binding")
SCARE = {
    **fields("scare label_en label_zh tier score band display_score display_band reading_state partial_composition n_legs_registered n_legs_resolved weight_coverage"),
    "firing_legs": [fields("leg pctile confirmed lead_d era_robust accruing")],
}
RADAR = {
    **fields("state state_zh top_score label_en label_zh do_en do_zh dd5 dd10 dd21 dd_lift is_warning is_loud can_force binding ceiling partial_composition reading_state"),
    "scares": [SCARE], "amp_unavailable": [None],
    "dd_base": fields("h5 h10 h21"),
    "dd_evidence": {
        **fields("schema evidence_class precision_grade source"), "limitations": [None],
        "window": fields("from through"), "target": fields("threshold_pct direction"),
        "horizons": {key: {**fields("matched displayed_probability n events observed_rate thin from through"), "observed_rate_ci90": [None]} for key in ("h5", "h10", "h21")},
    },
    "authority": fields("tier can_force binding can_size can_trade display_only reason note_en note_zh"),
    "counterread": fields("en zh label_en label_zh read_en read_zh"),
}
STATE = {
    **CLOCK, **fields("schema market score raw_score score_source capped score_ceiling score_gap verdict color label_en label_zh posture_en posture_zh headline_en headline_zh flip_en flip_zh caveat_en caveat_zh stale realtime is_display_only"),
    "components": [FACTOR], "score_caps": [CAP], "overrides": [CAP],
    "freshness": FRESHNESS, "radar": RADAR,
    "mtf": {"indices": [{**fields("ticker label_en label_zh confluence_en confluence_zh tone"),
        "cells": {key: fields("sign arrow tone rsi macd_pos") for key in ("D", "3D", "W", "M")}}]},
}
ENVELOPE = {
    **CLOCK, **fields("schema definition_id market revision bundle_id source_session observed_at data_state"),
    "authority": fields("envelope_may_execute envelope_may_gate envelope_may_rank envelope_may_size policy_actions_require_individual_authority"),
    "measured_state": fields("as_of role score verdict usable source_artifact"),
    "hazard_summary": {**fields("stage stage_reason active_episode_count display_only"), "unmapped_required_sources": [None], "unreadable_sources": [None]},
    "policy_summary": {**fields("posture policy_count basis display_only"), "active_policy_ids": [None]},
    "coverage": {"fresh": [None], "missing": [None], "stale": [None], "required": [None], "optional": [None], "source_count": None},
    "coherence": {**fields("state contradiction_count display_only"), "contradictions": [fields("key kind message en zh reason")]},
    "freshness": {**fields("all_on_session source_session"), "off_session_sources": [None],
        "per_source": {"*": fields("as_of matches_session state")}},
}
LIVE = {
    **CLOCK, **fields("schema live_active nightly_asof source_basis cause_basis stale realtime"),
    "nightly": STATE, "live": STATE, "display": {**STATE, "pending": fields("verdict score since reason")},
    "freshness": FRESHNESS, "risk_envelope": ENVELOPE,
}
EVENT = fields("date type label label_zh name name_zh title title_zh time_et impact source is_context_only days_to dow md md_zh note note_zh opex_risk_level opex_glance opex_glance_zh")
RATES = {
    **CLOCK, **fields("schema display_only authority"), "stance": PAIR,
    "expectations_pressure": {**fields("net_state hawk_score ease_score"), "state_label": PAIR,
        "legs": [fields("key active weight value detail_en detail_zh null_reason")]},
    "conditions": [fields("key direction en zh watch_en watch_zh")],
    "changes": {"vs_asof": None, "items": [fields("key from to en zh label_en label_zh")]},
    "divergence": [fields("key active value_bp detail_en detail_zh")],
    "qualified_comparisons": [{**fields("comparison_id difference status unit rule_id rule_version transform reason reference_only left_ref right_ref left_cutoff right_cutoff cutoff component"),
        "range": [None], "assumptions": [None], "limitations": [None]}],
    "caveats": [None],
}
THEME = fields("id name name_zh heat label score rank rank_delta_5d")
SENTIMENT_LEG = fields("key name_en name_zh value z pct pct_hist freshness obs_count orientation unit last_date null_reason reason")
SENTIMENT = {
    **fields("dial label_en label_zh n_legs_qualifying as_of generated_utc disclaimer_en disclaimer_zh"),
    "legs_included": [SENTIMENT_LEG], "legs_excluded_young": [SENTIMENT_LEG], "young_tiles": [SENTIMENT_LEG],
}
POLICY = {
    **fields("schema as_of state framing framing_zh"),
    "jawboning": fields("n_7d n_30d last_alert_ts last_alert_summary last_alert_summary_zh"),
    "levers": [{**fields("name name_zh asset watch watch_zh copy_as_of copy_age_days copy_stale"),
        "arming": fields("state label label_zh active armed")}],
}
BRIEF_TEXT = {**fields("summary regime_read rotation_check forward_read"), **{key: [None] for key in ("tldr", "conflicts", "transmission", "watch_items")}}
BRIEF = {**BRIEF_TEXT, **fields("state_asof generated_at generated_utc confidence degraded_reason"), "zh": BRIEF_TEXT,
    "key_facts": [fields("key label_en label_zh value_en value_zh tone")],
    "forward_watch": [fields("date label label_zh kind note note_zh")],
    "_freshness": fields("stale age_days generated_date refresh_days reason")}
NEWS_LEG = fields("n degraded_reason")
PUBLICATION = {
    **EVENT, **fields("event_id status data_ready detected_at verified_at source_released_at source_time_basis reference_period source_url source_sha256 content_sha256 note"),
    "actual": fields("headline_en headline_zh summary_en summary_zh source_url"),
}
RELEASE_FEED = {
    **fields("schema built as_of_et timezone is_context_only canonical_reconciliation"),
    "events": [PUBLICATION], "publications": [PUBLICATION],
}

# Release Radar has its own publisher and clock. This projection never upgrades
# its experimental models, withdrawn claims or excluded history into authority.
FORECAST_AUTHORITY = fields("can_score can_size can_trade")
FORECAST_BANDS = fields("point p10 p25 p50 p75 p90 mode reason")
FORECAST_COMPONENT = {**fields("name block contrib_pp contribution_pp mom_est weight confidence prior_only degraded legs_used legs_expected"), "missing_legs": [None]}
FORECAST_MARKET = fields("source event_key event_title event_ticker implied_median implied prob_top p_above_lowest_strike n_brackets asof")
FORECAST_WITHDRAWN = fields("verdict task target mae_ratio_vs_declared_baseline trial_family receipt receipt_sha256 protocol_sha256 note")
FORECAST_SHADOW = {
    **FORECAST_BANDS, **fields("schema model release period release_date asof display_only authority status warning model_epoch target_epoch promotion_authorized inputs_hash code_receipt prior_driven_share coverage_residual_pp weight_coverage confidence input_completeness weight_basis weight_basis_warning"),
    "claim_withdrawn": FORECAST_WITHDRAWN, "components": [FORECAST_COMPONENT],
    "degraded_blocks": [None], "known_scope_mismatches": [fields("block official_label warning")],
    **{key: fields("ref path sha256 schema status model_id release period decision_asof decision_cutoff model_epoch target_epoch source_sha256 receipt_sha256 content_sha256 input_manifest_sha256 training_receipt_sha256 point_raw") for key in ("input_manifest", "model_receipt", "truth_receipt", "training_receipt", "interval_receipt", "pit_provenance")},
    "mf_energy_components": {"*": None},
}
FORECAST_ITEM = {
    **fields("release release_type period release_date target cutoff_label primary_forecast_basis context_metrics_basis basis_warning confidence confidence_v2 input_completeness inputs_hash input_snapshot_ref model_epoch target_epoch code_receipt regime_axis print_integrity_regime"),
    "projection": FORECAST_BANDS,
    "benchmark_set": {**fields("naive_prior trailing_3m trailing_4w ar_model cleveland_nowcast expanding_mean"), "market_implied": FORECAST_MARKET},
    "combined": {**FORECAST_BANDS, **fields("combined_point n_scored_basis inputs_hash model_epoch target_epoch code_receipt display_only authority"),
        "combined_components": {**fields("MAE_pool sigma_champion Var_w sigma_combined cold_start k"), "inputs_used": [None],
            **{key: {"*": None} for key in ("points", "weights", "n_i", "MAE_shrunk_i", "input_hashes")}}},
    "shadows": {key: FORECAST_SHADOW for key in ("v3_factor", "cpi_bridge", "mf_energy", "coherent_ridge_v1")},
    "components": [FORECAST_COMPONENT], "input_manifest": {"*": None},
    "pit": {**fields("display_only authority n_train n_features_used reason note"),
        **{key: [None] for key in ("revision_optimistic_legs", "vintaged_legs", "unrevised_legs", "absent_legs")}},
    "confidence_components_v2": fields("w_known w_proxy w_residual c_raw input_completeness"),
    "coverage_flags": fields("weight_coverage fresh_proxy_coverage non_vintaged_share model_maturity"),
    "surprise_skew": fields("sigma sigma_scale_pp tag inline_band"),
    "surprise_distribution": fields("p_hot p_cold p_inline"),
    "expectation_read": {**fields("tag delta_pp standardized expectation_median n_sources"), "sources": [None]},
    "market_implied": FORECAST_MARKET,
    # Legacy gap/cut numbers have no comparability receipt; the rates owner
    # remains the only source for qualified numerical policy comparisons.
    "policy_backdrop": fields("fed_stance next_fomc guidance_direction"),
    "reaction_sensitivity": fields("dgs10_h1_hot_bp dgs10_h1_cold_bp spy_h1_hot_pct spy_h1_cold_pct era_basis regime_cells_used note"),
    "quirk_flags": [fields("code en zh cite")],
    "print_integrity": {**fields("regime collection_rate_vs_5y cpi_median_se_trend revision_streak as_of display_only authority"), "source_years": [None]},
    "revision_risk": fields("mean_k pct_upward n_periods"),
    "revision_context": {**fields("display_only authority"),
        "model_status": fields("track_r lean_display note"),
        "level_bias_annotation": fields("expansion_mean_cumulative_revision_k contraction_mean_cumulative_revision_k note display_only authority source")},
    "event_window_ctx": {**fields("is_context_only phase phase_read_en phase_read_zh"), "active_collisions": [None],
        "ex_ante": fields("available glance_en glance_zh disclaimer_en disclaimer_zh")},
}
FORECAST_TRACK = {
    **fields("release model clean_n first_print_matched_n proxy_scored_n other_basis_n display_state mae_ours mae_naive_prior early benchmark_only"),
    "mae_ours_ci": [None], "target_epochs": [None],
}
FORECAST_SCORED = {
    **fields("schema row_type model release release_type period release_date target prediction_id actual actual_first raw_initial_print actual_source exact_target_id asof_night point error abs_error covered_80 covered_50 actual_basis actual_source_url actual_source_sha256 actual_observed_at actual_receipt_id frozen_asof_night frozen_prediction_id score_receipt_id model_epoch target_epoch frozen_projection_point frozen_projection_p10 frozen_projection_p25 frozen_projection_p50 frozen_projection_p75 frozen_projection_p90 our_surprise surprise_vs_naive surprise_vs_trailing surprise_vs_ar surprise_vs_cleveland interval_hit skew_hit projection_mode benchmark_trailing_key expectation_hit cutoff_label code_receipt"),
    "supersedes_score_receipt_ids": [None],
    "projection": FORECAST_BANDS,
    "evaluation": {**fields("eligible basis"), "excluded_defect_ids": [None]},
}
RELEASE_FORECAST = {
    **fields("schema asof display_only scoreboard_ref"), "authority": FORECAST_AUTHORITY,
    "methodology_status": fields("forecast_epoch accuracy_claim street_consensus coherent_target_refit_status coherent_current_projection_n clean_forward_cpi_n next_required_step note"),
    "upcoming": [FORECAST_ITEM], "last_scored": [FORECAST_SCORED], "last_scored_all_forward": [FORECAST_SCORED],
    "track_record": {**fields("schema accuracy_claim display_min_n verdict_min_n evaluation_target evaluation_basis excluded_n"),
        "score_receipts": fields("raw_n canonical_n superseded_n note"), "releases": [FORECAST_TRACK], "shadows": [FORECAST_TRACK]},
    "capture_health": {**fields("last_nightly_asof nightly_gap_days past_due_unscored_count"),
        "enricher_staleness": fields("kalshi_releases_asof cleveland_nowcast_asof work_stoppages_asof print_integrity_asof"),
        "past_due_unscored": [fields("release release_type period release_date reason")]},
}


def project_release_forecast(value: dict) -> dict:
    result = project(value, RELEASE_FORECAST)
    for source, item in zip((value.get("upcoming") or [])[:200], result.get("upcoming") or []):
        if not isinstance(source, dict) or not isinstance(item, dict):
            continue
        if isinstance(source.get("components"), dict):
            item["components"] = project(source["components"], {
                **fields("private_trend government_trend birth_death_residual_prior residual"),
                "confidence_map": {"*": None}, "method_notes": {"*": None},
            })
        original_shadows = source.get("shadows") if isinstance(source.get("shadows"), dict) else {}
        for key, shadow in (item.get("shadows") or {}).items():
            original = original_shadows.get(key)
            if isinstance(original, dict) and isinstance(shadow, dict) and (original.get("claim_withdrawn") is True or isinstance(original.get("claim_withdrawn"), dict)):
                # A truthy withdrawal always suppresses numbers, even if an old
                # publisher used a boolean instead of the current receipt map.
                shadow["claim_withdrawn"] = project(original["claim_withdrawn"], FORECAST_WITHDRAWN) or True
                for field in ("point", "p10", "p25", "p50", "p75", "p90", "confidence", "components", "mf_energy_components"):
                    shadow.pop(field, None)
    return result


def project(value: Any, specification: Any) -> Any:
    """Finite, bounded, scalar-only leaves. Unknown keys and objects are omitted."""
    if isinstance(specification, dict):
        if not isinstance(value, dict):
            return None
        if "*" in specification:
            return {str(key)[:100]: project(child, specification["*"]) for key, child in list(value.items())[:200]}
        return {key: project(value[key], child) for key, child in specification.items() if key in value}
    if isinstance(specification, list):
        return [project(item, specification[0]) for item in value[:200]] if isinstance(value, (list, tuple)) else []
    value = finite_json_value(value)
    if isinstance(value, str):
        return value[:6000]
    return value if value is None or isinstance(value, (int, float, bool)) else None


def build_dashboard(vm: dict) -> dict:
    """Publish an explicit display projection of this build's existing VM."""
    generated = vm.get("generated_utc")
    if not isinstance(generated, str):
        raise ValueError("dashboard build clock unavailable")
    clock = datetime.fromisoformat(generated)
    # build_site's generated_utc is explicitly UTC, formatted without an offset.
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    state = project(vm.get("market_state"), STATE)
    latest = vm.get("latest") if isinstance(vm.get("latest"), dict) else {}
    return {
        "schema": SCHEMA, "market": "US", "display_only": True,
        "published_at": clock.isoformat(),
        "source_as_of": (state or {}).get("asof"),
        "market_state": state,
        "regime": project(latest, fields("date quad quad_name transition_state growth_score inflation_score confidence")),
        "history": project(vm.get("ms_history"), [fields("asof score")])[-60:],
        "risk_envelope": project(vm.get("risk_envelope"), ENVELOPE),
        "rates": project(vm.get("rates_command"), RATES),
        "events": project(vm.get("event_strip"), [EVENT])[:40],
        "sentiment": project(vm.get("fear_greed"), SENTIMENT),
        "breadth": project(vm.get("breadth_split"), fields("as_of stance_en stance_zh young disclaimer_en disclaimer_zh")),
        "sector_heat": project(vm.get("sector_heat"), {"as_of": None, "heating": [THEME], "cooling": [THEME], "rotation": [THEME]}),
        "policy": project(vm.get("policy_lever"), POLICY),
        "market_tiles": project(vm.get("market_tiles"), [{**fields("level chg pct tone sym mkt"), "label": PAIR, "tag": PAIR}]),
        "alerts": project(vm.get("alerts"), [fields("rule severity message message_zh plain_en plain_zh what_en what_zh detail_en detail_zh anchor href tier edge_en edge_zh")])[:50],
        # Error strings may contain provider credentials: they are never exported.
        "health": project(vm.get("health"), [fields("name status rows last_date")]),
        "brief": project(vm.get("master_brief"), BRIEF),
        "news": project((vm.get("macro_news") or {}).get("headlines"), [fields("title title_zh summary summary_zh url source source_name source_tier seendate domain theme importance")])[:20],
        "news_state": project(vm.get("macro_news"), {**fields("schema is_context_only fetched_at degraded_reason disclaimer"),
            "synthesis": fields("read read_zh"), "leg_status": {key: NEWS_LEG for key in ("gdelt", "official_rss", "news_rss")}}),
    }


def write_dashboard(vm: dict, destination: Path) -> None:
    payload = build_dashboard(vm)
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("native dashboard exceeds display bound")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_bytes(raw)
    temporary.replace(destination)
