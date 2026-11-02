from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.qbus_news_universe import qualify_universe

UTC = timezone.utc
ASOF = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def sec(i: int, ticker: str, *, aliases=(), valid_from=None, valid_to=None, known_at=None):
    return {
        "security_id": f"sec-{i}",
        "ticker": ticker,
        "aliases": list(aliases) or [ticker],
        "valid_from": valid_from or (ASOF - timedelta(days=100)),
        "valid_to": valid_to,
        "known_at": known_at or (ASOF - timedelta(days=10)),
    }


def snap(securities, **kw):
    base = {
        "owner": "security_reference.sp500",
        "revision": "sp500-2026-10-04-r1",
        "complete": True,
        "truncated": False,
        "effective_at": ASOF - timedelta(days=1),
        "known_at": ASOF - timedelta(hours=2),
        "fresh_until": ASOF + timedelta(days=2),
        "securities": list(securities),
    }
    base.update(kw)
    return base


def test_variable_constituent_count_is_preserved_not_capped_at_500():
    securities = [sec(i, f"T{i:03d}") for i in range(503)]
    out = qualify_universe(snap(securities), asof=ASOF)
    assert out.status == "qualified"
    assert out.count == 503
    assert len(out.securities) == 503
    assert out.reason_codes == ()


def test_share_classes_remain_distinct_security_ids():
    out = qualify_universe(snap([
        sec(1, "BRK.B", aliases=("BRK.B", "BRK-B")),
        sec(2, "BRK.A", aliases=("BRK.A", "BRK-A")),
    ]), asof=ASOF)
    assert out.status == "qualified"
    assert [x.security_id for x in out.securities] == ["sec-1", "sec-2"]
    assert {b.alias: b.security_id for b in out.alias_bindings}["BRK-B"] == "sec-1"


def test_missing_revision_incomplete_or_truncated_snapshots_are_held():
    missing = qualify_universe(snap([sec(1, "AAPL")], revision=""), asof=ASOF)
    incomplete = qualify_universe(snap([sec(1, "AAPL")], complete=False), asof=ASOF)
    truncated = qualify_universe(snap([sec(1, "AAPL")], truncated=True), asof=ASOF)
    assert missing.status == incomplete.status == truncated.status == "held"
    assert "missing_revision" in missing.reason_codes
    assert "incomplete_snapshot" in incomplete.reason_codes
    assert "truncated_snapshot" in truncated.reason_codes


def test_stale_or_future_top_level_snapshot_is_held():
    stale = qualify_universe(snap([sec(1, "AAPL")], fresh_until=ASOF - timedelta(seconds=1)), asof=ASOF)
    future = qualify_universe(snap([sec(1, "AAPL")], known_at=ASOF + timedelta(seconds=1)), asof=ASOF)
    assert stale.status == future.status == "held"
    assert "stale_snapshot" in stale.reason_codes
    assert "future_snapshot_knowledge" in future.reason_codes


def test_membership_windows_and_row_knowledge_are_point_in_time_filtered():
    rows = [
        sec(1, "KEEP"),
        sec(2, "REMOVED", valid_to=ASOF),
        sec(3, "FUTURE", valid_from=ASOF + timedelta(days=1)),
        sec(4, "UNKNOWN_YET", known_at=ASOF + timedelta(minutes=1)),
    ]
    out = qualify_universe(snap(rows), asof=ASOF)
    assert out.status == "qualified"
    assert [x.ticker for x in out.securities] == ["KEEP"]
    assert out.excluded == (
        ("sec-2", "not_effective_at_asof"),
        ("sec-3", "not_effective_at_asof"),
        ("sec-4", "not_known_at_asof"),
    )


def test_ambiguous_provider_alias_across_active_securities_holds_universe():
    out = qualify_universe(snap([
        sec(1, "AAA", aliases=("COLLIDE",)),
        sec(2, "BBB", aliases=("COLLIDE",)),
    ]), asof=ASOF)
    assert out.status == "held"
    assert out.reason_codes == ("ambiguous_alias",)
    assert out.ambiguous_aliases == ("COLLIDE",)


def test_empty_active_universe_is_not_treated_as_valid_coverage():
    out = qualify_universe(snap([sec(1, "OLD", valid_to=ASOF)]), asof=ASOF)
    assert out.status == "held"
    assert "empty_universe" in out.reason_codes
