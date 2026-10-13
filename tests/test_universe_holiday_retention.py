"""Synthetic inner universe persistence paths bypassing the base-runner summary."""
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from collectors import canada_universe as ca, china_universe as cn, hk_universe as hk
from lib import market_session, store


@pytest.fixture
def previous():
    return pd.DataFrame({"A": [100.0, 101.0, 102.0], "B": [200.0, 201.0, 202.0]},
                        index=pd.to_datetime(["2026-09-28", "2026-09-29", "2026-09-30"]))


def test_cn_stale_adjusted_column_retains_its_entire_old_basis(previous):
    stale = previous.iloc[:-1] * 0.5
    result = cn._overwrite_overlap(stale, previous)
    pd.testing.assert_frame_equal(result, previous)


def test_cn_stale_column_in_current_frame_cannot_erase_its_latest_valid_bar(previous):
    fresh = previous.copy()
    fresh["A"] *= 0.5
    fresh.loc[fresh.index[-1], "A"] = float("nan")
    result = cn._overwrite_overlap(fresh, previous)
    pd.testing.assert_series_equal(result["A"], previous["A"])
    pd.testing.assert_series_equal(result["B"], previous["B"])


@pytest.mark.parametrize("module,cls", [(cn, cn.ChinaUniverseAdapter), (ca, ca.CanadaUniverseAdapter)])
def test_stale_adjustment_is_not_sent_to_seam_repair(module, cls, previous, monkeypatch):
    adapter = cls.__new__(cls)
    stale = previous.iloc[:-1] * 0.5
    def forbidden(*args, **kwargs):
        raise AssertionError("rejected stale basis was sent for merging/repair")
    monkeypatch.setattr(module, "repair_seams", forbidden)
    result = adapter._merge_refreshed(stale, previous)
    pd.testing.assert_frame_equal(result, previous)


@pytest.mark.parametrize("module,cls,market,holiday", [
    (cn, cn.ChinaUniverseAdapter, "CN", "2026-10-07"),
    (ca, ca.CanadaUniverseAdapter, "CA", "2026-10-12"),
])
def test_download_closes_filters_only_non_session_provider_rows(
    module, cls, market, holiday, monkeypatch,
):
    adapter = cls.__new__(cls)
    adapter.ycfg = {"batch_size": 10, "retries": 1, "backoff_base_s": 0}
    adapter._latest_volumes = {}
    frame = pd.DataFrame({("Close", "A"): [100.0, 999.0],
                          ("Volume", "A"): [100.0, 999.0]},
                         index=pd.to_datetime(["2026-09-30", holiday]))
    monkeypatch.setattr(module.yf, "download", lambda *args, **kwargs: frame)
    monkeypatch.setattr(module.time, "sleep", lambda *args: None)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 13))
    result = adapter._download_closes(["A"], "1mo")
    assert result.index.tolist() == [pd.Timestamp("2026-09-30")]
    if market == "CA":
        assert adapter._latest_volumes["A"] == 100.0


def test_hk_inner_store_receives_only_actual_session_rows(tmp_path, monkeypatch):
    adapter = hk.HkUniverseAdapter.__new__(hk.HkUniverseAdapter)
    adapter.ycfg = {"batch_size": 50, "sleep_s": 0}
    monkeypatch.setattr(hk.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(hk, "_fetch_hsci_universe", lambda **kwargs: [{"ticker": "0700.HK"}])
    monkeypatch.setattr(hk, "_save_universe", lambda *args: None)
    monkeypatch.setattr(hk, "_ext_tickers", lambda *args: ["0700.HK"])
    monkeypatch.setattr(hk, "_load_checkpoint", lambda: {})
    monkeypatch.setattr(hk, "_save_checkpoint", lambda *args: None)
    monkeypatch.setattr(hk.time, "sleep", lambda *args: None)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    frame = pd.DataFrame({"close": [10.0, 999.0]}, index=pd.to_datetime(["2026-09-30", "2026-10-01"]))
    monkeypatch.setattr(hk, "fetch_ohlc", lambda *args: {"0700.HK": frame})
    writes = []
    monkeypatch.setattr(store, "upsert", lambda group, name, df, **kwargs: writes.append(df.copy()))
    # Full-history path avoids writing the adapter checkpoint/meta audit fixtures.
    monkeypatch.setattr(hk, "_checkpoint_path", lambda: tmp_path / "checkpoint.json")
    adapter.fetch(full_history=True)
    assert len(writes) == 1
    assert writes[0].index.tolist() == [pd.Timestamp("2026-09-30")]


def test_shared_filter_unknown_year_does_not_invent_a_holiday(monkeypatch):
    from lib.market_observations import filter_session_observations

    now = datetime(2027, 2, 10, 10, tzinfo=timezone.utc)
    # CN 2027 is unpublished; legacy LNY arithmetic may not delete provider observations.
    frame = pd.DataFrame({"close": [10, 11, 12]}, index=pd.to_datetime([
        "2027-02-08", "2027-02-06", "2027-02-11"]))
    result = filter_session_observations(frame, "CN", now=now)
    assert result.index.tolist() == [pd.Timestamp("2027-02-08")]



@pytest.mark.parametrize("cls", [cn.ChinaUniverseAdapter, ca.CanadaUniverseAdapter])
def test_older_full_repull_during_seam_repair_retains_whole_last_good_column(cls):
    index = pd.bdate_range("2025-01-06", periods=80)
    old = pd.DataFrame({"A": [100.0 + i for i in range(80)]}, index=index)
    fresh = old.iloc[-20:] * 0.1  # genuine adjustment requires a coherent full re-pull
    stale_repull = old.iloc[:-1] * 0.1
    adapter = cls.__new__(cls)
    calls = []
    def download(*args):
        calls.append(args)
        return stale_repull
    adapter._download_closes = download
    result = adapter._merge_refreshed(fresh, old)
    assert len(calls) == 1
    pd.testing.assert_frame_equal(result, old)



@pytest.mark.parametrize("cls", [cn.ChinaUniverseAdapter, ca.CanadaUniverseAdapter])
def test_full_repull_exception_retains_whole_last_good_column(cls):
    index = pd.bdate_range("2025-01-06", periods=80)
    old = pd.DataFrame({"A": [100.0 + i for i in range(80)]}, index=index)
    fresh = old.iloc[-20:] * 0.1
    adapter = cls.__new__(cls)
    calls = []

    def failed_download(*args):
        calls.append(args)
        raise RuntimeError("no valid closes downloaded")

    adapter._download_closes = failed_download
    result = adapter._merge_refreshed(fresh, old)
    assert len(calls) == 1
    pd.testing.assert_frame_equal(result, old)



def test_hk_real_unverified_historical_session_survives_inner_full_rebase(tmp_path, monkeypatch):
    # HKEX CT/038/20: 2021-12-28 traded. Legacy fallback invents a closure.
    adapter = hk.HkUniverseAdapter.__new__(hk.HkUniverseAdapter)
    adapter.ycfg = {"batch_size": 50, "sleep_s": 0}
    monkeypatch.setattr(hk.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(hk, "_fetch_hsci_universe", lambda **kwargs: [{"ticker": "0700.HK"}])
    monkeypatch.setattr(hk, "_save_universe", lambda *args: None)
    monkeypatch.setattr(hk, "_ext_tickers", lambda *args: ["0700.HK"])
    monkeypatch.setattr(hk, "_load_checkpoint", lambda: {})
    monkeypatch.setattr(hk, "_save_checkpoint", lambda *args: None)
    monkeypatch.setattr(hk.time, "sleep", lambda *args: None)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    old = pd.DataFrame({"close": [10.0, 100.0]},
                       index=pd.to_datetime(["2021-12-28", "2026-09-30"]))
    store.upsert(adapter.group, "0700.HK", old, overwrite_overlap=True)
    incoming = pd.DataFrame({"close": [9.0, 9.5, 95.0]},
                            index=pd.to_datetime(["2021-12-24", "2021-12-28", "2026-09-30"]))
    monkeypatch.setattr(hk, "fetch_ohlc", lambda *args: {"0700.HK": incoming})
    adapter.fetch(full_history=True)
    retained = store.read(adapter.group, "0700.HK")
    pd.testing.assert_frame_equal(retained, incoming)
    assert retained.loc[pd.Timestamp("2021-12-28"), "close"] == 9.5


def test_unverified_historical_weekdays_are_provider_observations():
    from lib.market_observations import filter_session_observations

    frame = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0]}, index=pd.to_datetime([
        "2021-12-28", "2021-12-25", "2026-10-01", "2026-10-09"]))
    result = filter_session_observations(
        frame, "HK", now=datetime(2026, 10, 7, 10, tzinfo=timezone.utc))
    assert result.index.tolist() == [pd.Timestamp("2021-12-28")]
