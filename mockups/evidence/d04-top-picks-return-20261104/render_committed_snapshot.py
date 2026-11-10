#!/usr/bin/env python3
"""Reproduce the D04 local fixture from the pinned committed ranking page.

This evidence helper projects the template's control markup onto a committed
data snapshot. It does not compute scores, refresh data, or replace the ordinary
scripts/build_discovery.py production builder. Sparse checkouts lack its input
enrichment; running that builder here is not a qualified ranking-data rebuild.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "d18d83019f3972c9bd915c736210176c7bd0b6b5"
BASE_HTML_SHA256 = "2555f1bbccb192b90502a28381446a80ec0db89dafaebd8e2cf16122416263f6"
sys.path.insert(0, str(ROOT))
from engine.i18n import tr
from lib.site_assets import copy_asset
from scripts.optimize_assets import make_optimizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    base = subprocess.check_output(["git", "show", BASE + ":site/discovery.html"], cwd=ROOT).decode()
    assert hashlib.sha256(base.encode()).hexdigest() == BASE_HTML_SHA256
    source = base
    template = (ROOT / "templates/discovery.html.j2").read_text()

    def replace(old, new, count=1):
        nonlocal source
        assert source.count(old) == count, (old, source.count(old), count)
        source = source.replace(old, new)

    assert "2026-11-03" in base
    replace("<body>", '<body data-discovery-history="v1" data-discovery-asof="2026-11-03">')
    replace("</head>", '<link rel="stylesheet" href="discovery-controls.css">\n</head>')
    replace('<div class="tabs">', '<p id="discovery-return-status" class="panel muted sm" role="status" aria-live="polite" hidden></p>\n<div class="tabs" role="tablist" aria-label="Discovery views">')
    for tab in ("global", "sectors", "sector"):
        cls = "tabbtn on" if tab == "global" else "tabbtn"
        new = re.search(r'<button class="' + cls + r'"[^>]*data-tab="' + tab + r'"[^>]*>', template).group()
        replace('<button class="' + cls + '" data-tab="' + tab + '">', new)
        old = '<div id="tab-' + tab + '" data-grp="tab"' + (' style="display:none"' if tab != "global" else '') + '>'
        new = re.search(r'<div id="tab-' + tab + r'"[^>]*>', template).group()
        replace(old, new)
    marker = "<!-- TOP PICKS (global, ranked by conviction) -->"
    hint = re.search(r'<p id="discovery-table-help"[^>]*>.*?</p>', template).group()
    replace(marker, hint + "\n\n" + marker)
    replace('<div class="seg">', '<div class="seg" role="group" aria-label="Conviction ranking">')
    for side in ("strong", "weak"):
        cls = "segbtn on" if side == "strong" else "segbtn"
        new = re.search(r'<button class="' + cls + r'" id="seg-' + side + r'"[^>]*>', template).group()
        replace('<button class="' + cls + '" id="seg-' + side + '">', new)
    label = re.search(r'<label class="filt">.*?</label>', source, re.S).group()
    replace(label, label + '\n    <p id="discovery-filter-status" class="muted sm note" role="status"></p>')
    sector_label = re.search(r'<label for="secsel"[^>]*>.*?</label>', template).group()
    replace('<select id="secsel" class="secsel">', sector_label + '\n    <select id="secsel" class="secsel">')
    options = re.findall(r'<option value="(\d+)">([^<]+) \((\d+)\)</option>', source)
    assert len(options) == 11
    replace('<select id="secsel" class="secsel">\n      ', '<select id="secsel" class="secsel">\n      <option value="" data-label-en="Choose a sector" data-label-zh="选择板块">Choose a sector</option>\n      ')
    for index, sector, count in options:
        raw = html.unescape(sector)
        replace('<option value="' + index + '">' + sector + ' (' + count + ')</option>',
                '<option value="' + sector + '" data-label-en="' + sector + '" data-label-zh="' + html.escape(tr(raw), quote=True) + '" data-count="' + count + '"' + (' selected' if index == "0" else '') + '>' + sector + ' (' + count + ')</option>')
        old = '<div id="sec-' + index + '" data-grp="seclist"'
        replace(old, old + ' data-sector="' + sector + '"')

    start = source.index(marker)
    before, tail = source[:start], source[start:]
    assert tail.count("<table>") == tail.count("</table>") == 25
    wrapper = '<div class="discovery-scroll tbl-scroll" role="region" aria-label="Ranked data / 排名数据" tabindex="0">'
    tail = tail.replace("<table>", wrapper + "<table>").replace("</table>", "</table></div>")
    source = before + tail
    old_script = re.search(r'<script>\s*\(function\(\)\{\s*function show\(id, grp\).*?</script>', source, re.S).group()
    replace(old_script, '<script src="discovery.js"></script>')

    # Every ranked row and Buy zone byte remains the pinned source snapshot.
    assert re.findall(r"<tr(?:\s[^>]*)?>.*?</tr>", source, re.S) == re.findall(r"<tr(?:\s[^>]*)?>.*?</tr>", base, re.S)
    buy_start, buy_end = base.index('class="bz-strip"'), base.index('<div class="tabs">')
    buy = base[buy_start:buy_end]
    assert buy in source
    site = ROOT / "site"
    if args.write:
        for asset in ("discovery.js", "discovery-controls.css"):
            copy_asset(asset, ROOT / "templates" / asset, site)
    optimize = make_optimizer(site)
    for tag in ('<script src="discovery.js"></script>', '<link rel="stylesheet" href="discovery-controls.css">'):
        source = source.replace(tag, optimize(tag, site))
    if args.write:
        (site / "discovery.html").write_text(source)
    print(json.dumps({"base": BASE, "base_html_sha256": BASE_HTML_SHA256,
                      "output_sha256": hashlib.sha256(source.encode()).hexdigest(),
                      "sectors": len(options), "tables": 25,
                      "rows_and_buy_zone_unchanged": True, "written": args.write}))


if __name__ == "__main__":
    main()
