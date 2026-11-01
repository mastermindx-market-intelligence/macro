"""Local EDGAR Item-2.02 store reader for live Radar catalyst coverage.

Owner: collectors.edgar_earnings_8k. Mapping:
research/live_entry_radar/INTRADAY_DISLOCATION_CATALYST_EDGAR_EARNINGS_R0_MAPPING.md
(§3 clock law, §6 refusals, §7 no-coverage rule).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from engine.entry_radar.catalyst_adapters import (
    EDGAR_EARNINGS_OWNER,
    adapt_edgar_earnings_item_202,
)
from engine.entry_radar.catalyst_context import (
    DEFAULT_MAX_SOURCE_STALENESS_SECONDS,
    CatalystContextError,
    CatalystEvidence,
    CatalystSourceRead,
    _require_ts,
)

EDGAR_STORE_SOURCE_ID = EDGAR_EARNINGS_OWNER
DEFAULT_LOOKBACK_DAYS = 10


@dataclass(frozen=True, slots=True)
class EdgarStoreRead:
    reads_by_ticker: dict[str, CatalystSourceRead]
    evidence_by_ticker: dict[str, tuple[CatalystEvidence, ...]]
    refusals: dict[str, int]
    rows_scanned: int
    error: str | None
    source_asof: datetime | None


def _parse_manifest_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    try:
        text = str(raw).replace("Z", "+00:00")
        got = datetime.fromisoformat(text)
        if got.tzinfo is None or got.utcoffset() is None:
            return None
        return got.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _manifest_entry(manifest: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_ts: datetime | None = None
    for key, entry in manifest.items():
        if not isinstance(entry, dict) or entry.get("ticker") != ticker:
            continue
        if not str(key).isdigit():
            continue
        ts = _parse_manifest_ts(entry.get("ts"))
        if best is None or (ts is not None and (best_ts is None or ts > best_ts)):
            best = entry
            best_ts = ts
    if best is not None:
        return best
    alt = manifest.get(f"ticker:{ticker}")
    return alt if isinstance(alt, dict) else None


def _build_read(
    entry: dict[str, Any] | None,
    *,
    generated_at: datetime,
) -> tuple[CatalystSourceRead, datetime | None]:
    if entry is None:
        return (
            CatalystSourceRead(
                source_id=EDGAR_STORE_SOURCE_ID,
                status="unavailable",
                source_asof=generated_at,
                observed_at=generated_at,
                fresh_until=generated_at,
                detail="manifest entry missing",
            ),
            None,
        )
    ts = _parse_manifest_ts(entry.get("ts"))
    if ts is None:
        return (
            CatalystSourceRead(
                source_id=EDGAR_STORE_SOURCE_ID,
                status="unavailable",
                source_asof=generated_at,
                observed_at=generated_at,
                fresh_until=generated_at,
                detail="manifest ts unparseable",
            ),
            None,
        )
    if ts > generated_at:
        return (
            CatalystSourceRead(
                source_id=EDGAR_STORE_SOURCE_ID,
                status="unavailable",
                source_asof=generated_at,
                observed_at=generated_at,
                fresh_until=generated_at,
                detail="manifest ts after generated_at",
            ),
            None,
        )
    status = str(entry.get("status") or "")
    try:
        n_missing = int(entry.get("n_shards_missing") or 0)
    except (TypeError, ValueError):
        n_missing = -1
    n_filings = entry.get("n_filings", "")
    if status == "ok" and n_missing == 0:
        fresh = ts + timedelta(seconds=DEFAULT_MAX_SOURCE_STALENESS_SECONDS)
        fresh = max(fresh, ts)
        detail = f"manifest ok n_filings={n_filings}"[:200]
        return (
            CatalystSourceRead(
                source_id=EDGAR_STORE_SOURCE_ID,
                status="ok",
                source_asof=ts,
                observed_at=generated_at,
                fresh_until=fresh,
                detail=detail,
            ),
            ts,
        )
    detail = f"manifest status={status} n_shards_missing={n_missing}"[:200]
    return (
        CatalystSourceRead(
            source_id=EDGAR_STORE_SOURCE_ID,
            status="unavailable",
            source_asof=ts,
            observed_at=generated_at,
            fresh_until=ts,
            detail=detail,
        ),
        ts,
    )


def _unavailable_reads(tickers: Sequence[str], generated_at: datetime) -> dict[str, CatalystSourceRead]:
    return {
        t: CatalystSourceRead(
            source_id=EDGAR_STORE_SOURCE_ID,
            status="unavailable",
            source_asof=generated_at,
            observed_at=generated_at,
            fresh_until=generated_at,
            detail="store unavailable",
        )
        for t in tickers
    }


def read_edgar_item_202_for_tickers(
    *,
    tickers: Sequence[str],
    decision_at: datetime,
    generated_at: datetime,
    store_path: Path | None = None,
    manifest_path: Path | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> EdgarStoreRead:
    decision = _require_ts("decision_at", decision_at)
    generated = _require_ts("generated_at", generated_at)
    if generated < decision:
        raise CatalystContextError("generated_at is before decision_at")

    normalized = sorted({str(t).strip().upper() for t in tickers if str(t).strip()})
    empty = EdgarStoreRead({}, {}, {}, 0, None, None)
    if not normalized:
        return empty

    import collectors.edgar_earnings_8k as edgar_mod

    store_p = store_path if store_path is not None else edgar_mod._store_path()
    manifest_p = manifest_path if manifest_path is not None else edgar_mod._manifest_path()

    try:
        if not store_p.exists():
            return EdgarStoreRead(
                _unavailable_reads(normalized, generated),
                {},
                {},
                0,
                f"store missing: {store_p}",
                None,
            )
        if not manifest_p.exists():
            return EdgarStoreRead(
                _unavailable_reads(normalized, generated),
                {},
                {},
                0,
                f"manifest missing: {manifest_p}",
                None,
            )

        if manifest_path is not None:
            manifest = json.loads(manifest_p.read_text())
        else:
            manifest = edgar_mod.load_manifest()

        reads: dict[str, CatalystSourceRead] = {}
        owner_ts: dict[str, datetime | None] = {}
        ok_asofs: list[datetime] = []
        for ticker in normalized:
            read, mts = _build_read(_manifest_entry(manifest, ticker), generated_at=generated)
            reads[ticker] = read
            owner_ts[ticker] = mts
            if read.status == "ok" and mts is not None:
                ok_asofs.append(mts)

        store_source_asof = max(ok_asofs) if ok_asofs else None

        cols = list(edgar_mod.STORE_COLUMNS)
        frame = pd.read_parquet(store_p, columns=cols)
        tick_set = set(normalized)
        frame = frame[frame["ticker"].astype(str).str.upper().isin(tick_set)]
        rows_scanned = len(frame)

        acceptance = pd.to_datetime(frame["acceptance_datetime"], utc=True, errors="coerce")
        cutoff = decision - timedelta(days=lookback_days)
        keep = (acceptance >= cutoff) | acceptance.isna()
        frame = frame.loc[keep]

        refusals: dict[str, int] = {}
        evidence_lists: dict[str, list[CatalystEvidence]] = {t: [] for t in normalized}
        seen: dict[str, set[str]] = {t: set() for t in normalized}

        for _, row in frame.iterrows():
            ticker = str(row["ticker"]).strip().upper()
            obs = owner_ts.get(ticker)
            if obs is None:
                key = "no owner observation receipt"[:60]
                refusals[key] = refusals.get(key, 0) + 1
                continue
            row_dict = row.to_dict()
            try:
                ev = adapt_edgar_earnings_item_202(row_dict, owner_observed_at=obs)
            except CatalystContextError as exc:
                key = str(exc)[:60]
                refusals[key] = refusals.get(key, 0) + 1
                continue
            if ev.evidence_ref in seen[ticker]:
                continue
            seen[ticker].add(ev.evidence_ref)
            evidence_lists[ticker].append(ev)

        evidence_by_ticker = {
            t: tuple(sorted(lst, key=lambda e: e.source_available_at))
            for t, lst in evidence_lists.items()
            if lst
        }

        return EdgarStoreRead(
            reads,
            evidence_by_ticker,
            refusals,
            rows_scanned,
            None,
            store_source_asof,
        )
    except CatalystContextError:
        raise
    except Exception as exc:
        return EdgarStoreRead(
            _unavailable_reads(normalized, generated),
            {},
            {},
            0,
            repr(exc)[:300],
            None,
        )
