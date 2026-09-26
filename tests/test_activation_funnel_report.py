"""The CA1A machine consumer, proven on fixed fixtures with EXACT expectations.

The report is the wave's real consumer: if these numbers can drift, the producers are
unmeasurable and the wave is an infrastructure-only patch — the thing the commission
explicitly prohibits (research/commercial_activation/CLAUDE_ORCHESTRATOR_HANDOFF_V1
_CA1A_EVENT_SPINE_20260903.md §15.22-24). So every assertion here is exact (counts,
ratios, the leak sentence's bytes), and the null-contract cases (missing denominator,
unknown identity) are pinned as NULLS, never zeros.
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "activation_funnel_report", ROOT / "scripts" / "activation_funnel_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AFR = _load_module()

SINCE = datetime(2026, 9, 1, tzinfo=timezone.utc)
UNTIL = datetime(2026, 9, 2, tzinfo=timezone.utc)


def _row(type_: str, sid: str, *, meta=None, ua="Mozilla/5.0", visitor="v-1",
         user=None, created="2026-09-01T12:00:00+00:00", client="2026-09-01T11:59:58+00:00"):
    return {"type": type_, "session_id": sid, "meta": meta, "ua": ua,
            "visitor_id": visitor, "user_id": user,
            "created_at": created, "client_ts": client}


def _full_session(sid: str, visitor: str = "v-1") -> list[dict]:
    return [
        _row("session_start", sid, visitor=visitor),
        _row("intelligence.viewed", sid, visitor=visitor,
             meta={"surface": "flow_velocity", "surface_group": "read",
                   "tier_seen": "anon", "rows_visible": 3}),
        _row("personal.act", sid, visitor=visitor,
             meta={"act": "watchlist_add", "surface": "watchlist"}),
        _row("watchlist.saved", sid, visitor=visitor,
             meta={"symbol_count": 3, "list_count": 1, "storage": "local"}),
    ]


def test_exact_stage_counts_and_ratios_on_a_fixed_fixture():
    rows = (
        _full_session("s-full")
        + [_row("session_start", "s-visit-only")]
        + [_row("session_start", "s-value-only"),
           _row("intelligence.viewed", "s-value-only",
                meta={"surface": "flow_velocity", "surface_group": "read",
                      "tier_seen": "anon", "rows_visible": 1})]
        + [_row("session_start", "s-act-no-save"),
           _row("intelligence.viewed", "s-act-no-save",
                meta={"surface": "flow_velocity", "surface_group": "read",
                      "tier_seen": "anon", "rows_visible": 2}),
           _row("personal.act", "s-act-no-save",
                meta={"act": "watchlist_add", "surface": "watchlist"})]
    )
    rep = AFR.build_report(rows, SINCE, UNTIL, set(), set())
    assert rep["stage_sessions"] == {
        "visit": 4, "intelligence_viewed": 3, "personal_act": 2, "watchlist_saved": 1,
    }
    assert rep["conversion"] == {
        "intelligence_viewed_over_visit": 0.75,
        "personal_act_over_intelligence_viewed": round(2 / 3, 4),
        "watchlist_saved_over_personal_act": 0.5,
    }
    assert rep["rows_admitted"] == len(rows)


def test_largest_leak_sentence_is_deterministic_and_exact():
    rows = (
        _full_session("s-1")
        + [_row("session_start", f"s-visit-{i}") for i in range(3)]
    )
    rep = AFR.build_report(rows, SINCE, UNTIL, set(), set())
    # visit=4 -> value=1 loses 3; every later transition loses 0.
    assert rep["largest_leak"] == (
        "Largest leak: visit -> intelligence_viewed: 4 -> 1 sessions "
        "(25.0% continue, 3 lost)."
    )


def test_missing_denominator_reports_null_not_zero():
    rep = AFR.build_report([], SINCE, UNTIL, set(), set())
    assert rep["stage_sessions"]["visit"] == 0
    for ratio in rep["conversion"].values():
        assert ratio is None, "a ratio with no denominator must be null, never 0"
    assert rep["largest_leak"] == "No leak measurable: no stage has a non-zero denominator."


def test_saved_below_three_symbols_does_not_count_as_saved_stage():
    rows = [_row("session_start", "s-2"),
            _row("watchlist.saved", "s-2",
                 meta={"symbol_count": 2, "list_count": 1, "storage": "local"})]
    rep = AFR.build_report(rows, SINCE, UNTIL, set(), set())
    assert rep["stage_sessions"]["watchlist_saved"] == 0


def test_bot_and_internal_exclusion_is_versioned_and_counted():
    rows = (
        _full_session("s-real")
        + [_row("session_start", "s-bot", ua="Mozilla/5.0 (compatible; Googlebot/2.1)")]
        + [_row("session_start", "s-internal", visitor="v-internal")]
        + [dict(r, user_id="11111111-1111-1111-1111-111111111111")
           for r in _full_session("s-staff", visitor="v-9")]
    )
    rep = AFR.build_report(
        rows, SINCE, UNTIL,
        internal_users={"11111111-1111-1111-1111-111111111111"},
        internal_visitors={"v-internal"},
    )
    assert rep["filter_version"] == "commercial_activation_filter.v1"
    assert rep["stage_sessions"]["visit"] == 1          # only s-real survives
    assert rep["rows_dropped"]["bot_ua"] == 1
    assert rep["rows_dropped"]["internal_visitor"] == 1
    assert rep["rows_dropped"]["internal_user"] == 4    # the whole staff session


def test_ingestion_window_is_enforced_and_reported():
    rows = (_full_session("s-in")
            + [_row("session_start", "s-late", created="2026-09-03T00:00:00+00:00")])
    rep = AFR.build_report(rows, SINCE, UNTIL, set(), set())
    assert rep["stage_sessions"]["visit"] == 1
    assert rep["rows_dropped"]["outside_window"] == 1
    assert rep["ingestion_cutoff"] == {
        "since": "2026-09-01T00:00:00+00:00", "until": "2026-09-02T00:00:00+00:00",
    }
    assert rep["occurrence_observed_max"] == "2026-09-01T11:59:58+00:00"


def test_rows_without_session_id_never_mint_a_stage():
    rows = [_row("intelligence.viewed", "", meta={"surface": "flow_velocity",
            "surface_group": "read", "tier_seen": "anon", "rows_visible": 1})]
    rep = AFR.build_report(rows, SINCE, UNTIL, set(), set())
    assert rep["stage_sessions"]["intelligence_viewed"] == 0


def test_report_is_byte_deterministic():
    rows = _full_session("s-det")
    a = json.dumps(AFR.build_report(rows, SINCE, UNTIL, set(), set()), sort_keys=True)
    b = json.dumps(AFR.build_report(list(rows), SINCE, UNTIL, set(), set()), sort_keys=True)
    assert a == b


# Ordered mode is opt-in: preserve the frozen v1 activity report above.
def _event(kind, sid, second, *, site="macro", **kwargs):
    meta = {"symbol_count": 3} if kind == "watchlist.saved" else {}
    row = _row(kind, sid, meta=meta,
               client=f"2026-09-01T11:59:{second:02d}+00:00", **kwargs)
    row["site"] = site
    return row


def _ordered_cli(tmp_path, rows):
    import subprocess
    import sys
    source = tmp_path / "synthetic-events.json"
    source.write_text(json.dumps(rows), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/activation_funnel_report.py"),
         "--input", str(source), "--since", SINCE.isoformat(),
         "--until", UNTIL.isoformat(), "--ordered"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, "Ordered CLI must be available: " + result.stderr
    return json.loads(result.stdout)


def test_ordered_cli_does_not_convert_between_disjoint_sessions(tmp_path):
    rows = [_event("intelligence.viewed", "A", 1),
            _event("personal.act", "B", 2),
            _event("watchlist.saved", "B", 3)]
    report = _ordered_cli(tmp_path, rows)
    assert report["stage_sessions"] == {
        "visit": 2, "intelligence_viewed": 1, "personal_act": 0, "watchlist_saved": 0}
    assert report["conversion"]["personal_act_over_intelligence_viewed"] == 0
    assert report["conversion"]["watchlist_saved_over_personal_act"] is None
    assert report["activity_stage_sessions"]["personal_act"] == 1


def test_ordered_cli_rejects_reverse_occurrence_sequence(tmp_path):
    rows = [_event("watchlist.saved", "A", 1),
            _event("personal.act", "A", 2),
            _event("intelligence.viewed", "A", 3)]
    report = _ordered_cli(tmp_path, rows)
    assert report["stage_sessions"]["personal_act"] == 0
    assert report["stage_sessions"]["watchlist_saved"] == 0
    assert report["activity_stage_sessions"]["watchlist_saved"] == 1


def test_ordered_cli_counts_forward_sequence(tmp_path):
    report = _ordered_cli(tmp_path, [
        _event("intelligence.viewed", "A", 1),
        _event("personal.act", "A", 2), _event("watchlist.saved", "A", 3)])
    assert report["report"] == "activation_funnel_report.ordered.v2"
    assert set(report["stage_sessions"].values()) == {1}
    assert set(report["conversion"].values()) == {1.0}


def test_ordered_cli_never_uses_array_order_to_resolve_tied_times(tmp_path):
    report = _ordered_cli(tmp_path, _full_session("all-tied"))
    assert report["stage_sessions"] == {
        "visit": 1, "intelligence_viewed": 1, "personal_act": 0, "watchlist_saved": 0}
    assert report["diagnostics"]["mixed_stage_timestamp_groups"] == 1


def _ordered(rows, users=None, visitors=None):
    return AFR.build_report(rows, SINCE, UNTIL, users or set(), visitors or set(), ordered=True)


def _sequence(sid="A", *, site="macro"):
    return [_event("intelligence.viewed", sid, 1, site=site),
            _event("personal.act", sid, 2, site=site),
            _event("watchlist.saved", sid, 3, site=site)]


def test_ordered_does_not_merge_equal_session_strings_across_sites():
    rows = [_event("intelligence.viewed", "shared", 1, site="macro"),
            _event("personal.act", "shared", 2, site="terminal"),
            _event("watchlist.saved", "shared", 3, site="terminal")]
    report = _ordered(rows)
    assert report["stage_sessions"] == {
        "visit": 2, "intelligence_viewed": 1, "personal_act": 0, "watchlist_saved": 0}
    assert report["measurement"]["cross_session_or_person_stitching"] is False


def test_ordered_missing_site_does_not_join_a_known_site():
    rows = _sequence()
    rows[0].pop("site")
    assert _ordered(rows)["stage_sessions"]["personal_act"] == 0


def test_ordered_same_visitor_does_not_join_different_sessions():
    rows = [_event("intelligence.viewed", "first", 1),
            _event("personal.act", "second", 2),
            _event("watchlist.saved", "second", 3)]
    assert _ordered(rows)["stage_sessions"]["watchlist_saved"] == 0


def test_ordered_uses_occurrence_time_not_array_or_arrival_order():
    rows = _sequence()
    rows[0]["created_at"] = "2026-09-01T14:00:00Z"
    rows[1]["created_at"] = "2026-09-01T13:00:00Z"
    rows[2]["created_at"] = "2026-09-01T12:00:00Z"
    report = _ordered(list(reversed(rows)))
    assert report["stage_sessions"]["watchlist_saved"] == 1
    assert report["measurement"]["order_clock"] == "client_ts_with_explicit_timezone"


def test_ordered_timezone_offsets_are_compared_as_instants():
    rows = _sequence()
    for row, stamp in zip(rows, ["2026-09-01T07:00:00-04:00", "2026-09-01T11:01:00Z",
                                 "2026-09-01T12:02:00+01:00"]):
        row["client_ts"] = stamp
    assert _ordered(rows)["stage_sessions"]["watchlist_saved"] == 1


def test_ordered_invalid_or_missing_clocks_do_not_use_ingestion_fallback():
    for bad in (None, "", "not-a-date", "2026-09-01T11:59:02", 42):
        rows = _sequence()
        rows[1]["client_ts"] = bad
        report = _ordered(rows)
        assert report["stage_sessions"]["personal_act"] == 0, repr(bad)
        assert report["activity_stage_sessions"]["personal_act"] == 1
        assert report["diagnostics"]["rows_with_unqualified_occurrence_time"] == 1


def test_ordered_clocks_after_the_cutoff_are_not_completed_actions():
    rows = _sequence()
    rows[2]["client_ts"] = "2026-09-03T00:00:00Z"
    report = _ordered(rows)
    assert report["stage_sessions"]["personal_act"] == 1
    assert report["stage_sessions"]["watchlist_saved"] == 0
    assert report["activity_stage_sessions"]["watchlist_saved"] == 1
    assert report["diagnostics"]["rows_with_occurrence_after_cutoff"] == 1
    assert report["occurrence_observed_max"] == "2026-09-03T00:00:00+00:00"


def test_ordered_occurrence_before_window_is_not_relabelled_as_new_activity():
    rows = _sequence()
    for row in rows:
        row["client_ts"] = row["client_ts"].replace("2026-09-01", "2026-08-31")
    report = _ordered(rows)
    assert report["stage_sessions"]["watchlist_saved"] == 1
    assert report["occurrence_observed_max"].startswith("2026-08-31")
    assert report["ingestion_cutoff"]["since"].startswith("2026-09-01")
    assert "admitted_rows_only" in report["measurement"]["coverage"]


def test_ordered_ingestion_window_still_excludes_late_arriving_rows():
    rows = _sequence()
    rows[2]["created_at"] = "2026-09-03T00:00:00Z"
    report = _ordered(rows)
    assert report["rows_dropped"]["outside_window"] == 1
    assert report["stage_sessions"]["watchlist_saved"] == 0


def test_ordered_tie_does_not_become_order_through_uuid_or_list_sort():
    import itertools
    rows = _sequence()
    for index, row in enumerate(rows):
        row["client_ts"] = "2026-09-01T11:59:00Z"
        row["id"] = f"00000000-0000-0000-0000-{index:012d}"
    results = [json.dumps(_ordered(list(p)), sort_keys=True) for p in itertools.permutations(rows)]
    assert len(set(results)) == 1
    assert _ordered(rows)["stage_sessions"]["personal_act"] == 0


def test_ordered_can_complete_after_an_earlier_out_of_order_attempt():
    rows = [_event("personal.act", "A", 0)] + _sequence()
    rows.insert(0, _event("watchlist.saved", "A", 0))
    assert _ordered(rows)["stage_sessions"]["watchlist_saved"] == 1


def test_ordered_later_action_can_resolve_a_previous_tie():
    rows = [_event("intelligence.viewed", "A", 1),
            _event("personal.act", "A", 1),
            _event("personal.act", "A", 2),
            _event("watchlist.saved", "A", 3)]
    assert _ordered(rows)["stage_sessions"]["watchlist_saved"] == 1


def test_ordered_same_time_act_and_save_do_not_complete_save():
    rows = _sequence()
    rows[-1]["client_ts"] = rows[-2]["client_ts"]
    report = _ordered(rows)
    assert report["stage_sessions"]["personal_act"] == 1
    assert report["stage_sessions"]["watchlist_saved"] == 0


def test_ordered_repeated_events_do_not_inflate_session_counts():
    rows = _sequence()
    assert _ordered(rows * 5)["stage_sessions"] == _ordered(rows)["stage_sessions"]


def test_ordered_saved_event_cannot_skip_missing_prior_steps():
    report = _ordered([_event("watchlist.saved", "A", 3)])
    assert report["stage_sessions"] == {
        "visit": 1, "intelligence_viewed": 0, "personal_act": 0, "watchlist_saved": 0}
    assert report["conversion"]["personal_act_over_intelligence_viewed"] is None


def test_ordered_empty_input_retains_null_denominators():
    report = _ordered([])
    assert set(report["stage_sessions"].values()) == {0}
    assert all(x is None for x in report["conversion"].values())
    assert "no stage has a denominator" in report["largest_leak"]


def test_ordered_invalid_saved_counts_are_not_silently_coerced():
    for bad in (True, 3.5, "3", None):
        rows = _sequence()
        rows[2]["meta"]["symbol_count"] = bad
        report = _ordered(rows)
        assert report["stage_sessions"]["watchlist_saved"] == 0
        assert report["diagnostics"]["saved_rows_with_unqualified_count"] == 1


def test_ordered_below_threshold_remains_unsaved():
    rows = _sequence()
    rows[2]["meta"]["symbol_count"] = 2
    assert _ordered(rows)["stage_sessions"]["watchlist_saved"] == 0


def test_ordered_absent_session_is_not_an_anonymous_shared_bucket():
    rows = _sequence("")
    report = _ordered(rows)
    assert report["stage_sessions"]["visit"] == 0
    assert report["diagnostics"]["rows_without_recorded_session"] == 3


def test_ordered_exclusions_are_inherited_before_aggregation():
    rows = _sequence("real")
    rows += [dict(row, ua="Googlebot") for row in _sequence("bot")]
    rows += [dict(row, user_id="operator") for row in _sequence("staff")]
    rows += [dict(row, visitor_id="excluded") for row in _sequence("excluded-visitor")]
    report = _ordered(rows, {"operator"}, {"excluded"})
    assert report["stage_sessions"]["watchlist_saved"] == 1
    assert report["rows_dropped"]["bot_ua"] == 3
    assert report["rows_dropped"]["internal_user"] == 3
    assert report["rows_dropped"]["internal_visitor"] == 3
    assert report["filter_version"] == "commercial_activation_filter.v1"


def test_ordered_input_and_private_values_are_not_projected():
    import copy
    rows = _sequence("private-session-123")
    for row in rows:
        row["visitor_id"] = "private-visitor-456"
        row["user_id"] = "private-user-789"
        row["path"] = "/private-research-context"
    before = copy.deepcopy(rows)
    report = _ordered(rows)
    output = json.dumps(report, sort_keys=True) + AFR._to_markdown(report)
    assert rows == before
    for text in ("private-session-123", "private-visitor-456", "private-user-789", "/private-research-context"):
        assert text not in output


def test_ordered_result_is_permutation_invariant():
    import random
    rows = _sequence("A") + _sequence("B") + [_event("personal.act", "C", 4)]
    expected = json.dumps(_ordered(rows), sort_keys=True)
    rng = random.Random(20)
    for _ in range(30):
        rng.shuffle(rows)
        assert json.dumps(_ordered(rows), sort_keys=True) == expected


def test_ordered_matches_independent_exhaustive_subsequence_oracle():
    import itertools
    import random
    rng = random.Random(6838)
    names = ["intelligence.viewed", "personal.act", "watchlist.saved"]
    for _ in range(150):
        pairs = [(rng.randrange(3), rng.randrange(6)) for _ in range(rng.randrange(1, 12))]
        rows = [_event(names[stage], "A", stamp) for stage, stamp in pairs]
        stages = [[stamp for stage, stamp in pairs if stage == i] for i in range(3)]
        expected = [1]
        for length in range(1, 4):
            expected.append(int(any(all(a < b for a, b in zip(seq, seq[1:]))
                                    for seq in itertools.product(*stages[:length]))))
        observed = list(_ordered(rows)["stage_sessions"].values())
        assert observed == expected, (pairs, observed, expected)


def test_ordered_ratios_are_nested_not_over_one():
    rows = _sequence("A")
    rows += [_event("personal.act", f"B{i}", 1) for i in range(10)]
    report = _ordered(rows)
    assert report["activity_stage_sessions"]["personal_act"] == 11
    assert report["stage_sessions"]["personal_act"] == 1
    assert all(v is None or 0 <= v <= 1 for v in report["conversion"].values())


def test_ordered_markdown_explains_measurement_not_causality():
    text = AFR._to_markdown(_ordered(_sequence()))
    assert "Ordered prefix" in text and "Independent activity" in text
    assert "not a resolved person" in text
    assert "not complete journeys or causal attribution" in text
    assert "0 lost" not in text


def test_ordered_cli_writes_real_json_and_markdown(tmp_path):
    source, target, markdown = [tmp_path / x for x in ("input.json", "result.json", "result.md")]
    source.write_text(json.dumps(_sequence()), encoding="utf-8")
    assert AFR.main(["--input", str(source), "--since", SINCE.isoformat(),
                     "--until", UNTIL.isoformat(), "--ordered", "--out", str(target),
                     "--markdown", str(markdown)]) == 0
    result = json.loads(target.read_text())
    assert result["stage_sessions"]["watchlist_saved"] == 1
    assert "Observed ordered activation" in markdown.read_text()


def test_ordered_file_mode_does_not_call_network(tmp_path, monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("Offline file mode must not access the network")
    monkeypatch.setattr(AFR.urllib.request, "urlopen", refused)
    source = tmp_path / "input.json"
    source.write_text("[]")
    assert AFR.main(["--input", str(source), "--since", SINCE.isoformat(),
                     "--until", UNTIL.isoformat(), "--ordered"]) == 0


def test_ordered_invalid_window_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="until precedes since"):
        AFR.build_report([], UNTIL, SINCE, set(), set(), ordered=True)


def test_explicit_unordered_is_identical_to_existing_default():
    rows = _full_session("tied-original")
    assert AFR.build_report(rows, SINCE, UNTIL, set(), set(), ordered=False) == \
        AFR.build_report(rows, SINCE, UNTIL, set(), set())
    assert AFR.build_report(rows, SINCE, UNTIL, set(), set())["report"] == "activation_funnel_report.v1"
