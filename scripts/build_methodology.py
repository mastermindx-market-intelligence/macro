"""Build the methodology page -> site/methodology.html.

Mostly-static documentation of how the Factor Lab / Baskets / Seasonality pages are
constructed (our actual free-data methodology + honest limits), with a few live stats
pulled from the already-built JSONs (IC scorecard, factor series, baskets). Additive —
any missing input falls back to a sensible default so it can never break the build.

Usage: python -m scripts.build_methodology
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_methodology")


def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    site = config.ROOT / "site"
    ic = _load(site / "factordata" / "ic_scorecard.json") or _load(config.data_dir() / "edgar" / "ic_scorecard.json")
    fs = _load(site / "factordata" / "factor_series.json")
    bk = _load(site / "basketdata" / "baskets.json")
    seas = _load(site / "factordata" / "factor_seasonality.json")

    meth = _build_meth(ic, fs, bk, seas)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    env = Environment(loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=True)
    html = env.get_template("methodology.html.j2").render(meth=meth, generated_utc=built)
    write_page(site / "methodology.html", html)
    log.info("wrote %s/methodology.html (%d KB)", site, len(html) // 1024)
    return 0


def _build_meth(ic: dict, fs: dict, bk: dict, seas: dict) -> dict:
    """Assemble the page context from the already-built artifacts. Pure: no I/O.

    Additive and fail-open like _load(): every key the W23 packet adds is None when
    its artifact does not carry the value — never 0, never False, never "" — so a
    missing input leaves the template's documented sentence untouched instead of
    printing a number the producer never recorded. Aggregation happens here, not in Jinja.
    """
    facs = (ic.get("factors") or {})
    meth = {
        "as_of": fs.get("as_of") or bk.get("as_of") or "—",
        "n_factors": len(fs.get("factors") or []) or 8,
        "n_baskets": len(bk.get("baskets") or []) or 14,
        "n_categories": len(bk.get("categories") or []) or 7,
        "n_sectors": len((fs.get("chart_data") or {}).get("sector") or {}) or 11,
        "ic_span": ic.get("span") or "the free-data window",
        "ic_rebalances": ic.get("rebalances") or 11,
        "ic_universe": ic.get("median_universe") or 1300,
        "ic_any_survive": any(v.get("survives_fdr") for v in facs.values()) if facs else False,
    }
    # SPEC 1 — the basket line is back-projected for a count of the real baskets.
    dates = (bk.get("chart") or {}).get("dates") or []
    baskets = bk.get("baskets") or []
    start = dates[0] if isinstance(dates, list) and dates else ""
    wired_bp = bool(start) and isinstance(baskets, list) and bool(baskets)
    meth["bk_series_start"] = start if wired_bp else None
    meth["bk_n_back_projected"] = (sum(1 for b in baskets if (b.get("created") or "") > start)
                                   if wired_bp else None)
    meth["bk_n_total"] = len(baskets) if wired_bp else None
    # SPEC 2 — the basis the IC artifact itself records, plus the surviving factors.
    bias = ic.get("survivorship_biased")
    meth["ic_survivorship_biased"] = bias if isinstance(bias, bool) else None
    kind, prices = ic.get("universe"), ic.get("price_span")
    meth["ic_universe_kind"] = kind if isinstance(kind, str) and kind else None
    meth["ic_price_span"] = prices if isinstance(prices, str) and prices else None
    horizon = ic.get("horizon_d")
    meth["ic_horizon_d"] = (horizon if isinstance(horizon, int)
                            and not isinstance(horizon, bool) else None)
    meth["ic_survivors"] = None if not ic.get("factors") else sorted(
        [{"name": k, "q_fdr": v.get("q_fdr") if isinstance(v.get("q_fdr"), (int, float)) else None}
         for k, v in facs.items() if isinstance(v, dict) and v.get("survives_fdr") is True],
        key=lambda r: (r["q_fdr"] is None, r["q_fdr"] or 0.0))
    # SPEC 3 — per-style Ken French starts, and the trailing windows that exist.
    sfacs = seas.get("factors")
    meth["seasonality_styles"] = None
    meth["seasonality_window_years"] = None
    if seas.get("schema") == "factor_seasonality.v2" and isinstance(sfacs, list) and sfacs:
        meth["seasonality_styles"] = [
            {"label_en": f.get("label_en"), "label_zh": f.get("label_zh"),
             "start": f.get("start"), "n_months": f.get("n_months")}
            for f in sfacs if isinstance(f, dict)]
        found = {int(k[9:-1]) for f in sfacs if isinstance(f, dict) for k in f
                 if k.startswith("trailing_") and k.endswith("y") and k[9:-1].isdigit()}
        meth["seasonality_window_years"] = sorted(found, reverse=True)
    # SPEC 4 — how the basket panel's prices resolved, and on how many of its members.
    pr = bk.get("price_resolution")
    meth["bk_price_resolution"] = None if not isinstance(pr, dict) else {
        "requested_n": pr.get("requested_n"), "resolved_n": pr.get("resolved_n"),
        "unresolved_n": pr.get("unresolved_n"),
        "unresolved_tickers": list(pr.get("unresolved_tickers") or []),
        "source_basis": pr.get("source_basis") if isinstance(pr.get("source_basis"), dict) else {},
        "adjustment_vintage": pr.get("adjustment_vintage")}
    obs = [b.get("observation") for b in baskets if isinstance(b.get("observation"), dict)]
    meth["bk_n_partial"] = sum(1 for o in obs if o.get("status") == "partial") if obs else None
    meth["bk_n_observed"] = len(obs) if obs else None
    rows = [(o.get("coverage"), b.get("id"), o.get("observed_n"), o.get("configured_n"))
            for b, o in ((b, b.get("observation")) for b in baskets)
            if isinstance(o, dict) and isinstance(o.get("coverage"), (int, float))]
    meth["bk_min_coverage"] = None if not rows else dict(
        zip(("id", "observed_n", "configured_n"), min(rows)[1:]))
    return meth


if __name__ == "__main__":
    sys.exit(main())
