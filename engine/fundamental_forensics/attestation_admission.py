"""FIF D2 — attestation admission state (pure, fail-closed, value-free).

This module makes "no lawful attestation exists" an explicit, machine-checkable
state instead of an absence.  It owns the admission vocabulary that the
publication plane (D3) may later reference: every capture it can describe is
``reconstruction``; ``historic_capture`` is not derivable in v1; ``admitted``
is reserved and unreachable because no verifiable signed trust anchor exists
(a self-asserted "admitted" mapping is exactly the forged attestation this
module exists to refuse).

Four clocks never collapse into one here: ``source_accepted_at`` (when the
source world accepted a fact), ``capture_recorded_at`` (when we observed and
recorded bytes), ``observed_at`` (when this admission status was built from
metadata), and the writer-key rotation stamp inside the evidence.  A
comparative reprint is not a restatement, and rounded consistency is not
transitive — so nothing in this module upgrades evidence into trust.

Purity contract: no I/O, no filesystem, no network, no subprocess, no clock
read — every time is an explicit argument.  It handles secret NAMES and
metadata timestamps only; any mapping key that looks like a secret VALUE
container is refused before any other evidence check, so the refusal names
the real danger.  The attested-history writer/credential path is human-owned;
this module never imports it, exercises it, or re-implements it.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any, NoReturn

ATTESTATION_ADMISSION_SCHEMA = "fundamental_forensics.attestation_admission/v1"

# ``admitted`` is RESERVED: v1 can never reach it (no verifiable signed trust
# anchor exists).  ``refused`` materialises as ``AttestationAdmissionRefused``.
ADMISSION_STATES = ("admitted", "unresolved_human_gate", "refused")

# ``historic_capture`` exists in the vocabulary so callers can name what does
# NOT exist yet; no function in this module can return it in v1.
CAPTURE_BASES = ("historic_capture", "reconstruction")

# Duplicated deliberately from the human-owned seed script
# (scripts/seed_fundamental_forensics_attested_history.py constants
# EXPECTED_GITHUB_ENVIRONMENT / EXPECTED_GITHUB_WORKFLOW).  A test pins the
# two literals equal by AST so drift fails CI instead of silently forking the
# writer-environment identity.
WRITER_ENVIRONMENT = "attested-history-seed"
SEED_WORKFLOW = "attested-history-aapl-seed"

# Repository secret NAMES only — never values, never env mappings.
ALLOWED_SECRET_NAMES = frozenset(
    {
        "R2_ATTESTED_HISTORY_ENDPOINT",
        "R2_ATTESTED_HISTORY_BUCKET",
        "R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID",
        "R2_ATTESTED_HISTORY_SEED_SECRET_ACCESS_KEY",
        "R2_ATTESTED_HISTORY_READONLY_ACCESS_KEY_ID",
        "R2_ATTESTED_HISTORY_READONLY_SECRET_ACCESS_KEY",
    }
)

REFUSAL_CODES = frozenset(
    {
        "unexpected_evidence_key",
        "secret_value_refused",
        "unknown_secret_name",
        "fixture_source_refused",
        "malformed_timestamp",
        "clock_order_violation",
        "attestation_claim_refused",
        "missing_evidence",
    }
)

# Case-insensitive mapping KEY names that would carry a secret VALUE.  Keys
# only — never string values, because legitimate secret NAMES contain words
# like ACCESS_KEY.  Checked across the whole evidence tree before any
# allowlist so the error names the real danger.
_FORBIDDEN_VALUE_KEYS = frozenset(
    {
        "value",
        "secret",
        "secret_value",
        "plaintext",
        "token",
        "password",
        "access_key",
        "secret_access_key",
    }
)

_TOP_LEVEL_KEYS = frozenset(
    {"repository", "environment", "writer_secrets", "last_seed_run", "candidate_sources"}
)
_ENVIRONMENT_KEYS = frozenset({"name", "required_reviewers"})
_WRITER_SECRET_KEYS = frozenset({"name", "updated_at"})
_SEED_RUN_KEYS = frozenset(
    {
        "run_id",
        "workflow",
        "event",
        "branch",
        "created_at",
        "run_attempt",
        "attempt_started_at",
        "completed_at",
        "conclusion",
        "failed_step",
    }
)
_SEED_RUN_REQUIRED = ("run_id", "conclusion", "attempt_started_at")
_SEED_RUN_TIMESTAMPS = ("created_at", "attempt_started_at", "completed_at")

# Aware ISO-8601 UTC only: ``Z`` or ``+00:00`` suffix, ``T`` separator.
# Naive, offset, and non-ISO shapes are all ``malformed_timestamp``.
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)$"
)

GATE_CASES = ("no_post_rotation_attempt", "post_rotation_attempt_failed", "seed_succeeded")

_NONCLAIMS = (
    "no secret value was read, printed, rotated or stored; only secret NAMES and metadata timestamps appear in this status",
    "no workflow was dispatched, rerun or re-run in producing this status",
    "this status is not an attestation and does not attest anything; attested is false",
    "fixture bytes and any bytes fetched today are reconstruction, never historic attestation",
    "state 'admitted' is reserved and unreachable in v1: no verifiable signed trust anchor exists",
    "'historic_capture' is not derivable from this module in v1",
)

_FORBIDDEN_AGENT_ACTIONS = (
    "dispatch, rerun or re-run any GitHub Actions workflow (never rerun seed run 31534160304, nor FF-1R runs 32626273461 or 32708350406)",
    "read, print, rotate or store any secret value (secret NAMES are the only credential fact this module ever handles)",
    "debug, repair, replace, wrap or re-implement the human-owned attested-history writer path",
    "label any capture, fixture or reconstruction as attested, or mint any ffatt_ id from fetched-today bytes",
)


class AttestationAdmissionRefused(ValueError):
    """Evidence or an admission claim that v1 must refuse, with a machine code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in REFUSAL_CODES:
            raise ValueError(f"refusal code outside the closed set: {code!r}")
        super().__init__(message)
        self.code = code


def _refuse(code: str, message: str) -> NoReturn:
    raise AttestationAdmissionRefused(code, message)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _parse_utc_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC_RE.match(value):
        _refuse(
            "malformed_timestamp",
            f"{field} must be an aware ISO-8601 UTC string ending in 'Z' or '+00:00', got {value!r}",
        )
    normalised = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        _refuse("malformed_timestamp", f"{field} is not a parseable ISO-8601 UTC instant: {value!r}")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        _refuse("malformed_timestamp", f"{field} must carry a zero-offset UTC designator: {value!r}")
    return parsed


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _check_keys(mapping: Mapping, allowed: frozenset, where: str) -> None:
    for key in mapping:
        if key not in allowed:
            _refuse(
                "unexpected_evidence_key",
                f"evidence key {key!r} at {where} is outside the allowlist {sorted(allowed)}",
            )


def _scan_secret_value_keys(node: Any, where: str = "evidence") -> None:
    """Pass 1 — refuse any mapping key that would carry a secret VALUE.

    Runs over the whole tree before any allowlist check so a value-shaped key
    nested under an unexpected parent is still reported as the danger it is.
    """
    if _is_mapping(node):
        for key in node:
            if isinstance(key, str) and key.strip().lower() in _FORBIDDEN_VALUE_KEYS:
                _refuse(
                    "secret_value_refused",
                    f"evidence key {key!r} at {where} looks like a secret VALUE container; "
                    "this module accepts secret NAMES only",
                )
        for key, child in node.items():
            _scan_secret_value_keys(child, f"{where}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, child in enumerate(node):
            _scan_secret_value_keys(child, f"{where}[{index}]")


def _validate_string_list(value: Any, where: str) -> None:
    if not isinstance(value, (list, tuple)):
        _refuse("unexpected_evidence_key", f"{where} must be a list, got {type(value).__name__}")
    for index, item in enumerate(value):
        if not isinstance(item, str):
            _refuse(
                "unexpected_evidence_key",
                f"{where}[{index}] must be a string, got {type(item).__name__}",
            )


def _validate_evidence(evidence: Any) -> None:
    """Pass 2 — strict allowlists, types, secret names, fixture refusal."""
    if not _is_mapping(evidence):
        _refuse("unexpected_evidence_key", f"evidence must be a mapping, got {type(evidence).__name__}")
    _check_keys(evidence, _TOP_LEVEL_KEYS, "evidence")

    if "repository" in evidence and not isinstance(evidence["repository"], str):
        _refuse("unexpected_evidence_key", "evidence.repository must be a string")

    environment = evidence.get("environment")
    if environment is not None:
        if not _is_mapping(environment):
            _refuse("unexpected_evidence_key", "evidence.environment must be a mapping")
        _check_keys(environment, _ENVIRONMENT_KEYS, "evidence.environment")
        if "name" in environment and not isinstance(environment["name"], str):
            _refuse("unexpected_evidence_key", "evidence.environment.name must be a string")
        if "required_reviewers" in environment:
            _validate_string_list(environment["required_reviewers"], "evidence.environment.required_reviewers")

    writer_secrets = evidence.get("writer_secrets")
    if writer_secrets is not None:
        if not isinstance(writer_secrets, (list, tuple)):
            _refuse("unexpected_evidence_key", "evidence.writer_secrets must be a list")
        for index, entry in enumerate(writer_secrets):
            where = f"evidence.writer_secrets[{index}]"
            if not _is_mapping(entry):
                _refuse("unexpected_evidence_key", f"{where} must be a mapping")
            _check_keys(entry, _WRITER_SECRET_KEYS, where)
            for required in ("name", "updated_at"):
                if required not in entry:
                    _refuse("missing_evidence", f"{where} is missing required key {required!r}")
            if not isinstance(entry["name"], str):
                _refuse("unexpected_evidence_key", f"{where}.name must be a string")
            if entry["name"] not in ALLOWED_SECRET_NAMES:
                _refuse(
                    "unknown_secret_name",
                    f"{where}.name {entry['name']!r} is not one of the six known repository secret names",
                )
            _parse_utc_timestamp(entry["updated_at"], f"{where}.updated_at")

    seed_run = evidence.get("last_seed_run")
    if seed_run is not None:
        where = "evidence.last_seed_run"
        if not _is_mapping(seed_run):
            _refuse("unexpected_evidence_key", f"{where} must be a mapping or null")
        _check_keys(seed_run, _SEED_RUN_KEYS, where)
        for required in _SEED_RUN_REQUIRED:
            if required not in seed_run:
                _refuse("missing_evidence", f"{where} is missing required key {required!r}")
        if not isinstance(seed_run["run_id"], (str, int)):
            _refuse("unexpected_evidence_key", f"{where}.run_id must be a string or integer")
        if not isinstance(seed_run["conclusion"], str):
            _refuse("unexpected_evidence_key", f"{where}.conclusion must be a string")
        if not isinstance(seed_run["run_attempt"], (str, int)):
            _refuse("unexpected_evidence_key", f"{where}.run_attempt must be a string or integer")
        for field in ("workflow", "event", "branch", "failed_step"):
            if field in seed_run and seed_run[field] is not None and not isinstance(seed_run[field], str):
                _refuse("unexpected_evidence_key", f"{where}.{field} must be a string or null")
        for field in _SEED_RUN_TIMESTAMPS:
            if field in seed_run:
                _parse_utc_timestamp(seed_run[field], f"{where}.{field}")

    if "candidate_sources" in evidence:
        candidate_sources = evidence["candidate_sources"]
        if not isinstance(candidate_sources, (list, tuple)):
            _refuse("unexpected_evidence_key", "evidence.candidate_sources must be a list")
        for index, path in enumerate(candidate_sources):
            if not isinstance(path, str):
                _refuse(
                    "unexpected_evidence_key",
                    f"evidence.candidate_sources[{index}] must be a repo-relative path string",
                )
            if path.startswith("tests/fixtures/") or "/fixtures/" in path:
                _refuse(
                    "fixture_source_refused",
                    f"candidate source {path!r} is a test fixture; fixture bytes are reconstruction "
                    "and can never be attested",
                )


def _writer_rotation(evidence: Mapping) -> tuple[datetime | None, str | None]:
    """Latest ``updated_at`` over writer secrets whose NAME contains ``_SEED_``."""
    latest_dt: datetime | None = None
    latest_str: str | None = None
    for entry in evidence.get("writer_secrets", ()):
        if "_SEED_" not in entry["name"]:
            continue
        stamp = _parse_utc_timestamp(entry["updated_at"], f"writer secret {entry['name']}")
        if latest_dt is None or stamp > latest_dt:
            latest_dt = stamp
            latest_str = entry["updated_at"]
    return latest_dt, latest_str


def _select_gate_case(seed_run: Mapping | None, rotated_at: datetime | None) -> str:
    if not seed_run:
        return "no_post_rotation_attempt"
    started = _parse_utc_timestamp(seed_run["attempt_started_at"], "evidence.last_seed_run.attempt_started_at")
    if rotated_at is not None and started >= rotated_at:
        if seed_run["conclusion"] == "success":
            return "seed_succeeded"
        return "post_rotation_attempt_failed"
    return "no_post_rotation_attempt"


def _build_gate(evidence: Mapping, case: str) -> dict:
    environment = evidence.get("environment") or {}
    reviewers = [r for r in (environment.get("required_reviewers") or ()) if isinstance(r, str)]
    who = [*reviewers, "Chairman"]
    seed_run = evidence.get("last_seed_run") or None
    _, rotated_str = _writer_rotation(evidence)
    rotation_text = rotated_str if rotated_str is not None else "unknown (no _SEED_ writer secret stamp in evidence)"

    if case == "no_post_rotation_attempt":
        if seed_run is None:
            why = (
                f"no seed run is recorded in evidence, so no attempt exists after the writer-key "
                f"rotation {rotation_text}"
            )
        else:
            why = (
                f"the latest recorded seed attempt (run {seed_run['run_id']}, attempt "
                f"{seed_run['run_attempt']}) started at {seed_run['attempt_started_at']}, before the "
                f"writer-key rotation {rotation_text}, so no post-rotation attempt exists"
            )
        what = (
            f"An operator-approved workflow_dispatch of workflow '{SEED_WORKFLOW}' on 'refs/heads/main' "
            f"with input enable_aapl_seed=true, approved in the '{WRITER_ENVIRONMENT}' environment by a "
            f"required reviewer."
        )
        next_lawful_action = (
            "A required reviewer or the Chairman verifies the protected writer environment out of band "
            "(writer-key stamp advanced past every prior attempt, required reviewers present, main ref), "
            "then performs the approved dispatch; an agent may never perform it."
        )
    elif case == "post_rotation_attempt_failed":
        failed_step = seed_run.get("failed_step")
        failed_step_text = failed_step if failed_step else "(failed step not recorded in evidence)"
        why = (
            f"seed run {seed_run['run_id']} attempt {seed_run['run_attempt']} started "
            f"{seed_run['attempt_started_at']} at/after the writer-key rotation {rotation_text} and "
            f"concluded '{seed_run['conclusion']}' at step {failed_step_text!r}; the post-rotation writer "
            f"path itself has failed, so re-dispatching without human diagnosis would only repeat it"
        )
        what = (
            f"Operator (human) diagnosis of the protected writer path at the failed step named in "
            f"evidence — out of band, in the human-owned lane — followed by an operator-approved "
            f"workflow_dispatch of '{SEED_WORKFLOW}' on 'refs/heads/main' with enable_aapl_seed=true in "
            f"the '{WRITER_ENVIRONMENT}' environment."
        )
        next_lawful_action = (
            "The Chairman or a required reviewer diagnoses the failed step out of band, fixes or rules on "
            "the writer path in the human-owned lane, and only then approves a fresh dispatch; agents "
            "prepare evidence and nothing more."
        )
    else:  # seed_succeeded
        why = (
            f"seed run {seed_run['run_id']} attempt {seed_run['run_attempt']} started "
            f"{seed_run['attempt_started_at']} at/after the writer-key rotation {rotation_text} and "
            f"concluded 'success'; v1 still cannot verify a signed trust anchor, so the state stays "
            f"'unresolved_human_gate' with attested=false until that verification is commissioned"
        )
        what = (
            "A separately commissioned verification of that seed bundle with "
            "scripts/verify_fundamental_forensics_attested_history_seed_bundle.py, before any admission "
            "can exist."
        )
        next_lawful_action = (
            "Commission the seed-bundle verification as its own bounded task (operator or commissioned "
            "lane); only a future, separately reviewed module version may define the admission step."
        )

    return {
        "case": case,
        "what": what,
        "who": who,
        "why": why,
        "next_lawful_action": next_lawful_action,
        "forbidden_agent_actions": list(_FORBIDDEN_AGENT_ACTIONS),
    }


def build_admission_status(evidence: Mapping, *, observed_at: str) -> dict:
    """Build a NON-SECRET admission status from strictly allowlisted metadata.

    Refuses (as ``AttestationAdmissionRefused``) any value-shaped key, unknown
    secret name, fixture candidate source, unexpected key, malformed timestamp,
    or missing ``environment``/``writer_secrets`` block.  For every lawful
    input in v1 the result is ``state='unresolved_human_gate'``,
    ``attested=False``, ``capture_basis='reconstruction'`` — never an
    admission, never ``historic_capture``.
    """
    # Validated only; ``observed_at`` never mixes into the evidence clocks.
    _parse_utc_timestamp(observed_at, "observed_at")

    _scan_secret_value_keys(evidence)
    _validate_evidence(evidence)
    if evidence.get("environment") is None:
        _refuse("missing_evidence", "evidence.environment is required (the writer environment identity)")
    if evidence.get("writer_secrets") is None:
        _refuse("missing_evidence", "evidence.writer_secrets is required (writer-key rotation stamps)")

    seed_run = evidence.get("last_seed_run") or None
    rotated_at, _ = _writer_rotation(evidence)
    case = _select_gate_case(seed_run, rotated_at)

    payload = _canonical_json(
        {
            "schema": ATTESTATION_ADMISSION_SCHEMA,
            "observed_at": observed_at,
            "evidence": evidence,
        }
    )
    admission_id = "ffadm_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    return {
        "schema": ATTESTATION_ADMISSION_SCHEMA,
        "admission_id": admission_id,
        "state": "unresolved_human_gate",
        "attested": False,
        "capture_basis": "reconstruction",
        "observed_at": observed_at,
        "evidence": deepcopy(evidence),
        "gate": _build_gate(evidence, case),
        "nonclaims": list(_NONCLAIMS),
    }


def resolve_capture_basis(
    *,
    source_accepted_at: str,
    capture_recorded_at: str,
    admission: Mapping | None = None,
) -> str:
    """Classify HOW bytes came into the house: ``reconstruction`` in v1.

    The two clocks are distinct inputs and are never merged, rewritten, or
    returned as one: recording before acceptance is a ``clock_order_violation``.
    An admission claiming ``state='admitted'`` or any truthy ``attested`` is
    refused — v1 cannot verify such a claim, and honouring it would be the
    forged attestation this module exists to prevent.  ``historic_capture`` is
    never returned in v1.
    """
    accepted = _parse_utc_timestamp(source_accepted_at, "source_accepted_at")
    recorded = _parse_utc_timestamp(capture_recorded_at, "capture_recorded_at")
    if recorded < accepted:
        _refuse(
            "clock_order_violation",
            f"capture_recorded_at {capture_recorded_at!r} precedes source_accepted_at "
            f"{source_accepted_at!r}; the observation clock may not run before the source clock",
        )
    if admission is not None:
        if not _is_mapping(admission):
            _refuse("unexpected_evidence_key", "admission must be a mapping or None")
        if admission.get("state") == "admitted":
            _refuse(
                "attestation_claim_refused",
                "admission claims state 'admitted'; v1 has no verifiable signed trust anchor and "
                "cannot honour an admitted claim",
            )
        if admission.get("attested"):
            _refuse(
                "attestation_claim_refused",
                "admission carries a truthy 'attested' claim; v1 cannot verify it and refuses the claim",
            )
    return "reconstruction"
