"""Private, source-scoped Procter & Gamble economic observations.

Prior PG EPS rows use the prior fiscal interval's ISO end date instead of the
generic ``prior_year_same_quarter`` label.  ``fiscal_scope`` supplies both
interval boundaries that ``FiscalPeriod`` lacks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
import re
from typing import Any, Sequence

from engine.fundamental_forensics.disclosure_diff import BlockKind

from .documents import TypedAbsence, text_span
from .event_workspace import IssuerRegistry
from .identity import IssuerIdentity, ListingAlias, company_id_for_cik
from .issuer_profiles import IssuerProfile, _no_guidance
from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import ReceiptError, SpanReceipt, receipt_for_literal


PG_CIK = "0000080424"
PG_PRIVATE_RIGHTS_PROFILE = "rp_internal_private_v1"


@dataclass(frozen=True)
class PGDefinition:
    metric: str
    value_kind: str
    unit: str
    scale: str
    basis: str
    scope: str
    quarter_duration: int
    comparison_family: str
    paired_metric: str | None = None
    segment_scope: str | None = None


PG_DEFINITIONS: tuple[PGDefinition, ...] = (
    PGDefinition("pg_reported_sales_growth_pct", "percent", "percent", "one", "reported_sales", "company", 91, "reported_sales"),
    PGDefinition("pg_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "company", 91, "organic_sales"),
    PGDefinition("pg_total_volume_growth_pct", "percent", "percent", "one", "total_volume", "company", 91, "total_volume"),
    PGDefinition("pg_organic_volume_growth_pct", "percent", "percent", "one", "organic_volume", "company", 91, "organic_volume"),
    PGDefinition("pg_price_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution"),
    PGDefinition("pg_mix_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution"),
    PGDefinition("pg_fx_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution"),
    PGDefinition("pg_other_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution"),
    PGDefinition("pg_diluted_eps", "currency_per_share", "usd_per_share", "one", "gaap_diluted", "company", 91, "same_measure", "pg_prior_diluted_eps"),
    PGDefinition("pg_prior_diluted_eps", "currency_per_share", "usd_per_share", "one", "gaap_diluted", "company", 91, "same_measure", "pg_diluted_eps"),
    PGDefinition("pg_reported_eps_growth_pct", "percent", "percent", "one", "reported_eps_growth", "company", 91, "reported_eps"),
    PGDefinition("pg_core_eps", "currency_per_share", "usd_per_share", "one", "core_non_gaap", "company", 91, "same_measure", "pg_prior_core_eps"),
    PGDefinition("pg_prior_core_eps", "currency_per_share", "usd_per_share", "one", "core_non_gaap", "company", 91, "same_measure", "pg_core_eps"),
    PGDefinition("pg_core_eps_growth_pct", "percent", "percent", "one", "core_eps_growth", "company", 91, "core_eps"),
    PGDefinition("pg_core_reconciliation_context", "bounded_text", "text", "one", "core_non_gaap_reconciliation", "company", 91, "core_reconciliation"),
    PGDefinition("pg_beauty_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "beauty_segment", 91, "organic_sales", segment_scope="Beauty"),
    PGDefinition("pg_grooming_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "grooming_segment", 91, "organic_sales", segment_scope="Grooming"),
    PGDefinition("pg_health_care_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "health_care_segment", 91, "organic_sales", segment_scope="Health Care"),
    PGDefinition("pg_fabric_home_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "fabric_home_segment", 91, "organic_sales", segment_scope="Fabric and Home Care"),
    PGDefinition("pg_baby_feminine_family_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "baby_feminine_family_segment", 91, "organic_sales", segment_scope="Baby, Feminine and Family Care"),
)
PG_METRIC_KEYS = tuple(item.metric for item in PG_DEFINITIONS)


def pg_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(PG_CIK),
        display_name="Procter & Gamble Co.",
        fiscal_year_end_month=6,
        reporting_currency="USD",
        listings=(ListingAlias(ticker="PG", mic="XNYS", share_class="common", trading_currency="USD", is_primary=True),),
        external_ids={"cik": PG_CIK},
    )


def pg_private_registry() -> IssuerRegistry:
    return IssuerRegistry([pg_issuer()])


def _scope(value: Sequence[Any]) -> tuple[date, date, date, date]:
    if not isinstance(value, Sequence) or len(value) != 4:
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


def pg_profile(*, fiscal_scope: tuple[str, str, str, str]) -> IssuerProfile:
    scope = _scope(fiscal_scope)
    def extract(**kwargs: Any) -> list[dict[str, Any]]:
        return extract_pg_release_facts(**kwargs, fiscal_scope=scope)
    return IssuerProfile(
        ticker="PG",
        extract_release_facts=extract,
        extract_transcript_claims=lambda **_kwargs: [],
        extract_guidance=_no_guidance,
    )


_NUMBER = r"[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?"
_PERCENT_PATTERN = rf"^(?:\(?\+?({_NUMBER})%\)?|\(?\+?({_NUMBER})\)?%)$"
_CURRENCY_PATTERN = rf"^(?:\$?({_NUMBER})|\(\$?({_NUMBER})\))$"


def parse_pg_literal(value: str, *, unit: str) -> float | None:
    literal = value.strip()
    if unit in {"percent", "percentage_points"}:
        match = re.fullmatch(_PERCENT_PATTERN, literal)
        negative = literal.startswith("(")
        groups = match.groups() if match else ()
    elif unit == "usd_per_share":
        match = re.fullmatch(_CURRENCY_PATTERN, literal)
        negative = literal.startswith("(")
        groups = match.groups() if match else ()
    else:
        return None
    if not match or not any(groups):
        return None
    number = float(next(item.replace(",", "") for item in groups if item is not None))
    value_number = -number if negative else number
    return value_number if math.isfinite(value_number) else None


def _normal(value: str) -> str:
    return " ".join(value.casefold().split())


def _table(blocks: Sequence[Any], heading: str) -> Any | None:
    active = False
    matches = []
    for block in blocks:
        if block.kind is BlockKind.HEADING:
            active = _normal(block.text) == _normal(heading)
        elif active and block.kind is BlockKind.TABLE and block.table is not None:
            matches.append(block)
    return matches[0] if len(matches) == 1 else None


def _column(table: Any, row_label: str, header: str) -> tuple[Any, int] | None:
    if table is None:
        return None
    rows = table.table.rows
    row_matches = [item for item in rows if item and _normal(item[0].text) == _normal(row_label)]
    header_cells = [
        (item, index)
        for item in rows
        for index, cell in enumerate(item)
        if _normal(cell.text) == _normal(header)
    ]
    if len(row_matches) != 1 or len(header_cells) != 1:
        return None
    row, (header_row, column) = row_matches[0], header_cells[0]
    if rows.index(header_row) >= rows.index(row) or column >= len(row):
        return None
    return row, column




def _receipt(source: BoundRelease, start: int, end: int, literal: str) -> SpanReceipt | None:
    try:
        return receipt_for_literal(
            source=source.source,
            source_sha256=source.revision.source_sha256,
            search_start=start,
            search_end=end,
            literal=literal,
        )
    except ReceiptError:
        return None


def _span(document_id: str, bound: BoundRelease, receipt: SpanReceipt) -> dict[str, Any]:
    return text_span(
        document_id=document_id,
        document_version=1,
        body_sha256=bound.revision.source_sha256,
        segment_index=0,
        segment_text=bound.source,
        start_byte=receipt.byte_start,
        end_byte=receipt.byte_end,
        text=receipt.span_text,
        rights_profile=PG_PRIVATE_RIGHTS_PROFILE,
    ).to_payload()


def _present(*, definition: PGDefinition, value: Any, document_id: str, bound: BoundRelease, receipt: SpanReceipt, event_id: str, period: str) -> dict[str, Any]:
    return {
        "schema": "event_fact.v1",
        "fact_id": f"fact_{definition.metric}",
        "event_id": event_id,
        "metric": definition.metric,
        "value": value,
        "unit": definition.unit,
        "period": period,
        "basis": definition.basis,
        "source_span": _span(document_id, bound, receipt),
    }


def _absent(
    *, definition: PGDefinition, document_id: str, event_id: str, detail: str, reason: str = "no_span_addressable_evidence"
) -> dict[str, Any]:
    return {
        "schema": "event_fact.v1",
        "fact_id": f"fact_{definition.metric}",
        "event_id": event_id,
        "metric": definition.metric,
        "typed_absence": TypedAbsence(
            reason=reason,
            subject=definition.metric,
            detail=detail,
            event_id=event_id,
            document_id=document_id,
        ).to_payload(),
    }


def _row_fact(*, definition: PGDefinition, blocks: Sequence[Any], heading: str, row_label: str, header: str, document_id: str, bound: BoundRelease, event_id: str, period: str) -> dict[str, Any]:
    table = _table(blocks, heading)
    located = _column(table, row_label, header)
    if located is None:
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="No unique heading, row label, and column header identifies this observation.")
    row, column = located
    cell = row[column]
    literal = cell.text.strip()
    value: float | None = None
    receipt: SpanReceipt | None = None
    if literal in {"-", "—", "–"}:
        neutral = _column(table, row_label, "Neutral convention")
        if neutral is None or _normal(neutral[0][neutral[1]].text) != "dash means zero":
            return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="A dash has no explicit neutral-zero convention.")
        value = 0.0
        receipt = _receipt(bound, cell.source_span.char_start, cell.source_span.char_end, literal)
    elif literal:
        value = parse_pg_literal(literal, unit=definition.unit)
        if value is None:
            return _absent(
                definition=definition,
                document_id=document_id,
                event_id=event_id,
                detail="The cell literal does not match the definition unit.",
                reason="missing_units",
            )
        receipt = _receipt(bound, cell.source_span.char_start, cell.source_span.char_end, literal)
    if value is None or not math.isfinite(value) or receipt is None:
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    return _present(definition=definition, value=value, document_id=document_id, bound=bound, receipt=receipt, event_id=event_id, period=period)


def _text_fact(
    *,
    definition: PGDefinition,
    blocks: Sequence[Any],
    heading: str,
    document_id: str,
    bound: BoundRelease,
    event_id: str,
    period: str,
) -> dict[str, Any]:
    active = False
    paragraphs = []
    for block in blocks:
        if block.kind is BlockKind.HEADING:
            active = _normal(block.text) == _normal(heading)
        elif active and block.kind is BlockKind.PARAGRAPH:
            normal = _normal(block.text)
            if all(term.casefold() in normal for term in ("core eps", "incremental charge", "dilution")):
                paragraphs.append(block)
    if len(paragraphs) != 1:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The reconciliation paragraph is not uniquely addressable under its heading.",
        )
    sentence = paragraphs[0].text.strip()
    receipt = _receipt(
        bound,
        paragraphs[0].source_span.char_start,
        paragraphs[0].source_span.char_end,
        sentence,
    )
    if receipt is None:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The reconciliation paragraph is not uniquely addressable in source bytes.",
        )
    return _present(
        definition=definition,
        value=sentence,
        document_id=document_id,
        bound=bound,
        receipt=receipt,
        event_id=event_id,
        period=period,
    )


def extract_pg_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, fiscal_period: Any, fiscal_scope: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    if fiscal_scope is None:
        raise ValueError("PG extraction requires fiscal_scope")
    _current_start, current_end, _prior_start, prior_end = _scope(fiscal_scope)
    current = current_end.isoformat()
    prior = prior_end.isoformat()
    if fiscal_period.calendar_end != current_end:
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The source fiscal period does not match the admitted fiscal scope.") for item in PG_DEFINITIONS]
    blocks = bound.document.blocks
    current_year = current_end.year
    prior_year = prior_end.year
    current_quarter = f"Fourth Quarter {current_year}"
    prior_quarter = f"Fourth Quarter {prior_year}"
    current_date = f"{current_end:%B} {current_end.day}, {current_end.year}"
    prior_date = prior_end.strftime("%B %#d, %Y")
    current_header = current_end.isoformat()
    prior_header = prior_end.isoformat()
    eps_rows = {
        "pg_diluted_eps": ("Diluted EPS", current_header),
        "pg_prior_diluted_eps": ("Prior Diluted EPS", prior_header),
        "pg_core_eps": ("Core EPS", current_header),
        "pg_prior_core_eps": ("Prior Core EPS", prior_header),
    }
    driver_headers = {
        "pg_reported_sales_growth_pct": "Reported sales growth percent",
        "pg_organic_sales_growth_pct": "Organic sales growth percent",
        "pg_total_volume_growth_pct": "Total volume growth percent",
        "pg_organic_volume_growth_pct": "Organic volume growth percent",
        "pg_price_contribution_pp": "Price contribution percent",
        "pg_mix_contribution_pp": "Mix contribution percent",
        "pg_fx_contribution_pp": "FX contribution percent",
        "pg_other_contribution_pp": "Other contribution percent",
    }
    segments = {
        "pg_beauty_organic_sales_growth_pct": "Beauty",
        "pg_grooming_organic_sales_growth_pct": "Grooming",
        "pg_health_care_organic_sales_growth_pct": "Health Care",
        "pg_fabric_home_organic_sales_growth_pct": "Fabric and Home Care",
        "pg_baby_feminine_family_organic_sales_growth_pct": "Baby, Feminine and Family Care",
    }
    facts = []
    for definition in PG_DEFINITIONS:
        if definition.metric in eps_rows:
            row_label, period_header = eps_rows[definition.metric]
            facts.append(
                _row_fact(
                    definition=definition,
                    blocks=blocks,
                    heading=f"Fourth Quarter {current_year} Results",
                    row_label=row_label,
                    header=period_header,
                    document_id=document_id,
                    bound=bound,
                    event_id=event_id,
                    period=period_header,
                )
            )
        elif definition.metric in driver_headers:
            volume = definition.metric in {
                "pg_total_volume_growth_pct", "pg_organic_volume_growth_pct",
            }
            facts.append(
                _row_fact(
                    definition=definition,
                    blocks=blocks,
                    heading=(
                        "Volume Conventions"
                        if volume
                        else f"Sales Drivers for the Quarter Ended {current_date}"
                    ),
                    row_label=(
                        driver_headers[definition.metric]
                        if volume
                        else current_header
                    ),
                    header=(
                        current_header
                        if volume
                        else driver_headers[definition.metric]
                    ),
                    document_id=document_id,
                    bound=bound,
                    event_id=event_id,
                    period=current_header,
                )
            )
        elif definition.metric in segments:
            facts.append(
                _row_fact(
                    definition=definition,
                    blocks=blocks,
                    heading="Segments",
                    row_label=segments[definition.metric],
                    header=current_header,
                    document_id=document_id,
                    bound=bound,
                    event_id=event_id,
                    period=current_header,
                )
            )
        elif definition.metric == "pg_core_reconciliation_context":
            facts.append(
                _text_fact(
                    definition=definition,
                    blocks=blocks,
                    heading="Core Reconciliation",
                    document_id=document_id,
                    bound=bound,
                    event_id=event_id,
                    period=current_header,
                )
            )
        else:
            facts.append(
                _absent(
                    definition=definition,
                    document_id=document_id,
                    event_id=event_id,
                    detail="This literal growth fact is not separately disclosed by the selected source.",
                )
            )
    return facts


__all__ = ["PG_DEFINITIONS", "PG_METRIC_KEYS", "extract_pg_release_facts", "pg_issuer", "pg_private_registry", "pg_profile"]
