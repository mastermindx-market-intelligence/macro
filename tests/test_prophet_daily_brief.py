from __future__ import annotations

import copy
import hashlib
import json

import pytest

from engine.prophet_entry_availability import (
    DEFINITION as B4_DEFINITION,
    ENTRY_POLICY_VERSION,
    HORIZON,
    HORIZON_ROLE,
    SCHEMA as B4_SCHEMA,
    STRATEGY_ID,
    validate_entry_availability,
)
from engine.prophet_strategy_definition import build_early_leadership_sector_rotation_definition
from engine.prophet_daily_brief import (
    DailyBriefContractError,
    SCHEMA,
    compose_daily_brief,
    validate_daily_brief_view,
)

SEC = "SEC:US-XNAS-AAPL"
EP = "ce:apple-1"
GEN = "cg:2026-09-30"
SESSION = "2026-09-30"
NOW = "2026-09-30T20:00:00Z"


def _canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _b4(state="ENTRY_OPEN", *, blockers=None, quote_asof="2026-09-30T19:59:00Z"):
    strategy = build_early_leadership_sector_rotation_definition()
    payload = {
        "schema": B4_SCHEMA,
        "definition": B4_DEFINITION,
        "episode_id": EP,
        "candidate_generation_id": GEN,
        "candidate_state_projection_id": "pcs:unit",
        "security_id": SEC,
        "identity_epoch": "epoch_0",
        "strategy_definition_id": strategy["strategy_definition_id"],
        "strategy_id": STRATEGY_ID,
        "strategy_version": strategy["strategy_version"],
        "horizon": HORIZON,
        "horizon_role": HORIZON_ROLE,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "evaluated_at": "2026-09-30T20:00:00Z",
        "market_session": SESSION,
        "state": state,
        "entry_open": state == "ENTRY_OPEN",
        "zone": {"low": 100.0, "high": 102.0, "basis": "adjusted:v7"},
        "current_price": 101.0,
        "current_price_basis": "trade:v1",
        "quote_asof": quote_asof,
        "quote_age_seconds": 60,
        "invalidation": {"price": 96.0, "kind": "structural", "basis": "adjusted:v7"},
        "distance_to_zone_pct": 0.0,
        "risk_to_invalidation_pct": 4.950495,
        "move_since_first_trigger_pct": 2.020202,
        "move_since_anchor_pct": 1.0,
        "extension_atr": -0.5,
        "chase_state": "within_boundary",
        "owner_status": "buy_now",
        "blockers": sorted(blockers or []),
        "reasons": [] if state != "ENTRY_OPEN" else [
            "CURRENT_PRICE_INSIDE_OWNER_ZONE", "FRESH_QUOTE", "LIQUIDITY_FILLABLE",
            "OWNER_CONFLUENCE_PASSED", "RISK_WITHIN_LANE_CEILING",
        ],
        "source_receipts": ["sha256:" + "1" * 64],
    }
    material = dict(payload)
    payload["availability_id"] = "pea:" + hashlib.sha256(_canon(material).encode()).hexdigest()
    validate_entry_availability(payload)
    return payload


def _bound(schema, *, state="CURRENT", asof="2026-09-30T19:58:00Z", **extra):
    out = {
        "schema": schema,
        "owner_ref": "owner:" + schema.split("/")[0].replace(".", "-") + ":v1",
        "security_id": SEC,
        "episode_id": EP,
        "candidate_generation_id": GEN,
        "market_session": SESSION,
        "asof": asof,
        "source_receipt": "sha256:" + "2" * 64,
        "state": state,
    }
    out.update(extra)
    return out


def _candidate(**extra):
    return _bound(
        "prophet.daily_brief_candidate_input/v1",
        state="SELECTED",
        selection_receipt="sha256:" + "3" * 64,
        display={"ticker": "AAPL", "why_selected": "Owner-selected setup"},
        **extra,
    )


def _plan(**extra):
    args = {
        "state": "RELATED_SECURITY",
        "relation_state": "related_security",
        "exact_relation": "unavailable",
        "plan_ids": ["AAPL-BULL-1"],
    }
    args.update(extra)
    return _bound("prophet.daily_brief_plan_input/v1", **args)


def _assessment(**extra):
    args = {"state": "CURRENT", "summary": {"headline": "Assessment remains current"}}
    args.update(extra)
    return _bound("prophet.daily_brief_assessment_input/v1", **args)


def _evidence(**extra):
    args = {"state": "CURRENT", "coverage": {"required": 5, "available": 5}}
    args.update(extra)
    return _bound("prophet.daily_brief_evidence_input/v1", **args)


def _assembly(**extra):
    out = {
        "schema": "prophet.daily_brief_assembly_input/v1",
        "owner_ref": "owner:daily-brief-assembly:v1",
        "state": "OK",
        "assembled_at": "2026-09-30T20:00:00Z",
        "source_receipts": ["sha256:" + "4" * 64],
        "reason": None,
    }
    out.update(extra)
    return out


def _compose(**overrides):
    args = {
        "candidate": _candidate(),
        "entry_availability": _b4(),
        "plan": _plan(),
        "assessment": _assessment(),
        "evidence": _evidence(),
        "assembly": _assembly(),
        "recovery": None,
        "previous": None,
        "now": NOW,
    }
    args.update(overrides)
    return compose_daily_brief(**args)


def test_entry_open_yields_entry_cleared_current_without_trading_authority():
    out = _compose()
    assert out["schema"] == SCHEMA
    assert out["decision_state"] == "ENTRY_CLEARED"
    assert out["health_state"] == "CURRENT"
    assert set(out["authority"].values()) == {False}
    assert out["identity"] == {
        "security_id": SEC, "episode_id": EP,
        "candidate_generation_id": GEN, "market_session": SESSION,
    }
    assert out["clocks"]["assessment"] == "2026-09-30T19:58:00Z"
    assert out["clocks"]["quote"] == "2026-09-30T19:59:00Z"
    assert out["clocks"]["assembly"] == "2026-09-30T20:00:00Z"
    validate_daily_brief_view(out)


def test_known_non_entry_b4_is_no_entry_cleared_not_unavailable():
    out = _compose(entry_availability=_b4("WAIT_PULLBACK", blockers=["CURRENT_PRICE_ABOVE_OWNER_ZONE"]))
    assert out["decision_state"] == "NO_ENTRY_CLEARED"
    assert out["health_state"] == "CURRENT"


def test_missing_malformed_or_unavailable_b4_never_rounds_down_to_no_entry():
    assert _compose(entry_availability=None)["decision_state"] == "UNAVAILABLE"
    malformed = _b4()
    malformed["availability_id"] = "pea:" + "0" * 64
    assert _compose(entry_availability=malformed)["decision_state"] == "UNAVAILABLE"
    unavailable = _b4("UNAVAILABLE_DATA", blockers=["SOURCE_HEALTH_UNKNOWN"])
    assert _compose(entry_availability=unavailable)["decision_state"] == "UNAVAILABLE"


def test_stale_quote_only_changes_health_and_preserves_plan_assessment_clocks():
    stale = _b4("UNAVAILABLE_DATA", blockers=["QUOTE_STALE"], quote_asof="2026-09-30T19:00:00Z")
    out = _compose(entry_availability=stale)
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["health_state"] == "STALE_QUOTE"
    assert out["clocks"]["quote"] == "2026-09-30T19:00:00Z"
    assert out["clocks"]["plan"] == "2026-09-30T19:58:00Z"
    assert out["clocks"]["assessment"] == "2026-09-30T19:58:00Z"


def test_partial_evidence_preserves_owner_records_but_cannot_promote_health():
    out = _compose(evidence=_evidence(state="PARTIAL", coverage={"required": 5, "available": 3}))
    assert out["decision_state"] == "ENTRY_CLEARED"
    assert out["health_state"] == "PARTIAL"
    assert out["owners"]["assessment"]["state"] == "CURRENT"
    assert out["owners"]["plan"]["state"] == "RELATED_SECURITY"


def test_unavailable_assembly_may_reference_valid_previous_read_only_but_never_copy_decision():
    previous = _compose()
    out = _compose(assembly=_assembly(state="UNAVAILABLE", reason="owner_missing"), previous=previous)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["fallback"] == {
        "kind": "LAST_ACCEPTED_READ_ONLY",
        "view_id": previous["view_id"],
        "decision_state": previous["decision_state"],
        "health_state": previous["health_state"],
    }


def test_effect_unknown_requires_exact_operation_carrier_and_target():
    with pytest.raises(DailyBriefContractError, match="effect-unknown recovery"):
        _compose(assembly=_assembly(state="EFFECT_UNKNOWN", reason="timeout"))
    recovery = {
        "schema": "prophet.daily_brief_recovery_input/v1",
        "owner_ref": "owner:prophet-rescue:v1",
        "state": "EFFECT_UNKNOWN",
        "operation_id": "op:123",
        "carrier": "github:issue:6817",
        "target": "prophet:daily-brief:AAPL",
        "source_receipt": "sha256:" + "5" * 64,
    }
    out = _compose(assembly=_assembly(state="EFFECT_UNKNOWN", reason="transport_unknown"), recovery=recovery)
    assert out["health_state"] == "EFFECT_UNKNOWN"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["recovery"] == {
        "operation_id": "op:123", "carrier": "github:issue:6817", "target": "prophet:daily-brief:AAPL"
    }


def test_generic_timeout_is_unavailable_not_effect_unknown():
    out = _compose(assembly=_assembly(state="UNAVAILABLE", reason="timeout"))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["recovery"] is None


def test_b4_identity_mismatch_fails_unavailable():
    bad = _b4()
    bad["security_id"] = "SEC:OTHER"
    material = {k: v for k, v in bad.items() if k != "availability_id"}
    bad["availability_id"] = "pea:" + hashlib.sha256(_canon(material).encode()).hexdigest()
    validate_entry_availability(bad)
    out = _compose(entry_availability=bad)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "OWNER_BINDING_MISMATCH" in out["issues"]


@pytest.mark.parametrize("which,field,value", [
    ("plan", "security_id", "SEC:OTHER"),
    ("assessment", "episode_id", "ce:other"),
    ("evidence", "candidate_generation_id", "cg:other"),
    ("candidate", "market_session", "2026-09-29"),
])
def test_cross_identity_generation_or_session_mismatch_fails_unavailable(which, field, value):
    inputs = {"plan": _plan(), "assessment": _assessment(), "evidence": _evidence(), "candidate": _candidate()}
    inputs[which][field] = value
    out = _compose(**inputs)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "OWNER_BINDING_MISMATCH" in out["issues"]


def test_future_owner_clock_fails_unavailable():
    out = _compose(assessment=_assessment(asof="2026-10-01T00:00:01Z"))
    assert out["health_state"] == "UNAVAILABLE"
    assert "FUTURE_OWNER_CLOCK" in out["issues"]


def test_unknown_owner_schema_or_state_fails_closed():
    bad_schema = _assessment()
    bad_schema["schema"] = "prophet.unknown/v99"
    out = _compose(assessment=bad_schema)
    assert out["health_state"] == "UNAVAILABLE"
    assert "OWNER_INPUT_UNAVAILABLE" in out["issues"]

    bad_state = _assessment(state="MAGIC_CURRENT")
    out = _compose(assessment=bad_state)
    assert out["health_state"] == "UNAVAILABLE"
    assert "OWNER_INPUT_UNAVAILABLE" in out["issues"]


def test_unknown_plan_relation_fails_closed_without_minting_plan_authority():
    bad = _plan(relation_state="candidate_specific_plan")
    out = _compose(plan=bad)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "OWNER_INPUT_UNAVAILABLE" in out["issues"]


def test_forbidden_authority_fields_are_rejected_before_composition():
    bad = _candidate()
    bad["display"]["probability"] = 0.91
    with pytest.raises(DailyBriefContractError, match="forbidden authority field"):
        _compose(candidate=bad)


def test_output_contains_no_score_probability_weight_size_order_broker_fill_position_retry_or_polling_keys():
    out = _compose()
    banned = {"score", "probability", "weight", "size", "order", "broker", "fill", "position", "retry", "polling"}
    seen = set()
    def walk(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if str(k).lower() in banned:
                    seen.add(str(k).lower())
                walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    walk(out)
    assert not seen


def test_view_is_deterministic_content_receipted_and_mutation_detected():
    a = _compose()
    b = _compose()
    assert a == b
    assert a["view_id"].startswith("pdbv:")
    tampered = copy.deepcopy(a)
    tampered["health_state"] = "PARTIAL"
    with pytest.raises(DailyBriefContractError, match="view_id"):
        validate_daily_brief_view(tampered)
