"""Dated additive correction and calendar qualification; never changes frozen v1."""
import argparse, hashlib, json, subprocess, sys
from datetime import date
from pathlib import Path

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,required=True)
    a=ap.parse_args()
    root=a.repo/"research/grey_deer/all_date_census"
    original=root/"RECORDED_VERSIONS_2026-10-17.json"
    target=root/"RECORDED_FIELDS_ADDENDUM_2026-10-17.json"
    calendar_target=root/"CALENDAR_COVERAGE_ADDENDUM_2026-10-17.json"
    if target.exists() or calendar_target.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    j=json.loads(original.read_text())
    rows=[]
    for r in j["records"]:
        if r["artifact"]!="data/regime/latest.json":
            continue
        raw=subprocess.check_output(["git","-C",str(a.repo),"cat-file","blob",r["blob_sha"]])
        if hashlib.sha256(raw).hexdigest()!=r["content_sha256"]:
            raise ValueError("RECORDED_BLOB_HASH_MISMATCH")
        native=json.loads(raw).get("risk_radar") or {}
        rows.append({
            "price_origin_date":r["price_origin_date"],
            "research_decision_cutoff":r["research_decision_cutoff"],
            "version_commit":r["version_commit"],"blob_sha":r["blob_sha"],
            "available_at":None,"delivered_at":None,
            "native_fields":{k:native.get(k) for k in
                ("asof","state","state_ungated","gate_clamped","top_score","alert","can_force")},
            "native_presence":{k:k in native for k in ("state_ungated","gate_clamped")},
        })
    out={"schema":"grey_deer.recorded_fields_addendum.v1",
         "corrects_artifact":str(original.relative_to(a.repo)),
         "original_sha256":sha(original),
         "script_sha256":sha(Path(__file__)),
         "correction":"The executed replay selected ungated_state; native Radar uses state_ungated. Null in the original extraction is not evidence of native absence. This addendum reads exact original blobs; no historical recomputation.",
         "records":rows}
    target.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n")
    sys.path.insert(0,str(a.repo))
    from lib.nyse_calendar import sessions_between
    import pandas as pd
    origins=a.repo/"research/grey_deer/all_date_census/v1/origins.csv.gz"
    d=pd.read_csv(origins,usecols=["date","ticker"])
    actual=sorted(d.loc[d.ticker=="SPY","date"].unique().tolist())
    expected={x.isoformat() for x in sessions_between(date.fromisoformat(actual[0]),date.fromisoformat(actual[-1]))}
    missing=sorted(expected-set(actual))
    extra=sorted(set(actual)-expected)
    coverage={"schema":"grey_deer.calendar_coverage_addendum.v1",
              "source_ref":j["source_ref"],
              "origins_sha256":sha(origins),
              "calendar_code_sha256":sha(a.repo/"lib/nyse_calendar.py"),
              "reference_sessions":len(actual),"rule_calendar_sessions":len(expected),
              "rule_sessions_absent_from_reference":missing,
              "reference_dates_not_rule_sessions":extra,
              "qualification":"UNRESOLVED_RULE_CALENDAR_DIFFERENCES",
              "caveat":"The existing calendar one-off closure list is not an exchange-certified historical calendar. Differences require independent historical closure/source evidence; neither missing bars nor calendar errors are assumed. Frozen census lattice and outcomes unchanged."}
    calendar_target.write_text(json.dumps(coverage,indent=2,sort_keys=True)+"\n")
    print("CALENDAR_RESULT",json.dumps(coverage))
    for r in rows:
        if r["price_origin_date"] in ["2026-09-01","2026-09-15","2026-09-30","2026-10-08","2026-10-12","2026-10-13","2026-10-14","2026-10-15"]:
            print("CORRECTED_RADAR",json.dumps(r))
if __name__=="__main__":
    main()
