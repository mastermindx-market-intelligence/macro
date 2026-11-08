"""Parquet time-series store. The repo is the database.

Rules:
- One parquet per logical series/table: data/<group>/<name>.parquet
- Default upsert() merges on the index and never drops rows present only on disk.
  This makes the FRED OAS cache permanent despite its rolling fetch window.
  Adjusted-series overwrite_overlap replaces its complete refresh span, but
  rejects responses that would move the stored latest timestamp backwards.
- Outlier guard (Phase 4): |daily change| > N sigma is quarantined to
  data/quarantine/, not silently ingested.
"""
from __future__ import annotations

import json
import base64
import io
import logging
import hashlib
import math
import numbers
import re
import os
import stat
import tempfile
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from lib import config

log = logging.getLogger(__name__)

OUTLIER_SIGMA = 8
OUTLIER_MIN_OBS = 60

# Explicit Yahoo-runner opt-in only. These are observations of future captures,
# not a replacement price store, Trial Ledger, or historical availability oracle.
YAHOO_CAPTURE_COHORT = frozenset({"XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"})
_CAPTURE_IMAGE_LIMIT = 4 * 1024 * 1024
_CAPTURE_ROW_LIMIT = 12_000


def _availability_now() -> datetime:
    return datetime.now(timezone.utc)


def _availability_clock(value: datetime) -> str:
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() != timezone.utc.utcoffset(value)):
        raise ValueError("availability clock must be aware UTC")
    return value.isoformat(timespec="microseconds")


def _availability_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _availability_image(frame: pd.DataFrame) -> bytes:
    """Documented normalized JSON values, never vendor wire/parquet bytes.

    Ordered naive midnight dates and fixed column order are preserved without
    imputation. Missing numeric cells become JSON null; infinities are refused.
    """
    if (not isinstance(frame, pd.DataFrame) or frame.empty
            or len(frame) > _CAPTURE_ROW_LIMIT or not frame.columns.is_unique
            or "close" not in frame.columns
            or not set(frame.columns) <= {"close", "close_price", "volume"}
            or not isinstance(frame.index, pd.DatetimeIndex)
            or frame.index.tz is not None or frame.index.hasnans
            or not frame.index.is_unique or not frame.index.is_monotonic_increasing
            or not frame.index.equals(frame.index.normalize())):
        raise ValueError("availability frame contract refused")
    columns = [c for c in ("close", "close_price", "volume") if c in frame.columns]
    rows = []
    for stamp, values in zip(frame.index, frame[columns].itertuples(index=False, name=None)):
        cells = []
        for value in values:
            if value is None or value is pd.NA:
                cells.append(None)
            elif isinstance(value, (bool,)) or not isinstance(value, numbers.Real):
                raise ValueError("availability cell must be numeric or missing")
            elif isinstance(value, numbers.Integral):
                if abs(int(value)) > 2**53 - 1:
                    raise ValueError("availability integer exceeds exact JSON range")
                cells.append(int(value))
            elif math.isnan(float(value)):
                cells.append(None)
            elif not math.isfinite(float(value)):
                raise ValueError("availability infinite value refused")
            else:
                cells.append(float(value))
        rows.append([stamp.date().isoformat(), *cells])
    data = _availability_json({"encoding": "dated_numeric_frame_json.v1",
                               "columns": columns, "rows": rows})
    if len(data) > _CAPTURE_IMAGE_LIMIT:
        raise ValueError("availability image exceeds byte limit")
    return data


def _availability_fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _availability_dir(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o022):
        raise ValueError("availability directory ownership or mode refused")
    _availability_fsync_dir(path.parent)


def _availability_verify_existing(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) & 0o077 or before.st_size != len(data)):
            raise ValueError("availability existing object refused")
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            actual = source.read(len(data) + 1)
        after = os.fstat(descriptor)
        if (actual != data or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("availability immutable object collision")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _availability_publish(directory: Path, data: bytes) -> str:
    """Atomic no-clobber publication. Never remove an existing object on failure."""
    digest = hashlib.sha256(data).hexdigest()
    target = directory / (digest + ".json")
    descriptor, temporary = tempfile.mkstemp(prefix=".partial-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError:
            _availability_verify_existing(target, data)
        _availability_fsync_dir(directory)
    finally:
        # Only our exclusive temporary name is removed; any published object stays.
        os.unlink(temporary)
        _availability_fsync_dir(directory)
    return digest


def capture_yahoo_observation(ticker: str, provider_slice: pd.DataFrame,
                              merged: pd.DataFrame, *, lineage: dict | None,
                              adapter_return_known_by: datetime) -> dict:
    """Retain two byte images after an explicitly requested Yahoo observation.

    The trusted incumbent caller owns acquisition, clocks and serialization.
    A lineage dictionary/hash is not authentication or a data-rights grant.
    Returned receipt means this separate capture was published durably; it says
    nothing about atomicity/durability of the existing canonical parquet write.
    Failure can leave unaccepted images (or a receipt whose publication outcome
    is uncertain); callers must reconcile those exact objects, never replay the
    acquisition merely to manufacture a successful receipt.
    """
    expected = {"provider": "yahoo", "field": "Adj Close", "basis": "total_return", "ticker": ticker}
    if type(ticker) is not str or ticker not in YAHOO_CAPTURE_COHORT or lineage != expected:
        raise ValueError("availability Yahoo lineage refused")
    return _capture_yahoo_images(ticker, provider_slice, merged,
                                 adapter_return_known_by=adapter_return_known_by)



def _wti_temporal_receipt(context: dict | None, provider: pd.DataFrame) -> dict | None:
    """Strict allowlist at the receipt boundary; unknown upstream facts stay null.

    A typed description is not authentication. Bind it to the existing image
    hashes below; never turn caller metadata or a local clock into vendor facts.
    """
    if context is None:
        return None
    expected = {"schema", "scope", "index", "request", "parser_versions",
                "on_disk_source_sha256_not_execution_attestation",
                "resolved_request_defaults", "vendor_session_metadata",
                "vendor_daily_label_convention", "provider_available_at",
                "futures_session_completion"}
    if not isinstance(context, dict) or set(context) != expected:
        raise ValueError("WTI temporal context shape refused")
    if (context["schema"] != "yahoo.wti_adapter_temporal_context.v1" or
            context["scope"] != "adapter_extracted_index_before_collector_validation_not_vendor_wire"):
        raise ValueError("WTI temporal context scope refused")
    for key in ("resolved_request_defaults", "vendor_session_metadata",
                "vendor_daily_label_convention", "provider_available_at", "futures_session_completion"):
        if context[key] is not None:
            raise ValueError("WTI temporal upstream fact unqualified")
    idx = context["index"]
    if (not isinstance(idx, dict) or set(idx) != {"kind", "unit", "timezone", "timezone_aware", "labels", "already_midnight"}
            or idx["kind"] != "datetime" or idx["unit"] not in {"s", "ms", "us", "ns"}
            or type(idx["timezone_aware"]) is not bool or type(idx["already_midnight"]) is not bool
            or not isinstance(idx["labels"], list) or not 0 < len(idx["labels"]) <= _CAPTURE_ROW_LIMIT):
        raise ValueError("WTI temporal index refused")
    # ISO datetime grammar excludes arbitrary attrs, names, URLs and credentials.
    for label in idx["labels"]:
        if (not isinstance(label, str) or not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?(?:[+-][0-9]{2}:[0-9]{2})?", label)):
            raise ValueError("WTI temporal label refused")
    if idx["timezone"] is not None:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(idx["timezone"])
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            raise ValueError("WTI temporal timezone refused") from None
    # Existing capture only accepts naive frames. Do not convert aware indexes
    # to force acceptance. Duplicates/order follow the unchanged validate path.
    try:
        original = pd.DatetimeIndex([pd.Timestamp(label) for label in idx["labels"]])
    except (ValueError, TypeError, OverflowError):
        raise ValueError("WTI temporal label refused") from None
    if (original.tz is not None or idx["timezone_aware"] or idx["timezone"] is not None
            or idx["already_midnight"] != bool(original.equals(original.normalize()))):
        raise ValueError("WTI temporal index disagrees with capture")
    normalized = original.normalize().drop_duplicates(keep="last").sort_values()
    if not normalized.equals(provider.index):
        raise ValueError("WTI temporal/image labels disagree")
    versions = context["parser_versions"]
    if not isinstance(versions, dict) or set(versions) != {"yfinance", "pandas"}:
        raise ValueError("WTI temporal parser fields refused")
    for value in versions.values():
        if value is not None and (not isinstance(value, str) or not re.fullmatch(
                r"[0-9]+(?:\.[0-9]+){1,3}(?:(?:a|b|rc|\.post|\.dev)[0-9]+)?", value)):
            raise ValueError("WTI temporal parser version refused")
    code = context["on_disk_source_sha256_not_execution_attestation"]
    if not isinstance(code, dict) or set(code) != {"collectors/yahoo.py", "collectors/base.py", "lib/store.py"}:
        raise ValueError("WTI temporal code fields refused")
    for value in code.values():
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)):
            raise ValueError("WTI temporal code digest refused")
    request = context["request"]
    if request is not None:
        if (not isinstance(request, dict) or set(request) != {"target", "period", "auto_adjust", "progress", "group_by", "threads", "batch_symbols_sha256", "batch_size"}
                or request["target"] != "CL=F" or request["period"] not in {"1mo", "max"}
                or request["auto_adjust"] is not False or request["progress"] is not False
                or request["threads"] is not True or request["group_by"] != "ticker"
                or type(request["batch_size"]) is not int or not 1 <= request["batch_size"] <= 10_000
                or not isinstance(request["batch_symbols_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", request["batch_symbols_sha256"])):
            raise ValueError("WTI temporal request refused")
    raw = _availability_json(context)
    if len(raw) > 1_000_000:
        raise ValueError("WTI temporal context exceeds bound")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "context": json.loads(raw), "execution_authenticity": "UNQUALIFIED"}


def capture_yahoo_wti_observation(provider_slice: pd.DataFrame, merged: pd.DataFrame, *,
                                  lineage: dict | None,
                                  adapter_return_known_by: datetime,
                                   temporal_context: dict | None = None) -> dict:
    """Capture this ordinary Yahoo CL=F return prospectively, without acquisition.

    Separate opt-in from the fixed nine-sector research cohort. This records the
    actual vendor field and immutable normalized values; neither CL session-date
    semantics nor roll policy, settlement basis, source-use adoption, or a past
    snapshot cutoff is inferred. The incumbent runner supplies current-call
    metadata and clocks; caller dictionaries are not authentication.
    """
    common = {"provider": "yahoo", "ticker": "CL=F",
              "series_identity": "vendor_continuous_CL=F"}
    allowed = [{**common, "field": field, "basis": basis} for field, basis in (
        ("Adj Close", "vendor_continuous_adjusted_close"),
        ("Close", "vendor_continuous_close_no_adj_close_returned"))]
    if lineage not in allowed:
        raise ValueError("availability WTI current-call lineage refused")
    return _capture_yahoo_images("CL=F", provider_slice, merged,
                                 adapter_return_known_by=adapter_return_known_by,
                                 wti_lineage=lineage, temporal_context=temporal_context)


def _capture_yahoo_images(ticker: str, provider_slice: pd.DataFrame,
                           merged: pd.DataFrame, *, adapter_return_known_by: datetime,
                           wti_lineage: dict | None = None,
                           temporal_context: dict | None = None) -> dict:
    temporal = _wti_temporal_receipt(temporal_context, provider_slice) if wti_lineage is not None else None
    # Shared incumbent content-addressed publication, not another store/registry.
    known_by = _availability_clock(adapter_return_known_by)
    provider_data = _availability_image(provider_slice)
    merged_data = _availability_image(merged)
    captured = _availability_now()
    captured_text = _availability_clock(captured)
    if captured < adapter_return_known_by:
        raise ValueError("availability clock regression")
    if any(f.index.max().date() > captured.date() for f in (provider_slice, merged)):
        raise ValueError("availability future row refused")
    # Explicitly retain under the existing Yahoo data owner. No hook in upsert.
    yahoo = config.data_dir() / "yahoo"
    if not yahoo.is_dir():
        raise ValueError("availability incumbent Yahoo directory missing")
    root = yahoo / ".availability_capture"
    _availability_dir(root)
    objects, receipts = root / "objects", root / "receipts"
    _availability_dir(objects)
    _availability_dir(receipts)
    provider_digest = _availability_publish(objects, provider_data)
    merged_digest = _availability_publish(objects, merged_data)
    durable = _availability_now()
    durable_text = _availability_clock(durable)
    if durable < captured:
        raise ValueError("availability publication clock regression")
    receipt = {
        "schema": "yahoo.availability_capture.v1", "ticker": ticker,
        "provider_return_image": {
            "sha256": provider_digest, "bytes": len(provider_data),
            "object_ref": "objects/" + provider_digest + ".json",
            "adapter_return_known_by_utc": known_by, "basis": "total_return",
            "scope": "validated_session_filtered_adapter_output_not_vendor_wire"},
        "merged_capture_image": {
            "sha256": merged_digest, "bytes": len(merged_data),
            "object_ref": "objects/" + merged_digest + ".json",
            "captured_known_by_utc": captured_text,
            "immutable_publication_durable_at_utc": durable_text,
            "basis": "total_return", "scope": "separate_capture_of_returned_merged_values"},
        "provider_available_at": None, "operation_identity": None,
        "source_code_identity": None, "rights_reference": None,
        "clock_attestation": None, "source_actor_authentication": None,
        "calendar_verification": "UNQUALIFIED",
        "upstream_revision_history_complete": False,
        "historical_original_availability_proven": False,
        "canonical_cache_transaction_durability": "UNQUALIFIED",
    }
    if wti_lineage is not None:
        receipt["schema"] = "yahoo.wti_observation_capture.v1"
        receipt["source_lineage"] = dict(wti_lineage)
        for image in (receipt["provider_return_image"], receipt["merged_capture_image"]):
            image["basis"] = wti_lineage["basis"]
        receipt["provider_return_image"]["scope"] = "validated_adapter_output_not_vendor_wire"
        receipt.update(
            collector="collectors.yahoo.YahooAdapter",
            series_generation="sha256:" + merged_digest,
            effective_bar_date=merged.index[-1].date().isoformat(),
            futures_session_date_convention=None,
            futures_session_completion=None,
            continuous_contract_roll_policy=None,
            settlement_price_equivalence=None,
            scenario_snapshot_binding=None,
            commercial_rights_attestation={
                "decision_key": "DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023",
                "named_route": "Research Factory Yahoo/yfinance data route",
                "status": "APPROVED_BY_CHAIRMAN_ATTESTATION",
                "native_collector_purpose_binding": "NOT_ESTABLISHED"},
            scenario_adoption="UNQUALIFIED_NATIVE_INPUTS")
    if temporal is not None:
        temporal["provider_image_sha256"] = provider_digest
        temporal["merged_image_sha256"] = merged_digest
        receipt["adapter_temporal_context"] = temporal
    receipt_digest = _availability_publish(receipts, _availability_json(receipt))
    return {"receipt_sha256": receipt_digest,
            "receipt_ref": "receipts/" + receipt_digest + ".json", "receipt": receipt}


_WTI_PARQUET_LIMIT = 8 * 1024 * 1024
_WTI_EXPORT_LIMIT = 2_000_000


def _wti_parquet_bytes(path: Path) -> bytes:
    """Bounded incumbent-file read; never follow a substituted final symlink."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= _WTI_PARQUET_LIMIT:
            raise ValueError("WTI canonical byte bound refused")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(before.st_size + 1)
        after = os.fstat(descriptor)
        if (len(raw) != before.st_size or
                (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("WTI canonical changed during read")
        return raw
    finally:
        os.close(descriptor)


def export_yahoo_wti_observation(capture: dict, provider_slice: pd.DataFrame,
                                  merged: pd.DataFrame) -> dict:
    """Export exact private capture bytes through existing Yahoo data publication.

    Git carries this ONE generation without pretending its files retain private
    CAS modes. No CAS import, new storage backend, acquisition or positive
    scenario adoption. A consumer must recheck the parquet hash, all image
    digests and clocks, then bind a NEW snapshot; old exports are never current
    merely because a file exists. Validation failure preserves the prior
    sidecar; a durability failure after replacement remains an uncertain
    publication, never grounds to replay acquisition or fabricate success.
    """
    import pyarrow.parquet as parquet

    receipt = capture["receipt"]
    if receipt.get("schema") != "yahoo.wti_observation_capture.v1" or receipt.get("ticker") != "CL=F":
        raise ValueError("WTI capture export schema refused")
    receipt_raw = _availability_json(receipt)
    provider_raw, merged_raw = _availability_image(provider_slice), _availability_image(merged)
    yahoo = config.data_dir() / "yahoo"
    private = yahoo / ".availability_capture"
    entries = [(receipt_raw, capture["receipt_sha256"], "receipts"),
               (provider_raw, receipt["provider_return_image"]["sha256"], "objects"),
               (merged_raw, receipt["merged_capture_image"]["sha256"], "objects")]
    for raw, digest, directory in entries:
        if digest != hashlib.sha256(raw).hexdigest():
            raise ValueError("WTI capture export digest mismatch")
        _availability_verify_existing(private / directory / (digest + ".json"), raw)
    for key, raw in (("provider_return_image", provider_raw), ("merged_capture_image", merged_raw)):
        if receipt[key]["bytes"] != len(raw):
            raise ValueError("WTI capture export length mismatch")
    canonical = yahoo / "CL_F.parquet"
    parquet_raw = _wti_parquet_bytes(canonical)
    # Bound decompression before decoding a local canonical parquet generation.
    table = parquet.ParquetFile(io.BytesIO(parquet_raw))
    metadata = table.metadata
    if (metadata.num_rows > _CAPTURE_ROW_LIMIT or metadata.num_columns > 4 or
            sum(metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups)) > 32 * 1024 * 1024):
        raise ValueError("WTI canonical decoded bound refused")
    if _availability_image(table.read().to_pandas()) != merged_raw:
        raise ValueError("WTI canonical/capture values differ")
    exported_at = _availability_now()
    if exported_at < datetime.fromisoformat(receipt["merged_capture_image"]["immutable_publication_durable_at_utc"]):
        raise ValueError("WTI export clock regression")
    def bound(raw):
        return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                "content_base64": base64.b64encode(raw).decode("ascii")}
    export = {"schema": "yahoo.wti_observation_export.v1", "ticker": "CL=F",
              "exported_known_by_utc": _availability_clock(exported_at),
              "capture_receipt": bound(receipt_raw),
              "provider_return_image": bound(provider_raw),
              "merged_capture_image": bound(merged_raw),
              "canonical_parquet": {"path": "data/yahoo/CL_F.parquet",
                                    "sha256": hashlib.sha256(parquet_raw).hexdigest(), "bytes": len(parquet_raw)},
              "scenario_adoption": "UNQUALIFIED_NATIVE_INPUTS",
              "historical_original_availability_proven": False}
    data = _availability_json(export)
    if len(data) > _WTI_EXPORT_LIMIT:
        raise ValueError("WTI export byte bound refused")
    descriptor, temporary = tempfile.mkstemp(prefix=".CL_F.observation-", dir=yahoo)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if _wti_parquet_bytes(canonical) != parquet_raw:
            raise ValueError("WTI canonical changed during export")
        os.replace(temporary, yahoo / "CL_F.observation.json")
        _availability_fsync_dir(yahoo)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": "data/yahoo/CL_F.observation.json", "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}


def _path(group: str, name: str) -> Path:
    safe = name.replace("^", "_").replace("=", "_").replace("/", "_").replace(" ", "_")
    p = config.data_dir() / group / f"{safe}.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_runtime_history(group: str, name: str) -> pd.DataFrame | None:
    """Bound-first read admission shared by store and direct member readers.

    None permits the ordinary legacy path. Runtime-owned missing binding raises;
    it is never represented by None and cannot fall back to checkout data.
    """
    from lib.yahoo_runtime_profile import (
        bound_snapshot_for, cohort_covers, parse_profile, require_snapshot, runtime_owns,
    )
    if not cohort_covers(group=group, symbol=name):
        return None
    snapshot = bound_snapshot_for(group=group, symbol=name)
    if snapshot is not None:
        return snapshot.frame(name)
    profile = parse_profile(config.load().get("yahoo"))
    if runtime_owns(profile, group=group, symbol=name):
        return require_snapshot(profile).frame(name)
    return None


def read(group: str, name: str) -> pd.DataFrame | None:
    runtime_frame = read_runtime_history(group, name)
    if runtime_frame is not None:
        return runtime_frame
    p = _path(group, name)
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def last_date(group: str, name: str) -> date | None:
    df = read(group, name)
    if df is None or df.empty:
        return None
    return df.index.max().date()


def _quarantine(group: str, name: str, rows: pd.DataFrame, reason: str) -> None:
    qdir = config.data_dir() / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    qp = qdir / f"{group}_{name}.csv".replace("^", "_").replace("=", "_")
    rows.assign(reason=reason).to_csv(qp, mode="a", header=not qp.exists())
    log.warning("quarantined %d rows of %s/%s: %s", len(rows), group, name, reason)


def stale_refresh_reason(old_tip, new_tip) -> str | None:
    """PURE: the overwrite_overlap stale-span rule, with no I/O.

    A fresh pull whose latest timestamp PRECEDES the stored one cannot be spliced:
    keeping its changed adjustment window beside newer stored bars mixes bases,
    and deleting the newer bars regresses the cache. ``upsert`` refuses that
    write; this is the same rule as a pure question, so a caller holding the
    stored frame in memory can ask it WITHOUT reading the store.

    Returns the reason, or None when the refresh may proceed. A missing tip on
    either side is not a stale refresh (nothing to compare against). An
    INCOMPARABLE pair of tips raises, exactly as the comparison it replaces
    raised — a tz-aware stored tip against a tz-naive fresh tip is a caller
    error, and silently treating it as "not stale" would splice the two."""
    if old_tip is None or new_tip is None:
        return None
    if new_tip < old_tip:
        return f"latest returned {new_tip} precedes stored {old_tip}"
    return None


def _normalise_merge_frame(frame: pd.DataFrame, *, normalize_index: bool) -> pd.DataFrame:
    result = frame.copy(deep=True)
    result.index = pd.to_datetime(result.index)
    if normalize_index:
        result.index = result.index.normalize()
    return result[~result.index.duplicated(keep="last")].sort_index()


def merge_frames(
    old: pd.DataFrame | None, new: pd.DataFrame, *,
    normalize_index: bool = True, overwrite_overlap: bool = False,
    refresh_start=None,
) -> pd.DataFrame:
    """Pure incumbent merge, with an explicit original refresh-span boundary.

    The legacy default retains combine_first behavior. Runtime explicitly selects
    overwrite_overlap: only old rows before refresh_start survive. A missing or
    null fresh observation never borrows an old value from that owned span.
    Store reads, outlier quarantine and parquet writes remain in upsert.
    """
    if not isinstance(new, pd.DataFrame):
        raise ValueError("new frame must be a DataFrame")
    fresh = _normalise_merge_frame(new, normalize_index=normalize_index)
    if old is None or old.empty:
        return fresh
    if overwrite_overlap:
        if fresh.empty:
            raise ValueError("empty overwrite_overlap frame after filtering; "
                             "retained complete stored history")
        stale = stale_refresh_reason(old.index.max(), fresh.index.max())
        if stale is not None:
            raise ValueError("stale overwrite_overlap frame: " + stale + "; "
                             "retained complete stored history to avoid mixing adjustment bases")
        lo = fresh.index.min() if refresh_start is None else pd.Timestamp(refresh_start)
        if pd.isna(lo) or lo > fresh.index.min():
            raise ValueError("refresh_start must precede every surviving fresh row")
        kept_old = old[old.index < lo]
        merged = pd.concat([kept_old, fresh]) if not kept_old.empty else fresh
        return merged[~merged.index.duplicated(keep="last")].sort_index().copy(deep=True)
    return fresh.combine_first(old).sort_index()


def upsert(group: str, name: str, new: pd.DataFrame, outlier_col: str | None = None,
           normalize_index: bool = True, overwrite_overlap: bool = False) -> pd.DataFrame:
    """Merge new rows into the stored series. New values win on date collision;
    The default path keeps rows present only on disk (append-only history).
    normalize_index=False preserves intraday timestamps (hourly candles).

    overwrite_overlap=True — for DIVIDEND/SPLIT-ADJUSTED series (yfinance
    auto_adjust=True). An adjusted history is a coherent whole: after an ex-dividend
    every prior bar is re-scaled, so a fresh pull's values for the overlapping window
    are the corrected truth and the stored ones are stale. Plain combine_first keeps
    old values wherever the fresh pull did not re-cover them, leaving a PERMANENT basis
    STEP at the refresh edge (measured 17/300 A-share names >0.4%, worst 40%, May-dividend
    clustered) that seasonally biases rev_z and can fabricate MACD/StochRSI crosses.
    With overwrite_overlap=True the fresh pull FULLY OVERWRITES its own date span
    [new.index.min(), new.index.max()]; only stored rows OUTSIDE that span (older deep
    history the short refresh window did not reach) are carried forward. A response
    that does not reach the stored latest timestamp, or becomes empty after outlier
    filtering, is rejected with ValueError before writing. Retain the whole known-good
    cache rather than splice a stale adjustment basis against newer stored rows.
    Reaching that timestamp still allows complete overlap replacement, including
    omitted interior bars. See research/ENGINE_FIX_MASTERPLAN.md §W6-CN fix 2."""
    from lib.yahoo_runtime_profile import (
        assert_legacy_write_allowed, cohort_covers, parse_profile,
    )
    if cohort_covers(group=group, symbol=name):
        assert_legacy_write_allowed(
            parse_profile(config.load().get("yahoo")), group=group, symbol=name)
    if new is None or new.empty:
        raise ValueError(f"upsert called with empty frame for {group}/{name}")
    new = _normalise_merge_frame(new, normalize_index=normalize_index)

    old = read(group, name)
    if old is not None and not old.empty and outlier_col and outlier_col in new.columns:
        new = _guard_outliers(group, name, old, new, outlier_col)

    try:
        merged = merge_frames(old, new, normalize_index=False,
                              overwrite_overlap=overwrite_overlap)
    except ValueError as exc:
        # Preserve the incumbent writer's contextual error text.
        message = str(exc).replace("frame after filtering;",
                                  f"frame after filtering for {group}/{name};")
        message = message.replace("stale overwrite_overlap frame:",
                                  f"stale overwrite_overlap frame for {group}/{name}:")
        raise ValueError(message) from exc

    merged.to_parquet(_path(group, name))
    return merged


#: Typed outcomes of a PURE adjustment-basis comparison (see ``compare_basis``).
#: A status is a FACT about what could be established, never a licence to splice.
BASIS_ALIGNED = "aligned"                 # overlap compared; within tolerance
BASIS_SHIFTED = "shifted"                 # overlap compared; a relative diff > tol
BASIS_NO_OVERLAP = "no_overlap"           # comparable prior, but no common dates
BASIS_NO_PRIOR = "no_prior"               # no comparable prior frame at all
BASIS_INCOMPARABLE = "incomparable"       # the fresh frame lacks the compared column
BASIS_COMPARISON_FAILED = "comparison_failed"  # the comparison itself raised


class BasisComparison(NamedTuple):
    """What a PURE basis comparison established (never a verdict on the data)."""
    status: str
    worst_relative_diff: float | None = None
    overlap_dates: int = 0
    detail: str | None = None


def compare_basis(old: pd.DataFrame | None, new: pd.DataFrame | None, *,
                  col: str = "close", tol: float = 1e-3,
                  strict: bool = False) -> BasisComparison:
    """PURE adjustment-basis comparison between a PRIOR frame and a FRESH frame.

    No I/O, no configuration, no store access: BOTH frames are inputs, so a
    caller holding the stored series in memory can ask the same question the
    store-backed guard asks without reading the repository. The comparison is
    the one ``basis_shifted`` has always made — the prior frame's dates against
    the fresh frame's normalised dates, on ``col``, with a relative difference
    over ``tol`` meaning a re-basing — so the legacy default and wrapper agree.
    strict=True adds finite positive-value validation and uses the actual positive
    denominator. This is a stronger runtime policy; the legacy floor is preserved.

    A missing prior (``None``, empty, or without ``col``) is
    ``BASIS_NO_PRIOR``: nothing to corrupt, nothing established. A prior with
    no date in common with the fresh frame is ``BASIS_NO_OVERLAP``: the basis is
    UNVERIFIABLE, which the guard has always treated as a shift. Never raises:
    a failed comparison reports ``BASIS_COMPARISON_FAILED`` rather than killing
    the caller.

    The PRIOR frame keeps its own index semantics (the caller owns it); the
    fresh frame's index is normalised to midnight exactly as the store's write
    path does, so a caller whose prior is not normalised must normalise it
    first — ``upsert`` does, and so does every seam that owns its prior."""
    if old is None:
        return BasisComparison(BASIS_NO_PRIOR)
    if new is None:
        return BasisComparison(BASIS_INCOMPARABLE if strict else BASIS_NO_PRIOR)
    try:
        if strict:
            import numpy as np
            if (type(tol) not in (int, float) or not np.isfinite(tol) or tol < 0
                    or not isinstance(old, pd.DataFrame)
                    or not isinstance(new, pd.DataFrame)):
                return BasisComparison(BASIS_COMPARISON_FAILED)
            for frame in (old, new):
                if (frame.empty or frame.columns.has_duplicates
                        or col not in frame.columns or frame.index.has_duplicates
                        or not isinstance(frame.index, pd.DatetimeIndex)
                        or frame.index.hasnans
                        or not pd.api.types.is_numeric_dtype(frame[col])
                        or pd.api.types.is_bool_dtype(frame[col])
                        or pd.api.types.is_complex_dtype(frame[col])):
                    return BasisComparison(BASIS_INCOMPARABLE)
                values = frame[col].to_numpy(dtype=float)
                if not np.isfinite(values).all() or not (values > 0).all():
                    return BasisComparison(BASIS_INCOMPARABLE)
        if old.empty or new.empty:
            return BasisComparison(BASIS_NO_PRIOR)
        if col not in old.columns:
            return BasisComparison(BASIS_NO_PRIOR)
        if col not in new.columns:
            return BasisComparison(BASIS_INCOMPARABLE)
        oc = old[col].dropna()
        nc = new[col].dropna()
        if oc.empty or nc.empty:
            return BasisComparison(BASIS_NO_PRIOR)
        idx = pd.to_datetime(nc.index)
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        nc = pd.Series(nc.to_numpy(), index=idx.normalize())
        nc = nc[~nc.index.duplicated(keep="last")]
        overlap = oc.index.intersection(nc.index)
        if len(overlap) == 0:
            return BasisComparison(BASIS_NO_OVERLAP)
        oc = oc.loc[overlap].astype(float)
        nv = nc.loc[overlap].astype(float)
        # Strict inputs are already positive and finite; a price floor would
        # hide large relative shifts in deeply adjusted historical values.
        denominator = nv.abs() if strict else nv.abs().clip(lower=1e-9)
        rel = (oc - nv).abs() / denominator
        worst = float(rel.max())
        if worst > tol:
            return BasisComparison(BASIS_SHIFTED, worst, len(overlap))
        return BasisComparison(BASIS_ALIGNED, worst, len(overlap))
    except Exception as e:  # noqa: BLE001 — a guard must never kill the collect
        # ``detail`` carries the RAW exception text, so the store-backed wrapper
        # logs byte-for-byte what it logged before this helper existed.
        return BasisComparison(BASIS_COMPARISON_FAILED, detail=str(e))


def basis_shifted(group: str, name: str, new: pd.DataFrame, col: str = "close",
                  tol: float = 1e-3) -> bool:
    """True when a freshly fetched refresh window sits on a DIFFERENT adjustment
    basis than the stored series — the signature of a dividend/split between
    fetches. yfinance re-adjusts the WHOLE series at every fetch, so splicing a
    short re-based window onto stored history strands every pre-window row on a
    stale basis: seam-crossing returns/SMAs go silently wrong and an unnoticed
    split is a 10x level step (measured: data/yahoo/SPY.parquet uniformly
    +0.2576% off a fresh fetch on all 8,382 rows before 2026-05-18 — exactly one
    dividend of drift). Note upsert(overwrite_overlap=True) cannot fix this
    class: it makes the fresh pull own its OWN span but never touches rows older
    than the window.

    Compares ``col`` on the overlap dates; a relative diff > ``tol`` is a shift.
    NO overlap at all (stored series ended before the window starts) also
    returns True — the basis is unverifiable and a splice would leave a bar gap.
    False when nothing is stored yet (fresh name — nothing to corrupt). Typed
    ownership/profile/binding refusals propagate. Ordinary comparison errors
    log and return False (old splice
    behavior). Callers respond by discarding the window and refetching
    period='max' for the flagged name — ported from the odds-store guard in
    scripts/build_odds.ensure_store.

    The comparison itself is the PURE ``compare_basis``; this wrapper adds the
    store read, the log lines and the boolean this contract has always returned."""
    from lib.yahoo_runtime_profile import (
        YahooRuntimeBindingError, YahooRuntimeOwnershipError, YahooRuntimeProfileError,
    )
    try:
        old = read(group, name)
        comparison = compare_basis(old, new, col=col, tol=tol)
    except (YahooRuntimeBindingError, YahooRuntimeOwnershipError, YahooRuntimeProfileError):
        raise  # Ownership/binding refusal is not a harmless comparison failure.
    except Exception as e:  # noqa: BLE001 — legacy comparison failure remains permissive
        log.warning("basis guard %s/%s: comparison failed (%s) — treating as unshifted",
                    group, name, e)
        return False
    if comparison.status == BASIS_NO_OVERLAP:
        log.info("basis guard %s/%s: no overlap between the refresh window and "
                 "stored history — full refetch required", group, name)
        return True
    if comparison.status == BASIS_SHIFTED:
        log.info("basis guard %s/%s: adjustment basis shifted (max overlap diff "
                 "%.4f%% over %d dates)", group, name,
                 (comparison.worst_relative_diff or 0.0) * 100.0, comparison.overlap_dates)
        return True
    if comparison.status == BASIS_COMPARISON_FAILED:
        log.warning("basis guard %s/%s: comparison failed (%s) — treating as unshifted",
                    group, name, comparison.detail or "unknown error")
        return False
    return False


def _guard_outliers(group: str, name: str, old: pd.DataFrame, new: pd.DataFrame, col: str) -> pd.DataFrame:
    hist = old[col].dropna()
    if len(hist) < OUTLIER_MIN_OBS:
        return new
    diffs = hist.diff().dropna()
    sigma = diffs.std()
    if not sigma or pd.isna(sigma) or sigma == 0:
        return new
    incoming = new[new.index > hist.index.max()]
    if incoming.empty:
        return new
    last_val = hist.iloc[-1]
    jump = (incoming[col] - last_val).abs()
    bad = incoming[jump > OUTLIER_SIGMA * sigma * max(1, len(incoming)) ** 0.5]
    if not bad.empty:
        _quarantine(group, name, bad, f"|change from {last_val:.4g}| > {OUTLIER_SIGMA} sigma ({sigma:.4g})")
        new = new.drop(index=bad.index)
    return new


def write_status(status: dict) -> None:
    p = Path(config.ROOT) / config.load()["storage"]["run_status_file"]
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(status, f, indent=2, default=str)


def read_status() -> dict:
    p = Path(config.ROOT) / config.load()["storage"]["run_status_file"]
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)
