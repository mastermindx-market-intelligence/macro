"""Earnings-window facts (P17.T9): only nonnegative whole day counts render.

Synthetic dict contexts only; exercises the three pure earnings consumers
(``snapshot_state``, ``_earnings_section``, ``_events_block``). No files, network, or portfolio fixtures.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from engine.portfolio_brief import _earnings_section, _events_block
from engine.portfolio_changes import (
    EARNINGS_WINDOW_DAYS,
    diff_snapshots,
    snapshot_state,
)


def _ctx(**earnings_by_ticker: dict) -> dict:
    """Minimal ctx: only the earnings blocks the pure consumers read."""
    return {"tickers": {t: {"earnings": e}
                        for t, e in earnings_by_ticker.items()}}


def test_window_stays_ten_days():
    assert EARNINGS_WINDOW_DAYS == 10








# --- invalid days omitted by all three consumers ---------------------------


@pytest.mark.parametrize("days", [-1, 10.9, True, math.inf, math.nan, None, "soon"])
def test_invalid_days_omitted_by_all_three_consumers(days):
    ctx = _ctx(AAA={"next": "2030-03-01", "days_to": days})

    rec = snapshot_state(ctx, ["AAA"])["names"]["AAA"]
    assert "earnings_next" not in rec
    assert "earnings_soon" not in rec

    assert _earnings_section(ctx, ["AAA"]) is None
    assert _events_block(ctx, ["AAA"]) == {}


# --- 0/10 boundaries stay inside -------------------------------------------


def test_zero_and_ten_days_stay_inside_the_window():
    ctx = _ctx(XXX={"next": "2030-03-11", "days_to": 10},
               YYY={"next": "2030-03-01", "days_to": 0})

    names = snapshot_state(ctx, ["XXX", "YYY"])["names"]
    assert names["XXX"]["earnings_soon"] is True
    assert names["YYY"]["earnings_soon"] is True

    section = _earnings_section(ctx, ["XXX", "YYY"])
    assert section["lines"][0] == {
        "en": "2 names report inside 10 days — YYY first "
              "(2030-03-01, in 0 days).",
        "zh": "有 2 只个股将在 10 天内公布财报 — YYY 最早（2030-03-01，0 天后）。",
    }
    assert section["lines"][1] == {
        "en": "All: YYY (2030-03-01), XXX (2030-03-11).",
        "zh": "全部：YYY（2030-03-01）、XXX（2030-03-11）。",
    }
    assert _events_block(ctx, ["XXX", "YYY"]) == {"earnings_10d": [
        {"ticker": "YYY", "date": "2030-03-01", "days_to": 0},
        {"ticker": "XXX", "date": "2030-03-11", "days_to": 10},
    ]}


def test_one_day_prose_keeps_singular_and_no_all_line():
    ctx = _ctx(BBB={"next": "2030-03-02", "days_to": 1})
    section = _earnings_section(ctx, ["BBB"])
    assert section["lines"][0]["en"] == (
        "1 name reports inside 10 days — BBB first (2030-03-02, in 1 day).")
    assert section["lines"][0]["zh"] == (
        "有 1 只个股将在 10 天内公布财报 — BBB 最早（2030-03-02，1 天后）。")
    assert len(section["lines"]) == 1


def test_equal_days_sort_by_ticker():
    ctx = _ctx(ZZZ={"next": "2030-03-02", "days_to": 5},
               MMM={"next": "2030-03-02", "days_to": 5})
    section = _earnings_section(ctx, ["ZZZ", "MMM"])
    assert section["lines"][1] == {
        "en": "All: MMM (2030-03-02), ZZZ (2030-03-02).",
        "zh": "全部：MMM（2030-03-02）、ZZZ（2030-03-02）。",
    }


# --- 11 is known outside ----------------------------------------------------


def test_eleven_days_is_known_outside_everywhere():
    ctx = _ctx(CCC={"next": "2030-03-11", "days_to": 11},
               DDD={"next": "2030-03-01", "days_to": 0},
               EEE={"next": "2030-03-03", "days_to": 2})

    names = snapshot_state(ctx, ["CCC", "DDD", "EEE"])["names"]
    assert names["CCC"] == {"earnings_next": "2030-03-11", "earnings_soon": False}

    section = _earnings_section(ctx, ["CCC", "DDD", "EEE"])
    en = "\n".join(line["en"] for line in section["lines"])
    zh = "\n".join(line["zh"] for line in section["lines"])
    assert "CCC" not in en
    assert "CCC" not in zh

    assert _events_block(ctx, ["CCC", "DDD", "EEE"]) == {"earnings_10d": [
        {"ticker": "DDD", "date": "2030-03-01", "days_to": 0},
        {"ticker": "EEE", "date": "2030-03-03", "days_to": 2},
    ]}

    outside_only = _ctx(CCC={"next": "2030-03-11", "days_to": 11})
    assert _earnings_section(outside_only, ["CCC"]) is None
    assert _events_block(outside_only, ["CCC"]) == {}


# --- representation parity --------------------------------------------------


@pytest.mark.parametrize("days_repr", [3, 3.0, "3", " 3 "])
def test_representations_render_identically(days_repr):
    ctx = _ctx(FFF={"next": "2030-03-04", "days_to": days_repr})

    names = snapshot_state(ctx, ["FFF"])["names"]
    assert names["FFF"] == {"earnings_next": "2030-03-04", "earnings_soon": True}

    section = _earnings_section(ctx, ["FFF"])
    assert "(2030-03-04, in 3 days)." in section["lines"][0]["en"]
    assert _events_block(ctx, ["FFF"]) == {"earnings_10d": [
        {"ticker": "FFF", "date": "2030-03-04", "days_to": 3},
    ]}


# --- no invented dates ------------------------------------------------------


@pytest.mark.parametrize("earn", [
    {"days_to": 3},
    {"next": None, "days_to": 3},
    {},
])
def test_missing_next_date_is_omitted_not_invented(earn):
    ctx = _ctx(GGG=earn)
    rec = snapshot_state(ctx, ["GGG"])["names"]["GGG"]
    assert "earnings_next" not in rec
    assert "earnings_soon" not in rec
    assert _earnings_section(ctx, ["GGG"]) is None
    assert _events_block(ctx, ["GGG"]) == {}


def test_dates_render_verbatim_at_day_precision():
    # Snapshot and events truncate the supplied `next` to day precision; the
    # prose line keeps the desk's verbatim string. Nothing is invented.
    ctx = _ctx(HHH={"next": "2030-03-15T09:00", "days_to": 2})
    assert (snapshot_state(ctx, ["HHH"])["names"]["HHH"]["earnings_next"]
            == "2030-03-15")
    assert _events_block(ctx, ["HHH"])["earnings_10d"][0]["date"] == "2030-03-15"
    section = _earnings_section(ctx, ["HHH"])
    assert "HHH first (2030-03-15T09:00, in 2 days)." in section["lines"][0]["en"]


@pytest.mark.parametrize("unknown", [None, -1, 10.9, True, math.inf, math.nan, "soon"])
def test_unknown_clock_does_not_claim_earnings_left_the_window(unknown):
    previous = snapshot_state(_ctx(AAA={"next": "2030-03-01", "days_to": 5}), ["AAA"])
    current = snapshot_state(_ctx(AAA={"next": "2030-03-01", "days_to": unknown}), ["AAA"])
    assert diff_snapshots(previous, current) == []


def test_known_outside_clock_still_reports_leaving_the_window():
    previous = snapshot_state(_ctx(AAA={"next": "2030-03-01", "days_to": 5}), ["AAA"])
    current = snapshot_state(_ctx(AAA={"next": "2030-03-01", "days_to": 11}), ["AAA"])
    changes = diff_snapshots(previous, current)
    assert len(changes) == 1
    assert changes[0]["kind"] == "earnings_passed"
    assert "no longer inside" in changes[0]["en"]
    assert changes[0]["zh"]
