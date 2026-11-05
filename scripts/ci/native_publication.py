#!/usr/bin/env python3
"""Publication-receipt validation for Macro's native-queue rollout.

The incumbent ``scripts/ci/push_retry.sh`` ``push_do`` helper returns zero only
for an actual ``git push`` success; ``render.yml`` then reports "published" and
deletes the local candidate ref.  As the native queue is introduced, queue
admission must never be mistaken for published output.  This module is the
leaf safety contract between those two worlds: it decides, from explicitly
supplied expected and observed evidence, whether a native-queue candidate may
be called PUBLISHED.

Scope (deliberately narrow):

* Pure stdlib, no I/O, no network, no credentials, no state store, no
  scheduler, no hidden fallback, no environment activation switch.
* Inputs are caller-collected.  **Authenticated collection (verified token
  scopes, exact-head reads) and QLedger bookkeeping checks remain caller
  duties**; this module never performs or assumes them.
* The ``protected_route_attestation`` flag is caller-supplied.  **A bare
  attestation does not authenticate source data**: it records that the caller
  observed the write arrive through the native protected route.  Every value
  in ``ObservedPublication`` is unauthenticated caller data; this module makes
  no authenticity claim for it.  Validation only refuses evidence that is
  internally inconsistent, incomplete, or not sufficient for the claimed
  outcome.
* Queue admission, ledger state, API clients and runtime activation are out of
  scope.  No old proof is relabelled and no QLedger entry can override the
  output readback comparison.

Decision rule (fail closed):

PUBLISHED   requires the same repo/target/PR/source-head identity, an actually
            merged PR, a valid merge SHA distinct from the source head, an
            explicit ancestor proof (merge SHA inside the observed protected
            target ancestry), a protected-route attestation, and a *complete*
            output readback exactly equal to the expected generation
            (including confirmed deletions).
PENDING     open, unmerged PR with otherwise well-formed identity.  Queue
            admission is not published output.
SUPERSEDED  merged, identity/ancestry/readback completeness all valid, but the
            observed output readback differs from the expected generation
            (a later legitimate merge on the target changed the rendered
            outputs).
typed error anything malformed, mismatched, closed-unmerged, ancestry
            unknown/false, readback incomplete, or merged without the
            protected-route attestation.  Never returns success in those cases.

Deletion convention: a path that must not exist in the published output is an
``ExpectedOutput(path, mode=ABSENT, blob_sha=ABSENT)``.  An observed readback
confirms deletion with ``ABSENT``/``ABSENT``; an entry whose readback could
not be resolved uses ``UNKNOWN``/``UNKNOWN``.  ABSENT (confirmed not present)
and UNKNOWN (unresolved evidence) are deliberately distinct.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

__all__ = [
    "ABSENT",
    "UNKNOWN",
    "ExpectedOutput",
    "ObservedOutput",
    "ExpectedPublication",
    "ObservedPublication",
    "PublicationOutcome",
    "PublicationReceipt",
    "PublicationValidationError",
    "MalformedEvidenceError",
    "IdentityMismatchError",
    "ClosedUnmergedError",
    "UnknownAncestryError",
    "UnattestedRouteError",
    "IncompleteReadbackError",
    "validate_publication",
]


class _Marker:
    """Immutable named sentinel (ABSENT vs UNKNOWN)."""

    __slots__ = ("_name",)

    def __new__(cls, name: str) -> "_Marker":
        obj = super().__new__(cls)
        obj._name = name
        return obj

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return "publication.%s" % self._name

    def __copy__(self) -> "_Marker":
        return self

    def __deepcopy__(self, _memo: dict) -> "_Marker":
        return self


ABSENT = _Marker("ABSENT")    # documented absent value: path confirmed not present
UNKNOWN = _Marker("UNKNOWN")  # evidence required at this slot was not resolvable

_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_OWNER_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_ALLOWED_MODES = frozenset({"100644", "100755", "120000"})
_PR_STATES = frozenset({"open", "closed"})
_MAX_PATH_LEN = 4096
_MAX_REF_LEN = 1024


class PublicationValidationError(Exception):
    """Base typed error: fail-closed refusal with a precise reason."""

    code = "PUBLICATION_VALIDATION_ERROR"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MalformedEvidenceError(PublicationValidationError):
    code = "MALFORMED_EVIDENCE"


class IdentityMismatchError(PublicationValidationError):
    code = "IDENTITY_MISMATCH"


class ClosedUnmergedError(PublicationValidationError):
    code = "CLOSED_UNMERGED"


class UnknownAncestryError(PublicationValidationError):
    code = "UNKNOWN_ANCESTRY"


class UnattestedRouteError(PublicationValidationError):
    code = "UNATTESTED_ROUTE"


class IncompleteReadbackError(PublicationValidationError):
    code = "INCOMPLETE_READBACK"


class PublicationOutcome(str, Enum):
    PUBLISHED = "PUBLISHED"
    PENDING = "PENDING"
    SUPERSEDED = "SUPERSEDED"


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA_RE.match(value) is not None


def _require_sha(value: object, field: str) -> str:
    if not _is_sha(value):
        raise MalformedEvidenceError(
            "%s must be a 40-char lowercase hex git SHA, got %r" % (field, value)
        )
    return value  # type: ignore[return-value]


def _require_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise MalformedEvidenceError("%s must be a bool, got %r" % (field, value))
    return value


def _require_optional_sha(value: object, field: str) -> Optional[str]:
    if value is None:
        return None
    return _require_sha(value, field)


def _require_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MalformedEvidenceError("%s must be a non-empty str" % field)
    if len(value) > _MAX_PATH_LEN:
        raise MalformedEvidenceError("%s exceeds %d chars" % (field, _MAX_PATH_LEN))
    if "\x00" in value or "\\" in value:
        raise MalformedEvidenceError("%s contains NUL or backslash: %r" % (field, value))
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise MalformedEvidenceError("%s contains control characters: %r" % (field, value))
    if value.startswith("/") or value.endswith("/"):
        raise MalformedEvidenceError("%s must be a relative path: %r" % (field, value))
    if len(value) > 1 and value[1] == ":":
        raise MalformedEvidenceError("%s must not carry a drive prefix: %r" % (field, value))
    segments = value.split("/")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise MalformedEvidenceError(
                "%s must not contain empty/'.'/..' segments: %r" % (field, value)
            )
        if segment.endswith(".lock") and segment != ".lock":
            pass  # ordinary file names ending in .lock are legal output paths
    return value


def _require_ref(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MalformedEvidenceError("%s must be a non-empty str" % field)
    if len(value) > _MAX_REF_LEN:
        raise MalformedEvidenceError("%s exceeds %d chars" % (field, _MAX_REF_LEN))
    if "\x00" in value or "\\" in value:
        raise MalformedEvidenceError("%s contains NUL or backslash: %r" % (field, value))
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise MalformedEvidenceError("%s contains control characters: %r" % (field, value))
    if value.startswith("/") or value.endswith("/") or "//" in value:
        raise MalformedEvidenceError("%s has empty ref component: %r" % (field, value))
    if value.startswith(".") or value.endswith(".") or value.startswith("-"):
        raise MalformedEvidenceError("%s has unsafe ref leading/trailing char: %r" % (field, value))
    if ".." in value or "@{" in value:
        raise MalformedEvidenceError("%s contains unsafe ref sequence: %r" % (field, value))
    for segment in value.split("/"):
        if segment.endswith(".lock"):
            raise MalformedEvidenceError("%s ends a component in .lock: %r" % (field, value))
        if segment == "":
            raise MalformedEvidenceError("%s has empty ref component: %r" % (field, value))
    return value


def _require_owner(value: object, field: str) -> str:
    if not isinstance(value, str) or _OWNER_RE.match(value) is None or ".." in value:
        raise MalformedEvidenceError("%s must match [A-Za-z0-9][A-Za-z0-9._-]* : %r" % (field, value))
    return value


def _require_pr_number(value: object, field: str) -> int:
    # bool is an int subclass; a True/False PR number is malformed evidence.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MalformedEvidenceError("%s must be a positive int, got %r" % (field, value))
    return value


def _freeze_outputs(raw: object, field: str, cls: type) -> tuple:
    if isinstance(raw, (list, tuple)):
        value = tuple(raw)
    else:
        raise MalformedEvidenceError("%s must be a list or tuple of %s" % (field, cls.__name__))
    seen = set()
    for entry in value:
        if not isinstance(entry, cls):
            raise MalformedEvidenceError("%s entries must be %s instances" % (field, cls.__name__))
        if entry.path in seen:
            raise MalformedEvidenceError("%s contains duplicate path %r" % (field, entry.path))
        seen.add(entry.path)
    return value


@dataclass(frozen=True)
class ExpectedOutput:
    """One expected output slot of the publication generation.

    ``mode`` is a canonical git mode (100644/100755/120000) or ABSENT for a
    required deletion; ``blob_sha`` is the 40-hex git blob SHA or ABSENT.
    Expected evidence is a plan: UNKNOWN is not a legal value here.
    """

    path: str
    mode: object
    blob_sha: object

    def __post_init__(self) -> None:
        _require_path(self.path, "ExpectedOutput.path")
        if self.blob_sha is ABSENT:
            if self.mode is not ABSENT:
                raise MalformedEvidenceError(
                    "ExpectedOutput %r: deletion must set mode=ABSENT too" % self.path
                )
        elif _is_sha(self.blob_sha):
            if self.mode not in _ALLOWED_MODES:
                raise MalformedEvidenceError(
                    "ExpectedOutput %r: mode must be one of %s for a present file"
                    % (self.path, sorted(_ALLOWED_MODES))
                )
        else:
            raise MalformedEvidenceError(
                "ExpectedOutput %r: blob_sha must be a 40-hex SHA or ABSENT, got %r"
                % (self.path, self.blob_sha)
            )
        if self.mode is UNKNOWN or self.blob_sha is UNKNOWN:
            raise MalformedEvidenceError(
                "ExpectedOutput %r is a plan; UNKNOWN is not a legal expected value" % self.path
            )


@dataclass(frozen=True)
class ObservedOutput:
    """One observed readback slot.

    ``blob_sha``/``mode`` are the resolved value, ABSENT (confirmed not
    present) or UNKNOWN (unresolved evidence).  A confirmed deletion is
    ABSENT/ABSENT; an unresolved entry is UNKNOWN/UNKNOWN.
    """

    path: str
    mode: object
    blob_sha: object

    def __post_init__(self) -> None:
        _require_path(self.path, "ObservedOutput.path")
        if (self.mode is UNKNOWN) != (self.blob_sha is UNKNOWN):
            raise MalformedEvidenceError(
                "ObservedOutput %r: mode/blob must be UNKNOWN together" % self.path
            )
        if self.blob_sha is ABSENT:
            if self.mode is not ABSENT:
                raise MalformedEvidenceError(
                    "ObservedOutput %r: absent blob requires mode=ABSENT" % self.path
                )
        elif self.blob_sha is UNKNOWN:
            pass
        elif _is_sha(self.blob_sha):
            if self.mode not in _ALLOWED_MODES:
                raise MalformedEvidenceError(
                    "ObservedOutput %r: mode must be one of %s for a present file"
                    % (self.path, sorted(_ALLOWED_MODES))
                )
        else:
            raise MalformedEvidenceError(
                "ObservedOutput %r: blob_sha must be a 40-hex SHA, ABSENT or UNKNOWN, got %r"
                % (self.path, self.blob_sha)
            )


@dataclass(frozen=True)
class ExpectedPublication:
    """What the caller expects the native publication to produce."""

    repo_owner: str
    repo_name: str
    target_ref: str
    pr_number: int
    source_head: str
    expected_outputs: Tuple[ExpectedOutput, ...]

    def __post_init__(self) -> None:
        _require_owner(self.repo_owner, "ExpectedPublication.repo_owner")
        _require_owner(self.repo_name, "ExpectedPublication.repo_name")
        _require_ref(self.target_ref, "ExpectedPublication.target_ref")
        _require_pr_number(self.pr_number, "ExpectedPublication.pr_number")
        _require_sha(self.source_head, "ExpectedPublication.source_head")
        outputs = _freeze_outputs(
            self.expected_outputs, "ExpectedPublication.expected_outputs", ExpectedOutput
        )
        if not outputs:
            raise MalformedEvidenceError(
                "ExpectedPublication.expected_outputs must contain at least one slot"
            )
        object.__setattr__(self, "expected_outputs", outputs)


@dataclass(frozen=True)
class ObservedPublication:
    """Caller-collected observation of the PR, protected target and outputs.

    Every field is unauthenticated caller evidence.  ``merge_sha`` is None
    while the PR is not merged.  ``ancestor_proof`` is True, False or UNKNOWN:
    True means the caller verified the merge SHA is included in the ancestry
    of ``observed_target_sha`` on the protected target route.
    """

    repo_owner: str
    repo_name: str
    target_ref: str
    pr_number: int
    source_head: str
    pr_state: str
    merged: bool
    merge_sha: Optional[str]
    observed_target_sha: Optional[str]
    ancestor_proof: object
    output_readback: Tuple[ObservedOutput, ...]
    protected_route_attestation: bool

    def __post_init__(self) -> None:
        _require_owner(self.repo_owner, "ObservedPublication.repo_owner")
        _require_owner(self.repo_name, "ObservedPublication.repo_name")
        _require_ref(self.target_ref, "ObservedPublication.target_ref")
        _require_pr_number(self.pr_number, "ObservedPublication.pr_number")
        _require_sha(self.source_head, "ObservedPublication.source_head")
        if self.pr_state not in _PR_STATES:
            raise MalformedEvidenceError(
                "ObservedPublication.pr_state must be 'open' or 'closed', got %r" % (self.pr_state,)
            )
        _require_bool(self.merged, "ObservedPublication.merged")
        _require_bool(
            self.protected_route_attestation, "ObservedPublication.protected_route_attestation"
        )
        if type(self.ancestor_proof) is not bool and self.ancestor_proof is not UNKNOWN:
            raise MalformedEvidenceError(
                "ObservedPublication.ancestor_proof must be True, False or UNKNOWN, got %r"
                % (self.ancestor_proof,)
            )
        merged_sha = _require_optional_sha(self.merge_sha, "ObservedPublication.merge_sha")
        target_sha = _require_optional_sha(
            self.observed_target_sha, "ObservedPublication.observed_target_sha"
        )
        if not self.merged and merged_sha is not None:
            raise MalformedEvidenceError(
                "ObservedPublication.merge_sha must be None while merged is False"
            )
        if self.merged:
            if merged_sha is None:
                raise MalformedEvidenceError(
                    "ObservedPublication.merge_sha is required while merged is True"
                )
            if target_sha is None:
                raise MalformedEvidenceError(
                    "ObservedPublication.observed_target_sha is required while merged is True"
                )
        readback = _freeze_outputs(
            self.output_readback, "ObservedPublication.output_readback", ObservedOutput
        )
        object.__setattr__(self, "output_readback", readback)


@dataclass(frozen=True)
class PublicationReceipt:
    """Immutable validation result.

    ``attestation_relied_upon`` is True only for PUBLISHED, where the
    caller-supplied protected-route attestation was required for the verdict.
    It records reliance, not authentication of the source data.
    """

    outcome: PublicationOutcome
    reasons: Tuple[str, ...]
    pr_number: int
    source_head: str
    merge_sha: Optional[str]
    observed_target_sha: Optional[str]
    attestation_relied_upon: bool
    notes: Tuple[str, ...]


_ATTESTATION_NOTE = (
    "protected_route_attestation is caller-supplied evidence of the write "
    "route; it does not authenticate source data. Authenticated collection "
    "and QLedger checks remain caller duties."
)
_PENDING_NOTE = (
    "queue admission is not published output; PENDING records an open, "
    "unmerged candidate only."
)


def _check_identity(expected: ExpectedPublication, observed: ObservedPublication) -> None:
    pairs = (
        ("repo_owner", expected.repo_owner, observed.repo_owner),
        ("repo_name", expected.repo_name, observed.repo_name),
        ("target_ref", expected.target_ref, observed.target_ref),
        ("pr_number", expected.pr_number, observed.pr_number),
        ("source_head", expected.source_head, observed.source_head),
    )
    mismatches = [
        "%s expected %r observed %r" % (name, want, got)
        for name, want, got in pairs
        if want != got
    ]
    if mismatches:
        raise IdentityMismatchError(
            "observed publication identity does not match expectation: " + "; ".join(mismatches)
        )


def _check_merged_gateways(observed: ObservedPublication) -> str:
    """Validated merge SHA for a merged PR, with merge-vs-source distinction."""
    merge_sha = observed.merge_sha
    assert merge_sha is not None  # narrowed by ObservedPublication.__post_init__
    if merge_sha == observed.source_head:
        raise MalformedEvidenceError(
            "merge_sha %s equals source_head; a merged PR must record the merge "
            "commit created by the target, not the candidate source head" % merge_sha
        )
    if observed.ancestor_proof is UNKNOWN:
        raise UnknownAncestryError(
            "ancestor proof is UNKNOWN: cannot place merge_sha %s inside the "
            "observed protected target ancestry of %s"
            % (merge_sha, observed.observed_target_sha)
        )
    if observed.ancestor_proof is False:
        raise UnknownAncestryError(
            "ancestor proof is False: merge_sha %s is not contained in the "
            "observed protected target ancestry of %s"
            % (merge_sha, observed.observed_target_sha)
        )
    if not observed.protected_route_attestation:
        raise UnattestedRouteError(
            "merged PR lacks the native protected-route attestation; refusing "
            "to call the target published"
        )
    return merge_sha


def _check_readback_complete(
    expected: ExpectedPublication, observed: ObservedPublication
) -> None:
    expected_paths = {slot.path for slot in expected.expected_outputs}
    observed_by_path = {}
    for slot in observed.output_readback:
        if slot.path in observed_by_path:
            raise IncompleteReadbackError(
                "output_readback contains duplicate path %r" % slot.path
            )
        observed_by_path[slot.path] = slot
    missing = sorted(expected_paths - set(observed_by_path))
    if missing:
        raise IncompleteReadbackError(
            "output readback is incomplete; missing expected output paths: %s"
            % ", ".join(repr(p) for p in missing)
        )
    extra = sorted(set(observed_by_path) - expected_paths)
    if extra:
        raise IncompleteReadbackError(
            "output readback contains paths outside the expected generation: %s"
            % ", ".join(repr(p) for p in extra)
        )
    unresolved = sorted(
        slot.path for slot in observed.output_readback if slot.blob_sha is UNKNOWN
    )
    if unresolved:
        raise IncompleteReadbackError(
            "output readback is incomplete; unresolved (UNKNOWN) paths: %s"
            % ", ".join(repr(p) for p in unresolved)
        )


def _compare_generation(
    expected: ExpectedPublication, observed: ObservedPublication
) -> Tuple[str, ...]:
    reasons = []
    expected_by_path = {slot.path: slot for slot in expected.expected_outputs}
    observed_by_path = {slot.path: slot for slot in observed.output_readback}
    for path in sorted(expected_by_path):
        want = expected_by_path[path]
        got = observed_by_path[path]
        if want.mode != got.mode or want.blob_sha != got.blob_sha:
            reasons.append(
                "output %r expected (mode=%r, blob=%r) observed (mode=%r, blob=%r)"
                % (path, want.mode, want.blob_sha, got.mode, got.blob_sha)
            )
    return tuple(reasons)


def validate_publication(
    expected: ExpectedPublication, observed: ObservedPublication
) -> PublicationReceipt:
    """Decide PUBLISHED / PENDING / SUPERSEDED, or raise a typed error.

    Fail-closed and pure: reads only the two supplied records, mutates
    nothing, and never reports success on queued, open, unknown, unreadable,
    mismatched or unattested evidence.
    """
    if not isinstance(expected, ExpectedPublication):
        raise MalformedEvidenceError(
            "expected must be an ExpectedPublication, got %r" % type(expected).__name__
        )
    if not isinstance(observed, ObservedPublication):
        raise MalformedEvidenceError(
            "observed must be an ObservedPublication, got %r" % type(observed).__name__
        )
    _check_identity(expected, observed)

    if not observed.merged:
        if observed.pr_state == "closed":
            raise ClosedUnmergedError(
                "PR %d is closed without being merged; the candidate was "
                "refused, not published" % observed.pr_number
            )
        # open + unmerged + otherwise well-formed identity -> queue admission.
        return PublicationReceipt(
            outcome=PublicationOutcome.PENDING,
            reasons=("PR %d is open and not merged; publication is still pending" % observed.pr_number,),
            pr_number=observed.pr_number,
            source_head=observed.source_head,
            merge_sha=None,
            observed_target_sha=observed.observed_target_sha,
            attestation_relied_upon=False,
            notes=(_PENDING_NOTE, _ATTESTATION_NOTE),
        )

    if observed.pr_state != "closed":
        raise MalformedEvidenceError(
            "merged is True but pr_state is %r; a merged PR is closed" % (observed.pr_state,)
        )
    merge_sha = _check_merged_gateways(observed)
    _check_readback_complete(expected, observed)
    supersession = _compare_generation(expected, observed)
    if supersession:
        return PublicationReceipt(
            outcome=PublicationOutcome.SUPERSEDED,
            reasons=("the merged target output differs from the expected generation:",)
            + supersession,
            pr_number=observed.pr_number,
            source_head=observed.source_head,
            merge_sha=merge_sha,
            observed_target_sha=observed.observed_target_sha,
            attestation_relied_upon=True,
            notes=(_ATTESTATION_NOTE,),
        )
    return PublicationReceipt(
        outcome=PublicationOutcome.PUBLISHED,
        reasons=(
            "PR %d merged at %s; merge SHA verified inside protected target %s "
            "ancestry; complete output readback matches the expected generation"
            % (observed.pr_number, merge_sha, observed.observed_target_sha),
        ),
        pr_number=observed.pr_number,
        source_head=observed.source_head,
        merge_sha=merge_sha,
        observed_target_sha=observed.observed_target_sha,
        attestation_relied_upon=True,
        notes=(_ATTESTATION_NOTE,),
    )
