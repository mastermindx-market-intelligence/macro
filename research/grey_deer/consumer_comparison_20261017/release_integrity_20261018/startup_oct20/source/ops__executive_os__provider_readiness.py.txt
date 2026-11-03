"""Composite, replay-safe provider readiness receipt for Executive OS.

This module never reads credential bytes.  It binds a sanitized App Server
identity verdict and one sanitized inference-canary receipt to the credential's
``lstat`` identity and the exact installed Codex binary.  A passing receipt can
be reused only while both identities remain byte-for-byte current.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_RELEASE_ROOT = Path(__file__).resolve().parents[2]
if os.fspath(_RELEASE_ROOT) not in sys.path:
    sys.path.insert(0, os.fspath(_RELEASE_ROOT))

from control_plane.fs_security import FilesystemSecurityError, has_macos_acl

_SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if __package__ in {None, ""} and str(_SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIRECTORY))

try:
    from ops.executive_os.provider_identity_policy import (
        COMPANY_WORKSPACE_BINDING_CLASS,
        COMPANY_DEVICE_DRIFT_PREDECESSOR_SHA256,
        PERSONAL_PRO_WORKER_BINDING_CLASS,
        EXPECTED_AUTH_MODE,
        WORKSPACE_BINDING_CLASSES,
        evaluate_identity_policy,
    )
except ModuleNotFoundError:  # pragma: no cover - installed direct-script mode
    from provider_identity_policy import (  # type: ignore[no-redef]
        COMPANY_WORKSPACE_BINDING_CLASS,
        COMPANY_DEVICE_DRIFT_PREDECESSOR_SHA256,
        PERSONAL_PRO_WORKER_BINDING_CLASS,
        EXPECTED_AUTH_MODE,
        WORKSPACE_BINDING_CLASSES,
        evaluate_identity_policy,
    )

try:
    from ops.executive_os import provider_worker_slots
except ModuleNotFoundError:  # pragma: no cover - installed direct-script mode
    import provider_worker_slots  # type: ignore[no-redef]


SCHEMA_VERSION = "mastermind.executive_provider_readiness/v2"
IDENTITY_SCHEMA = "mastermind.executive_provider_identity/v1"
CANARY_SCHEMA = "mastermind.executive_provider_inference_canary/v2"
RECEIPT_PATH = Path(
    "/Library/Application Support/MastermindExecutive/config/provider-readiness-v2.json"
)
AUTH_PATH = Path(
    "/var/db/mastermind-executive/workers/codex-01/provider-home/auth.json"
)
CODEX_BINARY = Path(
    "/Library/Application Support/MastermindExecutive/bin/codex-0.159.2"
)
CODEX_VERSION = "0.159.2"
CODEX_SHA256 = "16593cc2f422d5f398a8e40f550ebbaf1245392528957be342c295920a300704"
CODEX_TEAM_ID = "2DC432GLL2"
WORKER_UID = 451
WORKER_GID = 451
EXPECTED_KINDS = frozenset(
    {"service-account", "personal-access-token", "device-auth"}
)
WORKSPACE_BINDING_CLASS = COMPANY_WORKSPACE_BINDING_CLASS
CANARY_ID_RE = re.compile(r"^canary-[0-9a-f]{12}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROVIDER_DIAGNOSTIC_TERMS = frozenset(
    {
        "account", "auth", "authorization", "billing", "busy", "capacity",
        "connection", "conversation", "credits", "denied", "disabled",
        "error", "expired", "failed", "failure", "forbidden", "internal",
        "invalid", "limit", "model", "network", "output", "overloaded",
        "permission", "plan", "provider", "quota", "rate", "request",
        "schema", "service", "session", "stream", "supported",
        "temporarily", "tier", "timeout", "token", "unauthorized",
        "unavailable", "unknown", "unsupported", "usage", "workspace",
    }
)
PRODUCTION_MODEL = "gpt-5.6-sol"
# Closed predecessor for the reviewed 0.147.0 -> 0.159.2 recovery. Adding
# another generation requires source review; a receipt cannot nominate code.
REQUALIFICATION_PREDECESSOR_VERSION = "0.147.0"
REQUALIFICATION_PREDECESSOR_SHA256 = "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37"
MAX_REQUALIFICATION_HORIZON = timedelta(hours=1)
MAX_READINESS_AGE = timedelta(hours=24)
MIN_ACCEPTANCE_MARGIN = timedelta(minutes=30)
MAX_CLOCK_SKEW = timedelta(minutes=5)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "passed",
        "refusal",
        "observed_at",
        "credential_expires_at",
        "readiness_expires_at",
        "expected_credential_kind",
        "workspace_binding_class",
        "forced_chatgpt_workspace_id_applied",
        "credential_lstat",
        "codex_binary",
        "provider_identity",
        "inference_canary",
    }
)


class ReadinessError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _timestamp(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str) or TIMESTAMP_RE.fullmatch(value) is None:
        raise ReadinessError(code)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ReadinessError(code) from exc
    return parsed


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _deadline_fields(
    *,
    credential_expires_at: str,
    observed_at: str | None = None,
    readiness_expires_at: str | None = None,
    now: datetime | None = None,
    allow_expired_readiness: bool = False,
) -> tuple[str, str, str]:
    current = datetime.now(UTC) if now is None else now.astimezone(UTC)
    observed_text = now_iso() if observed_at is None else observed_at
    observed = _timestamp(observed_text, code="receipt_timestamp_malformed")
    credential_expiry = _timestamp(
        credential_expires_at, code="credential_expiry_malformed"
    )
    maximum = min(credential_expiry, observed + MAX_READINESS_AGE)
    if readiness_expires_at is None:
        readiness_expiry = maximum
        readiness_text = _iso(readiness_expiry)
    else:
        readiness_text = readiness_expires_at
        readiness_expiry = _timestamp(
            readiness_text, code="readiness_expiry_malformed"
        )
    if observed > current + MAX_CLOCK_SKEW:
        raise ReadinessError("receipt_timestamp_in_future")
    if readiness_expiry > maximum or readiness_expiry <= observed:
        raise ReadinessError("readiness_expiry_bounds_invalid")
    if (
        not allow_expired_readiness
        and readiness_expiry <= current + MIN_ACCEPTANCE_MARGIN
    ):
        raise ReadinessError("readiness_expired_or_insufficient_margin")
    return observed_text, credential_expires_at, readiness_text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_no_macos_acl(path: Path) -> None:
    try:
        present = has_macos_acl(path)
    except FilesystemSecurityError:
        raise ReadinessError("identity_acl_unsafe")
    if present:
        raise ReadinessError("identity_acl_unsafe")


def lstat_identity(
    path: Path,
    *,
    expected_uid: int | None = None,
    expected_gid: int | None = None,
    expected_mode: int | None = None,
    require_nonempty: bool = False,
) -> dict[str, int]:
    """Return safe filesystem identity without opening the file."""

    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ReadinessError("identity_not_regular")
    mode = stat.S_IMODE(info.st_mode)
    if expected_uid is not None and info.st_uid != expected_uid:
        raise ReadinessError("identity_owner_mismatch")
    if expected_gid is not None and info.st_gid != expected_gid:
        raise ReadinessError("identity_group_mismatch")
    if expected_mode is not None and mode != expected_mode:
        raise ReadinessError("identity_mode_mismatch")
    if info.st_nlink != 1:
        raise ReadinessError("identity_link_count_mismatch")
    if require_nonempty and info.st_size <= 0:
        raise ReadinessError("identity_empty")
    _assert_no_macos_acl(path)
    return {
        "device": int(info.st_dev),
        "inode": int(info.st_ino),
        "uid": int(info.st_uid),
        "gid": int(info.st_gid),
        "mode": mode,
        "size": int(info.st_size),
        "mtime_ns": int(info.st_mtime_ns),
        "ctime_ns": int(info.st_ctime_ns),
        "nlink": int(info.st_nlink),
    }


def current_auth_identity(
    path: Path = AUTH_PATH,
    *,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
) -> dict[str, int]:
    return lstat_identity(
        path,
        expected_uid=worker_uid,
        expected_gid=worker_gid,
        expected_mode=0o600,
        require_nonempty=True,
    )


def current_binary_identity(path: Path = CODEX_BINARY) -> dict[str, Any]:
    identity: dict[str, Any] = lstat_identity(path, expected_mode=0o555, require_nonempty=True)
    identity.update(
        {
            "path": os.fspath(path),
            "version": CODEX_VERSION,
            "sha256": _sha256_file(path),
            "team_identifier": CODEX_TEAM_ID,
        }
    )
    if identity["uid"] != 0 or identity["gid"] != 0:
        raise ReadinessError("binary_owner_mismatch")
    if identity["sha256"] != CODEX_SHA256:
        raise ReadinessError("binary_sha256_mismatch")
    return identity


def _safe_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "passed",
        "refusal",
        "expected_credential_kind",
        "auth_mode",
        "account_type",
        "plan_type",
        "requires_openai_auth",
        "workspace_binding_class",
        "observed_at",
        "codex_binary",
        "credential_lstat",
        "forced_chatgpt_workspace_id_applied",
    }
    if set(value) != allowed:
        raise ReadinessError("identity_contains_unreviewed_fields")
    if value.get("schema_version") != IDENTITY_SCHEMA or value.get("passed") is not True:
        raise ReadinessError("identity_not_passing")
    result = {key: value.get(key) for key in sorted(allowed)}
    # Belt-and-suspenders: these identifier-like fields are never in schema.
    if any(key in value for key in ("email", "account_id", "accountId", "workspace_id")):
        raise ReadinessError("identity_contains_identifier")
    expected_kind = result["expected_credential_kind"]
    if expected_kind not in EXPECTED_AUTH_MODE:
        raise ReadinessError("identity_credential_kind_unknown")
    refusal = evaluate_identity_policy(
        expected_kind=str(expected_kind),
        auth_mode=result["auth_mode"],
        account_type=result["account_type"],
        plan_type=result["plan_type"],
        requires_openai_auth=result["requires_openai_auth"],
        workspace_binding_class=result["workspace_binding_class"],
    )
    if refusal is not None:
        legacy_names = {
            "auth_mode_policy_mismatch": "identity_auth_mode_mismatch",
            "account_type_not_chatgpt": "identity_account_type_mismatch",
            "openai_auth_requirement_malformed": "identity_openai_auth_malformed",
            "workspace_binding_class_unknown": "identity_workspace_attestation_missing",
        }
        raise ReadinessError(legacy_names.get(refusal, f"identity_{refusal}"))
    _timestamp(result["observed_at"], code="identity_timestamp_malformed")
    if not isinstance(result["codex_binary"], Mapping):
        raise ReadinessError("identity_binary_missing")
    if not isinstance(result["credential_lstat"], Mapping):
        raise ReadinessError("identity_credential_lstat_missing")
    if result["forced_chatgpt_workspace_id_applied"] is not False:
        raise ReadinessError("identity_forced_workspace_forbidden")
    return result


def _assert_worker_identity(
    identity: Mapping[str, Any], *, worker_uid: int, worker_gid: int
) -> None:
    if (
        isinstance(worker_uid, bool)
        or isinstance(worker_gid, bool)
        or not 400 <= worker_uid < 500
        or not 400 <= worker_gid < 500
        or identity.get("uid") != worker_uid
        or identity.get("gid") != worker_gid
    ):
        raise ReadinessError("worker_identity_mismatch")


def _safe_canary(
    value: Mapping[str, Any], *, binary_identity: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if value.get("schema_version") != CANARY_SCHEMA or not isinstance(value.get("passed"), bool):
        raise ReadinessError("canary_malformed")
    allowed = (
        "schema_version",
        "canary_id",
        "observed_at",
        "codex_version",
        "codex_sha256",
        "codex_team_identifier",
        "model",
        "exit_code",
        "timed_out",
        "terminal_event_class",
        "result_valid",
        "stdout_sha256",
        "stderr_sha256",
        "provider_error_message_count",
        "provider_error_message_sha256",
        "provider_error_terms",
        "workspace_capability_outcome",
        "workspace_selection_mechanism",
        "forced_chatgpt_workspace_id_applied",
        "passed",
        "refusal",
    )
    if set(value) != set(allowed):
        raise ReadinessError("canary_contains_unreviewed_fields")
    result = {key: value.get(key) for key in allowed}
    if result["forced_chatgpt_workspace_id_applied"] is not False:
        raise ReadinessError("forced_workspace_forbidden")
    expected_binary = binary_identity or {
        "version": CODEX_VERSION, "sha256": CODEX_SHA256, "team_identifier": CODEX_TEAM_ID,
    }
    if (result["codex_version"] != expected_binary["version"]
            or result["codex_sha256"] != expected_binary["sha256"]):
        raise ReadinessError("canary_binary_mismatch")
    if result["codex_team_identifier"] != expected_binary["team_identifier"]:
        raise ReadinessError("canary_team_mismatch")
    _timestamp(result["observed_at"], code="canary_timestamp_malformed")
    if not isinstance(result["canary_id"], str) or CANARY_ID_RE.fullmatch(result["canary_id"]) is None:
        raise ReadinessError("canary_id_malformed")
    if not isinstance(result["stdout_sha256"], str) or SHA256_RE.fullmatch(result["stdout_sha256"]) is None:
        raise ReadinessError("canary_stdout_digest_malformed")
    if not isinstance(result["stderr_sha256"], str) or SHA256_RE.fullmatch(result["stderr_sha256"]) is None:
        raise ReadinessError("canary_stderr_digest_malformed")
    if (
        isinstance(result["provider_error_message_count"], bool)
        or not isinstance(result["provider_error_message_count"], int)
        or not 0 <= result["provider_error_message_count"] <= 4
    ):
        raise ReadinessError("canary_provider_error_count_malformed")
    provider_message_digest = result["provider_error_message_sha256"]
    if (
        provider_message_digest is not None
        and (
            not isinstance(provider_message_digest, str)
            or SHA256_RE.fullmatch(provider_message_digest) is None
        )
    ):
        raise ReadinessError("canary_provider_error_digest_malformed")
    if (result["provider_error_message_count"] == 0) is not (
        provider_message_digest is None
    ):
        raise ReadinessError("canary_provider_error_digest_conflict")
    provider_error_terms = result["provider_error_terms"]
    if (
        not isinstance(provider_error_terms, list)
        or len(provider_error_terms) > len(PROVIDER_DIAGNOSTIC_TERMS)
        or any(
            not isinstance(term, str) or term not in PROVIDER_DIAGNOSTIC_TERMS
            for term in provider_error_terms
        )
    ):
        raise ReadinessError("canary_provider_error_terms_malformed")
    if provider_error_terms != sorted(set(provider_error_terms)):
        raise ReadinessError("canary_provider_error_terms_malformed")
    if result["provider_error_message_count"] == 0 and provider_error_terms:
        raise ReadinessError("canary_provider_error_terms_conflict")
    if result["workspace_capability_outcome"] != "inert_untrusted_workspace":
        raise ReadinessError("canary_workspace_capability_mismatch")
    if result["workspace_selection_mechanism"] != "none":
        raise ReadinessError("canary_workspace_selection_mismatch")
    if result["model"] != PRODUCTION_MODEL:
        raise ReadinessError("canary_model_mismatch")
    if result["passed"] is True:
        if (
            result["exit_code"] != 0
            or result["timed_out"] is not False
            or result["terminal_event_class"] != "turn_completed"
            or result["result_valid"] is not True
            or result["refusal"] is not None
        ):
            raise ReadinessError("canary_terminal_mismatch")
    elif not isinstance(result["refusal"], str) or not result["refusal"]:
        raise ReadinessError("canary_refusal_missing")
    return result


def compose_receipt(
    *,
    identity: Mapping[str, Any],
    canary: Mapping[str, Any],
    auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
    expected_kind: str,
    workspace_binding_class: str,
    credential_expires_at: str,
    readiness_expires_at: str | None = None,
    canary_command_status: int | None = None,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
) -> dict[str, Any]:
    if expected_kind not in EXPECTED_KINDS:
        raise ReadinessError("credential_kind_unknown")
    if workspace_binding_class not in WORKSPACE_BINDING_CLASSES:
        raise ReadinessError("workspace_attestation_missing")
    _assert_worker_identity(
        auth_identity, worker_uid=worker_uid, worker_gid=worker_gid
    )
    safe_identity = _safe_identity(identity)
    if safe_identity["expected_credential_kind"] != expected_kind:
        raise ReadinessError("credential_kind_mismatch")
    if safe_identity["workspace_binding_class"] != workspace_binding_class:
        raise ReadinessError("workspace_attestation_mismatch")
    safe_canary = _safe_canary(canary)
    if canary_command_status is not None and (
        (canary_command_status == 0) is not (safe_canary["passed"] is True)
    ):
        raise ReadinessError("canary_command_status_conflict")
    if binary_identity.get("sha256") != CODEX_SHA256:
        raise ReadinessError("binary_sha256_mismatch")
    if safe_identity["codex_binary"] != dict(binary_identity):
        raise ReadinessError("identity_binary_mismatch")
    if safe_identity["credential_lstat"] != dict(auth_identity):
        raise ReadinessError("identity_credential_mismatch")
    observed_at, credential_expiry, readiness_expiry = _deadline_fields(
        credential_expires_at=credential_expires_at,
        readiness_expires_at=readiness_expires_at,
    )
    passed = safe_canary["passed"] is True
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": passed,
        "refusal": None if passed else str(safe_canary.get("refusal") or "provider_canary_failed"),
        "observed_at": observed_at,
        "credential_expires_at": credential_expiry,
        "readiness_expires_at": readiness_expiry,
        "expected_credential_kind": expected_kind,
        "workspace_binding_class": workspace_binding_class,
        "forced_chatgpt_workspace_id_applied": False,
        "credential_lstat": dict(auth_identity),
        "codex_binary": dict(binary_identity),
        "provider_identity": safe_identity,
        "inference_canary": safe_canary,
    }


def validate_receipt_document(
    value: Mapping[str, Any],
    *,
    auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
    expected_kind: str | None = None,
    workspace_binding_class: str | None = None,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
    allow_expired_readiness: bool = False,
) -> None:
    if set(value) != _RECEIPT_FIELDS:
        raise ReadinessError("readiness_receipt_fields_malformed")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("passed") is not True:
        raise ReadinessError("readiness_receipt_not_passing")
    if value.get("refusal") is not None:
        raise ReadinessError("readiness_receipt_has_refusal")
    _deadline_fields(
        observed_at=value.get("observed_at"),
        credential_expires_at=value.get("credential_expires_at"),
        readiness_expires_at=value.get("readiness_expires_at"),
        allow_expired_readiness=allow_expired_readiness,
    )
    if value.get("expected_credential_kind") not in EXPECTED_KINDS:
        raise ReadinessError("readiness_credential_kind_unknown")
    if value.get("workspace_binding_class") not in WORKSPACE_BINDING_CLASSES:
        raise ReadinessError("readiness_workspace_attestation_missing")
    if expected_kind is not None and value.get("expected_credential_kind") != expected_kind:
        raise ReadinessError("readiness_expected_kind_mismatch")
    if (
        workspace_binding_class is not None
        and value.get("workspace_binding_class") != workspace_binding_class
    ):
        raise ReadinessError("readiness_workspace_binding_mismatch")
    if value.get("forced_chatgpt_workspace_id_applied") is not False:
        raise ReadinessError("readiness_forced_workspace_forbidden")
    receipt_credential = value.get("credential_lstat")
    if not isinstance(receipt_credential, Mapping):
        raise ReadinessError("readiness_credential_stale")
    _assert_worker_identity(
        receipt_credential, worker_uid=worker_uid, worker_gid=worker_gid
    )
    _assert_worker_identity(
        auth_identity, worker_uid=worker_uid, worker_gid=worker_gid
    )
    if receipt_credential != dict(auth_identity):
        raise ReadinessError("readiness_credential_stale")
    if value.get("codex_binary") != dict(binary_identity):
        raise ReadinessError("readiness_binary_stale")
    identity = value.get("provider_identity")
    canary = value.get("inference_canary")
    if not isinstance(identity, Mapping) or not isinstance(canary, Mapping):
        raise ReadinessError("readiness_components_malformed")
    safe_identity = _safe_identity(identity)
    safe_canary = _safe_canary(canary)
    if safe_canary["passed"] is not True:
        raise ReadinessError("readiness_canary_not_passing")
    if safe_identity["expected_credential_kind"] != value["expected_credential_kind"]:
        raise ReadinessError("readiness_credential_kind_conflict")
    if safe_identity["codex_binary"] != dict(binary_identity):
        raise ReadinessError("readiness_identity_binary_conflict")
    if safe_identity["credential_lstat"] != dict(auth_identity):
        raise ReadinessError("readiness_identity_credential_conflict")


def classify_refresh_eligibility(
    value: Mapping[str, Any],
    *,
    auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
    expected_kind: str,
    workspace_binding_class: str,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
    new_credential_expires_at: str | None = None,
) -> None:
    """Return None if the document is refresh-eligible, else raise ReadinessError.

    A document is refresh-eligible iff ALL hold:
      a. validate_receipt_document(value, ..., allow_expired_readiness=True)
         passes — historically passing composite receipt, unchanged current
         auth + binary identity, matching kind and class.
      b. value["expected_credential_kind"] == "device-auth" AND
         expected_kind == "device-auth".  Service-account / personal-access-token
         expiry must keep requiring credential rotation.
      c. validate_receipt_document(value, ..., allow_expired_readiness=False)
         raises exactly ReadinessError("readiness_expired_or_insufficient_margin").
         If the strict call passes, the receipt is still live and must NOT be
         refreshed.  If it raises anything else, the document is tampered or
         otherwise ineligible.

    Between (a) and (c) two further refusals fire so the credential deadline
    can never be locally extended:
      (i) the receipt's own credential_expires_at must still be valid at
          refresh time with margin — only the readiness deadline may be
          expired, never the credential deadline.
      (ii) when a new credential deadline is provided, it must not be later
           than the receipt's credential_expires_at — the same auth identity
           cannot extend its own credential window.
    """

    if value.get("expected_credential_kind") != "device-auth" or expected_kind != "device-auth":
        raise ReadinessError("refresh_requires_credential_rotation")
    validate_receipt_document(
        value,
        auth_identity=auth_identity,
        binary_identity=binary_identity,
        expected_kind=expected_kind,
        workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid,
        worker_gid=worker_gid,
        allow_expired_readiness=True,
    )
    receipt_credential_expiry = _timestamp(
        value["credential_expires_at"], code="credential_expiry_malformed"
    )
    if receipt_credential_expiry <= datetime.now(UTC) + MIN_ACCEPTANCE_MARGIN:
        raise ReadinessError("refresh_requires_credential_rotation")
    if new_credential_expires_at is not None:
        new_credential_expiry = _timestamp(
            new_credential_expires_at, code="credential_expiry_malformed"
        )
        if new_credential_expiry > receipt_credential_expiry:
            raise ReadinessError("refresh_requires_credential_rotation")
    try:
        validate_receipt_document(
            value,
            auth_identity=auth_identity,
            binary_identity=binary_identity,
            expected_kind=expected_kind,
            workspace_binding_class=workspace_binding_class,
            worker_uid=worker_uid,
            worker_gid=worker_gid,
            allow_expired_readiness=False,
        )
    except ReadinessError as exc:
        if str(exc) == "readiness_expired_or_insufficient_margin":
            return None
        raise ReadinessError("refresh_not_eligible") from exc
    raise ReadinessError("refresh_not_eligible")




def _attested_predecessor_identity() -> dict[str, Any]:
    """Read only the fixed, previously reviewed installed predecessor."""
    from control_plane.codex_worker import (
        CodexWorkerError, load_codex_attestation_receipt,
    )

    path = CODEX_BINARY.with_name(f"codex-{REQUALIFICATION_PREDECESSOR_VERSION}")
    attestation_path = CODEX_BINARY.parent.parent / (
        f"codex-attestation-{REQUALIFICATION_PREDECESSOR_VERSION}.json"
    )
    _validate_receipt_directory(attestation_path)
    _validate_receipt_directory(path)
    _assert_no_macos_acl(attestation_path)
    try:
        attestation = load_codex_attestation_receipt(
            attestation_path, expected_binary_path=path, expected_owner_gid=WORKER_GID,
        )
    except (CodexWorkerError, OSError) as exc:
        raise ReadinessError("requalification_predecessor_attestation_invalid") from exc
    if (attestation.version != REQUALIFICATION_PREDECESSOR_VERSION
            or attestation.sha256 != REQUALIFICATION_PREDECESSOR_SHA256
            or attestation.team_identifier != CODEX_TEAM_ID):
        raise ReadinessError("requalification_predecessor_attestation_mismatch")
    identity: dict[str, Any] = lstat_identity(
        path, expected_uid=0, expected_gid=0, expected_mode=0o555, require_nonempty=True,
    )
    identity.update({
        "path": os.fspath(path), "version": attestation.version,
        "sha256": attestation.sha256, "team_identifier": attestation.team_identifier,
    })
    return identity


def classify_terminal_requalification(
    value: Mapping[str, Any], *,
    auth_identity: Mapping[str, Any], binary_identity: Mapping[str, Any],
    expected_kind: str, workspace_binding_class: str,
    new_credential_expires_at: str,
    worker_uid: int = WORKER_UID, worker_gid: int = WORKER_GID,
) -> None:
    """Admit only the closed terminal failure on the reviewed predecessor.

    This is explicit device-auth revalidation, not expiry extension for a token,
    an automatic retry, or resolution of an uncertain provider effect.
    """
    current = datetime.now(UTC)
    deadline = _timestamp(new_credential_expires_at, code="credential_expiry_malformed")
    if not current + MIN_ACCEPTANCE_MARGIN < deadline <= current + MAX_REQUALIFICATION_HORIZON:
        raise ReadinessError("requalification_deadline_out_of_bounds")
    validate_terminal_predecessor_document(
        value, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_kind=expected_kind, workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid, worker_gid=worker_gid,
    )


def paired_filesystem_device_renumbering(
    *, historical_auth: Mapping[str, Any], current_auth: Mapping[str, Any],
    historical_binary: Mapping[str, Any], attested_predecessor: Mapping[str, Any],
    current_binary: Mapping[str, Any],
) -> bool:
    """Recognize a paired device change for a NEW qualification only.

    There is no retrospective VolumeUUID claim. Both historical objects must
    share a device, all three current objects must share another device, and
    every other auth/predecessor field must match. Never use for passing-receipt
    reuse, expiry refresh or post-canary finalization.
    """
    documents = (historical_auth, historical_binary, current_auth,
                 attested_predecessor, current_binary)
    devices = [document.get("device") for document in documents]
    if any(type(device) is not int or device <= 0 for device in devices):
        return False
    if not (devices[0] == devices[1] and devices[2] == devices[3] == devices[4]
            and devices[0] != devices[2]):
        return False
    def persistent_fields(document):
        return {key: value for key, value in document.items() if key != "device"}
    return (persistent_fields(historical_auth) == persistent_fields(current_auth)
            and persistent_fields(historical_binary) == persistent_fields(attested_predecessor))


def validate_terminal_predecessor_document(
    value: Mapping[str, Any], *,
    auth_identity: Mapping[str, Any], binary_identity: Mapping[str, Any],
    expected_kind: str, workspace_binding_class: str,
    worker_uid: int = WORKER_UID, worker_gid: int = WORKER_GID,
) -> None:
    """Verify closed predecessor evidence without granting a new canary.

    Also used by broker reconciliation long after a request's deadline. A
    matching old digest plus pre-marker time proves absence of its reservation;
    expired authorization never prevents a read-only effect reconciliation.
    """
    if (expected_kind != "device-auth"
            or workspace_binding_class != COMPANY_WORKSPACE_BINDING_CLASS
            or (worker_uid, worker_gid) != (WORKER_UID, WORKER_GID)):
        raise ReadinessError("requalification_requires_company_device_auth")
    if (set(value) != _RECEIPT_FIELDS
            or value.get("schema_version") != SCHEMA_VERSION
            or value.get("passed") is not False
            or value.get("refusal") != "provider_turn_failed"
            or value.get("expected_credential_kind") != expected_kind
            or value.get("workspace_binding_class") != workspace_binding_class
            or value.get("forced_chatgpt_workspace_id_applied") is not False):
        raise ReadinessError("requalification_requires_terminal_adverse")
    _deadline_fields(
        observed_at=value.get("observed_at"),
        credential_expires_at=value.get("credential_expires_at"),
        readiness_expires_at=value.get("readiness_expires_at"),
        allow_expired_readiness=True,
    )
    _assert_worker_identity(auth_identity, worker_uid=worker_uid, worker_gid=worker_gid)
    historical_auth = value.get("credential_lstat")
    historical_binary = value.get("codex_binary")
    if not isinstance(historical_auth, Mapping) or not isinstance(historical_binary, Mapping):
        raise ReadinessError("requalification_historical_identity_missing")
    if (binary_identity.get("path") != os.fspath(CODEX_BINARY)
            or binary_identity.get("version") != CODEX_VERSION
            or binary_identity.get("sha256") != CODEX_SHA256
            or binary_identity.get("team_identifier") != CODEX_TEAM_ID):
        raise ReadinessError("requalification_current_binary_unreviewed")
    predecessor = _attested_predecessor_identity()
    if predecessor["sha256"] == binary_identity["sha256"]:
        raise ReadinessError("requalification_requires_reviewed_binary_upgrade")
    if (historical_auth != dict(auth_identity) or historical_binary != predecessor):
        if not paired_filesystem_device_renumbering(
            historical_auth=historical_auth, current_auth=auth_identity,
            historical_binary=historical_binary, attested_predecessor=predecessor,
            current_binary=binary_identity,
        ):
            raise ReadinessError("requalification_identity_continuity_unproven")
    identity, canary = value.get("provider_identity"), value.get("inference_canary")
    if not isinstance(identity, Mapping) or not isinstance(canary, Mapping):
        raise ReadinessError("requalification_components_missing")
    safe_identity = _safe_identity(identity)
    safe_canary = _safe_canary(canary, binary_identity=predecessor)
    if (safe_identity["refusal"] is not None
            or safe_identity["codex_binary"] != historical_binary
            or safe_identity["credential_lstat"] != historical_auth
            or safe_identity["expected_credential_kind"] != expected_kind
            or safe_identity["workspace_binding_class"] != workspace_binding_class):
        raise ReadinessError("requalification_identity_mismatch")
    # Exact reviewed failure class: no timeout, signal, missing result or
    # finalization failure may be promoted into evidence of a closed turn.
    if (safe_canary["passed"] is not False
            or type(safe_canary["exit_code"]) is not int or safe_canary["exit_code"] != 1
            or safe_canary["timed_out"] is not False
            or safe_canary["terminal_event_class"] != "provider_turn_failed"
            or safe_canary["result_valid"] is not False
            or safe_canary["refusal"] != "provider_turn_failed"):
        raise ReadinessError("requalification_effect_not_closed_terminal")
    observed = _timestamp(value["observed_at"], code="receipt_timestamp_malformed")
    for component in (safe_identity, safe_canary):
        if abs(_timestamp(component["observed_at"], code="receipt_timestamp_malformed") - observed) > MAX_CLOCK_SKEW:
            raise ReadinessError("requalification_component_timestamp_conflict")


def validate_revalidation_predecessor_document(
    value: Mapping[str, Any], *,
    auth_identity: Mapping[str, Any], binary_identity: Mapping[str, Any],
    expected_kind: str, workspace_binding_class: str,
    worker_uid: int = WORKER_UID, worker_gid: int = WORKER_GID,
) -> None:
    """Validate prior company device-auth PASS evidence without renewing it."""
    if (expected_kind != "device-auth"
            or workspace_binding_class != COMPANY_WORKSPACE_BINDING_CLASS
            or (worker_uid, worker_gid) != (WORKER_UID, WORKER_GID)):
        raise ReadinessError("revalidation_requires_company_device_auth")
    validate_receipt_document(
        value, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_kind=expected_kind, workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid, worker_gid=worker_gid, allow_expired_readiness=True,
    )
    identity = _safe_identity(value["provider_identity"])
    if (identity["refusal"] is not None
            or identity["workspace_binding_class"] != workspace_binding_class):
        raise ReadinessError("revalidation_provider_identity_conflict")


def classify_device_revalidation(
    value: Mapping[str, Any], *,
    auth_identity: Mapping[str, Any], binary_identity: Mapping[str, Any],
    expected_kind: str, workspace_binding_class: str,
    new_credential_expires_at: str,
    worker_uid: int = WORKER_UID, worker_gid: int = WORKER_GID,
) -> None:
    """Explicit bounded renewal requires new proof, never deadline-only reuse."""
    validate_revalidation_predecessor_document(
        value, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_kind=expected_kind, workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid, worker_gid=worker_gid,
    )
    current = datetime.now(UTC)
    prior = _timestamp(value["credential_expires_at"], code="credential_expiry_malformed")
    deadline = _timestamp(new_credential_expires_at, code="credential_expiry_malformed")
    if prior > current + MIN_ACCEPTANCE_MARGIN:
        raise ReadinessError("revalidation_not_due")
    if not (current + MIN_ACCEPTANCE_MARGIN < deadline <= current + MAX_REQUALIFICATION_HORIZON
            and deadline > prior):
        raise ReadinessError("revalidation_deadline_out_of_bounds")


def validate_company_device_drift_predecessor_document(
    value: Mapping[str, Any], *,
    auth_identity: Mapping[str, Any], binary_identity: Mapping[str, Any],
    expected_kind: str, workspace_binding_class: str,
    worker_uid: int = WORKER_UID, worker_gid: int = WORKER_GID,
) -> None:
    """Validate retained PASS evidence, without claiming old auth continuity.

    Only size/mtime/ctime may differ on the same dedicated credential inode.
    This is a current qualification, never evidence of who caused that drift.
    The receipt byte preimage is checked separately by the transaction owner.
    """
    if (expected_kind != "device-auth"
            or workspace_binding_class != COMPANY_WORKSPACE_BINDING_CLASS
            or (worker_uid, worker_gid) != (WORKER_UID, WORKER_GID)):
        raise ReadinessError("drift_requalification_requires_company_device_auth")
    historical = value.get("credential_lstat")
    fields = {"device", "inode", "uid", "gid", "mode", "size", "mtime_ns", "ctime_ns", "nlink"}
    for metadata in (historical, auth_identity):
        if (not isinstance(metadata, Mapping) or set(metadata) != fields
                or any(type(metadata[key]) is not int or metadata[key] < 0 for key in fields)
                or metadata["uid"] != WORKER_UID or metadata["gid"] != WORKER_GID
                or metadata["mode"] != 0o600 or metadata["nlink"] != 1
                or any(metadata[key] <= 0 for key in ("device", "inode", "size"))):
            raise ReadinessError("drift_requalification_credential_metadata_invalid")
    if (dict(historical) == dict(auth_identity)
            or any(historical[key] != auth_identity[key]
                   for key in fields - {"size", "mtime_ns", "ctime_ns"})):
        raise ReadinessError("drift_requalification_credential_changed")
    if (binary_identity.get("path") != os.fspath(CODEX_BINARY)
            or binary_identity.get("version") != CODEX_VERSION
            or binary_identity.get("sha256") != CODEX_SHA256
            or binary_identity.get("team_identifier") != CODEX_TEAM_ID):
        raise ReadinessError("drift_requalification_binary_unreviewed")
    # Validate the historical composite against its own historical credential,
    # while retaining exact equality to the current reviewed binary.
    validate_revalidation_predecessor_document(
        value, auth_identity=historical, binary_identity=binary_identity,
        expected_kind=expected_kind, workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid, worker_gid=worker_gid,
    )
    if _timestamp(value["credential_expires_at"], code="credential_expiry_malformed") > datetime.now(UTC):
        raise ReadinessError("drift_requalification_requires_expired_predecessor")


def classify_company_device_drift_requalification(
    value: Mapping[str, Any], *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any], expected_kind: str,
    workspace_binding_class: str, new_credential_expires_at: str,
    worker_uid: int = WORKER_UID, worker_gid: int = WORKER_GID,
) -> None:
    validate_company_device_drift_predecessor_document(
        value, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_kind=expected_kind, workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid, worker_gid=worker_gid,
    )
    current = datetime.now(UTC)
    deadline = _timestamp(new_credential_expires_at, code="credential_expiry_malformed")
    if not current + MIN_ACCEPTANCE_MARGIN < deadline <= current + MAX_REQUALIFICATION_HORIZON:
        raise ReadinessError("drift_requalification_deadline_out_of_bounds")


def _company_device_drift_preimage(
    args: argparse.Namespace, *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (args.requalify_company_device_drift_sha256 != COMPANY_DEVICE_DRIFT_PREDECESSOR_SHA256
            or args.receipt != RECEIPT_PATH or args.auth != AUTH_PATH
            or args.binary != CODEX_BINARY):
        raise ReadinessError("drift_requalification_unreviewed_preimage_or_path")
    return _explicit_requalification_preimage(
        args, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_digest=args.requalify_company_device_drift_sha256,
        classifier=classify_company_device_drift_requalification,
    )


def _device_revalidation_preimage(
    args: argparse.Namespace, *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return _explicit_requalification_preimage(
        args, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_digest=args.renew_device_revalidation_sha256,
        classifier=classify_device_revalidation,
    )


def _terminal_requalification_preimage(
    args: argparse.Namespace, *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return _explicit_requalification_preimage(
        args, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_digest=args.requalify_terminal_adverse_sha256,
        classifier=classify_terminal_requalification,
    )


def _explicit_requalification_preimage(
    args: argparse.Namespace, *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any], expected_digest: str, classifier: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(expected_digest, str) or SHA256_RE.fullmatch(expected_digest) is None:
        raise ReadinessError("requalification_receipt_digest_malformed")
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=args.workspace_binding_class, worker_gid=args.worker_gid,
    )
    first = lstat_identity(
        args.receipt, expected_uid=expected_uid, expected_gid=expected_gid,
        expected_mode=expected_mode,
    )
    document = _read_protected_receipt(
        args.receipt, workspace_binding_class=args.workspace_binding_class,
        worker_gid=args.worker_gid,
    )
    raw = args.receipt.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ReadinessError("requalification_receipt_digest_mismatch")
    try:
        raw_document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("requalification_receipt_changed") from exc
    if (raw_document != document or lstat_identity(
            args.receipt, expected_uid=expected_uid, expected_gid=expected_gid,
            expected_mode=expected_mode) != first):
        raise ReadinessError("requalification_receipt_changed")
    classifier(
        document, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_kind=args.expected_kind, workspace_binding_class=args.workspace_binding_class,
        new_credential_expires_at=args.credential_expires_at,
        worker_uid=args.worker_uid, worker_gid=args.worker_gid,
    )
    return document, first


def _current_pin_recovery_context(
    args: argparse.Namespace,
    *,
    auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
    observation_path: Path | None = None,
    qualification: Any = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str, Any]:
    """Return (document, receipt identity, grant, grant digest, preimage, identity).

    Every check here runs BEFORE any claim, archive, reservation or inference.
    The production qualification table is empty, so a production submission
    always stops at ``recovery_failure_cause_unproven``.  Recovery refusals are
    surfaced as ordinary readiness refusals so every entry point fails closed
    through one channel.
    """

    from ops.executive_os import provider_recovery as recovery

    try:
        return _current_pin_recovery_context_checked(
            args, auth_identity=auth_identity, binary_identity=binary_identity,
            observation_path=observation_path, qualification=qualification,
            recovery=recovery,
        )
    except recovery.RecoveryError as exc:
        raise ReadinessError(exc.code) from exc


def _current_pin_recovery_context_checked(
    args: argparse.Namespace,
    *,
    auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
    observation_path: Path | None,
    qualification: Any,
    recovery: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str, Any]:
    digest = args.recover_current_pin_grant_sha256
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        raise ReadinessError("recovery_grant_digest_malformed")
    request_id = getattr(args, "successor_request_id", None)
    if not isinstance(request_id, str) or re.fullmatch(
        r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$", request_id
    ) is None:
        raise ReadinessError("recovery_successor_request_malformed")
    if (args.expected_kind != "device-auth"
            or args.workspace_binding_class != COMPANY_WORKSPACE_BINDING_CLASS
            or (args.worker_uid, args.worker_gid) != (WORKER_UID, WORKER_GID)
            or args.receipt != RECEIPT_PATH or args.auth != AUTH_PATH
            or args.binary != CODEX_BINARY):
        raise ReadinessError("recovery_unreviewed_company_preimage")
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=args.workspace_binding_class, worker_gid=args.worker_gid,
    )
    receipt_identity = lstat_identity(
        args.receipt, expected_uid=expected_uid, expected_gid=expected_gid,
        expected_mode=expected_mode,
    )
    document = _read_protected_receipt(
        args.receipt, workspace_binding_class=args.workspace_binding_class,
        worker_gid=args.worker_gid,
    )
    raw = args.receipt.read_bytes()
    predecessor_digest = hashlib.sha256(raw).hexdigest()
    try:
        raw_document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("recovery_predecessor_changed") from exc
    if raw_document != document or lstat_identity(
        args.receipt, expected_uid=expected_uid, expected_gid=expected_gid,
        expected_mode=expected_mode,
    ) != receipt_identity:
        raise ReadinessError("recovery_predecessor_changed")
    _origin, grant = recovery.read_grant_for_admission(expected_digest=digest)
    if grant["successor_request_id"] != request_id:
        raise ReadinessError("recovery_successor_request_mismatch")
    context = recovery.admit_recovery_context(
        grant,
        grant_sha256=digest,
        **({} if qualification is None else {"qualification": qualification}),
    )
    if grant["executive_source"] != recovery.current_executive_source():
        raise ReadinessError("recovery_executive_source_mismatch")
    if context["admission_class"] == "ordinary":
        recovery.validate_original_terminal(context["cause"])
    else:
        # Incident admission: the exact validator already joined the designated
        # original terminal, the issuance commitment and the successful issuer
        # terminal.  Retained denial evidence still excludes admission, and no
        # claim that no denial occurred is ever manufactured from clean terms.
        recovery.refuse_evidenced_incident_denial(document)
    if context["original_receipt_sha256"] != predecessor_digest:
        raise ReadinessError("recovery_predecessor_preimage_mismatch")
    recovery.validate_current_pin_recovery_predecessor_document(
        document, grant=grant, auth_identity=auth_identity,
        binary_identity=binary_identity, expected_kind=args.expected_kind,
        workspace_binding_class=args.workspace_binding_class,
        worker_uid=args.worker_uid, worker_gid=args.worker_gid,
    )
    current = datetime.now(UTC)
    deadline = _timestamp(args.credential_expires_at, code="credential_expiry_malformed")
    if not current + MIN_ACCEPTANCE_MARGIN < deadline <= current + MAX_REQUALIFICATION_HORIZON:
        raise ReadinessError("recovery_deadline_out_of_bounds")
    if observation_path is not None:
        observation = recovery.validate_observation_document(
            _read_json(observation_path),
            successor_request_id=request_id,
            expected_kind=args.expected_kind,
            workspace_binding_class=args.workspace_binding_class,
            auth_identity=auth_identity,
            binary_identity=binary_identity,
        )
        fresh = _safe_identity(observation["provider_identity"])
        observed = _timestamp(fresh["observed_at"], code="identity_timestamp_malformed")
        if abs(current - observed) > MAX_CLOCK_SKEW:
            raise ReadinessError("requalification_fresh_identity_required")
        prior_identity = {
            **document["provider_identity"], "credential_lstat": auth_identity,
        }
        if _identity_stability_tuple(fresh) != _identity_stability_tuple(prior_identity):
            raise ReadinessError("requalification_provider_identity_changed")
    else:
        fresh = None
    return document, receipt_identity, grant, digest, predecessor_digest, fresh


def _current_pin_recovery_preimage(
    args: argparse.Namespace, *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read-only recovery eligibility check; never claims or archives."""

    document, receipt_identity, _grant, _digest, _preimage, _fresh = (
        _current_pin_recovery_context(
            args, auth_identity=auth_identity, binary_identity=binary_identity,
        )
    )
    return document, receipt_identity


def _reserve_current_pin_recovery(
    args: argparse.Namespace, *, auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any], qualification: Any = None,
) -> None:
    """Claim the one-use allocation, then CAS the reservation into place.

    The claim is durable and keyed by the original predecessor receipt digest
    and scope.  If the archive or CAS below fails, the budget stays consumed;
    only same-request status and reconciliation remain possible.
    """

    from ops.executive_os import provider_recovery as recovery

    if args.identity_json is not None or args.recovery_observation_json is None:
        raise ReadinessError("recovery_requires_bound_observation")
    try:
        (_document, receipt_identity, grant, digest, predecessor_digest, fresh) = (
            _current_pin_recovery_context(
                args, auth_identity=auth_identity, binary_identity=binary_identity,
                observation_path=args.recovery_observation_json,
                qualification=qualification,
            )
        )
        assert fresh is not None
        recovery.claim_or_refuse_allocation(
            recovery.RECOVERY_ALLOCATION_PATH,
            grant=grant,
            grant_sha256=digest,
            predecessor_receipt_sha256=predecessor_digest,
        )
    except recovery.RecoveryError as exc:
        raise ReadinessError(exc.code) from exc
    receipt = compose_reservation(
        identity=fresh, auth_identity=auth_identity, binary_identity=binary_identity,
        expected_kind=args.expected_kind, workspace_binding_class=args.workspace_binding_class,
        credential_expires_at=args.credential_expires_at,
        worker_uid=args.worker_uid, worker_gid=args.worker_gid,
    )
    refresh_expired_receipt(
        args.receipt, receipt, expected_identity=receipt_identity,
        workspace_binding_class=args.workspace_binding_class, worker_gid=args.worker_gid,
        expected_receipt_sha256=predecessor_digest,
    )


def receipt_storage_contract(
    *, workspace_binding_class: str | None, worker_gid: int
) -> tuple[int, int, int]:
    """Return the immutable authority-owned readability contract for one receipt."""

    binding = (
        WORKSPACE_BINDING_CLASS
        if workspace_binding_class is None
        else workspace_binding_class
    )
    if binding == COMPANY_WORKSPACE_BINDING_CLASS:
        return 0, 0, 0o400
    if binding == PERSONAL_PRO_WORKER_BINDING_CLASS:
        if isinstance(worker_gid, bool) or not isinstance(worker_gid, int):
            raise ReadinessError("readiness_receipt_reader_invalid")
        try:
            personal_slot_gids = {
                slot.worker_gid
                for slot in provider_worker_slots.all_slots()
                if slot.workspace_binding_class == PERSONAL_PRO_WORKER_BINDING_CLASS
            }
        except (AttributeError, provider_worker_slots.SlotCatalogError) as exc:
            raise ReadinessError("readiness_receipt_reader_invalid") from exc
        if worker_gid in personal_slot_gids:
            return 0, worker_gid, 0o440
    raise ReadinessError("readiness_receipt_reader_invalid")

def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("json_unreadable") from exc
    if not isinstance(value, dict):
        raise ReadinessError("json_not_object")
    return value


def _read_protected_receipt(
    path: Path,
    *,
    workspace_binding_class: str | None = None,
    worker_gid: int = WORKER_GID,
) -> dict[str, Any]:
    _validate_receipt_directory(path)
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    info = path.lstat()
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid != expected_uid
        or info.st_gid != expected_gid
        or stat.S_IMODE(info.st_mode) != expected_mode
        or info.st_nlink != 1
    ):
        raise ReadinessError("readiness_receipt_metadata_unsafe")
    _assert_no_macos_acl(path)
    return _read_json(path)


def validate_receipt_file(
    path: Path = RECEIPT_PATH,
    *,
    auth_path: Path = AUTH_PATH,
    binary_path: Path = CODEX_BINARY,
    expected_kind: str | None = None,
    workspace_binding_class: str | None = None,
    credential_expires_at: str | None = None,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
) -> dict[str, Any]:
    value = _read_protected_receipt(
        path,
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    auth_identity = current_auth_identity(
        auth_path, worker_uid=worker_uid, worker_gid=worker_gid
    )
    validate_receipt_document(
        value,
        auth_identity=auth_identity,
        binary_identity=current_binary_identity(binary_path),
        expected_kind=expected_kind,
        workspace_binding_class=workspace_binding_class,
        worker_uid=worker_uid,
        worker_gid=worker_gid,
    )
    if (
        credential_expires_at is not None
        and value.get("credential_expires_at") != credential_expires_at
    ):
        raise ReadinessError("readiness_credential_expiry_mismatch")
    return value


def compose_reservation(
    *,
    identity: Mapping[str, Any],
    auth_identity: Mapping[str, Any],
    binary_identity: Mapping[str, Any],
    expected_kind: str,
    workspace_binding_class: str,
    credential_expires_at: str,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
) -> dict[str, Any]:
    if expected_kind not in EXPECTED_KINDS:
        raise ReadinessError("credential_kind_unknown")
    if workspace_binding_class not in WORKSPACE_BINDING_CLASSES:
        raise ReadinessError("workspace_attestation_missing")
    _assert_worker_identity(
        auth_identity, worker_uid=worker_uid, worker_gid=worker_gid
    )
    safe_identity = _safe_identity(identity)
    if safe_identity["expected_credential_kind"] != expected_kind:
        raise ReadinessError("credential_kind_mismatch")
    if safe_identity["workspace_binding_class"] != workspace_binding_class:
        raise ReadinessError("workspace_attestation_mismatch")
    if safe_identity["codex_binary"] != dict(binary_identity):
        raise ReadinessError("identity_binary_mismatch")
    if safe_identity["credential_lstat"] != dict(auth_identity):
        raise ReadinessError("identity_credential_mismatch")
    observed_at, credential_expiry, readiness_expiry = _deadline_fields(
        credential_expires_at=credential_expires_at
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": False,
        "refusal": "canary_reserved",
        "observed_at": observed_at,
        "credential_expires_at": credential_expiry,
        "readiness_expires_at": readiness_expiry,
        "expected_credential_kind": expected_kind,
        "workspace_binding_class": workspace_binding_class,
        "forced_chatgpt_workspace_id_applied": False,
        "credential_lstat": dict(auth_identity),
        "codex_binary": dict(binary_identity),
        "provider_identity": safe_identity,
        "inference_canary": None,
    }


def validate_reservation_document(
    value: Mapping[str, Any],
    *,
    expected_kind: str,
    workspace_binding_class: str,
    credential_expires_at: str,
    worker_uid: int = WORKER_UID,
    worker_gid: int = WORKER_GID,
) -> dict[str, Any]:
    if set(value) != _RECEIPT_FIELDS:
        raise ReadinessError("reservation_fields_malformed")
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("passed") is not False
        or value.get("refusal") != "canary_reserved"
        or value.get("expected_credential_kind") != expected_kind
        or value.get("workspace_binding_class") != workspace_binding_class
        or value.get("credential_expires_at") != credential_expires_at
        or value.get("forced_chatgpt_workspace_id_applied") is not False
        or value.get("inference_canary") is not None
    ):
        raise ReadinessError("reservation_malformed")
    _deadline_fields(
        observed_at=value.get("observed_at"),
        credential_expires_at=value.get("credential_expires_at"),
        readiness_expires_at=value.get("readiness_expires_at"),
    )
    identity = value.get("provider_identity")
    if not isinstance(identity, Mapping):
        raise ReadinessError("reservation_identity_missing")
    safe_identity = _safe_identity(identity)
    if safe_identity["expected_credential_kind"] != expected_kind:
        raise ReadinessError("reservation_kind_mismatch")
    if safe_identity["workspace_binding_class"] != workspace_binding_class:
        raise ReadinessError("reservation_workspace_mismatch")
    credential_lstat = value.get("credential_lstat")
    if not isinstance(credential_lstat, Mapping):
        raise ReadinessError("reservation_credential_conflict")
    _assert_worker_identity(
        credential_lstat, worker_uid=worker_uid, worker_gid=worker_gid
    )
    if safe_identity["credential_lstat"] != value.get("credential_lstat"):
        raise ReadinessError("reservation_credential_conflict")
    if safe_identity["codex_binary"] != value.get("codex_binary"):
        raise ReadinessError("reservation_binary_conflict")
    return safe_identity


def _identity_stability_tuple(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(
        value[key]
        for key in (
            "expected_credential_kind",
            "auth_mode",
            "account_type",
            "plan_type",
            "requires_openai_auth",
            "workspace_binding_class",
            "forced_chatgpt_workspace_id_applied",
            "credential_lstat",
        )
    )


def compose_adverse_from_reservation(
    reservation: Mapping[str, Any],
    *,
    refusal: str,
    auth_identity: Mapping[str, Any] | None = None,
    binary_identity: Mapping[str, Any] | None = None,
    identity: Mapping[str, Any] | None = None,
    canary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a sanitized burn marker; it can never validate as READY."""

    safe_refusal = refusal if re.fullmatch(r"[a-z0-9_]{1,80}", refusal) else "finalization_failed"
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": False,
        "refusal": safe_refusal,
        "observed_at": now_iso(),
        "credential_expires_at": reservation.get("credential_expires_at"),
        "readiness_expires_at": reservation.get("readiness_expires_at"),
        "expected_credential_kind": reservation.get("expected_credential_kind"),
        "workspace_binding_class": reservation.get("workspace_binding_class"),
        "forced_chatgpt_workspace_id_applied": False,
        "credential_lstat": dict(auth_identity or reservation.get("credential_lstat") or {}),
        "codex_binary": dict(binary_identity or reservation.get("codex_binary") or {}),
        "provider_identity": dict(identity or reservation.get("provider_identity") or {}),
        "inference_canary": dict(canary) if isinstance(canary, Mapping) else None,
    }


def _validate_receipt_directory(path: Path) -> None:
    ancestors = (
        Path("/Library"),
        Path("/Library/Application Support"),
        RECEIPT_PATH.parent.parent,
        RECEIPT_PATH.parent,
    ) if path.parent == RECEIPT_PATH.parent else (path.parent,)
    for ancestor in ancestors:
        info = ancestor.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != 0
            or (stat.S_IMODE(info.st_mode) & 0o022) != 0
        ):
            raise ReadinessError("readiness_parent_unsafe")
        _assert_no_macos_acl(ancestor)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def invalidate_receipt_file(
    path: Path = RECEIPT_PATH,
    *,
    workspace_binding_class: str | None = None,
    worker_gid: int = WORKER_GID,
) -> None:
    """Remove one metadata-safe readiness receipt and durably fsync its parent."""

    _validate_receipt_directory(path)
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    first_identity = lstat_identity(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
    )
    if lstat_identity(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
    ) != first_identity:
        raise ReadinessError("readiness_receipt_changed_before_invalidation")
    path.unlink()
    _fsync_directory(path.parent)


def persist_receipt(
    path: Path,
    value: Mapping[str, Any],
    *,
    workspace_binding_class: str | None = None,
    worker_gid: int = WORKER_GID,
) -> None:
    _validate_receipt_directory(path)
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    payload = (json.dumps(dict(value), sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, expected_mode)
    try:
        os.fchown(descriptor, expected_uid, expected_gid)
        os.fchmod(descriptor, expected_mode)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ReadinessError("readiness_receipt_short_write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _assert_no_macos_acl(path)
    _fsync_directory(path.parent)


def replace_reserved_receipt(
    path: Path,
    value: Mapping[str, Any],
    *,
    expected_reservation_identity: Mapping[str, Any],
    workspace_binding_class: str | None = None,
    worker_gid: int = WORKER_GID,
) -> None:
    """Atomically replace an existing reservation with its final receipt."""

    _validate_receipt_directory(path)
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    payload = (json.dumps(dict(value), sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.final-", dir=os.fspath(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, expected_mode)
        os.fchown(descriptor, expected_uid, expected_gid)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ReadinessError("readiness_receipt_short_write")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        _assert_no_macos_acl(temporary)
        if lstat_identity(
            path,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=expected_mode,
        ) != dict(expected_reservation_identity):
            raise ReadinessError("reservation_changed_before_finalization")
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _superseded_sibling_path(path: Path, original_bytes: bytes) -> Path:
    digest = hashlib.sha256(original_bytes).hexdigest()[:16]
    return path.with_name(f"{path.name}.superseded-{digest}.json")


def _persist_superseded_receipt(
    superseded_path: Path,
    original_bytes: bytes,
    *,
    workspace_binding_class: str | None,
    worker_gid: int,
) -> None:
    """Write a byte-identical copy of the superseded live receipt as evidence.

    Idempotent after a crash: if the sibling already exists with the same
    bytes, accept it; if it exists with different bytes, refuse with
    ``superseded_receipt_conflict`` and leave the live receipt untouched.
    """

    _validate_receipt_directory(superseded_path)
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    if superseded_path.exists() or superseded_path.is_symlink():
        try:
            lstat_identity(
                superseded_path,
                expected_uid=expected_uid,
                expected_gid=expected_gid,
                expected_mode=expected_mode,
            )
        except ReadinessError as exc:
            raise ReadinessError("superseded_receipt_conflict") from exc
        existing = superseded_path.read_bytes()
        if existing == original_bytes:
            return
        raise ReadinessError("superseded_receipt_conflict")
    # Crash-safe write: stage to a sibling-local temp file, then atomically
    # rename over the digest-named path.  A SIGINT/power loss before the
    # rename leaves no partial file at the digest name, so the next retry
    # can simply re-create it cleanly.  Because the destination name is a
    # digest of the bytes being written, ``os.replace`` is idempotent and
    # cannot clobber divergent evidence (a divergent file at that name was
    # already refused by the exists-branch above).
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{superseded_path.name}.tmp-", dir=os.fspath(superseded_path.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, expected_mode)
        os.fchown(descriptor, expected_uid, expected_gid)
        view = memoryview(original_bytes)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ReadinessError("readiness_receipt_short_write")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        _assert_no_macos_acl(temporary)
        os.replace(temporary, superseded_path)
        _fsync_directory(superseded_path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def refresh_expired_receipt(
    path: Path,
    value: Mapping[str, Any],
    *,
    expected_identity: Mapping[str, Any],
    workspace_binding_class: str | None = None,
    worker_gid: int = WORKER_GID,
    expected_receipt_sha256: str | None = None,
    current_identity_guard: Callable[[], None] | None = None,
) -> None:
    """Replace a validated predecessor with a reservation, preserving evidence.

    Callers must separately classify expiry refresh or explicit terminal-adverse
    requalification; this storage primitive does not grant either transition.

    ``expected_identity`` is the lstat identity of the live receipt captured
    BEFORE preservation; if it changes between supersede and replace, the
    function refuses with ``receipt_changed_before_refresh``.
    """

    _validate_receipt_directory(path)
    if current_identity_guard is not None:
        current_identity_guard()
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    if lstat_identity(
        path,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
    ) != dict(expected_identity):
        raise ReadinessError("receipt_changed_before_refresh")
    original_bytes = path.read_bytes()
    if (expected_receipt_sha256 is not None
            and hashlib.sha256(original_bytes).hexdigest() != expected_receipt_sha256):
        raise ReadinessError("requalification_receipt_digest_mismatch")
    superseded_path = _superseded_sibling_path(path, original_bytes)
    _persist_superseded_receipt(
        superseded_path,
        original_bytes,
        workspace_binding_class=workspace_binding_class,
        worker_gid=worker_gid,
    )
    payload = (json.dumps(dict(value), sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.refresh-", dir=os.fspath(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, expected_mode)
        os.fchown(descriptor, expected_uid, expected_gid)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ReadinessError("readiness_receipt_short_write")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        _assert_no_macos_acl(temporary)
        if lstat_identity(
            path,
            expected_uid=expected_uid,
            expected_gid=expected_gid,
            expected_mode=expected_mode,
        ) != dict(expected_identity):
            raise ReadinessError("receipt_changed_before_refresh")
        if current_identity_guard is not None:
            current_identity_guard()
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the Executive provider readiness receipt")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--receipt", type=Path, default=RECEIPT_PATH)
    validate.add_argument("--auth", type=Path, default=AUTH_PATH)
    validate.add_argument("--binary", type=Path, default=CODEX_BINARY)
    validate.add_argument("--worker-uid", type=int, default=WORKER_UID)
    validate.add_argument("--worker-gid", type=int, default=WORKER_GID)
    reuse = sub.add_parser("reuse")
    reuse.add_argument("--receipt", type=Path, default=RECEIPT_PATH)
    reuse.add_argument("--auth", type=Path, default=AUTH_PATH)
    reuse.add_argument("--binary", type=Path, default=CODEX_BINARY)
    reuse.add_argument("--expected-kind", choices=sorted(EXPECTED_KINDS), required=True)
    reuse.add_argument("--workspace-binding-class", required=True)
    reuse.add_argument("--credential-expires-at", required=True)
    reuse.add_argument("--worker-uid", type=int, default=WORKER_UID)
    reuse.add_argument("--worker-gid", type=int, default=WORKER_GID)
    reuse_replacement = reuse.add_mutually_exclusive_group()
    reuse_replacement.add_argument("--requalify-terminal-adverse-sha256")
    reuse_replacement.add_argument("--renew-device-revalidation-sha256")
    reuse_replacement.add_argument("--requalify-company-device-drift-sha256")
    reuse_replacement.add_argument("--recover-current-pin-grant-sha256")
    reuse.add_argument("--successor-request-id")
    reserve = sub.add_parser("reserve")
    reserve.add_argument("--receipt", type=Path, default=RECEIPT_PATH)
    reserve.add_argument("--auth", type=Path, default=AUTH_PATH)
    reserve.add_argument("--binary", type=Path, default=CODEX_BINARY)
    reserve.add_argument("--identity-json", type=Path)
    reserve.add_argument("--expected-kind", choices=sorted(EXPECTED_KINDS), required=True)
    reserve.add_argument("--workspace-binding-class", required=True)
    reserve.add_argument("--credential-expires-at", required=True)
    reserve.add_argument("--worker-uid", type=int, default=WORKER_UID)
    reserve.add_argument("--worker-gid", type=int, default=WORKER_GID)
    replacement = reserve.add_mutually_exclusive_group()
    replacement.add_argument("--requalify-terminal-adverse-sha256")
    replacement.add_argument("--renew-device-revalidation-sha256")
    replacement.add_argument("--requalify-company-device-drift-sha256")
    replacement.add_argument("--recover-current-pin-grant-sha256")
    replacement.add_argument(
        "--refresh-expired",
        action="store_true",
        help="Replace an expired passing device-auth receipt (must already exist).",
    )
    reserve.add_argument("--successor-request-id")
    reserve.add_argument("--recovery-observation-json", type=Path)
    invalidate = sub.add_parser("invalidate")
    invalidate.add_argument("--receipt", type=Path, default=RECEIPT_PATH)
    invalidate.add_argument("--workspace-binding-class")
    invalidate.add_argument("--worker-gid", type=int, default=WORKER_GID)
    finalize = sub.add_parser("finalize")
    finalize.add_argument("--receipt", type=Path, default=RECEIPT_PATH)
    finalize.add_argument("--auth", type=Path, default=AUTH_PATH)
    finalize.add_argument("--binary", type=Path, default=CODEX_BINARY)
    finalize.add_argument("--post-identity-json", type=Path, required=True)
    finalize.add_argument("--post-identity-command-status", type=int, required=True)
    finalize.add_argument("--canary-json", type=Path, required=True)
    finalize.add_argument("--canary-command-status", type=int, required=True)
    finalize.add_argument("--expected-kind", choices=sorted(EXPECTED_KINDS), required=True)
    finalize.add_argument("--workspace-binding-class", required=True)
    finalize.add_argument("--credential-expires-at", required=True)
    finalize.add_argument("--worker-uid", type=int, default=WORKER_UID)
    finalize.add_argument("--worker-gid", type=int, default=WORKER_GID)
    return parser


def _finalize(args: argparse.Namespace) -> int:
    expected_uid, expected_gid, expected_mode = receipt_storage_contract(
        workspace_binding_class=args.workspace_binding_class,
        worker_gid=args.worker_gid,
    )
    reservation_identity = lstat_identity(
        args.receipt,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=expected_mode,
    )
    reservation = _read_protected_receipt(
        args.receipt,
        workspace_binding_class=args.workspace_binding_class,
        worker_gid=args.worker_gid,
    )
    pre_identity = validate_reservation_document(
        reservation,
        expected_kind=args.expected_kind,
        workspace_binding_class=args.workspace_binding_class,
        credential_expires_at=args.credential_expires_at,
        worker_uid=args.worker_uid,
        worker_gid=args.worker_gid,
    )
    final_auth: dict[str, Any] | None = None
    final_binary: dict[str, Any] | None = None
    post_identity: dict[str, Any] | None = None
    canary: dict[str, Any] | None = None
    try:
        final_auth = current_auth_identity(
            args.auth, worker_uid=args.worker_uid, worker_gid=args.worker_gid
        )
        final_binary = current_binary_identity(args.binary)
        if reservation.get("codex_binary") != final_binary:
            raise ReadinessError("binary_changed_during_canary")
        if reservation.get("credential_lstat") != final_auth:
            raise ReadinessError("credential_changed_during_canary")
        if args.post_identity_command_status != 0:
            raise ReadinessError("post_identity_command_failed")
        post_identity = _safe_identity(_read_json(args.post_identity_json))
        if post_identity["codex_binary"] != final_binary:
            raise ReadinessError("post_identity_binary_mismatch")
        if pre_identity["credential_lstat"] != post_identity["credential_lstat"]:
            raise ReadinessError("credential_changed_during_canary")
        if _identity_stability_tuple(pre_identity) != _identity_stability_tuple(post_identity):
            raise ReadinessError("provider_identity_changed_during_canary")
        canary = _safe_canary(_read_json(args.canary_json))
        receipt = compose_receipt(
            identity=post_identity,
            canary=canary,
            auth_identity=final_auth,
            binary_identity=final_binary,
            expected_kind=args.expected_kind,
            workspace_binding_class=args.workspace_binding_class,
            credential_expires_at=args.credential_expires_at,
            readiness_expires_at=str(reservation["readiness_expires_at"]),
            canary_command_status=args.canary_command_status,
            worker_uid=args.worker_uid,
            worker_gid=args.worker_gid,
        )
    except (ReadinessError, OSError) as exc:
        receipt = compose_adverse_from_reservation(
            reservation,
            refusal=str(exc),
            auth_identity=final_auth,
            binary_identity=final_binary,
            identity=post_identity,
            canary=canary,
        )
    replace_reserved_receipt(
        args.receipt,
        receipt,
        expected_reservation_identity=reservation_identity,
        workspace_binding_class=args.workspace_binding_class,
        worker_gid=args.worker_gid,
    )
    if receipt.get("passed") is not True:
        return 2
    validate_receipt_file(
        args.receipt,
        auth_path=args.auth,
        binary_path=args.binary,
        expected_kind=args.expected_kind,
        workspace_binding_class=args.workspace_binding_class,
        credential_expires_at=args.credential_expires_at,
        worker_uid=args.worker_uid,
        worker_gid=args.worker_gid,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            validate_receipt_file(
                args.receipt,
                auth_path=args.auth,
                binary_path=args.binary,
                worker_uid=args.worker_uid,
                worker_gid=args.worker_gid,
            )
            return 0
        if args.command == "reuse":
            if (args.successor_request_id is not None
                    and args.recover_current_pin_grant_sha256 is None):
                raise ReadinessError("recovery_arguments_are_recovery_only")
            if args.requalify_company_device_drift_sha256 is not None:
                _company_device_drift_preimage(
                    args, auth_identity=current_auth_identity(
                        args.auth, worker_uid=args.worker_uid, worker_gid=args.worker_gid,
                    ), binary_identity=current_binary_identity(args.binary),
                )
                return 7
            if args.renew_device_revalidation_sha256 is not None:
                _device_revalidation_preimage(
                    args, auth_identity=current_auth_identity(
                        args.auth, worker_uid=args.worker_uid, worker_gid=args.worker_gid,
                    ), binary_identity=current_binary_identity(args.binary),
                )
                return 6
            if args.requalify_terminal_adverse_sha256 is not None:
                _terminal_requalification_preimage(
                    args, auth_identity=current_auth_identity(
                        args.auth, worker_uid=args.worker_uid, worker_gid=args.worker_gid,
                    ), binary_identity=current_binary_identity(args.binary),
                )
                return 5
            if args.recover_current_pin_grant_sha256 is not None:
                _current_pin_recovery_preimage(
                    args, auth_identity=current_auth_identity(
                        args.auth, worker_uid=args.worker_uid, worker_gid=args.worker_gid,
                    ), binary_identity=current_binary_identity(args.binary),
                )
                return 8
            if not args.receipt.exists() and not args.receipt.is_symlink():
                return 3
            try:
                validate_receipt_file(
                    args.receipt,
                    auth_path=args.auth,
                    binary_path=args.binary,
                    expected_kind=args.expected_kind,
                    workspace_binding_class=args.workspace_binding_class,
                    credential_expires_at=args.credential_expires_at,
                    worker_uid=args.worker_uid,
                    worker_gid=args.worker_gid,
                )
                return 0
            except ReadinessError:
                if not args.receipt.exists() and not args.receipt.is_symlink():
                    raise
                document = _read_protected_receipt(
                    args.receipt,
                    workspace_binding_class=args.workspace_binding_class,
                    worker_gid=args.worker_gid,
                )
                auth_identity = current_auth_identity(
                    args.auth,
                    worker_uid=args.worker_uid,
                    worker_gid=args.worker_gid,
                )
                binary_identity = current_binary_identity(args.binary)
                classify_refresh_eligibility(
                    document,
                    auth_identity=auth_identity,
                    binary_identity=binary_identity,
                    expected_kind=args.expected_kind,
                    workspace_binding_class=args.workspace_binding_class,
                    worker_uid=args.worker_uid,
                    worker_gid=args.worker_gid,
                    new_credential_expires_at=args.credential_expires_at,
                )
                return 4
        if args.command == "invalidate":
            invalidate_receipt_file(
                args.receipt,
                workspace_binding_class=args.workspace_binding_class,
                worker_gid=args.worker_gid,
            )
            return 0
        if args.command == "reserve":
            auth_identity = current_auth_identity(
                args.auth,
                worker_uid=args.worker_uid,
                worker_gid=args.worker_gid,
            )
            binary_identity = current_binary_identity(args.binary)
            if args.recover_current_pin_grant_sha256 is not None:
                if (args.successor_request_id is None
                        or args.recovery_observation_json is None
                        or args.identity_json is not None
                        or args.refresh_expired):
                    raise ReadinessError("recovery_requires_bound_observation")
                _reserve_current_pin_recovery(
                    args, auth_identity=auth_identity, binary_identity=binary_identity,
                )
                return 0
            if (args.successor_request_id is not None
                    or args.recovery_observation_json is not None):
                raise ReadinessError("recovery_arguments_are_recovery_only")
            if args.identity_json is None:
                raise ReadinessError("identity_json_required")
            identity_payload = _read_json(args.identity_json)
            if (args.requalify_company_device_drift_sha256 is not None
                    or args.requalify_terminal_adverse_sha256 is not None
                    or args.renew_device_revalidation_sha256 is not None):
                preimage = (_company_device_drift_preimage
                            if args.requalify_company_device_drift_sha256 is not None
                            else _device_revalidation_preimage
                            if args.renew_device_revalidation_sha256 is not None
                            else _terminal_requalification_preimage)
                document, receipt_identity = preimage(
                    args, auth_identity=auth_identity, binary_identity=binary_identity,
                )
                fresh = _safe_identity(identity_payload)
                if (args.requalify_company_device_drift_sha256 is not None
                        and fresh["refusal"] is not None):
                    raise ReadinessError("drift_requalification_fresh_identity_refused")
                observed = _timestamp(fresh["observed_at"], code="identity_timestamp_malformed")
                if abs(datetime.now(UTC) - observed) > MAX_CLOCK_SKEW:
                    raise ReadinessError("requalification_fresh_identity_required")
                # The chosen explicit transition validated its own historical
                # evidence. The drift route does not claim historical auth
                # continuity. Fresh policy and exact current auth still bind
                # the reservation and the unchanged post-inference comparator.
                prior_identity = {
                    **document["provider_identity"], "credential_lstat": auth_identity,
                }
                if _identity_stability_tuple(fresh) != _identity_stability_tuple(prior_identity):
                    raise ReadinessError("requalification_provider_identity_changed")
                receipt = compose_reservation(
                    identity=fresh, auth_identity=auth_identity, binary_identity=binary_identity,
                    expected_kind=args.expected_kind, workspace_binding_class=args.workspace_binding_class,
                    credential_expires_at=args.credential_expires_at,
                    worker_uid=args.worker_uid, worker_gid=args.worker_gid,
                )
                identity_guard = None
                if args.requalify_company_device_drift_sha256 is not None:
                    # Freeze both observations across the durable archive and
                    # final receipt CAS. A race leaves old bytes and evidence.
                    expected_auth = dict(auth_identity)
                    expected_binary = dict(binary_identity)
                    def identity_guard() -> None:
                        if (current_auth_identity(
                                args.auth, worker_uid=args.worker_uid, worker_gid=args.worker_gid,
                            ) != expected_auth
                                or current_binary_identity(args.binary) != expected_binary):
                            raise ReadinessError("drift_requalification_identity_changed_before_reservation")
                refresh_expired_receipt(
                    args.receipt, receipt, expected_identity=receipt_identity,
                    workspace_binding_class=args.workspace_binding_class, worker_gid=args.worker_gid,
                    expected_receipt_sha256=(args.requalify_company_device_drift_sha256
                                             or args.requalify_terminal_adverse_sha256
                                             or args.renew_device_revalidation_sha256),
                    current_identity_guard=identity_guard,
                )
                return 0
            if args.refresh_expired:
                if not args.receipt.exists() and not args.receipt.is_symlink():
                    raise ReadinessError("refresh_requires_existing_receipt")
                expected_uid, expected_gid, expected_mode = receipt_storage_contract(
                    workspace_binding_class=args.workspace_binding_class,
                    worker_gid=args.worker_gid,
                )
                receipt_identity = lstat_identity(
                    args.receipt,
                    expected_uid=expected_uid,
                    expected_gid=expected_gid,
                    expected_mode=expected_mode,
                )
                document = _read_protected_receipt(
                    args.receipt,
                    workspace_binding_class=args.workspace_binding_class,
                    worker_gid=args.worker_gid,
                )
                classify_refresh_eligibility(
                    document,
                    auth_identity=auth_identity,
                    binary_identity=binary_identity,
                    expected_kind=args.expected_kind,
                    workspace_binding_class=args.workspace_binding_class,
                    worker_uid=args.worker_uid,
                    worker_gid=args.worker_gid,
                    new_credential_expires_at=args.credential_expires_at,
                )
                receipt = compose_reservation(
                    identity=identity_payload,
                    auth_identity=auth_identity,
                    binary_identity=binary_identity,
                    expected_kind=args.expected_kind,
                    workspace_binding_class=args.workspace_binding_class,
                    credential_expires_at=args.credential_expires_at,
                    worker_uid=args.worker_uid,
                    worker_gid=args.worker_gid,
                )
                refresh_expired_receipt(
                    args.receipt,
                    receipt,
                    expected_identity=receipt_identity,
                    workspace_binding_class=args.workspace_binding_class,
                    worker_gid=args.worker_gid,
                )
                return 0
            receipt = compose_reservation(
                identity=identity_payload,
                auth_identity=auth_identity,
                binary_identity=binary_identity,
                expected_kind=args.expected_kind,
                workspace_binding_class=args.workspace_binding_class,
                credential_expires_at=args.credential_expires_at,
                worker_uid=args.worker_uid,
                worker_gid=args.worker_gid,
            )
            persist_receipt(
                args.receipt,
                receipt,
                workspace_binding_class=args.workspace_binding_class,
                worker_gid=args.worker_gid,
            )
            return 0
        return _finalize(args)
    except (ReadinessError, OSError) as exc:
        print(f"provider readiness refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
