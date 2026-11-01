"""Integration tests for network acquisition without a second writer."""
from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
import json
import threading
from types import SimpleNamespace

from collectors import benzinga_news
from engine.massive_news import PollBatch
from engine.qbus_news_contract import normalize_massive_news, normalize_news
from engine.qbus_news_intake import SupplementalNewsIntake
from engine.qbus_news_receipts import parse_rights_receipt, load_rights_set
from engine.qbus_news_store import NewsStore, NewsReadRights
from engine.qbus_news_universe import qualify_universe
from scripts.run_qbus_news import NewsIngestRunner, _rights_receipt_for

T0 = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)


def policy(status="approved"):
    return {
        "schema": "qbus.news_rights_receipt.v1", "receipt_id": "fixture-massive",
        "owner_ref": "fixture-only", "status": status, "source": "massive:reuters.com",
        "provider": "massive", "product_id": "fixture", "audiences": ["site_full"],
        "effective_at": (T0-timedelta(days=1)).isoformat(),
        "expires_at": (T0+timedelta(days=1)).isoformat(),
        "capabilities": {"internal_ingestion": True, "historical_retention": True,
                         "headline_display": True, "source_link_display": True,
                         "teaser_display": True, "derivative_processing": False},
    }


def universe():
    return qualify_universe({
        "owner": "security_reference.sp500", "revision": "test-universe",
        "complete": True, "truncated": False, "effective_at": T0-timedelta(days=1),
        "known_at": T0-timedelta(hours=1), "fresh_until": T0+timedelta(days=1),
        "securities": [{"security_id": "sec-NVDA", "ticker": "NVDA", "aliases": ["NVDA"],
                        "valid_from": T0-timedelta(days=100), "valid_to": None,
                        "known_at": T0-timedelta(days=100)}],
    }, asof=T0)


def article(item="m1"):
    return normalize_massive_news({
        "id": item, "title": "Nvidia launches accelerator " + item,
        "article_url": "https://reuters.com/" + item, "description": "Verified summary",
        "published_utc": T0.isoformat(), "tickers": ["NVDA"],
        "publisher": {"name": "Reuters", "homepage_url": "https://reuters.com"},
    }, received_at=T0)


class ControlledPool:
    def __init__(self):
        self.calls = []
        self.future = None

    def submit(self, fn, **kwargs):
        self.calls.append(kwargs)
        self.future = Future()
        return self.future

    def shutdown(self, **kwargs):
        pass


def intake(store, rights):
    item = SupplementalNewsIntake(
        client=SimpleNamespace(poll=lambda **kwargs: None), store=store,
        rights_provider=lambda: rights, universe_provider=universe,
        clock=lambda: T0, monotonic=lambda: 0,
    )
    item._pool.shutdown()
    item._pool = ControlledPool()
    return item


def test_supplemental_completion_commits_on_owner_tick_and_preserves_primary_cursor(tmp_path):
    path = tmp_path/"q.db"
    with NewsStore(path, source_key="primary") as primary:
        primary.commit((), expected_cursor=None, next_cursor="primary-coverage")
        with NewsStore(path, source_key="massive-reference-news") as extra:
            task = intake(extra, [parse_rights_receipt(policy(), now=T0)])
            task.pump()
            assert extra.current_cursor() is None
            task._pool.future.set_result(PollBatch((article(),), T0, True, 1))
            task.pump()  # no primary article is needed to drain a completed batch
            assert json.loads(extra.current_cursor())["checkpoint"] == T0.isoformat()
            assert primary.current_cursor() == "primary-coverage"
            rows = primary.snapshot("sec-NVDA", cursor=None, limit=10, rights=NewsReadRights(frozenset({"massive:reuters.com"}))).rows
            assert len(rows) == 1
            assert task.health()["state"] == "available"
            task.close()


def test_revocation_between_network_submission_and_acceptance_blocks_write(tmp_path):
    rights = [parse_rights_receipt(policy(), now=T0)]
    with NewsStore(tmp_path/"q.db", source_key="extra") as store:
        task = intake(store, rights)
        task.pump()
        rights.clear()
        task._pool.future.set_result(PollBatch((article(),), T0, True, 1))
        task.pump()
        assert store.current_cursor() is None
        assert task.health()["state"] == "restricted"
        assert not store.snapshot("sec-NVDA", cursor=None, limit=10, rights=NewsReadRights(frozenset({"massive:reuters.com"}))).rows
        task.close()


def test_page_budget_resumes_exact_continuation_without_advancing_completed_coverage(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="extra") as store:
        task = intake(store, [parse_rights_receipt(policy(), now=T0)])
        task.pump()
        first = task._pool.calls[-1]
        next_url = "https://api.massive.com/v2/reference/news?cursor=page2"
        task._pool.future.set_result(PollBatch((article(),), T0, False, 10, next_url))
        task.pump()
        checkpoint = json.loads(store.current_cursor())
        assert checkpoint["next_url"] == next_url
        assert task.health()["last_error"] == "page_budget_exhausted"
        task._next_poll = 0
        task.pump()
        assert task._pool.calls[-1]["next_url"] == next_url
        assert task._pool.calls[-1]["since"] == first["since"]
        assert task._pool.calls[-1]["through"] == T0
        task._pool.future.set_result(PollBatch((), T0, True, 1))
        task.pump()
        assert json.loads(store.current_cursor())["next_url"] is None
        task.close()


def test_no_permission_means_no_supplemental_request(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="extra") as store:
        task = intake(store, [])
        task.pump()
        assert task._pool.calls == []
        assert task.health()["state"] == "restricted"
        task.close()


def test_revoked_duplicate_cannot_leave_older_grant_active(tmp_path):
    first, second = tmp_path/"first.json", tmp_path/"second.json"
    first.write_text(json.dumps(policy()))
    second.write_text(json.dumps(policy("revoked")))
    assert load_rights_set((first, second), now=T0) == ()
    assert _rights_receipt_for(first, now=T0, provider="benzinga") is None


def delta(observed_at, revisions=()):
    return benzinga_news.DeltaBatch(
        revisions=revisions, query_since_epoch=0, next_cursor_epoch=int(observed_at.timestamp()),
        gap_unresolved=False, hold_reasons=(), news_pages=1, removed_pages=1,
    )


def live_frame():
    return json.dumps({
        "id": "msg-101", "api_version": "websocket/v1", "kind": "news", "data": {"action": "created", "id": "101",
        "timestamp": "2026-10-20T10:00:03Z", "content": {
            "id": "101", "created": "Tue, 20 Oct 2026 06:00:00 -0400",
            "updated": "Tue, 20 Oct 2026 06:00:02 -0400",
            "title": "Nvidia wins $10 billion contract", "url": "https://benzinga.com/101",
            "stocks": [{"name": "NVDA"}],
        }},
    })


def test_slow_rest_does_not_block_live_acceptance_or_advance_rest_cursor(tmp_path):
    entered, release = threading.Event(), threading.Event()
    current = [T0]
    class Client:
        calls = 0
        def fetch_delta(self, *, cursor_epoch, observed_at):
            self.calls += 1
            if self.calls > 1:
                entered.set()
                assert release.wait(3)
            return delta(observed_at)
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        runner = NewsIngestRunner(token="fixture", store=store, universe_provider=universe,
                                  direct_client=Client(), clock=lambda: current[0])
        try:
            runner._catch_up()
            before = store.current_cursor()
            current[0] = T0+timedelta(seconds=10)
            runner._start_periodic_catchup()
            assert entered.wait(2)
            runner._handle_frame(live_frame())
            assert runner.stats.stream_events == 1
            assert not runner._catchup_future.done()
            assert len(store.snapshot("sec-NVDA", cursor=None, limit=10, rights=NewsReadRights.all_internal()).rows) == 1
            assert store.current_cursor() == before
            release.set()
            runner._catchup_future.result(timeout=3)
            runner._drain_catchup()
            assert store.current_cursor() == str(int(current[0].timestamp()))
            assert runner.stats.catchups_ok == 2
        finally:
            release.set()
            runner._catchup_pool.shutdown(wait=True)


def test_periodic_rights_revocation_refuses_completed_batch(tmp_path):
    admitted = [True]
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        runner = NewsIngestRunner(token="fixture", store=store, universe_provider=universe,
                                  direct_client=SimpleNamespace(fetch_delta=lambda **kwargs: delta(T0)),
                                  admission_guard=lambda: admitted[0])
        runner._catchup_pool.shutdown()
        runner._catchup_pool = ControlledPool()
        runner._start_periodic_catchup()
        runner._catchup_pool.future.set_result(delta(T0))
        admitted[0] = False
        runner._drain_catchup()
        assert store.current_cursor() is None
        assert runner.stop.is_set()


def test_older_periodic_rest_cannot_replace_newer_live_report(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        runner = NewsIngestRunner(token="fixture", store=store, universe_provider=universe,
                                  direct_client=SimpleNamespace(fetch_delta=lambda **kwargs: delta(T0)),
                                  clock=lambda: T0+timedelta(seconds=10))
        runner._catchup_pool.shutdown()
        runner._catchup_pool = ControlledPool()
        runner._start_periodic_catchup()
        runner._handle_frame(live_frame())
        older = normalize_news({
            "id":"101", "title":"Nvidia wins $9 billion contract", "stocks":["NVDA"],
            "url":"https://benzinga.com/101", "created":T0.isoformat(),
            "updated":(T0+timedelta(seconds=1)).isoformat(),
        }, transport="benzinga_rest", received_at=T0+timedelta(seconds=10))
        runner._catchup_pool.future.set_result(delta(T0+timedelta(seconds=10),(older,)))
        runner._drain_catchup()
        rows=store.snapshot("sec-NVDA", cursor=None, limit=10, rights=NewsReadRights.all_internal()).rows
        assert len(rows)==1
        assert rows[0].title=="Nvidia wins $10 billion contract"
        assert store.current_cursor()==str(int((T0+timedelta(seconds=10)).timestamp()))


def test_periodic_rest_failure_does_not_disconnect_or_disable_live_intake(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        runner=NewsIngestRunner(token="fixture", store=store, universe_provider=universe,
                               direct_client=SimpleNamespace(fetch_delta=lambda **kwargs: delta(T0)),clock=lambda:T0)
        runner._catchup_pool.shutdown()
        runner._catchup_pool=ControlledPool()
        runner._start_periodic_catchup()
        runner._catchup_pool.future.set_exception(RuntimeError("fixture failure"))
        runner._drain_catchup()
        runner._handle_frame(live_frame())
        assert runner.stats.catchups_failed==1
        assert runner.stats.stream_events==1
        assert runner.stats.disconnects==0
        assert not runner.stop.is_set()
