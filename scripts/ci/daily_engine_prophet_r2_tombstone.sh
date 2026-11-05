#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# engine original enforce Prophet R2 index tombstone (unconditional); size headroom, business body unchanged.
set -e
python3 - <<'PY'
import os

from scripts.build_prophet import _r2_client

# Forbidden public key literal (DEC:B1-PROPHET-PUBLIC-SPLIT), named
# here rather than imported — the tombstone check/delete never
# needs a live index, only the key it must never let stand.
FORBIDDEN_INDEX_KEY = "prophet/index.json"

client = _r2_client()
if client is None:
    print(
        "::notice title=Prophet R2 tombstone skipped::"
        "R2 credentials unavailable; nothing to enforce",
        flush=True,
    )
    raise SystemExit(0)
from botocore.exceptions import ClientError

bucket = os.environ.get("R2_BUCKET") or "mastermindx"

try:
    client.head_object(Bucket=bucket, Key=FORBIDDEN_INDEX_KEY)
except ClientError as exc:
    response = exc.response or {}
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    code = str((response.get("Error") or {}).get("Code") or "")
    if status == 404 or code in {"404", "NoSuchKey", "NotFound"}:
        print(
            "::notice title=Prophet R2 tombstone::"
            f"{FORBIDDEN_INDEX_KEY} already absent",
            flush=True,
        )
        raise SystemExit(0)
    print(
        "::warning title=Prophet R2 tombstone check failed::"
        f"could not verify {FORBIDDEN_INDEX_KEY} absence: {exc}",
        flush=True,
    )
    raise SystemExit(0)

try:
    client.delete_object(Bucket=bucket, Key=FORBIDDEN_INDEX_KEY)
except Exception as exc:  # noqa: BLE001 — deletion failure is non-fatal
    print(
        "::warning title=Prophet R2 tombstone delete failed::"
        f"forbidden public object {FORBIDDEN_INDEX_KEY} could not be removed: {exc}",
        flush=True,
    )
    raise SystemExit(0)
print(
    "::notice title=Prophet R2 tombstone::"
    f"removed forbidden public object {FORBIDDEN_INDEX_KEY}",
    flush=True,
)
PY
