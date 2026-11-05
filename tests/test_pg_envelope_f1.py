"""CDV-1 T1 first-release envelope, family F1-Q: the seat's witness suite, frozen before the build (R114, R116-R121;
GMI Meta-CEO direction on #7905, comment 5825632041).

Inputs are exact public SEC EDGAR exhibits, committed gzipped under ``tests/fixtures/pg_envelope/`` and pinned by the
sha256 of the bytes EDGAR serves (``SOURCES.md``).  Expected values are the independent oracle's (``oracle_f1.json``,
read from the raw bytes with no repository code); ``seat_adjudication.json`` corrects eight of its locators and no
value.  Every table/row/column locator is resolved by the stdlib grid reader in this file, which imports nothing from
``engine/``: the engine is only the system under test.
"""
from __future__ import annotations

import copy
import functools
import gzip
import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from engine.company_intelligence.documents import TypedAbsence
from engine.company_intelligence.economic_observations import EconomicObservationError, validate_selected_facts
from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.events import FiscalPeriod
import engine.company_intelligence.pg_profile as pgp
from engine.earnings_release.binding import bind_release_document
from engine.earnings_release.receipts import receipt_for_literal

FIX = Path(__file__).parent / "fixtures" / "pg_envelope"
ORACLE_FILES = {"oracle_f1.json": "75ec2190dba711a8c80f57fe309d02df481990d4f17e12c61822dcc32ab7a77c",
                "oracle_f1_notes.md": "7ca96abd5a8ba52e1452a40b0449af73401abca09be2f324ffe1ee5b0ac8e4f8",
                "oracle_f1_spec.md": "32a22721107f6bc38b34cc9a17f4119b6ae358ce2cf0628a06fa8c3f6f881ad4"}


@dataclass(frozen=True)
class Release:
    key: str
    file: str
    sha256: str  # of the bytes EDGAR serves
    size: int
    cik: str
    accession: str
    accepted: str
    filed: str
    fiscal: tuple[int, int, str]  # fiscal year, fiscal quarter, quarter end
    scope: tuple[str, str, str, str]  # quarter start and end, year-ago quarter start and end


FY25Q4 = Release("FY25Q4", "fy2425q4amj8-kexhibit991.htm", "6c625f3b78ba710da8a682e3ef5d5a57b157fd962f2d486154d9654ae25dcb6a", 454203,
                 "0000080424", "0000080424-25-000067", "2025-07-29T11:03:15Z", "2025-07-29", (2025, 4, "2025-06-30"),
                 ("2025-04-01", "2025-06-30", "2024-04-01", "2024-06-30"))
FY26Q1 = Release("FY26Q1", "fy2526q1jas8-kexhibit991.htm", "f3c987b34434671b6cad1f09c6fd42aa10701ac3c2a1fc62644b65c44e0dad96", 305212,
                 "0000080424", "0000080424-25-000240", "2025-10-24T11:04:27Z", "2025-10-24", (2026, 1, "2025-09-30"),
                 ("2025-07-01", "2025-09-30", "2024-07-01", "2024-09-30"))
FY26Q2 = Release("FY26Q2", "fy2526q2ond8-kexhibit991.htm", "f6d79042f16c6131100c6c6e678e96f43dd666b410356cc23cd43d7d1e032503", 296069,
                 "0000080424", "0000080424-26-000006", "2026-01-22T12:02:05Z", "2026-01-22", (2026, 2, "2025-12-31"),
                 ("2025-10-01", "2025-12-31", "2024-10-01", "2024-12-31"))
FY26Q3 = Release("FY26Q3", "fy2526q3jfm8-kexhibit991.htm", "eeef9d0de613e44ba3e4444c084431100491dd3a28a3b6226f0e8163ca770b84", 308066,
                 "0000080424", "0000080424-26-000056", "2026-04-24T11:01:47Z", "2026-04-24", (2026, 3, "2026-03-31"),
                 ("2026-01-01", "2026-03-31", "2025-01-01", "2025-03-31"))
FY26Q4 = Release("FY26Q4", "fy2526q4amj8-kexhibit991.htm", "9fe6812066a4ef6a1ca8b53b394ae0dbf2796eaef0c5141d2ae60fe94521dcbc", 472455,
                 "0000080424", "0000080424-26-000093", "2026-07-29T11:03:12Z", "2026-07-29", (2026, 4, "2026-06-30"),
                 ("2026-04-01", "2026-06-30", "2025-04-01", "2025-06-30"))
# The near neighbour: Colgate-Palmolive's Q2 2026 Ex-99 on the same Workiva template, run under P&G's FY26 Q4 scope.
COLGATE = Release("CL2Q26", "q22026pressreleasetables.htm", "a04042a7d643bea6bb3dc0aea14224e3705a4c56847d6694708897444f72d40e", 789706,
                  "0000021665", "0000021665-26-000041", "2026-07-31T11:58:00Z", "2026-07-31", FY26Q4.fiscal, FY26Q4.scope)
PG_RELEASES = (FY25Q4, FY26Q1, FY26Q2, FY26Q3, FY26Q4)
F1Q = (FY26Q1, FY26Q2, FY26Q3)
RELEASES = {r.key: r for r in (*PG_RELEASES, COLGATE)}

SALES, ORG = "pg_reported_sales_growth_pct", "pg_organic_sales_growth_pct"
TV, OV = "pg_total_volume_growth_pct", "pg_organic_volume_growth_pct"
PRICE, MIX, FX, OTHER = "pg_price_contribution_pp", "pg_mix_contribution_pp", "pg_fx_contribution_pp", "pg_other_contribution_pp"
DIL, PDIL, REPG = "pg_diluted_eps", "pg_prior_diluted_eps", "pg_reported_eps_growth_pct"
CORE, PCORE, COREG = "pg_core_eps", "pg_prior_core_eps", "pg_core_eps_growth_pct"
REC = "pg_core_reconciliation_context"
SEGMENTS = {"pg_beauty_organic_sales_growth_pct": "Beauty", "pg_grooming_organic_sales_growth_pct": "Grooming",
            "pg_health_care_organic_sales_growth_pct": "Health Care",
            "pg_fabric_home_organic_sales_growth_pct": "Fabric & Home Care",
            "pg_baby_feminine_family_organic_sales_growth_pct": "Baby, Feminine & Family Care"}
BEAUTY = "pg_beauty_organic_sales_growth_pct"
_BRIDGE = ("percentage_points", "reported_growth_bridge")
UNIT_BASIS = {SALES: ("percent", "reported_sales"), ORG: ("percent", "organic_sales"), TV: ("percent", "total_volume"),
              OV: ("percent", "organic_volume"), PRICE: _BRIDGE, MIX: _BRIDGE, FX: _BRIDGE, OTHER: _BRIDGE,
              DIL: ("usd_per_share", "gaap_diluted"), PDIL: ("usd_per_share", "gaap_diluted"),
              REPG: ("percent", "reported_eps_growth"), CORE: ("usd_per_share", "core_non_gaap"),
              PCORE: ("usd_per_share", "core_non_gaap"), COREG: ("percent", "core_eps_growth"),
              REC: ("text", "core_non_gaap_reconciliation"), **{m: ("percent", "organic_sales") for m in SEGMENTS}}
NUMERIC = tuple(m for m in UNIT_BASIS if m != REC)
PRIOR = {PDIL, PCORE}  # observations of the year-ago quarter; every other one is of the quarter itself

CONFLICT, UNLOCATED, EXCLUDED = "conflict", "unlocated", "excluded"
ABSENT = {CONFLICT: ("cross_check_conflict", "envelope_conflict"),
          UNLOCATED: ("no_span_addressable_evidence", "envelope_unlocated"),
          EXCLUDED: ("no_span_addressable_evidence", "envelope_excluded:pg_core_reconciliation_context")}


# --- the witness grid reader: stdlib only, independent of engine/ ---------------------------------------------------
_TABLE_OPEN = re.compile(r"<table\b", re.I)
_TABLE_CLOSE = re.compile(r"</table\s*>", re.I)
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr\s*>", re.I | re.S)
_CELL = re.compile(r"<t([dh])\b([^>]*)>(.*?)</t\1\s*>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_SPAN = {k: re.compile(k + r"""\s*=\s*["']?(\d+)""", re.I) for k in ("colspan", "rowspan")}
_LETTERS = re.compile(r"[A-Za-z].*[A-Za-z]", re.S)
_NOT_A_LABEL = {"n/a", "na", "nm", "bps"}  # value-position tokens that carry letters
UNIT_CELLS = {"$", "%"}


def text(fragment: str) -> str:
    return " ".join(html.unescape(_TAG.sub("", fragment)).replace("\xa0", " ").split())


def norm(label: str) -> str:
    return "".join(html.unescape(label).replace("\xa0", " ").split()).casefold()


@dataclass(frozen=True)
class Cell:
    table: int
    row: int
    col0: int
    col1: int
    start: int  # character offsets of the cell's content in the source
    end: int
    text: str


@functools.lru_cache(maxsize=None)
def tables(source: str) -> tuple[tuple[int, int], ...]:
    out = []
    for m in _TABLE_OPEN.finditer(source):
        close = _TABLE_CLOSE.search(source, m.end())
        if _TABLE_OPEN.search(source, m.end(), close.start()) is not None:
            raise ValueError("nested table: outside the pinned family's grammar")
        out.append((m.start(), close.end()))
    return tuple(out)


@functools.lru_cache(maxsize=None)
def grid(source: str, ordinal: int) -> tuple[tuple[Cell, ...], ...]:
    t0, t1 = tables(source)[ordinal]
    rows: list[tuple[Cell, ...]] = []
    carry: dict[int, tuple[int, Cell]] = {}  # grid column -> (rows remaining, cell)
    for r, rm in enumerate(_ROW.finditer(source, t0, t1)):
        row: list[Cell] = []
        col = 0
        pending, carry = dict(carry), {}

        def take_carried() -> None:
            nonlocal col
            while col in pending:
                left, cell = pending.pop(col)
                row.append(cell)
                if left > 1:
                    for c in range(cell.col0, cell.col1):
                        carry[c] = (left - 1, cell)
                col = cell.col1

        for cm in _CELL.finditer(rm.group(1)):
            take_carried()
            cs, rs = (int(m.group(1)) if (m := _SPAN[k].search(cm.group(2))) else 1 for k in ("colspan", "rowspan"))
            cell = Cell(ordinal, r, col, col + cs, rm.start(1) + cm.start(3), rm.start(1) + cm.end(3), text(cm.group(3)))
            row.append(cell)
            if rs > 1:
                for c in range(col, col + cs):
                    carry[c] = (rs - 1, cell)
            col += cs
        take_carried()
        rows.append(tuple(row))
    return tuple(rows)


def is_label(value: str) -> bool:
    return bool(_LETTERS.search(value)) and norm(value) not in _NOT_A_LABEL


def label_of(row, cell: Cell) -> str | None:
    """The nearest cell to the left holding a label."""
    best = None
    for other in row:
        if other.col1 <= cell.col0 and is_label(other.text) and other is not cell:
            if best is None or other.col1 > best.col1:
                best = other
    return best.text if best else None


def headers_over(rows, cell: Cell) -> list[str]:
    """Texts above the cell that stand over every grid column it occupies: covering cells, and title rows (one filled
    cell) over all of them (R168)."""
    def column(index: int) -> list[str]:
        out = []
        for row in rows[: cell.row]:
            filled = [o for o in row if o.text and o.row < cell.row]
            if len({id(o) for o in filled}) == 1:
                out.append(filled[0].text)
                continue
            out.extend(o.text for o in filled if o.col0 <= index < o.col1)
        return out

    first, *others = (column(index) for index in range(cell.col0, cell.col1))
    return [h for h in first if all(norm(h) in {norm(x) for x in other} for other in others)]


def own_cells(source: str, ordinal: int):
    """Every cell once, in the row it starts in (a rowspan carry belongs to its first row)."""
    rows = grid(source, ordinal)
    return rows, [(r, c) for r, row in enumerate(rows) for c in row if c.row == r]


def resolve(source: str, ordinal: int, row_label: str, column_header: str, cell_text: str) -> list[Cell]:
    rows, cells = own_cells(source, ordinal)
    return [c for r, c in cells if norm(c.text) == norm(cell_text) and norm(label_of(rows[r], c) or "") == norm(row_label)
            and norm(column_header) in {norm(h) for h in headers_over(rows, c)}]


def locate(source: str, pin) -> list[Cell]:
    """The value cells a pinned (table, row label, column header) names; unit-only cells are never values.  A pin with
    no column header names the number printed beside a separate percent-sign cell ("Core EPS | 3 | %")."""
    ordinal, row_label, header = pin
    rows, cells = own_cells(source, ordinal)
    if header is None:
        hits = []
        for r, c in cells:
            if norm(c.text) == norm(row_label):
                after = sorted((o for o in rows[r] if o.row == r and o.col0 >= c.col1 and o.text), key=lambda o: o.col0)
                if len(after) >= 2 and after[1].text == "%":
                    hits.append(after[0])
        return hits
    return [c for r, c in cells if c.text and c.text not in UNIT_CELLS and norm(label_of(rows[r], c) or "") == norm(row_label)
            and norm(header) in {norm(h) for h in headers_over(rows, c)}]


def one(source: str, pin) -> Cell:
    hits = locate(source, pin)
    assert len(hits) == 1, (pin, [h.text for h in hits])
    return hits[0]


def literal(printed: str) -> float:
    """A printed figure's value: a dash where a number belongs is zero in F1-Q, parentheses are negative."""
    s = printed.replace(" ", "")
    if s in ("—", "—%"):
        return 0.0
    if m := re.fullmatch(r"\((\d+(?:\.\d+)?)\)%?", s):
        return -float(m.group(1))
    if m := re.fullmatch(r"[+$]?(\d+(?:\.\d+)?)%?", s):
        return float(m.group(1))
    raise ValueError(printed)


# --- the frozen F1-Q bindings ----------------------------------------------------------------------------------------
# Table ordinals by role.  FY26 Q1 prints the year-ago quarter's Core EPS in a reconciliation table of its own.
F1Q_TABLES = {"FY26Q1": {"highlights": 2, "segment_drivers": 3, "earnings": 4, "drivers": 6, "core_reconciliation": 9,
                         "change_versus_year_ago": 10, "prior_core_reconciliation": 11, "organic_reconciliation": 12},
              "FY26Q2": {"highlights": 2, "segment_drivers": 3, "earnings": 4, "drivers": 6, "core_reconciliation": 9,
                         "change_versus_year_ago": 10, "organic_reconciliation": 11}}
F1Q_TABLES["FY26Q3"] = F1Q_TABLES["FY26Q2"]
EPS_ROW = {"FY26Q1": "Diluted net earnings per common share (1)", "FY26Q2": "Diluted net earnings per common share (2)",
           "FY26Q3": "Diluted net earnings per common share (2)"}
# The footnote under the core reconciliation that lets its year-ago GAAP column stand as the year-ago Core EPS; it is
# read between that table and the next one, whitespace ignored (the release sets the "(1)" marker in its own element).
NO_ADJUSTMENT_NOTE = {
    "FY26Q2": "(1) For the three months ended December 31, 2024, there were no adjustments to or reconciling items for Core EPS.",
    "FY26Q3": "(1) For the three months ended March 31, 2025, there were no adjustments to or reconciling items for Core EPS."}


def pins(rel: Release) -> dict[str, tuple[tuple, tuple]]:
    """metric -> (primary statement, second printed statement), each (table ordinal, row label, column header)."""
    t, fy, cal, eps = F1Q_TABLES[rel.key], rel.fiscal[0], date.fromisoformat(rel.fiscal[2]).year, EPS_ROW[rel.key]
    p = {}
    for m, col in ((SALES, "Net Sales"), (TV, "Volume"), (OV, "Organic Volume"), (PRICE, "Price"), (MIX, "Mix"),
                   (FX, "Foreign Exchange"), (OTHER, "Other (2)")):
        p[m] = ((t["segment_drivers"], "Total P&G", col), (t["drivers"], "Total Company", col))
    p[ORG] = ((t["organic_reconciliation"], "Total Company", "Organic Sales Growth"), (t["segment_drivers"], "Total P&G", "Organic Sales"))
    for m, segment in SEGMENTS.items():
        p[m] = ((t["organic_reconciliation"], segment, "Organic Sales Growth"), (t["segment_drivers"], segment, "Organic Sales"))
    p[DIL] = ((t["earnings"], "Diluted", str(cal)), (t["highlights"], "Diluted EPS", str(fy)))
    p[PDIL] = ((t["earnings"], "Diluted", str(cal - 1)), (t["highlights"], "Diluted EPS", str(fy - 1)))
    p[REPG] = ((t["earnings"], "Diluted", "% Chg"), (t["highlights"], "Diluted EPS", "% Change"))
    p[CORE] = ((t["core_reconciliation"], eps, "Core(Non-GAAP)"), (t["highlights"], "Core EPS", str(fy)))
    p[PCORE] = ((t["highlights"], "Core EPS", str(fy - 1)),
                (t["prior_core_reconciliation"], "Diluted net earnings per common share (1)", "Core(Non-GAAP)")
                if "prior_core_reconciliation" in t else (t["core_reconciliation"], eps, "As Reported (GAAP) (1)"))
    p[COREG] = ((t["highlights"], "Core EPS", "% Change"), (t["change_versus_year_ago"], "Core EPS", None))
    return p


def witness_outcome(source: str, rel: Release) -> dict[str, object]:
    """What the pinned table reads from ``source``: the agreed value, CONFLICT, or UNLOCATED."""
    t, note, out = F1Q_TABLES[rel.key], NO_ADJUSTMENT_NOTE.get(rel.key), {}
    for m, (a, b) in pins(rel).items():
        ha, hb = locate(source, a), locate(source, b)
        if m == PCORE and note is not None:
            after, following = tables(source)[t["core_reconciliation"]][1], tables(source)[t["core_reconciliation"] + 1][0]
            if norm(note) not in norm(text(source[after:following])):
                hb = []
        if len(ha) != 1 or len(hb) != 1:
            out[m] = UNLOCATED
        else:
            va, vb = literal(ha[0].text), literal(hb[0].text)
            out[m] = va if va == vb else CONFLICT
    return out


# --- mutations of FY26 Q3: each swaps the whole content of two cells of one statement --------------------------------
_Q3 = F1Q_TABLES["FY26Q3"]
MUTATIONS = {
    "period_single": ([(_Q3["earnings"], "2026", "2025")], {DIL: CONFLICT, PDIL: CONFLICT}),
    "period_both": ([(_Q3["earnings"], "2026", "2025"), (_Q3["highlights"], "2026", "2025")], {DIL: 1.54, PDIL: 1.63}),
    "row_single": ([(_Q3["organic_reconciliation"], "Total Company", "Beauty")], {ORG: CONFLICT, BEAUTY: CONFLICT}),
    "row_both": ([(_Q3["organic_reconciliation"], "Total Company", "Beauty"), (_Q3["segment_drivers"], "Total P&G", "Beauty")],
                 {SALES: CONFLICT, TV: CONFLICT, OV: CONFLICT, MIX: CONFLICT, ORG: 7.0, BEAUTY: 3.0}),
    "column_single": ([(_Q3["segment_drivers"], "Price", "Mix")], {PRICE: CONFLICT, MIX: CONFLICT}),
    "column_both": ([(_Q3["segment_drivers"], "Price", "Mix"), (_Q3["drivers"], "Price", "Mix")], {PRICE: 0.0, MIX: 1.0}),
    "basis_single": ([(_Q3["core_reconciliation"], "As Reported (GAAP)", "Core(Non-GAAP)")], {CORE: CONFLICT}),
    "basis_both": ([(_Q3["core_reconciliation"], "As Reported (GAAP)", "Core(Non-GAAP)"), (_Q3["highlights"], "Diluted EPS", "Core EPS")],
                   {DIL: CONFLICT, REPG: CONFLICT, CORE: 1.63, COREG: CONFLICT}),
    # The footnote no longer says the year-ago quarter had no adjustments, so its GAAP column is no second statement.
    "note_removed": ([("no adjustments to or reconciling items", "adjustments to and reconciling items")], {PCORE: UNLOCATED}),
}


def swap(source: str, ordinal: int, a: str, b: str) -> str:
    _, cells = own_cells(source, ordinal)
    x, y = sorted((next(c for _, c in cells if c.text == a), next(c for _, c in cells if c.text == b)), key=lambda c: c.start)
    return source[:x.start] + source[y.start:y.end] + source[x.end:y.start] + source[x.start:x.end] + source[y.end:]


def once(source: str, old: str, new: str) -> str:
    assert source.count(old) == 1, old
    return source.replace(old, new)


def mutate(source: str, steps) -> str:
    for step in steps:
        source = swap(source, *step) if len(step) == 3 else once(source, *step)
    return source


def in_table(source: str, ordinal: int, old: str, new: str) -> str:
    t0, t1 = tables(source)[ordinal]
    return source[:t0] + once(source[t0:t1], old, new) + source[t1:]


def drop_table(source: str, ordinal: int) -> str:
    t0, t1 = tables(source)[ordinal]
    return source[:t0] + source[t1:]


def repeat_table(source: str, ordinal: int) -> str:
    t0, t1 = tables(source)[ordinal]
    return source[:t1] + source[t0:t1] + source[t1:]


def after_table(source: str, ordinal: int, fragment: str) -> str:
    t1 = tables(source)[ordinal][1]
    return source[:t1] + fragment + source[t1:]


INJECTED_TABLE = "<table><tr><td>Pro Forma Combined Company</td><td>5%</td></tr></table>"
_ANY_UNKNOWN_TABLE = re.compile(r"envelope_refused:unknown_table:t\d+")  # the Q4 layouts: whichever table is first unknown
REFUSED = {  # case -> (release, rewrite of its source, fiscal period it is run under, the refusal detail every row carries)
    "type_ex_99_2": (FY26Q3, lambda s: once(s, "<TYPE>EX-99.1\n", "<TYPE>EX-99.2\n"), FY26Q3, "envelope_refused:not_ex_99_1"),
    "generator_removed": (FY26Q3, lambda s: once(s, "<!-- Document created using Wdesk -->\n", ""), FY26Q3,
                          "envelope_refused:generator_not_workiva"),
    "masthead_other_issuer": (FY26Q3, lambda s: in_table(s, 0, "The Procter &#38; Gamble Company", "The Clorox Company"), FY26Q3,
                              "envelope_refused:issuer_not_pg"),
    "table_injected": (FY26Q3, lambda s: after_table(s, _Q3["drivers"], INJECTED_TABLE), FY26Q3, "envelope_refused:unknown_table:t7"),
    "drivers_removed": (FY26Q3, lambda s: drop_table(s, _Q3["drivers"]), FY26Q3, "envelope_refused:required_table_missing:drivers"),
    "drivers_repeated": (FY26Q3, lambda s: repeat_table(s, _Q3["drivers"]), FY26Q3, "envelope_refused:required_table_repeated:drivers"),
    "q3_under_q2_scope": (FY26Q3, None, FY26Q2, "envelope_refused:quarter_mismatch"),
    "fy25_q4_layout": (FY25Q4, None, FY25Q4, _ANY_UNKNOWN_TABLE),
    "fy26_q4_layout": (FY26Q4, None, FY26Q4, _ANY_UNKNOWN_TABLE),
    "colgate": (COLGATE, None, FY26Q4, "envelope_refused:not_ex_99_1"),
    "colgate_as_ex_99_1": (COLGATE, lambda s: once(s, "<TYPE>EX-99\n", "<TYPE>EX-99.1\n"), FY26Q4, "envelope_refused:issuer_not_pg"),
}


# --- fixtures, oracle and workspaces ---------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def original(rel: Release) -> str:
    data = gzip.decompress((FIX / f"{rel.file}.gz").read_bytes())
    assert (hashlib.sha256(data).hexdigest(), len(data)) == (rel.sha256, rel.size), rel.file
    return data.decode("utf-8")


@functools.lru_cache(maxsize=None)
def oracle() -> dict:
    return json.loads((FIX / "oracle_f1.json").read_text(encoding="utf-8"))


def oracle_doc(rel: Release) -> dict:
    return next(d for d in oracle()["documents"] if d["file"] == rel.file)


def adjudication() -> dict:
    return json.loads((FIX / "seat_adjudication.json").read_text(encoding="utf-8"))


def expected_values(rel: Release) -> dict[str, object]:
    return {m: oracle_doc(rel)["metrics"][m]["expected"] for m in NUMERIC}


def oracle_cells(source: str, rel: Release, metric: str) -> set[tuple[int, int]]:
    """Every table cell the oracle records for ``metric``, with the seat's locator corrections applied.  Entries in the
    headline table (ordinal 1) or with no table quote headline prose and are not locators."""
    fixes = {c["entry"]: c["corrected"] for c in adjudication()["locator_corrections"]
             if (c["release"], c["metric"]) == (rel.key, metric)}
    entry, out = oracle_doc(rel)["metrics"][metric], set()
    primary = entry["locator"] and {**entry["locator"], "cell_text": entry["cell_text"]}  # its cell text sits on the entry
    for name, loc in [("locator", primary), *((f"also_found[{i}]", a) for i, a in enumerate(entry["also_found"]))]:
        if not loc or loc.get("table_ordinal") in (None, 1):
            continue
        hits = resolve(source, loc["table_ordinal"], loc["row_label"], fixes.get(name, loc["column_header"]), loc["cell_text"])
        assert len(hits) == 1, (metric, name, loc)
        out.add((hits[0].table, hits[0].start))
    return out


def exhibit_url(rel: Release) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(rel.cik)}/{rel.accession.replace('-', '')}/{rel.file}"


def workspace(rel: Release, body: str, period: Release):
    filing = {"cik": rel.cik, "accession": rel.accession, "form": "8-K", "filing_date": rel.filed,
              "acceptance_datetime": rel.accepted, "report_date": rel.filed, "exhibit_url": exhibit_url(rel)}
    bound = bind_release_document(body=body, content_type="text/html", **filing)
    year, quarter, end = period.fiscal
    ws = build_event_workspace(registry=pgp.pg_private_registry(), ticker="PG", asof=date.fromisoformat(rel.filed),
                               fiscal_period=FiscalPeriod(year=year, quarter=quarter, calendar_end=date.fromisoformat(end)),
                               exhibit_body=bound.source, filing=filing, transcript=None, observed_at=rel.accepted,
                               source_available_at=rel.accepted, profile=pgp.pg_profile(fiscal_scope=period.scope))
    return ws, {bound.revision.document_id: bound.source}, bound


@functools.lru_cache(maxsize=None)
def case(name: str):
    """A built workspace, shared read-only between tests; a test that tampers with one deep-copies it first."""
    if name in RELEASES:
        return workspace(RELEASES[name], original(RELEASES[name]), RELEASES[name])
    kind, _, key = name.partition(":")
    if kind == "mutation":
        return workspace(FY26Q3, mutate(original(FY26Q3), MUTATIONS[key][0]), FY26Q3)
    rel, rewrite, period, _ = REFUSED[key]
    return workspace(rel, rewrite(original(rel)) if rewrite else original(rel), period)


def pg_rows(ws) -> list[dict]:
    return [f for f in ws["facts"] if isinstance(f, dict) and str(f.get("metric", "")).startswith("pg_")]


def by_metric(ws) -> dict[str, dict]:
    return {f["metric"]: f for f in pg_rows(ws)}


def byte_offset(source: str, index: int) -> int:
    return len(source[:index].encode("utf-8"))


def assert_envelope(ws, texts, source: str, rel: Release, expected: dict[str, object]) -> None:
    """Each metric is present in its pinned primary cell with its frozen value, unit, basis and period, or a typed
    absence of the frozen kind; and the validator accepts the workspace unchanged."""
    rows, primary = by_metric(ws), {m: a for m, (a, _) in pins(rel).items()}
    assert set(rows) == set(UNIT_BASIS)
    for m, want in expected.items():
        row = rows[m]
        if want in ABSENT:
            reason, detail = ABSENT[want]
            absence = row.get("typed_absence") or {}
            assert row.get("value") is None, (m, row.get("value"))
            assert absence.get("reason") == reason and str(absence.get("detail", "")).startswith(detail), (m, absence)
            continue
        assert row.get("typed_absence") is None and row.get("value") == pytest.approx(want), (m, row.get("value"), row.get("typed_absence"))
        assert (row.get("unit"), row.get("basis")) == UNIT_BASIS[m], m
        assert row.get("period") == (rel.scope[3] if m in PRIOR else rel.scope[1]), (m, row.get("period"))
        cell, receipt = one(source, primary[m]), row["source_span"]["receipt"]
        start, end = receipt["span_start_byte"], receipt["span_end_byte"]
        assert byte_offset(source, cell.start) <= start < end <= byte_offset(source, cell.end), (m, cell.text)
        assert literal(text(source.encode("utf-8")[start:end].decode("utf-8"))) == pytest.approx(want), m
    assert validate_selected_facts(ws, source_texts=texts, fiscal_scope=rel.scope) == pg_rows(ws)


# --- the frozen inputs are what they claim to be ---------------------------------------------------------------------
def test_fixtures_are_the_bytes_edgar_serves():
    for rel in RELEASES.values():
        assert original(rel).startswith("<DOCUMENT>\n<TYPE>EX-99"), rel.file


def test_oracle_is_the_frozen_independent_read():
    for name, digest in ORACLE_FILES.items():
        assert hashlib.sha256((FIX / name).read_bytes()).hexdigest() == digest, name
    assert oracle()["family"] == "F1_pg_workiva_ex991"
    assert {d["file"]: d["sha256"] for d in oracle()["documents"]} == {r.file: r.sha256 for r in PG_RELEASES}
    for d in oracle()["documents"]:
        assert set(d["metrics"]) == set(UNIT_BASIS), d["file"]


def test_seat_adjudication_corrects_locators_and_no_value():
    adj = adjudication()
    assert adj["oracle"]["sha256"] == ORACLE_FILES["oracle_f1.json"] and adj["value_changes"] == []
    assert len(adj["locator_corrections"]) == 8
    for c in adj["locator_corrections"]:
        rel = RELEASES[c["release"]]
        loc = oracle_doc(rel)["metrics"][c["metric"]]["also_found"][int(c["entry"][len("also_found["):-1])]
        assert (loc["table_ordinal"], loc["column_header"], loc["cell_text"]) == (2, c["oracle"], c["cell_text"]), c
        assert len(resolve(original(rel), 2, loc["row_label"], c["corrected"], loc["cell_text"])) == 1, c


def test_frozen_units_agree_with_the_oracle():
    words = {"percent": "percent", "USD per share": "usd_per_share", "text": "text"}
    deviation = adjudication()["unit_label_deviation"]
    for d in oracle()["documents"]:
        for m, entry in d["metrics"].items():
            if m in deviation["metrics"]:
                assert (entry["unit"], UNIT_BASIS[m][0]) == (deviation["oracle"], deviation["binding"]), (d["file"], m)
            elif entry["unit"] is not None:
                assert words[entry["unit"]] == UNIT_BASIS[m][0], (d["file"], m)


@pytest.mark.parametrize("rel", F1Q, ids=lambda r: r.key)
def test_frozen_pins_reproduce_the_oracle(rel):
    """Both printed statements of every metric agree with the oracle, the primary is a cell the oracle recorded, and
    the two statements sit in different tables."""
    source = original(rel)
    assert witness_outcome(source, rel) == expected_values(rel)
    for m, (a, b) in pins(rel).items():
        assert a[0] != b[0], m
        cell = one(source, a)
        assert (cell.table, cell.start) in oracle_cells(source, rel, m), m


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_frozen_mutation_outcomes_follow_from_the_pins(name):
    steps, delta = MUTATIONS[name]
    assert witness_outcome(mutate(original(FY26Q3), steps), FY26Q3) == {**expected_values(FY26Q3), **delta}


# --- admitted F1-Q releases bind the frozen bindings -----------------------------------------------------------------
@pytest.mark.parametrize("rel", F1Q, ids=lambda r: r.key)
def test_admitted_release_binds_the_frozen_bindings(rel):
    ws, texts, bound = case(rel.key)
    assert_envelope(ws, texts, bound.source, rel, {**expected_values(rel), REC: EXCLUDED})


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_a_swap_in_one_statement_conflicts_and_in_both_binds_the_swapped_values(name):
    ws, texts, bound = case(f"mutation:{name}")
    assert_envelope(ws, texts, bound.source, FY26Q3, {**expected_values(FY26Q3), **MUTATIONS[name][1], REC: EXCLUDED})


# --- documents outside the envelope refuse, every metric, with a typed state -----------------------------------------
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_document_outside_the_envelope_refuses_every_metric(name):
    ws, texts, _ = case(f"refused:{name}")
    period, detail = REFUSED[name][2], REFUSED[name][3]
    rows = pg_rows(ws)
    assert {r["metric"] for r in rows} == set(UNIT_BASIS) and len(rows) == len(UNIT_BASIS)
    pattern = detail if isinstance(detail, re.Pattern) else re.compile(re.escape(detail))
    for row in rows:
        absence = row.get("typed_absence") or {}
        assert row.get("value") is None, (row["metric"], row.get("value"))
        assert absence.get("reason") == "no_span_addressable_evidence", (row["metric"], absence)
        assert pattern.fullmatch(str(absence.get("detail", ""))), (row["metric"], absence.get("detail"))
    assert len({r["typed_absence"]["detail"] for r in rows}) == 1
    assert validate_selected_facts(ws, source_texts=texts, fiscal_scope=period.scope) == rows


# --- the validator re-derives; it does not replay the extractor's selection ------------------------------------------
def _doc(ws) -> str:
    return next(s["document_id"] for s in ws["sources"] if s.get("kind") == "issuer_release")


def _row(ws, metric) -> dict:
    return next(f for f in ws["facts"] if isinstance(f, dict) and f.get("metric") == metric)


def _replaced(ws, metric, row):
    ws = copy.deepcopy(ws)
    ws["facts"][ws["facts"].index(_row(ws, metric))] = row
    return ws


def _fact_id(ws, metric, middle) -> str:
    return "fact_" + hashlib.sha256("|".join((ws["event_id"], metric, middle, UNIT_BASIS[metric][1])).encode()).hexdigest()[:16]


def _forged_present(ws, bound, metric, cell, printed, value, period):
    receipt = receipt_for_literal(source=bound.source, source_sha256=bound.revision.source_sha256,
                                  search_start=cell.start, search_end=cell.end, literal=printed)
    unit, basis = UNIT_BASIS[metric]
    return {"schema": "event_fact.v1", "fact_id": _fact_id(ws, metric, period), "event_id": ws["event_id"], "metric": metric,
            "value": value, "unit": unit, "period": period, "basis": basis, "source_span": pgp._span(_doc(ws), bound, receipt)}


def _absence(ws, metric, reason, detail):
    return {"schema": "event_fact.v1", "fact_id": _fact_id(ws, metric, metric), "event_id": ws["event_id"], "metric": metric,
            "typed_absence": TypedAbsence(reason=reason, subject=metric, detail=detail, event_id=ws["event_id"],
                                          document_id=_doc(ws)).to_payload()}


def _refuses(ws, texts, rel):
    with pytest.raises(EconomicObservationError):
        validate_selected_facts(ws, source_texts=texts, fiscal_scope=rel.scope)


def test_v1_a_span_moved_to_another_metrics_cell_is_refused():
    ws, texts, _ = case("FY26Q1")
    price, fx = _row(ws, PRICE), _row(ws, FX)
    assert price.get("value") is not None and price.get("value") == fx.get("value")
    ws = copy.deepcopy(ws)
    price, fx = _row(ws, PRICE), _row(ws, FX)
    price["source_span"], fx["source_span"] = fx["source_span"], price["source_span"]
    _refuses(ws, texts, FY26Q1)


def test_v2_a_value_that_is_not_its_cells_literal_is_refused():
    ws, texts, _ = case("FY26Q3")
    assert _row(ws, DIL).get("value") == pytest.approx(1.63)
    ws = copy.deepcopy(ws)
    _row(ws, DIL)["value"] = 1.64
    _refuses(ws, texts, FY26Q3)


def test_v3_a_refused_document_admits_no_present_fact():
    ws, texts, bound = case("refused:colgate")
    hits = resolve(bound.source, 1, "Total Company", "Organic Sales*", "+2.4%")  # Colgate's own organic sales growth
    assert len(hits) == 1
    forged = _forged_present(ws, bound, ORG, hits[0], "2.4", 2.4, COLGATE.scope[1])
    _refuses(_replaced(ws, ORG, forged), texts, COLGATE)


def test_v4_a_value_its_second_statement_contradicts_is_refused():
    ws, texts, bound = case("mutation:period_single")
    cell = one(bound.source, pins(FY26Q3)[DIL][0])
    assert cell.text == "1.54"
    forged = _forged_present(ws, bound, DIL, cell, "1.54", 1.54, FY26Q3.scope[1])
    _refuses(_replaced(ws, DIL, forged), texts, FY26Q3)


@pytest.mark.parametrize("reason, detail", [("no_span_addressable_evidence", "forged"),
                                            ("cross_check_conflict", "envelope_conflict:forged")], ids=["plain", "conflict"])
def test_v5_an_absence_that_hides_an_agreed_value_is_refused(reason, detail):
    ws, texts, _ = case("FY26Q3")
    assert _row(ws, ORG).get("value") == pytest.approx(3.0)
    _refuses(_replaced(ws, ORG, _absence(ws, ORG, reason, detail)), texts, FY26Q3)


def test_v6_a_refusal_code_the_bytes_do_not_support_is_refused():
    ws, texts, _ = case("refused:type_ex_99_2")
    assert {(r.get("typed_absence") or {}).get("detail") for r in pg_rows(ws)} == {"envelope_refused:not_ex_99_1"}
    ws = copy.deepcopy(ws)
    for row in pg_rows(ws):
        row["typed_absence"]["detail"] = "envelope_refused:issuer_not_pg"
    _refuses(ws, texts, FY26Q3)
