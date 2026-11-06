"""RIC-INCLUDED-CORE F0 gap (A10): canonical calendar owns schedule; no second calendar.

Lane packet F0-GAPS — event_window must read engine/event_calendar at call time.
Lane packet F0-HK — the HK desk (engine/hk_event_calendar) reads the SAME canonical
calendar at call time for its three US event types (FOMC / US_NFP / US_CPI).
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from engine import event_calendar as ec
from engine import event_window as ew
from engine import hk_event_calendar as hk

# The HK desk now READS the canonical calendar (engine/event_calendar) at call time
# for FOMC / US_NFP / US_CPI, so the known-drift ledgers are EMPTY by construction:
# a drift can only appear if a second calendar reappears in hk_event_calendar.
_HK_US_CPI_KNOWN_DRIFT = {}

_HK_US_NFP_KNOWN_DRIFT = {}


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
    full = hk.hk_macro_events(asof=date(2026, 1, 1), horizon_days=364)
    assert {e["date"] for e in full if e["type"] == "FOMC"} == {
        d.isoformat() for d in _canonical_fomc() if d.year == 2026
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


def _hk_year_dates(etype: str) -> dict[int, int]:
    """month -> day of the HK desk's 2026 rows for ``etype``, from the full-year
    call (so the drift ledgers measure what the desk EMITS, not what it stores)."""
    full = hk.hk_macro_events(asof=date(2026, 1, 1), horizon_days=364)
    out: dict[int, int] = {}
    for e in full:
        if e["type"] != etype:
            continue
        d = date.fromisoformat(e["date"])
        if d.year != 2026:
            continue
        assert d.month not in out, f"two {etype} rows in month {d.month}"
        out[d.month] = d.day
    return out


def test_hk_us_cpi_drift_is_exactly_the_recorded_ledger():
    hk_day = _hk_year_dates("US_CPI")
    drift = {
        m: (hk_day.get(m), ec._SCHED_2026["CPI"].get(m))
        for m in range(1, 13)
        if hk_day.get(m) != ec._SCHED_2026["CPI"].get(m)
    }
    assert drift == _HK_US_CPI_KNOWN_DRIFT, (
        "HK US CPI drift changed — fix hk_event_calendar to read canonical calendar"
    )


def test_hk_us_nfp_first_friday_drift_is_exactly_the_recorded_ledger():
    hk_day = _hk_year_dates("US_NFP")
    drift = {
        m: (hk_day.get(m), ec._SCHED_2026["NFP"].get(m))
        for m in range(1, 13)
        if hk_day.get(m) != ec._SCHED_2026["NFP"].get(m)
    }
    assert drift == _HK_US_NFP_KNOWN_DRIFT


def test_canonical_cpi_move_moves_hk_us_cpi(monkeypatch):
    monkeypatch.setitem(ec._SCHED_2026["CPI"], 10, 20)
    evs = hk.hk_macro_events(asof=date(2026, 10, 1), horizon_days=30)
    cpi = [e["date"] for e in evs if e["type"] == "US_CPI"]
    assert cpi == ["2026-10-20"]
    assert "2026-10-13" not in cpi and "2026-10-14" not in cpi


def test_canonical_nfp_move_moves_hk_us_nfp(monkeypatch):
    monkeypatch.setitem(ec._SCHED_2026["NFP"], 10, 9)
    evs = hk.hk_macro_events(asof=date(2026, 10, 1), horizon_days=30)
    nfp = [e["date"] for e in evs if e["type"] == "US_NFP"]
    assert nfp == ["2026-10-09"]
    assert "2026-10-02" not in nfp


def test_canonical_fomc_move_moves_hk_fomc_and_hkma(monkeypatch):
    moved = [
        ("2026-10-21", sep) if d == "2026-10-28" else (d, sep)
        for d, sep in ec._FOMC
    ]
    monkeypatch.setattr(ec, "_FOMC", moved)
    evs = hk.hk_macro_events(asof=date(2026, 10, 1), horizon_days=30)
    assert [e["date"] for e in evs if e["type"] == "FOMC"] == ["2026-10-21"]
    assert [e["date"] for e in evs if e["type"] == "HKMA_RATE"] == ["2026-10-22"]


def test_hk_desk_shows_canonical_us_cpi_dates():
    strip = hk.high_impact_strip(asof=date(2026, 10, 13), horizon_days=14)
    assert any(
        e["type"] == "US_CPI" and e["date"] == "2026-10-14" for e in strip
    )
    evs = hk.hk_macro_events(asof=date(2026, 11, 1), horizon_days=20)
    cpi = [e["date"] for e in evs if e["type"] == "US_CPI"]
    assert "2026-11-10" in cpi
    assert "2026-11-12" not in cpi


def test_hk_desk_has_no_literal_us_mirrors():
    assert "US_CPI" not in hk._HK_SCHED_2026
    assert not hasattr(hk, "_FOMC_2026")
    assert not hasattr(hk, "_first_friday")
    assert hk._canonical_calendar is ec
