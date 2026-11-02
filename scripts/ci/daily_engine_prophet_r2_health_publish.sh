#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job `engine`, step `publish Prophet public health receipt to R2`.
# 2026-11-02 512KB processing-cap diet (tests/test_workflow_file_size.py): #9774 took daily.yml to 488,050 B > 487,000.
# Env comes from the step's `env:` block, which stays in the YAML.
# Invoked as: bash scripts/ci/daily_engine_prophet_r2_health_publish.sh
set -e  # mirror GitHub's default `bash -e {0}` step shell — daily.yml declares no shell:

set -euo pipefail
R2_INDEX_FILE="$(mktemp "${RUNNER_TEMP}/prophet-r2-index.XXXXXX.json")"
cleanup_prophet_r2() { rm -f -- "$R2_INDEX_FILE"; }
trap cleanup_prophet_r2 EXIT

verify_prophet_checkpoint_current() {
  git fetch origin +refs/heads/main:refs/remotes/origin/main \
    || return 1
  git merge-base --is-ancestor "$PROPHET_CHECKPOINT_SHA" origin/main \
    || return 1
  git diff --quiet "$PROPHET_CHECKPOINT_SHA" origin/main -- \
    data/prophet \
    data/prophet_arena \
    site/prophet
}

if ! verify_prophet_checkpoint_current; then
  echo "::warning title=Prophet R2 publish superseded::checkpoint $PROPHET_CHECKPOINT_SHA is not the current origin/main Prophet projection; preserving the newer R2/main authority"
  exit 0
fi
git show "${PROPHET_CHECKPOINT_SHA}:site/prophet/index.json" > "$R2_INDEX_FILE"
ACTUAL_SHA256="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$R2_INDEX_FILE")"
if [ "$ACTUAL_SHA256" != "$PROPHET_INDEX_SHA256" ]; then
  echo "::error title=Prophet R2 publish hash mismatch::commit bytes do not match the checkpoint output; refusing R2 upload"
  exit 1
fi
# Close the fetch/hash window as far as the object store permits. R2
# has no compare-and-swap against a Git ref, so a second main proof is
# the last action before the single-object upload.
if ! verify_prophet_checkpoint_current; then
  echo "::warning title=Prophet R2 publish superseded::origin/main Prophet state advanced during verification; preserving the newer publication"
  exit 0
fi
python3 - "$R2_INDEX_FILE" <<'PY'
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_prophet import (
    R2_HEALTH_KEY,
    _r2_client,
    build_public_health_projection,
    guarded_put_object,
)

local_path = Path(sys.argv[1])
client = _r2_client()
if client is None:
    print(
        "::warning title=Prophet R2 credentials unavailable::"
        "guarded Git checkpoint landed; R2 remained unchanged",
        flush=True,
    )
    raise SystemExit(0)
from botocore.exceptions import ClientError

bucket = os.environ.get("R2_BUCKET") or "mastermindx"
expected_sha = os.environ["PROPHET_INDEX_SHA256"]
checkpoint_sha = os.environ["PROPHET_CHECKPOINT_SHA"]
published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

index = json.loads(local_path.read_text(encoding="utf-8"))
health_payload = build_public_health_projection(
    index,
    checkpoint_sha=checkpoint_sha,
    index_sha256=expected_sha,
    published_at=published_at,
)
health_bytes = json.dumps(
    health_payload, allow_nan=False, default=str, indent=2,
).encode("utf-8")

# Snapshot the destination generation first. The conditional put below
# makes any concurrent R2 writer win rather than be overwritten.
try:
    current = client.head_object(Bucket=bucket, Key=R2_HEALTH_KEY)
except ClientError as exc:
    response = exc.response or {}
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    code = str((response.get("Error") or {}).get("Code") or "")
    if status == 404 or code in {"404", "NoSuchKey", "NotFound"}:
        condition = {"IfNoneMatch": "*"}
    else:
        print(
            "::error title=Prophet R2 preflight failed::"
            "could not read the current object generation; upload withheld",
            flush=True,
        )
        raise SystemExit(1) from exc
else:
    etag = str(current.get("ETag") or "")
    metadata = current.get("Metadata") or {}
    if (
        metadata.get("git-checkpoint") == checkpoint_sha
        and metadata.get("sha256") == expected_sha
    ):
        print(
            "::notice title=Prophet R2 already current::"
            "the guarded checkpoint hash is already published",
            flush=True,
        )
        raise SystemExit(0)
    if not etag:
        print(
            "::error title=Prophet R2 preflight failed::"
            "current object supplied no ETag for a conditional update",
            flush=True,
        )
        raise SystemExit(1)
    condition = {"IfMatch": etag}

# Re-prove Git after the R2 generation snapshot. If main or R2 moves
# after its respective proof, the conditional put rejects the race.
git_checks = (
    ["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"],
    ["git", "merge-base", "--is-ancestor", checkpoint_sha, "origin/main"],
    [
        "git", "diff", "--quiet", checkpoint_sha, "origin/main", "--",
        "data/prophet", "data/prophet_arena", "site/prophet",
    ],
)
if any(subprocess.run(cmd, check=False).returncode for cmd in git_checks):
    print(
        "::warning title=Prophet R2 publish superseded::"
        "current main changed during R2 preflight; upload withheld",
        flush=True,
    )
    raise SystemExit(0)

try:
    guarded_put_object(
        client,
        bucket=bucket,
        key=R2_HEALTH_KEY,
        Body=health_bytes,
        ContentType="application/json",
        Metadata={
            "git-checkpoint": checkpoint_sha,
            "sha256": expected_sha,
        },
        **condition,
    )
except ClientError as exc:
    status = ((exc.response or {}).get("ResponseMetadata") or {}).get(
        "HTTPStatusCode"
    )
    if status == 412:
        print(
            "::warning title=Prophet R2 publish superseded::"
            "the R2 object advanced concurrently; preserving that writer",
            flush=True,
        )
        raise SystemExit(0) from exc
    print(
        "::error title=Prophet R2 upload failed::"
        "guarded Git checkpoint landed but its verified health receipt did not reach R2",
        flush=True,
    )
    raise SystemExit(1) from exc
print(
    "::notice title=Prophet R2 published::"
    "uploaded the public health receipt for the guarded Git checkpoint",
    flush=True,
)
PY
