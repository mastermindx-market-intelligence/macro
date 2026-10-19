"""Root-sealed adapter tests with explicit synthetic file-owner/OS-UID seams.

No real root grant/policy or OS identity is created; secure-reader filesystem
checks run on fixture-owned files, while adapter tests simulate root custody.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import os
import json
from unittest.mock import Mock
import pytest
from engine.research_intelligence import comparison_policy as p
from engine.research_intelligence import comparison_qualification as q
from engine.research_intelligence.store import _canonical_json_bytes
from engine.research_vault.comparison_runtime import build_comparison_owners
from tests.test_research_vault_comparison import configured, prepare, compare, CTX
from tests.test_research_comparison_qualification import proposal, pair_request

NOW = 1790985600


def policy_for(record):
    ref = hashlib.sha256(_canonical_json_bytes(record)).hexdigest()
    return {'schema': p.SCHEMA, 'policy_id': p.POLICY_ID,
            'authorization_provenance': 'synthetic authenticated operator assessment, not production',
            'entries': [{'qualification_sha256': ref,
                         'adjudicator_id': record['review']['adjudicator_id'],
                         'review_sha256': hashlib.sha256(_canonical_json_bytes(record['review'])).hexdigest(),
                         'audience': 'brain_pro', 'expires_at': NOW + 3600}]}


@pytest.fixture
def sealed(configured, tmp_path, monkeypatch):
    draft = proposal(configured); record = deepcopy(draft)
    record['review']['adjudicator_id'] = 'actual-synthetic-adjudicator'
    policy = policy_for(record); path = tmp_path/'policy.json'
    path.write_bytes(_canonical_json_bytes(policy)); path.chmod(0o600)
    original = p._read_policy_bytes
    def fixture_root_file(path, *, expected_owner_uid):
        assert expected_owner_uid == 0  # production adapter always demands root
        return original(path, expected_owner_uid=os.getuid())
    monkeypatch.setattr(p, '_read_policy_bytes', fixture_root_file)
    owner = p.SealedQualificationPolicy(str(path), clock=lambda: NOW)
    return owner, path, policy, draft, record


def test_concrete_root_policy_authoring_and_default_resolver_round_trip(sealed, configured, tmp_path, monkeypatch):
    from engine.research_vault.r2_store import LocalStore
    from engine.research_vault import view_ratelimit
    owner, _, policy, draft, record = sealed
    monkeypatch.setattr(p.os, 'geteuid', lambda: 0)  # explicit synthetic operator, no OS grant
    monkeypatch.setattr(view_ratelimit, 'preflight_many', lambda *a, **k: True, raising=False)
    monkeypatch.setattr(view_ratelimit, 'commit_many', lambda *a, **k: True, raising=False)
    store = LocalStore(tmp_path/'private')
    ref = q.publish_qualification(store, draft, actor=p.root_operator_context(), authority=owner.authority())
    assert ref == policy['entries'][0]['qualification_sha256']
    service = configured[0]
    service._comparison_owners = build_comparison_owners(store, authority=owner.authority())
    prepared = prepare(service)
    assert prepared['basis_options'][0]['basis_ref'] == ref
    assert compare(service, pair_request(prepared))['state'] == 'AVAILABLE'


def test_os_identity_and_exact_content_not_author_string_authorize_write(sealed, monkeypatch):
    owner, _, _, draft, _ = sealed
    monkeypatch.setattr(p.os, 'geteuid', lambda: 0)
    assert owner.authorize_write({'adjudicator_id': 'actual-synthetic-adjudicator'}, draft) is None
    actor = p.root_operator_context()
    changed = deepcopy(draft); changed['review']['provenance'] = 'unreviewed substitution'
    assert owner.authorize_write(actor, changed) is None
    assert owner.authorize_write(actor, draft) == 'actual-synthetic-adjudicator'
    monkeypatch.setattr(p.os, 'geteuid', lambda: 986)
    assert owner.authorize_write(actor, draft) is None
    with pytest.raises(p.PolicyRefused): p.root_operator_context()


@pytest.mark.parametrize('kind', ['principal', 'tier', 'scope', 'surface', 'mapping'])
def test_existing_caller_admission_cannot_be_replaced_by_policy(sealed, kind):
    owner, _, policy, _, record = sealed
    ctx = CTX
    if kind == 'principal': ctx = replace(CTX, entitlement='anonymous', principal_id=None)
    if kind == 'tier': ctx = replace(CTX, entitlement='preview')
    if kind == 'scope': ctx = replace(CTX, scopes=frozenset())
    if kind == 'surface': ctx = replace(CTX, surface='mcp')
    if kind == 'mapping': ctx = dict(CTX)
    assert owner.authorize_read(ctx, record, policy['entries'][0]['qualification_sha256']) is False


@pytest.mark.parametrize('mutation', ['expired', 'bool_expiry', 'wrong_policy', 'unknown', 'duplicate_ref', 'wrong_author', 'wrong_review', 'wrong_ref', 'wrong_audience'])
def test_policy_closed_scope_content_provenance_and_expiry(sealed, mutation):
    owner, path, policy, _, record = sealed
    ref = policy['entries'][0]['qualification_sha256']; e = policy['entries'][0]
    if mutation == 'expired': e['expires_at'] = NOW
    elif mutation == 'bool_expiry': e['expires_at'] = True
    elif mutation == 'wrong_policy': policy['policy_id'] = 'unrelated-mcp-grant'
    elif mutation == 'unknown': policy['accepted'] = True
    elif mutation == 'duplicate_ref': policy['entries'].append(deepcopy(e))
    elif mutation == 'wrong_author': e['adjudicator_id'] = 'forged-author'
    elif mutation == 'wrong_review': e['review_sha256'] = 'f' * 64
    elif mutation == 'wrong_ref': e['qualification_sha256'] = 'f' * 64
    elif mutation == 'wrong_audience': e['audience'] = 'mcp'
    path.write_bytes(_canonical_json_bytes(policy))
    assert owner.authorize_read(CTX, record, ref) is False


def test_policy_reload_revocation_and_optional_byte_pin(sealed):
    owner, path, policy, _, record = sealed
    ref = policy['entries'][0]['qualification_sha256']
    assert owner.authorize_read(CTX, record, ref) is True
    pinned = p.SealedQualificationPolicy(str(path), clock=lambda: NOW, expected_sha256='f'*64)
    assert pinned.authorize_read(CTX, record, ref) is False
    policy['entries'][0]['expires_at'] = NOW
    path.write_bytes(_canonical_json_bytes(policy))
    assert owner.authorize_read(CTX, record, ref) is False
    path.unlink()
    assert owner.authorize_read(CTX, record, ref) is False


@pytest.mark.parametrize('raw', [b'{"schema":1,"schema":2}', b'{"value":NaN}', b'[]', b'{}\n{}', b'x'*(p.MAX_BYTES+1)])
def test_untrusted_policy_serialization_refuses(raw):
    with pytest.raises(Exception): p.parse_policy(raw, now=NOW)


def test_secure_file_reader_owner_mode_symlink_hardlink_and_bound(tmp_path):
    path = tmp_path/'grant'; path.write_bytes(b'{}'); path.chmod(0o600)
    assert p._read_policy_bytes(str(path), expected_owner_uid=os.getuid()) == b'{}'
    with pytest.raises(p.PolicyRefused): p._read_policy_bytes(str(path), expected_owner_uid=os.getuid()+1)
    path.chmod(0o622)
    with pytest.raises(p.PolicyRefused): p._read_policy_bytes(str(path), expected_owner_uid=os.getuid())
    path.chmod(0o600); link = tmp_path/'symlink'; link.symlink_to(path)
    with pytest.raises(p.PolicyRefused): p._read_policy_bytes(str(link), expected_owner_uid=os.getuid())
    hard = tmp_path/'hard'; os.link(path, hard)
    with pytest.raises(p.PolicyRefused): p._read_policy_bytes(str(path), expected_owner_uid=os.getuid())
    hard.unlink(); path.write_bytes(b'x'*(p.MAX_BYTES+1))
    with pytest.raises(p.PolicyRefused): p._read_policy_bytes(str(path), expected_owner_uid=os.getuid())


def test_default_constructor_binds_real_policy_without_io(monkeypatch):
    from engine.research_vault.read_runtime import build_read_service
    reader = Mock(side_effect=AssertionError('construction must not open policy'))
    monkeypatch.setattr(p, '_read_policy_bytes', reader)
    store = Mock()
    service = build_read_service(catalog_store=store, corpus_connection=lambda: None)
    assert callable(service._comparison_owners.pair)
    assert reader.mock_calls == [] and store.mock_calls == []


def test_explicit_revoked_decision_is_not_read_admission(sealed):
    owner, path, _, _, record = sealed
    record['state'] = 'REVOKED'
    policy = policy_for(record)
    path.write_bytes(_canonical_json_bytes(policy))
    assert owner.authorize_read(CTX, record, policy['entries'][0]['qualification_sha256']) is False


def test_default_factory_uses_concrete_policy_for_actual_pair(sealed, configured, monkeypatch):
    """Default composition round trip, not a hand-injected admission callback."""
    from engine.research_vault.read_runtime import build_read_service
    from engine.research_vault import view_ratelimit
    import time
    owner, path, policy, draft, record = sealed
    policy['entries'][0]['expires_at'] = int(time.time()) + 3600
    path.write_bytes(_canonical_json_bytes(policy))
    fixture_reader = p._read_policy_bytes
    def installed_fixture_path(requested, *, expected_owner_uid):
        assert requested in (p.DEFAULT_PATH, str(path))
        return fixture_reader(str(path), expected_owner_uid=expected_owner_uid)
    monkeypatch.setattr(p, '_read_policy_bytes', installed_fixture_path)
    monkeypatch.setattr(p.os, 'geteuid', lambda: 0)  # simulated operator only
    monkeypatch.setattr(view_ratelimit, 'preflight_many', lambda *a, **k: True, raising=False)
    monkeypatch.setattr(view_ratelimit, 'commit_many', lambda *a, **k: True, raising=False)
    original = configured[0]
    q.publish_qualification(original._catalog_store, draft, actor=p.root_operator_context(), authority=owner.authority())
    service = build_read_service(catalog_store=original._catalog_store,
        corpus_connection=lambda: None, preview_selector=lambda _: [],
        extracted_text_loader=original._extracted_text_loader,
        source_digest_reader=original._source_digest_reader,
        rio_reader=original._rio_reader, clock=original._clock)
    result = prepare(service)
    assert result['basis_state'] == 'QUALIFIED'
    assert compare(service, pair_request(result))['state'] == 'AVAILABLE'
