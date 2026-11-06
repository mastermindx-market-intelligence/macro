"""Offline orchestration and real archive-pipeline tests for BOATS refresh.

Provider responses and credentials are always fixtures; the integration cases
exercise the actual archive, materializer, reader, builder and NYSE calendar.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from scripts.boats_history_window import CONSTANTS

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "refresh_boats_history.py"
_spec = importlib.util.spec_from_file_location("refresh_boats_history_under_test", MODULE)
refresh = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = refresh
_spec.loader.exec_module(refresh)

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
SESSION = "2026-10-19"                       # a Monday NYSE session
RECEIVED_AT = "2026-10-19T08:31:00Z"         # after the 04:00 ET session end
NOW_OK = datetime(2026, 10, 19, 9, 30, tzinfo=ET)
HISTORY_SCHEMA = "terminal.tiingo_boats_history.v1"


class FakeArchive:
    """Minimal stand-in for collectors.tiingo_archive.Archive."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.free_floor = 0
        self.stored: list[tuple[str, str, bytes]] = []

    def store_response(self, source, symbol, path, raw, *, received_at=None,
                       content_type="application/json"):
        assert source == "boats-bars"
        self.stored.append((symbol, path, raw))
        rid = hashlib.sha256(f"{symbol}|{path}".encode()).hexdigest()
        digest = hashlib.sha256(raw).hexdigest()
        observed = received_at or RECEIVED_AT
        receipt = {"vendor": "tiingo", "source": source, "symbol": symbol,
                   "request_path": path, "observed_at_utc": observed,
                   "raw_sha256": digest, "raw_path": f"raw/{observed[:10]}/{symbol}.gz",
                   "receipt_id": rid}
        day_dir = self.root / "receipts" / source / observed[:10]
        day_dir.mkdir(parents=True, exist_ok=True)
        (day_dir / f"{rid[:24]}.json").write_text(json.dumps(receipt) + "\n")
        return {"receipt_id": rid, "raw_sha256": digest, "rows_hint": None,
                "raw_bytes": len(raw), "new_raw": True, "observed_at_utc": observed}


class Fetcher:
    """One request per call; no retries exist anywhere in the module."""

    def __init__(self, payloads=None, fail_on=()):
        self.calls: list[str] = []
        self.payloads = payloads or {}
        self.fail_on = set(fail_on)

    def __call__(self, path, key, *, max_bytes):
        assert key == "test-isolated-key"
        assert 1 <= max_bytes <= 64 * 1024 * 1024
        self.calls.append(path)
        symbol = path.split("/boats/")[1].split("/")[0]
        if symbol in self.fail_on:
            raise RuntimeError("Tiingo transport unavailable")
        return self.payloads.get(symbol, b'[{"open": 1, "volume": 5}]'), "application/json"


def default_payload(symbol, refs):
    return {**CONSTANTS, "symbol": symbol,
            "receipts": [{"receipt_id": rid} for _, rid in refs],
            "bars": [[1792371600 + 60 * i, 1.0, 2.0, 0.5, 1.5, 7.0] for i in range(len(refs))],
            "bar_receipt_ids": [[rid] for _, rid in refs]}


class Builder:
    """Stand-in for build_chart_history; enforces the receipt-hint contract."""

    def __init__(self, payload_for=default_payload, fail=None):
        self.calls: list[tuple[str, list, dict]] = []
        self.payload_for = payload_for
        self.fail = fail

    def __call__(self, symbol, refs, *, root, check_mount, receipt_paths):
        assert set(receipt_paths) == set(refs), "hints must match every selected ref"
        for ref, path in receipt_paths.items():
            assert Path(path).is_file(), f"hint not a file: {ref}"
        self.calls.append((symbol, list(refs), {k: Path(v) for k, v in receipt_paths.items()}))
        fail = self.fail.get(symbol) if isinstance(self.fail, dict) else self.fail
        if fail is not None:
            raise fail
        payload = self.payload_for(symbol, refs)
        payload["receipts"] = [{k: json.loads(Path(receipt_paths[ref]).read_text())[k]
                                 for k in ("receipt_id", "raw_sha256", "observed_at_utc", "request_path")}
                                for ref in refs]
        return payload


def make_cfg(tmp_path, symbols, *, capture=True, name="out", max_requests=None,
             max_total_bytes=None, max_response_bytes=1_000_000, history_dir=None):
    symbols_path = tmp_path / "symbols.txt"
    symbols_path.write_text("\n".join(symbols) + "\n")
    if history_dir is None:
        history_dir = tmp_path / "history"
        history_dir.mkdir(exist_ok=True)
    return refresh.RefreshConfig(
        session=SESSION, symbols_path=symbols_path, history_dir=history_dir,
        output_dir=tmp_path / name, root=tmp_path / "archive", capture=capture,
        max_requests=len(symbols) if max_requests is None else max_requests,
        max_total_bytes=10**9 if max_total_bytes is None else max_total_bytes,
        max_response_bytes=max_response_bytes)


def make_deps(archive, fetcher, builder=None, *, materialize=None, session_check=None,
              clock=None):
    return refresh.RefreshDeps(
        archive_factory=lambda root, check_mount=True: archive,
        request_path=lambda symbol, session: (
            f"/boats/{symbol}/prices?columns=open%2Chigh%2Clow%2Cclose%2Cvolume"
            f"&endDate={session}&resampleFreq=1min&startDate={session}"),
        fetch=fetcher, read_key=lambda: "test-isolated-key",
        materialize=materialize or (lambda root, receipt, *, free_floor: {"status": "WRITTEN"}),
        build_history=builder or Builder(),
        session_check=session_check or (lambda day: True),
        clock=clock or (lambda: NOW_OK))


def seed_receipt(root, symbol, day, observed):
    rid = hashlib.sha256(f"seed|{symbol}|{observed}".encode()).hexdigest()
    receipt = {"vendor": "tiingo", "source": "boats-bars", "symbol": symbol,
               "request_path": f"/boats/{symbol}/prices?resampleFreq=1min",
               "observed_at_utc": observed,
               "raw_sha256": hashlib.sha256(f"raw|{rid}".encode()).hexdigest(),
               "raw_path": f"raw/{day}/{symbol}.gz", "receipt_id": rid}
    day_dir = Path(root) / "receipts" / "boats-bars" / day
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{rid[:24]}.json"
    path.write_text(json.dumps(receipt) + "\n")
    return (day, rid), path


def write_prior_history(history_dir, symbol, refs, bars=None):
    doc = {**CONSTANTS, "symbol": symbol,
           "receipts": [{"receipt_id": rid, "raw_sha256": "0" * 64,
                         "observed_at_utc": f"{day}T05:00:00Z", "request_path": f"/boats/{symbol}/prices?resampleFreq=1min"}
                        for day, rid in refs],
           "bars": bars if bars is not None else [[1791511200, 10.0, 12.0, 9.0, 11.0, 13.0]],
           "bar_receipt_ids": [[rid for _, rid in refs]]}
    path = history_dir / f"{symbol}.json"
    path.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    return path.read_bytes()


def tree_state(directory: Path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(directory).iterdir())}


# --------------------------------------------------------------------------- #
# Calendar, DST and end-of-window semantics.                                  #
# --------------------------------------------------------------------------- #

def test_overnight_window_maps_onto_session_utc_date_in_est_and_edt():
    est_start, est_end = refresh.window_utc_bounds("2026-01-15")
    assert (est_start, est_end) == (datetime(2026, 1, 15, 1, 0, tzinfo=UTC),
                                    datetime(2026, 1, 15, 9, 0, tzinfo=UTC))
    edt_start, edt_end = refresh.window_utc_bounds("2026-09-15")
    assert (edt_start, edt_end) == (datetime(2026, 9, 15, 0, 0, tzinfo=UTC),
                                    datetime(2026, 9, 15, 8, 0, tzinfo=UTC))
    # DST transition days: bounds are computed with ZoneInfo, never weekdays.
    for session in ("2026-03-08", "2026-11-01"):
        start, end = refresh.window_utc_bounds(session)
        assert start.date() == end.date() == date.fromisoformat(session)
        assert start < end


def test_capture_requires_real_session_and_closed_04et_window(tmp_path):
    archive, fetcher = FakeArchive(tmp_path / "archive"), Fetcher()
    cfg = make_cfg(tmp_path, ["AMD"])
    with pytest.raises(refresh.RefreshRefused, match="not an NYSE session"):
        refresh.run_refresh(cfg, make_deps(archive, fetcher, session_check=lambda d: False))
    early = datetime(2026, 10, 19, 3, 59, tzinfo=ET)
    with pytest.raises(refresh.RefreshRefused, match="not ended"):
        refresh.run_refresh(cfg, make_deps(archive, fetcher, clock=lambda: early))
    assert fetcher.calls == []
    assert not cfg.output_dir.exists()


# --------------------------------------------------------------------------- #
# Pre-effect validation: nothing reaches the provider.                        #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mutate,match", [
    ("bad_symbol", "invalid vendor ticker"),
    ("too_many_symbols", "exceed"),
    ("tiny_request_budget", "exceed max_requests"),
    ("tiny_byte_budget", "max_total_bytes must be positive"),
    ("existing_output_dir", "already exists"),
    ("public_output_tree", "private"),
    ("missing_history_dir", "chart-history directory"),
    ("symlinked_history_dir", "chart-history directory"),
])
def test_invalid_inputs_refused_before_any_provider_call(tmp_path, monkeypatch, mutate, match):
    archive, fetcher = FakeArchive(tmp_path / "archive"), Fetcher()
    symbols = ["AMD", "NVDA"]
    if mutate == "bad_symbol":
        symbols = ["amd"]
    if mutate == "too_many_symbols":
        monkeypatch.setattr(refresh, "MAX_SYMBOLS", 1)
    cfg = make_cfg(tmp_path, symbols,
                   max_requests=1 if mutate == "tiny_request_budget" else None,
                   max_total_bytes=0 if mutate == "tiny_byte_budget" else None,
                   name="out")
    if mutate == "existing_output_dir":
        cfg.output_dir.mkdir()
    if mutate == "public_output_tree":
        cfg.output_dir = tmp_path / "public" / "out"
    if mutate == "missing_history_dir":
        cfg.history_dir.rmdir()
    if mutate == "symlinked_history_dir":
        cfg.history_dir.rmdir()
        cfg.history_dir.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(refresh.RefreshRefused, match=match):
        refresh.run_refresh(cfg, make_deps(archive, fetcher))
    assert fetcher.calls == []
    if mutate != "existing_output_dir":
        assert not Path(tmp_path, "out").exists()
    assert archive.stored == []


def test_dry_run_reports_plan_and_performs_no_effect(tmp_path):
    archive, fetcher = FakeArchive(tmp_path / "archive"), Fetcher()
    cfg = make_cfg(tmp_path, ["AMD", "NVDA"], capture=False)
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetcher))
    assert code == 0
    assert manifest["mode"] == "dry_run" and manifest["runnable"] is True
    assert manifest["requests_planned"] == 2
    assert manifest["complete_history"] is False
    assert fetcher.calls == [] and archive.stored == []
    assert not cfg.output_dir.exists()


# --------------------------------------------------------------------------- #
# Capture ordering, rebuild lineage and preservation.                         #
# --------------------------------------------------------------------------- #

def test_rebuild_uses_one_new_receipt_and_preserves_prior_bar_lineage(tmp_path, monkeypatch):
    archive, fetcher = FakeArchive(tmp_path / "archive"), Fetcher()
    hist = tmp_path / "history"
    hist.mkdir()
    ref1, path1 = seed_receipt(tmp_path / "archive", "AMD", "2026-10-15", "2026-10-15T05:00:00Z")
    ref2, path2 = seed_receipt(tmp_path / "archive", "AMD", "2026-10-16", "2026-10-16T05:00:00Z")
    prior_bytes = write_prior_history(hist, "AMD", [ref1, ref2])
    builder = Builder()
    cfg = make_cfg(tmp_path, ["AMD"])
    counted = {"n": 0}

    original = refresh.index_receipts

    def counting(root, days=None):
        counted["n"] += 1
        return original(root, days)

    monkeypatch.setattr(refresh, "index_receipts", counting)
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetcher, builder))

    assert code == 0 and manifest["status"] == "complete"
    assert counted["n"] == 1, "receipt index must be resolved once per capture day"
    symbol, refs, hints = builder.calls[0]
    assert symbol == "AMD"
    assert len(refs) == 1 and refs[0][0] == "2026-10-19" and len(refs[0][1]) == 64
    assert set(hints) == set(refs)
    out = cfg.output_dir / "AMD.json"
    result = json.loads(out.read_text())
    assert result["bars"][0] == json.loads(prior_bytes)["bars"][0]
    assert result["bar_receipt_ids"][0] == [ref1[1], ref2[1]]
    entry = manifest["outputs"][0]
    assert entry["status"] == "rebuilt" and entry["bars"] == 2
    assert entry["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert manifest["complete_history"] is False and manifest["activated"] is False
    # The immutable input tree kept every byte, including the prior history file.
    assert (hist / "AMD.json").read_bytes() == prior_bytes
    assert tree_state(hist) == {"AMD.json": hashlib.sha256(prior_bytes).hexdigest()}


def test_raw_is_stored_before_normalization_and_survives_a_refusal(tmp_path):
    archive = FakeArchive(tmp_path / "archive")
    fetcher = Fetcher()
    hist = tmp_path / "history"
    hist.mkdir()

    def late_refusing_materialize(root, receipt, *, free_floor):
        assert archive.stored, "immutable raw retention must precede normalization"
        raise ValueError("conflicting BOATS revisions require explicit resolution")

    cfg = make_cfg(tmp_path, ["AMD"])
    manifest, code = refresh.run_refresh(
        cfg, make_deps(archive, fetcher, materialize=late_refusing_materialize))
    assert code == 3 and manifest["status"] == "partial"
    assert len(archive.stored) == 1
    symbol, path, raw = archive.stored[0]
    assert symbol == "AMD" and raw and "startDate=2026-10-19" in path
    assert manifest["unavailable"][0]["reason"].startswith("materialize_failed")
    assert manifest["outputs"] == []
    assert (cfg.output_dir / "result-receipt.json").is_file()
    assert not (cfg.output_dir / "AMD.json").exists()


def test_conflicting_revision_refusal_keeps_prior_and_other_symbols(tmp_path):
    archive = FakeArchive(tmp_path / "archive")
    fetcher = Fetcher()
    hist = tmp_path / "history"
    hist.mkdir()
    ref, _ = seed_receipt(tmp_path / "archive", "AMD", "2026-10-15", "2026-10-15T05:00:00Z")
    prior_bytes = write_prior_history(hist, "AMD", [ref])
    builder = Builder(fail={"AMD": ValueError("conflicting BOATS revisions require explicit resolution")})
    cfg = make_cfg(tmp_path, ["AMD", "NVDA"])
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetcher, builder))
    assert code == 3
    assert "conflicting" in manifest["unavailable"][0]["reason"]
    assert [o["symbol"] for o in manifest["outputs"]] == ["NVDA"]
    assert manifest["outputs"][0]["status"] == "rebuilt"
    assert (hist / "AMD.json").read_bytes() == prior_bytes
    assert not (cfg.output_dir / "AMD.json").exists()


def test_provider_failure_stops_new_calls_and_reports_partial(tmp_path):
    archive = FakeArchive(tmp_path / "archive")
    fetcher = Fetcher(fail_on={"NVDA"})
    hist = tmp_path / "history"
    hist.mkdir()
    builder = Builder()
    cfg = make_cfg(tmp_path, ["AMD", "NVDA", "TSLA"])
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetcher, builder))
    assert code == 3 and manifest["status"] == "partial"
    assert len(fetcher.calls) == 2, "no request may follow a provider failure"
    assert [o["symbol"] for o in manifest["outputs"]] == ["AMD"]
    assert manifest["unavailable"][0]["symbol"] == "NVDA"
    assert manifest["unavailable"][0]["reason"].startswith("provider_unavailable")
    assert manifest["not_requested"] == ["TSLA"]
    assert manifest["requests"] == {"made": 2, "limit": 3}


def test_empty_response_preserves_other_windows_and_marks_vendor_empty(tmp_path):
    archive = FakeArchive(tmp_path / "archive")
    fetcher = Fetcher(payloads={"AMD": b"[]", "NVDA": b"[]"})
    hist = tmp_path / "history"
    hist.mkdir()
    ref, _ = seed_receipt(tmp_path / "archive", "AMD", "2026-10-15", "2026-10-15T05:00:00Z")
    prior_bytes = write_prior_history(hist, "AMD", [ref])
    materialized = []
    builder = Builder()
    cfg = make_cfg(tmp_path, ["AMD", "NVDA"])
    manifest, code = refresh.run_refresh(
        cfg, make_deps(archive, fetcher, builder,
                       materialize=lambda root, receipt, *, free_floor:
                       materialized.append(receipt["symbol"]) or {"status": "EMPTY_NORMALIZED"}))
    assert code == 0 and manifest["status"] == "complete"
    assert sorted(materialized) == ["AMD", "NVDA"]
    kept = cfg.output_dir / "AMD.json"
    assert json.loads(kept.read_bytes())["bars"] == json.loads(prior_bytes)["bars"]
    assert (hist / "AMD.json").read_bytes() == prior_bytes
    assert manifest["outputs"][0]["status"] == "refreshed_empty_window"
    assert manifest["outputs"][0]["sha256"] == hashlib.sha256(kept.read_bytes()).hexdigest()
    assert not (cfg.output_dir / "NVDA.json").exists()
    assert len(manifest["outputs"][1]["new_receipt"]) == 64
    assert manifest["outputs"][1]["status"] == "vendor_empty"
    assert builder.calls == [], "an empty vendor response never enters the bar builder"


# --------------------------------------------------------------------------- #
# No silent replay, budgets and failure receipts.                             #
# --------------------------------------------------------------------------- #

def test_existing_output_directory_is_never_replayed(tmp_path):
    archive, fetcher = FakeArchive(tmp_path / "archive"), Fetcher()
    hist = tmp_path / "history"
    hist.mkdir()
    cfg = make_cfg(tmp_path, ["AMD"])
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetcher))
    assert code == 0
    before = tree_state(cfg.output_dir)
    with pytest.raises(refresh.RefreshRefused, match="already exists"):
        refresh.run_refresh(cfg, make_deps(archive, fetcher))
    assert tree_state(cfg.output_dir) == before
    assert len(archive.stored) == 1, "second run must not add provider effects"


def test_failure_after_start_writes_an_error_receipt(tmp_path):
    archive = FakeArchive(tmp_path / "archive")

    def broken_factory(root, check_mount=True):
        raise RuntimeError("external Mastermind drive not mounted; no SSD fallback")

    fetcher = Fetcher()
    cfg = make_cfg(tmp_path, ["AMD"])
    deps = make_deps(archive, fetcher)
    deps.archive_factory = broken_factory
    with pytest.raises(RuntimeError, match="not mounted"):
        refresh.run_refresh(cfg, deps)
    assert fetcher.calls == []
    receipts = json.loads((cfg.output_dir / "error-receipt.json").read_text())
    assert receipts["error"] == "RuntimeError"
    assert (cfg.output_dir / "start-receipt.json").is_file()
    assert not (cfg.output_dir / "manifest.json").exists()


def test_dry_run_reports_unknown_calendar_without_effect(tmp_path):
    archive, fetcher = FakeArchive(tmp_path / "archive"), Fetcher()

    def no_calendar(day):
        raise ImportError("No module named 'lib'")

    cfg = make_cfg(tmp_path, ["AMD"], capture=False)
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetcher,
                                                        session_check=no_calendar))
    assert code == 0 and manifest["runnable"] is False
    assert manifest["gate"]["is_session"] is None
    assert manifest["gate"]["calendar"] == "unavailable"
    assert fetcher.calls == [] and not cfg.output_dir.exists()

    with pytest.raises(refresh.RefreshRefused, match="calendar unavailable"):
        refresh.run_refresh(make_cfg(tmp_path, ["AMD"], capture=True, name="out2"),
                            make_deps(archive, fetcher, session_check=no_calendar))
    assert not (tmp_path / "out2").exists()


def test_cli_dry_run_is_the_default_and_prints_a_manifest(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(refresh, "is_nyse_session", lambda day: True)
    monkeypatch.setattr(refresh, "_now_et", lambda: NOW_OK)
    hist = tmp_path / "history"
    hist.mkdir()
    symbols = tmp_path / "symbols.txt"
    symbols.write_text("AMD\n")
    code = refresh.main([
        "--session", SESSION, "--symbols", str(symbols), "--history-dir", str(hist),
        "--output-dir", str(tmp_path / "out"), "--root", str(tmp_path / "archive")])
    assert code == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["mode"] == "dry_run" and manifest["runnable"] is True
    assert not (tmp_path / "out").exists()


def test_cli_capture_refuses_without_explicit_budgets(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "is_nyse_session", lambda day: True)
    monkeypatch.setattr(refresh, "_now_et", lambda: NOW_OK)
    hist = tmp_path / "history"
    hist.mkdir()
    symbols = tmp_path / "symbols.txt"
    symbols.write_text("AMD\n")
    code = refresh.main([
        "--session", SESSION, "--symbols", str(symbols), "--history-dir", str(hist),
        "--output-dir", str(tmp_path / "out"), "--root", str(tmp_path / "archive"),
        "--capture"])
    assert code == 2
    assert not (tmp_path / "out").exists()


def test_real_calendar_accepts_session_and_rejects_holiday():
    assert refresh.is_nyse_session("2026-10-19")
    assert not refresh.is_nyse_session("2026-07-03")
    assert not refresh.is_nyse_session("2026-10-18")


def test_receipt_scan_bound_applies_per_selected_day(tmp_path, monkeypatch):
    root = tmp_path / "archive"
    for day in ["2026-10-15", "2026-10-16", "2026-10-17"]:
        seed_receipt(root, "AMD", day, day + "T05:00:00Z")
    monkeypatch.setattr(refresh, "MAX_RECEIPT_FILES", 1)
    found, stats = refresh.index_receipts(root, {"2026-10-15", "2026-10-16"})
    assert len(found) == 2 and stats["days"] == 2 and stats["files"] == 2


@pytest.mark.parametrize("observed", [None, 42, {}, "invalid"])
def test_malformed_prior_observation_is_reported_not_crashed(tmp_path, observed):
    history = tmp_path / "AMD.json"
    history.write_text(json.dumps({"schema": HISTORY_SCHEMA, "symbol": "AMD", "bars": [],
        "receipts": [{"receipt_id": "a" * 64, "observed_at_utc": observed}]}))
    assert refresh._prior_history(history, "AMD") == (None, None, "prior_history_receipt_invalid")


def test_unavailable_ticker_does_not_retry_or_suppress_other_tickers(tmp_path):
    from collectors.tiingo_archive import TiingoArchiveError
    archive = FakeArchive(tmp_path / "archive")
    calls = []
    normal = Fetcher()
    def fetch(path, key, *, max_bytes):
        calls.append(path)
        if "/NVDA/" in path:
            raise TiingoArchiveError("Tiingo HTTP 404; source not admitted")
        return normal(path, key, max_bytes=max_bytes)
    cfg = make_cfg(tmp_path, ["AMD", "NVDA", "TSLA"])
    manifest, code = refresh.run_refresh(cfg, make_deps(archive, fetch))
    assert code == 3
    assert len(calls) == 3
    assert [o["symbol"] for o in manifest["outputs"]] == ["AMD", "TSLA"]
    assert manifest["not_requested"] == []
    assert [o["symbol"] for o in manifest["unavailable"]] == ["NVDA"]


def test_real_same_session_revision_and_cancellation_replace_the_window(tmp_path, monkeypatch):
    import collectors.tiingo_archive as archive_module
    monkeypatch.setattr(archive_module, "EXTERNAL_MOUNT", tmp_path)
    observed = ["2026-10-19T09:00:00Z"]
    monkeypatch.setattr(archive_module, "utc_now", lambda: observed[0])
    row = {"date": "2026-10-19T02:00:00Z", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 13}
    payload = [[row]]
    deps = refresh.RefreshDeps(
        archive_factory=lambda root, **_: archive_module.Archive(root, check_mount=False, free_floor=0),
        fetch=lambda *a, **kw: (json.dumps(payload[0]).encode(), "application/json"), read_key=lambda: "fixture",
        clock=lambda: datetime.fromisoformat(observed[0].replace("Z", "+00:00")))
    previous = None
    for index, volume in enumerate([13, 9, None]):
        observed[0] = f"2026-10-19T{9 + index:02d}:00:00Z"
        payload[0] = [] if volume is None else [{**row, "volume": volume}]
        cfg = make_cfg(tmp_path, ["AMD"], name=f"revision{index}", history_dir=previous)
        cfg.check_mount = False
        result, code = refresh.run_refresh(cfg, deps)
        assert code == 0, result
        doc = json.loads((cfg.output_dir / "AMD.json").read_text())
        assert doc["bars"] == ([] if volume is None else [[1792375200, 10., 12., 9., 11., float(volume)]])
        assert len(doc["receipts"]) == 1
        previous = cfg.output_dir


def test_attempt_is_durable_before_call_and_crash_cannot_replay(tmp_path):
    cfg = make_cfg(tmp_path, ["AMD"])
    archive = FakeArchive(cfg.root)
    def interrupted(path, key, **kwargs):
        assert json.loads((cfg.output_dir / "attempt-00001.json").read_text())["request_path"] == path
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        refresh.run_refresh(cfg, make_deps(archive, interrupted))
    assert (cfg.output_dir / "start-receipt.json").exists()
    assert not (cfg.output_dir / "captured-00001.json").exists()
    with pytest.raises(refresh.RefreshRefused, match="no silent replay"):
        refresh.run_refresh(cfg, make_deps(archive, Fetcher()))


def test_real_pipeline_empty_then_nonempty_then_append_preserves_prior(tmp_path, monkeypatch):
    import collectors.tiingo_archive as archive_module
    monkeypatch.setattr(archive_module, "EXTERNAL_MOUNT", tmp_path)
    observed = ["2026-10-19T09:00:00Z"]
    monkeypatch.setattr(archive_module, "utc_now", lambda: observed[0])
    response = [b"[]"]
    calls = []
    def fetch(path, key, *, max_bytes):
        calls.append(path)
        return response[0], "application/json"
    deps = refresh.RefreshDeps(
        archive_factory=lambda root, **_: archive_module.Archive(root, check_mount=False, free_floor=0),
        fetch=fetch, read_key=lambda: "fixture",
        clock=lambda: datetime.fromisoformat(observed[0].replace("Z", "+00:00")))
    cfg = make_cfg(tmp_path, ["AMD"], name="day1")
    cfg.check_mount = False
    manifest, code = refresh.run_refresh(cfg, deps)
    assert code == 0 and manifest["outputs"][0]["status"] == "vendor_empty"
    assert not (cfg.output_dir / "AMD.json").exists()
    empty_id = manifest["outputs"][0]["new_receipt"]
    old_output = cfg.output_dir
    observed[0] = "2026-10-20T09:00:00Z"
    response[0] = json.dumps([{"date": "2026-10-20T02:00:00Z", "open": 10,
        "high": 12, "low": 9, "close": 11, "volume": 13}]).encode()
    cfg = make_cfg(tmp_path, ["AMD"], name="day2", history_dir=old_output)
    cfg.session = "2026-10-20"
    cfg.check_mount = False
    manifest, code = refresh.run_refresh(cfg, deps)
    assert code == 0, manifest
    prior_bytes = (cfg.output_dir / "AMD.json").read_bytes()
    one = json.loads(prior_bytes)
    assert len(one["bars"]) == 1
    assert one["bars"][0][1:] == [10., 12., 9., 11., 13.]
    assert empty_id not in [r["receipt_id"] for r in one["receipts"]]
    old_output = cfg.output_dir
    observed[0] = "2026-10-21T09:00:00Z"
    response[0] = response[0].replace(b"2026-10-20", b"2026-10-21")
    cfg = make_cfg(tmp_path, ["AMD"], name="day3", history_dir=old_output)
    cfg.session = "2026-10-21"
    cfg.check_mount = False
    manifest, code = refresh.run_refresh(cfg, deps)
    assert code == 0, manifest
    two = json.loads((cfg.output_dir / "AMD.json").read_bytes())
    assert len(two["bars"]) == 2 and len(two["receipts"]) == 2
    assert two["bars"][0] == one["bars"][0]
    assert two["complete"] is False
    assert (old_output / "AMD.json").read_bytes() == prior_bytes
    assert len(calls) == 3
