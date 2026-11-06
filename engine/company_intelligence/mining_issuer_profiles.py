"""Witness profiles for FCX and MP. Synthetic bodies only; no public enrollment.

Shape copied from the IssuerProfile seam, not imported from an unmerged branch:

* ``IssuerProfile`` / ``_no_guidance`` — ``issuer_profiles.py`` lines 151-177
* ``receipt_for_literal`` — ``issuer_profiles.py`` lines 46 and 361-371
  (reimplemented here; the private ``_literal_receipt`` helper is not imported)
* ``_fact_present`` / ``_fact_absent`` — ``issuer_profiles.py`` lines 319-358
  (reimplemented; ``TypedAbsence`` comes from ``documents.py``, not ``_absence``)
* issuer constructor shape — ``issuer_profiles.py`` lines 76-86
* ``fiscal_scope`` profile shape — ``pg_profile.py`` lines 103-128

Fiscal year-end and listing MIC have no admitted submissions receipt on this
ref, so those fields are ``TypedAbsence`` and no ``IssuerIdentity`` is minted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import math
import re
from typing import Any, Mapping, Sequence

from ..earnings_release.binding import BoundRelease, bind_release_document
from ..earnings_release.receipts import ReceiptError, SpanReceipt, receipt_for_literal
from ..fundamental_forensics.disclosure_diff import BlockKind
from .documents import TypedAbsence, text_span
from .event_workspace import IssuerRegistry
from .identity import IssuerIdentity, company_id_for_cik
from .issuer_profiles import IssuerProfile, _no_guidance
from .qa_exchange import RIGHTS_PROFILE, RIGHTS_PROFILES


# CIKs frozen from the commission and data/edgar/ticker_cik_ledger.json
# tickers map (FCX 831259, MP 1801368). Identity is code, not a runtime read.
FCX_CIK = "0000831259"
MP_CIK = "0001801368"
MINING_TICKERS = ("FCX", "MP")

# Domain contract names, MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md lines 15 and 157.
FCX_DISPLAY_NAME = "Freeport-McMoRan"
MP_DISPLAY_NAME = "MP Materials"
_REPORTING_CURRENCY = "USD"

ATTRIBUTION_BASES = frozenset({
    "gross",
    "consolidated",
    "attributable",
    "payable",
    "saleable",
})
FLOW_KINDS = frozenset({
    "production",
    "purchases",
    "inventory",
    "internal_transfer",
    "external_delivery",
})

_PRIVATE_RIGHTS = tuple(sorted(RIGHTS_PROFILES - {RIGHTS_PROFILE}))
if len(_PRIVATE_RIGHTS) != 1:
    raise ImportError(
        "the rights registry must carry exactly one non-public profile for mining witness facts"
    )
MINING_PRIVATE_RIGHTS_PROFILE = _PRIVATE_RIGHTS[0]

_QUARTER_MARKERS = ("quarter", "three months")
_HALF_MARKERS = ("six months", "nine months", "half-year", "half year", "first-half", "first half")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class WitnessMetric:
    metric: str
    selection_label: str
    row_label: str
    unit: str
    flow_kind: str | None = None


@dataclass(frozen=True)
class SourcedMiningIdentity:
    """Fields with an admitted source. Unsourced fields are typed absences."""

    ticker: str
    cik: str
    display_name: str
    reporting_currency: str
    company_id: str


def _metrics(*items: WitnessMetric) -> tuple[WitnessMetric, ...]:
    seen: set[str] = set()
    for item in items:
        if item.metric in seen:
            raise ValueError(f"duplicate witness metric {item.metric}")
        if item.flow_kind is not None and item.flow_kind not in FLOW_KINDS:
            raise ValueError(f"unknown flow kind {item.flow_kind}")
        seen.add(item.metric)
    return items


# Selection labels are the domain contract's selection_label strings.
FCX_METRICS = _metrics(
    WitnessMetric(
        "consolidated_copper_sales",
        "Consolidated copper sales row",
        "Consolidated copper sales",
        "million_recoverable_pounds",
        "external_delivery",
    ),
    WitnessMetric(
        "copper_unit_net_cash_cost",
        "Copper consolidated unit net cash cost row",
        "Copper consolidated unit net cash cost",
        "usd_per_pound",
    ),
    WitnessMetric(
        "idle_and_restoration_costs_excluded_from_unit_cost",
        "Idle and restoration costs excluded from unit cost note",
        "Idle and restoration costs excluded from unit cost",
        "usd",
    ),
    WitnessMetric(
        "copper_production_consolidated",
        "Consolidated copper production row",
        "Consolidated copper production",
        "million_pounds",
        "production",
    ),
    WitnessMetric(
        "morenci_copper_production",
        "Morenci copper production row",
        "Morenci copper production",
        "million_pounds",
        "production",
    ),
    WitnessMetric(
        "management_issued_copper_sales_estimate",
        "Second-quarter consolidated copper sales outlook",
        "Second-quarter consolidated copper sales outlook",
        "million_recoverable_pounds",
        "external_delivery",
    ),
    WitnessMetric(
        "management_issued_copper_unit_net_cash_cost_estimate",
        "Second-quarter consolidated copper unit net cash cost outlook",
        "Second-quarter consolidated copper unit net cash cost outlook",
        "usd_per_pound",
    ),
)
MP_METRICS = _metrics(
    WitnessMetric(
        "materials_revenue_including_intersegment_sales",
        "Materials segment revenue including intersegment sales",
        "Materials segment revenue including intersegment sales",
        "usd_thousands",
    ),
    WitnessMetric(
        "magnetics_precursor_revenue",
        "Magnetics revenue",
        "Magnetics revenue",
        "usd_thousands",
    ),
    WitnessMetric(
        "revenue_elimination",
        "Segment revenue elimination row",
        "Segment revenue elimination",
        "usd_thousands",
        "internal_transfer",
    ),
    WitnessMetric(
        "consolidated_revenue",
        "Segment revenue table total revenue row",
        "Total revenue",
        "usd_thousands",
        "external_delivery",
    ),
    WitnessMetric(
        "price_protection_income",
        "Price protection income line",
        "Price protection income",
        "usd_thousands",
    ),
    WitnessMetric(
        "gaap_net_loss",
        "Consolidated results GAAP net loss row",
        "GAAP net loss",
        "usd_thousands",
    ),
    WitnessMetric(
        "adjusted_ebitda",
        "Consolidated results adjusted EBITDA row",
        "Adjusted EBITDA",
        "usd_thousands",
    ),
    WitnessMetric(
        "ndpr_production",
        "Operating indicators NdPr production row",
        "NdPr production",
        "metric_tonnes",
        "production",
    ),
    WitnessMetric(
        "ndpr_sales",
        "Operating indicators NdPr sales row",
        "NdPr sales",
        "metric_tonnes",
        "external_delivery",
    ),
)
FLOW_KIND_BY_METRIC = {
    item.metric: item.flow_kind
    for item in (*FCX_METRICS, *MP_METRICS)
    if item.flow_kind is not None
}


def _sourced(ticker: str, cik: str, display_name: str) -> SourcedMiningIdentity:
    return SourcedMiningIdentity(
        ticker=ticker,
        cik=cik,
        display_name=display_name,
        reporting_currency=_REPORTING_CURRENCY,
        company_id=company_id_for_cik(cik),
    )


def fcx_sourced_identity() -> SourcedMiningIdentity:
    return _sourced("FCX", FCX_CIK, FCX_DISPLAY_NAME)


def mp_sourced_identity() -> SourcedMiningIdentity:
    return _sourced("MP", MP_CIK, MP_DISPLAY_NAME)


def _unsourced(ticker: str) -> tuple[TypedAbsence, ...]:
    return tuple(
        TypedAbsence(
            reason="missing_source",
            subject=f"{ticker}.{field}",
            detail="no admitted SEC submissions receipt for this field on this ref",
        )
        for field in ("fiscal_year_end_month", "listing_mic")
    )


def fcx_unsourced_identity() -> tuple[TypedAbsence, ...]:
    return _unsourced("FCX")


def mp_unsourced_identity() -> tuple[TypedAbsence, ...]:
    return _unsourced("MP")


def fcx_issuer() -> IssuerIdentity | None:
    """No identity object: fiscal year-end and listing MIC are typed absences."""
    if fcx_unsourced_identity():
        return None
    return None


def mp_issuer() -> IssuerIdentity | None:
    if mp_unsourced_identity():
        return None
    return None


def mining_private_registry() -> IssuerRegistry:
    """No guessed listing is enrolled. Public discovery is a different registry."""
    return IssuerRegistry(())


def _scope(value: Sequence[Any]) -> tuple[date, date, date, date]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 4:
        raise ValueError("fiscal_scope must contain four dates")
    dates = tuple(date.fromisoformat(item) if isinstance(item, str) else item for item in value)
    if not all(isinstance(item, date) for item in dates):
        raise ValueError("fiscal_scope must contain four dates")
    current_start, current_end, prior_start, prior_end = dates
    if not (current_start < current_end and prior_start < prior_end and prior_end < current_start):
        raise ValueError("fiscal_scope ordering is invalid")
    if not 89 <= (current_end - current_start).days <= 92 or not 89 <= (prior_end - prior_start).days <= 92:
        raise ValueError("fiscal_scope must identify quarters")
    if (current_start - prior_start).days not in {364, 365, 366}:
        raise ValueError("prior fiscal interval does not match current")
    return dates


def mining_profile_for_ticker(
    ticker: str,
    *,
    publication: str = "private",
    fiscal_scope: tuple[str, str, str, str] | None = None,
) -> IssuerProfile | None:
    if publication not in {"public", "private"}:
        raise ValueError("publication must be 'public' or 'private'")
    normalized = str(ticker or "").strip().upper()
    factory = _PROFILE_FACTORIES.get(normalized)
    if publication != "private" or factory is None:
        return None
    if fiscal_scope is None:
        raise ValueError("private mining profile requires fiscal_scope")
    return factory(fiscal_scope=fiscal_scope)


def parse_mining_literal(value: object, *, unit: str) -> float | None:
    """A source literal to a float. Parentheses and a leading minus are the sign.

    ``True`` and ``False`` are rejected before conversion: ``bool`` is an
    ``int`` subclass, so converting one would publish a number.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        return None
    if not str(unit or "").strip():
        return None
    text = value.strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    elif text.startswith("-"):
        negative = True
        text = text[1:].strip()
    text = text.replace(",", "").replace("$", "")
    if text.startswith("+"):
        text = text[1:]
    if _NUMBER_RE.fullmatch(text) is None:
        return None
    number = float(text)
    if not math.isfinite(number):
        return None
    if negative:
        number = -number
    if not math.isfinite(number):
        return None
    return number


def fact_id_for(*, event_id: str, metric: str, period: str, basis: str, reason: str = "") -> str:
    material = "\x1f".join((event_id, metric, period, basis, reason))
    return "fact_" + sha256(material.encode("utf-8")).hexdigest()[:24]


def fact_is_borrowed(row: Mapping[str, Any], *, event_id: str) -> bool:
    if row.get("event_id") != event_id:
        return True
    if "typed_absence" in row:
        expected = fact_id_for(
            event_id=event_id,
            metric=str(row.get("metric") or ""),
            period="",
            basis="",
            reason=str(row["typed_absence"].get("reason") or ""),
        )
    else:
        expected = fact_id_for(
            event_id=event_id,
            metric=str(row.get("metric") or ""),
            period=str(row.get("period") or ""),
            basis=str(row.get("basis") or ""),
        )
    return row.get("fact_id") != expected


def bind_witness_release(**kwargs: Any) -> BoundRelease:
    """The incumbent binder. This module does not mint a second one."""
    return bind_release_document(**kwargs)


def _cell_receipt(bound: BoundRelease, cell: Any) -> SpanReceipt | None:
    literal = str(cell.text or "").strip()
    if not literal:
        return None
    span = cell.source_span
    try:
        return receipt_for_literal(
            source=bound.source,
            source_sha256=bound.revision.source_sha256,
            search_start=span.char_start,
            search_end=span.char_end,
            literal=literal,
        )
    except ReceiptError:
        return None


def _span_payload(*, document_id: str, bound: BoundRelease, receipt: SpanReceipt) -> dict[str, Any]:
    span = text_span(
        document_id=document_id,
        document_version=1,
        body_sha256=bound.revision.source_sha256,
        segment_index=0,
        segment_text=bound.source,
        start_byte=receipt.byte_start,
        end_byte=receipt.byte_end,
        text=receipt.span_text,
        rights_profile=MINING_PRIVATE_RIGHTS_PROFILE,
    )
    return span.to_payload()


def _present(
    *,
    event_id: str,
    metric: str,
    value: float,
    unit: str,
    period: str,
    basis: str,
    document_id: str,
    bound: BoundRelease,
    receipt: SpanReceipt,
) -> dict[str, Any]:
    return {
        "schema": "event_fact.v1",
        "fact_id": fact_id_for(event_id=event_id, metric=metric, period=period, basis=basis),
        "event_id": event_id,
        "metric": metric,
        "value": value,
        "unit": unit,
        "period": period,
        "basis": basis,
        "source_span": _span_payload(document_id=document_id, bound=bound, receipt=receipt),
    }


def _absent(
    *,
    event_id: str,
    metric: str,
    reason: str,
    detail: str,
    document_id: str,
) -> dict[str, Any]:
    return {
        "schema": "event_fact.v1",
        "fact_id": fact_id_for(event_id=event_id, metric=metric, period="", basis="", reason=reason),
        "event_id": event_id,
        "metric": metric,
        "typed_absence": TypedAbsence(
            reason=reason,
            subject=metric,
            detail=detail,
            event_id=event_id,
            document_id=document_id or None,
        ).to_payload(),
    }


def _filing_joins(bound: BoundRelease) -> bool:
    """Join on the filing pair (CIK, accession), never on a date."""
    entity = str(getattr(bound.document, "entity_cik", "") or "").strip()
    document_accession = str(getattr(bound.document, "accession", "") or "").strip()
    if not entity.isdigit() or not document_accession:
        return False
    key = bound.revision.filing_key
    return (
        f"{int(entity):010d}" == f"{key.cik:010d}"
        and document_accession == str(key.accession)
    )


def _bytes_held(bound: BoundRelease) -> bool:
    source = bound.source
    if not isinstance(source, str) or not source:
        return False
    digest = sha256(source.encode("utf-8")).hexdigest()
    return digest == bound.revision.source_sha256


def _unique_index(cells: Sequence[Any], predicate) -> int | None:
    matches = [index for index, cell in enumerate(cells) if predicate(cell)]
    if len(matches) != 1:
        return None
    return matches[0]


def _table_after_heading(blocks: Sequence[Any], label: str) -> Any | None:
    want = label.casefold()
    seen = False
    found = None
    for block in blocks:
        kind = block.kind
        if kind is BlockKind.HEADING and str(block.text or "").strip().casefold() == want:
            if seen:
                return None
            seen = True
            continue
        if not seen:
            continue
        if kind is BlockKind.HEADING:
            break
        if kind is BlockKind.TABLE and block.table is not None and not getattr(block.table, "nested", False):
            if found is not None:
                return None
            found = block
    return found


def _is_quarter_header(text: str, current_end: date) -> bool:
    lowered = text.casefold()
    if current_end.isoformat() not in lowered:
        return False
    if any(marker in lowered for marker in _HALF_MARKERS):
        return False
    return any(marker in lowered for marker in _QUARTER_MARKERS)


def _one_metric(
    metric: WitnessMetric,
    *,
    bound: BoundRelease,
    document_id: str,
    event_id: str,
    current_end: date,
) -> dict[str, Any]:
    block = _table_after_heading(bound.document.blocks, metric.selection_label)
    if block is None or not block.table.rows:
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="no_span_addressable_evidence",
            detail=f"{metric.selection_label} is not a uniquely addressable table",
            document_id=document_id,
        )
    header = block.table.rows[0]
    period_at = _unique_index(header, lambda cell: _is_quarter_header(str(cell.text or ""), current_end))
    if period_at is None:
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="missing_period",
            detail="no single quarter column header names the fiscal scope end",
            document_id=document_id,
        )
    period = str(header[period_at].text or "").strip()
    basis_at = _unique_index(header, lambda cell: str(cell.text or "").strip().casefold() == "basis")
    unit_at = _unique_index(header, lambda cell: str(cell.text or "").strip().casefold() == "unit")
    wanted = metric.row_label.casefold()
    matched = [
        row for row in block.table.rows[1:]
        if any(str(cell.text or "").strip().casefold() == wanted for cell in row)
    ]
    if len(matched) != 1:
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="no_span_addressable_evidence",
            detail=f"{metric.row_label} is not a unique row",
            document_id=document_id,
        )
    row = matched[0]
    if basis_at is None or basis_at >= len(row):
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="missing_basis",
            detail="the row has no basis cell",
            document_id=document_id,
        )
    basis = str(row[basis_at].text or "").strip().casefold()
    if basis not in ATTRIBUTION_BASES:
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="missing_basis",
            detail="the basis cell is not one attribution-basis word",
            document_id=document_id,
        )
    if unit_at is None or unit_at >= len(row):
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="missing_units",
            detail="the row has no unit cell",
            document_id=document_id,
        )
    unit = str(row[unit_at].text or "").strip()
    if unit.casefold() != metric.unit.casefold():
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="missing_units",
            detail="the unit cell does not match the witness unit",
            document_id=document_id,
        )
    if period_at >= len(row):
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="no_span_addressable_evidence",
            detail="the quarter column is not on this row",
            document_id=document_id,
        )
    receipt = _cell_receipt(bound, row[period_at])
    if receipt is None:
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="no_span_addressable_evidence",
            detail="the quarter literal is not uniquely addressable in its cell",
            document_id=document_id,
        )
    value = parse_mining_literal(receipt.value_text, unit=unit)
    if type(value) is not float:
        return _absent(
            event_id=event_id,
            metric=metric.metric,
            reason="no_span_addressable_evidence",
            detail="the quarter literal is not a single finite number",
            document_id=document_id,
        )
    return _present(
        event_id=event_id,
        metric=metric.metric,
        value=value,
        unit=unit,
        period=period,
        basis=basis,
        document_id=document_id,
        bound=bound,
        receipt=receipt,
    )


def extract_witness_facts(
    definitions: tuple[WitnessMetric, ...],
    *,
    bound: BoundRelease | None,
    document_id: str,
    event_id: str,
    current_end: date,
) -> list[dict[str, Any]]:
    if not isinstance(bound, BoundRelease) or not _bytes_held(bound):
        return [
            _absent(
                event_id=event_id,
                metric=item.metric,
                reason="document_bytes_not_held",
                detail="the release body is not held",
                document_id=document_id,
            )
            for item in definitions
        ]
    if not _filing_joins(bound):
        return [
            _absent(
                event_id=event_id,
                metric=item.metric,
                reason="unjoinable_filing_identity",
                detail="the document CIK and accession do not join the filing key",
                document_id=document_id,
            )
            for item in definitions
        ]
    return [
        _one_metric(
            item,
            bound=bound,
            document_id=document_id,
            event_id=event_id,
            current_end=current_end,
        )
        for item in definitions
    ]


_NEXT_PERIOD_MARKERS = ("subsequent-quarter outlook", "next-period outlook")


def witness_guidance_refusal(
    bound: BoundRelease,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, str] | None:
    """W-C: prior estimate and actual, with no next-period forward figure.

    ``extract_guidance`` stays ``_no_guidance``. ``assess_management_sequence``
    is not called. The typed refusal is minted here because that projector is
    not on this ref.
    """
    present = {str(row.get("metric") or "") for row in rows if "value" in row}
    if "management_issued_copper_sales_estimate" not in present:
        return None
    if "consolidated_copper_sales" not in present:
        return None
    if not isinstance(bound, BoundRelease):
        return None
    text = str(bound.source or "").casefold()
    if any(marker in text for marker in _NEXT_PERIOD_MARKERS):
        return None
    return {"status": "unavailable", "reason": "projector_unbound"}


def _profile(ticker: str, definitions: tuple[WitnessMetric, ...], fiscal_scope: tuple[str, str, str, str]) -> IssuerProfile:
    current_end = _scope(fiscal_scope)[1]

    def extract(*, bound: BoundRelease | None = None, document_id: str = "", event_id: str = "", **_kwargs: Any) -> list[dict[str, Any]]:
        return extract_witness_facts(
            definitions,
            bound=bound,
            document_id=document_id,
            event_id=event_id,
            current_end=current_end,
        )

    return IssuerProfile(
        ticker=ticker,
        extract_release_facts=extract,
        extract_transcript_claims=lambda **_kwargs: [],
        extract_guidance=_no_guidance,
    )


def fcx_profile(*, fiscal_scope: tuple[str, str, str, str]) -> IssuerProfile:
    return _profile("FCX", FCX_METRICS, fiscal_scope)


def mp_profile(*, fiscal_scope: tuple[str, str, str, str]) -> IssuerProfile:
    return _profile("MP", MP_METRICS, fiscal_scope)


_PROFILE_FACTORIES = {
    "FCX": fcx_profile,
    "MP": mp_profile,
}
