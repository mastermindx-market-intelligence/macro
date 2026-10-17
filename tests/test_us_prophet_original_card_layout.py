"""Regression guard for the October 2026 restoration of compact US Prophet cards."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_us_prophet_workspace_keeps_original_card_geometry():
    """The workspace may fix controls, not replace the shared chart-first card."""
    source = (ROOT / "templates/_prophet_workspace.css.j2").read_text()
    css = re.sub(r"\{#.*?#\}", "", source, flags=re.DOTALL)
    assert "#us-standouts :is(#us-today-grid, #us-cand-grid) .pv-ov" in css
    assert "z-index: 5" in css
    for forbidden in ("grid-template-columns", ".pv-chart", ".pv-bd", ".pv-nm",
                      ".pv-zn", "296px", ".pvcard", "!important"):
        assert forbidden not in css
    assert len(css.encode()) < 1024  # Must remain inline, not a bulky hashed asset.


def test_original_shared_card_remains_chart_first():
    template = (ROOT / "templates/_prophet_card.html.j2").read_text()
    assert "pv-chart" in template
    assert "pv-bd" in template
    assert template.index("pv-chart") < template.index("pv-bd")
    board = (ROOT / "templates/dashboard.html.j2").read_text()
    assert '{% include "_prophet_workspace.css.j2" %}' in board
