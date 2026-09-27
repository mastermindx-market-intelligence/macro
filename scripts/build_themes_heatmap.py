"""Build the Finviz *themes* treemap data feed (offline-safe).

Reads the committed Finviz snapshot (``data/themes_heatmap/themes_tree.json`` +
``perf_snapshot.json``, refreshed by ``scripts/fetch_finviz_themes.py``) and
writes ``site/marketdata/themes_heatmap.json``, consumed by the themes map-type
of ``site/sector_heatmap.html``. No network: the snapshot is the source of
record, so CI/offline builds always render.

Usage
-----
    python -m scripts.build_themes_heatmap
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import baskets as baskets_owner  # noqa: E402
from engine import equity_factors as ef  # noqa: E402
from engine import extension as ext  # noqa: E402
from engine import group_earnings as ge  # noqa: E402
from engine import guidance_gap as gg  # noqa: E402
from engine import narrative_rotation as nr  # noqa: E402
from engine import stock_fundamentals as sf  # noqa: E402
from engine import theme_crowding as tc  # noqa: E402
from engine import theme_rerating_durability as trd  # noqa: E402
from engine import theme_revisions as tr  # noqa: E402
from engine import themes_heatmap as th  # noqa: E402
from engine import valuation as valuation_owner  # noqa: E402
from lib import config, nyse_calendar, store  # noqa: E402

log = logging.getLogger("build_themes_heatmap")


def _data(*parts: str) -> Path:
    return config.data_dir().joinpath(*parts)


_AUTO = object()
_EVENT_LOOKBACK_CALENDAR_DAYS = 450


def _event_context_by_key(
    tree: list,
    asof: str,
    *,
    earn=_AUTO,
    eightk=_AUTO,
    hits=_AUTO,
) -> dict[str, dict]:
    """Group-Earnings owner rules projected onto Finviz source-local rosters.

    No new event classifier is introduced: this adapter supplies each subtheme roster to
    group_earnings.member_event_context. Missing source stores return an empty mapping.
    """
    if earn is _AUTO:
        earn = ge._earnings_store()
    if eightk is _AUTO:
        eightk = ge._eightk_results()
    if hits is _AUTO:
        try:
            hits = gg._hits()
        except Exception:  # noqa: BLE001 — guidance is optional context
            hits = None
    if earn is None and eightk is None and hits is None:
        return {}

    day = datetime.strptime(asof, "%Y-%m-%d").date()
    sessions = nyse_calendar.sessions_between(
        day - timedelta(days=_EVENT_LOOKBACK_CALENDAR_DAYS), day
    )
    if not sessions or sessions[-1] != day:
        return {}
    session_index = pd.DatetimeIndex(sessions)
    all_tickers = sorted({
        str(ticker).strip().upper()
        for theme in tree
        for sub in theme.get("subsectors", []) or []
        for ticker in sub.get("members", []) or []
        if str(ticker).strip()
    })
    shared_events = ge.build_report_events(
        all_tickers, session_index, earn, eightk
    )
    out: dict[str, dict] = {}
    for theme in tree:
        for sub in theme.get("subsectors", []) or []:
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            members = [
                str(ticker).strip().upper()
                for ticker in sub.get("members", []) or []
                if str(ticker).strip()
            ]
            out[key] = ge.member_event_context(
                members,
                as_of=pd.Timestamp(day),
                sessions=session_index,
                earn=earn,
                eightk=eightk,
                guidance_hits=hits,
                events=shared_events,
            )
    return out


def _theme_member_tickers(tree: list) -> list[str]:
    return sorted({
        str(ticker).strip().upper()
        for theme in tree
        for sub in theme.get("subsectors", []) or []
        for ticker in sub.get("members", []) or []
        if str(ticker).strip()
    })


def _current_roster_level(closes: pd.DataFrame) -> pd.Series:
    """Equal-weight level for today's roster over its available history.

    This is a DISPLAY texture, not a PIT backtest: the caller discloses current-roster
    membership explicitly. Missing member bars are skipped day by day; no member price
    is forward-filled here.
    """
    if closes is None or closes.empty:
        return pd.Series(dtype=float)
    ret = closes.pct_change(fill_method=None)
    ew = ret.mean(axis=1, skipna=True)
    first = ew.first_valid_index()
    out = pd.Series(np.nan, index=closes.index, dtype=float)
    if first is not None:
        out.loc[first:] = (1.0 + ew.loc[first:].fillna(0.0)).cumprod()
    return out


def _fragility_context_by_key(
    tree: list,
    *,
    closes=_AUTO,
    bench_close=_AUTO,
    valuation_by_ticker=_AUTO,
) -> dict[str, dict]:
    """Crowding/extension + valuation context for source-local Finviz subthemes.

    Owner reuse only:
      * price panel: engine.equity_factors + engine.baskets extras
      * market residuals: engine.narrative_rotation._market_residuals
      * extension: engine.extension.extension_signals
      * crowding: engine.theme_crowding.basket_crowding
      * valuation blocks: engine.stock_fundamentals.valuation_context_for_tickers
      * valuation bands: engine.valuation.read

    Nothing here creates a score, rank, gate, size, alert, exit order or trade action.
    """
    all_tickers = _theme_member_tickers(tree)

    if valuation_by_ticker is _AUTO:
        try:
            valuation_by_ticker = sf.valuation_context_for_tickers(all_tickers)
        except Exception as exc:  # noqa: BLE001 — optional named leg
            log.warning("theme valuation context unavailable: %s", exc)
            valuation_by_ticker = {}
    valuation_by_ticker = valuation_by_ticker or {}

    if closes is _AUTO:
        try:
            closes = ef._closes()
            extras = baskets_owner._basket_extras()
            if extras is not None and not extras.empty:
                add = [c for c in extras.columns if c not in closes.columns]
                if add:
                    closes = closes.join(extras[add], how="outer")
        except Exception as exc:  # noqa: BLE001 — optional named leg
            log.warning("theme crowding price panel unavailable: %s", exc)
            closes = None

    if bench_close is _AUTO:
        try:
            bench_df = store.read("yahoo", "SPY")
            bench_close = (
                bench_df["close"].astype(float)
                if bench_df is not None and "close" in bench_df.columns
                else None
            )
        except Exception as exc:  # noqa: BLE001 — optional named leg
            log.warning("theme crowding benchmark unavailable: %s", exc)
            bench_close = None

    panel = None
    residual_all = pd.DataFrame()
    extension_all: dict[str, dict] = {}
    bench_level = pd.Series(dtype=float)

    if closes is not None and not closes.empty and bench_close is not None:
        try:
            panel = closes.loc[:, [t for t in all_tickers if t in closes.columns]].copy()
            panel.index = pd.DatetimeIndex(panel.index)
            if panel.index.tz is not None:
                panel.index = panel.index.tz_localize(None)
            panel = panel[~panel.index.duplicated(keep="last")].sort_index()

            bench = bench_close.copy()
            bench.index = pd.DatetimeIndex(bench.index)
            if bench.index.tz is not None:
                bench.index = bench.index.tz_localize(None)
            bench = bench[~bench.index.duplicated(keep="last")].sort_index()
            bench = bench.reindex(panel.index)
            bench_tip = bench.last_valid_index()
            if bench_tip is None:
                raise ValueError("SPY benchmark has no overlap with theme price panel")
            panel = panel.loc[:bench_tip]
            bench = bench.loc[:bench_tip].ffill()
            bench_ret = bench.pct_change(fill_method=None)

            present = [c for c in panel.columns if panel[c].notna().sum() >= 60]
            panel = panel[present]
            if len(present) >= 3:
                residual_all = nr._market_residuals(panel, bench_ret)
                extension_all = ext.extension_signals(panel)
                first = bench.first_valid_index()
                if first is not None and float(bench.loc[first]) > 0:
                    bench_level = bench / float(bench.loc[first])
        except Exception as exc:  # noqa: BLE001 — optional named leg
            log.warning("theme crowding context unavailable: %s", exc)
            panel = None
            residual_all = pd.DataFrame()
            extension_all = {}
            bench_level = pd.Series(dtype=float)

    out: dict[str, dict] = {}
    for theme in tree:
        theme_name = str(theme.get("theme") or theme.get("key") or "").strip()
        for sub in theme.get("subsectors", []) or []:
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            members = [
                str(ticker).strip().upper()
                for ticker in sub.get("members", []) or []
                if str(ticker).strip()
            ]

            crowd = None
            price_present: list[str] = []
            if panel is not None and not panel.empty and not bench_level.empty:
                price_present = [
                    ticker for ticker in members
                    if ticker in panel.columns and panel[ticker].notna().sum() >= 60
                ]
                if len(price_present) >= 3:
                    member_close = panel[price_present]
                    level = _current_roster_level(member_close)
                    resid_cols = [t for t in price_present if t in residual_all.columns]
                    ext_rows = [
                        extension_all[t]
                        for t in price_present
                        if t in extension_all
                    ]
                    crowd = tc.basket_crowding(
                        residual_all[resid_cols] if len(resid_cols) >= 3 else pd.DataFrame(),
                        level / bench_level,
                        ext_rows,
                    )

            valuation_reads: list[dict] = []
            for ticker in members:
                raw = valuation_by_ticker.get(ticker)
                if not raw:
                    continue
                read = valuation_owner.read({"valuation": raw})
                if read:
                    valuation_reads.append({"ticker": ticker, **read})

            band_counts = {
                band: sum(row.get("band") == band for row in valuation_reads)
                for band in ("cheap", "fair", "stretched", "extreme")
            }
            basis_counts: dict[str, int] = {}
            for row in valuation_reads:
                basis = str(row.get("basis") or "unknown")
                basis_counts[basis] = basis_counts.get(basis, 0) + 1
            fwd = [
                float(row["forward_pe"])
                for row in valuation_reads
                if row.get("forward_pe") is not None
            ]
            n_members = len(members)
            n_val = len(valuation_reads)
            crowd_state = (
                "unavailable"
                if not crowd or crowd.get("crowding_z") is None
                else "crowded"
                if crowd.get("crowded")
                else "not_crowded"
            )
            ext_read = (crowd or {}).get("extension") or {}
            if ext_read.get("n") is None:
                extension_state = "unavailable"
            elif float(ext_read.get("pct_parabolic") or 0) > 0:
                extension_state = "parabolic_present"
            elif float(ext_read.get("pct_stretched") or 0) > 0:
                extension_state = "stretched_present"
            else:
                extension_state = "not_extended"

            out[key] = {
                "key": key,
                "theme": theme_name,
                "name": str(sub.get("name") or key).strip(),
                "authority": dict(trd.AUTHORITY),
                "basis": {
                    "membership":
                        "current_finviz_roster_historical_texture_not_pit_backtest",
                    "crowding_owner": "engine.theme_crowding.basket_crowding",
                    "crowding_semantics":
                        "owner_downsize_texture_not_adopted_as_size_or_exit_authority_here",
                    "market_residual_owner":
                        "engine.narrative_rotation._market_residuals",
                    "extension_owner": "engine.extension.extension_signals",
                    "valuation_owner": "engine.valuation.read",
                    "valuation_block_owner":
                        "engine.stock_fundamentals.valuation_context_for_tickers",
                },
                "crowding": {
                    "state": crowd_state,
                    "n_members": n_members,
                    "n_price_covered": len(price_present),
                    "coverage": (
                        round(len(price_present) / n_members, 3)
                        if n_members else None
                    ),
                    "read": crowd,
                },
                "extension": {
                    "state": extension_state,
                    **ext_read,
                },
                "valuation": {
                    "n_members": n_members,
                    "n_covered": n_val,
                    "coverage": round(n_val / n_members, 3) if n_members else None,
                    "band_counts": band_counts,
                    "watch_count": sum(bool(row.get("watch")) for row in valuation_reads),
                    "basis_counts": dict(sorted(basis_counts.items())),
                    "forward_pe_covered": len(fwd),
                    "forward_pe_median": (
                        round(float(np.median(fwd)), 1) if fwd else None
                    ),
                    "semantics":
                        "per_name_owner_distribution_no_group_valuation_score",
                },
                "decision_authority": {
                    "can_support_buy_decision": False,
                    "can_support_exit_decision": False,
                    "can_support_rotate_decision": False,
                },
            }
    return out


def _attach_revision_durability(
    payload: dict,
    tree: list,
    *,
    latest=_AUTO,
    hist=_AUTO,
    events=_AUTO,
    fragility=_AUTO,
) -> bool:
    """Attach named revision confirmation to the EXISTING owner heatmap payload.

    Missing revision stores are an honest no-op; the heatmap keeps its price context.
    Tests can inject frames directly without touching the data plane.
    """
    if latest is _AUTO:
        latest = tr._latest()
    if latest is None:
        return False
    if hist is _AUTO:
        hist = tr._history()
    if events is _AUTO:
        try:
            events = _event_context_by_key(tree, str(payload.get("asof") or ""))
        except Exception as exc:  # noqa: BLE001 — event context is an optional named leg
            log.warning("theme earnings/guidance context unavailable: %s", exc)
            events = {}
    if fragility is _AUTO:
        try:
            fragility = _fragility_context_by_key(tree)
        except Exception as exc:  # noqa: BLE001 — optional named leg
            log.warning("theme crowding/valuation fragility unavailable: %s", exc)
            fragility = {}
    price_context = {
        "subthemes": [tile["repricing"] for tile in payload.get("tiles", [])
                      if isinstance(tile.get("repricing"), dict)]
    }
    durability = trd.build_durability(
        tree,
        price_context,
        latest,
        hist,
        event_context_by_key=events or {},
        fragility_context_by_key=fragility or {},
    )
    by_key = {row["key"]: row for row in durability["subthemes"]}
    for tile in payload.get("tiles", []):
        tile["durability"] = by_key.get(tile.get("t"))
    payload["durability"] = {
        key: value for key, value in durability.items() if key != "subthemes"
    }
    return True


def build(site: Path | None = None, *, generated_utc: str | None = None) -> dict:
    """Assemble + write the themes heatmap JSON. Returns the payload."""
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])

    tree_path = _data("themes_heatmap", "themes_tree.json")
    perf_path = _data("themes_heatmap", "perf_snapshot.json")
    tree = json.loads(tree_path.read_text())
    snap = json.loads(perf_path.read_text())

    # as-of = the snapshot's embedded capture date. Never trust file mtime here:
    # on CI runners a checkout rewrites files with mtime = checkout time, so a
    # frozen snapshot would display today's date (#2690 class). mtime remains
    # only as an offline-safe fallback for legacy snapshots without the field.
    asof = snap.get("asof") or datetime.fromtimestamp(
        perf_path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
    generated_utc = generated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    payload = th.build_themes_heatmap(
        tree,
        snap.get("subsector_perf") or {},
        snap.get("member_perf") or {},
        generated_utc=generated_utc,
        asof=asof,
        source=snap.get("source") or "finviz-themes",
    )
    try:
        _attach_revision_durability(payload, tree)
    except Exception as exc:  # noqa: BLE001 — optional named leg, never kills price map
        log.warning("theme repricing revision durability unavailable: %s", exc)

    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "themes_heatmap.json"
    out.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    log.info("wrote %s — %d themes, %d subsector tiles, %d members, asof %s",
             out, len(payload["sectors"]), payload["n_tiles"],
             payload.get("n_members", 0), asof)
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    argparse.ArgumentParser(description="Build the Finviz themes heatmap feed").parse_args(argv)
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
