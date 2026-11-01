"""One private BOATS history delivery over the existing SSH transport.

An immutable local manifest and tar bundle are verified before transport. The
receiver creates a new version, validates every file, and atomically replaces
the existing history pointer only when its expected predecessor still matches.
No service restart, public endpoint, credential transfer, retry or scheduler.
A permanent local start receipt makes an interrupted delivery require explicit
same-operation reconciliation rather than an automatic second publication.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
FILE = re.compile(r"[A-Z][A-Z0-9.-]{0,31}\.json\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
MAX_MANIFEST = 8 * 1024**2
MAX_FILE = 32 * 1024**2
MAX_TOTAL = 8 * 1024**3
REMOTE_BASE = "/mnt/terminal_storage/boats-history"


def encode(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _private_write(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def validate_ssh_binding(ssh_target: str, ssh_key: Path) -> None:
    """Check static delivery configuration before a cycle consumes its budget."""
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*@[A-Za-z0-9][A-Za-z0-9.-]{0,252}", ssh_target):
        raise ValueError("invalid explicit SSH destination")
    info = ssh_key.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("private owned regular SSH key required")


def transfer_timeout(archive_bytes: int, file_count: int) -> int:
    # A single bounded transfer, allowing 1 MiB/s plus per-file receiver fsync
    # time. Slow transport still becomes an unknown effect, never a retry.
    return max(600, min(14400, 300 + math.ceil(archive_bytes / 1024**2) + math.ceil(file_count / 5)))


def validate_manifest(manifest: dict, version: str) -> None:
    if not isinstance(version, str) or not VERSION.fullmatch(version) or version == "current":
        raise ValueError("invalid immutable version")
    if (not isinstance(manifest, dict) or manifest.get("schema") != "terminal.private_boats_delivery.v1"
            or manifest.get("complete_history") is not False
            or manifest.get("directory") != REMOTE_BASE + "/" + version):
        raise ValueError("invalid private delivery manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) > 20000:
        raise ValueError("file count limit")
    seen, total, bars = set(), 0, 0
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("invalid file item")
        name, size, count, sha = (item.get(k) for k in ("name", "bytes", "bars", "sha256"))
        if (not isinstance(name, str) or not FILE.fullmatch(name) or name in seen
                or type(size) is not int or not 0 < size <= MAX_FILE
                or type(count) is not int or not 0 <= count <= 100000
                or not isinstance(sha, str) or not SHA.fullmatch(sha)):
            raise ValueError("invalid file identity or limits")
        seen.add(name)
        total += size
        bars += count
    if (type(manifest.get("bytes")) is not int or manifest["bytes"] != total or total > MAX_TOTAL
            or type(manifest.get("bars")) is not int or manifest["bars"] != bars):
        raise ValueError("invalid delivery totals")
    empty = manifest.get("vendor_empty_symbols", [])
    if (not isinstance(empty, list) or len(empty) > 20000
            or any(not isinstance(s, str) or not FILE.fullmatch(s + ".json") or s + ".json" in seen for s in empty)
            or len(set(empty)) != len(empty)):
        raise ValueError("invalid empty-symbol identities")


def verify_archive(stream, manifest_raw: bytes, manifest: dict) -> None:
    """Read the exact already-open file; no extraction or path interpretation."""
    expected = {item["name"]: item for item in manifest["files"]}
    seen = set()
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        first = archive.next()
        if (not first or not first.isfile() or first.name != ".delivery-manifest.json"
                or first.size != len(manifest_raw) or first.size > MAX_MANIFEST
                or archive.extractfile(first).read(MAX_MANIFEST + 1) != manifest_raw):
            raise ValueError("bundle manifest mismatch")
        for member in archive:
            if member.name == first.name and not seen and member.offset == first.offset:
                continue  # TarFile iteration includes the cached first member.
            if not member.isfile() or member.name not in expected or member.name in seen:
                raise ValueError("unexpected bundle member")
            item = expected[member.name]
            if member.size != item["bytes"] or member.size > MAX_FILE:
                raise ValueError("bundle member size mismatch")
            raw = archive.extractfile(member).read(MAX_FILE + 1)
            if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
                raise ValueError("bundle member digest mismatch")
            seen.add(member.name)
    if seen != set(expected):
        raise ValueError("incomplete bundle")
    stream.seek(0)


def receiver_code(version: str, predecessor: str, manifest_sha: str) -> str:
    """Fixed receiver; all caller data is bounded and Python-literal encoded."""
    if (not VERSION.fullmatch(version) or not VERSION.fullmatch(predecessor)
            or version in {"current", predecessor} or predecessor == "current" or not SHA.fullmatch(manifest_sha)):
        raise ValueError("invalid selection binding")
    return "VERSION=" + repr(version) + "\nPREVIOUS=" + repr(predecessor) + "\nMANIFEST_SHA=" + repr(manifest_sha) + "\n" + r'''
from pathlib import Path
import fcntl,hashlib,json,os,re,shutil,stat,sys,tarfile
base=Path('/mnt/terminal_storage/boats-history');target=base/VERSION;current=base/'current'
assert os.path.ismount('/mnt/terminal_storage') and not Path('/etc/terminal-storage-maintenance').exists()
assert base.is_dir() and not base.is_symlink() and base.stat().st_uid==os.geteuid() and stat.S_IMODE(base.stat().st_mode)==0o700
assert not Path('/opt/terminal/.terminal-build-resource.lock/hold').exists()
assert current.is_symlink() and os.readlink(current)==PREVIOUS
assert not os.path.lexists(target), 'Existing target requires reconciliation'
seen=set()
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as archive:
 first=archive.next()
 assert first and first.isfile() and first.name=='.delivery-manifest.json' and 0<first.size<=8*1024**2
 raw=archive.extractfile(first).read(first.size+1)
 assert len(raw)==first.size and hashlib.sha256(raw).hexdigest()==MANIFEST_SHA
 manifest=json.loads(raw)
 assert manifest['directory']==str(target) and manifest['schema']=='terminal.private_boats_delivery.v1' and manifest['complete_history'] is False
 files=manifest['files'];assert isinstance(files,list) and len(files)<=20000
 items={item['name']:item for item in files};assert len(items)==len(files)
 assert all(re.fullmatch(r'[A-Z][A-Z0-9.-]{0,31}\.json',name) for name in items)
 assert type(manifest['bytes']) is int and 0<=manifest['bytes']<=8*1024**3
 assert sum(item['bytes'] for item in files)==manifest['bytes']
 assert shutil.disk_usage(base).free>manifest['bytes']+5*1024**3
 target.mkdir(mode=0o700)
 while True:
  member=archive.next()
  if member is None:break
  assert member.isfile() and member.name in items and member.name not in seen
  item=items[member.name]
  assert type(item['bytes']) is int and member.size==item['bytes'] and 0<member.size<=32*1024**2
  body=archive.extractfile(member).read(member.size+1)
  assert len(body)==member.size and hashlib.sha256(body).hexdigest()==item['sha256']
  fd=os.open(target/member.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
  seen.add(member.name)
assert seen==set(items)
d=os.open(target,os.O_RDONLY)
try:os.fsync(d)
finally:os.close(d)
lock=os.open(base/'.history-selection.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
try:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not Path('/opt/terminal/.terminal-build-resource.lock/hold').exists()
 assert not Path('/etc/terminal-storage-maintenance').exists()
 assert current.is_symlink() and os.readlink(current)==PREVIOUS
 temporary=base/('.current-'+VERSION)
 assert not os.path.lexists(temporary)
 os.symlink(VERSION,temporary)
 os.replace(temporary,current)
 d=os.open(base,os.O_RDONLY)
 try:os.fsync(d)
 finally:os.close(d)
 assert os.readlink(current)==VERSION
 print(json.dumps({'schema':'terminal.private_boats_selection.v1','selected_version':VERSION,'previous_version':PREVIOUS,'files':len(seen),'manifest_sha256':MANIFEST_SHA,'service_restarted':False}))
finally:os.close(lock)
'''


def publish_bundle(manifest_path: Path, archive_path: Path, evidence_dir: Path,
                   version: str, predecessor: str, ssh_target: str, ssh_key: Path,
                   *, run=subprocess.run) -> dict:
    validate_ssh_binding(ssh_target, ssh_key)
    for path in (manifest_path, archive_path, ssh_key):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError("private owned regular inputs required")
    if manifest_path.stat().st_size > MAX_MANIFEST or archive_path.stat().st_size > MAX_TOTAL + 32*1024**2:
        raise ValueError("input size limit")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    validate_manifest(manifest, version)
    command = receiver_code(version, predecessor, digest(raw))
    info = evidence_dir.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("private evidence directory required")
    started, result = evidence_dir/"publish-start.json", evidence_dir/"publish-result.json"
    if started.exists() or result.exists():
        raise ValueError("existing publication requires same-operation reconciliation")
    fd = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        verify_archive(stream, raw, manifest)
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("bundle changed during validation")
        _private_write(started, encode({"schema":"terminal.private_boats_publication_start.v1",
            "version":version,"predecessor":predecessor,"manifest_sha256":digest(raw),
            "started_at_utc":datetime.now(timezone.utc).isoformat()}))
        response = run(["ssh", "-i", str(ssh_key), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                        "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
                        ssh_target, "python3 -c " + shlex.quote(command)],
                       stdin=stream, capture_output=True, timeout=transfer_timeout(before.st_size, len(manifest["files"])))
    if response.returncode:
        raise RuntimeError("private publication unconfirmed; retain start and reconcile original destination")
    if len(response.stdout) > 4096:
        raise RuntimeError("publication response exceeds bound; reconcile original destination")
    receipt = json.loads(response.stdout)
    expected = {"schema":"terminal.private_boats_selection.v1", "selected_version":version,
                "previous_version":predecessor, "files":len(manifest["files"]),
                "manifest_sha256":digest(raw), "service_restarted":False}
    if receipt != expected:
        raise RuntimeError("publication response mismatch; reconcile original destination")
    _private_write(result, encode(receipt))
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "archive", "evidence-dir", "ssh-key"):
        parser.add_argument("--"+name, type=Path, required=True)
    for name in ("version", "predecessor", "ssh-target"):
        parser.add_argument("--"+name, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    if not args.publish:
        parser.error("explicit --publish required; no transport started")
    result = publish_bundle(args.manifest, args.archive, args.evidence_dir, args.version,
                            args.predecessor, args.ssh_target, args.ssh_key)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
