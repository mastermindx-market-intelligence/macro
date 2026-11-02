#!/usr/bin/env python3
"""INTL-GS-W2A (IM13) fixture + evidence CLI: production, abstain-all and
specimen variants of the real intl.html through the REAL scanner/coverage
builders and templates.

CLI:
    python3 tests/intl_gs_scanner_fixture.py --out <dir>
    python3 tests/intl_gs_scanner_fixture.py --print-html
    python3 tests/intl_gs_scanner_fixture.py --print-abstain
    python3 tests/intl_gs_scanner_fixture.py --print-specimen

``--out`` writes the foundation site first (tests/intl_gs_fixture_site.py
write_site, NO --stub-coverage), then OVERWRITES intl.html with the
PRODUCTION variant (attach_surveillance over a synthetic admitted observation
set built exactly the way tests/test_intl_gs_foundation.py builds one: two
source_snapshot calls, build_return_records, qualify per basis, through
lib.intl_gs_observations.build_observation_set — every number reaches the page
through the Wave 1 contract), writes intl-abstain.html (observations=None) and
intl-gs-scanner-specimen.html (the spec §10.1 specimen rows inside the
specimen chip, layout acceptance only). Specimen values NEVER leave this
module: no production code path can set the specimen flag.
"""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


site = _load("intl_gs_fixture_site", "tests/intl_gs_fixture_site.py")  # noqa: E402

EVALUATED_AT = "2026-10-09T20:30:00+00:00"
CHECKED_AT = "2026-10-09T15:00:00+00:00"
W2A_GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}


def synthetic_closes(tmp_path):
    """The W2FX synthetic frame recipe (tests/test_intl_gs_foundation.py),
    verbatim in shape: 280 business days ending 2026-10-07, one strictly
    positive monotone series per configured index/fx symbol."""
    import pandas as pd
    from engine import intl_inputs
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    series = []
    for cc, market in intl_inputs.countries().items():
        for symbol in (market["index"], market["fx"]):
            if symbol not in series:
                series.append(symbol)
    cols = {}
    for slot, symbol in enumerate(series):
        if symbol == "^AXJO":
            # R-03 (review r2): one admitted declining series, so a QUALIFIED
            # negative observation exists and the sign -> direction ink is
            # pinnable on the production variant (every other series rises).
            value = [float(200 - 0.0625 * i) for i in range(len(dates))]
        else:
            value = [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))]
        cols[symbol] = pd.Series(value, index=dates)
        path = tmp_path / "intl" / (
            symbol.replace("^", "_").replace("=", "_").replace("/", "_") + ".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"close": value}, index=dates).to_parquet(path)
    return pd.DataFrame(cols).sort_index(), series


def _run_status(tmp_path):
    (tmp_path / "run_status.json").write_text(json.dumps({"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok", "checked_at": CHECKED_AT,
        "last_date": "2026-10-07"}}}), encoding="utf-8")


def observation_set(tmp_path):
    """PRODUCTION VARIANT: an admitted X2 set over the synthetic closes (some
    markets qualify on every horizon, so the scanner rows are real)."""
    from lib.intl_eod_publication import build_eod_inputs
    from lib.intl_gs_observations import build_observation_set
    frame, _series = synthetic_closes(tmp_path)
    _run_status(tmp_path)
    selected, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED_AT, rights=W2A_GRANT)
    return build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=EVALUATED_AT,
        data_root=tmp_path, rights=W2A_GRANT)


def render_production_page(tmp_path=None):
    """intl.html with attach_surveillance over the synthetic admitted set."""
    from lib.intl_surveillance_mount import attach_surveillance
    from lib.intl_library_mount import render_international_pages
    own_tmp = tmp_path is None
    tmp_path = Path(tempfile.mkdtemp(prefix="intl-gs-w2a-obs-")) if own_tmp else Path(tmp_path)
    try:
        observations = observation_set(tmp_path)
        vm = site._vm()
        vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"],
                                                   observations=observations)
        catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
        pages = render_international_pages(site._env().get_template("intl.html.j2"), vm,
                                           catalogue=catalogue)
        return pages[0]
    finally:
        if own_tmp:
            import shutil
            shutil.rmtree(tmp_path, ignore_errors=True)


def render_page_with_observations(observations):
    """intl.html with attach_surveillance over a caller-built observation set."""
    import json as _json
    from lib.intl_surveillance_mount import attach_surveillance
    from lib.intl_library_mount import render_international_pages
    vm = site._vm()
    vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"], observations=observations)
    catalogue = _json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
    pages = render_international_pages(site._env().get_template("intl.html.j2"), vm,
                                       catalogue=catalogue)
    return pages[0]


def render_abstain_page():
    """observations=None — the foundation's own production variant."""
    return site.render_intl_page(include_surveillance=True, stub_coverage=False)


def _specimen_panel():
    """The spec §10.1 specimen rows as a scanner panel payload. Layout
    acceptance only (§16.3 S1/S2); fabricated specimen numbers live in THIS
    function and never in lib/ or templates/. Abstain copy strings come from
    the foundation vocabulary (imported, never copied)."""
    from lib.intl_gs_display import horizon_label, reason_copy

    def _abstain(token):
        return {"token": token, "reason": reason_copy(token)}
    en, zh = horizon_label("1m")

    def leg(value):
        return {"state": "complete", "pct": value, "reasons": [], "specimen": True}

    rows = [
        {"id": "BR", "name_en": "Brazil", "name_zh": "巴西", "selected": True,
         "local": leg(-4.2), "fx": leg(-2.8), "usd": leg(-6.9), "common": 18,
         "divz": -2.6, "spark": [12, 11, 13, 12, 10, 9, 11, 12, 14, 13, 11, 10, 12, 13, 12, 10, 9, 11, 12, 11],
         "tier": {"kind": "specimen", "label": ("T1", "T1"), "note": ("Delayed 15m", "延迟15分钟"),
                  "state": "complete"}, "stance": "get_ready",
         "market_sub": {"index_id": "B3", "currency": "BRL", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "TW", "name_en": "Taiwan", "name_zh": "台湾", "selected": False,
         "local": leg(2.4), "fx": leg(0.3), "usd": leg(2.7), "common": 48,
         "divz": 1.9, "spark": [8, 9, 10, 9, 11, 12, 11, 10, 12, 13, 12, 11, 13, 14, 13, 12, 13, 14, 13, 14],
         "tier": {"kind": "specimen", "label": ("Proxy", "代理"), "note": None, "state": "complete"},
         "stance": "watch", "market_sub": {"index_id": "TWSE", "currency": "TWD", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "KR", "name_en": "Korea", "name_zh": "韩国", "selected": False,
         "local": leg(-1.1), "fx": leg(-0.6), "usd": leg(-1.7), "common": 71,
         "divz": -0.6, "spark": [10, 11, 10, 12, 11, 12, 13, 12, 11, 10, 11, 12, 11, 10, 11, 12, 13, 12, 11, 10],
         "tier": {"kind": "specimen", "label": ("T2", "T2"), "note": None, "state": "complete"},
         "stance": "watch", "market_sub": {"index_id": "KRX", "currency": "KRW", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "MX", "name_en": "Mexico", "name_zh": "墨西哥", "selected": False,
         "local": leg(-0.7), "fx": leg(-1.5), "usd": leg(-2.2), "common": 41,
         "divz": -1.1, "spark": [13, 12, 13, 11, 12, 11, 10, 11, 12, 11, 10, 9, 10, 11, 10, 11, 12, 11, 10, 9],
         "tier": {"kind": "specimen", "label": ("T3", "T3"), "note": ("Delayed 15m", "延迟15分钟"),
                  "state": "complete"}, "stance": "watch",
         "market_sub": {"index_id": "BMV", "currency": "MXN", "clock": {"datetime": "2026-10-21", "en": "20 Oct 2026", "zh": "2026年10月20日"}}},
        {"id": "JP", "name_en": "Japan", "name_zh": "日本", "selected": False,
         "local": leg(1.8), "fx": leg(-0.9), "usd": leg(0.9), "common": 62,
         "divz": 0.4, "spark": [11, 12, 11, 12, 13, 12, 13, 14, 13, 12, 13, 12, 13, 14, 13, 12, 13, 14, 13, 12],
         "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                  "state": "complete"}, "stance": "watch",
         "market_sub": {"index_id": "JPX", "currency": "JPY", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "AU", "name_en": "Australia", "name_zh": "澳大利亚", "selected": False,
         "local": leg(0.6), "fx": leg(0.2), "usd": leg(0.8), "common": 55,
         "divz": 0.3, "spark": [12, 12, 13, 12, 11, 12, 13, 12, 11, 12, 13, 12, 11, 12, 13, 12, 11, 12, 11, 12],
         "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                  "state": "complete"}, "stance": "stand_aside",
         "market_sub": {"index_id": "ASX", "currency": "AUD", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "IN", "name_en": "India", "name_zh": "印度", "selected": False,
         "local": {"state": "qualified", "pct": 0.4, "reasons": [], "specimen": True},
         "fx": {"state": "qualified", "pct": -0.2, "reasons": [], "specimen": True},
         "usd": {"state": "qualified", "pct": 0.2, "reasons": [], "specimen": True},
         "common": 22, "divz": 0.2,
         "spark": [11, 11, 12, 11, 12, 11, 12, 11, 12, 11, 12, 11, 10, 11, 12, 11, 12, 11, 12, 11],
         "tier": {"kind": "specimen", "label": ("Qualified", "有条件"), "note": None, "state": "qualified"},
         "stance": "stand_aside", "market_sub": {"index_id": "NSE", "currency": "INR", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "ZA", "name_en": "South Africa", "name_zh": "南非", "selected": False,
         "local": {"state": "stale", "pct": 0.3, "reasons": [], "specimen": True},
         "fx": {"state": "stale", "pct": -0.4, "reasons": [], "specimen": True},
         "usd": {"state": "stale", "pct": -0.1, "reasons": [], "specimen": True},
         "common": 35, "divz": 0.1,
         "spark": [12, 11, 12, 13, 12, 11, 10, 11, 10, 9, 10, 11, 10, 9, 8, 9, 10, 9, 8, 9],
         "tier": {"kind": "specimen", "label": ("Stale · 2d", "过期 · 2天"), "note": None, "state": "stale"},
         "stance": "stand_aside", "market_sub": {"index_id": "JSE", "currency": "ZAR", "clock": {"datetime": "2026-10-21", "en": "20 Oct 2026", "zh": "2026年10月20日"}}},
        {"id": "PL", "name_en": "Poland", "name_zh": "波兰", "selected": False,
         "local": {"state": "abstain", "pct": None, "reasons": [], "specimen": True,
                   "specimen_reason": ("Unscored · insufficient history", "未评分 · 历史数据不足")},
         "fx": {"state": "abstain", "pct": None, "reasons": [], "specimen": True,
                "specimen_reason": ("Unscored · insufficient history", "未评分 · 历史数据不足")},
         "usd": {"state": "abstain", "pct": None, "reasons": [], "specimen": True,
                 "specimen_reason": ("Unscored · insufficient history", "未评分 · 历史数据不足")},
         "common": None, "divz": None, "spark": None,
         "tier": {"kind": "specimen", "label": ("Abstain", "弃权"), "note": None, "state": "abstain"},
         "stance": "stand_aside",
         "market_sub": {"index_id": "GPW", "currency": "PLN", "clock": {"datetime": "2026-10-21", "en": "20 Oct 2026", "zh": "2026年10月20日"}}},
    ]
    payload = {
        "specimen": True,
        "horizon": {"id": "1m", "en": en, "zh": zh},
        "basis": {"id": "usd_unhedged"},
        "counts": {"rows": 9, "qualified": 7, "abstain": 2, "nodata": 0, "up": 4},
        "kpi": [
            {"id": "breadth", "kind": "breadth", "up": 4, "qualified": 7,
             "sub": ("20D · baseline 50% breadth", "20日 · 基线50%广度"),
             "clock": ("as of 06:44 UTC", "截至 06:44 UTC"),
             "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                      "state": "complete"}},
            {"id": "largest", "kind": "move", "pct": -6.9, "ink": "down",
             "market": ("BR Ibovespa", "巴西 Ibovespa"),
             "local_pct": -4.2, "fx_pct": -2.8,
             "sub": ("B3 close 21 Oct", "B3 10月21日收盘"),
             "clock": ("21 Oct 08:00 UTC", "10月21日 08:00 UTC"),
             "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                      "state": "complete"}},
            {"id": "common_factor", "kind": "abstain", "token": "common_factor_unadmitted",
             "reason": reason_copy("common_factor_unadmitted")},
            {"id": "spread", "kind": "abstain", "token": "credit_funding_unadmitted",
             "reason": reason_copy("credit_funding_unadmitted")},
        ],
        "rows": rows,
        "nodata": {"count": 0, "markets": []},
        "session_copy": reason_copy("session_calendar_unadmitted"),
        "abstain": {
            "common": _abstain("common_factor_unadmitted"),
            "divergence": _abstain("divergence_unadmitted"),
            "series": _abstain("series_unadmitted"),
            "stance": _abstain("stance_unadmitted"),
            "attention": _abstain("attention_unadmitted"),
            "bands": [{"q": q, **_abstain(token)}
                      for q, token in ((3, "credit_funding_unadmitted"),
                                       (4, "transmission_unadmitted"),
                                       (5, "us_corroboration_unadmitted"),
                                       (6, "thesis_unadmitted"))],
        },
        "market_scope": [],
        "footnote": {"source": None,
                     "withheld_copy": ("Specimen values · not live", "示例数值 · 非实时"),
                     "delay": None},
    }
    return dict(view="scanner", context_id="im-gs-scanner-specimen",
                context={"horizon": "1m", "currency_basis": "usd_unhedged",
                         "return_basis": "price", "source_reference": None},
                generation=None, payload=payload)


def render_specimen_page():
    """The §10.1 specimen panel through the SAME scanner template, wrapped in
    the specimen chip (spec §16.3 S1/S2 layout acceptance only)."""
    from copy import deepcopy
    from lib.intl_gs_display import horizon_label, snapshot_display
    from lib.intl_library_mount import render_international_pages
    vm = site._vm()
    workspace = deepcopy(vm["intl_workspace"])
    raw = {"clocks": {"observation": "2026-10-07",
                      "source_publication": "2026-10-09T15:00:00+00:00",
                      "ingestion": "2026-10-09T15:00:00+00:00",
                      "computation": "2026-10-09T20:30:00+00:00"},
           "qualified": 35, "total": 35}
    withheld = {"clocks": {"observation": None, "source_publication": None,
                           "ingestion": None, "computation": None}, "qualified": 0, "total": 35}
    workspace["surveillance"] = {
        "views": {view: {"status": "available" if view == "scanner" else "not_built"}
                  for view in ("scanner", "dislocations", "transmission", "dossier",
                               "scenario", "replay", "coverage")},
        "universe": {},
        "observations": {"status": None, "source_reference": None, "counts": {}},
        "snapshot": snapshot_display({"local": raw, "usd_unhedged": dict(raw),
                                      "usd_hedged": withheld}),
        "horizon_labels": {
            horizon: {"en": en, "zh": zh}
            for horizon, (en, zh) in ((h, horizon_label(h))
                                      for h in workspace["config"]["horizons"])},
    }
    workspace["surveillance_panels"] = [_specimen_panel()]
    vm["intl_workspace"] = workspace
    catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
    pages = render_international_pages(site._env().get_template("intl.html.j2"), vm,
                                       catalogue=catalogue)
    return pages[0]


def write_site(out_dir):
    """Foundation site (no stub) + the three W2A variants."""
    copied = site.write_site(out_dir)  # intl.html (abstain), states page, assets
    out = Path(out_dir)
    (out / "intl.html").write_text(render_production_page(), encoding="utf-8")
    (out / "intl-abstain.html").write_text(render_abstain_page(), encoding="utf-8")
    (out / "intl-gs-scanner-specimen.html").write_text(render_specimen_page(), encoding="utf-8")
    return copied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write the W2A fixture site (production + abstain + specimen)")
    parser.add_argument("--print-html", action="store_true", help="print the production intl.html")
    parser.add_argument("--print-abstain", action="store_true", help="print the abstain-all intl.html")
    parser.add_argument("--print-specimen", action="store_true", help="print the specimen page")
    args = parser.parse_args(argv)
    if args.print_html:
        sys.stdout.write(render_production_page())
    if args.print_abstain:
        sys.stdout.write(render_abstain_page())
    if args.print_specimen:
        sys.stdout.write(render_specimen_page())
    if args.out:
        copied = write_site(args.out)
        print(f"wrote intl.html (production), intl-abstain.html, "
              f"intl-gs-scanner-specimen.html + {copied} assets", file=sys.stderr)
    if not (args.out or args.print_html or args.print_abstain or args.print_specimen):
        parser.error("nothing to do: pass --out and/or a --print-* flag")


if __name__ == "__main__":
    main()
