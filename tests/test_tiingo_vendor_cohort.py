"""Offline fundamental acquisition cohorts are vendor snapshots, never PIT universes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import collectors.tiingo_archive as a
from scripts.tiingo_vendor_cohort import vendor_cohort


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def source_receipt(lake, data):
    lake.store_response("fund-meta", None, a.request_path("fund-meta", None),
                        json.dumps(data).encode(), received_at="2026-10-09T12:00:00Z")
    return json.loads(next((lake.root / "receipts").rglob("*.json")).read_text())


def test_cohort_keeps_delisted_identifiers_and_explicit_denominators(lake):
    record = source_receipt(lake, [
        {"permaTicker": "111", "ticker": "LIVE", "isActive": True},
        {"permaTicker": "222", "ticker": "OLD", "isActive": False},
        {"permaTicker": "333", "ticker": "UNKNOWN"},
        {"ticker": "UNKEYED", "isActive": False},
    ])
    result = vendor_cohort(lake.root, record)
    assert result["permaTicker_count"] == 3
    assert result["active_count"] == result["inactive_count"] == result["activity_unclassified"] == 1
    assert result["unkeyed_rows"] == 1
    assert result["canonical_dataos_identity"] is False
    assert result["historical_pit_membership_eligible"] is False
    assert (lake.root / result["permatickers_path"]).read_text().splitlines() == ["111", "222", "333"]


def test_duplicate_identical_vendor_records_are_deduplicated(lake):
    row = {"permaTicker": "111", "ticker": "LIVE", "isActive": True}
    result = vendor_cohort(lake.root, source_receipt(lake, [row, row]))
    assert result["total_rows_seen"] == 2 and result["permaTicker_count"] == 1


def test_conflicting_permanent_id_is_not_silently_overwritten(lake):
    record = source_receipt(lake, [
        {"permaTicker": "111", "ticker": "ONE"},
        {"permaTicker": "111", "ticker": "TWO"},
    ])
    with pytest.raises(a.TiingoArchiveError, match="conflicting"):
        vendor_cohort(lake.root, record)


def test_dry_run_writes_no_cohort_files(lake):
    result = vendor_cohort(lake.root, source_receipt(lake, [{"permaTicker": "111"}]), dry_run=True)
    assert result["would_write"] is True
    assert not (lake.root / "cohorts").exists()


def test_repeated_cohort_capture_keeps_same_identity_file(lake):
    record = source_receipt(lake, [{"permaTicker": "111"}])
    first = vendor_cohort(lake.root, record)
    second = vendor_cohort(lake.root, record)
    assert first == second


def test_cohort_refuses_non_meta_receipt(lake):
    record = source_receipt(lake, [])
    record["source"] = "eod-bars"
    with pytest.raises(a.TiingoArchiveError, match="fundamentals-meta"):
        vendor_cohort(lake.root, record)


def test_cohort_validates_raw_digest_before_reading_ids(lake):
    record = source_receipt(lake, [{"permaTicker": "111"}])
    record["raw_sha256"] = "0" * 64
    with pytest.raises(a.TiingoArchiveError, match="digest"):
        vendor_cohort(lake.root, record)


def test_cohort_rejects_pathlike_source_identifier(lake):
    record = source_receipt(lake, [{"permaTicker": "../private"}])
    with pytest.raises(a.TiingoArchiveError, match="identifier"):
        vendor_cohort(lake.root, record)
