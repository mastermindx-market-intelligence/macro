"""Original GEX bytes arriving through an independently authorized private copy.

This fills the existing configured producer directory only. It performs no
transfer, source acquisition, retention, Save, app binding or activation. The
caller owns the private channel, destination/account/ACL and resource authority.
"""
from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import stat
import uuid

from engine import options_hub_retention as retention
from engine.intelligence_workspace import scenario_source_resolution as source


class SourceArrivalRefused(ValueError):
    """The final source was not installed by this call."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class SourceArrivalUncertain(ValueError):
    """The target may exist. Inspect this same arrival; do not overwrite/replay."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _existing_gex_directory(path: Path) -> int:
    """Hold each existing component without following any symlink."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in (*path.parts[1:], "gex"):
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def arrive_gex_source(
    descriptor: source.ScenarioSourceDescriptor, raw: bytes, *,
    producer_out_dir: Path, today: date, directory_fd: int | None = None,
) -> retention.SnapshotReference:
    """Create the fixed source leaf once, preserving the original byte sequence.

    The typed descriptor selects content, not an atomic nightly generation or
    authenticated producer provenance. B's existing capture revalidates it under
    current Save/retention authority. No successful arrival clears those gates.
    A requested moves artifact is refused intact; it is never silently omitted.
    """
    try:
        source._validate_descriptor(descriptor)
    except Exception:
        raise SourceArrivalRefused("descriptor_invalid") from None
    if descriptor.moves is not None:
        raise SourceArrivalRefused("moves_requested")
    if descriptor.grant_id is not None:
        raise SourceArrivalRefused("owner_capture_required")
    if type(today) is not date or type(raw) is not bytes or not 0 < len(raw) <= retention.MAX_GEX_BYTES:
        raise SourceArrivalRefused("source_bytes_invalid")
    try:
        payload = retention.verify_snapshot(descriptor.gex, raw, today=today)
    except Exception:
        raise SourceArrivalRefused("source_mismatch") from None
    projection = payload.get("exposure_projection")
    clocks = projection.get("clocks") if type(projection) is dict else None
    observed = clocks.get("option_observed_at") if type(clocks) is dict else None
    if observed != descriptor.source_as_of:
        raise SourceArrivalRefused("source_clock_mismatch")
    if not isinstance(producer_out_dir, Path) or not producer_out_dir.is_absolute() or ".." in producer_out_dir.parts:
        raise SourceArrivalRefused("producer_path_invalid")

    directory = file_fd = None
    temporary = None
    owned_inode = None
    link_started = linked = False
    try:
        directory = (os.dup(directory_fd) if directory_fd is not None
                     else _existing_gex_directory(producer_out_dir))
        if not stat.S_ISDIR(os.fstat(directory).st_mode):
            raise SourceArrivalRefused("producer_directory_invalid")
        temporary = f".p052-gex-{uuid.uuid4().hex}.tmp"
        file_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          0o600, dir_fd=directory)
        info = os.fstat(file_fd)
        owned_inode = (info.st_dev, info.st_ino)
        view = memoryview(raw)
        while view:
            written = os.write(file_fd, view)
            if written <= 0:
                raise OSError("source write incomplete")
            view = view[written:]
        os.fsync(file_fd)
        named = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != owned_inode or not stat.S_ISREG(named.st_mode) or named.st_size != len(raw):
            raise OSError("temporary source changed")
        link_started = True
        os.link(temporary, f"{descriptor.root}.json", src_dir_fd=directory,
                dst_dir_fd=directory, follow_symlinks=False)
        linked = True
        published = os.stat(f"{descriptor.root}.json", dir_fd=directory, follow_symlinks=False)
        if (published.st_dev, published.st_ino) != owned_inode or not stat.S_ISREG(published.st_mode) or published.st_size != len(raw):
            raise OSError("published source changed")
        os.fsync(directory)
        return descriptor.gex
    except FileExistsError:
        # EEXIST from no-overwrite link is authoritative; no target was replaced.
        if link_started and not linked:
            raise SourceArrivalRefused("target_exists") from None
        if not link_started:
            raise SourceArrivalRefused("source_arrival_failed") from None
        raise SourceArrivalUncertain("source_arrival_uncertain") from None
    except Exception:
        if link_started:
            raise SourceArrivalUncertain("source_arrival_uncertain") from None
        raise SourceArrivalRefused("source_arrival_failed") from None
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass
        if temporary is not None and directory is not None and owned_inode is not None:
            try:
                info = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
                if (info.st_dev, info.st_ino) == owned_inode:
                    os.unlink(temporary, dir_fd=directory)
            except OSError:
                pass
        if directory is not None:
            try:
                os.close(directory)
            except OSError:
                pass
