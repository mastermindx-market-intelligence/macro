"""One date key for the settled index-close store's held vs fetched sessions.

The store's contract is ``trade_date`` as YYYY-MM-DD strings, but a store
written by any path that lets pandas keep its own stamps may hold Timestamps,
``datetime.date`` values or ``"YYYY-MM-DD 00:00:00"`` strings. These tests pin
that ``first_disagreement()`` and ``merge()`` compare every held session with
the vendor print on that one normalized key, and that a trade_date which does
not name an ISO day is refused, never written. ``refresh()`` reads the held
store's last session — the fetch-overlap start — through that same key, so a
typed store overlaps correctly and a store that names no day takes the
empty-store path. Synthetic frames only. No network and no token. Closes are
made-up levels.
"""
from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from collectors import tushare_index_daily as tid

HELD_FIRST_SEEN = "2026-10-11T20:00:00+00:00"
FETCH_FIRST_SEEN = "2026-10-12T02:00:00+00:00"


def _held(rows):
    return pd.DataFrame(
        [{"ticker": tid.TICKER, "trade_date": d, "close": c, "first_seen": HELD_FIRST_SEEN}
         for d, c in rows])


def _fetched(rows):
    return pd.DataFrame({"trade_date": [d for d, _ in rows],
                         "close": [c for _, c in rows]})


def _as_timestamp(frame):
    out = frame.copy()
    out["trade_date"] = [pd.Timestamp(d) for d in frame["trade_date"]]
    return out


def _as_date(frame):
    out = frame.copy()
    out["trade_date"] = [date.fromisoformat(d) for d in frame["trade_date"]]
    return out


def _as_long_stamp(frame):
    out = frame.copy()
    out["trade_date"] = [d + " 00:00:00" for d in frame["trade_date"]]
    return out


HELD_SHAPES = {
    "date": _as_date,
    "long_stamp": _as_long_stamp,
    "timestamp": _as_timestamp,
}


@pytest.mark.parametrize("shape", sorted(HELD_SHAPES))
def test_a_revision_of_a_typed_held_session_is_refused(shape):
    held = HELD_SHAPES[shape](_held([("2024-06-03", 3000.0), ("2024-06-04", 3010.0)]))
    fetched = _fetched([("2024-06-03", 9999.0), ("2024-06-05", 3020.0)])
    assert tid.first_disagreement(held, fetched) == ("2024-06-03", 3000.0, 9999.0)
    assert tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN) is None


@pytest.mark.parametrize("shape", sorted(HELD_SHAPES))
def test_agreeing_typed_sessions_merge_with_a_new_session_sorted(shape):
    held = HELD_SHAPES[shape](_held([("2024-06-03", 3000.0), ("2024-06-04", 3010.0)]))
    # The new session arrives before the agreeing overlap, and the merge still
    # sorts: a mixed str/Typed frame used to raise inside sort_values.
    fetched = _fetched([("2024-06-05", 3020.0), ("2024-06-04", 3010.0)])
    out = tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN)
    assert out is not None
    assert out["trade_date"].tolist() == ["2024-06-03", "2024-06-04", "2024-06-05"]
    assert out["close"].tolist() == [3000.0, 3010.0, 3020.0]
    assert all(isinstance(d, str) and len(d) == 10 for d in out["trade_date"])
    # Held rows pass through with their own first sighting; only the new
    # session carries the merge's stamp.
    assert out["first_seen"].tolist() == [
        HELD_FIRST_SEEN, HELD_FIRST_SEEN, FETCH_FIRST_SEEN,
    ]
    assert set(out["ticker"]) == {tid.TICKER}


@pytest.mark.parametrize("bad", ["2024-13-40", "", None])
def test_an_unparseable_fetched_day_refuses_the_whole_merge(bad):
    held = _held([("2024-06-03", 3000.0)])
    fetched = _fetched([("2024-06-03", 3000.0), (bad, 3010.0)])
    assert tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN) is None


def test_an_unparseable_held_day_refuses_too():
    held = _held([("2024-06-03", 3000.0), (None, 3010.0)])
    fetched = _fetched([("2024-06-05", 3020.0)])
    assert tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN) is None


def test_str_held_and_str_fetched_still_disagree_on_a_revised_close():
    held = _held([("2024-06-03", 3000.0), ("2024-06-04", 3010.0)])
    fetched = _fetched([("2024-06-04", 3011.0)])
    assert tid.first_disagreement(held, fetched) == ("2024-06-04", 3010.0, 3011.0)
    assert tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN) is None


def test_str_held_and_str_fetched_still_merge_new_sessions_in_order():
    held = _held([("2024-06-03", 3000.0)])
    fetched = _fetched([
        ("2024-06-05", 3020.0), ("2024-06-03", 3000.0), ("2024-06-04", 3010.0),
    ])
    out = tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN)
    assert out["trade_date"].tolist() == ["2024-06-03", "2024-06-04", "2024-06-05"]
    assert out["close"].tolist() == [3000.0, 3010.0, 3020.0]


def test_a_vendor_row_before_the_anchor_is_still_not_merged():
    assert tid.ANCHOR == date(2023, 1, 1)
    held = _held([("2023-01-03", 3100.0)])
    fetched = _fetched([("2022-12-30", 3000.0), ("2023-01-04", 3110.0)])
    out = tid.merge(held, fetched, first_seen=FETCH_FIRST_SEEN)
    assert out["trade_date"].tolist() == ["2023-01-03", "2023-01-04"]
    assert out["close"].tolist() == [3100.0, 3110.0]


#
# refresh() reads the held store's last session through that same key.
#

# Two held sessions whose later day is 2026-10-09, so the overlap starts
# 30 sessions back at 2026-09-09 — past the anchor either way.
HELD_DAYS = ["2026-10-08", "2026-10-09"]
OVERLAP_START = "20260909"
NEW_SESSION = [("20261012", 3310.0)]


@pytest.fixture
def store(tmp_path, monkeypatch):
    out = tmp_path / "tushare" / "index_daily.parquet"
    monkeypatch.setattr(tid, "OUT", out)
    monkeypatch.setattr(tid.tc, "enabled", lambda: True)
    return out


def _serve(monkeypatch, rows):
    calls = []

    def query(api_name, fields="", **params):
        calls.append((api_name, fields, params))
        return pd.DataFrame([{"ts_code": tid.TICKER, "trade_date": d, "close": c}
                             for d, c in rows])

    monkeypatch.setattr(tid.tc, "query", query)
    return calls


def _typed_days(shape):
    """The same two held sessions as the store would keep them."""
    if shape == "iso_str":
        return HELD_DAYS
    if shape == "compact_str":
        return [d.replace("-", "") for d in HELD_DAYS]
    if shape == "date":
        return [date.fromisoformat(d) for d in HELD_DAYS]
    if shape == "datetime":
        return [datetime.fromisoformat(d) for d in HELD_DAYS]
    if shape == "timestamp":
        return [pd.Timestamp(d) for d in HELD_DAYS]
    return [np.datetime64(d) for d in HELD_DAYS]


STORED_SHAPES = ["compact_str", "date", "datetime", "iso_str",
                 "np_datetime64", "timestamp"]


@pytest.mark.parametrize("shape", STORED_SHAPES)
def test_refresh_overlaps_from_the_held_session_whatever_type_it_stored(
        shape, store, monkeypatch):
    """A store that kept its own stamps still reads its true last session."""
    held = _held(list(zip(_typed_days(shape), [3000.0, 3010.0])))
    monkeypatch.setattr(tid, "_held", lambda: held)
    calls = _serve(monkeypatch, NEW_SESSION)
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert calls[0][2]["start_date"] == OVERLAP_START


@pytest.mark.parametrize("shape", STORED_SHAPES)
def test_refresh_overlaps_from_a_stored_frame_of_any_type(shape, store, monkeypatch):
    """The same through a real store file: whatever the parquet round-trip
    leaves on disk, the fetch still starts 30 sessions back."""
    held = _held(list(zip(_typed_days(shape), [3000.0, 3010.0])))
    store.parent.mkdir(parents=True, exist_ok=True)
    held.to_parquet(store, index=False)
    calls = _serve(monkeypatch, NEW_SESSION)
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert calls[0][2]["start_date"] == OVERLAP_START
    out = pd.read_parquet(store)
    # Held rows are written back on the one ISO key, whatever they stored as.
    assert out["trade_date"].tolist() == HELD_DAYS + ["2026-10-12"]


@pytest.mark.parametrize("bad", [pd.NaT, None, pd.NA, float("nan")])
def test_a_held_session_that_names_no_day_takes_the_empty_store_path(
        bad, store, monkeypatch):
    """NaT/None held days refuse to name an overlap start: the fetch falls
    back to the anchor, the same path an absent store takes, never raising."""
    held = pd.DataFrame([{"ticker": tid.TICKER, "trade_date": bad, "close": c,
                          "first_seen": HELD_FIRST_SEEN} for c in (3000.0, 3010.0)])
    monkeypatch.setattr(tid, "_held", lambda: held)
    calls = _serve(monkeypatch, NEW_SESSION)
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert calls[0][2]["start_date"] == "20230101"
    assert not store.exists()


@pytest.mark.parametrize("empty_case", ["missing", "empty_frame"])
def test_an_empty_store_still_fetches_from_the_anchor(empty_case, store, monkeypatch):
    if empty_case == "empty_frame":
        store.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=list(tid.COLUMNS)).to_parquet(store, index=False)
    calls = _serve(monkeypatch, NEW_SESSION)
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert calls[0][2]["start_date"] == "20230101"


def test_the_old_inline_held_max_reading_fails_on_a_timestamp_store(
        store, monkeypatch):
    """Teeth: the line this fix replaced is what a typed store broke."""
    held = _held([(pd.Timestamp(d), c)
                  for d, c in zip(HELD_DAYS, (3000.0, 3010.0))])
    monkeypatch.setattr(tid, "_held", lambda: held)

    def old_inline_key(day):
        return date.fromisoformat(str(day)).isoformat()

    monkeypatch.setattr(tid, "_session_key", old_inline_key)
    _serve(monkeypatch, NEW_SESSION)
    with pytest.raises(ValueError):
        tid.refresh(today=date(2026, 10, 12))
