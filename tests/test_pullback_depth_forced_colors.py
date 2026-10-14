"""Forced-colors block for the measured pullback section (Windows High Contrast)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "templates/_risk_radar_pullback_depth.css.j2"

SYSTEM_COLORS = ("CanvasText", "Canvas", "Highlight", "LinkText", "GrayText", "Mark")

# Classes found inside .rrp whose meaning is carried by a CSS-variable stroke/fill,
# a background/box-shadow, or an outline that forced-colors strips.
COVERED_CLASSES = {
    # Chart geometry: illus.css paints these from var(--down)/var(--muted)/currentColor.
    "ilx-path": "chart line stroke is currentColor / a CSS variable",
    "ilx-down": "drawdown path stroke is var(--down)",
    "ilx-dot": "end-of-series marker fill is currentColor / a CSS variable",
    "ilx-dot-down": "end marker fill is var(--down) (current/low settle point)",
    "ilx-ref": "reference (0%) hairline stroke is var(--muted)",
    "ilx-water": "peak/0% waterline stroke is var(--muted)",
    "ilx-water-top": "peak hairline stroke is var(--down)",
    # A system-colour fill under the line would sit the CanvasText stroke on a Mark
    # block, so the gradient veil is dropped rather than recoloured.
    "ilx-area": "under-curve fill is a var(--down) gradient",
    "ilx-tag": "end-value chip background/border come from color-mix of CSS variables",
    # Metrics: figure colour is the only down/up cue besides the digits.
    "rrp-primary": "current-drawdown figure colour is var(--ink-down)",
    "rrp-rebound": "rebound figure colour is var(--ink-up)",
    "rrp-metrics": "metric column figures use CSS-variable ink",
    # Phase trail reads as chips of muted text; colour is the only chrome.
    "rrp-phase-trail": "phase chips are muted-coloured list items, no other marker",
    # Signal rows sit next to the chart end-dot; both use variable colour.
    "rrp-signals": "signal labels use var(--muted); the chart settle marker is the dot",
    # Focus ring uses a CSS-variable outline that forced-colors remaps away from Highlight.
    "rrp-method": "disclosure focus ring is outline: var(--ink-info)",
    # Expiry notice colour is var(--ink-warn); keep it a distinct status in HC.
    "pbx-expiry": "expiry notice colour is var(--ink-warn)",
}

COLOR_PROPS = {
    "color", "fill", "stroke", "background", "background-color",
    "border", "border-color", "border-top-color", "border-right-color",
    "border-bottom-color", "border-left-color", "border-inline-start",
    "border-inline-start-color", "border-inline-end", "outline", "outline-color",
    "box-shadow", "stop-color",
}
NON_COLOR_TOKENS = {
    "none", "solid", "dashed", "dotted", "double", "hidden", "auto",
    "transparent", "currentcolor", "inherit", "initial", "unset",
    "px", "em", "rem", "ch", "ex",
}


def _css() -> str:
    return CSS_PATH.read_text()


def _forced_block(css: str) -> str:
    match = re.search(r"@media\s*\(\s*forced-colors\s*:\s*active\s*\)\s*\{", css)
    assert match, "missing @media (forced-colors: active) block"
    start = match.end()
    depth = 1
    i = start
    while i < len(css) and depth:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    assert depth == 0, "unbalanced forced-colors block"
    return css[start:i - 1]


def _rules(block: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", block):
        out.append((m.group(1).strip(), m.group(2)))
    return out


def test_forced_colors_block_exists_and_is_scoped_to_rrp():
    block = _forced_block(_css())
    assert block.strip(), "forced-colors block is empty"
    rules = _rules(block)
    assert rules, "forced-colors block has no rules"
    for selectors, _body in rules:
        for sel in selectors.split(","):
            sel = sel.strip()
            assert sel.startswith(".rrp"), f"selector is not scoped under .rrp: {sel!r}"


def test_forced_colors_block_uses_only_system_colour_keywords():
    block = _forced_block(_css())
    assert "#" not in block
    assert "var(" not in block
    assert "rgb(" not in block and "hsl(" not in block
    assert "color-mix(" not in block
    for selectors, body in _rules(block):
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            prop, value = decl.split(":", 1)
            prop = prop.strip().lower()
            if prop not in COLOR_PROPS:
                continue
            for tok in re.findall(r"[A-Za-z][A-Za-z0-9-]*", value):
                if tok.lower() in NON_COLOR_TOKENS:
                    continue
                assert tok in SYSTEM_COLORS, (
                    f"{selectors!r} {prop}: unexpected colour {tok!r}"
                )


def test_forced_colors_block_covers_measured_section_classes():
    block = _forced_block(_css())
    missing = [cls for cls in COVERED_CLASSES if cls not in block]
    assert not missing, f"forced-colors block missing classes {missing}"
    compact = re.sub(r"\s+", "", block)
    assert re.search(r"outline:2px\s*solid\s*Highlight", block)
    assert "forced-color-adjust:none" in compact


def test_forced_colors_drops_the_under_curve_fill():
    block = re.sub(r"\s+", "", _forced_block(_css()))
    assert ".ilx-area{fill:none;" in block
