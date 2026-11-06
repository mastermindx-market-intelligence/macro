"""Actual Factory consumes immutable old trial + admitted real retained owners."""
from dataclasses import replace
from hashlib import sha256
import json

import pytest

from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.research_factory import adapter_market_memory as old
from engine.research_factory import adapter_market_memory_evidence as evidence
from engine.research_factory import schema
from scripts import research_factory_run as runner
from tests.test_market_memory_retained_consumer import original
from tests.test_research_factory_market_memory import _bytes

REGISTERED = "2026-08-24T12:00:00.000000Z"
ATTACHED = "2026-08-25T12:00:00.000000Z"


def register(root, binding):
    binding = {k: v for k, v in binding.items() if k != "binding_id"}
    binding["binding_id"] = "mmrfbinding_" + sha256(cohort.canonical(binding)).hexdigest()
    body = cohort.canonical({"schema": "market_memory.factory_contextual_bindings.v1", "bindings": [binding]})
    (root / use.FACTORY_BINDINGS).write_bytes(body)
    p = root / use.REGISTRATION
    value = json.loads(p.read_text())
    value["service_consumers"] = {use.FACTORY_CONSUMER: {"enabled": True,
        "purpose": "contextual_cited_evidence", "binding_registry": use.FACTORY_BINDINGS,
        "binding_registry_sha256": sha256(body).hexdigest()}}
    p.write_bytes(cohort.canonical(value))
    return binding


@pytest.fixture
def admitted(original, monkeypatch):
    root, reader, pin, spec, captures = original
    body = _bytes()
    trial = json.loads(body)
    rel = "research/market_memory/trials/" + sha256(body).hexdigest() + ".json"
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    query = captures[3]
    binding = register(root, {"schema": "market_memory.factory_contextual_binding.v1",
        "origin": "current_owner_registered_contextual_attachment", "registered_at": REGISTERED,
        "trial_registration_id": trial["trial_registration_id"],
        "trial_registration_sha256": sha256(body).hexdigest(), "trial_record": rel,
        "store_id": pin.store_id, "context_id": query.packet["context_id"],
        "capture_id": query.capture_receipt["capture_id"], **spec,
        "consumer": use.FACTORY_CONSUMER, "mode": "historical_hypothetical"})
    monkeypatch.setattr(use, "_enforce_current_site_user", lambda uid: pytest.fail("Factory impersonated website user"))
    request = evidence.load_registered_factory_evidence(root, binding_id=binding["binding_id"], attached_at=ATTACHED)
    return root, binding, request, captures


def files(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("dry_run,count", [(True, False), (True, True), (False, False), (False, True)])
def test_actual_runner_consumes_nonempty_evidence_without_lifecycle(admitted, monkeypatch, dry_run, count):
    root, binding, request, _ = admitted
    before = files(root)
    monkeypatch.setattr(runner, "_perform_transition", lambda *a, **k: pytest.fail("MM attempted transition"))
    monkeypatch.setattr(runner, "_route_candidate", lambda *a, **k: pytest.fail("MM entered registered routing"))
    summary = runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=dry_run,
                         count=count, market_memory_inputs=(request,))
    value = summary["contextual_evidence"][0]
    assert schema.validate_market_memory_evidence_attachment(value) == []
    assert value["candidate"] == old.build_market_memory_candidate(
        exact_trial_registration_bytes=request.exact_trial_registration_bytes, created_at=REGISTERED)
    assert value["contextual_retrieval_join"]["denominator"]["returned"] == 2
    assert len(value["real_evidence_join"]["source_cards"]) == 3
    assert value["trial_binding"]["trial_original_query_provenance"] == "not_established"
    assert value["trial_binding"]["binding_id"] == binding["binding_id"]
    assert summary["transitions_attempted"] == summary["transitions_ok"] == 0
    assert summary["n_registered"] == summary["n_candidates"] == 0
    assert summary["routes"][0]["action"] == "no_action"
    assert files(root) == before
    assert not any(v for v in value["lifecycle"].values() if type(v) is bool)


def test_current_service_missing_denies_before_private_owner_read(original, monkeypatch):
    root, *_ = original
    p = root / use.REGISTRATION
    value = json.loads(p.read_text()); value.pop("service_consumers", None); p.write_text(json.dumps(value))
    monkeypatch.setattr(evidence.trusted, "TrustedFileAsKnownAtReader", lambda *a: pytest.fail("private owner read"))
    with pytest.raises(use.RetainedUseError):
        evidence.load_registered_factory_evidence(root, binding_id="mmrfbinding_" + "0" * 64, attached_at=ATTACHED)


def test_wrong_exact_original_trial_or_query_cannot_join(admitted):
    root, binding, request, _ = admitted
    with pytest.raises(evidence.MarketMemoryEvidenceError, match="trial_binding"):
        evidence.build_market_memory_evidence_attachment(replace(request, exact_trial_registration_bytes=b"{}"))
    binding = register(root, {**binding, "context_id": "mmctx_" + "0" * 64})
    with pytest.raises(evidence.MarketMemoryEvidenceError, match="join_required"):
        evidence.load_registered_factory_evidence(root, binding_id=binding["binding_id"], attached_at=ATTACHED)


def test_binding_revocation_during_existing_runner_work_refuses_final_disclosure(admitted, monkeypatch):
    root, binding, request, _ = admitted
    def revoke(_):
        p = root / use.REGISTRATION
        d = json.loads(p.read_text()); d["service_consumers"][use.FACTORY_CONSUMER]["enabled"] = False
        p.write_text(json.dumps(d)); return []
    monkeypatch.setattr(runner, "load_candidates", revoke)
    with pytest.raises(use.RetainedUseError):
        runner.run(rf_dir=root / "rf", data_dir=root, market_memory_inputs=(request,))


def test_unreturned_future_source_revocation_invalidates_cached_attachment(admitted):
    root, _, request, captures = admitted
    capability = evidence.build_market_memory_evidence_attachment(request)
    p = root / use.REGISTRATION
    value = json.loads(p.read_text())
    value["revoked_source_receipt_ids"] = captures[-1].capture_receipt["source_receipt_ids"]
    p.write_text(json.dumps(value))
    with pytest.raises(use.RetainedUseError):
        evidence.disclose_market_memory_evidence_attachment(capability)


def test_recursive_owned_markers_cannot_be_relabelled_into_generic_authority(admitted):
    _, _, request, _ = admitted
    value = evidence.disclose_market_memory_evidence_attachment(evidence.build_market_memory_evidence_attachment(request))
    for marker in [value["schema"], value["attachment_id"], value["trial_binding"]["binding_id"],
                   {"real_evidence_join": {}}]:
        assert schema.has_market_memory_owned_marker({"renamed": [{"inside": marker}]})
    hostile = dict(value)
    hostile["lifecycle"] = {**value["lifecycle"], "training_eligible": True}
    assert schema.validate_market_memory_evidence_attachment(hostile)
    with pytest.raises(evidence.MarketMemoryEvidenceError):
        evidence.MarketMemoryEvidenceAttachmentCapability(b"{}", request)
    with pytest.raises(evidence.MarketMemoryEvidenceError):
        evidence.disclose_market_memory_evidence_attachment(value)


def test_bounded_runner_inputs_rejected_before_candidate_counts(admitted, monkeypatch):
    root, _, request, _ = admitted
    monkeypatch.setattr(runner, "load_candidates", lambda *_: pytest.fail("unbounded input reached owner"))
    with pytest.raises(ValueError):
        runner.run(rf_dir=root, data_dir=root, market_memory_inputs=(request, request))


def test_existing_cli_consumes_registered_evidence(admitted, monkeypatch, capsys):
    root, binding, _, _ = admitted
    monkeypatch.setattr(runner, "ROOT", root)
    assert runner.main(["--market-memory-binding", binding["binding_id"], "--data-dir", str(root / "none")]) == 0
    output = capsys.readouterr().out
    assert "mmrfevidence_" in output and '"transitions_attempted": 0' in output
    assert "retained_original_house_output" in output


def test_authentic_caps_cannot_be_rebound_to_a_different_installed_query_id(admitted):
    root, binding, request, _ = admitted
    binding = register(root, {**binding, "query_id": "mmquery_" + "f" * 64})
    policy = use.RetainedFactoryUsePolicy(root, binding_id=binding["binding_id"])
    with pytest.raises(evidence.MarketMemoryEvidenceError, match="binding_owner_mismatch"):
        evidence.build_market_memory_evidence_attachment(replace(request, policy=policy))


def test_valid_alternate_method_is_denied_before_owner_reads(admitted, monkeypatch):
    root, binding, _, _ = admitted
    alternate = evidence.retrieval.RetainedContextMethodSpec(0, 0, binding["mode"]).disclosure()
    binding = register(root, {**binding, "method_spec_id": alternate["method_spec_id"]})
    monkeypatch.setattr(evidence.trusted, "TrustedFileAsKnownAtReader", lambda *a: pytest.fail("private owner read"))
    with pytest.raises(use.RetainedUseError):
        evidence.load_registered_factory_evidence(root, binding_id=binding["binding_id"], attached_at=ATTACHED)


def test_installed_current_proposal_and_binding_are_exact_readonly_records():
    from pathlib import Path
    from engine.neuralweb import market_memory_forward as forward
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / use.FACTORY_BINDINGS).read_bytes())
    assert len(registry["bindings"]) == 1
    binding, _digest = use._factory_binding(root, registry["bindings"][0]["binding_id"])
    body = (root / binding["trial_record"]).read_bytes()
    trial = forward.load_trial_registration_json(body)
    assert trial["trial_registration_id"] == binding["trial_registration_id"]
    assert sha256(body).hexdigest() == binding["trial_registration_sha256"]
    protocol_body = (root / "research/market_memory/protocols" / (trial["implementation"]["config_sha256"] + ".json")).read_bytes()
    protocol = json.loads(protocol_body)
    assert sha256(protocol_body).hexdigest() == trial["implementation"]["config_sha256"]
    for relative, digest in protocol["code_manifest"].items():
        assert sha256((root / relative).read_bytes()).hexdigest() == digest
    assert cohort.utc_instant(binding["query_cutoff"]) <= cohort.utc_instant(trial["registered_at"]) <= cohort.utc_instant(binding["registered_at"])
    candidate = old.build_market_memory_candidate(exact_trial_registration_bytes=body, created_at=binding["registered_at"])
    assert candidate["status"] == "proposed" and candidate["trial_accounting"]["mode"] == "read_only"
    assert trial["emission_enabled"] is False
    assert protocol["purpose"] == "current_contextual_cited_evidence_attachment"
