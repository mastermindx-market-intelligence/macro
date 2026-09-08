"""tests/test_freshness_chips_language_invariant.py — freshness / provenance chips never
inherit the Chinese-mode up/down colour swap.

THE DEFECT THIS PINS (Opus re-review of PR #6933). ``templates/theme.css`` swaps
``--up``/``--down`` under ``html[data-lang="zh"]`` because in Asia red = up, and every
token derived from that pair (``--ink-up``/``--ink-down`` are colour-mixes of it, the
Prophet verdict hues, the ``--q1``/``--q3`` quadrants) swaps with it. A freshness or
provenance chip — "Confirmed <date>", a fresh/stale coverage badge, an as-of live dot —
says how CURRENT a datum is, never which way a market moved. So a rule such as
``.imd-chip.fresh{color:var(--ink-up, var(--up))}`` painted the SAME chip green in
English and red in Chinese. The language-invariant home for those states is the status
plane (``--ok``/``--warn``/``--act`` and their ``--ink-*``), which theme.css documents as
"health/danger, NOT price direction" and never swaps at root.

WHY THIS SUITE IS BROWSER-FREE. The CI packs install a minimal dependency set, not
``requirements.txt`` — a ``pytest.importorskip("playwright")`` here would SKIP in CI and
report green while proving nothing. So it resolves the two properties that actually
broke straight from the shipped source with the stdlib:

1. **The swapped-token closure.** Every custom property (re)declared in an UNSCOPED
   ``html[...][data-lang="zh"]`` block of theme.css is a direction token, and so is any
   root-plane token whose value references one. The status plane must never enter that
   closure — a future ``html[data-lang="zh"] { --ok: ... }`` fails here before it ships.
   (Gauge-scoped remaps such as ``html[data-lang="zh"] .rrx { --ok: var(--up) }`` are a
   deliberate, documented exception and stay out of the closure because they are scoped.)
2. **No freshness rule references a swapped token.** A rule is a freshness rule when a
   class in its selector carries a freshness word in lowercase (``fresh``, ``stale``,
   ``verified``, ``updated``, ``asof``). Signal states such as ``.st-FRESH_BUY`` are
   market verdicts and are skipped by case; ``refresh`` controls are skipped by name.
   Failures name ``file:line`` so the fix is one edit away.
"""
from __future__ import annotations

import bisect
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
THEME = TEMPLATES / "theme.css"

TEXT_SUFFIXES = {".j2", ".html", ".css", ".js"}
FRESHNESS_WORD_RE = re.compile(r"(?<!re)fresh|stale|verified|updated|asof")
CLASS_RE = re.compile(r"\.([A-Za-z0-9_-]+)")
VAR_RE = re.compile(r"--[A-Za-z0-9_-]+")
DECL_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+)")
RULE_RE = re.compile(r"([^{}]*)\{([^{}]*)\}", re.S)
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
JINJA_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
ROOT_PLANE_PART_RE = re.compile(r"^(?::root|html)(?:\[[^\]]*\])*$")
# A brace pair whose "selector" is really JavaScript (a call, an arrow, a keyword) is
# not a CSS rule. Pseudo-class parentheses (:is/:not/:where/:has/:nth-*) stay CSS.
JS_SELECTOR_RE = re.compile(
    r"(?<!:is)(?<!:not)(?<!:where)(?<!:has)(?<!-child)(?<!-of-type)(?<!:lang)(?<!:dir)\("
    r"|=>|\b(?:return|function|var|const|let|if|else|for|while|switch|case|try|catch)\b"
)

STATUS_PLANE = ("--ok", "--warn", "--act", "--ink-ok", "--ink-warn", "--ink-act")
DIRECTION_PLANE = ("--up", "--down", "--ink-up", "--ink-down")


def _blank_preserving_newlines(match: re.Match) -> str:
    return "\n" * match.group(0).count("\n")


def _css_rules(text: str) -> list[tuple[str, str, int]]:
    r"""Return (selector, body, line) for every INNERMOST brace pair.

    Comments and Jinja tags are blanked with their newlines kept so ``line`` matches the
    source file. This is a single linear pass over the brace positions — a regex such as
    ``([^{}]*)\{([^{}]*)\}`` goes quadratic on the multi-thousand-line page templates
    (every failed start position rescans the brace-free stretch after it)."""
    text = COMMENT_RE.sub(_blank_preserving_newlines, text)
    text = JINJA_RE.sub(_blank_preserving_newlines, text)
    newlines = [m.start() for m in re.finditer("\n", text)]
    rules: list[tuple[str, str, int]] = []
    selector_start = 0          # after the previous '}' or the previous (outer) '{'
    open_at: int | None = None  # index of the innermost unclosed '{'
    open_selector_start = 0
    for brace in re.finditer(r"[{}]", text):
        pos = brace.start()
        if text[pos] == "{":
            open_at = pos
            open_selector_start = selector_start
            selector_start = pos + 1
        else:
            if open_at is not None:
                body = text[open_at + 1:pos]
                selector = text[open_selector_start:open_at].rsplit(";", 1)[-1].strip()
                line = bisect.bisect_left(newlines, open_at + 1) + 1
                rules.append((selector, body, line))
                open_at = None
            selector_start = pos + 1
    return rules


def _is_root_plane(selector: str) -> bool:
    parts = [p.strip() for p in selector.split(",") if p.strip()]
    return bool(parts) and all(ROOT_PLANE_PART_RE.match(p) for p in parts)


def swapped_token_closure(theme_css: str) -> set[str]:
    """Direction tokens: everything redeclared in an unscoped zh block of theme.css,
    plus every root-plane token whose value references one (transitively)."""
    rules = _css_rules(theme_css)
    swapped: set[str] = set()
    root_decls: list[tuple[str, str]] = []
    for selector, body, _line in rules:
        if not _is_root_plane(selector):
            continue
        decls = DECL_RE.findall(body)
        root_decls.extend(decls)
        if 'data-lang="zh"' in selector:
            swapped.update(name for name, _value in decls)
    changed = True
    while changed:
        changed = False
        for name, value in root_decls:
            if name not in swapped and any(tok in swapped for tok in VAR_RE.findall(value)):
                swapped.add(name)
                changed = True
    return swapped


def freshness_rules(text: str) -> list[tuple[str, str, int]]:
    out = []
    for selector, body, line in _css_rules(text):
        if JS_SELECTOR_RE.search(selector):
            continue
        if any(FRESHNESS_WORD_RE.search(cls) for cls in CLASS_RE.findall(selector)):
            out.append((selector, body, line))
    return out


def freshness_offenders(text: str, swapped: set[str]) -> list[tuple[int, str, list[str]]]:
    offenders = []
    for selector, body, line in freshness_rules(text):
        used = sorted({tok for tok in VAR_RE.findall(body) if tok in swapped})
        if used:
            offenders.append((line, " ".join(selector.split())[:90], used))
    return offenders


def _template_files() -> list[Path]:
    return sorted(p for p in TEMPLATES.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES)


# ── 1. the swapped closure is real, and the status plane is outside it ──────────────

def test_swap_closure_contains_the_direction_plane_and_not_the_status_plane():
    swapped = swapped_token_closure(THEME.read_text(encoding="utf-8"))
    missing = [tok for tok in DIRECTION_PLANE if tok not in swapped]
    assert not missing, f"theme.css zh swap closure lost {missing}: the parser or the swap block moved"
    leaked = [tok for tok in STATUS_PLANE if tok in swapped]
    assert not leaked, (
        f"{leaked} entered the html[data-lang=\"zh\"] swap closure — the status plane is the "
        "language-invariant home of every freshness / provenance / health chip and must never "
        "be redeclared at root under zh (gauge-scoped remaps like `.rrx` are the only allowed shape)"
    )


def test_closure_is_transitive_over_derived_tokens():
    css = (
        ':root { --up: #0f0; --down: #f00; --ok: #0a0; --ink-up: color-mix(in srgb, var(--up) 60%, #000);'
        ' --pv-buy: var(--ink-up); }\n'
        'html[data-lang="zh"] { --up: #f00; --down: #0f0; }\n'
        'html[data-lang="zh"] .gauge { --ok: var(--up); }\n'
    )
    swapped = swapped_token_closure(css)
    assert swapped == {"--up", "--down", "--ink-up", "--pv-buy"}, swapped


# ── 2. no freshness rule in any template paints with a swapped token ────────────────

def test_no_freshness_rule_references_a_swapped_direction_token():
    swapped = swapped_token_closure(THEME.read_text(encoding="utf-8"))
    report = []
    total = 0
    for path in _template_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        total += len(freshness_rules(text))
        for line, selector, used in freshness_offenders(text, swapped):
            report.append(f"  {path.relative_to(ROOT)}:{line}  {selector}  ->  {', '.join(used)}")
    assert total >= 10, f"only {total} freshness rules found under templates/ — the matcher is broken"
    assert not report, (
        "freshness / provenance rules must paint with the status plane (--ok/--warn/--act + --ink-*), "
        "never with tokens theme.css swaps under html[data-lang=\"zh\"]:\n" + "\n".join(report)
    )


def test_matcher_catches_the_original_defect_and_skips_signal_states():
    swapped = {"--up", "--down", "--ink-up", "--ink-down"}
    defect = '.imd-chip{padding:4px}\n.imd-chip.fresh,.imd-chip.clear{color:var(--ink-up, var(--up));border-color:var(--up)}\n'
    assert freshness_offenders(defect, swapped) == [
        (2, ".imd-chip.fresh,.imd-chip.clear", ["--ink-up", "--up"])
    ]
    healed = '.imd-chip.fresh{color:var(--ink-ok, var(--ok))}\n.imd-chip.stale{color:var(--ink-warn, var(--warn))}\n'
    assert freshness_offenders(healed, swapped) == []
    # a market verdict that happens to spell FRESH (Prophet's FRESH_BUY) is not a freshness chip
    signal = '.st-FRESH_BUY, .pill-ok { --c: var(--ink-up); }\n.ts-recovery-confirmed{color:var(--up)}\n'
    assert freshness_offenders(signal, swapped) == []
    # a refresh control is not a freshness state either
    assert freshness_offenders('.refresh-btn{color:var(--up)}', swapped) == []
    # JavaScript brace pairs are not CSS rules even when a freshness word appears
    js = 'function freshClass(ms){ return ms > 0 ? "fresh-live" : ""; }\nif(node){ node.classList.add("fresh-live"); }\n'
    assert freshness_offenders(js, swapped) == []
    # Jinja tags inside a <style> block do not break rule extraction
    jinja = '<style>{% if x %}.a{color:red}{% endif %}\n.tp-node.fresh-live{ box-shadow:0 0 0 4px var(--ch,var(--up)); }</style>'
    assert [o[0] for o in freshness_offenders(jinja, swapped)] == [2]


# ── 3. the motivating exemplar and the two JS-authored freshness colours ──────────────

def test_international_macro_health_chips_sit_on_the_status_plane():
    text = (TEMPLATES / "international_macro.html.j2").read_text(encoding="utf-8")
    by_class = {}
    for selector, body, _line in _css_rules(text):
        for cls in ("fresh", "stale", "missing"):
            if f".imd-chip.{cls}" in selector and "color" in body:
                by_class.setdefault(cls, []).append(body)
    assert set(by_class) == {"fresh", "stale", "missing"}, by_class.keys()
    assert any("var(--ink-ok" in b for b in by_class["fresh"]), by_class["fresh"]
    assert any("var(--ink-warn" in b for b in by_class["stale"]), by_class["stale"]
    assert any("var(--ink-act" in b for b in by_class["missing"]), by_class["missing"]
    # the health states must not share a rule with the market-stance states that DO swap
    for selector, body, _line in _css_rules(text):
        if ".imd-chip.fresh" in selector or ".imd-chip.missing" in selector:
            assert not any(s in selector for s in (".constructive", ".defensive", ".clear", ".risk")), selector


def test_committee_web_health_status_colours_are_not_direction_tokens():
    swapped = swapped_token_closure(THEME.read_text(encoding="utf-8"))
    text = (TEMPLATES / "committee.html.j2").read_text(encoding="utf-8")
    meta = re.search(r"var STATUS_META = \{(.*?)\};", text, re.S)
    assert meta, "committee.html.j2 renderWebHealth STATUS_META moved"
    for state, token in re.findall(r"(\w+):\s*\{[^}]*color:\s*'var\((--[\w-]+)\)'", meta.group(1)):
        assert token not in swapped, f"STATUS_META.{state} paints with swapped token {token}"
    fallback = re.search(r"STATUS_META\[st\] \|\| \{[^}]*color:\s*'var\((--[\w-]+)\)'", text)
    assert fallback and fallback.group(1) not in swapped, fallback and fallback.group(0)
    stale_items = re.search(r"d\.what_is_stale, 3, function \(s\) \{\s*return '<div style=\"[^\"]*color:var\((--[\w-]+)", text)
    assert stale_items and stale_items.group(1) not in swapped, stale_items and stale_items.group(0)
