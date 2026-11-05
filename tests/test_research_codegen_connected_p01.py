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
from engine.research_codegen import accounting_contract, contracts, plan_engine_provider
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


# Exercise the application-owned cycle, rather than reconstructing its sequence
# in this test. The old cases above remain independent component/oracle checks.
from engine.research_factory import adapter_codegen as cycle
from types import SimpleNamespace


def _cycle_variants(case, *, second_expected="scripted_malformed_output"):
    # Deliberately unusable caller readback: only the adapter's actual staging
    # return may reach preparation, execution, evaluation or review.
    placeholder = SimpleNamespace(expected_generation=case[3]["expected_generation"],
                                  trial_readback=pf.bound({"not": "an accounting receipt"}))
    return tuple(cycle.StagedVariant(descriptor["variant_id"], source,
        _run_for(case, placeholder, index), pf.spec(),
        "diagnostic" if index == 0 else second_expected)
        for index, (descriptor, source) in enumerate(zip(case[2], case[1])))


class ColdLedgerFakeEngine(pf.ScriptedFakeEngine):
    def __init__(self, case, behaviour=None):
        super().__init__(behaviour)
        self.case = case

    def run(self, argv, **kwargs):
        rows = [json.loads(line) for line in
                (self.case[0] / sa.LEDGER_BASENAME).read_bytes().splitlines()]
        assert {row["config_hash"] for row in rows if "config" in row} == {
            descriptor["incumbent_config_hash"] for descriptor in self.case[2]}
        return super().run(argv, **kwargs)


def _cycle_engines(case, first=None, second=None):
    return (ColdLedgerFakeEngine(case, first),
            ColdLedgerFakeEngine(case, second if second is not None else
                                 {"workload": b'{"value":Infinity}'}))


def _cycle(case, variants=None, engines=None, **overrides):
    return cycle.run_staged_cycle(**{**case[3], "variants": variants or _cycle_variants(case),
        "synthetic_test_engines": engines or _cycle_engines(case), **overrides})


def test_application_cycle_plan_providers_join_real_consumers_without_activation(connected_case):
    case = connected_case
    engines, retained = [[], []], set()
    def provider(index):
        def factory(plan):
            class Guarded(ColdLedgerFakeEngine):
                def run(self, argv, **kwargs):
                    if argv[1] == "start":
                        assert (plan.operation_id, pf.CID) in retained
                    return super().run(argv, **kwargs)
            fake = Guarded(case, None if index == 0 else {"workload": b'{"value":Infinity}'})
            engines[index].append(fake)
            return fake
        def receipt(plan, cid):
            retained.add((plan.operation_id, cid))
            return True
        return plan_engine_provider.PlanBoundEngineProvider(executor_for_plan=factory, retain_container=receipt)
    providers = tuple(provider(i) for i in range(2))
    result = cycle.run_staged_cycle(**case[3], variants=_cycle_variants(case),
                                     synthetic_test_providers=providers)
    assert result.status == "DIAGNOSTIC_CYCLE_COMPLETE"
    assert [len(group) for group in engines] == [6, 1]
    assert all(fake.creates == 1 for group in engines for fake in group)
    assert len(retained) == 7
    assert all(row.review_packet is not None for row in result.variants)
    assert not result.physical_acceptance and not result.authority_granted
    assert result.scientific_acceptance == "UNQUALIFIED"
    _assert_full_cold_accounting(case, result.staged)


def test_application_cycle_provider_unknown_stops_selection_and_preserves_accounting(connected_case):
    case = connected_case
    selected = []
    class Unknown(ColdLedgerFakeEngine):
        def run(self, argv, **kwargs):
            if argv[1] == "create":
                return pf.tp.EngineCommandResult(None, b"", b"", kwargs["deadline_seconds"],
                                                  kwargs["output_cap_bytes"])
            raise AssertionError("no guessed lifecycle command")
    def factory(plan):
        selected.append(plan)
        return Unknown(case)
    provider = plan_engine_provider.PlanBoundEngineProvider(executor_for_plan=factory,
                                            retain_container=lambda p, c: True)
    result = cycle.run_staged_cycle(**case[3], variants=_cycle_variants(case),
                                     synthetic_test_providers=(provider, provider))
    assert result.status == "EFFECT_UNKNOWN" and len(selected) == 1
    assert result.variants[1].status == "NOT_ATTEMPTED_AFTER_REFUSAL"
    assert len(result.variants[0].outcome.attempts) == 1
    with pytest.raises(pf.tp.TransportStateError): provider.engine_for(selected[0])
    _assert_full_cold_accounting(case, result.staged)


def test_application_cycle_provider_map_is_explicit_and_default_remains_dormant(connected_case):
    case = connected_case
    variants = _cycle_variants(case)
    provider = plan_engine_provider.PlanBoundEngineProvider()
    for sources in ({"synthetic_test_engines": _cycle_engines(case),
                     "synthetic_test_providers": (provider, provider)},
                    {"synthetic_test_providers": (provider, object())}):
        with pytest.raises(cycle.StagedCycleRefused):
            cycle.run_staged_cycle(**case[3], variants=variants, **sources)
        assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""
    result = cycle.run_staged_cycle(**case[3], variants=variants,
                                     synthetic_test_providers=(provider, provider))
    assert result.status == "REFUSED" and result.variants[0].outcome.attempts == ()
    assert result.variants[1].status == "NOT_ATTEMPTED_AFTER_REFUSAL"
    assert not result.physical_acceptance
    _assert_full_cold_accounting(case, result.staged)


def test_application_cycle_accounts_once_and_reaches_review(connected_case, monkeypatch):
    case = connected_case
    engines = _cycle_engines(case)
    original = sa.stage_synthetic_generation
    stages = []

    def stage(**kwargs):
        result = original(**kwargs)
        stages.append(result)
        return result

    monkeypatch.setattr(sa, "stage_synthetic_generation", stage)
    result = _cycle(case, engines=engines)
    assert len(stages) == 1 and result.staged is stages[0]
    assert result.status == "DIAGNOSTIC_CYCLE_COMPLETE"
    assert result.scope == "SYNTHETIC_ENGINEERING_ONLY"
    assert not result.physical_acceptance and not result.authority_granted
    assert result.scientific_acceptance == "UNQUALIFIED"
    _assert_full_cold_accounting(case, result.staged)
    assert [engine.creates for engine in engines] == [6, 1]
    for row in result.variants:
        assert row.status == "EXPECTED_ENGINEERING_RESULT"
        assert row.run.trial_readback is result.staged.trial_readback
        assert row.run.expected_generation is result.staged.expected_generation
        assert row.review_packet["allowed_decisions"] == []
        evidence = row.review_packet["engineering_evidence"]
        assert evidence["accounting"]["trial_readback_sha256"] == result.staged.trial_readback.sha256
        assert not evidence["physical_acceptance"]
        # Scripted refusal is never claimed as observed temporal leakage detection.
        assert evidence["controls"][2]["status"] == "NOT_RUN"
        assert all(attempt.cleanup_confirmed for attempt in row.outcome.attempts)
    good, bad = result.variants
    assert good.review_packet["frozen_gate_metrics"]["paired_mean_improvement"] == pytest.approx(.175)
    assert bad.review_packet["frozen_gate_metrics"]["paired_mean_improvement"] is None
    assert bad.review_packet["diagnostic"]["status"] == "REFUSED"


@pytest.mark.parametrize("mutation", ["variant_omitted", "config_omitted", "source_swapped"])
def test_application_cycle_rejects_incomplete_set_before_effects(connected_case, mutation):
    case = connected_case
    variants, engines = _cycle_variants(case), _cycle_engines(case)
    changes = {}
    if mutation == "variant_omitted":
        variants = variants[:1]
    elif mutation == "config_omitted":
        changes["configurations"] = case[3]["configurations"][:1]
    else:
        variants = (variants[0], replace(variants[1], source=variants[0].source))
    with pytest.raises(cycle.StagedCycleRefused):
        _cycle(case, variants, engines, **changes)
    assert all(engine.calls == [] for engine in engines)
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""


def test_application_cycle_preflights_later_inputs_before_first_attempt(connected_case):
    case = connected_case
    variants, engines = _cycle_variants(case), _cycle_engines(case)
    variants = (variants[0], replace(variants[1], run=replace(variants[1].run, schedules=())))
    result = _cycle(case, variants, engines)
    assert result.status == "REFUSED"
    assert {row.status for row in result.variants} == {"NOT_ATTEMPTED_INVALID_BATCH"}
    assert all(engine.calls == [] for engine in engines)
    # Generated choices remain charged even though no execution was attempted.
    _assert_full_cold_accounting(case, result.staged)


def test_application_cycle_unknown_stops_later_variants_and_retains_all_charges(connected_case):
    case = connected_case
    engines = _cycle_engines(case, first={"start_rc": 7})
    result = _cycle(case, engines=engines)
    assert result.status == "EFFECT_UNKNOWN"
    first, second = result.variants
    assert first.status == "EFFECT_UNKNOWN"
    assert len(first.outcome.attempts) == 1 and first.outcome.attempts[0].execution_uncertain
    assert first.review_packet["diagnostic"]["status"] == "REFUSED"
    assert second.status == "NOT_ATTEMPTED_AFTER_REFUSAL" and second.outcome is None
    assert engines[1].calls == []
    _assert_full_cold_accounting(case, result.staged)


def test_application_cycle_partial_output_is_not_salvaged(connected_case):
    case = connected_case
    variants = _cycle_variants(case)
    variants = (replace(variants[0], spec=pf.spec(max_attempts=1)), variants[1])
    engines = _cycle_engines(case)
    result = _cycle(case, variants, engines)
    assert result.status == "REFUSED"
    first, second = result.variants
    assert first.outcome.outputs == () and len(first.outcome.attempts) == 1
    assert first.review_packet["frozen_gate_metrics"]["paired_mean_improvement"] is None
    assert first.outcome.refusal_reasons == ("ATTEMPT_BUDGET_EXHAUSTED",)
    assert second.outcome is None and engines[1].calls == []


def test_transport_failure_does_not_pass_scripted_bad_control(connected_case):
    case = connected_case
    engines = _cycle_engines(case, second={"exit_state": {
        "Running": False, "ExitCode": 7, "OOMKilled": False}})
    result = _cycle(case, engines=engines)
    assert result.status == "REFUSED" and result.variants[1].status == "REFUSED"
    assert result.variants[1].outcome.refusal_reasons == ("TRANSPORT_ATTEMPT_NOT_CONFIRMED",)
    assert result.variants[1].review_packet["engineering_evidence"]["controls"][2]["status"] == "NOT_RUN"


def test_application_cycle_default_and_cli_refuse_without_effects(connected_case, capsys):
    case = connected_case
    with pytest.raises(cycle.StagedCycleRefused, match="RUNTIME_QUALIFICATION_UNAVAILABLE"):
        cycle.run_staged_cycle(**case[3], variants=_cycle_variants(case))
    from scripts.research_codegen_cycle import main
    assert main([]) == 78
    assert json.loads(capsys.readouterr().out)["execution_enabled"] is False
    with pytest.raises(SystemExit) as rejected:
        main(["--qualified"])
    assert rejected.value.code == 2
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""


def test_application_cycle_never_replays_existing_unknown_generation(connected_case):
    case = connected_case
    first = _cycle(case, engines=_cycle_engines(case, first={"start_rc": 7}))
    assert first.status == "EFFECT_UNKNOWN"
    before = (case[0] / sa.LEDGER_BASENAME).read_bytes()
    engines = _cycle_engines(case)
    second = _cycle(case, engines=engines, run_id="renamed-receipt-is-not-replay-authority")
    assert second.status == "RECONCILIATION_REQUIRED"
    assert all(row.status == "NOT_ATTEMPTED_EXISTING_GENERATION" for row in second.variants)
    assert all(engine.calls == [] for engine in engines)
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == before


def test_application_cycle_partial_existing_generation_does_not_replay(connected_case):
    case = connected_case
    expected = json.loads(case[3]["expected_generation"].raw)
    expected["variants"] = expected["variants"][:1]
    sa.stage_synthetic_generation(**{**case[3], "expected_generation": pf.bound(expected),
                                   "configurations": case[3]["configurations"][:1]})
    engines = _cycle_engines(case)
    result = _cycle(case, engines=engines)
    assert result.staged.newly_recorded_count == 1
    assert result.status == "RECONCILIATION_REQUIRED"
    assert all(engine.calls == [] for engine in engines)
    _assert_full_cold_accounting(case, result.staged)


def test_application_cycle_retains_attempt_if_review_consumer_refuses(connected_case, monkeypatch):
    case = connected_case
    engines = _cycle_engines(case)

    def refuse(*args, **kwargs):
        raise ValueError("fixture consumer failure")

    monkeypatch.setattr(cycle, "diagnostic_review_packet", refuse)
    result = _cycle(case, engines=engines)
    assert result.status == "REFUSED"
    first, later = result.variants
    assert first.reason == "DIAGNOSTIC_COMPOSITION_REFUSED"
    assert first.outcome.completed and len(first.outcome.attempts) == 6
    assert first.diagnostic is not None and first.review_packet is None
    assert later.outcome is None and engines[1].calls == []


def _declared_variants(case):
    from tests.test_research_codegen_contracts import role_declarations
    variants = []
    for variant in _cycle_variants(case):
        declared = replace(variant.run,
            role_declarations=pf.bound(role_declarations(json.loads(variant.run.manifest.raw))))
        assessment = b.prepare_synthetic_identity_assessment(declared, commission=case[3]["commission"])
        variants.append(replace(variant, run=replace(declared, identity_assessment=assessment)))
    return tuple(variants)


def test_declared_cycle_preserves_private_assessment_through_existing_consumers(connected_case):
    from engine.research_factory.review_queue import diagnostic_review_packet
    case = connected_case
    variants = _declared_variants(case)
    # The declaration helper requires no invented accounting receipt or effect.
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""
    result = _cycle(case, variants=variants)
    assert result.status == "DIAGNOSTIC_CYCLE_COMPLETE"
    commission = case[3]["commission"]
    for variant, row in zip(variants, result.variants):
        assert row.run.identity_assessment is variant.run.identity_assessment
        assert json.loads(row.run.identity_assessment.raw)["status"] == "DECLARED_SEPARATION_UNATTESTED"
        # The exact same receipt crosses unchanged output/review consumers.
        legacy = replace(row.run, role_declarations=None, identity_assessment=None)
        raw = (pd.connect_prepared_outputs(legacy, row.outcome, commission=commission)
               if row.outcome.completed else b.compute_synthetic_diagnostic(legacy, commission=commission))
        assert raw == row.diagnostic
        _, public = _decode_public(legacy, commission, raw)
        packet = diagnostic_review_packet(public, engineering_receipts=dict(run=legacy,
            commission=commission, source=variant.source, staged=result.staged, outcome=row.outcome))
        assert packet == row.review_packet
        prepared = b.prepare_synthetic_inputs(row.run, commission=commission)
        assert not hasattr(prepared, "identity_assessment")
        assert not hasattr(prepared, "role_declarations")
        encoded = json.dumps(packet)
        for role in json.loads(row.run.role_declarations.raw)["roles"].values():
            assert role["principal_sha256"] not in encoded
            assert all(role["principal_sha256"].encode() not in task.input_bytes.raw
                       for task in prepared.decisions)
        assert public["authority_granted"] is False


@pytest.mark.parametrize("damage", ["missing", "stale", "invalid_roles"])
def test_declared_cycle_invalid_later_assessment_prevents_all_transport(connected_case, damage):
    case = connected_case
    first, later = _declared_variants(case)
    if damage == "missing":
        later = replace(later, run=replace(later.run, identity_assessment=None))
    elif damage == "stale":
        later = replace(later, run=replace(later.run, identity_assessment=first.run.identity_assessment))
    else:
        declaration = json.loads(later.run.role_declarations.raw)
        declaration["roles"]["execution"]["capabilities"] = ["contents:write"]
        later = replace(later, run=replace(later.run, role_declarations=pf.bound(declaration)))
    engines = _cycle_engines(case)
    result = _cycle(case, variants=(first, later), engines=engines)
    assert result.status == "REFUSED"
    assert all(row.status == "NOT_ATTEMPTED_INVALID_BATCH" for row in result.variants)
    assert all(engine.calls == [] for engine in engines)
    _assert_full_cold_accounting(case, result.staged)
