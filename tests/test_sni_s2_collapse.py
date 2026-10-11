"""S2 collapse (IL §3, A22): bundles, programmes, absorption, cross-issuer.

Pins with synthetic events: BABA(adr_baba)+9988(hkd_9988) rows of one
occurrence collapse into ONE episode whose members span both counters (leg
outcomes are columns of one episode, never extra N); overlapping windows are
absorbed per IL §3 step 4 with no chaining; same-day shocks across issuer
groups stay two episodes sharing one cluster key (IL §8).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_collapse import run_collapse  # noqa: E402
from s2_seal import GRADE_HORIZONS  # noqa: E402
from s2_clocklaw import session_dates  # noqa: E402
import lib.nyse_calendar as nyse_calendar  # noqa: E402
import lib.hk_calendar as hk_calendar  # noqa: E402

US = session_dates(nyse_calendar)
HK = session_dates(hk_calendar)


def _row(rid, issuer, family, t, s_us, s_hk, counter, quality="PUBLISHER_STATED"):
    return {"id": rid, "issuer_key": issuer, "family": family,
            "category": family, "title": "T", "t_avail_utc": t,
            "t_avail_quality": quality, "s_us": s_us, "s_hk": s_hk,
            "evidence_pointer": f"synthetic#{rid}", "disposition": "SELECTED",
            "listed_exclusion_reason": None}


def test_cross_counter_occurrence_is_one_episode_with_two_counter_members() -> None:
    # one occurrence reported on the HKD counter and the ADS (dup report)
    rows = [
        _row("h1", "alibaba", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "hkd_9988"),
        _row("b1", "alibaba", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "adr_baba"),
    ]
    res = run_collapse(rows, [], US, HK, GRADE_HORIZONS)
    assert res["counts"]["kept_after_step0"] == 2
    evs = [e for e in res["events"] if e.issuer_key == "alibaba"]
    assert len(evs) == 1, "duplicate reports of one occurrence must merge"
    assert sorted(evs[0].member_ids) == ["b1", "h1"]
    eps = res["per_h"][5]["episodes"]
    assert len(eps) == 1
    assert eps[0].absorbed_count == 0


def test_overlapping_windows_absorb_only_into_the_opener() -> None:
    # E1 at T, E3 at T+9 (IL §6): inside W_21 but outside W_5
    rows = [
        _row("a1", "alibaba", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "adr_baba"),
        _row("a9", "alibaba", "regulatory_material",
             "2026-05-22T11:00:00+00:00", "2026-05-22", "2026-05-25", "adr_baba"),
    ]
    res = run_collapse(rows, [], US, HK, GRADE_HORIZONS)
    e5 = res["per_h"][5]["episodes"]
    e21 = res["per_h"][21]["episodes"]
    assert len(e5) == 2 and all(e.absorbed_count == 0 for e in e5)
    assert len(e21) == 1
    assert e21[0].absorbed_count == 1
    assert e21[0].absorbed[0].member_ids == ["a9"]


def test_no_chaining_only_opener_absorbs() -> None:
    # B at T+3 would be absorbed by opener A(T); C at T+5 must NOT chain
    # through B: it is judged against A's window only, and at h=5 lies outside
    # if the calendar distance exceeds 5 sessions.
    rows = [
        _row("A", "alibaba", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "adr_baba"),
        _row("B", "alibaba", "results", "2026-05-14T11:00:00+00:00",
             "2026-05-14", "2026-05-15", "adr_baba"),
        _row("C", "alibaba", "results", "2026-05-21T11:00:00+00:00",
             "2026-05-21", "2026-05-22", "adr_baba"),
    ]
    res = run_collapse(rows, [], US, HK, GRADE_HORIZONS)
    e5 = res["per_h"][5]["episodes"]
    openers = [e.opener.member_ids[0] for e in e5]
    assert openers == ["A", "C"]  # C opens; B was absorbed by A's window only
    absorbed = {m.member_ids[0] for e in e5 for m in e.absorbed}
    assert absorbed == {"B"}


def test_same_day_cross_issuer_two_episodes_one_cluster() -> None:
    rows = [
        _row("al", "alibaba", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "adr_baba"),
        _row("tn", "tencent", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "hkd_0700"),
    ]
    res = run_collapse(rows, [], US, HK, GRADE_HORIZONS)
    eps = res["per_h"][5]["episodes"]
    assert len(eps) == 2  # never merged (IL §3 step 5)
    assert {ep.opener.s_us for ep in eps} == {"2026-05-13"}  # one cluster key


def test_step0_excludes_inadmissible_quality_and_lists_it() -> None:
    rows = [
        _row("good", "alibaba", "results", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "adr_baba"),
        _row("evt", "alibaba", "results", None, None, None, "adr_baba",
             quality="EVENT_DATE"),
    ]
    res = run_collapse(rows, [], US, HK, GRADE_HORIZONS)
    assert res["counts"]["kept_after_step0"] == 1
    excl = res["counts"]["excluded_and_listed"]
    assert any(e["id"] == "evt" and "EVENT_DATE" in e["reason"] for e in excl)


def test_programme_exclusion_is_listed_and_never_counted() -> None:
    rows = [
        _row("p1", "alibaba", "capital_action", "2026-05-13T09:30:00+00:00",
             "2026-05-13", "2026-05-14", "hkd_9988"),
        _row("p2", "alibaba", "capital_action", "2026-05-14T09:30:00+00:00",
             "2026-05-14", "2026-05-15", "hkd_9988"),
    ]
    programmes = [{"key": "placing:alibaba", "issuer_key": "alibaba",
                   "counter": "hkd_9988", "member_ids": ["p1", "p2"]}]
    excl = [{"match": {"programme": "placing:alibaba"},
             "reason": "E0 gap 10 (synthetic)",
             "family_scope": "capital_action"}]
    res = run_collapse(rows, programmes, US, HK, GRADE_HORIZONS,
                       event_exclusions=excl)
    assert res["counts"]["events_after_step2"] == 1  # one programme = one event
    assert res["counts"]["events_after_step2_and_step3"] == 0  # then excluded
    assert any(e["family_scope"] == "capital_action"
               for e in res["counts"]["excluded_and_listed"])
