"""Offline regressions for two verified BOATS delivery defects.

F3: the BOATS coverage file must load up to the publisher's public ceiling
    while every ordinary collector keeps the 12000-symbol default.
F9: a failed publication PUT must consume its rate-limit slot, and an archive
    storage OSError must stop the stream instead of masquerading as a
    websocket transport break.

No network, provider, R2, credentials or live stream: every stream and socket
entrypoint is stubbed before it can open a connection.
"""
from __future__ import annotations

from datetime import datetime, timezone
import sys
import types

import pytest

import collectors.tiingo_archive as archive_module
import scripts.tiingo_ingest as ing
from scripts import build_ext_quotes as publisher

CLI_NOW = datetime(2026, 10, 19, 1, tzinfo=timezone.utc)
CAPTURE_ID = "12345678-1234-1234-1234-123456789abc"


# ── F3: bounded loader limit ─────────────────────────────────────────────────

def coverage_names(count, first=None):
    """Unique, uppercase, path-safe vendor identifiers."""
    names = [f"Z{index:05d}" for index in range(count)]
    if first is not None:
        names[0] = first
    return names


def write_coverage(directory, names):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "coverage.txt"
    path.write_text("\n".join(names) + "\n", encoding="utf-8")
    return str(path)


def stub_cli_stream(monkeypatch, calls, *, forbidden=False):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return CLI_NOW

    def stream(**kw):
        if forbidden:
            pytest.fail("invalid coverage reached the BOATS publisher")
        calls.append(kw)
        return {"publication_ok": True}

    monkeypatch.setattr(publisher, "datetime", Clock)
    monkeypatch.setattr(publisher, "publish_boats_stream", stream)


def run_boats_cli(monkeypatch, coverage_path):
    monkeypatch.setattr("sys.argv",
                        ["build_ext_quotes", "--boats", "--symbols-file", coverage_path])
    publisher.main()


def test_full_observed_universe_reaches_boats_cli_in_order(monkeypatch, tmp_path):
    calls = []
    stub_cli_stream(monkeypatch, calls)
    names = coverage_names(15_380, first="AMD")
    run_boats_cli(monkeypatch, write_coverage(tmp_path / "boats", names))
    assert calls[0]["symbols"] == names
    assert len(calls[0]["symbols"]) == 15_380
    assert calls[0]["max_seconds"] == 600
    assert calls[0]["publish"] is False


def test_boats_cli_admits_above_ordinary_default_and_loader_default_refuses(tmp_path, monkeypatch):
    # 12,500 names sit between the ordinary collector budget and the ceiling.
    names = coverage_names(12_500, first="AMD")
    coverage = write_coverage(tmp_path / "boats", names)
    with pytest.raises(ValueError):
        ing.load_symbols("", coverage)
    calls = []
    stub_cli_stream(monkeypatch, calls)
    run_boats_cli(monkeypatch, coverage)
    assert calls[0]["symbols"] == names


def test_loader_explicit_ceiling_is_accepted(tmp_path):
    path = write_coverage(tmp_path / "boats", coverage_names(20_000))
    symbols = ing.load_symbols("", path, limit=publisher.MAX_BOATS_SYMBOLS)
    assert len(symbols) == 20_000 and symbols[0] == "Z00000" and symbols[-1] == "Z19999"


def test_loader_and_cli_refuse_above_ceiling_before_any_provider_effect(tmp_path, monkeypatch):
    over = write_coverage(tmp_path / "over", coverage_names(20_001, first="AMD"))
    with pytest.raises(ValueError):
        ing.load_symbols("", over, limit=20_001)
    calls = []
    stub_cli_stream(monkeypatch, calls, forbidden=True)
    with pytest.raises(ValueError):
        run_boats_cli(monkeypatch, over)
    assert not calls


@pytest.mark.parametrize("limit", [0, -1, 20_001, 12_000.0, "12000", True, None])
def test_loader_limit_must_be_a_bounded_positive_integer(tmp_path, limit):
    # Validation precedes the file read: a missing file must not be reached.
    with pytest.raises(ValueError):
        ing.load_symbols("", str(tmp_path / "never-read.txt"), limit=limit)


def test_loader_default_budget_refuses_12001_but_admits_12000(tmp_path):
    with pytest.raises(ValueError, match="12000"):
        ing.load_symbols("", write_coverage(tmp_path / "over", coverage_names(12_001)))
    kept = ing.load_symbols("", write_coverage(tmp_path / "exact", coverage_names(12_000)))
    assert len(kept) == 12_000


def test_loader_preserves_dedup_comments_and_file_size_rules(tmp_path):
    path = tmp_path / "dedup.txt"
    path.write_text("AMD\nAMD\n# comment\n\nNVDA\nBRK.B\n", encoding="utf-8")
    symbols = ing.load_symbols("", str(path), limit=publisher.MAX_BOATS_SYMBOLS)
    assert symbols == ["AMD", "NVDA", "BRK.B"]
    big = tmp_path / "big.txt"
    big.write_text("A" * 2_000_001, encoding="utf-8")
    with pytest.raises(ValueError, match="bounded size"):
        ing.load_symbols("", str(big), limit=publisher.MAX_BOATS_SYMBOLS)


# ── F9a: failed publication attempts consume their rate-limit slot ───────────

def test_transient_failed_put_is_rate_limited_like_a_success(monkeypatch):
    import scripts.tiingo_ingest as ing

    clock = {"t": 0.0}
    put_attempts = []
    monkeypatch.setattr(publisher, "time",
                        types.SimpleNamespace(monotonic=lambda: clock["t"]))
    monkeypatch.setattr(publisher, "_publish_r2",
                        lambda raw: put_attempts.append(clock["t"]) or False)

    def stream(**kw):
        observe = kw["observer"]
        observe("connected", {"connection": 1})   # forced attempt at t=0.0 fails
        clock["t"] = 1.0
        for _ in range(50):
            observe("archived", {"active": True, "connection": 1, "frames": []})
            observe("tick", {})                   # 100 rapid emits, all < 5s apart
        clock["t"] = 5.5
        observe("tick", {})                       # slot elapsed: exactly one retry
        clock["t"] = 6.0
        for _ in range(50):
            observe("tick", {})                   # rate limited again
        observe("ended", {})                      # forced terminal invalidation
        return {"raw_messages": 102, "segments": 1}

    monkeypatch.setattr(ing, "boats_stream", stream)
    result = publisher.publish_boats_stream(publish=True)
    # t=0.0 connect, t=5.5 first eligible retry, t=6.0 forced final invalidation.
    assert put_attempts == [0.0, 5.5, 6.0]
    assert result["publication"]["attempted"] == 3
    assert result["publication"]["succeeded"] == 0 and result["publication"]["failed"] == 3
    assert result["publication"]["final_invalidation_delivered"] is False
    assert result["publication"]["access_denied"] is False
    assert result["publication_ok"] is False


def test_succeeded_put_keeps_forcing_only_the_terminal_invalidation(monkeypatch):
    import scripts.tiingo_ingest as ing

    clock = {"t": 0.0}
    put_attempts = []
    monkeypatch.setattr(publisher, "time",
                        types.SimpleNamespace(monotonic=lambda: clock["t"]))
    monkeypatch.setattr(publisher, "_publish_r2",
                        lambda raw: put_attempts.append(clock["t"]) or True)

    def stream(**kw):
        observe = kw["observer"]
        observe("connected", {"connection": 1})
        clock["t"] = 1.0
        for _ in range(50):
            observe("tick", {})
        clock["t"] = 2.0
        observe("ended", {})
        return {"raw_messages": 0, "segments": 0}

    monkeypatch.setattr(ing, "boats_stream", stream)
    result = publisher.publish_boats_stream(publish=True)
    assert put_attempts == [0.0, 2.0]
    assert result["publication"]["attempted"] == 2
    assert result["publication"]["succeeded"] == 2 and result["publication"]["failed"] == 0
    assert result["publication"]["final_invalidation_delivered"] is True
    assert result["publication_ok"] is True


# ── F9b: archive storage failure is not a transport break ────────────────────

class SocketStub:
    def __init__(self, incoming, clock=None):
        self.incoming = iter(incoming)
        self.closed = False
        self.sent = None
        self.clock = clock

    def settimeout(self, seconds):
        assert seconds == 3

    def send(self, payload):
        self.sent = payload

    def recv(self):
        if self.clock is not None:
            # Each delivered frame ages the flush clock past its deadline.
            self.clock["t"] += 5.0
        try:
            return next(self.incoming)
        except StopIteration:
            raise RuntimeError("mock transport interruption") from None

    def close(self):
        self.closed = True


def boats_frame(stamp="2026-10-09T01:00:01Z", symbol="AMD"):
    event = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    epoch_ns = int(event.timestamp()) * 1_000_000_000
    data = ["T", stamp, epoch_ns, symbol, 100.02, 25, "@", "F", "", ""]
    return f'{{"service":"boats","data":{data!r}}}'.replace("'", '"')


def fake_stream(monkeypatch, sockets, frames, arrivals, clock):
    sockets.append(SocketStub(frames, clock))
    queue = iter(sockets)
    stub = types.SimpleNamespace(
        create_connection=lambda *args, **kwargs: next(queue),
        WebSocketException=RuntimeError,
        WebSocketTimeoutException=TimeoutError,
    )
    monkeypatch.setitem(sys.modules, "websocket", stub)
    monkeypatch.setattr(ing, "read_key", lambda: "dummy-test-key-never-issued")
    arriving = iter(arrivals)
    monkeypatch.setattr(ing, "utc_now", lambda: next(arriving))
    monkeypatch.setattr(ing.time, "sleep", lambda _: None)
    monkeypatch.setattr(ing.time, "monotonic", lambda: clock["t"])


def scratch_lake(tmp_path, monkeypatch):
    monkeypatch.setattr(archive_module, "EXTERNAL_MOUNT", tmp_path)
    return archive_module.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def test_disk_oserror_stops_stream_without_reconnect_or_archived_event(
        tmp_path, monkeypatch):
    lake = scratch_lake(tmp_path, monkeypatch)
    sockets, seen = [], []
    clock = {"t": 0.0}
    fake_stream(monkeypatch, sockets, [boats_frame()],
                ["2026-10-09T01:00:01.100Z"], clock)

    def disk_failure(path, data):
        raise OSError(5, "simulated external-drive I/O error")

    monkeypatch.setattr(archive_module, "_publish_once", disk_failure)
    clock["t"] = 5.0  # flush deadline reached inside the receive loop
    with pytest.raises(archive_module.TiingoArchiveError, match="storage failed") as err:
        ing.boats_stream(max_seconds=10, max_messages=1, batch_messages=100,
                         flush_seconds=2, archive=lake,
                         observer=lambda kind, payload: seen.append(kind))
    assert isinstance(err.value.__cause__, OSError)
    # Storage failure is terminal: no second connection, no gap framing.
    assert len(sockets) == 1 and sockets[0].closed
    assert seen == ["connected", "error", "disconnected", "ended"]
    assert "archived" not in seen and "gap" not in seen
    assert seen[-1] == "ended"
    # Nothing was published as archived raw for the failed segment.
    assert not (tmp_path / "lake" / "receipts" / "boats-firehose").exists()


def test_archive_refusal_passthrough_keeps_message_and_cause(tmp_path, monkeypatch):
    lake = scratch_lake(tmp_path, monkeypatch)
    sockets, seen = [], []
    clock = {"t": 0.0}
    fake_stream(monkeypatch, sockets, [boats_frame()],
                ["2026-10-09T01:00:01.100Z"], clock)

    def refused(_messages):
        raise archive_module.TiingoArchiveError(
            "external archive space reserve reached; stop ingest")

    monkeypatch.setattr(lake, "store_boats_batch", refused)
    clock["t"] = 5.0
    with pytest.raises(archive_module.TiingoArchiveError,
                       match="space reserve reached") as err:
        ing.boats_stream(max_seconds=10, max_messages=1, batch_messages=100,
                         flush_seconds=2, archive=lake,
                         observer=lambda kind, payload: seen.append(kind))
    assert err.value.__cause__ is None
    assert len(sockets) == 1 and sockets[0].closed
    assert "archived" not in seen and "gap" not in seen
    assert seen[-1] == "ended"
