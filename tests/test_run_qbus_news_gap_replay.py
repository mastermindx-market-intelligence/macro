"""Deterministic catch-up replay for the ticker-news runner.

A scripted page source, keyed by ``(start_iso, page_token)``, and an injected
clock drive the real ``AlpacaNewsClient`` and ``NewsIngestRunner`` against a
real ``NewsStore`` on a temporary sqlite file. No socket is opened and no
credential is read from the environment.

Five tests pin overlap exactly-once delivery, a page-budget gap that holds an
existing cursor, a failed catch-up that does not open a hole, backoff treated
as a failed catch-up, and health-file projection through
``load_health_receipt``. A sixth test is a strict xfail: with no stored
cursor, ``catch_up_once`` drops the lookback base, and that hold belongs in
``collectors/benzinga_news.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from collectors import alpaca_news
from engine import qbus_news_receipts as receipts_mod
from engine import qbus_news_store as store_mod
from engine.qbus_news_universe import qualify_universe
from scripts import run_qbus_news


UTC = timezone.utc
T0 = datetime(2026, 10, 11, 14, 0, tzinfo=UTC)
OVERLAP = 3
LOOKBACK = 300
KEY_ID = "test-key-id"
SECRET_KEY = "test-secret"

_TITLES = {
    "A": "NVIDIA unveils a new data-center accelerator",
    "B": "Chile copper miners ratify a wage contract",
    "C": "French wheat crop misses the farm survey",
    "F": "Airline grounds a fleet for a sensor check",
    "G": "Port workers reopen the Oakland terminal",
}
_UPDATED = {
    "A": "2026-10-11T13:40:00Z",
    "B": "2026-10-11T13:41:00Z",
    "C": "2026-10-11T13:42:00Z",
    "F": "2026-10-11T13:50:00Z",
    "G": "2026-10-11T13:55:00Z",
}


def _rfc3339(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch(moment: datetime) -> int:
    return int(moment.timestamp())


def _item(item_id: str) -> dict:
    return {
        "id": item_id,
        "headline": _TITLES[item_id],
        "author": "Desk",
        "created_at": "2026-10-11T13:30:00Z",
        "updated_at": _UPDATED[item_id],
        "summary": f"teaser {item_id}",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "symbols": ["NVDA"],
        "source": "benzinga",
    }


def _page(news, *, next_token=None) -> dict:
    payload = {"news": list(news)}
    if next_token is not None:
        payload["next_page_token"] = next_token
    return payload


class FakeResponse:
    def __init__(self, payload, *, status=200):
        self._payload = payload
        self.status_code = status
        self.headers = {}
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http_{self.status_code}")


class ScriptedHttp:
    """Pages keyed by ``(start_iso, page_token)``. ``page_token`` is None on
    the first page of a window. A programmed failure answers before lookup.
    """

    def __init__(self, pages):
        self.pages = dict(pages)
        self.calls = []
        self._fail_status = None
        self._fail_left = 0

    def fail_next(self, status: int, times: int = 1) -> None:
        self._fail_status = status
        self._fail_left = times

    def __call__(self, url, *, params, headers, timeout):
        start = params.get("start")
        token = params.get("page_token")
        self.calls.append(
            {"start": start, "end": params.get("end"), "page_token": token}
        )
        if self._fail_left:
            self._fail_left -= 1
            return FakeResponse({}, status=self._fail_status)
        key = (start, token)
        try:
            payload = self.pages[key]
        except KeyError:
            known = ", ".join(repr(k) for k in self.pages)
            raise AssertionError(
                f"unscripted page start={start!r} token={token!r}; known={known}"
            ) from None
        return FakeResponse(payload)


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def _universe():
    return qualify_universe(
        {
            "owner": "security_reference.sp500",
            "revision": "sp500-r1",
            "complete": True,
            "truncated": False,
            "effective_at": T0 - timedelta(days=1),
            "known_at": T0 - timedelta(hours=1),
            "fresh_until": T0 + timedelta(days=2),
            "securities": [
                {
                    "security_id": "sec-NVDA",
                    "ticker": "NVDA",
                    "aliases": ["NVDA"],
                    "valid_from": T0 - timedelta(days=100),
                    "valid_to": None,
                    "known_at": T0 - timedelta(days=100),
                }
            ],
        },
        asof=T0,
    )


def _no_socket(*_args, **_kwargs):
    raise AssertionError("catch-up replay must not open a socket")


def _client(http: ScriptedHttp, clock: Clock, *, max_pages: int) -> alpaca_news.AlpacaNewsClient:
    return alpaca_news.AlpacaNewsClient(
        key_id=KEY_ID,
        secret_key=SECRET_KEY,
        http_get=http,
        page_size=50,
        max_pages=max_pages,
        overlap_seconds=OVERLAP,
        initial_lookback_seconds=LOOKBACK,
        clock=clock,
    )


def _runner(store, client, clock: Clock, health_path: Path):
    return run_qbus_news.NewsIngestRunner(
        token="test-token",
        store=store,
        universe_provider=_universe,
        direct_client=client,
        connect=_no_socket,
        clock=clock,
        monotonic=lambda: 0.0,
        wait=lambda _seconds: None,
        health_path=health_path,
        provider="alpaca",
        stream_target=alpaca_news.STREAM_URL,
        frame_normalizer=alpaca_news.normalize_stream_frames,
    )


def _capture_commits(store):
    receipts = []
    original = store.commit

    def commit(*args, **kwargs):
        receipt = original(*args, **kwargs)
        receipts.append(receipt)
        return receipt

    store.commit = commit
    return receipts


def _state_ids(store) -> tuple[str, ...]:
    rows = store._conn.execute(
        "SELECT source_item_id FROM news_states ORDER BY source_item_id"
    ).fetchall()
    return tuple(str(row["source_item_id"]) for row in rows)


def _change_rows(store) -> tuple[tuple[str, str], ...]:
    page = store.changes(
        after_sequence=0,
        limit=20,
        rights=store_mod.NewsReadRights.all_internal(),
    )
    assert page.has_more is False
    return tuple((row.kind, row.source_item_id) for row in page.rows)


@dataclass(frozen=True)
class HealthSnap:
    label: str
    path: Path
    now: datetime
    state: str
    reason: str
    gap: bool


def _snap(health_path: Path, dest: Path, *, label: str, now: datetime, state: str, reason: str, gap: bool) -> HealthSnap:
    dest.write_bytes(health_path.read_bytes())
    return HealthSnap(label, dest, now, state, reason, gap)


def _raw(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class OverlapReplay:
    health: list[HealthSnap]
    state_ids: tuple[str, ...]
    changes: tuple[tuple[str, str], ...]
    revision_count: int
    first_duplicate: int
    second_duplicate: int
    second_inserted: int
    second_applied: int
    second_start: str
    expected_second_start: str
    cursor: str | None


def _replay_overlap(tmp: Path) -> OverlapReplay:
    """Catch-up #1 commits A,B from a seeded cursor. Catch-up #2's query
    starts at that committed cursor minus the overlap and the source
    re-delivers B with new C.
    """
    tmp.mkdir(parents=True, exist_ok=True)
    clock = Clock(T0)
    base = _epoch(T0)
    first_at = T0 + timedelta(seconds=60)
    second_at = T0 + timedelta(seconds=120)
    start_1 = _rfc3339(base - OVERLAP)
    start_2 = _rfc3339(_epoch(first_at) - OVERLAP)
    http = ScriptedHttp(
        {
            (start_1, None): _page([_item("A"), _item("B")]),
            (start_2, None): _page([_item("B"), _item("C")]),
        }
    )
    client = _client(http, clock, max_pages=5)
    health_path = tmp / "health.json"
    with store_mod.NewsStore(tmp / "q.sqlite3", source_key="alpaca-rest") as store:
        store.commit((), expected_cursor=None, next_cursor=str(base))
        receipts = _capture_commits(store)
        runner = _runner(store, client, clock, health_path)

        clock.now = first_at
        runner._catch_up()
        snap_1 = _snap(
            health_path,
            tmp / "health-1.json",
            label="overlap-commit",
            now=clock.now,
            state="live",
            reason="fresh",
            gap=False,
        )
        assert store.current_cursor() == str(_epoch(first_at))

        clock.now = second_at
        runner._catch_up()
        snap_2 = _snap(
            health_path,
            tmp / "health-2.json",
            label="overlap-redelivery",
            now=clock.now,
            state="live",
            reason="fresh",
            gap=False,
        )
        return OverlapReplay(
            health=[snap_1, snap_2],
            state_ids=_state_ids(store),
            changes=_change_rows(store),
            revision_count=store.counts()["revisions"],
            first_duplicate=receipts[0].duplicate_revisions,
            second_duplicate=receipts[1].duplicate_revisions,
            second_inserted=receipts[1].inserted_revisions,
            second_applied=receipts[1].applied_states,
            second_start=http.calls[-1]["start"],
            expected_second_start=start_2,
            cursor=store.current_cursor(),
        )


def test_overlap_redelivery_is_exactly_once(tmp_path):
    result = _replay_overlap(tmp_path)

    assert result.state_ids == ("A", "B", "C")
    assert result.revision_count == 3
    assert result.changes == (
        ("upsert", "A"),
        ("upsert", "B"),
        ("upsert", "C"),
    )
    assert result.first_duplicate == 0
    assert result.second_duplicate == 1
    assert result.second_inserted == 1
    assert result.second_applied == 1
    assert result.second_start == result.expected_second_start
    assert result.cursor == str(_epoch(T0 + timedelta(seconds=120)))


@dataclass
class GapReplay:
    health: list[HealthSnap]
    base: str
    cursor_after_gap: str | None
    cursor_after_recovery: str | None
    ids_after_gap: tuple[str, ...]
    ids_after_recovery: tuple[str, ...]
    changes: tuple[tuple[str, str], ...]
    gap_starts: tuple[str, ...]
    recovery_starts: tuple[str, ...]
    gap_tokens: tuple[str | None, ...]
    recovery_tokens: tuple[str | None, ...]
    gap_raw: dict
    recovery_raw: dict
    catchups_gap: int
    catchups_ok: int
    catchups_failed: int
    gap_flag_after_recovery: bool
    recovery_duplicate: int
    recovery_applied: int
    receipts_after_gap: int


def _replay_gap(tmp: Path) -> GapReplay:
    tmp.mkdir(parents=True, exist_ok=True)
    clock = Clock(T0)
    base_epoch = _epoch(T0)
    held_start = _rfc3339(base_epoch - OVERLAP)
    http = ScriptedHttp(
        {
            (held_start, None): _page([_item("A")], next_token="page-2"),
            (held_start, "page-2"): _page([_item("B")], next_token="page-3"),
            (held_start, "page-3"): _page([_item("C")]),
        }
    )
    client = _client(http, clock, max_pages=2)
    health_path = tmp / "health.json"
    with store_mod.NewsStore(tmp / "q.sqlite3", source_key="alpaca-rest") as store:
        store.commit((), expected_cursor=None, next_cursor=str(base_epoch))
        receipts = _capture_commits(store)
        runner = _runner(store, client, clock, health_path)

        clock.advance(45)
        runner._catch_up()
        snap_gap = _snap(
            health_path,
            tmp / "health-gap.json",
            label="page-budget-gap",
            now=clock.now,
            state="degraded",
            reason="gap_unresolved",
            gap=True,
        )
        cursor_after_gap = store.current_cursor()
        ids_after_gap = _state_ids(store)
        receipts_after_gap = len(receipts)
        gap_calls = list(http.calls)

        client.max_pages = 5
        clock.advance(40)
        runner._catch_up()
        snap_live = _snap(
            health_path,
            tmp / "health-live.json",
            label="gap-recovery",
            now=clock.now,
            state="live",
            reason="fresh",
            gap=False,
        )
        recovery_calls = http.calls[len(gap_calls) :]
        return GapReplay(
            health=[snap_gap, snap_live],
            base=str(base_epoch),
            cursor_after_gap=cursor_after_gap,
            cursor_after_recovery=store.current_cursor(),
            ids_after_gap=ids_after_gap,
            ids_after_recovery=_state_ids(store),
            changes=_change_rows(store),
            gap_starts=tuple(call["start"] for call in gap_calls),
            recovery_starts=tuple(call["start"] for call in recovery_calls),
            gap_tokens=tuple(call["page_token"] for call in gap_calls),
            recovery_tokens=tuple(call["page_token"] for call in recovery_calls),
            gap_raw=_raw(snap_gap.path),
            recovery_raw=_raw(snap_live.path),
            catchups_gap=runner.stats.catchups_gap,
            catchups_ok=runner.stats.catchups_ok,
            catchups_failed=runner.stats.catchups_failed,
            gap_flag_after_recovery=runner._gap_unresolved,
            recovery_duplicate=receipts[-1].duplicate_revisions,
            recovery_applied=receipts[-1].applied_states,
            receipts_after_gap=receipts_after_gap,
        )


def test_page_budget_gap_holds_cursor_until_later_catchup(tmp_path):
    result = _replay_gap(tmp_path)
    held_start = _rfc3339(int(result.base) - OVERLAP)

    assert result.receipts_after_gap == 0
    assert result.ids_after_gap == ()
    assert result.cursor_after_gap == result.base
    assert result.cursor_after_gap != str(_epoch(T0 + timedelta(seconds=45)))
    assert result.gap_tokens == (None, "page-2")
    assert result.gap_starts == (held_start, held_start)
    assert result.gap_raw["state"] == "degraded"
    assert result.gap_raw["gap_unresolved"] is True
    assert result.catchups_gap == 1
    assert result.catchups_failed == 0

    assert result.recovery_starts == (held_start, held_start, held_start)
    assert result.recovery_tokens == (None, "page-2", "page-3")
    assert result.ids_after_recovery == ("A", "B", "C")
    assert result.changes == (
        ("upsert", "A"),
        ("upsert", "B"),
        ("upsert", "C"),
    )
    assert result.recovery_applied == 3
    assert result.recovery_duplicate == 0
    assert result.cursor_after_recovery == str(_epoch(T0 + timedelta(seconds=85)))
    assert result.recovery_raw["state"] == "live"
    assert result.recovery_raw["gap_unresolved"] is False
    assert result.gap_flag_after_recovery is False
    assert result.catchups_ok == 1


@pytest.mark.xfail(strict=True, reason="GAP: collectors/benzinga_news.py")
def test_null_cursor_gap_keeps_lookback_base_across_a_later_catchup(tmp_path):
    """A first catch-up with no stored cursor must keep the lookback base.

    ``catch_up_once`` returns on ``gap_unresolved`` without writing
    ``next_cursor_epoch``. The next catch-up then recomputes base from the
    new observed time, so items in the original window (including page 3,
    which the budget never fetched) are no longer requested. The hold
    belongs in ``collectors/benzinga_news.py``; this lane must not edit it.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    clock = Clock(T0)
    base = max(0, _epoch(T0) - LOOKBACK)
    held_start = _rfc3339(base - OVERLAP)
    http = ScriptedHttp(
        {
            (held_start, None): _page([_item("A")], next_token="page-2"),
            (held_start, "page-2"): _page([_item("B")], next_token="page-3"),
            (held_start, "page-3"): _page([_item("C")]),
        }
    )
    client = _client(http, clock, max_pages=2)
    health_path = tmp_path / "health.json"
    with store_mod.NewsStore(tmp_path / "q.sqlite3", source_key="alpaca-rest") as store:
        runner = _runner(store, client, clock, health_path)
        runner._catch_up()
        raw = _raw(health_path)
        assert raw["state"] == "degraded"
        assert raw["gap_unresolved"] is True
        assert _state_ids(store) == ()
        # Desired hold: the cursor is the lookback base, not the observed time.
        assert store.current_cursor() == str(base)

        client.max_pages = 5
        clock.advance(LOOKBACK + 50)
        runner._catch_up()
        assert {call["start"] for call in http.calls} == {held_start}
        assert _state_ids(store) == ("A", "B", "C")
        assert store.current_cursor() == str(_epoch(clock.now))


@dataclass
class FailureReplay:
    health: list[HealthSnap]
    cursor_after_first_failure: str | None
    cursor_after_first_success: str | None
    cursor_after_second_failure: str | None
    cursor_after_recovery: str | None
    ids_after_second_failure: tuple[str, ...]
    ids_after_recovery: tuple[str, ...]
    changes: tuple[tuple[str, str], ...]
    failed_window_start: str
    recovery_start: str
    catchups_failed: int
    catchups_ok: int
    first_failure_raw: dict
    second_failure_raw: dict
    recovery_raw: dict


def _replay_failure(tmp: Path) -> FailureReplay:
    tmp.mkdir(parents=True, exist_ok=True)
    clock = Clock(T0)
    first_success_at = T0 + timedelta(seconds=10)
    # Inside the 120s catch-up freshness window so a failure still projects
    # as runtime_degraded rather than a stale catch-up.
    second_failure_at = first_success_at + timedelta(seconds=30)
    # Far past the initial lookback. Recovery must still start from the
    # cursor held across the failed attempt, or item G is never requested.
    recovery_at = second_failure_at + timedelta(seconds=1000)
    success_start = _rfc3339(
        max(0, _epoch(first_success_at) - LOOKBACK) - OVERLAP
    )
    held_start = _rfc3339(_epoch(first_success_at) - OVERLAP)
    http = ScriptedHttp(
        {
            (success_start, None): _page([_item("F")]),
            (held_start, None): _page([_item("G")]),
        }
    )
    client = _client(http, clock, max_pages=5)
    health_path = tmp / "health.json"
    with store_mod.NewsStore(tmp / "q.sqlite3", source_key="alpaca-rest") as store:
        runner = _runner(store, client, clock, health_path)

        http.fail_next(401)
        runner._catch_up()
        snap_first = _snap(
            health_path,
            tmp / "health-first-failure.json",
            label="failure-no-prior-success",
            now=clock.now,
            state="catching_up",
            reason="catchup_pending",
            gap=False,
        )
        cursor_after_first_failure = store.current_cursor()

        clock.now = first_success_at
        runner._catch_up()
        snap_success = _snap(
            health_path,
            tmp / "health-first-success.json",
            label="failure-recovery-no-prior",
            now=clock.now,
            state="live",
            reason="fresh",
            gap=False,
        )
        cursor_after_first_success = store.current_cursor()

        clock.now = second_failure_at
        http.fail_next(401)
        runner._catch_up()
        snap_second = _snap(
            health_path,
            tmp / "health-second-failure.json",
            label="failure-after-success",
            now=clock.now,
            state="degraded",
            reason="runtime_degraded",
            gap=False,
        )
        cursor_after_second_failure = store.current_cursor()
        ids_after_second_failure = _state_ids(store)

        clock.now = recovery_at
        calls_before_recovery = len(http.calls)
        runner._catch_up()
        snap_recovery = _snap(
            health_path,
            tmp / "health-second-recovery.json",
            label="failure-window-recovered",
            now=clock.now,
            state="live",
            reason="fresh",
            gap=False,
        )
        recovery_call = http.calls[calls_before_recovery]
        return FailureReplay(
            health=[snap_first, snap_success, snap_second, snap_recovery],
            cursor_after_first_failure=cursor_after_first_failure,
            cursor_after_first_success=cursor_after_first_success,
            cursor_after_second_failure=cursor_after_second_failure,
            cursor_after_recovery=store.current_cursor(),
            ids_after_second_failure=ids_after_second_failure,
            ids_after_recovery=_state_ids(store),
            changes=_change_rows(store),
            failed_window_start=held_start,
            recovery_start=recovery_call["start"],
            catchups_failed=runner.stats.catchups_failed,
            catchups_ok=runner.stats.catchups_ok,
            first_failure_raw=_raw(snap_first.path),
            second_failure_raw=_raw(snap_second.path),
            recovery_raw=_raw(snap_recovery.path),
        )


def test_failed_catchup_holds_cursor_and_recovery_leaves_no_hole(tmp_path):
    result = _replay_failure(tmp_path)

    assert result.cursor_after_first_failure is None
    assert result.cursor_after_first_success == str(_epoch(T0 + timedelta(seconds=10)))
    assert result.cursor_after_second_failure == result.cursor_after_first_success
    assert result.ids_after_second_failure == ("F",)
    assert result.recovery_start == result.failed_window_start
    assert result.ids_after_recovery == ("F", "G")
    assert result.changes == (("upsert", "F"), ("upsert", "G"))
    assert result.cursor_after_recovery == str(
        _epoch(T0 + timedelta(seconds=10 + 30 + 1000))
    )
    assert result.catchups_failed == 2
    assert result.catchups_ok == 2
    assert result.first_failure_raw["state"] == "catching_up"
    assert result.first_failure_raw["last_catchup_error"] == "http_401"
    assert result.first_failure_raw["last_successful_catchup"] is None
    assert result.second_failure_raw["state"] == "degraded"
    assert result.second_failure_raw["last_catchup_error"] == "http_401"
    assert result.second_failure_raw["gap_unresolved"] is False
    assert result.recovery_raw["state"] == "live"
    assert result.recovery_raw["last_catchup_error"] is None
    assert result.recovery_raw["gap_unresolved"] is False


@dataclass
class BackoffReplay:
    health: list[HealthSnap]
    cursor_before: str | None
    cursor_after: str | None
    failed_before: int
    failed_after: int
    calls_before: int
    calls_after: int
    error: str | None
    raw: dict
    catchups_ok: int
    cursor_after_success: str | None
    receipt_count: int


def _replay_backoff(tmp: Path) -> BackoffReplay:
    tmp.mkdir(parents=True, exist_ok=True)
    clock = Clock(T0)
    start = _rfc3339(max(0, _epoch(T0) - LOOKBACK) - OVERLAP)
    http = ScriptedHttp({(start, None): _page([])})
    client = _client(http, clock, max_pages=5)
    health_path = tmp / "health.json"
    with store_mod.NewsStore(tmp / "q.sqlite3", source_key="alpaca-rest") as store:
        receipts = _capture_commits(store)
        runner = _runner(store, client, clock, health_path)

        runner._catch_up()
        snap_live = _snap(
            health_path,
            tmp / "health-live.json",
            label="backoff-prior-success",
            now=clock.now,
            state="live",
            reason="fresh",
            gap=False,
        )
        cursor_after_success = store.current_cursor()

        http.fail_next(429)
        runner._catch_up()
        snap_429 = _snap(
            health_path,
            tmp / "health-429.json",
            label="backoff-armed-by-429",
            now=clock.now,
            state="degraded",
            reason="runtime_degraded",
            gap=False,
        )
        failed_before = runner.stats.catchups_failed
        calls_before = len(http.calls)
        cursor_before = store.current_cursor()

        runner._catch_up()
        snap_backoff = _snap(
            health_path,
            tmp / "health-backoff.json",
            label="backoff-active",
            now=clock.now,
            state="degraded",
            reason="runtime_degraded",
            gap=False,
        )
        return BackoffReplay(
            health=[snap_live, snap_429, snap_backoff],
            cursor_before=cursor_before,
            cursor_after=store.current_cursor(),
            failed_before=failed_before,
            failed_after=runner.stats.catchups_failed,
            calls_before=calls_before,
            calls_after=len(http.calls),
            error=runner._last_catchup_error,
            raw=_raw(snap_backoff.path),
            catchups_ok=runner.stats.catchups_ok,
            cursor_after_success=cursor_after_success,
            receipt_count=len(receipts),
        )


def test_backoff_active_is_a_failed_catchup(tmp_path):
    result = _replay_backoff(tmp_path)

    assert result.cursor_after_success == str(_epoch(T0))
    assert result.cursor_before == result.cursor_after_success
    assert result.cursor_after == result.cursor_before
    assert result.failed_after == result.failed_before + 1
    assert result.failed_after == 2
    assert result.calls_after == result.calls_before
    assert result.error == "backoff_active"
    assert result.catchups_ok == 1
    assert result.receipt_count == 1
    assert result.raw["state"] == "degraded"
    assert result.raw["gap_unresolved"] is False
    assert result.raw["last_catchup_error"] == "backoff_active"


def test_health_files_round_trip_through_load_health_receipt(tmp_path):
    snaps: list[HealthSnap] = []
    snaps += _replay_overlap(tmp_path / "overlap").health
    snaps += _replay_gap(tmp_path / "gap").health
    snaps += _replay_failure(tmp_path / "failure").health
    snaps += _replay_backoff(tmp_path / "backoff").health

    assert [snap.label for snap in snaps] == [
        "overlap-commit",
        "overlap-redelivery",
        "page-budget-gap",
        "gap-recovery",
        "failure-no-prior-success",
        "failure-recovery-no-prior",
        "failure-after-success",
        "failure-window-recovered",
        "backoff-prior-success",
        "backoff-armed-by-429",
        "backoff-active",
    ]
    for snap in snaps:
        text = snap.path.read_text(encoding="utf-8")
        assert "test-secret" not in text
        assert "test-token" not in text
        assert KEY_ID not in text
        parsed = receipts_mod.load_health_receipt(snap.path, now=snap.now)
        assert parsed["state"] == snap.state, snap.label
        assert parsed["reason"] == snap.reason, snap.label
        assert parsed["gap_unresolved"] is snap.gap, snap.label
