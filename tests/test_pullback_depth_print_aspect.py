"""Print layout and drawdown-chart aspect for the pullback section.

The chart SVG is preserveAspectRatio=none inside a fixed viewBox. The fragment
must pin the figure to that viewBox (width / height) so a dialog resize does
not stretch the line. Print must open the closed price-history disclosure and
drop the dialog panel's scroll clip, without hiding the forecast, the settled-
close receipt (.rrp-stamp), or the expiry notice.
"""
from __future__ import annotations

import re
from pathlib import Path

from lib.illus import illus

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "templates" / "_risk_radar_pullback_depth.css.j2"
DASHBOARD = ROOT / "templates" / "dashboard.html.j2"
CHINA = ROOT / "templates" / "china.html.j2"

# The settled-close / valid-until line is the observation receipt.
_RECEIPT = ".rrp-stamp"
_NEVER_HIDE = (".rrp-forecast", _RECEIPT, ".pbx-expiry")


def _css(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _blocks(css: str, at_rule: str) -> list[str]:
    """Bodies of top-level at-rules whose prelude matches at_rule."""
    bodies = []
    for match in re.finditer(at_rule, css):
        brace = css.find("{", match.end())
        if brace < 0:
            continue
        depth, i = 1, brace + 1
        while i < len(css) and depth:
            depth += (css[i] == "{") - (css[i] == "}")
            i += 1
        if depth == 0:
            bodies.append(css[brace + 1:i - 1])
    return bodies


def _rules(block: str) -> list[tuple[str, str]]:
    rules = []
    i, n = 0, len(block)
    while i < n:
        brace = block.find("{", i)
        if brace < 0:
            break
        head = block[i:brace].strip()
        depth, end = 1, brace + 1
        while end < n and depth:
            depth += (block[end] == "{") - (block[end] == "}")
            end += 1
        body = block[brace + 1:end - 1 if depth == 0 else end]
        if head.startswith("@"):
            rules.extend(_rules(body))
        elif head:
            rules.append((head, body))
        i = end
    return rules


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _drawdown_viewbox() -> tuple[int, int]:
    """Same kind and height the presenter passes to illus.illus."""
    html = illus(
        {
            "dates": ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
            "vals": [0.0, -1.2, -3.4, -2.1, -4.0],
        },
        kind="drawdown",
        height=188,
        accent="var(--down)",
        reference=0,
    )
    match = re.search(r'viewBox="0 0 (\d+) (\d+)"', html)
    assert match, "drawdown fragment did not emit a viewBox"
    return int(match.group(1)), int(match.group(2))


def test_chart_rule_matches_the_drawdown_viewbox():
    css = _css(FRAGMENT)
    match = re.search(r"\.rrp \.rrp-chart \.ilx\{([^}]*)\}", css)
    assert match, "missing .rrp .rrp-chart .ilx rule"
    body = _compact(match.group(1))
    for kept in (
        "width:100%",
        "background:transparent",
        "border:0",
        "border-radius:0",
        "box-shadow:none",
        "margin:0",
        "height:auto",
    ):
        assert kept in body, f"chart rule dropped {kept}"
    width, height = _drawdown_viewbox()
    assert f"aspect-ratio:{width}/{height}" in body
    assert width / height == 560 / 188
    svg = re.search(
        r"\.rrp \.rrp-chart \.ilx svg\{([^}]*)\}",
        css,
    )
    assert svg, "missing .rrp .rrp-chart .ilx svg rule"
    assert _compact(svg.group(1)) == "display:block;width:100%;height:100%"
    presenter = (ROOT / "lib" / "pullback_depth.py").read_text(encoding="utf-8")
    assert 'kind="drawdown"' in presenter and "height=188" in presenter


def test_fragment_print_block_is_scoped_and_keeps_the_receipt():
    blocks = _blocks(_css(FRAGMENT), r"@media\s+print\b")
    assert len(blocks) == 1, f"expected one @media print block, found {len(blocks)}"
    block = blocks[0]
    assert "::details-content" in block
    assert "content-visibility:visible" in _compact(block)
    rules = _rules(block)
    assert rules, "print block has no rules"
    for selectors, body in rules:
        for selector in (part.strip() for part in selectors.split(",")):
            assert selector.startswith(".rrp"), f"unscoped print selector: {selector!r}"
        compact = _compact(body).lower()
        if "display:none" in compact:
            for banned in _NEVER_HIDE:
                assert banned not in selectors, (
                    f"print sets display:none on {banned}"
                )
            assert "summary" not in selectors, "print hides the history summary"


def test_host_print_blocks_release_the_dialog_panel():
    expectations = (
        (DASHBOARD, ".mx5-dlg-panel"),
        (CHINA, ".cnx-dlg-panel"),
    )
    for path, panel in expectations:
        blocks = _blocks(_css(path), r"@media\s+print\b")
        matched = [
            block for block in blocks
            if panel in block and "max-height:none" in _compact(block)
            and "overflow:visible" in _compact(block)
        ]
        assert matched, f"{path.name} print block does not release {panel} max-height/overflow"
