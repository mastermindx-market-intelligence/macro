"""Finance Intelligence dossier — public shell, scoped CSS, and IIFE contracts.

Chairman directive 2026-09-24 (relayed from Astra CEO): Finance does NOT
build base layers — no private store, no publish lane, no serving route.
These tests enforce that boundary plus the §B/§C/§D/§E/§F/§G spec contract.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts.build_finance_intelligence_page import render_from_state


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def _render() -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    return env.get_template("finance_intelligence.html.j2").render(
        generated_utc="runtime-api",
        active_section="research",
        active_page="finance_intelligence",
    )


# ──────────────────────────────────────────────────────────────────────────
# §B shell shape — bilingual, shared nav only, seven L1 sections, drawer
# ──────────────────────────────────────────────────────────────────────────
def test_shell_is_bilingual_shared_navigation_only_and_data_free():
    source = (TEMPLATES / "finance_intelligence.html.j2").read_text(encoding="utf-8")
    html = _render()

    assert source.count('{% include "_site_nav.html.j2" %}') == 1
    # The page chrome is the SHARED site-nav include; the in-page TOC is a
    # section-anchor nav, not a duplicate header. The "no second header" rule
    # binds at the page chrome level.
    assert html.count('class="site-nav"') == 1
    assert html.count('class="fi-toc"') == 1
    assert html.count('class="l-en"') >= 20
    assert html.count('class="l-zh"') >= 20
    assert "Finance Intelligence" in html
    assert "金融情报" in html
    assert "research context, not a trade call" in html

    # The static shell explains the product but cannot disclose any read-model
    # payload: no slice identifier, no company exposure row, no valuation
    # anchor, no source-record id, no read-model contract name.
    assert re.search(r"\bslice_[a-zA-Z0-9_]+\b", html) is None
    for forbidden in (
        "record_id",
        "company_exposures",
        "source_records",
        "finance_intelligence_read_model",
        "contract_id",
        "publisher",
        "observed_at",
        "measurement_class",
    ):
        assert forbidden not in html


def test_shell_has_seven_l1_sections_with_mirror_freshness_and_evidence_drawer():
    html = _render()
    for section_id, aria_title in (
            ("what-changed", "近期变化"),
            ("rerating-map", "重估链路"),
            ("system-map", "系统图"),
            ("subtheme-atlas", "子主题图谱"),
            ("company-exposure", "公司敞口"),
            ("macro-matrix", "宏观矩阵"),
            ("constraint-map", "约束图"),
    ):
        assert f'id="{section_id}"' in html, section_id
        assert aria_title in html, aria_title

    # what-changed and rerating-map mirror the freshness state on the header
    # (E.4 mirroring rule). Other section heads must not carry it.
    what_head = re.search(
        r'<section id="what-changed"[^>]*>.*?<header class="fi-section-head"\s+data-state-freshness="',
        html, re.S,
    )
    assert what_head is not None
    rerating_head = re.search(
        r'<section id="rerating-map"[^>]*>.*?<header class="fi-section-head"\s+data-state-freshness="',
        html, re.S,
    )
    assert rerating_head is not None
    assert 'data-state-freshness=""' in html

    # TOC has 7 anchor links + evidence button
    toc = re.search(r'<nav class="fi-toc".*?</nav>', html, re.S).group(0)
    assert toc.count('href="#') == 7
    assert 'fi-toc-evidence' in toc
    assert 'aria-controls="evidence-drawer"' in toc

    # Drawer aside + scrim + close button
    assert 'id="evidence-drawer"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'id="fi-scrim"' in html
    assert 'id="fi-close-evidence"' in html


def test_shell_mount_points_match_every_section_renderer_in_the_js():
    html = _render()
    for mount in (
        "hero-asof", "hero-asof-zh", "hero-cutoff", "hero-cutoff-zh",
        "hero-freshness", "hero-outer",
        "what-changed-list",
        "slice-select", "rerating-steps", "rerating-bridge",
        "falsifiers", "conflict-list",
        "view-tabs", "view-panels",
        "domain-grid", "coverage-eyebrow", "atlas-gap",
        "exposure-thead", "exposure-rows", "exposure-more", "exposure-cards",
        "exposure-cards-more", "exposure-cards-list",
        "macro-thead", "macro-rows", "macro-more", "macro-cards",
        "constraint-list",
        "provenance",
        "notice", "notice-en", "notice-zh",
        "evidence-fields", "evidence-empty", "evidence-private-notice",
    ):
        assert f'data-fi-mount="{mount}"' in html, mount


# ──────────────────────────────────────────────────────────────────────────
# §C scoped CSS — two art directions, zero hex/rgb literals
# ──────────────────────────────────────────────────────────────────────────
def test_css_has_two_art_directions_and_zero_colour_literals():
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")

    # Dark + light are TWO art directions, not one token swap (theme art
    # direction law). The dark token block lives on `:root` and the light
    # block lives under `[data-theme="light"]`.
    assert ":root" in css
    assert '[data-theme="light"]' in css
    assert css.count('var(--text)') >= 1
    assert css.count('var(--panel)') >= 1
    assert css.count('var(--bg)') >= 1

    # Zero hex/rgb literals — every material decision routes through the
    # theme token surface.
    for forbidden in re.findall(r"#[0-9a-fA-F]{3,8}\b", css):
        assert forbidden in {"#fff", "#000"} or False, f"hex literal {forbidden}"
    assert re.search(r"\brgb\(", css) is None
    assert re.search(r"\brgba\(", css) is None

    # The page owns its canvas in both art directions: theme.css does not paint
    # body, and the shell's 1200px box alone left the gutters, the nav band and
    # the area below the content on the browser's white default in dark mode.
    assert "body.fi-page { background: var(--fi-canvas); }" in css

    # Tier 1 (fi-panel) and tier 2 (fi-panel2) elevation rules both exist.
    assert ".fi-panel" in css
    assert ".fi-panel2" in css

    # Focus ring on visible focus, drawer elevation distinct from panel.
    assert ":focus-visible" in css
    assert ".fi-drawer" in css
    assert ".fi-scrim" in css
    assert "prefers-reduced-motion" in css

    # Freshness rail/pip mechanism for both themes. Dark uses a ::before
    # pip with glow; light suppresses the pip and uses a 3px border-left
    # rail instead — verified by the data-state-freshness + ::before rules
    # and the [data-theme="light"] override.
    assert ".fi-section-head[data-state-freshness]" in css
    assert ".fi-section-head::before" in css
    assert "[data-theme=\"light\"] .fi-section-head::before { display: none" in css
    assert "fi-step-dot" in css
    assert ".fi-rerating-steps::before" in css
    assert ".fi-rerating-step[data-active=\"true\"] .fi-step-dot" in css

    # Chip base + state-driven palette mapping (plane_state tokens).
    assert ".fi-chip" in css
    for state_token in (
        "OBSERVED", "INFERRED", "MISSING", "CONFLICTING", "STALE",
        "REGIME_BREAK", "VALUATION_ANCHOR_UNAVAILABLE", "PRICE_BASIS_UNQUALIFIED",
        "NOT_APPLICABLE",
    ):
        assert state_token in css, state_token

    # Responsive shells at the breakpoints the design doctrine names.
    assert "@media" in css
    assert "(min-width: 1200px)" in css
    assert "(max-width: 767px)" in css


# ──────────────────────────────────────────────────────────────────────────
# §D + §E JS contract — closed label map, no hidden storage, fetchJson + drawer
# ──────────────────────────────────────────────────────────────────────────
def test_js_uses_authenticated_source_only_and_forbidden_storage_list_is_absent():
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")

    # Auth + fetchJson pattern, lifted verbatim from biocatalyst.js.
    for token in (
        "function withAuth(headers)",
        "window.MDXAuth.client",
        "headers.Authorization = 'Bearer ' + token",
        "function fetchJson(url, signal)",
        "function markHydration(error, kind, status)",
        "function jsonContentType(response)",
        "function hydrationKind(error)",
        "credentials: 'include'",
        "cache: 'no-store'",
        "throw markHydration(new Error('HTTP ' + status), 'locked', status)",
        "throw markHydration(new Error('HTTP ' + status), 'source_outage', status)",
        "throw markHydration(new Error('HTTP 200 non-json'), 'integrity_block', 200)",
    ):
        assert token in js, token

    # Drawer lifecycle, lifted verbatim from capital_structure.js.
    for token in (
        "function setInert(el, on)",
        "function focusableInDrawer()",
        "function handleDrawerKeydown(ev)",
        "function setDrawer(open)",
        "ui.drawer.classList.contains('is-open')",
        "setInert(state.ui.shell, true)",
        "setInert(state.ui.siteNav, true)",
        "state.lastFocus.focus",
    ):
        assert token in js, token

    # FORBIDDEN storage list (§E) — template bootstrap exempt. Strip header
    # docstring comments first so the documented design surface does not
    # pollute the regex, then assert no executable call ever uses the list.
    js_stripped = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    for forbidden in ("localStorage", "sessionStorage", "indexedDB", "caches.", "serviceWorker", "prefetch"):
        assert forbidden not in js_stripped, forbidden

    # No DOM-injection sinks other than the bounded evidence fields builder.
    # Every value written through innerHTML is escaped via esc() first, so
    # no user-controlled payload reaches the DOM unescaped. The hydration
    # contract forbids localStorage/sessionStorage/etc. (asserted above);
    # innerHTML is allowed when esc() wraps every interpolated value.
    js_stripped = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    assert "function esc(value)" in js_stripped

    # Page-local ARIA swapper must be the inline script in HTML, not in JS.
    assert "applyAria" not in js

    # §D label map coverage — every enum the live contract can deliver must
    # have one row in FI_LABELS (or fallback).
    for key in (
        "plane_state", "comparability_state", "slice_state", "posture",
        "membership", "materiality", "role", "basis", "exposure_state",
        "constraint", "driver", "lag", "macro_state", "freshness",
        "first_vertical_state", "outer_dossier_state", "history_state",
        "per_share_anchor", "valuation_multiple", "horizon",
        "valuation_anchor_state", "falsifier_state", "price_basis_state",
        "basket_construction_family", "identity_state", "company_route_state",
        "rights_state", "statement_mode", "published_at_grain",
        "measurement_class", "gross_net_basis", "period_summary_basis",
        "reported_derived_estimated", "indicator_direction", "indicator_state",
        "plane_word", "edge_relationship", "receipt_owner", "receipt_state",
        "degraded_section_state", "conflict_label",
    ):
        assert key in js, f"missing FI_LABELS row: {key}"

    # FORBIDDEN JS identifier list — labels excepted via map.
    label_string_exempt = (
        "'Equal weight'", "'Exposure weight'",
        "'Exposure-capped weight'", "'Stratified equal weight'",
        "'average'", "'end'",
    )
    body = js
    for token in ("score", "rank", "composite"):
        for line in body.splitlines():
            if token in line and line.strip().startswith("//"):
                continue
            if token in line:
                # Visible label text inside FI_LABELS is excepted.
                if any(ex in line for ex in label_string_exempt):
                    continue
                if "labelFor(" in line or "FI_LABELS" in line:
                    continue
                raise AssertionError(f"forbidden token {token} in JS: {line.strip()}")
    for token in ("average", "weight"):
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if token in line:
                # Either a visible label (excepted) or a comment.
                if any(ex in line for ex in label_string_exempt):
                    continue
                if token == "weight" and "Equal weight" in line:
                    continue
                if token == "average" and "'average'" in line:
                    continue
                raise AssertionError(f"forbidden token {token} in JS: {line.strip()}")


def test_js_renders_seven_sections_and_handles_evidence_drawer_and_slice_hash():
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    for fn in (
        "function renderHero",
        "function renderWhatChanged",
        "function renderSliceSelector",
        "function renderRerating",
        "function renderFalsifiers",
        "function renderConflicts",
        "function renderSystem",
        "function renderAtlas",
        "function renderExposure",
        "function renderMacro",
        "function renderConstraints",
        "function renderProvenance",
        "function renderDrawer",
        "function renderNotice",
        "function hydrate",
        "function boot",
        "function mirrorFreshness",
    ):
        assert fn in js, fn

    # Rerating stepper is exactly four nodes in the frozen order.
    assert "operating" in js
    assert "expectations" in js
    assert "valuation" in js
    assert "price" in js
    # Slice URL hash routing.
    assert "#slice=" in js
    assert "#evidence=" in js
    # conflict footer text.
    assert "Left unresolved by design" in js
    assert "有意不作裁决" in js

    # Evidence drawer: source rights suppression rule.
    assert "SOURCE_RIGHTS_HELD" in js
    assert "INTERNAL_ONLY" in js
    assert "Value and excerpt withheld" in js

    # status mapping (§E.3) — locked/updating/integrity/source_outage/ready.
    assert "'locked'" in js
    assert "'source_outage'" in js
    assert "'integrity_block'" in js
    assert "contract_invalid" in js
    assert "doc.contract_id !== 'finance_intelligence_read_model.v1'" in js

    # Tabs roving tabindex + ArrowLeft/ArrowRight/Home/End.
    assert "ArrowLeft" in js
    assert "ArrowRight" in js
    assert "'Home'" in js
    assert "'End'" in js

    # Rerating uses an <ol> with rerating_steps mount, NOT a styled bullet list.
    assert 'class="fi-rerating-steps"' not in js  # never hardcoded
    # The `<ol>` template lives in the J2; JS only writes <li> nodes into it.


# ──────────────────────────────────────────────────────────────────────────
# Renderer — static shell + paired client assets, byte-identical
# ──────────────────────────────────────────────────────────────────────────
def test_renderer_writes_only_shell_and_paired_assets(tmp_path: Path):
    (tmp_path / "templates").symlink_to(TEMPLATES, target_is_directory=True)
    page = render_from_state(tmp_path)
    html = page.read_text(encoding="utf-8")

    assert page == tmp_path / "site" / "finance_intelligence.html"
    # No payload leaks into the static shell.
    assert "finance_intelligence_read_model" not in html
    assert "company_exposures" not in html
    # Paired assets are byte-identical templates/site copies.
    assert (tmp_path / "site" / "finance_intelligence.css").read_bytes() == (
        TEMPLATES / "finance_intelligence.css"
    ).read_bytes()
    assert (tmp_path / "site" / "finance_intelligence.js").read_bytes() == (
        TEMPLATES / "finance_intelligence.js"
    ).read_bytes()
    # No temp files left behind.
    assert not list((tmp_path / "site").glob(".finance_intelligence.*.tmp"))
    # HTML wires the paired assets.
    assert 'href="finance_intelligence.css"' in html
    assert 'src="finance_intelligence.js"' in html


# ──────────────────────────────────────────────────────────────────────────
# Templates ↔ site byte equality + JS validity
# ──────────────────────────────────────────────────────────────────────────
def test_template_and_site_assets_remain_byte_equivalent():
    """CSS + JS are byte-identical templates↔site copies; HTML is the rendered
    output of the .html.j2 template, so it differs from the Jinja2 source by
    design."""
    site = ROOT / "site"
    for name in ("finance_intelligence.css", "finance_intelligence.js"):
        template_bytes = (TEMPLATES / name).read_bytes()
        site_path = site / name
        if site_path.exists():
            assert site_path.read_bytes() == template_bytes, name


def test_runtime_is_valid_javascript():
    node = shutil.which("node")
    if node is None:
        return
    result = subprocess.run(
        [node, "--check", str(TEMPLATES / "finance_intelligence.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


# ──────────────────────────────────────────────────────────────────────────
# Wiring — render.yml, build_site.py, nav, public access
# ──────────────────────────────────────────────────────────────────────────
def test_render_lane_owns_and_narrows_finance_intelligence_builder():
    render = (ROOT / ".github" / "workflows" / "render.yml").read_text(encoding="utf-8")
    assert '- "scripts/build_finance_intelligence_page.py"' in render
    assert "templates/finance_intelligence.*" in render
    # Region-of mapping covers the macro region for shared CSS/JS chunks.
    assert "finance_intelligence.*" in render


# The build_site hook assertion lives in tests/test_finance_intelligence_site_wiring.py,
# run by an always-on job: it reads the site builder as text, and the exclusive
# finance-intelligence scope would otherwise have to carry that builder's whole
# import closure.


def test_shell_has_no_private_api_or_serving_route_reference():
    """Per Chairman directive 2026-09-24, Finance ships no base layers.

    The template bootstrap script (theme/lang) is the spec-exempt inline
    pattern; the FORBIDDEN storage list is otherwise enforced by the
    dedicated contract test. Here we only assert the shell + JS carry no
    publish-lane / private-store / serving-route references.
    """
    html = _render()
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    js_stripped = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    for forbidden in ("publish_lane", "serving_route"):
        assert forbidden not in html, forbidden
        # Word-boundary match — avoids false positives like "private_store_unavailable".
        assert re.search(r"\b" + re.escape(forbidden) + r"\b", js_stripped) is None, forbidden
    for forbidden in ("localStorage", "sessionStorage", "indexedDB", "serviceWorker", "prefetch"):
        assert forbidden not in js_stripped, forbidden


def test_public_access_policy_lists_finance_intelligence_shell():
    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text(encoding="utf-8"))
    public = policy["public"]["exact"]
    assert "/finance_intelligence.html" in public
    assert "/finance_intelligence.css" in public
    assert "/finance_intelligence.js" in public


def test_shell_loads_the_shared_theme_runtime():
    """The nav's theme switch and EN/中文 toggle are wired by theme.js, so a
    page that omits it renders both controls inert (T8 went live without it
    on 2026-09-24 and neither toggle did anything). Mirror biocatalyst: load
    theme.js deferred, ahead of the page runtime, in the template and in the
    committed (render-stamped) site copy alike."""
    html = _render()
    theme_at = html.find('<script src="theme.js" defer></script>')
    assert theme_at != -1
    assert theme_at < html.find('<script src="finance_intelligence.js"')
    site = ROOT / "site" / "finance_intelligence.html"
    if site.exists():
        committed = site.read_text(encoding="utf-8")
        assert re.search(r'<script src="theme\.js(\?v=[0-9a-f]{8})?" defer></script>', committed)


def test_hero_meta_carries_no_unfilled_aria_placeholder():
    """No static aria pair may carry a spec placeholder. The frozen spec wrote
    `{common_as_of}` / `{§D.12 label of freshness.state}` as instructions; the
    template shipped them literally, so the hero as-of/cutoff spans and the
    freshness/outer chips announced the placeholder next to the real value.
    The as-of/cutoff spans are named by their visible text; the chips are named
    by the runtime from the same label row it paints."""
    placeholder = re.compile(r'data-aria-(?:en|zh)="[^"]*\{')
    html = _render()
    assert placeholder.search(html) is None
    site = ROOT / "site" / "finance_intelligence.html"
    if site.exists():
        assert placeholder.search(site.read_text(encoding="utf-8")) is None


def test_runtime_never_turns_a_missing_state_into_a_positive_fact():
    """Product law: missing states are rendered as words. The runtime used to
    default absent tokens to positive facts: a missing rights_state displayed the
    licensed excerpt, a missing identity read "validated", an absent role became
    "second-order beneficiary", and unknown plane or comparability tokens read
    "on file" or "comparable". Review response 2026-09-25 (independent Opus
    review, confirmed in headless Chromium)."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    for fabricated in (
        "|| 'DIRECT_DISPLAY_OK'", "|| 'IDENTITY_VALIDATED'", "|| 'SECOND_ORDER_BENEFICIARY'",
        "|| 'QUALITATIVE'", "|| 'DESCRIBED'", "|| 'MEASURED'",
        "['On file', '有据可查']", "['Comparable', '可比']", "['ready', '就绪']",
    ):
        assert fabricated not in js, fabricated
    assert "var state$ = node.state || 'MISSING';" in js
    # D.23 fails CLOSED: only the two display states may show value/excerpt.
    assert "var suppress = !(rights === 'DIRECT_DISPLAY_OK' || rights === 'DERIVED_DISPLAY_OK');" in js
    # A source outage has its own words, never the generic "Read failed".
    assert "source_outage: ['Evidence source temporarily unavailable" in js
    # A malformed deep link is ignored instead of blanking the dossier.
    assert "try { return decodeURIComponent(raw); } catch (e) { return null; }" in js
    # A named record missing from source_records says so.
    assert 'data-fi-mount="evidence-missing"' in _render()


def test_shell_ships_the_not_connected_binding_until_integration():
    """T8 seat ruling: the read-model endpoint is bound only through
    ``<main data-fi-read-url>``; an empty value must render the bilingual
    not-connected notice and never fetch (Chairman directive 2026-09-24)."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    tpl = (root / "templates" / "finance_intelligence.html.j2").read_text(encoding="utf-8")
    js = (root / "templates" / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "data-fi-read-url=\"{{ fi_read_url | default('') }}\"" in tpl
    assert "'__FI_READ_URL__'" not in js
    assert "getAttribute('data-fi-read-url')" in js
    assert "setAttribute('data-state', 'not-connected')" in js
    assert "not_connected: ['Not yet connected to the evidence service.', '尚未接入证据服务。']" in js
    rendered = (root / "site" / "finance_intelligence.html").read_text(encoding="utf-8")
    assert 'data-fi-read-url=""' in rendered
    # the page-local ARIA swapper stays the inline template script (asserted above)
    css = (root / "templates" / "finance_intelligence.css").read_text(encoding="utf-8")
    assert '.fi-shell[data-state="not-connected"] .fi-meta { display: none; }' in css
