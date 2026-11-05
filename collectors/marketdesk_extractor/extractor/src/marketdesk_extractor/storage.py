"""Fail-closed storage guard for removable/external production volumes."""
from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DISKUTIL_TIMEOUT_SECONDS = 10.0


class StorageGuardError(RuntimeError):
    """The configured durable storage is absent, wrong, read-only, or too full."""


@dataclass(frozen=True)
class VolumeInfo:
    mount_point: Path
    volume_uuid: str
    external: bool
    writable: bool
    free_bytes: int
    total_bytes: int


@dataclass(frozen=True)
class StorageStatus:
    volume: Path
    root: Path
    volume_uuid: str
    free_bytes: int
    total_bytes: int
    min_free_bytes: int

    @property
    def free_gib(self) -> float:
        return self.free_bytes / (1024 ** 3)

    @property
    def total_gib(self) -> float:
        return self.total_bytes / (1024 ** 3)

    def describe(self) -> str:
        return (
            f"external storage ready: root={self.root} volume={self.volume} "
            f"uuid={self.volume_uuid or 'unavailable'} "
            f"free={self.free_gib:.1f}GiB/{self.total_gib:.1f}GiB "
            f"floor={self.min_free_bytes / (1024 ** 3):.1f}GiB"
        )


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def inspect_volume(volume: str | Path) -> VolumeInfo:
    """Inspect a mounted volume without ever creating its mount point."""
    mount = _resolved(volume)
    if not mount.is_dir():
        raise StorageGuardError(f"required storage volume is not mounted: {mount}")

    try:
        mount_dev = mount.stat().st_dev
        parent_dev = mount.parent.stat().st_dev
    except OSError as exc:
        raise StorageGuardError(f"cannot stat storage volume {mount}: {exc}") from exc
    if mount_dev == parent_dev:
        raise StorageGuardError(
            f"storage path is not a distinct mounted volume: {mount}"
        )

    volume_uuid = ""
    external = True
    writable = os.access(mount, os.W_OK)
    if sys.platform == "darwin":
        diskutil = Path("/usr/sbin/diskutil")
        if not diskutil.exists():
            raise StorageGuardError("/usr/sbin/diskutil is missing; cannot verify volume")
        try:
            proc = subprocess.run(
                [str(diskutil), "info", "-plist", str(mount)],
                check=True,
                capture_output=True,
                timeout=DISKUTIL_TIMEOUT_SECONDS,
            )
            info = plistlib.loads(proc.stdout)
        except subprocess.TimeoutExpired as exc:
            raise StorageGuardError(
                f"timed out inspecting storage volume {mount} after "
                f"{DISKUTIL_TIMEOUT_SECONDS:g}s"
            ) from exc
        except (OSError, subprocess.CalledProcessError, plistlib.InvalidFileException) as exc:
            raise StorageGuardError(f"cannot inspect storage volume {mount}: {exc}") from exc
        actual_mount = _resolved(info.get("MountPoint", ""))
        if actual_mount != mount:
            raise StorageGuardError(
                f"storage mount mismatch: expected {mount}, diskutil reports {actual_mount}"
            )
        volume_uuid = str(info.get("VolumeUUID", "")).strip().upper()
        external = not bool(info.get("Internal", True))
        writable = bool(info.get("Writable", False)) and writable

    usage = shutil.disk_usage(mount)
    return VolumeInfo(
        mount_point=mount,
        volume_uuid=volume_uuid,
        external=external,
        writable=writable,
        free_bytes=usage.free,
        total_bytes=usage.total,
    )


def check_storage(
    *,
    volume: str | Path,
    root: str | Path,
    managed_paths: Iterable[str | Path],
    required_volume_uuid: str = "",
    min_free_gib: int = 0,
    extra_required_bytes: int = 0,
) -> StorageStatus:
    """Verify exact external-volume identity, containment, writability, and space."""
    volume_path = _resolved(volume)
    root_path = _resolved(root)
    if not _contains(volume_path, root_path):
        raise StorageGuardError(
            f"storage root {root_path} is outside required volume {volume_path}"
        )
    if not root_path.is_dir():
        raise StorageGuardError(
            f"storage root is missing (refusing to create a fallback): {root_path}"
        )

    for raw_path in managed_paths:
        path = _resolved(raw_path)
        if not _contains(root_path, path):
            raise StorageGuardError(
                f"managed path escapes storage root {root_path}: {path}"
            )

    info = inspect_volume(volume_path)
    expected_uuid = required_volume_uuid.strip().upper()
    if expected_uuid and info.volume_uuid != expected_uuid:
        raise StorageGuardError(
            f"wrong storage volume at {volume_path}: expected UUID "
            f"{expected_uuid}, got {info.volume_uuid or 'unavailable'}"
        )
    if not info.external:
        raise StorageGuardError(f"required storage is not external: {volume_path}")
    if not info.writable or not os.access(root_path, os.W_OK):
        raise StorageGuardError(f"required storage is not writable: {root_path}")

    min_free_bytes = max(0, min_free_gib) * (1024 ** 3)
    needed = min_free_bytes + max(0, extra_required_bytes)
    if info.free_bytes < needed:
        raise StorageGuardError(
            f"storage safety floor reached on {volume_path}: "
            f"free={info.free_bytes / (1024 ** 3):.1f}GiB, "
            f"required={needed / (1024 ** 3):.1f}GiB"
        )

    return StorageStatus(
        volume=volume_path,
        root=root_path,
        volume_uuid=info.volume_uuid,
        free_bytes=info.free_bytes,
        total_bytes=info.total_bytes,
        min_free_bytes=min_free_bytes,
    )
