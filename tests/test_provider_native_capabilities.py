from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from engine import provider_native_capabilities as pnc


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "config/provider_native_capabilities.v1.json"
MODULE_PATH = "engine/provider_native_capabilities.py"
V1_ENGINE_SHA256 = "48a6661f7ea5b78e8a677645536d9daf714d31115868e86e135e8009443719bf"
V1_CLI_SHA256 = "6688e6278a8cde7107b4f565d381ca57314a71913f50606f231835bb4e3e20f5"
CAPABILITY_ID = "ncap_0123456789abcdef0123456789abcdef"


def _row(
    *,
    capability_id: str = CAPABILITY_ID,
    generation: int = 1,
    state: str = "registered",
) -> dict[str, object]:
    return {
        "capacity_capability_id": capability_id,
        "capability_generation": generation,
        "provider": "claude",
        "billing_mode": "subscription",
        "credential_kind": "attached_login",
        "execution_surface": "native_cli",
        "registration_state": state,
    }


def _registry(*rows: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "mastermind.provider_native_capability_registry/v1",
        "owner_program": "shared-ai-provider-control",
        "capabilities": list(rows),
    }


def _fact_digest(fact: dict[str, object]) -> str:
    unsigned = dict(fact)
    unsigned.pop("registration_receipt_digest")
    payload = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_registry_is_closed_and_opaque() -> None:
    document = _registry(_row())
    assert pnc.validate_registry(document) == (document["capabilities"][0],)

    extra = copy.deepcopy(document)
    extra["unexpected"] = True
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="REGISTRY_SCHEMA_INVALID"):
        pnc.validate_registry(extra)

    semantic_id = _registry(_row(capability_id="claude_account_1"))
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="CAPABILITY_ID_INVALID"):
        pnc.validate_registry(semantic_id)

    bad_generation = _registry(_row(generation=True))
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="CAPABILITY_GENERATION_INVALID"):
        pnc.validate_registry(bad_generation)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "anthropic"),
        ("billing_mode", "api"),
        ("credential_kind", "oauth"),
        ("execution_surface", "api"),
        ("registration_state", "unknown"),
    ],
)
def test_row_constants_are_closed(field: str, value: object) -> None:
    row = _row()
    row[field] = value
    with pytest.raises(pnc.ProviderNativeCapabilityError):
        pnc.validate_registry(_registry(row))


def test_duplicate_current_identity_refuses() -> None:
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="DUPLICATE_CAPABILITY_ID"):
        pnc.validate_registry(_registry(_row(), _row()))


def test_initial_registration_must_be_registered() -> None:
    pnc.validate_transition(None, _registry(_row()))
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="INITIAL_STATE_INVALID"):
        pnc.validate_transition(None, _registry(_row(state="revoked")))


def test_registered_to_revoked_retains_generation() -> None:
    previous = _registry(_row(generation=4, state="registered"))
    current = _registry(_row(generation=4, state="revoked"))
    pnc.validate_transition(previous, current)


def test_revoked_reenrollment_requires_strictly_new_generation() -> None:
    previous = _registry(_row(generation=4, state="revoked"))
    pnc.validate_transition(previous, _registry(_row(generation=5, state="registered")))

    with pytest.raises(pnc.ProviderNativeCapabilityError, match="GENERATION_REUSE"):
        pnc.validate_transition(previous, _registry(_row(generation=4, state="registered")))

    with pytest.raises(pnc.ProviderNativeCapabilityError, match="GENERATION_DECREMENT"):
        pnc.validate_transition(previous, _registry(_row(generation=3, state="registered")))


def test_source_reversion_to_older_registered_generation_refuses() -> None:
    previous = _registry(_row(generation=9, state="revoked"))
    reverted = _registry(_row(generation=2, state="registered"))
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="GENERATION_DECREMENT"):
        pnc.validate_transition(previous, reverted)


def test_registered_generation_cannot_change_without_revocation() -> None:
    previous = _registry(_row(generation=4, state="registered"))
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="GENERATION_TRANSITION_INVALID"):
        pnc.validate_transition(previous, _registry(_row(generation=5, state="registered")))


def test_row_removal_after_registration_refuses() -> None:
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="REGISTERED_ID_REMOVED"):
        pnc.validate_transition(_registry(_row()), _registry())


def test_new_identity_cannot_start_revoked() -> None:
    previous = _registry(_row())
    second = "ncap_fedcba9876543210fedcba9876543210"
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="INITIAL_STATE_INVALID"):
        pnc.validate_transition(previous, _registry(_row(), _row(capability_id=second, state="revoked")))


def test_registration_export_is_closed_and_deterministic() -> None:
    material = "a" * 64
    facts = pnc._registration_facts(_registry(_row(generation=7)), material_source_digest=material)
    assert len(facts) == 1
    fact = facts[0]
    assert set(fact) == {
        "schema",
        "capacity_capability_id",
        "capability_generation",
        "provider",
        "billing_mode",
        "credential_kind",
        "execution_surface",
        "registration_state",
        "material_source_digest",
        "registration_receipt_digest",
    }
    assert fact["schema"] == "mastermind.provider_native_capability_registration/v1"
    assert fact["material_source_digest"] == material
    assert fact["registration_receipt_digest"] == _fact_digest(fact)
    assert pnc._registration_facts(_registry(_row(generation=7)), material_source_digest=material) == facts


def test_revoked_export_is_truthful_and_deterministic() -> None:
    fact = pnc._registration_facts(
        _registry(_row(generation=8, state="revoked")),
        material_source_digest="b" * 64,
    )[0]
    assert fact["registration_state"] == "revoked"
    assert fact["registration_receipt_digest"] == _fact_digest(fact)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _init_fixture_repo(tmp_path: Path, current: dict[str, object], previous: dict[str, object] | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "engine").mkdir()
    shutil.copy2(ROOT / MODULE_PATH, repo / MODULE_PATH)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "B1 Test"], check=True)

    if previous is not None:
        (repo / REGISTRY_PATH).write_text(json.dumps(previous, sort_keys=True, indent=2) + "\n")
        subprocess.run(["git", "-C", str(repo), "add", MODULE_PATH, REGISTRY_PATH], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "previous"], check=True)
    else:
        subprocess.run(["git", "-C", str(repo), "add", MODULE_PATH], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "module baseline"], check=True)

    (repo / REGISTRY_PATH).write_text(json.dumps(current, sort_keys=True, indent=2) + "\n")
    subprocess.run(["git", "-C", str(repo), "add", REGISTRY_PATH], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "current"], check=True)
    return repo


def test_current_facts_bind_committed_source_and_first_parent(tmp_path: Path) -> None:
    repo = _init_fixture_repo(tmp_path, _registry(_row()))
    facts = pnc.current_registration_facts(repo_root=repo)
    assert len(facts) == 1
    receipt = pnc.material_source_receipt(repo_root=repo)
    assert receipt.material_sources_match_commit is True
    assert facts[0]["material_source_digest"] == receipt.material_source_digest


def test_current_facts_enforce_previous_transition(tmp_path: Path) -> None:
    previous = _registry(_row(generation=3, state="revoked"))
    current = _registry(_row(generation=3, state="registered"))
    repo = _init_fixture_repo(tmp_path, current, previous)
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="GENERATION_REUSE"):
        pnc.current_registration_facts(repo_root=repo)


def test_uncommitted_material_source_refuses(tmp_path: Path) -> None:
    repo = _init_fixture_repo(tmp_path, _registry(_row()))
    config = repo / REGISTRY_PATH
    config.write_text(config.read_text() + "\n")
    with pytest.raises(pnc.ProviderNativeCapabilityError, match="MATERIAL_SOURCE_UNGROUNDED"):
        pnc.current_registration_facts(repo_root=repo)


def test_current_facts_refuse_registry_aba_restore_before_material_proof(
    tmp_path: Path,
    monkeypatch,
) -> None:
    committed = _registry(_row(generation=1))
    repo = _init_fixture_repo(tmp_path, committed)
    path = repo / REGISTRY_PATH
    committed_text = path.read_text()
    transient = _registry(_row(generation=999))
    path.write_text(json.dumps(transient, sort_keys=True, indent=2) + "\n")

    original_read_bytes = Path.read_bytes
    target = path.resolve()
    restored = False

    def aba_read_bytes(self: Path) -> bytes:
        nonlocal restored
        data = original_read_bytes(self)
        if not restored and self.resolve() == target:
            restored = True
            path.write_text(committed_text)
        return data

    monkeypatch.setattr(Path, "read_bytes", aba_read_bytes)

    with pytest.raises(pnc.ProviderNativeCapabilityError, match="MATERIAL_SOURCE_UNGROUNDED"):
        pnc.current_registration_facts(repo_root=repo)

    assert restored is True
    assert json.loads(path.read_text()) == committed
    assert _git(repo, "status", "--porcelain") == ""


def test_v1_provider_capacity_material_source_is_byte_exact() -> None:
    assert hashlib.sha256((ROOT / "engine/provider_capacity.py").read_bytes()).hexdigest() == V1_ENGINE_SHA256
    assert hashlib.sha256((ROOT / "scripts/build_provider_capacity.py").read_bytes()).hexdigest() == V1_CLI_SHA256


def test_cli_has_no_identity_generation_or_state_override() -> None:
    script = ROOT / "scripts/build_provider_native_capability_registration.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--capacity-capability-id",
            CAPABILITY_ID,
            "--capability-generation",
            "99",
            "--registration-state",
            "revoked",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "unrecognized arguments" in proc.stderr


def test_cli_emits_current_checked_in_facts_only() -> None:
    script = ROOT / "scripts/build_provider_native_capability_registration.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert isinstance(payload, list)
    assert payload == list(pnc.current_registration_facts(repo_root=ROOT))
    assert all(set(item) == {
        "schema",
        "capacity_capability_id",
        "capability_generation",
        "provider",
        "billing_mode",
        "credential_kind",
        "execution_surface",
        "registration_state",
        "material_source_digest",
        "registration_receipt_digest",
    } for item in payload)
