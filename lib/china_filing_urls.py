"""Shared display-only CNInfo source URL normalization; no network or collection."""
from __future__ import annotations

import re

_CNINFO_STATIC_BASE = "https://static.cninfo.com.cn/"
_CNINFO_RELATIVE_PATH = re.compile(r"^finalpage/[A-Za-z0-9._/-]+$")


def cninfo_source_url(adjunct_url: str | None) -> str | None:
    """Expose the supplied CNInfo path without accepting arbitrary outbound URLs."""
    raw = str(adjunct_url or "").strip()
    if not raw or "://" in raw or "\\" in raw or ".." in raw:
        return None
    if any(ord(ch) < 32 for ch in raw):
        return None
    rel = raw.lstrip("/")
    if not _CNINFO_RELATIVE_PATH.fullmatch(rel):
        return None
    return _CNINFO_STATIC_BASE + rel
