"""Regulator, manufacturer and capacity kept as three separate foresight clauses.

Synthetic inputs only. The product module must not read the shortage store, must
not call the network, and must not import the scarcity engine or the theme graph.
The capacity slot is a closed refusal: no caller can hand it a thesis.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGULATOR = {"current": 2, "resolved": 0, "discontinued": 1}
MANUFACTURER = {"available": 0, "limited": 2, "unavailable": 0, "not_stated": 1}
BANNED = ("demand exceeds supply", "active", "rank", "size", "entry")


def _english_halves(split):
    return [split[slot]["en"] for slot in ("regulator", "manufacturer", "capacity")]


def test_three_slots_stay_separate():
    from engine.healthcare_observation_split import observation_split_clause

    split = observation_split_clause(REGULATOR, MANUFACTURER, capture_incomplete=False)
    regulator, manufacturer, capacity = (
        split["regulator"], split["manufacturer"], split["capacity"],
    )

    # Regulator names only the non-zero regulator words and its own slot.
    assert "regulator" in regulator["en"]
    assert "current" in regulator["en"]
    assert "discontinued" in regulator["en"]
    assert "resolved" not in regulator["en"]
    assert "manufacturer" not in regulator["en"]
    assert "limited" not in regulator["en"]

    # Manufacturer names only the non-zero availability words and its own slot.
    assert "manufacturer" in manufacturer["en"]
    assert "limited" in manufacturer["en"]
    assert "not stated" in manufacturer["en"]
    assert "available" not in manufacturer["en"]
    assert "unavailable" not in manufacturer["en"]
    assert "regulator" not in manufacturer["en"]
    assert "current" not in manufacturer["en"]

    # Capacity is the closed refusal: no number can ride in on it.
    assert "not observed" in capacity["en"]
    assert "capacity" in capacity["en"]
    assert not any(character.isdigit() for character in capacity["en"])

    for slot in (regulator, manufacturer, capacity):
        assert slot["zh"], "the Chinese half is its own string, never empty"
        assert slot["zh"] != slot["en"]
    for english in _english_halves(split):
        assert english.isascii()


def test_incomplete_capture_publishes_no_digit():
    from engine.healthcare_observation_split import observation_split_clause

    split = observation_split_clause(REGULATOR, MANUFACTURER, capture_incomplete=True)
    regulator, manufacturer, capacity = (
        split["regulator"], split["manufacturer"], split["capacity"],
    )
    assert "regulator" in regulator["en"]
    assert not any(character.isdigit() for character in regulator["en"])
    assert "manufacturer" in manufacturer["en"]
    assert not any(character.isdigit() for character in manufacturer["en"])
    assert "not observed" in capacity["en"]
    assert not any(character.isdigit() for character in capacity["en"])
    for slot in (regulator, manufacturer, capacity):
        assert slot["zh"] and slot["zh"] != slot["en"]
    for english in _english_halves(split):
        assert english.isascii()


def test_capacity_slot_never_claims_a_thesis():
    from engine.healthcare_observation_split import observation_split_clause

    for incomplete in (False, True):
        split = observation_split_clause(
            REGULATOR, MANUFACTURER, capture_incomplete=incomplete
        )
        capacity = split["capacity"]["en"]
        assert "not observed" in capacity
        assert "capacity" in capacity
        lowered = capacity.lower()
        for phrase in BANNED:
            assert phrase not in lowered
        assert "$" not in capacity
        assert not any(character.isdigit() for character in capacity)
        # No English half of the split may carry a banned phrase either.
        for english in _english_halves(split):
            for phrase in BANNED:
                assert phrase not in english.lower(), english
            assert "$" not in english

    # A caller cannot pass a thesis string: the function has no such argument.
    parameters = list(inspect.signature(observation_split_clause).parameters)
    assert len(parameters) == 3, parameters
    for name in parameters:
        lowered = name.lower()
        assert "thesis" not in lowered
        assert "text" not in lowered
        assert "capacity" not in lowered


def _observation_inputs_row(rows, freshness):
    """Minimal scarcity row in the shape the cascade reads.

    Keys mirror the publisher: row keys at engine/fda_scarcity.py:190-191 and
    :194 (absent), summary.freshness keys at engine/fda_scarcity.py:461 and
    :468; the consumer is engine/foresight_cascade.py:331-364, which returns
    (regulator_counts, manufacturer_counts, capture_incomplete) or None.
    """
    return {
        "summary": {
            "counts": {"current": 1, "resolved": 0, "discontinued": 0},
            "rows": rows,
            "freshness": freshness,
        }
    }


def test_observation_inputs_tally_skips_rows_absent_from_the_generation():
    from engine.foresight_cascade import _fda_observation_inputs

    available = {"manufacturer_availability": "Available",
                 "availability_normalized": "available"}
    rows = [dict(available, absent=False), dict(available, absent=True)]
    freshness = {"capture_qualified": True, "capture_incomplete": False}
    inputs = _fda_observation_inputs(_observation_inputs_row(rows, freshness))

    assert inputs is not None
    regulator, manufacturer, capture_incomplete = inputs
    assert regulator == {"current": 1, "resolved": 0, "discontinued": 0}
    assert manufacturer == {
        "available": 1, "limited": 0, "unavailable": 0, "not_stated": 0,
    }
    assert capture_incomplete is False


def test_observation_inputs_are_none_when_the_source_did_not_answer():
    from engine.foresight_cascade import _fda_observation_inputs

    rows = [{"manufacturer_availability": "Limited",
             "availability_normalized": "limited", "absent": False}]
    freshness = {"capture_qualified": False, "capture_incomplete": False}
    unqualified = _fda_observation_inputs(_observation_inputs_row(rows, freshness))
    assert unqualified is None


def test_observation_inputs_publish_the_withheld_form_for_unfinished_capture():
    from engine.foresight_cascade import _fda_observation_inputs

    rows = [{"manufacturer_availability": "Limited",
             "availability_normalized": "limited", "absent": False}]
    freshness = {"capture_qualified": False, "capture_incomplete": True}
    inputs = _fda_observation_inputs(_observation_inputs_row(rows, freshness))

    assert inputs is not None, "an unfinished capture must still reach the clause"
    _regulator, _manufacturer, capture_incomplete = inputs
    assert capture_incomplete is True


def test_template_reads_observation_split_outside_the_title():
    text = (ROOT / "templates" / "foresight.html.j2").read_text(encoding="utf-8")
    assert "observation_split" in text
    start = text.index('<div class="fx-chips">')
    block = text[start:text.index("</div>", start)]
    assert "observation_split" in block
    assert "t(" in block[block.index("observation_split"):]
    title_lines = [
        line for line in text.splitlines() if 'title="{{ tfs.rationale' in line
    ]
    assert title_lines
    for line in title_lines:
        assert "observation_split" not in line
    for slot in ("regulator", "manufacturer", "capacity"):
        needle = f"t(osp.{slot}.en, osp.{slot}.zh)"
        assert needle in block, f"the {slot} clause chip must render"
    for line in text.splitlines():
        if "title=" in line:
            assert "osp." not in line, line
            assert "observation_split" not in line, line


def test_cascade_source_calls_the_helper_and_does_not_edit_the_chip_dict():
    source = (ROOT / "engine" / "foresight_cascade.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    chip_line = None
    split_line = None
    row_assigns_split = False
    chip_mutated = False
    closure_safe_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name == "format_theme_feed_chip":
                chip_line = node.lineno
            if name == "observation_split_clause":
                split_line = node.lineno
            if name == "import_module" and node.args and isinstance(node.args[0], ast.BinOp):
                parts = [
                    operand.value
                    for operand in (node.args[0].left, node.args[0].right)
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, str)
                ]
                if "".join(parts) == "engine.healthcare_observation_split":
                    closure_safe_import = True
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {"update", "setdefault", "pop"}
                and isinstance(func.value, ast.Name)
                and func.value.id == "theme_feed_summary"
            ):
                chip_mutated = True
        if isinstance(node, ast.Subscript) and isinstance(getattr(node, "ctx", None), ast.Store):
            if isinstance(node.value, ast.Name) and node.value.id == "theme_feed_summary":
                chip_mutated = True
        if isinstance(node, ast.Dict):
            keys = {key.value for key in node.keys if isinstance(key, ast.Constant)}
            if "observation_split" in keys and "theme" in keys:
                row_assigns_split = True
            if "observation_split" in keys and "rationale" in keys and "theme" not in keys:
                chip_mutated = True
    assert split_line is not None and chip_line is not None
    assert split_line > chip_line
    assert row_assigns_split
    assert chip_mutated is False
    assert "healthcare_observation_split" in source
    assert closure_safe_import, (
        "the helper is reached through a split module name, so the closure walk "
        "does not attach it to every exclusive job that already walks the cascade"
    )


def test_module_imports_no_scarcity_or_theme_graph():
    from engine.healthcare_observation_split import observation_split_clause

    source = Path(
        observation_split_clause.__code__.co_filename
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "fda_scarcity" not in node.module
            assert "theme_graph" not in node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "fda_scarcity" not in alias.name
                assert "theme_graph" not in alias.name
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            assert name not in {"urlopen", "read_parquet", "request"}, name
    assert "shortages.parquet" not in source
    assert "importlib" not in source
