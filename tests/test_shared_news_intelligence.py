"""Shared ticker-news: source diversity, rights, quality, and live consistency."""
from datetime import datetime, timedelta, timezone
import asyncio
import json
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine.news_common import ticker_editorial_reason
from engine.qkernel import publisher_category, publisher_tier, source_tier
from engine.qbus_news_receipts import HEALTH_SCHEMA, parse_health_receipt

from engine.qbus_news_contract import normalize_news, normalize_massive_news, NewsContractError
from engine.qbus_news_receipts import parse_rights_receipt, combine_news_rights, load_rights_set
from engine.qbus_news_reducer import reduce_revision
from engine.qbus_news_store import NewsStore, NewsReadRights, RoutedRevision, SourceReadRights
from app.ticker_news_stream import SharedChangeReader

T0 = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
TITLE = "Nvidia launches new AI accelerator"


def benzinga(item="1", title=TITLE, minute=1, securities=("sec-NVDA",)):
    clock = T0 + timedelta(minutes=minute)
    revision = normalize_news({
        "id": item, "title": title, "url": "https://benzinga.com/news/" + item,
        "teaser": "Vendor summary", "created": T0.isoformat(), "updated": clock.isoformat(),
        "stocks": ["NVDA"],
    }, transport="benzinga_rest", received_at=clock + timedelta(seconds=1))
    return RoutedRevision(revision, securities, "universe-test")


def massive_payload(domain="reuters.com", title=TITLE, item="m1"):
    return {
        "id": item, "title": title, "article_url": "https://" + domain + "/news/" + item,
        "description": "Reporting with concrete details.",
        "published_utc": T0.isoformat(), "tickers": ["nvda"],
        "publisher": {"name": "Publisher", "homepage_url": "https://www." + domain},
        "insights": [{"sentiment_reasoning": "MUST NOT STORE"}],
        "image_url": "https://example.test/private.jpg", "body": "MUST NOT STORE",
    }


def massive(domain="reuters.com", title=TITLE, item="m1", securities=("sec-NVDA",)):
    revision = normalize_massive_news(
        massive_payload(domain, title, item), received_at=T0 + timedelta(seconds=1),
    )
    return RoutedRevision(revision, securities, "universe-test")


def all_rights():
    return NewsReadRights(frozenset({"benzinga", "massive:reuters.com", "massive:benzinga.com"}))


def receipt(source="benzinga", teaser=False, derivative=False):
    return {
        "schema": "qbus.news_rights_receipt.v1", "receipt_id": "test-" + source,
        "owner_ref": "fixture-only", "status": "approved", "source": source,
        "provider": "massive" if source.startswith("massive:") else "alpaca",
        "product_id": "fixture", "audiences": ["site_full"],
        "effective_at": (T0 - timedelta(days=1)).isoformat(),
        "expires_at": (T0 + timedelta(days=1)).isoformat(),
        "capabilities": {"internal_ingestion": True, "historical_retention": True,
                         "headline_display": True, "source_link_display": True,
                         "teaser_display": teaser, "derivative_processing": derivative},
    }


def test_general_news_preserves_publisher_and_clocks_without_provider_ai_or_body():
    first = normalize_massive_news(massive_payload(), received_at=T0 + timedelta(seconds=2))
    repeat = normalize_massive_news(massive_payload(), received_at=T0 + timedelta(minutes=10))
    assert first.source == "massive:reuters.com"
    assert first.transport == "massive_news_v2"
    assert first.provider_tickers == ("NVDA",)
    assert first.published_at == T0
    assert first.updated_at is None and first.source_event_at is None
    assert first.revision_id == repeat.revision_id
    assert "MUST NOT STORE" not in repr(first)
    assert reduce_revision(reduce_revision(None, first).state, repeat).disposition == "duplicate"


def test_same_vendor_article_id_from_different_publishers_cannot_collide():
    a = normalize_massive_news(massive_payload(), received_at=T0)
    b = normalize_massive_news(massive_payload(domain="cnbc.com"), received_at=T0)
    assert a.source_item_id == b.source_item_id
    assert a.source != b.source and a.revision_id != b.revision_id


def test_unclocked_changed_content_is_not_fabricated_as_authoritative_correction():
    first = normalize_massive_news(massive_payload(), received_at=T0)
    changed = normalize_massive_news(
        massive_payload(title="Nvidia cancels new AI accelerator"), received_at=T0 + timedelta(hours=1),
    )
    result = reduce_revision(reduce_revision(None, first).state, changed)
    assert result.disposition == "conflict"
    assert result.state.title == TITLE


@pytest.mark.parametrize("homepage", ["javascript:alert(1)", "https://user:secret@reuters.com", "https://reuters.com:9999", "reuters.com"])
def test_invalid_publisher_identity_refused(homepage):
    payload = massive_payload()
    payload["publisher"]["homepage_url"] = homepage
    with pytest.raises(NewsContractError, match="invalid_publisher"):
        normalize_massive_news(payload, received_at=T0)


def test_separate_receipts_cannot_share_teaser_permission():
    receipts = tuple(parse_rights_receipt(r, now=T0) for r in (
        receipt(teaser=False), receipt("massive:reuters.com", teaser=True),
    ))
    rights = combine_news_rights(receipts)
    assert rights.allows("massive:reuters.com", "teaser")
    assert not rights.allows("benzinga", "teaser")
    assert not rights.allows("massive:unapproved.test", "title")


def test_ambiguous_duplicate_source_receipts_fail_closed():
    a = parse_rights_receipt(receipt(), now=T0)
    b = parse_rights_receipt(receipt(teaser=True), now=T0)
    assert not combine_news_rights((a, b)).allowed_sources


def test_receipt_expiry_is_source_local_and_revalidated(tmp_path):
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    paths[0].write_text(json.dumps(receipt()))
    paths[1].write_text(json.dumps(receipt("massive:reuters.com", teaser=True)))
    assert len(load_rights_set(paths, now=T0)) == 2
    revoked = receipt("massive:reuters.com", teaser=True)
    revoked["status"] = "denied"
    paths[1].write_text(json.dumps(revoked))
    current = combine_news_rights(load_rights_set(paths, now=T0))
    assert current.allowed_sources == frozenset({"benzinga"})
    assert not current.allows("benzinga", "teaser")


def test_quality_representative_matches_snapshot_detail_and_stream(tmp_path):
    with NewsStore(tmp_path / "q.db", source_key="test") as store:
        store.commit([massive(), benzinga()], expected_cursor=None, next_cursor="1")
        snapshot = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights())
        assert len(snapshot.rows) == 1
        row = snapshot.rows[0]
        assert row.source == "massive:reuters.com"  # earlier, higher quality report
        assert row.source_count == 2 and row.item_count == 2
        detail = store.story(row.story_id, rights=all_rights())
        changes = store.projected_changes_for_security(
            "sec-NVDA", after_sequence=0, limit=200, rights=all_rights(),
        )
        assert detail.members[0].source == row.source
        assert len(changes.rows) == 1
        assert changes.rows[0].source == row.source
        assert changes.rows[0].title == row.title
        assert changes.next_sequence == row.sequence



def test_accepted_correction_stays_visible_over_an_older_high_quality_report(tmp_path):
    original = "Nvidia wins $8.2 billion contract"
    corrected = "Nvidia wins $9.1 billion contract"
    with NewsStore(tmp_path / "q.db", source_key="test") as store:
        store.commit([massive(title=original), benzinga(title=original)], expected_cursor=None, next_cursor="1")
        before = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights()).rows[0]
        assert before.source == "massive:reuters.com"
        store.commit([benzinga(title=corrected, minute=2)], expected_cursor="1", next_cursor="2")
        current = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights()).rows[0]
        detail = store.story(before.story_id, rights=all_rights())
        changes = store.projected_changes_for_security(
            "sec-NVDA", after_sequence=before.sequence, limit=200, rights=all_rights(),
        )
        assert current.story_id == before.story_id
        assert current.title == detail.members[0].title == changes.rows[0].title == corrected
        assert current.source == detail.members[0].source == changes.rows[0].source == "benzinga"
        assert len(changes.rows) == 1
        assert current.item_count == current.source_count == 2
        assert any(member.title == original for member in detail.members)
        assert current.reporting_state == detail.reporting_state == changes.rows[0].reporting_state == "reports_differ"
        assert changes.rows[0].source_count == current.source_count
        assert changes.rows[0].item_count == current.item_count
        assert changes.rows[0].published_at == current.published_at
        assert changes.rows[0].updated_at == current.updated_at
        assert changes.rows[0].received_at == current.received_at
        # An ineligible competing report cannot disclose a disagreement.
        restricted = store.snapshot(
            "sec-NVDA", limit=20, cursor=None,
            rights=NewsReadRights(frozenset({"massive:reuters.com"})),
        ).rows[0]
        assert restricted.title == original
        assert restricted.reporting_state == "not_compared"
        from app import ticker_news
        full = ticker_news._story_row(current, permitted=frozenset({"benzinga", "massive:reuters.com"}))
        partial = ticker_news._story_row(current, permitted=frozenset({"benzinga"}))
        assert full["reporting_state"] == "reports_differ"
        assert partial["reporting_state"] == "not_compared"
        assert "reporting_sources" not in full and "reporting_sources" not in partial


def test_restricted_best_report_cannot_hide_or_leak_into_eligible_view(tmp_path):
    rights = NewsReadRights(
        frozenset({"benzinga"}),
        source_fields=(SourceReadRights("benzinga", True, True, False),),
    )
    with NewsStore(tmp_path / "q.db", source_key="test") as store:
        store.commit([massive(), benzinga()], expected_cursor=None, next_cursor="1")
        row = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=rights).rows[0]
        change = store.projected_changes_for_security(
            "sec-NVDA", after_sequence=0, limit=200, rights=rights,
        ).rows[0]
        assert row.source == change.source == "benzinga"
        assert row.source_count == row.item_count == 1
        assert row.teaser == change.teaser == ""


def test_two_vendor_deliveries_do_not_count_as_two_publishers(tmp_path):
    with NewsStore(tmp_path / "q.db", source_key="test") as store:
        store.commit([massive("benzinga.com"), benzinga()], expected_cursor=None, next_cursor="1")
        row = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights()).rows[0]
    assert row.item_count == 2 and row.source_count == 1


def test_new_members_extend_subject_union_for_later_dedup(tmp_path):
    with NewsStore(tmp_path / "q.db", source_key="test") as store:
        store.commit([
            benzinga("1", securities=("sec-NVDA",)),
            benzinga("2", minute=2, securities=("sec-NVDA", "sec-AMD")),
            benzinga("3", minute=3, securities=("sec-AMD",)),
        ], expected_cursor=None, next_cursor="1")
        rows = store.snapshot("sec-AMD", limit=20, cursor=None, rights=all_rights()).rows
    assert len(rows) == 1 and rows[0].item_count == 2


def test_display_entities_decode_without_mutating_retained_revision(tmp_path):
    routed = benzinga(title="Nvidia&#39;s AI &amp; cloud update")
    with NewsStore(tmp_path / "q.db", source_key="test") as store:
        store.commit([routed], expected_cursor=None, next_cursor="1")
        row = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights()).rows[0]
    assert row.title == "Nvidia's AI & cloud update"
    assert routed.revision.title == "Nvidia&#39;s AI &amp; cloud update"


def test_stream_work_is_shared_but_entitlements_are_isolated():
    async def scenario():
        shared = SharedChangeReader(ttl_seconds=1)
        calls = []
        def read():
            calls.append(1)
            time.sleep(0.01)
            return "current"
        result = await asyncio.gather(*(shared.read(("db", "NVDA", "rights-a"), read) for _ in range(64)))
        assert result == ["current"] * 64 and len(calls) == 1
        await shared.read(("db", "NVDA", "rights-b"), read)
        assert len(calls) == 2
    asyncio.run(scenario())


def test_cancelled_reader_does_not_cancel_shared_work():
    async def scenario():
        shared = SharedChangeReader()
        started, release = threading.Event(), threading.Event()
        def read():
            started.set()
            assert release.wait(2)
            return "current"
        first = asyncio.create_task(shared.read(("scope",), read))
        while not started.is_set():
            await asyncio.sleep(0)
        second = asyncio.create_task(shared.read(("scope",), read))
        await asyncio.sleep(0)
        first.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await second == "current"
    asyncio.run(scenario())


def test_failed_shared_read_is_not_cached():
    async def scenario():
        shared = SharedChangeReader(ttl_seconds=10)
        def fail():
            raise RuntimeError("temporary")
        with pytest.raises(RuntimeError):
            await shared.read(("scope",), fail)
        assert await shared.read(("scope",), lambda: "recovered") == "recovered"
    asyncio.run(scenario())


@pytest.fixture
def stream_scope(monkeypatch, tmp_path):
    """Exercise the real receipt owner with a controllable clock."""
    from app import ticker_news
    db, rights_path = tmp_path / "q.db", tmp_path / "rights.json"
    policy = receipt(derivative=True)
    clock = [T0]

    class ReceiptClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz) if tz else clock[0].replace(tzinfo=None)

    rights_path.write_text(json.dumps(policy))
    monkeypatch.setenv("MM_TICKER_NEWS_DB", str(db))
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(rights_path))
    monkeypatch.delenv("MM_TICKER_NEWS_ADDITIONAL_RIGHTS", raising=False)
    monkeypatch.setattr(ticker_news, "datetime", ReceiptClock)
    monkeypatch.setattr(ticker_news, "_security_or_404", lambda *a, **k: ("NVDA", "sec-NVDA"))
    with NewsStore(db, source_key="test") as store:
        store.commit([benzinga(title="Nvidia wins $10 billion contract")], expected_cursor=None, next_cursor="1")
    return ticker_news, db, rights_path, policy, clock


@pytest.mark.parametrize("new_revision", [False, True])
def test_stream_purges_on_derivative_revocation_even_without_new_reporting(stream_scope, new_revision):
    ticker_news, db, rights_path, policy, _ = stream_scope

    async def scenario():
        events = []
        async for chunk in ticker_news._sse_events(ticker="NVDA", user={}, after_sequence=0, poll_seconds=0, max_cycles=2):
            events.append(chunk)
            if chunk.startswith("event: upsert"):
                policy["capabilities"]["derivative_processing"] = False
                rights_path.write_text(json.dumps(policy))
                if new_revision:
                    with NewsStore(db, source_key="test") as store:
                        store.commit([benzinga(title="Nvidia wins $11 billion contract", minute=2)], expected_cursor="1", next_cursor="2")
        assert len(events) == 2
        payload = json.loads(next(line[6:] for line in events[0].splitlines() if line.startswith("data: ")))
        assert payload["annotation"] is not None
        assert events[1].startswith("event: restricted")
        assert "$11" not in events[1]
    asyncio.run(scenario())


def test_stream_rechecks_permission_after_waiting_for_shared_read(stream_scope, monkeypatch):
    ticker_news, _, rights_path, policy, _ = stream_scope

    class RevokeDuringRead:
        async def read(self, key, read_page):
            page = read_page()
            policy["capabilities"]["derivative_processing"] = False
            rights_path.write_text(json.dumps(policy))
            return page

    monkeypatch.setattr(ticker_news, "_STREAM_CHANGE_READER", RevokeDuringRead())

    async def scenario():
        events = [chunk async for chunk in ticker_news._sse_events(
            ticker="NVDA", user={}, after_sequence=0, poll_seconds=0, max_cycles=1,
        )]
        assert len(events) == 1 and events[0].startswith("event: restricted")
        assert "$10" not in events[0]
    asyncio.run(scenario())


def test_quiet_stream_expires_a_receipt_without_file_changes(stream_scope):
    ticker_news, _, rights_path, policy, clock = stream_scope
    policy["expires_at"] = (T0 + timedelta(seconds=10)).isoformat()
    rights_path.write_text(json.dumps(policy))
    unchanged = rights_path.stat()

    async def scenario():
        events = []
        async for chunk in ticker_news._sse_events(
            ticker="NVDA", user={}, after_sequence=0, poll_seconds=0, max_cycles=2,
        ):
            events.append(chunk)
            if chunk.startswith("event: upsert"):
                clock[0] = T0 + timedelta(seconds=10)
        assert len(events) == 2
        assert events[0].startswith("event: upsert")
        assert events[1].startswith("event: restricted")
        current = rights_path.stat()
        assert (current.st_ino, current.st_mtime_ns, current.st_size) == (
            unchanged.st_ino, unchanged.st_mtime_ns, unchanged.st_size,
        )
    asyncio.run(scenario())



def test_live_upsert_contains_the_display_fields_needed_without_another_snapshot(stream_scope):
    ticker_news, db, _, _, _ = stream_scope
    with NewsStore.open_readonly(db, source_key="display-contract") as store:
        row = store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=ticker_news._rights_for_user({}),
        ).rows[0]
    expected = ticker_news._story_row(row, permitted=True)

    async def scenario():
        events = [chunk async for chunk in ticker_news._sse_events(
            ticker="NVDA", user={}, after_sequence=0, poll_seconds=0, max_cycles=1,
        )]
        assert len(events) == 1 and events[0].startswith("event: upsert")
        payload = json.loads(next(line[6:] for line in events[0].splitlines() if line.startswith("data: ")))
        for field in (
            "story_id", "sequence", "source", "source_item_id", "source_count",
            "item_count", "title", "url", "teaser", "published_at", "updated_at",
            "received_at", "universe_revision", "reporting_state", "publisher", "quality",
        ):
            assert payload[field] == expected[field], field
        assert payload["projection_sequence"] == expected["sequence"]
        assert "reporting_sources" not in payload
    asyncio.run(scenario())


def test_routine_ticker_templates_are_quality_labels_not_ingestion_drops():
    from engine.news_common import ticker_template_reason
    from engine.qbus_news_quality import story_quality
    assert ticker_template_reason("Apple whale alerts from today's trading session", "benzinga.com") == "routine_options_template"
    assert ticker_template_reason("Analyzing Apple In Comparison To Competitors", "benzinga.com") == "routine_peer_profile"
    assert ticker_template_reason("Apple wins antitrust appeal against competitors", "benzinga.com") is None
    assert ticker_template_reason("Apple whale alerts from today's trading session", "reuters.com") is None
    assert story_quality(title="Apple whale alerts from today's trading session", url="", source="benzinga")[1] == "routine_options_template"


def test_representative_does_not_use_a_denied_teaser_to_win():
    from engine.qbus_news_quality import representative_key
    base = {"title": TITLE, "url": "https://reuters.com/a", "source": "massive:reuters.com",
            "source_item_id": "a", "last_sequence": 1, "teaser": ""}
    with_teaser = {**base, "teaser": "Not permitted in this view"}
    rights = NewsReadRights(frozenset({"massive:reuters.com"}), allow_teaser=False)
    assert representative_key(base, rights) == representative_key(with_teaser, rights)


def test_evidence_bundle_is_revision_bound_and_requires_each_audience_and_derivative_grant(tmp_path):
    from engine.qbus_news_context import news_evidence_bundle
    db, policy_path = tmp_path/"context.db", tmp_path/"policy.json"
    policy = receipt(derivative=True)
    policy_path.write_text(json.dumps(policy))
    first = benzinga(title="Nvidia wins $10 billion contract")
    with NewsStore(db, source_key="test") as store:
        store.commit([first], expected_cursor=None, next_cursor="1")
    args = dict(database=db, security_id="sec-NVDA", receipt_paths=(policy_path,), now=T0)
    bundle = news_evidence_bundle(**args, audience="site_full")
    assert bundle["state"] == "available"
    report = bundle["stories"][0]["reports"][0]
    assert report["revision_id"] == first.revision.revision_id
    assert report["title"] == first.revision.title
    assert report["teaser"] == ""  # a derivative grant does not broaden field rights
    assert bundle["publication_authorized"] is False
    assert news_evidence_bundle(**args, audience="marketing_draft")["state"] == "restricted"
    policy["capabilities"]["derivative_processing"] = False
    policy_path.write_text(json.dumps(policy))
    revoked = news_evidence_bundle(**args, audience="site_full")
    assert revoked["state"] == "restricted"
    assert revoked["stories"] == []


def test_evidence_reread_after_correction_carries_new_revision_and_hash(tmp_path):
    from engine.qbus_news_context import news_evidence_bundle
    db, policy_path = tmp_path/"context.db", tmp_path/"policy.json"
    policy = receipt(derivative=True)
    policy_path.write_text(json.dumps(policy))
    args = dict(database=db, security_id="sec-NVDA", receipt_paths=(policy_path,), now=T0, audience="site_full")
    with NewsStore(db, source_key="test") as store:
        store.commit([benzinga()], expected_cursor=None, next_cursor="1")
        before = news_evidence_bundle(**args)
        correction = benzinga(title="Nvidia delays new AI accelerator", minute=2)
        store.commit([correction], expected_cursor="1", next_cursor="2")
        after = news_evidence_bundle(**args)
    assert after["evidence_sha256"] != before["evidence_sha256"]
    assert after["stories"][0]["reports"][0]["revision_id"] == correction.revision.revision_id
    assert after["stories"][0]["reports"][0]["title"] == correction.revision.title


def test_snapshot_rows_and_delivery_watermark_share_one_read_view(tmp_path):
    db = tmp_path / "atomic-view.db"
    with NewsStore(db, source_key="writer") as writer:
        writer.commit([benzinga()], expected_cursor=None, next_cursor="1")
        with NewsStore.open_readonly(db, source_key="reader") as reader:
            fired = []

            def commit_between_snapshot_queries(sql):
                if not fired and "SELECT m.cluster_id, s.last_sequence" in sql:
                    fired.append(True)
                    writer.commit(
                        [benzinga(title="Nvidia delays new AI accelerator", minute=2)],
                        expected_cursor="1", next_cursor="2",
                    )

            reader._conn.set_trace_callback(commit_between_snapshot_queries)
            before = reader.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights())
            reader._conn.set_trace_callback(None)
            assert fired
            assert before.change_sequence == before.rows[0].sequence == 1
            assert before.rows[0].title == TITLE
            assert not reader._conn.in_transaction

            after = reader.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights())
            assert after.change_sequence == after.rows[0].sequence == 2
            assert after.rows[0].title == "Nvidia delays new AI accelerator"


def test_snapshot_delivery_watermark_is_independent_of_visible_page(tmp_path):
    from app.ticker_news import _snapshot_payload
    with NewsStore(tmp_path / "watermark.db", source_key="writer") as store:
        store.commit(
            [benzinga(), benzinga("apple", "Apple opens a new service center", securities=("sec-AAPL",))],
            expected_cursor=None, next_cursor="2",
        )
        page = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights())
        empty = store.snapshot("sec-MSFT", limit=20, cursor=None, rights=all_rights())
        assert page.rows[0].sequence == 1
        assert page.change_sequence == empty.change_sequence == 2
        assert empty.rows == ()
        payload = _snapshot_payload(
            ticker="NVDA", security_id="sec-NVDA", snapshot=page,
            health={"state": "live"}, permitted=False,
        )
        assert payload["change_sequence"] == 2
        assert payload["next_cursor"] == 1


def test_current_group_order_does_not_skip_unconsumed_journal_rows(tmp_path):
    with NewsStore(tmp_path / "projection-order.db", source_key="writer") as store:
        store.commit(
            [
                benzinga("deal", "Nvidia acquisition consideration is $8.2 billion", minute=1),
                benzinga("factory", "Nvidia wins regulatory approval for a new factory", minute=2),
                benzinga("deal", "Nvidia acquisition consideration rises to $9.1 billion", minute=3),
            ],
            expected_cursor=None, next_cursor="3",
        )
        snapshot = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=all_rights())
        first = store.projected_changes_for_security(
            "sec-NVDA", after_sequence=0, limit=1, rights=all_rights(),
        )
        assert first.rows[0].sequence == first.next_sequence == 1
        assert first.rows[0].projection_sequence == snapshot.rows[0].sequence == 3
        assert first.rows[0].title == snapshot.rows[0].title
        assert "$9.1" in first.rows[0].title
        second = store.projected_changes_for_security(
            "sec-NVDA", after_sequence=first.next_sequence, limit=1, rights=all_rights(),
        )
        assert second.rows[0].sequence == second.next_sequence == 2
        assert second.rows[0].projection_sequence == snapshot.rows[1].sequence == 2
        assert "factory" in second.rows[0].title


def test_comparison_requires_two_visible_reports():
    from types import SimpleNamespace
    from engine.qbus_news_quality import reporting_state

    first = {"source": "benzinga", "title": "Nvidia wins a $10 billion contract"}
    second = {"source": "massive:reuters.com", "title": "Nvidia wins a $20 billion contract"}
    assert reporting_state([]) == "not_compared"
    assert reporting_state([first]) == "not_compared"
    assert reporting_state([first, second]) == "reports_differ"
    visible_first_only = SimpleNamespace(allows=lambda source, field: source == "benzinga")
    assert reporting_state([first, second], visible_first_only) == "not_compared"
    no_titles = SimpleNamespace(allows=lambda source, field: False)
    assert reporting_state([first, second], no_titles) == "not_compared"
    assert reporting_state([first, {**second, "title": first["title"]}]) == "no_material_difference"


def test_receipt_read_keeps_event_loop_responsive_and_rechecks_revocation(stream_scope, monkeypatch):
    ticker_news, _, rights_path, policy, _ = stream_scope
    original = ticker_news._rights_for_user
    entered, release = threading.Event(), threading.Event()
    event_loop_thread = threading.get_ident()

    def blocked_rights(user):
        assert threading.get_ident() != event_loop_thread, "receipt IO blocked the event loop"
        entered.set()
        assert release.wait(3), "test did not release the receipt reader"
        return original(user)

    monkeypatch.setattr(ticker_news, "_rights_for_user", blocked_rights)

    async def scenario():
        stream = ticker_news._sse_events(
            ticker="NVDA", user={}, after_sequence=0, poll_seconds=0, max_cycles=1,
        )
        first = asyncio.create_task(anext(stream))
        try:
            async def until_read_started():
                while not entered.is_set():
                    if first.done():
                        await first
                    await asyncio.sleep(0)
            await asyncio.wait_for(until_read_started(), 2)
            # The loop can process revocation while filesystem work is pending.
            assert not first.done()
            policy["status"] = "revoked"
            rights_path.write_text(json.dumps(policy))
            release.set()
            frame = await asyncio.wait_for(first, 2)
            assert frame.startswith("event: restricted") and "$10" not in frame
        finally:
            release.set()
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
            await stream.aclose()
    asyncio.run(scenario())


def test_blocking_read_pool_bounds_cancelled_work_and_never_reuses_permissions():
    from app.ticker_news_stream import BlockingReadPool

    async def scenario():
        pool = BlockingReadPool(concurrency=2)
        release = threading.Event()
        started = []
        def blocked(value):
            started.append(value)
            assert release.wait(3)
            return value
        first = asyncio.create_task(pool.read(lambda: blocked("first")))
        second = asyncio.create_task(pool.read(lambda: blocked("second")))
        third = None
        try:
            async def until_two_reads():
                while len(started) < 2:
                    await asyncio.sleep(0)
            await asyncio.wait_for(until_two_reads(), 2)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            third = asyncio.create_task(pool.read(lambda: blocked("third")))
            for _ in range(20):
                await asyncio.sleep(0)
            assert started == ["first", "second"] or started == ["second", "first"]
            assert not third.done()
            release.set()
            assert await asyncio.wait_for(second, 2) == "second"
            assert await asyncio.wait_for(third, 2) == "third"
            current = ["grant"]
            assert await pool.read(lambda: current[0]) == "grant"
            current[0] = "revoked"
            assert await pool.read(lambda: current[0]) == "revoked"
            def fail():
                raise OSError("fixture failure")
            with pytest.raises(OSError):
                await pool.read(fail)
            assert await pool.read(lambda: "recovered") == "recovered"
        finally:
            release.set()
            tasks = [task for task in (first, second, third) if task is not None]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.run(scenario())


# Editorial admission is independent from transport and display rights.
_EDITORIAL_T0 = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
_EDITORIAL_SECURITY = 'sec-NVDA'
_EDITORIAL_GOOD = 'Nvidia launches new AI accelerator'
_EDITORIAL_OTHER = 'Nvidia secures export approval for its data center chips'
_EDITORIAL_FOOL = "Where Will VGT Be in 20 Years? Here's What History Suggests."
_EDITORIAL_ZACKS = 'AI Stock Sell-Off: Are Mag 7 Stocks Still Buys? ETFs in Focus'

def _editorial_report(source, item, title, minute=1, *, url=None):
    clock = _EDITORIAL_T0 + timedelta(minutes=minute)
    if source == 'benzinga':
        rev = normalize_news({'id': item, 'title': title, 'url': url or 'https://benzinga.com/news/' + item, 'teaser': 'Fictional test summary.', 'created': _EDITORIAL_T0.isoformat(), 'updated': clock.isoformat(), 'stocks': ['NVDA']}, transport='benzinga_rest', received_at=clock)
    else:
        domain = source.removeprefix('massive:')
        rev = normalize_massive_news({'id': item, 'title': title, 'article_url': 'https://' + domain + '/news/' + item, 'description': 'Fictional test summary.', 'published_utc': clock.isoformat(), 'tickers': ['NVDA'], 'publisher': {'name': 'Fixture', 'homepage_url': 'https://' + domain}}, received_at=clock)
    return RoutedRevision(rev, (_EDITORIAL_SECURITY,), 'fixture-universe')

def _editorial_commit(store, rows):
    return store.commit(rows, expected_cursor=store.current_cursor(), next_cursor=str(store.counts()['revisions'] + len(rows)))

def _editorial_rights(*sources):
    return NewsReadRights(frozenset(sources or ('benzinga',)))

def _editorial_parsed_health(state='live', extra_state='available', publishers=None):
    clock = _EDITORIAL_T0 + timedelta(hours=1)
    return parse_health_receipt({'schema': HEALTH_SCHEMA, 'source': 'benzinga', 'state': state, 'observed_at': clock.isoformat(), 'last_successful_catchup': clock.isoformat(), 'gap_unresolved': False, 'additional_sources': [{'provider': 'massive', 'state': extra_state, 'publishers': publishers if publishers is not None else ['fool.com', 'globenewswire.com', 'zacks.com'], 'accepted_reports': 100, 'last_successful_poll': clock.isoformat()}]}, now=clock)

def _editorial_reader(db):
    return NewsStore.open_readonly(db, source_key='test', curated=True)

@pytest.mark.parametrize('domain,title,reason', [('fool.com', _EDITORIAL_FOOL, 'publisher_excluded'), ('zacks.com', _EDITORIAL_ZACKS, 'publisher_excluded'), ('www.FOOL.com', _EDITORIAL_GOOD, 'publisher_excluded'), ('news.zacks.com', _EDITORIAL_GOOD, 'publisher_excluded'), ('tipranks.com', _EDITORIAL_GOOD, 'publisher_excluded'), ('benzinga.com', _EDITORIAL_FOOL, 'single_stock_advertorial'), ('cnbc.com', '5 Stocks to Buy Now', 'stock_pick_roundup'), ('benzinga.com', 'What to watch ahead of Nvidia earnings', 'calendar_preview'), ('benzinga.com', 'Nvidia reports after the closing bell', 'calendar_preview'), ('benzinga.com', 'Nvidia earnings preview: what to expect', 'calendar_preview'), ('benzinga.com', 'Closing bell: Nvidia reports record revenue', 'calendar_preview'), ('benzinga.com', 'Live updates: Nvidia reports record revenue after the closing bell', 'calendar_preview'), ('benzinga.com', 'Stocks making the biggest moves: Microsoft raises its dividend ahead of earnings', 'calendar_preview'), ('benzinga.com', 'Earnings calendar: Microsoft raises its dividend ahead of earnings', 'calendar_preview'), ('benzinga.com', 'Nvidia could report record revenue after the closing bell', 'calendar_preview'), ('unknown.example', _EDITORIAL_GOOD, 'publisher_unreviewed'), ('notreuters.com', _EDITORIAL_GOOD, 'publisher_unreviewed'), ('reuters.com.attacker.example', _EDITORIAL_GOOD, 'publisher_unreviewed'), ('example.com', _EDITORIAL_GOOD, 'publisher_unreviewed'), ('globenewswire.com', 'SHAREHOLDER ALERT: Deadline Reminder for Investors', 'solicitation_press_release')])
def test_publisher_and_article_policy_catches_reported_leaks(domain, title, reason):
    assert ticker_editorial_reason(title, domain) == reason

@pytest.mark.parametrize('domain,title', [('reuters.com', _EDITORIAL_GOOD), ('www.bloomberg.com', _EDITORIAL_OTHER), ('benzinga.com', 'Nvidia raises quarterly dividend by 10%'), ('benzinga.com', 'Microsoft raises its dividend ahead of earnings'), ('benzinga.com', 'Nvidia reports record revenue after the closing bell'), ('benzinga.com', 'Nvidia reports $20 billion in quarterly revenue before the open'), ('benzinga.com', 'Aster secures FDA approval ahead of earnings'), ('globenewswire.com', 'Aster reports record quarterly revenue'), ('businesswire.com', 'Aster announces FDA approval of its new therapy'), ('cnbc.com', 'Why did Nvidia shares fall after its earnings beat?')])
def test_factual_reporting_and_primary_announcements_survive(domain, title):
    assert ticker_editorial_reason(title, domain) is None

def test_canonical_tiers_do_not_upgrade_excluded_or_lookalike_publishers():
    assert source_tier('fool.com') == source_tier('zacks.com') == 0
    assert publisher_tier('notreuters.com') == publisher_tier('reuters.com.evil.test') == 0
    assert publisher_category('globenewswire.com') == 'press_release'
    assert publisher_category('benzinga.com') == 'reporting'

def test_filter_precedes_limit_and_pagination_and_preserves_raw_history(tmp_path):
    db = tmp_path / 'news.sqlite3'
    with NewsStore(db, source_key='test') as store:
        _editorial_commit(store, [_editorial_report('benzinga', 'good', _EDITORIAL_GOOD), _editorial_report('benzinga', 'other', _EDITORIAL_OTHER)])
        _editorial_commit(store, [_editorial_report('benzinga', str(i), f'Prediction: Nvidia shares will reach ${i + 1000}', i + 2) for i in range(35)])
        _editorial_commit(store, [_editorial_report('massive:fool.com', 'f', _EDITORIAL_FOOL), _editorial_report('massive:zacks.com', 'z', _EDITORIAL_ZACKS)])
        before = store.counts()
    grant = _editorial_rights('benzinga', 'massive:fool.com', 'massive:zacks.com')
    with _editorial_reader(db) as store:
        first = store.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=None, rights=grant)
        assert len(first.rows) == 1 and first.has_more
        second = store.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=first.next_cursor, rights=grant)
        assert len(second.rows) == 1 and (not second.has_more)
        assert {first.rows[0].title, second.rows[0].title} == {_EDITORIAL_GOOD, _EDITORIAL_OTHER}
        assert store.counts() == before
        flow = store.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=grant)
        assert flow['reports_24h'] == 2 and flow['stories_24h'] == 2
        assert flow['provenance']['sources_counted'] == ['benzinga']
    with NewsStore.open_readonly(db, source_key='test') as store:
        assert len(store.snapshot(_EDITORIAL_SECURITY, limit=100, cursor=None, rights=grant).rows) > 20

def test_group_details_and_source_counts_use_only_curated_reports(tmp_path):
    db = tmp_path / 'news.sqlite3'
    grant = _editorial_rights('massive:reuters.com', 'massive:fool.com')
    with NewsStore(db, source_key='test') as store:
        _editorial_commit(store, [_editorial_report('massive:reuters.com', 'r', _EDITORIAL_GOOD), _editorial_report('massive:fool.com', 'f', _EDITORIAL_GOOD)])
        raw = store.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=grant)
        assert raw.rows[0].item_count == 2
        story_id = raw.rows[0].story_id
    with _editorial_reader(db) as store:
        row = store.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=grant).rows[0]
        detail = store.story(story_id, rights=grant)
        assert row.source_count == row.item_count == detail.source_count == detail.item_count == 1
        assert [member.source for member in detail.members] == ['massive:reuters.com']
        changes = store.projected_changes_for_security(_EDITORIAL_SECURITY, after_sequence=0, limit=50, rights=grant)
        assert len(changes.rows) == 1 and changes.rows[0].source == 'massive:reuters.com'

def test_correction_to_advertorial_emits_removal_and_can_be_restored(tmp_path):
    db = tmp_path / 'news.sqlite3'
    with NewsStore(db, source_key='test') as writer:
        _editorial_commit(writer, [_editorial_report('benzinga', 'one', _EDITORIAL_GOOD)])
        with _editorial_reader(db) as store:
            snapshot = store.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=_editorial_rights())
            story_id = snapshot.rows[0].story_id
            _editorial_commit(writer, [_editorial_report('benzinga', 'one', _EDITORIAL_FOOL, 2)])
            page = store.projected_changes_for_security(_EDITORIAL_SECURITY, after_sequence=snapshot.change_sequence, limit=50, rights=_editorial_rights())
            assert len(page.rows) == 1 and page.rows[0].kind == 'remove'
            assert page.rows[0].title == page.rows[0].teaser == page.rows[0].url == ''
            assert page.next_sequence > snapshot.change_sequence
            assert store.story(story_id, rights=_editorial_rights()) is None
            assert store.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=_editorial_rights())['reports_24h'] == 0
            _editorial_commit(writer, [_editorial_report('benzinga', 'one', _EDITORIAL_GOOD, 3)])
            restored = store.projected_changes_for_security(_EDITORIAL_SECURITY, after_sequence=page.next_sequence, limit=50, rights=_editorial_rights())
            assert len(restored.rows) == 1 and restored.rows[0].kind == 'upsert'
            assert restored.rows[0].title == _EDITORIAL_GOOD

def test_quality_never_grants_rights_or_uses_a_hidden_title(tmp_path):
    db = tmp_path / 'news.sqlite3'
    with NewsStore(db, source_key='test') as writer:
        _editorial_commit(writer, [_editorial_report('massive:reuters.com', 'r', _EDITORIAL_GOOD)])
    with _editorial_reader(db) as store:
        assert not store.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=_editorial_rights()).rows
        no_title = NewsReadRights(frozenset({'massive:reuters.com'}), allow_title=False)
        assert not store.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=no_title).rows

def test_real_api_open_path_filters_snapshot_details_changes_and_labels_releases(monkeypatch, tmp_path):
    from app import ticker_news
    db = tmp_path / 'news.sqlite3'
    sources = ('benzinga', 'massive:fool.com', 'massive:zacks.com', 'massive:globenewswire.com')
    with NewsStore(db, source_key='test') as store:
        _editorial_commit(store, [_editorial_report('massive:fool.com', 'f', _EDITORIAL_FOOL), _editorial_report('massive:zacks.com', 'z', _EDITORIAL_ZACKS)])
        excluded_id = store.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=_editorial_rights(*sources)).rows[0].story_id
        _editorial_commit(store, [_editorial_report('massive:globenewswire.com', 'p', 'Aster reports record quarterly revenue')])
    monkeypatch.setattr(ticker_news, '_news_db_path', lambda: db)
    monkeypatch.setattr(ticker_news, '_security_for_ticker', lambda ticker, now: _EDITORIAL_SECURITY)
    monkeypatch.setattr(ticker_news, '_rights_for_user', lambda user: _editorial_rights(*sources))
    monkeypatch.setattr(ticker_news, '_source_health', _editorial_parsed_health)
    monkeypatch.setattr(ticker_news, '_derivative_permitted_after_rights', lambda: True)
    monkeypatch.setattr(ticker_news, '_flow_now', lambda: _EDITORIAL_T0 + timedelta(hours=1))
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {'id': 'editorial-fixture'}
    with TestClient(app) as client:
        response = client.get('/api/ticker-news/NVDA')
        assert response.status_code == 200
        payload = response.json()
        assert payload['editorial_policy'] == 'ticker_news.curated.v1'
        assert len(payload['rows']) == 1
        assert payload['rows'][0]['content_kind'] == 'press_release'
        assert payload['flow']['reports_24h'] == 1
        assert payload['source_health']['additional_sources'] == [{'provider': 'massive', 'state': 'available', 'configured_publishers': ['globenewswire.com'], 'last_successful_poll': (_EDITORIAL_T0 + timedelta(hours=1)).isoformat(), 'delivery': 'polled'}]
        assert client.get('/api/ticker-news/stories/' + excluded_id).status_code == 404
        changes = client.get('/api/ticker-news/NVDA/changes').json()
        assert len(changes['rows']) == 1 and changes['rows'][0]['content_kind'] == 'press_release'
        assert response.headers['cache-control'] == 'private, no-store'

def test_excluded_publisher_health_cannot_degrade_or_rescue_curated_delivery():
    from app import ticker_news
    raw = _editorial_parsed_health(extra_state='unavailable', publishers=['fool.com', 'zacks.com'])
    scoped = ticker_news._curated_health(raw, _editorial_rights('benzinga', 'massive:fool.com', 'massive:zacks.com'))
    assert scoped['additional_sources'] == []
    assert ticker_news._state_from_health(scoped, row_count=1) == 'live'
    assert len(raw['additional_sources'][0]['configured_publishers']) == 2
    raw['state'] = 'unavailable'
    raw['additional_sources'][0]['state'] = 'available'
    scoped = ticker_news._curated_health(raw, _editorial_rights('massive:fool.com', 'massive:zacks.com'))
    assert ticker_news._state_from_health(scoped, row_count=0) == 'unavailable'

def test_health_does_not_claim_a_title_restricted_publisher():
    from app import ticker_news
    scoped = ticker_news._curated_health({'state': 'live'}, NewsReadRights(frozenset({'benzinga'}), allow_title=False))
    assert scoped['state'] == 'unavailable'
    assert scoped['last_successful_catchup'] is None

@pytest.mark.parametrize('primary,additional,expected', [('unavailable', 'available', 'degraded'), ('live', 'unavailable', 'degraded'), ('live', 'available', 'live')])
def test_curated_health_preserves_qualified_parsed_additional_source(primary, additional, expected):
    from app import ticker_news
    parsed = _editorial_parsed_health(state=primary, extra_state=additional)
    scoped = ticker_news._curated_health(parsed, _editorial_rights('benzinga', 'massive:globenewswire.com'))
    extra = scoped['additional_sources'][0]
    assert extra['configured_publishers'] == ['globenewswire.com']
    assert 'accepted_reports_since_start' not in extra
    assert parsed['additional_sources'][0]['accepted_reports_since_start'] == 100
    assert ticker_news._state_from_health(scoped, row_count=1) == expected


@pytest.mark.parametrize("title,reason", [
    ("Occidental Petroleum To Rally Over 18%? Here Are 10 Top Analyst Forecasts For Tuesday", "stock_pick_roundup"),
    ("This Apple Analyst Is No Longer Bullish; Here Are Top 5 Downgrades For Tuesday", "stock_pick_roundup"),
    ("Top 5 Analyst Upgrades For Wednesday", "stock_pick_roundup"),
    ("10 Top Analyst Forecasts For Tuesday", "stock_pick_roundup"),
    ("Comparing Apple With Industry Competitors In Technology Hardware, Storage & Peripherals Industry", "routine_peer_profile"),
    ("Industry Comparison: Evaluating Apple Against Competitors In Technology Hardware, Storage & Peripherals Industry", "routine_peer_profile"),
    ("‘Obviously This Is a Finger’: Apple’s ‘Pro and Tell’ Teaser Has Everyone Talking — MacBook Pro Buzz Intensifies", "promotional_hype"),
    ("10 Information Technology Stocks With Whale Alerts In Today’s Session", "routine_options_template"),
    ("5 Financials Stocks With Whale Alerts In Today's Trading Session", "routine_options_template"),
])
def test_live_editorial_template_variants(title, reason):
    assert ticker_editorial_reason(title, "benzinga.com") == reason


@pytest.mark.parametrize("url,reason", [
    ("https://www.benzinga.com/Opinion/26/10/1/market-outlook", "publisher_opinion"),
    ("https://benzinga.com/personal-finance/management/26/10/2/investing-advice", "personal_finance_advice"),
    ("https://www.benzinga.com/%4Fpinion/26/10/1/market-outlook", "publisher_opinion"),
    ("https://benzinga.com/news/26/10/1/opinion-poll", None),
    ("https://benzinga.com/news/26/10/1/report?section=opinion", None),
    ("https://benzinga.com/opinions/26/10/1/report", None),
    ("https://notbenzinga.com/Opinion/1", None),
    ("https://benzinga.com.evil.test/Opinion/1", None),
    ("https://reuters.com/Opinion/1", None),
    ("https://[invalid/Opinion/1", None),
    ("", None),
])
def test_editorial_sections_use_only_exact_publisher_url_categories(url, reason):
    assert ticker_editorial_reason(_EDITORIAL_GOOD, "benzinga.com", url=url) == reason


@pytest.mark.parametrize("title", [
    "Morgan Stanley upgrades Apple to overweight and raises price target to $250",
    "Apple reports $95 billion quarterly revenue after the closing bell",
    "Apple secures regulatory approval for its new device",
    "Apple wins antitrust appeal against competitors",
    "Berkshire increases its Apple holding",
    "SEC issues rules for personal financial advisers",
    "Company IPO shares decline 32% after trading begins",
    "Apple announces October 28 event for touch-screen MacBook Pro",
])
def test_live_editorial_screen_preserves_factual_company_reports(title):
    assert ticker_editorial_reason(title, "benzinga.com") is None


@pytest.mark.parametrize("global_url,source_url", [
    (True, None), (False, None), (False, True), (True, False),
])
def test_url_category_corrections_respect_field_rights_across_every_read(tmp_path, global_url, source_url):
    db = tmp_path / "url-category.sqlite3"
    fields = () if source_url is None else (SourceReadRights("benzinga", True, source_url, True),)
    grant = NewsReadRights(frozenset({"benzinga"}), allow_url=global_url, source_fields=fields)
    can_read_url = grant.allows("benzinga", "url")
    with NewsStore(db, source_key="test") as writer, _editorial_reader(db) as reader:
        _editorial_commit(writer, [_editorial_report("benzinga", "url-change", _EDITORIAL_GOOD)])
        before = reader.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=None, rights=grant)
        story_id = before.rows[0].story_id
        _editorial_commit(writer, [_editorial_report(
            "benzinga", "url-change", _EDITORIAL_GOOD, 2,
            url="https://www.benzinga.com/Opinion/26/10/url-change",
        )])
        current = reader.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=None, rights=grant)
        detail = reader.story(story_id, rights=grant)
        changes = reader.projected_changes_for_security(
            _EDITORIAL_SECURITY, after_sequence=before.change_sequence, limit=20, rights=grant,
        )
        flow = reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=grant)
        assert len(current.rows) == flow["reports_24h"] == flow["stories_24h"] == int(not can_read_url)
        assert (detail is None) == can_read_url
        assert len(changes.rows) == 1
        assert changes.rows[0].kind == ("remove" if can_read_url else "upsert")
        assert changes.rows[0].url == ""
        assert changes.next_sequence > before.change_sequence
        if detail is not None:
            assert detail.members[0].url == ""
        # Raw retention remains independent of this public editorial view.
        assert writer.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=None, rights=_editorial_rights()).rows
        _editorial_commit(writer, [_editorial_report("benzinga", "url-change", _EDITORIAL_GOOD, 3)])
        restored = reader.projected_changes_for_security(
            _EDITORIAL_SECURITY, after_sequence=changes.next_sequence, limit=20, rights=grant,
        )
        assert len(restored.rows) == 1 and restored.rows[0].kind == "upsert"
        assert reader.story(story_id, rights=grant).item_count == 1
        assert reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=grant)["reports_24h"] == 1


@pytest.mark.parametrize("allow_benzinga_url", [True, False])
def test_url_category_projection_keeps_group_members_and_counts_consistent(tmp_path, allow_benzinga_url):
    db = tmp_path / "group-url-category.sqlite3"
    grant = NewsReadRights(
        frozenset({"benzinga", "massive:reuters.com"}),
        source_fields=(
            SourceReadRights("benzinga", True, allow_benzinga_url, True),
            SourceReadRights("massive:reuters.com", True, True, True),
        ),
    )
    with NewsStore(db, source_key="test") as writer:
        _editorial_commit(writer, [
            _editorial_report("massive:reuters.com", "reported", _EDITORIAL_GOOD),
            _editorial_report("benzinga", "opinion", _EDITORIAL_GOOD, 2, url="https://benzinga.com/Opinion/1"),
        ])
    with _editorial_reader(db) as reader:
        page = reader.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=None, rights=grant)
        row = page.rows[0]
        detail = reader.story(row.story_id, rights=grant)
        expected = 1 if allow_benzinga_url else 2
        assert row.item_count == row.source_count == detail.item_count == detail.source_count == expected
        assert {member.source for member in detail.members} == (
            {"massive:reuters.com"} if allow_benzinga_url else {"massive:reuters.com", "benzinga"}
        )
        flow = reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=grant)
        assert flow["reports_24h"] == expected
        assert flow["stories_24h"] == 1


# Article-format and company-reference views are additive reader choices.
from engine.qbus_news_editorial import (
    NewsEditorialView, article_format, company_reference, company_reference_context,
)


def _company_view(mode="company", *, names=("Nvidia",), ticker="NVDA"):
    return NewsEditorialView(mode, company_reference_context(
        security_id=_EDITORIAL_SECURITY, ticker=ticker,
        universe_revision="fixture-universe", names=names,
    ))


@pytest.mark.parametrize("title,kind", [
    ("Benzinga Bulls and Bears: Nvidia, Apple, Aster", "roundup"),
    ("10 Industrials Stocks Whale Activity In Today's Session", "roundup"),
    ("Weekly recap: chip manufacturers", "roundup"),
    ("Nvidia manufacturing developments — Week in review", "roundup"),
    ("$100 Invested In ON Semiconductor 15 Years Ago Would Be Worth This Much Today", "investment_template"),
    ("If You Invested $1000 In JPMorgan Chase Stock 10 Years Ago, You Would Have This Much Today", "investment_template"),
    ("Commentary: what the AI cycle means for suppliers", "commentary"),
])
def test_editorial_view_classifies_explicit_formats_without_claiming_truth(title, kind):
    assert article_format(title, "benzinga")[0] == kind
    assert not _company_view("news").allows("benzinga", title)
    assert _company_view("all").allows("benzinga", title)


@pytest.mark.parametrize("title", [
    "Nvidia reports quarterly revenue of $20 billion",
    "Nvidia and Aster sign a manufacturing agreement",
    "Analyst says Nvidia raises quarterly dividend",
    "Nvidia unveils new processor ahead of next week's event",
    "Nvidia releases a weekly recap feature for enterprise users",
    "Nvidia beats earnings; Apple cuts guidance",
    "Nvidia shares rise after regulator approves acquisition",
    "Nvidia analyst maintains Buy and raises price target",
    "Nvidia supplier halts production after a fire",
])
def test_editorial_view_preserves_unclassified_company_developments(title):
    decision = _company_view().decision("benzinga", title)
    assert decision["format"] == "unclassified"
    assert decision["company_reference"] == "headline"
    assert decision["eligible"] is True


@pytest.mark.parametrize("title,teaser,expected", [
    ("Nvidia reports results", "", "headline"),
    ("Supplier factory closes", "Nvidia says its chip supply will be delayed.", "summary"),
    ("Unrelated company reports results", "", "not_observed"),
    ("Pineapple grower expands", "", "not_observed"),
    ("Shares rise", "$NVDA rose after the announcement.", "summary"),
    ("NASDAQ: NVDA reports results", "", "headline"),
    ("NVDA", "", "not_observed"),
    ("nvidia", "", "not_observed"),
])
def test_company_reference_is_bounded_visible_text_evidence(title, teaser, expected):
    assert company_reference(title, teaser, _company_view().company) == expected


def test_company_reference_handles_legal_suffixes_without_inventing_product_aliases():
    context = company_reference_context(
        security_id="on", ticker="ON", universe_revision="u",
        names=("ON SEMICONDUCTOR CORP",),
    )
    assert company_reference("ON Semiconductor reports results", "", context) == "headline"
    assert company_reference("ON THE RISE", "", context) == "not_observed"
    assert company_reference("$ON reports results", "", context) == "headline"
    assert company_reference("onsemi reports results", "", context) == "not_observed"
    apple = company_reference_context(
        security_id="apple", ticker="AAPL", universe_revision="u", names=("Apple",),
    )
    assert company_reference("Pineapple demand grows", "", apple) == "not_observed"
    assert company_reference("Farmers increase apple production", "", apple) == "not_observed"
    assert company_reference("iPhone production halted", "", apple) == "not_observed"


def test_editorial_context_revision_binds_identity_names_universe_and_view():
    a = _company_view()
    assert a.revision == _company_view().revision
    assert a.revision != _company_view("all").revision
    assert a.revision != _company_view(names=("Nvidia", "Aster")).revision
    other = company_reference_context(
        security_id="another-security", ticker="NVDA", universe_revision="fixture-universe",
        names=("Nvidia",),
    )
    assert a.revision != NewsEditorialView("company", other).revision
    with pytest.raises(ValueError):
        NewsEditorialView("unsupported")


def test_company_reference_profile_names_abstain_on_ambiguity_and_refresh(monkeypatch, tmp_path):
    import pandas as pd
    from engine import news_common

    monkeypatch.setattr(news_common.config, "ROOT", tmp_path)
    path = tmp_path / "data" / "profile" / "profiles.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame({"ticker": ["ZZQ", "ZZQ"], "name": ["Aster Corp", "Birch Corp"]}).to_parquet(path)
    assert news_common.company_reference_names("ZZQ") == ()
    pd.DataFrame({"ticker": ["ZZQ"], "name": ["Aster Corporation"]}).to_parquet(path)
    assert news_common.company_reference_names("ZZQ") == ("Aster Corporation",)
    path.unlink()
    assert news_common.company_reference_names("ZZQ") == ()


def _view_report(item, title, teaser="", minute=1, source="benzinga"):
    clock = _EDITORIAL_T0 + timedelta(minutes=minute)
    if source == "benzinga":
        rev = normalize_news({
            "id": item, "title": title, "teaser": teaser,
            "url": "https://benzinga.com/news/" + item,
            "created": _EDITORIAL_T0.isoformat(), "updated": clock.isoformat(),
            "stocks": ["NVDA"],
        }, transport="benzinga_rest", received_at=clock)
    else:
        domain = source.removeprefix("massive:")
        payload = massive_payload(domain, title, item)
        payload["description"] = teaser
        payload["published_utc"] = clock.isoformat()
        rev = normalize_massive_news(payload, received_at=clock)
    return RoutedRevision(rev, (_EDITORIAL_SECURITY,), "fixture-universe")


def _view_reader(db, mode="company"):
    return NewsStore.open_readonly(db, source_key="test", curated=True, editorial_view=_company_view(mode))


def test_company_view_filters_before_page_limit_and_keeps_broader_history(tmp_path):
    db = tmp_path / "view.sqlite3"
    with NewsStore(db, source_key="test") as writer:
        _editorial_commit(writer, [
            _view_report("real", "Nvidia announces a manufacturing agreement"),
            *[_view_report(str(n), "Aster opens facility " + str(n), minute=n+2) for n in range(25)],
        ])
    rights = _editorial_rights()
    with _view_reader(db) as reader:
        page = reader.snapshot(_EDITORIAL_SECURITY, limit=1, cursor=None, rights=rights)
        assert [row.source_item_id for row in page.rows] == ["real"]
        assert page.has_more is False
        assert reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=rights)["reports_24h"] == 1
        with pytest.raises(Exception, match="editorial_security_mismatch"):
            reader.snapshot("another-security", limit=1, cursor=None, rights=rights)
    with _view_reader(db, "all") as reader:
        assert len(reader.snapshot(_EDITORIAL_SECURITY, limit=100, cursor=None, rights=rights).rows) >= 2
        assert reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=rights)["reports_24h"] == 26
    with NewsStore(db, source_key="test") as writer:
        assert writer.counts()["revisions"] == 26


@pytest.mark.parametrize("allow_teaser", [False, True])
def test_company_view_corrections_use_only_permitted_summary_and_current_counts(tmp_path, allow_teaser):
    db = tmp_path / "view.sqlite3"
    rights = NewsReadRights(
        frozenset({"benzinga"}), source_fields=(SourceReadRights("benzinga", True, True, allow_teaser),),
    )
    with NewsStore(db, source_key="test") as writer:
        _editorial_commit(writer, [_view_report("same", "Supplier signs manufacturing agreement", "Nvidia is the customer.")])
    with _view_reader(db) as reader:
        page = reader.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=rights)
        assert len(page.rows) == int(allow_teaser)
        before_sequence = page.change_sequence
        before_flow = reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=rights)
        assert before_flow["reports_24h"] == int(allow_teaser)
    with NewsStore(db, source_key="test") as writer:
        _editorial_commit(writer, [_view_report("same", "Supplier signs manufacturing agreement", "Aster is the customer.", minute=2)])
    with _view_reader(db) as reader:
        assert reader.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=rights).rows == ()
        changes = reader.projected_changes_for_security(
            _EDITORIAL_SECURITY, after_sequence=before_sequence, limit=20, rights=rights,
        )
        assert all(row.kind == "remove" and not row.title and not row.teaser for row in changes.rows)
        assert reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=rights)["reports_24h"] == 0
    with NewsStore(db, source_key="test") as writer:
        _editorial_commit(writer, [_view_report("same", "Supplier signs manufacturing agreement", "Nvidia is the customer.", minute=3)])
    with _view_reader(db) as reader:
        assert len(reader.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=rights).rows) == int(allow_teaser)


def test_company_view_group_members_details_changes_and_flow_share_one_projection(tmp_path):
    db = tmp_path / "view.sqlite3"
    title = "Supplier signs manufacturing agreement"
    with NewsStore(db, source_key="test") as writer:
        _editorial_commit(writer, [
            _view_report("b", title, "Nvidia is the customer."),
            _view_report("r", title, "Nvidia is the customer.", source="massive:reuters.com"),
        ])
    rights = NewsReadRights(
        frozenset({"benzinga", "massive:reuters.com"}),
        source_fields=(SourceReadRights("benzinga", True, True, False),
                       SourceReadRights("massive:reuters.com", True, True, True)),
    )
    with _view_reader(db) as reader:
        page = reader.snapshot(_EDITORIAL_SECURITY, limit=20, cursor=None, rights=rights)
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row.source == "massive:reuters.com"
        assert row.source_count == row.item_count == 1
        detail = reader.story(row.story_id, rights=rights)
        assert detail.source_count == detail.item_count == len(detail.members) == 1
        changes = reader.projected_changes_for_security(_EDITORIAL_SECURITY, after_sequence=0, limit=20, rights=rights)
        assert len(changes.rows) == 1 and changes.rows[0].source == "massive:reuters.com"
        flow = reader.news_flow(_EDITORIAL_SECURITY, now=_EDITORIAL_T0 + timedelta(hours=1), rights=rights)
        assert flow["reports_24h"] == flow["stories_24h"] == 1
        assert flow["provenance"]["editorial_view"] == _company_view().metadata()
