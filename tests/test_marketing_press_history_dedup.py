"""Historical RSS replay regression: the daemon's bounded seen ring is not history.

The 2026-08/09/10 posted-state ledger repeats one BEA GDP release three times,
with the identical FeedItem id in its outbox source. These tests never call a
provider or the X publishing API; the outbox fixture is under tmp_path only.
"""
from __future__ import annotations

import json
import socket
from datetime import datetime, timedelta, timezone

import pytest

from engine.marketing import press_lane


_OLD_DAY = "2026-08-26"
_NOW = datetime(2026, 10, 29, 17, 0, tzinfo=timezone.utc)
_FEED_ID = "bea-gdp-release-2024"


def _put_history(tmp_path, *, feed_id=_FEED_ID, day=_OLD_DAY,
                 status="posted", spool=False, source_lane="press"):
    out = tmp_path / "data" / "marketing" / "outbox"
    out.mkdir(parents=True, exist_ok=True)
    row = {
        "id": "ob-archive-01", "as_of": day, "kind": "breaking",
        "account": "mastermind_news", "text": "The older GDP wire item.",
        "source": {"lane": source_lane, "feed_item_id": feed_id},
    }
    name = "items-host.jsonl" if spool else "items.jsonl"
    (out / name).write_text(json.dumps(row) + "\n", encoding="utf-8")
    (out / "status_ledger.jsonl").write_text(
        json.dumps({"id": row["id"], "to": status}) + "\n",
        encoding="utf-8",
    )
    return row


def test_canonical_history_survives_seen_ring_eviction_and_spool(tmp_path):
    _put_history(tmp_path, spool=True)
    assert press_lane._historical_press_feed_days(tmp_path) == {
        _FEED_ID: {_OLD_DAY}
    }


def test_quarantined_or_non_press_rows_do_not_own_feed_identity(tmp_path):
    _put_history(tmp_path, status="quarantined")
    assert press_lane._historical_press_feed_days(tmp_path) == {}
    _put_history(tmp_path, source_lane="hot_tape")
    assert press_lane._historical_press_feed_days(tmp_path) == {}


def test_aged_feed_id_is_skipped_before_paid_generation(tmp_path):
    _put_history(tmp_path)
    feed = {
        "id": _FEED_ID,
        "source": "bea_news", "source_name": "Bureau of Economic Analysis",
        "source_tier": "wire", "url": "https://www.bea.gov/news/2024/example",
        "headline": "Old GDP release repeated", "body_snippet": "GDP rose in 2022.",
        "published_at": _NOW.isoformat(),
    }
    result = press_lane.run_press_tick(
        [feed], root=tmp_path, now=_NOW,
        cfg={"breaking": {"scoring": {"enabled": False}}},
        press_cfg={"wire": {"flagship_top_k_per_day": 0, "tape": {"enabled": False}}},
        state={}, seen_ids=set(), dry_run=True,
    )
    assert any(e.get("reason") == "historical_feed_replay"
               and e.get("id") == _FEED_ID for e in result["skipped"])
    assert not result["emitted"]


def test_same_day_source_is_not_suppressed_by_history_guard(tmp_path):
    _put_history(tmp_path, day=_NOW.date().isoformat())
    days = press_lane._historical_press_feed_days(tmp_path)
    assert not any(day != _NOW.date().isoformat()
                   for day in days[_FEED_ID])


def test_2024_published_release_cannot_be_a_2026_breaking_flash(tmp_path):
    feed = {
        "id": "never-queued-old-source", "source": "bea_news",
        "source_name": "Bureau of Economic Analysis", "source_tier": "wire",
        "url": "https://www.bea.gov/news/2024/old-release",
        "headline": "2022 GDP release", "body_snippet": "Old data.",
        "published_at": "2024-08-26T13:00:00+00:00",
    }
    result = press_lane.run_press_tick(
        [feed], root=tmp_path, now=_NOW,
        cfg={"breaking": {"scoring": {"enabled": False}}},
        press_cfg={"wire": {"max_source_age_hours": 168,
                             "flagship_top_k_per_day": 0, "tape": {"enabled": False}}},
        state={}, seen_ids=set(), dry_run=True,
    )
    assert any(e.get("reason") == "stale_source_timestamp"
               and e.get("id") == feed["id"] for e in result["skipped"])
    assert not result["emitted"]


def test_source_clock_window_keeps_recent_and_unverifiable_separate():
    recent = {"published_at": "2026-10-28T16:00:00Z"}
    assert not press_lane._stale_feed_clock(recent, now=_NOW, max_age_hours=168)
    assert press_lane._stale_feed_clock(recent, now=_NOW, max_age_hours=24)
    # The legacy RSS parser may stamp a missing pubDate with poll time. A
    # missing/unparseable field cannot prove freshness; that is a distinct
    # ingress defect and must not be misrepresented as a detected stale date.
    assert not press_lane._stale_feed_clock({}, now=_NOW, max_age_hours=168)
    assert not press_lane._stale_feed_clock(
        {"published_at": "invalid"}, now=_NOW, max_age_hours=168)


def test_old_bea_archive_path_catches_feed_clock_fallback(tmp_path):
    feed = {
        "id": "first-seen-archive-2024", "source": "bea_news",
        "source_name": "Bureau of Economic Analysis", "source_tier": "wire",
        "url": "https://www.bea.gov/news/2024/gross-domestic-product-2022",
        "headline": "Old GDP release", "body_snippet": "Data for 2022.",
        # This is what breaking_feed._parse_pub_date returns when RSS has NO
        # usable pubDate: today's ingestion clock, not the article's year.
        "published_at": _NOW.isoformat(),
    }
    result = press_lane.run_press_tick(
        [feed], root=tmp_path, now=_NOW,
        cfg={"breaking": {"scoring": {"enabled": False}}},
        press_cfg={"wire": {"flagship_top_k_per_day": 0,
                             "tape": {"enabled": False}}},
        state={}, seen_ids=set(), dry_run=True,
    )
    assert any(e.get("reason") == "stale_official_archive_url"
               for e in result["skipped"])
    assert not result["emitted"]
    # An untrusted domain using the same path does not impersonate BEA, and a
    # genuinely new BEA article is not penalized for citing an old dataset.
    assert not press_lane._stale_bea_release_url(
        {"source": "bea_news", "url": "https://example.com/news/2024/a"}, now=_NOW)
    assert not press_lane._stale_bea_release_url(
        {"source": "bea_news", "url": "https://www.bea.gov/news/2026/a"}, now=_NOW)


@pytest.mark.parametrize(
    ("stamp", "expected_stale"),
    [
        ("0001-01-01T00:00:00+14:00", True),
        ("9999-12-31T23:59:59-12:00", False),
    ],
)
def test_source_clock_extreme_offsets_keep_age_policy(stamp, expected_stale):
    assert press_lane._stale_feed_clock(
        {"published_at": stamp}, now=_NOW, max_age_hours=168
    ) is expected_stale


@pytest.mark.parametrize(
    ("published", "expected_stale"),
    [
        (_NOW - timedelta(days=7), False),
        (_NOW - timedelta(days=7, microseconds=1), True),
        (_NOW - timedelta(days=7) + timedelta(microseconds=1), False),
        (_NOW.astimezone(timezone(timedelta(hours=8))), False),
        ((_NOW - timedelta(hours=169)).astimezone(
            timezone(timedelta(hours=-4))), True),
        ((_NOW - timedelta(hours=169)).replace(tzinfo=None), True),
    ],
)
def test_source_clock_preserves_strict_age_boundary_and_offsets(
        published, expected_stale):
    assert press_lane._stale_feed_clock(
        {"published_at": published.isoformat()}, now=_NOW, max_age_hours=168
    ) is expected_stale


@pytest.mark.parametrize(
    ("stamp", "expected_survivors", "expected_stale"),
    [
        ("0001-01-01T00:00:00+14:00", {"fresh"}, {"boundary", "ordinary-old"}),
        ("9999-12-31T23:59:59-12:00", {"boundary", "fresh"}, {"ordinary-old"}),
    ],
)
def test_extreme_clock_does_not_abort_real_mixed_tick(
        tmp_path, monkeypatch, stamp, expected_survivors, expected_stale):
    from engine.marketing import breaking_summary

    attempts = []

    def forbidden(effect):
        def fail(*args, **kwargs):
            attempts.append(effect)
            raise AssertionError(f"unexpected {effect}")
        return fail

    monkeypatch.setattr(
        breaking_summary, "build_breaking_payload", forbidden("generation"))
    monkeypatch.setattr(
        press_lane, "_emit_outbox_item", forbidden("emission"))
    monkeypatch.setattr(socket.socket, "connect", forbidden("socket"))
    monkeypatch.setattr(socket, "create_connection", forbidden("connection"))
    monkeypatch.setattr(socket, "getaddrinfo", forbidden("DNS"))

    def feed(item_id, headline, published_at):
        return {
            "id": item_id, "source": "reuters", "source_name": "Reuters",
            "source_tier": "wire",
            "url": f"https://example.com/synthetic/{item_id}",
            "headline": headline, "body_snippet": headline,
            "published_at": published_at,
        }

    # The fresh item follows the hostile clock, so an early batch abort cannot
    # masquerade as successful per-item disposition.
    items = [
        feed("boundary", "US GDP grows 2.3% in third quarter", stamp),
        feed("ordinary-old", "US consumer prices rise 0.2% in August",
             (_NOW - timedelta(days=30)).isoformat()),
        feed("fresh", "US retail sales rise 0.4% in September",
             (_NOW - timedelta(hours=1)).isoformat()),
    ]
    result = press_lane.run_press_tick(
        items, root=tmp_path, now=_NOW,
        cfg={
            "breaking": {
                "scoring": {"enabled": False},
                "llm": {"enabled": False},
            },
            "fomc_desk": {"enabled": False},
        },
        press_cfg={"wire": {
            "flagship_top_k_per_day": 0,
            "tape": {"enabled": False},
            "rail_salience_floor": 0,
            "intelligence": {"salience_floor": 0},
        }},
        state={}, seen_ids=set(), dry_run=True,
    )
    assert {
        row["id"] for row in result["skipped"]
        if row["reason"] == "stale_source_timestamp"
    } == expected_stale
    assert {row["item_id"] for row in result["corpus"]} == expected_survivors
    assert {row["id"] for row in result["rail"]} == expected_survivors
    evidence = [
        entry for packet in result["intelligence"]
        for entry in packet["evidence"]
    ]
    assert {entry["event_id"] for entry in evidence} == expected_survivors
    if "boundary" in expected_survivors:
        assert next(row for row in result["corpus"]
                    if row["item_id"] == "boundary")["published_at"] == stamp
        assert next(row for row in result["rail"]
                    if row["id"] == "boundary")["ts"] == stamp
        assert next(entry for entry in evidence
                    if entry["event_id"] == "boundary")["published_at"] == stamp
    assert result["emitted"] == []
    assert attempts == []
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
