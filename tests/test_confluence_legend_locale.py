"""Regression guard for Confluence ribbon labels in the English and Chinese UI.

The CSS legend layout belongs to its direct children. If the selector reaches
nested .l-en/.l-zh spans, it overrides theme.css locale visibility and shows
both translations simultaneously.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("sector_central.html", "sector_central.html.j2", "#si-confluence .sc-ribbon-legend"),
    ("subsectors.html", "subsectors.html.j2", ".sc-ribbon-legend"),
]


@pytest.mark.parametrize("page,template,selector", CASES)
def test_confluence_ribbon_legend_layout_is_direct_child_only(page, template, selector):
    template_css = (ROOT / "templates" / template).read_text(encoding="utf-8")
    narrow_rule = selector + " > span {"
    broad_rule = selector + " span {"

    assert narrow_rule in template_css
    assert broad_rule not in template_css


@pytest.mark.parametrize("page,template,selector", CASES)
def test_built_confluence_page_references_fixed_content_hashed_stylesheet(page, template, selector):
    html = (ROOT / "site" / page).read_text(encoding="utf-8")
    hashes = re.findall(r"assets/css/([0-9a-f]{8})\.css\?v=\1", html)
    assert hashes

    matching = []
    for digest in set(hashes):
        asset = ROOT / "site/assets/css" / (digest + ".css")
        data = asset.read_bytes()
        assert hashlib.sha256(data).hexdigest()[:8] == digest
        css = data.decode("utf-8")
        if selector + " > span {" in css:
            matching.append(css)
    assert len(matching) == 1
    assert selector + " span {" not in matching[0]


def test_theme_locale_visibility_still_has_priority_over_nested_legend_labels():
    theme_css = (ROOT / "site/theme.css").read_text(encoding="utf-8")
    js = (ROOT / "templates/subsectors.js").read_text(encoding="utf-8")
    assert 'html:not([data-lang="zh"]) .l-zh { display: none; }' in theme_css
    assert 'html[data-lang="zh"] .l-en { display: none; }' in theme_css
    assert '<span class="l-en">' in js
    assert '<span class="l-zh">' in js
