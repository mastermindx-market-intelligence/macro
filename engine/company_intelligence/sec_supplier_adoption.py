"""SEC supplier species in the existing disclosure lane, never a new owner/store.

Preparation accepts a native pinned inspection and native current identity
receipts. It grants nothing. The protected source owner must separately adopt
the resulting exact fact, purpose ruling and current identity observations.
No source text, network, producer or publication operation exists here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256

from . import issuer_disclosures as n
from . import issuer_disclosure_owner as owner

SCHEMA = 'company_intelligence.sec_supplier_owner_decision/v1'
PREPARATION_SCHEMA = 'company_intelligence.sec_supplier_preparation/v1'
POLICY_SCHEMA = 'company_intelligence.source_purpose_basis/v1'
SPEC_PATH = 'research/theme_graph/sec_supplier_20261019/NVDA_TSM_OWNER_DECISION.json'
POLICY_PATH = 'research/theme_graph/sec_supplier_20261019/SEC_PUBLIC_FILING_FACT_USE.json'
SOURCE_PATHS = (SPEC_PATH, POLICY_PATH, 'config/theme_sources.yml')
PARTIES = ('subject', 'object')
CONTINUITY = {'schema': owner.CONTINUITY_SCHEMA, 'policy': 'provenance_refresh',
    'semantic_fields': list(owner.SEMANTIC_IDENTITY_FIELDS),
    'provenance_fields': list(owner.PROVENANCE_IDENTITY_FIELDS), 'parties': list(PARTIES)}
POLICY_URLS = [
    'https://www.sec.gov/about/webmaster-frequently-asked-questions',
    'https://www.sec.gov/about/privacy-information#dissemination',
]


def qualify_source_policy(policy_raw, theme_sources_raw, edition, fact):
    """Protected installed source-policy records, never a caller URL allowlist."""
    import yaml
    policy = owner._json(policy_raw)
    n._closed(policy, {'schema', 'basis_id', 'recorded_at', 'reviewer', 'evidence_kind', 'decision',
        'rights_family', 'source_policy_evidence', 'source', 'permitted_use', 'scope_limits'})
    n._require(policy['schema'] == POLICY_SCHEMA and policy['rights_family'] == 'sec_public_filing_facts'
        and policy['evidence_kind'] == 'published_source_reuse_policy'
        and policy['decision'] == 'covered_for_described_use'
        and n._instant(policy['recorded_at']) <= datetime.now(timezone.utc), 'SEC_FACT_POLICY_NOT_QUALIFIED')
    n._require(type(policy['source_policy_evidence']) is list and len(policy['source_policy_evidence']) == 2
        and [x.get('url') for x in policy['source_policy_evidence']] == POLICY_URLS, 'SEC_FACT_POLICY_NOT_QUALIFIED')
    source = edition['sec_source']
    n._require(policy['source'] == {'accession': source['accession'], 'reporting_cik': source['issuer_cik'],
        'archive_url': source['archive_url'], 'raw_sha256': edition['source_sha256'],
        'byte_start': fact['span']['start_byte'], 'byte_end': fact['span']['end_byte'],
        'span_sha256': fact['span']['text_sha256']}, 'POLICY_SOURCE_MISMATCH')
    use = policy['permitted_use']
    n._closed(use, {'purpose', 'audience', 'paid_product_display', 'fact_retention', 'source_attribution_required',
        'kind', 'lifecycle', 'subject', 'object', 'direction', 'product_scope', 'amount', 'economic_share',
        'source_quotation', 'source_body_export', 'reviewer_text'})
    n._require(use['purpose'] == n.SEC_SUPPLIER_PURPOSE and use['audience'] == n.SEC_SUPPLIER_AUDIENCE
        and use['paid_product_display'] is True and use['fact_retention'] is True
        and use['source_attribution_required'] is True
        and use['kind'] == fact['kind'] == 'disclosed_supplier'
        and use['lifecycle'] == fact['lifecycle'] == 'reported_use'
        and use['direction'] == 'object_supplies_subject' and use['product_scope'] == fact['product']
        and use['amount'] is fact['amount'] is None and use['economic_share'] is fact['economic_share'] is None
        and use['source_quotation'] is use['source_body_export'] is use['reviewer_text'] is False,
        'PURPOSE_NOT_ADMITTED')
    row = yaml.safe_load(theme_sources_raw)['families'].get('sec_public_filing_facts')
    n._require(type(row) is dict and row.get('rights_class') == 'derived_display_ok'
        and row.get('auth_class') == 'keyless_public', 'SEC_FACT_POLICY_NOT_QUALIFIED')
    return {'schema': POLICY_SCHEMA, **owner.object_ref(policy_raw), 'family_revision': _digest(row)}


def _digest(value):
    return sha256(n._canonical(value)).hexdigest()


def _identities(identities, observed_at):
    n._closed(identities, {'subject', 'object'})
    instant = n._instant(observed_at)
    n._require(instant <= datetime.now(timezone.utc), 'FUTURE_IDENTITY_OBSERVATION')
    for r in identities.values():
        owner._validate_identity_receipt(r)
        n._require(r['evidence_source'] == 'sec_company_tickers'
                   and r['evidence_snapshot'] <= instant.date().isoformat(), 'IDENTITY_RECEIPT_INVALID')
    n._require(owner._same_generation(identities['subject'], identities['object'])
               and identities['subject']['issuer_id'] != identities['object']['issuer_id'], 'IDENTITY_GENERATION_SPLIT')


def prepare_supplier_input(candidate, inspection, *, identities, identity_queries, identity_observed_at, reviewed_at,
                           role_review):
    """Pure bounded preparation; a dict/hash is not an independently trusted read.

    The caller must actually have performed the pinned inspection and current
    identity reads. Protected-record qualification rechecks identity against
    the injected incumbent owner. Publication still replays the original span
    through the existing native source reader, after purpose admission.
    """
    n._canonical(inspection); n._canonical(candidate)
    _identities(identities, identity_observed_at)
    n._closed(identity_queries, {'subject', 'object'})
    for symbol in identity_queries.values():
        n._require(type(symbol) is str and owner.context._SYMBOL.fullmatch(symbol) is not None, 'IDENTITY_QUERY_INVALID')
    b = inspection.get('native_source_binding')
    i = inspection.get('candidate_inspection')
    n._require(inspection.get('inspection_status') == 'INSPECTABLE' and type(b) is dict
               and b.get('status') == 'NATIVE_PINNED_SOURCE_REPLAYED'
               and b.get('receipt_sidecar_verified') is True and type(i) is dict,
               'NATIVE_SOURCE_REPLAY_REQUIRED')
    a = candidate['assertion']; r = candidate['receipt']; v = i.get('current_candidate_view')
    n._require(type(v) is dict and v['candidate_id'] == candidate['candidate_id']
               and v['assertion'] == a and a['kind'] == 'disclosed_supplier'
               and a['lifecycle'] == 'reported_use' and a['magnitude'] is None
               and v['role_semantics']['direction'] == 'object_supplies_subject', 'SUPPLIER_CANDIDATE_INVALID')
    n._require(candidate['document'] == {'document_id': b['document_id'], 'version': b['document_version'],
               'source_ref': b['archive_url'], 'published_date': None}
               and b['document_version'] == 'sha256:' + b['raw_sha256']
               and b['retrieval_receipt']['content_sha256'] == b['raw_sha256'] == r['source_sha256']
               and b['retrieval_receipt']['byte_length'] == b['raw_byte_length']
               and b['retrieval_receipt']['document_id'] == b['document_id']
               and b['retrieval_receipt']['archive_url'] == b['archive_url'], 'PINNED_RECEIPT_MISMATCH')
    n._require(all(i['support'][k] == r[k] for k in ('byte_start', 'byte_end', 'span_sha256')),
               'PINNED_RECEIPT_MISMATCH')
    n._require(b['source_local_issuer']['cik'] == identities['subject']['evidenced_cik'], 'SUBJECT_IDENTITY_MISMATCH')
    # First-person attribution and the named supplier remain an explicit manual
    # role review. Current annotations cannot resolve a historical relationship.
    for label in (a['subject_label'], a['object_label'], a['product_scope']):
        n._require(type(label) is str and label in r['value_text'], 'SOURCE_LOCAL_LABEL_UNSUPPORTED')
    n._require(candidate['identity_annotations'] == {
        'subject_id': identities['subject']['issuer_id'], 'object_id': identities['object']['issuer_id']}, 'IDENTITY_BINDING_MISMATCH')
    clocks = b['source_local_clocks']
    source = {'snapshot_id': b['snapshot_id'], 'snapshot_at': b['snapshot_at'], 'manifest_key': b['manifest_key'],
        'document_id': b['document_id'], 'accession': b['source_local_filing']['accession'],
        'issuer_cik': b['source_local_issuer']['cik'], 'archive_url': b['archive_url'],
        'accepted_at': clocks['accepted_at'], 'retrieved_at': b['retrieval_receipt']['retrieved_at'],
        'recorded_at': clocks['recorded_at'], 'retrieval_receipt_id': b['retrieval_receipt']['receipt_id'],
        'span_start_byte': r['byte_start'], 'span_end_byte': r['byte_end'], 'span_sha256': r['span_sha256']}
    did = n.disclosure_id(identities['subject']['issuer_id'], b['document_id'])
    edition = {'schema': n.SEC_EDITION_SCHEMA, 'disclosure_id': did,
        'issuer_id': identities['subject']['issuer_id'], 'source_key': b['document_id'],
        'revision': 1, 'previous': None, 'source_sha256': b['raw_sha256'], 'source_byte_length': b['raw_byte_length'],
        'published_date': clocks['filed_on'], 'published_at': None, 'publication_precision': 'date',
        'known_at': b['snapshot_at'], 'sec_source': source}
    eref = n.validate_edition(edition)
    n._require(n._instant(b['snapshot_at']) <= n._instant(reviewed_at) <= datetime.now(timezone.utc), 'REVIEW_CLOCK_INVALID')
    expected_review = {'decision': 'supported_disclosed_supplier_in_selected_filing', 'direction': 'object_supplies_subject',
        'candidate_id': candidate['candidate_id'], 'source_sha256': b['raw_sha256'], 'span_sha256': r['span_sha256'],
        'snapshot_id': b['snapshot_id'], 'supplier_label': a['object_label']}
    # A byte-replayed co-mention must never silently become semantic support.
    # This explicit manual decision is subsequently pinned in protected owner
    # records; an arbitrary request cannot install it as an owner decision.
    n._require(role_review == expected_review, 'ROLE_REVIEW_REQUIRED')
    review = {**role_review, 'reviewed_at': reviewed_at}
    claim = 'supplier:' + _digest({'supplier': identities['object']['issuer_id'], 'product': a['product_scope']})
    fact = {'schema': n.SUPPLIER_FACT_SCHEMA, 'fact_id': n.fact_id(did, claim), 'claim_key': claim,
        'disclosure_id': did, 'edition': eref.payload(), 'revision': 1, 'previous': None,
        'review_revision': _digest(review), 'subject_id': identities['subject']['issuer_id'],
        'object_id': identities['object']['issuer_id'], 'subject_identity': _digest(identities['subject']),
        'object_identity': _digest(identities['object']), 'kind': 'disclosed_supplier', 'lifecycle': 'reported_use',
        'product': a['product_scope'], 'platform': 'foundry_services', 'amount': None, 'economic_share': None,
        'span': {'start_byte': r['byte_start'], 'end_byte': r['byte_end'], 'text_sha256': r['span_sha256']},
        'known_at': None, 'qualification': {'direction': 'object_supplies_subject', 'identity_mode': 'current',
            'identity_observed_at': identity_observed_at, 'evidence_revision': _digest(source)}}
    return {'schema': PREPARATION_SCHEMA, 'edition': edition, 'proposed_fact': fact,
        'identities': deepcopy(identities), 'identity_queries': dict(identity_queries), 'semantic_review': review,
        'adoption_state': 'NOT_ADOPTED', 'purpose_state': 'NOT_QUALIFIED_IN_PREPARATION',
        'publication_permitted': False, 'paid_consumer_permitted': False}


def adopt_supplier_input(prepared, *, adopted_at, ruling_raw, theme_sources_raw):
    """Prepare existing-lane publication inputs after an actual owner decision.

    This performs no adoption/publication effect and never chooses an adoption
    time. The source owner must record its actual decision clock, not the SEC
    acceptance or a retrospective availability estimate.
    """
    fact = deepcopy(prepared['proposed_fact']); fact['known_at'] = adopted_at
    n.validate_fact(fact)
    qualify_source_policy(ruling_raw, theme_sources_raw, prepared['edition'], fact)
    n._require(n._instant(owner._json(ruling_raw)['recorded_at']) <= n._instant(adopted_at), 'ADOPTION_PRECEDES_POLICY')
    n._require(n._instant(prepared['semantic_review']['reviewed_at']) <= n._instant(adopted_at)
               and n._instant(prepared['edition']['known_at']) <= n._instant(adopted_at), 'FACT_PRECEDES_SOURCE')
    return {'schema': SCHEMA, 'ruling_reference': owner.object_ref(ruling_raw),
        'edition': deepcopy(prepared['edition']), 'fact': fact, 'identities': deepcopy(prepared['identities']),
        'identity_queries': deepcopy(prepared['identity_queries']),
        'identity_continuity': deepcopy(prepared.get('identity_continuity', CONTINUITY)),
        'semantic_review': deepcopy(prepared['semantic_review']),
        'temporal_decision': {'identity_mode': 'current', 'historical_admitted': False,
            'identity_observed_at': fact['qualification']['identity_observed_at'], 'adopted_at': adopted_at},
        'correction_decision': {'status': 'current', 'edition': fact['edition'], 'fact': n.validate_fact(fact).payload()}}


def qualify_records(code_version, spec_raw, ruling_raw, registry_raw, identities, *, theme_sources_raw):
    """Called by the incumbent owner; inputs must be protected owner records."""
    import yaml
    from lib.dataos.registry import DatasetContract, Registry, validate_registry
    spec, ruling = owner._json(spec_raw), owner._json(ruling_raw)
    n._closed(spec, {'schema', 'ruling_reference', 'edition', 'fact', 'identities', 'identity_queries', 'semantic_review',
                     'temporal_decision', 'correction_decision', 'identity_continuity'})
    n._require(spec['schema'] == SCHEMA and spec['ruling_reference'] == owner.object_ref(ruling_raw), 'RULING_BINDING_MISMATCH')
    e, f = spec['edition'], spec['fact']
    n._closed(spec['semantic_review'], {'decision', 'direction', 'candidate_id', 'source_sha256',
        'span_sha256', 'snapshot_id', 'supplier_label', 'reviewed_at'})
    eref, fref = n.validate_edition(e), n.validate_fact(f)
    n._require(e['schema'] == n.SEC_EDITION_SCHEMA and f['schema'] == n.SUPPLIER_FACT_SCHEMA, 'FACT_SPECIES_INVALID')
    prepared = {'edition': e, 'proposed_fact': f, 'identities': spec['identities'],
        'identity_queries': spec['identity_queries'], 'semantic_review': spec['semantic_review'],
        'identity_continuity': spec['identity_continuity']}
    n._require(adopt_supplier_input(prepared, adopted_at=f['known_at'], ruling_raw=ruling_raw,
        theme_sources_raw=theme_sources_raw) == spec, 'SUPPLIER_DECISION_MISMATCH')
    owner._validate_continuity(spec['identity_continuity'], PARTIES)
    _identities(spec['identities'], f['qualification']['identity_observed_at'])
    _identities(identities, datetime.now(timezone.utc).isoformat())
    n._closed(spec['identity_queries'], {'subject', 'object'})
    n._require(all(type(x) is str and owner.context._SYMBOL.fullmatch(x) is not None
        for x in spec['identity_queries'].values()), 'IDENTITY_QUERY_INVALID')
    for party in PARTIES:
        n._require(all(identities[party][key] == spec['identities'][party][key]
            for key in owner.SEMANTIC_IDENTITY_FIELDS), 'CURRENT_IDENTITY_CHANGED')
    recorded = spec['identities']
    n._require(f['edition'] == eref.payload() and f['subject_id'] == e['issuer_id']
               and f['disclosure_id'] == e['disclosure_id']
               and f['subject_id'] == identities['subject']['issuer_id']
               and f['object_id'] == identities['object']['issuer_id']
               and f['subject_identity'] == _digest(recorded['subject'])
               and f['object_identity'] == _digest(recorded['object'])
               and e['sec_source']['issuer_cik'] == identities['subject']['evidenced_cik'], 'IDENTITY_BINDING_MISMATCH')
    n._require(_digest(spec['semantic_review']) == f['review_revision']
               and spec['semantic_review']['decision'] == 'supported_disclosed_supplier_in_selected_filing'
               and spec['semantic_review']['direction'] == 'object_supplies_subject'
               and spec['semantic_review']['source_sha256'] == e['source_sha256']
               and spec['semantic_review']['span_sha256'] == e['sec_source']['span_sha256']
               and spec['semantic_review']['snapshot_id'] == e['sec_source']['snapshot_id']
               and f['qualification']['evidence_revision'] == _digest(e['sec_source']),
               'REVIEW_BINDING_MISMATCH')
    n._require(spec['semantic_review']['supplier_label'] == ruling['permitted_use']['object'], 'POLICY_ROLE_MISMATCH')
    n._require(f['span'] == {'start_byte': e['sec_source']['span_start_byte'],
        'end_byte': e['sec_source']['span_end_byte'], 'text_sha256': e['sec_source']['span_sha256']}, 'SUPPLIER_EVIDENCE_MISMATCH')
    rows = [r for r in yaml.safe_load(registry_raw)['datasets'] if r.get('dataset_id') == owner.DATASET]
    n._require(len(rows) == 1, 'DATASET_NOT_ADOPTED')
    row = DatasetContract.from_mapping(rows[0])
    n._require(not validate_registry(Registry([row])) and row.owner == 'company-intelligence'
               and row.producer == owner.PRODUCER and row.temporal_profile.value == 'DERIVED'
               and row.status.value in {'PROPOSED', 'PRODUCED'}
               and row.storage == 'private:company-intelligence/state/generations/{sha256}.json'
               and {'computed_at', 'code_version', 'input_cutoffs'} <= set(row.schema), 'DATASET_NOT_ADOPTED')
    # Dataset existence/license text is not the source-purpose grant. The exact
    # separate supplier ruling above is mandatory; C01 cannot satisfy it.
    return owner.OwnerSnapshot(code_version, spec_raw, owner.digest(ruling_raw),
        owner.digest(n._canonical(rows[0])), row.status.value, n._canonical(identities))


class PinnedSupplierSource:
    """Existing publication source interface over the exact retained snapshot.

    No raw-source copy/store is required. Construction does no body I/O; native
    publish_disclosure calls read_source only after exact purpose admission.
    The caller supplies the already provisioned native read-only authority.
    """
    def __init__(self, snapshot, authority):
        from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
        n._require(type(authority) is PinnedSourceAuthority, 'EXACT_NATIVE_AUTHORITY_REQUIRED')
        self.edition = snapshot.spec['edition']
        self.authority = authority
        n._require(self.edition['schema'] == n.SEC_EDITION_SCHEMA, 'SEC_SOURCE_BINDING_MISMATCH')

    def read_source(self, **binding):
        from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority, gzip_stored_byte_ceiling
        from engine.fundamental_forensics.sec_document_spine import manifest_from_json_bytes
        e = self.edition; s = e['sec_source']
        n._require(binding == dict(disclosure_id=e['disclosure_id'], edition_reference=n.validate_edition(e),
            source_sha256=e['source_sha256'], expected_byte_length=e['source_byte_length'],
            max_byte_length=n.MAX_SEC_SOURCE_BYTES), 'RETAINED_SOURCE_BINDING_MISMATCH')
        a = PinnedSourceAuthority(store=self.authority._store, snapshot_id=s['snapshot_id'])
        manifest_read = a.read_file(kind='archive', relative_path=s['manifest_key'], maximum_bytes=1024 * 1024)
        m = manifest_from_json_bytes(manifest_read.content)
        selected = [d for d in m['documents'] if d['document_id'] == s['document_id']]
        n._require(len(selected) == 1, 'SEC_SOURCE_BINDING_MISMATCH')
        d = selected[0]; r = d['retrieval']
        n._require(a.snapshot_at == s['snapshot_at'] and m['issuer']['cik'] == s['issuer_cik']
            and m['filing']['accession'] == s['accession'] and m['clocks']['accepted_at'] == s['accepted_at']
            and m['clocks']['recorded_at'] == s['recorded_at'] and m['clocks']['filed_on'] == e['published_date']
            and d['archive_url'] == s['archive_url'] and r['receipt_id'] == s['retrieval_receipt_id']
            and r['retrieved_at'] == s['retrieved_at'] and r['content_sha256'] == e['source_sha256']
            and r['byte_length'] == e['source_byte_length'], 'SEC_SOURCE_BINDING_MISMATCH')
        read = a.read_archive_document(storage_key=d['storage_key'], expected_receipt=r,
            maximum_bytes=n.MAX_SEC_SOURCE_BYTES,
            maximum_stored_bytes=gzip_stored_byte_ceiling(e['source_byte_length']))
        n._require(read.receipt_sidecar_verified is True, 'NATIVE_SOURCE_REPLAY_REQUIRED')
        return read.content
