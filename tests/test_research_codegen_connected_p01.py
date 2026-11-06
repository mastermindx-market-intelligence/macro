"""Actual staging -> prefix -> diagnostic join, with invented engineering data.

The real incumbent ledger, staging adapter, driver and bridge are exercised.
Transport is always the accepted scripted fake. Candidate source remains opaque;
neither feature nor RUNNER_SOURCE is executed here. The refusal is a scripted
nonfinite plumbing control, not observed temporal bias detection. No holdout data,
Vault calls, canonical ledger, publication or physical acceptance is involved.
"""
from dataclasses import replace
import hashlib
import json
import os

import pytest

from engine import trial_ledger
from engine.research_codegen import accounting_contract, contracts
from engine.research_codegen import bridge as b, prefix_driver as pd
from engine.research_codegen import staging_accounting as sa
from tests import test_research_codegen_prefix_driver as pf


ROOT = "01a1333c-a475-7052-95a8-72a88eb8c17b"
FAMILY = "rf.synthetic.connected_p01"


def _initialize_new_history(path):
    """Explicit fixture owner creates and syncs its NEW history before anchor."""
    path.mkdir(mode=0o700)
    fd = os.open(path / sa.LEDGER_BASENAME,
                 os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@pytest.fixture
def connected_case(tmp_path):
    path = tmp_path.resolve() / "explicit-new-connected-family"
    _initialize_new_history(path)
    commission = b.SyntheticTestCommission(ROOT, str(path))
    anchor = pf.bound((path / sa.LEDGER_BASENAME).read_bytes())
    assert anchor.raw == b"" and anchor.size == 0
    sources = (pf.source_binding(pf.KNOWN_ANSWER_SOURCE),
               pf.source_binding(pf.TEMPORAL_BAD_SOURCE))
    names = ("fixture-known-answer", "fixture-controlled-refusal")
    configs = tuple(dict(source_sha256=source.sha256, parameters={"choice": n},
                         information_set_sha256=pf.hexid(2), horizon_id="h21",
                         objective_id="adverse_pair")
                    for n, source in enumerate(sources, 1))
    descriptors = tuple(dict(variant_id=name, source_sha256=source.sha256,
                             config_sha256=contracts.canonical_json_sha256(config),
                             incumbent_config_hash=trial_ledger._hash(FAMILY, config))
                        for name, source, config in zip(names, sources, configs))
    expected = pf.bound(dict(schema="research_codegen.expected_generation.v1",
        original_root_id=ROOT, family=FAMILY,
        protocol_sha256=pf.trusted_protocol()["protocol_sha256"],
        history_anchor_sha256=anchor.sha256, variants=list(descriptors),
        inherited_variants=[], trial_ceiling=2, vault_required=False,
        vault_request=None))
    configurations = tuple(sa.ScientificConfigBinding(name, source.sha256,
                                                      pf.bound(config))
                           for name, source, config in zip(names, sources, configs))
    kwargs = dict(commission=commission, run_id="connected-engineering-first",
                  expected_generation=expected, configurations=configurations,
                  history_anchor=anchor)
    return path, sources, descriptors, kwargs


def _stage(case, **changes):
    return sa.stage_synthetic_generation(**{**case[3], **changes})


def _assert_full_cold_accounting(case, staged):
    """Independent raw reread, repeated before EVERY fake transport call."""
    raw = (case[0] / sa.LEDGER_BASENAME).read_bytes()
    assert raw == staged.raw_snapshot.raw
    assert hashlib.sha256(raw).hexdigest() == staged.raw_snapshot.sha256
    assert len(raw) == staged.raw_snapshot.size
    rows = tuple(json.loads(line) for line in raw.splitlines())
    scientific = tuple(row for row in rows if "config" in row)
    assert len(scientific) == 2
    assert {row["config_hash"] for row in scientific} == {
        item["incumbent_config_hash"] for item in case[2]}
    assert {row["config"]["source_sha256"] for row in scientific} == {
        source.sha256 for source in case[1]}
    trial = json.loads(staged.trial_readback.raw)
    assert [trial[key] for key in ("literal_n", "declared_floor", "effective_n")] == [2, 2, 2]
    assert len(trial["recorded_variants"]) == 2
    assert trial["snapshot_sha256"] == staged.raw_snapshot.sha256
    assert trial["snapshot_bytes"] == staged.raw_snapshot.size
    assessment = accounting_contract.assess_accounting_references(
        json.loads(staged.expected_generation.raw), trial_readback=trial)
    assert assessment["status"] == "STRUCTURALLY_COMPLETE_DISABLED"
    assert assessment["owner_origin_and_durability"] == "UNQUALIFIED"
    assert not any(assessment[key] for key in
                   ("generation_enabled", "execution_enabled", "evaluation_enabled",
                    "authority_granted"))
    durable = json.loads(staged.durable_readback_observation.raw)
    assert durable["file_fsync_observed"] and durable["directory_fsync_observed"]
    assert durable["cold_readback_observed"]
    assert durable["durability_state"] == (
        "DURABLE_GENERATION_RECORDED" if staged.newly_recorded_count
        else "DURABLE_RECONCILED")


class AccountingGuardedFakeEngine(pf.ScriptedFakeEngine):
    def __init__(self, case, staged, behaviour=None):
        super().__init__(behaviour=behaviour)
        self._case = case
        self._staged = staged
        self.charge_checks = 0

    def run(self, argv, *, deadline_seconds, output_cap_bytes):
        _assert_full_cold_accounting(self._case, self._staged)
        self.charge_checks += 1
        return super().run(argv, deadline_seconds=deadline_seconds,
                           output_cap_bytes=output_cap_bytes)


def _run_for(case, staged, index):
    """Rebind incumbent fixture identities; preserve its causal/schedule logic."""
    source = case[1][index]
    descriptor = case[2][index]
    run, _, _, _, _ = pf.make_case(source_sha256=source.sha256)
    protocol = json.loads(run.protocol.raw)
    protocol.update(original_root_id=ROOT, trial_family=FAMILY)
    manifest = json.loads(run.manifest.raw)
    candidate = "rf-codegen-p01-known" if index == 0 else "rf-codegen-p01-controlled-refusal"
    manifest.update(candidate_id=candidate, trial_family=FAMILY,
                    config_sha256=descriptor["config_sha256"])
    manifest["lineage"]["original_root_id"] = ROOT
    decisions = []
    for decision in run.decisions:
        request = json.loads(decision.request.raw)
        request["candidate_id"] = candidate
        decisions.append(replace(decision, request=pf.bound(request)))
    schedules = []
    for binding in run.schedules:
        schedule = json.loads(binding.raw)
        schedule["candidate_id"] = candidate
        schedules.append(pf.bound(schedule))
    identity = replace(run.identity, artifact_path=str(case[0] / (candidate + ".json")),
                       diagnostic_id=candidate + "-diagnostic",
                       original_root_id=ROOT, candidate_id=candidate,
                       source_sha256=source.sha256,
                       config_sha256=descriptor["config_sha256"])
    joined = replace(run, identity=identity, manifest=pf.bound(manifest),
        protocol=pf.bound(protocol), owner_references=pf.bound(pf.owner_receipts(manifest)),
        expected_generation=staged.expected_generation,
        trial_readback=staged.trial_readback,
        decisions=tuple(decisions), schedules=tuple(schedules))
    assert joined.expected_generation is staged.expected_generation
    assert joined.trial_readback is staged.trial_readback
    assert joined.outputs == ()
    return joined


def _decode_public(run, commission, raw):
    binding = replace(run.identity, artifact_sha256=hashlib.sha256(raw).hexdigest(),
                      artifact_bytes=len(raw))
    readback = b.decode_bound_artifact(raw, expected=binding, commission=commission)
    public = b.public_diagnostic(readback)
    assert public["scientific_acceptance"] == "UNQUALIFIED"
    assert not any(public[key] for key in ("generation_enabled", "execution_enabled",
                                          "evaluation_enabled", "authority_granted"))
    assert all(token not in pf.encoded(public).decode() for token in
               ("XLB", "observations", "decision_ids", "source_b64", "cutoff",
                "trial_ledger.jsonl", "source_dispositions"))
    return readback, public


def test_actual_accounting_before_both_prefix_outcomes_and_diagnostics(connected_case):
    case = connected_case
    staged = _stage(case)
    assert staged.newly_recorded_count == 2
    assert staged.expected_generation is case[3]["expected_generation"]
    _assert_full_cold_accounting(case, staged)
    original = (case[0] / sa.LEDGER_BASENAME).read_bytes()
    commission = case[3]["commission"]

    good = _run_for(case, staged, 0)
    prepared = b.prepare_synthetic_inputs(good, commission=commission)
    assert len(prepared.decisions) == 6 and len(prepared.schedules) == 4
    good_engine = AccountingGuardedFakeEngine(case, staged)
    outcome = pd.run_prefix_driver(prepared, source=case[1][0], engine=good_engine,
                                  spec=pf.spec(), config_sha256=good.identity.config_sha256)
    assert outcome.completed and outcome.refusal_reasons == ()
    assert len(outcome.attempts) == 6 and good_engine.creates == 6
    assert good_engine.charge_checks == len(good_engine.calls) > 0
    assert all(attempt.transport_plan is not None
               and attempt.transport_attempt.cleanup_confirmed
               and not attempt.execution_uncertain for attempt in outcome.attempts)
    assert all(len(envelope["observations"]) == 63 for envelope in good_engine.envelopes)
    raw = pd.connect_prepared_outputs(good, outcome, commission=commission)
    readback, _ = _decode_public(good, commission, raw)
    aggregate = dict(readback.aggregates)
    assert readback.status == "DIAGNOSTIC_ONLY"
    assert [aggregate[key] for key in ("scheduled_formation_count",
        "source_excluded_formation_count", "source_qualified_formation_count",
        "no_opportunity_formation_count", "opportunity_formation_count",
        "paired_formation_count")] == [4, 1, 3, 1, 2, 2]
    assert aggregate["paired_mean_baseline_adverse_loss"] == pytest.approx(.3)
    assert aggregate["paired_mean_selected_adverse_loss"] == pytest.approx(.125)
    assert aggregate["paired_mean_improvement"] == pytest.approx(.175)

    bad = _run_for(case, staged, 1)
    bad_prepared = b.prepare_synthetic_inputs(bad, commission=commission)
    # Opaque temporal-bad bytes are NOT run. This is an injected nonfinite control.
    nonfinite = json.dumps(dict(schema="research_codegen.output.v1",
        candidate_id=bad.identity.candidate_id, fold_id="invented", entity_id="XLB",
        input_policy_sha256=bad.identity.input_policy_sha256,
        rows=[dict(decision_id=bad_prepared.decisions[0].decision_id,
                   status="available", value=float("inf"), reason=None)]),
        allow_nan=True).encode()
    bad_engine = AccountingGuardedFakeEngine(case, staged, {"workload": nonfinite})
    refused = pd.run_prefix_driver(bad_prepared, source=case[1][1], engine=bad_engine,
                                  spec=pf.spec(), config_sha256=bad.identity.config_sha256)
    assert not refused.completed and refused.outputs == ()
    assert len(refused.attempts) == 1 and bad_engine.creates == 1
    assert bad_engine.charge_checks == len(bad_engine.calls) > 0
    assert refused.attempts[0].cleanup_confirmed
    assert refused.refusal_reasons[0] in (
        "OUTPUT_CONTRACT_REFUSED", "INVALID_OUTPUT_JSON", "NONFINITE_JSON")
    with pytest.raises(pd.PrefixDriverRefused, match="DRIVER_OUTCOME_INCOMPLETE"):
        pd.connect_prepared_outputs(bad, refused, commission=commission)
    # The unchanged full run remains empty/refused; successful cells are not salvaged.
    bad_raw = b.compute_synthetic_diagnostic(bad, commission=commission)
    bad_readback, _ = _decode_public(bad, commission, bad_raw)
    bad_aggregate = dict(bad_readback.aggregates)
    assert bad_readback.status == "REFUSED"
    assert bad_aggregate["refusal_count"] > 0
    assert bad_aggregate["paired_mean_improvement"] is None
    assert [bad_aggregate[key] for key in ("scheduled_formation_count",
        "source_excluded_formation_count", "source_qualified_formation_count")] == [4, 1, 3]
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == original
    _assert_full_cold_accounting(case, staged)


def test_same_original_history_replay_keeps_both_charges_without_new_path(connected_case):
    case = connected_case
    first = _stage(case)
    replay = _stage(case, run_id="renamed-receipt-only")
    assert replay.newly_recorded_count == 0
    assert replay.expected_generation is first.expected_generation
    assert replay.raw_snapshot.raw == first.raw_snapshot.raw
    assert not (case[0] / "renamed-receipt-only").exists()
    _assert_full_cold_accounting(case, replay)
    run = _run_for(case, replay, 0)
    engine = AccountingGuardedFakeEngine(case, replay)
    result = pd.run_prefix_driver(b.prepare_synthetic_inputs(run, commission=case[3]["commission"]),
        source=case[1][0], engine=engine, spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert result.completed and engine.charge_checks == len(engine.calls) > 0
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == first.raw_snapshot.raw


def test_omitted_refusal_configuration_blocks_connected_driver(connected_case, monkeypatch):
    case = connected_case
    driver_calls = []
    monkeypatch.setattr(pd, "run_prefix_driver", lambda *args, **kwargs: driver_calls.append(1))
    with pytest.raises(sa.StagingAccountingRefused, match="CONFIG_MAP_INCOMPLETE"):
        staged = _stage(case, configurations=case[3]["configurations"][:1])
        run = _run_for(case, staged, 0)
        pd.run_prefix_driver(b.prepare_synthetic_inputs(run, commission=case[3]["commission"]),
            source=case[1][0], engine=AccountingGuardedFakeEngine(case, staged),
            spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert driver_calls == []
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""


def test_missing_original_history_blocks_driver_without_recreation(connected_case, monkeypatch):
    case = connected_case
    _stage(case)
    ledger = case[0] / sa.LEDGER_BASENAME
    ledger.unlink()
    driver_calls = []
    monkeypatch.setattr(pd, "run_prefix_driver", lambda *args, **kwargs: driver_calls.append(1))
    with pytest.raises(sa.StagingAccountingRefused, match="ORIGINAL_HISTORY_MISSING"):
        staged = _stage(case, run_id="renamed-after-missing")
        run = _run_for(case, staged, 0)
        pd.run_prefix_driver(b.prepare_synthetic_inputs(run, commission=case[3]["commission"]),
            source=case[1][0], engine=AccountingGuardedFakeEngine(case, staged),
            spec=pf.spec(), config_sha256=run.identity.config_sha256)
    assert driver_calls == [] and not ledger.exists()
    assert not (case[0] / "renamed-after-missing").exists()
