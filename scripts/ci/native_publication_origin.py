#!/usr/bin/env python3
"""Producer-origin admission document codec for Macro's native CI proof chain.

The native publication producer records *where* a published generation came
from: which workflow run and attempt, at which commit, through which job and
step, using which credential class, against which PR, source head, candidate
tree and projection digest.  ``ci-proof-admission`` documents carry that
record as canonical JSON.  This module is the pure codec for that document:
it turns explicitly supplied facts into the canonical compact UTF-8 encoding
and back, refusing anything malformed, mismatched or oversized.

Scope (deliberately narrow):

* Pure stdlib, no I/O, no network, no subprocess, no environment reads, no
  credentials, no state store, no collector, no browser, no registry walk,
  no token discovery, no scheduler, no hidden fallback.
* Inputs are explicit caller facts.  The module never infers an actor, a
  credential, a repository id or a run identity from the environment or from
  GitHub; every value must be supplied by the caller.
* **``encode_origin`` / ``decode_origin`` validate syntax and identity
  binding ONLY.**  They do not authenticate provenance and they do not admit
  a publication: a document that decodes cleanly is merely well-formed.
  Authenticated evidence (official artifact upload by the producer, a
  controller read of that artifact over an authenticated channel, exact-head
  GitHub reads, run/attempt cross-checks) remains a caller duty and stays
  outside this module.
* ``credential_origin`` is a fixed literal *recorded in the document*; the
  string ``"GITHUB_TOKEN"`` is a field value, never a credential.  No secret
  value is ever accepted, stored or reflected: refusal reasons name the field
  and the expectation and never echo caller-supplied input.

Document contract (canonical, compact UTF-8 JSON, at most 4096 bytes)::

    {"schema": "mastermind.ci-proof-producer-origin.v1",
     "repository_id": <positive int>,
     "producer_origin": {
         "producer_run_id": <positive int>,
         "producer_run_attempt": <positive int>,
         "workflow_path": ".github/workflows/<safe>.yml|.yaml",
         "workflow_ref": "<repository_full_name>/<workflow_path>@refs/heads/main",
         "workflow_sha": <40-hex git SHA>,
         "publishing_job": <nonempty safe text>,
         "publishing_step": <nonempty safe text>,
         "credential_origin": "GITHUB_TOKEN",
         "pr_number": <positive int>,
         "published_source_head": <40-hex git SHA>,
         "selected_target": "main" | "codex/merge-queue-pilot",
         "original_generation": <12 lowercase hex characters>,
         "candidate_tree": <40-hex git tree SHA>,
         "projection_sha256": <64-hex SHA-256>,
         "pr_creation_user_id": <positive int>,
         "pr_creation_login": <GitHub login>}}

Positive integer identity fields refuse bool, float and numeric-string
values.  ``repository_id`` must equal the caller-supplied expected id, and
the ``workflow_ref`` repository prefix must equal the caller-supplied
expected repository full name, so a document bound to another repository is
refused as a mismatch rather than decoded.  Encoding is deterministic
(sorted keys, compact separators, no incidental whitespace): the same facts
always produce the same bytes and therefore the same ``origin_sha256``.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Tuple

__all__ = [
    "SCHEMA_ID",
    "CREDENTIAL_ORIGIN",
    "SELECTED_TARGETS",
    "MAX_DOCUMENT_BYTES",
    "ProducerOriginError",
    "MalformedOriginError",
    "OversizedOriginError",
    "OriginIdentityMismatchError",
    "encode_origin",
    "decode_origin",
    "origin_sha256",
]


SCHEMA_ID = "mastermind.ci-proof-producer-origin.v1"
CREDENTIAL_ORIGIN = "GITHUB_TOKEN"
SELECTED_TARGETS = frozenset({"main", "codex/merge-queue-pilot"})
MAX_DOCUMENT_BYTES = 4096

_TOP_LEVEL_FIELDS: Tuple[str, ...] = ("schema", "repository_id", "producer_origin")
_PRODUCER_ORIGIN_FIELDS: Tuple[str, ...] = (
    "producer_run_id",
    "producer_run_attempt",
    "workflow_path",
    "workflow_ref",
    "workflow_sha",
    "publishing_job",
    "publishing_step",
    "credential_origin",
    "pr_number",
    "published_source_head",
    "selected_target",
    "original_generation",
    "candidate_tree",
    "projection_sha256",
    "pr_creation_user_id",
    "pr_creation_login",
)

_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
# Strict single-segment workflow file name under the fixed workflows dir.
_WORKFLOW_PATH_RE = re.compile(
    r"\A\.github/workflows/[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.(?:yml|yaml)\Z"
)
_REPO_FULL_NAME_RE = re.compile(
    r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,99}/[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z"
)
_LOGIN_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]{0,38}(?:\[bot\])?\Z")
_GENERATION_RE = re.compile(r"\A[0-9a-f]{12}\Z")

_WORKFLOW_REF_TAIL = "refs/heads/main"
_MAX_WORKFLOW_REF_LEN = 512
_MAX_WORKFLOW_PATH_LEN = 160
_MAX_SAFE_TEXT_LEN = 128


class ProducerOriginError(Exception):
    """Base typed error: fail-closed refusal with a precise reason."""

    code = "PRODUCER_ORIGIN_ERROR"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MalformedOriginError(ProducerOriginError):
    """Document shape, key set, field type or field format is invalid."""

    code = "MALFORMED_ORIGIN"


class OversizedOriginError(ProducerOriginError):
    """Document exceeds the 4096-byte canonical document cap."""

    code = "OVERSIZED_ORIGIN"


class OriginIdentityMismatchError(ProducerOriginError):
    """Document identity does not match the caller-supplied expected identity."""

    code = "ORIGIN_IDENTITY_MISMATCH"


def _require_positive_int(value: object, field: str) -> int:
    # bool is an int subclass; True/False, floats and numeric strings are all
    # refused for identity fields.
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedOriginError(
            "%s must be a positive int; bool, float and numeric-string values "
            "are refused" % field
        )
    if value < 1:
        raise MalformedOriginError("%s must be a positive int >= 1" % field)
    return value  # type: ignore[return-value]


def _require_safe_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise MalformedOriginError("%s must be a str" % field)
    if not value:
        raise MalformedOriginError("%s must be non-empty" % field)
    if len(value) > _MAX_SAFE_TEXT_LEN:
        raise MalformedOriginError("%s exceeds %d characters" % (field, _MAX_SAFE_TEXT_LEN))
    # Printable ASCII only: control characters (newline, CR, TAB) and
    # non-ASCII bytes are refused outright, so injected headers cannot ride
    # inside a job, step or generation label.
    if any(ord(ch) < 0x20 or ord(ch) > 0x7E for ch in value):
        raise MalformedOriginError(
            "%s must be printable ASCII without control characters; injected "
            "newlines are refused" % field
        )
    if value != value.strip():
        raise MalformedOriginError(
            "%s must not have leading or trailing whitespace" % field
        )
    return value  # type: ignore[return-value]


def _require_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA_RE.match(value) is None:
        raise MalformedOriginError("%s must be a 40-char lowercase hex git SHA" % field)
    return value  # type: ignore[return-value]


def _require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.match(value) is None:
        raise MalformedOriginError("%s must be a 64-char lowercase hex SHA-256" % field)
    return value  # type: ignore[return-value]


def _require_workflow_path(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise MalformedOriginError("%s must be a str" % field)
    if len(value) > _MAX_WORKFLOW_PATH_LEN:
        raise MalformedOriginError("%s exceeds %d characters" % (field, _MAX_WORKFLOW_PATH_LEN))
    if _WORKFLOW_PATH_RE.match(value) is None:
        raise MalformedOriginError(
            "%s must be .github/workflows/<safe>.yml or .github/workflows/<safe>.yaml "
            "with a safe single-segment file name" % field
        )
    if ".." in value:
        raise MalformedOriginError("%s must not contain '..' path segments" % field)
    return value  # type: ignore[return-value]


def _require_repository_full_name(value: object) -> str:
    field = "repository_full_name"
    if not isinstance(value, str) or _REPO_FULL_NAME_RE.match(value) is None:
        raise MalformedOriginError(
            "%s must be '<owner>/<name>' with safe owner and name characters" % field
        )
    owner, _, name = value.partition("/")
    if ".." in owner or ".." in name:
        raise MalformedOriginError("%s must not contain '..' segments" % field)
    return value  # type: ignore[return-value]


def _require_login(value: object, field: str) -> str:
    if not isinstance(value, str) or _LOGIN_RE.match(value) is None:
        raise MalformedOriginError(
            "%s must be a GitHub login: letters, digits and hyphens, starting "
            "with a letter or digit (max 39-character stem, optional [bot] suffix)" % field
        )
    return value  # type: ignore[return-value]


def _require_workflow_ref(
    value: object, workflow_path: str, repository_full_name: str
) -> str:
    field = "workflow_ref"
    if not isinstance(value, str) or not value:
        raise MalformedOriginError("%s must be a non-empty str" % field)
    if len(value) > _MAX_WORKFLOW_REF_LEN:
        raise MalformedOriginError("%s exceeds %d characters" % (field, _MAX_WORKFLOW_REF_LEN))
    # The ref is bound to the caller-supplied expected repository: a prefix
    # naming any other repository is an identity mismatch, and the remainder
    # must be exactly <workflow_path>@refs/heads/main.
    if not value.startswith(repository_full_name + "/"):
        raise OriginIdentityMismatchError(
            "%s must start with the expected repository full name prefix" % field
        )
    expected = "%s/%s@%s" % (repository_full_name, workflow_path, _WORKFLOW_REF_TAIL)
    if value != expected:
        raise MalformedOriginError(
            "%s must be exactly '<repository_full_name>/%s@%s'"
            % (field, workflow_path, _WORKFLOW_REF_TAIL)
        )
    return value  # type: ignore[return-value]


def _require_exact(value: object, field: str, expected: str) -> str:
    if not isinstance(value, str) or value != expected:
        raise MalformedOriginError("%s must be exactly %r" % (field, expected))
    return value  # type: ignore[return-value]


def _reject_duplicate_keys(pairs: Any) -> Dict[str, Any]:
    seen = set()
    for key, _value in pairs:
        if key in seen:
            # Refusal names the condition, never the caller-supplied key text.
            raise MalformedOriginError("document contains duplicate JSON object keys")
        seen.add(key)
    return dict(pairs)


def _require_exact_key_set(raw: Dict[str, Any], field: str, expected: Tuple[str, ...]) -> None:
    keys = frozenset(raw)
    expected_keys = frozenset(expected)
    if keys != expected_keys:
        missing = sorted(expected_keys - keys)
        extra = sorted(keys - expected_keys)
        raise MalformedOriginError(
            "%s keys must be exactly %s; missing=%s extra=%s"
            % (field, ", ".join(expected), missing or "none", extra or "none")
        )


def _validate_origin(
    mapping: object,
    *,
    repository_full_name: str,
    repository_id: int,
) -> Dict[str, Any]:
    """Validate one producer-origin document against the contract.

    Returns the mapping unchanged (validated in place).  Raises a typed
    ``ProducerOriginError`` subclass on any refusal.
    """
    if not isinstance(mapping, dict):
        raise MalformedOriginError("document must be a JSON object")
    expected_full_name = _require_repository_full_name(repository_full_name)
    _require_positive_int(repository_id, "expected repository_id")

    _require_exact_key_set(mapping, "document", _TOP_LEVEL_FIELDS)
    _require_exact(mapping["schema"], "schema", SCHEMA_ID)
    _require_positive_int(mapping["repository_id"], "repository_id")

    origin = mapping["producer_origin"]
    if not isinstance(origin, dict):
        raise MalformedOriginError("producer_origin must be a JSON object")
    _require_exact_key_set(origin, "producer_origin", _PRODUCER_ORIGIN_FIELDS)

    _require_positive_int(origin["producer_run_id"], "producer_origin.producer_run_id")
    _require_positive_int(
        origin["producer_run_attempt"], "producer_origin.producer_run_attempt"
    )
    workflow_path = _require_workflow_path(origin["workflow_path"], "workflow_path")
    _require_workflow_ref(origin["workflow_ref"], workflow_path, expected_full_name)
    _require_sha(origin["workflow_sha"], "producer_origin.workflow_sha")
    _require_safe_text(origin["publishing_job"], "producer_origin.publishing_job")
    _require_safe_text(origin["publishing_step"], "producer_origin.publishing_step")
    _require_exact(
        origin["credential_origin"],
        "producer_origin.credential_origin",
        CREDENTIAL_ORIGIN,
    )
    _require_positive_int(origin["pr_number"], "producer_origin.pr_number")
    _require_sha(origin["published_source_head"], "producer_origin.published_source_head")
    if origin["selected_target"] not in SELECTED_TARGETS:
        raise MalformedOriginError(
            "producer_origin.selected_target must be exactly 'main' or "
            "'codex/merge-queue-pilot'"
        )
    if not isinstance(origin["original_generation"], str) or not _GENERATION_RE.fullmatch(origin["original_generation"]):
        raise MalformedOriginError("producer_origin.original_generation must be 12 lowercase hex characters")
    _require_sha(origin["candidate_tree"], "producer_origin.candidate_tree")
    _require_sha256(origin["projection_sha256"], "producer_origin.projection_sha256")
    _require_positive_int(
        origin["pr_creation_user_id"], "producer_origin.pr_creation_user_id"
    )
    _require_login(origin["pr_creation_login"], "producer_origin.pr_creation_login")

    if mapping["repository_id"] != repository_id:
        raise OriginIdentityMismatchError(
            "document repository_id does not equal the expected repository identity"
        )

    return mapping


def encode_origin(
    mapping: object,
    *,
    repository_full_name: str,
    repository_id: int,
) -> bytes:
    """Encode a validated producer-origin document to canonical compact bytes.

    Deterministic: sorted keys, compact separators, no incidental whitespace,
    UTF-8.  The caller-supplied ``repository_full_name`` and ``repository_id``
    are the expected identity the document must be bound to; the caller's
    mapping is never mutated.

    This validates syntax and identity binding only; it does not authenticate
    the facts inside the document and does not admit any publication.
    """
    _validate_origin(
        mapping, repository_full_name=repository_full_name, repository_id=repository_id
    )
    origin = mapping["producer_origin"]
    canonical = {
        "schema": SCHEMA_ID,
        "repository_id": mapping["repository_id"],
        "producer_origin": {field: origin[field] for field in _PRODUCER_ORIGIN_FIELDS},
    }
    payload = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise OversizedOriginError(
            "canonical document exceeds %d bytes" % MAX_DOCUMENT_BYTES
        )
    return payload


def decode_origin(
    payload: object,
    *,
    repository_full_name: str,
    repository_id: int,
) -> Dict[str, Any]:
    """Decode canonical producer-origin bytes into a validated mapping.

    Refuses non-bytes payloads, documents over ``MAX_DOCUMENT_BYTES``, invalid
    UTF-8, invalid JSON, duplicate JSON object keys, non-object documents and
    every contract violation ``encode_origin`` refuses.  The caller-supplied
    ``repository_full_name`` and ``repository_id`` are the expected identity
    the document must be bound to.

    A clean decode proves well-formedness and identity binding only.  It does
    not authenticate provenance and does not admit any publication.
    """
    if isinstance(payload, (bytearray, memoryview)):
        payload = bytes(payload)
    if not isinstance(payload, bytes):
        raise MalformedOriginError(
            "encoded producer-origin document must be bytes, got %s"
            % type(payload).__name__
        )
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise OversizedOriginError(
            "document exceeds %d bytes" % MAX_DOCUMENT_BYTES
        )
    if not payload:
        raise MalformedOriginError("document is empty")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise MalformedOriginError("document is not valid UTF-8") from None
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError:
        raise MalformedOriginError("document is not valid JSON") from None
    return _validate_origin(
        parsed, repository_full_name=repository_full_name, repository_id=repository_id
    )


def origin_sha256(payload: object) -> str:
    """SHA-256 hex digest of an encoded producer-origin document.

    Deterministic: identical canonical bytes always produce the identical
    digest.  Accepts bytes-like input only.
    """
    if isinstance(payload, (bytearray, memoryview)):
        payload = bytes(payload)
    if not isinstance(payload, bytes):
        raise MalformedOriginError(
            "encoded producer-origin document must be bytes, got %s"
            % type(payload).__name__
        )
    return hashlib.sha256(payload).hexdigest()
