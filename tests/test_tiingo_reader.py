"""No network or credentials: Tiingo reader never silently certifies backtests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import collectors.tiingo_archive as a
from lib.dataos.tiingo_reader import TiingoViewRefusal, read_research_view
from scripts.tiingo_materialize import materialize_one


@pytest.fixture
def view(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    archive = a.Archive(tmp_path / "tiingo", check_mount=False, free_floor=0)
    saved = archive.store_response(
        "eod-bars", "AMD", a.request_path("eod-bars", "AMD"),
        b'[{"date":"2019-01-03","close":22,"adjClose":18}]',
        received_at="2026-10-09T05:00:00+00:00",
    )
    recpath = next((archive.root / "receipts").rglob("*.json"))
    receipt = json.loads(recpath.read_text())
    assert materialize_one(archive.root, receipt, free_floor=0)["status"] == "WRITTEN"
    return (archive.root, "eod-bars", "2026-10-09", saved["raw_sha256"])


def test_read_inspection_is_noncanonical(view):
    root, source, day, digest = view
    result = read_research_view(source, day, digest, root=root, check_mount=False)
    assert result.rows[0]["close_raw"] == 22
    assert result.rows[0]["close_tradj"] == 18
    assert result.rows[0]["pit_backtest_eligible"] is False
    assert result.metadata()["authority"] == "RESEARCH_ONLY_VENDOR_SOURCE"
    assert result.source_observed_at_utc.startswith("2026-")


def test_research_hindsight_requires_approval_flag(view):
    root, source, day, digest = view
    with pytest.raises(TiingoViewRefusal, match="acknowledge"):
        read_research_view(source, day, digest, root=root, check_mount=False,
                           purpose="RETROSPECTIVE_EXPLORATORY")
    good = read_research_view(source, day, digest, root=root, check_mount=False,
                               purpose="RETROSPECTIVE_EXPLORATORY",
                               acknowledge_hindsight=True)
    assert good.purpose == "RETROSPECTIVE_EXPLORATORY"
    assert good.pit_backtest_eligible is False


def test_pit_backtest_refused_until_canonical_admission(view):
    root, source, day, digest = view
    with pytest.raises(TiingoViewRefusal, match="unadmitted"):
        read_research_view(source, day, digest, root=root, check_mount=False,
                           purpose="PIT_BACKTEST", acknowledge_hindsight=True)


def test_manifest_tamper_fails_closed(view):
    root, source, day, digest = view
    manifest = root / "manifests" / source / day / (digest + ".json")
    data = json.loads(manifest.read_text())
    data["output_sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(TiingoViewRefusal, match="integrity"):
        read_research_view(source, day, digest, root=root, check_mount=False)


@pytest.mark.parametrize("day,hash", [
    ("../../2020", "a" * 64), ("2026-10-09", "../bad"),
    ("2026-10-09", "0" * 63), ("2026-10-9", "1" * 64),
])
def test_ref_evasion_blocked(view, day, hash):
    root, source, _, _ = view
    with pytest.raises(TiingoViewRefusal):
        read_research_view(source, day, hash, root=root, check_mount=False)


def test_missing_manifest_never_assumes_success(view):
    root, source, day, digest = view
    manifest = root / "manifests" / source / day / (digest + ".json")
    manifest.unlink()
    with pytest.raises(TiingoViewRefusal, match="lacks artifact-bound"):
        read_research_view(source, day, digest, root=root, check_mount=False)


def test_reader_invalid_cap_fails_closed(view):
    root, source, day, digest = view
    with pytest.raises(TiingoViewRefusal, match="invalid reader"):
        read_research_view(source, day, digest, root=root, check_mount=False,
                           max_rows=0)


def test_reader_quarantines_identical_bytes_from_another_ticker(view):
    root, source, day, digest = view
    archive = a.Archive(root, check_mount=False, free_floor=0)
    archive.store_response(
        "eod-bars", "OTHER", a.request_path("eod-bars", "OTHER"),
        b'[{"date":"2019-01-03","close":22,"adjClose":18}]',
        received_at="2026-10-09T05:00:00+00:00",
    )
    with pytest.raises(TiingoViewRefusal, match="ambiguous raw contexts"):
        read_research_view(source, day, digest, root=root, check_mount=False)


def test_inspection_refuses_manifest_claimed_pit_admission(view):
    root, source, day, digest = view
    manifest = root / "manifests" / source / day / (digest + ".json")
    data = json.loads(manifest.read_text())
    data["pit_backtest_eligible"] = True
    manifest.write_text(json.dumps(data))
    with pytest.raises(TiingoViewRefusal, match="cannot assert"):
        read_research_view(source, day, digest, root=root, check_mount=False)


def test_pit_manifest_flag_never_grants_pit_reader_permission(view):
    root, source, day, digest = view
    manifest = root / "manifests" / source / day / (digest + ".json")
    data = json.loads(manifest.read_text())
    data["pit_backtest_eligible"] = True
    data["dataos_identity_admitted"] = True
    manifest.write_text(json.dumps(data))
    with pytest.raises(TiingoViewRefusal, match="unadmitted"):
        read_research_view(source, day, digest, root=root, check_mount=False,
                           purpose="PIT_BACKTEST")


def test_missing_raw_receipt_does_not_pass_from_parquet_manifest_alone(view):
    root, source, day, digest = view
    next((root / "receipts" / source / day).glob("*.json")).unlink()
    with pytest.raises(TiingoViewRefusal, match="raw-context evidence"):
        read_research_view(source, day, digest, root=root, check_mount=False)


def test_altered_capture_clock_in_manifest_is_refused(view):
    root, source, day, digest = view
    file = root / "manifests" / source / day / (digest + ".json")
    manifest = json.loads(file.read_text())
    manifest["source_observed_at_utc"] = "2018-01-01T00:00:00Z"
    file.write_text(json.dumps(manifest))
    with pytest.raises(TiingoViewRefusal, match="lineage"):
        read_research_view(source, day, digest, root=root, check_mount=False)



def test_research_reader_rejects_older_projection_schema(view):
    root, source, day, digest = view
    file = root / "manifests" / source / day / (digest + ".json")
    meta = json.loads(file.read_text()); meta["view_schema"] = "mastermind.tiingo.research_views.v1"
    file.write_text(json.dumps(meta))
    with pytest.raises(TiingoViewRefusal, match="schema"):
        read_research_view(source, day, digest, root=root, check_mount=False)


def test_research_reader_schema_is_pinned_per_row_not_just_manifest(view):
    import hashlib
    import pyarrow as pa
    import pyarrow.parquet as pq
    root, source, day, digest = view
    file = root / "manifests" / source / day / (digest + ".json")
    meta = json.loads(file.read_text()); artifact = root / meta["output_path"]
    data = pq.read_table(artifact).to_pylist()
    data[0]["source_view_schema"] = "mastermind.tiingo.research_views.v1"
    pq.write_table(pa.Table.from_pylist(data), artifact)
    meta["output_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest(); file.write_text(json.dumps(meta))
    with pytest.raises(TiingoViewRefusal, match="lineage"):
        read_research_view(source, day, digest, root=root, check_mount=False)
