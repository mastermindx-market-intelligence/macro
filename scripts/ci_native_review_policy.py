"""CI native review policy qualification adapter (read-only, fail-closed).

Binds the canonical, verified ``control_plane/github_review_risk_*`` policy
modules of ``mastermindx-market-intelligence/Mastermind@master`` to the fixed
production repository and combines the canonical machine risk counts with the
repository's actual native GitHub requirements and the PR's authenticated
review inventory into one qualification result for the incumbent CI owner.

This helper is NOT standalone release authorization. It never approves, merges,
arms, enrolls, publishes or writes. The assigning core retains holds, source
binding, arm/head/target checks and the genuine non-author protected final
release; ``native_review_decision_required`` tells the core when its actual
GraphQL ``reviewDecision`` check must still be enforced.

Callable contract fixed by core::

    qualify_native_review(repository, pull, reviews, issuer_login, *, get, now,
                          native_facts)

``get`` returns parsed JSON on HTTP200 or raises NativeReviewReadError(code,body),
through the existing authenticated api.github.com reader/deadline/API budget.
Allowed absolute API paths are only the canonical Mastermind branches/master,
Contents control_plane/github_review_risk_{policy,source,dispatch}.py?ref=<same
40hex protected revision>, and the bound Macro pulls/<n>, pulls/<n>/files or
commits?per_page=100&page=N. No origin URL, download_url, admin/protection read,
foreign PR, new credential or HTTP client. Core constructs native_facts in the
same call from effective rules and same-PR GraphQL branch protection; it owns
complete enforcement reads, current source/rules/final-PR fences and actual
native reviewDecision semantics. This in-process port is not candidate JSON.

No token, credential or network client is passed to the policy child process: the verified
module sources are executed by ``sys.executable -I -B`` in a fresh isolated
child with a minimal non-secret environment and bounded wall time, via a fixed
bootstrap that registers an empty ``control_plane`` namespace and then the
three actual modules in dependency order, unmodified.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import types
import urllib.parse
from datetime import datetime, timezone

CANONICAL_POLICY_REPOSITORY = "mastermindx-market-intelligence/Mastermind"
CANONICAL_POLICY_BRANCH = "master"
CANONICAL_POLICY_PATHS = (
    "control_plane/github_review_risk_policy.py",
    "control_plane/github_review_risk_source.py",
    "control_plane/github_review_risk_dispatch.py",
)
PRODUCTION_REPOSITORY = "mastermindx-market-intelligence/macro"
ORIGIN_AUTOMATIC_POLICY = "AUTOMATIC_POLICY"

PAGE_SIZE = 100
MAX_FILES = 256
MAX_FILE_PAGES = 3
MAX_RULES_PAGES = 10
MAX_COMMIT_PAGES = 5
MAX_POLICY_MODULE_BYTES = 262_144
MAX_REVIEW_ROWS = 1_000
CHILD_TIMEOUT_SECONDS = 60.0

_REVIEW_STATES = frozenset({
    "APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING",
})
_REAL_DISPOSITIONS = frozenset({"APPROVED", "CHANGES_REQUESTED", "DISMISSED"})
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_NOREPLY_NEW = re.compile(r"^(\d+)\+([A-Za-z0-9-]{1,39})@users\.noreply\.github\.com$")
_NOREPLY_OLD = re.compile(r"^([A-Za-z0-9-]{1,39})@users\.noreply\.github\.com$")

API_BASE_HINT = "https://api.github.com"
UNSIGNED_ASSESSMENT_NOTE = (
    "accepted counts derive from the authenticated server review channel only; "
    "the unsigned typed canonical assessment is not a completed or signed "
    "technical review"
)


class NativeReviewPolicyError(Exception):
    """Fail-closed qualification refusal with a safe reason and known counts."""

    code = "NATIVE_REVIEW_POLICY_FAIL_CLOSED"

    def __init__(self, reason: str, **details) -> None:
        safe = {}
        for key, value in details.items():
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                safe[key] = repr(value)[:200]
            else:
                safe[key] = value
        self.reason = reason if type(reason) is str else self.code
        self.details = safe
        super().__init__(f"{self.code}:{self.reason}:{json.dumps(safe, sort_keys=True)}")

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "reason": self.reason,
            "details": self.details,
        }


class NativeReviewReadError(NativeReviewPolicyError):
    """HOLD that preserves the raw HTTP outcome for the incumbent caller."""

    code = "NATIVE_REVIEW_READ_REFUSED"

    def __init__(self, status_code, response_json, *, reason="HTTP_READ_UNAVAILABLE") -> None:
        if type(status_code) is not int or not 100 <= status_code <= 599:
            raise NativeReviewPolicyError("HTTP_STATUS_MALFORMED")
        super().__init__(reason, status_code=status_code)
        self.status_code = status_code
        self.response_json = response_json


class TechnicalProvenanceUnavailable(NativeReviewPolicyError):
    """Technical assessment is owed but no authenticated valid channel exists."""

    code = "TECHNICAL_PROVENANCE_UNAVAILABLE"


TECHNICAL_PROVENANCE_UNAVAILABLE = TechnicalProvenanceUnavailable


def _safe_body(value, limit: int = 600) -> object:
    """Bounded, secret-free echo of an HTTP body for diagnosis."""
    try:
        text = json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        text = repr(value)
    if len(text) > limit:
        text = text[:limit] + "...[truncated]"
    return text


def _fail(reason: str, **details) -> None:
    raise NativeReviewPolicyError(reason, **details)


def _read_fail(reason: str, status_code, response_json) -> None:
    raise NativeReviewReadError(status_code, response_json, reason=reason)


def _get_json(get, path: str, label: str) -> object:
    value = get(path)
    if type(value) not in (dict, list):
        _fail("READ_CALLBACK_MALFORMED_RESULT", route=path)
    return value


def _resolve_now(now) -> dict:
    """Validate ``now`` (epoch / aware datetime / clock callable) once, audit only.

    The observation is recorded for diagnosis. No review expiry or staleness is
    ever invented from it.
    """
    if type(now) is bool:
        _fail("NOW_MALFORMED", got="bool")
    if type(now) is int or type(now) is float:
        value = float(now)
        if not math.isfinite(value):
            _fail("NOW_MALFORMED", got="nonfinite")
        return {
            "source": "epoch",
            "epoch": value,
            "utc": datetime.fromtimestamp(value, tz=timezone.utc).isoformat(),
        }
    if isinstance(now, datetime):
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            _fail("NOW_MALFORMED", got="naive_datetime")
        return {"source": "datetime", "epoch": now.timestamp(), "utc": now.isoformat()}
    if callable(now):
        produced = now()
        if type(produced) is bool:
            _fail("NOW_CLOCK_MALFORMED", got="bool")
        if not isinstance(produced, datetime) and type(produced) not in (int, float):
            _fail("NOW_CLOCK_MALFORMED", got=type(produced).__name__)
        if isinstance(produced, datetime):
            if produced.tzinfo is None or produced.tzinfo.utcoffset(produced) is None:
                _fail("NOW_CLOCK_MALFORMED", got="naive_datetime")
            return {
                "source": "clock_callable",
                "epoch": produced.timestamp(),
                "utc": produced.isoformat(),
            }
        value = float(produced)
        if not math.isfinite(value):
            _fail("NOW_CLOCK_MALFORMED", got="nonfinite")
        return {
            "source": "clock_callable",
            "epoch": value,
            "utc": datetime.fromtimestamp(value, tz=timezone.utc).isoformat(),
        }
    _fail("NOW_MALFORMED", got=type(now).__name__)


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def _read_canonical_branch(get) -> str:
    """Read the canonical policy branch head; 40hex + protected or HOLD."""
    path = f"/repos/{CANONICAL_POLICY_REPOSITORY}/branches/{CANONICAL_POLICY_BRANCH}"
    body = _get_json(get, path, "POLICY_BRANCH")
    if type(body) is not dict:
        _read_fail("POLICY_BRANCH_MALFORMED", 200, body)
    if body.get("name") != CANONICAL_POLICY_BRANCH or body.get("protected") is not True:
        _fail("POLICY_BRANCH_NOT_PROTECTED", route=path)
    commit = body.get("commit")
    if type(commit) is not dict:
        _fail("POLICY_BRANCH_COMMIT_MALFORMED", route=path)
    sha = commit.get("sha")
    if type(sha) is not str or _SHA40.fullmatch(sha) is None:
        _fail("POLICY_BRANCH_SHA_MALFORMED", route=path)
    return sha


def _read_policy_modules(get, revision: str) -> list:
    """Fetch exactly the three canonical modules pinned to ``revision``."""
    modules = []
    for policy_path in CANONICAL_POLICY_PATHS:
        query = urllib.parse.urlencode({"ref": revision})
        route = f"/repos/{CANONICAL_POLICY_REPOSITORY}/contents/{policy_path}?{query}"
        body = _get_json(get, route, "POLICY_MODULE")
        if type(body) is not dict:
            _read_fail("POLICY_MODULE_MALFORMED", 200, body)
        if body.get("type") != "file" or body.get("path") != policy_path:
            _fail("POLICY_MODULE_IDENTITY_MISMATCH", route=route)
        if body.get("encoding") != "base64":
            _fail("POLICY_MODULE_ENCODING_UNSUPPORTED", route=route, encoding=body.get("encoding"))
        size = body.get("size")
        if type(size) is not int or type(size) is bool or size < 1 or size > MAX_POLICY_MODULE_BYTES:
            _fail("POLICY_MODULE_SIZE_OUT_OF_BOUNDS", route=route, size=repr(size)[:40])
        content = body.get("content")
        if type(content) is not str or not content:
            _fail("POLICY_MODULE_CONTENT_MALFORMED", route=route)
        try:
            data = base64.b64decode("".join(content.split()), validate=True)
        except (binascii.Error, ValueError):
            _fail("POLICY_MODULE_BASE64_INVALID", route=route)
        if len(data) != size:
            _fail("POLICY_MODULE_SIZE_MISMATCH", route=route, declared=size, decoded=len(data))
        if body.get("sha") != _git_blob_sha1(data):
            _fail("POLICY_MODULE_BLOB_MISMATCH", route=route, expected=body.get("sha"))
        modules.append({
            "path": policy_path,
            "source": data.decode("utf-8"),
            "blob_sha1": body.get("sha"),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": size,
        })
    return modules


def _pull_identity(repository: str, pull) -> dict:
    """Strictly validate the supplied current REST pull; no prose/labels read."""
    if type(pull) is not dict:
        _fail("PULL_IDENTITY_MALFORMED", got=type(pull).__name__)
    number = pull.get("number")
    if type(number) is not int or type(number) is bool or number <= 0:
        _fail("PULL_NUMBER_MALFORMED", got=repr(number)[:40])
    state = pull.get("state")
    if state != "open":
        _fail("PR_NOT_OPEN", state=repr(state)[:40])
    draft = pull.get("draft")
    if type(draft) is not bool:
        _fail("PULL_DRAFT_MALFORMED", got=repr(draft)[:40])
    user = pull.get("user")
    if type(user) is not dict or type(user.get("login")) is not str or not user.get("login"):
        _fail("PULL_AUTHOR_MALFORMED")
    head = pull.get("head")
    base = pull.get("base")
    for name, node in (("head", head), ("base", base)):
        if type(node) is not dict:
            _fail(f"PULL_{name.upper()}_MALFORMED")
        ref = node.get("ref")
        if type(ref) is not str or not ref:
            _fail(f"PULL_{name.upper()}_REF_MALFORMED")
        sha = node.get("sha")
        if type(sha) is not str or _SHA40.fullmatch(sha) is None:
            _fail(f"PULL_{name.upper()}_SHA_MALFORMED")
        repo_node = node.get("repo")
        if type(repo_node) is not dict:
            _fail(f"PULL_{name.upper()}_REPO_MALFORMED")
        full_name = repo_node.get("full_name")
        if full_name != repository:
            _fail("PR_FORK_OR_FOREIGN_REPOSITORY", side=name, repository=repr(full_name)[:120])
    for name in ("additions", "deletions", "changed_files"):
        value = pull.get(name)
        if type(value) is not int or type(value) is bool or value < 0:
            _fail("PULL_STATS_MALFORMED", field=name, got=repr(value)[:40])
    if pull["changed_files"] < 1 or pull["changed_files"] > MAX_FILES:
        _fail("PR_FILES_OUT_OF_SCOPE", changed_files=pull["changed_files"])
    return {
        "number": number,
        "head_sha": head["sha"],
        "base_ref": base["ref"],
        "author_login": user["login"],
        "draft": draft,
    }


def _fetch_file_pages(get, repository: str, number: int, changed_files: int) -> list:
    """Fetch the complete bounded file census; shape checks left to canonical code."""
    pages = []
    remaining = changed_files
    page = 1
    while remaining > 0:
        if page > MAX_FILE_PAGES:
            _fail("PR_FILE_PAGES_OUT_OF_BOUNDS", changed_files=changed_files)
        route = (f"/repos/{repository}/pulls/{number}/files"
                 f"?per_page={PAGE_SIZE}&page={page}")
        body = _get_json(get, route, "PR_FILES")
        if type(body) is not list or len(body) > PAGE_SIZE:
            _read_fail("PR_FILES_MALFORMED", 200, body)
        pages.append(body)
        # A short page is end-of-list or truncation; the canonical collector
        # classifies the inconsistency (never the caller guessing to zero).
        if len(body) < min(PAGE_SIZE, remaining):
            break
        remaining -= len(body)
        page += 1
    return pages


def _fetch_final_pull(get, repository: str, number: int) -> dict:
    route = f"/repos/{repository}/pulls/{number}"
    body = _get_json(get, route, "PR_FINAL")
    if type(body) is not dict:
        _read_fail("PR_FINAL_MALFORMED", 200, body)
    return body


# --- isolated policy child -------------------------------------------------
#
# The fixed bootstrap runs under `sys.executable -I -B -c` with a minimal
# non-secret environment: it registers an empty `control_plane` namespace and
# then executes the three verified module sources in dependency order
# (policy -> source -> dispatch), unmodified, so no preloaded module can
# shadow them. No token or network client is passed into the child.

_CHILD_BOOTSTRAP = """import importlib.util, json, sys, types
_pkg = types.ModuleType("control_plane")
_pkg.__path__ = []
sys.modules["control_plane"] = _pkg
_spec = importlib.util.spec_from_file_location("ci_native_review_policy", sys.argv[1])
_mod = importlib.util.module_from_spec(_spec)
sys.modules["ci_native_review_policy"] = _mod
_spec.loader.exec_module(_mod)
_payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
sys.stdout.write(json.dumps(_mod.child_evaluate(_payload)))
"""

_CHILD_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C.UTF-8",
    "PYTHONHASHSEED": "0",
}


def child_evaluate(payload: dict) -> dict:
    """Child-side entry: register canonical modules, assess, dispatch."""
    try:
        modules = payload.get("modules")
        if type(modules) is not dict or set(modules) != set(CANONICAL_POLICY_PATHS):
            return {"ok": False, "code": "CHILD_MODULE_PAYLOAD_MALFORMED"}
        for policy_path in CANONICAL_POLICY_PATHS:
            source = modules[policy_path]
            if type(source) is not str or not source:
                return {"ok": False, "code": "CHILD_MODULE_SOURCE_MALFORMED"}
            name = "control_plane." + policy_path.rsplit("/", 1)[-1][:-3]
            module = types.ModuleType(name)
            module.__file__ = policy_path
            sys.modules[name] = module
            try:
                exec(compile(source, policy_path, "exec"), module.__dict__)
            except Exception as exc:  # noqa: BLE001 - structured code only
                return {"ok": False, "code": "CHILD_MODULE_EXEC_FAILED",
                        "exception": type(exc).__name__}
        from control_plane.github_review_risk_source import (  # noqa: E501
            RiskSourceUnavailable,
            SourceFile,
            SourcePR,
            assess_current_pr_risk_with_final,
        )
        from control_plane.github_review_risk_dispatch import (  # noqa: E501
            ReviewOrigin,
            ReviewDispatch,
            decide_risk_dispatch,
        )
        try:
            from control_plane.github_review_risk_policy import (
                minimum_review_requirements,
            )
        except ImportError:
            minimum_review_requirements = None
        try:
            result = _child_assess_and_dispatch(
                payload, SourcePR, SourceFile, assess_current_pr_risk_with_final,
                ReviewOrigin, ReviewDispatch, decide_risk_dispatch,
                minimum_review_requirements,
            )
        except RiskSourceUnavailable as exc:
            return {"ok": False, "code": exc.code, "kind": "PR_SOURCE_UNAVAILABLE"}
        except ValueError as exc:
            return {"ok": False, "code": "CHILD_VALUE_REFUSED",
                    "exception": type(exc).__name__}
        return {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001 - no child text escapes
        return {"ok": False, "code": "CHILD_UNEXPECTED_FAILURE",
                "exception": type(exc).__name__}


def _child_assess_and_dispatch(payload, SourcePR, SourceFile,
                               assess_current_pr_risk_with_final, ReviewOrigin,
                               ReviewDispatch, decide_risk_dispatch,
                               minimum_review_requirements) -> dict:
    repository = payload["repository"]
    number = payload["pull_number"]
    bound_repository = repository
    bound_number = number
    initial = _map_pull_raw(payload["initial"], SourcePR, repository)
    final = _map_pull_raw(payload["final"], SourcePR, repository)
    pages = [_map_file_page(raw, SourceFile) for raw in payload["files_pages"]]

    class _SnapshotPort:
        """Canonical read port serving only the authenticated snapshots."""

        def __init__(self) -> None:
            self._source_reads = 0

        def read_pr_risk_source(self, *, repository, pull_number):
            if repository != bound_repository or pull_number != bound_number:
                raise _source_error("PR_SOURCE_IDENTITY_UNKNOWN")
            self._source_reads += 1
            if self._source_reads == 1:
                return initial
            if self._source_reads == 2:
                return final
            raise _source_error("PR_SOURCE_IDENTITY_UNKNOWN")

        def read_pr_risk_file_page(self, *, repository, pull_number, page, per_page):
            if repository != bound_repository or pull_number != bound_number:
                raise _source_error("PR_SOURCE_IDENTITY_UNKNOWN")
            if type(page) is not int or page < 1 or page > len(pages):
                raise _source_error("PR_SOURCE_PAGINATION_INCOMPLETE")
            return tuple(pages[page - 1])

    def _source_error(code):
        from control_plane.github_review_risk_source import RiskSourceUnavailable
        return RiskSourceUnavailable(code)

    assessment, latest = assess_current_pr_risk_with_final(
        _SnapshotPort(), repository=repository, pull_number=number,
    )
    advice = decide_risk_dispatch(
        origin=ReviewOrigin.AUTOMATIC_POLICY,
        assessment=assessment,
        expected_repository=repository,
        expected_pull_number=number,
        expected_head_sha=initial.head_sha,
        current_source=latest,
    )
    counts_consistent = True
    if minimum_review_requirements is not None:
        expected = minimum_review_requirements(assessment.tier)
        counts_consistent = (
            (assessment.minimum_independent_assessments,
             assessment.minimum_formal_non_author_approvals) == expected
        )
    return {
        "assessment": {
            "schema": assessment.schema,
            "repository": assessment.repository,
            "pull_number": assessment.pull_number,
            "head_sha": assessment.head_sha,
            "tier": assessment.tier.value,
            "minimum_independent_assessments":
                assessment.minimum_independent_assessments,
            "minimum_formal_non_author_approvals":
                assessment.minimum_formal_non_author_approvals,
            "reasons": list(assessment.reasons),
        },
        "advice": {
            "action": advice.action.value,
            "source_tier": advice.source_tier.value if advice.source_tier is not None else None,
            "reason": advice.reason,
            "repository": advice.repository,
            "pull_number": advice.pull_number,
            "head_sha": advice.head_sha,
        },
        "final_head_sha": latest.head_sha,
        "counts_consistent": counts_consistent,
    }


def _map_pull_raw(raw: dict, SourcePR, repository: str):
    """Strict REST -> canonical SourcePR; any type deviation is refused."""
    from control_plane.github_review_risk_source import RiskSourceUnavailable

    if type(raw) is not dict:
        raise RiskSourceUnavailable("PR_SOURCE_IDENTITY_UNKNOWN")
    number = raw.get("number")
    if type(number) is not int or type(number) is bool:
        raise RiskSourceUnavailable("PR_SOURCE_IDENTITY_UNKNOWN")
    head = raw.get("head")
    base = raw.get("base")
    if type(head) is not dict or type(base) is not dict:
        raise RiskSourceUnavailable("PR_SOURCE_IDENTITY_UNKNOWN")
    head_repo = head.get("repo")
    base_repo = base.get("repo")
    if type(head_repo) is not dict or type(base_repo) is not dict:
        raise RiskSourceUnavailable("PR_SOURCE_IDENTITY_UNKNOWN")
    stats = {}
    for name in ("changed_files", "additions", "deletions"):
        value = raw.get(name)
        if type(value) is not int or type(value) is bool:
            raise RiskSourceUnavailable("PR_FILE_STATS_INVALID")
        stats[name] = value
    source = SourcePR(
        repository=repository,
        pull_number=number,
        head_sha=head.get("sha"),
        base_sha=base.get("sha"),
        head_repository=head_repo.get("full_name"),
        base_repository=base_repo.get("full_name"),
        open=raw.get("state") == "open",
        draft=raw.get("draft") if type(raw.get("draft")) is bool else None,
        changed_files=stats["changed_files"],
        additions=stats["additions"],
        deletions=stats["deletions"],
    )
    return source


def _map_file_page(raw_page: list, SourceFile) -> list:
    """Strict REST file rows -> canonical SourceFile rows."""
    from control_plane.github_review_risk_source import RiskSourceUnavailable

    rows = []
    for raw in raw_page:
        if type(raw) is not dict or type(raw.get("filename")) is not str:
            raise RiskSourceUnavailable("PR_FILE_SHAPE_INVALID")
        previous = raw.get("previous_filename")
        patch = raw.get("patch")
        if patch is not None and type(patch) is not str:
            raise RiskSourceUnavailable("PR_CODE_PATCH_MISSING")
        rows.append(SourceFile(
            filename=raw["filename"],
            status=raw.get("status"),
            additions=raw.get("additions"),
            deletions=raw.get("deletions"),
            previous_filename=previous,
            patch_available="patch" in raw,
        ))
    return rows


def _run_policy_child(modules: list, repository: str, number: int,
                      initial: dict, final: dict, files_pages: list) -> dict:
    payload = {
        "modules": {entry["path"]: entry["source"] for entry in modules},
        "repository": repository,
        "pull_number": number,
        "initial": initial,
        "final": final,
        "files_pages": files_pages,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    adapter_path = os.path.abspath(__file__)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", "-c", _CHILD_BOOTSTRAP, adapter_path],
            input=encoded,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_CHILD_ENV,
            timeout=CHILD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _fail("POLICY_CHILD_TIMEOUT", timeout_seconds=CHILD_TIMEOUT_SECONDS)
    except OSError as exc:
        _fail("POLICY_CHILD_UNSTARTABLE", exception=type(exc).__name__)
    if completed.returncode != 0:
        _fail("POLICY_CHILD_FAILED", returncode=completed.returncode)
    try:
        parsed = json.loads(completed.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        _fail("CHILD_RESULT_MALFORMED")
    return parsed


def _parse_timestamp(value, row_id) -> datetime:
    if type(value) is not str or not value:
        _fail("REVIEW_ROW_MALFORMED", field="submitted_at", row_id=repr(row_id)[:40])
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("REVIEW_ROW_MALFORMED", field="submitted_at_format", row_id=repr(row_id)[:40])
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        _fail("REVIEW_ROW_MALFORMED", field="submitted_at_naive", row_id=repr(row_id)[:40])
    return parsed


def _parse_reviews(reviews, repository: str, number: int) -> dict:
    """Validate the complete review inventory; latest real disposition per actor.

    COMMENTED/PENDING never erase a prior actual approval; DISMISSED and a
    latest CHANGES_REQUESTED remain binding. Duplicate or malformed rows fail
    closed. Only real server ``User`` accounts are eligible channels.
    """
    if type(reviews) is not list:
        _fail("REVIEWS_MALFORMED", got=type(reviews).__name__)
    if len(reviews) > MAX_REVIEW_ROWS:
        _fail("REVIEWS_OUT_OF_BOUNDS", count=len(reviews))
    rows = []
    seen_ids = set()
    for raw in reviews:
        if type(raw) is not dict:
            _fail("REVIEW_ROW_MALFORMED", got=type(raw).__name__)
        row_id = raw.get("id")
        if type(row_id) is not int or type(row_id) is bool or row_id <= 0:
            _fail("REVIEW_ROW_MALFORMED", field="id", row_id=repr(row_id)[:40])
        if row_id in seen_ids:
            _fail("REVIEW_ROW_DUPLICATE", row_id=row_id)
        seen_ids.add(row_id)
        user = raw.get("user")
        if type(user) is not dict:
            _fail("REVIEW_ROW_MALFORMED", field="user", row_id=row_id)
        login = user.get("login")
        if type(login) is not str or not login:
            _fail("REVIEW_ROW_MALFORMED", field="login", row_id=row_id)
        user_type = user.get("type")
        if user_type is not None and type(user_type) is not str:
            _fail("REVIEW_ROW_MALFORMED", field="user_type", row_id=row_id)
        state = raw.get("state")
        if state not in _REVIEW_STATES:
            _fail("REVIEW_ROW_MALFORMED", field="state", row_id=row_id, state=repr(state)[:40])
        submitted = raw.get("submitted_at")
        if submitted is None:
            if state != "PENDING":
                _fail("REVIEW_ROW_MALFORMED", field="submitted_at_missing", row_id=row_id)
            submitted_dt = None
        else:
            submitted_dt = _parse_timestamp(submitted, row_id)
        pull_request_url = raw.get("pull_request_url")
        if pull_request_url is not None:
            if type(pull_request_url) is not str or not pull_request_url.endswith(
                f"/{repository}/pulls/{number}"
            ):
                _fail("REVIEW_ROW_FOREIGN_PULL", row_id=row_id)
        rows.append({
            "id": row_id,
            "login": login,
            "eligible_user": user_type == "User",
            "state": state,
            "at": submitted_dt,
            "commit_id": raw.get("commit_id"),
        })
    rows.sort(key=lambda row: ((row["at"] or datetime.min.replace(tzinfo=timezone.utc)),
                            row["id"]))
    actors: dict[str, dict] = {}
    for row in rows:
        key = row["login"].casefold()
        actor = actors.get(key)
        if actor is None:
            actor = {"login": row["login"], "eligible_user": row["eligible_user"],
                     "effective_state": None, "latest_id": None}
            actors[key] = actor
        if row["eligible_user"] is True and actor["eligible_user"] is not True:
            actor["eligible_user"] = True
        if row["state"] in _REAL_DISPOSITIONS:
            actor["effective_state"] = row["state"]
            actor["latest_id"] = row["id"]
            actor["commit_id"] = row["commit_id"]
    for actor in actors.values():
        actor["approves"] = actor["eligible_user"] is True and actor["effective_state"] == "APPROVED"
    states = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    return {
        "actors": actors,
        "inventory": {"rows": len(rows), "states": states,
                      "distinct_actors": len(actors)},
    }


def _qualified_native_facts(facts, repository, number, head_sha, target_ref):
    keys = {"repository", "pr_number", "head_sha", "target_ref", "protection_source_sha",
            "required_formal_approvals", "requires_code_owner_reviews", "review_decision",
            "review_decision_required", "native_enforcement_qualified"}
    if type(facts) is not dict or set(facts) != keys:
        _fail("NATIVE_FACTS_INCOMPLETE")
    if (facts["repository"] != repository or type(facts["pr_number"]) is not int
            or facts["pr_number"] != number or facts["head_sha"] != head_sha
            or facts["target_ref"] != target_ref or target_ref not in {"main", "codex/merge-queue-pilot"}
            or type(facts["protection_source_sha"]) is not str
            or not _SHA40.fullmatch(facts["protection_source_sha"])):
        _fail("NATIVE_FACTS_SUBJECT_MISMATCH")
    count = facts["required_formal_approvals"]
    if type(count) is not int or not 0 <= count <= MAX_REVIEW_ROWS:
        _fail("NATIVE_FACTS_COUNT_MALFORMED")
    for flag in ("requires_code_owner_reviews", "review_decision_required", "native_enforcement_qualified"):
        if type(facts[flag]) is not bool:
            _fail("NATIVE_FACTS_FLAG_MALFORMED", field=flag)
    if facts["native_enforcement_qualified"] is not True:
        _fail("NATIVE_ENFORCEMENT_UNKNOWN")
    decision = facts["review_decision"]
    if decision not in (None, "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED"):
        _fail("NATIVE_DECISION_MALFORMED")
    required = facts["review_decision_required"]
    if (count > 0 or facts["requires_code_owner_reviews"]) and not required:
        _fail("NATIVE_FACTS_SEMANTICS_INCONSISTENT")
    if decision in ("CHANGES_REQUESTED", "REVIEW_REQUIRED") or (required and decision != "APPROVED"):
        _fail("NATIVE_REVIEW_DISPOSITION_UNSATISFIED")
    return dict(facts)


_COAUTHOR_LINE = re.compile(r"^co-authored-by:(?:\s*)(.*)$", re.IGNORECASE)


def _coauthor_email(line: str):
    if "@" not in line:
        return None
    start = line.rfind("<")
    end = line.rfind(">")
    if start != -1 and end != -1 and end > start:
        candidate = line[start + 1:end].strip()
        return candidate or None
    candidate = line.strip()
    return candidate or None


def _noreply_login(email: str):
    folded = email.casefold()
    new_style = _NOREPLY_NEW.match(folded)
    if new_style is not None:
        return new_style.group(2)
    old_style = _NOREPLY_OLD.match(folded)
    return old_style.group(1) if old_style else None


def _read_source_contributors(get, repository, number, expected_commits):
    """Actual REST top-level mapped actors; only where independence is owed."""
    if type(expected_commits) is not int or not 1 <= expected_commits <= MAX_COMMIT_PAGES * PAGE_SIZE:
        _fail("PR_COMMITS_OUT_OF_BOUNDS")
    commits = []
    for page in range(1, (expected_commits + PAGE_SIZE - 1) // PAGE_SIZE + 1):
        body = _get_json(get, f"/repos/{repository}/pulls/{number}/commits?per_page=100&page={page}", "PR_COMMITS")
        expected = min(PAGE_SIZE, expected_commits-len(commits))
        if type(body) is not list or len(body) != expected:
            _fail("PR_COMMITS_INCONSISTENT", fetched=len(commits)+(len(body) if type(body) is list else 0), declared=expected_commits)
        commits.extend(body)
    role_emails, logins, unmapped, seen, trailers = {}, set(), [], set(), []
    for row in commits:
        if type(row) is not dict or type(row.get("sha")) is not str or not _SHA40.fullmatch(row["sha"]) or row["sha"] in seen:
            _fail("PR_COMMIT_IDENTITY_INCOMPLETE")
        seen.add(row["sha"])
        commit = row.get("commit")
        if type(commit) is not dict or type(commit.get("message")) is not str:
            _fail("PR_COMMIT_MALFORMED")
        for role in ("author", "committer"):
            mapped = row.get(role)
            login = mapped.get("login") if type(mapped) is dict else None
            node = commit.get(role)
            email = node.get("email") if type(node) is dict else None
            if type(login) is not str or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?", login):
                unmapped.append(role)
                continue
            logins.add(login)
            if email is not None and type(email) is not str:
                _fail("PR_COMMIT_MALFORMED", field=role+"_email")
            if email:
                key=email.casefold()
                if key in role_emails and role_emails[key].casefold()!=login.casefold():
                    _fail("CONTRIBUTOR_EMAIL_AMBIGUOUS")
                role_emails[key]=login
        for line in commit["message"].splitlines():
            match=_COAUTHOR_LINE.match(line.strip())
            if match:
                email=_coauthor_email(match.group(1))
                if not email:
                    unmapped.append("coauthor")
                else: trailers.append(email)
    for email in trailers:
        login=role_emails.get(email.casefold()) or _noreply_login(email)
        if login is None: unmapped.append("coauthor")
        else: logins.add(login)
    return {"logins":logins, "emails":sorted(role_emails), "unmapped":sorted(unmapped)}


def qualify_native_review(repository, pull, reviews, issuer_login, *, get, now, native_facts) -> dict:
    """Qualify one PR against canonical policy + native requirements, fail closed.

    Resolves effective requirements FIRST (canonical machine counts and the
    repository's actual native approval requirements, MAX not sum); skips all
    contributor/commits/identity mapping when neither technical nor formal
    review is owed; otherwise uses the authenticated server ``User`` APPROVED
    channel, excluding only actual source PR/commit authors/committers and
    coauthors. ``issuer_login`` is never a generic reviewer exclusion.
    """
    now_observation = _resolve_now(now)
    if not callable(get):
        _fail("READ_CALLBACK_UNAVAILABLE")
    if repository != PRODUCTION_REPOSITORY:
        _fail("PRODUCTION_REPOSITORY_MISMATCH", repository=repr(repository)[:120])
    if issuer_login is not None and type(issuer_login) is not str:
        _fail("ISSUER_LOGIN_MALFORMED")

    identity = _pull_identity(repository, pull)
    number = identity["number"]
    head_sha = identity["head_sha"]
    target_ref = identity["base_ref"]

    native = _qualified_native_facts(native_facts, repository, number, head_sha, target_ref)

    revision = _read_canonical_branch(get)
    modules = _read_policy_modules(get, revision)
    files_pages = _fetch_file_pages(get, repository, number, pull["changed_files"])
    final_pull = _fetch_final_pull(get, repository, number)
    child = _run_policy_child(modules, repository, number, pull, final_pull,
                              files_pages)
    if type(child) is not dict or child.get("ok") is not True:
        _fail("POLICY_EVALUATION_REFUSED",
              child_code=child.get("code") if type(child) is dict else "unparseable",
              child_exception=child.get("exception") if type(child) is dict else None)
    result = child.get("result")
    if type(result) is not dict:
        _fail("CHILD_RESULT_SHAPE_MALFORMED")
    if result.get("counts_consistent") is not True:
        _fail("RISK_COUNTS_INCONSISTENT")
    assessment = result.get("assessment")
    advice = result.get("advice")
    if type(assessment) is not dict or type(advice) is not dict:
        _fail("CHILD_RESULT_SHAPE_MALFORMED")
    if advice.get("action") not in ("AUTO_REVIEW_ELIGIBLE", "SKIP_NO_REVIEW_NEEDED"):
        _fail("RISK_DISPATCH_HOLD", advice_reason=advice.get("reason"))
    if result.get("final_head_sha") != head_sha:
        _fail("PR_SOURCE_HEAD_MOVED", expected=head_sha,
              final=repr(result.get("final_head_sha"))[:60])
    policy_schema = assessment.get("schema")
    policy_tech = assessment.get("minimum_independent_assessments")
    policy_formal = assessment.get("minimum_formal_non_author_approvals")
    for name, value in (("policy_tech", policy_tech), ("policy_formal", policy_formal)):
        if type(value) is not int or type(value) is bool or value < 0:
            _fail("POLICY_COUNTS_MALFORMED", field=name, got=repr(value)[:40])

    required_tech = policy_tech
    required_formal = max(policy_formal, native["required_formal_approvals"])

    inventory = _parse_reviews(reviews, repository, number)
    if any(actor["effective_state"] == "CHANGES_REQUESTED" for actor in inventory["actors"].values()):
        _fail("CURRENT_REVIEW_REQUESTS_CHANGES")
    approvers = [actor for actor in inventory["actors"].values()
                 if actor["approves"] is True]
    approver_logins = sorted({actor["login"] for actor in approvers})
    qualifying: list[str] = []
    contributors = {"logins": {identity["author_login"]}, "emails": [], "unmapped": []}
    accepted_tech = 0
    accepted_formal = 0
    technical_channel = "NONE_REQUIRED"

    if required_tech == 0 and required_formal == 0:
        pass
    elif not approvers:
        technical_channel = "NONE"
        if required_formal > 0:
            _fail("APPROVAL_CHANNEL_UNAVAILABLE",
                  required_independent_assessments=required_tech,
                  required_formal_non_author_approvals=required_formal,
                  accepted_independent_assessments=0,
                  accepted_formal_non_author_approvals=0)
        raise TechnicalProvenanceUnavailable(
            "TECHNICAL_PROVENANCE_UNAVAILABLE",
            required_independent_assessments=required_tech,
            required_formal_non_author_approvals=0,
            accepted_independent_assessments=0,
            accepted_formal_non_author_approvals=0,
        )
    else:
        technical_channel = "AUTHENTICATED_SERVER_USER_APPROVED"
        contributors = _read_source_contributors(
            get, repository, number, pull.get("commits"),
        )
        contributors["logins"].add(identity["author_login"])
        if contributors["unmapped"]:
            _fail("INDEPENDENCE_UNVERIFIABLE_CONTRIBUTOR_IDENTITY",
                  unmapped=contributors["unmapped"])
        excluded = {login.casefold() for login in contributors["logins"]}
        eligible = [actor for actor in approvers if actor["login"].casefold() not in excluded]
        exact = {actor["login"] for actor in eligible if actor.get("commit_id") == head_sha}
        native_valid = {actor["login"] for actor in eligible
                        if type(actor.get("commit_id")) is str and _SHA40.fullmatch(actor["commit_id"])
                        and native["review_decision"] == "APPROVED"}
        qualifying = sorted(exact | (native_valid if native["required_formal_approvals"] else set()))
        accepted_tech = len(exact)
        accepted_formal = len(exact | (native_valid if native["required_formal_approvals"] else set()))
        if len(exact) < policy_formal:
            _fail("REVIEW_REQUIREMENTS_UNMET", required_formal_non_author_approvals=policy_formal, accepted_independent_assessments=accepted_tech, accepted_formal_non_author_approvals=accepted_formal)
        if accepted_tech < required_tech or accepted_formal < required_formal:
            if required_formal == 0 and accepted_tech == 0:
                raise TechnicalProvenanceUnavailable(
                    "TECHNICAL_PROVENANCE_UNAVAILABLE",
                    required_independent_assessments=required_tech,
                    required_formal_non_author_approvals=0,
                    accepted_independent_assessments=0,
                    accepted_formal_non_author_approvals=0,
                    excluded_contributors=sorted(contributors["logins"]),
                )
            _fail("REVIEW_REQUIREMENTS_UNMET",
                  required_independent_assessments=required_tech,
                  required_formal_non_author_approvals=required_formal,
                  accepted_independent_assessments=accepted_tech,
                  accepted_formal_non_author_approvals=accepted_formal)

    revision_recheck = _read_canonical_branch(get)
    if revision_recheck != revision:
        _fail("POLICY_SOURCE_MOVED", revision=revision, recheck=revision_recheck)

    return {
        "disposition": "QUALIFIED",
        "repository": repository,
        "pull_number": number,
        "head_sha": head_sha,
        "target_ref": target_ref,
        "origin": ORIGIN_AUTOMATIC_POLICY,
        "policy_schema": policy_schema,
        "risk_tier": assessment.get("tier"),
        "minimum_independent_assessments": policy_tech,
        "minimum_formal_non_author_approvals": policy_formal,
        "required_independent_assessments": required_tech,
        "required_formal_non_author_approvals": required_formal,
        "accepted_independent_assessments": accepted_tech,
        "accepted_formal_non_author_approvals": accepted_formal,
        "native_review_decision_required": native["review_decision_required"],
        "qualifying_reviewer_logins": qualifying,
        "source_contributors": sorted(contributors["logins"]),
        "policy_source_identity": {
            "repository": CANONICAL_POLICY_REPOSITORY,
            "branch": CANONICAL_POLICY_BRANCH,
            "revision": revision,
            "revision_recheck": revision_recheck,
            "paths": [
                {key: entry[key] for key in ("path", "blob_sha1", "sha256", "size")}
                for entry in modules
            ],
        },
        "dispatch_action": advice.get("action"),
        "dispatch_reason": advice.get("reason"),
        "assessment_reasons": assessment.get("reasons"),
        "native_requirements": native,
        "review_inventory": inventory["inventory"],
        "now_observation": now_observation,
        "issuer_login": issuer_login,
        "technical_channel": technical_channel,
        "source_contributor_emails": contributors["emails"],
        "provenance_note": UNSIGNED_ASSESSMENT_NOTE,
        "api_origin_hint": API_BASE_HINT,
    }


__all__ = [
    "CANONICAL_POLICY_BRANCH",
    "CANONICAL_POLICY_PATHS",
    "CANONICAL_POLICY_REPOSITORY",
    "NativeReviewPolicyError",
    "NativeReviewReadError",
    "PRODUCTION_REPOSITORY",
    "TechnicalProvenanceUnavailable",
    "TECHNICAL_PROVENANCE_UNAVAILABLE",
    "child_evaluate",
    "qualify_native_review",
]
