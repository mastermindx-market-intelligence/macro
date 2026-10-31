"""Current native disclosure owner: protected decisions, metadata, then artifacts.

The dataset registry and committed decisions remain the authority. The private
current pointer selects their already-published immutable projection; it cannot
grant purpose, identity or correction authority. This module never chooses R2
credentials, retrieves a URL, creates directories or starts a producer.

Identity continuity: the recorded C01 receipts inside the protected
specification stay byte-exact and continue to bind the native fact decision
digests. A separate, explicit, versioned continuity policy may admit a fresher
current observation of the same semantic identity whose only drift is
provenance (source commit and reference Parquet digests). Absence of the
policy keeps the original exact-equality contract; there is no generic
relaxation and no silent fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
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
COLLECTION_SCHEMA = 'company_intelligence.issuer_disclosure_collection/v1'
MAX_CURRENT_MEMBERS = 16
POINTER_SCHEMA = 'company_intelligence.issuer_disclosure_current/v1'
BASE = 'research/theme_graph/issuer_disclosures_20261011/'
SPEC_PATH = BASE + 'C01_NATIVE_OWNER.json'
RULING_PATH = BASE + 'C01_CHAIRMAN_SOURCE_PURPOSE_RULING.json'
REGISTRY_PATH = 'config/dataset_registry.yml'
CURRENT_KEY = 'current.json'
OWNER_SCHEMA_V1 = 'company_intelligence.native_owner_decision/v1'
OWNER_SCHEMA_V2 = 'company_intelligence.native_owner_decision/v2'
CONTINUITY_SCHEMA = 'company_intelligence.identity_continuity_policy/v1'
CONTINUITY_BINDING_SCHEMA = 'company_intelligence.identity_continuity_binding/v1'
# Semantic/evidence fields must match the recorded decision exactly; only the
# provenance fields may refresh, and only under the explicit v2 policy.
SEMANTIC_IDENTITY_FIELDS = ('schema', 'identity_mode', 'issuer_id', 'evidenced_cik',
                            'evidence_source', 'evidence_snapshot')
PROVENANCE_IDENTITY_FIELDS = ('source_commit', 'sources')
IDENTITY_SOURCES = ('security_master', 'vendor_aliases', 'issuer_master')
IDENTITY_PARTIES = ('MU', 'NVDA')


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


def _validate_identity_receipt(receipt: dict) -> None:
    """Closed receipt shape; unknown or malformed identity fields refuse."""
    native._closed(receipt, {'schema', 'identity_mode', 'issuer_id', 'evidenced_cik',
                             'source_commit', 'sources', 'evidence_source', 'evidence_snapshot'})
    native._require(receipt['schema'] == context.RECEIPT_SCHEMA
                    and receipt['identity_mode'] == 'current'
                    and type(receipt['issuer_id']) is str and bool(receipt['issuer_id'])
                    and type(receipt['source_commit']) is str
                    and re.fullmatch('[0-9a-f]{40}', receipt['source_commit']) is not None
                    and type(receipt['evidenced_cik']) is str
                    and re.fullmatch('[0-9]{10}', receipt['evidenced_cik']) is not None
                    and int(receipt['evidenced_cik']) > 0, 'IDENTITY_RECEIPT_INVALID')
    sources = receipt['sources']
    native._closed(sources, set(IDENTITY_SOURCES))
    for name in IDENTITY_SOURCES:
        reference = native._closed(sources[name], {'sha256', 'byte_length'})
        native._digest(reference['sha256'])
        native._integer(reference['byte_length'], 1, context.MAX_REFERENCE_BYTES)
    native._require(type(receipt['evidence_source']) is str and bool(receipt['evidence_source'])
                    and type(receipt['evidence_snapshot']) is str
                    and re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', receipt['evidence_snapshot']) is not None,
                    'IDENTITY_RECEIPT_INVALID')
    try:
        valid_date = date.fromisoformat(receipt['evidence_snapshot']).isoformat() == receipt['evidence_snapshot']
    except ValueError:
        valid_date = False
    native._require(valid_date, 'IDENTITY_RECEIPT_INVALID')


def _validate_continuity(policy: dict, parties: tuple[str, ...] = IDENTITY_PARTIES) -> None:
    """The policy is literal: no free-form fields, no other policy name."""
    native._require(type(policy) is dict and set(policy) == {'schema', 'policy', 'semantic_fields', 'provenance_fields', 'parties'},
                    'IDENTITY_CONTINUITY_POLICY_INVALID')
    native._require(policy['schema'] == CONTINUITY_SCHEMA
                    and policy['policy'] == 'provenance_refresh'
                    and type(policy['semantic_fields']) is list
                    and policy['semantic_fields'] == list(SEMANTIC_IDENTITY_FIELDS)
                    and type(policy['provenance_fields']) is list
                    and policy['provenance_fields'] == list(PROVENANCE_IDENTITY_FIELDS)
                    and type(policy['parties']) is list
                    and policy['parties'] == list(parties),
                    'IDENTITY_CONTINUITY_POLICY_INVALID')


def _same_generation(left: dict, right: dict) -> bool:
    return left['source_commit'] == right['source_commit'] and left['sources'] == right['sources']


def _qualify_identities(spec: dict, identities: dict) -> bytes:
    """Validate recorded and fresh receipts; return observed canonical bytes.

    The recorded receipts remain the immutable identity decision: their digests
    are pinned inside the native fact. A fresh observation is admitted either by
    exact equality or, only when the explicit spec continuity policy is present,
    by provenance-only drift with all six semantic/evidence fields equal for
    that party. Because the receipt shape is closed, any difference that
    survives semantic equality is provenance-only by construction, and the
    refreshed provenance has already been fully shape-validated above. Both
    parties must additionally observe one shared current source generation.
    Any split generation, missing policy, malformed receipt or semantic change
    refuses.
    """
    continuity = spec.get('identity_continuity')
    native._require(type(identities) is dict and type(spec['identities']) is dict
                    and set(identities) == set(spec['identities']) == set(IDENTITY_PARTIES),
                    'CURRENT_IDENTITY_CHANGED')
    for receipt in (spec['identities']['MU'], spec['identities']['NVDA'],
                    identities['MU'], identities['NVDA']):
        _validate_identity_receipt(receipt)
    if continuity is not None:
        _validate_continuity(continuity)
    for symbol, party, field in [('MU', 'subject_id', 'subject_identity'),
                                ('NVDA', 'object_id', 'object_identity')]:
        recorded, current = spec['identities'][symbol], identities[symbol]
        native._require(current['issuer_id'] == spec['fact'][party], 'IDENTITY_BINDING_MISMATCH')
        if native._canonical(current) != native._canonical(recorded):
            native._require(continuity is not None, 'CURRENT_IDENTITY_CHANGED')
            native._require(all(current[k] == recorded[k] for k in SEMANTIC_IDENTITY_FIELDS),
                            'CURRENT_IDENTITY_CHANGED')
        # The recorded decision, never the fresh observation, binds the fact.
        native._require(digest(native._canonical(recorded)) == spec['fact'][field],
                        'IDENTITY_BINDING_MISMATCH')
    native._require(_same_generation(identities['MU'], identities['NVDA']),
                    'IDENTITY_GENERATION_SPLIT')
    return native._canonical(identities)


@dataclass(frozen=True)
class OwnerSnapshot:
    code_version: str
    spec_bytes: bytes
    ruling_revision: str
    adoption_revision: str
    dataset_status: str
    current_identities_raw: bytes | None = None

    @property
    def spec(self):
        return _json(self.spec_bytes)

    @property
    def bindings(self):
        return {'spec': digest(self.spec_bytes), 'purpose': self.ruling_revision,
                'adoption': self.adoption_revision}

    @property
    def identity_continuity(self):
        return self.spec.get('identity_continuity')

    @property
    def current_identities(self):
        """Observed fresh receipts frozen as canonical bytes at qualification.

        The default (absent observation) exists only for the pre-existing
        five-argument synthetic fixture constructor. It is safe solely because
        a v1 specification admits no drift at all, so the recorded receipts are
        the only admissible observation. Production qualification always stores
        observed bytes, and a v2 specification with missing observed bytes
        refuses outright in both properties below; no runtime fallback re-reads
        or re-derives identity from the environment.
        """
        raw = self.current_identities_raw
        if raw is None:
            native._require(self.identity_continuity is None, 'CURRENT_IDENTITY_CHANGED')
            return self.spec['identities']
        return _json(raw)

    @property
    def identity_binding(self):
        """Digest binding the recorded receipts, the observed receipts and the
        protected continuity policy into one in-flight identity decision.

        This is deliberately separate from ``bindings`` (spec/purpose/adoption),
        which stay pinned to the protected immutable records and therefore do
        not move when only reference provenance refreshes.
        """
        raw = self.current_identities_raw
        if raw is None:
            native._require(self.identity_continuity is None, 'CURRENT_IDENTITY_CHANGED')
            raw = native._canonical(self.spec['identities'])
        material = {'schema': CONTINUITY_BINDING_SCHEMA,
                    'recorded': digest(native._canonical(self.spec['identities'])),
                    'current': digest(raw)}
        continuity = self.identity_continuity
        if continuity is not None:
            material['policy'] = digest(native._canonical(continuity))
        return digest(native._canonical(material))


def qualify_records(code_version: str, spec_raw: bytes, ruling_raw: bytes,
                    registry_raw: bytes, identities: dict, *, theme_sources_raw: bytes | None = None) -> OwnerSnapshot:
    """Interpret original records, never an Admission or grant from a caller."""
    import yaml
    native._require(re.fullmatch('[0-9a-f]{40}', code_version) is not None, 'CODE_VERSION_INVALID')
    spec, ruling = _json(spec_raw), _json(ruling_raw)
    if spec.get('schema') == 'company_intelligence.sec_supplier_owner_decision/v1':
        from . import sec_supplier_adoption as supplier
        native._require(type(theme_sources_raw) is bytes, 'SEC_FACT_POLICY_NOT_QUALIFIED')
        return supplier.qualify_records(code_version, spec_raw, ruling_raw, registry_raw, identities,
                                        theme_sources_raw=theme_sources_raw)
    continuity = spec.get('identity_continuity')
    closed = {'schema', 'case_id', 'ruling_reference', 'edition', 'fact', 'identities',
              'temporal_decision', 'correction_decision', 'semantic_review'}
    native._require((spec.get('schema') == OWNER_SCHEMA_V1 and continuity is None and set(spec) == closed)
                    or (spec.get('schema') == OWNER_SCHEMA_V2 and continuity is not None
                        and set(spec) == closed | {'identity_continuity'}), 'OWNER_SPEC_INVALID')
    if continuity is not None:
        _validate_continuity(continuity)
    native._require(spec['case_id'] == ruling['case_id'] == 'C01-micron-planned-product-integration'
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
    observed = _qualify_identities(spec, identities)
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
                         digest(native._canonical(rows[0])), row.status.value, observed)


class CommittedDisclosureSource:
    """Fresh installed protected decisions plus the incumbent identity owner."""
    def __init__(self, repo: Path, identity_owner=None, *, sec_supplier_paths: tuple[str, str, str] | None = None):
        self.git = CommittedCompanyContextOwner(repo)
        self.identity_owner = identity_owner or self.git
        # Optional deployment-owned exact protected paths: spec, source-purpose
        # basis, theme_sources. No discovery, URL allowance or default activation.
        native._require(sec_supplier_paths is None or (type(sec_supplier_paths) is tuple
            and len(sec_supplier_paths) == 3 and all(type(p) is str and p and not p.startswith('/')
                and '..' not in p.split('/') for p in sec_supplier_paths)), 'SOURCE_PATH_INVALID')
        self.sec_supplier_paths = sec_supplier_paths

    def accepts_revision(self, revision: str) -> bool:
        native._require(re.fullmatch('[0-9a-f]{40}', revision) is not None, 'CODE_VERSION_INVALID')
        self.git._git('merge-base', '--is-ancestor', revision, self.git._head())
        return True

    def snapshot(self) -> OwnerSnapshot:
        head = self.git._head()
        self.git._git('merge-base', '--is-ancestor', head, 'refs/remotes/origin/main')
        spec_path, ruling_path, theme_path = (SPEC_PATH, RULING_PATH, None) if self.sec_supplier_paths is None else self.sec_supplier_paths
        paths = (spec_path, ruling_path, REGISTRY_PATH) + (() if theme_path is None else (theme_path,))
        blobs = self.git._read(self.git._objects(head, paths))
        queries = {symbol: symbol for symbol in IDENTITY_PARTIES} if theme_path is None else _json(blobs[spec_path])['identity_queries']
        if theme_path is not None:
            native._closed(queries, {'subject', 'object'})
        identities = {role: context.read_company_context(self.identity_owner, symbol,
            purpose=PURPOSE, audience=AUDIENCE)['identity_receipt'] for role, symbol in queries.items()}
        result = qualify_records(head, blobs[spec_path], blobs[ruling_path], blobs[REGISTRY_PATH], identities,
            theme_sources_raw=None if theme_path is None else blobs[theme_path])
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


def _manifest_reference(value):
    native._closed(value, {'sha256', 'byte_length'})
    native._digest(value['sha256'])
    native._integer(value['byte_length'], 1, native.MAX_OBJECT_BYTES)
    return value


def read_generation(state, reference):
    """One exact bounded immutable metadata object; never follow a pointer."""
    ref = _manifest_reference(reference)
    raw = state.get_bytes_strict_bounded('generations/' + ref['sha256'] + '.json',
        expected_byte_length=ref['byte_length'], max_byte_length=native.MAX_OBJECT_BYTES)
    native._require(raw is not None and object_ref(raw) == ref, 'CURRENT_MANIFEST_MISMATCH')
    return native._decode(raw)


def validate_component(manifest):
    native._closed(manifest, {'schema', 'dataset_id', 'temporal_profile', 'computed_at', 'code_version',
        'input_cutoffs', 'decisions', 'edition', 'fact'})
    native._require(manifest['schema'] == MANIFEST_SCHEMA and manifest['dataset_id'] == DATASET
        and manifest['temporal_profile'] == 'DERIVED', 'CURRENT_COMPONENT_INVALID')
    native._require(type(manifest['code_version']) is str
        and re.fullmatch('[0-9a-f]{40}', manifest['code_version']) is not None, 'GENERATION_CODE_INVALID')
    cutoffs = native._closed(manifest['input_cutoffs'], {'source_known_at', 'fact_known_at'})
    native._require(native._instant(cutoffs['source_known_at']) <= native._instant(cutoffs['fact_known_at'])
        <= native._instant(manifest['computed_at']) <= datetime.now(timezone.utc), 'GENERATION_TIME_INVALID')
    native._closed(manifest['decisions'], {'spec', 'purpose', 'adoption'})
    for value in manifest['decisions'].values():
        native._digest(value)
    fact = native.Reference(**native._closed(manifest['fact'], {'schema', 'sha256', 'byte_length'}))
    native._require(fact.schema in native.FACT_SCHEMAS, 'CURRENT_COMPONENT_INVALID')
    native._reference(manifest['edition'], native.SEC_EDITION_SCHEMA
        if fact.schema == native.SUPPLIER_FACT_SCHEMA else native.EDITION_SCHEMA)


def validate_members(members):
    native._require(type(members) is list and 1 <= len(members) <= MAX_CURRENT_MEMBERS, 'CURRENT_MEMBER_LIMIT')
    ids, references = [], []
    for member in members:
        native._closed(member, {'fact_id', 'subject_id', 'fact_schema', 'manifest'})
        native._require(type(member['fact_id']) is str and re.fullmatch('integration:[0-9a-f]{64}', member['fact_id']) is not None,
                        'CURRENT_MEMBER_INVALID')
        from .issuer_disclosure_selection import issuer_identity
        issuer_identity(member['subject_id'])
        native._require(type(member['fact_schema']) is str and member['fact_schema'] in native.FACT_SCHEMAS, 'CURRENT_MEMBER_INVALID')
        _manifest_reference(member['manifest'])
        ids.append(member['fact_id']); references.append(member['manifest']['sha256'])
    native._require(ids == sorted(set(ids)) and len(references) == len(set(references)), 'CURRENT_MEMBER_DUPLICATE_OR_UNORDERED')


def validate_collection(collection):
    native._closed(collection, {'schema', 'computed_at', 'members'})
    native._require(collection['schema'] == COLLECTION_SCHEMA, 'CURRENT_COLLECTION_INVALID')
    native._require(native._instant(collection['computed_at']) <= datetime.now(timezone.utc), 'GENERATION_TIME_INVALID')
    validate_members(collection['members'])


def collection_components(state, collection):
    """One layer only. A component can never be another collection."""
    validate_collection(collection)
    result = []
    for member in collection['members']:
        manifest = read_generation(state, member['manifest'])
        validate_component(manifest)
        native._require(manifest['fact']['schema'] == member['fact_schema']
            and native._instant(manifest['computed_at']) <= native._instant(collection['computed_at']), 'CURRENT_MEMBER_MISMATCH')
        result.append((member, manifest))
    return result


def read_current_manifest(state, *, pointer_raw=None):
    raw = state.get_bytes_strict_bounded(CURRENT_KEY, native.MAX_OBJECT_BYTES) if pointer_raw is None else pointer_raw
    pointer = native._decode(raw)
    native._closed(pointer, {'schema', 'manifest'})
    native._require(pointer['schema'] == POINTER_SCHEMA, 'CURRENT_POINTER_INVALID')
    reference = _manifest_reference(pointer['manifest'])
    manifest = read_generation(state, reference)
    return raw, reference, manifest


def member_descriptor(snapshot, reference):
    fact = snapshot.spec['fact']
    return {'fact_id': fact['fact_id'], 'subject_id': fact['subject_id'], 'fact_schema': fact['schema'],
            'manifest': dict(_manifest_reference(reference))}


def qualify_component(source, manifest):
    """Original per-source qualification, retaining the component generation."""
    validate_component(manifest)
    snapshot = source.snapshot()
    native._require(snapshot.dataset_status == 'PRODUCED', 'DATASET_NOT_PRODUCED')
    native._require(source.accepts_revision(manifest['code_version']), 'GENERATION_CODE_INVALID')
    expected = make_manifest(replace(snapshot, code_version=manifest['code_version']), manifest['computed_at'])
    native._require(manifest == expected, 'CURRENT_DECISION_CHANGED')
    return snapshot


def admission(snapshot: OwnerSnapshot, manifest: dict, request: native.Request,
              operation: str = 'read') -> native.Admission:
    spec, fact = snapshot.spec, snapshot.spec['fact']
    native._require(request.mode == 'current' and request.fact_id == fact['fact_id']
                    and (request.purpose, request.audience) == (PURPOSE, AUDIENCE), 'SOURCE_NOT_ADMITTED')
    # The subject binding names the exact current observation; the decision
    # revision stays the original recorded fact identity. The aggregate
    # identity revision binds both full current receipts plus the protected
    # continuity policy, separately from the manifest's protected decisions.
    supplier = fact['schema'] == native.SUPPLIER_FACT_SCHEMA
    identity = snapshot.current_identities['subject' if supplier else 'MU']
    raw_identity = native._canonical(identity)
    result = native.Admission(request, native.validate_fact(fact), native.validate_edition(spec['edition']),
        digest(native._canonical(manifest)), DATASET, 'DERIVED', snapshot.adoption_revision,
        snapshot.ruling_revision, snapshot.identity_binding,
        digest(native._canonical(spec['temporal_decision'])), digest(native._canonical(spec['correction_decision'])),
        fact['known_at'], spec['edition']['publication_precision'], 'current', native._FIELDS,
        operation, native.SubjectIdentityBinding(identity['issuer_id'], identity['evidenced_cik'],
            identity['schema'], digest(raw_identity), len(raw_identity), fact['subject_identity']))
    if supplier:
        other = snapshot.current_identities['object']; raw_other = native._canonical(other)
        result = replace(result, object_binding=native.SubjectIdentityBinding(other['issuer_id'], other['evidenced_cik'],
            other['schema'], digest(raw_other), len(raw_other), fact['object_identity']))
    return result


class CurrentDisclosureOwner:
    """Metadata-only resolver. It has no publication capability or artifact Store."""
    def __init__(self, source, state, *, supplier_sources=None):
        self.source, self.state = source, state
        native._require(supplier_sources is None or (type(supplier_sources) is dict
            and set(supplier_sources) <= native.FACT_SCHEMAS), 'SOURCE_SCHEMA_NOT_CONFIGURED')
        self.supplier_sources = {} if supplier_sources is None else dict(supplier_sources)

    def _current(self, *, fact_id=None, issuer_id=None):
        pointer_raw, _, manifest = read_current_manifest(self.state)
        member = None
        if manifest.get('schema') == COLLECTION_SCHEMA:
            components = collection_components(self.state, manifest)
            selected = [(m, c) for m, c in components if (fact_id is not None and m['fact_id'] == fact_id)
                        or (issuer_id is not None and m['subject_id'] == issuer_id)]
            native._require(len(selected) <= 1, 'CURRENT_SELECTION_AMBIGUOUS')
            if not selected:
                return None
            member, manifest = selected[0]
            schema = member['fact_schema']
            source = self.supplier_sources.get(schema, self.source if schema == native.FACT_SCHEMA else None)
            native._require(source is not None, 'SOURCE_SCHEMA_NOT_CONFIGURED')
        else:
            # Preserve the legacy explicit single-owner API, including callers
            # holding only a supplier source and its original v1 manifest.
            validate_component(manifest)
            source = self.supplier_sources.get(manifest['fact']['schema'], self.source)
        snapshot = qualify_component(source, manifest)
        if member is not None:
            native._require(member == member_descriptor(snapshot, object_ref(native._canonical(manifest))), 'CURRENT_MEMBER_MISMATCH')
        later = source.snapshot()
        native._require(later.bindings == snapshot.bindings
                        and later.identity_binding == snapshot.identity_binding
                        and self.state.get_bytes_strict_bounded(CURRENT_KEY, native.MAX_OBJECT_BYTES) == pointer_raw,
                        'CURRENT_GENERATION_CHANGED')
        return snapshot, manifest

    def resolve(self, request):
        if (type(request) is not native.Request or request.mode != 'current'
                or (request.purpose, request.audience) != (PURPOSE, AUDIENCE)):
            return None
        current = self._current(fact_id=request.fact_id)
        if current is None:
            return None
        snapshot, manifest = current
        return admission(snapshot, manifest, request)

    def authorize_publication(self, request, candidate):
        return None

    def resolve_issuer(self, issuer_id, purpose, audience):
        if (purpose, audience) != (PURPOSE, AUDIENCE):
            return None
        current = self._current(issuer_id=issuer_id)
        if current is None:
            return None
        snapshot, manifest = current
        fact = snapshot.spec['fact']
        if issuer_id != fact['subject_id']:
            return None
        a = admission(snapshot, manifest, native.Request(fact['fact_id'], purpose, audience))
        b = a.subject_binding
        return IssuerSelection(b.issuer_id, b.evidenced_cik, b.snapshot_schema,
            b.snapshot_sha256, b.snapshot_byte_length, a.generation, purpose, audience,
            (SelectionEntry(fact['fact_id'], a.reference, a.edition),))
