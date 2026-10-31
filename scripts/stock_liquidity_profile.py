"""Read the existing raw daily store for the per-stock liquidity projection.

This reader never restores a store, fetches a reference or writes an artifact.
The stock-library writer owns publication. Missing raw bars or currency-window
evidence remain unknown; the adjusted legacy chip is not a fallback source.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pyarrow.parquet as pq

from engine.liquidity_profile import project
from engine.liquidity_source_availability import coverage_clock, source_expected_session
from lib import nyse_calendar
from lib.massive_ticker import artifact_relative_path

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_SOURCE_ROWS = 50_000
MAX_DECODED_BYTES = 16 * 1024 * 1024


def read_profile(ticker: str, *, data_root: Path, recorded_at: datetime,
                 currency_evidence: dict | None = None) -> dict:
    """Return one typed projection from native producer inputs, with no effects.

    ``currency_evidence`` is an explicit qualified input, not inferred from a
    ticker, country, profile currency or a current-only reference. The
    stock-library caller adopts only the retained, exact dated-session receipt
    under stock_currency; missing evidence remains unknown.
    """
    try:
        expected = source_expected_session(recorded_at)
    except ValueError:
        return project(None, ticker=ticker, expected_session=None,
                       recorded_at=recorded_at, ingested_at=None,
                       source_sha256=None, currency_evidence=currency_evidence)
    kwargs = dict(ticker=ticker, expected_session=expected,
                  recorded_at=recorded_at, ingested_at=None,
                  source_sha256=None, currency_evidence=currency_evidence)
    if not isinstance(ticker, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^=-]{0,31}", ticker):
        result = project(None, **kwargs)
        result.update(status="READ_NO_COVERAGE", reason="IDENTITY_NOT_COVERED")
        return result
    root = Path(data_root) / "massive_stock_day"
    path = root / artifact_relative_path(ticker)
    if path.is_symlink():
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_NOT_REGULAR")
        return result
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
    except FileNotFoundError:
        return project(None, **kwargs)
    except OSError:
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_UNREADABLE")
        return result
    if len(raw) > MAX_SOURCE_BYTES:
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_OVER_BOUND")
        return result
    kwargs["source_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        parquet = pq.ParquetFile(io.BytesIO(raw))
        metadata = parquet.metadata
        decoded_bytes = sum(
            metadata.row_group(group).column(column).total_uncompressed_size
            for group in range(metadata.num_row_groups)
            for column in range(metadata.num_columns)
        )
        if metadata.num_rows > MAX_SOURCE_ROWS or decoded_bytes > MAX_DECODED_BYTES:
            result = project(None, **kwargs)
            result.update(status="READ_UNAVAILABLE", reason="SOURCE_OVER_BOUND")
            return result
        frame = pd.read_parquet(io.BytesIO(raw), columns=["close", "volume"])
    except Exception:  # malformed file is an unavailable read, never zero
        result = project(None, **kwargs)
        result.update(status="READ_UNAVAILABLE", reason="SOURCE_UNREADABLE")
        return result
    # Use the observed final bar only when it meets the provider's availability
    # floor and names a completed market session. A normal T+1 gap is explicit;
    # the pure projection still rejects future/malformed/gapped source rows.
    market_completed = nyse_calendar.expected_last_session(recorded_at)
    if isinstance(frame.index, pd.DatetimeIndex) and len(frame.index):
        final = frame.index[-1].date()
        if expected <= final <= market_completed:
            kwargs["expected_session"] = final
    if currency_evidence is None:
        receipt_path = Path(data_root) / "stock_currency" / artifact_relative_path(ticker).with_suffix(".json")
        try:
            if not receipt_path.is_symlink():
                with receipt_path.open("rb") as stream:
                    receipt_bytes = stream.read(3 * 1024 * 1024 + 1)
                if len(receipt_bytes) <= 3 * 1024 * 1024:
                    kwargs["currency_evidence"] = json.loads(receipt_bytes)
        except (OSError, ValueError, TypeError):
            pass
    # A store manifest's updated_at is not a ticker's ingestion time. Retain it
    # as a separately named observation rather than promoting it to known_at.
    store_updated_at = None
    try:
        with (root / "_manifest.json").open("rb") as stream:
            manifest_bytes = stream.read(8193)
        if len(manifest_bytes) <= 8192:
            value = json.loads(manifest_bytes).get("updated_at")
            stamp = datetime.fromisoformat(value) if isinstance(value, str) else None
            if stamp is not None and stamp.utcoffset() is not None and stamp <= recorded_at:
                store_updated_at = stamp.isoformat()
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    result = project(frame, **kwargs)
    result["store_updated_at"] = store_updated_at
    result["availability"] = coverage_clock(recorded_at)
    # This producer's parser fills a missing volume with zero. Its retained
    # parquet cannot distinguish that from genuine zero activity, so a window
    # containing zero cannot earn a qualified full-coverage turnover metric.
    if frame["volume"].tail(20).eq(0).any():
        result.update(status="READ_NO_COVERAGE", reason="ZERO_VOLUME_SOURCE_AMBIGUOUS",
                      metrics=None, sample_n=None, thinly_traded=None)
    return result


def write_record(path: Path, rec: dict, *, data_root: Path,
                 recorded_at: datetime) -> None:
    """Existing stock-library writer's one-record seam, with one added field.

    The caller supplies its existing output path; this function writes no
    index, board, source store or user state.
    """
    rec["liquidity_profile"] = read_profile(
        rec.get("ticker", ""), data_root=data_root, recorded_at=recorded_at)
    path.write_text(json.dumps(rec, default=str))


def adopt_native_profile(ticker: str, *, data_root: Path, site_root: Path,
                         served_root: Path, lock_path: Path,
                         recorded_at: datetime) -> dict:
    """Add one qualified profile through the native writer and release mutex.

    The local and served records may be different generations. Each keeps its
    own unrelated fields. The same rsync temp-write/rename mechanism used by
    macro-update publishes the two bounded candidates; no R2 object, universe
    manifest, account data or other site file is read or changed here.
    """
    import fcntl
    import subprocess
    import tempfile

    def stopped(reason: str, published: list[str] | None = None) -> dict:
        return {"status": "PARTIAL" if published else "REFUSED", "reason": reason,
                "published": published or []}

    if ticker != "MU":
        return stopped("TICKER_NOT_ADMITTED")
    if not isinstance(recorded_at, datetime) or recorded_at.utcoffset() is None:
        return stopped("INVALID_RECORDED_AT")
    if lock_path.is_symlink() or not lock_path.is_file():
        return stopped("EXISTING_RELEASE_LOCK_UNAVAILABLE")
    with lock_path.open("a+") as release_lock:
        try:
            fcntl.flock(release_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return stopped("RELEASE_BUSY")
        targets = {"native": site_root / "stockdata" / "MU.json",
                   "served": served_root / "stockdata" / "MU.json"}
        originals, records = {}, {}
        try:
            for name, path in targets.items():
                if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
                    return stopped("NATIVE_RECORD_NOT_REGULAR")
                with path.open("rb") as stream:
                    raw = stream.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    return stopped("NATIVE_RECORD_OVER_BOUND")
                record = json.loads(raw)
                if not isinstance(record, dict) or record.get("ticker") != ticker:
                    return stopped("NATIVE_IDENTITY_NOT_QUALIFIED")
                originals[name], records[name] = raw, record
        except (OSError, ValueError, TypeError):
            return stopped("NATIVE_RECORD_UNREADABLE")
        # Stage on the existing site filesystem; rsync itself creates its atomic
        # temporary file at each destination. Never use --inplace or --delete.
        with tempfile.TemporaryDirectory(prefix=".f08-profile-", dir=site_root.parent) as staging:
            candidates, profiles = {}, {}
            for name, record in records.items():
                directory = Path(staging) / name
                directory.mkdir()
                candidate = directory / "MU.json"
                write_record(candidate, dict(record), data_root=data_root, recorded_at=recorded_at)
                candidate.chmod(targets[name].stat().st_mode & 0o777)
                output = json.loads(candidate.read_bytes())
                profile = output.get("liquidity_profile", {})
                old_fields = {key: value for key, value in record.items() if key != "liquidity_profile"}
                new_fields = {key: value for key, value in output.items() if key != "liquidity_profile"}
                if old_fields != new_fields:
                    return stopped("UNRELATED_NATIVE_FIELDS_CHANGED")
                if profile.get("status") != "READ_OK" or profile.get("ticker") != ticker:
                    return stopped("NATIVE_PROFILE_NOT_QUALIFIED")
                candidates[name], profiles[name] = candidate, profile
            if profiles["native"] != profiles["served"]:
                return stopped("PRODUCER_INPUT_ADVANCED")
            planned = {name: {
                "before_sha256": hashlib.sha256(originals[name]).hexdigest(),
                "candidate_sha256": hashlib.sha256(candidates[name].read_bytes()).hexdigest(),
            } for name in targets}
            published = []
            for name, target in targets.items():
                # The mutex serializes macro-update. The exact byte check also
                # preserves a distinct producer that does not use that mutex.
                try:
                    current = target.read_bytes()
                except OSError:
                    return stopped("NATIVE_RECORD_UNREADABLE", published)
                if current != originals[name]:
                    return stopped("NATIVE_RECORD_ADVANCED", published)
                try:
                    result = subprocess.run(
                        ["rsync", "-a", "--min-size=1", "--", str(candidates[name]), str(target)],
                        capture_output=True, timeout=30, check=False)
                except subprocess.TimeoutExpired:
                    return {"status": "EFFECT_UNKNOWN", "reason": "ATOMIC_PUBLISH_TIMEOUT",
                            "published": published, "active_target": name, "planned_records": planned}
                except OSError:
                    return stopped("ATOMIC_PUBLISH_UNAVAILABLE", published)
                if result.returncode:
                    return {"status": "EFFECT_UNKNOWN", "reason": "ATOMIC_PUBLISH_FAILED",
                            "published": published, "active_target": name, "planned_records": planned}
                try:
                    verified = target.read_bytes() == candidates[name].read_bytes()
                except OSError:
                    verified = False
                if not verified:
                    return {"status": "EFFECT_UNKNOWN", "reason": "ATOMIC_PUBLISH_NOT_VERIFIED",
                            "published": published, "active_target": name, "planned_records": planned}
                published.append(name)
            return {"status": "NATIVE_PROFILE_PUBLISHED", "published": published,
                    "profile": profiles["native"],
                    "records": {name: {
                        "before_sha256": hashlib.sha256(originals[name]).hexdigest(),
                        "after_sha256": hashlib.sha256(targets[name].read_bytes()).hexdigest(),
                        "unrelated_fields_preserved": len(records[name]) - int("liquidity_profile" in records[name]),
                    } for name in targets}}


def main() -> int:
    import argparse
    from datetime import timezone
    from lib import config

    parser = argparse.ArgumentParser(description="Adopt one qualified native liquidity profile")
    parser.add_argument("--native-adopt", required=True, choices=["MU"])
    args = parser.parse_args()
    result = adopt_native_profile(
        args.native_adopt, data_root=config.data_dir(), site_root=config.site_dir(),
        served_root=config.ROOT / "site.served", lock_path=Path("/var/lock/macro-update.lock"),
        recorded_at=datetime.now(timezone.utc))
    print(json.dumps(result, allow_nan=False))
    return 0 if result["status"] == "NATIVE_PROFILE_PUBLISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
