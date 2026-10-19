"""Frozen retrieval benchmark v1 and the pure scorer.

T2 and T3 read the public catalog and excerpts snapshots through
``git show``. They skip only when that snapshot cannot be read, or when the
catalog blob has moved and the fixture must be re-frozen.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from engine.research_vault.retrieval_eval import (
    BENCHMARK_SCHEMA,
    CLASSES,
    CASE_KEYS,
    FORBIDDEN_KEYS,
    load_benchmark,
    score,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "research_vault" / "retrieval_benchmark_v1.json"
CATALOG_SPEC = "origin/main:data/research_vault/catalog.json"
EXCERPTS_SPEC = "origin/main:data/research_vault/excerpts.json"

_MINIMUMS = {cls: 2 for cls in CLASSES}
for _cls in ("R3", "R5", "R6", "R8", "R9", "R14"):
    _MINIMUMS[_cls] = 3

_READY = frozenset({
    "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R12", "R13", "R14",
})
_PENDING = frozenset({"R1", "R2", "R10", "R11", "R15", "R16"})


def _git(args: list[str], *, text: bool) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=text,
        check=False,
    )


def _git_show(spec: str) -> bytes:
    proc = _git(["git", "show", spec], text=False)
    if proc.returncode != 0:
        pytest.skip(f"snapshot unavailable: {spec}")
    return proc.stdout


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _pack(ranked, abstained, evidence=None, sources=None):
    return {
        "ranked_report_ids": list(ranked),
        "abstained": abstained,
        "evidence": evidence,
        "source_texts": dict(sources or {}),
    }


def _perfect(benchmark: dict) -> dict:
    results = {}
    for case in benchmark["cases"]:
        if case["fill_state"] != "READY":
            continue
        if case["abstain_expected"]:
            results[case["id"]] = _pack([], True)
        else:
            results[case["id"]] = _pack(case["expected_doc_ids"], False)
    return results


def _case(case_id: str, cls: str, *, fill: str, abstain: bool, expected: list[str],
          evidence: dict | None = None) -> dict:
    return {
        "id": case_id,
        "class": cls,
        "query": "synthetic query",
        "filters": {},
        "expected_doc_ids": list(expected),
        "abstain_expected": abstain,
        "fill_state": fill,
        "evidence": {} if evidence is None else evidence,
        "notes": "synthetic",
    }


def _minimal_document() -> dict:
    pending = {"R1", "R2", "R10", "R11", "R15", "R16"}
    cases = []
    for cls in CLASSES:
        abstain = cls in {"R9", "R13"}
        cases.append(_case(
            f"{cls}-1",
            cls,
            fill="PENDING_HOST_FILL" if cls in pending else "READY",
            abstain=abstain,
            expected=[] if abstain else [f"doc-{cls}"],
        ))
    return {
        "schema": BENCHMARK_SCHEMA,
        "version": 1,
        "source_snapshot": {"catalog_blob": "a" * 40, "excerpts_blob": "b" * 40},
        "cases": cases,
    }


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "bench.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _passage(source: str, text: str, *, report_id: str = "docA",
             start: int | None = None, end: int | None = None,
             digest: str | None = None) -> dict:
    encoded = text.encode("utf-8")
    if start is None:
        start = source.encode("utf-8").find(encoded)
    if end is None:
        end = start + len(encoded)
    if digest is None:
        digest = hashlib.sha256(encoded).hexdigest()
    return {
        "report_id": report_id,
        "text": text,
        "start_byte": start,
        "end_byte": end,
        "passage_text_sha256": digest,
    }


def _evidence(state: str, passages: list[dict]) -> dict:
    return {
        "schema": "research_vault.evidence_result.v1",
        "evidence_state": state,
        "passages": passages,
    }


def test_t1_fixture_loads_and_covers_every_class():
    benchmark = load_benchmark(FIXTURE)
    assert benchmark["schema"] == BENCHMARK_SCHEMA
    assert benchmark["version"] == 1
    assert set(benchmark["source_snapshot"]) == {"catalog_blob", "excerpts_blob"}
    counts = {cls: 0 for cls in CLASSES}
    for case in benchmark["cases"]:
        assert set(case) == set(CASE_KEYS)
        assert case["class"] in CLASSES
        counts[case["class"]] += 1
        if case["class"] in _READY:
            assert case["fill_state"] == "READY"
        else:
            assert case["class"] in _PENDING
            assert case["fill_state"] == "PENDING_HOST_FILL"
        anchor = case["evidence"].get("anchor") if case["evidence"] else None
        if anchor is not None:
            assert isinstance(anchor, str)
            assert len(anchor) <= 200
        if case["class"] == "R1":
            assert isinstance(anchor, str) and anchor
        if case["class"] == "R12":
            pages = int(case["notes"].split("pages=", 1)[1].split(";", 1)[0])
            assert pages >= 100
        if case["class"] == "R9":
            assert case["abstain_expected"] is True
            assert case["expected_doc_ids"] == []
            assert "zero-hit: catalog=0 excerpts=0" in case["notes"]
    for cls, minimum in _MINIMUMS.items():
        assert counts[cls] >= minimum, cls
    assert not (set(_walk_keys(benchmark)) & FORBIDDEN_KEYS)


def test_t2_ready_ids_exist_in_catalog_snapshot():
    rev = _git(["git", "rev-parse", CATALOG_SPEC], text=True)
    if rev.returncode != 0:
        pytest.skip(f"snapshot unavailable: {CATALOG_SPEC}")
    blob = rev.stdout.strip()
    benchmark = load_benchmark(FIXTURE)
    if benchmark["source_snapshot"]["catalog_blob"] != blob:
        pytest.skip("snapshot moved: re-freeze")
    catalog = json.loads(_git_show(CATALOG_SPEC))
    ids = {item["id"] for item in catalog["items"]}
    for case in benchmark["cases"]:
        if case["fill_state"] != "READY":
            continue
        missing = [doc_id for doc_id in case["expected_doc_ids"] if doc_id not in ids]
        assert not missing, (case["id"], missing)


def test_t3_anchors_are_byte_present_in_excerpts():
    excerpts = json.loads(_git_show(EXCERPTS_SPEC))["excerpts"]
    benchmark = load_benchmark(FIXTURE)
    checked = 0
    for case in benchmark["cases"]:
        anchor = case["evidence"].get("anchor") if case["evidence"] else None
        if not isinstance(anchor, str) or not anchor:
            continue
        checked += 1
        assert case["expected_doc_ids"], case["id"]
        passages = excerpts[case["expected_doc_ids"][0]]
        assert any(isinstance(passage, str) and anchor in passage for passage in passages)
    assert checked >= 1


def test_t4_load_benchmark_rejects_each_fault(tmp_path):
    extra = _minimal_document()
    extra["cases"][0]["comment"] = "nope"
    with pytest.raises(ValueError, match="comment"):
        load_benchmark(_write(tmp_path, extra))

    missing = _minimal_document()
    del missing["cases"][0]["notes"]
    with pytest.raises(ValueError, match="notes"):
        load_benchmark(_write(tmp_path, missing))

    unknown = _minimal_document()
    rogue = copy.deepcopy(unknown["cases"][0])
    rogue["id"] = "R17-1"
    rogue["class"] = "R17"
    unknown["cases"].append(rogue)
    with pytest.raises(ValueError, match="R17"):
        load_benchmark(_write(tmp_path, unknown))

    nested = _minimal_document()
    nested["cases"][0]["evidence"] = {"detail": {"r2_key": "nope"}}
    with pytest.raises(ValueError, match="r2_key"):
        load_benchmark(_write(tmp_path, nested))

    long_anchor = _minimal_document()
    long_anchor["cases"][0]["evidence"] = {"anchor": "a" * 201}
    with pytest.raises(ValueError, match="200"):
        load_benchmark(_write(tmp_path, long_anchor))

    duplicate = _minimal_document()
    duplicate["cases"][1]["id"] = duplicate["cases"][0]["id"]
    with pytest.raises(ValueError, match="duplicate case id"):
        load_benchmark(_write(tmp_path, duplicate))

    dropped = _minimal_document()
    dropped["cases"] = [case for case in dropped["cases"] if case["class"] != "R16"]
    with pytest.raises(ValueError, match="R16 has zero cases"):
        load_benchmark(_write(tmp_path, dropped))


def test_t5_score_on_synthetic_results():
    benchmark = load_benchmark(FIXTURE)
    pending = sum(
        case["fill_state"] == "PENDING_HOST_FILL" for case in benchmark["cases"]
    )
    ready_ids = [
        case["id"] for case in benchmark["cases"] if case["fill_state"] == "READY"
    ]

    perfect = score(benchmark, _perfect(benchmark))
    assert perfect["recall_at_k"] == 1.0
    assert perfect["mrr"] == 1.0
    assert perfect["invented_evidence_count"] == 0
    assert perfect["abstention_accuracy"] == 1.0
    assert perfect["excluded_pending"] == pending
    assert perfect["missing_results"] == []
    assert perfect["thresholds"] is None
    for cls, minimum in _MINIMUMS.items():
        assert perfect["per_class"][cls]["cases"] >= minimum
    assert perfect["per_class"]["R3"]["recall_at_k"] == 1.0
    assert perfect["per_class"]["R9"]["recall_at_k"] is None
    assert perfect["per_class"]["R13"]["mrr"] is None

    empty = score(benchmark, {})
    assert empty["recall_at_k"] == 0.0
    assert empty["mrr"] == 0.0
    assert empty["missing_results"] == ready_ids
    assert empty["excluded_pending"] == pending

    refused = _perfect(benchmark)
    for case in benchmark["cases"]:
        if case["fill_state"] == "READY" and case["abstain_expected"]:
            refused[case["id"]] = _pack(["should-not-rank"], False)
    assert score(benchmark, refused)["abstention_accuracy"] == 0.0

    tiny = {
        "schema": BENCHMARK_SCHEMA,
        "cases": [
            _case("M-1", "R5", fill="READY", abstain=False, expected=["docA"]),
            _case("A-1", "R9", fill="READY", abstain=True, expected=[]),
            _case("P-1", "R1", fill="PENDING_HOST_FILL", abstain=False, expected=["docP"]),
        ],
    }
    ranked = score(tiny, {
        "M-1": _pack(["other", "docA"], False),
        "A-1": _pack([], True),
    })
    assert ranked["mrr"] == 0.5
    assert ranked["recall_at_k"] == 1.0
    assert ranked["excluded_pending"] == 1
    assert ranked["abstention_accuracy"] == 1.0

    source = "alpha ANCHOR-TOKEN omega"
    anchor = "ANCHOR-TOKEN"
    found = _evidence("FOUND", [_passage(source, anchor)])
    anchored = {
        "schema": BENCHMARK_SCHEMA,
        "cases": [
            _case("R4-1", "R4", fill="READY", abstain=False, expected=["docA"],
                  evidence={"anchor": anchor}),
        ],
    }
    hit = score(anchored, {"R4-1": _pack(["docA"], False, found, {"docA": source})})
    assert hit["anchor_match_rate"] == 1.0
    assert hit["invented_evidence_count"] == 0

    miss_text = "alpha"
    missed = _evidence("FOUND", [_passage(source, miss_text)])
    miss = score(anchored, {"R4-1": _pack(["docA"], False, missed, {"docA": source})})
    assert miss["anchor_match_rate"] == 0.0
    assert miss["invented_evidence_count"] == 0


def _one_ready(evidence: dict, sources: dict) -> int:
    benchmark = {
        "schema": BENCHMARK_SCHEMA,
        "cases": [_case("R4-1", "R4", fill="READY", abstain=False, expected=["docA"])],
    }
    return score(
        benchmark,
        {"R4-1": _pack(["docA"], False, evidence, sources)},
    )["invented_evidence_count"]


def test_t6_invented_evidence_counter_is_one_per_failure():
    source = "abcdefghijklmnopqrstuvwxyz"
    faithful = _passage(source, source)
    byte_mismatch = _passage(source, "XXXXXXXXXX", start=0, end=10)
    bad_hash = _passage(source, source, digest="0" * 64)
    not_found = _evidence("NOT_FOUND", [faithful])
    unavailable = _evidence("UNAVAILABLE", [dict(faithful)])
    no_source = _evidence("FOUND", [_passage(source, source, report_id="missing")])
    found_bad_bytes = _evidence("FOUND", [byte_mismatch])
    found_bad_hash = _evidence("FOUND", [bad_hash])
    found_ok = _evidence("FOUND", [faithful])

    assert _one_ready(found_bad_bytes, {"docA": source}) == 1
    assert _one_ready(found_bad_hash, {"docA": source}) == 1
    assert _one_ready(not_found, {"docA": source}) == 1
    assert _one_ready(no_source, {"docA": source}) == 1
    assert _one_ready(unavailable, {"docA": source}) == 1
    assert _one_ready(found_ok, {"docA": source}) == 0


def test_t7_thresholds_are_none():
    benchmark = load_benchmark(FIXTURE)
    assert score(benchmark, {})["thresholds"] is None
    assert score(benchmark, _perfect(benchmark))["thresholds"] is None
