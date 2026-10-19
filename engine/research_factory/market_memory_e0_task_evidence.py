"""Join an exact declared E0 task to its sealed three-condition source packets.

The original frozen membership bytes and native source identities are checked
before source-packet reads. A matching task manifest is still supplied metadata:
installed study selection, reservation and reviewer exposure remain the trusted
executor's responsibility. This module never registers or starts a study.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory import market_memory_e0_baselines as baselines
from engine.research_factory import market_memory_e0_condition_evidence as sources

_TOKEN = object()
_IDENTITY = ("query_id", "context_id", "capture_id", "packet_sha256")


class E0TaskEvidenceError(ValueError):
    """Declared task bytes or their exact source join were refused."""


def _task_binding(task_manifest, frozen_membership, task_id, selected):
    for body in (task_manifest, frozen_membership):
        if type(body) is not bytes or not 0 < len(body) <= control.MAX_DOMAIN_OBJECT_BYTES:
            raise E0TaskEvidenceError("bounded_exact_task_and_membership_bytes_required")
    if sha256(frozen_membership).hexdigest() != control._FROZEN_DOMAIN_DIGESTS["membership"]:
        raise E0TaskEvidenceError("original_frozen_membership_bytes_required")
    if type(task_id) is not str or control._ID.fullmatch(task_id) is None:
        raise E0TaskEvidenceError("bounded_task_identity_required")
    membership = control._domain_json(frozen_membership)
    manifest = control._domain_json(task_manifest)
    control._validate_task_bindings(manifest, task_manifest, membership)
    tasks = [task for task in manifest["tasks"] if task["task_id"] == task_id]
    if len(tasks) != 1:
        raise E0TaskEvidenceError("one_exact_declared_task_required")
    task = tasks[0]
    owner = selected["query_owner"]
    if any(owner[key] != value for key, value in membership["owner"].items()):
        raise E0TaskEvidenceError("exact_frozen_source_generation_required")
    if (any(task[key] != selected["query"][key] for key in _IDENTITY if key != "query_id")
            or task["query_id"] != owner["query_id"] or task["subject_id"] != owner["subject_id"]
            or task["analysis_cutoff"] != owner["query_cutoff"]
            or task["mode"] != selected["method_spec"]["mode"]
            or task["k"] != selected["requested_k"]):
        raise E0TaskEvidenceError("exact_task_query_cutoff_mode_budget_required")
    permitted = {tuple(ref[key] for key in _IDENTITY) for ref in task["original_evidence"]}
    selected_refs = [{**selected["query"], "query_id": owner["query_id"]}]
    selected_refs += [ref for condition in selected["conditions"] for ref in condition["selected"]]
    if any(tuple(ref[key] for key in _IDENTITY) not in permitted for ref in selected_refs):
        raise E0TaskEvidenceError("condition_source_outside_declared_task_evidence")
    return {"task": task, "task_manifest_ref": {"schema": manifest["schema"],
        "object_id": manifest["object_id"], "sha256": sha256(task_manifest).hexdigest(),
        "bytes": len(task_manifest)}, "frozen_membership_sha256": sha256(frozen_membership).hexdigest(),
        "frozen_ordered_membership_sha256": manifest["membership_sha256"],
        "native_cohort_sha256": selected["membership_sha256"],
        "condition_selection_sha256": selected["condition_selection_sha256"],
        "method_spec_id": selected["method_spec"]["method_spec_id"],
        "metadata_consistent": True, "actual_task_registration_authenticated": False,
        "study_admitted": False}


@dataclass(frozen=True, slots=True, init=False)
class E0TaskConditionEvidence:
    _binding: bytes
    _digest: str
    _sources: sources.E0ConditionEvidence
    _seal: object

    def __init__(self, binding, evidence, *, _key=None):
        if _key is not _TOKEN:
            raise E0TaskEvidenceError("sealed_task_condition_evidence_required")
        body = cohort.canonical(binding)
        object.__setattr__(self, "_binding", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_sources", evidence)
        object.__setattr__(self, "_seal", _TOKEN)


def build_task_condition_evidence(selection, reader, generation, *, task_manifest: bytes,
                                  frozen_membership: bytes, task_id: str,
                                  expected_method: retrieval.RetainedContextMethodSpec, policy):
    # The installed executor must derive this exact typed expectation from its
    # selected registered method reference. A caller-supplied expectation is
    # consistency checking only and never authenticates that registration.
    if type(expected_method) is not retrieval.RetainedContextMethodSpec:
        raise E0TaskEvidenceError("exact_expected_native_method_required")
    selected = baselines.disclose_condition_selections(selection, policy=policy)
    if selected["method_spec"] != expected_method.disclosure():
        raise E0TaskEvidenceError("exact_expected_method_identity_required")
    binding = _task_binding(task_manifest, frozen_membership, task_id, selected)
    evidence = sources.build_condition_evidence(selection, reader, generation, policy=policy)
    result = E0TaskConditionEvidence(binding, evidence, _key=_TOKEN)
    disclose_task_condition_audit(result, policy=policy)
    return result


def disclose_task_condition_audit(capability, *, policy):
    if (type(capability) is not E0TaskConditionEvidence or capability._seal is not _TOKEN
            or type(capability._binding) is not bytes
            or not 0 < len(capability._binding) <= control.MAX_DOMAIN_OBJECT_BYTES
            or sha256(capability._binding).hexdigest() != capability._digest):
        raise E0TaskEvidenceError("sealed_task_condition_evidence_required")
    evidence = sources.disclose_condition_evidence(capability._sources, policy=policy)
    binding = json.loads(capability._binding)
    if binding["condition_selection_sha256"] != evidence["condition_selection_sha256"]:
        raise E0TaskEvidenceError("task_condition_selection_changed")
    return {"binding": binding, "evidence": evidence}


def disclose_task_condition_view(capability, *, condition: str, policy):
    audit = disclose_task_condition_audit(capability, policy=policy)
    task = audit["binding"]["task"]
    view = sources.disclose_method_redacted_view(capability._sources, condition=condition, policy=policy)
    # The same question/facets/context accompany every condition. Do not disclose
    # the full permitted-evidence list: that would expose absent condition cards.
    return {**view, "task": {key: task[key] for key in ("task_id", "subject_id", "instrument_id",
        "analysis_cutoff", "mode", "question", "question_sha256", "required_facet_ids")}}
