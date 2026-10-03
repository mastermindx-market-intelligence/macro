from __future__ import annotations

import hashlib
import json
import logging
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts.collect_nowcast_vintages import NOWCAST_SERIES, collect_nowcast_vintages


def _updates(series_id: str) -> pd.DataFrame:
    assert series_id == "GDPNOW"
    return pd.DataFrame([
        {"period": "2026-07-01", "realtime_start": "2026-07-30",
         "realtime_end": "2026-08-02", "value": 2.3},
        {"period": "2026-07-01", "realtime_start": "2026-08-03",
         "realtime_end": "2026-08-06", "value": 2.1},
        {"period": "2026-07-01", "realtime_start": "2026-08-07",
         "realtime_end": "9999-12-31", "value": 2.5},
    ])


def test_preserves_intraquarter_update_path_with_hash_bound_manifest(tmp_path: Path):
    receipt = collect_nowcast_vintages(
        repo_root=tmp_path, api_key="test-key",
        fetcher=lambda **kw: _updates(kw["series_id"]),
    )
    target = tmp_path / "data/fred_vintage/nowcast_vintages"
    output = target / "GDPNOW_all_vintages.parquet"
    stored = pd.read_parquet(output)
    manifest = json.loads((target / "manifest.json").read_text())

    assert receipt["status"] == "ok"
    assert receipt["schema"] == "nowcast_vintage_collection.v1"
    assert receipt["series"]["GDPNOW"]["rows"] == 3
    assert receipt["series"]["GDPNOW"]["periods"] == 1
    assert receipt["series"]["GDPNOW"]["release_dates"] == 3
    assert stored["realtime_start"].nunique() == 3
    assert stored["period"].nunique() == 1
    assert set(stored["source_output_type"]) == {2}
    assert manifest["series"]["GDPNOW"]["artifact_sha256"] == hashlib.sha256(
        output.read_bytes()).hexdigest()


def test_nowcast_cohort_does_not_touch_other_fred_cohorts_or_cpi_completion(tmp_path: Path):
    sentinels = [
        tmp_path / "data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet",
        tmp_path / "data/fred_vintage/cycle_vintages/INDPRO_all_vintages.parquet",
        tmp_path / "data/release_forecast/cpi_truth/build_completion.json",
    ]
    for p in sentinels:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"unchanged")

    collect_nowcast_vintages(
        repo_root=tmp_path, api_key="test-key",
        fetcher=lambda **kw: _updates(kw["series_id"]),
    )
    assert all(p.read_bytes() == b"unchanged" for p in sentinels)


def test_dry_run_fetches_and_validates_but_writes_nothing(tmp_path: Path):
    receipt = collect_nowcast_vintages(
        repo_root=tmp_path, api_key="test-key", dry_run=True,
        fetcher=lambda **kw: _updates(kw["series_id"]),
    )
    assert receipt["status"] == "dry_run"
    assert receipt["series"]["GDPNOW"]["rows"] == 3
    assert receipt["series"]["GDPNOW"]["release_dates"] == 3
    assert not (tmp_path / "data").exists()


def test_unsupported_series_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="unsupported collector series 'CPIAUCSL'"):
        collect_nowcast_vintages(
            repo_root=tmp_path, series_ids=["CPIAUCSL"], api_key="test-key",
            fetcher=lambda **kw: _updates(kw["series_id"]),
        )
    assert not (tmp_path / "data").exists()


def test_missing_key_is_nowcast_specific_and_nonmutating(tmp_path: Path, caplog):
    with caplog.at_level(logging.WARNING, logger="scripts.collect_release_target_vintages"):
        receipt = collect_nowcast_vintages(
            repo_root=tmp_path, api_key="",
            fetcher=lambda **_: pytest.fail("fetcher must not run"),
        )
    assert receipt["status"] == "skipped"
    assert receipt["reason"] == "missing_fred_api_key"
    assert "nowcast_vintages" in caplog.text
    assert not (tmp_path / "data").exists()


def test_cli_threads_series_realtime_start_and_dry_run(monkeypatch):
    recorded = {}

    def fake(**kwargs):
        recorded.update(kwargs)
        return {"status": "dry_run"}

    monkeypatch.setattr(
        "scripts.collect_release_target_vintages.collect_release_target_vintages", fake)
    monkeypatch.setattr(sys, "argv", [
        "collect-nowcast-vintages", "--series", "GDPNOW",
        "--realtime-start", "2014-01-01", "--dry-run",
    ])
    runpy.run_module("scripts.collect_nowcast_vintages", run_name="__main__")

    assert recorded["series_ids"] == ["GDPNOW"]
    assert recorded["realtime_start"] == "2014-01-01"
    assert recorded["dry_run"] is True
