"""Offline intelligence contracts. No production imports, files, ranking or collection."""
from __future__ import annotations
import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

POLICY = "research_qualified_atomic_v1"
SOURCE_MODE = "system_observed_replay"

class ContractError(ValueError):
    pass

def digest(value):
    b=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(b).hexdigest()

def number(value, low=None, high=None):
    # JSON strings and booleans are not measured numbers at this contract boundary.
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise ContractError("not_finite_json_number")
    try: value=float(value)
    except (ValueError,OverflowError): raise ContractError("not_finite_json_number") from None
    if not math.isfinite(value): raise ContractError("not_finite_json_number")
    if (low is not None and value<low) or (high is not None and value>high):
        raise ContractError("number_out_of_range")
    return float(value)

def timestamp(value):
    if not isinstance(value,str): raise ContractError("timestamp_missing")
    try: d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: raise ContractError("timestamp_invalid") from None
    if d.tzinfo is None or d.utcoffset() is None: raise ContractError("timestamp_requires_timezone")
    return d.astimezone(timezone.utc)

def session(value):
    if not isinstance(value,str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",value):
        raise ContractError("session_identity_invalid")
    try: datetime.strptime(value,"%Y-%m-%d")
    except ValueError: raise ContractError("session_identity_invalid") from None
    return value

def ticker_identity(value):
    # Boundary assumes the existing symbol owner has already canonicalized issuers.
    if not isinstance(value,str) or not re.fullmatch(r"[0-9]{6}\.(?:SS|SZ|BJ)",value):
        raise ContractError("invalid_ticker")
    return value

def qualified_order(rows, *, featured_cap=24, sector_cap=4):
    """Experimental featured scope; upstream qualification is an explicit supplied premise.

    Production must reuse the existing qualification predicate before caps. Public
    lane reasons reconstruct that population for this single observation only.
    """
    for x in (featured_cap,sector_cap):
        if isinstance(x,bool) or not isinstance(x,int) or x<0: raise ContractError("invalid_cap")
    ids=set(); qualified=[]
    for row in rows:
        ticker=row.get("ticker")
        ticker_identity(ticker)
        if ticker in ids: raise ContractError("duplicate_candidate_identity")
        ids.add(ticker)
        if type(row.get("qualified")) is not bool: raise ContractError("qualification_not_boolean")
        if not row["qualified"]: continue
        number(row.get("score"),0,100)
        sr=row.get("score_rank")
        if isinstance(sr,bool) or not isinstance(sr,int) or sr<1: raise ContractError("invalid_score_rank")
        qualified.append(deepcopy(row))
    if len({r["score_rank"] for r in qualified}) != len(qualified):
        raise ContractError("duplicate_score_rank")
    invalid=[]
    for row in qualified:
        try:
            if row.get("intel_basis")!="measured": raise ContractError("intel_unavailable")
            number(row.get("intel"),0,100)
        except ContractError as ex: invalid.append({"ticker":row["ticker"],"reason":str(ex)})
    mode="no_qualified_candidates" if not qualified else ("v3_atomic_fallback" if invalid else "intelligence_atomic")
    ordered=sorted(qualified,key=(lambda r:(r["score_rank"],r["ticker"])) if invalid else
                   (lambda r:(-r["intel"],-r["score"],r["ticker"])))
    selected=[]; excluded=[]; counts=Counter()
    for row in ordered:
        sector=row.get("sector") or "—"
        reason="featured_cap" if len(selected)>=featured_cap else ("sector_cap" if counts[sector]>=sector_cap else None)
        if reason: excluded.append({"ticker":row["ticker"],"reason":reason})
        else: selected.append(row["ticker"]);counts[sector]+=1
    return {"policy":POLICY,"coverage_scope":"qualified_pre_cap","mode":mode,
            "qualified_n":len(qualified),"invalid":sorted(invalid,key=lambda r:r["ticker"]),
            "ordered":[r["ticker"] for r in ordered],"selected":selected,
            "excluded_by_caps":excluded,"sector_counts":dict(counts)}

def source_snapshot(records, cutoff, *, expected_sessions, periodic_families=()):
    """Minimal candidate for an existing reader's temporal selection, not a store.

    Caller supplies source-specific observation family and validity semantics.
    Retrospective public-market reconstruction is deliberately outside this mode.
    """
    cutoff=timestamp(cutoff); identities={}; chosen={}; rejected=[]; suppressed=[]
    if not isinstance(expected_sessions,dict): raise ContractError("source_session_contract_missing")
    for family,value in expected_sessions.items():
        if not isinstance(family,str) or not family or family!=family.strip(): raise ContractError("source_family_invalid")
        session(value)
    if isinstance(periodic_families,str): raise ContractError("periodic_family_contract_invalid")
    periodic_families=frozenset(periodic_families)
    if any(not isinstance(f,str) or not f or f!=f.strip() for f in periodic_families) or periodic_families.intersection(expected_sessions):
        raise ContractError("periodic_family_contract_invalid")
    for record in records:
        r=deepcopy(record)
        keys=(r.get("ticker"),r.get("family"),r.get("observation_key"),r.get("source_record_id"))
        # Validly future availability is enough to exclude a record from this
        # system-observed replay, before its unrelated malformed payload/identity.
        available=[];clock_errors=[]
        for field in ("published_at","first_seen_at"):
            try: available.append(timestamp(r.get(field)))
            except ContractError as ex: clock_errors.append(str(ex))
        raw_identity=list(keys)+( [r.get("revision")] )
        if any(t>cutoff for t in available):
            rejected.append({"identity":raw_identity,"reason":"not_known_at_cutoff"});continue
        if clock_errors:
            rejected.append({"identity":raw_identity,"reason":clock_errors[0]});continue
        if any(not isinstance(x,str) or not x or x!=x.strip() for x in keys): raise ContractError("source_identity_missing")
        ticker_identity(r["ticker"])
        version=r.get("revision")
        if isinstance(version,bool) or not isinstance(version,int) or version<0: raise ContractError("invalid_revision")
        identity=keys+(version,)
        try:
            effective=timestamp(r.get("effective_from"))
        except ContractError:
            effective=None  # a known invalid revision must suppress, not revive
        if effective is not None and effective>cutoff:
            rejected.append({"identity":list(identity),"reason":"not_known_at_cutoff"});continue
        try:
            numeric=number(r.get("value"))
            # Coalesce 1 with 1.0 without rounding unequal large JSON integers
            # through a float (e.g. 2**53 and 2**53+1 must remain distinct).
            if isinstance(r["value"],int): pass
            elif numeric.is_integer(): r["value"]=int(numeric)
            else: r["value"]=numeric
        except ContractError: pass  # validate the chosen version below
        try: canonical=json.dumps(r,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
        except (ValueError,TypeError,OverflowError): raise ContractError("source_record_not_canonical_json") from None
        if identity in identities:
            if identities[identity]!=canonical: raise ContractError("conflicting_source_version")
            continue
        identities[identity]=canonical
        key=keys
        if key not in chosen or version>chosen[key]["revision"]: chosen[key]=r
    selected=[]
    for key,r in sorted(chosen.items()):
        identity=key+(r["revision"],)
        try:
            timestamp(r.get("effective_from"))
            if not isinstance(r.get("source_blob_sha256"),str) or len(r["source_blob_sha256"])!=64 or any(c not in "0123456789abcdef" for c in r["source_blob_sha256"]):
                raise ContractError("source_blob_identity_missing")
            status=r.get("status")
            if status=="retracted": raise ContractError("source_retracted")
            if status!="active": raise ContractError("source_status_unqualified")
            number(r.get("value"))
            if r.get("expires_at") is not None and cutoff>=timestamp(r["expires_at"]):
                raise ContractError("expired_by_source_contract")
            cadence="session" if r["family"] in expected_sessions else ("periodic" if r["family"] in periodic_families else None)
            if cadence is None: raise ContractError("source_family_unqualified")
            if r.get("cadence")!=cadence: raise ContractError("cadence_unqualified")
            if cadence=="session":
                observed=session(r.get("observation_session"))
                if observed!=expected_sessions[r["family"]]: raise ContractError("wrong_observation_session")
        except ContractError as ex:
            receipt={"identity":list(identity),"reason":str(ex)}
            rejected.append(receipt);suppressed.append(receipt);continue
        selected.append(r)
    # Payload fingerprints include the clocks/validity contract that qualified
    # these observations. This is still not proof of complete upstream history.
    fingerprint=[{k:r.get(k) for k in ("ticker","family","observation_key","source_record_id","revision","status","value","unit","feature_contract_id","source_blob_sha256","published_at","first_seen_at","effective_from","expires_at","cadence","observation_session")} for r in selected]
    return {"mode":SOURCE_MODE,"cutoff":cutoff.isoformat(),"expected_sessions":expected_sessions,"periodic_families":sorted(periodic_families),
            "selected":selected,"rejected":rejected,"suppressed":suppressed,
            "selected_input_digest":digest(fingerprint)}

def load_source_functions(inp):
    scope={"math":math,"Any":object,"Mapping":dict,"INTEL_BASIS_MEASURED":"measured"}
    for name in ("_rank_pct","_finite_float","intel_interest_is_measured"):
        node=ast.parse(inp["source_functions"][name]["source"]).body[0]
        exec(compile(ast.Module(body=[node],type_ignores=[]),name+"@"+inp["source_sha"],"exec"),scope)
    return scope

def main():
    here=Path(__file__).resolve().parent
    inp=json.loads((here/"source_input.json").read_text())
    source=load_source_functions(inp)
    checks=[]
    def check(name, condition, details=None):
        assert condition,name
        checks.append({"name":name,"passed":True,"details":details})
    def refused(name, fun, expected):
        try: fun()
        except ContractError as ex: check(name,str(ex)==expected,{"reason":str(ex)});return
        raise AssertionError(name+": accepted invalid input")
    rows=[dict(r,qualified=True) for r in inp["qualified_rows"]]
    all_intel=qualified_order(rows)
    v3rows=deepcopy(rows);v3rows[0]["intel_basis"]="fallback_v3"
    v3=qualified_order(v3rows)
    check("current_v3_exact_24_and_order",v3["selected"]==inp["published_featured"])
    check("current_qualified_intel_retains_four",len(set(all_intel["selected"])&set(v3["selected"]))==4)
    check("input_permutation_invariant",qualified_order(list(reversed(rows)))==all_intel)
    noncompeting={"ticker":"999999.SS","qualified":False,"intel":None}
    check("unqualified_missing_row_has_no_coverage_effect",qualified_order(rows+[noncompeting])==all_intel)
    check("qualified_missing_falls_back_atomically",v3["mode"]=="v3_atomic_fallback" and v3["ordered"]==[r["ticker"] for r in sorted(rows,key=lambda r:r["score_rank"])])
    zeros=[dict(r,intel=0.0) for r in rows]
    z=qualified_order(zeros)
    check("all_measured_zero_remains_intelligence",z["mode"]=="intelligence_atomic" and z["selected"]==v3["selected"])
    check("zero_cap_releases_zero",qualified_order(rows,featured_cap=0)["selected"]==[])
    check("empty_population_is_explicit",qualified_order([])["mode"]=="no_qualified_candidates")
    refused("duplicate_candidate_refused",lambda:qualified_order(rows+[rows[0]]),"duplicate_candidate_identity")
    bad=deepcopy(rows);bad[0]["qualified"]="true"
    refused("string_qualification_refused",lambda:qualified_order(bad),"qualification_not_boolean")
    type_witnesses=[]
    for label,value in [("boolean",True),("numeric_string","99"),("negative",-1),("above_range",101),("nan",float("nan")),("infinity",float("inf"))]:
        b=deepcopy(rows);b[0]["intel"]=value
        native=source["intel_interest_is_measured"]({"intel_interest_basis":"measured","intel_interest_score":value})
        proto=qualified_order(b)
        check("bad_intel_"+label,proto["mode"]=="v3_atomic_fallback")
        type_witnesses.append({"case":label,"native_direct_measurement_predicate":native,"prototype_mode":proto["mode"]})
    # This is a native predicate boundary test, not a claim that current stored rows contain these values.
    cutoff="2026-10-09T08:00:00Z";expected="2026-10-09"
    sessions={"test_valuation":expected,"test_margin":"2026-10-08"}
    def fact(ticker,value,**kw):
        out={"ticker":ticker,"family":"test_valuation","observation_key":expected,"source_record_id":ticker+"/valuation/"+expected,
             "revision":0,"value":value,"source_blob_sha256":"a"*64,"published_at":"2026-10-09T07:00:00Z",
             "first_seen_at":"2026-10-09T07:01:00Z","effective_from":"2026-10-09T07:00:00Z",
             "cadence":"session","observation_session":expected,"status":"active","unit":"synthetic_score"};out.update(kw)
        out.setdefault("feature_contract_id",out["family"]+"/synthetic-value/v1");return out
    facts=[fact("600000.SS",1.0),fact("000001.SZ",3.0)]
    base=source_snapshot(facts,cutoff,expected_sessions=sessions)
    check("known_source_values_accepted",len(base["selected"])==2)
    zero=source_snapshot([fact("600000.SS",0.0)],cutoff,expected_sessions=sessions)
    check("zero_source_value_preserved",zero["selected"][0]["value"]==0.0)
    late=fact("600111.SS",2.0,first_seen_at="2026-10-09T09:00:00Z")
    with_late=source_snapshot(facts+[late],cutoff,expected_sessions=sessions)
    check("post_cutoff_ingestion_cannot_change_selected_inputs",with_late["selected_input_digest"]==base["selected_input_digest"])
    correction=dict(facts[0],revision=1,value=10.0,first_seen_at="2026-10-09T09:00:00Z",published_at="2026-10-09T08:30:00Z",source_blob_sha256="b"*64)
    before=source_snapshot(facts+[correction],cutoff,expected_sessions=sessions)
    after=source_snapshot(facts+[correction],"2026-10-09T10:00:00Z",expected_sessions=sessions)
    check("late_correction_keeps_prior_version",before["selected_input_digest"]==base["selected_input_digest"])
    check("known_correction_selects_new_version",next(r for r in after["selected"] if r["ticker"]=="600000.SS")["revision"]==1)
    check("correction_changes_selected_input_digest",after["selected_input_digest"]!=base["selected_input_digest"])
    check("out_of_order_arrival_does_not_restore_old_revision",source_snapshot([correction]+facts,"2026-10-09T10:00:00Z",expected_sessions=sessions)["selected_input_digest"]==after["selected_input_digest"])
    check("identical_source_version_coalesced",source_snapshot(facts+[facts[0]],cutoff,expected_sessions=sessions)==base)
    refused("conflicting_source_version_refused",lambda:source_snapshot(facts+[dict(facts[0],value=9)],cutoff,expected_sessions=sessions),"conflicting_source_version")
    future_duplicate=dict(facts[0],value=9,first_seen_at="2026-10-09T09:00:00Z")
    check("future_conflicting_copy_does_not_change_prior_inputs",source_snapshot(facts+[future_duplicate],cutoff,expected_sessions=sessions)["selected_input_digest"]==base["selected_input_digest"])
    for label,updates,reason in [
        ("retraction",{"status":"retracted","value":None},"source_retracted"),
        ("invalid_payload",{"value":True},"not_finite_json_number"),
        ("expired_correction",{"expires_at":cutoff},"expired_by_source_contract"),
        ("unknown_status",{"status":"unknown"},"source_status_unqualified"),
        ("missing_blob_correction",{"source_blob_sha256":None},"source_blob_identity_missing"),
        ("wrong_session_correction",{"observation_session":"2026-09-30"},"wrong_observation_session")]:
        known=dict(facts[0],revision=1,**updates)
        snapshot=source_snapshot(facts+[known],cutoff,expected_sessions=sessions)
        check("known_"+label+"_does_not_resurrect_old_revision",all(r["ticker"]!="600000.SS" for r in snapshot["selected"]) and snapshot["suppressed"][0]["reason"]==reason)
        future=dict(known,first_seen_at="2026-10-09T09:00:00Z")
        check("future_"+label+"_keeps_prior_version",source_snapshot(facts+[future],cutoff,expected_sessions=sessions)["selected_input_digest"]==base["selected_input_digest"])
    for label,updates,reason in [
        ("missing_first_seen",{"first_seen_at":None},"timestamp_missing"),
        ("date_only_publication",{"published_at":"2026-10-09"},"timestamp_requires_timezone"),
        ("future_publication",{"published_at":"2026-10-10T00:00:00Z"},"not_known_at_cutoff"),
        ("future_effective",{"effective_from":"2026-10-10T00:00:00Z"},"not_known_at_cutoff"),
        ("wrong_session",{"observation_session":"2026-09-30"},"wrong_observation_session"),
        ("explicit_expiry",{"expires_at":cutoff},"expired_by_source_contract"),
        ("boolean_value",{"value":True},"not_finite_json_number"),
        ("missing_blob",{"source_blob_sha256":None},"source_blob_identity_missing")]:
        result=source_snapshot([dict(fact("600000.SS",1.0),**updates)],cutoff,expected_sessions=sessions)
        check("source_"+label,not result["selected"] and result["rejected"][0]["reason"]==reason)
    periodic=fact("600000.SS",1.0,family="test_filing",cadence="periodic",observation_session="2026-06-30",published_at="2026-08-01T07:00:00Z",first_seen_at="2026-08-01T07:01:00Z",effective_from="2026-08-01T07:00:00Z")
    check("older_periodic_fact_not_expired_by_arbitrary_age",len(source_snapshot([periodic],cutoff,expected_sessions=sessions,periodic_families={"test_filing"})["selected"])==1)
    margin=fact("600000.SS",1.0,family="test_margin",observation_session="2026-10-08")
    check("source_specific_previous_session_is_valid",len(source_snapshot([margin],cutoff,expected_sessions=sessions)["selected"])==1)
    check("one_global_session_would_wrongly_reject_delayed_source",not source_snapshot([margin],cutoff,expected_sessions={"test_margin":expected})["selected"])
    check("same_instant_timezone_equivalent",source_snapshot(facts,"2026-10-09T16:00:00+08:00",expected_sessions=sessions)==base)
    def normal(snapshot):
        if len({r["ticker"] for r in snapshot["selected"]})!=len(snapshot["selected"]):
            raise ContractError("normalization_requires_aggregated_unique_ticker_features")
        contracts={(r.get("family"),r.get("unit"),r.get("feature_contract_id")) for r in snapshot["selected"]}
        if len(contracts)!=1 or any(not isinstance(x,str) or not x or x!=x.strip() for item in contracts for x in item):
            raise ContractError("normalization_requires_homogeneous_feature_contract")
        return source["_rank_pct"]({r["ticker"]:r["value"] for r in snapshot["selected"]})
    n0=normal(base);nlate=normal(with_late)
    check("normalize_after_cutoff_blocks_future_reference_rows",nlate==n0)
    available=fact("600111.SS",0.0)
    expanded=source_snapshot(facts+[available],cutoff,expected_sessions=sessions)
    ne=normal(expanded)
    check("available_reference_addition_can_change_incumbent_percentiles",ne["600000.SS"]!=n0["600000.SS"])
    check("reference_population_change_changes_digest",expanded["selected_input_digest"]!=base["selected_input_digest"])
    check("native_midrank_ties_equal",source["_rank_pct"]({"A":2,"B":2,"C":3})["A"]==source["_rank_pct"]({"A":2,"B":2,"C":3})["B"])
    many=source_snapshot(facts+[dict(facts[0],source_record_id="separate-observation")],cutoff,expected_sessions=sessions)
    refused("multiple_source_observations_require_qualified_aggregation",lambda:normal(many),"normalization_requires_aggregated_unique_ticker_features")
    # Fiscal year selection is a wall-clock dependency in the native reader's source.
    analyst=inp["source_functions"]["analyst_consensus"]["source"]
    check("native_analyst_current_year_dependency_present","pd.Timestamp.now().year" in analyst)
    # Its currently consumed rating score uses rating counts, so no ranking effect is asserted here.
    result={"source_sha":inp["source_sha"],"policy":POLICY,"source_mode":SOURCE_MODE,
            "source_input_sha256":hashlib.sha256((here/"source_input.json").read_bytes()).hexdigest(),
            "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "checks":checks,"check_count":len(checks),"current_populations":inp["population_coverage"],
            "current_v3_control":v3,"current_qualified_intelligence":all_intel,
            "native_numeric_boundary_witnesses":type_witnesses,
            "normalization_witness":{"base":n0,"future_row_excluded":nlate,"available_new_row":ne},
            "version_witness":{"before_revision":before["selected"],"after_revision":after["selected"]},
            "limits":["Strict numeric contract is a proposal; native attachment clamps values and upstream actual data must be checked before changing compatibility.",
                      "Prototype consumes a previously qualified population; production must derive it with the existing shared safeguards before caps.",
                      "Source-time tests use synthetic independently labeled facts. Actual historical publication and first-seen fields are not invented.",
                      "Selection orders explicit upstream revisions, then validates the latest known payload. Unknown availability still prevents historical qualification; no complete upstream history is asserted.",
                      "This source digest is an input-fingerprint example to attach to existing generation ownership, not a new production identity store.",
                      "No return, alpha, execution, deployed behavior or operational source completeness claim."]}
    (here/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"checks":len(checks),"all_passed":True,"current_intel_overlap":len(set(all_intel["selected"])&set(v3["selected"])),"result":"results.json"}))

if __name__=="__main__":main()
