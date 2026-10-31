"""A39-L localhost Excel refresh harness tests.

Everything runs through ``fastapi.testclient.TestClient`` on the harness app
factory or through pure functions — no real socket is ever opened.  The
golden-corpus facts (entity, metrics, periods, both cutoff pairs) are read
from what the harness serves, never from gold review files.
"""
from __future__ import annotations

import csv
import io
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from scripts import fif_excel_refresh_harness as harness  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUERY_PATH = "/api/forensics/v1/financial/query"

TOKENS = {
    "full": "test-full-bearer-0123456789abcdef0123456789abcdef",
    "free": "test-free-bearer-0123456789abcdef0123456789abcdef",
}

_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}

_SSML = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OD_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_APP_MAIN_LOADED_BEFORE = "app.main" in sys.modules


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def harness_app():
    """The harness app factory with known tokens; module state restored."""
    import app.forensics as forensics_api

    saved_repo = forensics_api.REPO
    saved_revision = forensics_api._financial_revision_provider
    saved_env = os.environ.get("MACRO_REPO")
    app = harness.build_app(ROOT, TOKENS)
    try:
        yield app
    finally:
        forensics_api.REPO = saved_repo
        forensics_api._financial_revision_provider = saved_revision
        if saved_env is None:
            os.environ.pop("MACRO_REPO", None)
        else:
            os.environ["MACRO_REPO"] = saved_env


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    """One prepare_outputs run: receipts.json, tokens.json and the .pq files."""
    import app.forensics as forensics_api

    out = tmp_path_factory.mktemp("fif_harness_out")
    saved_repo = forensics_api.REPO
    saved_revision = forensics_api._financial_revision_provider
    saved_env = os.environ.get("MACRO_REPO")
    summary = harness.prepare_outputs(ROOT, out, port=harness.DEFAULT_PORT)
    try:
        assert summary is not None, "prepare_outputs refused the golden corpus"
        yield out
    finally:
        forensics_api.REPO = saved_repo
        forensics_api._financial_revision_provider = saved_revision
        if saved_env is None:
            os.environ.pop("MACRO_REPO", None)
        else:
            os.environ["MACRO_REPO"] = saved_env


def _post(app, body: bytes, token: str | None):
    headers = {"content-type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    with TestClient(app) as client:
        return client.post(QUERY_PATH, content=body, headers=headers)


def _pinned_body() -> bytes:
    return harness.serialize_request(harness.request_body(harness.PINNED_POLICY))


def _assert_private_headers(response) -> None:
    for name, expected in _PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected, f"header {name!r}"


# ---------------------------------------------------------------------------
# 1. Entitlement matrix through the stub
# ---------------------------------------------------------------------------


def test_full_token_query_is_200(harness_app) -> None:
    response = _post(harness_app, _pinned_body(), TOKENS["full"])
    assert response.status_code == 200
    _assert_private_headers(response)
    receipt = response.json()["receipt"]
    assert receipt["query_hash"]
    assert receipt["nodes"]


def test_missing_header_is_401_with_private_headers(harness_app) -> None:
    response = _post(harness_app, _pinned_body(), None)
    assert response.status_code == 401
    _assert_private_headers(response)


def test_unknown_token_is_401_with_private_headers(harness_app) -> None:
    response = _post(harness_app, _pinned_body(), "not-a-harness-token")
    assert response.status_code == 401
    _assert_private_headers(response)


def test_empty_bearer_is_401(harness_app) -> None:
    """signed_out.pq sends exactly 'Bearer ' with an empty token."""
    response = _post(harness_app, _pinned_body(), "")
    assert response.status_code == 401
    _assert_private_headers(response)


def test_free_token_is_403_with_private_headers(harness_app) -> None:
    response = _post(harness_app, _pinned_body(), TOKENS["free"])
    assert response.status_code == 403
    _assert_private_headers(response)


def test_build_app_does_not_import_app_main(harness_app) -> None:
    if _APP_MAIN_LOADED_BEFORE:
        pytest.skip("app.main was already imported by an earlier module")
    assert "app.main" not in sys.modules


# ---------------------------------------------------------------------------
# 2. Determinism, pinned/current difference, revisions evidence
# ---------------------------------------------------------------------------


def test_pinned_case_is_deterministic_and_current_differs(prepared) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    determinism = receipts["determinism"]
    assert determinism["pinned_query_hash_stable"] is True
    assert determinism["pinned_nodes_canonical_bytes_identical"] is True

    pinned = receipts["cases"]["pinned"]
    current = receipts["cases"]["current"]
    assert pinned["status"] == 200 and current["status"] == 200
    assert pinned["query_hash"] != current["query_hash"]

    differing = receipts["differing_cells"]
    assert differing, "the golden corpus must move at least one cell"
    newly_visible = [
        item
        for item in differing
        if item["pinned"]["state"] != item["current"]["state"]
    ]
    assert newly_visible, "at least one cell must be newly visible at current"

    # The honest revisions evidence: the route answered, and the corpus has no
    # revision_of events, so a newly visible FILED fact cannot appear there.
    evidence = receipts["revisions_evidence"]
    for case in ("pinned", "current"):
        assert evidence[case]["status"] == 200
        assert evidence[case]["revisions"] == []
    for item in differing:
        assert item["in_revisions_response"] is False
    assert receipts["gaps"], "the corpus limitation must be recorded, not invented away"


def test_error_cases_record_their_denials(prepared) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    signed_out = receipts["cases"]["signed_out"]
    free_tier = receipts["cases"]["free_tier"]
    assert signed_out["status"] == 401 and signed_out["expected_status"] == 401
    assert free_tier["status"] == 403 and free_tier["expected_status"] == 403


# ---------------------------------------------------------------------------
# 3. serve refusals (no socket is opened on any of these paths)
# ---------------------------------------------------------------------------


def test_serve_refuses_non_loopback_host(tmp_path, capsys) -> None:
    code = harness.main(
        ["serve", "--host", "0.0.0.0", "--out", str(tmp_path / "out")]
    )
    assert code == 2
    assert "127.0.0.1" in capsys.readouterr().err


def test_serve_refuses_production_dataset_mode(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv(harness.DATASET_MODE_ENV, "production")
    code = harness.main(["serve", "--out", str(tmp_path / "out")])
    assert code == 2
    assert harness.DATASET_MODE_ENV in capsys.readouterr().err


def test_serve_refuses_any_r2_prefixed_variable(
    tmp_path, monkeypatch, capsys
) -> None:
    sentinel = "R2_SENTINEL_VALUE_NEVER_TO_BE_SHOWN"
    monkeypatch.setenv("R2_DUMMY_PROBE", sentinel)
    code = harness.main(["serve", "--out", str(tmp_path / "out")])
    assert code == 2
    captured = capsys.readouterr()
    assert sentinel not in captured.out
    assert sentinel not in captured.err
    # The refusal names the variable by NAME only.
    assert "R2_DUMMY_PROBE" in captured.err


def test_check_environment_reads_r2_names_only(monkeypatch, capsys) -> None:
    sentinel = "another-secret-value-xyz"
    monkeypatch.setenv("R2_NAME_ONLY_PROBE", sentinel)
    reason = harness.check_environment()
    assert reason is not None
    assert "R2_NAME_ONLY_PROBE" in reason
    captured = capsys.readouterr()
    assert sentinel not in captured.out + captured.err


# ---------------------------------------------------------------------------
# 4. Generated artifacts
# ---------------------------------------------------------------------------


def _request_json_literal(pq_text: str) -> str:
    for line in pq_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("RequestJson ="):
            literal = stripped.split("RequestJson = ", 1)[1].strip()
            if literal.endswith(","):
                literal = literal[:-1]
            assert literal.startswith('"') and literal.endswith('"')
            return literal[1:-1].replace('""', '"')
    raise AssertionError("no RequestJson line in the generated pq")


def test_pq_files_are_template_bytes_with_only_placeholders_filled(
    prepared,
) -> None:
    template = harness.PQ_TEMPLATE_PATH.read_text(encoding="utf-8")
    receipts = json.loads((prepared / "receipts.json").read_text())
    tokens = json.loads((prepared / "tokens.json").read_text())
    url = f"http://127.0.0.1:{harness.DEFAULT_PORT}{QUERY_PATH}"
    expected_token = {
        "pinned": tokens["full"],
        "current": tokens["full"],
        "signed_out": "",
        "free_tier": tokens["free"],
    }
    for case in harness.CASE_ORDER:
        generated = (prepared / f"{case}.pq").read_text(encoding="utf-8")
        # No unfilled harness placeholder remains. (The template's own comment
        # line documents <<PLACEHOLDER>> and is preserved byte for byte.)
        assert "<<FIF_" not in generated
        request_text = harness.serialize_request(
            harness.request_body(harness.CASE_POLICY[case])
        ).decode("utf-8")
        expected = (
            template.replace("<<FIF_QUERY_URL>>", url)
            .replace("<<FIF_BEARER_TOKEN>>", expected_token[case])
            .replace("<<FIF_REQUEST_JSON>>", request_text.replace('"', '""'))
        )
        assert generated == expected
        # The request the .pq will send equals the receipts request body.
        assert json.loads(_request_json_literal(generated)) == receipts["cases"][
            case
        ]["request_body"]


def test_tokens_json_is_mode_0600(prepared) -> None:
    mode = stat.S_IMODE(os.stat(prepared / "tokens.json").st_mode)
    assert mode == 0o600
    tokens = json.loads((prepared / "tokens.json").read_text())
    assert set(tokens) == {"full", "free"}
    assert tokens["full"] != tokens["free"]


def test_no_token_reaches_stdout_or_stderr(tmp_path, capsys) -> None:
    import app.forensics as forensics_api

    saved_repo = forensics_api.REPO
    saved_revision = forensics_api._financial_revision_provider
    try:
        summary = harness.prepare_outputs(ROOT, tmp_path, port=harness.DEFAULT_PORT)
        assert summary is not None
        summary.pop("app", None)
        harness.print_summary(summary)
    finally:
        forensics_api.REPO = saved_repo
        forensics_api._financial_revision_provider = saved_revision
    tokens = json.loads((tmp_path / "tokens.json").read_text())
    captured = capsys.readouterr()
    for kind, token in tokens.items():
        assert token not in captured.out, f"{kind} token leaked to stdout"
        assert token not in captured.err, f"{kind} token leaked to stderr"


def test_cases_table_prints_without_tokens(capsys) -> None:
    assert harness.main(["cases"]) == 0
    out = capsys.readouterr().out
    for case in harness.CASE_ORDER:
        assert case in out
    assert TOKENS["full"] not in out
    assert TOKENS["free"] not in out
    for case in harness.CASE_ORDER:
        assert str(harness.CASE_EXPECTED_STATUS[case]) in out


# ---------------------------------------------------------------------------
# Minimal stdlib OOXML builder with a real table part
# ---------------------------------------------------------------------------


def _col_name(index: int) -> str:
    name = ""
    remaining = index
    while remaining:
        remaining, rem = divmod(remaining - 1, 26)
        name = chr(65 + rem) + name
    return name


def _sheet_xml(rows: list[list[str]]) -> str:
    body = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for col_number, value in enumerate(row, start=1):
            if value == "":
                continue
            ref = f"{_col_name(col_number)}{row_number}"
            escaped = (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>'
            )
        body.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{_SSML}" xmlns:r="{_OD_REL}"><sheetData>'
        f"{''.join(body)}</sheetData>"
        '<tableParts count="1"><tablePart r:id="rIdT1"/></tableParts>'
        "</worksheet>"
    )


def _table_workbook_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    """A minimal stdlib OOXML package whose sheet table is a real table part."""
    all_rows = [header, *rows]
    width = len(header)
    height = len(all_rows)
    ref = f"A1:{_col_name(width)}{height}"
    columns = "".join(
        f'<tableColumn id="{index}" name="{name}"/>'
        for index, name in enumerate(header, start=1)
    )
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Types xmlns="{_PKG_REL.replace("relationships", "content-types")}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{_PKG_REL}">'
            f'<Relationship Id="rId1" Type="{_OD_REL}/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{_SSML}" xmlns:r="{_OD_REL}"><sheets>'
            '<sheet name="Response" sheetId="1" r:id="rId1"/>'
            "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{_PKG_REL}">'
            f'<Relationship Id="rId1" Type="{_OD_REL}/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": _sheet_xml(all_rows),
        "xl/worksheets/_rels/sheet1.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{_PKG_REL}">'
            f'<Relationship Id="rIdT1" Type="{_OD_REL}/table" Target="../tables/table1.xml"/>'
            "</Relationships>"
        ),
        "xl/tables/table1.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<table xmlns="{_SSML}" id="1" name="FIFReceipt" ref="{ref}">'
            f'<tableColumns count="{width}">{columns}</tableColumns>'
            "</table>"
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in parts.items():
            zf.writestr(name, payload)
    return buffer.getvalue()


def _csv_projection(receipt: dict) -> tuple[list[str], list[list[str]]]:
    from engine.fundamental_forensics.query import MetricMatrix

    text = MetricMatrix.from_dict(receipt).to_csv_bytes().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], rows[1:]


def _column(header: list[str], name: str) -> int:
    return header.index(name)


# ---------------------------------------------------------------------------
# 5. verify-workbook, positive
# ---------------------------------------------------------------------------


def test_verify_workbook_match_on_static_export_fixture(prepared, tmp_path) -> None:
    from engine.fundamental_forensics.excel_export import to_xlsx_bytes

    receipts = json.loads((prepared / "receipts.json").read_text())
    for case in harness.SUCCESS_CASES:
        receipt = receipts["cases"][case]["receipt"]
        payload = to_xlsx_bytes(
            {
                "schema": "fundamental_forensics.financial_query_response/v1",
                "receipt": receipt,
            }
        )
        workbook = tmp_path / f"{case}_static.xlsx"
        workbook.write_bytes(payload)
        assert harness.verify_workbook(case, workbook, prepared) == 0


def test_verify_workbook_match_on_table_part_fixture(prepared, tmp_path) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    receipt = receipts["cases"]["pinned"]["receipt"]
    header, rows = _csv_projection(receipt)
    workbook = tmp_path / "pinned_table.xlsx"
    workbook.write_bytes(_table_workbook_bytes(header, rows))
    assert harness.verify_workbook("pinned", workbook, prepared) == 0


def test_verify_workbook_match_on_power_query_node_columns(prepared, tmp_path) -> None:
    """A load through the shipped .pq carries the node columns; the nested
    period/provenance records are bound by cell_id."""
    receipts = json.loads((prepared / "receipts.json").read_text())
    receipt = receipts["cases"]["pinned"]["receipt"]
    header = list(harness._PQ_TEXT_FIELDS) + ["period", "provenance"]
    rows = []
    for node in receipt["nodes"]:
        rows.append(
            ["" if node.get(field) is None else str(node.get(field)) for field in harness._PQ_TEXT_FIELDS]
            + ["[Record]", "[Record]"]
        )
    workbook = tmp_path / "pinned_pq.xlsx"
    workbook.write_bytes(_table_workbook_bytes(header, rows))
    assert harness.verify_workbook("pinned", workbook, prepared) == 0


# ---------------------------------------------------------------------------
# 6. verify-workbook, negative
# ---------------------------------------------------------------------------


def test_verify_workbook_mismatch_on_changed_digit(prepared, tmp_path, capsys) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    receipt = receipts["cases"]["pinned"]["receipt"]
    header, rows = _csv_projection(receipt)
    value_index = _column(header, "value")
    metric_index = _column(header, "metric_id")
    changed = [list(row) for row in rows]
    target = next(
        row
        for row in changed
        if row[metric_index] == "total_assets" and row[value_index]
    )
    original = target[value_index]
    target[value_index] = original[:-1] + ("1" if original[-1] != "1" else "2")
    workbook = tmp_path / "pinned_changed_digit.xlsx"
    workbook.write_bytes(_table_workbook_bytes(header, changed))
    code = harness.verify_workbook("pinned", workbook, prepared)
    assert code == 1
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["verdict"] == "mismatch"
    cells = [m for m in verdict["mismatches"] if m["kind"] == "cell"]
    assert cells, verdict["mismatches"]
    first = cells[0]
    assert first["column"] == "value"
    assert first["expected"] == original
    assert first["actual"] == target[value_index]
    # The mismatch names the cell: sheet, A1-style ref and row identity.
    assert first["ref"].startswith("P")
    assert first["ref"][1:].isdigit()
    assert "total_assets" in first["row"]
    assert "2025-09-27" in first["row"]
    assert first["sheet"] == "Response"


def test_verify_workbook_mismatch_on_missing_source_link_column(
    prepared, tmp_path, capsys
) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    receipt = receipts["cases"]["pinned"]["receipt"]
    header, rows = _csv_projection(receipt)
    drop = _column(header, "accession")
    header = header[:drop] + header[drop + 1 :]
    rows = [row[:drop] + row[drop + 1 :] for row in rows]
    workbook = tmp_path / "pinned_no_accession.xlsx"
    workbook.write_bytes(_table_workbook_bytes(header, rows))
    code = harness.verify_workbook("pinned", workbook, prepared)
    assert code == 1
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["verdict"] == "mismatch"
    missing = [
        m for m in verdict["mismatches"] if m.get("kind") == "missing_column"
    ]
    assert missing and missing[0]["column"] == "accession"


def test_verify_workbook_mismatch_when_no_sheet_carries_receipt_headers(
    prepared, tmp_path, capsys
) -> None:
    workbook = tmp_path / "blank.xlsx"
    workbook.write_bytes(
        _table_workbook_bytes(["Error", "Detail"], [["DataSource.Error", "401"]])
    )
    code = harness.verify_workbook("pinned", workbook, prepared)
    assert code == 1
    verdict = json.loads(capsys.readouterr().out)
    assert any(
        m.get("kind") == "no_receipt_sheet" for m in verdict["mismatches"]
    )


# ---------------------------------------------------------------------------
# 7. signed_out / free_tier workbooks
# ---------------------------------------------------------------------------


def test_signed_out_workbook_with_receipt_rows_is_mismatch(
    prepared, tmp_path, capsys
) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    receipt = receipts["cases"]["pinned"]["receipt"]
    header, rows = _csv_projection(receipt)
    workbook = tmp_path / "signed_out_cached.xlsx"
    workbook.write_bytes(_table_workbook_bytes(header, rows))
    code = harness.verify_workbook("signed_out", workbook, prepared)
    assert code == 1
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["verdict"] == "mismatch"
    unexpected = [
        m for m in verdict["mismatches"] if m.get("kind") == "unexpected_success_rows"
    ]
    assert unexpected
    assert "revenue" in unexpected[0]["row"] or "total_assets" in unexpected[0]["row"]


def test_signed_out_workbook_without_success_rows_matches(
    prepared, tmp_path, capsys
) -> None:
    workbook = tmp_path / "signed_out_failed.xlsx"
    workbook.write_bytes(
        _table_workbook_bytes(["Error", "Detail"], [["DataSource.Error", "401"]])
    )
    code = harness.verify_workbook("signed_out", workbook, prepared)
    assert code == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict == {
        "case": "signed_out",
        "rows_compared": 0,
        "mismatches": [],
        "verdict": "match",
    }


def test_free_tier_workbook_with_receipt_rows_is_mismatch(
    prepared, tmp_path, capsys
) -> None:
    receipts = json.loads((prepared / "receipts.json").read_text())
    receipt = receipts["cases"]["pinned"]["receipt"]
    header, rows = _csv_projection(receipt)
    workbook = tmp_path / "free_tier_cached.xlsx"
    workbook.write_bytes(_table_workbook_bytes(header, rows))
    code = harness.verify_workbook("free_tier", workbook, prepared)
    assert code == 1
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["verdict"] == "mismatch"


# ---------------------------------------------------------------------------
# Input-error exits
# ---------------------------------------------------------------------------


def test_verify_workbook_input_errors(prepared, tmp_path, capsys) -> None:
    workbook = tmp_path / "ok.xlsx"
    workbook.write_bytes(
        _table_workbook_bytes(["Error", "Detail"], [["DataSource.Error", "401"]])
    )
    # Missing receipts directory.
    assert harness.verify_workbook("pinned", workbook, tmp_path / "nowhere") == 2
    # Workbook that is not a zip package at all.
    junk = tmp_path / "junk.xlsx"
    junk.write_bytes(b"this is not an xlsx")
    assert harness.verify_workbook("pinned", junk, prepared) == 2
    # Missing workbook.
    assert (
        harness.verify_workbook("pinned", tmp_path / "absent.xlsx", prepared) == 2
    )
    capsys.readouterr()


def test_verify_workbook_unknown_case_is_usage_error(tmp_path, prepared) -> None:
    workbook = tmp_path / "ok.xlsx"
    workbook.write_bytes(_table_workbook_bytes(["Error"], [["401"]]))
    with pytest.raises(SystemExit) as excinfo:
        harness.main(
            [
                "verify-workbook",
                "--case",
                "bogus",
                "--workbook",
                str(workbook),
                "--out",
                str(prepared),
            ]
        )
    assert excinfo.value.code == 2
