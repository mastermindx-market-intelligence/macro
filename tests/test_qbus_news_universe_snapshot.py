"""Current S&P membership -> canonical qbus-news universe snapshot tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


UTC = timezone.utc
NOW = datetime(2026, 10, 5, 22, 0, tzinfo=UTC)


def _current(*symbols):
    return [{"symbol": symbol} for symbol in symbols]


def _pit(*rows):
    return [
        {
            "ticker": ticker,
            "start_date": start,
            "end_date": end,
            "src": "sp500",
        }
        for ticker, start, end in rows
    ]


def _aliases(*rows):
    out = []
    for membership, market, sid in rows:
        out.extend(
            [
                {
                    "vendor": "membership",
                    "vendor_symbol": membership,
                    "security_id": sid,
                    "valid_from": None,
                    "valid_to": None,
                },
                {
                    "vendor": "yahoo_fetch",
                    "vendor_symbol": market,
                    "security_id": sid,
                    "valid_from": None,
                    "valid_to": None,
                },
            ]
        )
    return out


def _master(*sids):
    return [
        {
            "security_id": sid,
            "issuer_id": "ISS:" + sid.removeprefix("SEC:"),
            "issuer_state": "RESOLVED",
            "listing_key": sid.removeprefix("SEC:"),
            "security_state": None,
            "superseded_by": None,
            "issuer_cik": None,
        }
        for sid in sids
    ]


def test_build_joins_current_membership_to_canonical_security_and_market_alias():
    from engine import qbus_news_universe_snapshot as m

    snapshot = m.build_news_universe_snapshot(
        current_rows=_current("NVDA", "MMC"),
        pit_rows=_pit(
            ("NVDA", "2001-01-01", None),
            ("MMC", "2003-01-01", None),
        ),
        alias_rows=_aliases(
            ("NVDA", "NVDA", "SEC:US-XNAS-NVDA"),
            ("MMC", "MRSH", "SEC:US-XNYS-MMC"),
        ),
        security_rows=_master("SEC:US-XNAS-NVDA", "SEC:US-XNYS-MMC"),
        observed_at=NOW,
        fresh_for=timedelta(hours=36),
        min_count=1,
    )

    assert snapshot["owner"] == "breadth.sp500+reference.security_master"
    assert snapshot["complete"] is True
    assert snapshot["truncated"] is False
    assert len(snapshot["securities"]) == 2
    mmc = next(x for x in snapshot["securities"] if x["ticker"] == "MMC")
    assert mmc["security_id"] == "SEC:US-XNYS-MMC"
    assert mmc["aliases"] == ["MMC", "MRSH"]
    assert snapshot["effective_at"] == "2003-01-01T00:00:00+00:00"
    assert snapshot["known_at"] == NOW.isoformat()
    assert snapshot["fresh_until"] == (NOW + timedelta(hours=36)).isoformat()


def test_revision_excludes_observation_clock_but_known_and_fresh_clocks_move():
    from engine import qbus_news_universe_snapshot as m

    kwargs = dict(
        current_rows=_current("NVDA"),
        pit_rows=_pit(("NVDA", "2001-01-01", None)),
        alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
        security_rows=_master("SEC:US-XNAS-NVDA"),
        fresh_for=timedelta(hours=36),
        min_count=1,
    )
    first = m.build_news_universe_snapshot(observed_at=NOW, **kwargs)
    second = m.build_news_universe_snapshot(
        observed_at=NOW + timedelta(hours=3), **kwargs
    )

    assert first["revision"] == second["revision"]
    assert first["known_at"] != second["known_at"]
    assert first["fresh_until"] != second["fresh_until"]


def test_constituent_count_is_variable_and_never_truncated_to_500():
    from engine import qbus_news_universe_snapshot as m

    symbols = [f"T{i:03d}" for i in range(7)]
    sids = [f"SEC:US-XNAS-{symbol}" for symbol in symbols]
    snapshot = m.build_news_universe_snapshot(
        current_rows=_current(*symbols),
        pit_rows=_pit(*[(s, "2020-01-01", None) for s in symbols]),
        alias_rows=_aliases(*[(s, s, sid) for s, sid in zip(symbols, sids)]),
        security_rows=_master(*sids),
        observed_at=NOW,
        min_count=1,
    )
    assert len(snapshot["securities"]) == 7


def test_current_roster_must_exactly_equal_active_pit_sp500():
    from engine import qbus_news_universe_snapshot as m

    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("NVDA", "AMD"),
            pit_rows=_pit(("NVDA", "2001-01-01", None)),
            alias_rows=_aliases(
                ("NVDA", "NVDA", "SEC:US-XNAS-NVDA"),
                ("AMD", "AMD", "SEC:US-XNAS-AMD"),
            ),
            security_rows=_master("SEC:US-XNAS-NVDA", "SEC:US-XNAS-AMD"),
            observed_at=NOW,
            min_count=1,
        )
    assert exc.value.code == "membership_set_mismatch"


def test_departed_pit_row_is_not_current_and_does_not_cause_mismatch():
    from engine import qbus_news_universe_snapshot as m

    snapshot = m.build_news_universe_snapshot(
        current_rows=_current("NVDA"),
        pit_rows=_pit(
            ("NVDA", "2001-01-01", None),
            ("OLD", "2001-01-01", "2020-01-01"),
        ),
        alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
        security_rows=_master("SEC:US-XNAS-NVDA"),
        observed_at=NOW,
        min_count=1,
    )
    assert [x["ticker"] for x in snapshot["securities"]] == ["NVDA"]


def test_every_current_member_must_resolve_through_membership_alias():
    from engine import qbus_news_universe_snapshot as m

    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("NVDA"),
            pit_rows=_pit(("NVDA", "2001-01-01", None)),
            alias_rows=[],
            security_rows=_master("SEC:US-XNAS-NVDA"),
            observed_at=NOW,
            min_count=1,
        )
    assert exc.value.code == "membership_alias_unresolved"


def test_every_member_requires_current_market_alias_for_provider_routing():
    from engine import qbus_news_universe_snapshot as m

    aliases = _aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA"))
    aliases = [row for row in aliases if row["vendor"] != "yahoo_fetch"]

    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("NVDA"),
            pit_rows=_pit(("NVDA", "2001-01-01", None)),
            alias_rows=aliases,
            security_rows=_master("SEC:US-XNAS-NVDA"),
            observed_at=NOW,
            min_count=1,
        )
    assert exc.value.code == "market_alias_unresolved"


def test_security_master_presence_and_active_state_are_mandatory():
    from engine import qbus_news_universe_snapshot as m

    aliases = _aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA"))
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("NVDA"),
            pit_rows=_pit(("NVDA", "2001-01-01", None)),
            alias_rows=aliases,
            security_rows=[],
            observed_at=NOW,
            min_count=1,
        )
    assert exc.value.code == "security_master_unresolved"

    master = _master("SEC:US-XNAS-NVDA")
    master[0]["security_state"] = "SUPERSEDED_DUPLICATE_MINT"
    master[0]["superseded_by"] = "SEC:US-XNAS-NVDA2"
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("NVDA"),
            pit_rows=_pit(("NVDA", "2001-01-01", None)),
            alias_rows=aliases,
            security_rows=master,
            observed_at=NOW,
            min_count=1,
        )
    assert exc.value.code == "security_master_superseded"


def test_two_current_members_cannot_collapse_to_one_security():
    from engine import qbus_news_universe_snapshot as m

    aliases = _aliases(
        ("AAA", "AAA", "SEC:US-XNYS-SAME"),
        ("BBB", "BBB", "SEC:US-XNYS-SAME"),
    )
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("AAA", "BBB"),
            pit_rows=_pit(
                ("AAA", "2020-01-01", None),
                ("BBB", "2020-01-01", None),
            ),
            alias_rows=aliases,
            security_rows=_master("SEC:US-XNYS-SAME"),
            observed_at=NOW,
            min_count=1,
        )
    assert exc.value.code in {
        "alias_table_invalid",
        "duplicate_security_resolution",
    }


def test_minimum_roster_guard_refuses_suspicious_partial_current_set():
    from engine import qbus_news_universe_snapshot as m

    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(
            current_rows=_current("NVDA"),
            pit_rows=_pit(("NVDA", "2001-01-01", None)),
            alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
            security_rows=_master("SEC:US-XNAS-NVDA"),
            observed_at=NOW,
            min_count=400,
        )
    assert exc.value.code == "current_roster_suspicious"


def test_builder_output_is_already_qualified_by_qbus_universe_contract():
    from engine import qbus_news_universe_snapshot as m
    from engine.qbus_news_universe import qualify_universe

    snapshot = m.build_news_universe_snapshot(
        current_rows=_current("NVDA"),
        pit_rows=_pit(("NVDA", "2001-01-01", None)),
        alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
        security_rows=_master("SEC:US-XNAS-NVDA"),
        observed_at=NOW,
        min_count=1,
    )
    qualified = qualify_universe(snapshot, asof=NOW)
    assert qualified.status == "qualified"
    assert qualified.count == 1
