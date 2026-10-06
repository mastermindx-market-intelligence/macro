"""Foreground single-writer service for qbus live news.

Source-only capability: no service is installed or started by this module. The
runner serializes REST catch-up and WebSocket observation commits through one
NewsStore connection. Catch-up runs before every connect/reconnect and
periodically during a healthy socket so a long-lived connection cannot hide a
REST/removal gap.

Production activation, credentials, source rights, host placement and supervision
remain separate owner gates.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from typing import Callable
from urllib.parse import urlencode

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collectors import benzinga_news
from engine.qbus_news_receipts import (
    HEALTH_SCHEMA,
    NewsReceiptError,
    load_rights_receipt,
    write_health_receipt,
)
from engine.qbus_news_store import NewsStore
from engine.qbus_news_universe import UniverseQualification, qualify_universe

STREAM_LOG_LABEL = "wss://api.benzinga.com/api/v1/news/stream?token=REDACTED"
StopFlag = threading.Event


@dataclass(slots=True)
class RunnerStats:
    connect_attempts: int = 0
    disconnects: int = 0
    stream_events: int = 0
    stream_ignored: int = 0
    stream_errors: int = 0
    catchups_ok: int = 0
    catchups_gap: int = 0
    catchups_failed: int = 0
    health_write_failures: int = 0


def exit_receipt(stats: RunnerStats) -> dict:
    return {"schema": "qbus.news_runner_exit.v1", **asdict(stats)}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stream_url(token: str) -> str:
    if not isinstance(token, str) or not token:
        raise ValueError("qbus_news:missing_stream_token")
    return f"{benzinga_news.STREAM_URL}?{urlencode({'token': token})}"


def _default_connect(url: str, **kwargs):
    from websockets.sync.client import connect  # lazy: CI can test without package
    return connect(url, **kwargs)


def _frame_size(raw: object) -> int:
    if isinstance(raw, str):
        return len(raw.encode("utf-8"))
    if isinstance(raw, (bytes, bytearray)):
        return len(raw)
    return 0


class NewsIngestRunner:
    """One serialized upstream writer. Browser clients never instantiate this."""

    def __init__(
        self,
        *,
        token: str,
        store: NewsStore,
        universe_provider: Callable[[], UniverseQualification],
        direct_client: benzinga_news.BenzingaNewsClient,
        connect: Callable[..., object] = _default_connect,
        clock: Callable[[], datetime] = _utc_now,
        monotonic: Callable[[], float] = time.monotonic,
        wait: Callable[[float], None] = time.sleep,
        stop: StopFlag | None = None,
        catchup_interval_seconds: float = 30.0,
        recv_timeout_seconds: float = 1.0,
        reconnect_base_seconds: float = 1.0,
        reconnect_max_seconds: float = 60.0,
        max_frame_bytes: int = 2 * 1024 * 1024,
        health_path: Path | None = None,
        admission_guard: Callable[[], bool] | None = None,
    ) -> None:
        if not token:
            raise ValueError("qbus_news:missing_stream_token")
        if catchup_interval_seconds <= 0 or recv_timeout_seconds <= 0:
            raise ValueError("qbus_news:invalid_interval")
        if reconnect_base_seconds <= 0 or reconnect_max_seconds < reconnect_base_seconds:
            raise ValueError("qbus_news:invalid_backoff")
        if not isinstance(max_frame_bytes, int) or max_frame_bytes < 1024:
            raise ValueError("qbus_news:invalid_frame_budget")
        self.token = token
        self.store = store
        self.universe_provider = universe_provider
        self.direct_client = direct_client
        self.connect = connect
        self.clock = clock
        self.monotonic = monotonic
        self.wait = wait
        self.stop = stop or StopFlag()
        self.catchup_interval_seconds = float(catchup_interval_seconds)
        self.recv_timeout_seconds = float(recv_timeout_seconds)
        self.reconnect_base_seconds = float(reconnect_base_seconds)
        self.reconnect_max_seconds = float(reconnect_max_seconds)
        self.max_frame_bytes = max_frame_bytes
        self.health_path = health_path
        self.admission_guard = admission_guard
        self.stats = RunnerStats()
        self._last_successful_catchup: datetime | None = None
        self._last_stream_event_at: datetime | None = None
        self._gap_unresolved = False

    def _health_payload(self, state: str) -> dict:
        observed = self.clock()
        return {
            "schema": HEALTH_SCHEMA,
            "source": "benzinga",
            "state": state,
            "observed_at": observed.isoformat(),
            "last_successful_catchup": (
                None
                if self._last_successful_catchup is None
                else self._last_successful_catchup.isoformat()
            ),
            "last_stream_event_at": (
                None
                if self._last_stream_event_at is None
                else self._last_stream_event_at.isoformat()
            ),
            "gap_unresolved": self._gap_unresolved,
            "connect_attempts": self.stats.connect_attempts,
            "disconnects": self.stats.disconnects,
            "catchups_failed": self.stats.catchups_failed,
        }

    def _publish_health(self, state: str) -> None:
        if self.health_path is None:
            return
        try:
            write_health_receipt(self.health_path, self._health_payload(state))
        except (OSError, NewsReceiptError):
            # Health publication is evidence, not ingestion authority. A missing
            # or stale health file makes the API fail closed on its own.
            self.stats.health_write_failures += 1

    def _admitted(self) -> bool:
        if self.admission_guard is None:
            return True
        try:
            return bool(self.admission_guard())
        except Exception:
            return False

    def _catch_up(self) -> None:
        observed_at = self.clock()
        try:
            result = benzinga_news.catch_up_once(
                client=self.direct_client,
                store=self.store,
                universe=self.universe_provider(),
                observed_at=observed_at,
            )
        except Exception:  # source/service loop records class, never raw secret text
            self.stats.catchups_failed += 1
            state = "degraded" if self._last_successful_catchup else "catching_up"
            self._publish_health(state)
            return
        if result.gap_unresolved:
            self.stats.catchups_gap += 1
            self._gap_unresolved = True
            self._publish_health("degraded")
        elif result.committed:
            self.stats.catchups_ok += 1
            self._last_successful_catchup = observed_at
            self._gap_unresolved = False
            self._publish_health("live")

    def _handle_frame(self, raw: object) -> None:
        size = _frame_size(raw)
        if size == 0 or size > self.max_frame_bytes:
            self.stats.stream_errors += 1
            return
        try:
            revision = benzinga_news.normalize_stream_frame(
                raw,
                received_at=self.clock(),
            )
            if revision is None:
                self.stats.stream_ignored += 1
                return
            routed = benzinga_news.route_revision(
                revision,
                self.universe_provider(),
            )
            self.store.commit_observations([routed])
            self.stats.stream_events += 1
            self._last_stream_event_at = self.clock()
            if self._gap_unresolved:
                state = "degraded"
            elif self._last_successful_catchup is None:
                state = "catching_up"
            else:
                state = "live"
            self._publish_health(state)
        except Exception:
            self.stats.stream_errors += 1

    def run(self, *, max_connections: int | None = None) -> RunnerStats:
        """Run until stop or optional test-only connection bound is reached."""
        if max_connections is not None and max_connections < 0:
            raise ValueError("qbus_news:invalid_connection_bound")
        backoff = self.reconnect_base_seconds
        self._publish_health("catching_up")

        try:
            while not self.stop.is_set():
                if not self._admitted():
                    self.stop.set()
                    break
                if (
                    max_connections is not None
                    and self.stats.connect_attempts >= max_connections
                ):
                    break

                self._catch_up()
                if self.stop.is_set():
                    break

                self.stats.connect_attempts += 1
                try:
                    with self.connect(
                        stream_url(self.token),
                        open_timeout=20,
                        close_timeout=5,
                        max_size=self.max_frame_bytes,
                    ) as ws:
                        backoff = self.reconnect_base_seconds
                        next_catchup = (
                            self.monotonic() + self.catchup_interval_seconds
                        )
                        while not self.stop.is_set():
                            if not self._admitted():
                                self.stop.set()
                                break
                            if self.monotonic() >= next_catchup:
                                self._catch_up()
                                next_catchup = (
                                    self.monotonic()
                                    + self.catchup_interval_seconds
                                )
                            try:
                                raw = ws.recv(timeout=self.recv_timeout_seconds)
                            except TimeoutError:
                                continue
                            if not self._admitted():
                                self.stop.set()
                                break
                            self._handle_frame(raw)
                except Exception:
                    self.stats.disconnects += 1
                    state = (
                        "degraded"
                        if self._last_successful_catchup is not None
                        else "catching_up"
                    )
                    self._publish_health(state)

                if self.stop.is_set():
                    break
                if (
                    max_connections is not None
                    and self.stats.connect_attempts >= max_connections
                ):
                    break
                self.wait(backoff)
                backoff = min(backoff * 2.0, self.reconnect_max_seconds)
        finally:
            self._publish_health("unavailable")

        return self.stats


def load_universe_snapshot(path: Path, *, asof: datetime) -> UniverseQualification:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("qbus_news:universe_snapshot_unreadable") from exc
    if not isinstance(raw, dict):
        raise RuntimeError("qbus_news:universe_snapshot_invalid")
    qualified = qualify_universe(raw, asof=asof)
    if qualified.status != "qualified":
        raise RuntimeError("qbus_news:universe_not_qualified")
    return qualified


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the disabled-by-default qbus news source service.")
    p.add_argument("--database", type=Path, default=Path("data/qbus/qbus.sqlite3"))
    p.add_argument(
        "--universe-snapshot",
        type=Path,
        default=Path("data/qbus/news_universe.json"),
    )
    p.add_argument("--rights-receipt", type=Path)
    p.add_argument("--health-path", type=Path)
    p.add_argument("--token-env", default="BENZINGA_API_KEY")
    p.add_argument("--run", action="store_true", help="explicitly enter the live service loop")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get(args.token_env, "")
    rights_path = args.rights_receipt
    if rights_path is None:
        env_rights = os.environ.get("MM_TICKER_NEWS_RIGHTS", "").strip()
        rights_path = Path(env_rights) if env_rights else None
    health_path = args.health_path
    if health_path is None:
        env_health = os.environ.get("MM_TICKER_NEWS_HEALTH", "").strip()
        health_path = Path(env_health) if env_health else None

    report = {
        "schema": "qbus.news_runner_preflight.v1",
        "run_requested": bool(args.run),
        "token_present": bool(token),
        "universe_present": bool(
            args.universe_snapshot and args.universe_snapshot.is_file()
        ),
        "rights_receipt_present": bool(rights_path and rights_path.is_file()),
        "health_path_present": health_path is not None,
        "database": str(args.database),
        "stream": STREAM_LOG_LABEL,
    }
    if not args.run:
        print(json.dumps(report, sort_keys=True))
        return 0
    if (
        not token
        or args.universe_snapshot is None
        or rights_path is None
        or health_path is None
    ):
        print(
            json.dumps(
                {**report, "error": "activation_prerequisite_missing"},
                sort_keys=True,
            )
        )
        return 2

    now = _utc_now()
    if load_rights_receipt(
        rights_path,
        now=now,
        audience="site_full",
    ) is None:
        print(
            json.dumps(
                {**report, "error": "activation_rights_unqualified"},
                sort_keys=True,
            )
        )
        return 2

    def rights_admitted() -> bool:
        return load_rights_receipt(
            rights_path,
            now=_utc_now(),
            audience="site_full",
        ) is not None

    stop = StopFlag()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_args: stop.set())

    universe = load_universe_snapshot(args.universe_snapshot, asof=now)
    client = benzinga_news.BenzingaNewsClient(token=token)
    with NewsStore(args.database, source_key="benzinga-rest") as store:
        runner = NewsIngestRunner(
            token=token,
            store=store,
            universe_provider=lambda: universe,
            direct_client=client,
            stop=stop,
            health_path=health_path,
            admission_guard=rights_admitted,
        )
        stats = runner.run()
    print(json.dumps(exit_receipt(stats), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())