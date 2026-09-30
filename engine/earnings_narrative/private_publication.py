"""Private, receipt-bound publication for member earnings evidence.

The public Earnings Wire builder writes redacted HTML into ``site/`` and writes
the member continuation into an operator-selected staging directory outside the
repository.  This module validates that staging tree, publishes immutable
content-addressed objects to the existing private Research Vault store, and
moves one small private pointer only after every object has been read back.

No object key or payload produced here is a browser URL.  Browser reads go
through the authenticated ``/api/earnings/v1/records/{slug}`` route, which uses
server-side Research Vault credentials and enforces ``site_full`` first.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import threading
from types import MappingProxyType
from typing import Any, Mapping

from engine.company_intelligence import documents, event_workspace, pg_profile
from engine.earnings_narrative import economic_interpretation
from engine.earnings_narrative.context_packets import (canonical_json_bytes, validate_context_manifest,
                                                      validate_context_packet_at_cutoff)
from engine.research_vault.r2_store import (
    StrictBoundedReadStore,
    StrictConditionalWriteStore,
    Store,
)
from engine.theme_graph import rights

PRIVATE_PREFIX = "earnings_wire_private/v1"
RECORD_SCHEMA_V2 = "earnings.tier_payload/v2"
MANIFEST_SCHEMA_V2 = "earnings.private_manifest/v2"
DOSSIER_PAGE = "earnings_economic_dossier"
NATIVE_STAGE_DIR = "native"
NATIVE_STAGE_MANIFEST_NAME = "latest.json"
NATIVE_STAGE_SCHEMA = "earnings.private_native_stage/v1"
MAX_NATIVE_CHAIN = 4
MAX_ECONOMIC_FACTS = 24
MAX_ECONOMIC_COMPARISONS = 24
MAX_SOURCE_BODY_BYTES = 8 * 1024 * 1024
MAX_NATIVE_WORKSPACE_BYTES = 2 * 1024 * 1024
MAX_NATIVE_DOCUMENT_BYTES = 64 * 1024
MAX_NATIVE_STAGE_MANIFEST_BYTES = 1024 * 1024
RECORD_UNAVAILABLE_REASONS = ("no_native_selection",)
NATIVE_RIGHTS_REGISTRY_PATH = None
CLOSURE_REASONS = (
    "unsupported_schema",
    "malformed_native_section",
    "unsafe_path",
    "missing_artifact",
    "unexpected_artifact",
    "wrong_role",
    "digest_mismatch",
    "size_mismatch",
    "over_limit",
    "mismatched_source",
    "cross_issuer",
    "broken_chain",
    "predecessor_cycle",
    "future_source_clock",
    "interpretation_mismatch",
    "interpretation_unsupported",
    "rights_refused",
)
_CLOSURE_MESSAGES = {
    "unsupported_schema": "The stored schema is not supported.",
    "malformed_native_section": "The native economic section is malformed.",
    "unsafe_path": "The native storage path is unsafe.",
    "missing_artifact": "A required native artifact is missing.",
    "unexpected_artifact": "An unexpected native artifact was found.",
    "wrong_role": "An object key has the wrong native role.",
    "digest_mismatch": "An artifact digest does not match its bytes.",
    "size_mismatch": "An artifact size does not match its receipt.",
    "over_limit": "The native evidence exceeds a fixed limit.",
    "mismatched_source": "The native source bindings disagree.",
    "cross_issuer": "The native issuer is not admitted for this chain.",
    "broken_chain": "The native document chain is broken.",
    "predecessor_cycle": "The native predecessor link is cyclic.",
    "future_source_clock": "A native source clock is later than the cutoff.",
    "interpretation_mismatch": "The stored interpretation does not replay.",
    "interpretation_unsupported": "The stored interpretation version is unsupported.",
    "rights_refused": "The native rights registry refused publication.",
}
POINTER_KEY = f"{PRIVATE_PREFIX}/current.json"
POINTER_SCHEMA = "earnings.private_pointer/v1"
MANIFEST_SCHEMA = "earnings.private_manifest/v1"
RECORD_SCHEMA = "earnings.tier_payload/v1"
RECORD_STAGE_DIR = "records"
CONTEXT_STAGE_DIR = "context"
CONTEXT_MANIFEST_NAME = "latest.json"

MAX_POINTER_BYTES = 16 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_RECORD_BYTES = 2 * 1024 * 1024
MAX_CONTEXT_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_CONTEXT_PACKET_BYTES = 512 * 1024
MAX_RECORDS = 10_000
MAX_CONTEXT_PACKETS = 10_000
IDEMPOTENT_READ_WORKERS = 8
PUBLISH_WORKERS = 8

_NATIVE_CATALOG_ROLES = MappingProxyType({
    "workspaces": "native_workspace",
    "documents": "native_document",
    "source_bodies": "source_body_text",
})
_NATIVE_GENERATION_ID_RE = re.compile(r"\A[a-f0-9]{24}\Z")
_INTERPRETATION_ID_RE = re.compile(r"\Aecon_[a-f0-9]{64}\Z")
_CANONICAL_CLOCK_RE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_CANONICAL_DATE_RE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_NATIVE_PATH_RE = re.compile(r"\A(?:native/latest\.json|native/workspaces/[a-f0-9]{24}\.json|native/documents/[a-f0-9]{64}\.json|native/source_bodies/[a-f0-9]{64}\.txt)\Z")
_ARTIFACT_ROLES: Mapping[str, tuple[str, str, int]] = MappingProxyType({
    "record": (".json", "application/json", MAX_RECORD_BYTES),
    "context_manifest": (".json", "application/json", MAX_CONTEXT_MANIFEST_BYTES),
    "context_packet": (".json", "application/json", MAX_CONTEXT_PACKET_BYTES),
    "native_workspace": (".json", "application/json", MAX_NATIVE_WORKSPACE_BYTES),
    "native_document": (".json", "application/json", MAX_NATIVE_DOCUMENT_BYTES),
    "source_body_text": (".txt", "text/plain; charset=utf-8", MAX_SOURCE_BODY_BYTES),
})

_SLUG_RE = re.compile(r"\A[a-z0-9][a-z0-9-]{0,120}\Z")
_TICKER_RE = re.compile(r"\A[A-Z0-9.\-]{1,16}\Z")
_GENERATION_RE = re.compile(r"\Aearnpriv_[a-f0-9]{32}\Z")
_SHA_RE = re.compile(r"\A[a-f0-9]{64}\Z")
_OBJECT_KEY_RE = re.compile(
    rf"\A{re.escape(PRIVATE_PREFIX)}/objects/sha256/[a-f0-9]{{2}}/[a-f0-9]{{64}}\.json\Z"
)
_MANIFEST_KEY_RE = re.compile(
    rf"\A{re.escape(PRIVATE_PREFIX)}/manifests/earnpriv_[a-f0-9]{{32}}\.json\Z"
)
_UNSAFE_HTML_RE = re.compile(
    r"<(?:script|iframe|object|embed|link|meta)\b|\bon[a-z]+\s*=|javascript\s*:",
    re.IGNORECASE,
)
_PUBLISH_LOCK = threading.Lock()

PUBLISH_CONFLICT_REASONS = (
    "predecessor_conflict",
    "downgrade_refused",
    "slot_removed",
    "retirement_invalid",
    "chain_not_extended",
    "conditional_write_unavailable",
    "stale_native_cutoff",
    "installed_unreadable",
)
NOT_FOUND_REASONS = (
    "no_slot",
    "unknown_generation",
    "unknown_record",
    "unknown_fact",
    "absent_fact",
)
READ_UNAVAILABLE_REASONS = (
    "interpretation_unsupported",
    "rights_refused",
    "evidence_retired",
)
_PUBLISH_CONFLICT_MESSAGES = {
    "predecessor_conflict": "The installed private generation moved before publication.",
    "downgrade_refused": "A v2 private generation cannot return to v1.",
    "slot_removed": "An installed economic slot was removed without retirement.",
    "retirement_invalid": "The economic slot retirement instruction is invalid.",
    "chain_not_extended": "A retained native evidence chain was not extended.",
    "conditional_write_unavailable": "The store offers no conditional pointer write so v2 promotion is refused.",
    "stale_native_cutoff": "The candidate native source cutoff is older than the installed cutoff.",
    "installed_unreadable": "The installed private generation cannot be read.",
}
_NOT_FOUND_MESSAGES = {
    "no_slot": "No economic slot is currently available for this ticker.",
    "unknown_generation": "The requested private generation is unknown.",
    "unknown_record": "The requested economic record is unknown.",
    "unknown_fact": "The requested economic fact is unknown.",
    "absent_fact": "The requested economic fact has no source excerpt.",
}
_READ_UNAVAILABLE_MESSAGES = {
    "interpretation_unsupported": "The stored economic interpretation is unsupported.",
    "rights_refused": "Current rights do not permit this economic evidence.",
    "evidence_retired": "The economic evidence was retired from the current generation.",
}

class EarningsPrivatePublicationError(RuntimeError):
    """Private staging, publication, or read verification failed closed."""

class EarningsPrivateRecordNotFound(EarningsPrivatePublicationError):
    """A syntactically valid slug is not present in the current generation."""

class EarningsPrivateClosureError(EarningsPrivatePublicationError):
    """A v2 native evidence closure was refused."""

    def __init__(self, reason: str, message: str | None = None):
        if reason not in CLOSURE_REASONS:
            raise ValueError("unknown private closure reason")
        self.reason = reason
        super().__init__(message or _CLOSURE_MESSAGES[reason])


class EarningsPrivatePublishConflict(EarningsPrivatePublicationError):
    """A v2 publication cannot advance from the installed generation."""

    def __init__(self, reason: str, message: str | None = None):
        if reason not in PUBLISH_CONFLICT_REASONS:
            raise ValueError("unknown private publish conflict reason")
        self.reason = reason
        super().__init__(message or _PUBLISH_CONFLICT_MESSAGES[reason])


class EarningsPrivatePointerEffectUnknown(EarningsPrivatePublicationError):
    """The conditional pointer write may or may not have taken effect."""

    def __init__(self, generation_id: str, pointer_sha256: str, expected_version: str):
        self.generation_id = generation_id
        self.pointer_sha256 = pointer_sha256
        self.expected_version = expected_version
        super().__init__("private earnings pointer write effect is unknown")


class EarningsEconomicNotFound(EarningsPrivateRecordNotFound):
    """A typed economic record absence."""

    def __init__(self, reason: str, message: str | None = None):
        if reason not in NOT_FOUND_REASONS:
            raise ValueError("unknown economic not-found reason")
        self.reason = reason
        super().__init__(message or _NOT_FOUND_MESSAGES[reason])


class EarningsEconomicUnavailable(EarningsPrivatePublicationError):
    """Current rights or interpretation support cannot serve economic evidence."""

    def __init__(self, reason: str, message: str | None = None):
        if reason not in READ_UNAVAILABLE_REASONS:
            raise ValueError("unknown economic read-unavailable reason")
        self.reason = reason
        super().__init__(message or _READ_UNAVAILABLE_MESSAGES[reason])


class EarningsPrivateManifestNotCurrent(EarningsPrivatePublicationError):
    """The supplied manifest is not the generation named by the current pointer."""

@dataclass(frozen=True)
class PrivateArtifact:
    """One immutable object and the receipt advertised by the manifest."""

    role: str
    identity: str
    object_key: str
    sha256: str
    byte_length: int
    maximum_bytes: int
    content_type: str = "application/json"

    def receipt(self) -> dict[str, Any]:
        return {
            "object_key": self.object_key,
            "sha256": self.sha256,
            "bytes": self.byte_length,
        }

@dataclass(frozen=True)
class PreparedPrivatePublication:
    """Locally verified immutable generation ready for private-store publish."""

    generation_id: str
    manifest_key: str
    manifest: Mapping[str, Any]
    manifest_bytes: bytes
    artifacts: tuple[PrivateArtifact, ...]
    payloads: Mapping[str, bytes]
    retired_slots: tuple[str, ...] = ()

def _strict_object(value: Any, *, keys: frozenset[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise EarningsPrivatePublicationError(f"{name} fields mismatch")
    return value

def _json_object(body: bytes, *, maximum: int, name: str) -> dict[str, Any]:
    if not isinstance(body, bytes) or not body or len(body) > maximum:
        raise EarningsPrivatePublicationError(f"{name} exceeds its safe size bound")
    try:
        value = json.loads(
            body.decode("utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EarningsPrivatePublicationError(f"{name} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != body:
        raise EarningsPrivatePublicationError(f"{name} is not canonical JSON")
    return value

def validate_slug(value: str) -> str:
    if not isinstance(value, str) or not _SLUG_RE.fullmatch(value):
        raise EarningsPrivatePublicationError("invalid earnings record slug")
    return value

def validate_ticker(value: str) -> str:
    if not isinstance(value, str) or not _TICKER_RE.fullmatch(value):
        raise EarningsPrivatePublicationError("invalid earnings context ticker")
    return value


def validate_generation_id(value: str) -> str:
    if type(value) is not str or not _GENERATION_RE.fullmatch(value):
        raise EarningsPrivatePublicationError("invalid earnings generation id")
    return value


def validate_digest(value: str) -> str:
    if type(value) is not str or not _SHA_RE.fullmatch(value):
        raise EarningsPrivatePublicationError("invalid earnings digest")
    return value

def _safe_fragment(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_RECORD_BYTES:
        raise EarningsPrivatePublicationError(f"private record {field} is invalid")
    if _UNSAFE_HTML_RE.search(value):
        raise EarningsPrivatePublicationError(f"private record {field} contains active content")
    return value

def validate_v1_record(value: object, *, expected_slug: str | None = None) -> dict[str, Any]:
    record = _strict_object(
        value,
        keys=frozenset(
            {
                "schema",
                "page",
                "slug",
                "required_tier",
                "public_facts",
                "locked_facts",
                "facts_html",
                "receipt_rows_html",
            }
        ),
        name="private earnings record",
    )
    slug = validate_slug(record.get("slug"))
    if expected_slug is not None and slug != validate_slug(expected_slug):
        raise EarningsPrivatePublicationError("private record slug does not match its identity")
    if (
        record.get("schema") != RECORD_SCHEMA
        or record.get("page") != "earnings_wire_article"
        or record.get("required_tier") != "essential"
    ):
        raise EarningsPrivatePublicationError("private record contract is invalid")
    for field in ("public_facts", "locked_facts"):
        count = record.get(field)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 10_000:
            raise EarningsPrivatePublicationError(f"private record {field} is invalid")
    if record["locked_facts"] < 1:
        raise EarningsPrivatePublicationError("private record must contain a member continuation")
    _safe_fragment(record.get("facts_html"), field="facts_html")
    _safe_fragment(record.get("receipt_rows_html"), field="receipt_rows_html")
    return dict(record)

def _interpretation_shape(value: Any) -> dict[str, Any] | None:
    if type(value) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    if value.get("schema") != economic_interpretation.SCHEMA:
        raise EarningsPrivateClosureError("interpretation_unsupported")
    if set(value) != set(economic_interpretation.TOP_LEVEL_KEYS):
        raise EarningsPrivateClosureError("malformed_native_section")
    if (
        type(value.get("interpretation_id")) is not str
        or type(value.get("event_id")) is not str
        or type(value.get("issuer")) is not dict
        or type(value.get("issuer", {}).get("company_id")) is not str
    ):
        raise EarningsPrivateClosureError("malformed_native_section")
    observations = value.get("observations")
    comparisons = value.get("comparisons")
    if (
        type(observations) is not list
        or type(comparisons) is not list
    ):
        raise EarningsPrivateClosureError("malformed_native_section")
    if (
        len(observations) > MAX_ECONOMIC_FACTS
        or len(comparisons) > MAX_ECONOMIC_COMPARISONS
    ):
        raise EarningsPrivateClosureError("over_limit")
    return value

def _validate_interpretation_field(value: Any) -> dict[str, Any]:
    unavailable = {"state": "unavailable", "reason": "no_native_selection"}
    if type(value) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    if set(value) == {"state", "reason"}:
        if value != unavailable:
            raise EarningsPrivateClosureError("malformed_native_section")
        return value
    return _interpretation_shape(value)

def validate_v2_record(value: object, *, expected_slug: str | None = None) -> dict[str, Any]:
    if type(value) is not dict or set(value) != frozenset(
        {
            "schema", "page", "slug", "required_tier", "public_facts", "locked_facts",
            "facts_html", "receipt_rows_html", "economic_interpretation",
        }
    ):
        raise EarningsPrivateClosureError("malformed_native_section")
    shared = {key: value[key] for key in (
        "schema", "page", "slug", "required_tier", "public_facts", "locked_facts",
        "facts_html", "receipt_rows_html",
    )}
    shared["schema"] = RECORD_SCHEMA
    shared["page"] = "earnings_wire_article"
    record = validate_v1_record(shared, expected_slug=expected_slug)
    record["schema"] = RECORD_SCHEMA_V2
    record["page"] = value["page"]
    if value["page"] not in ("earnings_wire_article", DOSSIER_PAGE):
        raise EarningsPrivateClosureError("malformed_native_section")
    interpretation = _validate_interpretation_field(value["economic_interpretation"])
    if record["page"] == DOSSIER_PAGE:
        if (
            record["required_tier"] != "essential"
            or record["public_facts"] != 0
            or record["facts_html"] != ""
            or record["receipt_rows_html"] != ""
            or set(interpretation) == {"state", "reason"}
            or record["locked_facts"] != len(interpretation.get("observations", []))
            or not 1 <= record["locked_facts"] <= MAX_ECONOMIC_FACTS
        ):
            raise EarningsPrivateClosureError("malformed_native_section")
    return {**record, "economic_interpretation": interpretation}

def validate_private_record(value: object, *, expected_slug: str | None = None) -> dict[str, Any]:
    if type(value) is not dict:
        return validate_v1_record(value, expected_slug=expected_slug)
    schema = value.get("schema")
    if schema == RECORD_SCHEMA:
        return validate_v1_record(value, expected_slug=expected_slug)
    if schema == RECORD_SCHEMA_V2:
        return validate_v2_record(value, expected_slug=expected_slug)
    raise EarningsPrivateClosureError("unsupported_schema", "unsupported private record schema")

def _stage_file(root: Path, relative: Path, *, maximum: int, name: str) -> bytes:
    root = root.resolve()
    path = root / relative
    # The staging tree is produced locally, but a no-symlink boundary prevents a
    # caller from turning the publisher into an arbitrary-file reader.
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise EarningsPrivatePublicationError(f"{name} cannot traverse a symlink")
        cursor = cursor.parent
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        size = resolved.stat().st_size
        if not resolved.is_file() or size <= 0 or size > maximum:
            raise EarningsPrivatePublicationError(f"{name} exceeds its safe size bound")
        body = resolved.read_bytes()
    except EarningsPrivatePublicationError:
        raise
    except (OSError, ValueError) as exc:
        raise EarningsPrivatePublicationError(f"{name} is unavailable") from exc
    if len(body) != size:
        raise EarningsPrivatePublicationError(f"{name} changed during read")
    return body

def _object_key(role: str, digest: str) -> str:
    suffix = _ARTIFACT_ROLES[role][0]
    return f"{PRIVATE_PREFIX}/objects/sha256/{digest[:2]}/{digest}{suffix}"

def _artifact(role: str, identity: str, body: bytes, *, maximum: int | None = None) -> PrivateArtifact:
    suffix, content_type, maximum = _ARTIFACT_ROLES[role]
    digest = sha256(body).hexdigest()
    return PrivateArtifact(
        role=role,
        identity=identity,
        object_key=_object_key(role, digest),
        sha256=digest,
        byte_length=len(body),
        maximum_bytes=maximum,
        content_type=content_type,
    )

def _generation_id(manifest: Mapping[str, Any]) -> str:
    unsigned = dict(manifest)
    unsigned["generation_id"] = "earnpriv_" + ("0" * 32)
    return "earnpriv_" + sha256(canonical_json_bytes(unsigned)).hexdigest()[:32]

def _validate_v1_receipt(value: Any, *, name: str) -> Mapping[str, Any]:
    receipt = _strict_object(
        value,
        keys=frozenset({"object_key", "sha256", "bytes"}),
        name=name,
    )
    if (
        not isinstance(receipt.get("object_key"), str)
        or not _OBJECT_KEY_RE.fullmatch(receipt["object_key"])
        or not isinstance(receipt.get("sha256"), str)
        or not _SHA_RE.fullmatch(receipt["sha256"])
        or receipt["object_key"].split("/")[-1] != f"{receipt['sha256']}.json"
        or isinstance(receipt.get("bytes"), bool)
        or not isinstance(receipt.get("bytes"), int)
        or receipt["bytes"] <= 0
    ):
        raise EarningsPrivatePublicationError(f"{name} is invalid")
    return receipt

def _validate_receipt(value: Any, *, name: str, role: str | None = None) -> Mapping[str, Any]:
    if role is None:
        return _validate_v1_receipt(value, name=name)
    if type(value) is not dict or set(value) != {"object_key", "sha256", "bytes"}:
        raise EarningsPrivateClosureError("malformed_native_section")
    receipt = value
    digest = receipt.get("sha256")
    count = receipt.get("bytes")
    object_key = receipt.get("object_key")
    if (
        type(digest) is not str
        or not _SHA_RE.fullmatch(digest)
        or type(count) is not int
        or count < 1
    ):
        raise EarningsPrivateClosureError("malformed_native_section")
    suffix, _content_type, maximum = _ARTIFACT_ROLES[role]
    expected = _object_key(role, digest)
    if type(object_key) is str and object_key == expected:
        if count > maximum:
            raise EarningsPrivateClosureError("over_limit")
        return receipt
    if type(object_key) is str:
        for other in _ARTIFACT_ROLES:
            if other != role and object_key == _object_key(other, digest):
                raise EarningsPrivateClosureError("wrong_role")
    raise EarningsPrivateClosureError("unsafe_path")

def _validate_v1_manifest(value: object, *, check_generation: bool = True) -> dict[str, Any]:
    manifest = _strict_object(
        value,
        keys=frozenset(
            {
                "schema",
                "generation_id",
                "published_at",
                "source",
                "record_count",
                "ticker_count",
                "records",
                "context",
            }
        ),
        name="private earnings manifest",
    )
    generation_id = manifest.get("generation_id")
    if (
        manifest.get("schema") != MANIFEST_SCHEMA
        or (check_generation and (
            not isinstance(generation_id, str)
            or not _GENERATION_RE.fullmatch(generation_id)
            or generation_id != _generation_id(manifest)
        ))
    ):
        raise EarningsPrivatePublicationError("private earnings generation identity is invalid")
    if not isinstance(manifest.get("published_at"), str) or len(manifest["published_at"]) > 64:
        raise EarningsPrivatePublicationError("private earnings publication clock is invalid")
    source = _strict_object(
        manifest.get("source"),
        keys=frozenset({"wire_manifest_id", "source_generation_id", "source_manifest_sha256"}),
        name="private earnings source",
    )
    if any(not isinstance(source.get(key), str) or not source[key] for key in source):
        raise EarningsPrivatePublicationError("private earnings source binding is invalid")
    if not _SHA_RE.fullmatch(source["source_manifest_sha256"]):
        raise EarningsPrivatePublicationError("private earnings source digest is invalid")
    records = manifest.get("records")
    context = manifest.get("context")
    if not isinstance(records, Mapping) or not 0 <= len(records) <= MAX_RECORDS:
        raise EarningsPrivatePublicationError("private earnings record catalog is invalid")
    if (
        isinstance(manifest.get("record_count"), bool)
        or manifest.get("record_count") != len(records)
    ):
        raise EarningsPrivatePublicationError("private earnings record count is invalid")
    for slug, receipt in records.items():
        validate_slug(slug)
        _validate_receipt(receipt, name=f"private record receipt {slug}")
    context = _strict_object(
        context,
        keys=frozenset({"manifest", "objects"}),
        name="private earnings context catalog",
    )
    context_objects = context.get("objects")
    if not isinstance(context_objects, Mapping) or len(context_objects) > MAX_CONTEXT_PACKETS:
        raise EarningsPrivatePublicationError("private earnings context objects are invalid")
    if (
        isinstance(manifest.get("ticker_count"), bool)
        or manifest.get("ticker_count") != len(context_objects)
    ):
        raise EarningsPrivatePublicationError("private earnings ticker count is invalid")
    _validate_receipt(context.get("manifest"), name="private context manifest receipt")
    for ticker, receipt in context_objects.items():
        validate_ticker(ticker)
        _validate_receipt(receipt, name=f"private context receipt {ticker}")
    return dict(manifest)

def validate_v1_manifest(value: object) -> dict[str, Any]:
    return _validate_v1_manifest(value)

def _canonical_clock(value: Any, *, date: bool = False) -> str:
    pattern = _CANONICAL_DATE_RE if date else _CANONICAL_CLOCK_RE
    if (
        type(value) is not str
        or pattern.fullmatch(value) is None
    ):
        raise EarningsPrivateClosureError("malformed_native_section")
    try:
        datetime.strptime(value, "%Y-%m-%d" if date else "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise EarningsPrivateClosureError("malformed_native_section") from exc
    return value

def _validate_native_selection(value: Any, slug: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "company_id", "event_id", "profile_version", "fiscal_scope", "chain", "selection", "interpretation_id",
    }:
        raise EarningsPrivateClosureError("malformed_native_section")
    for field in ("company_id", "event_id", "profile_version"):
        if type(value[field]) is not str:
            raise EarningsPrivateClosureError("malformed_native_section")
    scope = value["fiscal_scope"]
    if type(scope) is not list or len(scope) != 4:
        raise EarningsPrivateClosureError("malformed_native_section")
    for item in scope:
        _canonical_clock(item, date=True)
    chain = value["chain"]
    if type(chain) is not list:
        raise EarningsPrivateClosureError("malformed_native_section")
    if len(chain) > MAX_NATIVE_CHAIN:
        raise EarningsPrivateClosureError("over_limit")
    if not chain:
        raise EarningsPrivateClosureError("malformed_native_section")
    for entry in chain:
        if type(entry) is not dict or set(entry) != {"workspace", "document"}:
            raise EarningsPrivateClosureError("malformed_native_section")
        if (
            type(entry["workspace"]) is not str
            or not _NATIVE_GENERATION_ID_RE.fullmatch(entry["workspace"])
            or type(entry["document"]) is not str
            or not _SHA_RE.fullmatch(entry["document"])
        ):
            raise EarningsPrivateClosureError("unsafe_path")
    selection = value["selection"]
    if type(selection) is not dict or set(selection) != {"facts", "currentness"}:
        raise EarningsPrivateClosureError("malformed_native_section")
    facts = selection["facts"]
    if facts is not None:
        if type(facts) is not list:
            raise EarningsPrivateClosureError("malformed_native_section")
        if len(facts) > MAX_ECONOMIC_FACTS:
            raise EarningsPrivateClosureError("over_limit")
        if not facts:
            raise EarningsPrivateClosureError("malformed_native_section")
        for handle in facts:
            if type(handle) is not dict or set(handle) != {
                "workspace_generation_id", "event_id", "fact_id",
            }:
                raise EarningsPrivateClosureError("malformed_native_section")
            if any(type(handle[field]) is not str for field in handle):
                raise EarningsPrivateClosureError("malformed_native_section")
    currentness = selection["currentness"]
    if currentness is not None:
        if type(currentness) is not dict or set(currentness) != {"state", "source_clock"}:
            raise EarningsPrivateClosureError("malformed_native_section")
        if type(currentness["state"]) is not str:
            raise EarningsPrivateClosureError("malformed_native_section")
        if currentness["source_clock"] is not None:
            _canonical_clock(currentness["source_clock"])
    if type(value["interpretation_id"]) is not str or not _INTERPRETATION_ID_RE.fullmatch(value["interpretation_id"]):
        raise EarningsPrivateClosureError("malformed_native_section")
    return value

def _validate_native_section(value: Any, *, manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "workspaces", "documents", "source_bodies", "selections", "economic_slots",
    }:
        raise EarningsPrivateClosureError("malformed_native_section")
    catalogs: dict[str, dict[str, Any]] = {}
    for catalog_name in ("workspaces", "documents", "source_bodies"):
        catalog = value[catalog_name]
        if type(catalog) is not dict:
            raise EarningsPrivateClosureError("malformed_native_section")
        role = _NATIVE_CATALOG_ROLES[catalog_name]
        for identity, receipt in (
            catalog.items() if catalog_name != "source_bodies"
            else [(digest, item["text"]) for digest, item in catalog.items()]
        ):
            if type(identity) is not str:
                raise EarningsPrivateClosureError("unsafe_path")
            if catalog_name == "workspaces" and not _NATIVE_GENERATION_ID_RE.fullmatch(identity):
                raise EarningsPrivateClosureError("unsafe_path")
            if catalog_name != "workspaces" and not _SHA_RE.fullmatch(identity):
                raise EarningsPrivateClosureError("unsafe_path")
            _validate_receipt(receipt, name=f"native {catalog_name} receipt", role=role)
            if catalog_name != "workspaces" and receipt["sha256"] != identity:
                raise EarningsPrivateClosureError("digest_mismatch")
            catalogs[catalog_name] = catalog
    for digest, body in value["source_bodies"].items():
        if type(body) is not dict or set(body) != {"text", "received"}:
            raise EarningsPrivateClosureError("malformed_native_section")
        text = _validate_receipt(body["text"], name="native source body receipt", role="source_body_text")
        if text["sha256"] != digest:
            raise EarningsPrivateClosureError("digest_mismatch")
        received = body["received"]
        if type(received) is not dict or set(received) != {"sha256", "length", "declared_encoding"}:
            raise EarningsPrivateClosureError("malformed_native_section")
        if (
            type(received["sha256"]) is not str
            or type(received["length"]) is not int
            or received["sha256"] != digest
            or received["length"] != text["bytes"]
            or received["declared_encoding"] != "utf-8"
        ):
            raise EarningsPrivateClosureError("mismatched_source")
    selections = value["selections"]
    if type(selections) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    for slug, selection in selections.items():
        validate_slug(slug)
        value["selections"][slug] = _validate_native_selection(selection, slug)
    slots = value["economic_slots"]
    if type(slots) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    for company_id, slot in slots.items():
        if type(company_id) is not str or type(slot) is not dict or set(slot) != {"slug", "event_id"}:
            raise EarningsPrivateClosureError("malformed_native_section")
        if type(slot["slug"]) is not str or type(slot["event_id"]) is not str:
            raise EarningsPrivateClosureError("malformed_native_section")
    if manifest is None:
        object_keys = []
    else:
        object_keys = [receipt["object_key"] for receipt in manifest["records"].values()]
        object_keys.append(manifest["context"]["manifest"]["object_key"])
        object_keys.extend(receipt["object_key"] for receipt in manifest["context"]["objects"].values())
    for catalog_name in ("workspaces", "documents"):
        object_keys.extend(receipt["object_key"] for receipt in catalogs[catalog_name].values())
    object_keys.extend(entry["text"]["object_key"] for entry in value["source_bodies"].values())
    if len(object_keys) != len(set(object_keys)):
        raise EarningsPrivateClosureError("wrong_role")
    return value

def _validate_previous_manifest(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != {
        "generation_id", "manifest_key", "manifest_sha256", "manifest_bytes", "published_at",
    }:
        raise EarningsPrivateClosureError("malformed_native_section")
    validate_private_pointer({"schema": POINTER_SCHEMA, **value})
    return dict(value)

def _native_json(body: bytes, *, maximum: int, name: str) -> dict[str, Any]:
    if type(body) is not bytes or not body or len(body) > maximum:
        raise EarningsPrivateClosureError("over_limit")
    try:
        return _json_object(body, maximum=maximum, name=name)
    except (EarningsPrivatePublicationError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise EarningsPrivateClosureError("malformed_native_section") from exc


def _verify_body(body: bytes, receipt: Mapping[str, Any], maximum: int) -> None:
    if body is None:
        raise EarningsPrivateClosureError("missing_artifact")
    if len(body) > maximum:
        raise EarningsPrivateClosureError("over_limit")
    if len(body) != receipt["bytes"]:
        raise EarningsPrivateClosureError("size_mismatch")
    if sha256(body).hexdigest() != receipt["sha256"]:
        raise EarningsPrivateClosureError("digest_mismatch")

def _seam(call: Any, reason: str) -> Any:
    try:
        return call()
    except EarningsPrivateClosureError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize contract boundary
        raise EarningsPrivateClosureError(reason) from exc
def _document_roundtrip(document: Mapping[str, Any]) -> bool:
    return _seam(
        lambda: _unsafe_document_roundtrip(document),
        "malformed_native_section",
    )


def _unsafe_document_roundtrip(document: Mapping[str, Any]) -> bool:
    if (
        document.get("schema") != documents.DOCUMENT_SCHEMA
        or document.get("authority") != documents.AUTHORITY
    ):
        return False
    fields = {key: value for key, value in document.items() if key not in ("schema", "authority", "filing_key")}
    filing = document.get("filing_key")
    if type(filing) is not dict:
        return False
    rebuilt = documents.SourceDocument(**fields, filing_key=documents.FilingKey(**filing)).to_payload()
    return rebuilt == document

def _safe_field(mapping: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        return mapping[key]
    except (KeyError, TypeError, ValueError) as exc:
        raise EarningsPrivateClosureError("malformed_native_section") from exc

def validate_native_closure(
    manifest: Mapping[str, Any],
    objects: Mapping[str, bytes],
    *,
    slugs: tuple[str, ...] | list[str] | None = None,
    interpretations: bool = True,
) -> dict[str, dict[str, Any]]:
    try:
        if type(manifest) is not dict:
            try:
                manifest = dict(manifest)
            except (TypeError, ValueError) as exc:
                raise EarningsPrivateClosureError("malformed_native_section") from exc
        value = validate_private_manifest(manifest)
        record_slugs = tuple(sorted(value["records"]))
        selected_slugs = tuple(slugs) if slugs is not None else record_slugs
        for slug in selected_slugs:
            validate_slug(slug)
        if any(slug not in value["records"] for slug in selected_slugs):
            raise EarningsPrivateClosureError("missing_artifact")

        if slugs is None:
            expected_keys = {receipt["object_key"] for receipt in value["records"].values()}
            expected_keys.add(value["context"]["manifest"]["object_key"])
            expected_keys.update(receipt["object_key"] for receipt in value["context"]["objects"].values())
            native = value["native"]
            for catalog in ("workspaces", "documents"):
                expected_keys.update(receipt["object_key"] for receipt in native[catalog].values())
            expected_keys.update(entry["text"]["object_key"] for entry in native["source_bodies"].values())
            if set(objects) != expected_keys:
                unexpected = set(objects) - expected_keys
                if unexpected:
                    raise EarningsPrivateClosureError("unexpected_artifact")
                raise EarningsPrivateClosureError("missing_artifact")
        else:
            native = value["native"]

        records: dict[str, dict[str, Any]] = {}
        chains: dict[str, list[dict[str, Any]]] = {}
        for slug in selected_slugs:
            receipt = value["records"][slug]
            role = "record"
            body = objects.get(receipt["object_key"])
            if body is None:
                raise EarningsPrivateClosureError("missing_artifact")
            _verify_body(body, receipt, _ARTIFACT_ROLES[role][2])
            record = validate_private_record(
                _native_json(body, maximum=_ARTIFACT_ROLES[role][2], name=f"record {slug}"),
                expected_slug=slug,
            )
            records[slug] = record
            chains[slug] = []
            if slug not in native["selections"]:
                continue
            selection = native["selections"][slug]
            for index, entry in enumerate(selection["chain"], start=1):
                if entry["workspace"] not in native["workspaces"] or entry["document"] not in native["documents"]:
                    raise EarningsPrivateClosureError("missing_artifact")
                workspace_receipt = native["workspaces"][entry["workspace"]]
                workspace_body = objects.get(workspace_receipt["object_key"])
                if workspace_body is None:
                    raise EarningsPrivateClosureError("missing_artifact")
                _verify_body(workspace_body, workspace_receipt, MAX_NATIVE_WORKSPACE_BYTES)
                workspace = _native_json(workspace_body, maximum=MAX_NATIVE_WORKSPACE_BYTES, name="native workspace")
                _seam(lambda: event_workspace.validate_event_workspace(workspace), "malformed_native_section")
                computed = _seam(
                    lambda: event_workspace.preview_generation_identity(
                        {workspace["event_id"]: workspace},
                        workspace["generated_at"],
                        previous_generation_id=None,
                    ),
                    "malformed_native_section",
                )
                if (
                    computed != workspace.get("generation_id")
                    or workspace.get("generation_id") != entry["workspace"]
                ):
                    raise EarningsPrivateClosureError("digest_mismatch")
                document_receipt = native["documents"][entry["document"]]
                document_body = objects.get(document_receipt["object_key"])
                if document_body is None:
                    raise EarningsPrivateClosureError("missing_artifact")
                _verify_body(document_body, document_receipt, MAX_NATIVE_DOCUMENT_BYTES)
                document = _native_json(document_body, maximum=MAX_NATIVE_DOCUMENT_BYTES, name="native document")
                if not _document_roundtrip(document):
                    raise EarningsPrivateClosureError("malformed_native_section")
                if (
                    document.get("rights_profile") != pg_profile.PG_PRIVATE_RIGHTS_PROFILE
                    or document.get("rights_state") != "internal_only"
                    or document.get("holds_bytes") is not False
                ):
                    raise EarningsPrivateClosureError("malformed_native_section")
                if document.get("revision") != index:
                    raise EarningsPrivateClosureError("broken_chain")
                predecessor = document.get("supersedes_document_id")
                if index == 1:
                    if predecessor == document.get("document_id"):
                        raise EarningsPrivateClosureError("predecessor_cycle")
                    if predecessor is not None:
                        raise EarningsPrivateClosureError("broken_chain")
                else:
                    prior = chains[slug][-1]["document"]
                    if predecessor == document.get("document_id"):
                        raise EarningsPrivateClosureError("predecessor_cycle")
                    if predecessor != prior.get("document_id"):
                        raise EarningsPrivateClosureError("broken_chain")
                digest = document.get("content_sha256")
                if type(digest) is not str or digest not in native["source_bodies"]:
                    raise EarningsPrivateClosureError("missing_artifact")
                source = native["source_bodies"][digest]
                text_receipt = source["text"]
                text_body = objects.get(text_receipt["object_key"])
                if text_body is None:
                    raise EarningsPrivateClosureError("missing_artifact")
                _verify_body(text_body, text_receipt, MAX_SOURCE_BODY_BYTES)
                try:
                    text = text_body.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise EarningsPrivateClosureError("mismatched_source") from exc
                lifecycle = _safe_field(workspace, "lifecycle", {})
                release_rows = [row for row in _safe_field(workspace, "sources", []) if type(row) is dict and row.get("kind") == "issuer_release"]
                if len(release_rows) != 1:
                    raise EarningsPrivateClosureError("mismatched_source")
                release = release_rows[0]
                if (
                    document.get("content_bytes") != len(text_body)
                    or release.get("source_sha256") != sha256(text_body).hexdigest()
                    or release.get("document_id") != document.get("document_id")
                    or release.get("filing_key") != document.get("filing_key")
                    or document.get("event_id") != workspace.get("event_id")
                    or workspace.get("event_id") != selection.get("event_id")
                    or document.get("available_at") != _safe_field(lifecycle, "source_available_at")
                ):
                    raise EarningsPrivateClosureError("mismatched_source")
                if _safe_field(_safe_field(workspace, "issuer", {}), "company_id") != selection.get("company_id"):
                    raise EarningsPrivateClosureError("cross_issuer")
                clocks = (
                    _safe_field(lifecycle, "source_available_at"),
                    _safe_field(lifecycle, "observed_at"),
                    _safe_field(workspace, "generated_at"),
                    document.get("available_at"),
                    document.get("fetched_at"),
                )
                canonical_clocks = tuple(_canonical_clock(clock) for clock in clocks)
                cutoff = value["native_source_cutoff"]
                if canonical_clocks[0] > canonical_clocks[1] or any(clock > cutoff for clock in canonical_clocks):
                    raise EarningsPrivateClosureError("future_source_clock")
                currentness = selection["selection"]["currentness"]
                if currentness is not None and currentness["source_clock"] > cutoff:
                    raise EarningsPrivateClosureError("future_source_clock")
                if chains[slug] and canonical_clocks[0] < chains[slug][-1]["source_available_at"]:
                    raise EarningsPrivateClosureError("broken_chain")
                chains[slug].append({
                    "workspace": workspace,
                    "document": document,
                    "text": text,
                    "source_available_at": canonical_clocks[0],
                })

        registry = _seam(pg_profile.pg_private_registry, "cross_issuer")
        for company_id in native["economic_slots"]:
            if _seam(lambda: registry.get(company_id), "cross_issuer") is None:
                raise EarningsPrivateClosureError("cross_issuer")
        for slug, selection in native["selections"].items():
            if slug not in records:
                continue
            if _seam(lambda: registry.get(selection["company_id"]), "cross_issuer") is None:
                raise EarningsPrivateClosureError("cross_issuer")

        pairings: dict[str, dict[str, Any]] = {}
        events: dict[tuple[str, str], str] = {}
        for selection_slug in native["selections"]:
            if selection_slug not in records:
                raise EarningsPrivateClosureError("malformed_native_section")
        for slug, record in records.items():
            interpretation = record.get("economic_interpretation")
            has_native = type(interpretation) is dict and "interpretation_id" in interpretation
            has_selection = slug in native["selections"]
            if (record["schema"] == RECORD_SCHEMA_V2 and has_native) != has_selection:
                raise EarningsPrivateClosureError("malformed_native_section")
            if record["schema"] == RECORD_SCHEMA and has_selection:
                raise EarningsPrivateClosureError("malformed_native_section")
            if has_selection:
                selection = native["selections"][slug]
                identity = (selection["company_id"], selection["event_id"])
                if identity in events:
                    raise EarningsPrivateClosureError("malformed_native_section")
                events[identity] = slug
                pairings[slug] = {
                    key: interpretation[key] for key in economic_interpretation.TOP_LEVEL_KEYS
                }
        for company_id, slot in native["economic_slots"].items():
            slug = slot["slug"]
            if slug not in native["selections"]:
                raise EarningsPrivateClosureError("malformed_native_section")
            selection = native["selections"][slug]
            if (
                selection["company_id"] != company_id
                or selection["event_id"] != slot["event_id"]
            ):
                raise EarningsPrivateClosureError("malformed_native_section")

        if slugs is None:
            named_native = set(native["workspaces"]) | set(native["documents"])
            for selection in native["selections"].values():
                for entry in selection["chain"]:
                    named_native.discard(entry["workspace"])
                    named_native.discard(entry["document"])
            if named_native:
                raise EarningsPrivateClosureError("unexpected_artifact")

        if not interpretations:
            return {
                slug: {
                    "record": records[slug],
                    "selection": native["selections"].get(slug),
                    "interpretation": pairings.get(slug),
                    "chain": chains[slug],
                }
                for slug in selected_slugs
            }

        for slug in selected_slugs:
            if slug not in pairings:
                continue
            selection = native["selections"][slug]
            stored = pairings[slug]
            newest = chains[slug][-1]
            if selection["profile_version"] != pg_profile.PG_PROFILE_VERSION:
                raise EarningsPrivateClosureError("interpretation_unsupported")
            if (
                stored["interpretation_id"] != selection["interpretation_id"]
                or stored["event_id"] != selection["event_id"]
            ):
                raise EarningsPrivateClosureError("interpretation_mismatch")
            if stored["issuer"]["company_id"] != selection["company_id"]:
                raise EarningsPrivateClosureError("cross_issuer")
            ordered = {key: stored[key] for key in economic_interpretation.TOP_LEVEL_KEYS}
            texts = {newest["document"]["document_id"]: newest["text"]}
            scope = tuple(selection["fiscal_scope"])
            try:
                economic_interpretation.validate_economic_interpretation(
                    ordered,
                    workspaces=newest["workspace"],
                    source_texts=texts,
                    fiscal_scope=scope,
                )
            except economic_interpretation.UnsupportedInterpretationVersion as exc:
                raise EarningsPrivateClosureError("interpretation_unsupported") from exc
            except Exception as exc:  # noqa: BLE001 - normalize contract boundary
                raise EarningsPrivateClosureError("interpretation_mismatch") from exc
            try:
                rebuilt = economic_interpretation.build_economic_interpretation(
                    newest["workspace"],
                    source_texts=texts,
                    fiscal_scope=scope,
                    selection=selection["selection"],
                    semantic_revision=economic_interpretation.SEMANTIC_REVISION,
                    code_revision=economic_interpretation.CODE_REVISION,
                )
            except economic_interpretation.UnsupportedInterpretationVersion as exc:
                raise EarningsPrivateClosureError("interpretation_unsupported") from exc
            except Exception as exc:  # noqa: BLE001 - normalize contract boundary
                raise EarningsPrivateClosureError("interpretation_mismatch") from exc
            if canonical_json_bytes(rebuilt) != canonical_json_bytes(stored):
                raise EarningsPrivateClosureError("interpretation_mismatch")
        return {
            slug: {
                "record": records[slug],
                "selection": native["selections"].get(slug),
                "interpretation": pairings.get(slug),
                "chain": chains[slug],
            }
            for slug in selected_slugs
        }
    except EarningsPrivateClosureError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise EarningsPrivateClosureError("malformed_native_section") from exc

def validate_v2_manifest(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema", "generation_id", "published_at", "source", "record_count", "ticker_count",
        "records", "context", "native", "native_source_cutoff", "previous_manifest",
    }:
        raise EarningsPrivateClosureError("malformed_native_section")
    shared = dict(value)
    shared["schema"] = MANIFEST_SCHEMA
    del shared["native"], shared["native_source_cutoff"], shared["previous_manifest"]
    base = _validate_v1_manifest(shared, check_generation=False)
    base["schema"] = MANIFEST_SCHEMA_V2
    _canonical_clock(value["native_source_cutoff"])
    _validate_previous_manifest(value["previous_manifest"])
    native = _validate_native_section(value["native"], manifest=value)
    generation_id = value.get("generation_id")
    if (
        type(generation_id) is not str
        or not _GENERATION_RE.fullmatch(generation_id)
        or generation_id != _generation_id(value)
    ):
        raise EarningsPrivateClosureError("digest_mismatch", "private earnings generation identity is invalid")
    return {**base, "native": native, "native_source_cutoff": value["native_source_cutoff"], "previous_manifest": value["previous_manifest"]}

def validate_private_manifest(value: object) -> dict[str, Any]:
    if type(value) is not dict:
        try:
            validate_v1_manifest(value)
        except EarningsPrivatePublicationError:
            raise EarningsPrivateClosureError("malformed_native_section") from None
        value = dict(value)
    schema = value.get("schema")
    if schema == MANIFEST_SCHEMA:
        return validate_v1_manifest(value)
    if schema == MANIFEST_SCHEMA_V2:
        return validate_v2_manifest(value)
    raise EarningsPrivateClosureError("unsupported_schema", "unsupported private manifest schema")

def _native_stage_manifest(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema", "native_source_cutoff", "previous_manifest", "selections", "economic_slots", "received",
    }:
        raise EarningsPrivateClosureError("malformed_native_section")
    if value["schema"] != NATIVE_STAGE_SCHEMA:
        raise EarningsPrivateClosureError("unsupported_schema")
    _canonical_clock(value["native_source_cutoff"])
    _validate_previous_manifest(value["previous_manifest"])
    selections = value["selections"]
    if type(selections) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    for slug, selection in selections.items():
        validate_slug(slug)
        _validate_native_selection(selection, slug)
    slots = value["economic_slots"]
    if type(slots) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    for company_id, slot in slots.items():
        if type(company_id) is not str or type(slot) is not dict or set(slot) != {"slug", "event_id"}:
            raise EarningsPrivateClosureError("malformed_native_section")
        if type(slot["slug"]) is not str or type(slot["event_id"]) is not str:
            raise EarningsPrivateClosureError("malformed_native_section")
    received = value["received"]
    if type(received) is not dict:
        raise EarningsPrivateClosureError("malformed_native_section")
    for digest, receipt in received.items():
        if type(digest) is not str or not _SHA_RE.fullmatch(digest):
            raise EarningsPrivateClosureError("unsafe_path")
        if (
            type(receipt) is not dict
            or set(receipt) != {"sha256", "length", "declared_encoding"}
            or receipt.get("sha256") != digest
            or type(receipt.get("length")) is not int
            or receipt.get("declared_encoding") != "utf-8"
        ):
            raise EarningsPrivateClosureError("malformed_native_section")
    return value

def _native_stage_file(root: Path, relative: str, maximum: int) -> bytes:
    if not _NATIVE_PATH_RE.fullmatch(relative):
        raise EarningsPrivateClosureError("unsafe_path")
    path = root / Path(relative)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise EarningsPrivateClosureError("missing_artifact") from exc
    if size == 0:
        raise EarningsPrivateClosureError("malformed_native_section")
    if size > maximum:
        raise EarningsPrivateClosureError("over_limit")
    try:
        return _stage_file(root, Path(relative), maximum=maximum, name="native stage file")
    except EarningsPrivatePublicationError as exc:
        if "cannot traverse a symlink" in str(exc):
            raise EarningsPrivateClosureError("unsafe_path") from exc
        if "exceeds its safe size bound" in str(exc):
            raise EarningsPrivateClosureError("over_limit") from exc
        if "is unavailable" in str(exc):
            raise EarningsPrivateClosureError("missing_artifact") from exc
        raise EarningsPrivateClosureError("malformed_native_section") from exc

def _write_stage_file(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)

def assert_native_rights() -> None:
    try:
        family = pg_profile.source_family_for_profile(pg_profile.RIGHTS_PROFILE)
        rights.assert_public_emission_allowed(family, path=NATIVE_RIGHTS_REGISTRY_PATH)
    except EarningsPrivateClosureError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize contract boundary
        raise EarningsPrivateClosureError("rights_refused") from exc

def _prepare_v2_private_publication(
    root: Path,
    records: tuple[tuple[str, bytes], ...],
    context_manifest_body: bytes,
    context_packets: tuple[tuple[str, bytes], ...],
    retired_slots: tuple[str, ...],
) -> PreparedPrivatePublication:
    native_root = root / NATIVE_STAGE_DIR
    if native_root.is_symlink() or not native_root.is_dir():
        raise EarningsPrivateClosureError("unsafe_path")
    artifacts: list[PrivateArtifact] = []
    payloads: dict[str, bytes] = {}
    record_receipts: dict[str, dict[str, Any]] = {}
    expected_paths: set[Path] = set()
    for slug, body in records:
        validate_private_record(_native_json(body, maximum=MAX_RECORD_BYTES, name=f"record {slug}"), expected_slug=slug)
        artifact = _artifact("record", slug, body, maximum=MAX_RECORD_BYTES)
        artifacts.append(artifact)
        payloads[artifact.object_key] = body
        record_receipts[slug] = artifact.receipt()
        expected_paths.add((root / RECORD_STAGE_DIR / f"{slug}.json").resolve())

    context_manifest = _native_json(context_manifest_body, maximum=MAX_CONTEXT_MANIFEST_BYTES, name="context manifest")
    try:
        validate_context_manifest(context_manifest)
    except Exception as exc:  # noqa: BLE001 - normalize contract boundary
        raise EarningsPrivateClosureError("malformed_native_section") from exc
    context_manifest_artifact = _artifact(
        "context_manifest",
        "latest",
        context_manifest_body,
        maximum=MAX_CONTEXT_MANIFEST_BYTES,
    )
    artifacts.append(context_manifest_artifact)
    payloads[context_manifest_artifact.object_key] = context_manifest_body
    expected_paths.add((root / CONTEXT_STAGE_DIR / CONTEXT_MANIFEST_NAME).resolve())

    context_receipts: dict[str, dict[str, Any]] = {}
    for ticker, body in context_packets:
        artifact = _artifact(
            "context_packet",
            ticker,
            body,
            maximum=MAX_CONTEXT_PACKET_BYTES,
        )
        artifacts.append(artifact)
        payloads[artifact.object_key] = body
        context_receipts[ticker] = artifact.receipt()
        expected_paths.add((root / CONTEXT_STAGE_DIR / f"{ticker.lower()}.json").resolve())

    native_root = root / NATIVE_STAGE_DIR
    stage_manifest_body = _native_stage_file(
        root, f"{NATIVE_STAGE_DIR}/{NATIVE_STAGE_MANIFEST_NAME}", MAX_NATIVE_STAGE_MANIFEST_BYTES
    )
    stage_manifest = _native_stage_manifest(
        _native_json(stage_manifest_body, maximum=MAX_NATIVE_STAGE_MANIFEST_BYTES, name="native stage manifest")
    )
    expected_paths.add((native_root / NATIVE_STAGE_MANIFEST_NAME).resolve())

    workspace_catalog: dict[str, dict[str, Any]] = {}
    document_catalog: dict[str, dict[str, Any]] = {}
    source_catalog: dict[str, dict[str, Any]] = {}
    native_documents_by_key: dict[str, dict[str, Any]] = {}
    for selection in stage_manifest["selections"].values():
        for entry in selection["chain"]:
            workspace_name = entry["workspace"]
            workspace_body = _native_stage_file(
                root, f"{NATIVE_STAGE_DIR}/workspaces/{workspace_name}.json", MAX_NATIVE_WORKSPACE_BYTES
            )
            workspace_artifact = _artifact("native_workspace", workspace_name, workspace_body)
            artifacts.append(workspace_artifact)
            payloads[workspace_artifact.object_key] = workspace_body
            workspace_catalog[workspace_name] = workspace_artifact.receipt()
            expected_paths.add((native_root / "workspaces" / f"{workspace_name}.json").resolve())
            document_name = entry["document"]
            document_body = _native_stage_file(
                root, f"{NATIVE_STAGE_DIR}/documents/{document_name}.json", MAX_NATIVE_DOCUMENT_BYTES
            )
            document = _native_json(document_body, maximum=MAX_NATIVE_DOCUMENT_BYTES, name="native document")
            content_digest = _safe_field(document, "content_sha256")
            if type(content_digest) is not str or content_digest not in stage_manifest["received"]:
                raise EarningsPrivateClosureError("malformed_native_section")
            if content_digest not in source_catalog:
                body_digest = sha256(document_body).hexdigest()
                if document_name != body_digest:
                    raise EarningsPrivateClosureError("digest_mismatch")
                text_body = _native_stage_file(
                    root, f"{NATIVE_STAGE_DIR}/source_bodies/{content_digest}.txt", MAX_SOURCE_BODY_BYTES
                )
                received = stage_manifest["received"][content_digest]
                if (
                    sha256(text_body).hexdigest() != content_digest
                    or len(text_body) != received["length"]
                ):
                    raise EarningsPrivateClosureError("digest_mismatch")
                text_artifact = _artifact("source_body_text", content_digest, text_body)
                artifacts.append(text_artifact)
                payloads[text_artifact.object_key] = text_body
                source_catalog[content_digest] = {
                    "text": text_artifact.receipt(),
                    "received": {
                        "sha256": received["sha256"],
                        "length": received["length"],
                        "declared_encoding": received["declared_encoding"],
                    },
                }
                expected_paths.add((native_root / "source_bodies" / f"{content_digest}.txt").resolve())
            document_artifact = _artifact("native_document", document_name, document_body)
            if document_artifact.sha256 != document_name:
                raise EarningsPrivateClosureError("digest_mismatch")
            if document_name not in native_documents_by_key:
                native_documents_by_key[document_name] = document
            artifacts.append(document_artifact)
            payloads[document_artifact.object_key] = document_body
            document_catalog[document_name] = document_artifact.receipt()
            expected_paths.add((native_root / "documents" / f"{document_name}.json").resolve())

    named_digests = set(stage_manifest["received"])
    for selection in stage_manifest["selections"].values():
        for entry in selection["chain"]:
            named_digests.discard(_safe_field(native_documents_by_key[entry["document"]], "content_sha256"))
    if named_digests:
        raise EarningsPrivateClosureError("unexpected_artifact")

    expected_native_directories = {
        (native_root / name).resolve() for name in ("workspaces", "documents", "source_bodies")
    }
    expected_native_paths = {
        path for path in expected_paths
        if path.is_relative_to(native_root.resolve())
    } | expected_native_directories
    actual_native_paths = {path.resolve() for path in native_root.rglob("*")}
    if actual_native_paths != expected_native_paths:
        raise EarningsPrivateClosureError("unexpected_artifact")
    actual_paths = {path.resolve() for path in root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise EarningsPrivateClosureError("unexpected_artifact")

    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA_V2,
        "generation_id": "earnpriv_" + ("0" * 32),
        "published_at": str(context_manifest["knowledge_cutoff"]),
        "source": {
            "wire_manifest_id": str(context_manifest["source"]["wire_manifest_id"]),
            "source_generation_id": str(context_manifest["source"]["generation_id"]),
            "source_manifest_sha256": str(context_manifest["source"]["manifest_sha256"]),
        },
        "record_count": len(record_receipts),
        "ticker_count": len(context_receipts),
        "records": dict(sorted(record_receipts.items())),
        "context": {
            "manifest": context_manifest_artifact.receipt(),
            "objects": dict(sorted(context_receipts.items())),
        },
        "native": {
            "workspaces": dict(sorted(workspace_catalog.items())),
            "documents": dict(sorted(document_catalog.items())),
            "source_bodies": dict(sorted(source_catalog.items())),
            "selections": stage_manifest["selections"],
            "economic_slots": stage_manifest["economic_slots"],
        },
        "native_source_cutoff": stage_manifest["native_source_cutoff"],
        "previous_manifest": stage_manifest["previous_manifest"],
    }
    manifest["generation_id"] = _generation_id(manifest)
    validate_native_closure(manifest, payloads)
    manifest_bytes = canonical_json_bytes(manifest)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise EarningsPrivateClosureError("over_limit")
    manifest_key = f"{PRIVATE_PREFIX}/manifests/{manifest['generation_id']}.json"
    return PreparedPrivatePublication(
        generation_id=str(manifest["generation_id"]),
        manifest_key=manifest_key,
        manifest=MappingProxyType(manifest),
        manifest_bytes=manifest_bytes,
        artifacts=tuple(artifacts),
        payloads=MappingProxyType(payloads),
        retired_slots=retired_slots,
    )

def prepare_private_publication(
    stage_dir: str | Path,
    *,
    retire_slots: tuple[str, ...] | list[str] = (),
) -> PreparedPrivatePublication:
    """Validate a complete off-repo staging tree and freeze one generation."""
    if type(retire_slots) is not tuple and type(retire_slots) is not list:
        raise EarningsPrivateClosureError("malformed_native_section")
    if any(type(slot) is not str for slot in retire_slots):
        raise EarningsPrivateClosureError("malformed_native_section")
    retired = tuple(sorted(set(retire_slots)))
    root = Path(stage_dir).resolve()
    records_dir = root / RECORD_STAGE_DIR
    context_dir = root / CONTEXT_STAGE_DIR
    if not records_dir.is_dir() or not context_dir.is_dir():
        raise EarningsPrivatePublicationError("private earnings staging tree is incomplete")

    record_paths = sorted(records_dir.glob("*.json"))
    if not 0 <= len(record_paths) <= MAX_RECORDS:
        raise EarningsPrivatePublicationError("private earnings staging record count is invalid")
    artifacts: list[PrivateArtifact] = []
    payloads: dict[str, bytes] = {}
    record_receipts: dict[str, dict[str, Any]] = {}
    expected_paths: set[Path] = set()
    native_root = root / NATIVE_STAGE_DIR
    if native_root.is_symlink():
        raise EarningsPrivateClosureError("unsafe_path")
    native = native_root.is_dir()
    native_records: list[tuple[str, bytes]] = []
    for path in record_paths:
        slug = validate_slug(path.stem)
        relative = Path(RECORD_STAGE_DIR) / path.name
        body = _stage_file(root, relative, maximum=MAX_RECORD_BYTES, name=f"record {slug}")
        record = _json_object(body, maximum=MAX_RECORD_BYTES, name=f"record {slug}")
        if not native and record.get("schema") == RECORD_SCHEMA_V2:
            raise EarningsPrivateClosureError("malformed_native_section")
        validate_private_record(record, expected_slug=slug)
        native_records.append((slug, body))
        artifact = _artifact("record", slug, body, maximum=MAX_RECORD_BYTES)
        artifacts.append(artifact)
        payloads[artifact.object_key] = body
        record_receipts[slug] = artifact.receipt()
        expected_paths.add((root / relative).resolve())

    context_manifest_relative = Path(CONTEXT_STAGE_DIR) / CONTEXT_MANIFEST_NAME
    context_manifest_body = _stage_file(
        root,
        context_manifest_relative,
        maximum=MAX_CONTEXT_MANIFEST_BYTES,
        name="context manifest",
    )
    context_manifest = _json_object(
        context_manifest_body,
        maximum=MAX_CONTEXT_MANIFEST_BYTES,
        name="context manifest",
    )
    try:
        validate_context_manifest(context_manifest)
    except Exception as exc:  # noqa: BLE001 - normalize contract boundary
        raise EarningsPrivatePublicationError("private context manifest contract is invalid") from exc
    context_manifest_artifact = _artifact(
        "context_manifest",
        "latest",
        context_manifest_body,
        maximum=MAX_CONTEXT_MANIFEST_BYTES,
    )
    artifacts.append(context_manifest_artifact)
    payloads[context_manifest_artifact.object_key] = context_manifest_body
    expected_paths.add((root / context_manifest_relative).resolve())

    context_receipts: dict[str, dict[str, Any]] = {}
    context_objects = context_manifest.get("objects")
    if not isinstance(context_objects, Mapping) or len(context_objects) > MAX_CONTEXT_PACKETS:
        raise EarningsPrivatePublicationError("private context manifest object catalog is invalid")
    for ticker, advertised in sorted(context_objects.items()):
        validate_ticker(ticker)
        if not isinstance(advertised, Mapping):
            raise EarningsPrivatePublicationError(f"context receipt {ticker} is invalid")
        relative_name = advertised.get("path")
        if not isinstance(relative_name, str) or relative_name != f"{ticker.lower()}.json":
            raise EarningsPrivatePublicationError(f"context path {ticker} is unsafe")
        relative = Path(CONTEXT_STAGE_DIR) / relative_name
        body = _stage_file(
            root,
            relative,
            maximum=MAX_CONTEXT_PACKET_BYTES,
            name=f"context packet {ticker}",
        )
        if (
            isinstance(advertised.get("bytes"), bool)
            or advertised.get("bytes") != len(body)
            or advertised.get("sha256") != sha256(body).hexdigest()
        ):
            raise EarningsPrivatePublicationError(f"context receipt {ticker} mismatch")
        packet = _json_object(
            body,
            maximum=MAX_CONTEXT_PACKET_BYTES,
            name=f"context packet {ticker}",
        )
        try:
            validate_context_packet_at_cutoff(
                packet,
                knowledge_cutoff=context_manifest["knowledge_cutoff"],
            )
        except Exception as exc:  # noqa: BLE001
            raise EarningsPrivatePublicationError(f"context packet {ticker} is invalid") from exc
        if packet.get("context_id") != advertised.get("context_id") or (
            not isinstance(packet.get("event"), Mapping)
            or packet["event"].get("ticker") != ticker
        ):
            raise EarningsPrivatePublicationError(f"context packet {ticker} identity mismatch")
        artifact = _artifact(
            "context_packet",
            ticker,
            body,
            maximum=MAX_CONTEXT_PACKET_BYTES,
        )
        artifacts.append(artifact)
        payloads[artifact.object_key] = body
        context_receipts[ticker] = artifact.receipt()
        expected_paths.add((root / relative).resolve())


    if native:
        return _prepare_v2_private_publication(
            root,
            tuple(native_records),
            context_manifest_body,
            tuple((ticker, _stage_file(root, Path(CONTEXT_STAGE_DIR) / f"{ticker.lower()}.json", maximum=MAX_CONTEXT_PACKET_BYTES, name=f"context packet {ticker}")) for ticker in context_receipts),
            retired,
        )

    actual_paths = {path.resolve() for path in root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise EarningsPrivatePublicationError("private earnings staging tree contains unexpected files")

    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "generation_id": "earnpriv_" + ("0" * 32),
        "published_at": str(context_manifest["knowledge_cutoff"]),
        "source": {
            "wire_manifest_id": str(context_manifest["source"]["wire_manifest_id"]),
            "source_generation_id": str(context_manifest["source"]["generation_id"]),
            "source_manifest_sha256": str(context_manifest["source"]["manifest_sha256"]),
        },
        "record_count": len(record_receipts),
        "ticker_count": len(context_receipts),
        "records": {slug: record_receipts[slug] for slug in sorted(record_receipts)},
        "context": {
            "manifest": context_manifest_artifact.receipt(),
            "objects": {ticker: context_receipts[ticker] for ticker in sorted(context_receipts)},
        },
    }
    manifest["generation_id"] = _generation_id(manifest)
    validate_private_manifest(manifest)
    manifest_bytes = canonical_json_bytes(manifest)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise EarningsPrivatePublicationError("private earnings manifest exceeds its safe size bound")
    manifest_key = f"{PRIVATE_PREFIX}/manifests/{manifest['generation_id']}.json"
    return PreparedPrivatePublication(
        generation_id=str(manifest["generation_id"]),
        manifest_key=manifest_key,
        manifest=MappingProxyType(manifest),
        manifest_bytes=manifest_bytes,
        artifacts=tuple(artifacts),
        payloads=MappingProxyType(payloads),
        retired_slots=retired,
    )

def _bounded_read(store: Store, key: str, *, maximum: int) -> bytes | None:
    if not isinstance(store, StrictBoundedReadStore):
        raise EarningsPrivatePublicationError("private earnings store lacks bounded strict reads")
    try:
        body = store.get_bytes_strict_bounded(key, maximum)
    except Exception as exc:  # noqa: BLE001
        raise EarningsPrivatePublicationError("private earnings object read failed") from exc
    if body is not None and not isinstance(body, bytes):
        raise EarningsPrivatePublicationError("private earnings store returned non-bytes")
    return body

def _put_verified(store: Store, *, key: str, body: bytes, maximum: int, content_type: str = "application/json") -> None:
    existing = _bounded_read(store, key, maximum=maximum)
    if existing is not None and existing != body:
        raise EarningsPrivatePublicationError("immutable private earnings object collision")
    if existing is None:
        try:
            written = store.put_bytes(key, body, content_type=content_type)
        except Exception as exc:  # noqa: BLE001
            raise EarningsPrivatePublicationError("private earnings object write failed") from exc
        if written is not True:
            raise EarningsPrivatePublicationError("private earnings object write failed")
    echoed = _bounded_read(store, key, maximum=maximum)
    if echoed != body or sha256(echoed or b"").hexdigest() != sha256(body).hexdigest():
        raise EarningsPrivatePublicationError("private earnings object read-back mismatch")

def _pointer_for(prepared: PreparedPrivatePublication) -> dict[str, Any]:
    return {
        "schema": POINTER_SCHEMA,
        "generation_id": prepared.generation_id,
        "manifest_key": prepared.manifest_key,
        "manifest_sha256": sha256(prepared.manifest_bytes).hexdigest(),
        "manifest_bytes": len(prepared.manifest_bytes),
        "published_at": str(prepared.manifest["published_at"]),
    }

def validate_private_pointer(value: object) -> dict[str, Any]:
    pointer = _strict_object(
        value,
        keys=frozenset(
            {
                "schema",
                "generation_id",
                "manifest_key",
                "manifest_sha256",
                "manifest_bytes",
                "published_at",
            }
        ),
        name="private earnings pointer",
    )
    generation_id = pointer.get("generation_id")
    if (
        pointer.get("schema") != POINTER_SCHEMA
        or not isinstance(generation_id, str)
        or not _GENERATION_RE.fullmatch(generation_id)
        or pointer.get("manifest_key") != f"{PRIVATE_PREFIX}/manifests/{generation_id}.json"
        or not _MANIFEST_KEY_RE.fullmatch(str(pointer.get("manifest_key") or ""))
        or not isinstance(pointer.get("manifest_sha256"), str)
        or not _SHA_RE.fullmatch(pointer["manifest_sha256"])
        or isinstance(pointer.get("manifest_bytes"), bool)
        or not isinstance(pointer.get("manifest_bytes"), int)
        or not 1 <= pointer["manifest_bytes"] <= MAX_MANIFEST_BYTES
        or not isinstance(pointer.get("published_at"), str)
    ):
        raise EarningsPrivatePublicationError("private earnings pointer is invalid")
    return dict(pointer)

def _validated_prepared_payloads(
    prepared: PreparedPrivatePublication,
) -> tuple[tuple[PrivateArtifact, bytes], ...]:
    """Return the frozen payloads after rechecking their immutable receipts.

    ``PreparedPrivatePublication`` is normally only made by
    :func:`prepare_private_publication`, but publication is a security boundary
    and must not trust a caller-provided dataclass merely because it has the
    right type.  The same validation feeds both the normal promotion path and
    the idempotent replay path below.
    """
    verified: list[tuple[PrivateArtifact, bytes]] = []
    for artifact in prepared.artifacts:
        body = prepared.payloads.get(artifact.object_key)
        if not isinstance(body, bytes):
            raise EarningsPrivatePublicationError("prepared private payload is missing")
        if len(body) != artifact.byte_length or sha256(body).hexdigest() != artifact.sha256:
            raise EarningsPrivatePublicationError("prepared private payload receipt mismatch")
        verified.append((artifact, body))
    return tuple(verified)

def _bounded_artifact_read(store: Store, artifact: PrivateArtifact) -> bytes | None:
    """One immutable-object replay read, kept separate for ordered executor.map."""
    return _bounded_read(store, artifact.object_key, maximum=artifact.maximum_bytes)

def _unique_verified_payloads(
    verified_payloads: tuple[tuple[PrivateArtifact, bytes], ...],
) -> tuple[tuple[PrivateArtifact, bytes], ...]:
    """Deduplicate exact objects while preserving every caller-provided size bound.

    A shared content key must enter the worker pool only once: ``LocalStore`` uses
    one fixed temporary path per key, so concurrent same-key writes would race.
    Validate every duplicate before skipping it so deduplication cannot make a
    malformed, tighter bound pass when the former serial loop failed closed.
    """
    unique: list[tuple[PrivateArtifact, bytes]] = []
    seen: set[str] = set()
    for artifact, body in verified_payloads:
        if (
            isinstance(artifact.maximum_bytes, bool)
            or not isinstance(artifact.maximum_bytes, int)
            or not 1 <= len(body) <= artifact.maximum_bytes
        ):
            raise EarningsPrivatePublicationError(
                "prepared private payload exceeds its safe size bound"
            )
        if artifact.object_key in seen:
            continue
        seen.add(artifact.object_key)
        unique.append((artifact, body))
    return tuple(unique)

def _put_verified_artifact(
    store: Store,
    payload: tuple[PrivateArtifact, bytes],
) -> None:
    """Publish one immutable artifact for the bounded worker pool."""
    artifact, body = payload
    _put_verified(
        store,
        key=artifact.object_key,
        body=body,
        maximum=artifact.maximum_bytes,
        content_type=artifact.content_type,
    )

def _existing_exact_publication(
    store: Store,
    prepared: PreparedPrivatePublication,
    *,
    verified_payloads: tuple[tuple[PrivateArtifact, bytes], ...],
) -> dict[str, Any] | None:
    """Prove that *prepared* is already the complete current generation.

    A matching pointer is intentionally insufficient: it can reference a
    partial or corrupt immutable closure after an interrupted operator run.
    The fast path therefore requires canonical exact bytes for the pointer and
    manifest, a complete bounded read of every immutable artifact, and a final
    pointer reread to catch a concurrent promotion.  ``None`` means an object
    is authoritatively absent and permits the normal pointer-last repair path;
    a mismatched immutable byte string fails closed rather than overwriting it.
    """
    expected_pointer = _pointer_for(prepared)
    expected_pointer_bytes = canonical_json_bytes(expected_pointer)
    pointer_body = _bounded_read(store, POINTER_KEY, maximum=MAX_POINTER_BYTES)
    if pointer_body is None:
        return None
    pointer = validate_private_pointer(
        _json_object(pointer_body, maximum=MAX_POINTER_BYTES, name="prior private pointer")
    )
    if pointer["generation_id"] != prepared.generation_id:
        return None
    if pointer_body != expected_pointer_bytes or pointer != expected_pointer:
        raise EarningsPrivatePublicationError("private pointer disagrees with generation")

    manifest_body = _bounded_read(store, prepared.manifest_key, maximum=MAX_MANIFEST_BYTES)
    if manifest_body is None:
        return None
    if manifest_body != prepared.manifest_bytes:
        raise EarningsPrivatePublicationError("immutable private earnings manifest differs")
    manifest = validate_private_manifest(
        _json_object(manifest_body, maximum=MAX_MANIFEST_BYTES, name="private earnings manifest")
    )
    if manifest != dict(prepared.manifest):
        raise EarningsPrivatePublicationError("private earnings manifest replay mismatch")

    # Content addressing makes identical payloads share a key.  Read each key
    # only once while still requiring that every artifact advertised by this
    # generation is present and exact.  ``executor.map`` yields ordered
    # results, so a missing/mismatched receipt remains deterministic while the
    # remote IO is conservatively capped rather than serializing ~900 GETs.
    checked_keys: set[str] = set()
    unique_payloads: list[tuple[PrivateArtifact, bytes]] = []
    for artifact, expected_body in verified_payloads:
        if artifact.object_key in checked_keys:
            continue
        checked_keys.add(artifact.object_key)
        unique_payloads.append((artifact, expected_body))
    remote_bodies: tuple[bytes | None, ...] = ()
    if unique_payloads:
        worker_count = min(IDEMPOTENT_READ_WORKERS, len(unique_payloads))
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="earnings-private-read") as pool:
            remote_bodies = tuple(
                pool.map(
                    _bounded_artifact_read,
                    (store for _artifact, _body in unique_payloads),
                    (artifact for artifact, _body in unique_payloads),
                )
            )
    for (_artifact, expected_body), remote_body in zip(unique_payloads, remote_bodies, strict=True):
        if remote_body is None:
            return None
        if remote_body != expected_body:
            raise EarningsPrivatePublicationError("immutable private earnings object differs")

    # The local mutex does not coordinate another runner/process.  A second
    # exact bounded read prevents a stale snapshot from being reported ready.
    if _bounded_read(store, POINTER_KEY, maximum=MAX_POINTER_BYTES) != expected_pointer_bytes:
        raise EarningsPrivatePublicationError("private pointer changed during idempotent replay")
    return expected_pointer

def publish_private_publication(
    store: Store,
    prepared: PreparedPrivatePublication,
) -> dict[str, Any]:
    """Publish objects and manifest, then advance the private pointer last."""
    if not isinstance(prepared, PreparedPrivatePublication):
        raise TypeError("prepared must be PreparedPrivatePublication")
    if not isinstance(store, Store) or not isinstance(store, StrictBoundedReadStore):
        raise EarningsPrivatePublicationError("private earnings publication requires a strict store")
    if prepared.manifest.get("schema") != MANIFEST_SCHEMA:
        raise EarningsPrivatePublicationError("v2 private publication is not enabled")
    with _PUBLISH_LOCK:
        verified_payloads = _validated_prepared_payloads(prepared)
        # Validate every caller-provided bound before either the idempotent
        # fast path or promotion can return.  Reusing this set also keeps
        # duplicate content keys out of the write pool.
        unique_payloads = _unique_verified_payloads(verified_payloads)
        ready = _existing_exact_publication(
            store,
            prepared,
            verified_payloads=verified_payloads,
        )
        if ready is not None:
            return ready
        if unique_payloads:
            worker_count = min(PUBLISH_WORKERS, len(unique_payloads))
            with ThreadPoolExecutor(
                max_workers=worker_count,
                thread_name_prefix="earnings-private-publish",
            ) as pool:
                for _result in pool.map(
                    _put_verified_artifact,
                    (store for _payload in unique_payloads),
                    unique_payloads,
                ):
                    pass
        _put_verified(
            store,
            key=prepared.manifest_key,
            body=prepared.manifest_bytes,
            maximum=MAX_MANIFEST_BYTES,
        )
        pointer = _pointer_for(prepared)
        pointer_bytes = canonical_json_bytes(pointer)
        prior = _bounded_read(store, POINTER_KEY, maximum=MAX_POINTER_BYTES)
        if prior is not None:
            prior_pointer = validate_private_pointer(
                _json_object(prior, maximum=MAX_POINTER_BYTES, name="prior private pointer")
            )
            if prior_pointer["generation_id"] == prepared.generation_id:
                if prior != pointer_bytes:
                    raise EarningsPrivatePublicationError("private pointer disagrees with generation")
                return pointer
            if str(pointer["published_at"]) < str(prior_pointer["published_at"]):
                raise EarningsPrivatePublicationError("stale private publication cannot rewind current")
        try:
            written = store.put_bytes(POINTER_KEY, pointer_bytes, content_type="application/json")
        except Exception as exc:  # noqa: BLE001
            raise EarningsPrivatePublicationError("private earnings pointer write failed") from exc
        if written is not True:
            raise EarningsPrivatePublicationError("private earnings pointer write failed")
        echoed = _bounded_read(store, POINTER_KEY, maximum=MAX_POINTER_BYTES)
        if echoed != pointer_bytes:
            if prior is not None:
                try:
                    store.put_bytes(POINTER_KEY, prior, content_type="application/json")
                except Exception:  # pragma: no cover - original error remains authoritative
                    pass
            raise EarningsPrivatePublicationError("private earnings pointer read-back mismatch")
        # Replay the complete current closure after promotion.  This catches a
        # pointer/object mismatch before the workflow is allowed to publish its
        # corresponding public shells.
        loaded = load_private_manifest(store)
        if loaded != dict(prepared.manifest):
            raise EarningsPrivatePublicationError("private earnings publication replay mismatch")
        return pointer

def load_private_manifest(store: Store) -> dict[str, Any]:
    """Load the current private manifest through its pointer and exact receipt."""
    pointer_body = _bounded_read(store, POINTER_KEY, maximum=MAX_POINTER_BYTES)
    if pointer_body is None:
        raise EarningsPrivatePublicationError("private earnings pointer is unavailable")
    pointer = validate_private_pointer(
        _json_object(pointer_body, maximum=MAX_POINTER_BYTES, name="private earnings pointer")
    )
    manifest_body = _bounded_read(store, pointer["manifest_key"], maximum=MAX_MANIFEST_BYTES)
    if manifest_body is None:
        raise EarningsPrivatePublicationError("private earnings manifest is unavailable")
    if (
        len(manifest_body) != pointer["manifest_bytes"]
        or sha256(manifest_body).hexdigest() != pointer["manifest_sha256"]
    ):
        raise EarningsPrivatePublicationError("private earnings manifest receipt mismatch")
    manifest = validate_private_manifest(
        _json_object(manifest_body, maximum=MAX_MANIFEST_BYTES, name="private earnings manifest")
    )
    if (
        manifest["generation_id"] != pointer["generation_id"]
        or manifest["published_at"] != pointer["published_at"]
    ):
        raise EarningsPrivatePublicationError("private pointer does not bind its manifest")
    return manifest

def _load_receipted_object(
    store: Store,
    receipt: Mapping[str, Any],
    *,
    maximum: int,
    name: str,
) -> bytes:
    normalized = _validate_receipt(receipt, name=f"{name} receipt")
    if normalized["bytes"] > maximum:
        raise EarningsPrivatePublicationError(f"{name} exceeds its safe size bound")
    body = _bounded_read(store, normalized["object_key"], maximum=maximum)
    if body is None:
        raise EarningsPrivatePublicationError(f"{name} is unavailable")
    if len(body) != normalized["bytes"] or sha256(body).hexdigest() != normalized["sha256"]:
        raise EarningsPrivatePublicationError(f"{name} receipt mismatch")
    return body

def load_private_record(
    store: Store,
    slug: str,
    *,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one member record from the current private generation."""
    slug = validate_slug(slug)
    current = validate_private_manifest(manifest) if manifest is not None else load_private_manifest(store)
    receipt = current["records"].get(slug)
    if not isinstance(receipt, Mapping):
        raise EarningsPrivateRecordNotFound("earnings record is not covered")
    body = _load_receipted_object(
        store,
        receipt,
        maximum=MAX_RECORD_BYTES,
        name="private earnings record",
    )
    return validate_private_record(
        _json_object(body, maximum=MAX_RECORD_BYTES, name="private earnings record"),
        expected_slug=slug,
    )

def load_private_context_packet(
    store: Store,
    ticker: str,
    *,
    manifest: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
    """Return one exact-evidence context packet and both bound manifests.

    This is the server-side seam for Neural Web, Mastermind AI, and display-only
    Prophet annotations.  It never grants decision authority; the packet's own
    closed context contract is revalidated here.
    """
    ticker = validate_ticker(ticker)
    current = validate_private_manifest(manifest) if manifest is not None else load_private_manifest(store)
    context = current["context"]
    catalog_body = _load_receipted_object(
        store,
        context["manifest"],
        maximum=MAX_CONTEXT_MANIFEST_BYTES,
        name="private context manifest",
    )
    catalog = _json_object(
        catalog_body,
        maximum=MAX_CONTEXT_MANIFEST_BYTES,
        name="private context manifest",
    )
    try:
        validate_context_manifest(catalog)
    except Exception as exc:  # noqa: BLE001
        raise EarningsPrivatePublicationError("private context manifest contract is invalid") from exc
    catalog_source = catalog["source"]
    expected_source = {
        "wire_manifest_id": catalog_source["wire_manifest_id"],
        "source_generation_id": catalog_source["generation_id"],
        "source_manifest_sha256": catalog_source["manifest_sha256"],
    }
    if (
        current["published_at"] != catalog["knowledge_cutoff"]
        or current["source"] != expected_source
    ):
        raise EarningsPrivatePublicationError("private context catalogs disagree")
    advertised = catalog["objects"].get(ticker)
    receipt = context["objects"].get(ticker)
    if not isinstance(advertised, Mapping) or not isinstance(receipt, Mapping):
        raise EarningsPrivateRecordNotFound("earnings context ticker is not covered")
    body = _load_receipted_object(
        store,
        receipt,
        maximum=MAX_CONTEXT_PACKET_BYTES,
        name="private context packet",
    )
    if len(body) != advertised.get("bytes") or sha256(body).hexdigest() != advertised.get("sha256"):
        raise EarningsPrivatePublicationError("private context catalogs disagree")
    packet = _json_object(
        body,
        maximum=MAX_CONTEXT_PACKET_BYTES,
        name="private context packet",
    )
    try:
        validate_context_packet_at_cutoff(
            packet,
            knowledge_cutoff=catalog["knowledge_cutoff"],
        )
    except Exception as exc:  # noqa: BLE001
        raise EarningsPrivatePublicationError("private context packet contract is invalid") from exc
    if (
        packet.get("context_id") != advertised.get("context_id")
        or not isinstance(packet.get("event"), Mapping)
        or packet["event"].get("ticker") != ticker
    ):
        raise EarningsPrivatePublicationError("private context packet identity mismatch")
    return packet, catalog, receipt

__all__ = [
    "CLOSURE_REASONS",
    "CONTEXT_STAGE_DIR",
    "DOSSIER_PAGE",
    "EarningsEconomicNotFound",
    "EarningsEconomicUnavailable",
    "EarningsPrivateClosureError",
    "EarningsPrivateManifestNotCurrent",
    "EarningsPrivatePublicationError",
    "EarningsPrivatePublishConflict",
    "EarningsPrivatePointerEffectUnknown",
    "EarningsPrivateRecordNotFound",
    "MANIFEST_SCHEMA",
    "MANIFEST_SCHEMA_V2",
    "MAX_ECONOMIC_COMPARISONS",
    "MAX_ECONOMIC_FACTS",
    "MAX_NATIVE_CHAIN",
    "MAX_NATIVE_DOCUMENT_BYTES",
    "MAX_NATIVE_STAGE_MANIFEST_BYTES",
    "MAX_NATIVE_WORKSPACE_BYTES",
    "MAX_SOURCE_BODY_BYTES",
    "NOT_FOUND_REASONS",
    "NATIVE_RIGHTS_REGISTRY_PATH",
    "NATIVE_STAGE_DIR",
    "NATIVE_STAGE_MANIFEST_NAME",
    "NATIVE_STAGE_SCHEMA",
    "POINTER_KEY",
    "POINTER_SCHEMA",
    "PUBLISH_CONFLICT_REASONS",
    "PUBLISH_WORKERS",
    "READ_UNAVAILABLE_REASONS",
    "PreparedPrivatePublication",
    "RECORD_SCHEMA",
    "RECORD_SCHEMA_V2",
    "RECORD_STAGE_DIR",
    "RECORD_UNAVAILABLE_REASONS",
    "assert_native_rights",
    "load_current_economic_view",
    "load_economic_closure",
    "load_economic_evidence",
    "load_private_context_packet",
    "load_private_manifest",
    "load_private_manifest_version",
    "load_private_predecessor",
    "load_private_record",
    "prepare_private_publication",
    "publish_private_publication",
    "validate_native_closure",
    "validate_private_manifest",
    "validate_private_pointer",
    "validate_private_record",
    "validate_v1_manifest",
    "validate_v1_record",
    "validate_v2_manifest",
    "validate_v2_record",
    "validate_digest",
    "validate_generation_id",
    "validate_slug",
    "validate_ticker",
]
