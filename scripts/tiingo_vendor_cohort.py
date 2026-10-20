"""Build an exact-capture Tiingo fundamental permaTicker acquisition cohort.

Consumes an existing, checksum-verified L0 fund-meta receipt ONLY. Result is a
vendor address list for history acquisition, never canonical Data OS identity or
historical survivorship-free universe membership. No API connection/credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.tiingo_archive import (
    DEFAULT_ARCHIVE, TiingoArchiveError, _publish_once, require_external_root,
    symbol_path,
)
from scripts.tiingo_materialize import verified_raw


def vendor_cohort(root: Path, receipt: dict[str, Any], *,
                  dry_run: bool = False) -> dict[str, Any]:
    if (receipt.get("schema") != "mastermind.tiingo.raw_receipt.v1"
            or receipt.get("vendor") != "tiingo"
            or receipt.get("source") != "fund-meta"):
        raise TiingoArchiveError("a true Tiingo fundamentals-meta receipt is required")
    raw = verified_raw(root, receipt)
    try:
        content = json.loads(raw)
    except (ValueError, UnicodeError) as err:
        raise TiingoArchiveError("vendor fundamental meta could not be parsed") from err
    if not isinstance(content, list):
        raise TiingoArchiveError("fund-meta must contain one array of securities")

    identity: dict[str, dict[str, Any]] = {}
    unknown = 0
    for row in content:
        if not isinstance(row, dict):
            raise TiingoArchiveError("malformed fund-meta member")
        v = row.get("permaTicker")
        if v is None:
            unknown += 1
            continue
        vendor_id = str(v)
        try:
            symbol_path(vendor_id)
        except ValueError as err:
            raise TiingoArchiveError("invalid vendor permanent security identifier") from err
        item = {
            "permaTicker": vendor_id, "vendor_ticker": row.get("ticker"),
            "isActive": row.get("isActive"),
            "statementLastUpdated": row.get("statementLastUpdated"),
            "dailyLastUpdated": row.get("dailyLastUpdated"),
        }
        if vendor_id in identity and identity[vendor_id] != item:
            raise TiingoArchiveError("conflicting vendor permaTicker identity mapping")
        identity[vendor_id] = item

    ids = sorted(identity)
    batch = ("\n".join(ids) + "\n").encode("utf-8")
    digest = receipt["raw_sha256"]
    cohort_dir = root / "cohorts" / "fundamentals" / digest
    cohort_path = cohort_dir / "permatickers.txt"
    mapping_path = cohort_dir / "vendor_identity_snapshot.json"
    manifest_path = cohort_dir / "cohort_receipt.json"
    rec = {
        "schema": "mastermind.tiingo.vendor_cohort_receipt.v1",
        "source": "fund-meta", "vendor": "tiingo",
        "source_sha256": digest,
        "source_observed_at_utc": receipt.get("observed_at_utc"),
        "cohort_semantics": "CURRENT_VENDOR_REFERENCE_SNAPSHOT_ONLY",
        "historical_pit_membership_eligible": False,
        "canonical_dataos_identity": False,
        "total_rows_seen": len(content), "unkeyed_rows": unknown,
        "permaTicker_count": len(ids),
        "active_count": sum(row["isActive"] is True for row in identity.values()),
        "inactive_count": sum(row["isActive"] is False for row in identity.values()),
        "activity_unclassified": sum(
            row["isActive"] is not True and row["isActive"] is not False
            for row in identity.values()),
        "permatickers_sha256": hashlib.sha256(batch).hexdigest(),
    }
    if dry_run:
        return {**rec, "would_write": True}
    # Deterministic content-addressed candidate cohort; no overwrite.
    _publish_once(cohort_path, batch)
    _publish_once(mapping_path, (json.dumps(
        [identity[x] for x in ids], sort_keys=True) + "\n").encode("utf-8"))
    _publish_once(manifest_path, (json.dumps(rec, sort_keys=True)
                                  + "\n").encode("utf-8"))
    return {**rec, "permatickers_path": cohort_path.relative_to(root).as_posix()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True,
                        help="path to one specific fund-meta receipt under external lake")
    parser.add_argument("--dry-run", action="store_true")
    a = parser.parse_args(argv)
    try:
        root = require_external_root(DEFAULT_ARCHIVE)
        receipt_file = (root / a.receipt).resolve()
        if not receipt_file.is_relative_to(root / "receipts" / "fund-meta"):
            raise TiingoArchiveError("must choose a fund-meta source receipt")
        record = json.loads(receipt_file.read_text())
        print(json.dumps(vendor_cohort(root, record, dry_run=a.dry_run), indent=2))
        return 0
    except (ValueError, OSError, KeyError, TiingoArchiveError) as err:
        print(json.dumps({"status": "REFUSED", "reason": type(err).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
