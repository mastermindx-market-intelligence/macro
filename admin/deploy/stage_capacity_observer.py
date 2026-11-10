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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--expected-release", type=Path, required=True)
    parser.add_argument("--expected-plist-sha256", required=True)
    parser.add_argument("--expected-gateway-sha256", required=True)
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
    if original.count(old) != 1:
        raise SystemExit("service factory contract changed")
    service.write_text(original.replace(old, new))
    owned = {}
    for name in ("capacity_fabric_observer.py", "capacity_fabric_schema.py"):
        source = args.source_dir / "admin" / name
        ast.parse(source.read_text())
        shutil.copy2(source, target / package / name)
        owned[str(package / name)] = digest(target / package / name)
    owned[str(package / "service.py")] = digest(service)
    config_path = target / package / "observatory-export.json"
    config_path.write_text(json.dumps({"ssh_alias": "vps-mmx"}) + "\n")
    config_path.chmod(0o600)
    owned[str(config_path.relative_to(target))] = digest(config_path)
    receipt = {"source_repository": "mastermindx-market-intelligence/macro", "source_commit": args.commit,
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
