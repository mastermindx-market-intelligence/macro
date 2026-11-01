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


def _quote(**extra):
    args = {
        "state": "CURRENT",
        "observed_at": "2026-09-30T19:59:00Z",
        "price": 101.0,
        "basis": "trade:v1",
        "owner_ref": "owner:daily-brief-quote:v1",
        "source_receipt": "sha256:" + "6" * 64,
    }
    args.update(extra)
    schema = args.pop("schema", "prophet.daily_brief_quote_input/v1")
    return _bound(schema, **args)


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
        "quote": _quote(),
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
    assert out["clocks"]["entry_availability_quote"] == "2026-09-30T19:59:00Z"
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
    # B4's own quote clock stays visible as entry_availability_quote; the supplied
    # quote owner keeps clocks.quote and cannot renew the stale B4 result.
    assert out["clocks"]["entry_availability_quote"] == "2026-09-30T19:00:00Z"
    assert out["clocks"]["quote"] == "2026-09-30T19:59:00Z"
    assert out["clocks"]["plan"] == "2026-09-30T19:58:00Z"
    assert out["clocks"]["assessment"] == "2026-09-30T19:58:00Z"
    assert out["presentation"]["availability"]["state"] == "UNAVAILABLE_DATA"


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


@pytest.mark.parametrize("overrides", [
    {"schema": "wrong"},
    {"source_receipts": []},
    {"source_receipts": ["not-a-receipt"]},
    {"owner_ref": ""},
])
def test_invalid_assembly_cannot_leave_entry_cleared(overrides):
    out = _compose(assembly=_assembly(**overrides))
    assert "ASSEMBLY_UNAVAILABLE" in out["issues"]
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"


@pytest.mark.parametrize("assessment_state,evidence_state,quote_stale", [
    ("UNAVAILABLE", "PARTIAL", False),
    ("UNAVAILABLE", "CURRENT", True),
    ("UNAVAILABLE", "PARTIAL", True),
    ("CURRENT", "UNAVAILABLE", True),
    ("UNAVAILABLE", "UNAVAILABLE", True),
])
def test_partial_or_stale_health_cannot_mask_unavailable_required_owner(
    assessment_state, evidence_state, quote_stale
):
    b4 = (_b4("UNAVAILABLE_DATA", blockers=["QUOTE_STALE"])
          if quote_stale else _b4())
    out = _compose(
        assessment=_assessment(state=assessment_state),
        evidence=_evidence(state=evidence_state),
        entry_availability=b4,
    )
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["owners"]["assessment"]["state"] == assessment_state
    assert out["owners"]["evidence"]["state"] == evidence_state
    assert out["clocks"]["assessment"] == "2026-09-30T19:58:00Z"


@pytest.mark.parametrize("value", [
    "2026-09-30Z", "2026-09-30 19:58:00Z", "20260930T195800Z",
    "2026-09-30T19:58Z",
])
def test_non_rfc3339_owner_clock_is_not_presented_as_current(value):
    out = _compose(assessment=_assessment(asof=value))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"


def test_future_b4_assessment_clock_cannot_hide_behind_fresh_quote():
    b4 = _b4()
    b4["evaluated_at"] = "2026-10-01T00:00:01Z"
    material = {k: v for k, v in b4.items() if k != "availability_id"}
    b4["availability_id"] = "pea:" + hashlib.sha256(_canon(material).encode()).hexdigest()
    validate_entry_availability(b4)
    out = _compose(entry_availability=b4)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "FUTURE_OWNER_CLOCK" in out["issues"]


def test_composition_does_not_mutate_owner_receipts():
    inputs = {
        "candidate": _candidate(), "plan": _plan(), "assessment": _assessment(),
        "evidence": _evidence(), "assembly": _assembly(), "entry_availability": _b4(),
        "quote": _quote(),
    }
    before = copy.deepcopy(inputs)
    _compose(**inputs)
    assert inputs == before


@pytest.mark.parametrize("missing_b4", [None, {"schema": "invalid"}])
def test_missing_entry_owner_is_not_masked_by_partial_evidence(missing_b4):
    out = _compose(entry_availability=missing_b4, evidence=_evidence(state="PARTIAL"))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"


def test_view_does_not_alias_mutable_owner_presentation():
    candidate = _candidate()
    assessment = _assessment()
    evidence = _evidence()
    out = _compose(candidate=candidate, assessment=assessment, evidence=evidence)
    frozen = copy.deepcopy(out)
    candidate["display"]["ticker"] = "OTHER"
    assessment["summary"]["headline"] = "Changed after composition"
    evidence["coverage"]["available"] = 0
    assert out == frozen
    validate_daily_brief_view(out)


def test_editing_returned_view_does_not_edit_owner_receipt():
    candidate = _candidate()
    before = copy.deepcopy(candidate)
    out = _compose(candidate=candidate)
    out["presentation"]["candidate"]["ticker"] = "OTHER"
    assert candidate == before


def test_entry_assessment_clock_is_independent_and_shape_stable():
    present = _compose()
    missing = _compose(entry_availability=None)
    assert present["clocks"]["entry_availability"] == "2026-09-30T20:00:00Z"
    assert missing["clocks"]["entry_availability"] is None
    assert set(present["clocks"]) == set(missing["clocks"])


@pytest.mark.parametrize("overrides", [
    {"state": "NONE"},
    {"state": "RELATED_SECURITY", "relation_state": "none"},
    {"plan_ids": []},
    {"plan_ids": ["AAPL-BULL-1", "AAPL-BULL-1"]},
    {"plan_ids": [" "]},
    {"exact_relation": "available"},
    {"state": "UNAVAILABLE", "relation_state": "unavailable", "plan_ids": []},
])
def test_plan_relation_never_promotes_same_security_or_unavailable_to_exact_plan(overrides):
    out = _compose(plan=_plan(**overrides))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"


def test_explicit_no_related_plan_is_not_a_data_failure_or_entry_veto():
    out = _compose(plan=_plan(state="NONE", relation_state="none", plan_ids=[]))
    assert out["health_state"] == "CURRENT"
    assert out["decision_state"] == "ENTRY_CLEARED"
    assert out["presentation"]["plan"] == {
        "relation_state": "none", "exact_relation": "unavailable", "plan_ids": [],
    }


@pytest.mark.parametrize("owner,field", [
    ("plan", "relation_state"), ("plan", "plan_ids"), ("assembly", "state"),
])
@pytest.mark.parametrize("value", [None, True, 7, [], {}, [None]])
def test_malformed_owner_json_degrades_without_raw_exception(owner, field, value):
    record = {"plan": _plan, "assembly": _assembly}[owner]()
    record[field] = value
    out = _compose(**{owner: record})
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["health_state"] == "UNAVAILABLE"
    validate_daily_brief_view(out)


@pytest.mark.parametrize("field", ["decision_state", "health_state"])
@pytest.mark.parametrize("value", [None, True, 7, [], {}, ["unexpected"]])
def test_view_validator_uses_contract_errors_for_malformed_states(field, value):
    malformed = _compose()
    malformed[field] = value
    with pytest.raises(DailyBriefContractError):
        validate_daily_brief_view(malformed)


@pytest.mark.parametrize("field", ["decision_state", "health_state"])
@pytest.mark.parametrize("value", [[], {}, ["unexpected"]])
def test_invalid_previous_view_never_crashes_current_unavailable_view(field, value):
    previous = _compose()
    previous[field] = value
    out = _compose(assembly=_assembly(state="UNAVAILABLE"), previous=previous)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["fallback"] is None


def test_malformed_plan_is_typed_unavailable_in_presentation():
    out = _compose(plan=_plan(relation_state={"unexpected": True}, plan_ids=7))
    assert out["presentation"]["plan"] == {
        "relation_state": "unavailable", "exact_relation": "unavailable", "plan_ids": [],
    }


# ---------------------------------------------------------------------------
# Independent caller-supplied quote owner (ported R4.8 behavior, original contract)
# ---------------------------------------------------------------------------


def test_legacy_call_omitting_quote_is_explicitly_unavailable_never_b4_backfill():
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
    out = compose_daily_brief(**args)  # quote defaults to None
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "QUOTE_UNAVAILABLE" in out["issues"]
    assert out["clocks"]["quote"] is None
    assert out["owners"]["quote"] is None
    assert out["presentation"]["quote"] == {
        "state": "UNAVAILABLE", "observed_at": None, "price": None, "basis": None,
    }
    assert out["presentation"]["availability"]["state"] == "ENTRY_OPEN"
    validate_daily_brief_view(out)


def test_native_stale_quote_cannot_become_current_and_blocks_entry_publication():
    out = _compose(quote=_quote(state="STALE"))
    assert out["health_state"] == "STALE_QUOTE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["owners"]["quote"]["state"] == "STALE"
    assert out["clocks"]["quote"] == "2026-09-30T19:59:00Z"
    # Native quote state and facts are presented without calculation...
    assert out["presentation"]["quote"] == {
        "state": "STALE", "observed_at": "2026-09-30T19:59:00Z", "price": 101.0, "basis": "trade:v1",
    }
    # ...and the B4-owned result is preserved, not recomputed or downgraded by the quote.
    assert out["presentation"]["availability"]["state"] == "ENTRY_OPEN"
    validate_daily_brief_view(out)


def test_native_unavailable_quote_carries_no_price_or_time_facts():
    out = _compose(quote=_quote(state="UNAVAILABLE", observed_at=None, price=None, basis=None))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["owners"]["quote"]["state"] == "UNAVAILABLE"
    assert out["clocks"]["quote"] is None
    assert out["presentation"]["quote"] == {
        "state": "UNAVAILABLE", "observed_at": None, "price": None, "basis": None,
    }
    validate_daily_brief_view(out)


def test_unavailable_quote_cannot_smuggle_observed_price_facts():
    out = _compose(quote=_quote(state="UNAVAILABLE"))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "QUOTE_INPUT_UNAVAILABLE" in out["issues"]
    assert out["presentation"]["quote"]["price"] is None
    assert out["presentation"]["quote"]["observed_at"] is None
    validate_daily_brief_view(out)


@pytest.mark.parametrize("field,value", [
    ("security_id", "SEC:US-XNAS-MSFT"),
    ("episode_id", "ce:apple-2"),
    ("candidate_generation_id", "cg:2026-09-29"),
    ("market_session", "2026-09-29"),
])
def test_quote_identity_binding_is_exact_four_field(field, value):
    out = _compose(quote=_quote(**{field: value}))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "OWNER_BINDING_MISMATCH" in out["issues"]
    assert "QUOTE_INPUT_UNAVAILABLE" in out["issues"]
    assert out["presentation"]["quote"]["price"] is None
    validate_daily_brief_view(out)


@pytest.mark.parametrize("observed_at", [
    "2026-10-01T00:00:01Z",
    "2026-09-30 19:59:00Z",
    "2026-13-30T19:59:00Z",
    "2026-09-30T19:59:00+01:00",
    "not-a-time",
    7,
    None,
])
def test_quote_observed_at_must_be_valid_utc_and_not_future(observed_at):
    out = _compose(quote=_quote(observed_at=observed_at))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["presentation"]["quote"]["observed_at"] is None
    assert out["clocks"]["quote"] is None
    validate_daily_brief_view(out)


def test_future_quote_clock_reports_future_owner_clock():
    out = _compose(quote=_quote(observed_at="2026-10-01T00:00:01Z"))
    assert "FUTURE_OWNER_CLOCK" in out["issues"]


def test_quote_older_than_b4_quote_is_not_a_latest_quote():
    out = _compose(quote=_quote(observed_at="2026-09-30T19:58:00Z"))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "QUOTE_OLDER_THAN_ENTRY_AVAILABILITY" in out["issues"]
    validate_daily_brief_view(out)


@pytest.mark.parametrize("field,value", [("price", 102.5), ("basis", "trade:v2")])
def test_same_clock_quote_cannot_contradict_the_b4_bound_quote(field, value):
    out = _compose(quote=_quote(**{field: value}))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "QUOTE_CONTRADICTS_ENTRY_AVAILABILITY" in out["issues"]
    validate_daily_brief_view(out)


def test_newer_quote_preserves_b4_plan_and_assessment_clocks_and_decision():
    out = _compose(quote=_quote(observed_at="2026-09-30T19:59:30Z", price=101.5))
    assert out["decision_state"] == "ENTRY_CLEARED"
    assert out["health_state"] == "CURRENT"
    assert out["clocks"] == {
        "candidate": "2026-09-30T19:58:00Z",
        "quote": "2026-09-30T19:59:30Z",
        "entry_availability": "2026-09-30T20:00:00Z",
        "entry_availability_quote": "2026-09-30T19:59:00Z",
        "plan": "2026-09-30T19:58:00Z",
        "assessment": "2026-09-30T19:58:00Z",
        "evidence": "2026-09-30T19:58:00Z",
        "assembly": "2026-09-30T20:00:00Z",
    }
    assert out["presentation"]["availability"]["state"] == "ENTRY_OPEN"
    validate_daily_brief_view(out)


def test_quote_price_accepts_huge_integer_without_raw_exception():
    huge = 10**80
    out = _compose(quote=_quote(observed_at="2026-09-30T19:59:30Z", price=huge))
    assert out["presentation"]["quote"]["price"] == huge
    validate_daily_brief_view(out)
    contradicted = _compose(quote=_quote(price=huge))
    assert "QUOTE_CONTRADICTS_ENTRY_AVAILABILITY" in contradicted["issues"]
    assert contradicted["presentation"]["quote"]["price"] is None


@pytest.mark.parametrize("overrides", [
    {"state": None}, {"state": True}, {"state": 7}, {"state": []}, {"state": {}},
    {"state": "FRESH"},
    {"owner_ref": ""},
    {"source_receipt": "not-a-receipt"},
    {"schema": "prophet.daily_brief_quote_input/v2"},
    {"security_id": None},
    {"price": "101.0"}, {"price": True}, {"price": 0}, {"price": -1.0},
    {"price": float("inf")}, {"price": float("nan")},
    {"basis": ""}, {"basis": 5},
])
def test_malformed_quote_json_degrades_to_typed_unavailable(overrides):
    out = _compose(quote=_quote(**overrides))
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert "QUOTE_INPUT_UNAVAILABLE" in out["issues"]
    assert out["presentation"]["quote"] == {
        "state": "UNAVAILABLE", "observed_at": None, "price": None, "basis": None,
    }
    validate_daily_brief_view(out)


def test_quote_input_is_not_aliased_into_the_view_and_vice_versa():
    quote = _quote()
    out = _compose(quote=quote)
    validate_daily_brief_view(out)
    frozen = copy.deepcopy(out)
    quote["price"] = 1.0
    quote["state"] = "STALE"
    assert out == frozen
    assert out["presentation"]["quote"]["price"] == 101.0
    out["presentation"]["quote"]["price"] = 2.0
    assert quote["price"] == 1.0


def test_malformed_quote_still_allows_last_accepted_read_only_fallback():
    previous = _compose()
    out = _compose(quote=_quote(price="101.0"), previous=previous)
    assert out["health_state"] == "UNAVAILABLE"
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["fallback"] == {
        "kind": "LAST_ACCEPTED_READ_ONLY",
        "view_id": previous["view_id"],
        "decision_state": previous["decision_state"],
        "health_state": previous["health_state"],
    }


def test_quote_owner_presence_does_not_change_authority_or_view_field_closure():
    out = _compose()
    assert set(out["authority"].values()) == {False}
    assert set(out["owners"]) == {
        "candidate", "plan", "assessment", "evidence", "quote",
        "entry_availability", "assembly",
    }
    validate_daily_brief_view(out)


@pytest.mark.parametrize("overrides", [
    {"state": "NONE"},
    {"state": "UNAVAILABLE"},
    {"relation_state": "none", "plan_ids": []},
    {"plan_ids": []},
])
def test_inconsistent_plan_state_cannot_retain_a_usable_presented_relation(overrides):
    out = _compose(plan=_plan(**overrides))
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["health_state"] == "UNAVAILABLE"
    assert "OWNER_INPUT_UNAVAILABLE" in out["issues"]
    assert out["presentation"]["plan"] == {
        "relation_state": "unavailable", "exact_relation": "unavailable", "plan_ids": [],
    }
    validate_daily_brief_view(out)


@pytest.mark.parametrize("state,field,value", [
    ("ENTRY_OPEN", "reasons", [None]),
    ("ENTRY_OPEN", "reasons", [123]),
    ("WAIT_PULLBACK", "blockers", [123]),
    ("WAIT_PULLBACK", "blockers", {"unexpected": True}),
])
def test_malformed_b4_lists_close_decision_and_health_before_presentation(state, field, value):
    b4 = _b4(state)
    b4[field] = value
    material = {k: v for k, v in b4.items() if k != "availability_id"}
    b4["availability_id"] = "pea:" + hashlib.sha256(_canon(material).encode()).hexdigest()
    validate_entry_availability(b4)
    before = copy.deepcopy(b4)
    out = _compose(entry_availability=b4)
    assert "ENTRY_AVAILABILITY_INVALID" in out["issues"]
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["health_state"] == "UNAVAILABLE"
    assert out["presentation"]["availability"][field] == []
    assert b4 == before


@pytest.mark.parametrize("field,value", [
    ("current_price", "101.0"),
    ("current_price", None),
    ("current_price", True),
    ("current_price_basis", None),
    ("current_price_basis", {"unexpected": True}),
])
def test_same_clock_incomparable_b4_quote_cannot_authorize_latest_price(field, value):
    b4 = _b4()
    b4[field] = value
    material = {k: v for k, v in b4.items() if k != "availability_id"}
    b4["availability_id"] = "pea:" + hashlib.sha256(_canon(material).encode()).hexdigest()
    validate_entry_availability(b4)
    before = copy.deepcopy(b4)
    quote = _quote(price=999.0 if field == "current_price" else 101.0)
    out = _compose(entry_availability=b4, quote=quote)
    assert out["decision_state"] == "UNAVAILABLE"
    assert out["health_state"] == "UNAVAILABLE"
    assert "QUOTE_CONTRADICTS_ENTRY_AVAILABILITY" in out["issues"]
    assert out["presentation"]["quote"] == {
        "state": "UNAVAILABLE", "observed_at": None, "price": None, "basis": None,
    }
    assert b4 == before
