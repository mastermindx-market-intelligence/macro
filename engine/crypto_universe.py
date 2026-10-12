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

from engine import btc_signals
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


# Coinbase listing-era floors (config.yml coinbase.eth_earliest / sol_earliest).
# BTC-native legs stay off this path. Allocation is not a transfer output.
_PRICE_PATH_ASSETS = {"ETH": "eth_earliest", "SOL": "sol_earliest"}
_PRICE_PATH_COLUMNS = (
    "asset", "tier", "authority",
    "momentum", "momentum_state",
    "risk_index", "risk_oscillator", "risk_regime",
)


def price_path_listing_floor(asset: str) -> pd.Timestamp:
    """Calendar date before which an ETH or SOL close is not a listing observation."""
    key = _PRICE_PATH_ASSETS.get(str(asset).strip().upper())
    if key is None:
        raise ValueError("listing floor is defined for ETH and SOL only")
    floor = pd.Timestamp(config.load()["coinbase"][key])
    if floor.tzinfo is not None:
        floor = floor.tz_convert("UTC").tz_localize(None)
    return floor.normalize()


def _daily_close(close: pd.Series) -> pd.Series:
    """A unique, increasing, midnight daily close. Non-numeric cells become missing."""
    if not isinstance(close, pd.Series):
        raise TypeError("close must be a Series")
    if not isinstance(close.index, pd.DatetimeIndex):
        raise TypeError("close index must be a DatetimeIndex")
    out = pd.to_numeric(close, errors="coerce").astype(float)
    idx = out.index
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
        out = pd.Series(out.to_numpy(), index=idx)
    if not idx.is_monotonic_increasing or idx.has_duplicates:
        raise ValueError("daily close index must be unique and increasing")
    if len(idx) and not idx.equals(idx.normalize()):
        raise ValueError("daily close timestamps must be normalized to midnight")
    return out


def display_price_path(close: pd.Series, asset: str) -> pd.DataFrame:
    """Display-tier momentum and risk for one ETH or SOL daily close.

    Calls `btc_signals.momentum` and `btc_signals.risk` on the price path only.
    SOPR, short-term cost basis, intraday vol, ETF flow, and funding are not
    passed, so those votes are not created. No allocation, size, or exposure
    column is returned.

    A close before the asset's Coinbase listing floor, a missing close, and a
    non-positive close are unavailable. They are not filled, not replaced with
    zero, and not fed to the signal functions. The signal functions carry a
    state across gaps and park a quiet risk oscillator at 0.5; this frame
    still publishes unavailable on a row that had no usable close.
    """
    label = str(asset).strip().upper()
    if label not in _PRICE_PATH_ASSETS:
        raise ValueError("display price path is ETH or SOL only")
    series = _daily_close(close)
    floor = price_path_listing_floor(label)
    values = series.to_numpy(dtype=float)
    usable_row = (series.index >= floor) & np.isfinite(values) & (values > 0)
    usable = series.loc[usable_row]

    momentum = pd.Series(np.nan, index=series.index, dtype=float)
    risk_index = pd.Series(np.nan, index=series.index, dtype=float)
    risk_oscillator = pd.Series(np.nan, index=series.index, dtype=float)
    momentum_state = pd.Series("unavailable", index=series.index, dtype=object)
    risk_regime = pd.Series("unavailable", index=series.index, dtype=object)

    if not usable.empty:
        # Price only. Omitting the Bitcoin-native keys keeps those legs off.
        inputs = {"price": pd.DataFrame({"close": usable})}
        vector = config.load()["vector"]
        mom = btc_signals.momentum(inputs, vector["momentum"])
        rk = btc_signals.risk(inputs, mom["momentum"], vector["risk"])
        momentum.loc[usable.index] = mom["momentum"].to_numpy(dtype=float)
        risk_index.loc[usable.index] = rk["risk_index"].to_numpy(dtype=float)
        risk_oscillator.loc[usable.index] = rk["risk_oscillator"].to_numpy(dtype=float)
        momentum_state.loc[usable.index] = mom["momentum_state"].astype(object).to_numpy()
        risk_regime.loc[usable.index] = rk["risk_regime"].astype(object).to_numpy()

    blocked = ~usable_row
    momentum.loc[blocked] = np.nan
    risk_index.loc[blocked] = np.nan
    risk_oscillator.loc[blocked] = np.nan
    momentum_state.loc[blocked] = "unavailable"
    risk_regime.loc[blocked] = "unavailable"

    frame = pd.DataFrame(
        {
            "asset": label,
            "tier": "display",
            "authority": "none",
            "momentum": momentum,
            "momentum_state": momentum_state,
            "risk_index": risk_index,
            "risk_oscillator": risk_oscillator,
            "risk_regime": risk_regime,
        },
        index=series.index,
    )
    return frame.loc[:, list(_PRICE_PATH_COLUMNS)]
