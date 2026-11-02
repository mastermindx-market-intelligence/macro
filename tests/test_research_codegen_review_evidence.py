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
from engine.research_codegen import output_expectations as oe
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
                        execution_uncertain=True, local_observation=None)
    changed = {**receipts, "outcome": replace(outcome, attempts=(uncertain,))}
    calls = len(engine.calls)
    packet = diagnostic_review_packet(public, engineering_receipts=changed)
    row = packet["engineering_evidence"]["attempts"][0]
    assert row["state"] == "CLEANUP_UNCERTAIN" and row["reconciliation_required"]
    assert not row["cleanup_confirmed"]
    assert all(control["status"] == "NOT_RUN"
               for control in packet["engineering_evidence"]["controls"][1:])
    assert len(engine.calls) == calls


# Frozen owner declarations: scripted source controls, no candidate execution.
def _output_expectation_case(case, kind="known_answer"):
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


def _finish_output_expectation(case, parts, behavior=None, expectation=None):
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


def _scripted_output_row(status="available", value=999, reason=None):
    def emit(e):
        return pf.encoded(dict(schema="research_codegen.output.v1",
            candidate_id=e["candidate_id"], fold_id=e["fold_id"], entity_id=e["entity_id"],
            input_policy_sha256=e["input_policy_sha256"], rows=[dict(
                decision_id=e["decision_id"], status=status, value=value, reason=reason)]))
    return {"workload": emit}


@pytest.mark.parametrize("kind,behavior,status", [
    ("known_answer", None, "MATCHED_EXPECTATION"),
    ("known_answer", _scripted_output_row(), "DID_NOT_MATCH"),
    ("future_dependent", _scripted_output_row("refused", None, "FUTURE_OBSERVATION_UNAVAILABLE"), "MATCHED_EXPECTATION"),
    ("future_dependent", _scripted_output_row("refused", None, "UNRELATED_REFUSAL"), "DID_NOT_MATCH"),
    ("future_dependent", _scripted_output_row("failed", None, "FUTURE_OBSERVATION_UNAVAILABLE"), "DID_NOT_MATCH"),
    ("future_dependent", {"workload": b'{"value":Infinity}'}, "NOT_RUN"),
    ("future_dependent", {"exit_state": {"Running": False, "ExitCode": 1, "OOMKilled": False}}, "NOT_RUN"),
])
def test_semantic_controls_are_explicit_and_source_only(connected_case, kind, behavior, status):
    packet, outcome, _, _ = _finish_output_expectation(connected_case, _output_expectation_case(connected_case, kind), behavior)
    evidence = packet["engineering_evidence"]
    assert evidence["controls"][2]["status"] == status
    assert outcome.output_expectation_sha256
    assert evidence["physical_acceptance"] is False
    assert evidence["scientific_acceptance"] == "UNQUALIFIED"
    assert all(c["status"] == "NOT_RUN" for c in evidence["controls"][3:])
    assert packet["allowed_decisions"] == []


@pytest.mark.parametrize("mutation", ["source", "generation", "decision", "value", "kind"])
def test_changed_descriptor_cannot_replace_prefrozen_driver_binding(connected_case, mutation):
    parts = _output_expectation_case(connected_case)
    frozen = parts[3]
    doc = json.loads(frozen.descriptor.raw)
    if mutation == "source": doc["identity"]["source_sha256"] = "f" * 64
    elif mutation == "generation": doc["expected_generation_sha256"] = "f" * 64
    elif mutation == "decision": doc["cells"][0]["row"]["decision_id"] = "swapped"
    elif mutation == "value": doc["cells"][0]["row"]["value"] = 123
    else: doc["control_kind"] = "future_dependent"
    changed = replace(frozen, descriptor=pf.bound(doc))
    with pytest.raises((ValueError, oe.OutputExpectationRefused)):
        _finish_output_expectation(connected_case, parts, expectation=changed)


@pytest.mark.parametrize("mutation", ["source", "generation", "decision", "variant"])
def test_invalid_binding_refuses_before_transport(connected_case, mutation):
    staged, run, prepared, frozen, index = _output_expectation_case(connected_case)
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
    parts = _output_expectation_case(connected_case)
    packet, outcome, _, receipts = _finish_output_expectation(connected_case, parts)
    with pytest.raises(ValueError):
        diagnostic_review_packet(packet["diagnostic"], engineering_receipts={
            **receipts, "outcome": replace(outcome, output_expectation_sha256=None)})
    # A declaration omitted from the consumer must not imply that it was checked.
    receipts.pop("output_expectation")
    packet = diagnostic_review_packet(packet["diagnostic"], engineering_receipts=receipts)
    assert packet["engineering_evidence"]["controls"][2]["status"] == "NOT_RUN"


@pytest.mark.parametrize("mutation", ["drop", "duplicate", "order", "bool", "nonfinite", "extra", "schedule"])
def test_original_declaration_requires_exact_finite_coverage(connected_case, mutation):
    staged, _, prepared, frozen, _ = _output_expectation_case(connected_case)
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


# Native local instrumentation is source-only and cannot qualify prospective evidence.
def test_local_issue_observation_joins_real_preparation_without_new_authority(connected_case):
    _, outcome, public, _, receipts = execute_case(connected_case)
    prepared = b.prepare_synthetic_inputs(receipts["run"], commission=receipts["commission"])
    packet = diagnostic_review_packet(public, engineering_receipts=receipts)
    for attempt, task, projection in zip(outcome.attempts, prepared.decisions,
                                         packet["engineering_evidence"]["attempts"]):
        observation = json.loads(attempt.local_observation.raw)
        assert observation["identity"] == {key: getattr(prepared.identity, key) for key in b._IDENTITY}
        assert observation["input_sha256"] == task.input_bytes.sha256
        assert observation["capture_evidence_sha256"] == task.capture_evidence.sha256
        assert observation["clock_state"] == "LOCAL_CLOCK_UNATTESTED"
        assert observation["accepted_freeze_qualification"] == "UNAVAILABLE"
        assert observation["maturity_qualification"] == "UNAVAILABLE"
        assert observation["scope"] == "SYNTHETIC_ENGINEERING_ONLY"
        assert projection["local_observation"]["sha256"] == attempt.local_observation.sha256
    encoded = json.dumps(packet)
    assert "issued_at_utc" not in encoded and "returned_at_utc" not in encoded
    assert packet["engineering_evidence"]["physical_acceptance"] is False


@pytest.mark.parametrize("mutation", ["input", "decision", "clock", "qualification", "capture", "extra", "digest"])
def test_advisory_rejects_changed_local_observation_binding(connected_case, mutation):
    _, outcome, public, _, receipts = execute_case(connected_case)
    attempt = outcome.attempts[0]
    doc = json.loads(attempt.local_observation.raw)
    if mutation == "input": doc["input_sha256"] = "e" * 64
    elif mutation == "decision": doc["decision_id"] = "wrong-decision"
    elif mutation == "clock": doc["returned_at_utc"] = "naive clock"
    elif mutation == "qualification": doc["accepted_freeze_qualification"] = "ACCEPTED"
    elif mutation == "capture": doc["capture_evidence_sha256"] = "e" * 64
    else: doc["unbounded_extra"] = "no"
    altered = pf.bound(doc)
    if mutation == "digest": altered = replace(attempt.local_observation, sha256="e" * 64)
    changed = replace(outcome, attempts=(replace(attempt, local_observation=altered), *outcome.attempts[1:]))
    with pytest.raises(ValueError):
        diagnostic_review_packet(public, engineering_receipts={**receipts, "outcome": changed})


@pytest.mark.parametrize("return_clock", ["2026-11-01T00:00:00+00:00", "invalid", None])
def test_return_clock_problem_retains_actual_attempt_and_stops(connected_case, monkeypatch, return_clock):
    staged = p01._stage(connected_case)
    run = p01._run_for(connected_case, staged, 0)
    prepared = b.prepare_synthetic_inputs(run, commission=connected_case[3]["commission"])
    calls = []
    def clock():
        calls.append(1)
        if len(calls) == 1: return "2026-11-01T00:00:01+00:00"
        if return_clock is None: raise OSError("clock read unavailable")
        return return_clock
    monkeypatch.setattr(pd, "_local_utc_now", clock)
    engine = p01.AccountingGuardedFakeEngine(connected_case, staged)
    outcome = pd.run_prefix_driver(prepared, source=connected_case[1][0], engine=engine,
        spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert len(outcome.attempts) == 1 and not outcome.completed and outcome.outputs == ()
    assert outcome.attempts[0].transport_attempt.cleanup_confirmed
    assert engine.creates == 1
    doc = json.loads(outcome.attempts[0].local_observation.raw)
    assert doc["observation_problem"] in ("LOCAL_CLOCK_REGRESSION", "RETURN_CLOCK_UNAVAILABLE")
    raw = b.compute_synthetic_diagnostic(run, commission=connected_case[3]["commission"])
    _, public = p01._decode_public(run, connected_case[3]["commission"], raw)
    packet = diagnostic_review_packet(public, engineering_receipts=dict(run=run,
        commission=connected_case[3]["commission"], source=connected_case[1][0], staged=staged, outcome=outcome))
    assert packet["engineering_evidence"]["controls"][1]["status"] == "NOT_RUN"
    assert packet["engineering_evidence"]["attempts"][0]["local_observation"]["observation_problem"] == doc["observation_problem"]


def test_missing_historical_instrumentation_stays_absent(connected_case):
    _, outcome, public, _, receipts = execute_case(connected_case)
    old = replace(outcome, attempts=tuple(replace(a, local_observation=None) for a in outcome.attempts))
    packet = diagnostic_review_packet(public, engineering_receipts={**receipts, "outcome": old})
    assert all("local_observation" not in a for a in packet["engineering_evidence"]["attempts"])


def test_issue_clock_failure_prevents_effect(connected_case, monkeypatch):
    parts = _output_expectation_case(connected_case)
    _, run, prepared, frozen, index = parts
    def clock(): raise OSError("unavailable")
    monkeypatch.setattr(pd, "_local_utc_now", clock)
    engine = pf.ScriptedFakeEngine()
    outcome = pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
        spec=pf.spec(), config_sha256=run.identity.config_sha256, output_expectation=frozen)
    assert not engine.calls and not outcome.attempts and not outcome.completed
    assert outcome.refusal_reasons == ("ISSUE_CLOCK_UNAVAILABLE",)


@pytest.mark.parametrize("mutation", ["absent", "malformed"])
def test_capture_evidence_missing_is_absent_and_malformed_refuses_before_transport(connected_case, mutation):
    _, run, prepared, _, index = _output_expectation_case(connected_case)
    if mutation == "absent":
        prepared = replace(prepared, decisions=tuple(replace(t, capture_evidence=None) for t in prepared.decisions),
                           freeze_proposal=None)  # Historical preparation has neither new field.
    else:
        prepared = replace(prepared, decisions=(replace(prepared.decisions[0], capture_evidence=pf.bound({})), *prepared.decisions[1:]))
    engine = pf.ScriptedFakeEngine()
    if mutation == "malformed":
        with pytest.raises(ValueError):
            pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
                spec=pf.spec(), config_sha256=run.identity.config_sha256)
        assert engine.calls == []
    else:
        outcome = pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
            spec=pf.spec(), config_sha256=run.identity.config_sha256)
        assert all(json.loads(a.local_observation.raw)["capture_evidence_sha256"] is None for a in outcome.attempts)


def test_native_uncertainty_is_retained_in_local_observation(connected_case):
    staged, run, prepared, _, index = _output_expectation_case(connected_case)
    engine = p01.AccountingGuardedFakeEngine(connected_case, staged, {"absence": "exists"})
    outcome = pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
        spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert len(outcome.attempts) == 1 and not outcome.completed
    raw = b.compute_synthetic_diagnostic(run, commission=connected_case[3]["commission"])
    _, public = p01._decode_public(run, connected_case[3]["commission"], raw)
    packet = diagnostic_review_packet(public, engineering_receipts=dict(run=run,
        commission=connected_case[3]["commission"], source=connected_case[1][index], staged=staged, outcome=outcome))
    row = packet["engineering_evidence"]["attempts"][0]
    assert row["reconciliation_required"] and not row["cleanup_confirmed"]
    assert json.loads(outcome.attempts[0].local_observation.raw)["reconciliation_required"]
    assert row["local_observation"]["accepted_freeze_qualification"] == "UNAVAILABLE"


def test_clock_regression_before_later_attempt_keeps_first_return(connected_case, monkeypatch):
    staged, run, prepared, _, index = _output_expectation_case(connected_case)
    samples = iter(("2026-11-01T00:00:01+00:00", "2026-11-01T00:00:02+00:00", "2026-11-01T00:00:01+00:00"))
    monkeypatch.setattr(pd, "_local_utc_now", lambda: next(samples))
    engine = p01.AccountingGuardedFakeEngine(connected_case, staged)
    outcome = pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
        spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert engine.creates == 1 and len(outcome.attempts) == 1
    assert outcome.refusal_reasons == ("LOCAL_CLOCK_REGRESSION",)
    assert outcome.attempts[0].transport_attempt.cleanup_confirmed
    assert json.loads(outcome.attempts[0].local_observation.raw)["returned_at_utc"] == "2026-11-01T00:00:02+00:00"


# Freeze references and label readiness stay source proposals with no trusted issuer.
def test_freeze_proposal_is_connected_and_never_an_acceptance(connected_case):
    from engine.research_codegen import prospective_contract as pc
    _, outcome, public, _, receipts = execute_case(connected_case)
    prepared = b.prepare_synthetic_inputs(receipts["run"], commission=receipts["commission"])
    assert outcome.freeze_proposal_sha256 == prepared.freeze_proposal.sha256
    assessment = pc.verify_freeze_proposal(prepared.freeze_proposal)
    assert assessment["status"] == "UNQUALIFIED"
    assert "QUALIFIED_ACCEPTANCE_ISSUER_UNAVAILABLE" in assessment["missing_evidence"]
    packet = diagnostic_review_packet(public, engineering_receipts=receipts)
    result = packet["engineering_evidence"]["prospective_readiness"]
    assert result["freeze_status"] == "UNQUALIFIED" and result["mature_count"] == result["pending_count"] == 0
    assert result["unknown_count"] == 2 * len(prepared.decisions)
    assert result["execution_enabled"] is False
    assert all(label["state"] == "UNKNOWN" for label in result["labels"])


def _freeze_reference(run, prepared):
    from engine.research_codegen import prospective_contract as pc
    doc = json.loads(prepared.freeze_proposal.raw)
    return dict(schema=pc.REFERENCE_SCHEMA, issuer_origin="external-evidence-owner",
        receipt_id="external-receipt-1", evidence_sha256="e" * 64,
        proposal_identity_sha256=doc["proposal_identity_sha256"], state="current", superseded_by=None)


@pytest.mark.parametrize("mutation", ["version", "origin", "spoof", "superseded", "replayed", "identity", "duplicate"])
def test_freeze_reference_contract_rejects_spoofed_or_stale_inputs(connected_case, mutation):
    staged, run, prepared, _, _ = _output_expectation_case(connected_case)
    ref = _freeze_reference(run, prepared)
    if mutation == "version": ref["schema"] += ".wrong"
    elif mutation == "origin": ref["issuer_origin"] = None
    elif mutation == "spoof": ref["accepted"] = True
    elif mutation == "superseded": ref["superseded_by"] = "replacement"
    elif mutation == "replayed": ref["state"] = "replayed"
    elif mutation == "identity": ref["proposal_identity_sha256"] = "f" * 64
    refs = (pf.bound(ref),) * (2 if mutation == "duplicate" else 1)
    with pytest.raises(ValueError):
        b.prepare_synthetic_inputs(replace(run, freeze_evidence_references=refs), commission=connected_case[3]["commission"])


def _label_declarations(run, prepared):
    from engine.research_codegen import prospective_contract as pc
    declarations = []
    for task in prepared.decisions:
        labels = []
        trigger = run.session_dates.index(run.positions[task.calendar_index].trigger_date)
        for name, offset in pc.LABEL_DEPENDENCIES:
            day = run.session_dates[trigger + offset]
            labels.append(dict(label_id=name, dependency_end_session=day,
                declared_expected_maturity_at_utc=day + "T23:59:00+00:00",
                source_id="label-source", source_revision_sha256="a" * 64,
                basis="total_return", vintage="fixture-vintage", observation_id="obs-" + name,
                known_by_at_utc="2026-11-01T00:00:00+00:00",
                received_at_utc="2026-11-01T00:01:00+00:00", receipt_sha256="b" * 64,
                clock_basis="SOURCE_SESSION_REFERENCE", clock_evidence_reference=_freeze_reference(run, prepared)))
        declarations.append(pf.bound(dict(schema=pc.LABEL_SCHEMA, fold_id=task.fold_id,
            entity_id=task.entity_id, decision_id=task.decision_id,
            input_sha256=task.input_bytes.sha256, labels=labels)))
    return tuple(declarations)


@pytest.mark.parametrize("mutation", [None, "21_as_25", "unknown_maturity", "spoof_clock", "known_before_mature", "known_before_unknown_mature", "receipt_before_known", "decision", "revision", "availability_absent"])
def test_label_readiness_preserves_25session_dependency_and_never_infers_maturity(connected_case, mutation):
    from engine.research_codegen import prospective_contract as pc
    _, run, prepared, _, _ = _output_expectation_case(connected_case)
    declarations = _label_declarations(run, prepared)
    first = json.loads(declarations[0].raw)
    label = first["labels"][0]
    if mutation == "21_as_25": label["dependency_end_session"] = first["labels"][1]["dependency_end_session"]
    elif mutation == "unknown_maturity": label["declared_expected_maturity_at_utc"] = None
    elif mutation == "spoof_clock": label["clock_evidence_reference"] = {"qualified": True}
    elif mutation == "known_before_mature": label["known_by_at_utc"] = "2000-01-01T00:00:00+00:00"
    elif mutation == "known_before_unknown_mature":
        label["declared_expected_maturity_at_utc"] = None
        label["known_by_at_utc"] = "2000-01-01T00:00:00+00:00"
    elif mutation == "receipt_before_known":
        label["known_by_at_utc"] = "2026-11-01T00:00:00+00:00"
        label["received_at_utc"] = "2026-10-31T00:00:00+00:00"
        label["receipt_sha256"] = "b" * 64
    elif mutation == "decision": first["decision_id"] = "wrong"
    elif mutation == "revision": label["source_revision_sha256"] = None
    elif mutation == "availability_absent":
        label["known_by_at_utc"] = label["received_at_utc"] = label["receipt_sha256"] = None
    declarations = (pf.bound(first), *declarations[1:])
    assessed = pc.assess_label_readiness(replace(run, label_readiness=declarations), prepared)
    assert assessed["mature_count"] == assessed["pending_count"] == 0
    if mutation in ("21_as_25", "spoof_clock", "known_before_mature", "known_before_unknown_mature", "receipt_before_known", "decision"):
        assert assessed["refused_count"] > 0
    elif mutation in ("unknown_maturity", "revision", "availability_absent"):
        assert assessed["unknown_count"] > 0
    else:
        assert assessed["unqualified_count"] == len(prepared.decisions) * 2


def test_external_references_remain_unqualified_and_rendered_without_raw_evidence(connected_case):
    from engine.research_codegen import prospective_contract as pc
    _, run, prepared, _, _ = _output_expectation_case(connected_case)
    refs = (pf.bound(_freeze_reference(run, prepared)),)
    revised = replace(run, freeze_evidence_references=refs, label_readiness=_label_declarations(run, prepared))
    revised_prepared = b.prepare_synthetic_inputs(revised, commission=connected_case[3]["commission"])
    assert pc.verify_freeze_proposal(revised_prepared.freeze_proposal)["status"] == "UNQUALIFIED"
    assert pc.assess_label_readiness(revised, revised_prepared)["unqualified_count"] == 2 * len(prepared.decisions)
    # Historical outcomes can display a source proposal but never an observed pre-transport binding.
    _, outcome, public, _, receipts = execute_case(connected_case)
    old = replace(outcome, freeze_proposal_sha256=None)
    packet = diagnostic_review_packet(public, engineering_receipts={**receipts, "outcome": old})
    assert packet["engineering_evidence"]["prospective_readiness"]["driver_proposal_binding"] == "UNAVAILABLE"
    assert "Freeze proposal: UNQUALIFIED" in render_markdown([packet], "2026-11-01T00:00:00Z")


@pytest.mark.parametrize("mutation", ["admission", "accepted", "mature", "pending", "extra", "count", "scope"])
def test_public_readiness_cannot_promote_or_discard_labels(connected_case, mutation):
    _, _, public, _, receipts = execute_case(connected_case)
    evidence = diagnostic_review_packet(public, engineering_receipts=receipts)["engineering_evidence"]
    altered = {key: deepcopy(evidence[key]) for key in
        ("schema", "identity", "accounting", "attempts", "controls", "prospective_readiness")}
    readiness = altered["prospective_readiness"]
    if mutation == "admission": readiness["admission_enabled"] = True
    elif mutation == "accepted": readiness["freeze_status"] = "ACCEPTED"
    elif mutation == "mature": readiness["labels"][0]["state"] = "MATURE"
    elif mutation == "pending": readiness["labels"][0]["state"] = "PENDING"
    elif mutation == "extra": readiness["labels"][0]["value"] = 0
    elif mutation == "count": readiness["unknown_count"] -= 1
    else: readiness["scope"] = "PROSPECTIVE"
    with pytest.raises(ValueError):
        diagnostic_review_packet(public, engineering_evidence=altered)


def test_full_label_horizon_is_required_without_evaluation(connected_case):
    from engine.research_codegen import prospective_contract as pc
    _, run, _, _, _ = _output_expectation_case(connected_case)
    trigger = run.session_dates.index(run.positions[2].trigger_date)
    # Keep both declared entry positions and the 21-session reference dependency,
    # omit the later empty formation and the final MAE dependency in this fixture.
    short = replace(run, positions=run.positions[:3], session_dates=run.session_dates[:trigger + 25])
    prepared = b.prepare_synthetic_inputs(short, commission=connected_case[3]["commission"])
    assessment = pc.assess_label_readiness(short, prepared)
    assert assessment["refused_count"] > 0 and assessment["mature_count"] == 0
    assert any("LABEL_HORIZON_INCOMPLETE" in r["missing_evidence"] for r in assessment["labels"])


def test_sparse_formation_ids_are_mapped_without_tuple_indexing(connected_case):
    from engine.research_codegen import prospective_contract as pc
    _, run, prepared, _, _ = _output_expectation_case(connected_case)
    # A declared index is an identity; positional tuple lookup would raise or select wrong data.
    positions = tuple(replace(p, calendar_index=p.calendar_index + 17) for p in run.positions)
    tasks = tuple(replace(t, calendar_index=t.calendar_index + 17) for t in prepared.decisions)
    sparse = replace(run, positions=positions)
    adjusted = replace(prepared, decisions=tasks)
    adjusted = replace(adjusted, freeze_proposal=pc.produce_freeze_proposal(sparse, adjusted))
    result = pc.assess_label_readiness(sparse, adjusted)
    assert result["unknown_count"] == 2 * len(tasks) and result["refused_count"] == 0
    negative = replace(adjusted, decisions=(replace(tasks[0], calendar_index=-1), *tasks[1:]))
    negative = replace(negative, freeze_proposal=pc.produce_freeze_proposal(sparse, negative))
    assert pc.assess_label_readiness(sparse, negative)["refused_count"] == 2


def test_declared_freeze_after_local_issue_refuses_readiness_without_rewriting_observation(connected_case):
    from engine.research_codegen import prospective_contract as pc
    staged, run, _, _, index = _output_expectation_case(connected_case)
    run = replace(run, declared_freeze_at_utc="2100-01-01T00:00:00+00:00")
    prepared = b.prepare_synthetic_inputs(run, commission=connected_case[3]["commission"])
    engine = p01.AccountingGuardedFakeEngine(connected_case, staged)
    outcome = pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
        spec=pf.spec(), config_sha256=run.identity.config_sha256)
    observations = tuple(a.local_observation for a in outcome.attempts)
    raw = pd.connect_prepared_outputs(run, outcome, commission=connected_case[3]["commission"])
    _, public = p01._decode_public(run, connected_case[3]["commission"], raw)
    packet = diagnostic_review_packet(public, engineering_receipts=dict(run=run,
        commission=connected_case[3]["commission"], source=connected_case[1][index], staged=staged, outcome=outcome))
    readiness = packet["engineering_evidence"]["prospective_readiness"]
    assert readiness["status"] == "REFUSED" and readiness["freeze_status"] == "UNQUALIFIED"
    assert all(r["missing_evidence"] == ["DECLARED_FREEZE_AFTER_TRANSPORT_ISSUE"] for r in readiness["labels"])
    assert tuple(a.local_observation for a in outcome.attempts) == observations


@pytest.mark.parametrize("field", ["identity", "decision_inputs_sha256"])
def test_recomputed_but_substituted_proposal_refuses_before_transport(connected_case, field):
    _, run, prepared, _, index = _output_expectation_case(connected_case)
    doc = json.loads(prepared.freeze_proposal.raw)
    if field == "identity": doc["base"]["identity"]["evaluator_sha256"] = "e" * 64
    else: doc["base"][field] = "e" * 64
    doc["proposal_identity_sha256"] = pf.bound(doc["base"]).sha256
    prepared = replace(prepared, freeze_proposal=pf.bound(doc))
    engine = pf.ScriptedFakeEngine()
    with pytest.raises(ValueError, match="PROPOSAL_PREPARATION_MISMATCH"):
        pd.run_prefix_driver(prepared, source=connected_case[1][index], engine=engine,
            spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert engine.calls == []
