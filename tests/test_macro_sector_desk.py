"""The Macro card separates descriptive desk leadership from recommendation context."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from itertools import permutations

import pytest

# Sep-18 observations anchored to actual session dates; no hard-coded production winner.
NOW = datetime(2026, 9, 21, 20, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _freeze_card_clock(monkeypatch):
    # Adapter integration must remain deterministic after this fixture's date.
    from lib import sector_desk_view

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz or timezone.utc)

    monkeypatch.setattr(sector_desk_view, "datetime", FrozenClock)


def _row(key, rank, five, one, heat="heating", reco="accumulate", **extra):
    return dict(id=key, name=key.replace("_", " ").title(), name_zh="板块",
                rank=rank, rank_delta_5d=five, rank_delta_1d=one, heat=heat, reco=reco, **extra)


def _history(as_of="2026-09-18"):
    from lib.nyse_calendar import session_n_back
    try:
        day = date.fromisoformat(as_of)
        dates = {f"{n}d": session_n_back(day, n).isoformat() for n in (1, 5, 20)}
    except (TypeError, ValueError, AttributeError):
        dates = {}
    return {"basis": "nyse_sessions", "comparison_as_of": dict(dates),
            "expected_comparison_as_of": dict(dates)}


def _pulse():
    rows = [
        _row("crypto", 1, 1, 3, reco="hold"),
        _row("mag7", 2, 3, 0),
        _row("crypto_rails", 3, 4, 6),
        _row("cybersecurity", 4, 25, -3, reco="hold"),
        _row("memory_storage", 5, 8, 12),
        _row("ai_semiconductors", 6, 14, -1),
        _row("quantum_computing", 25, 15, -4, heat="idle", reco="hold"),
        _row("space_economy", 27, 15, 1, heat="broken"),
    ]
    rows[3].update(name="Cybersecurity", name_zh="网络安全")
    rows[5].update(name="AI Semiconductors", name_zh="AI 半导体")
    return dict(as_of="2026-09-18", history=_history(), heating=[r["id"] for r in rows[:6]], themes=rows)


def _desk(rows=None, as_of="2026-09-18", now=NOW):
    from lib.sector_desk_view import opportunity_desk
    return opportunity_desk(_pulse()["themes"] if rows is None else rows, as_of, history=_history(as_of), now=now)


def test_card_leader_is_selected_before_the_four_row_strip_cap(monkeypatch):
    from engine import sector_pulse
    from scripts import build_site
    pulse = _pulse()
    # The fifth/sixth rows must still compete for the primary desk even though
    # the visible strip is capped at four.
    semis = next(row for row in pulse["themes"] if row["id"] == "ai_semiconductors")
    semis["rank_delta_5d"] = 30
    before = deepcopy(pulse)
    monkeypatch.setattr(sector_pulse, "build_pulse", lambda _: pulse)
    view = build_site._sector_heat_view()
    assert [r["id"] for r in view["heating"]] == pulse["heating"][:4]
    assert view["desk"]["leader"]["id"] == "ai_semiconductors"
    assert view["desk"]["leader"]["rank_delta_5d"] == 30
    assert view["desk"]["positive_rating_leader"]["id"] == "ai_semiconductors"
    assert [r["id"] for r in view["rotation"]] == ["ai_semiconductors", "memory_storage"]
    assert pulse == before


def test_full_population_velocity_beats_absolute_rank_and_latest_day_alone():
    out = _desk()
    assert out["status"] == "ready"
    # Five-session velocity wins even when the latest session is weak and the
    # rating is Hold. Positive-rating context remains a separate answer.
    assert out["leader"]["id"] == "cybersecurity"
    assert out["leader"]["rank_delta_1d"] == -3
    assert out["leader"]["positive_rating"] is False
    assert out["positive_rating_leader"]["id"] == "ai_semiconductors"
    assert out["as_of"] == "2026-09-18"
    assert out["href"] == "basket/cybersecurity.html"


def test_order_does_not_choose_the_winner():
    rows = [_row("older", 1, 8, 0), _row("first", 4, 14, -3), _row("second", 6, 14, 10)]
    for ordering in permutations(rows):
        assert _desk(list(ordering))["leader"]["id"] == "second"


def test_a_different_desk_can_win_without_semiconductor_special_cases():
    out = _desk([_row("ai_semiconductors", 1, 4, 12), _row("cybersecurity", 9, 18, 2)])
    assert out["leader"]["id"] == "cybersecurity"


@pytest.mark.parametrize("heat", ["hot", "idle", "cooling", "broken", None])
def test_only_producer_heating_rows_are_eligible(heat):
    out = _desk([_row("ineligible", 1, 40, 40, heat), _row("eligible", 12, 5, 1)])
    assert out["leader"]["id"] == "eligible"


@pytest.mark.parametrize("value", [None, True, False, "14", float("nan"), float("inf"), -2, 0, 1.5])
def test_missing_invalid_or_nonpositive_history_never_becomes_leadership(value):
    assert _desk([_row("unknown", 1, value, 10)])["leader"] is None


@pytest.mark.parametrize("second_day", [None, float("nan"), True, 10])
def test_unresolved_tie_does_not_invent_a_sole_winner(second_day):
    out = _desk([_row("a", 1, 14, 10), _row("b", 2, 14, second_day)])
    assert out["status"] == "tied"
    assert out["leader"] is None


def test_zero_last_session_is_observed_not_missing():
    assert _desk([_row("a", 2, 14, -3), _row("b", 5, 14, 0)])["leader"]["id"] == "b"


@pytest.mark.parametrize("as_of", [None, "", "not-a-date", "2026-02-30", "2026-09-22", "2026-09-19"])
def test_undated_future_or_non_session_data_cannot_claim_a_leader(as_of):
    assert _desk(as_of=as_of)["leader"] is None


def test_weekends_and_exchange_holidays_do_not_create_false_staleness():
    holiday = datetime(2026, 9, 7, 23, 0, tzinfo=timezone.utc)
    assert _desk(as_of="2026-09-04", now=holiday)["status"] == "ready"
    assert _desk()["sessions_behind"] == 0


def test_late_daily_refresh_is_dated_but_multi_session_outage_is_not_hottest():
    monday_evening = datetime(2026, 9, 21, 23, 0, tzinfo=timezone.utc)
    assert _desk(now=monday_evening)["sessions_behind"] == 1
    assert _desk(now=monday_evening)["leader"] is not None
    stale = _desk(now=datetime(2026, 9, 22, 23, 0, tzinfo=timezone.utc))
    assert stale["status"] == "stale"
    assert stale["leader"] is None
    assert stale["as_of"] == "2026-09-18"


@pytest.mark.parametrize("key", ["../admin", "javascript:alert(1)", "a#x", "", None])
def test_invalid_theme_ids_cannot_become_navigation_targets(key):
    assert _desk([_row("valid", 5, 2, 1) | {"id": key}])["leader"] is None


def test_authoritative_empty_heating_roster_stays_empty(monkeypatch):
    from engine import sector_pulse
    from scripts import build_site
    pulse = _pulse()
    pulse["heating"] = []
    monkeypatch.setattr(sector_pulse, "build_pulse", lambda _: pulse)
    view = build_site._sector_heat_view()
    assert view["heating"] == []
    assert view["desk"]["leader"] is None


def test_macro_renders_exact_desk_with_source_date_and_real_destination():
    from bs4 import BeautifulSoup
    from tests.test_dashboard_template_render import _base_vm, _env
    vm = _base_vm()
    vm["sector_heat"] = {"desk": _desk(), "heating": [_row("wrong", 1, 1, 1)]}
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="macro")
    card = BeautifulSoup(html, "html.parser").select_one("#macro-sector-desk")
    assert card is not None
    assert card["href"] == "basket/cybersecurity.html"
    assert not card.has_attr("data-tip-en"), "Whole-link LENS hijacks the first mobile tap"
    assert "Cybersecurity" in card.get_text()
    assert "网络安全" in card.get_text()
    assert "Hottest desk" in card.get_text()
    assert "Up 25 places over 5 sessions" in card.get_text()
    assert "Current rating: Hold" in card.get_text()
    assert card["data-desk-rating"] == "hold"
    assert not card.has_attr("data-entry-actionable")
    assert card.select_one("time")["datetime"] == "2026-09-18"
    assert "Running hot right now" not in card.get_text()
    assert "Opportunity watch" not in card.get_text()
    assert "wrong" not in card.get_text().lower()


@pytest.mark.parametrize("desk", [None, {}, {"leader": None, "status": "unavailable"}])
def test_absent_history_renders_neutral_navigation_not_old_first_row(desk):
    from bs4 import BeautifulSoup
    from tests.test_dashboard_template_render import _base_vm, _env
    vm = _base_vm()
    vm["sector_heat"] = {"desk": desk, "heating": [_row("wrong", 1, 1, 1)]}
    html = _env().get_template("dashboard.html.j2").render(**vm, mode="macro")
    card = BeautifulSoup(html, "html.parser").select_one("#macro-sector-desk")
    assert card["href"] == "sector_central.html"
    assert "Opportunity watch" not in card.get_text()
    assert "wrong" not in card.get_text().lower()


def test_hold_rating_does_not_hide_descriptive_leadership():
    out = _desk([
        _row("ai_semiconductors", 3, 26, -3, reco="hold"),
        _row("memory_storage", 10, 23, 13, reco="accumulate"),
    ])
    assert out["leader"]["id"] == "ai_semiconductors"
    assert out["leader"]["reco"] == "hold"
    assert out["leader"]["rating_label_en"] == "Hold"
    assert out["leader"]["positive_rating"] is False
    assert out["positive_rating_leader"]["id"] == "memory_storage"
    assert out["positive_rating_leader"]["positive_rating"] is True


@pytest.mark.parametrize(
    ("reco", "label_en", "positive_rating"),
    [
        ("enter", "Enter", True),
        ("accumulate", "Accumulate", True),
        ("hold", "Hold", False),
        ("trim", "Trim", False),
        ("avoid", "Avoid", False),
        ("exit", "Exit", False),
        (None, "Unavailable", False),
        ("unknown", "Unavailable", False),
    ],
)
def test_recommendation_state_is_secondary_metadata_not_leadership_filter(reco, label_en, positive_rating):
    row = _row("leader", 4, 18, 2, reco="accumulate")
    row["reco"] = reco
    out = _desk([row])
    assert out["leader"]["id"] == "leader"
    assert out["leader"]["rating_label_en"] == label_en
    assert out["leader"]["positive_rating"] is positive_rating
    if positive_rating:
        assert out["positive_rating_leader"]["id"] == "leader"
    else:
        assert out["positive_rating_leader"] is None
    assert "entry_actionable" not in out["leader"]


@pytest.mark.parametrize("history", [None, {}, {"basis": "archive_rows"},
    {"basis": "nyse_sessions", "expected_comparison_as_of": {"5d": "2026-09-11"},
     "comparison_as_of": {"5d": "2026-09-09"}},
    {"basis": "nyse_sessions", "expected_comparison_as_of": {"5d": "2026-09-11"},
     "comparison_as_of": {"5d": None}}])
def test_old_or_unproven_comparison_clock_cannot_advertise_a_leader(history):
    from lib.sector_desk_view import opportunity_desk
    out = opportunity_desk(_pulse()["themes"], "2026-09-18", history=history, now=NOW)
    assert out["leader"] is None
    assert out["href"] == "sector_central.html"


def test_latest_session_tiebreak_requires_its_own_proven_date():
    from lib.sector_desk_view import opportunity_desk
    history = _history()
    history["comparison_as_of"]["1d"] = "2026-09-16"
    out = opportunity_desk([_row("a", 1, 14, -3), _row("b", 6, 14, 10)],
                           "2026-09-18", history=history, now=NOW)
    assert out["status"] == "tied"
    assert out["leader"] is None


# Sector Temperature — established leaders and honest five-session history
def _temperature_snapshot():
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


def _temperature_view(monkeypatch, payload, *, observed_at=None):
    from engine import sector_pulse
    from lib import sector_desk_view
    from scripts import build_site

    # Deterministic NYSE freshness for this October snapshot. The older desk
    # tests in this module deliberately pin a September clock instead.
    stamp = observed_at or datetime(2026, 11, 2, 23, 0, tzinfo=timezone.utc)

    class SourceClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return stamp.astimezone(tz or timezone.utc)

    before = deepcopy(payload)
    monkeypatch.setattr(sector_desk_view, "datetime", SourceClock)
    monkeypatch.setattr(sector_pulse, "build_pulse", lambda region: payload)
    view = build_site._sector_heat_view()
    assert payload == before  # read-only projection
    return view


def _temperature_render(view):
    from bs4 import BeautifulSoup
    from tests.test_dashboard_template_render import _base_vm, _env

    vm = _base_vm()
    vm["sector_heat"] = view
    return BeautifulSoup(
        _env().get_template("dashboard.html.j2").render(**vm, mode="macro"),
        "html.parser",
    )


def test_established_hot_leaders_survive_empty_acceleration_roster(monkeypatch):
    view = _temperature_view(monkeypatch, _temperature_snapshot())
    assert view["heating"] == []
    assert [r["id"] for r in view["leaders"]] == [
        "energy", "energy_complex", "health", "big_pharma", "consumer_staples",
    ]
    assert view["positive_hot"]["id"] == "consumer_staples"
    assert view["positive_hot"]["reco"] == "accumulate"
    assert view["positive_hot"]["score"] == 74
    assert view["desk"]["leader"] is None  # no invented velocity


def test_macro_face_and_modal_explain_consumer_staples_rating(monkeypatch):
    doc = _temperature_render(_temperature_view(monkeypatch, _temperature_snapshot()))
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
    modal = _temperature_render(_temperature_view(monkeypatch, _temperature_snapshot())).select_one("#dlg-sector")
    assert "2026-10-23 observation is missing" in modal.get_text(" ", strip=True)
    assert "History unavailable" in modal.get_text(" ", strip=True)
    assert len(modal.select(".sct-rung")) == 7
    assert len(modal.select(".sct-trace-na")) == 7
    assert len(modal.select(".sct-rung .sct-trace svg")) == 0
    assert [x.get_text(strip=True) for x in modal.select(".sct-delta-v")] == ["—"] * 7
    assert all("5d n/a" in row.get_text(" ", strip=True) for row in modal.select(".sct-rung"))


def test_measured_zero_rank_move_is_distinct_from_null(monkeypatch):
    payload = _temperature_snapshot()
    payload["history"]["comparison_as_of"]["5d"] = "2026-10-23"
    payload["themes"][0]["rank_delta_5d"] = 0
    payload["themes"][1]["rank_delta_5d"] = -3
    payload["themes"][4]["rank_delta_5d"] = 3
    modal = _temperature_render(_temperature_view(monkeypatch, payload)).select_one("#dlg-sector")
    rows = modal.select('[data-temperature-lane="established"] .sct-rung')
    assert rows[0].select_one(".sct-trace") is not None
    assert rows[0].select_one("svg.sct-trace") is not None
    assert rows[0].select_one(".sct-delta-v").get_text(strip=True) == "0"
    assert rows[1].select_one(".sct-delta-v").get_text(strip=True) == "-3"
    assert rows[4].select_one(".sct-delta-v").get_text(strip=True) == "+3"
    assert rows[2].select_one(".sct-trace-na") is not None
    assert "observation is missing" not in modal.get_text(" ", strip=True)


def test_new_acceleration_is_separate_from_established_hot(monkeypatch):
    payload = _temperature_snapshot()
    payload["themes"].append(
        {"id": "recovery", "name": "Recovery Theme", "name_zh": "复苏主题",
         "rank": 11, "score": 63, "label": "emerging", "heat": "heating",
         "reco": "hold", "rank_delta_5d": 4}
    )
    payload["heating"] = ["recovery"]
    doc = _temperature_render(_temperature_view(monkeypatch, payload))
    assert len(doc.select('[data-temperature-lane="established"] .sct-rung')) == 5
    accel = doc.select('[data-temperature-lane="accelerating"] .sct-rung')
    assert len(accel) == 1
    assert "Recovery Theme" in accel[0].get_text(" ", strip=True)
    assert "Consumer Staples" not in accel[0].get_text(" ", strip=True)


def test_mobile_layout_gives_missing_history_a_separate_row():
    """Keep long theme names, bilingual ratings and missing-history text readable."""
    from pathlib import Path

    css_template = (Path(__file__).resolve().parents[1] / "templates" / "dashboard.html.j2").read_text()
    sector_styles = css_template[css_template.index("/* ── Sector Temperature — rotation ladder"):
                                 css_template.index("/* ── News modal — Market Intelligence")]
    assert "@media(max-width:600px)" in sector_styles
    assert ".sct-trace{grid-column:2 / 4;grid-row:2;width:100%;height:24px;}" in sector_styles
    assert ".sct-body{grid-column:2;grid-row:1;}" in sector_styles
    assert ".sct-trace-na{min-height:20px;justify-content:flex-start;text-align:left;}" in sector_styles

def test_theme_freshness_reuses_completed_nyse_sessions(monkeypatch):
    # Friday's finished snapshot is still the most recent available Monday evening.
    view = _temperature_view(monkeypatch, _temperature_snapshot())
    assert view["snapshot_state"] == "current"
    assert view["sessions_behind"] == 1
    doc = _temperature_render(view)
    assert "Established theme leadership is active" in doc.select_one("#sx-v5-sector").get_text(" ", strip=True)
    assert "Outdated theme snapshot" not in doc.select_one("#dlg-sector").get_text(" ", strip=True)


def test_stale_theme_snapshot_is_historical_not_current_recommendation(monkeypatch):
    view = _temperature_view(
        monkeypatch, _temperature_snapshot(),
        observed_at=datetime(2026, 11, 5, 23, tzinfo=timezone.utc),
    )
    assert view["snapshot_state"] == "stale"
    assert view["sessions_behind"] > 1
    assert view["positive_hot"]["id"] == "consumer_staples"
    doc = _temperature_render(view)
    face = doc.select_one("#sx-v5-sector").get_text(" ", strip=True)
    modal = doc.select_one("#dlg-sector").get_text(" ", strip=True)
    assert "Last recorded theme leadership only" in face
    assert "Dated theme rating" in face
    assert "Established theme leadership is active" not in face
    assert "Outdated theme snapshot (2026-10-30)" in modal
    assert "not today's leadership or entry instructions" in modal
    assert "Theme rating: Accumulate" in modal


def test_future_or_invalid_theme_clock_cannot_advertise_current_leadership(monkeypatch):
    for bad in ("2026-11-03", "not-a-date", None):
        pulse = _temperature_snapshot()
        pulse["as_of"] = bad
        view = _temperature_view(monkeypatch, pulse)
        assert view["snapshot_state"] == "invalid"
        assert view["sessions_behind"] is None
        doc = _temperature_render(view)
        face = doc.select_one("#sx-v5-sector").get_text(" ", strip=True)
        modal = doc.select_one("#dlg-sector").get_text(" ", strip=True)
        assert "Theme observation date is unverified" in face
        assert "Theme snapshot clock is invalid or unverified" in modal
        assert "Established theme leadership is active" not in face
