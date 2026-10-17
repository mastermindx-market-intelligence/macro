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
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import market_heatmap as hm  # noqa: E402
from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402
from scripts.check_china_heatmap_freshness import (  # noqa: E402
    ChinaHeatmapFreshnessError, validate_china_heatmap,
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


def _validate_hk_completed_session(
    payload: dict, closes: pd.DataFrame, cons: pd.DataFrame, now: datetime,
) -> str:
    """Fail-closed settled HK cash-session payload, with current-member coverage.

    The HK breadth cache may be a runner-local restored snapshot while the
    committed deep panel remains several sessions back. A regenerated timestamp
    is never proof of fresh EOD marks. This is a local check on the incumbent
    publisher, not an alternate store or exchange calendar.
    """
    from lib import hk_calendar
    completed = hk_calendar.expected_last_session(now).isoformat()
    current = list(dict.fromkeys(map(str, cons.index)))
    if not current:
        raise RuntimeError("HK heatmap missing curated membership")
    source_idx = pd.to_datetime(closes.index).tz_localize(None).normalize()
    source = closes.copy()
    source.index = source_idx
    session = pd.Timestamp(completed)
    represented = [t for t in current if t in source.columns]
    if session not in source.index:
        raise RuntimeError(f"HK heatmap close stale: source missing {completed}")
    current_values = pd.to_numeric(source.loc[session, represented], errors="coerce")
    valid = sum(pd.notna(x) and float(x) > 0 for x in current_values)
    if valid / len(current) < 0.95:
        raise RuntimeError(
            f"HK heatmap close stale: only {valid}/{len(current)} positive "
            f"observations on required {completed}"
        )
    prior = hk_calendar.last_session_on_or_before(
        date.fromisoformat(completed) - timedelta(days=1)
    )
    if pd.Timestamp(prior) not in source.index:
        raise RuntimeError(f"HK heatmap previous session absent: {prior}")
    prior_values = pd.to_numeric(
        source.loc[pd.Timestamp(prior), represented], errors="coerce"
    )
    paired = sum(
        pd.notna(a) and pd.notna(b) and float(a) > 0 and float(b) > 0
        for a, b in zip(current_values, prior_values)
    )
    if paired / len(current) < 0.95:
        raise RuntimeError(
            f"HK heatmap previous session incomplete: 1D paired "
            f"{paired}/{len(current)} for {prior}->{completed}"
        )
    tiles = payload.get("tiles")
    if (payload.get("market") != "hk" or payload.get("map_type") != "stocks"
        or payload.get("source") != "daily-close"
        or payload.get("asof") != completed or not isinstance(tiles, list)
        or payload.get("n_tiles") != len(tiles)):
        raise RuntimeError(f"HK heatmap payload session/identity disagrees with {completed}")
    members = set(current)
    shown = [tile.get("t") for tile in tiles if isinstance(tile, dict)]
    if (len(shown) != len(tiles) or len(set(shown)) != len(shown)
        or not set(shown).issubset(members)
        or len(shown) / len(current) < 0.95):
        raise RuntimeError("HK heatmap payload membership coverage/identity invalid")
    valid_1d = sum(
        isinstance((tile.get("perf") or {}).get("1D"), (int, float))
        and not isinstance((tile.get("perf") or {}).get("1D"), bool)
        and np.isfinite((tile.get("perf") or {}).get("1D"))
        for tile in tiles
    )
    if valid_1d / len(current) < 0.95:
        raise RuntimeError(
            f"HK heatmap 1D observations incomplete: {valid_1d}/{len(current)} "
            f"rendered across {prior}->{completed}"
        )
    return completed


def _validate_hk_page(html: str, session: str) -> None:
    """One SSR market-day receipt matching the exact committed HK JSON pair."""
    if 'id="hm-ssr"' not in html or "marketdata/hk_heatmap.json" not in html:
        raise RuntimeError("HK heatmap SSR missing its payload/summary anchor")
    match = re.search(
        r'class=["\'][^"\']*\bhx-pulse-when\b[^"\']*["\'][^>]*>\s*'
        r'(\d{4}-\d{2}-\d{2})\s*</',
        html,
    )
    if not match or match.group(1) != session:
        raise RuntimeError(f"HK heatmap SSR session does not equal JSON {session}")


def build(
    market: str, site: Path | None = None, *,
    generated_utc: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Assemble + write one market's heatmap JSON. Returns the payload."""
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    cons, closes, caps, weights, names_zh = _LOADERS[market]()

    clock = _normalise_now(now)
    generated_utc = generated_utc or clock.strftime("%Y-%m-%d %H:%M")
    if market == "hk":
        # Never allow a still-open HK cash session to leak through a Yahoo
        # in-progress bar. The separate HK source collector validates marks.
        from lib import hk_calendar
        cutoff = pd.Timestamp(hk_calendar.expected_last_session(clock))
        closes = closes.copy()
        closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
        closes = closes.loc[closes.index <= cutoff]
    payload = hm.build_market_heatmap(
        market, cons, closes,
        caps=caps or None,
        weights=weights or None,
        names_zh=names_zh or None,
        generated_utc=generated_utc,
        board_breadth=_board_breadth(market),
    )
    if market == "china":
        validate_china_heatmap(
            payload, closes, now=clock,
            expected_tickers={str(t) for t in cons.index},
        )
    elif market == "hk":
        _validate_hk_completed_session(payload, closes, cons, clock)

    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{market}_heatmap.json"
    if market == "china" and out.is_file():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = None
        old_session = _plausible_published_china_session(existing)
        candidate_session = str(payload.get("asof") or "")
        if old_session and old_session > candidate_session:
            raise ChinaHeatmapFreshnessError(
                "China heatmap regression refused",
                f"existing={old_session} candidate={candidate_session}",
            )
        if old_session == candidate_session and isinstance(existing, dict):
            try:
                validate_china_heatmap(
                    existing, closes, now=clock,
                    expected_tickers={str(t) for t in cons.index},
                )
            except ChinaHeatmapFreshnessError:
                pass
            else:
                old_fields, new_fields = dict(existing), dict(payload)
                old_fields.pop("generated_utc", None)
                new_fields.pop("generated_utc", None)
                if old_fields == new_fields:
                    return existing
    out.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    log.info("wrote %s — %d tiles, %d sectors, size=%s, asof=%s",
             out.name, payload["n_tiles"], len(payload["sectors"]),
             payload["size_basis"], payload["asof"])
    return payload


def build_all(
    site: Path | None = None, *,
    generated_utc: str | None = None, now: datetime | None = None,
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    clock = _normalise_now(now)
    for m in MARKETS:
        try:
            out[m] = build(m, site, generated_utc=generated_utc, now=clock)
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
    now: datetime | None = None,
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
        clock = _normalise_now(now)
        payload = build(market, staged_site, generated_utc=generated_utc, now=clock)
        render_page(market, payload, staged_site, env=env)
        if market == "hk":
            _validate_hk_page(
                (staged_site / "hk_heatmap.html").read_text(encoding="utf-8"),
                str(payload["asof"]),
            )
            latest = site / "marketdata" / "hk_heatmap.json"
            if latest.is_file():
                try:
                    old_hk = json.loads(latest.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    old_hk = None
                if isinstance(old_hk, dict) and old_hk.get("market") == "hk":
                    previous = str(old_hk.get("asof") or "")
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", previous) and previous > payload["asof"]:
                        raise RuntimeError(
                            f"HK heatmap regression refused: published={previous}, candidate={payload['asof']}"
                        )
        if market == "china":
            current_json = site / "marketdata" / "china_heatmap.json"
            current_html = site / "china_heatmap.html"
            if current_json.is_file():
                try:
                    old = json.loads(current_json.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    old = None
                old_session = _plausible_published_china_session(old)
                if old_session and old_session > str(payload.get("asof") or ""):
                    raise ChinaHeatmapFreshnessError(
                        "China heatmap regression refused",
                        f"published={old_session} candidate={payload.get('asof')}",
                    )
                if old_session == payload.get("asof") and isinstance(old, dict):
                    old_fields, new_fields = dict(old), dict(payload)
                    old_fields.pop("generated_utc", None)
                    new_fields.pop("generated_utc", None)
                    if old_fields == new_fields and current_html.is_file():
                        from scripts.check_china_heatmap_freshness import validate_china_heatmap_page
                        try:
                            validate_china_heatmap_page(
                                current_html.read_text(encoding="utf-8"),
                                str(payload["asof"]),
                            )
                        except (ChinaHeatmapFreshnessError, OSError, ValueError):
                            pass
                        else:
                            log.info("China JSON/SSR unchanged — preserve published pair")
                            return old
        _commit_staged_pair(market, staged_site, site)
    return payload


def _parse_now(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Build the CN/HK/CA sector heatmap feeds")
    ap.add_argument("--market", choices=MARKETS, help="build a single market (default: all)")
    ap.add_argument("--render-page", action="store_true",
                    help="also render the matching standalone SSR page(s)")
    ap.add_argument("--generated-utc",
                    help="stable generation label (YYYY-MM-DD HH:MM) for publish retries")
    ap.add_argument("--now", help="freeze the completed-session clock (ISO-8601)")
    args = ap.parse_args(argv)
    now = _parse_now(args.now)
    if args.market:
        if args.render_page:
            publish(args.market, generated_utc=args.generated_utc, now=now)
        else:
            build(args.market, generated_utc=args.generated_utc, now=now)
    else:
        payloads = build_all(generated_utc=args.generated_utc, now=now)
        if args.render_page:
            render_pages(payloads)
    return 0


if __name__ == "__main__":
    sys.exit(main())
