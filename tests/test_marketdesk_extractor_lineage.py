from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = REPO_ROOT / "collectors" / "marketdesk_extractor"
INSTALLER_PATH = CANONICAL_ROOT / "tools" / "install_runtime.py"
EXPECTED_PACKET_SHA256 = (
    "2019c38650493e4cfa40f7ed87c175a91ea939ca57d1f404ec73c5572c340e7a"
)
EXPECTED_MANIFEST_SHA256 = "85581c72a868c8b759e793925d1932cbd5309794f98638379ce06a0faff85e03"
EXPECTED_RECOVERY_MANIFEST_SHA256 = (
    "6209be070fbdfe8b8269bb62c0b6f466dac9b425ba1e9244b9b1bf7d983ba602"
)
EXPECTED_PAYLOAD_COUNT = 58
EXPECTED_INSTALLED_FILE_COUNT = 56
HISTORICAL_TEMPLATE_NON_GOAL = (
    "Recovered extractor/deploy/ai.marketdesk.* plists and "
    "extractor/docs/DEPLOY_MAC_STUDIO.md are historical lineage only; "
    "they are superseded and must not be activated."
)
EXPECTED_NON_GOALS = {
    "No new collector, queue, scheduler, database, bucket, prefix, or publication authority.",
    "No Research Vault data migration or rewrite.",
    "No product redesign.",
    "No live runtime activation from this import PR.",
    HISTORICAL_TEMPLATE_NON_GOAL,
}


def _load_installer():
    assert INSTALLER_PATH.is_file(), "canonical installer is missing"
    spec = importlib.util.spec_from_file_location("marketdesk_install_runtime", INSTALLER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_packet_manifest_is_exact_and_complete() -> None:
    installer = _load_installer()
    result = installer.verify_source(CANONICAL_ROOT)

    assert installer.EXPECTED_MANIFEST_SHA256 == EXPECTED_MANIFEST_SHA256
    assert result["ok"] is True
    assert result["payload_count"] == EXPECTED_PAYLOAD_COUNT
    assert result["manifest_sha256"] == EXPECTED_MANIFEST_SHA256
    assert result["receipt_manifest_sha256"] == EXPECTED_MANIFEST_SHA256
    assert result["recovery_manifest_sha256"] == EXPECTED_RECOVERY_MANIFEST_SHA256
    assert result["missing"] == []
    assert result["mismatched"] == []
    assert result["unexpected"] == []


def test_source_verifier_rejects_rewritten_manifest_even_when_payload_matches(
    tmp_path: Path,
) -> None:
    installer = _load_installer()
    copied_root = tmp_path / "canonical-copy"
    shutil.copytree(CANONICAL_ROOT, copied_root, symlinks=True)
    payload = copied_root / "extractor" / "README.md"
    payload.write_bytes(payload.read_bytes() + b"\nmanifest-drift\n")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest = copied_root / "SHA256SUMS"
    lines = manifest.read_text().splitlines()
    relative = "./extractor/README.md"
    matches = [index for index, line in enumerate(lines) if line.endswith(f"  {relative}")]
    assert len(matches) == 1
    lines[matches[0]] = f"{digest}  {relative}"
    manifest.write_text("\n".join(lines) + "\n")

    result = installer.verify_source(copied_root)

    assert result["ok"] is False


def test_source_verifier_rejects_coordinated_manifest_and_receipt_rewrite(
    tmp_path: Path,
) -> None:
    installer = _load_installer()
    copied_root = tmp_path / "canonical-copy"
    shutil.copytree(CANONICAL_ROOT, copied_root, symlinks=True)
    payload = copied_root / "extractor" / "README.md"
    payload.write_bytes(payload.read_bytes() + b"\ncoordinated-drift\n")
    payload_digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest = copied_root / "SHA256SUMS"
    lines = manifest.read_text().splitlines()
    relative = "./extractor/README.md"
    matches = [index for index, line in enumerate(lines) if line.endswith(f"  {relative}")]
    assert len(matches) == 1
    lines[matches[0]] = f"{payload_digest}  {relative}"
    manifest.write_text("\n".join(lines) + "\n")

    receipt_path = copied_root / "RELEASE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    result = installer.verify_source(copied_root)

    assert result["ok"] is False
    assert "frozen manifest hash" in result["receipt_error"]


def test_destination_mapping_refuses_unapproved_runtime_plist(tmp_path: Path) -> None:
    installer = _load_installer()
    copied_root = tmp_path / "canonical-copy"
    shutil.copytree(CANONICAL_ROOT, copied_root, symlinks=True)
    rogue = copied_root / "runtime" / "com.mastermindx.unapproved.plist"
    rogue.write_text("<plist/>\n")
    digest = hashlib.sha256(rogue.read_bytes()).hexdigest()
    with (copied_root / "SHA256SUMS").open("a") as handle:
        handle.write(f"{digest}  ./runtime/{rogue.name}\n")

    with pytest.raises(ValueError, match="unapproved runtime payload"):
        installer._destination_mappings(
            copied_root,
            tmp_path / "runtime",
            tmp_path / "feed.sh",
            tmp_path / "LaunchAgents",
        )


def test_import_receipt_pins_provenance_and_non_goals() -> None:
    receipt = json.loads((CANONICAL_ROOT / "IMPORT_RECEIPT.json").read_text())

    assert receipt["schema"] == "mastermind.marketdesk_extractor.import.v1"
    assert receipt["operation_key"] == "research-vault-source-lineage-r1-20260914-sol-001"
    assert receipt["source_packet"]["sha256"] == EXPECTED_PACKET_SHA256
    assert receipt["source_packet"]["manifest"] == "RECOVERY_SHA256SUMS"
    assert receipt["source_packet"]["manifest_sha256"] == EXPECTED_RECOVERY_MANIFEST_SHA256
    assert receipt["import_commit"] == "31981dc66e9a37419b5b7a6aecfde28808785d03"
    assert receipt["current_release_receipt"] == "RELEASE_RECEIPT.json"
    assert receipt["source_packet"]["payload_count"] == EXPECTED_PAYLOAD_COUNT
    assert receipt["canonical_root"] == "collectors/marketdesk_extractor"
    assert receipt["runtime_cutover_in_import_pr"] is False
    assert receipt["creates_new_execution_plane"] is False
    assert receipt["production_state_at_import"] == "PROVEN_LIVE_UNCHANGED"
    assert receipt["review_state"] == "DRAFT_HOLD_FOR_SOL"
    assert receipt["independent_review_required"] is True
    assert set(receipt["non_goals"]) == EXPECTED_NON_GOALS


def test_canonical_readme_preserves_hold_and_activation_boundaries() -> None:
    readme = " ".join((CANONICAL_ROOT / "README.md").read_text().split())
    required_phrases = (
        "source-lineage import was accepted in Macro PR #7164",
        "collector also owns the post-publication Research Vault ingest dispatch",
        "hourly GitHub Actions workflow remains the correction backstop",
        "RECOVERY_SHA256SUMS",
        "RELEASE_RECEIPT.json",
        "com.mastermindx.research-feed",
        "superseded and must remain unloaded",
        "sole production launchd authority",
        "removes the retired feed script and feed plist",
        "one no-new-row cycle",
        "one later natural publication",
        "production API and browser result",
        "rollback",
        "Destination overrides are for hermetic tests and rehearsals only",
    )
    for phrase in required_phrases:
        assert phrase in readme


def test_destination_override_help_is_explicitly_nonproduction() -> None:
    installer = _load_installer()
    parser = installer._build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, installer.argparse._SubParsersAction)
    )
    install_help = subparsers_action.choices["install"].format_help()
    rollback_help = subparsers_action.choices["rollback"].format_help()

    for help_text in (install_help, rollback_help):
        assert "non-production test/rehearsal override" in help_text


def _seed_runtime_state(runtime_root: Path, feed_script: Path, launch_agents: Path) -> None:
    runtime_root.mkdir(parents=True)
    (runtime_root / ".env").write_text("KEEP_SECRET=1\n")
    (runtime_root / ".venv" / "bin").mkdir(parents=True)
    (runtime_root / ".venv" / "bin" / "python").write_text("keep venv\n")
    for name in ("browser_profile", "data", "logs"):
        (runtime_root / name).mkdir()
        (runtime_root / name / "keep.txt").write_text(f"keep {name}\n")

    (runtime_root / "src").mkdir()
    (runtime_root / "src" / "stale.py").write_text("stale source\n")
    (runtime_root / "README.md").write_text("old readme\n")
    feed_script.parent.mkdir(parents=True, exist_ok=True)
    feed_script.write_text("old feed\n")
    launch_agents.mkdir(parents=True)
    (launch_agents / "com.mastermindx.research-feed.plist").write_text("old feed plist\n")
    (launch_agents / "com.mastermindx.research-trickle.plist").write_text(
        "old trickle plist\n"
    )


def test_install_verify_and_rollback_are_deterministic(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "mastermind-research" / "marketdesk_paper_extractor"
    feed_script = tmp_path / "mastermind-research" / "feed.sh"
    launch_agents = tmp_path / "Library" / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)

    receipt = installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )
    assert receipt["installed_files"] == EXPECTED_INSTALLED_FILE_COUNT
    assert not (runtime_root / "src" / "stale.py").exists()
    assert (runtime_root / ".env").read_text() == "KEEP_SECRET=1\n"
    assert (runtime_root / ".venv" / "bin" / "python").read_text() == "keep venv\n"
    for name in ("browser_profile", "data", "logs"):
        assert (runtime_root / name / "keep.txt").read_text() == f"keep {name}\n"

    readback = installer.verify_installed(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
    )
    assert readback["ok"] is True
    assert readback["matched"] == EXPECTED_INSTALLED_FILE_COUNT
    assert readback["missing"] == []
    assert readback["mismatched"] == []

    installed_readme = runtime_root / "README.md"
    installed_readme.write_text("drift\n")
    drift = installer.verify_installed(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
    )
    assert drift["ok"] is False
    assert str(installed_readme) in drift["mismatched"]

    rollback = installer.rollback(
        backup_dir=backup_dir,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
    )
    assert rollback["restored"] > 0
    assert (runtime_root / "README.md").read_text() == "old readme\n"
    assert (runtime_root / "src" / "stale.py").read_text() == "stale source\n"
    assert feed_script.read_text() == "old feed\n"
    assert (
        launch_agents / "com.mastermindx.research-feed.plist"
    ).read_text() == "old feed plist\n"
    assert (
        launch_agents / "com.mastermindx.research-trickle.plist"
    ).read_text() == "old trickle plist\n"
    assert (runtime_root / ".env").read_text() == "KEEP_SECRET=1\n"


def test_install_refuses_reusing_a_backup_directory(tmp_path: Path) -> None:
    installer = _load_installer()
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    with pytest.raises(FileExistsError):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=tmp_path / "runtime",
            feed_script=tmp_path / "feed.sh",
            launch_agents_dir=tmp_path / "LaunchAgents",
            backup_dir=backup_dir,
        )


def test_feed_watcher_compatibility_link_uses_the_recovered_runtime_script() -> None:
    compatibility_link = CANONICAL_ROOT / "feed.sh"
    runtime_script = CANONICAL_ROOT / "runtime" / "feed.sh"

    assert compatibility_link.is_symlink()
    assert os.readlink(compatibility_link) == "runtime/feed.sh"
    assert compatibility_link.read_bytes() == runtime_script.read_bytes()


def test_install_preflight_leaves_no_partial_backup_on_symlink_refusal(
    tmp_path: Path,
) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    (runtime_root / "src" / "unsafe-link.py").symlink_to(runtime_root / ".env")

    with pytest.raises(RuntimeError, match="symlink"):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
            backup_dir=backup_dir,
        )

    assert not backup_dir.exists()
    assert (runtime_root / "src" / "stale.py").read_text() == "stale source\n"
    assert (runtime_root / ".env").read_text() == "KEEP_SECRET=1\n"


def test_install_failure_rolls_back_before_returning_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)

    original_atomic_copy = installer._atomic_copy
    failed = False

    def fail_once(source: Path, destination: Path) -> None:
        nonlocal failed
        if not failed and source == CANONICAL_ROOT / "extractor" / "README.md":
            failed = True
            raise OSError("injected copy failure")
        original_atomic_copy(source, destination)

    monkeypatch.setattr(installer, "_atomic_copy", fail_once)
    with pytest.raises(OSError, match="injected copy failure"):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
            backup_dir=backup_dir,
        )

    assert failed is True
    assert (runtime_root / "README.md").read_text() == "old readme\n"
    assert (runtime_root / "src" / "stale.py").read_text() == "stale source\n"
    assert feed_script.read_text() == "old feed\n"
    assert (runtime_root / ".env").read_text() == "KEEP_SECRET=1\n"
    rollback_receipt = json.loads(
        (backup_dir / installer.ROLLBACK_RECEIPT).read_text()
    )
    assert rollback_receipt["phase"] == "rolled_back"


def test_install_refuses_backup_inside_managed_runtime(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"

    with pytest.raises(ValueError, match="outside the managed runtime root"):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=runtime_root,
            feed_script=tmp_path / "feed.sh",
            launch_agents_dir=tmp_path / "LaunchAgents",
            backup_dir=runtime_root / "backup",
        )


def test_source_verifier_rejects_symlinked_payload(tmp_path: Path) -> None:
    installer = _load_installer()
    copied_root = tmp_path / "canonical-copy"
    shutil.copytree(CANONICAL_ROOT, copied_root, symlinks=True)
    payload = copied_root / "extractor" / "README.md"
    same_bytes = tmp_path / "same-bytes.md"
    same_bytes.write_bytes(payload.read_bytes())
    payload.unlink()
    payload.symlink_to(same_bytes)

    result = installer.verify_source(copied_root)

    assert result["ok"] is False
    assert "extractor/README.md" in result["symlinks"]


def test_verify_installed_rejects_executable_mode_drift(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )
    active_plist = launch_agents / "com.mastermindx.research-trickle.plist"
    active_plist.chmod(0o644)

    readback = installer.verify_installed(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
    )

    assert readback["ok"] is False
    assert str(active_plist) in readback["mode_mismatched"]


def test_install_refuses_symlinked_runtime_root(tmp_path: Path) -> None:
    installer = _load_installer()
    actual_runtime = tmp_path / "actual-runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(actual_runtime, feed_script, launch_agents)
    runtime_link = tmp_path / "runtime-link"
    runtime_link.symlink_to(actual_runtime, target_is_directory=True)

    with pytest.raises(RuntimeError, match="runtime root.*symlink"):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=runtime_link,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
            backup_dir=backup_dir,
        )

    assert not backup_dir.exists()
    assert (actual_runtime / "src" / "stale.py").read_text() == "stale source\n"


def test_install_refuses_symlinked_ancestor(tmp_path: Path) -> None:
    installer = _load_installer()
    actual_parent = tmp_path / "actual-parent"
    actual_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(actual_parent, target_is_directory=True)
    runtime_root = linked_parent / "runtime"

    with pytest.raises(RuntimeError, match="runtime root.*symlink"):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=runtime_root,
            feed_script=tmp_path / "feed.sh",
            launch_agents_dir=tmp_path / "LaunchAgents",
            backup_dir=tmp_path / "backup",
        )

    assert not (tmp_path / "backup").exists()


def test_install_refuses_symlinked_managed_directory_before_backup(
    tmp_path: Path,
) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    shutil.rmtree(runtime_root / "src")
    outside = tmp_path / "outside-src"
    outside.mkdir()
    (outside / "untouched.py").write_text("outside\n")
    (runtime_root / "src").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RuntimeError, match="managed source directory.*symlink"):
        installer.install(
            source_root=CANONICAL_ROOT,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
            backup_dir=backup_dir,
        )

    assert not backup_dir.exists()
    assert (outside / "untouched.py").read_text() == "outside\n"


def test_rollback_refuses_destination_outside_recorded_roots(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )

    receipt_path = backup_dir / installer.ROLLBACK_RECEIPT
    receipt = json.loads(receipt_path.read_text())
    receipt["entries"][0]["destination"] = str(tmp_path / "escape.txt")
    receipt_path.write_text(json.dumps(receipt))

    with pytest.raises(ValueError, match="outside managed source-owned destinations"):
        installer.rollback(
            backup_dir=backup_dir,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
        )

    assert not (tmp_path / "escape.txt").exists()


def test_rollback_refuses_tampered_backup_payload(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )

    receipt = json.loads((backup_dir / installer.ROLLBACK_RECEIPT).read_text())
    entry = next(item for item in receipt["entries"] if item.get("backup"))
    (backup_dir / entry["backup"]).write_text("tampered backup\n")

    with pytest.raises(RuntimeError, match="backup hash mismatch"):
        installer.rollback(
            backup_dir=backup_dir,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
        )

    assert (runtime_root / "README.md").read_text() != "old readme\n"


def test_rollback_refuses_runtime_state_inside_recorded_root(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )

    receipt_path = backup_dir / installer.ROLLBACK_RECEIPT
    receipt = json.loads(receipt_path.read_text())
    receipt["entries"].append(
        {
            "destination": str(runtime_root / ".env"),
            "existed": False,
            "backup": None,
            "backup_sha256": None,
            "backup_mode": None,
        }
    )
    receipt_path.write_text(json.dumps(receipt))

    with pytest.raises(ValueError, match="outside managed source-owned destinations"):
        installer.rollback(
            backup_dir=backup_dir,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
        )

    assert (runtime_root / ".env").read_text() == "KEEP_SECRET=1\n"


def test_rollback_refuses_receipt_root_rewrite(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "runtime"
    feed_script = tmp_path / "feed.sh"
    launch_agents = tmp_path / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)
    installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )

    receipt_path = backup_dir / installer.ROLLBACK_RECEIPT
    receipt = json.loads(receipt_path.read_text())
    receipt["runtime_root"] = str(tmp_path / "forged-runtime")
    receipt_path.write_text(json.dumps(receipt))

    with pytest.raises(ValueError, match="runtime_root does not match requested destination"):
        installer.rollback(
            backup_dir=backup_dir,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents,
        )

    assert (runtime_root / ".env").read_text() == "KEEP_SECRET=1\n"


def test_release_receipt_preserves_recovery_anchor_and_current_manifest() -> None:
    recovery_manifest = CANONICAL_ROOT / "RECOVERY_SHA256SUMS"
    release_receipt_path = CANONICAL_ROOT / "RELEASE_RECEIPT.json"
    import_receipt = json.loads((CANONICAL_ROOT / "IMPORT_RECEIPT.json").read_text())
    release_receipt = json.loads(release_receipt_path.read_text())

    assert hashlib.sha256(recovery_manifest.read_bytes()).hexdigest() == (
        "6209be070fbdfe8b8269bb62c0b6f466dac9b425ba1e9244b9b1bf7d983ba602"
    )
    assert import_receipt["source_packet"]["manifest"] == "RECOVERY_SHA256SUMS"
    assert import_receipt["source_packet"]["manifest_sha256"] == (
        "6209be070fbdfe8b8269bb62c0b6f466dac9b425ba1e9244b9b1bf7d983ba602"
    )
    assert import_receipt["import_commit"] == (
        "31981dc66e9a37419b5b7a6aecfde28808785d03"
    )
    assert release_receipt["schema"] == "mastermind.marketdesk_extractor.release.v1"
    assert release_receipt["manifest"] == "SHA256SUMS"
    assert release_receipt["payload_count"] == 58
    assert release_receipt["recovery_manifest"] == "RECOVERY_SHA256SUMS"
    assert release_receipt["recovery_manifest_sha256"] == (
        "6209be070fbdfe8b8269bb62c0b6f466dac9b425ba1e9244b9b1bf7d983ba602"
    )
    assert release_receipt["manifest_sha256"] == hashlib.sha256(
        (CANONICAL_ROOT / "SHA256SUMS").read_bytes()
    ).hexdigest()


def test_install_retires_separate_feed_carrier(tmp_path: Path) -> None:
    installer = _load_installer()
    runtime_root = tmp_path / "mastermind-research" / "marketdesk_paper_extractor"
    feed_script = tmp_path / "mastermind-research" / "feed.sh"
    launch_agents = tmp_path / "Library" / "LaunchAgents"
    backup_dir = tmp_path / "backup"
    _seed_runtime_state(runtime_root, feed_script, launch_agents)

    receipt = installer.install(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
        backup_dir=backup_dir,
    )

    assert receipt["retired"] == [
        str(feed_script),
        str(launch_agents / "com.mastermindx.research-feed.plist"),
    ]
    assert not feed_script.exists()
    assert not (launch_agents / "com.mastermindx.research-feed.plist").exists()
    assert (launch_agents / "com.mastermindx.research-trickle.plist").is_file()
    readback = installer.verify_installed(
        source_root=CANONICAL_ROOT,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
    )
    assert readback["ok"] is True
    assert readback["retired_present"] == []

    installer.rollback(
        backup_dir=backup_dir,
        runtime_root=runtime_root,
        feed_script=feed_script,
        launch_agents_dir=launch_agents,
    )
    assert feed_script.read_text() == "old feed\n"
    assert (
        launch_agents / "com.mastermindx.research-feed.plist"
    ).read_text() == "old feed plist\n"
