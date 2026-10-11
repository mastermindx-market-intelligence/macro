"""A zero-vendor, zero-secret local CLI for bounded Tiingo research studies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import collectors.tiingo_archive as a
from scripts.tiingo_materialize import materialize_one
from scripts.tiingo_research_query import (
    bounded_json, capture_ref, discover, main, query,
)

NOW = "2026-10-09T12:00:00Z"
CUTOFF = "2026-10-10T00:00:00Z"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "tiingo", check_mount=False, free_floor=0)


def partition(lake, source="eod-bars", symbol="AMD", rows=None, *,
              at=NOW, params=None):
    if params is None:
        params = {"startDate": "2019-01-01", "endDate": "2019-12-31"}
        if source == "fund-statements":
            params["asReported"] = "true"
    if rows is None:
        rows = [{"date": "2019-01-02", "close": 5, "volume": 100}]
    resp = lake.store_response(
        source, symbol, a.request_path(source, symbol, params),
        json.dumps(rows, separators=(",", ":")).encode(), received_at=at,
    )
    digest = resp["raw_sha256"]
    rec = next(
        json.loads(p.read_text())
        for p in (lake.root / "receipts").rglob("*.json")
        if json.loads(p.read_text()).get("raw_sha256") == digest
    )
    assert materialize_one(lake.root, rec, free_floor=0)["status"] == "WRITTEN"
    return at[:10], digest


def one_statement(value=42):
    return [{"date": "2020-02-01", "year": 2019, "quarter": 0,
             "statementData": {"incomeStatement": [
                 {"dataCode": "netIncome", "value": value}
             ]}}]


def test_missing_local_archive_is_explicitly_not_data_entitlement(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    root = tmp_path / "no-archive"
    out = discover(root, source="eod-bars", vendor_symbol="AMD", check_mount=False)
    assert out["status"] == "NO_LOCAL_ARCHIVE"
    assert out["archive_exists"] is False
    assert out["verified_candidates"] == []
    assert out["scan_complete"] is False
    assert out["complete_history_proven"] is False
    assert out["network"] is False and out["writes"] is False
    assert not root.exists()


def test_discovery_only_returns_verified_exact_vendor_source(lake):
    wanted = partition(lake)
    partition(lake, symbol="NVDA",
              rows=[{"date": "2019-01-02", "close": 100}])
    out = discover(lake.root, source="eod-bars", vendor_symbol="AMD", check_mount=False)
    assert out["scan_complete"] is True
    assert len(out["verified_candidates"]) == 1
    entry = out["verified_candidates"][0]
    assert (entry["capture_day"], entry["source_sha256"]) == wanted
    assert entry["observed_at_utc"] == NOW
    assert entry["vendor_authenticity_established"] is False
    assert out["historical_identity_admitted"] is False
    assert out["pit_backtest_eligible"] is False
    assert out["redistribution_admitted"] is False


def test_discovery_after_capture_cutoff_does_not_reveal_later_partition(lake):
    partition(lake)
    result = discover(
        lake.root, source="eod-bars", vendor_symbol="AMD",
        observed_before="2026-10-09T11:59:59Z", check_mount=False,
    )
    assert result["verified_candidates"] == []
    assert result["scan_complete"] is True


def test_discovery_truncated_scan_never_calls_corpus_complete(lake):
    partition(lake)
    partition(lake, symbol="NVDA",
              rows=[{"date": "2019-01-03", "close": 100}])
    out = discover(lake.root, source="eod-bars", vendor_symbol="AMD",
                   max_scan=1, check_mount=False)
    assert out["status"] == "PARTIAL_LOCAL_RESEARCH_DISCOVERY"
    assert out["scan_complete"] is False
    assert out["manifests_scanned"] == 1
    assert out["complete_history_proven"] is False


def test_discovery_count_rejects_corrupt_manifest_instead_of_accepting(lake):
    day, sha = partition(lake)
    manifest = lake.root / "manifests" / "eod-bars" / day / (sha + ".json")
    content = json.loads(manifest.read_text())
    content["output_sha256"] = "0" * 64
    manifest.write_text(json.dumps(content))
    out = discover(lake.root, source="eod-bars", vendor_symbol="AMD",
                   check_mount=False)
    assert out["verified_candidates"] == []
    assert out["rejected_local_artifacts"] == 1


def test_fully_explicit_research_query_returns_data_and_provenance(lake):
    first = partition(lake, rows=[{"date": "2019-01-02", "close": 5, "volume": 0}])
    second = partition(lake, rows=[{"date": "2019-01-03", "close": 6, "volume": 100}])
    # Distinct window paths do not alter the row value lineage contract.
    out = query(
        lake.root, source="eod-bars", vendor_symbol="AMD",
        captures=[first[0] + ":" + first[1], second[0] + ":" + second[1]],
        start="2019-01-01", end="2019-01-31", observed_before=CUTOFF,
        acknowledge_hindsight=True, check_mount=False,
    )
    assert out["status"] == "RETROSPECTIVE_EXPLORATORY"
    assert [r["close_raw"] for r in out["rows"]] == [5, 6]
    assert [r["volume_raw"] for r in out["rows"]] == [0, 100]
    assert out["metadata"]["source_partitions"] == 2
    assert out["metadata"]["availability_clock"] == "SOURCE_CAPTURE_ONLY_NO_PIT"
    assert out["complete_history_proven"] is False
    assert out["pit_backtest_eligible"] is False


def test_as_reported_statements_query_is_distinct_from_restated(lake):
    first = partition(lake, source="fund-statements", rows=one_statement(),
                      params={"startDate": "2019-01-01", "endDate": "2021-01-01",
                              "asReported": "true"})
    out = query(
        lake.root, source="fund-statements", vendor_symbol="AMD",
        captures=[first[0] + ":" + first[1]],
        start="2019-01-01", end="2020-12-31", observed_before=CUTOFF,
        as_reported="true", acknowledge_hindsight=True, check_mount=False,
    )
    assert out["rows"][0]["fiscal_quarter"] == 0
    assert out["metadata"]["as_reported_dimension"] == "AS_REPORTED_CURRENT_PERIOD"
    assert out["metadata"]["historical_known_at_proven"] is False
    with pytest.raises(ValueError, match="asReported"):
        query(lake.root, source="fund-statements", vendor_symbol="AMD",
              captures=[first[0] + ":" + first[1]], start="2019-01-01",
              end="2020-12-31", observed_before=CUTOFF,
              acknowledge_hindsight=True, check_mount=False)


def test_query_requires_hindsight_and_never_implies_vendor_availability(lake):
    ref = partition(lake)
    opts = dict(root=lake.root, source="eod-bars", vendor_symbol="AMD",
                captures=[ref[0] + ":" + ref[1]],
                start="2019-01-01", end="2019-12-31",
                observed_before=CUTOFF, check_mount=False)
    with pytest.raises(ValueError, match="acknowledge"):
        query(**opts, acknowledge_hindsight=False)
    with pytest.raises(ValueError, match="capture"):
        query(**{**opts, "captures": []}, acknowledge_hindsight=True)
    with pytest.raises(ValueError, match="duplicate"):
        query(**{**opts, "captures": opts["captures"] * 2},
              acknowledge_hindsight=True)
    with pytest.raises(ValueError, match="asReported"):
        query(**opts, acknowledge_hindsight=True, as_reported="true")


def test_read_only_commands_never_call_vendor_or_read_key(lake, monkeypatch):
    ref = partition(lake)
    def forbidden(*args, **kwargs):
        pytest.fail("research CLI invoked Tiingo provider or credential")
    monkeypatch.setattr(a, "read_key", forbidden)
    monkeypatch.setattr(a, "collect_one", forbidden)
    before = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in lake.root.rglob("*") if p.is_file()
    }
    discover(lake.root, source="eod-bars", vendor_symbol="AMD", check_mount=False)
    query(lake.root, source="eod-bars", vendor_symbol="AMD",
          captures=[ref[0] + ":" + ref[1]],
          start="2019-01-01", end="2019-12-31", observed_before=CUTOFF,
          acknowledge_hindsight=True, check_mount=False)
    after = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in lake.root.rglob("*") if p.is_file()
    }
    assert before == after


def test_cli_discovery_and_research_query_json(lake, capsys):
    day, digest = partition(lake)
    assert main(["discover", "--source", "eod-bars", "--symbol", "AMD"],
                root=lake.root, check_mount=False) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verified_candidates"][0]["source_sha256"] == digest
    args = ["query", "--source", "eod-bars", "--symbol", "AMD",
            "--capture", day + ":" + digest, "--start", "2019-01-01",
            "--end", "2019-12-31", "--observed-before", CUTOFF,
            "--acknowledge-hindsight"]
    assert main(args, root=lake.root, check_mount=False) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["rows"][0]["close_raw"] == 5
    assert out["status"] == "RETROSPECTIVE_EXPLORATORY"


def test_cli_bad_query_refuses_without_partial_rows(lake, capsys):
    args = ["query", "--source", "eod-bars", "--symbol", "AMD",
            "--capture", "2026-10-09:" + "a" * 64,
            "--start", "2019-01-01", "--end", "2019-12-31",
            "--observed-before", CUTOFF, "--acknowledge-hindsight"]
    assert main(args, root=lake.root, check_mount=False) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "REFUSED"
    assert "rows" not in out
    assert out["network"] is False


@pytest.mark.parametrize("text", [
    "", "2026-10-09", "2026-10-09:xyz",
    "2026-10-09:" + "f" * 63, "2026-10-9:" + "f" * 64,
    "2026-10-09:" + "G" * 64, "../2026-10-09:" + "a" * 64,
])
def test_explicit_capture_ref_is_strict(text):
    with pytest.raises(ValueError):
        capture_ref(text)


def test_no_json_truncation_as_implicit_research_success():
    with pytest.raises(ValueError, match="byte cap"):
        bounded_json({"rows": [{"value": "x" * 2000}]}, max_bytes=256)
    with pytest.raises(ValueError):
        bounded_json({"rows": []}, max_bytes=True)


def test_script_help_works_from_outside_repository(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tiingo_research_query.py"
    run = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path, capture_output=True, text=True, timeout=20, check=False,
    )
    assert run.returncode == 0
    assert "discover" in run.stdout and "query" in run.stdout



def test_discovery_rejects_l1_metadata_when_original_raw_has_changed(lake):
    day, digest = partition(lake)
    receipt = next(
        json.loads(file.read_text())
        for file in (lake.root / "receipts" / "eod-bars" / day).glob("*.json")
    )
    (lake.root / receipt["raw_path"]).write_bytes(b"corrupt raw but intact research parquet")
    out = discover(lake.root, source="eod-bars", vendor_symbol="AMD",
                   check_mount=False)
    assert out["verified_candidates"] == []
    assert out["rejected_local_artifacts"] == 1
    assert out["pit_backtest_eligible"] is False


def test_cli_large_research_output_refuses_without_partially_printing_rows(lake, capsys):
    day, sha = partition(lake)
    args = [
        "--max-output-bytes", "256", "query", "--source", "eod-bars",
        "--symbol", "AMD", "--capture", day + ":" + sha,
        "--start", "2019-01-01", "--end", "2019-12-31",
        "--observed-before", CUTOFF, "--acknowledge-hindsight",
    ]
    assert main(args, root=lake.root, check_mount=False) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "REFUSED"
    assert "rows" not in output


def boats_partition(lake):
    from datetime import datetime, timezone
    stamp = "2026-10-09T01:00:00Z"
    d = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    sec = int((d - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds())
    events = [
        ("2026-10-09T01:00:01Z", json.dumps({
            "service": "boats", "data": [
                "Q", stamp, sec * 10**9, "AMD", 100, 99.9, 100.0, 100.1, 120]})),
        ("2026-10-09T01:00:02Z", json.dumps({
            "service": "boats", "data": [
                "T", stamp, sec * 10**9, "NVDA", 100.0, 22, "@", "", "", ""]})),
    ]
    response = lake.store_boats_batch(events)
    digest = response["raw_sha256"]
    rec = next(
        json.loads(p.read_text())
        for p in (lake.root / "receipts" / "boats-firehose").rglob("*.json")
        if json.loads(p.read_text())["raw_sha256"] == digest
    )
    assert materialize_one(lake.root, rec, free_floor=0)["status"] == "WRITTEN"
    return "2026-10-09", digest


def test_boats_discovery_handles_multiticker_raw_segments_without_claiming_nbbo(lake):
    day, digest = boats_partition(lake)
    out = discover(lake.root, source="boats-firehose", vendor_symbol="AMD",
                   observed_before="2026-10-09T01:00:03Z", check_mount=False)
    assert out["scan_complete"] is True
    assert len(out["verified_candidates"]) == 1
    assert out["verified_candidates"][0]["source_sha256"] == digest
    assert out["complete_history_proven"] is False
    assert out["pit_backtest_eligible"] is False
    assert out["redistribution_admitted"] is False


def test_boats_discovery_entire_segment_must_be_observed_by_cutoff(lake):
    boats_partition(lake)
    out = discover(lake.root, source="boats-firehose", vendor_symbol="AMD",
                   observed_before="2026-10-09T01:00:01Z", check_mount=False)
    assert out["verified_candidates"] == []
    assert out["scan_complete"] is True


def test_boats_cli_query_is_read_only_venue_diagnostic_not_executable_price(lake, capsys):
    day, digest = boats_partition(lake)
    args = [
        "query", "--source", "boats-firehose", "--symbol", "AMD",
        "--capture", day + ":" + digest,
        "--start", "2026-10-09T01:00:00Z",
        "--end", "2026-10-09T03:00:00Z",
        "--observed-before", "2026-10-10T00:00:00Z",
        "--acknowledge-hindsight",
    ]
    assert main(args, root=lake.root, check_mount=False) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "OBSERVED_SOURCE_EVENTS_NOT_COVERAGE_PROOF"
    tape = data["boats_single_venue_tape_diagnostics"]
    assert tape["selected_kind_counts"] == {"Q": 1, "T": 0, "B": 0}
    assert tape["source_messages_all_tickers"] == 2
    assert tape["nbbo"] is False
    assert data["pit_backtest_eligible"] is False
    assert data["complete_history_proven"] is False


def test_boats_query_without_capture_clock_or_hindsight_refuses(lake, capsys):
    day, digest = boats_partition(lake)
    common = dict(
        root=lake.root, source="boats-firehose", vendor_symbol="AMD",
        captures=[day + ":" + digest],
        start="2026-10-09T01:00:00Z", end="2026-10-09T03:00:00Z",
        observed_before="2026-10-10T00:00:00Z", check_mount=False,
    )
    with pytest.raises(ValueError, match="hindsight"):
        query(**common, acknowledge_hindsight=False)
    with pytest.raises(ValueError, match="asReported"):
        query(**common, acknowledge_hindsight=True, as_reported="false")
    with pytest.raises(ValueError, match="UTC-offset"):
        query(**{**common, "end": "2026-10-09T03:00:00"}, acknowledge_hindsight=True)
