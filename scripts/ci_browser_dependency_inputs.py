"""Pure diagnostics for the unresolved apt .deb transfer bottleneck.

Strictly pure: inputs are caller-supplied bytes/mappings only; no process launch,
network access, package or browser install, filesystem access, CLI handling, retry
logic or environment mutation happens here, and no raw input, unknown name, malformed
value, exception text or environment value is ever echoed.  Records are diagnostic and
non-authoritative: they describe only the exact bytes supplied, never the original
historical runtime or an unchanged environment.  The recovered official 1.64.1 wheel
coreBundle digest is provenance context only; nothing here compares against it.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any, Dict

__all__ = ["summarize_apt_inputs", "summarize_playwright_inputs"]

_APT_FIELDS = ("APT_RETRIES", "APT_HTTP_TIMEOUT", "APT_HTTPS_TIMEOUT",
               "APT_HTTP_DL_LIMIT", "APT_HTTPS_DL_LIMIT")
_PROXY_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy")
_APT_RAW_LIMIT = 8192
_APT_MAX_VALUE = 2147483647
_APT_LINE_RE = re.compile(rb"^([A-Z][A-Z0-9_]*)='([0-9]+)'$")
_INPUT_NAMES = ("metadata", "driver_package_json", "driver_bundle")
_INPUT_LIMITS = {"metadata": 65536, "driver_package_json": 65536,
                 "driver_bundle": 8 * 1024 * 1024}
_VERSION_MAX_CHARS = 64
_VERSION_RE = re.compile(
    r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){1,3}(-[0-9A-Za-z][0-9A-Za-z.\-]*)?")
_METADATA_VERSION_RE = re.compile(rb"(?m)^Version:[ \t]*([^\r\n]*)\r?$")

_SHARED_NOTES = (
    "Diagnostic observation of caller-supplied bytes only; not authoritative; raw input,"
    " unknown names, malformed values, exception text and environment values are never echoed.",
    "Never asserts the original historical runtime or that any environment stayed unchanged.",
)
_APT_NOTES = _SHARED_NOTES + (
    "Missing numeric fields are listed as absent; zero or a default is never inferred.",
    "Proxy and APT_CONFIG entries are presence booleans only; values, URLs, users, passwords and paths are never returned.",
)
_PLAYWRIGHT_NOTES = _SHARED_NOTES + (
    "sha256 digests identify the exact supplied bytes only; they do not establish official authenticity or runtime identity.",
    "Distribution and bundled driver versions are recorded separately as observed; they need not match and imply no upgrade, downgrade or acceptance decision.",
    "No copy of any input is retained beyond the returned digest.",
)


def _record(kind, available, reason, **fields):
    body = {"kind": kind, "diagnostic": True, "authoritative": False,
            "available": available, "unavailable_reason": reason}
    body.update(fields)
    return body


def summarize_apt_inputs(raw_shell_output: bytes, environment: Mapping) -> Dict[str, Any]:
    """Observe apt-config numeric fields and proxy presence; never infer defaults."""
    if not isinstance(raw_shell_output, (bytes, bytearray)):
        return _apt_unavailable("INPUT_TYPE_INVALID", None)
    raw, size = bytes(raw_shell_output), len(raw_shell_output)
    if size > _APT_RAW_LIMIT:
        return _apt_unavailable("INPUT_OVERSIZE", size)
    if not raw.isascii():
        return _apt_unavailable("NON_ASCII_INPUT", size)
    observations = {}
    for line in raw.split(b"\n"):
        if not line:
            continue
        matched = _APT_LINE_RE.match(line)
        if matched is None:
            return _apt_unavailable("MALFORMED_LINE", size)
        name = matched.group(1).decode("ascii")
        if name not in _APT_FIELDS:
            return _apt_unavailable("UNKNOWN_FIELD", size)
        if name in observations:
            return _apt_unavailable("DUPLICATE_FIELD", size)
        digits = matched.group(2).lstrip(b"0") or b"0"
        if len(digits) > 10:
            return _apt_unavailable("VALUE_OUT_OF_RANGE", size)
        number = int(digits)
        if number > _APT_MAX_VALUE:
            return _apt_unavailable("VALUE_OUT_OF_RANGE", size)
        observations[name] = number
    if not isinstance(environment, Mapping):
        return _apt_unavailable("ENVIRONMENT_TYPE_INVALID", size)
    try:
        proxy_present = {name: name in environment for name in _PROXY_NAMES}
        apt_config_present = "APT_CONFIG" in environment
    except Exception:
        return _apt_unavailable("ENVIRONMENT_TYPE_INVALID", size)
    return _record("apt_dependency_inputs", True, None,
                   observations=observations,
                   absent_fields=[n for n in _APT_FIELDS if n not in observations],
                   proxy_present=proxy_present, apt_config_present=apt_config_present,
                   input_bytes=size, notes=list(_APT_NOTES))


def _apt_unavailable(reason, size):
    return _record("apt_dependency_inputs", False, reason, observations=None,
                   absent_fields=None, proxy_present=None, apt_config_present=None,
                   input_bytes=size, notes=list(_APT_NOTES))


class _DuplicateKey(ValueError):
    """Internal sentinel: carries the duplicated key, never echoed outward."""


def _reject_duplicate_keys(pairs):
    unique = {}
    for key, value in pairs:
        if key in unique:
            raise _DuplicateKey(key)
        unique[key] = value
    return unique


def _checked_version(text):
    if not text or len(text) > _VERSION_MAX_CHARS or not text.isascii():
        return False
    return _VERSION_RE.fullmatch(text) is not None


def summarize_playwright_inputs(metadata: bytes, driver_package_json: bytes,
                                driver_bundle: bytes) -> Dict[str, Any]:
    """Observe distribution/driver versions separately plus exact-bytes digests."""
    supplied = {"metadata": metadata, "driver_package_json": driver_package_json,
                "driver_bundle": driver_bundle}
    sizes = {}
    for name in _INPUT_NAMES:
        if not isinstance(supplied[name], (bytes, bytearray)):
            return _playwright_unavailable("INPUT_TYPE_INVALID")
        sizes[name] = len(supplied[name])
        if sizes[name] > _INPUT_LIMITS[name]:
            return _playwright_unavailable(name.upper() + "_OVERSIZE")
    observed_version, reason = _parse_metadata_version(supplied["metadata"])
    if reason is None:
        driver_version, reason = _parse_driver_version(supplied["driver_package_json"])
    if reason is not None:
        return _playwright_unavailable(reason)
    return _record("playwright_dependency_inputs", True, None,
                   observed_version=observed_version, driver_version=driver_version,
                   version_relationship="equal" if driver_version == observed_version else "different",
                   input_bytes=sizes,
                   input_sha256={name: hashlib.sha256(supplied[name]).hexdigest()
                                 for name in _INPUT_NAMES},
                   notes=list(_PLAYWRIGHT_NOTES))


def _playwright_unavailable(reason):
    return _record("playwright_dependency_inputs", False, reason, observed_version=None,
                   driver_version=None, version_relationship=None,
                   input_bytes=None, input_sha256=None, notes=list(_PLAYWRIGHT_NOTES))


def _parse_metadata_version(metadata):
    found = _METADATA_VERSION_RE.findall(metadata)
    if not found:
        return None, "METADATA_VERSION_MISSING"
    if len(found) > 1:
        return None, "METADATA_VERSION_DUPLICATE"
    try:
        text = found[0].decode("ascii")
    except UnicodeDecodeError:
        return None, "METADATA_VERSION_MALFORMED"
    return (text, None) if _checked_version(text) else (None, "METADATA_VERSION_MALFORMED")


def _parse_driver_version(driver_package_json):
    try:
        document = json.loads(driver_package_json.decode("utf-8"),
                              object_pairs_hook=_reject_duplicate_keys)
    except _DuplicateKey as error:
        return None, ("JSON_VERSION_DUPLICATE" if error.args[0] == "version"
                      else "JSON_DUPLICATE_KEY")
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, "JSON_PARSE_ERROR"
    if not isinstance(document, dict):
        return None, "JSON_PARSE_ERROR"
    if "version" not in document:
        return None, "JSON_VERSION_MISSING"
    version = document["version"]
    if not isinstance(version, str) or not _checked_version(version):
        return None, "JSON_VERSION_MALFORMED"
    return version, None
