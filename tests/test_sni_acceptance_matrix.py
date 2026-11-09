"""Keep the SNI acceptance evidence matrix JSON, renderer, and status law honest.

This is an SNI-local draft census. It consumes owner-supplied paths and does
not mint identity ids or feed a rank, gate, size, signal, escalation, or
trade path. All six authority flags on the matrix must stay false; a true
flag is refused by load_matrix at any depth.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
sys.path.insert(0, str(ACCEPTANCE))

from render_matrix import (  # noqa: E402
    AUTHORITY_FLAGS,
    check_counts,
    check_done_status_law,
    check_gated_status_law,
    check_main_evidence_paths,
    check_non_done_gaps,
    load_matrix,
    render,
)

JSON_PATH = ACCEPTANCE / "ACCEPTANCE_EVIDENCE_MATRIX.json"
MD_PATH = ACCEPTANCE / "ACCEPTANCE_EVIDENCE_MATRIX.md"
EXPECTED_IDS = [f"A{i:02d}" for i in range(1, 41)]
TOP_KEYS = (
    "schema_version",
    "as_of_utc",
    "sources",
    "authority_flags",
    "counts",
    "cases",
)
SOURCE_KEYS = ("census_ref", "census_path", "supersedes", "base_ref")


def _committed_doc() -> dict:
    return load_matrix(JSON_PATH)


def test_schema_pins():
    doc = _committed_doc()
    assert tuple(doc.keys()) == TOP_KEYS
    assert doc["schema_version"] == "sni_acceptance_matrix.v2"
    assert isinstance(doc["as_of_utc"], str) and doc["as_of_utc"]
    sources = doc["sources"]
    assert tuple(sources.keys()) == SOURCE_KEYS
    assert sources["census_ref"] == "7906ef1cd646282cb762651df0e33e9f70397ed5"
    assert sources["census_path"] == (
        "research/single_name_intelligence/e2e_20261011/CENSUS_AND_ACCEPTANCE.md"
    )
    assert sources["supersedes"] == "92eab08a156c405ea76efdeefa98416ccfae4af6"
    assert re.fullmatch(r"[0-9a-f]{40}", sources["base_ref"])
    flags = doc["authority_flags"]
    assert tuple(flags.keys()) == AUTHORITY_FLAGS
    for name in AUTHORITY_FLAGS:
        assert flags[name] is False


def test_ids_a01_to_a40_exactly_once_in_order():
    doc = _committed_doc()
    ids = [item["id"] for item in doc["cases"]]
    assert ids == EXPECTED_IDS
    assert len(set(ids)) == 40


def test_status_law_a_main_evidence_paths_exist():
    doc = _committed_doc()
    check_main_evidence_paths(doc, REPO)


def test_status_law_b_done_cases():
    doc = _committed_doc()
    check_done_status_law(doc, REPO)


def test_status_law_c_gated_cases():
    doc = _committed_doc()
    check_gated_status_law(doc)


def test_status_law_d_non_done_gaps():
    doc = _committed_doc()
    check_non_done_gaps(doc)


def test_status_law_e_counts():
    doc = _committed_doc()
    check_counts(doc)
    assert sum(doc["counts"].values()) == 40


def test_poisoned_authority_flag_refused_by_loader(tmp_path: Path):
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    for name in AUTHORITY_FLAGS:
        poisoned = copy.deepcopy(raw)
        poisoned["authority_flags"][name] = True
        path = tmp_path / f"poison_{name}.json"
        path.write_text(json.dumps(poisoned), encoding="utf-8")
        with pytest.raises(ValueError, match="authority flags must stay false"):
            load_matrix(path)


def test_poisoned_nested_trade_authority_refused_by_loader(tmp_path: Path):
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    poisoned = copy.deepcopy(raw)
    poisoned["cases"][0]["trade_authority"] = True
    path = tmp_path / "poison_nested_trade_authority.json"
    path.write_text(json.dumps(poisoned), encoding="utf-8")
    with pytest.raises(ValueError, match="authority flags must stay false"):
        load_matrix(path)


def test_render_determinism_matches_committed_markdown():
    doc = _committed_doc()
    first = render(doc)
    second = render(doc)
    assert first == second
    committed = MD_PATH.read_text(encoding="utf-8")
    assert committed == first


def test_poisoned_done_case_gated_on_r1_fails_status_law():
    doc = copy.deepcopy(_committed_doc())
    done = next(item for item in doc["cases"] if item["status"] == "DONE")
    done["gated_on"] = "R1"
    with pytest.raises(AssertionError, match="DONE but gated_on"):
        check_done_status_law(doc, REPO)
