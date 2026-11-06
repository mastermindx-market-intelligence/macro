"""Decision-time EDGAR Item-2.02 owner read for live Radar catalyst coverage.

Owner: collectors.edgar_earnings_8k (EDGAR_EARNINGS_OWNER). Same owner as the local
store reader, but reads the SEC submissions ``recent`` block at decision time (never
older-files shards; the 10-day lookback always sits inside ``recent``). Mapping:
research/live_entry_radar/INTRADAY_DISLOCATION_CATALYST_EDGAR_EARNINGS_R0_MAPPING.md
(§3 clock law, §6 refusals, §7 no-coverage rule).

Clock law: source_asof == observed_at == the instant the owner's endpoint answered;
fresh_until = observed_at + 900 s; the CALLER must set decision_at >= observed_at or
usable_at is False.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from engine.entry_radar.catalyst_adapters import adapt_edgar_earnings_item_202
from engine.entry_radar.catalyst_context import (
    DEFAULT_MAX_SOURCE_STALENESS_SECONDS,
    CatalystContextError,
    CatalystEvidence,
    CatalystSourceRead,
    _require_ts,
)
from engine.entry_radar.catalyst_edgar_store import (
    DEFAULT_LOOKBACK_DAYS,
    EDGAR_STORE_SOURCE_ID,
)

# Owner PACE_S (0.12 s) bounds rate at ≤10 req/s; worst case DEFAULT_MAX_LIVE_TICKERS
# requests per 5-minute live pass.
LIVE_SOURCE_ID = EDGAR_STORE_SOURCE_ID
CATALYST_LIVE_ENV = "ENTRY_RADAR_CATALYST_LIVE"
DEFAULT_MAX_LIVE_TICKERS = 48
DEFAULT_LIVE_TIME_BUDGET_SECONDS = 20.0


@dataclass(frozen=True, slots=True)
class EdgarLiveRead:
    reads_by_ticker: dict[str, CatalystSourceRead]
    evidence_by_ticker: dict[str, tuple[CatalystEvidence, ...]]
    refusals: dict[str, int]
    rows_scanned: int
    error: str | None
    attempted: int
    fetched_ok: int
    budget_exhausted: int
    elapsed_seconds: float
    last_observed_at: datetime | None


def _unavailable(now: datetime, detail: str) -> CatalystSourceRead:
    return CatalystSourceRead(
        source_id=LIVE_SOURCE_ID,
        status="unavailable",
        source_asof=now,
        observed_at=now,
        fresh_until=now,
        detail=detail[:200],
    )


def read_edgar_item_202_live(
    *,
    tickers: Sequence[str],
    now: datetime,
    cik_by_ticker: Mapping[str, int] | None = None,
    store_path: Path | None = None,
    fetch: Callable[[int], Mapping[str, Any] | None] | None = None,
    clock: Callable[[], datetime] | None = None,
    pace_seconds: float | None = None,
    max_tickers: int = DEFAULT_MAX_LIVE_TICKERS,
    time_budget_seconds: float = DEFAULT_LIVE_TIME_BUDGET_SECONDS,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> EdgarLiveRead:
    pass_now = _require_ts("now", now)
    normalized = sorted({str(t).strip().upper() for t in tickers if str(t).strip()})
    empty = EdgarLiveRead({}, {}, {}, 0, None, 0, 0, 0, 0.0, None)
    if not normalized:
        return empty

    t0 = time.monotonic()
    reads: dict[str, CatalystSourceRead] = {}
    try:
        import collectors.edgar_earnings_8k as edgar_mod

        if clock is None:
            clock = lambda: datetime.now(timezone.utc)
        if pace_seconds is None:
            pace_seconds = edgar_mod.PACE_S
        if fetch is None:
            fetch = lambda cik: edgar_mod._sec_get_json(
                edgar_mod.SUBMISSIONS_URL.format(int(cik))
            )

        cik_map: dict[str, int]
        if cik_by_ticker is not None:
            cik_map = {str(k).strip().upper(): int(v) for k, v in cik_by_ticker.items()}
        else:
            try:
                store_p = store_path if store_path is not None else edgar_mod._store_path()
                frame = pd.read_parquet(store_p, columns=["ticker", "cik"])
                frame = frame.dropna(subset=["cik"])
                cik_map = {}
                for _, row in frame.iterrows():
                    t = str(row["ticker"]).strip().upper()
                    if t not in cik_map:
                        cik_map[t] = int(row["cik"])
            except Exception as exc:
                reason = repr(exc)[:200]
                msg = f"cik lookup unavailable: {reason}"[:300]
                reads = {
                    t: _unavailable(
                        pass_now,
                        f"cik lookup unavailable: {reason}"[:200],
                    )
                    for t in normalized
                }
                elapsed = round(max(0.0, time.monotonic() - t0), 3)
                return EdgarLiveRead(
                    reads, {}, {}, 0, msg, 0, 0, 0, elapsed, None
                )

        for t in normalized:
            if t not in cik_map:
                reads[t] = _unavailable(pass_now, "cik unknown in store")

        cik_tickers = [t for t in normalized if t in cik_map]
        refusals: dict[str, int] = {}
        evidence_lists: dict[str, list[CatalystEvidence]] = {}
        seen: dict[str, set[str]] = {}
        rows_scanned = 0
        attempted = 0
        fetched_ok = 0
        budget_exhausted = 0
        last_observed_at: datetime | None = None
        cutoff = pass_now - timedelta(days=lookback_days)

        for idx, ticker in enumerate(cik_tickers):
            elapsed = time.monotonic() - t0
            if attempted >= max_tickers or elapsed >= time_budget_seconds:
                for t in cik_tickers[idx:]:
                    reads[t] = _unavailable(pass_now, "live budget exhausted")
                    budget_exhausted += 1
                break

            attempted += 1
            cik = cik_map[ticker]
            data: Mapping[str, Any] | None
            try:
                data = fetch(cik)
            except Exception as exc:
                reads[ticker] = _unavailable(
                    pass_now, f"live fetch failed: {type(exc).__name__}"
                )
                if pace_seconds > 0:
                    time.sleep(pace_seconds)
                continue

            if data is None:
                reads[ticker] = _unavailable(pass_now, "submissions 404")
                if pace_seconds > 0:
                    time.sleep(pace_seconds)
                continue

            observed = _require_ts("observed", clock())
            if observed < pass_now:
                reads[ticker] = _unavailable(pass_now, "clock before pass now")
                if pace_seconds > 0:
                    time.sleep(pace_seconds)
                continue

            recent = (data.get("filings") or {}).get("recent") or {}
            rows = edgar_mod._extract_8k_rows(ticker, cik, recent)
            rows_scanned += len(rows)

            if ticker not in evidence_lists:
                evidence_lists[ticker] = []
                seen[ticker] = set()

            kept = 0
            for row in rows:
                acc_raw = row.get("acceptance_datetime")
                acceptance = pd.to_datetime(acc_raw, utc=True, errors="coerce")
                if not (pd.isna(acceptance) or acceptance >= cutoff):
                    continue
                try:
                    ev = adapt_edgar_earnings_item_202(row, owner_observed_at=observed)
                except CatalystContextError as exc:
                    key = str(exc)[:60]
                    refusals[key] = refusals.get(key, 0) + 1
                    continue
                if ev.evidence_ref in seen[ticker]:
                    continue
                seen[ticker].add(ev.evidence_ref)
                evidence_lists[ticker].append(ev)
                kept += 1

            fetched_ok += 1
            reads[ticker] = CatalystSourceRead(
                source_id=LIVE_SOURCE_ID,
                status="ok",
                source_asof=observed,
                observed_at=observed,
                fresh_until=observed + timedelta(seconds=DEFAULT_MAX_SOURCE_STALENESS_SECONDS),
                detail=f"live submissions recent rows={len(rows)} kept={kept}"[:200],
            )
            last_observed_at = (
                observed
                if last_observed_at is None
                else max(last_observed_at, observed)
            )
            if pace_seconds > 0:
                time.sleep(pace_seconds)

        evidence_by_ticker = {
            t: tuple(sorted(lst, key=lambda e: e.source_available_at))
            for t, lst in evidence_lists.items()
            if lst
        }
        elapsed_seconds = round(max(0.0, time.monotonic() - t0), 3)
        return EdgarLiveRead(
            reads,
            evidence_by_ticker,
            refusals,
            rows_scanned,
            None,
            attempted,
            fetched_ok,
            budget_exhausted,
            elapsed_seconds,
            last_observed_at,
        )
    except CatalystContextError:
        raise
    except Exception as exc:
        pending = [t for t in normalized if t not in reads]
        for t in pending:
            reads[t] = _unavailable(pass_now, "live reader error")
        elapsed_seconds = round(max(0.0, time.monotonic() - t0), 3)
        return EdgarLiveRead(
            reads,
            {},
            {},
            0,
            repr(exc)[:300],
            0,
            0,
            0,
            elapsed_seconds,
            None,
        )
