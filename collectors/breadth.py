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

import copy
import hashlib
import io
import json
import logging
import re
import time
from collections import deque
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from collectors.base import Adapter, is_connection_error, safe_exc_text
from lib import config, delisted_symbols, nyse_calendar
from lib import sector_participation as w1_contract

log = logging.getLogger(__name__)


class LicensedSourceError(RuntimeError):
    """A licensed response could not become W1 evidence.

    ``member_state`` distinguishes an unavailable/refused request (``U``) from an
    identity/basis/shape qualification failure (``I``).  ``fatal`` is reserved for
    account-wide authentication/entitlement refusal: the bounded orchestrator may
    finish already-running calls but must stop scheduling new W1 requests.
    """

    def __init__(self, message: str, *, member_state: str = "U", fatal: bool = False):
        super().__init__(message)
        self.member_state = member_state if member_state in {"I", "U"} else "U"
        self.fatal = bool(fatal)


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
W1_LICENSED_BASIS = w1_contract.PRICE_BASIS
_W1_PACKAGE_SCHEMA = w1_contract.PACKAGE_SCHEMA
_W1_MEMBER_STATES = w1_contract.MEMBER_STATES


def _w1_http_controls(provider_cfg: dict) -> tuple[float, int, float]:
    """Derive bounded W1 controls from the existing licensed-provider owner.

    The provider's general timeout/retry settings remain the source of truth when
    tighter than W1's bounded ceiling. Optional W1 keys may tighten them further,
    but cannot turn a 503-name descriptive sidecar into an unbounded retry lane.
    """
    general_timeout = max(1.0, float(provider_cfg.get("request_timeout", 20.0)))
    general_retries = max(1, int(provider_cfg.get("retries", 2)))
    timeout = max(1.0, min(20.0, float(
        provider_cfg.get("w1_request_timeout_seconds", min(20.0, general_timeout)))))
    retries = max(1, min(2, int(
        provider_cfg.get("w1_request_retries", min(2, general_retries)))))
    backoff = max(0.0, min(1.0, float(
        provider_cfg.get("w1_request_backoff_seconds", 1.0))))
    return timeout, retries, backoff


def _w1_decimal_window_stats(
        series: pd.Series, *, window: int = 20) -> tuple[pd.Series, pd.Series]:
    """Return exact-decimal strict-above decisions and finite window means.

    Licensed daily closes arrive as JSON decimal numbers but are held in pandas as
    binary floats. Binary rolling arithmetic can both round an economically equal
    close below its mean and overflow while every accepted close remains finite.
    Reconstruct the shortest round-tripping decimal for each accepted close and own
    the entire W1 20-session window arithmetic here.

    The strict A/B decision avoids division entirely: current * window > sum.
    The companion mean is converted to float only after the exact Decimal sum is
    divided by the bounded window, which guarantees a finite mean for a window of
    finite positive closes. Missing/invalid closes stay ineligible and retain NaN
    means; state typing remains with the existing W1 window logic.
    """
    if window < 1:
        raise ValueError("window must be positive")

    above = pd.Series(False, index=series.index, dtype=bool)
    means = pd.Series(np.nan, index=series.index, dtype=float)
    rolling: deque[Decimal | None] = deque()
    rolling_sum = Decimal(0)
    valid_count = 0
    window_decimal = Decimal(window)

    # Accepted values are positive finite IEEE-754 doubles. Their shortest
    # round-tripping decimal strings can span roughly 5e-324..1.8e308. A
    # rolling sum must retain the tiny terms even while a huge term is present,
    # otherwise subtracting the huge term later fabricates a zero remainder.
    # 800 significant digits safely covers the full exponent span plus all
    # coefficient digits for this bounded 20-value sum, without mutating the
    # process-global Decimal context.
    with localcontext() as context:
        context.prec = 800
        for position, value in enumerate(series):
            decimal_value: Decimal | None = None
            if pd.notna(value):
                decimal_value = Decimal(str(float(value)))
                rolling_sum += decimal_value
                valid_count += 1
            rolling.append(decimal_value)

            if len(rolling) > window:
                expired = rolling.popleft()
                if expired is not None:
                    rolling_sum -= expired
                    valid_count -= 1

            if (len(rolling) == window and valid_count == window
                    and decimal_value is not None):
                above.iat[position] = decimal_value * window_decimal > rolling_sum
                exact_mean = rolling_sum / window_decimal
                mean_float = float(exact_mean)
                if not np.isfinite(mean_float):
                    raise ArithmeticError("finite W1 window produced a non-finite mean")
                means.iat[position] = mean_float

    return above, means

def _w1_request_ceiling_seconds(provider_cfg: dict) -> float:
    """Worst-case wall time of one bounded request under Adapter.http_get."""
    timeout, retries, backoff = _w1_http_controls(provider_cfg)
    sleeps = backoff * ((2 ** (retries - 1)) - 1) if retries > 1 else 0.0
    return timeout * retries + sleeps


_w1_canonicalize = w1_contract.canonicalize
_w1_observation_id = w1_contract.observation_id
_w1_generation_material = w1_contract.generation_material
_w1_generation_id = w1_contract.generation_id
_w1_json_bytes = w1_contract.json_bytes
_validate_w1_package = w1_contract.validate_package

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

        # W1 is a fail-soft side publication owned only by the exact US S&P adapter.
        # It never enters ``out`` and therefore cannot alter or suppress the protected
        # 50/200 breadth frames. Full-history runs retain their historical behavior and
        # do not spend a separate live licensed-request budget.
        if self._owns_sector_participation_20() and not full_history:
            try:
                w1_result, w1_failures = self.fetch_sector_participation_20(members)
                if not self.publish_sector_participation_20(
                        w1_result, w1_failures, members,
                        path=self.cache_path.parent / "sector_participation_20.json"):
                    log.warning(
                        "sector participation W1 did not replace its prior generation")
            except Exception as e:  # noqa: BLE001 — old breadth remains publishable
                log.warning(
                    "sector participation W1 failed (%s) — existing 50/200 breadth "
                    "outputs remain unchanged", e)
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
    def _owns_sector_participation_20(self) -> bool:
        """Only the exact US S&P reference owner may acquire or publish W1.

        Several regional/smaller-cap adapters inherit this class.  Exact type
        identity is deliberate: inherited methods are available for reuse in
        hermetic tests, but no sibling runtime may spend the licensed request
        budget or mutate the canonical US package.
        """
        return type(self) is BreadthAdapter

    def licensed_daily_window(self, ticker: str, start: date, end: date) -> pd.Series:
        """Return one qualified, split-adjusted daily series for ``[start, end]``.

        Transport completeness and historical observation completeness are different
        facts.  A malformed/truncated envelope is refused; a successful bounded
        response that simply has no row for an expected session remains a sparse
        series.  The latter carries ``missing_sessions`` so downstream 20-session
        windows can become ``M`` without discarding unaffected history.  Rows present
        for an expected session but carrying an invalid close are kept separately in
        ``invalid_sessions`` so the package can distinguish ``I`` from ``M``.

        No raw response or credential is persisted.  The API key travels only in the
        Authorization header, and the returned attrs contain bounded request/source
        identity sufficient to explain the derived generation.
        """
        from collections.abc import Mapping

        if end < start:
            raise LicensedSourceError(f"{ticker}: window {start}..{end} runs backwards")
        cfg = dict(config.load().get("polygon") or {})
        base = str(cfg.get("base_url") or "https://api.polygon.io").rstrip("/")
        key = (config.secret(str(cfg.get("api_key_env", "POLYGON_API_KEY")))
               or config.secret("MASSIVE_API_KEY"))
        if not key:
            raise LicensedSourceError(f"{ticker}: no licensed vendor key configured", fatal=True)
        url = f"{base}/v2/aggs/ticker/{ticker}/range/1/day/{start.isoformat()}/{end.isoformat()}"
        timeout, retries, backoff = _w1_http_controls(cfg)
        try:
            response = self.http_get(
                url,
                retries=retries,
                backoff_base=backoff,
                timeout=timeout,
                headers={"Authorization": f"Bearer {key}"},
                params={"adjusted": "true", "sort": "asc", "limit": 50000},
            )
        except Exception as exc:  # noqa: BLE001 — translated to typed W1 source state
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            fatal = bool(
                is_connection_error(exc)
                or status_code in {401, 403, 407, 429}
                or (isinstance(status_code, int) and status_code >= 500)
            )
            raise LicensedSourceError(
                f"{ticker}: licensed source transport failed ({safe_exc_text(exc)})",
                fatal=fatal,
            ) from exc
        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — malformed response cannot become evidence
            raise LicensedSourceError(
                f"{ticker}: licensed response body was not valid JSON/object data",
                member_state="I",
            ) from exc

        if not isinstance(payload, Mapping):
            raise LicensedSourceError(
                f"{ticker}: licensed response body must be a mapping/object", member_state="I")
        status = payload.get("status")
        if status not in ("OK", "DELAYED"):
            failure_text = " ".join(
                str(payload.get(key) or "") for key in ("status", "error", "message"))
            lowered = failure_text.casefold().replace("_", " ")
            fatal_markers = (
                "not authorized", "unauthorized", "forbidden", "api key",
                "invalid key", "entitlement", "subscription", "permission",
                "plan", "rate limit", "too many requests", "service unavailable",
                "internal server", "temporarily unavailable",
            )
            raise LicensedSourceError(
                f"{ticker}: licensed response status {status!r}, not successful",
                fatal=any(marker in lowered for marker in fatal_markers),
            )
        response_ticker = payload.get("ticker")
        if not isinstance(response_ticker, str):
            raise LicensedSourceError(
                f"{ticker}: licensed response omitted the requested ticker identity", member_state="I")
        # Case is identity.  The only accepted normalization is the vendor's class-
        # share separator (BRK-B <-> BRK.B); broad uppercasing would turn a malformed
        # response into apparently matching evidence.
        if response_ticker != ticker and response_ticker.replace(".", "-") != ticker.replace(".", "-"):
            raise LicensedSourceError(
                f"{ticker}: licensed response echoed ticker {response_ticker!r} — identity mismatch",
                member_state="I")
        adjusted = payload.get("adjusted")
        if adjusted is False:
            raise LicensedSourceError(
                f"{ticker}: licensed response explicitly reports adjusted=false", member_state="I")
        if adjusted is not True:
            raise LicensedSourceError(
                f"{ticker}: licensed response did not explicitly report adjusted=true",
                member_state="I")
        if payload.get("next_url"):
            raise LicensedSourceError(
                f"{ticker}: licensed response was truncated (next_url present) — "
                "refusing a partial window rather than paginating")

        results = payload.get("results")
        if not isinstance(results, list):
            raise LicensedSourceError(
                f"{ticker}: licensed response results must be a list", member_state="I")
        request_id = payload.get("request_id")
        if request_id is not None and not isinstance(request_id, str):
            raise LicensedSourceError(
                f"{ticker}: licensed response request_id is malformed", member_state="I")
        declared_count = payload.get("resultsCount")
        if (isinstance(declared_count, bool) or not isinstance(declared_count, int)
                or declared_count != len(results)):
            raise LicensedSourceError(
                f"{ticker}: resultsCount {declared_count!r} does not match "
                f"the {len(results)} returned result row(s)", member_state="I")

        expected = pd.DatetimeIndex(
            pd.Timestamp(d) for d in nyse_calendar.sessions_between(start, end))
        expected_set = set(expected)
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        rows: dict[pd.Timestamp, float] = {}
        seen_sessions: set[pd.Timestamp] = set()
        invalid_sessions: set[pd.Timestamp] = set()
        duplicate_sessions: set[pd.Timestamp] = set()

        for row in results:
            if not isinstance(row, Mapping):
                raise LicensedSourceError(
                    f"{ticker}: licensed result row must be a mapping/object", member_state="I")
            ts = row.get("t")
            if isinstance(ts, bool) or not isinstance(ts, (int, float, np.integer, np.floating)):
                raise LicensedSourceError(
                    f"{ticker}: licensed result row carried an invalid timestamp", member_state="I")
            try:
                stamp_et = pd.Timestamp(ts, unit="ms", tz="UTC").tz_convert("America/New_York")
                midnight_et = stamp_et.normalize()
                session = midnight_et.tz_localize(None)
            except (TypeError, ValueError, OverflowError) as exc:
                raise LicensedSourceError(
                    f"{ticker}: licensed result timestamp could not be qualified", member_state="I") from exc

            # An unexpected row is never accepted into the evidence set. Vendor APIs
            # can return a boundary row outside the requested interval; ignoring it is
            # safe because it contributes to neither the requested denominator nor a
            # missing/invalid classification. Shape qualification is intentionally
            # after this bound check so an irrelevant boundary row cannot poison the
            # requested evidence set.
            if session < lo or session > hi:
                continue
            if stamp_et != midnight_et:
                raise LicensedSourceError(
                    f"{ticker}: licensed daily aggregate timestamp must be midnight US/Eastern",
                    member_state="I")
            if session not in expected_set:
                raise LicensedSourceError(
                    f"{ticker}: licensed response carried an in-range non-session row "
                    f"for {session.date().isoformat()}", member_state="I")
            if session in seen_sessions:
                duplicate_sessions.add(session)
                continue
            seen_sessions.add(session)

            close = row.get("c")
            if (isinstance(close, bool)
                    or not isinstance(close, (int, float, np.integer, np.floating))
                    or not np.isfinite(close) or float(close) <= 0):
                invalid_sessions.add(session)
                continue
            rows[session] = float(close)

        if duplicate_sessions:
            raise LicensedSourceError(
                f"{ticker}: licensed response carried duplicate session(s) "
                f"{sorted(duplicate_sessions)[:3]} — refusing rather than overwriting",
                member_state="I")

        series = pd.Series(rows, dtype=float).sort_index()
        missing_sessions = sorted(expected_set - seen_sessions)
        acquired_at = pd.Timestamp.now(tz="UTC").isoformat()
        series.attrs.update({
            "price_source": "licensed_vendor",
            "adjusted": True,
            "basis": W1_LICENSED_BASIS,
            "vintage": acquired_at,
            "acquired_at": acquired_at,
            "requested_ticker": ticker,
            "response_ticker": response_ticker,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "response_status": status,
            "response_count": len(results),
            "request_id": request_id,
            "missing_sessions": [d.date().isoformat() for d in missing_sessions],
            "invalid_sessions": [d.date().isoformat() for d in sorted(invalid_sessions)],
        })
        return series

    def compute_sector_participation_20(self, closes: pd.DataFrame,
                                        members: pd.DataFrame) -> pd.DataFrame | None:
        """Compute typed 20-session participation on the expected NYSE calendar.

        The returned frame retains the compact sector columns used by the existing
        collector path and carries the exact same-generation per-member evidence in
        ``DataFrame.attrs``.  Every member/session is typed ``A/B/H/M/I/U``; the
        browser never reconstructs a moving average from prices.
        """
        from urllib.parse import quote

        if "sector" not in members.columns or "symbol" not in members.columns:
            return None
        if closes is None or closes.empty:
            return None

        roster_columns = ["symbol", "sector"] + (["name"] if "name" in members.columns else [])
        roster = members.loc[:, roster_columns].dropna(subset=["symbol", "sector"]).copy()
        if roster.empty:
            return None
        roster["symbol"] = roster["symbol"].astype(str)
        roster["sector"] = roster["sector"].astype(str)
        if "name" not in roster.columns:
            roster["name"] = roster["symbol"]
        else:
            roster["name"] = [
                " ".join(str(value).split()) if pd.notna(value) and str(value).strip() else symbol
                for value, symbol in zip(roster["name"], roster["symbol"])
            ]
        duplicate = roster["symbol"].duplicated(keep=False)
        if duplicate.any():
            names = sorted(roster.loc[duplicate, "symbol"].unique())
            raise ValueError(
                "duplicate roster membership is invalid until the identity owner "
                f"resolves it: {names[:5]}")
        sec_map = roster.set_index("symbol")["sector"]
        name_map = roster.set_index("symbol")["name"]

        source_evidence = dict(closes.attrs.get("member_evidence") or {})
        start, end = closes.index.min().date(), closes.index.max().date()
        full = pd.DatetimeIndex(
            pd.Timestamp(d) for d in nyse_calendar.sessions_between(start, end))
        raw = closes.reindex(full)
        universe = pd.Index(sec_map.index).union(raw.columns.astype(str))
        raw.columns = raw.columns.astype(str)
        raw = raw.reindex(columns=universe)

        clean = pd.DataFrame(index=raw.index, columns=raw.columns, dtype=float)
        invalid = pd.DataFrame(False, index=raw.index, columns=raw.columns, dtype=bool)
        for symbol in raw.columns:
            original = raw[symbol]
            bool_mask = original.map(
                lambda value: isinstance(value, (bool, np.bool_)) if pd.notna(value) else False)
            numeric = pd.to_numeric(original.where(~bool_mask), errors="coerce")
            valid = numeric.notna() & np.isfinite(numeric) & (numeric > 0)
            clean[symbol] = numeric.where(valid)
            invalid[symbol] = original.notna() & (~valid | bool_mask)

            evidence = dict(source_evidence.get(str(symbol)) or {})
            for day in evidence.get("invalid_sessions") or []:
                stamp = pd.Timestamp(day)
                if stamp in invalid.index:
                    invalid.at[stamp, symbol] = True
                    clean.at[stamp, symbol] = np.nan
            accepted_pairs = [
                [stamp.date().isoformat(), float(value)]
                for stamp, value in clean[symbol].items() if pd.notna(value)
            ]
            evidence["accepted_values_id"] = "sha256:" + hashlib.sha256(
                json.dumps(accepted_pairs, separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
            evidence.setdefault("basis", W1_LICENSED_BASIS)
            evidence.setdefault("adjusted", True)
            source_evidence[str(symbol)] = evidence

        # W1 owns its complete 20-session arithmetic in one bounded Decimal
        # window. This avoids both strict-boundary rounding and binary rolling-sum
        # overflow while leaving the protected 50/200 breadth calculations above
        # untouched.
        window_stats = {
            symbol: _w1_decimal_window_stats(clean[symbol], window=20)
            for symbol in clean.columns
        }
        above = pd.DataFrame(
            {symbol: stats[0] for symbol, stats in window_stats.items()},
            index=clean.index,
        )
        ma20 = pd.DataFrame(
            {symbol: stats[1] for symbol, stats in window_stats.items()},
            index=clean.index,
        )
        eligible = ma20.notna()

        cols: dict[str, pd.Series] = {}
        for sector, symbols in sec_map.groupby(sec_map).groups.items():
            tickers = list(symbols)
            expected_n = len(tickers)
            elig_n = eligible[tickers].sum(axis=1)
            above_n = above[tickers].sum(axis=1)
            pct = 100 * above_n / elig_n.where(elig_n > 0)
            floor_ok = (elig_n >= 5) & (elig_n >= 0.9 * expected_n)
            cols[f"{sector}|above_20"] = above_n.astype(float)
            cols[f"{sector}|eligible_20"] = elig_n.astype(float)
            cols[f"{sector}|expected_20"] = pd.Series(float(expected_n), index=clean.index)
            cols[f"{sector}|pct_above_20"] = pct.where(floor_ok)
        if not cols:
            return None
        out = pd.DataFrame(cols, index=clean.index)

        sessions = [stamp.date().isoformat() for stamp in clean.index]
        member_payload: dict[str, dict] = {}
        for symbol, sector in sec_map.items():
            evidence = dict(source_evidence.get(symbol) or {})
            forced_state = evidence.get("state")
            if evidence.get("unavailable"):
                forced_state = forced_state or "U"
            if forced_state not in (None, "I", "U"):
                forced_state = "U"

            valid_mask = clean[symbol].notna()
            observed_mask = valid_mask | invalid[symbol]
            observed_positions = np.flatnonzero(observed_mask.to_numpy())
            first_observed = int(observed_positions[0]) if len(observed_positions) else None
            states: list[str] = []
            distances: list[float | None] = []
            for position in range(len(clean.index)):
                if forced_state in ("I", "U"):
                    state = forced_state
                elif position < 19:
                    state = "H"
                else:
                    window_start = position - 19
                    invalid_window = invalid[symbol].iloc[window_start:position + 1]
                    valid_window = valid_mask.iloc[window_start:position + 1]
                    if bool(invalid_window.any()):
                        state = "I"
                    elif bool(valid_window.all()):
                        state = "A" if bool(above[symbol].iloc[position]) else "B"
                    else:
                        missing_positions = np.flatnonzero((~valid_window).to_numpy()) + window_start
                        leading_shortfall = (
                            first_observed is not None
                            and len(missing_positions) > 0
                            and bool((missing_positions < first_observed).all())
                        )
                        state = "H" if leading_shortfall else "M"
                states.append(state)
                if state in ("A", "B"):
                    price = float(clean[symbol].iloc[position])
                    average = float(ma20[symbol].iloc[position])
                    distances.append(round((price / average - 1.0) * 10000.0, 4))
                else:
                    distances.append(None)

            member_payload[symbol] = {
                "name": str(name_map[symbol]),
                "sector": sector,
                "states": states,
                "distance_bps": distances,
                "href": "stock.html#" + quote(symbol, safe=""),
            }

        acquired = sorted(
            str((source_evidence.get(symbol) or {}).get("acquired_at"))
            for symbol in sec_map.index
            if (source_evidence.get(symbol) or {}).get("acquired_at"))
        observed_rows = clean.notna().any(axis=1)
        observed_max = (
            clean.index[observed_rows].max().date().isoformat()
            if bool(observed_rows.any()) else None)
        out.attrs.update({
            "sessions": sessions,
            "members": member_payload,
            "member_evidence": source_evidence,
            "requested_start": sessions[0] if sessions else None,
            "requested_end": sessions[-1] if sessions else None,
            "observed_max_session": observed_max,
            "acquired_at": acquired[-1] if acquired else None,
            "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
        })
        return out

    def fetch_sector_participation_20(
            self, members: pd.DataFrame, *, end: date | None = None,
            window_days: int | None = None, fetch_one=None,
            max_workers: int | None = None,
            operation_budget_seconds: float | None = None,
            display_sessions: int = 252,
    ) -> tuple[pd.DataFrame | None, dict[str, str]]:
        """Acquire the full reference roster under one bounded operation budget.

        Work is scheduled incrementally, never all 503 names at once.  An account-wide
        auth/entitlement refusal stops new submissions; a per-member refusal remains
        ``U`` for that member.  The returned frame always covers the complete roster and
        expected-session range, even when every request fails, so an explicit
        unavailable generation can be published without shrinking denominators.
        """
        from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

        uses_default_reader = fetch_one is None
        fetch_one = fetch_one or self.licensed_daily_window
        end = end or nyse_calendar.expected_last_session()
        if window_days is None:
            if display_sessions < 1:
                raise ValueError("display_sessions must be positive")
            start = nyse_calendar.session_n_back(end, display_sessions + 19 - 1)
            if start is None:
                raise ValueError("NYSE calendar could not resolve the W1 warmup range")
        else:
            start = nyse_calendar.last_session_on_or_before(
                end - pd.Timedelta(days=window_days))
        symbols = [str(symbol) for symbol in members["symbol"].dropna().unique()]
        cfg = dict(config.load().get("polygon") or {})
        configured_workers = (
            max_workers if max_workers is not None
            else cfg.get("w1_max_workers", cfg.get("workers", 5)))
        workers = max(1, min(8, int(configured_workers)))
        budget = float(operation_budget_seconds if operation_budget_seconds is not None
                       else cfg.get("w1_operation_budget_seconds", 180.0))
        request_reserve = _w1_request_ceiling_seconds(cfg) if uses_default_reader else 0.0
        sessions = pd.DatetimeIndex(
            pd.Timestamp(day) for day in nyse_calendar.sessions_between(start, end))
        failures: dict[str, str] = {}
        evidence: dict[str, dict] = {}
        columns: dict[str, pd.Series] = {}

        def mark_failure(symbol: str, message: str, state: str = "U") -> None:
            failures[symbol] = message
            evidence[symbol] = {
                "state": state if state in {"I", "U"} else "U",
                "unavailable": state != "I",
                "reason": message,
            }

        if budget <= 0 or not symbols:
            for symbol in symbols:
                mark_failure(symbol, "W1 acquisition operation budget expired before scheduling")
        else:
            deadline = time.monotonic() + budget
            executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="w1-participation")
            pending: dict = {}
            cursor = 0
            fatal_message: str | None = None
            budget_expired = False

            def submit_until_full() -> None:
                nonlocal cursor
                while (fatal_message is None and cursor < len(symbols)
                       and len(pending) < workers
                       and time.monotonic() + request_reserve <= deadline):
                    symbol = symbols[cursor]
                    cursor += 1
                    pending[executor.submit(fetch_one, symbol, start, end)] = symbol

            submit_until_full()
            try:
                while pending and fatal_message is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        budget_expired = True
                        break
                    done, _ = wait(
                        tuple(pending), timeout=remaining, return_when=FIRST_COMPLETED)
                    if not done:
                        budget_expired = True
                        break
                    for future in done:
                        symbol = pending.pop(future)
                        try:
                            series = future.result()
                            if not isinstance(series, pd.Series):
                                raise LicensedSourceError(
                                    f"{symbol}: source reader returned a non-Series result",
                                    member_state="I")
                            columns[symbol] = series
                            attrs = dict(series.attrs)
                            evidence[symbol] = {
                                "missing_sessions": list(attrs.get("missing_sessions") or []),
                                "invalid_sessions": list(attrs.get("invalid_sessions") or []),
                                "acquired_at": attrs.get("acquired_at") or attrs.get("vintage"),
                                "requested_ticker": attrs.get("requested_ticker"),
                                "response_ticker": attrs.get("response_ticker"),
                                "requested_start": attrs.get("requested_start"),
                                "requested_end": attrs.get("requested_end"),
                                "response_status": attrs.get("response_status"),
                                "response_count": attrs.get("response_count"),
                                "request_id": attrs.get("request_id"),
                                "basis": attrs.get("basis"),
                                "adjusted": attrs.get("adjusted"),
                            }
                        except LicensedSourceError as exc:
                            mark_failure(symbol, str(exc), exc.member_state)
                            if exc.fatal:
                                fatal_message = str(exc)
                        except Exception as exc:  # noqa: BLE001 — member is unavailable, not dropped
                            mark_failure(symbol, f"{symbol}: {safe_exc_text(exc)}", "U")
                    if fatal_message is None:
                        submit_until_full()
                if fatal_message is None and cursor < len(symbols):
                    # No new request may start unless its bounded worst case fits in
                    # the remaining whole-operation budget. Unscheduled members are U.
                    budget_expired = True
            finally:
                if fatal_message is not None or budget_expired:
                    reason = (f"W1 acquisition stopped after fatal source refusal: {fatal_message}"
                              if fatal_message is not None
                              else "W1 acquisition operation budget expired")
                    for future in list(pending):
                        future.cancel()
                    # An operation-level refusal or deadline means this response set
                    # is incomplete, regardless of how many names finished first.
                    # Discard every partial success so 90%+ late failures cannot mint
                    # a replacement generation from a truncated acquisition.
                    columns.clear()
                    for symbol in symbols:
                        mark_failure(symbol, reason, "U")
                    executor.shutdown(wait=False, cancel_futures=True)
                else:
                    executor.shutdown(wait=True)

        frame = pd.DataFrame(index=sessions, columns=symbols, dtype=float)
        for symbol, series in columns.items():
            if series.empty:
                continue
            normalized = series.copy()
            normalized.index = pd.DatetimeIndex(pd.to_datetime(normalized.index)).tz_localize(None).normalize()
            common = frame.index.intersection(normalized.index)
            frame.loc[common, symbol] = normalized.reindex(common).to_numpy()
        frame.attrs["member_evidence"] = evidence
        result = self.compute_sector_participation_20(frame, members)
        if result is not None:
            result.attrs["latest_expected_session"] = end.isoformat()
            result.attrs["display_sessions"] = min(int(display_sessions), len(sessions))
        return result, failures

    def build_sector_participation_20_package(
            self, result: pd.DataFrame, failures: dict[str, str],
            members: pd.DataFrame) -> dict:
        """Build the one public/private W1 generation from typed member evidence."""
        if result is None or result.empty:
            raise ValueError("no W1 result is available for publication")
        source_sessions = list(result.attrs.get("sessions") or [])
        member_payload = copy.deepcopy(result.attrs.get("members") or {})
        if not source_sessions or not member_payload:
            raise ValueError("W1 result is missing same-generation member evidence")
        display_sessions = int(result.attrs.get("display_sessions") or len(source_sessions))
        if display_sessions < 1 or display_sessions > len(source_sessions):
            raise ValueError("W1 display session count is outside the qualified source range")
        public_offset = len(source_sessions) - display_sessions
        sessions = source_sessions[public_offset:]
        for symbol, evidence in member_payload.items():
            states = evidence.get("states")
            distances = evidence.get("distance_bps")
            if (not isinstance(states, list) or len(states) != len(source_sessions)
                    or not isinstance(distances, list) or len(distances) != len(source_sessions)):
                raise ValueError(f"W1 member {symbol} is not aligned to the qualified source range")
            evidence["states"] = "".join(states[public_offset:])
            evidence["distance_bps"] = distances[public_offset:]

        roster_columns = ["symbol", "sector"] + (["name"] if "name" in members.columns else [])
        roster = members.loc[:, roster_columns].dropna(subset=["symbol", "sector"]).copy()
        roster["symbol"] = roster["symbol"].astype(str)
        roster["sector"] = roster["sector"].astype(str)
        if "name" not in roster.columns:
            roster["name"] = roster["symbol"]
        else:
            roster["name"] = [
                " ".join(str(value).split()) if pd.notna(value) and str(value).strip() else symbol
                for value, symbol in zip(roster["name"], roster["symbol"])
            ]
        if roster["symbol"].duplicated(keep=False).any():
            raise ValueError("duplicate roster membership blocks W1 publication")
        expected_members = set(roster["symbol"])
        if set(member_payload) != expected_members:
            raise ValueError("W1 member evidence does not cover the full reference roster")
        roster_by_symbol = roster.set_index("symbol")
        for symbol in sorted(expected_members):
            member_payload[symbol]["name"] = str(roster_by_symbol.at[symbol, "name"])
            if member_payload[symbol].get("sector") != roster_by_symbol.at[symbol, "sector"]:
                raise ValueError(f"W1 member {symbol} sector disagrees with the reference roster")
        roster_pairs = sorted(
            (row.symbol, row.name, row.sector) for row in roster.itertuples(index=False))
        roster_bytes = json.dumps(roster_pairs, separators=(",", ":"), ensure_ascii=False).encode()
        roster_id = "sha256:" + hashlib.sha256(roster_bytes).hexdigest()

        sectors: dict[str, dict] = {}
        for sector in sorted(roster["sector"].unique()):
            names = sorted(roster.loc[roster["sector"] == sector, "symbol"])
            above: list[int] = []
            eligible: list[int] = []
            expected: list[int] = []
            pct: list[float | None] = []
            excluded = {state: [] for state in ("H", "M", "I", "U")}
            for position in range(len(sessions)):
                states = [member_payload[name]["states"][position] for name in names]
                above_n = states.count("A")
                eligible_n = above_n + states.count("B")
                expected_n = len(names)
                above.append(above_n)
                eligible.append(eligible_n)
                expected.append(expected_n)
                pct.append(
                    100.0 * above_n / eligible_n
                    if eligible_n >= 5 and eligible_n >= 0.9 * expected_n else None)
                for state in excluded:
                    excluded[state].append(states.count(state))
            sectors[sector] = {
                "above": above,
                "eligible": eligible,
                "expected": expected,
                "pct": pct,
                "excluded": excluded,
            }

        failed_names = sorted(set(str(name) for name in failures) & expected_members)
        source_evidence = dict(result.attrs.get("member_evidence") or {})
        receipt_fields = (
            "requested_ticker", "response_ticker", "response_status",
            "response_count", "requested_start", "requested_end", "missing_sessions",
            "invalid_sessions", "accepted_values_id", "basis", "adjusted",
            "state", "unavailable", "reason",
        )
        source_receipts: dict[str, dict] = {}
        for name in sorted(member_payload):
            evidence = dict(source_evidence.get(name) or {})
            source_receipts[name] = {
                field: copy.deepcopy(evidence[field])
                for field in receipt_fields if evidence.get(field) is not None
            }
        response_material = {
            "basis": W1_LICENSED_BASIS,
            "requested_start": result.attrs.get("requested_start") or source_sessions[0],
            "requested_end": result.attrs.get("requested_end") or source_sessions[-1],
            "members": {name: source_receipts[name] for name in sorted(member_payload)},
            "unavailable_members": failed_names,
        }
        response_set_id = "sha256:" + hashlib.sha256(json.dumps(
            response_material, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode()).hexdigest()
        latest_expected = (
            result.attrs.get("latest_expected_session")
            or result.attrs.get("requested_end")
            or sessions[-1]
        )
        source_session = result.attrs.get("observed_max_session")
        published_at = pd.Timestamp.now(tz="UTC").isoformat()
        package = {
            "schema": _W1_PACKAGE_SCHEMA,
            "available": any(
                value is not None
                for sector in sectors.values()
                for value in sector["pct"]
            ),
            "method": {
                "name": "sector_participation_20",
                "window_sessions": 20,
                "comparison": "close > MA20",
                "coverage_basis": "complete expected NYSE sessions through selected session",
                "display_floor": {"min_eligible": 5, "min_coverage": 0.9},
                "state_legend": {
                    "A": "eligible_above_ma20",
                    "B": "eligible_equal_or_below_ma20",
                    "H": "insufficient_history",
                    "M": "required_expected_session_missing",
                    "I": "invalid_identity_basis_or_observation",
                    "U": "source_request_unavailable_or_refused",
                },
            },
            "reference": {
                "universe": "S&P 500",
                "roster_id": roster_id,
                "member_count": len(member_payload),
                "observed_at": None,
                "reconstruction": (
                    "The current validated reference roster is held constant across "
                    "the requested historical window; this is not point-in-time membership."
                ),
                "reconstruction_zh": (
                    "当前已验证参考名单在整个历史请求窗口内保持不变；"
                    "这不是按历史时点还原的成分股名单。"
                ),
            },
            "source": {
                "provider": "licensed_vendor",
                "basis": W1_LICENSED_BASIS,
                "requested_start": result.attrs.get("requested_start") or source_sessions[0],
                "requested_end": result.attrs.get("requested_end") or source_sessions[-1],
                "source_session": source_session,
                "latest_expected_session": latest_expected,
                "acquired_at": result.attrs.get("acquired_at"),
                "request_identity": {
                    "resource": "/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
                    "adjusted": True,
                    "sort": "asc",
                    "limit": 50000,
                },
                "response_set_id": response_set_id,
                "requested_member_count": len(member_payload),
                "accepted_member_count": len(member_payload) - len(failed_names),
                "unavailable_member_count": len(failed_names),
            },
            "computed_at": result.attrs.get("computed_at"),
            "published_at": published_at,
            "sessions": sessions,
            "sectors": sectors,
            "members": member_payload,
        }
        package["observation_id"] = _w1_observation_id(package)
        package["generation_id"] = _w1_generation_id(package)
        _validate_w1_package(package)
        return package

    def publish_sector_participation_20(self, result: pd.DataFrame | None,
                                        failures: dict[str, str], members: pd.DataFrame,
                                        *, path=None) -> bool:
        """Atomically replace one validated W1 JSON generation.

        Any acquisition/build/write/replace failure leaves the prior valid generation
        byte-identical.  There is no sidecar and no independently visible detail file.
        """
        if result is None or result.empty:
            log.warning("sector participation W1: no new generation; preserving prior package")
            return False
        target = Path(path or (config.data_dir() / "breadth" / "sector_participation_20.json"))
        try:
            package = self.build_sector_participation_20_package(result, failures, members)
            if not package.get("available") and target.exists():
                try:
                    prior = json.loads(target.read_text(encoding="utf-8"))
                    _validate_w1_package(prior)
                except Exception:  # noqa: BLE001 — an invalid prior is not protected
                    pass
                else:
                    log.warning(
                        "sector participation W1: new generation is below the display "
                        "qualification floor; preserving prior valid package")
                    return False
            w1_contract.write_validated_package(package, target)
            return True
        except Exception as exc:  # noqa: BLE001 — old valid generation is the fallback
            log.warning("sector participation W1 publication failed; prior generation kept: %s", exc)
            return False

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
