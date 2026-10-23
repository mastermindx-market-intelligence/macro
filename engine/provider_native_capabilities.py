"""Provider Control native-capability registration source (pure, stdlib-only).

Scope (deliberately narrow):

* ``validate_registry`` validates one closed
  ``mastermind.provider_native_capability_registry/v1`` document and returns a
  fresh, canonically sorted, normalized copy.
* ``validate_registry_transition`` validates ``current`` as the lawful
  successor of ``previous`` under the generation/state machine and returns a
  fresh normalized ``current``.
* ``registration_export`` derives the deterministic
  ``mastermind.provider_native_capability_registration/v1`` export receipt for
  exactly one existing source row selected by the caller.

Out of scope (and intentionally absent): persistence, schedulers, workers,
account/quota databases, admission, quota math, network, filesystem access,
credentials, hosts, principals and paths.  This module is native
*registration* source only; it preserves ``provider_capacity.v1`` and all of
its semantics untouched.  The MiniMax API-key *kind* here is source vocabulary
of the already-reviewed finite Claude-compatible harness -- never credential
content and never an auth authority.

Failure discipline: every refusal raises :class:`NativeCapabilityError` (a
``ValueError``) carrying a bounded machine-readable ``code``; the exception
text is exactly that code, so no input content can leak through ``str()`` or
``repr()``.  Validation fails closed on bool-as-int, extra keys, duplicate
ids, malformed types, raw identity/secret fields, generation
removal/rollback/reuse, and resurrection.
"""

from __future__ import annotations

import hashlib
import json
import re

__all__ = [
    "NativeCapabilityError",
    "ERROR_CODES",
    "REGISTRY_SCHEMA",
    "REGISTRATION_EXPORT_SCHEMA",
    "OWNER_PROGRAM",
    "MAX_CAPABILITIES",
    "MAX_GENERATION",
    "validate_registry",
    "validate_registry_transition",
    "registration_export",
]

REGISTRY_SCHEMA = "mastermind.provider_native_capability_registry/v1"
REGISTRATION_EXPORT_SCHEMA = "mastermind.provider_native_capability_registration/v1"
OWNER_PROGRAM = "shared-ai-provider-control"

MAX_CAPABILITIES = 32
MAX_GENERATION = 2**63 - 1

REGISTRATION_STATE_REGISTERED = "registered"
REGISTRATION_STATE_REVOKED = "revoked"

PROVIDER_CLAUDE = "claude"
PROVIDER_MINIMAX = "minimax"

BILLING_MODE_SUBSCRIPTION = "subscription"
EXECUTION_SURFACE_NATIVE_CLI = "native_cli"

# Closed provider -> credential-kind pairing.  Claude registers only through
# its attached login; MiniMax registers only through the harness's API-key
# kind (source vocabulary, never credential material).
_PROVIDER_CREDENTIAL_KINDS = {
    PROVIDER_CLAUDE: "attached_login",
    PROVIDER_MINIMAX: "api_key",
}
_BILLING_MODES = frozenset({BILLING_MODE_SUBSCRIPTION})
_EXECUTION_SURFACES = frozenset({EXECUTION_SURFACE_NATIVE_CLI})
_REGISTRATION_STATES = frozenset(
    {REGISTRATION_STATE_REGISTERED, REGISTRATION_STATE_REVOKED}
)

_REGISTRY_TOP_KEYS = frozenset({"schema", "owner_program", "capabilities"})
_CAPABILITY_ROW_KEYS = frozenset(
    {
        "capacity_capability_id",
        "capability_generation",
        "provider",
        "billing_mode",
        "credential_kind",
        "execution_surface",
        "registration_state",
    }
)
# The four fields that make a capability's registration identity; they may
# never change across a transition.
_IDENTITY_KEYS = ("provider", "billing_mode", "credential_kind", "execution_surface")

_CAPABILITY_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_MATERIAL_SOURCE_DIGEST_RE = re.compile(r"\A[0-9a-f]{64}\Z")

# Legacy provider slot naming (the OAuth / Codex / DeepSeek era) is refused as
# a capability id, exactly or as a separator-prefixed stem, so callers can
# never equality-guess a registration slot by provider name.  Capability ids
# are opaque source-issued tokens.
_LEGACY_ID_EXACT = frozenset({"oauth", "codex", "deepseek"})
_LEGACY_ID_STEMS = ("oauth", "codex", "deepseek")
_LEGACY_ID_SEPARATORS = (".", "-", "_")

# Bounded refusal vocabulary.  NativeCapabilityError.code is always a member.
ERROR_CODES = frozenset(
    {
        "invalid_registry_document",
        "unexpected_registry_field",
        "missing_registry_field",
        "invalid_registry_schema",
        "invalid_owner_program",
        "invalid_capabilities",
        "capability_bound_exceeded",
        "duplicate_capability_id",
        "invalid_capability_row",
        "unexpected_capability_field",
        "missing_capability_field",
        "invalid_capability_id",
        "forbidden_capability_id",
        "invalid_capability_generation",
        "invalid_provider",
        "invalid_billing_mode",
        "invalid_credential_kind",
        "provider_credential_mismatch",
        "invalid_execution_surface",
        "invalid_registration_state",
        "missing_previous_registry",
        "missing_current_registry",
        "transition_first_registration_not_registered",
        "transition_capability_removed",
        "transition_identity_changed",
        "transition_registered_generation_changed",
        "transition_revocation_generation_changed",
        "transition_tombstone_generation_changed",
        "transition_generation_rollback",
        "transition_capability_resurrection",
        "transition_new_capability_not_registered",
        "invalid_material_source_digest",
        "unknown_capability_selection",
    }
)


class NativeCapabilityError(ValueError):
    """Fail-closed validation refusal.

    ``code`` is the bounded machine-readable reason (a member of
    :data:`ERROR_CODES`) and the exception text is exactly that code, so no
    input content can leak through ``str()``/``repr()``.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _refuse(code: str) -> "NativeCapabilityError":
    return NativeCapabilityError(code)


def _validate_capability_id(value: object) -> str:
    """Validate one opaque safe-token capability id."""
    if not isinstance(value, str) or not _CAPABILITY_ID_RE.match(value):
        raise _refuse("invalid_capability_id")
    lowered = value.lower()
    if lowered in _LEGACY_ID_EXACT:
        raise _refuse("forbidden_capability_id")
    for stem in _LEGACY_ID_STEMS:
        for separator in _LEGACY_ID_SEPARATORS:
            if lowered.startswith(stem + separator):
                raise _refuse("forbidden_capability_id")
    return value


def _validate_generation(value: object) -> int:
    """Validate one exact positive generation int (bool refused)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise _refuse("invalid_capability_generation")
    if value < 1 or value > MAX_GENERATION:
        raise _refuse("invalid_capability_generation")
    return value


def _validate_capability_row(raw_row: object) -> dict:
    """Validate one closed capability row and return a fresh normalized row."""
    if not isinstance(raw_row, dict):
        raise _refuse("invalid_capability_row")
    row_keys = set(raw_row)
    if not row_keys <= _CAPABILITY_ROW_KEYS:
        # Extra fields (host, principal, worker, path, quota, secret, ...)
        # are refused outright; the row schema is closed.
        raise _refuse("unexpected_capability_field")
    if not row_keys >= _CAPABILITY_ROW_KEYS:
        raise _refuse("missing_capability_field")

    capability_id = _validate_capability_id(raw_row["capacity_capability_id"])
    generation = _validate_generation(raw_row["capability_generation"])

    provider = raw_row["provider"]
    if not isinstance(provider, str) or provider not in _PROVIDER_CREDENTIAL_KINDS:
        raise _refuse("invalid_provider")

    billing_mode = raw_row["billing_mode"]
    if not isinstance(billing_mode, str) or billing_mode not in _BILLING_MODES:
        raise _refuse("invalid_billing_mode")

    credential_kind = raw_row["credential_kind"]
    if not isinstance(credential_kind, str):
        raise _refuse("invalid_credential_kind")
    if credential_kind != _PROVIDER_CREDENTIAL_KINDS[provider]:
        raise _refuse("provider_credential_mismatch")

    execution_surface = raw_row["execution_surface"]
    if (
        not isinstance(execution_surface, str)
        or execution_surface not in _EXECUTION_SURFACES
    ):
        raise _refuse("invalid_execution_surface")

    state = raw_row["registration_state"]
    if not isinstance(state, str) or state not in _REGISTRATION_STATES:
        raise _refuse("invalid_registration_state")

    return {
        "capacity_capability_id": capability_id,
        "capability_generation": generation,
        "provider": provider,
        "billing_mode": billing_mode,
        "credential_kind": credential_kind,
        "execution_surface": execution_surface,
        "registration_state": state,
    }


def validate_registry(document: object) -> dict:
    """Validate one registry document; return a fresh normalized copy.

    The returned mapping is a new object with new row dicts (the input is
    never mutated and never aliased) and ``capabilities`` is sorted
    canonically by ``capacity_capability_id``.
    """
    if not isinstance(document, dict):
        raise _refuse("invalid_registry_document")
    top_keys = set(document)
    if not top_keys <= _REGISTRY_TOP_KEYS:
        raise _refuse("unexpected_registry_field")
    if not top_keys >= _REGISTRY_TOP_KEYS:
        raise _refuse("missing_registry_field")

    if document["schema"] != REGISTRY_SCHEMA:
        raise _refuse("invalid_registry_schema")
    if document["owner_program"] != OWNER_PROGRAM:
        raise _refuse("invalid_owner_program")

    capabilities = document["capabilities"]
    if not isinstance(capabilities, list):
        raise _refuse("invalid_capabilities")
    if len(capabilities) > MAX_CAPABILITIES:
        raise _refuse("capability_bound_exceeded")

    seen: set[str] = set()
    rows = []
    for raw_row in capabilities:
        row = _validate_capability_row(raw_row)
        capability_id = row["capacity_capability_id"]
        if capability_id in seen:
            raise _refuse("duplicate_capability_id")
        seen.add(capability_id)
        rows.append(row)
    rows.sort(key=lambda row: row["capacity_capability_id"])

    return {
        "schema": REGISTRY_SCHEMA,
        "owner_program": OWNER_PROGRAM,
        "capabilities": rows,
    }


def validate_registry_transition(previous: object, current: object) -> dict:
    """Validate ``current`` as the lawful successor of ``previous``.

    Returns a fresh normalized ``current``.  Rules:

    * An absent on-disk registry is supplied explicitly by the owner as an
      empty registry document; this function never infers it from a read
      error and refuses ``None``.
    * First registration (empty ``previous``): every row must be ``registered``.
    * The existing domain cannot disappear and can never change its
      provider/billing_mode/credential_kind/execution_surface identity.
    * ``registered(g)`` -> ``registered(g)`` or ``revoked(g)`` only.
    * ``revoked(g)`` -> ``revoked(g)`` or ``registered(g2 > g)``; never a
      same-generation resurrection, never an incrementing tombstone.
    * A capability new to the transition may only enter as ``registered``.
    """
    if previous is None:
        raise _refuse("missing_previous_registry")
    if current is None:
        raise _refuse("missing_current_registry")

    previous_registry = validate_registry(previous)
    current_registry = validate_registry(current)

    previous_rows = {
        row["capacity_capability_id"]: row for row in previous_registry["capabilities"]
    }
    current_rows = {
        row["capacity_capability_id"]: row for row in current_registry["capabilities"]
    }

    if not previous_rows:
        # First registration: everything must start registered.
        for row in current_registry["capabilities"]:
            if row["registration_state"] != REGISTRATION_STATE_REGISTERED:
                raise _refuse("transition_first_registration_not_registered")
        return current_registry

    for capability_id, before in previous_rows.items():
        row = current_rows.get(capability_id)
        if row is None:
            raise _refuse("transition_capability_removed")
        for key in _IDENTITY_KEYS:
            if row[key] != before[key]:
                raise _refuse("transition_identity_changed")

        previous_generation = before["capability_generation"]
        previous_state = before["registration_state"]
        current_generation = row["capability_generation"]
        current_state = row["registration_state"]

        if previous_state == REGISTRATION_STATE_REGISTERED:
            if current_state == REGISTRATION_STATE_REGISTERED:
                if current_generation != previous_generation:
                    if current_generation < previous_generation:
                        raise _refuse("transition_generation_rollback")
                    raise _refuse("transition_registered_generation_changed")
            else:  # registered(g) -> revoked(g) only
                if current_generation != previous_generation:
                    if current_generation < previous_generation:
                        raise _refuse("transition_generation_rollback")
                    raise _refuse("transition_revocation_generation_changed")
        else:  # previous is a revoked tombstone
            if current_state == REGISTRATION_STATE_REVOKED:
                if current_generation != previous_generation:
                    raise _refuse("transition_tombstone_generation_changed")
            else:  # revival requires a strictly higher generation
                if current_generation < previous_generation:
                    raise _refuse("transition_generation_rollback")
                if current_generation == previous_generation:
                    raise _refuse("transition_capability_resurrection")

    for capability_id, row in current_rows.items():
        if capability_id not in previous_rows:
            if row["registration_state"] != REGISTRATION_STATE_REGISTERED:
                raise _refuse("transition_new_capability_not_registered")

    return current_registry


def _canonical_receipt_digest(mapping: dict) -> str:
    """SHA-256 over UTF-8 canonical JSON of ``mapping``."""
    payload = json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def registration_export(
    registry: object,
    capacity_capability_id: object,
    *,
    material_source_digest: object,
) -> dict:
    """Deterministically export one existing source row's registration.

    The caller selects only an existing row, by id; the registration state
    and generation always come from the registry row and can never be chosen
    (or overridden) by the caller.  A revoked row exports as revoked.
    ``material_source_digest`` must be exact lowercase 64-hex.
    """
    normalized = validate_registry(registry)
    capability_id = _validate_capability_id(capacity_capability_id)

    if not isinstance(material_source_digest, str) or not _MATERIAL_SOURCE_DIGEST_RE.match(
        material_source_digest
    ):
        raise _refuse("invalid_material_source_digest")

    selected = None
    for row in normalized["capabilities"]:
        if row["capacity_capability_id"] == capability_id:
            selected = row
            break
    if selected is None:
        raise _refuse("unknown_capability_selection")

    export = {
        "schema": REGISTRATION_EXPORT_SCHEMA,
        "capacity_capability_id": selected["capacity_capability_id"],
        "capability_generation": selected["capability_generation"],
        "provider": selected["provider"],
        "billing_mode": selected["billing_mode"],
        "credential_kind": selected["credential_kind"],
        "execution_surface": selected["execution_surface"],
        "registration_state": selected["registration_state"],
        "material_source_digest": material_source_digest,
    }
    export["registration_receipt_digest"] = _canonical_receipt_digest(export)
    return export
