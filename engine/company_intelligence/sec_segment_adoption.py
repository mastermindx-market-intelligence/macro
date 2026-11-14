"""SEC segment-activity species in the existing disclosure lane, never a new owner/store.

Mirrors ``sec_supplier_adoption`` for a single party: the issuer's own disclosed
business line in an annual report (10-K / 10-K/A / 20-F / 20-F/A). Preparation
accepts a native pinned inspection and a native current identity receipt. It
grants nothing. The protected source owner must separately adopt the resulting
exact fact, purpose ruling and current identity observation. No source text,
network, producer or publication operation exists here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256

from . import issuer_disclosures as n
from . import issuer_disclosure_owner as owner

SCHEMA = 'company_intelligence.sec_segment_owner_decision/v1'
PREPARATION_SCHEMA = 'company_intelligence.sec_segment_preparation/v1'
POLICY_SCHEMA = 'company_intelligence.source_purpose_basis/v1'
PARTIES = ('subject',)
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
        'kind', 'lifecycle', 'subject', 'disclosed_line', 'share_scope',
        'source_quotation', 'source_body_export', 'reviewer_text'})
    n._require(use['purpose'] == n.SEC_SUPPLIER_PURPOSE and use['audience'] == n.SEC_SUPPLIER_AUDIENCE
        and use['paid_product_display'] is True and use['fact_retention'] is True
        and use['source_attribution_required'] is True
        and use['kind'] == fact['kind'] == 'segment_activity'
        and use['lifecycle'] == fact['lifecycle'] == 'reported'
        and use['subject'] == fact['subject_id']
        and use['disclosed_line'] == fact['disclosed_line']
        and use['share_scope'] == fact['share_scope']
        and use['source_quotation'] is use['source_body_export'] is use['reviewer_text'] is False,
        'PURPOSE_NOT_ADMITTED')
    row = yaml.safe_load(theme_sources_raw)['families'].get('sec_public_filing_facts')
    n._require(type(row) is dict and row.get('rights_class') == 'derived_display_ok'
        and row.get('auth_class') == 'keyless_public', 'SEC_FACT_POLICY_NOT_QUALIFIED')
    return {'schema': POLICY_SCHEMA, **owner.object_ref(policy_raw), 'family_revision': _digest(row)}


def _digest(value):
    return sha256(n._canonical(value)).hexdigest()


def _identities(identities, observed_at):
    n._closed(identities, {'subject'})
    instant = n._instant(observed_at)
    n._require(instant <= datetime.now(timezone.utc), 'FUTURE_IDENTITY_OBSERVATION')
    for r in identities.values():
        owner._validate_identity_receipt(r)
        n._require(r['evidence_source'] == 'sec_company_tickers'
                   and r['evidence_snapshot'] <= instant.date().isoformat(), 'IDENTITY_RECEIPT_INVALID')


def prepare_segment_input(inspection, *, assertion, receipt, identities, identity_queries,
                          identity_observed_at, reviewed_at, role_review):
    """Pure bounded preparation; a dict/hash is not an independently trusted read.

    The caller must actually have performed the pinned inspection and the current
    identity read. The native source replay is semantics-independent: it binds the
    exact annual-report bytes, while the disclosed line and exposure magnitudes are
    the explicit segment assertion. Protected-record qualification rechecks identity
    against the injected incumbent owner. Publication still replays the original span
    through the existing native source reader, after purpose admission.
    """
    n._canonical(inspection)
    _identities(identities, identity_observed_at)
    n._closed(identity_queries, {'subject'})
    for symbol in identity_queries.values():
        n._require(type(symbol) is str and owner.context._SYMBOL.fullmatch(symbol) is not None, 'IDENTITY_QUERY_INVALID')
    b = inspection.get('native_source_binding')
    n._require(inspection.get('inspection_status') == 'INSPECTABLE' and type(b) is dict
               and b.get('status') == 'NATIVE_PINNED_SOURCE_REPLAYED'
               and b.get('receipt_sidecar_verified') is True,
               'NATIVE_SOURCE_REPLAY_REQUIRED')
    n._closed(assertion, {'subject_label', 'disclosed_line', 'share_scope', 'revenue', 'revenue_denominator',
        'profit', 'profit_denominator', 'profit_measure', 'fiscal_year', 'figure_spans'}
        | {f'{name}_{suffix}' for name in n.SEGMENT_FIGURE_NAMES for suffix in ('text', 'sign', 'scale')})
    form_type = b['source_local_filing']['form']
    n._require(type(form_type) is str and form_type in n.SEGMENT_FORM_TYPES, 'SEGMENT_FORM_NOT_ADMITTED')
    n._require(b['document_version'] == 'sha256:' + b['raw_sha256']
               and b['retrieval_receipt']['content_sha256'] == b['raw_sha256'] == receipt['source_sha256']
               and b['retrieval_receipt']['byte_length'] == b['raw_byte_length']
               and b['retrieval_receipt']['document_id'] == b['document_id']
               and b['retrieval_receipt']['archive_url'] == b['archive_url'], 'PINNED_RECEIPT_MISMATCH')
    n._require(b['source_local_issuer']['cik'] == identities['subject']['evidenced_cik'], 'SUBJECT_IDENTITY_MISMATCH')
    # First-person attribution and the disclosed line remain an explicit manual
    # review; both labels must be present in the replayed span text.
    for label in (assertion['subject_label'], assertion['disclosed_line']):
        n._require(type(label) is str and label in receipt['value_text'], 'SOURCE_LOCAL_LABEL_UNSUPPORTED')
    # Each non-null figure carries its own span in the same pinned document. The
    # match is literal, never numeric: the replayed span bytes must contain the
    # digits as printed, and the value is sign x digits x scale (a loss is negative).
    main_bytes = receipt['span_text'].encode('utf-8')
    main_start = receipt['byte_start']
    figure_spans = n._closed(assertion['figure_spans'], set(n.SEGMENT_FIGURE_NAMES))
    for name in n.SEGMENT_FIGURE_NAMES:
        value, span = assertion[name], figure_spans[name]
        if value is None:
            n._require(span is None, 'FIGURE_SPAN_MISMATCH')
            continue
        n._require(span is not None, 'FIGURE_SPAN_REQUIRED')
        n._segment_figure_span(span)
        rel_start, rel_end = span['start_byte'] - main_start, span['end_byte'] - main_start
        n._require(0 <= rel_start < rel_end <= len(main_bytes), 'FIGURE_SPAN_MISMATCH')
        text, sign, scale = (assertion[f'{name}_text'], assertion[f'{name}_sign'], assertion[f'{name}_scale'])
        n._verify_figure_span(name, {'start_byte': rel_start, 'end_byte': rel_end,
                                     'text_sha256': span['text_sha256']}, text, sign, main_bytes,
                              whole_document=False)
        n._require(type(text) is str and n._FIGURE_TEXT.fullmatch(text) is not None, 'FIGURE_TEXT_MISMATCH')
        n._require(sign in n.SEGMENT_FIGURE_SIGNS and scale in n.SEGMENT_FIGURE_SCALES, 'FIGURE_TEXT_MISMATCH')
        derived = (-1 if sign == '-' else 1) * int(text.replace(',', '')) * n.SEGMENT_FIGURE_SCALES[scale]
        n._require(value == derived, 'FIGURE_TEXT_MISMATCH')
    clocks = b['source_local_clocks']
    source = {'snapshot_id': b['snapshot_id'], 'snapshot_at': b['snapshot_at'], 'manifest_key': b['manifest_key'],
        'document_id': b['document_id'], 'accession': b['source_local_filing']['accession'],
        'issuer_cik': b['source_local_issuer']['cik'], 'archive_url': b['archive_url'],
        'accepted_at': clocks['accepted_at'], 'retrieved_at': b['retrieval_receipt']['retrieved_at'],
        'recorded_at': clocks['recorded_at'], 'retrieval_receipt_id': b['retrieval_receipt']['receipt_id'],
        'span_start_byte': receipt['byte_start'], 'span_end_byte': receipt['byte_end'],
        'span_sha256': receipt['span_sha256']}
    did = n.disclosure_id(identities['subject']['issuer_id'], b['document_id'])
    edition = {'schema': n.SEC_EDITION_SCHEMA, 'disclosure_id': did,
        'issuer_id': identities['subject']['issuer_id'], 'source_key': b['document_id'],
        'revision': 1, 'previous': None, 'source_sha256': b['raw_sha256'], 'source_byte_length': b['raw_byte_length'],
        'published_date': clocks['filed_on'], 'published_at': None, 'publication_precision': 'date',
        'known_at': b['snapshot_at'], 'sec_source': source}
    eref = n.validate_edition(edition)
    n._require(n._instant(b['snapshot_at']) <= n._instant(reviewed_at) <= datetime.now(timezone.utc), 'REVIEW_CLOCK_INVALID')
    expected_review = {'decision': 'supported_segment_activity_in_selected_filing',
        'source_sha256': b['raw_sha256'], 'span_sha256': receipt['span_sha256'],
        'snapshot_id': b['snapshot_id'], 'disclosed_line': assertion['disclosed_line']}
    # A byte-replayed span must never silently become semantic support. This
    # explicit manual decision is subsequently pinned in protected owner records;
    # an arbitrary request cannot install it as an owner decision.
    n._require(role_review == expected_review, 'ROLE_REVIEW_REQUIRED')
    review = {**role_review, 'reviewed_at': reviewed_at}
    claim = 'segment:' + _digest({'subject': identities['subject']['issuer_id'],
        'disclosed_line': assertion['disclosed_line']})
    fact = {'schema': n.SEGMENT_FACT_SCHEMA, 'fact_id': n.activity_fact_id(did, claim), 'claim_key': claim,
        'disclosure_id': did, 'edition': eref.payload(), 'revision': 1, 'previous': None,
        'review_revision': _digest(review), 'subject_id': identities['subject']['issuer_id'],
        'subject_identity': _digest(identities['subject']), 'kind': 'segment_activity', 'lifecycle': 'reported',
        'form_type': form_type, 'accession': b['source_local_filing']['accession'],
        'disclosed_line': assertion['disclosed_line'], 'share_scope': assertion['share_scope'],
        'revenue': assertion['revenue'], 'revenue_denominator': assertion['revenue_denominator'],
        'profit': assertion['profit'], 'profit_denominator': assertion['profit_denominator'],
        'profit_measure': assertion['profit_measure'], 'fiscal_year': assertion['fiscal_year'],
        'span': {'start_byte': receipt['byte_start'], 'end_byte': receipt['byte_end'],
            'text_sha256': receipt['span_sha256']},
        'figure_spans': figure_spans, 'known_at': None,
        **{f'{name}_{suffix}': assertion[f'{name}_{suffix}']
           for name in n.SEGMENT_FIGURE_NAMES for suffix in ('text', 'sign', 'scale')}}
    return {'schema': PREPARATION_SCHEMA, 'edition': edition, 'proposed_fact': fact,
        'identities': deepcopy(identities), 'identity_queries': dict(identity_queries), 'semantic_review': review,
        'identity_observed_at': identity_observed_at,
        'adoption_state': 'NOT_ADOPTED', 'purpose_state': 'NOT_QUALIFIED_IN_PREPARATION',
        'publication_permitted': False, 'paid_consumer_permitted': False}


def adopt_segment_input(prepared, *, adopted_at, ruling_raw, theme_sources_raw, identity_observed_at):
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
            'identity_observed_at': identity_observed_at, 'adopted_at': adopted_at},
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
    n._closed(spec['semantic_review'], {'decision', 'source_sha256', 'span_sha256', 'snapshot_id',
        'disclosed_line', 'reviewed_at'})
    eref, fref = n.validate_edition(e), n.validate_fact(f)
    n._require(e['schema'] == n.SEC_EDITION_SCHEMA and f['schema'] == n.SEGMENT_FACT_SCHEMA, 'FACT_SPECIES_INVALID')
    prepared = {'edition': e, 'proposed_fact': f, 'identities': spec['identities'],
        'identity_queries': spec['identity_queries'], 'semantic_review': spec['semantic_review'],
        'identity_continuity': spec['identity_continuity']}
    n._require(adopt_segment_input(prepared, adopted_at=f['known_at'], ruling_raw=ruling_raw,
        theme_sources_raw=theme_sources_raw,
        identity_observed_at=spec['temporal_decision']['identity_observed_at']) == spec, 'SEGMENT_DECISION_MISMATCH')
    owner._validate_continuity(spec['identity_continuity'], PARTIES)
    _identities(spec['identities'], spec['temporal_decision']['identity_observed_at'])
    _identities(identities, datetime.now(timezone.utc).isoformat())
    n._closed(spec['identity_queries'], {'subject'})
    n._require(all(type(x) is str and owner.context._SYMBOL.fullmatch(x) is not None
        for x in spec['identity_queries'].values()), 'IDENTITY_QUERY_INVALID')
    for party in PARTIES:
        n._require(all(identities[party][key] == spec['identities'][party][key]
            for key in owner.SEMANTIC_IDENTITY_FIELDS), 'CURRENT_IDENTITY_CHANGED')
    recorded = spec['identities']
    n._require(f['edition'] == eref.payload() and f['subject_id'] == e['issuer_id']
               and f['disclosure_id'] == e['disclosure_id']
               and f['subject_id'] == identities['subject']['issuer_id']
               and f['subject_identity'] == _digest(recorded['subject'])
               and e['sec_source']['issuer_cik'] == identities['subject']['evidenced_cik'], 'IDENTITY_BINDING_MISMATCH')
    n._require(f['accession'] == e['sec_source']['accession'], 'SEGMENT_ACCESSION_MISMATCH')
    n._require(_digest(spec['semantic_review']) == f['review_revision']
               and spec['semantic_review']['decision'] == 'supported_segment_activity_in_selected_filing'
               and spec['semantic_review']['source_sha256'] == e['source_sha256']
               and spec['semantic_review']['span_sha256'] == e['sec_source']['span_sha256']
               and spec['semantic_review']['snapshot_id'] == e['sec_source']['snapshot_id'],
               'REVIEW_BINDING_MISMATCH')
    n._require(spec['semantic_review']['disclosed_line'] == ruling['permitted_use']['disclosed_line'], 'POLICY_ROLE_MISMATCH')
    n._require(f['span'] == {'start_byte': e['sec_source']['span_start_byte'],
        'end_byte': e['sec_source']['span_end_byte'], 'text_sha256': e['sec_source']['span_sha256']}, 'SEGMENT_EVIDENCE_MISMATCH')
    rows = [r for r in yaml.safe_load(registry_raw)['datasets'] if r.get('dataset_id') == owner.DATASET]
    n._require(len(rows) == 1, 'DATASET_NOT_ADOPTED')
    row = DatasetContract.from_mapping(rows[0])
    n._require(not validate_registry(Registry([row])) and row.owner == 'company-intelligence'
               and row.producer == owner.PRODUCER and row.temporal_profile.value == 'DERIVED'
               and row.status.value in {'PROPOSED', 'PRODUCED'}
               and row.storage == 'private:company-intelligence/state/generations/{sha256}.json'
               and {'computed_at', 'code_version', 'input_cutoffs'} <= set(row.schema), 'DATASET_NOT_ADOPTED')
    # Dataset existence/license text is not the source-purpose grant. The exact
    # separate segment ruling above is mandatory; C01 cannot satisfy it.
    return owner.OwnerSnapshot(code_version, spec_raw, owner.digest(ruling_raw),
        owner.digest(n._canonical(rows[0])), row.status.value, n._canonical(identities))


def _stored_span_ok(span):
    """Fix 9b (B2): a stored span is exactly start_byte, end_byte (int, not bool) and text_sha256 (a digest string)."""
    return (type(span) is dict and set(span) == {'start_byte', 'end_byte', 'text_sha256'}
            and type(span['start_byte']) is int and type(span['end_byte']) is int
            and type(span['text_sha256']) is str)


def _stored_figure_spans_ok(figure_spans):
    """Fix 9b (B2): the stored container holds every figure name, each None or an exact span."""
    return (type(figure_spans) is dict and set(figure_spans) == set(n.SEGMENT_FIGURE_NAMES)
            and all(value is None or _stored_span_ok(value) for value in figure_spans.values()))


def _stored_source_fields_ok(edition):
    """Fix 9b (B2): the stored source fields compared with the body are a digest and an int (not bool)."""
    return (type(edition) is dict and type(edition.get('source_sha256')) is str
            and type(edition.get('source_byte_length')) is int)


class PinnedSegmentSource:
    """Existing publication source interface over the exact retained snapshot.

    No raw-source copy/store is required. Construction does no body I/O; native
    publish_disclosure calls read_source only after exact purpose admission.
    The caller supplies the already provisioned native read-only authority.
    """
    def __init__(self, snapshot, authority):
        from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
        n._require(type(authority) is PinnedSourceAuthority, 'EXACT_NATIVE_AUTHORITY_REQUIRED')
        spec = snapshot.spec
        n._require(type(spec) is dict and type(spec.get('edition')) is dict and type(spec.get('fact')) is dict,
                   'FACT_SPECIES_INVALID')
        self.edition = spec['edition']
        self.fact = spec['fact']
        self.authority = authority
        n._require(self.edition.get('schema') == n.SEC_EDITION_SCHEMA, 'SEC_SOURCE_BINDING_MISMATCH')

    def read_source(self, **binding):
        from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority, gzip_stored_byte_ceiling
        from engine.fundamental_forensics.sec_document_spine import manifest_from_json_bytes
        e = self.edition
        # Fix 9b (B2): every stored value is shape-checked before its first use.
        n._require(_stored_source_fields_ok(e), 'SOURCE_BYTES_MISMATCH')
        edition_reference = n.validate_edition(e)
        n._require(type(e.get('sec_source')) is dict, 'SEC_SOURCE_BINDING_MISMATCH')
        s = e['sec_source']
        n._require(_stored_figure_spans_ok(self.fact.get('figure_spans')), 'SOURCE_SPAN_MISMATCH')
        n._require(binding == dict(disclosure_id=e.get('disclosure_id'), edition_reference=edition_reference,
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
        # The annual-report form gate: the pinned manifest's own form must equal
        # the adopted fact's form_type, else the segment fact is not admitted.
        n._require(m['filing']['form'] == self.fact.get('form_type'), 'SEGMENT_FORM_NOT_ADMITTED')
        read = a.read_archive_document(storage_key=d['storage_key'], expected_receipt=r,
            maximum_bytes=n.MAX_SEC_SOURCE_BYTES,
            maximum_stored_bytes=gzip_stored_byte_ceiling(e['source_byte_length']))
        n._require(read.receipt_sidecar_verified is True, 'NATIVE_SOURCE_REPLAY_REQUIRED')
        # Replay re-verifies every figure span against the pinned bytes, exactly as
        # the activity span is checked: whole-token text, hash and declared sign
        # marker, then value == sign x digits x scale (not only at prepare).
        for name in n.SEGMENT_FIGURE_NAMES:
            span = self.fact['figure_spans'][name]
            if span is not None:
                n._verify_figure_span(name, span, self.fact.get(f'{name}_text'),
                                      self.fact.get(f'{name}_sign'), read.content)
                text, sign, scale = (self.fact.get(f'{name}_text'), self.fact.get(f'{name}_sign'),
                                     self.fact.get(f'{name}_scale'))
                n._require(type(text) is str and n._FIGURE_TEXT.fullmatch(text) is not None
                           and type(sign) is str and sign in n.SEGMENT_FIGURE_SIGNS
                           and type(scale) is str and scale in n.SEGMENT_FIGURE_SCALES,
                           'FIGURE_TEXT_MISMATCH')
                derived = (-1 if sign == '-' else 1) * int(text.replace(',', '')) * n.SEGMENT_FIGURE_SCALES[scale]
                n._require(self.fact.get(name) == derived, 'FIGURE_TEXT_MISMATCH')
        return read.content


def replay_segment_source(snapshot, authority):
    """Replay the pinned source document for one segment snapshot.

    The proposal path calls this before any ledger write. The disclosure store
    does not admit a segment fact, so ``publish_disclosure`` never reaches its
    own figure check for one. One bounded read of the pinned document; every
    failure is a ``DisclosureError``.
    """
    spec = snapshot.spec
    n._require(type(spec) is dict and type(spec.get('edition')) is dict and type(spec.get('fact')) is dict,
               'FACT_SPECIES_INVALID')
    e, f = spec['edition'], spec['fact']
    n._require(_stored_source_fields_ok(e), 'SOURCE_BYTES_MISMATCH')
    n._require(f.get('schema') == n.SEGMENT_FACT_SCHEMA and e.get('schema') == n.SEC_EDITION_SCHEMA
               and f.get('edition') == n.validate_edition(e).payload(), 'FACT_SPECIES_INVALID')
    # Fix 9b (B2): every stored value read below is shape-checked before its first use.
    n._require(_stored_span_ok(f.get('span')), 'SOURCE_SPAN_MISMATCH')
    n._require(_stored_figure_spans_ok(f.get('figure_spans')), 'SOURCE_SPAN_MISMATCH')
    body = PinnedSegmentSource(snapshot, authority).read_source(
        disclosure_id=e.get('disclosure_id'), edition_reference=n.validate_edition(e),
        source_sha256=e['source_sha256'], expected_byte_length=e['source_byte_length'],
        max_byte_length=n.MAX_SEC_SOURCE_BYTES)
    n._require(type(body) is bytes and len(body) == e['source_byte_length']
               and sha256(body).hexdigest() == e['source_sha256'], 'SOURCE_BYTES_MISMATCH')
    span = f['span']
    # Fix 9 (R9-5): stored offsets are int and not bool before any arithmetic or slicing, so no
    # TypeError or ValueError can leave replay for a malformed stored row.
    n._require(0 <= span['start_byte'] < span['end_byte'] <= len(body), 'SOURCE_SPAN_MISMATCH')
    n._require(sha256(body[span['start_byte']:span['end_byte']]).hexdigest() == span['text_sha256'],
               'SOURCE_SPAN_MISMATCH')
    # Prepare's containment check, repeated: every figure span lies inside the
    # activity span (relative to its start, within the hash-verified span bytes).
    main_len = len(body[span['start_byte']:span['end_byte']])
    for name in n.SEGMENT_FIGURE_NAMES:
        figure = f['figure_spans'][name]
        if figure is not None:
            n._require(0 <= figure['start_byte'] - span['start_byte']
                       < figure['end_byte'] - span['start_byte'] <= main_len, 'SOURCE_SPAN_MISMATCH')
    return None