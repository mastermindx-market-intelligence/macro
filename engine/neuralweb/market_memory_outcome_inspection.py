"""Public projection of an already-authorized, selection-bound L0 attachment.

This is presentation composition only. It grants no source purpose, selects no
observation, publishes nothing, and does not turn an observation into a return.
The installed owner must supply both original sealed capabilities and its policy.
"""
from __future__ import annotations

import json

from engine.neuralweb import market_memory_episode_outcomes as outcomes
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort


def project_outcome_inspection(selection, attachment, *, policy: object) -> dict:
    """Project exact published observations after checking original selection.

    No request dictionary, current-head lookup, preparation capability or caller
    supplied price can substitute for an authenticated attachment. Future and
    absent observations keep the native indistinguishable null shape.
    """
    original = retrieval.disclose_episode_retrieval(selection, policy=policy)
    attached = outcomes.disclose_contextual_outcomes(attachment, policy=policy)
    if (not 1 <= original["requested_k"] <= 8
            or attached["retrieval_id"] != original["retrieval_id"]
            or attached["selection_sha256"] != original["selection_sha256"]
            or attached["query_cutoff"] != original["query_owner"]["query_cutoff"]
            or attached["denominator"] != original["denominator"]
            or [row["selected"] for row in attached["rows"]] != original["selected"]):
        raise outcomes.EpisodeOutcomeError("exact_inspection_selection_required")
    if (attached["effective_n"] != "not_estimated"
            or any(attached[key] is not False for key in
                   ("economic_return", "corporate_action_adjusted", "RTH_close_authenticated"))):
        raise outcomes.EpisodeOutcomeError("registered_archived_mark_semantics_required")
    rows = []
    for rank, row in enumerate(attached["rows"], 1):
        if row["rank"] != rank:
            raise outcomes.EpisodeOutcomeError("exact_inspection_rank_required")
        comparison = row["selected"]
        candidate = comparison["candidate"]
        observation = None
        if "observation_id" in row:
            observation = {
                "id": row["observation_id"], "sha256": row["observation_sha256"],
                "revision_number": row["revision_number"],
                "previous_observation_id": row["previous_observation_id"],
                "clocks": dict(row["clocks"]),
            }
        rows.append({
            "rank": rank, "context_id": candidate["context_id"],
            "capture_id": candidate["capture_id"], "packet_sha256": candidate["packet_sha256"],
            "comparison_id": comparison["comparison_id"],
            "distance_q18": comparison["distance_q18"],
            "status": row["status"], "reason": row["reason"],
            "value_q18": row["value_q18"], "observation": observation,
        })
    value = {
        "schema": "market_memory.outcome_inspection.v1",
        "retrieval_id": original["retrieval_id"],
        "selection_sha256": original["selection_sha256"],
        "query_cutoff": attached["query_cutoff"],
        "outcome_cutoff": attached["outcome_cutoff"], "lens": attached["lens"],
        "definition_sha256": attached["definition_sha256"],
        "metric": "archived_close_ratio", "economic_return": False,
        "corporate_action_adjusted": False, "RTH_close_authenticated": False,
        "effective_n": "not_estimated", "rows": rows,
    }
    encoded = cohort.canonical(value)
    if len(encoded) > 256 * 1024:
        raise outcomes.EpisodeOutcomeError("outcome_inspection_byte_limit")
    # Source purposes, the complete comparison population and the original
    # observation pin must still be authorized at the disclosure boundary.
    outcomes.disclose_contextual_outcomes(attachment, policy=policy)
    retrieval.disclose_episode_retrieval(selection, policy=policy)
    return json.loads(encoded)
