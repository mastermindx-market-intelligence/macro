"""All Tools shared-header integration contracts.

These tests execute the production controller bytes embedded in nav_market.js.
They do not claim browser, visual, accessibility, or production acceptance.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
NAV_JS = TEMPLATES / "nav_market.js"
NAV_CSS = TEMPLATES / "navigation-refresh.css"
SITE_NAV = TEMPLATES / "_site_nav.html.j2"
HOST = TEMPLATES / "_all_tools_menu.html.j2"
ADOPTION_TESTS = ROOT / "research" / "market_os" / "all_tools_adoption" / "tests"
JS_START = "/* ALL_TOOLS_CONTROLLER_V1_START */"
JS_END = "/* ALL_TOOLS_CONTROLLER_V1_END */"
CSS_START = "/* ALL_TOOLS_MATERIAL_V1_START */"
CSS_END = "/* ALL_TOOLS_MATERIAL_V1_END */"


def _between(text: str, start: str, end: str) -> str:
    assert text.count(start) == 1, f"expected one {start}"
    assert text.count(end) == 1, f"expected one {end}"
    left = text.index(start) + len(start)
    right = text.index(end, left)
    return text[left:right].strip() + "\n"


def _render_site_nav(enabled: object = False) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False)
    env.globals["t"] = lambda en, zh="": en
    return env.get_template("_site_nav.html.j2").render(
        all_tools_enabled=enabled,
        nav_prefix="",
    )


def test_production_controller_is_owned_by_nav_market() -> None:
    source = NAV_JS.read_text()
    block = _between(source, JS_START, JS_END)
    assert "var PILOT = ['/macro.html', '/sector_central.html', '/reports.html'];" in block
    assert "data-mmx-all-tools" in block
    assert "createElement('style')" not in block
    for forbidden in ("localStorage", "sessionStorage", "fetch(", "XMLHttpRequest"):
        assert forbidden not in block


def test_documentary_reference_matches_production_controller() -> None:
    """A reference-only edit must not silently fork the shared navigation owner."""
    reference = ADOPTION_TESTS.parent / "src" / "all-tools.js"
    production = _between(NAV_JS.read_text(), JS_START, JS_END)
    assert reference.read_text() == production, (
        "The All tools reference is stale; sync the exact nav_market controller block."
    )


def test_production_controller_passes_source_driven_behavior_suite(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable")
    controller = tmp_path / "all-tools-production.cjs"
    controller.write_text(_between(NAV_JS.read_text(), JS_START, JS_END))
    tests = [
        ADOPTION_TESTS / "navigation.test.cjs",
        ADOPTION_TESTS / "controller.test.cjs",
        ADOPTION_TESTS / "refresh-boundaries.test.cjs",
    ]
    proc = subprocess.run(
        [node, "--test", *(str(p) for p in tests)],
        cwd=str(ADOPTION_TESTS),
        env={**os.environ, "ALL_TOOLS_SOURCE": str(controller)},
        text=True,
        capture_output=True,
        timeout=40,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_material_is_owned_by_navigation_refresh() -> None:
    block = _between(NAV_CSS.read_text(), CSS_START, CSS_END)
    assert ".mmx-tools" in block
    assert 'html[data-theme="light"] .mmx-tools-aside' in block
    assert "@media (max-width:600px)" in block
    assert "prefers-reduced-motion" in block
    assert "forced-colors:active" in block
    assert ":root" not in block
    assert not re.search(r"#[0-9a-fA-F]{3,8}\\b", block)


def test_footer_is_isolated_from_host_page_footer_rules() -> None:
    """Generic page-level ``footer`` rules must not shrink or offset the dialog footer."""
    block = _between(NAV_CSS.read_text(), CSS_START, CSS_END)
    match = re.search(r"\.mmx-tools-footer\s*\{([^}]*)\}", block)
    assert match, "missing .mmx-tools-footer rule"
    declarations = match.group(1)
    assert "width: 100%" in declarations
    assert "max-width: none" in declarations
    assert "margin: 0" in declarations


def test_shared_header_mount_is_default_off_and_single() -> None:
    source = SITE_NAV.read_text()
    assert source.count('{% include "_all_tools_menu.html.j2" %}') == 1
    off = _render_site_nav(False)
    on = _render_site_nav(True)
    assert "data-mmx-all-tools" not in off
    assert on.count("data-mmx-all-tools") == 1
    assert on.count('<nav class="site-nav">') == 1
    assert on.count('<dialog id="mmx-all-tools"') == 1


def test_host_uses_existing_shared_assets_and_strict_opt_in() -> None:
    source = HOST.read_text()
    assert "all_tools.js" not in source
    assert "all_tools.css" not in source
    assert "sameas true" in source
    assert "data-tools-open hidden" in source
    assert 'aria-haspopup="dialog"' in source
    assert 'role="status"' in source
    assert "Find a workspace, not a ticker." in source


def test_only_three_pilot_pages_opt_in() -> None:
    dashboard = (TEMPLATES / "dashboard.html.j2").read_text()
    sector = (TEMPLATES / "sector_central.html.j2").read_text()
    reports_builder = (ROOT / "scripts" / "build_reports.py").read_text()
    assert "{% set all_tools_enabled = (mode != 'stocks') %}" in dashboard
    assert "{% set all_tools_enabled = true %}" in sector
    assert reports_builder.count("all_tools_enabled=True") == 1
    index_segment = reports_builder.split("# ---- index ----", 1)[1].split("# ---- one page per report ----", 1)[0]
    detail_segment = reports_builder.split("# ---- one page per report ----", 1)[1]
    assert "all_tools_enabled=True" in index_segment
    assert "all_tools_enabled=True" not in detail_segment


def test_existing_asset_owner_serves_the_component() -> None:
    assert (ROOT / "site" / "navigation-refresh.css").read_bytes() == NAV_CSS.read_bytes()
    assert (ROOT / "site" / "nav_market.js").read_bytes() == NAV_JS.read_bytes()
    assert not (ROOT / "site" / "all_tools.css").exists()
    assert not (ROOT / "site" / "all_tools.js").exists()


def test_committed_pilots_bust_the_current_navigation_css_payload() -> None:
    css_digest = hashlib.sha256((ROOT / "site" / "navigation-refresh.css").read_bytes()).hexdigest()[:8]
    expected = f"navigation-refresh.css?v={css_digest}"
    for name in ("macro.html", "sector_central.html", "reports.html"):
        rendered = (ROOT / "site" / name).read_text()
        assert rendered.count(expected) == 2, name


def test_committed_pilot_pages_have_one_host_and_stocks_stays_off() -> None:
    for name in ("macro.html", "sector_central.html", "reports.html"):
        rendered = (ROOT / "site" / name).read_text()
        assert rendered.count("data-mmx-all-tools") == 1, name
        assert rendered.count('id="mmx-all-tools"') == 1, name
        assert rendered.count("data-tools-open") == 1, name
    stocks = (ROOT / "site" / "us_stocks.html").read_text()
    assert "data-mmx-all-tools" not in stocks
