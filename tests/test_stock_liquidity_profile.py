"""Actual one-record stock-library output and raw-source refusal boundaries."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.stock_liquidity_profile import MAX_SOURCE_BYTES, MAX_SOURCE_ROWS, read_profile, write_record

NOW = datetime(2026, 10, 20, 4, 0, tzinfo=timezone.utc)


def test_engine_materializes_the_existing_raw_store_before_the_stock_builder():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["engine"]["steps"]
    restores = [i for i, step in enumerate(steps)
                if "scripts.fetch_r2 --dirs massive_stock_day" in step.get("run", "")]
    builders = [i for i, step in enumerate(steps)
                if "scripts/ci/daily_engine_regime_dashboard.sh" in step.get("run", "")]
    assert len(restores) == 1
    assert builders and restores[0] < min(builders)
    assert set(steps[restores[0]]["env"]) == {
        "R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"}
    assert "collect" not in steps[restores[0]]["run"]


def test_existing_writer_emits_unknown_without_altering_legacy_fields(tmp_path):
    rec = {"ticker": "MU", "asof": "2026-10-14", "tech": {"price": 123},
           "conviction": {"score": 73}, "adv_dollar_21d": 1234567,
           "days_to_exit_at_10pct_adv": 0.8}
    before = copy.deepcopy(rec)
    out = tmp_path / "MU.json"
    write_record(out, rec, data_root=tmp_path / "data", recorded_at=NOW)
    emitted = json.loads(out.read_text())
    profile = emitted.pop("liquidity_profile")
    assert emitted == before
    assert profile["status"] == "READ_NO_COVERAGE"
    assert profile["metrics"] is None
    assert profile["thinly_traded"] is None
    assert profile["known_at"] is None
    assert not (tmp_path / "data").exists()  # no implicit source restoration


@pytest.mark.parametrize("ticker", ["../MU", "/MU", "MU/OTHER", "", "MU\\OTHER"])
def test_no_ticker_path_traversal(tmp_path, ticker):
    result = read_profile(ticker, data_root=tmp_path, recorded_at=NOW)
    assert result["status"] == "READ_NO_COVERAGE"
    assert result["reason"] == "IDENTITY_NOT_COVERED"
    assert list(tmp_path.iterdir()) == []


def test_unreadable_raw_file_does_not_fall_back_to_adjusted_store(tmp_path):
    raw = tmp_path / "massive_stock_day"
    raw.mkdir()
    (raw / "MU.parquet").write_bytes(b"not a parquet")
    adjusted = tmp_path / "stocks"
    adjusted.mkdir()
    pd.DataFrame({"close": [10.0] * 25, "volume": [1e7] * 25},
                 index=pd.date_range("2026-09-14", periods=25, freq="B")).to_parquet(adjusted / "MU.parquet")
    result = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert result["status"] == "READ_UNAVAILABLE"
    assert result["reason"] == "SOURCE_UNREADABLE"
    assert result["metrics"] is None


def test_source_file_bound_is_enforced_before_decode(tmp_path):
    root = tmp_path / "massive_stock_day"
    root.mkdir()
    with (root / "MU.parquet").open("wb") as out:
        out.truncate(MAX_SOURCE_BYTES + 1)
    result = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert result["reason"] == "SOURCE_OVER_BOUND"
    assert result["metrics"] is None


def test_symlink_source_is_not_a_native_ticker_file(tmp_path):
    root = tmp_path / "massive_stock_day"
    root.mkdir()
    (root / "MU.parquet").symlink_to(tmp_path / "other")
    result = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert result["reason"] == "SOURCE_NOT_REGULAR"


def test_small_encoded_file_with_excessive_decoded_rows_is_refused(tmp_path):
    root = tmp_path / "massive_stock_day"
    root.mkdir()
    p = root / "MU.parquet"
    pd.DataFrame({"close": [10.0] * (MAX_SOURCE_ROWS + 1),
                  "volume": [1] * (MAX_SOURCE_ROWS + 1)}).to_parquet(p)
    assert p.stat().st_size < MAX_SOURCE_BYTES
    result = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert result["reason"] == "SOURCE_OVER_BOUND"
    assert result["metrics"] is None


def test_current_raw_bars_do_not_invent_window_currency_or_ingestion(tmp_path):
    from lib import nyse_calendar
    days = [d for d in pd.date_range("2026-09-01", "2026-10-19")
            if nyse_calendar.is_session(d.date())][-20:]
    root = tmp_path / "massive_stock_day"
    root.mkdir()
    p = root / "MU.parquet"
    pd.DataFrame({"close": [100.0] * 20, "volume": [1e6] * 20}, index=days).to_parquet(p)
    (root / "_manifest.json").write_text(json.dumps({"updated_at": "2026-10-20T03:00:00+00:00"}))
    result = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert result["metrics"] is None
    assert result["thinly_traded"] is None
    assert result["source_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert result["store_updated_at"] == "2026-10-20T03:00:00+00:00"
    assert result["ingested_at"] is None
    assert result["known_at"] is None
    json.dumps(result, allow_nan=False)


def test_native_zero_filled_volume_does_not_become_qualified_activity(tmp_path):
    from lib import nyse_calendar
    days = [d for d in pd.date_range("2026-09-01", "2026-10-19")
            if nyse_calendar.is_session(d.date())][-20:]
    root = tmp_path / "massive_stock_day"
    root.mkdir()
    volume = [1e6] * 20
    volume[-1] = 0  # producer may have filled a missing source value
    pd.DataFrame({"close": [100.0] * 20, "volume": volume}, index=days).to_parquet(root / "MU.parquet")
    result = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert result["status"] == "READ_NO_COVERAGE"
    assert result["reason"] == "ZERO_VOLUME_SOURCE_AMBIGUOUS"
    assert result["metrics"] is None and result["thinly_traded"] is None


def test_source_availability_window_is_not_completed_market_cutoff(tmp_path):
    from engine.liquidity_profile import _expected_sessions
    from datetime import date
    days = _expected_sessions(date(2026, 10, 16), 20)
    root = tmp_path / "massive_stock_day"
    root.mkdir()
    pd.DataFrame({"close": [100.0]*20, "volume": [1000000]*20},
                 index=pd.DatetimeIndex(days)).to_parquet(root / "MU.parquet")
    early = read_profile("MU", data_root=tmp_path, recorded_at=NOW)
    assert early["reason"] == "CURRENCY_NOT_QUALIFIED"
    assert early["expected_session"] == "2026-10-16"
    assert early["availability"]["market_completed_session"] == "2026-10-19"
    assert early["availability"]["source_expected_session"] == "2026-10-16"
    late = read_profile("MU", data_root=tmp_path,
                        recorded_at=datetime(2026,10,20,15,tzinfo=timezone.utc))
    assert late["reason"] == "STALE_NO_EXPECTED_SESSION"
    assert late["metrics"] is None


def test_observed_newer_completed_file_is_usable_before_scheduled_floor(tmp_path):
    from engine.liquidity_profile import _expected_sessions
    from datetime import date
    days = _expected_sessions(date(2026,10,19),20)
    root = tmp_path / "massive_stock_day"; root.mkdir()
    pd.DataFrame({"close":[100.0]*20,"volume":[1000000]*20},index=pd.DatetimeIndex(days)).to_parquet(root / "MU.parquet")
    result=read_profile("MU",data_root=tmp_path,recorded_at=NOW)
    assert result["reason"] == "CURRENCY_NOT_QUALIFIED"
    assert result["expected_session"] == "2026-10-19"
    assert result["availability"]["source_expected_session"] == "2026-10-16"


@pytest.mark.parametrize("clock", [None, datetime(2026,10,20)])
def test_reader_clock_refusal_does_not_guess_timezone_or_raise(tmp_path, clock):
    result=read_profile("MU", data_root=tmp_path, recorded_at=clock)
    assert result["status"] == "READ_UNAVAILABLE"
    assert result["metrics"] is None and result["recorded_at"] is None


@pytest.fixture
def native_adoption(tmp_path, monkeypatch):
    from scripts import stock_liquidity_profile as module
    site, served = tmp_path / "site", tmp_path / "site.served"
    for directory, generation in [(site, "native"), (served, "served")]:
        (directory / "stockdata").mkdir(parents=True)
        path = directory / "stockdata" / "MU.json"
        path.write_text(json.dumps({"ticker": "MU", "asof": "2026-10-14",
                                   "ladder": generation, "sector_pulse": {"generation": generation}}))
        path.chmod(0o644)
        (directory / "stockdata" / "OTHER.json").write_text('{"untouched":true}')
    lock = tmp_path / "macro-update.lock"
    lock.touch()
    monkeypatch.setattr(module, "read_profile", lambda *a, **k: {
        "schema": "liquidity_profile.v1", "ticker": "MU", "status": "READ_OK",
        "sample_n": 20, "thinly_traded": False})
    args = dict(data_root=tmp_path / "data", site_root=site, served_root=served,
                lock_path=lock, recorded_at=NOW)
    return module, args


def test_native_adoption_uses_real_atomic_publisher_preserving_both_generations(native_adoption):
    module, args = native_adoption
    before = {name: (args[key] / "stockdata" / "MU.json").read_bytes()
              for name, key in [("native", "site_root"), ("served", "served_root")]}
    result = module.adopt_native_profile("MU", **args)
    assert result["status"] == "NATIVE_PROFILE_PUBLISHED"
    assert result["published"] == ["native", "served"]
    for name, key in [("native", "site_root"), ("served", "served_root")]:
        path = args[key] / "stockdata" / "MU.json"
        output = json.loads(path.read_bytes())
        profile = output.pop("liquidity_profile")
        assert output == json.loads(before[name])
        assert profile == result["profile"]
        assert path.stat().st_mode & 0o777 == 0o644
        assert result["records"][name]["unrelated_fields_preserved"] == 4
        assert (path.parent / "OTHER.json").read_text() == '{"untouched":true}'


def test_native_adoption_respects_the_existing_release_lock(native_adoption):
    import fcntl
    module, args = native_adoption
    before = (args["site_root"] / "stockdata/MU.json").read_bytes()
    with args["lock_path"].open("a+") as incumbent:
        fcntl.flock(incumbent, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert module.adopt_native_profile("MU", **args)["reason"] == "RELEASE_BUSY"
    assert (args["site_root"] / "stockdata/MU.json").read_bytes() == before


@pytest.mark.parametrize("fault", ["missing", "symlink", "identity", "malformed"])
def test_native_adoption_qualifies_both_records_before_effects(native_adoption, fault):
    module, args = native_adoption
    source = args["site_root"] / "stockdata/MU.json"
    before = source.read_bytes()
    target = args["served_root"] / "stockdata/MU.json"
    if fault == "missing":
        target.unlink()
    elif fault == "symlink":
        target.unlink(); target.symlink_to(source)
    elif fault == "identity":
        target.write_text('{"ticker":"OTHER"}')
    else:
        target.write_text("not json")
    result = module.adopt_native_profile("MU", **args)
    assert result["status"] == "REFUSED" and result["published"] == []
    assert source.read_bytes() == before


def test_native_adoption_does_not_publish_unknown(native_adoption, monkeypatch):
    module, args = native_adoption
    monkeypatch.setattr(module, "read_profile", lambda *a, **k: {
        "ticker": "MU", "status": "READ_NO_COVERAGE", "thinly_traded": None})
    before = (args["site_root"] / "stockdata/MU.json").read_bytes()
    assert module.adopt_native_profile("MU", **args)["reason"] == "NATIVE_PROFILE_NOT_QUALIFIED"
    assert (args["site_root"] / "stockdata/MU.json").read_bytes() == before


def test_native_adoption_preserves_an_advancing_native_writer(native_adoption, monkeypatch):
    module, args = native_adoption
    original = module.write_record
    source = args["site_root"] / "stockdata/MU.json"
    def advance(*a, **k):
        original(*a, **k)
        source.write_text('{"ticker":"MU","newer_generation":true}')
    monkeypatch.setattr(module, "write_record", advance)
    result = module.adopt_native_profile("MU", **args)
    assert result["reason"] == "NATIVE_RECORD_ADVANCED" and result["published"] == []
    assert json.loads(source.read_text())["newer_generation"] is True


def test_native_adoption_retains_unknown_atomic_effect_without_retry(native_adoption, monkeypatch):
    import subprocess
    module, args = native_adoption
    calls = []
    def timeout(command, **kwargs):
        calls.append(command)
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", timeout)
    result = module.adopt_native_profile("MU", **args)
    assert result["status"] == "EFFECT_UNKNOWN" and result["reason"] == "ATOMIC_PUBLISH_TIMEOUT"
    assert result["published"] == [] and result["active_target"] == "native"
    assert len(result["planned_records"]["native"]["candidate_sha256"]) == 64
    assert len(calls) == 1


def test_native_adoption_reports_partial_instead_of_retrying_the_other_record(native_adoption, monkeypatch):
    import subprocess
    module, args = native_adoption
    original_run = subprocess.run
    calls = []
    def fail_second(command, **kwargs):
        calls.append(command)
        return original_run(command, **kwargs) if len(calls) == 1 else subprocess.CompletedProcess(command, 1)
    monkeypatch.setattr(subprocess, "run", fail_second)
    result = module.adopt_native_profile("MU", **args)
    assert result["status"] == "EFFECT_UNKNOWN" and result["reason"] == "ATOMIC_PUBLISH_FAILED"
    assert result["published"] == ["native"] and result["active_target"] == "served"
    assert len(result["planned_records"]["served"]["before_sha256"]) == 64
    assert len(calls) == 2
    assert "liquidity_profile" in json.loads((args["site_root"] / "stockdata/MU.json").read_text())
    assert "liquidity_profile" not in json.loads((args["served_root"] / "stockdata/MU.json").read_text())


def test_native_adoption_preserves_unverified_write_as_unknown(native_adoption, monkeypatch):
    import subprocess
    module, args = native_adoption
    calls = []
    def pretend_success(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(subprocess, "run", pretend_success)
    result = module.adopt_native_profile("MU", **args)
    assert result["status"] == "EFFECT_UNKNOWN"
    assert result["reason"] == "ATOMIC_PUBLISH_NOT_VERIFIED"
    assert result["active_target"] == "native" and result["published"] == []
    assert len(calls) == 1 and result["planned_records"]["native"]["candidate_sha256"]
