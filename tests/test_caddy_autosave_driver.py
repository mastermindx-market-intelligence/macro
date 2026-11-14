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


@pytest.fixture
def www_recovery(driver, tmp_path, monkeypatch):
    from copy import deepcopy
    from types import SimpleNamespace

    from macro_caddy_overlay import plan_www_automatic_tls
    from macro_caddy_publication import publish

    www = "www.mastermind-x.com"
    source_before = {"apps": {
        "http": {"servers": {"https": {"listen": [":443"], "routes": [{"match": [{"host": [www]}]}]}}},
        "tls": {"automation": {"policies": [
            {"subjects": ["before.example", www, "after.example"], "issuers": [{"module": "internal"}]},
            {"subjects": ["public.example"]},
        ]}},
    }}
    source_after = deepcopy(source_before)
    after_policies = source_after["apps"]["tls"]["automation"]["policies"]
    after_policies[0]["subjects"].remove(www)
    after_policies[1]["subjects"].append(www)

    original = deepcopy(source_before)
    policies = original["apps"]["tls"]["automation"]["policies"]
    policies[0]["subjects"].insert(1, "active-only.example")
    policies[1]["subjects"].append("active-public.example")
    original["logging"] = {"logs": {"café": {"level": "INFO"}}}
    postimage = plan_www_automatic_tls(source_before, source_after, original)
    world = SimpleNamespace(active=deepcopy(original), autosave=deepcopy(original), installed=b"old",
                            checked_out=b"new", runtime=b"reviewed code", revision="a" * 40,
                            etag='"before"', write_mode="success", writes=[], on_read=lambda: None)

    class API:
        def read(self):
            world.on_read()
            return deepcopy(world.active), world.etag

        def write(self, config, etag):
            assert etag == world.etag
            world.writes.append((deepcopy(config), etag))
            if world.write_mode == "refused":
                return 412
            world.active = world.autosave = deepcopy(config)
            world.etag = '"after"'
            if world.write_mode == "lost":
                raise ConnectionError("lost response")
            return 200

    api = API()
    state = tmp_path / "private"

    def install(before, after):
        assert world.installed == before
        world.installed = after

    forward = publish(state_dir=state, api=api, expected_preimage=original, candidate=postimage,
                      source_before=b"old", source_after=b"new", read_autosave=lambda: world.autosave,
                      install_source=install)
    assert forward["status"] == "published" and world.active == postimage
    world.forward = forward["op_id"]
    world.original, world.postimage, world.state = original, postimage, state
    world.api, world.install = api, install

    def git(*args):
        if "rev-parse" in args:
            return world.revision.encode()
        assert "show" in args
        return b"new" if args[-1].endswith(":app/deploy/Caddyfile") else b"reviewed code"

    monkeypatch.setattr(driver, "STATE", state)
    monkeypatch.setattr(driver, "run", git)
    monkeypatch.setattr(driver, "adapt", {b"old": source_before, b"new": source_after}.__getitem__)
    monkeypatch.setattr(driver, "read_autosave", lambda: deepcopy(world.autosave))
    def read_source(path):
        if path == driver.INSTALLED:
            return world.installed
        if path == driver.APP / "app/deploy/Caddyfile":
            return world.checked_out
        return world.runtime

    monkeypatch.setattr(driver, "read_regular", read_source)
    monkeypatch.setattr(driver, "install_source", install)
    monkeypatch.setattr(driver, "validate", lambda candidate: None)
    world.restore = lambda: driver.restore_committed_www_tls(
        "a" * 40, world.forward, world.installed, world.checked_out, api, deepcopy(world.active),
    )
    return world


def test_www_recovery_restores_actual_forward_preimages_and_closes_new_intent(www_recovery):
    from macro_caddy_publication import journal_status, read_committed_tip

    world = www_recovery
    result = world.restore()
    assert result["status"] == "published" and result["op_id"] != world.forward
    assert world.active == world.autosave == world.original and world.installed == b"old"
    assert world.writes == [(world.postimage, '"before"'), (world.original, '"after"')]
    assert journal_status(world.state)["receipts"] == {world.forward: "committed", result["op_id"]: "committed"}
    inverse = json.loads((world.state / f"intent-{result['op_id']}.json").read_bytes())
    assert inverse["predecessor"] == world.forward
    assert read_committed_tip(world.state, result["op_id"])["source_after"] == b"old"
    with pytest.raises(ValueError, match="committed publication tip"):
        world.restore()
    assert len(world.writes) == 2


@pytest.mark.parametrize("change,message", [
    ("active_order", "active or autosave"),
    ("active_domain", "active or autosave"),
    ("autosave", "active or autosave"),
    ("source", "checkout differs"),
    ("installed", "source differs"),
    ("code", "runtime differs"),
    ("revision", "exact current protected revision"),
    ("journal_inode", "history is unresolved"),
])
def test_www_recovery_refuses_unrelated_drift_before_post(www_recovery, change, message):
    from copy import deepcopy

    world = www_recovery
    if change.startswith("active"):
        world.active = deepcopy(world.active)
        subjects = world.active["apps"]["tls"]["automation"]["policies"][0]["subjects"]
        if change == "active_order":
            subjects.reverse()
        else:
            subjects.append("changed.example")
    elif change == "autosave":
        world.autosave = deepcopy(world.autosave)
        world.autosave["logging"]["logs"]["café"]["level"] = "DEBUG"
    elif change == "source":
        world.checked_out = b"stale source"
    elif change == "installed":
        world.installed = b"stale installed"
    elif change == "code":
        world.runtime = b"stale code"
    elif change == "revision":
        world.revision = "b" * 40
    else:
        intent = world.state / f"intent-{world.forward}.json"
        replacement = intent.with_name("replacement")
        replacement.write_bytes(intent.read_bytes())
        replacement.chmod(0o600)
        replacement.replace(intent)
    with pytest.raises(ValueError, match=message):
        world.restore()
    assert len(world.writes) == 1


@pytest.mark.parametrize("change,message", [
    ("etag", "etag_stale"),
    ("source", "installed_source_preimage_changed"),
    ("checkout", "installed_source_read_failed"),
    ("autosave", "autosave_preimage_mismatch_concurrent"),
    ("journal", "required_committed_tip_recheck_failed"),
])
def test_www_recovery_refuses_concurrent_prewrite_change(www_recovery, change, message):
    world = www_recovery
    reads = 0

    def change_on_recheck():
        nonlocal reads
        reads += 1
        if reads != 2:
            return
        if change == "etag":
            world.etag = '"changed"'
        elif change == "source":
            world.installed = b"concurrent source"
        elif change == "checkout":
            world.checked_out = b"concurrent checkout"
        elif change == "autosave":
            world.autosave = world.original
        else:
            path = world.state / ("intent-" + "f" * 64 + ".json")
            path.write_bytes(b"unverified intent")
            path.chmod(0o600)

    world.on_read = change_on_recheck
    with pytest.raises(RuntimeError, match=message):
        world.restore()
    assert len(world.writes) == 1


@pytest.mark.parametrize("mode,first_error,next_error", [
    ("lost", "write_lost_response", "clean existing publication journal"),
    ("refused", "write_precondition_refused", "committed publication tip"),
])
def test_www_recovery_never_replays_lost_or_refused_write(www_recovery, mode, first_error, next_error):
    from macro_caddy_publication import journal_status

    world = www_recovery
    world.write_mode = mode
    with pytest.raises(RuntimeError, match=first_error):
        world.restore()
    result = journal_status(world.state)
    assert bool(result["pending_op_ids"]) == (mode == "lost")
    assert world.installed == b"new"
    with pytest.raises(ValueError, match=next_error):
        world.restore()
    if mode == "refused":
        world.forward = next(op for op, closure in result["receipts"].items() if closure == "refused_precondition")
        with pytest.raises(ValueError, match="committed publication tip"):
            world.restore()
    assert len(world.writes) == 2
