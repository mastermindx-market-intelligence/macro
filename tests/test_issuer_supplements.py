from pathlib import Path
from copy import deepcopy
import json
from hashlib import sha256
import pytest
from engine.company_intelligence.issuer_supplements import build_issuer_supplement,validate_supplement_source,append_issuer_supplements
from engine.company_intelligence.event_workspace import write_workspace_generation,validate_generation_clocks
from tests.test_government_revenue_defense_owner_adapter import make_workspace

FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'
FILING={'cik':'0000202058','accession':'0000202058-26-000058','form':'10-Q','filing_date':'2026-07-30','acceptance_datetime':'2026-07-30T13:06:49Z','report_date':'2026-07-03','primary_document':'hrs-20260703.htm'}
URL='https://www.sec.gov/Archives/edgar/data/202058/000020205826000058/hrs-20260703.htm'
SALE_URL='https://investors.l3harris.com/news/news-details/2026/L3Harris-Completes-Sale-of-Majority-Stake-in-Commercial-Space-Propulsion-Power-and-Electronics-Businesses-to-AE-Industrial-Partners/default.aspx'


def held(kind='LHX_10Q',mutate=lambda x:x,**overrides):
    name='10Q' if kind=='LHX_10Q' else 'sale';body=mutate((FIXTURES/f'LHX.{name}.html').read_bytes().decode())
    observed='2026-10-13T04:28:48Z'
    args=dict(kind=kind,body=body,url=URL if name=='10Q' else SALE_URL,filing=deepcopy(FILING) if name=='10Q' else None,event_id='evt_cik0000202058_2026q2_results',period='2026Q2' if name=='10Q' else '2026-08-04',observed_at=observed,source_available_at=FILING['acceptance_datetime'] if name=='10Q' else observed,expected_sha256=sha256(body.encode()).hexdigest())
    args.update(overrides);return build_issuer_supplement(**args)


def test_native_10q_and_issuer_publication_keep_distinct_identity_availability_basis():
    q,sale=held(),held('LHX_sale')
    validate_supplement_source(q['source'],event_id=q['facts'][0]['event_id']);validate_supplement_source(sale['source'],event_id=sale['facts'][0]['event_id'])
    assert q['source']['filing_key']=={'cik':'0000202058','accession':'0000202058-26-000058'}
    assert sale['source']['filing_key'] is None and sale['source']['form'] is None
    assert q['source']['document_id']!=sale['source']['document_id']
    assert sale['source']['source_document']['published_at'] is None
    assert sale['source']['source_clock']['available_at']==sale['source']['source_clock']['observed_at']


def test_preferred_conditional_terms_and_net_total_sale_basis_remain_explicit():
    q=held();sale=held('LHX_sale');facts={f['metric']:f for f in q['facts']+sale['facts']}
    assert '7% cumulative annual dividends, compounded quarterly' in facts['msl_preferred_payout_terms']['value']
    assert facts['msl_qipo_conversion_terms']['fact_class']=='company_forward'
    assert 'Upon completion of a QIPO' in facts['msl_qipo_conversion_terms']['value'] and '20% discount' in facts['msl_qipo_conversion_terms']['value']
    assert 'net enterprise value of $825 million' in facts['space_business_sale_pending_terms']['value']
    assert 'total enterprise value of $845 million' in facts['space_business_sale_completed_terms']['value']
    assert 'RS-25' in facts['space_business_sale_retained_scope']['value'] and '~40%' in facts['space_business_sale_retained_scope']['value']
    assert facts['space_business_sale_pending_terms']['basis']!=facts['space_business_sale_completed_terms']['basis']


def test_wrong_body_native_accession_origin_or_period_does_not_admit():
    with pytest.raises(ValueError,match='hash'):held(expected_sha256='0'*64)
    with pytest.raises(ValueError,match='native_url'):held(filing=dict(FILING,accession='0000202058-26-000059'))
    with pytest.raises(ValueError,match='form'):held(filing=dict(FILING,form='8-K'))
    with pytest.raises(ValueError,match='period'):held(period='2025Q2')
    with pytest.raises(ValueError,match='mismatch'):held(url=URL.replace('www.sec.gov','sec.example.com'))


def test_issuer_publication_cannot_borrow_SEC_clock_or_a_filing_key():
    with pytest.raises(ValueError,match='unproved'):held('LHX_sale',source_available_at='2026-08-04T00:00:00Z')
    with pytest.raises(ValueError,match='not_native'):held('LHX_sale',filing=FILING)


def test_append_keeps_original_ex99_lifecycle_and_generation_covers_newdoc_observation(tmp_path):
    base=make_workspace('LHX');original=deepcopy(base['lifecycle']);q,sale=held(),held('LHX_sale')
    row=append_issuer_supplements(base,[q,sale]);assert row['lifecycle']==original
    generation=write_workspace_generation(tmp_path/'company_intelligence',{row['event_id']:row})
    manifest=json.loads((generation/'manifest.json').read_text());published=json.loads((generation/'workspaces'/f'{row["event_id"]}.json').read_text())
    assert manifest['generated_at']=='2026-10-13T04:28:48Z'
    assert manifest['source_clock']=='2026-10-13T04:28:48Z'
    assert published['lifecycle']==original
    assert len([f for f in published['facts'] if f.get('unit')=='source_reported_terms'])==7
    broken=deepcopy(manifest);broken['generated_at']=original['observed_at'];published['generated_at']=broken['generated_at']
    with pytest.raises(ValueError,match='supplemental'):validate_generation_clocks(broken,{row['event_id']:published})


def test_first_observation_preserved_for_same_supplement_and_duplicate_event_refused():
    q=held();again=held(observed_at='2026-10-14T04:28:48Z',prior=q['source'])
    assert q['source']['source_clock']==again['source']['source_clock']
    sale=held('LHX_sale');sale_again=held('LHX_sale',observed_at='2026-10-14T04:28:48Z',source_available_at='2026-10-14T04:28:48Z',prior=sale['source'])
    assert sale_again['source']['source_clock']==sale['source']['source_clock']
    base=make_workspace('LHX')
    with pytest.raises(ValueError,match='duplicate'):append_issuer_supplements(base,[q,q])
    broken=deepcopy(q);broken['source']['source_document']['event_id']='evt_cik0000101829_2026q2_results'
    with pytest.raises(ValueError,match='event'):append_issuer_supplements(base,[broken])


# Literal retained parser fragment, not the complete SEC body or its SHA.
RMS_URL = "https://www.sec.gov/Archives/edgar/data/936468/000162828026049277/ex991q22026.htm"
RMS_EVENT = "evt_cik0000936468_2026q2_results"
RMS_CAPTURE = "2026-10-16T04:14:04Z"
RMS_FILING = {"cik":"0000936468", "accession":"0001628280-26-049277", "form":"8-K", "filing_date":"2026-07-23", "acceptance_datetime":"2026-07-23T10:30:57Z", "report_date":"2026-07-23"}


def rms_held(mutate=lambda value:value, **overrides):
    body = mutate((FIXTURES / "LMT.RMS.fragment.html").read_text())
    args = dict(kind="LMT_RMS", body=body, url=RMS_URL, filing=deepcopy(RMS_FILING), event_id=RMS_EVENT, period="2026Q2", observed_at=RMS_CAPTURE, source_available_at=RMS_CAPTURE, expected_sha256=sha256(body.encode()).hexdigest())
    args.update(overrides)
    return build_issuer_supplement(**args)


def test_rms_reports_quarter_cells_with_negative_prior_without_replacing_original_release(tmp_path):
    supplement = rms_held()
    base = make_workspace("LMT")
    before = deepcopy(base)
    row = append_issuer_supplements(base, [supplement])
    assert row["sources"][:-1] == before["sources"]
    assert row["facts"][:-6] == before["facts"]
    assert row["lifecycle"] == before["lifecycle"] and base == before
    assert supplement["source"]["document_id"] != before["sources"][0]["document_id"]
    facts = {fact["metric"]: fact for fact in supplement["facts"]}
    expected = {"fleet_rms_sales":4354, "fleet_rms_sales_prior":3995, "fleet_rms_operating_profit":437, "fleet_rms_operating_profit_prior":-172, "fleet_rms_margin":10.0, "fleet_rms_margin_prior":-4.3}
    assert {key:value["value"] for key,value in facts.items()} == expected
    assert facts["fleet_rms_sales"]["unit"] == "USD_million"
    assert facts["fleet_rms_margin_prior"]["unit"] == "percent"
    assert facts["fleet_rms_sales_prior"]["period"] == "2025Q2"
    assert all(f["basis"] == "issuer_reported_segment:Rotary and Mission Systems:reported" for f in facts.values())
    from engine.government_revenue.defense_economics_producer import build_defense_economics_payload
    workspaces = {ws["event_id"]:ws for ws in [row,make_workspace("RTX"),make_workspace("NOC"),make_workspace("LHX")]}
    write_workspace_generation(tmp_path/"data/company_intelligence",workspaces)
    current = build_defense_economics_payload(tmp_path,generated_at="2026-10-18T01:00:00Z")
    lmt = next(profile for profile in current["profiles"] if profile["issuer_id"]=="cik:0000936468")
    projected = {fact["fact_id"].rsplit(":",1)[-1]:fact for fact in lmt["axes"]["economics"]["facts"]}
    assert {key:projected[key]["value"] for key in expected} == expected
    assert projected["defense_segment_sales"]["value"] == 4101  # incumbent MFC stays distinct
    assert all(projected[key]["owner_ref"] != projected["defense_segment_sales"]["owner_ref"] for key in expected)
    assert lmt["program_workshare"] is None and lmt["shareholder_capture"]["state"]=="not_asserted"
    old = build_defense_economics_payload(tmp_path,generated_at="2026-10-18T01:00:00Z",as_of="2026-10-15T00:00:00Z")
    assert all("fleet_rms_" not in fact["fact_id"] for profile in old["profiles"] for fact in profile["axes"]["economics"]["facts"])


@pytest.mark.parametrize("overrides", [
    {"event_id":"evt_cik0000202058_2026q2_results"}, {"period":"2025Q2"},
    {"url":RMS_URL.replace("www.sec.gov","sec.example.com")},
    {"url":RMS_URL.replace("936468/","202058/")},
    {"url":RMS_URL+"?different=1"}, {"expected_sha256":"0"*64},
    {"source_available_at":RMS_FILING["acceptance_datetime"]},
    {"filing":{**RMS_FILING,"form":"8-K/A"}},
])
def test_rms_closed_identity_hash_and_conservative_clock_refuse(overrides):
    with pytest.raises(ValueError):rms_held(**overrides)


@pytest.mark.parametrize("old,new", [("millions","thousands"),("Quarters Ended","Six Months Ended"),("Operating profit (loss)","Adjusted profit")])
def test_rms_missing_unit_quarter_or_reported_row_refuses(old,new):
    # Visible retained literals can span HTML tags; change their literal text nodes.
    body=(FIXTURES/"LMT.RMS.fragment.html").read_text()
    assert old in body
    with pytest.raises(ValueError):rms_held(mutate=lambda value:value.replace(old,new))


@pytest.mark.parametrize("old,new", [("(4.3","4.3"),("%)","%")])
def test_rms_split_percent_cannot_drop_either_negative_parenthesis(old,new):
    with pytest.raises(ValueError):rms_held(mutate=lambda value:value.replace(old,new))


def test_rms_preserves_first_capture_and_refuses_workspace_period_or_projected_sign_tampering():
    supplement=rms_held()
    later=rms_held(observed_at="2026-10-17T04:14:04Z",source_available_at="2026-10-17T04:14:04Z",prior=supplement["source"])
    assert later["source"]["source_clock"]==supplement["source"]["source_clock"]
    wrong=make_workspace("LMT");wrong["fiscal_period"]["year"]=2025
    with pytest.raises(ValueError):append_issuer_supplements(wrong,[supplement])
    from engine.government_revenue.defense_economics_producer import _project_fact
    margin=deepcopy(next(f for f in supplement["facts"] if f["metric"]=="fleet_rms_margin_prior"))
    margin["value"]=4.3
    with pytest.raises(ValueError,match="literal"):
        _project_fact(margin,make_workspace("LMT"),supplement["source"],owner_ref="test-only")


def test_rms_null_receipt_is_a_qualified_refusal():
    from engine.company_intelligence.rms_segment_profile import receipt_value
    with pytest.raises(ValueError):receipt_value(None,"fleet_rms_margin_prior")


def test_rms_subsecond_retrieval_never_becomes_visible_before_actual_capture(tmp_path):
    captured="2026-10-16T04:14:04.500000Z"
    supplement=rms_held(observed_at=captured,source_available_at=captured)
    assert supplement["source"]["source_clock"]=={
        "observed_at":"2026-10-16T04:14:05Z","available_at":"2026-10-16T04:14:05Z"}
    from engine.government_revenue.defense_economics_producer import build_defense_economics_payload
    rows=[append_issuer_supplements(make_workspace("LMT"),[supplement])]
    rows.extend(make_workspace(t) for t in ("RTX","NOC","LHX"))
    write_workspace_generation(tmp_path/"data/company_intelligence",{row["event_id"]:row for row in rows})
    result=build_defense_economics_payload(tmp_path,generated_at="2026-10-18T01:00:00Z",as_of="2026-10-16T04:14:04.900000Z")
    assert all("fleet_rms_" not in fact["fact_id"] for profile in result["profiles"] for fact in profile["axes"]["economics"]["facts"])
