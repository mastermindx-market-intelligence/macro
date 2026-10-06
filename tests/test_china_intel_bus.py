"""China Intelligence transmission bus — contract tests (pure, network-free).

The bus is a context-only fan-in of four surface JSON emits. It must ALWAYS return a
valid, schema-versioned, JSON-serializable briefing — even with zero surfaces built —
and NEVER raise into a build.
"""
from __future__ import annotations

import json

from engine import china_intel_bus as bus


def test_briefing_shape(monkeypatch):
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)   # no surfaces built
    b = bus.briefing(asof="2026-06-20")
    assert b["schema"] == "china_intel.briefing.v6"
    assert b["is_context_only"] is True
    assert b["asof"] == "2026-06-20"
    for k in ("news", "policy", "altdata", "radar", "analysis"):
        assert k in b
    # v2 hoisted synthesis keys always present
    for k in ("conviction", "cross_surface", "flagged_tickers", "what_changed", "salience",
              "surface_asof", "max_staleness_days"):
        assert k in b
    # v6: analogs key always present (may be None)
    assert "analogs" in b
    assert isinstance(b["digest"], str) and b["digest"]
    assert b["disclaimer"] and b["disclaimer_zh"]


def test_briefing_is_json_serializable():
    json.dumps(bus.briefing(), default=str)  # must not raise


def test_digest_text_synthesis_led():
    b = {
        "analysis": {
            "what_matters": [{"label_en": "Brokers divergence (positive)", "detail_en": "stacked"}],
            "conviction": [{"sector_en": "Brokers", "radar_sign": "positive",
                            "context_conviction": 34, "surfaces_confirming": ["radar", "news"]}],
            "what_changed": {"stance_change": {"from": "neutral", "to": "easing"}},
        },
        "news": {"band": "supportive", "sentiment_z": 0.8, "n_events_7d": 12,
                 "flagged_baskets": [{"name_en": "Brokers", "hits": 3}]},
        "policy": {"pboc_stance": "easing", "lpr_1y": 3.0, "lpr_5y": 3.5, "rrr": 6.0},
        "altdata": {"accumulate": [{"name": "中信证券", "ticker": "600030.SS"}]},
        "radar": {"divergences": [{"signal_en": "PBoC easing", "sector": "Brokers", "sign": "positive"}],
                  "ledger": {"grade": "unproven"}},
    }
    txt = bus._digest_text(b)
    assert "WHAT MATTERS MOST" in txt
    assert "CHANGED TODAY" in txt and "neutral→easing" in txt
    assert "STACKED READS" in txt and "Brokers" in txt
    assert "中信证券(600030.SS)" in txt          # names, not bare codes
    assert "unproven" in txt


def test_digest_text_empty_when_nothing_present():
    assert "no surfaces" in bus._digest_text({}).lower()



# ── CIE-07: coverage-adjusted institutional-visit metadata discovery ──────────

def _visit_row(aid, code, published, *, name="测试公司", exchange="SZ",
               visitor_class="not_yet_available", title="机构调研活动记录表",
               recorded=None):
    return {
        "announcement_id": aid,
        "sec_code": code,
        "sec_name": name,
        "exchange": exchange,
        "title": title,
        "source_published_at": published,
        "system_recorded_at": recorded or published,
        "visitor_class": visitor_class,
    }


def _kind_labeler(title):
    return ("site visit", "特定对象调研") if "特定对象" in str(title) \
        else ("investor visit", "机构调研")


def test_visit_discovery_first_seen_requires_no_preexisting_observation():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A1", "000001", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-09-15",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    assert snap["n_recent_companies"] == 1
    assert snap["n_first_observed_recent"] == 1
    row = snap["examples"][0]
    assert row["first_seen_state"] == "first_observed_since_coverage_start"
    # The plane has not observed a full 90d baseline before this 30d window.
    assert row["baseline_state"] == "insufficient_observed_history"
    assert row["recent_vs_baseline_rate_ratio"] is None
    assert snap["global_negative_authority"] is True


def test_visit_discovery_missing_earlier_observation_clock_cannot_claim_first_seen():
    early = _visit_row(
        "A-missing", "000011", "2026-10-01T09:00:00+08:00",
        recorded="2026-10-01T02:00:00+00:00",
    )
    early["system_recorded_at"] = None
    later = _visit_row(
        "A-later", "000011", "2026-10-02T09:00:00+08:00",
        recorded="2026-10-02T02:00:00+00:00",
    )

    snap = bus._visit_discovery_snapshot(
        [early, later],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-09-15",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )

    assert snap["n_recent_companies"] == 1
    assert snap["n_first_observed_recent"] == 0
    row = snap["examples"][0]
    assert row["recent_count"] == 2
    assert row["first_seen_state"] == "observation_clock_unavailable"
    assert row["first_observed_system_day"] is None
    assert row["observation_clock_complete"] is False



def test_visit_discovery_malformed_full_observation_clock_cannot_claim_first_seen():
    row = _visit_row(
        "A-malformed", "000012", "2026-10-02T09:00:00+08:00",
        recorded="2026-10-02T99:99:99+99:99",
    )
    snap = bus._visit_discovery_snapshot(
        [row],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-09-15",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    assert snap["n_recent_companies"] == 1
    assert snap["n_first_observed_recent"] == 0
    out = snap["examples"][0]
    assert out["first_seen_state"] == "observation_clock_unavailable"
    assert out["first_observed_system_day"] is None
    assert out["observation_clock_complete"] is False


def test_visit_discovery_malformed_health_clock_cannot_authorize_absence():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A-health", "000013", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03garbage",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "last_success_clock_invalid"




def test_visit_discovery_malformed_coverage_stamp_cannot_authorize_absence():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A-coverage", "000014", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01garbage",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["coverage_start"] is None
    assert snap["owner_clock_state"] == "invalid"
    assert "coverage_start_invalid" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "coverage_start_invalid"


def test_visit_discovery_malformed_last_attempt_is_not_treated_as_absent():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A-attempt", "000015", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03garbage",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["owner_clock_state"] == "invalid"
    assert "last_attempt_clock_invalid" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "last_attempt_clock_invalid"




def test_visit_discovery_ok_health_missing_attempt_is_incomplete_receipt():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A-noattempt", "000026", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert "ok_health_receipt_incomplete" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "ok_health_receipt_incomplete"
    assert snap["n_first_observed_recent"] == 0


def test_visit_discovery_unusable_source_clock_preserves_explicit_unknown_company():
    row = _visit_row(
        "A-badsource", "000027", "2026-10-02T09:00:00+08:00",
        recorded="2026-10-02T10:00:00+00:00",
    )
    row["source_published_at"] = "not-a-source-clock"

    snap = bus._visit_discovery_snapshot(
        [row],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )

    assert "row_source_clock_invalid" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "row_source_clock_invalid"
    assert len(snap["examples"]) == 1
    out = snap["examples"][0]
    assert out["sec_code"] == "000027"
    assert out["coverage_state"] == "unknown_source_clock"
    assert out["source_clock_state"] == "invalid"
    assert out["first_seen_state"] == "unknown_source_clock"
    assert out["baseline_state"] == "blocked_source_clock_invalid"
    assert out["recent_count"] == 0



def test_visit_discovery_partial_or_naive_owner_timestamps_fail_closed():
    for bad in (
        "2026-10-03T01",
        "2026-10-03T01:00",
        "2026-10-03T01:00:00",
    ):
        snap = bus._visit_discovery_snapshot(
            [_visit_row(
                "A-partial", "000016", "2026-10-02T09:00:00+08:00",
                recorded=bad,
            )],
            health={
                "status": "ok",
                "last_success_utc": bad,
            },
            coverage_start="2026-01-01",
            open_scoped_codes=set(),
            has_unscoped_open=False,
            kind_labeler=_kind_labeler,
            reference_day=bus.date(2026, 10, 3),
        )
        assert snap["global_negative_authority"] is False
        assert "last_success_clock_invalid" in snap["owner_clock_errors"]
        assert snap["n_first_observed_recent"] == 0
        row = snap["examples"][0]
        assert row["first_seen_state"] == "unknown_owner_clock_order_invalid"
        assert row["first_observed_system_day"] is None


def test_visit_discovery_attempt_before_success_same_day_fails_at_instant_precision():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A-order", "000017", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T23:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert "last_attempt_before_last_success" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["examples"][0]["baseline_state"] == \
        "blocked_owner_clock_order_invalid"
    assert snap["examples"][0]["first_seen_state"] == \
        "unknown_owner_clock_order_invalid"


def test_visit_discovery_missing_last_success_cannot_measure_quiet_baseline():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("A-nosuccess", "000018", "2026-10-02T09:00:00+08:00")],
        health={"status": "ok"},
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "ok_health_receipt_incomplete"
    row = snap["examples"][0]
    assert row["baseline_state"] == "blocked_owner_clock_order_invalid"
    assert row["first_seen_state"] == "unknown_owner_clock_order_invalid"
    assert snap["n_first_observed_recent"] == 0


def test_visit_discovery_unknown_exception_coverage_cannot_claim_first_seen():
    visits = [_visit_row("A-except", "000019", "2026-10-02T09:00:00+08:00")]

    unreadable = bus._visit_discovery_snapshot(
        visits,
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        exception_ledger_readable=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert unreadable["examples"][0]["first_seen_state"] == \
        "unknown_exception_ledger_unreadable"
    assert unreadable["n_first_observed_recent"] == 0

    unscoped = bus._visit_discovery_snapshot(
        visits,
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=True,
        exception_ledger_readable=True,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert unscoped["examples"][0]["first_seen_state"] == \
        "unknown_unscoped_coverage_exception"
    assert unscoped["n_first_observed_recent"] == 0



def test_visit_discovery_row_newer_than_health_receipt_preserves_positive_but_blocks_authority():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "A-newer", "000020", "2026-10-03T09:00:00+08:00",
            recorded="2026-10-03T12:00:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T10:00:00+00:00",
            "last_attempt_utc": "2026-10-03T10:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )

    assert snap["n_recent_companies"] == 1
    assert "row_observation_after_health_receipt" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "row_observation_after_health_receipt"
    row = snap["examples"][0]
    assert row["recent_count"] == 1
    assert row["first_seen_state"] == "unknown_owner_clock_order_invalid"
    assert row["baseline_state"] == "blocked_owner_clock_order_invalid"
    assert snap["n_first_observed_recent"] == 0



def test_visit_discovery_next_day_post_receipt_positive_stays_visible_without_authority():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "A-next-day", "000021", "2026-10-03T09:00:00+00:00",
            recorded="2026-10-03T12:00:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-02T23:00:00+00:00",
            "last_attempt_utc": "2026-10-02T23:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )

    assert snap["observation_end"] == "2026-10-03"
    assert snap["n_recent_companies"] == 1
    assert snap["examples"][0]["sec_code"] == "000021"
    assert snap["examples"][0]["recent_count"] == 1
    assert "row_observation_after_health_receipt" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "row_observation_after_health_receipt"
    assert snap["examples"][0]["first_seen_state"] == \
        "unknown_owner_clock_order_invalid"
    assert snap["examples"][0]["baseline_state"] == \
        "blocked_owner_clock_order_invalid"
    assert snap["n_first_observed_recent"] == 0



def test_visit_discovery_unclocked_post_receipt_source_stays_visible_but_blocks_authority():
    row = _visit_row(
        "A-unclocked-late", "000022", "2026-10-03T09:00:00+00:00",
        recorded="2026-10-03T12:00:00+00:00",
    )
    row["system_recorded_at"] = None

    snap = bus._visit_discovery_snapshot(
        [row],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-02T23:00:00+00:00",
            "last_attempt_utc": "2026-10-02T23:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )

    assert snap["observation_end"] == "2026-10-03"
    assert snap["n_recent_companies"] == 1
    assert snap["examples"][0]["sec_code"] == "000022"
    assert snap["examples"][0]["recent_count"] == 1
    assert "row_source_after_health_receipt_without_observation_clock" in \
        snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "row_source_after_health_receipt_without_observation_clock"
    assert snap["examples"][0]["first_seen_state"] == \
        "unknown_owner_clock_order_invalid"
    assert snap["examples"][0]["baseline_state"] == \
        "blocked_owner_clock_order_invalid"
    assert snap["n_first_observed_recent"] == 0



def test_visit_discovery_source_timestamp_uses_utc_reference_domain():
    # 00:30 in Asia/Shanghai is still the prior UTC date. It must not disappear
    # merely because the source-local calendar is one day ahead.
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "A-tz", "000023", "2026-10-06T00:30:00+08:00",
            recorded="2026-10-05T16:31:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-05T16:31:00+00:00",
            "last_attempt_utc": "2026-10-05T16:31:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 5),
    )
    assert snap["n_recent_companies"] == 1
    row = snap["examples"][0]
    assert row["sec_code"] == "000023"
    assert row["recent_count"] == 1
    assert snap["observation_end"] == "2026-10-05"


def test_visit_discovery_observation_before_source_fails_closed_but_keeps_positive():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "A-pre-source", "000024", "2026-10-03T09:00:00+00:00",
            recorded="2026-10-03T08:59:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T10:00:00+00:00",
            "last_attempt_utc": "2026-10-03T10:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["n_recent_companies"] == 1
    assert "row_observation_before_source" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "row_observation_before_source"
    assert snap["n_first_observed_recent"] == 0


def test_visit_discovery_ok_health_requires_equal_attempt_and_success_receipts():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "A-health-mismatch", "000025", "2026-10-03T08:00:00+00:00",
            recorded="2026-10-03T08:30:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-02T23:00:00+00:00",
            "last_attempt_utc": "2026-10-03T09:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["n_recent_companies"] == 1
    assert "ok_health_receipt_mismatch" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == \
        "ok_health_receipt_mismatch"
    assert snap["n_first_observed_recent"] == 0



def test_visit_discovery_keeps_precoverage_source_event_as_positive_observation():
    # First production run can legitimately derive a filing published during
    # its bounded lookback before the write-once coverage-start date. The event
    # stays real positive evidence; only negative/baseline authority is gated.
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "A0", "000010", "2026-09-14T09:00:00+08:00",
            recorded="2026-09-15T02:00:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-09-15T02:00:00+00:00",
            "last_attempt_utc": "2026-09-15T02:00:00+00:00",
        },
        coverage_start="2026-09-15",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        recent_days=30,
        baseline_days=90,
    )
    assert snap["n_rows_observed"] == 1
    assert snap["n_recent_companies"] == 1
    row = snap["examples"][0]
    assert row["earliest_source_published_day"] == "2026-09-14"
    assert row["first_observed_system_day"] == "2026-09-15"
    assert row["first_seen_state"] == "first_observed_since_coverage_start"
    assert row["baseline_state"] == "insufficient_observed_history"


def test_visit_discovery_measures_only_fully_observed_baseline():
    visits = [
        _visit_row("B1", "600001", "2026-07-01T09:00:00+08:00", exchange="SH"),
        _visit_row("B2", "600001", "2026-08-01T09:00:00+08:00", exchange="SH"),
        _visit_row("B3", "600001", "2026-09-20T09:00:00+08:00", exchange="SH"),
        _visit_row("B4", "600001", "2026-09-25T09:00:00+08:00", exchange="SH"),
    ]
    snap = bus._visit_discovery_snapshot(
        visits,
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    row = snap["examples"][0]
    assert row["baseline_state"] == "measured"
    assert row["recent_count"] == 2
    assert row["baseline_count"] == 2
    assert row["recent_activity_higher_than_baseline"] is True
    assert row["rate_comparison"] == "recent_rate_higher"
    assert row["recent_vs_baseline_rate_ratio"] is not None
    assert row["recent_vs_baseline_rate_ratio"] > 1.0
    assert snap["n_measured_baselines"] == 1


def test_visit_discovery_scoped_exception_blocks_company_baseline_not_positive_evidence():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("C1", "000002", "2026-10-01T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes={"000002"},
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    row = snap["examples"][0]
    assert row["recent_count"] == 1
    assert row["coverage_state"] == "unknown_company_exception"
    assert row["first_seen_state"] == "unknown_due_coverage_exception"
    assert row["baseline_state"] == "blocked_company_coverage_exception"
    assert row["baseline_count"] is None
    # A scoped exception does not poison every other company globally.
    assert snap["global_negative_authority"] is True


def test_visit_discovery_unscoped_exception_blocks_global_negative_authority():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("D1", "000003", "2026-10-01T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=True,
        kind_labeler=_kind_labeler,
    )
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "unscoped_coverage_exception"
    assert snap["examples"][0]["baseline_state"] == "blocked_unscoped_coverage_exception"


def test_visit_discovery_stale_ok_health_loses_negative_and_baseline_authority():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("S1", "000099", "2026-09-20T09:00:00+08:00")],
        health={
            "status": "ok",
            "last_success_utc": "2026-09-20T01:00:00+00:00",
            "last_attempt_utc": "2026-09-20T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
        stale_after_days=4,
    )
    assert snap["owner_health_status"] == "ok"
    assert snap["source_status"] == "stale"
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "source_stale"
    assert snap["examples"][0]["baseline_state"] == "unavailable_source_stale"


def test_visit_discovery_future_last_success_fails_closed_without_future_window():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "CLK1", "000088", "2026-10-02T09:00:00+08:00",
            recorded="2026-10-02T10:00:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-04T01:00:00+00:00",
            "last_attempt_utc": "2026-10-04T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["owner_clock_state"] == "invalid"
    assert "last_success_after_reference" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "owner_clock_order_invalid"
    assert snap["observation_end"] == "2026-10-02"
    assert snap["examples"][0]["baseline_state"] == "blocked_owner_clock_order_invalid"


def test_visit_discovery_last_success_before_coverage_fails_closed():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "CLK2", "000089", "2026-10-02T09:00:00+08:00",
            recorded="2026-10-02T10:00:00+00:00",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-08-31T01:00:00+00:00",
            "last_attempt_utc": "2026-10-02T01:00:00+00:00",
        },
        coverage_start="2026-09-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
        reference_day=bus.date(2026, 10, 3),
    )
    assert snap["owner_clock_state"] == "invalid"
    assert "last_success_before_coverage_start" in snap["owner_clock_errors"]
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "owner_clock_order_invalid"
    assert snap["examples"][0]["baseline_state"] == "blocked_owner_clock_order_invalid"


def test_visit_discovery_degraded_source_keeps_positive_evidence_but_no_quiet_baseline():
    snap = bus._visit_discovery_snapshot(
        [_visit_row("E1", "000004", "2026-10-02T09:00:00+08:00")],
        health={
            "status": "upstream_degraded",
            "last_success_utc": "2026-09-28T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    assert snap["n_recent_companies"] == 1
    assert snap["global_negative_authority"] is False
    assert snap["global_negative_authority_blocker"] == "source_health_not_ok"
    assert snap["examples"][0]["baseline_state"] == "unavailable_source_health"


def test_visit_discovery_dedupes_announcement_identity_before_recurrence():
    same = _visit_row("F1", "000005", "2026-10-01T09:00:00+08:00")
    snap = bus._visit_discovery_snapshot(
        [same, dict(same)],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    assert snap["n_rows_observed"] == 1
    assert snap["examples"][0]["recent_count"] == 1


def test_visit_discovery_never_promotes_actor_or_rank_authority():
    snap = bus._visit_discovery_snapshot(
        [_visit_row(
            "G1", "000006", "2026-10-01T09:00:00+08:00",
            visitor_class="institution",
            title="特定对象调研记录",
        )],
        health={
            "status": "ok",
            "last_success_utc": "2026-10-03T01:00:00+00:00",
            "last_attempt_utc": "2026-10-03T01:00:00+00:00",
        },
        coverage_start="2026-01-01",
        open_scoped_codes=set(),
        has_unscoped_open=False,
        kind_labeler=_kind_labeler,
    )
    row = snap["examples"][0]
    # A future body stage may populate a visitor class, but this metadata slice
    # still refuses actor recurrence without that stage's own acceptance receipt.
    assert row["visitor_identity_state"] == "actor_enriched_rows_present"
    assert row["actor_recurrence_state"] == "not_evaluated_without_body_stage_receipt"
    assert row["may_rank"] is False and row["may_trade"] is False
    assert "score" not in row and "rank" not in row
    assert snap["authority"]["may_infer_visitor_identity"] is False
    assert snap["authority"]["may_claim_predictive_edge"] is False


def test_visit_discovery_block_absent_plane_stays_dark(monkeypatch):
    from collectors import china_visits as cv

    monkeypatch.setattr(cv, "read_visits_strict", lambda: [])
    monkeypatch.setattr(cv, "read_coverage_exceptions_strict", lambda: [])
    monkeypatch.setattr(cv, "read_health", lambda: {
        "status": "no_coverage", "detail": "china_visits has never run",
    })
    monkeypatch.setattr(cv, "read_coverage_start", lambda: None)
    assert bus._visit_discovery_block() is None


def test_visit_discovery_block_fails_closed_on_unreadable_owner(monkeypatch):
    from collectors import china_visits as cv

    monkeypatch.setattr(cv, "read_visits_strict", lambda: None)
    monkeypatch.setattr(cv, "read_coverage_exceptions_strict", lambda: [])
    out = bus._visit_discovery_block()
    assert out["source_status"] == "source_failure"
    assert out["global_negative_authority"] is False
    assert out["global_negative_authority_blocker"] == "visit_store_unreadable"
    assert out["examples"] == []


def test_visit_discovery_unreadable_exception_ledger_preserves_positive_rows(monkeypatch):
    from collectors import china_visits as cv

    today = bus.date.today().isoformat()
    row = _visit_row(
        "LEDGER1", "000077", f"{today}T09:00:00+08:00",
        recorded=f"{today}T10:00:00+00:00",
    )
    monkeypatch.setattr(cv, "read_visits_strict", lambda: [row])
    monkeypatch.setattr(cv, "read_coverage_exceptions_strict", lambda: None)
    monkeypatch.setattr(cv, "read_health", lambda: {
        "status": "ok",
        "last_success_utc": f"{today}T11:00:00+00:00",
        "last_attempt_utc": f"{today}T11:00:00+00:00",
    })
    monkeypatch.setattr(cv, "read_coverage_start", lambda: "2026-01-01")

    out = bus._visit_discovery_block()
    assert out is not None
    assert out["exception_ledger_readable"] is False
    assert out["n_recent_companies"] == 1
    assert out["examples"][0]["sec_code"] == "000077"
    assert out["examples"][0]["recent_count"] == 1
    assert out["global_negative_authority"] is False
    assert out["global_negative_authority_blocker"] == \
        "coverage_exception_ledger_unreadable"
    assert out["examples"][0]["baseline_state"] == \
        "blocked_exception_ledger_unreadable"


def test_briefing_exposes_visit_discovery_as_context_surface_only(monkeypatch):
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    monkeypatch.setattr(bus, "_visit_discovery_block", lambda: {
        "schema": "china_visits.discovery_metadata.v1",
        "is_context_only": True,
        "asof": "2026-10-03",
        "authority": {"may_rank": False, "may_trade": False},
        "examples": [],
    })
    b = bus.briefing(asof="2026-10-03")
    assert b["schema"] == "china_intel.briefing.v6"
    assert b["visit_discovery"]["authority"]["may_rank"] is False
    assert "visit_discovery" in b["surfaces_present"]
    assert b["surface_asof"]["visit_discovery"] == "2026-10-03"
    assert b["flagged_tickers"] == []
    assert b["conviction"] == []


# ── v4: policy_phrase block ───────────────────────────────────────────────────

def test_policy_phrase_block_missing_file(monkeypatch):
    """Missing communique_diff/latest.json → block returns None, no exception."""
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    result = bus._policy_phrase_block()
    assert result is None


def test_policy_phrase_block_empty_events(monkeypatch):
    """File present but events=[] (cold-start day) → block present with n=0."""
    payload = {
        "schema": "communique_diff.v1",
        "asof": "2026-07-02",
        "events": [],
        "cold_start_organs": ["pboc", "ndrc"],
        "counts": {"n_events": 0, "n_appeared": 0, "n_dropped": 0,
                   "n_lead_shift": 0, "n_cold_start_organs": 2},
    }
    monkeypatch.setattr(bus, "_read_json", lambda rel: payload if "communique_diff" in rel else None)
    result = bus._policy_phrase_block()
    assert result is not None
    assert result["n_events_recent"] == 0
    assert result["cold_start_organs"] == ["pboc", "ndrc"]
    assert result["is_context_only"] is True


def test_policy_phrase_block_happy_path(monkeypatch):
    """File with recent events → block populated correctly."""
    from datetime import date, timedelta
    today = date.today()
    recent_date = (today - timedelta(days=3)).isoformat()
    payload = {
        "schema": "communique_diff.v1",
        "asof": recent_date,
        "events": [
            {"event_id": "cd_abc", "kind": "APPEARED", "organ": "pboc",
             "phrase": "适度宽松", "gloss": "moderately loose", "domain": "monetary",
             "polarity": 0, "review_status": "PROVISIONAL",
             "asof": recent_date, "evidence_url": "http://pboc.gov.cn/1"},
            {"event_id": "cd_def", "kind": "DROPPED", "organ": "state_council",
             "phrase": "房住不炒", "gloss": "housing not for speculation", "domain": "real_estate",
             "polarity": 0, "review_status": "PROVISIONAL",
             "asof": recent_date, "evidence_url": ""},
        ],
        "cold_start_organs": [],
        "counts": {"n_events": 2, "n_appeared": 1, "n_dropped": 1,
                   "n_lead_shift": 0, "n_cold_start_organs": 0},
    }
    monkeypatch.setattr(bus, "_read_json", lambda rel: payload if "communique_diff" in rel else None)
    result = bus._policy_phrase_block()
    assert result is not None
    assert result["n_events_recent"] == 2
    assert result["n_appeared"] == 1
    assert result["n_dropped"] == 1
    assert result["n_lead_shift"] == 0
    assert "pboc" in result["organs_covered"]
    assert len(result["recent_events"]) == 2
    assert result["claim_family"] == "communique_diff"


def test_policy_phrase_old_events_excluded(monkeypatch):
    """Events older than 14d are excluded from recent_events count.

    NOTE: this exercises the defensive 14d filter path. In production,
    communique_diff stamps all events with the run asof (same as the top-level asof),
    so the filter is a no-op — this payload fabricates a per-event asof older than
    the top-level asof, which the producer cannot currently emit.
    """
    payload = {
        "schema": "communique_diff.v1",
        "asof": "2026-07-02",
        "events": [
            {"event_id": "cd_old", "kind": "APPEARED", "organ": "pboc",
             "phrase": "适度宽松", "gloss": "test", "domain": "monetary",
             "polarity": 0, "review_status": "PROVISIONAL",
             "asof": "2026-06-01",  # much older than 14d from 2026-07-02
             "evidence_url": ""},
        ],
        "cold_start_organs": [],
        "counts": {"n_events": 1, "n_appeared": 1, "n_dropped": 0,
                   "n_lead_shift": 0, "n_cold_start_organs": 0},
    }
    monkeypatch.setattr(bus, "_read_json", lambda rel: payload if "communique_diff" in rel else None)
    result = bus._policy_phrase_block()
    assert result is not None
    assert result["n_events_recent"] == 0  # old event filtered out (defensive path)


# ── W5: cycle-context regime chip helper ──────────────────────────────────────

def test_regime_chip_for_date_missing_parquet(monkeypatch, tmp_path):
    """Missing regime_history.parquet → returns None, no exception."""
    import types
    import engine.china_intel_bus as _bus
    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    # Clear the cache to force fresh lookup
    _bus._REGIME_HISTORY_CACHE.clear()
    result = _bus._regime_chip_for_date("2026-07-01")
    assert result is None


def test_regime_chip_for_date_happy_path(tmp_path, monkeypatch):
    """Valid parquet with known date → returns chip dict with expected keys."""
    import pandas as pd
    import types
    import engine.china_intel_bus as _bus

    p = tmp_path / "data" / "china_regime"
    p.mkdir(parents=True)
    df = pd.DataFrame({
        "quad": ["Q1"],
        "quad_name": ["Goldilocks"],
        "liquidity": ["expanding"],
        "cycle": ["early"],
    }, index=pd.DatetimeIndex(["2026-07-01"]))
    df.to_parquet(p / "regime_history.parquet")

    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    _bus._REGIME_HISTORY_CACHE.clear()

    result = _bus._regime_chip_for_date("2026-07-01")
    assert result is not None
    assert result["quad"] == "Q1"
    assert result["quad_name"] == "Goldilocks"
    assert result["liquidity"] == "expanding"
    assert result["cycle"] == "early"


def test_regime_chip_for_date_not_in_index(tmp_path, monkeypatch):
    """Date not in parquet index → returns None, no exception."""
    import pandas as pd
    import types
    import engine.china_intel_bus as _bus

    p = tmp_path / "data" / "china_regime"
    p.mkdir(parents=True)
    df = pd.DataFrame({
        "quad": ["Q1"],
        "quad_name": ["Goldilocks"],
        "liquidity": ["expanding"],
        "cycle": ["early"],
    }, index=pd.DatetimeIndex(["2026-07-01"]))
    df.to_parquet(p / "regime_history.parquet")

    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    _bus._REGIME_HISTORY_CACHE.clear()

    result = _bus._regime_chip_for_date("1990-01-01")
    assert result is None


def test_regime_chip_weekend_date_backward_asof(tmp_path, monkeypatch):
    """Weekend-dated event (regime_history is trading-days-only) maps back to
    the prior trading day's row — exact-match would silently drop the chip."""
    import pandas as pd
    import types
    import engine.china_intel_bus as _bus

    p = tmp_path / "data" / "china_regime"
    p.mkdir(parents=True)
    df = pd.DataFrame({
        "quad": ["Q2", "Q3"],
        "quad_name": ["Reflation", "Stagflation"],
        "liquidity": ["expanding", "contracting"],
        "cycle": ["early", "late"],
    }, index=pd.DatetimeIndex(["2026-07-02", "2026-07-03"]))  # Thu, Fri
    df.to_parquet(p / "regime_history.parquet")

    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    _bus._REGIME_HISTORY_CACHE.clear()

    result = _bus._regime_chip_for_date("2026-07-05")  # Sunday announcement
    assert result is not None
    assert result["quad"] == "Q3"  # Friday's row, never a later one


def test_policy_phrase_events_get_regime_chips(tmp_path, monkeypatch):
    """recent_events get regime_chip stamped when parquet has the date."""
    import pandas as pd
    import types
    from datetime import date, timedelta
    import engine.china_intel_bus as _bus

    # Write fixture parquet
    p = tmp_path / "data" / "china_regime"
    p.mkdir(parents=True)
    today = date.today().isoformat()
    df = pd.DataFrame({
        "quad": ["Q2"],
        "quad_name": ["Reflation"],
        "liquidity": ["neutral"],
        "cycle": ["mid"],
    }, index=pd.DatetimeIndex([today]))
    df.to_parquet(p / "regime_history.parquet")

    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    _bus._REGIME_HISTORY_CACHE.clear()

    payload = {
        "schema": "communique_diff.v1",
        "asof": today,
        "events": [
            {"event_id": "cd_x", "kind": "APPEARED", "organ": "pboc",
             "phrase": "适度宽松", "gloss": "moderately loose", "domain": "monetary",
             "polarity": 0, "review_status": "PROVISIONAL", "asof": today, "evidence_url": ""},
        ],
        "cold_start_organs": [],
        "counts": {"n_events": 1, "n_appeared": 1, "n_dropped": 0,
                   "n_lead_shift": 0, "n_cold_start_organs": 0},
    }
    monkeypatch.setattr(_bus, "_read_json", lambda rel: payload if "communique_diff" in rel else None)

    result = _bus._policy_phrase_block()
    assert result is not None
    assert len(result["recent_events"]) == 1
    ev = result["recent_events"][0]
    assert "regime_chip" in ev
    assert ev["regime_chip"]["quad"] == "Q2"
    assert ev["regime_chip"]["quad_name"] == "Reflation"


def test_policy_phrase_events_no_chip_when_no_parquet(monkeypatch, tmp_path):
    """recent_events have no regime_chip when parquet is absent — no crash."""
    import types
    from datetime import date
    import engine.china_intel_bus as _bus

    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    _bus._REGIME_HISTORY_CACHE.clear()

    today = date.today().isoformat()
    payload = {
        "schema": "communique_diff.v1",
        "asof": today,
        "events": [
            {"event_id": "cd_y", "kind": "DROPPED", "organ": "ndrc",
             "phrase": "房住不炒", "gloss": "housing not for spec", "domain": "real_estate",
             "polarity": 0, "review_status": "PROVISIONAL", "asof": today, "evidence_url": ""},
        ],
        "cold_start_organs": [],
        "counts": {"n_events": 1, "n_appeared": 0, "n_dropped": 1,
                   "n_lead_shift": 0, "n_cold_start_organs": 0},
    }
    monkeypatch.setattr(_bus, "_read_json", lambda rel: payload if "communique_diff" in rel else None)

    result = _bus._policy_phrase_block()
    assert result is not None
    ev = result["recent_events"][0]
    assert "regime_chip" not in ev  # no parquet → no chip, no crash


# ── v4: narrative_divergence block ───────────────────────────────────────────

def test_narrative_divergence_block_no_parquet(monkeypatch, tmp_path):
    """Missing parquet → block returns None, no exception."""
    import engine.china_intel_bus as _bus
    # Patch config.ROOT so the path doesn't exist
    import types
    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(_bus, "config", fake_config)
    result = _bus._narrative_divergence_block()
    assert result is None


def test_narrative_divergence_block_happy_path(monkeypatch, tmp_path):
    """Valid parquet → block returns z, trend, risk_flag."""
    import pandas as pd
    import math
    # Write a stub parquet
    parquet_dir = tmp_path / "data" / "missing_tape"
    parquet_dir.mkdir(parents=True)
    df = pd.DataFrame({
        "date": ["2026-07-01", "2026-07-02", "2026-07-03",
                 "2026-07-04", "2026-07-05", "2026-07-06"],
        "zh_tone": [1.0, 1.2, 1.5, 1.8, 2.0, 2.5],
        "en_tone": [-0.2, -0.3, -0.5, -0.4, -0.6, -0.8],
        "spread": [1.2, 1.5, 2.0, 2.2, 2.6, 3.3],
        "spread_expanding_z": [float("nan"), float("nan"), float("nan"),
                               float("nan"), float("nan"), 2.1],
        "fetch_status": ["ok"] * 6,
    })
    df.to_parquet(parquet_dir / "tone_divergence.parquet", index=False)

    import types
    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(bus, "config", fake_config)
    result = bus._narrative_divergence_block()
    assert result is not None
    assert result["divergence_z"] == pytest.approx(2.1, abs=0.01)
    assert result["risk_flag"] is True  # z > 1.5
    assert result["direction_proven"] is False
    assert result["asof"] == "2026-07-06"


def test_narrative_divergence_block_negative_z_no_flag(monkeypatch, tmp_path):
    """Negative z (e.g. -2.0) must NOT set risk_flag — semantics are one-sided (high = suspect)."""
    import pandas as pd
    parquet_dir = tmp_path / "data" / "missing_tape"
    parquet_dir.mkdir(parents=True)
    df = pd.DataFrame({
        "date": ["2026-07-01", "2026-07-02", "2026-07-03",
                 "2026-07-04", "2026-07-05", "2026-07-06"],
        "zh_tone": [-1.0, -1.2, -1.5, -1.8, -2.0, -2.5],
        "en_tone": [0.2, 0.3, 0.5, 0.4, 0.6, 0.8],
        "spread": [-1.2, -1.5, -2.0, -2.2, -2.6, -3.3],
        "spread_expanding_z": [float("nan"), float("nan"), float("nan"),
                               float("nan"), float("nan"), -2.0],
        "fetch_status": ["ok"] * 6,
    })
    df.to_parquet(parquet_dir / "tone_divergence.parquet", index=False)

    import types
    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(bus, "config", fake_config)
    result = bus._narrative_divergence_block()
    assert result is not None
    assert result["divergence_z"] == pytest.approx(-2.0, abs=0.01)
    assert result["risk_flag"] is False  # negative z = offshore quieter, not domestic suppression


def test_narrative_divergence_block_all_nan_z(monkeypatch, tmp_path):
    """All-NaN z-scores (cold-start) → block returns None (no z to show)."""
    import pandas as pd
    parquet_dir = tmp_path / "data" / "missing_tape"
    parquet_dir.mkdir(parents=True)
    df = pd.DataFrame({
        "date": ["2026-07-01", "2026-07-02"],
        "zh_tone": [1.0, 1.2],
        "en_tone": [-0.2, -0.3],
        "spread": [1.2, 1.5],
        "spread_expanding_z": [float("nan"), float("nan")],
        "fetch_status": ["ok", "ok"],
    })
    df.to_parquet(parquet_dir / "tone_divergence.parquet", index=False)

    import types
    fake_config = types.SimpleNamespace(ROOT=tmp_path)
    monkeypatch.setattr(bus, "config", fake_config)
    result = bus._narrative_divergence_block()
    assert result is None


# ── v4 integration: new blocks surface in briefing ───────────────────────────

def test_briefing_includes_v4_blocks(monkeypatch):
    """briefing() always has policy_phrase and narrative_divergence keys (may be None)."""
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    b = bus.briefing(asof="2026-07-06")
    assert "policy_phrase" in b
    assert "narrative_divergence" in b
    # both None when no data
    assert b["policy_phrase"] is None
    assert b["narrative_divergence"] is None


def test_digest_text_includes_policy_phrase_count():
    """digest text mentions policy phrase events when present."""
    from datetime import date, timedelta
    recent = (date.today() - timedelta(days=2)).isoformat()
    b = {
        "policy_phrase": {
            "asof": recent,
            "n_events_recent": 3,
            "n_appeared": 2,
            "n_dropped": 1,
            "n_lead_shift": 0,
            "organs_covered": ["pboc", "ndrc"],
            "is_context_only": True,
        },
        "narrative_divergence": None,
    }
    txt = bus._digest_text(b)
    assert "3 events" in txt
    assert "appeared" in txt.lower()
    assert "salience-only" in txt.lower()


def test_digest_text_includes_divergence_z():
    """digest text mentions onshore/offshore divergence z when present."""
    b = {
        "policy_phrase": None,
        "narrative_divergence": {
            "divergence_z": 2.3,
            "trend_5d": "rising",
            "risk_flag": True,
        },
    }
    txt = bus._digest_text(b)
    assert "2.3" in txt or "+2.30" in txt
    assert "direction=0" in txt


import pytest


# ── v5: special_situations block ─────────────────────────────────────────────

def test_special_situations_block_missing_file(monkeypatch):
    """Missing chinaspecialdata/special.json → block returns None, no exception."""
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    result = bus._special_situations_block()
    assert result is None


def test_special_situations_block_happy_path(monkeypatch):
    """Valid special.json → block returns compact summary."""
    payload = {
        "schema": "china_special_sits.v1",
        "asof": "2026-07-06",
        "unlocks": {"n_events_30d": 5, "n_large": 2, "events": [
            {"ticker": "600000.SS", "name": "浦发银行", "unlock_date": "2026-07-15",
             "float_ratio": 8.2, "large_flag": True, "mktcap_yi": 12.5}
        ]},
        "inquiry": {"n_letters": 3, "letters": [
            {"secCode": "000001", "secName": "平安银行", "title": "关注函",
             "date": "2026-07-05", "has_reply": False, "reply_state": "open",
             "kind": "letter"}
        ]},
        "preannounce": {"n_total": 45},
        "buyback": {"n_active": 12},
        "pledge": {"n_high": 8},
        "st": {"count": 211},
        "block_trades": {"n_names": 50},
    }
    monkeypatch.setattr(bus, "_read_json",
                        lambda rel: payload if "chinaspecialdata" in rel else None)
    result = bus._special_situations_block()
    assert result is not None
    assert result["asof"] == "2026-07-06"
    assert result["n_unlocks"] == 5
    assert result["n_inquiry"] == 3
    assert result["n_st"] == 211
    assert result["top_unlock"]["ticker"] == "600000.SS"
    assert result["top_unlock"]["large_flag"] is True
    assert result["newest_letter"]["secCode"] == "000001"
    # The hub card must carry the three-valued state, not only the boolean: a
    # consumer reading has_reply alone renders an 'undetermined' letter as an
    # open regulatory question.
    assert result["newest_letter"]["reply_state"] == "open"
    assert result["is_context_only"] is True


# ── v5 integration: block surfaces in briefing ──────────────────────────────

def test_briefing_includes_v5_blocks(monkeypatch):
    """briefing() always has special_situations key (may be None)."""
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    b = bus.briefing(asof="2026-07-06")
    assert "special_situations" in b
    assert b["special_situations"] is None  # None when artifact absent


def test_briefing_schema_is_v6(monkeypatch):
    """Schema string must be v6."""
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    b = bus.briefing(asof="2026-07-06")
    assert b["schema"] == "china_intel.briefing.v6"


# ── v6 integration: bus↔template contract integration test (BLOCKER 2) ────────

def test_template_renders_command_section(tmp_path, monkeypatch):
    """Integration test: fixture command.json + builder + template → cmd-tbl appears.

    This test was designed to FAIL against the pre-fix code (bus block carried top10
    but template guarded on b.command.command which didn't exist in the bus payload).
    Post-fix: builder loads cmd_full separately and passes it to the template.

    Steps:
    1. Write a fixture command.json to tmp_path/china_intel/command.json
    2. Run china_intel_bus.briefing() with _read_json monkeypatched to serve the fixture
    3. Load cmd_full exactly as build_china_intel._load_cmd_full() does
    4. Render the actual template with (b=b, cmd_full=cmd_full)
    5. Assert <table class="cmd-tbl">, Discovery Queue header, and (with analogs) analogs card
    """
    import json as _json
    from jinja2 import Environment, FileSystemLoader
    from lib import config
    from scripts.build_china_intel import _load_cmd_full

    # ── 1. Write fixture command.json ──────────────────────────────────────
    cmd_dir = tmp_path / "china_intel"
    cmd_dir.mkdir(parents=True)
    fixture_command = {
        "schema": "china_intel.command.v1",
        "is_context_only": True,
        "as_of": "2026-07-06",
        "n_universe": 5,
        "command": [
            {
                "ticker": "000563.SZ", "name": "武汉银行", "stage": "early",
                "opportunity_score": 82.2, "edge_remaining": 0.93,
                "edge_drivers": ["not on buy-board"], "edge_components": 2,
                "leading_gap": 1, "lead_up": 1, "lag_up": 0, "signal_core": 0.768,
                "falsifier": None, "falsifier_penalty": 1.0,
                "directions": {"altdata": 1, "radar": None, "news": None, "board": None},
                "desk_matrix": {
                    "news": {"present": False, "dir": None},
                    "altdata": {"present": True, "dir": 1},
                    "radar": {"present": False, "dir": None},
                    "board": {"present": False, "dir": None},
                    "special": {"present": False, "dir": None},
                },
                "off_desk": True, "veto_blind": False,
                "traj": {"ret_20d": 5.2, "rs_20d": 3.1, "rs_60d": 1.2,
                         "off_high_pct": -8.5, "rolling_over": False},
                "read": "A leading desk is ahead of the crowd — early, ~93% edge remaining.",
            },
            {
                # veto-blind row: traj is None and MUST NOT crash the render
                # (missing traj keys pass `is not none` as Undefined then crash on compare)
                "ticker": "832000.BJ", "name": "无价名", "stage": "early",
                "opportunity_score": 61.0, "edge_remaining": None,
                "edge_drivers": [], "edge_components": 0,
                "leading_gap": 1, "lead_up": 1, "lag_up": 0, "signal_core": 0.61,
                "falsifier": None, "falsifier_penalty": 1.0,
                "directions": {"altdata": 1, "radar": None, "news": None, "board": None},
                "desk_matrix": {
                    "news": {"present": False, "dir": None},
                    "altdata": {"present": True, "dir": 1},
                    "radar": {"present": False, "dir": None},
                    "board": {"present": False, "dir": None},
                    "special": {"present": False, "dir": None},
                },
                "off_desk": True, "veto_blind": True,
                "traj": None,
                "read": "Leading signal, no price plane — veto blind.",
            },
        ],
        "discovery": [
            {
                "ticker": "000001.SZ", "name": "平安银行", "disc_score": 0.65,
                "source": "lhb_first_seat", "reason": "First LHB seat in 90+ days",
                "off_desk": True, "experimental": False, "lhb_date": "2026-07-06",
            },
        ],
        "analogs": None,
        "desks": {"news": {"live": False}, "altdata": {"live": True},
                  "radar": {"live": False}, "board": {"live": False}, "special": {"live": False}},
        "counts": {"emerging": 0, "early": 1, "consensus": 0, "exhausted": 0,
                   "faltering": 0, "distribution": 0, "quiet": 0, "board_members": 0,
                   "with_price": 1, "veto_blind": 0, "board_only_unranked": 0},
    }
    (cmd_dir / "command.json").write_text(_json.dumps(fixture_command, ensure_ascii=False))

    # Also write a fixture analogs.json to test analogs card
    fixture_analogs = {
        "schema": "china_intel.analogs.v1",
        "as_of": "2026-07-06",
        "coverage": "CSI300 2010-2026",
        "query": {"quad": "Q2", "quad_name": "Bull", "liquidity": "easing", "cycle": "mid"},
        "fan": {"h20": {"p25": 0.01, "median": 0.03, "p75": 0.06, "n": 12}},
        "analogs": [{"date": "2015-06-01", "quad": "Q2", "fwd_shcomp": {"h20": 0.04}}],
        "method_note": "Cosine similarity on macro fingerprint.",
        "disclaimer_en": "Descriptive fan only.",
        "disclaimer_zh": "仅描述性分布。",
    }
    (cmd_dir / "analogs.json").write_text(_json.dumps(fixture_analogs, ensure_ascii=False))

    # ── 2. Run briefing() with _read_json reading from tmp_path ───────────
    def _mock_read_json(rel: str):
        p = tmp_path / rel
        if p.exists():
            return _json.loads(p.read_text())
        return None

    monkeypatch.setattr(bus, "_read_json", _mock_read_json)
    b = bus.briefing(asof="2026-07-06")

    # ── 3. Load cmd_full exactly as the builder does ───────────────────────
    cmd_full = _json.loads((cmd_dir / "command.json").read_text())

    # ── 4. Render the actual template ─────────────────────────────────────
    env = Environment(
        loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:
        # i18n may fail without full data; provide stub
        env.globals.update(td=lambda k, zh="": k, tr=lambda k, zh="": k,
                           t=lambda k, zh="": k)
    html = env.get_template("china_intel.html.j2").render(b=b, cmd_full=cmd_full)

    # ── 5. Assertions ──────────────────────────────────────────────────────
    # K2: command table rendered
    assert 'class="cmd-tbl"' in html, "cmd-tbl table not found — K2 command section not rendered"
    # K2: ticker in table
    assert "000563.SZ" in html, "fixture ticker not found in rendered HTML"
    # K3: Discovery Queue header present
    assert "Discovery Queue" in html or "发现队列" in html, \
        "Discovery Queue header not found — K3 not rendered"
    # K3: discovery ticker present
    assert "000001.SZ" in html, "discovery ticker not found in rendered HTML"

    # Analogs card: b.analogs is set (from fixture analogs.json via _mock_read_json)
    assert b.get("analogs") is not None, "b.analogs should be non-None with fixture analogs.json"
    assert "Cycle Context" in html or "周期背景" in html, \
        "Analogs card not rendered — K4 not present even with b.analogs set"


def test_template_command_pre_fix_would_fail(tmp_path, monkeypatch):
    """Demonstrate that WITHOUT cmd_full the old template guard fails silently.

    This test proves the pre-fix behavior: b.command is a compact dict with top10/discovery_n
    but no .command/.discovery keys, so K2/K3 render nothing.
    """
    import json as _json
    from jinja2 import Environment, FileSystemLoader
    from lib import config

    # monkeypatch: no artifacts on disk → bus command block returns compact form
    monkeypatch.setattr(bus, "_read_json", lambda rel: None)
    b = bus.briefing(asof="2026-07-06")

    # Inject a fake bus-style command block (as the OLD code would have returned)
    b["command"] = {
        "asof": "2026-07-06", "n_universe": 5, "counts": {},
        "top10": [{"ticker": "000563.SZ", "stage": "early"}],
        "discovery_n": 1, "is_context_only": True,
        # note: NO .command key, NO .discovery key
    }

    env = Environment(
        loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:
        env.globals.update(td=lambda k, zh="": k, tr=lambda k, zh="": k,
                           t=lambda k, zh="": k)

    # Render WITHOUT cmd_full (cmd_full=None simulates the old template behavior)
    html = env.get_template("china_intel.html.j2").render(b=b, cmd_full=None)

    # K2 must NOT render — cmd_full is None so the guard `{%- if cmd_full and cmd_full.command %}` fails
    assert 'class="cmd-tbl"' not in html, \
        "cmd-tbl should NOT be present when cmd_full=None (pre-fix behavior)"
