#!/usr/bin/env python3
"""SIC-V3-C06 check: Latin-script words on a rendered ZH document's FACE.

Reads a headless-Chrome --dump-dom file. Skips what the condition exempts or hides:
<nav>, <details> (provenance drawers), <code>, <script>, <style>, <svg>, <title>, <head>,
any element carrying the `hidden` attribute (not rendered; e.g. the composite desk outside board 40),
and any element whose class list contains l-en (hidden under html[data-lang=zh]).
Allowed tokens: tickers (XL?, FIX), SPY, MODEL, PRIOR; numerals never match [A-Za-z]{2,}; plus, with a
second argument, tokens from a names allow-file (one per line): the production zh basket names that
keep a Latin product term (AI, ETF, GLP-1) — sector/basket names are bilingual by the condition.
Usage: zh_latin_grep.py <dom.html> [allow.txt]   -> prints `zh-latin=<n>` and the offending tokens.
"""
import re, sys
from html.parser import HTMLParser
SKIP_TAGS = {"nav", "details", "code", "script", "style", "svg", "title", "head"}
ALLOW = re.compile(r"^(XL[A-Z]|FIX|SPY|MODEL|PRIOR)$")
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack = []; self.skip = 0; self.text = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); cls = a.get("class", "") or ""
        s = tag in SKIP_TAGS or "l-en" in cls.split() or "hidden" in a
        self.stack.append((tag, s)); self.skip += s
    def handle_endtag(self, tag):
        while self.stack:
            t, s = self.stack.pop(); self.skip -= s
            if t == tag: break
    def handle_data(self, data):
        if not self.skip: self.text.append(data)
p = P(); p.feed(open(sys.argv[1], encoding="utf-8").read())
extra = {l.strip() for l in open(sys.argv[2], encoding="utf-8") if l.strip() and not l.startswith("#")} if len(sys.argv) > 2 else set()
toks = re.findall(r"[A-Za-z][A-Za-z'’\-]+", " ".join(p.text))
bad = sorted({t for t in toks if not ALLOW.match(t) and t not in extra})
print(f"zh-latin={len(bad)}" + (" " + " ".join(bad[:40]) if bad else ""))
sys.exit(1 if bad else 0)
