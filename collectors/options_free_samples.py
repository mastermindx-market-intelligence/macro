"""Bounded, offline qualification of low-cost option participation sources.

The public Cboe C1 sample is an evaluation sample (20% of one 2025 session).
OCC's public account-type report does NOT include buy/sell or open/close intent,
and OCC's website terms do not grant commercial reuse. This module never
downloads data, publishes artifacts, or grants any research/signal authority.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from typing import Any

SAMPLE_DAY = "2025-03-28"
SAMPLE_URL = "https://datashop.cboe.com/download/sample/218"
SAMPLE_INNER_ZIP = "C1OpenClose_2025-03-28_sample_20pct.zip"
SAMPLE_CSV = "C1OpenClose_2025-03-28_sample_20pct.csv"
MAX_OUTER_BYTES = 12_000_000
MAX_INNER_BYTES = 30_000_000
MAX_ROWS = 100_000
_BUCKETS = ("lt_100", "100_199", "gt_199")
_PARTICIPANTS = ("cust", "procust")
_ACTIONS = ("open_buy", "close_buy", "open_sell", "close_sell")
_RIGHTS = ("C", "P")
CBOE_REQUIRED = frozenset({
    "quote_date", "underlying_symbol", "option_symbol",
    "expiration_date", "strike_price", "call_put_flag", "series_type",
    "total_exchange_vol", "open_interest",
    *(
        f"{p}_{b}_{a}_vol"
        for p in _PARTICIPANTS for b in _BUCKETS for a in _ACTIONS
    ),
})
OCC_REQUIRED = frozenset({
    "quantity", "underlying", "symbol", "actype",
    "porc", "exchange", "actdate", "contractDate",
})


class SourceRejected(ValueError):
    """An unqualified source is unavailable, not an observed zero."""


def _uint(value: Any, field: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise SourceRejected(f"missing/invalid nonnegative integer: {field}")
    return int(value)


def _member(z: zipfile.ZipFile, suffix: str, limit: int) -> bytes:
    matches = [i for i in z.infolist() if i.filename.endswith(suffix) and not i.is_dir()]
    if len(matches) != 1:
        raise SourceRejected(f"expected exactly one {suffix!r} member")
    item = matches[0]
    if item.file_size > limit or item.file_size <= 0:
        raise SourceRejected("member size is outside qualification bounds")
    content = z.read(item)
    if len(content) != item.file_size:
        raise SourceRejected("member byte count mismatch")
    return content


def _csv_dicts(blob: bytes, required: frozenset[str]) -> csv.DictReader:
    try:
        data = blob.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceRejected("source CSV must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(data))
    if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise SourceRejected("missing/duplicate CSV headings")
    if not required.issubset(reader.fieldnames):
        raise SourceRejected("missing required source fields: " +
                             ", ".join(sorted(required - set(reader.fieldnames))))
    return reader


def qualify_cboe_c1_sample(outer_zip: bytes, source_receipt: dict[str, Any]) -> dict[str, Any]:
    """Parse the precise publicly downloadable C1 sample; no market-wide inference."""
    if not 0 < len(outer_zip) <= MAX_OUTER_BYTES:
        raise SourceRejected("outer sample archive size exceeded")
    digest = hashlib.sha256(outer_zip).hexdigest()
    if digest != source_receipt.get("file_sha256"):
        raise SourceRejected("archive does not match original acquisition receipt")
    if source_receipt.get("sample_session") != SAMPLE_DAY:
        raise SourceRejected("original acquisition session mismatch")
    acquired_at = source_receipt.get("downloaded_at_utc")
    try:
        acquisition_clock = datetime.fromisoformat(acquired_at)
        if acquisition_clock.utcoffset() is None:
            raise ValueError("naive timestamp")
    except (ValueError, TypeError) as exc:
        raise SourceRejected("missing original UTC acquisition clock") from exc
    try:
        outer = zipfile.ZipFile(io.BytesIO(outer_zip))
        inner_bytes = _member(outer, SAMPLE_INNER_ZIP, MAX_INNER_BYTES)
        inner = zipfile.ZipFile(io.BytesIO(inner_bytes))
        csv_bytes = _member(inner, SAMPLE_CSV, MAX_INNER_BYTES)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise SourceRejected("invalid Cboe sample ZIP") from exc
    reader = _csv_dicts(csv_bytes, CBOE_REQUIRED)
    counters: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: {"C": defaultdict(int), "P": defaultdict(int)}
    )
    total_rows = 0
    standard_rows = 0
    nonstandard_rows = 0
    for row in reader:
        total_rows += 1
        if total_rows > MAX_ROWS:
            raise SourceRejected("sample exceeded row safety bound")
        if None in row or any(v is None for v in row.values()):
            raise SourceRejected("ragged sample CSV row")
        if row["quote_date"] != SAMPLE_DAY:
            raise SourceRejected("unexpected effective trade session")
        symbol = row["underlying_symbol"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9.^_-]{1,24}", symbol):
            raise SourceRejected("malformed underlying symbol")
        right = row["call_put_flag"].strip()
        if right not in _RIGHTS:
            raise SourceRejected("unknown option right")
        _uint(row["total_exchange_vol"], "total_exchange_vol")
        _uint(row["open_interest"], "open_interest")
        series_type = row["series_type"]
        if series_type != "S":
            nonstandard_rows += 1
            continue
        standard_rows += 1
        bucket = counters[symbol][right]
        bucket["standard_series_rows"] += 1
        for participant in _PARTICIPANTS:
            for action in _ACTIONS:
                key = f"{participant}_{action}_vol"
                bucket[key] += sum(
                    _uint(row[f"{participant}_{size}_{action}_vol"],
                          f"{participant}_{size}_{action}_vol")
                    for size in _BUCKETS
                )
    if total_rows == 0 or standard_rows == 0:
        raise SourceRejected("empty or nonstandard-only sample")
    return {
        "schema": "options.free_cboe_eval/v1",
        "origin": "Cboe DataShop publicly downloadable C1 sample",
        "source_url": SAMPLE_URL,
        "source_sha256": digest,
        "source_retrieved_at_utc": acquired_at,
        "effective_trade_session": SAMPLE_DAY,
        "source_event_available_at": None,
        "exchange": "C1",
        "population": "vendor_labeled_20_percent_sample_not_market_representative",
        "rights": "internal_evaluation_only_pending_commercial_rights",
        "publish": False,
        "signal_authority": False,
        "forward_validation_authority": False,
        "dealer_inventory_observed": False,
        "customer_position_ownership_observed": False,
        "delta_matching_performed": False,
        "rows_total": total_rows,
        "rows_standard": standard_rows,
        "rows_nonstandard": nonstandard_rows,
        "underlyings_standard": len(counters),
        "observed_sample_only": {k: dict(v) for k, v in sorted(counters.items())},
        "interpretation": (
            "Customer and professional-customer exchange volume by opening/closing "
            "and transaction side; cannot establish whole-portfolio motive, "
            "nationwide totals, representative exchange share or historical PIT."
        ),
    }


def qualify_occ_volume_csv(blob: bytes, expected_session: str, expected_underlying: str) -> dict[str, Any]:
    """Offline ONLY. OCC rows represent account-side cleared volume, not opening intent.

    No fetch or commercial consumption rights are granted by this parser.
    Never sum C/F/M account-side quantities and call them unique executed contracts.
    """
    reader = _csv_dicts(blob, OCC_REQUIRED)
    by_account_side: dict[str, int] = defaultdict(int)
    total_rows = 0
    for row in reader:
        total_rows += 1
        if total_rows > MAX_ROWS:
            raise SourceRejected("OCC report exceeded row safety bound")
        if None in row or any(v is None for v in row.values()):
            raise SourceRejected("ragged OCC CSV")
        if row["underlying"].upper() != expected_underlying.upper():
            raise SourceRejected("OCC report underlying mismatch")
        if row["actdate"] != datetime.strptime(expected_session, "%Y-%m-%d").strftime("%m/%d/%Y"):
            raise SourceRejected("OCC session mismatch")
        if row["porc"] not in _RIGHTS or row["actype"] not in ("C", "F", "M"):
            raise SourceRejected("unrecognized OCC category")
        venue = row["exchange"].strip()
        if not venue or len(venue) > 24:
            raise SourceRejected("unrecognized OCC venue")
        quantity = _uint(row["quantity"], "quantity")
        by_account_side[f"{venue}:{row['actype']}:{row['porc']}"] += quantity
    if total_rows == 0:
        raise SourceRejected("empty OCC account volume source")
    return {
        "schema": "options.occ_account_volume_eval/v1",
        "population": "source_rows_for_requested_underlying_only",
        "effective_trade_session": expected_session,
        "underlying": expected_underlying.upper(),
        "rows": total_rows,
        "account_side_quantity_by_venue": dict(sorted(by_account_side.items())),
        "opening_closing_observed": False,
        "trade_direction_observed": False,
        "nationwide_unique_contracts_computed": False,
        "commercial_use_authorized": False,
        "publish": False,
        "signal_authority": False,
    }
