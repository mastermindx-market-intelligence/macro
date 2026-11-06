"""One fixed public archive acquisition; no installer or executable invocation.

The future admitted qualification supplies its private operation directory and
existing phase deadline. This helper is not a dispatch or permission issuer.
Failed partial files stay on the original operation; it never retries or cleans.
"""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tarfile
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

import runsc_install as installer

URL = 'https://github.com/google/gvisor/releases/download/release-20261005.0/gvisor-x86_64.tar.bz2'
FILENAME = 'gvisor-x86_64.tar.bz2'
CHUNK = 65536


class ArchivePhaseRefused(ValueError):
    pass


def _check(ok, reason):
    if not ok:
        raise ArchivePhaseRefused(reason)


def acquire(operation_dir, deadline):
    """Production uses the immutable installer contract, no ambient proxy auth."""
    opener = build_opener(ProxyHandler({}))
    return _acquire(operation_dir, deadline, installer.PRODUCTION_CONTRACT,
                    opener.open, time.monotonic, shutil.disk_usage)


def _acquire(operation_dir, deadline, contract, open_url, clock, disk_usage):
    # Injection seams below are only for hermetic source tests. No contract,
    # URL, destination filename, opener or clock can be supplied by a CLI.
    def checkpoint():
        remaining = deadline - clock()
        _check(0 < remaining <= 240, 'phase_deadline')
        return remaining
    checkpoint()
    root = Path(operation_dir)
    meta = root.lstat()
    _check(root.is_absolute() and stat.S_ISDIR(meta.st_mode)
           and meta.st_uid == os.geteuid() and stat.S_IMODE(meta.st_mode) == 0o700,
           'operation_directory')
    _check(disk_usage(root).free >= contract.archive_size + contract.expanded_total
           + installer.DISK_ADMISSION_MARGIN_BYTES, 'archive_and_stage_disk_admission')
    path = root / FILENAME
    checkpoint()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    total, digest = 0, hashlib.sha256()
    try:
        with open_url(URL, timeout=min(20, checkpoint())) as response:
            _check(urlsplit(response.geturl()).scheme == 'https', 'https_required')
            _check(response.status == 200, 'http_status')
            length = response.headers.get('Content-Length')
            _check(length is None or length == str(contract.archive_size), 'http_length')
            while True:
                checkpoint()
                raw = response.read(CHUNK)
                checkpoint()
                if not raw:
                    break
                _check(type(raw) is bytes and len(raw) <= CHUNK, 'stream_chunk')
                total += len(raw)
                _check(total <= contract.archive_size <= installer.ARCHIVE_MAX_BYTES,
                       'archive_byte_ceiling')
                digest.update(raw)
                rest = memoryview(raw)
                while rest:
                    checkpoint()
                    n = os.write(fd, rest)
                    _check(type(n) is int and 0 < n <= len(rest), 'short_write_progress')
                    rest = rest[n:]
        _check(total == contract.archive_size and digest.hexdigest() == contract.archive_sha256,
               'archive_pin')
        checkpoint(); os.fsync(fd)
    finally:
        os.close(fd)
    checkpoint(); installer.fsync_dir(str(root))
    pins = {}
    # Bytes are already pinned. This pass derives only the six required hashes;
    # the installer independently validates all names/types/links before staging.
    with tarfile.open(path, 'r|bz2') as archive:
        for member in archive:
            checkpoint()
            if member.name not in contract.member_sizes:
                continue
            _check(member.name not in pins and member.isfile()
                   and member.size == contract.member_sizes[member.name], 'required_member')
            stream = archive.extractfile(member)
            _check(stream is not None, 'member_stream')
            h, seen = hashlib.sha256(), 0
            while True:
                checkpoint(); raw = stream.read(CHUNK); checkpoint()
                if not raw:
                    break
                seen += len(raw)
                _check(seen <= member.size, 'member_bound')
                h.update(raw)
            _check(seen == member.size, 'member_length')
            pins[member.name] = h.hexdigest()
    _check(set(pins) == set(contract.member_sizes)
           and pins['runsc'] == contract.runsc_member_sha256, 'member_pins')
    checkpoint()
    return {'archive_path': str(path), 'archive_bytes': total,
            'archive_sha256': digest.hexdigest(), 'member_sha256': pins,
            'acquisition_count': 1, 'executable_invoked': False}
