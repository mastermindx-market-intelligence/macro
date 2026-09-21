"""Current-observation coverage must survive the real China breadth producer.

Only network I/O is replaced. The inherited breadth calculation and parquet
writes are real. Historical prices must not qualify a missing latest quote.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.china_breadth import ChinaBreadthAdapter


def _fixture(tmp_path, monkeypatch):
    adapter = ChinaBreadthAdapter.__new__(ChinaBreadthAdapter)
    names = [f"{600000 + i}.SS" for i in range(40)]
    adapter.const_cfg = {"test_sector": names}
    adapter.cfg = {"ma_windows": [3, 5], "nhnl_window": 5,
                   "min_coverage": 0.6, "lookback_days_live": 800}
    adapter.cache_path = tmp_path / "china_breadth" / "_closes_cache.parquet"
    dates = pd.bdate_range(end="2026-09-18", periods=30)
    frame = pd.DataFrame(np.arange(30, dtype=float)[:, None] +
                         np.arange(40, dtype=float)[None, :] + 100,
                         index=dates, columns=names)
    monkeypatch.setattr(adapter, "_download_closes", lambda *_: frame.copy())
    return adapter, frame


@pytest.mark.parametrize("full_history", [False, True])
def test_history_does_not_qualify_missing_latest_quotes(tmp_path, monkeypatch, full_history):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    frame.iloc[-1, 16:] = np.nan  # 100% history, only 40% current coverage
    with pytest.raises(RuntimeError, match="coverage"):
        adapter.fetch(full_history=full_history)
    assert not adapter.cache_path.parent.exists()


def test_dropped_latest_breadth_row_cannot_publish_older_success(tmp_path, monkeypatch):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    frame.iloc[-1, 28:] = np.nan  # 70% clears config; inherited 80% guard drops it
    with pytest.raises(RuntimeError, match="latest.*coverage|coverage.*latest"):
        adapter.fetch(full_history=True)
    assert not adapter.cache_path.parent.exists()


@pytest.mark.parametrize("full_history", [False, True])
def test_complete_batch_preserves_real_breadth_math(tmp_path, monkeypatch, full_history):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    expected = adapter.compute(frame)
    actual = adapter.fetch(full_history=full_history)["breadth"]
    pd.testing.assert_frame_equal(actual, expected)
    assert actual.index[-1] == frame.index[-1]
    assert actual.iloc[-1]["n_members"] == 40
    assert adapter.cache_path.exists() is (not full_history)
    assert (adapter.cache_path.parent / "constituents.parquet").exists()


def test_unrequested_symbols_cannot_inflate_coverage(tmp_path, monkeypatch):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    frame.iloc[-1, 16:] = np.nan
    for i in range(30):
        frame[f"unexpected-{i}"] = 120.0
    with pytest.raises(RuntimeError, match="coverage"):
        adapter.fetch(full_history=True)
    assert not adapter.cache_path.parent.exists()


def test_accepted_partial_universe_does_not_include_unrequested_names(tmp_path, monkeypatch):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    frame["unexpected"] = 1.0
    actual = adapter.fetch(full_history=True)["breadth"]
    assert actual.iloc[-1]["n_members"] == 40
    expected = adapter.compute(frame.drop(columns="unexpected"))
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("bad_value", [np.inf, -np.inf, 0.0, -1.0])
def test_invalid_latest_prices_do_not_count_as_coverage(tmp_path, monkeypatch, bad_value):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    frame.iloc[-1, 16:] = bad_value
    with pytest.raises(RuntimeError, match="coverage"):
        adapter.fetch(full_history=True)
    assert not adapter.cache_path.parent.exists()


@pytest.mark.parametrize("full_history", [False, True])
def test_empty_download_fails_before_any_publication(tmp_path, monkeypatch, full_history):
    adapter, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(adapter, "_download_closes", lambda *_: pd.DataFrame())
    with pytest.raises(RuntimeError, match="coverage"):
        adapter.fetch(full_history=full_history)
    assert not adapter.cache_path.parent.exists()


def test_latest_quotes_alone_do_not_prove_moving_average_coverage(tmp_path, monkeypatch):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    frame.iloc[:-1, 10:] = np.nan  # 40 latest prices, just 10 usable moving averages
    with pytest.raises(RuntimeError, match="coverage"):
        adapter.fetch(full_history=True)
    assert not adapter.cache_path.parent.exists()


def test_bad_batch_keeps_existing_cache_and_constituents(tmp_path, monkeypatch):
    adapter, frame = _fixture(tmp_path, monkeypatch)
    adapter.cache_path.parent.mkdir()
    frame.iloc[:-1].to_parquet(adapter.cache_path)
    members = adapter.cache_path.parent / "constituents.parquet"
    adapter.constituents().to_parquet(members)
    cache_before, members_before = adapter.cache_path.read_bytes(), members.read_bytes()
    frame.iloc[-1, 16:] = np.nan
    with pytest.raises(RuntimeError, match="coverage"):
        adapter.fetch()
    assert adapter.cache_path.read_bytes() == cache_before
    assert members.read_bytes() == members_before


def test_collector_runner_reports_failure_and_preserves_store(tmp_path, monkeypatch):
    from collectors.base import run_adapter
    from lib import config
    adapter, frame = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    adapter.cache_path.parent.mkdir()
    target = adapter.cache_path.parent / "breadth.parquet"
    adapter.compute(frame.iloc[:-1]).to_parquet(target)
    before = target.read_bytes()
    frame.iloc[-1, 16:] = np.nan
    result = run_adapter(adapter, full_history=True)
    assert result.source == "china_breadth"
    assert result.status == "failed"
    assert "coverage" in result.error
    assert result.rows == 0
    assert target.read_bytes() == before


def test_collector_runner_publishes_valid_snapshot_for_existing_reader(tmp_path, monkeypatch):
    from collectors.base import run_adapter
    from collectors.breadth import breadth_summary
    from lib import config
    adapter, frame = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    result = run_adapter(adapter, full_history=True, stale_after_days=10000)
    assert result.status == "ok"
    assert result.last_date == "2026-09-18"
    stored = pd.read_parquet(adapter.cache_path.parent / "breadth.parquet")
    summary = breadth_summary(stored, full=False)
    assert (summary["asof"], summary["n_members"], summary["full"]) == ("2026-09-18", 40, False)
