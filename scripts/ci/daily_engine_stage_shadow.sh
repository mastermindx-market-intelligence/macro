#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Original engine/prophet_stage_shadow body; workflow-size headroom, no business change.
set -e
set +e
STAGE_BASELINE="${RUNNER_TEMP}/prophet-stage-${GITHUB_RUN_ID}.before.json"
STAGE_DELTA="${RUNNER_TEMP}/prophet-stage-${GITHUB_RUN_ID}.delta.tsv"
export STAGE_BASELINE STAGE_DELTA
python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["GITHUB_WORKSPACE"])
owned = (
    "data/prophet_stage_shadow/ledger.jsonl",
    "data/prophet_stage_shadow/revisions.jsonl",
    "data/prophet_stage_shadow/summary.json",
)

def fingerprint(path: Path) -> str:
    if path.is_symlink():
        raise RuntimeError(f"refusing symlinked Stage-shadow output: {path}")
    return (
        f"{path.stat().st_mode & 0o7777:04o}:"
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}"
    )

before = {
    rel: fingerprint(root / rel)
    for rel in owned
    if (root / rel).is_file()
}
Path(os.environ["STAGE_BASELINE"]).write_text(
    json.dumps(before, sort_keys=True), encoding="utf-8"
)
PY
baseline_rc=$?
if [ "$baseline_rc" -ne 0 ]; then
  echo "succeeded=false" >> "$GITHUB_OUTPUT"
  echo "::warning title=Prophet Stage manifest::could not fingerprint the accepted Stage-shadow baseline (rc=$baseline_rc); accrual checkpoint withheld"
  exit 0
fi
echo "::group::build_prophet_stage_shadow (tag + grade + summarize)"
python -m scripts.build_prophet_stage_shadow > "$RUNNER_TEMP/prophet_stage_shadow.log" 2>&1; rc=$?
cat "$RUNNER_TEMP/prophet_stage_shadow.log"
echo "::endgroup::"
if [ "$rc" -ne 0 ]; then
  echo "succeeded=false" >> "$GITHUB_OUTPUT"
  echo "::warning title=build_prophet_stage_shadow::rc=$rc (non-fatal; accrual checkpoint withheld)"
  exit 0
fi
python3 - <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

from engine import prophet_stage_shadow as shadow

root = Path(os.environ["GITHUB_WORKSPACE"])
data_root = root / "data"
site_root = root / "site"
owned = (
    "data/prophet_stage_shadow/ledger.jsonl",
    "data/prophet_stage_shadow/revisions.jsonl",
    "data/prophet_stage_shadow/summary.json",
)

def fingerprint(path: Path) -> str:
    if path.is_symlink():
        raise RuntimeError(f"refusing symlinked Stage-shadow output: {path}")
    return (
        f"{path.stat().st_mode & 0o7777:04o}:"
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}"
    )

before = json.loads(
    Path(os.environ["STAGE_BASELINE"]).read_text(encoding="utf-8")
)
after = {
    rel: fingerprint(root / rel)
    for rel in owned
    if (root / rel).is_file()
}
deleted = sorted(set(before) - set(after))
if deleted:
    print(
        "::error title=Prophet Stage output deletion::"
        + ", ".join(deleted)
        + " — append-only checkpoint refuses deletions",
        flush=True,
    )
    raise SystemExit(2)

summary_file = root / "data/prophet_stage_shadow/summary.json"
if not summary_file.is_file():
    print("::error title=Prophet Stage summary missing::no effective projection was emitted", flush=True)
    raise SystemExit(3)
summary = json.loads(summary_file.read_text(encoding="utf-8"))
projection = shadow._project_shadow_ledger(data_root)
expected_entries = shadow.collect_prophet_entries(site_root, data_root)
missing_ids, unexpected_ids = shadow.projection_membership_gaps(
    expected_entries, projection
)
receipt = summary.get("integrity_projection") or {}
if (
    summary.get("schema") != shadow.SUMMARY_SCHEMA
    or projection.authority_error is not None
    or receipt.get("authority_error") is not None
    or receipt.get("raw_rows") != projection.raw_count
    or receipt.get("revision_rows") != projection.revision_count
    or receipt.get("effective_rows") != len(projection.rows)
    or summary.get("n_entries") != len(projection.rows)
    # Lossless cohort contract: collect_prophet_entries already applies
    # current canonical quarantine. Every remaining expected plan must
    # have exactly one effective shadow row, and no orphan row may survive.
    or missing_ids
    or unexpected_ids
):
    print(
        "::error title=Prophet Stage projection mismatch::"
        "raw ledger, append-only revisions and summary do not form one "
        "validated effective projection; checkpoint withheld",
        flush=True,
    )
    raise SystemExit(4)

changed = sorted(path for path, value in after.items() if before.get(path) != value)
with Path(os.environ["STAGE_DELTA"]).open("w", encoding="utf-8") as handle:
    for rel in changed:
        handle.write(f"{rel}\t{before.get(rel, 'MISSING')}\t{after[rel]}\n")
PY
manifest_rc=$?
if [ "$manifest_rc" -eq 0 ]; then
  echo "succeeded=true" >> "$GITHUB_OUTPUT"
  echo "delta_manifest=$STAGE_DELTA" >> "$GITHUB_OUTPUT"
else
  echo "succeeded=false" >> "$GITHUB_OUTPUT"
  echo "::warning title=Prophet Stage manifest::accrual returned 0 but its effective projection could not be proven (rc=$manifest_rc); checkpoint withheld"
fi
exit 0
