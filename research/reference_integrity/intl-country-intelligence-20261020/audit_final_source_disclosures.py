"""Verify rendered source disclosures against the actual complete-input build model."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, os, sys
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[3]
RIG = Path(__file__).resolve().parent
BUILD = Path("/tmp/intl-rig-review-repair-20261020/final/source")
receipt = json.loads((RIG / "repair_final_build_receipt.json").read_text())
assert receipt["exit_code"] == 0 and not receipt["source_overlays"]
html = RIG / "proposed_final_repair/intl.html"
assert sha256(html.read_bytes()).hexdigest() == receipt["html_sha256"]
sys.path.insert(0, str(BUILD))
os.chdir(BUILD)
from lib import config
from lib.intl_country_inputs import load_country_inputs, load_stored_country_observations
from lib.intl_country_assessment import build_country_assessments
day = datetime.fromisoformat(receipt["started_at"]).date()
data = config.data_dir()
inputs = load_country_inputs(data, BUILD)
latest = json.loads((data / "intl/latest.json").read_text())
stored = load_stored_country_observations(data, config.load().get("intl") or {}, today=day)
model = build_country_assessments(latest, today=day, stored_observations=stored,
    official=inputs.get("official"), forecasts=inputs.get("forecasts"), commentary=inputs.get("commentary"),
    forecast_archive=inputs.get("forecast_archive"), policy_decisions=inputs.get("policy_decisions"),
    policy_reviews=inputs.get("policy_reviews"))
soup = BeautifulSoup(html.read_text(), "html.parser")
checks, countries = [], []
def check(identifier, passed, actual=None):
    checks.append({"id":identifier,"passed":bool(passed),"actual":actual})
def table_rows(node):
    return [[td.get_text(" ",strip=True) for td in tr.select("td")] for tr in node.select("tbody tr")]
for country in model["countries"]:
    cc = country["cc"]
    node = soup.select_one("#imc-country-" + cc)
    metrics = {m["key"]:m for m in country["metrics"]}
    gdp = metrics["gdp"]
    eq = country["market"]["equity_evidence"]
    check(cc+"-country-rendered", node is not None)
    if node is None:
        continue
    check(cc+"-gdp-source-link", bool(gdp["source_url"]) and any(a.get("href")==gdp["source_url"] for a in node.select(".imc-evidence a")))
    for m in metrics.values():
        e = m["evidence"]
        if not e:
            continue
        block = node.select_one(".imc-macro-inputs[data-metric='"+m["key"]+"']")
        rows = table_rows(block) if block else []
        expected = [[p["date"],str(p["value"])] for p in e["observations"]]
        check(cc+"-"+m["key"]+"-raw-inputs", rows==expected, {"rendered":rows,"expected":expected})
        text = block.get_text(" ",strip=True) if block else ""
        check(cc+"-"+m["key"]+"-identity", all(v in text for v in [e["series_id"],e["native_unit"],e["geography"],m["period_end"]]))
        check(cc+"-"+m["key"]+"-no-invented-vintage", e["retrieved_at"] is None and e["vintage_custody"]=="not_recorded")
    check(cc+"-equity-admitted", eq is not None)
    if eq:
        block = node.select_one(".imc-equity-evidence")
        links = [a.get("href") for a in block.select("a")] if block else []
        check(cc+"-equity-identity", eq["source"]["source_url"] in links and eq["source"]["symbol"] in block.get_text(" ",strip=True))
        raw = block.select_one(".imc-equity-rows") if block else None
        rows = table_rows(raw) if raw else []
        expected = [[row[0],str(row[1])] for row in eq["rows"]]
        check(cc+"-equity-raw-inputs", rows==expected, {"rendered_count":len(rows),"expected_count":len(expected),"first":rows[0] if rows else None,"last":rows[-1] if rows else None})
        window_table = block.select_one(":scope > .imc-table-wrap") if block else None
        windows = table_rows(window_table) if window_table else []
        expected_windows = [[format(eq[key]["value"],".8g") if eq[key]["value"] is not None else "—", str(eq[key]["observations"]),eq[key]["start"]+" → "+eq[key]["end"]] for key in ["mean_50","mean_200","recent_high"]]
        check(cc+"-equity-windows", [r[1:] for r in windows]==expected_windows, {"rendered":windows,"expected_values":expected_windows})
        check(cc+"-equity-no-invented-vintage", eq["retrieved_at"] is None and eq["vintage_custody"]=="not_recorded" and eq["session_finality"]=="not_verified")
    countries.append({"cc":cc,"gdp":{k:gdp[k] for k in ["value","period","period_end","source","source_url","quality"]},
        "gdp_calculated":bool(gdp["evidence"]),"unemployment":{k:metrics["unemployment"][k] for k in ["value","period","source","source_url","quality"]},
        "equity":{"state":country["market"]["state"],"as_of":country["market"]["as_of"],"source":eq["source"] if eq else None,"observations":len(eq["rows"]) if eq else 0},
        "currency_available":country["market"]["currency_observation"]["available"]})
check("seven-countries",len(countries)==7)
check("five-calculated-gdp",sum(c["gdp_calculated"] for c in countries)==5)
check("legacy-generic-source-removed","Existing international macro series" not in soup.select_one(".imc").get_text(" ",strip=True))
result={"recorded_at":datetime.now(timezone.utc).isoformat(),"source_commit":receipt["source_commit"],
    "html_sha256":receipt["html_sha256"],"evaluation_day":day.isoformat(),"checks":checks,"countries":countries,
    "passed":sum(c["passed"] for c in checks),"failed":sum(not c["passed"] for c in checks),
    "limits":["Stored input snapshot was copied without source reacquisition.","This audit compares the actual build model and rendered evidence, not authenticated access or production adoption."]}
for name,value in [("final_country_model.json",model),("final_source_disclosure_audit.json",result)]:
    path = RIG / name
    assert not path.exists()
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="checks"},ensure_ascii=False))
print(json.dumps({"failed_checks":[c for c in checks if not c["passed"]]},ensure_ascii=False))
raise SystemExit(bool(result["failed"]))
