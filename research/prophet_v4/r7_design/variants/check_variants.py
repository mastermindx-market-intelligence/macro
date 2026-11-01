#!/usr/bin/env python3
"""Static checks for the Prophet R7 decision-line design variant references.

Stdlib only. Parses each variant HTML file with html.parser (tag balance)
and enforces the FROZEN SPEC rules that are checkable as text.
"""
from html.parser import HTMLParser
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent

FILES = [
    "decision-strip/1.html",
    "decision-strip/2.html",
    "decision-strip/3.html",
    "receipt-shelf/1.html",
    "lens-switcher/1.html",
]

STRIP_FILES = {"decision-strip/1.html", "decision-strip/2.html", "decision-strip/3.html"}

SLOT_NAMES = [
    ("Company", "公司"),
    ("Current decision", "当前决策"),
    ("Timing", "时机"),
    ("What ends it", "失效条件"),
    ("Lens", "策略"),
]

REQUIRED_SUBSTRINGS = [
    "tabular-nums",
    ":focus-visible",
    "prefers-color-scheme: dark",
    '[data-theme="dark"]',
]

FORBIDDEN_SUBSTRINGS = [
    "border-left",
    "border-right",
    "border-top-color",
    "text-transform: uppercase",
    "monospace",
    "→",  # arrow character
    " · ",  # spaced middle dot
]

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
    "circle", "line", "path", "polygon", "polyline", "rect",
}


class BalanceParser(HTMLParser):
    """html.parser pass that flags unbalanced or out-of-order tags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.problems = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
            return
        self.problems.append(
            "unexpected </%s> (open stack tail: %s)" % (tag, self.stack[-3:])
        )
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()


def check_file(path: Path, is_strip: bool):
    errors = []
    text = path.read_text(encoding="utf-8")

    for needle in REQUIRED_SUBSTRINGS:
        if needle not in text:
            errors.append("missing required substring: %r" % needle)

    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in text:
            errors.append("forbidden substring present: %r" % bad)

    parser = BalanceParser()
    parser.feed(text)
    parser.close()
    for problem in parser.problems:
        errors.append("tag balance: " + problem)
    if parser.stack:
        errors.append("tag balance: unclosed tags %s" % parser.stack)
    for required_root in ("html", "head", "body"):
        if ("<%s" % required_root) not in text:
            errors.append("missing root element <%s>" % required_root)

    if is_strip:
        for en, zh in SLOT_NAMES:
            if en not in text:
                errors.append("missing EN slot name: %r" % en)
            if zh not in text:
                errors.append("missing ZH slot name: %r" % zh)

    return errors


def main() -> int:
    failures = 0
    for rel in FILES:
        path = HERE / rel
        if not path.is_file():
            print("FAIL %s: file missing" % rel)
            failures += 1
            continue
        errors = check_file(path, rel in STRIP_FILES)
        if errors:
            failures += 1
            for err in errors:
                print("FAIL %s: %s" % (rel, err))
        else:
            print("PASS %s" % rel)
    if failures:
        print("CHECK FAILED: %d file(s) with problems" % failures)
        return 1
    print("CHECK OK: %d files passed" % len(FILES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
