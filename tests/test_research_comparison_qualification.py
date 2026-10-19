"""Synthetic trusted-adjudication fixtures; no production semantic acceptance."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from unittest.mock import Mock
import pytest

from engine.research_intelligence import comparison_qualification as q
from engine.research_intelligence.store import ResearchIntelligenceConflict, ResearchIntelligenceEffectUnknown
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.comparison_runtime import build_comparison_owners
from tests.test_research_vault_comparison import configured, prepare, compare, CTX, BASIS

ACTOR = object()


def proposal(configured):
    _, _, records, stored, _, _ = configured
    return {"schema": q.SCHEMA, "state": "QUALIFIED",
        "legs": [{"report_id": rid, "source_pdf_sha256": records[rid]["source_pdf_sha256"],
                  "extracted_text_sha256": records[rid]["extracted_text_sha256"],
                  "rio_artifact_sha256": stored[rid].artifact_sha256, "claim_index": 0,
                  "published_at": f"2026-10-0{i+1}T00:00:00Z"}
                 for i, rid in enumerate(("fixture-left", "fixture-right"))],
        "bases": [dict(BASIS), dict(BASIS)],
        "subjects": [{"kind": "source_topic", "subject": "demand", "provenance": "synthetic independently assessed source topic"} for _ in range(2)],
        "families": ["", ""], "revision": None,
        "review": {"assessed_at": "2026-10-03T00:00:00Z", "method": "synthetic-test-review.v1", "provenance": "synthetic test only; not real report acceptance"}}


@pytest.fixture
def admitted(configured, tmp_path, monkeypatch):
    from engine.research_vault import view_ratelimit as meter
    monkeypatch.setattr(meter, 'preflight_many', lambda *a, **k: True, raising=False)
    commits = []
    monkeypatch.setattr(meter, 'commit_many', lambda uid, ids, **k: commits.append((uid, ids)) is None, raising=False)
    store = LocalStore(tmp_path/'qualification')
    allowed = set()
    authority = q.QualificationAuthority(
        lambda actor, draft: 'test-adjudicator' if actor is ACTOR else None,
        lambda caller, record, ref: caller.principal_id == 'member' and ref in allowed)
    draft = proposal(configured)
    ref = q.publish_qualification(store, draft, actor=ACTOR, authority=authority)
    allowed.add(ref)
    service = configured[0]
    service._comparison_owners = build_comparison_owners(store, authority=authority)
    return service, store, authority, draft, ref, allowed, commits


def pair_request(prepared):
    return {'action': 'compare', **prepared['basis_options'][0]}


def test_native_discovery_round_trip_and_shared_meter(admitted):
    service, _, _, _, ref, _, commits = admitted
    p = prepare(service)
    assert p['state'] == 'INPUTS_ONLY' and p['basis_state'] == 'QUALIFIED'
    assert len(p['basis_options']) == 1 and p['basis_options'][0]['basis_ref'] == ref
    result = compare(service, pair_request(p))
    assert result['state'] == 'AVAILABLE'
    assert result['comparison']['basis_provenance'].startswith('synthetic')
    assert commits == [('member', ('fixture-left', 'fixture-right'))] * 2


def test_record_author_flag_and_grounding_are_not_admission(admitted):
    service, store, authority, draft, ref, allowed, commits = admitted
    allowed.clear()
    assert prepare(service)['reason'] == 'SEMANTIC_UNQUALIFIED'
    assert commits == []
    service._comparison_owners = build_comparison_owners(store)
    assert prepare(service)['reason'] == 'SEMANTIC_UNQUALIFIED'
    forged = deepcopy(draft); forged['review']['adjudicator_id'] = 'test-adjudicator'
    with pytest.raises(ValueError): q.publish_qualification(store, forged, actor=ACTOR, authority=authority)
    with pytest.raises(ValueError): q.publish_qualification(store, draft, actor='test-adjudicator', authority=authority)


@pytest.mark.parametrize('mutation', ['reversed', 'pdf', 'text', 'artifact', 'publication'])
def test_exact_ordered_source_and_publication_binding(admitted, mutation):
    service, store, authority, draft, ref, allowed, commits = admitted
    legs = deepcopy(draft['legs'])
    if mutation == 'reversed': legs.reverse()
    elif mutation == 'publication': legs[1]['published_at'] = '2026-10-04T00:00:00Z'
    else:
        key = {'pdf': 'source_pdf_sha256', 'text': 'extracted_text_sha256', 'artifact': 'rio_artifact_sha256'}[mutation]
        legs[1][key] = 'f' * 64
    assert q.load_qualification(store, legs, caller=CTX, authority=authority) is None
    assert commits == []


def test_claim_scope_discovery_does_not_bless_other_claims(admitted):
    service, store, authority, draft, ref, allowed, commits = admitted
    p = prepare(service); req = pair_request(p); req['left']['claim_index'] = 1
    assert compare(service, req)['state'] == 'UNAVAILABLE'
    assert len(commits) == 1


def test_revocation_and_stale_ref_cannot_replay_admission(admitted):
    service, store, authority, draft, ref, allowed, commits = admitted
    req = pair_request(prepare(service)); commits.clear()
    draft['state'] = 'REVOKED'
    revoked = q.publish_qualification(store, draft, actor=ACTOR, authority=authority, expected_ref=ref)
    allowed.add(revoked)
    assert prepare(service)['reason'] == 'SEMANTIC_UNQUALIFIED'
    assert compare(service, req)['state'] == 'UNAVAILABLE'
    assert commits == []
    with pytest.raises(ResearchIntelligenceConflict):
        q.publish_qualification(store, draft, actor=ACTOR, authority=authority, expected_ref=ref)


def test_late_revocation_after_basis_resolution_exposes_neither_leg(admitted):
    service, store, authority, draft, ref, allowed, commits = admitted
    req = pair_request(prepare(service)); commits.clear()
    owners = service._comparison_owners
    def race(ctx, basis_ref, legs):
        answer = owners.basis(ctx, basis_ref, legs)
        draft['state'] = 'REVOKED'
        q.publish_qualification(store, draft, actor=ACTOR, authority=authority, expected_ref=ref)
        return answer
    service._comparison_owners = replace(owners, basis=race)
    result = compare(service, req)
    assert result['reason'] == 'QUALIFICATION_CHANGED'
    assert 'left' not in result and commits == []


@pytest.mark.parametrize('mutation', ['axis_missing', 'claim_bool', 'current_alias', 'unknown', 'forged_status'])
def test_closed_record_does_not_infer_missing_basis(admitted, mutation):
    _, store, authority, draft, ref, _, _ = admitted
    draft = deepcopy(draft)
    if mutation == 'axis_missing': del draft['bases'][0]['currency']
    elif mutation == 'claim_bool': draft['legs'][0]['claim_index'] = True
    elif mutation == 'unknown': draft['accepted'] = True
    elif mutation == 'forged_status': draft['state'] = 'accepted'
    else:
        draft['bases'][0]['subject'] = 'SEC:US-XNYS-MMC'
        draft['subjects'][0] = {'kind': 'historical_security', 'security_id': 'SEC:US-XNYS-MMC', 'alias_vendor': 'store', 'resolution_state': 'RESOLVED', 'resolution_date': '2026-10-01', 'decision_at': '2026-10-03T00:00:00Z', 'provenance': 'synthetic'}
    with pytest.raises(ValueError):
        q.publish_qualification(store, draft, actor=ACTOR, authority=authority, expected_ref=ref)


def test_tampered_immutable_record_cannot_be_read(admitted):
    _, store, authority, draft, ref, _, _ = admitted
    store.put_bytes(q.object_key(ref), b'{}')
    with pytest.raises(ValueError): q.load_qualification(store, draft['legs'], caller=CTX, authority=authority)


def test_lost_ack_reconciles_same_exact_cas_without_replay(configured, tmp_path):
    store = LocalStore(tmp_path/'lost-ack')
    authority = q.QualificationAuthority(lambda actor, draft: 'synthetic-author', lambda *args: False)
    original = store.put_bytes_strict_conditional
    calls = []
    def lost(key, data, **kwargs):
        calls.append(key); answer = original(key, data, **kwargs)
        if '/pairs/' in key: raise OSError('synthetic lost ack')
        return answer
    store.put_bytes_strict_conditional = lost
    draft = proposal(configured)
    ref = q.publish_qualification(store, draft, actor=ACTOR, authority=authority)
    assert len([k for k in calls if '/pairs/' in k]) == 1 and len(ref) == 64


def test_default_factory_composes_without_trusted_true_or_write(configured):
    from engine.research_vault.read_runtime import build_read_service
    source = configured[0]
    no_write = Mock()
    service = build_read_service(catalog_store=no_write, corpus_connection=lambda: None)
    assert callable(service._comparison_owners.pair)
    assert service._comparison_owners.semantic is None
    assert no_write.mock_calls == []


def test_different_principal_cannot_reuse_discovered_ref(admitted):
    service, _, _, _, _, _, commits = admitted
    req = pair_request(prepare(service)); commits.clear()
    denied = service.comparison_view(caller_context=replace(CTX, principal_id="another-member"), request=req)
    assert denied["reason"] == "SEMANTIC_UNQUALIFIED" and commits == []


def test_admission_callback_cannot_hide_pointer_revocation(admitted):
    _, store, authority, draft, ref, allowed, _ = admitted
    def revoke(caller, record, content_ref):
        draft["state"] = "REVOKED"
        q.publish_qualification(store, draft, actor=ACTOR, authority=authority, expected_ref=ref)
        return True
    racing = replace(authority, authorize_read=revoke)
    assert q.load_qualification(store, draft["legs"], caller=CTX, authority=racing) is None


def test_cas_unknown_is_not_replayed(configured, tmp_path):
    store = LocalStore(tmp_path/"unknown")
    authority = q.QualificationAuthority(lambda *_: "synthetic-author", lambda *_: False)
    original_get = store.get_bytes_strict_bounded_versioned
    original_put = store.put_bytes_strict_conditional
    attempted = []
    def put(key, data, **kwargs):
        if "/pairs/" in key:
            attempted.append(key)
            raise OSError("synthetic unobserved outcome")
        return original_put(key, data, **kwargs)
    def get(key, limit):
        if attempted: raise OSError("synthetic status unavailable")
        return original_get(key, limit)
    store.put_bytes_strict_conditional = put
    store.get_bytes_strict_bounded_versioned = get
    with pytest.raises(ResearchIntelligenceEffectUnknown):
        q.publish_qualification(store, proposal(configured), actor=ACTOR, authority=authority)
    assert len(attempted) == 1


def test_native_discovery_global_budget_refuses_before_charge(admitted, monkeypatch):
    service, _, _, _, _, _, commits = admitted
    from engine.research_vault import comparison
    monkeypatch.setattr(comparison, "MAX_CHARS", 100)
    result = prepare(service)
    assert result["state"] == "UNAVAILABLE" and "basis_options" not in result and commits == []


def test_native_write_capability_refuses_before_any_effect(configured, tmp_path):
    store = LocalStore(tmp_path/"no-cas")
    store.validate_strict_conditional_write_capability = Mock(side_effect=PermissionError("synthetic denied CAS"))
    store.put_bytes_strict_conditional = Mock()
    authority = q.QualificationAuthority(lambda *_: "synthetic-author", lambda *_: False)
    with pytest.raises(PermissionError):
        q.publish_qualification(store, proposal(configured), actor=ACTOR, authority=authority)
    store.put_bytes_strict_conditional.assert_not_called()


def test_last_qualification_io_cannot_return_old_source_body(admitted, configured):
    service, _, _, _, _, _, commits = admitted
    owners = service._comparison_owners
    calls = []
    def late(ctx, legs):
        answer = owners.pair(ctx, legs); calls.append(1)
        if len(calls) == 3:
            configured[2]["fixture-right"]["source_pdf_sha256"] = "f" * 64
        return answer
    service._comparison_owners = replace(owners, pair=late)
    result = prepare(service)
    assert result["state"] == "UNAVAILABLE" and "left" not in result
    assert commits == []


def test_real_pair_read_composition_needs_no_store_writer(admitted):
    service, store, authority, _, _, _, _ = admitted
    class ReadOnly:
        def get_bytes_strict_bounded(self, key, bound):
            return store.get_bytes_strict_bounded(key, bound)
    service._comparison_owners = build_comparison_owners(ReadOnly(), authority=authority)
    request = pair_request(prepare(service))
    assert compare(service, request)['state'] == 'AVAILABLE'
