"""Contract checks for the Risk Radar presentation boundary.

Risk/forecast authority stays in the existing engines. These cases exercise
missing owners, nullable values, horizon separation and the JSON/HTML boundary.
Interactive checks are in tests/risk_radar_workspace_browser.py.
"""
import json
from pathlib import Path

import jinja2
import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def projection(radar, *, envelope=None):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "templates"))
    html = env.get_template("_risk_radar_workspace.html.j2").render(
        market_state={"radar": radar}, risk_envelope=envelope
    )
    soup = BeautifulSoup(html, "html.parser")
    return json.loads(soup.select_one("#risk-radar-workspace-data").string), soup


@pytest.mark.parametrize("coverage,expected", [
    ({"fresh": ["market", "leadership", "radar"], "source_count": 4}, "3 of 4"),
    ({"fresh": [], "source_count": 4}, "0 of 4"),
    ({"fresh": "bad", "source_count": 4}, "incomplete source coverage"),
    (None, "incomplete source coverage"),
])
def test_internals_lead_with_settled_coverage(coverage, expected):
    envelope = {
        "schema": "mastermind.risk_envelope/v1", "data_state": "PARTIAL",
        "source_session": "2026-10-30", "coverage": coverage,
        "coherence": {"scope": "market_reads"},
    }
    model, soup = projection({"dd21": 0.22}, envelope=envelope)
    line = soup.select_one(".rkw-internals-slot .rkw-coverage")
    assert expected in line.select_one(".l-en").string
    assert "trend and stress" in line.select(".l-en")[1].string
    assert "趋势与压力" in line.select(".l-zh")[1].string
    assert model["horizons"]["21"]["probability"] == 0.22

    envelope["data_state"] = "FRESH"
    assert projection({}, envelope=envelope)[1].select_one(".rkw-coverage") is None


def test_projection_preserves_each_horizon_and_its_own_baseline():
    native = {
        "dd5": 0.054, "dd10": 0.12, "dd21": 0.22,
        "dd_base": {"h5": 0.036, "h10": 0.086, "h21": 0.178},
        "dd_evidence": {"horizons": {
            "h21": {"matched": True, "displayed_probability": 0.22, "thin": True, "n": 66}
        }},
    }
    model, _ = projection(native)
    assert model["schema"] == "mastermind.risk_radar_workspace/v1"
    assert model["scope"] == "US" and model["benchmark"] == "SPY"
    for day in (5, 10, 21):
        item = model["horizons"][str(day)]
        assert item["probability"] == native[f"dd{day}"]
        assert item["baseline"] == native["dd_base"][f"h{day}"]
    assert model["horizons"]["5"]["history"] == {}
    assert model["horizons"]["21"]["history"]["n"] == 66


@pytest.mark.parametrize("native", [None, {}, [], "missing"])
def test_missing_radar_never_becomes_zero_probability(native):
    model, _ = projection(native)
    for item in model["horizons"].values():
        assert item["probability"] is None
        assert item["baseline"] is None


@pytest.mark.parametrize("bad", [None, [], "unavailable", 42])
def test_malformed_optional_evidence_does_not_break_the_dashboard(bad):
    model, _ = projection({"dd5": 0.0, "dd_base": bad, "dd_evidence": bad})
    assert model["horizons"]["5"]["probability"] == 0.0
    assert model["horizons"]["5"]["baseline"] is None
    assert model["horizons"]["5"]["history"] == {}


def test_source_text_cannot_escape_the_json_element():
    hostile = '</script><img src=x onerror="window.injected=true">'
    model, soup = projection({
        "dd_evidence": {"horizons": {"h21": {"source": hostile}}}
    })
    assert model["horizons"]["21"]["history"]["source"] == hostile
    assert len(soup.find_all("script")) == 1
    assert soup.find("img") is None
    assert soup.select_one("#risk-radar-workspace-template") is not None


def test_no_live_hook_is_copied_into_the_inert_shell():
    _, soup = projection({})
    assert soup.select_one("#gde-live-stage") is None
    assert soup.select_one("#risk-envelope-band") is None
    assert len(soup.select("button[data-rkw-horizon]")) == 3


def test_partial_data_still_keeps_the_legacy_evidence_in_the_dialog():
    # The source's conditional closing tag used to close the dialog body when
    # the scare list was absent. Render this boundary with both states.
    source = (ROOT / "templates/dashboard.html.j2").read_text()
    start = source.index("        {% if latest.risk_radar and latest.risk_radar.scares %}", source.index('id="dlg-risk"'))
    end = source.index("{# Macro UX follow-up", start)
    fragment = source[start:end]
    rendered = jinja2.Environment().from_string(
        '<div id="host">' + fragment + '<span id="after">After</span></div>'
    ).render(latest={"risk_radar": {"scares": []}})
    soup = BeautifulSoup(rendered, "html.parser")
    assert soup.select_one("#after").parent.get("id") == "host"
