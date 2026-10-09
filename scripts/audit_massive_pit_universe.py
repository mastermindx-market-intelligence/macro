#!/usr/bin/env python3
"""Read-only Massive point-in-time universe -> Data OS identity qualification.

This is a qualification/audit tool, not a collector, writer, universe store, or
identity allocator.

WHY
---
Market Experience needs a survivorship-safe historical population without
silently treating a ticker string as an entity.  Massive's reference API can
return the common-stock population active on a historical date.  Data OS is the
estate's exact identity authority.  This script measures the seam between them
without mutating either side.

AUTHORITY
---------
* Source transport/credentials are reused from
  scripts.ingest_market_memory_sources_spy._build_fetcher.  No second vendor
  client or credential plane is created.
* Canonical identity is read only through the existing
  lib.dataos.identity.VendorAliasTable + reference.security_master.
* A source-native ticker/MIC or a CURRENT CIK match is diagnostic evidence only.
  It never becomes canonical identity without a dated Data OS alias.
* No output file exists.  The only artifact is one bounded JSON receipt on
  stdout.

The expected first-run result is intentionally NOT "ready": Data OS does not
currently carry a Massive historical-naming vendor namespace.  That refusal is
the useful result: it quantifies the exact owner gap before any identity rows
are authored.

Production credential selection remains owned by the existing Market Memory source
runtime.  This audit consumes CREDENTIALS_DIRECTORY only when that owning runtime
already supplied it; there is deliberately no CLI credential-path override.

Example (inside the owning credential environment, still read-only):

    python3 scripts/audit_massive_pit_universe.py --date 2006-01-03

Tests are network-free:
    python3 -m pytest tests/test_massive_pit_universe_audit.py -q
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qsl, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.dataos.identity import KNOWN_MICS, VendorAliasTable  # noqa: E402

SCHEMA = "market_experience.massive_pit_universe_audit.v1"
DEFAULT_VENDOR_NAMESPACE = "massive"
DEFAULT_REFERENCE_ROOT = ROOT / "data" / "reference"
DEFAULT_PAGE_LIMIT = 1000
DEFAULT_MAX_PAGES = 20
MAX_MAX_PAGES = 100
MAX_EXAMPLES_PER_STATUS = 5

STATUS_RESOLVED = "RESOLVED"
STATUS_SOURCE_ID_INCOMPLETE = "SOURCE_ID_INCOMPLETE"
STATUS_SOURCE_DUPLICATE = "SOURCE_DUPLICATE"
STATUS_UNSUPPORTED_MIC = "UNSUPPORTED_MIC"
STATUS_MISSING_CANONICAL_ALIAS = "MISSING_CANONICAL_ALIAS"
STATUS_CURRENT_CIK_MATCH_ONLY = "CURRENT_CIK_MATCH_ONLY"
STATUS_CURRENT_CIK_DIVERGENCE = "CURRENT_CIK_DIVERGENCE"
STATUS_AMBIGUOUS_CURRENT_MASTER = "AMBIGUOUS_CURRENT_MASTER"
STATUS_BROKEN_CANONICAL_ALIAS = "BROKEN_CANONICAL_ALIAS"

STATUSES = (
    STATUS_RESOLVED,
    STATUS_SOURCE_ID_INCOMPLETE,
    STATUS_SOURCE_DUPLICATE,
    STATUS_UNSUPPORTED_MIC,
    STATUS_MISSING_CANONICAL_ALIAS,
    STATUS_CURRENT_CIK_MATCH_ONLY,
    STATUS_CURRENT_CIK_DIVERGENCE,
    STATUS_AMBIGUOUS_CURRENT_MASTER,
    STATUS_BROKEN_CANONICAL_ALIAS,
)

_ALLOWED_NEXT_HOSTS = frozenset({"api.polygon.io", "api.massive.com"})
_FORBIDDEN_QUERY_KEYS = frozenset({"apikey", "api_key", "authorization", "token"})


class AuditError(RuntimeError):
    """The audit could not produce a trustworthy receipt."""


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    return text


def _normalize_cik(value: object) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    return digits.zfill(10)


def _source_stable_id_present(row: Mapping[str, Any]) -> bool:
    return any(
        _clean_text(row.get(field))
        for field in ("cik", "composite_figi", "share_class_figi")
    )


def _source_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        (_clean_text(row.get("primary_exchange")) or "").upper(),
        (_clean_text(row.get("ticker")) or "").upper(),
    )


def _safe_example(
    row: Mapping[str, Any],
    *,
    status: str,
    security_id: str | None = None,
    canonical_cik: str | None = None,
) -> dict[str, Any]:
    """Bounded, non-secret identity evidence; never include a provider body."""
    return {
        "ticker": (_clean_text(row.get("ticker")) or "").upper() or None,
        "primary_exchange": (
            (_clean_text(row.get("primary_exchange")) or "").upper() or None
        ),
        "source_cik": _normalize_cik(row.get("cik")),
        "source_composite_figi_present": bool(_clean_text(row.get("composite_figi"))),
        "source_share_class_figi_present": bool(
            _clean_text(row.get("share_class_figi"))
        ),
        "canonical_security_id": security_id,
        "canonical_current_cik": canonical_cik,
        "status": status,
    }


def _next_request(next_url: str) -> tuple[str, dict[str, str]]:
    """Turn Massive/Polygon next_url into the existing fetcher's path+params.

    The source client owns authentication.  A pagination URL carrying credentials
    is refused rather than copied into params/logs.
    """
    parsed = urlparse(str(next_url))
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in _ALLOWED_NEXT_HOSTS:
        raise AuditError(f"untrusted pagination host: {host or '<missing>'}")
    params: dict[str, str] = {}
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _FORBIDDEN_QUERY_KEYS:
            raise AuditError("pagination URL unexpectedly carries credential material")
        params[key] = value
    if not parsed.path.startswith("/"):
        raise AuditError("pagination URL has no absolute path")
    return parsed.path, params


def fetch_pit_common_stock_rows(
    fetcher: Callable[[str, Mapping[str, Any] | None], Any],
    *,
    on: date,
    max_pages: int = DEFAULT_MAX_PAGES,
    page_limit: int = DEFAULT_PAGE_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch a bounded PIT active-common-stock population.

    The function follows provider pagination only up to max_pages.  If another
    page remains, complete=False and no downstream caller may call the population
    complete.
    """
    if isinstance(max_pages, bool) or not 1 <= int(max_pages) <= MAX_MAX_PAGES:
        raise AuditError(f"max_pages must be 1..{MAX_MAX_PAGES}")
    if isinstance(page_limit, bool) or not 1 <= int(page_limit) <= DEFAULT_PAGE_LIMIT:
        raise AuditError(f"page_limit must be 1..{DEFAULT_PAGE_LIMIT}")

    path = "/v3/reference/tickers"
    params: dict[str, Any] = {
        "market": "stocks",
        "type": "CS",
        "date": on.isoformat(),
        "active": "true",
        "order": "asc",
        "sort": "ticker",
        "limit": int(page_limit),
    }
    rows: list[dict[str, Any]] = []
    pages = 0
    next_url: str | None = None

    while pages < int(max_pages):
        try:
            payload = fetcher(path, params)
        except Exception as exc:  # noqa: BLE001
            raise AuditError(
                f"Massive PIT request failed: {type(exc).__name__}"
            ) from exc
        if not isinstance(payload, dict):
            raise AuditError("Massive PIT response is not an object")
        body_status = str(payload.get("status") or "").upper()
        if body_status and body_status not in {"OK", "SUCCESS"}:
            raise AuditError(f"Massive PIT response status={body_status}")
        result_rows = payload.get("results")
        if not isinstance(result_rows, list):
            raise AuditError("Massive PIT response results is not a list")
        for row in result_rows:
            if not isinstance(row, dict):
                raise AuditError("Massive PIT result row is not an object")
            rows.append(dict(row))

        pages += 1
        raw_next = payload.get("next_url")
        next_url = str(raw_next).strip() if raw_next else None
        if not next_url:
            break
        path, params = _next_request(next_url)

    return rows, {
        "pages_fetched": pages,
        "row_count": len(rows),
        "complete": next_url is None,
        "truncated_by_max_pages": next_url is not None,
        "page_limit": int(page_limit),
        "max_pages": int(max_pages),
    }


def _active_master_rows(master_records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in master_records:
        row = dict(raw)
        if _clean_text(row.get("security_state")):
            # The only current non-null state is a superseded duplicate mint.
            continue
        sid = _clean_text(row.get("security_id"))
        if sid is None:
            continue
        out.append(row)
    return out


def audit_identity_rows(
    source_rows: Iterable[Mapping[str, Any]],
    *,
    on: date,
    alias_records: Iterable[Mapping[str, Any]],
    master_records: Iterable[Mapping[str, Any]],
    canonical_vendor: str = DEFAULT_VENDOR_NAMESPACE,
) -> dict[str, Any]:
    """Classify source rows against the existing Data OS authority.

    CURRENT_CIK_MATCH_ONLY is deliberately not RESOLVED.  Data OS documents
    issuer_cik as current-registrant evidence with no historical asof authority.
    """
    aliases_list = [dict(r) for r in alias_records]
    table = VendorAliasTable.from_records(aliases_list)
    active_master = _active_master_rows(master_records)
    by_security = {
        str(row["security_id"]): row
        for row in active_master
        if _clean_text(row.get("security_id"))
    }

    current_candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in active_master:
        mic = (_clean_text(row.get("mic")) or "").upper()
        code = (_clean_text(row.get("inception_code")) or "").upper()
        if mic and code:
            current_candidates[(mic, code)].append(row)

    source = [dict(r) for r in source_rows]
    key_counts = Counter(_source_key(r) for r in source)
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = {s: [] for s in STATUSES}

    vendor_rows = sum(1 for r in aliases_list if str(r.get("vendor") or "") == canonical_vendor)
    resolved_current_cik_divergence_count = 0

    for row in source:
        mic, ticker = _source_key(row)
        source_cik = _normalize_cik(row.get("cik"))
        stable_id_present = _source_stable_id_present(row)
        status: str
        sid: str | None = None
        canonical_cik: str | None = None

        if not mic or not ticker or key_counts[(mic, ticker)] > 1:
            status = STATUS_SOURCE_DUPLICATE
        elif mic not in KNOWN_MICS or not mic.startswith("X"):
            status = STATUS_UNSUPPORTED_MIC
        else:
            sid = table.resolve(canonical_vendor, ticker, on)
            if sid is not None:
                master = by_security.get(sid)
                if master is None:
                    status = STATUS_BROKEN_CANONICAL_ALIAS
                else:
                    canonical_cik = _normalize_cik(master.get("issuer_cik"))
                    if not stable_id_present:
                        status = STATUS_SOURCE_ID_INCOMPLETE
                    else:
                        # The dated Data OS alias is canonical security identity.
                        # issuer_cik is explicitly current-only evidence, so a
                        # historical source CIK divergence is diagnostic and may
                        # not veto the authoritative dated alias.
                        status = STATUS_RESOLVED
                        if source_cik and canonical_cik and source_cik != canonical_cik:
                            resolved_current_cik_divergence_count += 1
            else:
                candidates = current_candidates.get((mic, ticker), [])
                if len(candidates) > 1:
                    status = STATUS_AMBIGUOUS_CURRENT_MASTER
                elif len(candidates) == 1:
                    candidate = candidates[0]
                    canonical_cik = _normalize_cik(candidate.get("issuer_cik"))
                    if source_cik and canonical_cik and source_cik != canonical_cik:
                        status = STATUS_CURRENT_CIK_DIVERGENCE
                    elif source_cik and canonical_cik and source_cik == canonical_cik:
                        # Useful evidence, but current CIK has no historical asof authority.
                        status = STATUS_CURRENT_CIK_MATCH_ONLY
                    elif not stable_id_present:
                        status = STATUS_SOURCE_ID_INCOMPLETE
                    else:
                        status = STATUS_MISSING_CANONICAL_ALIAS
                elif not stable_id_present:
                    status = STATUS_SOURCE_ID_INCOMPLETE
                else:
                    status = STATUS_MISSING_CANONICAL_ALIAS

        counts[status] += 1
        if len(examples[status]) < MAX_EXAMPLES_PER_STATUS:
            examples[status].append(
                _safe_example(
                    row,
                    status=status,
                    security_id=sid,
                    canonical_cik=canonical_cik,
                )
            )

    compact_examples = {k: v for k, v in examples.items() if v}
    total = len(source)
    resolved = counts[STATUS_RESOLVED]
    return {
        "canonical_vendor_namespace": canonical_vendor,
        "canonical_vendor_rows_total": vendor_rows,
        "counts": {status: counts.get(status, 0) for status in STATUSES},
        "examples": compact_examples,
        "canonical_identity_ready": total > 0 and resolved == total,
        "resolved_fraction": (resolved / total) if total else 0.0,
        "current_cik_match_only_is_authority": False,
        "resolved_current_cik_divergence_count": (
            resolved_current_cik_divergence_count
        ),
    }


def _records_from_parquet(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - production dependency
        raise AuditError("pandas is required to read Data OS parquet") from exc
    if not path.is_file():
        raise AuditError(f"required Data OS artifact missing: {path}")
    try:
        df = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        raise AuditError(f"cannot read Data OS artifact: {path.name}") from exc

    records: list[dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        clean: dict[str, Any] = {}
        for key, value in raw.items():
            try:
                is_null = bool(pd.isna(value))
            except (TypeError, ValueError):
                is_null = False
            clean[key] = None if is_null else value
        records.append(clean)
    return records


def build_receipt(
    *,
    on: date,
    source_rows: list[dict[str, Any]],
    source_receipt: Mapping[str, Any],
    alias_records: list[dict[str, Any]],
    master_records: list[dict[str, Any]],
    canonical_vendor: str,
) -> dict[str, Any]:
    identity = audit_identity_rows(
        source_rows,
        on=on,
        alias_records=alias_records,
        master_records=master_records,
        canonical_vendor=canonical_vendor,
    )
    return {
        "schema": SCHEMA,
        "asof": on.isoformat(),
        "universe_definition": {
            "market": "stocks",
            "type": "CS",
            "active": True,
            "meaning": "Massive point-in-time active common-stock population; not S&P membership",
        },
        "source": dict(source_receipt),
        "identity": identity,
        "authority": {
            "source_population_complete": bool(source_receipt.get("complete")),
            "canonical_identity_ready": bool(identity["canonical_identity_ready"]),
            "may_write_identity": False,
            "may_train": False,
            "may_publish_forecast": False,
            "may_rank": False,
            "may_size": False,
            "may_trade": False,
        },
    }


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Read-only Massive PIT common-stock universe -> Data OS identity audit"
    )
    ap.add_argument("--date", required=True, type=_parse_date)
    ap.add_argument(
        "--reference-root",
        default=str(DEFAULT_REFERENCE_ROOT),
        help="directory containing security_master.parquet and vendor_aliases.parquet",
    )
    ap.add_argument(
        "--canonical-vendor",
        default=DEFAULT_VENDOR_NAMESPACE,
        help="Data OS vendor namespace to audit; no rows are created",
    )
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    args = ap.parse_args(argv)

    from scripts.ingest_market_memory_sources_spy import _build_fetcher  # noqa: PLC0415

    fetcher = _build_fetcher()
    if fetcher is None:
        receipt = {
            "schema": SCHEMA,
            "asof": args.date.isoformat(),
            "status": "no_credentials",
            "authority": {"may_write_identity": False, "may_train": False},
        }
        print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
        return 2

    try:
        rows, source_receipt = fetch_pit_common_stock_rows(
            fetcher,
            on=args.date,
            max_pages=args.max_pages,
        )
        ref_root = Path(args.reference_root)
        aliases = _records_from_parquet(ref_root / "vendor_aliases.parquet")
        master = _records_from_parquet(ref_root / "security_master.parquet")
        receipt = build_receipt(
            on=args.date,
            source_rows=rows,
            source_receipt=source_receipt,
            alias_records=aliases,
            master_records=master,
            canonical_vendor=str(args.canonical_vendor),
        )
    except AuditError as exc:
        receipt = {
            "schema": SCHEMA,
            "asof": args.date.isoformat(),
            "status": "refused",
            "reason": str(exc),
            "authority": {"may_write_identity": False, "may_train": False},
        }
        print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
        return 3

    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
