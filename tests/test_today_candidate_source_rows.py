"""Session-scoped expansion must preserve the native reader's byte boundary."""
from datetime import date, datetime, timezone
from hashlib import sha256

import pandas as pd
import pytest

from engine import us_context_vector as context_owner
from engine.us_candidate_episode import canonical_json


SESSION = "2026-11-05"


def _part(root, name, frame):
    path = root / "data/us_prophet_rank/candidates" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


@pytest.mark.parametrize("values", [
    [SESSION, "2026-11-04", None, "2026-11-05T00:00:00", " 2026-11-05"],
    pd.Series([SESSION, pd.NA, "2026-11-04"], dtype="string"),
    [date(2026, 11, 5), date(2026, 11, 4), None],
    [datetime(2026, 11, 5), datetime(2026, 11, 4), None],
    [datetime(2026, 11, 5, tzinfo=timezone.utc), None],
    pd.to_datetime([SESSION, "2026-11-04", None]),
    [20261105, 20261104, None],
    [],
])
def test_session_filter_equals_original_canonical_predicate(tmp_path, values):
    frame = pd.DataFrame({"stamp_date": values})
    frame["ticker"] = [f"T{i}" for i in range(len(frame))]
    frame["nested"] = [{"values": [1.0, None]} for _ in range(len(frame))]
    frame["today_selection_row_receipt"] = None
    path = _part(tmp_path, "1999-01.parquet", frame)
    original, receipts = context_owner.read_today_candidate_source_rows(tmp_path)
    selected, selected_receipts = context_owner.read_today_candidate_source_rows(
        tmp_path, market_session=SESSION)
    expected = [row for row in original if row.get("stamp_date") == SESSION]
    assert canonical_json(selected) == canonical_json(expected)
    assert selected_receipts == receipts == [
        {"path": str(path), "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest()}]


def test_all_parts_and_matching_duplicates_keep_order_and_receipts(tmp_path):
    # Filenames and duplicate identities cannot become a pruning/selection rule.
    _part(tmp_path, "1999-01.parquet", pd.DataFrame([
        {"stamp_date": SESSION, "ticker": "ALFA", "order": 1},
        {"stamp_date": "2026-10-01", "ticker": "OLD", "order": 2}]))
    _part(tmp_path, "2026-11.parquet", pd.DataFrame([
        {"stamp_date": SESSION, "ticker": "ALFA", "order": 3},
        {"stamp_date": SESSION, "ticker": "ALFA", "order": 4}]))
    _part(tmp_path, "2099-01.parquet", pd.DataFrame([{"ticker": "NO_SESSION"}]))
    original, receipts = context_owner.read_today_candidate_source_rows(tmp_path)
    selected, selected_receipts = context_owner.read_today_candidate_source_rows(
        tmp_path, market_session=SESSION)
    assert selected == [row for row in original if row.get("stamp_date") == SESSION]
    assert [row["order"] for row in selected] == [1, 3, 4]
    assert selected_receipts == receipts
    assert len(receipts) == 3


def test_historical_wide_rows_are_not_expanded(tmp_path, monkeypatch):
    frame = pd.DataFrame({f"field_{i}": list(range(100)) for i in range(220)})
    frame["stamp_date"] = ["2026-10-01"] * 98 + [SESSION] * 2
    frame["ticker"] = "ALFA"
    frame["nested"] = [{"values": [1.0, None]} for _ in range(100)]
    _part(tmp_path, "2026-11.parquet", frame)
    original_to_dict = pd.DataFrame.to_dict
    expansions = []

    def observe_expansion(self, orient="dict", *args, **kwargs):
        if orient == "records":
            expansions.append((len(self), len(self.columns)))
        return original_to_dict(self, orient, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_dict", observe_expansion)
    selected, receipts = context_owner.read_today_candidate_source_rows(
        tmp_path, market_session=SESSION)
    assert expansions == [(2, 223)]
    assert [row["field_0"] for row in selected] == [98, 99]
    assert len(receipts) == 1


def test_unreadable_nonmatching_part_still_refuses_the_read(tmp_path):
    _part(tmp_path, "2026-11.parquet", pd.DataFrame([
        {"stamp_date": SESSION, "ticker": "ALFA"}]))
    (tmp_path / "data/us_prophet_rank/candidates/1999-01.parquet").write_bytes(b"corrupt")
    with pytest.raises((OSError, ValueError)):
        context_owner.read_today_candidate_source_rows(tmp_path, market_session=SESSION)


def test_missing_source_parts_still_refuse_the_read(tmp_path):
    with pytest.raises(ValueError, match="candidate source parts are unavailable"):
        context_owner.read_today_candidate_source_rows(tmp_path, market_session=SESSION)
