"""Hong Kong breadth — computed from the curated constituent universe
(config["hk"]["sectors"] members), reusing BreadthAdapter.compute().

There is no free HK-ETF holdings feed, and HK sector-ETF coverage is thin, so the
universe is hand-curated by Hang-Seng-industry sector in config.yml. Those same
names also form the DEEP synthetic sector baskets (15-25y history, far richer than
the ~5y HK sector ETFs) the engine RS-ranks. That makes this a large-cap
(HSI/HSCEI-style) breadth gauge, not full-market breadth — labeled honestly on the
dashboard. yfinance handles .HK closes (verified); coverage is logged and the run
fails if too many curated names fail to resolve.

Outputs mirror the US/China breadth series (data/hk_breadth/breadth.parquet):
pct_above_50/200, nh/nl, adv/dec/ad_line, n_members. Also writes a constituents
table (symbol/name/sector) used by the per-sector drill-down + stock search, and
caches the close matrix for the search library + the synthetic baskets.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
from datetime import datetime

import pandas as pd

from collectors.breadth import BreadthAdapter
from lib import config

log = logging.getLogger(__name__)


def repair_settled_hk_closes(
    closes: pd.DataFrame,
    tickers: list[str],
    *,
    now: datetime | None = None,
    fetcher=None,
    min_coverage: float = 0.95,
    max_workers: int = 12,
    max_wait_s: float = 150.0,
) -> pd.DataFrame:
    """Fill ONLY proven missing HK settled-close marks in the existing panel.

    Reuses the incumbent Tencent adjusted-candle transport, with exact HKEX
    completed-session time and the same adjusted-overlap refusal as the
    mainland search collector. No second store or publisher. A delayed Yahoo
    current-session/previous-session quote is NOT a settlement witness.
    """
    from lib import hk_calendar
    from collectors import china_stock_tencent as tencent

    expected = pd.Timestamp(hk_calendar.expected_last_session(now))
    df = closes.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.loc[df.index <= expected].sort_index().dropna(axis=0, how="all")
    df = df.loc[:, ~df.columns.duplicated(keep="last")]
    if df.empty:
        raise RuntimeError("HK breadth has no verified closing-price history")
    current = list(dict.fromkeys(str(x) for x in tickers))
    if not current:
        raise RuntimeError("HK breadth membership is empty")
    present = [t for t in current if t in df.columns]
    if expected in df.index:
        numeric = pd.to_numeric(df.loc[expected, present], errors="coerce")
        valid = {t for t, price in numeric.items()
                 if pd.notna(price) and float(price) > 0}
    else:
        valid = set()
    if len(valid) / len(current) >= min_coverage:
        return df

    suppliers = fetcher or tencent.fetch_tencent
    candidates = [t for t in current if t not in valid and t in df.columns]
    recovered: dict[str, float] = {}
    incompatible = unavailable = 0
    pool = ThreadPoolExecutor(max_workers=max(1, min(max_workers, 16)))
    futures = {pool.submit(suppliers, t, 12, 1): t for t in candidates}
    try:
        try:
            for fut in as_completed(futures, timeout=max_wait_s):
                ticker = futures[fut]
                try:
                    data = fut.result()
                except Exception:
                    unavailable += 1
                    continue
                if data is None or data.empty:
                    unavailable += 1
                    continue
                data = data.copy()
                data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
                if expected not in data.index:
                    unavailable += 1
                    continue
                observed = pd.to_numeric(pd.Series([data.at[expected, "close"]]),
                                         errors="coerce").iloc[0]
                if pd.isna(observed) or float(observed) <= 0:
                    unavailable += 1
                    continue
                history = pd.to_numeric(df[ticker], errors="coerce").dropna()
                history = history.loc[history.index < expected]
                overlap = history.index.intersection(data.index)
                if len(overlap) == 0:
                    incompatible += 1
                    continue
                overlap = overlap.sort_values()[-3:]
                if not tencent._compatible_overlap(
                    history.loc[overlap].to_frame("close"),
                    data.loc[overlap, ["close"]],
                    0.005,
                ):
                    incompatible += 1
                    continue
                recovered[ticker] = float(observed)
        except FutureTimeout:
            unavailable += sum(not f.done() for f in futures)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    qualified = len(valid) + len(recovered)
    coverage = qualified / len(current)
    log.info(
        "hk_breadth close repair session=%s Yahoo=%d Tencent=%d "
        "current=%d/%d (%.1f%%) rejected_basis=%d unavailable=%d",
        expected.date(), len(valid), len(recovered), qualified, len(current),
        100*coverage, incompatible, unavailable,
    )
    if coverage < min_coverage:
        raise RuntimeError(
            f"hk_breadth settled closes {qualified}/{len(current)} "
            f"({coverage:.1%}) below {min_coverage:.0%} for {expected.date()}; "
            "prior canonical close cache preserved"
        )
    if recovered:
        if expected not in df.index:
            df.loc[expected, :] = float("nan")
        for ticker, px in recovered.items():
            df.at[expected, ticker] = px
    return df.sort_index().dropna(axis=0, how="all")


class HkBreadthAdapter(BreadthAdapter):
    name = "hk_breadth"
    group = "hk_breadth"
    session_calendar = "HK"  # observation dates follow the cash/Connect session

    def __init__(self) -> None:
        self.cfg = config.load()["hk"]["breadth"]
        hk = config.load()["hk"]
        self.ycfg = hk["yahoo"]          # batch_size/retries/backoff for base _download_closes
        self.sectors = hk["sectors"]
        self.names = hk.get("names", {})
        self.cache_path = config.data_dir() / "hk_breadth" / "_closes_cache.parquet"

    def constituents(self) -> pd.DataFrame:
        rows = []
        for sector, meta in self.sectors.items():
            for t in meta["members"]:
                rows.append({"symbol": t, "name": self.names.get(t, t), "sector": sector})
        return pd.DataFrame(rows).drop_duplicates(subset="symbol")

    def constituents_checked(self, members: pd.DataFrame) -> pd.DataFrame:
        if members.empty or len(members) < 30:
            raise ValueError(f"hk constituents list suspicious: {len(members)} rows")
        return members

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        members = self.constituents_checked(self.constituents())
        tickers = members["symbol"].tolist()

        if full_history:
            closes = self._download_closes(tickers, "max")
        else:
            closes = None
            if self.cache_path.exists():
                cached = pd.read_parquet(self.cache_path)
                age = (pd.Timestamp.utcnow().tz_localize(None) - cached.index.max()).days
                if age <= 14:
                    fresh = self._download_closes(tickers, "1mo")
                    closes = self._merge_refreshed(fresh, cached)  # split-seam repair
            if closes is None:
                days = self.cfg["lookback_days_live"]
                closes = self._download_closes(tickers, f"{max(1, days // 365 + 1)}y")
            cutoff = closes.index.max() - pd.Timedelta(days=self.cfg["lookback_days_live"] + 30)
            closes = closes[closes.index >= cutoff]

        if not full_history:
            closes = repair_settled_hk_closes(closes, tickers)

        live_cols = closes.dropna(axis=1, how="all").shape[1]
        coverage = live_cols / len(tickers)
        log.info("hk_breadth coverage: %d/%d curated names resolved (%.0f%%)",
                 live_cols, len(tickers), 100 * coverage)
        if coverage < self.cfg["min_coverage"]:
            raise RuntimeError(f"hk_breadth closes too sparse: {live_cols}/{len(tickers)} "
                               f"(< {self.cfg['min_coverage']:.0%})")

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_history:
            closes.to_parquet(self.cache_path)
        members.set_index("symbol").to_parquet(self.cache_path.parent / "constituents.parquet")

        return {"breadth": self.compute(closes)}
