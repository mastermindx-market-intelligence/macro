#!/usr/bin/env python3
"""Read two existing SRC-A1 Git blobs; print EXP-1 internal inspection JSON."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# Direct invocation works from an explicit file path without installation.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.k3e_expectation_surface import (
    ALIASES_PATH, ATTEMPTS_PATH, OBSERVATIONS_PATH, QueryRefusal,
    inspect_expectation_surface, parse_utc,
)


def _git(repository, *arguments):
    environment = os.environ.copy()
    environment["GIT_NO_LAZY_FETCH"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    # Transport denial also fences older Git versions lacking NO_LAZY_FETCH.
    environment["GIT_ALLOW_PROTOCOL"] = ""
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QueryRefusal("LOCAL_GIT_READ_FAILED") from exc
    if result.returncode:
        raise QueryRefusal("SOURCE_OBJECT_UNAVAILABLE_WITHOUT_FETCH")
    return result.stdout


def _read_verified_blob(root, revision, path):
    address = revision + ":" + path
    blob = _git(root, "rev-parse", "--verify", address).strip().decode("ascii")
    if not re.fullmatch(r"[0-9a-f]{40}", blob):
        raise QueryRefusal("INVALID_SOURCE_BLOB_ID")
    if _git(root, "cat-file", "-t", blob).strip() != b"blob":
        raise QueryRefusal("SOURCE_INPUT_MUST_BE_BLOB")
    raw = _git(root, "show", address)
    actual_blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()
    if actual_blob != blob:
        raise QueryRefusal("SOURCE_BLOB_BYTES_MISMATCH")
    return raw, {"git_blob_id": blob, "sha256": hashlib.sha256(raw).hexdigest()}


def load_frozen_source(repository, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        raise QueryRefusal("FULL_IMMUTABLE_SOURCE_REVISION_REQUIRED")
    root = Path(repository)
    if not root.is_dir():
        raise QueryRefusal("REPOSITORY_DIRECTORY_REQUIRED")
    if _git(root, "cat-file", "-t", revision).strip() != b"commit":
        raise QueryRefusal("SOURCE_REVISION_MUST_BE_COMMIT")
    inputs = {}
    frames = {}
    try:
        import pandas as pd
    except ImportError as exc:
        raise QueryRefusal("PARQUET_READER_UNAVAILABLE") from exc
    for path in (OBSERVATIONS_PATH, ATTEMPTS_PATH):
        raw, entry = _read_verified_blob(root, revision, path)
        inputs[path] = entry
        try:
            frame = pd.read_parquet(io.BytesIO(raw))
            # Pandas nan/NA represent parquet nulls; convert them without
            # converting genuine zero into missingness.
            frames[path] = frame.astype(object).where(pd.notna(frame), None)
        except Exception as exc:
            raise QueryRefusal("INVALID_PARQUET_INPUT") from exc
    observation_required = {
        "observation_id", "collection_session_id", "attempt_id", "provider",
        "provider_record_class", "provider_payload_hash", "ticker_compat",
        "metric", "horizon_label_raw", "observation_type", "value",
        "missingness_reason", "provider_observed_at", "system_observed_at",
    }
    attempt_required = {"attempt_id", "collection_session_id", "provider",
                        "ticker_compat", "attempted_at", "completed_at", "status",
                        "response_payload_hash"}
    for path, required in ((OBSERVATIONS_PATH, observation_required),
                           (ATTEMPTS_PATH, attempt_required)):
        if not required.issubset(frames[path].columns):
            raise QueryRefusal("SOURCE_SCHEMA_COLUMNS_MISSING")
    return (frames[OBSERVATIONS_PATH].to_dict("records"),
            frames[ATTEMPTS_PATH].to_dict("records"),
            {"source_revision": revision, "inputs": inputs})


def load_frozen_aliases(repository, revision):
    root = Path(repository)
    listing = _git(root, "ls-tree", revision, "--", ALIASES_PATH).strip()
    if not listing:
        return [], dict(absent_at_revision=True)
    try:
        import pandas as pd
    except ImportError as exc:
        raise QueryRefusal("PARQUET_READER_UNAVAILABLE") from exc
    raw, entry = _read_verified_blob(root, revision, ALIASES_PATH)
    try:
        frame = pd.read_parquet(io.BytesIO(raw))
        frame = frame.astype(object).where(pd.notna(frame), None)
    except Exception as exc:
        raise QueryRefusal("INVALID_PARQUET_INPUT") from exc
    required = {"vendor", "vendor_symbol", "security_id", "valid_from",
                  "valid_to", "ingested_at"}
    if not required.issubset(frame.columns):
        raise QueryRefusal("SOURCE_SCHEMA_COLUMNS_MISSING")
    return frame.to_dict("records"), entry


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise QueryRefusal("INVALID_CLI_ARGUMENTS")


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--metric", required=True, choices=("EPS", "revenue"))
    parser.add_argument("--horizon", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--provider", default="yfinance")
    try:
        args = parser.parse_args(argv)
        parse_utc(args.as_of)
        observations, attempts, provenance = load_frozen_source(
            args.repository, args.source_revision)
        records, entry = load_frozen_aliases(args.repository, args.source_revision)
        provenance["inputs"][ALIASES_PATH] = entry
        result = inspect_expectation_surface(
            observations, attempts, source_provenance=provenance,
            ticker=args.ticker, metric=args.metric, horizon=args.horizon,
            as_of=args.as_of, provider=args.provider,
            identity_aliases=records)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except QueryRefusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": exc.reason}), file=sys.stderr)
        return 2
    except (TypeError, ValueError, OverflowError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": "NON_JSON_SOURCE_VALUE"}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
