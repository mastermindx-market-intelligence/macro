"""One reviewed input migration; no network, Git, publishing or runtime actions."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import gzip
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.intl_forecast_vintages import merge_publications, select_publications
from collectors.intl_weo import WEO_OCTOBER_2026

SOURCES = Path("/tmp/intl-fiscal-coverage-20261019")
OUT = Path(__file__).resolve().parent
TARGET = ROOT / "config/intl_country_baseline.json"


def main():
    receipt_path = OUT / "admission.json"
    if receipt_path.exists():
        raise SystemExit("Admission already recorded; reconcile the existing receipt, do not replay.")
    before_bytes = TARGET.read_bytes()
    before = json.loads(before_bytes)
    old_archive = before["forecast_archive"]
    if len(old_archive) != 37:
        raise SystemExit("Unexpected archive; requires reconciliation before admission.")
    now = datetime.now(timezone.utc).isoformat()
    fixes = []
    for record in old_archive:
        if record["provider"] == "IMF" and record["family"] == "WEO" and record["edition"] == "2026-10":
            assert record["information_cutoff"] == "2026-10-01"
            assert record["correction_sequence"] == 0
            fixes.append({**deepcopy(record), "information_cutoff": "2026-09-30",
                          "correction_sequence": 1, "supersedes_record_id": record["record_id"],
                          "correction_source_url": WEO_OCTOBER_2026["documentation_url"]})
    assert len(fixes) == 28
    fiscal = json.loads((SOURCES / "qualified_fiscal_records.json").read_text())
    assert len(fiscal) == 8
    acquired = json.loads((SOURCES / "series_acquisition.json").read_text())
    for source in acquired:
        blob = (SOURCES / (source["series"] + ".json")).read_bytes()
        assert sha256(blob).hexdigest() == source["sha256"]
        assert source["status"] == 200
    archive, diagnostics = merge_publications(old_archive, fixes + fiscal, observed_at=now)
    assert not diagnostics and len(archive) == 73
    selected = [r for r in archive if r["correction_sequence"] == 1]
    for fixed in selected:
        old = next(r for r in old_archive if r["record_id"] == fixed["supersedes_record_id"])
        assert all(fixed[k] == old[k] for k in
                   ("values", "periods", "published", "retrieved_at", "source_sha256",
                    "source_row_sha256", "source_url", "dataset_url", "coverage_note"))
        assert fixed["first_observed_at"] == fixed["admitted_at"] == now
    after = deepcopy(before)
    after["forecast_archive"] = archive
    after["retrieved_at"] = now
    new_bytes = (json.dumps(after, ensure_ascii=False, indent=2) + "\n").encode()
    # Preserve the exact pre-migration seed and original numerical responses.
    (OUT / "baseline_before.json.gz").write_bytes(gzip.compress(before_bytes, mtime=0))
    raw_dir = OUT / "raw_api"
    raw_dir.mkdir(exist_ok=True)
    for source in acquired:
        blob = (SOURCES / (source["series"] + ".json")).read_bytes()
        (raw_dir / (source["series"] + ".json.gz")).write_bytes(gzip.compress(blob, mtime=0))
    for filename in ("help_acquisition.json", "indicators_acquisition.json",
                     "documentation_acquisition.json", "database_documentation_acquisition.json"):
        (OUT / filename).write_bytes((SOURCES / filename).read_bytes())
    (OUT / "source_acquisition.json").write_text(json.dumps(
        [{k: v for k, v in s.items() if k != "response"} for s in acquired], indent=2) + "\n")
    receipt = {
        "recorded_at": now, "kind": "reviewed_fiscal_input_admission",
        "baseline_before_sha256": sha256(before_bytes).hexdigest(),
        "baseline_after_sha256": sha256(new_bytes).hexdigest(),
        "archive_before": 37, "archive_after": 73, "diagnostics": diagnostics,
        "new_fiscal_records": [{k: r[k] for k in ("record_id", "cc", "series_id", "values",
            "period_basis", "fiscal_start_month", "definition_id", "information_cutoff",
            "first_observed_at", "admitted_at", "source_sha256")}
            for r in archive if r["record_id"] not in {x["record_id"] for x in old_archive}
            and r["correction_sequence"] == 0],
        "metadata_corrections": [{"record_id": r["record_id"], "supersedes": r["supersedes_record_id"],
                                 "cc": r["cc"], "series_id": r["series_id"]} for r in selected],
        "correction_reason": "Our normalization used October 1. IMF table and database appendices specify September 30. Forecast values are unchanged.",
        "country_update_dates": "Unknown; API last-modified is not the information cutoff.",
        "other_baseline_sections_unchanged": all(after[k] == v for k, v in before.items()
                                               if k not in ("forecast_archive", "retrieved_at")),
    }
    # Keep a concrete prepared receipt if the process is interrupted at replacement.
    (OUT / "admission_prepared.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    temporary = TARGET.with_suffix(".json.fiscal-next")
    temporary.write_bytes(new_bytes)
    os.replace(temporary, TARGET)
    assert sha256(TARGET.read_bytes()).hexdigest() == receipt["baseline_after_sha256"]
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    world = select_publications(archive, "WORLD", today=datetime.now(timezone.utc).date())[0]
    print(json.dumps({"admitted": True, "recorded_at": now, "new_fiscal_records": 8,
                      "corrected_cutoffs": 28, "archive_records": 73,
                      "baseline_sha256": receipt["baseline_after_sha256"],
                      "reviewed_world_record_id": world["record_id"]}))


if __name__ == "__main__":
    main()
