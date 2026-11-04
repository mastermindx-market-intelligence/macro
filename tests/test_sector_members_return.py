"""D05 Members display-source and typed return contract; no model/data publication."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def producer():
    # Execute the exact pure producer helpers, avoiding unrelated model imports.
    # Browser composition additionally uses the complete actual template.
    source = (ROOT / "scripts/build_theme_detail.py").read_text()
    parsed = ast.parse(source)
    functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"_member_rows", "_detail_payload"}]
    assert len(functions) == 2
    scope = {"hashlib": hashlib, "json": json}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(ROOT / "scripts/build_theme_detail.py"), "exec"), scope)
    return scope


@pytest.mark.parametrize("value,state", [
    ({}, "unavailable"), ({"members": None}, "unavailable"),
    ({"members": "not a collection"}, "unavailable"), ({"members": [{}]}, "unavailable"),
    ({"members": [{"symbol": None}]}, "unavailable"),
    ({"members": [{"symbol": "XOM\n"}]}, "unavailable"),
    ({"members": []}, "empty"), ({"members": [{"symbol": "000001.SZ"}]}, "available"),
    ({"members": [{"symbol": "CNQ.TO", "conviction": None}]}, "available"),
])
def test_member_availability_preserves_empty_and_thin_distinctions(value, state):
    rows, actual = producer()["_member_rows"](value)
    assert actual == state
    if actual == "available":
        assert rows == value["members"]
    else:
        assert rows == []


def test_member_stamp_binds_exact_base_payload_not_generation_time():
    emit = producer()["_detail_payload"]
    source = {"basket": {"id": "energy"}, "region": "us", "as_of": None,
              "members_state": "available", "members": [{"symbol": "XOM", "conviction": None}],
              "stock_base": "../stock.html#"}
    payload, stamp = emit(source)
    assert json.loads(payload) == source
    assert stamp == "members1-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert emit(source) == (payload, stamp)  # separate HTML generation time is not an input
    for changed in [
        {**source, "region": "canada"},
        {**source, "stock_base": "../canada_stock.html#"},
        {**source, "members": [{"symbol": "XOM", "conviction": {"score": 1}}]},
        {**source, "members": [{"symbol": "CVX", "conviction": None}]},
        {**source, "as_of": "2026-10-30"},
    ]:
        assert emit(changed)[1] != stamp
    assert not stamp.startswith("cycp1-")


def test_missing_and_explicit_empty_stamps_are_distinct():
    scope = producer()
    stamps = []
    for basket in [{"id": "energy"}, {"id": "energy", "members": []}]:
        rows, state = scope["_member_rows"](basket)
        stamps.append(scope["_detail_payload"]({"basket": basket, "members": rows, "members_state": state})[1])
    assert stamps[0] != stamps[1]
