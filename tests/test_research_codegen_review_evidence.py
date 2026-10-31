"""Actual P01 receipt -> existing review packet, invented data and fake engine.

This checks the compiled display attachment against real prefix/accounting
return shapes. It executes no candidate source and confers no physical proof.
The source composer joins typed receipts into the real advisory consumer.
"""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from engine.research_factory.review_queue import diagnostic_review_packet
from scripts.build_research_factory_review_queue import render_markdown
from engine.research_codegen import bridge as b, prefix_driver as pd
from tests import test_research_codegen_connected_p01 as p01
from tests.test_research_codegen_connected_p01 import connected_case
from tests import test_research_codegen_prefix_driver as pf


IDENTITY = ("diagnostic_id", "original_root_id", "candidate_id", "source_sha256",
            "config_sha256", "protocol_sha256", "input_policy_sha256",
            "runtime_sha256", "evaluator_sha256", "artifact_sha256")
def projection(public, staged, outcome, receipts):
    """Use the connected source composer; expectations are never inferred."""
    packet = diagnostic_review_packet(public, engineering_receipts=receipts)
    attached = packet["engineering_evidence"]
    return {key: attached[key] for key in
            ("schema", "identity", "accounting", "attempts", "controls")}


def execute_case(case, *, refused=False):
    staged = p01._stage(case)
    p01._assert_full_cold_accounting(case, staged)
    run = p01._run_for(case, staged, 1 if refused else 0)
    prepared = b.prepare_synthetic_inputs(run, commission=case[3]["commission"])
    behavior = None
    if refused:
        behavior = {"workload": json.dumps(dict(schema="research_codegen.output.v1",
            candidate_id=run.identity.candidate_id, fold_id="invented", entity_id="XLB",
            input_policy_sha256=run.identity.input_policy_sha256,
            rows=[dict(decision_id=prepared.decisions[0].decision_id,
                       status="available", value=float("inf"), reason=None)]),
            allow_nan=True).encode()}
    engine = p01.AccountingGuardedFakeEngine(case, staged, behavior)
    outcome = pd.run_prefix_driver(prepared, source=case[1][1 if refused else 0],
        engine=engine, spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert engine.charge_checks == len(engine.calls) > 0
    raw = (b.compute_synthetic_diagnostic(run, commission=case[3]["commission"])
           if refused else pd.connect_prepared_outputs(run, outcome,
                                                       commission=case[3]["commission"]))
    _, public = p01._decode_public(run, case[3]["commission"], raw)
    return staged, outcome, public, engine, dict(run=run, commission=case[3]["commission"],
        source=case[1][1 if refused else 0], staged=staged, outcome=outcome)


@pytest.mark.parametrize("refused", [False, True])
def test_actual_p01_receipts_preserve_controls_and_no_actions(connected_case, refused):
    staged, outcome, public, engine, receipts = execute_case(connected_case, refused=refused)
    attachment = projection(public, staged, outcome, receipts)
    original = deepcopy(attachment)
    calls_before = len(engine.calls)
    ledger_before = (connected_case[0] / "trial_ledger.jsonl").read_bytes()
    packet = diagnostic_review_packet(public, engineering_receipts=receipts)
    assert packet["allowed_decisions"] == [] and packet["candidate_type"] is None
    assert packet["current_status"] == "unregistered_synthetic_diagnostic"
    evidence = packet["engineering_evidence"]
    assert evidence["authority"] == "display_only"
    assert evidence["scope"] == "SYNTHETIC_ENGINEERING_ONLY"
    assert evidence["physical_acceptance"] is False
    assert evidence["scientific_acceptance"] == "UNQUALIFIED"
    assert "Synthetic/scripted source plumbing" in packet["note"]
    assert evidence["controls"][2] == {
        "id": "output_contract", "status": "NOT_RUN", "evidence_sha256": None}
    assert evidence["accounting"]["trial_readback_sha256"] == staged.trial_readback.sha256
    assert evidence["controls"] == original["controls"]
    assert len(evidence["attempts"]) == (1 if refused else 6)
    assert all(row["cleanup_confirmed"] for row in evidence["attempts"])
    assert evidence["controls"][-2:] == [
        {"id": "physical_boundary", "status": "NOT_RUN", "evidence_sha256": None},
        {"id": "resource_overload", "status": "NOT_RUN", "evidence_sha256": None}]
    if refused:
        assert public["aggregates"]["paired_mean_improvement"] is None
        assert evidence["controls"][1]["status"] == "NOT_RUN"
    # Neither the caller's later mutation nor the packet can mutate the source
    # receipt; compiling the display adds no transport or ledger operation.
    attachment["attempts"][0]["operation_id"] = "changed-after-compile"
    attachment["controls"][0]["status"] = "DID_NOT_MATCH"
    assert evidence["attempts"] == original["attempts"]
    assert evidence["controls"] == original["controls"]
    assert len(engine.calls) == calls_before
    assert (connected_case[0] / "trial_ledger.jsonl").read_bytes() == ledger_before
    encoded = json.dumps(packet)
    assert all(word not in encoded for word in (
        "source_b64", "workload_output", "container_id", "transport_plan",
        "XLB", "trial_ledger.jsonl", str(connected_case[0])))
    markdown = render_markdown([packet], "2026-10-14T00:00:00Z")
    assert "Candidates awaiting decision: 0" in markdown
    assert "| physical_boundary | NOT_RUN | none |" in markdown
    assert "| resource_overload | NOT_RUN | none |" in markdown
    assert f"Retained attempts: {1 if refused else 6}." in markdown
    assert "--decision" not in markdown
    assert "Synthetic/scripted source plumbing" in markdown
    for value in (True, 0):
        changed = deepcopy(packet)
        changed["engineering_evidence"]["physical_acceptance"] = value
        with pytest.raises(ValueError):
            render_markdown([changed], "2026-10-14T00:00:00Z")
    changed = deepcopy(packet)
    changed["engineering_evidence"]["private_extra"] = changed
    with pytest.raises(ValueError):
        render_markdown([changed], "2026-10-14T00:00:00Z")


def test_source_or_artifact_substitution_and_physical_claim_refuse(connected_case):
    staged, outcome, public, _, receipts = execute_case(connected_case)
    attachment = projection(public, staged, outcome, receipts)
    for key in IDENTITY:
        altered = deepcopy(attachment)
        altered["identity"][key] = "b" * 64 if key.endswith("sha256") else "other-id"
        if altered["identity"][key] == public[key]:
            altered["identity"][key] = "c" * 64
        with pytest.raises(ValueError):
            diagnostic_review_packet(public, engineering_evidence=altered)
    altered = deepcopy(attachment)
    altered["controls"][-2].update(status="MATCHED_EXPECTATION", evidence_sha256="f" * 64)
    with pytest.raises(ValueError):
        diagnostic_review_packet(public, engineering_evidence=altered)
    assert "engineering_evidence" not in diagnostic_review_packet(public)


def test_invalid_and_uncertain_receipts_are_not_silently_rewritten(connected_case, subtests):
    staged, outcome, public, _, receipts = execute_case(connected_case)
    attachment = projection(public, staged, outcome, receipts)
    changes = [
        lambda e: e.update(raw_output="must never be copied"),
        lambda e: e["accounting"].update(durable_observation_sha256="z" * 64),
        lambda e: e["controls"].pop(),
        lambda e: e["controls"][0].update(id="output_contract"),
        lambda e: e["controls"][0].update(status="NOT_RUN"),
        lambda e: e["controls"][0].update(evidence_sha256=None),
        lambda e: e["attempts"].append(deepcopy(e["attempts"][0])),
        lambda e: e["attempts"][0].update(output_bytes=True),
        lambda e: e["attempts"][0].update(output_bytes=float("nan")),
        lambda e: e["attempts"][0].update(workload_returncode=False),
        lambda e: e["attempts"][0].update(workload_confirmed=1),
        lambda e: e["attempts"][0].update(output_sha256=None),
        lambda e: e["attempts"][0].update(workload_returncode=1),
        lambda e: e["attempts"][0].update(cleanup_confirmed=False),
        lambda e: e["attempts"][0].update(execution_uncertain=True),
        lambda e: e["attempts"][0].update(reconciliation_required=True),
        lambda e: e["attempts"][0].update(workload_returncode=None),
        lambda e: e["attempts"][0].update(state="RUNNING"),
        lambda e: e["attempts"][0].update(operation_id="../private/path"),
        lambda e: e["attempts"][0].update(raw_command="not public evidence"),
        lambda e: e.update(attempts=tuple(e["attempts"])),
        lambda e: e.update(attempts=[e["attempts"][0]] * 4097),
        lambda e: e["attempts"][0].update(state="PLANNED", workload_confirmed=False,
            workload_returncode=None, cleanup_confirmed=False, output_bytes=0,
            output_sha256="7" * 64),
        lambda e: e["attempts"][0].update(state="CLEANED_FAILURE"),
    ]
    for index, change in enumerate(changes):
        with subtests.test(invalid_case=index):
            altered = deepcopy(attachment)
            change(altered)
            with pytest.raises(ValueError, match="INVALID_DIAGNOSTIC_ENGINEERING_EVIDENCE"):
                diagnostic_review_packet(public, engineering_evidence=altered)
    partial = deepcopy(attachment)
    partial["attempts"][0].update(state="CLEANUP_UNCERTAIN", cleanup_confirmed=False,
                                   reconciliation_required=True, execution_uncertain=True)
    partial["controls"][1].update(status="DID_NOT_MATCH")
    packet = diagnostic_review_packet(public, engineering_evidence=partial)
    assert packet["engineering_evidence"]["attempts"][0]["state"] == "CLEANUP_UNCERTAIN"
    assert packet["engineering_evidence"]["controls"][1]["status"] == "DID_NOT_MATCH"
    assert packet["allowed_decisions"] == []
    assert packet["engineering_evidence"]["physical_acceptance"] is False

    # Real bridge validation copies the identity and aggregate containers.
    # A stub that returns public unchanged would report a spurious alias bug.
    original = deepcopy(packet)
    public["diagnostic_id"] = "changed-after-real-validation"
    public["aggregates"]["paired_mean_improvement"] = None
    assert packet == original


def test_attempt_ceiling_does_not_drop_rows_or_invent_physical_proof(connected_case):
    staged, outcome, public, _, receipts = execute_case(connected_case)
    attachment = projection(public, staged, outcome, receipts)
    first = attachment["attempts"][0]
    attachment["attempts"] = [{**first, "operation_id": f"invented-operation-{i}"}
                              for i in range(4096)]
    packet = diagnostic_review_packet(public, engineering_evidence=attachment)
    assert len(packet["engineering_evidence"]["attempts"]) == 4096
    assert packet["engineering_evidence"]["attempts"][-1]["operation_id"] == "invented-operation-4095"
    assert packet["engineering_evidence"]["physical_acceptance"] is False


def test_source_composer_rejects_artifact_output_and_accounting_substitution(connected_case):
    staged, outcome, public, engine, receipts = execute_case(connected_case)
    calls = len(engine.calls)
    ledger = (connected_case[0] / "trial_ledger.jsonl").read_bytes()
    mutations = []
    other_public = deepcopy(public)
    other_public["artifact_sha256"] = "f" * 64
    mutations.append((other_public, receipts))
    output = outcome.outputs[0]
    for altered in (replace(output, sha256="f" * 64),
                    pf.bound(json.loads(output.raw) | {"rows": []})):
        mutations.append((public, {**receipts, "outcome": replace(
            outcome, outputs=(altered, *outcome.outputs[1:]))}))
    mutations.append((public, {**receipts, "source": replace(receipts["source"], sha256="f" * 64)}))
    mutations.append((public, {**receipts, "staged": replace(staged,
        durable_readback_observation=replace(staged.durable_readback_observation, sha256="f" * 64))}))
    for changed_public, changed_receipts in mutations:
        with pytest.raises(ValueError):
            diagnostic_review_packet(changed_public, engineering_receipts=changed_receipts)
    assert len(engine.calls) == calls
    assert (connected_case[0] / "trial_ledger.jsonl").read_bytes() == ledger


def test_source_composer_rejects_changed_schedule_request_and_attempts(connected_case):
    _, outcome, public, _, receipts = execute_case(connected_case)
    run = receipts["run"]
    first = outcome.attempts[0]
    altered_raw = replace(first.transport_attempt, operation_id="other-operation")
    variants = [replace(outcome, attempts=outcome.attempts[:-1]),
                replace(outcome, attempts=(first, *outcome.attempts[:-1])),
                replace(outcome, attempts=(replace(first, input_sha256="f" * 64), *outcome.attempts[1:])),
                replace(outcome, attempts=(replace(first, transport_attempt=altered_raw), *outcome.attempts[1:]))]
    for changed in variants:
        with pytest.raises(ValueError):
            diagnostic_review_packet(public, engineering_receipts={**receipts, "outcome": changed})
    # Same superficial candidate identity does not bind a changed request/schedule.
    for changed_run in (replace(run, schedules=run.schedules[:-1]),
                        replace(run, decisions=(replace(run.decisions[0], request=pf.bound({})),
                                                *run.decisions[1:]))):
        with pytest.raises(ValueError):
            diagnostic_review_packet(public, engineering_receipts={**receipts, "run": changed_run})


def test_source_composer_never_accepts_posthoc_expectation_or_mixed_inputs(connected_case):
    staged, outcome, public, _, receipts = execute_case(connected_case, refused=True)
    with pytest.raises(ValueError):
        diagnostic_review_packet(public, engineering_receipts={**receipts, "expected_refusal": True})
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        diagnostic_review_packet(public, engineering_receipts=receipts,
            engineering_evidence=projection(public, staged, outcome, receipts))
    packet = diagnostic_review_packet(public, engineering_receipts=receipts)
    assert packet["engineering_evidence"]["controls"][2]["status"] == "NOT_RUN"
    assert packet["engineering_evidence"]["physical_acceptance"] is False
    assert packet["diagnostic"]["execution_enabled"] is False


def test_source_composer_preserves_consistent_uncertain_attempt_without_effects(connected_case):
    _, outcome, public, engine, receipts = execute_case(connected_case, refused=True)
    attempt = outcome.attempts[0]
    state = pd.transport_module.AttemptState.CLEANUP_UNCERTAIN
    raw = replace(attempt.transport_attempt, state=state, cleanup_confirmed=False,
                  reconciliation_required=True, execution_uncertain=True)
    uncertain = replace(attempt, transport_attempt=raw, state=state.value,
                        cleanup_confirmed=False, reconciliation_required=True,
                        execution_uncertain=True)
    changed = {**receipts, "outcome": replace(outcome, attempts=(uncertain,))}
    calls = len(engine.calls)
    packet = diagnostic_review_packet(public, engineering_receipts=changed)
    row = packet["engineering_evidence"]["attempts"][0]
    assert row["state"] == "CLEANUP_UNCERTAIN" and row["reconciliation_required"]
    assert not row["cleanup_confirmed"]
    assert all(control["status"] == "NOT_RUN"
               for control in packet["engineering_evidence"]["controls"][1:])
    assert len(engine.calls) == calls
