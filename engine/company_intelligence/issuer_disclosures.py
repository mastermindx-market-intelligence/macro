"""Standalone issuer disclosures, owned by Company Intelligence.

These contracts do not invent an earnings period or an SEC filing identity.
Source editions and reviewed fact revisions have separate immutable chains.
The producer owns original source bytes; the object store below receives only
bounded metadata and constrained fact fields, never original/reviewer text.

``DisclosureAuthority`` is an injected *trusted source-owner* boundary, not an
entitlement supplied by a web caller. No production resolver, dataset adoption,
rights grant or HTTP endpoint is installed by this module. F04 must authenticate
and check its actual feature entitlement before calling the private reader.
Synthetic resolvers prove the contract, not permission to admit real C01.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Protocol

from .documents import text_span
from ..research_vault.r2_store import VersionedBytes

EDITION_SCHEMA = "company_intelligence.issuer_disclosure_edition/v1"
FACT_SCHEMA = "company_intelligence.product_integration_fact/v1"
MAX_OBJECT_BYTES = 16 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
MAX_REVISIONS = 64
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}\Z")
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")
_FIELDS = frozenset({"fact_id", "revision", "kind", "lifecycle", "subject_id",
                     "object_id", "product", "platform", "amount", "economic_share"})


class DisclosureError(ValueError):
    """A closed contract or a source-owner admission failed."""

    def __init__(self, code: str, *, effect_unknown: bool = False):
        super().__init__(code)
        self.code = code
        self.effect_unknown = effect_unknown
        self.automatic_retry_permitted = False


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise DisclosureError(code)


def _identifier(value: object) -> str:
    _require(type(value) is str and _ID.fullmatch(value) is not None, "IDENTITY_INVALID")
    return value


def _digest(value: object) -> str:
    _require(type(value) is str and _SHA.fullmatch(value) is not None, "DIGEST_INVALID")
    return value


def _integer(value: object, minimum: int, maximum: int) -> int:
    _require(type(value) is int and minimum <= value <= maximum, "INTEGER_INVALID")
    return value


def _instant(value: object) -> datetime:
    _require(type(value) is str and _INSTANT.fullmatch(value) is not None, "INSTANT_PRECISION_INVALID")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        raise DisclosureError("INSTANT_INVALID") from None


def _closed(value: object, fields: set[str]) -> dict:
    _require(type(value) is dict and set(value) == fields, "SCHEMA_INVALID")
    return value


def _canonical(value: dict) -> bytes:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise DisclosureError("JSON_INVALID") from None
    _require(0 < len(raw) <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE")
    return raw


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def _decode(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE")
    try:
        result = json.loads(raw, object_pairs_hook=_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(DisclosureError("JSON_INVALID")))
    except (ValueError, UnicodeError, RecursionError):
        raise DisclosureError("JSON_INVALID") from None
    _require(type(result) is dict and _canonical(result) == raw, "NONCANONICAL_OBJECT")
    return result


def disclosure_id(issuer_id: str, source_key: str) -> str:
    """Stable native identity; the source owner supplies the original key."""
    material = [_identifier(issuer_id), _identifier(source_key)]
    return "disclosure:" + hashlib.sha256(json.dumps(material, separators=(",", ":")).encode()).hexdigest()


def fact_id(disclosure: str, claim_key: str) -> str:
    material = [_identifier(disclosure), _identifier(claim_key)]
    return "integration:" + hashlib.sha256(json.dumps(material, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Reference:
    schema: str
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        _require(type(self.schema) is str and self.schema in {EDITION_SCHEMA, FACT_SCHEMA}, "REFERENCE_SCHEMA_INVALID")
        _digest(self.sha256)
        _integer(self.byte_length, 1, MAX_OBJECT_BYTES)

    def payload(self) -> dict:
        return {"schema": self.schema, "sha256": self.sha256, "byte_length": self.byte_length}


def _reference(value: object, schema: str) -> Reference:
    value = _closed(value, {"schema", "sha256", "byte_length"})
    result = Reference(**value)
    _require(result.schema == schema, "REFERENCE_SCHEMA_INVALID")
    return result


def _ref(value: dict) -> Reference:
    raw = _canonical(value)
    return Reference(value["schema"], hashlib.sha256(raw).hexdigest(), len(raw))


def validate_edition(value: dict) -> Reference:
    _closed(value, {"schema", "disclosure_id", "issuer_id", "source_key", "revision",
                    "previous", "source_sha256", "source_byte_length", "published_date",
                    "published_at", "publication_precision", "known_at"})
    _require(value["schema"] == EDITION_SCHEMA, "SCHEMA_INVALID")
    _require(value["disclosure_id"] == disclosure_id(value["issuer_id"], value["source_key"]), "DISCLOSURE_ID_MISMATCH")
    _integer(value["revision"], 1, MAX_REVISIONS)
    _integer(value["source_byte_length"], 1, MAX_SOURCE_BYTES)
    _digest(value["source_sha256"])
    known = _instant(value["known_at"])
    _require((value["revision"] == 1) == (value["previous"] is None), "PREDECESSOR_REQUIRED")
    if value["previous"] is not None:
        _reference(value["previous"], EDITION_SCHEMA)
    try:
        published_date = value["published_date"]
        _require(type(published_date) is str and date.fromisoformat(published_date).isoformat() == published_date, "DATE_INVALID")
    except ValueError:
        raise DisclosureError("DATE_INVALID") from None
    _require(type(value["publication_precision"]) is str and value["publication_precision"] in {"date", "instant"}, "PUBLICATION_PRECISION_INVALID")
    if value["publication_precision"] == "date":
        _require(value["published_at"] is None, "DATE_IS_NOT_INSTANT")
        _require(date.fromisoformat(published_date) <= known.date(), "FUTURE_PUBLICATION")
    else:
        published = _instant(value["published_at"])
        source_day = datetime.fromisoformat(value["published_at"].replace("Z", "+00:00")).date()
        _require(source_day.isoformat() == published_date and published <= known, "PUBLICATION_TIME_MISMATCH")
    return _ref(value)


def validate_fact(value: dict) -> Reference:
    _closed(value, {"schema", "fact_id", "claim_key", "disclosure_id", "edition",
                    "revision", "previous", "review_revision", "subject_id", "object_id",
                    "subject_identity", "object_identity", "kind", "lifecycle", "product",
                    "platform", "amount", "economic_share", "span", "known_at"})
    _require(value["schema"] == FACT_SCHEMA, "SCHEMA_INVALID")
    _require(value["fact_id"] == fact_id(value["disclosure_id"], value["claim_key"]), "FACT_ID_MISMATCH")
    _reference(value["edition"], EDITION_SCHEMA)
    _integer(value["revision"], 1, MAX_REVISIONS)
    _require((value["revision"] == 1) == (value["previous"] is None), "PREDECESSOR_REQUIRED")
    if value["previous"] is not None:
        _reference(value["previous"], FACT_SCHEMA)
    for field in ("review_revision", "subject_identity", "object_identity"):
        _digest(value[field])
    _identifier(value["subject_id"]); _identifier(value["object_id"])
    _require(value["subject_id"] != value["object_id"], "PARTY_IDENTITY_AMBIGUOUS")
    _require(value["kind"] == "product_integration" and value["lifecycle"] == "planned", "FACT_SPECIES_INVALID")
    for field in ("product", "platform"):
        _require(type(value[field]) is str and 0 < len(value[field]) <= 256 and len(value[field].encode("utf-8")) <= 256
                 and value[field].strip() == value[field], "FACT_SCOPE_INVALID")
    _require(value["amount"] is None and value["economic_share"] is None, "MAGNITUDE_NOT_ADMITTED")
    span = _closed(value["span"], {"start_byte", "end_byte", "text_sha256"})
    _integer(span["start_byte"], 0, MAX_SOURCE_BYTES)
    _integer(span["end_byte"], span["start_byte"] + 1, MAX_SOURCE_BYTES)
    _digest(span["text_sha256"])
    _instant(value["known_at"])
    return _ref(value)


@dataclass(frozen=True)
class Request:
    fact_id: str
    purpose: str
    audience: str
    as_of: str | None = None
    mode: str = "current"

    def __post_init__(self) -> None:
        for field in (self.fact_id, self.purpose, self.audience):
            _identifier(field)
        _require(type(self.mode) is str and self.mode in {"current", "historical"}, "QUERY_MODE_INVALID")
        if self.mode == "current":
            _require(self.as_of is None, "CURRENT_CUTOFF_NOT_ALLOWED")
        else:
            _instant(self.as_of)


@dataclass(frozen=True)
class SubjectIdentityBinding:
    """Owner-attested link from one fact decision to an immutable identity receipt.

    The schema names the actual supplied receipt; it does not invent a DataOS
    contract. The aggregate Admission.identity_revision remains a separate
    decision and must not be confused with this subject-specific revision.
    """
    issuer_id: str
    evidenced_cik: str
    snapshot_schema: str
    snapshot_sha256: str
    snapshot_byte_length: int
    decision_revision: str

    def __post_init__(self) -> None:
        _identifier(self.issuer_id)
        _require(type(self.evidenced_cik) is str
                 and re.fullmatch(r"[0-9]{10}", self.evidenced_cik) is not None
                 and int(self.evidenced_cik) > 0, "SUBJECT_IDENTITY_INVALID")
        _identifier(self.snapshot_schema)
        _digest(self.snapshot_sha256)
        _integer(self.snapshot_byte_length, 1, MAX_OBJECT_BYTES)
        _digest(self.decision_revision)


@dataclass(frozen=True)
class Admission:
    """Metadata returned only by the injected, adopted source-owner resolver.

    The exact request/reference bind the decision. Immutable decision digests
    name independently maintained registry, purpose, legal identity, temporal
    and correction decisions. They are not themselves permission tokens.
    """
    request: Request
    reference: Reference
    edition: Reference
    generation: str
    dataset_id: str
    profile: str
    adoption_revision: str
    purpose_revision: str
    identity_revision: str
    temporal_revision: str
    correction_revision: str
    known_at: str
    publication_precision: str
    identity_mode: str
    allowed_fields: frozenset[str]
    operation: str = "read"
    subject_binding: SubjectIdentityBinding | None = None

    def validate(self, request: Request, candidate: Reference | None) -> None:
        _require(self.subject_binding is None or type(self.subject_binding) is SubjectIdentityBinding,
                 "SUBJECT_IDENTITY_INVALID")
        _require(self.request == request, "ADMISSION_REQUEST_MISMATCH")
        _require(self.operation == ("publish" if candidate is not None else "read"), "ADMISSION_OPERATION_MISMATCH")
        _require(type(self.reference) is Reference and self.reference.schema == FACT_SCHEMA, "ADMISSION_REFERENCE_INVALID")
        _require(type(self.edition) is Reference and self.edition.schema == EDITION_SCHEMA, "ADMISSION_REFERENCE_INVALID")
        _require(candidate is None or self.reference == candidate, "ADMISSION_REFERENCE_MISMATCH")
        for field in (self.generation, self.dataset_id, self.profile):
            _identifier(field)
        for field in (self.adoption_revision, self.purpose_revision, self.identity_revision,
                      self.temporal_revision, self.correction_revision):
            _digest(field)
        now = datetime.now(timezone.utc)
        cutoff = now if request.mode == "current" else _instant(request.as_of)
        _require(cutoff <= now and _instant(self.known_at) <= cutoff, "FUTURE_KNOWLEDGE")
        _require(type(self.publication_precision) is str and self.publication_precision in {"date", "instant"}, "PUBLICATION_PRECISION_INVALID")
        _require(type(self.identity_mode) is str and self.identity_mode in {"current", "historical"}, "IDENTITY_MODE_INVALID")
        if request.mode == "historical":
            _require(self.publication_precision == "instant" and self.identity_mode == "historical", "HISTORICAL_BINDING_UNAVAILABLE")
        _require(type(self.allowed_fields) is frozenset and self.allowed_fields <= _FIELDS
                 and {"fact_id", "kind", "lifecycle"} <= self.allowed_fields, "FIELD_GRANT_INVALID")


class DisclosureAuthority(Protocol):
    def resolve(self, request: Request) -> Admission | None:
        """Resolve adopted source/purpose/identity/time/correction metadata only.

        Must not retrieve private source/reviewer content. For reads, select the
        owner-current immutable reference for the request. Read authority does
        not imply publication authority. Production installation is separate.
        """
        ...

    def authorize_publication(self, request: Request, candidate: Reference) -> Admission | None:
        """Separate source-owner write decision for this exact proposed root."""
        ...


def preflight(authority: DisclosureAuthority, request: Request,
              candidate: Reference | None = None) -> Admission:
    """No store argument and no private I/O; errors reveal no owner detail."""
    _require(type(request) is Request, "REQUEST_INVALID")
    try:
        admitted = (authority.resolve(request) if candidate is None
                    else authority.authorize_publication(request, candidate))
    except Exception:
        raise DisclosureError("OWNER_RESOLUTION_UNAVAILABLE") from None
    _require(type(admitted) is Admission, "SOURCE_NOT_ADMITTED")
    admitted.validate(request, candidate)
    return admitted


def _subject_binding(fact: dict, admission: Admission) -> None:
    binding = admission.subject_binding
    if binding is not None:
        _require(fact["subject_id"] == binding.issuer_id
                 and fact["subject_identity"] == binding.decision_revision,
                 "SUBJECT_IDENTITY_MISMATCH")


def _key(reference: Reference) -> str:
    kind = "editions" if reference.schema == EDITION_SCHEMA else "facts"
    return f"company_intelligence/issuer_disclosures/v1/{kind}/{reference.sha256}.json"


def _read(store: object, reference: Reference) -> bytes | None:
    try:
        raw = store.get_bytes_strict_bounded(_key(reference), expected_byte_length=reference.byte_length,
                                            max_byte_length=MAX_OBJECT_BYTES)
    except Exception:
        raise DisclosureError("PRIVATE_READ_UNAVAILABLE") from None
    if raw is not None:
        _require(type(raw) is bytes and len(raw) == reference.byte_length
                 and hashlib.sha256(raw).hexdigest() == reference.sha256, "PRIVATE_OBJECT_MISMATCH")
    return raw


def _load(store: object, reference: Reference) -> dict:
    raw = _read(store, reference)
    _require(raw is not None, "PRIVATE_OBJECT_ABSENT")
    value = _decode(raw)
    actual = validate_edition(value) if reference.schema == EDITION_SCHEMA else validate_fact(value)
    _require(actual == reference, "PRIVATE_OBJECT_MISMATCH")
    return value


def _slot(value: dict) -> tuple[str, bytes]:
    """The incumbent CAS store binds one value to each native revision."""
    identity = value["disclosure_id"] if value["schema"] == EDITION_SCHEMA else value["fact_id"]
    family = "editions" if value["schema"] == EDITION_SCHEMA else "facts"
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    path = f"company_intelligence/issuer_disclosures/v1/revisions/{family}/{key}/{value['revision']}.json"
    return path, _canonical({"schema": "company_intelligence.disclosure_revision_binding/v1",
                             "reference": _ref(value).payload()})


def _slot_read(store: object, key: str) -> bytes | None:
    try:
        versioned = store.get_bytes_strict_bounded_versioned(key, MAX_OBJECT_BYTES)
    except Exception:
        raise DisclosureError("PRIVATE_BINDING_UNAVAILABLE") from None
    _require(type(versioned) is VersionedBytes, "PRIVATE_BINDING_PROTOCOL_INVALID")
    if versioned.data is not None:
        _require(len(versioned.data) <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE")
    return versioned.data


def _binding(store: object, value: dict, *, reserve: bool = False) -> bool:
    key, raw = _slot(value)
    existing = _slot_read(store, key)
    if existing is not None:
        _require(existing == raw, "REVISION_CONFLICT")
        return False
    _require(reserve, "REVISION_BINDING_ABSENT")
    raised = False
    try:
        store.put_bytes_strict_conditional(key, raw, expected_version=None, content_type="application/json")
    except Exception:
        raised = True
    try:
        observed = _slot_read(store, key)
    except DisclosureError:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN", effect_unknown=True) from None
    if raised and observed != raw:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN", effect_unknown=True)
    _require(observed is not None, "WRITE_NOT_OBSERVED")
    _require(observed == raw, "REVISION_CONFLICT")
    return True


def _chain(store: object, value: dict) -> None:
    # Revision counters are bounded, decrease exactly once, and reach revision1.
    while value["previous"] is not None:
        prior = _load(store, _reference(value["previous"], value["schema"]))
        _binding(store, prior)
        identity = "disclosure_id" if value["schema"] == EDITION_SCHEMA else "fact_id"
        _require(prior[identity] == value[identity] and prior["revision"] + 1 == value["revision"], "CORRECTION_CHAIN_MISMATCH")
        _require(_instant(prior["known_at"]) <= _instant(value["known_at"]), "CORRECTION_TIME_REVERSED")
        value = prior


def _create(store: object, reference: Reference, raw: bytes) -> bool:
    existing = _read(store, reference)
    if existing is not None:
        _require(existing == raw, "PRIVATE_OBJECT_MISMATCH")
        return False
    raised = False
    try:
        store.put_bytes_strict_conditional(_key(reference), raw, expected_version=None,
                                           content_type="application/json")
    except Exception:
        raised = True
    try:
        observed = _read(store, reference)
    except DisclosureError:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN", effect_unknown=True) from None
    if observed != raw:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN" if raised else "WRITE_NOT_OBSERVED", effect_unknown=raised)
    return True


class DisclosureSourceReader(Protocol):
    def read_source(self, *, disclosure_id: str, edition_reference: Reference,
                    source_sha256: str, expected_byte_length: int,
                    max_byte_length: int) -> bytes:
        """Owner-pinned private source retrieval; enforce bounds before buffering."""
        ...


def publish_disclosure(store: object, authority: DisclosureAuthority, request: Request,
                       *, edition: dict, fact: dict, source_reader: DisclosureSourceReader) -> dict:
    """Append exact owner-admitted metadata/fact bytes; never chooses credentials.

    Original source is retrieved only after metadata admission and only for span
    verification. Publication does not change the resolver's current selection.
    The final fact is the root; a partial edition remains immutable and harmless.
    """
    # Snapshot before invoking untrusted callbacks; later mutation cannot rebind.
    _require(type(request) is Request, "REQUEST_INVALID")
    validate_edition(edition); validate_fact(fact)
    edition = _decode(_canonical(edition)); fact = _decode(_canonical(fact))
    eref, fref = validate_edition(edition), validate_fact(fact)
    _require(fact["fact_id"] == request.fact_id and fact["edition"] == eref.payload()
             and fact["disclosure_id"] == edition["disclosure_id"]
             and fact["subject_id"] == edition["issuer_id"], "SOURCE_BINDING_MISMATCH")
    _require(_instant(edition["known_at"]) <= _instant(fact["known_at"]), "FACT_PRECEDES_SOURCE")
    admission = preflight(authority, request, fref)
    _subject_binding(fact, admission)
    _require(admission.edition == eref and admission.known_at == fact["known_at"]
             and admission.publication_precision == edition["publication_precision"], "ADMISSION_METADATA_MISMATCH")
    try:
        store.validate_strict_conditional_write_capability()
    except Exception:
        raise DisclosureError("CONDITIONAL_STORE_UNAVAILABLE") from None
    _chain(store, edition); _chain(store, fact)
    try:
        body = source_reader.read_source(disclosure_id=edition["disclosure_id"], edition_reference=eref,
                                         source_sha256=edition["source_sha256"],
                                         expected_byte_length=edition["source_byte_length"],
                                         max_byte_length=MAX_SOURCE_BYTES)
    except Exception:
        raise DisclosureError("SOURCE_READ_UNAVAILABLE") from None
    _require(type(body) is bytes and len(body) == edition["source_byte_length"]
             and hashlib.sha256(body).hexdigest() == edition["source_sha256"], "SOURCE_BYTES_MISMATCH")
    span = fact["span"]
    try:
        segment = body.decode("utf-8")
        excerpt = body[span["start_byte"]:span["end_byte"]].decode("utf-8")
        receipt = text_span(document_id=edition["disclosure_id"], document_version=edition["revision"],
                            body_sha256=edition["source_sha256"], segment_index=0, segment_text=segment,
                            start_byte=span["start_byte"], end_byte=span["end_byte"], text=excerpt,
                            display_excerpt="")
    except Exception:
        raise DisclosureError("SOURCE_SPAN_INVALID") from None
    _require(receipt.text_sha256 == span["text_sha256"], "SOURCE_SPAN_MISMATCH")
    _require(preflight(authority, request, fref) == admission, "ADMISSION_CHANGED")
    writes = int(_create(store, eref, _canonical(edition)))
    writes += int(_binding(store, edition, reserve=True))
    # Stop before committing the root if rights/current generation changed.
    _require(preflight(authority, request, fref) == admission, "ADMISSION_CHANGED")
    writes += int(_create(store, fref, _canonical(fact)))
    writes += int(_binding(store, fact, reserve=True))
    return {"status": "COMMITTED_OBSERVED" if writes else "REPEATED", "reference": fref.payload(),
            "conditional_objects_observed": writes, "automatic_retry_permitted": False}


def read_disclosure(store: object, authority: DisclosureAuthority, request: Request, *,
                    expected_admission: Admission | None = None) -> dict:
    """Owner-selected private fact read, optionally pinned by a composing caller."""
    _require(expected_admission is None or type(expected_admission) is Admission,
             "ADMISSION_INVALID")
    admission = preflight(authority, request)
    _require(expected_admission is None or admission == expected_admission,
             "ADMISSION_CHANGED")
    fact = _load(store, admission.reference)
    _subject_binding(fact, admission)
    _require(fact["fact_id"] == request.fact_id and fact["edition"] == admission.edition.payload()
             and fact["known_at"] == admission.known_at, "ADMISSION_METADATA_MISMATCH")
    edition = _load(store, admission.edition)
    _require(fact["disclosure_id"] == edition["disclosure_id"]
             and fact["subject_id"] == edition["issuer_id"]
             and edition["publication_precision"] == admission.publication_precision
             and _instant(edition["known_at"]) <= _instant(fact["known_at"]), "SOURCE_BINDING_MISMATCH")
    _binding(store, fact); _binding(store, edition)
    _chain(store, fact); _chain(store, edition)
    _require(preflight(authority, request) == admission, "ADMISSION_CHANGED")
    return {"schema": "company_intelligence.private_product_integration/v1",
            "fact": {k: fact[k] for k in sorted(admission.allowed_fields)},
            "reference": admission.reference.payload(), "edition": admission.edition.payload(),
            "generation": admission.generation, "authority": "context_only"}
