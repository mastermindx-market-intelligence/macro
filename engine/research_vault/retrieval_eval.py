"""Pure scorer for the frozen Research Vault retrieval benchmark.

No store, network, or corpus access. The only I/O is ``load_benchmark``
reading the fixture path it is given. Thresholds stay unset: this module
measures a run, it does not decide whether a run passes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

BENCHMARK_SCHEMA = "research_vault.retrieval_benchmark.v1"
CLASSES = tuple(f"R{i}" for i in range(1, 17))
CASE_KEYS = frozenset({
    "id",
    "class",
    "query",
    "filters",
    "expected_doc_ids",
    "abstain_expected",
    "fill_state",
    "evidence",
    "notes",
})
FORBIDDEN_KEYS = frozenset({
    "bucket",
    "r2_key",
    "store",
    "root",
    "path",
    "url",
    "key",
    "locator",
})
FILL_STATES = frozenset({"READY", "PENDING_HOST_FILL"})
_ANCHOR_MAX = 200
_FOUND_STATES = frozenset({"FOUND", "PARTIAL"})
_BLOCKED_STATES = frozenset({"NOT_FOUND", "UNAVAILABLE"})


def load_benchmark(path: str) -> dict[str, Any]:
    """Load and validate a retrieval benchmark fixture.

    Raises ValueError on a wrong schema, a case whose keys are not exactly
    ``CASE_KEYS``, an unknown class or fill state, a forbidden key at any
    depth, an anchor longer than 200 characters, a duplicate case id, or a
    class in ``CLASSES`` with zero cases.
    """
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    _validate(document)
    return document


def score(
    benchmark: dict[str, Any],
    results_by_case: dict[str, Any] | None,
    *,
    k: int = 10,
) -> dict[str, Any]:
    """Score a retrieval run against a benchmark.

    ``results_by_case`` maps a case id to
    ``ranked_report_ids``, ``abstained``, ``evidence`` (an
    ``research_vault.evidence_result.v1`` object or None), and
    ``source_texts`` (report id to canonical extracted text).

    Evidence passages are read from ``evidence["passages"]``. Each passage
    carries ``report_id``, ``text``, ``start_byte``, ``end_byte``, and
    ``passage_text_sha256`` (lowercase hex sha256 of ``text`` as UTF-8).
    ``evidence["evidence_state"]`` is ``FOUND``, ``PARTIAL``, ``NOT_FOUND``,
    or ``UNAVAILABLE``.

    READY cases missing from ``results_by_case`` score as zero and are listed
    in ``missing_results``. PENDING_HOST_FILL cases are excluded from the
    rates and counted in ``excluded_pending``. They are never silently dropped.
    Recall uses the top-k ids. Reciprocal rank uses the full ranking, because
    the benchmark defines recall-at-k and MRR separately. A mean over an empty
    population is None. ``thresholds`` is always None.
    """
    cases = list(benchmark.get("cases") or [])
    results = results_by_case if isinstance(results_by_case, dict) else {}
    top_k = k if type(k) is int and k > 0 else 0

    recall_values: list[float] = []
    mrr_values: list[float] = []
    abstain_hits = 0
    abstain_total = 0
    anchor_hits = 0
    anchor_total = 0
    invented = 0
    missing: list[str] = []
    pending = 0
    grouped: dict[str, list[dict[str, Any]]] = {cls: [] for cls in CLASSES}

    for case in cases:
        if not isinstance(case, dict):
            continue
        cls = case.get("class")
        if cls in grouped:
            grouped[cls].append(case)
        elif isinstance(cls, str):
            grouped.setdefault(cls, []).append(case)
        if case.get("fill_state") == "PENDING_HOST_FILL":
            pending += 1

        result = results.get(case.get("id"))
        if isinstance(result, dict):
            invented += _invented_count(result)

        if case.get("fill_state") != "READY":
            continue

        case_id = case.get("id")
        present = isinstance(case_id, str) and case_id in results
        if not present and isinstance(case_id, str):
            missing.append(case_id)
        ranked = _ranked(result) if present else []

        if case.get("abstain_expected") is True:
            abstain_total += 1
            if present and _abstained_clean(result):
                abstain_hits += 1
        else:
            expected = _expected(case)
            recall_values.append(_recall(expected, ranked, top_k))
            mrr_values.append(_reciprocal(ranked, expected[0] if expected else None))

        anchor = _anchor(case)
        if anchor and present and _evidence_state(result) in _FOUND_STATES:
            anchor_total += 1
            if any(anchor in text for text in _passage_texts(result)):
                anchor_hits += 1

    per_class: dict[str, dict[str, Any]] = {}
    for cls, group in grouped.items():
        if not group and cls not in CLASSES:
            continue
        if cls in CLASSES and not group:
            # Loaded benchmarks have every class; still emit an explicit zero
            # so a class cannot disappear from the report.
            per_class[cls] = {
                "cases": 0,
                "ready": 0,
                "recall_at_k": None,
                "mrr": None,
            }
            continue
        ready_group = [c for c in group if c.get("fill_state") == "READY"]
        measurable = [c for c in ready_group if c.get("abstain_expected") is not True]
        class_recall: list[float] = []
        class_mrr: list[float] = []
        for case in measurable:
            case_id = case.get("id")
            present = isinstance(case_id, str) and case_id in results
            ranked = _ranked(results.get(case_id)) if present else []
            expected = _expected(case)
            class_recall.append(_recall(expected, ranked, top_k))
            class_mrr.append(_reciprocal(ranked, expected[0] if expected else None))
        per_class[cls] = {
            "cases": len(group),
            "ready": len(ready_group),
            "recall_at_k": _mean(class_recall),
            "mrr": _mean(class_mrr),
        }

    return {
        "recall_at_k": _mean(recall_values),
        "mrr": _mean(mrr_values),
        "abstention_accuracy": (
            abstain_hits / abstain_total if abstain_total else None
        ),
        "anchor_match_rate": (
            anchor_hits / anchor_total if anchor_total else None
        ),
        "invented_evidence_count": invented,
        "per_class": per_class,
        "excluded_pending": pending,
        "missing_results": missing,
        "thresholds": None,
    }


def _validate(document: Any) -> None:
    if not isinstance(document, dict):
        raise ValueError("benchmark must be an object")
    schema = document.get("schema")
    if schema != BENCHMARK_SCHEMA:
        raise ValueError(f"wrong schema {schema!r}")
    _reject_forbidden(document)
    cases = document.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")

    seen: set[str] = set()
    counts = {cls: 0 for cls in CLASSES}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        keys = set(case.keys())
        if keys != set(CASE_KEYS):
            extra = sorted(keys - set(CASE_KEYS))
            missing = sorted(set(CASE_KEYS) - keys)
            raise ValueError(f"case keys mismatch extra={extra} missing={missing}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("case id must be a non-empty string")
        if case_id in seen:
            raise ValueError(f"duplicate case id {case_id!r}")
        seen.add(case_id)
        cls = case.get("class")
        if cls not in CLASSES:
            raise ValueError(f"unknown class {cls!r}")
        counts[cls] += 1
        fill = case.get("fill_state")
        if fill not in FILL_STATES:
            raise ValueError(f"unknown fill_state {fill!r}")
        _reject_long_anchor(case.get("evidence"))

    for cls in CLASSES:
        if counts[cls] == 0:
            raise ValueError(f"class {cls} has zero cases")


def _reject_forbidden(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden key {key!r}")
            _reject_forbidden(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden(child)


def _reject_long_anchor(evidence: Any) -> None:
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    if "anchor" not in evidence:
        return
    anchor = evidence.get("anchor")
    if not isinstance(anchor, str):
        raise ValueError("anchor must be a string")
    if len(anchor) > _ANCHOR_MAX:
        raise ValueError("anchor exceeds 200 characters")


def _invented_count(result: dict[str, Any]) -> int:
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return 0
    passages = evidence.get("passages")
    if not isinstance(passages, list):
        return 0
    state = evidence.get("evidence_state")
    source_texts = result.get("source_texts")
    if not isinstance(source_texts, dict):
        source_texts = {}
    return sum(
        1 for passage in passages if _passage_invented(passage, state, source_texts)
    )


def _passage_invented(
    passage: Any,
    evidence_state: Any,
    source_texts: dict[str, Any],
) -> bool:
    """One invented passage counts once, whichever check fails.

    A passage is invented when its UTF-8 bytes are not the source slice, its
    sha256 does not match ``text``, its report has no source text, or it is
    carried under NOT_FOUND or UNAVAILABLE.
    """
    if not isinstance(passage, dict):
        return True
    text = passage.get("text")
    if not isinstance(text, str):
        return True
    passage_state = passage.get("evidence_state")
    if evidence_state in _BLOCKED_STATES or passage_state in _BLOCKED_STATES:
        return True
    report_id = passage.get("report_id")
    source = source_texts.get(report_id)
    if not isinstance(source, str):
        return True
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if passage.get("passage_text_sha256") != digest:
        return True
    start = passage.get("start_byte")
    end = passage.get("end_byte")
    if type(start) is not int or type(end) is not int:
        return True
    source_bytes = source.encode("utf-8")
    text_bytes = text.encode("utf-8")
    if start < 0 or end < start or end > len(source_bytes):
        return True
    return text_bytes != source_bytes[start:end]


def _ranked(result: Any) -> list[Any]:
    if not isinstance(result, dict):
        return []
    ranked = result.get("ranked_report_ids")
    return list(ranked) if isinstance(ranked, list) else []


def _expected(case: dict[str, Any]) -> list[Any]:
    expected = case.get("expected_doc_ids")
    return list(expected) if isinstance(expected, list) else []


def _abstained_clean(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    ranked = result.get("ranked_report_ids")
    return result.get("abstained") is True and isinstance(ranked, list) and not ranked


def _evidence_state(result: Any) -> Any:
    if not isinstance(result, dict):
        return None
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return None
    return evidence.get("evidence_state")


def _passage_texts(result: Any) -> list[str]:
    if not isinstance(result, dict):
        return []
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return []
    passages = evidence.get("passages")
    if not isinstance(passages, list):
        return []
    return [
        passage.get("text")
        for passage in passages
        if isinstance(passage, dict) and isinstance(passage.get("text"), str)
    ]


def _anchor(case: dict[str, Any]) -> str | None:
    evidence = case.get("evidence")
    if not isinstance(evidence, dict):
        return None
    anchor = evidence.get("anchor")
    if isinstance(anchor, str) and anchor:
        return anchor
    return None


def _recall(expected: list[Any], ranked: list[Any], top_k: int) -> float:
    if not expected:
        return 0.0
    target = set(expected)
    hit = target & set(ranked[:top_k])
    return len(hit) / len(target)


def _reciprocal(ranked: list[Any], first_expected: Any) -> float:
    if first_expected is None:
        return 0.0
    for index, report_id in enumerate(ranked):
        if report_id == first_expected:
            return 1.0 / (index + 1)
    return 0.0


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
