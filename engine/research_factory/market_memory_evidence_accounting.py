"""Descriptive evidence accounting for Market Memory (A0/E1 preparation).

Scope of this module, stated plainly:

* This is a pure descriptive reducer over caller-supplied data. It is NOT a
  registered study, NOT independent annotation, NOT an inferential estimator,
  and NOT a usefulness or acceptance conclusion.
* It never emits PASS/ACCEPT/NO_GO, operational admission=true, confidence
  intervals, effective N, or predictor/trade authority.
* Caller-provided ratings, verdicts and provenance are taken as given and are
  NOT authenticated by this API in any way. Synthetic test fixtures stay
  synthetic; the API has no way to know the provenance of any input.
* No threshold or margin is selected here. Existing method/protocol pins are
  untouched. No materiality or entailment is derived from hash/span validity;
  every materiality, criticality and verdict flag is a caller-provided
  judgment.

Interface: ``summarize_evidence_accounting(value)`` -> a detached JSON-native
dict, or raises ``EvidenceAccountingError`` (a ``ValueError``) with a stable
message that never echoes raw input. No IO of any kind. Stdlib only.
"""

from fractions import Fraction

INPUT_SCHEMA = "market_memory.evidence_accounting_input.v1"
OUTPUT_SCHEMA = "market_memory.evidence_accounting_summary.v1"

CONDITIONS = ("no_memory", "recency", "fixed_l1")
STATES = ("answered", "abstained", "missing", "source_unavailable", "pending", "censored")
OBSERVED_STATES = ("answered", "abstained")
ASSESSMENTS = ("correct", "incorrect", "unresolved", "not_applicable")
VERDICTS = ("supported", "contradicted", "unsupported", "attributed_inference", "unresolved")
ANSWERABILITY = ("answerable", "unanswerable", "unknown")

LEDGER_CELLS = (
    "answerable_answered_correct",
    "answerable_answered_incorrect",
    "answerable_answered_unresolved",
    "answerable_abstained",
    "unanswerable_asserted",
    "unanswerable_abstained",
    "unknown_answerability_answered",
    "unknown_answerability_abstained",
    "missing",
    "source_unavailable",
    "pending",
    "censored",
)

# Resource bounds only -- NOT scientific sample minima.
MAX_TASKS = 10000
MAX_OBSERVATIONS = 30000
MAX_CLAIMS_PER_OBSERVATION = 64
MAX_RETRIEVED_PER_OBSERVATION = 8
MAX_FACETS = 64
MAX_ID_LENGTH = 128

CLARIFICATIONS = {
    "ratings_provenance": "CALLER_SUPPLIED_NOT_AUTHENTICATED_BY_THIS_API",
    "study_status": "NOT_A_REGISTERED_STUDY_NO_REAL_STUDY_ACCEPTANCE",
    "inference": "DESCRIPTIVE_ONLY_NO_CONFIDENCE_INTERVALS_NO_EFFECTIVE_N",
    "thresholds": "NO_THRESHOLD_OR_MARGIN_SELECTION_IS_PERFORMED",
    "synthetic_fixtures": "TEST_FIXTURES_ARE_SYNTHETIC_AND_PROVE_NOTHING_ABOUT_REAL_DATA",
    "identity": "CALLER_MUST_PROVIDE_CANONICAL_IDENTITIES_BEFORE_THIS_BOUNDARY",
}


class EvidenceAccountingError(ValueError):
    """Raised for malformed or incoherent input. Message is stable and input-free."""


# ---------------------------------------------------------------------------
# primitive validation helpers (exact types; bool is never accepted as int)
# ---------------------------------------------------------------------------


def _is_int(value):
    return type(value) is int


def _is_bool(value):
    return type(value) is bool


def _is_id(value):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH:
        return False
    first = value[0]
    if not (first.isascii() and first.isalnum()):
        return False
    for ch in value[1:]:
        if not (ch.isascii() and (ch.isalnum() or ch in "_.:-")):
            return False
    return True


def _require_dict(value, where, keys):
    if type(value) is not dict:
        raise EvidenceAccountingError(where + " must be a JSON object")
    if (len(value) != len(keys) or any(type(key) is not str for key in value)
            or set(value) != set(keys)):
        raise EvidenceAccountingError(where + " has missing or unexpected keys")
    return value


def _require_list(value, where, limit):
    if type(value) is not list:
        raise EvidenceAccountingError(where + " must be a JSON array")
    if len(value) > limit:
        raise EvidenceAccountingError(where + " exceeds the resource bound")
    return value


def _require_id(value, where):
    if not _is_id(value):
        raise EvidenceAccountingError(where + " must be a valid identifier")
    return value


def _require_enum(value, allowed, where):
    if type(value) is not str or value not in allowed:
        raise EvidenceAccountingError(where + " has an invalid enumerated value")
    return value


def _require_int(value, low, high, where):
    if not _is_int(value) or value < low or value > high:
        raise EvidenceAccountingError(where + " must be an integer in [%d, %d]" % (low, high))
    return value


def _require_bool(value, where):
    if not _is_bool(value):
        raise EvidenceAccountingError(where + " must be a boolean")
    return value


def _require_id_list(value, where, limit):
    _require_list(value, where, limit)
    seen = set()
    for item in value:
        _require_id(item, where + " element")
        if item in seen:
            raise EvidenceAccountingError(where + " contains duplicate identifiers")
        seen.add(item)
    return value


# ---------------------------------------------------------------------------
# ratio helpers
# ---------------------------------------------------------------------------


def _ratio(numerator, denominator):
    if denominator == 0:
        return {"numerator": numerator, "denominator": 0, "value": None, "status": "EMPTY_DENOMINATOR"}
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator,
        "status": "OK",
    }


def _frac_ratio(frac):
    return {
        "numerator": frac.numerator,
        "denominator": frac.denominator,
        "value": float(frac),
        "status": "OK",
    }


def _frac_ratio_or_empty(frac):
    if frac is None:
        return _ratio(0, 0)
    return _frac_ratio(frac)


def _not_observed_ratio(denominator):
    return {"numerator": None, "denominator": denominator, "value": None, "status": "NOT_OBSERVED"}


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------


def _validate_task(raw, index):
    where = "tasks[%d]" % index
    _require_dict(raw, where, ("task_id", "cluster_id", "answerability", "required_facet_ids", "k"))
    task_id = _require_id(raw["task_id"], where + ".task_id")
    cluster_id = raw["cluster_id"]
    if cluster_id is not None:
        _require_id(cluster_id, where + ".cluster_id")
    answerability = _require_enum(raw["answerability"], ANSWERABILITY, where + ".answerability")
    facets = _require_id_list(raw["required_facet_ids"], where + ".required_facet_ids", MAX_FACETS)
    k = _require_int(raw["k"], 1, 8, where + ".k")
    return task_id, {
        "task_id": task_id,
        "cluster_id": cluster_id,
        "answerability": answerability,
        "required_facet_ids": list(facets),
        "k": k,
    }


def _validate_claims(raw, where):
    claims = _require_list(raw["claims"], where + ".claims", MAX_CLAIMS_PER_OBSERVATION)
    parsed = []
    seen = set()
    for i, entry in enumerate(claims):
        cwhere = "%s.claims[%d]" % (where, i)
        _require_dict(entry, cwhere, ("claim_id", "material", "verdict", "critical"))
        claim_id = _require_id(entry["claim_id"], cwhere + ".claim_id")
        if claim_id in seen:
            raise EvidenceAccountingError(where + " has a duplicate claim_id")
        seen.add(claim_id)
        material = _require_bool(entry["material"], cwhere + ".material")
        critical = _require_bool(entry["critical"], cwhere + ".critical")
        verdict = _require_enum(entry["verdict"], VERDICTS, cwhere + ".verdict")
        if critical and not material:
            raise EvidenceAccountingError(where + " has a critical claim that is not material")
        parsed.append({"claim_id": claim_id, "material": material, "verdict": verdict, "critical": critical})
    return parsed


def _validate_retrieved(raw, where, k, facet_registry):
    retrieved = _require_list(raw["retrieved"], where + ".retrieved", MAX_RETRIEVED_PER_OBSERVATION)
    if len(retrieved) > k:
        raise EvidenceAccountingError(where + " retrieved exceeds the task k bound")
    parsed = []
    seen = set()
    for i, entry in enumerate(retrieved):
        rwhere = "%s.retrieved[%d]" % (where, i)
        _require_dict(entry, rwhere, ("item_id", "relevance", "facet_ids"))
        item_id = _require_id(entry["item_id"], rwhere + ".item_id")
        if item_id in seen:
            raise EvidenceAccountingError(where + " has a duplicate item_id")
        seen.add(item_id)
        relevance = _require_int(entry["relevance"], 0, 2, rwhere + ".relevance")
        facet_ids = _require_id_list(entry["facet_ids"], rwhere + ".facet_ids", MAX_FACETS)
        for fid in facet_ids:
            if fid not in facet_registry:
                raise EvidenceAccountingError(rwhere + " references an unknown facet id")
        parsed.append({"item_id": item_id, "relevance": relevance, "facet_ids": list(facet_ids)})
    return parsed


def _validate_observation(raw, index, tasks, cells):
    where = "observations[%d]" % index
    _require_dict(
        raw,
        where,
        ("task_id", "condition", "state", "answer_assessment", "claims", "retrieved"),
    )
    task_id = _require_id(raw["task_id"], where + ".task_id")
    if task_id not in tasks:
        raise EvidenceAccountingError(where + " references an unregistered task_id")
    condition = _require_enum(raw["condition"], CONDITIONS, where + ".condition")
    key = (task_id, condition)
    if key in cells:
        raise EvidenceAccountingError(where + " duplicates a task/condition observation")
    task = tasks[task_id]
    state = _require_enum(raw["state"], STATES, where + ".state")
    assessment = _require_enum(raw["answer_assessment"], ASSESSMENTS, where + ".answer_assessment")
    claims = _validate_claims(raw, where)
    retrieved = _validate_retrieved(raw, where, task["k"], set(task["required_facet_ids"]))

    answerability = task["answerability"]
    if state == "answered":
        if assessment not in ("correct", "incorrect", "unresolved"):
            raise EvidenceAccountingError(where + " answered state requires a graded assessment")
        if answerability == "unanswerable" and assessment == "correct":
            raise EvidenceAccountingError(where + " an unanswerable task cannot be assessed correct")
        if answerability == "unknown" and assessment != "unresolved":
            raise EvidenceAccountingError(where + " an unknown-answerability answered cell must be unresolved")
    else:
        if assessment != "not_applicable":
            raise EvidenceAccountingError(where + " non-answered state requires not_applicable")
        if claims:
            raise EvidenceAccountingError(where + " non-answered state must carry no claims")
        if retrieved and state != "abstained":
            raise EvidenceAccountingError(where + " only answered or abstained states may carry retrieved items")

    cells[key] = {
        "task_id": task_id,
        "condition": condition,
        "state": state,
        "answer_assessment": assessment,
        "record_present": True,
        "claims": claims,
        "retrieved": retrieved,
    }


# ---------------------------------------------------------------------------
# accounting
# ---------------------------------------------------------------------------


def _ledger_cell(answerability, state, assessment):
    if state == "answered":
        if answerability == "answerable":
            return {
                "correct": "answerable_answered_correct",
                "incorrect": "answerable_answered_incorrect",
                "unresolved": "answerable_answered_unresolved",
            }[assessment]
        if answerability == "unanswerable":
            return "unanswerable_asserted"
        return "unknown_answerability_answered"
    if state == "abstained":
        if answerability == "answerable":
            return "answerable_abstained"
        if answerability == "unanswerable":
            return "unanswerable_abstained"
        return "unknown_answerability_abstained"
    return state


def _claim_tally(claims):
    material = {v: 0 for v in VERDICTS}
    nonmaterial = {v: 0 for v in VERDICTS}
    material_total = 0
    nonmaterial_total = 0
    critical = 0
    for claim in claims:
        bucket = material if claim["material"] else nonmaterial
        bucket[claim["verdict"]] += 1
        if claim["material"]:
            material_total += 1
        else:
            nonmaterial_total += 1
        if claim["critical"]:
            critical += 1
    return {
        "material": {"total": material_total, "verdict_counts": material},
        "nonmaterial": {"total": nonmaterial_total, "verdict_counts": nonmaterial},
        "critical": critical,
    }


def _support_section(tally):
    mat = tally["material"]
    d = mat["total"]
    s = mat["verdict_counts"]["supported"]
    u = mat["verdict_counts"]["unresolved"] + mat["verdict_counts"]["attributed_inference"]
    if d == 0:
        share = _ratio(s, 0)
        precision = {"numerator": s, "denominator": 0, "value": None, "status": "EMPTY_DENOMINATOR"}
        lower = _ratio(0, 0)
        upper = dict(lower)
    else:
        share = _ratio(s, d)
        if u > 0:
            precision = {"numerator": s, "denominator": d, "value": None, "status": "UNRESOLVED_MATERIAL_CLAIMS"}
        else:
            precision = _ratio(s, d)
        lower = _ratio(s, d)
        upper = _ratio(s + u, d)
    return {
        "material_claims": {
            "total": d,
            "verdict_counts": dict(mat["verdict_counts"]),
            "supported": s,
            "unresolved": mat["verdict_counts"]["unresolved"],
            "attributed_inference": mat["verdict_counts"]["attributed_inference"],
            "contradicted": mat["verdict_counts"]["contradicted"],
            "unsupported": mat["verdict_counts"]["unsupported"],
        },
        "nonmaterial_claims": {
            "total": tally["nonmaterial"]["total"],
            "verdict_counts": dict(tally["nonmaterial"]["verdict_counts"]),
        },
        "critical_claim_count": tally["critical"],
        "supported_share": share,
        "support_precision": precision,
        "identification_bounds": {
            "lower": lower,
            "upper": upper,
            "interpretation": "DESCRIPTIVE_BOUNDS_NOT_CONFIDENCE_INTERVALS",
        },
    }


def _coverage_for_cell(task, cell):
    facets = task["required_facet_ids"]
    if cell is None or cell["state"] not in OBSERVED_STATES:
        not_observed = {"numerator": None, "denominator": None, "value": None, "status": "NOT_OBSERVED"}
        return _not_observed_ratio(len(facets)), not_observed, 0, 0, None
    retrieved = cell["retrieved"]
    relevant2 = [item for item in retrieved if item["relevance"] == 2]
    covered = set()
    for item in relevant2:
        covered.update(item["facet_ids"])
    if not facets:
        coverage = _ratio(0, 0)
    else:
        covered_registered = sum(1 for fid in facets if fid in covered)
        coverage = _ratio(covered_registered, len(facets))
    if len(retrieved) == 0:
        precision = {"numerator": 0, "denominator": 0, "value": None, "status": "EMPTY_DENOMINATOR"}
    else:
        precision = _ratio(len(relevant2), len(retrieved))
    omission = len(facets) - len(covered & set(facets)) if facets else None
    return coverage, precision, len(retrieved), len(relevant2), omission


def _retrieval_counts(cells_for_condition):
    item_count = 0
    relevance_counts = {0: 0, 1: 0, 2: 0}
    observed = 0
    for cell in cells_for_condition:
        if cell is None or cell["state"] not in OBSERVED_STATES:
            continue
        observed += 1
        for item in cell["retrieved"]:
            item_count += 1
            relevance_counts[item["relevance"]] += 1
    return {
        "observed_cell_count": observed,
        "retrieved_item_count": item_count,
        "relevance_counts": {"0": relevance_counts[0], "1": relevance_counts[1], "2": relevance_counts[2]},
    }


def _paired_contrast(tasks, per_task):
    total = len(per_task)
    included = []
    excluded = []
    for record in per_task:
        rec = record["conditions"]["fixed_l1"]["coverage"]
        recency = record["conditions"]["recency"]["coverage"]
        if rec["status"] == "OK" and recency["status"] == "OK":
            included.append(record)
        else:
            excluded.append(
                {
                    "task_id": record["task_id"],
                    "fixed_l1_status": rec["status"],
                    "recency_status": recency["status"],
                }
            )

    per_task_diffs = []
    diffs = []
    for record in included:
        den = record["conditions"]["fixed_l1"]["coverage"]["denominator"]
        f_num = record["conditions"]["fixed_l1"]["coverage"]["numerator"]
        r_num = record["conditions"]["recency"]["coverage"]["numerator"]
        diff = Fraction(f_num - r_num, den)
        diffs.append(diff)
        per_task_diffs.append(
            {
                "task_id": record["task_id"],
                "recency": {
                    "numerator": r_num,
                    "denominator": den,
                    "value": r_num / den,
                },
                "fixed_l1": {
                    "numerator": f_num,
                    "denominator": den,
                    "value": f_num / den,
                },
                "signed_difference": _frac_ratio(diff),
            }
        )

    mean_diff = None
    if diffs:
        mean_diff = sum(diffs, Fraction(0)) / len(diffs)

    cluster_mean = None
    if not diffs:
        cluster_mean = {
            "value": None,
            "status": "EMPTY_DENOMINATOR",
            "cluster_count": None,
            "per_cluster_means": [],
        }
    elif any(record["cluster_id"] is None for record in included):
        cluster_mean = {
            "value": None,
            "status": "UNKNOWN_CLUSTER_MEMBERSHIP",
            "cluster_count": None,
            "per_cluster_means": [],
        }
    else:
        by_cluster = {}
        for record, diff in zip(included, diffs):
            by_cluster.setdefault(record["cluster_id"], []).append(diff)
        cluster_means = []
        for cluster_id in sorted(by_cluster):
            members = by_cluster[cluster_id]
            cluster_means.append(
                {
                    "cluster_id": cluster_id,
                    "task_count": len(members),
                    "mean_difference": _frac_ratio(sum(members, Fraction(0)) / len(members)),
                }
            )
        overall = sum(
            (Fraction(cm["mean_difference"]["numerator"], cm["mean_difference"]["denominator"]) for cm in cluster_means),
            Fraction(0),
        ) / len(cluster_means)
        cluster_mean = {
            **_frac_ratio(overall),
            "cluster_count": len(cluster_means),
            "per_cluster_means": cluster_means,
        }

    return {
        "comparison": "fixed_l1_minus_recency",
        "metric": "per_task_facet_coverage",
        "scope": "OBSERVED_PAIR_ONLY_NO_IMPUTATION",
        "total_task_count": total,
        "included_task_count": len(included),
        "included_task_ids": sorted(record["task_id"] for record in included),
        "excluded_tasks": sorted(excluded, key=lambda e: e["task_id"]),
        "per_task_differences": per_task_diffs,
        "mean_paired_difference": _frac_ratio_or_empty(mean_diff),
        "cluster_mean_difference": cluster_mean,
        "included_vs_total": {"included": len(included), "total": total},
        "note": "DESCRIPTIVE_OBSERVED_PAIR_MEAN_NOT_A_VARIANCE_OR_POWER_QUANTITY_CLUSTERS_ARE_NOT_INDEPENDENT",
    }


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def summarize_evidence_accounting(value):
    """Return a detached descriptive summary dict for caller-supplied evidence."""
    root = _require_dict(value, "input", ("schema", "conditions", "tasks", "observations"))
    if type(root["schema"]) is not str or root["schema"] != INPUT_SCHEMA:
        raise EvidenceAccountingError("input schema must be " + INPUT_SCHEMA)

    conditions = root["conditions"]
    _require_list(conditions, "conditions", len(CONDITIONS))
    if any(type(condition) is not str for condition in conditions) or tuple(conditions) != CONDITIONS:
        raise EvidenceAccountingError("conditions must be exactly the three fixed conditions in fixed order")

    raw_tasks = _require_list(root["tasks"], "tasks", MAX_TASKS)
    tasks = {}
    for i, raw in enumerate(raw_tasks):
        task_id, task = _validate_task(raw, i)
        if task_id in tasks:
            raise EvidenceAccountingError("tasks contains a duplicate task_id")
        tasks[task_id] = task

    raw_observations = _require_list(root["observations"], "observations", MAX_OBSERVATIONS)
    cells = {}
    for i, raw in enumerate(raw_observations):
        _validate_observation(raw, i, tasks, cells)

    per_condition = {}
    for condition in CONDITIONS:
        tally = {"material": {v: 0 for v in VERDICTS}, "nonmaterial": {v: 0 for v in VERDICTS}}
        totals = {"material": 0, "nonmaterial": 0, "critical": 0}
        ledger = {cell: 0 for cell in LEDGER_CELLS}
        for task_id in tasks:
            cell = cells.get((task_id, condition))
            if cell is None:
                ledger["missing"] += 1
                continue
            answerability = tasks[task_id]["answerability"]
            ledger[_ledger_cell(answerability, cell["state"], cell["answer_assessment"])] += 1
            cell_tally = _claim_tally(cell["claims"])
            for kind in ("material", "nonmaterial"):
                totals[kind] += cell_tally[kind]["total"]
                for verdict, count in cell_tally[kind]["verdict_counts"].items():
                    tally[kind][verdict] += count
            totals["critical"] += cell_tally["critical"]
        ledger_sum = sum(ledger.values())
        if ledger_sum != len(tasks):
            raise RuntimeError("internal ledger accounting error")
        per_condition[condition] = {
            "contradiction_recall": {"value": None, "status": "NOT_REGISTERED"},
            "task_ledger": dict(
                ledger,
                sum=ledger_sum,
                total_task_count=len(tasks),
            ),
            "support": _support_section(
                {
                    "material": {"total": totals["material"], "verdict_counts": tally["material"]},
                    "nonmaterial": {"total": totals["nonmaterial"], "verdict_counts": tally["nonmaterial"]},
                    "critical": totals["critical"],
                }
            ),
            "retrieval_counts": _retrieval_counts(
                [cells.get((task_id, condition)) for task_id in tasks]
            ),
        }

    per_task = []
    global_critical = 0
    for task_id in sorted(tasks):
        task = tasks[task_id]
        condition_records = {}
        for condition in CONDITIONS:
            cell = cells.get((task_id, condition))
            if cell is None:
                cell_tally = _claim_tally([])
                coverage = _not_observed_ratio(len(task["required_facet_ids"]))
                precision = {"numerator": None, "denominator": None, "value": None, "status": "NOT_OBSERVED"}
                condition_records[condition] = {
                    "record_present": False,
                    "state": "missing",
                    "answer_assessment": None,
                    "ledger_cell": "missing",
                    "claim_counts": {
                        "material": {"total": 0, "verdict_counts": {v: 0 for v in VERDICTS}},
                        "nonmaterial": {"total": 0, "verdict_counts": {v: 0 for v in VERDICTS}},
                        "critical": 0,
                    },
                    "coverage": coverage,
                    "retrieval_precision": precision,
                    "omission_count": None,
                    "retrieved_item_count": 0,
                    "relevance_2_item_count": 0,
                }
            else:
                cell_tally = _claim_tally(cell["claims"])
                coverage, precision, n_retrieved, n_rel2, omission = _coverage_for_cell(task, cell)
                condition_records[condition] = {
                    "record_present": True,
                    "state": cell["state"],
                    "answer_assessment": cell["answer_assessment"],
                    "ledger_cell": _ledger_cell(task["answerability"], cell["state"], cell["answer_assessment"]),
                    "claim_counts": {
                        "material": {"total": cell_tally["material"]["total"], "verdict_counts": dict(cell_tally["material"]["verdict_counts"])},
                        "nonmaterial": {"total": cell_tally["nonmaterial"]["total"], "verdict_counts": dict(cell_tally["nonmaterial"]["verdict_counts"])},
                        "critical": cell_tally["critical"],
                    },
                    "coverage": coverage,
                    "retrieval_precision": precision,
                    "omission_count": omission,
                    "retrieved_item_count": n_retrieved,
                    "relevance_2_item_count": n_rel2,
                }
                global_critical += cell_tally["critical"]
        per_task.append(
            {
                "task_id": task_id,
                "cluster_id": task["cluster_id"],
                "answerability": task["answerability"],
                "required_facet_ids": sorted(task["required_facet_ids"]),
                "k": task["k"],
                "conditions": condition_records,
            }
        )

    return {
        "schema": OUTPUT_SCHEMA,
        "assessment": "DESCRIPTIVE_ONLY_NOT_STUDY_ACCEPTANCE",
        "operational_admission": False,
        "statistical_inference": {
            "confidence_intervals": None,
            "effective_n": None,
            "reason": "NOT_REGISTERED",
        },
        "task_count": len(tasks),
        "condition_count": len(CONDITIONS),
        "clarifications": dict(CLARIFICATIONS),
        "per_condition": per_condition,
        "per_task": per_task,
        "paired_coverage_contrast": _paired_contrast(tasks, per_task),
        "critical_claim_count": global_critical,
    }
