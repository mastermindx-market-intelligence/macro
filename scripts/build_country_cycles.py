"""Build the Country Cycle Intelligence page -> site/country_cycles.html.

The international sibling of scripts/build_sector_cycles.py: engine/country_cycles derives
every country / region ETF's real-USD-price cycle (rebased price + 0-100 oscillator,
auto-detected turns, the 5-phase wheel, a median-half-cycle next-turn projection, RS vs
SPY). This script binds any researched leg narratives (data/country_cycles/narratives.json)
and cycle-DNA profiles (data/country_cycles/cycle_dna.json), emits site/country_cycles_data.js
(window.SECTOR_CYCLES + window.SECTOR_NARR + window.SECTOR_DNA — the SAME globals the shared
sector_cycles.js consumes), publishes the raw model under site/countrycyclesdata/, renders
templates/country_cycles.html.j2, and copies the shared cycle assets.

Reuses the already-built site/sector_cycles.{css,js} + mm_charts.js + cycle.css — the shared
cycle design system — so this page reads identically to the US and China cycle pages.

Additive — any failure is logged and returns 0 so it can never break the rest of the site build.

Usage: python -m scripts.build_country_cycles
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402

log = logging.getLogger("build_country_cycles")

PAGE_ASSETS = ("sector_cycles.css", "sector_cycles.js")   # SHARED with the US/China cycle pages
SHARED_ASSETS = ("mm_charts.js", "cycle.css")             # the shared cycle design system


def _load_narratives(root: Path) -> dict:
    """NARR keyed by the chart series id: countries by ticker.lower() (ewj…), aggregates
    likewise (efa…). Merges the file's `sectors` + `baskets` maps. Optional.

    W2.1: epoch-aware — resolves narratives.<epoch>.json for the engine's current epoch,
    falling back to the legacy un-suffixed file (tagged tr_v0). Country baskets keep their
    un-prefixed keying. Zero behaviour change today."""
    from scripts._narrative_epoch import resolve_narratives
    res = resolve_narratives("country_cycles", root / "data" / "country_cycles", "narratives")
    if res["stale_quarantined"]:
        log.warning("country_cycles: narratives stale-quarantined (epoch %s) — rendering without",
                    res["epoch"])
    return res["map"]


def _load_dna(root: Path) -> dict:
    """SECTOR_DNA cycle-cause profiles, same id keying as narratives (ticker.lower()).

    W2.1: epoch-aware (resolves cycle_dna.<epoch>.json, falls back to legacy cycle_dna.json)."""
    from scripts._narrative_epoch import resolve_narratives
    res = resolve_narratives("country_cycles", root / "data" / "country_cycles", "cycle_dna")
    if res["stale_quarantined"]:
        log.warning("country_cycles: cycle_dna stale-quarantined (epoch %s) — rendering without DNA",
                    res["epoch"])
    return res["map"]


def _cycle_records(data: dict):
    """Yield the country and aggregate records the builder already holds at render."""
    if not isinstance(data, dict):
        return
    for key in ("sectors", "baskets"):
        for rec in (data.get(key) or []):
            if isinstance(rec, dict):
                yield rec


def _display_pair(rec: dict):
    """A record's display names as strings; the Chinese name falls back to English."""
    name = str(rec.get("name") or "")
    zh = rec.get("name_zh")
    return name, (str(zh) if zh else name)


def _month_token(value) -> str:
    """The value only when it is a `YYYY-MM` month string, else the empty string."""
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        return ""
    head, tail = value[:4], value[5:]
    ok = head.isascii() and tail.isascii() and head.isdigit() and tail.isdigit()
    return value if ok else ""


def _finite_multiple(value):
    """The value as a finite float, or None — bool, NaN and inf are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    num = float(value)
    if num != num or num == float("inf") or num == float("-inf"):
        return None
    return num


def _projection_receipt(data: dict) -> dict:
    """Which projected next-turn windows have already lapsed, and how far past due.

    Reads the model's own projection verdict: `overdue` is the bool the producer
    recorded, `overdue_frac` is the lapse in median HALF-cycles since the anchor turn
    (so it is worded as a multiple of the half-cycle, never as a period), and
    `last_confirmed_t` is the confirmed turn the projection is anchored on.
    Returns {} when no record carries a bool verdict."""
    n_total = 0
    lapsed = []
    for rec in _cycle_records(data):
        proj = rec.get("proj")
        if not isinstance(proj, dict) or not isinstance(proj.get("overdue"), bool):
            continue
        n_total += 1
        if proj["overdue"] is not True:
            continue          # the window is still ahead of today — nothing to receipt
        name, name_zh = _display_pair(rec)
        turn = proj.get("nextTurn")
        rec_id = str(rec.get("id") or "")
        num = _finite_multiple(proj.get("overdue_frac"))
        row = {"id": rec_id, "name": name, "name_zh": name_zh,
               "turn": turn if turn in ("peak", "trough") else "",
               "central": _month_token(proj.get("central")),
               "anchor": _month_token(proj.get("last_confirmed_t")),
               "frac": None if num is None else round(num, 1)}
        order = (0, -num, rec_id) if num is not None else (1, 0.0, rec_id)
        lapsed.append((order, row))
    if n_total == 0:
        return {}
    rows = [row for _, row in sorted(lapsed, key=lambda item: item[0])]
    return {"lapsed": rows, "n_lapsed": len(rows), "n_total": n_total}


_HAZARD_REASON_COPY = {
    "non_monotone_cdf": (
        "the 1-, 3- and 6-month probabilities did not form a rising sequence, so none is shown",
        "1、3、6 个月概率未构成递增序列，故不予显示",
    ),
}


def _hazard_availability(data: dict) -> dict:
    """Which markets carry a calibrated turn probability and which were withheld.

    A hazard the producer marked unavailable is withheld, and its reason token is
    counted only when _HAZARD_REASON_COPY maps it to human wording — an unmapped
    token still counts as withheld but contributes no clause, so no machine token can
    reach the page. Returns {} when the model carries neither state anywhere."""
    available, withheld, counts = [], [], {}
    for rec in _cycle_records(data):
        now = rec.get("now")
        hazard = now.get("hazard") if isinstance(now, dict) else None
        if not isinstance(hazard, dict):
            continue
        name, name_zh = _display_pair(rec)
        entry = {"id": str(rec.get("id") or ""), "name": name, "name_zh": name_zh}
        if hazard.get("unavailable"):
            withheld.append(entry)
            token = hazard.get("unavailable_reason")
            if isinstance(token, str) and token in _HAZARD_REASON_COPY:
                counts[token] = counts.get(token, 0) + 1
        elif any(isinstance(hazard.get(key), dict) for key in ("1m", "3m", "6m")):
            available.append(entry)
    if not available and not withheld:
        return {}
    reasons = [{"en": _HAZARD_REASON_COPY[tok][0], "zh": _HAZARD_REASON_COPY[tok][1],
                "n": counts[tok]}
               for tok in _HAZARD_REASON_COPY if counts.get(tok, 0)]
    return {"available": available, "withheld": withheld,
            "n_available": len(available), "n_withheld": len(withheld),
            "n_total": len(available) + len(withheld), "reasons": reasons}

_PHASE_LABEL_COPY = {
    "Peak": ("Topping", "见顶"),
    "Expansion": ("Trending", "上行"),
    "Downturn": ("Rolling over", "回落"),
    "Recovery": ("Prime entry", "入场良机"),
    "Trough": ("Bottoming", "筑底"),
}


def _cc_pct(v):
    """Round a finite real percent to 1dp, or None; normalize -0.0 to 0.0."""
    f = _finite_multiple(v)
    if f is None:
        return None
    out = round(f, 1)
    return 0.0 if out == 0 else out


def _fx_contribution(data: dict) -> dict:
    """Per-market 3-month/1-year local-currency move vs USD (ccy-per-USD), or {} when none.

    Rows carry rounded r63/r252 (None when the leg is missing) and the currency code —
    never fx.pair, whose quote direction does not match the stored orientation.
    """
    rows = []
    for rec in _cycle_records(data):
        fx = rec.get("fx")
        if not isinstance(fx, dict) or fx.get("quote") != "ccy_per_usd":
            continue
        pair = fx.get("pair")
        if not (isinstance(pair, str) and len(pair) == 6 and pair.isalpha()
                and pair.isupper()):
            continue
        if pair[:3] == "USD":
            ccy = pair[3:]
        elif pair[3:] == "USD":
            ccy = pair[:3]
        else:
            continue
        r63 = _cc_pct(fx.get("leg_return_63d"))
        r252 = _cc_pct(fx.get("leg_return_252d"))
        if r63 is None and r252 is None:
            continue
        name = rec.get("name") if isinstance(rec.get("name"), str) else ""
        name_zh = rec.get("name_zh") if isinstance(rec.get("name_zh"), str) else name
        rows.append({"id": rec.get("id"), "name": name, "name_zh": name_zh,
                     "ccy": ccy, "r63": r63, "r252": r252})
    if not rows:
        return {}
    return {"rows": rows, "n_rows": len(rows)}


def _canonical_phase(data: dict) -> dict:
    """Canonical ontology phase/position per market (copy-mapped, read-only), or {}.

    Positions round like the drawer's JS Math.round (half up), not Python round;
    only mapped phase tokens leave this helper.
    """
    rows = []
    n_differ = 0
    for rec in _cycle_records(data):
        now = rec.get("now")
        if not isinstance(now, dict):
            continue
        canon = now.get("phase_v2")
        label = _PHASE_LABEL_COPY.get(canon) if isinstance(canon, str) else None
        if label is None:
            continue
        pv2 = now.get("pos_v2")
        if isinstance(pv2, bool) or not isinstance(pv2, (int, float)) or not 0 <= pv2 <= 100:
            continue
        ph = now.get("phase")
        differs = isinstance(ph, str) and ph != canon
        wheel = _PHASE_LABEL_COPY.get(ph) if isinstance(ph, str) else None
        p = now.get("pos")
        pos = None
        if isinstance(p, (int, float)) and not isinstance(p, bool) and 0 <= p <= 100:
            pos = int(p + 0.5)
        name = rec.get("name") if isinstance(rec.get("name"), str) else ""
        name_zh = rec.get("name_zh") if isinstance(rec.get("name_zh"), str) else name
        rows.append({"id": rec.get("id"), "name": name, "name_zh": name_zh,
                     "canon_en": label[0], "canon_zh": label[1],
                     "pos_v2": int(pv2 + 0.5), "differs": differs,
                     "wheel_en": wheel[0] if wheel else "",
                     "wheel_zh": wheel[1] if wheel else "", "pos": pos})
        if differs:
            n_differ += 1
    if not rows:
        return {}
    return {"rows": rows, "n_rows": len(rows), "n_differ": n_differ}


def main() -> int:
    root = config.ROOT
    try:
        site = root / config.load()["storage"]["site_dir"]
    except Exception:  # noqa: BLE001
        site = root / "site"
    site.mkdir(parents=True, exist_ok=True)

    try:
        from engine import country_cycles
        data = country_cycles.compute()
    except Exception as e:  # noqa: BLE001
        log.exception("country_cycles engine failed: %s", e)
        return 0
    if not data or not data.get("sectors"):
        log.warning("country_cycles: no data — skipped")
        return 0

    # W0.2: append prospective forward-log stamp (keep-FIRST per (date,id), additive)
    try:
        from engine.cycle_forward_log import append_forward_log
        n_stamped = append_forward_log(data, "country_cycles")
        log.info("country_cycles: forward log: %d rows stamped", n_stamped)
    except Exception as e:  # noqa: BLE001
        log.warning("country_cycles: forward log append skipped: %s", e)

    narr = _load_narratives(root)
    dna = _load_dna(root)

    # W3.4: enrich NARR map with TTL / staleness / archetype-check metadata
    try:
        from scripts._narrative_ttl import enrich_narr_ttl
        narr = enrich_narr_ttl(narr)
        log.info("country_cycles: narrative TTL enrichment applied")
    except Exception as e:  # noqa: BLE001
        log.warning("country_cycles: TTL enrichment skipped: %s", e)

    # data JS split for lazy loading (previously ONE file bundling all three globals —
    # 2.7MB in the critical path). Now:
    #   country_cycles_data.js        -> SECTOR_CYCLES (CORE — light, loaded at boot)
    #   country_cycles_series_data.js -> SECTOR_CYCLES_SERIES (price for all; osc/turns for
    #                                    baskets; fx + usd_record for the 24 countries —
    #                                    hydrated AFTER first paint by sector_cycles.js)
    #   country_cycles_narr_data.js   -> SECTOR_NARR (lazy, only needed in focus panels)
    #   country_cycles_dna_data.js    -> SECTOR_DNA  (lazy, only needed in dnaHTML())
    from scripts._cycles_payload import split_cycles_payload
    core, series = split_cycles_payload(data)   # does not mutate `data` (features json stays full)
    (site / "country_cycles_data.js").write_text(
        "window.SECTOR_CYCLES=" + json.dumps(core, separators=(",", ":"), ensure_ascii=False) + ";\n",
        encoding="utf-8")
    (site / "country_cycles_series_data.js").write_text(
        "window.SECTOR_CYCLES_SERIES=" + json.dumps(series, separators=(",", ":"), ensure_ascii=False) + ";\n",
        encoding="utf-8")
    (site / "country_cycles_narr_data.js").write_text(
        "window.SECTOR_NARR=" + json.dumps(narr, separators=(",", ":"), ensure_ascii=False) + ";\n",
        encoding="utf-8")
    (site / "country_cycles_dna_data.js").write_text(
        "window.SECTOR_DNA=" + json.dumps(dna, separators=(",", ":"), ensure_ascii=False) + ";\n",
        encoding="utf-8")

    # also publish the raw model for external consumers / debugging
    fdir = site / "countrycyclesdata"
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "country_cycles.json").write_text(
        json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=False,  # macro pages emit raw HTML; _navlinks uses |safe
    )
    try:                                       # _navlinks references t()/td()/tr() i18n globals
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — degrade to English-only rather than crash the build
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    html = env.get_template("country_cycles.html.j2").render(
        projection_receipt=_projection_receipt(data),
        hazard_availability=_hazard_availability(data),
        fx_contribution=_fx_contribution(data), canonical_phase=_canonical_phase(data))
    write_page(site / "country_cycles.html", html, encoding="utf-8")

    for asset in PAGE_ASSETS:
        src = root / "templates" / asset
        if src.exists():
            shutil.copy2(src, site / asset)
    for asset in SHARED_ASSETS:
        if not (site / asset).exists():
            src = root / "templates" / asset
            if src.exists():
                shutil.copy2(src, site / asset)
            else:
                log.warning("country_cycles: shared asset %s missing — run build_cycle first", asset)

    log.info("built site/country_cycles.html (%d countries, %d aggregates, %d narratives, %d dna)",
             len(data["sectors"]), len(data.get("baskets", [])), len(narr), len(dna))
    return 0



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
