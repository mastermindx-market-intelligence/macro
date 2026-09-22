"""Private, versioned persistence for grounded Research Intelligence.

Each immutable artifact contains the grounded RIO plus the exact successful W1
extraction receipt. One small per-document ``latest`` pointer is the only
mutable projection and advances through the existing Research Vault strict
compare-and-swap store. Writes must supply the exact source body so grounding
and content identity are revalidated before any storage effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from engine.research_vault.r2_store import StrictConditionalWriteStore, VersionedBytes

from .extractor import PROMPT_VERSION, SYSTEM_PROMPT, build_prompt, parse_model_output
from .schema import SCHEMA, validate_rio

ARTIFACT_SCHEMA = "mastermind.research_intelligence.artifact.v1"
POINTER_SCHEMA = "mastermind.research_intelligence.pointer.v1"
READ_SCHEMA = "mastermind.research_intelligence.read.v1"
WRITE_RECEIPT_SCHEMA = "mastermind.research_intelligence.write_receipt.v1"
ROOT_PREFIX = "research_vault/intelligence/v1"
RIO_MAX_BYTES = 128 * 1024
ARTIFACT_MAX_BYTES = 160 * 1024
POINTER_MAX_BYTES = 16 * 1024
SOURCE_BODY_MAX_BYTES = 8 * 1024 * 1024
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_SUCCESS_FIELDS = frozenset(
    {
        "state",
        "document",
        "rio",
        "provider",
        "model",
        "requested_model",
        "prompt_version",
        "prompt_contract_sha256",
        "prompt_sha256",
    }
)


class ResearchIntelligenceStoreError(RuntimeError):
    """Base typed failure for private Research Intelligence persistence."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ResearchIntelligenceEffectUnknown(ResearchIntelligenceStoreError):
    """A modifying write may have committed but canonical status cannot prove it."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        write_error: BaseException,
        status_error: BaseException | None = None,
    ):
        super().__init__(code, message)
        self.write_error_type = type(write_error).__name__
        self.status_error_code = (
            getattr(status_error, "code", type(status_error).__name__)
            if status_error is not None
            else None
        )


class ResearchIntelligenceInvalid(ResearchIntelligenceStoreError):
    """Stored or submitted state violates the frozen artifact contract."""


class ResearchIntelligenceConflict(ResearchIntelligenceStoreError):
    """The exact predecessor or immutable identity no longer matches."""


class ResearchIntelligenceCorrectionRequired(ResearchIntelligenceConflict):
    """A correction attempted to replace a version without naming it."""


@dataclass(frozen=True)
class StoredResearchIntelligence:
    document_id: str
    artifact_sha256: str
    rio_sha256: str
    source_content_sha256: str
    artifact_key: str
    pointer_key: str
    pointer_version: str | None
    is_latest: bool
    receipt: dict[str, Any]
    rio: dict[str, Any]


@dataclass(frozen=True)
class ResearchIntelligenceWriteReceipt:
    state: str
    document_id: str
    artifact_sha256: str
    rio_sha256: str
    source_content_sha256: str
    artifact_key: str
    pointer_key: str
    previous_artifact_sha256: str | None
    reconciled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": WRITE_RECEIPT_SCHEMA,
            "state": self.state,
            "document_id": self.document_id,
            "artifact_sha256": self.artifact_sha256,
            "rio_sha256": self.rio_sha256,
            "source_content_sha256": self.source_content_sha256,
            "artifact_key": self.artifact_key,
            "pointer_key": self.pointer_key,
            "previous_artifact_sha256": self.previous_artifact_sha256,
            "reconciled": self.reconciled,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _canonical_document_id(value: Any) -> str:
    document_id = " ".join(str(value or "").split())[:240]
    if not document_id:
        raise ResearchIntelligenceInvalid("document_id_invalid", "document_id is required")
    return document_id


def document_storage_id(document_id: str) -> str:
    canonical = _canonical_document_id(document_id)
    digest = hashlib.sha256(b"research-intelligence-document-v1\0")
    digest.update(canonical.encode("utf-8"))
    return digest.hexdigest()


def latest_pointer_key(document_id: str) -> str:
    return f"{ROOT_PREFIX}/documents/{document_storage_id(document_id)}/latest.json"


def artifact_object_key(document_id: str, artifact_sha256: str) -> str:
    if not isinstance(artifact_sha256, str) or _SHA256_RE.fullmatch(artifact_sha256) is None:
        raise ResearchIntelligenceInvalid(
            "artifact_sha256_invalid",
            "artifact_sha256 must be lowercase SHA-256 hex",
        )
    return (
        f"{ROOT_PREFIX}/documents/{document_storage_id(document_id)}"
        f"/objects/{artifact_sha256}.json"
    )


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ResearchIntelligenceInvalid(
            "json_invalid",
            "Research Intelligence state cannot be canonically encoded",
        ) from exc


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"invalid JSON constant: {token}")


def _decode_json_object(data: bytes, *, code: str, label: str) -> dict[str, Any]:
    if type(data) is not bytes:
        raise ResearchIntelligenceInvalid(code, f"{label} is not exact bytes")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ResearchIntelligenceInvalid(code, f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise ResearchIntelligenceInvalid(code, f"{label} must be a JSON object")
    return value


def _require_store(store: Any) -> StrictConditionalWriteStore:
    if not isinstance(store, StrictConditionalWriteStore):
        raise TypeError("Research Intelligence persistence requires StrictConditionalWriteStore")
    return store


def _receipt_text(value: Any, *, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            f"analysis receipt {field} must be a string",
        )
    normalized = value.strip()
    if not normalized:
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            f"analysis receipt {field} is required",
        )
    if len(normalized) > limit:
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            f"analysis receipt {field} exceeds its boundary",
        )
    return normalized


def _receipt_hash(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            f"analysis receipt {field} must be lowercase SHA-256 hex",
        )
    return value


_PROMPT_DOCUMENT_FIELDS = (
    "id",
    "source_type",
    "source_name",
    "institution",
    "desk",
    "title",
    "published_at",
    "content_sha256",
)


def _normalize_prompt_document(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(_PROMPT_DOCUMENT_FIELDS):
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            "analysis receipt document identity fields are invalid",
        )
    document: dict[str, str] = {}
    for field in _PROMPT_DOCUMENT_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or item != item.strip():
            raise ResearchIntelligenceInvalid(
                "analysis_receipt_invalid",
                f"analysis receipt document.{field} must be exact stripped text",
            )
        document[field] = item
    if not document["id"] or not document["source_type"]:
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            "analysis receipt document identity is incomplete",
        )
    if _SHA256_RE.fullmatch(document["content_sha256"]) is None:
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            "analysis receipt document.content_sha256 is invalid",
        )
    return document


def _normalize_successful_analysis(
    analysis: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(analysis, dict):
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            "successful analysis envelope must be an object",
        )
    if analysis.get("state") != "ok" or not isinstance(analysis.get("rio"), dict):
        raise ResearchIntelligenceInvalid(
            "analysis_not_successful",
            "only a successful grounded analysis can be persisted",
        )
    if set(analysis) != _SUCCESS_FIELDS:
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_invalid",
            "successful analysis envelope fields are invalid",
        )
    receipt: dict[str, Any] = {
        "state": "ok",
        "document": _normalize_prompt_document(analysis.get("document")),
        "requested_model": _receipt_text(
            analysis.get("requested_model"), field="requested_model", limit=240
        ),
        "provider": _receipt_text(analysis.get("provider"), field="provider", limit=160),
        "model": _receipt_text(analysis.get("model"), field="model", limit=240),
        "prompt_version": _receipt_text(
            analysis.get("prompt_version"), field="prompt_version", limit=200
        ),
        "prompt_contract_sha256": _receipt_hash(
            analysis.get("prompt_contract_sha256"), field="prompt_contract_sha256"
        ),
        "prompt_sha256": _receipt_hash(analysis.get("prompt_sha256"), field="prompt_sha256"),
    }
    try:
        rio = validate_rio(analysis["rio"])
    except (TypeError, ValueError) as exc:
        raise ResearchIntelligenceInvalid("rio_invalid", "submitted RIO violates schema") from exc
    return receipt, rio


def _verify_source_and_receipt(
    receipt: dict[str, Any],
    rio: dict[str, Any],
    source_body: Any,
) -> dict[str, Any]:
    if not isinstance(source_body, str) or not source_body.strip():
        raise ResearchIntelligenceInvalid(
            "source_body_invalid",
            "the exact non-empty source body is required",
        )
    raw_body_bytes = source_body.encode("utf-8")
    if len(raw_body_bytes) > SOURCE_BODY_MAX_BYTES:
        raise ResearchIntelligenceInvalid(
            "source_body_too_large",
            "source body exceeds the W2 verification boundary",
        )
    analyzed_body = source_body
    body_bytes = raw_body_bytes
    prompt_document = receipt["document"]
    source_sha256 = _sha256_bytes(body_bytes)
    if (
        rio["document"]["content_sha256"] != source_sha256
        or prompt_document["content_sha256"] != source_sha256
    ):
        raise ResearchIntelligenceInvalid(
            "source_body_mismatch",
            "source body does not match the prompt and RIO content identity",
        )

    system, user = build_prompt(prompt_document, analyzed_body)
    expected_contract_sha256 = _sha256_text(PROMPT_VERSION + "\n" + SYSTEM_PROMPT)
    expected_prompt_sha256 = _sha256_text(system + "\n" + user)
    if (
        receipt["prompt_version"] != PROMPT_VERSION
        or receipt["prompt_contract_sha256"] != expected_contract_sha256
        or receipt["prompt_sha256"] != expected_prompt_sha256
    ):
        raise ResearchIntelligenceInvalid(
            "analysis_receipt_mismatch",
            "analysis receipt is not bound to the exact W1 prompt and source body",
        )

    try:
        grounded = parse_model_output(
            _canonical_json_bytes(rio).decode("utf-8"),
            expected_document_id=prompt_document["id"],
            expected_document=prompt_document,
            source_body=analyzed_body,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ResearchIntelligenceInvalid(
            "grounding_invalid",
            "RIO claims do not survive exact source-body grounding",
        ) from exc
    if _canonical_json_bytes(grounded) != _canonical_json_bytes(rio):
        raise ResearchIntelligenceInvalid(
            "grounding_invalid",
            "RIO changes when re-grounded against the exact source body",
        )
    return grounded


def _build_artifact(
    analysis: Any,
    source_body: Any,
) -> tuple[dict[str, Any], bytes, str, str, str]:
    receipt, rio = _normalize_successful_analysis(analysis)
    submitted_rio_bytes = _canonical_json_bytes(rio)
    if len(submitted_rio_bytes) > RIO_MAX_BYTES:
        raise ResearchIntelligenceInvalid(
            "rio_too_large",
            "grounded RIO exceeds the private artifact boundary",
        )
    grounded = _verify_source_and_receipt(receipt, rio, source_body)
    rio_bytes = _canonical_json_bytes(grounded)
    rio_sha256 = _sha256_bytes(rio_bytes)
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "receipt": receipt,
        "rio": grounded,
    }
    artifact_bytes = _canonical_json_bytes(artifact)
    if len(artifact_bytes) > ARTIFACT_MAX_BYTES:
        raise ResearchIntelligenceInvalid(
            "artifact_too_large",
            "Research Intelligence artifact exceeds the storage boundary",
        )
    artifact_sha256 = _sha256_bytes(artifact_bytes)
    source_content_sha256 = grounded["document"]["content_sha256"]
    return artifact, artifact_bytes, artifact_sha256, rio_sha256, source_content_sha256


def _pointer_payload(
    artifact: dict[str, Any],
    *,
    artifact_sha256: str,
    rio_sha256: str,
) -> dict[str, str]:
    rio = artifact["rio"]
    document_id = _canonical_document_id(rio["document"]["id"])
    return {
        "schema": POINTER_SCHEMA,
        "artifact_schema": ARTIFACT_SCHEMA,
        "document_id": document_id,
        "document_storage_id": document_storage_id(document_id),
        "artifact_sha256": artifact_sha256,
        "artifact_key": artifact_object_key(document_id, artifact_sha256),
        "rio_sha256": rio_sha256,
        "source_content_sha256": rio["document"]["content_sha256"],
    }


def _decode_pointer(data: bytes, *, expected_document_id: str) -> dict[str, str]:
    value = _decode_json_object(
        data,
        code="pointer_invalid",
        label="Research Intelligence latest pointer",
    )
    expected_keys = {
        "schema",
        "artifact_schema",
        "document_id",
        "document_storage_id",
        "artifact_sha256",
        "artifact_key",
        "rio_sha256",
        "source_content_sha256",
    }
    if set(value) != expected_keys:
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer fields are invalid",
        )
    document_id = _canonical_document_id(value.get("document_id"))
    artifact_sha256 = value.get("artifact_sha256")
    rio_sha256 = value.get("rio_sha256")
    source_sha256 = value.get("source_content_sha256")
    if document_id != expected_document_id:
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer document identity mismatches",
        )
    if value.get("schema") != POINTER_SCHEMA or value.get("artifact_schema") != ARTIFACT_SCHEMA:
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer schema is invalid",
        )
    if value.get("document_storage_id") != document_storage_id(document_id):
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer storage identity mismatches",
        )
    for field, item in (
        ("artifact_sha256", artifact_sha256),
        ("rio_sha256", rio_sha256),
        ("source_content_sha256", source_sha256),
    ):
        if not isinstance(item, str) or _SHA256_RE.fullmatch(item) is None:
            raise ResearchIntelligenceInvalid(
                "pointer_invalid",
                f"Research Intelligence pointer {field} is invalid",
            )

    if value.get("artifact_key") != artifact_object_key(document_id, artifact_sha256):
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer artifact key mismatches",
        )
    normalized = {key: str(value[key]) for key in expected_keys}
    if _canonical_json_bytes(normalized) != data:
        raise ResearchIntelligenceInvalid(
            "pointer_noncanonical",
            "Research Intelligence pointer is not canonical JSON",
        )
    return normalized


def _read_versioned_pointer(
    store: StrictConditionalWriteStore,
    document_id: str,
) -> tuple[VersionedBytes, dict[str, str] | None]:
    key = latest_pointer_key(document_id)
    try:
        observed = store.get_bytes_strict_bounded_versioned(key, POINTER_MAX_BYTES)
    except Exception as exc:
        raise ResearchIntelligenceStoreError(
            "pointer_read_failed",
            "Research Intelligence latest pointer read failed",
        ) from exc
    if type(observed) is not VersionedBytes:
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer read returned invalid state",
        )
    if observed.data is None:
        if observed.version is not None:
            raise ResearchIntelligenceInvalid(
                "pointer_invalid",
                "missing Research Intelligence pointer has a version",
            )
        return observed, None
    if not isinstance(observed.version, str) or not observed.version:
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "present Research Intelligence pointer lacks an opaque version",
        )
    return observed, _decode_pointer(observed.data, expected_document_id=document_id)


def _normalize_stored_receipt(value: Any) -> dict[str, Any]:
    expected = _SUCCESS_FIELDS - {"rio"}
    if not isinstance(value, dict) or set(value) != expected or value.get("state") != "ok":
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "stored extraction receipt fields are invalid",
        )
    receipt: dict[str, Any] = {
        "state": "ok",
        "document": _normalize_prompt_document(value.get("document")),
        "requested_model": _receipt_text(
            value.get("requested_model"), field="requested_model", limit=240
        ),
        "provider": _receipt_text(value.get("provider"), field="provider", limit=160),
        "model": _receipt_text(value.get("model"), field="model", limit=240),
        "prompt_version": _receipt_text(
            value.get("prompt_version"), field="prompt_version", limit=200
        ),
        "prompt_contract_sha256": _receipt_hash(
            value.get("prompt_contract_sha256"), field="prompt_contract_sha256"
        ),
        "prompt_sha256": _receipt_hash(value.get("prompt_sha256"), field="prompt_sha256"),
    }
    expected_contract_sha256 = _sha256_text(PROMPT_VERSION + "\n" + SYSTEM_PROMPT)
    if (
        receipt["prompt_version"] != PROMPT_VERSION
        or receipt["prompt_contract_sha256"] != expected_contract_sha256
    ):
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "stored extraction receipt prompt contract is invalid",
        )
    return receipt


def _decode_artifact(
    data: bytes,
    *,
    expected_document_id: str,
    expected_artifact_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    if _sha256_bytes(data) != expected_artifact_sha256:
        raise ResearchIntelligenceInvalid(
            "artifact_hash_mismatch",
            "Research Intelligence artifact hash mismatches",
        )
    value = _decode_json_object(
        data,
        code="artifact_invalid",
        label="private Research Intelligence artifact",
    )
    if set(value) != {"schema", "receipt", "rio"} or value.get("schema") != ARTIFACT_SCHEMA:
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "private Research Intelligence artifact fields are invalid",
        )
    receipt = _normalize_stored_receipt(value.get("receipt"))
    try:
        rio = validate_rio(
            value.get("rio"),
            expected_document_id=expected_document_id,
            expected_document=receipt["document"],
        )
    except (TypeError, ValueError) as exc:
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "private Research Intelligence artifact violates the RIO schema",
        ) from exc
    normalized = {"schema": ARTIFACT_SCHEMA, "receipt": receipt, "rio": rio}
    if _canonical_json_bytes(normalized) != data:
        raise ResearchIntelligenceInvalid(
            "artifact_noncanonical",
            "private Research Intelligence artifact is not canonical",
        )
    return receipt, rio, _sha256_bytes(_canonical_json_bytes(rio))


def _read_artifact(
    store: StrictConditionalWriteStore,
    *,
    document_id: str,
    artifact_sha256: str,
    pointer_key: str,
    pointer_version: str | None,
    is_latest: bool,
) -> StoredResearchIntelligence:
    key = artifact_object_key(document_id, artifact_sha256)
    try:
        raw = store.get_bytes_strict_bounded(key, ARTIFACT_MAX_BYTES)
    except Exception as exc:
        raise ResearchIntelligenceStoreError(
            "artifact_read_failed",
            "private Research Intelligence artifact read failed",
        ) from exc
    if raw is None:
        raise ResearchIntelligenceInvalid(
            "artifact_missing",
            "Research Intelligence pointer references a missing artifact",
        )
    if type(raw) is not bytes or len(raw) > ARTIFACT_MAX_BYTES:
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "private Research Intelligence artifact bytes are invalid",
        )
    receipt, rio, rio_sha256 = _decode_artifact(
        raw,
        expected_document_id=document_id,
        expected_artifact_sha256=artifact_sha256,
    )
    return StoredResearchIntelligence(
        document_id=document_id,
        artifact_sha256=artifact_sha256,
        rio_sha256=rio_sha256,
        source_content_sha256=rio["document"]["content_sha256"],
        artifact_key=key,
        pointer_key=pointer_key,
        pointer_version=pointer_version,
        is_latest=is_latest,
        receipt=receipt,
        rio=rio,
    )


def _read_latest_state(
    store: StrictConditionalWriteStore,
    document_id: str,
) -> tuple[VersionedBytes, dict[str, str] | None, StoredResearchIntelligence | None]:
    canonical_id = _canonical_document_id(document_id)
    observed, pointer = _read_versioned_pointer(store, canonical_id)
    if pointer is None:
        return observed, None, None
    stored = _read_artifact(
        store,
        document_id=canonical_id,
        artifact_sha256=pointer["artifact_sha256"],
        pointer_key=latest_pointer_key(canonical_id),
        pointer_version=observed.version,
        is_latest=True,
    )
    if (
        stored.rio_sha256 != pointer["rio_sha256"]
        or stored.source_content_sha256 != pointer["source_content_sha256"]
    ):
        raise ResearchIntelligenceInvalid(
            "pointer_invalid",
            "Research Intelligence pointer does not bind the immutable artifact",
        )
    return observed, pointer, stored


def load_latest_research_intelligence(
    store: Any,
    document_id: str,
) -> StoredResearchIntelligence | None:
    checked = _require_store(store)
    _observed, _pointer, stored = _read_latest_state(
        checked,
        _canonical_document_id(document_id),
    )
    return stored


def load_research_intelligence_version(
    store: Any,
    document_id: str,
    artifact_sha256: str,
) -> StoredResearchIntelligence:
    checked = _require_store(store)
    canonical_id = _canonical_document_id(document_id)
    return _read_artifact(
        checked,
        document_id=canonical_id,
        artifact_sha256=artifact_sha256,
        pointer_key=latest_pointer_key(canonical_id),
        pointer_version=None,
        is_latest=False,
    )


def _read_bounded_optional(
    store: StrictConditionalWriteStore,
    key: str,
    maximum_bytes: int,
) -> bytes | None:
    try:
        value = store.get_bytes_strict_bounded(key, maximum_bytes)
    except Exception as exc:
        raise ResearchIntelligenceStoreError(
            "artifact_read_failed",
            "private Research Intelligence artifact read failed",
        ) from exc
    if value is not None and type(value) is not bytes:
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "private Research Intelligence store returned non-bytes",
        )
    if value is not None and len(value) > maximum_bytes:
        raise ResearchIntelligenceInvalid(
            "artifact_invalid",
            "private Research Intelligence store ignored its byte boundary",
        )
    return value


def _reconcile_immutable_create(
    store: StrictConditionalWriteStore,
    *,
    key: str,
    payload: bytes,
    cause: BaseException | None,
) -> bool:
    try:
        readback = _read_bounded_optional(store, key, ARTIFACT_MAX_BYTES)
    except ResearchIntelligenceStoreError as status_error:
        if cause is None:
            raise
        raise ResearchIntelligenceEffectUnknown(
            "artifact_effect_unknown",
            "immutable Research Intelligence write outcome is unknown",
            write_error=cause,
            status_error=status_error,
        ) from status_error
    if readback == payload:
        return True
    if cause is not None:
        raise ResearchIntelligenceEffectUnknown(
            "artifact_effect_unknown",
            "immutable Research Intelligence write outcome is unknown",
            write_error=cause,
        ) from cause
    if readback is not None:
        raise ResearchIntelligenceConflict(
            "artifact_collision",
            "immutable Research Intelligence key holds different bytes",
        )
    raise ResearchIntelligenceStoreError(
        "artifact_effect_unknown",
        "immutable Research Intelligence write outcome is unknown",
    )


def _ensure_immutable_artifact(
    store: StrictConditionalWriteStore,
    *,
    key: str,
    payload: bytes,
) -> bool:
    existing = _read_bounded_optional(store, key, ARTIFACT_MAX_BYTES)
    if existing == payload:
        return False
    if existing is not None:
        raise ResearchIntelligenceConflict(
            "artifact_collision",
            "immutable Research Intelligence key holds different bytes",
        )
    try:
        written = store.put_bytes_strict_conditional(
            key,
            payload,
            expected_version=None,
            content_type="application/json",
        )
    except Exception as exc:
        return _reconcile_immutable_create(store, key=key, payload=payload, cause=exc)
    if written is True:
        if _read_bounded_optional(store, key, ARTIFACT_MAX_BYTES) != payload:
            raise ResearchIntelligenceStoreError(
                "artifact_readback_failed",
                "private Research Intelligence artifact readback mismatches",
            )
        return False
    if written is False:
        return _reconcile_immutable_create(store, key=key, payload=payload, cause=None)
    raise ResearchIntelligenceStoreError(
        "artifact_write_failed",
        "private Research Intelligence store returned invalid write state",
    )


def _reconcile_pointer_write(
    store: StrictConditionalWriteStore,
    *,
    document_id: str,
    expected_payload: bytes,
    cause: BaseException | None,
) -> bool:
    try:
        observed, _pointer, _stored = _read_latest_state(store, document_id)
    except ResearchIntelligenceStoreError as status_error:
        if cause is None:
            raise
        raise ResearchIntelligenceEffectUnknown(
            "pointer_effect_unknown",
            "Research Intelligence latest-pointer write outcome is unknown",
            write_error=cause,
            status_error=status_error,
        ) from status_error
    if observed.data == expected_payload:
        return True
    if cause is not None:
        raise ResearchIntelligenceEffectUnknown(
            "pointer_effect_unknown",
            "Research Intelligence latest-pointer write outcome is unknown",
            write_error=cause,
        ) from cause
    raise ResearchIntelligenceConflict(
        "pointer_conflict",
        "Research Intelligence latest pointer changed concurrently",
    )


def _publish_pointer(
    store: StrictConditionalWriteStore,
    *,
    document_id: str,
    payload: bytes,
    expected_version: str | None,
) -> bool:
    if len(payload) > POINTER_MAX_BYTES:
        raise ResearchIntelligenceInvalid(
            "pointer_too_large",
            "Research Intelligence latest pointer exceeds its byte boundary",
        )
    key = latest_pointer_key(document_id)
    try:
        written = store.put_bytes_strict_conditional(
            key,
            payload,
            expected_version=expected_version,
            content_type="application/json",
        )
    except Exception as exc:
        return _reconcile_pointer_write(
            store,
            document_id=document_id,
            expected_payload=payload,
            cause=exc,
        )
    if written is not True:
        return _reconcile_pointer_write(
            store,
            document_id=document_id,
            expected_payload=payload,
            cause=None,
        )
    observed, _pointer, _stored = _read_latest_state(store, document_id)
    if observed.data == payload:
        return False
    raise ResearchIntelligenceConflict(
        "pointer_superseded",
        "Research Intelligence latest pointer was overtaken",
    )


def _validate_expected_predecessor(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ResearchIntelligenceInvalid(
            "expected_predecessor_invalid",
            "expected_current_artifact_sha256 must be lowercase SHA-256 hex",
        )
    return value


def validate_analysis_for_persistence(
    analysis: Any,
    *,
    source_body: Any,
    expected_current_artifact_sha256: str | None = None,
) -> None:
    """Validate one W1 envelope and source body without touching a store."""
    _validate_expected_predecessor(expected_current_artifact_sha256)
    _build_artifact(analysis, source_body)


def persist_analysis(
    store: Any,
    analysis: Any,
    *,
    source_body: Any,
    expected_current_artifact_sha256: str | None = None,
) -> ResearchIntelligenceWriteReceipt:
    """Persist one successful grounded analysis and atomically advance its pointer."""
    checked = _require_store(store)
    expected = _validate_expected_predecessor(expected_current_artifact_sha256)
    artifact, payload, artifact_sha256, rio_sha256, source_sha256 = _build_artifact(
        analysis,
        source_body,
    )
    document_id = _canonical_document_id(artifact["rio"]["document"]["id"])
    object_key = artifact_object_key(document_id, artifact_sha256)
    pointer_key = latest_pointer_key(document_id)

    try:
        checked.validate_strict_conditional_write_capability()
    except Exception as exc:
        raise ResearchIntelligenceStoreError(
            "conditional_write_unavailable",
            "strict compare-and-swap is unavailable",
        ) from exc

    observed, _current_pointer, current = _read_latest_state(checked, document_id)
    if current is not None and current.artifact_sha256 == artifact_sha256:
        return ResearchIntelligenceWriteReceipt(
            state="unchanged",
            document_id=document_id,
            artifact_sha256=artifact_sha256,
            rio_sha256=rio_sha256,
            source_content_sha256=source_sha256,
            artifact_key=object_key,
            pointer_key=pointer_key,
            previous_artifact_sha256=current.artifact_sha256,
        )

    if current is None:
        if expected is not None:
            raise ResearchIntelligenceConflict(
                "predecessor_mismatch",
                "Research Intelligence latest pointer is absent",
            )
        previous_artifact_sha256 = None
        state = "created"
    else:
        if expected is None:
            raise ResearchIntelligenceCorrectionRequired(
                "correction_requires_predecessor",
                "Research Intelligence correction requires the exact current artifact hash",
            )
        if expected != current.artifact_sha256:
            raise ResearchIntelligenceConflict(
                "predecessor_mismatch",
                "Research Intelligence predecessor no longer matches",
            )
        previous_artifact_sha256 = current.artifact_sha256
        state = "corrected"

    artifact_reconciled = _ensure_immutable_artifact(
        checked,
        key=object_key,
        payload=payload,
    )
    pointer = _pointer_payload(
        artifact,
        artifact_sha256=artifact_sha256,
        rio_sha256=rio_sha256,
    )
    pointer_payload = _canonical_json_bytes(pointer)
    pointer_reconciled = _publish_pointer(
        checked,
        document_id=document_id,
        payload=pointer_payload,
        expected_version=observed.version,
    )
    latest = load_latest_research_intelligence(checked, document_id)
    if latest is None or latest.artifact_sha256 != artifact_sha256:
        raise ResearchIntelligenceConflict(
            "pointer_superseded",
            "Research Intelligence latest pointer no longer selects the candidate",
        )
    return ResearchIntelligenceWriteReceipt(
        state=state,
        document_id=document_id,
        artifact_sha256=artifact_sha256,
        rio_sha256=rio_sha256,
        source_content_sha256=source_sha256,
        artifact_key=object_key,
        pointer_key=pointer_key,
        previous_artifact_sha256=previous_artifact_sha256,
        reconciled=artifact_reconciled or pointer_reconciled,
    )
