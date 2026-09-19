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
from collectors.sec_insider import parse_live_form4_submission


def test_official_sec_form4_parser_recovers_large_ceo_open_market_purchase():
    filing = """<SEC-DOCUMENT>
<ACCEPTANCE-DATETIME>20260814162715
ACCESSION NUMBER:        0000050863-26-000177
<ownershipDocument>
  <issuer><issuerCik>0000050863</issuerCik><issuerName>INTEL CORP</issuerName><issuerTradingSymbol>INTC</issuerTradingSymbol></issuer>
  <reportingOwner><reportingOwnerId><rptOwnerCik>0001008463</rptOwnerCik><rptOwnerName>TAN LIP BU</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>1</isOfficer><officerTitle>CEO</officerTitle></reportingOwnerRelationship></reportingOwner>
  <aff10b5One>0</aff10b5One>
  <nonDerivativeTable><nonDerivativeTransaction>
    <transactionDate><value>2026-08-11</value></transactionDate>
    <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>105263</value></transactionShares><transactionPricePerShare><value>95.00</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
    <postTransactionAmounts><sharesOwnedFollowingTransaction><value>1314669</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
    <ownershipNature><directOrIndirectOwnership><value>I</value></directOrIndirectOwnership><natureOfOwnership><value>by Family Trust</value></natureOfOwnership></ownershipNature>
  </nonDerivativeTransaction></nonDerivativeTable>
</ownershipDocument>"""
    rows = parse_live_form4_submission(
        filing,
        source_url="https://www.sec.gov/Archives/edgar/data/50863/0000050863-26-000177.txt",
        filed_date="2026-08-14",
        first_seen="2026-08-14T20:28:00+00:00",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["Ticker"] == "INTC"
    assert row["Name"] == "TAN LIP BU"
    assert row["officerTitle"] == "CEO"
    assert row["TransactionCode"] == "P"
    assert row["Shares"] * row["PricePerShare"] == 9_999_985
    assert row["fileDate"] == "2026-08-14T20:27:15+00:00"
    assert row["accession"] == "0000050863-26-000177"
    assert row["source"] == "sec_edgar_form4"
    assert row["provenance_class"] == "official_public_record"


def test_mixed_official_timestamp_shapes_do_not_drop_recovered_form4():
    # Historical timestamp shapes can coexist with the official SEC live rail. Pandas otherwise
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


def test_official_named_sponsorship_survives_to_user_brief_and_named_political_rows_do_not(monkeypatch):
    asof = pd.Timestamp("2026-08-25")
    congress = pd.DataFrame([
        {"Ticker": "INTC", "TransactionDate": "2026-07-24", "ReportDate": "2026-08-21",
         "Transaction": "Purchase", "Representative": "Example House Member", "BioGuideID": "X000001",
         "Party": "I", "House": "Representatives", "Range": "$500,001 - $1,000,000",
         "Amount": 500001.0, "Description": "PURCHASED 10,000 SHARES."},
    ])
    filing = """<SEC-DOCUMENT>
<ACCEPTANCE-DATETIME>20260814162715
ACCESSION NUMBER:        0000050863-26-000177
<ownershipDocument>
  <issuer><issuerCik>0000050863</issuerCik><issuerName>INTEL CORP</issuerName><issuerTradingSymbol>INTC</issuerTradingSymbol></issuer>
  <reportingOwner><reportingOwnerId><rptOwnerCik>0001008463</rptOwnerCik><rptOwnerName>TAN LIP BU</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>1</isOfficer><officerTitle>CEO</officerTitle></reportingOwnerRelationship></reportingOwner>
  <aff10b5One>0</aff10b5One>
  <nonDerivativeTable><nonDerivativeTransaction>
    <transactionDate><value>2026-08-11</value></transactionDate>
    <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
    <transactionAmounts><transactionShares><value>105263</value></transactionShares><transactionPricePerShare><value>95</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
    <postTransactionAmounts><sharesOwnedFollowingTransaction><value>1314669</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
    <ownershipNature><directOrIndirectOwnership><value>I</value></directOrIndirectOwnership><natureOfOwnership><value>by Family Trust</value></natureOfOwnership></ownershipNature>
  </nonDerivativeTransaction></nonDerivativeTable>
</ownershipDocument>"""
    ceo_buy = parse_live_form4_submission(
        filing,
        source_url="https://www.sec.gov/Archives/edgar/data/50863/0000050863-26-000177.txt",
        filed_date="2026-08-14",
        first_seen="2026-08-14T20:28:00+00:00",
    )[0]
    other_sale = {
        **ceo_buy, "Name": "OTHER OFFICER", "officerTitle": "EVP", "Date": "2026-08-12",
        "TransactionCode": "S", "Shares": 250000,
        "accession": "0000050863-26-000178", "transactionIndex": 0,
    }
    insiders = pd.DataFrame([ceo_buy, other_sale])

    monkeypatch.setattr(altdata, "_now", lambda: asof)
    monkeypatch.setattr(altdata, "_read", lambda ds: {"congress": congress, "insiders": insiders}.get(ds))
    signals = {
        "political": altdata.political_netflow(window_days=90, top=1),
        "insiders": altdata.insider_netflow(window_days=90, top=1),
    }

    monkeypatch.setattr(altdata_signals, "_write", lambda out: None)
    alt = altdata_signals.build({"as_of": "2026-08-25", "signals": signals})
    intc_alt = alt["tickers"]["INTC"]
    json.dumps(intc_alt, allow_nan=False)
    assert intc_alt["channels"] == ["congress_buy"]
    assert intc_alt["insider_net_usd"] < 0
    buy_event = next(e for e in intc_alt["sponsorship"]["insiders"] if e.get("side") == "buy")
    assert buy_event["actor"] == "TAN LIP BU" and buy_event["usd"] == 9_999_985
    assert buy_event["source"] == "sec_edgar_form4"
    assert buy_event["provenance_class"] == "official_public_record"
    assert "congress" not in intc_alt["sponsorship"]
    assert "Example House Member" not in json.dumps(intc_alt)

    bundle = intelligence.build({}, [], alt["tickers"], today=date(2026, 8, 25))
    assert bundle["tickers"]["INTC"]["alt"]["sponsorship"] == intc_alt["sponsorship"]

    discovery = intel_discovery.build(
        None, None, None, bundle_universe={"INTC"}, today=date(2026, 8, 25),
        fresh_insiders=insiders)
    disc = discovery["by_ticker"]["INTC"]
    assert disc["source"] == "top_officer_buy" and disc["actor"] == "TAN LIP BU"
    assert disc["off_desk"] is False and discovery["is_context_only"] is True
    assert disc["provenance_class"] == "official_public_record"

    sources = {
        "risk_state": {}, "us_standouts": {}, "subsector": {}, "sector_central": {},
        "screener": {}, "by_ticker": alt["tickers"],
        "insider": {"INTC": {"buyers": 1, "sellers": 1, "net_mn": -13.75, "bps": -0.2}},
        "smartmoney": {}, "baskets": {}, "membership": {}, "theme_lanes": {},
        "basket_lanes": {}, "congress": congress, "chain_state": {}, "stockdata": {},
        "washout_turn": {}, "dossier_index": set(),
    }
    ctx = build_ctx(sources, ["INTC"], "2026-08-25")
    ctx_buy = next(e for e in ctx["tickers"]["INTC"]["insider"]["events"] if e.get("side") == "buy")
    assert ctx_buy["actor"] == "TAN LIP BU"
    assert "actor" not in ctx["tickers"]["INTC"]["congress"][0]

    brief = compose_brief(
        ctx, [{"ticker": "INTC"}], "2026-08-25", "2026-08-25T21:00:00+00:00",
        population="positions")
    filings = next(section for section in brief["sections"] if section["key"] == "filings")
    english = [line["en"] for line in filings["lines"]]
    assert any("TAN LIP BU (CEO)" in line and "$9,999,985" in line for line in english)
    assert any("a Congress buy in INTC" in line for line in english)
    assert not any("Example House Member" in line for line in english)




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
