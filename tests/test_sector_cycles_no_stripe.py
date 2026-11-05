"""Sector cycle cards carry no accent stripe (#7646 Cycles wave, lane A2_D28).

The Chairman visual rule (docs/DESIGN_DOCTRINE.md) forbids a coloured accent
stripe on any container, on any edge. The shared base rule in site/cycle.css
paints a 3px top stripe through `.cyc-card::before`; on every `.sc-page` host
templates/sector_cycles.css now stops that pseudo-element from being generated.
The phase is still read from the labelled phase chip.

Pure text checks.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "templates" / "sector_cycles.css"

OVERRIDE = ".sc-page .cyc-card::before { content: none; }"
BASE_LINE = ".sc-page .cyc-card::before { background: var(--ph, var(--c)); }"

_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_THIN = re.compile(r"(?<![-\w])(height|width)\s*:\s*([0-9.]+)px")
_KEYED_EDGE = re.compile(r"border-(left|top|right|bottom)(-color)?\s*:[^;]*var\(--(ph|c)\b")


def stripe_problems(css: str) -> list[str]:
    """Every stripe-like rule on a cycle card; empty when the CSS passes."""
    problems = []
    for sel, body in _RULE.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        sel = " ".join(sel.split())
        if ".cyc-card" not in sel:
            continue
        pseudo = "::before" in sel or "::after" in sel
        paints = re.search(r"(?<![-\w])background(-color|-image)?\s*:", body)
        if pseudo and paints:
            thin = [float(v) for _, v in _THIN.findall(body)]
            if any(v <= 6 for v in thin):
                problems.append(f"thin painted pseudo-element: {sel}")
            if "::before" in sel and "content: none" not in body:
                problems.append(f"painted ::before that is still generated: {sel}")
        if _KEYED_EDGE.search(body):
            problems.append(f"single-edge border keyed to the phase/accent hue: {sel}")
    return problems


def test_sector_pages_suppress_the_card_stripe():
    assert OVERRIDE in CSS.read_text(encoding="utf-8")


def test_no_rule_paints_a_stripe_on_a_cycle_card():
    assert stripe_problems(CSS.read_text(encoding="utf-8")) == []


def test_the_base_line_is_gone():
    assert BASE_LINE not in CSS.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "bad",
    [
        BASE_LINE,
        ".cyc-card::before { content: \"\"; height: 3px; background: var(--c); }",
        ".sc-page .cyc-card::after { width: 4px; background: var(--ph); }",
        ".sc-page .cyc-card { border-left: 3px solid var(--ph); }",
    ],
)
def test_the_checker_rejects_a_stripe(bad):
    assert stripe_problems(bad)
