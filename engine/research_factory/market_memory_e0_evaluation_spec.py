"""Frozen H1/H2 declaration bindings, never annotation or an inference engine.

Financial forward-outcome horizons are disabled by the frozen H3 decision.
Actual annotation/exposure time is a different obligation and remains unknown.
Byte-bound criteria cannot authenticate reviewers, labels, clusters or source
coverage, and cannot make the existing descriptive reducer a study verdict.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from . import market_memory_contextual_registration as control


SCHEMAS = {
    "metrics_ref": "research_factory.market_memory_e0_metrics.v1",
    "outcome_definition_ref": "research_factory.market_memory_e0_outcome_definition.v1",
}
ACCOUNTING_SOURCE_REF = {
    "schema": "python.source.v1", "object_id": "market_memory_evidence_accounting_py",
    "sha256": "e809fb094baeaab6ec5686ae9f51f0ffe41f7978ed8e8205aacc81bef17e7baf",
    "bytes": 26812,
}


@lru_cache(maxsize=1)
def _validator():
    path = Path(__file__).resolve().parents[2] / "contracts" / "market_memory" / "e0_evaluation_spec.v1.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return control._INTEGER_VALIDATOR(schema)


def validate_declaration(value: object, body: bytes, *, role: str, registration: dict) -> dict:
    """Return detached declarations; the fixed margins are not observed scores."""
    if role not in SCHEMAS:
        raise control.E0ControlError("evaluation_declaration_role_required")
    declared, canonical = control._domain_snapshot(value)
    if declared.get("schema") != SCHEMAS[role]:
        raise control.E0ControlError("evaluation_declaration_schema_role_mismatch")
    if next(_validator().iter_errors(declared), None) is not None:
        raise control.E0ControlError("evaluation_declaration_schema_violation")
    if body != canonical:
        raise control.E0ControlError("noncanonical_evaluation_declaration_bytes")
    if (declared["study_id"] != registration["study_id"]
            or declared["protocol_sha256"] != registration["design_ref"]["sha256"]
            or declared["membership_sha256"] != registration["corpus"]["membership_sha256"]
            or declared["tasks_ref"] != registration["tasks_ref"]
            or declared["reviewer_plan_ref"] != registration["reviewer_plan_ref"]):
        raise control.E0ControlError("evaluation_declaration_registration_mismatch")
    if role == "metrics_ref":
        if (declared["outcome_definition_ref"] != registration["outcome_definition_ref"]
                or declared["accounting_source_ref"] != ACCOUNTING_SOURCE_REF):
            raise control.E0ControlError("metrics_outcome_or_accounting_source_mismatch")
    elif declared["access_rules_ref"] != registration["access_rules_ref"]:
        raise control.E0ControlError("outcome_access_rules_reference_mismatch")
    return declared


def provenance_references(declared: dict, *, role: str) -> list[tuple[str, dict]]:
    # Task/reviewer/outcome/access references already are registration roots.
    # Only this one extra immutable public source reference is followed.
    return [("metrics.accounting_source_ref", declared["accounting_source_ref"])] if role == "metrics_ref" else []


def binding_checks(declared: dict, *, role: str, tasks: dict | None,
                   reviewer_plan: dict | None, outcome_definition: dict | None,
                   resolved_digests: set[str]) -> dict:
    unresolved = []
    if tasks is None:
        unresolved.append("exact_task_manifest_bytes")
    if reviewer_plan is None:
        unresolved.append("declared_reviewer_plan_bytes")
    guide_bound = control._FROZEN_DOMAIN_DIGESTS["annotation_guide"] in resolved_digests
    if not guide_bound:
        unresolved.append("frozen_annotation_guide_bytes")
    result = {"schema": declared["schema"], "object_id": declared["object_id"],
              "exact_task_manifest_bytes_bound": tasks is not None,
              "declared_reviewer_plan_bytes_bound": reviewer_plan is not None,
              "frozen_annotation_guide_bytes_bound": guide_bound,
              "actual_annotations_observed": False,
              "annotation_exposure_history_verified": False,
              "inferential_estimator_qualified": False,
              "confidence_intervals_computed": False, "effective_n_estimated": False,
              "acceptance_verdict_emitted": False, "operational_admission": False}
    if role == "metrics_ref":
        source_bound = ACCOUNTING_SOURCE_REF["sha256"] in resolved_digests
        if not source_bound:
            unresolved.append("exact_descriptive_accounting_source_bytes")
        if outcome_definition is None:
            unresolved.append("outcome_definition_semantics")
        unresolved.append("qualified_critical_unsupported_claim_joint_scoring")
        result.update(accounting_source_bytes_bound=source_bound,
            all_declared_metric_computations_implemented=False,
            critical_unsupported_claim_joint_scoring_qualified=False,
            outcome_definition_semantics_bound=outcome_definition is not None,
            criteria_scope="frozen_declarations_not_observed_metrics",
            declared_margin_values={key: declared[key] for key in (
                "material_support_precision_floor", "paired_relevance_gain_floor",
                "support_difference_clustered_lower_bound_floor", "confidence_level")})
    else:
        result.update(financial_horizon_nonapplicability_scope="H3_disabled_only",
            financial_outcome_access_granted=False,
            annotation_exposure_span="not_established",
            label_interval_coverage="not_established",
            l0_financial_outcome_coverage="not_established")
    # A complete declaration must not disguise the actual evidence obligations.
    unresolved.extend(("authenticated_annotation_exposure_history",
                       "actual_independent_ratings_and_source_support",
                       "qualified_genuine_clusters_and_inferential_estimator"))
    result["unresolved"] = unresolved
    return result
