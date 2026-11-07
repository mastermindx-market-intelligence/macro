"""Real synthetic COMPLETE owner -> exact evidence -> actual Factory runner.

Original S3 deployment/source-verifier stand-ins remain explicit. No installed
admission, provider, annotation or production performance is asserted.
"""
import copy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import time

import pytest

from engine.research_factory import adapter_market_memory_fitted_evidence as fitted
from engine.research_factory import adapter_market_memory_evidence as adapter
from engine.research_factory import market_memory_fitted_factory_use as owner
from engine.research_factory import market_memory_fitted_persistence as persistence
from engine.research_factory import schema
from engine.neuralweb import market_memory_fitted_evidence as evidence
from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as house
from scripts import research_factory_run as runner
from tests.test_market_memory_fitted_factory_use import (
    completed_world, fitted_world, retained_owner, native_training, selection, records,
    native_owner, store_state,
)


def forbidden(*args, **kwargs):
    pytest.fail("context-only path attempted private work or lifecycle write")


@pytest.mark.parametrize("mode,dry,count", [
    (False, True, False), (None, True, False), (0, True, False), (1, True, False),
    ("true", True, False), (True, False, False), (True, 1, False), (True, None, False),
    (True, True, True), (True, True, 0), (True, True, None), (True, True, "false")])
@pytest.mark.parametrize("subclass", [False, True])
def test_runner_rejects_fitted_execution_modes_before_private_work(tmp_path, monkeypatch, mode, dry, count, subclass):
    class Child(fitted.FittedMarketMemoryEvidenceInput):
        pass
    value = object.__new__(Child if subclass else fitted.FittedMarketMemoryEvidenceInput)
    monkeypatch.setattr(adapter, "build_market_memory_evidence_attachment", forbidden)
    monkeypatch.setattr(runner, "load_candidates", forbidden)
    with pytest.raises(ValueError):
        runner.run(rf_dir=tmp_path, data_dir=tmp_path, market_memory_inputs=(value,),
            market_memory_only=mode, dry_run=dry, count=count)


def test_closed_types_refuse_dicts_and_subclasses_without_private_io(tmp_path, monkeypatch):
    class Child(fitted.FittedMarketMemoryEvidenceInput):
        pass
    monkeypatch.setattr(owner.FittedFactoryUsePolicy, "disclose_binding", forbidden)
    for value in ({}, object.__new__(Child)):
        with pytest.raises((ValueError, AttributeError)):
            adapter.build_market_memory_evidence_attachment(value)
    for value in ({}, object.__new__(fitted.FittedMarketMemoryEvidenceAttachmentCapability)):
        with pytest.raises((ValueError, AttributeError)):
            adapter.disclose_market_memory_evidence_attachment(value)


@pytest.mark.parametrize("marker", [fitted.SCHEMA, owner.SERVICE_SCHEMA, owner.CONSUMER,
    "mmrffittedevidence_" + "a" * 64,
    "market_memory.fitted_evidence_packet.v1", "market_memory.fitted_episode_retrieval.v2",
    "market_memory.fitted_normalizer.v2", "market_memory.fitted_exact_index.v2",
    *[prefix + "a" * 64 for prefix in ("mmfittedevidence_", "mmfittedretrieval_",
        "mmfittedmethod_", "mmfittednormalizer_", "mmfittedindex_")]])
def test_fitted_markers_cannot_smuggle_into_ordinary_candidates(marker):
    from tests.test_research_factory_schema import _base_candidate
    candidate = _base_candidate()
    assert not schema.validate_candidate(candidate)
    candidate["artifacts"] = {"nested": {"value": marker}}
    assert schema.validate_candidate(candidate)


def test_genuine_complete_to_actual_context_only_runner_and_refusals(completed_world, tmp_path, monkeypatch):
    world = completed_world
    policy = world["policy"]
    counts = {"policy_check": 0, "owner_recheck": 0, "native_context": 0, "source_verify": 0}
    def instrument(obj, name, key):
        original = getattr(obj, name)
        def counted(*args, **kwargs):
            counts[key] += 1
            return original(*args, **kwargs)
        monkeypatch.setattr(obj, name, counted)
    instrument(owner.FittedFactoryUsePolicy, "check", "policy_check")
    instrument(owner.FittedFactoryUsePolicy, "_recheck_owner", "owner_recheck")
    instrument(persistence, "_load_context", "native_context")
    instrument(owner.owner, "_verify_source", "source_verify")
    before = store_state(world)
    private_before = {str(p.relative_to(world["root"])): p.read_bytes()
                      for p in world["root"].rglob("*") if p.is_file()}
    for name in ("persist_registered_fit", "retain_registered_fitted_query", "initialize_registered_fit_accounting"):
        monkeypatch.setattr(persistence, name, forbidden)
    for name in ("reserve", "finish", "initialize"):
        monkeypatch.setattr(persistence.ReservationStore, name, forbidden)
    monkeypatch.setattr(runner, "load_candidates", forbidden)
    monkeypatch.setattr(runner, "filter_registered", forbidden)
    monkeypatch.setattr(runner, "_perform_transition", forbidden)
    wall, cpu = time.perf_counter(), time.process_time()
    selection_cap, _ = policy.reopen_registered_fitted_query()
    native = retrieval.disclose_fitted_retrieval(selection_cap, policy=policy)
    reader, pin = native_owner(tmp_path)
    packet_cap = evidence.build_fitted_evidence_packet(selection_cap, reader, pin, policy=policy)
    request = fitted.FittedMarketMemoryEvidenceInput(world["trial_body"],
        world["service"]["candidate_created_at"], "2026-10-14T11:00:00.000000Z",
        selection_cap, packet_cap, policy)
    summary = runner.run(rf_dir=tmp_path / "factory", data_dir=tmp_path,
        market_memory_inputs=(request,), market_memory_only=True, dry_run=True, count=False)
    metric = {"wall_seconds": time.perf_counter() - wall, "cpu_seconds": time.process_time() - cpu,
              "counts": dict(counts), "scope": "synthetic COMPLETE through actual runner; source-verifier stand-in"}
    print("FITTED_JOIN_COST " + json.dumps(metric, sort_keys=True), flush=True)
    value = summary["contextual_evidence"][0]
    assert value["schema"] == fitted.SCHEMA
    assert value["fitted_retrieval_join"] == native
    assert value["candidate"] == json.loads(policy._candidate_bytes)
    assert value["trial_binding"]["trial_original_query_provenance"] == "not_established"
    assert value["lifecycle"] == fitted.LIFECYCLE
    assert summary["n_candidates"] == summary["n_registered"] == summary["transitions_attempted"] == 0
    assert summary["effective_count"] is False and summary["routes"][0]["action"] == "no_action"
    assert not schema.validate_market_memory_fitted_evidence_attachment(value)
    assert store_state(world) == before
    assert {str(p.relative_to(world["root"])): p.read_bytes()
            for p in world["root"].rglob("*") if p.is_file()} == private_before
    for mutation in ("lifecycle", "candidate", "sourceorder", "claim"):
        bad = copy.deepcopy(value)
        if mutation == "lifecycle": bad["lifecycle"]["count_allowed"] = True
        elif mutation == "candidate": bad["candidate"]["status"] = "registered"
        elif mutation == "sourceorder": bad["fitted_evidence_join"]["source_cards"].reverse()
        else: bad["fitted_retrieval_join"]["claims"]["operational_study_admission"] = True
        assert schema.validate_market_memory_fitted_evidence_attachment(bad)
    # Trial mismatch refuses before the expensive COMPLETE reopen.
    with monkeypatch.context() as change:
        change.setattr(owner.FittedFactoryUsePolicy, "reopen_registered_fitted_query", forbidden)
        with pytest.raises(ValueError, match="original_trial"):
            adapter.build_market_memory_evidence_attachment(replace(request, exact_trial_registration_bytes=b"{}"))
    cap = fitted.FittedMarketMemoryEvidenceAttachmentCapability(cohort.canonical(value), request, _key=fitted._TOKEN)
    object.__setattr__(cap, "_digest", "f" * 64)
    with pytest.raises(ValueError, match="owner_verified"):
        adapter.disclose_market_memory_evidence_attachment(cap)
    # Genuine current control revocation also stops a cached request before read.
    world["registration_path"].write_bytes(b"{}")
    with pytest.raises(house.RetainedUseError, match="source_use_registration_unavailable"):
        adapter.build_market_memory_evidence_attachment(request)


def test_other_genuine_selection_in_same_scope_is_not_original_complete(completed_world, monkeypatch):
    world = completed_world
    policy = world["policy"]
    original, _ = policy.reopen_registered_fitted_query()
    base = original._eligibility
    method = persistence.retrieval.baseline.RetainedContextMethodSpec(5, 5, world["spec"]["mode"])
    other = retrieval.retrieve_fitted_contexts(original._normalizer, base._cohort, base._query,
        policy=policy, k=1, eligibility=method)
    assert retrieval.disclose_fitted_retrieval(other, policy=policy)["query_owner"] == world["result"]["value"]["result"]["query_owner"]
    before = store_state(world)
    monkeypatch.setattr(persistence, "retain_registered_fitted_query", forbidden)
    # Hostile evidence is never inspected: the different genuine selection
    # must fail the original COMPLETE join before packet disclosure.
    hostile_packet = object.__new__(evidence.FittedEvidenceCapability)
    monkeypatch.setattr(evidence, "disclose_fitted_evidence_packet", forbidden)
    request = fitted.FittedMarketMemoryEvidenceInput(world["trial_body"],
        world["service"]["candidate_created_at"], "2026-10-14T11:00:00.000000Z",
        other, hostile_packet, policy)
    with pytest.raises(fitted.FittedMarketMemoryEvidenceError, match="exact_original_complete"):
        adapter.build_market_memory_evidence_attachment(request)
    assert store_state(world) == before
