import copy
from datetime import datetime

import pytest

from scripts.boats_history_window import CONSTANTS, merge_session_window


def doc(session="2026-10-19", bars=None, letter="a", observed="2026-10-19T10:00:00Z"):
    rid = letter * 64
    rows = bars if bars is not None else [[int(datetime.fromisoformat(session + "T01:00:00+00:00").timestamp()), 10, 12, 9, 11, 123]]
    return {**CONSTANTS, "symbol": "AAPL", "receipts": [{"receipt_id": rid, "raw_sha256": "b" * 64,
        "observed_at_utc": observed, "request_path": f"/boats/AAPL/prices?resampleFreq=1min&startDate={session}&endDate={session}"}],
        "bars": rows, "bar_receipt_ids": [[rid] for _ in rows]}


def test_whole_revision_replaces_volume_and_does_not_mutate_inputs():
    old, new = doc(observed="2026-10-19T09:00:00Z"), doc(letter="c")
    new["bars"][0][-1] = 120
    before = copy.deepcopy((old, new))
    result = merge_session_window(old, new, "2026-10-19")
    assert result["bars"][0][-1] == 120
    assert result["bar_receipt_ids"] == [["c" * 64]]
    assert (old, new) == before


def test_empty_cancels_only_selected_window():
    old = doc(observed="2026-10-19T09:00:00Z")
    earlier = doc("2026-10-16", letter="d", observed="2026-10-16T10:00:00Z")
    old["bars"] = earlier["bars"] + old["bars"]
    old["bar_receipt_ids"] = earlier["bar_receipt_ids"] + old["bar_receipt_ids"]
    old["receipts"] += earlier["receipts"]
    result = merge_session_window(old, doc(bars=[], letter="c"), "2026-10-19")
    assert result["bars"] == earlier["bars"]
    assert {r["receipt_id"] for r in result["receipts"]} == {"c" * 64, "d" * 64}


def test_older_or_ambiguous_revision_is_refused():
    with pytest.raises(ValueError, match="older"):
        merge_session_window(doc(), doc(letter="c", observed="2026-10-19T09:00:00Z"), "2026-10-19")
    new = doc(letter="c"); new["bars"][0][-1] = 1
    with pytest.raises(ValueError, match="same-time"):
        merge_session_window(doc(), new, "2026-10-19")


def test_identical_receipt_is_idempotent():
    data = doc()
    assert merge_session_window(data, data, "2026-10-19") == data


@pytest.mark.parametrize("session,start,end", [("2026-03-09", "00", "08"), ("2026-11-02", "01", "09")])
def test_dst_window(session, start, end):
    epoch = lambda hour: int(datetime.fromisoformat(session + f"T{hour}:00:00+00:00").timestamp())
    d = doc(session, [[epoch(start), 1, 1, 1, 1, 0]], observed=session + "T12:00:00Z")
    assert merge_session_window(None, d, session)["bars"] == d["bars"]
    d["bars"][0][0] = epoch(end)
    with pytest.raises(ValueError, match="outside"):
        merge_session_window(None, d, session)


@pytest.mark.parametrize("kind", ["duplicate", "lineage", "future", "request", "volume", "boolean"])
def test_malformed_update_refused(kind):
    d = doc()
    if kind == "duplicate": d["bars"] *= 2; d["bar_receipt_ids"] *= 2
    elif kind == "lineage": d["bar_receipt_ids"] = [["f" * 64]]
    elif kind == "future": d["receipts"][0]["observed_at_utc"] = "2026-10-19T00:00:00Z"
    elif kind == "request": d["receipts"][0]["request_path"] += "&forceFill=true"
    elif kind == "volume": d["bars"][0][-1] = -1
    else: d["bars"][0][-1] = True
    with pytest.raises(ValueError): merge_session_window(None, d, "2026-10-19")
