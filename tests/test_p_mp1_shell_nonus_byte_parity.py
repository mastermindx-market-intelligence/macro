"""P-MP1-SHELL §7/§11/§12 item 3 — non-US byte-parity proof.

MP-1-prophet-board.md §7: "Other markets: hk/china/canada/intl keep the legacy
rail via the pv_card parameter default (ruling §10.2) — zero rendered-byte
change on non-US pages, test-pinned." §12 acceptance item 3: "The pv_card
lifecycle parameter defaults to legacy: non-US templates render byte-identical."

The ONLY file this packet's diff shares with hk.html.j2/china.html.j2/
canada.html.j2/intl.html.j2 is templates/_prophet_card.html.j2 (each of those
four does `{% import "_prophet_card.html.j2" as pv %}` then calls
`pv.pv_css()` once and `pv.pv_card(cx)` per row, with NO `lifecycle`/`id`/
`life`/`lane_mark` keys — every existing non-US call site). This suite proves,
against origin/main's pre-migration copy of that file:

  1. B1 MERGE-SAFETY FIX (2026-09-01 repair round 1, independent code review):
     items 1 and 2 below USED TO diff each file against `git merge-base
     origin/main HEAD` and assert a specific NON-EMPTY diff shape (an itemized
     added-date-rollout pin, or a 2-line pv_css() pin). That mechanism
     self-destructs the moment this PR merges: once `origin/main` contains
     this branch's commits, the merge-base of a later checkout IS (or
     descends past) this branch's own HEAD, so `_origin_main_text()` reads
     back the SAME post-rollout content `cur` already holds — the computed
     diff collapses to empty, and an assertion that expects a non-empty,
     itemized diff goes red forever. Fixed by dropping merge-base diffing
     entirely for the two tests that assert a SPECIFIC diff shape: they now
     pin exact SHA-256 hashes of the CURRENT (post-rollout) raw file bytes —
     no diffing, no historical baseline, no leniency of any kind (not
     comment-stripped, not sorted-line-set matched — literal bytes). A
     future legitimate edit to any of these five surfaces must recompute and
     update its pin by hand; that friction IS the guard's job — unrelated
     drift (or a bug that silently changes shared markup) breaks the pin
     without needing to know or care where `origin/main` currently sits.

     R6 CORRECTION (2026-09-01 repair round 3, independent repair-delta
     review): round 1's docstring claimed "`_merge_base()`/`_origin_main_
     text()` remain in use below ONLY by the pv_card()-output-equality test
     and the stocktable.js diff test, which both assert 'no diff at all' /
     a PRE-EXISTING (unrelated) shape rather than a rollout-specific
     non-empty diff — see their own docstrings for why those two are
     unaffected by this failure mode." That claim was FALSE for the
     stocktable.js diff test specifically, and round 1 never verified it:
     `test_stocktablejs_diff_is_exactly_the_two_additive_stagefilter_guards`
     asserted `hunk_count == 2` against `git diff -U0 $MERGE_BASE --
     templates/stocktable.js` — a SPECIFIC non-empty diff shape, the exact
     pattern item 1 warns about, not a "no diff at all" equality check. It
     was red on this exact head in CI pack 9: templates/stocktable.js's git
     blob (f8145bd6fb4ed0adba5f34b5c97a7895b7332f2e) is IDENTICAL at
     origin/main, at this branch's own merge-base, AND at HEAD — this
     branch's own commits never touched the file at all, so the two
     additive `stageFilter` guards the test exists to protect had already
     landed on main (from an earlier, unrelated change) before this
     branch's merge-base — collapsing the diff to 0 hunks regardless of
     when the test runs, not merely after this PR merges. Fixed the same
     way as item 1: `test_stocktablejs_is_byte_pinned_and_carries_both_
     stagefilter_guards` below drops the diff assertion and pins the
     CURRENT file's exact SHA-256 bytes (losing nothing — those bytes
     already ARE the fully-guarded post-rollout file) plus a direct
     substring check for both guards, no git dependency at all.

     Precise accounting of what remains true, so this docstring makes no
     further false assurances: `_merge_base()`/`_origin_main_text()` are
     still used by exactly two tests below —
     `test_pv_card_is_byte_identical_across_representative_non_us_calls`
     (via `_macros()`) and
     `test_non_us_stocktable_init_call_sites_are_byte_identical_to_origin_main`.
     Both assert EQUALITY ("no diff at all" between the origin/main-sourced
     text and the current text) rather than a specific non-empty diff
     shape — the collapse this section describes makes `orig`/`cur` (or
     `orig_call`/`cur_call`) identical BY CONSTRUCTION once merge-base
     reaches this branch's own HEAD, which keeps an equality assertion
     trivially true (never red), unlike a shape assertion that expects a
     particular non-empty diff and has nothing left to match once the diff
     empties out. Both genuinely survive; neither was re-verified to be
     false the way the stocktable.js diff test was, and both remain
     git-dependent (a legitimate future non-US template/stocktable.js edit
     on either side of the merge-base could still change what they compare,
     just never turn a currently-passing run red from the collapse itself).
  2. pv_css() — the shared <style> block every one of those four pages
     renders once — is byte-pinned (SHA-256 of the exact rendered CSS text).
     This is the check that caught a real defect during this packet's build:
     the new .pv-life/.pv-newer/.pv-mark CSS was first added INSIDE pv_css()
     (shared), which would have changed all four pages' bytes; it now lives
     in dashboard.html.j2's own <style> block instead (US-only, never
     included by the other four). The Added-date rollout's
     `.pv-added`/`.pv-dt+.pv-added` rules DO belong in this shared block
     (they render on every market, not US-only), and F1 (2026-09-01 repair
     round) further changed `.pv-znr`/`.pv-dt`/`.pv-added`'s flex-shrink
     behavior so the buy-zone price chip never loses the space fight to the
     Added-date metadata chip — `test_pv_css_is_byte_pinned_post_rollout`
     pins the CURRENT full CSS text exactly, superseding the old two-line
     diff pin (which could not express "these three rules changed together"
     without becoming exactly this — a whole-content hash).
  3. pv_card() — the per-row card macro — is byte-identical for representative
     cx dicts shaped exactly like the non-US callers' (no lifecycle/id/life/
     lane_mark keys), across several branches (buy/wait/hold/no-zone/flags/
     marks) so an additive-parameter regression that only shows up on one
     branch cannot hide.

A full whole-page render diff (synthetic VM through hk.html.j2 etc. in full)
is NOT attempted here — building synthetic view-models for four more
templates of this size is out of this suite's scope. Given (1) — no other
touched file — the shared-macro proof above is the complete surface by
construction: nothing else in the diff can reach those four pages' bytes.

STOCKTABLE.JS COVERAGE (commissioning follow-up, gap 2): templates/stocktable.js
is a SECOND shared file in scope (retiring the US-only Stage/阶段 filter
dropdown + its count chips, MP-1 §6/§9/§8) — its two additive `stageFilter`
guards are already present at `origin/main`, at this branch's merge-base, and
at HEAD alike (R6, see item 1 above), so it is more precisely "a file this
program's design touches" than "a file this branch's diff touches" today.
hk.html.j2/china.html.j2/canada.html.j2 each call `StockTable.init({...})`
with no `stageFilter` key — the guard (`cfg.stageFilter !== false` /
`cfg.stageFilter === false`) is mathematically a no-op for any caller that
never sets that key (`undefined !== false` is `true`; `undefined === false`
is `false`), so this is proven by (a) pinning stocktable.js's current bytes
exactly and asserting both guard substrings are present in them (R6 —
replaces the old origin/main diff, which could not survive the merge-base
collapse for a file this branch never itself modifies), and (b) grepping
every non-US `StockTable.init({...})` call site's own source text for the
literal string `stageFilter` — its absence in all three is what makes the
guard inert there. intl.html.j2 never calls StockTable.init at all and is
unaffected by construction. Same no-DOM-execution limitation as the page
templates above: this is a static-source proof, not a rendered/executed one.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

import jinja2
import pytest

ROOT = Path(__file__).resolve().parent.parent
NON_US_TEMPLATES = [
    "templates/hk.html.j2",
    "templates/china.html.j2",
    "templates/canada.html.j2",
    "templates/intl.html.j2",
]


def _merge_base() -> str:
    """Repair round 2, finding R5: this suite's job is proving THIS BRANCH'S
    OWN commits never touched the non-US files — a diff against the LIVE
    `origin/main` is the wrong comparison, because main keeps moving (nightly
    pushes, other merged PRs) and any of those commits touching
    hk.html.j2/canada.html.j2/etc. independently fails this suite for a
    reason that has nothing to do with this branch's diff. Confirmed as a
    standing false-positive landmine: `origin/main` had drifted ahead of this
    branch's merge-base by the time of both the round-1 and round-2 review
    (canada.html.j2/hk.html.j2 changed on main after this branch forked).
    The merge-base is the fixed point this branch actually diverged from —
    diffing against it answers the suite's real question and never moves
    again for THIS branch."""
    return subprocess.check_output(
        ["git", "merge-base", "origin/main", "HEAD"], cwd=str(ROOT)
    ).decode().strip()


_MERGE_BASE = _merge_base()


def _origin_main_text(rel_path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{_MERGE_BASE}:{rel_path}"], cwd=str(ROOT)
    ).decode()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: B1 (2026-09-01 repair round): exact SHA-256 of each non-US template's
#: CURRENT raw file bytes — see the module docstring's item 1 for why this
#: replaced the merge-base functional-diff mechanism. No comment-stripping,
#: no leniency: literal file bytes. A legitimate future edit to any of these
#: four templates must recompute and update its hash here.
_EXPECTED_TEMPLATE_SHA256: dict[str, str] = {
    "templates/hk.html.j2": "947b24a38f46ad53b22fc168cd84f45e8eb630b0d09cee8d5f8ad94e8f82fbdc",
    "templates/china.html.j2": "cb6e0685b96a6d897e9562418927c0bb5d5e656d4b31c99e843ec5f213fa7031",
    "templates/canada.html.j2": "878237e4c3d0bef90c2fce108b64cf859d8f67783dede4f77881392c2d1eb7e5",
    "templates/intl.html.j2": "c62b4a6373ac3130a16f622b8dae9b73218642e261051a3bd3493fc95fd0d9a5",
}


def test_non_us_templates_are_byte_pinned_post_rollout():
    """Merge-safe successor to the old merge-base functional-diff test (B1):
    pins each non-US template's CURRENT raw bytes exactly, with no comparison
    to any historical baseline — so this assertion's truth value does not
    depend on whether/when this branch has merged. Simulated merge-base==HEAD
    (the exact failure mode B1 fixes) changes NOTHING here: this test never
    calls git at all."""
    for rel_path in NON_US_TEMPLATES:
        cur = (ROOT / rel_path).read_text(encoding="utf-8")
        assert _sha256_text(cur) == _EXPECTED_TEMPLATE_SHA256[rel_path], (
            f"{rel_path}: content drifted from its pinned post-rollout hash — "
            f"if this is a legitimate edit, recompute and update the pin")


def _macros():
    orig_src = _origin_main_text("templates/_prophet_card.html.j2")
    cur_src = (ROOT / "templates" / "_prophet_card.html.j2").read_text()
    env = jinja2.Environment(autoescape=True)
    return env.from_string(orig_src).module, env.from_string(cur_src).module


#: B1 (2026-09-01 repair round 1): exact SHA-256 of the CURRENT pv_css() render
#: output — supersedes the old two-line merge-base diff pin (same failure
#: mode as the template pin above: a merge-base==HEAD comparison collapses to
#: an empty diff and an assertion expecting a non-empty one goes red). Covers
#: both the Added-date rollout's `.pv-added`/`.pv-dt+.pv-added` rules AND F1's
#: (2026-09-01 repair round 1) `.pv-znr`/`.pv-dt`/`.pv-added` flex-shrink fix
#: (the buy-zone price chip must never lose the space fight to the Added-date
#: metadata chip). Recomputed for round 3's R4 (.pv-znr gains its own bounded
#: max-width:100%;overflow:hidden;text-overflow:ellipsis so a pathologically
#: long zone string ellipsizes instead of hard-clipping) and R5 (the ≤680px
#: max-width:32% cap is scoped to `.pv-added` only, not `.pv-dt`).
#:
#: RECOMPUTED 2026-09-02 for the zone-shelf FOLD (Chairman visibility report):
#: `.pv-zn` gains `flex-wrap:wrap` + a 2px row-gap, `.pv-added` becomes
#: `flex:0 0 auto` with no overflow/ellipsis and no padding-left (it folds to
#: its own line instead of truncating), `.pv-znm` is hardened to `.pv-znr`'s
#: flex:none + bounded-ellipsis contract, and the ≤680px `max-width:32%`
#: truncation cap is removed. CSS-only: `pv_card()`'s markup is byte-unchanged,
#: which `test_pv_card_is_byte_identical_across_representative_non_us_calls`
#: below proves independently. The pin MECHANISM is untouched — this is a
#: recomputed value, not a weakened assertion. A legitimate future edit to
#: pv_css() must recompute and update this hash again.
_EXPECTED_PV_CSS_SHA256 = "e7dd2cf07a44230d9a1b9a82b335943070ca0bad76e6fc7c1b99aa0625a12258"


def test_pv_css_is_byte_pinned_post_rollout():
    """The shared <style> block every non-US page renders once via pv.pv_css().
    No git dependency — reads only the current file on disk, so this is
    immune to the merge-base==HEAD collapse B1 fixes (see module docstring)."""
    cur_src = (ROOT / "templates" / "_prophet_card.html.j2").read_text()
    cur = jinja2.Environment(autoescape=True).from_string(cur_src).module
    css = str(cur.pv_css())
    assert _sha256_text(css) == _EXPECTED_PV_CSS_SHA256, (
        "pv_css() drifted from its pinned post-rollout hash — if this is a "
        "legitimate edit, recompute and update the pin")


def _base_cx(**overrides) -> dict:
    cx = {
        "href": "stock.html#0700.HK", "tk": "0700", "mkt": "hk",
        "name": "Tencent", "sec": "Communication Services",
        "price_txt": "$400.00", "show_change": True,
        "verb": "buy", "edge": 72,
        "stage": 3, "spark": None,
        "zone_kind": "active", "zone_lo": "$390.00", "zone_hi": "$410.00",
        "date": "2026-07-04", "flags": [], "triage": False, "featured": False,
        "marks": None,
    }
    cx.update(overrides)
    return cx


CX_VARIANTS = [
    ("buy_featured", _base_cx(verb="buy", featured=True)),
    ("wait_no_zone", _base_cx(verb="wait", zone_kind="none", zone_lo=None, zone_hi=None, stage=0)),
    ("hold_readd", _base_cx(verb="hold", zone_kind="readd")),
    ("avoid_with_flags", _base_cx(
        verb="avoid",
        flags=[("Earnings soon", "财报临近"), ("Extended", "过热")],
    )),
    ("with_marks_and_trigger", _base_cx(
        marks=[{"k": "new", "en": "New", "zh": "新"},
               {"k": "theme", "en": "AI", "zh": "AI"}],
        trigger={"kind": "fired", "tip_en": "Fired.", "tip_zh": "已触发。"},
    )),
    ("triage_no_price", _base_cx(price_txt=None, show_change=False, triage=True)),
]


def test_pv_card_is_byte_identical_across_representative_non_us_calls():
    orig, cur = _macros()
    for label, cx in CX_VARIANTS:
        out_orig = str(orig.pv_card(cx))
        out_cur = str(cur.pv_card(cx))
        assert out_orig == out_cur, f"pv_card diverged for variant {label!r}"


# --------------------------------------------------------------------------- #
# stocktable.js — Stage/阶段 filter + count-chip retirement (gap 2)
# --------------------------------------------------------------------------- #

NON_US_STOCKTABLE_CALLERS = [
    "templates/hk.html.j2",
    "templates/china.html.j2",
    "templates/canada.html.j2",
]



_JS_IDENTIFIER_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"
)
_JS_STATEMENT_START = "<statement-start>"
_JS_CONTROL_HEADS = frozenset({"if", "while", "for", "with", "switch", "catch"})
_JS_REGEX_PREFIX_TOKENS = frozenset(
    {"", _JS_STATEMENT_START, "(", "[", "{", ",", "=", ":", "!", "&",
     "|", "?", ";", "+", "-", "*", "%", "~", "^", "<", ">",
     "return", "throw", "case", "delete", "void", "typeof", "instanceof",
     "in", "of", "yield", "await", "else", "do"}
)
_JS_STATEMENT_BLOCK_PREFIX_TOKENS = frozenset(
    {"", _JS_STATEMENT_START, "else", "do", "try", "finally"}
)
_JS_FUNCTION_DECL_PREFIX_TOKENS = frozenset(
    {"", _JS_STATEMENT_START, "{", ";"}
)

_SCRIPT_BODY_RE = re.compile(
    r"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_SCRIPT_TYPE_RE = re.compile(
    r"(?:^|[\t\n\f\r ])type[\t\n\f\r ]*=[\t\n\f\r ]*(?:"
    r'"(?P<double>[^"]*)"'
    r"|'(?P<single>[^']*)'"
    r"|(?P<bare>[^\s>]+))",
    re.IGNORECASE,
)
_SCRIPT_SRC_RE = re.compile(
    r"(?:^|[\t\n\f\r ])src[\t\n\f\r ]*=", re.IGNORECASE
)
_EXECUTABLE_SCRIPT_TYPES = frozenset(
    {"", "module", "text/javascript", "application/javascript",
     "text/ecmascript", "application/ecmascript"}
)
_CALL_LINE_RE = re.compile(
    r"(?m)^[ \t]*(?P<call>StockTable\.init[ \t]*\([ \t]*\{)"
)


def _mask_span(chars: list[str], start: int, end: int) -> None:
    """Blank a non-code span while preserving offsets and line boundaries."""
    for i in range(start, end):
        if chars[i] not in "\r\n":
            chars[i] = " "


def _quoted_literal_end(src: str, start: int, *, label: str) -> int:
    """Return one-past a single- or double-quoted JavaScript string."""
    quote = src[start]
    if quote not in "'\"":
        raise AssertionError(f"{label}: expected a JavaScript string quote")
    j = start + 1
    while j < len(src):
        ch = src[j]
        if ch == "\\":
            if j + 1 >= len(src):
                break
            j += 2
            continue
        if ch == quote:
            return j + 1
        if ch in "\r\n":
            raise AssertionError(f"{label}: unterminated JavaScript string literal")
        j += 1
    raise AssertionError(f"{label}: unterminated JavaScript string literal")


def _regex_literal_end(src: str, start: int) -> int | None:
    """Return one-past a same-line JS regex literal and its flags, if valid."""
    j = start + 1
    in_class = False
    while j < len(src):
        ch = src[j]
        if ch in "\r\n":
            return None
        if ch == "\\":
            j += 2
            continue
        if in_class:
            if ch == "]":
                in_class = False
            j += 1
            continue
        if ch == "[":
            in_class = True
            j += 1
            continue
        if ch == "/":
            j += 1
            while j < len(src) and src[j].isalpha():
                j += 1
            return j
        j += 1
    return None


def _delimited_end(src: str, start: int, close: str, *, label: str) -> int:
    end = src.find(close, start)
    if end < 0:
        raise AssertionError(f"{label}: unterminated {close!r} delimited region")
    return end + len(close)

def _mask_template_literal(
    src: str,
    chars: list[str],
    start: int,
    *,
    label: str,
) -> int:
    """Mask raw template text while preserving executable ``${...}`` code."""
    _mask_span(chars, start, start + 1)
    i = start + 1
    raw_start = i
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            if i + 1 >= len(src):
                break
            i += 2
            continue
        if ch == "`":
            _mask_span(chars, raw_start, i + 1)
            return i + 1
        if ch == "$" and i + 1 < len(src) and src[i + 1] == "{":
            _mask_span(chars, raw_start, i + 2)
            i = _mask_js_segment(
                src,
                chars,
                i + 2,
                label=label,
                stop_at_closing_brace=True,
            )
            raw_start = i
            continue
        i += 1
    raise AssertionError(f"{label}: unterminated JavaScript template literal")


def _mask_js_segment(
    src: str,
    chars: list[str],
    start: int,
    *,
    label: str,
    stop_at_closing_brace: bool,
) -> int:
    """Mask one JavaScript segment and return its first unconsumed offset."""
    i = start
    last_token = ""
    pending_control = False
    pending_function_declaration: bool | None = None
    pending_function_body: bool | None = None
    async_function_declaration_hint: bool | None = None
    paren_is_control: list[bool] = []
    paren_function_declaration: list[bool | None] = []
    brace_is_statement: list[bool] = []

    while i < len(src):
        if src.startswith("//", i):
            end = src.find("\n", i + 2)
            end = len(src) if end < 0 else end
            _mask_span(chars, i, end)
            i = end
            continue
        if src.startswith("/*", i):
            end = _delimited_end(src, i + 2, "*/", label=label)
            _mask_span(chars, i, end)
            i = end
            continue
        if src.startswith("<!--", i):
            end = _delimited_end(src, i + 4, "-->", label=label)
            _mask_span(chars, i, end)
            i = end
            continue
        if src.startswith("{#", i):
            end = _delimited_end(src, i + 2, "#}", label=label)
            _mask_span(chars, i, end)
            i = end
            continue
        if src.startswith("{{", i):
            end = _delimited_end(src, i + 2, "}}", label=label)
            _mask_span(chars, i, end)
            last_token = "VALUE"
            pending_control = False
            i = end
            continue
        if src.startswith("{%", i):
            end = _delimited_end(src, i + 2, "%}", label=label)
            _mask_span(chars, i, end)
            i = end
            continue

        ch = src[i]
        if (
            ch == "}"
            and stop_at_closing_brace
            and not brace_is_statement
        ):
            _mask_span(chars, i, i + 1)
            return i + 1
        if ch in "'\"":
            end = _quoted_literal_end(src, i, label=label)
            _mask_span(chars, i, end)
            last_token = "VALUE"
            pending_control = False
            i = end
            continue
        if ch == "`":
            i = _mask_template_literal(src, chars, i, label=label)
            last_token = "VALUE"
            pending_control = False
            continue
        if ch == "/" and last_token in _JS_REGEX_PREFIX_TOKENS:
            end = _regex_literal_end(src, i)
            if end is not None:
                _mask_span(chars, i, end)
                last_token = "VALUE"
                pending_control = False
                i = end
                continue
        if ch in _JS_IDENTIFIER_CHARS and not ch.isdigit():
            j = i + 1
            while j < len(src) and src[j] in _JS_IDENTIFIER_CHARS:
                j += 1
            word = src[i:j]
            prior = last_token
            if word == "async":
                async_function_declaration_hint = (
                    prior in _JS_FUNCTION_DECL_PREFIX_TOKENS
                )
            elif word == "function":
                pending_function_declaration = (
                    async_function_declaration_hint
                    if prior == "async"
                    and async_function_declaration_hint is not None
                    else prior in _JS_FUNCTION_DECL_PREFIX_TOKENS
                )
                async_function_declaration_hint = None
            elif pending_function_declaration is None:
                async_function_declaration_hint = None
            if pending_control and word == "await":
                last_token = word
                i = j
                continue
            pending_control = word in _JS_CONTROL_HEADS and prior != "."
            last_token = word
            i = j
            continue
        if ch.isdigit():
            j = i + 1
            while j < len(src) and (src[j].isalnum() or src[j] in "._"):
                j += 1
            last_token = "VALUE"
            pending_control = False
            i = j
            continue
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            paren_is_control.append(pending_control)
            paren_function_declaration.append(pending_function_declaration)
            pending_control = False
            pending_function_declaration = None
            async_function_declaration_hint = None
            last_token = "("
            i += 1
            continue
        if ch == ")":
            was_control = paren_is_control.pop() if paren_is_control else False
            function_declaration = (
                paren_function_declaration.pop()
                if paren_function_declaration
                else None
            )
            if function_declaration is not None:
                pending_function_body = function_declaration
                last_token = "VALUE"
            else:
                last_token = _JS_STATEMENT_START if was_control else "VALUE"
            pending_control = False
            i += 1
            continue
        if ch == "{":
            if pending_function_body is not None:
                is_statement = pending_function_body
                pending_function_body = None
            else:
                is_statement = last_token in _JS_STATEMENT_BLOCK_PREFIX_TOKENS
            brace_is_statement.append(is_statement)
            pending_control = False
            pending_function_declaration = None
            async_function_declaration_hint = None
            last_token = "{"
            i += 1
            continue
        if ch == "}":
            was_statement = brace_is_statement.pop() if brace_is_statement else False
            last_token = _JS_STATEMENT_START if was_statement else "VALUE"
            pending_control = False
            i += 1
            continue
        pending_control = False
        last_token = "VALUE" if ch == "]" else ch
        i += 1

    if stop_at_closing_brace:
        raise AssertionError(
            f"{label}: unterminated JavaScript template interpolation"
        )
    return i


def _mask_js_noncode(src: str, *, label: str) -> str:
    """Blank non-code regions while retaining executable template expressions."""
    chars = list(src)
    _mask_js_segment(
        src,
        chars,
        0,
        label=label,
        stop_at_closing_brace=False,
    )
    return "".join(chars)

def _script_body_is_executable(attrs: str) -> bool:
    """Mirror HTML script execution boundaries relevant to this static guard."""
    if _SCRIPT_SRC_RE.search(attrs):
        return False
    match = _SCRIPT_TYPE_RE.search(attrs)
    if match is None:
        return True
    value = next(value for value in match.groupdict().values() if value is not None)
    mime = value.split(";", 1)[0].strip().lower()
    return mime in _EXECUTABLE_SCRIPT_TYPES


def _js_regions(src: str) -> list[tuple[int, int]]:
    """Return executable inline-script bodies, or the whole unit-test snippet."""
    matches = list(_SCRIPT_BODY_RE.finditer(src))
    if not matches:
        return [(0, len(src))]
    return [
        match.span("body")
        for match in matches
        if _script_body_is_executable(match.group("attrs"))
    ]


def _literal_init_call_candidates(
    src: str, *, label: str
) -> list[tuple[int, int]]:
    """Return executable line-started literal calls with stable source offsets."""
    candidates: list[tuple[int, int]] = []
    for region_start, region_end in _js_regions(src):
        region = src[region_start:region_end]
        masked = _mask_js_noncode(region, label=label)
        for match in _CALL_LINE_RE.finditer(masked):
            candidates.append((region_start + match.start("call"), region_end))
    return candidates


def _init_call_source_from_text(src: str, *, label: str) -> str:
    """Return the one executable literal ``StockTable.init({...})`` expression.

    Full templates are limited to inline script bodies. A same-length JavaScript
    mask removes comments, strings, template literals, regexes, and Jinja regions
    before candidate detection and parenthesis balance. Duplicate or malformed
    executable calls fail closed, and post-init enhancement code stays outside.
    """
    candidates = _literal_init_call_candidates(src, label=label)
    if len(candidates) != 1:
        raise AssertionError(
            f"{label}: expected exactly one executable literal StockTable.init call; "
            f"found {len(candidates)}"
        )
    start, region_end = candidates[0]
    call_region = src[start:region_end]
    masked = _mask_js_noncode(call_region, label=label)
    open_paren = masked.find("(", len("StockTable.init"))
    assert open_paren >= 0  # established by _literal_init_call_candidates

    depth = 0
    for i in range(open_paren, len(masked)):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return call_region[:i + 1]
            if depth < 0:
                break
    raise AssertionError(f"{label}: StockTable.init call is unterminated")

def _init_call_source(template_rel_path: str) -> str:
    src = (ROOT / template_rel_path).read_text()
    return _init_call_source_from_text(src, label=template_rel_path)


def test_init_call_source_skips_comments_and_returns_literal_call():
    """A comment naming StockTable.init() must not masquerade as the call."""
    for rel in NON_US_STOCKTABLE_CALLERS:
        call = _init_call_source(rel)
        assert call.startswith("StockTable.init({"), (
            f"{rel}: extracted a comment or non-literal call")
        assert "dataId:" in call
        assert "containerId:" in call


def test_init_call_source_ignores_exact_token_inside_comment_text():
    src = """/* StockTable.init({ decoy: true }); */
  StockTable.init({ dataId: 'real', containerId: 'table' });
"""
    call = _init_call_source_from_text(src, label="synthetic-comment")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"


def test_init_call_source_skips_line_started_token_inside_block_comment():
    src = """/*
StockTable.init({ decoy: true });
*/
StockTable.init({ dataId: 'real', containerId: 'table' });
"""
    call = _init_call_source_from_text(src, label="synthetic-block-comment")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"


def test_init_call_source_ignores_parentheses_inside_js_literals_and_comments():
    src = """StockTable.init({
  dataId: 'real)',
  label: "literal ( still string",
  template: `literal ) template`,
  // ) line-comment noise
  /* ( block-comment noise */
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-literals")
    assert call == src.strip()[:-1]


def test_init_call_source_refuses_multiple_executable_literal_calls():
    src = """StockTable.init({ dataId: 'one', containerId: 'one' });
StockTable.init({ dataId: 'two', containerId: 'two' });
"""
    with pytest.raises(AssertionError, match="exactly one executable"):
        _init_call_source_from_text(src, label="synthetic-duplicate")


def test_init_call_source_skips_line_started_token_inside_template_literal():
    src = """const example = `
StockTable.init({ dataId: 'decoy', containerId: 'decoy' });
`;
StockTable.init({ dataId: 'real', containerId: 'table' });
"""
    call = _init_call_source_from_text(src, label="synthetic-template-decoy")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"



def test_init_call_source_counts_executable_template_interpolation():
    src = """StockTable.init({ dataId: 'real', containerId: 'table' });
const later = `prefix ${
StockTable.init({ dataId: 'second', containerId: 'second' })
}`;
"""
    with pytest.raises(AssertionError, match="found 2"):
        _init_call_source_from_text(src, label="synthetic-template-interpolation")

def test_init_call_source_ignores_parentheses_inside_regex_literals():
    src = r"""StockTable.init({
  dataId: 'real',
  matcher: /[()]/,
  escapedClose: /\)/,
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-regex-literals")
    assert call == src.strip()[:-1]


def test_init_call_source_preserves_division_parentheses_as_code():
    src = """StockTable.init({
  dataId: 'real',
  ratio: total / (count || 1),
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-division")
    assert call == src.strip()[:-1]



def test_init_call_source_ignores_non_javascript_script_blocks():
    src = """<script type="application/json">
StockTable.init({ dataId: 'decoy', containerId: 'decoy' });
</script>
<script>
StockTable.init({ dataId: 'real', containerId: 'table' });
</script>
"""
    call = _init_call_source_from_text(src, label="synthetic-json-script-decoy")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"


def test_init_call_source_refuses_non_javascript_script_as_only_call():
    src = """<script type="application/json">
StockTable.init({ dataId: 'decoy', containerId: 'decoy' });
</script>
"""
    with pytest.raises(AssertionError, match="found 0"):
        _init_call_source_from_text(src, label="synthetic-json-script-only")



def test_init_call_source_ignores_external_script_fallback_body():
    src = """<script src="stocktable.js">
StockTable.init({ dataId: 'decoy', containerId: 'decoy' });
</script>
<script>
StockTable.init({ dataId: 'real', containerId: 'table' });
</script>
"""
    call = _init_call_source_from_text(src, label="synthetic-external-script")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"


def test_init_call_source_accepts_javascript_module_script():
    src = """<script type="module">
StockTable.init({ dataId: 'real', containerId: 'table' });
</script>
"""
    call = _init_call_source_from_text(src, label="synthetic-module-script")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"



def test_init_call_source_does_not_treat_data_attributes_as_type_or_src():
    for attrs in ('data-src="metadata"', 'data-type="application/json"'):
        src = f"""<script {attrs}>
StockTable.init({{ dataId: 'real', containerId: 'table' }});
</script>
"""
        call = _init_call_source_from_text(src, label=f"synthetic-{attrs}")
        assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"


def test_init_call_source_masks_regex_statement_after_control_header():
    src = r"""StockTable.init({
  dataId: 'real',
  matcher: (function () {
    if (enabled) /\)/.test(value);
    return true;
  })(),
  stageFilter: false,
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-control-regex")
    assert call == src.strip()[:-1]
    assert "stageFilter: false" in call



def test_init_call_source_masks_regex_statement_after_control_block():
    src = r"""StockTable.init({
  dataId: 'real',
  matcher: (function () {
    if (enabled) {
      value += 1;
    }
    /\)/.test(value);
    return true;
  })(),
  stageFilter: false,
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-control-block-regex")
    assert call == src.strip()[:-1]
    assert "stageFilter: false" in call



def test_init_call_source_masks_regex_after_function_declaration_block():
    src = r"""StockTable.init({
  dataId: 'real',
  matcher: (function () {
    function probe() {}
    /\)/.test(value);
    return true;
  })(),
  stageFilter: false,
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-function-regex")
    assert call == src.strip()[:-1]
    assert "stageFilter: false" in call


def test_init_call_source_ignores_comment_delimiters_inside_prior_string_literal():
    src = """const literal = \"/*\";
StockTable.init({ dataId: 'real', containerId: 'table' });
"""
    call = _init_call_source_from_text(src, label="synthetic-string-comment-token")
    assert call == "StockTable.init({ dataId: 'real', containerId: 'table' })"


def test_init_call_source_ignores_parentheses_inside_regex_literal():
    src = r"""StockTable.init({
  dataId: 'real',
  pattern: /literal\)still-regex/,
  containerId: 'table'
});
"""
    call = _init_call_source_from_text(src, label="synthetic-regex")
    assert call == src.strip()[:-1]


#: R6 (2026-09-01 repair round 3): exact SHA-256 of the CURRENT
#: templates/stocktable.js raw bytes. Same merge-safety reasoning as the B1
#: template pins above (module docstring item 1) applies here, confirmed
#: independently in round 3: templates/stocktable.js's git blob
#: (f8145bd6fb4ed0adba5f34b5c97a7895b7332f2e) is IDENTICAL at origin/main,
#: at this branch's own merge-base, AND at HEAD — this branch never itself
#: modified the file, so the predecessor test's `git diff -U0 $MERGE_BASE`
#: was always going to collapse to 0 hunks, not merely after a future
#: merge. Pinning current bytes loses nothing: those bytes already ARE the
#: fully-guarded post-rollout file. A legitimate future edit to
#: templates/stocktable.js must recompute and update this hash.
_EXPECTED_STOCKTABLEJS_SHA256 = "56f6f93366f2e21024b4cd5c971766a7c9506aea49c21b37b428674b8f086819"


def test_stocktablejs_is_byte_pinned_and_carries_both_stagefilter_guards():
    """Merge-safe successor to
    test_stocktablejs_diff_is_exactly_the_two_additive_stagefilter_guards
    (R6, round 3): that test asserted a SPECIFIC non-empty diff shape
    (`hunk_count == 2`) against `git diff -U0 $MERGE_BASE --
    templates/stocktable.js` — measured RED on this exact head, in this
    exact file, inside CI pack 9, because the file's bytes are already
    identical at origin/main, this branch's merge-base, and HEAD (see the
    hash comment above). This test drops the diff entirely: it pins the
    CURRENT file's raw bytes exactly (no git dependency, immune to any
    future merge-base movement) and asserts the two additive `stageFilter`
    guards the retired test existed to protect are directly present in the
    file text — the property that mattered, checked without a diff
    artifact standing in for it."""
    cur = (ROOT / "templates" / "stocktable.js").read_text()
    assert _sha256_text(cur) == _EXPECTED_STOCKTABLEJS_SHA256, (
        "templates/stocktable.js drifted from its pinned byte hash — if this "
        "is a legitimate edit, recompute and update the pin")
    assert "cfg.stageFilter !== false && stageOpts.length > 0" in cur
    assert "cfg.stageFilter === false" in cur


def test_non_us_stocktable_init_calls_never_set_stagefilter():
    """The guard is `cfg.stageFilter !== false` / `=== false`. Neither branch
    changes behavior unless the CALLER sets the key — so a caller's source
    text containing no `stageFilter` substring at all is a complete proof
    that this retirement is invisible to it, independent of what the guard's
    JS semantics happen to be."""
    for rel in NON_US_STOCKTABLE_CALLERS:
        call = _init_call_source(rel)
        assert "stageFilter" not in call, f"{rel} unexpectedly sets stageFilter"


def test_non_us_stocktable_init_call_sites_are_byte_identical_to_origin_main():
    """The exact inline init expressions remain byte-identical to the baseline.

    Deliberate P0B owner-tagging and view-reconciliation code follows the call in
    HK and Canada.  It is outside this Stage-filter guard and must not be pulled in
    by an arbitrary post-call byte window.
    """
    for rel in NON_US_STOCKTABLE_CALLERS:
        orig_src = subprocess.check_output(
            ["git", "show", f"{_MERGE_BASE}:{rel}"], cwd=str(ROOT)
        ).decode()
        orig_call = _init_call_source_from_text(
            orig_src, label=f"{_MERGE_BASE}:{rel}"
        )
        cur_call = _init_call_source(rel)
        assert orig_call == cur_call, f"{rel}: StockTable.init call changed"


def test_intl_never_calls_stocktable_init():
    src = (ROOT / "templates" / "intl.html.j2").read_text()
    assert "StockTable.init(" not in src


def test_us_call_site_sets_stagefilter_false():
    """Unlike hk/china/canada (which pass an inline object literal straight to
    StockTable.init(...)), dashboard.html.j2 builds a named `STINIT` object
    first and calls `StockTable.init(STINIT)` — so the config to inspect is
    the `var STINIT = { ... };` literal, not the call site itself."""
    dash = (ROOT / "templates" / "dashboard.html.j2").read_text()
    assert "StockTable.init(STINIT)" in dash
    start = dash.index("var STINIT = {")
    depth = 0
    end = start
    for end in range(start, len(dash)):
        if dash[end] == "{":
            depth += 1
        elif dash[end] == "}":
            depth -= 1
            if depth == 0:
                break
    stinit_literal = dash[start:end + 1]
    assert "'us-stocktable-data'" in stinit_literal or '"us-stocktable-data"' in stinit_literal
    assert "stageFilter: false" in stinit_literal


def test_no_user_facing_stage_word_reachable_when_stagefilter_is_false():
    """The retirement mechanism itself: `_makeDD('stage', ...)` is the ONLY
    reader of FILTER_LABELS['stage']/FILTER_TITLES['stage'] (the 'Stage'/'阶段'
    strings) anywhere in stocktable.js, and its one call site is gated by the
    same flag the US init sets. This does not execute the guard (no DOM here
    — see module docstring); it proves the STRUCTURE that makes the ban hold:
    there is exactly one path from cfg to that label text, and it is gated."""
    js = (ROOT / "templates" / "stocktable.js").read_text()
    makedd_stage_calls = js.count("_makeDD('stage'")
    assert makedd_stage_calls == 1, (
        f"expected exactly one _makeDD('stage', ...) call site to reason about, found {makedd_stage_calls}"
    )
    call_line = next(line for line in js.splitlines() if "_makeDD('stage'" in line)
    assert "cfg.stageFilter !== false" in call_line, (
        "the sole _makeDD('stage', ...) call site is not gated by cfg.stageFilter"
    )
