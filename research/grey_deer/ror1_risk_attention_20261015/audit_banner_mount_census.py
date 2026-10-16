"""ROR-1 offline static-site market-alert mount census.

This is NOT a browser/entitlement check or a warning publisher. It checks the
committed HTML source that was actually selected by a caller for the existing
wh_banner.js client. Do not infer executable or deployed state from a token
found in documentation, copied text, or an unrelated script.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable


class MountAuditError(ValueError):
    pass


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts: list[list[tuple[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "script":
            self.scripts.append(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _paths(values: Any, label: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 16:
        raise MountAuditError(f"{label}: expected bounded file sequence")
    checked = []
    for value in values:
        if (not isinstance(value, str) or len(value) > 160
                or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.html", value)):
            raise MountAuditError(f"{label}: invalid HTML relative path")
        parts = PurePosixPath(value).parts
        if not parts or any(part in ("..", ".") for part in parts):
            raise MountAuditError(f"{label}: cannot escape source directory")
        checked.append(value)
    if len(set(checked)) != len(checked):
        raise MountAuditError(f"{label}: duplicate input paths")
    return tuple(checked)


def _check(page: Path, relative: str) -> dict:
    if not page.is_file():
        return {"state": "SOURCE_FILE_MISSING", "valid_mounts": 0,
                "candidate_scripts": 0, "source_sha256": None}
    raw = page.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise MountAuditError("source page exceeded static audit byte limit")
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MountAuditError("source file is not UTF-8") from exc
    parser = _Scripts()
    parser.feed(html)
    parser.close()
    depth = len(PurePosixPath(relative).parts) - 1
    expected_prefix = "../" * depth
    valid, candidates, invalid = 0, 0, 0
    for attrs in parser.scripts:
        d = dict(attrs)
        src = d.get("src") or ""
        has_marker = "data-whb" in d
        references_client = "wh_banner.js" in src
        if not (has_marker or references_client):
            continue
        candidates += 1
        if len(d) != len(attrs):
            invalid += 1
            continue
        expected = re.compile(
            r"^" + re.escape(expected_prefix) + r"wh_banner\.js(?:\?v=[0-9a-f]{6,32})?$"
        )
        if (has_marker and "defer" in d and d.get("data-root") == expected_prefix
                and expected.fullmatch(src)):
            valid += 1
        else:
            invalid += 1
    if candidates > 1:
        state = "DUPLICATE_MOUNT"
    elif invalid:
        state = "INVALID_MOUNT"
    elif valid == 1:
        state = "MOUNTED"
    else:
        state = "UNMOUNTED"
    return {"state": state, "valid_mounts": valid,
            "candidate_scripts": candidates,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_bytes": len(raw),
            "expected_root_prefix": expected_prefix}


def audit_mounts(
    root: Path | str,
    core: Iterable[str],
    controls: Iterable[str] = (),
) -> dict:
    """Classify source-only mount evidence on an explicit bounded page universe.

    Must not be used as proof of server deployment, a refreshed long-open tab,
    backend alert selection, issue-time publication or customer notification.
    """
    c = _paths(core, "core")
    v = _paths(controls, "controls")
    if not c or len(c) + len(v) > 16 or set(c) & set(v):
        raise MountAuditError("invalid or duplicate census universe")
    base = Path(root).resolve()
    if not base.is_dir():
        raise MountAuditError("source root missing")
    pages = {}
    for rel in c + v:
        path = base / rel
        if not path.resolve(strict=False).is_relative_to(base):
            raise MountAuditError("source page resolves outside source root")
        pages[rel] = _check(path, rel)
    missing = [rel for rel in c if pages[rel]["state"] != "MOUNTED"]
    invalid = [rel for rel, row in pages.items()
               if row["state"] in ("INVALID_MOUNT", "DUPLICATE_MOUNT")]
    status = ("DUPLICATE_OR_INVALID_ALERT_MOUNT" if invalid
              else "CORE_ALERT_CLIENT_UNMOUNTED_IN_SITE_SOURCE" if missing
              else "CORE_SITE_SOURCE_MOUNTED")
    return {
        "schema": "ror1.alert_script_source_mount_census.v1",
        "status": status,
        "core_all_mounted": not missing,
        "core_missing": missing,
        "mounts_observed": sum(row["valid_mounts"] for row in pages.values()),
        "invalid_source_mounts": invalid,
        "pages": pages,
        "installed_browser_proven": False,
        "alert_payload_qualified": False,
        "authenticated_user_delivery_proven": False,
        "note": ("Source-only static <script> syntax. No proof of served site, "
                 "script runtime, risk alert, source freshness, or notification."),
    }
