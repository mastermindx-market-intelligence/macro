#!/usr/bin/env python3
"""SIC-V3-C06 check: Latin-script words on a rendered ZH document's FACE — scope fixed by SIC-ADJ-03 (wave 5; SIC-V5-C04/C05/C06).

Reads a headless-Chrome --dump-dom file. Skipped WHOLESALE (nothing inside is ever counted, inside <code> or not):
  <details>  — the provenance drawers, where every identifier a face must reference lives (now.phase, phase_v2, dataset
               keys, the render sha, the capture tool); the face names the clocks in plain words instead;
  <nav>, <script>, <style>, <svg>, <title>, <head>;
  any element carrying the `hidden` attribute (not rendered; e.g. the composite desk outside boards 40/41);
  any element whose class list contains l-en (hidden under html[data-lang=zh]).
Nothing else is skipped by tag: a <code> identifier on the face COUNTS (wave 4 skipped <code> everywhere; SIC-ADJ-03 ends that).
Exempted tokens: ALLOW (unchanged since wave 3) — tickers XL?, FIX, SPY, MODEL, PRIOR — plus, with a second argument, the tokens
of a names allow-file (one per line): brief_repair/zh_face_latin_allow.txt carries AI, GLP-1, ETF from the production zh basket
names and deck copy; the Cycles boards run with no allow-file. Tokenizer (SIC-V4-C05): a letter-led run with digits, ', ’, -
and .digits — W5.1, P(...), GLP-1 are tokens; a lone letter counts.
Output: `zh-latin=<n> [offending tokens] skip=<tags above> code-on-face=counts allow=<ALLOW>[+<allow-file tokens>]`, so a
capture.log line that claims zh-latin=0 states the scope it was measured under and the tokens it exempted. Exit 1 if any offend.
Usage: zh_latin_grep.py <dom.html> [allow.txt]
"""
import re, sys
from html.parser import HTMLParser
SKIP_TAGS = {"nav", "details", "script", "style", "svg", "title", "head"}  # SIC-ADJ-03: no "code" — a <code> on the face counts
ALLOW = re.compile(r"^(XL[A-Z]|FIX|SPY|MODEL|PRIOR)$")  # unchanged (SIC-V5-C04)
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
# SIC-V4-C05: letter-plus-digit and letter-plus-punctuation tokens (W5.1, P(...), GLP-1) are tokens too; a lone letter counts.
toks = re.findall(r"[A-Za-z][A-Za-z0-9'’\-]*(?:\.[0-9]+)*", " ".join(p.text))
bad = sorted({t for t in toks if not ALLOW.match(t) and t not in extra})
scope = "skip=details(wholesale),nav,script,style,svg,title,head,[hidden],.l-en code-on-face=counts allow=XL?,FIX,SPY,MODEL,PRIOR" + ("+" + ",".join(sorted(extra)) if extra else "")
print(f"zh-latin={len(bad)}" + (" " + " ".join(bad[:40]) if bad else "") + " " + scope)
sys.exit(1 if bad else 0)
