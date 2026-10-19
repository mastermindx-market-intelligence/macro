"""Synthetic native-owner integration; no actual E0 study or reviewer admission."""
import copy
from hashlib import sha256
import json

import pytest

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_trusted as trusted
from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory import market_memory_e0_baselines as baselines
from engine.research_factory import market_memory_e0_condition_evidence as sources
from engine.research_factory import market_memory_e0_task_evidence as tasks
from tests.market_memory_e0_fixtures import Policy, capture, owner, load, CUTOFF

TASK_CUTOFF = CUTOFF.replace("Z", ".000000Z")


@pytest.fixture
def request_data(tmp_path, monkeypatch):
    a = capture(tmp_path, monkeypatch, session="2026-08-10", growth=0.2)
    b = capture(tmp_path, monkeypatch, session="2026-08-11", growth=0.8)
    q = capture(tmp_path, monkeypatch, session="2026-08-12", growth=0.2)
    reader, pin = owner(tmp_path)
    feature = features.read_episode_feature_capability(reader, pin,
        query_id=q.capture_receipt["query_id"], subject_id=q.packet["subject"]["subject_id"],
        query_cutoff=TASK_CUTOFF, policy=Policy())
    cap = baselines.build_condition_selections(load(reader, pin, q, cutoff=TASK_CUTOFF), feature, policy=Policy(), k=1,
        method=retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical"))
    selected = baselines.disclose_condition_selections(cap, policy=Policy())
    refs = [{key: row.capture_receipt[key] for key in tasks._IDENTITY} for row in (q, a, b)]
    membership = {"owner": {key: selected["query_owner"][key]
                   for key in ("profile", "store_id", "generation_id", "generation_sha256")},
        "query_candidates": [{**ref, "subject": q.packet["subject"],
            "first_available_for_contextual_analysis": TASK_CUTOFF} for ref in refs]}
    frozen = cohort.canonical(membership)
    # Synthetic source corpus only. Production accepts the single unmodified
    # frozen membership pin; this seam supplies no actual source authentication.
    monkeypatch.setitem(control._FROZEN_DOMAIN_DIGESTS, "membership", sha256(frozen).hexdigest())
    task = {**refs[0], "task_id": "fixture-task", **q.packet["subject"],
        "analysis_cutoff": TASK_CUTOFF, "mode": "historical_hypothetical", "k": 1,
        "question": "Compare the retained house growth outputs and explain their limits.",
        "required_facet_ids": ["growth", "evidence-limits"], "original_evidence": refs}
    # Trusted subject has additional display fields; the task grammar is exact.
    task = {key: value for key, value in task.items()
            if key in control._task_validator().schema["properties"]["tasks"]["items"]["properties"]}
    task["question_sha256"] = sha256(task["question"].encode()).hexdigest()
    manifest = {key: item["const"] for key, item in control._task_validator().schema["properties"].items()
                if "const" in item}
    manifest.update(object_id="fixture-manifest", tasks=[task])
    return {"selection": cap, "reader": reader, "generation": pin,
        "task_manifest": cohort.canonical(manifest), "frozen_membership": frozen,
        "task_id": "fixture-task", "policy": Policy(),
        "expected_method": retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical")}


def test_native_union_read_once_and_identical_task_across_method_redacted_views(request_data, monkeypatch):
    calls = []
    original = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def record(self, generation, *, query_ids):
        calls.append(query_ids)
        return original(self, generation, query_ids=query_ids)
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", record)
    cap = tasks.build_task_condition_evidence(**request_data)
    assert len(calls) == 1 and len(calls[0]) == len(set(calls[0])) == 3
    views = [tasks.disclose_task_condition_view(cap, condition=c, policy=Policy()) for c in sources.CONDITIONS]
    assert views[0]["task"] == views[1]["task"] == views[2]["task"]
    assert [len(v["source_cards"]) for v in views] == [1, 2, 2]
    assert "original_evidence" not in views[0]["task"]
    for view in views:
        assert not view["actual_blinding_established"]
        assert not ({"condition", "method_spec", "condition_selection_sha256", "accounting"} & view.keys())
    audit = tasks.disclose_task_condition_audit(cap, policy=Policy())
    assert audit["binding"]["metadata_consistent"]
    assert not audit["binding"]["actual_task_registration_authenticated"]
    assert not audit["binding"]["study_admitted"]
    assert audit["binding"]["task_manifest_ref"]["sha256"] == sha256(request_data["task_manifest"]).hexdigest()
    views[0]["task"]["question"] = "mutated"
    assert tasks.disclose_task_condition_view(cap, condition="no_memory", policy=Policy())["task"] != views[0]["task"]


@pytest.mark.parametrize("change", ["cutoff", "mode", "k", "query", "subject", "instrument", "evidence", "question", "extra"])
def test_inconsistent_task_refuses_before_source_packet_reads(request_data, monkeypatch, change):
    manifest = json.loads(request_data["task_manifest"])
    task = manifest["tasks"][0]
    if change == "cutoff": task["analysis_cutoff"] = "2026-08-21T12:00:00.000000Z"
    if change == "mode": task["mode"] = "current_contextual_support"
    if change == "k": task["k"] = 2
    if change == "query": task["context_id"] = "mmctx_" + "f" * 64
    if change == "subject": task["subject_id"] = "mmsecurity_" + "f" * 64
    if change == "instrument": task["instrument_id"] = "mmsecurity_" + "f" * 64
    if change == "evidence": task["original_evidence"] = task["original_evidence"][:1]
    if change == "question": task["question"] += " changed"
    if change == "extra": task["later_outcome"] = 0.9
    monkeypatch.setattr(sources, "build_condition_evidence", lambda *a, **k: pytest.fail("invalid task reached source reader"))
    with pytest.raises((tasks.E0TaskEvidenceError, control.E0ControlError)):
        tasks.build_task_condition_evidence(**{**request_data, "task_manifest": cohort.canonical(manifest)})


@pytest.mark.parametrize("change", ["membership", "manifest_format", "absent_task", "boolean_task", "owner_generation"])
def test_exact_bytes_and_source_owner_before_reads(request_data, monkeypatch, change):
    request = dict(request_data)
    if change == "membership": request["frozen_membership"] += b"\n"
    if change == "manifest_format": request["task_manifest"] += b"\n"
    if change == "absent_task": request["task_id"] = "not-present"
    if change == "boolean_task": request["task_id"] = True
    if change == "owner_generation":
        membership = json.loads(request["frozen_membership"])
        membership["owner"]["generation_sha256"] = "f" * 64
        request["frozen_membership"] = cohort.canonical(membership)
        monkeypatch.setitem(control._FROZEN_DOMAIN_DIGESTS, "membership", sha256(request["frozen_membership"]).hexdigest())
    monkeypatch.setattr(sources, "build_condition_evidence", lambda *a, **k: pytest.fail("invalid binding reached source reader"))
    with pytest.raises((tasks.E0TaskEvidenceError, control.E0ControlError)):
        tasks.build_task_condition_evidence(**request)


def test_cached_task_disclosure_rechecks_original_source_rights(request_data):
    cap = tasks.build_task_condition_evidence(**request_data)
    denied = Policy({"disclose_real_synthesis_source"})
    with pytest.raises(cohort.RetainedContextAccessError):
        tasks.disclose_task_condition_view(cap, condition="no_memory", policy=denied)
    with pytest.raises(tasks.E0TaskEvidenceError):
        tasks.disclose_task_condition_audit(copy.deepcopy(request_data["task_manifest"]), policy=Policy())
    with pytest.raises(tasks.E0TaskEvidenceError):
        tasks.E0TaskConditionEvidence({}, cap._sources)


def test_last_moment_whole_population_revocation(request_data, monkeypatch):
    class Revoking(Policy):
        revoked = False
        def check(self, action, resource):
            if self.revoked and action == "disclose_retained_macro_capture":
                raise PermissionError("revoked during source read")
            return super().check(action, resource)
    policy = Revoking()
    original = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def revoke(*args, **kwargs):
        result = original(*args, **kwargs)
        policy.revoked = True
        return result
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", revoke)
    with pytest.raises(cohort.RetainedContextAccessError):
        tasks.build_task_condition_evidence(**{**request_data, "policy": policy})


@pytest.mark.parametrize("expected", [None, {},
    retrieval.RetainedContextMethodSpec(5, 0, "historical_hypothetical"),
    retrieval.RetainedContextMethodSpec(0, 5, "historical_hypothetical"),
    retrieval.RetainedContextMethodSpec(0, 0, "current_contextual_support")])
def test_exact_method_expectation_before_source_packet_reads(request_data, monkeypatch, expected):
    monkeypatch.setattr(sources, "build_condition_evidence", lambda *a, **k: pytest.fail("wrong method reached source reader"))
    with pytest.raises(tasks.E0TaskEvidenceError, match="exact_expected"):
        tasks.build_task_condition_evidence(**{**request_data, "expected_method": expected})


def test_aggregate_native_read_budget_refuses_without_packet(request_data, monkeypatch):
    monkeypatch.setattr(sources.evidence, "MAX_OWNER_PAYLOAD_BYTES", 1)
    with pytest.raises(sources.E0ConditionEvidenceError, match="aggregate_owner_read_byte_bound"):
        tasks.build_task_condition_evidence(**request_data)


def test_combined_condition_output_budget_refuses_without_packet(request_data, monkeypatch):
    monkeypatch.setattr(sources, "MAX_PACKET_BYTES", 128)
    with pytest.raises(sources.E0ConditionEvidenceError, match="condition_evidence_byte_bound"):
        tasks.build_task_condition_evidence(**request_data)
