"""Exact customer request boundary; synthetic owners do not admit a study."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import market_memory as api
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.research_factory import market_memory_outcome_use as outcome
from tests.test_market_memory_retained_consumer import original, bounded_cohort_reuse, call
from tests.test_market_memory_outcome_use import (
    native_use, selected_use, selection, records, inputs, bundle, task_bundle,
    corpus, published, Policy,
)


def request_for(value, *, lens="then_known"):
    cutoff = value.get("query_cutoff") or value["owner"]["query_cutoff"]
    return {"retrieval_id": value["retrieval_id"], "selection_sha256": value["selection_sha256"],
            "lens": lens, "outcome_cutoff": cutoff}


def test_http_reconstructs_original_selection_and_preserves_private_response(original, monkeypatch):
    comparison = call(original)
    expected = request_for(comparison)
    seen = []
    def dormant(selection, *, site_policy, **request):
        native = retrieval.disclose_episode_retrieval(selection, policy=site_policy)
        seen.append((native["retrieval_id"], request))
        return None
    monkeypatch.setattr(outcome, "discover_registered_outcome_use", dormant)
    monkeypatch.setattr(api, "_repo_root", lambda: original[0])
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "member"}
    client = TestClient(app)
    response = client.get('/api/market-memory/v1/macro/retained/outcomes', params={**original[3], **expected})
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['vary'] == 'Authorization'
    assert response.json()['attachment'] is None and response.json()['status'] == 'NOT_CONFIGURED'
    assert seen[0][0] == expected['retrieval_id']
    assert seen[0][1]['lens'] == 'then_known'
    duplicate = client.get('/api/market-memory/v1/macro/retained/outcomes',
        params=list({**original[3], **expected}.items()) + [('lens', 'later_observed')])
    assert duplicate.status_code == 400 and len(seen) == 1


def test_changed_comparison_is_rejected_before_outcome_discovery(original, monkeypatch):
    expected = request_for(call(original))
    expected['selection_sha256'] = 'e' * 64
    monkeypatch.setattr(outcome, 'discover_registered_outcome_use', lambda *a, **k: pytest.fail('changed selection'))
    with pytest.raises(HTTPException) as failure:
        api.retained_macro_for_user(original[0], 'member', original[3], _outcome_request=expected)
    assert failure.value.status_code == 409


@pytest.mark.parametrize('change', [
    {'study_id': 'customer-selected-study'}, {'observation_generation_ref': {}},
    {'retrieval_id': 'mmretainedretrieval_bad'}, {'outcome_use_identity': None},
    {'outcome_cutoff': '2026-02-30T00:00:00Z'}, {'lens': 'latest'},
])
def test_invalid_or_authority_shaped_requests_reject_before_owner(original, monkeypatch, change):
    expected = {**request_for(call(original)), **change}
    monkeypatch.setattr(outcome, 'discover_registered_outcome_use', lambda *a, **k: pytest.fail('invalid input'))
    with pytest.raises(HTTPException) as failure:
        api.retained_macro_for_user(original[0], 'member', original[3], _outcome_request=expected)
    assert failure.value.status_code == 400


def test_entitlement_denial_precedes_outcome_lookup(original, monkeypatch):
    expected = request_for(call(original))
    monkeypatch.setattr(outcome, 'discover_registered_outcome_use', lambda *a, **k: pytest.fail('denied site'))
    with pytest.raises(HTTPException) as failure:
        api.retained_macro_for_user(original[0], 'not-member', original[3], _outcome_request=expected)
    assert failure.value.status_code == 403


def test_genuine_native_attachment_and_descriptor_share_the_original_selection(native_use, corpus, monkeypatch):
    _, _, prepare = native_use
    cap = prepare()
    descriptor = outcome.disclose_registered_outcome_use(cap)
    expected = request_for(descriptor, lens='later_observed')
    expected['outcome_cutoff'] = descriptor['outcome_cutoff']
    expected['outcome_use_identity'] = descriptor['outcome_use_identity']
    # Existing fixture authenticates private roles and source owners separately;
    # transport receives an actual sealed use, never a JSON substitute.
    monkeypatch.setattr(outcome, 'discover_registered_outcome_use', lambda *a, **k: (cap, descriptor))
    value = api._retained_outcome_result(corpus[2], Policy(), expected)
    assert value['available'] is True
    assert value['descriptor'] == descriptor
    assert value['attachment']['selection_sha256'] == expected['selection_sha256']
    assert value['attachment']['rows'][0]['status'] == 'observed'
    monkeypatch.setattr(outcome, 'disclose_registered_outcome_use', lambda *_: {**descriptor, 'lens': 'then_known'})
    with pytest.raises(HTTPException) as failure:
        api._retained_outcome_result(corpus[2], Policy(), expected)
    assert failure.value.status_code == 403
