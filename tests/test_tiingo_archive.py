"""Offline Tiingo Data OS archive contract tests; no token and no vendor request."""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

import collectors.tiingo_archive as a
from scripts.tiingo_ingest import (
    Task, archive_inventory, boats_subscribe_message, date_ranges,
    load_symbols, main, plan,
)


@pytest.fixture
def lake(tmp_path: Path, monkeypatch):
    # Mock only the externally-mounted pathname in hermetic CI, NEVER the prod CLI.
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    root = tmp_path / "tiingo"
    return a.Archive(root, check_mount=False, free_floor=0)


def test_source_contract_path():
    assert a.request_path("eod-bars", "NVDA", {"endDate": "2020-01-05",
                                              "startDate": "2020-01-01"}) == (
        "/tiingo/daily/NVDA/prices?endDate=2020-01-05&startDate=2020-01-01"
    )
    assert a.request_path("boats-bars", "AAPL", {"resampleFreq": "1min"}) == (
        "/boats/AAPL/prices?resampleFreq=1min"
    )


@pytest.mark.parametrize("sym", ["../secrets", "a/b", "a?token=x", ".", "a b", ""])
def test_symbols_cannot_escape_archive(sym):
    with pytest.raises(ValueError):
        a.symbol_path(sym)


@pytest.mark.parametrize("src,sym", [("fake", "SPY"), ("eod-bars", None),
                                      ("fund-meta", "SPY"), ("boats", "SPY")])
def test_source_allowlist(src, sym):
    with pytest.raises(ValueError):
        a.request_path(src, sym)


def test_api_key_cannot_be_url_query():
    with pytest.raises(ValueError):
        a.request_path("eod-bars", "NVDA", {"token": "nosir"})


def test_empty_root_is_external_only(monkeypatch, tmp_path):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path / "external")
    with pytest.raises(a.TiingoArchiveError):
        a.require_external_root(tmp_path / "ssd", check_mount=False)


def test_mount_unavailable_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path / "not-mounted")
    with pytest.raises(a.TiingoArchiveError, match="not mounted"):
        a.require_external_root(tmp_path / "not-mounted" / "tiingo", check_mount=True)


def test_storage_reserve_blocks_before_file(lake):
    with pytest.raises(a.TiingoArchiveError, match="space reserve"):
        a.require_space(lake.root, floor=10**30)


def test_raw_digest_idempotence_and_correspondence(lake):
    data = b'[{"date":"2026-10-07","close":192,"adjClose":190.5}]'
    path = a.request_path("eod-bars", "NVDA", {"startDate": "2026-10-07"})
    r1 = lake.store_response("eod-bars", "NVDA", path, data,
                             received_at="2026-10-09T08:00:00+00:00")
    r2 = lake.store_response("eod-bars", "NVDA", path, data,
                             received_at="2026-10-09T09:00:00+00:00")
    assert r1["new_raw"] and not r2["new_raw"]
    stored = lake.root / r1["path"]
    assert gzip.decompress(stored.read_bytes()) == data
    assert r1["raw_sha256"] == hashlib.sha256(data).hexdigest()
    assert r1["rows_hint"] == 1
    assert len(list((lake.root / "receipts").rglob("*.json"))) == 1
    # Unchanged responses should never multiply immutable data objects.
    inv = archive_inventory(lake.root, verify_hash=True, check_mount=False)
    assert inv["receipts"] == 1 and inv["invalid"] == 0


def test_restated_vintage_kept_not_mutated(lake):
    path = a.request_path("fund-statements", "NVDA")
    a1 = lake.store_response("fund-statements", "NVDA", path, b'[{"netIncome":1}]')
    a2 = lake.store_response("fund-statements", "NVDA", path, b'[{"netIncome":2}]')
    assert a1["path"] != a2["path"]
    assert len(list((lake.root / "raw").rglob("*.raw.gz"))) == 2


def test_boats_quote_raw_fields_not_nbbo():
    row = {"service": "boats", "messageType": "A", "data": [
        "Q", "2026-10-09T01:01:00Z", 1791507660000000000, "NVDA",
        100, 192.1, 192.15, 192.2, 200
    ]}
    projection = a.decode_boats(row, "2026-10-09T01:01:01Z")
    assert projection["bid_raw"] == 192.1
    assert projection["ask_raw"] == 192.2
    assert projection["mid_vendor"] == 192.15
    assert projection["is_nbbo"] is False
    assert projection["is_canonical_price"] is False


def test_boats_trade_break_cond_preservation():
    for kind in ("T", "B"):
        row = {"service": "boats", "data": [
            kind, "2026-10-09T01:01:00Z", 1791507660000000000, "NVDA",
            192.18, 12, "@", "F", "T", "X"
        ]}
        output = a.decode_boats(row, "2026-10-09T01:02:00Z")
        assert output["sale_conditions"] == ["@", "F", "T", "X"]
        assert output["is_break"] == (kind == "B")
        assert output["last_raw"] == 192.18


def test_bad_boats_frame_rejected():
    with pytest.raises(a.TiingoArchiveError):
        a.decode_boats({"service": "boats", "data": ["T", "a"]}, "t")


def test_boats_batch_keeps_unparsed_as_raw(lake):
    quote = json.dumps({"service": "boats", "data": [
        "Q", "2026-10-09T00:00:00Z", 1, "SPY", 10, 100.0, 100.1, 100.2, 10
    ]})
    trade = json.dumps({"service": "boats", "data": [
        "B", "2026-10-09T00:00:01Z", 2, "SPY", 100.0, 100,
        "@", "F", "", ""
    ]})
    items = [("2026-10-09T00:00:01Z", quote),
             ("2026-10-09T00:00:02Z", trade),
             ("2026-10-09T00:00:03Z", '{"service":"boats","messageType":"I"}')]
    saved = lake.store_boats_batch(items)
    assert saved["messages"] == 3
    assert saved["counts"] == {"Q": 1, "T": 0, "B": 1, "other": 1}
    lines = gzip.decompress((lake.root / saved["path"]).read_bytes()).splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0])["raw_message"] == quote
    assert archive_inventory(lake.root, verify_hash=True, check_mount=False)["invalid"] == 0


def test_boats_subscribe_payload_never_contains_unexpected_scope():
    msg = json.loads(boats_subscribe_message("a" * 40))
    assert msg["eventName"] == "subscribe"
    assert msg["eventData"] == {"thresholdLevel": 3}


def test_date_chunking_inclusive_and_no_gap():
    assert list(date_ranges(date(2026, 10, 1), date(2026, 10, 9), 4)) == [
        (date(2026, 10, 1), date(2026, 10, 4)),
        (date(2026, 10, 5), date(2026, 10, 8)),
        (date(2026, 10, 9), date(2026, 10, 9)),
    ]


def test_fundamentals_plan_as_reported_default_and_latest_restated():
    default = plan(["fund-statements", "fund-meta"], ["NVDA"],
                   date(2019, 1, 1), date(2020, 1, 1))
    assert default[0].params["asReported"] == "true"
    assert default[1].symbol is None
    restated = plan(["fund-statements"], ["NVDA"], None, None,
                    as_reported=False)
    assert restated[0].params["asReported"] == "false"


def test_boats_history_requests_are_overnight_only():
    items = plan(["boats-bars"], ["NVDA"], date(2026, 10, 1), date(2026, 10, 9))
    assert len(items) == 2
    assert all(item.params["columns"].endswith("volume") for item in items)
    assert all(item.params["resampleFreq"] == "1min" for item in items)


def test_no_today_survivorship_claim_for_symbol_file(tmp_path):
    file = tmp_path / "symbols.txt"
    file.write_text("# date-specific symbol cohort\nNVDA\nNVDA\nAAPL\n")
    assert load_symbols("", str(file)) == ["NVDA", "AAPL"]


def test_catalog_and_plan_do_not_need_credentials(capsys, monkeypatch):
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    assert main(["catalog"]) == 0
    assert "eod-bars" in capsys.readouterr().out
    assert main(["plan", "--sources", "eod-bars", "--symbols", "NVDA",
                 "--start", "2026-10-01", "--end", "2026-10-05"]) == 0
    assert '"network": false' in capsys.readouterr().out


def test_client_does_not_embed_token_in_url(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        headers = {"Content-Type": "application/json"}

        def read(self, _):
            return b"[]"

    requests = []

    def stub(req, timeout):
        requests.append(req)
        return Response()

    monkeypatch.setattr(a.urllib.request, "urlopen", stub)
    raw, ctype = a.fetch_json_bytes("/tiingo/daily/NVDA/prices", "dummy-test-token-not-secret")
    assert raw == b"[]" and ctype == "application/json"
    assert "dummy-test-token-not-secret" not in requests[0].full_url
    assert requests[0].get_header("Authorization") == "Token dummy-test-token-not-secret"


def test_unauthorized_response_has_no_payload_in_exception(monkeypatch):
    from io import BytesIO

    def stub(req, timeout):
        raise a.urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, BytesIO(b"Sensitive-Key-Should-Be-Hidden"))

    monkeypatch.setattr(a.urllib.request, "urlopen", stub)
    with pytest.raises(a.TiingoArchiveError) as exc:
        a.fetch_json_bytes("/boats", "dummy-test-token-not-secret")
    assert "Sensitive-Key-Should-Be-Hidden" not in str(exc.value)
    assert "403" in str(exc.value)


def test_crypto_bulk_request_scoped_to_symbols():
    items = plan(["crypto-bars"], ["BTCUSD", "ETHUSD"],
                 date(2026, 10, 1), date(2026, 10, 9))
    assert len(items) == 2
    assert all(i.params["tickers"] == "BTCUSD,ETHUSD" for i in items)
    assert all(i.symbol is None for i in items)


def test_no_unbounded_crypto_price_download():
    with pytest.raises(ValueError, match="requires symbols"):
        plan(["crypto-bars"], [], date(2026, 10, 1), date(2026, 10, 9))


def test_security_search_requires_explicit_text():
    with pytest.raises(ValueError, match="search-query"):
        plan(["security-search"], [], None, None)
    tasks = plan(["security-search"], [], None, None, search_query="historic"
                 )
    assert "query=historic" in a.request_path(tasks[0].source, tasks[0].symbol,
                                              tasks[0].params)


def test_news_source_bounded_and_symbol_scoped():
    tasks = plan(["news"], ["AMD", "NVDA"], None, None)
    assert tasks[0].params == {"limit": 100, "tickers": "AMD,NVDA"}


def test_offline_mock_boats_stream_durable_segments_no_secret(lake, monkeypatch):
    import sys
    import types
    import scripts.tiingo_ingest as ing

    token = "dummy-testing-only-not-real"
    frames = [
        json.dumps({"service": "boats", "data": [
            "Q", "2026-10-09T01:00:00Z", 77, "NVDA",
            10, 100, 100.1, 100.2, 10]}),
        json.dumps({"service": "boats", "data": [
            "T", "2026-10-09T01:00:01Z", 78, "NVDA",
            100.1, 20, "@", "", "", ""]}),
    ]
    sent = []
    class FakeSocket:
        def __init__(self):
            self.frames = list(frames)
        def settimeout(self, secs):
            assert secs == 3
        def send(self, msg):
            sent.append(msg)
        def recv(self):
            return self.frames.pop(0)
        def close(self):
            pass
    fake = types.SimpleNamespace(
        create_connection=lambda *a, **kw: FakeSocket(),
        WebSocketException=RuntimeError,
        WebSocketTimeoutException=TimeoutError)
    monkeypatch.setitem(sys.modules, "websocket", fake)
    monkeypatch.setattr(ing, "read_key", lambda: token)
    outcome = ing.boats_stream(max_seconds=10, max_messages=2,
                               batch_messages=100, flush_seconds=2, archive=lake)
    assert outcome["raw_messages"] == 2
    assert outcome["segments"] == 1
    assert outcome["transport_breaks"] == 0
    assert outcome["coverage_proven"] is False
    assert json.loads(sent[0])["eventData"]["thresholdLevel"] == 3
    raw = next((lake.root / "raw" / "boats-firehose").rglob("*.ndjson.gz"))
    body = gzip.decompress(raw.read_bytes())
    assert token.encode() not in body
    assert body.count(b"\n") == 2


def test_mock_boats_auth_rejection_stops_before_archive(lake, monkeypatch):
    import sys
    import types
    import scripts.tiingo_ingest as ing

    class FakeSocket:
        def settimeout(self, secs):
            pass
        def send(self, msg):
            pass
        def recv(self):
            return json.dumps({"service": "error", "messageType": "E",
                               "privateDetails": "DO_NOT_LOG"})
        def close(self):
            pass
    fake = types.SimpleNamespace(
        create_connection=lambda *a, **kw: FakeSocket(),
        WebSocketException=RuntimeError,
        WebSocketTimeoutException=TimeoutError)
    monkeypatch.setitem(sys.modules, "websocket", fake)
    monkeypatch.setattr(ing, "read_key", lambda: "dummy-testing-only-not-real")
    with pytest.raises(a.TiingoArchiveError) as exc:
        ing.boats_stream(max_seconds=10, max_messages=100,
                         batch_messages=100, flush_seconds=2, archive=lake)
    assert "DO_NOT_LOG" not in str(exc.value)
    assert not (lake.root / "raw" / "boats-firehose").exists()


def test_news_publisher_filter_uses_singular_wire_parameter():
    assert a.request_path("news", None, {
        "source": "bloomberg.com,cnbc.com", "limit": 250,
        "onlyWithTickers": "true", "sortBy": "crawlDate",
        "startDate": "2026-10-21", "endDate": "2026-10-22",
    }) == (
        "/tiingo/news?endDate=2026-10-22&limit=250&onlyWithTickers=true"
        "&sortBy=crawlDate&source=bloomberg.com,cnbc.com&startDate=2026-10-21"
    )


@pytest.mark.parametrize("source,symbol", [
    ("eod-bars", "NVDA"), ("news-bulk-index", None), ("crypto-bars", None),
])
def test_news_publisher_filter_is_not_a_global_parameter(source, symbol):
    with pytest.raises(ValueError):
        a.request_path(source, symbol, {"source": "cnbc.com"})


@pytest.mark.parametrize("params", [
    {"sources": "cnbc.com"},
    {"source": "cnbc.com", "sources": "bloomberg.com"},
])
def test_news_publisher_filter_rejects_plural_before_collection(monkeypatch, params):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid new query reached network or archive storage")

    class NoStorage:
        store_response = staticmethod(forbidden)

    monkeypatch.setattr(a.urllib.request, "urlopen", forbidden)
    with pytest.raises(ValueError):
        a.collect_one(NoStorage(), "news", None, "synthetic-test-key", params)


def test_news_publisher_filter_collection_keeps_wire_and_receipt_equal(lake, monkeypatch):
    class Response:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, _):
            return b"[]"

    requests = []

    def stub(req, timeout):
        requests.append(req)
        return Response()

    monkeypatch.setattr(a.urllib.request, "urlopen", stub)
    monkeypatch.setattr(a, "utc_now", lambda: "2026-10-22T00:00:00+00:00")
    result = a.collect_one(lake, "news", None, "synthetic-test-key", {
        "source": "bloomberg.com,cnbc.com", "limit": 250,
    })
    expected = "/tiingo/news?limit=250&source=bloomberg.com,cnbc.com"
    assert requests[0].full_url == a.API_ORIGIN + expected
    assert requests[0].get_header("Authorization") == "Token synthetic-test-key"
    receipt_bytes = next((lake.root / "receipts").rglob("*.json")).read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt["request_path"] == expected
    assert receipt["receipt_id"] == result["receipt_id"]
    assert a.validate_receipt(receipt) == result["receipt_id"]
    assert b"synthetic-test-key" not in receipt_bytes
    assert b"synthetic-test-key" not in gzip.decompress((lake.root / result["path"]).read_bytes())


@pytest.fixture
def legacy_news_receipt(lake):
    # Frozen synthetic output from the pre-fix owner at a92ee6e9. Do not rebuild
    # this identity using the current constructor or silently rename its query.
    raw = b'[{"id":"synthetic-news","source":"cnbc.com"}]'
    receipt = {
        "schema": "mastermind.tiingo.raw_receipt.v1",
        "source": "news", "vendor": "tiingo", "symbol": None,
        "request_path": "/tiingo/news?limit=250&sources=cnbc.com",
        "observed_at_utc": "2026-10-22T00:00:00+00:00",
        "publication_time_status": "UNVERIFIED_HISTORICALLY",
        "rights_status": "PER_PRODUCT_REDISTRIBUTION_NOT_VERIFIED",
        "http_status": 200, "content_type": "application/json",
        "raw_path": "raw/news/2026-10-22/all/4b6379df264c6ec0-e2577d5783da4b276ad65ee6.raw.gz",
        "raw_sha256": "e2577d5783da4b276ad65ee6bedd39ce4a6be906dbf396e12bc5ca4649238417",
        "raw_bytes": 45, "compressed_bytes": 64, "record_count_hint": 1,
        "source_modified_at": None,
        "correction_policy": "APPEND_VINTAGE_NEVER_IN_PLACE",
        "price_basis_policy": "PRESERVE_VENDOR_RAW_AND_ADJUSTED_AS_DIFFERENT_FIELDS",
        "receipt_id": "ef027895644252301c09d4b428776475a63f494a344ce89378745d944e833b89",
    }
    raw_path = lake.root / receipt["raw_path"]
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(gzip.compress(raw, mtime=0))
    receipt_path = lake.root / "receipts/news/2026-10-22/4b6379df264c6ec0-e2577d5783da4b276ad65ee6.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    return receipt, raw, raw_path, receipt_path


def test_legacy_news_filter_receipt_remains_readable_without_rewriting(lake, legacy_news_receipt):
    from scripts.tiingo_materialize import verified_raw

    receipt, raw, raw_path, receipt_path = legacy_news_receipt
    before = raw_path.read_bytes(), receipt_path.read_bytes()
    assert a.validate_receipt(receipt) == "ef027895644252301c09d4b428776475a63f494a344ce89378745d944e833b89"
    assert verified_raw(lake.root, receipt) == raw
    assert (raw_path.read_bytes(), receipt_path.read_bytes()) == before


def test_legacy_news_filter_cannot_be_newly_stored(lake, legacy_news_receipt):
    receipt, raw, raw_path, receipt_path = legacy_news_receipt
    before = {p.relative_to(lake.root): p.read_bytes()
              for p in lake.root.rglob("*") if p.is_file()}
    with pytest.raises(a.TiingoArchiveError):
        lake.store_response("news", None, receipt["request_path"], raw,
                            received_at="2026-10-22T01:00:00+00:00")
    assert {p.relative_to(lake.root): p.read_bytes()
            for p in lake.root.rglob("*") if p.is_file()} == before


def test_legacy_news_filter_renaming_does_not_inherit_receipt_identity(legacy_news_receipt):
    receipt, _, _, _ = legacy_news_receipt
    renamed = {**receipt, "request_path": "/tiingo/news?limit=250&source=cnbc.com"}
    with pytest.raises(a.TiingoArchiveError, match="original receipt identity mismatch"):
        a.validate_receipt(renamed)


def test_legacy_news_filter_and_corrected_capture_keep_distinct_identities(lake, legacy_news_receipt):
    receipt, raw, raw_path, receipt_path = legacy_news_receipt
    before = raw_path.read_bytes(), receipt_path.read_bytes()
    path = a.request_path("news", None, {"limit": 250, "source": "cnbc.com"})
    result = lake.store_response("news", None, path, raw,
                                received_at=receipt["observed_at_utc"])
    assert result["receipt_id"] != receipt["receipt_id"]
    assert result["path"] != receipt["raw_path"]
    assert result["raw_sha256"] == receipt["raw_sha256"]
    assert (raw_path.read_bytes(), receipt_path.read_bytes()) == before


def test_legacy_news_filter_compatibility_preserves_old_non_news_paths():
    # Old construction allowed plural sources globally; historical readers must
    # retain those exact bytes without admitting that syntax for new requests.
    path = "/tiingo/daily/NVDA/prices?sources=cnbc.com"
    assert a.validate_request("eod-bars", "NVDA", path) is None
    with pytest.raises(ValueError):
        a.request_path("eod-bars", "NVDA", {"sources": "cnbc.com"})


@pytest.mark.parametrize("path", [
    "/tiingo/news?source=cnbc.com&sources=bloomberg.com",
    "/tiingo/news?source=cnbc.com&source=bloomberg.com",
    "/tiingo/news?sources=cnbc.com&sources=bloomberg.com",
    "/tiingo/news?source=cnbc.com&limit=250",
    "/tiingo/news?sources=cnbc.com&limit=250",
    "/tiingo/news?source=cnbc.com&token=synthetic-test-key",
    "/tiingo/news?source=cnbc.com&unknown=value",
    "/tiingo/news?source=cnbc.com#fragment",
    "https://api.tiingo.com/tiingo/news?source=cnbc.com",
    "/tiingo/daily/NVDA/prices?source=cnbc.com",
])
def test_news_publisher_filter_history_does_not_weaken_path_validation(path):
    with pytest.raises(a.TiingoArchiveError):
        a.validate_request("news", None, path)

def test_legacy_news_filter_plan_preserves_frozen_digest_offline(monkeypatch):
    import scripts.tiingo_ingest as ing

    def forbidden(*args, **kwargs):
        pytest.fail("offline historical plan attempted collection")

    monkeypatch.setattr(ing, "collect", forbidden)
    monkeypatch.setattr(ing, "read_key", forbidden)
    monkeypatch.setattr(a.urllib.request, "urlopen", forbidden)
    tasks = [ing.Task("news", None, {"limit": 250, "sources": "cnbc.com"})]
    # Frozen from plan_page at a92ee6e9, before the HTTP parameter correction.
    digest = "39ca53761298a38c9c32e71b9a1e488199cd2fe0dcc41df11c66d5e193e21c0d"
    page = ing.plan_page(tasks, expected_digest=digest)
    assert page["plan_sha256"] == digest
    assert page["items"] == [{
        "ordinal": 0, "source": "news", "symbol": None,
        "request_path": "/tiingo/news?limit=250&sources=cnbc.com",
    }]
    assert page["network"] is False
    assert page["execution_authorized"] is False


def test_legacy_news_filter_corpus_audit_matches_original_plan_without_writes(
        lake, legacy_news_receipt, monkeypatch):
    import scripts.tiingo_ingest as ing
    from scripts.tiingo_corpus_audit import audit_corpus

    def forbidden(*args, **kwargs):
        pytest.fail("read-only historical audit attempted collection or storage")

    monkeypatch.setattr(ing, "read_key", forbidden)
    monkeypatch.setattr(a.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(a.Archive, "store_response", forbidden)
    before = {p.relative_to(lake.root): p.read_bytes()
              for p in lake.root.rglob("*") if p.is_file()}
    result = audit_corpus(
        [ing.Task("news", None, {"limit": 250, "sources": "cnbc.com"})],
        root=lake.root, observed_before="2026-10-22T01:00:00+00:00",
        check_mount=False,
    )
    assert result["plan_sha256"] == "39ca53761298a38c9c32e71b9a1e488199cd2fe0dcc41df11c66d5e193e21c0d"
    assert result["request_status_counts"] == {"RAW_RECORDS_CAPTURED": 1}
    assert result["requests"][0]["request_path"] == "/tiingo/news?limit=250&sources=cnbc.com"
    assert result["scan"]["verified_raw_responses"] == 1
    assert result["network"] is False
    assert result["writes"] is False
    assert result["execution_authorized"] is False
    assert result["canonical_identity_admitted"] is False
    assert result["source_authenticity_proven"] is False
    assert {p.relative_to(lake.root): p.read_bytes()
            for p in lake.root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("read_at,closed_at,storage_at,capture_date", [
    ("2026-10-22T03:59:59.900000+00:00", "2026-10-22T04:00:00.100000+00:00",
     "2026-10-22T04:00:01+00:00", "2026-10-22"),
    ("2026-10-22T23:59:59.900000+00:00", "2026-10-23T00:00:00.100000+00:00",
     "2026-10-23T00:00:01+00:00", "2026-10-22"),
])
def test_response_observation_precedes_teardown_and_storage(
        lake, monkeypatch, read_at, closed_at, storage_at, capture_date):
    # Model real ordering: response bytes finish first, HTTP teardown and the
    # storage reserve check each finish later. Only the first clock belongs to
    # the response; the midnight case also checks the actual archive partition.
    clock = {"now": read_at}
    samples, reads = [], []
    raw = b'[{"date":"2026-10-22T00:00:00Z","open":1,"high":1,"low":1,"close":1}]'

    class Response:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def read(self, limit):
            reads.append(limit)
            clock["now"] = read_at
            return raw

        def __exit__(self, *args):
            clock["now"] = closed_at

    def now():
        samples.append(clock["now"])
        return clock["now"]

    def delayed_storage_check(root, *, floor):
        clock["now"] = storage_at

    monkeypatch.setattr(a.urllib.request, "urlopen", lambda req, timeout: Response())
    monkeypatch.setattr(a, "utc_now", now)
    monkeypatch.setattr(a, "require_space", delayed_storage_check)
    saved = a.collect_one(lake, "forex-bars", "EURUSD", "synthetic-test-key",
                          {"resampleFreq": "1min"})

    assert saved["observed_at_utc"] == read_at
    assert samples == [read_at]
    assert reads == [a.MAX_RESPONSE_BYTES + 1]
    assert clock["now"] == storage_at
    assert Path(saved["path"]).parts[2] == capture_date
    assert gzip.decompress((lake.root / saved["path"]).read_bytes()) == raw
    receipts = list((lake.root / "receipts").rglob("*.json"))
    assert len(receipts) == 1 and receipts[0].parent.name == capture_date
    receipt = json.loads(receipts[0].read_bytes())
    assert receipt["observed_at_utc"] == read_at
    assert a.validate_receipt(receipt) == saved["receipt_id"]


def test_response_observation_keeps_first_receipt_bytes_and_clock(lake, monkeypatch):
    raw = b'[{"date":"2026-10-22T00:00:00Z","close":1}]'
    params = {"resampleFreq": "1min"}
    path = a.request_path("forex-bars", "EURUSD", params)
    first = lake.store_response("forex-bars", "EURUSD", path, raw,
                                received_at="2026-10-22T03:30:00+00:00")
    before = {p.relative_to(lake.root): p.read_bytes()
              for p in lake.root.rglob("*") if p.is_file()}

    class Response:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def read(self, _):
            return raw

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(a.urllib.request, "urlopen", lambda req, timeout: Response())
    monkeypatch.setattr(a, "utc_now", lambda: "2026-10-22T06:00:00+00:00")
    repeated = a.collect_one(lake, "forex-bars", "EURUSD", "synthetic-test-key", params)

    assert repeated["new_raw"] is False
    assert repeated["observed_at_utc"] == first["observed_at_utc"]
    assert repeated["receipt_id"] == first["receipt_id"]
    assert repeated["path"] == first["path"]
    assert {p.relative_to(lake.root): p.read_bytes()
            for p in lake.root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("raw,oversize", [(b"[]", False), (b"[ ]", True)])
def test_response_observation_preserves_public_pair_and_read_limit(monkeypatch, raw, oversize):
    reads, requests = [], []

    class Response:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def read(self, limit):
            reads.append(limit)
            return raw

        def __exit__(self, *args):
            return None

    def open_response(req, timeout):
        requests.append((req, timeout))
        return Response()

    monkeypatch.setattr(a.urllib.request, "urlopen", open_response)
    monkeypatch.setattr(a, "utc_now", lambda: "2026-10-22T03:59:59.900000+00:00")
    if oversize:
        with pytest.raises(a.TiingoArchiveError, match="response exceeded bounded archive size"):
            a.fetch_json_bytes("/boats", "synthetic-test-key", timeout=7, max_bytes=2)
    else:
        result = a.fetch_json_bytes("/boats", "synthetic-test-key", timeout=7, max_bytes=2)
        assert type(result) is tuple
        assert result == (b"[]", "application/json")
    assert reads == [3]
    assert len(requests) == 1 and requests[0][1] == 7
    assert requests[0][0].get_header("Authorization") == "Token synthetic-test-key"
    assert "synthetic-test-key" not in requests[0][0].full_url


def test_response_observation_teardown_failure_does_not_store(lake, monkeypatch):
    class Response:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def read(self, _):
            return b"[]"

        def __exit__(self, *args):
            raise a.urllib.error.URLError("sensitive transport detail")

    monkeypatch.setattr(a.urllib.request, "urlopen", lambda req, timeout: Response())
    monkeypatch.setattr(a, "utc_now", lambda: "2026-10-22T03:59:59.900000+00:00")
    with pytest.raises(a.TiingoArchiveError) as exc:
        a.collect_one(lake, "forex-bars", "EURUSD", "synthetic-test-key",
                      {"resampleFreq": "1min"})
    assert str(exc.value) == "Tiingo transport unavailable"
    assert not [p for p in lake.root.rglob("*") if p.is_file()]
