"""One bounded post-close BOATS capture, private bundle and history selection.

The provisioned state directory contains current.json pointing to the last
accepted local manifest. A kernel lock owns this whole cycle; a permanent
session directory prevents replay after interruption. The current local
selection advances only after the existing private SSH publisher confirms
selection of that exact version. This module never installs a schedule.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.publish_boats_history import MAX_FILE, MAX_TOTAL, REMOTE_BASE, encode, publish_bundle, validate_manifest, validate_ssh_binding, _private_write
from scripts.refresh_boats_history import RefreshConfig, RefreshDeps, _read_regular, run_refresh, is_nyse_session
from scripts.run_boats_session import validate_host_timezone, MIN_ARCHIVE_FREE_BYTES


@dataclass(frozen=True)
class CycleConfig:
    state_dir: Path
    archive_root: Path
    ssh_target: str
    ssh_key: Path
    max_requests: int
    max_total_bytes: int
    max_response_bytes: int = 1024**2
    scheduled: bool = False


def private_directory(path: Path) -> None:
    info = path.lstat()
    if (not path.is_absolute() or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("private owned absolute directory required")


def require_cycle_space(path: Path, capture_bytes: int) -> None:
    # Reserve the maximum bounded new data copy + tar, capture staging and the
    # archive's operating floor. Retained prior versions are never deleted by
    # the collector; low space refuses before creating a session or fetching.
    required = MIN_ARCHIVE_FREE_BYTES + 2 * MAX_TOTAL + 2 * capture_bytes + 32 * 1024**2
    if shutil.disk_usage(path).free < required:
        raise ValueError("insufficient private cycle staging space before capture")


def build_bundle(manifest: dict, baseline_dir: Path, refresh_dir: Path, output: Path) -> tuple[Path, Path]:
    """Copy only hash-qualified files into a new private, self-contained version."""
    for directory in (baseline_dir, refresh_dir, output): private_directory(directory)
    data = output/"data"
    data.mkdir(mode=0o700)
    manifest = dict(manifest, local_directory=str(data), activated=False)
    version = Path(manifest["directory"]).name
    validate_manifest(manifest, version)
    for item in manifest["files"]:
        origin = item.get("origin")
        if origin not in {"baseline", "refresh"}:
            raise ValueError("file copy origin required")
        root = baseline_dir if origin == "baseline" else refresh_dir
        raw = _read_regular(root/item["name"], MAX_FILE)
        if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("history file differs from accepted manifest")
        _private_write(data/item["name"], raw)
    mp, ap = output/"manifest.json", output/"history.tar"
    _private_write(mp, encode(manifest))
    fd = os.open(ap, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w+b") as stream:
        with tarfile.open(fileobj=stream, mode="w") as archive:
            # Explicit entries avoid filesystem-derived owners, path prefixes and symlinks.
            for name, source in [(".delivery-manifest.json", mp), *[(x["name"], data/x["name"]) for x in manifest["files"]]]:
                raw = _read_regular(source, 8*1024**2 if name == ".delivery-manifest.json" else MAX_FILE)
                entry = tarfile.TarInfo(name)
                entry.size, entry.mode = len(raw), 0o600
                archive.addfile(entry, io.BytesIO(raw))
        stream.flush()
        os.fsync(stream.fileno())
    return mp, ap


def run_cycle(config: CycleConfig, *, now: datetime | None = None,
              refresh=run_refresh, publish=publish_bundle, assemble=None,
              host_check=validate_host_timezone, session_check=is_nyse_session) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("aware clock required")
    host_check(now)
    local = now.astimezone(ZoneInfo("America/New_York"))
    session = local.date().isoformat()
    if not session_check(session):
        return {"status":"closed_calendar", "session":session, "provider_requests":0}
    if config.scheduled and local.hour != 4:
        return {"status":"scheduled_candidate_not_due", "session":session, "provider_requests":0}
    if not 4 <= local.hour < 12:
        raise ValueError("post-close cycle requires 04:00 through 11:59 ET")
    if (type(config.max_requests) is not int or not 1 <= config.max_requests <= 20000
            or type(config.max_total_bytes) is not int or not 1 <= config.max_total_bytes <= 1024**3
            or type(config.max_response_bytes) is not int or not 1 <= config.max_response_bytes <= 1024**2):
        raise ValueError("explicit finite capture budgets required")
    private_directory(config.state_dir)
    validate_ssh_binding(config.ssh_target, config.ssh_key)
    require_cycle_space(config.state_dir, config.max_total_bytes)
    lock = os.open(config.state_dir/".cycle.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pointer = config.state_dir/"current.json"
        selected_raw = _read_regular(pointer, 4096)
        selected = json.loads(selected_raw)
        if set(selected) != {"manifest_path"} or not isinstance(selected["manifest_path"], str):
            raise ValueError("invalid local selection")
        baseline_path = Path(selected["manifest_path"])
        if not baseline_path.is_absolute():
            raise ValueError("absolute baseline manifest required")
        baseline = json.loads(_read_regular(baseline_path, 8*1024**2))
        predecessor = Path(baseline["directory"]).name
        validate_manifest(baseline, predecessor)
        prior_dir = Path(baseline["local_directory"])
        private_directory(prior_dir)
        symbols = sorted([x["name"][:-5] for x in baseline["files"]] + baseline["vendor_empty_symbols"])
        if len(set(symbols)) != len(symbols) or not symbols or len(symbols) > config.max_requests:
            raise ValueError("capture coverage exceeds explicit budget")
        if assemble is None:
            from scripts.boats_history_delivery import assemble_delivery
            assemble = assemble_delivery
        # Validate the complete baseline partition before any provider effect.
        assemble(baseline, {"status":"complete", "symbols":[], "outputs":[], "unavailable":[], "not_requested":[]})
        operation = config.state_dir/("session-"+session)
        operation.mkdir(mode=0o700)  # permanent, including on capture or publication failure
        directory = os.open(config.state_dir, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        _private_write(operation/"cycle-start.json", encode({"session":session,
            "started_at_utc":now.isoformat(), "previous_manifest":str(baseline_path),
            "previous_selection_sha256":hashlib.sha256(selected_raw).hexdigest(),
            "max_requests":config.max_requests, "max_total_bytes":config.max_total_bytes}))
        symbol_path = operation/"symbols.txt"
        _private_write(symbol_path, ("\n".join(symbols)+"\n").encode())
        refresh_dir = operation/"refresh"
        dependencies = RefreshDeps()
        fetch = dependencies.fetch
        deadline = time.monotonic() + 7200
        def bounded_fetch(*args, **kwargs):
            if time.monotonic() >= deadline:
                raise RuntimeError("post-close provider time budget exhausted")
            return fetch(*args, **kwargs)
        dependencies.fetch = bounded_fetch
        refreshed, code = refresh(RefreshConfig(session=session, symbols_path=symbol_path,
            history_dir=prior_dir, output_dir=refresh_dir, root=config.archive_root, capture=True,
            max_requests=config.max_requests, max_total_bytes=config.max_total_bytes,
            max_response_bytes=config.max_response_bytes), dependencies)
        if code != 0:
            raise RuntimeError("capture incomplete; preserve this session and reconcile its receipts")
        assembled = assemble(baseline, refreshed)
        version = "session-"+session
        assembled.update(directory=REMOTE_BASE+"/"+version, completed_window_session=session)
        bundle_dir = operation/"bundle"
        bundle_dir.mkdir(mode=0o700)
        mp, ap = build_bundle(assembled, prior_dir, refresh_dir, bundle_dir)
        if _read_regular(pointer, 4096) != selected_raw:
            raise RuntimeError("local selection changed before publication")
        receipt = publish(mp, ap, operation, version, predecessor, config.ssh_target, config.ssh_key)
        if _read_regular(pointer, 4096) != selected_raw:
            raise RuntimeError("remote selected but local custody changed; reconcile original operation")
        temporary = config.state_dir/(".current-"+session+".json")
        _private_write(temporary, encode({"manifest_path":str(mp)}))
        os.replace(temporary, pointer)
        fd = os.open(config.state_dir, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
        result = {"status":"selected", "session":session, "manifest_path":str(mp),
                  "selection":receipt, "complete_history":False}
        _private_write(operation/"cycle-result.json", encode(result))
        return result
    finally:
        os.close(lock)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("state-dir", "archive-root", "ssh-key"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--ssh-target", required=True)
    parser.add_argument("--max-requests", type=int, required=True)
    parser.add_argument("--max-total-bytes", type=int, required=True)
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("explicit --execute required; no capture or publication started")
    config = CycleConfig(args.state_dir, args.archive_root, args.ssh_target, args.ssh_key,
                         args.max_requests, args.max_total_bytes, scheduled=args.scheduled)
    print(json.dumps(run_cycle(config)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
