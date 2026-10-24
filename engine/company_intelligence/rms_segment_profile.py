"""Closed reported LMT RMS quarter cells using the incumbent receipt owners.

These are segment observations, not fleet allocations or program workshare.
The separate supplement retains its actual byte-version observation clock.
"""
import re

from engine.company_intelligence.documents import text_span, verify_span
from engine.company_intelligence.defense_profiles import (
    _cells, _current_column, _row_for, _selected_number,
)
from engine.company_intelligence.defense_cash_profiles import _columns
from engine.earnings_release.receipts import receipt_for_literal, receipt_for_char_span, replay_receipt
from engine.earnings_release.figures import parse_numeric
from engine.fundamental_forensics.disclosure_diff import normalize_filing

BASIS = "issuer_reported_segment:Rotary and Mission Systems:reported"
URL = "https://www.sec.gov/Archives/edgar/data/936468/000162828026049277/ex991q22026.htm"
EVENT = "evt_cik0000936468_2026q2_results"
AVAILABILITY = "conservative_actual_retrieval_byte_version_unreconciled"
ROWS = (
    ("sales", "Sales", "reported_segment_sales", "USD_million"),
    ("operating_profit", "Operating profit (loss)", "reported_segment_operating_profit", "USD_million"),
    ("margin", "Operating margin", "reported_segment_margin", "percent"),
)


def numeric_rules():
    return {
        "fleet_rms_" + metric + ("_prior" if prior else ""):
        (fact_class, unit, BASIS, "2025Q2" if prior else "2026Q2")
        for metric, _, fact_class, unit in ROWS for prior in (False, True)
    }


def receipt_value(excerpt, metric):
    """Parse a literal, or the report's closed two-cell negative-percent form.

    The wrapper is parser context only. Receipts always quote the original
    contiguous source bytes, including both cells; no wrapper is certified.
    """
    if not isinstance(excerpt,str):
        raise ValueError("RMS_numeric_receipt_unqualified")
    direct = parse_numeric(excerpt)
    if direct is not None:
        return direct[0]
    if metric not in ("fleet_rms_margin", "fleet_rms_margin_prior"):
        raise ValueError("RMS_numeric_receipt_unqualified")
    if not excerpt.startswith("<td ") or not excerpt.endswith("</td>"):
        raise ValueError("RMS_split_percent_source_shape_unqualified")
    doc = normalize_filing({"content":"<table><tr>"+excerpt+"</tr></table>", "accession":"RMS-literal"})
    if len(doc.blocks)!=1 or not doc.blocks[0].table or len(doc.blocks[0].table.rows)!=1:
        raise ValueError("RMS_split_percent_table_unqualified")
    cells = doc.blocks[0].table.rows[0]
    if (len(cells)!=2 or cells[0].colspan!=2 or cells[1].colspan!=1
            or any(c.rowspan!=1 or c.span_overflow for c in cells)
            or not re.fullmatch(r"\(\d+(?:\.\d+)?",cells[0].text)
            or cells[1].text!="%)"):
        raise ValueError("RMS_split_percent_cells_unqualified")
    return parse_numeric(cells[0].text+")")[0]


def numeric_facts(*, document, body, digest, event_id):
    headings = [i for i, block in enumerate(document.blocks)
                if block.text.strip() == "Rotary and Mission Systems" and not block.table]
    if len(headings) != 1:
        raise ValueError("RMS_segment_heading_missing_or_ambiguous")
    index = headings[0] + 1
    if index >= len(document.blocks) or not document.blocks[index].table:
        raise ValueError("RMS_segment_table_missing")
    table = document.blocks[index]
    fiscal, current, _ = _current_column(table, "LMT")
    if (fiscal.year, fiscal.quarter) != (2026, 2):
        raise ValueError("RMS_quarter_period_mismatch")
    header = " ".join(c.text for row in table.table.rows[:5] for c in _cells(row)).lower()
    if "million" not in header or not any("$" in c.text for row in table.table.rows for c in row):
        raise ValueError("RMS_USD_million_units_unqualified")
    columns, positions = _columns(table, "Quarters Ended", 2026)
    if columns[0] != current:
        raise ValueError("RMS_current_quarter_column_mismatch")
    result = []
    for metric, label, fact_class, unit in ROWS:
        row = _row_for(table, "LMT", label)
        if row is None:
            raise ValueError("RMS_reported_row_missing_or_ambiguous")
        for prior, column in zip((False, True), columns):
            name = "fleet_rms_" + metric + ("_prior" if prior else "")
            try:
                cell, value = _selected_number(row, column, positions)
            except ValueError:
                selected=[c for c in row if column[0]<=positions[c.cell_id][0]<positions[c.cell_id][1]<=column[1] and c.text.strip()]
                if (unit!="percent" or len(selected)!=2
                        or positions[selected[0].cell_id][0]!=column[0]
                        or positions[selected[0].cell_id][1]!=positions[selected[1].cell_id][0]
                        or positions[selected[1].cell_id][1]!=column[1]):
                    raise ValueError("RMS_split_percent_quarter_geometry_unqualified")
                receipt=receipt_for_char_span(
                    source=body,source_sha256=digest,
                    char_start=selected[0].source_span.char_start,
                    char_end=selected[1].source_span.char_end,
                )
                value=receipt_value(receipt.span_text,name)
            else:
                literal = cell.text.strip()
                if not re.fullmatch(r"(?:-?\d+(?:,\d{3})*(?:\.\d+)?|\(\d+(?:,\d{3})*(?:\.\d+)?\))%?", literal):
                    raise ValueError("RMS_numeric_literal_unqualified")
                receipt = receipt_for_literal(
                    source=body, source_sha256=digest, literal=literal,
                    search_start=cell.source_span.char_start, search_end=cell.source_span.char_end,
                )
            replay_receipt(receipt, source=body)
            span = text_span(
                document_id=document.document_id, document_version=1,
                body_sha256=digest, segment_index=0, segment_text=body,
                start_byte=receipt.byte_start, end_byte=receipt.byte_end,
                text=receipt.span_text, rights_profile="rp_public_primary_v1",
            )
            verify_span(span, segment_text=body, body_sha256=digest)
            result.append({
                "schema": "event_fact.v1", "fact_id": event_id + ":" + name,
                "event_id": event_id, "metric": name, "value": value, "unit": unit,
                "period": "2025Q2" if prior else "2026Q2", "basis": BASIS,
                "fact_class": fact_class, "source_span": span.to_payload(),
            })
    return result
