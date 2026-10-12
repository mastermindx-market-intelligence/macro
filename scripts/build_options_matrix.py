"""scripts/build_options_matrix.py — one-shot strike×expiry matrix publisher (Package E).

Builds options_structure.matrix/v1 payloads for one or more roots from the
ThetaData EOD store and optionally publishes to R2 under the key
    options_structure/matrix/<ROOT>.json
Exact bytes are retained first under matrix/history/<ROOT>/<SHA256>.json.

Usage:
    python -m scripts.build_options_matrix [--roots SPY QQQ ...] [--publish]
        [--out DIR] [--date YYYY-MM-DD]

Environment variables:
    THETADATA_STORE   Path to the ThetaData EOD store root (required for real data)
    R2_ENDPOINT       Cloudflare R2 endpoint URL
    R2_ACCESS_KEY_ID  R2 access key
    R2_SECRET_ACCESS_KEY  R2 secret
    R2_BUCKET         R2 bucket name

Defaults:
    --roots   : SPY QQQ IWM NVDA TSLA AAPL MSFT META AMD GOOGL MU ARM
    --out     : data/live_flow_out/options_matrix/
    --publish : disabled unless flag is passed

SCHEDULING NOTE:
    Wired as a launchd lane (NOT daily.yml — the GH runner cannot see the theta store).
    ops/launchd/com.macro.optionsmatrix.plist fires weekdays at 19:00 local via
    ops/launchd/run_with_env.sh + /Users/chriswong/flow-ops-wt/.env.
    The runner ops/launchd/run_options_matrix.sh uses a conservative SPY OI
    readiness floor with bounded retry (20-min sleep, max 6 attempts = 2h window)
    before invoking this script with --publish. This builder then resolves the
    bounded common OI/EOD/Greeks source session; the runner never chooses it.
    Set MATRIX_FRESHNESS_BYPASS=1 to skip the wait (one-shot smoke / CI).

Isolated per-root: failures skip that root, allow healthy roots to finish, and
make the final process status nonzero. Source failures never replace a dated
valid matrix with a newly built empty artifact.
DISPLAY-TIER: no ranking, scoring, or money-path interaction.
OI TIMING LAW: all OI uses OI[t-1]; delta_oi = OI[t-1] − OI[t-2] (both lagged).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import stat
import tempfile
from pathlib import Path

# ── repo path ─────────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from engine.options_matrix import build_matrix
from engine import options_matrix_retention as retention
from engine.options_matrix_retention import retain_snapshot
from engine.thetadata_store import clear_parquet_cache

log = logging.getLogger(__name__)

# ── R2 key prefix ─────────────────────────────────────────────────────────────
R2_PREFIX = "options_structure/matrix/"

# ── default roots ─────────────────────────────────────────────────────────────
DEFAULT_ROOTS = [
    "SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL", "MSFT", "META", "AMD", "GOOGL",
    "MU", "ARM",
]


# --------------------------------------------------------------------------- #
# R2 helpers (mirrors scripts/build_options_hub_nightly.py pattern exactly)    #
# --------------------------------------------------------------------------- #

def _r2_client():
    """Build a boto3 S3 client for R2, or None if creds are absent."""
    ep = os.environ.get("R2_ENDPOINT")
    ak = os.environ.get("R2_ACCESS_KEY_ID")
    sk = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (ep and ak and sk):
        return None
    try:
        import boto3
        from botocore.config import Config
        kw = dict(
            region_name="auto",
            signature_version="s3v4",
            max_pool_connections=16,
            retries={"max_attempts": 3, "mode": "standard"},
        )
        try:
            cfg = Config(**kw,
                         request_checksum_calculation="when_required",
                         response_checksum_validation="when_required")
        except TypeError:
            cfg = Config(**kw)
        return boto3.client(
            "s3",
            endpoint_url=ep,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            config=cfg,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("options_matrix_builder: R2 client build failed: %s", e)
        return None


def _upload_r2(s3, bucket: str, raw: bytes, r2_key: str) -> bool:
    """Advance the head using the exact bytes already retained and read back."""
    try:
        s3.put_object(Bucket=bucket, Key=r2_key, Body=raw,
                      ContentType="application/json")
        log.info("options_matrix_builder: R2 upload ok → %s", r2_key)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("options_matrix_builder: R2 upload failed for %s: %s", r2_key, e)
        return False


def _serialize(data: dict) -> bytes:
    """Serialize once, rejecting oversize output before any artifact write."""
    raw = bytearray()
    for chunk in json.JSONEncoder(allow_nan=False, default=str).iterencode(data):
        part = chunk.encode("utf-8")
        if len(raw) + len(part) > retention.MAX_MATRIX_BYTES:
            raise retention.HistoricalUnavailable("matrix exceeds byte limit")
        raw.extend(part)
    return bytes(raw)


def _write_bytes(path: Path, raw: bytes) -> None:
    """Replace a local mutable head atomically only after retention succeeds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".matrix-", delete=False) as handle:
            temporary = Path(handle.name)
            mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
            os.fchmod(handle.fileno(), mode)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _retain_local(out_dir: Path, ref: retention.SnapshotReference, raw: bytes) -> None:
    """Retain beside the existing output, without another producer or manifest."""
    retention.verify_snapshot(ref, raw)
    path = out_dir / "history" / ref.root / f"{ref.sha256}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        if not path.exists():
            # Publish only a complete, synced inode. A failed preparation must
            # never reserve the immutable final key with truncated bytes.
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=".matrix-history-", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                os.fchmod(handle.fileno(), 0o644)
                if handle.write(raw) != len(raw):
                    raise OSError("short local retained write")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                # A racing key belongs to its existing writer. Verify below;
                # never replace it, even when its bytes are corrupt.
                pass
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    with path.open("rb") as handle:
        retained = handle.read(ref.byte_length + 1)
    retention.verify_snapshot(ref, retained)
    if retained != raw:
        raise retention.HistoricalUnavailable("local retained byte collision")


def _payload_session(data: dict) -> str | None:
    try:
        return retention.source_session(data)
    except retention.HistoricalUnavailable:
        return None


def _existing_usable_session(path: Path) -> tuple[str | None, str | None]:
    """Return (session, error) for a usable prior artifact.

    Empty/null historical artifacts are safe to replace because they carry no
    measured cells. A usable artifact with an unreadable/missing session is
    preserved fail-closed rather than silently overwritten.
    """
    if not path.exists():
        return None, None
    try:
        if path.stat().st_size > retention.MAX_MATRIX_BYTES:
            raise retention.HistoricalUnavailable("existing matrix exceeds byte limit")
        with path.open("rb") as handle:
            raw = handle.read(retention.MAX_MATRIX_BYTES + 1)
        if not 0 < len(raw) <= retention.MAX_MATRIX_BYTES:
            raise retention.HistoricalUnavailable("existing matrix exceeds byte limit")
        # Preserve legacy objects without modern schema/root fields, while
        # sharing the retained-byte decoder's strict JSON and identity rules.
        current = json.loads(
            raw.decode("utf-8"), object_pairs_hook=retention._unique_object,
            parse_constant=retention._nonfinite, parse_float=retention._finite_float,
        )
        session = retention.source_session(current)
        if "schema" in current and current["schema"] != retention.SCHEMA:
            raise retention.HistoricalUnavailable("existing matrix schema mismatch")
        if "root" in current and retention.validate_root(current["root"]) != path.stem:
            raise retention.HistoricalUnavailable("existing matrix root mismatch")
    except Exception as exc:  # noqa: BLE001
        return None, f"existing artifact unreadable: {exc}"
    if not current.get("cells") or current.get("spot") is None:
        return None, None
    if session is None:
        return None, "existing usable artifact lacks a trustworthy source session"
    return session, None


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Build strike×expiry options matrix (Package E)."
    )
    parser.add_argument(
        "--roots", nargs="+", default=DEFAULT_ROOTS,
        metavar="ROOT",
        help="Option root symbols to process (default: SPY QQQ IWM NVDA TSLA AAPL MSFT META AMD GOOGL MU ARM)",
    )
    parser.add_argument(
        "--publish", action="store_true", default=False,
        help="Upload outputs to R2 under options_structure/matrix/<ROOT>.json",
    )
    parser.add_argument(
        "--out", default=None,
        help="Local output directory (default: data/live_flow_out/options_matrix/)",
    )
    parser.add_argument(
        "--date", default=None,
        help="Reference date YYYY-MM-DD (default: most recent OI date per root)",
    )
    args = parser.parse_args()

    # ── resolve output dir ───────────────────────────────────────────────────
    out_dir = Path(args.out) if args.out else (_REPO / "data" / "live_flow_out" / "options_matrix")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── store path — canonical resolver (WP-RESOLVER) ─────────────────────────
    # THETADATA_STORE env → data_dir()/thetadata_eod → ops-wt, content-checked.
    # Fail-loud contract: this builder publishes matrices — when no store
    # resolves it exits nonzero instead of writing/uploading no-data payloads.
    from engine.thetadata_store import resolve_thetadata_store
    theta_store = resolve_thetadata_store(required=False, purpose="build_options_matrix")
    if theta_store is None:
        log.error(
            "options_matrix_builder: no ThetaData store resolves — exiting "
            "nonzero WITHOUT writing/publishing no-data matrices "
            "(set THETADATA_STORE or fix the store path)")
        sys.exit(1)

    # ── R2 setup ─────────────────────────────────────────────────────────────
    s3 = None
    bucket = None
    if args.publish:
        s3 = _r2_client()
        bucket = os.environ.get("R2_BUCKET")
        if s3 is None or not bucket:
            log.error(
                "options_matrix_builder: --publish requested but R2 creds incomplete "
                "(need R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET)"
            )
            sys.exit(1)  # --publish is an obligation, not an optional success claim.

    # ── per-root loop ─────────────────────────────────────────────────────────
    results: dict[str, dict] = {}   # root → {"n_cells", "uploaded", "error"}

    for root in args.roots:
        root = root.upper()
        try:
            try:
                retention.validate_root(root)
                payload = build_matrix(root, store=theta_store, asof=args.date)
            except Exception as e:  # noqa: BLE001
                log.error("options_matrix_builder: build failed for %s — %s", root, e)
                results[root] = {"n_cells": 0, "uploaded": False, "error": str(e)}
                continue

            # A null matrix is a source failure, not a fresh observation of zero exposure.
            # Preserve any existing dated artifact; its own session remains the honest clock.
            no_data = payload.get("_no_data_reason")
            if no_data or not payload.get("cells") or payload.get("spot") is None:
                reason = no_data or "no usable matrix cells or underlying reference"
                log.error("options_matrix_builder: withheld %s — %s", root, reason)
                results[root] = {
                    "n_cells": 0, "uploaded": False, "error": None, "no_data": reason,
                }
                continue

            local_path = out_dir / f"{root}.json"
            new_session = _payload_session(payload)
            if new_session is None:
                reason = "candidate matrix lacks a trustworthy source session"
                log.error("options_matrix_builder: withheld %s — %s", root, reason)
                results[root] = {
                    "n_cells": 0, "uploaded": False, "error": reason, "no_data": None,
                }
                continue

            existing_session, existing_error = _existing_usable_session(local_path)
            if existing_error is not None:
                log.error("options_matrix_builder: withheld %s — %s", root, existing_error)
                results[root] = {
                    "n_cells": 0, "uploaded": False, "error": existing_error, "no_data": None,
                }
                continue
            if existing_session is not None and new_session < existing_session:
                reason = (
                    f"resolved session {new_session} older than existing artifact "
                    f"{existing_session}"
                )
                log.error("options_matrix_builder: withheld %s — %s", root, reason)
                results[root] = {
                    "n_cells": 0, "uploaded": False, "error": None, "no_data": reason,
                }
                continue

            # Both immutable copies precede either mutable head. A failed or
            # uncertain retention operation preserves the prior current matrix.
            try:
                raw = _serialize(payload)
                ref = retention.reference_for_bytes(root, raw)
                _retain_local(out_dir, ref, raw)
                if args.publish:
                    retain_snapshot(s3, bucket, ref, raw)
                _write_bytes(local_path, raw)
                log.info(
                    "options_matrix_builder: wrote %s (%d cells, session=%s)",
                    local_path, len(payload.get("cells", [])), new_session,
                )
            except Exception as e:  # noqa: BLE001
                log.error("options_matrix_builder: write failed for %s — %s", root, e)
                results[root] = {"n_cells": 0, "uploaded": False, "error": str(e)}
                continue

            # upload to R2
            uploaded = False
            if args.publish and s3 and bucket:
                r2_key = f"{R2_PREFIX}{root}.json"
                uploaded = _upload_r2(s3, bucket, raw, r2_key)

            n_cells = len(payload.get("cells", []))
            results[root] = {
                "n_cells":   n_cells,
                "uploaded":  uploaded,
                "error":     "R2 publication failed" if args.publish and not uploaded else None,
                "no_data":   None,
                "session":   new_session,
                "version_ref": ref.version_ref,
            }
        finally:
            # Bound memory even when a build/write/source guard raises or continues.
            clear_parquet_cache()

    # ── summary ───────────────────────────────────────────────────────────────
    published  = [r for r, d in results.items() if d.get("uploaded")]
    failed     = [r for r, d in results.items() if d.get("error")]
    no_data    = [r for r, d in results.items() if d.get("no_data")]
    healthy    = [r for r, d in results.items() if not d.get("error") and not d.get("no_data")]

    print("\n--- options_matrix build summary ---")
    for root, d in results.items():
        status = "UPLOADED" if d.get("uploaded") else ("ERROR" if d.get("error") else "local-only")
        no_data_note = f" [{d['no_data']}]" if d.get("no_data") else ""
        print(f"  {root:10s}  cells={d['n_cells']:4d}  {status}{no_data_note}")
    health = "OK" if not failed and not no_data else ("FAILED" if not healthy else "DEGRADED")
    print(f"\npublished={published}  failed={failed}  no_data={no_data}")
    print(f"health={health}  healthy={healthy}  failed={failed}  no_data={no_data}")
    print("---")
    if failed or no_data:
        sys.exit(1)


if __name__ == "__main__":
    main()
