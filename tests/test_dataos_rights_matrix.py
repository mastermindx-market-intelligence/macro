"""K01 rights/leakage matrix discriminators for the Data OS read surfaces.

Lane O2-K01 (programme DATA-OS-COMPLETION, base 0939fbfc9e). Every negative
test drives a real surface end to end and asserts the ABSENCE of the synthetic
sentinels, of absolute host paths and of URLs in the FULL serialized response;
the positive controls in the same file prove the sentinels DO reach a granted
read, so an always-refusing surface cannot pass. All fixtures are synthetic
and live under pytest ``tmp_path``; no ``data/`` directory, network or real
credential is touched. Principal identity is deliberately absent from every
request: the only in-repo authority boundary is the host-owned binding
configuration and the root alias allowlist it defines.

The new file is not yet wired into any CI job (the seat wires it).
"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from lib.dataos import web_api
from lib.dataos.web_workspace import WorkspaceError, load_workspace_config

SENTINEL_VALUE = "SENTINEL_PRIVATE_VALUE_9f3"        # stored inside the bound root
SENTINEL_OUTSIDE = "SENTINEL_OUTSIDE_ROOT_2c8"       # stored outside every bound root
SENTINEL_REBOUND = "SENTINEL_REBOUND_SOURCE_7d1"     # stored content after re-source
SENTINEL_REQUEST = "SENTINEL_ENTITLEMENT_4b7"        # injected as a request value

REPO_ROOT = Path(__file__).resolve().parents[1]

_SPEC = importlib.util.spec_from_file_location(
    "data_workspace_cli", REPO_ROOT / "scripts" / "data_workspace.py")
CLI = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(CLI)


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "bound-root"
    root.mkdir()
    outside = tmp_path / "outside-root"
    outside.mkdir()
    (outside / "escaped.csv").write_text(
        "Session,ClosePx\n2026-10-05," + SENTINEL_OUTSIDE + "\n", encoding="utf-8")
    prices = root / "prices.csv"
    prices.write_text(
        "Session,ClosePx\n2026-10-05," + SENTINEL_VALUE + "\n2026-10-06,101\n",
        encoding="utf-8")
    registry = tmp_path / "registry.yml"
    registry.write_text("schema: dataset_registry.v1\ndatasets: []\n", encoding="utf-8")
    config = tmp_path / "host.json"
    payload = {
        "schema_version": "mastermind.data_workspace_bindings/v1",
        "registry_path": str(registry),
        "roots": [{"alias": "open", "path": str(root),
                   "evidence_kind": "research_capture"}],
    }
    config.write_text(json.dumps(payload), encoding="utf-8")
    return SimpleNamespace(config=config, root=root, tmp=tmp_path, prices=prices,
                           outside=outside)


def _run_cli(config_path, request, monkeypatch):
    """Drive the real CLI entry point with a synthetic stdin request."""
    monkeypatch.setattr(sys, "argv", ["data_workspace.py", "--config", str(config_path)])
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(request).encode())))
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    code = CLI.main()
    return code, out.getvalue()


def _assert_closed(response_text, env, *extra_secrets):
    """The full serialized response carries no sentinel, host path or URL."""
    for secret in (*extra_secrets, SENTINEL_VALUE, SENTINEL_OUTSIDE,
                   SENTINEL_REBOUND, SENTINEL_REQUEST):
        assert secret not in response_text
    assert str(env.tmp) not in response_text
    assert "://" not in response_text
    parsed = json.loads(response_text)
    assert set(parsed) == {"schema_version", "error", "error_type"}
    return parsed


def test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative(env, monkeypatch):
    """K01.01 positive control: the granted read serves the permitted class."""
    code, out = _run_cli(env.config, {"action": "read", "ref": "open:prices.csv",
                                      "limit": 10}, monkeypatch)
    assert code == 0
    result = json.loads(out)
    assert SENTINEL_VALUE in out
    assert result["source"]["relative_path"] == "prices.csv"
    assert result["source"]["root_alias"] == "open"
    assert str(env.root) not in out
    assert "://" not in out


@pytest.mark.parametrize("ref", [
    "open:../outside/escaped.csv",
    "open:prices.csv/../../outside/escaped.csv",
    "open:credential_store/prices.csv",
])
def test_path_escape_refusal_returns_closed_response(env, monkeypatch, ref):
    code, out = _run_cli(env.config, {"action": "read", "ref": ref}, monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env, SENTINEL_OUTSIDE)
    assert parsed["error"] == "PATH_REFUSED"


@pytest.mark.parametrize("key", [
    "config", "config_path", "credential", "token", "grant",
    "entitlement", "root_path", "source_url",
])
def test_credential_shaped_request_keys_are_refused_not_ignored(env, monkeypatch, key):
    request = {"action": "read", "ref": "open:prices.csv", key: SENTINEL_REQUEST}
    code, out = _run_cli(env.config, request, monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "INVALID_REQUEST_FIELDS"
    assert SENTINEL_VALUE not in out  # refusal happens before any source read


def test_lab_run_rejects_credential_shaped_outer_key_before_artifacts(env, monkeypatch):
    execution = {
        "action": "lab_run",
        "request": {"signal_id": "any", "refs": ["open:prices.csv"],
                    "n_configs_searched": 1},
        "time_column": "Session",
        "column_map": {"close": "ClosePx"},
        "bar_frequency": "daily",
        "credential": SENTINEL_REQUEST,
    }
    code, out = _run_cli(env.config, execution, monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "INVALID_REQUEST_FIELDS"
    assert not (env.tmp / "artifacts").exists()


@pytest.mark.parametrize("selector,probe", [
    ({"action": "browse", "root": "/etc"}, "/etc"),
    ({"action": "browse", "root": "../data"}, "../data"),
    ({"action": "read", "ref": "../etc/passwd:shadow"}, "../etc/passwd"),
])
def test_request_cannot_select_a_root_by_path(env, monkeypatch, selector, probe):
    """Root selection is alias-only; a path-shaped alias is just an alias miss."""
    code, out = _run_cli(env.config, selector, monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "ROOT_NOT_BOUND"
    assert probe not in out


def test_rebound_source_refuses_pinned_old_version_without_stale_value(env, monkeypatch):
    """K01.04: after the source is replaced, the pinned old binding serves no value."""
    code, out = _run_cli(env.config, {"action": "read", "ref": "open:prices.csv",
                                      "limit": 10}, monkeypatch)
    version = json.loads(out)["source"]["file_version"]
    assert SENTINEL_VALUE in out  # positive control on the original binding
    env.prices.write_text(
        "Session,ClosePx\n2026-10-05," + SENTINEL_REBOUND + "\n2026-10-07,202\n",
        encoding="utf-8")
    code, out = _run_cli(env.config, {"action": "read", "ref": "open:prices.csv",
                                      "limit": 10, "expected_version": version},
                         monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "SOURCE_VERSION_MISMATCH"
    code, out = _run_cli(env.config, {"action": "read", "ref": "open:prices.csv",
                                      "limit": 10}, monkeypatch)
    assert code == 0
    fresh = json.loads(out)
    assert SENTINEL_REBOUND in out and SENTINEL_VALUE not in out
    assert fresh["source"]["file_version"] != version


def test_unmounted_required_volume_refuses_before_any_read(env, monkeypatch):
    payload = json.loads(env.config.read_text(encoding="utf-8"))
    payload["roots"][0]["required_mount"] = str(env.tmp / "revoked-volume")
    env.config.write_text(json.dumps(payload), encoding="utf-8")
    code, out = _run_cli(env.config, {"action": "read", "ref": "open:prices.csv"},
                         monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "REQUIRED_VOLUME_NOT_MOUNTED"


def test_cli_error_response_never_carries_exception_detail_or_config_path(env, monkeypatch):
    env.config.write_text("{not json at all", encoding="utf-8")
    code, out = _run_cli(env.config, {"action": "read", "ref": "open:prices.csv"},
                         monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "INVALID_ARGUMENT_OR_HOST_CONFIGURATION"
    assert "not json" not in out


def test_web_lab_error_message_text_does_not_cross_the_cli_boundary(env, monkeypatch):
    code, out = _run_cli(env.config, {"action": "lab_plan",
                                      "signal_id": "definitely_not_a_signal_9f3",
                                      "refs": ["open:prices.csv"]}, monkeypatch)
    assert code == 2
    parsed = _assert_closed(out, env)
    assert parsed["error"] == "UNKNOWN_SIGNAL"
    assert "definitely_not_a_signal_9f3" not in out
    assert "Unknown catalog signal" not in out


def test_discovery_surfaces_return_names_and_codes_never_values_or_paths(env):
    workspace = load_workspace_config(env.config)
    searched = json.dumps(web_api.dispatch(
        workspace, {"action": "search", "query": "prices"}, config_path=env.config))
    browsed = json.dumps(web_api.dispatch(
        workspace, {"action": "browse", "root": "open"}, config_path=env.config))
    for text in (searched, browsed):
        assert SENTINEL_VALUE not in text
        assert str(env.root) not in text
        assert "://" not in text
    assert browsed and "open:prices.csv" in browsed  # names are the permitted class


def test_test_workspace_symlink_component_is_refused(tmp_path):
    target = tmp_path / "artifact-target"
    target.mkdir()
    runs = tmp_path / "runs"
    runs.symlink_to(target, target_is_directory=True)
    config = tmp_path / "host.json"
    config.write_text(json.dumps({
        "schema_version": "mastermind.data_workspace_bindings/v1",
        "registry_path": str(tmp_path / "registry.yml"),
        "roots": [],
        "test_workspace": {"path": str(runs), "required_mount": "/"},
    }), encoding="utf-8")
    with pytest.raises(WorkspaceError) as error:
        web_api._host_test_root(config)
    assert error.value.code == "TEST_WORKSPACE_SYMLINK_REFUSED"
    assert not target.exists() or list(target.iterdir()) == []
