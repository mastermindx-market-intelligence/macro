"""Actual A1 composition: unqualified class payloads cannot become task evidence.

Synthetic native ledgers only; no protected outcomes, producer execution or scorer.
The class-specific payloads deliberately have no accepted owner metric adapter.
Each case proves display/source preservation, not empirical validity.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from admin import intelligence_os as IOS

CLASS_PAYLOADS = {
    "predictive": ({"target": "UP/DOWN/FLAT at21 NYSE sessions", "probabilities": [.7,.2,.1]},
                   {"target": "UP/DOWN/FLAT at21 NYSE sessions", "probabilities": [65,20,15]}),
    "ranking": ({"eligible_at_cutoff": ["A","B","C"], "ranked": ["A","C","B"], "top_k": 1},
                {"eligible_at_cutoff": ["A","B","C"], "evaluated_universe": ["A"], "claimed_coverage": 1}),
    "classification_state": ({"label": "STABLE", "label_known_at": "2026-01-01T00:00:00Z", "decision_at": "2026-01-02T00:00:00Z"},
                             {"label": "STABLE", "label_known_at": "2026-01-03T00:00:00Z", "decision_at": "2026-01-02T00:00:00Z"}),
    "detection_event": ({"events": ["e1"], "alarms": ["a1"], "matches": [["a1","e1"]]},
                        {"events": ["e1"], "alarms": ["a1","a2","a3"], "matches": [["a1","e1"],["a2","e1"],["a3","e1"]]}),
    "descriptive": ({"entity": "fixture", "value": .1, "unit": "ratio", "window": "quarter"},
                    {"entity": "fixture", "value": .1, "unit": "percent", "window": "quarter"}),
    "salience": ({"rubric_owner": "independent-fixture", "target": "relevance", "direction": 0},
                 {"rubric_owner": "same-generating-model", "target": "price-hit-rate", "direction": 0}),
    "generative": ({"source_entity": "fixture", "source_unit": "USD", "source_window": "quarter", "answer_unit": "USD", "answer_window": "quarter"},
                   {"source_entity": "fixture", "source_unit": "USD", "source_window": "quarter", "answer_unit": "percent", "answer_window": "year", "self_grade": 100}),
}


def _snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def _estate(root, output_class, variant):
    fresh=(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat()
    ledger="data/fixture_ledger/theses.jsonl"
    eid="engine/eval_fixture.py::eval-composition-fixture"
    art={"path":ledger,"format":"jsonl","producer":"engine/eval_fixture.py",
         "owner_program":"eval-composition-fixture","cadence":"daily-engine",
         "storage":"git","asof_field":"asof","freshness_sla_hours":24,
         "schema":"none","tier":"shadow","horizon_role":"context",
         "weights":"none","consumers":[]}
    doc={"meta":{"schema_version":1,"description":"synthetic class composition",
                 "tier_vocabulary":{},"article2_surfaces":[]},"artifacts":{"fixture":art}}
    files={"config/synapse.yml":yaml.safe_dump(doc),
           "config/intelligence_registry_overlay.yml":yaml.safe_dump({"schema_version":1,"engines":{eid:{"output_class":{"value":output_class,"rationale":"synthetic declared class"}}}}),
           "config/qual_ladder.yml":"families: {}\n",
           "engine/eval_fixture.py":"# Synthetic artifact owner; never executed.\n",
           ledger:json.dumps({"asof":fresh,"class_payload":CLASS_PAYLOADS[output_class][variant]})+"\n",
           "data/species/registry.json":json.dumps({"species":[{"species_id":"fixture-v1","validation_status":"validated","version":"1.0","market_scope":["US"],"evidence_stack":["retained fixture source reference"],"ledger_binding":{"ledger":ledger,"since":"2026-01-01","flip_criteria":"existing owner fixture criterion"}}]}),
           "data/qledger/claims.jsonl":""}
    for rel,value in files.items():
        target=root/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(value)
    return eid


@pytest.mark.parametrize("output_class", list(CLASS_PAYLOADS))
@pytest.mark.parametrize("variant", [0,1], ids=["valid-metadata-unqualified-metric", "adversarial-payload"])
def test_seven_class_real_panel_detail_composition(tmp_path, output_class, variant, record_property):
    root=tmp_path/"estate"
    eid=_estate(root,output_class,variant)
    before=_snapshot(root)
    IOS._CACHE.clear()
    panel=IOS.panel(root=root,force=True)
    detail=IOS.engine_detail(eid,root=root)
    assert panel["ok"] and detail["ok"]
    row=panel["engines"][0]
    assert row["output_class"]==output_class
    assert detail["engine"]["validation_state"]=="validated"
    assert row["evidence_status"]=="Accruing"
    assert "owner_validation_scope_unqualified" in row["evidence_reason_codes"]
    assert row["evidence_owner_scope"]["qualified_task_scope"] is None
    bound=row["evidence_owner_scope"]["bound_species"]
    assert bound[0]["species_id"]=="fixture-v1"
    assert bound[0]["owner_scope"]["version"]=="1.0"
    assert "species:fixture-v1" in row["evidence_refs"]
    assert row["evidence_provider"]["kind"]=="t1_owner_native"
    assert all(o["state"]=="healthy" and o["assessment_status"]=="complete" for o in detail["outputs"])
    for key in ("evidence_status","evidence_reason_codes","evidence_owner_scope","evidence_provider","evidence_ruler"):
        assert row[key]==detail["engine"][key]
    assert sum(b["n_engines"] for b in panel["ceo_view"])==1
    assert len(panel["ceo_view"])==5
    assert _snapshot(root)==before  # Actual reader never registers/promotes/writes a claim/clock.
    assert "class_payload" not in json.dumps({"panel":panel,"detail":detail})
    record_property("output_class",output_class)
    record_property("variant",variant)
    record_property("composition_acceptance","PASS: actual registry/health/provider/panel/detail")
    record_property("task_metric_acceptance","UNAVAILABLE: no qualified class owner adapter in current projection")
    IOS._CACHE.clear()


def test_ready_matched_owner_does_not_grant_panel_validation_or_write_authority(tmp_path, record_property, monkeypatch):
    """Real readiness positive control reaches the consumer, without task qualification.

    Reuses incumbent QLedger fixture constructors; registrar clocks exist solely
    under tmp_path before the no-write snapshot. No outcome or production access.
    """
    from engine import qledger as q, qledger_evidence_clock
    import importlib.util
    spec=importlib.util.spec_from_file_location("eval_os_incumbent_control_fixtures",
        Path(__file__).with_name("test_qledger_control_policy.py"))
    fixtures=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    _cohort,_write_store,_start_clock=fixtures._cohort,fixtures._write_store,fixtures._start_clock

    root=tmp_path/"estate"
    eid=_estate(root,"predictive",0)
    doc=yaml.safe_load((root/"config/synapse.yml").read_text())
    old_ledger=root/doc["artifacts"]["fixture"]["path"]
    new_ledger="data/stock_desk/theses.jsonl"
    target=root/new_ledger
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(old_ledger.read_bytes())
    old_ledger.unlink()
    doc["artifacts"]["fixture"]["path"]=new_ledger
    (root/"config/synapse.yml").write_text(yaml.safe_dump(doc))
    species=json.loads((root/"data/species/registry.json").read_text())
    species["species"][0]["ledger_binding"]["ledger"]=new_ledger
    (root/"data/species/registry.json").write_text(json.dumps(species))
    claims,grades=_cohort("stock_desk",30,controlled=30)
    _write_store(root,claims,grades)
    _start_clock(root,"stock_desk")
    qledger_evidence_clock.record_start("stock_desk",horizon_d=21,horizon_unit="trading_days",
        root=root,now="2025-01-01T00:00:00+00:00")
    assert q.promotion_check_dispatch("stock_desk",21,root=root).eligible
    # The accepted A1 reader consumes the owner artifact, never recomputes it.
    # Publish through the actual owner before the no-write boundary; suppress
    # only external alert delivery for this synthetic estate.
    from scripts import grade_qledger as grader
    (root/"site/qledger").mkdir(parents=True)
    monkeypatch.setattr(grader,"_fire_readiness_alert",lambda *_a,**_k: None)
    published=grader.run_readiness_post_step(root,len(grades),len(claims),today="2026-10-12")
    assert "error" not in published
    recorded=json.loads((root/"site/qledger/track_record.json").read_text())
    assert recorded["promotion_readiness"]["stock_desk"]["21"]["ready"] is True
    monkeypatch.setattr(grader,"compute_promotion_readiness",
                        lambda *_a,**_k: pytest.fail("the consumer must not recompute readiness"))
    before=_snapshot(root)
    IOS._CACHE.clear()
    panel=IOS.panel(root=root,force=True)
    detail=IOS.engine_detail(eid,root=root)
    assert panel["ok"] and detail["ok"]
    row=panel["engines"][0]
    assert row["evidence_provider"]["family"]=="stock_desk"
    assert row["evidence_provider"]["read_status"]=="partial"
    context=row["evidence_provider"]["recorded_snapshot"]
    assert context["available"] is True
    assert context["receipt_status"]=="recorded_provenance"
    assert context["current_source_qualification"]=="unavailable"
    assert row["evidence_ruler"]["selected_qledger_rung"]=="21"
    assert row["evidence_maturity"]["rungs"]["21"]["ready"] is True
    assert row["evidence_status"]=="Degraded"
    assert "owner_recorded_snapshot_current_unqualified" in row["evidence_reason_codes"]
    assert row["evidence_owner_scope"]["qualified_task_scope"] is None
    assert row["evidence_status"]==detail["engine"]["evidence_status"]
    assert _snapshot(root)==before
    record_property("advisory_readiness","PASS: actual matched-control ready owner")
    record_property("authority_effect","PASS: no owner validation/promotion/clock/financial writes")
    IOS._CACHE.clear()


# Actual incumbent offline-owner dispatch, separate from the A1 visibility guards.
_MEASUREMENT_IDS = [f"{cls}-{kind}" for cls in CLASS_PAYLOADS for kind in ("valid", "adversarial")] + [
    "quantile-valid", "quantile-adversarial"]


def _measurement_document():
    from engine.neuralweb import response_eval
    return response_eval.load_benchmark("benchmark_eval_os_measurement_v1.json")


def _measurement_case(case_id):
    return next(c for c in _measurement_document()["cases"] if c["id"] == case_id)


@pytest.mark.parametrize("case_id", _MEASUREMENT_IDS)
def test_incumbent_offline_owner_dispatch_consumes_payload(case_id, record_property):
    from engine.neuralweb import response_eval
    case = _measurement_case(case_id)
    observed = response_eval.measurement_contract_checks(case)
    expected = case["expected"]
    assert observed["accepted"] is expected["accepted"]
    assert observed["reason"] == expected["reason"]
    assert observed["internal_qa_only"] is True
    assert observed["outcome_access_allowed"] is False
    assert observed["measurements"].keys() == expected["measurements"].keys()
    for key, value in expected["measurements"].items():
        if isinstance(value, float):
            assert observed["measurements"][key] == pytest.approx(value, abs=1e-12)
        else:
            assert observed["measurements"][key] == value
    record_property("reported_contract_acceptance", "actual payload consumed by incumbent internal QA owner")
    record_property("case_id", case_id)
    record_property("empirical_outcome_acceptance", "not granted")


def test_frozen_measurement_runner_uses_no_judge_or_model(monkeypatch):
    from engine.neuralweb import response_eval
    def forbidden(*args, **kwargs):
        raise AssertionError("deterministic acceptance must not call a model")
    monkeypatch.setattr(response_eval, "judge_via_llm_auth", forbidden)
    monkeypatch.setattr(response_eval, "answer_via_llm_auth", forbidden)
    result = response_eval.run_measurement_acceptance_cases()
    assert result["ok"] and len(result["cases"]) == 16
    assert all(c["agrees_with_oracle"] for c in result["cases"])
    assert result["outcome_access_allowed"] is False


@pytest.mark.parametrize("field", ["expected", "contract", "population", "output_class"])
def test_frozen_measurement_runner_cannot_launder_reference_changes(field):
    from engine.neuralweb import response_eval
    doc = _measurement_document()
    if field == "expected":
        doc["cases"][0]["expected"]["measurements"]["brier"] = 100
    elif field == "contract":
        doc["cases"][0]["contract"]["target_id"] = "another-target"
    elif field == "output_class":
        next(c for c in doc["cases"] if c["id"] == "descriptive-adversarial")["output_class"] = "generative"
    else:
        doc["cases"].pop()
    assert response_eval.run_measurement_acceptance_cases(doc)["ok"] is False


def test_ranking_missing_member_retains_intended_population():
    from engine.neuralweb import response_eval
    case = _measurement_case("ranking-valid")
    case["class_payload"].update(ranking=["A", "C"], missing=["B"])
    result = response_eval.measurement_contract_checks(case)
    assert result["accepted"]
    assert result["measurements"] == {"precision_at_k": 1.0, "coverage": 2 / 3, "eligible_n": 3}
    case["class_payload"]["missing"] = []
    assert response_eval.measurement_contract_checks(case)["reason"] == "ranking_population_mismatch"


def test_state_truth_cannot_be_a_future_return_proxy():
    from engine.neuralweb import response_eval
    case = _measurement_case("classification_state-valid")
    case["class_payload"]["truth_source"] = "future_return_proxy"
    assert response_eval.measurement_contract_checks(case)["reason"] == "state_label_source_mismatch"


def test_detector_expiry_misses_and_false_burden_do_not_disappear():
    from engine.neuralweb import response_eval
    case = _measurement_case("detection_event-valid")
    case["class_payload"]["matches"] = []
    result = response_eval.measurement_contract_checks(case)
    assert result["accepted"]
    assert result["measurements"] == {"matched": 0, "missed": 2, "false_alarms": 2,
        "false_alarm_rate": .02, "mean_lead": None}
    case["class_payload"]["matches"] = [["a1", "e2"]]
    assert response_eval.measurement_contract_checks(case)["reason"] == "event_match_outside_window"


def test_same_contract_contradiction_differs_from_cross_horizon_tension():
    from engine.neuralweb import response_eval
    case = _measurement_case("generative-valid")
    assert response_eval.measurement_contract_checks(case)["measurements"]["legitimate_scope_differences"] == 1
    case["class_payload"]["readings"][1]["window"] = 5
    assert response_eval.measurement_contract_checks(case)["reason"] == "same_contract_contradiction"
    case = _measurement_case("generative-valid")
    case["class_payload"]["self_grade"] = 100
    assert response_eval.measurement_contract_checks(case)["reason"] == "self_grading_forbidden"


def test_probability_target_and_quantile_units_remain_exact():
    from engine.neuralweb import response_eval
    case = _measurement_case("predictive-valid")
    case["class_payload"]["horizon_d"] = 63
    assert response_eval.measurement_contract_checks(case)["reason"] == "predictive_target_mismatch"
    case = _measurement_case("quantile-valid")
    case["class_payload"]["unit"] = "future_minimum_price"
    assert response_eval.measurement_contract_checks(case)["reason"] == "predictive_target_mismatch"


def test_duplicate_overlap_and_research_looks_are_separate():
    from copy import deepcopy
    from engine.neuralweb import response_eval
    frozen = _measurement_document()["protocol"]
    candidate = deepcopy(frozen)
    candidate["observations"].append(deepcopy(candidate["observations"][0]))
    candidate["observations"].append({"id": "o4", "block_id": "pretended-new-block", "start": 8, "end": 12})
    result = response_eval.validate_measurement_acceptance_protocol(candidate, frozen)
    assert result["accepted"]
    assert result["observation_rows"] == 5 and result["distinct_observations"] == 4
    assert result["independent_blocks"] == 2
    assert result["trial_count"] == 2 and result["look_count"] == 3
    assert result["contaminated_holdouts"] == ["synthetic-H1"]
    assert result["outcome_access_allowed"] is False


@pytest.mark.parametrize("mutation,expected", [
    ("inflate_blocks", "protocol_independent_count_inflated"),
    ("too_many_trials", "protocol_research_budget_exceeded"),
    ("too_many_looks", "protocol_research_budget_exceeded"),
    ("erase_trials", "protocol_research_history_erased"),
    ("erase_contamination", "protocol_contamination_erased"),
    ("erase_inspection", "protocol_inspection_erased"),
    ("change_primary", "protocol_frozen_term_changed:primary_target"),
    ("claim_outcome_access", "protocol_scope_forbidden"),
    ("fake_empirical_power", "protocol_frozen_term_changed:power_rule"),
    ("boolean_margin", "protocol_frozen_term_changed:practical_margin"),
    ("occurrence_collision", "protocol_occurrence_collision"),
    ("unbounded_rows", "protocol_observation_budget_exceeded"),
    ("erase_observations", "protocol_frozen_observation_changed"),
    ("rewrite_observation", "protocol_frozen_observation_changed"),
])
def test_finite_protocol_mutants_fail_for_the_intended_reason(mutation, expected):
    from copy import deepcopy
    from engine.neuralweb import response_eval
    frozen = _measurement_document()["protocol"]
    candidate = deepcopy(frozen)
    if mutation == "inflate_blocks": candidate["declared_independent_blocks"] = 5
    elif mutation == "too_many_trials": candidate["trial_ids"].append("fixture-c")
    elif mutation == "too_many_looks": candidate["look_ids"].append("look-4")
    elif mutation == "erase_trials": candidate["trial_ids"] = ["fixture-a"]
    elif mutation == "erase_contamination": candidate["contaminated_holdout_ids"] = []
    elif mutation == "erase_inspection": candidate["inspected_holdout_ids"] = []
    elif mutation == "change_primary": candidate["primary_target"] = "changed after looking"
    elif mutation == "claim_outcome_access": candidate["outcome_access_allowed"] = True
    elif mutation == "fake_empirical_power": candidate["power_rule"] = "100 rows imply 80% power"
    elif mutation == "boolean_margin": candidate["practical_margin"] = False
    elif mutation == "occurrence_collision": candidate["observations"].append(dict(candidate["observations"][0], end=11))
    elif mutation == "erase_observations":
        candidate["observations"] = candidate["observations"][:1]
        candidate["declared_independent_blocks"] = 1
    elif mutation == "rewrite_observation":
        candidate["observations"][1].update(start=16, end=20, block_id="b3")
        candidate["declared_independent_blocks"] = 3
    else: candidate["observations"] *= 6
    result = response_eval.validate_measurement_acceptance_protocol(candidate, frozen)
    assert result["accepted"] is False
    assert result["reason"] == expected
    assert result["outcome_access_allowed"] is False


@pytest.mark.parametrize("mutation", ["unmatched_event", "unmatched_alarm", "negative_alarm_window"])
def test_all_detector_records_have_valid_times_even_when_unmatched(mutation):
    from engine.neuralweb import response_eval
    case = _measurement_case("detection_event-valid")
    if mutation == "unmatched_event": case["class_payload"]["events"][1]["at"] = None
    elif mutation == "unmatched_alarm": case["class_payload"]["alarms"][1]["at"] = None
    else: case["class_payload"]["alarms"][1]["expires"] = 29
    assert response_eval.measurement_contract_checks(case)["accepted"] is False


@pytest.mark.parametrize("mutation", ["unknown_generator", "duplicate_population"])
def test_salience_independence_and_population_are_declared(mutation):
    from engine.neuralweb import response_eval
    case = _measurement_case("salience-valid")
    if mutation == "unknown_generator": case["class_payload"]["generator"] = None
    else: case["class_payload"]["eligible"].append("A")
    assert response_eval.measurement_contract_checks(case)["accepted"] is False


def test_future_known_ranking_universe_cannot_supply_pit_support():
    from engine.neuralweb import response_eval
    case = _measurement_case("ranking-valid")
    case["class_payload"]["eligible_known_at"] = 11
    assert response_eval.measurement_contract_checks(case)["reason"] == "ranking_population_not_known"


def test_a_single_reading_requires_complete_scope_without_a_pair():
    from engine.neuralweb import response_eval
    case = _measurement_case("generative-valid")
    case["class_payload"]["readings"] = [{"value": 1, "target_id": "synthetic_return", "unit": "percent"}]
    assert response_eval.measurement_contract_checks(case)["accepted"] is False
