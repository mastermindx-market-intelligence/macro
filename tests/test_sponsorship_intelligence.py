"""End-to-end regression for named sponsorship intelligence on the existing pipeline."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import json

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from engine import altdata, altdata_signals, intel_discovery, intelligence
from scripts.build_portfolio_ctx import build_ctx
from engine.portfolio_brief import compose_brief


def test_mixed_quiver_timestamp_shapes_do_not_drop_recovered_form4():
    # The committed Quiver tape contains millisecond ISO strings while a date-scoped
    # catch-up response may carry a plain/offset ISO timestamp. Pandas otherwise
    # infers the first strict shape for the entire Series and turns the recovered
    # row into NaT, silently deleting exactly the historical hole we are repairing.
    mixed = pd.Series([
        "2026-08-03T20:48:47.000",
        "2026-08-14T20:27:00+00:00",
        "2026-08-15",
    ])
    parsed = altdata._dt_naive(mixed)
    assert parsed.notna().all()
    assert parsed.iloc[1] == pd.Timestamp("2026-08-14T20:27:00")


def test_top_officer_discovery_keeps_recovered_mixed_timestamp_row():
    insiders = pd.DataFrame([
        {"Ticker": "OLD", "Date": "2026-08-03T00:00:00.000", "Name": "Old Officer",
         "TransactionCode": "S", "Shares": 1000, "PricePerShare": 10,
         "fileDate": "2026-08-03T20:48:47.000", "officerTitle": "EVP"},
        {"Ticker": "INTC", "Date": "2026-08-11", "Name": "Lip-Bu Tan",
         "TransactionCode": "P", "Shares": 105263, "PricePerShare": 95,
         "fileDate": "2026-08-14T20:27:00+00:00",
         "officerTitle": "Chief Executive Officer",
         "isOfficer": True, "isDirector": True},
    ])

    rows = intel_discovery.scan_top_officer_buys(
        insiders, today=date(2026, 8, 25), recent_days=45, min_usd=250_000)
    intc = next(r for r in rows if r["ticker"] == "INTC")
    assert intc["actor"] == "Lip-Bu Tan"
    assert intc["usd"] == 9_999_985
    assert intc["filing_date"] == "2026-08-14"
    assert intc["trans_date"] == "2026-08-11"
    assert intc["ranking_eligible"] is False
    assert intc["qualification_status"] == "measuring"


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



def test_measuring_top_officer_discovery_renders_without_numeric_score():
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(str(root / "templates")),
                      autoescape=select_autoescape(["html", "xml"]))
    env.globals["region_for"] = lambda sym: "us"
    cand = {"ticker": "INTC", "price": 95.0, "discovery": {
        "source": "top_officer_buy", "disc_score": 0.45,
        "ranking_eligible": False, "qualification_status": "measuring",
        "off_desk": False, "reason": "CEO open-market buy $9,999,985",
    }}
    hub = {
        "command": [], "emerging": [], "discovery": [cand], "exhausted": [],
        "catalysts": [], "track_record": None, "desk_grader": {}, "sector_heat": [],
        "disclaimer": "", "n_universe": 1, "macro_context": {}, "desks": {},
        "as_of": "2026-08-25", "counts": {}, "n_actionable": 0,
        "n_emerging": 0, "n_discovery": 1,
    }
    html = env.get_template("intelligence_hub.html.j2").render(
        hub=hub, built="2026-08-25T21:00:00+00:00", mode="intel_hub",
        qledger_chips={}, china=None, market_pulse_roster=[])
    assert "top officer buy" in html
    assert ">measuring<" in html
    assert "Measuring only — not used in Command ranking" in html
    # The heuristic 0.45 strength is an ordering aid while measuring; it must not be
    # rendered as the normal Discovery numeric score.
    card = html.split('class="card ecard dcard"', 1)[1].split('</div>', 4)
    assert 'class="dscore">45' not in "</div>".join(card)
