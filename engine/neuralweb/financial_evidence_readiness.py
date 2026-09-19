"""Source-bound financial evidence admission over existing Company Intelligence readers.

This module creates no source, store, calculator, model call, score or trade authority.
It separates byte-replayed accounting facts from weaker context metrics and explicitly
refuses to mint a calculator payload until the source contract carries comparable
period duration and the other required exact inputs.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

SCHEMA = "brain.financial_evidence_readiness.v1"
AUTHORITY = "context_only"

_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,15}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_CONTEXT_METRICS = (
    "revenue_growth_pct",
    "eps_growth_pct",
    "gross_margin_pct",
)
_UNIT_MAP = {
    "usd_thousands": ("USD", "thousands"),
    "usd_millions": ("USD", "millions"),
    "usd_billions": ("USD", "billions"),
}
_PROPhet_FALSE = {
    "may_rank": False,
    "may_size": False,
    "may_gate": False,
    "prophet_authority": False,
}


def _decimal_text(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or abs(number) > Decimal("1e18"):
        return None
    if not number:
        return "0"
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _bounded_text(value: object, *, maximum: int = 256) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > maximum:
        return None
    return text


def _source_receipt(span: object) -> dict[str, str] | None:
    if not isinstance(span, Mapping):
        return None
    if (
        span.get("schema") != "source_span.v1"
        or span.get("receipt_state") != "byte_replayed"
        or span.get("rights_profile") != "rp_public_primary_v1"
        or span.get("authority") != AUTHORITY
    ):
        return None
    span_id = _bounded_text(span.get("span_id"), maximum=128)
    text_sha = _bounded_text(span.get("text_sha256"), maximum=64)
    receipt = span.get("receipt")
    if not span_id or not text_sha or not _SHA256_RE.fullmatch(text_sha):
        return None
    if not isinstance(receipt, Mapping):
        return None
    source_sha = _bounded_text(receipt.get("source_sha256"), maximum=64)
    receipt_text_sha = _bounded_text(receipt.get("text_sha256"), maximum=64)
    if (
        not source_sha
        or not receipt_text_sha
        or not _SHA256_RE.fullmatch(source_sha)
        or receipt_text_sha != text_sha
    ):
        return None
    start = receipt.get("span_start_byte")
    end = receipt.get("span_end_byte")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > 100_000_000
    ):
        return None
    return {
        "span_id": span_id,
        "text_sha256": text_sha,
        "source_sha256": source_sha,
        "receipt_state": "byte_replayed",
        "rights_profile": "rp_public_primary_v1",
    }


def _event_payload(workspace_result: object) -> dict[str, Any]:
    if not isinstance(workspace_result, Mapping) or workspace_result.get("available") is not True:
        return {}
    workspace = workspace_result.get("workspace")
    if not isinstance(workspace, Mapping):
        return {}
    event_id = _bounded_text(workspace.get("event_id") or workspace_result.get("event_id"))
    generation = _bounded_text(workspace.get("generation_id"), maximum=64)
    lifecycle = workspace.get("lifecycle")
    fiscal = workspace.get("fiscal_period")
    out: dict[str, Any] = {
        "event_id": event_id,
        "generation_id": generation,
        "lifecycle_state": (
            _bounded_text(lifecycle.get("state"), maximum=32)
            if isinstance(lifecycle, Mapping)
            else None
        ),
        "source_available_at": (
            _bounded_text(lifecycle.get("source_available_at"), maximum=64)
            if isinstance(lifecycle, Mapping)
            else None
        ),
        "observed_at": (
            _bounded_text(lifecycle.get("observed_at"), maximum=64)
            if isinstance(lifecycle, Mapping)
            else None
        ),
        "fiscal_period": {
            "year": fiscal.get("year"),
            "quarter": fiscal.get("quarter"),
            "calendar_end": fiscal.get("calendar_end"),
        } if isinstance(fiscal, Mapping) else None,
    }
    return out


def _workspace_is_context_only(workspace_result: object) -> bool:
    if not isinstance(workspace_result, Mapping):
        return False
    workspace = workspace_result.get("workspace")
    if not isinstance(workspace, Mapping):
        return False
    return (
        workspace_result.get("available") is True
        and workspace_result.get("authority") == AUTHORITY
        and workspace_result.get("is_context_only") is True
        and workspace.get("schema") == "event_workspace.v1"
        and workspace.get("authority") == AUTHORITY
        and workspace.get("prophet_flags") == _PROPhet_FALSE
    )


def _exact_revenue(workspace_result: object) -> list[dict[str, Any]]:
    if not _workspace_is_context_only(workspace_result):
        return []
    workspace = workspace_result["workspace"]
    event_id = workspace.get("event_id")
    facts = workspace.get("facts")
    if not isinstance(facts, list):
        return []
    accepted: list[dict[str, Any]] = []
    for fact in facts:
        if not isinstance(fact, Mapping):
            continue
        if (
            fact.get("schema") != "event_fact.v1"
            or fact.get("fact_id") != "fact_revenue_gaap"
            or fact.get("event_id") != event_id
            or fact.get("metric") != "revenue"
            or fact.get("basis") != "gaap"
            or fact.get("typed_absence") is not None
        ):
            continue
        value = _decimal_text(fact.get("value"))
        unit = fact.get("unit")
        period = fact.get("period")
        source = _source_receipt(fact.get("source_span"))
        if (
            value is None
            or unit not in _UNIT_MAP
            or not isinstance(period, str)
            or not _DATE_RE.fullmatch(period)
            or source is None
        ):
            continue
        currency, scale = _UNIT_MAP[str(unit)]
        accepted.append({
            "fact_id": "fact_revenue_gaap",
            "metric": "revenue",
            "value": value,
            "unit": str(unit),
            "currency": currency,
            "amount_scale": scale,
            "period_end": period,
            "basis": "gaap",
            "source": source,
        })
        break
    return accepted


def _context_metrics(company_result: object) -> list[dict[str, str]]:
    if not isinstance(company_result, Mapping) or company_result.get("available") is not True:
        return []
    if company_result.get("authority") != AUTHORITY or company_result.get("is_context_only") is not True:
        return []
    event = company_result.get("latest_event")
    if not isinstance(event, Mapping):
        return []
    metrics = event.get("metrics")
    lineage_root = event.get("field_lineage")
    lineage = lineage_root.get("metrics") if isinstance(lineage_root, Mapping) else None
    if not isinstance(metrics, Mapping) or not isinstance(lineage, Mapping):
        return []
    out: list[dict[str, str]] = []
    for name in _ALLOWED_CONTEXT_METRICS:
        value = _decimal_text(metrics.get(name))
        owner = _bounded_text(lineage.get(name), maximum=64)
        if value is None or owner is None:
            continue
        out.append({
            "metric": name,
            "value": value,
            "lineage": owner,
            "evidence_class": "context_metric_not_span_bound",
        })
    return out


def _readiness(*, has_exact_revenue: bool) -> dict[str, Any]:
    blockers = [
        (
            "current_revenue_period_duration_unavailable"
            if has_exact_revenue
            else "current_exact_revenue_unavailable"
        ),
        "prior_exact_revenue_unavailable",
        "exact_gross_margin_unavailable",
        "exact_operating_profit_inputs_unavailable",
        "cash_bridge_inputs_unavailable",
        "valuation_inputs_unavailable",
    ]
    return {
        "authority": "admission_only",
        "ready": False,
        "calculator_payload": None,
        "blockers": blockers,
        "next_evidence_needed": [
            (
                "Preserve the release figure's exact period label or equivalent duration "
                "in the event fact before any automatic comparable-period calculation."
            ),
            (
                "Resolve a prior event workspace and retain an exact byte-replayed GAAP "
                "revenue fact for the comparable period."
            ),
            (
                "Retain exact source-bound gross margin or gross profit and operating "
                "income/expense facts before computing a profit bridge."
            ),
            (
                "Retain exact cash-flow components (or a separately governed reported "
                "cash-flow contract) before computing operating-cash or cash-after-capex."
            ),
            (
                "Retain exact annual/per-share earnings and an explicitly sourced "
                "valuation assumption before any price comparison."
            ),
        ],
    }


def build_financial_evidence_readiness(
    *,
    workspace_result: object,
    company_result: object,
) -> dict[str, Any]:
    """Project existing reader output into a bounded evidence/readiness packet."""
    exact = _exact_revenue(workspace_result)
    context = _context_metrics(company_result)
    event = _event_payload(workspace_result)

    ticker = None
    for candidate in (
        workspace_result.get("ticker") if isinstance(workspace_result, Mapping) else None,
        company_result.get("ticker") if isinstance(company_result, Mapping) else None,
    ):
        if isinstance(candidate, str) and _TICKER_RE.fullmatch(candidate.strip().upper()):
            ticker = candidate.strip().upper()
            break

    if exact:
        status = "partial"
    elif context:
        status = "context_only"
    else:
        status = "unavailable"

    return {
        "schema": SCHEMA,
        "status": status,
        "authority": AUTHORITY,
        "ticker": ticker,
        "event": event,
        "exact_facts": exact,
        "context_metrics": context,
        "financial_bridge_readiness": _readiness(has_exact_revenue=bool(exact)),
        "limits": [
            "Exact facts require a public byte-replayed source span; typed absences remain absent.",
            "Context metrics are useful context but are not promoted to span-bound accounting facts.",
            "This packet does not infer period duration from a fiscal-quarter label.",
            "This packet creates no calculation, valuation conclusion, ranking, sizing, or execution authority.",
        ],
    }


def _invalid_request() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "invalid_request",
        "authority": AUTHORITY,
        "ticker": None,
        "event": {},
        "exact_facts": [],
        "context_metrics": [],
        "financial_bridge_readiness": _readiness(has_exact_revenue=False),
        "limits": [
            "Request refused before Company Intelligence reader access.",
        ],
    }


def _reader_functions():
    from engine.neuralweb.company_intelligence_reader import (  # noqa: PLC0415
        read_company_intelligence,
        read_current_event_workspace,
    )
    return read_current_event_workspace, read_company_intelligence


def read_financial_evidence_readiness(params: object) -> dict[str, Any]:
    """Read through incumbent Company Intelligence owners and project readiness."""
    if not isinstance(params, Mapping) or set(params) != {"ticker"}:
        return _invalid_request()
    raw = params.get("ticker")
    if not isinstance(raw, str):
        return _invalid_request()
    ticker = raw.strip().upper()
    if (
        not _TICKER_RE.fullmatch(ticker)
        or ".." in ticker
        or ticker.startswith((".", "-"))
        or ticker.endswith((".", "-"))
    ):
        return _invalid_request()

    current_reader, company_reader = _reader_functions()
    try:
        workspace = current_reader({"ticker": ticker})
    except Exception:  # noqa: BLE001 - source availability must not become exception text
        workspace = {"available": False, "ticker": ticker, "note": "workspace_reader_unavailable"}
    try:
        company = company_reader({"ticker": ticker})
    except Exception:  # noqa: BLE001
        company = {"available": False, "ticker": ticker, "note": "company_reader_unavailable"}
    return build_financial_evidence_readiness(
        workspace_result=workspace,
        company_result=company,
    )
