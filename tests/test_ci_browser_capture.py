from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ci_browser_dependency_capture as CAPTURE


def _context(**extra):
    fields = {"APT_RETRIES": "1", "APT_HTTP_TIMEOUT": "15", "APT_HTTPS_TIMEOUT": "15",
              **{f"CTX_{i}": "0" for i in range(len(CAPTURE.CONTEXT_ENV))}, **extra}
    return "".join(f"{name}='{value}'\n" for name, value in fields.items()).encode()


def test_capture_preserves_numeric_absence_and_observes_safe_ip_queue_modes():
    report = CAPTURE.summarize_context_inputs(_context(APT_FORCE_IPV4="true", APT_FORCE_IPV6="0", APT_QUEUE_MODE="host"))
    assert report["status"] == "observed"
    assert report["credential_context"] == "installer_root_context"
    assert report["ip_and_queue"] == {"APT_FORCE_IPV4": True, "APT_FORCE_IPV6": False, "APT_QUEUE_MODE": "host"}
    assert report["ip_and_queue_absent"] == []
    absent = CAPTURE.summarize_context_inputs(_context())
    assert sorted(absent["ip_and_queue_absent"]) == sorted(CAPTURE.EXTRA_KEYS)
    assert absent["ip_and_queue"] == {}


@pytest.mark.parametrize("extra", [{"APT_FORCE_IPV4": "SENSITIVE"}, {"APT_QUEUE_MODE": "SENSITIVE"}, {"CTX_0": "SENSITIVE"}, {"UNKNOWN": "SENSITIVE"}])
def test_capture_refuses_unknown_or_malformed_fields_without_disclosing_values(extra):
    result = CAPTURE.summarize_context_inputs(_context(**extra))
    assert result["status"] == "unavailable"
    assert "SENSITIVE" not in json.dumps(result)


def test_capture_refuses_missing_root_environment_context_and_duplicate_fields():
    assert CAPTURE.summarize_context_inputs(b"APT_RETRIES='1'\n")["status"] == "unavailable"
    assert CAPTURE.summarize_context_inputs(_context() + b"APT_RETRIES='2'\n")["status"] == "unavailable"
    assert CAPTURE.summarize_context_inputs(b"x" * 8193)["status"] == "unavailable"


def test_capture_propagates_pure_numeric_refusal_instead_of_claiming_observation():
    report = CAPTURE.summarize_context_inputs(_context(APT_RETRIES="SENSITIVE"))
    assert report["status"] == "unavailable"
    assert "SENSITIVE" not in json.dumps(report)


def test_capture_passes_only_observed_root_proxy_presence_to_pure_helper(monkeypatch):
    observed = []
    monkeypatch.setattr(CAPTURE, "summarize_apt_inputs", lambda raw, env: observed.append(dict(env)) or {"available": True})
    result = CAPTURE.summarize_context_inputs(_context(CTX_0="1", CTX_6="1"))
    assert result["status"] == "observed"
    assert observed == [{"HTTP_PROXY": "present", "APT_CONFIG": "present"}]


MIRRORS = b"http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\nhttps://archive.ubuntu.com/ubuntu/\tpriority:2\nhttps://security.ubuntu.com/ubuntu/\tpriority:3\n"


def test_capture_reports_only_approved_mirror_identities_not_selected_endpoint():
    result = CAPTURE.summarize_mirror_list(MIRRORS)
    assert result["status"] == "observed"
    assert [e["identity"] for e in result["entries"]] == ["azure_ubuntu_http", "ubuntu_archive_https", "ubuntu_security_https"]
    assert result["selection"] == "image_mirror_list_only_not_selected_endpoint"


@pytest.mark.parametrize("uri", ["http://user:SECRET@azure.archive.ubuntu.com/ubuntu/", "http://private-SECRET/ubuntu/", "http://azure.archive.ubuntu.com/SECRET/", "http://azure.archive.ubuntu.com/ubuntu/?SECRET", "http://azure.archive.ubuntu.com:8080/ubuntu/"])
def test_capture_mirror_foreign_or_credential_data_never_reaches_output(uri):
    result = CAPTURE.summarize_mirror_list((uri + " priority:1\n").encode())
    assert result["status"] == "unavailable"
    assert "SECRET" not in json.dumps(result)


def test_capture_commands_keep_privileged_body_static_and_python_unprivileged():
    apt, provenance = CAPTURE.capture_commands()
    assert "sudo -n -- sh -c" in apt and "/usr/bin/apt-config shell" in apt
    assert apt.endswith("| python scripts/ci_browser_dependency_capture.py apt")
    assert provenance == "python scripts/ci_browser_dependency_capture.py playwright"
    assert all(key in apt for key in (*CAPTURE.NUMERIC_KEYS.values(), *CAPTURE.EXTRA_KEYS.values()))
    assert "eval " not in apt and " dump" not in apt and " install" not in apt
    assert all("${" + name + "+x}" in apt for name in CAPTURE.CONTEXT_ENV)
    assert all("${" + name + "}" not in apt for name in CAPTURE.CONTEXT_ENV)


def _distribution(tmp_path, monkeypatch):
    package = tmp_path / "playwright"
    (package / "driver/package/lib").mkdir(parents=True)
    origin = package / "__init__.py"
    origin.write_text("# not imported\n")
    info = tmp_path / "playwright-1.64.1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: playwright\nVersion: 1.64.1\n")
    (package / "driver/package/package.json").write_text('{"version":"1.64.1"}')
    (package / "driver/package/lib/coreBundle.js").write_bytes(b"driver source fixture")
    monkeypatch.setattr(CAPTURE.sysconfig, "get_path", lambda name: str(tmp_path))
    monkeypatch.setattr(CAPTURE.importlib.util, "find_spec", lambda name: SimpleNamespace(origin=str(origin)))
    return package


def test_capture_reads_driver_from_actual_dependency_python_without_importing_vendor(tmp_path, monkeypatch):
    _distribution(tmp_path, monkeypatch)
    result = CAPTURE.installed_playwright_inputs()
    serialized = json.dumps(result)
    assert "1.64.1" in serialized
    assert hashlib.sha256(b"driver source fixture").hexdigest() in serialized
    assert result.get("status") != "unavailable"


def test_capture_refuses_shadowed_module_without_reading_another_distribution(tmp_path, monkeypatch):
    _distribution(tmp_path, monkeypatch)
    monkeypatch.setattr(CAPTURE.importlib.util, "find_spec", lambda name: SimpleNamespace(origin="/different/SECRET.py"))
    monkeypatch.setattr(CAPTURE, "_bounded_read", lambda *_a: pytest.fail("unqualified module must not be read"))
    result = CAPTURE.installed_playwright_inputs()
    assert result["status"] == "unavailable" and "SECRET" not in json.dumps(result)


def test_capture_does_not_conflate_distribution_and_driver_versions(tmp_path, monkeypatch):
    package = _distribution(tmp_path, monkeypatch)
    (package / "driver/package/package.json").write_text('{"version":"1.62.0"}')
    result = CAPTURE.installed_playwright_inputs()
    assert result["status"] == "observed"
    assert result["observed_version"] == "1.64.1"
    assert result["driver_version"] == "1.62.0"
    assert result["version_relationship"] == "different"
    assert result["authoritative"] is False


def test_capture_main_uses_only_bounded_stdin_and_mocked_existing_mirror_file(monkeypatch, capsys):
    monkeypatch.setattr(CAPTURE.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(_context())))
    reads = []
    monkeypatch.setattr(CAPTURE, "_bounded_read", lambda path, limit: reads.append((str(path), limit)) or MIRRORS)
    assert CAPTURE.main(["apt"]) == 0
    line = capsys.readouterr().out
    assert line.startswith("CI_BROWSER_DEPENDENCY_INPUTS=")
    assert json.loads(line.split("=", 1)[1])["status"] == "observed"
    assert reads == [("/etc/apt/apt-mirrors.txt", 8192)]


def test_capture_standalone_help_does_not_run_apt_or_inspect_live_inputs():
    script = Path(CAPTURE.__file__)
    result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True, check=True)
    assert "{apt,playwright}" in result.stdout


def test_capture_commands_are_valid_shell_without_executing_queries():
    for command in CAPTURE.capture_commands():
        subprocess.run(["bash", "-n", "-c", command], check=True, capture_output=True)
