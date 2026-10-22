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
import math
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


def fake_connection(monkeypatch, frames_per_connection, arrivals, *, retain_sockets=None):
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
    if retain_sockets is not None:
        retain_sockets.extend(sockets)
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


def test_publication_denial_still_archives_and_closes_real_stream(lake, monkeypatch, caplog):
    import scripts.build_ext_quotes as builder

    sockets, writes = [], []
    raw = frame("T", "2026-10-09T01:00:01Z")
    fake_connection(monkeypatch, [[raw]], ["2026-10-09T01:00:01.100Z"],
                    retain_sockets=sockets)

    class Denial(Exception):
        response = {"Error": {"Code": "AccessDenied"}}

    class Storage:
        def put_object(self, **kwargs):
            writes.append(kwargs)
            raise Denial("SECRET_PROVIDER_BODY")

    monkeypatch.setattr(builder, "_r2_client", lambda: Storage())
    result = builder.publish_boats_stream(max_seconds=10, max_messages=1,
                                           publish=True, archive=lake)
    assert len(writes) == 1
    assert sockets and all(socket.closed for socket in sockets)
    assert result["raw_messages"] == 1 and result["segments"] == 1
    receipt = refs(lake)[0][2]
    stored = gzip.decompress((lake.root / receipt["raw_path"]).read_bytes())
    assert json.loads(stored.decode())["raw_message"] == raw
    assert result["publication_ok"] is False
    assert result["publication"]["access_denied"] is True
    assert result["publication"]["final_invalidation_delivered"] is False
    assert "publication stopped for this invocation" in caplog.text
    assert "SECRET_PROVIDER_BODY" not in caplog.text


# Bounded stream-failure diagnostics (Fabric implementation, integrated into
# the existing explicitly selected Tiingo CI suite).
DIAG_FAKE_KEY = "OFFLINE_DUMMY_KEY_NEVER_ISSUED"
DIAG_SENTINEL = "SENTINEL_SECRET_PAYLOAD_DO_NOT_LOG_7c1f"
DIAG_ALLOWED_FIELDS = {"stage", "category", "attempt", "elapsed"}
DIAG_FRAME = ('{"service":"boats","data":["T","2026-10-09T01:00:01Z",0,'
         '"AMD",100.02,25,"@","F","","X"]}')
DIAG_RECEIVED_AT = datetime(2026, 10, 9, 1, 0, 1, 100000, tzinfo=timezone.utc)


class DiagClock:
    """Deterministic monotonic clock; the real time module is never used."""

    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += seconds


class DiagArchive:
    """In-memory stand-in; no filesystem, no receipts, no real storage."""

    def __init__(self, fail=False):
        self.batches = []
        self.fail = fail

    def store_boats_batch(self, frames):
        if self.fail:
            raise OSError(DIAG_SENTINEL)
        kept = list(frames)
        self.batches.append(kept)
        return {"new_raw": bool(kept),
                "raw_bytes": sum(len(raw.encode("utf-8")) for _, raw in kept)}


class DiagSocket:
    """Fake websocket socket: scripted outcomes only, zero endpoint code."""

    def __init__(self, script, clock, *, fail_settimeout=None, fail_send=None):
        self.script = list(script)
        self.clock = clock
        self.fail_settimeout = fail_settimeout
        self.fail_send = fail_send
        self.timeouts = []
        self.sent = []
        self.closed = 0

    def settimeout(self, seconds):
        if self.fail_settimeout is not None:
            raise self.fail_settimeout
        self.timeouts.append(seconds)

    def send(self, payload):
        if self.fail_send is not None:
            raise self.fail_send
        self.sent.append(payload)

    def recv(self):
        # A leading TICK repeats: idle receive timeouts never exhaust the
        # script, so they can only ever be ordinary bounded-stream control
        # flow, never a scripted transport break.
        if self.script and self.script[0] is DIAG_TICK:
            self.clock.t += 3
            raise TimeoutError(DIAG_SENTINEL)
        action = self.script.pop(0) if self.script else None
        if action is None:
            raise RuntimeError(DIAG_SENTINEL)
        return action

    def close(self):
        self.closed += 1


DIAG_TICK = object()


class DiagHarness:
    """Installs faked websocket/read_key/time/utc_now for one bounded run."""

    def __init__(self, monkeypatch, scripts, *, connect_error=None,
                 fail_settimeout=None, fail_send=None, observer_error=None,
                 archive=None, max_seconds=30, websocket_types=None,
                 observer_error_kind="connected"):
        self.clock = DiagClock()
        self.sockets = []
        self.events = []
        self.archived_payloads = []
        self.archive = archive if archive is not None else DiagArchive()
        self.max_seconds = max_seconds
        scripts = list(scripts)
        built = self.sockets

        def establish(*args, **kwargs):
            if connect_error is not None:
                raise connect_error
            assert args == (ing.BOATS_WS,)
            assert kwargs["timeout"] == 8
            socket = DiagSocket(scripts.pop(0), self.clock,
                                    fail_settimeout=fail_settimeout,
                                    fail_send=fail_send)
            built.append(socket)
            return socket

        def observer(kind, payload=None):
            self.events.append(kind)
            if kind == "archived":
                self.archived_payloads.append(payload)
            if observer_error is not None and kind == observer_error_kind:
                raise observer_error

        stub = types.SimpleNamespace(create_connection=establish,
                                     WebSocketException=(websocket_types.WebSocketException if websocket_types else RuntimeError),
                                     WebSocketTimeoutException=(websocket_types.WebSocketTimeoutException if websocket_types else TimeoutError))
        monkeypatch.setitem(sys.modules, "websocket", stub)
        monkeypatch.setattr(ing, "read_key", lambda: DIAG_FAKE_KEY)
        monkeypatch.setattr(ing, "time", self.clock)
        monkeypatch.setattr(ing, "utc_now", lambda: DIAG_RECEIVED_AT)
        self.observer = observer

    def run(self, **overrides):
        kwargs = dict(max_seconds=self.max_seconds, max_messages=2000000,
                      batch_messages=1000, flush_seconds=10,
                      archive=self.archive, observer=self.observer)
        kwargs.update(overrides)
        return ing.boats_stream(**kwargs)


def assert_diag_record_wellformed(record, max_seconds):
    """Contract shape: only the four allowed fields, all bounded and finite."""
    assert set(record) == DIAG_ALLOWED_FIELDS
    assert record["stage"] in ing.STREAM_FAILURE_STAGES
    assert record["category"] in ing.STREAM_FAILURE_CATEGORIES
    assert type(record["attempt"]) is int
    assert 1 <= record["attempt"] <= 5
    assert type(record["elapsed"]) is float
    assert math.isfinite(record["elapsed"])
    assert 0.0 <= record["elapsed"] <= float(max_seconds)


def test_each_failure_site_is_recorded_with_its_own_distinct_stage(monkeypatch):
    expected = {
        "connect": ("connect", "transport"),
        "configure": ("configure", "transport"),
        "subscribe": ("subscribe", "transport"),
        "receive": ("receive", "transport"),
        "observer": ("observer", "callback"),
    }
    seen_stages = []
    for site, (stage, category) in expected.items():
        harness = DiagHarness(
            monkeypatch, [[]] * 5,
            connect_error=OSError(DIAG_SENTINEL) if site == "connect" else None,
            fail_settimeout=OSError(DIAG_SENTINEL) if site == "configure" else None,
            fail_send=OSError(DIAG_SENTINEL) if site == "subscribe" else None,
            observer_error=OSError(DIAG_SENTINEL) if site == "observer" else None,
        )
        result = harness.run(max_messages=1)
        failures = result["failures"]
        # Five exhausted attempts -> exactly five retained records, one per
        # attempt identity, capped and never exceeding five.
        assert result["transport_breaks"] == 5
        assert len(failures) == 5
        assert [record["attempt"] for record in failures] == [1, 2, 3, 4, 5]
        for record in failures:
            assert_diag_record_wellformed(record, harness.max_seconds)
            assert (record["stage"], record["category"]) == (stage, category)
        # Elapsed is a finite bounded monotonic duration, nondecreasing.
        elapsed = [record["elapsed"] for record in failures]
        assert elapsed == sorted(elapsed)
        assert elapsed[0] == 0.0
        seen_stages.append(stage)
        # Cleanup: every created socket closed exactly once; the 3s same-socket
        # timeout was applied wherever the attempt got past connect.
        for socket in harness.sockets:
            assert socket.closed == 1
            assert socket.timeouts == ([] if site == "configure" else [3])
        assert harness.clock.sleeps == [2, 4, 8, 12]
        serialized = json.dumps(result, allow_nan=False, sort_keys=True)
        assert DIAG_SENTINEL not in serialized
        assert DIAG_FAKE_KEY not in serialized
    # The five injected sites are pairwise distinct from each other and none
    # is reported as the observer callback or the archive storage boundary.
    assert len(set(seen_stages)) == 5
    assert "observer" in seen_stages and "storage" not in seen_stages


def test_connect_timeout_reports_timeout_category_not_transport(monkeypatch):
    connect = {"transport": OSError(DIAG_SENTINEL), "timeout": TimeoutError(DIAG_SENTINEL)}
    categories = {}
    for kind, error in connect.items():
        harness = DiagHarness(monkeypatch, [[]], connect_error=error)
        result = harness.run(max_messages=1)
        assert result["connections"] == 0
        assert len(result["failures"]) == 5
        categories[kind] = {record["category"] for record in result["failures"]}
        assert {record["stage"] for record in result["failures"]} == {"connect"}
    assert categories["transport"] == {"transport"}
    assert categories["timeout"] == {"timeout"}
    assert categories["timeout"] != categories["transport"]


def test_receive_timeout_is_control_flow_not_a_recorded_failure(monkeypatch):
    harness = DiagHarness(monkeypatch, [[DIAG_TICK]], max_seconds=9)
    result = harness.run(max_messages=5)
    # Same socket reused for the whole bounded run; 3s same-socket timeout.
    assert len(harness.sockets) == 1
    socket = harness.sockets[0]
    assert socket.timeouts == [3] and socket.closed == 1
    assert result["connections"] == 1 and result["transport_breaks"] == 0
    # Idle receive timeouts are ordinary bounded-stream control flow: no
    # failure record, no transport break, no backoff sleep, no reconnect.
    assert result["failures"] == []
    assert harness.clock.sleeps == [] and harness.clock.t == 9
    assert harness.events == ["connected", "tick", "tick", "tick",
                              "disconnected", "ended"]


def test_returned_counts_serialize_with_only_finite_allowed_fields(monkeypatch):
    harness = DiagHarness(monkeypatch, [[], [DIAG_FRAME]])
    result = harness.run(max_messages=1)
    # Attempt 1 breaks at receive; attempt 2 delivers one frame and the
    # bounded run ends and archives it after display eligibility closes.
    assert result["transport_breaks"] == 1 and result["connections"] == 2
    assert result["raw_messages"] == 1 and result["segments"] == 1
    assert result["bytes"] == len(DIAG_FRAME.encode("utf-8"))
    # Additive only: every original counts field survives unchanged.
    assert set(result) == {"connections", "transport_breaks", "raw_messages",
                           "segments", "bytes", "coverage_proven", "failures"}
    assert result["coverage_proven"] is False
    assert len(result["failures"]) == 1
    record = result["failures"][0]
    assert (record["stage"], record["category"], record["attempt"]) == (
        "receive", "transport", 1)
    assert_diag_record_wellformed(record, harness.max_seconds)
    # Only finite JSON: allow_nan=False proves no NaN/Infinity slipped in.
    serialized = json.dumps(result, allow_nan=False, sort_keys=True)
    assert DIAG_SENTINEL not in serialized and DIAG_FAKE_KEY not in serialized
    # Display payload stays raw-content-only and free of failure metadata,
    # and archival still happens only after display eligibility closes.
    assert harness.events == ["connected", "gap", "disconnected", "connected",
                              "disconnected", "archived", "ended"]
    assert len(harness.archived_payloads) == 1
    frames = harness.archived_payloads[0]["frames"]
    assert frames == ((DIAG_RECEIVED_AT, DIAG_FRAME),)
    assert "failures" not in harness.archived_payloads[0]
    assert DIAG_SENTINEL not in json.dumps(harness.archived_payloads, default=str)


@pytest.mark.parametrize("scenario", ["vendor_rejection", "auth_material",
                                      "storage_failure"])
def test_terminal_paths_propagate_and_return_no_diagnostics(monkeypatch,
                                                            scenario):
    if scenario == "vendor_rejection":
        script = [json.dumps({"messageType": "E",
                              "response": {"private": DIAG_SENTINEL}})]
        harness = DiagHarness(monkeypatch, [script])
        match = "subscription rejected"
    elif scenario == "auth_material":
        script = [json.dumps({"note": DIAG_FAKE_KEY})]
        harness = DiagHarness(monkeypatch, [script])
        match = "sensitive authentication material"
    else:
        harness = DiagHarness(monkeypatch, [[DIAG_FRAME]], archive=DiagArchive(fail=True))
        match = "storage failed"
    returned = None
    message_budget = 10 if scenario != "storage_failure" else 1
    with pytest.raises(ing.TiingoArchiveError, match=match) as excinfo:
        returned = harness.run(max_messages=message_budget)
    # Disclosure: terminal exceptions propagate unconverted, so this run has
    # NO returned counts and therefore no failure-record list at all — the
    # diagnostics contract only exists on runs that return normally.
    assert returned is None
    # Still no sentinel/credential/vendor-body leakage on the raised path.
    assert DIAG_SENTINEL not in str(excinfo.value)
    assert DIAG_FAKE_KEY not in str(excinfo.value)
    assert "archived" not in harness.events and harness.archive.batches == []
    assert harness.events[-1] == "ended"
    for socket in harness.sockets:
        assert socket.closed == 1
    # Terminal auth/storage failures are never laundered into retriable
    # transport records: nothing was classified as a callback/storage record.
    assert harness.events.count("error") + harness.events.count("gap") <= 1


@pytest.mark.parametrize("kind", ["closed", "connect_timeout"])
def test_diagnostics_real_websocket_exception_taxonomy(monkeypatch, kind):
    # Use installed websocket-client exception classes with a fake connection;
    # the Fabric executor could only check alias classes in its environment.
    import websocket as websocket_types

    if kind == "connect_timeout":
        error = websocket_types.WebSocketTimeoutException(DIAG_SENTINEL)
        expected = ("connect", "timeout")
        harness = DiagHarness(monkeypatch, [[]], connect_error=error,
                              websocket_types=websocket_types)
    else:
        harness = DiagHarness(monkeypatch, [[]] * 5,
                              websocket_types=websocket_types)

        def closed(_socket):
            raise websocket_types.WebSocketConnectionClosedException(DIAG_SENTINEL)

        monkeypatch.setattr(DiagSocket, "recv", closed)
        expected = ("receive", "transport")
    result = harness.run(max_messages=1)
    assert len(result["failures"]) == 5
    assert {(r["stage"], r["category"]) for r in result["failures"]} == {expected}
    assert harness.clock.sleeps == [2, 4, 8, 12]
    assert all(socket.closed == 1 for socket in harness.sockets)
    assert DIAG_SENTINEL not in json.dumps(result, allow_nan=False)


def test_diagnostics_archived_callback_is_not_a_receive_or_storage_failure(monkeypatch):
    # Fail the observer only after an immutable archive return while eligibility
    # is open, rather than at connected: this exercises the nested flush edge.
    harness = DiagHarness(monkeypatch, [[DIAG_FRAME] * 100] + [[]] * 4,
                          observer_error=OSError(DIAG_SENTINEL),
                          observer_error_kind="archived")
    result = harness.run(batch_messages=100)
    assert result["failures"][0]["stage"] == "observer"
    assert result["failures"][0]["category"] == "callback"
    assert [r["stage"] for r in result["failures"][1:]] == ["receive"] * 4
    assert result["raw_messages"] == 100 and result["segments"] == 1
    assert len(harness.archive.batches) == 1
    assert result["transport_breaks"] == 5  # preserve legacy counter semantics
    assert all(socket.closed == 1 for socket in harness.sockets)
    assert harness.events[-1] == "ended"
    assert DIAG_SENTINEL not in json.dumps(result, allow_nan=False)


def test_diagnostics_successful_callback_does_not_own_a_later_failure(monkeypatch):
    harness = DiagHarness(monkeypatch, [[]] * 5)
    original_observer = harness.observer
    original_clock = harness.clock.monotonic
    fail_next_read = False

    def observer(kind, payload=None):
        nonlocal fail_next_read
        original_observer(kind, payload)
        if kind == "connected":
            fail_next_read = True

    def monotonic():
        nonlocal fail_next_read
        if fail_next_read:
            fail_next_read = False
            raise OSError(DIAG_SENTINEL)
        return original_clock()

    # A successful callback must not retain ownership of an exception raised
    # after it returned. The stage remains the last reached operation boundary;
    # the record is not a claim about the remote server or its close cause.
    monkeypatch.setattr(harness.clock, "monotonic", monotonic)
    result = harness.run(observer=observer)
    assert len(result["failures"]) == 5
    assert all(record["stage"] != "observer" for record in result["failures"])
    assert all(record["category"] != "callback" for record in result["failures"])
    assert all(socket.closed == 1 for socket in harness.sockets)
    assert DIAG_SENTINEL not in json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("bad_duration", [float("nan"), float("inf"), -float("inf"), -1.0])
def test_diagnostics_invalid_duration_cannot_escape_finite_json(monkeypatch, bad_duration):
    harness = DiagHarness(monkeypatch, [[]])
    original_clock = harness.clock.monotonic
    next_duration = None

    def monotonic():
        nonlocal next_duration
        if next_duration is not None:
            value, next_duration = next_duration, None
            return value
        return original_clock()

    def fail_connect(*_args, **_kwargs):
        nonlocal next_duration
        next_duration = bad_duration
        raise OSError(DIAG_SENTINEL)

    monkeypatch.setattr(harness.clock, "monotonic", monotonic)
    monkeypatch.setattr(sys.modules["websocket"], "create_connection", fail_connect)
    result = harness.run()
    assert len(result["failures"]) == 5
    for record in result["failures"]:
        assert_diag_record_wellformed(record, harness.max_seconds)
        assert record["elapsed"] == 0.0
    assert DIAG_SENTINEL not in json.dumps(result, allow_nan=False)
