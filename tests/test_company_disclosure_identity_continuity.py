"""C01 identity provenance continuity: one explicit protected policy, never a
generic relaxation. Provenance-only refresh between requests requalifies; any
semantic change, split generation, malformed receipt or in-operation drift
refuses without artifact Store writes or source-body access."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import hashlib
import json

import pytest

from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import issuer_disclosure_publication as p
from engine.company_intelligence.issuer_disclosure_selection import read_issuer_selection
from engine.research_vault.r2_store import LocalStore

PRODUCED = (b'dataset_id: company_intelligence.issuer_disclosure_generations\n'
            b'    layer: L3\n    status: PROPOSED',
            b'dataset_id: company_intelligence.issuer_disclosure_generations\n'
            b'    layer: L3\n    status: PRODUCED')


def load_spec():
    return json.loads(Path(o.SPEC_PATH).read_bytes())


def refresh(identities, commit='b'*40):
    """Provenance-only drift: one new shared source generation, semantics equal."""
    out = deepcopy(identities)
    sources = {name: {'sha256': hashlib.sha256(f'{commit}:{name}'.encode()).hexdigest(),
                      'byte_length': length}
               for name, length in (('security_master', 81000), ('vendor_aliases', 52000),
                                    ('issuer_master', 45000))}
    for party in out.values():
        party['source_commit'] = commit
        party['sources'] = deepcopy(sources)
    return out


def qualify(spec, identities, ruling_raw, registry_raw, code='a'*40):
    return o.qualify_records(code, n._canonical(spec), ruling_raw, registry_raw, identities)


class FixtureSource:
    def __init__(self, snapshot):
        self.value = snapshot
        self.calls = 0
        self.action = None

    def snapshot(self):
        self.calls += 1
        if self.action:
            self.action()
        return self.value

    def accepts_revision(self, revision):
        return revision == self.value.code_version


@pytest.fixture
def records():
    return (load_spec(), Path(o.RULING_PATH).read_bytes(), Path(o.REGISTRY_PATH).read_bytes())


@pytest.fixture
def flow(tmp_path):
    """A v2 qualified generation published against refreshed current receipts."""
    spec = load_spec()
    ruling = json.loads(Path(o.RULING_PATH).read_bytes())
    registry = Path(o.REGISTRY_PATH).read_bytes().replace(*PRODUCED)
    body = b'C01 identity continuity synthetic retained source.'
    ruling['source'].update(sha256=o.digest(body), byte_length=len(body))
    rraw = n._canonical(ruling)
    spec['ruling_reference'] = o.object_ref(rraw)
    spec['edition'].update(source_sha256=o.digest(body), source_byte_length=len(body))
    spec['fact'].update(edition=n.validate_edition(spec['edition']).payload(),
        span=dict(start_byte=0, end_byte=len(body), text_sha256=o.digest(body)))
    spec['correction_decision'].update(edition=n.validate_edition(spec['edition']).payload(),
                                      fact=n.validate_fact(spec['fact']).payload())
    observed = refresh(spec['identities'])
    snapshot = o.qualify_records('a'*40, n._canonical(spec), rraw, registry, observed)
    source = FixtureSource(snapshot)
    state, artifacts = LocalStore(tmp_path/'state'), LocalStore(tmp_path/'artifacts')
    inputs = tmp_path/'input'; inputs.mkdir(); (inputs/'source.html').write_bytes(body)
    def factory(snap):
        return p.RetainedFileSource(snap, inputs, 'source.html')
    return {'source': source, 'state': state, 'artifacts': artifacts, 'factory': factory,
            'rraw': rraw, 'registry': registry, 'spec': spec, 'observed': observed}


def test_policy_admits_provenance_only_refresh_with_stable_fact_identity(records):
    spec, rraw, registry = records
    recorded = qualify(spec, spec['identities'], rraw, registry)
    fresh = qualify(spec, refresh(spec['identities']), rraw, registry)
    # The native fact decision and all protected bindings never move.
    assert recorded.spec['fact'] == fresh.spec['fact'] == spec['fact']
    assert n.validate_fact(spec['fact']).payload() == spec['correction_decision']['fact']
    assert recorded.bindings == fresh.bindings
    assert recorded.code_version == fresh.code_version
    # Only provenance drifted; semantics are identical for both parties.
    for symbol in o.IDENTITY_PARTIES:
        before = recorded.current_identities[symbol]
        after = fresh.current_identities[symbol]
        assert all(before[k] == after[k] for k in o.SEMANTIC_IDENTITY_FIELDS)
        assert after['source_commit'] != before['source_commit']
    assert fresh.current_identities_raw == n._canonical(refresh(spec['identities']))
    assert fresh.identity_binding != recorded.identity_binding


def test_legacy_exact_specification_still_refuses_the_same_refresh(records):
    spec, rraw, registry = records
    legacy = deepcopy(spec)
    del legacy['identity_continuity']
    legacy['schema'] = o.OWNER_SCHEMA_V1
    with pytest.raises(n.DisclosureError, match='CURRENT_IDENTITY_CHANGED'):
        qualify(legacy, refresh(spec['identities']), rraw, registry)
    exact = qualify(legacy, spec['identities'], rraw, registry)
    assert exact.current_identities == spec['identities']


@pytest.mark.parametrize('mutate', [
    lambda r: r['MU'].pop('evidenced_cik'),
    lambda r: r['NVDA'].update(extra='unknown'),
    lambda r: r['MU'].update(schema='company_intelligence.current_issuer_identity/v2'),
    lambda r: r['MU'].update(identity_mode='historical'),
    lambda r: r['MU'].update(source_commit='not-a-commit'),
    lambda r: r['MU']['sources']['security_master'].update(sha256='0'*63),
    lambda r: r['NVDA']['sources']['issuer_master'].update(byte_length=-1),
    lambda r: r['MU']['sources']['vendor_aliases'].update(byte_length=True),
    lambda r: r['MU']['sources']['issuer_master'].update(byte_length=0),
    lambda r: r['MU']['sources'].pop('issuer_master'),
    lambda r: r['MU']['sources'].update(other={'sha256': '0'*64, 'byte_length': 1}),
    lambda r: r.pop('NVDA'),
    lambda r: r.update(GOOGL=r['MU']),
    lambda r: r['MU'].update(evidenced_cik='12345'),
    lambda r: r['NVDA'].update(evidence_source='manual'),
    lambda r: r['NVDA'].update(evidence_snapshot='2026-13-99'),
])
def test_malformed_or_unknown_receipt_shape_refuses_before_content(records, mutate):
    spec, rraw, registry = records
    receipts = refresh(spec['identities'])
    mutate(receipts)
    with pytest.raises(n.DisclosureError):
        qualify(spec, receipts, rraw, registry)


@pytest.mark.parametrize('mutate', [
    lambda r: r['MU'].update(evidenced_cik='9999999999'),
    lambda r: r['NVDA'].update(issuer_id='ISS:US-XNAS-NVDA-ALT'),
    lambda r: r['MU'].update(evidence_snapshot='2026-09-01'),
    lambda r: r['MU'].update(evidence_source='manual'),
])
def test_policy_never_admits_semantic_or_party_drift(records, mutate):
    spec, rraw, registry = records
    receipts = refresh(spec['identities'])
    mutate(receipts)
    with pytest.raises(n.DisclosureError, match='CURRENT_IDENTITY_CHANGED|IDENTITY_BINDING_MISMATCH'):
        qualify(spec, receipts, rraw, registry)


def test_parties_must_share_one_current_source_generation(records):
    spec, rraw, registry = records
    split = refresh(spec['identities'])
    split['MU']['source_commit'] = 'c'*40
    with pytest.raises(n.DisclosureError, match='IDENTITY_GENERATION_SPLIT'):
        qualify(spec, split, rraw, registry)
    mixed = refresh(spec['identities'])
    mixed['MU']['sources']['security_master']['sha256'] = 'd'*64
    with pytest.raises(n.DisclosureError, match='IDENTITY_GENERATION_SPLIT'):
        qualify(spec, mixed, rraw, registry)


def test_recorded_receipt_tamper_breaks_the_fact_digest_binding(records):
    spec, rraw, registry = records
    receipts = refresh(spec['identities'])
    moved = deepcopy(spec)
    moved['identities']['MU']['source_commit'] = 'e'*40
    with pytest.raises(n.DisclosureError, match='IDENTITY_BINDING_MISMATCH'):
        qualify(moved, receipts, rraw, registry)
    flipped = deepcopy(spec)
    flipped['fact']['subject_identity'] = 'f'*64
    with pytest.raises(n.DisclosureError, match='IDENTITY_BINDING_MISMATCH'):
        qualify(flipped, receipts, rraw, registry)


def test_continuity_policy_is_literal_closed_and_version_bound(records):
    spec, rraw, registry = records
    receipts = refresh(spec['identities'])
    for mutate in [lambda p: p.update(policy='anything_goes'),
                   lambda p: p.update(schema='company_intelligence.identity_continuity_policy/v2'),
                   lambda p: p.update(extra=True),
                   lambda p: p.pop('semantic_fields'),
                   lambda p: p.update(semantic_fields=['schema', 'identity_mode']),
                   lambda p: p.update(provenance_fields=['source_commit', 'sources', 'evidence_snapshot']),
                   lambda p: p.update(parties=['MU'])]:
        variant = deepcopy(spec)
        mutate(variant['identity_continuity'])
        with pytest.raises(n.DisclosureError, match='IDENTITY_CONTINUITY_POLICY_INVALID'):
            qualify(variant, receipts, rraw, registry)
    hybrid = deepcopy(spec)
    hybrid['schema'] = o.OWNER_SCHEMA_V1
    with pytest.raises(n.DisclosureError, match='OWNER_SPEC_INVALID'):
        qualify(hybrid, receipts, rraw, registry)
    bare = deepcopy(spec)
    del bare['identity_continuity']
    bare['schema'] = o.OWNER_SCHEMA_V2
    with pytest.raises(n.DisclosureError, match='OWNER_SPEC_INVALID'):
        qualify(bare, receipts, rraw, registry)


@pytest.mark.parametrize('mutate', [
    lambda s, r: r['permitted_use'].update(purpose='public'),
    lambda s, r: s['temporal_decision'].update(historical_admitted=True),
    lambda s, r: s['correction_decision'].update(status='retracted'),
    lambda s, r: s['semantic_review'].update(decision='refused'),
])
def test_protected_decision_controls_survive_the_v2_policy(records, mutate):
    spec, rraw, registry = records
    ruling = json.loads(rraw)
    mutate(spec, ruling)
    changed = n._canonical(ruling)
    spec['ruling_reference'] = o.object_ref(changed)
    with pytest.raises(n.DisclosureError):
        qualify(spec, refresh(spec['identities']), changed, registry)


def test_snapshot_freezes_observed_bytes_against_caller_mutation(records):
    spec, rraw, registry = records
    receipts = refresh(spec['identities'])
    snapshot = qualify(spec, receipts, rraw, registry)
    expected = o.digest(n._canonical(receipts))
    receipts['MU']['source_commit'] = 'f'*40
    receipts['NVDA']['evidenced_cik'] = '9999999999'
    receipts.clear()
    assert snapshot.current_identities['MU']['source_commit'] == 'b'*40
    assert o.digest(n._canonical(snapshot.current_identities)) == expected
    with pytest.raises(FrozenInstanceError):
        snapshot.current_identities_raw = b'{}'
    with pytest.raises(FrozenInstanceError):
        snapshot.code_version = '0'*40


def test_refreshed_generation_publishes_reads_and_selects_at_one_current_binding(flow):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    intent = p.prepare_publication(source, state, expected_current_version=None)
    result = p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)
    assert result['status'] == 'COMMITTED_OBSERVED'
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    read = o.ReadOnlyLocalObjects(artifacts.root)
    request = n.Request(source.value.spec['fact']['fact_id'], o.PURPOSE, o.AUDIENCE)
    response = n.read_disclosure(read, current, request)
    receipt = source.value.current_identities['MU']
    raw = n._canonical(receipt)
    # The selection binding is the exact current context receipt.
    selection = read_issuer_selection(current, current, lambda: read,
        response['fact']['subject_id'], purpose=o.PURPOSE, audience=o.AUDIENCE)
    assert selection['issuer_binding']['identity_snapshot_reference'] == {
        'schema': receipt['schema'], 'sha256': o.digest(raw), 'byte_length': len(raw)}
    # The native fact keeps the original immutable decision link.
    admitted = current.resolve(request)
    assert admitted.subject_binding.decision_revision == source.value.spec['fact']['subject_identity']
    assert (admitted.subject_binding.issuer_id, admitted.subject_binding.evidenced_cik) == \
        (receipt['issuer_id'], receipt['evidenced_cik'])
    assert admitted.subject_binding.snapshot_sha256 == o.digest(raw)
    assert admitted.identity_revision == source.value.identity_binding
    assert admitted.identity_revision != o.digest(n._canonical(source.value.spec['identities']))
    assert response['fact']['subject_id'] == 'ISS:US-XNAS-MU'


def test_refresh_between_requests_requalifies_and_old_admission_refuses(flow):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    intent = p.prepare_publication(source, state, expected_current_version=None)
    assert p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)['status'] == \
        'COMMITTED_OBSERVED'
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    read = o.ReadOnlyLocalObjects(artifacts.root)
    request = n.Request(source.value.spec['fact']['fact_id'], o.PURPOSE, o.AUDIENCE)
    first = current.resolve(request)
    later = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], flow['registry'],
                              refresh(flow['observed'], commit='c'*40))
    source.value = later  # provenance-only refresh between separate requests
    second = current.resolve(request)
    assert second.identity_revision != first.identity_revision
    assert second.subject_binding.decision_revision == first.subject_binding.decision_revision
    assert n.read_disclosure(read, current, request, expected_admission=second)['generation'] == \
        second.generation
    with pytest.raises(n.DisclosureError, match='ADMISSION_CHANGED'):
        n.read_disclosure(read, current, request, expected_admission=first)


@pytest.mark.parametrize('after', [3, 5])
def test_identity_drift_during_publication_refuses_before_any_store_write(flow, after):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    drifted = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], flow['registry'],
                                refresh(flow['observed'], commit='c'*40))
    def action():
        if source.calls >= after:
            source.value = drifted
            source.action = None
    source.action = action
    intent = p.prepare_publication(source, state, expected_current_version=None)
    with pytest.raises(n.DisclosureError):
        p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)
    assert not (state.root/o.CURRENT_KEY).exists()
    if after == 3:  # refused inside the first authority recheck: zero member writes
        assert not (artifacts.root/'company_intelligence').exists()


def test_drift_after_the_pointer_never_certifies_the_operation(flow):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    drifted = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], flow['registry'],
                                refresh(flow['observed'], commit='c'*40))
    def action():
        if (state.root/o.CURRENT_KEY).exists():
            source.value = drifted
            source.action = None
    source.action = action
    intent = p.prepare_publication(source, state, expected_current_version=None)
    with pytest.raises(n.DisclosureError, match='PUBLICATION_IDENTITY_CONTINUITY_BROKEN'):
        p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)
    # The CAS already happened, so nothing is certified: any later observation
    # must requalify under the fresh drifted binding, never the stale admission.
    source.action = None
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    request = n.Request(source.value.spec['fact']['fact_id'], o.PURPOSE, o.AUDIENCE)
    assert current.resolve(request).identity_revision == drifted.identity_binding


@pytest.mark.parametrize('route', ['read', 'selection'])
def test_drift_inside_one_request_refuses_but_between_requests_requalifies(flow, route):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    intent = p.prepare_publication(source, state, expected_current_version=None)
    assert p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)['status'] == \
        'COMMITTED_OBSERVED'
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    read = o.ReadOnlyLocalObjects(artifacts.root)
    request = n.Request(source.value.spec['fact']['fact_id'], o.PURPOSE, o.AUDIENCE)
    drifted = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], flow['registry'],
                                refresh(flow['observed'], commit='c'*40))
    def action():
        if source.calls >= 1:
            source.value = drifted
            source.action = None
    source.action = action  # drift lands before the next request's first snapshot
    if route == 'read':
        assert n.read_disclosure(read, current, request)['generation'] == current.resolve(request).generation
    else:
        issuer = source.value.spec['fact']['subject_id']
        assert read_issuer_selection(current, current, lambda: read, issuer,
                                     purpose=o.PURPOSE, audience=o.AUDIENCE)['selections']
    source.value = drifted
    source.action = None
    later = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], flow['registry'],
                              refresh(flow['observed'], commit='d'*40))
    source.calls = 0  # count only this request's snapshots
    def midread():
        if source.calls >= 2:  # first snapshot pre-drift, later snapshots drifted
            source.value = later
            source.action = None
    source.action = midread
    with pytest.raises(n.DisclosureError):
        if route == 'read':
            n.read_disclosure(read, current, request)
        else:
            read_issuer_selection(current, current, lambda: read,
                                  source.value.spec['fact']['subject_id'],
                                  purpose=o.PURPOSE, audience=o.AUDIENCE)


@pytest.mark.parametrize('field', ['semantic_fields', 'provenance_fields', 'parties'])
@pytest.mark.parametrize('value', [None, True, 7, 'not-a-list', {}])
def test_malformed_policy_field_type_is_a_sanitized_refusal(records, field, value):
    spec, rraw, registry = records
    spec['identity_continuity'][field] = value
    with pytest.raises(n.DisclosureError, match='IDENTITY_CONTINUITY_POLICY_INVALID'):
        qualify(spec, refresh(spec['identities']), rraw, registry)


@pytest.mark.parametrize('identities', [None, True, 7, 'MU', []])
def test_malformed_identity_container_is_a_sanitized_refusal(records, identities):
    spec, rraw, registry = records
    with pytest.raises(n.DisclosureError, match='CURRENT_IDENTITY_CHANGED'):
        qualify(spec, identities, rraw, registry)


def test_missing_owner_schema_is_a_sanitized_refusal(records):
    spec, rraw, registry = records
    del spec['schema']
    with pytest.raises(n.DisclosureError, match='OWNER_SPEC_INVALID'):
        qualify(spec, spec['identities'], rraw, registry)


@pytest.mark.parametrize('failure', ['identity_drift', 'readback_mismatch', 'domain_error', 'read_error'])
def test_post_pointer_failure_always_requires_reconciliation(flow, monkeypatch, failure):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    original_read = p.native.read_disclosure
    drifted = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], flow['registry'],
                               refresh(flow['observed'], commit='c'*40))
    def after_pointer(*args, **kwargs):
        if (state.root/o.CURRENT_KEY).exists():
            if failure == 'domain_error':
                raise n.DisclosureError('CURRENT_DECISION_CHANGED')
            if failure == 'read_error':
                raise OSError('private-path-detail-must-not-escape')
            if failure == 'identity_drift':
                source.value = drifted
            result = original_read(*args, **kwargs)
            if failure == 'readback_mismatch':
                result = {**result, 'generation': 'f'*64}
            return result
        return original_read(*args, **kwargs)
    monkeypatch.setattr(p.native, 'read_disclosure', after_pointer)
    intent = p.prepare_publication(source, state, expected_current_version=None)
    with pytest.raises(n.DisclosureError) as caught:
        p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)
    assert (state.root/o.CURRENT_KEY).exists()
    assert caught.value.effect_unknown is True
    assert caught.value.automatic_retry_permitted is False
    assert 'private-path-detail' not in str(caught.value)


@pytest.mark.parametrize('status', ['PROPOSED', 'PRODUCED'])
def test_publication_receipt_binds_actual_current_identity(flow, status):
    source, state, artifacts = flow['source'], flow['state'], flow['artifacts']
    registry = flow['registry'] if status == 'PRODUCED' else flow['registry'].replace(*PRODUCED[::-1])
    source.value = o.qualify_records('a'*40, source.value.spec_bytes, flow['rraw'], registry, flow['observed'])
    expected = source.value.identity_binding
    intent = p.prepare_publication(source, state, expected_current_version=None)
    result = p.publish_generation(source, state, artifacts, flow['factory'], intent=intent)
    assert result['identity_binding'] == expected
    assert len(expected) == 64
    assert result['intent'] == intent
    assert result['pointer_written'] is (status == 'PRODUCED')
    assert result['automatic_retry_permitted'] is False


@pytest.mark.parametrize('invalid_date', ['2026-13-99', '2026-02-30', '0000-00-00'])
def test_identity_receipt_rejects_impossible_calendar_dates(records, invalid_date):
    spec, _, _ = records
    receipt = deepcopy(spec['identities']['MU'])
    receipt['evidence_snapshot'] = invalid_date
    with pytest.raises(n.DisclosureError, match='IDENTITY_RECEIPT_INVALID'):
        o._validate_identity_receipt(receipt)
