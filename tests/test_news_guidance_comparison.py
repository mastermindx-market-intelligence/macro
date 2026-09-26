"""Guidance comparison contract. All records are explicitly synthetic owner fixtures."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json

import pytest
from engine.company_intelligence.documents import text_span
from engine.company_intelligence.identity import ListingAlias

ASOF = datetime(2026, 9, 24, 16, 0, tzinfo=timezone.utc)
EVENT = "evt_cik0000000001_2026q3_results"
FLAGS = {"may_rank": False, "may_size": False, "may_gate": False, "prophet_authority": False}


def workspace(low=100000, high=103000, *, later=False, metric="vehicle_deliveries", unit="vehicles", horizon="FY2026 Q4", status="introduced"):
    # Real SourceSpan factory; no fake receipt_state/hash used as proof.
    body = f"For {horizon}, expected {metric} are {low} to {high} {unit}."
    digest = sha256(body.encode()).hexdigest()
    doc = "fixture-release-" + ("new" if later else "prior")
    span = text_span(document_id=doc, document_version=1, body_sha256=digest,
                     segment_index=0, segment_text=body, start_byte=0,
                     end_byte=len(body.encode()), text=body,
                     rights_profile="rp_public_primary_v1").to_payload()
    clock = "2026-09-24T15:00:00+00:00" if later else "2026-09-23T15:00:00+00:00"
    guide = {"schema": "guidance_item.v1", "metric": metric, "low": low, "high": high,
             "unit": unit, "horizon": horizon, "status": status, "source_span": span}
    return {"schema": "event_workspace.v1", "event_id": EVENT,
            "issuer": {"company_id": "cik:0000000001", "listings": [ListingAlias(ticker="ACME", mic="XNAS", share_class="common", trading_currency="USD", is_primary=True).to_payload()]},
            "generation_id": ("b" if later else "a") * 24, "generated_at": clock,
            "lifecycle": {"state": "distributed", "observed_at": clock, "source_available_at": clock},
            "authority": "context_only", "prophet_flags": dict(FLAGS),
            "guidance": [guide], "sources": [{"document_id": doc, "source_sha256": digest,
                "receipt_state": "byte_replayed", "kind": "issuer_release"}]}


def compare(current=None, prior=None):
    name = "engine.company_intelligence.guidance_comparison"
    assert importlib.util.find_spec(name) is not None, "Owner-bound guidance comparator is not implemented"
    from engine.company_intelligence.guidance_comparison import compare_guidance_workspaces
    return compare_guidance_workspaces(current or workspace(76000, 78000, later=True), prior, as_of=ASOF)


def test_vehicle_midpoint_change_has_two_owner_receipts_and_no_forecast():
    previous=workspace(); current=workspace(76000,78000,later=True); before=deepcopy((current,previous))
    result=compare(current,previous); row=result["comparisons"][0]
    assert row["current_midpoint"]=="77000"
    assert row["prior_midpoint"]=="101500"
    assert row["midpoint_delta"]=="-24500"
    assert row["relative_change_pct"]=="-24.137931"
    assert row["direction"]=="lower"
    assert len(row["evidence"])==2
    assert row["interpretation"]=="numeric_difference_only"
    assert result["authority"]=="context_only" and result["prophet_flags"]==FLAGS
    assert (current,previous)==before
    json.dumps(result,allow_nan=False)


def test_missing_prior_never_means_zero_change_or_zero_surprise():
    r=compare();assert not r["comparisons"]
    assert "prior_not_supplied" in r["reasons"]
    assert r["consensus"] is None


@pytest.mark.parametrize("field,value,reason",[
    ("horizon","FY2026 Q3","prior_comparable_missing"),
    ("metric","vehicle_production","prior_comparable_missing"),
    ("unit","units","measurement_mismatch"),
])
def test_mismatched_measurement_cannot_donate_a_baseline(field,value,reason):
    p=workspace();p["guidance"][0][field]=value
    r=compare(prior=p);assert not r["comparisons"] and reason in r["reasons"]


@pytest.mark.parametrize("field,value",[("authority","signal"),("schema","wrong")])
def test_invalid_workspace_contract(field,value):
    c=workspace(76000,78000,later=True);c[field]=value
    r=compare(c,workspace());assert not r["comparisons"] and "workspace_invalid" in r["reasons"]


def test_different_issuer_refused_even_when_ticker_and_numbers_match():
    p=workspace();p["event_id"]="evt_cik0000000002_2026q3_results";p["issuer"]["company_id"]="cik:0000000002"
    r=compare(prior=p);assert not r["comparisons"] and "issuer_mismatch" in r["reasons"]


def test_event_id_and_issuer_must_agree():
    c=workspace(later=True);c["issuer"]["company_id"]="cik:0000000002"
    r=compare(c,workspace());assert not r["comparisons"] and "workspace_invalid" in r["reasons"]


@pytest.mark.parametrize("value",[float("nan"),float("inf"),-float("inf"),True,"NaN",{},[],None,10**1000])
def test_invalid_numbers_are_absent(value):
    c=workspace(later=True);c["guidance"][0]["low"]=value
    r=compare(c,workspace());assert not r["comparisons"] and "guidance_invalid" in r["reasons"]


@pytest.mark.parametrize("low,high",[(11,10),(-1,5),(1.5,5)])
def test_invalid_physical_ranges(low,high):
    r=compare(workspace(low,high,later=True),workspace())
    assert not r["comparisons"] and "guidance_invalid" in r["reasons"]


def test_percent_change_is_percentage_points_not_relative_growth():
    p=workspace(9,11,metric="revenue_yoy_pct",unit="percent")
    c=workspace(10,12,later=True,metric="revenue_yoy_pct",unit="percent")
    row=compare(c,p)["comparisons"][0]
    assert row["midpoint_delta"]=="1" and row["delta_unit"]=="percentage_points"
    assert row["relative_change_pct"] is None


def test_zero_prior_midpoint_keeps_absolute_change_without_infinite_percentage():
    row=compare(workspace(1,3,later=True),workspace(0,0))["comparisons"][0]
    assert row["midpoint_delta"]=="2" and row["relative_change_pct"] is None
    assert row["relative_change_reason"]=="zero_prior_midpoint"


@pytest.mark.parametrize("change",["source_hash","document_id","text_hash","state","rights"])
def test_span_must_bind_the_exact_approved_source(change):
    c=workspace(later=True);sp=c["guidance"][0]["source_span"]
    if change=="source_hash":c["sources"][0]["source_sha256"]="0"*64
    elif change=="document_id":sp["document_id"]="unrelated-document"
    elif change=="text_hash":sp["text_sha256"]="0"*64
    elif change=="state":sp["receipt_state"]="address_only"
    else:sp["rights_profile"]="rp_unknown_v1"
    r=compare(c,workspace());assert not r["comparisons"] and "guidance_evidence_invalid" in r["reasons"]


def test_ambiguous_prior_is_not_first_match_wins():
    p=workspace();p["guidance"].append(deepcopy(p["guidance"][0]))
    r=compare(prior=p);assert not r["comparisons"] and "prior_ambiguous" in r["reasons"]


def test_withdrawn_current_never_gets_numeric_comparison():
    r=compare(workspace(later=True,status="withdrawn"),workspace())
    assert not r["comparisons"] and "guidance_withdrawn" in r["reasons"]


@pytest.mark.parametrize("clock",[None,"bad","2026-09-25T01:00:00+00:00","2026-09-24T15:00:00"])
def test_unknown_future_or_unzoned_clock_refused(clock):
    c=workspace(later=True);c["lifecycle"]["observed_at"]=clock
    r=compare(c,workspace());assert not r["comparisons"] and "clock_invalid" in r["reasons"]


def test_prior_observed_after_current_refused():
    c=workspace(later=True);p=workspace();p["lifecycle"]=deepcopy(c["lifecycle"])
    r=compare(c,p);assert not r["comparisons"] and "revision_order_invalid" in r["reasons"]


def test_unknown_financial_basis_is_not_comparable():
    c=workspace(95,105,later=True,metric="revenue",unit="USD_millions")
    p=workspace(100,110,metric="revenue",unit="USD_millions")
    r=compare(c,p);assert not r["comparisons"] and "measurement_basis_missing" in r["reasons"]


def test_same_fiscal_horizon_can_cross_earnings_event_boundaries():
    p=workspace();p["event_id"]="evt_cik0000000001_2026q2_results"
    assert compare(prior=p)["comparisons"]


def test_unchanged_guidance_does_not_claim_a_raise_or_cut():
    row=compare(workspace(later=True),workspace())["comparisons"][0]
    assert row["direction"]=="unchanged" and row["midpoint_delta"]=="0"


def test_actual_news_consumer_attaches_context_without_changing_news_lean(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    feed={"by_ticker":{"ACME":[{"title":"Company updates outlook","sentiment":"neutral"}]}}
    baseline=news.mastermind_by_ticker(feed)
    result=news.mastermind_by_ticker(feed,guidance_workspaces={"ACME":{"expected_security_id":"xnas:ACME","current":workspace(76000,78000,later=True),"prior":workspace()}},as_of=ASOF)
    context=result["ACME"].pop("guidance_context")
    assert result==baseline and context["comparisons"][0]["midpoint_delta"]=="-24500"


def test_auxiliary_guidance_cannot_create_a_new_news_ticker(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    assert news.mastermind_by_ticker({"by_ticker":{}},guidance_workspaces={"ACME":{"expected_security_id":"xnas:ACME","current":workspace()}},as_of=ASOF)=={}


@pytest.mark.parametrize("state",["cancelled","superseded","scheduled","published","unknown"])
def test_ineligible_event_state_cannot_present_live_guidance(state):
    c=workspace(later=True);c["lifecycle"]["state"]=state
    r=compare(c,workspace());assert not r["comparisons"] and "event_state_ineligible" in r["reasons"]


def test_permission_flags_require_actual_false_not_equal_zero():
    c=workspace(later=True);c["prophet_flags"]["may_rank"]=0
    r=compare(c,workspace());assert not r["comparisons"] and "workspace_invalid" in r["reasons"]


def test_small_rate_change_is_not_rounded_to_zero():
    p=workspace(0.0000001,0.0000003,metric="revenue_yoy_pct",unit="percent")
    c=workspace(0.0000002,0.0000004,later=True,metric="revenue_yoy_pct",unit="percent")
    row=compare(c,p)["comparisons"][0]
    assert row["midpoint_delta"]=="0.0000001" and row["current_midpoint"]=="0.0000003"


def test_corrected_source_is_not_labelled_a_management_guidance_cut():
    c=workspace(76000,78000,later=True);c["lifecycle"]["state"]="corrected"
    row=compare(c,workspace())["comparisons"][0]
    assert row["interpretation"]=="source_correction_difference"


def test_public_projection_never_leaks_document_span_or_body_details():
    from engine.company_intelligence.guidance_comparison import public_guidance_context
    internal=compare(prior=workspace());public=public_guidance_context(internal)
    raw=json.dumps(public)
    assert 'document_id' not in raw and 'span_id' not in raw and 'source_sha256' not in raw
    assert public["comparisons"][0]["evidence"][0]["receipt_state"]=="byte_replayed"


def test_news_ticker_membership_is_checked_before_auxiliary_context(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    feed={"by_ticker":{"OTHER":[{"title":"A story"}]}}
    result=news.mastermind_by_ticker(feed,guidance_workspaces={"OTHER":{"expected_security_id":"xnas:OTHER","current":workspace(later=True),"prior":workspace()}},as_of=ASOF)
    assert result["OTHER"]["guidance_context"]["reasons"]==["issuer_listing_mismatch"]


def test_existing_news_builder_writes_comparison_on_same_per_ticker_artifact(monkeypatch,tmp_path):
    import engine,sys,types
    from engine import financial_news as news
    from scripts import build_news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    feed={"by_ticker":{"ACME":[{"title":"Outlook revised","sentiment":"neutral"}]},"market":[]}
    monkeypatch.setattr(news,"feed",lambda:feed)
    monkeypatch.setattr(build_news.config,"ROOT",tmp_path)
    monkeypatch.setattr(build_news.config,"load",lambda:{"storage":{"site_dir":"site"}})
    monkeypatch.setattr(build_news,"_enrich",lambda sections:"")
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls,tz=None):return ASOF
    monkeypatch.setattr(build_news,"datetime",FrozenDateTime)
    boundaries={
      "macro_news":{"macro_headlines":lambda:None,"upcoming_catalysts":lambda **kw:[],"DISCLAIMER_TEXT":"","DISCLAIMER_TEXT_ZH":"","THEME_LABEL":{}},
      "news_rss":{"start_reject_log":lambda:([],None),"stop_reject_log":lambda token:None},
      "news_ai_feed":{"enabled":lambda:False},
      "china_news":{"panel":lambda:None},
      "news_vector":{"enabled":lambda:False,"recent_panel":lambda:None},
      "macro_surprise":{"build_release_cards":lambda **kw:None},
      "news_event_ledger":{"persist_kept_events":lambda *a,**kw:0,"persist_reject_sample":lambda *a,**kw:0},
    }
    for name,functions in boundaries.items():
        module=types.ModuleType("engine."+name)
        for key,fn in functions.items():setattr(module,key,fn)
        monkeypatch.setitem(sys.modules,"engine."+name,module)
        monkeypatch.setattr(engine,name,module,raising=False)
    build_news.build(guidance_workspaces={"ACME":{"expected_security_id":"xnas:ACME","current":workspace(76000,78000,later=True),"prior":workspace()}})
    artifact=json.loads((tmp_path/"site/news/by_ticker.json").read_text())
    row=artifact["tickers"]["ACME"]
    assert artifact["schema"]=="news_flow.v1" and row["n_recent"]==1
    assert row["guidance_context"]["comparisons"][0]["midpoint_delta"]=="-24500"
    assert row["guidance_context"]["as_of"]==ASOF.isoformat()



def test_news_join_requires_owner_security_binding_not_ticker_alone(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    result=news.mastermind_by_ticker({"by_ticker":{"ACME":[{"title":"News"}]}},
        guidance_workspaces={"ACME":{"current":workspace(later=True),"prior":workspace()}},as_of=ASOF)
    assert result["ACME"]["guidance_context"]["reasons"]==["listing_binding_missing"]


def test_foreign_listing_cannot_match_expected_us_security(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    c=workspace(later=True);c["issuer"]["listings"][0]["mic"]="XLON"
    result=news.mastermind_by_ticker({"by_ticker":{"ACME":[{"title":"News"}]}},
        guidance_workspaces={"ACME":{"expected_security_id":"xnas:ACME","current":c,"prior":workspace()}},as_of=ASOF)
    assert not result["ACME"]["guidance_context"]["comparisons"]
    assert result["ACME"]["guidance_context"]["reasons"]==["issuer_listing_mismatch"]


def test_expired_listing_is_not_known_now_ticker_authority(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    c=workspace(later=True);c["issuer"]["listings"][0]["valid_to"]="2026-09-24"
    result=news.mastermind_by_ticker({"by_ticker":{"ACME":[{"title":"News"}]}},
        guidance_workspaces={"ACME":{"expected_security_id":"xnas:ACME","current":c,"prior":workspace()}},as_of=ASOF)
    assert not result["ACME"]["guidance_context"]["comparisons"]


def test_history_can_use_prior_alias_of_same_issuer(monkeypatch):
    from engine import financial_news as news
    monkeypatch.setattr(news.nc,"build_entity_map",lambda:{"tickers":{}})
    p=workspace();p["issuer"]["listings"][0]["ticker"]="OLD";p["issuer"]["listings"][0]["security_id"]="xnas:OLD"
    result=news.mastermind_by_ticker({"by_ticker":{"ACME":[{"title":"News"}]}},
        guidance_workspaces={"ACME":{"expected_security_id":"xnas:ACME","current":workspace(later=True),"prior":p}},as_of=ASOF)
    assert result["ACME"]["guidance_context"]["comparisons"]


def test_original_observation_clocks_remain_visible_beside_build_clock():
    row=compare(prior=workspace())["comparisons"][0]
    assert row["evidence"][0]["observed_at"]=="2026-09-24T15:00:00+00:00"
    assert row["evidence"][1]["source_available_at"]=="2026-09-23T15:00:00+00:00"


def test_source_hash_cannot_be_missing_on_both_sides_of_association():
    c=workspace(later=True);c["sources"][0]["source_sha256"]=None
    c["guidance"][0]["source_span"]["receipt"]["source_sha256"]=None
    r=compare(c,workspace());assert not r["comparisons"] and "guidance_evidence_invalid" in r["reasons"]


def test_existing_source_gated_earnings_job_runs_this_suite():
    from pathlib import Path
    import yaml
    jobs=yaml.safe_load((Path(__file__).resolve().parents[1]/".github/ci/legacy-jobs.yml").read_text())["jobs"]
    job=jobs["earnings-release-identity"]
    assert job["gate"]=="code"
    assert any("tests/test_news_guidance_comparison.py" in s.get("run","") for s in job["steps"])


@pytest.mark.parametrize("where,value",[("event_state",{}),("guidance_status",[]),("rights",{})])
def test_malformed_enum_is_a_named_absence_not_an_exception(where,value):
    c=workspace(later=True)
    if where=="event_state":c["lifecycle"]["state"]=value
    elif where=="guidance_status":c["guidance"][0]["status"]=value
    else:c["guidance"][0]["source_span"]["rights_profile"]=value
    r=compare(c,workspace())
    assert not r["comparisons"] and r["reasons"]


def test_extreme_numeric_precision_is_not_unbounded_work():
    from decimal import Decimal
    c=workspace(later=True,metric="revenue_yoy_pct",unit="percent")
    c["guidance"][0]["low"]=Decimal("1e-100000")
    r=compare(c,workspace(metric="revenue_yoy_pct",unit="percent"))
    assert not r["comparisons"] and "guidance_invalid" in r["reasons"]


def test_tiny_financial_baseline_never_crashes_percentage_formatting():
    from decimal import Decimal
    p=workspace(metric="revenue",unit="USD_millions")
    c=workspace(1,2,later=True,metric="revenue",unit="USD_millions")
    for ws in (p,c):
        ws["guidance"][0].update(basis="gaap",currency="USD")
    p["guidance"][0].update(low=Decimal("1e-30"),high=Decimal("1e-30"))
    r=compare(c,p)
    assert r["comparisons"]
    assert r["comparisons"][0]["relative_change_pct"] is not None
    json.dumps(r,allow_nan=False)


# r6: unrelated Decimal users must not change the same evidence comparison.
@pytest.mark.parametrize("rounding", ["ROUND_FLOOR", "ROUND_CEILING"])
def test_comparison_does_not_inherit_decimal_rounding(rounding):
    from decimal import localcontext
    previous = workspace(); current = workspace(76000, 78000, later=True)
    expected = compare(current, previous)
    with localcontext() as context:
        context.prec = 8
        context.rounding = rounding
        assert compare(current, previous) == expected


def test_comparison_does_not_inherit_decimal_traps_or_exponents():
    from decimal import Inexact, Rounded, localcontext
    previous = workspace(); current = workspace(76000, 78000, later=True)
    expected = compare(current, previous)
    with localcontext() as context:
        context.prec = 8
        context.Emax = 4
        context.Emin = -4
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        assert compare(current, previous) == expected


def test_supported_amount_ceiling_is_checked_without_context_rounding():
    from decimal import Decimal
    current = workspace(Decimal("1000000000000000000000000000000.1"),
                        Decimal("1000000000000000000000000000000.2"),
                        later=True, unit="USD", metric="revenue")
    prior = workspace(1, 2, unit="USD", metric="revenue")
    for item in (current, prior):
        item["guidance"][0].update(basis="gaap", currency="USD")
    result = compare(current, prior)
    assert not result["comparisons"] and "guidance_invalid" in result["reasons"]


def test_late_arriving_older_disclosure_is_not_a_new_guidance_change():
    current = workspace(76000, 78000, later=True)
    current["lifecycle"]["source_available_at"] = "2026-09-22T15:00:00+00:00"
    result = compare(current, workspace())
    assert not result["comparisons"] and "revision_order_invalid" in result["reasons"]


@pytest.mark.parametrize("basis", [[], {}, True, "unknown"])
def test_malformed_financial_basis_returns_named_absence(basis):
    current = workspace(76, 78, later=True, metric="revenue", unit="USD")
    prior = workspace(100, 103, metric="revenue", unit="USD")
    for item in (current, prior):
        item["guidance"][0].update(basis=basis, currency="USD")
    result = compare(current, prior)
    assert not result["comparisons"] and "measurement_basis_missing" in result["reasons"]


@pytest.mark.parametrize("field,value", [("document_id", None), ("document_id", ""),
                                        ("span_id", None), ("document_version", True),
                                        ("document_version", 0)])
def test_receipt_identity_cannot_be_absent_on_both_sides(field, value):
    current = workspace(76000, 78000, later=True)
    current["guidance"][0]["source_span"][field] = value
    if field == "document_id":
        current["sources"][0][field] = value
    result = compare(current, workspace())
    assert not result["comparisons"] and "guidance_evidence_invalid" in result["reasons"]


# R8: disclosure clocks belong to the exact cited source, not its release sibling.
def transcript_workspace(*, later=False, known=True):
    from engine.company_intelligence.qa_exchange import source_clock_payload
    result = workspace(76000 if later else 100000, 78000 if later else 103000, later=later)
    source = result["sources"][0]
    source["kind"] = "transcript"
    day = "24" if later else "23"
    source["source_clock"] = source_clock_payload(
        document_id=source["document_id"], source_sha256=source["source_sha256"],
        source_available_at=f"2026-09-{day}T15:10:00+00:00" if known else None,
        system_recorded_at=f"2026-09-{day}T15:20:00+00:00")
    return result


def test_transcript_guidance_uses_its_own_source_clock_not_release_clock():
    c, p = transcript_workspace(later=True), transcript_workspace()
    result = compare(c, p)
    assert result["available"]
    evidence = result["comparisons"][0]["evidence"]
    assert evidence[0]["source_available_at"] == "2026-09-24T15:10:00+00:00"
    assert evidence[0]["observed_at"] == "2026-09-24T15:20:00+00:00"
    assert evidence[1]["observed_at"] == "2026-09-23T15:20:00+00:00"


def test_transcript_clock_unknown_does_not_inherit_known_release_time():
    result = compare(transcript_workspace(later=True, known=False), transcript_workspace())
    assert not result["available"] and "guidance_source_clock_unknown" in result["reasons"]


def test_transcript_clock_absent_does_not_inherit_known_release_time():
    c = transcript_workspace(later=True); c["sources"][0].pop("source_clock")
    result = compare(c, transcript_workspace())
    assert not result["available"] and "guidance_source_clock_missing" in result["reasons"]


@pytest.mark.parametrize("field,value", [
    ("document_id", "wrong-source"), ("source_sha256", "0"*64),
    ("rights_profile", "rp_unknown_v1"), ("clock_state", []),
    ("source_available_at", "2026-09-24T15:10:00"),
    ("system_recorded_at", "not-a-time"),
    ("system_recorded_at", "2026-09-24T16:01:00+00:00"),
    ("system_recorded_at", "2026-09-24T15:09:00+00:00"),
])
def test_invalid_or_future_source_clock_cannot_reach_news(field, value):
    c = transcript_workspace(later=True); c["sources"][0]["source_clock"][field] = value
    result = compare(c, transcript_workspace())
    assert not result["available"] and "guidance_source_clock_invalid" in result["reasons"]


def test_transcript_update_survives_unchanged_issuer_release_lifecycle_clock():
    c, p = transcript_workspace(later=True), transcript_workspace()
    c["lifecycle"] = deepcopy(p["lifecycle"])
    result = compare(c, p)
    assert result["available"] and result["comparisons"][0]["midpoint_delta"] == "-24500"


def test_old_transcript_arriving_after_new_release_is_not_new_guidance():
    c, p = transcript_workspace(later=True), transcript_workspace()
    c["sources"][0]["source_clock"]["source_available_at"] = "2026-09-22T15:10:00+00:00"
    result = compare(c, p)
    assert not result["available"] and "revision_order_invalid" in result["reasons"]


def test_explicit_unknown_release_source_clock_cannot_fall_back_to_lifecycle():
    c, p = transcript_workspace(later=True, known=False), workspace()
    c["sources"][0]["kind"] = "issuer_release"
    result = compare(c, p)
    assert not result["available"] and "guidance_source_clock_unknown" in result["reasons"]


@pytest.mark.parametrize("kind", [None, "news_article", [], {}])
def test_unrecognized_source_kind_cannot_borrow_the_event_clock(kind):
    c = workspace(later=True); c["sources"][0]["kind"] = kind
    result = compare(c, workspace())
    assert not result["available"] and "guidance_source_kind_unsupported" in result["reasons"]


def test_unknown_prior_transcript_clock_refuses_only_affected_comparison():
    result = compare(transcript_workspace(later=True), transcript_workspace(known=False))
    assert not result["available"] and "guidance_source_clock_unknown" in result["reasons"]


def test_multiple_release_sources_cannot_share_one_lifecycle_clock():
    c = workspace(later=True)
    other = deepcopy(c["sources"][0]); other["document_id"] = "other-release"
    c["sources"].append(other)
    result = compare(c, workspace())
    assert not result["available"] and "guidance_source_clock_ambiguous" in result["reasons"]
