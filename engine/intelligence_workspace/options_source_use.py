"""Server-owned source-use decision adapter for Options Matrix display/export.

WHAT THIS IS.  The composed consumer
(:func:`engine.intelligence_workspace.options_use.resolve_authorized_option_selection`)
calls a ``source_use_decision`` callback and accepts its closed seven-key
response as the source-use record for one display/export of one already
verified Matrix snapshot.  This module is one TRUSTED SERVER implementation of
that callback.  It joins THREE independently captured server records — the
dataset contract row in a :class:`lib.dataos.registry.Registry`, the policy
evidence document that the row's ``rights:`` block points at, and the trusted
backend's :class:`ServerUseContext` for this exact request — and answers
``allowed`` only when the exact request of THIS call sits inside all three.

WHAT THIS IS NOT.

* Not a rights authority and not a grant.  It writes no registry row, mints no
  policy, creates no entitlement, and cannot authenticate anybody.  The
  composed resolver's auth/entitlement callbacks stay separate and run first;
  nothing here substitutes for them.
* Not a browser-facing API.  Every input is injected by the server: the
  registry, the dataset id, the trusted expected evidence digest, the trusted
  registry revision, the trusted expected source family, the trusted
  use-context resolver and the evaluation clock.  A dict that arrived from a
  browser, or the request echoed back at itself, is never authority here — the
  only accepted request shape is the server-built frozen
  :class:`~engine.intelligence_workspace.options_use.OptionUseRequest`, and the
  only accepted use context is the server resolver's own frozen
  :class:`ServerUseContext` for THIS exact request.
* Not a store.  No decision, binding, context or policy is cached, persisted
  or replayed; every call re-reads the contract and the evidence bytes,
  re-invokes the use-context resolver and re-reads the evaluation clock.  A
  decision observed once authorizes nothing later.

USE CONTEXT (what actually gets done, to whom, through what).  This module
NEVER infers a right, an output basis or a delivery channel from the action
verb: ``display`` and ``export`` are only labels, and nothing about them
implies ``internal_computation`` or ``redistribution``, raw or derived bytes,
or any channel.  Instead the backend's mandatory ``use_context_for_request``
callable — an independently trusted server snapshot/handler resolver — is
invoked ONCE per decision with the fresh server request and must return the
exact type :class:`ServerUseContext`, describing the use the server is about
to perform from the ACTUAL intended output, recipients, channel and customer.
Its ``binding`` must equal every field of the request of this call (all
fourteen, including the nonce and both digests).  The context is never
derived from policy values and never accepted from a request parameter or a
browser dict; a missing resolver, a resolver failure or a non-conforming
context refuses (``context_unavailable`` / ``context_invalid`` /
``context_binding_mismatch``).

HONESTY ABOUT PYTHON MECHANICS.  Nothing here authenticates provenance or
enforces server trust by itself.  Frozen (``frozen=True``) dataclasses,
``slots`` and name-mangled private tokens are ordinary Python objects: they
can be constructed or copied by any code with a reference to the class, and
they prove NOTHING about who built them.  The SHA-256 digest pin authenticates
only that the captured bytes are the bytes the operator pinned — it grants no
authority and makes no object "self-proving".  :class:`ServerUseContext`,
:class:`OptionsSourcePolicy` and the private ``_VerifiedEvidence`` token are
construction guards and documentation, not security boundaries.  The trust
lives in the AUDITED SERVER INTEGRATION that injects the registry, the
operator pins and a genuine resolver, and in nothing else.  None of these
objects may be exposed as request parameters or accepted from callers.

TRUST BOUNDARY.  Only verified evidence may become an
:class:`OptionsSourcePolicy`, and verified evidence can only be minted by
:func:`load_options_source_policy` after (a) every right the trusted context
requires is ``granted`` on the captured row and points at ONE shared, lawful
:data:`lib.dataos.registry.EVIDENCE_ROOTS` evidence file, (b) that file is
read under the real evidence root by walking directory file descriptors with
``O_NOFOLLOW``/``O_DIRECTORY`` from the root (no ``..``/``.`` component, no
symlink substitution at any depth, bounded regular file only), (c) the exact
captured bytes hash to the operator's trusted expected digest, and (d) the
parsed record joins the captured contract row, the trusted context and the
request field by field.  A pointer whose SYNTAX is valid proves nothing by
itself — the digest pin and the joins are the evidence.

FAILURE MODEL.  Policy and evidence refusals raise :class:`SourceUseRefused`
with a stable code and release no value. Invalid server configuration may
instead raise a Python configuration/type exception; the composed consumer
maps either callback exception to ``rights_unavailable``. A missing, stale, revoked, ambiguous, mutated or
mismatched record never degrades to a permissive default, never invents a
policy id/revision/family (not even for an ``unavailable`` answer), and inside
the composed resolver surfaces as the existing ``rights_unavailable``
callback-error path.  An affirmative, in-scope, current policy that explicitly
sets ``allowed: false`` for the action is the only producer of a ``denied``
response; an action the policy does not mention at all is a refusal, never a
wildcard.

The native rights stay independent.  Only the rights the trusted context
names are consulted, each must independently be ``granted`` and evidenced by
the same verified bytes, and no single granted flag ever substitutes for
another (K01.02, R00.02).  ``purchase_access`` has no special role either
way: it is consulted only when the context explicitly requires it, and a
purchased subscription implies nothing else.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, fields as dataclass_fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# The evidence-pointer law is imported (not re-typed) from the registry: the
# row's `granted` rights are only as lawful as the registry's own R00.02
# definition, and two definitions of "lawful pointer" would drift apart.
from lib.dataos.registry import (
    DatasetStatus,
    Layer,
    Registry,
    RIGHTS_KEYS,
    _is_evidence_pointer,
    validate_registry,
)

# Scalar/instant validation is reused from the sibling consumer rather than
# re-typed here: one bounded-scalar law and one strict-instant law, so this
# adapter and its consumer can never drift apart on what a valid scalar or
# timestamp is.
from .options_use import OptionUseRequest, _is_valid_scalar, _parse_instant

__all__ = [
    "SourceUseRefused",
    "ServerUseContext",
    "OptionsSourcePolicy",
    "ActionUseScope",
    "OptionsSourceUseBackend",
    "resolve_options_source_use_decision",
    "load_options_source_policy",
    "MATRIX_OWNER",
    "MATRIX_SCHEMA",
]

#: The only request owner/schema this adapter serves.  Both are fixed Matrix
#: constants of the composed consumer's request shape; they identify the
#: REQUEST vocabulary only.  They are deliberately NOT the policy's source
#: family: a genuine source family arrives from the trusted context, the
#: policy evidence and the operator pin; this module does not infer one from the owner.
MATRIX_OWNER = "options_structure.matrix"
MATRIX_SCHEMA = "options_structure.matrix/v1"

#: The only action verbs the composed consumer sends.  A verb carries NO
#: right, output basis or channel with it: all of that arrives only in the
#: trusted :class:`ServerUseContext` and must be licensed by the policy scope.
_ACTION_VERBS = ("display", "export")

_RECIPIENT_VALUES = ("authenticated_customer", "internal_customer")
_CUSTOMER_SCOPES = ("named_authenticated_principal",)
_OUTPUT_VALUES = ("raw", "derived")

#: Policy file key sets.  Closed: an extra key is as dishonest as a missing one,
#: because an extra key is how a future "default_allow" hides in a stale file.
_POLICY_KEYS = frozenset(
    {
        "policy_id",
        "policy_revision",
        "registry_revision",
        "source_family",
        "dataset_id",
        "dataset_version",
        "vendor",
        "state",
        "known_at",
        "effective_from",
        "effective_until",
        "evidence_revision",
        "source_sessions",
        "actions",
    }
)
_ACTION_SCOPE_KEYS = frozenset(
    {
        "allowed",
        "fields",
        "output",
        "channel",
        "recipients",
        "customer_scope",
        "principal_id",
        "principal_issuer",
        "auth_epoch",
        "customer_id",
        "required_rights",
    }
)

_STATE_VALUES = ("active", "revoked")
_MAX_FIELDS = 64
_MAX_RECIPIENTS = 8
_MAX_RIGHTS = 16
_MAX_SOURCE_SESSIONS = 16
_MAX_EVIDENCE_BYTES = 256 * 1024

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_NONCE = re.compile(r"\A[0-9a-f]{32}\Z")

_LAYERS = (Layer.L0_SOURCE, Layer.L1_NORMALIZED)


class SourceUseRefused(ValueError):
    """Every refusal of this adapter.

    ``code`` is a stable lower_snake string (the :mod:
    ``engine.intelligence_workspace.options_use`` idiom).  Details never quote
    evidence contents, policy values or request bytes, and no refusal ever
    fabricates a policy id, revision or family to answer with.
    """

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code


class _VerifiedEvidence:
    """Private construction-guard token.

    ``__init__`` raises, so the only instance that can ever exist is minted by
    :meth:`_mint` inside :func:`_resolve_joined` after the evidence bytes have
    been captured and their digest pinned.  This is a GUARD, not proof: a
    Python token is not unforgeable, object identity authenticates nothing,
    and carrying this token grants no authority.  It only makes it awkward to
    build an :class:`OptionsSourcePolicy` from unvalidated metadata by
    accident.  Verification lives in the digest pin and the audited server
    integration that injected the pins — never in a Python object.
    """

    __slots__ = ()

    def __init__(self) -> None:
        raise TypeError(
            "verified-evidence token is minted only by load_options_source_policy"
        )

    @classmethod
    def _mint(cls) -> "_VerifiedEvidence":
        return object.__new__(cls)


@dataclass(frozen=True)
class ServerUseContext:
    """The trusted server's own record of the use it is about to perform.

    Built by the backend's ``use_context_for_request`` resolver — an
    independently trusted server snapshot/handler resolver — from the ACTUAL
    intended output, recipients, channel, dataset and customer of THIS
    request.  Never derived from policy values, never accepted from a request
    parameter, never a browser dict.

    THIS OBJECT AUTHENTICATES NOTHING.  ``frozen=True`` is ordinary Python: a
    frozen dataclass can be constructed by any code holding the class, and it
    does not enforce server trust or prove provenance.  It is accepted here
    only because the AUDITED SERVER INTEGRATION injected the resolver that
    produced it.  ``binding`` must be the exact :class:`OptionUseRequest` of
    this call; the adapter re-checks every field (type and value) itself.
    """

    binding: OptionUseRequest
    dataset_id: str
    vendor: str
    source_family: str
    fields: tuple[str, ...]
    output: str
    channel: str
    recipients: tuple[str, ...]
    customer_id: str
    required_rights: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActionUseScope:
    """What one policy says about ONE action, already shape-validated.

    ``fields`` are the only output fields the policy names for the action, and
    every one of them is checked against the captured contract's declared
    schema before any allow — a policy may not invent a column the dataset row
    does not declare.  ``principal_id``/``principal_issuer``/``auth_epoch``/
    ``customer_id`` name the exact principal, issuer, auth epoch and customer
    this scope covers; ``required_rights`` maps each native right this action
    needs to a bounded nonempty rationale for why it applies.  Nothing here is
    inferred from the action verb.
    """

    allowed: bool
    fields: tuple[str, ...]
    output: str
    channel: str
    recipients: tuple[str, ...]
    customer_scope: str
    principal_id: str
    principal_issuer: str
    auth_epoch: str
    customer_id: str
    required_rights: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class OptionsSourcePolicy:
    """Validated source-use policy metadata — immutable captured state.

    Every field was read from evidence bytes whose SHA-256 equals the
    operator-pinned digest, captured under a lawful shared evidence pointer of
    the captured contract row.  Construction requires the private guard token;
    there is deliberately no dict-convenience constructor, because a policy
    assembled from arbitrary data is precisely the thing this module exists to
    refuse.  Immutability is bookkeeping, not authentication: this object does
    not certify its own provenance, and holding one grants no authority.
    """

    policy_id: str
    policy_revision: str
    registry_revision: str
    source_family: str
    dataset_id: str
    dataset_version: str
    vendor: str
    state: str
    known_at: datetime
    effective_from: datetime
    effective_until: datetime
    evidence_revision: str
    evidence_sha256: str
    evidence_pointer: str
    source_sessions: tuple[str, ...] | None
    scopes: tuple[tuple[str, ActionUseScope], ...]

    def __init__(
        self,
        *,
        token: _VerifiedEvidence,
        policy_id: str,
        policy_revision: str,
        registry_revision: str,
        source_family: str,
        dataset_id: str,
        dataset_version: str,
        vendor: str,
        state: str,
        known_at: datetime,
        effective_from: datetime,
        effective_until: datetime,
        evidence_revision: str,
        evidence_sha256: str,
        evidence_pointer: str,
        source_sessions: tuple[str, ...] | None,
        scopes: tuple[tuple[str, ActionUseScope], ...],
    ) -> None:
        if not isinstance(token, _VerifiedEvidence):
            raise TypeError("OptionsSourcePolicy requires verified evidence")
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "policy_revision", policy_revision)
        object.__setattr__(self, "registry_revision", registry_revision)
        object.__setattr__(self, "source_family", source_family)
        object.__setattr__(self, "dataset_id", dataset_id)
        object.__setattr__(self, "dataset_version", dataset_version)
        object.__setattr__(self, "vendor", vendor)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "known_at", known_at)
        object.__setattr__(self, "effective_from", effective_from)
        object.__setattr__(self, "effective_until", effective_until)
        object.__setattr__(self, "evidence_revision", evidence_revision)
        object.__setattr__(self, "evidence_sha256", evidence_sha256)
        object.__setattr__(self, "evidence_pointer", evidence_pointer)
        object.__setattr__(self, "source_sessions", source_sessions)
        object.__setattr__(self, "scopes", tuple(scopes))

    def scope_for(self, action: str) -> ActionUseScope | None:
        """The validated scope for *action*, or ``None`` when unmentioned.

        ``None`` is honest absence: the policy does not speak for that action,
        and the caller must refuse rather than default it.
        """
        for name, scope in self.scopes:
            if name == action:
                return scope
        return None


@dataclass(frozen=True)
class OptionsSourceUseBackend:
    """One trusted server binding of the injected inputs, callable as a callback.

    ``registry`` is the loaded :class:`Registry`; ``dataset_id`` names the one
    Matrix source row this backend answers for; ``expected_evidence_sha256`` is
    the operator's trusted digest of the exact policy bytes (the pin that makes
    a re-written evidence file refuse); ``expected_registry_revision`` is the
    operator's trusted registry revision the policy must have been authored
    against; ``expected_source_family`` is the operator's trusted source
    family the policy and the use context must both name. Family values are
    opaque metadata: equality to ``MATRIX_OWNER`` is neither prohibited nor
    evidence of provenance. ``use_context_for_request`` is the
    mandatory trusted server resolver that builds the :class:`ServerUseContext`
    for one fresh request.  All trusted inputs come from the server's own
    audited configuration — never from the request, the browser, or the
    evidence file itself.
    """

    registry: Registry
    dataset_id: str
    expected_evidence_sha256: str
    expected_registry_revision: str
    expected_source_family: str
    use_context_for_request: Callable[[OptionUseRequest], ServerUseContext] | None = None
    evidence_root: str | Path | None = None
    clock: Callable[[], datetime] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.registry, Registry):
            raise ValueError("registry must be a lib.dataos.registry.Registry")
        if not _is_valid_scalar(self.dataset_id):
            raise ValueError("dataset_id must be a nonblank bounded string")
        for name in ("expected_evidence_sha256", "expected_registry_revision", "expected_source_family"):
            value = getattr(self, name)
            if not _is_valid_scalar(value):
                raise ValueError(f"{name} must be a nonblank bounded string")
        if not _SHA256.match(self.expected_evidence_sha256):
            raise ValueError("expected_evidence_sha256 must be 64 lowercase hex")
        if self.use_context_for_request is not None and not callable(self.use_context_for_request):
            raise ValueError("use_context_for_request must be callable or None")
        if self.clock is not None and not callable(self.clock):
            raise ValueError("clock must be callable or None")

    def decision(self, request: OptionUseRequest) -> dict[str, Any]:
        """The ``source_use_decision`` callback body: one fresh decision."""
        return resolve_options_source_use_decision(
            request,
            registry=self.registry,
            dataset_id=self.dataset_id,
            expected_evidence_sha256=self.expected_evidence_sha256,
            expected_registry_revision=self.expected_registry_revision,
            expected_source_family=self.expected_source_family,
            use_context_for_request=self.use_context_for_request,
            evidence_root=self.evidence_root,
            clock=self.clock,
        )


def _default_root() -> Path:
    """The repository root this module is installed in (engine/x/y → root)."""
    return Path(__file__).resolve().parents[2]


def _format_instant(moment: datetime) -> str:
    """Strict RFC3339 UTC instant with a ``Z`` suffix (consumer-parseable)."""
    utc = moment.astimezone(timezone.utc)
    return utc.isoformat().replace("+00:00", "Z")


def _is_digest(value: object) -> bool:
    return type(value) is str and _SHA256.match(value) is not None


def _requests_identical(left: Any, right: Any) -> bool:
    """True only when both are OptionUseRequest with every field same TYPE+value.

    A dataclass ``==`` would call ``True == 1`` equal; the exact per-field type
    check is what makes the context's binding the request of THIS call.
    """
    if type(left) is not OptionUseRequest or type(right) is not OptionUseRequest:
        return False
    for field in dataclass_fields(OptionUseRequest):
        a = getattr(left, field.name)
        b = getattr(right, field.name)
        if type(a) is not type(b) or a != b:
            return False
    return True


def _validate_context(context: Any, request: OptionUseRequest) -> ServerUseContext:
    """Accept only a well-shaped ServerUseContext bound to THIS exact request."""
    if type(context) is not ServerUseContext:
        raise SourceUseRefused("context_invalid", "use context must be the frozen ServerUseContext")
    if not _requests_identical(context.binding, request):
        raise SourceUseRefused("context_binding_mismatch", "context binding is not this exact request")
    for name in ("dataset_id", "vendor", "source_family", "customer_id", "channel"):
        if not _is_valid_scalar(getattr(context, name)):
            raise SourceUseRefused("context_invalid", f"context {name} is not a bounded nonblank scalar")
    for name, bound in (
        ("fields", _MAX_FIELDS),
        ("recipients", _MAX_RECIPIENTS),
        ("required_rights", _MAX_RIGHTS),
    ):
        value = getattr(context, name)
        if (
            type(value) is not tuple
            or not value
            or len(value) > bound
            or any(not _is_valid_scalar(item) for item in value)
            or len(set(value)) != len(value)
        ):
            raise SourceUseRefused("context_invalid", f"context {name} must be unique bounded scalars")
    if context.output not in _OUTPUT_VALUES:
        raise SourceUseRefused("context_invalid", "context output is not raw/derived")
    if any(r not in _RECIPIENT_VALUES for r in context.recipients):
        raise SourceUseRefused("context_invalid", "context recipients are not the closed set")
    if any(r not in RIGHTS_KEYS for r in context.required_rights):
        raise SourceUseRefused("context_invalid", "context names a right outside the native vocabulary")
    if context.customer_id != request.principal_id:
        raise SourceUseRefused("context_invalid", "context customer is not the named request principal")
    return context


def _read_captured_bytes(root: Path, body: str) -> bytes:
    """Read the exact evidence bytes under *root*, refusing every escape.

    Lawful: relative ``root/first/rest`` with no ``.``/``..`` component, no
    backslash or control byte, opened by walking DIRECTORY FILE DESCRIPTORS
    from the evidence root — every component is opened ``O_NOFOLLOW`` (and
    ``O_DIRECTORY`` for intermediates), so no symlink at any depth can be
    substituted between a check and the open — ending at a bounded REGULAR
    file.  Each failure is a distinct refusal code; none falls back to a
    permissive read.
    """
    parts = body.split("/")
    for part in parts:
        if part in (".", "..") or "\\" in part or "\x00" in part or not part.strip():
            raise SourceUseRefused("evidence_path_forbidden", "path component is not a plain name")
    try:
        root_fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        raise SourceUseRefused("evidence_root_invalid", "evidence root is not a directory") from None
    try:
        dir_fd = root_fd
        try:
            for part in parts[:-1]:
                try:
                    info = os.stat(part, dir_fd=dir_fd, follow_symlinks=False)
                except OSError:
                    raise SourceUseRefused("evidence_unreadable", "evidence directory is missing") from None
                if stat.S_ISLNK(info.st_mode):
                    raise SourceUseRefused(
                        "evidence_path_forbidden", "symlinked directory in evidence path"
                    )
                try:
                    next_fd = os.open(
                        part, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=dir_fd
                    )
                except OSError:
                    # Covers a link swapped in after the lstat above: still a
                    # refusal, only its label could differ.  The O_NOFOLLOW
                    # open, not the lstat, is the boundary.
                    raise SourceUseRefused(
                        "evidence_path_forbidden", "symlinked directory in evidence path"
                    ) from None
                if dir_fd != root_fd:
                    os.close(dir_fd)
                dir_fd = next_fd
            try:
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise SourceUseRefused("evidence_path_forbidden", "symlinked evidence file") from None
                raise SourceUseRefused("evidence_unreadable", "evidence file is unreadable") from None
        finally:
            if dir_fd != root_fd:
                os.close(dir_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise SourceUseRefused("evidence_path_forbidden", "evidence is not a regular file")
            if info.st_size > _MAX_EVIDENCE_BYTES:
                raise SourceUseRefused("evidence_unbounded", "evidence file exceeds the bounded size")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_EVIDENCE_BYTES:
                    raise SourceUseRefused("evidence_unbounded", "evidence file exceeds the bounded size")
                chunks.append(chunk)
        except OSError:
            raise SourceUseRefused("evidence_unreadable", "evidence file is unreadable") from None
        finally:
            os.close(fd)
    finally:
        os.close(root_fd)
    return b"".join(chunks)


def _load_policy_record(raw: bytes) -> dict[str, Any]:
    """Strict JSON capture: no duplicate keys, no NaN/Infinity, closed shape."""
    def unique(pairs):
        out: dict[Any, Any] = {}
        for key, value in pairs:
            if key in out:
                raise SourceUseRefused("evidence_invalid", "duplicate key in policy evidence")
            out[key] = value
        return out

    def nonfinite(_):
        raise SourceUseRefused("evidence_invalid", "nonfinite constant in policy evidence")

    try:
        record = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite
        )
    except SourceUseRefused:
        raise
    except (UnicodeDecodeError, ValueError):
        raise SourceUseRefused("evidence_invalid", "policy evidence is not strict JSON") from None
    if type(record) is not dict:
        raise SourceUseRefused("evidence_invalid", "policy evidence is not a JSON object")
    if set(record) != _POLICY_KEYS:
        raise SourceUseRefused("evidence_invalid", "policy evidence keys are not the closed set")
    return record


def _parse_action_scope(action: str, block: object) -> ActionUseScope:
    if type(block) is not dict or set(block) != _ACTION_SCOPE_KEYS:
        raise SourceUseRefused("evidence_invalid", "action scope keys are not the closed set")
    allowed = block["allowed"]
    if type(allowed) is not bool:
        raise SourceUseRefused("evidence_invalid", "action allowed flag must be a bool")
    fields = block["fields"]
    if (
        type(fields) is not list
        or not fields
        or len(fields) > _MAX_FIELDS
        or any(not _is_valid_scalar(f) for f in fields)
        or len(set(fields)) != len(fields)
    ):
        raise SourceUseRefused("evidence_invalid", "action fields must be unique bounded scalars")
    output = block["output"]
    if output not in _OUTPUT_VALUES:
        raise SourceUseRefused("evidence_invalid", "action output is not raw/derived")
    channel = block["channel"]
    if not _is_valid_scalar(channel):
        raise SourceUseRefused("evidence_invalid", "action channel is invalid")
    recipients = block["recipients"]
    if (
        type(recipients) is not list
        or not recipients
        or len(recipients) > _MAX_RECIPIENTS
        or any(r not in _RECIPIENT_VALUES for r in recipients)
        or len(set(recipients)) != len(recipients)
    ):
        raise SourceUseRefused("evidence_invalid", "action recipients are not the closed set")
    customer_scope = block["customer_scope"]
    if customer_scope not in _CUSTOMER_SCOPES:
        raise SourceUseRefused("evidence_invalid", "action customer_scope is not the closed set")
    identity = {}
    for name in ("principal_id", "principal_issuer", "auth_epoch", "customer_id"):
        value = block[name]
        if not _is_valid_scalar(value):
            raise SourceUseRefused("evidence_invalid", f"action {name} is not a bounded nonblank scalar")
        identity[name] = value
    required = block["required_rights"]
    if (
        type(required) is not dict
        or not required
        or len(required) > _MAX_RIGHTS
        or any(not _is_valid_scalar(right) for right in required)
        or any(not _is_valid_scalar(why) for why in required.values())
    ):
        raise SourceUseRefused(
            "evidence_invalid",
            "action required_rights must map native rights to nonempty rationales",
        )
    return ActionUseScope(
        allowed=allowed,
        fields=tuple(fields),
        output=output,
        channel=channel,
        recipients=tuple(recipients),
        customer_scope=customer_scope,
        principal_id=identity["principal_id"],
        principal_issuer=identity["principal_issuer"],
        auth_epoch=identity["auth_epoch"],
        customer_id=identity["customer_id"],
        required_rights=tuple(sorted((str(k), str(v)) for k, v in required.items())),
    )


def _validate_request(request: Any) -> OptionUseRequest:
    """Accept only the server-built frozen request, with sane field formats."""
    if type(request) is not OptionUseRequest:
        raise SourceUseRefused("request_invalid", "request must be the frozen OptionUseRequest")
    if not _NONCE.match(request.request_id):
        raise SourceUseRefused("request_invalid", "request_id must be a fresh uuid4 nonce")
    if request.owner != MATRIX_OWNER or request.schema != MATRIX_SCHEMA:
        raise SourceUseRefused("request_invalid", "owner/schema is outside this adapter's family")
    for name in ("principal_id", "principal_issuer", "auth_epoch", "vendor", "root", "underlying_id"):
        if not _is_valid_scalar(getattr(request, name)):
            raise SourceUseRefused("request_invalid", f"{name} is not a bounded nonblank scalar")
    if request.session is not None and not _is_valid_scalar(request.session):
        raise SourceUseRefused("request_invalid", "session must be None or a bounded nonblank scalar")
    if type(request.byte_length) is not int or not 0 < request.byte_length <= 2**33:
        raise SourceUseRefused("request_invalid", "byte_length must be a positive bounded int")
    if not _is_digest(request.sha256) or not _is_digest(request.selection_sha256):
        raise SourceUseRefused("request_invalid", "snapshot/selection digests must be 64 hex")
    if request.action not in _ACTION_VERBS:
        raise SourceUseRefused("request_invalid", "action must be display or export")
    return request


def _resolve_contract(
    registry: Registry, dataset_id: str, vendor: str
) -> Any:
    """Resolve exactly one produced source row, never last-wins, never a default."""
    if not isinstance(registry, Registry):
        raise SourceUseRefused("trust_invalid", "registry is not a Registry")
    rows = [c for c in registry.all() if c.dataset_id == dataset_id]
    if not rows:
        raise SourceUseRefused("dataset_missing", "no registry row for the dataset")
    if len(rows) > 1:
        # last-wins get() would silently elect one duplicate; ambiguity refuses.
        raise SourceUseRefused("dataset_ambiguous", "duplicate dataset_id rows in the registry")
    contract = rows[0]
    if contract.status is not DatasetStatus.PRODUCED:
        raise SourceUseRefused("source_not_produced", "dataset row is not PRODUCED")
    if contract.layer not in _LAYERS:
        raise SourceUseRefused("source_layer_unsupported", "dataset row is not a source layer")
    if not _is_valid_scalar(contract.vendor) or contract.vendor != vendor:
        raise SourceUseRefused("dataset_vendor_mismatch", "dataset row vendor does not match the request")
    violations = validate_registry(Registry([contract]))
    if violations:
        # from_mapping coerces leniently by design; the row is validated for
        # real before anything is granted on it.
        raise SourceUseRefused("registry_contract_invalid", "dataset row fails registry validation")
    return contract


def _shared_evidence_pointer(contract: Any, required_rights: tuple[str, ...]) -> tuple[str, str]:
    """The ONE evidence pointer every required right must independently share.

    Each required right must be ``granted`` on the captured row and carry its
    own lawful pointer at the same evidence file — one file, several
    independent grants.  No right is inferred from the action or from another
    right, and no single granted flag substitutes for another.  Returns the
    full pointer of the first required right and the shared path body.
    """
    rights = contract.rights if type(contract.rights) is dict else {}
    evidence = rights.get("evidence")
    evidence = evidence if type(evidence) is dict else {}
    bodies = []
    for right in required_rights:
        if right not in RIGHTS_KEYS or rights.get(right) != "granted":
            raise SourceUseRefused("right_not_granted", "a required native right is not granted")
        pointer = evidence.get(right)
        if not isinstance(pointer, str) or not _is_evidence_pointer(pointer):
            raise SourceUseRefused("evidence_pointer_invalid", "evidence pointer is not a lawful form")
        body = pointer.split("#", 1)[0].strip()
        if body.startswith(("DEC:", "DSC:")):
            # A decision key is a pointer into the decisions registry, which this
            # adapter does not hold; approximating it with a path would invent
            # authority.  Refuse instead.
            raise SourceUseRefused("evidence_unresolvable", "decision-key evidence cannot be resolved here")
        bodies.append((right, pointer, body))
    unique = {body for _right, _pointer, body in bodies}
    if len(unique) != 1:
        raise SourceUseRefused(
            "evidence_pointer_mismatch", "required rights do not point at one shared evidence file"
        )
    return bodies[0][1], bodies[0][2]


def _resolve_joined(
    request: OptionUseRequest,
    *,
    registry: Registry,
    dataset_id: str,
    expected_evidence_sha256: str,
    expected_registry_revision: str,
    expected_source_family: str,
    use_context_for_request: Callable[[OptionUseRequest], ServerUseContext] | None,
    evidence_root: str | Path | None,
    clock: Callable[[], datetime],
) -> tuple[OptionsSourcePolicy, Any, ServerUseContext, datetime]:
    """Join request + trusted context + captured contract row + captured policy.

    Returns the minted policy, the captured contract, the trusted use context
    and the decision instant.  Any gap raises; nothing is cached between calls.
    """
    request = _validate_request(request)
    if (
        not _is_digest(expected_evidence_sha256)
        or not _is_valid_scalar(expected_registry_revision)
        or not _is_valid_scalar(expected_source_family)
    ):
        raise SourceUseRefused("trust_invalid", "trusted expected digest/revision/family are malformed")
    if not callable(use_context_for_request):
        raise SourceUseRefused("context_unavailable", "no trusted use-context resolver is configured")
    try:
        decided_at = clock()
    except Exception:
        raise SourceUseRefused("clock_invalid", "evaluation clock raised") from None
    if not isinstance(decided_at, datetime) or decided_at.tzinfo is None or (
        decided_at.utcoffset() is None
    ):
        raise SourceUseRefused("clock_invalid", "evaluation clock returned a naive or non-datetime")

    # The trusted server resolver speaks ONCE per decision, for THIS request.
    try:
        context = use_context_for_request(request)
    except SourceUseRefused:
        raise
    except Exception:
        raise SourceUseRefused("context_unavailable", "trusted use-context resolver failed") from None
    context = _validate_context(context, request)

    if context.dataset_id != dataset_id:
        raise SourceUseRefused("context_dataset_mismatch", "context dataset is not this backend's dataset")
    contract = _resolve_contract(registry, dataset_id, request.vendor)
    if context.vendor != contract.vendor:
        raise SourceUseRefused("dataset_vendor_mismatch", "context vendor does not match the dataset row")

    pointer, body = _shared_evidence_pointer(contract, context.required_rights)
    root = Path(evidence_root) if evidence_root is not None else _default_root()
    raw = _read_captured_bytes(root, body)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_evidence_sha256:
        raise SourceUseRefused("evidence_digest_mismatch", "captured evidence digest is not trusted")

    record = _load_policy_record(raw)
    for name in (
        "policy_id", "policy_revision", "registry_revision", "source_family",
        "dataset_id", "dataset_version", "vendor", "state", "evidence_revision",
    ):
        if not _is_valid_scalar(record.get(name)):
            raise SourceUseRefused("evidence_invalid", f"{name} is not a bounded nonblank scalar")
    if (
        record["source_family"] != context.source_family
        or record["source_family"] != expected_source_family
    ):
        raise SourceUseRefused("policy_family_mismatch", "policy family is not the trusted source family")
    if record["dataset_id"] != dataset_id or record["dataset_id"] != contract.dataset_id:
        raise SourceUseRefused("policy_dataset_mismatch", "policy dataset does not match the row")
    if record["vendor"] != contract.vendor:
        raise SourceUseRefused("policy_vendor_mismatch", "policy vendor does not match the row")
    if not _is_valid_scalar(contract.version) or record["dataset_version"] != contract.version:
        raise SourceUseRefused("dataset_version_mismatch", "policy dataset_version does not join the row version")
    if record["registry_revision"] != expected_registry_revision:
        raise SourceUseRefused("registry_revision_mismatch", "policy registry revision is not trusted")
    if record["state"] not in _STATE_VALUES:
        raise SourceUseRefused("evidence_invalid", "policy state is not active/revoked")
    if record["state"] == "revoked":
        raise SourceUseRefused("policy_revoked", "policy evidence is revoked")

    known_at = _parse_instant(record["known_at"])
    if known_at is None:
        raise SourceUseRefused("policy_known_at_invalid", "known_at is not a strict RFC3339 instant")
    if known_at > decided_at:
        # A policy cannot have been known in the future relative to the fresh
        # decision clock; an old snapshot must not smuggle one in either.
        raise SourceUseRefused("policy_known_at_future", "policy claims knowledge after the decision instant")
    effective_from = _parse_instant(record["effective_from"])
    effective_until = _parse_instant(record["effective_until"])
    if effective_from is None or effective_until is None or effective_until < effective_from:
        raise SourceUseRefused("policy_window_invalid", "effective window is not two strict instants")
    if decided_at < effective_from or decided_at >= effective_until:
        raise SourceUseRefused("policy_not_current", "evaluation instant is outside the effective window")

    sessions = record["source_sessions"]
    if sessions is not None:
        if (
            type(sessions) is not list
            or not sessions
            or len(sessions) > _MAX_SOURCE_SESSIONS
            or any(not _is_valid_scalar(s) for s in sessions)
            or len(set(sessions)) != len(sessions)
        ):
            raise SourceUseRefused("evidence_invalid", "source_sessions must be null or unique bounded scalars")
        if request.session is None or request.session not in sessions:
            raise SourceUseRefused("source_session_excluded", "the request source session is not covered")

    actions = record["actions"]
    if type(actions) is not dict or not actions:
        raise SourceUseRefused("evidence_invalid", "actions must be a non-empty mapping")
    unknown = sorted(set(actions) - set(_ACTION_VERBS))
    if unknown:
        raise SourceUseRefused("evidence_invalid", "actions name unknown verbs")
    scopes = tuple(
        (name, _parse_action_scope(name, block)) for name, block in actions.items()
    )
    action = request.action
    scope = next((s for n, s in scopes if n == action), None)
    if scope is None:
        # Unmentioned action: honest absence, never a wildcard.
        raise SourceUseRefused("action_not_licensed", "policy does not speak for this action")

    # Scope vs trusted-context joins: the policy must license exactly the use
    # the trusted server says it is about to perform — nothing inferred.
    if scope.output != context.output or scope.channel != context.channel:
        raise SourceUseRefused("scope_mismatch", "policy output/channel does not match the intended use")
    if set(scope.recipients) != set(context.recipients):
        raise SourceUseRefused("scope_mismatch", "policy recipients do not match the intended recipients")
    if scope.customer_id != context.customer_id:
        raise SourceUseRefused("scope_mismatch", "policy customer does not match the intended customer")
    if (
        scope.principal_id != request.principal_id
        or scope.principal_issuer != request.principal_issuer
        or scope.auth_epoch != request.auth_epoch
    ):
        raise SourceUseRefused("scope_mismatch", "policy principal/issuer/auth epoch does not match the request")
    undeclared = [f for f in scope.fields if f not in contract.schema]
    if undeclared:
        # The join that matters: the policy may only name fields the captured
        # dataset contract actually declares.
        raise SourceUseRefused("scope_mismatch", "policy names fields the dataset row does not declare")
    if not set(context.fields) <= set(scope.fields):
        raise SourceUseRefused("scope_mismatch", "intended fields exceed the policy's allowed fields")
    if {right for right, _why in scope.required_rights} != set(context.required_rights):
        raise SourceUseRefused("scope_mismatch", "policy required rights do not match the intended rights")

    policy = OptionsSourcePolicy(
        token=_VerifiedEvidence._mint(),
        policy_id=record["policy_id"],
        policy_revision=record["policy_revision"],
        registry_revision=record["registry_revision"],
        source_family=record["source_family"],
        dataset_id=record["dataset_id"],
        dataset_version=record["dataset_version"],
        vendor=record["vendor"],
        state=record["state"],
        known_at=known_at,
        effective_from=effective_from,
        effective_until=effective_until,
        evidence_revision=record["evidence_revision"],
        evidence_sha256=digest,
        evidence_pointer=pointer,
        source_sessions=tuple(sessions) if sessions is not None else None,
        scopes=scopes,
    )
    return policy, contract, context, decided_at


def load_options_source_policy(
    *,
    request: OptionUseRequest,
    registry: Registry,
    dataset_id: str,
    expected_evidence_sha256: str,
    expected_registry_revision: str,
    expected_source_family: str,
    use_context_for_request: Callable[[OptionUseRequest], ServerUseContext] | None = None,
    evidence_root: str | Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> OptionsSourcePolicy:
    """Verify and return the policy for one request context (audit entry point).

    Runs the full capture/join path used for a decision, for the action the
    request itself carries, and returns the minted
    :class:`OptionsSourcePolicy` — including when the policy affirmatively
    denies that action.  Refusals raise :class:`SourceUseRefused`; nothing is
    cached, so a later call re-captures the bytes.
    """
    policy, _contract, _context, _decided_at = _resolve_joined(
        request,
        registry=registry,
        dataset_id=dataset_id,
        expected_evidence_sha256=expected_evidence_sha256,
        expected_registry_revision=expected_registry_revision,
        expected_source_family=expected_source_family,
        use_context_for_request=use_context_for_request,
        evidence_root=evidence_root,
        clock=clock if clock is not None else (lambda: datetime.now(timezone.utc)),
    )
    return policy


def resolve_options_source_use_decision(
    request: Any,
    *,
    registry: Registry,
    dataset_id: str,
    expected_evidence_sha256: str,
    expected_registry_revision: str,
    expected_source_family: str,
    use_context_for_request: Callable[[OptionUseRequest], ServerUseContext] | None = None,
    evidence_root: str | Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Produce the closed seven-key source-use response for THIS request.

    Returns ``status: "allowed"`` only when the exact request, bound to a
    trusted :class:`ServerUseContext` from the injected resolver, joins a
    produced, unambiguous source row whose required rights' shared evidence
    bytes (digest-pinned by the operator) hold an active, current policy
    licensing exactly this action's intended output, channel, fields,
    recipients, customer, principal and rights.  An explicit ``allowed: false``
    in the same verified scope yields ``status: "denied"`` with the same
    genuine metadata.  Every other outcome raises :class:`SourceUseRefused` —
    never a permissive default, never an invented policy id/revision/family,
    and no state kept between calls.
    """
    policy, _contract, context, decided_at = _resolve_joined(
        request,
        registry=registry,
        dataset_id=dataset_id,
        expected_evidence_sha256=expected_evidence_sha256,
        expected_registry_revision=expected_registry_revision,
        expected_source_family=expected_source_family,
        use_context_for_request=use_context_for_request,
        evidence_root=evidence_root,
        clock=clock if clock is not None else (lambda: datetime.now(timezone.utc)),
    )
    scope = policy.scope_for(context.binding.action)
    if scope is None:
        raise SourceUseRefused("action_not_licensed", "policy does not speak for this action")
    binding = request.as_dict()
    return {
        "status": "allowed" if scope.allowed else "denied",
        "binding": binding,
        "source_family": policy.source_family,
        "policy_id": policy.policy_id,
        "policy_revision": policy.policy_revision,
        "registry_revision": policy.registry_revision,
        "decided_at": _format_instant(decided_at),
    }
