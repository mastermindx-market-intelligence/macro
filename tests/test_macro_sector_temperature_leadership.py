"""Sector Temperature consumer regression: hot leaders, ratings, and null history.

This is display-only. The adapter must not modify Theme Intelligence scores,
recommendations, membership, historical evidence or stock-entry authority.
"""
from __future__ import annotations

from copy import deepcopy

from bs4 import BeautifulSoup

from tests.test_dashboard_template_render import _base_vm, _env


def _pulse():
    return {
        "as_of": "2026-10-30",
        "history": {
            "basis": "nyse_sessions",
            "expected_comparison_as_of": {"5d": "2026-10-23"},
            "comparison_as_of": {"5d": None},
        },
        "heating": [],
        "themes": [
            {"id": "energy", "name": "Energy (Equal-Weight)", "name_zh": "能源",
             "rank": 1, "score": 78, "label": "dominant", "heat": "hot",
             "reco": "hold", "rank_delta_5d": None},
            {"id": "energy_complex", "name": "US Energy Complex", "name_zh": "美国能源",
             "rank": 2, "score": 75, "label": "dominant", "heat": "hot",
             "reco": "hold", "rank_delta_5d": None},
            {"id": "health", "name": "Health Care (Equal-Weight)", "name_zh": "医疗保健",
             "rank": 3, "score": 75, "label": "dominant", "heat": "hot",
             "reco": "hold", "rank_delta_5d": None},
            {"id": "big_pharma", "name": "Big Pharma", "name_zh": "大型制药",
             "rank": 4, "score": 74, "label": "dominant", "heat": "hot",
             "reco": "hold", "rank_delta_5d": None},
            {"id": "consumer_staples", "name": "Consumer Staples (Equal-Weight)",
             "name_zh": "必需消费", "rank": 5, "score": 74, "label": "dominant",
             "heat": "hot", "reco": "accumulate", "rank_delta_5d": None},
            {"id": "cybersecurity", "name": "Cybersecurity", "name_zh": "网络安全",
             "rank": 17, "score": 55, "label": "fading", "heat": "cooling",
             "reco": "trim", "rank_delta_5d": None},
            {"id": "robotics_automation", "name": "Robotics & Automation",
             "name_zh": "机器人与自动化", "rank": 26, "score": 42,
             "label": "deteriorating", "heat": "broken", "reco": "avoid",
             "rank_delta_5d": None},
        ],
    }


def _view(monkeypatch, payload):
    from engine import sector_pulse
    from scripts import build_site

    before = deepcopy(payload)
    monkeypatch.setattr(sector_pulse, "build_pulse", lambda region: payload)
    view = build_site._sector_heat_view()
    assert payload == before  # read-only projection
    return view


def _render(view):
    vm = _base_vm()
    vm["sector_heat"] = view
    return BeautifulSoup(
        _env().get_template("dashboard.html.j2").render(**vm, mode="macro"),
        "html.parser",
    )


def test_established_hot_leaders_survive_empty_acceleration_roster(monkeypatch):
    view = _view(monkeypatch, _pulse())
    assert view["heating"] == []
    assert [r["id"] for r in view["leaders"]] == [
        "energy", "energy_complex", "health", "big_pharma", "consumer_staples",
    ]
    assert view["positive_hot"]["id"] == "consumer_staples"
    assert view["positive_hot"]["reco"] == "accumulate"
    assert view["positive_hot"]["score"] == 74
    assert view["desk"]["leader"] is None  # no invented velocity


def test_macro_face_and_modal_explain_consumer_staples_rating(monkeypatch):
    doc = _render(_view(monkeypatch, _pulse()))
    face = doc.select_one("#sx-v5-sector")
    modal = doc.select_one("#dlg-sector")
    assert face is not None and modal is not None
    assert "Established theme leadership is active" in face.get_text(" ", strip=True)
    assert "Energy (Equal-Weight)" in face.get_text(" ", strip=True)
    assert "Consumer Staples (Equal-Weight)" in face.get_text(" ", strip=True)
    assert "Accumulate" in face.get_text(" ", strip=True)
    assert "Stand aside — no sector is running hot today." not in face.get_text(" ", strip=True)
    leader_rows = modal.select('[data-temperature-lane="established"] .sct-rung')
    assert len(leader_rows) == 5
    staples = next(r for r in leader_rows if "Consumer Staples" in r.get_text(" ", strip=True))
    assert "#5" in staples.get_text(" ", strip=True)
    assert "Theme rating: Accumulate" in staples.get_text(" ", strip=True)
    assert not modal.select('[data-temperature-lane="accelerating"]')
    assert len(modal.select('[data-temperature-lane="weakening"] .sct-rung')) == 2
    assert "not measured fund flows or stock entry calls" in modal.get_text(" ", strip=True)
    assert modal.select_one('a[href="sector_central.html"]') is not None


def test_missing_history_is_not_flat_or_zero_movement(monkeypatch):
    modal = _render(_view(monkeypatch, _pulse())).select_one("#dlg-sector")
    assert "2026-10-23 observation is missing" in modal.get_text(" ", strip=True)
    assert "History unavailable" in modal.get_text(" ", strip=True)
    assert len(modal.select(".sct-rung")) == 7
    assert len(modal.select(".sct-trace-na")) == 7
    assert len(modal.select(".sct-rung .sct-trace svg")) == 0
    assert [x.get_text(strip=True) for x in modal.select(".sct-delta-v")] == ["—"] * 7
    assert all("5d n/a" in row.get_text(" ", strip=True) for row in modal.select(".sct-rung"))


def test_measured_zero_rank_move_is_distinct_from_null(monkeypatch):
    payload = _pulse()
    payload["history"]["comparison_as_of"]["5d"] = "2026-10-23"
    payload["themes"][0]["rank_delta_5d"] = 0
    payload["themes"][1]["rank_delta_5d"] = -3
    payload["themes"][4]["rank_delta_5d"] = 3
    modal = _render(_view(monkeypatch, payload)).select_one("#dlg-sector")
    rows = modal.select('[data-temperature-lane="established"] .sct-rung')
    assert rows[0].select_one(".sct-trace") is not None
    assert rows[0].select_one("svg.sct-trace") is not None
    assert rows[0].select_one(".sct-delta-v").get_text(strip=True) == "0"
    assert rows[1].select_one(".sct-delta-v").get_text(strip=True) == "-3"
    assert rows[4].select_one(".sct-delta-v").get_text(strip=True) == "+3"
    assert rows[2].select_one(".sct-trace-na") is not None
    assert "observation is missing" not in modal.get_text(" ", strip=True)


def test_new_acceleration_is_separate_from_established_hot(monkeypatch):
    payload = _pulse()
    payload["themes"].append(
        {"id": "recovery", "name": "Recovery Theme", "name_zh": "复苏主题",
         "rank": 11, "score": 63, "label": "emerging", "heat": "heating",
         "reco": "hold", "rank_delta_5d": 4}
    )
    payload["heating"] = ["recovery"]
    doc = _render(_view(monkeypatch, payload))
    assert len(doc.select('[data-temperature-lane="established"] .sct-rung')) == 5
    accel = doc.select('[data-temperature-lane="accelerating"] .sct-rung')
    assert len(accel) == 1
    assert "Recovery Theme" in accel[0].get_text(" ", strip=True)
    assert "Consumer Staples" not in accel[0].get_text(" ", strip=True)
