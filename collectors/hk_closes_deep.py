"""HK closes-deep nightly refresh — incremental append to data/hk_search/closes_deep.parquet.

The deep wide matrix (Date x ticker, close-only, ~40y back to 1986 for the blue chips) was
originally built by a one-off research script (scripts/hk_residual_alpha_phase0.py --fetch)
and was NEVER wired into the nightly collect lane.  As a result the file drifted stale
(last observed gap: closes_deep 2026-06-18 vs hk_stocks 2026-07-03, HKCA-3 in the audit).

This adapter closes that gap:
  - On a normal run it downloads the trailing ~2 months for all constituents and
    merge-upserts (combine_first) onto the existing parquet, keeping the full deep history.
  - On --full-history it refetches from the beginning (same as the one-off --fetch flag).
  - It writes to data/hk_search/ (group="hk_search", series_name="closes_deep") so the
    path is identical to what all consumers already read.
  - Stale-after-days = 5 (same cadence as hk_breadth).
  - Named tripwire: stale detection fires if max date falls behind hk_stocks.

Universe: data/hk_breadth/constituents.parquet (written by HkBreadthAdapter; must exist).
Fail-closed: if the constituents file is missing, raises immediately (do not silently produce
an empty or truncated parquet).  If yfinance returns fewer names than expected, coverage is
logged and the run proceeds (consistent with hk_breadth min_coverage behavior).
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import yfinance as yf

from collectors.base import Adapter
from collectors.breadth import repair_seams
from lib import config, hk_calendar

log = logging.getLogger(__name__)

_CONSTITUENTS_PATH = "hk_breadth/constituents.parquet"
_MIN_COVERAGE = 0.50          # fail if yfinance returns < 50% of expected tickers
_INCREMENTAL_PERIOD = "2mo"   # enough to cover any short outage (>= stale_after_days x margin)


def reconcile_settled_hk_cache(
    fresh: pd.DataFrame,
    tickers: list[str],
    *,
    cache: pd.DataFrame | None,
    reference: pd.DataFrame | None = None,
    now: datetime | None = None,
    min_coverage: float = 0.95,
) -> pd.DataFrame:
    """Extend the single existing HK deep-close store with validated breadth marks.

    hk_breadth runs earlier in the same SERIAL Asia collector and writes the
    source-qualified, runner-local adjusted close cache. This existing deep
    store is the durable sole owner of HK historical close persistence.
    No additional vendor collector or second lifecycle is introduced here.

    Require the HKEX completed settlement day, >=95% current stock coverage,
    and agreement within 0.5% with at least two historic adjusted prices in
    the durable deep store (or fresh Yahoo history if deep is absent).
    """
    expected = pd.Timestamp(hk_calendar.expected_last_session(now))

    def normalize(frame):
        if frame is None or frame.empty:
            return pd.DataFrame()
        out = frame.copy()
        out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
        out = out[~out.index.duplicated(keep="last")]
        out = out.loc[out.index <= expected]
        return out.loc[:, ~out.columns.duplicated(keep="last")].sort_index()

    df = normalize(fresh)
    if df.empty:
        raise RuntimeError("HK deep close publisher has no completed-session history")
    current = list(dict.fromkeys(map(str, tickers)))
    if not current:
        raise RuntimeError("HK deep close current membership is empty")
    valid: set[str] = set()
    if expected in df.index:
        for ticker in current:
            if ticker not in df.columns:
                continue
            raw = pd.to_numeric(pd.Series([df.at[expected, ticker]]), errors="coerce").iloc[0]
            if pd.notna(raw) and float(raw) > 0:
                valid.add(ticker)
    recovered: dict[str, float] = {}
    recovered_durable = recovered_breadth = 0
    rejected_basis = missing = 0
    if len(valid) / len(current) < min_coverage:
        existing = normalize(reference)
        observed = normalize(cache)
        # On an ordinary next render, a fully source-qualified last-good
        # session already lives in the COMMITTED deep store. Cold runners may
        # miss the ephemeral breadth cache, so preserve those durable marks
        # only when their previous adjusted closes agree with fresh Yahoo
        # history. This reuses the existing owner, never trusts a bare date.
        disallowed_basis: set[str] = set()
        sources = (
            ("durable", existing, df),
            ("breadth", observed, existing if not existing.empty else df),
        )
        for label, source, historical in sources:
            if source.empty or expected not in source.index:
                continue
            for ticker in current:
                if ticker in valid or ticker in recovered or ticker in disallowed_basis:
                    continue
                if ticker not in source.columns or ticker not in historical.columns:
                    continue
                candle = pd.to_numeric(
                    pd.Series([source.at[expected, ticker]]), errors="coerce"
                ).iloc[0]
                if pd.isna(candle) or float(candle) <= 0:
                    missing += 1
                    continue
                primary = pd.to_numeric(historical[ticker], errors="coerce").dropna()
                primary = primary.loc[(primary.index < expected) & (primary > 0)]
                secondary = pd.to_numeric(source[ticker], errors="coerce").dropna()
                secondary = secondary.loc[(secondary.index < expected) & (secondary > 0)]
                overlap = primary.index.intersection(secondary.index).sort_values()[-3:]
                if len(overlap) < 2:
                    rejected_basis += 1
                    disallowed_basis.add(ticker)
                    continue
                rel = (primary.loc[overlap] - secondary.loc[overlap]).abs() / (
                    primary.loc[overlap].abs().clip(lower=1e-9)
                )
                if float(rel.max()) > 0.005:
                    rejected_basis += 1
                    disallowed_basis.add(ticker)
                    continue
                recovered[ticker] = float(candle)
                if label == "durable":
                    recovered_durable += 1
                else:
                    recovered_breadth += 1
    count = len(valid) + len(recovered)
    ratio = count / len(current)
    log.info(
        "HK deep-source reconciliation: session=%s primary=%d "
        "verified_existing_deep=%d incumbent_breadth_cache=%d "
        "coverage=%d/%d (%.1f%%), basis_rejected=%d unavailable=%d",
        expected.date(), len(valid), recovered_durable, recovered_breadth,
        count, len(current), ratio * 100, rejected_basis, missing,
    )
    if ratio < min_coverage:
        raise RuntimeError(
            f"HK deep close coverage {count}/{len(current)} ({ratio:.1%}) "
            f"below {min_coverage:.0%} for {expected.date()}; keep last-good store"
        )
    if recovered:
        if expected not in df.index:
            df.loc[expected, :] = float("nan")
        for ticker, close in recovered.items():
            df.at[expected, ticker] = close
    return df.sort_index().dropna(axis=0, how="all")


class HkClosesDeepAdapter(Adapter):
    """Nightly incremental refresh of data/hk_search/closes_deep.parquet."""

    name = "hk_closes_deep"
    group = "hk_search"        # -> store writes data/hk_search/closes_deep.parquet
    stale_after_days = 5

    def _tickers(self) -> list[str]:
        p = config.data_dir() / _CONSTITUENTS_PATH
        if not p.exists():
            raise RuntimeError(
                "hk_closes_deep: constituents file missing "
                f"({p}) -- run hk_breadth first"
            )
        return list(pd.read_parquet(p).index)

    def _download(self, tickers: list[str], period: str) -> pd.DataFrame:
        raw = yf.download(
            tickers,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        # yfinance returns a multi-level frame for multiple tickers.
        if hasattr(raw.columns, "levels"):
            level0 = raw.columns.get_level_values(0)
            if "Close" in level0:
                return raw["Close"]
            return raw.xs("Close", axis=1, level=0)
        # Single ticker fallback (shouldn't happen for 150+ tickers, but be safe)
        return raw[["Close"]] if "Close" in raw.columns else raw

    def _heal_store_seams(self, fresh: pd.DataFrame) -> None:
        """In-place split-seam repair of the stored deep matrix (#2120 KLAC class).

        The runner merges fetch()'s fresh window into closes_deep.parquet with
        plain combine_first (store.upsert, overwrite_overlap=False), so after a
        split the stored PRE-window history stays on the old price basis — a
        permanent fake ±N00% day at the refresh boundary. Detection therefore
        runs here against the stored file, and the heal rewrites the flagged
        columns WHOLESALE in the store BEFORE the runner's merge: returning the
        healed history through fetch() would let stale cached cells resurrect
        via combine_first wherever the re-pull lacks a row. Never fatal."""
        try:
            path = config.data_dir() / self.group / "closes_deep.parquet"
            if not path.exists():
                return
            cached = pd.read_parquet(path)
            # merged target IS the cached matrix: detector (a) sees a boundary
            # re-basing via fresh-vs-cached overlap, detector (b) sees residual
            # seams from past refreshes inside cached itself.
            cached, healed = repair_seams(cached, fresh, cached, self._download,
                                          "max", name=self.name)
            if healed:
                cached.to_parquet(path)
                log.info("hk_closes_deep: healed %d split-seamed column(s) in %s: %s",
                         len(healed), path.name, healed[:12])
        except Exception as e:  # noqa: BLE001 — repair must never kill the run
            log.warning("hk_closes_deep: seam heal failed (%s) — store kept as-is; "
                        "the scan retries next run", e)

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        tickers = self._tickers()

        if full_history:
            period = "max"
            log.info("hk_closes_deep: full-history fetch for %d tickers", len(tickers))
        else:
            period = _INCREMENTAL_PERIOD
            log.info(
                "hk_closes_deep: incremental fetch for %d tickers (%s)",
                len(tickers), period,
            )

        closes = self._download(tickers, period)

        # Keep only the requested tickers (yfinance may silently drop delisted names)
        valid = [t for t in tickers if t in closes.columns]
        closes = closes[valid].dropna(how="all")

        coverage = len(valid) / len(tickers) if tickers else 0.0
        log.info(
            "hk_closes_deep: %d/%d tickers resolved (%.0f%%), date range %s->%s",
            len(valid), len(tickers), 100 * coverage,
            closes.index.min().date() if not closes.empty else "N/A",
            closes.index.max().date() if not closes.empty else "N/A",
        )
        if coverage < _MIN_COVERAGE:
            raise RuntimeError(
                f"hk_closes_deep: coverage {coverage:.0%} < {_MIN_COVERAGE:.0%} "
                f"({len(valid)}/{len(tickers)} tickers)"
            )
        if closes.empty:
            raise RuntimeError("hk_closes_deep: yfinance returned no rows")

        # HK source completion is a per-session observation contract, NOT a
        # count of ticker columns. The earlier hk_breadth owner has already
        # fetched/qualified the same adjusted HKEX close in its local cache.
        # Reuse it here before the normal store upsert, so the next site render
        # can read current HK close history even if its runner cache is missing.
        if not full_history:
            cache_p = config.data_dir() / "hk_breadth" / "_closes_cache.parquet"
            deep_p = config.data_dir() / "hk_search" / "closes_deep.parquet"
            cache = pd.read_parquet(cache_p) if cache_p.is_file() else None
            reference = pd.read_parquet(deep_p) if deep_p.is_file() else None
            closes = reconcile_settled_hk_cache(
                closes, tickers, cache=cache, reference=reference,
            )
            # Keep the pre-existing split-seam repair and durable owner.
            self._heal_store_seams(closes)

        # The validate() + store.upsert() path in run_adapter handles the merge with
        # the existing parquet (combine_first keeps old deep-history rows).
        return {"closes_deep": closes}
