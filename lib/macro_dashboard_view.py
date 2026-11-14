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
