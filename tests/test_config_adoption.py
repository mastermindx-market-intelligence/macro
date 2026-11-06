"""Read-only configuration-source adoption; no providers or credentials."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lib import config


@pytest.fixture
def source(monkeypatch, tmp_path):
    config.load.cache_clear()
    monkeypatch.setattr(config, "ROOT", tmp_path)
    path = tmp_path / "config.yml"
    path.write_text("master_brain:\n  llm_model: model-a\n")
    yield path
    config.load.cache_clear()


def observe():
    observer = getattr(config, "configuration_adoption", None)
    assert callable(observer), "the existing loader must expose its source snapshot"
    return observer()


def test_observation_does_not_initialize_the_loader(source):
    before = config.load.cache_info()
    result = observe()
    assert result["state"] == "NOT_LOADED"
    assert result["loaded_sha256"] is None
    assert result["installed_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert config.load.cache_info() == before


def test_observation_detects_changed_source_without_reloading(source):
    original = config.load()
    loaded_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    result = observe()
    assert result["state"] == "SOURCE_CHANGED"
    assert result["loaded_sha256"] == loaded_hash
    assert result["installed_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result["source_bytes_match"] is False
    assert config.load() is original
    assert config.load()["master_brain"]["llm_model"] == "model-a"
    assert config.load.cache_info().misses == 1


def test_explicit_existing_cache_clear_then_load_adopts_new_source(source):
    config.load()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    config.load.cache_clear()
    assert observe()["state"] == "NOT_LOADED"
    assert config.load()["master_brain"]["llm_model"] == "model-b"
    result = observe()
    assert result["state"] == "MATCHING_SOURCE"
    assert result["source_bytes_match"] is True
    assert result["loaded_sha256"] == result["installed_sha256"]


def test_missing_source_is_not_a_matching_loaded_snapshot(source):
    original = config.load()
    source.unlink()
    result = observe()
    assert result["state"] == "SOURCE_UNAVAILABLE"
    assert result["installed_sha256"] is None
    assert result["loaded_sha256"] is not None
    assert result["source_bytes_match"] is None
    assert config.load() is original


def test_observation_is_closed_and_never_reads_credentials(source, monkeypatch):
    source.write_text("private_setting: synthetic-sensitive-value\n")
    config.load()
    def forbidden(*args, **kwargs):
        raise AssertionError("credential access is not diagnostic work")
    monkeypatch.setattr(config, "secret", forbidden)
    monkeypatch.setattr(config, "_load_dotenv", forbidden)
    result = observe()
    assert set(result) == {"schema", "state", "scope", "source", "observed_at",
                           "loaded_sha256", "installed_sha256", "source_bytes_match",
                           "not_covered"}
    assert result["scope"] == "current_process_source_snapshot"
    assert "remote_processes" in result["not_covered"]
    assert "credentials" in result["not_covered"]
    assert "runtime_overrides" in result["not_covered"]
    encoded = json.dumps(result)
    for value in ["synthetic-sensitive-value", "private_setting", str(source.parent)]:
        assert value not in encoded


def test_loader_retains_the_existing_cache_contract(source):
    value = config.load()
    assert config.load() is value
    assert config.load.cache_parameters() == {"maxsize": 1, "typed": False}
    assert config.load.cache_info().currsize == 1


def test_existing_ai_admin_response_carries_actual_adoption(source, monkeypatch):
    from admin import ai_cost
    config.load()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    monkeypatch.setattr(ai_cost, "ROOT", source.parent)
    monkeypatch.setattr(ai_cost, "SITE", source.parent / "site")
    monkeypatch.setattr(ai_cost, "DATA", source.parent / "data")
    monkeypatch.setattr(ai_cost, "secret_present", lambda name: False)
    monkeypatch.setattr(ai_cost, "unified", lambda: None)
    result = ai_cost.estimate({})
    assert "monthly_usd" in result
    assert "configuration_adoption" in result
    assert result["configuration_adoption"]["state"] == "SOURCE_CHANGED"
    assert result["configuration_adoption"]["scope"] == "current_process_source_snapshot"


def test_changed_module_root_is_not_reported_matching(source, monkeypatch, tmp_path):
    config.load()
    other = tmp_path / "other"
    other.mkdir()
    (other / "config.yml").write_bytes(source.read_bytes())
    monkeypatch.setattr(config, "ROOT", other)
    assert observe()["state"] == "SOURCE_ROOT_CHANGED"
    assert observe()["source_bytes_match"] is None


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_nonregular_sources_are_refused_without_loading(source, kind, tmp_path):
    source.unlink()
    if kind == "symlink":
        target = tmp_path / "not-config.txt"
        target.write_text("must-not-be-read")
        source.symlink_to(target)
    elif kind == "directory":
        source.mkdir()
    else:
        import os
        os.mkfifo(source)
    result = observe()
    assert result["state"] == "SOURCE_UNAVAILABLE"
    assert result["installed_sha256"] is None
    assert config.load.cache_info().currsize == 0


def test_oversized_source_is_bounded_and_does_not_initialize(source, monkeypatch):
    monkeypatch.setattr(config, "_MAX_OBSERVER_BYTES", 32)
    source.write_bytes(b"x" * 33)
    assert observe()["state"] == "SOURCE_TOO_LARGE"
    assert config.load.cache_info().currsize == 0


def test_source_changed_during_read_is_not_a_matching_observation(source, monkeypatch):
    config.load()
    original = Path.lstat
    reads = []
    def changing(path, *args, **kwargs):
        if path == source:
            reads.append(True)
            if len(reads) == 2:
                source.write_text("master_brain:\n  llm_model: model-changed-during-read\n")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", changing)
    result = observe()
    assert result["state"] == "SOURCE_CHANGED_DURING_OBSERVATION"
    assert result["source_bytes_match"] is None
    assert result["installed_sha256"] is None


def test_admin_observer_does_not_import_an_unloaded_config_owner(source, monkeypatch):
    import sys
    from admin import ai_cost
    with monkeypatch.context() as local:
        local.delitem(sys.modules, "lib.config")
        assert ai_cost._configuration_adoption() is None
        assert "lib.config" not in sys.modules


def test_existing_http_response_reports_stale_loaded_source(source, monkeypatch):
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from admin import ai_cost, server
    config.load()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    monkeypatch.setattr(ai_cost, "ROOT", source.parent)
    monkeypatch.setattr(ai_cost, "SITE", source.parent / "site")
    monkeypatch.setattr(ai_cost, "DATA", source.parent / "data")
    monkeypatch.setattr(ai_cost, "secret_present", lambda name: False)
    monkeypatch.setattr(ai_cost, "unified", lambda: None)
    monkeypatch.setattr(ai_cost.config_store, "read_config", lambda: {})
    monkeypatch.setattr(server.settings, "auth_enabled", lambda: False)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/cost?force=1", timeout=5) as response:
            result = json.loads(response.read())
        assert result["configuration_adoption"]["state"] == "SOURCE_CHANGED"
        assert result["configuration_adoption"]["scope"] == "current_process_source_snapshot"
        assert "monthly_usd" in result
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)


def test_empty_or_invalid_yaml_retains_existing_loader_semantics(source):
    source.write_text("")
    assert config.load() is None
    assert observe()["state"] == "MATCHING_SOURCE"
    config.load.cache_clear()
    source.write_text("broken: [")
    import yaml
    with pytest.raises(yaml.YAMLError):
        config.load()
    assert observe()["state"] == "NOT_LOADED"


def test_unwrapped_load_does_not_replace_the_cached_snapshot(source):
    original = config.load()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    assert config.load.__wrapped__()["master_brain"]["llm_model"] == "model-b"
    assert config.load() is original
    assert observe()["state"] == "SOURCE_CHANGED"


def test_mutated_values_are_not_misrepresented_as_effective_configuration(source):
    config.load()["master_brain"]["llm_model"] = "runtime-override"
    result = observe()
    assert result["state"] == "MATCHING_SOURCE"
    assert "runtime_overrides" in result["not_covered"]
    assert "runtime-override" not in json.dumps(result)


def test_observation_never_echoes_read_failure_details(source, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("synthetic-sensitive-value /private/credential-home")
    with monkeypatch.context() as local:
        local.setattr(config.os, "open", denied)
        result = observe()
    assert result["state"] == "SOURCE_UNAVAILABLE"
    assert "synthetic-sensitive-value" not in json.dumps(result)
    assert "/private/credential-home" not in json.dumps(result)


def test_parallel_first_load_has_one_coherent_source_snapshot(source):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda _: config.load(), range(12)))
    assert all(value is values[0] for value in values)
    assert config.load.cache_info().misses == 1
    result = observe()
    assert result["state"] == "MATCHING_SOURCE"
    assert result["loaded_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_existing_http_auth_blocks_the_adoption_observer(source, monkeypatch):
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer
    from admin import ai_cost, server
    calls = []
    monkeypatch.setattr(server.settings, "auth_enabled", lambda: True)
    monkeypatch.setattr(server.Handler, "_authed", lambda self: False)
    monkeypatch.setattr(ai_cost, "estimate", lambda *a, **k: calls.append(True) or {})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/cost?force=1", timeout=5)
        assert caught.value.code == 401
        caught.value.close()
        assert calls == []
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)


def test_adoption_suite_is_in_an_existing_code_gate():
    import shlex
    from scripts.run_ci_pack import load_legacy_jobs, partition_jobs
    root = Path(__file__).resolve().parents[1]
    jobs = load_legacy_jobs(root / ".github/ci/legacy-jobs.yml", gate="code")
    command = ["python", "-m", "pytest", "tests/test_config_adoption.py", "-q"]
    matches = [(job, step) for pack in partition_jobs(jobs, 12) for job in pack
               for step in job.definition["steps"]
               if shlex.split(step.get("run", ""), comments=True) == command]
    assert len(matches) == 1
    job, step = matches[0]
    assert job.job_id == "unrun-brain-desks"
    assert "if" not in step and not step.get("continue-on-error", False)


def test_same_size_and_preserved_mtime_do_not_hide_a_configuration_change(source):
    import os
    before = source.stat()
    config.load()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    assert source.stat().st_size == before.st_size
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    result = observe()
    assert result["state"] == "SOURCE_CHANGED"
    assert result["loaded_sha256"] != result["installed_sha256"]


def test_unknown_observation_never_claims_current_adoption(source, monkeypatch):
    config.load()
    monkeypatch.setattr(config, "ROOT", object())
    result = observe()
    assert result["state"] == "OBSERVATION_UNAVAILABLE"
    assert result["source_bytes_match"] is None


def test_matching_loader_does_not_claim_retained_references_were_updated(source):
    previous = config.load()
    source.write_text("master_brain:\n  llm_model: model-b\n")
    config.load.cache_clear()
    current = config.load()
    assert current is not previous
    assert previous["master_brain"]["llm_model"] == "model-a"
    assert current["master_brain"]["llm_model"] == "model-b"
    result = observe()
    assert result["state"] == "MATCHING_SOURCE"
    assert "retained_config_references" in result["not_covered"]
