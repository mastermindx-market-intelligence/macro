"""Build the Sector Cycle Intelligence page -> site/sector_cycles.html.

A data-driven sibling of Cycle Intelligence (build_cycle.py): engine/sector_cycles
derives each US sector ETF's real-price series, auto-detected turns, cycle phase and
next-turn projection; this script binds the researched leg narratives
(data/sector_cycles/narratives.json), emits them as three split data files:
  - site/sector_cycles_data.js      -> window.SECTOR_CYCLES only (core, ~2MB)
  - site/sector_cycles_narr_data.js -> window.SECTOR_NARR only (lazy-loaded, ~1.8MB)
  - site/sector_cycles_dna_data.js  -> window.SECTOR_DNA only (lazy-loaded, ~330KB)
NARR and DNA are loaded lazily after boot (only used in tap-to-focus panels / dnaHTML).
Renders the page shell from templates/sector_cycles.html.j2, copies the page-specific
assets. Reuses the already-committed site/mm_charts.js + site/cycle.css (the shared
cycle design system).

Additive — any failure is logged and returns 0 so it can never break the rest of the
site build.

Usage: python -m scripts.build_sector_cycles
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

log = logging.getLogger("build_sector_cycles")

PAGE_ASSETS = ("sector_cycles.css", "sector_cycles.js")
# the shared cycle design system this page reuses — must exist in site/ (built by
# build_cycle.py and committed); copied from templates/ only if a refactor moves them.
SHARED_ASSETS = ("mm_charts.js", "cycle.css")


def backtest_turn_record(scorecard_path: Path) -> dict | None:
    """Pooled BACKTEST turn grades, or None when the file is not that record."""
    try:
        raw = json.loads(Path(scorecard_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    cohorts = raw.get("cohorts")
    if not isinstance(cohorts, dict):
        return None
    back = cohorts.get("BACKTEST")
    if not isinstance(back, dict) or back.get("cohort") != "BACKTEST":
        return None
    turn_pr = back.get("turn_pr")
    if not isinstance(turn_pr, dict):
        return None
    rows = turn_pr.get("per_instrument")
    if not isinstance(rows, dict) or len(rows) == 0:
        return None
    turns = met = right = n_false = 0
    tau: int | None = None
    count_keys = ("tp", "fp", "fn", "n_truth_turns", "tau_months")
    for row in rows.values():
        if not isinstance(row, dict):
            return None
        vals: dict[str, int] = {}
        for key in count_keys:
            val = row.get(key)
            # A bool is an int subclass, and it is not a count.
            if type(val) is not int or val < 0:
                return None
            vals[key] = val
        if vals["fn"] > vals["n_truth_turns"]:
            return None
        if tau is None:
            tau = vals["tau_months"]
        elif vals["tau_months"] != tau:
            return None
        turns += vals["n_truth_turns"]
        met += vals["n_truth_turns"] - vals["fn"]
        right += vals["tp"]
        n_false += vals["fp"]
    if type(tau) is not int:
        return None
    if "pooled" in turn_pr:
        pooled = turn_pr.get("pooled")
        if not isinstance(pooled, dict):
            return None
        got = (pooled.get("tp"), pooled.get("fp"), pooled.get("fn"))
        if got != (right, n_false, turns - met):
            return None
    as_of = raw.get("as_of")
    if not isinstance(as_of, str) or len(as_of) < 10:
        return None
    parts = as_of[:10].split("-")
    if len(parts) != 3:
        return None
    if not all(ch in "0123456789" for ch in "".join(parts)):
        return None
    if (len(parts[0]), len(parts[1]), len(parts[2])) != (4, 2, 2):
        return None
    year = int(parts[0])
    month = int(parts[1])
    day = int(parts[2])
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    month_days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if month < 1 or month > 12 or day < 1 or day > month_days[month - 1]:
        return None
    return {
        "as_of": as_of[:10],
        "tau_months": tau,
        "funds": sorted(rows),
        "turns": turns,
        "met": met,
        "right": right,
        "false": n_false,
    }


def _load_narratives(root: Path, receipt: dict | None = None) -> dict:
    """NARR keyed by the chart's series id: sectors by ticker.lower() (xlk…), baskets
    by the engine's "b-"+membership-key (b-mag7…). Merges the file's sectors+baskets.

    W2.1: epoch-aware — resolves narratives.<epoch>.json for the engine's current epoch,
    falling back to the legacy un-suffixed file (tagged tr_v0). Zero behaviour change
    today (no flip → legacy file resolves exactly as before)."""
    from scripts._narrative_epoch import resolve_narratives, publication_receipt
    res = resolve_narratives("sector_cycles", root / "data" / "sector_cycles", "narratives")
    if res["stale_quarantined"]:
        log.warning("sector_cycles: narratives stale-quarantined (epoch %s) — page renders without",
                    res["epoch"])
    if receipt is not None:
        receipt.update(publication_receipt(res))
    return res["map"]


def _load_dna(root: Path, receipt: dict | None = None) -> dict:
    """SECTOR_DNA (the front-loaded "history rhymes" / cycle-cause profiles), same id keying as
    narratives: sectors by ticker.lower(), baskets by "b-"+key. Optional — page renders without.

    W2.1: epoch-aware (resolves cycle_dna.<epoch>.json, falls back to legacy cycle_dna.json)."""
    from scripts._narrative_epoch import resolve_narratives, publication_receipt
    res = resolve_narratives("sector_cycles", root / "data" / "sector_cycles", "cycle_dna")
    if res["stale_quarantined"]:
        log.warning("sector_cycles: cycle_dna stale-quarantined (epoch %s) — rendering without DNA",
                    res["epoch"])
    if receipt is not None:
        receipt.update(publication_receipt(res))
    return res["map"]


def _stamp_rotation_context(payload: dict, *, site_root=None, today=None) -> None:
    """SIC-D-B02: stamp a backend-stamped, guarded rotation context into the cycles payload.

    Adds top-level ``rotation_context`` (schema sector_cycles.rotation_context.v1) and
    ``rotation_alignment_version``; every other payload byte is untouched.  The page
    receiver (templates/sector_cycles.js loadRotation) can consume this block; its
    raw marketdata read path is unchanged until the receiver is switched over, so
    the stamp is additive, not a replacement (RB02 #3).

    Events (site/marketdata/rotation_events.json): schema must be rotation_events.v1
    and ok is True, else invalid_payload; alignment compares the payload's top-level
    ``as_of`` — the SAME field the Central measured adapter compares
    (engine/leadership_rotation_context.py, measured_group_read:
    rotation_payload["as_of"] != session_end).  ``active`` is copied only when
    aligned and list-typed.

    Fragmentation (site/marketdata/sector_fragmentation.json): alignment compares its
    top-level ``as_of`` (written by engine/sector_fragmentation.py compute() as the
    max per-sector ``asof`` bar date); per-sector rows are copied only when aligned.

    Missing files → missing_input.  Any exception in here degrades the whole block
    to {"schema", "status": "unavailable", "reason": "projection_error"} — never
    breaks the rest of the cycles build.
    """
    import datetime as _dt

    def _aligned_copy(align: dict, ok_payload, data_key) -> dict:
        out = dict(align)
        out[data_key] = None
        if align["status"] == "aligned" and isinstance(ok_payload.get(data_key), (list, tuple)):
            out[data_key] = list(ok_payload[data_key])
        return out

    try:
        from engine import sector_generation_guard as _sgg

        root = Path(site_root) if site_root is not None else (
            config.ROOT / config.load().get("storage", {}).get("site_dir", "site"))
        today = today if today is not None else _dt.datetime.now(_dt.timezone.utc).date()
        consumer = (payload.get("meta") or {}).get("asOf")

        ctx: dict = {"schema": "sector_cycles.rotation_context.v1"}

        # --- events ---
        ev_path = root / "marketdata" / "rotation_events.json"
        try:
            ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else None
        except Exception:  # noqa: BLE001 — unreadable is missing, not fatal
            ev = None
        if ev is None:
            ctx["events"] = {"status": "missing_input", "reason": "missing_input",
                             "artifact_session": None,
                             "consumer_session": _sgg.parse_session(consumer).isoformat()
                             if _sgg.parse_session(consumer) else None,
                             "clock": "settled_daily_session", "active": None}
        elif ev.get("schema") != "rotation_events.v1" or ev.get("ok") is not True:
            ctx["events"] = {"status": "invalid_payload", "reason": "invalid_payload",
                             "artifact_session": None,
                             "consumer_session": _sgg.parse_session(consumer).isoformat()
                             if _sgg.parse_session(consumer) else None,
                             "clock": "settled_daily_session", "active": None}
        else:
            ctx["events"] = _aligned_copy(
                _sgg.session_alignment(ev.get("as_of"), consumer, today=today), ev, "active")

        # --- fragmentation ---
        fr_path = root / "marketdata" / "sector_fragmentation.json"
        try:
            fr = json.loads(fr_path.read_text(encoding="utf-8")) if fr_path.exists() else None
        except Exception:  # noqa: BLE001
            fr = None
        if fr is None:
            ctx["fragmentation"] = {"status": "missing_input", "reason": "missing_input",
                                    "artifact_session": None,
                                    "consumer_session": _sgg.parse_session(consumer).isoformat()
                                    if _sgg.parse_session(consumer) else None,
                                    "clock": "settled_daily_session", "sectors": None}
        else:
            ctx["fragmentation"] = _aligned_copy(
                _sgg.session_alignment(fr.get("as_of"), consumer, today=today), fr, "sectors")

        payload["rotation_context"] = ctx
        payload["rotation_alignment_version"] = 1
    except Exception as e:  # noqa: BLE001 — projection never breaks the build
        log.warning("sector_cycles: rotation_context projection failed (%s) — stamped unavailable", e)
        payload["rotation_context"] = {"schema": "sector_cycles.rotation_context.v1",
                                       "status": "unavailable", "reason": "projection_error"}
        payload["rotation_alignment_version"] = 1


def main() -> int:
    root = config.ROOT
    try:
        site = root / config.load()["storage"]["site_dir"]
    except Exception:  # noqa: BLE001
        site = root / "site"
    site.mkdir(parents=True, exist_ok=True)

    try:
        from engine import sector_cycles
        data = sector_cycles.compute()
    except Exception as e:  # noqa: BLE001
        log.exception("sector_cycles engine failed: %s", e)
        return 0
    if not data or not data.get("sectors"):
        log.warning("sector_cycles: no data — skipped")
        return 0

    # W0.2: append prospective forward-log stamp (keep-FIRST per (date,id), additive)
    try:
        from engine.cycle_forward_log import append_forward_log
        n_stamped = append_forward_log(data, "sector_cycles")
        log.info("sector_cycles: forward log: %d rows stamped", n_stamped)
    except Exception as e:  # noqa: BLE001
        log.warning("sector_cycles: forward log append skipped: %s", e)

    sources = {"narr": {}, "dna": {}}
    narr = _load_narratives(root, sources["narr"])
    dna = _load_dna(root, sources["dna"])

    # W3.4: enrich NARR map with TTL / staleness / archetype-check metadata
    try:
        from scripts._narrative_ttl import enrich_narr_ttl
        narr = enrich_narr_ttl(narr)
        log.info("sector_cycles: narrative TTL enrichment applied")
    except Exception as e:  # noqa: BLE001
        log.warning("sector_cycles: TTL enrichment skipped: %s", e)

    # SIC-D-B02: backend-stamped, guarded rotation context — added before the
    # split so it rides the CORE payload; receiver-side raw-file trust can be
    # retired only once the receiver reads this block (RB02 #3).
    _stamp_rotation_context(data)

    # data JS split for lazy loading:
    #   sector_cycles_data.js        -> SECTOR_CYCLES (CORE — light, loaded at boot)
    #   sector_cycles_series_data.js -> SECTOR_CYCLES_SERIES (heavy per-entity arrays,
    #                                   hydrated AFTER first paint by sector_cycles.js)
    #   sector_cycles_narr_data.js   -> SECTOR_NARR (lazy, only needed in focus panels)
    #   sector_cycles_dna_data.js    -> SECTOR_DNA  (lazy, only needed in dnaHTML())
    # The CORE keeps sectors' osc+turns (default sectors-osc first paint) but strips
    # price everywhere and osc/turns from baskets/nasdaq/russell — see split_cycles_payload.
    from scripts._cycles_payload import publication_scripts
    turn_rec = backtest_turn_record(
        root / "data" / "sector_cycles" / "scorecards" / "promises_price_v1_zz14_v0.json")
    publication = publication_scripts(data, narr, dna, sources=sources, core_extra={"turn_record": turn_rec} if turn_rec is not None else None)
    for kind, suffix in (("core", "data"), ("series", "series_data"), ("narr", "narr_data"), ("dna", "dna_data")):
        (site / ("sector_cycles_" + suffix + ".js")).write_text(publication[kind], encoding="utf-8")


    # also publish the raw model for external consumers / debugging
    fdir = site / "sectordata"
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "sector_cycles.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=False,  # macro pages emit raw HTML; _navlinks uses |safe
    )
    try:                                       # _navlinks references t()/td()/tr() i18n globals
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — degrade to English-only rather than crash the build
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    html = env.get_template("sector_cycles.html.j2").render()
    write_page(site / "sector_cycles.html", html, encoding="utf-8")

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
                log.warning("sector_cycles: shared asset %s missing from site/ — run build_cycle first", asset)

    log.info("built site/sector_cycles.html (%d sectors, %d with narratives)",
             len(data["sectors"]), len(narr))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
