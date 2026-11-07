"""Fetch the baskets-only DEEP close store the thematic baskets render over.

The thematic baskets (engine/baskets.py) read the FREE breadth price caches. Two gaps make
those caches insufficient on their own:

  1. OFF-INDEX members — on-thesis names outside the S&P-1500 universe (recent IPOs like
     Circle/CRCL, Cerebras/CBRS, CoreWeave/CRWV, Arm/ARM, Astera/ALAB; the nuclear leg
     Oklo/NuScale/Centrus; the crypto-equity cohort MicroStrategy/Riot/Galaxy). Adding them
     to the breadth constituent lists would silently pollute the S&P-1500 breadth/factor
     universe the rest of the dashboard depends on.
  2. SHALLOW history — the large-cap breadth cache is a ~15-month ROLLING window (it only needs
     enough tape for 200DMA / NH-NL). So a large-cap-heavy basket (mag7, defensives, …) would
     render only a ~15-month stub and flag every member `partial`, even though full history is
     freely available from yfinance.

So we keep a SEPARATE, baskets-only DEEP close cache and let engine.baskets PREFER it:

    data/baskets/extras.parquet     wide [Date x TICKER] close matrix, deep (~3y) history
    data/yahoo/IBIT.parquet etc.    ETF proxies a basket references but the site doesn't track

engine.baskets.compute_baskets() combine_first's this store over the shallow breadth columns,
so every basket resolves a deep series and off-index members resolve at all. The free-S&P-1500
invariant elsewhere is untouched (this store is read by baskets only).

The fetch list is DERIVED, not hard-coded: every membership ticker that the mid/small-cap caches
do NOT already hold deeply is fetched here (large-caps + off-index) — so the store self-maintains
as membership.json evolves. Members already deep in the mid/small-cap caches are left to those.

Keyless (yfinance), batched. Additive and non-fatal: the fresh pull is MERGED onto the prior
store (prior fills any column the pull missed), so a flaky day can never drop a member or break
the daily build.

Usage: python -m scripts.fetch_basket_extras
"""
from __future__ import annotations

import json
import logging
import sys
import time
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from collections.abc import Mapping
from types import MappingProxyType
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.ticker_aliases import YAHOO_FETCH_ALIASES as ALIASES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_basket_extras")

START = "2023-01-01"        # a touch before the baskets seed_date (2023-05-09)
RETRIES = 4
BACKOFF_S = 3.0
BATCH = 60                  # tickers per yfinance download call

# Ticker renames where the vendor symbol differs from the membership ticker (Yahoo serves
# the series under a different symbol — sometimes the old one, sometimes the new one).
# Fetched under the value, stored under the key. Shared with the DEEP-store sibling
# scripts/fetch_basket_ohlcv via lib/ticker_aliases: this map used to be local to each
# collector, and the entry that was here but not there is why the deep store never held MMC.

# ETF proxies a basket's reference cross-check points at but the rest of the site does not
# already cache (members go in extras.parquet; proxies go in the yahoo store like SPY).
PROXIES = [
    "IBIT",   # spot-BTC ETF — the crypto basket's "what is it beta to" anchor
    "GDX",    # VanEck Gold Miners — direct reference for the gold_miners basket
    "SIL",    # Global X Silver Miners — direct reference for the silver_miners basket
    "KWEB",   # KraneShares CSI China Internet — proxy for 0700/3690/1810/1024 in hk_adr_bridge
    "FXI",    # iShares China Large-Cap — proxy for 0981 (SMIC) in hk_adr_bridge + intl/cycle scripts
    "TCOM",   # Trip.com Group ADR — direct twin for 9961.HK in hk_adr_bridge (identity fix 2026-08-03)
]


def _deep_cache_columns() -> set[str]:
    """Tickers the mid/small-cap caches already hold DEEPLY (~3y). Members in here don't need a
    yfinance backfill — only the shallow large-cap cache (~15m rolling) and off-index names do."""
    cols: set[str] = set()
    for grp in ("smallcap_breadth", "midcap_breadth"):
        p = config.data_dir() / grp / "_closes_cache.parquet"
        if p.exists():
            cols |= set(pd.read_parquet(p).columns)
    return cols


def _membership_tickers() -> set[str]:
    p = config.data_dir() / "baskets" / "membership.json"
    if not p.exists():
        return set()
    mem = json.loads(p.read_text())
    out: set[str] = set()
    for b in (mem.get("baskets") or {}).values():
        for m in b.get("members", []):
            t = m.get("ticker")
            if t:
                out.add(t)
    return out


def _download_closes(tickers: list[str], *, request_settings=None,
                     history_start: str = START, source_session: str | None = None) -> pd.DataFrame:
    """Adjusted closes for `tickers`, [Date x TICKER], deep history from START. Reuses the breadth
    yfinance pattern (crumb/cookie auth that works headless), batched with retry+backoff."""
    if (request_settings is None) != (source_session is None):
        raise ValueError("Explicit extras download requires both policy and source session")
    strict = request_settings is not None
    batch_size = request_settings.batch_size if strict else BATCH
    retries = request_settings.retries if strict else RETRIES
    backoff = request_settings.backoff_base_s if strict else BACKOFF_S
    import yfinance as yf
    frames: list[pd.DataFrame] = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        for attempt in range(retries):
            try:
                df = yf.download(batch, start=history_start, auto_adjust=True,
                                 progress=False, group_by="column", threads=True)
                if df is None or df.empty:
                    raise RuntimeError("empty frame")
                if strict:
                    closes = _capture_close_response(df, requested=tuple(batch), source_session=source_session)
                else:
                    closes = df["Close"] if "Close" in df.columns.get_level_values(0) else df
                    if isinstance(closes, pd.Series):              # single-ticker shape
                        closes = closes.to_frame(batch[0])
                    closes = closes.sort_index()
                frames.append(closes)
                break
            except Exception as e:  # noqa: BLE001
                wait = backoff * (2 ** attempt)
                log.warning("batch %d/%d (%s…) attempt %d failed (%s); retry in %.0fs",
                            i // batch_size + 1, (len(tickers) - 1) // batch_size + 1, batch[0], attempt + 1, e, wait)
                time.sleep(wait)
        else:
            log.error("batch starting %s failed after %d retries — leaving to prior store", batch[0], retries)
    if not frames:
        raise RuntimeError("all download batches failed")
    if strict:
        from lib import adjusted_price_capture as bounds
        union = pd.DatetimeIndex([])
        names = []
        for frame in frames:
            union = union.union(frame.index)
            names.extend(frame.columns)
        if (len(names) != len(set(names)) or len(union) > bounds.MAX_ROWS
                or len(names) > bounds.MAX_COLUMNS or len(union) * len(names) > bounds.MAX_PANEL_CELLS):
            raise bounds.AdjustedCaptureError("extras_download_union_bound")
    out = pd.concat(frames, axis=1).sort_index()
    return out.loc[:, ~out.columns.duplicated()]


@dataclass(frozen=True)
class BasketExtrasAcquisition:
    """Private values/evidence; per-basket admission remains its existing owner."""
    status: str
    source_session: str
    effective_as_of: str | None
    archive: pd.DataFrame
    resolved_panel: pd.DataFrame
    resolution: Mapping[str, object]
    requested: tuple[str, ...]
    downloaded: tuple[str, ...]
    retained: tuple[str, ...]
    unresolved: tuple[str, ...]
    evidence: Mapping[str, object]


def _capture_close_response(frame, *, requested: tuple[str, ...], source_session: str) -> pd.DataFrame:
    from lib.adjusted_price_capture import capture_close_panel, AdjustedCaptureError, MAX_ROWS
    if (not isinstance(frame, pd.DataFrame) or frame.empty or len(frame) > MAX_ROWS
            or not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans
            or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
            or frame.index.tz is not None or not frame.index.equals(frame.index.normalize())
            or frame.columns.has_duplicates):
        raise AdjustedCaptureError("invalid_extras_response")
    multi = isinstance(frame.columns, pd.MultiIndex)
    if (multi and frame.columns.nlevels != 2) or (not multi and len(requested) != 1):
        raise AdjustedCaptureError("ambiguous_extras_symbols")
    level0 = frame.columns.get_level_values(0) if multi else frame.columns
    if "Close" not in level0 or (multi and not set(frame.columns.get_level_values(1)).issubset(requested)):
        raise AdjustedCaptureError("unexpected_extras_symbols")
    closes = frame["Close"]
    if isinstance(closes, pd.Series): closes = closes.to_frame(requested[0])
    if closes.columns.has_duplicates or not set(closes.columns).issubset(requested):
        raise AdjustedCaptureError("unexpected_extras_symbols")
    closes = closes.loc[closes.index <= pd.Timestamp(source_session)].reindex(columns=requested)
    if closes.empty:
        raise AdjustedCaptureError("no_completed_extras_observations")
    return capture_close_panel(closes, source_session=source_session)


def acquire_extras_from_inputs(*, membership: Mapping, primary_panel: pd.DataFrame,
                               prior_extras: pd.DataFrame | None,
                               qualified_primary_members: frozenset[str],
                               primary_history_threshold: int, evaluation_instant: datetime,
                               yahoo_config: Mapping, aliases: Mapping, history_start: str,
                               primary_basis: str = "unrecorded",
                               index_membership: Mapping | None = None) -> BasketExtrasAcquisition:
    """Acquire through the incumbent downloader; keep the actual resolver choice.

    ``qualified_primary_members`` is supplied by the caller's captured primary
    source owner and is checked against the actual frozen primary column. Depth
    controls download planning only; it never excludes a newly observed IPO.
    This function performs no legacy store, proxy-seed or publication effects.
    """
    from collectors.yahoo import YahooRequestSettings
    from lib import market_session, adjusted_price_capture as captured
    from lib.closes_panel import resolve_thematic_close_panel, population_observation
    if (not isinstance(evaluation_instant, datetime) or evaluation_instant.tzinfo is None
            or evaluation_instant.utcoffset() is None or not isinstance(membership, Mapping)
            or not isinstance(aliases, Mapping) or not isinstance(qualified_primary_members, frozenset)
            or any(not isinstance(t, str) for t in qualified_primary_members)
            or type(primary_history_threshold) is not int or primary_history_threshold < 1
            or primary_basis not in ("unrecorded", "provider_auto_adjusted")):
        raise captured.AdjustedCaptureError("invalid_extras_request")
    try:
        if not isinstance(history_start, str) or date.fromisoformat(history_start).isoformat() != history_start:
            raise ValueError
    except (TypeError, ValueError):
        raise captured.AdjustedCaptureError("invalid_extras_history_start") from None
    request = YahooRequestSettings.capture(yahoo_config)
    policy_start = str(history_start)
    evaluation = evaluation_instant.astimezone(timezone.utc)
    local = market_session.market_local_date("US", evaluation)
    target = market_session.expected_session("US", evaluation)
    if (not market_session.calendar_verified("US", local.year)
            or not market_session.calendar_verified("US", target.year) or date.fromisoformat(policy_start) > target):
        raise captured.AdjustedCaptureError("extras_target_calendar_or_start_invalid")
    source = target.isoformat()
    primary = captured.capture_close_panel(primary_panel, source_session=source)
    prior = captured.capture_close_panel(prior_extras, source_session=source, allow_absent=True)
    if primary.empty or not bool(primary.iloc[-1].notna().any()):
        raise captured.AdjustedCaptureError("observed_frozen_primary_tail_required")
    # Membership-time eligibility stays with the existing basket observation owner.
    document = deepcopy(dict(membership))
    if index_membership is not None:
        # The native receipt requires the strict thematic contract before any
        # provider request. Legacy callers retain their existing value API.
        from lib.breadth_member_generation_contract import _membership
        _membership(document, primary)
    baskets = document.get("baskets")
    if not isinstance(baskets, dict) or len(baskets) > 1000:
        raise captured.AdjustedCaptureError("invalid_basket_membership")
    requested_set, active_set = set(), set()
    required_end = {}
    populations = {}
    for basket_id, basket in baskets.items():
        if not isinstance(basket_id, str) or not isinstance(basket, dict) or not isinstance(basket.get("members"), list):
            raise captured.AdjustedCaptureError("invalid_basket_membership")
        rows = basket["members"]
        if len(rows) > 5000 or any(not isinstance(row, dict) for row in rows):
            raise captured.AdjustedCaptureError("invalid_basket_membership")
        for row in rows:
            ticker = row.get("ticker") or row.get("symbol")
            if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,23}", ticker):
                raise captured.AdjustedCaptureError("invalid_basket_member_symbol")
            for when in (row.get("added"), row.get("removed")):
                if when is not None:
                    try:
                        if not isinstance(when, str) or date.fromisoformat(when).isoformat() != when: raise ValueError
                    except (TypeError, ValueError):
                        raise captured.AdjustedCaptureError("invalid_basket_member_date") from None
            # Historical resolution keeps the full dated-membership universe.
            # Its visible end is the last frozen-calendar date within any of
            # that member's existing added/removed intervals; no new clock.
            requested_set.add(ticker)
            eligible_dates = primary.index
            if row.get("added"): eligible_dates = eligible_dates[eligible_dates >= pd.Timestamp(row["added"])]
            if row.get("removed"): eligible_dates = eligible_dates[eligible_dates < pd.Timestamp(row["removed"])]
            if len(eligible_dates):
                required_end[ticker] = max(required_end.get(ticker, eligible_dates[-1]), eligible_dates[-1])
        observation = population_observation(primary, rows, primary.index[-1])
        populations[basket_id] = observation["configured_members"]
        active_set.update(observation["configured_members"])
    index_populations = None
    if index_membership is not None:
        from lib.sector_index_membership_capture import index_population
        additional, eligible, ends, index_populations = index_population(
            deepcopy(dict(index_membership)), primary=primary, before=evaluation)
        requested_set.update(additional)
        active_set.update(eligible)
        for ticker, end in ends.items():
            required_end[ticker] = max(required_end.get(ticker, end), end)
    requested = tuple(sorted(requested_set))
    if not requested or len(requested) > captured.MAX_COLUMNS:
        raise captured.AdjustedCaptureError("empty_or_oversized_basket_membership")
    alias_values = deepcopy(dict(aliases))
    mapping = {t: alias_values.get(t, t) for t in requested}
    if (any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^=-]{0,23}", v)
            for v in mapping.values()) or len(set(mapping.values())) != len(mapping)):
        raise captured.AdjustedCaptureError("extras_vendor_alias_collision_or_invalid")
    basis = {"primary_breadth": primary_basis, "baskets_extras": "unrecorded"}
    def resolve(archive):
        names = [ticker for ticker in requested if ticker in archive.columns]
        if (len(primary) * len(names) > captured.MAX_PANEL_CELLS
                or len(primary) * len(requested) > captured.MAX_PANEL_CELLS):
            raise captured.AdjustedCaptureError("extras_resolver_projection_bound")
        # Keep the full archive separately; the incumbent resolver need only
        # allocate the historical membership universe on this frozen calendar.
        return resolve_thematic_close_panel(primary, archive.loc[:, names], requested, source_basis=basis)
    _, initial_resolution = resolve(prior)
    skipped = []
    no_visible_obligation = tuple(t for t in requested if t not in required_end)
    for ticker in requested:
        column = primary[ticker].dropna() if ticker in primary else pd.Series(dtype=float)
        required = pd.Timestamp(source) if ticker in active_set else required_end.get(ticker)
        if (ticker in qualified_primary_members and len(column) >= primary_history_threshold
                and required is not None and required in column.index
                and initial_resolution["price_source"].get(ticker) == "primary_breadth"):
            skipped.append(ticker)
    needed = tuple(ticker for ticker in requested if ticker not in skipped and ticker not in no_visible_obligation)
    fresh = captured.empty_panel()
    failed_download = False
    if needed:
        request_map = {t: mapping[t] for t in needed}
        try:
            raw = _download_closes(list(request_map.values()), request_settings=request,
                                   history_start=policy_start, source_session=source)
        except RuntimeError:
            failed_download = True
        else:
            raw = captured.capture_close_panel(raw, source_session=source)
            if not set(raw.columns).issubset(request_map.values()):
                raise captured.AdjustedCaptureError("unexpected_extras_symbols")
            inverse = {v: k for k, v in request_map.items()}
            fresh = raw.rename(columns=inverse).copy(deep=True)
    union_index = prior.index.union(fresh.index).sort_values().as_unit("ns")
    union_columns = sorted(set(prior.columns) | set(fresh.columns))
    if (len(union_index) > captured.MAX_ROWS or len(union_columns) > captured.MAX_COLUMNS
            or len(union_index) * len(union_columns) > captured.MAX_PANEL_CELLS):
        raise captured.AdjustedCaptureError("extras_archive_union_bound")
    archive = prior.reindex(index=union_index, columns=union_columns).copy(deep=True)
    downloaded, unresolved, member_evidence = [], [], {}
    for ticker in requested:
        old = prior[ticker].dropna() if ticker in prior else pd.Series(dtype=float)
        new = fresh[ticker].dropna() if ticker in fresh else pd.Series(dtype=float)
        required = pd.Timestamp(source) if ticker in active_set else required_end.get(ticker)
        refreshed = (ticker in needed and len(new) > 0 and required is not None and required in new.index
                     and (not len(old) or old.index.isin(new.index).all()))
        if refreshed:
            archive[ticker] = fresh[ticker].reindex(union_index)
            downloaded.append(ticker)
        elif ticker in needed:
            unresolved.append(ticker)
        member_evidence[ticker] = {"vendor_symbol": mapping[ticker], "download_requested": ticker in needed,
            "returned_span": [new.index[0].date().isoformat(), new.index[-1].date().isoformat()] if len(new) else None,
            "downloaded": bool(refreshed), "archive_prior_retained": bool(len(old) and not refreshed),
            "refresh_unresolved": ticker in unresolved,
            "refresh_reason": ("download_failed" if failed_download else "missing_target_or_prior_observations")
                if ticker in unresolved else None,
            "acquisition_basis": "provider_auto_adjusted" if refreshed else None}
    resolved, resolution = resolve(archive)
    retained = tuple(ticker for ticker in prior.columns if ticker not in downloaded)
    for ticker in requested:
        chosen = resolution["price_source"].get(ticker)
        observed = resolved[ticker].dropna() if ticker in resolved else pd.Series(dtype=float)
        member_evidence[ticker].update({"selected_source": chosen,
            "selection_reason": resolution["selection_reason"].get(ticker),
            "selected_history_sessions": len(observed),
            "selected_history_start": observed.index[0].date().isoformat() if len(observed) else None,
            "selected_observation_date": observed.index[-1].date().isoformat() if len(observed) else None,
            "target_observed": bool(len(observed) and observed.index[-1] == pd.Timestamp(source)),
            "currently_eligible": ticker in active_set,
            "required_history_end": required_end[ticker].date().isoformat() if ticker in required_end else None,
            "required_history_end_observed": bool(ticker in required_end and required_end[ticker] in observed.index),
            "desk_observed": bool(primary.index[-1] in observed.index),
            "chosen_prior_retained": chosen == "baskets_extras" and ticker in retained,
            "chosen_acquired_this_attempt": chosen == "baskets_extras" and ticker in downloaded,
            "supplied_primary_qualified": ticker in qualified_primary_members,
            "stitched": deepcopy(resolution["stitched"].get(ticker))})
    selection_shortfalls = tuple(t for t in requested if t in required_end
                                 and not member_evidence[t]["required_history_end_observed"])
    for ticker in requested:
        member_evidence[ticker]["selection_history_shortfall"] = ticker in selection_shortfalls
    complete = (not unresolved and not selection_shortfalls
                and all(member_evidence[t]["target_observed"] for t in active_set))
    status = "complete" if complete else "partial" if any(member_evidence[t]["desk_observed"] for t in requested) else "unavailable"
    evidence = {"evaluation_instant": evaluation.isoformat(), "source_session": source,
        "effective_as_of": resolution["effective_as_of"], "completed_sessions_only": True,
        "request": {"history_start": policy_start, "batch_size": request.batch_size,
                    "retries": request.retries, "backoff_base_s": request.backoff_base_s,
                    "primary_history_threshold": primary_history_threshold},
        "skipped_qualified_primary": list(skipped), "basket_populations": populations,
        "currently_eligible": sorted(active_set), "no_visible_history_obligation": list(no_visible_obligation),
        "selection_history_shortfalls": list(selection_shortfalls),
        "members": member_evidence,
        "unknown": {"vendor_publication_clock": "Not supplied per bar by yfinance",
                    "provider_available_at": "First retrievable time is not observed"}}
    if index_populations is not None:
        evidence["index_populations"] = index_populations
    return BasketExtrasAcquisition(status, source, resolution["effective_as_of"], archive, resolved,
        MappingProxyType(resolution), requested, tuple(downloaded), retained, tuple(unresolved), MappingProxyType(evidence))


def main() -> int:
    bdir = config.data_dir() / "baskets"
    bdir.mkdir(parents=True, exist_ok=True)
    out = bdir / "extras.parquet"

    deep = _deep_cache_columns()
    members = _membership_tickers()
    needed = sorted(members - deep)        # large-caps (shallow cache) + off-index — everything not already deep
    if not needed:
        log.info("no deep basket members to fetch (all %d already deep in the mid/small-cap caches)", len(members))
        return _seed_proxies()

    log.info("fetching deep history for %d basket members (%d already deep): %s",
             len(needed), len(members & deep), ", ".join(needed))
    try:
        fetch_syms = [ALIASES.get(t, t) for t in needed]          # resolve renamed tickers to Yahoo's symbol
        fresh = _download_closes(fetch_syms)
        fresh = fresh.rename(columns={v: k for k, v in ALIASES.items()})   # store back under the membership ticker
        fresh = fresh.reindex(columns=[t for t in needed if t in fresh.columns]).dropna(axis=1, how="all")
        blank = sorted(set(needed) - set(fresh.columns))
        if blank:
            log.warning("no data returned for: %s", ", ".join(blank))
        # MERGE onto the prior store so a partial/flaky pull never drops a column: fresh wins where
        # present, prior backfills any column/cell the pull missed.
        prior = pd.read_parquet(out) if out.exists() else None
        merged = fresh if prior is None else fresh.combine_first(prior)
        merged.index = pd.DatetimeIndex(merged.index)
        merged.index.name = "Date"
        merged = merged.sort_index()
        if not merged.empty:
            merged.to_parquet(out)
            spans = {t: str(merged[t].dropna().index.min().date()) for t in fresh.columns}
            log.info("wrote %s (%d tickers, %d kept from prior; first dates: %s)",
                     out, len(merged.columns), len(set(merged.columns) - set(fresh.columns)), spans)
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("extras fetch failed, keeping prior cache: %s", e)

    return _seed_proxies()


def _seed_proxies() -> int:
    """ETF proxies -> yahoo store (close[,volume]), matching SPY.parquet's shape. Only seed if absent."""
    for p in PROXIES:
        if (config.data_dir() / "yahoo" / f"{p}.parquet").exists():
            continue
        try:
            px = _download_closes([p])
            if p in px.columns:
                s = px[p].dropna().to_frame("close")
                s.index.name = "Date"
                s.to_parquet(config.data_dir() / "yahoo" / f"{p}.parquet")
                log.info("seeded proxy %s (%d rows from %s)", p, len(s), s.index.min().date())
        except Exception as e:  # noqa: BLE001
            log.warning("proxy %s fetch failed: %s", p, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
