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


@pytest.mark.parametrize("input_mode", ["explicit_pair", "release_history"])
def test_existing_news_builder_writes_comparison_on_same_per_ticker_artifact(monkeypatch,tmp_path,input_mode):
    import engine,sys,types
    from pathlib import Path
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
    if input_mode == "release_history":
        history, transport_calls = transport_release_history(monkeypatch,
            [workspace(), workspace(76000,78000,later=True,status="revised")])
        assert len(transport_calls) == 5
        source_input = {"expected_security_id":"xnas:ACME", "event_id":EVENT,
                        "release_revisions":history}
    else:
        source_input = {"expected_security_id":"xnas:ACME",
                        "current":workspace(76000,78000,later=True),"prior":workspace()}
    build_news.build(guidance_workspaces={"ACME":source_input})
    artifact=json.loads((tmp_path/"site/news/by_ticker.json").read_text())
    row=artifact["tickers"]["ACME"]
    assert artifact["schema"]=="news_flow.v1" and row["n_recent"]==1
    assert row["guidance_context"]["comparisons"][0]["midpoint_delta"]=="-24500"
    assert row["guidance_context"]["as_of"]==ASOF.isoformat()
    if input_mode == "release_history":
        from scripts import build_ticker_pages as pages
        from jinja2 import Environment, FileSystemLoader
        aggregate = pages.load_all_aggregates(tmp_path/"site")
        page = pages.build_page_context("ACME","Synthetic","Technology",{},aggregate,ASOF.isoformat())
        html = Environment(loader=FileSystemLoader(str(Path(build_news.__file__).parents[1]/"templates")),
                           autoescape=True).get_template("ticker.html.j2").render(**page)
        assert "76,000–78,000 vehicles" in html and "-24,500 vehicles" in html
        assert len(transport_calls) == 5




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


# R9: selection consumes the existing release-history reader, not another store.
def release_revision(ws):
    from engine.neuralweb.company_intelligence_reader import _receipt_from_revision
    body = json.dumps(ws, sort_keys=True, allow_nan=False).encode()
    return _receipt_from_revision(ws, generation_id=ws['generation_id'],
        workspace_receipt={'sha256': sha256(body).hexdigest(), 'bytes': len(body)})


def history_context(revisions, *, event_id=EVENT, ticker=None, expected_security_id=None):
    from engine.company_intelligence import guidance_comparison as comparison
    fn = getattr(comparison, 'compare_release_guidance_history', None)
    assert callable(fn), 'Release history is not connected to guidance baseline selection'
    return fn(revisions, event_id=event_id, as_of=ASOF, ticker=ticker,
              expected_security_id=expected_security_id)


def release_history():
    return [release_revision(workspace()),
            release_revision(workspace(76000, 78000, later=True, status='revised'))]


def test_release_history_selects_the_latest_adjacent_disclosures_without_mutating_input():
    history = release_history(); before = deepcopy(history)
    result = history_context(history)
    expected = compare(history[-1]['workspace'], history[-2]['workspace'])
    assert result == expected and result['comparisons'][0]['midpoint_delta'] == '-24500'
    assert history == before


@pytest.mark.parametrize('bad', [None, {}, 'history', (1, 2), [None]])
def test_malformed_release_history_is_absent(bad):
    result = history_context(bad)
    assert not result['available'] and result['reasons'] == ['release_history_invalid']


def test_missing_release_history_is_not_zero_change():
    result = history_context([])
    assert not result['available'] and result['reasons'] == ['release_history_empty']


def test_first_release_has_no_invented_baseline():
    result = history_context(release_history()[:1])
    assert not result['available'] and result['reasons'] == ['prior_not_supplied']


@pytest.mark.parametrize('field,value', [
    ('generation_id', 'f'*24), ('source_sha256', '0'*64),
    ('source_available_at', '2026-09-20T15:00:00+00:00'),
    ('observed_at', '2026-09-20T15:00:00+00:00'),
    ('lifecycle_state', 'complete'), ('form', 'invented'),
])
def test_release_history_metadata_must_match_its_workspace(field, value):
    history = release_history(); history[-1][field] = value
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['release_history_metadata_mismatch']


@pytest.mark.parametrize('receipt', [None, {}, {'sha256':'bad','bytes':20},
    {'sha256':'0'*64,'bytes':True}, {'sha256':'0'*64,'bytes':0},
    {'sha256':'0'*64,'bytes':524289}])
def test_release_history_requires_owner_workspace_receipt_shape(receipt):
    history = release_history(); history[-1]['workspace_receipt'] = receipt
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['release_history_receipt_invalid']


def test_release_history_refuses_order_changes_instead_of_sorting_to_a_good_answer():
    result = history_context(list(reversed(release_history())))
    assert not result['available'] and result['reasons'] == ['release_history_order_invalid']


def test_release_history_refuses_a_mixed_event_even_when_issuer_and_horizon_match():
    history = release_history(); history[0]['workspace']['event_id'] = 'evt_cik0000000001_2026q2_results'
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['release_history_identity_mismatch']


def test_release_history_cannot_replay_duplicate_generations():
    history = release_history(); history[-1]['generation_id'] = history[0]['generation_id']
    history[-1]['workspace']['generation_id'] = history[0]['generation_id']
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['release_history_duplicate_generation']


def test_release_history_does_not_globally_deduplicate_return_to_earlier_outlook():
    history = release_history()
    earlier = deepcopy(history[0]['workspace']); earlier['generation_id'] = 'c'*24
    earlier['lifecycle']['source_available_at'] = '2026-09-24T15:30:00+00:00'
    earlier['lifecycle']['observed_at'] = '2026-09-24T15:30:00+00:00'
    earlier['generated_at'] = '2026-09-24T15:30:00+00:00'
    history.append(release_revision(earlier))
    result = history_context(history)
    assert result['available'] and result['comparisons'][0]['midpoint_delta'] == '24500'
    assert result['comparisons'][0]['evidence'][0]['generation_id'] == 'c'*24


def test_release_history_does_not_fall_back_past_the_latest_actual_only_release():
    history = release_history(); actual = deepcopy(history[-1]['workspace'])
    actual['guidance'] = []; history[-1] = release_revision(actual)
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['guidance_absent']


def test_release_history_never_treats_transcript_rows_as_complete_guidance_history():
    history = [release_revision(transcript_workspace()), release_revision(transcript_workspace(later=True))]
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['release_history_guidance_source_mismatch']


def test_release_history_refuses_oversize_instead_of_truncating_a_baseline():
    result = history_context([release_history()[0]] * 65)
    assert not result['available'] and result['reasons'] == ['release_history_bound_exceeded']


def test_release_history_keeps_security_binding_as_a_separate_required_join():
    history = release_history()
    result = history_context(history, ticker='ACME')
    assert not result['available'] and result['reasons'] == ['listing_binding_missing']
    security = history[-1]['workspace']['issuer']['listings'][0]['security_id']
    result = history_context(history, ticker='ACME', expected_security_id=security)
    assert result['available']


def test_release_history_does_not_search_older_revisions_for_a_convenient_baseline():
    history = release_history(); middle = deepcopy(history[0]['workspace'])
    middle['generation_id'] = 'd'*24
    middle['guidance'][0]['horizon'] = 'FY2026 Q3'
    middle['lifecycle']['observed_at'] = '2026-09-23T18:00:00+00:00'
    middle['lifecycle']['source_available_at'] = '2026-09-23T18:00:00+00:00'
    middle['sources'][0]['source_sha256'] = 'd'*64
    history.insert(1, release_revision(middle))
    result = history_context(history)
    assert not result['available'] and result['reasons'] == ['prior_comparable_missing']



def transport_release_history(monkeypatch, workspaces, *, corrupt=False):
    """Exercise the actual legacy reader; only byte transport is replaced."""
    from engine.neuralweb import company_intelligence_reader as reader
    from engine.company_intelligence.event_workspace import validate_workspace_manifest
    base = 'https://example.test/company_intelligence/event_workspaces'
    objects = {}; previous_id = previous_sha = None
    for ws in workspaces:
        body = json.dumps(ws,sort_keys=True,allow_nan=False).encode()
        generation = ws['generation_id']
        manifest = {'schema':'event_workspace_manifest.v2','generation_id':generation,
            'generated_at':ws['generated_at'],'status':'ready','event_count':1,
            'files':{f'workspaces/{ws["event_id"]}.json':{'bytes':len(body),'sha256':sha256(body).hexdigest()}},
            'aliases':{},'authority':'context_only','warnings':[],
            'previous_generation_id':previous_id,'previous_manifest_sha256':previous_sha}
        validate_workspace_manifest(manifest)
        raw_manifest = json.dumps(manifest,sort_keys=True,allow_nan=False).encode()
        objects[f'{base}/generations/{generation}/manifest.json'] = raw_manifest
        objects[f'{base}/generations/{generation}/workspaces/{ws["event_id"]}.json'] = body
        previous_id, previous_sha = generation, sha256(raw_manifest).hexdigest()
    objects[f'{base}/manifest.json'] = raw_manifest
    if corrupt:
        key = f'{base}/generations/{previous_id}/workspaces/{workspaces[-1]["event_id"]}.json'
        objects[key] += b' '
    calls = []
    def fetch(url, *, limit, allow_404=False):
        calls.append(url)
        assert url in objects, 'Unexpected endpoint in synthetic transport'
        assert len(objects[url]) <= limit
        return objects[url]
    monkeypatch.setattr(reader,'_fetch_bytes',fetch)
    result = reader.read_all_event_source_revisions([EVENT],base_url='https://example.test/company_intelligence')
    return result[EVENT], calls


def test_existing_reader_output_drives_selection_with_raw_receipts(monkeypatch):
    old, current = workspace(), workspace(76000,78000,later=True,status='revised')
    history, calls = transport_release_history(monkeypatch,[old,current])
    result = history_context(history)
    assert result['available'] and result['comparisons'][0]['midpoint_delta']=='-24500'
    assert len(calls)==5 and len(set(calls))==5
    assert history[0]['workspace_receipt']['sha256']==sha256(json.dumps(old,sort_keys=True,allow_nan=False).encode()).hexdigest()


def test_existing_reader_rejects_corrupt_bytes_before_selection(monkeypatch):
    from engine.neuralweb.company_intelligence_reader import WorkspaceChainIntegrityError
    with pytest.raises(WorkspaceChainIntegrityError):
        transport_release_history(monkeypatch,[workspace(),workspace(76000,78000,later=True)],corrupt=True)


def test_release_history_rejects_consecutive_source_copies_as_new_revisions():
    history=release_history()
    copied=deepcopy(history[0]['workspace'])
    copied['generation_id']=history[-1]['generation_id']
    copied['lifecycle']=deepcopy(history[-1]['workspace']['lifecycle'])
    history[-1]=release_revision(copied)
    result=history_context(history)
    assert not result['available'] and result['reasons']==['release_history_duplicate_source']



def test_release_reader_deduplication_cannot_hide_a_transcript_change_as_release_guidance(monkeypatch):
    older, newer = transcript_workspace(), transcript_workspace(later=True)
    release = deepcopy(workspace()["sources"][0]); release["document_id"] = "distinct-release"
    for ws in (older,newer):
        ws["sources"].append(deepcopy(release))
    history, calls = transport_release_history(monkeypatch,[older,newer])
    assert len(history)==1 and len(calls)==5  # owner's release-only deduplication
    result = history_context(history)
    assert not result["available"]
    assert result["reasons"]==["release_history_guidance_source_mismatch"]



def test_two_release_revisions_still_cannot_certify_transcript_guidance_history(monkeypatch):
    workspaces = [transcript_workspace(),transcript_workspace(later=True)]
    for i,ws in enumerate(workspaces):
        release = deepcopy(workspace(76000 if i else 100000, 78000 if i else 103000, later=bool(i))["sources"][0])
        release["document_id"] = "distinct-release-"+str(i)
        ws["sources"].append(release)
    history,_ = transport_release_history(monkeypatch,workspaces)
    assert len(history)==2
    result=history_context(history)
    assert not result["available"] and result["reasons"]==["release_history_guidance_source_mismatch"]
