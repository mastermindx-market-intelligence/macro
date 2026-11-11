"""FINRA daily short-volume: collector parse + engine signal."""
from __future__ import annotations

import pandas as pd
import pytest
import json
from datetime import date
from types import SimpleNamespace

import numpy as np

from collectors.finra_short_volume import _business_days, _parse
from engine.short_volume import load_panel, signal_map
from collectors import finra_short_volume as fsv
from collectors.base import run_adapter
from engine import short_volume as sv
from engine import stock_fundamentals as sf
from lib import config, store

SAMPLE = """Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
20240117|A|252768|9924|403203|B,Q,N
20240117|NVDA|13510815|125613|29647745|B,Q,N
20240117|ZERO|0|0|0|Q
Total Records: 3
"""


def test_parse_drops_header_footer_and_zero_total():
    df = _parse(SAMPLE)
    assert set(df["ticker"]) == {"A", "NVDA"}          # header + footer + ZERO row dropped
    assert {"date", "ticker", "short_vol", "total_vol", "short_ratio"} <= set(df.columns)
    nvda = df[df["ticker"] == "NVDA"].iloc[0]
    assert nvda["short_ratio"] == pytest.approx(13510815 / 29647745, abs=1e-4)
    assert df["date"].iloc[0] == pd.Timestamp("2024-01-17")


def test_parse_empty_on_garbage():
    assert _parse("nonsense\nno pipes here").empty


def _panel(rows):
    return pd.DataFrame(rows, columns=["date", "ticker", "short_vol", "total_vol", "short_ratio"])


def test_signal_map_volume_weighted_trend():
    # baseline (all 6) vw = 1200/6000 = .20; recent(3) vw = 900/3000 = .30
    rows = []
    for i, (sv, tv) in enumerate([(100, 1000)] * 3 + [(300, 1000)] * 3, start=1):
        rows.append((pd.Timestamp(f"2024-01-0{i}"), "AAA", sv, tv, round(sv / tv, 4)))
    sig = signal_map(_panel(rows), recent=3, baseline=20)
    assert "AAA" in sig
    s = sig["AAA"]
    assert s["ratio_recent"] == pytest.approx(0.30, abs=1e-4)
    assert s["ratio_baseline"] == pytest.approx(0.20, abs=1e-4)
    assert s["trend_pp"] == pytest.approx(10.0, abs=0.05)   # building short flow
    assert s["n_days"] == 6
    assert s["asof"] == "2024-01-06"


def test_signal_map_excludes_thin_history():
    rows = [(pd.Timestamp("2024-01-01"), "BBB", 1, 10, 0.1),
            (pd.Timestamp("2024-01-02"), "BBB", 1, 10, 0.1)]   # only 2 days < 3
    assert signal_map(_panel(rows)) == {}


@pytest.mark.parametrize("recent,baseline", [(0, 20), (5, 0)])
def test_empty_requested_window_preserves_no_signal(recent, baseline):
    assert signal_map(_paired_panel(), recent=recent, baseline=baseline) == {}


def test_signal_map_empty_inputs():
    assert signal_map(pd.DataFrame()) == {}
    assert signal_map(None) == {} or isinstance(signal_map(None), dict)  # no panel -> {}


def test_load_panel_roundtrip_and_missing(tmp_path):
    assert load_panel(tmp_path / "nope.parquet") is None
    p = tmp_path / "panel.parquet"
    _panel([(pd.Timestamp("2024-01-01"), "AAA", 5, 10, 0.5)]).to_parquet(p)
    got = load_panel(p)
    assert got is not None and list(got["ticker"]) == ["AAA"]


def test_business_days_are_weekdays_newest_first():
    days = _business_days(14)
    assert days == sorted(days, reverse=True)              # newest-first
    assert all(d.weekday() < 5 for d in days)              # no Sat/Sun
    assert len(days) <= 14


def _paired_panel(n=20, short=50.0, total=100.0):
    return pd.DataFrame({
        "date": pd.bdate_range("2026-10-01", periods=n),
        "ticker": ["AAA"] * n,
        "short_vol": [short] * n,
        "total_vol": [total] * n,
        "short_ratio": [round(short / total, 4) if total else np.nan] * n,
    })


@pytest.mark.parametrize("short,total,state", [
    (np.nan, 100.0, sv.UNAVAILABLE),
    (50.0, np.nan, sv.UNAVAILABLE),
    (np.nan, np.nan, sv.UNAVAILABLE),
    (float("inf"), 100.0, sv.PARSE_ERROR),
    (50.0, float("inf"), sv.PARSE_ERROR),
    (float("-inf"), 100.0, sv.PARSE_ERROR),
    (-1.0, 100.0, sv.PARSE_ERROR),
    (50.0, -1.0, sv.PARSE_ERROR),
    (101.0, 100.0, sv.PARSE_ERROR),
    (1.0, 0.0, sv.PARSE_ERROR),
    (0.0, 0.0, sv.UNAVAILABLE),
    (np.nan, float("inf"), sv.PARSE_ERROR),
    ("bad", 100.0, sv.PARSE_ERROR),
])
def test_bad_pair_withholds_only_dependent_measurements(short, total, state):
    panel = _paired_panel().astype({"short_vol": object, "total_vol": object})
    panel.loc[19, ["short_vol", "total_vol"]] = [short, total]
    sig = signal_map(panel)["AAA"]
    assert all(sig[k] is None for k in (
        "short_ratio", "ratio_recent", "ratio_baseline", "trend_pp", "ratio_z"))
    assert sv.ticker_state(sig) == state
    for scope, count in [("latest", 1), ("recent", 5), ("baseline", 20), ("history_z", 20)]:
        c = sig["coverage"][scope]
        assert c["reason"] == "paired_operands"
        assert c["n_rows"] == count
        assert c["n_invalid"] == int(state == sv.PARSE_ERROR)
        assert c["n_missing"] == int(state != sv.PARSE_ERROR)
    json.dumps(sig, allow_nan=False)


@pytest.mark.parametrize("column", ["short_vol", "total_vol"])
def test_reported_nan_skip_trends_are_withheld(column):
    panel = _paired_panel()
    panel.loc[16:19, column] = np.nan
    sig = signal_map(panel)["AAA"]
    assert sig["ratio_recent"] is None
    assert sig["ratio_baseline"] is None
    assert sig["trend_pp"] is None
    assert sig["coverage"]["recent"]["n_missing"] == 4
    assert sv.ticker_state(sig) == sv.UNAVAILABLE


@pytest.mark.parametrize("short,total", [(np.nan, 100.0), (0.0, 0.0)])
def test_no_pairs_is_no_observation_never_measured_zero(short, total):
    panel = _paired_panel()
    panel["short_vol"] = short
    panel["total_vol"] = total
    sig = signal_map(panel)["AAA"]
    assert sv.ticker_state(sig) == sv.NO_OBSERVATION
    assert sig["short_ratio"] is None
    assert sig["ratio_recent"] is None
    assert sig["coverage"]["recent"]["state"] == sv.NO_OBSERVATION


@pytest.mark.parametrize("short,total,state", [
    (0.0, 100.0, sv.OBSERVED_ZERO),
    (1.0, 100_000_000.0, sv.OBSERVED),
])
def test_zero_state_uses_unrounded_observation(short, total, state):
    sig = signal_map(_paired_panel(short=short, total=total))["AAA"]
    assert sig["ratio_recent"] == 0.0
    assert sv.ticker_state(sig) == state
    assert "coverage" not in sig


def test_old_invalid_pair_only_withholds_full_history_z():
    panel = _paired_panel(25)
    panel.loc[0, "short_vol"] = -1
    sig = signal_map(panel)["AAA"]
    assert {k: sig[k] for k in ("short_ratio", "ratio_recent", "ratio_baseline", "trend_pp")} == {
        "short_ratio": 0.5, "ratio_recent": 0.5, "ratio_baseline": 0.5, "trend_pp": 0.0}
    assert sig["ratio_z"] is None
    assert set(sig["coverage"]) == {"history_z"}
    assert sv.ticker_state(sig) == sv.PARSE_ERROR


def test_incomplete_windows_are_not_backfilled_from_older_rows():
    panel = _paired_panel(25)
    panel.loc[23, "short_vol"] = np.nan
    first = signal_map(panel)["AAA"]
    panel.loc[:4, "short_vol"] = 99.0
    panel.loc[:4, "short_ratio"] = 0.99
    second = signal_map(panel)["AAA"]
    assert first == second
    assert first["short_ratio"] == 0.5
    assert first["ratio_recent"] is None
    assert first["coverage"]["recent"]["n_rows"] == 5
    assert first["coverage"]["baseline"]["n_rows"] == 20


@pytest.mark.parametrize("value", [float("inf"), -0.1, 1.1, 0.6, "bad"])
def test_invalid_stored_ratio_does_not_poison_sound_paired_windows(value):
    panel = _paired_panel().astype({"short_ratio": object})
    panel.loc[19, "short_ratio"] = value
    sig = signal_map(panel)["AAA"]
    assert sig["short_ratio"] is None
    assert sig["ratio_z"] is None
    assert (sig["ratio_recent"], sig["ratio_baseline"], sig["trend_pp"]) == (0.5, 0.5, 0.0)
    assert set(sig["coverage"]) == {"latest", "history_z"}
    assert all(c["reason"] == "stored_ratio" for c in sig["coverage"].values())
    assert sv.ticker_state(sig) == sv.PARSE_ERROR


@pytest.mark.parametrize("mode", ["absent", "latest_missing", "interior_missing"])
def test_optional_ratio_legacy_semantics_are_preserved(mode):
    panel = _paired_panel()
    panel.loc[19, ["short_vol", "short_ratio"]] = [70.0, 0.7]
    if mode == "absent":
        panel = panel.drop(columns="short_ratio")
    elif mode == "latest_missing":
        panel.loc[19, "short_ratio"] = np.nan
    else:
        panel.loc[0, "short_ratio"] = np.nan
    sig = signal_map(panel)["AAA"]
    assert "coverage" not in sig
    if mode == "interior_missing":
        expected = round((0.7 - np.nanmean(panel.short_ratio)) / np.nanstd(panel.short_ratio), 2)
        assert sig["short_ratio"] == 0.7
        assert sig["ratio_z"] == expected
    else:
        assert sig["short_ratio"] == 0.54
        assert sig["ratio_z"] is None
        assert sv.ticker_state(sig) == sv.PARTIAL


def test_finite_large_pairs_do_not_overflow_into_nan():
    sig = signal_map(_paired_panel(short=5e307, total=1e308))["AAA"]
    assert sig["short_ratio"] == sig["ratio_recent"] == sig["ratio_baseline"] == 0.5
    assert sig["trend_pp"] == 0.0
    assert sig["ratio_z"] == 0.0
    json.dumps(sig, allow_nan=False)


def test_panel_boundary_retains_and_flags_bad_pair_without_changing_raw_cells(tmp_path):
    panel = _paired_panel()
    panel.loc[19, "short_vol"] = -1
    path = tmp_path / "panel.parquet"
    panel.to_parquet(path)
    got, state = sv.panel_state(path)
    assert state == sv.OBSERVED  # readable container; cell qualification is separate
    assert len(got) == len(panel)
    assert got.loc[19, "short_vol"] == -1
    assert got.loc[19, "_pair_state"] == sv.PARSE_ERROR
    assert got.loc[18, "_pair_state"] == sv.OBSERVED
    assert signal_map(got) == signal_map(panel)


@pytest.mark.parametrize("bad_date", ["not-a-date", None])
def test_bad_calendar_cannot_escape_panel_parse_state(tmp_path, bad_date):
    panel = _paired_panel().astype({"date": str})
    panel.loc[19, "date"] = bad_date
    path = tmp_path / "panel.parquet"
    panel.to_parquet(path)
    assert sv.panel_state(path) == (None, sv.PARSE_ERROR)


@pytest.mark.parametrize("kind", ["healthy", "zero", "tiny_positive", "missing", "invalid", "old_invalid"])
def test_real_parquet_reader_to_positioning_preserves_null_and_coverage(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    panel = _paired_panel(25)
    if kind == "zero":
        panel[["short_vol", "short_ratio"]] = 0.0
    elif kind == "tiny_positive":
        panel["short_vol"], panel["total_vol"], panel["short_ratio"] = 1.0, 1e8, 0.0
    elif kind == "missing":
        panel.loc[24, "short_vol"] = np.nan
    elif kind == "invalid":
        panel.loc[24, "total_vol"] = float("inf")
    elif kind == "old_invalid":
        panel.loc[0, "short_vol"] = -1
    path = tmp_path / "finra_short_volume" / "panel.parquet"
    path.parent.mkdir()
    panel.to_parquet(path)
    direct = signal_map(sv.panel_state(path)[0])
    assert direct and direct == sf._load_short_volume(), "the catch-all reader must not hide an exception"
    sig = direct["AAA"]
    got = sf._positioning("AAA", {}, None, None, sig)["short_flow"]
    encoded = json.dumps(got, allow_nan=False, sort_keys=True)
    assert json.loads(encoded) == got
    if kind in {"missing", "invalid"}:
        assert got["short_ratio_pct"] is None
        assert got["trend_pp"] is None
        assert got["coverage"] == sig["coverage"]
    elif kind == "old_invalid":
        assert got["short_ratio_pct"] == 50.0
        assert got["ratio_z"] is None
        assert set(got["coverage"]) == {"history_z"}
    else:
        assert "coverage" not in got
        assert got == {"short_ratio_pct": 50.0 if kind == "healthy" else 0.0,
                       "trend_pp": 0.0, "ratio_z": 0.0, "n_days": 25,
                       "asof": str(panel.iloc[-1]["date"].date()),
                       **({"state": sv.OBSERVED_ZERO} if kind == "zero" else {})}


def _daily(*rows, day="20240117"):
    return "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n" + "\n".join(
        f"{day}|{ticker}|{short}|0|{total}|Q" for ticker, short, total in rows)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("bad", ["", "bad", "nan", "inf", "-1", "101"])
def test_invalid_uppercase_winner_cannot_substitute_preferred(reverse, bad):
    rows = [("ABC", bad, "100"), ("AbC", "40", "100")]
    with pytest.raises(ValueError, match="invalid paired volumes.*ABC"):
        _parse(_daily(*(rows[::-1] if reverse else rows)))


@pytest.mark.parametrize("reverse", [False, True])
def test_discarded_bad_preferred_does_not_poison_uppercase_winner(reverse):
    rows = [("ABC", "50", "100"), ("AbC", "bad", "100")]
    got = _parse(_daily(*(rows[::-1] if reverse else rows)))
    assert got[["ticker", "short_vol", "total_vol"]].to_dict("records") == [
        {"ticker": "ABC", "short_vol": 50.0, "total_vol": 100.0}]


@pytest.mark.parametrize("reverse", [False, True])
def test_truncated_uppercase_row_is_not_dropped_before_identity(reverse):
    lines = ["20240117|ABC|50|0", "20240117|AbC|40|0|100|Q"]
    with pytest.raises(ValueError, match="invalid paired volumes.*ABC"):
        _parse("\n".join(lines[::-1] if reverse else lines))


@pytest.mark.parametrize("reverse", [False, True])
def test_zero_total_uppercase_winner_does_not_substitute_preferred(reverse):
    rows = [("ABC", "0", "0"), ("AbC", "40", "100")]
    assert _parse(_daily(*(rows[::-1] if reverse else rows))).empty


def _fixture_adapter(tmp_path, monkeypatch, responses, universe=None):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(fsv, "_universe_tickers", lambda: {"AAA"} if universe is None else universe)
    wanted = [date.fromisoformat(day) for day in responses]
    monkeypatch.setattr(fsv, "_business_days", lambda n: wanted)
    adapter = fsv.FinraShortVolumeAdapter()
    def get(url, **kwargs):
        day = pd.Timestamp(url.rsplit("CNMSshvol", 1)[1].removesuffix(".txt")).date().isoformat()
        value = responses[day]
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(text=value)
    monkeypatch.setattr(adapter, "http_get", get)
    return adapter


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("mode", ["all_invalid", "mixed", "valid_then_invalid"])
def test_invalid_refresh_fails_before_any_cache_witness_or_clock_write(tmp_path, monkeypatch, cached, mode):
    responses = {"2024-01-17": _daily(("AAA", "nan", "100"))}
    if mode == "mixed":
        responses["2024-01-17"] = _daily(("AAA", "50", "100"), ("BBB", "bad", "100"))
    elif mode == "valid_then_invalid":
        responses = {"2024-01-18": _daily(("AAA", "60", "100"), day="20240118"), **responses}
    adapter = _fixture_adapter(tmp_path, monkeypatch, responses, {"AAA", "BBB"})
    if cached:
        panel = fsv._panel_path()
        panel.parent.mkdir(parents=True)
        _parse(_daily(("AAA", "50", "100"))).to_parquet(panel)
        fsv._superseded_path().write_bytes(b"unchanged existing witness")
        store.upsert(fsv.GROUP, "finra_short_volume__ingest", pd.DataFrame(
            {"new_rows": [1], "fetched": [1]}, index=[pd.Timestamp("2024-01-17")]))
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = run_adapter(adapter)
    assert result.status == "failed"
    assert "invalid paired volumes" in result.error
    assert result.rows == 0 and result.last_date is None
    after = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


def test_invalid_untracked_row_is_excluded_before_admission(tmp_path, monkeypatch):
    adapter = _fixture_adapter(tmp_path, monkeypatch, {
        "2024-01-17": _daily(("AAA", "50", "100"), ("BAD", "nan", "100"))})
    result = run_adapter(adapter)
    assert result.status in {"ok", "stale"}
    assert pd.read_parquet(fsv._panel_path())["ticker"].tolist() == ["AAA"]


@pytest.mark.parametrize("response", [RuntimeError("not posted"), _daily(("AAA", "0", "0"))])
def test_legitimate_cache_only_heartbeat_keeps_observation_date(tmp_path, monkeypatch, response):
    adapter = _fixture_adapter(tmp_path, monkeypatch, {"2024-01-18": response})
    path = fsv._panel_path()
    path.parent.mkdir(parents=True)
    _parse(_daily(("AAA", "50", "100"))).to_parquet(path)
    before = path.read_bytes()
    result = run_adapter(adapter)
    assert result.status in {"ok", "stale"}
    assert result.last_date == "2024-01-17"
    assert path.read_bytes() == before
    heartbeat = store.read(fsv.GROUP, "finra_short_volume__ingest")
    assert heartbeat.index.max() == pd.Timestamp("2024-01-17")
    assert int(heartbeat.iloc[-1]["new_rows"]) == 0


def test_valid_correction_witnesses_once_and_reread_is_noop(tmp_path, monkeypatch):
    responses = {"2024-01-17": _daily(("AAA", "50", "100"))}
    adapter = _fixture_adapter(tmp_path, monkeypatch, responses)
    assert run_adapter(adapter).status in {"ok", "stale"}
    assert not fsv._superseded_path().exists()
    responses["2024-01-17"] = _daily(("AAA", "60", "100"))
    assert run_adapter(adapter).status in {"ok", "stale"}
    witness = pd.read_parquet(fsv._superseded_path())
    assert witness["short_vol"].tolist() == [50.0]
    assert pd.read_parquet(fsv._panel_path())["short_vol"].tolist() == [60.0]
    before = fsv._superseded_path().read_bytes()
    assert run_adapter(adapter).status in {"ok", "stale"}
    assert fsv._superseded_path().read_bytes() == before
