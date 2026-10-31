"""Frozen owner declarations, synthetic transport only; no candidate execution."""
from dataclasses import replace
import json

import pytest

from engine.research_codegen import bridge as b, prefix_driver as pd
from engine.research_codegen import output_expectations as oe
from engine.research_factory.review_queue import diagnostic_review_packet
from tests import test_research_codegen_connected_p01 as p01
from tests.test_research_codegen_connected_p01 import connected_case
from tests import test_research_codegen_prefix_driver as pf


def setup(case, kind="known_answer"):
    staged = p01._stage(case)
    index = 0 if kind == "known_answer" else 1
    run = p01._run_for(case, staged, index)
    prepared = b.prepare_synthetic_inputs(run, commission=case[3]["commission"])
    # Independent control declaration, fixed before any fake output exists.
    answers = {"XLB": 9, "XLE": 8, "XLF": 7, "XLI": 6, "XLK": 5,
               "XLP": 4, "XLU": 3, "XLV": 2, "XLY": 1}
    rows = tuple(dict(decision_id=t.decision_id,
        status="available" if index == 0 else "refused",
        value=answers[t.node] if index == 0 else None,
        reason=None if index == 0 else "FUTURE_OBSERVATION_UNAVAILABLE")
        for t in prepared.decisions)
    expectation = oe.freeze_output_expectation(prepared,
        expected_generation=staged.expected_generation,
        variant_id=case[2][index]["variant_id"], control_kind=kind, expected_rows=rows)
    return staged, run, prepared, expectation, index


def finish(case, parts, behavior=None, expectation=None):
    staged, run, prepared, frozen, index = parts
    engine = p01.AccountingGuardedFakeEngine(case, staged, behavior)
    outcome = pd.run_prefix_driver(prepared, source=case[1][index], engine=engine,
        spec=pf.spec(), config_sha256=run.identity.config_sha256,
        output_expectation=frozen)
    raw = (pd.connect_prepared_outputs(run, outcome, commission=case[3]["commission"])
           if outcome.completed else b.compute_synthetic_diagnostic(run, commission=case[3]["commission"]))
    _, public = p01._decode_public(run, case[3]["commission"], raw)
    receipts = dict(run=run, commission=case[3]["commission"], source=case[1][index],
                    staged=staged, outcome=outcome, output_expectation=expectation or frozen)
    return diagnostic_review_packet(public, engineering_receipts=receipts), outcome, engine, receipts


def row_output(status="available", value=999, reason=None):
    def emit(e):
        return pf.encoded(dict(schema="research_codegen.output.v1",
            candidate_id=e["candidate_id"], fold_id=e["fold_id"], entity_id=e["entity_id"],
            input_policy_sha256=e["input_policy_sha256"], rows=[dict(
                decision_id=e["decision_id"], status=status, value=value, reason=reason)]))
    return {"workload": emit}


@pytest.mark.parametrize("kind,behavior,status", [
    ("known_answer", None, "MATCHED_EXPECTATION"),
    ("known_answer", row_output(), "DID_NOT_MATCH"),
    ("future_dependent", row_output("refused", None, "FUTURE_OBSERVATION_UNAVAILABLE"), "MATCHED_EXPECTATION"),
    ("future_dependent", row_output("refused", None, "UNRELATED_REFUSAL"), "DID_NOT_MATCH"),
    ("future_dependent", row_output("failed", None, "FUTURE_OBSERVATION_UNAVAILABLE"), "DID_NOT_MATCH"),
    ("future_dependent", {"workload": b'{"value":Infinity}'}, "NOT_RUN"),
    ("future_dependent", {"exit_state": {"Running": False, "ExitCode": 1, "OOMKilled": False}}, "NOT_RUN"),
])
def test_semantic_controls_are_explicit_and_source_only(connected_case, kind, behavior, status):
    packet, outcome, _, _ = finish(connected_case, setup(connected_case, kind), behavior)
    evidence = packet["engineering_evidence"]
    assert evidence["controls"][2]["status"] == status
    assert outcome.output_expectation_sha256
    assert evidence["physical_acceptance"] is False
    assert evidence["scientific_acceptance"] == "UNQUALIFIED"
    assert all(c["status"] == "NOT_RUN" for c in evidence["controls"][3:])
    assert packet["allowed_decisions"] == []


@pytest.mark.parametrize("mutation", ["source", "generation", "decision", "value", "kind"])
def test_changed_descriptor_cannot_replace_prefrozen_driver_binding(connected_case, mutation):
    parts = setup(connected_case)
    frozen = parts[3]
    doc = json.loads(frozen.descriptor.raw)
    if mutation == "source": doc["identity"]["source_sha256"] = "f" * 64
    elif mutation == "generation": doc["expected_generation_sha256"] = "f" * 64
    elif mutation == "decision": doc["cells"][0]["row"]["decision_id"] = "swapped"
    elif mutation == "value": doc["cells"][0]["row"]["value"] = 123
    else: doc["control_kind"] = "future_dependent"
    changed = replace(frozen, descriptor=pf.bound(doc))
    with pytest.raises((ValueError, oe.OutputExpectationRefused)):
        finish(connected_case, parts, expectation=changed)


@pytest.mark.parametrize("mutation", ["source", "generation", "decision", "variant"])
def test_invalid_binding_refuses_before_transport(connected_case, mutation):
    staged, run, prepared, frozen, index = setup(connected_case)
    if mutation == "source": prepared = replace(prepared, identity=replace(prepared.identity, source_sha256="e" * 64))
    elif mutation == "decision": prepared = replace(prepared, decisions=tuple(reversed(prepared.decisions)))
    elif mutation == "generation": frozen = replace(frozen, expected_generation=pf.bound({}))
    else:
        doc = json.loads(frozen.descriptor.raw); doc["variant_id"] = "unknown"
        frozen = replace(frozen, descriptor=pf.bound(doc))
    engine = pf.ScriptedFakeEngine()
    with pytest.raises(ValueError):
        pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
            spec=pf.spec(), config_sha256=run.identity.config_sha256, output_expectation=frozen)
    assert engine.calls == []


def test_missing_commitment_never_upgrades_old_outcome(connected_case):
    parts = setup(connected_case)
    packet, outcome, _, receipts = finish(connected_case, parts)
    with pytest.raises(ValueError):
        diagnostic_review_packet(packet["diagnostic"], engineering_receipts={
            **receipts, "outcome": replace(outcome, output_expectation_sha256=None)})
    # A declaration omitted from the consumer must not imply that it was checked.
    receipts.pop("output_expectation")
    packet = diagnostic_review_packet(packet["diagnostic"], engineering_receipts=receipts)
    assert packet["engineering_evidence"]["controls"][2]["status"] == "NOT_RUN"


@pytest.mark.parametrize("mutation", ["drop", "duplicate", "order", "bool", "nonfinite", "extra", "schedule"])
def test_original_declaration_requires_exact_finite_coverage(connected_case, mutation):
    staged, _, prepared, frozen, _ = setup(connected_case)
    doc = json.loads(frozen.descriptor.raw)
    rows = [cell["row"] for cell in doc["cells"]]
    if mutation == "drop": rows.pop()
    elif mutation == "duplicate": rows[1] = dict(rows[0])
    elif mutation == "order": rows.reverse()
    elif mutation == "bool": rows[0]["value"] = True
    elif mutation == "nonfinite": rows[0]["value"] = float("inf")
    elif mutation == "extra": rows[0]["authority"] = "allowed"
    else: prepared = replace(prepared, schedules=prepared.schedules[:-1])
    with pytest.raises(ValueError):
        oe.freeze_output_expectation(prepared, expected_generation=staged.expected_generation,
            variant_id=doc["variant_id"], control_kind=doc["control_kind"], expected_rows=tuple(rows))
