"""Resolve two unavailable-GDP audit assumptions without rewriting the failed receipt."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
from bs4 import BeautifulSoup
RIG = Path(__file__).resolve().parent
prior_path = RIG / "final_source_disclosure_audit.json"
prior = json.loads(prior_path.read_text())
model = json.loads((RIG / "final_country_model.json").read_text())
html_path = RIG / "proposed_final_repair/intl.html"
assert sha256(html_path.read_bytes()).hexdigest() == prior["html_sha256"]
assert prior["passed"] == 80 and prior["failed"] == 2
assert {c["id"] for c in prior["checks"] if not c["passed"]} == {"TW-gdp-source-link", "IN-gdp-source-link"}
soups = {name:BeautifulSoup((RIG/path).read_text(), "html.parser") for name,path in
    [("original","proposed/intl.html"),("repaired","proposed_final_repair/intl.html")]}
checks = []
for cc in ("TW","IN"):
    country = next(c for c in model["countries"] if c["cc"] == cc)
    metric = next(m for m in country["metrics"] if m["key"] == "gdp")
    checks.append({"id":cc+"-no-admitted-GDP", "passed":metric["value"] is None and not metric["source_url"] and not metric["evidence"],
                   "actual":{k:metric[k] for k in ("value","source_url","evidence","quality")}})
    for version,soup in soups.items():
        node = soup.select_one("#imc-country-"+cc)
        rows = [tr for tr in node.select(".imc-evidence tbody tr") if "GDP growth" in tr.get_text(" ",strip=True)]
        cells = [td.get_text(" ",strip=True) for td in rows[0].select("td")] if rows else []
        checks.append({"id":cc+"-"+version+"-unavailable-observation", "passed":len(cells)>=3 and cells[1:3]==["—","—"],
                       "actual":cells})
        vitals = [x.get_text(" ",strip=True) for x in node.select(".imc-vitals > *")]
        checks.append({"id":cc+"-"+version+"-visible-missing-data", "passed":any("GDP growth" in x and "No current observation" in x for x in vitals),
                       "actual":vitals})
    repaired = soups["repaired"].select_one("#imc-country-"+cc)
    checks.append({"id":cc+"-no-invented-GDP-inputs", "passed":repaired.select_one(".imc-macro-inputs[data-metric='gdp']") is None})
result = {"recorded_at":datetime.now(timezone.utc).isoformat(), "source_commit":prior["source_commit"],
          "html_sha256":prior["html_sha256"], "prior_failed_receipt":{"path":str(prior_path.name),"sha256":sha256(prior_path.read_bytes()).hexdigest(),
          "preserved_passed":80,"preserved_failed":2},
          "cause":"The first audit required a GDP source link even when no GDP observation was admitted. Both economies already lacked observed GDP in the original complete-input build.",
          "resolution":"Source links are required for admitted observations. Missing observations remain unavailable without invented numbers or attribution; this receipt verifies only those missing-data cases.",
          "checks":checks, "passed":sum(c["passed"] for c in checks),"failed":sum(not c["passed"] for c in checks),
          "remaining_coverage_gap":["Taiwan observed GDP","India observed GDP"],
          "limits":["Does not fill either observation gap, prove production adoption, or change the preserved 80-pass/2-fail audit."]}
target=RIG/"final_source_disclosure_resolution.json"
assert not target.exists()
target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="checks"},ensure_ascii=False))
print(json.dumps({"failed_checks":[c for c in checks if not c["passed"]]},ensure_ascii=False))
raise SystemExit(bool(result["failed"]))
