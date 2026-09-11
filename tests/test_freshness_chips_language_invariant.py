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

   Resolution is not line-local. A rule that paints with ``var(--rvc)`` while markup
   or a sibling rule sets ``--rvc: var(--ok)`` is treated as using ``--ok``. A
   scoped zh remap (``html[data-lang="zh"] .rrx { --ok: var(--up) }``) applies to
   any freshness rule whose selector lives in that scope, unless the used token is
   a root-plane alias (``:root { --fresh-ok: var(--ok) }``) that inherits RESOLVED
   and is not redeclared inside the remap zone. Harvesting only ``:root`` /
   ``html[...]`` declarations is how this suite once counted the ``.rrx-rec-chip.fresh``
   counterexample and cleared it.
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

STATUS_PLANE = ("--ok", "--warn", "--act", "--ink-ok", "--ink-warn", "--ink-act", "--fresh-ok")
DIRECTION_PLANE = ("--up", "--down", "--ink-up", "--ink-down")
SET_VAR_RE = re.compile(
    r"\{%-?\s*set\s+(\w+)\s*=\s*'var\((--[A-Za-z0-9_-]+)\)'",
)
STYLE_ATTR_RE = re.compile(r"""style\s*=\s*["']([^"']*)["']""")
STYLE_PROP_RE = re.compile(
    r"(--[A-Za-z0-9_-]+)\s*:\s*(?:\{\{\s*(\w+)\s*\}\}|([^;]+))"
)


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


def _selector_classes(selector: str) -> set[str]:
    return set(CLASS_RE.findall(selector))


def _lives_in_scope(usage_selector: str, scope_selector: str) -> bool:
    """True when a freshness rule's selector sits inside a scoped remap zone.

    ``html[data-lang="zh"] .rrx`` scopes ``.rrx .rrx-rec-chip.fresh``.
    ``html[data-lang="zh"] :is(.igx, .igs)`` scopes both gauge families.
    A root-plane selector has no classes and never matches.
    """
    scope = _selector_classes(scope_selector)
    return bool(scope) and bool(scope & _selector_classes(usage_selector))


def scoped_zh_remaps(theme_css: str) -> list[tuple[str, dict[str, str]]]:
    """Custom properties redeclared under zh on a SCOPED selector (not :root/html)."""
    remaps: list[tuple[str, dict[str, str]]] = []
    for selector, body, _line in _css_rules(theme_css):
        if 'data-lang="zh"' not in selector or _is_root_plane(selector):
            continue
        decls = {name: value.strip() for name, value in DECL_RE.findall(body)}
        if decls:
            remaps.append((selector, decls))
    return remaps


def _primary_var_tokens(value: str) -> list[str]:
    """First argument of each ``var()``, ignoring nested fallbacks.

    ``var(--ok, var(--up))`` is a missing-token fallback, not an alias of
    ``--up``. Walking fallbacks is how a page-local ``_state_inks`` formula
    once painted every ``--ink-ok`` user as a direction-token offender.
    """
    tokens: list[str] = []
    i, n = 0, len(value)
    while i < n:
        if value.startswith("var(", i):
            m = re.match(r"var\(\s*(--[A-Za-z0-9_-]+)", value[i:])
            if m:
                tokens.append(m.group(1))
            depth = 0
            j = i
            while j < n:
                if value[j] == "(":
                    depth += 1
                elif value[j] == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            i = j
            continue
        i += 1
    return tokens


def collect_aliases(*texts: str) -> list[tuple[str, str, list[str]]]:
    """(name, declaring_selector, value_tokens) from CSS rules and markup.

    Markup covers ``style="--rvc:{{ rvc }}"`` plus a sibling
    ``{% set rvc = 'var(--ok)' if ... %}`` so the receding-state assignment is
    visible even though it is not a CSS declaration.
    """
    aliases: list[tuple[str, str, list[str]]] = []
    for text in texts:
        for selector, body, _line in _css_rules(text):
            if JS_SELECTOR_RE.search(selector):
                continue
            for name, value in DECL_RE.findall(body):
                toks = _primary_var_tokens(value)
                if toks:
                    aliases.append((name, selector, toks))
        jinja_sets = {var: token for var, token in SET_VAR_RE.findall(text)}
        for style in STYLE_ATTR_RE.findall(text):
            for name, jinja_var, raw_value in STYLE_PROP_RE.findall(style):
                if jinja_var and jinja_var in jinja_sets:
                    aliases.append((name, "markup", [jinja_sets[jinja_var]]))
                elif raw_value:
                    toks = _primary_var_tokens(raw_value)
                    if toks:
                        aliases.append((name, "markup", toks))
    return aliases


def _usage_in_remap(usage_selector: str, remaps: list[tuple[str, dict[str, str]]]) -> bool:
    return any(_lives_in_scope(usage_selector, remap_sel) for remap_sel, _ in remaps)


def _matching_aliases(
    token: str,
    usage_selector: str,
    aliases: list[tuple[str, str, list[str]]],
    remaps: list[tuple[str, dict[str, str]]],
) -> list[tuple[str, str, list[str]]]:
    # A root-plane lookup (inherited resolved alias) must not pick up scoped
    # rebindings of the same name — those compute in the remap zone, not at :root.
    if _is_root_plane(usage_selector):
        return [a for a in aliases if a[0] == token and _is_root_plane(a[1])]
    # Local indirections (--rvc, --ic-col, a redeclared --fresh-ok) only matter
    # when the freshness rule lives in a scoped zh remap. A generic --c on a
    # .pill-stale / .st-FRESH_BUY badge is a per-class theme hook, not a remap
    # escape, and must not be walked estate-wide.
    in_remap = _usage_in_remap(usage_selector, remaps)
    scoped: list[tuple[str, str, list[str]]] = []
    if in_remap:
        for a in aliases:
            if a[0] != token or _is_root_plane(a[1]):
                continue
            if a[1] == "markup" or _lives_in_scope(usage_selector, a[1]):
                scoped.append(a)
    if scoped:
        return scoped
    return [a for a in aliases if a[0] == token and _is_root_plane(a[1])]


def resolve_freshness_hits(
    used: set[str],
    usage_selector: str,
    swapped: set[str],
    aliases: list[tuple[str, str, list[str]]],
    remaps: list[tuple[str, dict[str, str]]],
) -> list[str]:
    """Swapped tokens reachable from ``used`` at ``usage_selector``.

    A root-plane alias (``:root { --fresh-ok: var(--ok) }``) resolves its value
    at the declaration site, so a scoped zh remap of ``--ok`` does not apply.
    A local alias declared inside the remap zone (``--rvc: var(--ok)`` on
    ``.rrx-rec``, or ``.rrx { --fresh-ok: var(--ok) }``) does re-resolve.
    """
    bad: set[str] = set()

    def walk(token: str, decl_selector: str, seen: frozenset[str]) -> None:
        if token in seen:
            return
        next_seen = seen | {token}
        if not _is_root_plane(decl_selector):
            for remap_sel, remap_decls in remaps:
                if token not in remap_decls:
                    continue
                if _lives_in_scope(usage_selector, remap_sel) or _lives_in_scope(decl_selector, remap_sel):
                    for nxt in _primary_var_tokens(remap_decls[token]):
                        if nxt in swapped:
                            bad.add(token)
                        walk(nxt, remap_sel, next_seen)
                    if token in swapped:
                        bad.add(token)
                    return
        if token in swapped:
            bad.add(token)
            return
        lookup = decl_selector if _is_root_plane(decl_selector) else usage_selector
        for _name, alias_sel, value_tokens in _matching_aliases(token, lookup, aliases, remaps):
            for nxt in value_tokens:
                walk(nxt, alias_sel, next_seen)

    dirty_used: set[str] = set()
    for tok in used:
        before = set(bad)
        walk(tok, usage_selector, frozenset())
        if bad - before:
            dirty_used.add(tok)
    return sorted(dirty_used)


def freshness_offenders(
    text: str,
    swapped: set[str],
    *,
    theme_css: str | None = None,
    alias_texts: list[str] | None = None,
    aliases: list[tuple[str, str, list[str]]] | None = None,
    remaps: list[tuple[str, dict[str, str]]] | None = None,
) -> list[tuple[int, str, list[str]]]:
    if remaps is None:
        remaps = scoped_zh_remaps(theme_css) if theme_css else []
    if aliases is None:
        sources = [text]
        if theme_css:
            sources.append(theme_css)
        if alias_texts:
            sources.extend(alias_texts)
        aliases = collect_aliases(*sources)
    offenders = []
    for selector, body, line in freshness_rules(text):
        used = set(VAR_RE.findall(body))
        hits = resolve_freshness_hits(used, selector, swapped, aliases, remaps)
        if hits:
            offenders.append((line, " ".join(selector.split())[:90], hits))
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
    theme = THEME.read_text(encoding="utf-8")
    swapped = swapped_token_closure(theme)
    remaps = scoped_zh_remaps(theme)
    theme_aliases = collect_aliases(theme)
    report = []
    total = 0
    for path in _template_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        sibling_texts = [
            sib.read_text(encoding="utf-8", errors="replace")
            for sib in path.parent.glob(path.name.split(".", 1)[0] + ".*")
            if sib != path and sib.suffix in TEXT_SUFFIXES
        ]
        aliases = theme_aliases + collect_aliases(text, *sibling_texts)
        total += len(freshness_rules(text))
        for line, selector, used in freshness_offenders(
            text, swapped, aliases=aliases, remaps=remaps
        ):
            report.append(f"  {path.relative_to(ROOT)}:{line}  {selector}  ->  {', '.join(used)}")
    assert total >= 10, f"only {total} freshness rules found under templates/ — the matcher is broken"
    assert not report, (
        "freshness / provenance rules must paint with the status plane (--ok/--warn/--act + --ink-*), "
        "never with tokens theme.css swaps under html[data-lang=\"zh\"] "
        "(local aliases and scoped remaps resolved):\n" + "\n".join(report)
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


def test_matcher_resolves_local_indirection_and_scoped_zh_remaps():
    theme = (
        ':root { --ok: #0a0; --up: #0f0; --fresh-ok: var(--ok); }\n'
        'html[data-lang="zh"] { --up: #f00; }\n'
        'html[data-lang="zh"] .rrx { --ok: var(--up); }\n'
        'html[data-lang="zh"] :is(.igx, .igs) { --ok: var(--up); --ink-ok: var(--ink-up); }\n'
    )
    swapped = swapped_token_closure(theme)
    assert "--up" in swapped and "--ok" not in swapped

    # (a) local custom-property indirection: --rvc set from --ok in CSS + markup
    rrx_css = (
        '.rrx .rrx-rec { --rvc: var(--info); }\n'
        '.rrx .rrx-rec-chip.fresh { color: var(--rvc); }\n'
    )
    rrx_html = (
        "{%- set rvc = 'var(--ok)' if rv.receding else 'var(--info)' -%}\n"
        '<div class="rrx-rec" style="--rvc:{{ rvc }}"></div>\n'
    )
    assert freshness_offenders(rrx_css, swapped, theme_css=theme, alias_texts=[rrx_html]) == [
        (2, ".rrx .rrx-rec-chip.fresh", ["--rvc"])
    ]

    # (b) scoped zh remap of --ok inside .igs — counted-and-cleared by the old root-only harvest
    igs = '.igs .igs-dot.fresh { box-shadow: 0 0 0 2px color-mix(in srgb, var(--ok) 30%, transparent); }\n'
    assert freshness_offenders(igs, swapped, theme_css=theme) == [
        (1, ".igs .igs-dot.fresh", ["--ok"])
    ]

    # --fresh-ok inherited from :root escapes the remap (computes unremapped, inherits resolved)
    healed_rrx = '.rrx .rrx-rec-chip.fresh { color: var(--fresh-ok); }\n'
    assert freshness_offenders(healed_rrx, swapped, theme_css=theme) == []
    healed_igs = '.igs .igs-dot.fresh { box-shadow: 0 0 0 2px var(--fresh-ok); }\n'
    assert freshness_offenders(healed_igs, swapped, theme_css=theme) == []

    # redeclaring the alias inside the remap zone re-resolves against remapped --ok
    trap = (
        '.rrx { --fresh-ok: var(--ok); }\n'
        '.rrx .rrx-rec-chip.fresh { color: var(--fresh-ok); }\n'
    )
    assert freshness_offenders(trap, swapped, theme_css=theme) == [
        (2, ".rrx .rrx-rec-chip.fresh", ["--fresh-ok"])
    ]

    # a freshness rule OUTSIDE the remap zone may still use --ok
    outside = '.imd-chip.fresh { color: var(--ink-ok, var(--ok)); }\n'
    assert freshness_offenders(outside, swapped, theme_css=theme) == []


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
