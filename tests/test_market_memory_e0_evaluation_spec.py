"""Synthetic declarations only; no annotations, financial labels or study run."""
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory import market_memory_e0_evaluation_spec as evaluation
from engine.research_factory import market_memory_evidence_accounting as accounting
from tests.test_market_memory_e0_control_records import (
    bundle, canonical, records, reference, reviewer_bundle, task_bundle,
)


@pytest.fixture
def declarations(reviewer_bundle):
    original, plan = reviewer_bundle
    reg = copy.deepcopy(original[0])
    common = {"authority": "display_only", "study_id": reg["study_id"],
              "protocol_sha256": control._FROZEN_DOMAIN_DIGESTS["design"],
              "membership_sha256": reg["corpus"]["membership_sha256"],
              "annotation_guide_sha256": control._FROZEN_DOMAIN_DIGESTS["annotation_guide"],
              "tasks_ref": copy.deepcopy(reg["tasks_ref"]),
              "reviewer_plan_ref": copy.deepcopy(reg["reviewer_plan_ref"])}
    outcome = {**common, "schema": evaluation.SCHEMAS["outcome_definition_ref"],
        "object_id": "synthetic-outcome-definition", "access_rules_ref": reg["access_rules_ref"],
        "hypotheses": ["H1", "H2"], "annotation_scope": "permitted_decision_time_evidence",
        "financial_forward_outcomes_enabled": False,
        "financial_label_horizon": "not_applicable_H3_disabled",
        "annotation_exposure_span": "not_established", "later_outcomes_as_then_known_support": False,
        "citation_validity_implies_entailment": False,
        "guide_scope_dispositions": ["supported_original_house_output", "supported_registered_comparison",
            "requires_missing_exact_source_or_clock", "requires_unavailable_or_immature_outcome",
            "unsupported_causal_or_forecast_request"],
        "accounting_answerability": list(accounting.ANSWERABILITY),
        "material_claim_verdicts": list(accounting.VERDICTS),
        "relevance_ordinals": [0, 1, 2], "primary_relevance_ordinal": 2}
    reg["outcome_definition_ref"] = reference(canonical(outcome), outcome["schema"], outcome["object_id"])
    metrics = {**common, "schema": evaluation.SCHEMAS["metrics_ref"], "object_id": "synthetic-metrics",
        "outcome_definition_ref": copy.deepcopy(reg["outcome_definition_ref"]),
        "accounting_source_ref": copy.deepcopy(evaluation.ACCOUNTING_SOURCE_REF),
        "accounting_input_schema": accounting.INPUT_SCHEMA, "accounting_output_schema": accounting.OUTPUT_SCHEMA,
        "conditions": list(accounting.CONDITIONS), "observation_states": list(accounting.STATES),
        "maximum_k": 8, "margin_encoding": "exact_decimal_proportions.v1",
        "material_support_precision_floor": "0.95", "paired_relevance_gain_floor": "0.10",
        "paired_relevance_contrast": ["fixed_l1", "recency"],
        "paired_relevance_clustered_lower_bound": "strictly_greater_than_zero",
        "support_difference_clustered_lower_bound_floor": "-0.02", "confidence_level": "0.95",
        "primary_unit": "query_task_nested_in_economic_episode",
        "inference_requires_qualified_clusters_and_estimator": True,
        "insufficient_evidence_when_unqualified": True,
        "critical_unsupported_claim_blocks_positive": True,
        "preserve_all_registered_tasks": True, "secondary_utility_after_correctness": True}
    return reg, metrics, outcome, original, plan


def validate(value, role, reg):
    return evaluation.validate_declaration(value, canonical(value), role=role, registration=reg)


def test_frozen_declarations_match_real_protocol_guide_and_existing_accounting_source(declarations):
    reg, metrics, outcome, original, plan = declarations
    for role, value in (("metrics_ref", metrics), ("outcome_definition_ref", outcome)):
        assert validate(value, role, reg) == value
    protocol = json.loads(original[1][control._FROZEN_DOMAIN_DIGESTS["design"]], parse_float=Decimal)
    margins = protocol["proposed_decision_margins"]
    assert Decimal(metrics["material_support_precision_floor"]) == margins["material_support_precision_floor"]
    assert Decimal(metrics["paired_relevance_gain_floor"]) == margins["retrieval_relevance_minimum_absolute_paired_gain_vs_recency"]
    assert Decimal(metrics["support_difference_clustered_lower_bound_floor"]) == Decimal("-0.02")
    assert "-0.02" in margins["support_noninferiority"]
    assert "95%" in margins["positive_gain_confidence_rule"]
    source = Path(accounting.__file__).read_bytes()
    assert len(source) == evaluation.ACCOUNTING_SOURCE_REF["bytes"]
    assert hashlib.sha256(source).hexdigest() == evaluation.ACCOUNTING_SOURCE_REF["sha256"]
    guide = original[1][control._FROZEN_DOMAIN_DIGESTS["annotation_guide"]].decode()
    assert all(name in guide for name in outcome["guide_scope_dispositions"])


@pytest.mark.parametrize("role,field,value", [
    ("metrics_ref", "material_support_precision_floor", "0.94"),
    ("metrics_ref", "paired_relevance_gain_floor", "0.09"),
    ("metrics_ref", "support_difference_clustered_lower_bound_floor", "-0.03"),
    ("metrics_ref", "confidence_level", "0.90"),
    ("metrics_ref", "critical_unsupported_claim_blocks_positive", False),
    ("metrics_ref", "preserve_all_registered_tasks", False),
    ("metrics_ref", "maximum_k", 9),
    ("metrics_ref", "conditions", ["recency", "fixed_l1"]),
    ("metrics_ref", "observation_states", ["answered", "abstained"]),
    ("metrics_ref", "observations", []),
    ("metrics_ref", "estimator", "invented-cluster-estimator"),
    ("metrics_ref", "confidence_interval", [0.1, 0.2]),
    ("metrics_ref", "acceptance_verdict", "PASS"),
    ("outcome_definition_ref", "financial_forward_outcomes_enabled", True),
    ("outcome_definition_ref", "hypotheses", ["H1", "H2", "H3"]),
    ("outcome_definition_ref", "annotation_exposure_span", "not_applicable"),
    ("outcome_definition_ref", "later_outcomes_as_then_known_support", True),
    ("outcome_definition_ref", "citation_validity_implies_entailment", True),
    ("outcome_definition_ref", "actual_annotations", []),
    ("outcome_definition_ref", "financial_price_horizon_days", 5),
])
def test_declarations_cannot_weaken_frozen_criteria_or_introduce_labels_results_or_activation(declarations, role, field, value):
    reg, metrics, outcome, _, _ = declarations
    target = metrics if role == "metrics_ref" else outcome
    target[field] = value
    with pytest.raises(control.E0ControlError, match="schema_violation"):
        validate(target, role, reg)


@pytest.mark.parametrize("field", ["study_id", "tasks_ref", "reviewer_plan_ref", "outcome_definition_ref"])
def test_metrics_bind_exact_existing_registration_roles(declarations, field):
    reg, metrics, _, _, _ = declarations
    metrics[field] = "another-study" if field == "study_id" else reference(b"another exact object")
    with pytest.raises(control.E0ControlError, match="registration_mismatch|outcome_or_accounting"):
        validate(metrics, "metrics_ref", reg)


@pytest.mark.parametrize("mutation", [lambda x: x.update(tasks_ref="unbounded-name"),
    lambda x: x["tasks_ref"].update(bytes=True),
    lambda x: x["reviewer_plan_ref"].update(object_id="x" * 129),
    lambda x: x["accounting_source_ref"].update(sha256="0" * 64)])
def test_bound_references_are_exact_and_accounting_source_version_is_not_substitutable(declarations, mutation):
    reg, metrics, _, _, _ = declarations
    mutation(metrics)
    with pytest.raises(control.E0ControlError, match="schema_violation"):
        validate(metrics, "metrics_ref", reg)


def test_h3_nonapplicability_never_becomes_annotation_timing_or_l0_coverage(declarations):
    reg, _, outcome, original, plan = declarations
    value = validate(outcome, "outcome_definition_ref", reg)
    result = evaluation.binding_checks(value, role="outcome_definition_ref", tasks={}, reviewer_plan=plan,
        outcome_definition=value, resolved_digests=set(original[1]))
    assert result["financial_horizon_nonapplicability_scope"] == "H3_disabled_only"
    assert result["annotation_exposure_span"] == "not_established"
    assert result["label_interval_coverage"] == "not_established"
    assert result["l0_financial_outcome_coverage"] == "not_established"
    assert result["annotation_exposure_history_verified"] is False
    assert result["actual_annotations_observed"] is False
    assert result["financial_outcome_access_granted"] is False
    assert result["operational_admission"] is False


def test_metrics_no_estimator_execution_or_inference_and_missing_bytes_stay_unknown(declarations, monkeypatch):
    reg, metrics, outcome, original, plan = declarations
    value = validate(metrics, "metrics_ref", reg)
    monkeypatch.setattr(accounting, "summarize_evidence_accounting",
        lambda *a, **k: pytest.fail("declaration validation must not score observations"))
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("unexpected source/store I/O"))
    result = evaluation.binding_checks(value, role="metrics_ref", tasks=None, reviewer_plan=None,
        outcome_definition=None, resolved_digests=set())
    assert {"exact_task_manifest_bytes", "declared_reviewer_plan_bytes", "outcome_definition_semantics",
            "exact_descriptive_accounting_source_bytes", "frozen_annotation_guide_bytes"} <= set(result["unresolved"])
    for key in ("inferential_estimator_qualified", "confidence_intervals_computed", "effective_n_estimated",
                "acceptance_verdict_emitted", "operational_admission",
                "all_declared_metric_computations_implemented",
                "critical_unsupported_claim_joint_scoring_qualified"):
        assert result[key] is False
    assert "qualified_critical_unsupported_claim_joint_scoring" in result["unresolved"]
    result["declared_margin_values"].clear()
    assert evaluation.binding_checks(value, role="metrics_ref", tasks={}, reviewer_plan=plan,
        outcome_definition=outcome, resolved_digests=set(original[1]))["declared_margin_values"]


def test_canonical_bytes_and_declared_schema_role_are_not_interchangeable(declarations):
    reg, metrics, outcome, _, _ = declarations
    with pytest.raises(control.E0ControlError, match="noncanonical"):
        evaluation.validate_declaration(metrics, canonical(metrics) + b"\n", role="metrics_ref", registration=reg)
    with pytest.raises(control.E0ControlError, match="schema_role_mismatch"):
        validate(outcome, "metrics_ref", reg)


def evaluation_bundle(declarations):
    reg, metrics, outcome, original, _ = declarations
    objects = dict(original[1])
    for role in ("metrics_ref", "outcome_definition_ref"):
        objects.pop(original[0][role]["sha256"])
        value = metrics if role == "metrics_ref" else outcome
        body = canonical(value)
        reg[role] = reference(body, value["schema"], value["object_id"])
        objects[reg[role]["sha256"]] = body
    objects[evaluation.ACCOUNTING_SOURCE_REF["sha256"]] = Path(accounting.__file__).read_bytes()
    return reg, objects, original[2]


def resolve_evaluation(prepared):
    reg, objects, prelabel = prepared
    return control.resolve_e0_domain_references(registration=reg, objects=objects, prelabel_design=prelabel)


def test_resolver_binds_real_public_source_guide_and_declarations_without_metric_truth(declarations):
    result = resolve_evaluation(evaluation_bundle(declarations))
    assert result["references_complete"] is True
    checks = {row["schema"]: row for row in result["evaluation_binding_checks"]}
    metrics = checks[evaluation.SCHEMAS["metrics_ref"]]
    assert metrics["accounting_source_bytes_bound"] is True
    assert metrics["outcome_definition_semantics_bound"] is True
    assert metrics["all_declared_metric_computations_implemented"] is False
    assert metrics["critical_unsupported_claim_joint_scoring_qualified"] is False
    assert all(row["frozen_annotation_guide_bytes_bound"] for row in checks.values())
    assert all(row["operational_admission"] is False for row in checks.values())
    assert result["domain_metadata_complete"] is result["operational_admission"] is False


@pytest.mark.parametrize("role", ["metrics_ref", "outcome_definition_ref"])
def test_evaluation_schema_role_contradiction_precedes_missing_bytes(declarations, role):
    reg, objects, prelabel = evaluation_bundle(declarations)
    other = "outcome_definition_ref" if role == "metrics_ref" else "metrics_ref"
    reg[role] = copy.deepcopy(reg[other])
    objects.clear()
    with pytest.raises(control.E0ControlError, match="evaluation_declaration_reference_role_mismatch"):
        resolve_evaluation((reg, objects, prelabel))


@pytest.mark.parametrize("missing,obligation", [
    ("accounting", "exact_descriptive_accounting_source_bytes"),
    ("outcome", "outcome_definition_semantics"),
    ("guide", "frozen_annotation_guide_bytes"),
])
def test_missing_evaluation_dependencies_remain_explicit_and_never_execute(declarations, missing, obligation):
    reg, objects, prelabel = evaluation_bundle(declarations)
    digest = (evaluation.ACCOUNTING_SOURCE_REF["sha256"] if missing == "accounting" else
              reg["outcome_definition_ref"]["sha256"] if missing == "outcome" else
              control._FROZEN_DOMAIN_DIGESTS["annotation_guide"])
    del objects[digest]
    result = resolve_evaluation((reg, objects, prelabel))
    assert result["references_complete"] is False
    metrics = next(row for row in result["evaluation_binding_checks"]
                   if row["schema"] == evaluation.SCHEMAS["metrics_ref"])
    assert obligation in metrics["unresolved"]
    assert metrics["acceptance_verdict_emitted"] is metrics["operational_admission"] is False
