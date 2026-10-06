"""I/O wrapper tests for the exact qbus news universe snapshot."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pytest

from scripts import build_qbus_news_universe as cli


UTC = timezone.utc
NOW = datetime(2026, 10, 5, 22, 0, tzinfo=UTC)


def _fixtures(root):
    breadth = root / "breadth"
    ref = root / "reference"
    breadth.mkdir(parents=True)
    ref.mkdir(parents=True)

    pd.DataFrame(
        [
            {"symbol": "NVDA", "name": "NVIDIA", "sector": "Technology"},
            {"symbol": "MMC", "name": "Marsh McLennan", "sector": "Financials"},
        ]
    ).set_index("symbol").to_parquet(breadth / "constituents.parquet")

    pd.DataFrame(
        [
            {"ticker": "NVDA", "start_date": "2001-01-01", "end_date": None, "src": "sp500"},
            {"ticker": "MMC", "start_date": "2003-01-01", "end_date": None, "src": "sp500"},
            {"ticker": "OLD", "start_date": "1990-01-01", "end_date": "2020-01-01", "src": "sp500"},
        ]
    ).to_parquet(breadth / "sp1500_pit_membership.parquet", index=False)

    pd.DataFrame(
        [
            {"vendor": "membership", "vendor_symbol": "NVDA", "security_id": "SEC:US-XNAS-NVDA", "valid_from": None, "valid_to": None},
            {"vendor": "yahoo_fetch", "vendor_symbol": "NVDA", "security_id": "SEC:US-XNAS-NVDA", "valid_from": None, "valid_to": None},
            {"vendor": "membership", "vendor_symbol": "MMC", "security_id": "SEC:US-XNYS-MMC", "valid_from": None, "valid_to": None},
            {"vendor": "yahoo_fetch", "vendor_symbol": "MRSH", "security_id": "SEC:US-XNYS-MMC", "valid_from": None, "valid_to": None},
        ]
    ).to_parquet(ref / "vendor_aliases.parquet", index=False)

    pd.DataFrame(
        [
            {
                "security_id": "SEC:US-XNAS-NVDA",
                "issuer_id": "ISS:US-XNAS-NVDA",
                "issuer_state": "RESOLVED",
                "listing_key": "US-XNAS-NVDA",
                "security_state": None,
                "superseded_by": None,
                "issuer_cik": None,
            },
            {
                "security_id": "SEC:US-XNYS-MMC",
                "issuer_id": "ISS:US-XNYS-MMC",
                "issuer_state": "RESOLVED",
                "listing_key": "US-XNYS-MMC",
                "security_state": None,
                "superseded_by": None,
                "issuer_cik": None,
            },
        ]
    ).to_parquet(ref / "security_master.parquet", index=False)

    return {
        "current": breadth / "constituents.parquet",
        "pit": breadth / "sp1500_pit_membership.parquet",
        "aliases": ref / "vendor_aliases.parquet",
        "security": ref / "security_master.parquet",
    }


def test_check_only_reads_owners_and_does_not_create_output(tmp_path):
    paths = _fixtures(tmp_path / "data")
    out = tmp_path / "qbus" / "news_universe.json"

    report = cli.build_from_files(
        **paths,
        output=out,
        observed_at=NOW,
        fresh_for=timedelta(hours=36),
        min_count=1,
        write=False,
    )

    assert report["mode"] == "check_only"
    assert report["qualified"] is True
    assert report["count"] == 2
    assert report["revision"].startswith("sp500-news-")
    assert not out.exists()


def test_write_atomically_publishes_qualified_snapshot_without_mutating_sources(tmp_path):
    paths = _fixtures(tmp_path / "data")
    out = tmp_path / "qbus" / "news_universe.json"
    before = {key: path.read_bytes() for key, path in paths.items()}

    report = cli.build_from_files(
        **paths,
        output=out,
        observed_at=NOW,
        fresh_for=timedelta(hours=36),
        min_count=1,
        write=True,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert report["mode"] == "write"
    assert report["qualified"] is True
    assert payload["revision"] == report["revision"]
    assert payload["owner"] == "breadth.sp500+reference.security_master"
    assert [x["ticker"] for x in payload["securities"]] == ["MMC", "NVDA"]
    assert {key: path.read_bytes() for key, path in paths.items()} == before
    assert list(out.parent.glob(".news_universe.json.*.tmp")) == []


def test_wrapper_normalizes_pandas_nat_and_nan_to_none(tmp_path):
    paths = _fixtures(tmp_path / "data")
    aliases = pd.read_parquet(paths["aliases"])
    aliases["valid_from"] = pd.NaT
    aliases["valid_to"] = pd.NaT
    aliases.to_parquet(paths["aliases"], index=False)

    report = cli.build_from_files(
        **paths,
        output=tmp_path / "out.json",
        observed_at=NOW,
        min_count=1,
        write=False,
    )
    assert report["qualified"] is True


def test_wrapper_refuses_missing_or_unreadable_owner_artifact(tmp_path):
    paths = _fixtures(tmp_path / "data")
    paths["aliases"].unlink()

    with pytest.raises(cli.NewsUniverseBuildError) as exc:
        cli.build_from_files(
            **paths,
            output=tmp_path / "out.json",
            observed_at=NOW,
            min_count=1,
            write=False,
        )
    assert exc.value.code == "owner_artifact_unreadable"


def test_cli_defaults_to_check_only_and_emits_metadata_not_roster(monkeypatch, tmp_path, capsys):
    paths = _fixtures(tmp_path / "data")
    out = tmp_path / "qbus" / "news_universe.json"

    rc = cli.main(
        [
            "--current", str(paths["current"]),
            "--pit", str(paths["pit"]),
            "--aliases", str(paths["aliases"]),
            "--security-master", str(paths["security"]),
            "--output", str(out),
            "--min-count", "1",
            "--observed-at", NOW.isoformat(),
        ]
    )
    printed = capsys.readouterr().out
    payload = json.loads(printed)

    assert rc == 0
    assert payload["mode"] == "check_only"
    assert payload["count"] == 2
    assert "securities" not in payload
    assert "NVDA" not in printed
    assert not out.exists()


def test_cli_write_requires_explicit_flag(monkeypatch, tmp_path, capsys):
    paths = _fixtures(tmp_path / "data")
    out = tmp_path / "qbus" / "news_universe.json"

    rc = cli.main(
        [
            "--current", str(paths["current"]),
            "--pit", str(paths["pit"]),
            "--aliases", str(paths["aliases"]),
            "--security-master", str(paths["security"]),
            "--output", str(out),
            "--min-count", "1",
            "--observed-at", NOW.isoformat(),
            "--write",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["mode"] == "write"
    assert out.is_file()
