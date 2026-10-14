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
