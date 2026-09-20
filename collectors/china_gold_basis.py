"""Close-aligned source plane for the China physical-gold premium monitor.

This adapter reuses two already-governed provider surfaces:

* Tushare sge_daily -> SGE Au99.99 close in RMB/gram.
* Massive/Polygon Currencies -> C:XAUCNY minute aggregates.

It does not compute the premium. The product engine owns that calculation. The
only timestamp synthesis here is explicit: Tushare defines an SGE trade-date
daily row across the prior-night 20:00-02:30 session plus the current
09:00-15:30 session, so its final trade-date close is stamped at 15:30
Asia/Shanghai (=07:30 UTC) for the like-clock global comparison.

Massive data rights are governed by research/licenses/MASSIVE_ENTITLEMENT_RECORD.md.
Tushare compliance is governed by
DEC:CNLI-TUSHARE-COMPLIANCE-IS-CHAIRMAN-VERIFIED-PRIVATE. This module therefore
checks technical credential/access state only and does not recreate license gates.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import logging

import numpy as np
import pandas as pd

from collectors import tushare_client
from collectors.base import Adapter
from lib import config, store


_SGE_CODE = "Au99.99"
_MASSIVE_TICKER = "C:XAUCNY"
_CLOSE_HOUR_UTC = 7
_CLOSE_MINUTE_UTC = 30
_REFRESH_DAYS = 13  # today + 13 prior days = one <=14-day minute-bar request
_COLD_START_DAYS = 90  # enough calendar depth for honest 30-session product statistics
_MAX_MASSIVE_RESULTS = 50_000

log = logging.getLogger("collector.gold_china_basis")


def _date_chunks(start, end, *, max_days: int = 14, newest_first: bool = False):
    """Yield inclusive windows small enough for one minute-aggregate response.

    Historical helpers default to ascending order. The live collector requests
    newest-first so an older-history entitlement/gap can never prevent the current
    Shanghai-close point from being admitted first.
    """
    if max_days < 1:
        raise ValueError("max_days must be >= 1")
    if newest_first:
        cursor = end
        while cursor >= start:
            chunk_start = max(start, cursor - timedelta(days=max_days - 1))
            yield chunk_start, cursor
            cursor = chunk_start - timedelta(days=1)
        return

    cursor = start
    while cursor <= end:
        stop = min(end, cursor + timedelta(days=max_days - 1))
        yield cursor, stop
        cursor = stop + timedelta(days=1)


def _utc_close_for_trade_date(value) -> pd.Timestamp | None:
    try:
        day = pd.to_datetime(str(value), format="%Y%m%d", errors="raise")
    except (TypeError, ValueError, OverflowError):
        return None
    return pd.Timestamp(
        year=day.year,
        month=day.month,
        day=day.day,
        hour=_CLOSE_HOUR_UTC,
        minute=_CLOSE_MINUTE_UTC,
    )


def _sge_au9999_frame(raw: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize Tushare sge_daily rows to close-aligned RMB/gram observations."""
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        return pd.DataFrame(columns=["rmb_per_g"])
    required = {"ts_code", "trade_date", "close"}
    if not required.issubset(raw.columns):
        return pd.DataFrame(columns=["rmb_per_g"])

    rows: list[tuple[pd.Timestamp, float]] = []
    for _, row in raw.iterrows():
        if str(row.get("ts_code") or "").strip() != _SGE_CODE:
            continue
        stamp = _utc_close_for_trade_date(row.get("trade_date"))
        value = pd.to_numeric(row.get("close"), errors="coerce")
        if stamp is None or not np.isfinite(value) or float(value) <= 0:
            continue
        rows.append((stamp, float(value)))
    if not rows:
        return pd.DataFrame(columns=["rmb_per_g"])
    out = pd.DataFrame(
        {"rmb_per_g": [v for _, v in rows]},
        index=pd.DatetimeIndex([ts for ts, _ in rows]),
    )
    return out[~out.index.duplicated(keep="last")].sort_index()


def _massive_xaucny_frame(payload: object, *, tolerance_minutes: int = 2) -> pd.DataFrame:
    """Pick one XAUCNY minute bar nearest 07:30 UTC for each represented UTC date."""
    if not isinstance(payload, dict):
        return pd.DataFrame(columns=["cny_per_oz"])
    results = payload.get("results")
    if not isinstance(results, list):
        return pd.DataFrame(columns=["cny_per_oz"])

    candidates: dict[pd.Timestamp, tuple[float, pd.Timestamp, float]] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        try:
            stamp = pd.Timestamp(int(row["t"]), unit="ms", tz="UTC")
            close = float(row["c"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not np.isfinite(close) or close <= 0:
            continue
        day = stamp.normalize()
        target = day + pd.Timedelta(hours=_CLOSE_HOUR_UTC, minutes=_CLOSE_MINUTE_UTC)
        distance = abs((stamp - target).total_seconds()) / 60.0
        if distance > float(tolerance_minutes):
            continue
        prior = candidates.get(day)
        if prior is None or distance < prior[0] or (
            distance == prior[0] and stamp < prior[1]
        ):
            candidates[day] = (distance, stamp, close)

    if not candidates:
        return pd.DataFrame(columns=["cny_per_oz"])
    rows = sorted(
        (
            target_day + pd.Timedelta(hours=_CLOSE_HOUR_UTC, minutes=_CLOSE_MINUTE_UTC),
            value[2],
        )
        for target_day, value in candidates.items()
    )
    index = pd.DatetimeIndex([ts.tz_convert(None) for ts, _ in rows])
    return pd.DataFrame({"cny_per_oz": [v for _, v in rows]}, index=index)


class ChinaGoldBasisAdapter(Adapter):
    """Accrue the two raw legs needed for the close-aligned indicative basis."""

    name = "gold_china_basis"
    group = "gold_china_basis"
    stale_after_days = 4
    normalize_index = False

    def __init__(self) -> None:
        self.massive_key = (
            config.secret("POLYGON_API_KEY")
            or config.secret("MASSIVE_API_KEY")
        )
        if not tushare_client.enabled() or not self.massive_key:
            self.expected_failure = (
                "Tushare and Massive currency credentials are required for "
                "the China gold close-aligned source plane"
            )

    def validate(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Preserve the 07:30 UTC observation timestamp instead of day-normalizing it."""
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError(f"{self.name}/{name}: empty frame")
        out = df.copy()
        idx = pd.to_datetime(out.index, errors="coerce", utc=True)
        out.index = pd.DatetimeIndex(idx).tz_convert(None)
        out = out[~out.index.isna()]
        out = out[~out.index.duplicated(keep="last")].sort_index().dropna(how="all")
        if out.empty:
            raise ValueError(f"{self.name}/{name}: all-NaN after cleaning")
        return out

    def _stored_aligned_points(self) -> int:
        """Count dates that already have both raw legs in the persisted store."""
        try:
            sge = store.read(self.group, "sge_au9999")
            global_spot = store.read(self.group, "xaucny_spot")
            if (
                sge is None
                or global_spot is None
                or sge.empty
                or global_spot.empty
            ):
                return 0
            sge_days = pd.DatetimeIndex(
                pd.to_datetime(sge.index, errors="coerce", utc=True)
            ).normalize()
            global_days = pd.DatetimeIndex(
                pd.to_datetime(global_spot.index, errors="coerce", utc=True)
            ).normalize()
            sge_days = sge_days[~sge_days.isna()]
            global_days = global_days[~global_days.isna()]
            return len(sge_days.unique().intersection(global_days.unique()))
        except Exception:
            return 0

    def _fetch_window_days(
        self,
        *,
        full_history: bool,
        today: date | None = None,
    ) -> int:
        """Bound refreshes while healing both freshness gaps and history depth."""
        if full_history:
            return 370

        today = today or datetime.now(timezone.utc).date()
        latest = [
            store.last_date(self.group, name)
            for name in ("sge_au9999", "xaucny_spot")
        ]
        if any(value is None for value in latest):
            return _COLD_START_DAYS

        oldest = min(value for value in latest if value is not None)
        gap_days = max(0, (today - oldest).days)
        if gap_days > _REFRESH_DAYS:
            # Re-cover the whole outage plus overlap, while keeping an accidental
            # multi-year gap bounded to the explicit full-history horizon.
            return min(
                370,
                max(_COLD_START_DAYS, gap_days + 14),
            )

        # A successful partial cold-start must not permanently strand the chart
        # below the 30-session statistics floor. Keep asking for cold-start depth
        # until both stored legs overlap on at least 30 observation dates.
        if self._stored_aligned_points() < 30:
            return _COLD_START_DAYS

        return _REFRESH_DAYS

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        if not tushare_client.enabled() or not self.massive_key:
            raise RuntimeError(
                "provider credentials unavailable for China gold close-aligned sources"
            )

        now = datetime.now(timezone.utc)
        days = self._fetch_window_days(
            full_history=full_history,
            today=now.date(),
        )
        start = (now - timedelta(days=days)).date()
        end = now.date()

        raw_sge = tushare_client.query(
            "sge_daily",
            ts_code=_SGE_CODE,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            fields="ts_code,trade_date,close",
        )
        sge = _sge_au9999_frame(raw_sge)
        if sge.empty:
            raise RuntimeError("sge_daily returned no valid Au99.99 close rows")

        base = str(config.load().get("polygon", {}).get("base_url") or "https://api.massive.com")
        pieces: list[pd.DataFrame] = []
        for chunk_start, chunk_end in _date_chunks(
            start, end, max_days=14, newest_first=True
        ):
            url = (
                f"{base.rstrip('/')}/v2/aggs/ticker/{_MASSIVE_TICKER}/range/1/minute/"
                f"{chunk_start.isoformat()}/{chunk_end.isoformat()}"
            )
            try:
                response = self.http_get(
                    url,
                    retries=3,
                    timeout=60,
                    headers={"Authorization": f"Bearer {self.massive_key}"},
                    params={
                        "adjusted": "true",
                        "sort": "asc",
                        "limit": _MAX_MASSIVE_RESULTS,
                    },
                )
                piece = _massive_xaucny_frame(response.json(), tolerance_minutes=2)
            except Exception as exc:
                # Once the current chunk has produced an aligned point, an older
                # history failure is a DEPTH degradation, not a reason to black
                # out today's product. The next nightly keeps attempting depth
                # until the 30-session readiness floor is reached.
                if pieces:
                    log.warning(
                        "Massive XAUCNY historical chunk %s..%s unavailable; "
                        "keeping newer close-aligned rows (%s)",
                        chunk_start, chunk_end, exc,
                    )
                    continue
                raise
            if not piece.empty:
                pieces.append(piece)

        if not pieces:
            raise RuntimeError("Massive XAUCNY returned no Shanghai-close-aligned bars")
        xaucny = pd.concat(pieces).sort_index()
        xaucny = xaucny[~xaucny.index.duplicated(keep="last")]

        return {
            "sge_au9999": sge,
            "xaucny_spot": xaucny,
        }
