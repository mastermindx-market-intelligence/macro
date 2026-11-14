"""Historical RSS replay regression: the daemon's bounded seen ring is not history.

The 2026-08/09/10 posted-state ledger repeats one BEA GDP release three times,
with the identical FeedItem id in its outbox source. These tests never call a
provider or the X publishing API; the outbox fixture is under tmp_path only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

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
