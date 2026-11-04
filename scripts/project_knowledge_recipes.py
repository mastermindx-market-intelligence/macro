"""Pure typed recipes for canonical AgentOS project-file publication and
project-scoped communication-preference edits.

These recipes are SOURCE-ONLY and DETACHED:

* They accept already-captured trusted bindings (actor scope stamp, permission
  binding digest, captured commit, retained private decision date) and already
  captured preimage texts (workstream record, optional existing project file,
  optional existing decision record).
* They validate the closed public request, re-derive every identity (file id,
  path, decision key) from validated inputs, and return DRAFT_ONLY postimages.
* They never read or write the filesystem, never run Git or subprocesses, never
  touch a network, never mint credentials/grants/identity, and never observe a
  clock.  Publication itself stays with the existing fixed Git publisher, which
  independently re-verifies the sealed action grant, the current principal, the
  source preimages and revisions before any atomic commit and actual receipt.
* Recipe output is always ``state: DRAFT_ONLY``.  It can never claim that an
  attachment was uploaded, that memory was saved, or that anything was
  published or accepted.  Same-ID conflict reconciliation stays with the
  original writer; these recipes never re-issue a conflicting request under a
  new identity.

The two recipes exported here intentionally cover the distinct owner-store
action slots frozen for project knowledge on the sealed v4 owner:

* ``build_project_file_add``      -> action ``project_file_add``
* ``build_project_preference_set`` -> action ``project_preference_set``

Canonical serialization (``canonical``) is UTF-8 JSON with sorted keys,
``,``/``:`` separators, ``ensure_ascii=False`` and ``allow_nan=False``.
"""

from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import re
from typing import Any, Optional

import yaml

__all__ = [
    "KnowledgeRecipeError",
    "canonical",
    "build_project_file_add",
    "build_project_preference_set",
    "MAX_FILE_BYTES",
    "MAX_PREFERENCE_BYTES",
    "MAX_PROJECT_FILES",
]

MAX_FILE_BYTES = 32768
MAX_PREFERENCE_BYTES = 2000
MAX_PROJECT_FILES = 32

MAX_ACTOR_REF_CHARS = 256
MAX_WORKSTREAM_BYTES = 131072
MAX_DECISION_BYTES = 16384
MAX_DISPLAY_NAME_CHARS = 128
MAX_ARTIFACTS = 256
MAX_EVIDENCE = 64
MAX_RECIPE_OUTPUT_BYTES = 262144
MAX_STRUCTURE_DEPTH = 48

SCHEMA_RECIPE = "mastermind.project_knowledge_recipe.v1"
SCHEMA_REQUEST_FINGERPRINT = "mastermind.project_knowledge_request_fingerprint.v1"
SCHEMA_FILE_ADD_REQUEST = "mastermind.project_file_add_request.v1"
SCHEMA_PREFERENCE_SET_REQUEST = "mastermind.project_preference_set_request.v1"

SCHEMA_WORKSTREAM = "agentos.workstream.v1"
SCHEMA_DECISION = "agentos.decision.v1"
SCHEMA_PROJECT_PREFERENCE = "agentos.project_preference.v1"

FILE_ADD_REQUEST_ID_PREFIX = "mmos-project-file-add-"
PREFERENCE_REQUEST_ID_PREFIX = "mmos-project-preference-set-"

ACTOR_REF_PREFIX = "workspace:"
STATE_DRAFT_ONLY = "DRAFT_ONLY"
ACTION_FILE_ADD = "project_file_add"
ACTION_PREFERENCE_SET = "project_preference_set"

ORIGIN_PRINCIPAL_UPLOAD = "PRINCIPAL_UPLOAD"
ORIGIN_USER_EDIT = "USER_EDIT"
ORIGIN_CONVERSATION = "CONVERSATION"

MEDIA_MD = "text/markdown"
MEDIA_TXT = "text/plain"

PREFERENCE_KIND = "COMMUNICATION"
PREFERENCE_DECISION_KEY_PREFIX = "PROJECT-COMMUNICATION-PREFERENCE-"
PREFERENCE_QUESTION = "How should this project communicate with its owner?"
PREFERENCE_RATIONALE = (
    "Explicit project-scoped communication preference supplied through the "
    "authorized project editor."
)
PREFERENCE_ALTERNATIVE_OPTION = "Leave the preference unset"
PREFERENCE_ALTERNATIVE_WHY_NOT = "The authorized editor requested this value."
EVIDENCE_ENTRY_PREFIX = "project-authoring-request:"

WORKSTREAM_DIR = "agentos/workstreams"
PROJECT_FILES_DIR = "agentos/project-files"
DECISIONS_DIR = "agentos/decisions"

_ERROR_MESSAGES = {
    "MALFORMED_REQUEST_SCHEMA": "request does not match the closed public request schema",
    "INVALID_REQUEST_ID": "request_id does not match the fixed action prefix and a 40 hex stamp",
    "INVALID_ACTOR_REF": "actor_ref is not a trusted bounded workspace scope stamp",
    "INVALID_PERMISSION_BINDING_DIGEST": "permission_binding_digest is not a 64 lower hex stamp",
    "INVALID_CAPTURED_COMMIT": "captured_commit is not a 40 lower hex commit stamp",
    "INVALID_WORKSTREAM_TEXT": "workstream_text is not bounded UTF-8 record text",
    "INVALID_WORK_REF": "work_ref is not a canonical WS: reference",
    "SOURCE_COMMIT_MISMATCH": "request source_commit does not equal the captured commit",
    "BASE_REVISION_MISMATCH": "request base_revision does not equal the workstream preimage stamp",
    "WORK_SCOPE_MISMATCH": "workstream record key does not equal the work_ref key",
    "INVALID_WORKSTREAM_RECORD": "workstream record frontmatter is malformed or not canonical",
    "INVALID_WORKSTREAM_FIELD": "workstream record is missing required structural fields",
    "REPOSITORY_SCOPE_MISMATCH": "workstream state does not include the macro repo member",
    "INVALID_EXISTING_PROJECT_FILE": "an existing recorded project file entry is not a closed entry",
    "INVALID_PROJECT_FILE": "project file request content is not a valid bounded UTF-8 media file",
    "LIMIT_EXCEEDED": "a bounded size or count limit is exceeded",
    "ALREADY_RECORDED": "the same original identity or path is already recorded",
    "CONFLICT": "the same identity or path is recorded with different metadata",
    "INVALID_DECISION_DATE": "decision_date is not a real YYYY-MM-DD calendar date",
    "INVALID_PREFERENCE_VALUE": "preference value is not a nonblank bounded literal scalar",
    "SOURCE_MISMATCH": "decision source association does not match the expected revision or pointer",
    "INVALID_EXISTING_DECISION": "existing decision record is not the canonical fixed-key record",
}


class KnowledgeRecipeError(Exception):
    """Fixed safe recipe diagnostic.

    Carries only a stable ``code``.  The message is a constant per code and
    never echoes rejected input, so refused drafts leak no payload text.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(_ERROR_MESSAGES.get(code, "recipe rejected the request"))


_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_HEX40_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_UPPER_KEBAB_RE = re.compile(r"\A[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_WORK_REF_RE = re.compile(r"\AWS:[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_DEC_POINTER_RE = re.compile(r"\ADEC:[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_SESSION_REPLY_REF_RE = re.compile(r"\Asession-reply-[0-9a-f]{64}\Z")
_DECISION_DATE_RE = re.compile(r"\A([0-9]{4})-([0-9]{2})-([0-9]{2})\Z")
_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", re.DOTALL
)

_ALLOWED_CONTROLS = frozenset("\n\r\t")

_WS_STATUS_VALUES = frozenset(
    ["proposed", "active", "blocked", "awaiting_ci", "awaiting_review",
     "done", "parked", "killed"]
)
_WS_PROGRAM_CLASS_VALUES = frozenset(
    ["research", "build", "design", "adjudication", "mechanical"]
)
_WS_BLAST_RADIUS_VALUES = frozenset(["reversible", "user_facing", "irreversible"])
_WS_AMBIGUITY_VALUES = frozenset(["specified", "scoped", "open"])
_WS_REPO_VALUES = frozenset(["macro", "terminal", "mastermind"])

_WS_REQUIRED_SCALARS = ("title", "objective", "program", "owner", "next_action")

_PROJECT_FILE_ENTRY_KEYS = frozenset(
    ["file_id", "artifact_ref", "display_name", "media_type", "content_sha256",
     "origin"]
)
_PROJECT_FILE_ORIGIN_KEYS = frozenset(["kind", "actor_ref", "request_sha256"])

_FILE_ADD_REQUEST_KEYS = frozenset(
    ["schema", "request_id", "work_ref", "source_commit", "base_revision", "file"]
)
_FILE_REQUEST_KEYS = frozenset(["display_name", "media_type", "content_utf8"])

_PREFERENCE_REQUEST_KEYS = frozenset(
    ["schema", "request_id", "work_ref", "source_commit", "base_revision",
     "expected_preference_revision", "value"]
)

_RECIPE_KEYS = frozenset(
    ["schema", "state", "action", "work_ref", "request_id",
     "request_fingerprint", "captured_commit", "permission_binding_digest",
     "postimages"]
)
_POSTIMAGE_KEYS = frozenset(
    ["path", "content_utf8", "content_sha256", "expected_preimage_sha256"]
)

_PREFERENCE_ORIGIN_KEYS = frozenset(
    ["kind", "actor_ref", "source_ref", "source_revision"]
)
_PREFERENCE_LAST_EDIT_KEYS = frozenset(["actor_ref", "request_sha256"])
_PREFERENCE_KEYS = frozenset(
    ["schema", "work_ref", "kind", "value", "origin", "last_edit"]
)

_DECISION_ALLOWED_KEYS = frozenset(
    ["schema", "key", "question", "answer", "rationale", "alternatives",
     "evidence", "affects", "confidence", "reversibility", "decided_by",
     "decided_at", "project_preference", "review_by", "supersedes"]
)

def canonical(value: Any) -> str:
    """Canonical UTF-8 JSON: sorted keys, ``(',',':')``, non-ASCII raw, no NaN."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        raise KnowledgeRecipeError("MALFORMED_REQUEST_SCHEMA") from None


def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_str(value: Any, code: str) -> str:
    if type(value) is not str:
        raise KnowledgeRecipeError(code)
    return value


def _require_exact_keys(mapping: Any, expected: frozenset, code: str) -> dict:
    if type(mapping) is not dict:
        raise KnowledgeRecipeError(code)
    keys = set(mapping.keys())
    if keys != set(expected):
        raise KnowledgeRecipeError(code)
    return mapping


def _require_hex64(value: Any, code: str) -> str:
    _require_str(value, code)
    if not _HEX64_RE.fullmatch(value):
        raise KnowledgeRecipeError(code)
    return value


def _validate_actor_ref(actor_ref: Any) -> str:
    _require_str(actor_ref, "INVALID_ACTOR_REF")
    if not actor_ref.startswith(ACTOR_REF_PREFIX):
        raise KnowledgeRecipeError("INVALID_ACTOR_REF")
    try:
        actor_bytes = actor_ref.encode("utf-8")
    except UnicodeEncodeError:
        raise KnowledgeRecipeError("INVALID_ACTOR_REF") from None
    if len(actor_bytes) > MAX_ACTOR_REF_CHARS:
        raise KnowledgeRecipeError("INVALID_ACTOR_REF")
    scope = actor_ref[len(ACTOR_REF_PREFIX):]
    if not scope:
        raise KnowledgeRecipeError("INVALID_ACTOR_REF")
    for char in scope:
        if char.isspace() or ord(char) < 0x20 or 0x7F <= ord(char) <= 0x9F:
            raise KnowledgeRecipeError("INVALID_ACTOR_REF")
    return actor_ref


def _validate_permission_binding_digest(digest: Any) -> str:
    _require_str(digest, "INVALID_PERMISSION_BINDING_DIGEST")
    if not _HEX64_RE.fullmatch(digest):
        raise KnowledgeRecipeError("INVALID_PERMISSION_BINDING_DIGEST")
    return digest


def _validate_captured_commit(commit: Any) -> str:
    _require_str(commit, "INVALID_CAPTURED_COMMIT")
    if not _HEX40_RE.fullmatch(commit):
        raise KnowledgeRecipeError("INVALID_CAPTURED_COMMIT")
    return commit


def _validate_work_ref(work_ref: Any) -> str:
    _require_str(work_ref, "INVALID_WORK_REF")
    if not _WORK_REF_RE.fullmatch(work_ref):
        raise KnowledgeRecipeError("INVALID_WORK_REF")
    key = work_ref[len("WS:"):]
    if not 2 <= len(key) <= 64:
        raise KnowledgeRecipeError("INVALID_WORK_REF")
    return work_ref


def _validate_request_id(request_id: Any, prefix: str) -> str:
    _require_str(request_id, "INVALID_REQUEST_ID")
    if not request_id.startswith(prefix):
        raise KnowledgeRecipeError("INVALID_REQUEST_ID")
    stamp = request_id[len(prefix):]
    if not _HEX40_RE.fullmatch(stamp):
        raise KnowledgeRecipeError("INVALID_REQUEST_ID")
    return request_id


def _validate_bounded_utf8(
    value: Any,
    *,
    code: str,
    max_bytes: int,
    allow_empty: bool = False,
    allowed_controls: frozenset = _ALLOWED_CONTROLS,
) -> bytes:
    text = _require_str(value, code)
    try:
        raw = text.encode("utf-8")
    except UnicodeEncodeError:
        raise KnowledgeRecipeError(code) from None
    if not raw and not allow_empty:
        raise KnowledgeRecipeError(code)
    if len(raw) > max_bytes:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    for char in text:
        if char in allowed_controls:
            continue
        point = ord(char)
        if point < 0x20 or 0x7F <= point <= 0x9F:
            raise KnowledgeRecipeError(code)
    return raw


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys."""


def _construct_mapping_no_duplicates(loader: Any, node: Any, deep: bool = False) -> dict:
    seen = set()
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if isinstance(key, (list, dict)):
            raise yaml.constructor.ConstructorError(
                None, None, "unhashable mapping key", key_node.start_mark
            )
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate mapping key", key_node.start_mark
            )
        seen.add(key)
    return yaml.constructor.SafeConstructor.construct_mapping(loader, node, deep=deep)


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


def _check_acyclic(node: Any, depth: int = 0, seen: frozenset = frozenset(), budget=None) -> None:
    if budget is None:
        budget = [8192]
    budget[0] -= 1
    if budget[0] < 0:
        raise KnowledgeRecipeError("INVALID_WORKSTREAM_RECORD")
    if depth > MAX_STRUCTURE_DEPTH:
        raise KnowledgeRecipeError("INVALID_WORKSTREAM_RECORD")
    if isinstance(node, dict):
        marker = frozenset([id(node)]) | seen
        if id(node) in seen:
            raise KnowledgeRecipeError("INVALID_WORKSTREAM_RECORD")
        for value in node.values():
            _check_acyclic(value, depth + 1, marker, budget)
    elif isinstance(node, list):
        marker = frozenset([id(node)]) | seen
        if id(node) in seen:
            raise KnowledgeRecipeError("INVALID_WORKSTREAM_RECORD")
        for value in node:
            _check_acyclic(value, depth + 1, marker, budget)


def _load_record(text: str, code: str) -> tuple:
    """Split ``text`` into (detached frontmatter mapping, exact body text)."""
    if isinstance(text, bool) or not isinstance(text, str):
        raise KnowledgeRecipeError(code)
    match = _FRONTMATTER_RE.fullmatch(text)
    if not match:
        raise KnowledgeRecipeError(code)
    try:
        data = yaml.load(match.group(1), Loader=_StrictSafeLoader)
    except (yaml.YAMLError, TypeError, ValueError, RecursionError):
        raise KnowledgeRecipeError(code) from None
    except KnowledgeRecipeError:
        raise
    if not isinstance(data, dict):
        raise KnowledgeRecipeError(code)
    _check_acyclic(data)
    return copy.deepcopy(data), match.group(2)


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100000,
    )


def _serialize_record(data: dict, body: str) -> str:
    return "---\n" + _dump_yaml(data) + "---\n" + body


def _require_nonempty_str(mapping: dict, field: str, code: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or isinstance(value, bool) or not value.strip():
        raise KnowledgeRecipeError(code)
    return value


def _require_enum(mapping: dict, field: str, allowed: frozenset, code: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or value not in allowed:
        raise KnowledgeRecipeError(code)
    return value


def _require_str_list(
    mapping: dict,
    field: str,
    code: str,
    default: Optional[list] = None,
    pattern: Any = None,
) -> list:
    if field not in mapping:
        if default is None:
            raise KnowledgeRecipeError(code)
        return list(default)
    value = mapping[field]
    if not isinstance(value, list):
        raise KnowledgeRecipeError(code)
    for item in value:
        if not isinstance(item, str) or isinstance(item, bool):
            raise KnowledgeRecipeError(code)
        if not item:
            raise KnowledgeRecipeError(code)
        if pattern is not None and not pattern.fullmatch(item):
            raise KnowledgeRecipeError(code)
    return list(value)

def _validate_display_name(name: Any) -> str:
    _require_str(name, "INVALID_PROJECT_FILE")
    if not name or len(name) > MAX_DISPLAY_NAME_CHARS:
        raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
    for char in name:
        if char in _ALLOWED_CONTROLS:
            raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
        point = ord(char)
        if point < 0x20 or 0x7F <= point <= 0x9F:
            raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
    if "/" in name or "\\" in name:
        raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
    if "." not in name:
        raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
    stem, _, ext = name.rpartition(".")
    ext = ext.lower()
    if not stem or ext not in ("md", "txt"):
        raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
    return ext


def _validate_media_type(media_type: Any, ext: str) -> str:
    _require_str(media_type, "INVALID_PROJECT_FILE")
    expected = MEDIA_MD if ext == "md" else MEDIA_TXT
    if media_type != expected:
        raise KnowledgeRecipeError("INVALID_PROJECT_FILE")
    return media_type


def _validate_project_file_entry(entry: Any, ws_key: str) -> dict:
    _require_exact_keys(entry, _PROJECT_FILE_ENTRY_KEYS, "INVALID_EXISTING_PROJECT_FILE")
    file_id = _require_hex64(entry["file_id"], "INVALID_EXISTING_PROJECT_FILE")
    _require_hex64(entry["content_sha256"], "INVALID_EXISTING_PROJECT_FILE")
    display_name = entry["display_name"]
    ext = _validate_display_name(display_name)
    media_type = entry["media_type"]
    _validate_media_type(media_type, ext)
    expected_path = f"{PROJECT_FILES_DIR}/WS-{ws_key}/{file_id}.{ext}"
    if entry["artifact_ref"] != expected_path:
        raise KnowledgeRecipeError("INVALID_EXISTING_PROJECT_FILE")
    origin = _require_exact_keys(
        entry["origin"], _PROJECT_FILE_ORIGIN_KEYS, "INVALID_EXISTING_PROJECT_FILE"
    )
    if origin["kind"] != ORIGIN_PRINCIPAL_UPLOAD:
        raise KnowledgeRecipeError("INVALID_EXISTING_PROJECT_FILE")
    _validate_actor_ref(origin["actor_ref"])
    _require_hex64(origin["request_sha256"], "INVALID_EXISTING_PROJECT_FILE")
    return entry


def _validate_workstream(data: dict, work_ref: str) -> str:
    """Structural checks on the WS preimage.  Returns the WS key."""
    if "schema" in data and data["schema"] != SCHEMA_WORKSTREAM:
        raise KnowledgeRecipeError("INVALID_WORKSTREAM_RECORD")
    key = data.get("key")
    _require_str(key, "INVALID_WORKSTREAM_FIELD")
    if not _UPPER_KEBAB_RE.fullmatch(key) or not 2 <= len(key) <= 64:
        raise KnowledgeRecipeError("INVALID_WORKSTREAM_FIELD")
    if key != work_ref[len("WS:"):]:
        raise KnowledgeRecipeError("WORK_SCOPE_MISMATCH")
    for field in _WS_REQUIRED_SCALARS:
        _require_nonempty_str(data, field, "INVALID_WORKSTREAM_FIELD")
    _require_enum(data, "status", _WS_STATUS_VALUES, "INVALID_WORKSTREAM_FIELD")
    _require_enum(data, "class", _WS_PROGRAM_CLASS_VALUES, "INVALID_WORKSTREAM_FIELD")
    _require_enum(data, "blast_radius", _WS_BLAST_RADIUS_VALUES, "INVALID_WORKSTREAM_FIELD")
    _require_enum(data, "ambiguity", _WS_AMBIGUITY_VALUES, "INVALID_WORKSTREAM_FIELD")
    repos = data.get("repos")
    if not isinstance(repos, list) or not repos:
        raise KnowledgeRecipeError("REPOSITORY_SCOPE_MISMATCH")
    for item in repos:
        if not isinstance(item, str) or item not in _WS_REPO_VALUES:
            raise KnowledgeRecipeError("REPOSITORY_SCOPE_MISMATCH")
    if "macro" not in repos:
        raise KnowledgeRecipeError("REPOSITORY_SCOPE_MISMATCH")
    waves = data.get("waves")
    if not isinstance(waves, list) or not waves:
        raise KnowledgeRecipeError("INVALID_WORKSTREAM_FIELD")
    for wave in waves:
        if not isinstance(wave, dict):
            raise KnowledgeRecipeError("INVALID_WORKSTREAM_FIELD")
    _validate_workstream_lists(data)
    return key


def _validate_workstream_lists(data: dict) -> None:
    _require_str_list(
        data, "decisions", "INVALID_WORKSTREAM_FIELD", default=[], pattern=_DEC_POINTER_RE
    )
    artifacts = _require_str_list(
        data, "artifacts", "INVALID_WORKSTREAM_FIELD", default=[]
    )
    if len(artifacts) > MAX_ARTIFACTS:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    for item in artifacts:
        if item.startswith("/") or item.startswith("\\"):
            raise KnowledgeRecipeError("INVALID_WORKSTREAM_FIELD")
        if "\x00" in item:
            raise KnowledgeRecipeError("INVALID_WORKSTREAM_FIELD")
        if any(part == ".." for part in item.replace("\\", "/").split("/")):
            raise KnowledgeRecipeError("INVALID_WORKSTREAM_FIELD")
    project_files = data.get("project_files", [])
    if not isinstance(project_files, list):
        raise KnowledgeRecipeError("INVALID_EXISTING_PROJECT_FILE")
    if len(project_files) > MAX_PROJECT_FILES:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    seen_ids = set()
    seen_paths = set()
    ws_key = data["key"]
    for entry in project_files:
        validated = _validate_project_file_entry(entry, ws_key)
        if validated["file_id"] in seen_ids or validated["artifact_ref"] in seen_paths:
            raise KnowledgeRecipeError("CONFLICT")
        if validated["artifact_ref"] not in artifacts:
            raise KnowledgeRecipeError("INVALID_EXISTING_PROJECT_FILE")
        seen_ids.add(validated["file_id"])
        seen_paths.add(validated["artifact_ref"])

def _validate_public_request(
    request: Any,
    *,
    schema: str,
    keys: frozenset,
    request_id_prefix: str,
) -> dict:
    _require_exact_keys(request, keys, "MALFORMED_REQUEST_SCHEMA")
    if request["schema"] != schema:
        raise KnowledgeRecipeError("MALFORMED_REQUEST_SCHEMA")
    _validate_request_id(request["request_id"], request_id_prefix)
    _validate_work_ref(request["work_ref"])
    _require_hex64(request["base_revision"], "MALFORMED_REQUEST_SCHEMA")
    _require_str(request["source_commit"], "MALFORMED_REQUEST_SCHEMA")
    if not _HEX40_RE.fullmatch(request["source_commit"]):
        raise KnowledgeRecipeError("MALFORMED_REQUEST_SCHEMA")
    return copy.deepcopy(request)


def _validate_trusted_bindings(
    *,
    actor_ref: Any,
    permission_binding_digest: Any,
    captured_commit: Any,
    workstream_text: Any,
) -> bytes:
    _validate_actor_ref(actor_ref)
    _validate_permission_binding_digest(permission_binding_digest)
    _validate_captured_commit(captured_commit)
    return _validate_bounded_utf8(
        workstream_text, code="INVALID_WORKSTREAM_TEXT", max_bytes=MAX_WORKSTREAM_BYTES
    )


def _request_fingerprint(
    *,
    request: dict,
    actor_ref: str,
    permission_binding_digest: str,
    captured_commit: str,
    workstream_sha256: str,
    decision_sha256: Optional[str],
) -> str:
    payload = {
        "schema": SCHEMA_REQUEST_FINGERPRINT,
        "request": request,
        "actor_ref": actor_ref,
        "permission_binding_digest": permission_binding_digest,
        "captured_commit": captured_commit,
        "preimages": ({"workstream": workstream_sha256, "file": None}
            if request["schema"] == SCHEMA_FILE_ADD_REQUEST else
            {"workstream": workstream_sha256, "decision": decision_sha256}),
    }
    return _sha256_hex(canonical(payload).encode("utf-8"))


def _recipe_envelope(
    *,
    action: str,
    work_ref: str,
    request_id: str,
    fingerprint: str,
    captured_commit: str,
    permission_binding_digest: str,
    postimages: list,
) -> dict:
    recipe = {
        "schema": SCHEMA_RECIPE,
        "state": STATE_DRAFT_ONLY,
        "action": action,
        "work_ref": work_ref,
        "request_id": request_id,
        "request_fingerprint": fingerprint,
        "captured_commit": captured_commit,
        "permission_binding_digest": permission_binding_digest,
        "postimages": postimages,
    }
    _require_exact_keys(recipe, _RECIPE_KEYS, "MALFORMED_REQUEST_SCHEMA")
    total = 0
    if len(recipe["postimages"]) > 2:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    for image in recipe["postimages"]:
        _require_exact_keys(image, _POSTIMAGE_KEYS, "MALFORMED_REQUEST_SCHEMA")
        total += len(image["content_utf8"].encode("utf-8"))
    if total > MAX_RECIPE_OUTPUT_BYTES:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    return recipe


def _media_postimage(path: str, content_utf8: str, content_raw: bytes) -> dict:
    return {
        "path": path,
        "content_utf8": content_utf8,
        "content_sha256": _sha256_hex(content_raw),
        "expected_preimage_sha256": None,
    }


def _ws_postimage(ws_key: str, data: dict, body: str, ws_sha256: str) -> dict:
    text = _serialize_record(data, body)
    return {
        "path": f"{WORKSTREAM_DIR}/WS-{ws_key}.md",
        "content_utf8": text,
        "content_sha256": _sha256_hex(text.encode("utf-8")),
        "expected_preimage_sha256": ws_sha256,
    }


def build_project_file_add(
    request: Any,
    *,
    actor_ref: str,
    permission_binding_digest: str,
    captured_commit: str,
    workstream_text: str,
    existing_file_text: Optional[str] = None,
) -> dict:
    """Build the DRAFT_ONLY postimages for ``project_file_add``.

    ``existing_file_text`` is the trusted captured preimage observed at the
    would-be target path; ``None`` means the publisher reports the path
    currently absent.  Any captured text at that path is ALREADY_RECORDED:
    the original owner reconciles the SAME original request id, and no
    overwrite or adoption-by-existence happens here.  A recorded entry with
    the same identity and payload is ALREADY_RECORDED; the same id or path
    with a different payload is CONFLICT.
    """
    _validate_trusted_bindings(
        actor_ref=actor_ref,
        permission_binding_digest=permission_binding_digest,
        captured_commit=captured_commit,
        workstream_text=workstream_text,
    )
    if existing_file_text is not None:
        if isinstance(existing_file_text, bool) or not isinstance(existing_file_text, str):
            raise KnowledgeRecipeError("INVALID_EXISTING_PROJECT_FILE")
    validated = _validate_public_request(
        request,
        schema=SCHEMA_FILE_ADD_REQUEST,
        keys=_FILE_ADD_REQUEST_KEYS,
        request_id_prefix=FILE_ADD_REQUEST_ID_PREFIX,
    )
    work_ref = validated["work_ref"]
    if validated["source_commit"] != captured_commit:
        raise KnowledgeRecipeError("SOURCE_COMMIT_MISMATCH")
    ws_raw = workstream_text.encode("utf-8")
    if validated["base_revision"] != _sha256_hex(ws_raw):
        raise KnowledgeRecipeError("BASE_REVISION_MISMATCH")
    ws_data, ws_body = _load_record(workstream_text, "INVALID_WORKSTREAM_RECORD")
    ws_key = _validate_workstream(ws_data, work_ref)
    ws_sha256 = _sha256_hex(ws_raw)

    file_request = _require_exact_keys(
        validated["file"], _FILE_REQUEST_KEYS, "MALFORMED_REQUEST_SCHEMA"
    )
    display_name = file_request["display_name"]
    ext = _validate_display_name(display_name)
    media_type = file_request["media_type"]
    _validate_media_type(media_type, ext)
    content_utf8 = file_request["content_utf8"]
    content_raw = _validate_bounded_utf8(
        content_utf8, code="INVALID_PROJECT_FILE", max_bytes=MAX_FILE_BYTES
    )

    file_id = _sha256_hex(
        canonical(
            {
                "principal_scope": actor_ref[len(ACTOR_REF_PREFIX):],
                "request_id": validated["request_id"],
                "work_ref": work_ref,
            }
        ).encode("utf-8")
    )
    artifact_ref = f"{PROJECT_FILES_DIR}/WS-{ws_key}/{file_id}.{ext}"
    content_sha256 = _sha256_hex(content_raw)

    fingerprint = _request_fingerprint(
        request=validated,
        actor_ref=actor_ref,
        permission_binding_digest=permission_binding_digest,
        captured_commit=captured_commit,
        workstream_sha256=ws_sha256,
        decision_sha256=None,
    )

    existing_entries = list(ws_data.get("project_files") or [])
    target_entry = {
        "file_id": file_id,
        "artifact_ref": artifact_ref,
        "display_name": display_name,
        "media_type": media_type,
        "content_sha256": content_sha256,
        "origin": {
            "kind": ORIGIN_PRINCIPAL_UPLOAD,
            "actor_ref": actor_ref,
            "request_sha256": fingerprint,
        },
    }
    for entry in existing_entries:
        same_payload = all(
            entry.get(field) == target_entry[field]
            for field in ("file_id", "artifact_ref", "display_name",
                          "media_type", "content_sha256")
        )
        if same_payload:
            raise KnowledgeRecipeError("ALREADY_RECORDED")
        if entry["file_id"] == file_id or entry["artifact_ref"] == artifact_ref:
            raise KnowledgeRecipeError("CONFLICT")
    if existing_file_text is not None:
        raise KnowledgeRecipeError("ALREADY_RECORDED")
    if len(existing_entries) + 1 > MAX_PROJECT_FILES:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")

    artifacts = list(ws_data.get("artifacts") or [])
    if artifact_ref in artifacts:
        raise KnowledgeRecipeError("CONFLICT")
    if len(artifacts) + 1 > MAX_ARTIFACTS:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")

    ws_data["project_files"] = existing_entries + [target_entry]
    ws_data["artifacts"] = artifacts + [artifact_ref]

    postimages = [
        _media_postimage(artifact_ref, content_utf8, content_raw),
        _ws_postimage(ws_key, ws_data, ws_body, ws_sha256),
    ]
    return _recipe_envelope(
        action=ACTION_FILE_ADD,
        work_ref=work_ref,
        request_id=validated["request_id"],
        fingerprint=fingerprint,
        captured_commit=captured_commit,
        permission_binding_digest=permission_binding_digest,
        postimages=postimages,
    )

def _validate_decision_date(value: Any) -> str:
    _require_str(value, "INVALID_DECISION_DATE")
    match = _DECISION_DATE_RE.fullmatch(value)
    if not match:
        raise KnowledgeRecipeError("INVALID_DECISION_DATE")
    year, month, day = (int(part) for part in match.groups())
    if month < 1 or month > 12 or day < 1 or day > 31 or year < 1:
        raise KnowledgeRecipeError("INVALID_DECISION_DATE")
    try:
        _dt.date(year, month, day)
    except ValueError:
        raise KnowledgeRecipeError("INVALID_DECISION_DATE") from None
    return value


def _validate_preference_origin(origin: Any, code: str) -> dict:
    _require_exact_keys(origin, _PREFERENCE_ORIGIN_KEYS, code)
    kind = origin["kind"]
    if kind not in (ORIGIN_USER_EDIT, ORIGIN_CONVERSATION):
        raise KnowledgeRecipeError(code)
    _validate_actor_ref(origin["actor_ref"])
    if kind == ORIGIN_USER_EDIT:
        if origin["source_ref"] is not None or origin["source_revision"] is not None:
            raise KnowledgeRecipeError(code)
    else:
        source_ref = origin["source_ref"]
        if (
            not isinstance(source_ref, str)
            or not _SESSION_REPLY_REF_RE.fullmatch(source_ref)
        ):
            raise KnowledgeRecipeError(code)
        _require_hex64(origin["source_revision"], code)
    return origin


def _validate_project_preference(preference: Any, work_ref: str, code: str) -> dict:
    _require_exact_keys(preference, _PREFERENCE_KEYS, code)
    if preference["schema"] != SCHEMA_PROJECT_PREFERENCE:
        raise KnowledgeRecipeError(code)
    if preference["work_ref"] != work_ref:
        raise KnowledgeRecipeError(code)
    if preference["kind"] != PREFERENCE_KIND:
        raise KnowledgeRecipeError(code)
    _validate_bounded_utf8(
        preference["value"], code=code, max_bytes=MAX_PREFERENCE_BYTES
    )
    _validate_preference_origin(preference["origin"], code)
    last_edit = _require_exact_keys(
        preference["last_edit"], _PREFERENCE_LAST_EDIT_KEYS, code
    )
    _validate_actor_ref(last_edit["actor_ref"])
    _require_hex64(last_edit["request_sha256"], code)
    return preference


def _validate_existing_preference_decision(
    data: dict,
    *,
    decision_key: str,
    work_ref: str,
) -> dict:
    code = "INVALID_EXISTING_DECISION"
    if data.get("schema") != SCHEMA_DECISION:
        raise KnowledgeRecipeError(code)
    unknown = set(data.keys()) - _DECISION_ALLOWED_KEYS
    if unknown:
        raise KnowledgeRecipeError(code)
    if "superseded_by" in data:
        raise KnowledgeRecipeError(code)
    supersedes = data.get("supersedes")
    if supersedes is not None and supersedes != []:
        raise KnowledgeRecipeError(code)
    if data.get("key") != decision_key:
        raise KnowledgeRecipeError(code)
    for field in ("question", "answer", "rationale", "decided_by", "decided_at"):
        if field not in data or not isinstance(data[field], str):
            raise KnowledgeRecipeError(code)
    if data["question"] != PREFERENCE_QUESTION:
        raise KnowledgeRecipeError(code)
    if data["rationale"] != PREFERENCE_RATIONALE:
        raise KnowledgeRecipeError(code)
    expected_alternatives = [
        {
            "option": PREFERENCE_ALTERNATIVE_OPTION,
            "why_not": PREFERENCE_ALTERNATIVE_WHY_NOT,
        }
    ]
    if data.get("alternatives") != expected_alternatives:
        raise KnowledgeRecipeError(code)
    if data.get("confidence") != "high" or data.get("reversibility") != "easy":
        raise KnowledgeRecipeError(code)
    if data.get("affects") != [work_ref]:
        raise KnowledgeRecipeError(code)
    evidence = data.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise KnowledgeRecipeError(code)
    for item in evidence:
        if not isinstance(item, str) or isinstance(item, bool) or not item:
            raise KnowledgeRecipeError(code)
    if len(evidence) > MAX_EVIDENCE:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    _validate_actor_ref(data["decided_by"])
    _validate_decision_date(data["decided_at"])
    review_by = data.get("review_by")
    if review_by is not None:
        _validate_decision_date(review_by)
    preference = data.get("project_preference")
    _validate_project_preference(preference, work_ref, code)
    if data["answer"] != preference["value"]:
        raise KnowledgeRecipeError(code)
    return preference

def build_project_preference_set(
    request: Any,
    *,
    actor_ref: str,
    permission_binding_digest: str,
    captured_commit: str,
    workstream_text: str,
    decision_text: Optional[str],
    decision_date: str,
) -> dict:
    """Build the DRAFT_ONLY postimages for ``project_preference_set``.

    ``decision_date`` is the retained private date supplied by the trusted
    caller; it is validated as a real calendar date and never derived from a
    clock here.  ``decision_text`` is the captured preimage of the fixed-key
    decision record, or ``None`` when the publisher reports no such record.
    The public request carries no origin: a new record is USER_EDIT, and a
    qualified CONVERSATION origin can only ever be preserved from a validated
    canonical preimage.
    """
    _validate_trusted_bindings(
        actor_ref=actor_ref,
        permission_binding_digest=permission_binding_digest,
        captured_commit=captured_commit,
        workstream_text=workstream_text,
    )
    _validate_decision_date(decision_date)
    validated = _validate_public_request(
        request,
        schema=SCHEMA_PREFERENCE_SET_REQUEST,
        keys=_PREFERENCE_REQUEST_KEYS,
        request_id_prefix=PREFERENCE_REQUEST_ID_PREFIX,
    )
    work_ref = validated["work_ref"]
    if validated["source_commit"] != captured_commit:
        raise KnowledgeRecipeError("SOURCE_COMMIT_MISMATCH")
    ws_raw = workstream_text.encode("utf-8")
    if validated["base_revision"] != _sha256_hex(ws_raw):
        raise KnowledgeRecipeError("BASE_REVISION_MISMATCH")
    _validate_bounded_utf8(
        validated["value"], code="INVALID_PREFERENCE_VALUE",
        max_bytes=MAX_PREFERENCE_BYTES,
    )
    if not validated["value"].strip():
        raise KnowledgeRecipeError("INVALID_PREFERENCE_VALUE")
    expected_revision = validated["expected_preference_revision"]
    if expected_revision is not None:
        _require_hex64(expected_revision, "MALFORMED_REQUEST_SCHEMA")

    ws_data, ws_body = _load_record(workstream_text, "INVALID_WORKSTREAM_RECORD")
    ws_key = _validate_workstream(ws_data, work_ref)
    ws_sha256 = _sha256_hex(ws_raw)
    decisions = list(ws_data.get("decisions") or [])

    decision_key = PREFERENCE_DECISION_KEY_PREFIX + ws_key
    pointer = "DEC:" + decision_key
    value = validated["value"]

    if decision_text is None:
        if expected_revision is not None:
            raise KnowledgeRecipeError("SOURCE_MISMATCH")
        if pointer in decisions:
            raise KnowledgeRecipeError("SOURCE_MISMATCH")
        decision_sha256 = None
        decision_data = None
        decision_body = ""
    else:
        decision_raw = _validate_bounded_utf8(
            decision_text, code="INVALID_EXISTING_DECISION",
            max_bytes=MAX_DECISION_BYTES,
        )
        decision_sha256 = _sha256_hex(decision_raw)
        if expected_revision != decision_sha256:
            raise KnowledgeRecipeError("SOURCE_MISMATCH")
        if pointer not in decisions:
            raise KnowledgeRecipeError("SOURCE_MISMATCH")
        decision_data, decision_body = _load_record(
            decision_text, "INVALID_EXISTING_DECISION"
        )
        _validate_existing_preference_decision(
            decision_data, decision_key=decision_key, work_ref=work_ref
        )

    fingerprint = _request_fingerprint(
        request=validated,
        actor_ref=actor_ref,
        permission_binding_digest=permission_binding_digest,
        captured_commit=captured_commit,
        workstream_sha256=ws_sha256,
        decision_sha256=decision_sha256,
    )
    evidence_entry = EVIDENCE_ENTRY_PREFIX + fingerprint

    if decision_data is None:
        record = {
            "schema": SCHEMA_DECISION,
            "key": decision_key,
            "question": PREFERENCE_QUESTION,
            "answer": value,
            "rationale": PREFERENCE_RATIONALE,
            "alternatives": [
                {
                    "option": PREFERENCE_ALTERNATIVE_OPTION,
                    "why_not": PREFERENCE_ALTERNATIVE_WHY_NOT,
                }
            ],
            "evidence": [evidence_entry],
            "affects": [work_ref],
            "confidence": "high",
            "reversibility": "easy",
            "decided_by": actor_ref,
            "decided_at": decision_date,
            "project_preference": {
                "schema": SCHEMA_PROJECT_PREFERENCE,
                "work_ref": work_ref,
                "kind": PREFERENCE_KIND,
                "value": value,
                "origin": {
                    "kind": ORIGIN_USER_EDIT,
                    "actor_ref": actor_ref,
                    "source_ref": None,
                    "source_revision": None,
                },
                "last_edit": {
                    "actor_ref": actor_ref,
                    "request_sha256": fingerprint,
                },
            },
        }
        decision_post = {
            "path": f"{DECISIONS_DIR}/DEC-{decision_key}.md",
            "content_utf8": _serialize_record(record, ""),
            "content_sha256": None,
            "expected_preimage_sha256": None,
        }
        decision_post["content_sha256"] = _sha256_hex(
            decision_post["content_utf8"].encode("utf-8")
        )
        ws_data["decisions"] = decisions + [pointer]
    else:
        preference = decision_data["project_preference"]
        # ``preference["origin"]`` is never rewritten here: a previously actual
        # USER_EDIT or qualified CONVERSATION origin is preserved byte-for-byte
        # from the validated canonical preimage.
        evidence = list(decision_data["evidence"])
        if evidence_entry not in evidence:
            if len(evidence) + 1 > MAX_EVIDENCE:
                raise KnowledgeRecipeError("LIMIT_EXCEEDED")
            evidence.append(evidence_entry)
        decision_data["answer"] = value
        decision_data["decided_by"] = actor_ref
        decision_data["decided_at"] = decision_date
        decision_data["evidence"] = evidence
        preference["value"] = value
        preference["last_edit"] = {
            "actor_ref": actor_ref,
            "request_sha256": fingerprint,
        }
        decision_data["project_preference"] = preference
        text = _serialize_record(decision_data, decision_body)
        decision_post = {
            "path": f"{DECISIONS_DIR}/DEC-{decision_key}.md",
            "content_utf8": text,
            "content_sha256": _sha256_hex(text.encode("utf-8")),
            "expected_preimage_sha256": decision_sha256,
        }
        ws_data["decisions"] = decisions

    if len(decision_post["content_utf8"].encode("utf-8")) > MAX_DECISION_BYTES:
        raise KnowledgeRecipeError("LIMIT_EXCEEDED")
    ws_post = _ws_postimage(ws_key, ws_data, ws_body, ws_sha256)
    return _recipe_envelope(
        action=ACTION_PREFERENCE_SET,
        work_ref=work_ref,
        request_id=validated["request_id"],
        fingerprint=fingerprint,
        captured_commit=captured_commit,
        permission_binding_digest=permission_binding_digest,
        postimages=[decision_post, ws_post],
    )
