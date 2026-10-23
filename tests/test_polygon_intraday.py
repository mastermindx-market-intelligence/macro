"""Polygon intraday (4H chart data) collector — scripts/build_polygon_intraday.

The live aggregate fetch needs the entitled key (CI secret), so these pin the parts that
DON'T: the US class-share symbol mapping (Polygon uses a dot, our store a dash), the
curated universe (deep-history names + ETFs), and the load-bearing fail-safe — no key must
be a clean no-op so the daily collect run never breaks on the additive 4H step.
"""

from __future__ import annotations

import hashlib
import json

from scripts import build_polygon_intraday as bpi


def test_poly_sym_maps_class_share_dash_to_dot():
    assert bpi._poly_sym("AAPL") == "AAPL"
    assert bpi._poly_sym("BRK-B") == "BRK.B"     # Polygon wants the dot form
    assert bpi._poly_sym("BF-B") == "BF.B"


def test_universe_is_curated_us_set():
    u = bpi._universe()
    assert isinstance(u, list) and len(u) > 50      # ~deep names + ETFs
    assert "AAPL" in u
    assert u == sorted(u)                            # deterministic
    assert all(not t.startswith("^") for t in u)     # no index symbols


def test_explicit_symbols_are_not_intersected_with_chart_universe(monkeypatch, tmp_path):
    """The live board can request leaders absent from the curated chart universe."""
    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: True)
    monkeypatch.setattr(bpi, "_universe", lambda: ["AAPL"])
    requested = []

    def get(self, path, params=None):
        requested.append(path)
        return _bars((1_000, 10.0))

    monkeypatch.setattr(bpi.PolygonOptions, "_get", get)
    out = bpi.accrue(only=["snow", "AAPL"], out_dir=tmp_path)

    assert out["rows"] == 2
    assert any("/AAPL/" in path for path in requested)
    assert any("/SNOW/" in path for path in requested)
    assert (tmp_path / "SNOW.parquet").exists()


def test_accrue_without_key_is_a_clean_noop(monkeypatch):
    # force the client to look key-less regardless of the local environment
    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: False)
    out = bpi.accrue()
    assert out == {"status": "skipped", "rows": 0}


def _bars(*ms_close):
    """Synthetic Polygon /v2/aggs rows: (timestamp_ms, close) -> aggregate dicts."""
    return [{"t": t, "o": c, "h": c, "l": c, "c": c, "v": 100} for t, c in ms_close]


def test_accrue_is_incremental_append_and_key_deduped(monkeypatch, tmp_path):
    """Two runs over the same ticker must EXTEND the store (not overwrite) and de-dupe
    on the bar timestamp with last-write-wins — the append-only/key-dedup contract."""
    import pandas as pd

    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: True)
    monkeypatch.setattr(bpi.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(bpi, "_universe", lambda: ["AAPL"])

    runs = iter([
        _bars((1_000, 10.0), (2_000, 11.0)),                 # run 1: two bars
        _bars((2_000, 99.0), (3_000, 12.0)),                 # run 2: dup ts=2000 (new value) + new bar
    ])
    monkeypatch.setattr(bpi.PolygonOptions, "_get",
                        lambda self, path, params=None: next(runs))

    out1 = bpi.accrue()
    assert out1["status"] == "ok" and out1["rows"] == 1
    assert out1["delayed_min"] == bpi.DELAYED_MIN == 15

    df1 = pd.read_parquet(tmp_path / "intraday" / "AAPL.parquet")
    assert len(df1) == 2

    out2 = bpi.accrue()
    df2 = pd.read_parquet(tmp_path / "intraday" / "AAPL.parquet")
    assert len(df2) == 3                                      # appended, not overwritten
    assert df2.index.is_monotonic_increasing
    # ts=2000 kept the LAST write (run 2's 99.0), not the original 10/11 series
    dup_close = float(df2.iloc[1]["close"])
    assert dup_close == 99.0


def test_accrue_stamps_delayed_meta_sidecar(monkeypatch, tmp_path):
    """The store carries an honest 15-min-delayed label (sidecar survives the parquet
    round-trip where DataFrame.attrs would not)."""
    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: True)
    monkeypatch.setattr(bpi.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(bpi, "_universe", lambda: ["AAPL"])
    monkeypatch.setattr(bpi.PolygonOptions, "_get",
                        lambda self, path, params=None: _bars((1_000, 10.0)))

    bpi.accrue()
    meta = json.loads((tmp_path / "intraday" / "_meta.json").read_text())
    assert meta["delayed_min"] == 15
    assert meta["realtime"] is False
    assert meta["source"] == "polygon_standard"
    assert meta["adjusted"] is True
    assert meta["price_basis"] == bpi.PRICE_BASIS

    source = (tmp_path / "intraday" / "AAPL.parquet").resolve()
    receipt_path = tmp_path / "intraday" / "AAPL.parquet.receipt.json"
    receipt = json.loads(receipt_path.read_text())
    assert receipt == {
        "schema": bpi.PRICE_RECEIPT_SCHEMA,
        "ticker": "AAPL",
        "source_file": source.name,
        "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_available_at": receipt["source_available_at"],
        "bar_seconds": 3600,
        "vendor_delay_minutes": 15,
        "adjusted": True,
        "price_basis": bpi.PRICE_BASIS,
        "timestamp_basis": bpi.TIMESTAMP_BASIS,
        "row_count": 1,
        "first_time": "1970-01-01T00:00:01Z",
        "last_time": "1970-01-01T00:00:01Z",
    }
    assert receipt_path.read_bytes().endswith(b"\n")


def _cadence_fixture(monkeypatch):
    """Only synthetic aggregates; record if a rejected run reaches the vendor."""
    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: True)
    monkeypatch.setattr(bpi, "_universe", lambda: ["SPY"])
    monkeypatch.setattr(bpi.time, "sleep", lambda _: None)
    requested = []

    def get(self, path, params=None):
        requested.append(path)
        return _bars((1_700_000_000_000, 100.0),
                     (1_700_003_600_000, 102.0))

    monkeypatch.setattr(bpi.PolygonOptions, "_get", get)
    return requested


def _minute_config(monkeypatch):
    import copy
    cfg = copy.deepcopy(bpi.config.load())
    cfg["polygon"]["intraday"].update(
        multiplier=1, timespan="minute", lookback_days=1, sleep=0)
    monkeypatch.setattr(bpi.config, "load", lambda: cfg)


def test_cadence_flip_rejects_hourly_store_before_vendor_or_any_write(monkeypatch, tmp_path):
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["SPY"], out_dir=tmp_path)
    paths = [tmp_path / "SPY.parquet", tmp_path / "SPY.parquet.receipt.json",
             tmp_path / "_meta.json"]
    original = {p.name: p.read_bytes() for p in paths}
    assert len(calls) == 1
    _minute_config(monkeypatch)
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert len(calls) == 1
    assert {p.name: p.read_bytes() for p in paths} == original


def test_cadence_flip_rejects_other_ticker_even_full_mode(monkeypatch, tmp_path):
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["AAPL"], out_dir=tmp_path)
    original = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    _minute_config(monkeypatch)
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path, full=True)
    assert len(calls) == 1
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()} == original


def test_cadence_flip_rejects_hourly_receipt_with_missing_meta(monkeypatch, tmp_path):
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["SPY"], out_dir=tmp_path)
    (tmp_path / "_meta.json").unlink()
    source_before = (tmp_path / "SPY.parquet").read_bytes()
    receipt_before = (tmp_path / "SPY.parquet.receipt.json").read_bytes()
    _minute_config(monkeypatch)
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert len(calls) == 1
    assert (tmp_path / "SPY.parquet").read_bytes() == source_before
    assert (tmp_path / "SPY.parquet.receipt.json").read_bytes() == receipt_before


def test_unknown_legacy_store_blocks_minute_but_preserves_hourly(monkeypatch, tmp_path):
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["SPY"], out_dir=tmp_path)
    (tmp_path / "_meta.json").unlink()
    (tmp_path / "SPY.parquet.receipt.json").unlink()
    _minute_config(monkeypatch)
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert len(calls) == 1
    import copy
    cfg = copy.deepcopy(bpi.config.load())
    cfg["polygon"]["intraday"].update(multiplier=1, timespan="hour", sleep=0)
    monkeypatch.setattr(bpi.config, "load", lambda: cfg)
    out = bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert out["status"] == "ok" and len(calls) == 2


def test_fresh_dedicated_minute_store_writes_honest_receipt(monkeypatch, tmp_path):
    calls = _cadence_fixture(monkeypatch)
    _minute_config(monkeypatch)
    out = bpi.accrue(only=["SPY"], out_dir=tmp_path / "minute-only")
    root = tmp_path / "minute-only"
    assert out["status"] == "ok" and len(calls) == 1
    assert "/range/1/minute/" in calls[0]
    assert json.loads((root / "_meta.json").read_text())["bar"] == "1minute"
    assert json.loads((root / "SPY.parquet.receipt.json").read_text())["bar_seconds"] == 60


def test_matching_minute_store_can_accrue_again_without_rejection(monkeypatch, tmp_path):
    calls = _cadence_fixture(monkeypatch)
    _minute_config(monkeypatch)
    outdir = tmp_path / "minute-only"
    first = bpi.accrue(only=["SPY"], out_dir=outdir)
    second = bpi.accrue(only=["SPY"], out_dir=outdir)
    assert first["status"] == second["status"] == "ok"
    assert len(calls) == 2
    assert json.loads((outdir / "SPY.parquet.receipt.json").read_text())["bar_seconds"] == 60


def test_corrupt_cadence_receipt_fails_closed_before_fetch(monkeypatch, tmp_path):
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["SPY"], out_dir=tmp_path)
    receipt = tmp_path / "SPY.parquet.receipt.json"
    receipt.write_text('{"bar_seconds":"3600"}')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert len(calls) == 1
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_corrupt_cadence_metadata_fails_closed_before_fetch(monkeypatch, tmp_path):
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["SPY"], out_dir=tmp_path)
    (tmp_path / "_meta.json").write_text('{')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert len(calls) == 1
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_unknown_legacy_store_rejects_60minute_alias(monkeypatch, tmp_path):
    import copy
    import pytest
    calls = _cadence_fixture(monkeypatch)
    bpi.accrue(only=["SPY"], out_dir=tmp_path)
    (tmp_path / "_meta.json").unlink()
    (tmp_path / "SPY.parquet.receipt.json").unlink()
    cfg = copy.deepcopy(bpi.config.load())
    cfg["polygon"]["intraday"].update(multiplier=60, timespan="minute", sleep=0)
    monkeypatch.setattr(bpi.config, "load", lambda: cfg)
    with pytest.raises(ValueError, match="cadence"):
        bpi.accrue(only=["SPY"], out_dir=tmp_path)
    assert len(calls) == 1
