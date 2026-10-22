"""Tests for engine.news_impact.observation (A4 observation-window calculator).

Acceptance fixtures are the A4 design worked cases 5.5/5.6/5.7
(``designs/A4_transfer_obs/cases/W_obs_*.json``) and every Appendix C clock
row.  Hermetic: no network, no repo data files (the design-case files are
fail closed with the missing path when absent), no writes outside tmp_path (this
suite writes nothing).  Deterministic: no clock reads anywhere.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.news_impact.observation import (
    CODES,
    DELAYED_ENTRY_POLICIES,
    Bar,
    OBSERVATION_VERSION,
    TradingCalendar,
    WindowGeometry,
    build_observation_window,
    canonical_json,
    compute_window_geometry,
    parse_utc,
    to_ny_local,
    to_utc_stamp,
    validate_record,
)
from engine.news_impact.observation import ObservationError

# --- paths ----------------------------------------------------------------------

SRC = Path(__file__).resolve().parents[1]
DESIGN_CASES = Path(__file__).resolve().parents[1] / "research" / "prophet_v4" / "news_to_business_impact_20261006" / "phase1_designs" / "A4_transfer_obs" / "cases"
AMENDMENTS_CASES = DESIGN_CASES.parents[1] / "AMENDMENTS_W1C.cases.json"

T0 = "2026-09-28T13:32:14Z"  # App C base row: 09:32:14 America/New_York, EDT

TARGET = "cik:0001046179"  # TSMC (design cases)
SOURCE_FACT = "fact_678e8bf5a1906cc701210c40"

PEER_SET = {
    "selection": "documented_exposure",
    "member_ids": ["cik:0000937966", "cik:0000723125"],
    "excluded_target_id": TARGET,
    "target_excluded": True,
}
RESIDUAL_FIT = {
    "method": "ols_trailing_pre_cutoff",
    "fit_start": "2026-07-01T20:00:00Z",
    "fit_end": "2026-09-25T20:00:00Z",
    "legs": [
        {"factor_id": "market", "fitted_coefficient": 1.12, "window_bars": 60},
        {"factor_id": "documented_peer_residual", "fitted_coefficient": 0.41, "window_bars": 60},
    ],
}


# --- helpers ---------------------------------------------------------------------


def weekday_calendar(start: date, end: date, early: dict[str, str] | None = None, drop: set[str] | None = None) -> dict:
    """An injected NYSE-style calendar: every weekday, optional early closes/holidays."""
    early = early or {}
    drop = drop or set()
    sessions: dict[str, dict[str, str]] = {}
    day = start
    while day <= end:
        if day.weekday() < 5 and day.isoformat() not in drop:
            sessions[day.isoformat()] = {"open": "09:30:00", "close": early.get(day.isoformat(), "16:00:00")}
        day += timedelta(days=1)
    return {"sessions": sessions}


def main_calendar() -> dict:
    """Sessions around the design week (2026-09-25 Fri, 09-28 Mon, 09-29 Tue)."""
    return weekday_calendar(date(2026, 9, 21), date(2026, 10, 2))


def five_min_bars(day: str, first: str, last: str) -> list[dict]:
    """Synthetic 5-minute bars [first, last) on one UTC day as mappings."""
    start = parse_utc(f"{day}T{first}Z")
    stop = parse_utc(f"{day}T{last}Z")
    out = []
    while start + timedelta(minutes=5) <= stop:
        out.append({"start": to_utc_stamp(start), "end": to_utc_stamp(start + timedelta(minutes=5))})
        start += timedelta(minutes=5)
    return out


def week_bars() -> list[dict]:
    return five_min_bars("2026-09-25", "13:00:00", "20:00:00") + five_min_bars("2026-09-28", "13:00:00", "20:00:00") + five_min_bars("2026-09-29", "13:30:00", "20:00:00")


def load_case(name: str) -> dict:
    path = DESIGN_CASES / f"{name}.json"
    assert path.is_file(), f"repo-owned design case fixture missing (fail closed, never skip): {path}"
    case = json.loads(path.read_text(encoding="utf-8"))
    # X4 (DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS): the case files stay byte-frozen; the
    # session-counted matched-window values come from the machine-readable overlay,
    # applied here fail-closed (the overlay must exist, and the frozen values it
    # supersedes must still match the case file, so a drifted fixture is caught).
    assert AMENDMENTS_CASES.is_file(), f"amendments overlay missing (fail closed, never skip): {AMENDMENTS_CASES}"
    entry = json.loads(AMENDMENTS_CASES.read_text(encoding="utf-8")).get("cases", {}).get(
        f"A4_transfer_obs/cases/{name}.json"
    )
    if entry is None:
        return case
    for field, frozen_value in entry["superseded"].items():
        assert case[field] == frozen_value, (
            f"frozen fixture {name}.{field} drifted from the overlay's superseded value: "
            f"{case[field]!r} != {frozen_value!r}"
        )
    for field, value in entry.items():
        if field not in ("superseded", "reason"):
            case[field] = value
    return case


def geometry_stamp_dict(geometry: WindowGeometry) -> dict:
    """The geometry fields the fixtures pin, as a comparable dict."""
    return {key: geometry.to_dict()[key] for key in STAMP_FIELDS}


STAMP_FIELDS = (
    "mode",
    "policy",
    "test_purpose",
    "first_admissible_feed_receipt",
    "entry_timestamp",
    "information_cutoff",
    "decision_timestamp",
    "outcome_start",
    "outcome_end",
    "matched_window_start",
    "matched_window_end",
    "full_session_return_used",
)

#: geometry field name -> fixture field name (the fixtures use the schema names).
FIXTURE_KEY = {"policy": "delayed_entry_policy"}


def assert_geometry_matches_case(geometry: WindowGeometry, case: dict) -> None:
    for field in STAMP_FIELDS:
        key = FIXTURE_KEY.get(field, field)
        assert geometry.to_dict()[field] == case[key], f"{field}: {geometry.to_dict()[field]!r} != {case[key]!r}"


# --- Appendix C clock rows (design App C ~L1152): base + 5 derived ----------------

APP_C_ROWS = [
    ("base_t0", "2026-09-28T13:32:14Z"),
    ("plus_60s_entry", "2026-09-28T13:33:14Z"),
    ("plus_900s_entry", "2026-09-28T13:47:14Z"),
    ("ny_0935_et", "2026-09-28T13:35:00Z"),
    ("ny_1600_et", "2026-09-28T20:00:00Z"),
    ("next_rth_open", "2026-09-29T13:30:00Z"),
]


@pytest.mark.parametrize("row,expected", APP_C_ROWS, ids=[r[0] for r in APP_C_ROWS])
def test_app_c_row(row: str, expected: str) -> None:
    print(f"APP_C rows={len(APP_C_ROWS)} tested={len(APP_C_ROWS)}")
    cal = main_calendar()
    if row == "base_t0":
        assert to_utc_stamp(parse_utc(T0)) == expected
    elif row == "plus_60s_entry":
        got = compute_window_geometry(T0, "plus_60s", cal, bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z")
        assert to_utc_stamp(got.entry_timestamp) == expected
    elif row == "plus_900s_entry":
        got = compute_window_geometry(T0, "plus_900s", cal, bars=week_bars())
        assert to_utc_stamp(got.entry_timestamp) == expected
    elif row == "ny_0935_et":
        assert to_utc_stamp(datetime(2026, 9, 28, 13, 35, tzinfo=timezone.utc)) == expected
        assert to_ny_local("2026-09-28T13:35:00Z") == "2026-09-28 09:35:00"
    elif row == "ny_1600_et":
        assert to_utc_stamp(datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)) == expected
        assert to_ny_local("2026-09-28T20:00:00Z") == "2026-09-28 16:00:00"
    elif row == "next_rth_open":
        got = compute_window_geometry(T0, "next_rth_open", cal)
        assert to_utc_stamp(got.entry_timestamp) == expected
        got2 = compute_window_geometry(T0, "plus_60s", cal, bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z")
        assert to_utc_stamp(got2.next_rth_open_utc) == expected


# --- case 5.6: 09:35 at-origin (plus_60s) exact boundaries -------------------------


def test_case_5_6_exact_boundaries() -> None:
    case = load_case("W_obs_0935_at_origin")
    geometry = compute_window_geometry(
        case["first_admissible_feed_receipt"],
        case["delayed_entry_policy"],
        main_calendar(),
        bars=week_bars(),
        decision_timestamp=case["decision_timestamp"],
    )
    assert_geometry_matches_case(geometry, case)
    build = build_observation_window(
        source_fact_id=case["source_fact_id"],
        target_company_id=case["target_company_id"],
        first_admissible_feed_receipt=case["first_admissible_feed_receipt"],
        policy=case["delayed_entry_policy"],
        calendar=main_calendar(),
        bars=week_bars(),
        decision_timestamp=case["decision_timestamp"],
        absolute_response=case["absolute_response"],
        residual_response=case["residual_response"],
        residual_fit=case["residual_fit"],
        peer_set=case["peer_set"],
        coincident_events=case["coincident_events"],
        observed_at=case["observed_at"],
        source_available_at=case["source_available_at"],
        display_summary=case["display_summary"],
    )
    validate_record(build.record)
    assert build.record["attribution_state"] == case["attribution_state"]
    assert build.record["coincident_events"] == case["coincident_events"]
    # seat default Q7: last completed bar with end <= cutoff 13:33:14Z
    assert build.geometry.at_origin_reference_bar is not None
    assert to_utc_stamp(build.geometry.at_origin_reference_bar.end_utc) == "2026-09-28T13:30:00Z"
    assert build.geometry.first_outcome_bar is not None
    assert to_utc_stamp(build.geometry.first_outcome_bar.end_utc) == "2026-09-28T13:35:00Z"
    assert build.geometry.at_origin_reference_bar.end_utc <= build.geometry.information_cutoff


# --- case 5.7: 16:00 landmark (outcome starts next RTH open) -----------------------


def test_case_5_7_exact_boundaries() -> None:
    case = load_case("W_obs_1600_landmark")
    geometry = compute_window_geometry(
        case["first_admissible_feed_receipt"], case["delayed_entry_policy"], main_calendar()
    )
    assert_geometry_matches_case(geometry, case)
    build = build_observation_window(
        source_fact_id=case["source_fact_id"],
        target_company_id=case["target_company_id"],
        first_admissible_feed_receipt=case["first_admissible_feed_receipt"],
        policy=case["delayed_entry_policy"],
        calendar=main_calendar(),
        absolute_response=case["absolute_response"],
        residual_response=case["residual_response"],
        residual_fit=case["residual_fit"],
        peer_set=case["peer_set"],
        coincident_events=case["coincident_events"],
        observed_at=case["observed_at"],
        source_available_at=case["source_available_at"],
        display_summary=case["display_summary"],
    )
    validate_record(build.record)
    assert build.record["attribution_state"] == case["attribution_state"]
    # the landmark outcome starts at the NEXT RTH open and ends at that close
    assert build.record["outcome_start"] == "2026-09-29T13:30:00Z"
    assert build.record["outcome_end"] == "2026-09-29T20:00:00Z"
    # 5.7's residual fit ends exactly AT the cutoff: <= is legal (V_FIT_CUTOFF)
    assert build.record["residual_fit"]["fit_end"] == build.record["information_cutoff"]
    # matched window: session law (X4), k=1 — the session before the anchor (the
    # cutoff's own Monday session), i.e. Friday 2026-09-25, not the frozen Saturday
    assert build.record["matched_window_start"] == "2026-09-25T13:30:00Z"
    assert build.record["matched_window_end"] == "2026-09-25T20:00:00Z"


# --- case 5.5: coincident events => ambiguous attribution (fixture rule) -----------


def test_case_5_5_coincident_fixture_rule() -> None:
    case = load_case("W_obs_coincident_ambiguous")
    geometry = compute_window_geometry(
        case["first_admissible_feed_receipt"], case["delayed_entry_policy"], main_calendar(), bars=week_bars()
    )
    assert_geometry_matches_case(geometry, case)
    build = build_observation_window(
        source_fact_id=case["source_fact_id"],
        target_company_id=case["target_company_id"],
        first_admissible_feed_receipt=case["first_admissible_feed_receipt"],
        policy=case["delayed_entry_policy"],
        calendar=main_calendar(),
        bars=week_bars(),
        absolute_response=case["absolute_response"],
        residual_response=case["residual_response"],
        residual_fit=case["residual_fit"],
        peer_set=case["peer_set"],
        coincident_events=case["coincident_events"],  # the 13:40Z event, before the cutoff
        observed_at=case["observed_at"],
        source_available_at=case["source_available_at"],
        display_summary=case["display_summary"],
    )
    validate_record(build.record)
    # fixture rule: observed_at 13:40Z inside [t0, outcome_end] is coincident
    assert build.record["coincident_events"] == case["coincident_events"]
    assert build.record["attribution_state"] == "ambiguous_coincident"


def test_coincident_classifier_bounds() -> None:
    events = [
        {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa01", "company_id": TARGET, "observed_at": "2026-09-28T13:40:00Z"},
        {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa02", "company_id": TARGET, "observed_at": "2026-09-28T13:32:13Z"},  # before t0
        {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa03", "company_id": TARGET, "observed_at": "2026-09-28T20:00:01Z"},  # after outcome_end
        {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa04", "company_id": "cik:0000937966", "observed_at": "2026-09-28T14:00:00Z"},  # peer: kept
        {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa05", "company_id": "cik:0000320193", "observed_at": "2026-09-28T14:00:00Z"},  # stranger: dropped
    ]
    from engine.news_impact.observation import classify_coincident_events

    kept = classify_coincident_events(events, TARGET, peer_member_ids=PEER_SET["member_ids"], t0=T0, outcome_end="2026-09-28T20:00:00Z")
    assert [e["fact_id"] for e in kept] == [
        "fact_aaaaaaaaaaaaaaaaaaaaaa01",
        "fact_aaaaaaaaaaaaaaaaaaaaaa04",
    ]


# --- DST weeks --------------------------------------------------------------------


def test_dst_spring_forward_week() -> None:
    cal = weekday_calendar(date(2026, 3, 2), date(2026, 3, 13))
    t0 = "2026-03-06T14:32:14Z"  # Friday 09:32:14 ET, still EST (UTC-5)
    nxt = compute_window_geometry(t0, "next_rth_open", cal)
    assert to_utc_stamp(nxt.entry_timestamp) == "2026-03-09T13:30:00Z"  # Monday open, now EDT (UTC-4)
    landmark = compute_window_geometry(t0, "same_session_close_1600_et", cal)
    assert to_utc_stamp(landmark.entry_timestamp) == "2026-03-06T21:00:00Z"  # 16:00 ET in EST
    plus_one = compute_window_geometry(t0, "next_rth_open_plus_one_session", cal)
    assert to_utc_stamp(plus_one.entry_timestamp) == "2026-03-09T13:30:00Z"  # session after Friday = Monday (EDT)


def test_dst_fall_back_week() -> None:
    cal = weekday_calendar(date(2026, 10, 26), date(2026, 11, 6))
    t0 = "2026-10-30T13:32:14Z"  # Friday 09:32:14 ET, still EDT (UTC-4)
    nxt = compute_window_geometry(t0, "next_rth_open", cal)
    assert to_utc_stamp(nxt.entry_timestamp) == "2026-11-02T14:30:00Z"  # Monday open, now EST (UTC-5)
    plus_one = compute_window_geometry(t0, "next_rth_open_plus_one_session", cal)
    assert to_utc_stamp(plus_one.entry_timestamp) == "2026-11-02T14:30:00Z"
    # The 16:00 ET landmark with defaults: the cutoff is Fri 10-30 20:00Z = the Friday
    # close, so the anchor is Friday and the matched window is Thursday 10-29 (EDT):
    # same ET wall times as the Monday outcome, so the UTC duration stays 6.5h across
    # the fall-back (the session-counted law absorbs the DST change).
    landmark = compute_window_geometry(t0, "same_session_close_1600_et", cal)
    assert to_utc_stamp(landmark.entry_timestamp) == "2026-10-30T20:00:00Z"  # 16:00 ET in EDT
    assert to_utc_stamp(landmark.outcome_start) == "2026-11-02T14:30:00Z"  # Monday open in EST
    assert to_utc_stamp(landmark.outcome_end) == "2026-11-02T21:00:00Z"  # Monday close in EST
    assert to_utc_stamp(landmark.matched_window_start) == "2026-10-29T13:30:00Z"  # Thursday open in EDT
    assert to_utc_stamp(landmark.matched_window_end) == "2026-10-29T20:00:00Z"  # <= Friday 20:00Z cutoff


# --- early close day ---------------------------------------------------------------


def early_close_calendar() -> dict:
    # 2026-11-26 Thanksgiving absent (holiday); 2026-11-27 13:00 ET early close (EST => 18:00Z)
    return weekday_calendar(
        date(2026, 11, 23),
        date(2026, 11, 30),
        early={"2026-11-27": "13:00:00"},
        drop={"2026-11-26"},
    )


def test_early_close_at_origin_window_end() -> None:
    bars = five_min_bars("2026-11-27", "14:30:00", "18:00:00")
    geometry = compute_window_geometry(
        "2026-11-27T15:10:00Z", "plus_60s", early_close_calendar(), bars=bars, decision_timestamp="2026-11-27T15:30:00Z"
    )
    assert geometry.session_date == "2026-11-27"
    assert to_utc_stamp(geometry.outcome_end) == "2026-11-27T18:00:00Z"  # 13:00 ET early close, not 21:00Z
    assert to_utc_stamp(geometry.information_cutoff) == "2026-11-27T15:11:00Z"


def test_early_close_landmark_policy_uses_1600et_stamp() -> None:
    # in-session on the early-close day: the policy is named for 16:00 ET (documented reading)
    geometry = compute_window_geometry("2026-11-27T15:10:00Z", "same_session_close_1600_et", early_close_calendar())
    assert to_utc_stamp(geometry.entry_timestamp) == "2026-11-27T21:00:00Z"
    # after the 13:00 ET close: no session contains T0; the next session-date 16:00 ET wins
    geometry2 = compute_window_geometry("2026-11-27T19:30:00Z", "same_session_close_1600_et", early_close_calendar())
    assert to_utc_stamp(geometry2.entry_timestamp) == "2026-11-27T21:00:00Z"


# --- matched window: session-counted law (X4) ----------------------------------------


def test_matched_window_skips_holiday() -> None:
    # Friday 2026-09-25 dropped (holiday): the k=1 session before the Monday anchor is
    # Thursday 09-24, and the matched window keeps the outcome's ET wall times.
    cal = weekday_calendar(date(2026, 9, 21), date(2026, 10, 2), drop={"2026-09-25"})
    geometry = compute_window_geometry(
        T0, "plus_60s", cal,
        bars=five_min_bars("2026-09-28", "13:00:00", "20:00:00"),
        decision_timestamp="2026-09-28T13:35:00Z",
    )
    assert to_utc_stamp(geometry.matched_window_start) == "2026-09-24T13:35:00Z"
    assert to_utc_stamp(geometry.matched_window_end) == "2026-09-24T20:00:00Z"


def test_matched_window_skips_early_close() -> None:
    # Thanksgiving week: 11-26 absent, 11-27 closes 13:00 ET.  The Monday 11-30 outcome
    # is [14:35Z, 21:00Z] (EST); the Friday candidate's 16:00 ET end misses the 13:00
    # close and 11-26 is absent, so the matched window is Wednesday 11-25 with the same
    # ET wall times as the outcome (16:00 ET = 21:00Z in EST).
    cal = weekday_calendar(
        date(2026, 11, 23), date(2026, 12, 4), early={"2026-11-27": "13:00:00"}, drop={"2026-11-26"}
    )
    geometry = compute_window_geometry(
        "2026-11-30T14:32:14Z", "plus_60s", cal,
        bars=five_min_bars("2026-11-30", "14:00:00", "21:00:00"),
        decision_timestamp="2026-11-30T14:35:00Z",
    )
    assert to_utc_stamp(geometry.matched_window_start) == "2026-11-25T14:35:00Z"
    assert to_utc_stamp(geometry.matched_window_end) == "2026-11-25T21:00:00Z"


def test_landmark_outcome_end_same_session_after_early_close() -> None:
    # 16:00 ET landmark on the early-close Friday: the cutoff (21:00Z) is outside the
    # 13:00 ET session, so with Monday bars the outcome starts at the first Monday bar
    # end and ends at MONDAY's close, not the 12-01 close (X4 landmark outcome-end fix).
    geometry = compute_window_geometry(
        "2026-11-27T15:10:00Z", "same_session_close_1600_et", early_close_calendar(),
        bars=five_min_bars("2026-11-30", "14:30:00", "21:00:00"),
    )
    assert to_utc_stamp(geometry.outcome_start) == "2026-11-30T14:35:00Z"
    assert to_utc_stamp(geometry.outcome_end) == "2026-11-30T21:00:00Z"  # NOT the 12-01 close
    assert to_utc_stamp(geometry.matched_window_start) == "2026-11-25T14:35:00Z"
    assert to_utc_stamp(geometry.matched_window_end) == "2026-11-25T21:00:00Z"


def test_matched_window_sessions_back_k2() -> None:
    # k=2 moves the matched window exactly one more session back than k=1 (Friday
    # 09-25 -> Thursday 09-24) on the 5.6 case.
    case = load_case("W_obs_0935_at_origin")
    geometry = compute_window_geometry(
        case["first_admissible_feed_receipt"], case["delayed_entry_policy"], main_calendar(),
        bars=week_bars(), decision_timestamp=case["decision_timestamp"], matched_window_sessions_back=2,
    )
    assert to_utc_stamp(geometry.matched_window_start) == "2026-09-24T13:35:00Z"
    assert to_utc_stamp(geometry.matched_window_end) == "2026-09-24T20:00:00Z"


@pytest.mark.parametrize("k", [0, 11, -1, True, False, 1.0, "1"])
def test_bad_matched_window_sessions(k) -> None:
    # bool is an int subclass but is rejected alongside out-of-range and non-int shapes
    with pytest.raises(ObservationError) as excinfo:
        compute_window_geometry(
            T0, "plus_60s", main_calendar(), bars=week_bars(),
            decision_timestamp="2026-09-28T13:35:00Z", matched_window_sessions_back=k,
        )
    assert excinfo.value.code == "BAD_MATCHED_WINDOW_SESSIONS"


def test_matched_window_no_session_when_calendar_too_short() -> None:
    # Monday 09-28 is the calendar's first session, so it is the anchor itself and no
    # session exists before it: MATCHED_WINDOW_NO_SESSION, not a silent window.
    cal = weekday_calendar(date(2026, 9, 28), date(2026, 10, 2))
    with pytest.raises(ObservationError) as excinfo:
        compute_window_geometry(
            T0, "plus_60s", cal,
            bars=five_min_bars("2026-09-28", "13:00:00", "20:00:00"),
            decision_timestamp="2026-09-28T13:35:00Z",
        )
    assert excinfo.value.code == "MATCHED_WINDOW_NO_SESSION"


@pytest.mark.parametrize("policy", DELAYED_ENTRY_POLICIES)
def test_matched_window_invariants_every_policy(policy: str) -> None:
    # decision defaults to the entry stamp, in-session for every at-origin arm; the
    # landmark arms ignore it (their decision IS the landmark entry).
    cal = TradingCalendar.from_mapping(main_calendar())
    geometry = compute_window_geometry(T0, policy, main_calendar(), bars=week_bars())
    assert geometry.matched_window_end <= geometry.information_cutoff
    assert (geometry.matched_window_end - geometry.matched_window_start) == (
        geometry.outcome_end - geometry.outcome_start
    )
    for stamp in (geometry.matched_window_start, geometry.matched_window_end):
        session = cal.session_containing(stamp)
        assert session is not None, f"{to_utc_stamp(stamp)} is not inside a calendar session"
        assert session.open_utc <= stamp <= session.close_utc


# --- a bar closing exactly at the cutoff counts (seat default Q7) ------------------


def test_bar_closing_exactly_at_cutoff_is_reference() -> None:
    bars = [
        {"start": "2026-09-28T13:23:14Z", "end": "2026-09-28T13:28:14Z"},
        {"start": "2026-09-28T13:28:14Z", "end": "2026-09-28T13:33:14Z"},  # ends exactly at the cutoff
        {"start": "2026-09-28T13:33:14Z", "end": "2026-09-28T13:38:14Z"},
    ]
    geometry = compute_window_geometry(T0, "plus_60s", main_calendar(), bars=bars, decision_timestamp="2026-09-28T13:35:00Z")
    assert to_utc_stamp(geometry.information_cutoff) == "2026-09-28T13:33:14Z"
    assert geometry.at_origin_reference_bar is not None
    assert to_utc_stamp(geometry.at_origin_reference_bar.end_utc) == "2026-09-28T13:33:14Z"
    assert geometry.first_outcome_bar is not None
    assert to_utc_stamp(geometry.first_outcome_bar.end_utc) == "2026-09-28T13:38:14Z"


# --- origin on a non-session day ----------------------------------------------------


def test_origin_on_non_session_day() -> None:
    t0 = "2026-09-26T15:00:00Z"  # Saturday 11:00 ET
    cal = main_calendar()
    assert to_utc_stamp(compute_window_geometry(t0, "next_rth_open", cal).entry_timestamp) == "2026-09-28T13:30:00Z"
    plus_one = compute_window_geometry(t0, "next_rth_open_plus_one_session", cal)
    assert to_utc_stamp(plus_one.entry_timestamp) == "2026-09-29T13:30:00Z"
    assert plus_one.test_purpose == "stale_news_treatment"
    assert plus_one.stale_news_treatment is True
    assert to_utc_stamp(compute_window_geometry(t0, "same_session_close_1600_et", cal).entry_timestamp) == "2026-09-28T20:00:00Z"
    # at_origin arm from a Saturday T0: entry is plain +60s, but the decision must
    # land inside an RTH session (Monday 09:35 ET here) — decision >= cutoff holds,
    # and the at-origin reference bar is Friday's last completed bar.
    plus_60 = compute_window_geometry(t0, "plus_60s", cal, bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z")
    assert to_utc_stamp(plus_60.entry_timestamp) == "2026-09-26T15:01:00Z"
    assert to_utc_stamp(plus_60.outcome_start) == "2026-09-28T13:35:00Z"
    assert plus_60.at_origin_reference_bar is not None
    assert to_utc_stamp(plus_60.at_origin_reference_bar.end_utc) == "2026-09-25T20:00:00Z"


def test_in_session_plus_one_equals_next_open_documented_degeneracy() -> None:
    # For an in-session T0 the design text makes plus_one equal next_rth_open (docstring law).
    cal = main_calendar()
    a = compute_window_geometry(T0, "next_rth_open", cal)
    b = compute_window_geometry(T0, "next_rth_open_plus_one_session", cal)
    assert a.entry_timestamp == b.entry_timestamp


# --- landmark next_rth_open arm: outcome starts at the next bar after the cutoff ----


def test_landmark_next_rth_open_arm_with_bars() -> None:
    geometry = compute_window_geometry(T0, "next_rth_open", main_calendar(), bars=week_bars())
    assert to_utc_stamp(geometry.entry_timestamp) == "2026-09-29T13:30:00Z"  # Tuesday open (Monday's open < T0)
    assert to_utc_stamp(geometry.outcome_start) == "2026-09-29T13:35:00Z"  # first bar ending after the cutoff
    assert to_utc_stamp(geometry.outcome_end) == "2026-09-29T20:00:00Z"  # that session's close
    assert geometry.mode == "landmark"
    assert geometry.test_purpose == "gap_open"


def test_landmark_next_rth_open_arm_without_bars() -> None:
    geometry = compute_window_geometry(T0, "next_rth_open", main_calendar())
    # cutoff is Tuesday's open (Monday's open precedes T0); no bars injected, so the
    # outcome window is the next full session AFTER the cutoff: Wednesday 2026-09-30.
    assert to_utc_stamp(geometry.outcome_start) == "2026-09-30T13:30:00Z"
    assert to_utc_stamp(geometry.outcome_end) == "2026-09-30T20:00:00Z"


# --- every emitted window validates against the frozen schema ------------------------


@pytest.mark.parametrize(
    "policy",
    ["feed_receipt", "plus_60s", "plus_900s", "next_rth_open", "same_session_close_1600_et", "next_rth_open_plus_one_session"],
)
def test_every_policy_emits_schema_valid_window(policy: str) -> None:
    build = build_observation_window(
        source_fact_id=SOURCE_FACT,
        target_company_id=TARGET,
        first_admissible_feed_receipt=T0,
        policy=policy,
        calendar=main_calendar(),
        bars=week_bars(),
        residual_fit=RESIDUAL_FIT,
        peer_set=PEER_SET,
        observed_at="2026-09-28T20:00:00Z",
    )
    validate_record(build.record)
    assert build.record["delayed_entry_policy"] == policy
    assert build.record["mode"] in ("at_origin", "landmark")
    assert build.record["full_session_return_used"] is False
    assert re.fullmatch(r"obs_[0-9a-f]{24}", build.record["observation_id"])


# --- determinism: permuted input order gives byte-identical canonical JSON ------------


def test_determinism_permuted_inputs() -> None:
    base = dict(
        source_fact_id=SOURCE_FACT,
        target_company_id=TARGET,
        first_admissible_feed_receipt=T0,
        policy="plus_900s",
        calendar=main_calendar(),
        bars=week_bars(),
        absolute_response={
            "form": "measured",
            "unit": "simple_return",
            "value": 0.018,
            "window_start": "2026-09-28T13:47:14Z",
            "window_end": "2026-09-28T20:00:00Z",
        },
        residual_fit=RESIDUAL_FIT,
        peer_set=PEER_SET,
        coincident_events=[
            {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa01", "company_id": TARGET, "observed_at": "2026-09-28T13:40:00Z"},
            {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa02", "company_id": "cik:0000937966", "observed_at": "2026-09-28T13:50:00Z"},
        ],
        observed_at="2026-09-28T20:00:00Z",
    )
    first = build_observation_window(**base)
    permuted = dict(base)
    permuted["calendar"] = {"sessions": dict(reversed(list(main_calendar()["sessions"].items())))}
    permuted["bars"] = list(reversed(week_bars()))
    permuted["coincident_events"] = list(reversed(base["coincident_events"]))
    second = build_observation_window(**permuted)
    assert first.canonical_json == second.canonical_json
    assert first.record["observation_id"] == second.record["observation_id"]
    assert canonical_json(json.loads(first.canonical_json)) == first.canonical_json
    # attribution: both events coincide with the window => ambiguous
    assert first.record["attribution_state"] == "ambiguous_coincident"


def test_observation_id_stable_and_versioned() -> None:
    build = build_observation_window(
        source_fact_id=SOURCE_FACT,
        target_company_id=TARGET,
        first_admissible_feed_receipt=T0,
        policy="plus_60s",
        calendar=main_calendar(),
        bars=week_bars(),
        decision_timestamp="2026-09-28T13:35:00Z",
        observed_at="2026-09-28T20:00:00Z",
    )
    assert build.observation_version == OBSERVATION_VERSION
    again = build_observation_window(
        source_fact_id=SOURCE_FACT,
        target_company_id=TARGET,
        first_admissible_feed_receipt=T0,
        policy="plus_60s",
        calendar=main_calendar(),
        bars=week_bars(),
        decision_timestamp="2026-09-28T13:35:00Z",
        observed_at="2026-09-28T20:00:00Z",
    )
    assert build.record["observation_id"] == again.record["observation_id"]
    validate_record(build.record)


# --- W3-R3: forbidden keys are stripped at ingest and recorded ------------------------


def test_forbidden_keys_stripped_and_recorded() -> None:
    build = build_observation_window(
        source_fact_id=SOURCE_FACT,
        target_company_id=TARGET,
        first_admissible_feed_receipt=T0,
        policy="plus_60s",
        calendar=main_calendar(),
        bars=week_bars(),
        decision_timestamp="2026-09-28T13:35:00Z",
        absolute_response={
            "form": "measured",
            "unit": "simple_return",
            "value": 0.012,
            "confidence": 0.9,
            "window_start": "2026-09-28T13:35:00Z",
            "window_end": "2026-09-28T20:00:00Z",
        },
        residual_fit={
            "method": "ols_trailing_pre_cutoff",
            "fit_start": "2026-07-01T20:00:00Z",
            "fit_end": "2026-09-25T20:00:00Z",
            "legs": [{"factor_id": "market", "fitted_coefficient": 1.1, "window_bars": 60, "score": 3}],
            "unused_collinear_factors": [],
        },
        peer_set=PEER_SET,
        coincident_events=[
            {"fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaa01", "company_id": TARGET, "observed_at": "2026-09-28T13:40:00Z", "sentiment": "bad"}
        ],
        observed_at="2026-09-28T20:00:00Z",
    )
    assert "absolute_response.confidence" in build.stripped_fields
    assert "residual_fit.legs[0].score" in build.stripped_fields
    assert "coincident_events.sentiment" in build.stripped_fields
    assert "confidence" not in canonical_json(build.record)
    validate_record(build.record)  # schema-valid after stripping


# --- error paths: every code in CODES has a trigger asserting the exact string --------


def _code_triggers():
    cal = main_calendar()
    return {
        "BAD_TIMESTAMP": lambda: parse_utc(datetime(2026, 9, 28, 13, 32)),
        "BAD_BAR": lambda: Bar(parse_utc("2026-09-28T13:30:00Z"), parse_utc("2026-09-28T13:30:00Z")),
        "BAR_OUT_OF_ORDER": lambda: compute_window_geometry(
            T0, "plus_60s", cal,
            bars=[{"start": "2026-09-28T13:00:00Z", "end": "2026-09-28T13:30:00Z"}] * 2,
            decision_timestamp="2026-09-28T13:35:00Z",
        ),
        "CALENDAR_BAD_SHAPE": lambda: TradingCalendar.from_mapping({"dates": {}}),
        "CALENDAR_EMPTY": lambda: TradingCalendar.from_mapping({"sessions": {}}),
        "CALENDAR_BAD_SESSION": lambda: TradingCalendar.from_mapping(
            {"sessions": {"2026-09-28": {"open": "16:00:00", "close": "09:30:00"}}}
        ),
        "UNKNOWN_POLICY": lambda: compute_window_geometry(T0, "plus_1h", cal),
        "NO_NEXT_SESSION": lambda: compute_window_geometry("2026-10-02T21:00:00Z", "next_rth_open", cal),
        "DECISION_OUTSIDE_SESSION": lambda: compute_window_geometry(
            T0, "plus_60s", cal, decision_timestamp="2026-09-28T21:30:00Z"  # Monday 17:30 ET: after the close, no session
        ),
        "DECISION_BEFORE_CUTOFF": lambda: compute_window_geometry(
            T0, "plus_60s", cal, bars=week_bars(), decision_timestamp="2026-09-28T13:32:14Z"
        ),
        "WINDOW_USES_FULL_SESSION": lambda: compute_window_geometry(
            "2026-09-28T13:00:00Z", "feed_receipt", cal, bars=week_bars(), decision_timestamp="2026-09-28T13:30:00Z"
        ),
        "REFERENCE_BAR_MISSING": lambda: compute_window_geometry(
            T0, "plus_60s", cal,
            bars=[{"start": "2026-09-28T13:40:00Z", "end": "2026-09-28T13:45:00Z"}],
            decision_timestamp="2026-09-28T13:35:00Z",
        ),
        "MATCHED_WINDOW_AFTER_CUTOFF": lambda: WindowGeometry(
            policy="plus_60s",
            mode="at_origin",
            test_purpose="source_delay",
            stale_news_treatment=False,
            t0=parse_utc("2026-09-28T13:32:14Z"),
            entry_timestamp=parse_utc("2026-09-28T13:33:14Z"),
            information_cutoff=parse_utc("2026-09-28T13:33:14Z"),
            decision_timestamp=parse_utc("2026-09-28T13:35:00Z"),
            outcome_start=parse_utc("2026-09-28T13:35:00Z"),
            outcome_end=parse_utc("2026-09-28T20:00:00Z"),
            matched_window_start=parse_utc("2026-09-28T13:35:00Z"),
            matched_window_end=parse_utc("2026-09-28T20:00:00Z"),  # after the cutoff
            next_rth_open_utc=parse_utc("2026-09-29T13:30:00Z"),
            session_date="2026-09-28",
        ),
        "BAD_MATCHED_WINDOW_SESSIONS": lambda: compute_window_geometry(
            T0, "plus_60s", cal, bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z",
            matched_window_sessions_back=0,
        ),
        "MATCHED_WINDOW_NO_SESSION": lambda: compute_window_geometry(
            T0, "plus_60s", weekday_calendar(date(2026, 9, 28), date(2026, 10, 2)),
            bars=five_min_bars("2026-09-28", "13:00:00", "20:00:00"),
            decision_timestamp="2026-09-28T13:35:00Z",
        ),
        "CUTOFF_VIOLATION": lambda: compute_window_geometry(
            T0, "plus_60s", cal, bars=week_bars(), decision_timestamp="2026-09-28T20:00:00Z"  # decision == close
        ),
        "RESPONSE_WINDOW_MISMATCH": lambda: build_observation_window(
            source_fact_id=SOURCE_FACT, target_company_id=TARGET,
            first_admissible_feed_receipt=T0, policy="plus_60s", calendar=cal,
            bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z",
            absolute_response={"form": "measured", "unit": "simple_return", "value": 0.1,
                               "window_start": "2026-09-28T13:30:00Z", "window_end": "2026-09-28T20:00:00Z"},
            observed_at="2026-09-28T20:00:00Z",
        ),
        "BAD_RESIDUAL_FIT": lambda: build_observation_window(
            source_fact_id=SOURCE_FACT, target_company_id=TARGET,
            first_admissible_feed_receipt=T0, policy="plus_60s", calendar=cal,
            bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z",
            residual_fit={"method": "ols", "fit_start": "2026-07-01T20:00:00Z", "fit_end": "2026-09-25T20:00:00Z", "legs": []},
            observed_at="2026-09-28T20:00:00Z",
        ),
        "FIT_END_AFTER_CUTOFF": lambda: build_observation_window(
            source_fact_id=SOURCE_FACT, target_company_id=TARGET,
            first_admissible_feed_receipt=T0, policy="plus_60s", calendar=cal,
            bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z",
            residual_fit=dict(RESIDUAL_FIT, fit_end="2026-09-28T14:00:00Z"),
            observed_at="2026-09-28T20:00:00Z",
        ),
        "BAD_PEER_SET": lambda: build_observation_window(
            source_fact_id=SOURCE_FACT, target_company_id=TARGET,
            first_admissible_feed_receipt=T0, policy="plus_60s", calendar=cal,
            bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z",
            peer_set=dict(PEER_SET, member_ids=[TARGET, "cik:0000937966"]),
            observed_at="2026-09-28T20:00:00Z",
        ),
        "BAD_COINCIDENT_EVENT": lambda: build_observation_window(
            source_fact_id=SOURCE_FACT, target_company_id=TARGET,
            first_admissible_feed_receipt=T0, policy="plus_60s", calendar=cal,
            bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z",
            coincident_events=[{"company_id": TARGET, "observed_at": "2026-09-28T13:40:00Z"}],
            observed_at="2026-09-28T20:00:00Z",
        ),
        "RECORD_SCHEMA_INVALID": lambda: validate_record({"schema": "observation_window.v1"}),
    }


@pytest.mark.parametrize("code", sorted(CODES))
def test_error_code_exact_string(code: str) -> None:
    triggers = _code_triggers()
    assert set(triggers) == set(CODES), "every code needs exactly one trigger"
    with pytest.raises(ObservationError) as excinfo:
        triggers[code]()
    assert excinfo.value.code == code
    assert str(excinfo.value).startswith(f"{code}:")


# --- determinism deliverable: no clock reads in the module source ----------------------


def test_residual_factor_set_is_exactly_the_v1_pair() -> None:
    from engine.news_impact.observation import RESIDUAL_FACTOR_SET, UNUSED_COLLINEAR_FACTORS

    geometry = compute_window_geometry(T0, "plus_60s", main_calendar(), bars=week_bars(), decision_timestamp="2026-09-28T13:35:00Z")
    assert set(RESIDUAL_FACTOR_SET) == {"market", "documented_peer_residual"}
    assert geometry.residual_factor_ids == tuple(sorted(RESIDUAL_FACTOR_SET))
    assert UNUSED_COLLINEAR_FACTORS == ("sector", "mag7", "gpu_theme")


def test_strip_forbidden_keys_direct() -> None:
    from engine.news_impact.observation import strip_forbidden_keys

    clean, stripped = strip_forbidden_keys({"a": 1, "confidence": 0.5, "nested": [{"score": 2, "ok": True}]}, "root")
    assert clean == {"a": 1, "nested": [{"ok": True}]}
    assert stripped == ["root.confidence", "root.nested[0].score"]


def test_window_build_to_dict_roundtrip() -> None:
    build = build_observation_window(
        source_fact_id=SOURCE_FACT,
        target_company_id=TARGET,
        first_admissible_feed_receipt=T0,
        policy="plus_60s",
        calendar=main_calendar(),
        bars=week_bars(),
        decision_timestamp="2026-09-28T13:35:00Z",
        observed_at="2026-09-28T20:00:00Z",
    )
    dumped = build.to_dict()
    assert dumped["record"] == build.record
    assert dumped["geometry"]["policy"] == "plus_60s"
    assert dumped["observation_version"] == OBSERVATION_VERSION


def test_module_source_has_no_clock_reads() -> None:
    source = (SRC / "engine" / "news_impact" / "observation.py").read_text(encoding="utf-8")
    for banned in ("datetime.now", "time.time", "date.today", "import random"):
        assert banned not in source, banned
