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


# --- L6.5: the rule covers every container on the Cycles pages, not only the cards ----
# The L6.4 capture's stripe audit flagged three containers that the card-only check could
# not see: the turns/legs rows (.sc-leg), the projected-turn box (.sc-fcast) and the DNA
# group (.sc-dna); the shared .cyc-fhead edge is suppressed on .sc-page hosts.
WAVE_CSS = sorted((ROOT / "templates").glob("sector_cycles*.css"))
FHEAD_OVERRIDE = ".sc-page .cyc-fhead { border-left: 0; padding-left: 0; }"

_EDGE = re.compile(r"border-(left|top|right|bottom)\s*:\s*([^;]*)")
_EDGE_COLOR = re.compile(r"border-(left|top|right|bottom)-color\s*:")


def edge_stripes(css: str) -> list[str]:
    """Single-edge borders of 2px or more in a visible colour, on any selector.

    Two shapes are marks, not containers, and are allowed: a CSS triangle (another edge
    of the same rule is transparent) and a zero-width needle (`width: 0`).
    """
    problems = []
    for sel, body in _RULE.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        sel = " ".join(sel.split())
        edges = _EDGE.findall(body)
        glyph = any("transparent" in v for _, v in edges) or re.search(r"(?<![-\w])width\s*:\s*0(px)?\s*(;|$)", body)
        if _EDGE_COLOR.search(body) and not glyph:
            problems.append(f"edge colour override: {sel}")
        for side, val in edges:
            m = re.match(r"\s*([0-9.]+)px", val)
            if not m or float(m.group(1)) < 2 or "transparent" in val or glyph:
                continue
            problems.append(f"{side} {m.group(1)}px edge: {sel}")
    return problems


@pytest.mark.parametrize("css", WAVE_CSS, ids=lambda p: p.name)
def test_no_wave_stylesheet_paints_an_edge_stripe(css):
    assert edge_stripes(css.read_text(encoding="utf-8")) == []


def test_the_shared_focus_head_edge_is_suppressed():
    assert FHEAD_OVERRIDE in CSS.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "bad",
    [
        ".sc-leg { border: 1px solid var(--line); border-left: 3px solid var(--lc, var(--muted)); }",
        ".sc-fcast.pk { border-left-color: var(--down); }",
        ".sc-dna { border-left: 3px solid color-mix(in srgb, var(--link) 55%, var(--line)); }",
        ".x { border-top: 2px solid var(--warn); }",
    ],
)
def test_the_edge_checker_rejects_a_stripe(bad):
    assert edge_stripes(bad)


@pytest.mark.parametrize(
    "ok",
    [
        ".cyc-legend .lm-pk { border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 7px solid var(--warn); }",
        ".sc-sig-bar i { display: block; height: 100%; width: 0; border-right: 2px solid var(--text); }",
        ".scf .scf-sec { border-top: 1px solid var(--line); }",
        ".sc-page .cyc-fhead { border-left: 0; padding-left: 0; }",
    ],
)
def test_the_edge_checker_allows_marks_and_hairlines(ok):
    assert edge_stripes(ok) == []


def test_the_dossier_verdict_box_keeps_its_even_hairline():
    """theme.css gives .verdict a left accent; the dossier overrides it with an even border."""
    assert ".verdict { border:1px solid var(--line); }" in (ROOT / "templates" / "sector.html.j2").read_text(encoding="utf-8")


def test_the_act_now_lane_head_stripe_is_suppressed():
    """theme.css paints a bar before .anv2-lane-hd; the China act-now board removes it."""
    board = (ROOT / "templates" / "_china_act_now_board.html.j2").read_text(encoding="utf-8")
    assert ".anv2-lane-hd::before { content: none; }" in board
