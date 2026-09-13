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
from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf

from collectors.base import Adapter
from lib import config, delisted_symbols, nyse_calendar

log = logging.getLogger(__name__)


class LicensedSourceError(RuntimeError):
    """A licensed-vendor daily-history request could not be qualified for W1 use.

    Never a partial result: the caller must re-fetch the whole window rather than
    splice a fresh read onto an older, possibly differently-adjusted cache (W1
    source ruling, research/skylit/W1_SOURCE_IMPLEMENTATION_RULING_2026-09-11.md §2).
    """


#: research/skylit/W1_SOURCE_IMPLEMENTATION_RULING_2026-09-11.md §2 / §"Why this is
#: not a new data platform": of the stores inspected, the ONLY one covered by the
#: Massive entitlement (research/licenses/MASSIVE_ENTITLEMENT_RECORD.md) is
#: collectors/massive_stock_day.py, and it is RAW — see lib/dataos/price.py
#: KNOWN_STORE_BASES. Every *adjusted* store inspected (data/stocks, data/yahoo,
#: baskets_ohlcv, baskets_extras, and this module's own _closes_cache.parquet) is
#: yfinance-derived, and no qualified licensed provenance has been established for
#: any of them — a limitation of what was inspected, not a claim that no adjusted
#: store anywhere could ever carry one. W1_LICENSED_BASIS names what THIS reader
#: actually returns, straight from the licensed vendor's own adjusted=true
#: aggregate — closing that gap directly rather than reusing either existing side.
W1_LICENSED_BASIS = "split_adjusted"

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


class BreadthAdapter(Adapter):
    name = "breadth"
    group = "breadth"

    def __init__(self) -> None:
        self.cfg = config.load()["breadth"]
        self.ycfg = config.load()["yahoo"]
        self.cache_path = config.data_dir() / "breadth" / "_closes_cache.parquet"

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

    def _repair(self, members: pd.DataFrame) -> pd.DataFrame:
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
        fixups = {str(k).strip().upper(): str(v).strip().upper()
                  for k, v in (self.cfg.get("ticker_fixups") or {}).items()}
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
        dead = df["symbol"].isin(delisted_symbols.tickers())
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
        bs = self.ycfg["batch_size"]
        parts: list[pd.DataFrame] = []
        # ADDITIVE OHLCV capture: yfinance already downloads high/low/volume — keep them
        # (instead of discarding all but Close) so the stock library can compute
        # volume-based signals (engine/bottom_radar) for the full universe, not just the
        # ~114 deep names. Stashed on self for fetch() to cache; never affects closes.
        extras: dict[str, list] = {"high": [], "low": [], "volume": []}
        for i in range(0, len(tickers), bs):
            batch = tickers[i:i + bs]
            for attempt in range(self.ycfg["retries"]):
                try:
                    df = yf.download(batch, period=period, auto_adjust=True,
                                     progress=False, group_by="column", threads=True)
                    lvl0 = (df.columns.get_level_values(0)
                            if isinstance(df.columns, pd.MultiIndex) else df.columns)
                    parts.append(df["Close"] if "Close" in lvl0 else df)
                    for k, F in (("high", "High"), ("low", "Low"), ("volume", "Volume")):
                        if F in lvl0:
                            extras[k].append(df[F])
                    break
                except Exception as e:  # noqa: BLE001
                    wait = self.ycfg["backoff_base_s"] * (2 ** attempt)
                    log.warning("breadth batch %d failed (%s); retry in %.0fs", i // bs, e, wait)
                    time.sleep(wait)
            time.sleep(1)
        if not parts:
            raise RuntimeError("no constituent closes downloaded")

        def _wide(plist: list) -> pd.DataFrame:
            w = pd.concat(plist, axis=1)
            return w.loc[:, ~w.columns.duplicated()].sort_index()

        self._last_extras = {k: _wide(v) for k, v in extras.items() if v}
        return _wide(parts)

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

    # ── W1: 20-session sector participation (additive; does not touch the
    # existing 50/200 acquisition/output above) ────────────────────────────
    def licensed_daily_window(self, ticker: str, start: date, end: date) -> pd.Series:
        """One bounded ``/v2/aggs`` daily request for ``ticker`` over ``[start, end]``,
        ``adjusted=true``, against the licensed vendor (research/licenses/
        MASSIVE_ENTITLEMENT_RECORD.md) — see the ``W1_LICENSED_BASIS`` note above for
        why this reads the vendor directly rather than an existing adjusted cache.

        No raw response is persisted here; the caller (``compute_sector_participation_20``)
        only keeps the derived participation product. Key travels as an
        ``Authorization: Bearer`` header, never a query param — the documented reason
        (``scripts/massive_entitlement_probe.py``) is that query strings leak into
        exception/retry/proxy logs, not merely a style preference.

        Raises :class:`LicensedSourceError` rather than returning a partial series —
        callers must re-fetch the whole window, never splice onto an older cache.
        """
        if end < start:
            raise LicensedSourceError(f"{ticker}: window {start}..{end} runs backwards")
        cfg = dict(config.load().get("polygon") or {})
        base = str(cfg.get("base_url") or "https://api.polygon.io").rstrip("/")
        key = (config.secret(str(cfg.get("api_key_env", "POLYGON_API_KEY")))
               or config.secret("MASSIVE_API_KEY"))
        if not key:
            raise LicensedSourceError(f"{ticker}: no licensed vendor key configured")
        url = f"{base}/v2/aggs/ticker/{ticker}/range/1/day/{start.isoformat()}/{end.isoformat()}"
        r = self.http_get(url, headers={"Authorization": f"Bearer {key}"},
                          params={"adjusted": "true", "sort": "asc", "limit": 50000})
        payload = r.json()

        # R3: qualify the RETURNED envelope, not merely the request we made.
        status = payload.get("status")
        if status not in ("OK", "DELAYED"):
            raise LicensedSourceError(f"{ticker}: licensed response status {status!r}, not OK")
        resp_ticker = payload.get("ticker")
        if resp_ticker and resp_ticker.upper() != ticker.upper():
            raise LicensedSourceError(
                f"{ticker}: licensed response echoed ticker {resp_ticker!r} — identity mismatch")
        if payload.get("adjusted") is False:
            raise LicensedSourceError(f"{ticker}: licensed response explicitly reports adjusted=false")
        if payload.get("next_url"):
            # We asked for a single bounded window with limit=50000 (far beyond any
            # daily-bar count for it). A next_url means the vendor truncated anyway —
            # unexpected transport truncation, not a genuinely absent observation. We
            # have no pagination/retry authority here, so refuse rather than silently
            # accept a partial window (R3).
            raise LicensedSourceError(
                f"{ticker}: licensed response was truncated (next_url present) — "
                "refusing a partial window rather than paginating")

        results = payload.get("results") or []
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        rows: dict[pd.Timestamp, float] = {}
        dup_dates: set[pd.Timestamp] = set()
        for row in results:
            ts, c = row.get("t"), row.get("c")
            if ts is None or c is None or isinstance(c, bool):
                continue  # missing or non-numeric-typed close — never coerced to 0/1
            c = float(c) if not isinstance(c, (int, float)) else c
            if not np.isfinite(c) or c <= 0:
                continue  # invalid close (R2's numeric contract applies to the source too)
            d = (pd.Timestamp(ts, unit="ms", tz="UTC")
                 .tz_convert("America/New_York").normalize().tz_localize(None))
            if d < lo or d > hi:
                continue  # out-of-window row — not part of the requested bounded range
            if d in rows:
                dup_dates.add(d)  # never silently overwrite a duplicate session (R3)
                continue
            rows[d] = c
        if dup_dates:
            raise LicensedSourceError(
                f"{ticker}: licensed response carried duplicate session(s) "
                f"{sorted(dup_dates)[:3]} — refusing rather than overwriting")
        if not rows:
            raise LicensedSourceError(f"{ticker}: empty/unusable licensed response for {start}..{end}")
        s = pd.Series(rows).sort_index()
        missing = nyse_calendar.missing_sessions(s.index, start, end)
        if missing:
            # A genuinely absent expected session (a real historical hole) must stay
            # absent here — it is NOT the same failure as transport truncation above,
            # and re-fetching cannot manufacture data that was never printed (R3).
            raise LicensedSourceError(
                f"{ticker}: licensed window {start}..{end} is missing "
                f"{len(missing)} expected session(s) (e.g. {missing[:3]}); "
                "re-fetch the whole window, never splice a partial result")
        s.attrs["price_source"] = "licensed_vendor"
        s.attrs["adjusted"] = True
        s.attrs["basis"] = W1_LICENSED_BASIS
        s.attrs["vintage"] = pd.Timestamp.utcnow().isoformat()
        return s

    def compute_sector_participation_20(self, closes: pd.DataFrame,
                                        members: pd.DataFrame) -> pd.DataFrame | None:
        """20-session sector participation, same eligibility discipline as
        :meth:`compute_sectors` (min_periods=20, wide ``<sector>|metric`` columns) but
        on a window strictly reindexed to the NYSE calendar (:mod:`lib.nyse_calendar`)
        — never a ``dropna``-then-``tail(20)`` compression, so a missing interior
        expected session excludes the cell rather than silently closing the gap
        (mission A03/A04). ``closes`` is expected to already be split-adjusted
        (:meth:`licensed_daily_window`); this method performs no acquisition.

        A member is eligible at ``t`` iff it has 20 finite, positive, non-boolean
        closes on the 20 consecutive expected sessions through and including ``t``.
        Booleans are explicitly rejected rather than coerced to 0/1 (mission A06) —
        pandas' own numeric coercion would otherwise read `True` as `1 > 0`.

        A genuinely CONSTANT 20-session window is forced to ``above=False`` regardless
        of the floating-point rolling mean, because ``mean([x]*20)`` is not always
        bit-exact to ``x`` (measured: 20 copies of 0.3 average to
        0.29999999999999993) — a naive ``price > ma20`` would misclassify a flat
        window as a crossing (mission A01; the constant-window case named in Sol's
        source ruling §5). This is an exact ``rolling max == rolling min`` check on
        the observed values themselves, not an epsilon on the comparison — it changes
        nothing for a genuine near-miss crossing.

        Returns ``None`` when no sector clears the >=5-name reference floor. A
        sector's participation *percentage* is additionally withheld (columns stay
        NaN) on any session where eligible names fall below 5 or below 90% of that
        sector's expected reference membership — counts remain visible either way
        (mission's W1 display-floor policy, §2)."""
        if "sector" not in members.columns or closes is None or closes.empty:
            return None
        start, end = closes.index.min().date(), closes.index.max().date()
        full = pd.DatetimeIndex([pd.Timestamp(d) for d in nyse_calendar.sessions_between(start, end)])
        raw = closes.reindex(full)
        # R2: the expected reference population is EVERY member symbol, not merely
        # whichever ones happen to have a price column. A symbol wholly absent from
        # `closes` (a data gap, not a sector-membership fact) must still count toward
        # expected_20 and simply never become eligible — reindexing the columns to the
        # full member universe makes that the natural, un-special-cased outcome below,
        # instead of silently shrinking the denominator (the exact bug: a missing
        # symbol could turn real 50% coverage into apparent 100%).
        universe = pd.Index(members["symbol"].dropna().unique()).union(raw.columns)
        raw = raw.reindex(columns=universe)
        clean = pd.DataFrame(index=raw.index)
        for c in raw.columns:
            col = raw[c]
            if pd.api.types.is_bool_dtype(col):
                clean[c] = np.nan          # A06: an entirely-boolean column is invalid, never 0/1
                continue
            if col.dtype == object:
                # an ISOLATED Python bool inside an otherwise-numeric object column is
                # the same defect one level down: is_bool_dtype only ever catches a
                # column whose dtype is bool, and pd.to_numeric happily reads a bare
                # True/False as 1/0 if given the chance (R2).
                col = col.map(lambda x: np.nan if isinstance(x, bool) else x)
            v = pd.to_numeric(col, errors="coerce")
            clean[c] = v.where(np.isfinite(v) & (v > 0))
        ma20 = clean.rolling(20, min_periods=20).mean()
        roll_max = clean.rolling(20, min_periods=20).max()
        roll_min = clean.rolling(20, min_periods=20).min()
        is_constant = roll_max == roll_min
        above = (clean > ma20) & ~is_constant
        eligible = ma20.notna()

        sec_map = members.set_index("symbol")["sector"].dropna()
        # R2: unresolved or conflicting membership (the same symbol claimed by more than
        # one sector, or a duplicated row) must not be guessed into a sector or double-
        # counted — drop it from every sector's roster rather than pick one arbitrarily.
        dup_symbols = sec_map.index[sec_map.index.duplicated(keep=False)]
        sec_map = sec_map[~sec_map.index.isin(dup_symbols)]

        cols = {}
        for sector, syms in sec_map.groupby(sec_map).groups.items():
            tick = list(syms)          # the FULL reference roster for this sector (R2)
            expected_n = len(tick)
            if expected_n == 0:
                continue
            elig_n = eligible[tick].sum(axis=1)
            above_n = above[tick].sum(axis=1)
            pct = 100 * above_n / elig_n.where(elig_n > 0)
            floor_ok = (elig_n >= 5) & (elig_n >= 0.9 * expected_n)
            cols[f"{sector}|above_20"] = above_n.astype(float)
            cols[f"{sector}|eligible_20"] = elig_n.astype(float)
            cols[f"{sector}|expected_20"] = pd.Series(float(expected_n), index=clean.index)
            cols[f"{sector}|pct_above_20"] = pct.where(floor_ok)
        if not cols:
            return None
        out = pd.DataFrame(cols)
        keep = [c for c in out.columns if c.endswith("|eligible_20")]
        return out.dropna(subset=keep, how="all")

    def fetch_sector_participation_20(self, members: pd.DataFrame, *,
                                      end: date | None = None, window_days: int = 45,
                                      fetch_one=None) -> tuple[pd.DataFrame | None, dict[str, str]]:
        """R1: the connected SP500-only owning invocation — one
        :meth:`licensed_daily_window` call per reference member, assembled into a wide
        closes frame and reduced through :meth:`compute_sector_participation_20`.

        ``fetch_one`` defaults to ``self.licensed_daily_window`` and exists so tests can
        inject fake per-ticker responses with zero network access — this is the
        "connected path, tested with injected responses" R1 requires. This method is
        deliberately NOT called from :meth:`fetch`: a live 500+-ticker acquisition is a
        separate, explicitly gated qualification step (Sol's source ruling), not
        something merely writing and testing this connector authorizes.

        Returns ``(participation_or_None, failures)`` — ``failures`` maps ticker ->
        error string for any member whose fetch didn't qualify (R4: a partial roster is
        disclosed, not hidden; a name absent from the assembled frame is simply never
        eligible, per the R2 fix to :meth:`compute_sector_participation_20`)."""
        fetch_one = fetch_one or self.licensed_daily_window
        end = end or nyse_calendar.expected_last_session()
        start = end - pd.Timedelta(days=window_days)
        start = nyse_calendar.last_session_on_or_before(start)
        cols: dict[str, pd.Series] = {}
        failures: dict[str, str] = {}
        for t in members["symbol"].dropna().unique():
            try:
                cols[str(t)] = fetch_one(t, start, end)
            except LicensedSourceError as e:
                failures[str(t)] = str(e)
        if not cols:
            return None, failures
        closes = pd.DataFrame(cols)
        result = self.compute_sector_participation_20(closes, members)
        return result, failures

    def publish_sector_participation_20(self, result: pd.DataFrame | None,
                                        failures: dict[str, str], members: pd.DataFrame,
                                        *, path=None) -> None:
        """R1/R4: bounded derived publication. Writes the derived participation
        product WHOLESALE — never a ``combine_first`` merge onto a prior file, so a
        cell that is genuinely unavailable today can never be silently backfilled by a
        stale value left over from an earlier, differently-shaped publish (R4). A
        companion ``_meta.json`` carries the metadata a bare parquet cannot round-trip
        through ``DataFrame.attrs`` (pandas does not serialize ``attrs``): method,
        basis, reference-roster identity, per-fetch failures, and the SEPARATE
        observation/expected-session clocks R4 requires — never just the returned
        frame's own max date."""
        import hashlib
        import json
        p = path or (config.data_dir() / "breadth" / "sector_participation_20.parquet")
        p.parent.mkdir(parents=True, exist_ok=True)
        expected_last = nyse_calendar.expected_last_session()
        roster_sha = hashlib.sha256(
            ",".join(sorted(members["symbol"].dropna().astype(str))).encode()).hexdigest()
        meta = {
            "method": "sector_participation_20",
            "basis": W1_LICENSED_BASIS,
            "computed_at": pd.Timestamp.utcnow().isoformat(),
            "expected_last_session": expected_last.isoformat(),
            "observed_max_session": (result.index.max().date().isoformat()
                                     if result is not None and not result.empty else None),
            "reference_roster_sha256": roster_sha,
            "reference_roster_count": int(members["symbol"].dropna().nunique()),
            "fetch_failure_count": len(failures),
            "fetch_failures_sample": dict(list(failures.items())[:10]),
        }
        if result is None or result.empty:
            (p.parent / "sector_participation_20_meta.json").write_text(
                json.dumps({**meta, "available": False}, indent=2))
            if p.exists():
                p.unlink()  # no result this run — never leave a stale parquet claiming otherwise
            return
        result.to_parquet(p)  # wholesale overwrite, no merge (R4)
        (p.parent / "sector_participation_20_meta.json").write_text(
            json.dumps({**meta, "available": True}, indent=2))

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
