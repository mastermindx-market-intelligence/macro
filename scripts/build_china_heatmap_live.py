#!/usr/bin/env python3
"""Publish the display-only live China A-share heatmap overlay."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import signal
import tempfile
import time
from typing import Any, Callable

from collectors import tushare_client
from engine import china_heatmap_live as contract
from engine import live_quotes
from engine.prophet_live import cn_clock
from lib import config

log = logging.getLogger("china_heatmap_live")

RT_K_TS_CODE = "6*.SH,3*.SZ,0*.SZ"
RT_K_FIELDS = "ts_code,pre_close,high,open,low,close,vol,amount,num,trade_time"
FETCH_PHASES = frozenset({"morning", "afternoon", "closing_auction", "post_close"})
FAST_PHASES = frozenset({"morning", "afternoon", "closing_auction"})
DEFAULT_BASE = config.ROOT / "site" / "marketdata" / "china_heatmap.json"
DEFAULT_OUT = Path(os.environ.get(
    "CHINA_HEATMAP_LIVE_OUT",
    str(Path(os.environ.get("MACRO_LIVE_DIR", "/var/lib/macro-live/public/live")) / "china_heatmap.json"),
))


def fetch_tushare_snapshot(
    baseline: contract.BaselineHeatmap,
) -> dict[str, dict[str, Any]] | None:
    """Fetch one whole-market ``rt_k`` response and normalize it."""
    frame = tushare_client.query(
        "rt_k",
        fields=RT_K_FIELDS,
        ts_code=RT_K_TS_CODE,
        _timeout=5.0,
        _retries=0,
        _return_empty=True,
    )
    if frame is None or frame.empty:
        return None
    quotes = contract.normalize_tushare_rows(frame, baseline)
    return quotes or None


def fetch_tencent_snapshot(
    baseline: contract.BaselineHeatmap,
) -> dict[str, dict[str, Any]]:
    raw, _, _ = live_quotes.fetch_tencent_cn(
        list(baseline.tickers), batch_size=30, max_workers=6,
        timeout=5, retries=0,
    )
    return contract.normalize_tencent_quotes(raw, baseline)


def atomic_write_payload(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace a complete public JSON artifact with mode 0644."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o644)
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


class ChinaHeatmapLiveProducer:
    def __init__(
        self,
        *,
        base_path: Path,
        out_path: Path,
        tushare_fetch: Callable[[contract.BaselineHeatmap], dict[str, dict[str, Any]] | None] = fetch_tushare_snapshot,
        tencent_fetch: Callable[[contract.BaselineHeatmap], dict[str, dict[str, Any]]] = fetch_tencent_snapshot,
        phase_fn: Callable[[datetime | None], str] = cn_clock.phase,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleeper: Callable[[float], None] = time.sleep,
        interval: float = 2.0,
        fallback_interval: float = 15.0,
        heartbeat_interval: float = 30.0,
    ) -> None:
        self.base_path = Path(base_path)
        self.out_path = Path(out_path)
        self.tushare_fetch = tushare_fetch
        self.tencent_fetch = tencent_fetch
        self.phase_fn = phase_fn
        self.clock = clock
        self.sleeper = sleeper
        self.interval = float(interval)
        self.fallback_interval = float(fallback_interval)
        self.heartbeat_interval = float(heartbeat_interval)
        self._baseline_signature: tuple[int, int, int] | None = None
        self._baseline: contract.BaselineHeatmap | None = None
        self._last_good_quotes: dict[str, dict[str, Any]] | None = None
        self._last_good_source: str | None = None
        self._last_good_fallback = False
        self._last_fallback_at: datetime | None = None
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def request_stop(self) -> None:
        self._stopped = True

    def _restore_last_good(self, baseline: contract.BaselineHeatmap) -> None:
        """Recover the existing atomic artifact, never a second snapshot store.

        Validate its original publication first. step() then rechecks every
        recovered quote against the current session clock before using it.
        This keeps a lunch restart from erasing the valid morning close.
        """
        try:
            if not self.out_path.is_file() or self.out_path.stat().st_size > 8 * 1024 * 1024:
                return
            payload = json.loads(self.out_path.read_text(encoding="utf-8"))
            generated = datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))
            if generated.tzinfo is None:
                return
            restored = contract.validate_live_payload(payload, baseline, now=generated)
            if restored["usable"] and restored["quotes"]:
                self._last_good_quotes = restored["quotes"]
                self._last_good_source = restored["source"]
                self._last_good_fallback = restored["fallback"]
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            # Corrupt/old/baseline-mismatched data is not a startup authority.
            log.warning("Prior China heatmap artifact is not reusable")

    def _load_baseline(self) -> contract.BaselineHeatmap:
        current = self.base_path.stat()
        signature = (current.st_ino, current.st_mtime_ns, current.st_size)
        if self._baseline is not None and signature == self._baseline_signature:
            return self._baseline
        payload = json.loads(self.base_path.read_text(encoding="utf-8"))
        baseline = contract.validate_baseline(payload)
        if self._baseline is not None and baseline != self._baseline:
            self._last_good_quotes = None
            self._last_good_source = None
            self._last_good_fallback = False
            self._last_fallback_at = None
        first_load = self._baseline is None
        self._baseline = baseline
        self._baseline_signature = signature
        if first_load:
            self._restore_last_good(baseline)
        return baseline

    def _candidate_usable(
        self,
        baseline: contract.BaselineHeatmap,
        quotes: dict[str, dict[str, Any]],
        *,
        source: str,
        fallback: bool,
        phase: str,
        now: datetime,
    ) -> bool:
        try:
            candidate = contract.build_live_payload(
                baseline, quotes, source=source, fallback=fallback,
                phase=phase, now=now,
            )
            contract.validate_live_payload(candidate, baseline, now=now)
        except (contract.LiveContractError, TypeError, ValueError, OverflowError):
            return False
        if not candidate["usable"]:
            return False
        previous = self._last_good_quotes or {}
        return not any(
            ticker in previous and quote["ts"] < previous[ticker]["ts"]
            for ticker, quote in candidate["quotes"].items()
        )

    def step(
        self,
        now: datetime | None = None,
        *,
        require_usable: bool = False,
    ) -> dict[str, Any]:
        instant = (now or self.clock()).astimezone(timezone.utc)
        baseline = self._load_baseline()
        phase = self.phase_fn(instant)
        fresh_quotes: dict[str, dict[str, Any]] | None = None
        fresh_source: str | None = None
        fresh_fallback = False
        if phase in FETCH_PHASES:
            try:
                fresh_quotes = self.tushare_fetch(baseline)
            except Exception as exc:  # noqa: BLE001 - do not echo request-bearing errors
                log.warning("Tushare live heatmap fetch failed (%s)", type(exc).__name__)
        # Explicit now= is the deterministic test seam. Production calls resample
        # after each network leg, so latency cannot fabricate future/fresh quotes
        # or carry a morning decision across the lunch boundary.
        instant = (now or self.clock()).astimezone(timezone.utc)
        phase = self.phase_fn(instant)
        if fresh_quotes:
            if self._candidate_usable(
                baseline, fresh_quotes, source="tushare-rt-k", fallback=False,
                phase=phase, now=instant,
            ):
                fresh_source = "tushare-rt-k"
            else:
                fresh_quotes = None
        if not fresh_quotes and phase in FETCH_PHASES:
            fallback_due = (
                self._last_fallback_at is None
                or (instant - self._last_fallback_at).total_seconds() >= self.fallback_interval
            )
            if fallback_due:
                self._last_fallback_at = instant
                try:
                    fresh_quotes = self.tencent_fetch(baseline) or None
                except Exception as exc:  # noqa: BLE001 - bounded independent fallback
                    log.warning("Tencent live heatmap fallback failed (%s)", type(exc).__name__)
                    fresh_quotes = None
                instant = (now or self.clock()).astimezone(timezone.utc)
                phase = self.phase_fn(instant)
                if fresh_quotes and self._candidate_usable(
                    baseline, fresh_quotes, source="tencent", fallback=True,
                    phase=phase, now=instant,
                ):
                    fresh_source = "tencent"
                    fresh_fallback = True
                else:
                    fresh_quotes = None
        if fresh_quotes:
            self._last_good_quotes = fresh_quotes
            self._last_good_source = fresh_source
            self._last_good_fallback = fresh_fallback
        quotes = self._last_good_quotes or {}
        source = self._last_good_source if quotes else None
        fallback = self._last_good_fallback if quotes else False
        payload = contract.build_live_payload(
            baseline, quotes, source=source, fallback=fallback,
            phase=phase, now=instant,
        )
        payload = contract.validate_live_payload(payload, baseline, now=instant)
        if require_usable and not payload["usable"]:
            raise RuntimeError("live China heatmap snapshot is not usable")
        atomic_write_payload(self.out_path, payload)
        return payload


    def run_forever(self) -> None:
        """Run until requested to stop, keeping each failure lane-local."""
        while not self._stopped:
            instant = self.clock().astimezone(timezone.utc)
            phase = self.phase_fn(instant)
            try:
                self.step()
            except Exception as exc:  # noqa: BLE001 - retain the last atomic artifact
                log.warning("China heatmap live iteration failed (%s)", type(exc).__name__)
            if self._stopped:
                break
            delay = self.interval if phase in FAST_PHASES else self.heartbeat_interval
            try:
                self.sleeper(delay)
            except KeyboardInterrupt:
                self.request_stop()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="publish one usable snapshot and exit")
    mode.add_argument("--loop", action="store_true", help="run the persistent live publisher")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--fallback-interval", type=float, default=15.0)
    parser.add_argument("--heartbeat-interval", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    args = _parser().parse_args(argv)
    instance = ChinaHeatmapLiveProducer(
        base_path=args.base,
        out_path=args.out,
        interval=args.interval,
        fallback_interval=args.fallback_interval,
        heartbeat_interval=args.heartbeat_interval,
    )

    def stop(_signum=None, _frame=None) -> None:
        instance.request_stop()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        if args.once:
            instance.step(require_usable=True)
        else:
            instance.run_forever()
        return 0
    except Exception as exc:  # noqa: BLE001 - preserve output, omit request-bearing errors
        log.error("China heatmap live publisher failed (%s)", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
