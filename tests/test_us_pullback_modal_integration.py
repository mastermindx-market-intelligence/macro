"""US Risk Radar popup switches to observed damage without replacing its modal shell.

Uses the existing product-sized Jinja render fixture; no new modal framework.
"""
from copy import deepcopy

from bs4 import BeautifulSoup
import pytest

from tests.test_macro_risk_dialog import _vm, _render, _dlg
from tests.test_risk_radar_pullback_depth_template import native_view


def dialog(view=None, *, mode="macro"):
    vm = _vm()
    if view is not None:
        vm["us_pullback_view"] = view
    return BeautifulSoup(_dlg(_render(vm=vm, mode=mode)), "html.parser")


def test_current_active_observation_leads_and_original_risk_evidence_remains_accessible():
    mode = "macro"
    root = dialog(native_view("us"), mode=mode)
    assert len(root.select('#dlg-risk')) <= 1  # extracted snippet begins inside the modal
    measured = root.select_one("section.rrp")
    assert measured and measured.get("data-pb-phase") == "underway"
    assert measured.select_one('[data-metric="current"]').get_text(strip=True) == "−6.8%"
    assert measured.select_one('[data-metric="worst"]').get_text(strip=True) == "−7.4%"
    assert measured.select_one('[data-forecast-status="unavailable"]')
    old = root.select_one(".riskdlg-brief")
    assert old is not None
    assert old.find_parent("details", class_="riskdlg-legacy-details") is not None
    disclosure = root.select_one("details.riskdlg-legacy-details")
    assert disclosure is not None and not disclosure.has_attr("open")
    assert "Forward risk and drivers" in disclosure.select_one("summary").get_text(" ", strip=True)
    html = str(root)
    assert "mx5CloseDlg()" in html
    assert "mx5-dlg-backdrop" in html


@pytest.mark.parametrize("phase", ["stabilizing", "recovering"])
def test_repair_observations_keep_the_measurement_primary_without_authorizing_buy(phase):
    view = native_view("us")
    view["phase"] = phase
    view["observation"]["phase"] = phase
    root = dialog(view)
    assert root.select_one("section.rrp").get("data-pb-phase") == phase
    assert "not a new-entry signal" in root.get_text(" ", strip=True)
    assert root.select_one('details.riskdlg-legacy-details') is not None


@pytest.mark.parametrize("change", [
    ("quality", "delayed"),
    ("schema", "wrong.v1"),
    ("clock", "intraday"),
    ("valid_until", None),
    ("available", False),
    ("market", "cn"),
    ("active", False),
    ("phase", "monitoring"),
])
def test_unqualified_or_pre_episode_view_keeps_previous_forecast_first_layout(change):
    v = native_view("us")
    k, value = change
    v["observation"][k] = value
    if k == "phase":
        v["phase"] = value
    root = dialog(v)
    assert root.select_one("section.rrp") is None
    assert root.select_one(".riskdlg-brief")
    assert root.select_one("details.riskdlg-legacy-details") is None


def test_missing_view_keeps_existing_popup_untouched():
    root = dialog()
    assert root.select_one(".riskdlg-brief")
    assert root.select_one("section.rrp") is None


def test_shared_pullback_css_is_present_in_the_real_us_page():
    html = _render(vm=_vm(), mode="macro")
    assert ".riskdlg-legacy-details" in html
    assert ".rrp-metrics" in html


ILLUS_LINK = '<link rel="stylesheet" href="illus.css">'


def test_observed_path_chart_loads_the_shared_illustration_stylesheet():
    # Without the shared stylesheet the chart's stroke path fills black and its
    # axis labels collapse into one unpositioned run (seen in the served page).
    vm = _vm()
    vm["us_pullback_view"] = native_view("us")
    html = _render(vm=vm, mode="macro")
    dlg = _dlg(html)
    assert dlg.count(ILLUS_LINK) == 1
    assert dlg.index(ILLUS_LINK) < dlg.index('class="ilx')


@pytest.mark.parametrize("view", [None, "inactive", "no_chart"])
def test_macro_page_is_unchanged_when_no_observed_chart_renders(view):
    vm = _vm()
    if view == "inactive":
        v = native_view("us")
        v["observation"]["quality"] = "delayed"
        vm["us_pullback_view"] = v
    elif view == "no_chart":
        v = native_view("us")
        v["detail_chart_html"] = ""
        vm["us_pullback_view"] = v
        assert dialog(v).select_one("section.rrp") is not None
    assert ILLUS_LINK not in _render(vm=vm, mode="macro")


def test_illustration_stylesheet_is_published_beside_the_macro_page():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert (root / "templates" / "illus.css").is_file()
    assert '"illus.css"' in (root / "scripts" / "build_site.py").read_text()
