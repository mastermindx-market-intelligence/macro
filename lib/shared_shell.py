"""The common HTML owner for the dormant Shared Shell document capability.

The bridge executes before page scripts so a framed document can retain its
local History state while the parent owns browser entries. The external asset is
content-versioned and otherwise follows the existing template/site asset owner.
"""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path

DOCUMENT_VERSION = "20261018.1"
ASSET_NAME = "shared_shell_bridge.js"
STYLESHEET_NAME = "shared_shell.css"
ROOT = Path(__file__).resolve().parent.parent
START = "<!-- mmx-shared-shell:start -->"
END = "<!-- mmx-shared-shell:end -->"
BLOCK = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)


class _HeadFound(Exception):
    pass


class _DocumentHead(HTMLParser):
    """Find a real document head without matching markup inside a script/comment."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.document = False
        self.position = None
        self.tag_length = 0

    def handle_decl(self, decl):
        if decl.lower().strip().startswith("doctype html"):
            self.document = True

    def handle_starttag(self, tag, attrs):
        if tag == "html":
            self.document = True
        if tag == "head" and self.document:
            self.position = self.getpos()
            self.tag_length = len(self.get_starttag_text())
            raise _HeadFound


def _head_end(html: str) -> int | None:
    parser = _DocumentHead()
    try:
        parser.feed(html)
    except _HeadFound:
        pass
    if parser.position is None:
        return None
    line, column = parser.position
    offset = 0
    for _ in range(line - 1):
        offset = html.index("\n", offset) + 1
    return offset + column + parser.tag_length


@lru_cache(maxsize=8)
def asset_version(site_dir: Path | None = None) -> str:
    emitted = (site_dir or ROOT / "site") / ASSET_NAME
    asset = emitted if emitted.is_file() else ROOT / "templates" / ASSET_NAME
    return hashlib.sha256(asset.read_bytes()).hexdigest()[:8]


@lru_cache(maxsize=8)
def stylesheet_version(site_dir: Path | None = None) -> str:
    emitted = (site_dir or ROOT / "site") / STYLESHEET_NAME
    asset = emitted if emitted.is_file() else ROOT / "templates" / STYLESHEET_NAME
    return hashlib.sha256(asset.read_bytes()).hexdigest()[:8]


def copy_shared_shell_asset(site_dir: Path) -> None:
    from lib.site_assets import copy_asset

    for name in (ASSET_NAME, STYLESHEET_NAME):
        copy_asset(name, ROOT / "templates" / name, site_dir)
    asset_version.cache_clear()
    stylesheet_version.cache_clear()


@lru_cache(maxsize=8)
def ensure_shared_shell_asset(site_dir: Path | None = None) -> None:
    # Standalone sentinels do not own a refresh of existing tracked assets.
    site = site_dir or ROOT / "site"
    if site.is_dir():
        from lib.site_assets import copy_asset

        for name in (ASSET_NAME, STYLESHEET_NAME):
            if not (site / name).exists():
                copy_asset(name, ROOT / "templates" / name, site)
                asset_version.cache_clear()
                stylesheet_version.cache_clear()


def inject_shared_shell_text(html: str, prefix: str = "", *, version: str | None = None,
                             site_dir: Path | None = None, response_kind: str = "content",
                             css_version: str | None = None) -> str:
    """Add/update only the owned capability block; fragments stay byte-identical."""
    if prefix != "/" and not re.fullmatch(r"(?:\.\./)*", prefix):
        raise ValueError("Shared Shell asset prefix must be depth-relative or site-root-relative")
    if response_kind not in {"content", "coming_soon"}:
        raise ValueError("Unknown Shared Shell response kind")
    if START in html or END in html:
        if html.count(START) != 1 or html.count(END) != 1 or not BLOCK.search(html):
            raise ValueError("Ambiguous Shared Shell capability block")
        html = BLOCK.sub("", html, count=1)
    at = _head_end(html)
    if at is None:
        return html
    if version is None:
        ensure_shared_shell_asset(site_dir)
    value = version if version is not None else asset_version(site_dir)
    if not re.fullmatch(r"[0-9a-f]{8}", value):
        raise ValueError("Shared Shell asset version must be a content digest")
    css_value = css_version if css_version is not None else stylesheet_version(site_dir)
    if not re.fullmatch(r"[0-9a-f]{8}", css_value):
        raise ValueError("Shared Shell stylesheet version must be a content digest")
    if re.search(r'<meta\b[^>]*\bname\s*=\s*["\']mmx-shell-(?:document|response)["\']', html, re.I):
        raise ValueError("Shared Shell document marker exists outside its owner block")
    block = (
        START
        + '<meta name="mmx-shell-document" content="' + DOCUMENT_VERSION + '">'
        + '<meta name="mmx-shell-response" content="' + response_kind + '">'
        + '<link rel="stylesheet" data-mmx-shared-shell-styles="' + DOCUMENT_VERSION
        + '" href="' + prefix + STYLESHEET_NAME + '?v=' + css_value + '">'
        + '<script data-sync data-mmx-shared-shell-bridge="' + DOCUMENT_VERSION
        + '" src="' + prefix + ASSET_NAME + '?v=' + value + '"></script>'
        + END
    )
    return html[:at] + block + html[at:]
