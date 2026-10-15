"""Closed presentation contract for Brain's existing chart transport.

This module neither fetches nor authenticates sources. Numeric equality is checked
against authorized, already-completed tool observations in this SAME turn. Equality
is not freshness, semantic verification, a recommendation, or a new signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Sequence
from typing import Any

TEMPLATES = ("bar", "line", "area", "scatter", "donut", "table", "metrics", "status", "scenarios", "timeline", "flow")
MAX_BYTES = 65536
MAX_VISUALS = 4
_FIELDS = {"version", "template", "title", "subtitle", "takeaway", "unit", "columns", "rows", "basis", "bindings"}
_REQUIRED = {"version", "template", "title", "columns", "rows", "basis"}
_UNSAFE = re.compile(r"<\s*[/!a-z]|https?://|javascript\s*:|data\s*:|[\x00-\x08\x0b\x0c\x0e-\x1f\u202a-\u202e\u2066-\u2069]", re.I)
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,79}\Z")
_ID = re.compile(r"[a-f0-9]{24}\Z")


class VisualError(ValueError):
    """Opaque, bounded user-correctable contract rejection."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise VisualError(reason)


def _text(value: Any, *, empty: bool = True) -> str:
    _require(isinstance(value, str) and len(value) <= 500, "invalid_text")
    _require(empty or bool(value.strip()), "empty_text")
    _require(not _UNSAFE.search(value), "unsafe_text")
    return value


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1e15


def _size(value: Any) -> None:
    _require(len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) <= MAX_BYTES, "payload_too_large")


def _shape(params: Any) -> dict:
    _require(isinstance(params, dict), "invalid_spec")
    _size(params)
    _require(_REQUIRED <= params.keys() and not params.keys() - _FIELDS, "unknown_or_missing_field")
    _require(type(params["version"]) is int and params["version"] == 1, "unsupported_version")
    template = params["template"]
    _require(template in TEMPLATES, "unknown_template")
    _require(params["basis"] in ("source", "illustrative"), "invalid_basis")
    result = {"version": 1, "template": template, "basis": params["basis"], "title": _text(params["title"], empty=False)}
    for key in ("subtitle", "takeaway", "unit"):
        result[key] = _text(params.get(key, ""))
    columns, rows = params["columns"], params["rows"]
    _require(isinstance(columns, list) and 2 <= len(columns) <= 6, "invalid_columns")
    result["columns"] = [_text(c, empty=False) for c in columns]
    _require(len(set(columns)) == len(columns), "duplicate_columns")
    _require(isinstance(rows, list) and 1 <= len(rows) <= 80, "invalid_rows")
    normalized = []
    for row in rows:
        _require(isinstance(row, list) and len(row) == len(columns), "ragged_row")
        clean = []
        for cell in row:
            if cell is None or _number(cell):
                clean.append(cell)
            else:
                clean.append(_text(cell))
        normalized.append(clean)
    result["rows"] = normalized
    if params["basis"] == "source":
        _require(not any(isinstance(c, str) and re.match(r"^\s*[+\-]?(?:\d|\.\d)", c)
                         for r in normalized for c in r[1:]), "numeric_text_is_unbound")
    if template in ("bar", "line", "area", "donut", "scatter"):
        for row in normalized:
            if template == "scatter":
                _require(row[0] is None or _number(row[0]), "invalid_x")
            else:
                _text(row[0], empty=False)
            _require(all(v is None or _number(v) for v in row[1:]), "nonnumeric_series")
        _require(any(_number(v) for r in normalized for v in r[1:]), "no_numeric_data")
    if template == "donut":
        _require(len(columns) == 2 and len(rows) <= 12, "invalid_donut_cardinality")
        _require(all(r[1] is None or r[1] >= 0 for r in normalized), "negative_share")
        _require(sum(r[1] or 0 for r in normalized) > 0, "empty_total")
    if template in ("status", "scenarios", "timeline", "flow"):
        _require(len(columns) in (2, 3) and len(rows) <= 20, "invalid_narrative_cardinality")
        _require(all(isinstance(c, str) or c is None for r in normalized for c in r), "narrative_cells_must_be_text")
    if template == "metrics":
        _require(len(columns) in (2, 3) and len(rows) <= 6, "invalid_metric_cardinality")
    return result


def _pointer(value: Any, pointer: Any) -> Any:
    _require(isinstance(pointer, str) and 0 < len(pointer) <= 512 and pointer.startswith("/"), "invalid_source_pointer")
    parts = pointer[1:].split("/")
    _require(len(parts) <= 32, "source_pointer_too_deep")
    for part in parts:
        _require(not re.search(r"~(?![01])", part), "invalid_source_pointer")
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            _require(key in value, "source_not_found")
            value = value[key]
        elif isinstance(value, list):
            _require(bool(re.fullmatch(r"0|[1-9][0-9]*", key)), "invalid_source_index")
            index = int(key)
            _require(index < len(value), "source_not_found")
            value = value[index]
        else:
            raise VisualError("source_not_found")
    return value


def _bind(view: dict, bindings: Any, observations: Sequence[tuple[str, Any]]) -> dict:
    _require(isinstance(bindings, list) and len(bindings) <= 480, "invalid_bindings")
    numeric = {(ri, ci) for ri, row in enumerate(view["rows"]) for ci, cell in enumerate(row) if _number(cell)}
    if view["basis"] == "illustrative":
        _require(not bindings, "illustrations_cannot_claim_sources")
        return {"numeric_cells_matched": 0, "sources": [], "semantic_verification": False, "freshness_verified": False}
    _require(bool(numeric), "source_requires_numeric_data")
    # Retain the existing tool-use ID to distinguish repeated source calls.
    records = [(o[0], o[1], o[2] if len(o) == 3 else None) for o in observations]
    matched, sources = set(), set()
    for b in bindings:
        _require(isinstance(b, dict) and {"row", "column", "tool", "pointer"} <= set(b)
                 and not set(b) - {"row", "column", "tool", "pointer", "call_id"}, "invalid_binding")
        ri, ci, tool = b["row"], b["column"], b["tool"]
        _require(type(ri) is int and type(ci) is int, "invalid_cell_index")
        cell = (ri, ci)
        _require(cell in numeric and cell not in matched, "duplicate_or_invalid_binding")
        _require(isinstance(tool, str) and bool(_TOKEN.fullmatch(tool)) and tool != "render_inline_visual", "invalid_source_tool")
        call_id = b.get("call_id")
        _require(call_id is None or (isinstance(call_id, str) and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", call_id))), "invalid_call_id")
        candidates = [record for record in records if record[0] == tool and (call_id is None or record[2] == call_id)]
        _require(len(candidates) == 1, "ambiguous_or_missing_source_call")
        source = candidates[0][1]
        _require(isinstance(source, (dict, list)), "source_not_found")
        if isinstance(source, dict):
            _require(not source.get("error") and source.get("ok") is not False, "source_failed")
        value = _pointer(source, b["pointer"])
        _require(_number(value) and value == view["rows"][ri][ci], "source_value_mismatch")
        matched.add(cell)
        sources.add(tool)
    _require(matched == numeric, "unbound_numeric_cell")
    return {"numeric_cells_matched": len(matched), "sources": sorted(sources), "semantic_verification": False, "freshness_verified": False}


def compile_visual(params: Any, observations: Sequence[tuple[str, Any]], identity: str,
                   *, screen: Callable[[str], bool] | None = None) -> dict:
    """Return an existing chart wire or a small non-sensitive correction receipt."""
    try:
        view = _shape(params)
        view["provenance"] = _bind(view, params.get("bindings", []), observations)
        if screen:
            text = "\n".join([view[k] for k in ("title", "subtitle", "takeaway", "unit")] + view["columns"] + [c for r in view["rows"] for c in r if isinstance(c, str)])
            _require(screen(text), "visual_copy_rejected")
        _require(isinstance(identity, str) and 0 < len(identity) <= 256, "invalid_identity")
        encoded = json.dumps(view, sort_keys=True, ensure_ascii=False, allow_nan=False)
        ident = hashlib.sha256((identity + "\n" + encoded).encode("utf-8")).hexdigest()[:24]
        wire = {"type": "chart", "visual_id": ident, "visual": view}
        _size(wire)
        return wire
    except (VisualError, TypeError, ValueError, OverflowError, RecursionError, KeyError, IndexError):
        return {"error": "visual_not_available", "note": "Use a supported bounded template and exact prior numeric source bindings; otherwise label the example illustrative."}


def validate_view(wire: Any) -> bool:
    """Validate retained presentation ONLY, never re-admit a tool/source or expose meta."""
    try:
        _require(isinstance(wire, dict) and set(wire) == {"type", "visual_id", "visual"}, "invalid_wire")
        _size(wire)
        _require(wire["type"] == "chart" and isinstance(wire["visual_id"], str) and bool(_ID.fullmatch(wire["visual_id"])), "invalid_wire")
        view = wire["visual"]
        _require(isinstance(view, dict) and set(view) == (_REQUIRED | {"subtitle", "takeaway", "unit", "provenance"}), "invalid_view")
        clean = _shape({k: v for k, v in view.items() if k != "provenance"})
        p = view["provenance"]
        _require(isinstance(p, dict) and set(p) == {"numeric_cells_matched", "sources", "semantic_verification", "freshness_verified"}, "invalid_provenance")
        _require(p["semantic_verification"] is False and p["freshness_verified"] is False, "unsupported_claim")
        _require(type(p["numeric_cells_matched"]) is int and isinstance(p["sources"], list) and len(p["sources"]) <= 40, "invalid_provenance")
        _require(all(isinstance(t, str) and bool(_TOKEN.fullmatch(t)) for t in p["sources"]), "invalid_source")
        count = sum(_number(c) for r in clean["rows"] for c in r)
        _require((clean["basis"] == "source" and count > 0 and p["numeric_cells_matched"] == count and bool(p["sources"])) or
                 (clean["basis"] == "illustrative" and p["numeric_cells_matched"] == 0 and not p["sources"]), "invalid_claim")
        return True
    except (VisualError, TypeError, ValueError, OverflowError, RecursionError, KeyError):
        return False


def public_visuals(meta: Any) -> list[dict]:
    """Project only bounded display payloads after the caller's existing thread auth."""
    if not isinstance(meta, dict) or not isinstance(meta.get("visuals"), list):
        return []
    return [v for v in meta["visuals"][:MAX_VISUALS] if validate_view(v)]


def tool_schema() -> dict:
    cell = {"type": ["string", "number", "null"]}
    return {"name": "render_inline_visual", "description":
        "Draw a preset chart/table/metrics/scenario/timeline/relationship visual in this reply. "
        "Prefer zero or one useful visual after an answer. Keep price candles on render_inline_chart. "
        "For observed numeric data use basis=source and bind EVERY numeric cell to a completed prior tool "
        "with {row,column,tool,pointer,call_id}; repeated tools require the exact existing tool-use call_id. "
        "Pointer is RFC6901 into that result. Values must match exactly; "
        "do not invent freshness, units or evidence. For teaching examples use illustrative (visibly unverified). "
        "Line/bar/area: first column category, remaining numbers/null, one shared unit. Scatter: numeric X,Y. "
        "Donut: category and nonnegative value. Metrics: label,value,optional delta. Narrative templates: 2-3 text columns. "
        "No HTML/URLs/styles. At most four per report. Final guards may withhold a rejected visual.",
        "input_schema": {"type": "object", "additionalProperties": False,
            "required": sorted(_REQUIRED), "properties": {
                "version": {"type": "integer", "enum": [1]}, "template": {"type": "string", "enum": list(TEMPLATES)},
                "title": {"type": "string", "maxLength": 500}, "subtitle": {"type": "string", "maxLength": 500},
                "takeaway": {"type": "string", "maxLength": 500}, "unit": {"type": "string", "maxLength": 500},
                "basis": {"type": "string", "enum": ["source", "illustrative"]},
                "columns": {"type": "array", "minItems": 2, "maxItems": 6, "items": {"type": "string", "maxLength": 500}},
                "rows": {"type": "array", "minItems": 1, "maxItems": 80, "items": {"type": "array", "minItems": 2, "maxItems": 6, "items": cell}},
                "bindings": {"type": "array", "maxItems": 480, "items": {"type": "object", "additionalProperties": False,
                    "required": ["row", "column", "tool", "pointer"], "properties": {
                        "row": {"type": "integer", "minimum": 0, "maximum": 79},
                        "column": {"type": "integer", "minimum": 0, "maximum": 5},
                        "call_id": {"type": "string", "maxLength": 128},
                        "tool": {"type": "string", "maxLength": 80}, "pointer": {"type": "string", "maxLength": 512}}}}}}}
