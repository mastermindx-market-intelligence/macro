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


# Tiingo's vendor list is a bounded observation, not a new qbus writer.
# These tests deliberately never invoke an HTTP client or use a real receipt.

def tiingo_rights(publishers=("reuters.com",), status="approved"):
    return parse_rights_receipt({
        "schema": "qbus.news_rights_receipt.v1",
        "status": status,
        "receipt_id": "synthetic-tiingo-integration",
        "owner_ref": "TEST-ONLY-NOT-COMMERCIAL-AUTHORITY",
        "source": "tiingo", "product_id": "TEST-ONLY-news",
        "audiences": ["site_full"],
        "effective_at": (T0-timedelta(days=1)).isoformat(),
        "expires_at": (T0+timedelta(days=1)).isoformat(),
        "licensed_publisher_domains": list(publishers),
        "capabilities": {
            "internal_ingestion": True, "historical_retention": True,
            "headline_display": True, "derivative_processing": True,
            "source_link_display": False, "teaser_display": False,
        },
    }, now=T0, source="tiingo")


def tiingo_vendor_article(publisher="reuters.com", article_id=81234):
    return {
        "id": article_id, "source": publisher,
        "url": f"https://www.{publisher}/news/{article_id}",
        "title": f"Nvidia announced a new manufacturing investment {article_id}",
        "description": "Synthetic original-provider observation",
        "publishedDate": (T0-timedelta(hours=1)).isoformat(),
        "crawlDate": (T0-timedelta(minutes=10)).isoformat(),
        "tickers": ["NVDA"], "tags": ["earnings"],
    }


def tiingo_fixture_intake(store, owner_grants, enabled):
    from engine.qbus_news_intake import TiingoSupplementalIntake
    task = TiingoSupplementalIntake(
        token="synthetic-token-never-used",
        store=store,
        rights_provider=lambda: owner_grants[0] if owner_grants else None,
        universe_provider=universe,
        enabled=lambda: enabled[0],
        clock=lambda: T0,
        monotonic=lambda: 0.0,
    )
    task._pool.shutdown(wait=True)
    task._pool = ControlledPool()
    return task


def test_tiingo_supplemental_requires_exact_publisher_rights_before_fetch(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        grants, enabled = [], [False]
        task = tiingo_fixture_intake(store, grants, enabled)
        try:
            task.pump()
            assert not task._pool.calls
            enabled[0] = True
            task._next_poll = 0
            task.pump()
            assert not task._pool.calls
            grants.append(tiingo_rights(()))  # generic Tiingo permission is not sublicensing
            task._next_poll = 0
            task.pump()
            assert not task._pool.calls
            grants[0] = tiingo_rights()
            task._next_poll = 0
            task.pump()
            assert len(task._pool.calls) == 1
            assert store.current_cursor() is None
        finally:
            task.close()


def test_tiingo_uses_incumbent_sqlite_writer_and_read_rights(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        store.commit((), expected_cursor=None, next_cursor="incumbent-primary-cursor")
        grant, enabled = [tiingo_rights()], [True]
        task = tiingo_fixture_intake(store, grant, enabled)
        try:
            task.pump()
            task._pool.future.set_result(([tiingo_vendor_article()], "ok"))
            task.pump()
            assert task.health()["state"] == "available"
            assert task.accepted_reports == 1
            assert store.current_cursor() == "incumbent-primary-cursor"
            rows = store.snapshot("sec-NVDA", cursor=None, limit=10, rights=grant[0].rights).rows
            assert len(rows) == 1
            assert rows[0].source == "tiingo:reuters.com"
            assert rows[0].url == "" and rows[0].teaser == ""
            # Repeated vendor snapshots remain keep-FIRST and never advance REST.
            task._next_poll = 0
            task.pump()
            task._pool.future.set_result(([tiingo_vendor_article()], "ok"))
            task.pump()
            assert task.accepted_reports == 1
            assert store.current_cursor() == "incumbent-primary-cursor"
        finally:
            task.close()


def test_tiingo_rights_revocation_during_fetch_blocks_any_commit(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        grant, enabled = [tiingo_rights()], [True]
        task = tiingo_fixture_intake(store, grant, enabled)
        try:
            task.pump()
            assert len(task._pool.calls) == 1
            grant.clear()
            task._pool.future.set_result(([tiingo_vendor_article()], "ok"))
            task.pump()
            assert task.health()["state"] == "restricted"
            assert task.accepted_reports == 0
            assert not store.snapshot("sec-NVDA", cursor=None, limit=10,
                                      rights=NewsReadRights(frozenset({"tiingo:reuters.com"}))).rows
        finally:
            task.close()


def test_tiingo_denied_original_publisher_never_reaches_writer(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        grant, enabled = [tiingo_rights(("reuters.com",))], [True]
        task = tiingo_fixture_intake(store, grant, enabled)
        try:
            task.pump()
            task._pool.future.set_result(([
                tiingo_vendor_article("fakebloomberg.com", 99),
                tiingo_vendor_article("reuters.com", 81234),
            ], "ok"))
            task.pump()
            assert task.accepted_reports == 1
            rows = store.snapshot("sec-NVDA", cursor=None, limit=10,
                                  rights=NewsReadRights(frozenset({"tiingo:reuters.com", "tiingo:fakebloomberg.com"}))).rows
            assert len(rows) == 1 and rows[0].source == "tiingo:reuters.com"
        finally:
            task.close()


def test_tiingo_disabled_or_failed_fetch_never_changes_primary_cursor(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        grant, enabled = [tiingo_rights()], [True]
        task = tiingo_fixture_intake(store, grant, enabled)
        try:
            task.pump()
            task._pool.future.set_result(([], "http_403"))
            task.pump()
            assert task.accepted_reports == 0
            assert task.health()["state"] == "degraded"
            assert store.current_cursor() is None
            enabled[0] = False
            task._next_poll = 0
            task.pump()
            assert len(task._pool.calls) == 1
        finally:
            task.close()

def test_tiingo_preflight_never_networks_and_fails_closed_on_owner_revocation(
    tmp_path, monkeypatch, capsys,
):
    """Owner receipt + explicit flag are needed even to qualify an add-on."""
    from scripts import run_qbus_news as runner
    rights_path = tmp_path/"primary-owner.json"
    universe_path = tmp_path/"universe.json"
    health_path = tmp_path/"health.json"
    add_on = tmp_path/"tiingo-owner.json"
    for f in (rights_path, universe_path):
        f.write_text("{}")
    from copy import deepcopy
    from unittest.mock import patch
    def tiingo_policy():
        return {
            "schema": "qbus.news_rights_receipt.v1", "status": "approved",
            "receipt_id": "fixture-tiingo", "owner_ref": "SYNTHETIC-only",
            "source": "tiingo", "product_id": "fixture-only",
            "audiences": ["site_full"],
            "effective_at": (T0-timedelta(days=1)).isoformat(),
            "expires_at": (T0+timedelta(days=1)).isoformat(),
            "licensed_publisher_domains": ["reuters.com"],
            "capabilities": {
                "internal_ingestion": True, "historical_retention": True,
                "headline_display": True, "derivative_processing": True,
                "source_link_display": False, "teaser_display": False,
            },
        }
    monkeypatch.setenv("BENZINGA_API_KEY", "synthetic-no-network")
    monkeypatch.setenv("TIINGO_API_KEY", "synthetic-no-network")
    monkeypatch.setenv("TIINGO_NEWS_ENABLED", "1")
    monkeypatch.setattr(runner, "_utc_now", lambda: T0)
    monkeypatch.setattr(runner, "_rights_receipt_for", lambda *a, **kw: object())
    monkeypatch.setattr(runner, "load_universe_snapshot", lambda *a, **kw: universe())
    monkeypatch.setattr(runner.benzinga_news.BenzingaNewsClient, "fetch_delta",
                        lambda *a, **kw: (_ for _ in ()).throw(
                            AssertionError("preflight must not contact provider")))
    base_args = [
        "--check-activation", "--universe-snapshot", str(universe_path),
        "--rights-receipt", str(rights_path),
        "--health-path", str(health_path),
        "--tiingo-news", "--tiingo-rights-file", str(add_on),
    ]
    add_on.write_text(json.dumps(tiingo_policy()))
    assert runner.main(base_args) == 0
    good = json.loads(capsys.readouterr().out)
    assert good["activation_qualified"] and good["tiingo_news_qualified"]
    assert good["tiingo_publisher_count"] == 1
    denied = deepcopy(tiingo_policy())
    denied["status"] = "revoked"
    add_on.write_text(json.dumps(denied))
    assert runner.main(base_args) == 2
    fault = json.loads(capsys.readouterr().out)
    assert fault["error"] == "activation_tiingo_rights_unqualified"
    assert not fault["tiingo_publisher_rights_present"]


def test_multiple_supplements_preserve_runner_writer_and_health_contract(tmp_path):
    from types import SimpleNamespace
    class Probe:
        def __init__(self, name):
            self.name = name
            self.closed = False
            self.pumps = 0
        def pump(self):
            self.pumps += 1
        def health(self):
            return {"provider": self.name, "state": "quiet"}
        def close(self):
            self.closed = True
    with NewsStore(tmp_path/"q.db", source_key="primary") as store:
        a,b=Probe("massive"),Probe("tiingo")
        runner=NewsIngestRunner(
            token="synthetic", store=store, universe_provider=universe,
            direct_client=SimpleNamespace(fetch_delta=lambda **kw: None),
            supplemental=(a,b), clock=lambda:T0,
        )
        report=runner._health_payload("catching_up")
        assert [i["provider"] for i in report["additional_sources"]] == [
            "massive", "tiingo",
        ]
        runner.run(max_connections=0)  # neither socket nor live feed is touched
        assert a.closed and b.closed
        assert store.current_cursor() is None

def test_tiingo_activation_flag_is_explicit_and_off_by_default(monkeypatch):
    from scripts.run_qbus_news import build_parser
    monkeypatch.delenv("MM_TICKER_NEWS_TIINGO_ENABLED", raising=False)
    assert not build_parser().parse_args([]).tiingo_news
    monkeypatch.setenv("MM_TICKER_NEWS_TIINGO_ENABLED", "0")
    assert not build_parser().parse_args([]).tiingo_news
    monkeypatch.setenv("MM_TICKER_NEWS_TIINGO_ENABLED", "true")
    assert not build_parser().parse_args([]).tiingo_news
    monkeypatch.setenv("MM_TICKER_NEWS_TIINGO_ENABLED", "1")
    assert build_parser().parse_args([]).tiingo_news
    monkeypatch.delenv("MM_TICKER_NEWS_TIINGO_ENABLED", raising=False)
    assert build_parser().parse_args(["--tiingo-news"]).tiingo_news
