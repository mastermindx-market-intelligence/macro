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
