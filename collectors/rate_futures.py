"""Rate-futures collector — keyless ZQ/SR3 implied policy-path curve.

Fetches multi-contract Fed Funds (ZQ, 30-day, CBOT) + 3-Month SOFR (SR3, CME)
futures from Yahoo and distils them into a daily *implied policy path* snapshot at
fixed horizons (1/3/6/12 months ahead). 100 − price = the policy rate the market
prices for that contract's reference period; we interpolate across the strip to the
target horizons.

DISPLAY-ONLY. The implied rate IS a market price, not a forecast edge — it feeds
engine/fed_path.py (bonds.html + latest.json LLM context) and is NEVER scored, never
an MRS leg. See research/DATA_SIGNAL_EXPANSION_2026.md #2.

Yahoo throttles the build sandbox (HTTP 429), so the live fetch runs in CI; the pure
path-math helpers (`gen_contracts`, `implied_path`) are unit-tested on synthetic
prices. The contract strip rolls automatically off the run date — nothing hard-coded.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from collectors.base import Adapter
from lib import config

log = logging.getLogger(__name__)

# CME/CBOT delivery-month codes
_MONTH_CODE = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
               7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
# the reference-period CENTRE, in months past the contract's delivery month, so the
# implied rate is placed at the middle of the period it actually averages
_CENTRE_OFFSET = {"monthly": 0.5, "quarterly": 1.5}


def _months_diff(cy: int, cm: int, dy: int, dm: int) -> int:
    """Whole months from (dy, dm) to the contract (cy, cm)."""
    return (cy * 12 + cm) - (dy * 12 + dm)


def gen_contracts(symbol_root: str, exchanges: list[str], cadence: str,
                  n: int, asof: date) -> list[dict]:
    """The next `n` live contract months as Yahoo candidate symbols.

    Monthly cadence walks every calendar month from `asof`. For the incumbent
    SR3 quarterly family, contract names identify the month in which the
    reference quarter BEGINS, so April/May still need the March contract and
    July/August still need June. Use the existing reference-period owner to
    locate the active quarter instead of rolling at civil month boundaries.
    """
    if cadence not in ("monthly", "quarterly"):
        raise ValueError("unsupported_contract_cadence")

    out: list[dict] = []
    if cadence == "quarterly":
        from engine.rate_futures_repricing import reference_period

        # Start from the latest quarterly named month not after the civil month.
        quarter_months = (3, 6, 9, 12)
        prior = [month for month in quarter_months if month <= asof.month]
        if prior:
            y, m = asof.year, prior[-1]
        else:
            y, m = asof.year - 1, 12

        # Before that quarter's third-Wednesday reference start, the previous
        # quarterly contract is still the active reference-quarter contract.
        start, _ = reference_period(symbol_root, y, m)
        if asof < date.fromisoformat(start):
            m -= 3
            if m <= 0:
                m += 12
                y -= 1

        for _ in range(n):
            code = f"{symbol_root}{_MONTH_CODE[m]}{y % 100:02d}"
            out.append({
                "year": y, "month": m,
                "symbols": [f"{code}.{ex}" for ex in exchanges],
            })
            m += 3
            if m > 12:
                m -= 12
                y += 1
        return out

    y, m = asof.year, asof.month
    for _ in range(n):
        code = f"{symbol_root}{_MONTH_CODE[m]}{y % 100:02d}"
        out.append({
            "year": y, "month": m,
            "symbols": [f"{code}.{ex}" for ex in exchanges],
        })
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def implied_path(contracts: dict[tuple[int, int], pd.Series], horizons_m: list[int],
                 max_months: int, cadence: str) -> pd.DataFrame:
    """Distil a strip of dated contracts into a per-day implied-rate path.

    `contracts` maps (year, month) → that contract's close Series (price, e.g.
    96.50 ⇒ 3.50% implied). For each date we place every live contract at its
    reference-period centre (months-ahead) and linearly interpolate the implied
    rate to each target horizon. A contract contributes only on dates where its
    centre is within [0, max_months]; the overlapping lives of the strip yield a
    continuous recent path. Columns: ``m1, m3, m6, ...`` (implied policy rate %).
    """
    centre = _CENTRE_OFFSET.get(cadence, 0.5)
    # implied rate per contract, on a shared business-day index
    rates = {km: (100.0 - s.astype(float)) for km, s in contracts.items()
             if s is not None and not s.dropna().empty}
    if not rates:
        return pd.DataFrame()
    idx = pd.DatetimeIndex(sorted(set().union(*[r.index for r in rates.values()])))
    cols = {f"m{h}": [] for h in horizons_m}
    for d in idx:
        pts: list[tuple[float, float]] = []
        for (cy, cm), r in rates.items():
            if d not in r.index:
                continue
            v = r.loc[d]
            if pd.isna(v):
                continue
            ma = _months_diff(cy, cm, d.year, d.month) + centre
            if 0.0 <= ma <= max_months:
                pts.append((ma, float(v)))
        pts.sort()
        for h in horizons_m:
            # only interpolate within the strip's span — never extrapolate a horizon
            if len(pts) >= 2 and pts[0][0] <= h <= pts[-1][0]:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                cols[f"m{h}"].append(round(_interp(h, xs, ys), 4))
            elif len(pts) == 1 and abs(pts[0][0] - h) <= 1.0:
                cols[f"m{h}"].append(round(pts[0][1], 4))
            else:
                cols[f"m{h}"].append(None)
    df = pd.DataFrame(cols, index=idx).dropna(how="all")
    return df


def _interp(x: float, xs: list[float], ys: list[float]) -> float:
    """Piecewise-linear interpolation (xs assumed sorted ascending)."""
    for i in range(1, len(xs)):
        if x <= xs[i]:
            x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]


def implied_path_with_components(contracts, horizons_m, max_months, cadence):
    """Preserve the incumbent curve, plus its exact interpolation constituents.

    The original numeric helper remains authoritative. The downstream reader
    checks that these weights reproduce it; a mismatch withholds attribution.
    """
    import math
    path = implied_path(contracts, horizons_m, max_months, cadence)
    components = {}
    centre = _CENTRE_OFFSET.get(cadence, 0.5)
    for d in path.index:
        points = []
        for (year, month), series in contracts.items():
            if d not in series.index:
                continue
            rate = 100.0 - float(series.loc[d])
            coordinate = _months_diff(year, month, d.year, d.month) + centre
            if math.isfinite(rate) and 0 <= coordinate <= max_months:
                points.append((coordinate, f'{year:04d}-{month:02d}'))
        points.sort()
        row = {}
        for h in horizons_m:
            weights, state = {}, 'uncovered'
            if len(points) >= 2 and points[0][0] <= h <= points[-1][0]:
                for left, right in zip(points, points[1:]):
                    if h <= right[0]:
                        fraction = (h - left[0]) / (right[0] - left[0])
                        weights = {left[1]: 1.0 - fraction, right[1]: fraction}
                        weights = {key: value for key, value in weights.items() if value > 0}
                        state = 'exact' if len(weights) == 1 else 'interpolated'
                        break
            elif len(points) == 1 and abs(points[0][0] - h) <= 1:
                weights, state = {points[0][1]: 1.0}, 'single_contract_proximity'
            row[f'm{h}'] = {'weights': weights, 'status': state}
        components[d] = row
    return path, components


class _EmptyQuoteBatch(RuntimeError):
    """Provider returned no rows after the incumbent download retry budget."""


class RateFuturesAdapter(Adapter):
    name = "rate_futures"
    group = "rate_futures"
    stale_after_days = 5

    def __init__(self) -> None:
        self.cfg = config.load().get("rate_futures", {}) or {}
        ycfg = config.load()["yahoo"]
        self.retries = int(ycfg.get("retries", 3))
        self.backoff = float(ycfg.get("backoff_base_s", 5))

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        import yfinance as yf  # local import — keep module importable without yfinance

        horizons = list(self.cfg.get("horizons_m", [1, 3, 6, 12]))
        max_months = int(self.cfg.get("max_months", 18))
        period = "5y" if full_history else "3mo"
        # Contract-month identity follows the U.S. market calendar, not UTC.
        # Between 00:00 UTC and New York midnight, UTC is already the next date;
        # using it can roll the requested strip a month early at month-end.
        asof = datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York")).date()
        out: dict[str, pd.DataFrame] = {}
        for key, spec in (self.cfg.get("roots", {}) or {}).items():
            contracts = gen_contracts(spec["symbol_root"], list(spec["exchanges"]),
                                      spec.get("cadence", "monthly"),
                                      int(spec.get("months", 12)), asof)
            # one batch download of every candidate symbol; pick the variant that prints
            symbols = [s for c in contracts for s in c["symbols"]]
            try:
                raw = self._download(symbols, period, yf)
            except _EmptyQuoteBatch:
                log.warning("rate_futures: %s - exhausted empty batch; retaining other families", key)
                continue
            if raw is None or raw.empty:
                # Empty is not unidentified nonempty data. Keep earlier valid
                # families, while the existing consumer reports this source missing.
                log.warning("rate_futures: %s - empty batch; retaining other families", key)
                continue
            if len(symbols) > 1 and not isinstance(raw.columns, pd.MultiIndex):
                # A flat batch response cannot identify which contract was quoted.
                raise ValueError('batch_quotes_lack_contract_identity')
            captured_at = datetime.now(timezone.utc).isoformat()
            series: dict[tuple[int, int], pd.Series] = {}
            chosen_symbols = {}
            for c in contracts:
                for sym in c["symbols"]:
                    s = self._close(raw, sym)
                    if s is not None and not s.dropna().empty:
                        identity = (c["year"], c["month"])
                        series[identity] = s
                        chosen_symbols[identity] = sym
                        break
            cadence = spec.get("cadence", "monthly")
            path, components = implied_path_with_components(series, horizons, max_months, cadence)
            if not path.empty:
                from engine.rate_futures_repricing import attach_constituents
                path, evidence = attach_constituents(path, components, series, chosen_symbols,
                    root=spec['symbol_root'], cadence=cadence, max_months=max_months,
                    captured_at=captured_at)
                out[f"{key}_path"] = path
                out[f"{key}_constituents"] = evidence
                log.info("rate_futures: %s — %d live contracts, %d path days",
                         key, len(series), len(path))
            else:
                log.warning("rate_futures: %s — no usable contracts", key)
        if not out:
            raise RuntimeError("rate_futures: no implied path for any root (Yahoo empty)")
        return out

    @staticmethod
    def _close(raw: pd.DataFrame, sym: str) -> pd.Series | None:
        if raw is None or raw.empty:
            return None
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                if sym not in raw.columns.get_level_values(0):
                    return None
                sub = raw[sym]
            else:
                sub = raw
            col = "Close" if "Close" in sub.columns else ("close" if "close" in sub.columns else None)
            return sub[col].dropna() if col else None
        except (KeyError, AttributeError):
            return None

    def _download(self, symbols: list[str], period: str, yf) -> pd.DataFrame:
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                df = yf.download(symbols, period=period, auto_adjust=False,
                                 progress=False, group_by="ticker", threads=True)
                if df is None or df.empty:
                    raise _EmptyQuoteBatch("empty yfinance response")
                return df
            except Exception as e:  # noqa: BLE001 — retried, then surfaced to the runner
                last_exc = e
                wait = self.backoff * (2 ** attempt)
                log.warning("rate_futures download failed (%s); retry in %.0fs", e, wait)
                if attempt < self.retries - 1:
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]
