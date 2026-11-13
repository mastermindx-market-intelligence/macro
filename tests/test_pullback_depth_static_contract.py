"""Static CSS/JS/HTML contract for the pullback fragment's own three sources.

The fragment ships as a matched triple — ``_risk_radar_pullback_depth
{.html,.css,.js}.j2`` — and this file pins the triple to itself at the source
level, one rule per test:

1. every class the expiry script adds/removes/toggles/queries gets a CSS
   answer in the fragment stylesheet;
2. every class the stylesheet styles is emitted by the template or added by
   the script (no dead CSS);
3. every selector stays inside the fragment's ``.rrp`` scope and @keyframes
   names carry the ``rrp``/``pb`` prefix;
4. every declared animation/transition has a ``prefers-reduced-motion:
   reduce`` override that disables it;
5. every ``data-*`` attribute the script reads is emitted by the template;
6. the phone (max-width:480px) block lowers the study and chart-card gutters
   so the chart clears 0.88 of the popup width at 390px, never fixes the svg's
   height, and adds neither ``!important`` nor an ``overflow:hidden``.

Parsing is regexes over the template SOURCE: Jinja spans and comments are
stripped first, so the contract holds for every render, not one. A class the
script queries but the stylesheet never names can still be answered when the
fragment emits it on an element that carries another styled class — a script
hook riding a styled element.

Cross-boundary classes are named exceptions, each self-verifying: when the
boundary moves, the stale entry fails its test, so a list entry survives only
by staying true.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
# Scratch runs of this test repoint TEMPLATE_DIR at a mutated template copy.
TEMPLATE_DIR = ROOT / "templates"
HTML_NAME = "_risk_radar_pullback_depth.html.j2"
CSS_NAME = "_risk_radar_pullback_depth.css.j2"
JS_NAME = "_risk_radar_pullback_depth.js.j2"

# Bilingual spans the fragment's t() macro emits and the site's global
# stylesheets own (theme.css, ontology.css, market_memory.css). The expiry
# script swaps their text only — the fragment stylesheet needs no rule.
JS_GLOBAL_HOOK_CLASSES = frozenset({"l-en", "l-zh"})

# The shared inline-chart SVG that {{ v.detail_chart_html|safe }} embeds;
# templates/illus.css styles the family. The fragment neutralises its scroll
# choreography so critical ink never waits for JS — those rules are live.
CHART_PAYLOAD_CLASSES = frozenset({
    "ilx", "ilx-path", "ilx-water", "ilx-ref", "ilx-tag", "ilx-d", "ilx-reflab", "ilx-dot",
    # kind="drawdown" also emits these; the forced-colours block restyles them.
    "ilx-area", "ilx-down", "ilx-dot-down", "ilx-water-top",
})
CHART_STYLESHEET = "illus.css"

# The one original US modal (dashboard.html.j2) and the shared country dialog
# (_risk_radar_dlg.html.j2) render the legacy-details disclosure; this
# fragment's stylesheet owns its look, scoped to the fragment root's following
# sibling so the class stays inside the fragment's .rrp scope.
HOST_MODAL_CLASSES = frozenset({"riskdlg-legacy-details"})
HOST_DETAIL_EMITTERS = ("dashboard.html.j2", "_risk_radar_dlg.html.j2")

SCOPED_SELECTOR_EXCEPTIONS: tuple[str, ...] = ()

# The phone fix, measured at 390px in headless Chromium over synthetic pages:
# the collapsed study's 16px gutters, the chart card's 20px gutters and its 1px
# borders eat ~74px of the popup, so the chart svg spanned only 0.76 of the
# .rrp content width (238/312 cn, 248/322 us). The max-width:480px block lowers
# both gutters to <=8px per side, which puts the svg at ~0.89 (278/312,
# 288/322) without touching the svg's viewBox aspect ratio.
NARROW_MEDIA = re.compile(r"^@media\s*\(\s*max-width\s*:\s*480px\s*\)$")
STUDY_SELECTOR = re.compile(r"^\.rrp \.rrp-study$")
CHART_CARD_SELECTOR = re.compile(r"^\.rrp \.rrp-study>div$")
CHART_SIZING_SELECTOR = re.compile(r"\.rrp-chart\b|\.ilx\b")
PHONE_GUTTER_PX = 8.0

_JINJA_SPANS = tuple(re.compile(p, re.S) for p in (r"\{#.*?#\}", r"\{%.*?%\}", r"\{\{.*?\}\}"))
_BLOCK_COMMENTS = re.compile(r"/\*.*?\*/", re.S)
_CLASS_TOKEN = re.compile(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)")
_QUERY_ARGS = re.compile(
    r"(?:querySelectorAll|querySelector|closest|matches)\(\s*'([^']*)'")
_CLASSLIST_ARGS = re.compile(r"classList\.(add|remove|toggle|contains)\(([^)]*)\)")
_QUOTED = re.compile(r"'([^']*)'")
_CLASS_ATTRS = re.compile(r'class="([^"]*)"')
_DATA_ATTRS = re.compile(r"\b(data-[a-z][a-z0-9-]*)\s*=")
_KEYFRAMES_NAME = re.compile(r"^@(?:-webkit-)?keyframes\s+([\w-]+)$")
_SCOPED_SELECTORS = (
    re.compile(r"^\.rrp\b"),
    re.compile(r'^html\[data-theme\s*=\s*["\']?[\w-]+["\']?\]\s*\.rrp\b'),
)
_DISABLED_VALUE = re.compile(r"^none\b")


def _source(name):
    return (TEMPLATE_DIR / name).read_text()


def _strip_jinja_and_comments(text, block_comments=False):
    for pattern in _JINJA_SPANS:
        text = pattern.sub(" ", text)
    if block_comments:
        text = _BLOCK_COMMENTS.sub(" ", text)
    return text


def _html_source():
    return _strip_jinja_and_comments(_source(HTML_NAME))


def _css_source():
    return _strip_jinja_and_comments(_source(CSS_NAME), block_comments=True)


def _js_source():
    return _strip_jinja_and_comments(_source(JS_NAME), block_comments=True)


def _css_rules(css):
    """Every rule as (preludes, head, body); preludes are enclosing @media /
    @supports heads, outermost first. A brace counter is enough for this
    hand-written stylesheet: no string or comment (already stripped) holds a
    brace, and rules nest only inside those at-rule blocks."""
    rules = []
    i, n = 0, len(css)
    while i < n:
        brace = css.find("{", i)
        if brace < 0:
            break
        head = css[i:brace].strip()
        depth, end = 1, brace + 1
        while end < n and depth:
            depth += (css[end] == "{") - (css[end] == "}")
            end += 1
        body = css[brace + 1:end - 1 if depth == 0 else end]
        if head.startswith(("@media", "@supports")):
            rules.extend(((head, *preludes), sel, b)
                         for preludes, sel, b in _css_rules(body))
        else:
            rules.append(((), head, body))
        i = end
    return rules


def _declarations(body):
    out = []
    for chunk in body.split(";"):
        prop, sep, value = chunk.partition(":")
        if sep:
            out.append((prop.strip().lower(), value.strip()))
    return out


def _norm_selector(selector):
    """Collapse the whitespace a hand-written selector may or may not carry."""
    text = re.sub(r"\s*([>~+])\s*", r"\1", selector.strip())
    return re.sub(r"\s+", " ", text)


def _px(value):
    """One padding component in px, ``var()`` fallbacks resolved.

    Fails closed: a gutter this helper cannot resolve to px (a bare ``var()``,
    a ``%``, an ``em``) is a failure, never an unverifiable pass."""
    text = value.strip()
    fallback = re.fullmatch(r"var\(--[\w-]+,\s*(.+)\)", text)
    if fallback:
        text = fallback.group(1).strip()
    match = re.fullmatch(r"([0-9.]+)px", text)
    assert match, f"cannot resolve a padding component to px: {value!r}"
    return float(match.group(1))


def _horizontal_padding(body):
    """(left, right) px that the declarations in one rule body set."""
    left = right = None
    for prop, value in _declarations(body):
        if prop == "padding":
            sides = [_px(side) for side in value.split()]
            if len(sides) == 1:
                left = right = sides[0]
            elif len(sides) == 4:
                left, right = sides[3], sides[1]
            else:
                # 2 values: vertical | horizontal; 3: top | horizontal | bottom.
                assert len(sides) in (2, 3), (
                    f"padding shorthand with {len(sides)} values: {value!r}")
                left = right = sides[1]
        elif prop == "padding-left":
            left = _px(value)
        elif prop == "padding-right":
            right = _px(value)
    return left, right


def _narrow_rules():
    """Every rule inside the phone (max-width:480px) block, as (head, body)."""
    return [(head, body) for preludes, head, body in _css_rules(_css_source())
            if any(NARROW_MEDIA.match(prelude) for prelude in preludes)]


def _css_classes():
    return {cls for _, head, _ in _css_rules(_css_source())
            if not head.startswith("@")
            for cls in _CLASS_TOKEN.findall(head)}


def _html_class_lists():
    return [frozenset(attrs.split()) for attrs in _CLASS_ATTRS.findall(_html_source())]


def _js_class_refs():
    """Every class the script adds or queries, mapped to one readable site."""
    js = _js_source()
    refs = {}
    for m in _CLASSLIST_ARGS.finditer(js):
        for name in _QUOTED.findall(m.group(2)):
            refs.setdefault(name, f"classList.{m.group(1)}('{name}')")
    for m in _QUERY_ARGS.finditer(js):
        for name in _CLASS_TOKEN.findall(m.group(1)):
            refs.setdefault(name, f"selector '{m.group(1).strip()}'")
    return refs


def _inert_template_classes():
    """Classes carried only by <template> elements: inert content never renders, so
    a script that queries it to clone the content owes the stylesheet nothing."""
    html = _html_source()
    inert = {c for attrs in re.findall(r'<template\b[^>]*\bclass="([^"]*)"', html)
             for c in attrs.split()}
    rendered = {c for attrs in re.findall(r'<(?!template\b)[a-z][a-z0-9]*\b[^>]*\bclass="([^"]*)"', html)
                for c in attrs.split()}
    return inert - rendered


def _js_owned_data_attributes():
    """data-* attributes the script itself writes; reading back its own state needs
    no template emission."""
    return set(re.findall(r"setAttribute\(\s*'(data-[a-z][a-z0-9-]*)'", _js_source()))


def _js_scripted_classes():
    js = _js_source()
    return {name for m in _CLASSLIST_ARGS.finditer(js)
            if m.group(1) in ("add", "remove", "toggle")
            for name in _QUOTED.findall(m.group(2))}


def _js_data_reads():
    """Every data-* attribute the script reads, mapped to one readable site."""
    js = _js_source()
    reads = {}
    for m in re.finditer(r"getAttribute\(\s*'([^']*)'\s*\)", js):
        reads.setdefault(m.group(1), f"getAttribute('{m.group(1)}')")
    for m in re.finditer(r"dataset\.([A-Za-z][A-Za-z0-9_]*)", js):
        attr = "data-" + re.sub(r"(?<!^)(?=[A-Z])", "-", m.group(1)).lower()
        reads.setdefault(attr, f"dataset.{m.group(1)}")
    for m in _QUERY_ARGS.finditer(js):
        for attr in re.findall(r"\[([A-Za-z][A-Za-z0-9_-]*)", m.group(1)):
            if attr.startswith("data-"):
                reads.setdefault(attr, f"selector '{m.group(1).strip()}'")
    return reads


def test_every_class_the_script_touches_gets_a_css_answer():
    css_classes = _css_classes()
    html_lists = _html_class_lists()
    orphaned = []
    for cls, site in sorted(_js_class_refs().items()):
        if cls in css_classes:
            continue
        # A script hook riding a styled element is answered: the fragment
        # emits the class on an element that also carries a styled class.
        if any(cls in tokens and (tokens - {cls}) & css_classes for tokens in html_lists):
            continue
        if cls in JS_GLOBAL_HOOK_CLASSES:
            continue
        if cls in _inert_template_classes():
            continue
        orphaned.append(f"{cls!r} via {site}")
    assert not orphaned, (
        "the script adds or queries classes no fragment stylesheet rule answers: "
        + ", ".join(orphaned))
    stale = sorted(
        cls for cls in JS_GLOBAL_HOOK_CLASSES
        if cls in css_classes
        or cls not in _js_class_refs()
        or not any(cls in tokens for tokens in html_lists))
    assert not stale, f"JS_GLOBAL_HOOK_CLASSES entries are stale, remove them: {stale}"


def test_every_class_the_css_styles_is_live_in_the_fragment():
    styled = _css_classes()
    emitted = set().union(*_html_class_lists())
    dead = styled - emitted - _js_scripted_classes()
    unexplained = sorted(dead - CHART_PAYLOAD_CLASSES - HOST_MODAL_CLASSES)
    assert not unexplained, (
        "the stylesheet styles classes the fragment neither emits nor scripts: "
        + ", ".join(unexplained))
    unused = sorted(cls for cls in CHART_PAYLOAD_CLASSES | HOST_MODAL_CLASSES
                    if cls not in styled)
    assert not unused, f"exception entries the stylesheet no longer styles: {unused}"
    assert "detail_chart_html" in _source(HTML_NAME), (
        "the template no longer embeds detail_chart_html; the chart payload "
        "classes it neutralised are dead CSS and CHART_PAYLOAD_CLASSES is stale")
    unowned = sorted(cls for cls in CHART_PAYLOAD_CLASSES
                     if not re.search(rf"\.{re.escape(cls)}\b", _source(CHART_STYLESHEET)))
    assert not unowned, (
        f"classes CHART_PAYLOAD_CLASSES no longer finds in {CHART_STYLESHEET}: "
        + ", ".join(unowned))
    hosts = [name for name in HOST_DETAIL_EMITTERS
             if "riskdlg-legacy-details" in _source(name)]
    assert hosts, (
        "no host dialog emits .riskdlg-legacy-details any more; HOST_MODAL_CLASSES "
        f"and the {', '.join(HOST_DETAIL_EMITTERS)} check are stale")


def test_every_selector_stays_inside_the_fragment_scope():
    offenders = []
    for preludes, head, _ in _css_rules(_css_source()):
        keyframes = _KEYFRAMES_NAME.match(head)
        if keyframes:
            if not keyframes.group(1).startswith(("rrp", "pb")):
                offenders.append(f"@keyframes {keyframes.group(1)} (unprefixed)")
            continue
        if head.startswith("@"):  # @font-face and friends carry no selector
            continue
        for selector in (part.strip() for part in head.split(",")):
            if not selector:
                continue
            if any(pattern.match(selector) for pattern in _SCOPED_SELECTORS):
                continue
            if selector.startswith(SCOPED_SELECTOR_EXCEPTIONS):
                continue
            where = f" (inside {preludes[-1]})" if preludes else ""
            offenders.append(f"{selector}{where}")
    assert not offenders, (
        "selectors outside the fragment's .rrp scope: " + "; ".join(offenders))


def test_declared_motion_has_a_reduced_motion_off_switch():
    rules = _css_rules(_css_source())
    overrides = []  # (property family, selector classes) inside a reduce block
    for preludes, head, body in rules:
        if not any("prefers-reduced-motion" in p and "reduce" in p for p in preludes):
            continue
        for prop, value in _declarations(body):
            if prop.startswith(("animation", "transition")) and _DISABLED_VALUE.match(value):
                overrides.append((prop.split("-")[0],
                                  frozenset(_CLASS_TOKEN.findall(head))))
    declared = []
    for preludes, head, body in rules:
        if head.startswith("@"):  # @keyframes frames are not declarations
            continue
        for prop, value in _declarations(body):
            if (prop.startswith(("animation", "transition"))
                    and not _DISABLED_VALUE.match(value)):
                declared.append((head, prop, value,
                                 frozenset(_CLASS_TOKEN.findall(head))))
    uncovered = [
        f"{head} {{{prop}: {value}}}"
        for head, prop, value, classes in declared
        if not any(family == prop.split("-")[0] and classes <= covered
                   for family, covered in overrides)
    ]
    assert not uncovered, (
        "declared motion without a prefers-reduced-motion override: "
        + "; ".join(uncovered))


def test_every_data_attribute_the_script_reads_the_template_emits():
    emitted = set(_DATA_ATTRS.findall(_html_source()))
    missing = [f"{attr} (read via {site})"
               for attr, site in sorted(_js_data_reads().items())
               if attr not in emitted and attr not in _js_owned_data_attributes()]
    assert not missing, (
        "the script reads data-* attributes the template never emits: "
        + ", ".join(missing))


def test_narrow_viewport_block_exists_and_stays_in_the_fragment_scope():
    rules = _narrow_rules()
    assert rules, (
        "no @media (max-width:480px) block: the phone chart fix must live in one")
    offenders = [
        selector
        for head, _ in rules
        for selector in (part.strip() for part in head.split(","))
        if selector and not any(pattern.match(selector)
                                for pattern in _SCOPED_SELECTORS)
    ]
    assert not offenders, (
        "selectors in the narrow-viewport block outside the fragment's .rrp "
        "scope: " + "; ".join(offenders))


def _narrow_gutter(rules, selector_pattern, role):
    """The (left, right) px gutters the block's one rule for `role` declares."""
    hits = [(head, body) for head, body in rules
            if any(selector_pattern.match(_norm_selector(part))
                   for part in head.split(","))]
    assert len(hits) == 1, (
        f"expected exactly one narrow-viewport rule for {role}, found {len(hits)}")
    left, right = _horizontal_padding(hits[0][1])
    assert left is not None and right is not None, (
        f"the narrow-viewport rule for {role} sets no horizontal padding")
    assert left <= PHONE_GUTTER_PX and right <= PHONE_GUTTER_PX, (
        f"{role} keeps {left:g}px/{right:g}px gutters in the narrow block; both "
        f"must be <= {PHONE_GUTTER_PX:g}px per side (parsed values) so the chart "
        "svg reaches >= 0.88 of the .rrp content width at 390px (measured "
        "238/312 at the 16px study + 20px card gutters)")
    return left, right


def test_narrow_viewport_lowers_the_study_and_chart_card_gutters():
    study = _narrow_gutter(_narrow_rules(), STUDY_SELECTOR, ".rrp .rrp-study")
    card = _narrow_gutter(_narrow_rules(), CHART_CARD_SELECTOR,
                          ".rrp .rrp-study>div")
    # Equal gutters per rule keep the width:100% svg centred; both dialogs then
    # clear 0.88 with the borders included: 312 - 2*8 - 2*8 - 2 = 278px
    # (278/312 = 0.891) and 322 - 2*8 - 2*8 - 2 = 288px (288/322 = 0.894).
    assert study[0] == study[1] and card[0] == card[1], (
        "asymmetric gutters would off-centre the chart: "
        f"study {study}, card {card}")


def test_narrow_viewport_sets_no_fixed_height_on_the_chart():
    offenders = []
    for head, body in _narrow_rules():
        if not CHART_SIZING_SELECTOR.search(_norm_selector(head)):
            continue
        for prop, value in _declarations(body):
            if prop in ("height", "min-height", "max-height") and value != "auto":
                offenders.append(f"{head} {{{prop}: {value}}}")
    assert not offenders, (
        "the narrow-viewport block fixes the chart's height and would break its "
        "viewBox aspect ratio: " + "; ".join(offenders))


def test_narrow_viewport_adds_no_important_and_no_overflow_hidden():
    offenders = []
    for head, body in _narrow_rules():
        for prop, value in _declarations(body):
            if "!important" in value:
                offenders.append(f"{head} {{{prop}: {value}}}")
            if prop == "overflow" and "hidden" in value:
                offenders.append(f"{head} {{overflow:{value}}} clips focus rings")
    assert not offenders, (
        "the narrow-viewport block must stay a plain gutter change: "
        + "; ".join(offenders))
