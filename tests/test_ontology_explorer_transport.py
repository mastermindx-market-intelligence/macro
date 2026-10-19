"""tests/test_ontology_explorer_transport.py — F04-X1 private transport (RED first).

`/ontology.html` is public and carries no current value. Every current value
reaches the researcher through `GET /api/ontology/explorer/v1` behind the
existing `require_user -> enforce_site_full(always=True)` authority.

The hard part is not the happy path — it is the outcomes where a header is
easiest to forget. A 401 raised inside a dependency never reaches the endpoint
body, so a router that only stamps its headers on success will serve its
rejections cacheable and indexable. These tests therefore assert the private
header set on EVERY outcome: success, 401, 403, typed 503 and 422.

They also pin the two refusals that make the paywall meaningful at all: there is
no static fallback to serve when the source is unavailable, and no error body
ever carries a current owner reading.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="ontology explorer transport tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ontology_explorer_fixtures as fx  # noqa: E402

ROUTE = "/api/ontology/explorer/v1"

REQUIRED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _api():
    from app import ontology_explorer as api
    return api


def _client(monkeypatch, tmp_path, *, entitled: bool = True, authed: bool = True,
            root: Path | None = None, chain: str = fx.SLUG) -> TestClient:
    api = _api()
    root = fx.build_root(tmp_path) if root is None else root
    monkeypatch.setattr(api, "_repo_root", lambda: root)
    monkeypatch.setattr(api, "DEFAULT_CHAIN", chain)
    monkeypatch.setattr(api, "ACCEPTED_CHAINS", frozenset({chain}))
    app = FastAPI()
    app.include_router(api.router)

    def _dep():
        if not authed:
            raise HTTPException(401, "missing bearer token")
        if not entitled:
            raise HTTPException(403, detail={"locked": True, "tier": "essential",
                                             "required_feature": "site_full",
                                             "upgrade_url": "/plans.html?upgrade=1"})
        return {"id": "paid-user"}

    app.dependency_overrides[api.require_site_full_user] = _dep
    return TestClient(app, raise_server_exceptions=False)


def _assert_private(response) -> None:
    for name, value in REQUIRED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == value, (
            f"{name} missing or wrong on a {response.status_code} response")


# --------------------------------------------------------------------------
# the authenticated happy path
# --------------------------------------------------------------------------
def test_entitled_read_returns_the_snapshot_privately(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        response = client.get(ROUTE)
    assert response.status_code == 200
    assert response.json()["schema"] == "ontology_explorer_snapshot.v1"
    _assert_private(response)


def test_the_route_is_registered_under_the_frozen_namespace(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        assert ROUTE in client.app.openapi()["paths"]


# --------------------------------------------------------------------------
# rejection outcomes still carry the private header set
# --------------------------------------------------------------------------
def test_anonymous_read_is_401_and_still_private(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, authed=False) as client:
        response = client.get(ROUTE)
    assert response.status_code == 401
    _assert_private(response)


def test_authenticated_without_site_full_is_403_and_still_private(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, entitled=False) as client:
        response = client.get(ROUTE)
    assert response.status_code == 403
    _assert_private(response)
    assert response.json()["detail"]["required_feature"] == "site_full"


def test_a_missing_source_is_a_typed_503_and_still_private(monkeypatch, tmp_path):
    root = fx.build_root(tmp_path)
    (root / "data" / "transmission" / "chain_state.json").unlink()
    with _client(monkeypatch, tmp_path, root=root) as client:
        response = client.get(ROUTE)
    assert response.status_code == 503
    _assert_private(response)
    detail = response.json()["detail"]
    assert detail["code"] == "source_unavailable"
    assert detail["schema"] == "ontology_explorer_error.v1"


def test_an_incoherent_source_is_a_typed_503_and_still_private(monkeypatch, tmp_path):
    root = fx.build_root(tmp_path, yaml_doc=fx.chain_yaml(rev=3),
                         state_doc=fx.chain_state(rev=2))
    with _client(monkeypatch, tmp_path, root=root) as client:
        response = client.get(ROUTE)
    assert response.status_code == 503
    _assert_private(response)
    assert response.json()["detail"]["code"] == "source_incoherent"


def test_an_unknown_chain_parameter_is_rejected_privately(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        response = client.get(ROUTE, params={"chain": "../../etc/passwd"})
    assert response.status_code in {400, 422}
    _assert_private(response)


# --------------------------------------------------------------------------
# no fallback, no leak
# --------------------------------------------------------------------------
def test_source_failure_never_falls_back_to_a_stale_snapshot(monkeypatch, tmp_path):
    """A cached last-good answer served on failure is exactly the "old static
    fallback" the operation forbids: the researcher would read a stale state as
    the current one."""
    root = fx.build_root(tmp_path)
    with _client(monkeypatch, tmp_path, root=root) as client:
        assert client.get(ROUTE).status_code == 200
        (root / "data" / "transmission" / "chain_state.json").unlink()
        failed = client.get(ROUTE)
    assert failed.status_code == 503
    assert "path" not in failed.json().get("detail", {})


def test_error_bodies_carry_no_owner_reading(monkeypatch, tmp_path):
    root = fx.build_root(tmp_path, yaml_doc=fx.chain_yaml(rev=3),
                         state_doc=fx.chain_state(rev=2))
    with _client(monkeypatch, tmp_path, root=root) as client:
        body = client.get(ROUTE).text
    for leaked in ("receipts", "value_receipt", "confirmed", "threshold"):
        assert leaked not in body


def test_the_router_serves_no_write_verbs(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        paths = client.app.openapi()["paths"]
    assert set(paths[ROUTE]) == {'get'}, 'the snapshot remains read-only'
    assert set(paths['/api/ontology/explorer/scenario/v1']) == {'post'}


def test_a_get_does_not_mutate_the_owner_artifacts(monkeypatch, tmp_path):
    root = fx.build_root(tmp_path)
    before = {p: (p.stat().st_mtime_ns, p.stat().st_size)
              for p in sorted(root.rglob("*")) if p.is_file()}
    with _client(monkeypatch, tmp_path, root=root) as client:
        assert client.get(ROUTE).status_code == 200
    after = {p: (p.stat().st_mtime_ns, p.stat().st_size)
             for p in sorted(root.rglob("*")) if p.is_file()}
    assert before == after


def test_the_router_reuses_the_shared_entitlement_authority(monkeypatch, tmp_path):
    """A second identity path is how a paywall quietly stops being one. The
    dependency must resolve through app.main.require_user and
    app.paywall.enforce_site_full(always=True), not a local re-implementation."""
    import inspect
    source = inspect.getsource(_api().require_site_full_user)
    assert "require_user" in source
    assert "enforce_site_full" in source
    assert "always=True" in source


# --------------------------------------------------------------------------
# outcomes that never reach the endpoint at all
#
# The route class stamps headers by wrapping the endpoint. Three outcomes do not
# go through it: an exception it does not catch escapes to Starlette's outermost
# error middleware, and a method mismatch is raised by Starlette's router BEFORE
# the wrapper is entered. An independent review measured all three arriving with
# none of the private header set.
# --------------------------------------------------------------------------
def _boom_client(monkeypatch, tmp_path) -> TestClient:
    api = _api()
    root = fx.build_root(tmp_path)
    monkeypatch.setattr(api, "_repo_root", lambda: root)
    monkeypatch.setattr(api, "DEFAULT_CHAIN", fx.SLUG)
    monkeypatch.setattr(api, "ACCEPTED_CHAINS", frozenset({fx.SLUG}))

    def explode(*a, **k):
        raise ValueError("boom /Users/someone/private/path.json")

    monkeypatch.setattr(api, "compose_snapshot", explode)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "paid-user"}
    return TestClient(app, raise_server_exceptions=False)


def test_an_unexpected_exception_is_still_a_private_response(monkeypatch, tmp_path):
    with _boom_client(monkeypatch, tmp_path) as client:
        response = client.get(ROUTE)
    assert response.status_code >= 500
    _assert_private(response)


def test_an_unexpected_exception_does_not_leak_its_message(monkeypatch, tmp_path):
    """A stray exception string is where internal paths escape."""
    with _boom_client(monkeypatch, tmp_path) as client:
        body = client.get(ROUTE).text
    assert "boom" not in body
    assert "/Users/" not in body


def test_a_disallowed_method_is_still_a_private_response(monkeypatch, tmp_path):
    for method in ("post", "put", "patch", "delete"):
        with _client(monkeypatch, tmp_path) as client:
            response = getattr(client, method)(ROUTE)
        assert response.status_code == 405, method
        _assert_private(response)


def test_head_is_answered_and_is_private(monkeypatch, tmp_path):
    """A cache or crawler that probes with HEAD must not get an un-noindexed,
    un-nosniffed response."""
    with _client(monkeypatch, tmp_path) as client:
        response = client.head(ROUTE)
    assert response.status_code == 200
    _assert_private(response)
    assert response.content == b""


# --------------------------------------------------------------------------
# the chain parameter
# --------------------------------------------------------------------------
def test_a_trailing_newline_cannot_smuggle_a_slug_past_the_guard(monkeypatch, tmp_path):
    """Python's `$` matches before a trailing newline, so `^...$` accepted a slug
    with a line break appended — which then reached the composer and split one
    log call across two lines."""
    with _client(monkeypatch, tmp_path) as client:
        response = client.get(ROUTE, params={"chain": f"{fx.SLUG}\n"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unknown_chain"
    _assert_private(response)


def test_an_explicitly_empty_chain_is_rejected_not_silently_defaulted(monkeypatch, tmp_path):
    """Every other malformed value is refused; an empty one asked for something
    specific and got the default instead."""
    with _client(monkeypatch, tmp_path) as client:
        response = client.get(ROUTE, params={"chain": ""})
    assert response.status_code == 400
    _assert_private(response)


def test_the_composer_also_refuses_a_trailing_newline_slug():
    from engine.ontology_explorer import SourceUnavailable, compose_snapshot
    with pytest.raises(SourceUnavailable):
        compose_snapshot(Path("/nonexistent"), chain="oil_inflation_duration_derate\n")


# --------------------------------------------------------------------------
# the builder
# --------------------------------------------------------------------------
def test_the_builder_fails_loudly_when_a_paired_asset_is_missing(tmp_path, monkeypatch):
    """`return 0` from main() is SystemExit(0): a missing asset made the build a
    silent success that also skipped every later asset."""
    import scripts.build_ontology_explorer as builder
    monkeypatch.setattr(builder, "PAIRED_ASSETS", ("ontology.css", "definitely_absent.js"))
    # Render into tmp_path, never the real site/: build_shell writes the page
    # BEFORE it copies the paired assets, so the in-place render used to leave
    # site/ontology.html modified whenever the committed bytes differ from a
    # plain render -- which they do since the render-public lane re-stamps
    # committed pages (?v=, preload, defer) after merge. CI's MM_DATA_GUARD
    # then failed the whole job as "test session dirtied ... site/" (2026-09-24,
    # #7959; identical in the base replay, so main carried it too).
    monkeypatch.setattr(builder.config, "load",
                        lambda: {"storage": {"site_dir": str(tmp_path)}})
    assert builder.main() == 1
    assert (tmp_path / "ontology.html").exists()


def test_a_chain_that_composes_is_not_thereby_an_accepted_product(monkeypatch, tmp_path):
    """The composer is chain-generic because it is a library. A slug it can parse
    is not a product this vertical has built and proven, and serving every valid
    slug would advertise surfaces nobody verified."""
    api = _api()
    root = fx.build_root(tmp_path)
    monkeypatch.setattr(api, "_repo_root", lambda: root)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(ROUTE, params={"chain": fx.SLUG})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "chain_not_admitted"
    _assert_private(response)


def test_admission_is_limited_to_the_verified_oil_and_dollar_paths():
    from app.ontology_explorer import ACCEPTED_CHAINS, DEFAULT_CHAIN
    assert ACCEPTED_CHAINS == {"oil_inflation_duration_derate", "dollar_spike_em_multinational"}
    assert DEFAULT_CHAIN in ACCEPTED_CHAINS


@pytest.mark.parametrize('authed,entitled,status', [(False,False,401),(True,False,403),(True,True,200)])
def test_dollar_native_path_preserves_authorization_and_private_headers(monkeypatch,tmp_path,authed,entitled,status):
    api = _api()
    accepted = api.ACCEPTED_CHAINS
    root = fx.dollar_root(tmp_path)
    with _client(monkeypatch,tmp_path,root=root,authed=authed,entitled=entitled) as client:
        monkeypatch.setattr(api,'ACCEPTED_CHAINS',accepted)
        response=client.get(ROUTE,params={'chain':'dollar_spike_em_multinational'})
    assert response.status_code==status,response.text
    _assert_private(response)
    if status==200:
        body=response.json()
        assert body['source']['chain']=='dollar_spike_em_multinational'
        assert len(body['path']['legs'])==3
        assert body['source']['asof']=='2026-01-02'
        assert {s['id'] for s in body['exposure_screens']}=={
            'em_revenue_exposure','multinational_fx_translation','dollar_debt_burden','em_commodity_sector_proxy'}
    else:
        assert 'receipts' not in response.text


def test_dollar_missing_source_does_not_substitute_oil_and_duplicate_chain_is_rejected(monkeypatch,tmp_path):
    api=_api()
    accepted=api.ACCEPTED_CHAINS
    root=fx.dollar_root(tmp_path)
    with _client(monkeypatch,tmp_path,root=root) as client:
        monkeypatch.setattr(api,'ACCEPTED_CHAINS',accepted)
        duplicate=client.get(ROUTE,params=[('chain','oil_inflation_duration_derate'),('chain','dollar_spike_em_multinational')])
        assert duplicate.status_code==400
        _assert_private(duplicate)
        (root/'data/transmission/chain_state.json').unlink()
        missing=client.get(ROUTE,params={'chain':'dollar_spike_em_multinational'})
        assert missing.status_code==503 and missing.json()['detail']['code']=='source_unavailable'
        _assert_private(missing)


def test_dollar_portfolio_requires_the_exact_selected_native_snapshot(tmp_path):
    from engine.ontology_explorer import compose_snapshot
    from engine.ontology_portfolio import project_portfolio_read, PortfolioInputError
    from datetime import date
    snapshot=compose_snapshot(fx.dollar_root(tmp_path),chain='dollar_spike_em_multinational')
    payload=dict(schema='ontology_portfolio_request.v1',chain=snapshot['source']['chain'],
                 source_manifest_hash=snapshot['source']['source_manifest_hash'],symbols=['UNRESOLVED'])
    snapshot['company_exposure']['asof']='2026-01-02'
    response=project_portfolio_read(payload,snapshot=snapshot,aliases=None,identity_date=date(2026,1,4))
    assert response['chain']==payload['chain'] and response['rows'][0]['state']=='identity_unresolved'
    assert response['pnl'] is None and not any(response['authority'].values())
    with pytest.raises(PortfolioInputError,match='snapshot_changed'):
        project_portfolio_read({**payload,'chain':'oil_inflation_duration_derate'},snapshot=snapshot,aliases=None,identity_date=date(2026,1,4))


SCENARIO_ROUTE = '/api/ontology/explorer/scenario/v1'


def _rates_scenario_client(monkeypatch, tmp_path, x2_inputs, *, old=False):
    from tests.test_rate_inflation_transmission import _native_scenario_calibration
    from engine import ontology_scenario_runtime as runtime
    client, root = _qualified_scenario_client(monkeypatch, tmp_path, x2_inputs)
    def forbidden(*a, **k): raise AssertionError('rates must not enter WTI series/calendar adapter')
    monkeypatch.setattr(runtime, '_load_native_baseline', forbidden)
    cal, _ = _native_scenario_calibration(monkeypatch, asof=x2_inputs[2].effective_at)
    if old: cal.pop('scenario_beta_metadata')
    path = root/'data/transmission/calibration.json'
    path.write_text(json.dumps(cal))
    return client, root, path, cal


def _rates_payload(snapshot):
    payload = _scenario_payload(snapshot)
    payload['assumption'].update(node_ref='transmission:real10y_chg63', shock_definition='absolute_change_bp_over_horizon',
      magnitude=50, unit='bp', horizon='63d', path_shape='terminal_only')
    return payload


def test_rates_scenario_native_emitter_to_private_http_without_recalibration_or_writes(monkeypatch, tmp_path, x2_inputs):
    from scripts import calibrate_rate_inflation as producer
    client, root, path, cal = _rates_scenario_client(monkeypatch, tmp_path, x2_inputs)
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    def forbidden(*a, **k): raise AssertionError('HTTP request tried to fit/read input series')
    monkeypatch.setattr(producer, 'scenario_betas', forbidden)
    monkeypatch.setattr(producer.inputs, 'build_features', forbidden)
    monkeypatch.setattr(producer.inputs, 'yahoo_closes', forbidden)
    with client:
        snapshot = client.get(ROUTE).json()
        assert any(r['path']=='data/transmission/calibration.json' for r in snapshot['source']['reads'])
        response = client.post(SCENARIO_ROUTE, json=_rates_payload(snapshot))
        repeated = client.post(SCENARIO_ROUTE, json=_rates_payload(snapshot))
    _assert_scenario_private(response)
    assert response.status_code == 200
    value = response.json(); numeric = value['root_evaluation']
    assert numeric['status'] == 'NUMERIC_ILLUSTRATION'
    assert numeric['method_class'] == 'EMPIRICAL_SAME_WINDOW_BETA'
    assert numeric['scenario']['shock_bp'] == 50 and numeric['coverage']['displayed_assets'] == ['SPY','TLT']
    assert all(not v for v in value['authority'].values()) and all(v == 0 for v in value['side_effect_receipt'].values())
    assert value['combined_estimate'] is None and all(h['value'] is None for h in value['hop_evaluations'])
    assert value['owner_receipt']['generation'].startswith('sha256:')
    assert value['owner_receipt']['knowledge_cutoff'] == cal['scenario_beta_metadata']['generated_at']
    assert value['owner_receipt']['selected_knowledge_cutoff'] == snapshot['source']['built']
    assert 'rights_ref' not in value['owner_receipt']
    assert repeated.json()['scenario_eval_id'] == value['scenario_eval_id']
    assert {p:p.read_bytes() for p in root.rglob('*') if p.is_file()} == before


def test_rates_old_scalar_artifact_is_typed_unavailable_but_stays_in_selected_manifest(monkeypatch, tmp_path, x2_inputs):
    client, root, path, _ = _rates_scenario_client(monkeypatch, tmp_path, x2_inputs, old=True)
    with client:
        snapshot = client.get(ROUTE).json()
        response = client.post(SCENARIO_ROUTE, json=_rates_payload(snapshot))
    assert response.status_code == 200
    assert response.json()['root_evaluation']['reason'] == 'NUMERIC_OWNER_METADATA_UNAVAILABLE'
    _assert_scenario_private(response)


def test_rates_selected_generation_change_refuses_instead_of_substituting_new_calibration(monkeypatch, tmp_path, x2_inputs):
    client, root, path, _ = _rates_scenario_client(monkeypatch, tmp_path, x2_inputs)
    with client:
        snapshot = client.get(ROUTE).json()
        path.write_bytes(path.read_bytes()+b'\n')
        response = client.post(SCENARIO_ROUTE, json=_rates_payload(snapshot))
    assert response.status_code == 409 and response.json()['detail']['code'] == 'source_changed'
    _assert_scenario_private(response)


def test_rates_scenario_rechecks_native_bytes_after_numeric_composition(monkeypatch, tmp_path, x2_inputs):
    from engine import rate_inflation_transmission as owner
    client, root, path, _ = _rates_scenario_client(monkeypatch, tmp_path, x2_inputs)
    original = owner.evaluate_scenario_beta
    def changed(*a, **kw):
        value = original(*a, **kw)
        path.write_bytes(path.read_bytes()+b'\n')
        return value
    monkeypatch.setattr(owner, 'evaluate_scenario_beta', changed)
    with client:
        response = client.post(SCENARIO_ROUTE, json=_rates_payload(client.get(ROUTE).json()))
    assert response.status_code == 503
    assert 'NUMERIC_ILLUSTRATION' not in response.text
    _assert_scenario_private(response)


def _scenario_payload(snapshot):
    return {'schema':'ontology_scenario_request.v1',
            'source_manifest_hash':snapshot['source']['source_manifest_hash'],
            'assumption':{'schema':'ontology_scenario_assumption.v1','node_ref':'yahoo:CL=F',
                'shock_definition':'terminal_change_over_horizon','magnitude':30,'unit':'percent',
                'horizon':'60d','path_shape':'linear_sessions','origin_class':'supply',
                'baseline_effective_at':snapshot['source']['asof'],
                'baseline_knowledge_cutoff':snapshot['source']['built']}}


def test_x2_post_runs_only_after_auth_and_returns_private_native_refusal(monkeypatch, tmp_path):
    # Default loader must explain actual native gaps, never fabricate a calendar.
    from engine import ontology_scenario_runtime as runtime
    monkeypatch.setattr(runtime,'DEFAULT_CHAIN',fx.SLUG)
    with _client(monkeypatch,tmp_path) as client:
        payload = _scenario_payload(client.get(ROUTE).json())
        response = client.post(SCENARIO_ROUTE,json=payload)
    assert response.status_code == 200
    _assert_scenario_private(response)
    assert response.json()['root_evaluation']['reason'] == 'WTI_FUTURES_CALENDAR_UNAVAILABLE'
    assert response.json()['combined_estimate'] is None


def _assert_scenario_private(response):
    for key,value in REQUIRED_PRIVATE_HEADERS.items():
        if key != 'vary': assert response.headers.get(key) == value
    assert {'authorization','cookie'} <= {s.strip().lower() for s in response.headers['vary'].split(',')}


@pytest.mark.parametrize('authed,entitled,status',[(False,True,401),(True,False,403)])
def test_x2_auth_precedes_body_and_source_access(monkeypatch,tmp_path,authed,entitled,status):
    api = _api()
    def forbidden(*args,**kwargs): raise AssertionError('owner read before entitlement')
    with _client(monkeypatch,tmp_path,authed=authed,entitled=entitled) as client:
        monkeypatch.setattr(api,'evaluate_current_scenario',forbidden)
        response=client.post(SCENARIO_ROUTE,content=b'private malformed assumption')
    assert response.status_code==status
    _assert_scenario_private(response)


@pytest.mark.parametrize('body,headers,status',[
    (b'{}',{'content-type':'text/plain'},415),
    (b'{}',{'content-type':'application/json','content-encoding':'gzip'},415),
    (b'{}',{'content-type':'application/json','content-length':'9000'},413),
    (b'{}',{'content-type':'application/json','content-length':'invalid'},400),
    (b'x'*4097,{'content-type':'application/json'},413),
    (b'{"schema":"a","schema":"b"}',{'content-type':'application/json'},400),
    (b'{"private":"DO_NOT_ECHO"}',{'content-type':'application/json'},400),
])
def test_x2_bounded_parsing_never_echoes_private_input(monkeypatch,tmp_path,body,headers,status,caplog):
    with _client(monkeypatch,tmp_path) as client:
        response=client.post(SCENARIO_ROUTE,content=body,headers=headers)
    assert response.status_code==status
    _assert_scenario_private(response)
    assert 'DO_NOT_ECHO' not in response.text and 'DO_NOT_ECHO' not in caplog.text


def test_x2_post_rejects_source_change_and_query_parameters(monkeypatch,tmp_path):
    from engine import ontology_scenario_runtime as runtime
    monkeypatch.setattr(runtime,'DEFAULT_CHAIN',fx.SLUG)
    with _client(monkeypatch,tmp_path) as client:
        payload=_scenario_payload(client.get(ROUTE).json())
        payload['source_manifest_hash']='sha256:'+'0'*64
        response=client.post(SCENARIO_ROUTE,json=payload)
        query=client.post(SCENARIO_ROUTE+'?magnitude=30',json=payload)
    assert response.status_code==409 and response.json()['detail']['code']=='source_changed'
    assert query.status_code==400
    _assert_scenario_private(response); _assert_scenario_private(query)


def test_x2_unexpected_error_does_not_log_assumption_or_exception(monkeypatch,tmp_path,caplog):
    api=_api()
    with _client(monkeypatch,tmp_path) as client:
        payload=_scenario_payload(client.get(ROUTE).json())
        def explode(*args,**kwargs): raise ValueError('PRIVATE_SOURCE_AND_ASSUMPTION')
        monkeypatch.setattr(api,'evaluate_current_scenario',explode)
        response=client.post(SCENARIO_ROUTE,json=payload)
    assert response.status_code==500
    _assert_scenario_private(response)
    assert 'PRIVATE_SOURCE_AND_ASSUMPTION' not in response.text+caplog.text


@pytest.mark.parametrize('method',['get','head','put','patch','delete','options'])
def test_x2_other_verbs_cannot_run_evaluation(monkeypatch,tmp_path,method):
    with _client(monkeypatch,tmp_path) as client:
        response=getattr(client,method)(SCENARIO_ROUTE)
    assert response.status_code==405
    assert response.headers['allow']=='POST'
    _assert_scenario_private(response)


from tests.test_ontology_explorer_contract import x2_inputs


def _qualified_scenario_client(monkeypatch,tmp_path,x2_inputs):
    from dataclasses import replace
    from engine import ontology_scenario_runtime as runtime
    snapshot,chain,baseline,assumption=x2_inputs
    ids=list(chain['nodes'])
    mapping=dict(zip(['n1','n2','n3','n4'],ids))
    state=fx.chain_state(slug=chain['chain'])
    state.update(asof=baseline.effective_at,built=baseline.knowledge_cutoff)
    for node in state['chains'][0]['nodes']: node['id']=mapping[node['id']]
    for hop in state['chains'][0]['hops']:
        hop['from']=mapping[hop['from']];hop['to']=mapping[hop['to']]
    root=fx.build_root(tmp_path,yaml_doc=chain,state_doc=state,slug=chain['chain'])
    def qualified(root,snapshot,assumption):
        return replace(baseline,source_manifest_hash=snapshot['source']['source_manifest_hash'])
    monkeypatch.setattr(runtime,'_load_native_baseline',qualified)
    return _client(monkeypatch,tmp_path,root=root,chain=chain['chain']),root


def test_x2_http_handoff_evaluates_qualified_synthetic_owner_inputs_without_writes(monkeypatch,tmp_path,x2_inputs):
    client,root=_qualified_scenario_client(monkeypatch,tmp_path,x2_inputs)
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with client:
        payload=_scenario_payload(client.get(ROUTE).json())
        first=client.post(SCENARIO_ROUTE,json=payload)
        second=client.post(SCENARIO_ROUTE,json=payload)
    assert first.status_code==second.status_code==200
    assert first.json()['root_evaluation']['status']=='ROOT_THRESHOLD_MET'
    assert first.json()['scenario_eval_id']==second.json()['scenario_eval_id']
    assert first.json()['combined_estimate'] is None
    assert all(v==0 for v in first.json()['side_effect_receipt'].values())
    assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    _assert_scenario_private(first)


def test_x2_post_detects_owner_mutation_after_evaluation(monkeypatch,tmp_path,x2_inputs):
    from engine import ontology_scenario_runtime as runtime
    client,root=_qualified_scenario_client(monkeypatch,tmp_path,x2_inputs)
    original=runtime._load_native_baseline
    def changing(*args):
        baseline=original(*args)
        target=root/'data/transmission/chain_state.json'
        target.write_bytes(target.read_bytes()+b'\n')
        return baseline
    monkeypatch.setattr(runtime,'_load_native_baseline',changing)
    with client:
        response=client.post(SCENARIO_ROUTE,json=_scenario_payload(client.get(ROUTE).json()))
    assert response.status_code==503
    assert 'assumption' not in response.text and 'receipts' not in response.text
    _assert_scenario_private(response)


def test_x2_nested_duplicate_assumption_is_rejected(monkeypatch,tmp_path):
    with _client(monkeypatch,tmp_path) as client:
        raw=json.dumps(_scenario_payload(client.get(ROUTE).json()))
        raw=raw.replace('"magnitude": 30','"magnitude": 30, "magnitude": 20')
        response=client.post(SCENARIO_ROUTE,content=raw,headers={'content-type':'application/json'})
    assert response.status_code==400
    _assert_scenario_private(response)


def test_x2_validation_dependency_cannot_echo_private_inputs(monkeypatch,tmp_path):
    from fastapi.exceptions import RequestValidationError
    api=_api()
    with _client(monkeypatch,tmp_path) as client:
        def bad_dependency():
            raise RequestValidationError([{'type':'value_error','loc':('body',),
                                          'input':'PRIVATE_VALIDATION_INPUT','msg':'PRIVATE_VALIDATION_MESSAGE'}])
        client.app.dependency_overrides[api.require_site_full_user]=bad_dependency
        response=client.post(SCENARIO_ROUTE,content=b'{}',headers={'content-type':'application/json'})
    assert response.status_code==422
    assert 'PRIVATE_VALIDATION' not in response.text
    _assert_scenario_private(response)


@pytest.mark.parametrize('declared',[None,'2'])
def test_x2_stream_bound_applies_without_honest_content_length(monkeypatch,tmp_path,declared):
    headers={'content-type':'application/json'}
    if declared is not None: headers['content-length']=declared
    with _client(monkeypatch,tmp_path) as client:
        response=client.post(SCENARIO_ROUTE,content=iter([b'x'*2050,b'x'*2050]),headers=headers)
    assert response.status_code==413
    if declared is None: assert 'content-length' not in response.request.headers
    _assert_scenario_private(response)


def test_x2_body_wait_has_a_real_deadline():
    import asyncio
    from starlette.requests import Request
    api=_api()
    async def exercise():
        async def silent(): await asyncio.Event().wait()
        request=Request({'type':'http','method':'POST','path':SCENARIO_ROUTE,'query_string':b'',
                         'headers':[(b'content-type',b'application/json')]},receive=silent)
        with pytest.raises(HTTPException) as error:
            await api._private_post_body(request)
        assert error.value.status_code==408
        assert error.value.detail['code']=='body_deadline_exceeded'
    asyncio.run(exercise())


PORTFOLIO_ROUTE='/api/ontology/explorer/portfolio/v1'


def _portfolio_native_client(monkeypatch,tmp_path):
    import pandas as pd
    from engine import ontology_explorer as explorer
    monkeypatch.setattr(explorer,'DEFAULT_CHAIN',fx.SLUG)
    state=fx.chain_state(state='arming')
    state['substrate']={'universe':10,'substrate_asof':{'min':'2026-01-01','max':'2026-01-02'}}
    state['chains'][0]['blast']={'synthetic_screen':{'resolved':True,'n':2,'unevaluable':1,
        'names':['OLD','REUSED'],'cuts':{},'label':{'en':'Synthetic','zh':'合成'},
        'note':{'en':'Synthetic membership','zh':'合成成员'}}}
    root=fx.build_root(tmp_path,state_doc=state)
    records=[{'vendor':'store','vendor_symbol':symbol,'security_id':sid,'valid_from':start,'valid_to':end}
             for symbol,sid,start,end in [
                 ('OLD','SEC:US-XNYS-OLD',None,'2026-02-01'),
                 ('NEW','SEC:US-XNYS-OLD','2026-02-01',None),
                 ('REUSED','SEC:US-XNYS-REUSED',None,'2026-02-01'),
                 ('REUSED','SEC:US-XNYS-REUSED.2','2026-02-01',None)]]
    target=root/'data/reference/vendor_aliases.parquet';target.parent.mkdir(parents=True)
    pd.DataFrame(records).to_parquet(target,index=False)
    return _client(monkeypatch,tmp_path,root=root),root


def _portfolio_payload(snapshot):
    return {'schema':'ontology_portfolio_request.v1','chain':fx.SLUG,
            'source_manifest_hash':snapshot['source']['source_manifest_hash'],
            'symbols':['NEW','REUSED','MISSING']}


def test_x4_private_http_runs_actual_composer_alias_reader_and_portfolio_join(monkeypatch,tmp_path):
    client,root=_portfolio_native_client(monkeypatch,tmp_path)
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with client:
        snapshot=client.get(ROUTE).json()
        response=client.post(PORTFOLIO_ROUTE,json=_portfolio_payload(snapshot))
    assert response.status_code==200,response.text
    result=response.json()
    assert result['rows'][0]['state']=='covered'
    assert result['rows'][0]['security_id']=='SEC:US-XNYS-OLD'
    assert result['rows'][1]['state']=='not_in_available_screens'
    assert result['rows'][1]['security_id']=='SEC:US-XNYS-REUSED.2'
    assert result['rows'][2]['state']=='identity_unresolved'
    assert result['pnl'] is None and not any(result['authority'].values())
    assert 'shares' not in response.text and 'notes' not in response.text
    assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    _assert_scenario_private(response)


@pytest.mark.parametrize('authed,entitled,status',[(False,True,401),(True,False,403)])
def test_x4_auth_precedes_private_body_and_owner_reads(monkeypatch,tmp_path,authed,entitled,status):
    api=_api()
    with _client(monkeypatch,tmp_path,authed=authed,entitled=entitled) as client:
        def forbidden(*args): raise AssertionError('private portfolio read before auth')
        monkeypatch.setattr(api,'compose_portfolio_read',forbidden)
        response=client.post(PORTFOLIO_ROUTE,content=b'PRIVATE_INVALID_BODY')
    assert response.status_code==status
    _assert_scenario_private(response)


@pytest.mark.parametrize('mutation',[lambda r:r.update(shares=[123]),lambda r:r.update(symbols=['NEW','NEW'])])
def test_x4_domain_rejection_has_no_private_echo(monkeypatch,tmp_path,mutation,caplog):
    client,_=_portfolio_native_client(monkeypatch,tmp_path)
    with client:
        payload=_portfolio_payload(client.get(ROUTE).json());mutation(payload)
        response=client.post(PORTFOLIO_ROUTE,json=payload)
    assert response.status_code==400
    assert 'NEW' not in response.text+caplog.text
    _assert_scenario_private(response)


def test_x4_changed_snapshot_and_response_ceiling_fail_closed(monkeypatch,tmp_path):
    api=_api();client,_=_portfolio_native_client(monkeypatch,tmp_path)
    with client:
        payload=_portfolio_payload(client.get(ROUTE).json())
        changed={**payload,'source_manifest_hash':'sha256:'+'0'*64}
        response=client.post(PORTFOLIO_ROUTE,json=changed)
        monkeypatch.setattr(api,'compose_portfolio_read',lambda *args:{'private':'x'*262145})
        oversize=client.post(PORTFOLIO_ROUTE,json=payload)
    assert response.status_code==409
    assert oversize.status_code==503 and oversize.json()['detail']['code']=='response_too_large'
    _assert_scenario_private(response);_assert_scenario_private(oversize)


@pytest.mark.parametrize('method',['get','head','put','patch','delete','options'])
def test_x4_no_other_method_reads_private_portfolio(monkeypatch,tmp_path,method):
    with _client(monkeypatch,tmp_path) as client:
        response=getattr(client,method)(PORTFOLIO_ROUTE)
    assert response.status_code==405 and response.headers['allow']=='POST'
    _assert_scenario_private(response)


def test_x4_duplicate_and_stream_request_bounds(monkeypatch,tmp_path):
    with _client(monkeypatch,tmp_path) as client:
        duplicate=client.post(PORTFOLIO_ROUTE,content=b'{"symbols":[],"symbols":[]}',headers={'content-type':'application/json'})
        oversize=client.post(PORTFOLIO_ROUTE,content=iter([b'x'*40000,b'x'*40000]),headers={'content-type':'application/json'})
    assert duplicate.status_code==400 and oversize.status_code==413
    _assert_scenario_private(duplicate);_assert_scenario_private(oversize)


def test_x4_actual_numeric_nan_validity_is_not_normalized_to_unbounded(monkeypatch,tmp_path):
    import pyarrow as arrow
    import pyarrow.parquet as parquet
    client,root=_portfolio_native_client(monkeypatch,tmp_path)
    path=root/'data/reference/vendor_aliases.parquet'
    records=parquet.read_table(path).to_pylist()
    for row in records:
        row['valid_from']=float('nan');row['valid_to']=None
    parquet.write_table(arrow.Table.from_pylist(records),path)
    with client:
        snapshot=client.get(ROUTE).json()
        response=client.post(PORTFOLIO_ROUTE,json=_portfolio_payload(snapshot))
    assert snapshot['company_exposure']['identity_source']['status']=='unavailable'
    assert response.status_code==200
    assert all(row['security_id'] is None and row['state']=='identity_unresolved' for row in response.json()['rows'])
    _assert_scenario_private(response)


THEME_ROUTE = '/api/ontology/explorer/theme/v1'


def _theme_owner_root(tmp_path):
    import pyarrow as arrow
    import pyarrow.parquet as parquet
    from engine.theme_graph import store
    from test_theme_graph_hierarchy_paths import _selected_house_view, _selected_security_row
    root = fx.build_root(tmp_path)
    view = _selected_house_view()
    tables = {'nodes': (view._nodes, store.NODE_COLUMNS), 'edges': (view._edges, store.EDGE_COLUMNS),
              'node_lifecycle': ([], store.NODE_LIFECYCLE_COLUMNS),
              'evidence': (view._evidence, store.EVIDENCE_COLUMNS),
              'identity_resolution': ([_selected_security_row()], store.IDENTITY_RESOLUTION_COLUMNS)}
    directory = root / 'data/theme_graph'
    directory.mkdir(parents=True)
    for name, (rows, columns) in tables.items():
        table = arrow.Table.from_pylist(rows) if rows else arrow.table({c: [] for c in columns})
        parquet.write_table(table, directory / f'{name}.parquet')
    (root / 'config').mkdir()
    (root / 'config/theme_sources.yml').write_bytes((Path(__file__).parents[1] / 'config/theme_sources.yml').read_bytes())
    return root


def _theme_body(client):
    return dict(schema='ontology_theme_request.v1', chain=fx.SLUG,
        source_manifest_hash=client.get(ROUTE).json()['source']['source_manifest_hash'],
        identity_kind='security', identity_id='SEC:US-XNAS-AAA')


def test_theme_actual_native_http_read_is_house_only_and_byte_bound(monkeypatch, tmp_path):
    import hashlib
    root = _theme_owner_root(tmp_path)
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with _client(monkeypatch, tmp_path, root=root) as client:
        body = _theme_body(client)
        response = client.post(THEME_ROUTE, json=body)
    assert response.status_code == 200, response.text
    assert response.headers['vary'] == 'Authorization, Cookie'
    assert response.headers['cache-control'] == 'private, no-store'
    result = response.json()
    assert result['source']['source_manifest_hash'] == body['source_manifest_hash']
    assert result['source']['built'] == '2026-01-03 02:10 UTC'
    assert result['theme_map']['knowledge_cutoff'] == '2026-01-03T02:10:00+00:00'
    assert result['theme_map']['availability']['state'] == 'AVAILABLE'
    assert 'PRIVATE' not in response.text and 'ltheme:' not in response.text
    assert 'source_receipts' not in response.text and 'research_internal_only' not in response.text
    assert len(result['source']['reads']) == 6
    for receipt in result['source']['reads']:
        assert hashlib.sha256(before[receipt['path']]).hexdigest() == receipt['sha256']
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('kind,identity', [('ticker','AAA'), ('security','AAA'), ('issuer','SEC:US-XNAS-AAA'),
    ('security','SEC: US-XNAS-AAA'), ('security', ['SEC:US-XNAS-AAA'])])
def test_theme_rejects_labels_and_mismatched_identity(monkeypatch, tmp_path, kind, identity):
    with _client(monkeypatch, tmp_path) as client:
        body = _theme_body(client); body.update(identity_kind=kind, identity_id=identity)
        response = client.post(THEME_ROUTE, json=body)
    assert response.status_code == 400
    assert response.headers['cache-control'] == 'private, no-store'


@pytest.mark.parametrize('mutation', ['stale', 'missing', 'policy', 'mid_read', 'snapshot_mid_read'])
def test_theme_withholds_changed_or_unavailable_source(monkeypatch, tmp_path, mutation):
    from engine import ontology_theme as owner
    root = _theme_owner_root(tmp_path)
    with _client(monkeypatch, tmp_path, root=root) as client:
        body = _theme_body(client)
        if mutation == 'stale': body['source_manifest_hash'] = 'sha256:' + '0' * 64
        elif mutation == 'missing': (root / 'data/theme_graph/nodes.parquet').unlink()
        elif mutation == 'policy': (root / 'config/theme_sources.yml').write_text('families: {mastermind_curated: {rights_class: internal_only, auth_class: house}}')
        else:
            original = owner.security_navigation.compose_security_hierarchy
            def changed(*a, **kw):
                result = original(*a, **kw)
                path = root / ('data/theme_graph/nodes.parquet' if mutation == 'mid_read' else owner.explorer._STATE_REL)
                path.write_bytes(path.read_bytes() + b' ')
                return result
            monkeypatch.setattr(owner.security_navigation, 'compose_security_hierarchy', changed)
        response = client.post(THEME_ROUTE, json=body)
    assert response.status_code == (409 if mutation == 'stale' else 503)
    assert 'bindings' not in response.text and 'PRIVATE' not in response.text


@pytest.mark.parametrize('authed,entitled,code', [(False, True,401), (True,False,403)])
def test_theme_auth_precedes_owner_io(monkeypatch, tmp_path, authed, entitled, code):
    monkeypatch.setattr(_api(), 'compose_theme_continuation', lambda *a: pytest.fail('source read before auth'))
    with _client(monkeypatch, tmp_path, authed=authed, entitled=entitled) as client:
        response = client.post(THEME_ROUTE, json={})
    assert response.status_code == code
    assert response.headers['vary'] == 'Authorization, Cookie'


def test_theme_duplicate_request_private_bounds_and_methods(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        assert client.post(THEME_ROUTE, content='{"schema":1,"schema":2}', headers={'content-type':'application/json'}).status_code == 400
        assert client.post(THEME_ROUTE, content='x' * 4097, headers={'content-type':'application/json'}).status_code == 413
        assert client.post(THEME_ROUTE+'?identity_id=secret', json={}).status_code == 400
        assert client.post(THEME_ROUTE, content='{}', headers={'content-type':'text/plain'}).status_code == 415
        for method in ['get','head','put','patch','delete','options']:
            response = getattr(client,method)(THEME_ROUTE)
            assert response.status_code == 405 and response.headers['cache-control'] == 'private, no-store'



def test_theme_uses_existing_product_admission_and_response_ceiling(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        body = _theme_body(client)
        body['chain'] = 'unadmitted_chain'
        assert client.post(THEME_ROUTE, json=body).status_code == 404
        body['chain'] = fx.SLUG
        monkeypatch.setattr(_api(), 'compose_theme_continuation', lambda *a: {'payload': 'x' * 262144})
        response = client.post(THEME_ROUTE, json=body)
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'response_too_large'
        assert response.headers['vary'] == 'Authorization, Cookie'


def test_theme_http_binds_tracking_references_to_selected_source_and_private_route(monkeypatch, tmp_path):
    import pyarrow as arrow
    import pyarrow.parquet as parquet
    from tests.test_theme_graph_hierarchy_paths import _selected_etf_view
    root = _theme_owner_root(tmp_path)
    view = _selected_etf_view()
    for name, rows in [('nodes',view._nodes),('edges',view._edges),('evidence',view._evidence)]:
        parquet.write_table(arrow.Table.from_pylist(rows), root / 'data/theme_graph' / (name+'.parquet'))
    before = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with _client(monkeypatch, tmp_path, root=root) as client:
        request = _theme_body(client)
        response = client.post(THEME_ROUTE,json=request)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['vary'] == 'Authorization, Cookie'
    value = response.json()
    assert value['selection']['identity_id'] == request['identity_id']
    assert value['source']['source_manifest_hash'] == request['source_manifest_hash']
    assert value['theme_map']['etf_tracking']['references'][0]['selected_security_id'] == request['identity_id']
    assert len(value['source']['reads']) == 6
    assert value['theme_map']['etf_tracking']['holdings']['asof'] is None
    assert before == {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mutation', ['authority_revoked', 'both_revoked', 'malformed', 'invalid_yaml', 'mid_read', 'class_changed'])
def test_theme_binds_fresh_code_authority_even_with_separate_data_root_and_warm_cache(monkeypatch, tmp_path, mutation):
    from engine import ontology_theme as owner
    from engine.theme_graph import rights
    root = _theme_owner_root(tmp_path / 'estate')
    data_policy = root / 'config/theme_sources.yml'
    authority = tmp_path / 'code/config/theme_sources.yml'
    authority.parent.mkdir(parents=True)
    authority.write_bytes(data_policy.read_bytes())
    monkeypatch.setattr(rights, 'registry_path', lambda: authority)
    rights._load.cache_clear()
    try:
        assert rights.rights_class('mastermind_curated') == 'direct_display_ok'
        with _client(monkeypatch, tmp_path, root=root) as client:
            request = _theme_body(client)
            if mutation in ('authority_revoked', 'both_revoked'):
                authority.write_text('families: {mastermind_curated: {rights_class: internal_only, auth_class: house}}')
                if mutation == 'both_revoked': data_policy.write_bytes(authority.read_bytes())
            elif mutation in ('malformed', 'invalid_yaml'):
                authority.write_text('families: {mastermind_curated: true}' if mutation == 'malformed' else 'families: [')
                data_policy.write_bytes(authority.read_bytes())
            elif mutation == 'mid_read':
                original = owner.security_navigation.compose_security_hierarchy
                def changed(*args, **kwargs):
                    value = original(*args, **kwargs)
                    authority.write_bytes(authority.read_bytes() + b'\n')
                    return value
                monkeypatch.setattr(owner.security_navigation, 'compose_security_hierarchy', changed)
            else:
                authority.write_bytes(authority.read_bytes().replace(b'rights_class: direct_display_ok', b'rights_class: derived_display_ok'))
                data_policy.write_bytes(authority.read_bytes())
            # The incumbent cache remains permissive; the serving guard must
            # enforce the actual authority bytes instead of trusting this cache.
            assert rights.rights_class('mastermind_curated') == 'direct_display_ok'
            response = client.post(THEME_ROUTE, json=request)
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.headers['vary'] == 'Authorization, Cookie'
        if mutation == 'class_changed':
            assert response.status_code == 200, response.text
            value = response.json()
            assert value['source']['policy_binding'] == 'AUTHORITATIVE_CODE_REGISTRY_EQUALS_SELECTED_SOURCE'
            paths = value['theme_map']['bindings'][0]['paths']
            assert paths
            assert all(n['rights']['rights_class'] == 'derived_display_ok' for p in paths for n in p['path']+[h['node'] for h in p['via']])
        else:
            assert response.status_code == 503, response.text
            # The private transport deliberately collapses source failures.
            assert response.json()['detail']['code'] == 'source_unavailable'
            assert 'bindings' not in response.text
    finally:
        rights._load.cache_clear()


@pytest.mark.parametrize('asof', ['2026-01-04T07:00:00+09:00', '2026-W01-3', '2026-01-02T09:00:00Z', '2026-01-04'])
def test_theme_refuses_noncalendar_or_after_build_observation_clock(monkeypatch, tmp_path, asof):
    root = _theme_owner_root(tmp_path)
    path = root / 'data/transmission/chain_state.json'
    state = json.loads(path.read_text())
    state['asof'] = asof
    path.write_text(json.dumps(state))
    with _client(monkeypatch, tmp_path, root=root) as client:
        response = client.post(THEME_ROUTE, json=_theme_body(client))
    assert response.status_code == 503, response.text
    assert response.json()['detail']['code'] == 'source_unavailable'
    assert response.headers['cache-control'] == 'private, no-store'
    assert 'bindings' not in response.text


@pytest.mark.parametrize('mutate_source',[False,True])
def test_theme_etf_adoption_uses_native_alias_and_rechecks_identity_generation(monkeypatch,tmp_path,mutate_source):
    import pyarrow as arrow
    import pyarrow.parquet as parquet
    from tests.test_theme_graph_hierarchy_paths import _etf_adoption_inputs
    from engine.theme_graph import identity_resolution as owner
    root=_theme_owner_root(tmp_path)
    view,sources,*_=_etf_adoption_inputs(tmp_path/'classification',monkeypatch)
    for name,rows in [('nodes',view._nodes),('edges',view._edges),('evidence',view._evidence)]:
        parquet.write_table(arrow.Table.from_pylist(rows),root/'data/theme_graph'/(name+'.parquet'))
    for rel,raw in sources.items():
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    original=owner.adopt_etf_references
    if mutate_source:
        def changed(*args,**kwargs):
            value=original(*args,**kwargs)
            path=root/'data/reference/security_master.parquet';path.write_bytes(path.read_bytes()+b'changed')
            return value
        monkeypatch.setattr(owner,'adopt_etf_references',changed)
    with _client(monkeypatch,tmp_path,root=root) as client:
        response=client.post(THEME_ROUTE,json=_theme_body(client))
    assert response.status_code==(503 if mutate_source else 200),response.text
    if mutate_source:
        assert 'SEC:US-XNAS-DIFFERENT' not in response.text and 'references' not in response.text
    else:
        value=response.json();tracking=value['theme_map']['etf_tracking']
        assert tracking['security_identity']['status']=='available'
        assert tracking['references'][0]['security_identity']['security_id']=='SEC:US-XNAS-DIFFERENT'
        assert tracking['references'][0]['selected_security_id']=='SEC:US-XNAS-AAA'
        assert len(value['source']['reads'])==11
        assert tracking['holdings']['status']=='unavailable'


def test_router_import_and_auth_refusal_do_not_load_numeric_owner_runtime():
    import subprocess
    probe = """
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.', 1)[0] in {'pandas', 'numpy', 'pyarrow', 'jsonschema', 'referencing'}:
        raise AssertionError('numeric owner loaded before an authorized scenario')
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import ontology_explorer as api
app = FastAPI()
app.include_router(api.router)
def refuse():
    raise HTTPException(401, 'authentication required')
app.dependency_overrides[api.require_site_full_user] = refuse
with TestClient(app) as client:
    for path in ['/api/ontology/explorer/v1', '/api/ontology/explorer/scenario/v1', '/api/ontology/explorer/theme/v1']:
        response = client.request('GET' if path == '/api/ontology/explorer/v1' else 'POST', path,
                                  content=b'private malformed assumption')
        assert response.status_code == 401
        assert response.headers['cache-control'] == 'private, no-store'
        assert 'private malformed assumption' not in response.text
"""
    result = subprocess.run([sys.executable, '-c', probe],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
