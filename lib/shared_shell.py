"""The common HTML owner for the dormant Shared Shell document capability.

The bridge executes before page scripts so a framed document can retain its
local History state while the parent owns browser entries. The external asset is
content-versioned and otherwise follows the existing template/site asset owner.
"""
from __future__ import annotations

import hashlib
import logging
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


log = logging.getLogger(__name__)
MIN_BYTES = 1024  # smaller inline blocks are cheaper than a request
_JS_SUBDIR = ("assets", "js")
_SHARED_ROLES = ("theme", "onboard")
_SHARED_TAG_RE = re.compile(r"<script\b([^>]*)>(\s*)</script>", re.IGNORECASE)
SHARED_ROLE_RE = re.compile(r'\sdata-mmx-shared-bundle="(theme|onboard)"')
_SHARED_SRC_RE = re.compile(r'(?<![\w-])src\s*=\s*"([^"]*)"')
_SHARED_BINDING_RE = re.compile(r'\sdata-mmx-shared-(?:root|theme|onboard)="[^"]*"')
_SHARED_ALIAS_RE = re.compile(r"assets/js/([0-9a-f]{8})\.js\?v=\1")


def hashed_js_url(js_root: Path, data: bytes, *, write: bool = True) -> str | None:
    if len(data) < MIN_BYTES:
        return None
    h = hashlib.sha256(data).hexdigest()[:8]
    dst = js_root / f"{h}.js"
    if write and not dst.exists():
        try:
            js_root.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        except OSError as error:
            log.warning("write js %s failed: %s", dst.name, error)
            return None
    return f"assets/js/{h}.js?v={h}"


def shared_bundle_urls(site_dir: Path, js_root: Path, *, write: bool = True) -> dict[str, str]:
    """Bind both linked aliases to final, already-emitted public bundle bytes."""
    urls = {}
    for role in _SHARED_ROLES:
        try:
            raw = (site_dir / f"{role}.js").read_bytes()
            url = hashed_js_url(js_root, raw, write=write)
            if url is None or (site_dir / url.split("?", 1)[0]).read_bytes() != raw:
                return {}
        except OSError:
            return {}
        urls[role] = url
    return urls


def bind_shared_bundles(text: str, prefix: str, urls: dict[str, str]) -> str:
    """Rewrite explicitly marked classic tags and keep their timing/position."""
    bound_tags = 0

    def replace_tag(match):
        nonlocal bound_tags
        attrs, body = match.groups()
        role = SHARED_ROLE_RE.search(attrs)
        src = _SHARED_SRC_RE.search(attrs)
        if role is None or src is None or not src[1].startswith(prefix):
            return match[0]
        path = src[1][len(prefix):]
        if (not re.fullmatch(rf"{role[1]}\.js(?:\?v=[0-9a-f]{{8}})?", path)
                and not _SHARED_ALIAS_RE.fullmatch(path)):
            return match[0]
        bound_tags += 1
        attrs = attrs[:src.start(1)] + prefix + urls[role[1]] + attrs[src.end(1):]
        attrs = _SHARED_BINDING_RE.sub("", attrs)
        attrs += f' data-mmx-shared-root="{prefix or "./"}"'
        attrs += "".join(f' data-mmx-shared-{name}="{prefix}{urls[name]}"' for name in _SHARED_ROLES)
        return f"<script{attrs}>{body}</script>"

    updated = _SHARED_TAG_RE.sub(replace_tag, text)
    if bound_tags != len(SHARED_ROLE_RE.findall(text)):
        raise ValueError("malformed shared bundle script tag")
    return updated


def reconcile_shared_bundles(site_dir: Path, *, fix: bool = False) -> list[str]:
    """Rebind opted-in pages after the last named copy, or report mismatches read-only."""
    urls = None
    invalid = []
    for html in [site_dir / "forex.html", *sorted((site_dir / "learn").rglob("*.html"))]:
        if not html.is_file():
            continue
        rel = html.relative_to(site_dir)
        try:
            text = html.read_bytes().decode("utf-8")
            if not SHARED_ROLE_RE.search(text):
                continue
            if urls is None:
                urls = shared_bundle_urls(site_dir, site_dir.joinpath(*_JS_SUBDIR), write=fix)
            if not urls:
                invalid.append(rel.as_posix())
                continue
            bound = bind_shared_bundles(text, "../" * (len(rel.parts) - 1), urls)
            if bound != text:
                if fix:
                    # The finalized page already carries its shim and other stamps.
                    html.write_bytes(bound.encode("utf-8"))
                else:
                    invalid.append(rel.as_posix())
        except (OSError, ValueError):
            invalid.append(rel.as_posix())
    return invalid
