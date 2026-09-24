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
import html
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
# A bounded-text observation is at most this many characters on BOTH sides of the contract (R45).
PG_BOUNDED_TEXT_MAX = 240
_EPS_METRICS = frozenset({"pg_diluted_eps", "pg_prior_diluted_eps", "pg_core_eps", "pg_prior_core_eps"})
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
# Period contexts that exclude a table, a column or a row section from binding.
_EXCLUDED = frozenset({"annual", "foreign", "unknown"})


@functools.lru_cache(maxsize=16)
def parse_release_blocks(source: str) -> tuple[Any, ...]:
    """The ONE parse of a release body (R36).

    The extractor and the validator both read these blocks from the same source text, so a heading, table,
    or paragraph exists for one exactly when it exists for the other.  The accession and form are
    placeholders: block kinds, texts and spans do not depend on them (section keys may, and are unused here).
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


@dataclass(frozen=True)
class _Cell:
    """One grid position of a table: the parser cell that occupies it (R49)."""

    text: str
    char_start: int
    char_end: int
    origin: Any


_EMPTY_CELL = _Cell("", 0, 0, None)


@dataclass(frozen=True)
class _Table:
    block: Any
    rows: tuple[tuple[_Cell, ...], ...]
    depth: int
    caption: str
    governing: tuple[str, ...]
    context: str | None
    row_context: tuple[str | None, ...]
    forward: bool = False


def _grid(block: Any) -> tuple[tuple[_Cell, ...], ...]:
    """The table as an occupancy grid from the parser's own colspan / rowspan facts (R49).

    A spanning cell occupies every position it covers; rows are padded to the grid width with empty
    placeholders so every row can be indexed by column.
    """
    emitted = list(block.table.rows)
    ordinals = [next((int(getattr(cell, "row_ordinal", -1)) for cell in row), -1) for row in emitted]
    if any(ordinal < 0 for ordinal in ordinals):
        ordinals = list(range(len(emitted)))
    by_ordinal: dict[int, list[Any]] = {}
    for ordinal, row in zip(ordinals, emitted):
        by_ordinal.setdefault(ordinal, []).extend(row)
    carried: dict[tuple[int, int], _Cell] = {}
    grid: list[list[_Cell]] = []
    group: int | None = None
    # Every HTML row exists, including one that emitted no cell: a rowspan from above occupies it (R49); a
    # rowspan never crosses a row group (thead / tbody / tfoot), exactly as HTML clips it (R61).
    for row_index in range(max(by_ordinal, default=-1) + 1):
        row = by_ordinal.get(row_index, [])
        row_group = next((int(getattr(cell, "row_group", 0)) for cell in row), group)
        if group is not None and row_group != group:
            carried = {}
        group = row_group
        line: list[_Cell] = []
        column = 0
        for cell in row:
            while (row_index, column) in carried:
                line.append(carried.pop((row_index, column)))
                column += 1
            span = getattr(cell, "source_span", None)
            item = _Cell(cell.text, getattr(span, "char_start", 0), getattr(span, "char_end", 0), cell)
            colspan = max(1, int(getattr(cell, "colspan", 1) or 1))
            rowspan = max(1, int(getattr(cell, "rowspan", 1) or 1))
            for offset in range(colspan):
                line.append(item)
                for below in range(1, rowspan):
                    carried[(row_index + below, column + offset)] = item
            column += colspan
        while (row_index, column) in carried:
            line.append(carried.pop((row_index, column)))
            column += 1
        grid.append(line)
    width = max((len(line) for line in grid), default=0)
    return tuple(tuple(line) + (_EMPTY_CELL,) * (width - len(line)) for line in grid)


def _is_literal_cell(text: str) -> bool:
    """A metric literal: a dash, a percent, or a currency amount -- never a bare integer such as a year label (R37)."""
    literal = text.strip()
    return (
        literal in _DASHES
        or re.fullmatch(_PERCENT_PATTERN, literal) is not None
        or (re.fullmatch(_CURRENCY_PATTERN, literal) is not None and re.fullmatch(r"[0-9]+", literal) is None)
    )


def _header_band(rows: Sequence[Sequence[_Cell]]) -> int:
    """Depth of the header band: the leading rows with an empty label cell or no metric literal beyond it (R37)."""
    depth = 0
    for row in rows:
        if row and _normal(row[0].text) and any(_is_literal_cell(cell.text) for cell in row[1:]):
            break
        depth += 1
    return depth


def _band_width(rows: Sequence[Sequence[_Cell]], depth: int) -> int:
    return max((len(row) for row in rows[:depth]), default=0)


def _column_header_cells(rows: Sequence[Sequence[_Cell]], depth: int, column: int) -> tuple[_Cell, ...]:
    """The distinct band cells stacked over one column; a cell spanning several band rows counts once (R49)."""
    cells: list[_Cell] = []
    seen: set[int] = set()
    for index in range(depth):
        if column < len(rows[index]):
            cell = rows[index][column]
            if cell.text.strip() and cell.origin is not None and id(cell.origin) not in seen:
                seen.add(id(cell.origin))
                cells.append(cell)
    return tuple(cells)


def _column_headers(rows: Sequence[Sequence[_Cell]], depth: int, column: int) -> tuple[str, ...]:
    """Header forms of one column: the stacked band text first, then each band cell on its own (R37)."""
    cells = [cell.text.strip() for cell in _column_header_cells(rows, depth, column)]
    return tuple(dict.fromkeys(form for form in (" ".join(cells), *cells) if form))


def _row_text(row: Sequence[_Cell]) -> str:
    """The distinct texts of a row in column order, each spanning cell once."""
    texts: dict[int, str] = {}
    for cell in row:
        if cell.text.strip() and cell.origin is not None:
            texts.setdefault(id(cell.origin), cell.text.strip())
    return " ".join(texts.values())


def _section_text(row: Sequence[_Cell]) -> str | None:
    """A row that carries no metric literal is a label row -- one cell or several, in any column, at any colspan --
    and its whole text is what names a section (R51, R57, R62); a row holding a literal is a data row."""
    if not row or any(_is_literal_cell(cell.text) for cell in row):
        return None
    return _row_text(row)


# Markers that open a period FORM ("... ended <date>", "<n> months", "FY..", "fiscal ..."): a bare "Quarter" band
# cell over a readable period stack is a caption word, not a second period (r19c).
_RESIDUAL_MARKER = re.compile(r"\b(?:ended|ending|months?|ytd|fiscal|fy)\b", re.IGNORECASE)


def _residual_marker(normal: str) -> bool:
    """True when the text still carries a period-form marker after every recognised period form is removed (R62)."""
    residual = normal
    for pattern in (_ANNUAL_QUALIFIER, _QUARTER_ENDED, _Q_FY, _DRIVERS_YEARS, _FISCAL_YEAR_LABEL, _QUARTER_WORD):
        residual = pattern.sub(" ", residual)
    return _RESIDUAL_MARKER.search(residual) is not None


def _marked_context(text: str, identity: tuple[int, int, date]) -> str | None:
    """``period_context`` made fail-closed (R50, R55, R62): text carrying a period marker that resolves to no
    known form is "unknown", and so is text that names the admitted quarter BESIDE a marker that resolves to
    nothing ("Three Months Ended June 30, 2026 vs. Quarter Ended 31/03/2026"); unknown refuses exactly as an
    annual label does."""
    verdict = period_context(text, identity)
    if verdict in {None, "scope"} and _residual_marker(_normal(text)):
        return "unknown"
    return verdict


def _band_context(rows: Sequence[Sequence[_Cell]], depth: int, caption: str, identity: tuple[int, int, date]) -> str | None:
    """Period context of a table's own header band (R37, R43, R50).

    The caption, every label-column band cell and every value column's stacked band text are classified:
    a twelve-month or cumulative label anywhere refuses the table ("annual"); a column whose stack carries a
    period marker that does not resolve to any known form is "unknown" and refuses it too; a column naming
    the admitted quarter keeps the band in scope beside a prior-period column ("scope"); a band that names
    periods and never the admitted quarter is "foreign"; a band with no period label at all is None.
    """
    verdicts: set[str | None] = set()
    labels: dict[int, str] = {}
    for row in rows[:depth]:
        if row and row[0].origin is not None and row[0].text.strip():
            labels.setdefault(id(row[0].origin), row[0].text)
    for text in (caption, *labels.values()):
        if text.strip():
            verdicts.add(_marked_context(text, identity))
    for column in range(1, _band_width(rows, depth)):
        stacked = " ".join(cell.text.strip() for cell in _column_header_cells(rows, depth, column))
        if stacked.strip():
            verdicts.add(_marked_context(stacked, identity))
    for verdict in ("annual", "unknown", "scope", "foreign"):
        if verdict in verdicts:
            return verdict
    return None


def _row_contexts(rows: Sequence[Sequence[_Cell]], depth: int, identity: tuple[int, int, date]) -> tuple[str | None, ...]:
    """Section context of every row below the band (R51): a label-only row naming a period governs the rows
    after it until the next such label; rows under an out-of-scope or unknown section never bind."""
    contexts: list[str | None] = [None] * depth
    section: str | None = None
    for row in rows[depth:]:
        text = _section_text(row)
        if text:
            verdict = _marked_context(text, identity)
            if verdict is not None:
                section = verdict
        contexts.append(section)
    return tuple(contexts)


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


def expected_receipt_span(source: str, char_start: int, char_end: int, literal: str) -> tuple[int, int] | None:
    """The byte span the extractor's own receipt minting yields for ``literal`` inside a window (R52).

    The validator compares a stored receipt against this, so a receipt pointing at an attribute copy or a
    comment inside the cell can never validate: the extractor's search ignores markup and demands uniqueness.
    """
    try:
        receipt = receipt_for_literal(
            source=source,
            source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            search_start=char_start,
            search_end=char_end,
            literal=literal,
        )
    except ReceiptError:
        return None
    return receipt.byte_start, receipt.byte_end


def _cell_at(tables: Sequence[_Table], char_start: int, char_end: int) -> tuple[_Table, int, int] | None:
    for table in tables:
        for row_index, row in enumerate(table.rows):
            for column, cell in enumerate(row):
                if cell.origin is not None and cell.char_start <= char_start and char_end <= cell.char_end:
                    return table, row_index, column
    return None


def replay_table_layout(
    source: str, *, start: int, end: int, header_forms: Sequence[str] = (), identity: tuple[int, int, date] | None = None
) -> tuple[str, str, int]:
    """The ONE cell locator: the extractor confirms every located cell through it and the validator replays through it (R28).

    The byte location is resolved against the parsed grid (R36, R49); the table's period context comes from the
    same heading scan the extractor binds with (R27), its row section from the same label-row scan (R51) and its
    column header from the same header band (R37).  The replayed bytes must be exactly the receipt the
    extractor mints for the cell's visible text (R52).
    """
    char_start, char_end = _char_span(source, start, end)
    hit = _cell_at(_table_scan(parse_release_blocks(source), identity), char_start, char_end)
    if hit is None:
        raise ValueError("location is not a table cell")
    table, row_index, column = hit
    if table.context in _EXCLUDED:
        raise ValueError("table is governed by a period outside the admitted fiscal quarter")
    if row_index < table.depth:
        raise ValueError("location is a header cell")
    if table.row_context[row_index] in _EXCLUDED:
        raise ValueError("row sits in a section outside the admitted fiscal quarter")
    if column < 1:
        raise ValueError("cell has no matching header")
    cell = table.rows[row_index][column]
    if expected_receipt_span(source, cell.char_start, cell.char_end, cell.text.strip()) != (start, end):
        raise ValueError("replayed bytes are not the cell's receipt")
    accepted = {_normal(form) for form in header_forms if form}
    header = next((form for form in _column_headers(table.rows, table.depth, column) if not accepted or _normal(form) in accepted), None)
    if header is None:
        raise ValueError("cell has no matching header")
    return table.rows[row_index][0].text.strip(), header, column


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


_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
)
_MONTHS = {name: index for index, name in enumerate(_MONTH_NAMES, start=1)}
_MONTHS.update({name[:3]: index for index, name in enumerate(_MONTH_NAMES, start=1)})
_MONTHS["sept"] = 9
_DATE = r"(?:(?P<m1>[a-z]{3,9})\.?\s+(?P<d1>\d{1,2}),?\s*(?P<y1>\d{4})|(?P<d2>\d{1,2})\s+(?P<m2>[a-z]{3,9}),?\s*(?P<y2>\d{4}))"
_ANNUAL_QUALIFIER = re.compile(
    r"\b(?:six|nine|twelve|6|9|12)[\s-]+months?\b|\byear[\s-]+to[\s-]+date\b|\bytd\b|\byear\s+(?:ended|ending)\b"
    r"|\bfull[\s-]+year\b|\bannual\b",
    re.IGNORECASE,
)
_FISCAL_YEAR_LABEL = re.compile(r"\b(?:fiscal(?:\s+year)?|fy)[\s\-]*['\u2019]?\s*(?:20)?(\d{2})\b", re.IGNORECASE)
_QUARTER_WORD = re.compile(r"\b(first|second|third|fourth)\s+quarter\b", re.IGNORECASE)
_Q_FY = re.compile(r"\bq([1-4])\s*fy\s*(\d{4}|\d{2})\b", re.IGNORECASE)
_QUARTER_ENDED = re.compile(
    r"\b(?:(?:three|3)[\s-]+months?(?:\s+period)?|quarter(?:ly\s+period)?)\s+(?:ended|ending)\s+" + _DATE, re.IGNORECASE
)
_PERIOD_MARKER = re.compile(r"\b(?:ended|ending|months?|ytd|fiscal|quarter|fy)\b", re.IGNORECASE)
_DRIVERS_YEARS = re.compile(r"\bnet sales change drivers\s+(\d{4})\s+vs\.?\s+(\d{4})\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(20\d{2})\b")
_ORDINAL_INDEX = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_OUT_OF_SCOPE = frozenset({"annual", "foreign"})
_FORWARD_LOOKING = re.compile(
    r"\b(?:outlooks?|guidance|forecast(?:s|ed|ing)?|expect(?:s|ed|ing|ations?)?|project(?:ed|ing|ions?)"
    r"|target(?:s|ed|ing)?|estimat(?:e|es|ed|ing)|anticipat(?:e|es|ed|ing|ions?))\b"
)
_LABEL_PREFIX = re.compile(r"^for(?: the)?\s+")
_LABEL_NOISE = re.compile(r"\([^()]*\)|\bunaudited\b|[\u2014\u2013:;]")


def visible_text(source: str) -> str:
    """Rendered body text as the release parser reads it (R29, R38).

    Comments, scripts, styles, hidden elements, templates, attribute values and head content are not document
    statements because the parser never emits a block for them; there is no second, regex-shaped reading.
    """
    parts: list[str] = []
    for block in parse_release_blocks(source):
        if getattr(block, "table", None) is not None:
            parts.append(getattr(block.table, "caption", "") or "")
            parts.extend(cell.text for row in block.table.rows for cell in row)
        else:
            parts.append(getattr(block, "text", "") or "")
    return " ".join(part for part in parts if part)


def neutral_zero_convention(source: str) -> bool:
    return _NEUTRAL_ZERO.search(visible_text(source)) is not None


def _match_date(match: "re.Match[str]") -> tuple[int, int, int] | None:
    month = (match.group("m1") or match.group("m2") or "").casefold()
    day = match.group("d1") or match.group("d2")
    year = match.group("y1") or match.group("y2")
    if month not in _MONTHS or day is None or year is None:
        return None
    return int(year), _MONTHS[month], int(day)


def period_context(text: str, identity: tuple[int, int, date]) -> str | None:
    """Classify a heading, header band, section label or sentence against the admitted fiscal scope (R27, R44, R50).

    Returns ``"annual"`` for twelve-month, cumulative (six/nine-month, year-to-date), full-year forms and for a
    bare fiscal-year label with no quarter qualifier; ``"scope"`` when the text names the admitted quarter (an
    ordinal quarter, Q-FY, or "Three Months / Quarter Ended|Ending <date>" whose date is the admitted quarter
    end, in either date order, with or without a comma); ``"foreign"`` when it names another quarter, year or
    an unparseable quarter-end date; ``None`` when it carries no period information at all.
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
        year = int(m.group(2))
        year = year + 2000 if year < 100 else year
        ok = int(m.group(1)) == quarter and year == fiscal_year
        verdict = "foreign" if (not ok or verdict == "foreign") else "scope"
    for m in _QUARTER_ENDED.finditer(normal):
        ok = _match_date(m) == (current_end.year, current_end.month, current_end.day)
        verdict = "foreign" if (not ok or verdict == "foreign") else "scope"
    m = _DRIVERS_YEARS.search(normal)
    if m and int(m.group(1)) != fiscal_year:
        verdict = "foreign"
    labelled = False
    for m in _FISCAL_YEAR_LABEL.finditer(normal):
        labelled = True
        if 2000 + int(m.group(1)) != fiscal_year:
            verdict = "foreign"
    if verdict is None and labelled:
        return "annual"
    return verdict


def _is_heading(block: Any) -> bool:
    return getattr(block, "kind", None) is not None and block.kind.value == "heading"


def _is_paragraph(block: Any) -> bool:
    return getattr(block, "kind", None) is not None and block.kind.value == BlockKind.PARAGRAPH.value


_PURE_DATE = r"(?:[a-z]{3,9}\.? \d{1,2},? \d{4}|\d{1,2} [a-z]{3,9},? \d{4})"
_PURE_PERIOD_CORE = (
    r"(?:q[1-4]\s*fy\s*\d{2,4}|(?:first|second|third|fourth) quarter(?: fiscal(?: year)?)? \d{4}"
    r"|fiscal year \d{4} (?:first|second|third|fourth) quarter"
    r"|(?:three|six|nine|twelve|\d{1,2})[\s-]+months?(?: period)? (?:ended|ending) " + _PURE_DATE
    + r"|quarter(?:ly period)? (?:ended|ending) " + _PURE_DATE
    + r"|(?:fiscal )?year (?:ended|ending) " + _PURE_DATE + r")"
    + r"(?: and (?:\d{4}|" + _PURE_DATE + r"))?"
)
_PURE_PERIOD_HEADING = re.compile(r"^" + _PURE_PERIOD_CORE + r"$")
# A label paragraph: a pure period form, alone or with at most forty characters of other text before or after it
# ("Segment data. Three Months Ended March 31, 2026").
_LABEL_SHAPE = re.compile(r"^(?:.{0,40}?\s)?" + _PURE_PERIOD_CORE + r"(?:\s.{0,40})?$")


def _period_label_text(text: str) -> str:
    """A period label stripped of its decoration: parentheticals such as "(Unaudited)" or "(In millions)", the
    word "unaudited", dashes, colons and semicolons anywhere, a leading "For the", edge punctuation (R56, R62)."""
    normal = _LABEL_NOISE.sub(" ", _normal(text))
    normal = _LABEL_PREFIX.sub("", " ".join(normal.split()))
    return normal.strip(" .,")


def _is_pure_period(text: str) -> bool:
    return _PURE_PERIOD_HEADING.match(_period_label_text(text)) is not None


def _pure_period_label(block: Any) -> bool:
    """A paragraph that is a period label -- a bold "Nine Months Ended ..." line, decorated or not, or a short
    line that begins or ends with one -- governs like a pure-period heading (R50, R56, R62)."""
    return _is_paragraph(block) and _LABEL_SHAPE.match(_period_label_text(getattr(block, "text", "") or "")) is not None


def _is_forward(text: str, identity: tuple[int, int, date] | None) -> bool:
    """A heading or caption that names a forward-looking view (outlook, guidance, targets ...) and not the
    admitted quarter's actual results: "Fourth Quarter Fiscal Year 2026 Results and Outlook" names the results
    and is not forward-looking (R59, R63)."""
    if _FORWARD_LOOKING.search(_normal(text)) is None:
        return False
    return identity is None or period_context(text, identity) != "scope"


def _heading_level(block: Any) -> int:
    """The heading's level for section hierarchy: h1..h6 as written, a promoted or plain-text heading as 2."""
    level = int(getattr(block, "heading_level", 0) or 0)
    return level if 1 <= level <= 6 else 2


class _ForwardState:
    """Section hierarchy for forward-looking headings (R63): a forward heading governs every block after it until
    a heading of the same or a higher level; a paragraph label never releases it."""

    def __init__(self) -> None:
        self.level: int | None = None

    def heading(self, block: Any, text: str, identity: tuple[int, int, date] | None) -> None:
        level = _heading_level(block)
        if self.level is not None and level <= self.level:
            self.level = None
        if _is_forward(text, identity):
            self.level = level

    @property
    def active(self) -> bool:
        return self.level is not None


def _table_scan(blocks: Sequence[Any], identity: tuple[int, int, date] | None) -> list[_Table]:
    """Every table as a grid with its governing headings (immediate + enclosing topic), its period context and
    its row sections.

    A pure period label such as "Three Months Ended June 30, 2026" -- a heading or a label-only paragraph --
    refines the context of the topic heading above it without replacing that topic; both are consumed by the
    table they govern (R27, R50).  A table's own header band can only narrow the context (R37).
    """
    context: str | None = None
    immediate: str | None = None
    topic: str | None = None
    forward = _ForwardState()
    scanned: list[_Table] = []
    for block in blocks:
        if _is_heading(block) or _pure_period_label(block):
            immediate = getattr(block, "text", "")
            if not _is_pure_period(immediate):
                topic = immediate
            if _is_heading(block):
                forward.heading(block, immediate, identity)
            verdict = _marked_context(immediate, identity) if identity is not None else None
            if verdict is not None:
                context = verdict
        elif getattr(block, "table", None) is not None:
            rows = _grid(block)
            depth = _header_band(rows)
            caption = getattr(block.table, "caption", "") or ""
            band = _band_context(rows, depth, caption, identity) if identity is not None else None
            row_context = _row_contexts(rows, depth, identity) if identity is not None else tuple([None] * len(rows))
            governing = tuple(dict.fromkeys(item for item in (immediate, topic) if item))
            scanned.append(
                _Table(
                    block, rows, depth, caption, governing, band if band in _EXCLUDED else context, row_context,
                    forward.active or _is_forward(caption, identity),
                )
            )
            immediate = None
            topic = None
    return scanned


def document_period_verdict(blocks: Sequence[Any], identity: tuple[int, int, date], source: str | None = None) -> str | None:
    """The document's own period identity (R35).

    ``"scope"`` when any heading, pure-period label or table header band names the admitted quarter, or a
    year-level drivers heading names the admitted fiscal year; ``"foreign"`` / ``"annual"`` when the document
    carries period signals and none of them is consistent with the admitted scope; ``None`` when it carries no
    period signal at all -- such a document binds by the admitted scope.  ``source`` is accepted for call
    parity and unused: the grid comes from the parser's own span facts (R49).
    """
    fiscal_year = identity[0]
    signals: set[str] = set()
    for block in blocks:
        if _is_heading(block) or _pure_period_label(block):
            text = getattr(block, "text", "")
            years = _DRIVERS_YEARS.search(_normal(text))
            verdict = "scope" if years and int(years.group(1)) == fiscal_year else _marked_context(text, identity)
        elif getattr(block, "table", None) is not None:
            rows = _grid(block)
            verdict = _band_context(rows, _header_band(rows), getattr(block.table, "caption", "") or "", identity)
        else:
            continue
        if verdict is not None:
            signals.add(verdict)
    for verdict in ("scope", "foreign", "annual", "unknown"):
        if verdict in signals:
            return "annual" if verdict == "unknown" else verdict
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
    return any(normal == _normal(form) or normal.startswith(f"{_normal(form)} ") for form in forms)


def _admissible_table(table: _Table) -> bool:
    """An in-scope table that no forward-looking heading or caption governs (R54, R59, R63): the forward state
    is the section hierarchy of the scan, so "Outlook" over "Segment Results" still refuses."""
    return table.context not in _EXCLUDED and not table.forward


def _keyword_tables(tables: Sequence[_Table], *, keywords: Sequence[str]) -> list[_Table]:
    return [
        table
        for table in tables
        if _admissible_table(table)
        and any(all(_normal(keyword) in _normal(heading) for keyword in keywords) for heading in table.governing)
    ]


def _quarterly_tables(tables: Sequence[_Table], headings: Sequence[str]) -> list[_Table]:
    return [
        table
        for table in tables
        if _admissible_table(table) and any(_heading_matches(heading, headings) for heading in table.governing)
    ]


def _candidate_tables(tables: Sequence[_Table], headings: Sequence[str]) -> list[_Table]:
    """The in-scope tables a heading rule admits: a one-word keyword, a drivers heading, or a quarterly form (R27)."""
    if len(headings) == 1 and len(_normal(headings[0]).split()) == 1:
        return _keyword_tables(tables, keywords=(_normal(headings[0]),))
    if _normal(headings[0]).startswith("net sales change drivers"):
        return _keyword_tables(tables, keywords=(_normal(headings[0]),))
    return _quarterly_tables(tables, headings)


def _combined_presentation(table: _Table) -> bool:
    """True when the table's header band carries a combined Volume/Mix column (R39)."""
    return any(
        forms and _normal(forms[0]).startswith("volume/mix")
        for forms in (_column_headers(table.rows, table.depth, column) for column in range(1, _band_width(table.rows, table.depth)))
    )


def combined_volume_mix_presentation(source: str, *, current_start: date, current_end: date, prior_end: date) -> bool:
    """Whether the ONE in-scope drivers table of ``source`` presents volume and mix as a combined column (R39)."""
    fiscal_year, quarter = _fiscal_identity(current_start, current_end)
    _quarterly, driver_headings, _current, _prior = _scope_period_forms(current_start, current_end, prior_end)
    tables = _table_scan(parse_release_blocks(source), (fiscal_year, quarter, current_end))
    drivers = _candidate_tables(tables, (driver_headings[0],))
    return len(drivers) == 1 and _combined_presentation(drivers[0])


def _column(table: _Table, row_label: str, headers: Sequence[str]) -> tuple[Sequence[_Cell], int, str] | None:
    """The unique (row, column, header form) a row label and an accepted header form address in ``table`` (R37, R43, R51).

    Rows under an out-of-scope or unknown section never match.  The header form returned is the first band
    form of that column in band order, exactly as ``replay_table_layout`` reports it.  A header (or a stack
    of headers) spanning several columns addresses the single spanned column holding a metric literal in the
    target row, provided the other spanned cells are empty or a bare currency symbol (the "$" / "3.07" split
    of EDGAR tables); a sign fragment or a second literal under one spanning header is ambiguous.
    """
    if table is None:
        return None
    rows, depth = table.rows, table.depth
    accepted = {_normal(header) for header in headers if header}
    row_matches = [
        item
        for index, item in enumerate(rows)
        if index >= depth and item and _normal(item[0].text) == _normal(row_label) and table.row_context[index] not in _EXCLUDED
    ]
    if len(row_matches) != 1:
        return None
    row = row_matches[0]
    columns: list[tuple[int, str, Any]] = []
    for column in range(1, _band_width(rows, depth)):
        cells = _column_header_cells(rows, depth, column)
        forms = _column_headers(rows, depth, column)
        form = next((item for item in forms if _normal(item) in accepted), None)
        if form is None:
            continue
        # The key is the set of band cells that COMPOSE the matched form: every stacked cell for the joined
        # form, the one cell for a per-cell form -- so a stack in which only one row spans still shares its
        # key across the spanned columns (R49, R55).
        if cells and _normal(form) == _normal(" ".join(cell.text.strip() for cell in cells)):
            key: Any = tuple(id(cell.origin) for cell in cells)
        else:
            key = tuple(id(cell.origin) for cell in cells if _normal(cell.text) == _normal(form))
        # Band cells outside the key tell spanned columns apart ("As Reported" / "Restated") unless they are a
        # bare "$" or a parenthetical such as "(unaudited)" (R58, R64).
        residual = [cell.text.strip() for cell in cells if id(cell.origin) not in key]
        plain = all(re.fullmatch(r"\$|\(.*\)", item) is not None for item in residual)
        columns.append((column, form, key, plain))
    if len(columns) > 1 and len({key for _column_index, _form, key, _plain in columns}) == 1:
        spanned = [column for column, _form, _key, _plain in columns if column < len(row)]
        literal = [column for column in spanned if _is_literal_cell(row[column].text)]
        others_clean = all(_normal(row[column].text) in {"", "$"} for column in spanned if column not in literal)
        distinct = not all(plain for _column_index, _form, _key, plain in columns)
        columns = [item for item in columns if item[0] in literal] if len(literal) == 1 and others_clean and not distinct else []
    if len(columns) != 1 or columns[0][0] >= len(row):
        return None
    column = columns[0][0]
    cell = row[column]
    # One literal spanning several value columns whose header stacks differ names no single period (R55).
    covered = [index for index in range(1, len(row)) if cell.origin is not None and row[index].origin is cell.origin]
    stacks = {tuple(id(item.origin) for item in _column_header_cells(rows, depth, index)) for index in covered}
    if len(stacks) > 1:
        return None
    return row, column, columns[0][1]


@dataclass(frozen=True)
class _Plan:
    headings: tuple[str, ...]
    header_forms: tuple[str, ...]
    periods: dict[str, str]
    preferred_period: str

    def period_for(self, header: str) -> str:
        return self.periods.get(_normal(header), self.preferred_period)


def _observation_plan(definition: PGDefinition, current_start: date, current_end: date, prior_end: date) -> _Plan | None:
    """How one observation is addressed: which headings admit a table, which header forms name its column, and
    which period each form means.  Shared by the extractor and the validator (R46)."""
    quarterly_headings, driver_headings, current_forms, prior_forms = _scope_period_forms(current_start, current_end, prior_end)
    periods = {_normal(form): endpoint.isoformat() for forms, endpoint in ((current_forms, current_end), (prior_forms, prior_end)) for form in forms}
    if definition.metric in _EPS_METRICS:
        forms = prior_forms if definition.metric.startswith("pg_prior_") else current_forms
        return _Plan(tuple(quarterly_headings), tuple(forms), periods, periods[_normal(forms[0])])
    if definition.row_label is not None and definition.column_label is not None:
        return _Plan((driver_headings[0],), tuple(current_forms), periods, current_end.isoformat())
    if definition.metric.endswith("_organic_sales_growth_pct") and definition.row_label is not None:
        return _Plan(("Segment",), tuple(current_forms), periods, current_end.isoformat())
    return None


def _select_cell(tables: Sequence[_Table], definition: PGDefinition, plan: _Plan) -> tuple[_Table, Sequence[_Cell], int, str] | None:
    """Exactly ONE (table, row, column) across every admitted table may address the observation (R42)."""
    row_label = definition.row_label or plan.header_forms[0]
    headers = (definition.column_label,) if definition.column_label else plan.header_forms
    located = [
        (table, *found)
        for table in _candidate_tables(tables, plan.headings)
        if (found := _column(table, row_label, headers)) is not None
    ]
    return located[0] if len(located) == 1 else None


def _identity(current_start: date, current_end: date) -> tuple[int, int, date]:
    fiscal_year, quarter = _fiscal_identity(current_start, current_end)
    return fiscal_year, quarter, current_end


def locate_pg_observation(
    source: str, definition: PGDefinition, *, current_start: date, current_end: date, prior_end: date
) -> tuple[_Cell, str, int, str] | None:
    """The validator's replay of the extractor's selection: the unique cell, header form, column and period an
    observation is addressed by in ``source`` (R46).  None when the observation is not uniquely addressable."""
    plan = _observation_plan(definition, current_start, current_end, prior_end)
    if plan is None:
        return None
    tables = _table_scan(parse_release_blocks(source), _identity(current_start, current_end))
    located = _select_cell(tables, definition, plan)
    if located is None:
        return None
    _table, row, column, header = located
    return row[column], header, column, plan.period_for(header)


def pg_volume_cross_check(source: str, *, value: float, current_start: date, current_end: date, prior_end: date) -> bool:
    """The validator's replay of the total-volume cross-check (R52): every other same-period statement of Total
    P&G volume in ``source`` must agree with ``value``; False when the observation is not even addressable."""
    definition = next(item for item in PG_DEFINITIONS if item.metric == "pg_total_volume_growth_pct")
    plan = _observation_plan(definition, current_start, current_end, prior_end)
    identity = _identity(current_start, current_end)
    blocks = parse_release_blocks(source)
    tables = _table_scan(blocks, identity)
    located = _select_cell(tables, definition, plan) if plan is not None else None
    if located is None:
        return False
    return _volume_cross_check(tables, blocks, value=value, identity=identity, skip=located[0])


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


def _row_fact(*, definition: PGDefinition, tables: Sequence[_Table], blocks: Sequence[Any], plan: _Plan, document_id: str, bound: BoundRelease, event_id: str, identity: tuple[int, int, date]) -> dict[str, Any]:
    candidates = _candidate_tables(tables, plan.headings)
    headers = (definition.column_label,) if definition.column_label else plan.header_forms
    located = _select_cell(tables, definition, plan)
    # The combined subject is structural: ONE admitted drivers table presenting a Volume/Mix column (R39).
    combined = definition.metric in PG_COMBINED_VOLUME_MIX_METRICS and len(candidates) == 1 and _combined_presentation(candidates[0])
    if located is None:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            subject=f"{definition.metric} combined volume/mix" if combined else definition.metric,
            detail="The combined volume/mix presentation does not separately disclose this observation." if combined else "No unique heading, row label, and column header identifies this observation.",
        )
    table, row, column, matched_header = located
    period = plan.period_for(matched_header)
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
    receipt = _receipt(bound, cell.char_start, cell.char_end, literal)
    if receipt is None or not math.isfinite(value):
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    try:
        replayed_row, replayed_header, _column_index = replay_table_layout(
            bound.source, start=receipt.byte_start, end=receipt.byte_end, header_forms=headers, identity=identity
        )
    except ValueError:
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    if _normal(replayed_row) != _normal(definition.row_label or plan.header_forms[0]) or _normal(replayed_header) != _normal(matched_header):
        return _absent(definition=definition, document_id=document_id, event_id=event_id, detail="The cell is blank, nonnumeric, ambiguous, or not uniquely addressable.")
    if definition.metric == "pg_total_volume_growth_pct" and not _volume_cross_check(tables, blocks, value=value, identity=identity, skip=table):
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The document carries conflicting statements of total volume growth.",
            reason="cross_check_conflict",
        )
    return _present(definition=definition, value=value, document_id=document_id, bound=bound, receipt=receipt, event_id=event_id, period=period)


# "volume" as the total-volume measure: not "organic volume", not "volume excluding ...", not "volume/mix" (R40).
_VOLUME_TERM = r"(?<!organic )\bvolumes?\b(?!\s*/\s*mix\b|\s+excluding\b|\s+mix\b)"
_VOLUME_STATEMENT = re.compile(
    rf"{_VOLUME_TERM}[^.;]{{0,40}}?\b(increased|grew|rose|was up|up|decreased|declined|fell|was down|down)\b"
    r"[^.;%]{0,24}?(\d+(?:\.\d+)?)\s*(?:%|percent\b)",
    re.IGNORECASE,
)
_TOTAL_PG = re.compile(r"\btotal p&g\b")
_VOLUME_DECREASE = {"decreased", "declined", "fell", "was down", "down"}
# Whole words only: "previously announced" and "priorities" are not prior-period qualifiers (R47).
_PRIOR_PERIOD = re.compile(r"\b(?:prior|previous|year[\s-]+ago|last year|a year earlier)\b")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_VOLUME_COLUMN_QUALIFIERS = ("excluding", "organic", "mix")


def _volume_statements(tables: Sequence[_Table], blocks: Sequence[Any], *, identity: tuple[int, int, date], skip: _Table) -> list[float]:
    """Every same-period statement of Total P&G volume growth other than the bound drivers cell (R32).

    Tables are read through the same grid and header band as the bound cell (R37, R43): a column counts only
    when its stacked header names volume without an organic / excluding / mix qualifier, and the Total P&G row
    may sit anywhere below the band.  A sentence counts when it names Total P&G and the total-volume measure
    with a growth verb and a percentage; a prior-period qualifier BEFORE the verb scopes it to the prior period
    and an out-of-scope period label skips it (R40, R47).
    """
    statements: list[float] = []
    for table in tables:
        if table.block is skip.block or table.context in _EXCLUDED:
            continue
        rows, depth = table.rows, table.depth
        for index, row in enumerate(rows):
            if index < depth or not row or _normal(row[0].text) != "total p&g" or table.row_context[index] in _EXCLUDED:
                continue
            seen: set[int] = set()
            for column in range(1, len(row)):
                if id(row[column].origin) in seen:
                    continue
                seen.add(id(row[column].origin))
                forms = _column_headers(rows, depth, column)
                header = _normal(forms[0]) if forms else ""
                if "volume" not in header or any(word in header for word in _VOLUME_COLUMN_QUALIFIERS):
                    continue
                statement = parse_pg_literal(row[column].text, unit="percent")
                if statement is not None:
                    statements.append(statement)
    context = None
    forward = _ForwardState()
    for block in blocks:
        if _is_heading(block) or _pure_period_label(block):
            if _is_heading(block):
                forward.heading(block, getattr(block, "text", ""), identity)
            verdict = _marked_context(getattr(block, "text", ""), identity)
            if verdict is not None:
                context = verdict
        elif context not in _OUT_OF_SCOPE and not forward.active and _is_paragraph(block):
            for sentence in _SENTENCE_SPLIT.split(_normal(getattr(block, "text", ""))):
                if not _TOTAL_PG.search(sentence) or period_context(sentence, identity) in _OUT_OF_SCOPE:
                    continue
                for match in _VOLUME_STATEMENT.finditer(sentence):
                    if _PRIOR_PERIOD.search(sentence[: match.start(1)]):
                        continue
                    magnitude = float(match.group(2))
                    statements.append(-magnitude if match.group(1) in _VOLUME_DECREASE else magnitude)
    return statements


def _volume_cross_check(tables: Sequence[_Table], blocks: Sequence[Any], *, value: float, identity: tuple[int, int, date], skip: _Table) -> bool:
    return all(statement == value for statement in _volume_statements(tables, blocks, identity=identity, skip=skip))


def _reconciliation_paragraph(blocks: Sequence[Any], definition: PGDefinition, identity: tuple[int, int, date]) -> Any | None:
    """The ONE paragraph a bounded-text observation may bind: under a reconciliation / non-GAAP heading, naming
    the row label, not carried under another quarter's heading, and within the bounded length (R35, R45).
    Shared by the extractor and the validator."""
    active = False
    context: str | None = None
    forward = _ForwardState()
    paragraphs = []
    metric_name = _normal(definition.row_label or "")
    for block in blocks:
        if _is_heading(block) or _pure_period_label(block):
            normal = _normal(getattr(block, "text", ""))
            if _is_heading(block):
                forward.heading(block, normal, identity)
            active = ("reconciliation" in normal and metric_name in normal or "non-gaap" in normal) and not forward.active
            verdict = _marked_context(normal, identity)
            if verdict is not None:
                context = verdict
        # A reconciliation paragraph carried under another quarter's heading -- or under a heading whose period
        # cannot be read, or inside a forward-looking section -- is not this quarter's statement (R35, R55, R63);
        # a twelve-month heading does not refuse it, because a Q4 release's non-GAAP section covers both periods.
        elif active and context not in {"foreign", "unknown"} and _is_paragraph(block):
            text = getattr(block, "text", "") or ""
            if metric_name in _normal(text):
                paragraphs.append(block)
    # Uniqueness is judged over every candidate; only then is the one candidate held to the bounded length (R45).
    if len(paragraphs) != 1:
        return None
    text = (getattr(paragraphs[0], "text", "") or "").strip()
    return paragraphs[0] if 0 < len(text) <= PG_BOUNDED_TEXT_MAX else None


def pg_reconciliation_paragraph(source: str, definition: PGDefinition, identity: tuple[int, int, date]) -> Any | None:
    return _reconciliation_paragraph(parse_release_blocks(source), definition, identity)


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
    paragraph = _reconciliation_paragraph(blocks, definition, identity)
    if paragraph is None:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The reconciliation paragraph is not uniquely addressable under its heading.",
        )
    sentence = paragraph.text.strip()
    receipt = _receipt(bound, paragraph.source_span.char_start, paragraph.source_span.char_end, sentence)
    if receipt is None:
        return _absent(
            definition=definition,
            document_id=document_id,
            event_id=event_id,
            detail="The reconciliation paragraph is not uniquely addressable in source bytes.",
        )
    return _present(definition=definition, value=sentence, document_id=document_id, bound=bound, receipt=receipt, event_id=event_id, period=period)


def extract_pg_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, fiscal_period: Any, fiscal_scope: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    if fiscal_scope is None:
        raise ValueError("PG extraction requires fiscal_scope")
    current_start, current_end, _prior_start, prior_end = _scope(fiscal_scope)
    if fiscal_period.calendar_end != current_end:
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The source fiscal period does not match the admitted fiscal scope.") for item in PG_DEFINITIONS]
    source = bound.source
    blocks = parse_release_blocks(source)
    fiscal_year, quarter = _fiscal_identity(current_start, current_end)
    identity = (fiscal_year, quarter, current_end)
    if (str(getattr(fiscal_period, "year", None)), str(getattr(fiscal_period, "quarter", None))) != (str(fiscal_year), str(quarter)):
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The workspace fiscal identity does not match the admitted fiscal scope.") for item in PG_DEFINITIONS]
    if document_period_verdict(blocks, identity) in _OUT_OF_SCOPE:
        return [_absent(definition=item, document_id=document_id, event_id=event_id, detail="The document's period signals do not name the admitted fiscal quarter.") for item in PG_DEFINITIONS]
    tables = _table_scan(blocks, identity)
    facts = []
    for definition in PG_DEFINITIONS:
        plan = _observation_plan(definition, current_start, current_end, prior_end)
        if definition.metric == "pg_core_reconciliation_context":
            facts.append(_text_fact(definition=definition, blocks=blocks, document_id=document_id, bound=bound, event_id=event_id, period=current_end.isoformat(), identity=identity))
        elif plan is None:
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, detail="This literal growth fact is not separately disclosed by the selected source."))
        else:
            facts.append(_row_fact(definition=definition, tables=tables, blocks=blocks, plan=plan, document_id=document_id, bound=bound, event_id=event_id, identity=identity))
    return facts


__all__ = ["PG_BOUNDED_TEXT_MAX", "PG_COMBINED_VOLUME_MIX_METRICS", "PG_DEFINITIONS", "PG_METRIC_KEYS", "combined_volume_mix_presentation", "document_period_verdict", "extract_pg_release_facts", "expected_receipt_span", "locate_pg_observation", "neutral_zero_convention", "parse_release_blocks", "period_context", "pg_issuer", "pg_private_registry", "pg_profile", "pg_reconciliation_paragraph", "pg_volume_cross_check", "replay_table_layout", "visible_text"]
