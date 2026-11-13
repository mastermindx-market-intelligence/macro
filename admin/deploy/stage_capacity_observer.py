"""Stage an observer overlay, preserving the incumbent router release byte for byte.

This is a one-shot deployment preparation tool. It does not change launchd, start
services, load credentials, edit the primary checkout, or operate a controller.
Activation belongs to the existing launchd job under its existing reload lock.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()



def native_writer_candidate(name, source, helper):
    """Adapt the installed writer without changing any of its policy transforms."""
    loader = ("import importlib.util as _capacity_importlib\n"
              + "_capacity_spec = _capacity_importlib.spec_from_file_location('capacity_configuration_writer', " + repr(str(helper)) + ")\n"
              + "_capacity_writer = _capacity_importlib.module_from_spec(_capacity_spec)\n"
              + "_capacity_spec.loader.exec_module(_capacity_writer)\n")
    if "BEGIN CAPACITY_CONFIGURATION_WRITER" in source:
        # Re-enrollment only updates the exact shared helper path, retaining the
        # already-qualified wrapper and every independently advanced policy byte.
        pattern = r"(?m)^_capacity_spec = _capacity_importlib.spec_from_file_location\('capacity_configuration_writer', .+\)$"
        replacement = "_capacity_spec = _capacity_importlib.spec_from_file_location('capacity_configuration_writer', " + repr(str(helper)) + ")"
        result, count = re.subn(pattern, lambda match: replacement, source)
        if count != 1:
            raise ValueError("installed writer wrapper changed")
        return result
    if name == "model_exclusivity_guard.py":
        needle = "def guard_routes() -> None:"
        if source.count(needle) != 1:
            raise ValueError("guard writer contract changed")
        wrapper = ("# BEGIN CAPACITY_CONFIGURATION_WRITER\n" + loader
            + "def guard_routes() -> None:\n"
            + "    try:\n"
            + "        with _capacity_writer.configuration_writer(ROUTES_JSON):\n"
            + "            return _capacity_unlocked_guard_routes()\n"
            + "    except (_capacity_writer.WriterBusy, _capacity_writer.PendingConfiguration):\n"
            + "        log('configuration transaction held; native policy left unchanged')\n"
            + "# END CAPACITY_CONFIGURATION_WRITER\n\n"
            + "def _capacity_unlocked_guard_routes() -> None:")
        result = source.replace(needle, wrapper)
        ast.parse(result)
        return result
    if name == "peak_router.sh":
        needle = "p = pathlib.Path(path)\n"
        if source.count(needle) != 1:
            raise ValueError("peak writer contract changed")
        block = (needle + "# BEGIN CAPACITY_CONFIGURATION_WRITER\n" + loader
            + "import atexit as _capacity_atexit, os as _capacity_os\n"
            + "try:\n"
            + "    _capacity_fd = _capacity_writer.acquire_writer(p)\n"
            + "except (_capacity_writer.WriterBusy, _capacity_writer.PendingConfiguration):\n"
            + "    print('HELD')\n"
            + "    raise SystemExit(0)\n"
            + "_capacity_atexit.register(_capacity_os.close, _capacity_fd)\n"
            + "# END CAPACITY_CONFIGURATION_WRITER\n")
        result = source.replace(needle, block)
        needle = '  log "reload: $OUT"\nelse\n'
        if result.count(needle) != 1:
            raise ValueError("peak reload outcome contract changed")
        return result.replace(needle, '  log "reload: $OUT"\nelif [[ "$CLEAN" == "HELD" ]]; then\n  log "configuration transaction held; native policy left unchanged"\n  exit 0\nelse\n')
    raise ValueError("unsupported native writer")


def native_maintenance_candidate(name, source):
    """Fence an unfinished attended transaction inside the existing owners."""
    marker = "CAPACITY_ATTENDED_MAINTENANCE"
    if marker in source:
        return source
    if name == "reload.sh":
        needle = 'if ! mkdir "$LOCK" 2>/dev/null; then\n'
        block = ('  # CAPACITY_ATTENDED_MAINTENANCE: elapsed time cannot resolve effects.\n'
                 '  if [[ -e "$LOCK/maintenance.json" ]]; then\n'
                 '    log "attended maintenance requires its owner to reconcile; reload held"\n'
                 '    print "held (attended maintenance)"\n'
                 '    exit 0\n'
                 '  fi\n')
    elif name == "watchdog.sh":
        needle = '  if [[ -d "$STATE_DIR/reload.lock" ]]; then\n'
        block = ('    # CAPACITY_ATTENDED_MAINTENANCE: never kill a known draining generation.\n'
                 '    if [[ "$label" == "ai.mastermind.fabric-router" && -e "$STATE_DIR/reload.lock/maintenance.json" ]]; then\n'
                 '      log "$label attended maintenance awaiting owner reconciliation — standing down"\n'
                 '      return 0\n'
                 '    fi\n')
    elif name == "service.py":
        guard = r'''# BEGIN CAPACITY_ATTENDED_MAINTENANCE

def _capacity_startup_held():
    """A retiring release cannot reopen admission during attended maintenance."""
    import json as _capacity_json
    import os as _capacity_os
    import stat as _capacity_stat
    from pathlib import Path as _CapacityPath
    marker = _CapacityPath.home() / ".local/share/mastermind/fabric-router/state/reload.lock/maintenance.json"
    fd = None
    try:
        try:
            fd = _capacity_os.open(marker, _capacity_os.O_RDONLY | _capacity_os.O_NOFOLLOW | _capacity_os.O_NONBLOCK)
        except FileNotFoundError:
            return False
        meta = _capacity_os.fstat(fd)
        if not _capacity_stat.S_ISREG(meta.st_mode) or meta.st_uid != _capacity_os.geteuid() or meta.st_nlink != 1 or not 0 < meta.st_size <= 65536:
            return True
        receipt = _capacity_json.loads(_capacity_os.read(fd, 65537))
        if receipt.get("schema") != "mastermind.capacity_router.maintenance.v1":
            return True
        release = str(_CapacityPath(__file__).resolve().parents[3])
        held = receipt.get("base_release") == release and receipt.get("phase") not in {"COMPLETED", "ROLLED_BACK"}
        if held:
            print(_capacity_json.dumps({"capacity_maintenance_startup_held": True, "pid": _capacity_os.getpid(), "release": release, "operation_id": receipt.get("operation_id")}), flush=True)
        return held
    except (OSError, ValueError, TypeError, AttributeError):
        return True
    finally:
        if fd is not None:
            _capacity_os.close(fd)

# END CAPACITY_ATTENDED_MAINTENANCE

'''
        lines = source.splitlines(keepends=True)
        functions = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "main"]
        if len(functions) != 1:
            raise ValueError("native service entry contract changed")
        main = functions[0]
        lines.insert(main.body[0].lineno - 1, "    if _capacity_startup_held():\n        return\n")
        lines.insert(main.lineno - 1, guard)
        result = "".join(lines)
        ast.parse(result)
        return result
    else:
        raise ValueError("unsupported maintenance owner")
    if source.count(needle) != 1:
        raise ValueError("native maintenance owner contract changed")
    return source.replace(needle, needle + block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--expected-release", type=Path, required=True)
    parser.add_argument("--expected-plist-sha256", required=True)
    parser.add_argument("--expected-gateway-sha256", required=True)
    parser.add_argument("--prepare-controls", action="store_true", help="Prepare shared native writer adapters; activation remains a separate exact-preimage effect")
    parser.add_argument("--prepare-maintenance", action="store_true", help="Prepare the incumbent owners for a serial attended drain; no activation")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}", args.commit):
        raise SystemExit("full source commit required")
    root = Path.home() / ".local/share/mastermind/fabric-router"
    plist = Path.home() / "Library/LaunchAgents/ai.mastermind.fabric-router.plist"
    raw = plist.read_bytes()
    config = plistlib.loads(raw)
    base = Path(config["WorkingDirectory"])
    package = Path("ops/native_fabric/unified_router")
    if base != args.expected_release or digest(plist) != args.expected_plist_sha256:
        raise SystemExit("incumbent launchd definition changed; reconcile first")
    if digest(base / package / "gateway.py") != args.expected_gateway_sha256:
        raise SystemExit("incumbent gateway changed; reconcile first")
    if base.parent != root / "releases" or base.is_symlink():
        raise SystemExit("unexpected incumbent release location")
    if (root / "state/reload.lock").exists():
        raise SystemExit("incumbent reload is active; do not displace it")
    target = root / "releases" / (base.name + "-obs-" + args.commit[:12])
    if target.exists():
        raise SystemExit("staged generation already exists; inspect its receipt")
    originals = {}
    ops_root = base / "ops"
    for source in sorted(ops_root.rglob("*")):
        # Prune on the path RELATIVE to the scan root. `source.parts` is absolute,
        # so a `__pycache__` component anywhere above `base` (a worktree or temp
        # directory named that way) would silently skip every file in the tree.
        if "__pycache__" in source.relative_to(ops_root).parts or source.suffix == ".pyc":
            continue
        if source.is_symlink():
            raise SystemExit("source release contains a symlink; reconcile before copying")
        if source.is_file():
            originals[str(source.relative_to(base))] = digest(source)
    target.mkdir(mode=0o700)
    shutil.copytree(base / "ops", target / "ops", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for extra in ("pyproject.toml", "setup.py", "setup.cfg", "SOURCE.json"):
        if (base / extra).is_file():
            shutil.copy2(base / extra, target / extra)
    for rel, expected in originals.items():
        if digest(target / rel) != expected:
            raise SystemExit("copied source does not match incumbent")
    service = target / package / "service.py"
    original = service.read_text()
    old = "ops.native_fabric.unified_router.gateway:create_app"
    new = "ops.native_fabric.unified_router.capacity_fabric_observer:create_app"
    if original.count(old) == 1:
        service.write_text(original.replace(old, new))
    elif original.count("from ops.native_fabric.unified_router.capacity_fabric_observer import create_app") != 1:
        raise SystemExit("service factory contract changed")
    if args.prepare_maintenance:
        service.write_text(native_maintenance_candidate("service.py", service.read_text()))
    owned = {}
    for name in ("capacity_fabric_observer.py", "capacity_fabric_schema.py",
                 "capacity_control_owner.py", "capacity_config_transaction.py"):
        source = args.source_dir / "admin" / name
        ast.parse(source.read_text())
        shutil.copy2(source, target / package / name)
        owned[str(package / name)] = digest(target / package / name)
    owned[str(package / "service.py")] = digest(service)
    config_path = target / package / "observatory-export.json"
    export_config = json.loads(config_path.read_text()) if config_path.is_file() else {"ssh_alias": "vps-mmx"}
    if not isinstance(export_config, dict):
        raise SystemExit("incumbent observation configuration changed")
    writer_patches = []
    if args.prepare_controls:
        patch_root = target / "capacity-writer-patches"
        patch_root.mkdir(mode=0o700)
        for name in ("model_exclusivity_guard.py", "peak_router.sh"):
            current = root / name
            if current.is_symlink() or not current.is_file():
                raise SystemExit("native writer is not a regular installed file")
            before = current.read_text()
            candidate = native_writer_candidate(name, before, target / package / "capacity_config_transaction.py")
            prepared = patch_root / name
            prepared.write_text(candidate)
            prepared.chmod(current.stat().st_mode & 0o777)
            writer_patches.append({"path": str(current), "before_sha256": digest(current),
                                   "sha256": digest(prepared), "candidate": str(prepared)})
        export_config["control_writers"] = [{"path": r["path"], "sha256": r["sha256"]} for r in writer_patches]
        export_config["controls_enabled"] = True
    maintenance_patches = []
    if args.prepare_maintenance:
        patch_root = target / "capacity-maintenance-patches"
        patch_root.mkdir(mode=0o700)
        for name in ("reload.sh", "watchdog.sh"):
            current = root / name
            if current.is_symlink() or not current.is_file():
                raise SystemExit("native maintenance owner is not a regular installed file")
            prepared = patch_root / name
            prepared.write_text(native_maintenance_candidate(name, current.read_text()))
            prepared.chmod(current.stat().st_mode & 0o777)
            maintenance_patches.append({"path": str(current), "before_sha256": digest(current),
                                        "sha256": digest(prepared), "candidate": str(prepared)})
    config_path.write_text(json.dumps(export_config, indent=2) + "\n")
    config_path.chmod(0o600)
    owned[str(config_path.relative_to(target))] = digest(config_path)
    manifest_path = target / "SOURCE.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        if isinstance(manifest.get("runtime_files"), dict):
            manifest["runtime_files"].update(owned)
            manifest["capacity_observer"] = {"repository": "mastermindx-market-intelligence/macro", "commit": args.commit}
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            owned["SOURCE.json"] = digest(manifest_path)
    receipt = {"source_repository": "mastermindx-market-intelligence/macro", "source_commit": args.commit,
        "native_writer_patches": writer_patches, "maintenance_patches": maintenance_patches,
        "maintenance_startup_guard": args.prepare_maintenance,
        "staged_at": time.time(), "base_release": str(base), "release": str(target),
        "original_plist_sha256": hashlib.sha256(raw).hexdigest(),
        "base_gateway_sha256": args.expected_gateway_sha256, "preserved_files": originals,
        "overlay_files": owned, "state": "STAGED_NOT_ACTIVE",
        "activation": "Existing ai.mastermind.fabric-router launchd job; existing state/reload.lock; health and snapshot proof required"}
    (target / "CAPACITY_OBSERVER_SOURCE.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "release": str(target), "commit": args.commit,
                      "preserved_files": len(originals), "overlay_files": owned}))


if __name__ == "__main__":
    main()
