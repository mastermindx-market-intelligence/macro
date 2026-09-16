"""Build the China / Hong Kong / Canada sector-treemap heatmap feeds.

The international sibling of ``scripts/build_sp500_heatmap.py``. Reads each
market's local close matrix + sector classification (offline-safe, no keys) and
writes ``site/marketdata/<market>_heatmap.json`` consumed by the shared
``site/heatmap.js`` (flat Sector → stock treemap, ``map_type:"stocks"``).

Sizing
------
* China  — real market cap (``china_search/members.parquet`` ``mktcap_yi`` × 1e8).
* Canada — real market cap (``canada_fundamentals`` ``marketCap``), gaps filled
           from the index ``weight`` calibrated against the names that carry a cap.
* HK     — average dollar turnover (close × volume over the last sessions) from
           the per-name OHLC store, a liquidity proxy for size (no shares feed).

Usage
-----
    python -m scripts.build_market_heatmap                 # all three markets
    python -m scripts.build_market_heatmap --market china  # one market
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import market_heatmap as hm  # noqa: E402
from lib import config  # noqa: E402
from scripts.check_china_heatmap_freshness import (  # noqa: E402
    ChinaHeatmapFreshnessError,
    validate_china_heatmap,
)

log = logging.getLogger("build_market_heatmap")

MARKETS = ("china", "hk", "canada")
_ADV_WINDOW = 30  # sessions averaged for the HK dollar-turnover size proxy


def _data(*parts: str) -> Path:
    return config.data_dir().joinpath(*parts)


def _board_breadth(market: str) -> dict | None:
    """Newest whole-board adv/dec row for *market*, as a plain dict (or None).

    Only China has a whole-board feed (collectors/china_board_breadth). The engine
    gates the row against the map's own as-of date, so a store that stopped
    advancing degrades to the tile-derived count instead of printing a stale board.
    """
    if market != "china":
        return None
    p = _data("china_board_breadth", "breadth.parquet")
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p).sort_index()
    except Exception as e:  # noqa: BLE001 — a corrupt side-store must not break the map
        log.warning("china board breadth unreadable (%s) — tile-derived count stands", e)
        return None
    if df.empty:
        return None
    row = df.iloc[-1].to_dict()
    row["date"] = pd.Timestamp(df.index[-1]).strftime("%Y-%m-%d")
    return row


# --------------------------------------------------------------------------- #
#  China
# --------------------------------------------------------------------------- #
def _load_china() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict, dict]:
    members = pd.read_parquet(_data("china_search", "members.parquet"))
    closes = pd.read_parquet(_data("china_search", "closes.parquet")).sort_index()
    closes.index = pd.to_datetime(closes.index)
    closes = closes.loc[:, ~closes.columns.duplicated()]

    # English display name from name_en (the combined `name` column is "EN / 中文").
    cons = pd.DataFrame(index=members.index)
    cons.index.name = "ticker"
    cons["name"] = members.get("name_en", members.get("name")).fillna(members.index.to_series())
    cons["sector"] = members["sector"].astype(str)

    # china_universe seeds CSI/config extras with a 30.0亿 sentinel (~46% of members
    # carry it exactly) — NOT a real cap; sizing tiles from it fabricates a uniform
    # mid-cap for half the map. Drop the sentinel, then fill the gaps with real caps
    # from the asof-gated Tushare valuation plane (same guard as build_china_library).
    _PLACEHOLDER_MCAP = 30.0
    caps: dict[str, float] = {}
    if "mktcap_yi" in members.columns:
        for t, v in members["mktcap_yi"].items():
            if pd.notna(v) and float(v) > 0 and float(v) != _PLACEHOLDER_MCAP:
                caps[t] = float(v) * 1e8  # 亿 CNY -> absolute CNY
    try:
        from engine.tushare_freshness import prefer_tushare as _prefer_tv
        tv_p = _data("tushare", "valuation.parquet")
        pe_p = _data("china_a_val", "pe.parquet")
        tv = pd.read_parquet(tv_p) if tv_p.exists() else None
        chosen, _src = _prefer_tv(tv if (tv is not None and "total_mv_yi" in tv.columns) else None,
                                  pd.read_parquet(pe_p) if pe_p.exists() else None)
        if _src == "tushare" and chosen is not None and "total_mv_yi" in chosen.columns:
            filled = 0
            member_set = set(cons.index.astype(str))
            for _, r in chosen.iterrows():
                t, v = str(r.get("ticker")), r.get("total_mv_yi")
                if t in member_set and t not in caps and pd.notna(v) and float(v) > 0:
                    caps[t] = float(v) * 1e8
                    filled += 1
            log.info("china heatmap caps: filled %d names from Tushare total_mv_yi "
                     "(30.0亿 placeholders dropped)", filled)
    except Exception as e:  # noqa: BLE001 — Tushare overlay is additive; engine floor covers the rest
        log.debug("china tushare mktcap overlay skipped (%s)", e)

    names_zh: dict[str, str] = {}
    if "name_zh" in members.columns:
        names_zh = {t: str(v) for t, v in members["name_zh"].items() if pd.notna(v) and str(v).strip()}

    return cons, closes, caps, {}, names_zh


# --------------------------------------------------------------------------- #
#  Hong Kong — size = average dollar turnover (liquidity proxy)
# --------------------------------------------------------------------------- #
def _load_hk() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict, dict]:
    cons = pd.read_parquet(_data("hk_breadth", "constituents.parquet"))
    if cons.index.name != "symbol" and "symbol" in cons.columns:
        cons = cons.set_index("symbol")
    cons.index.name = "ticker"

    # The breadth cache is fresh (latest session) but shallow (~30d for most
    # names); closes_deep carries decades of history but ends a few sessions back.
    # Merge so the fresh recent prints win and the deep history fills the rest —
    # the two stores are the same adjusted yfinance series (level-identical on
    # overlap), so the splice is seamless. This unlocks 3M/6M/YTD/1Y for HK.
    # The breadth cache is runner-local (gitignored, actions/cache-ferried) — a
    # runner that missed the restore still renders from the committed deep panel.
    def _read_panel(p) -> pd.DataFrame | None:
        if not p.exists():
            return None
        try:
            df = pd.read_parquet(p).sort_index()
            df.index = pd.to_datetime(df.index)
            return df.loc[:, ~df.columns.duplicated()]
        except Exception as e:  # noqa: BLE001 — either store may be absent/corrupt
            log.warning("hk close panel %s unreadable (%s)", p.name, e)
            return None
    breadth = _read_panel(_data("hk_breadth", "_closes_cache.parquet"))
    deep = _read_panel(_data("hk_search", "closes_deep.parquet"))
    if breadth is not None and deep is not None:
        closes = breadth.combine_first(deep).sort_index()
    elif breadth is not None:
        closes = breadth
    elif deep is not None:
        log.warning("hk heatmap: breadth cache missing — deep panel only")
        closes = deep
    else:
        raise FileNotFoundError("hk close panels missing (hk_breadth/_closes_cache.parquet "
                                "and hk_search/closes_deep.parquet)")

    # ADV$ from the per-name OHLC store (close × volume), averaged over the last
    # valid sessions. Tracks size/importance well (Tencent/Alibaba on top).
    turnover: dict[str, float] = {}
    sdir = _data("hk_stocks")
    if sdir.exists():
        for t in cons.index:
            fp = sdir / f"{t}.parquet"
            if not fp.exists():
                continue
            try:
                df = pd.read_parquet(fp)
            except Exception:  # noqa: BLE001 — corrupt parquet must not break the build
                continue
            if "close" not in df.columns or "volume" not in df.columns:
                continue
            tail = df.dropna(subset=["close", "volume"]).tail(_ADV_WINDOW)
            if len(tail) >= 5:
                adv = float((tail["close"] * tail["volume"]).mean())
                if adv > 0:
                    turnover[t] = adv
    missing = [t for t in cons.index if t not in turnover]
    if missing:
        log.warning("hk heatmap: no turnover for %d/%d names (sized at floor): %s",
                    len(missing), len(cons.index), ", ".join(missing[:12]))
    # Chinese tile labels from the curated map (HK has no zh-name feed). Names
    # absent from the map fall back to the English name in the renderer.
    names_zh = {t: hm.HK_NAME_ZH[t] for t in cons.index if t in hm.HK_NAME_ZH}
    no_zh = [t for t in cons.index if t not in hm.HK_NAME_ZH]
    if no_zh:
        log.info("hk heatmap: %d/%d names have no zh label (English fallback): %s",
                 len(no_zh), len(cons.index), ", ".join(no_zh[:12]))
    return cons, closes, turnover, {}, names_zh


# --------------------------------------------------------------------------- #
#  Canada — real market cap, gaps filled from the calibrated index weight
# --------------------------------------------------------------------------- #
def _canada_caps_from_fundamentals() -> dict[str, float]:
    p = _data("canada_fundamentals", "fundamentals.parquet")
    if not p.exists():
        return {}
    try:
        df = pd.read_parquet(p)
    except Exception as e:  # noqa: BLE001
        log.warning("canada fundamentals unreadable: %s", e)
        return {}
    caps: dict[str, float] = {}
    for _, row in df.iterrows():
        t = str(row.get("ticker") or "").strip()
        pl = row.get("payload")
        if not t or pl is None:
            continue
        try:
            pl = json.loads(pl) if isinstance(pl, str) else pl
        except Exception:  # noqa: BLE001
            continue
        cap = (pl or {}).get("marketCap")
        if cap is not None and float(cap) > 0:
            caps[t] = float(cap)
    return caps


def _complete_caps_from_weight(caps: dict[str, float], weights: dict[str, float]) -> dict[str, float]:
    """Estimate a cap for names missing one from the index weight, calibrated
    (cap ≈ k · weight) against the names that carry both. Keeps mid-caps that
    lack a fundamentals row sized sensibly instead of collapsing to a floor."""
    ratios = [caps[t] / weights[t] for t in weights if t in caps and weights[t] > 0]
    if not ratios:
        return caps
    k = float(np.median(ratios))
    filled = dict(caps)
    n = 0
    for t, w in weights.items():
        if filled.get(t, 0) <= 0 and w > 0:
            filled[t] = k * w
            n += 1
    if n:
        log.info("canada cap-completion: estimated %d caps from index weight", n)
    return filled


def _load_canada() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict, dict]:
    members = pd.read_parquet(_data("canada_search", "members.parquet"))
    closes = pd.read_parquet(_data("canada_search", "closes.parquet")).sort_index()
    closes.index = pd.to_datetime(closes.index)
    closes = closes.loc[:, ~closes.columns.duplicated()]

    cons = pd.DataFrame(index=members.index)
    cons.index.name = "ticker"
    cons["name"] = members["name"].astype(str)
    cons["sector"] = members["sector"].astype(str)

    weights: dict[str, float] = {}
    if "weight" in members.columns:
        weights = {t: float(v) for t, v in members["weight"].items() if pd.notna(v) and float(v) > 0}

    caps = _canada_caps_from_fundamentals()
    # keep only universe names, then complete the gaps from weight
    caps = {t: v for t, v in caps.items() if t in members.index}
    caps = _complete_caps_from_weight(caps, weights)
    return cons, closes, caps, weights, {}


_LOADERS = {"china": _load_china, "hk": _load_hk, "canada": _load_canada}


def _normalise_now(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _plausible_published_china_session(payload: object) -> str | None:
    """Return ``asof`` for a structurally plausible published China payload.

    This deliberately does not compare the payload with the caller's close
    panel. A generic render can have an inferior checkout; using that checkout
    to decide whether a newer on-disk publication is "valid" recreates the
    exact backward-overwrite failure this lane is meant to prevent.
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("market") != "china" or payload.get("source") != "daily-close":
        return None
    try:
        session = date.fromisoformat(str(payload.get("asof") or "").strip()).isoformat()
    except ValueError:
        return None
    tiles = payload.get("tiles")
    n_tiles = payload.get("n_tiles")
    if (
        not isinstance(tiles, list)
        or not tiles
        or isinstance(n_tiles, bool)
        or not isinstance(n_tiles, int)
        or n_tiles != len(tiles)
    ):
        return None
    tickers = [
        str(tile.get("t") or "").strip()
        for tile in tiles
        if isinstance(tile, dict)
    ]
    if len(tickers) != len(tiles) or not all(tickers) or len(set(tickers)) != len(tickers):
        return None
    return session


def render_standalone_page(
    market: str,
    payload: dict,
    *,
    site: Path | None = None,
) -> Path:
    """Render the crawlable/fallback heatmap page from the exact tile payload."""
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n
    from lib.pages import write_page
    from lib.seo import SITE_BASE, is_public_path

    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    env = Environment(
        loader=FileSystemLoader(config.ROOT / "templates"),
        autoescape=True,
    )
    env.filters["min"] = lambda seq: min(seq)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip, SITE_BASE=SITE_BASE)
    summary = hm.page_summary(payload)
    out = site / f"{market}_heatmap.html"
    write_page(
        out,
        env.get_template("market_heatmap.html.j2").render(
            mk=hm.PAGE_META[market],
            summary=summary,
            gated=is_public_path(f"/{market}_heatmap.html"),
            n_tiles=(summary or {}).get("n_tiles") or payload.get("n_tiles") or 0,
            siblings=hm.sibling_markets(market),
        ),
    )
    log.info("wrote %s (%.0f KB, ssr=%s)", out, out.stat().st_size / 1024, bool(summary))
    return out


def build(
    market: str,
    site: Path | None = None,
    *,
    generated_utc: str | None = None,
    now: datetime | None = None,
    render_page: bool = False,
) -> dict:
    """Assemble + write one market's heatmap JSON. Returns the payload.

    China is validated against the completed mainland-session clock before the
    output path is touched.  This prevents a generic render running from a stale
    checkout from overwriting a newer production heatmap with an old session and
    a deceptively fresh ``generated_utc`` timestamp.
    """
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    cons, closes, caps, weights, names_zh = _LOADERS[market]()

    clock = _normalise_now(now)
    generated_utc = generated_utc or clock.strftime("%Y-%m-%d %H:%M")
    payload = hm.build_market_heatmap(
        market, cons, closes,
        caps=caps or None,
        weights=weights or None,
        names_zh=names_zh or None,
        generated_utc=generated_utc,
        board_breadth=_board_breadth(market),
    )
    if market == "china":
        # Binding pre-write fence: build_all() is invoked by generic render lanes
        # whose checkout can predate the settled-close collector.  Never let one
        # of those lanes replace a newer production JSON with stale tiles merely
        # because it stamped a new generated_utc value.
        validate_china_heatmap(
            payload,
            closes,
            now=clock,
            expected_tickers={str(ticker) for ticker in cons.index},
        )

    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{market}_heatmap.json"

    # The asia push loop rebuilds after every rebase to repair a racing stale
    # payload.  Do not manufacture a follow-up commit when the only difference
    # is the wall-clock generation stamp; preserve the already-published stamp
    # when every semantic field is identical.  A changed session/tile/contract
    # still writes normally and receives the fresh generated_utc above.
    result = payload
    write_payload = True
    if market == "china" and out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict):
            existing_session = _plausible_published_china_session(existing)
            candidate_session = str(payload.get("asof") or "").strip()
            if existing_session is not None and existing_session > candidate_session:
                # Monotonic publication fence.  Do not ask an inferior checkout
                # to validate a session it cannot know; that turns "newer than
                # me" into "invalid" and rewrites production backward.
                raise ChinaHeatmapFreshnessError(
                    "China heatmap regression refused",
                    f"existing={existing_session} candidate={candidate_session}",
                )
            try:
                validate_china_heatmap(
                    existing,
                    closes,
                    now=clock,
                    expected_tickers={str(ticker) for ticker in cons.index},
                )
            except ChinaHeatmapFreshnessError as exc:
                log.warning(
                    "%s existing payload is not preservable (%s: %s) — rewriting",
                    out.name,
                    exc.title,
                    exc.detail,
                )
            else:
                existing_semantic = dict(existing)
                payload_semantic = dict(payload)
                existing_semantic.pop("generated_utc", None)
                payload_semantic.pop("generated_utc", None)
                if existing_semantic == payload_semantic:
                    log.info(
                        "%s unchanged for asof=%s — preserving generated_utc=%s",
                        out.name,
                        payload["asof"],
                        existing.get("generated_utc"),
                    )
                    result = existing
                    write_payload = False

    if write_payload:
        out.write_text(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("wrote %s — %d tiles, %d sectors, size=%s, asof=%s",
                 out.name, payload["n_tiles"], len(payload["sectors"]),
                 payload["size_basis"], payload["asof"])
    if render_page:
        render_standalone_page(market, result, site=site)
    return result


def build_all(
    site: Path | None = None,
    *,
    generated_utc: str | None = None,
    now: datetime | None = None,
    render_pages: bool = False,
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    clock = _normalise_now(now)
    for m in MARKETS:
        try:
            out[m] = build(
                m,
                site,
                generated_utc=generated_utc,
                now=clock,
                render_page=render_pages,
            )
        except Exception as e:  # noqa: BLE001 — one market must never break the others / the site
            log.error("%s heatmap failed: %s", m, e)
    return out


def _parse_now(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Build the CN/HK/CA sector heatmap feeds")
    ap.add_argument("--market", choices=MARKETS, help="build a single market (default: all)")
    ap.add_argument("--render-page", action="store_true", help="also render standalone SSR page(s)")
    ap.add_argument("--now", help="freeze the build/session clock (ISO-8601)")
    args = ap.parse_args(argv)
    try:
        now = _parse_now(args.now)
    except ValueError as exc:
        ap.error(f"invalid --now: {exc}")
    if args.market:
        build(args.market, now=now, render_page=args.render_page)
    else:
        build_all(now=now, render_pages=args.render_page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
