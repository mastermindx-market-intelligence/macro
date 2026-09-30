"""Resumable point-in-time XNYS breadth history seed.

This module deliberately does not create another price, identity, calendar, or
publication plane.  It checkpoints only accepted breadth sessions.  Recent
prices are read from the canonical ``massive_stock_day`` R2 mirror; sessions
older than that mirror may be hydrated in memory from Massive grouped daily with
``adjusted=false`` and fed through the same split-adjusted breadth engine.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests

from collectors.base import safe_exc_text
from collectors.exchange_breadth import (
    OUTPUT_DIR,
    PRICE_BASIS,
    SCHEMA_VERSION,
    MassiveReferenceClient,
    _build_frames,
    _default_price_loader,
    _load_alias_table,
    _load_prices,
    _merge_source_splits,
    _promote_generation,
    _read_json,
    _read_parquet,
    _resolve_split_entities,
    _source_split_frame,
)
from engine.close_pass.massive_close import (
    GROUPED_PATH,
    SOURCE_GROUPED,
    universe_ticker,
)
from engine.exchange_breadth import (
    AUTHORITY,
    SOURCE_RULES_VERSION,
    UNIVERSE_ALL_ISSUES,
    UNIVERSE_OPERATING,
    normalize_roster,
    update_membership_intervals,
)
from lib import config
from lib.nyse_calendar import (
    expected_last_session,
    is_session,
    last_session_on_or_before,
    session_n_back,
    sessions_between,
)

DEFAULT_RECENT_SESSIONS = 270
STATE_SCHEMA_VERSION = "exchange_breadth.backfill.v1"
DEFAULT_STATE_NAME = "_backfill_state.json"
DEFAULT_BASE_URL = "https://api.polygon.io"

SessionProcessor = Callable[[date], "SessionAcceptance"]
RequestJson = Callable[[str, dict[str, Any]], Mapping[str, Any]]


class BackfillRefused(RuntimeError):
    """A session could not be accepted without weakening an evidence gate."""


@dataclass(frozen=True)
class SessionAcceptance:
    session: date
    roster_reconciled: bool
    price_reconciled: bool
    published: bool
    source: str
    receipt: dict[str, Any]


@dataclass(frozen=True)
class BackfillReport:
    requested_sessions: tuple[date, ...]
    processed_sessions: tuple[date, ...]
    skipped_sessions: tuple[date, ...]
    remaining_sessions: tuple[date, ...]
    completed_total: int
    dry_run: bool
    state_path: str


@dataclass(frozen=True)
class GroupedSessionEvidence:
    session: date
    closes: dict[str, float]
    source: str
    finalized: bool
    wanted_n: int
    matched_n: int
    vendor_rows: int
    observed_at: str
    receipt: dict[str, Any]


def _safe_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _parse_date(value: str | date | None, *, field: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise BackfillRefused(f"invalid {field}: {value!r}") from exc


def enumerate_backfill_sessions(
    *,
    start: date | str | None = None,
    end: date | str | None = None,
    recent_sessions: int = DEFAULT_RECENT_SESSIONS,
    now: datetime | None = None,
) -> list[date]:
    """Return completed XNYS sessions, ascending, using the canonical calendar."""
    if recent_sessions < 1:
        raise BackfillRefused("recent_sessions must be positive")
    completed = expected_last_session(now)
    requested_end = _parse_date(end, field="end")
    last = min(requested_end, completed) if requested_end else completed
    if not is_session(last):
        # Anchor explicit closed dates to the preceding reviewed XNYS session.
        last = last_session_on_or_before(last)
    requested_start = _parse_date(start, field="start")
    if requested_start is None:
        first = session_n_back(last, recent_sessions - 1)
        if first is None:
            raise BackfillRefused(
                f"cannot enumerate {recent_sessions} sessions ending {last}"
            )
    else:
        first = requested_start
    if first > last:
        return []
    sessions = sessions_between(first, last)
    if requested_start is None and len(sessions) != recent_sessions:
        raise BackfillRefused(
            f"calendar returned {len(sessions)} sessions, expected {recent_sessions}"
        )
    return sessions


def _blank_state() -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "completed_sessions": [],
        "sessions": {},
    }


def _load_state(path: Path, *, resume: bool) -> dict[str, Any]:
    if not resume or not path.exists():
        return _blank_state()
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        raise BackfillRefused(f"backfill state is unreadable: {path}") from exc
    if not isinstance(payload, dict):
        raise BackfillRefused("backfill state is not an object")
    if payload.get("schema_version") != STATE_SCHEMA_VERSION:
        raise BackfillRefused(
            f"backfill state schema mismatch: {payload.get('schema_version')!r}"
        )
    completed = payload.get("completed_sessions")
    sessions = payload.get("sessions")
    if not isinstance(completed, list) or not isinstance(sessions, dict):
        raise BackfillRefused("backfill state shape is invalid")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _validate_acceptance(expected: date, accepted: SessionAcceptance) -> None:
    if accepted.session != expected:
        raise BackfillRefused(
            f"processor returned session {accepted.session}, expected {expected}"
        )
    if not accepted.roster_reconciled:
        raise BackfillRefused(f"{expected}: roster evidence did not reconcile")
    if not accepted.price_reconciled:
        raise BackfillRefused(f"{expected}: price evidence did not reconcile")
    if not accepted.published:
        raise BackfillRefused(f"{expected}: no published generation receipt")
    receipt_session = accepted.receipt.get("accepted_session")
    if receipt_session != expected.isoformat():
        raise BackfillRefused(
            f"{expected}: published generation receipt is not session-bound"
        )


def run_backfill(
    sessions: Iterable[date],
    *,
    processor: SessionProcessor,
    state_path: Path,
    max_sessions: int | None = None,
    resume: bool = True,
    dry_run: bool = False,
) -> BackfillReport:
    """Run a bounded acceptance loop; checkpoint only after full reconciliation."""
    requested = tuple(sorted(set(sessions)))
    if any(not is_session(session) for session in requested):
        invalid = [
            session.isoformat() for session in requested if not is_session(session)
        ]
        raise BackfillRefused(f"non-XNYS session requested: {invalid[:5]}")
    if max_sessions is not None and max_sessions < 0:
        raise BackfillRefused("max_sessions must be non-negative")
    path = Path(state_path)
    state = _load_state(path, resume=resume)
    completed_before = {
        date.fromisoformat(str(raw)) for raw in state.get("completed_sessions", [])
    }
    skipped = tuple(session for session in requested if session in completed_before)
    pending = [session for session in requested if session not in completed_before]
    limit = len(pending) if max_sessions is None else int(max_sessions)
    selected = pending[:limit]
    if dry_run:
        return BackfillReport(
            requested_sessions=requested,
            processed_sessions=(),
            skipped_sessions=skipped,
            remaining_sessions=tuple(pending),
            completed_total=len(completed_before),
            dry_run=True,
            state_path=str(path),
        )

    processed: list[date] = []
    completed = set(completed_before)
    session_meta = dict(state.get("sessions") or {})
    for session in selected:
        accepted = processor(session)
        _validate_acceptance(session, accepted)
        completed.add(session)
        session_meta[session.isoformat()] = {
            "source": accepted.source,
            "receipt": accepted.receipt,
        }
        next_state = {
            "schema_version": STATE_SCHEMA_VERSION,
            "completed_sessions": sorted(day.isoformat() for day in completed),
            "sessions": session_meta,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_write_json(path, next_state)
        state = next_state
        processed.append(session)

    remaining = tuple(session for session in pending if session not in processed)
    return BackfillReport(
        requested_sessions=requested,
        processed_sessions=tuple(processed),
        skipped_sessions=skipped,
        remaining_sessions=remaining,
        completed_total=len(completed),
        dry_run=False,
        state_path=str(path),
    )


class GroupedDailyPriceClient:
    """Grouped-daily-only raw close source for sessions outside the R2 mirror."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        request_json: RequestJson | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        key = str(api_key or "").strip()
        if not key:
            raise ValueError("api_key is required")
        self.api_key = key
        self.base_url = str(base_url).rstrip("/")
        self.timeout_s = float(timeout_s)
        self._request_json = request_json or self._requests_json

    def _requests_json(self, url: str, params: dict[str, Any]) -> Mapping[str, Any]:
        response = requests.get(
            url,
            params=params,
            timeout=self.timeout_s,
            headers={"User-Agent": "MastermindX exchange-breadth-backfill/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise TypeError("source response is not a JSON object")
        return payload

    def fetch(
        self,
        session: date,
        wanted: Iterable[str],
        *,
        min_coverage: float = 0.85,
    ) -> GroupedSessionEvidence:
        wanted_set = {str(ticker).strip() for ticker in wanted if str(ticker).strip()}
        if not wanted_set:
            raise BackfillRefused(f"{session}: no grouped-daily tickers requested")
        url = f"{self.base_url}{GROUPED_PATH.format(session=session.isoformat())}"
        params: dict[str, Any] = {
            "adjusted": "false",
            "include_otc": "false",
            "apiKey": self.api_key,
        }
        try:
            payload = self._request_json(url, params)
        except Exception as exc:  # noqa: BLE001
            raise BackfillRefused(
                f"{session}: grouped daily request failed: {safe_exc_text(exc)}"
            ) from exc
        if not isinstance(payload, Mapping):
            raise BackfillRefused(f"{session}: grouped daily response is not an object")
        status = str(payload.get("status") or "").upper()
        if status != "OK":
            raise BackfillRefused(
                f"{session}: grouped daily non-OK response: {status or 'missing status'}"
            )
        rows = payload.get("results")
        if not isinstance(rows, list) or not rows:
            raise BackfillRefused(f"{session}: grouped daily returned no rows")
        closes: dict[str, float] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            raw = str(row.get("T") or "").strip()
            ticker = universe_ticker(raw)
            if ticker not in wanted_set or ticker in closes:
                continue
            value = row.get("c")
            if isinstance(value, bool):
                continue
            try:
                close = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(close) and close > 0:
                closes[ticker] = close
        coverage = len(closes) / len(wanted_set)
        if coverage < float(min_coverage):
            raise BackfillRefused(
                f"{session}: grouped daily price coverage {coverage:.3f} below "
                f"{float(min_coverage):.3f}"
            )
        observed_at = datetime.now(timezone.utc).isoformat()
        receipt = {
            "endpoint": _safe_url(url),
            "session": session.isoformat(),
            "source": SOURCE_GROUPED,
            "price_basis": "raw_rth_close",
            "adjusted": False,
            "include_otc": False,
            "finalized": True,
            "vendor_rows": len(rows),
            "wanted_n": len(wanted_set),
            "matched_n": len(closes),
            "coverage_pct": round(coverage * 100.0, 4),
            "observed_at": observed_at,
            "request_id": payload.get("request_id"),
        }
        return GroupedSessionEvidence(
            session=session,
            closes=closes,
            source=SOURCE_GROUPED,
            finalized=True,
            wanted_n=len(wanted_set),
            matched_n=len(closes),
            vendor_rows=len(rows),
            observed_at=observed_at,
            receipt=receipt,
        )


def grouped_session_maps_to_history(
    sessions: Mapping[date, Mapping[str, float]],
) -> dict[str, pd.Series]:
    """Transpose ephemeral grouped session maps into ticker-indexed raw histories."""
    values: dict[str, dict[date, float]] = {}
    for session in sorted(sessions):
        if not is_session(session):
            raise BackfillRefused(f"grouped evidence contains non-session {session}")
        for ticker, raw_close in sessions[session].items():
            close = float(raw_close)
            if not math.isfinite(close) or close <= 0:
                raise BackfillRefused(
                    f"grouped evidence has invalid close for {ticker} on {session}"
                )
            values.setdefault(str(ticker), {})[session] = close
    out: dict[str, pd.Series] = {}
    for ticker, by_session in values.items():
        ordered = sorted(by_session)
        out[ticker] = pd.Series(
            [by_session[session] for session in ordered],
            index=pd.DatetimeIndex(ordered),
            name=ticker,
            dtype=float,
        )
    return out


def compute_backfill_frames(
    *,
    intervals: pd.DataFrame,
    splits: pd.DataFrame,
    prices: dict[str, pd.Series],
    observation_session: date,
    state: dict[str, Any],
    counts: dict[str, dict[str, int]],
) -> dict[str, pd.DataFrame]:
    """Backfill seam into the same split-adjusted collector/core calculation."""
    frames, _diagnostics = _build_frames(
        intervals=intervals,
        splits=splits,
        prices=prices,
        observation_session=observation_session,
        state=state,
        counts=counts,
    )
    return frames


@dataclass(frozen=True)
class PriceHistoryEvidence:
    prices: dict[str, pd.Series]
    current_source: str
    receipt: dict[str, Any]


def _r2_manifest_coverage(data_root: Path) -> tuple[date, date]:
    manifest_path = Path(data_root) / "massive_stock_day" / "_manifest.json"
    if not manifest_path.exists():
        raise BackfillRefused("massive_stock_day R2 manifest is absent")
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as exc:  # noqa: BLE001
        raise BackfillRefused("massive_stock_day R2 manifest is unreadable") from exc
    if not isinstance(manifest, Mapping):
        raise BackfillRefused("massive_stock_day R2 manifest is not an object")
    coverage = manifest.get("coverage")
    anchor = manifest.get("anchor")
    first_raw = None
    last_raw = manifest.get("latest_date")
    if isinstance(coverage, Mapping):
        first_raw = coverage.get("first_day")
        last_raw = coverage.get("last_day") or last_raw
    if isinstance(anchor, Mapping):
        first_raw = first_raw or anchor.get("first")
        last_raw = last_raw or anchor.get("last")
    if not first_raw or not last_raw:
        raise BackfillRefused("massive_stock_day R2 manifest lacks coverage bounds")
    try:
        first = pd.Timestamp(first_raw).date()
        last = pd.Timestamp(last_raw).date()
    except Exception as exc:  # noqa: BLE001
        raise BackfillRefused(
            "massive_stock_day R2 coverage bounds are invalid"
        ) from exc
    if first > last or not is_session(first) or not is_session(last):
        raise BackfillRefused(
            f"massive_stock_day R2 coverage is invalid: {first}..{last}"
        )
    return first, last


class HybridPriceHistory:
    """Load raw history from R2, hydrating only out-of-coverage days over REST."""

    def __init__(
        self,
        *,
        data_root: Path,
        grouped_client: GroupedDailyPriceClient | None,
        r2_first_session: date | None = None,
        r2_last_session: date | None = None,
        price_loader: Callable[[str], pd.DataFrame] | None = None,
        min_coverage: float = 0.85,
    ) -> None:
        if (r2_first_session is None) != (r2_last_session is None):
            raise ValueError("both R2 coverage bounds must be supplied together")
        if r2_first_session is None:
            r2_first_session, r2_last_session = _r2_manifest_coverage(data_root)
        assert r2_first_session is not None and r2_last_session is not None
        if r2_first_session > r2_last_session:
            raise ValueError("R2 first session must not be after last session")
        self.data_root = Path(data_root)
        self.grouped_client = grouped_client
        self.r2_first_session = r2_first_session
        self.r2_last_session = r2_last_session
        self.price_loader = price_loader or _default_price_loader
        self.min_coverage = float(min_coverage)
        self._grouped_cache: dict[date, GroupedSessionEvidence] = {}
        self._grouped_wanted: dict[date, frozenset[str]] = {}

    def _inside_r2(self, session: date) -> bool:
        return self.r2_first_session <= session <= self.r2_last_session

    @staticmethod
    def _merge_ticker_series(
        left: pd.Series | None,
        right: pd.Series,
        *,
        ticker: str,
    ) -> pd.Series:
        if left is None or left.empty:
            return right.sort_index()
        overlap = left.index.intersection(right.index)
        if len(overlap):
            lhs = pd.to_numeric(left.loc[overlap], errors="coerce")
            rhs = pd.to_numeric(right.loc[overlap], errors="coerce")
            if not ((lhs - rhs).abs() <= 1e-9).all():
                raise BackfillRefused(
                    f"price-source parity mismatch for {ticker} on overlap"
                )
        merged = pd.concat([left, right])
        return merged[~merged.index.duplicated(keep="last")].sort_index()

    def load(
        self,
        tickers: Iterable[str],
        *,
        start: date,
        end: date,
    ) -> PriceHistoryEvidence:
        wanted = sorted({str(t).strip() for t in tickers if str(t).strip()})
        if not wanted:
            raise BackfillRefused(f"{end}: no price histories requested")
        if start > end:
            raise ValueError("price history start must not be after end")
        prices: dict[str, pd.Series] = {}
        r2_start = max(start, self.r2_first_session)
        r2_end = min(end, self.r2_last_session)
        if r2_start <= r2_end:
            prices.update(
                _load_prices(
                    wanted,
                    loader=self.price_loader,
                    start=r2_start,
                    end=r2_end,
                )
            )

        grouped_maps: dict[date, dict[str, float]] = {}
        grouped_days = [
            session
            for session in sessions_between(start, end)
            if not self._inside_r2(session)
        ]
        if grouped_days and self.grouped_client is None:
            raise BackfillRefused(
                f"{end}: grouped-daily source required outside R2 coverage "
                f"{self.r2_first_session}..{self.r2_last_session}"
            )
        requested_set = frozenset(wanted)
        for session in grouped_days:
            cached = self._grouped_cache.get(session)
            cached_wanted = self._grouped_wanted.get(session, frozenset())
            if cached is None or not requested_set.issubset(cached_wanted):
                assert self.grouped_client is not None
                cached = self.grouped_client.fetch(
                    session,
                    wanted,
                    min_coverage=self.min_coverage,
                )
                self._grouped_cache[session] = cached
                self._grouped_wanted[session] = requested_set
            grouped_maps[session] = dict(cached.closes)
        grouped_history = grouped_session_maps_to_history(grouped_maps)
        for ticker, series in grouped_history.items():
            prices[ticker] = self._merge_ticker_series(
                prices.get(ticker), series, ticker=ticker
            )

        current_source = (
            "massive_stock_day_r2" if self._inside_r2(end) else SOURCE_GROUPED
        )
        receipt = {
            "price_basis": "raw_rth_close",
            "current_source": current_source,
            "history_start": start.isoformat(),
            "history_end": end.isoformat(),
            "r2_first_session": self.r2_first_session.isoformat(),
            "r2_last_session": self.r2_last_session.isoformat(),
            "r2_tickers_loaded": len(prices),
            "grouped_sessions_hydrated": len(grouped_days),
            "grouped_receipts": [
                self._grouped_cache[session].receipt for session in grouped_days
            ],
        }
        return PriceHistoryEvidence(
            prices=prices,
            current_source=current_source,
            receipt=receipt,
        )


class ExchangeBreadthSessionProcessor:
    """One accepted historical session through the production breadth writer."""

    def __init__(
        self,
        *,
        target_sessions: Iterable[date],
        reference_client: MassiveReferenceClient,
        grouped_client: GroupedDailyPriceClient | None,
        data_root: Path | None = None,
        r2_first_session: date | None = None,
        r2_last_session: date | None = None,
        price_loader: Callable[[str], pd.DataFrame] | None = None,
        min_roster_rows: int = 1_000,
        min_operating_rows: int = 500,
        min_identity_coverage: float = 0.90,
        min_price_coverage: float = 0.85,
    ) -> None:
        sessions = tuple(sorted(set(target_sessions)))
        if not sessions:
            raise BackfillRefused("no target sessions were supplied")
        if any(not is_session(session) for session in sessions):
            raise BackfillRefused("target range contains a non-XNYS session")
        self.target_sessions = sessions
        self.target_set = set(sessions)
        self.first_session = sessions[0]
        self.last_session = sessions[-1]
        self.reference_client = reference_client
        self.data_root = Path(data_root or config.data_dir())
        self.output_dir = self.data_root / OUTPUT_DIR
        self.min_roster_rows = int(min_roster_rows)
        self.min_operating_rows = int(min_operating_rows)
        self.min_identity_coverage = float(min_identity_coverage)
        self.min_price_coverage = float(min_price_coverage)

        self.state = _read_json(
            self.output_dir / "_state.json",
            default={
                "schema_version": SCHEMA_VERSION,
                "source_rules_version": SOURCE_RULES_VERSION,
                "accepted_sessions": [],
                "session_counts": {},
            },
        )
        accepted = {str(raw) for raw in self.state.get("accepted_sessions", [])}
        last_raw = self.state.get("last_observed_session")
        if last_raw:
            last_seen = pd.Timestamp(last_raw).date()
            missing_before_tip = [
                session
                for session in sessions
                if session < last_seen and session.isoformat() not in accepted
            ]
            if missing_before_tip:
                raise BackfillRefused(
                    "out of order backfill would move the accepted breadth tip "
                    f"behind {last_seen}: first missing={missing_before_tip[0]}"
                )

        self.alias_table = _load_alias_table(self.data_root)
        self.intervals = _read_parquet(self.output_dir / "universe_intervals.parquet")
        existing_splits = _read_parquet(self.output_dir / "source_splits.parquet")
        split_bundle = reference_client.fetch_splits(
            self.first_session, self.last_session
        )
        self.split_receipt = split_bundle.receipt
        self.source_splits = _merge_source_splits(
            existing_splits, _source_split_frame(split_bundle.rows)
        )
        self.price_history = HybridPriceHistory(
            data_root=self.data_root,
            grouped_client=grouped_client,
            r2_first_session=r2_first_session,
            r2_last_session=r2_last_session,
            price_loader=price_loader,
            min_coverage=self.min_price_coverage,
        )

    def _counts(self, observed: pd.DataFrame) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for universe_key in (UNIVERSE_OPERATING, UNIVERSE_ALL_ISSUES):
            rows = observed[observed["universe_key"] == universe_key]
            listed_n = int(len(rows))
            resolved_n = int(rows["identity_resolved"].fillna(False).sum())
            counts[universe_key] = {
                "listed_n": listed_n,
                "resolved_identity_n": resolved_n,
            }
        if counts[UNIVERSE_OPERATING]["listed_n"] < self.min_operating_rows:
            raise BackfillRefused(
                "operating-company row floor not met: "
                f"{counts[UNIVERSE_OPERATING]['listed_n']} < "
                f"{self.min_operating_rows}"
            )
        for universe_key, values in counts.items():
            listed_n = values["listed_n"]
            coverage = values["resolved_identity_n"] / listed_n if listed_n else 0.0
            if coverage < self.min_identity_coverage:
                raise BackfillRefused(
                    f"{universe_key} identity coverage {coverage:.3f} below "
                    f"{self.min_identity_coverage:.3f}"
                )
        return counts

    def _reconcile_existing_generation(self, session: date) -> SessionAcceptance:
        session_key = session.isoformat()
        counts = self.state.get("session_counts")
        if not isinstance(counts, Mapping) or session_key not in counts:
            raise BackfillRefused(
                f"{session}: accepted state lacks session-bound denominator counts"
            )
        timestamp = pd.Timestamp(session)
        for filename in ("nyse_operating.parquet", "nyse_all_issues.parquet"):
            frame = _read_parquet(self.output_dir / filename)
            if frame.empty:
                raise BackfillRefused(
                    f"{session}: accepted generation is missing {filename}"
                )
            index = pd.to_datetime(frame.index, errors="coerce")
            if timestamp not in pd.DatetimeIndex(index).tz_localize(None).normalize():
                raise BackfillRefused(
                    f"{session}: accepted generation frame {filename} lacks session"
                )
        tip = str(self.state.get("last_observed_session") or "")
        latest_receipt = _read_json(self.output_dir / "_receipt.json", default={})
        if tip == session_key:
            if latest_receipt.get("accepted_session") != session_key:
                raise BackfillRefused(
                    f"{session}: latest receipt does not match accepted state tip"
                )
            if latest_receipt.get("authority") != AUTHORITY:
                raise BackfillRefused(
                    f"{session}: latest receipt authority does not match breadth law"
                )
        receipt = {
            "accepted_session": session_key,
            "reconciled_existing_generation": True,
            "state_tip": tip,
            "authority": AUTHORITY,
            "session_counts": counts[session_key],
        }
        return SessionAcceptance(
            session=session,
            roster_reconciled=True,
            price_reconciled=True,
            published=True,
            source="accepted_generation_reconciliation",
            receipt=receipt,
        )

    def __call__(self, session: date) -> SessionAcceptance:
        if session not in self.target_set:
            raise BackfillRefused(f"session {session} is outside the target range")
        accepted = {str(raw) for raw in self.state.get("accepted_sessions", [])}
        if session.isoformat() in accepted:
            return self._reconcile_existing_generation(session)
        last_raw = self.state.get("last_observed_session")
        if last_raw:
            last_seen = pd.Timestamp(last_raw).date()
            previous = last_session_on_or_before(
                date.fromordinal(session.toordinal() - 1)
            )
            if session <= last_seen or previous != last_seen:
                raise BackfillRefused(
                    f"session {session} is out of order after accepted tip {last_seen}"
                )

        roster_bundle = self.reference_client.fetch_roster(
            session, min_rows=self.min_roster_rows
        )
        observed = normalize_roster(
            list(roster_bundle.rows),
            session,
            alias_table=self.alias_table,
        )
        if observed.empty:
            raise BackfillRefused(f"{session}: normalized XNYS roster is empty")
        counts = self._counts(observed)
        previous = last_session_on_or_before(date.fromordinal(session.toordinal() - 1))
        candidate_intervals = update_membership_intervals(
            self.intervals,
            observed,
            session,
            previous_session=previous,
            last_observed_session=self.state.get("last_observed_session"),
        )
        candidate_splits, resolved_splits, unresolved_splits = _resolve_split_entities(
            self.source_splits, candidate_intervals
        )
        relevant = candidate_intervals[
            (
                pd.to_datetime(candidate_intervals["valid_to_session"])
                >= pd.Timestamp(self.first_session)
            )
            & (
                pd.to_datetime(candidate_intervals["valid_from_session"])
                <= pd.Timestamp(session)
            )
        ]
        tickers = sorted(set(relevant["ticker"].dropna().astype(str)))
        price_evidence = self.price_history.load(
            tickers,
            start=self.first_session,
            end=session,
        )
        frames, diagnostics = _build_frames(
            intervals=candidate_intervals,
            splits=resolved_splits,
            prices=price_evidence.prices,
            observation_session=session,
            state=self.state,
            counts=counts,
        )
        latest_ts = pd.Timestamp(session)
        for universe_key, frame in frames.items():
            if latest_ts not in frame.index:
                raise BackfillRefused(
                    f"{session}: {universe_key} aggregate lacks accepted session"
                )
            latest = frame.loc[latest_ts]
            listed_n = counts[universe_key]["listed_n"]
            priced_n = int(latest.get("priced_n", 0) or 0)
            price_coverage = priced_n / listed_n if listed_n else 0.0
            counts[universe_key]["priced_n"] = priced_n
            counts[universe_key]["price_coverage_pct"] = round(
                price_coverage * 100.0, 4
            )
            counts[universe_key]["seasoned_n"] = int(latest.get("seasoned_n", 0) or 0)
            if price_coverage < self.min_price_coverage:
                raise BackfillRefused(
                    f"{session}: {universe_key} price coverage "
                    f"{price_coverage:.3f} below {self.min_price_coverage:.3f}"
                )

        accepted_sessions = sorted(accepted | {session.isoformat()})
        session_counts = dict(self.state.get("session_counts") or {})
        session_counts[session.isoformat()] = counts
        candidate_state = {
            "schema_version": SCHEMA_VERSION,
            "source_rules_version": SOURCE_RULES_VERSION,
            "last_observed_session": session.isoformat(),
            "accepted_sessions": accepted_sessions,
            "session_counts": session_counts,
            "last_source_clock": datetime.now(timezone.utc).isoformat(),
        }
        unresolved_rows = observed[~observed["identity_resolved"].fillna(False)]
        unresolved_examples = sorted(set(unresolved_rows["ticker"].astype(str)))[:10]
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "accepted": True,
            "accepted_session": session.isoformat(),
            "source_clock": candidate_state["last_source_clock"],
            "source_rules_version": SOURCE_RULES_VERSION,
            "authority": AUTHORITY,
            "price_basis": PRICE_BASIS,
            "universes": counts,
            "unresolved_identity_count": int(len(unresolved_rows)),
            "unresolved_identity_examples": unresolved_examples,
            "roster": roster_bundle.receipt,
            "splits": {
                **self.split_receipt,
                "cache_rows": int(len(candidate_splits)),
                "resolved_rows": (
                    int(candidate_splits["entity_key"].notna().sum())
                    if not candidate_splits.empty
                    else 0
                ),
                "unresolved_relevant_count": len(unresolved_splits),
                "unresolved_relevant_examples": unresolved_splits[:10],
            },
            "diagnostics": diagnostics,
            "backfill": {
                "target_start": self.first_session.isoformat(),
                "target_end": self.last_session.isoformat(),
                "price_source": price_evidence.current_source,
                "price_history": price_evidence.receipt,
            },
        }
        _promote_generation(
            self.output_dir,
            intervals=candidate_intervals,
            splits=candidate_splits,
            frames=frames,
            state=candidate_state,
            receipt=receipt,
        )
        self.intervals = candidate_intervals
        self.source_splits = candidate_splits
        self.state = candidate_state
        return SessionAcceptance(
            session=session,
            roster_reconciled=True,
            price_reconciled=True,
            published=True,
            source=price_evidence.current_source,
            receipt=receipt,
        )


def _default_state_path() -> Path:
    return Path(config.data_dir()) / "exchange_breadth" / DEFAULT_STATE_NAME


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="first calendar date (YYYY-MM-DD)")
    parser.add_argument("--end", help="last completed calendar date (YYYY-MM-DD)")
    parser.add_argument(
        "--recent-sessions",
        type=int,
        default=DEFAULT_RECENT_SESSIONS,
        help=f"default recent seed size (default: {DEFAULT_RECENT_SESSIONS})",
    )
    parser.add_argument("--max-sessions", type=int, default=None)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state-path", type=Path, default=None)
    return parser


def _report_payload(report: BackfillReport) -> dict[str, Any]:
    return {
        "requested_sessions": [d.isoformat() for d in report.requested_sessions],
        "processed_sessions": [d.isoformat() for d in report.processed_sessions],
        "skipped_sessions": [d.isoformat() for d in report.skipped_sessions],
        "remaining_sessions": [d.isoformat() for d in report.remaining_sessions],
        "completed_total": report.completed_total,
        "dry_run": report.dry_run,
        "state_path": report.state_path,
    }


def _configured_vendor_key(settings: Mapping[str, Any]) -> str | None:
    breadth_cfg = settings.get("exchange_breadth")
    if not isinstance(breadth_cfg, Mapping):
        breadth_cfg = {}
    env_name = str(breadth_cfg.get("api_key_env") or "POLYGON_API_KEY")
    return config.secret(env_name) or config.secret("MASSIVE_API_KEY")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    sessions = enumerate_backfill_sessions(
        start=args.start,
        end=args.end,
        recent_sessions=args.recent_sessions,
    )
    state_path = args.state_path or _default_state_path()
    if args.dry_run:
        report = run_backfill(
            sessions,
            processor=lambda session: SessionAcceptance(
                session=session,
                roster_reconciled=False,
                price_reconciled=False,
                published=False,
                source="dry_run",
                receipt={},
            ),
            state_path=state_path,
            max_sessions=args.max_sessions,
            resume=args.resume,
            dry_run=True,
        )
        print(json.dumps(_report_payload(report), indent=2))
        return 0

    preview_state = _load_state(state_path, resume=args.resume)
    completed_preview = {
        str(raw) for raw in preview_state.get("completed_sessions", [])
    }
    pending_preview = [
        session for session in sessions if session.isoformat() not in completed_preview
    ]
    if not pending_preview or args.max_sessions == 0:
        report = run_backfill(
            sessions,
            processor=lambda session: (_ for _ in ()).throw(
                AssertionError(f"unexpected processing of {session}")
            ),
            state_path=state_path,
            max_sessions=args.max_sessions,
            resume=args.resume,
            dry_run=False,
        )
        print(json.dumps(_report_payload(report), indent=2))
        return 0

    settings = config.load()
    breadth_cfg = settings.get("exchange_breadth")
    if not isinstance(breadth_cfg, Mapping):
        breadth_cfg = {}
    key = _configured_vendor_key(settings)
    if not key:
        raise BackfillRefused(
            "POLYGON_API_KEY/MASSIVE_API_KEY is required for historical rosters"
        )
    base_url = str(
        breadth_cfg.get("base_url")
        or (settings.get("polygon") or {}).get("base_url")
        or DEFAULT_BASE_URL
    )
    timeout_s = float(breadth_cfg.get("timeout_s", 60))
    reference_client = MassiveReferenceClient(
        key,
        base_url=base_url,
        max_pages=int(breadth_cfg.get("max_pages", 50)),
        timeout_s=timeout_s,
    )
    grouped_client = GroupedDailyPriceClient(
        key,
        base_url=base_url,
        timeout_s=timeout_s,
    )
    processor = ExchangeBreadthSessionProcessor(
        target_sessions=sessions,
        reference_client=reference_client,
        grouped_client=grouped_client,
        min_roster_rows=int(breadth_cfg.get("roster_min_rows", 1_000)),
        min_operating_rows=int(breadth_cfg.get("operating_min_rows", 500)),
        min_identity_coverage=float(breadth_cfg.get("min_identity_coverage", 0.90)),
        min_price_coverage=float(breadth_cfg.get("min_price_coverage", 0.85)),
    )
    report = run_backfill(
        sessions,
        processor=processor,
        state_path=state_path,
        max_sessions=args.max_sessions,
        resume=args.resume,
        dry_run=False,
    )
    print(json.dumps(_report_payload(report), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
