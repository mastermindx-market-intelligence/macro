"""Current native disclosure owner: protected decisions, metadata, then artifacts.

The dataset registry and committed decisions remain the authority. The private
current pointer selects their already-published immutable projection; it cannot
grant purpose, identity or correction authority. This module never chooses R2
credentials, retrieves a URL, creates directories or starts a producer.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from . import issuer_disclosures as native
from . import current_company_context as context
from .current_context_runtime import CommittedCompanyContextOwner
from .issuer_disclosure_selection import IssuerSelection, SelectionEntry
from ..research_vault.r2_store import LocalStore, VersionedBytes
from lib.dataos.registry import DatasetContract, Registry, validate_registry

PURPOSE = 'private_company_intelligence_context'
AUDIENCE = 'company_intelligence_entitled'
DATASET = 'company_intelligence.issuer_disclosure_generations'
PRODUCER = 'scripts/publish_company_disclosure.py'
MANIFEST_SCHEMA = 'company_intelligence.issuer_disclosure_generation/v1'
POINTER_SCHEMA = 'company_intelligence.issuer_disclosure_current/v1'
BASE = 'research/theme_graph/issuer_disclosures_20261011/'
SPEC_PATH = BASE + 'C01_NATIVE_OWNER.json'
RULING_PATH = BASE + 'C01_CHAIRMAN_SOURCE_PURPOSE_RULING.json'
REGISTRY_PATH = 'config/dataset_registry.yml'
CURRENT_KEY = 'current.json'


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def object_ref(raw: bytes) -> dict:
    return {'sha256': digest(raw), 'byte_length': len(raw)}


def bounded_file(root: Path, key: str, maximum: int) -> bytes | None:
    """No-follow descriptor walk, regular files only, cap before allocation.

    Metadata reads need an unknown-length mode; LocalStore's expected-length
    mode remains the artifact verifier. Missing roots refuse; a missing key is
    the only absence. No constructor or read has mkdir/write side effects.
    """
    native._require(type(maximum) is int and 0 < maximum <= native.MAX_SOURCE_BYTES,
                    'READ_BOUND_INVALID')
    parts = key.split('/')
    native._require(key and not key.startswith('/') and all(
        p not in {'', '.', '..'} and '\\' not in p for p in parts), 'KEY_INVALID')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors = [os.open('/', flags)]
    try:
        for part in Path(os.path.abspath(root)).parts[1:]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        try:
            for part in parts[:-1]:
                descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=descriptors[-1])
        except FileNotFoundError:
            return None
        descriptors.append(fd)
        before = os.fstat(fd)
        native._require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum,
                        'READ_OBJECT_INVALID')
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(fd)
        native._require(len(raw) == before.st_size and
                        (before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                        (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'READ_OBJECT_CHANGED')
        return bytes(raw)
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


class ReadOnlyLocalObjects:
    """Read capability only; deployment must additionally enforce OS read-only."""
    def __init__(self, root: Path):
        self.root = Path(root)

    def get_bytes_strict_bounded(self, key, maximum_bytes=None, *,
                                expected_byte_length=None, max_byte_length=None):
        maximum = maximum_bytes if maximum_bytes is not None else max_byte_length
        raw = bounded_file(self.root, key, maximum)
        if raw is not None and expected_byte_length is not None:
            native._require(len(raw) == expected_byte_length, 'READ_LENGTH_MISMATCH')
        return raw

    def get_bytes_strict_bounded_versioned(self, key, maximum_bytes):
        raw = self.get_bytes_strict_bounded(key, maximum_bytes)
        return VersionedBytes(raw, None if raw is None else LocalStore._local_version(raw))


def _json(raw: bytes) -> dict:
    native._require(type(raw) is bytes and 0 < len(raw) <= native.MAX_OBJECT_BYTES,
                    'OWNER_RECORD_INVALID')
    value = json.loads(raw, object_pairs_hook=native._pairs,
                       parse_constant=lambda _: native._require(False, 'JSON_INVALID'))
    native._require(type(value) is dict, 'OWNER_RECORD_INVALID')
    return value


@dataclass(frozen=True)
class OwnerSnapshot:
    code_version: str
    spec_bytes: bytes
    ruling_revision: str
    adoption_revision: str
    dataset_status: str

    @property
    def spec(self):
        return _json(self.spec_bytes)

    @property
    def bindings(self):
        return {'spec': digest(self.spec_bytes), 'purpose': self.ruling_revision,
                'adoption': self.adoption_revision}


def qualify_records(code_version: str, spec_raw: bytes, ruling_raw: bytes,
                    registry_raw: bytes, identities: dict) -> OwnerSnapshot:
    """Interpret original records, never an Admission or grant from a caller."""
    import yaml
    native._require(re.fullmatch('[0-9a-f]{40}', code_version) is not None, 'CODE_VERSION_INVALID')
    spec, ruling = _json(spec_raw), _json(ruling_raw)
    native._closed(spec, {'schema', 'case_id', 'ruling_reference', 'edition', 'fact',
                         'identities', 'temporal_decision', 'correction_decision', 'semantic_review'})
    native._require(spec['schema'] == 'company_intelligence.native_owner_decision/v1'
                    and spec['case_id'] == ruling['case_id'] == 'C01-micron-planned-product-integration'
                    and spec['ruling_reference'] == object_ref(ruling_raw), 'RULING_BINDING_MISMATCH')
    native._require(ruling['decision'] == 'covered' and ruling['rights_evidence_task_complete'] is True
                    and ruling['evidence_kind'] == 'direct_chairman_source_rights_confirmation',
                    'PURPOSE_NOT_ADMITTED')
    use, source = ruling['permitted_use'], ruling['source']
    native._require((use['purpose'], use['audience']) == (PURPOSE, AUDIENCE)
                    and use['paid_product_display'] is True and use['fact_retention'] is True
                    and use['source_quotation'] is False and use['reviewer_text'] is False,
                    'PURPOSE_NOT_ADMITTED')
    edition, fact = spec['edition'], spec['fact']
    eref, fref = native.validate_edition(edition), native.validate_fact(fact)
    native._require(fact['edition'] == eref.payload() and fact['subject_id'] == edition['issuer_id']
                    and fact['disclosure_id'] == edition['disclosure_id'], 'SOURCE_BINDING_MISMATCH')
    native._require(all(edition[k] == source[k] for k in
        ['source_key', 'published_date', 'published_at', 'publication_precision'])
        and (edition['source_sha256'], edition['source_byte_length']) ==
        (source['sha256'], source['byte_length']), 'RULING_SOURCE_MISMATCH')
    native._require(all(fact[k] == use[k] for k in
        ['kind', 'lifecycle', 'product', 'platform', 'amount', 'economic_share']), 'RULING_FACT_MISMATCH')
    native._require(set(identities) == set(spec['identities']) == {'MU', 'NVDA'}
                    and identities == spec['identities'], 'CURRENT_IDENTITY_CHANGED')
    for symbol, party, field in [('MU', 'subject_id', 'subject_identity'),
                                ('NVDA', 'object_id', 'object_identity')]:
        identity = identities[symbol]
        native._require(identity['schema'] == 'company_intelligence.current_issuer_identity/v1'
                        and identity['identity_mode'] == 'current'
                        and identity['issuer_id'] == fact[party]
                        and digest(native._canonical(identity)) == fact[field], 'IDENTITY_BINDING_MISMATCH')
    temporal, correction = spec['temporal_decision'], spec['correction_decision']
    native._require(temporal == {'identity_mode': 'current', 'historical_admitted': False,
                    'published_date': edition['published_date'], 'published_at': edition['published_at'],
                    'publication_precision': edition['publication_precision'],
                    'edition_known_at': edition['known_at'], 'fact_known_at': fact['known_at']},
                    'TEMPORAL_DECISION_INVALID')
    native._require(correction == {'status': 'current', 'edition': eref.payload(), 'fact': fref.payload()},
                    'CORRECTION_DECISION_INVALID')
    native._require(digest(native._canonical(spec['semantic_review'])) == fact['review_revision'],
                    'REVIEW_BINDING_MISMATCH')
    payload = yaml.safe_load(registry_raw)
    rows = [r for r in payload['datasets'] if r.get('dataset_id') == DATASET]
    native._require(len(rows) == 1, 'DATASET_NOT_ADOPTED')
    row = DatasetContract.from_mapping(rows[0])
    native._require(not validate_registry(Registry([row])) and row.owner == 'company-intelligence'
                    and row.producer == PRODUCER and row.temporal_profile.value == 'DERIVED'
                    and row.status.value in {'PROPOSED', 'PRODUCED'}
                    and row.storage == 'private:company-intelligence/state/generations/{sha256}.json',
                    'DATASET_NOT_ADOPTED')
    # PROPOSED permits staged publication only; serving requires source-owned
    # PRODUCED status plus exact current presence. A pointer cannot adopt a row.
    native._require({'computed_at', 'code_version', 'input_cutoffs'} <= set(row.schema),
                    'DATASET_CLOCKS_MISSING')
    return OwnerSnapshot(code_version, spec_raw, digest(ruling_raw),
                         digest(native._canonical(rows[0])), row.status.value)


class CommittedDisclosureSource:
    """Fresh installed protected decisions plus the incumbent identity owner."""
    def __init__(self, repo: Path, identity_owner=None):
        self.git = CommittedCompanyContextOwner(repo)
        self.identity_owner = identity_owner or self.git

    def accepts_revision(self, revision: str) -> bool:
        native._require(re.fullmatch('[0-9a-f]{40}', revision) is not None, 'CODE_VERSION_INVALID')
        self.git._git('merge-base', '--is-ancestor', revision, self.git._head())
        return True

    def snapshot(self) -> OwnerSnapshot:
        head = self.git._head()
        self.git._git('merge-base', '--is-ancestor', head, 'refs/remotes/origin/main')
        blobs = self.git._read(self.git._objects(head, (SPEC_PATH, RULING_PATH, REGISTRY_PATH)))
        identities = {symbol: context.read_company_context(self.identity_owner, symbol,
            purpose=PURPOSE, audience=AUDIENCE)['identity_receipt'] for symbol in ('MU', 'NVDA')}
        result = qualify_records(head, blobs[SPEC_PATH], blobs[RULING_PATH], blobs[REGISTRY_PATH], identities)
        native._require(self.git._head() == head, 'SOURCE_GENERATION_CHANGED')
        return result


def make_manifest(snapshot: OwnerSnapshot, computed_at: str) -> dict:
    spec = snapshot.spec
    native._require(native._instant(spec['fact']['known_at']) <= native._instant(computed_at)
                    <= datetime.now(timezone.utc), 'GENERATION_TIME_INVALID')
    return {'schema': MANIFEST_SCHEMA, 'dataset_id': DATASET, 'temporal_profile': 'DERIVED',
            'computed_at': computed_at, 'code_version': snapshot.code_version,
            'input_cutoffs': {'source_known_at': spec['edition']['known_at'],
                             'fact_known_at': spec['fact']['known_at']},
            'decisions': snapshot.bindings,
            'edition': native.validate_edition(spec['edition']).payload(),
            'fact': native.validate_fact(spec['fact']).payload()}


def admission(snapshot: OwnerSnapshot, manifest: dict, request: native.Request,
              operation: str = 'read') -> native.Admission:
    spec, fact = snapshot.spec, snapshot.spec['fact']
    native._require(request.mode == 'current' and request.fact_id == fact['fact_id']
                    and (request.purpose, request.audience) == (PURPOSE, AUDIENCE), 'SOURCE_NOT_ADMITTED')
    identity = spec['identities']['MU']
    raw_identity = native._canonical(identity)
    return native.Admission(request, native.validate_fact(fact), native.validate_edition(spec['edition']),
        digest(native._canonical(manifest)), DATASET, 'DERIVED', snapshot.adoption_revision,
        snapshot.ruling_revision, digest(native._canonical(spec['identities'])),
        digest(native._canonical(spec['temporal_decision'])), digest(native._canonical(spec['correction_decision'])),
        fact['known_at'], spec['edition']['publication_precision'], 'current', native._FIELDS,
        operation, native.SubjectIdentityBinding(identity['issuer_id'], identity['evidenced_cik'],
            identity['schema'], digest(raw_identity), len(raw_identity), fact['subject_identity']))


class CurrentDisclosureOwner:
    """Metadata-only resolver. It has no publication capability or artifact Store."""
    def __init__(self, source, state):
        self.source, self.state = source, state

    def _current(self):
        snapshot = self.source.snapshot()
        native._require(snapshot.dataset_status == 'PRODUCED', 'DATASET_NOT_PRODUCED')
        pointer_raw = self.state.get_bytes_strict_bounded(CURRENT_KEY, native.MAX_OBJECT_BYTES)
        pointer = native._decode(pointer_raw)
        native._closed(pointer, {'schema', 'manifest'})
        native._require(pointer['schema'] == POINTER_SCHEMA, 'CURRENT_POINTER_INVALID')
        ref = native._closed(pointer['manifest'], {'sha256', 'byte_length'})
        native._digest(ref['sha256']); native._integer(ref['byte_length'], 1, native.MAX_OBJECT_BYTES)
        raw = self.state.get_bytes_strict_bounded('generations/' + ref['sha256'] + '.json',
            expected_byte_length=ref['byte_length'], max_byte_length=native.MAX_OBJECT_BYTES)
        native._require(raw is not None and object_ref(raw) == ref, 'CURRENT_MANIFEST_MISMATCH')
        manifest = native._decode(raw)
        native._require(self.source.accepts_revision(manifest['code_version']), 'GENERATION_CODE_INVALID')
        expected = make_manifest(replace(snapshot, code_version=manifest['code_version']), manifest['computed_at'])
        native._require(manifest == expected, 'CURRENT_DECISION_CHANGED')
        native._require(self.source.snapshot().bindings == snapshot.bindings and
            self.state.get_bytes_strict_bounded(CURRENT_KEY, native.MAX_OBJECT_BYTES) == pointer_raw,
            'CURRENT_GENERATION_CHANGED')
        return snapshot, manifest

    def resolve(self, request):
        if (type(request) is not native.Request or request.mode != 'current'
                or (request.purpose, request.audience) != (PURPOSE, AUDIENCE)):
            return None
        snapshot, manifest = self._current()
        return admission(snapshot, manifest, request)

    def authorize_publication(self, request, candidate):
        return None

    def resolve_issuer(self, issuer_id, purpose, audience):
        if (purpose, audience) != (PURPOSE, AUDIENCE):
            return None
        snapshot, manifest = self._current()
        fact = snapshot.spec['fact']
        if issuer_id != fact['subject_id']:
            return None
        a = admission(snapshot, manifest, native.Request(fact['fact_id'], purpose, audience))
        b = a.subject_binding
        return IssuerSelection(b.issuer_id, b.evidenced_cik, b.snapshot_schema,
            b.snapshot_sha256, b.snapshot_byte_length, a.generation, purpose, audience,
            (SelectionEntry(fact['fact_id'], a.reference, a.edition),))
