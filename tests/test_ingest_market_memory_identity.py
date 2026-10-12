from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.neuralweb import market_memory_identity_observation as OBSERVATION
from engine.neuralweb import market_memory_identity_store as STORE
from lib import symbol_directory_receipts as RECEIPTS
from scripts import ingest_market_memory_identity as INGEST

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "symbol_directory" / "snapshots"

_OPEN_TRACE: list[str] | None = None


def _record_open(event: str, args: tuple) -> None:
    if event != "open" or not isinstance(_OPEN_TRACE, list):
        return
    target = args[0]
    if isinstance(target, int):
        return
    _OPEN_TRACE.append(os.fsdecode(os.fspath(target)))


sys.addaudithook(_record_open)


def _pyc_to_py(path: Path) -> Path:
    if path.parent.name == "__pycache__":
        match = re.fullmatch(r"(?P<stem>.+)\.cpython-[^.]+\.pyc", path.name)
        if match:
            return path.parent.parent / f"{match['stem']}.py"
    return path


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _temporary_repository(tmp_path: Path, *, tracked_count: int = 1) -> Path:
    repository = tmp_path / "repository"
    target = repository / "data" / "symbol_directory" / "snapshots"
    target.mkdir(parents=True)
    sources = sorted(SNAPSHOTS.glob("*.parquet"))
    assert len(sources) >= tracked_count + 1
    for source in sources[: tracked_count + 1]:
        shutil.copyfile(source, target / source.name)
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "tests@example.invalid")
    _git(repository, "config", "user.name", "Market Memory Tests")
    for source in sources[:tracked_count]:
        _git(repository, "add", f"data/symbol_directory/snapshots/{source.name}")
    _git(repository, "commit", "-qm", "fixture")
    return repository


def _operational_repository(tmp_path: Path) -> tuple[Path, dict]:
    repository = tmp_path / "operational-repository"
    partition = "2026-08-11"
    snapshot = (
        repository / "data" / "symbol_directory" / "snapshots" / f"{partition}.parquet"
    )
    frame = pd.read_parquet(min(SNAPSHOTS.glob("*.parquet")))
    frame["date"] = partition
    RECEIPTS.durable_atomic_write_parquet(frame, snapshot)
    sources = (
        (
            RECEIPTS.NASDAQ_LISTED_SOURCE_ID,
            RECEIPTS.SourceFetch(
                value="decoded Nasdaq response",
                content=b"exact Nasdaq response bytes\r\n",
                requested_url=(
                    "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
                ),
                started_at=f"{partition}T00:00:01.000000Z",
                completed_at=f"{partition}T00:00:01.100000Z",
            ),
        ),
        (
            RECEIPTS.OTHER_LISTED_SOURCE_ID,
            RECEIPTS.SourceFetch(
                value="decoded other response",
                content=b"exact other response bytes\r\n",
                requested_url=(
                    "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
                ),
                started_at=f"{partition}T00:00:02.000000Z",
                completed_at=f"{partition}T00:00:02.100000Z",
            ),
        ),
    )
    source_counts = frame["source"].value_counts().to_dict()
    spy = frame.loc[frame["symbol"] == "SPY"].iloc[0]
    receipt = RECEIPTS.build_symbol_directory_completion_receipt(
        kind="listing_snapshot",
        observation_date=partition,
        artifact_path=snapshot,
        source_fetches=sources,
        collector_started_at=f"{partition}T00:00:00.000000Z",
        collector_completed_at=f"{partition}T00:00:04.000000Z",
        pre_dedupe_rows=len(frame),
        duplicate_occurrences=0,
        duplicate_key_count=0,
        source_row_counts=(
            (
                RECEIPTS.NASDAQ_LISTED_SOURCE_ID,
                int(source_counts.get("nasdaqlisted", 0)),
            ),
            (
                RECEIPTS.OTHER_LISTED_SOURCE_ID,
                int(source_counts.get("otherlisted", 0)),
            ),
        ),
        pre_dedupe_spy_occurrences=(
            {
                "source_id": RECEIPTS.OTHER_LISTED_SOURCE_ID,
                "symbol": "SPY",
                "security_name": spy["security_name"],
                "exchange": spy["exchange"],
                "etf": bool(spy["etf"]),
                "test_issue": bool(spy["test_issue"]),
                "is_preferred": bool(spy["is_preferred"]),
            },
        ),
        non_authoritative_footers=(
            RECEIPTS.footer_diagnostic(
                source_id=RECEIPTS.NASDAQ_LISTED_SOURCE_ID,
                text=f"File Creation Time: {partition} 00:00:01",
            ),
            RECEIPTS.footer_diagnostic(
                source_id=RECEIPTS.OTHER_LISTED_SOURCE_ID,
                text=f"File Creation Time: {partition} 00:00:02",
            ),
        ),
    )
    sidecar = RECEIPTS.completion_receipt_path(
        snapshot.parent.parent,
        kind="listing_snapshot",
        observation_date=partition,
    )
    RECEIPTS.write_symbol_directory_completion_receipt(
        sidecar,
        receipt,
        snapshot,
        expected_kind="listing_snapshot",
    )
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "tests@example.invalid")
    _git(repository, "config", "user.name", "Market Memory Tests")
    _git(repository, "add", "data/symbol_directory")
    _git(repository, "commit", "-qm", "operational fixture")
    return repository, receipt


def test_ingest_captures_only_git_owned_snapshots_and_retries_idempotently(
    tmp_path: Path,
) -> None:
    repository = _temporary_repository(tmp_path)
    store = tmp_path / "identity-store"

    first = INGEST.ingest_identity_observations(repository, store_root=store)
    second = INGEST.ingest_identity_observations(repository, store_root=store)

    assert first["tracked_snapshot_count"] == 1
    assert first["published_count"] == 1
    assert first["idempotent_count"] == 0
    assert first["reconstruction_count"] == 1
    assert first["operational_count"] == 0
    assert second["tracked_snapshot_count"] == 1
    assert second["published_count"] == 0
    assert second["idempotent_count"] == 1
    assert second["generation_id"] == first["generation_id"]
    assert first["authority"] == {
        "context_only": True,
        "training_eligible": False,
        "promotion_eligible": False,
    }


def test_ingest_admits_an_exact_tracked_post_cutoff_receipt_operationally(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, receipt = _operational_repository(tmp_path)
    store = tmp_path / "identity-store"
    monkeypatch.setattr(
        OBSERVATION,
        "_utc_now",
        lambda: datetime(2026, 8, 11, 0, 5, tzinfo=timezone.utc),
    )

    result = INGEST.ingest_identity_observations(repository, store_root=store)
    snapshot = STORE.load_identity_observation_store(
        store,
        repository_root=repository,
    )
    assert result["tracked_snapshot_count"] == 1
    assert result["published_count"] == 1
    assert result["operational_count"] == 1
    assert result["reconstruction_count"] == 0
    assert snapshot.head["capture_count"] == 1
    assert snapshot.captures[0].observation["pit_basis"] == "live_captured"
    assert snapshot.captures[0].completion_receipt == receipt


def test_ingest_rejects_a_worktree_snapshot_that_differs_from_the_pinned_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _temporary_repository(tmp_path)
    real_tracked_bytes = INGEST._tracked_bytes

    def changed_bytes(root: Path, commit: str, key: str) -> bytes:
        return real_tracked_bytes(root, commit, key) + b"changed"

    monkeypatch.setattr(INGEST, "_tracked_bytes", changed_bytes)
    with pytest.raises(INGEST.IdentityIngestError, match="not owned"):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


def test_ingest_never_downgrades_a_tracked_but_missing_receipt_to_reconstruction(
    tmp_path: Path,
) -> None:
    repository = _temporary_repository(tmp_path)
    snapshot_key = _git(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
        "--",
        "data/symbol_directory/snapshots",
    )
    partition = Path(snapshot_key).stem
    receipt = (
        repository
        / "data"
        / "symbol_directory"
        / "receipts"
        / "snapshots"
        / f"{partition}.json"
    )
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}\n", encoding="utf-8")
    _git(repository, "add", receipt.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "track completion receipt")
    receipt.unlink()
    store = tmp_path / "identity-store"

    with pytest.raises(INGEST.IdentityIngestError, match="presence differs"):
        INGEST.ingest_identity_observations(repository, store_root=store)

    assert not list((store / "captures").rglob("*.json"))


def test_ingest_rejects_a_tracked_receipt_without_its_snapshot(tmp_path: Path) -> None:
    repository = _temporary_repository(tmp_path)
    orphan = (
        repository
        / "data"
        / "symbol_directory"
        / "receipts"
        / "snapshots"
        / "2099-01-01.json"
    )
    orphan.parent.mkdir(parents=True)
    orphan.write_text("{}\n", encoding="utf-8")
    _git(repository, "add", orphan.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "track orphan receipt")

    with pytest.raises(INGEST.IdentityIngestError, match="no matching snapshot"):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


def test_ingest_fails_closed_when_checkout_head_changes_during_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _temporary_repository(tmp_path)
    original = INGEST._repository_commit(repository)
    calls = 0

    def moving_head(root: Path) -> str:
        nonlocal calls
        calls += 1
        return original if calls == 1 else "f" * 40

    monkeypatch.setattr(INGEST, "_repository_commit", moving_head)
    with pytest.raises(INGEST.IdentityIngestError, match="changed during"):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


def _capture_with_mid_run_commit(commit_action):
    """Wrap the store capture so the first call moves the checkout first."""

    real_capture = STORE.capture_spy_listing_observation
    calls = 0

    def capture(store, bundle, *, repository_root):
        nonlocal calls
        calls += 1
        if calls == 1:
            commit_action()
        return real_capture(store, bundle, repository_root=repository_root)

    return capture


def test_ingest_completes_when_the_checkout_moves_only_unrelated_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _temporary_repository(tmp_path)
    before = INGEST._repository_commit(repository)

    def commit_unrelated_tracked_file() -> None:
        (repository / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
        _git(repository, "add", "unrelated.txt")
        _git(repository, "commit", "-qm", "unrelated tracked file")

    monkeypatch.setattr(
        STORE,
        "capture_spy_listing_observation",
        _capture_with_mid_run_commit(commit_unrelated_tracked_file),
    )

    moved = INGEST.ingest_identity_observations(
        repository,
        store_root=tmp_path / "moved-store",
    )

    after = INGEST._repository_commit(repository)
    assert moved["deployed_commit"] == before
    assert moved["completion_commit"] == after
    assert moved["completion_commit"] != moved["deployed_commit"]

    reference = INGEST.ingest_identity_observations(
        _temporary_repository(tmp_path / "reference"),
        store_root=tmp_path / "reference-store",
    )
    for count in ("published_count", "idempotent_count", "divergence_count"):
        assert moved[count] == reference[count]


def test_ingest_fails_closed_when_the_checkout_moves_an_identity_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _temporary_repository(tmp_path)
    snapshots = repository / "data" / "symbol_directory" / "snapshots"

    def commit_extra_identity_snapshot() -> None:
        shutil.copyfile(
            min(snapshots.glob("*.parquet")),
            snapshots / "2030-01-01.parquet",
        )
        _git(
            repository,
            "add",
            "data/symbol_directory/snapshots/2030-01-01.parquet",
        )
        _git(repository, "commit", "-qm", "track an extra identity snapshot")

    monkeypatch.setattr(
        STORE,
        "capture_spy_listing_observation",
        _capture_with_mid_run_commit(commit_extra_identity_snapshot),
    )

    with pytest.raises(
        INGEST.IdentityIngestError,
        match="changed during.*identity path",
    ):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


def test_ingest_fails_closed_when_the_checkout_moves_a_loaded_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _temporary_repository(tmp_path)
    dependency = repository / "fake_identity_dependency.py"
    dependency.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repository, "add", "fake_identity_dependency.py")
    _git(repository, "commit", "-qm", "track the fake identity dependency")
    module = types.ModuleType("fake_identity_dependency")
    module.__file__ = str(dependency)
    monkeypatch.setitem(sys.modules, "fake_identity_dependency", module)

    def commit_loaded_module_edit() -> None:
        dependency.write_text("VALUE = 2\n", encoding="utf-8")
        _git(repository, "add", "fake_identity_dependency.py")
        _git(repository, "commit", "-qm", "edit the loaded module")

    monkeypatch.setattr(
        STORE,
        "capture_spy_listing_observation",
        _capture_with_mid_run_commit(commit_loaded_module_edit),
    )

    with pytest.raises(INGEST.IdentityIngestError, match="changed during"):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


def test_ingest_fails_closed_when_a_module_imported_during_capture_moves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A module first imported inside the per-key loop must be judged at completion, not snapshotted before the loop."""
    repository = _temporary_repository(tmp_path)
    dependency = repository / "fake_lazy_identity_dependency.py"
    dependency.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repository, "add", "fake_lazy_identity_dependency.py")
    _git(repository, "commit", "-qm", "track the lazily imported dependency")
    monkeypatch.delitem(sys.modules, "fake_lazy_identity_dependency", raising=False)
    assert "fake_lazy_identity_dependency" not in sys.modules  # non-vacuity: not loaded before the run

    def import_lazily_then_commit_edit() -> None:
        module = types.ModuleType("fake_lazy_identity_dependency")
        module.__file__ = str(dependency)
        monkeypatch.setitem(sys.modules, "fake_lazy_identity_dependency", module)
        dependency.write_text("VALUE = 2\n", encoding="utf-8")
        _git(repository, "add", "fake_lazy_identity_dependency.py")
        _git(repository, "commit", "-qm", "edit the lazily imported module")

    monkeypatch.setattr(
        STORE,
        "capture_spy_listing_observation",
        _capture_with_mid_run_commit(import_lazily_then_commit_edit),
    )

    with pytest.raises(INGEST.IdentityIngestError, match="changed during.*identity path"):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


def test_completion_paths_cover_every_checkout_file_the_ingest_opens(
    tmp_path: Path,
) -> None:
    global _OPEN_TRACE
    repository, _receipt = _operational_repository(tmp_path)
    RECEIPTS._validator.cache_clear()
    store_root = (tmp_path / "trace-store").resolve()
    _OPEN_TRACE = []
    try:
        INGEST.ingest_identity_observations(repository, store_root=store_root)
    finally:
        trace = _OPEN_TRACE
        _OPEN_TRACE = None
    assert isinstance(trace, list)

    entries = INGEST._IDENTITY_INPUT_PATHS
    modules = {root: set(INGEST._loaded_checkout_modules(root)) for root in (repository, ROOT)}
    covered: set[str] = set()
    uncovered: list[str] = []
    for raw in trace:
        path = _pyc_to_py(Path(raw).resolve())
        posix = path.as_posix()
        if path.is_relative_to(store_root) or "/.git/" in posix:
            continue
        for root in (repository, ROOT):
            try:
                rel = path.relative_to(root.resolve()).as_posix()
            except ValueError:
                continue
            if any(rel == entry or rel.startswith(entry + "/") for entry in entries) or rel in modules[root]:
                covered.add(rel)
            else:
                uncovered.append(rel)
            break

    assert not uncovered, f"unopened-coverage checkout paths: {sorted(uncovered)}"
    assert any(
        rel.startswith("data/symbol_directory/snapshots/") and rel.endswith(".parquet")
        for rel in covered
    )
    assert any(
        rel.startswith("data/symbol_directory/receipts/snapshots/")
        and rel.endswith(".json")
        for rel in covered
    )
    assert "config/market_memory_canary.v1.json" in covered
    assert (
        "contracts/symbol_directory/symbol_directory_completion_receipt.v1.schema.json"
        in covered
    )
    print("COVERED_PATHS_BEGIN")
    for rel in sorted(covered):
        print(f"COVERED {rel}")
    print("COVERED_PATHS_END")


@pytest.mark.parametrize(
    "path",
    [
        "config/market_memory_canary.v1.json",
        "contracts/symbol_directory/symbol_directory_completion_receipt.v1.schema.json",
    ],
    ids=("config", "schema"),
)
def test_ingest_fails_closed_when_the_checkout_moves_a_non_module_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    repository = _temporary_repository(tmp_path)

    def commit_non_module_input() -> None:
        target = repository / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
        _git(repository, "add", path)
        _git(repository, "commit", "-qm", f"track {path}")

    monkeypatch.setattr(
        STORE,
        "capture_spy_listing_observation",
        _capture_with_mid_run_commit(commit_non_module_input),
    )

    with pytest.raises(
        INGEST.IdentityIngestError,
        match="changed during.*identity path",
    ):
        INGEST.ingest_identity_observations(
            repository,
            store_root=tmp_path / "identity-store",
        )


@pytest.mark.parametrize(
    "moved",
    ["unrelated", "config"],
    ids=("unrelated", "config"),
)
def test_ingest_on_a_depth_one_deployed_clone_judges_the_tree_not_the_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    moved: str,
) -> None:
    origin = _temporary_repository(tmp_path)
    branch = _git(origin, "rev-parse", "--abbrev-ref", "HEAD")
    deployed = tmp_path / "deployed"
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{origin}", str(deployed))
    _git(deployed, "config", "user.email", "tests@example.invalid")
    _git(deployed, "config", "user.name", "Market Memory Tests")
    assert _git(deployed, "rev-parse", "--is-shallow-repository") == "true"
    before = INGEST._repository_commit(deployed)

    def deploy_pull() -> None:
        if moved == "unrelated":
            (origin / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
            _git(origin, "add", "unrelated.txt")
        else:
            canary = origin / "config" / "market_memory_canary.v1.json"
            canary.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "config" / "market_memory_canary.v1.json", canary)
            _git(origin, "add", "config/market_memory_canary.v1.json")
        _git(origin, "commit", "-qm", "push a new deployed tip")
        _git(deployed, "fetch", "--depth", "1", "-q", "origin", branch)
        _git(deployed, "reset", "--hard", "-q", "FETCH_HEAD")
        assert _git(deployed, "rev-list", "--count", "HEAD") == "1"

    monkeypatch.setattr(
        STORE,
        "capture_spy_listing_observation",
        _capture_with_mid_run_commit(deploy_pull),
    )

    if moved == "unrelated":
        result = INGEST.ingest_identity_observations(
            deployed,
            store_root=tmp_path / "identity-store",
        )
        assert result["deployed_commit"] == before
        assert result["completion_commit"] == _git(deployed, "rev-parse", "HEAD")
        assert result["completion_commit"] != before
    else:
        with pytest.raises(
            INGEST.IdentityIngestError,
            match="changed during.*identity path",
        ):
            INGEST.ingest_identity_observations(
                deployed,
                store_root=tmp_path / "identity-store",
            )


def test_loaded_checkout_modules_lists_only_files_inside_the_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repository"
    inside = root / "engine" / "inside.py"
    inside.parent.mkdir(parents=True)
    inside.write_text("pass\n", encoding="utf-8")
    inside_module = types.ModuleType("inside_module")
    inside_module.__file__ = str(inside)
    outside_module = types.ModuleType("outside_module")
    outside_module.__file__ = str(tmp_path / "outside.py")
    monkeypatch.setitem(sys.modules, "inside_module", inside_module)
    monkeypatch.setitem(sys.modules, "outside_module", outside_module)
    monkeypatch.setitem(
        sys.modules,
        "bare_module",
        types.ModuleType("bare_module"),
    )

    assert INGEST._loaded_checkout_modules(root) == ("engine/inside.py",)


def test_entry_script_pins_the_repository_before_importing_engine_modules() -> None:
    source = (ROOT / "scripts" / "ingest_market_memory_identity.py").read_text(
        encoding="utf-8"
    )
    function = source.index("def ingest_identity_observations(")
    pin = source.index("deployed_commit = _repository_commit(root)", function)
    engine_import = source.index("from engine.neuralweb import", function)
    post_import_check = source.index(
        "if _repository_commit(root) != deployed_commit:", engine_import
    )
    assert "from engine.neuralweb import" not in source[:function]
    assert pin < engine_import < post_import_check


def _rewrite_snapshot(path: Path) -> None:
    frame = pd.read_parquet(path)
    path.unlink()
    RECEIPTS.durable_atomic_write_parquet(frame.iloc[:-1].copy(), path)


def test_ingest_replay_over_a_captured_date_with_identical_bytes_is_a_noop(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _temporary_repository(tmp_path)
    store = tmp_path / "identity-store"

    first = INGEST.ingest_identity_observations(repository, store_root=store)
    capsys.readouterr()
    second = INGEST.ingest_identity_observations(repository, store_root=store)

    assert second["published_count"] == 0
    assert second["idempotent_count"] == 1
    assert second["divergence_count"] == 0
    assert second["divergences"] == []
    assert second["generation_id"] == first["generation_id"]
    warnings = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("::warning")
    ]
    assert warnings == []


def test_ingest_records_an_upstream_rewrite_after_capture_and_keeps_accruing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _temporary_repository(tmp_path)
    store = tmp_path / "identity-store"

    first = INGEST.ingest_identity_observations(repository, store_root=store)
    assert first["published_count"] == 1

    tracked_key = _git(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
        "--",
        "data/symbol_directory/snapshots",
    )
    tracked_name = Path(tracked_key).name
    date_partition = Path(tracked_key).stem
    snapshot_dir = repository / "data" / "symbol_directory" / "snapshots"
    untracked = [
        path
        for path in sorted(snapshot_dir.glob("*.parquet"))
        if path.name != tracked_name
    ]
    assert len(untracked) == 1

    captured = STORE.load_identity_observation_store(store, repository_root=repository)
    stored_capture = next(
        capture
        for capture in captured.captures
        if capture.observation["date_partition"] == date_partition
    )
    stored_id = stored_capture.observation["source_observation_id"]
    original_bytes = stored_capture.source_artifact_bytes
    assert original_bytes == (snapshot_dir / tracked_name).read_bytes()

    _rewrite_snapshot(snapshot_dir / tracked_name)
    _git(repository, "add", f"data/symbol_directory/snapshots/{tracked_name}")
    _git(repository, "add", f"data/symbol_directory/snapshots/{untracked[0].name}")
    _git(repository, "commit", "-qm", "rewrite captured date and track the next one")
    capsys.readouterr()

    second = INGEST.ingest_identity_observations(repository, store_root=store)

    assert second["tracked_snapshot_count"] == 2
    assert second["divergence_count"] == 1
    assert second["published_count"] == 1
    assert second["idempotent_count"] == 0
    assert (
        second["published_count"]
        + second["idempotent_count"]
        + second["divergence_count"]
        == second["tracked_snapshot_count"]
    )
    divergence = second["divergences"][0]
    assert divergence["kind"] == "upstream_rewrite_after_capture"
    assert divergence["date_partition"] == date_partition
    assert divergence["authoritative"] == "stored"
    assert divergence["stored_source_observation_id"] == stored_id
    assert divergence["candidate_source_observation_id"] != stored_id
    assert re.fullmatch(r"[0-9a-f]{64}", divergence["stored_source_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", divergence["candidate_source_sha256"])
    assert divergence["stored_source_sha256"] != divergence["candidate_source_sha256"]

    warning_prefix = "::warning title=upstream_rewrite_after_capture::"
    warning_lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(warning_prefix)
    ]
    assert len(warning_lines) == 1
    assert json.loads(warning_lines[0][len(warning_prefix) :]) == divergence

    after = STORE.load_identity_observation_store(store, repository_root=repository)
    after_capture = next(
        capture
        for capture in after.captures
        if capture.observation["date_partition"] == date_partition
    )
    assert after_capture.observation["source_observation_id"] == stored_id
    assert after_capture.source_artifact_bytes == original_bytes
    after_dates = {
        capture.observation["date_partition"] for capture in after.captures
    }
    assert untracked[0].stem in after_dates

    capsys.readouterr()
    third = INGEST.ingest_identity_observations(repository, store_root=store)
    assert third["divergence_count"] == 1
    assert third["published_count"] == 0
    assert third["idempotent_count"] == 1
    assert third["generation_id"] == second["generation_id"]


def test_ingest_completes_when_every_tracked_date_diverges(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _temporary_repository(tmp_path)
    store = tmp_path / "identity-store"

    first = INGEST.ingest_identity_observations(repository, store_root=store)
    assert first["published_count"] == 1
    captured = STORE.load_identity_observation_store(store, repository_root=repository)
    recorded_generation_id = captured.head["generation_id"]

    def store_digests() -> dict[str, str]:
        return {
            path.relative_to(store).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(store.rglob("*"))
            if path.is_file()
        }

    recorded_digests = store_digests()

    tracked_key = _git(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
        "--",
        "data/symbol_directory/snapshots",
    )
    tracked_name = Path(tracked_key).name
    snapshot_dir = repository / "data" / "symbol_directory" / "snapshots"
    _rewrite_snapshot(snapshot_dir / tracked_name)
    _git(repository, "add", f"data/symbol_directory/snapshots/{tracked_name}")
    _git(repository, "commit", "-qm", "rewrite the only tracked date")
    capsys.readouterr()

    second = INGEST.ingest_identity_observations(repository, store_root=store)

    assert second["tracked_snapshot_count"] == 1
    assert second["published_count"] == 0
    assert second["idempotent_count"] == 0
    assert second["divergence_count"] == 1
    assert second["generation_id"] == recorded_generation_id
    assert store_digests() == recorded_digests
    warning_prefix = "::warning title=upstream_rewrite_after_capture::"
    warning_lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(warning_prefix)
    ]
    assert len(warning_lines) == 1


def test_ingest_of_uncaptured_dates_is_unchanged_by_the_divergence_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _temporary_repository(tmp_path, tracked_count=2)
    store = tmp_path / "identity-store"

    result = INGEST.ingest_identity_observations(repository, store_root=store)

    assert result["published_count"] == 2
    assert result["idempotent_count"] == 0
    assert result["divergence_count"] == 0
    assert result["divergences"] == []
    warnings = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("::warning")
    ]
    assert warnings == []
