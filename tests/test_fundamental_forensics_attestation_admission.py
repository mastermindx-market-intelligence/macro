"""FIF D2 — attestation admission state contracts (A13 / A18 / A52-seam).

Offline and deterministic: no network, no clock reads, no fixture mutation.
Every fixture path on disk is swept as a candidate source and refused, the
OBSERVED 2026-10-12 writer metadata yields the post-rotation-failure human
gate, and no input can produce an attestation or a historic-capture basis.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import re

import jsonschema
import pytest

from engine.fundamental_forensics import attestation_admission as aa
from engine.fundamental_forensics.attestation_admission import (
    ADMISSION_STATES,
    ALLOWED_SECRET_NAMES,
    ATTESTATION_ADMISSION_SCHEMA,
    CAPTURE_BASES,
    REFUSAL_CODES,
    SEED_WORKFLOW,
    WRITER_ENVIRONMENT,
    AttestationAdmissionRefused,
    build_admission_status,
    resolve_capture_basis,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "fundamental_forensics_attestation_admission.schema.json"
SEED_SCRIPT_PATH = REPO_ROOT / "scripts" / "seed_fundamental_forensics_attested_history.py"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "fundamental_forensics"

OBSERVED_AT = "2026-10-12T00:00:00Z"
FAILED_STEP = "acquire bounded AAPL seed and run zero-write preflight"

# The 2026-10-12 observed writer metadata (metadata APIs only; no secret value
# exists anywhere in this fixture — secret NAMES and timestamps only).  Only
# the two _SEED_ writer keys carry observed rotation stamps.
OBSERVED_EVIDENCE = {
    "repository": "mastermindx-market-intelligence/macro",
    "environment": {
        "name": "attested-history-seed",
        "required_reviewers": ["chriswong6031-creator"],
    },
    "writer_secrets": [
        {"name": "R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID", "updated_at": "2026-09-29T06:06:34Z"},
        {"name": "R2_ATTESTED_HISTORY_SEED_SECRET_ACCESS_KEY", "updated_at": "2026-09-29T06:06:40Z"},
    ],
    "last_seed_run": {
        "run_id": "36397411740",
        "workflow": "attested-history-aapl-seed",
        "event": "workflow_dispatch",
        "branch": "main",
        "created_at": "2026-09-28T08:26:53Z",
        "run_attempt": 2,
        "attempt_started_at": "2026-09-29T07:34:44Z",
        "completed_at": "2026-09-29T08:17:43Z",
        "conclusion": "failure",
        "failed_step": FAILED_STEP,
    },
    "candidate_sources": [
        "engine/fundamental_forensics/attestation_admission.py",
        "research/FIF_D2_ATTESTATION_ADMISSION_GATE_2026-10-12.md",
    ],
}


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _evidence(**overrides) -> dict:
    evidence = copy.deepcopy(OBSERVED_EVIDENCE)
    evidence.update(overrides)
    return evidence


def _refusal(code: str, evidence: dict, observed_at: str = OBSERVED_AT):
    with pytest.raises(AttestationAdmissionRefused) as excinfo:
        build_admission_status(evidence, observed_at=observed_at)
    assert excinfo.value.code == code
    assert excinfo.value.code in REFUSAL_CODES
    return excinfo.value


# --- (a) the observed metadata yields the post-rotation-failure gate --------


def test_observed_metadata_is_unresolved_human_gate_post_rotation_failure():
    status = build_admission_status(OBSERVED_EVIDENCE, observed_at=OBSERVED_AT)
    assert status["schema"] == ATTESTATION_ADMISSION_SCHEMA == "fundamental_forensics.attestation_admission/v1"
    assert status["state"] == "unresolved_human_gate"
    assert status["attested"] is False
    assert status["capture_basis"] == "reconstruction"
    assert status["observed_at"] == OBSERVED_AT
    assert re.fullmatch(r"ffadm_[0-9a-f]{32}", status["admission_id"])

    gate = status["gate"]
    assert gate["case"] == "post_rotation_attempt_failed"
    assert gate["who"] == ["chriswong6031-creator", "Chairman"]
    assert "36397411740" in gate["why"]
    assert FAILED_STEP in gate["why"]
    assert "2026-09-29T07:34:44Z" in gate["why"]
    assert "2026-09-29T06:06:40Z" in gate["why"]  # writer-key rotation stamp
    assert SEED_WORKFLOW in gate["what"]
    assert WRITER_ENVIRONMENT in gate["what"]
    for action in (
        "dispatch",
        "secret",
        "writer path",
        "attested",
    ):
        assert any(action in line for line in gate["forbidden_agent_actions"])

    for fragment in ("no secret value", "no workflow was dispatched", "not an attestation", "reconstruction"):
        assert any(fragment in claim for claim in status["nonclaims"])

    assert status["evidence"] == OBSERVED_EVIDENCE
    jsonschema.validate(instance=status, schema=_contract())


# --- (b) the other two gate cases still refuse to attest --------------------


def test_no_post_rotation_attempt_case():
    pre_rotation = _evidence(
        last_seed_run={
            "run_id": "36397411740",
            "workflow": SEED_WORKFLOW,
            "event": "workflow_dispatch",
            "branch": "main",
            "created_at": "2026-09-28T08:26:53Z",
            "run_attempt": 1,
            "attempt_started_at": "2026-09-28T09:00:00Z",
            "completed_at": "2026-09-28T09:40:00Z",
            "conclusion": "failure",
            "failed_step": FAILED_STEP,
        }
    )
    for evidence in (pre_rotation, _evidence(last_seed_run=None)):
        status = build_admission_status(evidence, observed_at=OBSERVED_AT)
        assert status["gate"]["case"] == "no_post_rotation_attempt"
        assert status["state"] == "unresolved_human_gate"
        assert status["attested"] is False
        assert status["capture_basis"] == "reconstruction"
        assert "enable_aapl_seed=true" in status["gate"]["what"]
        jsonschema.validate(instance=status, schema=_contract())

    no_run = copy.deepcopy(OBSERVED_EVIDENCE)
    del no_run["last_seed_run"]
    status = build_admission_status(no_run, observed_at=OBSERVED_AT)
    assert status["gate"]["case"] == "no_post_rotation_attempt"
    assert status["attested"] is False
    jsonschema.validate(instance=status, schema=_contract())


def test_seed_succeeded_case_still_refuses_admission():
    succeeded = _evidence(
        last_seed_run={
            "run_id": "36397411741",
            "workflow": SEED_WORKFLOW,
            "event": "workflow_dispatch",
            "branch": "main",
            "run_attempt": 1,
            "attempt_started_at": "2026-10-01T00:00:00Z",
            "completed_at": "2026-10-01T00:20:00Z",
            "conclusion": "success",
        }
    )
    status = build_admission_status(succeeded, observed_at=OBSERVED_AT)
    assert status["gate"]["case"] == "seed_succeeded"
    assert status["state"] == "unresolved_human_gate"
    assert status["attested"] is False
    assert "verify_fundamental_forensics_attested_history_seed_bundle.py" in status["gate"]["what"]
    jsonschema.validate(instance=status, schema=_contract())


# --- (c) every fixture on disk is refused as a candidate source -------------


def test_every_disk_fixture_is_refused_as_candidate_source():
    paths = sorted(
        "tests/fixtures/fundamental_forensics/" + p.relative_to(FIXTURE_ROOT).as_posix()
        for p in FIXTURE_ROOT.rglob("*")
        if p.is_file()
    )
    assert "tests/fixtures/fundamental_forensics/aapl_10k_2025/package_manifest.json" in paths
    assert paths, "fixture tree missing from this checkout"
    for path in paths:
        _refusal("fixture_source_refused", _evidence(candidate_sources=[path]))
    _refusal(
        "fixture_source_refused",
        _evidence(candidate_sources=["engine/x.py", "vendor/fixtures/thing.json"]),
    )


# --- (d) evidence vocabulary refusals ---------------------------------------


def test_secret_value_keys_refused_before_allowlist():
    nested_token = _evidence()
    nested_token["environment"]["required_reviewers"] = [{"login": "x", "token": "y"}]
    _refusal("secret_value_refused", nested_token)

    _refusal(
        "secret_value_refused",
        _evidence(
            writer_secrets=[
                {"name": "R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID", "updated_at": "2026-09-29T06:06:34Z"},
                {"name": "R2_ATTESTED_HISTORY_SEED_SECRET_ACCESS_KEY", "value": "x"},
            ]
        ),
    )
    _refusal(
        "secret_value_refused",
        _evidence(
            writer_secrets=[
                {"name": "R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID", "ACCESS_KEY": "x", "updated_at": "2026-09-29T06:06:34Z"}
            ]
        ),
    )
    # A secret NAME as a string VALUE is legitimate evidence, not a leak.
    status = build_admission_status(
        _evidence(environment={"name": WRITER_ENVIRONMENT, "required_reviewers": ["R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID"]}),
        observed_at=OBSERVED_AT,
    )
    assert status["state"] == "unresolved_human_gate"


def test_unknown_secret_name_refused():
    _refusal(
        "unknown_secret_name",
        _evidence(
            writer_secrets=[
                {"name": "R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID", "updated_at": "2026-09-29T06:06:34Z"},
                {"name": "R2_GENERIC_FALLBACK_KEY", "updated_at": "2026-09-29T06:06:34Z"},
            ]
        ),
    )


def test_unexpected_evidence_key_refused_top_level_and_nested():
    top = _evidence()
    top["actor"] = "chriswong6031-creator"
    _refusal("unexpected_evidence_key", top)

    nested = _evidence()
    nested["environment"]["url"] = "https://example.invalid"
    _refusal("unexpected_evidence_key", nested)


def test_missing_evidence_refused():
    without_environment = copy.deepcopy(OBSERVED_EVIDENCE)
    del without_environment["environment"]
    _refusal("missing_evidence", without_environment)

    without_secrets = copy.deepcopy(OBSERVED_EVIDENCE)
    del without_secrets["writer_secrets"]
    _refusal("missing_evidence", without_secrets)

    incomplete_run = _evidence(last_seed_run={"run_id": "36397411740", "conclusion": "failure"})
    _refusal("missing_evidence", incomplete_run)


def test_malformed_evidence_timestamp_refused():
    bad_run = _evidence()
    bad_run["last_seed_run"]["attempt_started_at"] = "2026-09-29 07:34:44"
    _refusal("malformed_timestamp", bad_run)

    _refusal("malformed_timestamp", _evidence(), observed_at="2026-10-12T00:00:00")


# --- (e) resolve_capture_basis ----------------------------------------------


@pytest.mark.parametrize(
    "admission",
    [
        None,
        {},
        {"state": "unresolved_human_gate"},
        {"state": "refused"},
        {"attested": False},
        {"schema": ATTESTATION_ADMISSION_SCHEMA, "state": "unresolved_human_gate", "attested": False},
    ],
)
def test_capture_basis_is_never_historic_capture(admission):
    basis = resolve_capture_basis(
        source_accepted_at="2025-09-27T00:00:00Z",
        capture_recorded_at="2026-10-12T00:00:00Z",
        admission=admission,
    )
    assert basis == "reconstruction"
    assert basis in CAPTURE_BASES
    assert basis != "historic_capture"


def test_capture_basis_accepts_module_built_status():
    status = build_admission_status(OBSERVED_EVIDENCE, observed_at=OBSERVED_AT)
    assert (
        resolve_capture_basis(
            source_accepted_at="2025-09-27T00:00:00Z",
            capture_recorded_at="2026-10-12T00:00:00Z",
            admission=status,
        )
        == "reconstruction"
    )


def test_capture_basis_refuses_attestation_claims():
    accepted = "2025-09-27T00:00:00Z"
    recorded = "2026-10-12T00:00:00Z"
    for claim in ({"state": "admitted"}, {"state": "unresolved_human_gate", "attested": True}):
        with pytest.raises(AttestationAdmissionRefused) as excinfo:
            resolve_capture_basis(source_accepted_at=accepted, capture_recorded_at=recorded, admission=claim)
        assert excinfo.value.code == "attestation_claim_refused"


def test_capture_basis_clock_order_violation():
    with pytest.raises(AttestationAdmissionRefused) as excinfo:
        resolve_capture_basis(
            source_accepted_at="2026-10-12T00:00:01Z",
            capture_recorded_at="2026-10-12T00:00:00Z",
        )
    assert excinfo.value.code == "clock_order_violation"
    # Equal clocks are not a violation (recorded at the same instant as accepted).
    assert (
        resolve_capture_basis(
            source_accepted_at="2026-10-12T00:00:00Z",
            capture_recorded_at="2026-10-12T00:00:00+00:00",
        )
        == "reconstruction"
    )


@pytest.mark.parametrize(
    "accepted,recorded",
    [
        ("2026-10-12T00:00:00", "2026-10-13T00:00:00Z"),
        ("not-a-date", "2026-10-13T00:00:00Z"),
        ("2026-10-12T00:00:00+02:00", "2026-10-13T00:00:00Z"),
        ("2026-10-12T00:00:00Z", 12345),
        (None, "2026-10-13T00:00:00Z"),
        ("2026-10-12T00:00:00Z", "2026-10-12"),
    ],
)
def test_capture_basis_malformed_timestamps(accepted, recorded):
    with pytest.raises(AttestationAdmissionRefused) as excinfo:
        resolve_capture_basis(source_accepted_at=accepted, capture_recorded_at=recorded)
    assert excinfo.value.code == "malformed_timestamp"


# --- (f) determinism and input immutability ---------------------------------


def test_admission_id_determinism_and_input_immutability():
    original = copy.deepcopy(OBSERVED_EVIDENCE)
    first = build_admission_status(OBSERVED_EVIDENCE, observed_at=OBSERVED_AT)
    second = build_admission_status(OBSERVED_EVIDENCE, observed_at=OBSERVED_AT)
    assert first == second
    assert first["admission_id"] == second["admission_id"]
    assert OBSERVED_EVIDENCE == original  # input never mutated

    later = build_admission_status(OBSERVED_EVIDENCE, observed_at="2026-10-12T00:01:00Z")
    assert later["admission_id"] != first["admission_id"]

    assert first["evidence"] is not OBSERVED_EVIDENCE
    first["evidence"]["environment"]["name"] = "mutated-after-build"
    assert OBSERVED_EVIDENCE["environment"]["name"] == "attested-history-seed"


def test_admission_id_is_derived_from_canonical_payload():
    payload = json.dumps(
        {"schema": ATTESTATION_ADMISSION_SCHEMA, "observed_at": OBSERVED_AT, "evidence": OBSERVED_EVIDENCE},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    status = build_admission_status(OBSERVED_EVIDENCE, observed_at=OBSERVED_AT)
    assert status["admission_id"] == "ffadm_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


# --- (g) AST drift pin against the human-owned seed script ------------------


def test_seed_script_constants_pinned_by_ast():
    tree = ast.parse(SEED_SCRIPT_PATH.read_text(encoding="utf-8"))
    literals: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "EXPECTED_GITHUB_ENVIRONMENT",
                    "EXPECTED_GITHUB_WORKFLOW",
                }:
                    assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                    literals[target.id] = node.value.value
    assert literals == {
        "EXPECTED_GITHUB_ENVIRONMENT": WRITER_ENVIRONMENT,
        "EXPECTED_GITHUB_WORKFLOW": SEED_WORKFLOW,
    }


# --- (h) module purity -------------------------------------------------------


def test_module_source_is_pure():
    source = Path(aa.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "datetime.now",
        "time.time",
        "date.today",
        "import requests",
        "import httpx",
        "import boto",
        "import urllib",
        "import socket",
        "import subprocess",
        "from scripts",
        "attested_history_credentials",
    ):
        assert forbidden not in source, forbidden


def test_vocabulary_constants():
    assert ADMISSION_STATES == ("admitted", "unresolved_human_gate", "refused")
    assert CAPTURE_BASES == ("historic_capture", "reconstruction")
    assert ALLOWED_SECRET_NAMES == frozenset(
        {
            "R2_ATTESTED_HISTORY_ENDPOINT",
            "R2_ATTESTED_HISTORY_BUCKET",
            "R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID",
            "R2_ATTESTED_HISTORY_SEED_SECRET_ACCESS_KEY",
            "R2_ATTESTED_HISTORY_READONLY_ACCESS_KEY_ID",
            "R2_ATTESTED_HISTORY_READONLY_SECRET_ACCESS_KEY",
        }
    )
