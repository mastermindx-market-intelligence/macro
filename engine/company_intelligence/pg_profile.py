"""Private, source-scoped Procter & Gamble economic observations.

Prior PG EPS rows use the prior fiscal interval's ISO end date instead of the
generic ``prior_year_same_quarter`` label.  ``fiscal_scope`` supplies both
interval boundaries that ``FiscalPeriod`` lacks.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
import functools
import hashlib
import html
import math
import re
from typing import Any, Sequence
import unicodedata

from engine.fundamental_forensics.disclosure_diff import BlockKind, normalize_filing

from .documents import TypedAbsence, text_span
from .event_workspace import IssuerRegistry
from .identity import IssuerIdentity, ListingAlias, company_id_for_cik
from .issuer_profiles import IssuerProfile, _no_guidance
from . import pg_envelope
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
    # The table's own labels: its caption and every label-shaped paragraph since the last heading or table (R89).
    labels: tuple[str, ...] = ()
    # The prose paragraphs around it, read per metric for a measure basis (R99).
    prose: tuple[str, ...] = ()
    # Its own label cells -- every band row's stub cell and every label-only row above its last value row -- read
    # positively (R107).
    cell_labels: tuple[str, ...] = ()
    # The paragraphs and topic headings of every section that holds it, beyond its own stretch and governing
    # headings, read per metric for a measure basis (R108).
    section_prose: tuple[str, ...] = ()
    # Whether a sentence anywhere in the document declares a measure basis (R108).
    declared_measure: bool = False


_GROUP_ORDER = {"thead": 0, "tbody": 1, "tfoot": 2}


def _grid(block: Any) -> tuple[tuple[_Cell, ...], ...]:
    """The table as an occupancy grid from the parser's own layout facts (R49, R55, R61, R66).

    Rows are laid out in the order a browser DRAWS them -- the first thead group, then the remaining groups in
    source order, then the first tfoot group -- and every HTML row exists, including one that emitted no cell.  A
    spanning cell fills every position its colspan covers; a rowspan carries the cell down its own row group
    and never across a group boundary; a rowspan of 0 runs to the end of the group.  Rows are padded to the
    grid width with empty placeholders so every row can be indexed by column.
    """
    emitted = list(block.table.rows)
    layout = list(getattr(block.table, "row_layout", ()) or ())
    ordinals = [next((int(getattr(cell, "row_ordinal", -1)) for cell in row), -1) for row in emitted]
    if not layout or any(ordinal < 0 for ordinal in ordinals):
        ordinals = list(range(len(emitted)))
        layout = [(index, 0, "tbody") for index in range(len(emitted))]
    cells_by_ordinal: dict[int, list[Any]] = {}
    for ordinal, row in zip(ordinals, emitted):
        cells_by_ordinal.setdefault(ordinal, []).extend(row)
    known = {ordinal for ordinal, _group, _kind in layout}
    layout.extend((ordinal, 0, "tbody") for ordinal in cells_by_ordinal if ordinal not in known)
    groups: dict[int, tuple[str, list[int]]] = {}
    for ordinal, group, kind in sorted(layout):
        groups.setdefault(group, (kind, []))[1].append(ordinal)
    grid: list[list[_Cell]] = []
    first: dict[str, int] = {}
    # The parser records every row group it opened -- including one that holds no row -- so an empty first
    # <thead> is still the header group and the second one is drawn in place (R78).
    for ordinal, kind in getattr(block.table, "group_layout", ()) or ():
        first.setdefault(kind, int(ordinal))
    for group in sorted(groups):
        first.setdefault(groups[group][0], group)

    def drawn(group: int) -> tuple[int, int]:
        # CSS 2.1 §17.2: only the FIRST thead is the header and only the FIRST tfoot the footer; every other
        # row group renders in source order.
        kind = groups[group][0]
        return (_GROUP_ORDER.get(kind, 1) if first.get(kind) == group else 1, group)

    for group in sorted(groups, key=drawn):
        _kind, members = groups[group]
        carried: dict[tuple[int, int], _Cell] = {}
        for position, ordinal in enumerate(members):
            line: list[_Cell] = []
            column = 0
            for cell in cells_by_ordinal.get(ordinal, []):
                while (position, column) in carried:
                    line.append(carried.pop((position, column)))
                    column += 1
                span = getattr(cell, "source_span", None)
                item = _Cell(cell.text, getattr(span, "char_start", 0), getattr(span, "char_end", 0), cell)
                colspan = max(1, int(getattr(cell, "colspan", 1) or 1))
                rowspan = int(getattr(cell, "rowspan", 1))
                remaining = len(members) - position
                below = remaining if rowspan <= 0 else min(rowspan, remaining)
                for offset in range(colspan):
                    line.append(item)
                    for step in range(1, below):
                        carried[(position + step, column + offset)] = item
                column += colspan
            while (position, column) in carried:
                line.append(carried.pop((position, column)))
                column += 1
            grid.append(line)
    width = max((len(line) for line in grid), default=0)
    return tuple(tuple(line) + (_EMPTY_CELL,) * (width - len(line)) for line in grid)


def _layout_overflow(block: Any) -> bool:
    """True when any cell declared an absurd span the parser read as 1: the layout cannot be trusted (R66)."""
    return any(getattr(cell, "span_overflow", False) for row in block.table.rows for cell in row)


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


def _is_mark_cell(text: str) -> bool:
    """A value cell that is a dash or wholly decoration -- a footnote mark "(1)", "(a)", "(ii)", "(*)" (R84, R92)."""
    literal = text.strip()
    return literal in _DASHES or (bool(literal) and _DECORATION.fullmatch(_normal(literal)) is not None)


def _section_text(row: Sequence[_Cell]) -> str | None:
    """A row that carries no metric literal other than marks is a label row -- one cell or several, in any
    column, at any colspan -- and its whole text is what names a section (R51, R57, R62, R84, R92); a row holding
    a number is a data row."""
    if not row or any(_is_literal_cell(cell.text) and not _is_mark_cell(cell.text) for cell in row):
        return None
    # A label row may carry dashes or footnote marks in its value columns ("Twelve Months Ended June 30, 2026 |
    # (1) | —") (R84, R92).
    return _row_text([cell for cell in row if not _is_mark_cell(cell.text)])


def _marked_context(text: str, identity: tuple[int, int, date]) -> str | None:
    """The ONE period classifier (R67); kept under its historical name for every governed text."""
    return period_context(text, identity)


def _band_context(rows: Sequence[Sequence[_Cell]], depth: int, caption: str, identity: tuple[int, int, date]) -> str | None:
    """Period context of a table's own header band (R37, R43, R50).

    The caption, every label-column band cell and every value column's stacked band text are classified:
    a twelve-month or cumulative label anywhere refuses the table ("annual"); a column whose stack carries a
    period marker that does not resolve to any known form is "unknown" and refuses it too; a column naming
    the admitted quarter keeps the band in scope beside a prior-period column ("scope"); a band that names
    periods and never the admitted quarter is "foreign"; a band with no period label at all is None.
    """
    labels: dict[int, str] = {}
    for row in rows[:depth]:
        if row and row[0].origin is not None and row[0].text.strip():
            labels.setdefault(id(row[0].origin), row[0].text)
    # Table-level texts (caption, label-column cells) name the whole table: a foreign one refuses it.  Value
    # columns name their own column: a foreign one is the prior-period column beside a current one.
    table_level = {band_context(text, identity) for text in (caption, *labels.values()) if text.strip()} - {None}
    columns: set[str] = set()
    for column in range(1, _band_width(rows, depth)):
        stacked = " ".join(cell.text.strip() for cell in _column_header_cells(rows, depth, column))
        if stacked.strip():
            verdict = band_context(stacked, identity)
            if verdict is not None:
                columns.add(verdict)
    for verdict in ("annual", "unknown"):
        if verdict in table_level or verdict in columns:
            return verdict
    if "foreign" in table_level:
        return "foreign"
    if "scope" in columns or "scope" in table_level:
        return "scope"
    return "foreign" if "foreign" in columns else None


def _row_contexts(rows: Sequence[Sequence[_Cell]], depth: int, identity: tuple[int, int, date]) -> tuple[str | None, ...]:
    """Section context of every row below the band (R51, R78): a label-only row naming a period FORM governs
    the rows after it until the next such label; a repeated band row of bare years ("2026 | 2025") names the
    columns, never a section, so it cannot release a twelve-month label above it; rows under an out-of-scope or
    unknown section never bind."""
    contexts: list[str | None] = [None] * depth
    section: str | None = None
    for row in rows[depth:]:
        text = _section_text(row)
        if text:
            verdict = period_context(text, identity)
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
    if table.forward:
        raise ValueError("table sits in a non-results section")
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


_NON_GAAP_SPELLING = re.compile(r"\bnon[\s-]*gaap\b")
_US_DOLLAR_SPELLING = re.compile(r"\bus\s+\$")


def _normal(value: str) -> str:
    normal = " ".join(value.replace("\xa0", " ").replace("&nbsp;", " ").casefold().split())
    return _US_DOLLAR_SPELLING.sub("us$", _NON_GAAP_SPELLING.sub("non-gaap", normal))


# Invisible format characters a renderer draws as nothing, and every dash that may join a word's parts (R106).
_INVISIBLE_FORMAT = re.compile("[\u00ad\u034f\u115f\u1160\u17b4\u17b5\u180b-\u180f\u200b-\u200d\u2060-\u2064\ufeff]")
_WORD_DASH = re.compile("[\u2010-\u2015\u2212\u2e3a\u2e3b\ufe58\ufe63\uff0d]")
# Characters that reorder what is drawn: text carrying one is not read as written (R106).
_BIDI_CONTROL = re.compile("[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]")


# Scripts with no letter a reader could take for a Latin one: a whole word in them is a foreign word (R106).
_FOREIGN_SCRIPTS = ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH", "IDEOGRAPHIC", "HIRAGANA", "KATAKANA", "HANGUL")
_LETTER_RUN = re.compile(r"[^\W\d_]+")


@functools.lru_cache(maxsize=65536)
def _lexicon_text(text: str, *, prose: bool = False) -> str | None:
    """Text as the closed lexicons read it (R106): NFKC-folded, invisible format characters removed, every dash read
    as a hyphen, diacritics dropped, then ``_normal``.  None when the text cannot be read as written: it carries a
    bidirectional control, or a letter that is not a plain Latin letter ("ʟ", a Cyrillic "а").  PROSE reads a
    whole word of a script that has no Latin look-alike (Han, kana, Hangul) as a foreign word the lexicons do not
    name -- "全球品牌 demand was stable" -- but never a word that mixes it with Latin letters."""
    folded = _WORD_DASH.sub("-", _INVISIBLE_FORMAT.sub("", unicodedata.normalize("NFKC", text)))
    if _BIDI_CONTROL.search(folded):
        return None
    folded = unicodedata.normalize(
        "NFC", "".join(char for char in unicodedata.normalize("NFD", folded) if unicodedata.category(char) != "Mn")
    )
    words: list[str] = []
    for run in _LETTER_RUN.finditer(folded):
        word = run.group(0)
        if word.isascii():
            continue
        if prose and all(unicodedata.name(char, "").startswith(_FOREIGN_SCRIPTS) for char in word):
            words.append(word)
            continue
        return None
    for word in words:
        folded = folded.replace(word, " ")
    return _normal(folded)


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
_MONTH_WORD = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?"
    r"|nov(?:ember)?|dec(?:ember)?)"
)
_DATE = r"(?:(?P<m1>[a-z]{3,9})\.?\s+(?P<d1>\d{1,2}),?\s*(?P<y1>\d{4})|(?P<d2>\d{1,2})\s+(?P<m2>[a-z]{3,9}),?\s*(?P<y2>\d{4}))"
# A fiscal-year tail in every spelling in use: "fiscal year 2026", "fiscal-year 2026", "fiscal '25", "FY-25",
# "FY’25", "FY 2025", "FY2025", "fiscal 25".  The group captures the two-digit year.
_FY_TAIL = r"(?:fiscal(?:[\s-]+year)?|fy)[\s\-]*['\u2019]?\s*(?:20)?(\d{2})\b"
_ANNUAL_QUALIFIER = re.compile(
    r"\b(?:six|nine|twelve|6|9|12)[\s-]+months?(?:\s+period)?(?:\s+(?:ended|ending)\s+" + _DATE + r")?"
    r"|\byear[\s-]+to[\s-]+date\b|\bytd\b|\b(?:fiscal[\s-]+)?year\s+(?:ended|ending)\b(?:\s+" + _DATE.replace("?P<", "?P<x") + r")?"
    r"|\bfull[\s-]+year\b|\bannual\b",
    re.IGNORECASE,
)
_FISCAL_YEAR_LABEL = re.compile(r"\b" + _FY_TAIL, re.IGNORECASE)
_QUARTER_WORD = re.compile(
    r"\b(first|second|third|fourth)[\s-]+quarter\b(?:[\s-]+(?:of\s+)?(?:" + _FY_TAIL + r"|['\u2019](\d{2})\b))?", re.IGNORECASE
)
_Q_FY = re.compile(
    r"\b(?:q[\s-]*([1-4])|([1-4])q)[\s\-]*(?:of\s+)?fy[\s\-]*['\u2019]?\s*(?:20)?(\d{2})\b", re.IGNORECASE
)
# The same form with the fiscal year first: "FY26 Q4", "Fiscal Year 2026 Q4", "fiscal '26 Q4" (R72).
_FY_Q = re.compile(r"\b" + _FY_TAIL + r"[\s\-]*q[\s-]*([1-4])\b", re.IGNORECASE)
# A bare quarter number with no year anywhere in the text ("Q3 Highlights", "Quarter 3 Highlights"): the admitted
# quarter when the number matches; beside any year it stays an unreadable token, because "Q3 2026" may be fiscal or
# calendar (R82, R94).
_Q_BARE = re.compile(r"\b(?:q[\s-]?|quarter\s+)([1-4])\b(?![\s-]*(?:fy|fiscal|20\d\d|['\u2019]\d\d))", re.IGNORECASE)
_QUARTER_ENDED = re.compile(
    r"\b(?:(?:three|3)[\s-]+months?(?:\s+period)?|(?:fiscal\s+)?quarter(?:ly\s+period)?)\s+(?:ended|ending)\s+" + _DATE,
    re.IGNORECASE,
)
# The drivers heading's years alone are the form; the heading words stay in the residual for route admission (R73).
# Any connective, parentheses and either order name the same PAIR -- "2027 vs. 2026", "2027 v. 2026", "2027 versus
# 2026", "2027 compared with 2026", "(2026 vs. 2025)", "2025 vs. 2026" (R87).
_DRIVERS_YEARS = re.compile(
    r"(?<=\bnet sales change drivers )\(?(\d{4})\s+(?:vs?\.?|versus|compared\s+(?:with|to)|against)\s+(\d{4})\b\)?", re.IGNORECASE
)
_BARE_DATE = re.compile(r"\b" + _DATE, re.IGNORECASE)
_YEAR = re.compile(r"\b(20\d{2})\b")
_ORDINAL_INDEX = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_OUT_OF_SCOPE = frozenset({"annual", "foreign"})
# R67 -- the rule, not a list of places: any token that names a period in ANY vocabulary (a year, a month, a
# quarter number, a period word).  Text carrying one outside a recognised form is "unknown" and refuses.
_PERIOD_TOKEN = re.compile(
    r"\b(?:19|20)\d{2}\b|(?<![\w])['\u2019]\d{2}\b|\b" + _MONTH_WORD + r"\b|\b\d{0,2}[\s-]*q[\s-]*[1-4]\w*\b|\b[1-4]q\d*\b"
    r"|\b[12]h\d*\b|\bh[12]\b|\bcy\d*\b|\bttm\b|\bltm\b|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}"
    r"|\b(?:quarters?|quarterly|qtrs?|months?|monthly|years?|yearly|fiscal|fy|ytd|ended|ending|periods?|annual"
    r"|annually|half|halves|interim|semiannual|semester|trailing|calendar|weeks?|prior|previous|next|last)\b|\bto[\s-]+date\b",
    re.IGNORECASE,
)
# Words that may accompany a period form in an admitted heading without naming a topic (R73).
_HEADING_GLUE = frozenset({"for", "the", "vs", "vs.", "versus", "compared", "with", "to", "and", "of", "-", "—", "–", ":", ";", ","})
# R73 -- positive admission: a table binds only under a heading that decomposes into recognised period forms
# plus words of ONE route's vocabulary.  Every other heading is unknown territory and admits nothing.
_ROUTE_WORDS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "segment": (
        frozenset({"segment", "segments"}),
        frozenset({"segment", "segments", "result", "results", "organic", "sales", "growth", "change", "by", "reportable", "business", "information", "net", "of", "and"}),
    ),
    "drivers": (frozenset({"drivers"}), frozenset({"net", "sales", "change", "drivers", "driver", "of", "and", "by"})),
    "quarterly": (
        frozenset(),
        frozenset({"result", "results", "eps", "diluted", "net", "earnings", "per", "share", "common", "consolidated", "information", "of", "and", "financial", "income", "statement", "statements"}),
    ),
    "reconciliation": (
        frozenset({"reconciliation", "reconciliations", "non-gaap"}),
        frozenset({"reconciliation", "reconciliations", "of", "non-gaap", "gaap", "measures", "measure", "core", "eps", "to", "diluted", "net", "earnings", "per", "share", "common", "and", "financial"}),
    ),
}
_FORWARD_LOOKING = re.compile(
    r"\b(?:out[\s-]*looks?|guidance|fore[\s-]*cast(?:s|ed|ing)?|expect(?:s|ed|ing|ations?)?|project(?:ed|ing|ions?)"
    r"|target(?:s|ed|ing)?|estimat(?:e|es|ed|ing)|anticipat(?:e|es|ed|ing|ions?)|looking[\s-]+ahead|going[\s-]+forward"
    r"|pre[\s-]*views?)\b"
)


def _names_forward(text: str) -> bool:
    """A forward-looking word, read through the lexicon reading; text that cannot be read as written counts as one
    (R106, R112)."""
    lexicon = _lexicon_text(text)
    return lexicon is None or _FORWARD_LOOKING.search(lexicon) is not None


# R67 -- the tokens that make a short paragraph a period LABEL rather than prose: a year, a month, a quarter
# number, or a period-form word.  "prior year" alone in a sentence is prose.
_STRONG_PERIOD_TOKEN = re.compile(
    r"\b(?:19|20)\d{2}\b|\b" + _MONTH_WORD + r"\b|\b\d{0,2}q[1-4]\w*\b|\b[1-4]q\d*\b"
    r"|\b(?:quarters?|quarterly|qtrs?|months?|fiscal|fy|ytd|ended|ending)\b",
    re.IGNORECASE,
)
_LABEL_PREFIX = re.compile(r"^for(?: the)?\s+")
# Decoration that says nothing about period, topic or basis (R82): "(unaudited)", a units note, a footnote mark.
# Any OTHER parenthetical keeps its words -- "(Outlook)", "(Pro Forma Combined Company)" -- so admission sees them.
# The units note is a CLOSED grammar (R88): "(in millions)", "(amounts in millions, except per share amounts)",
# "(in millions of dollars, except per share data and percentages)", optionally closed by "unaudited"; a
# parenthetical holding any other word -- "(in millions, pro forma combined)" -- keeps every one of its words.
_UNITS_EXCEPT = r"(?:per[\s-]+share(?:\s+(?:amounts?|data|figures))?|percentages?|ratios?)"
_UNITS_NOTE = (
    r"(?:amounts?|dollars|figures|\$|us\$)?\s*in\s+(?:millions|thousands|billions)(?:\s+of\s+(?:us\s+|u\.s\.\s+)?dollars)?"
    r"(?:\s*[,;]?\s*except\s+" + _UNITS_EXCEPT + r"(?:\s*(?:,\s*(?:and\s+)?|and\s+)" + _UNITS_EXCEPT + r")*)?"
    r"(?:\s*[,;]\s*unaudited)?\s*"
)
_DECORATION = re.compile(
    r"\((?:unaudited|" + _UNITS_NOTE + r"|\d{1,2}[a-z]?|[a-z]|[ivx]{2,4}|\*{1,3}|\u2020|\u2021|%|percent(?:ages?)?)\)"
)
_LABEL_NOISE = re.compile(r"\bunaudited\b|[\u2014\u2013:;()]")


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


def _prior_quarter_end(current_end: date) -> date:
    try:
        return current_end.replace(year=current_end.year - 1)
    except ValueError:
        return current_end.replace(year=current_end.year - 1, day=28)


def _date_verdict(parsed: tuple[int, int, int] | None, current_end: date, prior_end: date, current: str) -> str:
    """A quarter-end date: the admitted one (``current`` -- "scope" for a quarter-ended form, "year" for a bare
    date), the prior year's ("prior_quarter": neutral only beside a scope form, as in "Three Months Ended June 30,
    2026 and 2025"), or another ("foreign") (R81)."""
    if parsed == (current_end.year, current_end.month, current_end.day):
        return current
    if parsed == (prior_end.year, prior_end.month, prior_end.day):
        return "prior_quarter"
    return "foreign"


def _quarter_year_verdict(ordinal: int, year: int, quarter: int, fiscal_year: int) -> str:
    """A quarter named with its fiscal year: the admitted one, the same quarter of the prior fiscal year
    ("prior_quarter": neutral beside a scope form, foreign alone or beside a year-level form -- frozen s12), or
    another (R81)."""
    if ordinal != quarter:
        return "foreign"
    if year == fiscal_year:
        return "scope"
    return "prior_quarter" if year == fiscal_year - 1 else "foreign"


def _drivers_pair(match: "re.Match[str]", fiscal_year: int) -> bool:
    """The drivers heading's year PAIR names the admitted fiscal year against its prior, in either order (R81, R87)."""
    return {int(match.group(1)), int(match.group(2))} == {fiscal_year, fiscal_year - 1}


def _period_forms(normal: str, identity: tuple[int, int, date]) -> tuple[list[str], str]:
    """Every recognised period form in ``normal`` with its verdict, and the residual text they leave (R67).

    Verdicts: ``"annual"`` (cumulative / full-year forms), ``"scope"`` (the admitted quarter), ``"foreign"``
    (another readable period), ``"fiscal"`` (a bare label of the admitted fiscal year), ``"year"`` (the bare
    admitted year), ``"calendar"`` (the bare quarter-end calendar year when it is not the fiscal year), ``"prior"``
    (the bare year before the fiscal year, or before the calendar year when the text names no fiscal year, as in
    "2026 vs 2025").  Recognised forms are removed from the residual in the order they are judged.
    """
    fiscal_year, quarter, current_end = identity
    verdicts: list[str] = []
    residual = normal

    def take(pattern: "re.Pattern[str]", judge: Any) -> list["re.Match[str]"]:
        nonlocal residual
        found = list(pattern.finditer(normal))
        for match in found:
            verdicts.append(judge(match))
        residual = pattern.sub(" ", residual)
        return found

    if _ANNUAL_QUALIFIER.search(normal):
        verdicts.append("annual")
        residual = _ANNUAL_QUALIFIER.sub(" ", residual)
    prior_end = _prior_quarter_end(current_end)
    quarter_forms = bool(take(_QUARTER_ENDED, lambda m: _date_verdict(_match_date(m), current_end, prior_end, "scope")))
    quarter_forms |= bool(take(_Q_FY, lambda m: _quarter_year_verdict(int(m.group(1) or m.group(2)), 2000 + int(m.group(3)), quarter, fiscal_year)))
    quarter_forms |= bool(take(_FY_Q, lambda m: _quarter_year_verdict(int(m.group(2)), 2000 + int(m.group(1)), quarter, fiscal_year)))
    # The drivers heading is a YEAR-level signal (R35): consistent with the admitted year only when its pair is the
    # fiscal year and its prior ("2026 vs. 2025"); any other pair is another table (R81, R87).
    take(_DRIVERS_YEARS, lambda m: "year" if _drivers_pair(m, fiscal_year) else "foreign")
    quarter_words = list(_QUARTER_WORD.finditer(normal))
    residual = _QUARTER_WORD.sub(" ", residual)
    quarter_forms |= bool(quarter_words)
    if _Q_BARE.search(residual) is not None and _YEAR.search(normal) is None and _FISCAL_YEAR_LABEL.search(normal) is None:
        quarter_forms |= bool(take(_Q_BARE, lambda m: "scope" if int(m.group(1)) == quarter else "foreign"))
    labels = list(_FISCAL_YEAR_LABEL.finditer(residual))
    residual = _FISCAL_YEAR_LABEL.sub(" ", residual)
    label_years = [2000 + int(m.group(1)) for m in labels]
    dates = list(_BARE_DATE.finditer(residual))
    residual = _BARE_DATE.sub(" ", residual)
    bare_years = [int(m.group(1)) for m in _YEAR.finditer(residual)]
    residual = _YEAR.sub(" ", residual)
    # The fiscal year named ANYWHERE in the text -- a bare year, a fiscal-year label, a quarter's tail, or inside the
    # drivers pair -- decides how the year before the quarter-end calendar year reads (R87, R97).
    named = {int(year) for year in _YEAR.findall(normal)}
    named |= {2000 + int(year) for year in [*_FISCAL_YEAR_LABEL.findall(normal), *re.findall(r"['\u2019](\d{2})\b", normal)]}
    fiscal_named = fiscal_year in named
    # A bare year names the current column when it is the fiscal year OR the calendar year of the quarter end
    # (a Q1 FY2027 column reads "2026"), the prior column when it is the year before the fiscal year, or the year
    # before the calendar year in a calendar reading (R87); a year that qualifies an ordinal quarter, and a
    # fiscal-year label, compare to the fiscal year alone (R72).
    years = [*label_years, *bare_years]
    # An untailed ordinal quarter names the admitted quarter only beside the fiscal year, alone, or beside the
    # fiscal year and its prior ("Fourth Quarter Segment Results 2026 vs. 2025"); any other year is foreign (R76).
    other_years_foreign = any(year != fiscal_year and not (year == fiscal_year - 1 and fiscal_year in years) for year in years)
    for match in quarter_words:
        ordinal = _ORDINAL_INDEX[match.group(1).casefold()]
        tail = match.group(2) or match.group(3)
        if tail is not None:
            verdicts.append(_quarter_year_verdict(ordinal, 2000 + int(tail), quarter, fiscal_year))
        else:
            verdicts.append("scope" if ordinal == quarter and not other_years_foreign else "foreign")
    verdicts.extend("fiscal" if year == fiscal_year else "foreign" for year in label_years)
    for match in dates:
        verdicts.append(_date_verdict(_match_date(match), current_end, prior_end, "year"))
    for year in bare_years:
        if year == fiscal_year:
            verdicts.append("year")
        elif year == current_end.year:
            # The quarter-end calendar year of a Q1/Q2 release: the current column in a calendar-year band, the
            # prior fiscal year beside "2027" -- ambiguous on its own (R76).
            verdicts.append("calendar")
        elif year == fiscal_year - 1 or (year == current_end.year - 1 and not fiscal_named):
            # Beside the fiscal year, the calendar year before the quarter end is two fiscal years back: "2025" in
            # "... 2027 versus 2025" and in "... 2027 vs. 2026 vs. 2025" of a Q1 FY2027 release is another table
            # (R87, R97).
            verdicts.append("prior")
        else:
            verdicts.append("foreign")
    # A bare "quarter" / "quarterly" that is ALL the residual beside a recognised quarter form is a caption word
    # ("Quarter" over a "Three Months Ended ..." stack); "Next Quarter" is not (R72).
    if quarter_forms and " ".join(residual.split()) in {"quarter", "quarterly"}:
        residual = " "
    return verdicts, residual


def period_context(text: str, identity: tuple[int, int, date], *, bare_fiscal_is_annual: bool = True) -> str | None:
    """Classify a heading, caption, header band, section label, paragraph label or sentence against the
    admitted fiscal scope (R27, R44, R50, R62, R67) -- fail-closed as a RULE, not a list of places.

    ``"unknown"`` whenever the text still carries a period token (a year, a month, a quarter number, a period
    word) after every recognised form is removed -- an unreadable date beside a readable one, "Q3 2026",
    "3Q26", "Prior Quarter", "January to March 2026".  Otherwise ``"annual"`` for cumulative / full-year forms;
    ``"scope"`` when a recognised form names the admitted quarter (an ordinal quarter with or without an
    attached fiscal-year tail, Q-FY, "Three Months / Quarter Ended|Ending <date>", the drivers heading, a bare
    admitted quarter-end date), even beside a readable foreign clause ("... Results and Fiscal Year 2027
    Outlook"); ``"foreign"`` when it names another readable period; ``"annual"`` for a bare label of the
    admitted fiscal year with no quarter; ``None`` when it carries no period information at all.
    """
    normal = _normal(text)
    verdicts, residual = _period_forms(normal, identity)
    if _PERIOD_TOKEN.search(residual):
        return "unknown"
    for verdict in ("annual", "scope", "foreign"):
        if verdict in verdicts:
            return verdict
    # A prior year is neutral only BESIDE the admitted year ("2026 vs 2025"); alone it names the prior period.  A
    # bare calendar year that is not the fiscal year is ambiguous alone (R76).
    if "prior" in verdicts and not ({"year", "fiscal", "calendar"} & set(verdicts)):
        return "foreign"
    if "prior_quarter" in verdicts:
        return "foreign"
    if "calendar" in verdicts and not ({"year", "fiscal"} & set(verdicts)):
        return "unknown"
    if "fiscal" in verdicts and bare_fiscal_is_annual:
        return "annual"
    return None


def band_context(text: str, identity: tuple[int, int, date]) -> str | None:
    """``period_context`` for a table's own text -- a band cell, a caption, a section row -- where a bare admitted
    year or quarter-end date names the CURRENT column ("2026" beside "2025") rather than a year-level signal
    (R37, R67)."""
    normal = _normal(text)
    verdicts, residual = _period_forms(normal, identity)
    if _PERIOD_TOKEN.search(residual):
        return "unknown"
    for verdict in ("annual", "scope", "foreign"):
        if verdict in verdicts:
            return verdict
    if "year" in verdicts or "calendar" in verdicts:
        return "scope"
    if "prior" in verdicts or "prior_quarter" in verdicts:
        return "foreign"
    return "annual" if "fiscal" in verdicts else None


def _has_scope_form(text: str, identity: tuple[int, int, date]) -> bool:
    """True when a recognised form in ``text`` names the admitted quarter, whatever else the text says."""
    verdicts, _residual = _period_forms(_normal(text), identity)
    return "scope" in verdicts


def _is_heading(block: Any) -> bool:
    return getattr(block, "kind", None) is not None and block.kind.value == "heading"


def _is_paragraph(block: Any) -> bool:
    return getattr(block, "kind", None) is not None and block.kind.value == BlockKind.PARAGRAPH.value


def _period_label_text(text: str) -> str:
    """A period label stripped of its decoration: the closed decoration set ("(Unaudited)", "(In millions)", a
    footnote mark), the word "unaudited", dashes, colons, semicolons and parentheses anywhere, a leading "For
    the", edge punctuation (R56, R62, R82).  Words inside any other parenthetical are kept."""
    normal = _LABEL_NOISE.sub(" ", _DECORATION.sub(" ", _normal(text)))
    normal = _LABEL_PREFIX.sub("", " ".join(normal.split()))
    return normal.strip(" .,")


_WORD_EDGE = ",.;:/()[]{}\"'"


def _residual_words(text: str, identity: tuple[int, int, date] | None) -> tuple[list[str], list[str]]:
    """The recognised period-form verdicts of ``text`` and the words left once those forms, decoration and
    glue are removed (R73)."""
    stripped = _period_label_text(text)
    verdicts, residual = _period_forms(stripped, identity) if identity is not None else ([], stripped)
    words = [word.strip(_WORD_EDGE) for word in residual.split()]
    return verdicts, [word for word in words if word and word not in _HEADING_GLUE]


def _is_pure_period(text: str, identity: tuple[int, int, date] | None = None) -> bool:
    """A text that is nothing but recognised period forms and glue -- "Three Months Ended June 30, 2026",
    "Three Months Ended March 31, 2026 and 2025", "For the Fourth Quarter Fiscal Year 2026:" -- whatever period it
    names (R50, R73)."""
    verdicts, words = _residual_words(text, identity)
    return bool(verdicts) and not words


PG_LABEL_CONTENT_WORDS = 3
# An explicit period token names a period on its own -- unlike "quarter" or "year", which need context (R84).
_EXPLICIT_PERIOD_TOKEN = re.compile(
    r"\b(?:19|20)\d{2}\b|(?<![\w])['\u2019]\d{2}\b|\b" + _MONTH_WORD + r"\b|\b\d{0,2}[\s-]*q[\s-]*[1-4]\w*\b|\b[1-4]q\d*\b"
    r"|\bfy\s*['\u2019]?\d|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}|\b[12]h\d*\b|\bh[12]\b",
    re.IGNORECASE,
)


def _pure_period_label(block: Any, identity: tuple[int, int, date] | None = None) -> bool:
    """A paragraph that is a period LABEL rather than prose (R50, R67, R77): it carries a year, a month, a
    quarter number or a period-form word, and once recognised forms, decoration, glue and period tokens are
    removed at most ``PG_LABEL_CONTENT_WORDS`` words remain -- whatever its punctuation ("Q3 2026." is a label,
    "Diluted EPS was $3.07 for the quarter." is prose).  A label is classified in full -- an unreadable one
    refuses what follows -- while prose only refuses on a readable foreign or cumulative form."""
    if not _is_paragraph(block) or identity is None:
        return False
    text = _period_label_text(_normal(getattr(block, "text", "") or ""))
    if not text or _STRONG_PERIOD_TOKEN.search(text) is None:
        return False
    _verdicts, words = _residual_words(text, identity)
    return len([word for word in words if _PERIOD_TOKEN.fullmatch(word) is None]) <= PG_LABEL_CONTENT_WORDS


def _admits(text: str, route: str, identity: tuple[int, int, date] | None) -> bool:
    """Positive admission (R73): ``text`` names the admitted quarter or no period at all (its recognised forms
    are scope, year-level or prior-comparison forms; nothing unreadable remains), and every other word belongs to
    ``route``'s vocabulary, which must contain the route's key word when it has one.  The quarterly route
    additionally requires a scope form.  "Looking Ahead: Segment Organic Sales", "TTM Segment Results",
    "Segment Results vs. Expected" and "Supplemental Synthetic Data" admit nothing."""
    verdicts, words = _residual_words(text, identity)
    if any(verdict in {"annual", "foreign"} for verdict in verdicts):
        return False
    # A bare fiscal-year label, or a bare year outside the year-level drivers heading, names a year, not the
    # admitted quarter: "Fiscal Year 2026 Segment Results" is an annual table.  The drivers heading is year-level
    # (R35) only when it names the admitted FISCAL year as a bare year, alone or beside its prior; a prior year
    # alone ("... Drivers 2025") or an ambiguous calendar year ("... Drivers 2026" in Q1 FY2027) names another
    # table (R76).
    if "prior_quarter" in verdicts and "scope" not in verdicts:
        return False
    year_level = {"fiscal", "year", "prior", "calendar"} & set(verdicts)
    if year_level and "scope" not in verdicts:
        if route != "drivers" or "year" not in verdicts or year_level - {"year", "prior"}:
            return False
    if _PERIOD_TOKEN.search(" ".join(words)):
        return False
    keys, vocabulary = _ROUTE_WORDS[route]
    if any(word not in vocabulary for word in words):
        return False
    if keys and not any(word in keys for word in words):
        return False
    if route == "quarterly" and "scope" not in verdicts:
        return False
    return True


def _is_admitted_heading(text: str, identity: tuple[int, int, date] | None) -> bool:
    """A section heading that positively names results of the admitted quarter -- a pure period label naming
    it, or a heading some route admits (R68, R73).  Everything else opens a section no table binds from."""
    if identity is None:
        return True
    if _is_pure_period(text, identity) and period_context(text, identity) in {"scope", None}:
        return True
    return any(_admits(text, route, identity) for route in _ROUTE_WORDS)


def _is_forward_caption(text: str, identity: tuple[int, int, date] | None) -> bool:
    """A caption naming a forward-looking view and not the admitted quarter (R63)."""
    normal = _normal(text)
    if not normal or not _names_forward(text):
        return False
    return identity is None or not _has_scope_form(normal, identity)


def _heading_level(block: Any) -> int:
    """The heading's level for section hierarchy: h1..h6 as written, a promoted or plain-text heading as 2."""
    level = int(getattr(block, "heading_level", 0) or 0)
    return level if 1 <= level <= 6 else 2


# The closed set of topic words an ancestor heading may consist of without naming a period or a view (R77):
# "Overview", "Financial Highlights", "Business Summary".  Anything else -- "Ambitions", "Priorities", "Cumulative
# Results" -- is not evidence of the admitted quarter's results and refuses the tables beneath it.
_NEUTRAL_WORDS = frozenset({"overview", "highlights", "highlight", "summary", "key", "financial", "financials", "business", "results", "result", "company"})
# Words a table's own caption or short label may add beyond the route, neutral and period vocabularies: units
# and presentation notes (R83).
_UNITS_WORDS = frozenset({"amounts", "amount", "in", "millions", "thousands", "billions", "except", "per", "share", "data", "dollars", "usd", "us$", "$", "percent", "%", "unaudited", "and", "of", "the", "table", "tables"})
# A table label may name the issuer: "The Procter & Gamble Company and Subsidiaries" (R89).
_MASTHEAD_WORDS = frozenset({"procter", "&", "gamble", "p&g", "subsidiaries"})
_ALL_ROUTE_WORDS = frozenset(word for _keys, vocabulary in _ROUTE_WORDS.values() for word in vocabulary)
# A metric's own basis words a label over its table may carry (R90): "Core" and "Non-GAAP" head the core EPS
# measures, never GAAP diluted EPS.
_LABEL_BASIS_WORDS = {"core_non_gaap": frozenset({"core", "non-gaap"})}
# Labels are read positively (R89, R90); prose is narrative -- the frozen P5, Q31, S16 and S17 bind beside it -- so
# two closed lexicons are the only reading prose allows (R99).  A PRESENTATION basis -- another entity or another
# accounting -- refuses the table for every metric.
_PRESENTATION_BASIS = re.compile(
    r"\b(?:pro[\s-]*forma|(?:combined|merged)[\s-]*(?:company|companies|results?|basis|entity|entities|group|business(?:es)?|operations)"
    r"|(?:post|pre)[\s-]*(?:acquisitions?|mergers?|combinations?|transactions?)|as[\s-]*(?:though|if)|giv(?:e|es|en|ing)[\s-]*effect"
    r"|supplemental|illustrative|hypothetical|re[\s-]*cast(?:s|ing)?|re[\s-]*stat(?:e|es|ed|ing|ements?)|successor|predecessor)\b"
)
# A MEASURE basis describes the organic and core measures and changes the basis of every reported one, so prose may
# name it only beside a metric whose own basis it is -- as R90 reads "Core" and "Non-GAAP" in a label (R99).
_MEASURE_BASIS = re.compile(
    r"\b(?:non-gaap|core[\s-]*(?:diluted[\s-]*)?(?:basis|eps|earnings|results?|measures?)"
    r"|adjusted[\s-]*(?:diluted[\s-]*)?(?:basis|results?|eps|earnings|amounts|figures|measures?)"
    r"|as[\s-]*adjusted|exclud(?:e|es|ed|ing)|excl\b|exclusions?|constant[\s-]*currency|currency[\s-]*neutral|comparable[\s-]*basis"
    r"|before[\s-]+(?:special|one[\s-]*time|non[\s-]*recurring)[\s-]+items)\b"
)
_MEASURE_BASES = frozenset({"core_non_gaap", "core_non_gaap_reconciliation", "core_eps_growth", "organic_sales", "organic_volume"})


def _names_presentation(text: str, *, prose: bool = False) -> bool:
    """A presentation basis in ``text``, read through the lexicon reading; unreadable text names one (R106)."""
    lexicon = _lexicon_text(text, prose=prose)
    return lexicon is None or _PRESENTATION_BASIS.search(lexicon) is not None


def _phrase(text: str, *, prose: bool = False) -> str | None:
    lexicon = _lexicon_text(text, prose=prose)
    return None if lexicon is None else " ".join(lexicon.replace("&", " and ").split())


# A sentence that speaks about the table's presentation rather than narrating one of its figures (R107): "All per-share
# amounts in the table below are presented as Core EPS."
_DECLARATION_WORD = re.compile(
    r"\b(?:tables?|below|above|following|herein|present(?:s|ed)?|shown?|shows|stated?|states|reflect(?:s|ed)?|amounts?"
    r"|figures?|all|basis|bases)\b"
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")


def _measure_names(table: _Table) -> frozenset[str]:
    """A table's measure-bearing NAMES: its band cells and its value rows' names (R99, R107, R108)."""
    names = {_phrase(cell.text) for row in table.rows[: table.depth] for cell in row}
    names |= {
        _phrase(next((cell.text for cell in row if cell.text.strip()), ""))
        for row in table.rows[table.depth :]
        if _section_text(row) is None
    }
    return frozenset(name for name in names if name and _MEASURE_BASIS.search(name) is not None)


def _covered(sentence: str, names: frozenset[str]) -> bool:
    """Whether every measure-basis term in ``sentence`` lies inside a repetition of one of ``names``."""
    covered = [
        (found.start(), found.end())
        for name in names
        for found in re.finditer(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", sentence)
    ]
    return all(
        any(start <= match.start() and match.end() <= end for start, end in covered) for match in _MEASURE_BASIS.finditer(sentence)
    )


def _names_own_basis(prose: str, table: _Table) -> bool:
    """True when every measure-basis term in ``prose`` lies inside a repetition of one of the table's own column
    names or VALUE-row names, in a sentence that states a figure and declares nothing about the table's presentation:
    "Total P&G volume excluding acquisitions and divestitures increased 3%" names the table's "Volume Excluding
    Acquisitions & Divestitures" column, "Core EPS increased 5%" its "Core EPS" row.  "Amounts below exclude the
    acquired business", "All per-share amounts in the table below are presented as Core EPS." and a note row
    repeating the prose name the table's basis and refuse (R99, R107, frozen R32d)."""
    normal = _phrase(prose, prose=True)
    if normal is None:
        return False
    names = _measure_names(table)
    for sentence in _SENTENCE_SPLIT.split(normal):
        if _MEASURE_BASIS.search(sentence) is None:
            continue
        if _STATEMENT_FIGURE.search(sentence) is None or _DECLARATION_WORD.search(sentence) is not None:
            return False
        if not _covered(sentence, names):
            return False
    return True


# The document's own parts a sentence may name as its scope ("in this release", "amounts in this section") (R108).
_SCOPE_WORD = re.compile(r"\b(?:releases?|documents?|sections?|exhibits?|schedules?|attachments?|appendix|appendices)\b")


def _declares_measure(text: str, *, prose: bool) -> bool:
    """Whether ``text``, wherever it stands in the document, DECLARES a measure basis (R108): a sentence with a
    measure-basis term that speaks about a presentation or names a part of the document -- "All amounts in this
    release exclude restructuring charges." -- reaches every table.  Narrative about a measure ("Core EPS excludes
    an incremental charge of 0.20") reaches only the tables of its own sections.  Unreadable text declares one."""
    normal = _phrase(text, prose=prose)
    if normal is None:
        return True
    return any(
        _MEASURE_BASIS.search(sentence) is not None
        and (_DECLARATION_WORD.search(sentence) is not None or _SCOPE_WORD.search(sentence) is not None)
        for sentence in _SENTENCE_SPLIT.split(normal)
    )


# The closed notes a LABEL may be besides its vocabulary (R99): the dash convention, the rounding note and the
# lead-in ("The results for the quarter were as follows:").
_BENIGN_NOTE = re.compile(
    r"(?:note:\s*)?(?:in\s+(?:this|these|the)\s+tables?,?\s+)?(?:an?\s+)?dash(?:es)?\s+(?:means?|represents?|indicates?)\s+zero"
    r"(?:\s+(?:in|throughout)\s+(?:this|these|the)\s+tables?(?:\s+(?:above|below))?)?"
    r"|(?:amounts|totals|numbers|figures|percentages|sums)\s+may\s+not\s+(?:add|sum|foot|total)(?:\s+(?:up|across|down))?"
    r"\s+due\s+to\s+rounding"
    r"|(?:the\s+)?(?:following\s+tables?\s+(?:presents?|shows?|sets?\s+forth|summari[sz]es?)\s+(?:the\s+)?(?:results|amounts|figures)"
    r"|(?:results|amounts|figures)\s+(?:for\s+the\s+(?:quarter|period)\s+)?(?:were|are)\s+as\s+follows)"
)
# A figure makes a paragraph a statement, not a label: "Diluted EPS of $3.07, up 5% versus the prior year" (R99).
_STATEMENT_FIGURE = re.compile(r"\$\s?\d|\d(?:\.\d+)?\s?%|\d(?:\.\d+)?\s+percent\b")


def _table_label_admissible(text: str, identity: tuple[int, int, date] | None, vocabulary: frozenset[str] = _ALL_ROUTE_WORDS) -> bool:
    """A table's label -- its caption, or a label-shaped paragraph between the last heading or table and it -- must
    decompose into period forms and words of the neutral, units, masthead and glue vocabularies plus
    ``vocabulary``: the union of every route when the table is scanned, the plan's route and the metric's own basis
    words when it is admitted.  "The Procter & Gamble Company and Subsidiaries" is a masthead; "Pro Forma Combined"
    and "Supplemental Unaudited Pro Forma Combined Company Information" refuse every table; "Non-GAAP Results" and
    "Core Results" refuse GAAP diluted EPS (R83, R89, R90)."""
    verdicts, words = _residual_words(text, identity)
    if any(verdict in {"annual", "foreign"} for verdict in verdicts):
        return False
    allowed = _NEUTRAL_WORDS | _UNITS_WORDS | _MASTHEAD_WORDS | vocabulary
    return all(word in allowed for word in words) and _PERIOD_TOKEN.search(" ".join(words)) is None


# The profile's own row names a label row may repeat with its values left blank or dashed ("Beauty", "Total P&G")
# (R107); basis words are never among them.
_ROW_NAME_WORDS = frozenset({"beauty", "grooming", "health", "care", "fabric", "home", "baby", "feminine", "family", "total", "p&g", "and", "&"})


def _cell_label_admissible(text: str, identity: tuple[int, int, date] | None, vocabulary: frozenset[str] = _ALL_ROUTE_WORDS) -> bool:
    """A label CELL -- a band row's stub cell, or a label-only row above the table's last value row -- is read
    positively like a label (R107): beyond its period tokens, which the band and row contexts classify (R37, R51),
    every word must be of the label vocabularies or a profile row name, or it is a closed note.  "Pro Forma
    Combined", "Non-GAAP" and "As Adjusted:" refuse the table."""
    if _BENIGN_NOTE.fullmatch(_normal(text).strip().rstrip(".!:").strip()) is not None:
        return True
    _verdicts, words = _residual_words(text, identity)
    allowed = _NEUTRAL_WORDS | _UNITS_WORDS | _MASTHEAD_WORDS | _ROW_NAME_WORDS | vocabulary
    return all(word.strip(",") in allowed or _PERIOD_TOKEN.fullmatch(word) is not None for word in words)


def _cell_labels(rows: Sequence[Sequence[_Cell]], depth: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """A table's own label cells (R107): every band row's stub cell and every label-only row above its last value
    row, read positively; and its NOTE rows -- the label-only rows after its last value row -- which are read like
    prose, by the closed lexicons, because the frozen S02 binds beside a free-text footer note."""
    stubs = {id(row[0].origin): row[0].text for row in rows[:depth] if row and row[0].origin is not None and row[0].text.strip()}
    body = [(_section_text(row), row) for row in rows[depth:]]
    last = max((index for index, (text, _row) in enumerate(body) if text is None), default=-1)
    sections = [text for index, (text, _row) in enumerate(body) if text and index < last]
    notes = [text for index, (text, _row) in enumerate(body) if text and index > last]
    return tuple(dict.fromkeys((*stubs.values(), *sections))), tuple(dict.fromkeys(notes))


def _label_shaped(text: str) -> bool:
    """A paragraph around a table is a LABEL unless it ends in sentence punctuation or states a figure, whatever its
    length: "Pro Forma Combined Company Results for the Three Months Ended June 30, 2026" is a label; "Expectations
    are discussed below." and the bullet "Diluted EPS of $3.07, up 5% versus the prior year" are prose (R83, R89,
    R99)."""
    normal = _normal(text).rstrip()
    return not normal.endswith((".", "!", "?")) and _STATEMENT_FIGURE.search(normal) is None


def _label_admissible(text: str, identity: tuple[int, int, date] | None, vocabulary: frozenset[str] = _ALL_ROUTE_WORDS) -> bool:
    """A label is admissible when its words are (``_table_label_admissible``) or it is a closed note (R99)."""
    return _BENIGN_NOTE.fullmatch(_normal(text).strip().rstrip(".!:").strip()) is not None or _table_label_admissible(text, identity, vocabulary)


def _around_admissible(stretch: Sequence[tuple[str, bool]], caption: str, identity: tuple[int, int, date] | None) -> bool:
    """What stands around a table -- every paragraph between its topic heading (or the previous table) and the next
    topic heading (or table), period headings crossed (R89, R99, R101): the caption and every label must be
    admissible, and no prose paragraph may name a presentation basis ("Combined results are presented below.",
    "The table above presents pro forma combined company results."); a measure basis is read per metric by
    ``_candidate_tables``."""
    labels = [item for item in (caption, *(text for text, label in stretch if label)) if item and item.strip()]
    if any(not _label_admissible(item, identity) for item in labels):
        return False
    return not any(_names_presentation(text, prose=True) for text, label in stretch if not label)


def _table_labels(caption: str, items: Sequence[tuple[str, bool]]) -> tuple[str, ...]:
    """A table's caption and every label standing around it (R89, R101)."""
    return tuple(item for item in (caption, *(text for text, label in items if label)) if item and item.strip())


def _after_table(
    blocks: Sequence[Any], index: int, identity: tuple[int, int, date] | None
) -> tuple[list[tuple[str, bool]], bool, list[int]]:
    """The paragraphs after the table at ``index`` up to the next topic heading or table, each with whether it is a
    label, whether visible text the parser read into no block lies in that stretch (R100, R101), and their block
    indices."""
    stretch: list[tuple[str, bool]] = []
    indices: list[int] = []
    unread = bool(getattr(blocks[index], "unread_after", False))
    for offset, block in enumerate(blocks[index + 1:], start=index + 1):
        unread = unread or bool(getattr(block, "unread_before", False))
        text = getattr(block, "text", "") or ""
        if getattr(block, "table", None) is not None or (_is_heading(block) and not _is_pure_period(text, identity)):
            break
        unread = unread or bool(getattr(block, "unread_after", False))
        if _is_paragraph(block) and identity is not None:
            stretch.append((text, _label_shaped(text) or _pure_period_label(block, identity)))
            indices.append(offset)
    return stretch, unread, indices


def _section_owners(blocks: Sequence[Any], identity: tuple[int, int, date] | None) -> tuple[list[int | None], dict[int, int]]:
    """Each block's section -- the innermost open TOPIC heading before it (itself, for a topic heading), or None
    before the first -- and where each topic heading's section ends: at the next topic heading of the same or a
    higher level.  A pure period heading neither opens nor closes a section, as it ends no stretch (R99, R108)."""
    owners: list[int | None] = []
    ends: dict[int, int] = {}
    stack: list[tuple[int, int]] = []
    for index, block in enumerate(blocks):
        text = getattr(block, "text", "") or ""
        if _is_heading(block) and not _is_pure_period(text, identity):
            level = _heading_level(block)
            while stack and stack[-1][1] >= level:
                ends[stack.pop()[0]] = index
            stack.append((index, level))
        owners.append(stack[-1][0] if stack else None)
    for heading, _level in stack:
        ends[heading] = len(blocks)
    return owners, ends


def _is_neutral_topic(text: str, identity: tuple[int, int, date] | None) -> bool:
    """Neutral topic words with no period, the admitted quarter, or the admitted fiscal year's bare label ("Fiscal
    Year 2026 Highlights" heads a Q4 release's quarter AND year tables; the heading context keeps the quarter
    tables waiting for a scope heading) (R77, R82)."""
    verdicts, words = _residual_words(text, identity)
    if not words or any(word not in _NEUTRAL_WORDS for word in words):
        return False
    if identity is None:
        return True
    return period_context(text, identity) in {"scope", None} or set(verdicts) == {"fiscal"}


def _is_non_results_section(text: str, identity: tuple[int, int, date] | None) -> bool:
    """An ANCESTOR heading governs only by positive evidence (R63, R73, R77): it must be admitted by a route, be a
    pure label of the admitted quarter, or consist of neutral topic words ("Overview", "Financial Highlights").
    A forward-looking word, a period other than the admitted quarter, or any other topic ("Ambitions",
    "Cumulative Results") opens a section no table binds from."""
    if _names_forward(text):
        return True
    if _is_admitted_heading(text, identity):
        return False
    return not _is_neutral_topic(text, identity)


# A title's clauses: split at ";", ":", "|", a spaced dash, "and" and "&" (R93).
_TITLE_CLAUSE = re.compile(r"\s*[;:|]\s*|\s+[-\u2014\u2013]+\s+|\s+(?:and|&)\s+")
# A title clause names reported results by a results NOUN (R98, R110); a clause that also names a date, a call or
# a webcast announces an event, not results.
_RESULTS_WORD = re.compile(r"\b(?:results?|earnings)\b")
_SCHEDULE_WORD = re.compile(r"\b(?:dates?|calls?|webcasts?|conferences?|schedul(?:e|es|ed|ing)|timing|times?)\b")


def _is_non_results_title(block: Any, text: str, identity: tuple[int, int, date] | None) -> bool:
    """The TITLE -- a first heading block at level 1, a masthead naming the company -- is exempt from the topic
    rule only: a forward-looking word -- unless a clause without one names the admitted quarter's RESULTS and no
    clause with one names the admitted quarter -- or a period outside the admitted quarter, still opens a section
    (R77, R98).  A first heading at any deeper level is an ordinary ancestor (R82)."""
    if _heading_level(block) != 1:
        return _is_non_results_section(text, identity)
    normal = _normal(text)
    if _names_forward(text):
        # "Fourth Quarter Fiscal Year 2026 Results and Fiscal Year 2027 Outlook" heads the quarter; "Q4 Outlook",
        # "Fourth Quarter and Fiscal Year 2026 Outlook" and "Fourth Quarter Fiscal Year 2026 -- Outlook" name a view
        # of it (R98).
        if identity is None:
            return True
        clauses = [clause for clause in _TITLE_CLAUSE.split(normal) if clause.strip()]
        forward = [clause for clause in clauses if _names_forward(clause)]
        results = any(
            _RESULTS_WORD.search(clause) is not None and _SCHEDULE_WORD.search(clause) is None and _has_scope_form(clause, identity)
            for clause in clauses
            if clause not in forward
        )
        if not results or any(_has_scope_form(clause, identity) for clause in forward):
            return True
    return identity is not None and _marked_context(text, identity) in _EXCLUDED


class _SectionState:
    """Section hierarchy (R63, R68, R73): the SHALLOWEST open non-results heading governs every block after it
    until a heading of the same or a higher level; a deeper heading never releases it, nor does a paragraph
    label.  The document TITLE -- the first heading block, whatever its level -- is exempt from the topic rule
    (a masthead cannot refuse a release) but not from forward words or foreign periods (R77); a later h1 governs
    like any heading."""

    def __init__(self) -> None:
        self.level: int | None = None
        self.seen = 0

    def heading(self, block: Any, text: str, identity: tuple[int, int, date] | None) -> None:
        self.seen += 1
        level = _heading_level(block)
        if self.level is not None and level <= self.level:
            self.level = None
        governs = _is_non_results_title(block, text, identity) if self.seen == 1 else _is_non_results_section(text, identity)
        if governs:
            self.level = level if self.level is None else min(self.level, level)

    @property
    def active(self) -> bool:
        return self.level is not None


class _PeriodContext:
    """The two-layer period context (R73, R77).  Headings carry a persistent context: a heading that names a
    period sets it until another heading names one.  Paragraphs carry a context cleared at every heading: a
    period LABEL is classified in full and refuses when unreadable, foreign or cumulative, while a scope label
    sets scope only under a heading context of None or scope -- it never re-opens a quarter a heading closed;
    prose refuses only on a readable foreign or cumulative form."""

    def __init__(self, identity: tuple[int, int, date] | None) -> None:
        self.identity = identity
        self.heading_context: str | None = None
        self.paragraph_context: str | None = None

    def heading(self, text: str) -> None:
        self.paragraph_context = None
        verdict = _marked_context(text, self.identity) if self.identity is not None else None
        if verdict is not None:
            self.heading_context = verdict

    def label(self, text: str) -> None:
        if self.identity is None:
            return
        verdict = _marked_context(text, self.identity)
        if verdict == "scope":
            if self.heading_context in {None, "scope"}:
                self.paragraph_context = "scope"
        elif verdict is not None:
            self.paragraph_context = verdict

    def prose(self, text: str) -> None:
        if self.identity is None:
            return
        verdict = period_context(text, self.identity, bare_fiscal_is_annual=False)
        if verdict in _OUT_OF_SCOPE:
            self.paragraph_context = verdict

    @property
    def context(self) -> str | None:
        return self.paragraph_context if self.paragraph_context is not None else self.heading_context


def _table_scan(blocks: Sequence[Any], identity: tuple[int, int, date] | None) -> list[_Table]:
    """Every table as a grid with its governing headings (immediate + enclosing topic), its period context
    (``_PeriodContext``), its row sections and its section admissibility (R27, R50, R73, R77).  A table's own
    header band can only narrow the context (R37)."""
    period = _PeriodContext(identity)
    immediate: str | None = None
    topic: str | None = None
    # Everything since the last TOPIC heading or table stands before the next table; a pure period heading
    # ("Three Months Ended June 30, 2026") does not end the stretch (R99).
    before: list[tuple[str, bool]] = []
    before_indices: list[int] = []
    before_unread = False
    section = _SectionState()
    scanned: list[_Table] = []
    blocks = tuple(blocks)
    # A presentation basis anywhere in the document's visible text -- a heading, a paragraph, a caption or a cell of
    # any table -- or visible text the parser read into no block anywhere in it, makes every table unreadable: "All
    # amounts in this release are pro forma combined company results." reaches every table it names, wherever it
    # stands (R108).
    unreadable = identity is not None and any(
        getattr(block, "unread_before", False)
        or getattr(block, "unread_after", False)
        or _names_presentation(getattr(block, "text", "") or "", prose=_is_paragraph(block))
        or (getattr(block, "table", None) is not None and _names_presentation(getattr(block.table, "caption", "") or ""))
        for block in blocks
    )
    owners, ends = _section_owners(blocks, identity)
    for index, block in enumerate(blocks):
        text = getattr(block, "text", "") or ""
        if _is_heading(block):
            immediate = text
            if not _is_pure_period(text, identity):
                topic = text
                before, before_indices, before_unread = [], [], False
            else:
                before_unread = before_unread or bool(getattr(block, "unread_before", False))
            section.heading(block, text, identity)
            period.heading(text)
        elif _is_paragraph(block) and identity is not None:
            if _pure_period_label(block, identity):
                immediate = text
                if not _is_pure_period(text, identity):
                    topic = text
                period.label(text)
                item = (text, True)
            else:
                period.prose(text)
                item = (text, _label_shaped(text))
            before.append(item)
            before_indices.append(index)
            before_unread = before_unread or bool(getattr(block, "unread_before", False))
        elif getattr(block, "table", None) is not None:
            rows = _grid(block)
            depth = _header_band(rows)
            caption = getattr(block.table, "caption", "") or ""
            band = _band_context(rows, depth, caption, identity) if identity is not None else None
            if _layout_overflow(block) or getattr(block.table, "nested", False) or getattr(block.table, "contains_nested", False):
                band = "unknown"
            # Labels around the table are read positively and prose by closed lexicons; visible text the parser read
            # into no block -- before it, inside it or after it -- makes it unreadable (R99, R100, R101).
            after, after_unread, after_indices = _after_table(blocks, index, identity)
            around = (*before, *after)
            labels = _table_labels(caption, around)
            prose = tuple(text for text, label in around if not label)
            unread = before_unread or bool(getattr(block, "unread_before", False)) or after_unread
            cell_labels, notes = _cell_labels(rows, depth)
            if identity is not None and (
                unreadable
                or unread
                or not _around_admissible((*around, *((note, False) for note in notes)), caption, identity)
                or not all(_cell_label_admissible(text, identity) for text in cell_labels)
            ):
                band = "unknown"
            stretch_indices = {*before_indices, *after_indices}
            before, before_indices, before_unread = [], [], False
            row_context = _row_contexts(rows, depth, identity) if identity is not None else tuple([None] * len(rows))
            governing = tuple(dict.fromkeys(item for item in (immediate, topic) if item))
            # Every paragraph and topic heading of a section holding the table, beyond its stretch and its governing
            # headings: the title's section holds every table; a sibling section none (R108).
            section_prose = tuple(
                getattr(other, "text", "") or ""
                for position, other in enumerate(blocks)
                if position not in stretch_indices
                and (_is_paragraph(other) or (_is_heading(other) and position == owners[position]))
                and (getattr(other, "text", "") or "") not in governing
                and (owners[position] is None or owners[position] < index < ends[owners[position]])
            ) if identity is not None else ()
            scanned.append(
                _Table(
                    block, rows, depth, caption, governing, band if band in _EXCLUDED else period.context, row_context,
                    section.active or _is_forward_caption(caption, identity), labels, (*prose, *notes), cell_labels,
                    section_prose,
                )
            )
            immediate = None
            topic = None
    if identity is not None and scanned:
        # A sentence DECLARING a measure basis anywhere -- a heading, a paragraph, a caption, a stub cell, a section
        # row or a note row of any table -- reaches every table (R108).
        units = [
            (getattr(block, "text", "") or "", _is_paragraph(block)) for block in blocks if _is_heading(block) or _is_paragraph(block)
        ]
        for table in scanned:
            cells, notes = _cell_labels(table.rows, table.depth)
            units.extend([(table.caption, False), *((cell, False) for cell in cells), *((note, True) for note in notes)])
        if any(_declares_measure(text, prose=prose) for text, prose in units if text and text.strip()):
            scanned = [replace(table, declared_measure=True) for table in scanned]
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
        if _is_heading(block) or _pure_period_label(block, identity):
            text = getattr(block, "text", "")
            years = _DRIVERS_YEARS.search(_normal(text))
            drivers = years is not None and _drivers_pair(years, fiscal_year)
            verdict = "scope" if drivers else _marked_context(text, identity)
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
    # A bare year names a column in ONE of two readings (R76): the fiscal year ("2027" beside "2026" in a Q1
    # FY2027 release) or the quarter-end calendar year ("2026" beside "2025").  Both spellings are forms; the
    # band's own reading decides which applies (``_band_headers``).
    current_forms = (
        current_end.isoformat(),
        str(fiscal_year),
        *([str(current_end.year)] if current_end.year != fiscal_year else []),
        f"Q{quarter} FY{fiscal_year}",
        current_date,
        f"Three Months Ended {current_date}",
    )
    prior_forms = (
        prior_end.isoformat(),
        str(fiscal_year - 1),
        *([str(prior_end.year)] if prior_end.year != fiscal_year - 1 else []),
        f"Q{quarter} FY{fiscal_year - 1}",
        prior_date,
        f"Three Months Ended {prior_date}",
    )
    return quarterly_headings, driver_headings, current_forms, prior_forms


def _admissible_table(table: _Table) -> bool:
    """An in-scope table that no non-results heading or forward caption governs (R54, R63, R73)."""
    return table.context not in _EXCLUDED and not table.forward


def _route_for(headings: Sequence[str]) -> str:
    """The admission route a plan's heading rule names (R73)."""
    first = _normal(headings[0]) if headings else ""
    if first == "segment":
        return "segment"
    if first.startswith("net sales change drivers"):
        return "drivers"
    return "quarterly"


def _candidate_tables(
    tables: Sequence[_Table], headings: Sequence[str], identity: tuple[int, int, date] | None = None, basis: str | None = None
) -> list[_Table]:
    """The in-scope tables a route admits: a governing heading must decompose into recognised period forms plus
    that route's vocabulary (R27, R73), every label of the table into the route's vocabulary plus the words of the
    metric's ``basis`` (R90), and no prose around it may name a measure basis the metric does not have, outside a
    repetition of the table's own row or column names (R99), nor may any section that holds it, nor a declaration
    anywhere in the document (R108)."""
    route = _route_for(headings)
    vocabulary = _ROUTE_WORDS[route][1] | _LABEL_BASIS_WORDS.get(basis or "", frozenset())
    return [
        table
        for table in tables
        if _admissible_table(table)
        and any(_admits(heading, route, identity) for heading in table.governing)
        and (identity is None or all(_label_admissible(label, identity, vocabulary) for label in table.labels))
        and (identity is None or all(_cell_label_admissible(label, identity, vocabulary) for label in table.cell_labels))
        and (
            basis is None
            or basis in _MEASURE_BASES
            or (not table.declared_measure and all(_names_own_basis(text, table) for text in (*table.prose, *table.section_prose)))
        )
    ]


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
    drivers = _candidate_tables(tables, (driver_headings[0],), (fiscal_year, quarter, current_end))
    return len(drivers) == 1 and _combined_presentation(drivers[0])


# A band cell that does not tell spanned columns apart (R64, R69): a bare "$", "(unaudited)", or a footnote mark
# such as "(a)", "(1)", "(*)".  "(Restated)" and "(As Reported)" DO tell them apart.
# A currency sign, "(unaudited)", or footnote marks -- digits, a digit-letter such as "(1a)", ONE letter, a roman
# numeral, asterisks, daggers, stacked or bare; never a two-letter code such as "(py)" (R74, R79).
_PLAIN_SUBCELL = re.compile(
    r"(?:us|ca|au|nz|hk|sg)?\$|\u20ac|\u00a3|\u00a5|\u2020|\u2021|\*{1,3}"
    r"|(?:\((?:unaudited|\d{1,2}[a-z]?|[a-z]|[ivx]{2,4}|\*{1,3}|\u2020|\u2021)\))+"
)


def _column(
    table: _Table, row_label: str, headers: Sequence[str], identity: tuple[int, int, date] | None = None, *,
    current: bool = True, fiscal_mode: bool | None = None,
) -> tuple[Sequence[_Cell], int, str] | None:
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
        plain = all(_PLAIN_SUBCELL.fullmatch(_normal(item)) is not None for item in residual)
        columns.append((column, form, key, plain))
    if len(columns) > 1 and len({key for _column_index, _form, key, _plain in columns}) == 1:
        spanned = [column for column, _form, _key, _plain in columns if column < len(row)]
        literal = [column for column in spanned if _is_literal_cell(row[column].text)]
        others_clean = all(_normal(row[column].text) in {"", "$"} for column in spanned if column not in literal)
        distinct = not all(plain for _column_index, _form, _key, plain in columns)
        columns = [item for item in columns if item[0] in literal] if len(literal) == 1 and others_clean and not distinct else []
    if len(columns) != 1 or columns[0][0] >= len(row):
        return None
    column, form, _key, plain = columns[0]
    # The whole stack over the matched column must decompose into the matched form, period forms and plain
    # marks: "Pro Forma", "As Reported" or "Diluted" over one column names a basis, not the observation (R79).
    # Which period the stack names is judged elsewhere (the matched form, ``band_context``, the row section).
    stack = " ".join(cell.text.strip() for cell in _column_header_cells(rows, depth, column))
    if not plain:
        _verdicts, stack_words = _residual_words(stack, identity)
        _form_verdicts, form_words = _residual_words(form, identity)
        leftover = Counter(stack_words) - Counter(form_words)
        if identity is None or any(_PLAIN_SUBCELL.fullmatch(word) is None for word in leftover.elements()):
            return None
    # The matched column's OWN stack must name this observation's period or no period at all: a current
    # observation never binds a column stacked under "Three Months Ended June 30, 2025", a prior observation never
    # a column stacked under the admitted quarter (R84).
    if identity is not None and not _stack_period_agrees(stack, identity, current=current, fiscal_mode=fiscal_mode):
        return None
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
    prior_plan = definition.metric in _EPS_METRICS and definition.metric.startswith("pg_prior_")
    # A spelling shared by both periods ("2026" is the calendar current year AND the prior fiscal year of a Q1
    # FY2027 release) means THIS observation's own period (R76).
    own, other = ((prior_forms, prior_end), (current_forms, current_end)) if prior_plan else ((current_forms, current_end), (prior_forms, prior_end))
    periods = {_normal(form): endpoint.isoformat() for forms, endpoint in (other, own) for form in forms}
    if definition.metric in _EPS_METRICS:
        forms = own[0]
        return _Plan(tuple(quarterly_headings), tuple(forms), periods, periods[_normal(forms[0])])
    if definition.row_label is not None and definition.column_label is not None:
        return _Plan((driver_headings[0],), tuple(current_forms), periods, current_end.isoformat())
    if definition.metric.endswith("_organic_sales_growth_pct") and definition.row_label is not None:
        return _Plan(("Segment",), tuple(current_forms), periods, current_end.isoformat())
    return None


def _select_cell(
    tables: Sequence[_Table], definition: PGDefinition, plan: _Plan, identity: tuple[int, int, date] | None = None
) -> tuple[_Table, Sequence[_Cell], int, str] | None:
    """Exactly ONE (table, row, column) across every admitted table may address the observation (R42)."""
    row_label = definition.row_label or plan.header_forms[0]
    located = [
        (table, *found)
        for table in _candidate_tables(tables, plan.headings, identity, definition.basis)
        if (found := _column(
            table, row_label, _band_headers(table, definition, plan, identity), identity,
            current=identity is None or plan.preferred_period != _prior_quarter_end(identity[2]).isoformat(),
            fiscal_mode=_fiscal_mode(table, identity),
        )) is not None
    ]
    return located[0] if len(located) == 1 else None


def _stack_period_agrees(stack: str, identity: tuple[int, int, date], *, current: bool, fiscal_mode: bool | None) -> bool:
    """The matched column's stack names this observation's period or none (R84).  Under the fiscal reading of a
    Q1/Q2 band the bare quarter-end calendar year is the prior column."""
    verdicts, residual = _period_forms(_period_label_text(stack), identity)
    if _PERIOD_TOKEN.search(residual) is not None:
        return False
    found = set(verdicts)
    if fiscal_mode and "calendar" in found:
        found = (found - {"calendar"}) | {"prior"}
    if current:
        if found & {"annual", "foreign", "fiscal"} or ("prior_quarter" in found and "scope" not in found):
            return False
        return not found or bool(found & {"scope", "year", "calendar"})
    return found <= {"prior", "prior_quarter"}


def _band_years(table: _Table) -> set[int]:
    """The bare years of the band's PURE-year columns -- a column whose stack is a bare year and plain marks --
    the only columns a bare-year form can match; "2027 Guidance" beside "2026 | 2025" decides nothing (R81)."""
    rows, depth = table.rows, table.depth
    years: set[int] = set()
    for column in range(1, _band_width(rows, depth)):
        words = _period_label_text(" ".join(cell.text.strip() for cell in _column_header_cells(rows, depth, column))).split()
        bare = [word for word in words if _YEAR.fullmatch(word)]
        if len(bare) == 1 and all(_PLAIN_SUBCELL.fullmatch(word) is not None for word in words if not _YEAR.fullmatch(word)):
            years.add(int(bare[0]))
    return years


def _fiscal_mode(table: _Table, identity: tuple[int, int, date] | None) -> bool | None:
    """The band's year reading (R76, R81): None when the fiscal and quarter-end calendar years coincide, True when
    the admitted fiscal year appears among the band's pure-year columns, False (calendar reading) otherwise."""
    if identity is None:
        return None
    fiscal_year, _quarter, current_end = identity
    if current_end.year == fiscal_year:
        return None
    return fiscal_year in _band_years(table)


def _band_headers(table: _Table, definition: PGDefinition, plan: _Plan, identity: tuple[int, int, date] | None) -> tuple[str, ...]:
    """The header forms that may name this observation's column in ``table`` (R76).  A band is read in ONE year
    reading: when the admitted FISCAL year appears among its bare years, every bare year is a fiscal year (the
    quarter-end calendar year is then the PRIOR column); otherwise bare years are calendar years.  The bare-year
    form of the other reading is dropped, so "2026" beside "2027" can never be a Q1 FY2027 current column."""
    if definition.column_label:
        return (definition.column_label,)
    if identity is None:
        return plan.header_forms
    fiscal_year, _quarter, current_end = identity
    fiscal_mode = _fiscal_mode(table, identity)
    if fiscal_mode is None:
        return plan.header_forms
    current = plan.preferred_period == current_end.isoformat()
    expected = (fiscal_year if current else fiscal_year - 1) if fiscal_mode else (current_end.year if current else current_end.year - 1)

    def keep(form: str) -> bool:
        match = _YEAR.fullmatch(_normal(form))
        return match is None or int(match.group(1)) == expected

    return tuple(form for form in plan.header_forms if keep(form))


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
    identity = _identity(current_start, current_end)
    tables = _table_scan(parse_release_blocks(source), identity)
    located = _select_cell(tables, definition, plan, identity)
    if located is None:
        return None
    _table, row, column, header = located
    return row[column], header, column, plan.period_for(header)


def pg_observation_present(source: str, definition: PGDefinition, *, current_start: date, current_end: date, prior_end: date) -> bool:
    """Whether the extractor's own decision path yields a PRESENT value for ``definition`` in ``source`` (R80,
    R85): the document verdict, the admitted tables, the unique cell, its literal and dash convention, the receipt
    for its bytes, the layout replay and the total-volume cross-check -- or, for the bounded text, the unique
    reconciliation paragraph and its receipt.  The validator refuses a typed absence that hides such a value
    (round-6 disposition (a))."""
    identity = _identity(current_start, current_end)
    blocks = parse_release_blocks(source)
    if document_period_verdict(blocks, identity) in _OUT_OF_SCOPE:
        return False
    if definition.value_kind == "bounded_text":
        paragraph = _reconciliation_paragraph(blocks, definition, identity)
        if paragraph is None:
            return False
        span = getattr(paragraph, "source_span", None)
        text = (paragraph.text or "").strip()
        return span is not None and expected_receipt_span(source, span.char_start, span.char_end, text) is not None
    plan = _observation_plan(definition, current_start, current_end, prior_end)
    if plan is None:
        return False
    tables = _table_scan(blocks, identity)
    located = _select_cell(tables, definition, plan, identity)
    if located is None:
        return False
    table, row, column, matched_header = located
    cell = row[column]
    literal = cell.text.strip()
    is_dash = literal in _DASHES
    if not literal or (is_dash and not neutral_zero_convention(source)):
        return False
    value = 0.0 if is_dash else parse_pg_literal(literal, unit=definition.unit)
    if value is None or not math.isfinite(value):
        return False
    headers = (definition.column_label,) if definition.column_label else plan.header_forms
    # The extractor mints a receipt for the literal's bytes; a literal it cannot receipt (an entity, a comment
    # inside the cell) is absent for it, so it is absent here (R85).
    receipt = expected_receipt_span(source, cell.char_start, cell.char_end, literal)
    if receipt is None:
        return False
    try:
        start, end = receipt
        replayed_row, replayed_header, _column_index = replay_table_layout(source, start=start, end=end, header_forms=headers, identity=identity)
    except ValueError:
        return False
    if _normal(replayed_row) != _normal(definition.row_label or plan.header_forms[0]) or _normal(replayed_header) != _normal(matched_header):
        return False
    if definition.metric == "pg_total_volume_growth_pct" and not _volume_cross_check(tables, blocks, value=value, identity=identity, skip=table):
        return False
    return True


def pg_volume_cross_check(source: str, *, value: float, current_start: date, current_end: date, prior_end: date) -> bool:
    """The validator's replay of the total-volume cross-check (R52): every other same-period statement of Total
    P&G volume in ``source`` must agree with ``value``; False when the observation is not even addressable."""
    definition = next(item for item in PG_DEFINITIONS if item.metric == "pg_total_volume_growth_pct")
    plan = _observation_plan(definition, current_start, current_end, prior_end)
    identity = _identity(current_start, current_end)
    blocks = parse_release_blocks(source)
    tables = _table_scan(blocks, identity)
    located = _select_cell(tables, definition, plan, identity) if plan is not None else None
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
    candidates = _candidate_tables(tables, plan.headings, identity, definition.basis)
    headers = (definition.column_label,) if definition.column_label else plan.header_forms
    located = _select_cell(tables, definition, plan, identity)
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
_VOLUME_COLUMN_QUALIFIERS = ("excluding", "organic", "mix")


# A year-level phrase with no year number: "this fiscal year", "for the fiscal year", "the full fiscal year" (R94).
_YEAR_LEVEL_PHRASE = re.compile(
    r"\b(?:this|the)\s+(?:full\s+|current\s+|entire\s+)?fiscal[\s-]+year\b"
    r"(?![\s-]+(?:ago|ended|ending|to[\s-]+date)\b|[\s-]*['\u2019]?\s*(?:20)?\d{2}\b)"
)


def _other_period_sentence(sentence: str, identity: tuple[int, int, date]) -> bool:
    """A sentence that names a readable other period, or an unreadable one by an EXPLICIT token -- a year, a
    month, a quarter number, a date ("in Q3 2026") -- is not a same-period statement; nor is one whose ONLY period
    reference is a year-level phrase ("increased 4% for the fiscal year").  A sentence that merely says "the
    quarter", "this quarter" or "last year" is, and conflicts (R47, R79, R84, R94)."""
    verdict = period_context(sentence, identity)
    if verdict in _OUT_OF_SCOPE:
        return True
    if verdict != "unknown":
        return False
    verdicts, residual = _period_forms(_normal(sentence), identity)
    if _EXPLICIT_PERIOD_TOKEN.search(residual) is not None:
        return True
    stripped = _YEAR_LEVEL_PHRASE.sub(" ", residual)
    return "scope" not in verdicts and stripped != residual and _PERIOD_TOKEN.search(stripped) is None


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
    period = _PeriodContext(identity)
    forward = _SectionState()
    for block in blocks:
        if _is_heading(block):
            forward.heading(block, getattr(block, "text", ""), identity)
            period.heading(getattr(block, "text", ""))
        elif _pure_period_label(block, identity):
            period.label(getattr(block, "text", ""))
        elif period.context not in _OUT_OF_SCOPE and not forward.active and _is_paragraph(block):
            for sentence in _SENTENCE_SPLIT.split(_normal(getattr(block, "text", ""))):
                if not _TOTAL_PG.search(sentence) or _other_period_sentence(sentence, identity):
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
    period = _PeriodContext(identity)
    forward = _SectionState()
    paragraphs = []
    metric_name = _normal(definition.row_label or "")
    for block in blocks:
        if _is_heading(block):
            normal = _normal(getattr(block, "text", ""))
            forward.heading(block, normal, identity)
            active = _admits(normal, "reconciliation", identity) and (metric_name in normal or "non-gaap" in normal) and not forward.active
            period.heading(normal)
        elif _pure_period_label(block, identity):
            # A period label under the reconciliation heading refines its period; it never switches the section
            # off (R79).
            period.label(_normal(getattr(block, "text", "")))
        # A reconciliation paragraph carried under another quarter's heading -- or under a heading whose period
        # cannot be read, or inside a forward-looking section -- is not this quarter's statement (R35, R55, R63);
        # a twelve-month heading does not refuse it, because a Q4 release's non-GAAP section covers both periods.
        elif active and period.context not in {"foreign", "unknown"} and _is_paragraph(block):
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
    if pg_envelope._wrapped(source):
        admission = pg_envelope.admit(source, fiscal_scope)
        document = pg_envelope._document(source)
        return pg_envelope.extract(document, admission, PG_DEFINITIONS, bound=bound, document_id=document_id, event_id=event_id, fiscal_period=fiscal_period, fiscal_scope=fiscal_scope)
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


__all__ = ["PG_BOUNDED_TEXT_MAX", "PG_COMBINED_VOLUME_MIX_METRICS", "PG_DEFINITIONS", "PG_METRIC_KEYS", "combined_volume_mix_presentation", "document_period_verdict", "extract_pg_release_facts", "expected_receipt_span", "locate_pg_observation", "neutral_zero_convention", "parse_release_blocks", "period_context", "pg_issuer", "pg_observation_present", "pg_private_registry", "pg_profile", "pg_reconciliation_paragraph", "pg_volume_cross_check", "replay_table_layout", "visible_text"]
