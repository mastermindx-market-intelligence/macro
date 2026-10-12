"""FIF A20 — ONE incumbent shared SEC request pacer across all forensics collectors.

Offline and deterministic throughout: every clock is a fake closure and every
sleep is a list append.  The suites pin three facts:

1. one ``SecRequestPacer`` shared by ``SecForensicsCollector``,
   ``SecCompanyFactsCollector`` and ``SecFilingArchiveCollector`` sleeps
   between EVERY consecutive pair of requests across collectors, where three
   private pacers sleep strictly less (the multiplication A20 forbids);
2. ``acquire_bounded_filings`` hands BOTH collector factories the SAME pacer
   object (injected or self-built);
3. ``live_fetchers`` routes both the submissions and the companyfacts fetch
   paths through one injected pacer, and concurrent acquires can never place
   two marks inside one interval.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from collectors.edgar_forensics import SecForensicsCollector
from collectors.fundamental_forensics_acquisition import acquire_bounded_filings
from collectors.fundamental_forensics_companyfacts import SecCompanyFactsCollector
from collectors.sec_document_spine import SecFilingArchiveCollector
from collectors.sec_request_pacer import SecRequestPacer

USER_AGENT = "MastermindX research@example.com"


class FakeClock:
    """A clock that advances ONLY when the pacer sleeps (plus call epsilon)."""

    def __init__(self, *, epsilon: float = 0.0) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self.reads: list[float] = []
        self._epsilon = epsilon
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            self.now += self._epsilon
            self.reads.append(self.now)
            return self.now

    def sleeper(self, seconds: float) -> None:
        with self._lock:
            self.sleeps.append(seconds)
            self.now += seconds


def _shared_collectors(tmp_path: Path, pacer: SecRequestPacer):
    forensics = SecForensicsCollector(
        tmp_path / "raw", user_agent=USER_AGENT, session=_Session(), pacer=pacer
    )
    facts = SecCompanyFactsCollector(user_agent=USER_AGENT, pacer=pacer)
    archive = SecFilingArchiveCollector(
        tmp_path / "archive", user_agent=USER_AGENT, session=_Session(), pacer=pacer
    )
    return forensics, facts, archive


def test_one_shared_pacer_sleeps_between_every_consecutive_pair(tmp_path: Path):
    clock = FakeClock()
    pacer = SecRequestPacer(min_interval_seconds=0.12, sleeper=clock.sleeper, monotonic=clock.monotonic)
    forensics, facts, archive = _shared_collectors(tmp_path, pacer)

    # Interleave requests across the three collectors on the shared budget.
    for _round in range(3):
        forensics._pace()
        facts._pace()
        archive._pace()

    # 9 acquires: the first never sleeps, every later one sleeps the full
    # interval because the fake clock advances only inside the sleeper.
    assert len(clock.sleeps) == 8
    assert all(wait == pytest.approx(0.12) for wait in clock.sleeps)
    # All three collectors really delegate to the SAME pacer object.
    assert forensics._pacer is pacer and facts._pacer is pacer and archive._pacer is pacer


def test_three_private_pacers_sleep_strictly_less_on_the_same_sequence(tmp_path: Path):
    # The identical interleave with NO shared pacer: each collector owns a
    # private SecRequestPacer on the same fake clock — the exact object each
    # constructor builds for itself when ``pacer=`` is not supplied.
    clock = FakeClock()
    pacers = [
        SecRequestPacer(min_interval_seconds=0.12, sleeper=clock.sleeper, monotonic=clock.monotonic)
        for _ in range(3)
    ]
    for _round in range(3):
        for pacer in pacers:
            pacer.acquire()

    # Only the first pacer of each round pays the interval; the others ride
    # the clock it advanced — the per-worker multiplication A20 forbids.
    assert 0 < len(clock.sleeps) < 8

    # Collectors built without ``pacer=`` really do get private pacers bound
    # to their own interval (byte-for-byte legacy behaviour).
    forensics = SecForensicsCollector(tmp_path / "raw", user_agent=USER_AGENT, session=_Session())
    facts = SecCompanyFactsCollector(user_agent=USER_AGENT)
    archive = SecFilingArchiveCollector(tmp_path / "archive", user_agent=USER_AGENT, session=_Session())
    for collector in (forensics, facts, archive):
        assert isinstance(collector._pacer, SecRequestPacer)
        assert collector._pacer.min_interval_seconds == collector.min_interval_seconds
    assert forensics._pacer is not facts._pacer
    assert facts._pacer is not archive._pacer


def test_first_acquire_never_sleeps_and_interval_is_floored():
    clock = FakeClock()
    pacer = SecRequestPacer(min_interval_seconds=0.001, sleeper=clock.sleeper, monotonic=clock.monotonic)
    assert pacer.min_interval_seconds == 0.1  # the 0.1s floor, exactly as before
    assert pacer.last_request_at is None
    pacer.acquire()
    assert clock.sleeps == []  # never sleeps before the first request
    pacer.acquire()
    assert clock.sleeps == [pytest.approx(0.1)]


def test_acquisition_hands_both_factories_the_same_pacer_object(tmp_path: Path):
    captured: dict[str, dict] = {}

    class _StubSubmissions:
        def __init__(self, raw_root, **kwargs) -> None:
            captured["submissions"] = kwargs

        def fetch(self, *args, **kwargs):  # offline stub: per-ticker failure
            raise RuntimeError("offline stub")

    class _StubArchive:
        def __init__(self, archive_root, **kwargs) -> None:
            captured["archive"] = kwargs

        def fetch_primary_document(self, *args, **kwargs):
            raise RuntimeError("offline stub")

    pacer = SecRequestPacer(sleeper=lambda _s: None, monotonic=lambda: 0.0)
    acquire_bounded_filings(
        targets=("FXT=1",),
        raw_root=tmp_path / "raw",
        archive_root=tmp_path / "archive",
        user_agent=USER_AGENT,
        as_of="2026-08-01T23:59:59Z",
        recorded_at="2026-08-02T00:05:00Z",
        min_interval_seconds=0.1,
        submissions_collector_factory=_StubSubmissions,
        archive_collector_factory=_StubArchive,
        pacer=pacer,
    )
    assert captured["submissions"]["pacer"] is pacer
    assert captured["archive"]["pacer"] is pacer

    # Default path: no injected pacer — the run still builds exactly ONE and
    # hands the same object to both collectors.
    captured.clear()
    acquire_bounded_filings(
        targets=("FXT=1",),
        raw_root=tmp_path / "raw2",
        archive_root=tmp_path / "archive2",
        user_agent=USER_AGENT,
        as_of="2026-08-01T23:59:59Z",
        recorded_at="2026-08-02T00:05:00Z",
        min_interval_seconds=0.1,
        submissions_collector_factory=_StubSubmissions,
        archive_collector_factory=_StubArchive,
    )
    shared = captured["submissions"]["pacer"]
    assert isinstance(shared, SecRequestPacer)
    assert captured["archive"]["pacer"] is shared


class _Response:
    def __init__(self, url: str, body: bytes) -> None:
        self.url = url
        self.status_code = 200
        self.headers = {"Content-Length": str(len(body))}
        self._body = body
        self.closed = False

    def iter_content(self, *, chunk_size: int):
        yield self._body

    def raise_for_status(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class _Session:
    def get(self, url, **_kwargs):
        return _Response(url, b"{}")


class _FactsFetcher:
    def __init__(self) -> None:
        self.last_url: str | None = None

    def __call__(self, url: str, **_kwargs):
        self.last_url = url
        return _Response(url, json.dumps({"cik": 320193, "entityName": "X", "facts": {}}).encode())


class _RecordingPacer:
    """Duck-typed pacer: counts acquires so routing is observable."""

    def __init__(self) -> None:
        self.acquires = 0

    def acquire(self) -> None:
        self.acquires += 1


def test_live_fetchers_routes_both_fetch_paths_through_one_pacer(tmp_path: Path):
    from engine.fundamental_forensics.broad_sec_store import live_fetchers

    pacer = _RecordingPacer()
    fetch_submissions, _historical, fetch_companyfacts, _index = live_fetchers(
        user_agent=USER_AGENT,
        scratch_root=tmp_path / "scratch",
        submissions_session=_Session(),
        companyfacts_fetcher=_FactsFetcher(),
        pacer=pacer,
    )
    assert pacer.acquires == 0  # nothing fired yet

    body, headers = fetch_submissions("0000320193")
    assert json.loads(body) == {}
    assert headers["url"].endswith("/submissions/CIK0000320193.json")
    after_submissions = pacer.acquires
    assert after_submissions >= 1

    facts_body, _facts_headers = fetch_companyfacts("0000320193", 1024 * 1024)
    assert json.loads(facts_body)["facts"] == {}
    assert pacer.acquires > after_submissions  # the SAME pacer served both paths


def test_concurrent_acquires_never_mark_twice_inside_one_interval():
    clock = FakeClock(epsilon=0.001)
    pacer = SecRequestPacer(min_interval_seconds=0.12, sleeper=clock.sleeper, monotonic=clock.monotonic)
    acquires_per_thread = 40
    barrier = threading.Barrier(2)

    def worker() -> None:
        barrier.wait()
        for _ in range(acquires_per_thread):
            pacer.acquire()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Acquires serialize under the pacer lock, so the global monotonic-call
    # log segments cleanly: call #1 is the first mark, and every later acquire
    # contributes exactly [wait-read, mark].  Marks are therefore every other
    # read starting from the first.
    reads = clock.reads
    assert len(reads) == 2 * (2 * acquires_per_thread) - 1
    marks = reads[0::2]
    for earlier, later in zip(marks, marks[1:]):
        assert later - earlier >= 0.12 - 1e-9
    # Every non-first acquire had to wait a positive interval.
    assert len(clock.sleeps) >= 2 * acquires_per_thread - 2


def test_edgar_forensics_re_exports_the_stdlib_pacer() -> None:
    import collectors.edgar_forensics
    import collectors.sec_request_pacer

    assert (
        collectors.edgar_forensics.SecRequestPacer
        is collectors.sec_request_pacer.SecRequestPacer
    )


def test_the_pacer_module_imports_without_heavy_dependencies() -> None:
    code = (
        "import sys\n"
        "for name in ('pandas', 'requests', 'yaml'):\n"
        "    sys.modules[name] = None\n"
        "import collectors.sec_request_pacer\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
