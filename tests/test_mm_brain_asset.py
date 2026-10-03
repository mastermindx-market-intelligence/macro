"""Runtime-shape guard for the shared Brain widget asset (mm_brain.js).

Born from a production outage (2026-08-25, W1-C heal): a design comment INSIDE
the widget's CSS template literal used markdown-style backticks. The first
backtick terminated the template literal, the following ``.on`` became a
property access on the giant CSS string, and the next backtick re-opened a
template — turning the tail into a tagged-template CALL of a string:
``TypeError: "…" is not a function`` at load, on every page, with `node
--check` and the whole CI suite green (the defect is syntactically valid).

This test is dependency-free and pins the exact failure class: the widget's
CSS template literal may never contain an interior backtick, and the span it
closes must still contain the late-stylesheet composer rules (so an early
termination is named even if the interior backtick itself moved).
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPIES = [ROOT / "templates" / "mm_brain.js", ROOT / "site" / "mm_brain.js"]


def _css_template_span(text: str) -> tuple[int, int]:
    """Return (open_index, close_index) of the `var CSS = <backtick>` literal."""
    marker = "var CSS = `"
    start = text.index(marker) + len(marker) - 1
    close = text.index("`", start + 1)
    return start, close


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_css_template_literal_has_no_interior_backtick(path: pathlib.Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} absent (sparse checkout)")
    text = path.read_text(encoding="utf-8")
    start, close = _css_template_span(text)
    body = text[start + 1 : close]
    line_of_close = text[:close].count("\n") + 1
    # The first backtick after the opener must terminate the WHOLE stylesheet:
    # the "explain this panel" affordance rules (.mmb-exp) are the final block
    # of the sheet, so if the span ends before them, an interior backtick split
    # the template and the tail becomes a tagged-template call of a string at
    # page load.
    assert ".mmb-exp" in body, (
        "CSS template literal of mm_brain.js terminated early at line "
        f"{line_of_close} — an interior backtick splits the stylesheet and "
        "the widget crashes at load (string-is-not-a-function outage, "
        "2026-08-25). Use quotes, never backticks, in comments inside the "
        "template."
    )


# The Chairman removed the entire composer notice on 2026-09-21.
# DEC:BRAIN-COMPOSER-NO-RESEARCH-NOTICE supersedes only the old F11 composer
# placement. Research routing, billing, and answer-level boundaries stay intact.

def _read(path: pathlib.Path) -> str:
    if not path.exists():
        pytest.skip(f"{path} absent (sparse checkout)")
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_composer_has_no_research_notice_or_empty_row(path: pathlib.Path) -> None:
    text = _read(path)
    for removed in (
        "mmb-rrow", "mmb-rpill", "mmb-rtext", "mmb-rcost", "mmb-rtip",
        "RESEARCH_CEILING", 'data-act="research"',
        "This is a reading of what we already published.",
        "Runs on Pro", "\u8fd9\u662f\u5bf9\u6211\u4eec\u5df2\u7ecf\u53d1\u5e03\u5185\u5bb9\u7684\u89e3\u8bfb",
        "\u6d88\u8017\u4e00\u6761 Pro \u6d88\u606f",
    ):
        assert removed not in text, f"Removed composer notice returned: {removed}"


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_removed_notice_has_no_dangling_dom_updates(path: pathlib.Path) -> None:
    text = _read(path)
    assert "researchBtn" not in text
    assert "paintResearch" not in text


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_fast_pro_depth_controls_and_quota_remain(path: pathlib.Path) -> None:
    text = _read(path)
    start = text.index('id="mmb-lane"')
    group = text[start:text.index("</div>", start)]
    assert re.findall(r'data-lane="([^"]+)"', group) == ["fast", "pro"]
    assert 'role="group"' in group and 'aria-pressed="true"' in group
    assert "#mmb-lane button[data-lane]" in text
    assert "quotas[researchMode ? 'pro' : lane]" in text


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_research_still_uses_existing_explicit_slash_and_pro_lane(path: pathlib.Path) -> None:
    text = _read(path)
    assert "{ key: 'research'," in text
    assert "if (proEligible) { if (!researchMode) setResearch(true);" in text
    assert "lane: researchMode ? 'pro' : lane" in text
    assert "mode: researchMode ? 'research' : 'chat'" in text
    assert "if (lane === 'fast' && researchMode) researchMode = false;" in text
    assert "JSON.stringify({ lane: lane })" in text


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_explain_panel_affordance_is_touch_and_keyboard_reachable(
    path: pathlib.Path,
) -> None:
    """Panel explain control must not depend on mouse hover to become usable."""
    if not path.exists():
        pytest.skip(f"{path} absent (sparse checkout)")
    text = path.read_text(encoding="utf-8")
    start, close = _css_template_span(text)
    css = text[start + 1 : close]

    assert ".mmb-exp{position:absolute;top:6px;right:6px;width:40px;height:40px" in css
    assert "touch-action:manipulation" in css
    assert "html[data-theme=\"light\"] .mmb-exp{" in css
    assert (
        ".sx:hover .mmb-exp,.sx:focus-within .mmb-exp,"
        ".mmb-exp:focus-visible{opacity:1;pointer-events:auto}"
    ) in css
    assert ".mmb-exp:focus-visible{outline:2px solid" in css
    assert "@media (hover:none),(pointer:coarse){.mmb-exp{opacity:1;pointer-events:auto}}" in css
    assert "@media(prefers-reduced-motion:reduce){.mmb-exp{transition:none}}" in css
    assert "btn.title = L('Ask the Brain', '询问 Mastermind AI');" in text
    assert "btn.setAttribute('aria-label', btn.title);" in text


def test_mm_brain_template_and_site_copy_stay_identical() -> None:
    if not all(path.exists() for path in COPIES):
        pytest.skip("paired asset absent (sparse checkout)")
    assert COPIES[0].read_bytes() == COPIES[1].read_bytes()
