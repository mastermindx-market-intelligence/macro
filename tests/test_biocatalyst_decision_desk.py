"""Expose the actual JavaScript consumer checks to the repository pytest lane."""
from pathlib import Path
import runpy
import shutil
import subprocess

import pytest


def test_decision_desk_contract_and_response_lifecycle():
    node = shutil.which("node")
    assert node, "Decision Desk verification requires the repository's Node runtime"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, str(root / "tests/test_biocatalyst_decision_desk.cjs")],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # Invoke directly: some Node environments summarize --test as one file.
    # Prove the discriminating cases actually ran, rather than just importing.
    assert "late old list response cannot resurrect" in result.stdout
    assert "context change immediately clears" in result.stdout
    assert "fixtures retain exact API response bytes" in result.stdout


def test_decision_desk_host_account_route_and_request_lifecycle():
    node = shutil.which("node")
    assert node, "Decision Desk host verification requires Node"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, str(root / "tests/test_biocatalyst_decision_desk_host.cjs")],
        cwd=root, text=True, capture_output=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "idle logout clears rendered owner data synchronously" in result.stdout
    assert "a direct case URL restores only a row admitted" in result.stdout
    assert "initial anonymous context stays access-required" in result.stdout


# Exact current-owner capture is a test-only source compatibility check. These
# use a real tiny Git fixture; no Company/DataOS publication or admission is made.


def _capture_helpers():
    root = Path(__file__).resolve().parents[1]
    return runpy.run_path(str(root / "research/catalyst_intelligence/decision_desk_r1/generate_company_evidence_fixtures.py"))


@pytest.fixture
def capture_owner(tmp_path):
    owner = tmp_path / "synthetic-owner"
    owner.mkdir()
    subprocess.run(["git", "init", "-q", str(owner)], check=True, capture_output=True)
    (owner / "tracked.txt").write_text("original test-only source\n")
    subprocess.run(["git", "-C", str(owner), "add", "tracked.txt"], check=True)
    subprocess.run([
        "git", "-C", str(owner), "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
        "commit", "-qm", "test-only source",
    ], check=True, capture_output=True)
    head = subprocess.check_output(["git", "-C", str(owner), "rev-parse", "HEAD"], text=True).strip()
    return owner, head


def test_current_owner_capture_accepts_exact_clean_pin_without_writing(capture_owner, tmp_path):
    owner, head = capture_owner
    helper = _capture_helpers().get("validate_capture_request")
    assert callable(helper), "current-owner capture needs an exact-source preflight"
    output = tmp_path / "fresh-consumer-proof"
    assert helper(owner, head, output) == (owner.resolve(), output.resolve())
    assert not output.exists()
    assert subprocess.check_output(["git", "-C", str(owner), "status", "--porcelain"], text=True) == ""


@pytest.mark.parametrize("mutation, message", [
    ("moving_ref", "40-character"),
    ("wrong_head", "pinned"),
    ("tracked_change", "clean"),
    ("untracked_source", "clean"),
    ("output_in_owner", "owner"),
    ("output_symlink_to_owner", "owner"),
    ("existing_output", "already exists"),
    ("historical_fixture_target", "historical"),
])
def test_current_owner_capture_refuses_unsafe_or_ambiguous_source(capture_owner, tmp_path, mutation, message):
    owner, head = capture_owner
    output = tmp_path / "new-proof"
    module = _capture_helpers()
    helper = module.get("validate_capture_request")
    assert callable(helper), "current-owner capture needs an exact-source preflight"
    if mutation == "moving_ref":
        head = "main"
    elif mutation == "wrong_head":
        head = "f" * 40
    elif mutation == "tracked_change":
        (owner / "tracked.txt").write_text("changed by another writer\n")
    elif mutation == "untracked_source":
        (owner / "uncommitted_source.py").write_text("uncommitted = True\n")
    elif mutation == "output_in_owner":
        output = owner / "do-not-create"
    elif mutation == "output_symlink_to_owner":
        alias = tmp_path / "owner-alias"
        alias.symlink_to(owner, target_is_directory=True)
        output = alias / "do-not-create"
    elif mutation == "existing_output":
        output.mkdir()
        (output / "retained.json").write_text('{"preserve": true}\n')
    elif mutation == "historical_fixture_target":
        output = Path(__file__).resolve().parents[1] / "research/catalyst_intelligence/decision_desk_r1/fixtures/company_evidence_r2"
    before = (owner / "tracked.txt").read_bytes()
    with pytest.raises(ValueError, match=message):
        helper(owner, head, output)
    assert (owner / "tracked.txt").read_bytes() == before
    assert not (owner / "do-not-create").exists()
    if mutation == "existing_output":
        assert (output / "retained.json").read_text() == '{"preserve": true}\n'


def test_legacy_default_capture_also_refuses_owner_output_before_import(capture_owner, monkeypatch):
    owner, head = capture_owner
    capture = _capture_helpers()["capture"]
    # Use the real capture entrypoint with a harmless temporary source pin and
    # default destination. A legacy default must not bypass the owner boundary.
    monkeypatch.setitem(capture.__globals__, "PIN", head)
    monkeypatch.setitem(capture.__globals__, "HISTORICAL_OUTPUT", owner / "historical-proof")
    with pytest.raises(ValueError, match="owner"):
        capture(owner, expected_head=head)
    assert not (owner / "historical-proof").exists()
    assert subprocess.check_output(["git", "-C", str(owner), "status", "--porcelain"], text=True) == ""


def test_failed_owner_fixture_import_restores_python_context_without_output(capture_owner, tmp_path):
    import sys

    owner, head = capture_owner
    output = tmp_path / "no-partial-proof"
    before_path, before_bytecode = sys.path[:], sys.dont_write_bytecode
    # The exact clean test repository intentionally lacks the fixture module.
    # Exercise the real failure path, not a mocked successful native capture.
    with pytest.raises(FileNotFoundError):
        _capture_helpers()["capture"](owner, expected_head=head, output_dir=output)
    assert sys.path == before_path
    assert sys.dont_write_bytecode is before_bytecode
    assert not output.exists()
    assert subprocess.check_output(["git", "-C", str(owner), "status", "--porcelain"], text=True) == ""
