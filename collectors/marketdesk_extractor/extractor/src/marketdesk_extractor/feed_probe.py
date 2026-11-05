"""Bounded, read-only state probe for the Research Vault feed watcher."""
from __future__ import annotations

import argparse
import signal
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

from .config import Config
from . import db as db_mod


class FeedProbeError(RuntimeError):
    """The watcher could not safely read the configured MarketDesk database."""


class FeedProbeTimeout(FeedProbeError):
    """The database probe exceeded its hard wall-clock deadline."""


@dataclass(frozen=True)
class VaultState:
    database: Path
    newest: str
    count: int
    producer_auth_state: str
    producer_auth_observed_at: str
    producer_auth_required_at: str
    producer_auth_reason: str


def _run_command(
    command: Sequence[str], *, timeout_seconds: float
) -> subprocess.CompletedProcess[str]:
    """Run the actual DB opener out-of-process so it can be killed reliably."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    try:
        return subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise FeedProbeTimeout(
            f"database probe exceeded {timeout_seconds:g}s hard deadline"
        ) from exc


@contextmanager
def _hard_deadline(seconds: float):
    if seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    previous_handler = signal.getsignal(signal.SIGALRM)

    def expire(_signum, _frame):
        raise FeedProbeTimeout(
            f"database probe exceeded {seconds:g}s hard deadline"
        )

    signal.signal(signal.SIGALRM, expire)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer != (0.0, 0.0):
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


def _readonly_uri(database: Path) -> str:
    return f"file:{quote(str(database), safe='/')}?mode=ro"


def read_vault_state(
    database: Path | str,
    watermark: str,
    *,
    timeout_seconds: float = 10,
) -> VaultState:
    database = Path(database)
    with _hard_deadline(timeout_seconds):
        if not database.is_file():
            raise FeedProbeError(f"configured database is missing: {database}")
        conn = sqlite3.connect(
            _readonly_uri(database),
            uri=True,
            timeout=min(float(timeout_seconds), 5.0),
        )
        try:
            conn.execute("PRAGMA query_only=ON")
            conn.execute(f"PRAGMA busy_timeout={max(1, int(timeout_seconds * 1000))}")
            row = conn.execute(
                """SELECT COALESCE(MAX(vaulted_at), ''),
                          COALESCE(SUM(CASE WHEN vaulted_at > ? THEN 1 ELSE 0 END), 0)
                     FROM papers
                    WHERE vaulted_at IS NOT NULL""",
                (watermark,),
            ).fetchone()
            try:
                meta_rows = conn.execute(
                    "SELECT key, value FROM meta WHERE key IN (?,?,?,?)",
                    (
                        db_mod.PRODUCER_AUTH_STATE_KEY,
                        db_mod.PRODUCER_AUTH_OBSERVED_AT_KEY,
                        db_mod.PRODUCER_AUTH_REQUIRED_AT_KEY,
                        db_mod.PRODUCER_AUTH_REASON_KEY,
                    ),
                ).fetchall()
            except sqlite3.OperationalError:
                meta_rows = []
        finally:
            conn.close()
    meta = {str(item[0]): str(item[1] or "") for item in meta_rows}
    auth_state = meta.get(db_mod.PRODUCER_AUTH_STATE_KEY, db_mod.AUTH_UNKNOWN)
    if auth_state not in db_mod.PRODUCER_AUTH_STATES:
        auth_state = db_mod.AUTH_UNKNOWN
    return VaultState(
        database=database,
        newest=str(row[0]),
        count=int(row[1]),
        producer_auth_state=auth_state,
        producer_auth_observed_at=meta.get(db_mod.PRODUCER_AUTH_OBSERVED_AT_KEY, ""),
        producer_auth_required_at=meta.get(db_mod.PRODUCER_AUTH_REQUIRED_AT_KEY, ""),
        producer_auth_reason=meta.get(db_mod.PRODUCER_AUTH_REASON_KEY, ""),
    )


def _field(value: str) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ").replace("\r", " ")


def _render(state: VaultState) -> str:
    return "|".join(
        (
            _field(str(state.database)),
            _field(state.newest),
            str(state.count),
            _field(state.producer_auth_state),
            _field(state.producer_auth_observed_at),
            _field(state.producer_auth_required_at),
            _field(state.producer_auth_reason),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("watermark")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--database", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        if args.worker:
            if not args.database:
                raise FeedProbeError("worker database path is required")
            state = read_vault_state(
                args.database,
                args.watermark,
                timeout_seconds=args.timeout,
            )
            print(_render(state))
            return 0

        cfg = Config.from_env()
        result = _run_command(
            [
                sys.executable,
                "-m",
                "marketdesk_extractor.feed_probe",
                args.watermark,
                "--timeout",
                str(args.timeout),
                "--worker",
                "--database",
                str(cfg.database_url),
            ],
            timeout_seconds=args.timeout,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or f"worker exited {result.returncode}"
            raise FeedProbeError(detail)
        output = result.stdout.strip()
        fields = output.split("|")
        if len(fields) != 7 or not fields[2].isdigit():
            raise FeedProbeError("worker returned malformed state")
        if fields[3] not in db_mod.PRODUCER_AUTH_STATES:
            raise FeedProbeError("worker returned unsupported producer auth state")
        print(output)
        return 0
    except (FeedProbeError, sqlite3.Error, OSError, ValueError) as exc:
        parser.exit(2, f"feed probe failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
