"""Real disposable Git histories for fixed native registration acquisition."""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import tempfile
from unittest import mock

import pytest

from engine import provider_capacity as v1
from engine import provider_native_capability_source as source


def registry(state="registered", generation=1):
    return {"schema": "mastermind.provider_native_capability_registry/v1",
            "owner_program": "shared-ai-provider-control", "capabilities": [{
                "capacity_capability_id": "cap.fixture", "capability_generation": generation,
                "provider": "minimax", "billing_mode": "subscription",
                "credential_kind": "api_key", "execution_surface": "native_cli",
                "registration_state": state}]}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def commit(root):
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--allow-empty", "-qm", "fixture")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        git(root, "init", "-q", "-b", "main")
        actual = Path(__file__).resolve().parent.parent
        for rel in source.MATERIAL_SOURCE_PATHS:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((actual / rel).read_bytes())
        # Disposable history starts before any registration regardless of the
        # current company's registry. Never remove a real domain as test setup.
        (root / source.REGISTRY_PATH).write_text(json.dumps({**registry(), "capabilities": []}))
        commit(root)
        yield root


def write_registry(root, value):
    (root / source.REGISTRY_PATH).write_text(json.dumps(value))


def test_exact_current_predecessor_and_derived_export(repo):
    previous = git(repo, "rev-parse", "HEAD")
    write_registry(repo, registry())
    current = commit(repo)
    result = source._read_source(repo)
    assert (result.repository_commit, result.previous_repository_commit) == (current, previous)
    export, = result.registrations
    assert export["material_source_digest"] == result.material_source_digest
    assert export["capability_generation"] == 1
    unsigned = {k: v for k, v in export.items() if k != "registration_receipt_digest"}
    assert export["registration_receipt_digest"] == hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def test_empty_registry_still_retains_source_binding(repo):
    commit(repo)
    result = source._read_source(repo)
    assert result.registrations == ()
    assert result.repository_commit != result.previous_repository_commit


def test_dirty_material_refused(repo):
    commit(repo)
    (repo / "engine/provider_native_capabilities.py").write_text("changed")
    with pytest.raises(source.NativeSourceError, match="^MATERIAL_SOURCE_UNGROUNDED$"):
        source._read_source(repo)


def test_registry_is_in_v2_identity_while_v1_unchanged(repo):
    commit(repo)
    before = source._read_source(repo).material_source_digest
    v1_before = v1.material_source_receipt(repo).material_source_digest
    write_registry(repo, registry())
    commit(repo)
    assert source._read_source(repo).material_source_digest != before
    assert v1.material_source_receipt(repo).material_source_digest == v1_before


def test_revocation_and_generation_resurrection_use_actual_predecessor(repo):
    write_registry(repo, registry())
    commit(repo)
    write_registry(repo, registry("revoked"))
    commit(repo)
    assert source._read_source(repo).registrations[0]["registration_state"] == "revoked"
    write_registry(repo, registry())
    commit(repo)
    with pytest.raises(source.NativeSourceError, match="^transition_capability_resurrection$"):
        source._read_source(repo)


def test_registered_row_cannot_disappear(repo):
    write_registry(repo, registry())
    commit(repo)
    write_registry(repo, {**registry(), "capabilities": []})
    commit(repo)
    with pytest.raises(source.NativeSourceError, match="^transition_capability_removed$"):
        source._read_source(repo)


def test_missing_previous_registry_never_infers_empty(repo):
    git(repo, "rm", "-q", source.REGISTRY_PATH)
    commit(repo)
    write_registry(repo, registry())
    commit(repo)
    with pytest.raises(source.NativeSourceError, match="^REGISTRY_SOURCE_UNAVAILABLE$"):
        source._read_source(repo)


def test_parent_symlink_refused(repo):
    path = repo / source.REGISTRY_PATH
    path.unlink()
    path.symlink_to("elsewhere.json")
    commit(repo)
    path.unlink()
    write_registry(repo, registry())
    commit(repo)
    with pytest.raises(source.NativeSourceError, match="^REGISTRY_SOURCE_UNAVAILABLE$"):
        source._read_source(repo)


def test_root_history_refused(repo):
    with pytest.raises(source.NativeSourceError, match="^SINGLE_PARENT_SOURCE_REQUIRED$"):
        source._read_source(repo)


def test_ambiguous_merge_predecessor_refused(repo):
    git(repo, "checkout", "-qb", "other")
    (repo / "other.txt").write_text("other")
    commit(repo)
    git(repo, "checkout", "-q", "main")
    (repo / "main.txt").write_text("main")
    commit(repo)
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "merge", "-q", "--no-ff", "-m", "fixture", "other")
    with pytest.raises(source.NativeSourceError, match="^SINGLE_PARENT_SOURCE_REQUIRED$"):
        source._read_source(repo)


def test_duplicate_json_keys_refused(repo):
    (repo / source.REGISTRY_PATH).write_text('{"schema":"bad","schema":"bad"}')
    commit(repo)
    with pytest.raises(source.NativeSourceError, match="^REGISTRY_SOURCE_INVALID$"):
        source._read_source(repo)


def test_oversized_registry_refused(repo):
    (repo / source.REGISTRY_PATH).write_bytes(b" " * (source.MAX_REGISTRY_BYTES + 1))
    commit(repo)
    with pytest.raises(source.NativeSourceError, match="^REGISTRY_SOURCE_INVALID$"):
        source._read_source(repo)


def test_source_ref_change_during_acquisition_refused(repo):
    commit(repo)
    real = source._commits
    first = real(repo)
    with mock.patch.object(source, "_commits", side_effect=[first, (first[1], first[0])]):
        with pytest.raises(source.NativeSourceError, match="^SOURCE_CHANGED_DURING_ACQUISITION$"):
            source._read_source(repo)


def test_public_entry_has_no_override_parameters():
    assert not inspect.signature(source.current_registration_source).parameters
    assert set(v1.MATERIAL_SOURCE_PATHS).issubset(source.MATERIAL_SOURCE_PATHS)
    assert len(source.MATERIAL_SOURCE_PATHS) == len(v1.MATERIAL_SOURCE_PATHS) + 4


def test_cli_refuses_digest_predecessor_or_identity_arguments():
    from scripts.build_provider_native_capability_registration import main
    for option in ("--material-source-digest", "--previous-registry", "--repo-root", "--generation"):
        with pytest.raises(SystemExit) as exc:
            main([option, "untrusted"])
        assert exc.value.code == 2
