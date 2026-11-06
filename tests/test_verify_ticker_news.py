"""Tests for the reproducible synthetic ticker-news load verifier."""
from __future__ import annotations

import json

from scripts import verify_ticker_news as verify


def test_small_verifier_run_reports_lossless_store_and_reader_metrics(tmp_path):
    report = verify.run_verification(
        database=tmp_path / "qbus.sqlite3",
        sustained_seconds=1,
        sustained_rate=4,
        burst_seconds=1,
        burst_rate=8,
        readers=8,
        security_count=8,
    )

    assert report["schema"] == "ticker_news.synthetic_verification.v1"
    assert report["synthetic_only"] is True
    assert report["load"]["scheduled_revisions"] == 12
    assert report["load"]["committed_revisions"] == 12
    assert report["load"]["dropped_revisions"] == 0
    assert report["load"]["commit_p95_ms"] >= 0
    assert report["load"]["commit_p99_ms"] >= report["load"]["commit_p95_ms"]
    assert report["readers"]["requested"] == 8
    assert report["readers"]["page_limit"] == 20
    assert report["readers"]["completed"] == 8
    assert report["readers"]["failures"] == 0
    assert report["readers"]["snapshot_p95_ms"] >= 0
    assert report["database"]["states"] == 12
    assert report["database"]["revisions"] == 12
    assert report["database"]["changes"] == 12


def test_verifier_pass_gate_uses_engineering_targets_not_hidden_relaxation(tmp_path):
    report = verify.run_verification(
        database=tmp_path / "qbus.sqlite3",
        sustained_seconds=1,
        sustained_rate=3,
        burst_seconds=1,
        burst_rate=5,
        readers=4,
        security_count=4,
        targets=verify.VerificationTargets(
            commit_p95_ms=10_000,
            commit_p99_ms=10_000,
            reader_p95_ms=10_000,
            minimum_service_rate=0.1,
        ),
    )
    assert report["result"]["passed"] is True
    assert report["result"]["targets"] == {
        "commit_p95_ms": 10000.0,
        "commit_p99_ms": 10000.0,
        "reader_p95_ms": 10000.0,
        "minimum_service_rate": 0.1,
    }


def test_verifier_writes_metadata_only_json_receipt(tmp_path):
    database = tmp_path / "qbus.sqlite3"
    output = tmp_path / "evidence" / "load.json"

    report = verify.run_verification(
        database=database,
        sustained_seconds=1,
        sustained_rate=2,
        burst_seconds=1,
        burst_rate=2,
        readers=2,
        security_count=2,
    )
    verify.write_report(output, report)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["schema"] == "ticker_news.synthetic_verification.v1"
    assert "title" not in json.dumps(saved).lower()
    assert "teaser" not in json.dumps(saved).lower()
    assert "body" not in json.dumps(saved).lower()


def test_cli_rejects_nonpositive_load_shape(capsys):
    rc = verify.main(["--sustained-seconds", "0"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["error"] == "invalid_load_shape"


def test_direct_script_invocation_works_from_repo_root(tmp_path):
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_ticker_news.py",
            "--sustained-seconds", "1",
            "--sustained-rate", "1",
            "--burst-seconds", "1",
            "--burst-rate", "1",
            "--readers", "1",
            "--security-count", "1",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode in {0, 1}, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["schema"] == "ticker_news.synthetic_verification.v1"
    assert payload["load"]["scheduled_revisions"] == 2
