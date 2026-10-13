"""End-to-end OFFLINE BOATS source-connection fixture -> existing L0/L1 -> reader.

No vendor request or real token. This suite tests the existing stream/archiver
rather than creating a replacement collector or lifting platform refusals.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
import sys
import types
from pathlib import Path

import pytest

import collectors.tiingo_archive as a
import scripts.tiingo_ingest as ing
from lib.dataos.tiingo_reader import TiingoViewRefusal, read_research_view
from lib.dataos.tiingo_boats_tape import audit_boats_tape
from scripts.tiingo_materialize import materialize_one
from lib.dataos.registry import load_registry

START = "2026-10-09T01:00:00Z"
END = "2026-10-09T01:05:00Z"
CUT = "2026-10-09T03:00:00Z"
FAKE_KEY = "dummy-test-key-never-issued"
EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def frame(kind: str, when: str, *, ticker: str = "AMD", size=25) -> str:
    stamp = datetime.fromisoformat(when.replace("Z", "+00:00"))
    delta = stamp - EPOCH_UTC
    epoch_ns = ((delta.days * 86400 + delta.seconds) * 1_000_000
                + delta.microseconds) * 1000
    if kind == "Q":
        data = ["Q", when, epoch_ns, ticker, 100, 99.9, 100.0, 100.1, 120]
    elif kind in {"T", "B"}:
        data = [kind, when, epoch_ns, ticker, 100.02, size, "@", "F", "", "X"]
    else:
        return json.dumps({"service": "boats", "messageType": "I", "data": []})
    return json.dumps({"service": "boats", "data": data}, separators=(",", ":"))


def fake_connection(monkeypatch, frames_per_connection, arrivals):
    """Simulate only a WebSocket socket: zero endpoint/network/auth code."""
    sockets = []
    sent = []
    for frames in frames_per_connection:
        class Socket:
            def __init__(self, incoming):
                self.incoming = iter(incoming)
                self.closed = False

            def settimeout(self, seconds):
                assert seconds == 3

            def send(self, payload):
                sent.append(payload)

            def recv(self):
                try:
                    return next(self.incoming)
                except StopIteration:
                    raise RuntimeError("mock transport interruption") from None

            def close(self):
                self.closed = True

        sockets.append(Socket(frames))
    queue = iter(sockets)

    def establish(*args, **kwargs):
        assert args == (ing.BOATS_WS,)
        assert kwargs["timeout"] == 8
        return next(queue)

    stub = types.SimpleNamespace(
        create_connection=establish, WebSocketException=RuntimeError,
        WebSocketTimeoutException=TimeoutError,
    )
    monkeypatch.setitem(sys.modules, "websocket", stub)
    monkeypatch.setattr(ing, "read_key", lambda: FAKE_KEY)
    arrivals = iter(arrivals)
    monkeypatch.setattr(ing, "utc_now", lambda: next(arrivals))
    monkeypatch.setattr(ing.time, "sleep", lambda _: None)
    return sent


def refs(lake):
    items = []
    for path in sorted((lake.root / "receipts" / "boats-firehose").rglob("*.json")):
        receipt = json.loads(path.read_text())
        items.append((receipt["first_received_at_utc"][:10],
                      receipt["raw_sha256"], receipt))
    return items


def test_stream_to_immutable_raw_to_parquet_to_evidence_bound_tape(lake, monkeypatch):
    quotes = frame("Q", "2026-10-09T01:00:01Z")
    trade = frame("T", "2026-10-09T01:00:01.200Z")
    broken = frame("B", "2026-10-09T01:00:01.300Z", size=10)
    unknown = frame("I", "2026-10-09T01:00:01.500Z")
    sent = fake_connection(
        monkeypatch, [[quotes, trade, broken, unknown]],
        ["2026-10-09T01:00:01.100Z", "2026-10-09T01:00:01.400Z",
         "2026-10-09T01:00:01.500Z", "2026-10-09T01:00:01.600Z"],
    )
    output = ing.boats_stream(max_seconds=10, max_messages=4,
                              batch_messages=100, flush_seconds=2, archive=lake)
    assert output["raw_messages"] == 4
    assert output["connections"] == 1 and output["segments"] == 1
    assert output["transport_breaks"] == 0
    assert output["coverage_proven"] is False
    assert sent and all(FAKE_KEY in payload for payload in sent)
    ref = refs(lake)
    assert len(ref) == 1
    day, digest, receipt = ref[0]
    assert receipt["counts"] == {"Q": 1, "T": 1, "B": 1, "other": 1}
    assert receipt["transport_continuity"] == "NOT_PROVEN"
    assert receipt["nbbo"] is False
    assert receipt["rights_status"] == "BOATS_REDISTRIBUTION_NOT_VERIFIED"
    raw = gzip.decompress((lake.root / receipt["raw_path"]).read_bytes())
    assert FAKE_KEY.encode() not in raw
    assert hashlib.sha256(raw).hexdigest() == digest
    assert raw.count(b"\n") == 4
    materialized = materialize_one(lake.root, receipt, free_floor=0)
    assert materialized["status"] == "WRITTEN" and materialized["rows"] == 3
    view = read_research_view("boats-firehose", day, digest,
                              root=lake.root, check_mount=False)
    assert len(view.rows) == 3
    assert [r["kind"] for r in view.rows] == ["Q", "T", "B"]
    assert view.redistribution_admitted is False
    assert view.pit_backtest_eligible is False
    tape = audit_boats_tape([(day, digest)], root=lake.root,
                            vendor_symbol="AMD", start_event_at_utc=START,
                            end_event_at_utc=END, observed_before_utc=CUT,
                            check_mount=False)
    assert tape["source_messages_all_tickers"] == 4
    assert tape["observed_unfiltered_T_message_shares"] == 25
    assert tape["observed_B_trade_break_message_shares_NOT_NETTED"] == 10
    assert tape["trade_quote_age_diagnostics"]["fresh_prior_venue_quote"] == 1
    assert tape["point_in_time_backtest_eligible"] is False
    assert tape["redistribution_admitted"] is False
    assert tape["transport_continuity_proven"] is False


def test_transport_disconnect_flushes_source_and_does_not_bridge_quote(lake, monkeypatch):
    quote = frame("Q", "2026-10-09T01:00:01Z")
    trade = frame("T", "2026-10-09T01:00:01.200Z")
    fake_connection(
        monkeypatch, [[quote], [trade]],
        ["2026-10-09T01:00:01.100Z", "2026-10-09T01:00:01.400Z"],
    )
    out = ing.boats_stream(max_seconds=10, max_messages=2,
                           batch_messages=100, flush_seconds=2, archive=lake)
    assert out["connections"] == 2
    assert out["transport_breaks"] == 1
    assert out["segments"] == 2
    assert out["coverage_proven"] is False
    captured = refs(lake)
    assert len(captured) == 2
    for day, digest, receipt in captured:
        assert materialize_one(lake.root, receipt, free_floor=0)["status"] == "WRITTEN"
    tape = audit_boats_tape([(day, digest) for day, digest, _ in captured],
                            root=lake.root, vendor_symbol="AMD",
                            start_event_at_utc=START, end_event_at_utc=END,
                            observed_before_utc=CUT, check_mount=False)
    assert tape["selected_kind_counts"] == {"Q": 1, "T": 1, "B": 0}
    assert tape["trade_quote_age_diagnostics"]["fresh_prior_venue_quote"] == 0
    assert tape["trade_quote_age_diagnostics"]["no_prior_quote"] == 1
    assert tape["transport_continuity_proven"] is False


def test_vendor_rejection_after_received_frame_keeps_partial_raw_without_claims(lake, monkeypatch):
    accepted = frame("Q", "2026-10-09T01:00:01Z")
    rejected = json.dumps({
        "service": "error", "messageType": "E",
        "privateDetails": "DO_NOT_LOG_MOCK_VENDOR_BODY",
    })
    fake_connection(monkeypatch, [[accepted, rejected]],
                    ["2026-10-09T01:00:01.100Z"])
    with pytest.raises(a.TiingoArchiveError, match="subscription rejected") as err:
        ing.boats_stream(max_seconds=10, max_messages=10,
                         batch_messages=100, flush_seconds=2, archive=lake)
    assert "DO_NOT_LOG_MOCK_VENDOR_BODY" not in str(err.value)
    captured = refs(lake)
    assert len(captured) == 1
    receipt = captured[0][2]
    assert receipt["counts"] == {"Q": 1, "T": 0, "B": 0, "other": 0}
    assert receipt["coverage"] == "SOURCE_MESSAGES_RECEIVED_ONLY"
    assert receipt["transport_continuity"] == "NOT_PROVEN"


def test_chairman_attestation_is_distinct_from_proven_live_boats_registry():
    from pathlib import Path
    import yaml

    path = Path(__file__).resolve().parent.parent / "config/dataset_registry.yml"
    registry = yaml.safe_load(path.read_text())
    assert isinstance(registry, dict)
    entries = registry.get("datasets")
    assert isinstance(entries, list)
    raw = next(x for x in entries if x.get("dataset_id") == "vendor.tiingo.raw.boats")
    view = next(x for x in entries if x.get("dataset_id") == "vendor.tiingo.research.boats")
    assert raw["licensing"] == (
        "chairman_attested_boats_realtime_purchased_licensed_full_redistribution_runtime_unproven"
    )
    assert raw["status"] == view["status"] == "PROPOSED"
    assert "not_canonical" in view["licensing"]
    assert raw["producer"] == "collectors/tiingo_archive.py::Archive.store_boats_batch"


def test_display_callback_sees_only_persisted_raw(lake, monkeypatch):
    raw = frame("T", "2026-10-09T01:00:01Z")
    fake_connection(monkeypatch, [[raw]], ["2026-10-09T01:00:01.100Z"])
    seen = []
    def observer(kind, payload):
        if kind == "archived":
            assert (lake.root / payload["receipt"]["path"]).is_file()
            assert len(refs(lake)) == 1
            assert payload["frames"] == (("2026-10-09T01:00:01.100Z", raw),)
            assert payload["active"] is False
        seen.append(kind)
    ing.boats_stream(max_seconds=10, max_messages=1, batch_messages=100,
                     flush_seconds=2, archive=lake, observer=observer)
    assert seen == ["connected", "disconnected", "archived", "ended"]

def test_archive_failure_cannot_emit_a_display_batch(lake, monkeypatch):
    raw = frame("T", "2026-10-09T01:00:01Z")
    fake_connection(monkeypatch, [[raw]], ["2026-10-09T01:00:01.100Z"])
    def failed_store(_):
        raise a.TiingoArchiveError("offline simulated disk failure")
    monkeypatch.setattr(lake, "store_boats_batch", failed_store)
    seen = []
    with pytest.raises(a.TiingoArchiveError, match="disk failure"):
        ing.boats_stream(max_seconds=10, max_messages=1, batch_messages=100,
                         flush_seconds=2, archive=lake, observer=lambda k,p:seen.append(k))
    assert "archived" not in seen
    assert seen[-1] == "ended"
