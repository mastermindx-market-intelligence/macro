#!/usr/bin/env python3
"""TEST-ONLY builder + site writer for the INTL-GS W4B Transmission board.

Specimen inputs, real IM17 engine calls: the synthetic scenario below composes
build_observation/build_edge/build_event/summarize_event/channel_rank_strip/
build_board exactly as an admitted live producer one day will, marks the
payload ``specimen``, and injects itself as ``lib.intl_gs_transmission_view``
through the W2 mount seam so the REAL templates render the board. This module
is a test fixture: it must never be imported by templates/, lib/ or scripts/,
nothing here is production code, and no data/ path is read.

CLI:
    python3 tests/intl_gs_transmission_fixture.py --out <dir>
    python3 tests/intl_gs_transmission_fixture.py --print-html
"""
import argparse
import json
import shutil
import sys
import types
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine.intl_transmission_evidence as te  # noqa: E402
from lib.intl_gs_transmission_present import present_transmission  # noqa: E402
from tests.intl_gs_fixture_site import _env, _vm  # noqa: E402
from tests.test_intl_transmission_evidence import (  # noqa: E402
    AS_OF,
    SESSIONS,
    ind,
    make_clocks,
    make_observation,
    resp,
    stress_block,
)
from lib.intl_library_mount import render_international_pages  # noqa: E402
from lib.intl_surveillance_mount import attach_surveillance  # noqa: E402

VIEW_MODULE = "lib.intl_gs_transmission_view"
CONTEXT_ID = "im-gs-transmission"

MARKET_IDS_DEFAULT = ["JP", "KR", "GB", "IN"]
MARKET_IDS_EXTRA = ["AU", "TW"]


# --------------------------------------------------------------------------
# The synthetic specimen scenario (real engine calls, invented values)
# --------------------------------------------------------------------------

def _observation(market, **clock_kw):
    return make_observation(market, clocks=make_clocks(**clock_kw) if clock_kw else None)


def _jp_edges(extra=0):
    def edge(**kw):
        return te.build_edge(**kw)

    base = [
        edge(origin_market="JP", receiver="us_funding", channel="dollar_funding",
             pathway="observed_source_stress", model_status="observed_qualified",
             source_id="bis.statistics", measure_id="cross_border_usd_claims",
             units="usd_bn",
             interpretation_en=("Qualified funding pressure observed at the "
                                "origin market."),
             interpretation_zh="在源头市场观测到的合格融资压力。",
             evidence_family="funding", coverage_state="qualified",
             coverage_basis="synthetic"),
        edge(origin_market="JP", receiver="us_funding", channel="dollar_funding",
             pathway="documented_exposure", model_status="documented_source",
             source_id="bis.statistics", measure_id="cross_border_usd_claims",
             units="usd_bn", as_of="2026-09-30", amount=210.4,
             denominator="reporting_bank_usd_claims",
             exposure_kind="direct_financial_claims",
             interpretation_en=("Cross-border USD claims of reporting banks "
                                "on the market."),
             interpretation_zh="报告银行对该市场的跨境美元债权。",
             evidence_family="funding"),
        edge(origin_market="JP", receiver="us_credit", channel="sovereign_banking",
             pathway="documented_exposure", model_status="documented_source",
             source_id="bis.statistics", measure_id="us_bank_consolidated_claims",
             units="usd_bn", as_of="2026-09-30", amount=96.2,
             denominator="us_reporting_bank_claims",
             exposure_kind="direct_financial_claims",
             interpretation_en="US banks' consolidated claims on the market.",
             interpretation_zh="美国银行对该市场的合并债权。",
             evidence_family="rates_credit"),
        edge(origin_market="JP", receiver="us_broad_equity",
             channel="portfolio_fund_ownership", pathway="documented_exposure",
             model_status="documented_source", source_id="us_treasury_tic",
             measure_id="us_holdings_of_securities", units="usd_bn",
             as_of="2026-06-30", amount=188.7,
             denominator="us_portfolio_holdings", exposure_kind="fund_holdings",
             interpretation_en=("US portfolio holdings of the market's "
                                "securities."),
             interpretation_zh="美国对该市场证券的组合持仓。",
             evidence_family="equity"),
        edge(origin_market="JP", receiver="us_broad_equity",
             channel="portfolio_fund_ownership", pathway="statistical_association",
             model_status="statistical_estimate_frozen",
             source_id="contagion_dy_var_14etf", measure_id="gfevd_to_us",
             units="share",
             interpretation_en=("Frozen fourteen-ETF connectedness estimate of "
                                "association with the US market."),
             interpretation_zh="冻结的十四只ETF关联度估计。",
             evidence_family="equity", direction="down",
             direction_support="statistical_candidate", coverage_state="qualified",
             coverage_basis="synthetic"),
        edge(origin_market="JP", receiver="us_broad_equity", channel="trade_earnings",
             pathway="documented_exposure", model_status="documented_source",
             source_id="licensed_global_feed.us_exposure",
             measure_id="us_company_revenue_from_market", units="percent_of_revenue",
             as_of="2026-09-30", amount=1.8, denominator="company_revenue",
             exposure_kind="operating_revenue",
             interpretation_en="US company revenue attributable to the market.",
             interpretation_zh="美国公司来自该市场的收入。",
             evidence_family="equity"),
        edge(origin_market="JP", receiver="us_credit",
             channel="commodity_terms_of_trade", pathway="documented_exposure",
             model_status="documented_source", source_id="usda_fas",
             measure_id="us_ag_trade_with_market", units="usd_bn",
             as_of="2026-09-30", amount=3.4, denominator="us_ag_trade",
             exposure_kind="production_import",
             interpretation_en="US agricultural trade with the market.",
             interpretation_zh="美国与该市场的农产品贸易金额。",
             evidence_family="commodity"),
        edge(origin_market="JP", receiver="us_funding", channel="leverage_liquidity",
             pathway="hypothetical_scenario",
             model_status="structural_prior_frozen", source_id="contagion_links",
             measure_id="structural_link_prior", units="prior",
             interpretation_en="Structural prior link under the frozen graph.",
             interpretation_zh="冻结图下的结构性先验联系。",
             evidence_family="rates_credit", coverage_state="qualified",
             coverage_basis="synthetic"),
    ]
    pool = [
        dict(origin_market="JP", receiver="us_funding", channel="dollar_funding",
             pathway="documented_exposure", model_status="documented_source",
             source_id="imf.data", measure_id="external_usd_debt", units="usd_bn",
             as_of="2026-06-30", amount=6.1, denominator="external_debt_stock",
             exposure_kind="direct_financial_claims",
             interpretation_en="External USD debt stock of the market.",
             interpretation_zh="该市场的对外美元债务存量。",
             evidence_family="funding"),
        dict(origin_market="JP", receiver="us_broad_equity", channel="trade_earnings",
             pathway="documented_exposure", model_status="documented_source",
             source_id="us_census_trade", measure_id="us_imports_from_market",
             units="usd_bn", as_of="2026-09-30", amount=14.6,
             denominator="us_total_imports", exposure_kind="production_import",
             interpretation_en="US imports of goods from the market.",
             interpretation_zh="美国自该市场进口的商品金额。",
             evidence_family="equity"),
        dict(origin_market="JP", receiver="us_credit",
             channel="commodity_terms_of_trade", pathway="hypothetical_scenario",
             model_status="scenario_assumption", source_id="contagion_links",
             measure_id="scenario_commodity_link", units="prior",
             interpretation_en="Scenario assumption link under stated assumptions.",
             interpretation_zh="在既定假设下的情景假设联系。",
             evidence_family="commodity", coverage_state="qualified",
             coverage_basis="synthetic"),
        dict(origin_market="JP", receiver="us_broad_equity",
             channel="portfolio_fund_ownership", pathway="hypothetical_scenario",
             model_status="scenario_assumption", source_id="contagion_links",
             measure_id="scenario_flow_link", units="prior",
             interpretation_en="Scenario assumption link under stated assumptions.",
             interpretation_zh="在既定假设下的情景假设联系。",
             evidence_family="equity", coverage_state="qualified",
             coverage_basis="synthetic"),
    ]
    wanted = len(base) + (extra or 0)
    full = base + [te.build_edge(**kw) for kw in pool]
    return full[:max(wanted, 0)] if extra else base


def _kr_edges():
    def edge(**kw):
        return te.build_edge(**kw)

    return [
        edge(origin_market="KR", receiver="us_funding", channel="dollar_funding",
             pathway="documented_exposure", model_status="documented_source",
             source_id="imf.data", measure_id="external_usd_debt", units="usd_bn",
             as_of="2026-06-30", amount=41.3, denominator="external_debt_stock",
             exposure_kind="direct_financial_claims",
             interpretation_en="External USD debt stock of the market.",
             interpretation_zh="该市场的对外美元债务存量。",
             evidence_family="funding"),
        edge(origin_market="KR", receiver="us_broad_equity",
             channel="portfolio_fund_ownership", pathway="documented_exposure",
             model_status="documented_source",
             source_id="ishares_ucits_holdings.legacy_configured_funds",
             measure_id="fund_constituent_weight", units="percent_of_fund",
             as_of="2026-09-30", amount=18.2, denominator="fund_net_assets",
             exposure_kind="fund_holdings",
             interpretation_en=("Constituent weight of the market inside the "
                                "configured funds."),
             interpretation_zh="已配置基金中该市场成份股权重。",
             evidence_family="equity"),
        edge(origin_market="KR", receiver="us_broad_equity", channel="trade_earnings",
             pathway="documented_exposure", model_status="documented_source",
             source_id="us_census_trade", measure_id="us_imports_from_market",
             units="usd_bn", as_of="2026-09-30", amount=22.9,
             denominator="us_total_imports", exposure_kind="production_import",
             interpretation_en="US imports of goods from the market.",
             interpretation_zh="美国自该市场进口的商品金额。",
             evidence_family="equity"),
    ]


def _gb_edges():
    def edge(**kw):
        return te.build_edge(**kw)

    return [
        edge(origin_market="GB", receiver="us_credit", channel="sovereign_banking",
             pathway="documented_exposure", model_status="documented_source",
             source_id="bis.statistics", measure_id="us_bank_consolidated_claims",
             units="usd_bn", as_of="2026-09-30", amount=121.5,
             denominator="us_reporting_bank_claims",
             exposure_kind="direct_financial_claims",
             interpretation_en="US banks' consolidated claims on the market.",
             interpretation_zh="美国银行对该市场的合并债权。",
             evidence_family="rates_credit"),
        edge(origin_market="GB", receiver="us_credit",
             channel="portfolio_fund_ownership", pathway="statistical_association",
             model_status="statistical_estimate_frozen",
             source_id="contagion_dy_var_14etf", measure_id="gfevd_to_us",
             units="share",
             interpretation_en=("Frozen fourteen-ETF connectedness estimate of "
                                "association with the US market."),
             interpretation_zh="冻结的十四只ETF关联度估计。",
             evidence_family="equity", direction="down",
             direction_support="statistical_candidate", coverage_state="qualified",
             coverage_basis="synthetic"),
    ]


def _one_edge(market, **kw):
    base = dict(origin_market=market, receiver="us_funding",
                channel="dollar_funding", pathway="observed_source_stress",
                model_status="observed_qualified", source_id="bis.statistics",
                measure_id="cross_border_usd_claims", units="usd_bn",
                interpretation_en="Qualified funding pressure observed at the origin market.",
                interpretation_zh="在源头市场观测到的合格融资压力。",
                evidence_family="funding", coverage_state="qualified",
                coverage_basis="synthetic")
    base.update(kw)
    return te.build_edge(**base)


_RANK_MEASURES = [
    ("JP", "dollar_funding", "bis.statistics", "cross_border_usd_claims",
     "usd_bn", "reporting_bank_usd_claims", 210.4),
    ("KR", "dollar_funding", "bis.statistics", "cross_border_usd_claims",
     "usd_bn", "reporting_bank_usd_claims", 87.6),
    ("GB", "dollar_funding", "bis.statistics", "cross_border_usd_claims",
     "usd_bn", "reporting_bank_usd_claims", 154.9),
    ("JP", "sovereign_banking", "bis.statistics", "us_bank_consolidated_claims",
     "usd_bn", "us_reporting_bank_claims", 96.2),
    ("KR", "sovereign_banking", "bis.statistics", "us_bank_consolidated_claims",
     "usd_bn", "us_reporting_bank_claims", 41.8),
    ("GB", "sovereign_banking", "bis.statistics", "us_bank_consolidated_claims",
     "usd_bn", "us_reporting_bank_claims", 121.5),
    ("JP", "portfolio_fund_ownership", "us_treasury_tic",
     "us_holdings_of_securities", "usd_bn", "us_portfolio_holdings", 188.7),
    ("KR", "portfolio_fund_ownership",
     "ishares_ucits_holdings.legacy_configured_funds", "fund_constituent_weight",
     "percent_of_fund", "fund_net_assets", 18.2),
    ("JP", "trade_earnings", "licensed_global_feed.us_exposure",
     "us_company_revenue_from_market", "percent_of_revenue", "company_revenue", 1.8),
    ("KR", "trade_earnings", "us_census_trade", "us_imports_from_market",
     "usd_bn", "us_total_imports", 22.9),
    ("JP", "commodity_terms_of_trade", "usda_fas", "us_ag_trade_with_market",
     "usd_bn", "us_ag_trade", 3.4),
]


def _measures():
    return [{"market_id": m, "channel": c, "source_id": s, "measure_id": mid,
             "units": u, "denominator": d, "value": v, "as_of": "2026-09-30"}
            for m, c, s, mid, u, d, v in _RANK_MEASURES]


def build_scenario(*, origins=None, edges_per_origin=None):
    """(payload_inputs, board_market_ids) for the synthetic scenario."""
    jp_edges = _jp_edges(extra=(edges_per_origin or 0) - 8
                         if edges_per_origin else 0)
    jp_obs = _observation("JP")
    jp_event = te.build_event(
        origin_observation=jp_obs,
        stress=stress_block(indicators=[
            ind("equity_index_return", "JP-IDX"),
            ind("sovereign_spread", "JP-CDS"),
            ind("usd_funding_spread", "JP-BASIS")], persistence=2),
        edges=jp_edges,
        responses=[resp(receiver="us_broad_equity", family="equity",
                        direction="down", wstart="2026-10-21T06:00:00Z",
                        wend="2026-10-21T20:00:00Z"),
                   resp(receiver="us_credit", family="rates_credit",
                        label="within_reference_range", direction=None,
                        wstart="2026-10-21T13:30:00Z",
                        wend="2026-10-21T20:00:00Z")],
        global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of=AS_OF)

    kr_obs = _observation("KR")
    kr_event = te.build_event(
        origin_observation=kr_obs,
        stress=stress_block(indicators=[ind("equity_index_return", "KR-IDX")]),
        edges=_kr_edges(),
        responses=[resp(receiver="us_broad_equity", family="equity",
                        label="within_reference_range", direction=None,
                        wstart="2026-10-21T06:00:00Z",
                        wend="2026-10-21T20:00:00Z")],
        global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of=AS_OF)

    gb_obs = _observation("GB", pub="2026-10-21T15:35:00Z",
                          ing="2026-10-21T15:40:00Z",
                          comp="2026-10-21T15:45:00Z")
    gb_event = te.build_event(
        origin_observation=gb_obs,
        stress=stress_block(indicators=[ind("fx_spot_return", "USDGBP")]),
        edges=_gb_edges(),
        responses=[resp(receiver="us_credit", family="rates_credit",
                        direction="down", wstart="2026-10-21T20:00:00Z",
                        wend="2026-10-22T20:00:00Z")],
        global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of=AS_OF)

    in_obs = _observation("IN")
    broken = deepcopy(in_obs["clocks"])
    broken["ingestion"]["at"] = "2026-10-20T00:00:00Z"
    in_obs["clocks"] = broken
    in_event = te.build_event(
        origin_observation=in_obs,
        stress=stress_block(indicators=[ind("equity_index_return", "IN-IDX")]),
        edges=[], responses=[], global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of=AS_OF)

    events = [jp_event, kr_event, gb_event, in_event]
    observations = [jp_obs, kr_obs, gb_obs, in_obs]
    all_edges = list(jp_edges) + _kr_edges() + _gb_edges()
    market_ids = list(MARKET_IDS_DEFAULT)

    if origins is not None and origins > 4:
        au_obs = _observation("AU")
        au_event = te.build_event(
            origin_observation=au_obs,
            stress=stress_block(indicators=[
                ind("equity_index_return", "AU-IDX")]),
            edges=[_one_edge("AU")], responses=[],
            global_factors=[], regional_stress=[],
            receiver_sessions=SESSIONS, as_of=AS_OF)
        tw_obs = _observation("TW")
        tw_event = te.build_event(
            origin_observation=tw_obs,
            stress=stress_block(
                indicators=[ind("constituent_breadth", "TW-BREADTH")],
                label="within_reference_range"),
            edges=[_one_edge("TW", pathway="documented_exposure",
                             model_status="documented_source",
                             receiver="us_credit",
                             channel="sovereign_banking",
                             measure_id="us_bank_consolidated_claims",
                             as_of="2026-09-30", amount=33.1,
                             denominator="us_reporting_bank_claims",
                             exposure_kind="direct_financial_claims",
                             interpretation_en="US banks' consolidated claims on the market.",
                             interpretation_zh="美国银行对该市场的合并债权。",
                             evidence_family="rates_credit")],
            responses=[], global_factors=[], regional_stress=[],
            receiver_sessions=SESSIONS, as_of=AS_OF)
        events += [au_event, tw_event]
        observations += [au_obs, tw_obs]
        all_edges += [_one_edge("AU")]
        market_ids += list(MARKET_IDS_EXTRA)

    market_ids.append("BR")  # out of the structural graph, no IM12 record
    board = te.build_board(market_ids=market_ids, edges=all_edges,
                           observations=observations, events=events,
                           as_of=AS_OF)
    summaries = {event["event_id"]: te.summarize_event(event)
                 for event in events}
    measures = _measures()
    strip_markets = [m for m in market_ids if m != "BR"]
    rank_strips = {market: te.channel_rank_strip(market, measures)
                   for market in strip_markets}
    return {"board": board, "events": events, "summaries": summaries,
            "rank_strips": rank_strips}, market_ids


def build_payload(*, specimen=True, origins=None, edges_per_origin=None,
                  selection=None):
    inputs, _market_ids = build_scenario(
        origins=origins, edges_per_origin=edges_per_origin)
    default_selection = {"origin_market": "JP",
                         "event_id": inputs["events"][0]["event_id"],
                         "edge_id": None}
    payload = dict(inputs)
    payload["selection"] = selection or default_selection
    payload["specimen"] = bool(specimen)
    return payload


# --------------------------------------------------------------------------
# W2 mount-seam injection (the production builder does not exist yet)
# --------------------------------------------------------------------------

def _view_module(payload):
    module = types.ModuleType(VIEW_MODULE)
    module.__doc__ = "Test-only transmission builder injected by the W4B fixture."

    def build_view(*, universe, rights, contexts, workspace,
                   observations=None):
        return [dict(view="transmission", context_id=CONTEXT_ID, context={},
                     generation=None,
                     payload=present_transmission(payload))]

    module.build_view = build_view
    return module


def attach_transmission(payload=None):
    """attach_surveillance with the test builder injected -> the workspace."""
    if payload is None:
        payload = build_payload()
    vm = _vm()
    sys.modules[VIEW_MODULE] = _view_module(payload)
    try:
        return attach_surveillance(vm["intl_workspace"])
    finally:
        sys.modules.pop(VIEW_MODULE, None)


def render_transmission_page(*, specimen=True, origins=None,
                             edges_per_origin=None, payload=None):
    """The REAL intl.html with the test-only transmission view available."""
    if payload is None:
        payload = build_payload(specimen=specimen, origins=origins,
                                edges_per_origin=edges_per_origin)
    vm = _vm()
    catalogue = json.loads(
        (ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
    sys.modules[VIEW_MODULE] = _view_module(payload)
    try:
        vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"])
        pages = render_international_pages(
            _env().get_template("intl.html.j2"), vm, catalogue=catalogue)
        return pages[0]
    finally:
        sys.modules.pop(VIEW_MODULE, None)


def write_site(out_dir, **render_kw):
    """<dir>/intl.html + the template assets, like the W2F fixture site."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "intl.html").write_text(
        render_transmission_page(**render_kw), encoding="utf-8")
    copied = 0
    for pattern in ("*.css", "*.js"):
        for asset in (ROOT / "templates").glob(pattern):
            shutil.copy2(asset, out / asset.name)
            copied += 1
    fonts = out / "fonts"
    fonts.mkdir(exist_ok=True)
    for font in (ROOT / "templates" / "fonts").glob("*.woff2"):
        shutil.copy2(font, fonts / font.name)
        copied += 1
    live_config = ROOT / "templates" / "live_config.js"
    if live_config.is_file():
        shutil.copy2(live_config, out / "live_config.js")
    else:
        (out / "live_config.js").write_text(
            "/* fixture stub: no live configuration on the evidence site */\n",
            encoding="utf-8")
    copied += 1
    return copied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write <out>/intl.html + template assets")
    parser.add_argument("--print-html", action="store_true",
                        help="print the rendered intl.html to stdout")
    parser.add_argument("--origins", type=int, default=None)
    parser.add_argument("--edges-per-origin", type=int, default=None)
    args = parser.parse_args(argv)
    rendered = False
    if args.print_html:
        sys.stdout.write(render_transmission_page(
            origins=args.origins, edges_per_origin=args.edges_per_origin))
        rendered = True
    if args.out:
        copied = write_site(args.out, origins=args.origins,
                            edges_per_origin=args.edges_per_origin)
        print(f"wrote {args.out}/intl.html + {copied} assets", file=sys.stderr)
        rendered = True
    if not rendered:
        parser.error("nothing to do: pass --out and/or --print-html")


if __name__ == "__main__":
    main()
