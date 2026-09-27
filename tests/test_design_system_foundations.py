"""tests/test_design_system_foundations.py — design-system packet PR-0(a)(b).

Guards the two foundations every later migration builds on:

  * **(a) the site type ramp.** The 11-step ``--fs-*`` scale was invented inside
    ``body.page-macro`` (dashboard.html.j2) and hand-copied into three more page
    templates. PR-0 promotes it VERBATIM to ``:root`` in theme.css. It must live at
    ``:root`` and not on a body class: ``body.page-stocks`` (the Prophet board), the
    ``seo_*`` estate children and ``/calculators`` all consume ``var(--fs-*)`` without
    ever declaring it, so a body-scoped home silently drops them off the scale.
  * **(b) the three shared primitives** (``.mx-ladder`` / ``.mx-chg-row`` /
    ``.mx-empty``), so ``build_site.py`` and ``build_vector.py`` templates consume one
    definition instead of re-inventing a local family each.

WHY THIS SUITE IS BROWSER-FREE. The CI packs install a minimal dependency set, not
``requirements.txt`` — a ``pytest.importorskip("playwright")`` here would SKIP in CI and
report green while proving nothing (house trap: ci-packs-install-minimal-deps-not-requirements).
So the language-toggle check below does not measure a browser: it RESOLVES THE CASCADE
against the shipped theme.css with a small matcher (stdlib only), which is the property
that actually broke. The browser measurement that confirms it — ``getComputedStyle`` in
both locales — is run by hand and pasted into the PR body.

THE DEFECT THIS PINS. ``.mx-ladder .mx-lad-total small { display:block }`` and theme.css's
own ``html[data-lang="zh"] .l-en { display:none }`` both land at specificity (0,2,1). The
toggle is declared EARLIER in the file, so source order hands the tie to the ``display:block``
rule and BOTH language labels print in the total cell under zh ("47 setups 形态"). The
restoring rule is what makes exactly one label paint, and deleting it is the mutation this
suite must fail on.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "templates" / "theme.css"

# The promoted ramp, value-for-value as it left body.page-macro. A change here is a
# RETUNE of the whole site and must be a deliberate, reviewed act — not a side effect.
SITE_RAMP = {
    "--fs-display": "46px",
    "--fs-num-xl": "38px",
    "--fs-h1": "28px",
    "--fs-num-lg": "22px",
    "--fs-h2": "17px",
    "--fs-md": "15px",
    "--fs-body": "14px",
    "--fs-h3": "14px",
    "--fs-sm": "12.5px",
    "--fs-label": "11px",
    "--fs-micro": "10px",
}

# Page-local ramp declarations that are allowed to survive the promotion, because their
# value genuinely DIFFERS from the site ramp. PR-0 promotes; it does not retune. Each is
# a design decision owned by that page's own lane.
DOCUMENTED_OVERRIDES = {
    "templates/leader_radar.html.j2": {"--fs-display": "44px", "--fs-h1": "27px", "--fs-h2": "16px"},
    "templates/intraday_flow.html.j2": {"--fs-display": "44px", "--fs-h1": "27px"},
}


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


@pytest.fixture(scope="module")
def theme() -> str:
    return THEME.read_text(encoding="utf-8")


# ── (a) the ramp ────────────────────────────────────────────────────────────────────

def test_the_site_type_ramp_is_declared_at_root(theme):
    """All 11 steps, at :root, with the exact promoted values."""
    body = _root_block(theme)
    for token, value in SITE_RAMP.items():
        m = re.search(rf"{re.escape(token)}\s*:\s*([^;]+);", body)
        assert m, f"{token} is not declared in theme.css's :root block"
        assert m.group(1).strip() == value, (
            f"{token} is {m.group(1).strip()!r}, expected {value!r} — PR-0 promoted the ramp "
            f"verbatim; changing a value here re-sizes every page at once."
        )


def _root_block(theme: str) -> str:
    """The first top-level ``:root { … }`` block of theme.css."""
    css = _strip_comments(theme)
    i = css.index(":root")
    depth, start = 0, css.index("{", i)
    for j in range(start, len(css)):
        if css[j] == "{":
            depth += 1
        elif css[j] == "}":
            depth -= 1
            if depth == 0:
                return css[start : j + 1]
    raise AssertionError("unterminated :root block in theme.css")


def test_the_ramp_is_not_scoped_to_a_body_class(theme):
    """body.page-stocks (Prophet) never declares the ramp and inherits ONLY via :root."""
    block = _root_block(theme)
    assert all(t in block for t in SITE_RAMP), "the ramp must be in the :root block itself"


def test_no_page_template_shadows_the_ramp_except_documented_overrides():
    """Every surviving page-local --fs-* declaration must be a KNOWN, differing override."""
    offenders: list[str] = []
    for path in sorted((ROOT / "templates").rglob("*.j2")):
        rel = path.relative_to(ROOT).as_posix()
        allowed = DOCUMENTED_OVERRIDES.get(rel, {})
        for token, value in re.findall(r"(--fs-[a-z0-9-]+)\s*:\s*([^;]+);", _strip_comments(path.read_text(encoding="utf-8"))):
            if token not in SITE_RAMP:
                continue  # not a ramp step (e.g. bonds' --fs-hero) — out of scope
            value = value.strip()
            if token not in allowed:
                offenders.append(f"{rel}: {token}:{value} shadows the site ramp — remove it")
            elif allowed[token] != value:
                offenders.append(f"{rel}: {token}:{value} != documented override {allowed[token]}")
    assert not offenders, "page-local ramp shadows found:\n  " + "\n  ".join(offenders)


def test_documented_overrides_actually_differ_from_the_site_ramp():
    """An 'override' equal to the ramp is a leftover shadow, not a decision."""
    for rel, tokens in DOCUMENTED_OVERRIDES.items():
        for token, value in tokens.items():
            assert value != SITE_RAMP[token], (
                f"{rel} {token}:{value} equals the site ramp — delete it and inherit instead"
            )


# ── (b) the primitives ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("selector", [".mx-ladder", ".mx-chg-row", ".mx-empty"])
def test_the_shared_primitive_is_defined_in_theme_css(theme, selector):
    # A trailing :not()/compound is allowed: C8-C split the ladder into two disjoint
    # forms (the generic bar and .mx-ladder--board), so the bar's own rule now reads
    # `.mx-ladder:not(.mx-ladder--board) {`. What this guard is for is that the
    # primitive has ONE definition in theme.css rather than a page-local re-invention,
    # and that is unchanged — so the pattern accepts the qualifier and nothing else
    # (no descendant space, no comma).
    pattern = rf"^{re.escape(selector)}(?::[a-z-]+\([^)]*\))*\s*\{{"
    assert re.search(pattern, _strip_comments(theme), re.M), (
        f"{selector} must be defined in theme.css so both builders consume one definition"
    )


def test_mx_empty_why_ships_with_mx_empty(theme):
    """Doctrine: a null is disclosed in plain words, so the empty state carries its reason."""
    css = _strip_comments(theme)
    assert ".mx-empty" in css and re.search(r"^\.mx-empty-why\s*\{", css, re.M), (
        ".mx-empty-why is REQUIRED alongside .mx-empty — an empty state without its why "
        "is a bare blank, which the doctrine forbids"
    )


def test_the_ladder_carries_sol_scoping_rider(theme):
    """Sol §J.9 (2026-08-12): .mx-ladder is scoped to Prophet/lifecycle-derived surfaces."""
    m = re.search(r"/\*[^*]*(?:\*(?!/)[^*]*)*\*/\s*\.mx-ladder(?::[a-z-]+\([^)]*\))*\s*\{", theme)
    assert m, ".mx-ladder must carry a comment immediately above its rule"
    comment = m.group(0)
    assert "J.9" in comment and "MUST NOT proliferate" in comment, (
        "the comment above .mx-ladder must record Sol's binding §J.9 scope rider"
    )


# ── (b2) loading + error states — the other two non-live states (P-MP1-SHELL gate) ──
#
# MP-1 Amendment 1 (V-B4) makes review of §10's loading/error states blocking against
# the specimen's own .skel / .mx-error components. This section is the DS-PR that
# discharges that gate: it ports both, verbatim, from
# mockups/design_system/specimen.html:112-116 into theme.css, additive-only, with zero
# consumers wired here (the shell builder owns markup wiring next).

SPECIMEN = ROOT / "mockups" / "design_system" / "specimen.html"


@pytest.fixture(scope="module")
def specimen() -> str:
    return SPECIMEN.read_text(encoding="utf-8")


def _rule_body(css: str, selector_pattern: str) -> str:
    """First balanced-brace rule body whose selector matches ``selector_pattern`` at
    the start of a line — a generalisation of ``_root_block`` above to an arbitrary
    anchored selector (comments already stripped by the caller's fixture source)."""
    stripped = _strip_comments(css)
    m = re.search(rf"^{selector_pattern}\s*\{{", stripped, re.M)
    assert m, f"selector {selector_pattern!r} not found"
    depth, start = 0, m.end() - 1
    for j in range(start, len(stripped)):
        if stripped[j] == "{":
            depth += 1
        elif stripped[j] == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : j + 1]
    raise AssertionError(f"unterminated rule for {selector_pattern!r}")


def _normalize_declarations(body: str) -> str:
    """Collapse whitespace, and drop the ONE documented accommodation — the
    DS-PR-0 --r-ctl/--r-card forward-compat fallback (see the comment above
    .skel in theme.css) — so the comparison judges the DECLARATION the specimen
    ships, not the landed-token workaround theme.css needs until DS-PR-0 lands
    the scale at :root. var(--r-ctl,8px) normalizes to var(--r-ctl), which is
    exactly what the specimen itself resolves to (specimen.html:24 defines
    --r-ctl:8px at :root), so this does not paper over an actual drift."""
    body = re.sub(r"var\(\s*(--r-ctl|--r-card)\s*,\s*[^)]+\)", r"var(\1)", body)
    body = re.sub(r"\s+", " ", body).strip()
    return re.sub(r"\s*\{", "{", body)


@pytest.mark.parametrize("selector", [r"\.skel", r"@keyframes skel", r"\.mx-error", r"\.mx-error b"])
def test_loading_error_rules_match_the_specimen_verbatim(theme, specimen, selector):
    """Drift guard: theme.css and the specimen can never silently diverge.

    Re-derives both rule bodies from source (not from a hand-copied constant) and
    compares them declaration-for-declaration, so a future edit to either file that
    is not mirrored in the other fails here rather than shipping unnoticed.
    """
    theme_body = _normalize_declarations(_rule_body(theme, selector))
    specimen_body = _normalize_declarations(_rule_body(specimen, selector))
    assert theme_body == specimen_body, (
        f"{selector} has drifted from the specimen:\n"
        f"  theme.css:  {theme_body}\n"
        f"  specimen:   {specimen_body}"
    )


def test_skel_reduced_motion_guard_present(theme):
    """prefers-reduced-motion disables the shimmer (specimen.html:165)."""
    css = _strip_comments(theme)
    assert re.search(
        r"@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*\{\s*"
        r"\.skel\s*\{\s*animation\s*:\s*none\s*;?\s*\}\s*\}",
        css,
    ), ".skel must be disabled under prefers-reduced-motion, per the specimen (line 165)"


def test_the_loading_and_error_states_are_additive_only(theme):
    """Purely-additive proof, by construction. The port was a single insertion
    between two byte-exact anchors that already shipped in theme.css: the last
    declaration PR-0(b) gave .mx-empty-why, and the first line of the comment
    C8-C gave the count ladder. If both anchors still read exactly as they did
    before this PR, nothing between or around them was touched — only the new
    block was inserted in the gap.
    """
    before_anchor = (
        ".mx-empty-why { color:var(--muted); font-size:var(--fs-sm); margin-top:4px; }"
    )
    after_anchor = (
        "/* Count ladder — control form; the active cell reads as WEIGHT (solid underline"
    )
    assert before_anchor in theme, "the pre-existing .mx-empty-why rule must be untouched"
    assert after_anchor in theme, "the pre-existing count-ladder comment must be untouched"
    gap = theme[theme.index(before_anchor) + len(before_anchor) : theme.index(after_anchor)]
    assert ".skel" in gap and ".mx-error" in gap, (
        "the new loading/error block must sit in the gap between the two untouched anchors"
    )


def test_no_consumer_wires_the_new_primitives_yet(theme):
    """Blast-radius guard for THIS PR: additive only, zero consumers estate-wide.

    The shell builder (P-MP1-SHELL / PR #6049 lane) owns wiring .skel/.mx-error into
    actual markup next. A consumer appearing in the same PR that ports the primitive
    would be undisclosed scope creep against this PR's own stated blast radius.
    """
    offenders = []
    for path in sorted((ROOT / "templates").rglob("*")):
        if not path.is_file() or path.suffix not in {".j2", ".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Token-exact: a naive `\bskel\b` false-boundaries on the hyphen in
        # page-local compounds like "trd-skel"/"oew-skel-bar"/"rx-skel" (all of
        # which are pre-existing, unrelated page classes, not this primitive) —
        # a hyphen is a non-word char, so `\b` fires on both of its sides and a
        # substring match would misreport every one of them as a consumer.
        # Split each class attribute on whitespace and check for the exact
        # token "skel" instead.
        has_skel = any(
            "skel" in cls.split()
            for cls in re.findall(r'class=["\']([^"\']*)["\']', text)
        )
        if has_skel or "mx-error" in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert not offenders, (
        f"unexpected consumers of .skel/.mx-error found: {offenders} — this PR is "
        "additive-only; wiring belongs to the shell builder (P-MP1-SHELL)"
    )


# ── (c) the archetype-B board ladder + the lifecycle weight grammar (C8-C) ──────────

#: The seven lifecycle states the grammar draws, over six distinct weights — Delivering
#: is deliberately Entered's solid commitment weight plus an arrival mark, not a seventh
#: weight, because a holder reads them as the same commitment at different stages. A
#: CLOSED set: the grammar is what lets a reader learn one vocabulary on the ladder and
#: re-read it on a card, so a state added without a weight would paint as nothing at all.
LIFECYCLE_STATES = ("watch", "ready", "entered", "delivering", "overtime", "invalidated",
                    "resolved")


@pytest.mark.parametrize("selector", [".mx-ladder--board", ".mx-mark", ".mx-cell"])
def test_the_board_ladder_primitives_are_defined_in_theme_css(theme, selector):
    """MP-1 §5 (Amendment 1) classes these as inherited DS primitives, not page-scoped
    inventions — so the packet's builder must find them here, in the shared sheet."""
    css = _strip_comments(theme)
    assert re.search(rf"(?:^|[\s,>]){re.escape(selector)}(?![\w-])", css, re.M), (
        f"{selector} must be defined in theme.css — MP-1 §5 reuses it as an inherited "
        "primitive, and a page-scoped copy is exactly what the namespace law forbids"
    )


@pytest.mark.parametrize("state", LIFECYCLE_STATES)
def test_every_lifecycle_state_ships_at_both_scales(theme, state):
    """One grammar, two scales: the cap on a ladder cell and the inline mark on a card.

    A state that ships at only one scale silently breaks the link the grammar exists
    to make — the ladder would name a state the card cannot echo, or the reverse.
    """
    css = _strip_comments(theme)
    for family in ("mx-cap", "mx-mark"):
        assert f".{family}--{state}" in css, (
            f".{family}--{state} is missing — the weight grammar must ship at BOTH scales "
            "(.mx-cap on a ladder cell, .mx-mark inline on a card/table row)"
        )


def test_the_weight_grammar_never_touches_a_direction_hue(theme):
    """Lifecycle is WEIGHT; stance is HUE. The two channels must never collide.

    The marks paint in currentColor/--text/--muted only. That is what makes the whole
    grammar byte-identical under the Chinese direction flip: if any weight referenced
    --up/--down/--q*, a plan's lifecycle state would silently recolour with the tape's
    convention and mean something different in the two languages.
    """
    css = _strip_comments(theme)
    block = re.search(r"\.mx-cell\s*>\s*\.mx-cap\s*\{.*?(?=\n@media|\nhtml\[)", css, re.S)
    assert block, "the weight-grammar block must be locatable for this guard to bind"
    banned = re.findall(r"var\(\s*(--(?:up|down|q[1-4]|pv-[a-z]+))\b", block.group(0))
    assert not banned, (
        f"the lifecycle weight grammar references {sorted(set(banned))} — a direction or "
        "stance hue inside a weight mark breaks the zh flip and collides the two channels"
    )


def test_the_cap_is_structurally_confined_to_ladder_cells(theme):
    """R4.2-corrected contract: .mx-cap is a LADDER-CELL cap and nothing else.

    The card's own top cap was repealed so it would stop competing with the chart for
    the card's head. Here that repeal is enforced by the selector rather than by prose
    plus an external guard: both the cap's base rule and its ``content:""`` are scoped
    to ``.mx-cell``, so a .mx-cap emitted anywhere else generates no box at all instead
    of a stray 3px artefact. Deleting the scope is the mutation this must fail on.
    """
    css = _strip_comments(theme)
    assert re.search(r"^\.mx-cell\s*>\s*\.mx-cap\s*\{", css, re.M), (
        ".mx-cap's base rule must be scoped to .mx-cell — an unscoped cap re-opens the "
        "repealed card-cap contract"
    )
    # EVERY rule that gives some .mx-cap a box, not just the first one found. The
    # weight modifiers are inert unscoped only because they declare no content of
    # their own; two of them (--delivering, --invalidated) DO declare it for their
    # second mark, and those shipped unscoped in this PR's first pass — a first-match
    # re.search found the base rule, reported green, and never looked at them.
    # Judged per comma-part: the shared `content` rule legitimately pairs a scoped
    # `.mx-cell > .mx-cap::before` with an unscoped `.mx-mark::before`, because
    # .mx-mark is a different primitive that is SUPPOSED to live outside a ladder.
    # Only the parts naming .mx-cap owe the scope.
    # Walk EVERY rule. The pattern deliberately carries no `}`/`^` anchor: an anchored
    # version consumes the closing brace of each match, so the very next rule has
    # nothing left to anchor on and is skipped — which is how a first draft of this
    # guard passed a mutation that reverted .mx-cap--delivering::after to unscoped.
    leaks = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, re.S):
        selector, body = m.group(1).strip(), m.group(2)
        if ".mx-cap" not in selector or not re.search(r"(?:^|;)\s*content\s*:", body):
            continue
        unscoped = [p.strip() for p in selector.split(",")
                    if ".mx-cap" in p and ".mx-cell" not in p]
        if unscoped:
            leaks.extend(unscoped)
    assert not leaks, (
        "these .mx-cap rules declare content:\"\" without .mx-cell scope, so a cap "
        f"emitted outside a ladder cell paints a stray box: {leaks}. Scope each as "
        "`.mx-cell > …` — the containment law is carried by the selector, not by prose."
    )


def test_the_two_ladder_forms_are_disjoint(theme):
    """The generic bar and the board grid must not half-inherit each other.

    ``.mx-ladder button:last-child`` and ``.mx-ladder button[aria-pressed]`` out-specify
    a bare ``.mx-cell``: on an element carrying both classes they would strip the
    terminal cell's dashed rule and double-mark selection. The bar's rules therefore
    exclude the board form explicitly.
    """
    css = _strip_comments(theme)
    # Every selector in the file, not just the ones anchored at column 0. The first
    # version of this guard anchored on `^\.mx-ladder`, which a prefixed rule walks
    # straight past: `html[data-theme="light"] .mx-ladder button {…}` is (0,2,2) and
    # BEATS `.mx-ladder--board .mx-cell` (0,2,0), so the exact collision the guard
    # exists to prevent could ship under a theme prefix and still report green.
    # :where() forms are included too — zero specificity does not mean zero reach.
    descendant = re.compile(
        r"\.mx-ladder(?!--board)(?!:not\(\s*\.mx-ladder--board\s*\))[\w:()\[\]\"'=-]*"
        r"[\s>+~]+[^,{]*?(?:\bbutton\b|\.mx-cell)"
    )
    leaks = []
    for m in re.finditer(r"(?:^|\}|\{)\s*([^{}]+?)\{", css, re.S):
        selector = m.group(1).strip()
        if selector.startswith("@") or "\n\n" in selector:
            continue
        for part in re.split(r",(?![^()]*\))", selector):
            for inner in re.findall(r":where\(([^()]*)\)", part) or [part]:
                for sub in inner.split(","):
                    if descendant.search(sub):
                        leaks.append(selector)
                        break
    assert not leaks, (
        "these rules reach a board child through the BAR form's selector: "
        f"{sorted(set(leaks))} — an element carrying both classes would inherit half "
        "of each form. Add :not(.mx-ladder--board), or scope the rule to the form it "
        "belongs to. Specificity is not a defence: a prefixed bar rule out-specifies "
        "`.mx-ladder--board .mx-cell`."
    )


def test_no_comment_closes_itself_early(theme):
    """A `*/` inside a comment's PROSE silently deletes the rule that follows it.

    Found the hard way in this PR: a comment reading "not re-keyed to --r-*/--fs-*"
    terminated at the `*/` in the middle of that token name. Everything after it —
    four more lines of prose plus the whole `.mx-ladder--board { display:grid … }`
    rule — became one unparseable declaration block, so the board ladder shipped with
    no grid at all while every regex-based guard in this file still passed: strip the
    comments the way a browser does and the selector is still right there in the text.

    The check is the residue of a NON-GREEDY comment strip, which is exactly what a
    CSS parser does. If a comment body contains an extra `*/`, the strip stops at it
    and the comment's real terminator is left behind in the residue — so a stray `*/`
    outside any comment is a proof of the defect, not a heuristic for it.
    """
    residue = _strip_comments(theme)
    assert "*/" not in residue, (
        "a comment in theme.css closes early — some token in its prose contains `*/`, "
        "which ends the comment and swallows the next rule into unparseable garbage. "
        f"First offence near: ...{residue[max(0, residue.index('*/') - 90):residue.index('*/') + 40]}..."
    )


# ── the language toggle, resolved through the real cascade ──────────────────────────

_ATTR = re.compile(r"\[([a-zA-Z0-9_-]+)(?:([~|^$*]?=)\"?([^\]\"]*)\"?)?\]")


def _parse_compound(sel: str) -> dict:
    """A single compound selector -> {tag, classes, attrs, negations}."""
    negations = []
    while True:
        m = re.search(r":not\(([^()]*)\)", sel)
        if not m:
            break
        negations.append(_parse_compound(m.group(1)))
        sel = sel[: m.start()] + sel[m.end() :]
    classes = set(re.findall(r"\.([a-zA-Z0-9_-]+)", sel))
    attrs = [(a, op, v) for a, op, v in _ATTR.findall(sel)]
    tag = re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", sel)
    return {"tag": tag.group(1) if tag else None, "classes": classes,
            "attrs": attrs, "negations": negations}


def _matches(compound: dict, el: dict) -> bool:
    if compound["tag"] and compound["tag"] != el["tag"]:
        return False
    if not compound["classes"] <= el["classes"]:
        return False
    for name, op, value in compound["attrs"]:
        if name not in el["attrs"]:
            return False
        if op and el["attrs"][name] != value:
            return False
    return not any(_matches(n, el) for n in compound["negations"])


def _specificity(selector: str) -> tuple[int, int, int]:
    flat = re.sub(r":not\(([^()]*)\)", r" \1 ", selector)
    ids = len(re.findall(r"#[a-zA-Z0-9_-]+", flat))
    classes = len(re.findall(r"\.[a-zA-Z0-9_-]+", flat)) + len(_ATTR.findall(flat))
    elements = len(re.findall(r"(?:^|[\s>+~])([a-zA-Z][a-zA-Z0-9]*)", flat))
    return ids, classes, elements


def _selector_matches_chain(selector: str, chain: list[dict]) -> bool:
    """Descendant-combinator matching, right to left, against an ancestor chain."""
    compounds = [_parse_compound(p) for p in selector.split() if p.strip()]
    if not compounds or not _matches(compounds[-1], chain[-1]):
        return False
    i = len(chain) - 2
    for compound in reversed(compounds[:-1]):
        while i >= 0 and not _matches(compound, chain[i]):
            i -= 1
        if i < 0:
            return False
        i -= 1
    return True


def _top_level_rules(css: str):
    """(selector_list, declarations, order) for every rule OUTSIDE an at-block.

    At-blocks are skipped deliberately: moving the restoring rule into a @media would
    change when it applies, and this resolver should notice rather than absorb it.
    """
    css = _strip_comments(css)
    out, i, order = [], 0, 0
    while i < len(css):
        brace = css.find("{", i)
        if brace < 0:
            break
        prelude = css[i:brace].strip()
        depth, j = 1, brace + 1
        while j < len(css) and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        if not prelude.startswith("@"):
            out.append((prelude, css[brace + 1 : j - 1], order))
            order += 1
        i = j
    return out


def _resolve_display(css: str, chain: list[dict]) -> str:
    """The winning `display` for chain[-1]: max by (!important, specificity, source order)."""
    best, winner = None, "inline"  # <small> initial display
    for prelude, decls, order in _top_level_rules(css):
        m = re.search(r"(?:^|;)\s*display\s*:\s*([^;]+)", decls)
        if not m:
            continue
        value = m.group(1).strip()
        important = value.endswith("!important")
        value = value.replace("!important", "").strip()
        for selector in prelude.split(","):
            selector = selector.strip()
            if not selector or not _selector_matches_chain(selector, chain):
                continue
            key = (important, _specificity(selector), order)
            if best is None or key > best:
                best, winner = key, value
    return winner


def _ladder_label_chain(lang: str, label_class: str) -> list[dict]:
    return [
        {"tag": "html", "classes": set(), "attrs": {"data-lang": lang}},
        {"tag": "body", "classes": set(), "attrs": {}},
        {"tag": "div", "classes": {"mx-ladder"}, "attrs": {}},
        {"tag": "div", "classes": {"mx-lad-total"}, "attrs": {}},
        {"tag": "small", "classes": {label_class}, "attrs": {}},
    ]


def test_the_language_toggle_resolver_agrees_with_theme_css_on_a_plain_label(theme):
    """Sanity-check the resolver itself against the toggle's uncontested behaviour."""
    plain = [
        {"tag": "html", "classes": set(), "attrs": {"data-lang": "zh"}},
        {"tag": "span", "classes": {"l-en"}, "attrs": {}},
    ]
    assert _resolve_display(theme, plain) == "none", "resolver disagrees with the base toggle"


@pytest.mark.parametrize(
    "lang,visible,hidden",
    [("en", "l-en", "l-zh"), ("zh", "l-zh", "l-en")],
)
def test_ladder_total_prints_exactly_one_language_label(theme, lang, visible, hidden):
    """The regression: theme.css must not out-specify its own language toggle.

    Under zh the total cell read "47 setups 形态" — both labels — because
    `.mx-ladder .mx-lad-total small { display:block }` ties the toggle on specificity
    (0,2,1) and wins on source order. Deleting the restoring rule fails this test.
    """
    shown = _resolve_display(theme, _ladder_label_chain(lang, visible))
    gone = _resolve_display(theme, _ladder_label_chain(lang, hidden))
    assert shown != "none", f"[{lang}] .{visible} is hidden — the ladder total has no label"
    assert gone == "none", (
        f"[{lang}] .{hidden} resolves to {gone!r}, not 'none' — BOTH language labels paint "
        f"in the ladder total. theme.css is out-specifying its own language toggle; keep the "
        f"restoring rule below .mx-ladder .mx-lad-total small."
    )


def test_specimen_language_toggle_updates_document_language(specimen):
    """Visible locale and the assistive-technology language must change together.

    This is a browser-free source-contract guard for the specimen's small toggle,
    not a JavaScript interpreter. The real-browser R5 observation found data-lang
    switched to zh while html lang stayed en. Executing the actual handler and
    checking both directions is separate behavior evidence in the repair record.
    """
    scripts = "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", specimen, re.S))
    handler = re.search(
        r"document\.getElementById\(['\"]t-lang['\"]\)\.onclick\s*=\s*function\s*\(\)\s*\{(.*?)\};",
        scripts, re.S,
    )
    assert handler, "The specimen language control must have an inspectable handler"
    body = re.sub(r"\s+", "", handler.group(1)).replace('"', "'")
    assert "root.setAttribute('data-lang'," in body, "Keep the visual locale binding"
    assert "root.setAttribute('lang',root.getAttribute('data-lang')==='zh'?'zh-CN':'en');" in body, (
        "The specimen changes the visible locale but not the document language; "
        "bind html lang to the resulting data-lang using the existing zh-CN/en mapping."
    )


# Specimen-only layout: retain every example without widening the document.
@pytest.mark.parametrize("selector", [r"\.spec-grid", r"\.do-dont"])
def test_specimen_grid_minimum_fits_its_container(specimen, selector):
    body = re.sub(r"\s+", "", _rule_body(specimen, selector))
    assert "minmax(min(300px,100%),1fr)" in body


def test_specimen_type_samples_reflow_without_reducing_the_ramp(specimen):
    assert "flex-wrap:wrap" in re.sub(r"\s+", "", _rule_body(specimen, r"\.trow"))
    sample = re.sub(r"\s+", "", _rule_body(specimen, r"\.trow > span"))
    assert "max-width:100%" in sample and "overflow-wrap:anywhere" in sample
    assert "font-size" not in sample


def test_specimen_static_lens_and_long_buttons_fit_the_panel(specimen):
    lens = re.sub(r"\s+", "", _rule_body(specimen, r"\.lens-pop-demo"))
    assert "max-width:100%" in lens and "box-sizing:border-box" in lens
    button = re.sub(r"\s+", "", _rule_body(specimen, r"\.wrap \.gbtn"))
    assert "max-width:100%" in button and "white-space:normal" in button


def test_specimen_wide_tables_keep_an_explicit_scroll_container(specimen):
    tables = re.findall(r'<table class="mx-tbl"', specimen)
    wrapped = re.findall(r'<div class="mx-tblbox"[^>]*>\s*<table class="mx-tbl"', specimen)
    assert tables and len(wrapped) == len(tables), "Every wide table needs its existing scroll wrapper"
    ladder = re.sub(r"\s+", "", _rule_body(specimen, r"\.mx-ladder"))
    assert "overflow-x:auto" in ladder, "Late ladder cells must be reachable, not clipped"


def test_specimen_long_reference_copy_can_wrap(specimen):
    body = re.sub(r"\s+", "", _rule_body(specimen, r"\.mockup-note"))
    assert "overflow-wrap:anywhere" in body


def test_specimen_binds_the_existing_mobile_spine_preview(specimen):
    # The owner CSS intentionally scopes narrow spine rows to page-macro or this
    # preview adapter. The specimen must use the adapter, not copy production CSS.
    assert re.search(r'<div class="wrap mockup-spine-390">', specimen)
    assert not re.search(r'<body[^>]*class="[^"]*page-macro', specimen)


# R7: prepared recoveries are examples in the incumbent specimen, not a save engine.
def _prepared_case(specimen, kind, name):
    block = re.search(r'<article\b[^>]*data-spec-' + kind + r'="' + name + r'"[^>]*>(.*?)</article>', specimen, re.S)
    assert block, f"Missing existing-component example: {kind}/{name}"
    return block.group(1)


@pytest.mark.parametrize("state", ["loading", "stale", "error", "empty", "filtered-empty", "partial", "conflicting", "locked"])
def test_prepared_recovery_state_is_bilingual_and_explicit(specimen, state):
    body = _prepared_case(specimen, "state", state)
    assert 'class="l-en"' in body and 'class="l-zh"' in body
    assert not re.search(r'\brole="(?:alert|status)"', body), "Static gallery examples must not announce fictional events"


@pytest.mark.parametrize("outcome", ["ready", "pending", "confirmed", "failed", "unknown"])
def test_prepared_save_examples_cannot_submit_fictional_actions(specimen, outcome):
    body = _prepared_case(specimen, "save", outcome)
    buttons = re.findall(r'<button\b([^>]*)>', body)
    assert buttons and all('type="button"' in x and re.search(r'\bdisabled(?:\s|=|$)', x) for x in buttons)
    assert 'class="l-en"' in body and 'class="l-zh"' in body
    assert 'onclick=' not in body and '<form' not in body
    if outcome == "unknown":
        assert "Check save status" in body and "查询保存状态" in body
        assert "Try saving again" not in body


def test_prepared_recovery_denominators_and_caveats_are_not_hidden(specimen):
    partial = _prepared_case(specimen, "state", "partial")
    at_rest = partial.split('<details', 1)[0]
    assert "6 of 9 above average" in at_rest and "3 of 12" in at_rest
    assert "6 / 9" in partial and "6 / 12" not in partial
    assert "All 24 checked" in _prepared_case(specimen, "state", "empty")
    assert "12 items" in _prepared_case(specimen, "state", "filtered-empty")
    conflicting = _prepared_case(specimen, "state", "conflicting").split('<details', 1)[0]
    assert "Entry: Ready" in conflicting and "Extension: Wait" in conflicting
    assert "No combined entry call" in conflicting


def test_prepared_recovery_uses_native_inspection_not_nested_modals(specimen):
    for state in ["stale", "empty", "filtered-empty", "partial", "conflicting", "locked"]:
        body = _prepared_case(specimen, "state", state)
        assert '<details class="mx-disc"' in body
        assert '<summary' in body and 'data-spec-inspect=' in body
        assert not re.search(r'<details[^>]*>.*<details', body, re.S)
        assert '<dialog' not in body
    assert 'id="specimen-state-actions-note"' in specimen
    assert "Fictional examples" in specimen and "not connected" in specimen


def test_prepared_recovery_does_not_add_a_persistence_or_state_engine(specimen):
    script = "\n".join(re.findall(r'<script\b[^>]*>(.*?)</script>', specimen, re.S))
    assert not re.search(r'localStorage|sessionStorage|fetch\(|XMLHttpRequest|setInterval', script)
    assert "data-spec-save" not in script and "data-spec-state" not in script


def test_prepared_samples_keep_internal_delivery_language_out_of_customer_copy(specimen):
    samples = re.findall(r'<article\b[^>]*data-spec-(?:state|save)="[^"]+"[^>]*>(.*?)</article>', specimen, re.S)
    assert samples
    forbidden = ("owner confirms", "original request", "effect is unknown", "保存服务", "原请求")
    for body in samples:
        assert not any(term in body for term in forbidden), "Customer examples must not expose delivery plumbing"


# Executable-reference tab semantics; browser behavior is qualified separately.
def _specimen_tab_nodes(specimen):
    from html.parser import HTMLParser

    class Nodes(HTMLParser):
        def __init__(self):
            super().__init__()
            self.items = []
        def handle_starttag(self, tag, attrs):
            self.items.append((tag, dict(attrs)))

    parser = Nodes()
    parser.feed(specimen)
    return parser.items


def test_specimen_tabs_use_distinct_reciprocal_panels(specimen):
    nodes = _specimen_tab_nodes(specimen)
    tabs = [a for _, a in nodes if a.get('role') == 'tab']
    targets = [a.get('aria-controls') for a in tabs]
    assert len(tabs) == 3 and len(set(targets)) == 3, 'Three tasks need three actual panels'
    for tab in tabs:
        matching = [a for _, a in nodes if a.get('id') == tab['aria-controls']]
        assert len(matching) == 1
        assert matching[0].get('role') == 'tabpanel'
        assert matching[0].get('aria-labelledby') == tab['id']


def test_specimen_tabs_have_one_initial_keyboard_entry(specimen):
    nodes = _specimen_tab_nodes(specimen)
    tabs = [(tag, a) for tag, a in nodes if a.get('role') == 'tab']
    selected = [a for _, a in tabs if a.get('aria-selected') == 'true']
    assert len(selected) == 1
    assert all(tag == 'button' and a.get('type') == 'button' for tag, a in tabs)
    for _, tab in tabs:
        assert tab.get('tabindex') == ('0' if tab in selected else '-1')
        panel = next(a for _, a in nodes if a.get('id') == tab['aria-controls'])
        assert panel.get('tabindex') == '0'
        assert ('hidden' in panel) == (tab not in selected)
    tablist = next(a for _, a in nodes if a.get('role') == 'tablist')
    assert any(a.get('id') == tablist.get('aria-labelledby') for _, a in nodes)


@pytest.mark.parametrize('key', ['ArrowLeft', 'ArrowRight', 'Home', 'End'])
def test_specimen_tabs_name_keyboard_navigation_keys(specimen, key):
    scripts = '\n'.join(re.findall(r'<script\b[^>]*>(.*?)</script>', specimen, re.S))
    assert key in scripts


def test_specimen_tabs_restore_history_without_rebuilding_content(specimen):
    scripts = '\n'.join(re.findall(r'<script\b[^>]*>(.*?)</script>', specimen, re.S))
    assert 'hashchange' in scripts and 'popstate' in scripts
    assert '.hidden =' in scripts and 'pushState' in scripts
    assert not re.search(r'innerHTML\s*=|localStorage|sessionStorage|fetch\(', scripts)


def test_specimen_tabs_state_the_example_boundary(specimen):
    assert 'id="specimen-tabs-note"' in specimen
    assert 'Fictional examples' in specimen and '虚构示例' in specimen
    assert 'No filing examples loaded' in specimen


def test_specimen_tabs_simple_fundamentals_do_not_require_sideways_reading(specimen):
    panel = specimen.split('id="pane-fundamentals"', 1)[1].split('id="pane-filings"', 1)[0]
    assert re.search(r'<table class="mx-tbl" style="min-width:0">', panel)
    assert '>Revenue trend<' not in panel and '>Margin trend<' not in panel


# First-use reference journey: preparation, honest comparison and direct access.
def _specimen_prepared_answer(specimen):
    start = specimen.index('<section class="spec-sec" id="spec-identity"')
    return specimen[start:specimen.index('</section>', start)]


def test_specimen_has_one_title_main_and_skip_link(specimen):
    nodes = _specimen_tab_nodes(specimen)
    assert sum(tag == 'h1' for tag, _ in nodes) == 1
    assert sum(tag == 'main' for tag, _ in nodes) == 1
    skip = next(a for tag, a in nodes if tag == 'a' and a.get('class') == 'spec-skip')
    assert skip['href'] == '#specimen-main'
    main = next(a for tag, a in nodes if tag == 'main')
    assert main['id'] == 'specimen-main' and main.get('tabindex') == '-1'


def test_specimen_task_directory_has_real_reachable_destinations(specimen):
    nodes = _specimen_tab_nodes(specimen)
    nav = next(a for tag, a in nodes if tag == 'nav' and a.get('id') == 'specimen-directory')
    assert nav.get('aria-labelledby') == 'specimen-directory-title'
    jumps = [a for tag, a in nodes if tag == 'a' and a.get('class') == 'spec-jump']
    assert len(jumps) == 6
    assert len({a['href'] for a in jumps}) == 6
    for link in jumps:
        matching = [a for _, a in nodes if a.get('id') == link['href'][1:]]
        assert link['href'].startswith('#') and len(matching) == 1
        assert matching[0].get('tabindex') == '-1'


def test_specimen_answer_is_explicitly_fictional_not_live_or_trade_authority(specimen):
    body = _specimen_prepared_answer(specimen)
    assert 'Fictional example' in body and '虚构示例' in body
    assert 'Index up. Breadth weak.' in body
    assert 'dtp-chip--live' not in body and '>LIVE<' not in body and '>Act<' not in body
    assert 'Positive index returns do not establish broad participation.' in body
    assert body.index('Positive index returns') < body.index('<details')


@pytest.mark.parametrize('read,value', [('index','+1.2%'),('equal-weight','−0.6%'),('participation','3 of 11')])
def test_specimen_answer_exposes_comparable_evidence_at_rest(specimen, read, value):
    body = _specimen_prepared_answer(specimen).split('<details', 1)[0]
    assert 'data-spec-read="'+read+'"' in body and value in body
    assert '5 sessions ending 28 Aug 2026' in body


def test_specimen_complete_breakdown_reconciles_the_participation_count(specimen):
    from decimal import Decimal
    body = _specimen_prepared_answer(specimen)
    nodes = _specimen_tab_nodes(body)
    rows = [a for tag, a in nodes if tag == 'tr' and 'data-spec-change' in a]
    assert len(rows) == 11
    assert sum(Decimal(a['data-spec-change']) > 0 for a in rows) == 3
    assert sum(Decimal(a['data-spec-change']) <= 0 for a in rows) == 8
    assert 'data-spec-total="11"' in body and 'data-spec-unavailable="0"' in body


def test_specimen_inspection_returns_to_the_same_assessment(specimen):
    body = _specimen_prepared_answer(specimen)
    assert '<details class="mx-disc" id="spec-sector-breakdown"' in body
    assert 'href="#spec-answer-title"' in body
    assert 'id="spec-answer-title" tabindex="-1"' in body
    assert 'Inspect all 11 sectors' in body and 'Back to assessment' in body
    assert 'role="dialog"' not in body


def test_specimen_navigation_accounts_for_resized_header_without_hiding_content(specimen):
    assert 'ResizeObserver' in specimen and '--spec-header-height' in specimen
    assert 'scroll-margin-block-start' in specimen
    assert 'scrollIntoView({behavior:' not in specimen
    assert re.search(r'\.spec-jump[^{}]*\{[^}]*min-height:var\(--sp-8\)', specimen)



def test_specimen_answer_deep_link_includes_example_and_window(specimen):
    body = _specimen_prepared_answer(specimen)
    assert body.index('id="spec-answer-title"') < body.index('Fictional example')
    assert '<header id="spec-answer-title" tabindex="-1">' in body


def test_specimen_sector_rows_use_readable_body_text(specimen):
    row = re.sub(r"\s+", "", _rule_body(specimen, r"\.spec-answer \.mx-tbl tbody th"))
    assert 'font-size:var(--fs-body)' in row and 'text-transform:none' in row


def test_specimen_unavailable_spine_has_no_orphan_travel_cell(specimen):
    # The existing narrow null-row grid has name/stance/rail, no travel area.
    # An extra travel cell creates an implicit column on text enlargement.
    assert 'data-null="1"' in specimen
    assert '<div class="mx-spine-travel"><span class="muted">—</span></div>' not in specimen
    assert 'Unavailable' in specimen and '暂无数据' in specimen  # A missing read does not imply an active refresh.


def test_specimen_prepared_answer_reuses_the_existing_verdict_primitive(specimen):
    body = _specimen_prepared_answer(specimen)
    assert 'class="spec-answer mx-vh"' in body
    assert 'class="mx-vh-word"' in body and 'class="mx-vh-clause"' in body


# Quantitative comparison examples must encode the numbers they actually state.
def _spine_examples(specimen):
    return specimen.split('<!-- ══ 6.5', 1)[1].split('<!-- ══ 7 ·', 1)[0]


def _spine_group(specimen, group):
    part = _spine_examples(specimen).split(f'data-spec="{group}"', 1)[1]
    return part.split('</div>\n\n    <p', 1)[0] if group == 'ud-b1' else part


def _spine_rows(specimen, group):
    part = _spine_group(specimen, group)
    limit = 5 if group == 'ud-b1' else 3
    return re.split(r'(?=<div class="mx-spine-row")', part)[1:limit+1]


def _spine_geometry(row):
    def percent(cls, prop):
        tag = next(a for _, a in _specimen_tab_nodes(row) if cls in a.get('class', '').split())
        return float(re.search(rf'(?:^|;)\s*{prop}:([\d.]+)%', tag['style']).group(1))
    travel = re.search(r'class="mx-spine-travel".*?<span class="tnum">([^<]+)</span>', row, re.S)
    return (percent('mx-spine-prev', 'left'), percent('mx-spine-mark', 'left'),
            percent('mx-spine-conn', 'left'), percent('mx-spine-conn', 'width'),
            float(travel.group(1).replace('−', '-')))


@pytest.mark.parametrize('row_number', range(4))
def test_spine_comparison_markers_connector_and_change_agree(specimen, row_number):
    row = _spine_rows(specimen, 'ud-b1')[row_number]
    previous, current, start, distance, change = _spine_geometry(row)
    assert current - previous == change, 'Earlier marker disagrees with stated change'
    assert start == min(previous, current), 'Connector must begin at the lower endpoint'
    assert distance == abs(change), 'Connector length must equal the stated movement'
    assert 0 <= min(previous, current) <= max(previous, current) <= 100
    assert ('←' if change < 0 else '→') in row


@pytest.mark.parametrize('row_number', [0, 1])
def test_spine_comparison_narrow_examples_preserve_both_endpoints(specimen, row_number):
    assert _spine_geometry(_spine_rows(specimen, 'ud-b1-390')[row_number]) == _spine_geometry(_spine_rows(specimen, 'ud-b1')[row_number])


def test_spine_comparison_exposes_complete_same_window_values(specimen):
    section = _spine_examples(specimen)
    assert 'id="spec-spine-values"' in section and 'id="spec-spine-context"' in section
    assert '2026-07-12' in section and '2026-08-12' in section
    assert 'Fictional' in section and '虚构' in section
    assert 'Score points' in section and '分值' in section
    table = section.split('id="spec-spine-values"', 1)[1].split('</table>', 1)[0]
    caption = re.search(r'<caption>(.*?)</caption>', table, re.S).group(1)
    assert 'Fictional values' in caption and '虚构分值' in caption and '2026' in caption
    rows = re.findall(r'<tr data-spec-spine-market="([^"]+)">(.*?)</tr>', table, re.S)
    assert len(rows) == 5
    for i, (_, row) in enumerate(rows[:4]):
        nums = re.findall(r'<td class="tnum">([+−\d.]+)</td>', row)
        assert len(nums) == 3
        earlier, current, change = [float(x.replace('−', '-')) for x in nums]
        expected = _spine_geometry(_spine_rows(specimen, 'ud-b1')[i])
        assert (earlier, current, change) == (expected[0], expected[1], expected[4])
    assert 'Unavailable' in rows[-1][1] and '暂无数据' in rows[-1][1]
    assert not re.search(r'<td[^>]*>\s*0\s*</td>', rows[-1][1])


def test_spine_comparison_summary_is_not_a_trade_or_return_estimate(specimen):
    section = _spine_examples(specimen)
    assert 'id="spec-spine-summary"' in section
    summary = section.split('id="spec-spine-summary"', 1)[1].split('</p>', 1)[0]
    assert '2 toward risk-on' in summary and '2 toward risk-off' in summary and '1 unavailable' in summary
    assert 'not price returns' in section and 'not probabilities' in section
    assert 'Example stance' in section and '示例立场' in section


def test_spine_comparison_values_are_native_readable_disclosure(specimen):
    section = _spine_examples(specimen)
    assert re.search(r'<details[^>]+id="spec-spine-details"', section)
    assert 'id="spec-spine-inspect"' in section
    assert re.search(r'<table class="mx-tbl" id="spec-spine-values"', section)
    assert '<caption>' in section and 'scope="col"' in section and 'scope="row"' in section
    assert 'aria-describedby="spec-spine-context spec-spine-summary"' in section
    assert 'role="dialog"' not in section and 'aria-hidden="true" id="spec-spine-values"' not in section


def test_spine_comparison_null_rows_never_grow_measured_marks(specimen):
    for group in ['ud-b1', 'ud-b1-390']:
        row = _spine_rows(specimen, group)[-1]
        assert 'data-null="1"' in row
        for cls in ['mx-spine-mark', 'mx-spine-prev', 'mx-spine-conn', 'mx-spine-travel']:
            assert not any(cls in a.get('class', '').split() for _, a in _specimen_tab_nodes(row))


def test_spine_comparison_material_preview_uses_the_same_example(specimen):
    section = _spine_examples(specimen)
    preview = section.split('class="mx-tier-blurred--spec"', 1)[1].split('<p class="mockup-note', 1)[0]
    assert 'aria-hidden="true"' in preview
    assert _spine_geometry(preview) == _spine_geometry(_spine_rows(specimen, 'ud-b1')[0])
    assert 'Protect gains' in preview and '保护收益' in preview


def test_spine_comparison_preview_mode_follows_available_width(specimen):
    # The class is a safe stacked no-JS fallback, not a permanent desktop mode.
    scripts = "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", specimen, re.S))
    assert "stage.classList.toggle('mockup-spine-390', stage.getBoundingClientRect().width <= 640)" in scripts
    assert 'referenceObserver.observe(stage)' in scripts
    assert 'referenceObserver.observe(bar)' in scripts


def test_spine_comparison_missing_stance_keeps_its_desktop_column(specimen):
    compact = re.sub(r'\s+', '', specimen)
    assert '.wrap:not(.mockup-spine-390)#spec-spine-comparison[data-spec="ud-b1"].mx-spine-row[data-null="1"]>.mx-spine-stance{grid-column:4;}' in compact
    for group in ['ud-b1', 'ud-b1-390']:
        row = _spine_rows(specimen, group)[-1]
        assert 'No score' in row and '暂无分值' in row


def test_spine_comparison_phone_preview_has_a_real_phone_bound(specimen):
    nodes = _specimen_tab_nodes(_spine_examples(specimen))
    frame = next(a for _,a in nodes if {'mobile-sim','mockup-spine-390'} <= set(a.get('class','').split()))
    style = re.sub(r'\s+', '', frame.get('style',''))
    assert 'max-width:390px' in style and 'box-sizing:border-box' in style


def test_spine_comparison_value_headers_carry_machine_readable_dates(specimen):
    table = _spine_examples(specimen).split('id="spec-spine-values"', 1)[1].split('</table>', 1)[0]
    assert '<time datetime="2026-07-12">' in table and '<time datetime="2026-08-12">' in table


# R11: historical evidence is not a next-event probability.
def _specimen_rate_evidence(specimen):
    m = re.search(r'<div class="panel" id="specimen-evidence-rate"[^>]*>(.*?)<!-- END RATE EVIDENCE -->', specimen, re.S)
    assert m, "Keep one source-owned LENS open-state example"
    return m.group(1)


def test_evidence_rate_has_visible_fictional_and_historical_boundaries(specimen):
    body = _specimen_rate_evidence(specimen)
    assert 'Fictional study' in body and '虚构研究' in body
    front = body.split('class="lens-pop-demo"')[0]
    assert 'Small historical sample—not a forecast.' in front
    assert '少量历史样本，不是预测。' in front
    assert '约六成会消退' not in body


def test_evidence_rate_counts_reconcile_and_support_the_rounded_phrase(specimen):
    body = _specimen_rate_evidence(specimen)
    values = {k:int(v) for k,v in re.findall(r'data-spec-(total|faded|other)="(\d+)"', body)}
    assert values == {'total':26, 'faded':16, 'other':10}
    assert values['faded'] + values['other'] == values['total']
    assert round(values['faded'] / values['total'] * 10) == 6
    assert '16 of 26' in body and 'other 10' in body
    assert 'within a day' in body and '2021–2026' in body


def test_evidence_rate_static_trigger_does_not_pretend_runtime_works(specimen):
    body = _specimen_rate_evidence(specimen)
    nodes = _specimen_tab_nodes(body)
    trigger = next(a for tag,a in nodes if a.get('id') == 'spec-lens-trigger')
    assert trigger.get('type') == 'button' and 'disabled' in trigger
    assert trigger.get('aria-describedby') == 'spec-lens-limit'
    assert 'open-state example' in body and 'static' in body
    assert not re.search(r'<script\b|onclick=|onfocus=', body)


def test_evidence_rate_keeps_the_existing_lens_binding_and_legible_receipt(specimen):
    body = _specimen_rate_evidence(specimen)
    assert 'data-tip-en=' in body and 'data-tip-zh=' in body
    assert 'data-tip-rc-en=' in body and 'data-tip-rc-zh=' in body
    assert body.count('class="lens-pop-demo"') == 1
    assert 'not the next signal' in body and '不是下一次' in body
    css = re.sub(r'\s+', '', _rule_body(specimen, r'#specimen-evidence-rate \.lens-pop-demo'))
    assert 'position:static' in css and 'width:auto' in css
    rc = re.sub(r'\s+', '', _rule_body(specimen, r'#specimen-evidence-rate \.rc'))
    assert 'font-size:var(--fs-sm)' in rc


# R12: simplicity means the product assembles the first answer for the user.
def test_design_system_names_user_assembly_debt_as_a_first_read_defect():
    master = (ROOT / "research" / "MASTER_PRODUCT_DESIGN_SYSTEM_V1.md").read_text(encoding="utf-8")
    assert "user assembly debt" in master.lower()
    assert "target is zero" in master.lower()
    assert "configure" in master.lower() and "compute" in master.lower()


def test_migration_packet_requires_user_assembly_debt_accounting():
    factory = (ROOT / "research" / "DESIGN_MIGRATION_FACTORY_V1.md").read_text(encoding="utf-8")
    assert "ASSEMBLY DEBT:" in factory
    assert "target 0" in factory
    assert "before the useful first read" in factory


def test_agent_guidance_projects_the_same_prepared_answer_rule():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "user assembly debt" in agents.lower()
    assert "prepared answer" in agents.lower()
    assert "target zero" in agents.lower()