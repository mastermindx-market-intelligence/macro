"""Closed native-APT command/archive contract for the qualified Playwright input.

No process, configuration write, network request or production selector exists
here. The executable adapter must obtain a complete native resolver transaction
and use the native lock-held final fence before any package mutation.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import re
import shlex
from urllib.parse import unquote

from scripts.ci_apt_cold_acquisition import AcquisitionRefused, Archive, make_download_plan


# Official Playwright1.64.1 nativeDeps.ts ubuntu24.04-x64; registry adds
# chromium then tools, preserving the original33 direct requested packages.
# Source nativeDeps SHA256:1c4244d21f785e11e08b94ede8797bc15941f24b0bdfa677b13fc246f4ace35f.
DIRECT_PACKAGES = (
    "libasound2t64", "libatk-bridge2.0-0t64", "libatk1.0-0t64", "libatspi2.0-0t64",
    "libcairo2", "libcups2t64", "libdbus-1-3", "libdrm2", "libgbm1", "libglib2.0-0t64",
    "libnspr4", "libnss3", "libpango-1.0-0", "libx11-6", "libxcb1", "libxcomposite1",
    "libxdamage1", "libxext6", "libxfixes3", "libxkbcommon0", "libxrandr2",
    "xvfb", "fonts-noto-color-emoji", "fonts-unifont", "libfontconfig1", "libfreetype6",
    "xfonts-cyrillic", "xfonts-scalable", "fonts-liberation", "fonts-ipafont-gothic",
    "fonts-wqy-zenhei", "fonts-tlwg-loma-otf", "fonts-freefont-ttf",
)
QUALIFIED_DRIVER = "829521b67ed7be90c7d6d6098ff39f2241562d47e4ad7ccab13710924a56001d"
INHERITED_INSTALL_FLAGS = ("install", "-y", "--no-install-recommends")


def qualified_direct_packages(*, distribution_version: str, driver_version: str,
                              bundle_sha256: str, os_id: str, os_version: str,
                              machine: str) -> tuple[str, ...]:
    if (distribution_version, driver_version, bundle_sha256, os_id, os_version, machine) != (
        "1.64.1", "1.64.0-beta-1791568591000", QUALIFIED_DRIVER, "ubuntu", "24.04", "x86_64"
    ):
        raise AcquisitionRefused("DEPENDENCY_SOURCE_UNQUALIFIED")
    return DIRECT_PACKAGES


def _job_path(value: str) -> str:
    if not re.fullmatch(r"/tmp/ci-apt-[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*", value):
        raise AcquisitionRefused("JOB_PATH_UNQUALIFIED")
    if ".." in PurePosixPath(value).parts:
        raise AcquisitionRefused("JOB_PATH_UNQUALIFIED")
    return value


def resolver_argv(*, hook: str, cache: str) -> tuple[str, ...]:
    """Native print-URIs is read-only; its JSON0.2 hook supplies full actions.

    ForceHash only changes the printed digest from its legacy MD5 default to
    SHA256. Actual downloads/install retain native authentication/hash checks.
    """
    hook, cache = _job_path(hook), _job_path(cache)
    return ("/usr/bin/apt-get", "--print-uris", "-o", "Acquire::ForceHash=SHA256",
            "-o", f"Dir::Cache::Archives={cache}",
            "-o", f"AptCli::Hooks::Install::={shlex.quote(hook)} json",
            *INHERITED_INSTALL_FLAGS, *DIRECT_PACKAGES)


def no_download_install_argv(*, hook: str, cache: str) -> tuple[str, ...]:
    hook, cache = _job_path(hook), _job_path(cache)
    return ("/usr/bin/apt-get", "--no-download", "-o", "APT::Get::Fix-Missing=false",
            "-o", "APT::Get::AllowUnauthenticated=false", "-o", "Debug::NoLocking=false",
            "-o", "Acquire::AllowInsecureRepositories=false",
            "-o", "Acquire::AllowDowngradeToInsecureRepositories=false",
            "-o", f"Dir::Cache::Archives={cache}",
            "-o", f"AptCli::Hooks::Install::={shlex.quote(hook)} json",
            "-o", f"DPkg::Pre-Install-Pkgs::={shlex.quote(hook)} preinstall",
            "-o", f"DPkg::Tools::Options::{hook}::Version=3",
            "-o", f"DPkg::Tools::Options::{hook}::InfoFD=0",
            *INHERITED_INSTALL_FLAGS, *DIRECT_PACKAGES)


def complete_archive_inventory(transaction: dict, raw_uris: bytes) -> tuple[Archive, ...]:
    """Bind every printed archive to the complete normalized native transaction.

    The resolver uses a fresh job-local archive directory, so missing records
    cannot be explained away as a cache hit. This is not an auth receipt;
    native APT download must independently authenticate each exact selection.
    """
    if len(raw_uris) > 1024 * 1024 or not raw_uris.isascii():
        raise AcquisitionRefused("URI_INPUT_UNQUALIFIED")
    if transaction.get("search-terms") != list(DIRECT_PACKAGES) or transaction.get("command") != "install":
        raise AcquisitionRefused("DIRECT_DEPENDENCIES_CHANGED")
    expected = {}
    for row in transaction["packages"]:
        if row["mode"] in {"deinstall", "purge"}:
            continue
        selected = row["versions"]["install"]
        identity = row["name"], selected["version"], selected["architecture"]
        if identity in expected:
            raise AcquisitionRefused("TRANSACTION_ARCHIVE_AMBIGUOUS")
        expected[identity] = row["architecture"]
    found = {}
    for line in raw_uris.decode("ascii").splitlines():
        if not line.startswith("'"):
            continue  # ordinary APT summary; never interpreted or echoed
        try:
            fields = shlex.split(line)
            if len(fields) != 4 or not re.fullmatch(r"[0-9]{1,10}", fields[2]):
                raise ValueError
            filename = fields[1]
            decoded = unquote(filename)
            if not decoded.endswith(".deb"):
                raise ValueError
            pieces = decoded[:-4].split("_")
            if len(pieces) != 3:
                raise ValueError
            identity = tuple(pieces)
            if identity not in expected or identity in found or not re.fullmatch(r"SHA256:[0-9a-f]{64}", fields[3]):
                raise ValueError
            found[identity] = Archive(pieces[0], pieces[1], expected[identity], pieces[2], filename,
                                      int(fields[2]), fields[3][7:], fields[0])
        except (ValueError, UnicodeError):
            raise AcquisitionRefused("URI_TRANSACTION_MISMATCH") from None
    if found.keys() != expected.keys():
        raise AcquisitionRefused("TRANSACTION_ARCHIVE_MISSING")
    archives = tuple(found[key] for key in expected)
    make_download_plan(archives)
    return archives


def trusted_package_indexes_argv() -> tuple[str, ...]:
    # cmdline/apt-get.cc emits metaIndex::IsTrusted for existing targets.
    # Fixed-format native output excludes origins/configuration/credentials.
    return ('/usr/bin/apt-get','indextargets','--release-info','--format','$(TRUSTED)','Identifier: Packages')


def require_trusted_package_indexes(raw: bytes) -> None:
    if type(raw) is not bytes or not 0 < len(raw) <= 4096 or not raw.endswith(b'\n'):
        raise AcquisitionRefused('NATIVE_INDEX_TRUST_UNPROVEN')
    rows=raw.splitlines()
    if not 1 <= len(rows) <= 256 or raw != b'yes\n' * len(rows):
        raise AcquisitionRefused('NATIVE_INDEX_TRUST_UNPROVEN')


def completion_download_argv(*, hook: str, cache: str) -> tuple[str, ...]:
    hook, cache = _job_path(hook), _job_path(cache)
    return ('/usr/bin/apt-get','--download-only','-o','APT::Sandbox::User=_apt','-o','APT::Get::Fix-Missing=false',
            '-o','APT::Get::AllowUnauthenticated=false','-o','Debug::NoLocking=false',
            '-o','Acquire::AllowInsecureRepositories=false',
            '-o','Acquire::AllowDowngradeToInsecureRepositories=false',
            '-o',f'Dir::Cache::Archives={cache}',
            '-o',f'AptCli::Hooks::Install::={shlex.quote(hook)} json',
            *INHERITED_INSTALL_FLAGS,*DIRECT_PACKAGES)
