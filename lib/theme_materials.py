"""Stdlib-only export of the canonical neutral CSS, shared by emitter and publish guard.

No palette lives here. The authoring source remains templates/theme.css. Keeping
this reader free of configuration/YAML lets the stripped-down publisher validate
that standalone pages receive the exact same material rules as stylesheet pages.
"""
from __future__ import annotations

from pathlib import Path

SOFT_CONTRAST_TOKEN = "/*__SOFT_CONTRAST_CSS__*/''"


def shared_contrast_css(src: Path) -> str:
    """Export the canonical CSS block; a missing/ambiguous source is a build error."""
    css = src.with_name("theme.css").read_text(encoding="utf-8")
    start = "/* BEGIN SHARED_CONTRAST_CSS"
    end = "/* END SHARED_CONTRAST_CSS */"
    if css.count(start) != 1 or css.count(end) != 1:
        raise ValueError("theme.css must contain exactly one SHARED_CONTRAST_CSS block")
    before, block = css.split(start, 1)
    if end in before:
        raise ValueError("SHARED_CONTRAST_CSS markers are out of order")
    block = start + block.split(end, 1)[0] + end
    if "html.soft-contrast" not in block or "--panel:" not in block:
        raise ValueError("SHARED_CONTRAST_CSS contains no shared material rules")
    return block
