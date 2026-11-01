"""A51: the Z0 closure matrix covers every acceptance case and never overclaims.

The matrix maps each masterplan acceptance case to a verdict, the tests that
evidence it, and owned obligations for whatever is still open.  A CLOSED row
must cite tests that exist; every other row must name an owner and a next
action; the final claim stays unavailable while any row is not CLOSED."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "research" / "financial_intelligence_fabric" / "FIF_Z0_CLOSURE_MATRIX.json"
REQUIRED_KIND = {"HUMAN_GATE": "human_gate", "PENDING_LIVE": "live_proof"}


def _matrix() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def _test_exists(ref: str) -> bool:
    path, _, name = ref.partition("::")
    source = ROOT / path
    if not name or not source.is_file():
        return False
    text = source.read_text(encoding="utf-8")
    if path.endswith(".py"):
        return re.search(rf"^\s*def {re.escape(name)}\(", text, flags=re.M) is not None
    return name in text


def test_matrix_covers_every_case_once() -> None:
    doc = _matrix()
    ids = [case["id"] for case in doc["cases"]]
    assert ids == [f"A{n:02d}" for n in range(1, 55)]
    assert doc["masterplan"]["case_count"] == len(ids)
    for case in doc["cases"]:
        assert case["verdict"] in doc["verdicts"]
        assert case["condition"] and case["required_behavior"] and case["tasks"]
        assert all(obligation["kind"] in doc["obligation_kinds"] for obligation in case["obligations"])


def test_closed_rows_cite_existing_tests() -> None:
    for case in _matrix()["cases"]:
        missing = [ref for ref in case["evidence"] if not _test_exists(ref)]
        assert missing == [], case["id"]
        if case["verdict"] == "CLOSED":
            assert case["evidence"], case["id"]
            assert case["obligations"] == [], case["id"]


def test_open_rows_carry_owned_obligations() -> None:
    for case in _matrix()["cases"]:
        if case["verdict"] == "CLOSED":
            continue
        assert case["obligations"], case["id"]
        for obligation in case["obligations"]:
            assert obligation["owner"].strip() and obligation["next_action"].strip(), case["id"]
        required = REQUIRED_KIND.get(case["verdict"])
        if required:
            assert required in {obligation["kind"] for obligation in case["obligations"]}, case["id"]


def test_no_final_claim_while_any_row_is_open() -> None:
    doc = _matrix()
    counts = Counter(case["verdict"] for case in doc["cases"])
    assert doc["summary"] == {verdict: counts.get(verdict, 0) for verdict in doc["verdicts"]}
    all_closed = counts["CLOSED"] == len(doc["cases"])
    assert doc["final_acceptance"]["claimable"] is all_closed
    if not all_closed:
        assert doc["final_acceptance"]["independent_acceptance"] == "Z1 pending"
