"""Subsector detail ZH "setup" wording (#7646 Cycles wave, lane A2_D36).

On a no-sizing surface the Chinese for a chart setup is 形态, the deck's own
rendering (copy_deck.json brief.lane_sub_get_ready), never 配置, which reads
as an allocation or position configuration.

Pure text checks; no node.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SUBSECTOR = ROOT / "templates" / "subsector_detail.html.j2"
DECK = ROOT / "design_refs" / "sector-paper-20261021" / "copy_deck.json"

REQUIRED = ("T1 · 已确认形态", "T2 · 早期形态", "L('Own setup','自身形态')")
FORBIDDEN = "配置"


def setup_zh_problems(text: str) -> list[str]:
    """Every reason the text fails the setup wording rule; empty when it passes."""
    problems = [f"missing {s!r}" for s in REQUIRED if s not in text]
    if FORBIDDEN in text:
        problems.append(f"{FORBIDDEN!r} appears {text.count(FORBIDDEN)} time(s)")
    return problems


def test_subsector_template_uses_the_deck_word_for_setup():
    text = SUBSECTOR.read_text(encoding="utf-8")
    for s in REQUIRED:
        assert s in text, s


def test_subsector_template_has_no_allocation_word():
    assert FORBIDDEN not in SUBSECTOR.read_text(encoding="utf-8")


def test_deck_renders_setup_as_xingtai():
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    row = deck["brief"]["lane_sub_get_ready"]
    assert row["en"].startswith("Setup")
    assert "形态" in row["zh"]
    assert FORBIDDEN not in row["zh"]


def test_subsector_template_passes_the_rule():
    assert setup_zh_problems(SUBSECTOR.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "old",
    [
        "const zh = {T1:'T1 · 已确认配置',T2:'T2 · 早期配置',T3:'T3 · 形成中'};",
        "L('Own setup','自身配置')",
    ],
)
def test_the_rule_rejects_the_base_strings(old):
    text = SUBSECTOR.read_text(encoding="utf-8") + "\n" + old
    assert any(FORBIDDEN in p for p in setup_zh_problems(text))
    assert setup_zh_problems(old)
