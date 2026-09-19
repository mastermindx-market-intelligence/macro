"""Native D5 producer -> owner validator -> research view, no provider calls."""
from copy import deepcopy
import importlib
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from tests.test_prophet_lab import _build_d5, _d5_master, _d5_workspace, _d5_revisions
from tests.test_prophet_lab_api import _d5_snapshot, _d5_master as _api_master, _D5_EPISODE_ID
from engine.prophet_lab.intelligence_vector import IntelligenceVectorContractError
import app.prophet_lab as api

def view_module():
    return importlib.import_module("engine.prophet_lab.earnings_view")

def test_native_owner_payload_reaches_readable_view_without_mutation():
    payload = _build_d5()
    original = deepcopy(payload)
    view = view_module().build_earnings_view(payload)
    assert view["source_projection_id"] == payload["projection_id"]
    assert view["episode_ref"] == payload["episode_ref"]
    assert view["decision_cut"] == payload["decision_cut"]
    assert view["metrics"][0]["value"] == 109_417_000_000
    assert view["metrics"][1]["value"] == {"low": 9.0, "high": 11.0}
    assert payload == original
    assert view["authority"] == payload["authority"]
    assert not any(view["authority"].values())
    assert "available" in view["summary"].lower()
    assert "unresolved" not in view["summary"].lower()

def test_event_context_is_not_forward_consensus_or_entry_or_hold():
    view = view_module().build_earnings_view(_build_d5())
    assert view["expectation_revision"]["state"] == "NOT_CONNECTED"
    assert view["expectation_revision"]["horizon_sessions"] == 21
    assert view["availability"]["state"] == "NOT_ASSERTED"
    assert view["hold"]["state"] == "NOT_SUPPLIED"
    assert view["freshness"]["state"] == "UNKNOWN"
    assert view["comparison"]["consensus"]["state"] == "ABSENT"
    assert view["comparison"]["consensus"]["reason"] == "consensus_unlicensed"

def test_native_identity_unresolved_remains_visible_and_nonnumeric():
    payload = _build_d5(issuer_master=_d5_master(include_cik=False))
    view = view_module().build_earnings_view(payload)
    assert view["metrics"] == []
    assert view["identity_state"] == payload["evidence_families"][0]["identity_state"]
    assert view["coverage"]["state"] == "UNKNOWN"
    assert "identity" in view["summary"].lower()

def test_no_owner_event_is_not_a_zero_revision():
    view = view_module().build_earnings_view(_build_d5(find_event_id=lambda _: None))
    assert view["coverage"]["state"] == "NOT_COVERED"
    assert view["metrics"] == []
    assert view["expectation_revision"]["state"] == "NOT_CONNECTED"

def corrected_payload():
    old = _d5_workspace()
    new = deepcopy(old)
    new["generation_id"] = "2" * 24
    new["generated_at"] = "2026-07-31T12:03:00Z"
    new["lifecycle"]["source_available_at"] = "2026-07-31T12:00:00Z"
    new["lifecycle"]["observed_at"] = "2026-07-31T12:02:00Z"
    new["sources"][0]["source_sha256"] = "e" * 64
    new["facts"][0]["value"] = 108_000_000_000
    new["deltas"][0]["current"]["value"] = 108_000_000_000
    return _build_d5(read_revisions=lambda _: _d5_revisions(workspace=old) + _d5_revisions(workspace=new))

def test_later_correction_flags_without_replacing_decision_time_number():
    payload = corrected_payload()
    view = view_module().build_earnings_view(payload)
    assert view["metrics"][0]["value"] == 109_417_000_000
    assert view["correction"]["current_state"] == "CORRECTED"
    assert view["correction"]["later_correction_ref_ids"]
    assert "later" in view["summary"].lower()
    assert view["source_refs"] == payload["evidence_families"][0]["source_refs"]

@pytest.mark.parametrize("mutation", ["rank", "wrong_hash", "private_body", "identity", "future", "rights"])
def test_native_validator_remains_required(mutation):
    payload = _build_d5()
    if mutation == "rank": payload["authority"]["can_rank"] = True
    if mutation == "wrong_hash": payload["projection_id"] = "piv:" + "0" * 64
    if mutation == "private_body": payload["evidence_families"][0]["body"] = "PRIVATE RAW CONTENT"
    if mutation == "identity": payload["episode_ref"]["identity_ref"] = "ISS:US:999999"
    if mutation == "future": payload["decision_cut"]["opened_at"] = "2026-01-01T00:00:00Z"
    if mutation == "rights": payload["evidence_families"][0]["rights"]["state"] = "BLOCKED"
    with pytest.raises(IntelligenceVectorContractError):
        view_module().build_earnings_view(payload)

@pytest.mark.parametrize("language", ["en", "zh"])
def test_renderer_has_disclosures_and_no_scripts_or_raw_source(language):
    html = view_module().render_earnings_fragment(corrected_payload(), language=language)
    assert "109,417,000,000" in html
    assert "108,000,000,000" not in html
    assert "RAW FACT" not in html and "private.example" not in html
    assert "<script" not in html and "onclick=" not in html
    assert "<details" in html and 'lang="' + language + '"' in html
    assert "9" in html and "11" in html
    assert ("Later correction" in html) if language == "en" else ("后续更正" in html)

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("PROPHET_LAB_DISABLED", raising=False)
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: _d5_snapshot())
    monkeypatch.setattr(api, "_load_issuer_master", lambda _: _api_master(include_cik=False))
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        yield c, app

def url(): return f"/api/prophet/lab/v1/episodes/{_D5_EPISODE_ID}/research-view"

def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"

def test_native_http_json_and_html_share_same_evidence(client):
    c, _ = client
    original = c.get(url().replace("research-view", "intelligence"))
    response = c.get(url())
    assert response.status_code == 200
    private(response)
    assert response.json()["source_projection_id"] == original.json()["projection_id"]
    html = c.get(url(), params={"format": "html", "language": "zh"})
    assert html.status_code == 200
    private(html)
    assert "text/html" in html.headers["content-type"]
    assert "script-src 'none'" in html.headers["content-security-policy"]

@pytest.mark.parametrize("code", [401, 403])
def test_same_auth_gate_denies_before_data_read(client, monkeypatch, code):
    c, app = client
    def denied(): raise HTTPException(code, "denied", headers=api._PRIVATE_HEADERS)
    app.dependency_overrides[api.require_site_full_user] = denied
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: pytest.fail("read before auth"))
    response = c.get(url())
    assert response.status_code == code
    private(response)

def test_kill_switch_and_missing_episode_preserve_original_errors(client, monkeypatch):
    c, _ = client
    missing = c.get(url().replace(_D5_EPISODE_ID, "unknown"))
    assert missing.status_code == 404
    private(missing)
    monkeypatch.setenv("PROPHET_LAB_DISABLED", "true")
    disabled = c.get(url())
    assert disabled.status_code == 503
    private(disabled)

def test_source_failure_does_not_become_empty_success(client, monkeypatch):
    c, _ = client
    def broken(_): raise RuntimeError("private-path secret should not escape")
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", broken)
    response = c.get(url(), params={"format": "html"})
    assert response.status_code == 503
    private(response)
    assert "private-path" not in response.text


@pytest.mark.parametrize("params", [{"format":"xml"},{"language":"fr"},{"format":"HTML"}])
def test_invalid_view_options_do_not_read_the_source(client, monkeypatch, params):
    c, _ = client
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: pytest.fail("invalid option read source"))
    response=c.get(url(),params=params)
    assert response.status_code == 400
    private(response)

@pytest.mark.parametrize("code", [401,403])
def test_native_auth_dependency_preserved_not_a_parallel_authenticator(monkeypatch,code):
    import app.main as main
    import app.paywall as paywall
    calls=[]
    def auth(value):
        calls.append(("auth",value))
        if code == 401: raise HTTPException(401,"sign in")
        return {"id":"test-free"}
    def entitle(user,always=False):
        calls.append(("entitlement",always))
        raise HTTPException(403,"site_full required")
    monkeypatch.setattr(main,"require_user",auth)
    monkeypatch.setattr(paywall,"enforce_site_full",entitle)
    monkeypatch.setattr(api,"load_candidate_episode_store_snapshot",lambda _: pytest.fail("unauthorized source read"))
    app=FastAPI();app.include_router(api.router)
    with TestClient(app) as c:
        response=c.get(url())
    assert response.status_code == code
    private(response)
    assert calls[0]==("auth",None)
    if code == 403: assert calls[1]==("entitlement",True)

def test_html_csp_matches_the_actual_inline_style(client):
    import hashlib,base64,re
    c,_=client
    response=c.get(url(),params={"format":"html"})
    style=re.search(r"<style>(.*?)</style>",response.text,re.S).group(1)
    expected=base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    assert "'sha256-"+expected+"'" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert "frame-ancestors 'self'" in response.headers["content-security-policy"]

def test_projection_integrity_failure_is_not_rendered(client,monkeypatch):
    from fastapi.responses import JSONResponse
    c,_=client
    bad=_build_d5();bad["authority"]["can_rank"]=True
    monkeypatch.setattr(api,"episode_intelligence_v1",lambda *a,**kw: JSONResponse(bad))
    response=c.get(url(),params={"format":"html"})
    assert response.status_code == 503
    assert "109417" not in response.text
    private(response)

def test_event_does_not_claim_unexposed_fiscal_or_guidance_horizon():
    text=view_module().render_earnings_fragment(_build_d5())
    assert "fiscal period is not exposed" in text
    assert "horizon is not exposed" in text
    assert "FY2026 Q4" not in text
    assert "Earnings beat" not in text
    assert "not the +1y EPS/revenue revision species" in text

def test_no_owner_facts_preserves_typed_absence():
    workspace=_d5_workspace();workspace["facts"]=[];workspace["guidance"]=[];workspace["deltas"]=[]
    payload=_build_d5(read_revisions=lambda _: _d5_revisions(workspace=workspace))
    v=view_module().build_earnings_view(payload)
    assert v["metrics"]==[]
    assert v["comparison"] is None
    assert "No source-backed numeric evidence" in view_module().render_earnings_fragment(payload)

def test_original_source_is_requested_exactly_once(client,monkeypatch):
    c,_=client;calls=[]
    original=api.episode_intelligence_v1
    def wrapped(*args,**kwargs):
        calls.append(args[0]);return original(*args,**kwargs)
    monkeypatch.setattr(api,"episode_intelligence_v1",wrapped)
    assert c.get(url()).status_code==200
    assert len(calls)==1

def test_invalid_language_refuses_before_any_presentation():
    with pytest.raises(ValueError):view_module().build_earnings_view(_build_d5(),language="fr")


@pytest.mark.parametrize("language", ["en","zh"])
@pytest.mark.parametrize("fmt", ["json","html"])
def test_real_native_producer_through_http_covered_and_corrected(client,monkeypatch,language,fmt):
    from engine.prophet_lab.intelligence_vector import build_earnings_intelligence_vector
    c,_=client
    old=_d5_workspace();later=deepcopy(old)
    later["generation_id"]="2"*24
    later["generated_at"]="2026-07-31T12:03:00Z"
    later["lifecycle"]["source_available_at"]="2026-07-31T12:00:00Z"
    later["lifecycle"]["observed_at"]="2026-07-31T12:02:00Z"
    later["sources"][0]["source_sha256"]="e"*64
    later["facts"][0]["value"]=108_000_000_000
    later["deltas"][0]["current"]["value"]=108_000_000_000
    def native_build(**kwargs):
        return build_earnings_intelligence_vector(**kwargs,
            find_event_id=lambda _:old["event_id"],
            read_revisions=lambda _:_d5_revisions(workspace=old)+_d5_revisions(workspace=later))
    monkeypatch.setattr(api,"_load_issuer_master",lambda _:_api_master(include_cik=True))
    monkeypatch.setattr(api,"build_earnings_intelligence_vector",native_build)
    response=c.get(url(),params={"language":language,"format":fmt})
    assert response.status_code==200
    private(response)
    if fmt=="json":
        assert response.json()["metrics"][0]["value"]==109_417_000_000
        assert response.json()["correction"]["current_state"]=="CORRECTED"
    else:
        assert "109,417,000,000" in response.text
        assert "108,000,000,000" not in response.text

def test_complete_native_source_validator_is_used_for_readdressed_poison():
    from tests.test_prophet_lab import _readdress_d5
    payload=_build_d5();payload["authority"]["can_gate"]=True
    _readdress_d5(payload)
    with pytest.raises(IntelligenceVectorContractError):
        view_module().build_earnings_view(payload)


def test_frozen_spacing_fallbacks_cover_unlanded_shared_scale_tokens():
    style=view_module().STYLE
    for name,value in {"--r-ctl":"8px","--r-card":"12px","--sp-1":"4px","--sp-2":"8px","--sp-3":"12px","--sp-4":"16px","--sp-5":"20px","--sp-6":"24px"}.items():
        assert "var("+name+")" not in style
        assert "var("+name+","+value+")" in style
    assert ":root" not in style


def test_native_earnings_view_exists():
    assert callable(view_module().build_earnings_view)

def test_existing_private_router_exposes_research_view():
    assert any(route.path.endswith("/research-view") for route in api.router.routes)


# Exact episode discovery uses the existing B1 snapshot, never a ticker join.
def test_episode_directory_links_native_view_at_exact_generation(client, monkeypatch):
    c, _ = client
    calls = []
    def load(_root):
        calls.append("b1")
        return _d5_snapshot()
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", load)
    response = c.get("/api/prophet/lab/v1/episodes")
    assert response.status_code == 200
    private(response)
    data = response.json()
    assert calls == ["b1"]
    assert data["population_completeness"] == "NOT_ASSERTED"
    assert data["selection"]["total_episodes"] == 1
    assert not any(data["authority"].values())
    row = data["episodes"][0]
    assert row["episode_ref"]["episode_id"] == _D5_EPISODE_ID
    assert row["episode_ref"]["generation_id"] == data["generation_id"]
    detail = c.get(row["research_view_url"])
    assert detail.status_code == 200
    assert detail.json()["episode_ref"] == row["episode_ref"]


def test_episode_directory_never_reads_earnings_or_filters_by_coverage(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", lambda **kw: pytest.fail("directory read earnings"))
    response = c.get("/api/prophet/lab/v1/episodes", params={"q": "aapl"})
    assert response.status_code == 200
    assert len(response.json()["episodes"]) == 1


@pytest.mark.parametrize("params", [
    {"limit": "0"}, {"limit": "101"}, {"limit": "true"}, {"limit": "1.0"},
    {"offset": "-1"}, {"offset": "1000001"}, {"offset": "1"},
    {"q": "x" * 81}, {"q": "AAPL\n"}, {"expected_generation": "bad"},
])
def test_episode_directory_invalid_options_are_private_before_read(client, monkeypatch, params):
    c, _ = client
    reads = []
    def load(_):
        reads.append("B1")
        return _d5_snapshot()
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", load)
    response = c.get("/api/prophet/lab/v1/episodes", params=params)
    assert response.status_code == 400
    private(response)
    assert reads == []


@pytest.mark.parametrize("code", [401, 403])
def test_episode_directory_auth_denies_before_b1(client, monkeypatch, code):
    c, app = client
    def denied():
        raise HTTPException(code, "denied", headers=api._PRIVATE_HEADERS)
    app.dependency_overrides[api.require_site_full_user] = denied
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: pytest.fail("auth failure read B1"))
    response = c.get("/api/prophet/lab/v1/episodes")
    assert response.status_code == code
    private(response)


def test_episode_directory_kill_switch_denies_before_b1(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv("PROPHET_LAB_DISABLED", "1")
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: pytest.fail("disabled read B1"))
    response = c.get("/api/prophet/lab/v1/episodes")
    assert response.status_code == 503
    private(response)


def test_episode_directory_corrupt_source_is_not_empty_success(client, monkeypatch):
    c, _ = client
    def broken(_):
        raise ValueError("PRIVATE PATH MUST NOT LEAK")
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", broken)
    response = c.get("/api/prophet/lab/v1/episodes")
    assert response.status_code == 503
    private(response)
    assert "PRIVATE" not in response.text


def test_episode_directory_empty_and_unmatched_are_honest(client, monkeypatch):
    c, _ = client
    unmatched = c.get("/api/prophet/lab/v1/episodes", params={"q": "does-not-exist"})
    assert unmatched.status_code == 200
    assert unmatched.json()["selection"]["total_matches"] == 0
    assert unmatched.json()["selection"]["total_episodes"] == 1
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: _d5_snapshot(episodes=()))
    response = c.get("/api/prophet/lab/v1/episodes")
    assert response.status_code == 200
    assert response.json()["episodes"] == []
    assert response.json()["selection"]["next_offset"] is None


def test_episode_directory_keeps_distinct_same_security_episodes(client, monkeypatch):
    c, _ = client
    first = deepcopy(_d5_snapshot().generation.episodes[0])
    second = deepcopy(first)
    second["identity_epoch"] = "epoch_1"
    second["episode_id"] = second["episode_id"].replace(":epoch_0:", ":epoch_1:")
    second["episode_state"] = "EXPIRED"
    original = deepcopy((first, second))
    snapshot = _d5_snapshot(episodes=(first, second))
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: snapshot)
    one = c.get("/api/prophet/lab/v1/episodes", params={"q": "AAPL", "limit": "1"}).json()
    assert one["selection"]["total_matches"] == 2
    assert one["selection"]["next_offset"] == 1
    two_response = c.get("/api/prophet/lab/v1/episodes", params={"q": "AAPL", "limit": "1", "offset": "1", "expected_generation": one["generation_id"]})
    assert two_response.status_code == 200
    two = two_response.json()
    assert one["episodes"][0]["episode_ref"] != two["episodes"][0]["episode_ref"]
    assert two["selection"]["next_offset"] is None
    assert snapshot.generation.episodes == original
    assert "EXPIRED" in {one["episodes"][0]["episode_state"], two["episodes"][0]["episode_state"]}


@pytest.mark.parametrize("route", ["directory", "view"])
def test_episode_generation_pin_refuses_changed_evidence(client, route):
    c, _ = client
    path = "/api/prophet/lab/v1/episodes" if route == "directory" else url()
    response = c.get(path, params={"expected_generation": "peg:" + "b" * 64})
    assert response.status_code == 409
    private(response)
    assert response.json()["error"] == "prophet_episode_generation_changed"
    assert "episodes" not in response.json()
    assert "metrics" not in response.json()


def test_episode_view_invalid_generation_pin_refuses_before_read(client, monkeypatch):
    c, _ = client
    reads = []
    def load(_):
        reads.append("B1")
        return _d5_snapshot()
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", load)
    response = c.get(url(), params={"expected_generation": "../foreign"})
    assert response.status_code == 400
    private(response)
    assert reads == []


def test_native_presentation_is_shared_without_changing_source_facts():
    payload=_build_d5(); before=deepcopy(payload)
    view=view_module().build_earnings_view(payload)
    assert view['metrics'][0]['display_value']=='$109,417,000,000'
    assert view['metrics'][1]['display_value']=='9 – 11%'
    assert view['presentation']['title']=='Earnings evidence'
    assert 'Not connected' in view['presentation']['separate'][0]['note']
    assert payload==before and not any(view['authority'].values())

@pytest.mark.parametrize('language',['en','zh'])
def test_shared_presentation_keeps_decision_time_values_after_correction(language):
    payload=corrected_payload();view=view_module().build_earnings_view(payload,language=language)
    assert view['metrics'][0]['display_value']=='$109,417,000,000'
    assert view['presentation']['correction_note'] in view_module().render_earnings_fragment(payload,language=language)
    assert view['presentation']['comparisons'][1]['note']

@pytest.mark.parametrize('language',['en','zh'])
def test_withdrawn_guidance_is_not_presented_as_current_growth_range(language):
    workspace=_d5_workspace();workspace['guidance'][0]['status']='withdrawn'
    payload=_build_d5(read_revisions=lambda _: _d5_revisions(workspace=workspace))
    view=view_module().build_earnings_view(payload,language=language)
    metric=next(m for m in view['metrics'] if m['native_metric_id']=='guidance:revenue_yoy_pct')
    assert metric['value']=={'low':9.0,'high':11.0}
    assert metric['display_value']==('Guidance withdrawn' if language=='en' else '指引已撤回')
    html=view_module().render_earnings_fragment(payload,language=language)
    assert '9 – 11%' not in html


@pytest.mark.parametrize('status',['introduced','reiterated','raised','cut'])
@pytest.mark.parametrize('language',['en','zh'])
def test_nonwithdrawn_guidance_keeps_original_numeric_display(status,language):
    workspace=_d5_workspace();workspace['guidance'][0]['status']=status
    payload=_build_d5(read_revisions=lambda _: _d5_revisions(workspace=workspace))
    before=deepcopy(payload);view=view_module().build_earnings_view(payload,language=language)
    metric=next(m for m in view['metrics'] if m['native_metric_id']=='guidance:revenue_yoy_pct')
    assert metric['display_value']=='9 – 11%'
    assert metric['value']=={'low':9.0,'high':11.0}
    assert metric['guidance_status_label']
    assert payload==before and not any(view['authority'].values())


def test_withdrawn_guidance_keeps_old_bounds_in_receipt_not_headline():
    workspace=_d5_workspace();workspace['guidance'][0]['status']='withdrawn'
    payload=_build_d5(read_revisions=lambda _: _d5_revisions(workspace=workspace))
    before=deepcopy(payload);html=view_module().render_earnings_fragment(payload)
    assert 'Guidance withdrawn' in html
    before_receipt,receipt=html.split('<pre>',1)
    assert '9 – 11%' not in before_receipt
    assert '&quot;low&quot;: 9.0' in receipt and '&quot;high&quot;: 11.0' in receipt
    assert payload==before

@pytest.mark.parametrize('language',['en','zh'])
def test_absent_guidance_never_becomes_an_active_numeric_outlook(language):
    workspace=_d5_workspace();workspace['guidance'][0]['status']='absent'
    payload=_build_d5(read_revisions=lambda _: _d5_revisions(workspace=workspace))
    view=view_module().build_earnings_view(payload,language=language)
    metric=next(m for m in view['metrics'] if m['native_metric_id']=='guidance:revenue_yoy_pct')
    assert metric['display_value']==('Guidance not supplied' if language=='en' else '未提供指引')
    assert metric['value']=={'low':9.0,'high':11.0}
    assert '9 – 11%' not in view_module().render_earnings_fragment(payload,language=language)


def test_stale_research_generation_pin_refuses_before_d5_source_build(client, monkeypatch):
    c, _ = client
    build_calls = []

    def forbidden_build(**kwargs):
        build_calls.append(kwargs)
        raise AssertionError("stale generation entered D5 source build")

    monkeypatch.setattr(api, "build_earnings_intelligence_vector", forbidden_build)
    response = c.get(url(), params={"expected_generation": "peg:" + "b" * 64})
    assert response.status_code == 409
    private(response)
    assert response.json()["error"] == "prophet_episode_generation_changed"
    assert build_calls == []
