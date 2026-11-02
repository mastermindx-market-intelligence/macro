"""Host-driver refusals use local fixtures; no service/API/host mutations."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def driver(monkeypatch):
    deploy = Path(__file__).resolve().parents[1] / "app/deploy"
    monkeypatch.syspath_prepend(str(deploy))
    spec = importlib.util.spec_from_file_location("caddy_autosave_driver", deploy / "reconcile-caddy-autosave.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_regular_input_refuses_symlink_alias_and_writable_file(driver, tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"source")
    source.chmod(0o600)
    assert driver.read_regular(source, root_owned=False) == b"source"
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(OSError):
        driver.read_regular(link, root_owned=False)
    alias = tmp_path / "alias"
    os.link(source, alias)
    with pytest.raises(ValueError, match="unsafe"):
        driver.read_regular(source, root_owned=False)
    alias.unlink()
    source.chmod(0o666)
    with pytest.raises(ValueError, match="unsafe"):
        driver.read_regular(source, root_owned=False)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'[]'])
def test_native_json_is_unambiguous(driver, raw):
    with pytest.raises(ValueError):
        driver.decode(raw)


def test_conditional_native_request_uses_full_candidate_once(driver, monkeypatch):
    calls = []
    api = driver.NativeAPI()
    monkeypatch.setattr(api, "_request", lambda *args: calls.append(args) or (200, {}, b""))
    candidate = {"apps": {"http": {"servers": {"preserve": {}}}}}
    assert api.write(candidate, '"v1"') == 200
    assert calls == [("POST", driver.canonical(candidate), {
        "Content-Type": "application/json", "If-Match": '"v1"'})]


@pytest.mark.parametrize("status,headers", [(500, {}), (200, {}), (200, {"ETag": "unsafe\r\nvalue"})])
def test_api_missing_or_unsafe_version_refuses(driver, monkeypatch, status, headers):
    api = driver.NativeAPI()
    monkeypatch.setattr(api, "_request", lambda *args: (status, headers, b"{}"))
    with pytest.raises(ValueError):
        api.read()


def test_explicit_prior_source_requires_exact_protected_ancestor(driver, monkeypatch):
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(args)
        return b"prior-source" if "show" in args else b""
    monkeypatch.setattr(driver, "run", fake_run)
    revision = "a" * 40
    assert driver.previous_source(revision, b"installed") == b"prior-source"
    assert calls[0][-4:] == ("merge-base", "--is-ancestor", revision, "origin/main")
    assert calls[1][-1] == revision + ":app/deploy/Caddyfile"
    calls.clear()
    with pytest.raises(ValueError):
        driver.previous_source("main", b"installed")
    assert calls == []
    assert driver.previous_source(None, b"installed") == b"installed"


@pytest.mark.parametrize("changed", ["ExecStart", "ExecReload"])
def test_unknown_service_mode_never_falls_back_to_reload(driver, monkeypatch, changed):
    def fake_run(*args, **kwargs):
        prop = args[-1]
        if prop == changed:
            return b"/usr/bin/caddy reload --config /etc/caddy/Caddyfile.combined"
        verb = "run" if prop == "ExecStart" else "reload"
        return f"/usr/bin/caddy {verb} --config {driver.AUTOSAVE}".encode()
    monkeypatch.setattr(driver, "run", fake_run)
    with pytest.raises(ValueError, match="qualified autosave"):
        driver.require_autosave_mode()


def test_imported_source_requires_separate_qualification(driver, monkeypatch):
    calls = []
    monkeypatch.setattr(driver, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="imports"):
        driver.adapt(b"example.com {\n import relative.snippet\n}\n")
    assert calls == []


def test_adapter_generated_filename_is_only_logical_source_translation(driver, monkeypatch):
    value = {"handler": "file_server", "hide": ["/dev/stdin", "private.txt"]}
    monkeypatch.setattr(driver, "run", lambda *args, **kwargs: json.dumps(value).encode())
    assert driver.adapt(b"public source") == {
        "handler": "file_server", "hide": [str(driver.INSTALLED), "private.txt"]}
    value["hide"][0] = "unexpected"
    with pytest.raises(ValueError, match="hide topology"):
        driver.adapt(b"public source")
