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


def test_www_tls_source_binds_complete_active_and_current_protected_bytes(driver, monkeypatch):
    import hashlib

    active = {"apps": {"tls": {"automation": {"policies": []}}}, "admin": {"listen": "localhost:2019"}}
    digest = hashlib.sha256(driver.canonical(active)).hexdigest()
    revision = "a" * 40
    source = b"exact current Caddyfile"
    calls = []
    refs = {"HEAD": revision, "origin/main": revision}

    def fake_run(*args):
        calls.append(args)
        if "rev-parse" in args:
            return refs[args[-1]].encode()
        assert args[-1] == f"{revision}:app/deploy/Caddyfile"
        return source

    monkeypatch.setattr(driver, "run", fake_run)
    driver.qualified_www_tls_source(revision, digest, source, active)
    assert [args[-1] for args in calls] == ["HEAD", "origin/main", f"{revision}:app/deploy/Caddyfile"]

    calls.clear()
    active["admin"]["listen"] = "localhost:2020"
    with pytest.raises(ValueError, match="active preimage digest changed"):
        driver.qualified_www_tls_source(revision, digest, source, active)
    assert calls == []

    digest = hashlib.sha256(driver.canonical(active)).hexdigest()
    with pytest.raises(ValueError, match="checkout differs"):
        driver.qualified_www_tls_source(revision, digest, b"different source", active)
    refs["origin/main"] = "b" * 40
    with pytest.raises(ValueError, match="exact current protected revision"):
        driver.qualified_www_tls_source(revision, digest, source, active)


@pytest.mark.parametrize("case", ["qualified", "pending", "stale"])
def test_www_tls_driver_keeps_existing_native_transaction_boundary(driver, monkeypatch, case):
    import hashlib
    import stat
    import sys
    from types import SimpleNamespace

    import macro_caddy_overlay as overlay
    import macro_caddy_publication as publication

    events = []
    revision = "a" * 40
    active = {"native": "reviewed"}
    candidate = {"native": "qualified www"}
    old, source = b"installed source", b"protected source"
    installed = [old]
    digest = hashlib.sha256(driver.canonical(active)).hexdigest()
    if case == "stale":
        digest = "0" * 64
    monkeypatch.setattr(sys, "argv", ["driver", "--www-automatic-tls", revision, digest])
    lock = SimpleNamespace(st_dev=1, st_ino=2)
    monkeypatch.setattr(driver, "os", SimpleNamespace(geteuid=lambda: 0, fstat=lambda fd: lock, stat=lambda *a, **kw: lock))
    monkeypatch.setattr(driver, "Path", lambda p: SimpleNamespace(read_text=lambda: "FLOCK  ADVISORY  WRITE"))
    state = SimpleNamespace(lstat=lambda: SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o700))
    monkeypatch.setattr(driver, "STATE", state)
    monkeypatch.setattr(driver, "require_autosave_mode", lambda: events.append("autosave"))
    monkeypatch.setattr(publication, "journal_status",
                        lambda directory: {"ok": directory is state, "pending_op_ids": ["held"] if case == "pending" else []})
    monkeypatch.setattr(driver, "read_regular", lambda path: installed[0] if path == driver.INSTALLED else source)
    monkeypatch.setattr(driver, "NativeAPI",
                        lambda: SimpleNamespace(read=lambda: (events.append("active") or active, '"etag"')))
    monkeypatch.setattr(driver, "run", lambda *a: revision.encode() if "rev-parse" in a else source)
    monkeypatch.setattr(driver, "adapt", lambda raw: {"source": raw})

    def plan(previous, protected, actual):
        events.append("www-only plan")
        assert (previous, protected, actual) == ({"source": old}, {"source": source}, active)
        return candidate

    def publish(**kwargs):
        events.append("existing publish")
        assert kwargs["expected_preimage"] == active and kwargs["candidate"] == candidate
        assert kwargs["source_before"] == old and kwargs["source_after"] == source
        assert kwargs["state_dir"] is state and kwargs["install_source"] is driver.install_source
        installed[0] = source
        return {"status": "published", "op_id": "receipt", "published": True,
                "installed_source": True, "receipt_written": True}

    monkeypatch.setattr(overlay, "plan_www_automatic_tls", plan)
    monkeypatch.setattr(driver, "validate", lambda cfg: events.append("validate"))
    monkeypatch.setattr(publication, "publish", publish)
    if case == "pending":
        with pytest.raises(ValueError, match="clean existing publication journal"):
            driver.main()
        assert events == ["autosave"]
    elif case == "stale":
        with pytest.raises(ValueError, match="active preimage digest changed"):
            driver.main()
        assert events == ["autosave", "active"]
    else:
        assert driver.main()["status"] == "published"
        assert events == ["autosave", "active", "www-only plan", "validate", "existing publish"]
