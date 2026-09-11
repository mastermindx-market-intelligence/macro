"""China Central Bank & Government Policy Watch — assembler.

LEAF · DISPLAY/CONTEXT-ONLY · KEYLESS. The China sibling of the US policy_watch page,
but PBoC-and-State-Council-centric. Fans together, with no new scoring:

  * PBoC stance + rate corridor + FX/reserves  (engine/china_pboc_stance.py)
  * NBS latest-prints board                      (china_macro / china_credit stores)
  * Policy tape                                  (filtered china_news_intel PIT bus)
  * Curated intel substrate                      (data/china_policy/intel.json:
      thesis · NPC targets · sector-policy matrix · falsifiable prediction ledger)

Emits the page view-model + a compact data/china_policy/latest.json (the machine-readable
hub contract the intel bus + future China Mastermind read). Never raises.
See research/CHINA_INTEL_POWERHOUSE.md §3.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from lib import config, store

log = logging.getLogger(__name__)

SCHEMA = "china_policy_watch.v1"

# NBS / macro latest-prints board: (group, series, col, label_en, label_zh, unit)
_NBS_BOARD = [
    ("china_macro", "pmi", "pmi_mfg", "Mfg PMI", "制造业PMI", ""),
    ("china_macro", "pmi", "pmi_nonmfg", "Non-mfg PMI", "非制造业PMI", ""),
    ("china_macro", "cpi", "cpi_yoy", "CPI YoY", "CPI同比", "%"),
    ("china_macro", "ppi", "ppi_yoy", "PPI YoY", "PPI同比", "%"),
    ("china_macro", "money_supply", "m2_yoy", "M2 YoY", "M2同比", "%"),
    ("china_macro", "money_supply", "m1_yoy", "M1 YoY", "M1同比", "%"),
    ("china_macro", "gdp", "gdp_yoy", "GDP YoY", "GDP同比", "%"),
    ("china_macro", "retail", "retail_yoy", "Retail YoY", "社零同比", "%"),
    ("china_macro", "customs", "exports_yoy", "Exports YoY", "出口同比", "%"),
    ("china_credit", "tsf", "tsf_total", "TSF (mo)", "社融(当月)", "¥bn"),
]

_POLICY_THEMES = {"policy", "monetary", "fiscal", "trade", "industrial_policy", "credit"}


def _latest(group: str, name: str, col: str):
    try:
        df = store.read(group, name)
        if df is None or df.empty or col not in df.columns:
            return None, None
        s = df[col].dropna()
        if s.empty:
            return None, None
        return float(s.iloc[-1]), str(s.index.max().date())
    except Exception:  # noqa: BLE001
        return None, None


def _nbs_prints() -> list[dict]:
    rows = []
    for group, name, col, en, zh, unit in _NBS_BOARD:
        v, d = _latest(group, name, col)
        if v is None:
            continue
        rows.append({"label_en": en, "label_zh": zh,
                     "value": round(v, 2), "unit": unit, "asof": d})
    return rows


def _host(url: str) -> str:
    """Lowercased hostname with a leading www. stripped. Empty on unparseable URL."""
    from urllib.parse import urlparse
    try:
        h = (urlparse(url or "").netloc or "").lower()
    except Exception:  # noqa: BLE001
        return ""
    return h[4:] if h.startswith("www.") else h


def _china_news_cfg() -> dict:
    """Same config block the official-pages fetcher reads."""
    from engine.china_news import _cfg
    return _cfg()


def _official_pages() -> list[dict]:
    """Fetcher source: cfg['official_pages'] or the OFFICIAL_PAGES constant."""
    from engine.china_news import OFFICIAL_PAGES
    return _china_news_cfg().get("official_pages") or OFFICIAL_PAGES


def _official_hosts() -> set[str]:
    """Hostnames of the same official-pages list the fetcher uses (www. stripped)."""
    return {_host(p.get("url", "")) for p in _official_pages()} - {""}


def _host_in(host: str, hosts: set[str]) -> bool:
    if not host:
        return False
    if host in hosts:
        return True
    return any(host.endswith("." + h) for h in hosts if h)


def _china_native_hosts() -> set[str]:
    """china_native / zh NEWS_PAGES domains (yicai.com, stcn.com, …)."""
    from engine.china_news import NEWS_PAGES
    hosts = set()
    for p in NEWS_PAGES:
        if p.get("tier") == "china_native" or p.get("source_lang") == "zh":
            d = (p.get("domain") or _host(p.get("url", ""))).casefold()
            if d:
                hosts.add(d)
    return hosts


def _host_anchors_china(host: str) -> bool:
    """Hostname leg of the China gate.

    `_host()` lowercases; `_is_china_anchored` casefolds strong tokens, so
    chinadaily.com.cn matches "China". yicai.com has no token — it lands via
    the china_native page list. A .cn TLD is itself a China domain anchor
    (cls.cn), after the theme slice has already restricted the row.
    """
    h = (host or "").casefold()
    if not h:
        return False
    from engine.china_news import _is_china_anchored
    if _is_china_anchored(h):
        return True
    if h.endswith(".cn"):
        return True
    return _host_in(h, _china_native_hosts())


def _official_page_name(host: str) -> str:
    for p in _official_pages():
        ph = _host(p.get("url", ""))
        if ph and _host_in(host, {ph}):
            return str(p.get("name") or ph)
    return ""


def _source_chip(url: str, source: str) -> str:
    """Per-row officialness: official-page name if the host is one, else the host."""
    host = _host(url)
    return _official_page_name(host) or host or (source or "")


def row_is_china_policy(title: str, url: str, source_tier: int = 0, *,
                        official_hosts: set[str] | None = None) -> bool:
    """China-desk gate for the policy tape.

    Keep a row when (a) a China anchor lands in the title or hostname, or
    (b) source_tier==1 (official-pages fetch tag — the docstring promise),
    or (c) the host is in the same official-pages list the fetcher uses
    (config `official_pages` or OFFICIAL_PAGES). A Eurozone/Fed monetary
    flash on a global wire must not fill this card.
    """
    if int(source_tier or 0) == 1:
        return True
    host = _host(url)
    hosts = official_hosts if official_hosts is not None else _official_hosts()
    if _host_in(host, hosts):
        return True
    from engine.china_news import _is_china_anchored
    return _is_china_anchored(title or "") or _host_anchors_china(host)


def _select_policy_feed_rows(df, top_n: int = 12) -> list[dict]:
    """Theme/tier slice, then the China gate. Empty list is a designed empty — never unfiltered."""
    from engine import china_news_intel as ni
    if df is None or getattr(df, "empty", True):
        return []
    mask = (df["source_tier"] == 1) | (df["theme"].isin(_POLICY_THEMES))
    sub = df[mask].sort_values("first_seen_utc", ascending=False)
    official_hosts = _official_hosts()
    out = []
    for r in sub.itertuples():
        if not row_is_china_policy(getattr(r, "title", ""), getattr(r, "url", ""),
                                   getattr(r, "source_tier", 0),
                                   official_hosts=official_hosts):
            continue
        tl = ni.THEME_LABEL.get(r.theme, (r.theme, r.theme))
        url = r.url
        src = r.source
        out.append({"title": r.title, "url": url, "source": src,
                    "source_chip": _source_chip(url, src),
                    "theme": r.theme, "theme_en": tl[0], "theme_zh": tl[1],
                    "tier": int(r.source_tier),
                    "scheduled_ref": getattr(r, "scheduled_ref", "") or ""})
        if len(out) >= top_n:
            break
    return out


def _policy_feed(top_n: int = 12) -> tuple[str, list[dict]]:
    """China-gated policy-tape slice.

    Returns (status, rows):
      * ``ok`` — one or more China rows survived the gate
      * ``quiet`` — the parquet loaded, but zero China rows survived
      * ``unavailable`` — missing parquet or a read exception
    Quiet and unavailable must not share a UI sentence.
    """
    try:
        import pandas as pd
        from engine import china_news_intel as ni
        path = ni._events_path()
        if not path.exists():
            return "unavailable", []
        df = pd.read_parquet(path)
        rows = _select_policy_feed_rows(df, top_n=top_n)
        if rows:
            return "ok", rows
        return "quiet", []
    except Exception as e:  # noqa: BLE001
        log.debug("china policy feed unavailable (%s)", e)
        return "unavailable", []


def _intel() -> dict:
    try:
        p = config.ROOT / "data" / "china_policy" / "intel.json"
        if p.exists():
            return json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        log.debug("china policy intel.json unreadable (%s)", e)
    return {}


def _compact(pboc: dict | None, intel: dict) -> dict:
    """The machine-readable latest.json the intel bus + China Mastermind read.

    PBoC corridor mixes vintages — LPR is monthly while FR007/CNY are daily — so each field
    carries its own asof, the top-level asof is the NEWEST constituent (not LPR-anchored),
    and `stale` flags when even the newest is > ~35 days old."""
    corridor = {c["key"]: c["value"] for c in (pboc or {}).get("corridor", [])}
    fx = (pboc or {}).get("fx", {})
    asof_lpr = (pboc or {}).get("asof")
    asof_res = fx.get("asof_reserves")
    asof_cny = fx.get("asof_cny")
    dates = [d for d in (asof_lpr, asof_res, asof_cny) if d]
    newest = max(dates) if dates else str(date.today())
    stale = False
    try:
        stale = (date.today() - date.fromisoformat(newest[:10])).days > 35
    except (ValueError, TypeError):
        pass
    return {
        "schema": SCHEMA, "is_context_only": True,
        "asof": newest, "asof_lpr": asof_lpr, "asof_reserves": asof_res, "asof_cny": asof_cny,
        "stale": stale,
        "stance": (pboc or {}).get("stance"),
        "stance_en": (pboc or {}).get("stance_en"), "stance_zh": (pboc or {}).get("stance_zh"),
        "lpr_1y": corridor.get("lpr_1y"), "lpr_5y": corridor.get("lpr_5y"),
        "rrr": corridor.get("rrr"), "fr007": corridor.get("fr007"),
        "fx_reserves": fx.get("reserves"), "usd_cny": fx.get("usd_cny"),
        "last_moves": [m.get("detail_en") for m in (pboc or {}).get("last_moves", [])],
        "predictions": [p.get("text_en") for p in intel.get("predictions", [])
                        if p.get("status") == "open"],
    }


def snapshot(asof: date | str | None = None) -> dict | None:
    """Full China Policy Watch view-model + the compact latest.json payload. Never raises."""
    try:
        from engine import china_pboc_stance, policy_dates
        pboc = china_pboc_stance.snapshot(asof)
        intel = _intel()
        prints = _nbs_prints()
        feed_status, feed = _policy_feed()
        if pboc is None and not prints and not intel:
            return None
        # Audit fix: annotate the intel substrate with live date status so the template can
        # surface the intel age and warn when the hand-authored intel.json is stale (>14d).
        intel_dates = policy_dates.annotate(intel)
        # National Team Radar — display-tier state-intervention footprint gauge. Additive and
        # degrade-safe: a failure degrades to None (the template guards on it).
        try:
            from engine import china_national_team
            national_team = china_national_team.snapshot(asof)
        except Exception as e:  # noqa: BLE001 — additive, never fatal
            log.error("china_policy_watch: national_team snapshot failed (%s)", e)
            national_team = None
        return {
            "schema": SCHEMA, "is_context_only": True,
            "asof": (str(asof) if asof else (pboc or {}).get("asof") or str(date.today())),
            "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "pboc": pboc, "nbs_prints": prints,
            "policy_feed": feed, "policy_feed_status": feed_status,
            "intel": intel,
            "intel_dates": intel_dates,
            "national_team": national_team,
            "latest": _compact(pboc, intel),
        }
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("china_policy_watch.snapshot failed (%s)", e)
        return None


def write_latest(vm: dict | None) -> None:
    """Persist the compact contract to data/china_policy/latest.json (for the bus)."""
    try:
        if not vm or not vm.get("latest"):
            return
        p = config.ROOT / "data" / "china_policy" / "latest.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(vm["latest"], ensure_ascii=False,
                                separators=(",", ":"), default=str))
    except Exception as e:  # noqa: BLE001
        log.error("china_policy_watch.write_latest failed (%s)", e)
