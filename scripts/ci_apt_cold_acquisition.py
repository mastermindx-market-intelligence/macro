"""Bounded cold native-APT acquisition core; no production selection or I/O.

This executable orchestration core is deliberately separate from the native
resolver/hook/process adapter. A backend must retain native authentication and
the lock-held final transaction/archive fence. Test backends are not evidence
of native installation, process settlement, throughput or a product result.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Protocol
from urllib.parse import unquote, urlsplit


class AcquisitionRefused(ValueError):
    """Fixed reason only; no untrusted command/configuration payloads."""


@dataclass(frozen=True)
class Archive:
    package: str
    version: str
    package_architecture: str
    archive_architecture: str
    filename: str
    size: int
    sha256: str
    uri: str

    @property
    def selector(self) -> str:
        return f"{self.package}:{self.package_architecture}={self.version}"


@dataclass(frozen=True)
class DownloadPlan:
    transaction: tuple[Archive, ...]
    # Largest first is scheduling only. The complete original transaction is
    # retained in original order and passed unchanged to the final native fence.
    schedule: tuple[int, ...]
    concurrency: int = 4


APPROVED_ORIGINS = {
    ("http", "azure.archive.ubuntu.com"),
    ("https", "archive.ubuntu.com"),
    ("https", "security.ubuntu.com"),
}
_NAME = re.compile(r"[a-z0-9][a-z0-9+.-]{0,127}\Z")
_ARCH = re.compile(r"[a-z0-9][a-z0-9-]{0,31}\Z")
_VERSION = re.compile(r"[0-9][A-Za-z0-9.+:~\-]{0,127}\Z")


def make_download_plan(archives: tuple[Archive, ...], *, concurrency: int = 4) -> DownloadPlan:
    """Validate the entire native archive inventory without dropping a row."""
    if type(concurrency) is not int or not 1 <= concurrency <= 4:
        raise AcquisitionRefused("CONCURRENCY_INVALID")
    if not isinstance(archives, tuple) or len(archives) > 128:
        raise AcquisitionRefused("ARCHIVE_LIMIT")
    identities, filenames, uris = set(), set(), set()
    total = 0
    for item in archives:
        if not isinstance(item, Archive):
            raise AcquisitionRefused("ARCHIVE_SHAPE")
        if any(not isinstance(value, str) for value in (item.package, item.version, item.package_architecture,
                                                       item.archive_architecture, item.filename, item.sha256, item.uri)):
            raise AcquisitionRefused("ARCHIVE_SHAPE")
        if not _NAME.fullmatch(item.package) or not _VERSION.fullmatch(item.version):
            raise AcquisitionRefused("PACKAGE_IDENTITY")
        if not all(_ARCH.fullmatch(a) for a in (item.package_architecture, item.archive_architecture)):
            raise AcquisitionRefused("PACKAGE_ARCHITECTURE")
        identity = item.package, item.package_architecture
        if identity in identities or item.filename in filenames or item.uri in uris:
            raise AcquisitionRefused("ARCHIVE_DUPLICATE")
        identities.add(identity); filenames.add(item.filename); uris.add(item.uri)
        expected_filename = f"{item.package}_{item.version}_{item.archive_architecture}.deb"
        if "/" in item.filename or "\\" in item.filename or unquote(item.filename) != expected_filename:
            raise AcquisitionRefused("ARCHIVE_FILENAME")
        if type(item.size) is not int or not 0 < item.size <= 128 * 1024 * 1024:
            raise AcquisitionRefused("ARCHIVE_SIZE")
        total += item.size
        if total > 512 * 1024 * 1024:
            raise AcquisitionRefused("ARCHIVE_TOTAL")
        if not re.fullmatch(r"[0-9a-f]{64}", item.sha256):
            raise AcquisitionRefused("ARCHIVE_HASH")
        try:
            uri = urlsplit(item.uri)
            if (uri.scheme, uri.hostname) not in APPROVED_ORIGINS or uri.port is not None:
                raise ValueError
            if uri.username or uri.password or uri.query or uri.fragment:
                raise ValueError
            if not uri.path.startswith("/ubuntu/pool/") or unquote(uri.path.rsplit("/", 1)[-1]) != expected_filename:
                raise ValueError
        except (ValueError, UnicodeError):
            raise AcquisitionRefused("ARCHIVE_ORIGIN") from None
    return DownloadPlan(archives, tuple(sorted(range(len(archives)), key=lambda i: (-archives[i].size, i))), concurrency)


def download_argv(archive: Archive) -> tuple[str, ...]:
    """Native APT retains signed-index/hash checks; no URI downloader/override."""
    return ("/usr/bin/apt-get", "-o", "APT::Get::AllowUnauthenticated=false", "download", archive.selector)


@dataclass(frozen=True)
class ChildResult:
    outcome: str  # passed, failed, timed_out, or unknown
    settlement: str  # settled or unknown; supplied by the native child observer


@dataclass(frozen=True)
class AcquisitionResult:
    outcome: str
    settlement: str
    completed: tuple[int, ...]
    pending: tuple[int, ...]
    installation: str  # never_started, passed, failed, timed_out, unknown
    reason: str
    observations: tuple[tuple[int, str, str], ...] = ()


class NativeBackend(Protocol):
    """Required adapter contract, not a caller-provided authorization receipt.

    Each launched native process gets a unique staging path. collect() must
    observe existing processes only, return by the SAME absolute deadline and
    never retry a download. Native method descendants must be reconciled by its
    process owner; an unknown observation must not be called settled.
    """

    def now(self) -> float: ...
    def launch(self, index: int, argv: tuple[str, ...], deadline: float) -> object: ...
    def collect(self, children: dict[int, object], deadline: float) -> dict[int, ChildResult]: ...
    def verify_archive(self, index: int, archive: Archive) -> None: ...
    def install_frozen(self, original: tuple[Archive, ...], deadline: float) -> ChildResult: ...
    def cleanup_success(self) -> None: ...


def acquire_and_install(plan: DownloadPlan, backend: NativeBackend, *, deadline: float) -> AcquisitionResult:
    """Schedule native downloads once; install only after positive completion.

    Planning/update elapsed time is already included in deadline. The final
    backend must use --no-download, forbid fix-missing, compare the full native
    transaction, and check exact archive bytes under the native pre-dpkg lock.
    A missing adapter is an implementation boundary, never a success/fallback.
    """
    if make_download_plan(plan.transaction, concurrency=plan.concurrency) != plan:
        raise AcquisitionRefused("PLAN_CHANGED")
    queued = list(plan.schedule)
    active: dict[int, object] = {}
    complete: list[int] = []
    history: list[tuple[int, str, str]] = []
    failed = None
    uncertain = False
    while queued or active:
        while queued and failed is None and len(active) < plan.concurrency and backend.now() < deadline:
            index = queued.pop(0)
            try:
                active[index] = backend.launch(index, download_argv(plan.transaction[index]), deadline)
            except Exception:
                # A launch response can be lost after the effect. Never assume
                # no child exists, retry, install, clean or launch later work.
                failed, uncertain = "LAUNCH_RESPONSE_UNKNOWN", True
                active[index] = None
                break
        if not active:
            if queued:
                failed = failed or "TOTAL_DEADLINE"
            break
        if backend.now() >= deadline:
            failed, uncertain = failed or "TOTAL_DEADLINE", True
            break
        try:
            observations = backend.collect(dict(active), deadline)
            if not observations or set(observations) - set(active):
                raise AcquisitionRefused("OBSERVATION_SHAPE")
            for index, result in observations.items():
                if not isinstance(result, ChildResult) or result.outcome not in {"passed", "failed", "timed_out", "unknown"}:
                    raise AcquisitionRefused("OBSERVATION_SHAPE")
                history.append((index, result.outcome, result.settlement))
                if result.settlement != "settled" or result.outcome in {"timed_out", "unknown"}:
                    failed, uncertain = "CHILD_SETTLEMENT_UNKNOWN", True
                    continue
                del active[index]
                if result.outcome != "passed":
                    failed = failed or "NATIVE_DOWNLOAD_FAILED"
                    continue
                try:
                    backend.verify_archive(index, plan.transaction[index])
                except AcquisitionRefused:
                    failed = failed or "ARCHIVE_BYTES_UNPROVEN"
                    continue
                complete.append(index)
        except Exception:
            failed, uncertain = "OBSERVATION_OR_ARCHIVE_UNPROVEN", True
            break
        if uncertain:
            break
    if uncertain:
        return AcquisitionResult("timed_out" if backend.now() >= deadline else "failed", "unknown", tuple(complete), tuple(active), "never_started", failed, tuple(history))
    if failed:
        return AcquisitionResult("failed", "settled", tuple(complete), (), "never_started", failed, tuple(history))
    if backend.now() >= deadline:
        return AcquisitionResult("timed_out", "settled", tuple(complete), (), "never_started", "TOTAL_DEADLINE", tuple(history))
    try:
        result = backend.install_frozen(plan.transaction, deadline)
        if not isinstance(result, ChildResult) or result.settlement != "settled" or result.outcome not in {"passed", "failed"}:
            return AcquisitionResult("timed_out" if isinstance(result, ChildResult) and result.outcome == "timed_out" else "failed", "unknown", tuple(complete), (), result.outcome if isinstance(result, ChildResult) else "unknown", "INSTALLATION_UNPROVEN", tuple(history))
        if result.outcome != "passed":
            return AcquisitionResult("failed", "settled", tuple(complete), (), "failed", "NATIVE_INSTALL_FAILED", tuple(history))
    except Exception:
        return AcquisitionResult("failed", "unknown", tuple(complete), (), "unknown", "INSTALL_RESPONSE_UNKNOWN", tuple(history))
    if backend.now() >= deadline:
        return AcquisitionResult("timed_out", "settled", tuple(complete), (), "passed", "TOTAL_DEADLINE_AFTER_INSTALL", tuple(history))
    try:
        backend.cleanup_success()
    except Exception as error:
        return AcquisitionResult("timed_out" if getattr(error, "outcome", None) == "timed_out" else "failed", "unknown", tuple(complete), (), "passed", "CLEANUP_RESPONSE_UNKNOWN", tuple(history))
    return AcquisitionResult("passed", "settled", tuple(complete), (), "passed", "NATIVE_TRANSACTION_COMPLETE", tuple(history))


def verify_payload(archive: Archive, payload: bytes) -> None:
    """Synthetic/reproducer helper; production adapter must stream bounded files."""
    if len(payload) != archive.size or hashlib.sha256(payload).hexdigest() != archive.sha256:
        raise AcquisitionRefused("ARCHIVE_BYTES_CHANGED")
