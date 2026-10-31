"""Synthetic native custody/identity checks, never real-source acceptance.

The production profile is fixed. Tests explicitly substitute a synthetic pin
set, retaining native manifest, gzip, receipt, snapshot and span verification.
No developer cache, HTTP, owner publication or provider access is required.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd

from collectors.sec_document_spine import persist_archive_document, persist_filing_manifest, receipt_storage_key
from engine.company_intelligence import h20_reported_event as h20
from engine.company_intelligence.current_company_context import resolve_current_company
from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
from engine.fundamental_forensics.sec_document_spine import (
    build_filing_manifests, documents_from_archive_index, with_archive_documents,
    with_document_retrievals,
)
from engine.fundamental_forensics.source_sync import sync_source_roots, HARD_MAX_SNAPSHOT_MANIFEST_BYTES
from engine.research_vault.r2_store import LocalStore
from engine.theme_graph import native_disclosure_propagation as adapter
from tests.test_gmi_native_disclosure_propagation import native as synthetic_identity_base

NOW = '2026-10-19T18:00:00+00:00'
COMPILED = '2026-10-19T18:01:00+00:00'
ASOF = '2026-10-19'
# A visibly synthetic sentence, deliberately not the retained filing quotation.
SPAN = b'<p>SYNTHETIC first quarter of fiscal year 2026 test: as the demand for H20 products diminished.</p>'
BODY = b'SYNTHETIC prefix\n' + SPAN + b'\nSYNTHETIC footer'


class SyntheticReadOnlySpy:
    def __init__(self, backing):
        self.backing, self.reads, self.missing_key = backing, [], None

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        self.reads.append((key, maximum_bytes))
        if key == self.missing_key:
            return None
        return self.backing.get_bytes_strict_bounded(key, maximum_bytes)

    def _denied(self, *args, **kwargs):
        raise AssertionError('source qualifier attempted write, discovery or unbounded read')

    get_bytes = get_bytes_strict = put_bytes = list_prefix = exists = upload_time = _denied


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


@pytest.fixture
def captured(tmp_path, monkeypatch):
    raw_root, archive_root = tmp_path/'raw', tmp_path/'archive'
    raw_root.mkdir(); archive_root.mkdir()
    manifest = build_filing_manifests({'cik': h20.CIK, 'name': 'SYNTHETIC NVIDIA',
        'filings': {'recent': {'accessionNumber': [h20.ACCESSION], 'form': ['10-K'],
        'filingDate': ['2026-02-25'], 'reportDate': ['2026-01-25'],
        'acceptanceDateTime': ['2026-02-25T21:42:19Z'],
        'primaryDocument': ['nvda-20260125.htm']}}},
        recorded_at='2026-10-09T04:00:00Z')[0]
    manifest = with_archive_documents(manifest, documents_from_archive_index(manifest,
        {'directory': {'item': [{'name': 'nvda-20260125.htm'}]}}))
    document = manifest['documents'][0]
    receipt = persist_archive_document(archive_root, document, BODY,
        retrieved_at='2026-10-09T03:53:33Z')
    manifest = with_document_retrievals(manifest, {document['document_id']: receipt.to_dict()})
    manifest_key = persist_filing_manifest(archive_root, manifest)
    backing = LocalStore(tmp_path/'source-store')
    snapshot = sync_source_roots(raw_root=raw_root, archive_root=archive_root, store=backing,
        snapshot_at='2026-10-09T04:00:01Z', publish_latest=False)
    reader = SyntheticReadOnlySpy(backing)
    authority = PinnedSourceAuthority(store=reader, snapshot_id=snapshot.snapshot_id)
    decision = json.loads(Path(h20.DECISION_PATH).read_bytes())
    policy = json.loads(Path(h20.POLICY_PATH).read_bytes())
    source = {**decision['source'], 'raw_sha256': sha256(BODY).hexdigest(),
        'byte_start': BODY.index(SPAN), 'byte_end': BODY.index(SPAN)+len(SPAN),
        'span_sha256': sha256(SPAN).hexdigest()}
    decision['source'] = deepcopy(source); policy['source'] = deepcopy(source)
    policy_raw = canonical(policy); decision['policy_sha256'] = sha256(policy_raw).hexdigest()
    decision_raw = canonical(decision)
    for key, value in {'RAW_SHA256': source['raw_sha256'], 'RAW_BYTES': len(BODY),
        'SPAN_START': source['byte_start'], 'SPAN_END': source['byte_end'],
        'SPAN_SHA256': source['span_sha256'], 'SNAPSHOT_ID': snapshot.snapshot_id,
        'MANIFEST_KEY': manifest_key, 'DECISION_SHA256': sha256(decision_raw).hexdigest(),
        'POLICY_SHA256': sha256(policy_raw).hexdigest()}.items():
        monkeypatch.setattr(h20, key, value)
    monkeypatch.setattr(h20, '_now', lambda: datetime.fromisoformat(NOW))
    theme = b'families:\n  sec_public_filing_facts:\n    rights_class: derived_display_ok\n    auth_class: keyless_public\n'
    return SimpleNamespace(authority=authority, decision=decision_raw, policy=policy_raw,
        theme=theme, reader=reader, backing=backing, snapshot=snapshot, document=manifest['documents'][0])


def qualify(c, **overrides):
    return h20.qualify_retained_h20_event(overrides.pop('authority', c.authority),
        decision_raw=overrides.pop('decision_raw', c.decision),
        policy_raw=overrides.pop('policy_raw', c.policy),
        theme_sources_raw=overrides.pop('theme_sources_raw', c.theme), **overrides)


@pytest.fixture
def native_context(synthetic_identity_base):
    view, bundle, records = synthetic_identity_base
    substitutions = [('ALPHA', 'NVDA'), ('BETA', 'TSM'), ('US-XNAS-TSM', 'US-XNYS-TSM'),
        ('0000000001', '0001045810'), ('0000000002', '0001046179'),
        ('c'*64, '24185935320d4ff8fe852584b1497f16f000f4af4cb5e9f195f61c7a2ff9948b'),
        ('d'*64, '49cbd4aac98292e5889e0af7b6f868b337223dd2b3a8ae5c367cabde2b4c678c')]
    def replace(value):
        for before, after in substitutions:
            value = value.replace(before, after)
        return value
    for rows in records.values():
        for row in rows:
            for key, value in row.items():
                if type(value) is str:
                    row[key] = replace(value)
    view = json.loads(replace(json.dumps(view)))
    c = view['context']
    c['source_attribution'] = {'source': 'SEC public issuer filing', 'archive_url': h20.URL,
        'accession': h20.ACCESSION, 'document_id': h20.DOCUMENT_ID}
    c['provenance']['current_identity_sha256s'] = {
        p: resolve_current_company(bundle(), symbol, today=date.fromisoformat(ASOF))[
            'issuer_binding']['identity_snapshot_reference']['sha256']
        for p, symbol in [('subject', 'NVDA'), ('object', 'TSM')]}
    return view, bundle


def compose(c, native_context, **overrides):
    view, bundle = native_context
    return adapter.compose_qualified_h20_supplier(overrides.pop('context', view),
        overrides.pop('qualified_event', qualify(c)), identity_bundle=overrides.pop('identity_bundle', bundle()),
        identity_observed_at=NOW, asof=ASOF, compiled_at=overrides.pop('compiled_at', COMPILED),
        review_by='2026-11-19', **overrides)


def assert_unavailable(result):
    assert result['status'] == 'unavailable'
    assert all(result[k] is None for k in ('candidate', 'source_event', 'event_evidence', 'lineage', 'contextual_refusal'))
    assert not any(result['authority'].values())
    assert 'SYNTHETIC' not in json.dumps(result)


def test_h20_context_binding_is_pure_and_preserves_native_inputs(native_context, monkeypatch):
    context, bundle = native_context
    before = deepcopy(context)
    monkeypatch.setattr(h20, 'qualify_retained_h20_event',
        lambda *a, **kw: pytest.fail('pure context binding opened source qualifier'))
    actual = adapter.bind_h20_supplier_context(context, identity_bundle=bundle(),
        identity_observed_at=NOW, asof=ASOF, compiled_at=COMPILED)
    expected = adapter.bind_current_supplier(context, identity_bundle=bundle(),
        subject_symbol='NVDA', object_symbol='TSM', identity_observed_at=NOW,
        asof=ASOF, compiled_at=COMPILED)
    assert actual == expected and context == before
    assert actual['source_identity']['issuer_id'] == 'ISS:US-XNAS-NVDA'
    assert actual['target']['resolution']['security_id'] == 'SEC:US-XNYS-TSM'


@pytest.mark.parametrize('mutation', ['other_pair', 'identity_unavailable', 'receipt_changed',
    'generation_changed', 'other_fact', 'other_edition', 'other_filing', 'subject_cik', 'object_cik'])
def test_h20_context_binding_refuses_before_any_event_is_needed(native_context, mutation):
    context, bundle = native_context
    context = deepcopy(context); c = context['context']; binding = bundle()
    if mutation == 'other_pair': c['relationship']['object_id'] = 'ISS:US-XNYS-OTHER'
    elif mutation == 'identity_unavailable': binding = None
    elif mutation == 'receipt_changed': c['provenance']['current_identity_sha256s']['subject'] = 'f'*64
    elif mutation == 'generation_changed': binding = bundle(commit='e'*40)
    elif mutation in ('subject_cik', 'object_cik'):
        old_cik = '0001045810' if mutation == 'subject_cik' else '0001046179'
        data = {name: pd.read_parquet(BytesIO(getattr(binding, name))).to_dict('records')
            for name in ('security_master', 'issuer_master', 'vendor_aliases')}
        for rows in data.values():
            for row in rows:
                for key in ('cik', 'issuer_cik'):
                    if row.get(key) == old_cik: row[key] = '0000000099'
        binding = bundle(data=data)
        c['provenance']['current_identity_sha256s'] = {
            party: resolve_current_company(binding, symbol, today=date.fromisoformat(ASOF))[
                'issuer_binding']['identity_snapshot_reference']['sha256']
            for party, symbol in [('subject', 'NVDA'), ('object', 'TSM')]}
        adapter.bind_current_supplier(context, identity_bundle=binding,
            subject_symbol='NVDA', object_symbol='TSM', identity_observed_at=NOW,
            asof=ASOF, compiled_at=COMPILED)
    elif mutation in ('other_fact', 'other_edition'):
        # Keep the generic native carrier internally coherent: only the fixed
        # H20 profile gate, not a malformed carrier, must reject this case.
        key = 'reference' if mutation == 'other_fact' else 'edition'
        old = c['provenance'][key]['sha256']
        context = json.loads(json.dumps(context).replace(old, 'f'*64))
        adapter.bind_current_supplier(context, identity_bundle=binding,
            subject_symbol='NVDA', object_symbol='TSM', identity_observed_at=NOW,
            asof=ASOF, compiled_at=COMPILED)
    elif mutation == 'other_filing': c['source_attribution']['document_id'] = 'another_document'
    with pytest.raises(adapter.EconomicPropagationError):
        adapter.bind_h20_supplier_context(context, identity_bundle=binding,
            identity_observed_at=NOW, asof=ASOF, compiled_at=COMPILED)


def test_native_capture_replays_exact_span_and_keeps_clocks_distinct(captured):
    before = {str(p): p.read_bytes() for p in captured.backing.root.rglob('*') if p.is_file()}
    evidence = qualify(captured).evidence()
    assert evidence['fact']['schema'] == 'event_fact.v1'
    assert evidence['fact']['period'] == '2026Q1'
    assert evidence['source_report_period'] == 'FY2026'
    assert evidence['reported_occurrence_period'] == {'year': 2026, 'quarter': 1}
    assert evidence['occurrence_at'] is evidence['source_document']['available_at'] is None
    assert evidence['historical_body_availability'] == 'unknown'
    assert evidence['source_document']['published_at'] is None
    assert evidence['clocks']['reporting_basis'] == 'SEC_acceptance'
    assert evidence['clocks']['adopted_at'] != evidence['clocks']['retrieved_at']
    assert evidence['fact']['source_span']['receipt_state'] == 'byte_replayed'
    assert BODY.decode() not in json.dumps(evidence) and SPAN.decode() not in json.dumps(evidence)
    assert evidence['fact']['source_span']['display_excerpt'] == ''
    assert not any('latest' in key for key, _ in captured.reader.reads)
    assert all(type(limit) is int and 0 < limit <= HARD_MAX_SNAPSHOT_MANIFEST_BYTES for _, limit in captured.reader.reads)
    assert before == {str(p): p.read_bytes() for p in captured.backing.root.rglob('*') if p.is_file()}


def test_real_native_contract_shape_builds_conditional_not_observed_transfer(captured, native_context):
    result = compose(captured, native_context)
    assert result['status'] == 'available', result['reason']
    candidate = result['candidate']
    assert candidate['hypothesis_state'] == 'supported_hypothesis'
    assert candidate['mechanism']['state'] == 'hypothesized'
    assert candidate['mechanism']['operating_metric_class'] == 'volume'
    assert candidate['economic_share'] is None
    assert result['source_event']['known_at'] == json.loads(captured.decision)['adopted_at']
    assert result['source_event']['event_time'] == result['event_evidence']['clocks']['reporting_at']
    assert result['event_evidence']['counterparty_applicability'] == 'unestablished'
    assert result['lineage']['same_document'] is True
    assert result['lineage']['independent_corroboration'] is False
    assert result['contextual_refusal']['hypothesis'] is None
    assert result['contextual_refusal']['relationship_input_used'] is False
    assert result['contextual_refusal']['reason'] == 'CO_DOCUMENT_CONTEXT_IS_NOT_GRAPH1'
    assert not any(result['authority'].values())
    assert BODY.decode() not in json.dumps(result) and SPAN.decode() not in json.dumps(result)


@pytest.mark.parametrize('field', ['decision_raw', 'policy_raw'])
def test_protected_pins_refuse_before_owner_io(captured, field):
    captured.reader.reads.clear()
    with pytest.raises(h20.ReportedEventError, match='H20_PROTECTED_RECORD_MISMATCH'):
        qualify(captured, **{field: b'{"source":"C01_OR_OTHER"}'})
    assert not captured.reader.reads


@pytest.mark.parametrize('theme', [b'families: {}', b'families:\n  sec_public_filing_facts:\n    rights_class: internal_only\n    auth_class: keyless_public', b'SECRET_PROVIDER_ERROR:\xff'])
def test_absent_denied_or_malformed_source_purpose_refuses_without_io(captured, theme):
    captured.reader.reads.clear()
    with pytest.raises(h20.ReportedEventError) as error:
        qualify(captured, theme_sources_raw=theme)
    assert 'SECRET' not in str(error.value) and not captured.reader.reads


def test_future_native_adoption_refuses_before_source_read(captured, monkeypatch):
    captured.reader.reads.clear()
    monkeypatch.setattr(h20, '_now', lambda: datetime(2026, 10, 18, tzinfo=timezone.utc))
    with pytest.raises(h20.ReportedEventError, match='H20_ADOPTION_CLOCK_INVALID'):
        qualify(captured)
    assert not captured.reader.reads


def test_wrong_authority_and_cached_override_cannot_supply_evidence(captured):
    captured.reader.reads.clear()
    with pytest.raises(h20.ReportedEventError, match='H20_EXACT_NATIVE_SOURCE_REQUIRED'):
        qualify(captured, authority=SimpleNamespace(snapshot_id=h20.SNAPSHOT_ID))
    assert not captured.reader.reads
    captured.authority.read_archive_document = lambda **kw: pytest.fail('session override trusted')
    assert qualify(captured).evidence()['source_ref']['snapshot_id'] == h20.SNAPSHOT_ID


@pytest.mark.parametrize('key_kind', ['manifest', 'receipt', 'object'])
def test_missing_native_custody_link_never_falls_back(captured, key_kind):
    # Map the exact archive-relative address through its native snapshot witness;
    # the storage layer deliberately uses content-addressed names.
    paths = {'manifest': h20.MANIFEST_KEY,
        'receipt': receipt_storage_key(captured.document['retrieval']['receipt_id']),
        'object': captured.document['storage_key']}
    witness = captured.authority.read_file(kind='archive', relative_path=paths[key_kind],
        maximum_bytes=1024*1024).witness
    captured.reader.missing_key = witness.object_key
    with pytest.raises(h20.ReportedEventError, match='H20_NATIVE_QUALIFICATION_UNAVAILABLE'):
        qualify(captured)


@pytest.mark.parametrize('mutation', ['serialized_event', 'forged_nominal', 'event_after_compilation',
    'wrong_supplier_fact', 'wrong_supplier_edition', 'wrong_source_attribution', 'wrong_current_receipt',
    'wrong_current_bundle', 'c01_substitution', 'reversed_role', 'graph2', 'graph3', 'purpose', 'historical'])
def test_conditional_entry_cannot_promote_unqualified_or_misbound_inputs(captured, native_context, mutation):
    context = deepcopy(native_context[0]); c = context['context']; kw = {'context': context}
    if mutation == 'serialized_event': kw['qualified_event'] = qualify(captured).evidence()
    elif mutation == 'forged_nominal': kw['qualified_event'] = object.__new__(h20.QualifiedReportedEvent)
    elif mutation == 'event_after_compilation': kw['compiled_at'] = '2026-10-19T17:59:00Z'
    elif mutation == 'wrong_supplier_fact': c['provenance']['reference']['sha256'] = 'f'*64
    elif mutation == 'wrong_supplier_edition': c['provenance']['edition']['sha256'] = 'f'*64
    elif mutation == 'wrong_source_attribution': c['source_attribution']['document_id'] = 'another_document'
    elif mutation == 'wrong_current_receipt': c['provenance']['current_identity_sha256s']['subject'] = 'f'*64
    elif mutation == 'wrong_current_bundle': kw['identity_bundle'] = native_context[1](commit='e'*40)
    elif mutation == 'c01_substitution': c['relationship'].update(kind='product_integration', lifecycle='planned')
    elif mutation == 'reversed_role': c['relationship']['direction'] = 'subject_supplies_object'
    elif mutation in ('graph2', 'graph3'): c['mapping']['k3_input']['graph'] = 'graph_' + mutation[-1]
    elif mutation == 'purpose': c['usage']['purpose'] = 'training'
    elif mutation == 'historical': c['timing'].update(query_mode='historical', query_as_of='2026-02-25')
    assert_unavailable(compose(captured, native_context, **kw))
