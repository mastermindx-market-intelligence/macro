"""Invented frames only; no provider, canonical cache, or live collector calls."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import pandas as pd
import pytest


@pytest.fixture
def modules(monkeypatch, tmp_path):
    # Loading copies also lets the root review these exact source artifacts
    # before integrating them. Canonical module bindings are restored by pytest.
    root = Path(__file__).resolve().parents[1]
    import lib
    import collectors
    yf = types.ModuleType("yfinance")

    def no_network(*args, **kwargs):
        raise AssertionError("provider call forbidden in capture fixture")

    yf.download = no_network
    monkeypatch.setitem(sys.modules, "yfinance", yf)

    def load(name, relative):
        spec = importlib.util.spec_from_file_location(name, root / relative)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        package, attr = name.rsplit(".", 1)
        monkeypatch.setattr(sys.modules[package], attr, module, raising=False)
        return module

    store = load("lib.store", "lib/store.py")
    base = load("collectors.base", "collectors/base.py")
    yahoo = load("collectors.yahoo", "collectors/yahoo.py")
    monkeypatch.setattr(store.config, "data_dir", lambda: tmp_path)
    (tmp_path / "yahoo").mkdir()
    return store, base, yahoo


def frame(dates=("2024-01-02", "2024-01-03"), values=(10.0, 11.0)):
    return pd.DataFrame({"close": values, "close_price": values, "volume": [100] * len(dates)},
                        index=pd.to_datetime(list(dates)))


def lineage(ticker="XLB"):
    return {"provider": "yahoo", "field": "Adj Close", "basis": "total_return", "ticker": ticker}


def capture(store, monkeypatch, *, provider=None, merged=None, ticker="XLB", source=None):
    known = datetime(2026, 10, 13, 9, tzinfo=timezone.utc)
    clocks = iter([known + timedelta(seconds=1), known + timedelta(seconds=2)])
    monkeypatch.setattr(store, "_availability_now", lambda: next(clocks))
    return store.capture_yahoo_observation(
        ticker, frame(("2024-01-03",), (11.0,)) if provider is None else provider,
        frame() if merged is None else merged,
        lineage=lineage(ticker) if source is None else source, adapter_return_known_by=known)


def capture_root(tmp_path):
    return tmp_path / "yahoo" / ".availability_capture"


def test_distinct_images_clocks_and_limited_claims(modules, monkeypatch, tmp_path):
    store, _, _ = modules
    result = capture(store, monkeypatch)
    receipt = result["receipt"]
    provider, merged = receipt["provider_return_image"], receipt["merged_capture_image"]
    assert provider["sha256"] != merged["sha256"]
    root = capture_root(tmp_path)
    for entry in (provider, merged):
        data = (root / entry["object_ref"]).read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert (root / entry["object_ref"]).stat().st_mode & 0o777 == 0o600
    assert len(json.loads((root / provider["object_ref"]).read_bytes())["rows"]) == 1
    assert len(json.loads((root / merged["object_ref"]).read_bytes())["rows"]) == 2
    assert provider["adapter_return_known_by_utc"] < merged["captured_known_by_utc"]
    assert merged["captured_known_by_utc"] < merged["immutable_publication_durable_at_utc"]
    assert receipt["provider_available_at"] is None
    assert receipt["operation_identity"] is None
    assert receipt["source_actor_authentication"] is None
    assert receipt["historical_original_availability_proven"] is False
    assert receipt["upstream_revision_history_complete"] is False
    assert receipt["canonical_cache_transaction_durability"] == "UNQUALIFIED"
    assert receipt["calendar_verification"] == "UNQUALIFIED"
    assert json.loads((root / result["receipt_ref"]).read_bytes()) == receipt
    assert not list(root.rglob(".partial-*"))


def test_same_bytes_are_reused_without_overwrite(modules, monkeypatch, tmp_path):
    store, _, _ = modules
    first = capture(store, monkeypatch)
    root = capture_root(tmp_path)
    path = root / first["receipt"]["provider_return_image"]["object_ref"]
    before = path.stat()
    second = capture(store, monkeypatch)
    assert second == first
    assert path.stat().st_ino == before.st_ino
    assert path.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("kind", ["content", "mode", "symlink"])
def test_existing_object_collision_refuses_without_replacement(modules, monkeypatch, tmp_path, kind):
    store, _, _ = modules
    first = capture(store, monkeypatch)
    root = capture_root(tmp_path)
    path = root / first["receipt"]["provider_return_image"]["object_ref"]
    if kind == "content":
        path.write_bytes(b"corrupt invented fixture")
    elif kind == "mode":
        path.chmod(0o644)
    else:
        path.unlink()
        path.symlink_to(tmp_path / "not-present")
    identity = path.lstat().st_ino
    with pytest.raises((ValueError, OSError)):
        capture(store, monkeypatch)
    assert path.lstat().st_ino == identity
    assert len(list((root / "receipts").glob("*.json"))) == 1


@pytest.mark.parametrize("ticker,source", [
    ("XLC", lineage("XLC")), ("SPY", lineage("SPY")),
    ("XLB", {}), ("XLB", {**lineage(), "provider": "stooq"}),
    ("XLB", {**lineage(), "field": "Close"}),
    ("XLB", {**lineage(), "ticker": "XLE"}),
])
def test_lineage_and_cohort_refuse_before_io(modules, monkeypatch, tmp_path, ticker, source):
    store, _, _ = modules
    with pytest.raises(ValueError):
        capture(store, monkeypatch, ticker=ticker, source=source)
    assert not capture_root(tmp_path).exists()


@pytest.mark.parametrize("kind", ["duplicate", "unsorted", "intraday", "aware", "nat", "inf", "bool", "string", "columns", "empty", "huge_integer"])
def test_malformed_images_refuse_before_io(modules, monkeypatch, tmp_path, kind):
    store, _, _ = modules
    f = frame()
    if kind == "duplicate": f.index = pd.to_datetime(["2024-01-02"] * 2)
    elif kind == "unsorted": f = f.iloc[::-1]
    elif kind == "intraday": f.index += pd.Timedelta(hours=1)
    elif kind == "aware": f.index = f.index.tz_localize("UTC")
    elif kind == "nat": f.index = pd.to_datetime(["2024-01-02", None])
    elif kind == "inf": f.loc[f.index[0], "close"] = float("inf")
    elif kind == "bool": f["close"] = [True, False]
    elif kind == "string": f["close"] = ["10", "11"]
    elif kind == "columns": f["unexpected"] = 1
    elif kind == "empty": f = f.iloc[:0]
    elif kind == "huge_integer": f["volume"] = [2**53, 1]
    with pytest.raises(ValueError):
        capture(store, monkeypatch, provider=f)
    assert not capture_root(tmp_path).exists()


def test_missing_numeric_values_remain_null(modules):
    store, _, _ = modules
    f = frame()
    f.loc[f.index[0], "volume"] = float("nan")
    decoded = json.loads(store._availability_image(f))
    assert decoded["rows"][0][-1] is None


@pytest.mark.parametrize("limit", ["rows", "bytes"])
def test_resource_bounds_before_publication(modules, monkeypatch, tmp_path, limit):
    store, _, _ = modules
    monkeypatch.setattr(store, "_CAPTURE_ROW_LIMIT" if limit == "rows" else "_CAPTURE_IMAGE_LIMIT", 1)
    with pytest.raises(ValueError):
        capture(store, monkeypatch)
    assert not capture_root(tmp_path).exists()


@pytest.mark.parametrize("kind", ["naive", "non_utc", "regression", "future_row"])
def test_unknown_or_inconsistent_clocks_refuse(modules, monkeypatch, tmp_path, kind):
    store, _, _ = modules
    now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    known = now - timedelta(seconds=1)
    f = frame()
    if kind == "naive": known = known.replace(tzinfo=None)
    elif kind == "non_utc": known = known.astimezone(timezone(timedelta(hours=1)))
    elif kind == "regression": known = now + timedelta(seconds=1)
    elif kind == "future_row": f.index = pd.to_datetime(["2027-01-02", "2027-01-03"])
    monkeypatch.setattr(store, "_availability_now", lambda: now)
    with pytest.raises(ValueError):
        store.capture_yahoo_observation("XLB", f, f, lineage=lineage(), adapter_return_known_by=known)
    assert not capture_root(tmp_path).exists()


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_interrupted_publication_never_returns_acceptance(modules, monkeypatch, tmp_path, fail_at):
    store, _, _ = modules
    original = store._availability_publish
    calls = []
    def failing(directory, payload):
        calls.append(directory.name)
        if len(calls) == fail_at:
            raise OSError("injected publication failure")
        return original(directory, payload)
    monkeypatch.setattr(store, "_availability_publish", failing)
    with pytest.raises(OSError):
        capture(store, monkeypatch)
    assert not list(capture_root(tmp_path).glob("receipts/*.json"))
    if fail_at == 3:
        assert calls == ["objects", "objects", "receipts"]
        assert len(list(capture_root(tmp_path).glob("objects/*.json"))) == 2


def test_directory_durability_failure_is_not_accepted(modules, monkeypatch, tmp_path):
    store, _, _ = modules
    def fail(path): raise OSError("directory durability unavailable")
    monkeypatch.setattr(store, "_availability_fsync_dir", fail)
    with pytest.raises(OSError):
        capture(store, monkeypatch)
    assert not list(capture_root(tmp_path).glob("receipts/*.json"))


def setup_yahoo(modules, monkeypatch, *, adj=True):
    store, base, yahoo = modules
    adapter = yahoo.YahooAdapter.__new__(yahoo.YahooAdapter)
    adapter.cfg = {"batch_size": 1, "tickers": {"vol": []}}
    monkeypatch.setattr(adapter, "all_tickers", lambda: ["XLB"])
    monkeypatch.setattr(adapter, "maintained_tickers", lambda: ["XLB"])
    monkeypatch.setattr(yahoo, "_report_delisted_exclusions", lambda x: [])
    monkeypatch.setattr(yahoo, "_report_missing_symbols", lambda *args: [])
    monkeypatch.setattr(yahoo.config, "load", lambda: {"stock_search": {"extra_tickers": []}})
    raw = pd.DataFrame({"Close": [10.0, 11.0], "Volume": [100, 100]}, index=frame().index)
    if adj: raw["Adj Close"] = [9.0, 10.0]
    monkeypatch.setattr(adapter, "_download", lambda *args: raw)
    return adapter


def test_lineage_is_only_current_qualified_yahoo_adj_close(modules, monkeypatch):
    _, _, yahoo = modules
    adapter = setup_yahoo(modules, monkeypatch)
    adapter.fetch(full_history=True)
    assert not hasattr(adapter, "_availability_sources")
    adapter.fetch(full_history=True, capture_source_metadata=True)
    assert adapter.availability_source_metadata("XLB") == lineage()
    assert adapter.availability_source_metadata("SPY") is None
    adapter.fetch(full_history=True)
    assert adapter.availability_source_metadata("XLB") is None
    assert not hasattr(adapter, "_availability_sources")


def test_missing_adj_close_never_gets_tr_lineage(modules, monkeypatch):
    adapter = setup_yahoo(modules, monkeypatch, adj=False)
    assert "XLB" in adapter.fetch(full_history=True, capture_source_metadata=True)
    assert adapter.availability_source_metadata("XLB") is None


@pytest.mark.parametrize("heal", ["qualified", "no_adj", "failed"])
def test_rebase_replaces_lineage_with_actual_healed_response(modules, monkeypatch, heal):
    store, _, _ = modules
    adapter = setup_yahoo(modules, monkeypatch, adj=heal != "no_adj")
    adapter._availability_sources = {"XLB": lineage()}
    monkeypatch.setattr(store, "basis_shifted", lambda *args, **kwargs: True)
    if heal == "failed":
        def fail(*args): raise RuntimeError("fixture provider unavailable")
        monkeypatch.setattr(adapter, "_download", fail)
    frames = {"XLB": frame()}
    deferred = adapter._rebase_shifted(frames, set(), capture_source_metadata=True)
    if heal == "qualified":
        assert adapter.availability_source_metadata("XLB") == lineage()
        assert deferred == []
    else:
        assert adapter.availability_source_metadata("XLB") is None
        assert deferred == (["XLB"] if heal == "failed" else [])
        if heal == "failed": assert "XLB" not in frames


def test_stooq_fallback_gets_no_yahoo_lineage(modules, monkeypatch):
    _, _, _ = modules
    adapter = setup_yahoo(modules, monkeypatch)
    adapter._availability_sources = {}
    fallback = types.ModuleType("lib.stooq")
    fallback.stooq_daily = lambda ticker: frame()
    monkeypatch.setitem(sys.modules, "lib.stooq", fallback)
    import lib
    monkeypatch.setattr(lib, "stooq", fallback, raising=False)
    frames = {}
    adapter._fill_missing_extras(frames, ["XLB"])
    assert "XLB" in frames
    assert adapter.availability_source_metadata("XLB") is None


def runner_setup(modules, monkeypatch):
    store, base, _ = modules
    adapter = setup_yahoo(modules, monkeypatch)
    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    monkeypatch.setattr(base, "_series_session_calendar", lambda *args: None)
    monkeypatch.setattr(base, "detect_stale_series", lambda *args, **kwargs: [])
    monkeypatch.setattr(base, "_contract_entries", lambda *args: [])
    monkeypatch.setattr(base, "_emit_dark_columns", lambda *args: [])
    monkeypatch.setattr(store, "upsert", lambda *args, **kwargs: frame())
    return adapter


def test_runner_default_off_does_no_capture_work(modules, monkeypatch, tmp_path):
    store, base, _ = modules
    adapter = runner_setup(modules, monkeypatch)
    def forbidden(*args, **kwargs): raise AssertionError("default off capture invoked")
    monkeypatch.setattr(store, "capture_yahoo_observation", forbidden)
    result = base.run_adapter(adapter, full_history=True)
    assert result.status in {"ok", "stale"}
    assert not any("availability" in note for note in result.notes)
    assert not hasattr(adapter, "_availability_sources")
    assert not capture_root(tmp_path).exists()


def test_runner_opt_in_reaches_real_capture_helper(modules, monkeypatch, tmp_path):
    _, base, _ = modules
    adapter = runner_setup(modules, monkeypatch)
    result = base.run_adapter(adapter, full_history=True, capture_yahoo_receipts=True)
    assert result.status in {"ok", "stale"}
    assert any("XLB receipt=" in note for note in result.notes)
    assert len(list(capture_root(tmp_path).glob("receipts/*.json"))) == 1
    assert sum("no qualified returned" in note for note in result.notes) == 8


def test_runner_capture_failure_is_visible_without_cache_replay(modules, monkeypatch, tmp_path):
    store, base, _ = modules
    adapter = runner_setup(modules, monkeypatch)
    writes = []
    monkeypatch.setattr(store, "upsert", lambda *args, **kwargs: writes.append(args) or frame())
    def fail(*args, **kwargs): raise OSError("must not leak this private diagnostic")
    monkeypatch.setattr(store, "capture_yahoo_observation", fail)
    result = base.run_adapter(adapter, full_history=True, capture_yahoo_receipts=True)
    assert result.status in {"ok", "stale"}
    assert len(writes) == 1
    assert any("XLB refused" in note for note in result.notes)
    assert "private diagnostic" not in str(result)
    assert not capture_root(tmp_path).exists()


def test_runner_rejects_other_adapter_before_fetch(modules, monkeypatch):
    _, base, _ = modules
    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    adapter = base.Adapter()
    def forbidden(*args, **kwargs): raise AssertionError("wrong adapter fetched")
    monkeypatch.setattr(adapter, "fetch", forbidden)
    result = base.run_adapter(adapter, capture_yahoo_receipts=True)
    assert result.status == "failed"
    assert "incumbent Yahoo adapter" in result.error
