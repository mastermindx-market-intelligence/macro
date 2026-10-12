"""Deterministic stdlib OOXML export of a financial query response.

Builds a minimal ``.xlsx`` with :mod:`zipfile` only.  The Response sheet is
the CSV projection from :meth:`MetricMatrix.to_csv_bytes` (same rows and
columns, including the value-column ``_csv_safe`` exemption).  The Meta sheet
carries scalar fields the response already holds plus ``exact_text_cells``
when a Decimal cannot round-trip through IEEE-754.
"""
from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipInfo

from .query import QUERY_SCHEMA, MetricMatrix, _csv_safe
from .raw_ledger import utc_text

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# CSV value column is index 15; query.py:3655-3700 leaves it unsanitised so a
# negative Decimal stays numeric.
_CSV_VALUE_INDEX = 15

_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
_ENTRY_ORDER = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/worksheets/sheet1.xml",
    "xl/worksheets/sheet2.xml",
)

_SSML = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OD_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

_XML_QUOTE_ENTITIES = {"'": "&apos;", '"': "&quot;"}
_SKIP_META_KEYS = frozenset(
    {
        "rows",
        "nodes",
        "confirmations",
        "metrics",
        "mappings",
        "formulas",
        "root_cell_ids",
    }
)

_CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{ct}">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
""".format(ct=_CT_NS)

_ROOT_RELS = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{_PKG_REL}">
<Relationship Id="rId1" Type="{_OD_REL}/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

_WORKBOOK = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{_SSML}" xmlns:r="{_OD_REL}">
<sheets>
<sheet name="Response" sheetId="1" r:id="rId1"/>
<sheet name="Meta" sheetId="2" r:id="rId2"/>
</sheets>
</workbook>
"""

_WORKBOOK_RELS = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{_PKG_REL}">
<Relationship Id="rId1" Type="{_OD_REL}/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="{_OD_REL}/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="{_OD_REL}/styles" Target="styles.xml"/>
</Relationships>
"""

# Mandatory empty stylesheet: one of each required collection, no formats.
_STYLES = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="{_SSML}">
<fonts count="1"><font/></fonts>
<fills count="1"><fill/></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf/></cellStyleXfs>
<cellXfs count="1"><xf/></cellXfs>
</styleSheet>
"""


class _ExactNumeric:
    """CSV value-column spelling that must appear verbatim in ``<v>``."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


def to_xlsx_bytes(response: Mapping[str, Any]) -> bytes:
    """Encode ``response`` as a byte-deterministic ``.xlsx`` payload."""
    if not isinstance(response, Mapping):
        raise TypeError("response must be a mapping")
    exact_text_cells: list[str] = []
    response_rows = _response_rows(response)
    sheet1 = _worksheet_xml(response_rows, exact_text_cells)
    meta_rows = _meta_rows(response, exact_text_cells)
    sheet2 = _worksheet_xml(meta_rows, exact_text_cells)
    parts = {
        "[Content_Types].xml": _CONTENT_TYPES,
        "_rels/.rels": _ROOT_RELS,
        "xl/workbook.xml": _WORKBOOK,
        "xl/_rels/workbook.xml.rels": _WORKBOOK_RELS,
        "xl/styles.xml": _STYLES,
        "xl/worksheets/sheet1.xml": sheet1,
        "xl/worksheets/sheet2.xml": sheet2,
    }
    return _zip_parts(parts)


def response_query_id(response: Mapping[str, Any]) -> str:
    """Filename stem: query id the response already carries."""
    for key in ("query_id", "query_hash"):
        value = response.get(key)
        if isinstance(value, str) and value:
            return _filename_stem(value)
    receipt = response.get("receipt")
    if isinstance(receipt, Mapping):
        value = receipt.get("query_hash")
        if isinstance(value, str) and value:
            return _filename_stem(value)
    return "financial_query"


def _filename_stem(value: str) -> str:
    cleaned = "".join(
        ch if ch.isalnum() or ch in "._-" else "_" for ch in value
    )
    return cleaned or "financial_query"


def _zip_parts(parts: Mapping[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(
        buf, mode="w", compression=ZIP_DEFLATED, compresslevel=6
    ) as zf:
        for name in _ENTRY_ORDER:
            info = ZipInfo(filename=name, date_time=_ZIP_EPOCH)
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.create_version = 20
            info.extract_version = 20
            info.external_attr = 0
            payload = parts[name].encode("utf-8")
            zf.writestr(
                info, payload, compress_type=ZIP_DEFLATED, compresslevel=6
            )
    return buf.getvalue()


def _response_rows(response: Mapping[str, Any]) -> list[list[Any]]:
    matrix = _matrix_from_response(response)
    if matrix is not None:
        return _rows_from_csv_bytes(matrix.to_csv_bytes())
    rows = response.get("rows")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
        return [list(row) for row in rows]
    return []


def _matrix_from_response(response: Mapping[str, Any]) -> MetricMatrix | None:
    receipt = response.get("receipt")
    candidate: Mapping[str, Any] | None = None
    if isinstance(receipt, Mapping) and receipt.get("schema") == QUERY_SCHEMA:
        candidate = receipt
    elif response.get("schema") == QUERY_SCHEMA and "query_hash" in response:
        candidate = response
    if candidate is None:
        return None
    return MetricMatrix.from_dict(candidate)


def _rows_from_csv_bytes(payload: bytes) -> list[list[Any]]:
    reader = csv.reader(io.StringIO(payload.decode("utf-8")))
    rows: list[list[Any]] = []
    for row_index, row in enumerate(reader):
        converted: list[Any] = []
        for col_index, cell in enumerate(row):
            if row_index > 0 and col_index == _CSV_VALUE_INDEX:
                converted.append(_csv_value_cell(cell))
            else:
                converted.append(cell)
        rows.append(converted)
    return rows


def _csv_value_cell(text: str) -> Any:
    if text == "":
        return None
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        return text
    if not parsed.is_finite():
        return text
    if _fits_ieee754(parsed):
        return _ExactNumeric(text)
    return text


def _meta_rows(
    response: Mapping[str, Any], exact_text_cells: list[str]
) -> list[list[Any]]:
    pairs: list[tuple[str, Any]] = []
    _flatten_meta(response, "", pairs)
    if exact_text_cells:
        pairs.append(("exact_text_cells", ",".join(exact_text_cells)))
    return [[key, value] for key, value in pairs]


def _flatten_meta(
    value: Any, prefix: str, out: list[tuple[str, Any]]
) -> None:
    leaf = prefix.rsplit(".", 1)[-1] if prefix else ""
    if leaf in _SKIP_META_KEYS:
        return
    if value is None:
        return
    if isinstance(value, Mapping):
        for key in sorted(value.keys(), key=str):
            child = f"{prefix}.{key}" if prefix else str(key)
            _flatten_meta(value[key], child, out)
        return
    if isinstance(value, (list, tuple)):
        if not value:
            return
        if any(isinstance(item, (Mapping, list, tuple)) for item in value):
            return
        out.append((prefix, ",".join(str(item) for item in value)))
        return
    out.append((prefix, value))


def _worksheet_xml(rows: Sequence[Sequence[Any]], exact_text_cells: list[str]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_SSML}"><sheetData>',
    ]
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for col_index, value in enumerate(row, start=1):
            encoded = _encode_cell(row_index, col_index, value, exact_text_cells)
            if encoded is not None:
                cells.append(encoded)
        if cells:
            parts.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def _encode_cell(
    row_index: int,
    col_index: int,
    value: Any,
    exact_text_cells: list[str],
) -> str | None:
    if value is None:
        return None
    a1 = f"{_col_name(col_index)}{row_index}"
    if isinstance(value, _ExactNumeric):
        return _numeric_cell(a1, value.text)
    if isinstance(value, bool):
        return _inline_str_cell(a1, _csv_safe("true" if value else "false"))
    if isinstance(value, int):
        decimal_value = Decimal(value)
        text = format(decimal_value, "f")
        if _fits_ieee754(decimal_value):
            return _numeric_cell(a1, text)
        exact_text_cells.append(a1)
        return _inline_str_cell(a1, _csv_safe(text))
    if isinstance(value, Decimal):
        if not value.is_finite():
            return _inline_str_cell(a1, _csv_safe(str(value)))
        text = format(value, "f")
        if _fits_ieee754(value):
            return _numeric_cell(a1, text)
        exact_text_cells.append(a1)
        return _inline_str_cell(a1, _csv_safe(text))
    if isinstance(value, datetime):
        return _inline_str_cell(a1, _csv_safe(_datetime_text(value)))
    if isinstance(value, date):
        return _inline_str_cell(a1, _csv_safe(value.isoformat()))
    return _inline_str_cell(a1, _csv_safe(str(value)))


def _fits_ieee754(value: Decimal) -> bool:
    if not value.is_finite():
        return False
    try:
        as_float = float(value)
    except (OverflowError, ValueError):
        return False
    if as_float != as_float or as_float in (float("inf"), float("-inf")):
        return False
    try:
        return Decimal(as_float) == value
    except (InvalidOperation, ValueError):
        return False


def _datetime_text(value: datetime) -> str:
    if value.tzinfo is not None:
        text = utc_text(value)
        return text if text is not None else value.isoformat()
    return value.isoformat()


def _numeric_cell(a1: str, text: str) -> str:
    return f'<c r="{a1}"><v>{_xml_escape(text)}</v></c>'


def _inline_str_cell(a1: str, text: str) -> str:
    return (
        f'<c r="{a1}" t="inlineStr"><is>'
        f'<t xml:space="preserve">{_xml_escape(text)}</t>'
        f"</is></c>"
    )


def _xml_escape(text: str) -> str:
    # XML 1.0 end-of-line handling turns CR into LF before the tree is built.
    # A character reference is the only way a CR-leading _csv_safe payload
    # round-trips through ElementTree / Excel.
    return escape(text, _XML_QUOTE_ENTITIES).replace("\r", "&#13;")


def _col_name(index: int) -> str:
    name = ""
    remaining = index
    while remaining:
        remaining, rem = divmod(remaining - 1, 26)
        name = chr(65 + rem) + name
    return name


__all__ = ["XLSX_MEDIA_TYPE", "response_query_id", "to_xlsx_bytes"]
