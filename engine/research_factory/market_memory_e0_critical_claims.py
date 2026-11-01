"""Count caller-declared critical/unsupported intersections without study verdicts.

Inputs retain the exact descriptive accounting contract and validator semantics.
Claim identity is scoped to its task/condition; the same spelling in another
cell is a different observation. Contradicted, unresolved and attributed claims
remain distinct native verdicts. No unsupported rating is inferred from them.

This additive utility does not change descriptive accounting, authenticate
ratings or severity, select a threshold, estimate uncertainty, or admit a study.
It performs no I/O and returns detached counts for every registered task/cell.
"""
from __future__ import annotations

from . import market_memory_evidence_accounting as accounting

OUTPUT_SCHEMA = "market_memory.e0_critical_claim_counts.v1"
_COUNT_KEYS = ("all_claim_count", "material_claim_count", "critical_claim_count",
               "critical_unsupported_claim_count")


def _native_cells(value):
    """Reuse the incumbent's strict native validators, with no second schema."""
    root = accounting._require_dict(value, "input", ("schema", "conditions", "tasks", "observations"))
    if type(root["schema"]) is not str or root["schema"] != accounting.INPUT_SCHEMA:
        raise accounting.EvidenceAccountingError("input schema must be " + accounting.INPUT_SCHEMA)
    conditions = accounting._require_list(root["conditions"], "conditions", len(accounting.CONDITIONS))
    if any(type(item) is not str for item in conditions) or tuple(conditions) != accounting.CONDITIONS:
        raise accounting.EvidenceAccountingError("conditions must be exactly the three fixed conditions in fixed order")
    tasks = {}
    for index, raw in enumerate(accounting._require_list(root["tasks"], "tasks", accounting.MAX_TASKS)):
        identity, task = accounting._validate_task(raw, index)
        if identity in tasks:
            raise accounting.EvidenceAccountingError("tasks contains a duplicate task_id")
        tasks[identity] = task
    cells = {}
    for index, raw in enumerate(accounting._require_list(
            root["observations"], "observations", accounting.MAX_OBSERVATIONS)):
        accounting._validate_observation(raw, index, tasks, cells)
    return tasks, cells


def _cell(raw):
    claims = [] if raw is None else raw["claims"]
    ids = {verdict: sorted(claim["claim_id"] for claim in claims
                           if claim["critical"] and claim["verdict"] == verdict)
           for verdict in accounting.VERDICTS}
    return {"record_present": raw is not None,
            "state": "missing" if raw is None else raw["state"],
            "counts": {"all_claim_count": len(claims),
                       "material_claim_count": sum(claim["material"] for claim in claims),
                       "critical_claim_count": sum(len(rows) for rows in ids.values()),
                       "critical_unsupported_claim_count": len(ids["unsupported"])},
            "critical_claim_ids_by_verdict": ids}


def score_critical_claims(value):
    """Return deterministic joint counts, never a scientific acceptance verdict.

    Zero counts on an absent or non-answered cell are not observed evidence of
    safety. Explicit state and record presence remain alongside the unchanged
    task denominator, including pending, censored and unavailable observations.
    """
    tasks, cells = _native_cells(value)
    per_task = [{**tasks[identity], "conditions": {
        condition: _cell(cells.get((identity, condition)))
        for condition in accounting.CONDITIONS}} for identity in sorted(tasks)]
    per_condition = {}
    for condition in accounting.CONDITIONS:
        rows = [task["conditions"][condition] for task in per_task]
        recorded = sum(row["record_present"] for row in rows)
        per_condition[condition] = {
            "registered_task_count": len(tasks), "recorded_task_count": recorded,
            "unrecorded_task_count": len(tasks) - recorded,
            "state_counts": {state: sum(row["state"] == state for row in rows)
                             for state in accounting.STATES},
            "counts": {key: sum(row["counts"][key] for row in rows) for key in _COUNT_KEYS},
            "critical_verdict_counts": {verdict: sum(len(row["critical_claim_ids_by_verdict"][verdict])
                                                     for row in rows)
                                        for verdict in accounting.VERDICTS}}
    return {"schema": OUTPUT_SCHEMA, "authority": "display_only",
            "input_schema": accounting.INPUT_SCHEMA, "conditions": list(accounting.CONDITIONS),
            "total_registered_tasks": len(tasks), "per_task": per_task, "per_condition": per_condition,
            "ratings_authenticated": False, "inferential_estimator_qualified": False,
            "acceptance_verdict_emitted": False, "operational_admission": False}
