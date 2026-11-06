"""Configured FDA molecules with no rows — bilingual clause beside the foresight chip.

Synthetic inputs only. The product module must not read the shortage store.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_absent_molecule_is_named_and_present_ones_are_not():
    from engine.healthcare_molecule_gap import molecule_gap_clause

    clause = molecule_gap_clause(
        ("semaglutide", "tirzepatide", "liraglutide"),
        ("semaglutide", "liraglutide"),
    )
    english, chinese = clause["en"], clause["zh"]
    assert "tirzepatide" in english
    assert "no records" in english
    assert "semaglutide" not in english
    assert "liraglutide" not in english
    assert english.isascii()
    assert chinese
    assert chinese != english

    ordered = molecule_gap_clause(
        ("semaglutide", "tirzepatide", "liraglutide"),
        (),
    )
    assert ordered["en"].index("semaglutide") < ordered["en"].index("tirzepatide")
    assert ordered["en"].index("tirzepatide") < ordered["en"].index("liraglutide")
    assert ordered["zh"].index("semaglutide") < ordered["zh"].index("tirzepatide")

    source = Path(molecule_gap_clause.__code__.co_filename).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "fda_scarcity" not in node.module
            assert "theme_graph" not in node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "fda_scarcity" not in alias.name
                assert "theme_graph" not in alias.name
    assert "shortages.parquet" not in source


def test_full_coverage_is_none():
    from engine.healthcare_molecule_gap import molecule_gap_clause

    assert molecule_gap_clause(
        ("semaglutide", "tirzepatide", "liraglutide"),
        ("liraglutide", "semaglutide", "tirzepatide"),
    ) is None
    assert molecule_gap_clause((), ("semaglutide",)) is None
    assert molecule_gap_clause(None, None) is None


def test_clause_does_not_claim_a_count_or_a_banned_phrase():
    from engine.healthcare_molecule_gap import molecule_gap_clause

    clause = molecule_gap_clause(
        ("semaglutide", "tirzepatide", "liraglutide"),
        ("semaglutide",),
    )
    english = clause["en"]
    assert "demand exceeds supply" not in english
    assert "active" not in english
    assert not any(character.isdigit() for character in english)
    assert english.index("tirzepatide") < english.index("liraglutide")
    assert "semaglutide" not in english


def test_template_reads_molecule_gap_outside_the_title():
    text = (ROOT / "templates" / "foresight.html.j2").read_text(encoding="utf-8")
    assert "molecule_gap" in text
    start = text.index('<div class="fx-chips">')
    block = text[start:text.index("</div>", start)]
    assert "molecule_gap" in block
    assert "t(" in block[block.index("molecule_gap"):]
    title_lines = [
        line for line in text.splitlines() if 'title="{{ tfs.rationale' in line
    ]
    assert title_lines
    for line in title_lines:
        assert "molecule_gap" not in line


def test_cascade_source_calls_the_helper_and_does_not_edit_the_chip_dict():
    source = (ROOT / "engine" / "foresight_cascade.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    chip_line = None
    gap_line = None
    row_assigns_gap = False
    chip_mutated = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name == "format_theme_feed_chip":
                chip_line = node.lineno
            if name == "molecule_gap_clause":
                gap_line = node.lineno
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
            keys = {
                key.value for key in node.keys
                if isinstance(key, ast.Constant)
            }
            if "molecule_gap" in keys and "theme" in keys:
                row_assigns_gap = True
            if "molecule_gap" in keys and "rationale" in keys and "theme" not in keys:
                chip_mutated = True
    assert gap_line is not None and chip_line is not None
    assert gap_line > chip_line
    assert row_assigns_gap
    assert chip_mutated is False
    assert "healthcare_molecule_gap" in source
