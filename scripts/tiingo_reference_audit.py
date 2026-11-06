"""Offline Tiingo public catalogue census and bounded acquisition candidates.

No API/credential access, download, archive mutation, canonical symbol mapping,
backtest enrollment, or work queue. Reads the vendor's public ZIP as evidence.
The catalogue includes reservations; dates/listing do NOT prove account access.
Reference: https://www.tiingo.com/documentation/end-of-day
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.tiingo_archive import require_external_root, symbol_path

MAX_ZIP_BYTES = 16 * 1024 * 1024
MAX_CSV_BYTES = 64 * 1024 * 1024
MAX_ROWS = 250_000
FIELDS = ("ticker", "exchange", "assetType", "priceCurrency", "startDate", "endDate")


class ReferenceAuditError(ValueError):
    pass


def _day(value: str) -> date | None:
    if not value or value.casefold() in {"null", "none", "nat", "nan"}:
        return None
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("noncanonical date")
    return parsed


def _observed(value: str) -> str:
    clock = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if clock.tzinfo is None or clock.utcoffset() is None:
        raise ReferenceAuditError("public evidence observation must be timezone-aware")
    return clock.astimezone(timezone.utc).isoformat()


def catalogue_rows(raw_zip: bytes) -> list[dict[str, str]]:
    if not isinstance(raw_zip, bytes) or len(raw_zip) > MAX_ZIP_BYTES:
        raise ReferenceAuditError("catalogue ZIP exceeds bounded size")
    try:
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
            entries = z.infolist()
            if len(entries) != 1 or entries[0].filename != "supported_tickers.csv":
                raise ReferenceAuditError("unexpected catalogue ZIP members")
            if entries[0].file_size > MAX_CSV_BYTES or entries[0].flag_bits & 1:
                raise ReferenceAuditError("catalogue CSV exceeds bound or is encrypted")
            with z.open(entries[0]) as stream:
                payload = stream.read(MAX_CSV_BYTES + 1)
            if len(payload) > MAX_CSV_BYTES:
                raise ReferenceAuditError("catalogue decompression bound exceeded")
        text = payload.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        header = reader.fieldnames or []
        if len(header) != len(set(header)) or not set(FIELDS).issubset(header):
            raise ReferenceAuditError("catalogue header is missing/duplicated")
        rows = []
        for row in reader:
            if len(rows) >= MAX_ROWS:
                raise ReferenceAuditError("catalogue row limit exceeded")
            if None in row or any(row.get(field) is None for field in FIELDS):
                raise ReferenceAuditError("ragged catalogue record")
            rows.append({field: row[field] for field in FIELDS})
        return rows
    except (zipfile.BadZipFile, UnicodeError, csv.Error, RuntimeError, EOFError) as exc:
        raise ReferenceAuditError("invalid catalogue archive") from exc


def _sizing_historical_eod(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Size an *offline* EOD acquisition hypothesis from the public catalogue.

    The existing planner currently chunks each EOD date range into at most
    366-day requests. Tiingo's public ingestion guide recommends fetching
    each full security history initially, then querying the daily bulk
    endpoint and refreshing adjusted histories after splits/dividends.
    A single full-history query is ONLY a request-count hypothesis; it may
    fail, paginate, exceed vendor quotas, or be unavailable to this account.
    This function does not create tasks, queues, authorizations or requests.
    """
    buckets: dict[tuple[str, str], list[int]] = {}
    per_year = 0
    for row in candidates:
        first, last = date.fromisoformat(row["request_start"]), date.fromisoformat(row["request_end"])
        days = (last - first).days + 1
        if days < 1:
            raise ReferenceAuditError("history candidate outside requested bounds")
        chunks = (days + 365) // 366
        per_year += chunks
        key = (row["assetType"], row["priceCurrency"])
        if key not in buckets:
            buckets[key] = [0, 0]
        buckets[key][0] += 1
        buckets[key][1] += chunks
    return {
        "scope": "ELIGIBLE_UNAMBIGUOUS_PUBLIC_CATALOGUE_EOD_METADATA_ONLY",
        "eligible_public_catalogue_records": len(candidates),
        "current_366_day_chunk_requests": per_year,
        "single_full_history_request_hypothesis": len(candidates),
        "one_call_guaranteed_by_vendor": False,
        "entitlement_confirmed": False,
        "downloaded_history": False,
        "execution_authorized": False,
        "network": False,
        "refresh_for_corporate_action_changes_unmodeled": True,
        "groups": [
            {"asset_type": asset, "currency": currency,
             "eligible_records": values[0], "current_366_day_requests": values[1]}
            for (asset, currency), values in sorted(buckets.items())
        ],
        "vendor_guidance": "https://www.tiingo.com/kb/article/the-fastest-method-to-ingest-tiingo-end-of-day-stock-api-data/",
        "caveat": (
            "Public metadata is not endpoint entitlement or an active EOD security census. "
            "The one-history-call comparison is a documented strategy hypothesis, not a "
            "guaranteed downloadable request count. Vendor throttles, payload limits, "
            "adjustment refreshes, retry costs, raw storage and actual bytes are unmeasured."
        ),
    }


def audit_catalogue(raw_zip: bytes, *, observed_at: str, start: date,
                    end: date, currencies: tuple[str, ...] = (),
                    asset_types: tuple[str, ...] = (), offset: int = 0,
                    limit: int = 25, expected_sha256: str | None = None) -> dict[str, Any]:
    if type(start) is not date or type(end) is not date or end < start:
        raise ReferenceAuditError("ordered history dates are required")
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
        raise ReferenceAuditError("invalid catalogue page bounds")
    observation = _observed(observed_at)
    digest = hashlib.sha256(raw_zip).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ReferenceAuditError("catalogue changed; page cursor cannot be reused")
    rows = catalogue_rows(raw_zip)
    by_asset, by_currency, by_exchange = Counter(), Counter(), Counter()
    end_dates = Counter()
    flags = Counter()
    seen: dict[tuple[str, ...], dict[str, str]] = {}
    conflicts: set[tuple[str, ...]] = set()
    ticker_keys: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    prepared: dict[tuple[str, ...], dict[str, Any]] = {}
    earliest: date | None = None
    latest: date | None = None
    max_future = datetime.fromisoformat(observation).date()
    for row in rows:
        by_asset[row["assetType"]] += 1
        by_currency[row["priceCurrency"]] += 1
        by_exchange[row["exchange"]] += 1
        end_dates[row["endDate"]] += 1
        key = tuple(row[field] for field in FIELDS[:4])
        ticker_keys[row["ticker"]].add(key)
        if key in seen:
            if seen[key] == row:
                flags["duplicate_exact_rows"] += 1
            else:
                conflicts.add(key)
                flags["conflicting_duplicate_rows"] += 1
            continue
        seen[key] = row
        symbol_ok = True
        try:
            symbol_path(row["ticker"])
        except (ValueError, TypeError):
            symbol_ok = False
            flags["current_adapter_symbol_refused"] += 1
        try:
            lo, hi = _day(row["startDate"]), _day(row["endDate"])
        except ValueError:
            flags["invalid_history_bounds"] += 1
            continue
        if lo is None or hi is None:
            flags["missing_history_bounds"] += 1
            continue
        if lo > hi:
            flags["invalid_history_bounds"] += 1
            continue
        flags["with_valid_history_bounds"] += 1
        earliest = min(earliest, lo) if earliest else lo
        latest = max(latest, hi) if latest else hi
        if hi > max_future:
            flags["history_end_after_observation_date"] += 1
        if hi < end:
            flags["history_ends_before_requested_end"] += 1
        if hi < start or lo > end:
            flags["outside_requested_history"] += 1
            continue
        if not symbol_ok:
            continue
        if currencies and row["priceCurrency"] not in currencies:
            continue
        if asset_types and row["assetType"] not in asset_types:
            continue
        prepared[key] = {
            **row, "request_start": max(lo, start).isoformat(),
            "request_end": min(hi, end).isoformat(),
            "provider_metadata_confirmation_needed": True,
            "account_access_proven": False, "canonical_identity_admitted": False,
        }
    ambiguous_tickers = {ticker for ticker, keys in ticker_keys.items() if len(keys) > 1}
    candidates = [prepared[key] for key in sorted(prepared)
                  if key not in conflicts and key[0] not in ambiguous_tickers]
    if offset > len(candidates):
        raise ReferenceAuditError("catalogue offset outside selected candidates")
    selected = candidates[offset:offset + limit]
    counts = {name: flags[name] for name in (
        "with_valid_history_bounds", "missing_history_bounds", "invalid_history_bounds",
        "current_adapter_symbol_refused", "duplicate_exact_rows", "conflicting_duplicate_rows",
        "history_end_after_observation_date", "history_ends_before_requested_end",
        "outside_requested_history",
    )}
    return {
        "schema": "mastermind.tiingo.public_reference_audit.v1",
        "catalogue_sha256": digest, "compressed_bytes": len(raw_zip),
        "observed_at_utc": observation,
        "public_source": "https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip",
        "history_requested": {"start": start.isoformat(), "end": end.isoformat()},
        "rows": len(rows), "unique_catalogue_keys": len(seen),
        "unique_ticker_strings": len(ticker_keys), "ambiguous_ticker_strings": len(ambiguous_tickers),
        "conflicting_catalogue_keys": len(conflicts), **counts,
        "asset_types": dict(sorted(by_asset.items())),
        "currencies": dict(sorted(by_currency.items())),
        "exchanges": dict(sorted(by_exchange.items())),
        "most_common_history_end_dates": end_dates.most_common(10),
        "earliest_advertised_history": earliest.isoformat() if earliest else None,
        "latest_advertised_history": latest.isoformat() if latest else None,
        "filters": {"currencies": list(currencies), "asset_types": list(asset_types)},
        "acquisition_candidate_count": len(candidates),
        "historical_eod_request_sizing": _sizing_historical_eod(candidates),
        "offset": offset, "selected": selected,
        "next_offset": offset + len(selected) if offset + len(selected) < len(candidates) else None,
        "catalogue_is_account_entitlement_proof": False,
        "historical_survivorship_safe_universe": False,
        "downloaded_price_rows": 0, "execution_authorized": False, "network": False,
        "caveat": "Public catalogue includes reservations; confirm individual metadata and actual responses. Old endDate is not proof of delisting.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-zip", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--currencies", default="")
    parser.add_argument("--asset-types", default="")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--expect-sha256")
    args = parser.parse_args(argv)
    try:
        path = require_external_root(Path(args.catalog_zip))
        if path.stat().st_size > MAX_ZIP_BYTES:
            raise ReferenceAuditError("catalogue ZIP exceeds bounded size")
        result = audit_catalogue(
            path.read_bytes(), observed_at=args.observed_at,
            start=date.fromisoformat(args.start), end=date.fromisoformat(args.end),
            currencies=tuple(x for x in args.currencies.split(",") if x),
            asset_types=tuple(x for x in args.asset_types.split(",") if x),
            offset=args.offset, limit=args.limit, expected_sha256=args.expect_sha256,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": type(exc).__name__}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
