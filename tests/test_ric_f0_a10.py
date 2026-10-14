"""RIC-INCLUDED-CORE F0 gap (A10): canonical calendar owns schedule; no second calendar.

Lane packet F0-GAPS — event_window must read engine/event_calendar at call time.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from engine import event_calendar as ec
from engine import event_window as ew
from engine import hk_event_calendar as hk

# Known live drift in engine/hk_event_calendar.py (not ORCH-B-owned). The fix makes hk read the canonical
# calendar and EMPTIES this ledger in the same PR.
_HK_US_CPI_KNOWN_DRIFT = {10: (13, 14), 11: (12, 10)}

_HK_US_NFP_KNOWN_DRIFT = {1: (2, 9), 5: (1, 8), 7: (3, 2)}


def _oct_tag() -> pd.DataFrame:
    return ew.tag(pd.bdate_range("2026-10-01", "2026-10-31"))


def _canonical_fomc():
    return ec.fomc_decision_dates(date.min, date.max)


@pytest.mark.parametrize(
    "etype,column,old,new",
    [
        ("CPI", "td_to_cpi", 14, 20),
        ("PPI", "td_to_ppi", 15, 22),
        ("NFP", "td_to_nfp", 2, 9),
    ],
    ids=["CPI", "PPI", "NFP"],
)
def test_canonical_release_day_move_moves_event_window_tag(
    monkeypatch, etype, column, old, new
):
    assert ec._SCHED_2026[etype][10] == old
    monkeypatch.setitem(
        ec._SCHED_2026, etype, {**ec._SCHED_2026[etype], 10: new}
    )
    t = _oct_tag()
    assert t.loc[pd.Timestamp(2026, 10, new), column] == 0
    assert t.loc[pd.Timestamp(2026, 10, old), column] != 0


def test_canonical_fomc_move_moves_event_window_tag(monkeypatch):
    assert ("2026-10-28", False) in ec._FOMC
    monkeypatch.setattr(
        ec,
        "_FOMC",
        [
            ("2026-10-27", s) if d == "2026-10-28" else (d, s)
            for d, s in ec._FOMC
        ],
    )
    t = _oct_tag()
    assert t.loc[pd.Timestamp(2026, 10, 27), "td_to_fomc"] == 0
    assert t.loc[pd.Timestamp(2026, 10, 28), "td_to_fomc"] != 0


def test_fomc_archive_ends_before_canonical_begins():
    assert max(int(s[:4]) for s in ew._FOMC_ARCHIVE_PRE_CANONICAL) < min(
        d.year for d in _canonical_fomc()
    )


def test_event_window_has_no_literal_release_mirrors():
    for name in (
        "_CPI_2026",
        "_PPI_2026",
        "_NFP_2026",
        "_FOMC_ANNOUNCEMENT_DATES",
    ):
        assert not hasattr(ew, name)
    assert {s for s in ew._fomc_announcement_dates() if s >= "2026"} == {
        d.isoformat() for d in _canonical_fomc()
    }


def test_event_window_tag_matches_canonical_for_current_inputs():
    t = ew.tag(pd.bdate_range("2026-01-01", "2026-12-31"))
    for etype, column in (
        ("CPI", "td_to_cpi"),
        ("PPI", "td_to_ppi"),
        ("NFP", "td_to_nfp"),
    ):
        expected = {
            pd.Timestamp(2026, m, d)
            for m, d in ec._SCHED_2026[etype].items()
        } & set(t.index)
        actual = set(t.index[t[column] == 0])
        assert actual == expected, f"{etype}: {actual} != {expected}"
    fomc_expected = {
        pd.Timestamp(d.year, d.month, d.day) for d in _canonical_fomc() if d.year == 2026
    } & set(t.index)
    fomc_actual = set(t.index[t["td_to_fomc"] == 0])
    assert fomc_actual == fomc_expected


def test_hk_fomc_matches_canonical():
    assert set(hk._FOMC_2026) == {
        d for d in _canonical_fomc() if d.year == 2026
    }


def _iso_date(val) -> str:
    if isinstance(val, str):
        return val[:10]
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, (tuple, list)) and val:
        return _iso_date(val[0])
    raise TypeError(f"cannot normalise FOMC date: {type(val)!r}")


def test_catalyst_tone_and_marketing_fomc_copies_match_canonical():
    import engine.catalyst_tone as ct
    from engine.marketing import fomc_statements as fs

    canonical_by_year: dict[int, set[str]] = {}
    for d in _canonical_fomc():
        canonical_by_year.setdefault(d.year, set()).add(d.isoformat())

    tone_dates = [_iso_date(x) for x in ct._FOMC_MEETINGS]
    marketing_dates = [_iso_date(x) for x in fs._FOMC_2026_FALLBACK]

    for year in canonical_by_year:
        tone_year = {d for d in tone_dates if d.startswith(str(year))}
        if tone_year:
            assert tone_year == canonical_by_year[year]
    mkt_year = {d for d in marketing_dates if d.startswith("2026")}
    if mkt_year:
        assert mkt_year == canonical_by_year.get(2026, set())


def test_hk_us_cpi_drift_is_exactly_the_recorded_ledger():
    drift = {
        m: (
            hk._HK_SCHED_2026["US_CPI"].get(m),
            ec._SCHED_2026["CPI"].get(m),
        )
        for m in range(1, 13)
        if hk._HK_SCHED_2026["US_CPI"].get(m) != ec._SCHED_2026["CPI"].get(m)
    }
    assert drift == _HK_US_CPI_KNOWN_DRIFT, (
        "HK US CPI drift changed — fix hk_event_calendar to read canonical calendar"
    )


def test_hk_us_nfp_first_friday_drift_is_exactly_the_recorded_ledger():
    drift = {
        m: (
            hk._first_friday(2026, m).day,
            ec._SCHED_2026["NFP"].get(m),
        )
        for m in range(1, 13)
        if hk._first_friday(2026, m).day != ec._SCHED_2026["NFP"].get(m)
    }
    assert drift == _HK_US_NFP_KNOWN_DRIFT
