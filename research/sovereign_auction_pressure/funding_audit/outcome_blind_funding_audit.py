"""Reproduce bounded October 6 funding-source accounting without market outcomes.

Only local captured source bytes are read. No imports fetch, no data collectors
are executed, and no private-cash completeness assertion is created. Requires
the installed pdftotext command for the source PDF's explicit cash-basis bridge.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
# The attended scratch capture and the canonical repository evidence bundle use
# different, documented sibling names. Neither path is a network fallback.
SOURCE_ROOT = WORKSPACE / ("research_source" if (WORKSPACE / "research_source").is_dir() else "source_audit")
DATE = "2026-10-06"
USD_PER_MILLION = Decimal("1000000")
S_MINUS_ONE = datetime(2026,10,5,16,tzinfo=ZoneInfo("America/New_York"))

def aware(value):
    d = datetime.fromisoformat(value.replace("Z","+00:00"))
    if d.utcoffset() is None: raise ValueError("aware receipt clock required")
    return d

def exact(value):
    if value is None or (isinstance(value,str) and value.strip().lower() in ("","null","none","nan")):
        return None
    if isinstance(value,bool): raise ValueError("bool is not a monetary value")
    number = Decimal(str(value))
    if not number.is_finite(): raise ValueError("nonfinite source amount")
    return number

def sum_known(values):
    parsed = [exact(v) for v in values]
    if not parsed or any(v is None for v in parsed): return None
    with localcontext() as context:
        context.prec = max(50, sum(len(v.as_tuple().digits) for v in parsed)+20)
        return sum(parsed,Decimal(0))

def fmt(value): return None if value is None else format(value,"f")

def qualified_document(document,field):
    if document["meta"]["dataFormats"][field] != "$1,000,000":
        raise ValueError("source monetary unit must be explicit USD millions")
    rows = document["data"]
    if any(r["record_date"] != DATE for r in rows): raise ValueError("mixed record dates")
    if document["meta"]["total-pages"] != 1 or document["meta"]["total-count"] != len(rows) or document["links"]["next"] is not None:
        raise ValueError("queried source slice incomplete")
    return rows

def load_sources():
    receipts = json.loads((ROOT / "SOURCE_RECEIPTS.json").read_text())
    if len(receipts) != 12: raise ValueError("expected original twelve captured requests")
    sources = {}
    for receipt in receipts:
        path = ROOT / receipt["file"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != receipt["sha256"] or len(raw) != receipt["bytes"]:
            raise ValueError("source bytes differ from original receipt: "+str(path))
        if receipt["status"] != 200: raise ValueError("source request did not succeed")
        if not aware(receipt["request_started_at"]) <= aware(receipt["body_received_at"]) <= aware(receipt["verified_present_at"]):
            raise ValueError("receipt clocks not causal")
        source_id = path.stem
        sources[source_id] = {**receipt,"source_id":source_id,"hash_verified":True,
            "known_at_upper_bound":receipt["verified_present_at"],
            "known_at_basis":"original verified local file availability; retrospective capture, not publication",
            "eligible_s_minus_one":aware(receipt["verified_present_at"]) <= S_MINUS_ONE,
            "historical_first_release_verified":False}
    return sources

def single(rows,predicate):
    found = [r for r in rows if predicate(r)]
    if len(found) != 1: raise ValueError("expected one uniquely identified source row")
    return found[0]

def sourced_value(row,field,source_id,row_index):
    return {"value":fmt(exact(row[field])),"unit":"USD_MILLION","currency":"USD",
            "source_id":source_id,"locator":f"data[{row_index}].{field}","record_date":row["record_date"],
            "src_line_nbr":row["src_line_nbr"]}

def pdf_number(text,label):
    for line in text.splitlines():
        if label in line:
            matched = re.search(re.escape(label)+r"\s+\$?\s*([\d,]+)",line)
            if matched: return Decimal(matched.group(1).replace(",",""))
    raise ValueError("PDF cash-basis source line not found: "+label)

def build_casebook():
    sources = load_sources()
    cashdoc = json.loads((ROOT / sources["dts_oct6_cash"]["file"]).read_text())
    debtdoc = json.loads((ROOT / sources["dts_oct6_marketable"]["file"]).read_text())
    cashrows = qualified_document(cashdoc,"open_today_bal")
    debtrows = qualified_document(debtdoc,"transaction_today_amt")
    labels = {"opening":"Treasury General Account (TGA) Opening Balance",
              "deposits":"Total TGA Deposits (Table II)",
              "withdrawals":"Total TGA Withdrawals (Table II) (-)",
              "closing":"Treasury General Account (TGA) Closing Balance"}
    tga = {}
    for key,label in labels.items():
        row = single(cashrows,lambda r:r["account_type"]==label)
        tga[key] = sourced_value(row,"open_today_bal","dts_oct6_cash",cashrows.index(row))
    tga_values = {k:Decimal(v["value"]) for k,v in tga.items()}
    reconstructed = tga_values["opening"]+tga_values["deposits"]-tga_values["withdrawals"]
    if reconstructed != tga_values["closing"]: raise ValueError("TGA arithmetic does not reconcile")
    delta = tga_values["closing"]-tga_values["opening"]
    if any(r["security_market"] != "Marketable" for r in debtrows): raise ValueError("mixed marketability")
    issues = sum_known(r["transaction_today_amt"] for r in debtrows if r["transaction_type"]=="Issues")
    redemptions = sum_known(r["transaction_today_amt"] for r in debtrows if r["transaction_type"]=="Redemptions")
    bills_i = single(debtrows,lambda r:r["transaction_type"]=="Issues" and r["security_type"]=="Bills" and r["security_type_desc"]=="Regular Series")
    bills_r = single(debtrows,lambda r:r["transaction_type"]=="Redemptions" and r["security_type"]=="Bills")
    increment = single(debtrows,lambda r:r["transaction_type"]=="Issues" and r["security_type"]=="Inflation-Protected Securities Increment")
    regular_bills = exact(bills_i["transaction_today_amt"])-exact(bills_r["transaction_today_amt"])
    debt_net = issues-redemptions
    increment_value = exact(increment["transaction_today_amt"])
    pdf = subprocess.run(["pdftotext","-layout",str(ROOT / sources["dts_oct6"]["file"]),"-"],check=True,capture_output=True,text=True).stdout
    if "available by 4:00 p.m. the following business day" not in pdf:
        raise ValueError("DTS publication-policy note not present in inspected PDF")
    discount = pdf_number(pdf,"Bills (-)")
    total_cash_issues = pdf_number(pdf,"Deposited in TGA")
    total_cash_redemptions = pdf_number(pdf,"Withdrawn from TGA")
    adjusted_market_net = debt_net-increment_value-discount
    bridge = {"source_id":"dts_oct6","locator":"PDF page 3, Table IIIB: Today column",
              "bill_issue_discount_usd_million":fmt(discount),
              "tips_principal_increment_removed_usd_million":fmt(increment_value),
              "restricted_marketable_cash_basis_bridge_usd_million":fmt(adjusted_market_net),
              "formula":"marketable Table IIIA Issues - Redemptions - TIPS principal increment - Bill new-issue discount",
              "classification":"bounded accounting adjustment inference; not private cash certification",
              "total_public_debt_cash_issues_usd_million":fmt(total_cash_issues),
              "total_public_debt_cash_redemptions_usd_million":fmt(total_cash_redemptions),
              "total_public_debt_cash_net_usd_million":fmt(total_cash_issues-total_cash_redemptions),
              "total_cash_scope":"Table IIIB all public-debt cash, including nonmarketable categories; not the selected marketable or private cohort"}
    # Original auction source has no independently recorded receive clock; preserve
    # its conservative verified-present bound without relabeling it body receipt.
    auction_receipts=json.loads((SOURCE_ROOT/"casebook_fetch_manifest.json").read_text())
    auction_receipt=single(auction_receipts,lambda r:r["source"]=="treasury_october_search")
    auction_raw=(SOURCE_ROOT/"raw/treasury_october_search.json").read_bytes()
    if hashlib.sha256(auction_raw).hexdigest()!=auction_receipt["sha256"]: raise ValueError("auction source digest mismatch")
    auction_rows=json.loads(auction_raw)
    auction=single(auction_rows,lambda r:r["cusip"]=="912797VP9" and r["auctionDate"].startswith("2026-10-01"))
    if auction != json.loads((SOURCE_ROOT/"fixtures/bill_october_completed.json").read_text()):
        raise ValueError("auction fixture differs from captured source row")
    linked={"episode_id":"auction:912797VP9:2026-10-01","cusip":auction["cusip"],"auction_date":auction["auctionDate"][:10],
            "issue_date":auction["issueDate"][:10],"competitive_deadline_raw":auction["closingTimeCompetitive"],
            "source":auction_receipt,"row_index":auction_rows.index(auction),
            "funding_link":"same reported issue date only; aggregate DTS is a separate accounting observation",
            "individual_settled_payment_observed":None,"net_private_cash_usd":None}
    first=json.loads((ROOT/"raw/tgcr_first_week.json").read_text())["refRates"]
    latest=json.loads((ROOT/"raw/nyfed_latest_rates.json").read_text(),parse_float=Decimal)["refRates"]
    rate_samples=[{"type":r["type"],"effective_date":r["effectiveDate"],"revision_indicator":r["revisionIndicator"],
                   "rate_unit":"PERCENT" if "percentRate" in r else "SOFR_AVERAGE_PERCENT_AND_INDEX",
                   "volume_unit":"USD_BILLION" if "volumeInBillions" in r else None} for r in latest]
    oldest=json.loads((ROOT/"raw/dts_tga_earliest.json").read_text())["data"][0]
    newest=json.loads((ROOT/"raw/dts_tga_latest.json").read_text())["data"][0]
    missing_mutation=copy.deepcopy(debtrows); missing_mutation[0]["transaction_today_amt"]="null"
    missing_issue_sum=sum_known(r["transaction_today_amt"] for r in missing_mutation if r["transaction_type"]=="Issues")
    if missing_issue_sum is not None or sum_known(["0"])!=0: raise ValueError("missingness contract failed")
    return {"schema_version":"outcome_blind_funding_feasibility_v1","research_owner":"existing sovereign auction / Macro research owner",
      "analysis_scope":"official-source accounting and input feasibility only; no market outcomes or forecasting",
      "record_date":DATE,"sources":sources,
      "decision_cutoff_s_minus_one":S_MINUS_ONE.isoformat(),"all_new_sources_s_minus_one_eligible":all(s["eligible_s_minus_one"] for s in sources.values()),
      "s_minus_one_status":"NOT_TESTABLE_FROM_RETROSPECTIVE_RECEIPTS",
      "tga":{"inputs":tga,"reconstructed_closing_usd_million":fmt(reconstructed),"reconciliation_difference_usd_million":fmt(reconstructed-tga_values["closing"]),
             "delta_usd_million":fmt(delta),"delta_usd":fmt(delta*USD_PER_MILLION),"reserve_pressure":None},
      "marketable_debt_accounting":{"source_id":"dts_oct6_marketable","complete_queried_slice":True,"complete_private_cash_ledger":False,
        "rows":[{**r,"source_locator":f"data[{i}].transaction_today_amt"} for i,r in enumerate(debtrows)],
        "issues_usd_million":fmt(issues),"redemptions_usd_million":fmt(redemptions),"issues_minus_redemptions_usd_million":fmt(debt_net),
        "regular_bill_issues_minus_redemptions_usd_million":fmt(regular_bills),"tips_principal_increment_usd_million":fmt(increment_value),
        "classification":"Table IIIA face/debt accounting, not certified private cash"},
      "cash_basis_bridge":bridge,"auction_lifecycle_link":linked,
      "private_cash":{"status":"NOT_COMPUTABLE","net_private_cash_usd":None,"private_proceeds_ex_soma_usd":None,
        "private_marketable_redemptions_usd":None,"funded_buyback_cash_outlays_usd":None,"completeness_certified":False,"reserve_pressure":None,
        "null_reasons":["no complete same-cohort private proceeds excluding SOMA","no complete private cash redemption ledger","no funded buyback cash inventory or sourced explicit zero","no source-qualified PIT ledger known at S-1"]},
      "sampled_coverage":{"dts_ascending_one_row":{"record_date":oldest["record_date"],"account_type":oldest["account_type"],"selected_balance_field":"close_today_bal"},
        "dts_descending_one_row":{"record_date":newest["record_date"],"account_type":newest["account_type"],"selected_balance_field":"open_today_bal","scope":"one opening row, not latest complete TGA day"},
        "tgcr":{"first_sampled_effective_date":min(r["effectiveDate"] for r in first),"last_first_week_sampled_date":max(r["effectiveDate"] for r in first),"sampled_rows":len(first),"full_intervening_history_audited":False},
        "latest_reference_rate_rows":rate_samples,"full_history_or_initial_vintages_certified":False},
      "adversarial_contract_checks":{"synthetic_missing_bill_issue_total":fmt(missing_issue_sum),"explicit_observed_zero":fmt(sum_known(["0"])),
        "missing_category_total":fmt(sum_known([])),"unknown_replaced_with_zero":False},
      "gates":{"SLF006":"NO-GO preserved","D2":"FAIL preserved","Terminal":"KILL preserved","risk_authority":False,"exit_authority":False,"deploy_authority":False,"probability_authority":False}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"OUTCOME_BLIND_FUNDING_CASEBOOK.json")
    parser.add_argument("--check",action="store_true",help="recompute and compare without writing")
    args=parser.parse_args()
    casebook=build_casebook()
    raw=json.dumps(casebook,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+"\n"
    if args.check:
        if args.output.read_text()!=raw: raise ValueError("casebook differs from exact recomputation")
    else: args.output.write_text(raw)
    print(json.dumps({"output":str(args.output),"sha256":hashlib.sha256(raw.encode()).hexdigest(),"source_hashes_verified":len(casebook["sources"]),
      "tga_delta_usd_million":casebook["tga"]["delta_usd_million"],"marketable_debt_net_usd_million":casebook["marketable_debt_accounting"]["issues_minus_redemptions_usd_million"],
      "net_private_cash_usd":None,"s_minus_one_eligible":False,"check_only":args.check},indent=2))

if __name__=="__main__": main()
