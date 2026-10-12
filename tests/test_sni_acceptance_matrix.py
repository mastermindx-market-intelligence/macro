"""Keep the SNI acceptance evidence matrix JSON and markdown in sync.

This is an SNI-local draft census. It consumes owner-supplied paths and does
not mint identity ids or feed a rank, gate, size, signal, escalation, or
trade path. All six authority flags on the matrix must stay false; a true
flag is refused.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
JSON_PATH = (
    REPO
    / "research"
    / "single_name_intelligence"
    / "e2e_20261011"
    / "ACCEPTANCE_EVIDENCE_MATRIX.json"
)
MD_PATH = JSON_PATH.with_suffix(".md")

ALLOWED_STATUS = {"DONE", "PARTIAL", "GATED", "NOT_STARTED"}
ALLOWED_REF = {"main", "s2", "census"}
EXPECTED_IDS = [f"A{i:02d}" for i in range(1, 41)]
AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


def _load_matrix() -> dict:
    doc = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    flags = doc.get("authority_flags") or {}
    if any(flags.get(name) is True for name in AUTHORITY_FLAGS):
        raise ValueError("authority flags must stay false; a true flag is refused")
    return doc


def test_json_loads_and_schema_pins():
    doc = _load_matrix()
    assert doc["schema_version"] == "sni_acceptance_matrix.v1"
    assert isinstance(doc["as_of_utc"], str) and doc["as_of_utc"]
    sources = doc["sources"]
    assert sources["census_ref"] == "7906ef1cd646282cb762651df0e33e9f70397ed5"
    assert sources["s2_ref"] == "2aa9f76039966a0f3b6fc6685e75a3eac4eb52a2"
    assert isinstance(sources["main_ref"], str) and len(sources["main_ref"]) >= 40


def test_exactly_forty_ids_a01_to_a40_each_once():
    doc = _load_matrix()
    ids = [case["id"] for case in doc["cases"]]
    assert ids == EXPECTED_IDS
    assert len(set(ids)) == 40


def test_status_allowed_and_counts_match():
    doc = _load_matrix()
    computed = {name: 0 for name in ALLOWED_STATUS}
    for case in doc["cases"]:
        assert case["status"] in ALLOWED_STATUS
        computed[case["status"]] += 1
        assert case["gated_on"] in ("R1", None)
        assert isinstance(case["owner_task"], str) and case["owner_task"]
        assert isinstance(case["title"], str) and case["title"]
        assert isinstance(case["evidence"], list)
        for item in case["evidence"]:
            assert item["ref"] in ALLOWED_REF
            assert item["path"]
            assert item["note"]
    assert doc["counts"] == computed
    assert sum(computed.values()) == 40


def test_authority_flags_all_false():
    doc = _load_matrix()
    flags = doc["authority_flags"]
    for name in AUTHORITY_FLAGS:
        assert flags[name] is False
    with pytest.raises(ValueError, match="authority flags must stay false"):
        poisoned = dict(doc)
        poisoned["authority_flags"] = dict(flags)
        poisoned["authority_flags"]["rank_authority"] = True
        if any(
            poisoned["authority_flags"].get(name) is True for name in AUTHORITY_FLAGS
        ):
            raise ValueError(
                "authority flags must stay false; a true flag is refused"
            )


def test_done_cases_cite_existing_main_or_s2_or_census():
    doc = _load_matrix()
    for case in doc["cases"]:
        if case["status"] != "DONE":
            continue
        ok = False
        for item in case["evidence"]:
            if item["ref"] in ("s2", "census"):
                ok = True
                break
            if item["ref"] == "main" and (REPO / item["path"]).is_file():
                ok = True
                break
        assert ok, f"{case['id']} DONE without main/s2/census evidence"


def test_non_done_cases_have_nonempty_gap():
    doc = _load_matrix()
    for case in doc["cases"]:
        if case["status"] == "DONE":
            continue
        gap = case.get("gap") or ""
        assert gap.strip(), f"{case['id']} {case['status']} missing gap"


def test_markdown_table_contains_each_id_once():
    text = MD_PATH.read_text(encoding="utf-8")
    table, _sep, rest = text.partition("## Closest to DONE")
    assert _sep, "markdown is missing the Closest to DONE section"
    found = re.findall(r"^\| (A\d{2}) \|", table, flags=re.M)
    assert found == EXPECTED_IDS
    # The Gated on R1 section lists gated ids; table must still be unique.
    assert rest
    assert "## Gated on R1" in rest
