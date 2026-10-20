"""Shared ticker-news: source diversity, rights, quality, and live consistency."""
from datetime import datetime, timedelta, timezone
import asyncio
import json
import threading
import time

import pytest

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
