"""Tests for engine/gdelt_client.py — shared GDELT fetch client.

No live network: all HTTP calls are mocked.  Covers:
  - Cross-process throttle: spacing >= min_interval across two calls.
  - 429 -> backoff -> success path: sleeps the right intervals, returns articles.
  - Final-failure path (429 on every attempt): returns (None, 'rate_limited').
  - Failure never cached: a rate_limited result is NOT written to cache_path.
  - Success cached: a successful result IS written to cache_path, and a second
    call with a fresh cache returns the cached articles without hitting the network.
  - no_articles reason: empty artlist -> ([], 'no_articles').
  - Non-200 -> (None, 'fetch_error').
  - Non-JSON content-type -> (None, 'rate_limited') (GDELT rate-limit text pattern).

Run:  python3 -m pytest tests/test_gdelt_client.py -x -q
"""
from __future__ import annotations

import json
import multiprocessing
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import gdelt_client as _gc


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_response(status: int, json_body: dict | None = None, content_type: str = "application/json"):
    """Build a minimal mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"Content-Type": content_type}
    if json_body is not None:
        resp.json.return_value = json_body
    return resp


def _gdelt_body(titles: list[str]) -> dict:
    """Minimal GDELT artlist JSON with the given titles."""
    return {
        "articles": [
            {"title": t, "url": f"https://example.com/{i}", "domain": "example.com",
             "seendate": "20260710T120000Z"}
            for i, t in enumerate(titles)
        ]
    }


_SAMPLE_PARAMS = {"query": "tariff", "mode": "artlist", "format": "json", "maxrecords": "10"}


# ── throttle tests ────────────────────────────────────────────────────────────

class _VirtualClock:
    """Virtual clock with recorded sleeps and explicit scheduling advances.
    Substituted for the throttle's
    `_now` / `_sleep` seams so spacing tests assert exactly what the throttle
    requested instead of a wall-clock measurement that flakes on loaded runners."""

    def __init__(self, t0: float = 1000.0):
        self.t = float(t0)
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


def test_throttle_spacing_between_two_calls(tmp_path):
    """Two sequential calls must be spaced >= min_interval seconds apart.

    Deterministic: the throttle runs on a virtual clock, so the gap equals the
    sleep the throttle itself requested — runner load cannot shrink it."""
    clock = _VirtualClock()
    timestamps: list[float] = []

    def _fake_requests_get(*args, **kwargs):
        timestamps.append(clock.now())
        return _make_response(200, _gdelt_body(["headline one"]))

    min_interval = 0.05  # short for speed
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch("requests.get", side_effect=_fake_requests_get):
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=min_interval)
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=min_interval)

    assert len(timestamps) == 2, "expected exactly two network requests"
    gap = timestamps[1] - timestamps[0]
    # Tolerance only absorbs float rounding of the virtual clock's t += sleep.
    assert gap >= min_interval - 1e-9, (
        f"requests were only {gap:.4f}s apart on the virtual clock; "
        f"expected >= {min_interval}s"
    )
    # The second call must actually have paced: with the clock frozen between
    # calls, the only legal sleep is the full remaining interval.
    assert clock.sleeps and abs(clock.sleeps[0] - min_interval) < 1e-9, (
        f"throttle did not request a {min_interval}s sleep; sleeps={clock.sleeps}"
    )


def test_transport_spacing_survives_delay_after_unlock(tmp_path):
    """A pause after releasing the slot must not bunch real transport starts."""
    clock = _VirtualClock()
    stamp_file = tmp_path / "last_request"
    starts = []
    real_flock = _gc.fcntl.flock
    delayed = False

    def delayed_unlock(fd, operation):
        nonlocal delayed
        real_flock(fd, operation)
        if operation == _gc.fcntl.LOCK_UN and not delayed:
            delayed = True
            clock.t += 0.02

    def transport(*args, **kwargs):
        starts.append(clock.now())
        return _make_response(200, _gdelt_body(["headline"]))

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch.object(_gc.fcntl, "flock", side_effect=delayed_unlock), \
         patch("requests.get", side_effect=transport):
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.05)
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.05)

    assert len(starts) == 2
    assert starts[1] - starts[0] >= 0.05 - 1e-9


def _assert_stamp_lock(stamp_file, *, held):
    with open(stamp_file, "a+") as probe:
        if held:
            with pytest.raises(BlockingIOError):
                _gc.fcntl.flock(probe, _gc.fcntl.LOCK_EX | _gc.fcntl.LOCK_NB)
        else:
            _gc.fcntl.flock(probe, _gc.fcntl.LOCK_EX | _gc.fcntl.LOCK_NB)
            _gc.fcntl.flock(probe, _gc.fcntl.LOCK_UN)


def _hold_guard_in_child(stamp_file, entered, release, fail):
    _gc._stamp_path = lambda: Path(stamp_file)
    try:
        with _gc.request_turn(0):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("parent did not release fixture transport")
            if fail:
                raise ValueError("fixture transport failed")
    except ValueError:
        if not fail:
            raise


def _exit_during_transport_in_child(stamp_file):
    _gc._stamp_path = lambda: Path(stamp_file)
    _gc._now = lambda: 1000.0
    with _gc.request_turn(0.05):
        os._exit(23)  # Abrupt transport death deliberately skips Python finally.


def test_abrupt_transport_exit_retains_reservation_for_next_process(tmp_path):
    stamp_file = tmp_path / "last_request"
    stamp_file.write_text("0")
    identity = (stamp_file.stat().st_dev, stamp_file.stat().st_ino)
    ctx = multiprocessing.get_context("spawn")
    child = ctx.Process(target=_exit_during_transport_in_child,
                        args=(str(stamp_file),))
    child.start()
    try:
        child.join(10)
        assert not child.is_alive(), "fixture transport did not exit"
        assert child.exitcode == 23
        _assert_stamp_lock(stamp_file, held=False)
        assert (stamp_file.stat().st_dev, stamp_file.stat().st_ino) == identity
        assert float(stamp_file.read_text()) == pytest.approx(1000.0)

        clock = _VirtualClock(1000.02)
        starts = []
        with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
             patch.object(_gc, "_now", clock.now), \
             patch.object(_gc, "_sleep", clock.sleep):
            with _gc.request_turn(0.05):
                starts.append(clock.now())
        assert starts == pytest.approx([1000.05])
        assert clock.sleeps == pytest.approx([0.03])
        assert float(stamp_file.read_text()) == pytest.approx(1000.05)
        _assert_stamp_lock(stamp_file, held=False)
    finally:
        if child.is_alive():
            child.terminate()
        child.join(2)


@pytest.mark.parametrize("fail", [False, True])
def test_request_guard_keeps_same_inode_locked_across_processes(tmp_path, fail):
    stamp_file = tmp_path / "last_request"
    stamp_file.write_text("0")
    identity = (stamp_file.stat().st_dev, stamp_file.stat().st_ino)
    ctx = multiprocessing.get_context("spawn")
    entered, release = ctx.Event(), ctx.Event()
    child = ctx.Process(target=_hold_guard_in_child,
                        args=(str(stamp_file), entered, release, fail))
    child.start()
    try:
        assert entered.wait(10), "child did not enter its transport"
        _assert_stamp_lock(stamp_file, held=True)
        assert (stamp_file.stat().st_dev, stamp_file.stat().st_ino) == identity
        release.set()
        child.join(10)
        assert not child.is_alive(), "request guard did not settle"
        assert child.exitcode == 0
        _assert_stamp_lock(stamp_file, held=False)
        assert (stamp_file.stat().st_dev, stamp_file.stat().st_ino) == identity
    finally:
        release.set()
        child.join(2)
        if child.is_alive():
            child.terminate()
            child.join(2)


def test_artlist_failure_stamps_completion_and_next_request_waits(tmp_path):
    clock = _VirtualClock()
    stamp_file = tmp_path / "last_request"
    starts = []

    def transport(*args, **kwargs):
        _assert_stamp_lock(stamp_file, held=True)
        starts.append(clock.now())
        clock.t += 0.02
        if len(starts) == 1:
            raise OSError("fixture transport failure")
        return _make_response(200, _gdelt_body(["recovered"]))

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch("requests.get", side_effect=transport):
        assert _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.05) == (None, "fetch_error")
        assert len(starts) == 1
        completed = float(stamp_file.read_text())
        assert completed == pytest.approx(1000.02)
        _assert_stamp_lock(stamp_file, held=False)
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.05)
    assert articles and reason is None
    assert len(starts) == 2
    assert starts[1] - completed == pytest.approx(0.05)
    assert float(stamp_file.read_text()) == pytest.approx(starts[1] + 0.02)


@pytest.mark.parametrize("phase", ["open", "acquire", "read", "sleep",
                                   "reservation_write", "completion_write", "unlock", "close"])
@pytest.mark.parametrize("body_raises", [False, True])
def test_pacing_failures_never_repeat_or_mask_transport(tmp_path, phase, body_raises):
    stamp_file = tmp_path / "last_request"
    stamp_file.write_text("1000.0")
    clock = _VirtualClock()
    real_open, real_flock = open, _gc.fcntl.flock
    opened, calls = [], []
    sentinel = RuntimeError("fixture transport exception")

    class Stamp:
        def __init__(self, raw):
            self.raw = raw
            self.writes = 0

        def __getattr__(self, name):
            return getattr(self.raw, name)

        def read(self):
            if phase == "read":
                raise OSError("fixture read failure")
            return self.raw.read()

        def write(self, value):
            self.writes += 1
            if ((phase == "reservation_write" and self.writes == 1)
                    or (phase == "completion_write" and self.writes == 2)):
                raise OSError(f"fixture {phase} failure")
            return self.raw.write(value)

        def close(self):
            self.raw.close()
            if phase == "close":
                raise OSError("fixture close failure after descriptor release")

    def open_stamp(*args, **kwargs):
        if phase == "open":
            raise OSError("fixture open failure")
        fd = Stamp(real_open(*args, **kwargs))
        opened.append(fd)
        return fd

    def flock(fd, operation):
        if ((phase == "acquire" and operation == _gc.fcntl.LOCK_EX)
                or (phase == "unlock" and operation == _gc.fcntl.LOCK_UN)):
            raise OSError("fixture lock operation failure")
        return real_flock(fd, operation)

    def sleep(seconds):
        if phase == "sleep":
            raise OSError("fixture pacing failure")
        clock.sleep(seconds)

    def invoke():
        with _gc.request_turn(0.05):
            calls.append("transport")
            clock.t += 0.02
            if body_raises:
                raise sentinel
            return "transport result"

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", side_effect=sleep), \
         patch.object(_gc, "open", side_effect=open_stamp, create=True), \
         patch.object(_gc.fcntl, "flock", side_effect=flock):
        if body_raises:
            with pytest.raises(RuntimeError) as exc:
                invoke()
            assert exc.value is sentinel
        else:
            assert invoke() == "transport result"
    assert calls == ["transport"]
    assert all(fd.raw.closed for fd in opened)
    _assert_stamp_lock(stamp_file, held=False)


def test_cancelled_transport_preserves_exception_and_releases_lock(tmp_path):
    clock = _VirtualClock()
    stamp_file = tmp_path / "last_request"
    sentinel = KeyboardInterrupt("fixture cancellation")
    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep):
        with pytest.raises(KeyboardInterrupt) as exc:
            with _gc.request_turn(0):
                clock.t += 0.02
                raise sentinel
    assert exc.value is sentinel
    assert float(stamp_file.read_text()) == pytest.approx(1000.02)
    _assert_stamp_lock(stamp_file, held=False)


@pytest.mark.parametrize("volume_error", [False, True])
def test_hk_entity_guards_each_real_transport_once(tmp_path, volume_error):
    from collectors import hk_gdelt as hk

    clock = _VirtualClock()
    stamp_file = tmp_path / "last_request"
    starts, modes = [], []

    def transport(url, *, params, timeout):
        _assert_stamp_lock(stamp_file, held=True)
        assert url == hk._GDELT_BASE and timeout == 30
        starts.append(clock.now())
        modes.append(params["mode"])
        clock.t += 0.02
        if volume_error and params["mode"] == "timelinevol":
            raise OSError("fixture volume failure")
        value = 2.0 if params["mode"] == "timelinevol" else 3.0
        return _make_response(200, {"timeline": [{"data": [
            {"date": "20260708T000000Z", "value": value}]}]})

    session = SimpleNamespace(get=transport)
    entity = hk._Entity("fixture", "TEST.HK", "Fixture", "Fixture", ["fixture"])
    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch.object(_gc, "wait_turn", wraps=_gc.wait_turn) as old_gate:
        frame = hk._fetch_entity(entity, session)
    assert frame is not None and len(frame) == 1
    assert frame.iloc[0]["avg_tone"] == 3.0
    if not volume_error:
        assert frame.iloc[0]["vol_intensity"] == 2.0
    assert modes == ["timelinevol", "timelinetone"]
    assert starts[1] - starts[0] == pytest.approx(0.02 + hk._REQUEST_GAP)
    assert len(clock.sleeps) == 1
    old_gate.assert_not_called()
    _assert_stamp_lock(stamp_file, held=False)


@pytest.mark.parametrize("outcome", ["ok", "http_error", "read_error"])
def test_missing_tape_guards_open_read_and_close(tmp_path, outcome):
    from engine import missing_tape_gdelt as mt
    from urllib.error import HTTPError

    clock = _VirtualClock()
    stamp_file = tmp_path / "last_request"
    records = [{"date": "20260708", "value": 2.0}]
    calls, closes = [], []
    response = MagicMock()
    response.__enter__.return_value = response
    response.getcode.return_value = 200

    def read():
        _assert_stamp_lock(stamp_file, held=True)
        clock.t += 0.02
        if outcome == "read_error":
            raise OSError("fixture response read failure")
        return json.dumps({"timeline": records}).encode()

    def close(*args):
        _assert_stamp_lock(stamp_file, held=True)
        closes.append("closed")

    response.read.side_effect = read
    response.__exit__.side_effect = close

    def urlopen(req, *, timeout):
        _assert_stamp_lock(stamp_file, held=True)
        assert timeout == 30
        calls.append(req.full_url)
        if outcome == "http_error":
            clock.t += 0.02
            raise HTTPError(req.full_url, 503, "fixture", {}, None)
        return response

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch.object(mt.urllib.request, "urlopen", side_effect=urlopen):
        result = mt._fetch_gdelt("https://example.invalid/fixture")
    expected = (records, "ok") if outcome == "ok" else (
        [], "http_503" if outcome == "http_error" else "error")
    assert result == expected
    assert calls == ["https://example.invalid/fixture"]
    assert closes == ([] if outcome == "http_error" else ["closed"])
    assert float(stamp_file.read_text()) == pytest.approx(1000.02)
    _assert_stamp_lock(stamp_file, held=False)


@pytest.mark.parametrize("caller", ["hk", "missing_tape"])
def test_timeline_breaker_bypass_keeps_one_unpaced_transport(tmp_path, caller):
    from collectors import hk_gdelt as hk
    from engine import missing_tape_gdelt as mt

    stamp_file = tmp_path / "last_request"
    _penalty_file(stamp_file).write_text(str(time.time() + 600))
    response = _make_response(200, {"timeline": []})
    response.__enter__.return_value = response
    response.getcode.return_value = 200
    response.read.return_value = b'{"timeline": []}'
    transport = MagicMock(return_value=response)
    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", side_effect=AssertionError("pacing must be bypassed")), \
         patch.object(_gc, "_sleep", side_effect=AssertionError("pacing must be bypassed")), \
         patch.object(mt.urllib.request, "urlopen", transport):
        if caller == "hk":
            assert hk._gdelt_timeline("fixture", "timelinevol",
                                      SimpleNamespace(get=transport)) == []
        else:
            assert mt._fetch_gdelt("https://example.invalid/fixture") == ([], "empty")
    assert transport.call_count == 1
    assert not stamp_file.exists()


def test_retry_backoffs_release_lock_and_keep_three_attempt_limit(tmp_path):
    stamp_file = tmp_path / "last_request"
    clock = _VirtualClock()
    backoffs, calls = [], []

    def transport(*args, **kwargs):
        _assert_stamp_lock(stamp_file, held=True)
        calls.append("request")
        return _make_response(429)

    def backoff(seconds):
        _assert_stamp_lock(stamp_file, held=False)
        backoffs.append(seconds)
        clock.t += seconds

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch("requests.get", side_effect=transport), \
         patch("time.sleep", side_effect=backoff):
        assert _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.05) == (None, "rate_limited")
    assert calls == ["request"] * 3
    assert backoffs == [30, 75]


# ── retry / backoff tests ─────────────────────────────────────────────────────

def test_429_then_success(tmp_path):
    """429 on attempt-0 -> sleep 30s -> success on attempt-1 -> returns articles."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    responses = [
        _make_response(429),
        _make_response(200, _gdelt_body(["Tariff news headline"])),
    ]

    sleep_calls: list[float] = []

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", side_effect=responses), \
         patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):

        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles is not None and len(articles) == 1
    assert articles[0]["title"] == "Tariff news headline"
    assert reason is None
    # Must have slept the first-retry interval
    assert any(s >= 29 for s in sleep_calls), (
        f"expected a sleep >= 29s after first 429; got sleep_calls={sleep_calls}"
    )


def test_429_all_attempts_returns_none(tmp_path):
    """Three consecutive 429s -> (None, 'rate_limited')."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    responses = [_make_response(429)] * 3

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", side_effect=responses), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles is None
    assert reason == "rate_limited"


def test_non_200_returns_fetch_error(tmp_path):
    """HTTP 500 -> (None, 'fetch_error')."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", return_value=_make_response(500)), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles is None
    assert reason == "fetch_error"


def test_non_json_content_type_rate_limited(tmp_path):
    """200 + text/plain content-type (GDELT rate-limit text body) -> rate_limited."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    # Three non-JSON responses (all retry attempts)
    responses = [_make_response(200, content_type="text/plain")] * 3

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", side_effect=responses), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles is None
    assert reason == "rate_limited"


# ── cache tests ───────────────────────────────────────────────────────────────

def test_failure_not_cached(tmp_path):
    """A rate_limited result must NOT be written to cache_path."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file = tmp_path / "cache.json"
    responses = [_make_response(429)] * 3

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", side_effect=responses), \
         patch("time.sleep"):
        _gc.get_articles(_SAMPLE_PARAMS, cache_path=cache_file,
                         cache_ttl_s=3600, min_interval=0.0)

    assert not cache_file.exists(), "failure result must not be written to cache"


def test_success_is_cached(tmp_path):
    """A successful fetch must write to cache_path; a second call returns cached data
    without any network request."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file = tmp_path / "cache.json"
    resp = _make_response(200, _gdelt_body(["Tariff headline for cache test"]))

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", return_value=resp) as mock_get, \
         patch("time.sleep"):
        # First call: hits network
        arts1, r1 = _gc.get_articles(_SAMPLE_PARAMS, cache_path=cache_file,
                                     cache_ttl_s=3600, min_interval=0.0)
        # Second call: should use cache, NOT the network
        arts2, r2 = _gc.get_articles(_SAMPLE_PARAMS, cache_path=cache_file,
                                     cache_ttl_s=3600, min_interval=0.0)

    assert cache_file.exists(), "cache file must be written after success"
    assert mock_get.call_count == 1, (
        f"network was called {mock_get.call_count} times; expected 1 (cache hit on 2nd)"
    )
    assert arts1 is not None and len(arts1) == 1
    assert arts2 is not None and len(arts2) == 1
    assert arts1[0]["title"] == arts2[0]["title"] == "Tariff headline for cache test"


# ── article normalisation ─────────────────────────────────────────────────────

def test_parse_articles_seendate_normalisation():
    """_parse_articles converts GDELT compact seendate to ISO 8601."""
    raw = {
        "articles": [
            {"title": "T", "url": "http://x.com", "domain": "x.com",
             "seendate": "20260710T120000Z"},
        ]
    }
    out = _gc._parse_articles(raw)
    assert len(out) == 1
    assert out[0]["seendate"].startswith("2026-07-10"), out[0]["seendate"]


def test_parse_articles_language_sourcecountry_passthrough():
    """_parse_articles must preserve language and sourcecountry from the raw article.
    These fields are needed by commodity_news; hardcoding '' would silently drop
    real per-article metadata."""
    raw = {
        "articles": [
            {"title": "T", "url": "http://x.com", "domain": "x.com",
             "seendate": "20260710T120000Z",
             "language": "English", "sourcecountry": "United States"},
            # Article without these fields — should default to empty string, not KeyError
            {"title": "T2", "url": "http://y.com", "domain": "y.com",
             "seendate": "20260710T120000Z"},
        ]
    }
    out = _gc._parse_articles(raw)
    assert len(out) == 2
    assert out[0]["language"] == "English"
    assert out[0]["sourcecountry"] == "United States"
    assert out[1]["language"] == ""
    assert out[1]["sourcecountry"] == ""


def test_empty_artlist_returns_no_articles_reason(tmp_path):
    """An empty articles list -> ([], 'no_articles')."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    resp = _make_response(200, {"articles": []})

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", return_value=resp), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles == []
    assert reason == "no_articles"


# ── cross-process stamp correctness tests ────────────────────────────────────

def test_stamp_is_wall_clock_unix_time(tmp_path):
    """The on-disk stamp written by _throttle must be a wall-clock unix timestamp
    (time.time()) so it is meaningful when read by a different process.  Before this
    fix the code wrote time.monotonic() instead — not comparable across processes or
    after a reboot."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)

    before = time.time()

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", return_value=_make_response(200, _gdelt_body(["t"]))), \
         patch("time.sleep"):
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    after = time.time()
    assert stamp_file.exists(), "stamp file must be written after a request"

    raw = stamp_file.read_text().strip()
    stamp_val = float(raw)
    # A wall-clock unix timestamp for now is ~1.75e9; time.monotonic() on this
    # box is in the tens-of-thousands-of-seconds range (boot-relative).
    # Assert the stamp is within the wall-clock window.
    assert before <= stamp_val <= after + 1.0, (
        f"stamp {stamp_val!r} is not a wall-clock unix time (expected {before:.1f}..{after:.1f}); "
        "was time.monotonic() written instead of time.time()?"
    )


def test_cross_process_stamp_honoured(tmp_path):
    """Simulate a prior process writing a wall-clock stamp. A second call in THIS
    process must read it and enforce the spacing — proving cross-process pacing works.
    If the code were writing time.monotonic() this test would still pass by accident
    (same-process), but combined with test_stamp_is_wall_clock_unix_time it catches
    the regression.

    Deterministic: the throttle runs on the virtual clock, so the asserted gap is
    the sleep the throttle requested — no wall-clock measurement."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    min_interval = 0.05
    clock = _VirtualClock()

    # Simulate a prior process having fetched 0.5 * min_interval ago
    prior_ts = clock.now() - (min_interval * 0.5)
    stamp_file.write_text(str(prior_ts))

    request_times: list[float] = []

    def _fake_get(*args, **kwargs):
        request_times.append(clock.now())
        return _make_response(200, _gdelt_body(["x"]))

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep), \
         patch("requests.get", side_effect=_fake_get):
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=min_interval)

    assert len(request_times) == 1
    # The throttle must sleep out exactly the remaining half interval, so the
    # request lands a full min_interval after the prior-process stamp.
    assert len(clock.sleeps) == 1, (
        f"expected exactly one pacing sleep; got {clock.sleeps}"
    )
    assert abs(clock.sleeps[0] - min_interval * 0.5) < 1e-9, (
        f"throttle requested sleep {clock.sleeps[0]!r}; expected {min_interval * 0.5}s"
    )
    elapsed_since_prior = request_times[0] - prior_ts
    assert elapsed_since_prior >= min_interval - 1e-9, (
        f"request fired only {elapsed_since_prior:.4f}s after prior-process stamp "
        f"(expected >= {min_interval}s); cross-process pacing not honoured"
    )


# ── query-rejection tests (the 2026-06-20..07-10 news_vector stall shape) ────

def test_query_rejected_is_structural_not_retried(tmp_path):
    """GDELT 200 + text/html 'Your query was too short or too long.' must return
    (None, 'query_rejected') after ONE request — retrying a rejected query can
    never heal it and only burns the shared per-IP budget. Binning it as
    rate_limited/fetch_error is how the news_vector stall hid for three weeks."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    rejected = _make_response(200, content_type="text/html; charset=utf-8")
    rejected.text = "Your query was too short or too long.\n"
    calls: list[int] = []

    def _fake_get(*args, **kwargs):
        calls.append(1)
        return rejected

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", side_effect=_fake_get), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles is None
    assert reason == "query_rejected"
    assert len(calls) == 1, "a rejected query must NOT be retried"


def test_non_json_unknown_text_still_retried_as_rate_limit(tmp_path):
    """200 + non-JSON WITHOUT a rejection marker keeps the conservative
    retry-as-rate-limit behavior (GDELT's throttle text is 200 + plain text)."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    throttled = _make_response(200, content_type="text/plain")
    throttled.text = "Please limit requests to one every 5 seconds or contact ..."

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", return_value=throttled), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles is None
    assert reason == "rate_limited"


# ── public wait_turn gate (timeline-endpoint callers) ─────────────────────────

def test_wait_turn_public_gate_spaces_calls(tmp_path):
    """The compatibility wait_turn() must still honour the shared stamp.

    Deterministic: wait_turn routes through _throttle, which runs on the virtual
    clock, so we assert the requested sleep and the persisted stamp delta instead
    of timing the second call with a wall clock (a scheduler pause between the
    first stamp and a monotonic t0 could otherwise shrink the measured gap)."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    min_interval = 0.05
    clock = _VirtualClock()

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_now", clock.now), \
         patch.object(_gc, "_sleep", clock.sleep):
        _gc.wait_turn(min_interval)          # claims the slot
        first_stamp = float(stamp_file.read_text())
        _gc.wait_turn(min_interval)          # must wait out the interval
        last_stamp = float(stamp_file.read_text())

    # Exactly one pacing sleep, for the full interval: with the clock frozen
    # between calls the second wait_turn had zero elapsed credit.
    assert len(clock.sleeps) == 1, (
        f"expected exactly one pacing sleep; got {clock.sleeps}"
    )
    assert abs(clock.sleeps[0] - min_interval) < 1e-9, (
        f"throttle requested sleep {clock.sleeps[0]!r}; expected {min_interval}s"
    )
    # The persisted stamp advanced by the same interval — the gap the next
    # process will observe when it reads the stamp file.
    assert abs(last_stamp - first_stamp - min_interval) < 1e-9, (
        f"stamp advanced {last_stamp - first_stamp!r}s; expected {min_interval}s"
    )


# ── circuit breaker: keep a 429-boxed IP off the critical path ────────────────

def _penalty_file(stamp_file: Path) -> Path:
    """The breaker stamp lives beside the throttle stamp (see _penalty_path), so
    mocking _stamp_path relocates BOTH into tmp — keeping these tests hermetic."""
    return stamp_file.parent / "rate_limit_until"


def test_breaker_short_circuits_when_active(tmp_path):
    """With the breaker armed (penalty stamp in the future), get_articles returns
    (None, 'rate_limited') INSTANTLY — no network request, no backoff sleep. This
    is what takes build_news off the 26-29 min critical path when the IP is boxed."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    _penalty_file(stamp_file).write_text(str(time.time() + 600))  # boxed for 10 min

    mock_get = MagicMock()
    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", mock_get), \
         patch("time.sleep") as mock_sleep:
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert (articles, reason) == (None, "rate_limited")
    assert mock_get.call_count == 0, "breaker must skip the network entirely"
    assert mock_sleep.call_count == 0, "breaker must not sleep/backoff while boxed"


def test_persistent_429_arms_breaker(tmp_path):
    """Three consecutive 429s (terminal rate_limited) must ARM the breaker by
    writing a penalty stamp ~cooldown seconds into the future."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_cooldown", return_value=900.0), \
         patch("requests.get", side_effect=[_make_response(429)] * 3), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert (articles, reason) == (None, "rate_limited")
    pen = _penalty_file(stamp_file)
    assert pen.exists(), "a persistent 429 must arm the breaker"
    assert float(pen.read_text()) > time.time() + 800, "penalty must extend ~cooldown ahead"


def test_success_clears_stale_breaker(tmp_path):
    """A valid 200 clears the breaker stamp — the IP recovered, so later calls fetch."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    pen = _penalty_file(stamp_file)
    pen.write_text(str(time.time() - 10))  # EXPIRED → breaker inactive, fetch proceeds

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", return_value=_make_response(200, _gdelt_body(["ok"]))), \
         patch("time.sleep"):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert articles and reason is None
    assert not pen.exists(), "a successful fetch must clear the stale breaker stamp"


def test_cache_served_even_when_breaker_active(tmp_path):
    """A FRESH cache is still served while the breaker is armed — the breaker skips
    only LIVE fetches; it must never suppress real cached data."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    _penalty_file(stamp_file).write_text(str(time.time() + 600))  # boxed
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps({"articles": [{"title": "cached"}], "degraded_reason": None}))

    mock_get = MagicMock()
    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("requests.get", mock_get):
        articles, reason = _gc.get_articles(_SAMPLE_PARAMS, cache_path=cache_file,
                                            cache_ttl_s=3600, min_interval=0.0)

    assert articles == [{"title": "cached"}]
    assert mock_get.call_count == 0, "cache hit must not touch the network even when boxed"


def test_breaker_disabled_when_cooldown_zero(tmp_path):
    """Cooldown 0 is the off-switch: a persistent 429 must NOT arm the breaker."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch.object(_gc, "_cooldown", return_value=0.0), \
         patch("requests.get", side_effect=[_make_response(429)] * 3), \
         patch("time.sleep"):
        _gc.get_articles(_SAMPLE_PARAMS, min_interval=0.0)

    assert not _penalty_file(stamp_file).exists(), "cooldown=0 must disable the breaker"


def test_wait_turn_short_circuits_when_breaker_active(tmp_path):
    """The compatibility wait_turn() must return immediately — no pacing
    sleep — while the IP is boxed, instead of burning 6s per doomed call."""
    stamp_file = tmp_path / "gdelt" / "last_request"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    _penalty_file(stamp_file).write_text(str(time.time() + 600))

    with patch.object(_gc, "_stamp_path", return_value=stamp_file), \
         patch("time.sleep") as mock_sleep:
        _gc.wait_turn(5.0)

    assert mock_sleep.call_count == 0, "wait_turn must not pace while the breaker is armed"


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-q"])
