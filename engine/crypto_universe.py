"""Display-only crypto universe and dated snapshot coverage.

The collector's asset files accrue independently; an old rank must not re-enter
a newer cross-section. Source bytes are never modified by this read projection.
No trading or allocation authority is owned here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from lib import config


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return out if np.isfinite(out) else None


def _state(change_30d: float | None, change_7d: float | None) -> tuple[str, str]:
    """Return restrained display state and tone from price follow-through."""
    guide = change_30d if change_30d is not None else change_7d
    if guide is None:
        return "Building", "neutral"
    if guide >= 15:
        return "Leading", "bull"
    if guide >= 3:
        return "Firm", "bull"
    if guide <= -15:
        return "Weak", "bear"
    if guide <= -3:
        return "Fading", "bear"
    return "Range", "neutral"


def _history_chip(days: int) -> str:
    if days >= 90:
        return "90D"
    if days >= 30:
        return f"{days}D"
    return "Building"


def load_universe_snapshot(top_n: int = 50, root: Path | None = None) -> dict:
    """Read one latest recorded cross-section, with inspectable exclusions.

    `as_of` is the collector observation date, not a live quote or a provider
    publication-time guarantee. An unreadable/invalid latest row is never
    replaced with an older valid quote. Older files remain in the source store.
    """
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    root = root or (config.data_dir() / "crypto_universe")
    observations: list[tuple[dict, pd.DataFrame, pd.Series]] = []
    excluded: list[dict] = []
    today = pd.Timestamp.now(tz="UTC").normalize()
    for path in sorted(root.glob("market_*.parquet")) if root.exists() else []:
        receipt = {"file": path.name, "symbol": path.stem.removeprefix("market_").upper(),
                   "id": None, "source": None, "as_of": None}
        try:
            frame = pd.read_parquet(path)
            if frame.empty:
                excluded.append({**receipt, "reason": "EMPTY_HISTORY"})
                continue
            frame.index = pd.to_datetime(frame.index, utc=True, errors="raise")
            if frame.index.hasnans:
                raise ValueError("missing observation date")
            frame = frame.sort_index(kind="stable")
            # A collector observation is daily; repeated dates do not create
            # additional history coverage. Keep the last recorded row per day.
            frame.index = frame.index.normalize()
            frame = frame.loc[~frame.index.duplicated(keep="last")]
            current = frame.iloc[-1]
            receipt.update({
                "id": str(current.get("coin_id") or path.stem.removeprefix("market_")),
                "source": str(current.get("source") or "Unknown"),
                "symbol": str(current.get("symbol") or "").upper(),
                "as_of": str(frame.index[-1].date()),
            })
            if frame.index[-1] > today:
                excluded.append({**receipt, "reason": "FUTURE_OBSERVATION"})
                continue
            observations.append((receipt, frame, current))
        except Exception:
            excluded.append({**receipt, "reason": "UNREADABLE_HISTORY"})

    as_of = max((r[0]["as_of"] for r in observations), default=None)
    rows: list[dict] = []
    for receipt, frame, current in observations:
        rank = _number(current.get("market_cap_rank"))
        price = _number(current.get("current_price"))
        if receipt["as_of"] != as_of:
            reason = "OLDER_SNAPSHOT"
        elif rank is None or not rank.is_integer() or rank < 1:
            reason = "INVALID_RANK"
        elif rank > top_n:
            reason = "OUTSIDE_RANK_RANGE"
        elif price is None or price <= 0:
            reason = "INVALID_LATEST_PRICE"
        elif not receipt["symbol"]:
            reason = "MISSING_ASSET_IDENTITY"
        else:
            reason = None
        if reason:
            excluded.append({**receipt, "reason": reason})
            continue

        # Files are keyed by ticker, not globally unique asset identity. Without
        # a canonical crosswalk, a source/id change breaks historical continuity.
        same_identity = pd.Series(True, index=frame.index)
        for column, value in (("source", receipt["source"]), ("coin_id", receipt["id"])):
            if column in frame:
                same_identity &= frame[column].eq(value).fillna(False)
        breaks = np.flatnonzero(~same_identity.to_numpy())
        start = int(breaks[-1]) + 1 if len(breaks) else 0
        history_frame = frame.iloc[start:]
        prices = pd.to_numeric(history_frame["current_price"], errors="coerce")
        prices = prices.loc[np.isfinite(prices) & (prices > 0)]
        hist = prices.tail(90)
        c24 = _number(current.get("change_24h_pct"))
        c7 = _number(current.get("change_7d_pct"))
        c30 = _number(current.get("change_30d_pct"))
        state, tone = _state(c30, c7)
        rows.append({
            "id": receipt["id"], "source": receipt["source"],
            "symbol": receipt["symbol"],
            "name": str(current.get("name") or receipt["symbol"]),
            "rank": int(rank), "price": price,
            "change_24h": c24, "change_7d": c7, "change_30d": c30,
            "market_cap": _number(current.get("market_cap")),
            "volume": _number(current.get("total_volume")),
            "state": state, "tone": tone,
            "history_days": len(hist), "history_chip": _history_chip(len(hist)),
            "history_reset": "SOURCE_IDENTITY_CHANGED" if start else None,
            "spark_dates": [str(x.date()) for x in hist.index],
            "spark_values": [round(float(x), 8) for x in hist.to_numpy()],
            "as_of": receipt["as_of"],
        })
    rows = sorted(rows, key=lambda x: (x["rank"], x["symbol"]))[:top_n]
    return {"as_of": as_of, "rows": rows, "excluded": excluded,
            "requested": top_n, "observed": len(observations),
            "sources": sorted({row["source"] for row in rows})}


def load_universe(top_n: int = 50, root: Path | None = None) -> list[dict]:
    """Compatibility projection of the same dated snapshot, not another loader."""
    return load_universe_snapshot(top_n, root)["rows"]


def breadth_read(rows: list[dict]) -> dict:
    """Share with a positive reported 30-day return, not altseason or forecast.

    A missing return is excluded, never counted as zero or a negative vote.
    The existing minimum of ten assets and accrued-history gate are retained.
    """
    as_of = max((r.get("as_of") for r in rows if r.get("as_of")), default=None)
    eligible = []
    for row in rows:
        days = _number(row.get("history_days"))
        change = _number(row.get("change_30d"))
        if (days is not None and days >= 30 and change is not None
                and (as_of is None or row.get("as_of") == as_of)):
            eligible.append(change)
    positive = sum(change > 0 for change in eligible)
    receipt = {"as_of": as_of, "eligible": len(eligible), "required": 10,
               "excluded": len(rows) - len(eligible), "positive": positive,
               "basis": "reported_30d_return_positive"}
    if len(eligible) < 10:
        return {**receipt, "available": False, "value": None,
                "state": "Building history", "tone": "neutral"}
    pct = round(100 * positive / len(eligible))
    return {**receipt, "available": True, "value": pct,
            "state": "Broad" if pct >= 60 else ("Narrow" if pct <= 40 else "Mixed"),
            "tone": "bull" if pct >= 60 else ("bear" if pct <= 40 else "neutral")}
