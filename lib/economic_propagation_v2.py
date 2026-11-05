"""K3-D v2 compiler-owned qualitative narrative; same native owner and validators.

Legacy v1 remains in economic_propagation. No record migration, new graph/store,
identity allocation, source admission, forecast or trading authority occurs here.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from typing import Any
from jsonschema import Draft202012Validator
from lib.economic_propagation import (
    EconomicPropagationError, Finding, SCHEMA_ID, _CONTRACT_DIR, _f,
    compose_hypothesis, validate_hypothesis, content_sha256,
    derive_record_id, derive_target_identity_component,
)


# ---------------------------------------------------------------------------
# V2 candidate — compiler-owned qualitative narrative.
# This is a versioned consumer construction, not native evidence admission.
# The existing v1 implementation and persisted v1 records remain unchanged.
# ---------------------------------------------------------------------------

_V2_SCHEMA_ID = "economic_propagation.propagation_hypothesis/v2"
_V2_PROFILE = "compiler_owned_qualitative.v2"
_V2_MAX_BYTES = 256 * 1024
_V2_METRICS = {
    "revenue": "revenue", "volume": "operating volume", "pricing": "realized pricing",
    "gross_margin": "gross margin", "operating_margin": "operating margin",
    "backlog_orders": "order backlog", "capacity_utilization": "capacity utilization",
    "input_cost": "input costs", "market_share": "market share",
}
# Antecedent polarity is supplied independently of the proposed target outcome.
# These are conditional scenarios, not a finding that the antecedent occurred.
_V2_ANTECEDENTS = {
    "demand_transfer": {
        "toward_target": "demand shifts toward the target",
        "away_from_target": "demand shifts away from the target",
    },
    "supply_constraint": {
        "tightens": "qualified supply available to the target tightens",
        "eases": "qualified supply available to the target eases",
    },
    "pricing_power_shift": {
        "strengthens": "the target's pricing power strengthens",
        "weakens": "the target's pricing power weakens",
    },
    "input_cost_shift": {
        "increases": "the cost of inputs used by the target increases",
        "decreases": "the cost of inputs used by the target decreases",
    },
    "capacity_reallocation": {
        "toward_target": "operating capacity is reallocated toward the target",
        "away_from_target": "operating capacity is reallocated away from the target",
    },
    "share_shift_competitive": {
        "toward_target": "competitive business share shifts toward the target",
        "away_from_target": "competitive business share shifts away from the target",
    },
    "regulatory_exposure": {
        "tightens": "restrictions applicable to the target tighten",
        "eases": "restrictions applicable to the target ease",
    },
    "program_funding_flow": {
        "increases": "funding for the target's program increases",
        "decreases": "funding for the target's program decreases",
    },
    "common_end_market_demand": {
        "increases": "demand in the target's shared end market increases",
        "decreases": "demand in the target's shared end market decreases",
    },
}
_V2_ALLOWED_METRICS = {
    "demand_transfer": ("revenue", "volume", "backlog_orders", "capacity_utilization"),
    "supply_constraint": ("volume", "capacity_utilization", "gross_margin", "operating_margin", "input_cost", "revenue"),
    "pricing_power_shift": ("pricing", "gross_margin", "operating_margin", "market_share"),
    "input_cost_shift": ("input_cost", "gross_margin", "operating_margin"),
    "capacity_reallocation": ("volume", "capacity_utilization", "backlog_orders", "revenue"),
    "share_shift_competitive": ("market_share", "volume", "revenue"),
    "regulatory_exposure": ("volume", "revenue", "gross_margin", "operating_margin", "input_cost"),
    "program_funding_flow": ("backlog_orders", "revenue", "volume"),
    "common_end_market_demand": ("volume", "revenue", "pricing", "backlog_orders", "capacity_utilization"),
}
_V2_ALT_TEXT = {
    "common_cause_macro": "A shared macroeconomic driver could explain the observation without a transfer between the businesses.",
    "sector_factor": "A shared industry driver could explain the observation without a transfer between the businesses.",
    "narrative_similarity_only": "Similar operating descriptions may explain the association without an economic transfer.",
    "market_sympathy_only": "Market co-movement may explain the association without an economic transfer.",
    "liquidity_flow_technical": "Market liquidity and positioning may explain the observation without operating transmission.",
    "coincident_timing": "Coincident timing may explain the observation without an economic transfer.",
}
_V2_EXPIRY_NOTE = (
    "Reassess with native-owner evidence eligible at the next query cutoff; "
    "later information does not rewrite this record."
)


def _v2_snapshot(value: Any) -> Any:
    """Bounded copy of exact JSON types; no hooks, arbitrary objects or coercion."""
    active: set[int] = set()
    count = 0

    def visit(node: Any, depth: int) -> Any:
        nonlocal count
        count += 1
        if count > 7000 or depth > 20:
            raise EconomicPropagationError("K3D_V2_JSON_BOUND")
        kind = type(node)
        if node is None or kind is bool:
            return node
        if kind is str:
            if len(node) > 4096:
                raise EconomicPropagationError("K3D_V2_JSON_BOUND")
            return node
        if kind is int and -(2**63) <= node < 2**63:
            return node
        if kind not in (dict, list):
            raise EconomicPropagationError("K3D_V2_JSON_TYPE")
        marker = id(node)
        if marker in active:
            raise EconomicPropagationError("K3D_V2_JSON_CYCLE")
        active.add(marker)
        try:
            if kind is list:
                return [visit(item, depth + 1) for item in node]
            result = {}
            for key, item in node.items():
                if type(key) is not str or len(key) > 100:
                    raise EconomicPropagationError("K3D_V2_JSON_KEY")
                result[key] = visit(item, depth + 1)
            return result
        finally:
            active.remove(marker)

    result = visit(value, 0)
    try:
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise EconomicPropagationError("K3D_V2_JSON_ENCODING") from exc
    if len(encoded) > _V2_MAX_BYTES:
        raise EconomicPropagationError("K3D_V2_JSON_BOUND")
    return result


def _v2_spec(spec: Any) -> dict | None:
    if spec is None:
        return None
    keys = {"mechanism_class", "mechanism_polarity", "predicted_operating_direction", "operating_metric_class"}
    if type(spec) is not dict or set(spec) != keys or any(type(v) is not str for v in spec.values()):
        raise EconomicPropagationError("K3D_V2_MECHANISM_SPEC")
    mechanism = spec["mechanism_class"]
    if (mechanism not in _V2_ALLOWED_METRICS
            or spec["operating_metric_class"] not in _V2_ALLOWED_METRICS[mechanism]
            or spec["predicted_operating_direction"] not in ("improves", "deteriorates")
            or spec["mechanism_polarity"] not in _V2_ANTECEDENTS[mechanism]):
        raise EconomicPropagationError("K3D_V2_UNSUPPORTED_COMBINATION")
    return dict(spec)


def _v2_classes(classes: Any) -> list[str]:
    if (type(classes) not in (list, tuple) or not 1 <= len(classes) <= 6
            or any(type(item) is not str or item not in _V2_ALT_TEXT for item in classes)):
        raise EconomicPropagationError("K3D_V2_ALTERNATIVE_CLASSES")
    if len(set(classes)) != len(classes):
        raise EconomicPropagationError("K3D_V2_ALTERNATIVE_CLASSES")
    return sorted(classes)


def _v2_calendar_date(value: Any) -> None:
    # Syntax/calendar validation only; NOT a new PIT or source-availability clock.
    import datetime
    if type(value) is not str or len(value) != 10:
        raise EconomicPropagationError("K3D_V2_DATE")
    try:
        if datetime.date.fromisoformat(value).isoformat() != value:
            raise ValueError("not canonical")
    except ValueError as exc:
        raise EconomicPropagationError("K3D_V2_DATE") from exc


# This record defines a test; it does not register, run or grade that test.
_V2_EVALUATION_REQUIREMENTS = [
    "native_owner_confirmed_antecedent_occurrence",
    "applicable_role_specific_relationship",
    "preregistered_metric_scope_and_comparable_baseline",
    "preregistered_event_window_outcome_lag_and_window",
    "preregistered_rejection_rule_and_uncertainty_handling",
    "sufficient_purpose_eligible_comparable_outcome_observations",
]
_V2_NONTEST_CONDITIONS = (
    ("antecedent_not_observed",
     "The specified antecedent did not occur or its occurrence is not established.",
     "The conditional claim is untested, not falsified."),
    ("relationship_inapplicable",
     "The evidenced relationship is invalid or inapplicable to the proposed test.",
     "The test is inapplicable, not falsified; preserve any source correction."),
    ("outcome_unavailable",
     "The relevant outcome is missing, incomparable, or not yet observable.",
     "There is insufficient outcome evidence; absence of disclosure is not a contrary observation."),
    ("evaluation_not_registered",
     "The metric scope, baseline, event window, lag, outcome window, or rejection rule was not fixed before testing.",
     "No qualified test exists; do not derive an empirical outcome from this record."),
    ("review_expired_untested",
     "The review deadline passed without a completed eligible test.",
     "The claim expired untested, not falsified; a new query does not rewrite this record."),
)
_V2_COMPATIBILITY_FALSIFIER = {
    "condition": "No directional claim exists in this internal compatibility object.",
    "observable": "This internal placeholder is never emitted as a V2 falsifier.",
}


def _v2_applicability(spec: dict | None) -> list[dict]:
    rows = [{"reason": reason, "condition": condition, "consequence": consequence}
            for reason, condition, consequence in _V2_NONTEST_CONDITIONS]
    if spec is None:
        rows.insert(0, {
            "reason": "no_directional_claim",
            "condition": "The record abstains from a directional mechanism.",
            "consequence": "There is no directional claim to falsify; later eligible evidence requires a new query.",
        })
    return rows


def _v2_narrative(spec: dict | None, classes: list[str]) -> tuple[dict | None, list, list]:
    alternatives = [{"explanation_class": item, "text": _V2_ALT_TEXT[item]} for item in classes]
    if spec is None:
        return None, alternatives, []
    mechanism = dict(spec)
    metric_key = spec["operating_metric_class"]
    metric = _V2_METRICS[metric_key]
    direction = spec["predicted_operating_direction"]
    # "Mixed" needs a separately scoped component test; this profile refuses it.
    if metric_key == "input_cost":
        change = "decrease" if direction == "improves" else "increase"
    else:
        change = "increase" if direction == "improves" else "decrease"
    antecedent = _V2_ANTECEDENTS[spec["mechanism_class"]][spec["mechanism_polarity"]]
    mechanism["hypothesis_text"] = (
        "If " + antecedent + " under the evidenced relationship within the preregistered event window, "
        "the target is hypothesized to show " + ("an increase" if change == "increase" else "a decrease")
        + " in " + metric + " relative to its preregistered comparable baseline over the fixed outcome window. "
        "This is an uncalibrated conditional research claim, not a measured effect."
    )
    falsifiers = [{
        "condition": (
            "The stated antecedent occurred under an applicable relationship, but a preregistered "
            "test finds the target's " + metric + " did not " + change
            + " over the fixed outcome window against its comparable baseline."
        ),
        "observable": (
            "Eligible owner records of antecedent occurrence and relationship applicability, and comparable "
            + metric + " observations satisfying the registered scope, baseline, lag, window, uncertainty "
            "and rejection rule. Absence of disclosure is not a contrary observation."
        ),
    }]
    return mechanism, alternatives, falsifiers


def _v2_native_mechanism(mechanism: dict | None) -> dict | None:
    if mechanism is None:
        return None
    return {key: value for key, value in mechanism.items() if key != "mechanism_polarity"}


def _v2_native_falsifiers(falsifiers: list[dict]) -> list[dict]:
    # V1 requires a nonempty array, including on abstentions. This private
    # shape bridge never gives that placeholder to a V2 consumer.
    return falsifiers or [dict(_V2_COMPATIBILITY_FALSIFIER)]


@lru_cache(maxsize=1)
def _v2_validator() -> Draft202012Validator:
    schema = json.loads((_CONTRACT_DIR / "propagation_hypothesis.v2.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _derive_v2_record_id(event_id: str, target: dict, asof: str, spec: dict | None) -> str:
    payload = json.dumps(
        ["k3d.record_id/typed-prose-v2", _V2_PROFILE, event_id,
         *derive_target_identity_component(target), asof, spec],
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return "eph2:" + hashlib.sha256(payload).hexdigest()[:16]


def validate_hypothesis_v2(record: Any) -> list[Finding]:
    """Validate exact generated narrative AND all existing native v1 semantics.

    Does not authenticate owners, infer commercial roles or qualify time/rights.
    V1 archives are explicitly NOT promoted to this construction profile.
    """
    try:
        data = _v2_snapshot(record)
    except EconomicPropagationError as exc:
        return [_f("K3D_V2_R000", "$", str(exc))]
    if type(data) is not dict:
        return [_f("K3D_V2_R000", "$", "record must be an exact JSON object")]
    errors = list(_v2_validator().iter_errors(data))
    if errors:
        return [_f("K3D_V2_R001", error.json_path, error.message[:160]) for error in errors[:32]]
    findings = []
    if type(data["version"]) is not int:
        findings.append(_f("K3D_V2_R001", "$.version", "version must be integer 2"))
    try:
        _v2_calendar_date(data["asof"])
        _v2_calendar_date(data["expiry"]["review_by"])
        classes = _v2_classes(data["alternative_classes"])
        raw_mechanism = data["mechanism"]
        spec = None if raw_mechanism["state"] == "abstained" else _v2_spec({
            key: raw_mechanism[key] for key in (
                "mechanism_class", "mechanism_polarity", "predicted_operating_direction", "operating_metric_class"
            )
        })
        mechanism, alternatives, falsifiers = _v2_narrative(spec, classes)
    except EconomicPropagationError as exc:
        return [_f("K3D_V2_R020", "$", str(exc))]
    expected_mechanism = ({
        "state": "abstained", "mechanism_class": None, "hypothesis_text": None,
        "predicted_operating_direction": None, "operating_metric_class": None, "mechanism_polarity": None,
    } if mechanism is None else {"state": "hypothesized", **mechanism})
    for field, expected in (
        ("mechanism", expected_mechanism), ("alternatives", alternatives),
        ("falsifiers", falsifiers), ("alternative_classes", classes),
        ("applicability_conditions", _v2_applicability(spec)),
        ("evaluation_requirements", _V2_EVALUATION_REQUIREMENTS),
    ):
        if data[field] != expected:
            findings.append(_f("K3D_V2_R010", "$." + field, "not the exact compiler-owned construction"))
    if data["expiry"]["note"] != _V2_EXPIRY_NOTE:
        findings.append(_f("K3D_V2_R010", "$.expiry.note", "not the compiler-owned review note"))
    expected_id = _derive_v2_record_id(data["source_event"]["event_id"], data["target"], data["asof"], spec)
    if data["record_id"] != expected_id:
        findings.append(_f("K3D_V2_R082", "$.record_id", "not the versioned logical record identity"))
    if data["content_sha256"] != content_sha256(data):
        findings.append(_f("K3D_V2_R081", "$.content_sha256", "content hash mismatch"))
    # Internal validation projection only: never emitted, stored, or advertised
    # as a migration of legacy free text into validated prose.
    shadow = dict(data)
    shadow.pop("construction_profile")
    shadow.pop("alternative_classes")
    shadow.pop("applicability_conditions")
    shadow.pop("evaluation_requirements")
    shadow["mechanism"] = _v2_native_mechanism(data["mechanism"])
    shadow["falsifiers"] = _v2_native_falsifiers(data["falsifiers"])
    shadow["schema"] = SCHEMA_ID
    shadow["version"] = 1
    shadow["record_id"] = derive_record_id(data["source_event"]["event_id"], data["target"], data["asof"])
    shadow["content_sha256"] = content_sha256(shadow)
    findings.extend(validate_hypothesis(shadow))
    return findings


def compose_hypothesis_v2(
    *, source_event: dict, target: dict, asof: str, compiled_at: str,
    generator_admissions: list[dict] | tuple = (),
    relationship_paths: list[dict] | tuple = (),
    similarity_evidence: list[dict] | tuple = (),
    market_evidence: list[dict] | tuple = (),
    mechanism_spec: dict | None = None,
    alternative_classes: list[str] | tuple,
    review_by: str,
) -> dict:
    """Typed qualitative construction with no caller prose slots.

    All native evidence/identity/rights/clock gates still run. Nothing is acquired,
    admitted, stored, published, forecast-ranked or traded by this function.
    """
    classes = _v2_classes(alternative_classes)
    spec = _v2_spec(mechanism_spec)
    _v2_calendar_date(asof)
    _v2_calendar_date(review_by)
    inputs = {"source_event": source_event, "target": target, "asof": asof, "compiled_at": compiled_at}
    for label, rows in (
        ("generator_admissions", generator_admissions), ("relationship_paths", relationship_paths),
        ("similarity_evidence", similarity_evidence), ("market_evidence", market_evidence),
    ):
        if type(rows) not in (list, tuple) or len(rows) > (24 if label == "generator_admissions" else 16):
            raise EconomicPropagationError("K3D_V2_EVIDENCE_ARRAY")
        inputs[label] = list(rows)
    inputs = _v2_snapshot(inputs)
    # Reuse the same schema for input shapes so malformed keys cannot reach
    # unhashable vocabulary lookups in the legacy semantic validator.
    wire_schema = _v2_validator().schema
    for field, value in inputs.items():
        fragment = {"$defs": wire_schema["$defs"], **wire_schema["properties"][field]}
        if not Draft202012Validator(fragment).is_valid(value):
            raise EconomicPropagationError("K3D_V2_INPUT_SHAPE: " + field)
    _, alternatives, refusal_falsifiers = _v2_narrative(None, classes)
    expiry = {"review_by": review_by, "note": _V2_EXPIRY_NOTE}
    # Ask the incumbent composer to establish native eligibility BEFORE rendering
    # a conditional mechanism. This reuses its law instead of duplicating it.
    probe = compose_hypothesis(
        **inputs, mechanism_proposal=None, alternatives=alternatives,
        falsifiers=_v2_native_falsifiers(refusal_falsifiers), expiry=expiry,
    )
    if spec is None:
        base = probe
    else:
        if (probe["graph_states"]["graph_1"] != "supported"
                or probe["abstention"]["reasons"] != ["no_mechanism_hypothesized"]):
            raise EconomicPropagationError("K3D_V2_MECHANISM_NOT_ELIGIBLE")
        mechanism, alternatives, falsifiers = _v2_narrative(spec, classes)
        base = compose_hypothesis(
            **inputs, mechanism_proposal=_v2_native_mechanism(mechanism), alternatives=alternatives,
            falsifiers=_v2_native_falsifiers(falsifiers), expiry=expiry,
        )
    mechanism, _, falsifiers = _v2_narrative(spec, classes)
    base["mechanism"] = ({**base["mechanism"], "mechanism_polarity": None}
                         if mechanism is None else {"state": "hypothesized", **mechanism})
    base["falsifiers"] = falsifiers
    base["applicability_conditions"] = _v2_applicability(spec)
    base["evaluation_requirements"] = list(_V2_EVALUATION_REQUIREMENTS)
    base["schema"] = _V2_SCHEMA_ID
    base["version"] = 2
    base["construction_profile"] = _V2_PROFILE
    base["alternative_classes"] = classes
    base["record_id"] = _derive_v2_record_id(base["source_event"]["event_id"], base["target"], asof, spec)
    base["content_sha256"] = content_sha256(base)
    findings = validate_hypothesis_v2(base)
    if findings:
        raise EconomicPropagationError("K3D_V2_COMPOSITION_REFUSED: " + findings[0].code)
    return base
