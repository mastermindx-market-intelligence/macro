"""Stdlib OOXML export tests for FIF X1.  Read workbooks with zipfile + ElementTree."""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from engine.fundamental_forensics.excel_export import (
    XLSX_MEDIA_TYPE,
    response_query_id,
    to_xlsx_bytes,
)
from engine.fundamental_forensics.query import _csv_safe

from tests.test_fundamental_forensics_query import PERIOD, _engine, _fact, _policy

SSML = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ENTRY_ORDER = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/worksheets/sheet1.xml",
    "xl/worksheets/sheet2.xml",
)
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
ROOT = Path(__file__).resolve().parents[1]


def _q(tag: str) -> str:
    return f"{{{SSML}}}{tag}"


def _synthetic(**extra: object) -> dict:
    payload: dict = {
        "schema": "fundamental_forensics.financial_query_response/v1",
        "query_id": "q-synthetic",
        "query_hash": "ab" * 32,
        "sha256": "cd" * 32,
    }
    payload.update(extra)
    return payload


def _cell_ref_parts(ref: str) -> tuple[str, int]:
    i = 0
    while i < len(ref) and ref[i].isalpha():
        i += 1
    return ref[:i], int(ref[i:])


def _read_zip(payload: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(payload), "r")


def _sheet_root(payload: bytes, name: str) -> ET.Element:
    with _read_zip(payload) as zf:
        return ET.fromstring(zf.read(name))


def _cell_text(cell: ET.Element) -> str | None:
    kind = cell.get("t")
    if kind == "inlineStr":
        text_el = cell.find(f"{_q('is')}/{_q('t')}")
        if text_el is None:
            return None
        return text_el.text or ""
    value_el = cell.find(_q("v"))
    if value_el is None:
        return None
    return value_el.text


def _sheet_grid(payload: bytes, sheet: str = "xl/worksheets/sheet1.xml") -> dict[str, str]:
    root = _sheet_root(payload, sheet)
    grid: dict[str, str] = {}
    for cell in root.iter(_q("c")):
        ref = cell.get("r")
        if not ref:
            continue
        text = _cell_text(cell)
        if text is not None:
            grid[ref] = text
    return grid


def _sheet_rows(payload: bytes, sheet: str = "xl/worksheets/sheet1.xml") -> list[list[str]]:
    root = _sheet_root(payload, sheet)
    rows: list[list[str]] = []
    for row in root.findall(f"{_q('sheetData')}/{_q('row')}"):
        by_col: dict[int, str] = {}
        max_col = 0
        for cell in row.findall(_q("c")):
            ref = cell.get("r") or ""
            letters, _ = _cell_ref_parts(ref)
            col = 0
            for ch in letters:
                col = col * 26 + (ord(ch) - 64)
            max_col = max(max_col, col)
            text = _cell_text(cell)
            by_col[col] = "" if text is None else text
        if max_col == 0:
            rows.append([])
            continue
        rows.append([by_col.get(index, "") for index in range(1, max_col + 1)])
    return rows


def _escaped_matrix():
    escaped_fact = _fact(entity_id="=2+2", accession="@evil", value="-42")
    return _engine(escaped_fact, entities={"AAA": "=2+2"}).query_matrix(
        tickers=("AAA",),
        metrics=("revenue",),
        periods=(PERIOD,),
        policy=_policy(),
    )


def test_xlsx_bytes_are_deterministic() -> None:
    response = _synthetic(rows=[["h1", "h2"], ["a", Decimal("1")]])
    assert to_xlsx_bytes(response) == to_xlsx_bytes(response)


def test_zip_entry_order_and_dos_epoch() -> None:
    payload = to_xlsx_bytes(_synthetic(rows=[["h"], ["v"]]))
    with _read_zip(payload) as zf:
        names = [info.filename for info in zf.infolist()]
        assert names == list(ENTRY_ORDER)
        for info in zf.infolist():
            assert info.date_time == ZIP_EPOCH
            assert info.compress_type == zipfile.ZIP_DEFLATED


def test_both_sheets_parse_as_xml() -> None:
    payload = to_xlsx_bytes(_synthetic(rows=[["h"], ["v"]]))
    for name in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"):
        root = _sheet_root(payload, name)
        assert _q("sheetData") in {child.tag for child in root} or root.find(
            _q("sheetData")
        ) is not None


def test_package_has_no_shared_strings_part() -> None:
    payload = to_xlsx_bytes(_synthetic(rows=[["h"], ["v"]]))
    with _read_zip(payload) as zf:
        assert "xl/sharedStrings.xml" not in zf.namelist()


def test_a40_csv_xlsx_roundtrip_cell_text() -> None:
    matrix = _escaped_matrix()
    csv_rows = list(
        csv.reader(io.StringIO(matrix.to_csv_bytes().decode("utf-8")))
    )
    response = {
        "schema": "fundamental_forensics.financial_query_response/v1",
        "receipt": matrix.to_dict(),
        "query_hash": matrix.query_hash,
        "sha256": hashlib.sha256(matrix.to_json_bytes()).hexdigest(),
    }
    payload = to_xlsx_bytes(response)
    xlsx_rows = _sheet_rows(payload)
    assert len(xlsx_rows) == len(csv_rows)
    for csv_row, xlsx_row in zip(csv_rows, xlsx_rows, strict=True):
        width = max(len(csv_row), len(xlsx_row))
        csv_padded = list(csv_row) + [""] * (width - len(csv_row))
        xlsx_padded = list(xlsx_row) + [""] * (width - len(xlsx_row))
        assert csv_padded == xlsx_padded


def test_formula_injection_neutralised_like_csv_safe() -> None:
    probes = ["=1+1", "+", "-", "@", "\tled", "\rled"]
    response = _synthetic(rows=[["label"], *[[item] for item in probes]])
    grid = _sheet_grid(to_xlsx_bytes(response))
    for index, item in enumerate(probes, start=2):
        assert grid[f"A{index}"] == _csv_safe(item)


def test_none_cell_is_omitted() -> None:
    response = _synthetic(rows=[["a", "b", "c"], ["keep", None, "tail"]])
    payload = to_xlsx_bytes(response)
    root = _sheet_root(payload, "xl/worksheets/sheet1.xml")
    refs = {cell.get("r") for cell in root.iter(_q("c"))}
    assert "A2" in refs and "C2" in refs
    assert "B2" not in refs


def test_decimal_1234_50_emits_exact_numeric_v() -> None:
    response = _synthetic(rows=[["amount"], [Decimal("1234.50")]])
    xml = _sheet_root(to_xlsx_bytes(response), "xl/worksheets/sheet1.xml")
    cell = next(c for c in xml.iter(_q("c")) if c.get("r") == "A2")
    assert cell.get("t") is None
    value = cell.find(_q("v"))
    assert value is not None
    assert value.text == "1234.50"


def test_datetime_is_iso8601_text() -> None:
    moment = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
    response = _synthetic(rows=[["when"], [moment]])
    grid = _sheet_grid(to_xlsx_bytes(response))
    assert grid["A2"] == "2026-08-05T12:00:00.000000Z"


def test_xml_special_characters_are_escaped() -> None:
    raw = '&<>"\''
    response = _synthetic(rows=[["x"], [raw]])
    payload = to_xlsx_bytes(response)
    with _read_zip(payload) as zf:
        xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "&amp;" in xml
    assert "&lt;" in xml
    assert "&gt;" in xml
    assert "&quot;" in xml
    assert "&apos;" in xml
    assert _sheet_grid(payload)["A2"] == raw


def test_meta_sheet_contains_response_hash() -> None:
    matrix = _escaped_matrix()
    digest = hashlib.sha256(matrix.to_json_bytes()).hexdigest()
    response = {
        "schema": "fundamental_forensics.financial_query_response/v1",
        "receipt": matrix.to_dict(),
        "query_hash": matrix.query_hash,
        "sha256": digest,
    }
    rows = _sheet_rows(to_xlsx_bytes(response), "xl/worksheets/sheet2.xml")
    as_map = {row[0]: row[1] for row in rows if len(row) >= 2}
    assert digest in as_map.values() or digest in as_map.get("sha256", "")
    assert matrix.query_hash in as_map.values() or matrix.query_hash in as_map.get(
        "query_hash", ""
    ) or matrix.query_hash in as_map.get("receipt.query_hash", "")


def test_xlsx_media_type_constant() -> None:
    assert XLSX_MEDIA_TYPE == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_non_ieee_decimal_is_text_and_flagged() -> None:
    awkward = Decimal("0.1")
    response = _synthetic(rows=[["n"], [awkward]])
    payload = to_xlsx_bytes(response)
    xml = _sheet_root(payload, "xl/worksheets/sheet1.xml")
    cell = next(c for c in xml.iter(_q("c")) if c.get("r") == "A2")
    assert cell.get("t") == "inlineStr"
    assert _cell_text(cell) == "0.1"
    meta = {row[0]: row[1] for row in _sheet_rows(payload, "xl/worksheets/sheet2.xml") if row}
    assert "A2" in meta.get("exact_text_cells", "")


def test_response_query_id_uses_receipt_hash() -> None:
    matrix = _escaped_matrix()
    assert (
        response_query_id({"receipt": matrix.to_dict()}) == matrix.query_hash
    )


def test_xlsx_query_route_post_only_attachment() -> None:
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.forensics as forensics_api
    from engine.fundamental_forensics.query_service import fip1_fixture_dataset

    dataset = fip1_fixture_dataset(ROOT)

    class _Provider:
        def resolve(self, entity_id: str):
            if entity_id == "mmx.issuer.fip1":
                return dataset
            raise AssertionError(f"unexpected entity {entity_id}")

    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    original_provider = forensics_api._financial_query_provider
    forensics_api._financial_query_provider = lambda: _Provider()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            body = (
                b'{"schema":"fundamental_forensics.financial_query_request/v1",'
                b'"entity_id":"mmx.issuer.fip1",'
                b'"policy":{"selection":"latest_known_as_of",'
                b'"source_snapshot_at":"2024-12-31T23:59:59Z",'
                b'"recorded_at":"2026-08-03T12:00:00Z"},'
                b'"metric_ids":["revenue"],'
                b'"periods":[{"kind":"duration","start":"2023-01-01",'
                b'"end":"2023-12-31","label":"FY2023"}]}'
            )
            path = "/api/forensics/v1/financial/query.xlsx"
            denied = client.get(path)
            assert denied.status_code == 405
            posted = client.post(
                path, content=body, headers={"content-type": "application/json"}
            )
            assert posted.status_code == 200
            assert posted.headers.get("content-type", "").startswith(XLSX_MEDIA_TYPE)
            disposition = posted.headers.get("content-disposition", "")
            assert disposition.startswith("attachment; filename=")
            assert disposition.endswith('.xlsx"')
            assert posted.headers.get("cache-control") == "private, no-store"
            with zipfile.ZipFile(io.BytesIO(posted.content)) as zf:
                assert zf.namelist() == list(ENTRY_ORDER)
    finally:
        forensics_api._financial_query_provider = original_provider
