"""Finite-source envelope for wrapped P&G quarterly release exhibits."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import functools
import html
import math
import re
import unicodedata
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from .pg_profile import PGDefinition

from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import receipt_for_char_span


_TABLE_OPEN = re.compile(r"<table\b", re.I)
_TABLE_CLOSE = re.compile(r"</table\s*>", re.I)
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr\s*>", re.I | re.S)
_CELL = re.compile(r"<t([dh])\b([^>]*)>(.*?)</t\1\s*>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_SPAN_PATTERNS = {key: re.compile(key + r"\s*=\s*[\"']?(\d+)", re.I) for key in ("colspan", "rowspan")}
_LETTERS = re.compile(r"[A-Za-z].*[A-Za-z]", re.S)
_NOT_A_LABEL = {"n/a", "na", "nm", "bps"}
_UNIT_CELLS = {"$", "%"}
_DASH = "\u2014"
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_UNIT = re.compile(r"(<!--.*?-->)|(<[^>]+>)|(&(?:#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?))|([^<&]+|[<&])", re.S)
_FOLD_NUMBERS = re.compile(rf"(?:{_DASH}%?|[-+%$(]?\d+(?:[.,]\d+)*%?)")
_HTML_SPACE = "[ \t\n\r\f]"
_ATTRIBUTE = re.compile(
    rf"{_HTML_SPACE}+([A-Za-z_:][A-Za-z0-9_:.-]*)"
    rf"(?:{_HTML_SPACE}*={_HTML_SPACE}*(?:\"([^\"<>]*)\"|'([^'<>]*)'|([^ \t\n\r\f\"'=<>`]+)))?"
)
_START_TAG = re.compile(
    rf"<([A-Za-z][A-Za-z0-9]*)((?:{_HTML_SPACE}+[A-Za-z_:][A-Za-z0-9_:.-]*"
    rf"(?:{_HTML_SPACE}*={_HTML_SPACE}*(?:\"[^\"<>]*\"|'[^'<>]*'|[^ \t\n\r\f\"'=<>`]+))?)*){_HTML_SPACE}*/?>"
)
_END_TAG = re.compile(rf"</([A-Za-z][A-Za-z0-9]*){_HTML_SPACE}*>")
_MARKUP_OPEN = re.compile(r"<[A-Za-z/!?]")
_RAW_TEXT_CLOSE = {
    name: re.compile(rf"</{name}[ \t\n\r\f/>]", re.I)
    for name in ("script", "style", "title", "textarea", "xmp", "iframe", "noembed", "noframes", "noscript")
}
_UNREAD_ELEMENTS = frozenset({
    "plaintext", "template", "svg", "math", "select", "object", "embed", "frameset", "frame", "isindex",
    "caption", "colgroup", "col", "thead", "tbody", "tfoot",
})
_TABLE_NAMES = frozenset({"table", "tr", "td", "th"})
_SPAN_LIMITS = {"colspan": 1000, "rowspan": 65534}
_READABLE = frozenset(map(chr, range(0x20, 0x7F))) | {_DASH}
_YEAR = re.compile(r"(?<![0-9])20[0-9]{2}(?![0-9])")
_FOOTNOTE_MARKER = re.compile(r"\([0-9]\)")
_FIGURE = re.compile(r"\(?\$?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?\)?%?")
_PERIOD_LABEL = "<period>"
_NUMERIC = "<n>"
_ROLES = (
    "highlights",
    "segment_drivers",
    "earnings",
    "drivers",
    "core_reconciliation",
    "change_versus_year_ago",
    "organic_reconciliation",
    "prior_core_reconciliation",
    "cash_flows",
    "balance_sheet",
    "masthead",
    "headline",
    "segment_results",
    "sales_guidance",
    "eps_guidance",
    "cash_flow",
    "cash_flow_reconciliation",
)
_REQUIRED_ROLES = frozenset(_ROLES[:7])


@dataclass(frozen=True)
class Cell:
    table: int
    row: int
    col0: int
    col1: int
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Document:
    source: str
    tables: tuple[tuple[tuple[Cell, ...], ...], ...]
    admission_roles: Mapping[str, int] | None = None
    source_sha256: str | None = None
    fiscal_scope: Sequence[str | date] | None = None
    prior_metrics: frozenset[str] = frozenset()

    @functools.cached_property
    def signatures(self) -> tuple[frozenset[str], ...]:
        return tuple(_signature(rows) for rows in self.tables)


@dataclass(frozen=True)
class Admission:
    code: str
    roles: Mapping[str, int] | None = None


@dataclass(frozen=True)
class Outcome:
    kind: str
    detail: str | None = None
    value: float | None = None
    primary: Cell | None = None
    literal: str | None = None
    second: Cell | None = None


@dataclass(frozen=True)
class PeriodTitle:
    month: int
    day: int | None
    year: int | None


@dataclass(frozen=True)
class Pin:
    metric: str
    primary: tuple[str, str, str | None, str]
    second: tuple[str, str, str | None, str]


def _units(raw: str):
    for match in _UNIT.finditer(raw):
        if match.group(1) is not None or match.group(2) is not None:
            yield "markup", "", match.start(), match.end()
        elif match.group(3) is not None:
            yield "reference", html.unescape(match.group(0)).replace("\xa0", " "), match.start(), match.end()
        else:
            yield "text", match.group(0).replace("\xa0", " "), match.start(), match.end()


def _text(fragment: str) -> str:
    return " ".join("".join(decoded for _kind, decoded, _start, _end in _units(fragment)).split())


def _norm(value: str) -> str:
    return "".join(html.unescape(value).replace("\xa0", " ").split()).casefold()


def _label_token(value: str) -> str:
    folded = _norm(value)
    folded = re.sub(
        r"(three|six|nine|twelve)monthsended[a-z]*\.?\d{1,2},20\d{2}",
        r"\1<period>",
        folded,
    )
    folded = re.sub(
        r"(three|six|nine|twelve)monthsended[a-z]*\.?\d{1,2}",
        r"\1<period>",
        folded,
    )
    folded = re.sub(
        r"[a-z]+-[a-z]+20\d{2}",
        lambda match: _PERIOD_LABEL if _is_quarter_range(match.group(0)) else "<range>",
        folded,
    )
    folded = re.sub(r"(?:fy|fiscalyear)20\d{2}(?:,?20\d{2})?", "<fiscalyear>", folded)
    folded = re.sub(r"20\d{2}(?:,?20\d{2})?", _PERIOD_LABEL, folded)
    folded = _FOLD_NUMBERS.sub(_NUMERIC, folded)
    return re.sub(r"[a-z]+<n>,<period>", "<month><n>,<period>", folded)


def _is_quarter_range(value: str) -> bool:
    match = re.fullmatch(r"([a-z]+)-([a-z]+)20\d{2}", value)
    if match is None:
        return False
    start = month_number(match.group(1))
    end = month_number(match.group(2))
    return start is not None and end is not None and (end - start) % 12 == 2


def _is_label(value: str) -> bool:
    return bool(_LETTERS.search(value)) and _norm(value) not in _NOT_A_LABEL


def _signature(rows: Sequence[Sequence[Cell]]) -> frozenset[str]:
    return frozenset(
        _label_token(cell.text)
        for row in rows
        for cell in row
        if cell.text and _is_label(cell.text)
    )


def _document(source: str) -> Document:
    tables: list[tuple[tuple[Cell, ...], ...]] = []
    for ordinal, (start, end) in enumerate(_table_spans(source)):
        tables.append(_grid(source, ordinal, start, end))
    return Document(source, tuple(tables))


@functools.lru_cache(maxsize=8)
def _structure(source: str) -> str:
    return _COMMENT.sub(lambda match: " " * len(match.group(0)), source)


def _table_spans(source: str) -> tuple[tuple[int, int], ...]:
    view = _structure(source)
    stack: list[tuple[int, int]] = []
    out: list[tuple[int, int]] = []
    events = sorted(
        [(match.start(), 1, match.end()) for match in _TABLE_OPEN.finditer(view)]
        + [(match.start(), 0, match.end()) for match in _TABLE_CLOSE.finditer(view)]
    )
    for _position, kind, end in events:
        if kind == 1:
            stack.append((_position, end))
        elif stack:
            start_position, _start_end = stack.pop()
            out.append((start_position, end))
    out.extend((start_position, len(source)) for start_position, _start_end in stack)
    return tuple(sorted(out, key=lambda span: span[0]))


def _nested_tables(source: str) -> frozenset[int]:
    view = _structure(source)
    return frozenset(
        ordinal
        for ordinal, (start, end) in enumerate(_table_spans(source))
        if _TABLE_OPEN.search(view, start + 1, end) is not None
    )


def _span_attributes(attributes: str) -> list[tuple[str, str | None]]:
    return [
        (match.group(1).lower(), next((value for value in match.group(2, 3, 4) if value is not None), None))
        for match in _ATTRIBUTE.finditer(attributes)
    ]


def _spans_read_alike(attributes: str) -> bool:
    parsed = _span_attributes(attributes)
    for key, limit in _SPAN_LIMITS.items():
        values = [value for name, value in parsed if name == key]
        engine = _SPAN_PATTERNS[key].search(attributes)
        if not values:
            if engine is not None:
                return False
            continue
        if len(values) > 1 or values[0] is None or re.fullmatch(r"[1-9][0-9]{0,4}", values[0]) is None:
            return False
        if int(values[0]) > limit or engine is None or engine.group(1) != values[0]:
            return False
    return not any(
        name not in _SPAN_LIMITS and re.search("colspan|rowspan", f"{name}={value or ''}", re.I)
        for name, value in parsed
    )


@functools.lru_cache(maxsize=8)
def _unreadable_markup(source: str) -> str | None:
    state: str | None = None
    cell_name = ""
    position = 0
    filled: dict[int, int] = {}
    y = x = -1
    while True:
        lt = source.find("<", position)
        text = source[position:] if lt < 0 else source[position:lt]
        if ">" in text:
            return "gt"
        if state in ("table", "row") and text.strip(" \t\n\r\f"):
            return "table"
        if lt < 0:
            break
        if source.startswith("<!--", lt):
            close = source.find("-->", lt + 4)
            if close < 0 or source.startswith((">", "->"), lt + 4) or "--!>" in source[lt + 4:close]:
                return "comment"
            position = close + 3
            continue
        start = _START_TAG.match(source, lt)
        end = None if start else _END_TAG.match(source, lt)
        if start is None and end is None:
            return "tag" if _MARKUP_OPEN.match(source, lt) else "lt"
        if start is not None:
            name = start.group(1).lower()
            position = start.end()
            if name in _UNREAD_ELEMENTS:
                return "element"
            if name in _RAW_TEXT_CLOSE:
                close = _RAW_TEXT_CLOSE[name].search(source, position)
                if state is not None or close is None or re.search("[<>]", source[position:close.start()]):
                    return "element"
                position = close.start()
                continue
            if state is None:
                if name == "table":
                    state, filled, y = "table", {}, -1
                elif name in _TABLE_NAMES:
                    return "table"
            elif state == "table":
                if name != "tr":
                    return "table"
                state, y, x = "row", y + 1, 0
            elif state == "row":
                if name not in ("td", "th"):
                    return "table"
                if not _spans_read_alike(start.group(2)):
                    return "span"
                spans = dict(_span_attributes(start.group(2)))
                colspan, rowspan = int(spans.get("colspan") or 1), int(spans.get("rowspan") or 1)
                while filled.get(x, -1) >= y:
                    x += 1
                for column in range(x, x + colspan):
                    if filled.get(column, -1) >= y:
                        return "grid"
                    filled[column] = y + rowspan - 1
                x += colspan
                state, cell_name = "cell", name
            elif name in _TABLE_NAMES:
                return "table"
        else:
            name = end.group(1).lower()
            position = end.end()
            if state is None:
                continue
            if state == "table":
                if name != "table":
                    return "table"
                state = None
            elif state == "row":
                if name != "tr":
                    return "table"
                occupied = {column for column, last in filled.items() if last >= y}
                if occupied != set(range(len(occupied))):
                    return "grid"
                state = "table"
            elif name == cell_name:
                state = "row"
            elif name in _TABLE_NAMES or name in _UNREAD_ELEMENTS:
                return "table"
    return "table" if state is not None else None


def _grid(source: str, ordinal: int, start: int, end: int) -> tuple[tuple[Cell, ...], ...]:
    view = _structure(source)
    rows: list[tuple[Cell, ...]] = []
    carry: dict[int, tuple[int, Cell]] = {}
    for row_number, row_match in enumerate(_ROW.finditer(view, start, end)):
        row: list[Cell] = []
        col = 0
        pending, carry = dict(carry), {}

        def take_carried() -> None:
            nonlocal col
            while col in pending:
                left, carried = pending.pop(col)
                row.append(carried)
                if left > 1:
                    for span_col in range(carried.col0, carried.col1):
                        carry[span_col] = (left - 1, carried)
                col = carried.col1

        for cell_match in _CELL.finditer(row_match.group(1)):
            take_carried()
            attributes = cell_match.group(2)
            widths = []
            for key in ("colspan", "rowspan"):
                match = _SPAN_PATTERNS[key].search(attributes)
                widths.append(int(match.group(1)) if match else 1)
            colspan, rowspan = widths
            cell_start = row_match.start(1) + cell_match.start(3)
            cell_end = row_match.start(1) + cell_match.end(3)
            cell = Cell(ordinal, row_number, col, col + colspan, cell_start, cell_end, _text(source[cell_start:cell_end]))
            row.append(cell)
            if rowspan > 1:
                for span_col in range(col, col + colspan):
                    carry[span_col] = (rowspan - 1, cell)
            col += colspan
        take_carried()
        rows.append(tuple(row))
    return tuple(rows)


@functools.lru_cache(maxsize=8)
def _cached_document(source: str) -> Document:
    return _document(source)


def _wrapped(source: str) -> bool:
    body = source.removeprefix("\ufeff").lstrip()
    return body.casefold().startswith("<document>")


def _reported_quarter(document: Document, drivers_ordinal: int) -> str | None:
    match = re.search(
        r"Three Months Ended ([A-Z][a-z]+ \d{1,2}, \d{4})",
        _table_text(document.tables[drivers_ordinal]),
    )
    return match.group(1) if match else None


_VOCABULARIES = {
    'highlights': frozenset({
        '%change',
        'coreeps',
        'dilutedeps',
        'firstquarter($billions,excepteps)',
        'gaap',
        'netsales',
        'non-gaap*',
        'organicsales',
        'secondquarter($billions,excepteps)',
        'thirdquarter($billions,excepteps)',
    }),
    'segment_drivers': frozenset({
        '<period>',
        'baby,feminine&familycare',
        'beauty',
        'fabric&homecare',
        'foreignexchange',
        'grooming',
        'healthcare',
        'mix',
        'netsales',
        'netsalesdrivers<n>)',
        'organicsales',
        'organicvolume',
        'other<n>)',
        'price',
        'totalp&g',
        'volume',
    }),
    'earnings': frozenset({
        '%chg',
        'three<period>',
        'amountsinmillionsexceptpershareamounts',
        'basic',
        'basisptchg',
        'comparisonsasa%ofnetsales',
        'consolidatedearningsinformation',
        'costofproductssold',
        'diluted',
        'dilutedweightedaveragecommonsharesoutstanding',
        'dividendspercommonshare',
        'earningsbeforeincometaxes',
        'effectivetaxrate',
        'grossprofit',
        'incometaxes',
        'interestexpense',
        'interestincome',
        'less:netearningsattributabletononcontrollinginterests',
        'netearnings',
        'netearningsattributabletoprocter&gamble',
        'netearningspercommonshare<n>)',
        'netsales',
        'operatingincome',
        'otheroperatingincome,net',
        'otheroperatingincome/(expense),net',
        'selling,generalandadministrativeexpense',
        'theprocter&gamblecompanyandsubsidiaries',
    }),
    'drivers': frozenset({
        'three<period>',
        'baby,feminine&familycare',
        'beauty',
        'fabric&homecare',
        'foreignexchange',
        'grooming',
        'healthcare',
        'mix',
        'netsales',
        'netsalesdrivers<n>)',
        'organicvolume',
        'other<n>)',
        'price',
        'totalcompany',
        'volume',
    }),
    'core_reconciliation': frozenset({
        'three<period>',
        'amountsinmillionsexceptpershareamounts',
        'asreported(gaap)',
        'asreported(gaap)<n>)',
        'core(non-gaap)',
        'coreeps',
        'costofproductssold',
        'currency-neutralcoreeps',
        'currency-neutralcoregrossmargin',
        'currency-neutralcoreoperatingmargin',
        'currency-neutralcoreselling,generalandadministrativeexpenseasa%ofnetsales',
        'currency-neutraleps',
        'currencyimpacttocoreeps',
        'currencyimpacttocoregrossmargin',
        'currencyimpacttocoreoperatingmargin',
        'currencyimpacttocoreselling,generalandadministrativeexpenseasa%ofnetsales',
        'currencyimpacttoearnings',
        'dilutednetearningspercommonshare<n>)',
        'dilutedweightedaveragecommonsharesoutstanding',
        'gladjointventureagreement',
        'grossmargin',
        'grossprofit',
        'incometaxes',
        'incrementalrestructuring',
        'less:netearningsattributabletononcontrollinginterests',
        'netearnings',
        'netearningsattributabletop&g',
        'operatingincome',
        'operatingmargin',
        'othernon-operatingincome/(expense),net',
        'selling,generalandadministrativeexpense',
        'selling,generalandadministrativeexpenseasa%ofnetsales',
        'theprocter&gamblecompanyandsubsidiariesreconciliationofnon-gaapmeasures',
    }),
    'change_versus_year_ago': frozenset({
        'changeversusyearago',
        'coreeps',
        'coregrossmargin',
        'coreoperatingmargin',
        'coreselling,generalandadministrativeexpenseasa%ofnetsales',
        'currency-neutralcoreeps',
        'currency-neutralcoregrossmargin',
        'currency-neutralcoreoperatingmargin',
        'currency-neutralcoreselling,generalandadministrativeasa%ofnetsales',
        'dilutedeps',
        'grossmargin',
        'operatingmargin',
        'selling,generalandadministrativeexpenseasa%ofnetsales',
    }),
    'organic_reconciliation': frozenset({
        '<period>',
        'acquisition&divestitureimpact/other<n>)',
        'baby,feminine&familycare',
        'beauty',
        'fabric&homecare',
        'foreignexchangeimpact',
        'grooming',
        'healthcare',
        'netsalesgrowth',
        'organicsalesgrowth',
        'totalcompany',
    }),
    'prior_core_reconciliation': frozenset({
        'three<period>',
        'amountsinmillionsexceptpershareamounts',
        'asreported(gaap)',
        'core(non-gaap)',
        'coreeps',
        'costofproductssold',
        'dilutednetearningspercommonshare<n>)',
        'dilutedweightedaveragecommonsharesoutstanding',
        'grossmargin',
        'grossprofit',
        'incometaxes',
        'incrementalrestructuring',
        'netearningsattributabletop&g',
        'operatingincome',
        'operatingmargin',
        'selling,generalandadministrativeexpense',
        'selling,generalandadministrativeexpenseasa%ofnetsales',
        'theprocter&gamblecompanyandsubsidiariesreconciliationofnon-gaapmeasures',
    }),
    'cash_flows': frozenset({
        '(gain)/lossonsaleofassets',
        'six<period>',
        'nine<period>',
        'three<period>',
        'acquisitions,netofcashacquired',
        'additionstolong-termdebt',
        'additionstoshort-termdebtwithoriginalmaturitiesofmorethanthreemonths',
        'amountsinmillions',
        'capitalexpenditures',
        'cash,cashequivalentsandrestrictedcash,beginningofperiod',
        'cash,cashequivalentsandrestrictedcash,endofperiod',
        'changeinaccountspayable',
        'changeinaccountsreceivable',
        'changeincash,cashequivalentsandrestrictedcash',
        'changeininventories',
        'consolidatedstatementsofcashflows',
        'deferredincometaxes',
        'depreciationandamortization',
        'dividendstoshareholders',
        'effectofexchangeratechangesoncash,cashequivalentsandrestrictedcash',
        'financingactivities',
        'impactofstockoptionsandother',
        'investingactivities',
        'loss/(gain)onsaleofassets',
        'netadditions/(reductions)toothershort-termdebt',
        'netearnings',
        'operatingactivities<n>)',
        'other',
        'otherinvestingactivity',
        'proceedsfromassetsales',
        'reductionsinlong-termdebt',
        'reductionsinshort-termdebtwithoriginalmaturitiesofmorethanthreemonths',
        'share-basedcompensationexpense',
        'theprocter&gamblecompanyandsubsidiaries',
        'totalfinancingactivities',
        'totalinvestingactivities',
        'totaloperatingactivities',
        'treasurystockpurchases',
    }),
    'balance_sheet': frozenset({
        'accountspayable',
        'accountsreceivable',
        'accruedandotherliabilities',
        'amountsinmillions',
        'cashandcashequivalents',
        'condensedconsolidatedbalancesheets',
        'debtduewithinoneyear',
        '<month><n>,<period>',
        'deferredincometaxes',
        'goodwill',
        'inventories',
        'long-termdebt',
        'othernoncurrentassets',
        'othernoncurrentliabilities',
        'prepaidexpensesandothercurrentassets',
        'property,plantandequipment,net',
        'theprocter&gamblecompanyandsubsidiaries',
        'totalassets',
        'totalcurrentassets',
        'totalcurrentliabilities',
        'totalliabilities',
        "totalliabilitiesandshareholders'equity",
        "totalshareholders'equity",
        'trademarksandotherintangibleassets,net',
    }),
    'masthead': frozenset({'cincinnati,oh<n>', 'newsrelease', 'onep&gplaza', 'theprocter&gamblecompany'}),
    'headline': frozenset({
        'dilutedeps<n>,<n>;coreeps<n>',
        'dilutedeps<n>,<n>;coreeps<n>,<n>',
        'maintainsfiscalyearsales,coreepsgrowthandcashreturnguidance',
        'maintainsfiscalyearsales,epsgrowthandcashreturnguidance',
        'netsales<n>;organicsales<n>',
        'p&gannounces<fiscalyear>firstquarterresults',
        'p&gannounces<fiscalyear>secondquarterresults',
        'p&gannounces<fiscalyear>thirdquarterresults',
        'updatesgaapepsforrestructuringoutlook',
    }),
    'segment_results': frozenset({
        'three<period>',
        '%changeversusyearago',
        'amountsinmillions',
        'baby,feminine&familycare',
        'beauty',
        'consolidatedearningsinformation',
        'corporate',
        'earnings/(loss)beforeincometaxes',
        'fabric&homecare',
        'grooming',
        'healthcare',
        'netearnings',
        'netearnings/(loss)',
        'netsales',
        'theprocter&gamblecompanyandsubsidiaries',
        'totalcompany',
    }),
    'sales_guidance': frozenset({
        '-%to<n>',
        '<n>to<n>',
        '<fiscalyear>(estimate)',
        'combinedforeignexchange&acquisition/divestitureimpact/other<n>)',
        'netsalesgrowth',
        'organicsalesgrowth',
        'totalcompany',
    }),
    'eps_guidance': frozenset({
        '-%to<n>',
        '<n>to<n>',
        '<fiscalyear>(estimate)',
        'coreepsgrowth',
        'dilutedepsgrowth',
        'impactofincrementalnon-coreitems<n>)',
        'totalcompany',
    }),
    'cash_flow': frozenset({
        'three<period>',
        '<period>u.s.taxactpayments',
        'adjustedfreecashflow',
        'capitalspending',
        'operatingcashflow',
    }),
    'cash_flow_reconciliation': frozenset({
        'three<period>',
        'adjustedfreecashflow',
        'adjustedfreecashflowproductivity',
        'adjustmentstonetearnings<n>)',
        'netearnings',
        'netearningsasadjusted',
    }),
}

_ANCHORS = {
    'highlights': frozenset({'%change', 'coreeps', 'dilutedeps', 'gaap'}),
    'segment_drivers': frozenset({'netsalesdrivers<n>)', 'organicsales', 'organicvolume', 'totalp&g'}),
    'earnings': frozenset({'%chg', 'consolidatedearningsinformation', 'diluted', 'netearningspercommonshare<n>)'}),
    'drivers': frozenset({'netsalesdrivers<n>)', 'organicvolume', 'totalcompany'}),
    'core_reconciliation': frozenset({'coreeps', 'incrementalrestructuring', 'currencyimpacttocoregrossmargin'}),
    'change_versus_year_ago': frozenset({'changeversusyearago', 'coreeps', 'dilutedeps'}),
    'organic_reconciliation': frozenset({'netsalesgrowth', 'organicsalesgrowth', 'totalcompany'}),
    'prior_core_reconciliation': frozenset({'asreported(gaap)', 'dilutednetearningspercommonshare<n>)', 'three<period>', 'incrementalrestructuring', 'costofproductssold', 'grossprofit', 'incometaxes', 'operatingincome', 'selling,generalandadministrativeexpense', 'selling,generalandadministrativeexpenseasa%ofnetsales', 'grossmargin', 'operatingmargin', 'dilutedweightedaveragecommonsharesoutstanding', 'netearningsattributabletop&g', 'amountsinmillionsexceptpershareamounts', 'theprocter&gamblecompanyandsubsidiariesreconciliationofnon-gaapmeasures'}),
    'cash_flows': frozenset({'consolidatedstatementsofcashflows', 'totaloperatingactivities'}),
    'balance_sheet': frozenset({'condensedconsolidatedbalancesheets', 'totalassets'}),
    'masthead': frozenset({'newsrelease', 'theprocter&gamblecompany'}),
    'segment_results': frozenset({'%changeversusyearago', 'consolidatedearningsinformation', 'totalcompany'}),
    'sales_guidance': frozenset({'<fiscalyear>(estimate)', 'organicsalesgrowth', 'totalcompany'}),
    'eps_guidance': frozenset({'<fiscalyear>(estimate)', 'coreepsgrowth', 'totalcompany'}),
    'cash_flow': frozenset({'adjustedfreecashflow', 'capitalspending', 'operatingcashflow'}),
    'cash_flow_reconciliation': frozenset({'adjustedfreecashflow', 'adjustedfreecashflowproductivity'}),
    'headline': frozenset({'netsales<n>;organicsales<n>'}),
}


def _match_role(signature: frozenset[str]) -> str | None:
    hits = [
        role for role in _ROLES
        if _ANCHORS.get(role, frozenset()) <= signature
        and signature <= _VOCABULARIES.get(role, frozenset())
    ]
    if len(hits) == 1:
        return hits[0]
    return None


def admit(source: str, fiscal_scope: Sequence[str | date]) -> Admission:
    return _admission(_cached_document(source), fiscal_scope)


def _admission(document: Document, fiscal_scope: Sequence[str | date]) -> Admission:
    from .pg_profile import _scope
    current_start, current_end, _prior_start, _prior_end = _scope(fiscal_scope)
    source = document.source
    text_match = re.search(r"<text>", source, re.I)
    if text_match is None:
        return Admission("not_ex_99_1")
    header = source[:text_match.start()]
    type_matches = list(re.finditer(r"<type>(.*)", header, re.I))
    type_line = type_matches[0].group(0) if type_matches else ""
    if type_line.endswith("\r"):
        type_line = type_line[:-1]
    if len(type_matches) != 1 or type_line != "<TYPE>EX-99.1":
        return Admission("not_ex_99_1")
    if re.search(r"\n<!-- Document created using Wdesk -->\r?\n", source) is None:
        return Admission("generator_not_workiva")
    if not document.tables or "The Procter & Gamble Company" not in _table_text(document.tables[0]):
        return Admission("issuer_not_pg")
    role_tables: list[tuple[str, int]] = []
    for ordinal, signature in enumerate(document.signatures):
        role = _match_role(signature)
        if role is None:
            return Admission(f"unknown_table:t{ordinal}")
        if ordinal in _nested_tables(source):
            return Admission(f"unknown_table:t{ordinal}")
        role_tables.append((role, ordinal))
    required_roles = _REQUIRED_ROLES | {"prior_core_reconciliation"} if current_end.month == 9 else _REQUIRED_ROLES
    counts = {role: sum(candidate == role for candidate, _ordinal in role_tables) for role in _ROLES if role in required_roles}
    repeated = [role for role in _ROLES if role in required_roles and counts[role] > 1]
    if repeated:
        return Admission(f"required_table_repeated:{repeated[0]}")
    roles = {role: ordinal for role, ordinal in role_tables}
    missing = [role for role in _ROLES if role in required_roles and counts[role] == 0]
    if missing:
        return Admission(f"required_table_missing:{missing[0]}")
    reported = _reported_quarter(document, roles["drivers"])
    expected_quarter = f"{_ENGLISH_MONTHS[current_end.month - 1]} {current_end.day}, {current_end.year}"
    if reported != expected_quarter:
        return Admission("quarter_mismatch")
    if (unreadable := _unreadable_markup(source)) is not None:
        return Admission(f"markup_unreadable:{unreadable}")
    return Admission("F1-Q", roles)


def _table_text(rows: Sequence[Sequence[Cell]]) -> str:
    return " ".join(cell.text for row in rows for cell in row)


def _own_cells(rows: Sequence[Sequence[Cell]]) -> list[tuple[int, Cell]]:
    return [(row_number, cell) for row_number, row in enumerate(rows) for cell in row if cell.row == row_number]


def _label_of(row: Sequence[Cell], cell: Cell) -> str | None:
    best = None
    for other in row:
        if other.col1 <= cell.col0 and _is_label(other.text) and other is not cell:
            if best is None or other.col1 > best.col1:
                best = other
    return best.text if best else None


def _headers_over(rows: Sequence[Sequence[Cell]], cell: Cell) -> list[str]:
    out: list[str] = []
    for row_index, row in enumerate(rows[: cell.row]):
        own = [other for other in row if other.text and other.row == row_index]
        if not own:
            continue
        if any(_is_period_title(other.text) for other in own):
            out.extend(other.text for other in own if other.col0 <= cell.col0 < other.col1)
            continue
        if len({id(other) for other in own}) == 1:
            out.append(own[0].text)
            continue

        out.extend(other.text for other in own if other.col0 <= cell.col0 < other.col1)
    return out


def _period_titles(rows: Sequence[Sequence[Cell]], cell: Cell) -> list[date | None]:
    governing = [value for value in _headers_over(rows, cell) if _is_period_title(value)]
    if governing:
        return [_parse_period_title(value) for value in governing]
    return [
        _parse_period_title(other.text)
        for row in rows
        for other in row
        if _is_period_title(other.text)
    ]


def _parse_period_title(value: str) -> date | None:
    match = re.fullmatch(
        r"three months ended ([a-z]+) (\d{1,2})(?:, (\d{4}))?",
        " ".join(value.replace("&#160;", " ").replace("<br/>", " ").split()).casefold(),
    )
    if match:
        month = month_number(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3)) if match.group(3) is not None else None
        if month is None or not _valid_day(year, month, day):
            return None
        return PeriodTitle(month, day, year)
    match = re.fullmatch(r"([a-z]+) - ([a-z]+) (\d{4})", " ".join(value.replace("&#160;", " ").replace("<br/>", " ").split()).casefold())
    if match:
        start = month_number(match.group(1))
        end = month_number(match.group(2))
        year = int(match.group(3))
        if start is None or end is None:
            return None
        expected_start = (end - 3) % 12 + 1
        if start != expected_start:
            return None
        return PeriodTitle(end, None, year)
    return None


def month_number(name: str) -> int | None:
    return _MONTH_NUMBERS.get(name.casefold())


_MONTH_NUMBERS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
_ENGLISH_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
)


def _valid_day(year: int | None, month: int, day: int) -> bool:
    lengths = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    if year is not None and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        lengths[2] = 29
    return 1 <= day <= lengths[month]


def _is_period_title(value: str) -> bool:
    return "ended" in _norm(value) or re.fullmatch(
        r"[A-Za-z]+ - [A-Za-z]+ \d{4}", value.strip()
    ) is not None


def _period_matches(rows: Sequence[Sequence[Cell]], cell: Cell, period: date, *, growth: bool, required: bool) -> bool:
    years = _header_years(rows, cell)
    if years is None:
        return False
    titles = _period_titles(rows, cell)
    if not titles:
        return not required
    if len(titles) != 1:
        return False
    title = titles[0]
    if title is None:
        return False
    if title.year is not None:
        years.add(title.year)
    day_matches = title.day is None or title.day == period.day
    return title.month == period.month and day_matches and (growth or years == {period.year})


def _header_years(rows: Sequence[Sequence[Cell]], cell: Cell) -> set[int] | None:
    years: set[int] = set()
    for value in _headers_over(rows, cell):
        if not any(character.isnumeric() for character in value):
            continue
        title = _parse_period_title(value)
        if title is not None:
            if title.year is not None:
                years.add(title.year)
            continue
        if _FIGURE.fullmatch(value):
            continue
        if any(character.isnumeric() for character in _FOOTNOTE_MARKER.sub("", _YEAR.sub("", value))):
            return None
        years.update(int(year) for year in _YEAR.findall(value))
    return years


def _parse_year(value: str) -> int | None:
    match = re.search(r"(?<!\d)(20\d{2})(?!\d)", value)
    return int(match.group(1)) if match else None


def _as_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


_UNIT_MARKERS = {
    "pg_diluted_eps": "usd_per_share", "pg_prior_diluted_eps": "usd_per_share",
    "pg_core_eps": "usd_per_share", "pg_prior_core_eps": "usd_per_share",
}


def _unit_for_metric(metric: str) -> str | None:
    return _UNIT_MARKERS.get(metric) or (
        "percentage_points" if metric in {
            "pg_price_contribution_pp", "pg_mix_contribution_pp",
            "pg_fx_contribution_pp", "pg_other_contribution_pp",
        } else "percent"
    )


def _locate(document: Document, locator: tuple[str, str, str | None]) -> list[Cell]:
    role, row_label, header, pin_metric = locator
    ordinal = document.admission_roles[role]
    rows = document.tables[ordinal]
    hits: list[Cell] = []
    for row_number, cell in _own_cells(rows):
        if not cell.text or cell.text in _UNIT_CELLS:
            continue
        occupied = [number for number, row in enumerate(rows) if any(other is cell for other in row)]
        if not row_label or any(_norm(_label_of(rows[number], cell) or "") != _norm(row_label) for number in occupied):
            continue
        if header is None:
            after = sorted(
                (other for other in rows[row_number] if other.row == row_number and other.col0 >= cell.col1 and other.text),
                key=lambda other: other.col0,
            )
            literal = _literal(cell.text)
            if literal is None and cell.text == _DASH and after and after[0].text == "%":
                literal = 0.0
            if literal is not None and after and after[0].text == "%":
                hits.append(cell)
            continue
        if all(
            _reads_under(document, rows, replace(cell, col0=column, col1=column + 1), role, header, pin_metric)
            for column in range(cell.col0, cell.col1)
        ):
            hits.append(cell)
    return hits


def _reads_under(document: Document, rows: Sequence[Sequence[Cell]], view: Cell, role: str, header: str, pin_metric: str) -> bool:
    if _norm(header) not in {_norm(value) for value in _headers_over(rows, view)}:
        return False
    pin_year = _parse_year(header)
    if pin_year is not None and _header_years(rows, view) != {pin_year}:
        return False
    required = role in {
        "earnings", "drivers", "core_reconciliation", "prior_core_reconciliation",
        "segment_drivers", "organic_reconciliation",
    }
    current_end = _as_date(document.fiscal_scope[1])
    prior_end = _as_date(document.fiscal_scope[3])
    period = prior_end if pin_metric in document.prior_metrics else current_end
    growth = _norm(header) in {"%chg", "%change"}
    return _period_matches(rows, view, period, growth=growth, required=required)


def _eps_row(document: Document, role: str) -> str:
    candidates = sorted(
        {
            _norm(cell.text)
            for row in document.tables[document.admission_roles[role]]
            for cell in row
            if re.fullmatch(r"Diluted net earnings per common share \(\d\)", cell.text, re.I)
        }
    )
    if len(candidates) != 1:
        return ""
    return candidates[0]


def _unit_admits(printed: str, unit: str | None) -> bool:
    if unit == "usd_per_share":
        return "%" not in printed
    if unit in {"percent", "percentage_points"}:
        return "$" not in printed
    return True


def _literal(printed: str) -> float | None:
    if printed != printed.strip() or any(character.isspace() for character in printed):
        return None
    if printed == _DASH + "%":
        return 0.0
    if not all(ord(character) < 128 for character in printed):
        return None
    match = re.fullmatch(r"\((\d+(?:\.\d+)?)\)%?", printed)
    if match:
        return _finite(-float(match.group(1)))
    match = re.fullmatch(r"[+$]?(\d+(?:\.\d+)?)%?", printed)
    return _finite(float(match.group(1))) if match else None


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _pins(document: Document, fiscal_year: int, calendar_year: int, has_prior_reconciliation: bool) -> tuple[Pin, ...]:
    drivers = "segment_drivers"
    statement_drivers = "drivers"
    eps_row = _eps_row(document, "core_reconciliation")
    pins: list[Pin] = []
    total_metrics = {
        "pg_reported_sales_growth_pct": "Net Sales",
        "pg_total_volume_growth_pct": "Volume",
        "pg_organic_volume_growth_pct": "Organic Volume",
        "pg_price_contribution_pp": "Price",
        "pg_mix_contribution_pp": "Mix",
        "pg_fx_contribution_pp": "Foreign Exchange",
        "pg_other_contribution_pp": "Other (2)",
    }
    for metric, column in total_metrics.items():
        pins.append(Pin(metric, (drivers, "Total P&G", column, metric), (statement_drivers, "Total Company", column, metric)))
    pins.extend((
        Pin("pg_organic_sales_growth_pct", ("organic_reconciliation", "Total Company", "Organic Sales Growth", "pg_organic_sales_growth_pct"), (drivers, "Total P&G", "Organic Sales", "pg_organic_sales_growth_pct")),
        Pin("pg_diluted_eps", ("earnings", "Diluted", str(calendar_year), "pg_diluted_eps"), ("highlights", "Diluted EPS", str(fiscal_year), "pg_diluted_eps")),
        Pin("pg_prior_diluted_eps", ("earnings", "Diluted", str(calendar_year - 1), "pg_prior_diluted_eps"), ("highlights", "Diluted EPS", str(fiscal_year - 1), "pg_prior_diluted_eps")),
        Pin("pg_reported_eps_growth_pct", ("earnings", "Diluted", "% Chg", "pg_reported_eps_growth_pct"), ("highlights", "Diluted EPS", "% Change", "pg_reported_eps_growth_pct")),
        Pin("pg_core_eps", ("core_reconciliation", eps_row, "Core(Non-GAAP)", "pg_core_eps"), ("highlights", "Core EPS", str(fiscal_year), "pg_core_eps")),
        Pin("pg_prior_core_eps", ("highlights", "Core EPS", str(fiscal_year - 1), "pg_prior_core_eps"),
            (("prior_core_reconciliation", "Diluted net earnings per common share (1)", "Core(Non-GAAP)", "pg_prior_core_eps")
             if has_prior_reconciliation else ("core_reconciliation", eps_row, "As Reported (GAAP) (1)", "pg_prior_core_eps"))),
        Pin("pg_core_eps_growth_pct", ("highlights", "Core EPS", "% Change", "pg_core_eps_growth_pct"), ("change_versus_year_ago", "Core EPS", None, "pg_core_eps_growth_pct")),
    ))
    for metric, segment in {
        "pg_beauty_organic_sales_growth_pct": "Beauty",
        "pg_grooming_organic_sales_growth_pct": "Grooming",
        "pg_health_care_organic_sales_growth_pct": "Health Care",
        "pg_fabric_home_organic_sales_growth_pct": "Fabric & Home Care",
        "pg_baby_feminine_family_organic_sales_growth_pct": "Baby, Feminine & Family Care",
    }.items():
        pins.append(Pin(metric, ("organic_reconciliation", segment, "Organic Sales Growth", metric), (drivers, segment, "Organic Sales", metric)))
    return tuple(pins)


def _outcome(document: Document, pin: Pin, prior_note: bool) -> Outcome:
    primary = _locate(document, pin.primary)
    second = _locate(document, pin.second)
    if pin.metric == "pg_prior_core_eps" and not prior_note:
        second = []
    if len(primary) != 1 or len(second) != 1:
        return Outcome("unlocated")
    unit = _unit_for_metric(pin.metric)
    primary_value = _literal(primary[0].text)
    second_value = _literal(second[0].text)
    if second_value is None and second[0].text == _DASH and unit in {"percent", "percentage_points"}:
        following = sorted(
            (other for other in document.tables[second[0].table][second[0].row]
             if other.row == second[0].row and other.col0 >= second[0].col1 and other.text),
            key=lambda other: other.col0,
        )
        if following and following[0].text == "%":
            second_value = 0.0
    if primary_value is None or second_value is None:
        return Outcome("unlocated")
    if primary_value != second_value:
        return Outcome("conflict")
    if not (_unit_admits(primary[0].text, unit) and _unit_admits(second[0].text, unit)):
        return Outcome("unlocated")
    if not (_neighbours_admit(document, primary[0], unit) and _neighbours_admit(document, second[0], unit)):
        return Outcome("unlocated")
    return Outcome("present", value=primary_value, primary=primary[0], literal=primary[0].text, second=second[0])


def _seen(text: str) -> str:
    return "".join(character for character in unicodedata.normalize("NFKC", text) if character in _READABLE).strip()


def _neighbours_admit(document: Document, cell: Cell, unit: str | None) -> bool:
    for row in document.tables[cell.table]:
        if not any(other is cell for other in row):
            continue
        printed = sorted((other for other in row if _seen(other.text) and other is not cell), key=lambda other: other.col0)
        left = [other for other in printed if other.col1 <= cell.col0]
        right = [other for other in printed if other.col0 >= cell.col1]
        nearest = ([_seen(left[-1].text)] if left else []) + ([_seen(right[0].text)] if right else [])
        if not all(_unit_admits(text, unit) for text in nearest if text in _UNIT_CELLS):
            return False
    return True


def _prior_note_present(document: Document, prior_end: date) -> bool:
    ordinal = document.admission_roles["core_reconciliation"]
    if len(document.tables) <= ordinal + 1:
        return False
    end = _table_end(document.source, ordinal)
    following = _table_start(document.source, ordinal + 1)
    sentence = (
        f"(1) For the three months ended {_ENGLISH_MONTHS[prior_end.month - 1]} {prior_end.day}, {prior_end.year}, "
        "there were no adjustments to or reconciling items for Core EPS."
    )
    return _norm(sentence) in _norm(_text(document.source[end:following]))


def _table_start(source: str, ordinal: int) -> int:
    return _table_spans(source)[ordinal][0]


def _table_end(source: str, ordinal: int) -> int:
    return _table_spans(source)[ordinal][1]


def _receipt(document: Document, cell: Cell) -> Any | None:
    raw = document.source[cell.start:cell.end]
    decoded = ""
    extents: list[tuple[int, int]] = []
    markup_spans: list[tuple[int, int]] = []
    for kind, unit_text, unit_start, unit_end in _units(raw):
        decoded += unit_text
        if kind == "text":
            extents.extend((unit_start + offset, unit_start + offset + 1) for offset in range(len(unit_text)))
        elif kind == "reference":
            extents.extend((unit_start, unit_end) for _character in unit_text)
        else:
            markup_spans.append((unit_start, unit_end))
    if not cell.text or not decoded.strip():
        return None
    words = decoded.split()
    if words != [cell.text]:
        return None
    first = decoded.index(cell.text)
    last = first + len(cell.text) - 1
    span_start, span_end = extents[first][0], extents[last][1]
    for position in range(first, last + 1):
        if position > first and extents[position][0] != extents[position - 1][1]:
            return None
    if any(max(start, span_start) < min(end, span_end) for start, end in markup_spans):
        return None
    if first > 0 and extents[first - 1][1] > extents[first][0]:
        return None
    if last + 1 < len(extents) and extents[last][1] > extents[last + 1][0]:
        return None
    if any(character.isspace() for character in raw[span_start:span_end]):
        return None
    if _text(raw[span_start:span_end]) != cell.text:
        return None
    return receipt_for_char_span(
        source=document.source,
        source_sha256=document.source_sha256,
        char_start=cell.start + span_start,
        char_end=cell.start + span_end,
    )


def extract(document: Document, admission: Admission, definitions: Sequence["PGDefinition"], *, bound: BoundRelease, document_id: str, event_id: str, fiscal_period: Any, fiscal_scope: Sequence[str | date]) -> list[dict[str, Any]]:
    from .pg_profile import _absent, _fiscal_identity, _present, _scope
    if admission.code != "F1-Q" or admission.roles is None:
        return [
            _absent(
                definition=definition,
                document_id=document_id,
                event_id=event_id,
                detail=f"envelope_refused:{admission.code}",
            )
            for definition in definitions
        ]
    document = Document(
        document.source,
        document.tables,
        admission.roles,
        bound.revision.source_sha256,
        fiscal_scope,
        frozenset({"pg_prior_diluted_eps", "pg_prior_core_eps"}),
    )
    current_start, current_end, _prior_start, prior_end = _scope(document.fiscal_scope)
    fiscal_year, _quarter = _fiscal_identity(current_start, current_end)
    current_end = _as_date(fiscal_scope[1])
    has_prior = current_end.month == 9 and "prior_core_reconciliation" in admission.roles
    prior_note = has_prior or _prior_note_present(document, prior_end)
    outcomes = {
        pin.metric: _outcome(document, pin, prior_note)
        for pin in _pins(document, fiscal_year, current_end.year, has_prior)
    }
    facts: list[dict[str, Any]] = []
    for definition in definitions:
        if definition.metric == "pg_core_reconciliation_context":
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, detail="envelope_excluded:pg_core_reconciliation_context"))
            continue
        outcome = outcomes[definition.metric]
        period = prior_end.isoformat() if definition.metric in {"pg_prior_diluted_eps", "pg_prior_core_eps"} else current_end.isoformat()
        receipt = _receipt(document, outcome.primary) if outcome.kind == "present" and outcome.primary is not None else None
        if outcome.kind == "present" and outcome.primary is not None and receipt is not None:
            facts.append(_present(definition=definition, value=outcome.value, document_id=document_id, bound=bound, receipt=receipt, event_id=event_id, period=period))
        elif outcome.kind == "conflict":
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, reason="cross_check_conflict", detail=f"envelope_conflict:{definition.metric}"))
        else:
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, detail=f"envelope_unlocated:{definition.metric}"))
    return facts


def wrapped_admit(source: str, fiscal_scope: Sequence[str | date]) -> Admission | None:
    if not _wrapped(source):
        return None
    return _admission(_cached_document(source), fiscal_scope)
