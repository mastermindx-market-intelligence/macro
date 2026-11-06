"""RATIFIED 2026-10-21 micro-theme expansion — additive display tier, frozen table intact.

The expansion rows (C1+C2+C3 union, ratified by GMI COMPLETION seat 6f14c2da;
receipts copied verbatim to research/theme_graph/micro_expansion_20261021/)
append sub_themes/micro_themes/parents to config/theme_crosswalk.yml dated
2026-10-21. They are display-tier taxonomy only: no membership, no issuer
mapping, no evaluation authority, and no change to the frozen 68-micro
acceptance set (DECLARED_MICRO_COUNT stays 68 in scripts/gmi_coverage_proof.py).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from engine.theme_graph.materialize import validate_theme_hierarchy
from engine.theme_graph.membership_evidence import MICRO_EXPANSION_ASSERTED_ON

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "config" / "theme_crosswalk.yml"
RECEIPTS = ROOT / "research/theme_graph/micro_expansion_20261021/RATIFICATION_RECEIPTS.md"
SECTIONS = ("categories", "sub_themes", "micro_themes", "parents")
VALUE_CHAIN_POSITIONS = ("upstream", "midstream", "downstream", "enabler")

DOC = yaml.safe_load(CROSSWALK.read_text(encoding="utf-8"))
HIERARCHY = DOC["hierarchy"]


def _expansion(section: str) -> list:
    return [row for row in HIERARCHY[section]
            if row["asserted_on"] == MICRO_EXPANSION_ASSERTED_ON]


def _frozen(section: str) -> list:
    return [row for row in HIERARCHY[section]
            if row["asserted_on"] < MICRO_EXPANSION_ASSERTED_ON]


def _expansion_research_targets() -> set[str]:
    return {row["nominated_from"] for section in ("sub_themes", "micro_themes")
            for row in _expansion(section)}


def test_expansion_rows_exist_and_are_exactly_the_expansion_date():
    appended = {section: _expansion(section) for section in SECTIONS}
    # The ratified union: C1 (20/121/240) + C2 (20/97/213) + C3 (13/85/159).
    assert {k: len(v) for k, v in appended.items()} == {
        "categories": 0, "sub_themes": 53, "micro_themes": 303, "parents": 612}
    for section in SECTIONS:
        assert all(row["asserted_on"] == MICRO_EXPANSION_ASSERTED_ON
                   for row in appended[section])
        # The block partitions cleanly: frozen rows + expansion-dated rows,
        # nothing in between and nothing undated.
        assert len(appended[section]) + len(_frozen(section)) == len(HIERARCHY[section])


def test_frozen_table_is_unchanged():
    assert len(_frozen("categories")) == 10
    assert len(_frozen("sub_themes")) == 12
    assert len(_frozen("micro_themes")) == 68
    assert len(_frozen("parents")) == 132


def test_materialized_hierarchy_accepts_the_expanded_tier():
    validated = validate_theme_hierarchy(DOC)
    assert {k: len(v) for k, v in validated.items()} == {
        "categories": 10, "sub_themes": 65, "micro_themes": 371, "parents": 744}


def test_no_id_collisions_across_tiers():
    theme_ids = [row["theme_node_id"] for row in DOC["themes"] if row.get("theme_node_id")]
    ids: list[str] = list(theme_ids)
    for section in ("categories", "sub_themes", "micro_themes"):
        ids.extend(row["id"] for row in HIERARCHY[section])
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("section", ["sub_themes", "micro_themes"])
def test_expansion_rows_are_bilingual_with_value_chain_position(section):
    for row in _expansion(section):
        assert isinstance(row["name_en"], str) and row["name_en"].strip(), row["id"]
        assert isinstance(row["name_zh"], str) and row["name_zh"].strip(), row["id"]
        assert row["value_chain_position"] in VALUE_CHAIN_POSITIONS, row["id"]


def test_expansion_nominated_from_points_at_existing_research_record():
    targets = _expansion_research_targets()
    assert targets, "no expansion row carries a nominated_from research pointer"
    for target in sorted(targets):
        assert target.startswith("research:"), target
        path = ROOT / target.removeprefix("research:")
        research_root = (ROOT / "research/theme_graph/micro_expansion_20261021").resolve()
        assert path.resolve().is_relative_to(research_root), target
        assert path.is_file(), target


def test_every_expansion_micro_has_a_parent_row():
    children = {row["child"] for row in _expansion("parents")}
    declared = {row["id"] for section in ("categories", "sub_themes", "micro_themes")
                for row in HIERARCHY[section]}
    declared |= {row["theme_node_id"] for row in DOC["themes"] if row.get("theme_node_id")}
    for row in _expansion("parents"):
        assert row["parent"] in declared, row
        assert row["child"] in declared, row
    for row in _expansion("micro_themes"):
        assert row["id"] in children, f"{row['id']} has no theme->micro parents row"


def test_ratification_receipts_are_present():
    assert RECEIPTS.is_file()
    text = RECEIPTS.read_text(encoding="utf-8")
    assert "ratification receipts" in text.lower()
    assert "display-tier" in text.lower() or "display tier" in text.lower()
