"""Classification-axis registry (WS:GMI-THEME-GRAPH Taxonomy V2, lane L11).

The registry composes the per-axis readers into one display-only AxisRow.
These tests inject every reader, so discovery never reaches a real axis
module. They pin: the exact row shape, per-axis soft failure, import
failure classification, subject/as_of/axes validation before any reader
call, abstention freshness against the theme-graph edges contract,
``validate_row``'s never-raise contract, agreement with the JSON Schemas,
and the module's own source bans.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import json
import sys
import types
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.classification_axes import cell
from engine.classification_axes import registry as registry_mod

ROOT = Path(__file__).resolve().parents[1]
ROW_SCHEMA_PATH = ROOT / "contracts" / "classification_axes" / "axis_row.v1.schema.json"
CELL_SCHEMA_PATH = ROOT / "contracts" / "classification_axes" / "axis_cell.v1.schema.json"
EDGES_SCHEMA_PATH = ROOT / "contracts" / "theme_graph" / "edges.v1.schema.json"
REGISTRY_PATH = ROOT / "engine" / "classification_axes" / "registry.py"

ROW_SCHEMA = json.loads(ROW_SCHEMA_PATH.read_text(encoding="utf-8"))
CELL_SCHEMA = json.loads(CELL_SCHEMA_PATH.read_text(encoding="utf-8"))
ROW_VALIDATOR = Draft202012Validator(ROW_SCHEMA)
CELL_VALIDATOR = Draft202012Validator(CELL_SCHEMA)

AS_OF = "2026-10-11"
SUBJECT = "co:us:AAPL"
ROW_KEYS = frozenset({
    "schema_version",
    "subject_id",
    "as_of",
    "cells",
    "abstentions",
    "labels",
    "quality",
})
EXPECTED_ABSTENTIONS = ({
    "facet": "supply_chain",
    "status": "not_populated",
    "labels": ["NO_MAPPING"],
    "reserved_edge_types": ["BENEFITS_FROM", "BOTTLENECK_OF", "ENABLES", "SUPPLIES"],
    "contract": "contracts/theme_graph/edges.v1.schema.json",
},)


def _cell_source(axis: str) -> dict:
    return {
        "owner": f"engine.classification_axes.{axis}",
        "artifact": f"engine/classification_axes/{axis}.py",
        "field": None,
    }


def _ok_cell(axis: str, subject_id: str, as_of: str = AS_OF, **overrides: object) -> dict:
    return cell.available(
        axis=axis,
        subject_id=subject_id,
        value={"reading": f"{axis}:{subject_id}"},
        as_of=as_of,
        source=_cell_source(axis),
        **overrides,
    )


_UNSET = object()


def _recorder(axis: str, log: list, out: object = _UNSET):
    """An injected reader: logs its axis, raises/returns ``out`` when given."""

    def reader(subject_id: str, *, as_of: str, root: object = None) -> dict:
        log.append(axis)
        if isinstance(out, Exception):
            raise out
        if out is not _UNSET:
            return out  # type: ignore[no-any-return]
        return _ok_cell(axis, subject_id, as_of=as_of)

    return reader


def _all_readers(log: list) -> dict:
    return {axis: _recorder(axis, log) for axis in cell.AXES}


def _read(subject_id: str = SUBJECT, as_of: str = AS_OF, **kwargs: object):
    log: list = []
    row = registry_mod.read_axes(subject_id, as_of=as_of, readers=_all_readers(log), **kwargs)
    return row, log


def _valid_row() -> dict:
    row, _log = _read()
    assert registry_mod.validate_row(row) == []
    return row


def _foreign_cell(kind: str) -> dict:
    """A valid cell that answers a different question than the one asked."""
    if kind == "subject":
        return _ok_cell("geography", "co:us:MSFT")
    if kind == "axis":
        return _ok_cell("lifecycle", SUBJECT)
    return _ok_cell("geography", SUBJECT, as_of="2026-10-10")


def test_constants_and_public_surface_are_exact():
    assert registry_mod.ROW_SCHEMA_VERSION == "axis_row.v1"
    assert registry_mod.REGISTRY_OWNER == "engine/classification_axes/registry.py"
    assert registry_mod.ROW_LABELS == ("read_time_composition",)
    assert registry_mod.ABSTENTIONS == EXPECTED_ABSTENTIONS
    public = {
        name
        for name, obj in inspect.getmembers(registry_mod, inspect.isfunction)
        if not name.startswith("_") and obj.__module__ == registry_mod.__name__
    }
    assert public == {"read_axes", "validate_row", "row_to_json", "abstentions"}


def test_six_injected_readers_produce_six_cells_in_axes_order():
    row, log = _read()
    assert set(row) == ROW_KEYS
    assert list(row["cells"]) == list(cell.AXES)
    assert sorted(log) == sorted(cell.AXES)
    for axis in cell.AXES:
        one = row["cells"][axis]
        assert one["axis"] == axis
        assert one["status"] == "available"
        assert one["subject_id"] == SUBJECT
        assert one["as_of"] == AS_OF
        assert cell.validate_cell(one) == []
        assert one["value"] == {"reading": f"{axis}:{SUBJECT}"}
    assert row["schema_version"] == "axis_row.v1"
    assert row["subject_id"] == SUBJECT
    assert row["as_of"] == AS_OF
    assert row["abstentions"] == list(EXPECTED_ABSTENTIONS)
    assert row["labels"] == ["read_time_composition"]
    assert row["quality"] == "display_only"
    assert registry_mod.validate_row(row) == []


def test_axes_selection_is_deduped_and_reordered():
    log: list = []
    row = registry_mod.read_axes(
        SUBJECT,
        as_of=AS_OF,
        axes=("lifecycle", "geography", "lifecycle"),
        readers=_all_readers(log),
    )
    assert list(row["cells"]) == ["geography", "lifecycle"]
    assert log == ["geography", "lifecycle"]
    assert registry_mod.validate_row(row) == []


@pytest.mark.parametrize("bad_axes", ["geography", (), ("geography", "nope"), 42])
def test_bad_axes_selection_raises_before_any_reader_call(bad_axes):
    log: list = []
    with pytest.raises(cell.AxisCellError):
        registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=bad_axes, readers=_all_readers(log))
    assert log == []


def test_unknown_readers_key_raises():
    log: list = []
    readers = _all_readers(log)
    readers["nope"] = readers["geography"]
    with pytest.raises(cell.AxisCellError):
        registry_mod.read_axes(SUBJECT, as_of=AS_OF, readers=readers)
    assert log == []


def test_non_callable_reader_value_raises():
    log: list = []
    readers = _all_readers(log)
    readers["geography"] = "not callable"
    with pytest.raises(cell.AxisCellError):
        registry_mod.read_axes(SUBJECT, as_of=AS_OF, readers=readers)
    assert log == []


@pytest.mark.parametrize("subject_id", ["ltheme:finviz:x", "foo", "basket:finviz_themes:x"])
def test_invalid_subject_raises_before_any_reader_call(subject_id):
    log: list = []
    with pytest.raises(cell.AxisCellError):
        registry_mod.read_axes(subject_id, as_of=AS_OF, readers=_all_readers(log))
    assert log == []


@pytest.mark.parametrize("as_of", ["2026-13-01", "2026-02-30", "20261012", None, ""])
def test_bad_as_of_raises_before_any_reader_call(as_of):
    log: list = []
    with pytest.raises(cell.AxisCellError):
        registry_mod.read_axes(SUBJECT, as_of=as_of, readers=_all_readers(log))
    assert log == []


def test_a_raising_reader_degrades_only_its_own_cell():
    log: list = []
    readers = _all_readers(log)
    readers["geography"] = _recorder("geography", log, RuntimeError("boom /secret/path"))
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, readers=readers)
    bad = row["cells"]["geography"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_degraded"
    assert bad["provenance"] == ["registry_caught:RuntimeError"]
    assert bad["value"] is None
    assert bad["labels"] == []
    assert bad["freshness"] is None
    assert bad["rights_context"] is None
    assert bad["source"] == {
        "owner": "engine/classification_axes/registry.py",
        "artifact": "engine/classification_axes/geography.py",
        "field": None,
    }
    assert "boom /secret/path" not in registry_mod.row_to_json(row)
    for axis in cell.AXES:
        if axis == "geography":
            continue
        one = row["cells"][axis]
        assert one["status"] == "available"
        assert one["value"] == {"reading": f"{axis}:{SUBJECT}"}
        assert one["provenance"] == []
    assert registry_mod.validate_row(row) == []


@pytest.mark.parametrize("bad_return", [None, {"axis": "x"}])
def test_invalid_reader_return_degrades_its_cell(bad_return):
    log: list = []
    readers = _all_readers(log)
    readers["lifecycle"] = _recorder("lifecycle", log, bad_return)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, readers=readers)
    bad = row["cells"]["lifecycle"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_degraded"
    assert bad["provenance"] == ["registry_invalid_cell"]
    assert registry_mod.validate_row(row) == []


@pytest.mark.parametrize("kind", ["subject", "axis", "as_of"])
def test_foreign_but_valid_cell_degrades_with_mismatch(kind):
    log: list = []
    readers = _all_readers(log)
    readers["geography"] = _recorder("geography", log, _foreign_cell(kind))
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, readers=readers)
    bad = row["cells"]["geography"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_degraded"
    assert bad["provenance"] == ["registry_mismatched_cell"]
    assert registry_mod.validate_row(row) == []


def test_reader_module_absent_is_owner_missing(monkeypatch):
    real = importlib.import_module

    def fake(name, *args, **kwargs):
        if name == "engine.classification_axes.geography":
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return real(name, *args, **kwargs)

    monkeypatch.setattr(registry_mod.importlib, "import_module", fake)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("geography",))
    bad = row["cells"]["geography"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_missing"
    assert bad["provenance"] == ["registry_reader_absent"]
    assert registry_mod.validate_row(row) == []


def test_missing_dependency_of_a_reader_is_owner_degraded(monkeypatch):
    real = importlib.import_module

    def fake(name, *args, **kwargs):
        if name == "engine.classification_axes.geography":
            raise ModuleNotFoundError("No module named 'some_dependency'", name="some_dependency")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(registry_mod.importlib, "import_module", fake)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("geography",))
    bad = row["cells"]["geography"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_degraded"
    assert bad["provenance"] == ["registry_import_error:ModuleNotFoundError"]
    assert registry_mod.validate_row(row) == []


def test_value_error_at_import_is_owner_degraded(monkeypatch):
    real = importlib.import_module

    def fake(name, *args, **kwargs):
        if name == "engine.classification_axes.geography":
            raise ValueError("bad module payload /private/path")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(registry_mod.importlib, "import_module", fake)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("geography",))
    bad = row["cells"]["geography"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_degraded"
    assert bad["provenance"] == ["registry_import_error:ValueError"]
    assert "bad module payload" not in registry_mod.row_to_json(row)
    assert registry_mod.validate_row(row) == []


def test_real_discovery_finds_a_module_placed_in_sys_modules(monkeypatch):
    fake = types.ModuleType("engine.classification_axes.geography")
    fake.read_geography = lambda subject_id, *, as_of, root=None: _ok_cell("geography", subject_id, as_of=as_of)
    monkeypatch.setitem(sys.modules, "engine.classification_axes.geography", fake)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("geography",))
    good = row["cells"]["geography"]
    assert good["status"] == "available"
    assert good["value"] == {"reading": f"geography:{SUBJECT}"}
    assert registry_mod.validate_row(row) == []


def test_module_without_the_reader_entry_point_is_owner_degraded(monkeypatch):
    fake = types.ModuleType("engine.classification_axes.geography")
    monkeypatch.setitem(sys.modules, "engine.classification_axes.geography", fake)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("geography",))
    bad = row["cells"]["geography"]
    assert bad["status"] == "unavailable"
    assert bad["reason_code"] == "owner_degraded"
    assert bad["provenance"] == ["registry_reader_missing"]
    assert registry_mod.validate_row(row) == []


def test_non_callable_reader_attribute_is_owner_degraded(monkeypatch):
    fake = types.ModuleType("engine.classification_axes.geography")
    fake.read_geography = "not callable"
    monkeypatch.setitem(sys.modules, "engine.classification_axes.geography", fake)
    row = registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("geography",))
    bad = row["cells"]["geography"]
    assert bad["provenance"] == ["registry_reader_missing"]
    assert registry_mod.validate_row(row) == []


def test_keyboard_interrupt_from_a_reader_propagates():
    def interrupt(subject_id: str, *, as_of: str, root: object = None) -> dict:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        registry_mod.read_axes(SUBJECT, as_of=AS_OF, axes=("lifecycle",), readers={"lifecycle": interrupt})


def test_rows_are_byte_identical_across_calls():
    first = registry_mod.row_to_json(_read()[0])
    second = registry_mod.row_to_json(_read()[0])
    assert first == second


def _edge_type_enum() -> list:
    doc = json.loads(EDGES_SCHEMA_PATH.read_text(encoding="utf-8"))
    stack = [doc]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            spec = node.get("type")
            if isinstance(spec, dict) and isinstance(spec.get("enum"), list):
                return spec["enum"]  # type: ignore[no-any-return]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    raise AssertionError("edge type enum not found in the edges contract")


def test_abstentions_are_fresh_copies_pinned_to_the_edges_contract():
    assert registry_mod.abstentions() == list(registry_mod.ABSTENTIONS)
    first = registry_mod.abstentions()
    first[0]["facet"] = "mutated"
    first[0]["reserved_edge_types"].append("TRACKS")
    second = registry_mod.abstentions()
    assert second == list(registry_mod.ABSTENTIONS)
    assert registry_mod.ABSTENTIONS == EXPECTED_ABSTENTIONS
    enum = _edge_type_enum()
    reserved = registry_mod.ABSTENTIONS[0]["reserved_edge_types"]
    assert set(reserved) <= set(enum)
    assert reserved == sorted(reserved)


@pytest.mark.parametrize("garbage", [None, [], "x", {}])
def test_validate_row_never_raises_on_garbage(garbage):
    problems = registry_mod.validate_row(garbage)
    assert isinstance(problems, list)
    assert problems


def test_validate_row_reports_a_bad_cell_without_raising():
    row = _valid_row()
    row["cells"]["geography"] = {"axis": "geography"}
    problems = registry_mod.validate_row(row)
    assert problems
    assert any("geography" in problem for problem in problems)


def test_validate_row_reports_each_targeted_violation():
    row = _valid_row()

    missing_key = dict(row)
    del missing_key["labels"]
    assert any("labels" in problem for problem in registry_mod.validate_row(missing_key))

    extra_key = dict(row)
    extra_key["summary"] = {"note": "n"}
    assert any("summary" in problem for problem in registry_mod.validate_row(extra_key))

    out_of_order = dict(row)
    out_of_order["cells"] = {
        "lifecycle": row["cells"]["lifecycle"],
        "geography": row["cells"]["geography"],
    }
    assert any("order" in problem.lower() for problem in registry_mod.validate_row(out_of_order))

    foreign_subject = dict(row)
    foreign_subject["cells"] = dict(row["cells"])
    foreign_subject["cells"]["geography"] = _ok_cell("geography", "co:us:MSFT")
    assert any("subject" in problem for problem in registry_mod.validate_row(foreign_subject))

    bad_abstention = dict(row)
    bad_abstention["abstentions"] = [dict(row["abstentions"][0], status="reserved")]
    assert any("status" in problem for problem in registry_mod.validate_row(bad_abstention))

    wrong_labels = dict(row)
    wrong_labels["labels"] = ["NO_MAPPING"]
    assert any("labels" in problem for problem in registry_mod.validate_row(wrong_labels))

    non_dict_cells = dict(row)
    non_dict_cells["cells"] = ["geography"]
    assert any("cells" in problem for problem in registry_mod.validate_row(non_dict_cells))

    bad_quality = dict(row)
    bad_quality["quality"] = "aggregate"
    assert any("quality" in problem for problem in registry_mod.validate_row(bad_quality))

    bad_version = dict(row)
    bad_version["schema_version"] = "axis_row.v2"
    assert any("schema_version" in problem for problem in registry_mod.validate_row(bad_version))


def _has_ref_key(node: object) -> bool:
    """True when any schema position carries a ``$ref`` keyword."""
    if isinstance(node, dict):
        return "$ref" in node or any(_has_ref_key(value) for value in node.values())
    if isinstance(node, list):
        return any(_has_ref_key(value) for value in node)
    return False


def test_row_schema_document_shape():
    assert ROW_SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert ROW_SCHEMA["$id"] == "axis_row.v1"
    assert ROW_SCHEMA["additionalProperties"] is False
    assert set(ROW_SCHEMA["required"]) == set(ROW_KEYS)
    assert ROW_SCHEMA["properties"]["schema_version"] == {"const": "axis_row.v1"}
    assert ROW_SCHEMA["properties"]["quality"] == {"const": "display_only"}
    assert ROW_SCHEMA["properties"]["labels"] == {"const": ["read_time_composition"]}
    cells_schema = ROW_SCHEMA["properties"]["cells"]
    assert cells_schema["minProperties"] == 1
    assert cells_schema["propertyNames"]["enum"] == list(cell.AXES)
    assert cells_schema["additionalProperties"] == {"type": "object"}
    assert (
        ROW_SCHEMA["properties"]["as_of"]["pattern"]
        == CELL_SCHEMA["properties"]["as_of"]["pattern"]
    )
    abstention_schema = ROW_SCHEMA["properties"]["abstentions"]["items"]
    assert abstention_schema["additionalProperties"] is False
    assert set(abstention_schema["required"]) == {
        "facet", "status", "labels", "reserved_edge_types", "contract",
    }
    assert abstention_schema["properties"]["status"] == {"const": "not_populated"}
    Draft202012Validator.check_schema(ROW_SCHEMA)
    description = ROW_SCHEMA["description"]
    assert "axis_cell.v1.schema.json" in description
    assert "registry.validate_row" in description
    assert "Python-only" in description
    assert not _has_ref_key(ROW_SCHEMA)


def test_produced_row_and_cells_validate_against_the_schemas():
    row = _valid_row()
    assert ROW_VALIDATOR.is_valid(row)
    for one in row["cells"].values():
        assert CELL_VALIDATOR.is_valid(one)

    def unknown_reader(subject_id: str, *, as_of: str, root: object = None) -> dict:
        return cell.missing(
            axis="sic_industry",
            subject_id=subject_id,
            status="unknown",
            reason_code="value_missing",
            as_of=as_of,
            source=_cell_source("sic_industry"),
        )

    degraded = registry_mod.read_axes(
        SUBJECT,
        as_of=AS_OF,
        axes=("sic_industry",),
        readers={"sic_industry": unknown_reader},
    )
    assert degraded["cells"]["sic_industry"]["status"] == "unknown"
    assert ROW_VALIDATOR.is_valid(degraded)
    assert CELL_VALIDATOR.is_valid(degraded["cells"]["sic_industry"])


def test_row_schema_rejects_shape_violations():
    row = _valid_row()

    extra = dict(row)
    extra["notes"] = "n"
    assert not ROW_VALIDATOR.is_valid(extra)

    bad_quality = dict(row)
    bad_quality["quality"] = "aggregate"
    assert not ROW_VALIDATOR.is_valid(bad_quality)

    unknown_axis = dict(row)
    unknown_axis["cells"] = dict(row["cells"])
    unknown_axis["cells"]["sector"] = row["cells"]["geography"]
    assert not ROW_VALIDATOR.is_valid(unknown_axis)

    empty_cells = dict(row)
    empty_cells["cells"] = {}
    assert not ROW_VALIDATOR.is_valid(empty_cells)


def test_registry_source_honors_the_bans():
    source = REGISTRY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                imported.add(node.module)
    banned = (
        "engine.intelligence_workspace",
        "engine.market_ontology",
        "engine.company_intelligence",
        "engine.theme_graph",
        "scripts",
        "pandas",
        "numpy",
    )
    for prefix in banned:
        offenders = [name for name in imported if name == prefix or name.startswith(prefix + ".")]
        assert offenders == []
    for axis in cell.AXES:
        assert f"engine.classification_axes.{axis}" not in imported
    engine_imports = sorted(name for name in imported if name == "engine" or name.startswith("engine."))
    assert engine_imports == ["engine.classification_axes"]
    for token in ("datetime.now", "date.today", "time.time", "lru_cache", "open("):
        assert token not in source
