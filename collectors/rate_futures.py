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

import calendar
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone

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

# --- provenance vocabulary (RIC D0) ------------------------------------------ #
# The exact contract identity + strip basis of what this collector prints, so the
# display layer can attach it per row and refuse cross-basis numbers. Enum values
# are the seat's B0 freeze (rates_command_basis.v1) spelled literally.
VENDOR = "yfinance"
PRICE_TYPE = "vendor_daily_close"
RIGHTS = "unknown"
EXCHANGE_BY_SUFFIX = {"CBT": "CBOT", "CME": "CME"}
STRIP_BASIS = {
    "ZQ": {"rate_index": "EFFR", "averaging_law": "arithmetic_calendar_day",
           "target": "effr_monthly_average", "basket_or_index": "EFFR",
           "cadence": "monthly"},
    "SR3": {"rate_index": "SOFR", "averaging_law": "compounded_business_day",
            "target": "sofr_compounded_imm_quarter", "basket_or_index": "SOFR",
            "cadence": "quarterly"},
}
_MONTH_FROM_CODE = {v: k for k, v in _MONTH_CODE.items()}


def strip_basis(symbol_root: str) -> dict:
    """COPY of the strip's basis entry; an unknown root gets the same keys, all None."""
    entry = STRIP_BASIS.get(symbol_root)
    if entry is None:
        return {k: None for k in ("rate_index", "averaging_law", "target",
                                  "basket_or_index", "cadence")}
    return dict(entry)


_CONTRACT_SYMBOL_RE = re.compile(
    r"^(?P<root>[A-Z0-9]+?)(?P<code>[FGHJKMNQUVXZ])(?P<yy>\d{2})(?:\.(?P<ex>[A-Z]+))?$")


def parse_contract_symbol(sym: str) -> dict | None:
    """Contract identity for an EXACT vendor symbol (e.g. ``ZQX26.CBT``), or None.

    Never guesses: an unparseable symbol stays unknown — the caller records a
    contract_reference_unknown limitation rather than inventing a period."""
    if not isinstance(sym, str):
        return None
    m = _CONTRACT_SYMBOL_RE.match(sym)
    if m is None:
        return None
    root, code, yy, ex = m.group("root"), m.group("code"), m.group("yy"), m.group("ex")
    return {"vendor_symbol": sym, "contract_code": f"{root}{code}{yy}",
            "symbol_root": root, "month_code": code,
            "year": 2000 + int(yy), "month": _MONTH_FROM_CODE[code],
            "exchange_suffix": ex, "listing_exchange": EXCHANGE_BY_SUFFIX.get(ex)}


def _third_wednesday(year: int, month: int) -> date:
    weeks = calendar.monthcalendar(year, month)
    weds = [w[calendar.WEDNESDAY] for w in weeks if w[calendar.WEDNESDAY]]
    return date(year, month, weds[2])


def contract_reference_period(year: int, month: int, cadence: str) -> tuple[str | None, str | None]:
    """Inclusive ISO reference period the printed rate covers.

    Monthly (ZQ): the whole calendar month. Quarterly (SR3/IMM): third Wednesday
    of the contract month .. the day before the third Wednesday of month+3.
    Any other cadence is unknown — (None, None), never a guess."""
    if cadence == "monthly":
        last = calendar.monthrange(year, month)[1]
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"
    if cadence == "quarterly":
        start = _third_wednesday(year, month)
        ey, em = (year, month + 3) if month <= 9 else (year + 1, month + 3 - 12)
        end = _third_wednesday(ey, em) - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    return None, None


def contracts_frame(chosen: dict[str, pd.Series]) -> pd.DataFrame:
    """Wide frame of the EXACT vendor symbols that printed (vendor daily close,
    as downloaded — no fill, no drop). Empty input → empty DataFrame."""
    live = {sym: s for sym, s in (chosen or {}).items()
            if s is not None and not s.dropna().empty}
    if not live:
        return pd.DataFrame()
    idx = pd.DatetimeIndex(sorted(set().union(*[s.index for s in live.values()])))
    return pd.DataFrame({sym: s.reindex(idx) for sym, s in live.items()}, index=idx)


def _months_diff(cy: int, cm: int, dy: int, dm: int) -> int:
    """Whole months from (dy, dm) to the contract (cy, cm)."""
    return (cy * 12 + cm) - (dy * 12 + dm)


def gen_contracts(symbol_root: str, exchanges: list[str], cadence: str,
                  n: int, asof: date) -> list[dict]:
    """The next `n` live delivery months as Yahoo candidate symbols.

    Returns one dict per (year, month) with the candidate Yahoo symbols (one per
    exchange suffix, e.g. ``ZQF26.CBT``). Monthly cadence walks every month;
    quarterly walks only the IMM months (Mar/Jun/Sep/Dec). Rolls off `asof`, so
    the strip is always current — no contract is ever hard-coded.
    """
    out: list[dict] = []
    y, m = asof.year, asof.month
    steps = 0
    # walk forward month-by-month until we have n contracts of the right cadence
    while len(out) < n and steps < 60:
        if cadence == "monthly" or (cadence == "quarterly" and m in (3, 6, 9, 12)):
            code = f"{symbol_root}{_MONTH_CODE[m]}{y % 100:02d}"
            out.append({
                "year": y, "month": m,
                "symbols": [f"{code}.{ex}" for ex in exchanges],
            })
        m += 1
        if m > 12:
            m, y = 1, y + 1
        steps += 1
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
        asof = datetime.now(timezone.utc).date()
        out: dict[str, pd.DataFrame] = {}
        for key, spec in (self.cfg.get("roots", {}) or {}).items():
            contracts = gen_contracts(spec["symbol_root"], list(spec["exchanges"]),
                                      spec.get("cadence", "monthly"),
                                      int(spec.get("months", 12)), asof)
            # one batch download of every candidate symbol; pick the variant that prints
            symbols = [s for c in contracts for s in c["symbols"]]
            raw = self._download(symbols, period, yf)
            series: dict[tuple[int, int], pd.Series] = {}
            chosen: dict[str, pd.Series] = {}
            for c in contracts:
                for sym in c["symbols"]:
                    s = self._close(raw, sym)
                    if s is not None and not s.dropna().empty:
                        series[(c["year"], c["month"])] = s
                        chosen[sym] = s
                        break
            path = implied_path(series, horizons, max_months,
                                spec.get("cadence", "monthly"))
            if not path.empty:
                out[f"{key}_path"] = path
                # exact-symbol provenance frame — must never fail the path itself
                try:
                    cf = contracts_frame(chosen)
                    if not cf.empty:
                        out[f"{key}_contracts"] = cf
                except Exception as exc:  # noqa: BLE001 — additive, never fatal
                    log.warning("rate_futures: %s contracts frame unavailable (%s)",
                                key, exc)
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
                    raise RuntimeError("empty yfinance response")
                return df
            except Exception as e:  # noqa: BLE001 — retried, then surfaced to the runner
                last_exc = e
                wait = self.backoff * (2 ** attempt)
                log.warning("rate_futures download failed (%s); retry in %.0fs", e, wait)
                if attempt < self.retries - 1:
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]
