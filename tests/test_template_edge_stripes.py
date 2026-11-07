"""tests/test_template_edge_stripes.py — no colored container-edge stripe in the
page templates migrated family by family after the dashboard stripe sweep.

Chairman design rule 2026-10-18 (docs/DESIGN_DOCTRINE.md §3): no colored left
border, inset stripe, pseudo-element rail or equivalent edge accent on cards,
panels, callouts, rows, navigation selections or banners — and never move the
stripe to another edge. Identity rides the icon, the name ink and labeled
semantic text. Chart series, data marks, neutral dividers and complete focus
outlines keep their distinct jobs.

Companion to tests/test_container_edge_stripes.py (dashboard / theme.css /
intraday_flow, which still pins a shrink-only legacy rail list). This file has
no legacy pin: a template family joins ``FILES`` only once it is clean. It also
catches three shapes that file does not look for — an IN-FLOW pseudo bar (a
``display:block`` ``::before`` strip that pushes the content down), a
``currentColor`` edge, and a stripe written in an inline ``style=""`` attribute.
Fold the two files into one once both guards are on main.

  GUARD 1 — pseudo-element bars: an absolutely positioned ``::before`` /
  ``::after`` drawing a <=5px bar along a full container edge, or an in-flow
  one (<=5px tall and full width, or <=5px wide and full height) painted in a
  colored background.

  GUARD 2 — inset box-shadow stripes: ``inset 3px 0 0 <color>`` style shadows
  (one axis offset, no blur) that paint a single edge of a cell or card, in a
  rule or an inline style.

  GUARD 3 — colored single-edge borders (left/top/right and their logical
  forms) in a rule or an inline style. ``currentColor`` and a Jinja expression
  count as colored: the rendered value is a state ink either way.

Browser-free: plain regex over the template bytes. LOAD CLOSURE: the template
files named in ``FILES`` via ``Path.read_text``. Nothing else.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHINA = "templates/china.html.j2"
FILES = (CHINA,)
SRC = {name: (ROOT / name).read_text(encoding="utf-8") for name in FILES}

_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
# Inline style attributes; Jinja ``{{ }}`` inside the value is kept whole.
_STYLE_ATTR_RE = re.compile(r"""\sstyle\s*=\s*(?:"((?:[^"{]|\{\{.*?\}\}|\{(?!\{))*)"|'((?:[^'{]|\{\{.*?\}\}|\{(?!\{))*)')""")


def _rules(name: str):
    """Yield (selector, body) for every innermost ``sel { body }`` block."""
    for m in _RULE_RE.finditer(SRC[name]):
        selector = " ".join(m.group(1).strip().splitlines()[-1].split()) if m.group(1).strip() else ""
        yield selector, m.group(2)


def _inline_styles(name: str):
    """Yield (line-number label, style value) for every inline style attribute."""
    src = SRC[name]
    for m in _STYLE_ATTR_RE.finditer(src):
        yield f"line {src.count(chr(10), 0, m.start()) + 1}", m.group(1) or m.group(2) or ""


def _decl(body: str, prop: str) -> str | None:
    m = re.search(r"(?<![-\w])%s\s*:\s*([^;]+)" % re.escape(prop), body)
    return m.group(1).strip() if m else None


# Tokens that are neutral surface/ink, not semantic color.
_NEUTRAL_VARS = {"line", "hair", "hair-strong", "glass-line", "rule", "text",
                 "ink-1", "ink-2", "ink-3", "panel", "panel2", "bg", "tile", "mx5-glass-border"}


def _chromatic(r: int, g: int, b: int) -> bool:
    return max(r, g, b) - min(r, g, b) > 24


def _is_colored(value: str) -> bool:
    if "{{" in value or re.search(r"currentcolor", value, re.I):
        return True
    if any(v not in _NEUTRAL_VARS for v in re.findall(r"var\(\s*--([\w-]+)", value)):
        return True
    for h in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", value):
        h = h if len(h) == 6 else "".join(c * 2 for c in h)
        if _chromatic(*(int(h[i:i + 2], 16) for i in (0, 2, 4))):
            return True
    for r, g, b in re.findall(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)", value):
        if _chromatic(int(r), int(g), int(b)):
            return True
    return False


# --------------------------------------------------------------------------- #
# GUARD 1 — pseudo-element bars
# --------------------------------------------------------------------------- #

def _is_zero(v: str | None) -> bool:
    return v is not None and v in {"0", "0px"}


def _px(v: str | None) -> float | None:
    m = re.fullmatch(r"([0-9.]+)px", v or "")
    return float(m.group(1)) if m else None


def _edges(body: str) -> dict[str, str | None]:
    edges = {k: _decl(body, k) for k in ("top", "right", "bottom", "left")}
    inset = (_decl(body, "inset") or "").split()
    if inset:
        # CSS shorthand: 1 → all, 2 → (block, inline), 3 → (top, inline, bottom), 4 → t r b l
        t, r, b, l = {1: inset * 4, 2: inset * 2, 3: inset + inset[1:2]}.get(len(inset), inset)[:4]
        for k, v in zip(("top", "right", "bottom", "left"), (t, r, b, l)):
            edges[k] = edges[k] or v
    return edges


def _is_absolute_edge_bar(body: str) -> bool:
    if not re.search(r"position\s*:\s*absolute", body):
        return False
    e = _edges(body)
    w, h = _px(_decl(body, "width")), _px(_decl(body, "height"))
    vertical = (w is not None and w <= 5 and _is_zero(e["top"]) and _is_zero(e["bottom"])
                and (_is_zero(e["left"]) or _is_zero(e["right"])))
    horizontal = (h is not None and h <= 5 and _is_zero(e["left"]) and _is_zero(e["right"])
                  and (_is_zero(e["top"]) or _is_zero(e["bottom"])))
    return vertical or horizontal


def _is_in_flow_bar(body: str) -> bool:
    if re.search(r"position\s*:\s*(?:absolute|fixed)", body):
        return False
    paint = _decl(body, "background") or _decl(body, "background-color") or _decl(body, "background-image")
    if not paint or not _is_colored(paint):
        return False
    w, h = _decl(body, "width"), _decl(body, "height")
    full = {None, "100%", "auto"}
    strip = _px(h) is not None and _px(h) <= 5 and w in full
    rail = _px(w) is not None and _px(w) <= 5 and (h == "100%" or re.search(r"align-self\s*:\s*stretch", body))
    return bool(strip or rail)


@pytest.mark.parametrize("name", FILES)
def test_guard1_no_pseudo_element_edge_bar(name):
    hits = [sel for sel, body in _rules(name)
            if re.search(r"::?(?:before|after)\b", sel)
            and (_is_absolute_edge_bar(body) or _is_in_flow_bar(body))]
    assert not hits, f"{name}: pseudo-element edge stripe(s) — remove, identity rides the label ink: {hits}"


# --------------------------------------------------------------------------- #
# GUARD 2 — inset box-shadow stripes
# --------------------------------------------------------------------------- #

# inset <x> <y> <blur>: a stripe is exactly one non-zero axis offset, no blur.
_INSET_RE = re.compile(r"\binset\s+(-?[0-9.]+)(?:px)?\s+(-?[0-9.]+)(?:px)?\s+(-?[0-9.]+)(?:px)?")


def _inset_stripes(body: str) -> list[str]:
    out = []
    for decl in re.findall(r"box-shadow\s*:\s*([^;]+)", body):
        for m in _INSET_RE.finditer(decl):
            x, y, blur = (abs(float(g)) for g in m.groups())
            if blur == 0 and (x == 0) != (y == 0) and max(x, y) >= 2:
                out.append(m.group(0))
    return out


@pytest.mark.parametrize("name", FILES)
def test_guard2_no_inset_shadow_stripe(name):
    hits = [(sel, s) for sel, body in _rules(name) for s in _inset_stripes(body)]
    hits += [(where, s) for where, style in _inline_styles(name) for s in _inset_stripes(style)]
    assert not hits, f"{name}: inset-shadow edge stripe(s): {hits}"


# --------------------------------------------------------------------------- #
# GUARD 3 — colored single-edge borders
# --------------------------------------------------------------------------- #

_EDGE_DECL_RE = re.compile(
    r"(?<![-\w])(border-(?:top|left|right|inline-start|inline-end|block-start)(?:-color)?)\s*:\s*([^;]+)")


def _colored_edges(body: str) -> list[str]:
    return [m.group(1) for m in _EDGE_DECL_RE.finditer(body) if _is_colored(m.group(2))]


@pytest.mark.parametrize("name", FILES)
def test_guard3_no_colored_single_edge_border(name):
    hits = [(sel, e) for sel, body in _rules(name) for e in _colored_edges(body)]
    hits += [(where, e) for where, style in _inline_styles(name) for e in _colored_edges(style)]
    assert not hits, (f"{name}: colored single-edge border(s) — use an even neutral border "
                      f"and a labeled state instead: {hits}")


# --------------------------------------------------------------------------- #
# The detectors themselves: each shape this file retired must still be caught.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("body, caught", [
    # china .nbcard::before — in-flow 3px gradient strip above the card body
    ('content:""; display:block; flex:none; height:3px; background:linear-gradient(90deg,var(--up),transparent)', True),
    # absolute 3px top bar (hk/canada card idiom)
    ("content:''; position:absolute; top:0; left:0; right:0; height:3px; background:var(--up)", True),
    # neutral 1px in-flow hairline stays legal
    ('content:""; display:block; height:1px; background:var(--line)', False),
    # a 4px dot is a data mark, not a strip
    ("content:''; display:inline-block; width:4px; height:4px; border-radius:50%; background:var(--up)", False),
])
def test_guard1_detector_shapes(body, caught):
    assert (_is_absolute_edge_bar(body) or _is_in_flow_bar(body)) is caught


@pytest.mark.parametrize("body, caught", [
    ("border-top:2px solid currentColor", True),
    ("border-left:3px solid {{ _rs_col }}", True),
    ("border-top-color:var(--warn)", True),
    ("border-left:3px solid rgb(220, 60, 60)", True),
    ("border-top:1px solid var(--line)", False),
    ("border-left:1px solid #2a2a2a", False),
])
def test_guard3_detector_shapes(body, caught):
    assert bool(_colored_edges(body)) is caught


def test_inline_style_reader_keeps_jinja_values_whole():
    SRC["<probe>"] = ('<div style="padding:7px 11px;border-left:3px solid {{ _rs_col }};'
                      'background:color-mix(in srgb,{{ _rs_col }} 6%,var(--panel))">')
    try:
        (where, style), = _inline_styles("<probe>")
    finally:
        del SRC["<probe>"]
    assert where == "line 1" and _colored_edges(style) == ["border-left"]
