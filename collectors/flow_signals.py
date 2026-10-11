"""collectors/flow_signals.py — append-only flow-event PIT ledger harvester.

Harvests qualifying flow events from the live_flow R2 archive blobs and the
feed_current.json snapshot, deduplicates on _event_id (keep-first), normalizes
all timestamps to timezone-aware UTC, and appends new rows to
data/flow_signals/ledger.parquet.

SOURCE PRIORITY ORDER (FS-R1 / masterplan §2 F1):
  1. R2 live_flow/archive/YYYYMMDDTHH.json blobs within the 48h window.
  2. live_flow/feed_current.json snapshot (supplement for events not in archive).

ARCHIVE UPLOAD REALITY (verified in scripts/live_flow_poller.py lines 1514-1519):
  The poller DOES upload hourly archive blobs to R2 under the key
  live_flow/archive/YYYYMMDDTHH.json (ARCHIVE_HOUR_CADENCE=3600s, pruned at 48h).
  The key stem format is strftime("%Y%m%dT%H"). Both the local write AND R2 upload
  occur in the poller's main loop, so archive blobs exist on R2 whenever the
  poller ran. If R2 creds are absent or no blobs exist yet (first run before the
  poller has cycled for an hour), the collector falls back to feed_current.json.

PIT CONTRACT:
  - Append-only: existing rows are never mutated.
  - keep-first on _event_id: the first ingested record for a given event id is
    the authority; subsequent harvests of the same blob are safe (idempotent).
  - detector_version from config/flow_detector.yml is stamped on every row.
  - All timestamps (ts, ingested_at) are timezone-aware UTC at parse.
  - source field = 'live_feed' for all rows from this collector.

SINGLE-WRITER LAW: only this collector writes to data/flow_signals/ledger.parquet.
  The outcome grader (engine/flow_signals_grade.py) reads the ledger and writes
  a separate data/flow_signals/grades.parquet — no commingling of write paths.

GRACEFUL DEGRADATION:
  Absent R2 creds / no archive blobs / empty feed / missing config →
  clean no-op with a log line. Never a crash, never fake rows.

Usage (nightly, via scripts/build_flow_signals.py):
  from collectors.flow_signals import harvest
  n_new = harvest()

Usage (smoke, no side-effects):
  python -m collectors.flow_signals --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from lib.live_flow_event_stage import parse_stage_bytes

log = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────
LEDGER_DIR = "flow_signals"
LEDGER_FILE = "ledger.parquet"
R2_ARCHIVE_PREFIX = "live_flow/archive/"
R2_FEED_KEY = "live_flow/feed_current.json"
R2_EVENT_PREFIX = "live_flow/events/"
ARCHIVE_WINDOW_HOURS = 48

# Detector version loaded from config/flow_detector.yml at module import.
# Cached after first load; consumers see the same version for the process lifetime.
_DETECTOR_VERSION: str | None = None

# Raw event producer clocks, read under their original payload names and stored
# under a dedicated diagnostic namespace. These must not collide with the FS-5
# verified-stage receipts (decision_at / available_at / source_stage_*). Older
# parquet rows remain null when ordinary keep-first appends add these columns.
_SOURCE_CLOCK_INPUT_FIELDS = (
    "observed_at", "decision_at", "available_at", "published_at", "source_snapshot_asof",
)
_SOURCE_EVENT_CLOCK_FIELDS = (
    "source_event_observed_at",
    "source_event_decision_at",
    "source_event_available_at",
    "source_event_published_at",
    "source_event_snapshot_asof",
)
_SOURCE_CLOCK_INPUT_TO_OUTPUT = dict(
    zip(_SOURCE_CLOCK_INPUT_FIELDS, _SOURCE_EVENT_CLOCK_FIELDS)
)
_SOURCE_CLOCK_STATES = ("ordered", "partial", "unavailable", "invalid")
_SOURCE_TIME_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


# Full event schema columns (all fields from engine/live_flow.py event dict).
# These are the ingest fields — never mutated after first write (keep-first law).
_EVENT_COLS = [
    "event_id",       # renamed from 'id' for clarity in parquet schema
    "session_date",   # injected from archive key / feed session_date field
    "ts",             # trade timestamp (aware-UTC string, normalized at parse)
    "root",
    "group",
    "group_zh",
    "right",
    "exp",
    "strike",
    "dte",
    "dte_bucket",
    "mny_bucket",
    "side",
    "n_prints",
    "size",
    "avg_price",
    "premium",
    "premium_z",
    "baseline_source",
    "vol_gt_oi",
    "repeated",
    "zerodte",
    "signing_source",
    "swept",
    # OA-1T measured trade-vs-NBBO microstructure, flattened from the event's
    # additive `microstructure` block. Historical rows stay null on every one of
    # these: a later NBBO/OI observation is not event-time truth.
    "vol_gt_oi_ratio",
    "microstructure_schema",
    "source_print_count",
    "nbbo_valid_print_count",
    "source_premium_usd",
    "nbbo_covered_premium_usd",
    "nbbo_print_coverage",
    "nbbo_premium_coverage",
    "at_ask_share",
    "at_bid_share",
    "inside_share",
    "outside_share",
    "aggression_share",
    "aggression_balance",
    "spread_median_usd",
    "spread_median_pct",
    "quote_age_median_ms",
    "quote_age_max_ms",
    "bid_size_median",
    "ask_size_median",
    # Additive raw-event source-clock diagnostics. Distinct from the FS-5
    # verified-stage receipts below. Diagnostic status is NOT strategy,
    # publication, or execution eligibility. Grader/model anchors are unchanged.
    *_SOURCE_EVENT_CLOCK_FIELDS,
    "source_clock_status",
    # Collector-stamped metadata
    "detector_version",
    "source",         # 'live_feed'
    "ingested_at",    # aware-UTC ISO string
    # Immutable FS-5 stage evidence.  Absent for archive/feed display fallback.
    "decision_at",
    "available_at",
    "source_stage_observed_at",
    "source_stage_key",
    "source_stage_schema",
    "source_stage_prefix_records",
    "source_stage_prefix_sha256",
]


# ── detector version loader ───────────────────────────────────────────────────

def _load_detector_version() -> str:
    """Return detector version from config/flow_detector.yml.

    Caches in module-level _DETECTOR_VERSION. Falls back to 'unknown' on any
    error (logged; never a crash).
    """
    global _DETECTOR_VERSION
    if _DETECTOR_VERSION is not None:
        return _DETECTOR_VERSION
    try:
        import yaml
        cfg_path = Path(__file__).resolve().parent.parent / "config" / "flow_detector.yml"
        if not cfg_path.exists():
            log.warning("flow_signals: config/flow_detector.yml not found — version='unknown'")
            _DETECTOR_VERSION = "unknown"
            return _DETECTOR_VERSION
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f)
        ver = str(cfg.get("version", "unknown"))
        _DETECTOR_VERSION = ver
        return _DETECTOR_VERSION
    except Exception as e:  # noqa: BLE001
        log.warning("flow_signals: could not load detector version: %s", e)
        _DETECTOR_VERSION = "unknown"
        return _DETECTOR_VERSION


# ── R2 client (same pattern as live_flow_poller.py) ─────────────────────────

def _r2_client():
    """Build boto3 S3 client for R2 using env vars R2_ENDPOINT / R2_ACCESS_KEY_ID
    / R2_SECRET_ACCESS_KEY. Returns None if creds absent (graceful degradation).
    """
    ep = os.environ.get("R2_ENDPOINT")
    ak = os.environ.get("R2_ACCESS_KEY_ID")
    sk = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (ep and ak and sk):
        log.info("flow_signals: R2 creds absent — archive harvest skipped")
        return None
    try:
        import boto3
        from botocore.config import Config
        kw = dict(region_name="auto", signature_version="s3v4",
                  max_pool_connections=4,
                  retries={"max_attempts": 3, "mode": "standard"})
        try:
            cfg = Config(**kw, request_checksum_calculation="when_required",
                         response_checksum_validation="when_required")
        except TypeError:
            cfg = Config(**kw)
        return boto3.client("s3", endpoint_url=ep,
                            aws_access_key_id=ak,
                            aws_secret_access_key=sk,
                            config=cfg)
    except Exception as e:  # noqa: BLE001
        log.warning("flow_signals: R2 client build failed: %s", e)
        return None


def _r2_bucket() -> str:
    """Return R2 bucket name from env R2_BUCKET (default: mastermindx)."""
    return os.environ.get("R2_BUCKET", "mastermindx")


# ── archive blob discovery ────────────────────────────────────────────────────

def _archive_keys_within_window(s3, bucket: str,
                                window_hours: int = ARCHIVE_WINDOW_HOURS) -> list[str]:
    """List live_flow/archive/ keys whose timestamp is within window_hours of now.

    Archive key format: live_flow/archive/YYYYMMDDTHH.json
    Stem format: strftime('%Y%m%dT%H')  (verified: live_flow_poller.py:1515,1517-1518)
    """
    try:
        out: list[str] = []
        tok = None
        while True:
            kw: dict[str, Any] = {"Bucket": bucket, "Prefix": R2_ARCHIVE_PREFIX}
            if tok:
                kw["ContinuationToken"] = tok
            r = s3.list_objects_v2(**kw)
            for o in r.get("Contents", []):
                out.append(o["Key"])
            if not r.get("IsTruncated"):
                break
            tok = r.get("NextContinuationToken")
    except Exception as e:  # noqa: BLE001
        log.warning("flow_signals: list archive keys failed: %s", e)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    valid: list[str] = []
    for k in out:
        stem = Path(k).stem  # e.g. "20260713T14"
        try:
            ts = datetime.strptime(stem, "%Y%m%dT%H").replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                valid.append(k)
        except Exception:  # noqa: BLE001
            pass  # non-standard key; skip silently
    return sorted(valid)


def _fetch_r2_json(s3, bucket: str, key: str) -> dict | None:
    """Download a JSON object from R2. Returns None on any error."""
    try:
        import io
        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        return json.loads(body)
    except Exception as e:  # noqa: BLE001
        log.warning("flow_signals: fetch R2 key %s failed: %s", key, e)
        return None


# ── timestamp normalization ───────────────────────────────────────────────────

def _normalize_ts(ts_val: Any) -> str:
    """Normalize any timestamp representation to aware-UTC ISO string.

    Handles:
      - strings ending in 'Z' (already UTC)
      - strings with '+00:00' suffix
      - naive strings (assume UTC per repo convention)
      - pd.Timestamp / datetime objects

    Returns ISO string like '2026-07-13T14:23:45+00:00'.
    Raises on completely unparsable input (caller should catch).
    """
    ts = pd.Timestamp(ts_val)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat()  # includes +00:00 offset for aware timestamps


def _strict_source_clock(value: Any) -> tuple[str | None, bool]:
    """Return an explicit ISO/offset clock plus whether supplied input was invalid.

    Unlike the legacy trade-time normalizer, this never assumes UTC for a naive
    source clock or interprets a numeric value as a nanosecond epoch.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, False
    if not isinstance(value, str) or not _SOURCE_TIME_RE.fullmatch(value.strip()):
        return None, True
    try:
        stamp = pd.Timestamp(value.strip())
        if pd.isna(stamp) or stamp.tzinfo is None:
            return None, True
        return stamp.tz_convert("UTC").isoformat(), False
    except (ValueError, TypeError, OverflowError):
        return None, True


def _source_clock_cols(ev: dict, ingested_at: str) -> dict[str, Any]:
    """Preserve raw event clocks under source_event_* and describe structure.

    Reads original payload names. Writes a dedicated diagnostic namespace so
    FS-5 verified-stage receipts stay exclusive owners of decision_at /
    available_at / source_stage_*. Valid fields survive another field's failure.
    Status is computed only from these raw event inputs plus the existing
    trade/ingestion order rules; the stage envelope cannot elevate it. Values
    are never borrowed from ts, ingested_at, the wrapper, or a stage receipt.
    Even 'ordered' does not prove source authenticity, public delivery, rights,
    or a tradable entry. No old event is restamped on re-harvest.
    """
    parsed: dict[str, Any] = {}
    invalid = False
    for key in _SOURCE_CLOCK_INPUT_FIELDS:
        parsed[key], bad = _strict_source_clock(ev.get(key))
        invalid |= bad
    values: dict[str, Any] = {
        _SOURCE_CLOCK_INPUT_TO_OUTPUT[key]: parsed[key]
        for key in _SOURCE_CLOCK_INPUT_FIELDS
    }
    if not invalid and not any(values.values()):
        values["source_clock_status"] = "unavailable"
        return values

    trade, bad_trade = _strict_source_clock(ev.get("ts"))
    invalid |= bad_trade
    chain = [
        trade,
        parsed["observed_at"],
        parsed["decision_at"],
        parsed["available_at"],
        parsed["published_at"],
    ]
    known = [pd.Timestamp(v) for v in chain if v is not None]
    invalid |= any(a > b for a, b in zip(known, known[1:]))
    ingested = pd.Timestamp(ingested_at)
    invalid |= any(pd.Timestamp(v) > ingested for v in values.values() if v is not None)
    required = (
        trade,
        parsed["observed_at"],
        parsed["decision_at"],
        parsed["available_at"],
    )
    values["source_clock_status"] = (
        "invalid" if invalid else "ordered" if all(v is not None for v in required) else "partial"
    )
    return values


def _source_clock_coverage(df: pd.DataFrame) -> dict[str, Any]:
    """Diagnostic counts in the incumbent gate, not eligibility or score flags."""
    counts = {key: 0 for key in (*_SOURCE_CLOCK_STATES, "legacy_unknown", "unrecognized")}
    if "source_clock_status" not in df.columns:
        counts["legacy_unknown"] = len(df)
    else:
        for status, count in df["source_clock_status"].value_counts(dropna=False).items():
            key = "legacy_unknown" if pd.isna(status) else str(status)
            counts[key if key in counts else "unrecognized"] += int(count)
    return {
        "schema": "flow_signals.clock_coverage/v1",
        "authority": "diagnostic_only",
        "rows_total": len(df),
        "status_counts": counts,
        "field_non_null": {
            key: int(df[key].notna().sum()) if key in df.columns else 0
            for key in _SOURCE_EVENT_CLOCK_FIELDS
        },
    }


def _infer_session_date_from_archive_key(key: str) -> str | None:
    """Infer YYYY-MM-DD session date from archive key stem YYYYMMDDTHH."""
    stem = Path(key).stem
    try:
        ts = datetime.strptime(stem, "%Y%m%dT%H")
        return ts.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


# ── event extraction ─────────────────────────────────────────────────────────

MICROSTRUCTURE_SCHEMA = "options.trade_nbbo_microstructure/v1"


def _finite_float(v: Any) -> float | None:
    """`_coerce_float` filters NaN but not Infinity.

    The live producer cannot emit one — the event stage serialises with
    ``allow_nan=False`` — but a corrupt or foreign archive blob can, and this
    flattener is the last gate before the ML ledger. An infinite measurement is
    unmeasured, not enormous.
    """
    value = _coerce_float(v)
    if value is None:
        return None
    import math

    return value if math.isfinite(value) else None


_LEGACY_CATEGORICAL_KEYS = frozenset({
    "ask_share",
    "bid_share",
    "category_proxy_share",
    "category_proxy",
    "side",
    "soft_side",
    "lean",
})
_LOCATION_SHARE_KEYS = (
    "at_ask_share",
    "at_bid_share",
    "inside_share",
    "outside_share",
)
_LOCATION_IDENTITY_TOL = 6e-6


def _block_number(value: Any) -> float | None:
    """Finite float from a block field, or None when the value is not one."""
    import math

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isfinite(number):
            return number
    return None


def measured_block_rejection_reason(block: dict | None) -> str | None:
    """Return why ``block`` must not be read as a trade-vs-NBBO measurement.

    ``None`` means the block is admissible: exact v1 schema, no legacy category
    key, location shares all present or all absent, the four shares sum to 1
    within 6e-6, aggression equals at_ask + at_bid within 6e-6, covered premium
    does not exceed source premium, and each coverage ratio is inside [0, 1].
    """
    if not isinstance(block, dict) or block.get("schema") != MICROSTRUCTURE_SCHEMA:
        return "SCHEMA_MISMATCH"
    if any(key in block for key in _LEGACY_CATEGORICAL_KEYS):
        return "LEGACY_CATEGORICAL_KEY"

    states: list[str] = []
    numbers: list[float] = []
    for key in _LOCATION_SHARE_KEYS:
        if key not in block or block[key] is None:
            states.append("absent")
            continue
        number = _block_number(block[key])
        if number is None:
            states.append("bad")
        else:
            states.append("number")
            numbers.append(number)
    if "bad" in states or ("absent" in states and "number" in states):
        return "LOCATION_IDENTITY"
    if states and all(state == "number" for state in states):
        if abs(sum(numbers) - 1.0) > _LOCATION_IDENTITY_TOL:
            return "LOCATION_IDENTITY"
        aggression = _block_number(block.get("aggression_share"))
        edge = numbers[0] + numbers[1]
        if aggression is None or abs(aggression - edge) > _LOCATION_IDENTITY_TOL:
            return "LOCATION_IDENTITY"

    for key in ("source_premium_usd", "nbbo_covered_premium_usd"):
        if key in block and block[key] is not None and _block_number(block[key]) is None:
            return "COVERAGE_BOUNDS"
    source = _block_number(block.get("source_premium_usd"))
    covered = _block_number(block.get("nbbo_covered_premium_usd"))
    if (
        source is not None
        and covered is not None
        and covered > source + _LOCATION_IDENTITY_TOL
    ):
        return "COVERAGE_BOUNDS"
    for key in ("nbbo_premium_coverage", "nbbo_print_coverage"):
        if key not in block or block[key] is None:
            continue
        coverage = _block_number(block[key])
        if (
            coverage is None
            or coverage < -_LOCATION_IDENTITY_TOL
            or coverage > 1.0 + _LOCATION_IDENTITY_TOL
        ):
            return "COVERAGE_BOUNDS"
    return None


def _measured_microstructure_cols(ev: dict) -> dict[str, Any]:
    """Flatten the event's additive measured block into ledger columns.

    The nested object is admitted only when ``measured_block_rejection_reason``
    is None.  A matching schema string is not enough: a legacy category key, a
    broken location identity, or a coverage break yields nulls on every measured
    column.  Missing never becomes 0: a zero share and an unmeasured share are
    different facts.  ``vol_gt_oi_ratio`` stays the event's own field.
    """
    micro = ev.get("microstructure")
    trusted: dict = micro if measured_block_rejection_reason(micro) is None else {}
    return {
        # Top level on the event, not inside the block, so it stands on its own.
        "vol_gt_oi_ratio": _finite_float(ev.get("vol_gt_oi_ratio")),
        "microstructure_schema": MICROSTRUCTURE_SCHEMA if trusted else None,
        "source_print_count": _coerce_int(trusted.get("source_print_count")),
        "nbbo_valid_print_count": _coerce_int(trusted.get("nbbo_valid_print_count")),
        "source_premium_usd": _finite_float(trusted.get("source_premium_usd")),
        "nbbo_covered_premium_usd": _finite_float(
            trusted.get("nbbo_covered_premium_usd"),
        ),
        "nbbo_print_coverage": _finite_float(trusted.get("nbbo_print_coverage")),
        "nbbo_premium_coverage": _finite_float(trusted.get("nbbo_premium_coverage")),
        "at_ask_share": _finite_float(trusted.get("at_ask_share")),
        "at_bid_share": _finite_float(trusted.get("at_bid_share")),
        "inside_share": _finite_float(trusted.get("inside_share")),
        "outside_share": _finite_float(trusted.get("outside_share")),
        "aggression_share": _finite_float(trusted.get("aggression_share")),
        "aggression_balance": _finite_float(trusted.get("aggression_balance")),
        "spread_median_usd": _finite_float(trusted.get("spread_median_usd")),
        "spread_median_pct": _finite_float(trusted.get("spread_median_pct")),
        "quote_age_median_ms": _finite_float(trusted.get("quote_age_median_ms")),
        "quote_age_max_ms": _finite_float(trusted.get("quote_age_max_ms")),
        "bid_size_median": _finite_float(trusted.get("bid_size_median")),
        "ask_size_median": _finite_float(trusted.get("ask_size_median")),
    }


def _events_from_blob(blob: dict, session_date_hint: str | None = None) -> list[dict]:
    """Extract and normalize events from a feed/archive blob.

    A blob is either a live_flow.feed/v1 payload (has 'events' list) or a
    raw list of event dicts. Returns normalized event dicts ready for ledger.
    """
    if isinstance(blob, list):
        raw_events = blob
        session_date = session_date_hint or ""
        if session_date_hint:
            # N8: UTC archive-key hint can mis-date late-ET sessions (events after
            # ~20:00 UTC belong to the next calendar day per the key stem but may
            # have been captured for the prior trading session).
            log.warning(
                "flow_signals: blob is a raw list — session_date derived from UTC "
                "archive-key hint '%s' which can mis-date late-ET sessions",
                session_date_hint,
            )
    elif isinstance(blob, dict):
        raw_events = blob.get("events", [])
        blob_session = blob.get("session_date", "")
        if blob_session:
            session_date = blob_session
        elif session_date_hint:
            # N8: fell back to UTC archive-key hint; warn because late-ET sessions
            # risk being stamped with the wrong date.
            session_date = session_date_hint
            log.warning(
                "flow_signals: blob lacks session_date field — falling back to "
                "UTC archive-key hint '%s' which can mis-date late-ET sessions",
                session_date_hint,
            )
        else:
            session_date = ""
    else:
        return []

    ingested_at = datetime.now(timezone.utc).isoformat()
    detector_version = _load_detector_version()
    results: list[dict] = []

    for ev in raw_events:
        if not isinstance(ev, dict):
            continue
        event_id = ev.get("id", "")
        if not event_id:
            continue  # malformed event; skip

        # Normalize timestamp to aware-UTC
        raw_ts = ev.get("ts", "")
        try:
            ts_norm = _normalize_ts(raw_ts) if raw_ts else ""
        except Exception:  # noqa: BLE001
            ts_norm = ""

        row: dict[str, Any] = {
            "event_id":        str(event_id),
            "session_date":    str(session_date),
            "ts":              ts_norm,
            "root":            str(ev.get("root", "")),
            "group":           str(ev.get("group", "")),
            "group_zh":        str(ev.get("group_zh", "")),
            "right":           str(ev.get("right", "")),
            "exp":             str(ev.get("exp", "")),
            "strike":          _coerce_float(ev.get("strike")),
            "dte":             _coerce_int(ev.get("dte")),
            "dte_bucket":      str(ev.get("dte_bucket", "")),
            "mny_bucket":      str(ev.get("mny_bucket", "unknown")),
            "side":            str(ev.get("side", "mixed")),
            "n_prints":        _coerce_int(ev.get("n_prints", 1)),
            "size":            _coerce_int(ev.get("size", 0)),
            "avg_price":       _coerce_float(ev.get("avg_price")),
            "premium":         _coerce_float(ev.get("premium")),
            "premium_z":       _coerce_float(ev.get("premium_z")),
            "baseline_source": str(ev.get("baseline_source", "")),
            "vol_gt_oi":       _coerce_bool(ev.get("vol_gt_oi")),
            "repeated":        _coerce_bool(ev.get("repeated", False)),
            "zerodte":         _coerce_bool(ev.get("zerodte", False)),
            "signing_source":  str(ev.get("signing_source", "tape")),
            "swept":           _coerce_bool(ev.get("swept", False)),
            **_measured_microstructure_cols(ev),
            **_source_clock_cols(ev, ingested_at),
            "detector_version": detector_version,
            "source":          "live_feed",
            "ingested_at":     ingested_at,
            # Archive/feed_current are display continuity inputs only.  Keep
            # every FS-5 receipt field explicitly absent; never synthesize a
            # stage clock from ingestion or object metadata.
            "decision_at": None,
            "available_at": None,
            "source_stage_observed_at": None,
            "source_stage_key": None,
            "source_stage_schema": None,
            "source_stage_prefix_records": None,
            "source_stage_prefix_sha256": None,
        }
        results.append(row)

    return results


def _coerce_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        import math
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _coerce_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _coerce_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    try:
        return bool(int(v))
    except (TypeError, ValueError):
        return None


# ── ledger I/O ───────────────────────────────────────────────────────────────

def _ledger_path() -> Path:
    """Return the absolute path to data/flow_signals/ledger.parquet."""
    from lib import config
    p = config.data_dir() / LEDGER_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p / LEDGER_FILE


_LEDGER_UNREADABLE = object()  # sentinel: ledger exists but could not be read


def _load_existing_ids(ledger_path: Path) -> set[str] | object:
    """Return the set of event_ids already in the ledger.

    Returns:
      - empty set: ledger file is absent (first run — fine, proceed)
      - set[str]:  ledger read successfully
      - _LEDGER_UNREADABLE sentinel: ledger exists but is corrupt/unreadable
        → caller MUST abort to avoid re-ingesting the full history (M3: fail CLOSED)
    """
    if not ledger_path.exists():
        return set()
    try:
        df = pd.read_parquet(ledger_path, columns=["event_id"])
        return set(df["event_id"].astype(str).tolist())
    except Exception as e:  # noqa: BLE001
        log.error(
            "flow_signals: ledger exists but is unreadable — aborting harvest "
            "to prevent double-ingest: %s", e
        )
        return _LEDGER_UNREADABLE


def _append_rows(ledger_path: Path, rows: list[dict]) -> int:
    """Append new rows to the ledger parquet. Returns count of rows written.

    Uses atomic write: writes to a temp file then renames.
    All timestamps in 'ts' and 'ingested_at' columns are stored as plain
    strings (no tz-aware dtype conversion) to avoid the LETHAL naive/aware
    mismatch class in parquet (tz-aware-into-naive-parquet memory).
    """
    if not rows:
        return 0
    new_df = pd.DataFrame(rows, columns=_EVENT_COLS)

    if ledger_path.exists():
        try:
            existing = pd.read_parquet(ledger_path)
        except Exception as e:  # noqa: BLE001
            log.error("flow_signals: could not read existing ledger: %s — aborting append", e)
            return 0
        merged = pd.concat([existing, new_df], ignore_index=True)
    else:
        merged = new_df

    # Structural backstop: deduplicate on event_id, keep-first (M3).
    # This is a last-resort guard; the harvest loop's existing_ids check is
    # the primary dedup gate. This prevents a corrupt double-write from persisting.
    merged = merged.drop_duplicates(subset=["event_id"], keep="first")

    tmp = ledger_path.with_suffix(".tmp.parquet")
    try:
        merged.to_parquet(tmp, index=False)
        tmp.rename(ledger_path)
    except Exception as e:  # noqa: BLE001
        log.error("flow_signals: parquet write failed: %s", e)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return 0

    return len(rows)


# ── feed_current.json fallback ────────────────────────────────────────────────

def _feed_current_path() -> Path | None:
    """Resolve the path to data/live_flow_out/feed_current.json.

    The poller writes this file to config.data_dir() / 'live_flow_out' /
    'feed_current.json' (see live_flow_poller._out_dir and _write_json).
    Returns None if not found.
    """
    try:
        from lib import config
        p = config.data_dir() / "live_flow_out" / "feed_current.json"
        return p if p.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _r2_feed_current(s3, bucket: str) -> dict | None:
    """Fetch live_flow/feed_current.json from R2. Returns None on any error."""
    return _fetch_r2_json(s3, bucket, R2_FEED_KEY)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_stage_keys_within_window(s3, bucket: str,
                                    window_hours: int = ARCHIVE_WINDOW_HOURS,
                                    now: datetime | None = None) -> list[str]:
    """Return only recent date-keyed stages; never use R2 listing as replay."""
    try:
        keys: list[str] = []
        token = None
        while True:
            request: dict[str, Any] = {"Bucket": bucket, "Prefix": R2_EVENT_PREFIX}
            if token:
                request["ContinuationToken"] = token
            page = s3.list_objects_v2(**request)
            keys.extend(str(item.get("Key") or "") for item in page.get("Contents") or [])
            if not page.get("IsTruncated"):
                break
            token = page.get("NextContinuationToken")
            if not token:
                return []
    except Exception as exc:  # noqa: BLE001
        log.warning("flow_signals: list event-stage keys failed: %s", exc)
        return []
    current = now or datetime.now(timezone.utc)
    cutoff_date = (current - timedelta(hours=window_hours)).date()
    upper_date = current.date()
    valid: list[str] = []
    for key in keys:
        if not key.startswith(R2_EVENT_PREFIX) or not key.endswith(".jsonl"):
            continue
        session = key[len(R2_EVENT_PREFIX):-len(".jsonl")]
        try:
            parsed = datetime.strptime(session, "%Y-%m-%d").date()
        except ValueError:
            continue
        if parsed.isoformat() == session and cutoff_date <= parsed <= upper_date:
            valid.append(key)
    return sorted(valid)


def _fetch_staged_rows(s3, bucket: str, key: str) -> list[dict[str, Any]] | None:
    """Fetch one stage and bind new rows to original-byte prefix receipts.

    The observation clock is sampled after ``Body.read`` completes.  It is never
    derived from R2 metadata, local ingestion, or the poller's local durability
    clock (``available_at``).
    """
    session = key[len(R2_EVENT_PREFIX):-len(".jsonl")]
    try:
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        observed_at = _utc_now_iso()
        paired = parse_stage_bytes(
            raw, expected_session_date=session, source_stage_key=key,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("flow_signals: staged event key %s rejected: %s", key, exc)
        return None
    rows: list[dict[str, Any]] = []
    for item in paired:
        normalized = _events_from_blob({"session_date": session, "events": [item["event"]]})
        if len(normalized) != 1:
            continue
        row = normalized[0]
        row.update({
            "decision_at": item["decision_at"],
            "available_at": item["available_at"],
            "source_stage_observed_at": observed_at,
            "source_stage_key": item["source_stage_key"],
            "source_stage_schema": item["source_stage_schema"],
            "source_stage_prefix_records": item["source_stage_prefix_records"],
            "source_stage_prefix_sha256": item["source_stage_prefix_sha256"],
        })
        rows.append(row)
    return rows


# ── main harvest function ─────────────────────────────────────────────────────

def harvest(dry_run: bool = False) -> int:
    """Harvest flow events from R2 archives + feed_current, append to ledger.

    Returns the count of new rows appended (0 on no-op or error).

    Priority:
      1. R2 archive blobs within 48h window (preferred — more complete)
      2. feed_current.json (R2 then local) — supplement for events not in archive

    keep-first dedup on event_id ensures repeated harvests are idempotent.
    """
    ledger_path = _ledger_path()
    _existing = _load_existing_ids(ledger_path)
    if _existing is _LEDGER_UNREADABLE:
        # Ledger exists but is corrupt/unreadable — abort to prevent double-ingest (M3).
        log.error("flow_signals: harvest aborted — ledger unreadable (written nothing)")
        return 0
    existing_ids: set[str] = _existing  # type: ignore[assignment]
    all_new_rows: dict[str, dict] = {}  # event_id -> row (keep-first)

    s3 = _r2_client()
    bucket = _r2_bucket()

    # ── 1. R2 archive blobs ───────────────────────────────────────────────────
    n_archive_blobs = 0
    if s3 is not None:
        # FS-5 science source: append-only staged evidence wins before the
        # archive/display paths.  The bounded date window avoids history replay.
        for key in _event_stage_keys_within_window(s3, bucket, ARCHIVE_WINDOW_HOURS):
            staged_rows = _fetch_staged_rows(s3, bucket, key)
            if staged_rows is None:
                continue
            for row in staged_rows:
                eid = row["event_id"]
                if eid not in existing_ids and eid not in all_new_rows:
                    all_new_rows[eid] = row
        archive_keys = _archive_keys_within_window(s3, bucket, ARCHIVE_WINDOW_HOURS)
        log.info("flow_signals: found %d archive blobs within %dh window",
                 len(archive_keys), ARCHIVE_WINDOW_HOURS)
        for key in archive_keys:
            session_hint = _infer_session_date_from_archive_key(key)
            blob = _fetch_r2_json(s3, bucket, key)
            if blob is None:
                continue
            n_archive_blobs += 1
            for row in _events_from_blob(blob, session_date_hint=session_hint):
                eid = row["event_id"]
                if eid not in existing_ids and eid not in all_new_rows:
                    all_new_rows[eid] = row  # keep-first: first archive wins

    # ── 2. feed_current supplement ────────────────────────────────────────────
    # Fetch events from feed_current that weren't in archive blobs.
    feed_blob: dict | None = None
    if s3 is not None:
        feed_blob = _r2_feed_current(s3, bucket)
    if feed_blob is None:
        local_feed = _feed_current_path()
        if local_feed is not None:
            try:
                feed_blob = json.loads(local_feed.read_text())
                log.debug("flow_signals: loaded local feed_current.json (%s)", local_feed)
            except Exception as e:  # noqa: BLE001
                log.warning("flow_signals: local feed_current.json read failed: %s", e)

    if feed_blob is not None:
        for row in _events_from_blob(feed_blob):
            eid = row["event_id"]
            if eid not in existing_ids and eid not in all_new_rows:
                all_new_rows[eid] = row  # keep-first: archive already applied above

    new_rows = list(all_new_rows.values())
    log.info(
        "flow_signals: %d archive blobs processed; %d new events to append "
        "(existing ledger: %d rows)",
        n_archive_blobs, len(new_rows), len(existing_ids),
    )

    if not new_rows:
        log.info("flow_signals: nothing new to append — ledger unchanged")
        return 0

    if dry_run:
        log.info("flow_signals: dry-run — would append %d rows (not writing)", len(new_rows))
        return len(new_rows)

    n_written = _append_rows(ledger_path, new_rows)
    log.info("flow_signals: appended %d rows → %s", n_written, ledger_path)
    return n_written


# ── ledger stats ─────────────────────────────────────────────────────────────

def ledger_stats() -> dict:
    """Return summary stats for the current ledger. Empty dict if absent."""
    ledger_path = _ledger_path()
    if not ledger_path.exists():
        return {"n_rows": 0, "n_sessions": 0, "dte_bucket_counts": {}, "last_ts": None}
    try:
        # Project only existing optional columns so pre-clock ledgers remain
        # readable and their rows are counted as legacy_unknown, not zero rows.
        import pyarrow.parquet as pq

        names = set(pq.read_schema(ledger_path).names)
        columns = ["event_id", "session_date", "dte_bucket", "ts"]
        columns.extend(
            key for key in (*_SOURCE_EVENT_CLOCK_FIELDS, "source_clock_status") if key in names
        )
        df = pd.read_parquet(ledger_path, columns=columns)
        n_rows = len(df)
        n_sessions = df["session_date"].nunique()
        dte_counts = df["dte_bucket"].value_counts().to_dict()

        # events per day
        events_per_day: dict[str, int] = {}
        if "session_date" in df.columns:
            epd = df.groupby("session_date").size()
            events_per_day = epd.to_dict()

        # last ingested ts (string; sort lexicographically on ISO strings)
        last_ts = df["ts"].dropna().max() if n_rows > 0 else None

        return {
            "n_rows": n_rows,
            "source_clock_coverage": _source_clock_coverage(df),
            "n_sessions": n_sessions,
            "dte_bucket_counts": {str(k): int(v) for k, v in dte_counts.items()},
            "events_per_day":    {str(k): int(v) for k, v in events_per_day.items()},
            "last_ts": str(last_ts) if last_ts is not None else None,
        }
    except Exception as e:  # noqa: BLE001
        log.warning("flow_signals: ledger_stats failed: %s", e)
        return {"n_rows": 0, "n_sessions": 0, "dte_bucket_counts": {}, "last_ts": None}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flow-event ledger harvester")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count new events without writing to disk")
    parser.add_argument("--stats", action="store_true",
                        help="Print current ledger stats and exit")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.stats:
        stats = ledger_stats()
        import json as _json
        print(_json.dumps(stats, indent=2))
        return 0

    n = harvest(dry_run=args.dry_run)
    print(f"flow_signals: {'would append' if args.dry_run else 'appended'} {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
