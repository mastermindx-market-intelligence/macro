"""Research Vault subject candidates and exact Data OS identity binding.

This module is deliberately a bridge, not an identity authority.

Candidate discovery may use the existing context-only engine.entity_resolver plus
source-provided sidecar tickers. Exact security identity is granted only by the
caller-supplied lib.dataos.identity.VendorAliasTable for an explicit vendor
namespace and publication date.

Unmapped symbols remain typed unresolved candidates. Nothing here mints a
security id, edits the alias table, or treats model output as identity truth.

No I/O and no model calls live here.
"""
from __future__ import annotations

from datetime import date, datetime
import math
from typing import Any, Iterable, Mapping

from lib.dataos.identity import IdentityError, VendorAliasTable, parse_id

CANDIDATE_SCHEMA = "research_vault.subject_candidates.v1"
RESOLUTION_SCHEMA = "research_vault.subject_resolution.v1"
RESOLVED = "RESOLVED"
UNMAPPED = "UNMAPPED"

_MAX_SYMBOL_LEN = 32
_SOURCE_FIELDS = ("source_sidecar", "title", "summary", "body")


def _symbol(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    raw = value.strip().upper()
    if not raw or len(raw) > _MAX_SYMBOL_LEN:
        return ""
    if any(ch.isspace() for ch in raw):
        return ""
    return raw


def _publication_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("published_at must be a date/datetime/ISO string")
    raw = value.strip()
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("published_at must start with an ISO date") from exc


def _confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("candidate confidence must be finite")
    return max(0.0, min(1.0, result))


def _add_candidate(
    bucket: dict[str, dict[str, Any]],
    *,
    symbol: str,
    confidence: float,
    method: str,
    source_field: str,
) -> None:
    sym = _symbol(symbol)
    if not sym:
        return
    if source_field not in _SOURCE_FIELDS:
        raise ValueError(f"unsupported source_field: {source_field!r}")
    if not isinstance(method, str) or not method.strip():
        raise ValueError("candidate method must be nonempty")

    row = bucket.get(sym)
    if row is None:
        bucket[sym] = {
            "symbol": sym,
            "confidence": _confidence(confidence),
            "methods": [method.strip()],
            "source_fields": [source_field],
        }
        return
    row["confidence"] = max(row["confidence"], _confidence(confidence))
    if method.strip() not in row["methods"]:
        row["methods"].append(method.strip())
    if source_field not in row["source_fields"]:
        row["source_fields"].append(source_field)


def discover_candidates(
    *,
    report_id: str,
    source_tickers: Iterable[str] = (),
    title: str = "",
    summary_points: Iterable[str] = (),
    body: str = "",
    include_body: bool = False,
) -> dict[str, Any]:
    """Return deterministic ticker candidates without granting exact identity.

    source_tickers are highest-confidence source metadata.
    Existing engine.entity_resolver output is candidate/context evidence only.
    Literal publisher text is not copied into this artifact; provenance records
    only which input field caused the candidate.

    Body scanning is opt-in because full Research Vault bodies are licensed/private
    and may be large. F5/F7 choose when a full-text derivative is available.
    """
    if not isinstance(report_id, str) or not report_id.strip():
        raise ValueError("report_id must be nonempty")
    if not isinstance(title, str) or not isinstance(body, str):
        raise TypeError("title/body must be strings")

    if isinstance(source_tickers, (str, bytes)):
        raise TypeError("source_tickers must be an iterable of symbols, not a string")

    bucket: dict[str, dict[str, Any]] = {}
    for raw in source_tickers:
        _add_candidate(
            bucket,
            symbol=str(raw),
            confidence=1.0,
            method="source_sidecar",
            source_field="source_sidecar",
        )

    summary = "\n".join(
        item.strip()
        for item in summary_points
        if isinstance(item, str) and item.strip()
    )

    from engine import entity_resolver

    for field, text in (("title", title), ("summary", summary)):
        if not text:
            continue
        for row in entity_resolver.resolve_us(text):
            _add_candidate(
                bucket,
                symbol=row.get("ticker", ""),
                confidence=row.get("confidence", 0.0),
                method=f"entity_resolver:{row.get('method', 'unknown')}",
                source_field=field,
            )
        for row in entity_resolver.resolve_cn(text):
            _add_candidate(
                bucket,
                symbol=row.get("ticker", ""),
                confidence=row.get("confidence", 0.0),
                method=f"entity_resolver:{row.get('method', 'unknown')}",
                source_field=field,
            )

    if include_body and body:
        for row in entity_resolver.resolve_us(body):
            _add_candidate(
                bucket,
                symbol=row.get("ticker", ""),
                confidence=row.get("confidence", 0.0),
                method=f"entity_resolver:{row.get('method', 'unknown')}",
                source_field="body",
            )
        for row in entity_resolver.resolve_cn(body):
            _add_candidate(
                bucket,
                symbol=row.get("ticker", ""),
                confidence=row.get("confidence", 0.0),
                method=f"entity_resolver:{row.get('method', 'unknown')}",
                source_field="body",
            )

    rows = sorted(
        bucket.values(),
        key=lambda row: (-row["confidence"], row["symbol"]),
    )
    return {
        "schema": CANDIDATE_SCHEMA,
        "report_id": report_id.strip(),
        "candidate_count": len(rows),
        "body_scanned": bool(include_body and body),
        "candidates": rows,
        "authority": "candidate_context_only",
    }


def resolve_candidates(
    candidates: Mapping[str, Any],
    *,
    aliases: VendorAliasTable,
    alias_vendor: str,
    published_at: date | datetime | str,
) -> dict[str, Any]:
    """Bind candidates to exact Data OS security ids or preserve typed UNMAPPED.

    The caller must choose the reviewed Data OS alias namespace. This module does
    not guess that a Research Vault/MarketDesk symbol belongs to membership,
    store, yahoo or any other vendor space.
    """
    if not isinstance(candidates, Mapping) or candidates.get("schema") != CANDIDATE_SCHEMA:
        raise ValueError("unsupported candidate artifact")
    report_id = candidates.get("report_id")
    if not isinstance(report_id, str) or not report_id.strip():
        raise ValueError("candidate artifact report_id must be nonempty")
    if not isinstance(aliases, VendorAliasTable):
        raise TypeError("aliases must be VendorAliasTable")
    if not isinstance(alias_vendor, str) or not alias_vendor.strip():
        raise ValueError("alias_vendor must be explicit")
    on = _publication_date(published_at)

    raw_rows = candidates.get("candidates")
    if not isinstance(raw_rows, list):
        raise ValueError("candidates must be a list")

    resolved: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"candidates[{index}] must be an object")
        symbol = _symbol(row.get("symbol"))
        if not symbol:
            raise ValueError(f"candidates[{index}].symbol is invalid")
        confidence = _confidence(row.get("confidence"))
        methods = row.get("methods")
        source_fields = row.get("source_fields")
        if not isinstance(methods, list) or not all(
            isinstance(item, str) and item for item in methods
        ):
            raise ValueError(f"candidates[{index}].methods is invalid")
        if not isinstance(source_fields, list) or not all(
            item in _SOURCE_FIELDS for item in source_fields
        ):
            raise ValueError(f"candidates[{index}].source_fields is invalid")

        security_id = aliases.resolve(alias_vendor.strip(), symbol, on)
        if security_id is not None:
            try:
                kind, _listing = parse_id(security_id)
            except IdentityError as exc:
                raise ValueError(
                    f"Data OS alias target for {symbol!r} is not a valid security id"
                ) from exc
            if kind != "security":
                raise ValueError(
                    f"Data OS alias target for {symbol!r} is not a security id"
                )
        state = RESOLVED if security_id else UNMAPPED
        resolved.append(
            {
                "symbol": symbol,
                "resolution_state": state,
                "security_id": security_id,
                "alias_vendor": alias_vendor.strip(),
                "resolution_date": on.isoformat(),
                "confidence": confidence,
                "methods": list(methods),
                "source_fields": list(source_fields),
            }
        )

    return {
        "schema": RESOLUTION_SCHEMA,
        "report_id": report_id.strip(),
        "alias_vendor": alias_vendor.strip(),
        "resolution_date": on.isoformat(),
        "resolved_count": sum(1 for row in resolved if row["resolution_state"] == RESOLVED),
        "unmapped_count": sum(1 for row in resolved if row["resolution_state"] == UNMAPPED),
        "subjects": resolved,
        "authority": {
            "candidate": "context_only",
            "exact_security_identity": "data_os_vendor_alias_table",
        },
    }
