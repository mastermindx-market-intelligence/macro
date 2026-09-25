"""Finite-source envelope for wrapped P&G quarterly release exhibits."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import functools
import html
import re
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from .pg_profile import PGDefinition

from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import ReceiptError, receipt_for_char_span


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
_PERIOD_LABEL = "<period>"
_YEAR = r"20\d{2}"
_ROLES = (
    "highlights",
    "segment_drivers",
    "earnings",
    "drivers",
    "core_reconciliation",
    "change_versus_year_ago",
    "organic_reconciliation",
    "prior_core_reconciliation",
    "other_core_reconciliation",
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
_OTHER_ROLES = frozenset(_ROLES[7:])


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
class Pin:
    metric: str
    primary: tuple[str, str, str | None]
    second: tuple[str, str, str | None]


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAG.sub("", fragment)).replace("\xa0", " ").split())


def _norm(value: str) -> str:
    return "".join(html.unescape(value).replace("\xa0", " ").split()).casefold()


def _label_token(value: str) -> str:
    folded = _norm(value)
    folded = re.sub(rf"(?:fy|fiscalyear)?{_YEAR}(?:,?{_YEAR})?", _PERIOD_LABEL, folded)
    folded = re.sub(rf"(?:three|six|nine|twelve)monthsended[a-z]*\.?\d{{1,2}},{_YEAR}", _PERIOD_LABEL, folded)
    folded = re.sub(rf"[a-z]+-[a-z]+{_YEAR}", _PERIOD_LABEL, folded)
    return folded


def _is_label(value: str) -> bool:
    return bool(_LETTERS.search(value)) and _norm(value) not in _NOT_A_LABEL


def _signature(rows: Sequence[Sequence[Cell]]) -> frozenset[str]:
    return frozenset(
        _label_token(cell.text)
        for row in rows
        for cell in row
        if cell.text and _is_label(cell.text)
    )


def _document(source: str) -> Document | None:
    tables: list[tuple[tuple[Cell, ...], ...]] = []
    for ordinal, (start, end) in enumerate(_table_spans(source)):
        tables.append(_grid(source, ordinal, start, end))
    return Document(source, tuple(tables))


def _table_spans(source: str) -> tuple[tuple[int, int], ...]:
    out: list[tuple[int, int]] = []
    for match in _TABLE_OPEN.finditer(source):
        close = _TABLE_CLOSE.search(source, match.end())
        if close is None or _TABLE_OPEN.search(source, match.end(), close.start()) is not None:
            return ()
        out.append((match.start(), close.end()))
    return tuple(out)


def _grid(source: str, ordinal: int, start: int, end: int) -> tuple[tuple[Cell, ...], ...]:
    rows: list[tuple[Cell, ...]] = []
    carry: dict[int, tuple[int, Cell]] = {}
    for row_number, row_match in enumerate(_ROW.finditer(source, start, end)):
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
            cell = Cell(
                ordinal,
                row_number,
                col,
                col + colspan,
                row_match.start(1) + cell_match.start(3),
                row_match.start(1) + cell_match.end(3),
                _text(cell_match.group(3)),
            )
            row.append(cell)
            if rowspan > 1:
                for span_col in range(col, col + colspan):
                    carry[span_col] = (rowspan - 1, cell)
            col += colspan
        take_carried()
        rows.append(tuple(row))
    return tuple(rows)


@functools.lru_cache(maxsize=8)
def _cached_document(source: str) -> Document | None:
    return _document(source)


def _wrapped(source: str) -> bool:
    if not source.startswith("<DOCUMENT>\n"):
        return False
    text_start = source.find("<TEXT>")
    if text_start < 0:
        return False
    header = source[:text_start]
    return re.search(r"<TYPE>([^\n<]+)\n", header) is not None


def _labels(rows: Sequence[Sequence[Cell]]) -> set[str]:
    return {
        _label_token(cell.text)
        for row in rows
        for cell in row
        if cell.text and _is_label(cell.text)
    }


def _reported_quarter(document: Document, drivers_ordinal: int) -> str | None:
    match = re.search(
        r"Three Months Ended ([A-Z][a-z]+ \d{1,2}, \d{4})",
        _table_text(document.tables[drivers_ordinal]),
    )
    return match.group(1) if match else None


def _visible_text(markup: str) -> str:
    return _text(markup)


def _anchor(anchor: str, mask: str = _PERIOD_LABEL) -> str:
    return _label_token(anchor)


_VOCABULARIES = {
    "highlights": frozenset({
        "%change", "coreeps", "dilutedeps", "firstquarter($billions,excepteps)",
        "gaap", "netsales", "non-gaap*", "organicsales",
        "secondquarter($billions,excepteps)", "thirdquarter($billions,excepteps)",
    }),
    "segment_drivers": frozenset({
        "baby,feminine&familycare", "beauty", "fabric&homecare", "foreignexchange", "grooming",
        "healthcare", "january-march<period>", "july-september<period>", "mix", "netsales",
        "netsalesdrivers(1)", "october-december<period>", "organicsales", "organicvolume",
        "other(2)", "price", "totalp&g", "volume",
    }),
    "earnings": frozenset({
        "%chg", "amountsinmillionsexceptpershareamounts", "basic", "basisptchg",
        "comparisonsasa%ofnetsales", "consolidatedearningsinformation", "costofproductssold",
        "diluted", "dilutedweightedaveragecommonsharesoutstanding", "dividendspercommonshare",
        "earningsbeforeincometaxes", "effectivetaxrate", "grossprofit", "incometaxes",
        "interestexpense", "interestincome", "less:netearningsattributabletononcontrollinginterests",
        "netearnings", "netearningsattributabletoprocter&gamble", "netearningspercommonshare(1)",
        "netsales", "operatingincome", "otheroperatingincome,net",
        "otheroperatingincome/(expense),net", "selling,generalandadministrativeexpense",
        "theprocter&gamblecompanyandsubsidiaries", "threemonthsendeddecember31",
        "threemonthsendedmarch31", "threemonthsendedseptember30",
    }),
    "drivers": frozenset({
        "baby,feminine&familycare", "beauty", "fabric&homecare", "foreignexchange", "grooming",
        "healthcare", "mix", "netsales", "netsalesdrivers(1)", "organicvolume", "other(2)",
        "price", "threemonthsendeddecember31,<period>", "threemonthsendedmarch31,<period>",
        "threemonthsendedseptember30,<period>", "totalcompany", "volume",
    }),
    "core_reconciliation": frozenset({
        "amountsinmillionsexceptpershareamounts", "asreported(gaap)", "asreported(gaap)(1)",
        "core(non-gaap)", "coreeps", "costofproductssold", "currency-neutralcoreeps",
        "currency-neutralcoregrossmargin", "currency-neutralcoreoperatingmargin",
        "currency-neutralcoreselling,generalandadministrativeexpenseasa%ofnetsales",
        "currency-neutraleps", "currencyimpacttocoreeps", "currencyimpacttocoregrossmargin",
        "currencyimpacttocoreoperatingmargin", "currencyimpacttocoreselling,generalandadministrativeexpenseasa%ofnetsales",
        "currencyimpacttoearnings", "dilutednetearningspercommonshare(1)",
        "dilutednetearningspercommonshare(2)", "dilutedweightedaveragecommonsharesoutstanding",
        "gladjointventureagreement", "grossmargin", "grossprofit", "incometaxes",
        "incrementalrestructuring", "less:netearningsattributabletononcontrollinginterests",
        "netearnings", "netearningsattributabletop&g", "operatingincome", "operatingmargin",
        "othernon-operatingincome/(expense),net", "selling,generalandadministrativeexpense",
        "selling,generalandadministrativeexpenseasa%ofnetsales",
        "theprocter&gamblecompanyandsubsidiariesreconciliationofnon-gaapmeasures",
        "threemonthsendeddecember31,<period>", "threemonthsendedmarch31,<period>",
        "threemonthsendedseptember30,<period>",
    }),
    "change_versus_year_ago": frozenset({
        "changeversusyearago", "coreeps", "coregrossmargin", "coreoperatingmargin",
        "coreselling,generalandadministrativeexpenseasa%ofnetsales", "currency-neutralcoreeps",
        "currency-neutralcoregrossmargin", "currency-neutralcoreoperatingmargin",
        "currency-neutralcoreselling,generalandadministrativeasa%ofnetsales", "dilutedeps",
        "grossmargin", "operatingmargin", "selling,generalandadministrativeexpenseasa%ofnetsales",
    }),
    "organic_reconciliation": frozenset({
        "acquisition&divestitureimpact/other(1)", "baby,feminine&familycare", "beauty",
        "fabric&homecare", "foreignexchangeimpact", "grooming", "healthcare",
        "january-march<period>", "july-september<period>", "netsalesgrowth",
        "october-december<period>", "organicsalesgrowth", "totalcompany",
    }),
    "prior_core_reconciliation": frozenset({
        "amountsinmillionsexceptpershareamounts", "asreported(gaap)", "core(non-gaap)", "coreeps",
        "costofproductssold", "dilutednetearningspercommonshare(1)",
        "dilutedweightedaveragecommonsharesoutstanding", "grossmargin", "grossprofit", "incometaxes",
        "incrementalrestructuring", "netearningsattributabletop&g", "operatingincome",
        "operatingmargin", "selling,generalandadministrativeexpense",
        "selling,generalandadministrativeexpenseasa%ofnetsales",
        "theprocter&gamblecompanyandsubsidiariesreconciliationofnon-gaapmeasures",
        "threemonthsendedseptember30,<period>",
    }),
    "other_core_reconciliation": frozenset({
        "amountsinmillionsexceptpershareamounts", "asreported(gaap)", "core(non-gaap)", "coreeps",
        "costofproductssold", "dilutednetearningspercommonshare(1)",
        "dilutedweightedaveragecommonsharesoutstanding", "grossmargin", "grossprofit", "incometaxes",
        "incrementalrestructuring", "netearningsattributabletop&g", "operatingincome",
        "operatingmargin", "selling,generalandadministrativeexpense",
        "selling,generalandadministrativeexpenseasa%ofnetsales",
        "theprocter&gamblecompanyandsubsidiariesreconciliationofnon-gaapmeasures",
        "threemonthsendedseptember30,<period>",
    }),
    "cash_flows": frozenset({
        "(gain)/lossonsaleofassets", "acquisitions,netofcashacquired", "additionstolong-termdebt",
        "additionstoshort-termdebtwithoriginalmaturitiesofmorethanthreemonths", "amountsinmillions",
        "capitalexpenditures", "cash,cashequivalentsandrestrictedcash,beginningofperiod",
        "cash,cashequivalentsandrestrictedcash,endofperiod", "changeinaccountspayable",
        "changeinaccountsreceivable", "changeincash,cashequivalentsandrestrictedcash",
        "changeininventories", "consolidatedstatementsofcashflows", "deferredincometaxes",
        "depreciationandamortization", "dividendstoshareholders",
        "effectofexchangeratechangesoncash,cashequivalentsandrestrictedcash", "financingactivities",
        "impactofstockoptionsandother", "investingactivities", "loss/(gain)onsaleofassets",
        "netadditions/(reductions)toothershort-termdebt", "netearnings",
        "ninemonthsendedmarch31", "operatingactivities(1)", "other", "otherinvestingactivity",
        "proceedsfromassetsales", "reductionsinlong-termdebt",
        "reductionsinshort-termdebtwithoriginalmaturitiesofmorethanthreemonths",
        "share-basedcompensationexpense", "sixmonthsendeddecember31",
        "theprocter&gamblecompanyandsubsidiaries", "threemonthsendedseptember30",
        "totalfinancingactivities", "totalinvestingactivities", "totaloperatingactivities",
        "treasurystockpurchases",
    }),
    "balance_sheet": frozenset({
        "accountspayable", "accountsreceivable", "accruedandotherliabilities", "amountsinmillions",
        "cashandcashequivalents", "condensedconsolidatedbalancesheets", "debtduewithinoneyear",
        "december31,<period>", "deferredincometaxes", "goodwill", "inventories", "june30,<period>",
        "long-termdebt", "march31,<period>", "othernoncurrentassets", "othernoncurrentliabilities",
        "prepaidexpensesandothercurrentassets", "property,plantandequipment,net",
        "september30,<period>", "theprocter&gamblecompanyandsubsidiaries", "totalassets",
        "totalcurrentassets", "totalcurrentliabilities", "totalliabilities",
        "totalliabilitiesandshareholders'equity", "totalshareholders'equity",
        "trademarksandotherintangibleassets,net",
    }),
    "masthead": frozenset({
        "cincinnati,oh45202", "newsrelease", "onep&gplaza", "theprocter&gamblecompany",
    }),
    "headline": frozenset({
        "dilutedeps$1.63,+6%;coreeps$1.59,+3%", "dilutedeps$1.78,-5%;coreeps$1.88,0%",
        "dilutedeps$1.95,+21%;coreeps$1.99,+3%",
        "maintainsfiscalyearsales,coreepsgrowthandcashreturnguidance",
        "maintainsfiscalyearsales,epsgrowthandcashreturnguidance", "netsales+1%;organicsales0%",
        "netsales+3%;organicsales+2%", "netsales+7%;organicsales3%",
        "p&gannounces<period>firstquarterresults", "p&gannounces<period>secondquarterresults",
        "p&gannounces<period>thirdquarterresults", "updatesgaapepsforrestructuringoutlook",
    }),
    "segment_results": frozenset({
        "%changeversusyearago", "amountsinmillions", "baby,feminine&familycare", "beauty",
        "consolidatedearningsinformation", "corporate", "earnings/(loss)beforeincometaxes",
        "fabric&homecare", "grooming", "healthcare", "netearnings", "netearnings/(loss)", "netsales",
        "theprocter&gamblecompanyandsubsidiaries", "threemonthsendeddecember31,<period>",
        "threemonthsendedmarch31,<period>", "threemonthsendedseptember30,<period>", "totalcompany",
    }),
    "sales_guidance": frozenset({
        "+1%to+5%", "-%to+4%", "<period>(estimate)",
        "combinedforeignexchange&acquisition/divestitureimpact/other(1)", "netsalesgrowth",
        "organicsalesgrowth", "totalcompany",
    }),
    "eps_guidance": frozenset({
        "+1%to+6%", "+3%to+9%", "-%to+4%", "-1%to-2%", "-3%to-5%", "<period>(estimate)",
        "coreepsgrowth", "dilutedepsgrowth", "impactofincrementalnon-coreitems(1)", "totalcompany",
    }),
    "cash_flow": frozenset({
        "<period>u.s.taxactpayments", "adjustedfreecashflow", "capitalspending", "operatingcashflow",
        "threemonthsendeddecember31,<period>", "threemonthsendedmarch31,<period>",
        "threemonthsendedseptember30,<period>",
    }),
    "cash_flow_reconciliation": frozenset({
        "adjustedfreecashflowproductivity", "adjustmentstonetearnings(1)", "netearnings", "netearningsasadjusted",
        "netearnings", "netearningsasadjusted", "threemonthsendeddecember31,<period>",
        "threemonthsendedmarch31,<period>", "threemonthsendedseptember30,<period>",
    }),
}


_ANCHORS = {
    "highlights": frozenset({"dilutedeps", "coreeps", "gaap", "%change"}),
    "segment_drivers": frozenset({"totalp&g", "organicsales", "organicvolume", "netsalesdrivers(1)"}),
    "earnings": frozenset({"consolidatedearningsinformation", "diluted", "netearningspercommonshare(1)", "%chg"}),
    "drivers": frozenset({"totalcompany", "netsalesdrivers(1)", "organicvolume"}),
    "core_reconciliation": frozenset({"coreeps", "asreported(gaap)", "core(non-gaap)", "incrementalrestructuring"}),
    "change_versus_year_ago": frozenset({"changeversusyearago", "dilutedeps", "coreeps"}),
    "organic_reconciliation": frozenset({"totalcompany", "netsalesgrowth", "organicsalesgrowth"}),
    "prior_core_reconciliation": frozenset({
        "dilutednetearningspercommonshare(1)", "asreported(gaap)", "core(non-gaap)",
        "threemonthsendedseptember30,<period>",
    }),
    "other_core_reconciliation": frozenset({"dilutednetearningspercommonshare(1)", "coreeps", "asreported(gaap)", "core(non-gaap)", "threemonthsendedseptember30,<period>"}),
    "cash_flows": frozenset({"consolidatedstatementsofcashflows", "totaloperatingactivities"}),
    "balance_sheet": frozenset({"condensedconsolidatedbalancesheets", "totalassets"}),
    "masthead": frozenset({"newsrelease", "theprocter&gamblecompany"}),
    "segment_results": frozenset({"consolidatedearningsinformation", "%changeversusyearago", "totalcompany"}),
    "sales_guidance": frozenset({"<period>(estimate)", "organicsalesgrowth", "totalcompany"}),
    "eps_guidance": frozenset({"<period>(estimate)", "coreepsgrowth", "totalcompany"}),
    "cash_flow": frozenset({"operatingcashflow", "capitalspending", "adjustedfreecashflow"}),
    "cash_flow_reconciliation": frozenset({"adjustedfreecashflow", "adjustedfreecashflowproductivity", "netearningsasadjusted"}),
    "__cash_flow_reconciliation": frozenset(),
}


_ANCHORS["headline"] = frozenset()


_ANCHORS["cash_flow_reconciliation"] = frozenset({"netearningsasadjusted", "adjustedfreecashflowproductivity"})

_VOCABULARIES["cash_flow_reconciliation"] |= frozenset({"adjustedfreecashflow"})
_ANCHORS["cash_flow_reconciliation"] = frozenset({"adjustedfreecashflow", "adjustedfreecashflowproductivity"})

def _match_role(signature: frozenset[str]) -> str | None:
    hits = [
        role for role in _ROLES
        if _ANCHORS.get(role, frozenset()) <= signature
        and signature <= _VOCABULARIES.get(role, frozenset())
    ]
    if len(hits) == 1:
        return hits[0]
    if {"core_reconciliation", "prior_core_reconciliation"} == set(hits):
        return "core_reconciliation"
    if {"core_reconciliation", "prior_core_reconciliation", "other_core_reconciliation"} == set(hits):
        return "prior_core_reconciliation"
    return None


def admit(source: str, fiscal_scope: Sequence[str | date]) -> Admission:
    document = _cached_document(source)
    if document is None:
        return Admission("unknown_table:t0")
    admission = _admission(document, fiscal_scope)
    if admission.roles is None:
        return admission
    document = Document(source, document.tables, admission.roles, fiscal_scope=fiscal_scope)
    return Admission(admission.code, admission.roles)


def _admission(document: Document, fiscal_scope: Sequence[str | date]) -> Admission:
    from .pg_profile import _scope
    current_start, current_end, _prior_start, _prior_end = _scope(fiscal_scope)
    source = document.source
    type_match = re.search(r"<TYPE>([^\n<]+)\n", source[:source.find("<TEXT>")])
    if type_match is None or type_match.group(1).strip() != "EX-99.1":
        return Admission("not_ex_99_1")
    if "\n<!-- Document created using Wdesk -->\n" not in source:
        return Admission("generator_not_workiva")
    if not document.tables or "The Procter & Gamble Company" not in _table_text(document.tables[0]):
        return Admission("issuer_not_pg")
    assignments: list[str | None] = []
    roles: dict[str, int] = {}
    for ordinal, signature in enumerate(document.signatures):
        role = _match_role(signature)
        if role is None:
            return Admission(f"unknown_table:t{ordinal}")
        if role in roles:
            return Admission(f"required_table_repeated:{role}")
        roles[role] = ordinal
        assignments.append(role)
    for role in _REQUIRED_ROLES:
        if role not in roles:
            return Admission(f"required_table_missing:{role}")
    reported = _reported_quarter(document, roles["drivers"])
    if reported != current_end.strftime("%B %-d, %Y"):
        return Admission("quarter_mismatch")
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
    for row in rows[: cell.row]:
        filled = [other for other in row if other.text and other.row < cell.row]
        if len({id(other) for other in filled}) == 1:
            out.append(filled[0].text)
            continue
        out.extend(other.text for other in filled if other.col0 <= cell.col0 < other.col1)
    return out


def _locate(document: Document, locator: tuple[str, str, str | None]) -> list[Cell]:
    role, row_label, header = locator
    ordinal = document.admission_roles[role]
    rows = document.tables[ordinal]
    hits: list[Cell] = []
    for row_number, cell in _own_cells(rows):
        if not cell.text or cell.text in _UNIT_CELLS:
            continue
        if _norm(_label_of(rows[row_number], cell) or "") != _norm(row_label):
            continue
        if header is None:
            after = sorted(
                (other for other in rows[row_number] if other.row == row_number and other.col0 >= cell.col1 and other.text),
                key=lambda other: other.col0,
            )
            if after and after[0].text == "%":
                hits.append(cell)
            continue
        if _norm(header) in {_norm(value) for value in _headers_over(rows, cell)}:
            hits.append(cell)
    return hits


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
        raise ValueError("the core reconciliation does not carry exactly one pinned EPS row")
    return candidates[0]


def _literal(printed: str) -> float | None:
    value = printed.replace(" ", "")
    if value in {_DASH, _DASH + "%"}:
        return 0.0
    match = re.fullmatch(r"\((\d+(?:\.\d+)?)\)%?", value)
    if match:
        return -float(match.group(1))
    match = re.fullmatch(r"[+$]?(\d+(?:\.\d+)?)%?", value)
    return float(match.group(1)) if match else None


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
        pins.append(Pin(metric, (drivers, "Total P&G", column), (statement_drivers, "Total Company", column)))
    pins.extend((
        Pin("pg_organic_sales_growth_pct", ("organic_reconciliation", "Total Company", "Organic Sales Growth"), (drivers, "Total P&G", "Organic Sales")),
        Pin("pg_diluted_eps", ("earnings", "Diluted", str(calendar_year)), ("highlights", "Diluted EPS", str(fiscal_year))),
        Pin("pg_prior_diluted_eps", ("earnings", "Diluted", str(calendar_year - 1)), ("highlights", "Diluted EPS", str(fiscal_year - 1))),
        Pin("pg_reported_eps_growth_pct", ("earnings", "Diluted", "% Chg"), ("highlights", "Diluted EPS", "% Change")),
        Pin("pg_core_eps", ("core_reconciliation", eps_row, "Core(Non-GAAP)"), ("highlights", "Core EPS", str(fiscal_year))),
        Pin("pg_prior_core_eps", ("highlights", "Core EPS", str(fiscal_year - 1)),
            (("prior_core_reconciliation", "Diluted net earnings per common share (1)", "Core(Non-GAAP)")
             if has_prior_reconciliation else ("core_reconciliation", eps_row, "As Reported (GAAP) (1)"))),
        Pin("pg_core_eps_growth_pct", ("highlights", "Core EPS", "% Change"), ("change_versus_year_ago", "Core EPS", None)),
    ))
    for metric, segment in {
        "pg_beauty_organic_sales_growth_pct": "Beauty",
        "pg_grooming_organic_sales_growth_pct": "Grooming",
        "pg_health_care_organic_sales_growth_pct": "Health Care",
        "pg_fabric_home_organic_sales_growth_pct": "Fabric & Home Care",
        "pg_baby_feminine_family_organic_sales_growth_pct": "Baby, Feminine & Family Care",
    }.items():
        pins.append(Pin(metric, ("organic_reconciliation", segment, "Organic Sales Growth"), (drivers, segment, "Organic Sales")))
    return tuple(pins)


def _outcome(document: Document, pin: Pin, prior_note: bool) -> Outcome:
    primary = _locate(document, pin.primary)
    second = _locate(document, pin.second)
    if pin.metric == "pg_prior_core_eps" and not prior_note:
        second = []
    if len(primary) != 1 or len(second) != 1:
        return Outcome("unlocated")
    primary_value = _literal(primary[0].text)
    second_value = _literal(second[0].text)
    if primary_value is None or second_value is None:
        return Outcome("unlocated")
    if primary_value != second_value:
        return Outcome("conflict")
    return Outcome("present", value=primary_value, primary=primary[0], literal=primary[0].text, second=second[0])


def _prior_note_present(document: Document, prior_end: date) -> bool:
    from .pg_profile import _scope
    ordinal = document.admission_roles["core_reconciliation"]
    if len(document.tables) <= ordinal + 1:
        return False
    end = _table_end(document.source, ordinal)
    following = _table_start(document.source, ordinal + 1)
    sentence = (
        f"(1) For the three months ended {prior_end:%B} {prior_end.day}, {prior_end.year}, "
        "there were no adjustments to or reconciling items for Core EPS."
    )
    return _norm(sentence) in _norm(_text(document.source[end:following]))


def _table_start(source: str, ordinal: int) -> int:
    return _table_spans(source)[ordinal][0]


def _table_end(source: str, ordinal: int) -> int:
    return _table_spans(source)[ordinal][1]


def _receipt(document: Document, cell: Cell):
    return receipt_for_char_span(
        source=document.source,
        source_sha256=document.source_sha256,
        char_start=cell.start,
        char_end=cell.end,
    )



def derive_outcomes(source: str, fiscal_scope: Sequence[str | date], admission: Admission) -> dict[str, Outcome]:
    from .pg_profile import _fiscal_identity, _scope

    base = _cached_document(source)
    if base is None or admission.roles is None:
        raise ValueError("an admitted document cannot be read")
    current_start, current_end, _prior_start, prior_end = _scope(fiscal_scope)
    fiscal_year, _quarter = _fiscal_identity(current_start, current_end)
    document = Document(source, base.tables, admission.roles, fiscal_scope=fiscal_scope)
    has_prior = "prior_core_reconciliation" in admission.roles
    prior_note = has_prior or _prior_note_present(document, prior_end)
    return {
        pin.metric: _outcome(document, pin, prior_note)
        for pin in _pins(document, fiscal_year, current_end.year, has_prior)
    }


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
    )
    current_start, current_end, _prior_start, prior_end = _scope(document.fiscal_scope)
    fiscal_year, _quarter = _fiscal_identity(current_start, current_end)
    has_prior = "prior_core_reconciliation" in admission.roles
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
        if outcome.kind == "present" and outcome.primary is not None:
            facts.append(_present(definition=definition, value=outcome.value, document_id=document_id, bound=bound, receipt=_receipt(document, outcome.primary), event_id=event_id, period=period))
        elif outcome.kind == "conflict":
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, reason="cross_check_conflict", detail=f"envelope_conflict:{definition.metric}"))
        else:
            facts.append(_absent(definition=definition, document_id=document_id, event_id=event_id, detail=f"envelope_unlocated:{definition.metric}"))
    return facts


def wrapped_admit(source: str, fiscal_scope: Sequence[str | date]) -> Admission | None:
    if not _wrapped(source):
        return None
    document = _cached_document(source)
    if document is None:
        return Admission("unknown_table:t0")
    return _admission(document, fiscal_scope)
