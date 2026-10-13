"""Render the Global Market Cycles page (templates/markets.html.j2 -> site/markets.html).

W3.5 addition: emit site/marketsdata/markets_engine.js (window.MARKETS_ENGINE) by
mapping each of the 10 curated markets to its engine record in
site/countrycyclesdata/country_cycles.json.  The hand-curated markets_data.js STAYS
as the overlay source (turning-point history, valuations, prose) — it no longer drives
plotted cycle positions.  The engine's pos_v2 / phase_v2 / turns / proj / overdue /
basis fields become the authoritative plotted values.

Markets without a country_cycles record (US and Europe — SPY / VGK are not in the
country engine yet) get a null engine record so markets_app.js can gracefully fall
back to rendering the curated position clearly flagged as OPINION.

Sibling of build_cycle.py: a bespoke cycle-family dashboard (ten national equity
markets on one clock) whose data, logic and styles live as committed site/ assets —
markets_data.js (the curated dataset), markets_app.js (synthesis + UI), markets_i18n.js
(bilingual copy), cycle.css (the shared cycle design system) and mm_charts.js (the
dependency-free SVG charting engine). The browser loads those directly; this builder
re-renders the HTML shell and emits markets_engine.js.
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402

log = logging.getLogger(__name__)

# committed page assets (kept in site/); copied from templates/ only if a future
# refactor moves the canonical copy there — otherwise these are graceful no-ops.
PAGE_ASSETS = ("cycle.css", "mm_charts.js", "markets_i18n.js", "markets_data.js", "markets_app.js")

# Map markets.html market-id → country_cycles ETF ticker (lowercase).
# None = market not yet in the country engine; engine record will be null.
MARKET_TO_ENGINE: dict[str, str | None] = {
    "us":      None,   # SPY not in country_cycles yet
    "uk":      "ewu",
    "japan":   "ewj",
    "hk":      "ewh",
    "canada":  "ewc",
    "china":   "fxi",
    "india":   "inda",
    "taiwan":  "ewt",
    "korea":   "ewy",
    "australia": "ewa",
    "europe":  None,   # VGK not in country_cycles yet
}

# country_cycles.html anchor IDs that correspond to each market (for cross-links).
MARKET_TO_CC_ANCHOR: dict[str, str | None] = {
    "us":      None,
    "uk":      "ewu",
    "japan":   "ewj",
    "hk":      "ewh",
    "canada":  "ewc",
    "china":   "fxi",
    "india":   "inda",
    "taiwan":  "ewt",
    "korea":   "ewy",
    "australia": "ewa",
    "europe":  None,
}


def _load_country_cycles(site: Path) -> dict[str, dict]:
    """Return a dict keyed by ETF ticker from site/countrycyclesdata/country_cycles.json."""
    cc_path = site / "countrycyclesdata" / "country_cycles.json"
    if not cc_path.exists():
        log.warning("country_cycles.json not found at %s — engine records will be null", cc_path)
        return {}
    with cc_path.open(encoding="utf-8") as f:
        cc = json.load(f)
    return {s["id"]: s for s in cc.get("sectors", [])}


def _extract_engine_record(sector: dict) -> dict:
    """Extract only the fields markets_app.js needs from a country_cycles sector record.

    W3.9 basis decision: markets.html is the US-investor allocation surface (SPY-relative,
    "what did owning this market do for a dollar holder") — so it consumes the **USD-ETF**
    cycle, NOT the new local-currency primary.  When a country record carries a nested
    `usd_record` (W3.9 FX decomposition), read THAT: it keeps markets on the `price` tape,
    so the cross-page consistency checker sees country_cycles' usd_record and markets agree
    on the same (ticker, price) identity, while the local record differs under a declared
    `local_native`/`local_synth` label.  Pre-W3.9 records (no usd_record) read the top level
    unchanged."""
    src = sector.get("usd_record") or sector
    now = src.get("now", {})
    proj = src.get("proj", {})
    turns = src.get("turns", [])

    # Confirmed turns: pull the last 6 major turns so the spark/history overlay works.
    major_turns = [t for t in turns if t.get("major", True)][-8:]

    return {
        "id":              sector.get("id"),
        "ticker":          sector.get("ticker"),
        "name":            sector.get("name"),
        # basis from the USD source record (W3.9: the usd_record's "price", or the pre-W3.9
        # top-level basis) — this is what the cross-page checker keys markets on.
        "basis":           src.get("basis") or sector.get("basis"),
        "epoch":           sector.get("epoch"),  # may be None
        # ---- engine position (pos_v2 semantics, 0-100 oscillator) ----
        "pos_v2":          now.get("pos_v2"),
        "phase_v2":        now.get("phase_v2") or now.get("phase"),
        "phase_label":     now.get("phaseLabel"),
        # ---- signal / stance ----
        "signal":          now.get("signal"),
        "stance":          now.get("stance"),
        "tone":            now.get("tone"),
        "divergence":      now.get("divergence"),
        # ---- timing ----
        "lastPeak":        now.get("lastPeak"),
        "lastTrough":      now.get("lastTrough"),
        "osc_slope":       now.get("osc_slope"),
        # ---- projection (engine-computed, not hand-typed) ----
        "proj_nextTurn":   proj.get("nextTurn"),
        "proj_central":    proj.get("central"),
        "proj_low":        proj.get("low"),
        "proj_high":       proj.get("high"),
        "overdue":         proj.get("overdue"),
        "overdue_frac":    proj.get("overdue_frac"),
        "last_confirmed_t": proj.get("last_confirmed_t"),
        "period_yrs":      proj.get("period_yrs"),
        # ---- confirmed turns (for spark/chart overlay) ----
        "turns":           major_turns,
        # ---- RS ranking ----
        "rs_rank":         now.get("rs_rank"),
        "rs_63d":          now.get("rs_63d"),
        "rs_126d":         now.get("rs_126d"),
    }


def _regime_disagreement(markets_data_js: Path) -> dict | None:
    """W4.5 — compare curated market ``regime_claim`` fields against the live engine quad.

    Parses ``markets_data.js`` with the shared JS-literal parser (``scripts._cycle_seed``),
    builds narratives (every market that carries a claim + the MARKET_META.regime block as a
    synthetic "meta" narrative — which leans Q2/omit, so it opts out by default), and defers
    to ``regime_prior.disagreement_block``.  Additive + non-fatal: any failure yields None
    (no banner), never a build failure (doctrine #7).

    Note: only ``us`` (judgment call) and ``hk`` (Fed-premised via USD peg) carry a US-quad
    claim.  Every other market conditions on its LOCAL central bank, so a US-quad claim there
    would be a category error — those markets omit ``regime_claim`` and are skipped."""
    try:
        from scripts import _cycle_seed as cs
        from engine.regime_prior import disagreement_block, regime_prior

        raw = markets_data_js.read_text(encoding="utf-8")
        src = cs._strip_comments(raw)
        markets = cs._P(cs._tokenize(cs._extract_assignment(src, "MARKETS"))).value()
        meta = cs._P(cs._tokenize(cs._extract_assignment(src, "MARKET_META"))).value()
        narratives: list[dict] = [m for m in markets if isinstance(m, dict) and "id" in m]
        meta_regime = (meta.get("regime") or {}) if isinstance(meta, dict) else {}
        narratives.append({"id": "meta", "regime_claim": meta_regime.get("regime_claim")})
        prior = regime_prior()
        return disagreement_block(narratives, prior=prior)
    except Exception as exc:  # noqa: BLE001
        log.warning("build_markets: regime disagreement check failed (non-fatal): %s", exc)
        return None


def _build_engine_js(
    site: Path,
    country_sectors: dict[str, dict],
    as_of: str,
    regime_disagreement: dict | None = None,
) -> int:
    """Emit site/marketsdata/markets_engine.js and return count of markets with engine data."""
    out_dir = site / "marketsdata"
    out_dir.mkdir(parents=True, exist_ok=True)

    records: dict[str, dict | None] = {}
    n_matched = 0
    for mkt_id, etf_id in MARKET_TO_ENGINE.items():
        cc_anchor = MARKET_TO_CC_ANCHOR.get(mkt_id)
        if etf_id is None or etf_id not in country_sectors:
            records[mkt_id] = {
                "has_engine": False,
                "etf_id": etf_id,
                "cc_anchor": cc_anchor,
                "note": "not yet in country engine — curated position only (OPINION-class)",
            }
        else:
            rec = _extract_engine_record(country_sectors[etf_id])
            rec["has_engine"] = True
            rec["etf_id"] = etf_id
            rec["cc_anchor"] = cc_anchor
            records[mkt_id] = rec
            n_matched += 1

    payload = {
        "version": 1,
        "wave": "W4.5",
        "as_of": as_of,
        "source": "site/countrycyclesdata/country_cycles.json",
        "markets": records,
        "regime_disagreement": regime_disagreement,
    }
    js_content = (
        "/* markets_engine.js — GENERATED by scripts/build_markets.py (W3.5).\n"
        "   window.MARKETS_ENGINE: engine-computed position/phase/turns/projection\n"
        "   per market, sourced from country_cycles.json.  Do not edit by hand.\n"
        "   Markets without a country_cycles record have has_engine=false. */\n"
        f"window.MARKETS_ENGINE = {json.dumps(payload, ensure_ascii=False)};\n"
    )
    out_path = out_dir / "markets_engine.js"
    out_path.write_text(js_content, encoding="utf-8")
    log.info("emitted %s (%d/%d markets with engine data)", out_path, n_matched, len(MARKET_TO_ENGINE))
    return n_matched


def _persisted_ms_view(market_key: str) -> dict | None:
    """Read one persisted market-state snapshot into the macro vm shape.

    Same reader and view shape as the nested ``_persisted_ms_view`` in
    ``scripts/build_site.py`` (the helper ``test_persisted_ms_view_helper_matches_build_site_contract``
    names). This calls ``engine.market_state.load_persisted`` — it does not open
    the JSON itself. A missing or unreadable feed returns None so the strip
    prints the designed-null row and the build does not crash.
    """
    try:
        from engine.market_state import load_persisted as _lp  # noqa: PLC0415

        _snap = _lp(market_key=market_key)
        if not _snap:
            return None
        _view = {
            "score": _snap.get("score"),
            "raw_score": _snap.get("raw_score"),
            "verdict": _snap.get("verdict"),
            "label_en": _snap.get("label_en"),
            "label_zh": _snap.get("label_zh"),
            "asof": _snap.get("asof"),
            "caveat_en": _snap.get("caveat_en") or "",
            "caveat_zh": _snap.get("caveat_zh") or "",
            "display_only": True,
            "market": market_key,
            "ms_history": [],
        }
        # Directory rule copied from the build_site helper: cn → china_market_state,
        # anything else → <key>_market_state. US history is not required here;
        # load_persisted("us") still reads data/market_state/latest.json.
        _log_dir = "china_market_state" if market_key == "cn" else f"{market_key}_market_state"
        _sl_path = config.data_dir() / _log_dir / "score_log.parquet"
        if _sl_path.exists():
            import pandas as pd  # noqa: PLC0415

            _all = pd.read_parquet(_sl_path).sort_values("date")
            _view["ms_history"] = _all.tail(60).to_dict(orient="records")
        return _view
    except Exception as exc:  # noqa: BLE001 — missing feed degrades to a null row
        log.warning("%s_market_state ingest failed (%s); degrading to None", market_key, exc)
        return None


def main() -> int:
    root = config.ROOT
    cfg = config.load()
    site = root / cfg["storage"]["site_dir"]
    site.mkdir(parents=True, exist_ok=True)

    # ---- 0. Emit the shared regime prior artifact (W4.5 — additive, cheap, never fatal) ----
    # Snapshot first. The emit rewrites regime_prior.js from live data, and this
    # page does not ship that rewrite. The bytes go back before the stamp below
    # so markets.html's ?v= names the file that remains.
    _prior_path = site / "regimedata" / "regime_prior.js"
    _prior_kept = _prior_path.read_bytes() if _prior_path.is_file() else None
    try:
        from scripts.build_regime_prior import emit as _emit_prior
        from lib import config as _cfg
        _emit_prior(data_dir=_cfg.data_dir(), site_dir=site)
    except Exception as _rp_exc:  # noqa: BLE001
        log.warning("build_markets: regime_prior emit failed (non-fatal): %s", _rp_exc)
    if _prior_kept is not None:
        _prior_path.write_bytes(_prior_kept)

    # ---- 1. Load country_cycles engine data ----
    country_sectors = _load_country_cycles(site)

    # ---- 2. Determine as_of (from country_cycles meta or fallback) ----
    cc_path = site / "countrycyclesdata" / "country_cycles.json"
    as_of = "unknown"
    if cc_path.exists():
        with cc_path.open(encoding="utf-8") as f:
            cc_meta = json.load(f).get("meta", {})
        as_of = cc_meta.get("asOf", "unknown")

    # ---- 3. Emit engine JS (with the W4.5 curated-vs-engine regime reconciliation) ----
    regime_disagreement = _regime_disagreement(site / "markets_data.js")
    n_matched = _build_engine_js(site, country_sectors, as_of, regime_disagreement)
    if regime_disagreement:
        log.warning("build_markets: regime disagreement: %s (%d claims, %s)",
                    regime_disagreement.get("banner_en"), regime_disagreement.get("n"),
                    "provisional/soft" if regime_disagreement.get("provisional") else "firm")
    if n_matched == 0:
        log.warning("build_markets: no engine records matched — check country_cycles.json path")
        return 1

    # ---- 4. Render HTML shell ----
    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=False,  # macro pages emit raw HTML; _navlinks uses |safe
    )
    try:                                       # _navlinks references t()/td()/tr() i18n globals
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — degrade to English-only rather than crash the build
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    # UD-B2-W4B-1: three persisted reads for the risk-regime strip.
    # None (missing / unreadable) renders the designed-null row. Never a crash.
    market_state = _persisted_ms_view("us")
    hk_market_state = _persisted_ms_view("hk")
    cn_market_state = _persisted_ms_view("cn")
    log.info(
        "market regime strip: us=%s hk=%s cn=%s",
        (market_state or {}).get("verdict"),
        (hk_market_state or {}).get("verdict"),
        (cn_market_state or {}).get("verdict"),
    )
    html = env.get_template("markets.html.j2").render(
        market_state=market_state,
        hk_market_state=hk_market_state,
        cn_market_state=cn_market_state,
    )
    # Stamp ?v= and defer before the page is committed. build_markets is the
    # writer for site/markets.html and this packet commits that file directly;
    # write_page alone would strip the stamps the render lane had already applied
    # (same regression build_whitehouse stamps around). Degrade-never-raise.
    try:
        from scripts.optimize_assets import make_optimizer
        html = make_optimizer(site)(html, site)
    except Exception as exc:  # noqa: BLE001
        log.warning("build_markets: asset stamp failed (%s); page left unstamped", exc)
    write_page(site / "markets.html", html, encoding="utf-8")

    # ---- 5. Copy committed page assets ----
    for asset in PAGE_ASSETS:
        src = root / "templates" / asset
        if src.exists():
            shutil.copy2(src, site / asset)

    # ---- 6. Refresh the `now` stanzas (level / %-off-ATH) from on-disk parquets ----
    # Fail-soft: a missing/stale series is skipped; the hand-written value is kept.
    try:
        from scripts.refresh_markets_now import refresh as _refresh_now
        n = _refresh_now(config.data_dir(), site / "markets_data.js")
        log.info("refresh_markets_now: patched %d market(s)", n)
    except Exception as exc:  # noqa: BLE001
        log.warning("refresh_markets_now failed (non-fatal): %s", exc)

    log.info(
        "built site/markets.html and site/marketsdata/markets_engine.js "
        "(%d/%d markets engine-backed)",
        n_matched,
        len(MARKET_TO_ENGINE),
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
