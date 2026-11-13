#!/usr/bin/env python3
"""Trusted-base gate for files capable of manufacturing CI proof.

``pull_request_target`` runs this controller from the default branch.  It never
checks out or executes pull-request code.  The event identifies the proposed
head and base, then read-only API calls re-prove the current PR identity and
enumerate its exact changed files within the endpoint ceiling. Oversized
inventories remain explicitly unclassified and require the same strongest
same-repository, dual-admin authority as a known CI-control change; they never
take the ordinary-change route. No candidate code or alternate file reader is
used. Complementary base-specific checks are
written to that exact head: the current-base verdict and a terminal failure for
the other supported base.  They must never be the sole required authority; the
organization required-workflow rule and its stable ``ci-authority`` job remain
mandatory.

Read-only GET calls (``get_pull``, ``list_pull_files``,
``get_collaborator_permission``) are retried with bounded backoff on transient
conditions only (timeouts, 429/408/5xx, and rate-limit-shaped 403s); the gate
still fails closed on every non-transient or exhausted-retry outcome, and the
published reject reason names the failure mode (rate limited, timeout,
rejected, or unavailable) instead of one opaque string.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from scripts.ci_authority_paths import (
        AuthorityPathError,
        canonical_repo_path,
        is_ci_authority_path,
    )
except ModuleNotFoundError:  # Direct ``python scripts/ci_authority.py``.
    from ci_authority_paths import (  # type: ignore[no-redef]
        AuthorityPathError,
        canonical_repo_path,
        is_ci_authority_path,
    )


SCHEMA = "ci.authority.v1"
CHECK_NAME = "ci-authority"
SUPPORTED_BASE_REFS = ("main", "codex/merge-queue-pilot")
MAX_CHANGED_FILES = 3000  # GitHub's pull-files API hard ceiling.
MAX_AUTHORITY_PATHS_IN_RECEIPT = 20
MAX_RECEIPT_PATH_CHARS = 160
_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")

API_TIMEOUT_SECONDS = 20
API_RETRY_ATTEMPTS = 4  # one initial attempt plus up to three retries
API_RETRY_BASE_DELAY_SECONDS = 1.0
API_RETRY_MAX_DELAY_SECONDS = 8.0
API_RETRY_TOTAL_BUDGET_SECONDS = 45.0
RETRYABLE_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class AuthorityContractError(ValueError):
    """The trusted workflow received an unusable event envelope."""


class GitHubApiError(RuntimeError):
    """A GitHub API request did not produce bounded, usable evidence."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "unavailable",
        status: int | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.retryable = retryable
        self.retry_after = retry_after


class AuthorityApi(Protocol):
    def get_pull(self, repository: str, number: int) -> object: ...

    def list_pull_files(
        self, repository: str, number: int, expected_count: int
    ) -> object: ...

    def get_collaborator_permission(self, repository: str, login: str) -> object: ...

    def create_check(self, repository: str, payload: Mapping[str, object]) -> object: ...


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _sha(value: object) -> str | None:
    return value if type(value) is str and _SHA.fullmatch(value) else None


def _positive_int(value: object) -> int | None:
    return value if type(value) is int and value > 0 else None


def _nonnegative_int(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _safe_login(value: object) -> str | None:
    if type(value) is not str or not (1 <= len(value) <= 100):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    return value


def _safe_ref(value: object) -> str | None:
    if type(value) is not str or not (1 <= len(value.encode("utf-8")) <= 1024):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    if (
        value.startswith("/")
        or value.endswith("/")
        or value.startswith(".")
        or value.endswith(".")
        or ".." in value
        or "@{" in value
        or "\\" in value
        or any(character in value for character in " ~^:?*[")
    ):
        return None
    return value


def _repository(value: object) -> str | None:
    if type(value) is not str or value.count("/") != 1:
        return None
    owner, name = value.split("/", 1)
    if not owner or not name or len(value) > 200:
        return None
    if any(ord(character) < 33 or ord(character) > 126 for character in value):
        return None
    return value


def _event_target(payload: object, expected_repository: str) -> dict[str, object]:
    event = _mapping(payload)
    if event is None:
        raise AuthorityContractError("event must be an object")
    repository = _mapping(event.get("repository"))
    pull = _mapping(event.get("pull_request"))
    sender = _mapping(event.get("sender"))
    action = event.get("action")
    if repository is None or pull is None or sender is None:
        raise AuthorityContractError(
            "event requires repository, pull_request, and sender"
        )
    if action not in {"opened", "synchronize", "reopened", "edited"}:
        raise AuthorityContractError("unsupported pull_request_target action")
    trusted_repository = _repository(expected_repository)
    if trusted_repository is None or repository.get("full_name") != trusted_repository:
        raise AuthorityContractError("event repository does not match workflow repository")

    number = _positive_int(pull.get("number"))
    head = _mapping(pull.get("head"))
    head_repo = None if head is None else _mapping(head.get("repo"))
    base = _mapping(pull.get("base"))
    base_repo = None if base is None else _mapping(base.get("repo"))
    user = _mapping(pull.get("user"))
    head_sha = None if head is None else _sha(head.get("sha"))
    head_repository = None if head_repo is None else _repository(head_repo.get("full_name"))
    base_sha = None if base is None else _sha(base.get("sha"))
    base_ref = None if base is None else _safe_ref(base.get("ref"))
    base_repository = None if base_repo is None else _repository(base_repo.get("full_name"))
    author = None if user is None else _safe_login(user.get("login"))
    actor = _safe_login(sender.get("login"))
    if (
        number is None
        or head_sha is None
        or head_repository is None
        or base_sha is None
        or base_ref is None
        or base_repository != trusted_repository
        or author is None
        or actor is None
    ):
        raise AuthorityContractError("event PR identity is missing or malformed")
    return {
        "repository": trusted_repository,
        "pull_request_number": number,
        "event_action": action,
        "head_sha": head_sha,
        "head_repository": head_repository,
        "base_sha": base_sha,
        "base_ref": base_ref,
        "base_repository": base_repository,
        "author": author,
        "actor": actor,
    }


def _base_decision(target: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "event": "pull_request_target",
        **target,
        "current_base_sha": None,
        "post_files_base_sha": None,
        "inventory_base_sha": None,
        "inventory_mode": "unavailable",
        "inventory_complete": False,
        "post_authorization_base_sha": None,
        "changed_files_snapshot_attempts": 0,
        "changed_file_count": None,
        "authority_hit_count": 0,
        "authority_hits": [],
        "author_admin_verified": False,
        "actor_admin_verified": False,
        "admin_verified": False,
        "allowed": False,
        "reason": "unproven",
    }


def _reject(decision: Mapping[str, object], reason: str) -> dict[str, object]:
    result = dict(decision)
    result["allowed"] = False
    result["reason"] = reason
    return result


def _current_pull_identity(
    response: object, target: Mapping[str, object]
) -> tuple[Mapping[str, Any], int] | None:
    pull = _mapping(response)
    if pull is None:
        return None
    base = _mapping(pull.get("base"))
    base_repo = None if base is None else _mapping(base.get("repo"))
    head = _mapping(pull.get("head"))
    head_repo = None if head is None else _mapping(head.get("repo"))
    user = _mapping(pull.get("user"))
    changed_count = _nonnegative_int(pull.get("changed_files"))
    if (
        pull.get("number") != target["pull_request_number"]
        or pull.get("state") != "open"
        or base_repo is None
        or base_repo.get("full_name") != target["repository"]
        or _sha(base.get("sha")) is None
        or _safe_ref(base.get("ref")) is None
        or head is None
        or _sha(head.get("sha")) is None
        or head_repo is None
        or _repository(head_repo.get("full_name")) is None
        or user is None
        or _safe_login(user.get("login")) is None
        or changed_count is None
    ):
        return None
    return pull, changed_count


def _changed_paths(file_entries: object, expected_count: int) -> tuple[str, ...]:
    if not isinstance(file_entries, Sequence) or isinstance(file_entries, (str, bytes)):
        raise AuthorityContractError("pull files response is not an array")
    if len(file_entries) != expected_count:
        raise AuthorityContractError("pull files response count does not match current PR")
    paths: list[str] = []
    current_names: set[str] = set()
    for entry in file_entries:
        item = _mapping(entry)
        if item is None:
            raise AuthorityContractError("pull files response contains a non-object")
        status = item.get("status")
        if status not in {
            "added",
            "removed",
            "modified",
            "renamed",
            "copied",
            "changed",
            "unchanged",
        }:
            raise AuthorityContractError("pull files response has an unknown status")
        current = canonical_repo_path(item.get("filename"))
        if current in current_names:
            raise AuthorityContractError("pull files response repeats a filename")
        current_names.add(current)
        paths.append(current)
        previous = item.get("previous_filename")
        if status == "renamed" and previous is None:
            raise AuthorityContractError("renamed file omits previous_filename")
        if previous is not None:
            paths.append(canonical_repo_path(previous))
    return tuple(dict.fromkeys(paths))


def _candidate_identity_still_matches(
    current: Mapping[str, Any],
    target: Mapping[str, object],
) -> bool:
    """Bind candidate authority identity without binding integration composition.

    ``target["base_sha"]`` is immutable event provenance, but the live tip of the
    same trusted base ref may advance independently while an unchanged candidate is
    being evaluated.  Semantic CI binds the exact synthetic merge and its parent-1
    base; this controller instead binds the candidate, repositories, and target ref.
    """
    head = _mapping(current.get("head"))
    head_repo = None if head is None else _mapping(head.get("repo"))
    base = _mapping(current.get("base"))
    base_repo = None if base is None else _mapping(base.get("repo"))
    user = _mapping(current.get("user"))
    return bool(
        head is not None
        and head_repo is not None
        and base is not None
        and base_repo is not None
        and user is not None
        and head.get("sha") == target["head_sha"]
        and head_repo.get("full_name") == target["head_repository"]
        and base.get("ref") == target["base_ref"]
        and base_repo.get("full_name") == target["base_repository"]
        and user.get("login") == target["author"]
    )


def _permission_proves_admin(response: object, login: str) -> bool:
    permission = _mapping(response)
    permission_user = None if permission is None else _mapping(permission.get("user"))
    return bool(
        permission is not None
        and permission.get("permission") == "admin"
        and permission_user is not None
        and permission_user.get("login") == login
    )


def _receipt_path(path: str) -> str:
    """Keep the check summary bounded without losing long-path identity."""
    if len(path) <= MAX_RECEIPT_PATH_CHARS:
        return path
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
    prefix = path[: MAX_RECEIPT_PATH_CHARS - 70]
    return f"{prefix}...sha256:{digest}"


_API_FAILURE_SUFFIX = {
    "rate_limited": "rate_limited",
    "timeout": "timeout",
    "rejected": "api_rejected",
}


def _api_failure_reason(prefix: str, exc: BaseException) -> str:
    """Name the failure MODE so triage does not restart from zero."""
    kind = getattr(exc, "kind", "")
    return f"{prefix}_{_API_FAILURE_SUFFIX.get(kind, 'api_unavailable')}"


def _log_api_failure(stage: str, exc: BaseException) -> None:
    """Surface the swallowed exception instead of discarding it silently.

    A GitHub annotation MUST start at column 0 of a bare ``print`` — never go
    through a logger, which prefixes the line and makes GitHub drop it (house
    law, ``tests/test_gh_annotation_line_start.py``). The full traceback goes
    to stderr for humans reading the job log.
    """
    status = getattr(exc, "status", None)
    kind = getattr(exc, "kind", None)
    cause = exc.__cause__
    detail = f"{stage}: {type(exc).__name__}: {exc}"
    if status is not None:
        detail += f" (status={status})"
    if kind:
        detail += f" (kind={kind})"
    if cause is not None:
        detail += f" (cause={type(cause).__name__}: {cause})"
    detail = " ".join(detail.split())
    if len(detail) > 300:
        detail = detail[:300]
    print(f"::error title=ci-authority-api::{detail}", flush=True)
    traceback_text = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    print(traceback_text, file=sys.stderr)


def _authorize_same_repo_admin_change(
    decision: dict[str, object],
    target: Mapping[str, object],
    api: AuthorityApi,
    *,
    oversized_count: int | None = None,
) -> dict[str, object]:
    """Apply the one existing maximum-authority predicate to this candidate."""
    repository = str(target["repository"])
    if target["head_repository"] != repository:
        return _reject(decision, "fork_cannot_change_ci_authority")

    try:
        author_permission = api.get_collaborator_permission(
            repository, str(target["author"])
        )
    except Exception as exc:
        _log_api_failure("author_admin_permission", exc)
        return _reject(decision, _api_failure_reason("author_admin_permission", exc))
    if not _permission_proves_admin(author_permission, str(target["author"])):
        return _reject(decision, "same_repo_author_is_not_admin")
    decision["author_admin_verified"] = True

    # PR authorship is stable across synchronize events and therefore cannot
    # identify who pushed the exact head being evaluated. Bind the signed event
    # sender and re-check that actor's live repository permission too. Reuse the
    # author result only when GitHub identifies the same login in both fields.
    if target["actor"] == target["author"]:
        actor_permission = author_permission
    else:
        try:
            actor_permission = api.get_collaborator_permission(
                repository, str(target["actor"])
            )
        except Exception as exc:
            _log_api_failure("actor_admin_permission", exc)
            return _reject(decision, _api_failure_reason("actor_admin_permission", exc))
    if not _permission_proves_admin(actor_permission, str(target["actor"])):
        return _reject(decision, "current_head_actor_is_not_admin")

    decision["actor_admin_verified"] = True
    decision["admin_verified"] = True

    if oversized_count is not None:
        # Size can select stricter authorization, never a fictitious path proof.
        # Recheck the exact candidate after the live permission reads. Same-ref
        # base movement remains integration composition, not candidate identity.
        try:
            final_response = api.get_pull(repository, int(target["pull_request_number"]))
        except Exception as exc:
            _log_api_failure("post_authorization_pull", exc)
            return _reject(decision, _api_failure_reason("post_authorization_pull", exc))
        final_identity = _current_pull_identity(final_response, target)
        if (
            final_identity is None
            or final_identity[1] != oversized_count
            or not _candidate_identity_still_matches(final_identity[0], target)
        ):
            return _reject(decision, "post_authorization_identity_drift")
        final_base = _mapping(final_identity[0].get("base"))
        decision["post_authorization_base_sha"] = (
            None if final_base is None else _sha(final_base.get("sha"))
        )

    decision["allowed"] = True
    decision["reason"] = (
        "same_repo_admin_unclassified_change"
        if oversized_count is not None
        else "same_repo_admin_authority_change"
    )
    return decision


def evaluate_pull_request_target(
    payload: object,
    expected_repository: str,
    api: AuthorityApi,
) -> dict[str, object]:
    """Return a fail-closed authority decision from current GitHub evidence."""
    target = _event_target(payload, expected_repository)
    decision = _base_decision(target)
    number = int(target["pull_request_number"])
    repository = str(target["repository"])

    try:
        current_response = api.get_pull(repository, number)
    except Exception as exc:
        _log_api_failure("current_pull", exc)
        return _reject(decision, _api_failure_reason("current_pull", exc))
    identity = _current_pull_identity(current_response, target)
    if identity is None:
        return _reject(decision, "current_pull_identity_rejected")
    current, changed_count = identity
    current_base = _mapping(current.get("base"))
    decision["current_base_sha"] = (
        None if current_base is None else _sha(current_base.get("sha"))
    )
    if not _candidate_identity_still_matches(current, target):
        return _reject(decision, "event_head_base_or_author_drift")

    if changed_count > MAX_CHANGED_FILES:
        # GitHub cannot enumerate this inventory through the bounded endpoint.
        # Conservatively classify the whole candidate at the strongest existing
        # authority tier. Unknown paths are neither an empty inventory nor zero
        # observed authority hits; other proof/review owners still need their
        # own complete source evidence.
        decision.update(
            changed_file_count=changed_count,
            inventory_mode="conservative_authority",
            authority_hit_count=None,
            authority_hits=None,
        )
        return _authorize_same_repo_admin_change(
            decision, target, api, oversized_count=changed_count
        )

    try:
        entries = api.list_pull_files(repository, number, changed_count)
        paths = _changed_paths(entries, changed_count)
        decision["changed_files_snapshot_attempts"] = 1
    except (AuthorityContractError, AuthorityPathError):
        return _reject(decision, "changed_files_rejected")
    except Exception as exc:
        _log_api_failure("changed_files", exc)
        return _reject(decision, _api_failure_reason("changed_files", exc))

    # The files endpoint is PR-number scoped rather than SHA scoped. Re-read the
    # PR after pagination so a push between the first identity GET and the last
    # files page cannot let a new candidate inherit an old inventory (or vice
    # versa). The new synchronize event will evaluate the new head independently.
    try:
        after_response = api.get_pull(repository, number)
    except Exception as exc:
        _log_api_failure("post_files_pull", exc)
        return _reject(decision, _api_failure_reason("post_files_pull", exc))
    after_identity = _current_pull_identity(after_response, target)
    if after_identity is not None:
        post_files_base = _mapping(after_identity[0].get("base"))
        decision["post_files_base_sha"] = (
            None if post_files_base is None else _sha(post_files_base.get("sha"))
        )
    if (
        after_identity is None
        or after_identity[1] != changed_count
        or not _candidate_identity_still_matches(after_identity[0], target)
    ):
        return _reject(decision, "event_head_base_or_files_drift")

    # The base SHA is integration composition, not candidate identity. If it
    # advanced while the paginated inventory was being read, discard the crossed
    # inventory and make one bounded attempt to acquire a snapshot bracketed by
    # the same live base SHA. This keeps normal same-ref movement lawful while
    # refusing to classify a mixed old/new page population.
    if decision["post_files_base_sha"] != decision["current_base_sha"]:
        snapshot_base_sha = decision["post_files_base_sha"]
        try:
            recheck_entries = api.list_pull_files(repository, number, changed_count)
            recheck_paths = _changed_paths(recheck_entries, changed_count)
            decision["changed_files_snapshot_attempts"] = 2
        except (AuthorityContractError, AuthorityPathError):
            return _reject(decision, "changed_files_recheck_rejected")
        except Exception as exc:
            _log_api_failure("changed_files_recheck", exc)
            return _reject(
                decision, _api_failure_reason("changed_files_recheck", exc)
            )
        try:
            final_response = api.get_pull(repository, number)
        except Exception as exc:
            _log_api_failure("post_recheck_pull", exc)
            return _reject(decision, _api_failure_reason("post_recheck_pull", exc))
        final_identity = _current_pull_identity(final_response, target)
        if final_identity is not None:
            final_base = _mapping(final_identity[0].get("base"))
            decision["post_files_base_sha"] = (
                None if final_base is None else _sha(final_base.get("sha"))
            )
        if (
            final_identity is None
            or final_identity[1] != changed_count
            or not _candidate_identity_still_matches(final_identity[0], target)
        ):
            return _reject(decision, "event_head_base_or_files_drift")
        if decision["post_files_base_sha"] != snapshot_base_sha:
            return _reject(decision, "changed_files_snapshot_unstable")
        paths = recheck_paths

    decision["inventory_base_sha"] = decision["post_files_base_sha"]
    decision["inventory_mode"] = "exact_changed_paths"
    decision["inventory_complete"] = True

    authority_hits = sorted(path for path in paths if is_ci_authority_path(path))
    decision["changed_file_count"] = changed_count
    decision["authority_hit_count"] = len(authority_hits)
    decision["authority_hits"] = [
        _receipt_path(path)
        for path in authority_hits[:MAX_AUTHORITY_PATHS_IN_RECEIPT]
    ]
    if not authority_hits:
        decision["allowed"] = True
        decision["reason"] = "ordinary_change"
        return decision

    return _authorize_same_repo_admin_change(decision, target, api)


def _completed_check_payload(
    receipt: Mapping[str, object],
    *,
    name: str,
    head_sha: str,
    external_id: str,
    allowed: bool,
    details_url: str = "",
) -> dict[str, object]:
    """Build complementary evidence; never the sole required authority."""
    if _sha(head_sha) is None or not name.startswith(CHECK_NAME + "/"):
        raise AuthorityContractError("check cannot identify an exact supported context")
    summary = json.dumps(receipt, ensure_ascii=True, separators=(",", ":"))
    payload: dict[str, object] = {
        "name": name,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "success" if allowed else "failure",
        "external_id": external_id,
        "output": {
            "title": (
                "CI authority context accepted"
                if allowed
                else "CI authority context rejected"
            ),
            "summary": summary,
        },
    }
    if details_url:
        if not details_url.startswith("https://") or len(details_url) > 2048:
            raise AuthorityContractError("details URL must be bounded HTTPS")
        payload["details_url"] = details_url
    return payload


def _base_context_receipt(
    decision: Mapping[str, object], context_base_ref: str
) -> tuple[dict[str, object], bool]:
    active = decision.get("base_ref") == context_base_ref
    allowed = active and decision.get("allowed") is True
    receipt = dict(decision)
    receipt.update(
        {
            "check_context": f"{CHECK_NAME}/{context_base_ref}",
            "context_base_ref": context_base_ref,
            "context_active": active,
            "context_allowed": allowed,
            "context_reason": (
                decision.get("reason") if active else "inactive_base_context"
            ),
        }
    )
    return receipt, allowed


def check_payload(
    decision: Mapping[str, object],
    context_base_ref: str,
    *,
    details_url: str = "",
) -> dict[str, object]:
    """Build one PR base-context check on the exact proposed head."""
    if context_base_ref not in SUPPORTED_BASE_REFS:
        raise AuthorityContractError("unsupported base-specific authority context")
    head_sha = _sha(decision.get("head_sha"))
    number = _positive_int(decision.get("pull_request_number"))
    repository = _repository(decision.get("repository"))
    if head_sha is None or number is None or repository is None:
        raise AuthorityContractError("decision cannot identify an exact PR head")
    receipt, allowed = _base_context_receipt(decision, context_base_ref)
    return _completed_check_payload(
        receipt,
        name=f"{CHECK_NAME}/{context_base_ref}",
        head_sha=head_sha,
        external_id=(
            f"{SCHEMA}:{repository}:{number}:{head_sha}:{context_base_ref}"
        ),
        allowed=allowed,
        details_url=details_url,
    )


def run_pull_request_target(
    payload: object,
    expected_repository: str,
    api: AuthorityApi,
    *,
    details_url: str = "",
) -> tuple[int, dict[str, object], dict[str, object]]:
    """Publish current-base verdict plus terminal invalidation of the other base."""
    decision = evaluate_pull_request_target(payload, expected_repository, api)
    current_base = decision.get("base_ref")
    if current_base in SUPPORTED_BASE_REFS:
        ordered_bases = tuple(
            base_ref
            for base_ref in SUPPORTED_BASE_REFS
            if base_ref != current_base
        ) + (str(current_base),)
    else:
        decision = _reject(decision, "unsupported_base_ref")
        ordered_bases = SUPPORTED_BASE_REFS
    # Invalidate the inactive context first. If publication later fails, the
    # organization required workflow is red and no stale cross-base success can
    # be treated as current by the complementary branch rule.
    checks: list[dict[str, object]] = []
    for base_ref in ordered_bases:
        check = check_payload(decision, base_ref, details_url=details_url)
        try:
            api.create_check(expected_repository, check)
        except Exception as exc:
            raise GitHubApiError(
                "completed base-specific ci-authority check could not be created"
            ) from exc
        checks.append(check)
    active_check = next(
        (check for check in checks if check["name"] == f"{CHECK_NAME}/{current_base}"),
        checks[-1],
    )
    return (0 if decision["allowed"] is True else 1), decision, active_check


# Source support only: activating main requires a separate protected rollout.
NATIVE_QUEUE_TARGET = "codex/merge-queue-pilot"
NATIVE_QUEUE_TARGETS = frozenset({"main", NATIVE_QUEUE_TARGET})
NATIVE_QUEUE_QUERY = """
query($owner: String!, $name: String!, $target: String!, $qualifiedRef: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    ref(qualifiedName: $qualifiedRef) { name target { oid } }
    mergeQueue(branch: $target) {
      configuration {
        mergeMethod maximumEntriesToBuild maximumEntriesToMerge minimumEntriesToMerge
      }
      entries(first: 100) {
        totalCount pageInfo { hasNextPage }
        nodes {
          id position baseCommit { oid }
          headCommit { oid tree { oid } parents(first: 3) { nodes { oid } } }
          pullRequest {
            number state isDraft baseRefName headRefOid headRefName
            baseRepository { nameWithOwner } headRepository { nameWithOwner }
            potentialMergeCommit { tree { oid } parents(first: 3) { nodes { oid } } }
          }
        }
      }
    }
  }
}
"""


NATIVE_PR_RELEASE_QUERY = """query($owner:String!,$name:String!,$number:Int!){
 repository(owner:$owner,name:$name){ nameWithOwner pullRequest(number:$number){
 id number state isDraft headRefOid baseRefName reviewDecision
 baseRef { name branchProtectionRule {
   requiresApprovingReviews requiredApprovingReviewCount requiresCodeOwnerReviews
 } }
 } }
}"""


def validate_native_queue_snapshot(
    data: object, payload: object, expected_repository: str, *,
    execution_sha: str, execution_ref: str,
) -> dict[str, object]:
    """Bind one native pilot group; this grants neither admission nor release.

    The trusted event supplies execution_sha/ref. Candidate jobs separately
    check their actual checkout against this result. No branch-name-derived PR
    number, default-branch alias, incomplete page or native configuration guess.
    """
    def require(condition: object, reason: str) -> None:
        if not condition:
            raise AuthorityContractError(reason)

    def mapping(value: object, reason: str) -> Mapping[str, Any]:
        result = _mapping(value)
        require(result is not None, reason)
        return result  # type: ignore[return-value]

    def oid(value: object) -> str:
        require(type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value),
                "invalid native queue SHA")
        return str(value)

    event = mapping(payload, "missing native event")
    require(_repository(expected_repository) == expected_repository,
            "invalid expected repository")
    require(event.get("action") == "checks_requested", "wrong native action")
    require(mapping(event.get("repository"), "missing event repository").get("full_name")
            == expected_repository, "foreign event repository")
    group = mapping(event.get("merge_group"), "missing native group")
    head, base = oid(group.get("head_sha")), oid(group.get("base_sha"))
    target_ref = group.get("base_ref")
    selected_target = target_ref.removeprefix("refs/heads/") if isinstance(target_ref,str) else ""
    require(target_ref == "refs/heads/" + selected_target and selected_target in NATIVE_QUEUE_TARGETS,
            "native target is not allowlisted")
    ref = group.get("head_ref")
    require(type(ref) is str and ref.startswith("refs/heads/gh-readonly-queue/" + selected_target + "/")
            and _safe_ref(ref) is not None and ref == execution_ref,
            "native event/execution ref differs")
    require(head == execution_sha, "native event/execution SHA differs")
    root = mapping(data, "missing native snapshot")
    repo = mapping(root.get("repository"), "missing API repository")
    require(repo.get("nameWithOwner") == expected_repository, "foreign API repository")
    target = mapping(repo.get("ref"), "selected pilot target is absent")
    require(target.get("name") == selected_target
            and mapping(target.get("target"), "target tip absent").get("oid") == base,
            "group base is not the selected current target tip")
    queue = mapping(repo.get("mergeQueue"), "selected native queue is absent")
    config = mapping(queue.get("configuration"), "native configuration absent")
    require(config.get("mergeMethod") == "SQUASH" and all(
        type(config.get(key)) is int and config[key] == 1
        for key in ("maximumEntriesToBuild", "maximumEntriesToMerge", "minimumEntriesToMerge")
    ), "only serial SQUASH build1/merge1/min1 is supported")
    entries = mapping(queue.get("entries"), "queue inventory absent")
    nodes = entries.get("nodes")
    require(isinstance(nodes, list) and len(nodes) <= 100
            and type(entries.get("totalCount")) is int
            and entries["totalCount"] == len(nodes)
            and mapping(entries.get("pageInfo"), "queue page info absent").get("hasNextPage") is False,
            "native queue inventory incomplete")
    ids: set[str] = set()
    positions: set[int] = set()
    matches = []
    for raw in nodes:
        row = mapping(raw, "malformed queue member")
        entry_id, position = row.get("id"), row.get("position")
        require(type(entry_id) is str and 0 < len(entry_id) <= 256
                and all(32 < ord(c) < 127 for c in entry_id) and entry_id not in ids
                and type(position) is int and position > 0 and position not in positions,
                "duplicate or malformed native entry identity")
        ids.add(entry_id); positions.add(position)
        candidate = row.get("headCommit")
        require(candidate is None or isinstance(candidate, Mapping), "malformed queue head")
        if isinstance(candidate, Mapping) and candidate.get("oid") == head:
            matches.append(row)
    require(len(matches) == 1, "native group has no unique entry")
    entry = matches[0]
    require(entry["position"] == 1, "native group is not first")
    require(mapping(entry.get("baseCommit"), "entry base absent").get("oid") == base,
            "entry base differs")
    candidate = mapping(entry.get("headCommit"), "entry head absent")
    require(mapping(candidate.get("parents"), "group parents absent").get("nodes") == [{"oid": base}],
            "native group is not an exact single-parent squash")
    tree = oid(mapping(candidate.get("tree"), "group tree absent").get("oid"))
    pr = mapping(entry.get("pullRequest"), "native source PR absent")
    number = pr.get("number")
    require(type(number) is int and number > 0 and pr.get("state") == "OPEN"
            and pr.get("isDraft") is False and pr.get("baseRefName") == selected_target,
            "native source PR is not open ready against selected target")
    require(all(mapping(pr.get(key), "PR repository absent").get("nameWithOwner") == expected_repository
                for key in ("baseRepository", "headRepository")), "foreign native source PR")
    require(_safe_ref(pr.get("headRefName")) is not None, "native source branch is missing or malformed")
    source = oid(pr.get("headRefOid"))
    merge = mapping(pr.get("potentialMergeCommit"), "potential PR merge unavailable")
    require(mapping(merge.get("parents"), "PR merge parents absent").get("nodes")
            == [{"oid": base}, {"oid": source}], "potential merge does not bind source/base")
    require(mapping(merge.get("tree"), "PR merge tree absent").get("oid") == tree,
            "potential PR merge and native group trees differ")
    return dict(target_ref=selected_target, queue_entry_id=entry["id"],
                pr_number=number, source_head_sha=source, group_head_sha=head,
                base_sha=base, tree_sha=tree)



def native_protection_contract(rules: object, *, repository_id: int,
                               protected_source_sha: str,
                               protected_source_ref: str = "refs/heads/main",
                               selected_target: str = NATIVE_QUEUE_TARGET) -> dict[str, object]:
    """Validate COMPLETE effective branch-rule rows read for the pilot.

    Caller reads the selected target's active rules through the normal API;
    evaluate/disabled rules never qualify. Source pins are exact immutable
    controller bytes, not a candidate-supplied expected workflow name.
    """
    if (selected_target not in NATIVE_QUEUE_TARGETS or protected_source_ref not in {"refs/heads/main", "refs/heads/" + NATIVE_QUEUE_TARGET}
            or _positive_int(repository_id) is None or _sha(protected_source_sha) is None
            or not isinstance(rules, list) or not 0 < len(rules) <= 1000
            or any(not isinstance(row, dict) for row in rules)):
        raise AuthorityContractError("native effective protection is unavailable")
    queue_rules = [r.get('parameters') for r in rules if r.get('type') == 'merge_queue']
    if len(queue_rules) != 1 or not isinstance(queue_rules[0], dict):
        raise AuthorityContractError("native merge queue rule missing or ambiguous")
    queue = queue_rules[0]
    if (queue.get('merge_method') != 'SQUASH' or queue.get('grouping_strategy') != 'ALLGREEN'
            or any(type(queue.get(key)) is not int or queue[key] != 1 for key in (
                'max_entries_to_build', 'max_entries_to_merge', 'min_entries_to_merge'))):
        raise AuthorityContractError("native protection is not serial single-entry SQUASH")
    required = {'.github/workflows/ci.yml', '.github/workflows/fences.yml',
                '.github/workflows/ci-authority.yml'}
    found = set()
    for rule in rules:
        if rule.get('type') != 'workflows':
            continue
        parameters = rule.get('parameters')
        if (not isinstance(parameters, dict) or parameters.get('do_not_enforce_on_create') is True
                or not isinstance(parameters.get('workflows'), list)):
            raise AuthorityContractError("native workflow protection incomplete")
        for row in parameters['workflows']:
            if not isinstance(row, dict):
                raise AuthorityContractError("native required workflow malformed")
            if row.get('path') in required:
                if (type(row.get('repository_id')) is not int or row['repository_id'] != repository_id
                        or row.get('sha') != protected_source_sha
                        or row.get('ref') not in {None, protected_source_ref, protected_source_ref.removeprefix('refs/heads/')}
                        or row['path'] in found):
                    raise AuthorityContractError("native required workflow source is not uniquely protected")
                found.add(row['path'])
    if found != required:
        raise AuthorityContractError("native integrated proof/fence/authority protection absent")
    # Preserve effective ruleset minima for the policy adapter. Classic rules
    # are read on the same current PR GraphQL snapshot below, never through an
    # additional Administration-token REST endpoint.
    approvals = 0
    codeowners = False
    last_push = False
    for rule in rules:
        if rule.get('type') != 'pull_request':
            continue
        parameters = rule.get('parameters')
        if (not isinstance(parameters, dict)
                or type(parameters.get('required_approving_review_count')) is not int
                or not 0 <= parameters['required_approving_review_count'] <= 100
                or type(parameters.get('require_code_owner_review')) is not bool
                or type(parameters.get('require_last_push_approval')) is not bool):
            raise AuthorityContractError('native effective review protection incomplete')
        approvals = max(approvals, parameters['required_approving_review_count'])
        codeowners = codeowners or parameters['require_code_owner_review']
        last_push = last_push or parameters['require_last_push_approval']
    return dict(target_ref=selected_target, protected_source_sha=protected_source_sha,
                protected_source_ref=protected_source_ref,
                required_workflows=sorted(found),
                required_formal_approvals=approvals,
                requires_code_owner_reviews=codeowners,
                review_decision_required=approvals>0 or codeowners or last_push)


def native_review_facts(protection, current_pr, *, repository, group):
    """Bind already-qualified native enforcement to one fresh PR snapshot.

    This is an in-process contract, not candidate JSON or durable approval.
    The caller authenticates complete effective rules and the GraphQL response.
    Server reviewDecision retains CODEOWNERS/last-push enforcement; this helper
    does not try to recreate GitHub's reviewer-eligibility engine.
    """
    if (not isinstance(protection, dict) or not isinstance(current_pr, dict)
            or not isinstance(group, dict) or _repository(repository) is None
            or group.get('target_ref') not in NATIVE_QUEUE_TARGETS
            or protection.get('target_ref') != group['target_ref']
            or _sha(protection.get('protected_source_sha')) is None
            or protection.get('required_workflows') != sorted([
                '.github/workflows/ci.yml', '.github/workflows/fences.yml',
                '.github/workflows/ci-authority.yml'])
            or type(protection.get('required_formal_approvals')) is not int
            or not 0 <= protection['required_formal_approvals'] <= 100
            or type(protection.get('requires_code_owner_reviews')) is not bool
            or type(protection.get('review_decision_required')) is not bool
            or type(current_pr.get('number')) is not int
            or current_pr['number'] != group.get('pr_number')
            or current_pr.get('headRefOid') != group.get('source_head_sha')
            or _sha(group.get('source_head_sha')) is None
            or current_pr.get('baseRefName') != group['target_ref']
            or 'reviewDecision' not in current_pr
            or current_pr['reviewDecision'] not in {
                None, 'APPROVED', 'REVIEW_REQUIRED', 'CHANGES_REQUESTED'}):
        raise AuthorityContractError('native review facts are missing or misbound')
    base = current_pr.get('baseRef')
    if (not isinstance(base, dict) or base.get('name') != group['target_ref']
            or 'branchProtectionRule' not in base):
        raise AuthorityContractError('native current classic review protection unavailable')
    classic = base['branchProtectionRule']
    approvals = protection['required_formal_approvals']
    codeowners = protection['requires_code_owner_reviews']
    decision_required = protection['review_decision_required']
    if classic is not None:
        if (not isinstance(classic, dict)
                or type(classic.get('requiresApprovingReviews')) is not bool
                or type(classic.get('requiredApprovingReviewCount')) is not int
                or not 0 <= classic['requiredApprovingReviewCount'] <= 100
                or type(classic.get('requiresCodeOwnerReviews')) is not bool
                or (classic['requiresApprovingReviews'] is False
                    and classic['requiredApprovingReviewCount'] != 0)):
            raise AuthorityContractError('native current classic review protection malformed')
        approvals = max(approvals, classic['requiredApprovingReviewCount'])
        codeowners = codeowners or classic['requiresCodeOwnerReviews']
        decision_required = decision_required or classic['requiresApprovingReviews']
    decision_required = decision_required or approvals>0 or codeowners
    decision = current_pr['reviewDecision']
    if decision in {'REVIEW_REQUIRED', 'CHANGES_REQUESTED'} or (
            decision_required and decision != 'APPROVED'):
        raise AuthorityContractError('native server review disposition is not satisfied')
    return dict(repository=repository, pr_number=group['pr_number'],
        head_sha=group['source_head_sha'], target_ref=group['target_ref'],
        protection_source_sha=protection['protected_source_sha'],
        required_formal_approvals=approvals, requires_code_owner_reviews=codeowners,
        review_decision=decision, review_decision_required=decision_required,
        native_enforcement_qualified=True)


def native_source_entry_qualification(loaded, *, expected_head_sha: str,
                                      protection: dict[str, object]) -> None:
    """Only entry may use exact-head success against an older base.

    The caller first authenticates the original artifact/run/definition via the
    incumbent reader. This function cannot authenticate arbitrary JSON. The
    final group gate uses a separate exact-group reader and cannot call this
    predicate to transfer PR green to a group.
    """
    from scripts.ci_semantic_proof import load_semantic_evidence, semantic_gate_verdict
    if (not isinstance(protection, dict) or protection.get('target_ref') not in NATIVE_QUEUE_TARGETS
            or _sha(protection.get('protected_source_sha')) is None
            or protection.get('required_workflows') != sorted([
                '.github/workflows/ci.yml', '.github/workflows/fences.yml', '.github/workflows/ci-authority.yml'])):
        raise AuthorityContractError("native entry lacks verified integrated protection")
    document = getattr(loaded, 'evidence', None)
    if getattr(loaded, 'mode', None) != 'semantic' or not isinstance(document, dict):
        raise AuthorityContractError("native entry lacks authenticated original source proof")
    validated = load_semantic_evidence(document, advertised=True,
        expected_subject_head_sha=expected_head_sha, expected_role='pr_head', expected_workflow='ci')
    # The exact original must be wholly clear. No inherited-red waiver is entry
    # authority; this does not compare its base with current mutable target.
    if (not semantic_gate_verdict(validated.evidence).clear
            or any(step.get('classification') != 'passed' for job in document['jobs'] for step in job['steps'])):
        raise AuthorityContractError("native source original is not wholly passed")


def native_release_authorization(pull, comments, reviews, *, group,
                                 review_decision, issuer_permission,
                                 comments_complete, reviews_complete, expected_repository,
                                 review_policy=None, issuer_login=None, producer_intent=None):
    """Current release disposition; never cached at enqueue or inferred from CI.

    The read adapter supplies complete original server rows and the permission
    of the server-recorded arm/enqueue actor. It preserves the incumbent hold
    grammar and current non-author review requirement. Target rules independently
    enforce their own additional counts/code-owner/security requirements.
    """
    from scripts.merge_on_green import recorded_hold, label_names
    if (not isinstance(pull,dict) or not isinstance(group,dict)
            or comments_complete is not True or reviews_complete is not True
            or not isinstance(comments,list) or not isinstance(reviews,list)
            or len(comments)>1000 or len(reviews)>1000
            or any(not isinstance(c,dict) or type(c.get('id')) is not int or c['id']<=0
                   or not isinstance(c.get('body'),str) or not isinstance(c.get('user'),dict)
                   for c in comments)
            or len({c['id'] for c in comments})!=len(comments)):
        raise AuthorityContractError('native current release custody incomplete')
    producer_authorized=(isinstance(producer_intent,dict)
        and producer_intent.get('kind')=='github_actions_producer'
        and producer_intent.get('repository')==expected_repository
        and producer_intent.get('pr_number')==group.get('pr_number')
        and producer_intent.get('head_sha')==group.get('source_head_sha')
        and producer_intent.get('target_ref')==group.get('target_ref')
        and producer_intent.get('actor_login')==issuer_login=='github-actions[bot]'
        and all(type(producer_intent.get(k)) is int and producer_intent[k]>0 for k in
            ('repository_id','pr_number','arm_event_id','actor_id','app_id','producer_run_id','producer_run_attempt'))
        and isinstance(producer_intent.get('producer_generation'),str)
        and re.fullmatch('[0-9a-f]{12}',producer_intent['producer_generation']) is not None)
    if (type(pull.get('number')) is not int or pull.get('number')!=group['pr_number'] or pull.get('state')!='open'
            or pull.get('draft') is not False or pull.get('merged') is not False
            or (pull.get('head') or {}).get('sha')!=group['source_head_sha']
            or group.get('target_ref') not in NATIVE_QUEUE_TARGETS
            or (pull.get('base') or {}).get('ref')!=group['target_ref']
            or _repository(expected_repository) is None
            or any(((pull.get(key) or {}).get('repo') or {}).get('full_name')!=expected_repository for key in ('head','base'))
            or 'merge-on-green' not in label_names(pull) or 'merge-blocked' in label_names(pull)
            or (issuer_permission not in {'write','maintain','admin'} and not producer_authorized)):
        raise AuthorityContractError('native current source/intent/issuer is not authorized')
    if not isinstance(pull.get('body'),str) or not isinstance(pull.get('title'),str):
        raise AuthorityContractError('native current hold text unavailable')
    if recorded_hold(pull['body'],comments,pull['title']):
        raise AuthorityContractError('native current source is under a recorded hold')
    author=(pull.get('user') or {}).get('login')
    if (not _safe_login(author) or _safe_login(issuer_login) is None
            or not isinstance(review_policy,dict)
            or review_policy.get('disposition')!='QUALIFIED'
            or review_policy.get('origin')!='AUTOMATIC_POLICY'
            or review_policy.get('repository')!=expected_repository
            or type(review_policy.get('pull_number')) is not int
            or review_policy['pull_number']!=group['pr_number']
            or review_policy.get('head_sha')!=group['source_head_sha']
            or review_policy.get('target_ref')!=group['target_ref']
            or type(review_policy.get('native_review_decision_required')) is not bool):
        raise AuthorityContractError('native protected policy qualification missing or misbound')
    for kind in ('independent_assessments','formal_non_author_approvals'):
        required=review_policy.get('required_'+kind)
        accepted=review_policy.get('accepted_'+kind)
        if type(required) is not int or type(accepted) is not int or not 0<=required<=accepted:
            raise AuthorityContractError('native protected policy review requirement unsatisfied')
    if (review_decision not in {None,'APPROVED'}
            or review_policy['native_review_decision_required'] and review_decision!='APPROVED'):
        raise AuthorityContractError('native current server review disposition unsatisfied')
    latest={}; seen=set()
    for row in reviews:
        if (not isinstance(row,dict) or _positive_int(row.get('id')) is None or row['id'] in seen
                or not isinstance(row.get('user'),dict) or not _safe_login(row['user'].get('login'))
                or row.get('state') not in {'APPROVED','CHANGES_REQUESTED','COMMENTED','DISMISSED','PENDING'}):
            raise AuthorityContractError('native original review inventory incomplete')
        seen.add(row['id'])
        # Comment-only reviews do not dismiss a prior request/approval. An
        # actual DISMISSED row supersedes that same review's disposition.
        if row['state'] in {'COMMENTED','PENDING'}:continue
        actor=row['user']['login'].lower()
        if actor not in latest or row['id']>latest[actor]['id']:latest[actor]=row
    if any(row['state']=='CHANGES_REQUESTED' for row in latest.values()):
        raise AuthorityContractError('native current review requests changes')
    if any(review_policy['required_'+kind]>0 for kind in (
            'independent_assessments','formal_non_author_approvals')):
        contributors=review_policy.get('source_contributors')
        reviewers=review_policy.get('qualifying_reviewer_logins')
        if (not isinstance(contributors,list) or not contributors
                or any(_safe_login(x) is None for x in contributors)
                or not isinstance(reviewers,list) or not reviewers
                or any(_safe_login(x) is None for x in reviewers)
                or len({x.lower() for x in reviewers})!=len(reviewers)
                or any(x.lower() in {author.lower(),*(c.lower() for c in contributors)} for x in reviewers)):
            raise AuthorityContractError('native policy source-independent review binding unavailable')


def native_final_evidence(loaded, *, admission_record, run_id, attempt):
    """No PR/main/cross-run proof may finalize a native queue original."""
    from scripts import ci_proof_admission as admission
    from scripts.ci_semantic_proof import load_semantic_evidence, semantic_gate_verdict
    if (not isinstance(admission_record,admission.NativeAdmission)
            or admission_record.run_id!=run_id or admission_record.run_attempt!=attempt
            or getattr(loaded,'mode',None)!='semantic'):
        raise AuthorityContractError('native final original admission differs')
    expected=admission.native_execution_identity(admission_record)
    checked=load_semantic_evidence(loaded.evidence,advertised=True,
        expected_run_id=run_id,expected_role='merge_group',expected_event='merge_group',expected_workflow='ci',
        expected_tested_tree_sha=expected['group_head_sha'],expected_subject_head_sha=expected['source_head_sha'],
        expected_base_sha=expected['base_sha'],expected_admission_generation=admission_record.generation,
        expected_native_group=expected)
    if not semantic_gate_verdict(checked.evidence).clear:
        raise AuthorityContractError('native final group execution is incomplete or failed')

def evaluate_merge_group(payload: object, expected_repository: str) -> dict[str, object]:
    """Validate the queue event consumed by the trusted-default-branch job."""
    event = _mapping(payload)
    repository = None if event is None else _mapping(event.get("repository"))
    group = None if event is None else _mapping(event.get("merge_group"))
    raw_base_ref = None if group is None else group.get("base_ref")
    prefix = "refs/heads/"
    base_ref = (
        _safe_ref(raw_base_ref[len(prefix) :])
        if type(raw_base_ref) is str and raw_base_ref.startswith(prefix)
        else None
    )
    if (
        event is None
        or event.get("action") != "checks_requested"
        or repository is None
        or repository.get("full_name") != _repository(expected_repository)
        or group is None
        or _sha(group.get("head_sha")) is None
        or _sha(group.get("base_sha")) is None
        or base_ref not in SUPPORTED_BASE_REFS
    ):
        raise AuthorityContractError("merge_group event identity is missing or malformed")
    return {
        "schema": SCHEMA,
        "event": "merge_group",
        "repository": expected_repository,
        "head_sha": group["head_sha"],
        "base_sha": group["base_sha"],
        "base_ref": base_ref,
        "base_repository": expected_repository,
        "allowed": True,
        "reason": "trusted_default_branch_merge_group",
    }


def run_merge_group(
    payload: object,
    expected_repository: str,
    api: AuthorityApi,
    *,
    details_url: str = "",
) -> tuple[int, dict[str, object], dict[str, object]]:
    """Legacy envelope-only publication cannot grant native final authority."""
    raise AuthorityContractError("native group requires authenticated membership and final integrated proof")


def _retry_after_seconds(headers: Any) -> float | None:
    """Read a server-provided retry hint, tolerating a missing header object.

    ``urllib`` hands back an ``email.message.Message`` whose ``.get`` is
    already case-insensitive, so no case-folding is required here.
    """
    if headers is None:
        return None
    retry_after = headers.get("Retry-After")
    if retry_after is not None:
        try:
            seconds = float(int(str(retry_after).strip()))
        except (TypeError, ValueError):
            pass
        else:
            return seconds if seconds >= 0 else None
    if headers.get("x-ratelimit-remaining") == "0":
        reset = headers.get("x-ratelimit-reset")
        try:
            seconds = float(reset) - time.time()
        except (TypeError, ValueError):
            return None
        return seconds if seconds >= 0 else None
    return None


def _api_failure_message(method: str, status: int | None) -> str:
    if status is None:
        return f"GitHub {method} request failed"
    return f"GitHub {method} request failed (HTTP {status})"


def _classify_api_exception(method: str, exc: BaseException) -> GitHubApiError:
    """Turn a raw urllib failure into a fail-closed, retry-aware error.

    Retryable means transient only: timeouts and 408/429/5xx are retried; a
    403 is retried solely when the response itself says it is a rate limit
    (header or body), never treated as a permission verdict by default; every
    other 4xx (401, 403 without a rate-limit signal, 404, ...) is a genuine
    rejection and must never be retried.
    """
    if isinstance(exc, urllib.error.HTTPError):
        status = getattr(exc, "status", None) or getattr(exc, "code", None)
        headers = getattr(exc, "headers", None)
        retry_after = _retry_after_seconds(headers)
        if status == 429:
            return GitHubApiError(
                _api_failure_message(method, status),
                kind="rate_limited",
                status=status,
                retryable=True,
                retry_after=retry_after,
            )
        if status == 403:
            rate_limited = retry_after is not None
            if not rate_limited:
                try:
                    body = exc.read(2048)
                    text = body.decode("utf-8", errors="replace")
                except Exception:
                    text = ""
                if "rate limit" in text.lower():
                    rate_limited = True
            if rate_limited:
                return GitHubApiError(
                    _api_failure_message(method, status),
                    kind="rate_limited",
                    status=status,
                    retryable=True,
                    retry_after=retry_after,
                )
            return GitHubApiError(
                _api_failure_message(method, status),
                kind="rejected",
                status=status,
                retryable=False,
            )
        if status == 408:
            return GitHubApiError(
                _api_failure_message(method, status),
                kind="timeout",
                status=status,
                retryable=True,
                retry_after=retry_after,
            )
        if status in RETRYABLE_HTTP_STATUSES:
            return GitHubApiError(
                _api_failure_message(method, status),
                kind="unavailable",
                status=status,
                retryable=True,
                retry_after=retry_after,
            )
        return GitHubApiError(
            _api_failure_message(method, status),
            kind="rejected",
            status=status,
            retryable=False,
        )
    if isinstance(exc, TimeoutError) or (
        isinstance(exc, urllib.error.URLError)
        and isinstance(exc.reason, TimeoutError)
    ):
        return GitHubApiError(
            _api_failure_message(method, None), kind="timeout", retryable=True
        )
    return GitHubApiError(
        _api_failure_message(method, None), kind="unavailable", retryable=True
    )


class GitHubApi:
    """Small REST client exposing only the calls required by this controller."""

    def __init__(
        self,
        api_url: str,
        token: str,
        *,
        sleep=time.sleep,
        jitter=random.random,
        retry_attempts: int = API_RETRY_ATTEMPTS,
        retry_budget: float = API_RETRY_TOTAL_BUDGET_SECONDS,
    ) -> None:
        if not api_url.startswith("https://"):
            raise GitHubApiError("GITHUB_API_URL must use https")
        if not token:
            raise GitHubApiError("GITHUB_TOKEN is absent")
        self.api_url = api_url.rstrip("/")
        self.token = token
        self._sleep = sleep
        self._jitter = jitter
        self._retry_attempts = retry_attempts
        self._retry_budget = retry_budget

    @staticmethod
    def _repo_path(repository: str) -> str:
        trusted = _repository(repository)
        if trusted is None:
            raise GitHubApiError("repository must be owner/name")
        owner, name = trusted.split("/", 1)
        return "/repos/{}/{}".format(
            urllib.parse.quote(owner, safe=""),
            urllib.parse.quote(name, safe=""),
        )

    def _attempt_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
        expected_status: int,
    ) -> object:
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "macro-ci-authority",
        }
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.api_url + path,
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(
                request, timeout=API_TIMEOUT_SECONDS
            ) as response:
                status = response.status
                response_body = response.read(4_000_001)
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise _classify_api_exception(method, exc) from exc
        if status != expected_status:
            raise GitHubApiError(
                f"GitHub {method} returned HTTP {status}, expected {expected_status}"
            )
        if len(response_body) > 4_000_000:
            raise GitHubApiError("GitHub response exceeds size bound")
        try:
            return json.loads(response_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubApiError("GitHub response is not valid JSON") from exc

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
        expected_status: int,
    ) -> object:
        """Retry a bounded number of times on transient GET failures only.

        POST is never retried here: ``create_check`` is not idempotent, and a
        retried POST that actually succeeded server-side would publish a
        duplicate check run on the PR head.
        """
        remaining_budget = self._retry_budget
        last_exc: GitHubApiError | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                return self._attempt_json(
                    method, path, payload=payload, expected_status=expected_status
                )
            except GitHubApiError as exc:
                last_exc = exc
                if (
                    method != "GET"
                    or not exc.retryable
                    or attempt >= self._retry_attempts
                ):
                    raise
                if exc.retry_after is not None:
                    delay = (
                        min(max(exc.retry_after, 0.0), API_RETRY_MAX_DELAY_SECONDS)
                        + self._jitter() * API_RETRY_BASE_DELAY_SECONDS
                    )
                else:
                    base = min(
                        API_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
                        API_RETRY_MAX_DELAY_SECONDS,
                    )
                    delay = base * (0.5 + 0.5 * self._jitter())
                if delay > remaining_budget:
                    raise
                print(
                    f"::warning title=ci-authority-api-retry::"
                    f"{method} {path} attempt {attempt} failed "
                    f"({exc.kind}); retrying in {delay:.2f}s",
                    flush=True,
                )
                self._sleep(delay)
                remaining_budget -= delay
        assert last_exc is not None  # pragma: no cover - loop always raises or returns
        raise last_exc

    def get_pull(self, repository: str, number: int) -> object:
        return self._request_json(
            "GET",
            f"{self._repo_path(repository)}/pulls/{number}",
            expected_status=200,
        )

    def list_pull_files(
        self, repository: str, number: int, expected_count: int
    ) -> object:
        if not (0 <= expected_count <= MAX_CHANGED_FILES):
            raise GitHubApiError("changed-file count exceeds API proof ceiling")
        entries: list[object] = []
        page_count = max(1, (expected_count + 99) // 100)
        for page in range(1, page_count + 1):
            response = self._request_json(
                "GET",
                f"{self._repo_path(repository)}/pulls/{number}/files"
                f"?per_page=100&page={page}",
                expected_status=200,
            )
            if not isinstance(response, list):
                raise GitHubApiError("pull files page is not an array")
            if len(response) > 100:
                raise GitHubApiError("pull files page exceeds per_page bound")
            entries.extend(response)
            if len(response) < 100:
                break
        if len(entries) != expected_count:
            raise GitHubApiError("paginated pull files do not match changed_files")
        return entries

    def get_collaborator_permission(self, repository: str, login: str) -> object:
        safe_login = _safe_login(login)
        if safe_login is None:
            raise GitHubApiError("collaborator login is malformed")
        return self._request_json(
            "GET",
            f"{self._repo_path(repository)}/collaborators/"
            f"{urllib.parse.quote(safe_login, safe='')}/permission",
            expected_status=200,
        )

    def create_check(self, repository: str, payload: Mapping[str, object]) -> object:
        return self._request_json(
            "POST",
            f"{self._repo_path(repository)}/check-runs",
            payload=payload,
            expected_status=201,
        )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityContractError("cannot read workflow event JSON") from exc


def _details_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "")
    repository = _repository(os.environ.get("GITHUB_REPOSITORY", ""))
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if (
        not server.startswith("https://")
        or repository is None
        or not run_id.isdigit()
    ):
        return ""
    return f"{server.rstrip('/')}/{repository}/actions/runs/{run_id}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--event", type=Path, default=Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    )
    parser.add_argument("--native-membership", action="store_true")
    parser.add_argument("--native-final", action="store_true")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-branch-output", type=Path)
    args = parser.parse_args(argv)
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    try:
        payload = _read_json(args.event)
        event = _mapping(payload)
        if args.native_membership or args.native_final:
            from scripts.resolve_ci_pr_admission import resolve_native, ResolutionError, _integer
            workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF", "")
            prefix = repository + "/.github/workflows/"
            workflow_file = workflow_ref[len(prefix):].split("@", 1)[0] if workflow_ref.startswith(prefix) else ""
            if args.native_membership == args.native_final:
                raise AuthorityContractError("native reader mode is ambiguous")
            if args.native_membership and args.output is None:
                raise AuthorityContractError("native membership output destination missing")
            evidence = None
            if args.native_final:
                if workflow_file != "ci.yml" or args.evidence is None:
                    raise AuthorityContractError("native final evidence/caller missing")
                from scripts.ci_semantic_proof import _strict_json_load
                evidence = _strict_json_load(args.evidence)
            try:
                group = resolve_native(payload, repository=repository,
                    repository_id=_integer(os.environ.get("GITHUB_REPOSITORY_ID", "")),
                    run_id=_integer(os.environ.get("GITHUB_RUN_ID", "")),
                    run_attempt=_integer(os.environ.get("GITHUB_RUN_ATTEMPT", "")),
                    workflow_sha=os.environ.get("GITHUB_WORKFLOW_SHA", ""),
                    workflow_ref=workflow_ref, event_sha=os.environ.get("GITHUB_SHA", ""),
                    event_name=os.environ.get("GITHUB_EVENT_NAME", ""), ref=os.environ.get("GITHUB_REF", ""),
                    token=os.environ.get("GITHUB_TOKEN", ""), membership_only=args.native_membership, workflow_file=workflow_file, include_source_branch=True, final_evidence=evidence)
            except ResolutionError as exc:
                raise AuthorityContractError("native membership is incomplete") from exc
            if args.native_final:
                return 0
            if args.source_branch_output is not None:
                if args.source_branch_output == args.output:
                    raise AuthorityContractError("native sidecar destinations overlap")
                args.source_branch_output.write_text(group["source_branch"] + "\n", encoding="utf-8")
            args.output.write_text(json.dumps(group["group"], sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            return 0
        api = GitHubApi(
            os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            os.environ.get("GITHUB_TOKEN", ""),
        )
        if event is not None and event.get("merge_group") is not None:
            exit_code, decision, _check = run_merge_group(
                payload,
                repository,
                api,
                details_url=_details_url(),
            )
        else:
            exit_code, decision, _check = run_pull_request_target(
                payload,
                repository,
                api,
                details_url=_details_url(),
            )
    except (AuthorityContractError, GitHubApiError, OSError, ValueError):
        print(
            json.dumps(
                {"schema": SCHEMA, "allowed": False, "reason": "controller_error"},
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(decision, ensure_ascii=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
