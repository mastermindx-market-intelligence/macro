"""C1 trade-by-trade publicly downloadable demo: offline, private-only qualification.

The official demo is a vendor-labelled 3%-sample of participant-side execution
rows from 2025-03-28. Historical rows are NOT captured-PIT. SIDE denotes a
participant side, not necessarily aggressor; two sides may share execution ID.
Quote timestamps are absent even when NBBO values are present. Never publish,
score, rank, trade, or turn rows into unique institutional orders.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from collectors.options_free_samples import SourceRejected, _member, _csv_dicts, _uint

URL = "https://datashop.cboe.com/download/sample/289"
DAY = "2025-03-28"
INNER_ZIP = "C1_TBT_2025-03-28_sample_3pct.zip"
INNER_CSV = "C1_TBT_2025-03-28_sample_3pct.csv"
REQUIRED = frozenset({
    "transact_time", "trading_dt", "underlying", "osi_root",
    "expire_date", "call_put_flag", "strike_price", "size", "price",
    "nbbo_bid", "nbbo_ask", "side", "open_close", "capacity",
    "trade_type", "exec_id", "complex_exec_id", "session", "trading_segment",
})
CAPACITIES = frozenset({
    "Customer", "ProCustomer", "BrokerDealer", "Firm", "MarketMaker",
})
MAX_OUTER_BYTES = 12_000_000
MAX_CSV_BYTES = 32_000_000
MAX_ROWS = 250_000


def _money(value: str) -> Decimal | None:
    try:
        v = Decimal(value)
        if not v.is_finite():
            return None
        return v
    except (InvalidOperation, TypeError):
        return None


def qualify_cboe_tbt_sample(archive: bytes, receipt: dict[str, Any]) -> dict[str, Any]:
    if not 0 < len(archive) <= MAX_OUTER_BYTES:
        raise SourceRejected("TBT outer sample archive size exceeded")
    digest = hashlib.sha256(archive).hexdigest()
    if receipt.get("file_sha256") != digest or receipt.get("sample_session") != DAY:
        raise SourceRejected("TBT archive digest / session does not match acquisition")
    clock = receipt.get("downloaded_at_utc")
    try:
        d = datetime.fromisoformat(clock)
        if d.utcoffset() is None:
            raise ValueError("naive")
    except (ValueError, TypeError) as e:
        raise SourceRejected("TBT acquisition UTC clock missing") from e
    try:
        outer = zipfile.ZipFile(io.BytesIO(archive))
        inner = zipfile.ZipFile(io.BytesIO(
            _member(outer, INNER_ZIP, MAX_CSV_BYTES)
        ))
        csv_bytes = _member(inner, INNER_CSV, MAX_CSV_BYTES)
    except (zipfile.BadZipFile, RuntimeError) as e:
        raise SourceRejected("invalid TBT ZIP structure") from e
    reader = _csv_dicts(csv_bytes, REQUIRED)
    if receipt.get("columns") != reader.fieldnames:
        raise SourceRejected("TBT columns differ from acquisition receipt")
    n = 0
    known_side = 0
    known_open_close = 0
    known_capacity = 0
    fully_classified = 0
    incomplete_economics = 0
    valid_price_only_nbbo = 0
    nonmissing_complex_id = 0
    trade_dates = Counter()
    trade_types = Counter()
    capacity_counts = Counter()
    unknowns = Counter()
    by_symbol: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"participant_side_rows": 0, "classifiable_rows": 0,
                 "classifiable_contracts": defaultdict(int)}
    )
    for row in reader:
        n += 1
        if n > MAX_ROWS:
            raise SourceRejected("TBT sample exceeds row safety bound")
        if None in row or any(x is None for x in row.values()):
            raise SourceRejected("ragged TBT CSV row")
        session = row["trading_dt"].strip()
        if session != DAY:
            raise SourceRejected("TBT event does not belong to expected trading session")
        trade_dates[session] += 1
        symbol = row["underlying"].strip().upper()
        if not symbol or len(symbol) > 32 or any(ord(x) < 33 for x in symbol):
            raise SourceRejected("malformed TBT underlying")
        right = row["call_put_flag"].strip().upper()
        if right not in ("C", "P"):
            unknowns["right_unknown"] += 1
        bucket = by_symbol[symbol]
        bucket["participant_side_rows"] += 1
        side = row["side"].strip().upper()
        oc = row["open_close"].strip().upper()
        capacity = row["capacity"].strip()
        trade_types[row["trade_type"].strip() or "UNKNOWN"] += 1
        capacity_counts[capacity or "UNKNOWN"] += 1
        if row["complex_exec_id"].strip():
            nonmissing_complex_id += 1
        if side in ("B", "S"):
            known_side += 1
        else:
            unknowns["side_unknown"] += 1
        if oc in ("O", "C"):
            known_open_close += 1
        else:
            unknowns["open_close_unknown"] += 1
        if capacity in CAPACITIES:
            known_capacity += 1
        else:
            unknowns["capacity_unknown"] += 1
        try:
            size = _uint(row["size"], "size")
        except SourceRejected:
            size = 0
        price = _money(row["price"].strip())
        if size <= 0 or price is None or price <= 0:
            incomplete_economics += 1
        bid, ask = _money(row["nbbo_bid"].strip()), _money(row["nbbo_ask"].strip())
        if bid is not None and ask is not None and bid > 0 and ask > bid:
            valid_price_only_nbbo += 1
        # A price-consistent NBBO is NOT qualified for historical quote-age.
        if (right in ("C", "P") and side in ("B", "S") and oc in ("O", "C")
                and capacity in CAPACITIES and size > 0 and price is not None and price > 0):
            fully_classified += 1
            bucket["classifiable_rows"] += 1
            key = f"{right}:{capacity}:{'buy' if side == 'B' else 'sell'}:{'open' if oc == 'O' else 'close'}"
            bucket["classifiable_contracts"][key] += size
    if n == 0:
        raise SourceRejected("empty Cboe TBT sample")
    return {
        "schema": "options.free_cboe_tbt_eval/v1",
        "origin": "Cboe DataShop publicly downloadable C1 TBT demonstration sample",
        "source_url": URL,
        "source_sha256": digest,
        "source_retrieved_at_utc": clock,
        "effective_trade_session": DAY,
        "historical_original_available_at": None,
        "source_event_clock_timezone_qualified": False,
        "exchange": "C1",
        "population": "vendor_labeled_3_percent_sample_not_market_representative",
        "rights": "internal_evaluation_only_pending_commercial_rights",
        "publish": False,
        "signal_authority": False,
        "side_is_observed_participant_side_not_aggressor": True,
        "unique_executions_from_two_sided_rows": None,
        "quote_age_ms": None,
        "quote_age_qualified": False,
        "quote_age_null_reason": "TBT demo has no original NBBO quote event timestamp",
        "original_receiver_clock": None,
        "delta_matching_performed": False,
        "complex_package_reconstruction": False,
        "qualified_forward_response_windows": False,
        "rows_total": n,
        "rows_known_side": known_side,
        "rows_known_open_close": known_open_close,
        "rows_known_capacity": known_capacity,
        "rows_fully_classified_with_economics": fully_classified,
        "rows_price_only_valid_nbbo": valid_price_only_nbbo,
        "rows_incomplete_economics": incomplete_economics,
        "rows_with_complex_exec_id": nonmissing_complex_id,
        "unknown_reasons": dict(unknowns),
        "trade_types_observed": dict(sorted(trade_types.items())),
        "capacities_observed": dict(sorted(capacity_counts.items())),
        "underlyings": len(by_symbol),
        "participant_side_by_underlying": {
            symbol: {
                "participant_side_rows": counters["participant_side_rows"],
                "classifiable_rows": counters["classifiable_rows"],
                "classifiable_contracts": dict(sorted(counters["classifiable_contracts"].items())),
            }
            for symbol, counters in sorted(by_symbol.items())
        },
        "interpretation": (
            "These are partial participant-side observations, not distinct executions "
            "or institutional account ownership. Missing side/position stays unknown. "
            "No true quote-age, historic availability, prospectively matured markout "
            "or whole-market inference is established."
        ),
    }
