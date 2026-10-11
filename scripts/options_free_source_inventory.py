"""Private, point-in-time-honest source-availability receipt for free options demos.

This is a read-only consumer of the existing sample qualifier artifacts, not a
second source registry or a producer of research/trading signals. It asserts
physical custody and schema/hash identity. Research outputs remain host-private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from collectors.options_free_samples import SourceRejected
from scripts.qualify_options_free_samples import (
    _checked_root, EXTERNAL_PRIVATE_ROOT, EXTERNAL_VOLUME_UUID,
)

EOD_ARCHIVE = "cboe_c1_openclose_public_eval_2025-03-28_outer.zip"
TBT_ARCHIVE = "cboe_c1_tbt_public_eval_2025-03-28_outer.zip"
EOD_QUALIFIED = "qualified_cboe_c1_sample.json"
TBT_QUALIFIED = "qualified_cboe_c1_tbt_sample.json"
EOD_RECEIPT = "receipt.json"
TBT_RECEIPT = "cboe_tbt_receipt.json"
MIGRATION_RECEIPT = "external_storage_receipt.json"
CUTOVER_RECEIPT = "cutover_receipt.json"
PRIMARY = (
    EOD_ARCHIVE, TBT_ARCHIVE, EOD_QUALIFIED, TBT_QUALIFIED,
    EOD_RECEIPT, TBT_RECEIPT,
)
# This is a tiny, illustrative coverage probe, NOT a canonical theme
# membership table, defensives allocation, delta- or tenor-matched cohort.
RESEARCH_ETFS = {
    "technology": ("XLK", "SMH", "SOXX"),
    "defensives": ("XLP", "XLU", "XLV"),
}


def _private_regular_bytes(root: Path, name: str) -> bytes:
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise SourceRejected("missing or linked private evidence: " + name)
    st = path.stat()
    if st.st_dev != root.stat().st_dev or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise SourceRejected("untrusted private evidence owner/mode/device: " + name)
    return path.read_bytes()


def _json_bytes(blob: bytes, name: str) -> dict:
    try:
        value = json.loads(blob)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SourceRejected("invalid JSON: " + name) from exc
    if not isinstance(value, dict):
        raise SourceRejected("unexpected JSON shape: " + name)
    return value


def _verify_manifest(root: Path) -> tuple[dict, dict, dict]:
    migration_bytes = _private_regular_bytes(root, MIGRATION_RECEIPT)
    migration = _json_bytes(migration_bytes, MIGRATION_RECEIPT)
    cutover_bytes = _private_regular_bytes(root, CUTOVER_RECEIPT)
    cutover = _json_bytes(cutover_bytes, CUTOVER_RECEIPT)
    if (migration.get("schema") != "mastermind.options.external_custody_receipt/v1"
            or migration.get("volume_uuid") != EXTERNAL_VOLUME_UUID
            or migration.get("destination") != str(root)
            or migration.get("file_count") != 28):
        raise SourceRejected("invalid source transfer receipt")
    if (cutover.get("schema") != "mastermind.options.external_custody_cutover/v1"
            or cutover.get("phase") != "moved_verified"
            or cutover.get("volume_uuid") != EXTERNAL_VOLUME_UUID
            or cutover.get("actual_private_data_root") != str(root)
            or cutover.get("original_data_files_removed_from_main_ssd") is not True):
        raise SourceRejected("external SSD cutover is not verified")
    expected = {entry["relpath"]: entry for entry in migration["files"]}
    if len(expected) != migration["file_count"]:
        raise SourceRejected("duplicate or missing transfer entries")
    blobs: dict[str, bytes] = {}
    for name in PRIMARY:
        meta = expected.get(name)
        if not isinstance(meta, dict):
            raise SourceRejected("missing primary evidence in transfer manifest: " + name)
        blob = _private_regular_bytes(root, name)
        if len(blob) != meta.get("size") or hashlib.sha256(blob).hexdigest() != meta.get("sha256"):
            raise SourceRejected("verified primary bytes changed: " + name)
        blobs[name] = blob
    return migration, cutover, blobs


def build_receipt(eod: dict, tbt: dict, *, volume_uuid: str,
                  source_sha: dict[str, str], cutover_at: str) -> dict:
    """One deterministic research-only inventory, never an options signal."""
    if eod.get("schema") != "options.free_cboe_eval/v1":
        raise SourceRejected("unexpected EOD qualification schema")
    if tbt.get("schema") != "options.free_cboe_tbt_eval/v1":
        raise SourceRejected("unexpected TBT qualification schema")
    if (eod.get("effective_trade_session") != "2025-03-28"
            or tbt.get("effective_trade_session") != "2025-03-28"):
        raise SourceRejected("unexpected effective trading session")
    for obj in (eod, tbt):
        if obj.get("publish") is not False or obj.get("signal_authority") is not False:
            raise SourceRejected("classified-source authority unexpectedly enabled")
        if obj.get("rights") != "internal_evaluation_only_pending_commercial_rights":
            raise SourceRejected("classified-source redistribution gate changed")
    etf_census: dict[str, Any] = {}
    eod_by_symbol = eod.get("observed_sample_only", {})
    tbt_by_symbol = tbt.get("participant_side_by_underlying", {})
    for sleeve, tickers in RESEARCH_ETFS.items():
        etf_census[sleeve] = {}
        for ticker in tickers:
            eod_sides = eod_by_symbol.get(ticker)
            tbt_source = tbt_by_symbol.get(ticker)
            etf_census[sleeve][ticker] = {
                "eod_sample_series_rows": (
                    sum(int(side.get("standard_series_rows", 0))
                        for side in eod_sides.values()) if eod_sides else None
                ),
                "tbt_sample_participant_side_rows": (
                    int(tbt_source["participant_side_rows"]) if tbt_source else None
                ),
                "tbt_sample_classifiable_rows": (
                    int(tbt_source["classifiable_rows"]) if tbt_source else None
                ),
                "missing_means_sample_not_selected_not_zero_market_volume": True,
            }
    return {
        "schema": "options.private_research_source_receipt/v1",
        "authority": "research_only_not_a_source_of_live_market_truth",
        "acquisition_scope": "C1 one-day, independent non-representative vendor demo samples",
        "physical_location": "identified_4tb_external_mastermind_volume",
        "volume_uuid": volume_uuid,
        "cutover_verified_at": cutover_at,
        "sample_trade_session": "2025-03-28",
        "source_raw_sha256": source_sha,
        "sources": [
            {
                "key": "cboe_c1_eod_demo_20pct",
                "state": "PRIVATE_HISTORICAL_RESEARCH_SAMPLE_QUALIFIED",
                "rows": eod["rows_total"],
                "standard_series_rows": eod["rows_standard"],
                "underlyings": eod["underlyings_standard"],
                "license": eod["rights"],
                "sample_fraction_vendor_label": 0.20,
                "quote_age_eligible": False,
                "original_historical_available_at": None,
                "nationwide_market_representative": False,
                "current_data": False,
            },
            {
                "key": "cboe_c1_tbt_demo_3pct",
                "state": "PRIVATE_HISTORICAL_RESEARCH_SAMPLE_QUALIFIED",
                "participant_side_rows": tbt["rows_total"],
                "field_classifiable_rows": tbt["rows_fully_classified_with_economics"],
                "unknown_reasons": tbt["unknown_reasons"],
                "underlyings": tbt["underlyings"],
                "license": tbt["rights"],
                "sample_fraction_vendor_label": 0.03,
                "side_is_aggressor": False,
                "quote_age_eligible": False,
                "original_historical_available_at": None,
                "nationwide_market_representative": False,
                "current_data": False,
            },
        ],
        "other_access_state": {
            "occ_volume_query": "TECHNICAL_HTTP_200_ONLY_RIGHTS_NOT_CLEARED_NO_COMMERCIAL_INGESTION",
            "box_openclose_trial": "NOT_APPLIED_NOT_ENROLLED",
            "thetadata_trade_quote": "HISTORICAL_ENTITLEMENT_PROBE_ONLY_CURRENT_UNKNOWN",
        },
        "illustrative_fixed_etf_sample_coverage": etf_census,
        "cohort_note": (
            "Non-exhaustive six ETF symbols, NOT canonical microthemes; sample rows "
            "are not comparable population denominators across the 3% and 20% files."
        ),
        "validation_gaps": [
            "current multi-session classified opening/closing venue coverage",
            "licensed commercial research and derived-data terms",
            "trade condition, correction/sequence and execution deduplication",
            "independent NBBO quote event age and original consumer receipt clocks",
            "underlying/contract reference and comparable delta-tenor snapshots",
            "sector/theme membership as-of event clock and stable comparison universe",
            "captured-PIT original availability and matured forward labels",
            "independent prospective incremental predictive validation",
        ],
        "research_consumers": [
            "options_intelligence_source_admission_reference",
            "options_alpha_observation_and_calibration_research",
            "classified_options_semantics_contract_tests",
        ],
        "live_consumers_enabled": [],
        "publish": False,
        "rank": False,
        "signal_authority": False,
        "may_train_production_model": False,
        "trading_authority": False,
    }


def inventory(root: Path) -> dict:
    root = _checked_root(root)
    migration, cutover, blobs = _verify_manifest(root)
    eod = _json_bytes(blobs[EOD_QUALIFIED], EOD_QUALIFIED)
    tbt = _json_bytes(blobs[TBT_QUALIFIED], TBT_QUALIFIED)
    eod_acq = _json_bytes(blobs[EOD_RECEIPT], EOD_RECEIPT)
    tbt_acq = _json_bytes(blobs[TBT_RECEIPT], TBT_RECEIPT)
    for qualified, acquired, archive in [
        (eod, eod_acq, EOD_ARCHIVE),
        (tbt, tbt_acq, TBT_ARCHIVE),
    ]:
        sha = hashlib.sha256(blobs[archive]).hexdigest()
        if acquired.get("file_sha256") != sha or qualified.get("source_sha256") != sha:
            raise SourceRejected("source/qualified/raw archive lineage mismatch")
        if acquired.get("sample_session") != "2025-03-28":
            raise SourceRejected("source acquisition date does not match")
    raw_sha = {
        "c1_eod_demo": hashlib.sha256(blobs[EOD_ARCHIVE]).hexdigest(),
        "c1_tbt_demo": hashlib.sha256(blobs[TBT_ARCHIVE]).hexdigest(),
    }
    return build_receipt(
        eod, tbt,
        volume_uuid=migration["volume_uuid"], source_sha=raw_sha,
        cutover_at=cutover["cutover_time_utc"],
    )


def materialize(root: Path, *, persist: bool) -> dict:
    obj = inventory(root)
    if persist:
        canonical = _checked_root(root)
        target = canonical / "private_research_source_inventory.json"
        content = (json.dumps(obj, sort_keys=True, indent=2) + "\n").encode()
        if target.exists():
            if target.is_symlink() or target.read_bytes() != content:
                raise SourceRejected("private inventory already exists with different bytes")
        else:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            st = target.stat()
            if st.st_mode & 0o077 or st.st_dev != canonical.stat().st_dev:
                raise SourceRejected("private inventory not on protected external volume")
    return obj


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, default=EXTERNAL_PRIVATE_ROOT)
    parser.add_argument("--persist-private", action="store_true")
    args = parser.parse_args()
    obj = materialize(args.private_root, persist=args.persist_private)
    print(json.dumps({
        "schema": obj["schema"],
        "source_count": len(obj["sources"]),
        "sample_trade_session": obj["sample_trade_session"],
        "external_volume_verified": True,
        "research_only": True,
        "publish": False,
        "signal_authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
