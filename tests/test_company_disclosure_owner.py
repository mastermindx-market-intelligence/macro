"""Synthetic publication effects; real protected decisions are read-only inputs."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import os

import pytest

from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import issuer_disclosure_publication as p
from engine.company_intelligence.issuer_disclosure_selection import read_issuer_selection
from engine.research_vault.r2_store import LocalStore


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
def case(tmp_path):
    spec = json.loads(Path(o.SPEC_PATH).read_bytes())
    ruling = json.loads(Path(o.RULING_PATH).read_bytes())
    registry = Path(o.REGISTRY_PATH).read_bytes()
    registry = registry.replace(
        b'dataset_id: company_intelligence.issuer_disclosure_generations\n    layer: L3\n    status: PROPOSED',
        b'dataset_id: company_intelligence.issuer_disclosure_generations\n    layer: L3\n    status: PRODUCED')
    body = b'Synthetic retained source for native publication contract proof.'
    ruling['source'].update(sha256=o.digest(body), byte_length=len(body))
    rraw = n._canonical(ruling)
    spec['ruling_reference'] = o.object_ref(rraw)
    spec['edition'].update(source_sha256=o.digest(body), source_byte_length=len(body))
    spec['fact'].update(edition=n.validate_edition(spec['edition']).payload(),
        span=dict(start_byte=0, end_byte=len(body), text_sha256=o.digest(body)))
    spec['correction_decision'].update(edition=n.validate_edition(spec['edition']).payload(),
                                      fact=n.validate_fact(spec['fact']).payload())
    source = FixtureSource(o.qualify_records('a'*40, n._canonical(spec), rraw, registry, spec['identities']))
    state, artifacts = LocalStore(tmp_path/'state'), LocalStore(tmp_path/'artifacts')
    inputs = tmp_path/'input'; inputs.mkdir(); (inputs/'source.html').write_bytes(body)
    def factory(snapshot):
        return p.RetainedFileSource(snapshot, inputs, 'source.html')
    return source, state, artifacts, factory, rraw, registry


def publish(case):
    intent = p.prepare_publication(case[0], case[1], expected_current_version=None)
    return p.publish_generation(*case[:4], intent=intent)


def request(case, **changes):
    return n.Request(case[0].value.spec['fact']['fact_id'], changes.pop('purpose', o.PURPOSE),
                     changes.pop('audience', o.AUDIENCE), **changes)


def test_real_local_generation_read_and_selection_have_one_binding_without_writes(case):
    result = publish(case)
    assert result['status'] == 'COMMITTED_OBSERVED'
    assert result['native_result']['conditional_objects_observed'] == 4
    source, state, artifacts, *_ = case
    files = {str(p): p.read_bytes() for root in [state.root, artifacts.root]
             for p in root.rglob('*') if p.is_file()}
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    read = o.ReadOnlyLocalObjects(artifacts.root)
    response = n.read_disclosure(read, current, request(case))
    assert response['generation'] == result['generation']
    assert response['source_timing']['published_date'] == '2024-02-26'
    assert response['source_timing']['published_at'] is None
    selection = read_issuer_selection(current, current, lambda: read,
        response['fact']['subject_id'], purpose=o.PURPOSE, audience=o.AUDIENCE)
    assert selection['generation'] == response['generation']
    assert selection['selections'][0]['fact_reference'] == response['reference']
    assert selection['issuer_binding']['identity_snapshot_reference']['sha256'] == source.value.spec['fact']['subject_identity']
    assert files == {str(p): p.read_bytes() for root in [state.root, artifacts.root]
                     for p in root.rglob('*') if p.is_file()}
    assert not hasattr(read, 'put_bytes_strict_conditional')
    assert current.authorize_publication(request(case), current.resolve(request(case)).reference) is None


@pytest.mark.parametrize('change', ['ruling_hash', 'purpose', 'audience', 'source', 'claim',
    'identity', 'historical', 'correction', 'review', 'registry', 'clock'])
def test_owner_records_cannot_self_grant_or_substitute_inputs(case, change):
    source, _, _, _, rraw, registry = case
    spec = source.value.spec; ruling = json.loads(rraw); identities = deepcopy(spec['identities'])
    if change == 'ruling_hash': spec['ruling_reference']['sha256'] = '0'*64
    elif change in {'purpose','audience'}: ruling['permitted_use'][change] = 'other'
    elif change == 'source': ruling['source']['sha256'] = '0'*64
    elif change == 'claim': ruling['permitted_use']['product'] = 'different'
    elif change == 'identity': identities['MU']['source_commit'] = 'b'*40
    elif change == 'historical': spec['temporal_decision']['historical_admitted'] = True
    elif change == 'correction': spec['correction_decision']['status'] = 'retracted'
    elif change == 'review': spec['semantic_review']['decision'] = 'refused'
    elif change == 'registry': registry = registry.replace(b'owner: company-intelligence', b'owner: other')
    else: registry = registry.replace(b'computed_at: {dtype: RFC3339_UTC', b'wrong_clock: {dtype: RFC3339_UTC')
    changed = n._canonical(ruling)
    if change != 'ruling_hash': spec['ruling_reference'] = o.object_ref(changed)
    with pytest.raises(n.DisclosureError):
        o.qualify_records('a'*40, n._canonical(spec), changed, registry, identities)


def test_read_refuses_revoked_metadata_before_any_artifact_access(case):
    publish(case)
    source, state, *_ = case
    source.value = replace(source.value, ruling_revision='0'*64)
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    with pytest.raises(n.DisclosureError):
        n.preflight(current, request(case))


@pytest.mark.parametrize('route', ['fact', 'selection'])
def test_proposed_registry_never_becomes_adopted_by_private_pointer(case, route):
    source, state, _, _, ruling, _ = case
    spec = source.value.spec
    source.value = o.qualify_records('a'*40, n._canonical(spec), ruling,
                                    Path(o.REGISTRY_PATH).read_bytes(), spec['identities'])
    result = publish(case)
    assert result['status'] == 'MEMBERS_OBSERVED_NOT_ADOPTED'
    assert result['pointer_written'] is False and not (state.root/o.CURRENT_KEY).exists()
    # Even a privileged but erroneous pointer write cannot turn staged members
    # into a serving adoption while the protected registry still says PROPOSED.
    pointer = n._canonical({'schema': o.POINTER_SCHEMA, 'manifest': result['intent']['manifest_reference']})
    state.put_bytes_strict_conditional(o.CURRENT_KEY, pointer, expected_version=None)
    current = o.CurrentDisclosureOwner(case[0], o.ReadOnlyLocalObjects(case[1].root))
    with pytest.raises(n.DisclosureError, match='DATASET_NOT_PRODUCED'):
        if route == 'fact':
            current.resolve(request(case))
        else:
            current.resolve_issuer(case[0].value.spec['fact']['subject_id'], o.PURPOSE, o.AUDIENCE)


@pytest.mark.parametrize('changes', [dict(mode='historical',as_of='2026-10-10T00:00:00Z'),
                                    dict(purpose='public'), dict(audience='anonymous')])
def test_request_refusal_has_zero_metadata_or_source_io(case, changes):
    class NoMetadata:
        def __getattr__(self, key): pytest.fail('metadata access before closed request admission')
    source = case[0]; before = source.calls
    current = o.CurrentDisclosureOwner(source, NoMetadata())
    assert current.resolve(request(case, **changes)) is None
    assert source.calls == before


def test_retained_reader_refuses_wrong_binding_before_source_read(case):
    reader = case[3](case[0].value)
    reader.root = Path('/absent-should-not-be-opened')
    with pytest.raises(n.DisclosureError, match='RETAINED_SOURCE_BINDING_MISMATCH'):
        reader.read_source(disclosure_id='wrong')


def test_wrong_predecessor_stops_before_source_factory_or_writes(case):
    def forbidden(snapshot): pytest.fail('source factory before predecessor check')
    with pytest.raises(n.DisclosureError, match='PUBLICATION_PREDECESSOR_CHANGED'):
        p.prepare_publication(case[0], case[1], expected_current_version='stale')
    assert not list(case[1].root.iterdir()) and not list(case[2].root.iterdir())


@pytest.mark.parametrize('changed_at', ['member', 'manifest'])
def test_revocation_during_publication_never_promotes_pointer(case, changed_at):
    source, state, artifacts, *_ = case
    target = artifacts if changed_at == 'member' else state
    original = target.put_bytes_strict_conditional
    def revoke(*args, **kwargs):
        result = original(*args, **kwargs)
        source.value = replace(source.value, ruling_revision='0'*64)
        return result
    target.put_bytes_strict_conditional = revoke
    with pytest.raises(n.DisclosureError): publish(case)
    assert not (state.root/'current.json').exists()


def test_pointer_cas_loss_keeps_competing_generation_and_does_not_retry(case):
    state = case[1]; original = state.put_bytes_strict_conditional; calls=[]
    competitor = n._canonical({'competing': 'owner operation'})
    def competing(key, raw, **kwargs):
        calls.append(key)
        if key == o.CURRENT_KEY:
            original(key, competitor, expected_version=None)
        return original(key, raw, **kwargs)
    state.put_bytes_strict_conditional = competing
    with pytest.raises(n.DisclosureError, match='PUBLICATION_CAS_CONFLICT'): publish(case)
    assert calls.count(o.CURRENT_KEY) == 1
    assert (state.root/o.CURRENT_KEY).read_bytes() == competitor


def test_lost_pointer_ack_reconciles_exact_same_write(case):
    state = case[1]; original = state.put_bytes_strict_conditional; calls=[]
    def lost(key, raw, **kwargs):
        calls.append(key); result = original(key, raw, **kwargs)
        if key == o.CURRENT_KEY: raise OSError('synthetic lost ack')
        return result
    state.put_bytes_strict_conditional = lost
    assert publish(case)['status'] == 'COMMITTED_OBSERVED'
    assert calls.count(o.CURRENT_KEY) == 1


def test_unobservable_pointer_effect_is_not_retried(case):
    state = case[1]; original = state.put_bytes_strict_conditional; calls=[]
    def unknown(key, raw, **kwargs):
        calls.append(key)
        if key == o.CURRENT_KEY: raise OSError('unknown write')
        return original(key, raw, **kwargs)
    state.put_bytes_strict_conditional = unknown
    with pytest.raises(n.DisclosureError) as error: publish(case)
    assert error.value.effect_unknown and error.value.automatic_retry_permitted is False
    assert calls.count(o.CURRENT_KEY) == 1


def test_selected_orphan_member_without_winning_binding_is_unservable(case):
    publish(case)
    source, state, artifacts, *_ = case
    bindings = list(artifacts.root.rglob('*.json'))
    binding = next(x for x in bindings if '/revisions/' in str(x))
    binding.unlink()
    current = o.CurrentDisclosureOwner(source, o.ReadOnlyLocalObjects(state.root))
    with pytest.raises(n.DisclosureError):
        n.read_disclosure(o.ReadOnlyLocalObjects(artifacts.root), current, request(case))


@pytest.mark.parametrize('kind', ['symlink-root','symlink-key','traversal','oversized','fifo'])
def test_readonly_transport_refuses_unsafe_metadata_without_mutation(tmp_path, kind):
    root = tmp_path/'root'; root.mkdir(); (root/'value').write_bytes(b'{}')
    key = 'value'
    if kind == 'symlink-root':
        link = tmp_path/'link'; link.symlink_to(root, target_is_directory=True); root = link
    elif kind == 'symlink-key':
        (root/'link').symlink_to(root/'value'); key = 'link'
    elif kind == 'traversal': key = '../value'
    elif kind == 'oversized': (root/'value').write_bytes(b'X'*40)
    else: os.mkfifo(root/'pipe'); key = 'pipe'
    with pytest.raises((OSError, n.DisclosureError)):
        o.ReadOnlyLocalObjects(root).get_bytes_strict_bounded(key, 20)


def test_readonly_constructor_never_creates_missing_root(tmp_path):
    missing = tmp_path/'missing'
    read = o.ReadOnlyLocalObjects(missing)
    assert not missing.exists()
    with pytest.raises(FileNotFoundError): read.get_bytes_strict_bounded('value',20)
    assert not missing.exists()


def test_cli_reserves_same_operation_once_before_effects(case, tmp_path, monkeypatch):
    from scripts import publish_company_disclosure as cli
    source = case[0]
    for key in ['publisher/source', 'publisher/operations']:
        (tmp_path/key).mkdir(parents=True)
    monkeypatch.setattr(cli.owner, 'CommittedDisclosureSource', lambda repo: source)
    calls = []
    def operation(*args, **kwargs):
        receipt = json.loads((tmp_path/'publisher/operations/synthetic.json').read_text())
        assert receipt['state'] == 'STARTED'
        assert receipt['intent']['manifest_reference'] == o.object_ref(n._canonical(receipt['intent']['manifest']))
        assert receipt['intent']['expected_current_version'] is None
        assert kwargs['intent'] == receipt['intent']
        calls.append(1)
        return {'status': 'COMMITTED_OBSERVED'}
    monkeypatch.setattr(cli, 'publish_generation', operation)
    monkeypatch.setattr('sys.argv', ['publisher', '--repo', str(tmp_path), '--root', str(tmp_path),
                                    '--operation-id', 'synthetic', '--expect-empty'])
    old = os.umask(0o077)
    try:
        assert cli.main() == 0
        with pytest.raises(FileExistsError): cli.main()
    finally:
        os.umask(old)
    assert calls == [1]
    receipt = tmp_path/'publisher/operations/synthetic.json'
    assert receipt.stat().st_mode & 0o777 == 0o600
    assert json.loads(receipt.read_text())['state'] == 'STARTED'
    result = tmp_path/'publisher/operations/synthetic.result.json'
    assert json.loads(result.read_text())['state'] == 'COMMITTED_OBSERVED'


@pytest.mark.parametrize('boundary', ['manifest', 'pointer'])
def test_unknown_effect_retains_exact_immutable_intent_without_replay(case, tmp_path, monkeypatch, boundary):
    from scripts import publish_company_disclosure as cli
    source = case[0]
    for key in ['publisher/source', 'publisher/operations']:
        (tmp_path/key).mkdir(parents=True)
    body = (tmp_path/'input/source.html').read_bytes()
    (tmp_path/'publisher/source'/(source.value.spec['edition']['source_sha256']+'.html')).write_bytes(body)
    monkeypatch.setattr(cli.owner, 'CommittedDisclosureSource', lambda repo: source)
    put, get = LocalStore.put_bytes_strict_conditional, LocalStore.get_bytes_strict_bounded_versioned
    written=[]
    def matches(key): return key == o.CURRENT_KEY if boundary == 'pointer' else key.startswith('generations/')
    def lost(self, key, raw, **kwargs):
        result = put(self, key, raw, **kwargs)
        if self.root == tmp_path/'state' and matches(key):
            written.append((key, raw)); raise OSError('lost response')
        return result
    def unavailable(self, key, limit):
        if written and self.root == tmp_path/'state' and matches(key):
            raise OSError('readback unavailable')
        return get(self, key, limit)
    monkeypatch.setattr(LocalStore, 'put_bytes_strict_conditional', lost)
    monkeypatch.setattr(LocalStore, 'get_bytes_strict_bounded_versioned', unavailable)
    monkeypatch.setattr('sys.argv', ['publisher', '--repo', str(tmp_path), '--root', str(tmp_path),
                                    '--operation-id', 'unknown', '--expect-empty'])
    old = os.umask(0o077)
    try: assert cli.main() == 2
    finally: os.umask(old)
    raw = (tmp_path/'publisher/operations/unknown.json').read_bytes()
    intent = json.loads(raw)['intent']
    assert intent['expected_current_version'] is None and intent['expected_current_sha256'] is None
    ref = intent['manifest_reference']
    assert ref == o.object_ref(n._canonical(intent['manifest']))
    assert (tmp_path/'state/generations'/(ref['sha256']+'.json')).read_bytes() == n._canonical(intent['manifest'])
    result = json.loads((tmp_path/'publisher/operations/unknown.result.json').read_bytes())
    assert result['state'] == 'RECONCILIATION_REQUIRED' and result['effect_unknown'] is True
    assert len(written) == 1
    assert (tmp_path/'publisher/operations/unknown.json').read_bytes() == raw
