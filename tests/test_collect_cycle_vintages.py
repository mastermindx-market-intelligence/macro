from __future__ import annotations

import hashlib
import json
import logging
import runpy
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts.collect_cycle_vintages import CYCLE_SERIES, collect_cycle_vintages


def _frame(series_id: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "period": "2025-01-01",
                "realtime_start": "2025-02-01",
                "realtime_end": "9999-12-31",
                "value": 100.0,
            }
        ]
    )


def _fetcher(**kwargs):
    return _frame(kwargs["series_id"])


def test_collects_exact_cycle_cohort_with_hash_bound_manifest(tmp_path: Path):
    receipt = collect_cycle_vintages(
        repo_root=tmp_path,
        api_key="test-key",
        fetcher=_fetcher,
    )

    target_dir = tmp_path / "data/fred_vintage/cycle_vintages"
    assert receipt["status"] == "ok"
    assert receipt["schema"] == "cycle_vintage_collection.v1"
    assert {path.name for path in target_dir.glob("*")} == {
        *(f"{series_id}_all_vintages.parquet" for series_id in CYCLE_SERIES),
        "manifest.json",
    }
    manifest = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "cycle_vintage_collection.v1"
    for series_id in CYCLE_SERIES:
        output = target_dir / f"{series_id}_all_vintages.parquet"
        stored = pd.read_parquet(output)
        assert set(stored["series"]) == {series_id}
        assert set(stored["source_output_type"]) == {2}
        assert manifest["series"][series_id]["artifact_sha256"] == hashlib.sha256(
            output.read_bytes()
        ).hexdigest()
        assert manifest["series"][series_id]["artifact_bytes"] == (
            output.stat().st_size
        )


def test_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    receipt = collect_cycle_vintages(
        repo_root=tmp_path,
        api_key="test-key",
        dry_run=True,
        fetcher=_fetcher,
    )

    assert receipt["status"] == "dry_run"
    assert not (tmp_path / "data").exists()


def test_unsupported_series_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="unsupported collector series 'CPIAUCSL'"):
        collect_cycle_vintages(
            repo_root=tmp_path,
            series_ids=["CPIAUCSL"],
            api_key="test-key",
            fetcher=_fetcher,
        )
    assert not (tmp_path / "data").exists()


def test_release_target_store_is_untouched(tmp_path: Path):
    release_target_dir = tmp_path / "data/fred_vintage/release_targets"
    release_target_dir.mkdir(parents=True)
    sentinel = release_target_dir / "CPIAUCSL_all_vintages.parquet"
    sentinel.write_bytes(b"unchanged")

    collect_cycle_vintages(
        repo_root=tmp_path,
        api_key="test-key",
        fetcher=_fetcher,
    )

    assert sentinel.read_bytes() == b"unchanged"
    assert list(release_target_dir.iterdir()) == [sentinel]


def test_cycle_collection_preserves_cpi_completion_boundary(tmp_path: Path):
    completion = tmp_path / "data/release_forecast/cpi_truth/build_completion.json"
    completion.parent.mkdir(parents=True)
    completion.write_bytes(b'{"prior_completion":true}\n')

    receipt = collect_cycle_vintages(
        repo_root=tmp_path,
        api_key="test-key",
        fetcher=_fetcher,
    )

    assert receipt["status"] == "ok"
    assert completion.read_bytes() == b'{"prior_completion":true}\n'


def test_missing_key_uses_a_cycle_specific_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(
        logging.WARNING, logger="scripts.collect_release_target_vintages"
    ):
        receipt = collect_cycle_vintages(
            repo_root=tmp_path,
            api_key="",
            fetcher=lambda **_kwargs: pytest.fail("fetcher must not run"),
        )

    assert receipt["status"] == "skipped"
    assert caplog.record_tuples == [
        (
            "scripts.collect_release_target_vintages",
            logging.WARNING,
            "[cycle_vintages] The FRED API key is absent, so the cycle vintage stores are untouched.",
        )
    ]


def test_cli_passes_series_realtime_start_and_dry_run(
    monkeypatch: pytest.MonkeyPatch,
):
    recorded = {}

    def fake_collect_release_target_vintages(**kwargs):
        recorded.update(
            {
                "series_ids": kwargs["series_ids"],
                "realtime_start": kwargs["realtime_start"],
                "dry_run": kwargs["dry_run"],
            }
        )
        return {"status": "dry_run"}

    monkeypatch.setattr(
        "scripts.collect_release_target_vintages.collect_release_target_vintages",
        fake_collect_release_target_vintages,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "collect-cycle-vintages",
            "--series",
            "NEWORDER",
            "ISRATIO",
            "--realtime-start",
            "1999-02-03",
            "--dry-run",
        ],
    )

    runpy.run_module("scripts.collect_cycle_vintages", run_name="__main__")

    assert recorded["series_ids"] == ["NEWORDER", "ISRATIO"]
    assert recorded["realtime_start"] == "1999-02-03"
    assert recorded["dry_run"] is True


def test_cli_without_a_key_skips_cleanly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    repo_root = Path(__file__).resolve().parents[1]
    environment = {"PYTHONPATH": str(repo_root), "PATH": "/usr/bin:/bin"}

    completed = subprocess.run(
        [sys.executable, "-m", "scripts.collect_cycle_vintages"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    manifest = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert manifest["status"] == "skipped"
    assert manifest["reason"] == "missing_fred_api_key"
    assert "[cycle_vintages] The FRED API key is absent" in completed.stderr
    assert not (tmp_path / "data").exists()


def test_missing_key_skips_cleanly_and_writes_no_files(tmp_path: Path):
    receipt = collect_cycle_vintages(
        repo_root=tmp_path,
        api_key="",
        fetcher=lambda **_kwargs: pytest.fail("fetcher must not run"),
    )

    assert receipt["status"] == "skipped"
    assert receipt["reason"] == "missing_fred_api_key"
    assert not (tmp_path / "data").exists()
