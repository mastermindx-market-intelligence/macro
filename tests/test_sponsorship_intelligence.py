"""End-to-end regression for named sponsorship intelligence on the existing pipeline."""
from __future__ import annotations

from datetime import date
import json

import pandas as pd

from engine import altdata, altdata_signals, intel_discovery, intelligence
from scripts.build_portfolio_ctx import build_ctx
from engine.portfolio_brief import compose_brief


def test_intel_style_named_sponsorship_survives_to_user_brief(monkeypatch):
    asof = pd.Timestamp("2026-08-25")
    congress = pd.DataFrame([
        {"Ticker": "INTC", "TransactionDate": "2026-07-24", "ReportDate": "2026-08-21",
         "Transaction": "Purchase", "Representative": "Nancy Pelosi", "BioGuideID": "P000197",
         "Party": "D", "House": "Representatives", "Range": "$500,001 - $1,000,000",
         "Amount": 500001.0, "Description": "PURCHASED 10,000 SHARES."},
    ])
    insiders = pd.DataFrame([
        {"Ticker": "INTC", "Date": "2026-08-11", "Name": "Lip-Bu Tan",
         "TransactionCode": "P", "Shares": 105263, "PricePerShare": 95,
         "fileDate": "2026-08-14", "officerTitle": "Chief Executive Officer",
         "isOfficer": True, "isDirector": True, "directOrIndirectOwnership": "I"},
        # A larger unrelated sale makes aggregate insider flow negative.  The CEO buy is
        # still a public fact and must survive even though it earns no bullish insider vote.
        {"Ticker": "INTC", "Date": "2026-08-12", "Name": "Other Officer",
         "TransactionCode": "S", "Shares": 250000, "PricePerShare": 95,
         "fileDate": "2026-08-14", "officerTitle": "EVP",
         "isOfficer": True, "isDirector": False, "directOrIndirectOwnership": "D"},
    ])

    monkeypatch.setattr(altdata, "_now", lambda: asof)
    monkeypatch.setattr(altdata, "_read", lambda ds: {
        "congress": congress, "insiders": insiders}.get(ds))
    political = altdata.political_netflow(window_days=90, top=1)
    insider = altdata.insider_netflow(window_days=90, top=1)
    signals = {"political": political, "insiders": insider}

    monkeypatch.setattr(altdata_signals, "_write", lambda out: None)
    alt = altdata_signals.build({"as_of": "2026-08-25", "signals": signals})
    intc_alt = alt["tickers"]["INTC"]
    json.dumps(intc_alt, allow_nan=False)  # publication payload must be strict JSON
    assert intc_alt["channels"] == ["congress_buy"]
    assert intc_alt["insider_net_usd"] < 0
    buy_event = next(e for e in intc_alt["sponsorship"]["insiders"] if e.get("side") == "buy")
    assert buy_event["actor"] == "Lip-Bu Tan" and buy_event["usd"] == 9_999_985
    assert intc_alt["sponsorship"]["congress"][0]["actor"] == "Nancy Pelosi"

    bundle = intelligence.build({}, [], alt["tickers"], today=date(2026, 8, 25))
    assert bundle["tickers"]["INTC"]["alt"]["sponsorship"] == intc_alt["sponsorship"]

    discovery = intel_discovery.build(
        None, None, None, bundle_universe={"INTC"}, today=date(2026, 8, 25),
        fresh_insiders=insiders)
    disc = discovery["by_ticker"]["INTC"]
    assert disc["source"] == "top_officer_buy" and disc["actor"] == "Lip-Bu Tan"
    assert disc["off_desk"] is False and discovery["is_context_only"] is True

    sources = {
        "risk_state": {}, "us_standouts": {}, "subsector": {}, "sector_central": {},
        "screener": {}, "by_ticker": alt["tickers"],
        "insider": {"INTC": {"buyers": 1, "sellers": 1, "net_mn": -13.75, "bps": -0.2}},
        "smartmoney": {}, "baskets": {}, "membership": {}, "theme_lanes": {},
        "basket_lanes": {}, "congress": congress, "chain_state": {}, "stockdata": {},
        "washout_turn": {}, "dossier_index": set(),
    }
    ctx = build_ctx(sources, ["INTC"], "2026-08-25")
    ctx_buy = next(e for e in ctx["tickers"]["INTC"]["insider"]["events"]
                   if e.get("side") == "buy")
    assert ctx_buy["actor"] == "Lip-Bu Tan"
    assert ctx["tickers"]["INTC"]["congress"][0]["actor"] == "Nancy Pelosi"

    brief = compose_brief(
        ctx, [{"ticker": "INTC"}], "2026-08-25", "2026-08-25T21:00:00+00:00",
        population="positions")
    filings = next(section for section in brief["sections"] if section["key"] == "filings")
    english = [line["en"] for line in filings["lines"]]
    assert any("Lip-Bu Tan (Chief Executive Officer)" in line and "$9,999,985" in line
               for line in english)
    assert any("Congress disclosure: Nancy Pelosi" in line and "$500,001 - $1,000,000" in line
               for line in english)
