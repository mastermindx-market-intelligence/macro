"""Regression guard for compact fallback controls alongside the rich Prophet cards."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_fallback_keeps_original_card_geometry():
    """Rich-card composition must not re-enlarge or intercept legacy cards."""
    source = (ROOT / "templates/_prophet_workspace.css.j2").read_text()
    legacy = source.split("/* Legacy compact cards retain their original interactive overlays. */", 1)[1]
    css = re.sub(r"\{#.*?#\}", "", legacy, flags=re.DOTALL)
    assert ".pvcard:not(.po-card) .pv-ov" in css
    assert "z-index: 5" in css
    for forbidden in ("grid-template-columns", ".pv-chart", ".pv-bd", ".pv-nm",
                      ".pv-zn", "296px", "!important"):
        assert forbidden not in css
    assert len(css.encode()) < 1024
    for selectors, _ in re.findall(r"([^{}]+)\{([^}]+)\}", css):
        for selector in selectors.split(",\n"):
            assert ".pvcard:not(.po-card)" in selector


def test_original_shared_card_remains_chart_first():
    template = (ROOT / "templates/_prophet_card.html.j2").read_text()
    assert "pv-chart" in template
    assert "pv-bd" in template
    assert template.index("pv-chart") < template.index("pv-bd")
    board = (ROOT / "templates/dashboard.html.j2").read_text()
    assert '{% include "_prophet_workspace.css.j2" %}' in board


def test_passive_overlay_keeps_stock_link_clickable():
    css = (ROOT / "templates/_prophet_workspace.css.j2").read_text()
    rule = re.search(r"\.pvcard:not\(\.po-card\) \.pv-ov\s*\{([^}]+)\}", css).group(1)
    assert "pointer-events: none" in rule


def test_real_overlay_controls_remain_interactive():
    css = (ROOT / "templates/_prophet_workspace.css.j2").read_text()
    rules = re.findall(r"([^{}]+)\{([^}]+)\}", re.sub(r"\{#.*?#\}", "", css, flags=re.DOTALL))
    for selector in (".pv-cau", ".pv-trg", ".pv-live:not([hidden])"):
        assert any(selector in selectors and "pointer-events: auto" in body
                   for selectors, body in rules), selector


def test_compact_card_suite_is_registered_with_existing_prophet_ci_owner():
    source = (ROOT / ".github/ci/legacy-jobs.yml").read_text()
    job = re.search(r"(?ms)^  washout-turn-organ:\n.*?(?=^  [\w-]+:|\Z)", source).group()
    suite = "tests/test_us_prophet_original_card_layout.py"
    assert f'- "{suite}"' in job
    step = re.search(r"(?m)^        run: python -m pytest tests/test_prophet_card_shared\.py.*$", job).group()
    assert suite in step
