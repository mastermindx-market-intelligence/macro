"""Attended native publication; same-operation reconciliation, never retry loops."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from . import issuer_disclosures as native
from . import issuer_disclosure_owner as owner

APPEND_MODE = 'APPEND_CURRENT_MEMBER'
APPEND_INTENT_SCHEMA = 'company_intelligence.native_publication_intent/v2'
_INTENT_KEYS = {'schema', 'manifest', 'manifest_reference', 'expected_current_version',
                'expected_current_sha256', 'mode'}
_APPEND_KEYS = _INTENT_KEYS | {'prior_manifest', 'preserved_members', 'collection', 'collection_reference'}


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
        # Both the protected decisions and the full current identity qualification
        # must stay stable for the whole operation; a provenance-only refresh of
        # either MU or NVDA mid-operation changes identity_binding and refuses.
        fresh = self.source.snapshot()
        native._require(fresh.bindings == self.snapshot.bindings
                        and fresh.identity_binding == self.snapshot.identity_binding,
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


def _preserved_members(state, prior, preserved_sources):
    native._require(prior.data is not None, 'APPEND_CURRENT_REQUIRED')
    _, reference, manifest = owner.read_current_manifest(state, pointer_raw=prior.data)
    if manifest.get('schema') == owner.COLLECTION_SCHEMA:
        owner.collection_components(state, manifest)
        return reference, manifest['members']
    owner.validate_component(manifest)
    schema = manifest['fact']['schema']
    native._require(type(preserved_sources) is dict and schema in preserved_sources, 'PRESERVED_SOURCE_REQUIRED')
    snapshot = owner.qualify_component(preserved_sources[schema], manifest)
    return reference, [owner.member_descriptor(snapshot, reference)]


def _collection(snapshot, manifest_reference, members, computed_at):
    collection = {'schema': owner.COLLECTION_SCHEMA, 'computed_at': computed_at,
        'members': sorted([*members, owner.member_descriptor(snapshot, manifest_reference)], key=lambda m: m['fact_id'])}
    owner.validate_collection(collection)
    return collection


def prepare_publication(source, state, *, expected_current_version, mode=None, preserved_sources=None):
    """Metadata-only candidate preparation; reserve this exact intent durably."""
    snapshot = source.snapshot()
    prior = state.get_bytes_strict_bounded_versioned(owner.CURRENT_KEY, native.MAX_OBJECT_BYTES)
    native._require(prior.version == expected_current_version, 'PUBLICATION_PREDECESSOR_CHANGED')
    manifest = owner.make_manifest(snapshot, datetime.now(timezone.utc).isoformat())
    intent = {'schema': 'company_intelligence.native_publication_intent/v1',
            'manifest': manifest, 'manifest_reference': owner.object_ref(native._canonical(manifest)),
            'expected_current_version': prior.version,
            'expected_current_sha256': None if prior.data is None else owner.digest(prior.data),
            'mode': 'PROMOTE_CURRENT' if snapshot.dataset_status == 'PRODUCED' else 'STAGE_MEMBERS'}
    if mode is not None:
        native._require(mode == APPEND_MODE and snapshot.dataset_status == 'PRODUCED', 'PUBLICATION_MODE_INVALID')
        prior_reference, members = _preserved_members(state, prior, preserved_sources)
        collection = _collection(snapshot, intent['manifest_reference'], members, manifest['computed_at'])
        intent.update(schema=APPEND_INTENT_SCHEMA, mode=APPEND_MODE, prior_manifest=prior_reference,
            preserved_members=members, collection=collection,
            collection_reference=owner.object_ref(native._canonical(collection)))
        native._require(state.get_bytes_strict_bounded_versioned(owner.CURRENT_KEY, native.MAX_OBJECT_BYTES) == prior,
                        'PUBLICATION_PREDECESSOR_CHANGED')
    # Snapshot return bytes now, not caller-owned collection/source mappings.
    return native._decode(native._canonical(intent))


def validate_publication_intent(source, state, intent, *, preserved_sources=None):
    """Same bounded validation for preflight and publication; no effects."""
    snapshot = source.snapshot()
    append = type(intent) is dict and intent.get('schema') == APPEND_INTENT_SCHEMA
    native._closed(intent, _APPEND_KEYS if append else _INTENT_KEYS)
    intent = native._decode(native._canonical(intent))
    manifest = intent['manifest']
    native._require(manifest == owner.make_manifest(snapshot, manifest['computed_at'])
        and intent['manifest_reference'] == owner.object_ref(native._canonical(manifest)), 'PUBLICATION_INTENT_CHANGED')
    if append:
        native._require(intent['mode'] == APPEND_MODE and snapshot.dataset_status == 'PRODUCED', 'PUBLICATION_INTENT_CHANGED')
    else:
        native._require(intent['schema'] == 'company_intelligence.native_publication_intent/v1'
            and intent['mode'] == ('PROMOTE_CURRENT' if snapshot.dataset_status == 'PRODUCED' else 'STAGE_MEMBERS'),
            'PUBLICATION_INTENT_CHANGED')
    prior = state.get_bytes_strict_bounded_versioned(owner.CURRENT_KEY, native.MAX_OBJECT_BYTES)
    native._require(prior.version == intent['expected_current_version'] and
        (None if prior.data is None else owner.digest(prior.data)) == intent['expected_current_sha256'],
        'PUBLICATION_PREDECESSOR_CHANGED')
    if append:
        reference, members = _preserved_members(state, prior, preserved_sources)
        expected = _collection(snapshot, intent['manifest_reference'], members, manifest['computed_at'])
        native._require(intent['prior_manifest'] == reference and intent['preserved_members'] == members
            and intent['collection'] == expected
            and intent['collection_reference'] == owner.object_ref(native._canonical(expected)), 'PUBLICATION_INTENT_CHANGED')
    return snapshot, prior


def publish_generation(source, state, artifacts, source_reader_factory, *, intent, preserved_sources=None):
    """One operation: verify authority, publish members, verify, then CAS current.

    Source and Store capabilities are supplied by the attended owner. A returned
    failure never authorizes retry, a replacement generation or another carrier.
    The CLI durably reserves its operation receipt before invoking this function.
    """
    # Freeze caller metadata before invoking any callback. No replacement clock
    # or generation is minted after the operation reservation.
    intent = native._decode(native._canonical(intent))
    snapshot, prior = validate_publication_intent(source, state, intent, preserved_sources=preserved_sources)
    manifest = intent['manifest']
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
        'identity_binding': snapshot.identity_binding,
        'native_result': result, 'manifest_written': manifest_written,
        'automatic_retry_permitted': False, 'production_accepted': False}
    if intent['mode'] == 'STAGE_MEMBERS':
        # Concrete retained-input production can justify a subsequent protected
        # registry amendment. This stage never creates a serving pointer.
        return {**receipt, 'status': 'MEMBERS_OBSERVED_NOT_ADOPTED', 'pointer_written': False}
    append = intent['mode'] == APPEND_MODE
    if append:
        collection_raw = native._canonical(intent['collection'])
        collection_reference = intent['collection_reference']
        collection_written = _put_observed(state, 'generations/' + collection_reference['sha256'] + '.json', collection_raw, None)
        # Revalidate the preserved descriptors and exact prior selection after
        # all immutable writes, immediately before the only pointer CAS.
        validate_publication_intent(source, state, intent, preserved_sources=preserved_sources)
        authority.resolve(request)
        pointer_reference = collection_reference
        receipt.update(collection_reference=collection_reference, collection_written=collection_written,
                       preserved_members=intent['preserved_members'])
    else:
        pointer_reference = reference
    pointer = native._canonical({'schema': owner.POINTER_SCHEMA, 'manifest': pointer_reference})
    pointer_written = _put_observed(state, owner.CURRENT_KEY, pointer, prior.version)
    # A concurrent revocation after the commit leaves an unservable pointer;
    # never certify it as currently adopted just because CAS succeeded.
    try:
        current = owner.CurrentDisclosureOwner(source, state,
            supplier_sources={spec['fact']['schema']: source}) if append else owner.CurrentDisclosureOwner(source, state)
        final = native.read_disclosure(artifacts, current, request)
        native._require(final == observed, 'PUBLICATION_FINAL_READBACK_MISMATCH')
        # A fresh observation may requalify a later request, but this operation
        # must finish under the exact identity binding that admitted its writes.
        native._require(source.snapshot().identity_binding == snapshot.identity_binding,
                        'PUBLICATION_IDENTITY_CONTINUITY_BROKEN')
    except native.DisclosureError as exc:
        # The pointer CAS has already succeeded. Every subsequent refusal needs
        # same-operation reconciliation, even when its own read failed closed.
        raise native.DisclosureError(exc.code, effect_unknown=True) from None
    except Exception:
        raise native.DisclosureError('PUBLICATION_FINAL_OBSERVATION_FAILED',
                                     effect_unknown=True) from None
    return {**receipt, 'status': 'COMMITTED_OBSERVED',
            'pointer_written': pointer_written, 'private_response_sha256': owner.digest(native._canonical(final)),
            'automatic_retry_permitted': False, 'production_accepted': False}
