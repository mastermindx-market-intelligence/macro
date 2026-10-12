"""Attended native publication; same-operation reconciliation, never retry loops."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from . import issuer_disclosures as native
from . import issuer_disclosure_owner as owner


class RetainedFileSource:
    """Producer-only source capability, exactly bound before the first body read."""
    def __init__(self, snapshot, root: Path, key: str):
        self.edition = snapshot.spec['edition']
        self.root, self.key = Path(root), key

    def read_source(self, **binding):
        e = self.edition
        expected = dict(disclosure_id=e['disclosure_id'], edition_reference=native.validate_edition(e),
            source_sha256=e['source_sha256'], expected_byte_length=e['source_byte_length'],
            max_byte_length=native.MAX_SOURCE_BYTES)
        native._require(binding == expected, 'RETAINED_SOURCE_BINDING_MISMATCH')
        raw = owner.bounded_file(self.root, self.key, native.MAX_SOURCE_BYTES)
        native._require(raw is not None and len(raw) == e['source_byte_length']
                        and owner.digest(raw) == e['source_sha256'], 'RETAINED_SOURCE_MISMATCH')
        return raw


class _PublicationAuthority:
    def __init__(self, source, state, snapshot, manifest, prior):
        self.source, self.state, self.snapshot, self.manifest, self.prior = source, state, snapshot, manifest, prior

    def resolve(self, request):
        native._require(self.source.snapshot().bindings == self.snapshot.bindings,
                        'PUBLICATION_AUTHORITY_CHANGED')
        native._require(self.state.get_bytes_strict_bounded_versioned(
            owner.CURRENT_KEY, native.MAX_OBJECT_BYTES) == self.prior, 'PUBLICATION_PREDECESSOR_CHANGED')
        return owner.admission(self.snapshot, self.manifest, request)

    def authorize_publication(self, request, candidate):
        admitted = self.resolve(request)
        native._require(admitted.reference == candidate, 'PUBLICATION_CANDIDATE_CHANGED')
        return replace(admitted, operation='publish')


def _put_observed(store, key, raw, expected_version):
    raised = False
    try:
        changed = store.put_bytes_strict_conditional(key, raw, expected_version=expected_version,
                                                     content_type='application/json')
    except Exception:
        raised, changed = True, None
    try:
        result = store.get_bytes_strict_bounded_versioned(key, native.MAX_OBJECT_BYTES)
    except Exception:
        raise native.DisclosureError('PUBLICATION_EFFECT_UNKNOWN', effect_unknown=True) from None
    if result.data != raw:
        raise native.DisclosureError('PUBLICATION_EFFECT_UNKNOWN' if raised else 'PUBLICATION_CAS_CONFLICT',
                                     effect_unknown=raised)
    return bool(changed or raised)


def prepare_publication(source, state, *, expected_current_version):
    """Metadata-only candidate preparation; reserve this exact intent durably."""
    snapshot = source.snapshot()
    prior = state.get_bytes_strict_bounded_versioned(owner.CURRENT_KEY, native.MAX_OBJECT_BYTES)
    native._require(prior.version == expected_current_version, 'PUBLICATION_PREDECESSOR_CHANGED')
    manifest = owner.make_manifest(snapshot, datetime.now(timezone.utc).isoformat())
    return {'schema': 'company_intelligence.native_publication_intent/v1',
            'manifest': manifest, 'manifest_reference': owner.object_ref(native._canonical(manifest)),
            'expected_current_version': prior.version,
            'expected_current_sha256': None if prior.data is None else owner.digest(prior.data),
            'mode': 'PROMOTE_CURRENT' if snapshot.dataset_status == 'PRODUCED' else 'STAGE_MEMBERS'}


def publish_generation(source, state, artifacts, source_reader_factory, *, intent):
    """One operation: verify authority, publish members, verify, then CAS current.

    Source and Store capabilities are supplied by the attended owner. A returned
    failure never authorizes retry, a replacement generation or another carrier.
    The CLI durably reserves its operation receipt before invoking this function.
    """
    snapshot = source.snapshot()
    native._closed(intent, {'schema', 'manifest', 'manifest_reference', 'expected_current_version',
                           'expected_current_sha256', 'mode'})
    # Freeze caller metadata before invoking any callback. No replacement clock
    # or generation is minted after the operation reservation.
    intent = native._decode(native._canonical(intent))
    manifest = intent['manifest']
    native._require(intent['schema'] == 'company_intelligence.native_publication_intent/v1'
        and manifest == owner.make_manifest(snapshot, manifest['computed_at'])
        and intent['manifest_reference'] == owner.object_ref(native._canonical(manifest))
        and intent['mode'] == ('PROMOTE_CURRENT' if snapshot.dataset_status == 'PRODUCED' else 'STAGE_MEMBERS'),
        'PUBLICATION_INTENT_CHANGED')
    prior = state.get_bytes_strict_bounded_versioned(owner.CURRENT_KEY, native.MAX_OBJECT_BYTES)
    native._require(prior.version == intent['expected_current_version'] and
        (None if prior.data is None else owner.digest(prior.data)) == intent['expected_current_sha256'],
        'PUBLICATION_PREDECESSOR_CHANGED')
    state.validate_strict_conditional_write_capability()
    spec = snapshot.spec
    request = native.Request(spec['fact']['fact_id'], owner.PURPOSE, owner.AUDIENCE)
    authority = _PublicationAuthority(source, state, snapshot, manifest, prior)
    # Factory is producer-owned. No source bytes may be read by its constructor.
    source_reader = source_reader_factory(snapshot)
    result = native.publish_disclosure(artifacts, authority, request, edition=spec['edition'],
                                      fact=spec['fact'], source_reader=source_reader)
    # This read proves winning identity/revision bindings as well as both blobs.
    observed = native.read_disclosure(artifacts, authority, request)
    native._require(observed['generation'] == owner.digest(native._canonical(manifest)),
                    'PUBLICATION_READBACK_MISMATCH')
    authority.resolve(request)
    raw = native._canonical(manifest)
    reference = owner.object_ref(raw)
    manifest_written = _put_observed(state, 'generations/' + reference['sha256'] + '.json', raw, None)
    # Recheck after the immutable write and immediately before the commit point.
    authority.resolve(request)
    receipt = {'schema': 'company_intelligence.native_publication_receipt/v1',
        'generation': reference['sha256'], 'intent': intent,
        'source_code_version': snapshot.code_version, 'decisions': snapshot.bindings,
        'native_result': result, 'manifest_written': manifest_written,
        'automatic_retry_permitted': False, 'production_accepted': False}
    if intent['mode'] == 'STAGE_MEMBERS':
        # Concrete retained-input production can justify a subsequent protected
        # registry amendment. This stage never creates a serving pointer.
        return {**receipt, 'status': 'MEMBERS_OBSERVED_NOT_ADOPTED', 'pointer_written': False}
    pointer = native._canonical({'schema': owner.POINTER_SCHEMA, 'manifest': reference})
    pointer_written = _put_observed(state, owner.CURRENT_KEY, pointer, prior.version)
    # A concurrent revocation after the commit leaves an unservable pointer;
    # never certify it as currently adopted just because CAS succeeded.
    current = owner.CurrentDisclosureOwner(source, state)
    final = native.read_disclosure(artifacts, current, request)
    native._require(final == observed, 'PUBLICATION_FINAL_READBACK_MISMATCH')
    return {**receipt, 'status': 'COMMITTED_OBSERVED',
            'pointer_written': pointer_written, 'private_response_sha256': owner.digest(native._canonical(final)),
            'automatic_retry_permitted': False, 'production_accepted': False}
