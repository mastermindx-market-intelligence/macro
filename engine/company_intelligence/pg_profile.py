"""Private, source-scoped Procter & Gamble economic observations.

Prior PG EPS rows use the prior fiscal interval's ISO end date instead of the
generic ``prior_year_same_quarter`` label.  ``fiscal_scope`` supplies both
interval boundaries that ``FiscalPeriod`` lacks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import functools
import hashlib
import math
import re
from typing import Any, Sequence

from engine.fundamental_forensics.disclosure_diff import BlockKind, normalize_filing

from .documents import TypedAbsence, text_span
from .event_workspace import IssuerRegistry
from .identity import IssuerIdentity, ListingAlias, company_id_for_cik
from .issuer_profiles import IssuerProfile, _no_guidance
from .qa_exchange import RIGHTS_PROFILE, RIGHTS_PROFILES
from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import ReceiptError, SpanReceipt, receipt_for_literal


PG_CIK = "0000080424"
_PRIVATE_RIGHTS_PROFILES = tuple(sorted(RIGHTS_PROFILES - {RIGHTS_PROFILE}))
if len(_PRIVATE_RIGHTS_PROFILES) != 1:
    raise ImportError("the rights registry must carry exactly one non-public profile for PG private facts")
PG_PRIVATE_RIGHTS_PROFILE = _PRIVATE_RIGHTS_PROFILES[0]


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
    row_label: str | None = None
    column_label: str | None = None


PG_DEFINITIONS: tuple[PGDefinition, ...] = (
    PGDefinition("pg_reported_sales_growth_pct", "percent", "percent", "one", "reported_sales", "company", 91, "reported_sales", row_label="Total P&G", column_label="Net Sales Growth"),
    PGDefinition("pg_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "company", 91, "organic_sales", row_label="Total P&G", column_label="Organic Sales Growth"),
    PGDefinition("pg_total_volume_growth_pct", "percent", "percent", "one", "total_volume", "company", 91, "total_volume", row_label="Total P&G", column_label="Volume with Acquisitions & Divestitures"),
    PGDefinition("pg_organic_volume_growth_pct", "percent", "percent", "one", "organic_volume", "company", 91, "organic_volume", row_label="Total P&G", column_label="Volume Excluding Acquisitions & Divestitures"),
    PGDefinition("pg_price_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution", row_label="Total P&G", column_label="Price"),
    PGDefinition("pg_mix_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution", row_label="Total P&G", column_label="Mix"),
    PGDefinition("pg_fx_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution", row_label="Total P&G", column_label="Foreign Exchange"),
    PGDefinition("pg_other_contribution_pp", "percentage_points", "percentage_points", "one", "reported_growth_bridge", "company", 91, "growth_contribution", row_label="Total P&G", column_label="Other"),
    PGDefinition("pg_diluted_eps", "currency_per_share", "usd_per_share", "one", "gaap_diluted", "company", 91, "same_measure", "pg_prior_diluted_eps", row_label="Diluted Net Earnings per Common Share"),
    PGDefinition("pg_prior_diluted_eps", "currency_per_share", "usd_per_share", "one", "gaap_diluted", "company", 91, "same_measure", "pg_diluted_eps", row_label="Diluted Net Earnings per Common Share"),
    PGDefinition("pg_reported_eps_growth_pct", "percent", "percent", "one", "reported_eps_growth", "company", 91, "reported_eps"),
    PGDefinition("pg_core_eps", "currency_per_share", "usd_per_share", "one", "core_non_gaap", "company", 91, "same_measure", "pg_prior_core_eps", row_label="Core EPS"),
    PGDefinition("pg_prior_core_eps", "currency_per_share", "usd_per_share", "one", "core_non_gaap", "company", 91, "same_measure", "pg_core_eps", row_label="Core EPS"),
    PGDefinition("pg_core_eps_growth_pct", "percent", "percent", "one", "core_eps_growth", "company", 91, "core_eps"),
    PGDefinition("pg_core_reconciliation_context", "bounded_text", "text", "one", "core_non_gaap_reconciliation", "company", 91, "core_reconciliation", row_label="Core EPS"),
    PGDefinition("pg_beauty_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "beauty_segment", 91, "organic_sales", segment_scope="Beauty", row_label="Beauty"),
    PGDefinition("pg_grooming_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "grooming_segment", 91, "organic_sales", segment_scope="Grooming", row_label="Grooming"),
    PGDefinition("pg_health_care_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "health_care_segment", 91, "organic_sales", segment_scope="Health Care", row_label="Health Care"),
    PGDefinition("pg_fabric_home_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "fabric_home_segment", 91, "organic_sales", segment_scope="Fabric and Home Care", row_label="Fabric and Home Care"),
    PGDefinition("pg_baby_feminine_family_organic_sales_growth_pct", "percent", "percent", "one", "organic_sales", "baby_feminine_family_segment", 91, "organic_sales", segment_scope="Baby, Feminine and Family Care", row_label="Baby, Feminine and Family Care"),
)

PG_METRIC_KEYS = tuple(item.metric for item in PG_DEFINITIONS)
# The only observations a combined volume/mix drivers column can fold together (R39).
PG_COMBINED_VOLUME_MIX_METRICS = frozenset({"pg_total_volume_growth_pct", "pg_organic_volume_growth_pct", "pg_mix_contribution_pp"})
_FISCAL_YEAR_END_MONTH = 6
_QUARTER_ORDINALS = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}


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
_PERCENT_PATTERN = rf"^(?:\+?({_NUMBER})%|\(\+?({_NUMBER})\)%|\(\+?({_NUMBER})%\))$"
_CURRENCY_PATTERN = rf"^(?:\$?({_NUMBER})|\(\$?({_NUMBER})\))$"
_NEUTRAL_ZERO = re.compile(r"\bdash(?:es)?\s+(?:means|represent[sd]?)\s+zero\b", re.IGNORECASE)
_DASHES = frozenset({"-", "\u2014", "\u2013"})
_PLACEHOLDER_ACCESSION = "0000000000-00-000000"


@functools.lru_cache(maxsize=16)
def parse_release_blocks(source: str) -> tuple[Any, ...]:
    """The ONE parse of a release body (R36).

    The extractor binds through ``bind_release_document`` and the validator replays from the caller-held
    source text; both read these blocks, so a heading, table, or paragraph exists for one exactly when it
    exists for the other.  The accession is a placeholder: block spans do not depend on it.
    """
    document = normalize_filing(
        {
            "accession": _PLACEHOLDER_ACCESSION,
            "entity_cik": PG_CIK,
            "form": "8-K",
            "content": source,
            "filed_at": "",
            "report_date": "",
            "source_url": None,
            "content_type": "text/html",
        }
    )
    return tuple(document.blocks)


def _is_literal_cell(text: str) -> bool:
    """A metric literal: a dash, a percent, or a currency amount -- never a bare integer such as a year label (R37)."""
    literal = text.strip()
    return (
        literal in _DASHES
        or re.fullmatch(_PERCENT_PATTERN, literal) is not None
        or (re.fullmatch(_CURRENCY_PATTERN, literal) is not None and re.fullmatch(r"[0-9]+", literal) is None)
    )


def _header_band(rows: Sequence[Any]) -> int:
    """Depth of the header band: the leading rows with an empty label cell or no metric literal beyond it (R37)."""
    depth = 0
    for row in rows:
        if row and _normal(row[0].text) and any(_is_literal_cell(cell.text) for cell in row[1:]):
            break
        depth += 1
    return depth


def _column_headers(rows: Sequence[Any], depth: int, column: int) -> tuple[str, ...]:
    """Header forms of one column: the stacked band text first, then each band cell on its own (R37)."""
    cells = [
        rows[index][column].text.strip()
        for index in range(depth)
        if column < len(rows[index]) and rows[index][column].text.strip()
    ]
    return tuple(dict.fromkeys(form for form in (" ".join(cells), *cells) if form))


def _band_context(rows: Sequence[Any], depth: int, identity: tuple[int, int, date]) -> str | None:
    """Period context of a table's own header band (R37).

    Each band cell is classified on its own: a twelve-month label anywhere refuses the table ("annual"); a cell
    naming the admitted quarter makes the band in scope even beside a prior-period column ("scope"); a band that
    names periods and never the admitted quarter is "foreign"; a band with no period label at all is None.
    """
    verdicts = {period_context(cell.text, identity) for row in rows[:depth] for cell in row if cell.text.strip()}
    for verdict in ("annual", "scope", "foreign"):
        if verdict in verdicts:
            return verdict
    return None


def _char_span(source: str, start: int, end: int) -> tuple[int, int]:
    source_bytes = source.encode("utf-8")
    if not 0 <= start < end <= len(source_bytes):
        raise ValueError("location is outside the source")
    try:
        char_start = len(source_bytes[:start].decode("utf-8"))
        char_end = char_start + len(source_bytes[start:end].decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("table bytes are not UTF-8 aligned") from exc
    return char_start, char_end


def replay_table_layout(
    source: str, *, start: int, end: int, header_forms: Sequence[str] = (), identity: tuple[int, int, date] | None = None
) -> tuple[str, str, int]:
    """The ONE cell locator: the extractor confirms every located cell through it and the validator replays through it (R28).

    The byte location is resolved against the parsed blocks (R36); the table's period context comes from the
    same heading scan the extractor binds with (R27) and its column header from the same header band (R37).
    """
    char_start, char_end = _char_span(source, start, end)
    hit = None
    for block, _governing, context in _table_scan(parse_release_blocks(source), identity):
        for row_index, row in enumerate(block.table.rows):
            for column, cell in enumerate(row):
                if cell.source_span.char_start <= char_start and char_end <= cell.source_span.char_end:
                    hit = (block, context, row_index, column)
    if hit is None:
        raise ValueError("location is not a table cell")
    block, context, row_index, column = hit
    if context in _OUT_OF_SCOPE:
        raise ValueError("table is governed by a period outside the admitted fiscal quarter")
    rows = block.table.rows
    depth = _header_band(rows)
    if row_index < depth:
        raise ValueError("location is a header cell")
    if column < 1:
        raise ValueError("cell has no matching header")
    accepted = {_normal(form) for form in header_forms if form}
    header = next((form for form in _column_headers(rows, depth, column) if not accepted or _normal(form) in accepted), None)
    if header is None:
        raise ValueError("cell has no matching header")
    return rows[row_index][0].text.strip(), header, column


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
    return " ".join(value.replace("\xa0", " ").replace("&nbsp;", " ").casefold().split())


def _fiscal_identity(current_start: date, current_end: date) -> tuple[int, int]:
    fiscal_year = (
        current_end.year + 1
        if current_start.month > _FISCAL_YEAR_END_MONTH
        else current_end.year
    )
    quarter = (
        (current_start.month - (_FISCAL_YEAR_END_MONTH + 1)) % 12 // 3 + 1
    )
    return fiscal_year, quarter


def _long_date(value: date) -> str:
    return f"{value:%B} {value.day}, {value.year}"


_ANNUAL_QUALIFIER = re.compile(r"\btwelve[\s-]+months?\b|\byear ended\b|\bfull[\s-]+year\b|\bannual\b", re.IGNORECASE)
_FISCAL_YEAR_LABEL = re.compile(r"\bfiscal(?:\s+year)?\s+(20\d{2})\b|\bfy\s*(20\d{2})\b", re.IGNORECASE)
_QUARTER_WORD = re.compile(r"\b(first|second|third|fourth)\s+quarter\b", re.IGNORECASE)
_Q_FY = re.compile(r"\bq([1-4])\s*fy\s*(\d{4})\b", re.IGNORECASE)
_THREE_MONTHS = re.compile(r"\bthree months ended\s+([a-z]+\s+\d{1,2},\s*\d{4})", re.IGNORECASE)
_DRIVERS_YEARS = re.compile(r"\bnet sales change drivers\s+(\d{4})\s+vs\.?\s+(\d{4})\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(20\d{2})\b")
_ORDINAL_INDEX = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_OUT_OF_SCOPE = frozenset({"annual", "foreign"})


def visible_text(source: str) -> str:
    """Rendered body text as the release parser reads it (R29, R38).

    Comments, scripts, styles, hidden elements, templates, attribute values and head content are not document
    statements because the parser never emits a block for them; there is no second, regex-shaped reading.
    """
    parts: list[str] = []
    for block in parse_release_blocks(source):
        if getattr(block, "table", None) is not None:
            parts.extend(cell.text for row in block.table.rows for cell in row)
        else:
            parts.append(getattr(block, "text", "") or "")
    return " ".join(part for part in parts if part)


def neutral_zero_convention(source: str) -> bool:
    return _NEUTRAL_ZERO.search(visible_text(source)) is not None


def period_context(text: str, identity: tuple[int, int, date]) -> str | None:
    """Classify a heading, header band, or sentence against the admitted fiscal scope (R27).

    Returns ``"annual"`` for twelve-month / full-year forms and for a bare fiscal-year label that carries no
    quarter qualifier (R37), ``"scope"`` when the text names the admitted quarter, ``"foreign"`` when it names
    another quarter or year, and ``None`` when it carries no period information at all.
    """
    fiscal_year, quarter, current_end = identity
    normal = _normal(text)
    if _ANNUAL_QUALIFIER.search(normal):
        return "annual"
    verdict: str | None = None
    quarter_words = [_ORDINAL_INDEX[m.group(1)] for m in _QUARTER_WORD.finditer(normal)]
    if quarter_words:
        years = [int(item) for item in _YEAR.findall(normal)]
        verdict = "scope" if all(q == quarter for q in quarter_words) and all(y == fiscal_year for y in years) else "foreign"
    for m in _Q_FY.finditer(normal):
        ok = int(m.group(1)) == quarter and int(m.group(2)) == fiscal_year
        verdict = "foreign" if (not ok or verdict == "foreign") else "scope"
    for m in _THREE_MONTHS.finditer(normal):
        ok = _normal(m.group(1)) == _normal(_long_date(current_end))
        verdict = "foreign" if (not ok or verdict == "foreign") else "scope"
    m = _DRIVERS_YEARS.search(normal)
    if m and int(m.group(1)) != fiscal_year:
        verdict = "foreign"
    if verdict is None and _FISCAL_YEAR_LABEL.search(normal):
        return "annual"
    return verdict


def _is_heading(block: Any) -> bool:
    return getattr(block, "kind", None) is not None and block.kind.value == "heading"


_PURE_PERIOD_HEADING = re.compile(
    r"^(?:q[1-4]\s*fy\s*\d{4}|(?:first|second|third|fourth) quarter(?: fiscal(?: year)?)? \d{4}"
    r"|fiscal year \d{4} (?:first|second|third|fourth) quarter|(?:three|twelve) months ended [a-z]+ \d{1,2}, \d{4}"
    r"|(?:fiscal )?year ended [a-z]+ \d{1,2}, \d{4})$"
)


def _table_scan(
    blocks: Sequence[Any], identity: tuple[int, int, date] | None
) -> list[tuple[Any, tuple[str, ...], str | None]]:
    """Every table with its governing headings (the immediate heading and the enclosing topic heading) and its period context.

    A pure period label such as "Three Months Ended June 30, 2026" refines the context of the topic heading above it
    without replacing that topic; both are consumed by the table they govern (R27).  A table's own header band can
    only narrow the context: a band naming a twelve-month period or another quarter refuses the table (R37).
    """
    context: str | None = None
    immediate: str | None = None
    topic: str | None = None
    scanned: list[tuple[Any, tuple[str, ...], str | None]] = []
    for block in blocks:
        if _is_heading(block):
            immediate = getattr(block, "text", "")
            if not _PURE_PERIOD_HEADING.match(_normal(immediate)):
                topic = immediate
            verdict = period_context(immediate, identity) if identity is not None else None
            if verdict is not None:
                context = verdict
        elif getattr(block, "table", None) is not None:
            rows = block.table.rows
            band = _band_context(rows, _header_band(rows), identity) if identity is not None else None
            governing = tuple(dict.fromkeys(item for item in (immediate, topic) if item))
            scanned.append((block, governing, band if band in _OUT_OF_SCOPE else context))
            immediate = None
            topic = None
    return scanned


def document_period_verdict(blocks: Sequence[Any], identity: tuple[int, int, date]) -> str | None:
    """The document's own period identity (R35).

    ``"scope"`` when any heading or table header band names the admitted quarter, or a year-level drivers heading
    names the admitted fiscal year; ``"foreign"`` / ``"annual"`` when the document carries period signals and none
    of them is consistent with the admitted scope; ``None`` when it carries no period signal at all -- such a
    document binds by the admitted scope.
    """
    fiscal_year = identity[0]
    signals: set[str] = set()
    for block in blocks:
        if _is_heading(block):
            text = getattr(block, "text", "")
            years = _DRIVERS_YEARS.search(_normal(text))
            verdict = "scope" if years and int(years.group(1)) == fiscal_year else period_context(text, identity)
        elif getattr(block, "table", None) is not None:
            rows = block.table.rows
            verdict = _band_context(rows, _header_band(rows), identity)
        else:
            continue
        if verdict is not None:
            signals.add(verdict)
    for verdict in ("scope", "foreign", "annual"):
        if verdict in signals:
            return verdict
    return None


def _scope_period_forms(
    current_start: date, current_end: date, prior_end: date
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    fiscal_year, quarter = _fiscal_identity(current_start, current_end)
    ordinal = _QUARTER_ORDINALS[quarter]
    current_date = _long_date(current_end)
    prior_date = _long_date(prior_end)
    quarterly_headings = (
        f"{ordinal} Quarter Fiscal Year {fiscal_year}",
        f"{ordinal} Quarter {fiscal_year}",
        f"Fiscal Year {fiscal_year} {ordinal} Quarter",
        f"{ordinal} Quarter Fiscal {fiscal_year}",
        f"Q{quarter} FY{fiscal_year}",
        f"Three Months Ended {current_date}",
    )
    driver_headings = (
        f"Net Sales Change Drivers {fiscal_year} vs. {fiscal_year - 1}",
        *quarterly_headings,
    )
    current_forms = (
        current_end.isoformat(),
        str(current_end.year),
        f"Q{quarter} FY{fiscal_year}",
        current_date,
        f"Three Months Ended {current_date}",
    )
    prior_forms = (
        prior_end.isoformat(),
        str(prior_end.year),
        f"Q{quarter} FY{fiscal_year - 1}",
        prior_date,
        f"Three Months Ended {prior_date}",
    )
    return quarterly_headings, driver_headings, current_forms, prior_forms


def _heading_matches(value: str, forms: Sequence[str]) -> bool:
    normal = _normal(value)
    return any(
        normal == _normal(form) or normal.startswith(f"{_normal(form)} ")
        for form in forms
    )


def _keyword_tables(blocks: Sequence[Any], *, keywords: Sequence[str], identity: tuple[int, int, date]) -> list[Any]:
    return [
        block
        for block, governing, context in _table_scan(blocks, identity)
        if context not in _OUT_OF_SCOPE
        and any(all(_normal(keyword) in _normal(heading) for keyword in keywords) for heading in governing)
    ]


def _drivers_tables(blocks: Sequence[Any], heading: str, *, identity: tuple[int, int, date]) -> list[Any]:
    return _keyword_tables(blocks, keywords=(_normal(heading),), identity=identity)


def _quarterly_tables(blocks: Sequence[Any], headings: Sequence[str], *, identity: tuple[int, int, date]) -> list[Any]:
    return [
        block
        for block, governing, context in _table_scan(blocks, identity)
        if context not in _OUT_OF_SCOPE and any(_heading_matches(heading, headings) for heading in governing)
    ]


def _band_width(rows: Sequence[Any], depth: int) -> int:
    return max((len(row) for row in rows[:depth]), default=0)


def _combined_presentation(table: Any) -> bool:
    """True when the table's header band carries a combined Volume/Mix column (R39)."""
    rows = table.table.rows
    depth = _header_band(rows)
    return any(
        forms and _normal(forms[0]).startswith("volume/mix")
        for forms in (_column_headers(rows, depth, column) for column in range(1, _band_width(rows, depth)))
    )


def combined_volume_mix_presentation(source: str, *, current_start: date, current_end: date, prior_end: date) -> bool:
    """Whether the ONE in-scope drivers table of ``source`` presents volume and mix as a combined column (R39)."""
    fiscal_year, quarter = _fiscal_identity(current_start, current_end)
    _quarterly, driver_headings, _current, _prior = _scope_period_forms(current_start, current_end, prior_end)
    tables = _drivers_tables(parse_release_blocks(source), driver_headings[0], identity=(fiscal_year, quarter, current_end))
    return len(tables) == 1 and _combined_presentation(tables[0])


def _column(table: Any, row_label: str, headers: Sequence[str]) -> tuple[Any, int, str] | None:
    """The unique (row, column, header form) a row label and an accepted header form address in ``table`` (R37).

    The header form returned is the first band form of that column in band order, exactly as
    ``replay_table_layout`` reports it, so the extractor and the validator name the same header.
    """
    if table is None:
        return None
    rows = table.table.rows
    depth = _header_band(rows)
    accepted = {_normal(header) for header in headers if header}
    row_matches = [item for item in rows[depth:] if item and _normal(item[0].text) == _normal(row_label)]
    columns = [
        (column, form)
        for column in range(1, _band_width(rows, depth))
        if (form := next((item for item in _column_headers(rows, depth, column) if _normal(item) in accepted), None)) is not None
    ]
    if len(row_matches) != 1 or len(columns) != 1 or columns[0][0] >= len(row_matches[0]):
        return None
    return row_matches[0], columns[0][0], columns[0][1]


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
    identity = "|".join((event_id, definition.metric, period, definition.basis))
    fact_digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return {
        "schema": "event_fact.v1",
        "fact_id": f"fact_{fact_digest}",
        "event_id": event_id,
        "metric": definition.metric,
        "value": value,
        "unit": definition.unit,
        "period": period,
        "basis": definition.basis,
        "source_span": _span(document_id, bound, receipt),
    }


def _absent(
    *,
    definition: PGDefinition,
    document_id: str,
    event_id: str,
    detail: str,
    reason: str = "no_span_addressable_evidence",
    subject: str | None = None,
) -> dict[str, Any]:
    identity = "|".join((event_id, definition.metric, definition.metric, definition.basis))
    fact_digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return {
        "schema": "event_fact.v1",
        "fact_id": f"fact_{fact_digest}",
        "event_id": event_id,
        "metric": definition.metric,
        "typed_absence": TypedAbsence(
            reason=reason,
            subject=subject or definition.metric,
            detail=detail,
            event_id=event_id,
            document_id=document_id,
        ).to_payload(),
    }


def _row_fact(*, definition: PGDefinition, blocks: Sequence[Any], headings: Sequence[str], header_forms: Sequence[str], document_id: str, bound: BoundRelease, event_id: str, periods: dict[str, str], preferred_period: str, identity: tuple[int, int, date]) -> dict[str, Any]:
    if len(headings) == 1 and len(_normal(headings[0]).split()) == 1:
        tables = _keyword_tables(blocks, keywords=(_normal(headings[0]),), identity=identity)
    elif _normal(headings[0]).startswith("net sales change drivers"):
        tables = _drivers_tables(blocks, headings[0], identity=identity)
    else:
        tables = _quarterly_tables(blocks, headings, identity=identity)
    row_label = definition.row_label or header_forms[0]
    headers = [definition.column_label] if definition.column_label else list(header_forms)
    # Exactly ONE (table, row, column) across every in-scope candidate table may address the observation;
    # a second addressable table is ambiguity, never a first-match fallback (R27, R36).
    located = [(table, *found) for table in tables if (found := _column(table, row_label, headers)) is not None]
    combined = definition.metric in PG_COMBINED_VOLUME_MIX_METRICS and any(_combined_presentation(table) for table in tables)
    if len(located) != 1:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            subject=f"{definition.metric} combined volume/mix" if combined else definition.metric,
            detail="The combined volume/mix presentation does not separately disclose this observation." if combined else "No unique heading, row label, and column header identifies this observation.",
        )
    table, row, column, matched_header = located[0]
    period = periods.get(matched_header, preferred_period)
    cell = row[column]
    literal = cell.text.strip()
    is_dash = literal in _DASHES
    if is_dash and not neutral_zero_convention(bound.source):
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="A dash has no explicit neutral-zero convention.")
    if not literal:
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    value: float | None = 0.0 if is_dash else parse_pg_literal(literal, unit=definition.unit)
    if value is None:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The cell literal does not match the definition unit.",
            reason="unit_mismatch",
        )
    receipt = _receipt(bound, cell.source_span.char_start, cell.source_span.char_end, literal)
    if receipt is None or not math.isfinite(value):
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    try:
        replayed_row, replayed_header, _column_index = replay_table_layout(
            bound.source, start=receipt.byte_start, end=receipt.byte_end, header_forms=headers, identity=identity
        )
    except ValueError:
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    if _normal(replayed_row) != _normal(row_label) or _normal(replayed_header) != _normal(matched_header):
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    if definition.metric == "pg_total_volume_growth_pct" and not _volume_cross_check(blocks, value=value, identity=identity, skip=table):
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The document carries conflicting statements of total volume growth.",
            reason="cross_check_conflict",
        )
    return _present(definition=definition, value=value, document_id=document_id, bound=bound, receipt=receipt, event_id=event_id, period=period)


# "volume" as the total-volume measure: not "organic volume", not "volume excluding ...", not "volume/mix" (R40).
_VOLUME_TERM = r"(?<!organic )\bvolume\b(?!\s*/\s*mix\b|\s+excluding\b|\s+mix\b)"
_VOLUME_SENTENCE = re.compile(
    rf"(?:\btotal p&g\b[^.]{{0,80}}?{_VOLUME_TERM}|{_VOLUME_TERM}[^.]{{0,40}}?\b(?:for|of|at)\s+total p&g\b)[^.]{{0,40}}?"
    r"\b(increased|grew|rose|was up|up|decreased|declined|fell|was down|down)\b[^.%]{0,24}?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_VOLUME_DECREASE = {"decreased", "declined", "fell", "was down", "down"}
_PRIOR_PERIOD_WORDS = ("prior", "previous", "year-ago", "year ago", "last year", "a year earlier")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_VOLUME_COLUMN_QUALIFIERS = ("excluding", "organic", "mix")


def _volume_statements(blocks: Sequence[Any], *, identity: tuple[int, int, date], skip: Any) -> list[float]:
    """Every same-period statement of Total P&G volume growth other than the bound drivers cell (R32).

    Tables are read through the same scan and header band as the bound cell (R37): a column counts only when its
    stacked header names volume without an organic / excluding / mix qualifier, and the Total P&G row may sit
    anywhere below the band.  A sentence counts only when it names Total P&G and the total-volume measure with
    no prior-period or out-of-scope qualifier (R40).
    """
    statements: list[float] = []
    for block, _governing, context in _table_scan(blocks, identity):
        if block is skip or context in _OUT_OF_SCOPE:
            continue
        rows = block.table.rows
        depth = _header_band(rows)
        for row in rows[depth:]:
            if not row or _normal(row[0].text) != "total p&g":
                continue
            for column in range(1, len(row)):
                forms = _column_headers(rows, depth, column)
                header = _normal(forms[0]) if forms else ""
                if "volume" not in header or any(word in header for word in _VOLUME_COLUMN_QUALIFIERS):
                    continue
                statement = parse_pg_literal(row[column].text, unit="percent")
                if statement is not None:
                    statements.append(statement)
    context = None
    for block in blocks:
        if _is_heading(block):
            verdict = period_context(getattr(block, "text", ""), identity)
            if verdict is not None:
                context = verdict
        elif context not in _OUT_OF_SCOPE and getattr(block, "kind", None) is not None and block.kind.value == BlockKind.PARAGRAPH.value:
            for sentence in _SENTENCE_SPLIT.split(_normal(getattr(block, "text", ""))):
                if period_context(sentence, identity) in _OUT_OF_SCOPE:
                    continue
                for match in _VOLUME_SENTENCE.finditer(sentence):
                    # "In the prior-year quarter, Total P&G volume increased 7%" is a prior-period statement;
                    # "Total P&G volume increased 4% versus the prior year period" is a same-period statement
                    # with a comparison basis: only a qualifier BEFORE the verb scopes the statement (R40).
                    head = sentence[: match.start(1)]
                    if any(word in head for word in _PRIOR_PERIOD_WORDS):
                        continue
                    magnitude = float(match.group(2))
                    statements.append(-magnitude if match.group(1) in _VOLUME_DECREASE else magnitude)
    return statements


def _volume_cross_check(blocks: Sequence[Any], *, value: float, identity: tuple[int, int, date], skip: Any) -> bool:
    return all(statement == value for statement in _volume_statements(blocks, identity=identity, skip=skip))


def _text_fact(
    *,
    definition: PGDefinition,
    blocks: Sequence[Any],
    document_id: str,
    bound: BoundRelease,
    event_id: str,
    period: str,
    identity: tuple[int, int, date],
) -> dict[str, Any]:
    active = False
    context: str | None = None
    paragraphs = []
    for block in blocks:
        if getattr(block, "kind", None) is not None and block.kind.value == "heading":
            normal = _normal(getattr(block, "text", ""))
            metric_name = _normal(definition.row_label or "")
            active = "reconciliation" in normal and metric_name in normal or "non-gaap" in normal
            verdict = period_context(normal, identity)
            if verdict is not None:
                context = verdict
        # A reconciliation paragraph carried under another quarter's heading is that quarter's statement (R35);
        # a twelve-month heading does not refuse it, because a Q4 release's non-GAAP section covers both periods.
        elif active and context != "foreign" and block.kind.value == BlockKind.PARAGRAPH.value:
            normal = _normal(block.text)
            if _normal(definition.row_label or "") in normal:
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
    if fiscal_period.calendar_end != current_end:
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The source fiscal period does not match the admitted fiscal scope.") for item in PG_DEFINITIONS]
    blocks = bound.document.blocks
    fiscal_year, quarter = _fiscal_identity(_current_start, current_end)
    identity = (fiscal_year, quarter, current_end)
    if (str(getattr(fiscal_period, "year", None)), str(getattr(fiscal_period, "quarter", None))) != (str(fiscal_year), str(quarter)):
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The workspace fiscal identity does not match the admitted fiscal scope.") for item in PG_DEFINITIONS]
    if document_period_verdict(blocks, identity) in _OUT_OF_SCOPE:
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The document's period signals do not name the admitted fiscal quarter.") for item in PG_DEFINITIONS]
    quarterly_headings, driver_headings, current_forms, prior_forms = _scope_period_forms(
        _current_start, current_end, prior_end
    )
    periods = {form: endpoint.isoformat() for forms, endpoint in ((current_forms, current_end), (prior_forms, prior_end)) for form in forms}
    facts = []
    for definition in PG_DEFINITIONS:
        if definition.metric in {
            "pg_diluted_eps", "pg_prior_diluted_eps", "pg_core_eps", "pg_prior_core_eps",
        }:
            forms = current_forms if definition.metric.startswith("pg_diluted") or definition.metric.startswith("pg_core") and "prior" not in definition.metric else prior_forms
            if definition.metric in {"pg_prior_diluted_eps", "pg_prior_core_eps"}:
                forms = prior_forms
            facts.append(_row_fact(definition=definition, blocks=blocks, headings=quarterly_headings, header_forms=forms, document_id=document_id, bound=bound, event_id=event_id, periods=periods, preferred_period=periods[forms[0]], identity=identity))
        elif definition.row_label is not None and definition.column_label is not None:
            facts.append(_row_fact(definition=definition, blocks=blocks, headings=(driver_headings[0],), header_forms=current_forms, document_id=document_id, bound=bound, event_id=event_id, periods=periods, preferred_period=current_end.isoformat(), identity=identity))
        elif definition.metric.endswith("_organic_sales_growth_pct") and definition.row_label is not None:
            facts.append(_row_fact(definition=definition, blocks=blocks, headings=("Segment",), header_forms=current_forms, document_id=document_id, bound=bound, event_id=event_id, periods=periods, preferred_period=current_end.isoformat(), identity=identity))
        elif definition.metric == "pg_core_reconciliation_context":
            facts.append(_text_fact(definition=definition, blocks=blocks, document_id=document_id, bound=bound, event_id=event_id, period=current_end.isoformat(), identity=identity))
        else:
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, detail="This literal growth fact is not separately disclosed by the selected source."))
    return facts


__all__ = ["PG_COMBINED_VOLUME_MIX_METRICS", "PG_DEFINITIONS", "PG_METRIC_KEYS", "combined_volume_mix_presentation", "document_period_verdict", "extract_pg_release_facts", "neutral_zero_convention", "parse_release_blocks", "period_context", "pg_issuer", "pg_private_registry", "pg_profile", "replay_table_layout", "visible_text"]
