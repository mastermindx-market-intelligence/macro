"""capital-structure-document-terms/1.3.0: three measured parser-gap closures.

Real-EDGAR fixtures named ``p130_*.txt`` (never an ``ex107_`` name, which the
1.2.0 suite counts) pin each new rule against the filing bytes it was measured
on.  Released 1.1.0 and 1.2.0 behavior must stay byte-identical: the
invariance tests re-derive every released fixture and every p130 fixture
under 1.2.0 and compare.
"""
from __future__ import annotations

import dataclasses
from hashlib import sha256
import re
from pathlib import Path

import pytest

import engine.capital_structure.document_terms as document_terms
from engine.capital_structure.document_terms import compile_document_term_records
from engine.capital_structure.source_identity import manifest_id_for

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests/fixtures/capital_structure/document_terms"
P130_FIXTURES = sorted(FIXTURE_DIR.glob("p130_*.txt"))

V1_2_0 = "capital-structure-document-terms/1.2.0"
V1_3_0 = "capital-structure-document-terms/1.3.0"

AGGREGATE = "proposed_maximum_aggregate_offering_price"


def _p130_identity(raw: bytes) -> tuple[str, str, str]:
    """The accession, form, and CIK pinned inside one committed envelope."""
    accession = re.search(
        rb"^<SEC-DOCUMENT>([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt", raw, re.MULTILINE,
    ).group(1).decode("ascii")
    form = re.search(
        rb"^CONFORMED SUBMISSION TYPE:\s*(\S+)", raw, re.MULTILINE,
    ).group(1).decode("ascii")
    cik = re.search(
        rb"^[ \t]*CENTRAL INDEX KEY:[ \t]*([0-9]+)", raw, re.MULTILINE,
    ).group(1).decode("ascii")
    return accession, form, cik


def _p130_manifest(raw: bytes) -> dict:
    accession, form, cik = _p130_identity(raw)
    digest = sha256(raw).hexdigest()
    record = {
        "schema": "capital_structure.source_manifest/v1",
        "source_system": "sec_edgar",
        "source_id": f"{accession}:0:complete-submission.txt",
        "issuer": {
            "issuer_id": f"sec:cik:{cik}", "cik": cik, "ticker": "ABC",
            "aliases": ["ABC Corp"],
        },
        "filing": {
            "accession": accession, "form": form,
            "filing_date": "2026-08-01", "accepted_at": "2026-08-01T11:00:00Z",
            "file_number": "333-123456",
        },
        "document": {
            "canonical_url": (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession.replace('-', '')}/{accession}.txt"
            ),
            "document_name": "complete-submission.txt", "document_type": form,
            "document_role": "complete_submission", "sequence": "0",
            "media_type": "text/plain", "byte_length": len(raw),
            "document_version": 1, "content_sha256": digest,
            "parent_manifest_id": None, "root_locator": f"sha256:{digest}",
        },
        "retrieval": {
            "retrieved_at": "2026-08-02T12:00:00Z",
            "first_seen_at": "2026-08-02T12:00:00Z", "transport_status": "retrieved",
        },
        "storage": {
            "backend": "r2", "store_id": "r2_shared",
            "object_key": f"capital_structure/sec/sha256/{digest[:2]}/{digest}",
            "content_addressed": True, "retention_state": "retained",
        },
        "rights": {
            "redistribution_class": "public_source_link", "attribution_required": True,
            "license_note": "United States SEC EDGAR public filing",
        },
        "privacy": {"classification": "public", "contains_personal_data": False},
        "parser": {
            "eligibility": "eligible", "corruption_state": "clean",
            "parser_version": "sec-source-inspector/1.0.0",
        },
        "spans": [{
            "span_id": f"root:{digest}", "locator_type": "document",
            "locator": f"bytes:0-{len(raw)}", "text_sha256": digest,
        }],
    }
    record["manifest_id"] = manifest_id_for(record)
    return record


def _reader(raw: bytes):
    return lambda manifest: raw


def _fixture(stem: str) -> tuple[bytes, dict]:
    matches = [path for path in P130_FIXTURES if path.name.startswith(stem)]
    assert len(matches) == 1, stem
    raw = matches[0].read_bytes()
    return raw, _p130_manifest(raw)


def _totals(rows: list[dict]) -> list[dict]:
    return [
        row for row in rows
        if row["term"]["scope"] == "registration_fee_table_total"
        and row["term"]["name"] == AGGREGATE
    ]


def _states(rows: list[dict]) -> set[tuple[str, str]]:
    return {(row["state"]["disposition"], row["state"]["reason"]) for row in rows}


def _drop_parser_version(rows: list[dict]) -> list[dict]:
    """Compare two released parsers' records modulo the one version-derived
    field, ``extraction.parser_version`` (no record field other than that
    string embeds the parser version)."""
    stripped = []
    for row in rows:
        row = {**row}
        extraction = dict(row["extraction"])
        extraction.pop("parser_version")
        row["extraction"] = extraction
        stripped.append(row)
    return stripped


# ---------------------------------------------------------------------------
# B: a legacy primary-document fee table whose headers are "Securities to be
# Registered" / "Amount To Be Registered" / "Offering Price Per Share" /
# "Aggregate Offering Price" / "Registration Fee".  1.2.0 maps only
# amount_to_be_registered, so the table is never detected.
# ---------------------------------------------------------------------------

def test_p130_b_securities_to_be_registered_header_is_detected():
    raw, manifest = _fixture("p130_b_")
    result = compile_document_term_records(
        [manifest], source_reader=_reader(raw), generated_at="2026-08-03T00:00:00Z",
    )
    rows = result["observations"]
    assert {row["extraction"]["parser_version"] for row in rows} == {V1_3_0}
    # The filing has no "Total Offering Amounts" row; the aggregate is the
    # security data row's own displayed cell, quoted here from the fixture.
    assert "120,000".encode() in raw
    aggregates = [
        row for row in rows
        if row["term"]["name"] == AGGREGATE
        and row["term"]["scope"] == "registration_fee_table_row"
    ]
    assert len(aggregates) == 1
    aggregate = aggregates[0]
    assert aggregate["state"] == {
        "disposition": "observed", "reason": "direct_table_value",
    }
    assert aggregate["reported"]["raw_text"] == "120,000"
    assert aggregate["reported"]["value"] == "120000"
    assert aggregate["reported"]["unit"] == "USD"
    assert aggregate["reported"]["currency"] == "USD"
    assert aggregate["security"]["title_raw"] == "Common Stock"
    assert aggregate["security"]["classification"] == "common_stock"
    assert aggregate["document"]["child_document_type"] == "S-1/A"
    # The header cell "Registration Fee" (no "Amount of ...") maps to no term
    # under either released parser, so this filing's displayed fee cell keeps
    # its honest unavailable refusal -- never a guessed fee amount.
    assert "$16.57*".encode() in raw
    fees = [
        row for row in rows
        if row["term"]["name"] == "registration_fee"
        and row["term"]["scope"] == "registration_fee_table_row"
    ]
    assert fees[0]["state"] == {
        "disposition": "unavailable", "reason": "header_without_direct_value",
    }
    # Exactly one security row of five term slots: no totals row exists.
    assert len(rows) == len(document_terms.TERM_NAMES)


# ---------------------------------------------------------------------------
# C title-header variant: "Title of Class of Security being registered".
# ---------------------------------------------------------------------------

def test_p130_c_title_of_class_header_reads_the_total():
    raw, manifest = _fixture("p130_c_title_")
    result = compile_document_term_records(
        [manifest], source_reader=_reader(raw), generated_at="2026-08-03T00:00:00Z",
    )
    rows = result["observations"]
    assert {row["extraction"]["parser_version"] for row in rows} == {V1_3_0}
    assert "209,587,500".encode() in raw
    totals = _totals(rows)
    assert len(totals) == 1
    total = totals[0]
    assert total["state"] == {
        "disposition": "observed", "reason": "direct_table_value",
    }
    assert total["reported"]["raw_text"] == "209,587,500"
    assert total["reported"]["value"] == "209587500"
    assert total["reported"]["unit"] == "USD"
    assert total["reported"]["currency"] == "USD"
    assert total["security"]["title_raw"] == "Total Offering Amounts"
    assert total["document"]["child_document_type"] == "EX-FILING FEES"


# ---------------------------------------------------------------------------
# C "Security Class Type (1)": the frozen 1.3.0 security-header rule does NOT
# match this spelling (only "security classtitle" without the space and the
# other listed literals are released), so this filing keeps its 1.2.0
# refusal.  The rule is never loosened to make a fixture pass.
# ---------------------------------------------------------------------------

def test_p130_c_class_type_spelling_keeps_its_refusal():
    raw, manifest = _fixture("p130_c_classtype_")
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    assert len(rows) == len(document_terms.TERM_NAMES)
    assert _states(rows) == {("ambiguous", "unit_semantics_ambiguous")}
    # 1.2.0 produced the very same refusal on the very same bytes.
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    assert _drop_parser_version(rows) == _drop_parser_version(prior)
    assert document_terms._security_header_v1_3_0("Security Class Type (1)") is False


# ---------------------------------------------------------------------------
# C left-shifted totals row: the aggregate and fee amounts sit one grid
# column left of their (entirely blank) header spans.
# ---------------------------------------------------------------------------

def test_p130_c_leftshift_reads_the_shifted_totals_cell():
    raw, manifest = _fixture("p130_c_leftshift_")
    result = compile_document_term_records(
        [manifest], source_reader=_reader(raw), generated_at="2026-08-03T00:00:00Z",
    )
    rows = result["observations"]
    assert {row["extraction"]["parser_version"] for row in rows} == {V1_3_0}
    # The digits are quoted from the fixture bytes; the cell's leading "$"
    # glyph is a separate markup run the cell text joins back on.
    assert "18,000,000".encode() in raw
    totals = _totals(rows)
    assert len(totals) == 1
    total = totals[0]
    assert total["state"] == {
        "disposition": "observed", "reason": "direct_table_value",
    }
    assert total["reported"]["raw_text"] == "$18,000,000"
    assert total["reported"]["value"] == "18000000"
    assert total["reported"]["unit"] == "USD"
    assert total["security"]["title_raw"] == "Total Offering Amounts"
    # The evidence span records the ACTUAL cell read: the aggregate column's
    # left neighbor (grid column A-1 = 5), never the declared span.
    value_locators = [
        span["locator"] for span in total["evidence"]["spans"]
        if "role=proposed_maximum_aggregate_offering_price" in span["locator"]
    ]
    assert len(value_locators) == 1
    assert ":cell=5:" in value_locators[0]


# ---------------------------------------------------------------------------
# D legacy-plus-exhibit: the fee table appears in BOTH the primary document
# and an EX-FILING FEES child; 1.3.0 continues with the EX-FILING FEES child
# only.  Real filing 0001065949-26-000044.
# ---------------------------------------------------------------------------

def test_p130_d_legacy_selects_the_ex_filing_fees_child():
    raw, manifest = _fixture("p130_d_legacy_")
    result = compile_document_term_records(
        [manifest], source_reader=_reader(raw), generated_at="2026-08-03T00:00:00Z",
    )
    rows = result["observations"]
    assert {row["extraction"]["parser_version"] for row in rows} == {V1_3_0}
    assert rows
    for row in rows:
        assert row["document"]["child_document_type"] == "EX-FILING FEES"
        assert row["document"]["child_sequence"] == "28"
        assert row["document"]["child_filename"] == "EXFILINGFEES.htm"
        for span in row["evidence"]["spans"]:
            assert "type=EX-FILING FEES:sequence=28" in span["locator"]
            assert "type=S-1:sequence=1" not in span["locator"]
    # The digits are quoted from the fixture bytes; the cell's leading "$"
    # glyph is a separate markup run the cell text joins back on.
    assert "11,715,328.00".encode() in raw
    totals = _totals(rows)
    assert len(totals) == 1
    total = totals[0]
    assert total["state"] == {
        "disposition": "observed", "reason": "direct_table_value",
    }
    assert total["reported"]["raw_text"] == "$ 11,715,328.00"
    assert total["reported"]["value"] == "11715328"
    assert total["security"]["title_raw"] == "Total Offering Amounts:"


# ---------------------------------------------------------------------------
# D refusal case: two EX-FILING FEES children.  1.3.0 keeps the 1.2.0 refusal
# byte for byte (0001816590-26-000065).
# ---------------------------------------------------------------------------

def test_p130_d_two_ex_filing_fees_children_still_refuse():
    raw, manifest = _fixture("p130_d_refusal_")
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    assert len(rows) == len(document_terms.TERM_NAMES)
    assert _states(rows) == {
        ("ambiguous", "multiple_fee_tables_detected"),
    }
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    # The refusal is 1.2.0's byte for byte, apart from the record's own
    # parser-version provenance string.
    assert _drop_parser_version(rows) == _drop_parser_version(prior)


# ---------------------------------------------------------------------------
# Released-parser invariance: 1.3.0 leaves every released ex107 fixture and
# every p130 fixture's 1.2.0 rows byte-identical apart from
# ``extraction.parser_version`` (the only version-derived record field).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture_name",
    sorted(path.name for path in FIXTURE_DIR.glob("ex107_*.txt")),
)
def test_released_ex107_fixtures_are_byte_identical_under_1_3_0(fixture_name):
    raw = (FIXTURE_DIR / fixture_name).read_bytes()
    manifest = _p130_manifest(raw)
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    current = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    assert len(current) == len(prior)
    for row in current:
        assert row["extraction"]["parser_version"] == V1_3_0
    for row in prior:
        assert row["extraction"]["parser_version"] == V1_2_0
    assert _drop_parser_version(current) == _drop_parser_version(prior)


@pytest.mark.parametrize(
    "fixture_name", sorted(path.name for path in P130_FIXTURES),
)
def test_p130_fixtures_keep_their_1_2_0_rows_unchanged(fixture_name):
    raw = (FIXTURE_DIR / fixture_name).read_bytes()
    manifest = _p130_manifest(raw)
    expected_states = {
        "p130_b_": {("unavailable", "fee_table_not_detected")},
        "p130_c_title_": {("ambiguous", "unit_semantics_ambiguous")},
        "p130_c_classtype_": {("ambiguous", "unit_semantics_ambiguous")},
        "p130_c_leftshift_": {
            ("ambiguous", "unsupported_dimensional_value"),
            ("observed", "direct_table_value"),
            ("unavailable", "header_without_direct_value"),
        },
        "p130_d_legacy_": {("ambiguous", "multiple_fee_tables_detected")},
        "p130_d_refusal_": {("ambiguous", "multiple_fee_tables_detected")},
    }
    stem = next(
        prefix for prefix in expected_states if fixture_name.startswith(prefix)
    )
    # The registered released parser path (what every historical consumer
    # uses) still produces exactly the 1.2.0 records.
    through_registry = document_terms._records_for_manifest(
        manifest, raw, parser_version=V1_2_0,
    )
    direct = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    assert through_registry == direct
    for row in through_registry:
        assert row["extraction"]["parser_version"] == V1_2_0
    assert _states(through_registry) == expected_states[stem]


# ---------------------------------------------------------------------------
# Negative rule tests on synthetic tables (real EDGAR envelope shape).
# ---------------------------------------------------------------------------

def _envelope(children: list[tuple[str, str, str, bytes]], form: str = "S-1") -> bytes:
    """A complete-submission envelope: children are (type, sequence, filename,
    text) tuples in document order."""
    parts = [
        f"<SEC-DOCUMENT>0000000001-26-000001.txt\n"
        f"<SEC-HEADER>0000000001-26-000001.hdr.sgml : 20260801\n"
        f"<ACCEPTANCE-DATETIME>20260801112314\n"
        f"ACCESSION NUMBER:\t\t0000000001-26-000001\n"
        f"CONFORMED SUBMISSION TYPE:\t{form}\n"
        f"PUBLIC DOCUMENT COUNT:\t\t{len(children)}\n"
        f"FILED AS OF DATE:\t\t20260801\n\n"
        f"FILER:\n\n\tCOMPANY DATA:\t\n"
        f"\t\tCOMPANY CONFORMED NAME:\t\t\tABC Corp\n"
        f"\t\tCENTRAL INDEX KEY:\t\t\t0000000001\n\n"
        f"\tFILING VALUES:\n\t\tFORM TYPE:\t{form}\n"
        f"</SEC-HEADER>\n".encode("ascii"),
    ]
    for index, (doc_type, sequence, filename, text) in enumerate(children, start=1):
        parts.append(
            f"<DOCUMENT>\n<TYPE>{doc_type}\n<SEQUENCE>{sequence}\n"
            f"<FILENAME>{filename}\n<TEXT>\n".encode("ascii") + text
            + b"\n</TEXT>\n</DOCUMENT>\n"
        )
    parts.append(b"</SEC-DOCUMENT>\n")
    return b"".join(parts)


def _fee_table_html(header_cells: str, body_rows: str) -> bytes:
    return (
        "<html><body><table>"
        f"<tr>{header_cells}</tr>{body_rows}"
        "</table></body></html>"
    ).encode()


def test_security_type_header_alone_is_never_a_title_column():
    header = (
        "<td>Security Type</td>"
        "<td>Maximum Aggregate Offering Price</td>"
        "<td>Amount of Registration Fee</td>"
    )
    body = (
        "<tr><td>Common Stock</td><td>$ 5,000,000.00</td><td>$ 690.50</td></tr>"
        "<tr><td colspan=\"3\">Total Offering Amounts:</td></tr>"
    )
    raw = _envelope([("EX-FILING FEES", "1", "fee.htm", _fee_table_html(header, body))])
    manifest = _p130_manifest(raw)
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    assert document_terms._security_header_v1_3_0("Security Type") is False
    # The table itself is still detected (two term columns) but has no title
    # column, so the 1.2.0 unit-semantics refusal stands.
    assert _states(rows) == {("ambiguous", "unit_semantics_ambiguous")}
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    assert _drop_parser_version(rows) == _drop_parser_version(prior)


def test_security_classtitle_spelling_is_a_title_column():
    # The no-space "Security ClassTitle" spelling is one of the released
    # 1.3.0 title-column literals (distinct from "Security Class Type",
    # which no released rule matches -- see the p130_c_classtype fixture).
    # No committed fixture carries this spelling; this synthetic test is
    # its only exercise.
    assert document_terms._security_header_v1_3_0("Security ClassTitle") is True
    header = (
        "<td>Security ClassTitle</td>"
        "<td>Maximum Aggregate Offering Price</td>"
        "<td>Amount of Registration Fee</td>"
    )
    body = (
        "<tr><td>Common Stock</td><td>$ 5,000,000.00</td><td>$ 690.50</td></tr>"
        "<tr><td>Total Offering Amounts:</td>"
        "<td>$ 5,000,000.00</td><td></td></tr>"
    )
    raw = _envelope([("EX-FILING FEES", "1", "fee.htm", _fee_table_html(header, body))])
    manifest = _p130_manifest(raw)
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    totals = _totals(rows)
    assert len(totals) == 1
    assert totals[0]["state"] == {
        "disposition": "observed", "reason": "direct_table_value",
    }
    assert totals[0]["reported"]["value"] == "5000000"
    assert totals[0]["security"]["title_raw"] == "Total Offering Amounts:"


def test_fee_header_naming_the_aggregate_stays_a_fee_column():
    header_text = (
        "Amount of Registration Fee (based on aggregate offering price)"
    )
    assert document_terms._term_for_header_v1_3_0(header_text) == "registration_fee"
    header = (
        "<td>Security Class Title</td>"
        "<td>Amount to be Registered</td>"
        f"<td>{header_text}</td>"
    )
    body = (
        "<tr><td>Common Stock</td><td>1,000,000</td><td>$ 138.10</td></tr>"
    )
    raw = _envelope([("EX-FILING FEES", "1", "fee.htm", _fee_table_html(header, body))])
    manifest = _p130_manifest(raw)
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    fees = [
        row for row in rows
        if row["term"]["name"] == "registration_fee"
        and row["term"]["scope"] == "registration_fee_table_row"
    ]
    assert fees[0]["state"] == {
        "disposition": "observed", "reason": "direct_table_value",
    }
    assert fees[0]["reported"]["value"] == "138.1"
    aggregates = [
        row for row in rows if row["term"]["name"] == AGGREGATE
    ]
    assert all(
        row["state"]["disposition"] == "unavailable" for row in aggregates
    )


def test_per_share_aggregate_spelling_maps_to_nothing():
    assert document_terms._term_for_header_v1_3_0(
        "Aggregate offering price per share",
    ) is None
    assert document_terms._term_for_header_v1_3_0(
        "Aggregate offering price per unit",
    ) is None
    # Any per-share or per-unit word excludes the bare aggregate spelling,
    # not only the literal "per ".
    for header in (
        "Aggregate offering price/unit",
        "Aggregate offering price per-share",
        "Aggregate offering price (shares)",
        "Aggregate offering price, units",
    ):
        assert document_terms._term_for_header_v1_3_0(header) is None, header
    # A unit word inside another word never excludes the aggregate spelling.
    assert document_terms._term_for_header_v1_3_0(
        "Aggregate offering price (community)",
    ) == AGGREGATE
    # A spelling 1.2.0 already maps keeps the 1.2.0 mapping untouched.
    for header in (
        "Proposed maximum aggregate offering price per unit",
        "Maximum Aggregate Offering Price",
        "Amount of Registration Fee (based on aggregate offering price)",
        "Fee Rate",
    ):
        assert document_terms._term_for_header_v1_3_0(
            header,
        ) == document_terms._term_for_header_v1_2_0(header)


# ---------------------------------------------------------------------------
# C-left unit negatives: synthetic FeeTableV1_2 grids exercising each
# condition of the fallback in isolation.
# ---------------------------------------------------------------------------

def _synth_cell(text: str, column_start: int, column_span: int = 1):
    raw = f"<td>{text}</td>".encode()
    return document_terms.TableCell(
        raw=raw, text=text, start=0, end=len(raw),
        column_start=column_start, column_span=column_span,
    )


def _synth_row(*cells):
    raw = b"".join(cell.raw for cell in cells)
    return document_terms.TableRow(
        raw=raw, start=0, end=len(raw), cells=cells,
    )


def _synth_table(columns: dict, column_spans: dict, rows, security_column=0):
    return document_terms.FeeTableV1_2(
        raw=b"", start=0, end=0,
        document=document_terms.SubmissionDocument(
            document_type="EX-FILING FEES", sequence="1", filename="fee.htm",
            text=b"", text_start=0, text_end=0,
        ),
        table_index=0, rows=tuple(rows), header_index=0, columns=columns,
        security_column=security_column, duplicate_headers=(),
        column_spans=column_spans,
    )


def _leftshift_grid(
    *,
    aggregate: int = 4,
    fee: int = 6,
    aggregate_span: int = 1,
    fee_span: int = 1,
    aggregate_inside: tuple[str, ...] = ("",),
    fee_inside: tuple[str, ...] = ("",),
    aggregate_left: str = "$18,000,000",
    fee_left: str = "$2,485.80",
):
    """A totals-row grid with the aggregate column at ``aggregate`` and the
    fee column at ``fee``, the amounts sitting one grid column left."""
    column = max(aggregate + aggregate_span, fee + fee_span)
    cells = [_synth_cell("Total Offering Amounts", 0)]
    position = 1
    while position < column:
        if position == aggregate - 1:
            cells.append(_synth_cell(aggregate_left, position))
            position += 1
        elif position == fee - 1:
            cells.append(_synth_cell(fee_left, position))
            position += 1
        elif aggregate <= position < aggregate + aggregate_span:
            text = aggregate_inside[position - aggregate]
            cells.append(_synth_cell(text, position))
            position += 1
        elif fee <= position < fee + fee_span:
            text = fee_inside[position - fee]
            cells.append(_synth_cell(text, position))
            position += 1
        else:
            cells.append(_synth_cell("", position))
            position += 1
    row = _synth_row(*cells)
    table = _synth_table(
        columns={
            AGGREGATE: aggregate, "registration_fee": fee,
        },
        column_spans={AGGREGATE: aggregate_span, "registration_fee": fee_span},
        rows=[row],
    )
    return table, row


def test_leftshift_fallback_reads_the_shifted_cell_when_all_conditions_hold():
    table, row = _leftshift_grid()
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    assert cell is not None
    assert cell.text == "$18,000,000"
    assert cell.column_start == 3


def test_leftshift_fallback_refuses_when_aggregate_left_equals_fee_left():
    # Both left neighbors are the same grid cell (A-1 == F-1): the two
    # columns would share one amount, which is not a readable total.
    table, row = _leftshift_grid(aggregate=4, fee=4)
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    # 1.2.0 behavior stands: the blank declared-span cell, never a guess.
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_leftshift_fallback_refuses_when_the_fee_span_cell_is_not_blank():
    table, row = _leftshift_grid(fee_inside=("$ 1,617.89",))
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_leftshift_fallback_refuses_when_the_shifted_cell_does_not_parse():
    table, row = _leftshift_grid(aggregate_left="n/a")
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_leftshift_fallback_refuses_when_the_fee_left_cell_does_not_parse():
    table, row = _leftshift_grid(fee_left="—")
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_leftshift_fallback_never_applies_to_other_terms():
    table, row = _leftshift_grid()
    cell = document_terms._total_row_value_cell_v1_3_0(
        table, row, "registration_fee",
    )
    # The fee column's own 1.2.0 result: the blank declared-span cell.
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_leftshift_fallback_refuses_when_a_left_neighbor_is_under_another_header():
    # A-1 sits in a declared per-unit price column: that cell is the per-unit
    # price, never a shifted aggregate amount.
    table, row = _leftshift_grid()
    per_unit = "proposed_maximum_offering_price_per_unit"
    table = dataclasses.replace(
        table,
        columns={**table.columns, per_unit: 3},
        column_spans={**table.column_spans, per_unit: 1},
    )
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_leftshift_fallback_refuses_when_fee_left_is_under_another_header():
    # F-1 sits in a declared fee-rate column: that cell is the fee rate,
    # never a shifted fee amount.
    table, row = _leftshift_grid()
    table = dataclasses.replace(
        table,
        columns={**table.columns, "filing_fee_rate": 5},
        column_spans={**table.column_spans, "filing_fee_rate": 1},
    )
    cell = document_terms._total_row_value_cell_v1_3_0(table, row, AGGREGATE)
    assert cell is not None and cell.text == ""
    assert document_terms._parse_number(cell.text).disposition != "observed"


def test_per_unit_price_and_fee_rate_are_never_read_as_shifted_totals():
    # Review counterexample: the totals row's only values sit under the
    # per-unit price and fee-rate headers, left of the blank aggregate and
    # fee spans.  1.3.0 must keep the 1.2.0 refusal, byte for byte.
    header = (
        "<td>Security Class Title</td><td>Amount Registered</td>"
        "<td>Proposed Maximum Offering Price Per Unit</td>"
        "<td>Maximum Aggregate Offering Price</td><td>Fee Rate</td>"
        "<td>Amount of Registration Fee</td>"
    )
    body = (
        "<tr><td>Common Stock</td><td>1,000,000</td><td>$10.00</td>"
        "<td></td><td>0.0001531</td><td></td></tr>"
        "<tr><td>Total Offering Amounts</td><td></td><td>$10.00</td>"
        "<td></td><td>0.0001531</td><td></td></tr>"
    )
    raw = _envelope([("EX-FILING FEES", "1", "fee.htm", _fee_table_html(header, body))])
    manifest = _p130_manifest(raw)
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    totals = _totals(rows)
    assert len(totals) == 1
    assert totals[0]["state"] == {
        "disposition": "unavailable", "reason": "header_without_direct_value",
    }
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    assert _drop_parser_version(rows) == _drop_parser_version(prior)


# Condition (v)'s span-overlap halves (neither A-1 inside F's declared span
# nor F-1 inside A's) are defense in depth: on any grid where a left
# neighbor parses observed, that neighbor's text also makes the blank-span
# condition (ii)/(iii) refuse first, so no honest grid can construct the
# overlap alone.  The A-1 == F-1 case above is the reachable half of (v).
# The same holds for a left neighbor in the title column: a totals row's
# title cell never parses observed, so condition (iv) refuses first.


# ---------------------------------------------------------------------------
# D-select negatives on synthetic envelopes.
# ---------------------------------------------------------------------------

_D_HEADER = (
    "<td>Security Class Title</td>"
    "<td>Amount to be Registered</td>"
    "<td>Maximum Aggregate Offering Price</td>"
    "<td>Amount of Registration Fee</td>"
)
_D_BODY = (
    "<tr><td>Common Stock</td><td>1,000,000</td>"
    "<td>$ 5,000,000.00</td><td>$ 690.50</td></tr>"
    "<tr><td colspan=\"4\">Total Offering Amounts:</td></tr>"
)


def test_d_select_refuses_with_two_ex_filing_fees_children():
    raw = _envelope([
        ("EX-FILING FEES", "2", "fees1.htm", _fee_table_html(_D_HEADER, _D_BODY)),
        ("EX-FILING FEES", "3", "fees2.htm", _fee_table_html(_D_HEADER, _D_BODY)),
    ])
    manifest = _p130_manifest(raw)
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    assert _states(rows) == {("ambiguous", "multiple_fee_tables_detected")}
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    assert _drop_parser_version(rows) == _drop_parser_version(prior)


def test_d_select_refuses_when_no_table_is_in_an_ex_filing_fees_child():
    two_tables = (
        b"<html><body>"
        b"<table><tr>" + _D_HEADER.encode() + b"</tr>"
        b"<tr><td>Common Stock</td><td>1,000,000</td>"
        b"<td>$ 5,000,000.00</td><td>$ 690.50</td></tr></table>"
        b"<table><tr>" + _D_HEADER.encode() + b"</tr>"
        b"<tr><td>Preferred Stock</td><td>500,000</td>"
        b"<td>$ 2,500,000.00</td><td>$ 345.25</td></tr></table>"
        b"</body></html>"
    )
    raw = _envelope([("S-1", "1", "body.htm", two_tables)])
    manifest = _p130_manifest(raw)
    rows = document_terms._records_for_manifest_v1_3_0(manifest, raw, V1_3_0)
    assert _states(rows) == {("ambiguous", "multiple_fee_tables_detected")}
    prior = document_terms._records_for_manifest_v1_2_0(manifest, raw, V1_2_0)
    assert _drop_parser_version(rows) == _drop_parser_version(prior)
