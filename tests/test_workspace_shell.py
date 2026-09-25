"""Contract tests for the opt-in Mastermind workspace shell.

The shell is presentation only. _site_nav.html.j2 remains the one product-header
owner; the shell may replace the legacy top-level link row on opted-in pages, but
must not duplicate search, Terminal, theme/language controls, routes, auth or state.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SIDEBAR = TEMPLATES / "_workspace_sidebar.html.j2"


def _t(en: str, zh: str = "") -> Markup:
    return Markup(en)


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False)


def _render_nav(**context: object) -> str:
    return _env().get_template("_site_nav.html.j2").render(t=_t, **context)


def test_legacy_header_is_identical_when_shell_mode_is_false_or_absent() -> None:
    absent = _render_nav()
    explicit_false = _render_nav(workspace_shell=False)
    assert absent == explicit_false
    assert 'class="nav-links"' in absent


def test_workspace_mode_reuses_header_controls_but_suppresses_legacy_link_row() -> None:
    html = _render_nav(workspace_shell=True, workspace_scope="all")
    assert 'class="nav-links"' not in html
    for marker in (
        'class="nav-search"',
        "product-icon-terminal",
        'class="theme-switch"',
        'class="lang-toggle"',
    ):
        assert marker in html
    assert html.count('class="nav-ctrls"') == 1


def test_workspace_sidebar_exists_as_one_shared_partial() -> None:
    assert SIDEBAR.exists(), "workspace sidebar must have one reusable template source"


def test_workspace_sidebar_uses_nested_prefix_and_one_active_research_item() -> None:
    if not SIDEBAR.exists():
        pytest.skip("sidebar source does not exist yet; existence test is the RED")
    html = _env().get_template(SIDEBAR.name).render(
        t=_t,
        nav_prefix="../",
        workspace_active="research",
        workspace_scope="all",
    )
    assert 'data-workspace-nav="primary"' in html
    assert html.count('aria-current="page"') == 1
    assert 'href="../research_vault.html"' in html
    for href in (
        "macro.html",
        "sector_central.html",
        "us_stocks.html",
        "options.html",
    ):
        assert f'href="../{href}"' in html
    assert "localStorage" not in html
    assert "<script" not in html


def test_workspace_sidebar_active_state_is_presentational_only() -> None:
    if not SIDEBAR.exists():
        pytest.skip("sidebar source does not exist yet; existence test is the RED")
    html = _env().get_template(SIDEBAR.name).render(
        t=_t,
        nav_prefix="",
        workspace_active="stocks",
        workspace_scope="us",
    )
    assert 'data-workspace-active="stocks"' in html
    assert "onclick=" not in html
    assert "data-market-write" not in html
