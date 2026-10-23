"""Build the China / Hong Kong / Canada sector-treemap heatmap feeds.

The international sibling of ``scripts/build_sp500_heatmap.py``. Reads each
market's local close matrix + sector classification (offline-safe, no keys) and
writes ``site/marketdata/<market>_heatmap.json`` consumed by the shared
``site/heatmap.js`` (flat Sector → stock treemap, ``map_type:"stocks"``). The
optional page publisher renders the matching standalone SSR shell from that
same payload so a close-cycle lane cannot advance the JSON while leaving the
crawler-visible summary on an older observation session.

Sizing
------
* China  — real market cap (``china_search/members.parquet`` ``mktcap_yi`` × 1e8).
* Canada — real market cap (``canada_fundamentals`` ``marketCap``), gaps filled
           from the index ``weight`` calibrated against the names that carry a cap.
* HK     — average dollar turnover (close × volume over the last sessions) from
           the per-name OHLC store, a liquidity proxy for size (no shares feed).

Usage
-----
    python -m scripts.build_market_heatmap                 # all three feeds
    python -m scripts.build_market_heatmap --market china  # one feed
    python -m scripts.build_market_heatmap --market china --render-page
                                                          # feed + matching SSR page
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import market_heatmap as hm  # noqa: E402
from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402

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


def build(market: str, site: Path | None = None, *, generated_utc: str | None = None) -> dict:
    """Assemble + write one market's heatmap JSON. Returns the payload."""
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    cons, closes, caps, weights, names_zh = _LOADERS[market]()

    generated_utc = generated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    payload = hm.build_market_heatmap(
        market, cons, closes,
        caps=caps or None,
        weights=weights or None,
        names_zh=names_zh or None,
        generated_utc=generated_utc,
        board_breadth=_board_breadth(market),
    )

    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{market}_heatmap.json"
    out.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    log.info("wrote %s — %d tiles, %d sectors, size=%s, asof=%s",
             out.name, payload["n_tiles"], len(payload["sectors"]),
             payload["size_basis"], payload["asof"])
    return payload


def build_all(site: Path | None = None, *, generated_utc: str | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for m in MARKETS:
        try:
            out[m] = build(m, site, generated_utc=generated_utc)
        except Exception as e:  # noqa: BLE001 — one market must never break the others / the site
            log.error("%s heatmap failed: %s", m, e)
    return out


def _page_environment() -> Environment:
    """Standalone renderer environment matching the build_site heatmap surface."""
    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"), autoescape=True)
    env.filters["min"] = lambda seq: min(seq)
    from engine import i18n
    from lib.seo import SITE_BASE

    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip, SITE_BASE=SITE_BASE)
    return env


def _page_payload(market: str, payload: dict | None, site: Path) -> dict | None:
    """Use the just-built payload or the last committed file, exactly as the browser will."""
    if payload:
        return payload
    try:
        return json.loads((site / "marketdata" / f"{market}_heatmap.json").read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — no map means an honest empty shell
        log.debug("%s heatmap page has no readable payload (%s)", market, e)
        return None


def render_page(
    market: str,
    payload: dict | None = None,
    site: Path | None = None,
    *,
    env: Environment | None = None,
) -> Path:
    """Render one standalone heatmap page from the payload its browser will fetch."""
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    payload = _page_payload(market, payload, site)
    summary = hm.page_summary(payload)
    from lib.seo import is_public_path

    gated = is_public_path(f"/{market}_heatmap.html")
    env = env or _page_environment()
    out = site / f"{market}_heatmap.html"
    write_page(out, env.get_template("market_heatmap.html.j2").render(
        mk=hm.PAGE_META[market],
        summary=summary,
        gated=gated,
        n_tiles=(summary or {}).get("n_tiles") or (payload or {}).get("n_tiles") or 0,
        siblings=hm.sibling_markets(market),
    ))
    log.info("wrote %s (%.0f KB, ssr=%s, gated=%s)", out, out.stat().st_size / 1024,
             bool(summary), gated)
    return out


def render_pages(
    payloads: dict[str, dict] | None = None,
    site: Path | None = None,
    *,
    env: Environment | None = None,
) -> dict[str, Path]:
    """Render all three pages through the one shared payload-to-SSR owner."""
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    payloads = payloads or {}
    env = env or _page_environment()
    return {market: render_page(market, payloads.get(market), site, env=env) for market in MARKETS}


def _commit_staged_pair(market: str, staged_site: Path, site: Path) -> None:
    """Replace the generated pair only after both staged artifacts exist."""
    source_json = staged_site / "marketdata" / f"{market}_heatmap.json"
    source_page = staged_site / f"{market}_heatmap.html"
    if not source_json.is_file() or not source_page.is_file():
        raise RuntimeError(f"{market} heatmap staging did not produce a complete pair")

    target_json = site / "marketdata" / f"{market}_heatmap.json"
    target_page = site / f"{market}_heatmap.html"
    target_json.parent.mkdir(parents=True, exist_ok=True)
    site.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}-{market}"
    pending_json = target_json.with_name(f".{target_json.name}.{token}.tmp")
    pending_page = target_page.with_name(f".{target_page.name}.{token}.tmp")
    backup_json = target_json.with_name(f".{target_json.name}.{token}.bak")
    backup_page = target_page.with_name(f".{target_page.name}.{token}.bak")
    had_json = target_json.is_file()
    had_page = target_page.is_file()
    replaced_json = False
    replaced_page = False
    try:
        # Prepare both target-filesystem copies and rollback material before
        # exposing either new artifact. Two paths cannot be renamed atomically;
        # if the second replacement fails, restore the first before returning.
        shutil.copyfile(source_json, pending_json)
        shutil.copyfile(source_page, pending_page)
        if had_json:
            shutil.copy2(target_json, backup_json)
        if had_page:
            shutil.copy2(target_page, backup_page)
        os.replace(pending_json, target_json)
        replaced_json = True
        os.replace(pending_page, target_page)
        replaced_page = True
    except Exception as exc:
        rollback_errors: list[str] = []
        for replaced, had_prior, backup, target in (
            (replaced_page, had_page, backup_page, target_page),
            (replaced_json, had_json, backup_json, target_json),
        ):
            if not replaced:
                continue
            try:
                if had_prior:
                    os.replace(backup, target)
                else:
                    target.unlink(missing_ok=True)
            except Exception as rollback_exc:  # noqa: BLE001 — preserve exact damage
                rollback_errors.append(f"{target}: {rollback_exc}")
        if rollback_errors:
            raise RuntimeError(
                f"{market} heatmap pair replacement failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    finally:
        for path in (pending_json, pending_page, backup_json, backup_page):
            path.unlink(missing_ok=True)


def publish(
    market: str,
    site: Path | None = None,
    *,
    generated_utc: str | None = None,
    env: Environment | None = None,
) -> dict:
    """Publish one coherent JSON + SSR-page pair and return the exact payload.

    The payload and page are built outside the destination first. A template or
    validation failure therefore leaves the prior committed pair untouched rather
    than advancing only the browser JSON before asia-close's final site commit.
    """
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    site.parent.mkdir(parents=True, exist_ok=True)
    # Stage outside the repository: an interrupted runner must not leave an
    # untracked publish directory in the worktree that the final site commit can
    # mistake for product output. _commit_staged_pair prepares same-filesystem
    # destination temps only after both artifacts are complete.
    with tempfile.TemporaryDirectory(prefix=f".{market}-heatmap-publish-") as staging:
        staged_site = Path(staging)
        payload = build(market, staged_site, generated_utc=generated_utc)
        render_page(market, payload, staged_site, env=env)
        _commit_staged_pair(market, staged_site, site)
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Build the CN/HK/CA sector heatmap feeds")
    ap.add_argument("--market", choices=MARKETS, help="build a single market (default: all)")
    ap.add_argument("--render-page", action="store_true",
                    help="also render the matching standalone SSR page(s)")
    ap.add_argument("--generated-utc",
                    help="stable generation label (YYYY-MM-DD HH:MM) for publish retries")
    args = ap.parse_args(argv)
    if args.market:
        if args.render_page:
            publish(args.market, generated_utc=args.generated_utc)
        else:
            build(args.market, generated_utc=args.generated_utc)
    else:
        payloads = build_all(generated_utc=args.generated_utc)
        if args.render_page:
            render_pages(payloads)
    return 0


if __name__ == "__main__":
    sys.exit(main())
