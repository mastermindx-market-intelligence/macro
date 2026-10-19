"""Actual Git object-type provenance checks on a synthetic private fixture."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from engine.research_factory import market_memory_e0_installed_control as installed


@pytest.fixture
def source_repository():
    # /tmp is world-writable; it must not be allowed by the real ancestor guard.
    with tempfile.TemporaryDirectory(prefix="mm-source-test-", dir=Path.home()) as directory:
        root = Path(directory)
        for name in installed._SOURCE_PATHS:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic source fixture\n")
            path.chmod(0o600)
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("GIT_")}
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        def git(*args):
            return subprocess.check_output(
                ["/usr/bin/git", "-C", str(root), *args], env=environment, text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Synthetic", "-c", "user.email=test@example.invalid",
            "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Synthetic source")
        yield root, git


def test_exact_commit_with_matching_installed_bytes_is_consistent(source_repository):
    root, git = source_repository
    assert installed._verify_source(root, git("rev-parse", "HEAD")) is None


def test_raw_tree_cannot_be_labeled_as_a_source_commit(source_repository):
    root, git = source_repository
    tree = git("rev-parse", "HEAD^{tree}")
    assert git("ls-tree", tree) == git("ls-tree", "HEAD")
    with pytest.raises(installed.E0InstalledControlError, match="selected_source_commit_invalid"):
        installed._verify_source(root, tree)


def test_annotated_tag_cannot_be_labeled_as_a_source_commit(source_repository):
    root, git = source_repository
    git("-c", "user.name=Synthetic", "-c", "user.email=test@example.invalid",
        "tag", "-a", "synthetic", "-m", "Synthetic tag")
    tag = git("rev-parse", "refs/tags/synthetic")
    with pytest.raises(installed.E0InstalledControlError, match="selected_source_commit_invalid"):
        installed._verify_source(root, tag)


def test_git_environment_cannot_select_a_foreign_object_store(source_repository, monkeypatch):
    root, git = source_repository
    commit = git("rev-parse", "HEAD")
    monkeypatch.setenv("GIT_DIR", "/nonexistent/foreign/git")
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "/nonexistent/foreign/objects")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    assert installed._verify_source(root, commit) is None


def test_installed_byte_drift_is_still_refused(source_repository):
    root, git = source_repository
    commit = git("rev-parse", "HEAD")
    (root / installed._SOURCE_PATHS[0]).write_bytes(b"changed synthetic bytes\n")
    with pytest.raises(installed.E0InstalledControlError, match="installed_source_changed"):
        installed._verify_source(root, commit)


@pytest.mark.parametrize("changed", [
    "engine/neuralweb/market_memory_episode_retrieval.py",
    "engine/research_factory/market_memory_e0_task_evidence.py",
    "contracts/market_memory/e0_tasks.v1.schema.json",
])
def test_task_preparation_requires_expanded_source_closure_and_exact_bytes(source_repository, changed):
    root, git = source_repository
    with pytest.raises(installed.E0InstalledControlError, match="selected_source_closure_incomplete"):
        installed._verify_source(root, git("rev-parse", "HEAD"), paths=installed._TASK_SOURCE_PATHS)
    for name in set(installed._TASK_SOURCE_PATHS) - set(installed._SOURCE_PATHS):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic task preparation source\n")
        path.chmod(0o600)
    git("add", ".")
    git("-c", "user.name=Synthetic", "-c", "user.email=test@example.invalid",
        "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Synthetic expanded closure")
    commit = git("rev-parse", "HEAD")
    assert installed._verify_source(root, commit, paths=installed._TASK_SOURCE_PATHS) is None
    (root / changed).write_bytes(b"changed after selection\n")
    with pytest.raises(installed.E0InstalledControlError, match="installed_source_changed"):
        installed._verify_source(root, commit, paths=installed._TASK_SOURCE_PATHS)


def test_task_preparation_module_origins_include_native_method_and_domain_parser(monkeypatch):
    from engine.research_factory import market_memory_e0_task_evidence
    for relative in installed._TASK_SOURCE_PATHS:
        if relative.startswith("engine/") and relative.endswith(".py"):
            name = relative.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
            if name in sys.modules:
                monkeypatch.setattr(sys.modules[name], "__file__", str(installed.INSTALLED_ROOT / relative))
    installed._verify_loaded_sources(paths=installed._TASK_SOURCE_PATHS)
    monkeypatch.setattr(market_memory_e0_task_evidence, "__file__", "/foreign/task_evidence.py")
    with pytest.raises(installed.E0InstalledControlError, match="loaded_source_origin_invalid"):
        installed._verify_loaded_sources(paths=installed._TASK_SOURCE_PATHS)


@pytest.mark.parametrize("foreign_name", [
    "engine.research_factory.market_memory_contextual_registration",
    "engine.research_factory.market_memory_e0_access_history",
    "engine.research_factory.ledger",
])
def test_executed_project_module_must_match_installed_origin(monkeypatch, foreign_name):
    # Only a synthetic module-origin seam; never an actual OS grant.
    for relative in installed._SOURCE_PATHS:
        if relative.startswith("engine/") and relative.endswith(".py"):
            name = relative.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
            if name in sys.modules:
                monkeypatch.setattr(sys.modules[name], "__file__", str(installed.INSTALLED_ROOT / relative))
    installed._verify_loaded_sources()
    monkeypatch.setattr(sys.modules[foreign_name], "__file__", "/foreign/source.py")
    with pytest.raises(installed.E0InstalledControlError, match="loaded_source_origin_invalid"):
        installed._verify_loaded_sources()
