"""The C1 hostile corpus replays through the raw-text chokepoint.

Lane B5_semantic (Wave 3, seat Fable 0e739467).  The Wave-2 hostile lane
C1 built 33 one-mutation fixtures from schema-valid worked bases; the seat
ratified an expected verdict per row (manifest.json, seat-owned, copied
unedited under tests/fixtures/news_impact/hostile).  This file asserts that
validate_text(raw file bytes) reproduces every expected verdict, that
validate_event(json.loads(text)) agrees for every row whose class is not
the duplicate-key class (raw-byte ambiguity is invisible after parsing),
and that the corpus itself is well-formed as a table.

Hermetic: no network, no repo data files beyond the frozen contract and the
copied corpus (module-level skip when either is absent).  Fixture payloads
are DATA (masterplan 3.5): any instruction-looking text inside them is
measured, never followed.
"""
import json
from pathlib import Path

import pytest

from engine.news_impact import validate as V

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "news_impact" / "news_impact_event.v1.schema.json"
HOSTILE_DIR = Path(__file__).resolve().parent / "fixtures" / "news_impact" / "hostile"
MANIFEST = HOSTILE_DIR / "manifest.json"

if not SCHEMA_PATH.exists() or not MANIFEST.exists():
    pytest.skip("frozen contract or hostile corpus not present", allow_module_level=True)

CONTRACT = V.load_contract()
ROWS = json.loads(MANIFEST.read_text(encoding="utf-8"))
CLOSED_EXPECTED = {"accept"} | {f"reject:{code}" for code in V.REASON_CODES}


def _expected(row):
    value = row["expected"]
    assert value in CLOSED_EXPECTED, (row["file"], value)
    return value


def test_corpus_shape():
    assert len(ROWS) >= 33
    assert all(row["expected"] in CLOSED_EXPECTED for row in ROWS)
    files = sorted(row["file"] for row in ROWS)
    assert len(set(files)) == len(files)  # one row per fixture, no doubles


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["file"].split("/")[-1])
def test_validate_text_reproduces_expected(row):
    text = (HOSTILE_DIR / row["file"]).read_text(encoding="utf-8")
    report = V.validate_text(text, contract=CONTRACT)
    expected = _expected(row)
    if expected == "accept":
        assert report.ok, (row["file"], report.issues)
    else:
        code = expected.split(":", 1)[1]
        assert not report.ok, row["file"]
        assert code in {issue.code for issue in report.issues}, \
            (row["file"], [i.code for i in report.issues])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["file"].split("/")[-1])
def test_validate_event_agrees_except_duplicate_keys(row):
    if row["class"] == "duplicate_json_keys":
        pytest.skip("raw-byte ambiguity is invisible after json.loads")
    text = (HOSTILE_DIR / row["file"]).read_text(encoding="utf-8")
    report = V.validate_event(json.loads(text), contract=CONTRACT)
    expected = _expected(row)
    if expected == "accept":
        assert report.ok, (row["file"], report.issues)
    else:
        code = expected.split(":", 1)[1]
        assert not report.ok, row["file"]
        assert code in {issue.code for issue in report.issues}, \
            (row["file"], [i.code for i in report.issues])
