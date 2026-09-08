#!/usr/bin/env python3
"""scripts/check_macro_command_copy.py — Macro Command copy guard.

Frozen spec (F01 Macro Command, 2026-09-06) §5 "Copy law" + §9 P1 acceptance:
Macro Command (`site/macro_monetary.html`) is the single customer-facing
dashboard for the fourteen `macro_*` research workspaces, and the FRONT-END
CLARITY LAW (CLAUDE.md "Design (user-first law)") forbids machine text — raw
slugs, internal state/study names, untranslated stat names, bare timestamps —
anywhere a non-quant reader's eye lands. G2 makes that mechanically true:
zero occurrences of the banned vocabulary OUTSIDE a
`<details class="mc-details">` subtree or a `class="mc-primer"` body, in
either theme or language. G2b adds one more shape: no bare `YYYY-MM-DD` /
`YYYY-MM-DDTHH:MM` in visible text without an immediately preceding plain
word — every as-of the page shows must read "Data to 3 Sep 2026" /
"数据截至 2026年9月3日" in the TEXT, with the machine value living only in
`datetime=`.

This guard ships in P1 (frozen spec §9 P1 standing note: "the guard ships in
P1, not at the end, because a customer-visible page that is ungated against
the FRONT-END CLARITY LAW cannot lawfully be reviewed PASS") even though P1
itself ships no stance/primer/Read/chip copy — later packets (P2-P5) populate
that copy and this guard is what keeps it honest as it lands.

Usage:
    python3 scripts/check_macro_command_copy.py
        # scan every suite page + both hubs; exit 1 on any violation
    python3 scripts/check_macro_command_copy.py path/to/some.html
        # scan one or more built HTML files (used by the test suite
        # against a freshly rendered page in a tmp_path)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS_PATH = ROOT / "lib" / "macro_suite_labels.py"
sys.path.insert(0, str(ROOT))


def default_targets() -> list[Path]:
    """Every suite page plus the Macro Command hub (n1)."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SUITE_PAGES
    names = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    return [ROOT / "site" / name for name in names]

# §5's banned-substring CI list, verbatim from the frozen spec's table
# footer. Case-sensitive and taken literally — the spec lists both cases of
# a word ("axis"/"Axis", "vector"/"Vector") exactly where it wants both
# banned, and leaves the other case alone where it does not.
BANNED_SUBSTRINGS: tuple[str, ...] = (
    "accepted print", "accepted snapshot", "method version", "method-comparable",
    "hysteresis", "axis", "Axis", "authority ceiling", "content hash",
    "generation id", "producer", "artifact", "manifest", "trace_ref",
    "definition_id", "owner_ref", "standardized", "Diagnostics", "Vector",
    "vector", "snapshot", "deterministic", "schema", "Regime map", "Freshness",
    "Presence", "coverage_ratio", "null_reason",
)

# Falsifier/refutation vocabulary is never front-facing (CLAUDE.md "Design
# (user-first law)", #3821 — tripwires keep evaluating in the background,
# but user surfaces never say "falsifier fired / thesis refuted / 证伪").
# Not itself a row in the frozen spec's §5 table, but exactly the shape of
# internal-study-name leak G2 exists to catch, and named explicitly in this
# packet's own commission.
FALSIFIER_SUBSTRINGS: tuple[str, ...] = ("falsifier", "refuted", "证伪")

# G2b — no bare timestamp in visible text. A YYYY-MM-DD with no immediately
# preceding plain word (a letter followed by a space), or any ISO
# "T\d\d:\d\d" fragment at all — the datetime separator has no legitimate
# reason to reach visible text; the machine value belongs only in
# `datetime=`, which tag-stripped visible text never sees in the first place.
# One-or-more whitespace (space or NBSP) after a letter: the emitted markup
# is `<span>Data to</span> <time>…</time>`, so after tags are stripped the
# word and the date are still separated by whitespace. A single-character
# lookbehind (`[A-Za-z一-鿿][ ]`) cannot see that shape.
_BARE_DATE_RE = re.compile(r'(?<![A-Za-z\u4e00-\u9fff]\s)\d{4}-\d{2}-\d{2}')
_ISO_TIME_RE = re.compile(r'T\d{2}:\d{2}')
_WS_RE = re.compile(r'[\s\u00a0]+')
# P5 v9 E-m3: raw machine floats never reach the reading path.
_MACHINE_FLOAT_RE = re.compile(
    r'(?<![\d.])[+\u2212-]?\d+\.\d{4,}(?![\d])'
    r'|[+\u2212-]?\d+\.?\d*[eE][+\-]\d+'
)
# P5 v10 E-m1: painted bilingual copy may not leak slugs / study ids.
_SNAKE_RE = re.compile(r"[a-z]+_[a-z_]+")
_RULE_ID_RE = re.compile(r"\bR\d[A-Z]?\b|\bF\d{2}\b")
_BRACE_RE = re.compile(r"[{}]")
_PARQUET_RE = re.compile(r"\bparquets?\b", re.I)
# Enumerated — no wildcard. Tickers / ISO / proper nouns that match a shape.
MACHINE_TEXT_EXCEPTIONS: frozenset[str] = frozenset({
    "FRED", "FOMC", "SOFR", "TIPS", "OECD", "NBER", "HICP", "VIX",
    "CPI", "GDP", "NFCI", "OFR", "BLS", "ECB", "BOJ", "TGA", "USD",
    "US", "EU", "JP", "CN", "GB",
})

# Strip only the <details> BODY (children after <summary>). The summary
# is painted while closed, so the predicate must see it (P5 r4 m-b).
_DETAILS_RE = re.compile(
    r'(<details\b[^>]*>\s*<summary\b[^>]*>.*?</summary>)(.*?)(</details>)',
    re.S,
)
_PRIMER_RE = re.compile(r'<details\s+class="mc-primer"[^>]*>.*?</details>', re.S)
_SCRIPT_RE = re.compile(r'<script\b[^>]*>.*?</script>', re.S)
_TAG_RE = re.compile(r'<[^>]+>')

# Every ALL-CAPS closed-vocabulary dict key in lib/macro_suite_labels.py
# (§5 row 61: "CURRENT", "WARMUP", "SOURCE_FAILED", ... — "must never reach
# screen"). Matched as a dict-key assignment line so a stray all-caps English
# word elsewhere in the module's prose docstrings is never mistaken for a
# closed-vocabulary token.
_LABEL_TOKEN_RE = re.compile(r'^\s*"([A-Z][A-Z0-9_]{2,})":\s', re.M)


def _closed_vocabulary_tokens() -> tuple[str, ...]:
    """Read the closed-vocabulary tokens from source rather than duplicating
    them by hand, so the guard tracks `lib/macro_suite_labels.py` as it grows
    in P2+. Returns an empty tuple (never raises) if the module cannot be
    read — a missing file is a different, louder failure elsewhere."""
    try:
        text = LABELS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ()
    return tuple(sorted(set(_LABEL_TOKEN_RE.findall(text))))


def reading_path_text(html: str) -> str:
    """The page's reading path: the built HTML with every `<script>`,
    `<details class="mc-details">` and `<details class="mc-primer">`
    subtree removed (G2 — those are the two places machine text and primer
    copy may legitimately live), then every remaining tag stripped so
    attribute values (`id=`, `href=`, `datetime=`) never feed the
    banned-substring or bare-timestamp scan — only what a reader actually
    sees does."""
    stripped = _SCRIPT_RE.sub("", html)
    stripped = _DETAILS_RE.sub(r"\1\3", stripped)
    stripped = _PRIMER_RE.sub("", stripped)
    # Tags become empty, not a space: the page emits the plain word and the
    # date in sibling elements (`<span class="mc-asof-word">Data to</span>
    # <time>…</time>`), and a space-per-tag would break G2b's lookbehind
    # between the word and the date (Opus review PR #6930 B2).
    stripped = _TAG_RE.sub("", stripped)
    return _WS_RE.sub(" ", stripped)


def locale_span_texts(html: str) -> list[tuple[str, str]]:
    """Visible ``.l-en`` / ``.l-zh`` bodies, including details (E-m1)."""
    stripped = _SCRIPT_RE.sub("", html)
    found: list[tuple[str, str]] = []
    for locale in ("en", "zh"):
        for raw in re.findall(
                rf'<span class="l-{locale}">(.*?)</span>', stripped, re.S):
            text = _TAG_RE.sub("", raw)
            text = _WS_RE.sub(" ", text).strip()
            if text:
                found.append((locale, text))
    return found


def machine_copy_hits(text: str) -> list[str]:
    """Front-facing machine-text shapes (E-m1). Empty means the string is plain."""
    if not text:
        return []
    hits: list[str] = []
    if _BRACE_RE.search(text):
        hits.append("braces")
    for match in _SNAKE_RE.finditer(text):
        token = match.group(0)
        if token not in MACHINE_TEXT_EXCEPTIONS:
            hits.append(f"snake:{token}")
    if _PARQUET_RE.search(text):
        hits.append("parquet")
    for match in _RULE_ID_RE.finditer(text):
        token = match.group(0)
        if token not in MACHINE_TEXT_EXCEPTIONS:
            hits.append(f"rule:{token}")
    return hits


def find_violations(html: str) -> list[str]:
    """Return every copy-law violation found in `html`'s reading path. An
    empty list means the page is clean."""
    text = reading_path_text(html)
    violations: list[str] = []

    banned = BANNED_SUBSTRINGS + FALSIFIER_SUBSTRINGS + _closed_vocabulary_tokens()
    for phrase in banned:
        if phrase in text:
            violations.append(
                f"banned phrase {phrase!r} found in the reading path (outside "
                "mc-details/mc-primer) — move it into <details class=\"mc-details\"> "
                "or replace it with the plain-word copy from spec §5"
            )

    for match in _BARE_DATE_RE.finditer(text):
        violations.append(
            f"bare timestamp {match.group(0)!r} in visible text with no preceding "
            "plain word (G2b) — prefix it (\"Data to\" / \"数据截至\") in the visible "
            "text; the machine value belongs only in datetime="
        )

    for match in _ISO_TIME_RE.finditer(text):
        violations.append(
            f"raw ISO time fragment {match.group(0)!r} in visible text (G2b) — "
            "no ISO datetime separator belongs in what a reader sees"
        )

    # Tag-stripped bilingual twins (`18.83` + `18.83`) must not glue into a
    # false 4-decimal token. Scan the same reading path with a space per tag.
    # Drop <time> bodies so ISO fractional seconds are not mistaken for
    # machine floats (those are already G2b-gated).
    float_html = re.sub(r"<time\b[^>]*>.*?</time>", " ", html, flags=re.S)
    spaced = _TAG_RE.sub(" ", _PRIMER_RE.sub(
        "", _DETAILS_RE.sub(r"\1\3", _SCRIPT_RE.sub("", float_html))))
    spaced = _WS_RE.sub(" ", spaced)
    for match in _MACHINE_FLOAT_RE.finditer(spaced):
        token = match.group(0)
        violations.append(
            f"raw machine float {token!r} in visible text (E-m3) — "
            "format momentum/z-scores to 2 decimals and percentages to 1 decimal "
            "with a unit at the builder/renderer boundary"
        )

    for locale, span in locale_span_texts(html):
        for hit in machine_copy_hits(span):
            snippet = span[:80]
            violations.append(
                f"machine-text {hit!r} in .{locale} span {snippet!r} "
                "(E-m1) — replace with plain words a customer can read"
            )

    return violations


def check_file(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path} does not exist — build the page first"]
    html = path.read_text(encoding="utf-8")
    return find_violations(html)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "targets", nargs="*",
        help="built HTML pages to scan (default: every suite page + both hubs)",
    )
    args = parser.parse_args(argv)

    paths = [Path(item) for item in args.targets] if args.targets else default_targets()
    scanned = [str(path) for path in paths]
    violations: list[str] = []
    for path in paths:
        for item in check_file(path):
            violations.append(f"{path.name}: {item}")
    if violations:
        for violation in violations:
            # House law: a GitHub annotation must START the line, so this is
            # a bare print, never a logger call (CLAUDE.md "GitHub
            # annotations must START the line").
            print(f"::error title=macro-command-copy-law::{violation}", flush=True)
        print(
            f"macro command copy guard: {len(violations)} violation(s) in "
            f"{len(scanned)} page(s): {', '.join(Path(p).name for p in scanned)}",
            file=sys.stderr,
        )
        return 1

    print(
        f"macro command copy guard: clean "
        f"({len(scanned)} pages: {', '.join(Path(p).name for p in scanned)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
