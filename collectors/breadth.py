"""S&P 500 internal breadth, computed from constituents (not scraped).

- Constituents: Wikipedia table (current members — survivorship caveat:
  fine for the live signal, biased for backtests; see LIMITATIONS.md).
- Closes: yfinance in batches. The raw close matrix is a local cache
  (data/breadth/_closes_cache.parquet, gitignored — in CI restored via
  actions/cache; on miss it is re-downloaded, ~2 min). Only the small
  computed aggregate series is committed to the repo.
- Outputs (data/breadth/breadth.parquet):
    pct_above_50, pct_above_200  — % of members above 50/200DMA
    nh, nl                       — counts of 252d new highs / lows
    adv, dec, ad_line            — daily up/down counts + cumulative A-D line
    n_members                    — denominator that day
"""
from __future__ import annotations

import io
import logging
import re
import time
import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Mapping
from types import MappingProxyType

import pandas as pd
import yfinance as yf

from collectors.base import Adapter
from lib import config, delisted_symbols

log = logging.getLogger(__name__)

# A real US listing symbol: a letter, then up to 5 more letters/digits/dashes
# (class shares like BRK-B after the .->- swap). Anything else in the Symbol
# column is vandalism / footnote junk and must not enter the universe.
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9-]{0,5}$")

# --- split-seam detection (2026-07-10 incident) -----------------------------
# yfinance auto_adjust back-adjusts ONLY the window it downloads, so the tail
# refresh (fresh 1mo window merged over the cached matrix) leaves every cached
# row BEFORE that window on the old price basis after a stock split. The merged
# series then carries a permanent fake step where the refresh window stopped
# rewriting: KLAC's 10:1 split (2026-06-12) left $1,842.80 -> $180.90 across
# 2026-05-11/12 (a fake -90.2% "day"); CRWD's 4:1 left a fake -75% day at
# 2026-06-02. A poisoned column biases pct_above_50/200, 252d NH/NL, adv/dec
# and everything reading the closes/OHLCV caches (trailing vol, beta) until the
# lookback rolls past the seam (~10 months for the 200DMA).
# lib.store.upsert(overwrite_overlap=True) solves this class for STORED series
# but only inside the fresh window — the cache's pre-window history needs the
# per-ticker repair in BreadthAdapter._merge_refreshed.
_BASIS_TOL = 0.05    # cached-vs-fresh overlap disagreeing beyond this = stale basis.
                     # Dividend re-adjustments shift the basis by the yield fraction
                     # (< ~2% a quarter, must NOT trigger); splits shift it 2x-25x.
_SEAM_LO, _SEAM_HI = 0.60, 1.65   # 1-day ratio bounds for the residual-seam scan:
                     # catches every >=2:1 split seam in either direction. Genuine
                     # ±40% news days (CNC -40% 2025-07, SATS +70% 2025-08) DO trip
                     # it — for those the repair re-pull returns identical data, so
                     # a false positive costs one batched download, never data.


def seam_suspects(fresh: pd.DataFrame | None, cached: pd.DataFrame | None,
                  merged: pd.DataFrame) -> list[str]:
    """Tickers whose close history mixes price-adjustment bases (split seams).

    Two independent detectors, union of both:
    (a) basis break at the refresh boundary — cached vs fresh disagree by a
        roughly constant factor over their overlap (a split since the last
        refresh re-based the fresh window but not the cache);
    (b) residual seams from PAST refreshes — a 1-day ratio in the merged
        matrix outside [_SEAM_LO, _SEAM_HI] (scanned on a ffilled frame so a
        seam across a data gap is still visible).
    Pass fresh=None/cached=None to run only (b) on an existing cache."""
    bad: set[str] = set()
    if fresh is not None and cached is not None:
        overlap = fresh.index.intersection(cached.index)
        if len(overlap) >= 3:
            common = fresh.columns.intersection(cached.columns)
            f = fresh.loc[overlap, common]
            ratio = (cached.loc[overlap, common] / f.where(f > 0)).median().dropna()
            bad |= set(ratio.index[(ratio - 1).abs() > _BASIS_TOL])
    filled = merged.ffill()
    r = filled / filled.shift(1)
    sus = ((r < _SEAM_LO) | (r > _SEAM_HI)).any()
    bad |= set(sus.index[sus])
    return sorted(bad)


_SEAM_SCAN_DAYS = 550   # residual-seam scan window for PERPETUAL caches (repair_seams):
                        # a new seam can only form at a refresh boundary, i.e. within days
                        # of the split, so ~18 months catches every operational seam with
                        # margin — while keeping genuine deep-history crash days (1987/
                        # 1997/2008 in the 40y hk_search matrix, one-off -50% earnings
                        # days in the 5y+ search caches) from triggering a re-pull every
                        # night forever. Legacy seams beyond the window are healed one-
                        # shot by scripts/heal_breadth_split_seams.py (full-file scan).


def repair_seams(merged: pd.DataFrame, fresh: pd.DataFrame | None,
                 cached: pd.DataFrame | None, downloader, period: str | None = None,
                 *, name: str = "closes",
                 scan_days: int | None = _SEAM_SCAN_DAYS) -> tuple[pd.DataFrame, list[str]]:
    """Split-seam repair for a merged wide-closes matrix; returns (merged, healed).

    The reusable core of BreadthAdapter._merge_refreshed for the collectors that
    merge an auto-adjusted fresh window over a cached matrix OUTSIDE the breadth
    cache (canada/intl/china search closes.parquet, hk_search closes_deep):
    every ticker flagged by seam_suspects gets its full window re-downloaded in
    one batched ``downloader(tickers, period)`` call and its column replaced
    WHOLESALE in ``merged`` (mutated in place and returned). period=None derives
    the re-pull window from the merged span ("max" beyond 10y, else "<span>y"
    like the one-shot healer). Correct whether the flag was a real seam or a
    genuine ±40% news day (the re-pull returns identical data). Never fatal: on
    a failed re-pull the poisoned columns are LEFT IN PLACE (loud warning) so
    the scan re-flags them next run. ``healed`` lists the columns actually
    replaced — empty when nothing was flagged or the re-pull failed."""
    scan = merged
    if scan_days is not None and len(merged.index):
        scan = merged[merged.index >= merged.index.max() - pd.Timedelta(days=scan_days)]
    bad = seam_suspects(fresh, cached, scan)
    if not bad:
        return merged, []
    if period is None:
        span_years = max(1, (merged.index.max() - merged.index.min()).days // 365 + 1)
        period = "max" if span_years > 10 else f"{span_years}y"
    log.warning("%s: %d ticker(s) with mixed adjustment basis in the closes cache "
                "(split seam) — re-pulling %s: %s", name, len(bad), period, bad[:12])
    try:
        repull = downloader(bad, period)
    except Exception as e:  # noqa: BLE001 — repair must never kill the run
        log.warning("%s: seam re-pull failed (%s) — cache kept as-is; the seam "
                    "scan retries next run", name, e)
        return merged, []
    if repull is None:
        repull = pd.DataFrame()
    healed = [t for t in bad if t in repull.columns and repull[t].notna().any()]
    for t in healed:
        merged[t] = repull[t].reindex(merged.index)
    if missed := sorted(set(bad) - set(healed)):
        log.warning("%s: seam re-pull returned no data for %s — kept as-is, "
                    "retried next run", name, missed[:12])
    return merged, healed


def compute_updown(closes: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """Market-wide up/down volume and up/down points aggregates.

    Accruing store for the Lowry/Desmond 90%-day family (masterplan W2).
    Deep history is impossible: the volume cache is a ~35-row tail accrued nightly
    from the breadth OHLCV extras. The store grows forward from first collection;
    no backfill claim is made (label honesty). All history is this-panel-derived,
    never sourced from third-party Desmond/Lowry event rosters (universe differs).

    Columns returned (all float64, date-indexed):
      up_vol      — total share volume on members with a positive close-to-close change
      down_vol    — total share volume on members with a negative close-to-close change
      up_pts      — sum of positive close-to-close price changes (Desmond points; NOT volume-weighted)
      down_pts    — sum of |negative| close-to-close price changes
      n_reporting — member count with both a price change and non-NaN volume

    Rows where n_reporting < 300 are dropped (S&P panel with <300 reporting = data gap).

    Args:
        closes:  Wide date×ticker close-price matrix (any adjustment basis; only diff used).
        volume:  Wide date×ticker share-volume matrix; must share the closes index/columns layout.

    Returns:
        DataFrame indexed by date; empty if inputs are empty or produce no qualifying rows.
        Never raises; caller should wrap in try/except for extra safety.
    """
    if closes is None or closes.empty or volume is None or volume.empty:
        return pd.DataFrame(columns=["up_vol", "down_vol", "up_pts", "down_pts", "n_reporting"])

    dpx = closes.diff()  # price change vs prior close
    vol = volume.reindex(columns=closes.columns)  # align columns

    up_mask = dpx > 0
    dn_mask = dpx < 0
    both_present = dpx.notna() & vol.notna()

    up_vol = (vol.where(up_mask & both_present)).sum(axis=1, min_count=1)
    down_vol = (vol.where(dn_mask & both_present)).sum(axis=1, min_count=1)
    up_pts = (dpx.where(up_mask & both_present)).sum(axis=1, min_count=1)
    down_pts = ((-dpx).where(dn_mask & both_present)).sum(axis=1, min_count=1)
    n_reporting = both_present.sum(axis=1)

    out = pd.DataFrame({
        "up_vol": up_vol,
        "down_vol": down_vol,
        "up_pts": up_pts,
        "down_pts": down_pts,
        "n_reporting": n_reporting.astype(float),
    })
    out = out[out["n_reporting"] >= 300]
    # On extreme days (all-up or all-down) min_count=1 leaves the empty side as NaN.
    # Fill those to 0 so that ratio metrics (e.g. down_vol/(up_vol+down_vol)) produce
    # 0/1 on the very days that matter most for Lowry/Desmond 90%-day detection.
    out[["up_vol", "down_vol", "up_pts", "down_pts"]] = (
        out[["up_vol", "down_vol", "up_pts", "down_pts"]].fillna(0.0)
    )
    return out.dropna(how="all", subset=["up_vol", "down_vol"])


_STALE_CAL_DAYS = 7  # cross-ref: engine.name_score_grader._MAX_BAR_LAG_DAYS /
# collectors.yahoo._STALE_CAL_DAYS — the SAME 7-calendar-day staleness law, duplicated
# here because collectors must not import engine (layering).


def disclose_stale_constituent_columns(members_symbols, closes: pd.DataFrame,
                                       group_name: str) -> dict:
    """Current-constituent column disclosure (R4, research/ADJUDICATION_20260803_
    UNIVERSE_SIDE_STORE_FRESHNESS.md). ``_merge_refreshed``'s
    ``fresh.combine_first(cached)`` is a deliberate FEATURE (a survivorship-honest
    perpetual archive for replay/backtest readers) — it must never prune history.
    But it also means a symbol Yahoo silently stops returning (CWEN-A: dead at
    Yahoo since 2026-06-26, sibling CWEN advancing daily in the same batches)
    carries its frozen column forward every night, byte-identical to a departed
    name, with zero disclosure. This only classifies CURRENT members (a name
    Wikipedia already dropped is correctly gone — no disclosure owed there).

    Classifies each symbol in ``members_symbols`` against ``closes``:
      no column          — symbol absent from the closes matrix entirely
      never populated     — column present but 100% NaN (FI/MMC class)
      frozen(tip)          — column's own last non-NaN obs is more than
                            _STALE_CAL_DAYS behind the merged frame's overall tip
    Bare ::warning (cap 15) if any non-empty category; annotation law — never
    through the logger. Returns {"no_column": [...], "never_populated": [...],
    "frozen": {ticker: tip}} so a caller/test can assert on the classification
    without re-parsing the printed text."""
    no_column: list[str] = []
    never_populated: list[str] = []
    frozen: dict[str, str] = {}
    if closes is None or closes.empty:
        return {"no_column": list(members_symbols), "never_populated": [], "frozen": {}}
    # the merged frame's own overall tip — the freshest date ANY column still carries
    # data for (closes.index.max() is not reliable once trailing rows are all-NaN).
    _nonempty = closes.dropna(axis=1, how="all")
    overall_tip = _nonempty.index[_nonempty.notna().any(axis=1)].max() if not _nonempty.empty else None
    for sym in members_symbols:
        if sym not in closes.columns:
            no_column.append(sym)
            continue
        col = closes[sym].dropna()
        if col.empty:
            never_populated.append(sym)
            continue
        if overall_tip is not None:
            tip = col.index.max()
            if (pd.Timestamp(overall_tip) - pd.Timestamp(tip)).days > _STALE_CAL_DAYS:
                frozen[sym] = str(pd.Timestamp(tip).date())
    if no_column or never_populated or frozen:
        parts: list[str] = []
        if no_column:
            shown = sorted(no_column)[:15]
            more = len(no_column) - len(shown)
            parts.append(f"no column ({len(no_column)}): {', '.join(shown)}"
                         f"{f', +{more} more' if more > 0 else ''}")
        if never_populated:
            shown = sorted(never_populated)[:15]
            more = len(never_populated) - len(shown)
            parts.append(f"never populated ({len(never_populated)}): {', '.join(shown)}"
                         f"{f', +{more} more' if more > 0 else ''}")
        if frozen:
            shown = sorted(frozen)[:15]
            more = len(frozen) - len(shown)
            parts.append(f"frozen ({len(frozen)}): "
                         f"{', '.join(f'{t}({frozen[t]})' for t in shown)}"
                         f"{f', +{more} more' if more > 0 else ''}")
        print(f"::warning title={group_name} breadth constituents not refreshing::"
              f"{'; '.join(parts)}", flush=True)
    # M1: self-relative blindness backstop — the `frozen` check above is relative to
    # overall_tip (this merged frame's own tip), so a TOTAL freeze (every constituent
    # frozen together, e.g. the whole download host down) is invisible to it. Disclosure
    # only, against wall-clock now — never a gate.
    if overall_tip is not None:
        _now = pd.Timestamp.utcnow().tz_localize(None)
        _tip_ts = pd.Timestamp(overall_tip)
        if _tip_ts.tzinfo is not None:
            _tip_ts = _tip_ts.tz_localize(None)
        _behind_wall = (_now.normalize() - _tip_ts.normalize()).days
        if _behind_wall > _STALE_CAL_DAYS:
            print(f"::warning title={group_name} breadth tip stale::overall tip "
                  f"{_tip_ts.date()} is >{_STALE_CAL_DAYS}d behind today — possible "
                  "collector outage", flush=True)
    return {"no_column": no_column, "never_populated": never_populated, "frozen": frozen}


@dataclass(frozen=True)
class BreadthPriceAcquisition:
    """Detached values and observed qualification, never publication authority."""
    accepted: bool
    reason: str
    source_session: str
    members: pd.DataFrame
    panels: Mapping[str, pd.DataFrame]
    current: tuple[str, ...]
    unresolved: tuple[str, ...]
    repaired: tuple[str, ...]
    departed: tuple[str, ...]
    evidence: Mapping[str, object]


def _download_batches(tickers, period, *, batch_size, retries, backoff_base_s, consume):
    """The incumbent breadth retry/batching owner, shared by both adapters."""
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        for attempt in range(retries):
            try:
                df = yf.download(batch, period=period, auto_adjust=True,
                                 progress=False, group_by="column", threads=True)
                consume(batch, df)
                break
            except Exception as e:  # noqa: BLE001
                wait = backoff_base_s * (2 ** attempt)
                log.warning("breadth batch %d failed (%s); retry in %.0fs", i // batch_size, e, wait)
                time.sleep(wait)
        time.sleep(1)


def capture_adjusted_policy(policy: Mapping) -> dict:
    """Detach and validate the native acquisition policy before provider work."""
    from lib.adjusted_price_capture import AdjustedCaptureError
    if not isinstance(policy, Mapping):
        raise AdjustedCaptureError("invalid_breadth_policy")
    cfg = deepcopy(dict(policy))
    windows, nhw, lookback = (cfg.get(key) for key in
                              ("ma_windows", "nhnl_window", "lookback_days_live"))
    fixups = cfg.get("ticker_fixups") or {}
    if (not isinstance(windows, (list, tuple)) or len(windows) != 2
            or any(type(v) is not int or v < 1 for v in windows)
            or type(nhw) is not int or nhw < 1 or type(lookback) is not int or lookback < 1
            or not isinstance(fixups, dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in fixups.items())):
        raise AdjustedCaptureError("invalid_breadth_policy")
    cfg["ma_windows"], cfg["ticker_fixups"] = list(windows), fixups
    return cfg


class BreadthAdapter(Adapter):
    name = "breadth"
    group = "breadth"

    def __init__(self, *, breadth_config: Mapping | None = None,
                 yahoo_config: Mapping | None = None) -> None:
        if breadth_config is None and yahoo_config is None:
            self.cfg = config.load()[self.group]
            self.ycfg = config.load()["yahoo"]
            self.cache_path = config.data_dir() / self.group / "_closes_cache.parquet"
        elif isinstance(breadth_config, Mapping) and isinstance(yahoo_config, Mapping):
            self.cfg = deepcopy(dict(breadth_config))
            self.ycfg = deepcopy(dict(yahoo_config))
            self.cache_path = None
        else:
            raise ValueError("Both explicit breadth and Yahoo configurations are required")

    def constituents(self) -> pd.DataFrame:
        r = self.http_get(self.cfg["constituents_url"], retries=3,
                          headers={"User-Agent": "Mozilla/5.0 (macro-dashboard research)"})
        tables = pd.read_html(io.StringIO(r.text))
        for t in tables:
            if "Symbol" in t.columns:
                t = t.rename(columns={"Symbol": "symbol", "Security": "name",
                                      "GICS Sector": "sector"})
                return self._repair(t[["symbol", "name", "sector"]])
        raise ValueError("constituents table not found on Wikipedia page")

    @staticmethod
    def sanitize_company_name(name) -> str:
        """Strip TRANSPORT residue from a scraped company name — nothing else.

        The constituent tables are parsed out of community-edited wiki markup, where
        "|" is the cell delimiter. One leaked into the S&P 500 table and made RMD's
        issuer "ResMed|", which then reached every downstream identity surface of the
        public dossier: the <title>, the meta description, OpenGraph, the JSON-LD
        Corporation.name and the visible company name. The name field had no cleanup
        at all here, while `symbol` next to it had three.

        Deliberately narrow. A pipe is a delimiter and is never part of a company
        name, so text after one is a leaked neighbouring cell. Legitimate punctuation
        is LOAD-BEARING and must survive untouched: "AT&T", "Johnson & Johnson",
        "O'Reilly Automotive", "Berkshire Hathaway Inc.", "Alphabet Inc. (Class A)",
        "Coca-Cola". Only a delimiter run at the very edge of the string is removed."""
        s = " ".join(str(name or "").split())
        if not s:
            return ""
        if "|" in s:                      # keep the first real cell, drop the rest
            s = next((p.strip() for p in s.split("|") if p.strip()), "")
        s = re.sub(r"^[|;,/\s]+", "", s)
        s = re.sub(r"[|;,/\s]+$", "", s)  # trailing delimiter run; "Inc." keeps its dot
        return " ".join(s.split())

    def _repair(self, members: pd.DataFrame, *, ticker_fixups: Mapping | None = None,
                excluded_symbols: frozenset[str] | None = None) -> pd.DataFrame:
        """Clean a freshly-scraped constituents table before it becomes the universe.

        Wikipedia is community-edited and ships the occasional non-ticker junk cell,
        which is dropped outright. It also ships symbols that are perfectly correct but
        disagree with the key this repo stores a company under, because a TICKER RENAME
        moved one side and not the other (Fiserv FISV->FI in 2023, where the page kept
        the old symbol; Marsh McLennan MMC->MRSH on 2026-01-14, where the page took the
        new one). Left unpinned those silently split one company across two universe
        keys. This normalises symbols, drops junk, and applies the config
        ``ticker_fixups`` map (scraped symbol -> the stored key).

        ``ticker_fixups`` is a KEY PIN, not a claim about which symbol trades today —
        see the config comment before changing a row; the price feed's own view of the
        same renames lives in lib/ticker_aliases. Pure + logged; never raises."""
        df = members.copy()
        df["symbol"] = (df["symbol"].astype(str).str.strip().str.upper()
                        .str.replace(".", "-", regex=False))         # BRK.B -> BRK-B
        # drop non-ticker junk (vandalism, footnote artefacts) before it poisons ratios
        ok = df["symbol"].str.match(_TICKER_RE)
        if not ok.all():
            log.warning("%s constituents: dropping %d non-ticker row(s): %s",
                        self.name, int((~ok).sum()), df.loc[~ok, "symbol"].tolist()[:10])
            df = df[ok]
        # repair known-bad symbols (vandalism / stale renames) -> the real ticker
        repair_map = (self.cfg.get("ticker_fixups") or {}) if ticker_fixups is None else ticker_fixups
        fixups = {str(k).strip().upper(): str(v).strip().upper()
                  for k, v in repair_map.items()}
        if fixups:
            hit = df["symbol"].isin(fixups)
            if hit.any():
                log.info("%s constituents: repaired %d Wikipedia ticker(s): %s",
                         self.name, int(hit.sum()),
                         {s: fixups[s] for s in sorted(df.loc[hit, "symbol"].unique())})
                df["symbol"] = df["symbol"].map(lambda s: fixups.get(s, s))
        # drop securities the exit ledger says stopped existing: Wikipedia's index
        # tables lag a merger close by days, and one lagging row re-admits a dead
        # symbol to the universe every night — the fetch then requests a tape that
        # can never return (LEG, 2026-08: Form 25 filed 08-27, page still listed it).
        # lib.delisted_symbols fails open, so an unreadable ledger drops nothing.
        excluded = delisted_symbols.tickers() if excluded_symbols is None else excluded_symbols
        dead = df["symbol"].isin(excluded)
        if dead.any():
            log.info("%s constituents: dropping %d delisted symbol(s) per the exit "
                     "ledger: %s", self.name, int(dead.sum()),
                     sorted(df.loc[dead, "symbol"].unique()))
            df = df[~dead]
        # strip wiki-markup transport residue from the ISSUER NAME (see
        # sanitize_company_name) — this is the canonical boundary the whole US
        # dossier estate inherits its company names from, so a stray delimiter
        # repaired here never reaches a <title>, a JSON-LD block or an OG tag.
        raw_names = df["name"].astype(str)
        df["name"] = raw_names.map(self.sanitize_company_name)
        changed = raw_names[raw_names != df["name"]]
        if not changed.empty:
            log.info("%s constituents: sanitised %d company name(s): %s",
                     self.name, len(changed),
                     {df.loc[i, "symbol"]: (raw_names[i], df.loc[i, "name"])
                      for i in list(changed.index)[:5]})
        # a repair can collide with an already-correct row -> keep one
        df = df.drop_duplicates(subset="symbol", keep="first").reset_index(drop=True)
        return df[["symbol", "name", "sector"]]

    def _download_closes(self, tickers: list[str], period: str) -> pd.DataFrame:
        parts: list[pd.DataFrame] = []
        extras: dict[str, list] = {"high": [], "low": [], "volume": []}
        def consume(batch, df):
            lvl0 = (df.columns.get_level_values(0)
                    if isinstance(df.columns, pd.MultiIndex) else df.columns)
            parts.append(df["Close"] if "Close" in lvl0 else df)
            for k, field in (("high", "High"), ("low", "Low"), ("volume", "Volume")):
                if field in lvl0:
                    extras[k].append(df[field])
        _download_batches(tickers, period, batch_size=self.ycfg["batch_size"],
            retries=self.ycfg["retries"], backoff_base_s=self.ycfg["backoff_base_s"], consume=consume)
        if not parts:
            raise RuntimeError("no constituent closes downloaded")

        def _wide(plist: list) -> pd.DataFrame:
            w = pd.concat(plist, axis=1)
            return w.loc[:, ~w.columns.duplicated()].sort_index()

        self._last_extras = {k: _wide(v) for k, v in extras.items() if v}
        return _wide(parts)

    def _download_adjusted_capture(self, tickers: tuple[str, ...], period: str, *,
                                   request_settings, source_session: str):
        from lib.adjusted_price_capture import capture_adjusted_response, combine_adjusted_captures
        captures = []
        def consume(batch, frame):
            # Append only after the entire batch has been validated/detached.
            captures.append(capture_adjusted_response(frame, requested=tuple(batch),
                                                       source_session=source_session))
        _download_batches(list(tickers), period, batch_size=request_settings.batch_size,
            retries=request_settings.retries, backoff_base_s=request_settings.backoff_base_s,
            consume=consume)
        return combine_adjusted_captures(captures, requested=tickers)

    def acquire_adjusted_prices(self, *, members: pd.DataFrame, prior_panels: Mapping,
                                excluded_symbols: frozenset[str], aliases: Mapping,
                                evaluation_instant: datetime, period: str = "1mo") -> BreadthPriceAcquisition:
        """Capture a completed four-field cohort without any legacy file effects.

        Request values are detached before provider access. The whole archive is
        retained, but current qualification uses active members observed in this
        acquisition only. This method does not flip the global ownership profile.
        """
        from collectors.yahoo import YahooRequestSettings
        from lib import market_session
        from lib.adjusted_price_capture import (capture_panels, merge_adjusted_capture,
            remap_adjusted_capture, AdjustedCaptureError, FIELDS)
        cfg = capture_adjusted_policy(self.cfg)
        request = YahooRequestSettings.capture(self.ycfg)
        if (not isinstance(evaluation_instant, datetime) or evaluation_instant.tzinfo is None
                or evaluation_instant.utcoffset() is None or not isinstance(period, str)
                or not isinstance(excluded_symbols, frozenset)
                or any(not isinstance(t, str) for t in excluded_symbols)
                or not isinstance(aliases, Mapping)):
            raise AdjustedCaptureError("invalid_breadth_request")
        evaluation = evaluation_instant.astimezone(timezone.utc)
        local = market_session.market_local_date("US", evaluation)
        target = market_session.expected_session("US", evaluation)
        if (not market_session.calendar_verified("US", local.year)
                or not market_session.calendar_verified("US", target.year)):
            raise AdjustedCaptureError("target_calendar_unavailable")
        source = target.isoformat()
        windows = cfg.get("ma_windows")
        nhw = cfg.get("nhnl_window")
        lookback = cfg.get("lookback_days_live")
        depth = max(*windows, nhw)
        cold_period = f"{max(1, lookback // 365 + 1)}y"
        if period not in ("1mo", "max", cold_period):
            raise AdjustedCaptureError("invalid_breadth_period")
        if (not isinstance(members, pd.DataFrame) or members.columns.has_duplicates
                or not {"symbol", "name", "sector"}.issubset(members.columns)
                or len(members) > 10_000
                or any(not isinstance(v, str) for v in members["symbol"])
                or any(not isinstance(v, str) for v in members["name"])
                or any(not (isinstance(v, str) or v is None or v is pd.NA
                           or isinstance(v, float) and math.isnan(v)) for v in members["sector"])):
            raise AdjustedCaptureError("invalid_breadth_membership")
        repaired_members = self.constituents_checked(self._repair(members.copy(deep=True),
            ticker_fixups=deepcopy(cfg.get("ticker_fixups") or {}), excluded_symbols=excluded_symbols))
        active = tuple(repaired_members["symbol"])
        if (len(active) > 5000 or any(not _TICKER_RE.fullmatch(t) for t in active)
                or len(set(active)) != len(active)):
            raise AdjustedCaptureError("invalid_breadth_membership")
        alias_values = deepcopy(dict(aliases))
        mapping = {t: alias_values.get(t, t) for t in active}
        if any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^=-]{0,23}", v)
               for v in mapping.values()) or len(set(mapping.values())) != len(mapping):
            raise AdjustedCaptureError("vendor_alias_collision_or_invalid")
        previous = capture_panels(prior_panels, source_session=source, allow_absent=True)
        if period == cold_period and any(not panel.empty for panel in previous.values()):
            raise AdjustedCaptureError("finite_cold_period_requires_empty_prior")
        raw = self._download_adjusted_capture(tuple(mapping.values()), period,
            request_settings=request, source_session=source)
        initial = remap_adjusted_capture(raw, canonical_to_vendor=mapping)
        arguments = dict(prior=previous, fresh=initial, active=active, source_session=source,
                         basis_tolerance=request.basis_tolerance, minimum_repair_sessions=depth,
                         full_replacement=period != "1mo")
        tentative = merge_adjusted_capture(**arguments)
        scan = tentative.panels["close"].reindex(columns=active)
        scan = scan.loc[scan.index >= pd.Timestamp(source) - pd.Timedelta(days=_SEAM_SCAN_DAYS)]
        suspects = tuple(seam_suspects(None, None, scan)) if period == "1mo" else ()
        arguments["residual_suspects"] = suspects
        tentative = merge_adjusted_capture(**arguments)
        repair_capture = None
        if tentative.needs_repair and period == "1mo":
            repair_map = {t: mapping[t] for t in tentative.needs_repair}
            # One full-history recovery preserves prior depth across basis changes.
            repair_raw = self._download_adjusted_capture(tuple(repair_map.values()), "max",
                request_settings=request, source_session=source)
            repair_capture = remap_adjusted_capture(repair_raw, canonical_to_vendor=repair_map)
        result = merge_adjusted_capture(**arguments, repair=repair_capture)
        required = math.ceil(len(active) * 0.8)
        accepted = len(result.current) >= required
        archive = set().union(*(set(panel.columns) for panel in result.panels.values()))
        member_evidence = {}
        for ticker in active:
            selected_capture = (initial if ticker not in result.repaired or period != "1mo" else repair_capture)
            span = selected_capture.spans.get(ticker) if selected_capture is not None else None
            member_evidence[ticker] = {"vendor_symbol": mapping[ticker],
                "initial_span": [s.date().isoformat() for s in initial.spans[ticker]] if ticker in initial.spans else None,
                "accepted_span": [s.date().isoformat() for s in span] if ticker in result.current and span else None,
                "repair_reason": result.reasons.get(ticker),
                "repaired": ticker in result.repaired, "current": ticker in result.current,
                "unresolved": ticker in result.unresolved}
        evidence = {"evaluation_instant": evaluation.isoformat(), "source_session": source,
            "completed_sessions_only": True, "target_calendar_verified": True,
            "basis": "provider_auto_adjusted", "fields": list(FIELDS),
            "selection_policy": {"ma_windows": list(windows), "nhnl_window": nhw,
                "ticker_fixups": deepcopy(cfg.get("ticker_fixups") or {}),
                "excluded_symbols": sorted(excluded_symbols)},
            "active_members": len(active), "current_members": len(result.current), "required_current": required,
            "request": {"period": period, "recovery_period": "max" if repair_capture is not None else None,
                "batch_size": request.batch_size, "retries": request.retries,
                "backoff_base_s": request.backoff_base_s, "basis_tolerance": request.basis_tolerance,
                "minimum_repair_sessions": depth, "calculation_lookback_days": lookback},
            "members": member_evidence,
            "unknown": {"vendor_publication_clock": "Not supplied per bar by yfinance",
                        "provider_available_at": "First retrievable time is not observed"}}
        return BreadthPriceAcquisition(accepted, "accepted" if accepted else "active_target_coverage_insufficient",
            source, repaired_members.copy(deep=True), result.panels, result.current, result.unresolved,
            result.repaired, tuple(sorted(archive - set(active))), MappingProxyType(evidence))

    def _merge_refreshed(self, fresh: pd.DataFrame, cached: pd.DataFrame) -> pd.DataFrame:
        """``fresh.combine_first(cached)`` + split-seam repair (see module comment).

        Flagged tickers get their FULL live window re-downloaded (one batched
        call) and the column replaced wholesale — correct whether the flag was
        a real seam (stale basis replaced by a coherent adjusted history) or a
        genuine ±40% news day (the re-pull returns identical data). The
        re-pulled tickers' OHLCV extras are grafted over the fresh-window
        extras so the _high/_low/_volume caches heal on the same run. If the
        re-pull fails the poisoned columns are LEFT IN PLACE (loud warning):
        the scan re-flags them next run, whereas truncating them would erase
        the evidence and silently orphan the seam in the extras caches."""
        merged = fresh.combine_first(cached)
        bad = seam_suspects(fresh, cached, merged)
        if not bad:
            return merged
        days = self.cfg["lookback_days_live"]
        log.warning("%s: %d ticker(s) with mixed adjustment basis in the closes cache "
                    "(split seam) — re-pulling full window: %s",
                    self.name, len(bad), bad[:12])
        fresh_extras = getattr(self, "_last_extras", {}) or {}
        try:
            repull = self._download_closes(bad, f"{max(1, days // 365 + 1)}y")
        except Exception as e:  # noqa: BLE001 — repair must never kill the run
            log.warning("%s: seam re-pull failed (%s) — cache kept as-is; the seam "
                        "scan retries next run", self.name, e)
            self._last_extras = fresh_extras
            return merged
        repull_extras = getattr(self, "_last_extras", {}) or {}
        self._last_extras = fresh_extras
        healed = [t for t in bad if t in repull.columns and repull[t].notna().any()]
        for t in healed:
            merged[t] = repull[t].reindex(merged.index)
        if missed := sorted(set(bad) - set(healed)):
            log.warning("%s: seam re-pull returned no data for %s — kept as-is, "
                        "retried next run", self.name, missed[:12])
        for k, w in list(fresh_extras.items()):
            rw = repull_extras.get(k)
            # NOT filtered by `t in w.columns` (2026-08-06 split-basis incident): w is the
            # FRESH 1mo window, and a healed ticker missing from it — yfinance returned no
            # High/Low for that name in that batch — is exactly the case where the extras
            # cache still holds the OLD basis. Skipping it there healed the closes and left
            # high/low re-based, with no warning (the closes half succeeded), which is the
            # one split shape no scanner in the tree can see: seam_suspects only ever reads
            # the closes matrix. The assignment below creates the column when absent, and
            # the union reindex already guarantees it spans the extras cache's rows.
            cols = [t for t in healed if rw is not None and t in rw.columns]
            if not cols:
                continue
            # union index: the grafted column must span the extras CACHE's rows,
            # not just the 1mo fresh window, so combine_first in fetch() overrides
            # the poisoned cached rows instead of keeping them
            w = w.reindex(w.index.union(rw.index)).sort_index()
            for t in cols:
                w[t] = rw[t].reindex(w.index)
            fresh_extras[k] = w
        return merged

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        if self.cache_path is None:
            raise ValueError("Explicit breadth configuration requires acquire_adjusted_prices")
        members = self.constituents_checked(self.constituents())
        tickers = members["symbol"].tolist()

        if full_history:
            closes = self._download_closes(tickers, "max")
        else:
            closes = None
            if self.cache_path.exists():
                cached = pd.read_parquet(self.cache_path)
                # refresh tail; full re-pull if cache is stale beyond the overlap
                age = (pd.Timestamp.utcnow().tz_localize(None) - cached.index.max()).days
                if age <= 14:
                    fresh = self._download_closes(tickers, "1mo")
                    closes = self._merge_refreshed(fresh, cached)
            if closes is None:
                days = self.cfg["lookback_days_live"]
                closes = self._download_closes(tickers, f"{max(1, days // 365 + 1)}y")
            cutoff = closes.index.max() - pd.Timedelta(days=self.cfg["lookback_days_live"] + 30)
            closes = closes[closes.index >= cutoff]

        # R4 current-constituent column disclosure (CWEN-A class): a symbol Yahoo
        # silently stops returning is otherwise indistinguishable from a departed
        # member — combine_first carries the frozen column forward forever, silently.
        # NIT fix: this runs BEFORE the coverage-sanity raise below — the run that
        # most needs this report (sparse enough to abort) is exactly the one a
        # post-raise placement would have denied it to.
        try:
            disclose_stale_constituent_columns(tickers, closes, self.name)
        except Exception as e:  # noqa: BLE001 — disclosure must never break the run
            log.warning("%s: constituent freshness disclosure failed (%s)", self.name, e)

        # coverage sanity: a half-empty matrix silently poisons every ratio
        live_cols = closes.dropna(axis=1, how="all").shape[1]
        if live_cols < len(tickers) * 0.8:
            raise RuntimeError(f"breadth closes too sparse: {live_cols}/{len(tickers)}")

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_history:
            closes.to_parquet(self.cache_path)
            # ADDITIVE: persist the OHLCV extras the download already captured, with the
            # SAME tail-refresh + window logic as closes. Never fatal — breadth itself
            # only needs closes; the stock library falls back to close-only when absent.
            try:
                cutoff_e = closes.index.max() - pd.Timedelta(days=self.cfg["lookback_days_live"] + 30)
                for k, w in (getattr(self, "_last_extras", {}) or {}).items():
                    ep = self.cache_path.parent / f"_{k}_cache.parquet"
                    if ep.exists():
                        w = w.combine_first(pd.read_parquet(ep))
                    w[w.index >= cutoff_e].to_parquet(ep)
            except Exception as e:  # noqa: BLE001
                log.warning("breadth OHLCV extras cache failed (%s) — volume signals close-only", e)
        # constituents list is reference data, not a time series — written directly.
        # Log membership churn vs the prior committed list so a vandalised / partial
        # scrape that silently drops real members is visible in the run output.
        cpath = self.cache_path.parent / "constituents.parquet"
        try:
            if cpath.exists():
                prior = set(pd.read_parquet(cpath).index)
                new = set(members["symbol"])
                added, dropped = new - prior, prior - new
                if added or dropped:
                    log.info("%s constituents churn: +%d -%d (added %s; dropped %s)",
                             self.name, len(added), len(dropped),
                             sorted(added)[:8], sorted(dropped)[:8])
        except Exception as e:  # noqa: BLE001 — observability only, never fatal
            log.warning("%s constituents churn log failed (%s)", self.name, e)
        members.set_index("symbol").to_parquet(cpath)

        out = {"breadth": self.compute(closes)}
        # per-GICS-sector breadth (rotation-tensor breadth-migration gap,
        # 2026-07-02 incident handoff H5): same closes matrix, split by the
        # sector labels already on the constituents table. Never fatal —
        # market-wide breadth must ship even if the sector split fails.
        try:
            sb = self.compute_sectors(closes, members)
            if sb is not None and not sb.empty:
                out["sector_breadth"] = sb
        except Exception as e:  # noqa: BLE001 — additive, never fatal
            log.warning("breadth sector split failed (%s) — market-wide only", e)
        # W2: up/down volume + points aggregate — accruing nightly into updown.parquet.
        # Volume comes from _volume_cache.parquet, a TRACKED committed store written
        # earlier in this same breadth run.  The try/except is a fail-soft for the case
        # where the cache write was skipped (e.g. network outage) or the file is corrupt.
        try:
            vcache = self.cache_path.parent / "_volume_cache.parquet"
            if vcache.exists():
                vol_df = pd.read_parquet(vcache).reindex(index=closes.index,
                                                          columns=closes.columns)
                new_updown = compute_updown(closes, vol_df)
                if not new_updown.empty:
                    udpath = self.cache_path.parent / "updown.parquet"
                    if udpath.exists():
                        old_updown = pd.read_parquet(udpath)
                        # combine_first by date: new rows win, old history preserved (no-regress)
                        merged_ud = new_updown.combine_first(old_updown)
                        merged_ud = merged_ud.sort_index()
                    else:
                        merged_ud = new_updown.sort_index()
                    merged_ud.to_parquet(udpath)
                    log.info("breadth updown: %d total rows (W2 accrual)", len(merged_ud))
            else:
                log.info("breadth updown: volume cache absent — updown.parquet not updated")
        except Exception as e:  # noqa: BLE001 — updown must never break the breadth build
            log.warning("breadth updown accrual failed (%s) — breadth.parquet unaffected", e)
        return out

    def compute_sectors(self, closes: pd.DataFrame,
                        members: pd.DataFrame) -> pd.DataFrame | None:
        """pct_above_50 / pct_above_200 / n_members per GICS sector, wide frame
        with flat '<sector>|<metric>' columns (parquet-friendly). Same MA windows
        and partial-row discipline as the market-wide compute()."""
        if "sector" not in members.columns:
            return None
        w50, w200 = self.cfg["ma_windows"]
        sec_map = members.set_index("symbol")["sector"].dropna()
        ma50 = closes.rolling(w50, min_periods=w50).mean()
        ma200 = closes.rolling(w200, min_periods=w200).mean()
        cols = {}
        for sector, syms in sec_map.groupby(sec_map).groups.items():
            tick = [t for t in syms if t in closes.columns]
            if len(tick) < 5:  # a sector this thin would print noise
                continue
            c, m50, m200 = closes[tick], ma50[tick], ma200[tick]
            n50 = m50.notna().sum(axis=1)
            n200 = m200.notna().sum(axis=1)
            cols[f"{sector}|pct_above_50"] = (
                100 * (c > m50).sum(axis=1) / n50.where(n50 > 0)).astype(float)
            cols[f"{sector}|pct_above_200"] = (
                100 * (c > m200).sum(axis=1) / n200.where(n200 > 0)).astype(float)
            cols[f"{sector}|n"] = c.notna().sum(axis=1).astype(float)
        if not cols:
            return None
        out = pd.DataFrame(cols).dropna(how="all")
        p50 = [c for c in out.columns if c.endswith("|pct_above_50")]
        return out.dropna(subset=p50, how="all")

    def compute(self, closes: pd.DataFrame) -> pd.DataFrame:
        w50, w200 = self.cfg["ma_windows"]
        nhw = self.cfg["nhnl_window"]
        valid = closes.notna()
        ma50 = closes.rolling(w50, min_periods=w50).mean()
        ma200 = closes.rolling(w200, min_periods=w200).mean()
        out = pd.DataFrame(index=closes.index)
        out["n_members"] = valid.sum(axis=1)
        out["pct_above_50"] = 100 * (closes > ma50).sum(axis=1) / ma50.notna().sum(axis=1)
        out["pct_above_200"] = 100 * (closes > ma200).sum(axis=1) / ma200.notna().sum(axis=1)
        roll_hi = closes.rolling(nhw, min_periods=nhw).max()
        roll_lo = closes.rolling(nhw, min_periods=nhw).min()
        out["nh"] = (closes >= roll_hi).sum(axis=1)
        out["nl"] = (closes <= roll_lo).sum(axis=1)
        chg = closes.diff()
        out["adv"] = (chg > 0).sum(axis=1)
        out["dec"] = (chg < 0).sum(axis=1)
        out["ad_line"] = (out["adv"] - out["dec"]).cumsum()
        out = out.dropna(subset=["pct_above_50"])
        # partial rows (e.g. an in-progress trading day where only a handful of
        # tickers have printed) would poison every ratio — drop them
        return out[out["n_members"] >= out["n_members"].rolling(20, min_periods=1).max() * 0.8]

    def constituents_checked(self, members: pd.DataFrame) -> pd.DataFrame:
        if members.empty or len(members) < 400:
            raise ValueError(f"constituents list suspicious: {len(members)} rows")
        return members


def breadth_summary(br: pd.DataFrame | None, full: bool) -> dict | None:
    """Latest-row breadth read for the regional dashboard cards (China / HK / Canada).

    Pure function of a computed breadth frame (the 8-column output of
    ``BreadthAdapter.compute``). Returns the fields the cards already used plus a
    plain-language participation read — ``state`` (broad / thin / mixed), ``tone``,
    and ``net_nh`` — mirroring the US S&P-1500 scorecard's thresholds so the regional
    pages answer the same "how many stocks are actually participating" question.
    DISPLAY-ONLY (never scored). ``full`` flags whether the source was the full
    searchable universe (True) or the curated large-cap gauge (False)."""
    if br is None or br.empty:
        return None
    last = br.iloc[-1]
    pa50 = float(last.get("pct_above_50", float("nan")))
    nh, nl = int(last.get("nh", 0) or 0), int(last.get("nl", 0) or 0)
    net_nh = nh - nl
    # same thresholds as build_site._breadth_read (the US scorecard) — % above the
    # 50-day line is normalized 0-100 so the bands port across markets unchanged
    if pa50 >= 60 and net_nh >= 0:
        state, tone = "broad", "pos"
    elif pa50 <= 40 or net_nh < 0:
        state, tone = "thin", "neg"
    else:
        state, tone = "mixed", "muted"
    try:
        chg20 = round(float(br["pct_above_50"].diff(20).iloc[-1]), 1)
    except Exception:  # noqa: BLE001 — short history → no 20d change
        chg20 = 0.0
    return {
        "pct_above_50": round(pa50, 1),
        "pct_above_200": round(float(last.get("pct_above_200", float("nan"))), 1),
        "nh": nh, "nl": nl, "net_nh": net_nh,
        "adv": int(last.get("adv", 0) or 0), "dec": int(last.get("dec", 0) or 0),
        "ad_trend": "up" if br["ad_line"].diff(20).iloc[-1] > 0 else "down",
        "n_members": int(last.get("n_members", 0) or 0),
        "pct50_chg20": chg20,
        "state": state, "tone": tone, "full": bool(full),
        "asof": pd.Timestamp(last.name).strftime("%Y-%m-%d"),
    }
