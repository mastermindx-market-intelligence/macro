"""No SSH or production effects: a create-only install in a private test namespace."""
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import uuid

import pytest

from scripts import install_options_plan_reference as install


@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / "state"; root.mkdir(mode=0o755)
    destination = root / "options_plan/reference.json"
    monkeypatch.setattr(install, "DESTINATION", destination)
    observed = dict(schema="options_reference_capability_observation/v1", state="response_observed",
        origin="https://api.polygon.io", path="/v3/reference/options/contracts", params=dict(as_of="2026-10-19"),
        capability=dict(http_status=200, verdict="entitled"), contracts=[], payload_sha256="a" * 64,
        completed_at="2026-10-20T08:43:25.307134+00:00")
    raw = json.dumps(observed).encode()
    source = tmp_path / "source.json"; source.write_bytes(raw); source.chmod(0o600)
    request = dict(schema="options.plan_reference_install/v1", operation_id=str(uuid.uuid4()),
        original_root="01a10340-ddc1-7e41-9b42-9c8543c28c3d", assigning_parent="01a16cd9-b929-7bf2-ace4-d331f583643d",
        sha256=sha256(raw).hexdigest(), byte_length=len(raw), original_observation_path="/original/private/retained-reference.json",
        provider_payload_sha256="a" * 64, captured_at=observed["completed_at"], reference_as_of="2026-10-19")
    def invoke(action, request, body=b""):
        return install.endpoint(dict(action=action, request=request, expected_uid=os.geteuid()), io.BytesIO(body))
    return request, raw, source, destination, tmp_path / "operation.json", invoke


def test_preflight_is_read_only_and_arrival_private_exact_no_overwrite(case):
    request, raw, source, destination, receipt, invoke = case
    assert invoke("preflight", request)["status"] == "ready_create_private_leaf"
    assert not destination.parent.exists()
    assert install.deliver(request, source, receipt, invoke)["status"] == "installed"
    assert destination.read_bytes() == raw
    assert destination.stat().st_mode & 0o777 == 0o600
    assert destination.parent.stat().st_mode & 0o777 == 0o700
    assert destination.stat().st_nlink == 1
    assert json.loads(receipt.read_bytes())["status"] == "INSTALLED"
    assert invoke("inspect", request)["status"] == "present_exact"
    with pytest.raises(FileExistsError): install.deliver(request, source, receipt, invoke)
    with pytest.raises(install.InstallRefused, match="target_exists"): invoke("arrive", request, raw)
    assert destination.read_bytes() == raw


def test_unknown_after_transport_is_sticky_across_reentry(case):
    request, raw, source, destination, receipt, invoke = case
    calls = []
    def lose_return(action, request, body=b""):
        calls.append(action)
        result = invoke(action, request, body)
        if action == "arrive": raise TimeoutError("original response lost")
        return result
    with pytest.raises(install.InstallRefused, match="EFFECT_UNKNOWN"):
        install.deliver(request, source, receipt, lose_return)
    assert destination.read_bytes() == raw
    assert json.loads(receipt.read_bytes())["status"] == "EFFECT_UNKNOWN"
    with pytest.raises(FileExistsError): install.deliver(request, source, receipt, lose_return)
    assert calls == ["preflight", "arrive"]
    assert invoke("inspect", request)["status"] == "present_exact"
    assert json.loads(receipt.read_bytes())["status"] == "EFFECT_UNKNOWN"  # read does not self-clear custody


def test_failed_final_receipt_never_downgrades_effect_to_preflight(case, monkeypatch):
    request, raw, source, destination, receipt, invoke = case
    original = install._save_receipt
    def fail_installed(path, record, **kwargs):
        if record["status"] == "INSTALLED": raise OSError("fsync uncertain")
        return original(path, record, **kwargs)
    monkeypatch.setattr(install, "_save_receipt", fail_installed)
    with pytest.raises(install.InstallRefused, match="EFFECT_UNKNOWN"):
        install.deliver(request, source, receipt, invoke)
    assert json.loads(receipt.read_bytes())["status"] == "EFFECT_UNKNOWN"
    assert destination.read_bytes() == raw


@pytest.mark.parametrize("mutation", ["bytes", "owner", "symlink", "mode", "existing"])
def test_bad_source_or_receiver_never_overwrites(case, mutation):
    request, raw, source, destination, receipt, invoke = case
    if mutation == "bytes":
        with pytest.raises(install.InstallRefused): invoke("arrive", request, raw + b"x")
        assert not destination.parent.exists(); return
    if mutation == "owner":
        with pytest.raises(install.InstallRefused):
            install.endpoint(dict(action="arrive", request=request, expected_uid=os.geteuid() + 1), io.BytesIO(raw))
        assert not destination.parent.exists(); return
    if mutation == "symlink":
        target = destination.parent.parent / "other"; target.mkdir(mode=0o700); destination.parent.symlink_to(target)
    elif mutation == "mode": destination.parent.mkdir(mode=0o755)
    else:
        destination.parent.mkdir(mode=0o700); destination.write_bytes(b"owned-other-source")
    with pytest.raises((install.InstallRefused, OSError)):
        invoke("arrive", request, raw)
    if mutation == "existing": assert destination.read_bytes() == b"owned-other-source"


def test_local_existing_receipt_rejects_before_any_transport(case):
    request, raw, source, destination, receipt, invoke = case
    receipt.write_text('{"status":"EFFECT_UNKNOWN"}')
    with pytest.raises(FileExistsError):
        install.deliver(request, source, receipt, lambda *a: pytest.fail("must never repeat transport"))
    assert not destination.parent.exists()


def test_file_entry_pins_own_repo_before_foreign_cwd_and_pythonpath(tmp_path):
    import subprocess
    import sys
    root = Path(install.__file__).resolve().parents[1]
    decoy = tmp_path / "foreign"
    for name in ("scripts", "lib"):
        package = decoy / name
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("raise RuntimeError('foreign package imported')\n")
    cwd = tmp_path / "unrelated"; cwd.mkdir()
    # -S excludes ambient editable installs. The only repo-root admission is
    # this entry file's own strong pin; neither __main__ nor transport executes.
    code = (
        "import json,runpy,sys; "
        "runpy.run_path(sys.argv[1],run_name='entry_pin_probe'); "
        "import scripts,lib; print(json.dumps([scripts.__file__,lib.__file__]))"
    )
    env = dict(os.environ, PYTHONPATH=str(decoy))
    result = subprocess.run([sys.executable, "-S", "-c", code, str(root / "scripts/install_options_plan_reference.py")],
        cwd=cwd, env=env, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [str(root / "scripts/__init__.py"), str(root / "lib/__init__.py")]
