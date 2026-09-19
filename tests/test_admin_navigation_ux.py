"""Admin shell UX guardrails for navigation and progressive disclosure.

These source-level tests keep the admin console usable as its page count grows. They
intentionally test the shipped static shell rather than backend behavior.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "admin" / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "admin" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "admin" / "static" / "styles.css").read_text(encoding="utf-8")


def test_admin_navigation_has_search_and_keyboard_access():
    assert 'id="navSearch"' in APP
    assert 'placeholder="Find an admin page…"' in APP
    assert 'data-nav-group' in APP
    assert 'data-nav-label=' in APP
    assert 'tabindex="0" role="button"' in APP
    assert 'e.key === "Enter" || e.key === " "' in APP
    assert 'No matching pages' in APP


def test_mobile_navigation_is_a_drawer_not_a_horizontal_page_strip():
    assert 'id="sidebarToggle"' in INDEX
    assert 'aria-controls="sidebar"' in INDEX
    assert 'id="sidebarScrim"' in INDEX
    assert '.sidebar.open' in CSS
    assert 'transform:translateX(-102%)' in CSS
    assert '.sidebar-scrim.show' in CSS
    assert 'body.nav-open' in CSS
    assert 'if (e.key === "Escape") setSidebarOpen(false)' in APP
    assert 'if (window.matchMedia("(max-width: 900px)").matches) setSidebarOpen(false)' in APP


def test_overview_keeps_primary_copy_concise_and_diagnostics_progressive():
    assert 'Key alerts — check in with Fable' not in APP
    assert 'Brief for Fable' not in APP
    assert '<div class="section">Needs attention</div>' in APP
    assert 'title="Copy the full alert context">Copy brief</button>' in APP
    assert 'class="tech-details"' in APP
    assert 'Program-watch data was not returned. This is not an all-clear.' in APP
    assert 'Deploy actions are unavailable.' in APP


def test_research_tools_do_not_repeat_internal_proprietary_disclaimers_on_every_card():
    assert '<div class="rt-kicker">Research workspace</div>' in APP
    assert '<p>Diagnostics, calibration, and internal research methods.</p>' in APP
    assert 'Internal diagnostics for model votes and neural-system output.' not in APP
    assert 'Proprietary cross-market, liquidity, and risk diagnostics.' not in APP
    assert 'Admin-only research workspace.' in APP


def test_experiments_table_hides_secondary_details_until_needed():
    assert 'Long-running tests and data collections, with the next review date and action.' in APP
    assert '<summary>Source</summary>' in APP
    assert '<details class="row-actions">' in APP
    assert '<summary class="btn">Actions</summary>' in APP
    assert '>Mark acted</button>' in APP
    assert '>Snooze</button>' in APP
    assert '>Dismiss</button>' in APP
    assert '>Override</button>' in APP
    assert '.row-actions-menu' in CSS


def test_site_access_keeps_provider_details_out_of_primary_copy():
    assert 'Country detection not configured' in APP
    assert '<summary>Technical details</summary>' in APP
    assert 'Country source is resolved by <code>/api/gate/check</code>' in APP
    assert '<div class="section">Blocked IPs ' in APP
    assert '<div class="section">Always allowed ' in APP
    assert '<div class="section">Blocked countries ' in APP
    assert 'Names via browser Intl.DisplayNames' not in APP
    assert 'Off = fail-open.' not in APP
