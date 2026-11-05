"""Observation-date-bounded flow/options/gamma receipts (Rotation Events v2).

These are context only, never event classifier or creation-gate inputs. Each value
keeps its own observation date. An explicit as_of bounds rows BEFORE transforms or
last-nonnull selection; omission retains the live latest-observation read.

Observation date is not availability time: these legacy stores do not establish
when a value first became available. Every receipt preserves that limitation.
"""
from __future__ import annotations

import logging
import math
from datetime import date
from pathlib import Path

import pandas as pd

from lib import config, nyse_calendar

log = logging.getLogger(__name__)


def _date_limit(as_of: str | date | None) -> pd.Timestamp | None:
    if as_of is None:
        return None
    stamp = pd.Timestamp(as_of)
    if pd.isna(stamp):
        raise ValueError("missing observation cutoff")
    if stamp.tzinfo is not None:
        stamp = stamp.tz_localize(None)
    return stamp.normalize()


def _retained_rows(df: pd.DataFrame, as_of: str | date | None) -> pd.DataFrame:
    """Resolve daily observation labels, cut off, then validate/order retained rows."""
    limit = _date_limit(as_of)
    if df.empty:
        return df.copy()
    if pd.api.types.is_numeric_dtype(df.index.dtype):
        raise ValueError("observation dates missing")
    dates = pd.DatetimeIndex(pd.to_datetime(df.index, errors="coerce"))
    if dates.isna().any():
        raise ValueError("invalid observation date")
    if dates.tz is not None:
        dates = dates.tz_localize(None)
    out = df.copy()
    out.index = dates.normalize()
    if limit is not None:
        out = out.loc[out.index <= limit]
    # Future duplicate rows must not poison a valid historical prefix.
    if out.index.has_duplicates:
        raise ValueError("duplicate retained observation dates")
    return out.sort_index()


def _receipt(value_key: str, date_key: str, value, value_date, *,
             as_of: str | date | None, latest_row=None,
             note: str | None = None, window: dict | None = None) -> dict:
    """Qualify observation freshness without manufacturing publication clocks."""
    requested = None
    if as_of is not None:
        try:
            requested = _date_limit(as_of).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            requested = str(as_of)
    observed = pd.Timestamp(value_date).date().isoformat() if value_date is not None else None
    latest = pd.Timestamp(latest_row).date().isoformat() if latest_row is not None else None
    reference = requested if as_of is not None else latest
    status = "UNAVAILABLE"
    if observed is not None:
        status = "AS_OF" if as_of is not None else "AVAILABLE"
        if reference is not None and observed < reference:
            status = "STALE"
            stale_note = f"stale observation: value dated {observed}; reference date {reference}"
            note = f"{note}; {stale_note}" if note else stale_note
    out = {
        value_key: value, date_key: observed, "status": status,
        "requested_as_of": requested, "latest_row_as_of": latest,
        "availability": {"status": "UNKNOWN", "available_at": None},
    }
    if note:
        out["note"] = note
    if window is not None:
        out["window"] = window
    return out


# ------------------------------------------------------------------ etf flow ----

def etf_flow_receipt(etf: str, data_dir: Path | None = None, *,
                     as_of: str | date | None = None) -> dict:
    """Implied ETF flow, retaining the existing last-five-valid-change formula.

    implied = so_mn.diff() * nav ($M). The legacy flow_5d_mn field remains the
    sum of the last five nonnull changes, which may span more than five sessions.
    The receipt now discloses the actual change dates and observation count.
    NEVER reads etf_flow_proxy.parquet.
    """
    def result(value=None, stamp=None, **kwargs):
        return _receipt("flow_5d_mn", "flow_asof", value, stamp,
                        as_of=as_of, **kwargs)

    dd = data_dir or config.data_dir()
    path = dd / "flows" / f"{etf.upper()}.parquet"
    if not path.exists():
        return result(note=f"no ETF flow feed ({etf})")
    try:
        df = _retained_rows(pd.read_parquet(path), as_of)
        latest = df.index[-1] if not df.empty else None
        if df.empty:
            return result(note="no flow observations at requested cutoff")
        if "so_mn" not in df.columns or "nav" not in df.columns:
            return result(latest_row=latest, note="flow parquet missing so_mn/nav columns")
        implied = df["so_mn"].diff() * df["nav"]
        last5 = implied.dropna().tail(5)
        if last5.empty:
            return result(latest_row=latest, note="insufficient flow rows")
        total = float(last5.sum())
        if not math.isfinite(total):
            raise ValueError("nonfinite implied flow")
        return result(round(total, 2), last5.index[-1], latest_row=latest, window={
            "basis": "last_five_nonnull_changes", "observations": len(last5),
            "first_value_as_of": last5.index[0].date().isoformat(),
            "last_value_as_of": last5.index[-1].date().isoformat(),
        })
    except Exception as exc:  # noqa: BLE001
        log.warning("rotation_flows: etf_flow_receipt(%s) failed — %s", etf, exc)
        return result(note=f"read error: {type(exc).__name__}: {exc}")


# ------------------------------------------------------------------ options ----

def options_receipt(etf: str, data_dir: Path | None = None, *,
                    as_of: str | date | None = None) -> dict:
    """Latest usable net premium at/before the cutoff, with its genuine date."""
    def result(value=None, stamp=None, **kwargs):
        return _receipt("net_premium_mn", "options_asof", value, stamp,
                        as_of=as_of, **kwargs)

    dd = data_dir or config.data_dir()
    path = dd / "options_flow" / f"summary_{etf.upper()}.parquet"
    if not path.exists():
        return result(note=f"no options flow feed ({etf})")
    try:
        df = _retained_rows(pd.read_parquet(path), as_of)
        latest = df.index[-1] if not df.empty else None
        if df.empty:
            return result(note="no options observations at requested cutoff")
        if "net_premium_mn" not in df.columns:
            return result(latest_row=latest, note="net_premium_mn column missing")
        val = df["net_premium_mn"].dropna()
        if val.empty:
            return result(latest_row=latest, note="no net_premium_mn data")
        value = float(val.iloc[-1])
        if not math.isfinite(value):
            raise ValueError("nonfinite net premium")
        return result(round(value, 2), val.index[-1], latest_row=latest)
    except Exception as exc:  # noqa: BLE001
        log.warning("rotation_flows: options_receipt(%s) failed — %s", etf, exc)
        return result(note=f"read error: {type(exc).__name__}: {exc}")


# ------------------------------------------------------------------ gamma ----

def gamma_receipt(etf: str, data_dir: Path | None = None, *,
                  as_of: str | date | None = None) -> dict:
    """Latest usable gamma regime at/before the cutoff, with its genuine date."""
    def result(value=None, stamp=None, **kwargs):
        return _receipt("gamma_regime", "gex_asof", value, stamp,
                        as_of=as_of, **kwargs)

    dd = data_dir or config.data_dir()
    path = dd / "polygon_gex" / f"summary_{etf.upper()}.parquet"
    if not path.exists():
        return result(note=f"no GEX feed ({etf})")
    try:
        df = _retained_rows(pd.read_parquet(path), as_of)
        # Retain the existing GEX session guard after the historical cutoff.
        df = nyse_calendar.session_rows(df, label=f"cboe/gex_{etf}")
        latest = df.index[-1] if not df.empty else None
        if df.empty:
            return result(note="no GEX observations at requested cutoff")
        if "gamma_regime" not in df.columns:
            return result(latest_row=latest, note="gamma_regime column missing")
        val = df["gamma_regime"].dropna()
        if val.empty:
            return result(latest_row=latest, note="no gamma_regime data")
        return result(str(val.iloc[-1]), val.index[-1], latest_row=latest)
    except Exception as exc:  # noqa: BLE001
        log.warning("rotation_flows: gamma_receipt(%s) failed — %s", etf, exc)
        return result(note=f"read error: {type(exc).__name__}: {exc}")


# ------------------------------------------------------------------ combined ----

def flow_receipt_for_series(spec: dict, data_dir: Path | None = None, *,
                            as_of: str | date | None = None) -> dict:
    """Combined observation-date-bounded context; never classification inputs."""
    if spec.get("kind", "etf") == "etf":
        ticker = spec.get("ticker", "")
        fl = etf_flow_receipt(ticker, data_dir, as_of=as_of)
        opt = options_receipt(ticker, data_dir, as_of=as_of)
        gex = gamma_receipt(ticker, data_dir, as_of=as_of)
        return {
            "flow_5d_mn": fl.get("flow_5d_mn"), "flow_asof": fl.get("flow_asof"),
            "flow_note": fl.get("note"), "flow_status": fl["status"],
            "flow_window": fl.get("window"),
            "net_premium_mn": opt.get("net_premium_mn"),
            "options_asof": opt.get("options_asof"),
            "options_note": opt.get("note"), "options_status": opt["status"],
            "gamma_regime": gex.get("gamma_regime"), "gex_asof": gex.get("gex_asof"),
            "gex_note": gex.get("note"), "gex_status": gex["status"],
            "requested_as_of": fl["requested_as_of"],
            "availability": {"status": "UNKNOWN", "available_at": None},
        }
    # Baskets and ticker_ew composites have no direct ETF flow receipt.
    return {
        "flow_5d_mn": None, "flow_asof": None, "flow_note": "no ETF flow feed",
        "flow_status": "UNAVAILABLE", "flow_window": None,
        "net_premium_mn": None, "options_asof": None, "options_note": None,
        "options_status": "UNAVAILABLE",
        "gamma_regime": None, "gex_asof": None, "gex_note": None,
        "gex_status": "UNAVAILABLE",
        "requested_as_of": _receipt("", "", None, None, as_of=as_of)["requested_as_of"],
        "availability": {"status": "UNKNOWN", "available_at": None},
    }
