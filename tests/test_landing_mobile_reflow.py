"""Narrow-screen layout contracts; browser evidence verifies the rendered result."""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _media(css: str, width: int) -> str:
    match = re.search(r"@media\s*\(max-width:\s*" + str(width) + r"px\)\s*\{", css)
    assert match, f"Missing existing {width}px responsive block"
    depth, end = 1, match.end()
    while depth and end < len(css):
        depth += (css[end] == "{") - (css[end] == "}")
        end += 1
    return re.sub(r"\s+", "", css[match.end():end - 1])


@pytest.mark.parametrize("surface", ["templates", "site"])
def test_footer_uses_shared_public_two_column_mobile_layout(surface):
    css = (ROOT / surface / "landing.css").read_text()
    mobile = _media(css, 900)
    rule = re.search(r"\.f-cols\{([^}]+)\}", mobile)
    assert rule, "Landing footer must reflow like shared public chrome"
    for declaration in ("display:grid", "width:100%", "grid-template-columns:repeat(2,minmax(0,1fr))"):
        assert declaration in rule.group(1)


@pytest.mark.parametrize("surface", ["templates", "site"])
def test_situation_score_and_timing_can_wrap_without_clipping(surface):
    css = (ROOT / surface / "landing.css").read_text()
    mobile = _media(css, 680)
    assert ".sits{grid-template-columns:minmax(0,1fr)}" in mobile
    assert ".sit{min-width:0}" in mobile
    # Whitespace stripping removes the descendant separator; inspect the source too.
    assert re.search(r"\.sit\s+\.meter\s*\{\s*flex-wrap:\s*wrap", css)
    timing = re.search(r"\.sit\.early\{([^}]+)\}", mobile)
    assert timing and "white-space:normal" in timing.group(1)
    assert "max-width:100%" in timing.group(1)


def test_landing_styles_are_byte_paired():
    assert (ROOT / "templates/landing.css").read_bytes() == (ROOT / "site/landing.css").read_bytes()
