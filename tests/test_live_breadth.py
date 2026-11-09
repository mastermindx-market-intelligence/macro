"""Tests for the live intraday breadth poller (Phase 2 engine lane).

No network anywhere: the pure join/count core (engine.live_breadth) and the
session-window + fail-soft logic (scripts.live_breadth_poller) are exercised
against synthetic fixtures. Session-window tests use FIXED datetimes across DST
boundaries — no wall-clock-dependent assertion that could flip after 5pm PDT
(UTC-fixture-bomb class).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from engine import live_breadth as lb
from scripts import live_breadth_poller as poller


# ── the gate-1 schema contract, asserted at the byte-key level ─────────────────

TIER_KEYS = {"key", "label", "univ", "n", "adv", "dec", "unch", "adv_pct",
             "pa50", "pa200", "nh", "nl", "net_nh"}
COMP_KEYS = {"n", "adv", "dec", "unch", "adv_pct", "pa50", "pa200", "net_nh"}
# FROZEN CONTRACT §1/§9: the truth-boundary wave adds built_at/source_asof/
# source_age_min/feed_status/usable/unusable_reason/coverage/producer —
# purely additive, `asof` stays for back-compat (mirrors built_at).
TOP_KEYS = {"schema", "asof", "built_at", "source_asof", "source_age_min",
            "delay_min", "session", "basis", "feed_status", "usable",
            "unusable_reason", "coverage", "producer", "tiers", "comp", "meta"}
COVERAGE_KEYS = {"n", "expected", "pct"}


def _th(prev, ma50, ma200, hi52, lo52):
    return {"prev_close": prev, "ma50": ma50, "ma200": ma200,
            "hi52": hi52, "lo52": lo52}


# ── pure join / count ─────────────────────────────────────────────────────────

def test_basic_counts():
    """last vs prev_close -> adv/dec; last vs MA -> pa50/pa200; 52w band -> nh/nl."""
    th = {
        "AAA": _th(100, 90, 80, 120, 70),   # last 110 -> adv, >ma50, >ma200
        "BBB": _th(100, 90, 80, 120, 70),   # last 95  -> dec, >ma50, >ma200
        "CCC": _th(100, 90, 80, 120, 70),   # last 130 -> adv, new high
        "DDD": _th(100, 90, 80, 120, 70),   # last 65  -> dec, new low, <ma
    }
    last = {"AAA": 110, "BBB": 95, "CCC": 130, "DDD": 65}
    t = lb.compute_tier("large", "S&P 500", {"en": "Large cap", "zh": "大盘"}, th, last)
    assert t["n"] == 4
    assert t["adv"] == 2 and t["dec"] == 2 and t["unch"] == 0
    assert t["adv_pct"] == pytest.approx(50.0)
    # pa50: AAA,BBB,CCC above 90; DDD(65) below -> 3/4 = 75
    assert t["pa50"] == pytest.approx(75.0)
    # pa200: AAA,BBB,CCC above 80; DDD below -> 3/4 = 75
    assert t["pa200"] == pytest.approx(75.0)
    assert t["nh"] == 1 and t["nl"] == 1
    assert t["net_nh"] == 0
    assert set(t.keys()) == TIER_KEYS


def test_unchanged_name_not_an_advancer():
    """A halted / flat name (last == prev_close) is unch, never adv or dec, and is
    excluded from adv_pct's denominator (gate 4)."""
    th = {"FLAT": _th(100, 90, 80, 120, 70), "UP": _th(100, 90, 80, 120, 70)}
    last = {"FLAT": 100, "UP": 105}
    t = lb.compute_tier("mid", "S&P 400", {"en": "Mid cap", "zh": "中盘"}, th, last)
    assert t["adv"] == 1 and t["dec"] == 0 and t["unch"] == 1
    assert t["adv_pct"] == pytest.approx(100.0)   # 1 adv / (1 adv + 0 dec)
    assert t["n"] == 2


def test_missing_member_excluded_from_denominators():
    """A member absent from the snapshot is excluded from every count — never
    silently treated as unchanged (gate 4). The caller tallies it in meta."""
    th = {"HERE": _th(100, 90, 80, 120, 70), "GONE": _th(100, 90, 80, 120, 70)}
    last = {"HERE": 110}                        # GONE has no live price
    t = lb.compute_tier("small", "S&P 600", {"en": "Small cap", "zh": "小盘"}, th, last)
    assert t["n"] == 1                          # only HERE counted
    assert t["adv"] == 1 and t["dec"] == 0 and t["unch"] == 0


def test_zero_denominator_ratios_are_none():
    """No members with a live last -> ratios are None, not a ZeroDivisionError."""
    th = {"X": _th(100, 90, 80, 120, 70)}
    t = lb.compute_tier("large", "S&P 500", {"en": "L", "zh": "大"}, th, {})
    assert t["n"] == 0
    assert t["adv_pct"] is None and t["pa50"] is None and t["pa200"] is None
    assert t["nh"] == 0 and t["nl"] == 0


def test_none_ma_excluded_from_pa_denominator():
    """A member the cache holds too shallowly for a 200DMA (ma200 None) is excluded
    from pa200's denominator but still counted in adv/dec and pa50."""
    th = {
        "SHALLOW": _th(100, 90, None, 120, 70),  # no ma200
        "DEEP": _th(100, 90, 80, 120, 70),
    }
    last = {"SHALLOW": 110, "DEEP": 110}
    t = lb.compute_tier("large", "S&P 500", {"en": "L", "zh": "大"}, th, last)
    assert t["pa50"] == pytest.approx(100.0)     # both above ma50 -> 2/2
    assert t["pa200"] == pytest.approx(100.0)    # only DEEP has ma200 -> 1/1


def test_composite_is_member_weighted_and_labelless():
    """comp rolls up counts, weights pa50/pa200 by member count, and carries NO
    label/verdict/tone (stance is the surface's job — gate 1)."""
    big = lb.compute_tier("large", "S&P 500", {"en": "L", "zh": "大"},
                          {f"L{i}": _th(100, 90, 80, 120, 70) for i in range(100)},
                          {f"L{i}": (110 if i < 80 else 95) for i in range(100)})
    small = lb.compute_tier("small", "S&P 600", {"en": "S", "zh": "小"},
                            {f"S{i}": _th(100, 90, 80, 120, 70) for i in range(10)},
                            {f"S{i}": 95 for i in range(10)})   # all below ma50? no, 95>90
    p = lb.build_payload([big, small], asof="2026-07-24T14:00:00Z",
                         delay_min=15, session="rth", missing={"large": 1})
    assert p["comp"]["n"] == 110
    assert p["comp"]["adv"] == big["adv"] + small["adv"]
    # comp carries NO stance wording
    assert "label" not in p["comp"] and "verdict" not in p["comp"] and "tone" not in p["comp"]
    # weighted pa50 lands between the two tier values, closer to the larger tier
    assert big["pa50"] is not None and small["pa50"] is not None
    lo, hi = sorted((big["pa50"], small["pa50"]))
    assert lo <= p["comp"]["pa50"] <= hi
    assert p["meta"]["missing"] == {"large": 1}


# ── schema golden: byte-level key parity with the gate-1 contract ─────────────

def test_schema_key_parity():
    t = lb.compute_tier("large", "S&P 500", {"en": "L", "zh": "大"},
                        {"A": _th(100, 90, 80, 120, 70)}, {"A": 110})
    p = lb.build_payload([t], asof="2026-07-24T14:00:00Z", delay_min=15,
                         session="rth")
    assert set(p.keys()) == TOP_KEYS
    assert p["schema"] == "live.breadth.v1"
    assert p["basis"] == "poll"
    assert set(p["tiers"][0].keys()) == TIER_KEYS
    assert set(p["comp"].keys()) == COMP_KEYS
    assert set(p["tiers"][0]["label"].keys()) == {"en", "zh"}


def test_tier_order_and_keys_mirror_nightly():
    """Tier keys/order match build_site._BREADTH_TIERS (large, mid, small)."""
    assert [t[0] for t in lb.BREADTH_TIERS] == ["large", "mid", "small"]
    assert [t[1] for t in lb.BREADTH_TIERS] == ["breadth", "midcap_breadth", "smallcap_breadth"]
    assert [t[2] for t in lb.BREADTH_TIERS] == ["S&P 500", "S&P 400", "S&P 600"]


def test_payload_is_json_serialisable_finite():
    t = lb.compute_tier("large", "S&P 500", {"en": "L", "zh": "大"},
                        {"A": _th(100, 90, 80, 120, 70)}, {"A": 110})
    p = lb.build_payload([t], asof="x", delay_min=15, session="rth")
    # allow_nan=False path (mirrors write_payload) must not raise
    json.loads(json.dumps(p, allow_nan=False))


# ── symbol canonicalisation (single mapping, dot -> dash) ─────────────────────

def test_canonical_symbol_dot_to_dash():
    assert lb.canonical_symbol("BRK.B") == "BRK-B"
    assert lb.canonical_symbol("bf.b") == "BF-B"
    assert lb.canonical_symbol(" aapl ") == "AAPL"
    assert lb.canonical_symbol("BRK-B") == "BRK-B"   # already dash — idempotent


# ── session window across DST boundaries (fixed datetimes; no wall-clock) ──────

def _utc(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def test_session_rth_summer_edt():
    # 2026-07-24 (EDT, UTC-4): 14:00 UTC = 10:00 ET -> rth
    assert poller.session_tag(_utc(2026, 7, 24, 14, 0)) == "rth"


def test_session_rth_winter_est():
    # 2026-01-14 (EST, UTC-5): 15:00 UTC = 10:00 ET -> rth
    assert poller.session_tag(_utc(2026, 1, 14, 15, 0)) == "rth"


def test_session_pre_and_post_edt():
    # 12:00 UTC = 08:00 ET (EDT) -> pre ; 21:00 UTC = 17:00 ET -> post
    assert poller.session_tag(_utc(2026, 7, 24, 12, 0)) == "pre"
    assert poller.session_tag(_utc(2026, 7, 24, 21, 0)) == "post"


def test_session_closed_overnight_and_weekend():
    # 07:00 UTC = 03:00 ET -> closed (before 04:00 pre-open)
    assert poller.session_tag(_utc(2026, 7, 24, 7, 0)) == "closed"
    # Saturday 2026-07-25 14:00 UTC -> closed
    assert poller.session_tag(_utc(2026, 7, 25, 14, 0)) == "closed"


def test_session_dst_transition_days():
    """The exact DST switch days: the tag depends on the ET wall clock, not a
    fixed UTC offset. 2026 US DST: spring-forward Mar 8, fall-back Nov 1."""
    # Mar 8 2026 (spring forward at 02:00->03:00 ET): 14:00 UTC = 10:00 EDT -> rth
    assert poller.session_tag(_utc(2026, 3, 9, 14, 0)) == "rth"   # Monday after
    # Nov 2 2026 (Monday after fall-back, now EST UTC-5): 15:00 UTC = 10:00 EST -> rth
    assert poller.session_tag(_utc(2026, 11, 2, 15, 0)) == "rth"
    # Same 14:00 UTC on Nov 2 = 09:00 EST -> pre (offset flipped vs summer)
    assert poller.session_tag(_utc(2026, 11, 2, 14, 0)) == "pre"


def test_within_rth_window_edges():
    # 09:25 ET (13:25 UTC EDT) inside; 16:05 ET (20:05 UTC) inside; 16:06 outside
    assert poller.within_rth(_utc(2026, 7, 24, 13, 25)) is True
    assert poller.within_rth(_utc(2026, 7, 24, 20, 5)) is True
    assert poller.within_rth(_utc(2026, 7, 24, 20, 6)) is False
    assert poller.within_rth(_utc(2026, 7, 25, 14, 0)) is False    # Saturday


# ── stale-snapshot delay stamping ─────────────────────────────────────────────

def test_delay_min_adds_snapshot_staleness(monkeypatch):
    """delay_min = vendor floor + minutes since the freshest snapshot ts."""
    monkeypatch.setattr(poller, "_delay_floor", lambda: 15)

    class _Store:
        by_tier = {"large": {"A": _th(100, 90, 80, 120, 70)}}
    now = _utc(2026, 7, 24, 14, 0)
    snap_ts = _utc(2026, 7, 24, 13, 42)          # 18 min stale
    p = poller.build_breadth(_Store(), {"A": 110}, now=now, snapshot_ts=snap_ts)
    assert p["delay_min"] == 15 + 18
    assert p["session"] == "rth"
    assert p["tiers"][0]["adv"] == 1


# ── fail-soft: offline / no-snapshot emits empty tiers, never crashes ──────────

def test_build_breadth_offline_empty(monkeypatch):
    monkeypatch.setattr(poller, "_delay_floor", lambda: 15)

    class _Store:
        by_tier = {"large": {"A": _th(100, 90, 80, 120, 70)}}
    p = poller.build_breadth(_Store(), {}, now=_utc(2026, 7, 24, 14, 0), offline=True)
    assert p["tiers"] == []
    assert p["comp"]["n"] == 0 and p["comp"]["pa50"] is None
    assert p["meta"]["note"] == "offline"
    assert set(p.keys()) == TOP_KEYS


def test_empty_payload_shape():
    p = lb.empty_payload(asof="x", delay_min=15, session="closed", note="no_key")
    assert set(p.keys()) == TOP_KEYS
    assert p["tiers"] == [] and p["basis"] == "poll"
    assert set(p["comp"].keys()) == COMP_KEYS


# ── fetch_full_market key handling (no network) ───────────────────────────────

def test_fetch_offline_short_circuits():
    last, status, ts = poller.fetch_full_market(offline=True)
    assert last == {} and status == "offline" and ts is None


def test_fetch_no_key(monkeypatch):
    monkeypatch.setattr(poller.config, "secret", lambda name: None)
    last, status, ts = poller.fetch_full_market(offline=False)
    assert last == {} and status == "no_key" and ts is None


# ── the --once --offline CLI path emits a well-formed file, never crashes ──────

def test_cli_once_offline_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(poller.config, "site_dir", lambda: tmp_path)
    rc = poller.main(["--once", "--offline"])
    assert rc == 0
    out = tmp_path / "live" / "breadth.json"
    assert out.exists()
    p = json.loads(out.read_text())
    assert set(p.keys()) == TOP_KEYS
    assert p["basis"] == "poll"
    # offline -> empty tiers, fail-soft
    assert p["tiers"] == []
    assert p["usable"] is False


# ── evaluate_usable: the ONE truth-boundary adjudicator (FROZEN CONTRACT §1) ──

def _base_usable_kwargs(**over):
    base = dict(feed_status="ok", session="rth", n_tiers=3, coverage_pct=95.0,
                source_age_min=10.0)
    base.update(over)
    return base


def test_evaluate_usable_happy_path_is_true():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs())
    assert usable is True and reason is None


def test_evaluate_usable_feed_not_ok():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(feed_status="no_key"))
    assert usable is False and reason == "feed_no_key"
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(feed_status="offline"))
    assert usable is False and reason == "feed_offline"


def test_evaluate_usable_session_closed_or_falsy():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(session="closed"))
    assert usable is False and reason == "session_closed"
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(session=""))
    assert usable is False and reason == "session_closed"


def test_evaluate_usable_tiers_incomplete():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(n_tiers=2))
    assert usable is False and reason == "tiers_incomplete"


def test_evaluate_usable_no_source_clock():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(source_age_min=None))
    assert usable is False and reason == "no_source_clock"


def test_evaluate_usable_source_stale():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(source_age_min=30.0))
    assert usable is False and reason == "source_stale"


def test_evaluate_usable_negative_source_age_is_allowed_not_rejected():
    """Clock skew (source clock ahead of the build) is NOT staleness — never
    rejected here; only display code may clamp it."""
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(source_age_min=-5.0))
    assert usable is True and reason is None


def test_evaluate_usable_no_coverage():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(coverage_pct=None))
    assert usable is False and reason == "no_coverage"


def test_evaluate_usable_coverage_low():
    usable, reason = lb.evaluate_usable(**_base_usable_kwargs(coverage_pct=50.0))
    assert usable is False and reason == "coverage_low"


def test_evaluate_usable_checks_fire_in_declared_order():
    """When multiple checks would fail at once, the FIRST one in the declared
    order wins — a degraded feed is reported as a feed problem even though the
    session/coverage/source-clock checks would also fail."""
    usable, reason = lb.evaluate_usable(
        feed_status="error", session="closed", n_tiers=0,
        coverage_pct=None, source_age_min=None,
    )
    assert usable is False and reason == "feed_error"


# ── holiday-aware session (Defect 3) ────────────────────────────────────────

def test_session_closed_on_good_friday_2026():
    # 2026-04-03 is Good Friday. EDT (UTC-4): 14:00 UTC = 10:00 ET — an ordinary
    # Friday at this instant would be "rth" (see test below); the full-day
    # closure must win over the clock.
    assert poller.session_tag(_utc(2026, 4, 3, 14, 0)) == "closed"
    assert poller.within_rth(_utc(2026, 4, 3, 14, 0)) is False


def test_session_closed_on_thanksgiving_2026():
    # 2026-11-26 is Thanksgiving (4th Thursday of November). EST (UTC-5):
    # 15:00 UTC = 10:00 ET.
    assert poller.session_tag(_utc(2026, 11, 26, 15, 0)) == "closed"
    assert poller.within_rth(_utc(2026, 11, 26, 15, 0)) is False


def test_session_closed_on_observed_independence_day_2026():
    # 2026-07-04 (Independence Day) is a Saturday, observed Friday 2026-07-03.
    # EDT (UTC-4): 14:00 UTC = 10:00 ET.
    assert poller.session_tag(_utc(2026, 7, 3, 14, 0)) == "closed"
    assert poller.within_rth(_utc(2026, 7, 3, 14, 0)) is False


def test_ordinary_friday_still_rth_2026():
    # 2026-04-10 is an ordinary (non-holiday) Friday. EDT: 14:00 UTC = 10:00 ET.
    assert poller.session_tag(_utc(2026, 4, 10, 14, 0)) == "rth"
    assert poller.within_rth(_utc(2026, 4, 10, 14, 0)) is True


# The pre-existing EDT/EST DST tests (test_session_rth_summer_edt,
# test_session_rth_winter_est, test_session_pre_and_post_edt,
# test_session_closed_overnight_and_weekend, test_session_dst_transition_days,
# test_within_rth_window_edges) are UNCHANGED above and must stay green — the
# calendar check runs BEFORE the time-of-day logic, never replacing it.


# ── source clock is first class (Defect 2) ──────────────────────────────────

def test_build_breadth_emits_source_clock_and_usable_fields(monkeypatch):
    monkeypatch.setattr(poller, "_delay_floor", lambda: 15)
    monkeypatch.setattr(poller, "_producer_id", lambda: "host:test")

    class _Store:
        by_tier = {
            "large": {"A": _th(100, 90, 80, 120, 70)},
            "mid": {"B": _th(100, 90, 80, 120, 70)},
            "small": {"C": _th(100, 90, 80, 120, 70)},
        }
    now = _utc(2026, 7, 24, 14, 0)
    snap_ts = _utc(2026, 7, 24, 13, 54)          # 6 min stale
    p = poller.build_breadth(_Store(), {"A": 110, "B": 105, "C": 95}, now=now,
                             snapshot_ts=snap_ts, feed_status="ok")
    assert p["source_asof"] == "2026-07-24T13:54:00Z"
    assert p["source_age_min"] == pytest.approx(6.0)
    assert p["feed_status"] == "ok"
    assert p["producer"] == "host:test"
    assert p["built_at"] == p["asof"]
    assert isinstance(p["usable"], bool)
    assert set(p.keys()) == TOP_KEYS


def test_source_age_over_sla_marks_unusable(monkeypatch):
    """built-now (fresh artifact) + a 2h-stale SOURCE clock -> unusable, and the
    reason names the source clock, not the build clock."""
    monkeypatch.setattr(poller, "_delay_floor", lambda: 15)

    class _Store:
        by_tier = {
            "large": {"A": _th(100, 90, 80, 120, 70)},
            "mid": {"B": _th(100, 90, 80, 120, 70)},
            "small": {"C": _th(100, 90, 80, 120, 70)},
        }
    now = _utc(2026, 7, 24, 14, 0)
    snap_ts = now - timedelta(hours=2)
    p = poller.build_breadth(_Store(), {"A": 110, "B": 105, "C": 95}, now=now,
                             snapshot_ts=snap_ts)
    assert p["source_age_min"] == pytest.approx(120.0)
    assert p["usable"] is False
    assert p["unusable_reason"] == "source_stale"


def test_empty_payload_no_key_is_never_usable():
    p = lb.empty_payload(asof="2026-07-24T14:00:00Z", delay_min=15, session="rth",
                         note="no_key", feed_status="no_key")
    assert p["usable"] is False
    assert p["unusable_reason"] == "feed_no_key"
    assert set(p.keys()) == TOP_KEYS


def test_build_breadth_no_key_and_offline_are_never_usable(monkeypatch):
    monkeypatch.setattr(poller, "_delay_floor", lambda: 15)

    class _Store:
        by_tier = {"large": {"A": _th(100, 90, 80, 120, 70)}}
    p_offline = poller.build_breadth(_Store(), {}, now=_utc(2026, 7, 24, 14, 0),
                                     offline=True)
    assert p_offline["usable"] is False
    p_no_key = poller.build_breadth(_Store(), {}, now=_utc(2026, 7, 24, 14, 0),
                                    offline=False, feed_status="no_key")
    assert p_no_key["usable"] is False
    assert p_no_key["feed_status"] == "no_key"


# ── _out_path honours MACRO_LIVE_DIR (Defect 5) ─────────────────────────────

def test_out_path_honours_macro_live_dir_env(monkeypatch, tmp_path):
    live_dir = tmp_path / "public" / "live"
    monkeypatch.setenv("MACRO_LIVE_DIR", str(live_dir))
    out = poller._out_path()
    assert out == live_dir / "breadth.json"
    assert out.parent == live_dir            # no extra "live" segment appended


def test_out_path_explicit_site_dir_wins_over_env(monkeypatch, tmp_path):
    live_dir = tmp_path / "env-live"
    monkeypatch.setenv("MACRO_LIVE_DIR", str(live_dir))
    explicit = tmp_path / "explicit"
    out = poller._out_path(explicit)
    assert out == explicit / "live" / "breadth.json"


def test_out_path_default_falls_back_to_site_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("MACRO_LIVE_DIR", raising=False)
    monkeypatch.setattr(poller.config, "site_dir", lambda: tmp_path)
    out = poller._out_path()
    assert out == tmp_path / "live" / "breadth.json"


# ── publication truth (Defect 4) ────────────────────────────────────────────

def test_main_once_publish_returns_1_and_annotates_when_publish_fails(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(poller.config, "site_dir", lambda: tmp_path)
    monkeypatch.setattr(poller, "publish", lambda out: False)
    rc = poller.main(["--once", "--offline", "--publish"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "::error title=live-breadth-publish::" in out
    # line-start, never through the logger (tests/test_gh_annotation_line_start.py)
    assert any(line.startswith("::error") for line in out.splitlines())


def test_main_once_publish_returns_0_when_publish_succeeds(monkeypatch, tmp_path):
    """Covers both a real successful publish AND the deliberate no-op success for
    a byte-identical unchanged payload — both make `publish()` return True, and
    `main()`/`run_cycle` treat them identically (the no-op-vs-real-commit
    distinction lives entirely inside `publish()`, which this test does not
    re-exercise so the suite never shells out to real git)."""
    monkeypatch.setattr(poller.config, "site_dir", lambda: tmp_path)
    monkeypatch.setattr(poller, "publish", lambda out: True)
    rc = poller.main(["--once", "--offline", "--publish"])
    assert rc == 0


def test_loop_path_does_not_raise_when_publish_fails(monkeypatch, tmp_path):
    """Loop mode: a publish failure must never kill the daemon — only `--once`
    treats it as fatal. Drives exactly one iteration by pre-arming the SIGTERM
    stop flag the loop already checks after each cycle, so the test needs no
    real sleep."""
    monkeypatch.setattr(poller.config, "site_dir", lambda: tmp_path)
    monkeypatch.setattr(poller, "publish", lambda out: False)
    monkeypatch.setitem(poller._SIGTERM, "stop", True)
    rc = poller.main(["--offline", "--publish"])
    assert rc == 0


# ── native parquet reads (Python-file-object abort hazard; PR #9043) ──────────

def _write_one_tier_stores(tmp_path, monkeypatch):
    """One BREADTH_TIERS tier's stores under tmp_path (30 daily rows, 3 symbols,
    one dotted) with poller.config.data_dir pointed there. The other two tiers
    stay absent — refresh() skips them fail-soft, so a refresh exercises exactly
    the three parquet reads under test: constituents, full close cache, and the
    columns=[] header check. Returns (tier_key, closes_frame)."""
    import pandas as pd

    key, ns, _univ, _label = lb.BREADTH_TIERS[0]
    dates = pd.date_range("2026-09-01", periods=30, freq="D")
    closes = pd.DataFrame(
        {"AAPL": [100.0 + i for i in range(30)],
         "MNX": [50.0 + 0.5 * i for i in range(30)],
         "BRK.B": [400.0 + i for i in range(30)]},
        index=dates,
    )
    nsdir = tmp_path / ns
    nsdir.mkdir(parents=True)
    closes.to_parquet(nsdir / "_closes_cache.parquet")
    symbols = pd.Index(["AAPL", "MNX", "BRK.B"], name="symbol")
    pd.DataFrame({"weight": [1.0, 1.0, 1.0]}, index=symbols).to_parquet(
        nsdir / "constituents.parquet")
    monkeypatch.setattr(poller.config, "data_dir", lambda: tmp_path)
    return key, closes


def test_threshold_store_reads_parquet_through_native_filesystem(monkeypatch, tmp_path):
    """ThresholdStore's three parquet reads all reach pandas.read_parquet with
    pyarrow's native LocalFileSystem and the threaded knobs off. pandas
    otherwise opens plain local paths as Python file objects and hands those to
    pyarrow; a delayed pyarrow IO-pool completion destroying such a buffer once
    interpreter finalization has begun ends in std::terminate (SIGABRT, after
    the output is written) — the census harness's 3/200 poller aborts (0/600 in
    the build-lane fixture tree), PR #9043's 63/1002 -> 0/1002 on the
    news-universe builder."""
    import inspect
    from pathlib import Path

    import pandas

    key, closes = _write_one_tier_stores(tmp_path, monkeypatch)
    calls: list[tuple[str, dict]] = []
    real_read_parquet = pandas.read_parquet
    has_tpk = "to_pandas_kwargs" in inspect.signature(real_read_parquet).parameters
    # Warm the helper's capability probe against the REAL pandas before the spy
    # replaces pandas.read_parquet (the probe signs whatever the attribute is at
    # first call; the spy's (path, **kwargs) signature would read as "no kwarg").
    # Guarded so on pre-helper code the spy still sees the bare base reads.
    try:
        import lib.native_parquet as _npq
        _npq._has_to_pandas_kwargs()
    except ImportError:
        pass

    def spy(path, **kwargs):
        calls.append((Path(path).name, dict(kwargs)))
        return real_read_parquet(path, **kwargs)

    monkeypatch.setattr(pandas, "read_parquet", spy)

    store = poller.ThresholdStore()
    store.refresh()

    # all three reads happened through the spy: the columns=[] header check and
    # the full load of the close cache, plus the constituents read
    names = [name for name, _kwargs in calls]
    assert names.count("_closes_cache.parquet") == 2
    assert names.count("constituents.parquet") == 1
    assert [kwargs.get("columns") for _name, kwargs in calls].count([]) == 1
    for _name, kwargs in calls:
        assert kwargs["use_threads"] is False
        assert kwargs["pre_buffer"] is False
        assert type(kwargs["filesystem"]).__name__ == "LocalFileSystem"
        if has_tpk:
            assert kwargs["to_pandas_kwargs"] == {"use_threads": False}
        else:
            assert "to_pandas_kwargs" not in kwargs
    # and the stores actually loaded: last closes, last date, dot->dash keys
    last_row = closes.iloc[-1]
    assert store._asof[key] == closes.index.max().strftime("%Y-%m-%d")
    for sym in closes.columns:
        assert store.by_tier[key][lb.canonical_symbol(sym)]["prev_close"] == float(last_row[sym])
    assert "BRK-B" in store.by_tier[key] and "BRK.B" not in store.by_tier[key]


def test_read_parquet_native_columns_empty_keeps_index(tmp_path):
    """columns=[] must reach pandas as [] (the refresh() header check), never be
    dropped-to-None (a full read) or swallowed."""
    import pandas as pd

    from lib.native_parquet import read_parquet_native

    frame = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]},
                         index=pd.date_range("2026-09-01", periods=3, freq="D"))
    path = tmp_path / "empty_cols.parquet"
    frame.to_parquet(path)
    out = read_parquet_native(path, columns=[])
    assert list(out.columns) == []
    pd.testing.assert_index_equal(out.index, frame.index)


def test_read_parquet_native_accepts_file_uri_and_path(tmp_path):
    """A Path, its str, and its file: URI (as argparse's type=Path collapses
    file:///a to file:/a) all read the same frame — the native LocalFileSystem
    answers a URI with ArrowInvalid, so the helper must normalize file: forms
    first (mirrors the PR #9043 URI behaviour)."""
    import pandas as pd
    from pathlib import Path

    from lib.native_parquet import read_parquet_native

    frame = pd.DataFrame({"close": [10.0, 11.0]}, index=pd.Index(["NVDA", "MMC"]))
    path = tmp_path / "frame.parquet"
    frame.to_parquet(path)
    pd.testing.assert_frame_equal(read_parquet_native(path), frame)
    pd.testing.assert_frame_equal(read_parquet_native(str(path)), frame)
    pd.testing.assert_frame_equal(read_parquet_native(Path(path.as_uri())), frame)
    pd.testing.assert_frame_equal(read_parquet_native(path.as_uri()), frame)


def test_read_parquet_native_propagates_missing_file(tmp_path):
    """No catching or mapping in the helper: a missing file surfaces as the
    underlying OSError. Observed as FileNotFoundError on pandas 3.0.6/pyarrow
    26 and on pandas 2.2.3/pyarrow 16.1; asserted as an OSError subclass so the
    exact pyarrow alias stays an implementation detail."""
    from lib.native_parquet import read_parquet_native

    missing = tmp_path / "nope.parquet"
    with pytest.raises(OSError) as exc_info:
        read_parquet_native(missing)
    assert issubclass(type(exc_info.value), OSError)
    assert type(exc_info.value).__name__ == "FileNotFoundError"


def test_read_parquet_native_probe_immune_to_read_parquet_monkeypatch(
        monkeypatch, tmp_path, request):
    """_has_to_pandas_kwargs signs the pandas DEFINITION SITE
    (pandas.io.parquet.read_parquet), never the pandas.read_parquet attribute:
    the probe is lru_cached and fires lazily, so a test that monkeypatches
    pandas.read_parquet with a (path, **kwargs) spy before the first call would
    otherwise cache the spy's signature as "no to_pandas_kwargs" for the rest
    of the process and silently drop the kwarg (isolation-red at 1f231f23:
    the arrow_pools_idle test only passed when an earlier test warmed the
    cache first)."""
    import inspect

    import pandas

    from lib import native_parquet

    # Reset the lazy probe so it fires fresh INSIDE this test, under the spy;
    # monkeypatch can undo the spy but never a cache, so clear again on the way
    # out to leave the process exactly as this test found it.
    native_parquet._has_to_pandas_kwargs.cache_clear()
    request.addfinalizer(native_parquet._has_to_pandas_kwargs.cache_clear)

    real = "to_pandas_kwargs" in inspect.signature(pandas.read_parquet).parameters
    real_read_parquet = pandas.read_parquet
    seen: list[dict] = []

    def spy(path, **kwargs):
        seen.append(dict(kwargs))
        return real_read_parquet(path, **kwargs)

    monkeypatch.setattr(pandas, "read_parquet", spy)

    path = tmp_path / "frame.parquet"
    pandas.DataFrame({"close": [10.0, 11.0]},
                     index=pandas.Index(["NVDA", "MMC"])).to_parquet(path)
    out = native_parquet.read_parquet_native(path)

    assert len(seen) == 1
    if real:
        assert seen[0]["to_pandas_kwargs"] == {"use_threads": False}
    else:
        assert "to_pandas_kwargs" not in seen[0]
    assert list(out["close"]) == [10.0, 11.0]


# ── qualify_snapshot_members: snapshot-source qualification (additive slice) ──
# Pure fixtures only — no network, no wall clock (all instants are fixed aware
# datetimes). These tests use the REAL parse_polygon_snapshot for the parser-
# shaped rows so a parser contract change fails here, not in production.

import copy

from engine import live_quotes as lq

QUAL_KEYS = {"last_by_symbol", "source_asof_by_symbol", "excluded_by_symbol",
             "eligible_n", "qualified_n", "qualification_coverage_pct",
             "oldest_source_asof", "newest_source_asof"}

RECEIPT = _utc(2026, 10, 30, 14, 0)          # snapshot received at the host
ASOF_Q = _utc(2026, 10, 30, 14, 5)           # query instant (>= receipt)
SESSION_START = _utc(2026, 10, 30, 13, 30)   # 09:30 ET (EDT, UTC-4)
SESSION_END = _utc(2026, 10, 30, 20, 0)      # 16:00 ET — half-open upper edge
T_TRADE = _utc(2026, 10, 30, 13, 59)         # a real in-session print
T_STALE = _utc(2026, 10, 30, 13, 35)         # in session, 30 min old at ASOF_Q
T_PREV_SESSION = _utc(2026, 10, 29, 20, 0)   # yesterday's close


def _kw(**over):
    base = dict(observed_at=RECEIPT, asof=ASOF_Q,
                session_start=SESSION_START, session_end=SESSION_END)
    base.update(over)
    return base


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _ident(sym):
    return {"schema": "native_quote_identity.v1", "vendor": "polygon",
            "vendor_symbol": sym, "response_field": "tickers[].ticker"}


def _q(price=101.0, ts="2026-10-30T13:59:00+00:00", sym="AAPL", basis="trade",
       synthetic=False, ident=None, **over):
    """One parser-shaped quote record (engine.live_quotes.parse_polygon_snapshot)."""
    rec = {
        "price": price, "quote_ts": ts, "quote_ts_synthetic": synthetic,
        "source": "polygon", "price_basis": basis, "delay_min": 1.0,
        "native_quote_identity": _ident(sym) if ident is None else ident,
        "prev_close": None, "currency": "USD", "day_volume": None,
        "day_high": None, "day_low": None,
    }
    rec.update(over)
    return rec


def _poly_trade(price, when):
    s = int(when.timestamp())
    return {"lastTrade": {"p": price, "t": s * 1_000_000_000},
            "min": {"c": price - 1.0, "t": s * 1_000},
            "day": {"c": price - 2.0}, "prevDay": {"c": price - 3.0},
            "updated": s * 1_000_000_000}


def _poly_minute(price, when):
    s = int(when.timestamp())
    return {"min": {"c": price, "t": s * 1_000}, "updated": s * 1_000_000_000}


def test_qualify_accepts_real_parser_trade_and_minute_quotes():
    payload = {"tickers": [{**_poly_trade(101.25, T_TRADE), "ticker": "AAPL"},
                           {**_poly_minute(51.5, T_TRADE), "ticker": "MSFT"}]}
    quotes = lq.parse_polygon_snapshot(payload, now=RECEIPT)
    assert quotes["AAPL"]["price_basis"] == "trade"
    assert quotes["MSFT"]["price_basis"] == "minute"
    assert quotes["AAPL"]["quote_ts_synthetic"] is False
    assert quotes["MSFT"]["quote_ts_synthetic"] is False
    res = lb.qualify_snapshot_members(quotes, ["AAPL", "MSFT"], **_kw())
    assert res["qualified_n"] == 2 and res["eligible_n"] == 2
    assert res["last_by_symbol"] == {"AAPL": 101.25, "MSFT": 51.5}
    assert res["source_asof_by_symbol"] == {"AAPL": _iso(T_TRADE), "MSFT": _iso(T_TRADE)}
    assert res["excluded_by_symbol"] == {}
    assert res["qualification_coverage_pct"] == pytest.approx(100.0)
    assert res["oldest_source_asof"] == res["newest_source_asof"] == _iso(T_TRADE)


def test_qualify_rejects_real_parser_day_prev_and_timeless_trade_synthetic_clocks():
    s = int(T_TRADE.timestamp())
    payload = {"tickers": [
        {"ticker": "DAYY", "day": {"c": 52.0}, "updated": s * 1_000_000_000},
        {"ticker": "PRVV", "prevDay": {"c": 50.0}, "updated": s * 1_000_000_000},
        {"ticker": "NOTR", "lastTrade": {"p": 101.0}, "updated": s * 1_000_000_000},
    ]}
    quotes = lq.parse_polygon_snapshot(payload, now=RECEIPT)
    for sym in ("DAYY", "PRVV", "NOTR"):
        assert quotes[sym]["quote_ts_synthetic"] is True
        assert quotes[sym]["quote_ts"] == _iso(T_TRADE)   # stamped the synthetic clock
    res = lb.qualify_snapshot_members(quotes, ["DAYY", "PRVV", "NOTR"], **_kw())
    assert res["qualified_n"] == 0
    # contract's require ORDER: day/prev fall on the basis check first (still
    # a non-live basis), while the timeless trade reaches the synthetic-clock
    # check; all three are excluded either way
    assert res["excluded_by_symbol"] == {
        "DAYY": "unsupported_price_basis", "PRVV": "unsupported_price_basis",
        "NOTR": "synthetic_quote_ts"}
    assert res["last_by_symbol"] == {}
    assert res["oldest_source_asof"] is None and res["newest_source_asof"] is None
    assert res["qualification_coverage_pct"] == pytest.approx(0.0)


def test_qualify_one_fresh_name_cannot_launder_a_stale_group():
    quotes = {
        "AAA": _q(sym="AAA", price=10.0, ts=_iso(T_STALE)),
        "BBB": _q(sym="BBB", price=20.0, ts=_iso(T_STALE)),
        "CCC": _q(sym="CCC", price=30.0),
        "ZZZ": _q(sym="ZZZ", price=40.0),        # fresh but OUT of the cohort
    }
    res = lb.qualify_snapshot_members(quotes, ["AAA", "BBB", "CCC"], **_kw())
    assert res["last_by_symbol"] == {"CCC": 30.0}
    assert res["qualified_n"] == 1 and res["eligible_n"] == 3
    assert res["excluded_by_symbol"] == {"AAA": "stale_quote", "BBB": "stale_quote"}
    assert res["qualification_coverage_pct"] == pytest.approx(100.0 / 3)
    # only ADMITTED rows set the admitted source clock — the stale prints and
    # the fresh out-of-cohort ticker refresh nothing
    assert res["oldest_source_asof"] == res["newest_source_asof"] == _iso(T_TRADE)
    assert all("ZZZ" not in res[k] for k in QUAL_KEYS if isinstance(res[k], dict))


def test_qualify_genuine_flat_admitted_and_stale_flat_excluded_for_compute_tier():
    th = {"FLAT": _th(100, 90, 80, 120, 70), "UP": _th(100, 90, 80, 120, 70)}
    quotes = {"FLAT": _q(sym="FLAT", price=100.0), "UP": _q(sym="UP", price=105.0)}
    res = lb.qualify_snapshot_members(quotes, ["FLAT", "UP"], **_kw())
    t = lb.compute_tier("mid", "S&P 400", {"en": "Mid cap", "zh": "中盘"}, th,
                        res["last_by_symbol"])
    assert res["qualified_n"] == 2 and t["n"] == 2
    assert t["unch"] == 1 and t["adv"] == 1 and t["dec"] == 0
    # the same flat print, stale on the source clock, is NOT admitted:
    # compute_tier never sees it, so a stale halt cannot masquerade as a live
    # unchanged name (never coerced to unchanged/zero)
    quotes["FLAT"] = _q(sym="FLAT", price=100.0, ts=_iso(T_STALE))
    res = lb.qualify_snapshot_members(quotes, ["FLAT", "UP"], **_kw())
    assert res["excluded_by_symbol"] == {"FLAT": "stale_quote"}
    assert res["last_by_symbol"] == {"UP": 105.0}
    t = lb.compute_tier("mid", "S&P 400", {"en": "Mid cap", "zh": "中盘"}, th,
                        res["last_by_symbol"])
    assert t["n"] == 1 and t["unch"] == 0 and t["adv"] == 1


def test_qualify_missing_vs_invalid_price_classes():
    quotes = {
        "NANP": _q(sym="NANP", price=float("nan")),
        "INFP": _q(sym="INFP", price=float("inf")),
        "BOOLP": _q(sym="BOOLP", price=True),
        "ZERO": _q(sym="ZERO", price=0),
        "NEG": _q(sym="NEG", price=-3.0),
    }
    res = lb.qualify_snapshot_members(
        quotes, ["GONE", "NANP", "INFP", "BOOLP", "ZERO", "NEG"], **_kw())
    assert res["excluded_by_symbol"]["GONE"] == "missing_quote"
    for sym in ("NANP", "INFP", "BOOLP", "ZERO", "NEG"):
        assert res["excluded_by_symbol"][sym] == "invalid_price"
    assert res["last_by_symbol"] == {} and res["qualified_n"] == 0


def test_qualify_source_identity_basis_and_malformed_rejections():
    quotes = {
        "YHOO": _q(sym="YHOO", source="yahoo"),
        "SWAP": _q(sym="SWAP", ident=_ident("AAPL")),   # identity names another print
        "NOID": _q(sym="NOID", ident={}),               # identity missing entirely
        "BADSC": _q(sym="BADSC", ident={**_ident("BADSC"),
                                        "schema": "native_quote_identity.v2"}),
        "PREV": _q(sym="PREV", basis="prev"),
        "JUNK": "not-a-mapping",
    }
    res = lb.qualify_snapshot_members(quotes, list(quotes), **_kw())
    assert res["excluded_by_symbol"] == {
        "YHOO": "unknown_source", "SWAP": "identity_mismatch",
        "NOID": "identity_mismatch", "BADSC": "identity_mismatch",
        "PREV": "unsupported_price_basis", "JUNK": "malformed_quote"}
    assert res["qualified_n"] == 0


def test_qualify_unknown_or_malformed_source_clock_and_non_bool_synthetic():
    absent = _q(sym="ABSENT")
    del absent["quote_ts_synthetic"]                # flag missing entirely
    quotes = {
        "NOTS": _q(sym="NOTS", ts="not-a-timestamp"),
        "NUMS": _q(sym="NUMS", ts=1794439940000),   # epoch int, not an ISO string
        "NAIV": _q(sym="NAIV", ts="2026-10-30T13:59:00"),   # no tz -> unknown instant
        "ZEROB": _q(sym="ZEROB", synthetic=0),      # falsy but NOT literally False
        "NONEB": _q(sym="NONEB", synthetic=None),
        "ABSENT": absent,
    }
    res = lb.qualify_snapshot_members(quotes, list(quotes), **_kw())
    for sym in ("NOTS", "NUMS", "NAIV"):
        assert res["excluded_by_symbol"][sym] == "invalid_quote_ts"
    for sym in ("ZEROB", "NONEB", "ABSENT"):
        assert res["excluded_by_symbol"][sym] == "synthetic_quote_ts"
    assert res["qualified_n"] == 0


def test_qualify_quote_ahead_of_receipt_is_rejected_not_used():
    quotes = {"FUT": _q(sym="FUT", ts=_iso(RECEIPT + timedelta(minutes=1)))}
    res = lb.qualify_snapshot_members(quotes, ["FUT"], **_kw())
    assert res["excluded_by_symbol"] == {"FUT": "quote_ts_after_receipt"}
    assert res["last_by_symbol"] == {}


def test_qualify_timezone_offsets_normalize_to_utc():
    quotes = {"AAPL": _q(ts="2026-10-30T19:29:00+05:30")}   # == 13:59:00 UTC
    res = lb.qualify_snapshot_members(quotes, ["AAPL"], **_kw())
    assert res["qualified_n"] == 1
    assert res["source_asof_by_symbol"] == {"AAPL": "2026-10-30T13:59:00+00:00"}
    assert res["oldest_source_asof"] == res["newest_source_asof"] == "2026-10-30T13:59:00+00:00"


def test_qualify_session_is_half_open_and_cross_session_prints_rejected():
    # a window fully in the receiver's past so the SESSION check (never the
    # receipt check) is what fires on the edges
    w_start, w_end = _utc(2026, 10, 30, 12, 0), _utc(2026, 10, 30, 13, 0)
    kw = _kw(session_start=w_start, session_end=w_end, max_source_age_min=130)
    res = lb.qualify_snapshot_members(
        {"OPEN": _q(sym="OPEN", ts=_iso(w_start))}, ["OPEN"], **kw)
    assert res["qualified_n"] == 1                          # start edge is INSIDE
    res = lb.qualify_snapshot_members(
        {"END": _q(sym="END", ts=_iso(w_end))}, ["END"], **kw)
    assert res["excluded_by_symbol"] == {"END": "out_of_session"}   # end edge OUTSIDE
    # yesterday's close is rejected by the SESSION check (checked before age)
    res = lb.qualify_snapshot_members(
        {"YDAY": _q(sym="YDAY", ts=_iso(T_PREV_SESSION))}, ["YDAY"], **kw)
    assert res["excluded_by_symbol"] == {"YDAY": "out_of_session"}


def test_qualify_max_age_exact_admitted_just_older_rejected():
    edge = _iso(ASOF_Q - timedelta(minutes=25))             # exactly the SLA age
    over = _iso(ASOF_Q - timedelta(seconds=25 * 60 + 1))    # one second past it
    res = lb.qualify_snapshot_members(
        {"EDGE": _q(sym="EDGE", ts=edge), "OVER": _q(sym="OVER", ts=over)},
        ["EDGE", "OVER"], max_source_age_min=25, **_kw())
    assert res["last_by_symbol"] == {"EDGE": 101.0}
    assert res["excluded_by_symbol"] == {"OVER": "stale_quote"}


def test_qualify_dot_dash_collision_never_last_wins_and_single_dotted_joins():
    dot = _q(sym="BRK.B", price=111.0)
    dash = _q(sym="BRK-B", price=222.0)                     # last-wins would take this
    res = lb.qualify_snapshot_members({"BRK.B": dot, "BRK-B": dash},
                                      ["BRK-B"], **_kw())
    assert res["excluded_by_symbol"] == {"BRK-B": "vendor_key_collision"}
    assert res["last_by_symbol"] == {} and res["qualified_n"] == 0
    # one dotted key alone resolves to the dash member, identity still matching
    res = lb.qualify_snapshot_members({"BRK.B": dot}, ["BRK-B"], **_kw())
    assert res["last_by_symbol"] == {"BRK-B": 111.0}
    assert res["source_asof_by_symbol"] == {"BRK-B": _iso(T_TRADE)}


def test_qualify_empty_cohort_has_none_coverage_and_clocks():
    res = lb.qualify_snapshot_members({"AAPL": _q()}, [], **_kw())
    assert res["eligible_n"] == 0 and res["qualified_n"] == 0
    assert res["qualification_coverage_pct"] is None
    assert res["oldest_source_asof"] is None and res["newest_source_asof"] is None


def test_qualify_does_not_mutate_inputs():
    quotes = {"AAPL": _q(), "STALE": _q(sym="STALE", ts=_iso(T_STALE)),
              "BRK.B": _q(sym="BRK.B", price=111.0)}
    members = ["AAPL", "STALE", "BRK-B"]
    before_quotes = copy.deepcopy(quotes)
    before_members = list(members)
    aapl_ref = quotes["AAPL"]
    lb.qualify_snapshot_members(quotes, members, **_kw())
    assert quotes == before_quotes and members == before_members
    assert quotes["AAPL"] is aapl_ref                       # records untouched in place


def test_qualify_structural_validation_rejects_bad_inputs():
    good = {"AAPL": _q()}
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(["nope"], ["AAPL"], **_kw())       # quotes not a mapping
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(good, "AAPL", **_kw())             # members is one string
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(good, 123, **_kw())                # members not a sequence
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(good, ["AAPL", "AAPL"], **_kw())   # duplicate member
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(good, ["brk.b"], **_kw())          # non-canonical
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(good, [" AAPL "], **_kw())         # non-canonical
    for name in ("observed_at", "asof", "session_start", "session_end"):
        bad = _kw()
        bad[name] = bad[name].replace(tzinfo=None)                     # naive
        with pytest.raises(ValueError):
            lb.qualify_snapshot_members(good, ["AAPL"], **bad)
    bad = _kw()
    bad["asof"] = "2026-10-30"                                         # not a datetime
    with pytest.raises(ValueError):
        lb.qualify_snapshot_members(good, ["AAPL"], **bad)
    with pytest.raises(ValueError):                                    # start >= end
        lb.qualify_snapshot_members(good, ["AAPL"], observed_at=RECEIPT, asof=ASOF_Q,
                                    session_start=SESSION_END, session_end=SESSION_START)
    with pytest.raises(ValueError):                                    # receipt after query
        lb.qualify_snapshot_members(good, ["AAPL"], observed_at=ASOF_Q, asof=RECEIPT,
                                    session_start=SESSION_START, session_end=SESSION_END)
    for bad_age in (True, 0, -1, float("nan"), float("inf"), "10"):
        with pytest.raises(ValueError):
            lb.qualify_snapshot_members(good, ["AAPL"],
                                        max_source_age_min=bad_age, **_kw())


def test_qualify_slots_in_without_changing_the_existing_payload_schema():
    payload = {"tickers": [{**_poly_trade(101.25, T_TRADE), "ticker": "AAPL"}]}
    quotes = lq.parse_polygon_snapshot(payload, now=RECEIPT)
    res = lb.qualify_snapshot_members(quotes, ["AAPL"], **_kw())
    assert set(res.keys()) == QUAL_KEYS                    # additive result shape
    assert "usable" not in res and "verdict" not in res and "measured" not in res
    t = lb.compute_tier("large", "S&P 500", {"en": "L", "zh": "大"},
                        {"AAPL": _th(100, 90, 80, 120, 70)}, res["last_by_symbol"])
    p = lb.build_payload([t], asof="2026-10-30T14:00:00Z", delay_min=6, session="rth")
    assert set(p.keys()) == TOP_KEYS and p["schema"] == "live.breadth.v1"
    assert set(t.keys()) == TIER_KEYS and t["n"] == 1


def test_qualify_future_receipt_refused_across_repeated_local_hour():
    from zoneinfo import ZoneInfo

    # Identical local labels; the later fold is one actual hour after the cutoff.
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    later = first.replace(fold=1)
    with pytest.raises(ValueError, match="observed_at"):
        lb.qualify_snapshot_members({}, [], **_kw(observed_at=later, asof=first))


def test_qualify_unrepresentable_row_does_not_erase_a_valid_peer():
    quotes = {"AAPL": _q(), "B": _q(sym="B", price=10**400),
              "C": _q(sym="C", ts="0001-01-01T00:00:00+14:00")}
    r = lb.qualify_snapshot_members(quotes, list(quotes), **_kw())
    assert r["last_by_symbol"] == {"AAPL": 101.0}
    assert r["excluded_by_symbol"] == {"B": "invalid_price", "C": "invalid_quote_ts"}


def test_qualify_empty_member_and_unrepresentable_global_age_are_invalid():
    with pytest.raises(ValueError, match="canonical"):
        lb.qualify_snapshot_members({}, [""], **_kw())
    with pytest.raises(ValueError, match="max_source_age_min"):
        lb.qualify_snapshot_members({}, [], max_source_age_min=10**400, **_kw())
