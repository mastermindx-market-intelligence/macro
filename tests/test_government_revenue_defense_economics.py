from copy import deepcopy
import pytest
from engine.government_revenue.defense_economics import compose_defense_economics

NOW='2026-10-13T03:00:00Z'
BINDINGS={'identity':{'sha256':'a'*64,'issuer_id':'ISS:US-XNYS-NOC','security_id':'SEC:US-XNYS-NOC'}, 'company':{'sha256':'b'*64,'owner_family':'company_intelligence','issuer_id':'ISS:US-XNYS-NOC','security_id':'SEC:US-XNYS-NOC','periods':['2026Q2']},
          'market':{'sha256':'c'*64},'gov':{'sha256':'d'*64}}

def fixture():
    fact=dict(fact_id='issuer:segment-sales', value=2093, unit='USD_million',
              period='2026Q2', accounting_basis='issuer_reported_segment',
              fact_class='reported_segment_sales', owner_ref='company',
              source_span=dict(receipt_state='byte_replayed',text_sha256='e'*64,
                               document_id='sec:release:1'))
    axis=dict(display_scope='government_revenue_entitled',state='supported',
              owner_ref='company',observed_at='2026-07-21T10:00:00Z',
              summary_en='Sales rose while profitability fell.', summary_zh='销售增长而盈利下降。',
              fiscal_period='2026Q2', facts=[fact])
    return {'NOC':dict(identity_owner_ref='identity',
        identity={'identity_mode':'current','issuer_binding':{'issuer_id':'ISS:US-XNYS-NOC'},
                  'security_id':'SEC:US-XNYS-NOC'}, axes={'economics':axis},
        contrary_case='USD68M unfavorable SiAW EAC; operating income declined38%.')}

def profile(payload):
    return next(v for v in payload['profiles'] if v['ticker_display']=='NOC')

def compose(x):
    return compose_defense_economics(x,generated_at=NOW,source_bindings=BINDINGS)

def test_optional_missing_axes_do_not_erase_qualified_financial_evidence():
    row=profile(compose(fixture()))
    assert row['axes']['economics']['facts'][0]['value']==2093
    assert row['axes']['recognition']['state']=='missing_owner'
    assert row['research_state']=='EVIDENCE_INSUFFICIENT'
    assert row['program_workshare'] is None
    assert 'USD68M' in row['contrary_case']

def test_unqualified_identity_cannot_attribute_supplied_company_numbers():
    x=fixture();x['NOC']['identity_owner_ref']='unknown'
    row=profile(compose(x));assert row['issuer_id'] is None
    assert row['axes']['economics']['facts']==[]

def test_metadata_only_or_pending_citation_never_becomes_financial_truth():
    for change in ({'claim_citations_pending':True},{'summary_lineage':'score_overlay'}):
        x=fixture();x['NOC']['axes']['economics'].update(change)
        assert profile(compose(x))['axes']['economics']['facts']==[]

def test_missing_period_and_address_only_span_refuse_without_inventing_zero():
    for key,value in [('period',None),('source_span',{'receipt_state':'address_only'})]:
        x=fixture();x['NOC']['axes']['economics']['facts'][0][key]=value
        row=profile(compose(x))['axes']['economics']
        assert row['state']=='unreviewed' and row['facts']==[]

def test_derived_ratio_cannot_use_another_period_or_unit():
    for change in ({'period':'2025Q2'},{'unit':'USD_billion'}):
        x=fixture();f=x['NOC']['axes']['economics']['facts'][0]
        f['derived']=True;f['numerator']={'period':f['period'],'unit':f['unit'],
             'accounting_basis':f['accounting_basis'],'owner_ref':'company'}
        f['denominator']={'period':f['period'],'unit':f['unit'],
             'accounting_basis':f['accounting_basis'],'owner_ref':'company',**change}
        assert profile(compose(x))['axes']['economics']['facts']==[]

def test_recent_generation_cannot_remove_stale_observation_state():
    x=fixture();x['NOC']['axes']['economics']['state']='stale'
    row=profile(compose(x))['axes']['economics']
    assert row['state']=='stale' and row['observed_at']=='2026-07-21T10:00:00Z'
    assert row['facts'][0]['value']==2093

def test_unqualified_display_scope_never_exports_admitted_private_numbers():
    x=fixture();x['NOC']['axes']['economics']['display_scope']='company_private'
    assert profile(compose(x))['axes']['economics']['facts']==[]

def test_future_observation_and_nonfinite_owner_value_refuse():
    x=fixture();x['NOC']['axes']['economics']['observed_at']='2026-12-01T00:00:00Z'
    assert profile(compose(x))['axes']['economics']['state']=='contradictory'
    x=fixture();x['NOC']['axes']['economics']['facts'][0]['value']=float('nan')
    assert profile(compose(x))['axes']['economics']['facts']==[]

def test_observed_expectations_are_not_minted_from_scenario_or_price():
    x=fixture();x['NOC']['axes']['recognition']={**x['NOC']['axes']['economics'],
        'expectations_kind':'not_priced_in','owner_ref':'market'}
    assert profile(compose(x))['axes']['recognition']['state']=='unreviewed'

def test_source_correction_changes_identity_generation_clock_alone_does_not():
    x=fixture();before=deepcopy(x);first=compose(x)
    assert x==before
    later=compose_defense_economics(x,generated_at='2026-10-14T03:00:00Z',source_bindings=BINDINGS)
    assert first['content_id']==later['content_id']
    revised=deepcopy(BINDINGS);revised['company']['sha256']='f'*64
    updated=compose_defense_economics(x,generated_at=NOW,source_bindings=revised)
    assert first['content_id']!=updated['content_id']
    assert list(profile(first)['axes'])==['participation','demand','economics','recognition']
    assert not profile(first)['authority']['can_rank']


def test_government_amount_cannot_be_relabelled_issuer_revenue_or_backlog():
    x=fixture();x['NOC']['axes']['economics']['facts'][0]['owner_ref']='gov'
    assert profile(compose(x))['axes']['economics']['facts']==[]

def test_duplicate_source_facts_count_once_and_private_body_is_not_forwarded():
    x=fixture();f=x['NOC']['axes']['economics']['facts'][0]
    f['private_body']='PRIVATE_SENTINEL';f['source_span']['body']='WHOLE_DOCUMENT_SENTINEL'
    x['NOC']['axes']['economics']['facts'].append(deepcopy(f))
    y=compose(x);facts=profile(y)['axes']['economics']['facts']
    assert len(facts)==1
    assert 'PRIVATE_SENTINEL' not in str(y) and 'WHOLE_DOCUMENT_SENTINEL' not in str(y)


def test_wrong_issuer_or_period_source_binding_refuses_fact_attribution():
    for change in ({'issuer_id':'ISS:US-XNYS-LMT'},{'security_id':'SEC:US-XNYS-LMT'},{'periods':['2025Q2']}):
        revised=deepcopy(BINDINGS);revised['company'].update(change)
        y=compose_defense_economics(fixture(),generated_at=NOW,source_bindings=revised)
        assert profile(y)['axes']['economics']['facts']==[]

def test_raw_recognition_and_nested_fields_do_not_escape_projection():
    x=fixture();x['NOC']['axes']['recognition']={**x['NOC']['axes']['economics'],
        'price_response':{'private_body':'SECRET','observed_expectations':'buy'},
        'valuation_scenario':{'private_body':'SECRET','not_priced_in':True},
        'evidence_refs':[{'private_body':'SECRET'}], 'limitations':[{'private_body':'SECRET'}]}
    y=compose(x);assert 'SECRET' not in str(y)
    assert profile(y)['axes']['recognition']['price_response']['state']=='missing_owner'

def test_strict_output_validator_refuses_tampering_even_with_recomputed_hash():
    from engine.government_revenue.defense_economics import validate_defense_economics_payload,defense_economics_content_id
    y=compose(fixture());assert validate_defense_economics_payload(y)
    y['profiles'][0]['authority']['can_rank']=True
    y['content_id']=defense_economics_content_id(y)
    with pytest.raises(ValueError): validate_defense_economics_payload(y)


def test_unrelated_nested_operand_and_raw_output_fields_refuse():
    x=fixture();f=x['NOC']['axes']['economics']['facts'][0];f['derived']=True
    operand={'value':2093,'period':'2026Q2','unit':'USD_million','accounting_basis':'issuer_reported_segment','owner_ref':'company'}
    f['numerator']=deepcopy(operand);f['denominator']=deepcopy(operand);f['denominator']['owner_ref']='foreign'
    bindings=deepcopy(BINDINGS);bindings['foreign']={**bindings['company'],'issuer_id':'ISS:US-XNYS-LMT'}
    y=compose_defense_economics(x,generated_at=NOW,source_bindings=bindings)
    assert profile(y)['axes']['economics']['facts']==[]
    from engine.government_revenue.defense_economics import validate_defense_economics_payload,defense_economics_content_id
    y=compose(fixture());profile(y)['axes']['economics']['private_body']='SECRET'
    y['content_id']=defense_economics_content_id(y)
    with pytest.raises(ValueError):validate_defense_economics_payload(y)


def test_canonical_json_sorting_keeps_read_model_valid_and_identity_stable():
    import json
    from engine.government_revenue.defense_economics import validate_defense_economics_payload
    y=compose(fixture());stored=json.loads(json.dumps(y,sort_keys=True))
    assert validate_defense_economics_payload(stored)
    assert stored['content_id']==y['content_id']


def test_rehashed_unsupported_economics_and_completion_are_refused():
    from engine.government_revenue.defense_economics import validate_defense_economics_payload,defense_economics_content_id
    for mutate in ('empty_facts','missing_observation','false_completion','wrong_identity'):
        y=compose(fixture());row=profile(y)
        if mutate=='empty_facts':row['axes']['economics']['facts']=[]
        elif mutate=='missing_observation':row['axes']['economics']['observed_at']=None
        elif mutate=='false_completion':row['research_state']='SOURCE_CONTEXT_COMPLETE'
        else:y['source_bindings']['identity']['issuer_id']='ISS:US-XNYS-LMT'
        y['content_id']=defense_economics_content_id(y)
        with pytest.raises(ValueError):validate_defense_economics_payload(y)

def test_wrong_identity_binding_cannot_qualify_input_identity():
    bindings=deepcopy(BINDINGS);bindings['identity']['issuer_id']='ISS:US-XNYS-LMT'
    y=compose_defense_economics(fixture(),generated_at=NOW,source_bindings=bindings)
    assert profile(y)['issuer_id'] is None

def test_invalid_recognition_horizon_and_vintage_remain_unqualified():
    bindings=deepcopy(BINDINGS);bindings['market'].update(owner_family='market',issuer_id='ISS:US-XNYS-NOC',security_id='SEC:US-XNYS-NOC')
    for change in ({'window_sessions':0},{'window_sessions':2.5},{'price_vintage':'not-a-clock'}):
        x=fixture();x['NOC']['axes']['recognition']={**x['NOC']['axes']['economics'],'owner_ref':'market','facts':[],
            'price_response':{'state':'supported','owner_ref':'market','observed_at':'2026-10-08T20:00:00Z','security_id':'SEC:US-XNYS-NOC','price_adjustment':'split_and_dividend_adjusted','price_vintage':'2026-10-12T23:00:00Z','window_sessions':20,'return_pct':-6.64,**change}}
        y=compose_defense_economics(x,generated_at=NOW,source_bindings=bindings)
        assert profile(y)['axes']['recognition']['price_response']['state']=='missing_owner'


@pytest.mark.parametrize("fault", [None, "missing", "mismatch", "rehash_unsupported", "nonfinite"])
def test_entitled_http_returns_only_the_exact_verified_committed_view(tmp_path, monkeypatch, fault):
    import json
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app import government_revenue as api
    from engine.government_revenue.defense_economics import defense_economics_content_id
    payload = compose(fixture())
    canonical, twin = tmp_path / "canonical.json", tmp_path / "site.json"
    if fault == "rehash_unsupported":
        profile(payload)["axes"]["economics"]["facts"] = []
        payload["content_id"] = defense_economics_content_id(payload)
    elif fault == "nonfinite":
        profile(payload)["axes"]["economics"]["facts"][0]["value"] = float("nan")
    raw = json.dumps(payload, sort_keys=True).encode()
    canonical.write_bytes(raw)
    twin.write_bytes(raw)
    if fault == "missing": canonical.unlink()
    if fault == "mismatch": twin.write_text("{}")
    monkeypatch.setattr(api, "_DEFENSE_ECONOMICS_PATHS", (canonical, twin))
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"site_full": True}
    response = TestClient(app).get("/api/government-revenue/defense-economics")
    assert response.status_code == (200 if fault is None else 503)
    if fault is None: assert response.json() == payload


@pytest.mark.parametrize("denied", [401, 403])
def test_economics_access_is_checked_before_any_evidence_file_read(monkeypatch, denied):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app import government_revenue as api
    class ForbiddenRead:
        def read_bytes(self):
            raise AssertionError("access denial must precede source access")
    monkeypatch.setattr(api, "_DEFENSE_ECONOMICS_PATHS", (ForbiddenRead(), ForbiddenRead()))
    app = FastAPI()
    app.include_router(api.router)
    def reject(): raise HTTPException(status_code=denied, detail="access denied")
    app.dependency_overrides[api.require_site_full_user] = reject
    assert TestClient(app).get("/api/government-revenue/defense-economics").status_code == denied


def test_site_projection_mirrors_canonical_without_recomputing_or_promoting(tmp_path):
    from scripts import build_government_revenue as builder
    canonical = tmp_path / "data/government_revenue/defense_economics.json"
    twin = tmp_path / "site/government-revenue-data/defense-economics.json"
    payload = compose(fixture())
    raw = builder._canonical_json(payload)
    canonical.parent.mkdir(parents=True)
    canonical.write_text(raw)
    builder._project_committed_defense_economics(tmp_path)
    assert canonical.read_bytes() == twin.read_bytes() == raw.encode()
    before = twin.read_bytes()
    canonical.write_text("{}")
    with pytest.raises(ValueError): builder._project_committed_defense_economics(tmp_path)
    assert twin.read_bytes() == before
    canonical.unlink()
    with pytest.raises(ValueError, match="no canonical source"):
        builder._project_committed_defense_economics(tmp_path)
