#!/usr/bin/env python3
"""Publish the display-only live China A-share heatmap overlay."""
from __future__ import annotations

import argparse
from datetime import datetime, time as clock_time, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
from typing import Any, Callable, Literal

# Runnable directly as a file as well as via python -m. Pin this repository
# before module-scope imports to avoid loading another checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import tushare_client
from engine import china_heatmap_live as contract
from engine import live_quotes
from engine.prophet_live import cn_clock
from lib import cn_calendar, config

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


_RejectionReason = Literal[
    "no_normalized_quotes", "fetch_exception", "contract_rejected",
    "insufficient_qualified_coverage", "phase_or_source_freshness_rejected",
    "source_timestamp_regression", "no_usable_snapshot",
]


def _log_one_shot_rejection(
    *,
    source: str | None,
    reason: _RejectionReason,
    requested: int,
    normalized: int | None = None,
    qualified: int | None = None,
    retained: int | None = None,
) -> None:
    """Report fixed labels and aggregate counts, never provider or quote data."""
    event = {
        "source": source if source in {"tushare-rt-k", "tencent"} else "unavailable",
        "reason": reason,
        "requested": requested,
    }
    for name, count in (
        ("normalized", normalized), ("qualified", qualified), ("retained", retained),
    ):
        if count is not None:
            event[name] = count
    log.info("China heatmap one-shot rejection: %s", json.dumps(event, sort_keys=True))


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
    raw, failed, status = live_quotes.fetch_tencent_cn(
        list(baseline.tickers), batch_size=30, max_workers=6,
        timeout=5, retries=0,
    )
    # During an actual session, sporadic connect timeouts can drop whole
    # 30-name envelopes (~240/1720 missing in the 2026-10-14 morning probe).
    # Retry only explicitly FAILED TRANSPORT batches. A provider response
    # with "no trade" is authoritative: never retry it as a fake live quote.
    #
    # One bounded repair wave, using smaller requests. The interval loop is
    # already the canonical retry owner; do not add another queue/scheduler,
    # recurse, mint wall-clock timestamps or accept <95% qualified coverage.
    failed = list(dict.fromkeys(
        ticker for ticker in failed
        if ticker in baseline.ticker_set and ticker not in raw
    ))
    if status == "partial" and failed and len(failed) <= 480:
        recovered, unresolved, _ = live_quotes.fetch_tencent_cn(
            failed, batch_size=15, max_workers=8,
            timeout=5, retries=0,
        )
        raw.update({
            ticker: quote for ticker, quote in recovered.items()
            if ticker in baseline.ticker_set and ticker in failed
        })
        log.info(
            "China heatmap Tencent transport recovery: initial_failed=%d "
            "recovered=%d unresolved_batches=%d final_quotes=%d",
            len(failed), len(recovered), len(unresolved), len(raw),
        )
    elif failed:
        log.warning(
            "China heatmap Tencent transport recovery not attempted: "
            "status=%s failed_names=%d (bounded max=480)",
            status, len(failed),
        )
    return contract.normalize_tencent_quotes(raw, baseline)


def should_poll_pending_close(
    baseline: contract.BaselineHeatmap, now: datetime, phase: str,
) -> bool:
    """Only poll existing sources after close while today's EOD is unposted.

    The live producer's ordinary closed phase extends all night; fetching
    the entire China universe every heartbeat would be unnecessary provider
    load. During a lawful Shanghai session between 15:15 and 19:30 CST, a
    still-previous-session baseline may instead receive a bounded, slow
    provisional close refresh. If the official daily map advances or it is a
    holiday/non-session, this fetch path automatically shuts off.
    """
    if phase != "closed":
        return False
    local = cn_clock.cst_clock(now)
    today = local.date()
    if (not cn_calendar.is_session(today)
        or not (cn_clock.POST_CLOSE_END <= local.time() < clock_time(19, 30))):
        return False
    previous = cn_calendar.last_session_on_or_before(today - timedelta(days=1))
    return baseline.asof == previous.isoformat()


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
        self._last_pending_close_poll_at: datetime | None = None
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
            self._last_pending_close_poll_at = None
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
        report_rejection: bool = False,
    ) -> bool:
        # A nonstandard mapping may reject the contract; diagnostics must not
        # call its custom __len__ or turn that refusal into a different failure.
        normalized = len(quotes) if report_rejection and type(quotes) is dict else None
        try:
            candidate = contract.build_live_payload(
                baseline, quotes, source=source, fallback=fallback,
                phase=phase, now=now,
            )
            contract.validate_live_payload(candidate, baseline, now=now)
        except (contract.LiveContractError, TypeError, ValueError, OverflowError):
            if report_rejection:
                _log_one_shot_rejection(
                    source=source, reason="contract_rejected",
                    requested=len(baseline.tickers), normalized=normalized,
                )
            return False
        if not candidate["usable"]:
            if report_rejection:
                reason: _RejectionReason = (
                    "insufficient_qualified_coverage"
                    if candidate["coverage"] < contract.MIN_COVERAGE
                    else "phase_or_source_freshness_rejected"
                )
                _log_one_shot_rejection(
                    source=source, reason=reason, requested=len(baseline.tickers),
                    normalized=normalized, qualified=candidate["resolved"],
                )
            return False
        previous = self._last_good_quotes or {}
        regressed = any(
            ticker in previous and quote["ts"] < previous[ticker]["ts"]
            for ticker, quote in candidate["quotes"].items()
        )
        if regressed and report_rejection:
            _log_one_shot_rejection(
                source=source, reason="source_timestamp_regression",
                requested=len(baseline.tickers), normalized=normalized,
                qualified=candidate["resolved"],
            )
        return not regressed

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
        pending_poll = should_poll_pending_close(baseline, instant, phase)
        if pending_poll:
            due = (self._last_pending_close_poll_at is None
                   or (instant - self._last_pending_close_poll_at).total_seconds() >= 120)
            pending_poll = due
            if due:
                self._last_pending_close_poll_at = instant
        if phase in FETCH_PHASES or pending_poll:
            try:
                fresh_quotes = self.tushare_fetch(baseline)
            except Exception as exc:  # noqa: BLE001 - do not echo request-bearing errors
                log.warning("Tushare live heatmap fetch failed (%s)", type(exc).__name__)
                if require_usable:
                    _log_one_shot_rejection(
                        source="tushare-rt-k", reason="fetch_exception",
                        requested=len(baseline.tickers),
                    )
            else:
                if require_usable and not fresh_quotes:
                    _log_one_shot_rejection(
                        source="tushare-rt-k", reason="no_normalized_quotes",
                        requested=len(baseline.tickers), normalized=0,
                    )
        # Explicit now= is the deterministic test seam. Production calls resample
        # after each network leg, so latency cannot fabricate future/fresh quotes
        # or carry a morning decision across the lunch boundary.
        instant = (now or self.clock()).astimezone(timezone.utc)
        phase = self.phase_fn(instant)
        if fresh_quotes:
            if self._candidate_usable(
                baseline, fresh_quotes, source="tushare-rt-k", fallback=False,
                phase=phase, now=instant, report_rejection=require_usable,
            ):
                fresh_source = "tushare-rt-k"
            else:
                fresh_quotes = None
        if not fresh_quotes and (phase in FETCH_PHASES or pending_poll):
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
                    if require_usable:
                        _log_one_shot_rejection(
                            source="tencent", reason="fetch_exception",
                            requested=len(baseline.tickers),
                        )
                else:
                    if require_usable and not fresh_quotes:
                        _log_one_shot_rejection(
                            source="tencent", reason="no_normalized_quotes",
                            requested=len(baseline.tickers), normalized=0,
                        )
                instant = (now or self.clock()).astimezone(timezone.utc)
                phase = self.phase_fn(instant)
                if fresh_quotes and self._candidate_usable(
                    baseline, fresh_quotes, source="tencent", fallback=True,
                    phase=phase, now=instant, report_rejection=require_usable,
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
            _log_one_shot_rejection(
                source=source, reason="no_usable_snapshot",
                requested=len(baseline.tickers), retained=len(quotes),
                qualified=payload["resolved"],
            )
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
