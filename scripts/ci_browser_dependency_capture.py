"""Bounded, non-authoritative inputs for the existing browser setup boundary.

No acquisition policy is selected here. The pack runner owns launch, deadlines
and settlement. The CLI only reads selected inputs and prints sanitized JSON.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import sys
import sysconfig
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ci_browser_dependency_inputs import summarize_apt_inputs, summarize_playwright_inputs

NUMERIC_KEYS = {
    "APT_RETRIES": "Acquire::Retries", "APT_HTTP_TIMEOUT": "Acquire::http::Timeout",
    "APT_HTTPS_TIMEOUT": "Acquire::https::Timeout", "APT_HTTP_DL_LIMIT": "Acquire::http::Dl-Limit",
    "APT_HTTPS_DL_LIMIT": "Acquire::https::Dl-Limit",
}
EXTRA_KEYS = {"APT_FORCE_IPV4": "Acquire::ForceIPv4", "APT_FORCE_IPV6": "Acquire::ForceIPv6", "APT_QUEUE_MODE": "Acquire::Queue-Mode"}
CONTEXT_ENV = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "APT_CONFIG")
MIRRORS = {("http", "azure.archive.ubuntu.com", "/ubuntu/"): "azure_ubuntu_http",
           ("https", "archive.ubuntu.com", "/ubuntu/"): "ubuntu_archive_https",
           ("https", "security.ubuntu.com", "/ubuntu/"): "ubuntu_security_https"}


def _unavailable(reason: str) -> dict:
    return {"status": "unavailable", "reason": reason, "authority": "diagnostic_only"}


def capture_commands() -> tuple[str, str]:
    query = "/usr/bin/apt-config shell " + " ".join(f"{name} {key}" for name, key in {**NUMERIC_KEYS, **EXTRA_KEYS}.items())
    lines = [query]
    for index, name in enumerate(CONTEXT_ENV):
        lines.append(f'''if [ "${{{name}+x}}" = x ]; then printf "CTX_{index}='1'\\n"; else printf "CTX_{index}='0'\\n"; fi''')
    body = shlex.quote(" && ".join(lines))
    # Only fixed shell builtins and the native config reader run elevated.
    # Candidate Python/helper code runs after the pipe as the original user.
    query_command = f'''{{ if [ "$(/usr/bin/id -u)" -eq 0 ]; then sh -c {body}; else sudo -n -- sh -c {body}; fi; }} 2>/dev/null | python scripts/ci_browser_dependency_capture.py apt'''
    return query_command, "python scripts/ci_browser_dependency_capture.py playwright"


def summarize_context_inputs(raw: bytes) -> dict:
    import re

    if len(raw) > 8192:
        return _unavailable("INPUT_LIMIT")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError:
        return _unavailable("INPUT_ENCODING")
    fields = {}
    allowed = {*NUMERIC_KEYS, *EXTRA_KEYS, *(f"CTX_{i}" for i in range(len(CONTEXT_ENV)))}
    for line in lines:
        match = re.fullmatch(r"([A-Z_0-9]+)='([^']*)'", line)
        if not match or match[1] not in allowed or match[1] in fields:
            return _unavailable("INPUT_SHAPE")
        fields[match[1]] = match[2]
    environment = {}
    for index, name in enumerate(CONTEXT_ENV):
        value = fields.get(f"CTX_{index}")
        if value not in {"0", "1"}:
            return _unavailable("CONTEXT_UNAVAILABLE")
        if value == "1":
            environment[name] = "present"
    numeric = "".join(f"{name}='{fields[name]}'\n" for name in NUMERIC_KEYS if name in fields).encode("ascii")
    observed = summarize_apt_inputs(numeric, environment)
    if observed.get("available") is not True:
        return _unavailable(observed["unavailable_reason"])
    extra = {}
    for name in EXTRA_KEYS:
        if name not in fields:
            continue
        value = fields[name]
        if name == "APT_QUEUE_MODE":
            if value not in {"host", "access"}:
                return _unavailable("QUEUE_MODE_INVALID")
            extra[name] = value
        else:
            if value not in {"true", "false", "1", "0"}:
                return _unavailable("IP_MODE_INVALID")
            extra[name] = value in {"true", "1"}
    return {"status": "observed", "authority": "diagnostic_only", "credential_context": "installer_root_context",
            "apt": observed, "ip_and_queue": extra, "ip_and_queue_absent": sorted(set(EXTRA_KEYS) - set(extra)),
            "blindspots": ["resolved_network_endpoint", "effective_apt_proxy_configuration", "apt_get_exec_wrapper", "transfer_cause"]}


def summarize_mirror_list(raw: bytes) -> dict:
    if len(raw) > 8192:
        return _unavailable("MIRROR_INPUT_LIMIT")
    try:
        entries = []
        for line in raw.decode("ascii").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 2 or not parts[1].startswith("priority:"):
                return _unavailable("MIRROR_SHAPE")
            value = urlsplit(parts[0])
            if value.username or value.password or value.query or value.fragment or value.port:
                return _unavailable("MIRROR_UNQUALIFIED")
            identity = MIRRORS.get((value.scheme, value.hostname, value.path.rstrip("/") + "/"))
            priority = parts[1].removeprefix("priority:")
            if identity is None or not priority.isdecimal() or len(priority) > 6:
                return _unavailable("MIRROR_UNQUALIFIED")
            entries.append({"identity": identity, "priority": int(priority)})
        if not entries or len(entries) > 3 or len({e["identity"] for e in entries}) != len(entries):
            return _unavailable("MIRROR_SHAPE")
        return {"status": "observed", "authority": "diagnostic_only", "entries": entries,
                "selection": "image_mirror_list_only_not_selected_endpoint"}
    except (UnicodeError, ValueError):
        return _unavailable("MIRROR_UNQUALIFIED")


def _bounded_read(path: Path, limit: int) -> bytes:
    with path.open("rb") as source:
        return source.read(limit + 1)


def installed_playwright_inputs() -> dict:
    try:
        library = Path(sysconfig.get_path("purelib"))
        spec = importlib.util.find_spec("playwright")
        if spec is None or spec.origin is None or Path(spec.origin).resolve() != (library / "playwright/__init__.py").resolve():
            return _unavailable("MODULE_ORIGIN_UNQUALIFIED")
        metadata = list(library.glob("playwright-*.dist-info/METADATA"))
        if len(metadata) != 1:
            return _unavailable("DISTRIBUTION_AMBIGUOUS")
        package = library / "playwright/driver/package"
        observed = summarize_playwright_inputs(_bounded_read(metadata[0], 65536),
                                               _bounded_read(package / "package.json", 65536),
                                               _bounded_read(package / "lib/coreBundle.js", 8 * 1024 * 1024))
        return {**observed, "status": "observed" if observed["available"] else "unavailable"}
    except Exception:
        return _unavailable("SOURCE_READ_UNAVAILABLE")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("apt", "playwright"))
    args = parser.parse_args(argv)
    if args.mode == "apt":
        result = summarize_context_inputs(sys.stdin.buffer.read(8193))
        try:
            result["image_mirror_list"] = summarize_mirror_list(_bounded_read(Path("/etc/apt/apt-mirrors.txt"), 8192))
        except OSError:
            result["image_mirror_list"] = _unavailable("MIRROR_READ_UNAVAILABLE")
    else:
        result = installed_playwright_inputs()
    print("CI_BROWSER_DEPENDENCY_INPUTS=" + json.dumps(result, sort_keys=True))
    return 1 if result.get("status") == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
