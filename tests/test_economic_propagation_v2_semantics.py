"""Discriminators for review 5485984589: polarized conditions and real falsification."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from lib import economic_propagation_v2 as subject

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "tests/fixtures/economic_propagation/golden_supported_hypothesis.json").read_bytes())
POLARITIES = {
    "demand_transfer": ("toward_target", "away_from_target"),
    "supply_constraint": ("tightens", "eases"),
    "pricing_power_shift": ("strengthens", "weakens"),
    "input_cost_shift": ("increases", "decreases"),
    "capacity_reallocation": ("toward_target", "away_from_target"),
    "share_shift_competitive": ("toward_target", "away_from_target"),
    "regulatory_exposure": ("tightens", "eases"),
    "program_funding_flow": ("increases", "decreases"),
    "common_end_market_demand": ("increases", "decreases"),
}
METRIC = {
    "demand_transfer": "revenue", "supply_constraint": "volume",
    "pricing_power_shift": "pricing", "input_cost_shift": "input_cost",
    "capacity_reallocation": "capacity_utilization",
    "share_shift_competitive": "market_share", "regulatory_exposure": "revenue",
    "program_funding_flow": "backlog_orders", "common_end_market_demand": "volume",
}
PHRASES = {
    "demand_transfer": ("demand shifts toward the target", "demand shifts away from the target"),
    "supply_constraint": ("qualified supply available to the target tightens", "qualified supply available to the target eases"),
    "pricing_power_shift": ("the target's pricing power strengthens", "the target's pricing power weakens"),
    "input_cost_shift": ("the cost of inputs used by the target increases", "the cost of inputs used by the target decreases"),
    "capacity_reallocation": ("operating capacity is reallocated toward the target", "operating capacity is reallocated away from the target"),
    "share_shift_competitive": ("competitive business share shifts toward the target", "competitive business share shifts away from the target"),
    "regulatory_exposure": ("restrictions applicable to the target tighten", "restrictions applicable to the target ease"),
    "program_funding_flow": ("funding for the target's program increases", "funding for the target's program decreases"),
    "common_end_market_demand": ("demand in the target's shared end market increases", "demand in the target's shared end market decreases"),
}

def kwargs(mechanism="demand_transfer", polarity="toward_target", direction="improves"):
    keys = ("source_event", "target", "asof", "compiled_at", "generator_admissions",
            "relationship_paths", "similarity_evidence", "market_evidence")
    out = {key: copy.deepcopy(BASE[key]) for key in keys}
    out.update(mechanism_spec={
        "mechanism_class": mechanism, "mechanism_polarity": polarity,
        "predicted_operating_direction": direction, "operating_metric_class": METRIC[mechanism],
    }, alternative_classes=["sector_factor"], review_by=BASE["expiry"]["review_by"])
    return out

def rehash(record):
    out = copy.deepcopy(record)
    out["content_sha256"] = subject.content_sha256(out)
    return out

@pytest.mark.parametrize("mechanism", POLARITIES)
def test_missing_polarity_cannot_be_inferred_from_target_direction(mechanism):
    call = kwargs(mechanism, POLARITIES[mechanism][0])
    del call["mechanism_spec"]["mechanism_polarity"]
    with pytest.raises(subject.EconomicPropagationError):
        subject.compose_hypothesis_v2(**call)

@pytest.mark.parametrize("mechanism", POLARITIES)
def test_opposite_antecedents_have_distinct_text_and_scenario_identity(mechanism):
    records = [subject.compose_hypothesis_v2(**kwargs(mechanism, p)) for p in POLARITIES[mechanism]]
    for record, phrase in zip(records, PHRASES[mechanism]):
        assert subject.validate_hypothesis_v2(record) == []
        assert record["mechanism"]["hypothesis_text"].startswith("If " + phrase)
        assert record["mechanism"]["mechanism_polarity"] in POLARITIES[mechanism]
        assert " may " not in record["mechanism"]["hypothesis_text"]
    assert records[0]["record_id"] != records[1]["record_id"]
    assert records[0]["mechanism"]["hypothesis_text"] != records[1]["mechanism"]["hypothesis_text"]

@pytest.mark.parametrize("value", [None, "", "unknown", "increases", True, 1, {}, [], "toward_target "])
def test_invalid_demand_polarity_refuses_before_native_graph_derivation(value, monkeypatch):
    from lib import economic_propagation as native
    call = kwargs()
    call["mechanism_spec"]["mechanism_polarity"] = value
    def forbidden(*args, **kw):
        raise AssertionError("invalid polarity reached native graph derivation")
    monkeypatch.setattr(native, "derive_graph_states", forbidden)
    with pytest.raises(subject.EconomicPropagationError):
        subject.compose_hypothesis_v2(**call)

@pytest.mark.parametrize("mechanism", POLARITIES)
def test_mixed_without_scoped_components_cannot_be_claimed_falsifiable(mechanism):
    with pytest.raises(subject.EconomicPropagationError):
        subject.compose_hypothesis_v2(**kwargs(mechanism, POLARITIES[mechanism][0], "mixed"))

def test_falsifier_requires_occurrence_applicability_and_contrary_outcome():
    record = subject.compose_hypothesis_v2(**kwargs())
    assert len(record["falsifiers"]) == 1
    condition = record["falsifiers"][0]["condition"]
    observable = record["falsifiers"][0]["observable"]
    assert "occurred" in condition and "applicable relationship" in condition
    assert "did not increase" in condition and "preregistered" in condition
    assert all(word in observable for word in ("baseline", "scope", "lag", "window", "uncertainty", "rejection rule"))
    assert "mechanism did not occur" not in condition
    assert "not a contrary observation" in observable
    assert record["evaluation_requirements"]
    assert record["authority"] == BASE["authority"]

def test_antecedent_absence_inapplicability_and_expiry_are_separate_from_falsifiers():
    record = subject.compose_hypothesis_v2(**kwargs())
    notes = {row["reason"]: row for row in record["applicability_conditions"]}
    assert set(notes) == {
        "antecedent_not_observed", "relationship_inapplicable",
        "outcome_unavailable", "evaluation_not_registered", "review_expired_untested",
    }
    assert "not falsified" in notes["antecedent_not_observed"]["consequence"]
    assert "not falsified" in notes["relationship_inapplicable"]["consequence"]
    assert "not falsified" in notes["review_expired_untested"]["consequence"]
    assert all("status" not in row for row in notes.values())  # no claimed observed outcome
    assert not any("state" in key or "grade" in key for key in record["evaluation_requirements"])

def test_genuine_abstention_emits_no_directional_falsifier():
    call = kwargs()
    call["mechanism_spec"] = None
    call["relationship_paths"] = []
    call["generator_admissions"] = [copy.deepcopy(BASE["generator_admissions"][1])]
    record = subject.compose_hypothesis_v2(**call)
    assert subject.validate_hypothesis_v2(record) == []
    assert record["hypothesis_state"] == "abstained"
    assert record["falsifiers"] == []
    assert record["mechanism"]["mechanism_polarity"] is None
    assert any(row["reason"] == "no_directional_claim" for row in record["applicability_conditions"])
    assert record["economic_share"] is None and record["authority"] == BASE["authority"]

@pytest.mark.parametrize("direction,expected", [("improves", "decrease"), ("deteriorates", "increase")])
def test_input_cost_claim_and_contrary_outcome_share_physical_direction(direction, expected):
    record = subject.compose_hypothesis_v2(**kwargs("input_cost_shift", "increases", direction))
    assert ("an increase" if expected == "increase" else "a decrease") + " in input costs" in record["mechanism"]["hypothesis_text"]
    assert "did not " + expected in record["falsifiers"][0]["condition"]

@pytest.mark.parametrize("field", ["applicability_conditions", "evaluation_requirements", "falsifiers"])
def test_rehash_cannot_change_applicability_or_test_requirements(field):
    record = subject.compose_hypothesis_v2(**kwargs())
    record[field] = []
    assert subject.validate_hypothesis_v2(rehash(record))

def test_rehash_cannot_reverse_polarity_without_reconstructing_narrative_and_identity():
    record = subject.compose_hypothesis_v2(**kwargs())
    record["mechanism"]["mechanism_polarity"] = "away_from_target"
    findings = subject.validate_hypothesis_v2(rehash(record))
    assert "K3D_V2_R010" in {f.code for f in findings}
    assert "K3D_V2_R082" in {f.code for f in findings}

def test_previous_unpolarized_profile_is_not_silently_promoted():
    record = subject.compose_hypothesis_v2(**kwargs())
    record["construction_profile"] = "compiler_owned_qualitative.v1"
    assert subject.validate_hypothesis_v2(rehash(record))

def test_polarity_and_hypothesized_outcome_are_explicit_separate_inputs():
    improving = subject.compose_hypothesis_v2(**kwargs(direction="improves"))
    worsening = subject.compose_hypothesis_v2(**kwargs(direction="deteriorates"))
    assert improving["mechanism"]["mechanism_polarity"] == worsening["mechanism"]["mechanism_polarity"]
    assert improving["record_id"] != worsening["record_id"]  # competing scenario, not one interchangeable claim

def test_no_external_evaluation_or_source_write_was_invented():
    record = subject.compose_hypothesis_v2(**kwargs())
    assert "evaluation_result" not in record and "evaluated_at" not in record
    assert all(record["authority"][k] is False for k in ("trading", "ranking", "gating", "sizing", "entry", "originates_signals"))
    assert record["economic_share"] is None


def test_scenario_key_order_is_not_a_new_identity_or_content():
    left = kwargs()
    right = copy.deepcopy(left)
    right["mechanism_spec"] = dict(reversed(list(right["mechanism_spec"].items())))
    a = subject.compose_hypothesis_v2(**left)
    b = subject.compose_hypothesis_v2(**right)
    assert a == b
    assert a["record_id"] == b["record_id"] and a["content_sha256"] == b["content_sha256"]

@pytest.mark.parametrize("field", ["applicability_conditions", "evaluation_requirements", "falsifiers"])
def test_same_shape_rehash_cannot_replace_semantic_conditions(field):
    record = subject.compose_hypothesis_v2(**kwargs())
    if field == "applicability_conditions":
        record[field][0]["consequence"] = "Treat this non-occurrence as a failed claim."
    elif field == "evaluation_requirements":
        record[field][0] = "no_observed_antecedent_required"
    else:
        record[field][0]["condition"] = "The mechanism never happened."
    findings = subject.validate_hypothesis_v2(rehash(record))
    assert "K3D_V2_R010" in {f.code for f in findings}
