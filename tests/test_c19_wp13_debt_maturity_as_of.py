"""C19-W5-WP13: point-in-time (``as_of``) debt-maturity ladder guards.

Offline only: the real trimmed Apple companyfacts fixture plus stdlib
json/copy/datetime. No network, no wall clock, no randomness.
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from engine.debt_maturity import extract_maturity_ladder, extract_maturity_ladder_as_of

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "debt_maturity"
AAPL_CIK = "0000320193"
OTHER_CIK = "0000789019"
NEXT_TWELVE = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
ACCN_FY2023 = "0000320193-23-000106"
ACCN_FY2024 = "0000320193-24-000123"
_ABSENT = object()


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def _annual_entries(companyfacts: dict) -> list[dict]:
    return companyfacts["facts"]["us-gaap"][NEXT_TWELVE]["units"]["USD"]


def _template_entry(companyfacts: dict) -> dict:
    """A real annual entry of the fixture, to mirror its exact key set."""
    for entry in _annual_entries(companyfacts):
        if entry.get("form") == "10-K" and entry.get("fp") == "FY":
            return entry
    raise AssertionError(f"fixture has no annual {NEXT_TWELVE} entry")


def _synthetic_annual(
    companyfacts: dict, *, accn: str, fy: int, end: str, val: float, filed: object = _ABSENT
) -> dict:
    """A synthetic FY ``10-K`` entry using the fixture's own entry key set."""
    values = {"accn": accn, "end": end, "fy": fy, "fp": "FY", "form": "10-K", "val": val}
    if filed is not _ABSENT:
        values["filed"] = filed
    return {key: values[key] for key in _template_entry(companyfacts) if key in values}


def _with_extra_annuals(companyfacts: dict, extra: list[dict]) -> dict:
    """A deep copy of the fixture with ``extra`` appended to the y1 USD list."""
    mutated = copy.deepcopy(companyfacts)
    _annual_entries(mutated).extend(copy.deepcopy(extra))
    return mutated


def test_as_of_between_filings_picks_earlier_annual():
    result = extract_maturity_ladder_as_of(
        _load("aapl_trimmed.json"), cik=AAPL_CIK, as_of=date(2024, 6, 1)
    )
    assert result["status"] == "reported"
    assert result["period"]["accn"] == ACCN_FY2023
    assert result["period"]["filed"] == "2023-11-03"


def test_as_of_filed_boundary_is_inclusive():
    companyfacts = _load("aapl_trimmed.json")
    on_filed_day = extract_maturity_ladder_as_of(
        companyfacts, cik=AAPL_CIK, as_of=date(2024, 11, 1)
    )
    assert on_filed_day["period"]["accn"] == ACCN_FY2024
    one_day_earlier = extract_maturity_ladder_as_of(
        companyfacts, cik=AAPL_CIK, as_of=date(2024, 10, 31)
    )
    assert one_day_earlier["period"]["accn"] == ACCN_FY2023


def test_as_of_after_all_filings_matches_existing_extractor():
    as_of = date(2025, 1, 1)
    point_in_time = extract_maturity_ladder_as_of(
        _load("aapl_trimmed.json"), cik=AAPL_CIK, as_of=as_of
    )
    existing = extract_maturity_ladder(_load("aapl_trimmed.json"), cik=AAPL_CIK, as_of=as_of)
    assert point_in_time == existing


def test_as_of_before_any_filing_fails_closed():
    result = extract_maturity_ladder_as_of(
        _load("aapl_trimmed.json"), cik=AAPL_CIK, as_of=date(2023, 1, 1)
    )
    assert result["status"] == "no_maturity_facts"
    assert result["buckets_reported"] == 0
    assert result["total_reported_usd"] is None


def test_missing_or_unparseable_filed_never_wins():
    companyfacts = _load("aapl_trimmed.json")
    no_filed = _synthetic_annual(
        companyfacts, accn="SYN-NOFILED", fy=2025, end="2025-09-27", val=7000000000.0
    )
    assert "filed" not in no_filed
    bad_filed = _synthetic_annual(
        companyfacts,
        accn="SYN-BADFILED",
        fy=2025,
        end="2025-09-27",
        val=8000000000.0,
        filed="not-a-date",
    )
    mutated = _with_extra_annuals(companyfacts, [no_filed, bad_filed])
    assert mutated is not companyfacts
    result = extract_maturity_ladder_as_of(mutated, cik=AAPL_CIK, as_of=date(2026, 1, 1))
    assert result["period"]["accn"] == ACCN_FY2024


def test_later_synthetic_annual_excluded_until_filed():
    companyfacts = _load("aapl_trimmed.json")
    later = _synthetic_annual(
        companyfacts,
        accn="SYN-FY2025",
        fy=2025,
        end="2025-09-27",
        val=9000000000.0,
        filed="2025-10-31",
    )
    mutated = _with_extra_annuals(companyfacts, [later])
    before_filed = extract_maturity_ladder_as_of(mutated, cik=AAPL_CIK, as_of=date(2025, 6, 1))
    assert before_filed["period"]["accn"] == ACCN_FY2024
    after_filed = extract_maturity_ladder_as_of(mutated, cik=AAPL_CIK, as_of=date(2025, 12, 1))
    assert after_filed["period"]["accn"] == "SYN-FY2025"


def test_as_of_does_not_mutate_input():
    companyfacts = _load("aapl_trimmed.json")
    before = copy.deepcopy(companyfacts)
    extract_maturity_ladder_as_of(companyfacts, cik=AAPL_CIK, as_of=date(2024, 6, 1))
    assert companyfacts == before


def test_as_of_identity_mismatch_still_fails_closed():
    result = extract_maturity_ladder_as_of(
        _load("aapl_trimmed.json"), cik=OTHER_CIK, as_of=date(2025, 1, 1)
    )
    assert result["status"] == "identity_mismatch"


def test_as_of_is_required_date():
    companyfacts = _load("aapl_trimmed.json")
    with pytest.raises(TypeError):
        extract_maturity_ladder_as_of(companyfacts, cik=AAPL_CIK, as_of=None)
    with pytest.raises(TypeError):
        extract_maturity_ladder_as_of(companyfacts, cik=AAPL_CIK, as_of=datetime(2024, 6, 1))
