"""Executable E0 condition selections over the same sealed eligible population.

No study, synthesis, annotation or outcome access occurs here. No-memory retains
the exact query and selects no historical evidence. Recency orders the SAME
eligible representatives by source session descending, then context ID. Fixed
L1 keeps the original selection unchanged. Current rights on the entire pool
are checked by the incumbent retrieval owner, including on later disclosure.

This joint preparation executes the fixed method to establish its eligibility
accounting. Its elapsed time is NOT an isolated recency/no-memory latency or
cost measurement. The eventual registered study must account for shared work.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort

_TOKEN = object()
_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
_MAX_BYTES = 2 * 1024 * 1024
# Existing E0 task grammar and descriptive accounting share this bound. The
# general retrieval owner's larger product limit is not this study's budget.
MAX_K = 8


class E0BaselineError(ValueError):
    """Condition selection or disclosure refused."""


@dataclass(frozen=True, slots=True, init=False)
class E0ConditionSelections:
    _body: bytes
    _digest: str
    _retrieval: retrieval.EpisodeRetrievalCapability
    _seal: object

    def __init__(self, body, original, *, _key=None):
        if _key is not _TOKEN:
            raise E0BaselineError("sealed_condition_selections_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_retrieval", original)
        object.__setattr__(self, "_seal", _TOKEN)


def build_condition_selections(population, query, *, policy: object, k: int,
                               method: retrieval.RetainedContextMethodSpec) -> E0ConditionSelections:
    """Prepare the three frozen conditions; no caller-supplied ranks or rows."""
    if type(k) is not int or not 1 <= k <= MAX_K:
        raise E0BaselineError("e0_task_k_bound_required")
    original = retrieval.retrieve_retained_contexts(population, query, policy=policy, k=k, method=method)
    fixed = retrieval.disclose_episode_retrieval(original, policy=policy)
    source = cohort.disclose_retained_context_cohort(population, policy=policy)
    rows = {row["context_id"]: row for row in source["rows"]}
    eligible = {row["context_id"] for row in fixed["accounting"] if row["reason"] == "numerically_eligible"}
    recent = sorted(eligible, key=lambda key: (-date.fromisoformat(rows[key]["source_session"]).toordinal(), key))[:k]
    fixed_ids = [row["candidate"]["context_id"] for row in fixed["selected"]]
    if (fixed["membership_sha256"] != source["membership_sha256"]
            or len(eligible) != fixed["denominator"]["eligible_representatives"]
            or not set(fixed_ids) <= eligible):
        raise E0BaselineError("original_selection_closure_mismatch")

    def selection(condition, ids):
        refs = [{key: rows[identity][key] for key in
                 ("context_id", "capture_id", "query_id", "packet_sha256", "source_session")}
                for identity in ids]
        return {"condition": condition, "selected": refs, "returned": len(refs),
                "status": ("WITHHELD_BY_CONDITION" if condition == "no_memory"
                           else "MATCHES" if refs else "ABSTAINED")}

    value = {"schema": "research_factory.market_memory_e0_condition_selections.v1",
             "authority": "display_only",
             "query": {key: value for key, value in fixed["query"].items() if key != "projection_id"},
             "query_owner": fixed["query_owner"], "membership_sha256": fixed["membership_sha256"],
             "fixed_selection_sha256": fixed["selection_sha256"],
             "method_spec": fixed["method_spec"], "requested_k": k,
             "source_sha256": _SOURCE_SHA256,
             "recency_order": "source_session_descending_then_context_id_ascending",
             "accounting": fixed["accounting"],
             "denominator": {key: value for key, value in fixed["denominator"].items() if key != "returned"},
             "conditions": [selection("no_memory", []), selection("recency", recent),
                            selection("fixed_l1", fixed_ids)],
             "operational_admission": False, "evaluation_performed": False,
             "label_interval_coverage": "not_established",
             "independent_episode_count": "not_established",
             "cost_scope": "joint_qualification_and_fixed_method_not_isolated_condition_cost"}
    digest = sha256(cohort.canonical(value)).hexdigest()
    body = cohort.canonical({**value, "condition_selection_sha256": digest})
    if len(body) > _MAX_BYTES:
        raise E0BaselineError("condition_selection_byte_limit")
    capability = E0ConditionSelections(body, original, _key=_TOKEN)
    disclose_condition_selections(capability, policy=policy)
    return capability


def disclose_condition_selections(capability: E0ConditionSelections, *, policy: object) -> dict:
    if (type(capability) is not E0ConditionSelections or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > _MAX_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise E0BaselineError("sealed_condition_selections_required")
    # The original owner's check includes unreturned compared candidates and
    # the complete cohort. A cached condition cannot narrow that authorization.
    retrieval.disclose_episode_retrieval(capability._retrieval, policy=policy)
    return json.loads(capability._body)
