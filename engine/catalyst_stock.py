"""Single-stock catalyst / tone RESEARCH BRIEF (LLM "Option 2").

LEAF · GATED · DEFAULT-OFF · RESEARCH/CONTEXT-ONLY. This is the per-stock analogue
of engine/master_brain.py (the cross-asset Tier-B synthesis): it assembles ONE
ticker's already-computed PUBLIC context — the cycle/ladder signal, the technical
state, the cross-sectional factor z-scores, and the EDGAR fundamentals — adds an
optional DeepSeek V4 Flash digest of that stock's recent public news, then asks a
reasoning model (DeepSeek V4 Pro) to write a short research brief:
    {summary, drivers[], risks[], catalysts[], confidence, is_context_only, ...}

It NEVER feeds a score, signal or position size; nothing in the scoring path
imports it. It is firewalled exactly like engine/commodity_news.py and
engine/catalyst_tone.py: it imports nothing from the mechanical core, and every
public function returns plain data or None and NEVER raises into the pipeline —
all network / parse / LLM failures degrade to a flagged record or None.

FIREWALL — what is sent to the (third-party) model:
  ONLY PUBLIC / DERIVED context about the stock itself — price/technical state,
  the deterministic cycle-ladder read, public cross-sectional factor scores, and
  public SEC-EDGAR fundamentals, plus public news headlines. NO holdings, NO
  positions, NO watchlist composition — none of those is ever read or sent. The
  context is assembled from a fixed whitelist of public fields (see
  `assemble_context`), so a user's portfolio cannot leak even by accident.

REUSE: the model client, the tolerant JSON parser, the citation-normalizer and
the confidence ranks come straight from engine/catalyst_tone (the Tier-A digest
leaf) — this module does not re-implement them. The news leg reuses
catalyst_tone.digest_document() wholesale, so all FIVE Tier-A safety gates
(tolerant parse, schema-validate, verbatim-citation-verify, confidence-floor,
degrade-never-raise) apply to the news read for free; it is additionally gated by
catalyst_tone.enabled() and degrades to "no news" when that switch is off.

STATIC-SITE DELIVERY (and the on-demand upgrade path)
-----------------------------------------------------
The dashboard is a STATIC GitHub-Pages site. A browser "analyze this" button
CANNOT call DeepSeek directly without shipping the API key to the client, so true
on-demand-for-any-ticker is NOT possible from the static site. The MVP here is
therefore a BUILD-TIME PRECOMPUTE: `precompute_briefs()` writes
site/stockbrief/<TICKER>.json for a small, bounded set (the watchlist's suggested
tickers + the action-board "standout" stocks), cached per ticker per day to cap
cost (~$0.04/brief). stock.html fetches that file client-side and shows a
"🧠 AI brief" panel, hidden when the file is absent (i.e. the default-off case).

UPGRADE (documented follow-up, NOT built here): to make the button work for ANY
searched ticker on demand, put the model call behind a SERVERLESS PROXY that holds
the key server-side and enforces per-IP rate limits — a Supabase Edge Function is
the natural fit since the repo already uses Supabase (see config `watchlist`). The
browser would POST a ticker to the function; the function would run this module's
brief_for_ticker() (or a JS port of the same firewalled context assembly) and
return the JSON. Until then, coverage = the precomputed set.
"""
from __future__ import annotations

import json
import copy
import logging
import os
import re
import secrets
import time
from datetime import date, datetime, timezone
from pathlib import Path

from lib import config
# Reuse the Tier-A digest leaf's primitives — do NOT reinvent them.
from engine.catalyst_tone import _client, _extract_json  # noqa: F401  (shared leaf utils)
from engine import catalyst_tone as _tone

log = logging.getLogger(__name__)

_CONF = {"low", "medium", "high"}
_MAX_ITEMS = 8          # cap each list field so a runaway reply can't bloat the JSON
_MAX_STR = 600          # cap any single bullet / the summary

DISCLAIMER_TEXT = (
    "Research context only — not a signal, not advice. This is an AI-generated "
    "reading of one stock's PUBLIC, already-computed context (its cycle/technical "
    "state, cross-sectional factor scores, SEC fundamentals, and recent public "
    "news). It does NOT feed any score, signal, ladder call or position size, and "
    "it can be wrong or overconfident. The mechanical engine never sees it. Verify "
    "every claim against the deterministic analysis on the same page. No holdings "
    "or watchlist information is used."
)

STOCK_SYSTEM = (
    "You are an equity research analyst writing a SHORT, sober research brief on ONE "
    "stock for a self-directed trader. You are given that stock's OWN already-computed "
    "PUBLIC context: its deterministic cycle/ladder signal, technical state, "
    "cross-sectional factor z-scores (value/quality/low-vol/etc., where + is a "
    "favourable tilt), SEC-EDGAR fundamentals, and an OPTIONAL digest of recent public "
    "news. Your job is to SYNTHESIZE that context into a readable brief — not to "
    "recompute it, invent numbers, or issue a buy/sell.\n\n"
    "Rules:\n"
    "- Use ONLY the provided context. Never fabricate a price, ratio, score or news "
    "item. If something isn't in the context, treat it as unknown and say so.\n"
    "- Do NOT give a recommendation, target price or position size — the "
    "deterministic system owns the call. Give the READ: what is driving the stock, "
    "what could go wrong, and what's on the calendar.\n"
    "- Be concise and concrete. Prefer 'unknown' over a confident guess. Flag where "
    "the technical signal and the fundamentals/news DISAGREE.\n"
    "- Single stocks are noisy and idiosyncratic; be honest about uncertainty.\n\n"
    "Return ONLY a JSON object (no markdown fences) with keys:\n"
    "  summary: string — one or two sentences, the TL;DR read.\n"
    "  drivers: array of strings — the main things currently driving the stock "
    "(trend, factor tilts, fundamentals, news), each a short phrase.\n"
    "  risks: array of strings — the main risks / what could invalidate the read.\n"
    "  catalysts: array of strings — known upcoming or recent catalysts to watch "
    "(earnings, product, macro sensitivities) that are supported by the context.\n"
    "  confidence: one of \"low\",\"medium\",\"high\"."
)

_BRIEF_LIST_FIELDS = ("drivers", "risks", "catalysts")


def _cfg() -> dict:
    return config.load().get("catalyst_stock", {}) or {}


def enabled() -> bool:
    return bool(_cfg().get("enabled", False))


def safe_name(ticker: str) -> str:
    """Filesystem-safe ticker -> stockdata/stockbrief filename stem. Mirrors the
    transform in scripts/build_stock_library.py so a brief lines up with its
    stockdata/<safe>.json sibling (e.g. GC=F -> GC_F, ^VIX -> _VIX)."""
    return str(ticker).replace("=", "_").replace("^", "_")


# --------------------------------------------------------------------------- #
# context assembly — PUBLIC / DERIVED fields only (no holdings/positions ever)
# --------------------------------------------------------------------------- #
def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:  # noqa: BLE001
        return None


def _num(v):
    """Coerce to a finite float, else None (drops NaN/inf and junk)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _round(v, n=3):
    f = _num(v)
    return round(f, n) if f is not None else None


def _signal_context(sd: dict) -> dict:
    """The deterministic cycle/ladder read + technical state from the nightly
    stockdata JSON — the SAME public analysis the stock page already shows."""
    lad = sd.get("ladder") or {}
    tech = sd.get("tech") or {}
    cyc = sd.get("cycle") or {}
    entry = lad.get("entry") or {}
    return {
        "asof": sd.get("asof"),
        "name": sd.get("name"),
        "sector": sd.get("sector"),
        "ladder_state": lad.get("state"),
        "ladder_label": lad.get("label"),
        "ladder_action": lad.get("action"),
        "summary_line": lad.get("summary_line"),
        "regime_label": lad.get("regime_label"),
        "why": lad.get("why"),
        "points": (lad.get("points") or [])[:6],
        "entry_tag": entry.get("tag"),
        "entry_urgency": entry.get("urgency"),
        "technical": {
            "price": _round(tech.get("price"), 4),
            "above_50dma": tech.get("above50"),
            "above_200dma": tech.get("above200"),
            "pct_vs_50dma": _round(tech.get("pct_vs_50dma"), 1),
            "pct_vs_200dma": _round(tech.get("pct_vs_200dma"), 1),
            "rsi14": _round(tech.get("rsi14"), 1),
            "macd_positive": tech.get("macd_pos"),
            "off_52w_high_pct": _round(tech.get("off_52w_high_pct"), 1),
        },
        "cycle": {
            "daily_phase": cyc.get("dc_phase"),
            "investor_phase": cyc.get("ic_phase"),
            "translation": cyc.get("translation"),
            "failed_cycle": cyc.get("failed_cycle"),
        },
        "seasonality": {"this_month": sd.get("season_this"),
                        "next_month": sd.get("season_next")},
    }


_FACTOR_KEYS = ("value", "profitability", "quality", "accruals", "investment",
                "payout", "low_vol", "low_beta", "short_interest", "composite")


def _factor_context(root: Path, ticker: str) -> dict | None:
    """Cross-sectional factor z-scores for the ticker from the public factors.json
    (built by scripts/build_site.build_factors_page). + is a favourable tilt."""
    site = root / config.load()["storage"].get("site_dir", "site")
    fac = _read_json(site / "factordata" / "factors.json")
    if not isinstance(fac, dict):
        return None
    for row in fac.get("table") or []:
        if str(row.get("ticker")) == ticker:
            out = {}
            for k in _FACTOR_KEYS:
                rv = _round(row.get(k), 3)      # _round drops NaN/inf/junk to None
                if rv is not None:
                    out[k] = rv
            mc = _num(row.get("mktcap_bn"))
            if mc is not None:
                out["mktcap_bn"] = round(mc, 1)
            out["as_of"] = fac.get("as_of")
            return out or None
    return None


def _edgar_context(root: Path, ticker: str) -> dict | None:
    """A few headline SEC-EDGAR fundamentals + simple derived ratios. Public data;
    optional (degrades to None if the parquet is missing or the ticker absent)."""
    p = root / "data" / "edgar" / "fundamentals.parquet"
    if not p.exists():
        return None
    try:
        import pandas as pd
        df = pd.read_parquet(p)
        if ticker not in df.index:
            return None
        r = df.loc[ticker]
        if hasattr(r, "iloc") and getattr(r, "ndim", 1) > 1:   # dup index -> first row
            r = r.iloc[0]
        rev, ni, eq = _num(r.get("revenue")), _num(r.get("ni")), _num(r.get("equity"))
        ni_prior = _num(r.get("ni_prior"))
        out: dict = {}
        if rev is not None:
            out["revenue"] = round(rev, 0)
        if ni is not None:
            out["net_income"] = round(ni, 0)
        if rev and ni is not None:
            out["net_margin_pct"] = round(100 * ni / rev, 1)
        if eq and ni is not None:
            out["roe_pct"] = round(100 * ni / eq, 1)
        if ni_prior and ni is not None:
            out["ni_growth_pct"] = round(100 * (ni / ni_prior - 1), 1)
        for k in ("debt_lt", "cfo", "dividends", "repurchases"):
            v = _num(r.get(k))
            if v is not None:
                out[k] = round(v, 0)
        return out or None
    except Exception as e:  # noqa: BLE001 — fundamentals are optional context
        log.debug("edgar context %s failed: %s", ticker, e)
        return None


def assemble_context(ticker: str, root: Path | None = None) -> dict | None:
    """Assemble ONE ticker's PUBLIC research context from already-stored artifacts.
    Returns None only when there is no usable signal context (no stockdata JSON).

    PRIVACY/FIREWALL: every field here is public or derived-from-public. Holdings,
    positions and watchlist files are never opened. The shape is a fixed whitelist
    so nothing private can leak into the model prompt."""
    root = Path(root) if root else config.ROOT
    site = root / config.load()["storage"].get("site_dir", "site")
    sd = _read_json(site / "stockdata" / f"{safe_name(ticker)}.json")
    if not isinstance(sd, dict) or not sd.get("ladder"):
        return None                         # no deterministic read -> nothing to brief on
    ctx: dict = {
        "ticker": ticker,
        "identity": {"name": sd.get("name"), "sector": sd.get("sector"),
                     "asof": sd.get("asof")},
        "signal": _signal_context(sd),
    }
    fac = _factor_context(root, ticker)
    if fac:
        ctx["factors"] = fac
    fund = _edgar_context(root, ticker)
    if fund:
        ctx["fundamentals"] = fund
    return ctx


# --------------------------------------------------------------------------- #
# news leg — reuse the Tier-A digest WHOLESALE (all five gates apply for free)
# --------------------------------------------------------------------------- #
def _stock_news_query(ticker: str, name: str | None) -> str:
    nm = (name or "").strip()
    base = f'"{nm}"' if nm else ticker
    # bias toward market/finance coverage of THIS company
    return f'({base}) (stock OR shares OR earnings OR results OR analyst OR guidance)'


def _fetch_stock_headlines(ticker: str, name: str | None, cfg: dict) -> list[str]:
    """Recent public headlines about the company from GDELT (free, keyless). Clones
    the catalyst_tone event-headline fetch with a company-specific query. [] on any
    error (the news leg is optional).

    Delegates HTTP, throttling, and retry handling to engine.gdelt_client so
    all GDELT callers share a single cross-process pacing lock (GDELT 5s/IP rule;
    nine callers without shared throttle caused a penalty-box incident 2026-06-20)."""
    from datetime import timedelta
    from engine import gdelt_client as _gc
    today = date.today()
    win = int(cfg.get("news_window_days", 5))
    start = datetime(today.year, today.month, today.day) - timedelta(days=win)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)
    n = int(cfg.get("news_max_records", 8))
    params = {"query": _stock_news_query(ticker, name) + " sourcelang:eng",
              "mode": "artlist", "format": "json", "maxrecords": str(n), "sort": "datedesc",
              "startdatetime": start.strftime("%Y%m%d%H%M%S"),
              "enddatetime": end.strftime("%Y%m%d%H%M%S")}
    try:
        arts, _ = _gc.get_articles(params, timeout=30)
        if not arts:
            return []
        return [a.get("title", "").strip() for a in arts[:n] if a.get("title")]
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("stock headline fetch failed (%s)", e)
        return []


def news_digest(ticker: str, name: str | None, cfg: dict | None = None,
                headlines: list[str] | None = None, *, root=None,
                fabric_cfg=None, asof=None) -> dict | None:
    """Digest recent public headlines about the company into the Tier-A tone record
    (reusing catalyst_tone.digest_document, so the citation-verify + confidence-floor
    gates apply). Returns None when the news leg is disabled, no headlines are found,
    or the Tier-A digest switch (catalyst_tone.enabled) is off. NEVER raises."""
    cfg = cfg or _cfg()
    if not cfg.get("news_enabled", True):
        return None
    try:
        from engine import catalyst_tone
        heads = headlines if headlines is not None else _fetch_stock_headlines(ticker, name, cfg)
        if not heads:
            return None
        text = (f"Recent news headlines about {name or ticker} ({ticker}):\n"
                + "\n".join(f"- {h}" for h in heads))
        stamp = asof if asof is not None else date.today().isoformat()
        source_key = _tone._cache_hash(ticker) if fabric_cfg is not None else safe_name(ticker)
        rec = catalyst_tone.digest_document(
            text, kind="stock_news", doc_id=f"stocknews_{source_key}_{stamp}",
            context=f"recent news for {name or ticker} ({ticker})", asof=stamp,
            root=root, fabric_cfg=fabric_cfg)
        if rec is None:                     # Tier-A digest disabled -> no news leg
            return None
        # keep only the compact, model-facing fields (drop the heavy disclaimer)
        result = {k: rec.get(k) for k in (
            "tone_score", "guidance_direction", "risk_delta", "confidence",
            "confidence_gated", "evidence", "degraded_reason")}
        if fabric_cfg is not None or "fabric" in rec:
            result["fabric"] = rec.get("fabric")
        return result
    except Exception as e:  # noqa: BLE001 — news is optional context
        log.warning("stock news_digest failed (%s)", e)
        return {"degraded_reason": "fabric_news_unavailable", "fabric": None} if fabric_cfg is not None else None


# --------------------------------------------------------------------------- #
# the reasoning call (DeepSeek V4 Pro via the Anthropic-compatible endpoint)
# --------------------------------------------------------------------------- #
def _call_model(system: str, user: str, cfg: dict) -> tuple[str | None, str | None]:
    """Return (reply_text, degraded_reason). Mirrors master_brain._call_model and
    reuses catalyst_tone._client. Never raises."""
    from engine import llm_auth
    try:
        if llm_auth.application_mode_id(cfg) is not None:
            return None, "fabric_document_owner_required"
    except Exception:
        return None, "fabric_selection_refused"
    client = _client(cfg)
    if client is None:
        return None, "no_client_or_key"
    try:
        resp = client.messages.create(
            model=cfg.get("llm_model", "deepseek-v4-pro"),
            max_tokens=int(cfg.get("max_tokens", 2000)),
            system=system,
            messages=[{"role": "user", "content": user}])
        sr = getattr(resp, "stop_reason", None)
        if sr == "refusal":
            return None, "stop_refusal"
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if not text:
            return None, "empty_reply"
        return text, ("truncated" if sr == "max_tokens" else None)
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("catalyst_stock model call failed (%s)", e)
        return None, "llm_error"


def _clean_str(v) -> str | None:
    if not isinstance(v, (str, int, float)):
        return None
    s = str(v).strip()
    return s[:_MAX_STR] if s else None


def _clean_list(v) -> list[str]:
    if not isinstance(v, list):
        return []
    out = []
    for item in v:
        s = _clean_str(item)
        if s:
            out.append(s)
        if len(out) >= _MAX_ITEMS:
            break
    return out


def _validate_brief(parsed: dict) -> dict:
    """Coerce a parsed reply into the canonical brief shape — lists of clean strings,
    enum-checked confidence. Mirrors the catalyst_tone validator's spirit (no field
    can carry a surprising type into the JSON the page renders)."""
    conf = str(parsed.get("confidence", "")).strip().lower()
    return {
        "summary": _clean_str(parsed.get("summary")),
        "drivers": _clean_list(parsed.get("drivers")),
        "risks": _clean_list(parsed.get("risks")),
        "catalysts": _clean_list(parsed.get("catalysts")),
        "confidence": conf if conf in _CONF else "low",
    }


# --------------------------------------------------------------------------- #
# public: brief for one ticker
# --------------------------------------------------------------------------- #
_ZH_SCALARS = ("summary",)
_ZH_LISTS = ("drivers", "risks", "catalysts")


def _stock_path(root, cfg, ticker):
    if type(ticker) is not str or not ticker.strip() or len(ticker.encode()) > 512:
        raise ValueError("fabric_stock_ticker_invalid")
    directory = Path(root) / cfg.get("brief_cache_dir", "data/catalyst/stockbrief_cache")
    return directory / ("fabric-stock-" + _tone._cache_hash(ticker) + ".json")


def _stock_state(path, ticker):
    value = _tone._cache_read(path)
    if value is None:
        return {"schema": "macro.stockbrief_fabric_cache.v1", "ticker": ticker, "entries": []}
    if (type(value) is not dict or set(value) != {"schema", "ticker", "entries"}
            or value["schema"] != "macro.stockbrief_fabric_cache.v1" or value["ticker"] != ticker
            or type(value["entries"]) is not list or len(value["entries"]) > 64):
        raise ValueError("fabric_stock_cache_invalid")
    seen = set()
    fields = {"input", "input_digest", "mode_id", "inspection", "state", "news", "english",
              "translation", "record", "record_digest"}
    for row in value["entries"]:
        if (type(row) is not dict or set(row) != fields or type(row["input"]) is not dict
                or row["input_digest"] != _tone._cache_hash(row["input"])
                or row["input_digest"] in seen or type(row["mode_id"]) is not str
                or type(row["inspection"]) is not dict or row["state"] not in ("pending", "held", "terminal")
                or type(row["record"]) is not dict or row["record_digest"] != _tone._cache_hash(row["record"])
                or row["record"].get("ticker") != ticker or row["record"].get("is_context_only") is not True
                or row["news"] is not None and type(row["news"]) is not dict):
            raise ValueError("fabric_stock_cache_invalid")
        if row["english"] is not None:
            cache = _tone._fabric_cache_value(row["english"], _stock_logical(ticker, row["input_digest"]))
            if len(cache["entries"]) != 1 or cache["entries"][0]["inspection"] != row["inspection"]:
                raise ValueError("fabric_stock_english_invalid")
            if row["state"] == "terminal" and cache["entries"][0]["state"] != "terminal":
                raise ValueError("fabric_stock_original_held")
        elif row["state"] == "terminal":
            raise ValueError("fabric_stock_terminal_without_english")
        news = row["news"]
        if news is not None:
            if (set(news) != {"headlines", "asof", "document_id", "state", "result"}
                    or type(news["headlines"]) is not list
                    or any(type(headline) is not str for headline in news["headlines"])
                    or news["asof"] != row["input"].get("day")
                    or news["document_id"] != "stocknews_" + _tone._cache_hash(ticker) + "_" + news["asof"]
                    or news["state"] not in ("pending", "held", "terminal", "not_dispatched")
                    or news["result"] is not None and type(news["result"]) is not dict
                    or news["state"] in ("pending", "not_dispatched") and news["result"] is not None
                    or news["state"] in ("terminal", "held") and news["result"] is None
                    or row["state"] == "terminal" and news["state"] not in ("terminal", "not_dispatched")):
                raise ValueError("fabric_stock_news_invalid")
            if news["state"] == "terminal":
                receipt = news["result"].get("fabric")
                if (type(receipt) is not dict or receipt.get("effect_unknown") is not False
                        or type(receipt.get("close")) is not dict
                        or receipt["close"].get("effect_unknown") is not False
                        or receipt["close"].get("disposition") in (None, "pending", "effect_unknown")):
                    raise ValueError("fabric_stock_news_unsettled")
        leg = row["translation"]
        if leg is not None:
            if (type(leg) is not dict or set(leg) != {"operation_id", "inspection", "input", "input_digest",
                    "state", "output", "served_model", "usage", "close", "effect_unknown"}
                    or type(leg["operation_id"]) is not str
                    or re.fullmatch(r"translate-profiles:[0-9a-f]{32}", leg["operation_id"]) is None
                    or type(leg["inspection"]) is not dict or type(leg["input"]) is not dict
                    or leg["input_digest"] != _tone._cache_hash(leg["input"])
                    or leg["state"] not in ("pending", "output_observed", "output_unavailable")
                    or any(leg[k] is not None for k in ("served_model", "usage", "close"))
                    or leg["effect_unknown"] is not True or row["state"] == "terminal"
                    or leg["output"] is not None and (type(leg["output"]) is not list
                        or len(leg["output"]) != len(leg["input"].get("texts", []))
                        or any(v is not None and type(v) is not str for v in leg["output"]))):
                raise ValueError("fabric_stock_translation_invalid")
        seen.add(row["input_digest"])
    if sum(r["state"] != "terminal" for r in value["entries"]) > 1:
        raise ValueError("fabric_stock_cache_invalid")
    return value


def _stock_logical(ticker, digest):
    return {"task": "catalyst-stock", "ticker": ticker, "input_digest": digest}


def _stock_commit(path, root, ticker, digest, change):
    with _tone._cache_lock(path, root):
        document = _stock_state(path, ticker)
        row = next(r for r in document["entries"] if r["input_digest"] == digest)
        if row["state"] != "pending":
            raise ValueError("fabric_stock_original_changed")
        change(row)
        row["record_digest"] = _tone._cache_hash(row["record"])
        _tone._cache_save(path, document)


def _stock_held(row):
    result = copy.deepcopy(row["record"])
    # Recover a durably validated English answer after a lost outer save. This
    # is local delivery only; an interrupted later stage is never restarted.
    cache = row["english"]
    if cache and cache["entries"][0]["result"] is not None:
        english = cache["entries"][0]
        if _stock_validate(english["text"]) != english["result"]:
            raise ValueError("fabric_stock_result_invalid")
        result.update(english["result"], model=english["receipt"]["served_model"],
                      fabric=english["receipt"])
    result["degraded_reason"] = "fabric_original_held"
    return result


def _stock_validate(text):
    parsed = _extract_json(text)
    if type(parsed) is not dict:
        raise ValueError("fabric_stock_reply_invalid")
    result = _validate_brief(parsed)
    if not result["summary"] and not any(result[k] for k in _BRIEF_LIST_FIELDS):
        raise ValueError("fabric_stock_reply_empty")
    return result


def _stock_prompt(context):
    return ("One stock's PUBLIC research context (JSON). Write the brief per your "
            "instructions. Context only — no holdings or positions are included.\n"
            "<context>\n" + json.dumps(context, indent=2, default=str) + "\n</context>")


def _stock_translation_input(brief):
    texts, layout = [], []
    for key in _ZH_SCALARS:
        value = brief.get(key)
        if isinstance(value, str) and value.strip():
            texts.append(value)
            layout.append([key, None])
    for key in _ZH_LISTS:
        for index, value in enumerate(brief.get(key) or []):
            if isinstance(value, str) and value.strip():
                texts.append(value)
                layout.append([key, index])
    return texts, layout


def _stock_attach_translation(brief, layout, output):
    if not output or all(v is None for v in output):
        return
    translated = {"summary": None, **{key: [None] * len(brief.get(key) or []) for key in _ZH_LISTS}}
    for (key, index), text in zip(layout, output):
        if text is not None:
            if index is None:
                translated[key] = text
            else:
                translated[key][index] = text
    brief["zh"] = translated


def _stock_translate_selected(path, root, ticker, digest, cfg, mode_id, record):
    from engine import translate as translator, llm_auth
    if not cfg.get("translate_zh", True):
        return False
    texts, layout = _stock_translation_input(record)
    if not texts:
        return False
    # The approved translator seam has no root argument. Do not retarget its
    # global configuration or bind against another caller's authority.
    if Path(root).resolve(strict=True) != Path(translator.config.ROOT).resolve(strict=True):
        record["translation_error"] = "fabric_translation_root_mismatch"
        return False
    tcfg = {"enabled": True, "max_chars": 1500, "max_tokens": 3000, "batch_size": 24,
            **{k: cfg[k] for k in ("application_fabric_mode", "workload_profile", "usage_sink") if k in cfg}}
    tcfg.setdefault("workload_profile", "site_batch")
    if llm_auth.application_mode_id(tcfg) != mode_id:
        record["translation_error"] = "fabric_selection_changed"
        return False
    factory = translator._fabric_factory(tcfg, mode_id)
    if factory is None:
        record["translation_error"] = "fabric_translation_unavailable"
        return False
    inspection = factory.inspect(tcfg)
    payload = {"texts": texts, "layout": layout, "max_chars": 1500, "max_tokens": 3000,
               "batch_size": 24, "system": translator._SYSTEM}
    leg = {"operation_id": "translate-profiles:" + secrets.token_hex(16), "inspection": inspection,
           "input": payload, "input_digest": _tone._cache_hash(payload), "state": "pending", "output": None,
           "served_model": None, "usage": None, "close": None, "effect_unknown": True}
    def claim(row):
        if row["translation"] is not None:
            raise ValueError("fabric_stock_translation_claimed")
        row["translation"] = leg
        row["record"] = copy.deepcopy(record)
    _stock_commit(path, root, ticker, digest, claim)
    # Original ID and full inspection are committed before any translator bind.
    # The list API exposes output only; neither full nor partial output is a
    # receipt for upstream settlement. Keep this original leg held thereafter.
    try:
        output = translator.translate_to_zh(texts, tcfg, fabric_operation_id=leg["operation_id"],
                                             fabric_inspection=inspection)
    except Exception:
        output = None
    if (type(output) is not list or len(output) != len(texts)
            or any(v is not None and (type(v) is not str or not v.strip()) for v in output)):
        output = None
    leg.update(output=output, state="output_observed" if output and any(output) else "output_unavailable")
    _stock_attach_translation(record, layout, output)
    record["translation"] = {k: copy.deepcopy(leg[k]) for k in
        ("operation_id", "state", "served_model", "usage", "close", "effect_unknown")}
    record["translation_error"] = "fabric_translation_settlement_unobserved"
    def save_output(row):
        original = row["translation"]
        if original["operation_id"] != leg["operation_id"] or original["input_digest"] != leg["input_digest"]:
            raise ValueError("fabric_stock_translation_changed")
        row["translation"] = leg
        row["record"] = copy.deepcopy(record)
        row["state"] = "held"
    _stock_commit(path, root, ticker, digest, save_output)
    return True


def _stock_selected(ticker, root, cfg, include_news, record):
    """The existing per-ticker cache owns the three deliberate brief stages."""
    from engine import llm_auth
    from engine.provider_production_modes import make_application_fabric_factory
    root = Path(root).resolve(strict=True)
    path = _stock_path(root, cfg, ticker)
    if os.path.lexists(path):
        with _tone._cache_lock(path, root):
            state = _stock_state(path, ticker)
            held = next((r for r in state["entries"] if r["state"] != "terminal"), None)
            if held is not None:
                return _stock_held(held)
    mode_id = llm_auth.application_mode_id(cfg)
    if mode_id is None:
        return None
    record.update(requested_model=record["model"], model=None)
    context = assemble_context(ticker, root)
    if context is None:
        record["degraded_reason"] = "no_context"
        return record
    record["name"] = (context.get("identity") or {}).get("name")
    record["asof"] = (context.get("identity") or {}).get("asof")
    actual_cfg = {"max_tokens": 2000, **cfg, "provider_order": ["fabric"], "usage_lane": "catalyst-stock"}
    actual_cfg.setdefault("workload_profile", "site_batch")
    bound = actual_cfg["max_tokens"]
    if type(bound) is not int or not 1 <= bound <= 32768:
        raise ValueError("fabric_stock_bound_invalid")
    factory = make_application_fabric_factory(mode_id=mode_id, lane="catalyst-stock", root=root,
                                              workload_cfg={**actual_cfg, "workload_profile": "site_batch"})
    inspection = factory.inspect(actual_cfg)
    inputs = {"day": date.today().isoformat(), "context": context, "include_news": bool(include_news),
              "system": STOCK_SYSTEM, "max_tokens": bound,
              "news_enabled": bool(cfg.get("news_enabled", True)),
              "news_window_days": cfg.get("news_window_days", 5),
              "news_max_records": cfg.get("news_max_records", 8),
              "translate_zh": bool(cfg.get("translate_zh", True))}
    digest = _tone._cache_hash(inputs)
    with _tone._cache_lock(path, root):
        state = _stock_state(path, ticker)
        held = next((r for r in state["entries"] if r["state"] != "terminal"), None)
        if held is not None:
            return _stock_held(held)
        prior = next((r for r in state["entries"] if r["input_digest"] == digest), None)
        if prior is not None:
            if prior["inspection"] != inspection or prior["mode_id"] != mode_id:
                raise ValueError("fabric_stock_identity_changed")
            if prior["english"] and prior["english"]["entries"][0]["result"] is not None:
                english = prior["english"]["entries"][0]
                if _stock_validate(english["text"]) != english["result"]:
                    raise ValueError("fabric_stock_result_invalid")
            return copy.deepcopy(prior["record"])
        if len(state["entries"]) >= 64:
            raise ValueError("fabric_stock_cache_bound")
        state["entries"].append({"input": inputs, "input_digest": digest, "mode_id": mode_id,
            "inspection": inspection, "state": "pending", "news": None, "english": None,
            "translation": None, "record": copy.deepcopy(record), "record_digest": _tone._cache_hash(record)})
        _tone._cache_save(path, state)
    # No network or credential work runs while the per-ticker lock is held.
    if include_news:
        if llm_auth.application_mode_id(actual_cfg) != mode_id:
            raise ValueError("fabric_stock_selection_changed")
        news_cfg = {k: actual_cfg[k] for k in ("application_fabric_mode", "workload_profile", "usage_sink")
                    if k in actual_cfg}
        news_cfg.setdefault("application_fabric_mode", mode_id)
        heads = (_fetch_stock_headlines(ticker, record["name"], actual_cfg)
                 if actual_cfg.get("news_enabled", True) and _tone.enabled() else [])
        snapshot = {"headlines": heads, "asof": inputs["day"],
                    "document_id": "stocknews_" + _tone._cache_hash(ticker) + "_" + inputs["day"],
                    "state": "pending", "result": None}
        def claim_news(row):
            row["news"] = snapshot
        _stock_commit(path, root, ticker, digest, claim_news)
        news = news_digest(ticker, record["name"], actual_cfg, headlines=heads,
                           root=root, fabric_cfg=news_cfg, asof=inputs["day"])
        if news is not None:
            receipt = news.get("fabric")
            uncertain = not isinstance(receipt, dict) or receipt.get("effect_unknown") is not False
            public_news = {k: v for k, v in news.items() if k != "fabric"}
            record["news"] = public_news
            record["news_fabric"] = receipt
            if uncertain:
                record["degraded_reason"] = "fabric_news_original_held"
            def save_news(row):
                row["news"] = {**snapshot, "state": "held" if uncertain else "terminal", "result": news}
                row["record"] = copy.deepcopy(record)
                if uncertain:
                    row["state"] = "held"
            _stock_commit(path, root, ticker, digest, save_news)
            if uncertain:
                return record
            context = {**context, "news": public_news}
        else:
            def skip_news(row):
                row["news"] = {**snapshot, "state": "not_dispatched", "result": None}
            _stock_commit(path, root, ticker, digest, skip_news)
    logical = _stock_logical(ticker, digest)
    def load_english():
        document = _stock_state(path, ticker)
        row = next(r for r in document["entries"] if r["input_digest"] == digest)
        if row["state"] != "pending":
            raise ValueError("fabric_stock_original_changed")
        return row["english"]
    def store_english(cache):
        if len(cache["entries"]) != 1 or cache["entries"][0]["inspection"] != inspection:
            raise ValueError("fabric_stock_english_changed")
        document = _stock_state(path, ticker)
        row = next(r for r in document["entries"] if r["input_digest"] == digest)
        if row["state"] != "pending":
            raise ValueError("fabric_stock_original_changed")
        if row["english"] is not None and any(row["english"]["entries"][0][key] != cache["entries"][0][key]
                for key in ("operation_id", "input_digest")):
            raise ValueError("fabric_stock_english_claimed")
        row["english"] = cache
        _tone._cache_save(path, document)
    english = _tone._fabric_cached_document(path=path, root=root, logical_source=logical,
        cfg=actual_cfg, lane="catalyst-stock", system=STOCK_SYSTEM, user=_stock_prompt(context),
        input_context=inputs, validate=_stock_validate, load_cache=load_english, store_cache=store_english,
        allow_truncated=True)
    receipt = english["receipt"] if english is not None else None
    record["fabric"] = receipt
    record["model"] = receipt.get("served_model") if receipt else None
    if english and english["result"] is not None:
        record.update(english["result"])
    record["degraded_reason"] = english["error"] if english else "fabric_selection_changed"
    uncertain = not isinstance(receipt, dict) or receipt.get("effect_unknown") is not False
    def save_english(row):
        row["record"] = copy.deepcopy(record)
        if uncertain:
            row["state"] = "held"
    _stock_commit(path, root, ticker, digest, save_english)
    if uncertain:
        return record
    if english["result"] is not None:
        try:
            if _stock_translate_selected(path, root, ticker, digest, actual_cfg, mode_id, record):
                return record
        except Exception:
            # A failed preflight is no call. A visible Chinese claim is retained
            # as an unresolved original, including a lost write acknowledgement.
            with _tone._cache_lock(path, root):
                current = next(r for r in _stock_state(path, ticker)["entries"] if r["input_digest"] == digest)
                if current["translation"] is not None:
                    return _stock_held(current)
            record["translation_error"] = "fabric_translation_unavailable"
    def finish(row):
        row["record"] = copy.deepcopy(record)
        row["state"] = "terminal"
    _stock_commit(path, root, ticker, digest, finish)
    return record


def _translate_brief(brief: dict, cfg: dict) -> None:
    """Attach a Chinese version (brief['zh']) via the shared DeepSeek translator so the
    #stock-brief panel can show the read under the 中文 toggle. Cheap V4-Flash pass;
    degrade-never-raise with per-field English fallback. (Mirrors master_brain._translate_brief.)"""
    if not cfg.get("translate_zh", True):
        return
    try:
        from engine import translate as _tr
        texts: list[str] = []
        layout: list[tuple[str, int | None]] = []
        for k in _ZH_SCALARS:
            v = brief.get(k)
            if isinstance(v, str) and v.strip():
                layout.append((k, None)); texts.append(v)
        for k in _ZH_LISTS:
            for i, v in enumerate(brief.get(k) or []):
                if isinstance(v, str) and v.strip():
                    layout.append((k, i)); texts.append(v)
        if not texts:
            return
        tcfg = {
            "enabled": True,
            "base_url": cfg.get("llm_base_url", "https://api.deepseek.com/anthropic"),
            "api_key_env": cfg.get("api_key_env", "DEEPSEEK_API_KEY"),
            "model": cfg.get("translate_model", "deepseek-v4-flash"),
            "max_chars": 1500, "max_tokens": 3000, "batch_size": 24,
        }
        zh_list = _tr.translate_to_zh(texts, tcfg)
        if not zh_list or all(x is None for x in zh_list):
            return
        zh: dict = {"summary": None,
                    "drivers": [None] * len(brief.get("drivers") or []),
                    "risks": [None] * len(brief.get("risks") or []),
                    "catalysts": [None] * len(brief.get("catalysts") or [])}
        for (k, i), t in zip(layout, zh_list):
            if t is None:
                continue
            if i is None:
                zh[k] = t
            else:
                zh[k][i] = t
        brief["zh"] = zh
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("catalyst_stock zh translation failed (%s)", e)


def brief_for_ticker(ticker: str, root: Path | None = None,
                     include_news: bool = True) -> dict | None:
    """Assemble PUBLIC context -> optional Flash news digest -> Pro reasoning brief.
    Returns None when the master switch is off; otherwise ALWAYS returns a record
    (degraded fields flagged). NEVER raises into the pipeline."""
    return _brief_for_ticker(ticker, dict(_cfg()), root, include_news)


def _brief_for_ticker(ticker, cfg, root=None, include_news=True):
    """Private configuration snapshot; threaded force never mutates `_cfg`."""
    if not cfg.get("enabled", False):
        return None

    rec = {
        "schema": "catalyst_stock.v1",
        "is_context_only": True,
        "ticker": ticker,
        "name": None,
        "asof": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": cfg.get("llm_model", "deepseek-v4-pro"),
        "summary": None, "drivers": [], "risks": [], "catalysts": [],
        "confidence": "low",
        "news": None,
        "degraded_reason": None,
        "disclaimer": DISCLAIMER_TEXT,
    }
    try:
        root = Path(root) if root else config.ROOT
        selected = _stock_selected(ticker, root, cfg, include_news, rec)
        if selected is not None:
            return selected
        ctx = assemble_context(ticker, root)
        if ctx is None:
            rec["degraded_reason"] = "no_context"
            return rec
        rec["name"] = (ctx.get("identity") or {}).get("name")
        rec["asof"] = (ctx.get("identity") or {}).get("asof")

        if include_news:
            news = news_digest(ticker, rec["name"], cfg)
            if news:
                ctx["news"] = news
                rec["news"] = news

        user = _stock_prompt(ctx)
        reply, reason = _call_model(STOCK_SYSTEM, user, cfg)
        if reply is None:
            rec["degraded_reason"] = reason
            return rec
        parsed = _extract_json(reply)
        if not isinstance(parsed, dict):
            rec["degraded_reason"] = reason or "unparseable_reply"
            return rec
        rec.update(_validate_brief(parsed))
        _translate_brief(rec, cfg)          # attach rec['zh'] for the 中文 toggle
        if reason:                          # parsed, but flag e.g. truncation
            rec["degraded_reason"] = reason
        return rec
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("brief_for_ticker(%s) failed (%s)", ticker, e)
        if _stock_owns(ticker, root, cfg):
            rec["degraded_reason"] = "fabric_stock_refused"
            rec.setdefault("requested_model", rec["model"])
            receipt = rec.get("fabric")
            rec["model"] = receipt.get("served_model") if isinstance(receipt, dict) else None
        else:
            rec["degraded_reason"] = "internal_error"
        return rec


# --------------------------------------------------------------------------- #
# static-site precompute — write site/stockbrief/<TICKER>.json for a small set,
# cached per ticker per day to cap cost. Called from scripts/build_site.main().
# --------------------------------------------------------------------------- #
def _cache_path(root: Path, cfg: dict, safe: str, day: str) -> Path:
    cdir = root / cfg.get("brief_cache_dir", "data/catalyst/stockbrief_cache")
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir / f"{safe}_{day}.json"


def _stock_owns(ticker, root, cfg):
    from engine import llm_auth
    try:
        return os.path.lexists(_stock_path(root, cfg, ticker)) or llm_auth.application_mode_id(cfg) is not None
    except Exception:
        return True


def _brief_workers() -> int:
    """Thread-pool size for the per-ticker brief LLM calls (I/O-bound on DeepSeek).
    Precedence: STOCK_BRIEF_WORKERS env (1 = force serial) > config
    catalyst_stock.brief_workers > 6. Capped at 12 to stay polite to the rate limit."""
    n = os.environ.get("STOCK_BRIEF_WORKERS") or _cfg().get("brief_workers")
    if n is None:
        n = 6
    return max(1, min(int(n), 12))


def precompute_briefs(tickers, root: Path | None = None, site: Path | None = None,
                      force: bool = False) -> list[dict]:
    """Precompute briefs for `tickers` -> site/stockbrief/<safe>.json. De-dups,
    caps to config `precompute_max`, and caches a successful brief per ticker per
    day (so repeated builds the same day don't re-spend). Returns a list of
    {ticker, degraded_reason}. Returns [] when disabled (unless force). NEVER raises."""
    cfg = dict(_cfg())
    if not force and not cfg.get("enabled", False):
        return []
    if force:
        cfg["enabled"] = True
    try:
        root = Path(root) if root else config.ROOT
        site = Path(site) if site else (root / config.load()["storage"].get("site_dir", "site"))
        outdir = site / "stockbrief"
        outdir.mkdir(parents=True, exist_ok=True)
        day = date.today().isoformat()
        cap = int(cfg.get("precompute_max", 30))
        seen: set[str] = set()
        written: list[dict] = []
        dropped = 0
        # 1) de-dup + apply the cap up front to get the bounded work list, in order.
        work: list[str] = []
        for t in tickers or []:
            if not t or t in seen:
                continue
            seen.add(t)
            if len(work) >= cap:
                dropped += 1
                continue
            work.append(t)

        # 2) resolve each ticker. A daily cache hit is free; a miss is a DeepSeek
        # reasoning call (~30-60s). Those calls are independent, thread-safe (each
        # builds its own record, never raises) and I/O-bound, so fan them across a
        # small thread pool — the rest stays serial. This is the build's last big
        # serial stretch after factor-series + the stock library were parallelised.
        def _resolve(t: str):
            safe = safe_name(t)
            if _stock_owns(t, root, cfg):
                return t, safe, None, _brief_for_ticker(t, cfg, root), False
            cache = _cache_path(root, cfg, safe, day)
            if cache.exists():
                rec = _read_json(cache)
                if rec is not None:
                    return t, safe, cache, rec, False    # cached -> don't re-write cache
            result = _brief_for_ticker(t, cfg, root) if force else brief_for_ticker(t, root=root)
            return t, safe, cache, result, True

        workers = _brief_workers()
        if workers > 1 and len(work) > 1:
            from concurrent.futures import ThreadPoolExecutor
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=workers) as ex:
                resolved = list(ex.map(_resolve, work))
            log.info("stock briefs: resolved %d ticker(s) in %.0fs (%d threads)",
                     len(work), time.time() - t0, workers)
        else:
            resolved = [_resolve(t) for t in work]

        # 3) serial: cache + write the per-ticker JSONs, preserving input order.
        for t, safe, cache, rec, fresh in resolved:
            if rec is None:                  # master switch flipped off mid-run (force path)
                continue
            if fresh and rec.get("degraded_reason") is None:   # only cache a usable brief
                try:
                    cache.write_text(json.dumps(rec, default=str))
                except Exception:  # noqa: BLE001
                    pass
            try:
                (outdir / f"{safe}.json").write_text(json.dumps(rec, default=str))
                written.append({"ticker": t, "degraded_reason": rec.get("degraded_reason")})
            except Exception as e:  # noqa: BLE001
                log.warning("write stockbrief %s failed (%s)", safe, e)
        if dropped:
            log.info("stock-brief precompute capped at %d; %d ticker(s) dropped", cap, dropped)
        return written
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.error("precompute_briefs failed (%s)", e)
        return []


def render_markdown(brief: dict) -> str:
    """Human-readable rendering of a brief (for the CLI)."""
    if not brief:
        return "_no brief_"
    if brief.get("degraded_reason") and not brief.get("summary") and not brief.get("drivers"):
        return f"_stock brief unavailable: {brief['degraded_reason']}_"
    L = [f"# {brief.get('name') or brief.get('ticker')} ({brief.get('ticker')}) — "
         f"AI brief ({brief.get('model', '?')})", ""]
    if brief.get("summary"):
        L += [f"**{brief['summary']}**", ""]
    for title, key in (("Drivers", "drivers"), ("Risks", "risks"), ("Catalysts", "catalysts")):
        if brief.get(key):
            L += [f"## {title}", *[f"- {x}" for x in brief[key]], ""]
    L += [f"_confidence: {brief.get('confidence', '?')} · context only, not a signal_"]
    return "\n".join(L)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tk = args[0] if args else "AAPL"
    if force:
        # ad-hoc single-ticker run even when disabled (for live verification)
        b = _brief_for_ticker(tk, {**_cfg(), "enabled": True})
    else:
        b = brief_for_ticker(tk)
    if b is None:
        print("catalyst_stock disabled — set catalyst_stock.enabled: true, or pass --force")
    else:
        print(render_markdown(b))
        if b.get("degraded_reason"):
            print(f"\n[degraded: {b['degraded_reason']}]")
