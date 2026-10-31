"""Real private router with synthetic identity and native test-owner state.

No production endpoint, credential, private source or publication is accessed.
"""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import json

import pytest
from fastapi.testclient import TestClient

from app import company_disclosures as api
from engine.theme_graph import economic_context
from engine.theme_graph import issuer_economic_context as consumer
from tests.test_company_issuer_disclosures import sample
from tests.test_company_disclosure_owner import case
from tests.test_company_disclosures_api import boundary, selection_boundary, private_headers


@pytest.fixture
def route(selection_boundary):
    native_boundary, owner, url = selection_boundary
    authority = native_boundary[4]
    authority.admission = replace(authority.admission, allowed_fields=economic_context.REQUIRED_FIELDS)
    return native_boundary, owner, url.replace("/product-integrations", "/economic-context")


def get(value, suffix="", headers=None):
    b, _, url = value
    return b[0].get(url+suffix, headers={"Authorization":"Bearer synthetic-token"} if headers is None else headers)


def refusal(response, status, code):
    assert response.status_code == status, response.text
    private_headers(response)
    assert response.json() == {"schema":api.ERROR_SCHEMA, "code":code, "automatic_retry_permitted":False}


def test_main_mount_rejects_unauthenticated_before_entitlement_or_owner(route):
    b, owner, url = route
    response = TestClient(b[-1].app).get(url)
    refusal(response,401,"AUTHENTICATION_REQUIRED")
    assert b[3] == [] and b[4].calls == owner.calls == 0


def test_authenticated_route_returns_exact_native_human_machine_payload(route):
    b, owner, _ = route
    before={p:p.read_bytes() for p in b[5].root.rglob("*") if p.is_file()}
    response=get(route)
    assert response.status_code==200, response.text
    private_headers(response)
    assert b[3]==["authenticate","entitlement","private_store","authenticate","entitlement"]
    result=response.json()
    expected=consumer.read_issuer_economic_context(owner,b[4],lambda:b[5],owner.value.issuer_id,
        purpose=api.PURPOSE,audience=api.AUDIENCE)
    assert result==expected
    assert result["authority"]=="context_only" and result["context"]["usage"]=={
        "purpose":api.PURPOSE,"audience":api.AUDIENCE}
    row=result["context"]["relationships"][0]
    assert row["relationship"]["lifecycle"]=="planned"
    assert row["relationship"]["amount"] is None and row["relationship"]["economic_share"] is None
    assert row["mapping"]["legacy_theme_graph_edge"] is None
    assert not any(row["limitations"].values())
    assert before=={p:p.read_bytes() for p in b[5].root.rglob("*") if p.is_file()}
    assert all(s not in response.text for s in ["synthetic-token","text_sha256","review_revision","source.html"])


def test_cookie_and_bearer_use_same_identity_and_payload(route,monkeypatch):
    b,_,_=route
    bearer=get(route)
    seen=[]
    def cookie(request):
        seen.append(request.cookies.get("synthetic-session"))
        return "synthetic-token" if seen[-1]=="present" else None
    monkeypatch.setattr(b[-1],"_mm_supabase_access_token",cookie)
    other=get(route,headers={"Cookie":"synthetic-session=present"})
    assert bearer.status_code==other.status_code==200
    assert bearer.json()==other.json()
    assert seen==["present","present"]


@pytest.mark.parametrize("change",[
    {"features":[]},{"features":["site_full"]},{"features":api.FEATURE},
    {"features":[api.FEATURE,1]},{"tier":"free"},{"status":"canceled"},
    {"status":"past_due"},{"tier":None},{"status":None},
])
def test_actual_feature_grant_precedes_selection_and_private_io(route,change):
    b,owner,_=route;b[2].update(change)
    refusal(get(route),403,"ENTITLEMENT_REQUIRED")
    assert b[3]==["authenticate","entitlement"] and b[4].calls==owner.calls==0


@pytest.mark.parametrize("query",[
    "?purpose=public","?audience=any","?ticker=TEST","?cik=0000000001",
    "?generation=old","?mode=historical","?as_of=2020-01-01","?fact_id=other",
    "?Admission={}","?root=/private","?mode=current&mode=current",
])
def test_queries_are_not_permission_or_identity_controls(route,query):
    b,owner,_=route
    refusal(get(route,query),400,"REQUEST_INVALID")
    assert b[3]==["authenticate","entitlement"] and owner.calls==b[4].calls==0


@pytest.mark.parametrize("issuer",["MU","cik:0000000001","%20ISS:US-XNAS-TEST","unknown"])
def test_issuer_route_does_not_allocate_ticker_or_cik_identity(route,issuer):
    b,owner,url=route
    response=b[0].get(url.replace(owner.value.issuer_id,issuer),headers={"Authorization":"Bearer synthetic-token"})
    refusal(response,400,"REQUEST_INVALID")
    assert owner.calls==b[4].calls==0 and "private_store" not in b[3]


def test_qualified_empty_selection_is_available_but_not_global_absence(route):
    b,owner,_=route;owner.value=replace(owner.value,selections=())
    response=get(route)
    assert response.status_code==200
    assert response.json()["context"]["relationships"]==[]
    assert response.json()["context"]["coverage"]["global_relationship_coverage_established"] is False
    assert b[4].calls==0 and "private_store" not in b[3]
    assert b[3]==["authenticate","entitlement","authenticate","entitlement"]


def test_missing_selection_is_not_empty_or_previous_positive(route):
    b,owner,_=route
    assert get(route).status_code==200
    b[3].clear();owner.value=None
    refusal(get(route),503,"PRIVATE_SOURCE_UNAVAILABLE")
    assert "private_store" not in b[3]


def test_runtime_missing_is_not_public_fallback(route):
    b,owner,_=route;del b[0].app.state.company_disclosure_reader
    refusal(get(route),503,"SOURCE_RUNTIME_UNAVAILABLE")
    assert owner.calls==b[4].calls==0


def test_missing_selection_capability_does_not_allocate_an_owner(route):
    b,_,_=route;old=b[0].app.state.company_disclosure_reader
    b[0].app.state.company_disclosure_reader=replace(old,selection_owner=None)
    refusal(get(route),503,"SOURCE_RUNTIME_UNAVAILABLE")
    assert b[4].calls==0


def test_field_grant_refusal_precedes_store_construction(route):
    b,_,_=route;b[4].admission=replace(b[4].admission,
        allowed_fields=b[4].admission.allowed_fields-{"product"})
    refusal(get(route),503,"PRIVATE_SOURCE_UNAVAILABLE")
    assert "private_store" not in b[3]


def test_native_subject_identity_refusal_is_not_exposed(route):
    b,owner,_=route;owner.value=replace(owner.value,evidenced_cik="0000000099")
    refusal(get(route),503,"PRIVATE_SOURCE_UNAVAILABLE")
    assert "private_store" not in b[3]


def test_late_selection_change_withholds_all_facts(route):
    _,owner,_=route;owner.change_at=2
    refusal(get(route),503,"PRIVATE_SOURCE_UNAVAILABLE")


def test_late_native_admission_change_withholds_all_facts(route):
    b,_,_=route;b[4].change_at=4
    refusal(get(route),503,"PRIVATE_SOURCE_UNAVAILABLE")


def test_entitlement_revoked_during_fact_read_never_serializes(route,monkeypatch):
    b,_,_=route;old=b[5].get_bytes_strict_bounded
    def revoke(*args,**kwargs):
        b[2]["features"]=[]
        return old(*args,**kwargs)
    monkeypatch.setattr(b[5],"get_bytes_strict_bounded",revoke)
    refusal(get(route),403,"ENTITLEMENT_REQUIRED")
    assert b[3][-2:]==["authenticate","entitlement"]


def test_principal_change_during_read_refuses_serialization(route,monkeypatch):
    from app import paywall
    b,_,_=route;calls=[]
    def who(token):
        calls.append(token)
        uid="synthetic-user" if len(calls)==1 else "different-user"
        return SimpleNamespace(status="ok",uid=uid,record={"id":uid})
    from app import billing
    monkeypatch.setattr(paywall,"_resolve_identity",who)
    monkeypatch.setattr(billing,"read_entitlement",lambda uid: b[2])
    refusal(get(route),401,"AUTHENTICATION_REQUIRED")
    assert len(calls)==2


def test_reader_exception_is_private_and_never_retried(route,monkeypatch):
    calls=[]
    def broken(*args,**kwargs):
        calls.append(1);raise OSError("sensitive store path /private/source")
    monkeypatch.setattr(consumer,"read_issuer_economic_context",broken)
    refusal(get(route),503,"PRIVATE_SERVICE_UNAVAILABLE")
    assert calls==[1]


@pytest.mark.parametrize("bad",[
    {"schema":consumer.SCHEMA,"status":"unavailable","reason":"secret","context":{"fact":"private"},"authority":"context_only"},
    {"schema":"old","status":"available","reason":None,"context":{},"authority":"context_only"},
    {"schema":consumer.SCHEMA,"status":"available","reason":None,"context":{},"authority":"ranking"},
    {"schema":consumer.SCHEMA,"status":"available","reason":None,"context":None,"authority":"context_only"},
    None,
])
def test_unavailable_or_wrong_contract_never_returns_partial_context(route,monkeypatch,bad):
    monkeypatch.setattr(consumer,"read_issuer_economic_context",lambda *a,**k:bad)
    refusal(get(route),503,"PRIVATE_SOURCE_UNAVAILABLE")


def test_real_current_owner_and_read_only_local_artifacts_via_http(boundary,case):
    from engine.company_intelligence import issuer_disclosure_owner as owner
    from tests.test_company_disclosure_owner import publish
    published=publish(case)
    source,state,artifacts,*_=case
    current=owner.CurrentDisclosureOwner(source,owner.ReadOnlyLocalObjects(state.root))
    opened=[]
    def factory():
        opened.append(1);return owner.ReadOnlyLocalObjects(artifacts.root)
    boundary[0].app.state.company_disclosure_reader=api.PrivateDisclosureReader(current,factory,current)
    issuer=source.value.spec["fact"]["subject_id"]
    url="/api/company-intelligence/private/issuers/"+issuer+"/economic-context"
    before={p:p.read_bytes() for root in (state.root,artifacts.root) for p in root.rglob("*") if p.is_file()}
    response=boundary[0].get(url,headers={"Authorization":"Bearer synthetic-token"})
    assert response.status_code==200,response.text
    private_headers(response)
    assert response.json()["context"]["generation"]==published["generation"]
    assert response.json()["context"]["relationships"][0]["provenance"]["reference"]==source.value.spec["correction_decision"]["fact"]
    assert before=={p:p.read_bytes() for root in (state.root,artifacts.root) for p in root.rglob("*") if p.is_file()}
    count=len(opened);source.value=replace(source.value,ruling_revision="0"*64)
    refusal(boundary[0].get(url,headers={"Authorization":"Bearer synthetic-token"}),503,"PRIVATE_SOURCE_UNAVAILABLE")
    assert len(opened)==count
