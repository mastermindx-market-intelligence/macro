"""Build the standalone China Alternative-Data desk page + machine-readable emits.

Runs the per-ticker convergence kernel + the honest signal-lab scorecard, fuses in the
richer alt-data planes that already ran upstream in the nightly (participation "who controls
the tape" regime, special-situations catalysts, THS narrative-basket radar) plus the fast
keyless microstructure parsers (涨停池 limit-up pool + sector breadth), renders
site/china_altdata.html, and emits site/chinaaltdata/{by_ticker,mastermind,feed}.json (the
mastermind.json is the context lens the intel bus + future China Mastermind read).

Render budget: special situations and narrative radar reuse upstream JSON. The current
participation projection is recomputed once from already-collected files so late arrivals
and same-date corrections are visible even on the first render. It never writes the archive
or invokes collectors. The company kernel is also computed once for all display outputs.

Callable standalone + importable (build()). CONTEXT-ONLY · never raises · never blocks render.
See research/CHINA_INTEL_POWERHOUSE.md §2.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config, site_assets  # noqa: E402
from lib.pages import write_page  # noqa: E402

log = logging.getLogger(__name__)

ASSETS = ("theme.css", "theme.js", "navigation-refresh.css", "china-altdata-desk.css", "china-altdata-desk.js")

def _site_dir() -> Path:
    sd = Path(config.load()["storage"]["site_dir"])
    return sd if sd.is_absolute() else (config.ROOT / sd)


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — missing/half-written upstream emit degrades to {}
        return {}


def _zt_rows(zt: dict, names: dict, top_n: int = 14) -> list[dict]:
    """涨停池 limit-up pool → top names by consecutive boards then seal size."""
    rows = [{"ticker": t, "name": names.get(t, t), **(v or {})} for t, v in (zt or {}).items()]
    rows.sort(key=lambda r: (r.get("consec_boards") or 0, r.get("seal_fund_yi") or 0), reverse=True)
    return rows[:top_n]


def _zt_breadth_rows(ztb: dict, top_n: int = 12) -> list[dict]:
    """涨停 sector breadth → hottest sectors by count of limit-ups."""
    rows = [{"sector": s, **(v or {})} for s, v in (ztb or {}).items()]
    rows.sort(key=lambda r: (r.get("n_zt") or 0, r.get("consec_max") or 0), reverse=True)
    return rows[:top_n]


def _narr_rows(narr: dict, top_n: int = 12) -> list[dict]:
    """THS narrative baskets → top by 63-day momentum rank."""
    baskets = sorted((narr or {}).get("baskets") or [], key=lambda b: b.get("rank_63d", 9999))
    return baskets[:top_n]


def _current_participation(site: Path) -> dict:
    """Read-only source computation, including the first render after this upgrade.

    No collector or archive writer is reachable here. A same-date revision must not
    be missed by trusting a cached artifact's maximum observation date.
    """
    try:
        from engine.china_participation import build_tape, current_projection
        current = current_projection(build_tape(backfill=False))
        if not current.get("date"):
            raise ValueError("current source frame has no observation")
        path = site / "chinastatedata" / "participation_current.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        return current
    except Exception as exc:  # archive fallback remains visibly qualified
        log.warning("China current participation unavailable: %s", exc)
        fallback = _read_json(site / "chinastatedata" / "participation.json")
        fallback["projection_kind"] = "first_observed_archive"
        fallback["computed_at"] = None
        return fallback


def build() -> dict | None:
    from engine import china_altdata as ad
    from engine import china_extras as ce
    from engine import china_signal_lab as lab

    weights = ad._leg_weights()
    full_rows = ad.full_rows(weights=weights)
    bt = ad.by_ticker(rows=full_rows, weights=weights)
    mm = ad.mastermind(bt)
    scorecard = lab.build_china_scorecard()
    try:                                        # 券商金股 + 业绩预告 — GATED display panels ([]/{} without token)
        broker_gold = ce.broker_gold()
        guidance = ce.forecast_guidance()
        guidance_labels = {k: list(v) for k, v in ce.GUIDANCE_LABELS.items()}
    except Exception:  # noqa: BLE001
        broker_gold, guidance, guidance_labels = [], {}, {}
    try:
        from engine.china_crowding import FLAG_LABELS as _crowd_labels
        crowd_labels = {k: list(v) for k, v in _crowd_labels.items()}
    except Exception:  # noqa: BLE001
        crowd_labels = {}

    site = _site_dir()
    site.mkdir(parents=True, exist_ok=True)

    # ---- richer alt-data planes: READ upstream emits (render-budget) + cheap keyless parsers ----
    participation = _current_participation(site)
    special = _read_json(site / "chinaspecialdata" / "special.json")
    narr_raw = _read_json(site / "factordata" / "china_narrative_radar.json")
    narr = _narr_rows(narr_raw)
    try:
        names = ad._name_map()
    except Exception:  # noqa: BLE001
        names = {}
    try:
        zt = _zt_rows(ce.zt_pool(), names)
        zt_breadth = _zt_breadth_rows(ce.zt_sector_breadth())
    except Exception:  # noqa: BLE001
        zt, zt_breadth = [], []

    from engine.china_altdata_desk import build_desk
    desk = build_desk(full_rows, weights, participation, special, crowd_labels)

    env = Environment(
        loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=False)
    from engine import i18n
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    html = env.get_template("china_altdata.html.j2").render(
        ad=bt, lab=scorecard, mm=mm, crowd_labels=crowd_labels, broker_gold=broker_gold,
        guidance=guidance, guidance_labels=guidance_labels,
        desk=desk, special=special, narr=narr,
        narr_asof=(narr_raw or {}).get("as_of"), zt=zt, zt_breadth=zt_breadth)
    write_page(site / "china_altdata.html", html)
    for a in ASSETS:
        src = config.ROOT / "templates" / a
        if src.exists():
            site_assets.copy_asset(a, src, site)
    log.info("wrote %s/china_altdata.html (%d KB)", site, len(html) // 1024)

    out = site / "chinaaltdata"
    out.mkdir(parents=True, exist_ok=True)
    (out / "desk.json").write_text(json.dumps(desk, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    (out / "by_ticker.json").write_text(
        json.dumps(bt or {}, ensure_ascii=False, separators=(",", ":"), default=str))
    (out / "mastermind.json").write_text(
        json.dumps(mm, ensure_ascii=False, separators=(",", ":"), default=str))
    (out / "feed.json").write_text(
        json.dumps(scorecard, ensure_ascii=False, separators=(",", ":"), default=str))
    log.info("wrote %s/chinaaltdata/{by_ticker,mastermind,feed}.json", site)
    return bt


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
