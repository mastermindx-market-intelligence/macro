"""Materialize a Cboe sample qualification on the mounted 4 TB external disk.

Never downloads, publishes, triggers a live pipeline, or writes to Git/R2/Terminal.
Call from the macro repo root with python3 -m scripts.qualify_options_free_samples.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import stat
import subprocess
from pathlib import Path

from collectors.options_free_samples import SourceRejected, qualify_cboe_c1_sample


# Private Cboe evaluation bytes are anchored to the identified, physical 4 TB
# external APFS volume. Do not fall back to the main SSD when it is unplugged.
EXTERNAL_VOLUME = Path("/Volumes/Mastermind")
EXTERNAL_PRIVATE_ROOT = EXTERNAL_VOLUME / ".mastermind_private" / "options_free_trials_20261008"
EXTERNAL_VOLUME_UUID = "7EE5D196-8BB6-4E6D-B1D7-AFEA5DEB172A"
EXTERNAL_VOLUME_BYTES = 4_000_577_273_856


def _check_volume(info: dict, *, mounted_device: int, system_device: int) -> None:
    """Refuse an unmounted folder, a renamed disk, or a different same-name disk."""
    if (info.get("VolumeUUID") != EXTERNAL_VOLUME_UUID
            or info.get("MountPoint") != str(EXTERNAL_VOLUME)
            or info.get("TotalSize") != EXTERNAL_VOLUME_BYTES
            or mounted_device == system_device):
        raise SourceRejected("specified 4 TB Mastermind external volume is not mounted/identical")


def _checked_root(candidate: Path) -> Path:
    try:
        root = candidate.resolve(strict=True)
        expected = EXTERNAL_PRIVATE_ROOT.resolve(strict=True)
        mounted = EXTERNAL_VOLUME.resolve(strict=True)
        if root != expected or root == mounted or root.is_symlink():
            raise SourceRejected("qualification requires the exact external private Cboe root")
        with subprocess.Popen(
            ["/usr/sbin/diskutil", "info", "-plist", str(mounted)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ) as process:
            data = process.communicate(timeout=8)[0]
            if process.returncode != 0:
                raise SourceRejected("cannot establish 4 TB external volume identity")
        info = plistlib.loads(data)
        _check_volume(
            info, mounted_device=mounted.stat().st_dev,
            system_device=Path("/").stat().st_dev,
        )
        if root.stat().st_dev != mounted.stat().st_dev:
            raise SourceRejected("source root is not physically on the 4 TB external disk")
        private_parent = mounted / ".mastermind_private"
        for path in (private_parent, root):
            st = path.stat()
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
                    or st.st_mode & 0o077):
                raise SourceRejected("external private directory owner/permissions unsafe")
        return root
    except SourceRejected:
        raise
    except (OSError, ValueError, plistlib.InvalidFileException,
            subprocess.TimeoutExpired) as exc:
        raise SourceRejected("external drive not ready; refusing internal fallback") from exc


def qualify(root: Path, *, persist: bool = False) -> dict:
    root = _checked_root(root)
    receipt_path = root / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    filename = receipt.get("file")
    if filename != "cboe_c1_openclose_public_eval_2025-03-28_outer.zip":
        raise SourceRejected("unexpected archive name in acquisition receipt")
    archive = root / filename
    if archive.is_symlink() or receipt_path.is_symlink():
        raise SourceRejected("linked source inputs prohibited")
    if archive.stat().st_uid != os.getuid():
        raise SourceRejected("source archive ownership mismatch")
    report = qualify_cboe_c1_sample(archive.read_bytes(), receipt)
    if persist:
        out = root / "qualified_cboe_c1_sample.json"
        content = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if out.exists():
            if out.read_bytes() != content:
                raise SourceRejected("existing qualification differs; do not overwrite")
        else:
            fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            if out.stat().st_mode & 0o077:
                raise SourceRejected("qualification report not private")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-root", required=True, type=Path)
    ap.add_argument("--persist-private", action="store_true")
    args = ap.parse_args()
    report = qualify(args.private_root, persist=args.persist_private)
    print(json.dumps({
        "schema": report["schema"],
        "sample_session": report["effective_trade_session"],
        "rows_total": report["rows_total"],
        "rows_standard": report["rows_standard"],
        "underlyings_standard": report["underlyings_standard"],
        "rights": report["rights"],
        "persisted": args.persist_private,
        "publish": False,
        "signal_authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
