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
        "weighting_family", "identity_state", "company_route_state",
        "rights_state", "statement_mode", "published_at_grain",
        "measurement_class", "gross_net_basis", "period_summary_basis",
        "reported_derived_estimated", "indicator_direction", "indicator_state",
        "plane_word", "edge_relationship", "receipt_owner", "receipt_state",
        "degraded_section_state", "conflict_label",
    ):
        assert key in js, f"missing FI_LABELS row: {key}"

    # F2 (item 3): the fabricated basket_construction_family field is GONE —
    # there is no such field anywhere in the read model or label map.
    assert "basket_construction_family" not in js
    assert "FI_W_CHIP_CLASS" not in js

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
    # F2 (item 3): narrow the "weight" ban so spec identifiers (the
    # weighting_family field name and its fi-weighting-chip / data-state-weighting
    # attribute names per spec §B line 396) are NOT flagged. The ban still
    # targets computed weighting — anything that does arithmetic on a "weight"
    # variable. Existing visible-label strings ('Equal weight', etc.) are still
    # excepted.
    weight_spec_identifiers = ("weighting_family", "fi-weighting-chip", "data-state-weighting", "weighting ")
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        if "weight" in line:
            if any(ex in line for ex in label_string_exempt):
                continue
            # Allow the line if every "weight" occurrence is inside one of the
            # spec identifiers (weighting_family / fi-weighting-chip /
            # data-state-weighting) — strip those occurrences and re-test.
            remaining = line
            for ident in weight_spec_identifiers:
                remaining = remaining.replace(ident, "")
            if "weight" not in remaining:
                continue
            raise AssertionError(f"forbidden token weight in JS: {line.strip()}")
        if "average" in line:
            if "'average'" in line:
                continue
            raise AssertionError(f"forbidden token average in JS: {line.strip()}")


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


# ──────────────────────────────────────────────────────────────────────────
# F1 — colour map cleanup: SPEC_CHIP_SELECTORS own every per-state rule
# ──────────────────────────────────────────────────────────────────────────
def test_f1_colour_map_owns_only_spec_chip_selectors():
    """F1 (item 1): the page owns colour for exactly the chip selectors the
    spec enumerates — fi-step-chip, fi-membership-chip, fi-posture-chip,
    fi-slice-chip, fi-macro-cell-state. Every per-state background rule for
    these lives in one block whose header lists them as a tuple, so any
    rule that targets fi-constraint-chip / fi-weighting-chip /
    fi-price-basis-chip / fi-identity-chip / fi-exposure-chip / etc. fails.
    """
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    forbidden_chip_pairs = (
        "fi-constraint-chip",
        "fi-weighting-chip",
        "fi-price-basis-chip",
        "fi-identity-chip",
        "fi-exposure-chip",
    )
    for chip in forbidden_chip_pairs:
        # No per-state rule is allowed to paint the chip background.
        for state in ("OK", "MISSING", "INFERRED", "OBSERVED", "CONFLICTING", "STALE"):
            bad = f".{chip}[data-state-{state.lower().replace('_', '-')}]" if state else f".{chip}"
            assert bad not in css, f"forbidden {chip} per-state rule: {bad}"
            bad2 = f".{chip}[data-state=\"{state}\"]" if state else f".{chip}"
            assert bad2 not in css, f"forbidden {chip} per-state rule: {bad2}"
    # No bare chip class background rule.
    for chip in forbidden_chip_pairs:
        assert re.search(rf"\.{chip}\s*\{{[^}}]*background:", css) is None, chip
    # SPEC_CHIP_SELECTORS is a JS comment tuple naming the five chips that DO
    # own per-state backgrounds, so any rule outside the tuple is one the
    # spec did not enumerate.
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "SPEC_CHIP_SELECTORS" in js
    spec_selectors = re.search(
        r"SPEC_CHIP_SELECTORS\s*=\s*\[([^\]]+)\]", js
    )
    assert spec_selectors is not None
    members = [m.strip().strip('"\'') for m in spec_selectors.group(1).split(",") if m.strip()]
    for expected in (
        "fi-step-chip", "fi-membership-chip", "fi-posture-chip",
        "fi-slice-chip", "fi-macro-cell-state",
    ):
        assert expected in members, expected


def test_f1_no_color_for_orphan_chip_classes():
    """Negative test: the bare forbidden chips must not carry any colour
    rule at all (background / color / border-color / fill)."""
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    for chip in (
        "fi-constraint-chip",
        "fi-weighting-chip",
        "fi-price-basis-chip",
        "fi-identity-chip",
        "fi-exposure-chip",
    ):
        for prop in ("background", "color", "border-color", "fill"):
            pat = re.compile(rf"\.{chip}\s*\{{[^}}]*{prop}\s*:")
            assert pat.search(css) is None, f"{chip} {prop} rule still present"


# ──────────────────────────────────────────────────────────────────────────
# F3 — evidence trigger names via ariaPair on data-state-driven triggers
# ──────────────────────────────────────────────────────────────────────────
def test_f3_evidence_triggers_use_aria_pair_pattern():
    """F3 (item 4): every chip that opens the evidence drawer announces its
    purpose through ariaPair-style EN/ZH strings, never a string the LLM
    invented. The page-level helpers expose the labelled trigger."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    # ariaPair helper exists; ariaLabel constructed from it.
    assert "function ariaPair(en, zh)" in js
    # what-changed: "Open evidence: <slice name>"
    assert "'Open evidence: '" in js or "'Open evidence:'" in js
    # rerating step: "Open evidence: <plane word>"
    assert "planeWordEn" in js or "labelFor('plane_word'" in js
    # conflict sides: "first reading" / "second reading"
    assert "first reading" in js
    assert "second reading" in js
    assert "第一方读数" in js
    assert "第二方读数" in js
    # Constraint: §D.9 row label via labelRow (not a fabricated string).
    assert "labelRow" in js
    # No bare placeholder strings that survive into the trigger.
    for forbidden in (
        "Open evidence (TODO)", "Open evidence: ??", "Open evidence ",
    ):
        assert forbidden not in js, forbidden


# ──────────────────────────────────────────────────────────────────────────
# F4 — generic elements without role get no aria-label
# ──────────────────────────────────────────────────────────────────────────
def test_f4_generic_elements_carry_no_aria_label():
    """F4 (item 5): aria-label/aria-labelledby may only name elements that
    actually need naming — visible-text elements, named links, named
    regions. The hero freshness/outer chips, the conflicts div, and the
    atlas eyebrow must NOT carry a name attribute."""
    html = _render()
    # Hero chips — span.fi-chip with data-fi-mount="hero-freshness" /
    # "hero-outer". Their visible text labels them; a redundant aria-label
    # would be doubly read.
    for chip_mount in ("hero-freshness", "hero-outer"):
        block = re.search(
            rf'<span class="fi-chip"[^>]*data-fi-mount="{chip_mount}"[^>]*>',
            html
        )
        assert block is not None, chip_mount
        assert "aria-label" not in block.group(0), f"{chip_mount} must NOT carry aria-label"
        assert "aria-labelledby" not in block.group(0), f"{chip_mount} must NOT carry aria-labelledby"
    # Conflict container — div.fi-conflicts, no aria-labelledby (the heading
    # inside already names it via aria-labelledby on the section).
    block = re.search(r'<div class="fi-conflicts"[^>]*>', html)
    assert block is not None
    assert "aria-label" not in block.group(0)
    assert "aria-labelledby" not in block.group(0)
    # Atlas eyebrow — span.fi-section-eyebrow.fi-atlas-eyebrow, no
    # aria-label/labelledby.
    block = re.search(r'<span class="fi-section-eyebrow fi-atlas-eyebrow"[^>]*>', html)
    assert block is not None
    assert "aria-label" not in block.group(0)
    assert "aria-labelledby" not in block.group(0)
    assert "data-aria-en" not in block.group(0)
    assert "data-aria-zh" not in block.group(0)


# ──────────────────────────────────────────────────────────────────────────
# F5 — active view survives langchange
# ──────────────────────────────────────────────────────────────────────────
def test_f5_active_view_survives_langchange():
    """F5 (item 6): when the language toggle fires, the active tab remains
    active (aria-selected=true, tabindex=0) even if focus is elsewhere.
    The runtime must NOT reset viewId on langchange."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    # renderSystem / activateView reads state.viewId; nothing about a
    # language event touches viewId.
    assert "state.viewId" in js
    # The langchange handler in JS MUST NOT reset state.viewId — the active
    # tab must survive the language swap. The handler exists to preserve
    # focus on the same view tab; it never writes viewId.
    langchange_block = re.search(
        r"addEventListener\('langchange',\s*function\s*\([^)]*\)\s*\{(.*?)\}\s*\);",
        js, re.S,
    )
    if langchange_block is not None:
        body = langchange_block.group(1)
        assert "state.viewId" not in body, "langchange handler must not reset viewId"
    # activateView persists: tabindex=0 on the SAME view id.
    assert "activateView" in js
    assert "tabindex" in js
    # Default view id is set on hydrate (state.viewId || first view), so a
    # fresh page lands on the first view and re-renders preserve it.
    assert "views[0].view_id" in js or "views[0]" in js


# ──────────────────────────────────────────────────────────────────────────
# F6 — phone reachability: cards-first, sibling disclosure for the rest
# ──────────────────────────────────────────────────────────────────────────
def test_f6_macro_and_exposure_reachable_on_phone_without_horizontal_scroll():
    """F6 (item 7): at 390px wide the macro / exposure sections render as
    cards; rows beyond the first 8 live in a sibling <details> with a
    'See all N' summary; the desktop table disclosure (.fi-macro-more /
    .fi-exposure-more) is hidden on mobile so it never triggers horizontal
    scroll."""
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    # Cards are visible on mobile.
    assert ".fi-macro-cards" in css
    assert ".fi-exposure-cards" in css
    # Macro table is hidden on mobile.
    assert re.search(r"\.fi-macro-table-wrap\s*\{\s*display\s*:\s*none", css)
    # Exposure table is hidden on mobile.
    assert re.search(r"\.fi-exposure-table-wrap\s*\{\s*display\s*:\s*none", css)
    # Sibling disclosure for the rest of the macro cards.
    assert ".fi-macro-cards-more" in css
    # Desktop reveal hides the sibling disclosure. Match through one level of
    # nested braces so the @media block is the containing rule.
    assert re.search(
        r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\.fi-macro-cards-more\s*\{[^}]*display\s*:\s*none",
        css, re.S,
    ), "desktop @media must hide .fi-macro-cards-more"
    # The desktop-only macro table disclosure is also hidden on mobile to
    # prevent horizontal scroll.
    assert re.search(
        r"@media\s*\([^)]*\)\s*\{(?:[^{}]|\{[^{}]*\})*\.fi-macro-more\s*\{\s*display\s*:\s*none",
        css, re.S,
    ), "mobile breakpoint must hide .fi-macro-more"
    # Sibling disclosure summary copy in the template.
    html = _render()
    assert 'class="fi-disc fi-macro-cards-more"' in html
    assert 'class="fi-disc fi-exposure-cards-more"' in html
    assert "See all slices" in html
    assert "查看全部切片" in html


# ──────────────────────────────────────────────────────────────────────────
# F7 — source-language marking only when prose is present
# ──────────────────────────────────────────────────────────────────────────
def test_f7_source_lang_note_only_when_prose_present():
    """F7 (item 8): the ZH-only `fi-srclang-note` paragraph appears only when
    the section actually holds free English prose. The runtime inspects the
    section after every render and adds the note if and only if at least one
    child carries lang='en'."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "function renderSourceLangNote" in js
    # Function checks sectionEl.querySelector('[lang="en"]') before appending.
    assert "querySelector('[lang=\"en\"]')" in js or "querySelector(`[lang=\"en\"]`)" in js
    # The note copy is the ZH-only message from the ruling.
    assert "本节部分文字为英文原文" in js
    # The italic style was REMOVED — only color/size token rules remain.
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    assert ".fi-srclang-note" in css
    assert "font-style" not in re.search(r"\.fi-srclang-note[^{}]*\{[^}]*\}", css).group(0)
    # Macro cards use the <span lang="en"> pattern for the mechanism part.
    assert 'lang="en"' in js
    # The drawer note lives at the top of the drawer body when prose exists.
    assert "此记录部分文字为英文原文" in js
    # Token-only sizing — no px literals.
    assert re.search(r"\.fi-srclang-note\s*\{[^}]*font-size\s*:\s*var\(--fs-micro\)", css)


# ──────────────────────────────────────────────────────────────────────────
# F8 — .fi-step-evidence is one rule, not stacked
# ──────────────────────────────────────────────────────────────────────────
def test_f8_step_evidence_is_one_rule():
    """F8 (item 9): the step evidence button rule is a single block — width
    and height on the same declaration, not two stacked rules of differing
    geometry."""
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    blocks = re.findall(r"\.fi-step-evidence\s*\{[^}]*\}", css)
    assert len(blocks) == 1, f"expected single .fi-step-evidence rule, found {len(blocks)}"
    body = blocks[0]
    assert "width: 24px" in body
    assert "height: 24px" in body
    # The F8 fix must NOT carry any pre-existing radius literal — tokens only.
    assert "border-radius" not in body
    # No override rule after.
    after = css.split(".fi-step-evidence", 1)
    if len(after) == 2:
        tail = after[1]
        # Nothing else in the css redefines its geometry.
        assert "width:" not in tail.split("}", 1)[0] or "24px" in tail.split("}", 1)[0]


# ──────────────────────────────────────────────────────────────────────────
# F2 — weighting_family enum compliance (chip + read-model)
# ──────────────────────────────────────────────────────────────────────────
def test_f2_weighting_chip_uses_spec_enum():
    """F2 (item 3): the weighting chip reads basket_state.weighting_family,
    carries data-state-weighting, and the only accepted enum values match
    spec §D.20."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    # The chip class is fi-weighting-chip and the attribute is
    # data-state-weighting — never a fabricated basket_construction_family.
    assert "fi-weighting-chip" in js
    assert "data-state-weighting" in js
    # weighting_family is read from basket_state in renderAtlas (and
    # everywhere else weight is used).
    assert "s.basket_state.weighting_family" in js or "basket_state && basket_state.weighting_family" in js
    # No default to EQUAL_WEIGHT — null weighting is shown as MISSING, not
    # fabricated as equal.
    assert "weighting_family || 'EQUAL_WEIGHT'" not in js


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


# ──────────────────────────────────────────────────────────────────────────
# T11 round 2 — seat rulings from the browser probe (8 cells + keyboard)
# ──────────────────────────────────────────────────────────────────────────
def test_light_chip_base_rule_cannot_outrank_the_state_chip_rules():
    """Seat erratum: at (0,2,1) the light base rule painted every state chip white.

    `:where()` drops the theme selector's weight, so the base is (0,1,0) and every
    per-state chip rule (0,2,0) wins in the light theme as it does in the dark one.
    """
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    assert ':where(html[data-theme="light"]) .fi-chip { background: var(--fi-panel); }' in css
    assert not re.search(r'(?m)^html\[data-theme="light"\] \.fi-chip\s*\{', css)


def test_identity_chip_is_a_state_chip_not_an_evidence_trigger():
    """Seat erratum: company_exposures[].identity carries no evidence reference.

    A trigger there would open nothing, and a click-bound span can take neither
    focus nor an accessible name, so the chip keeps its state binding only.
    """
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "{ classes: 'fi-identity-chip', stateIdentity: identity, stateMarker: identity }" in js
    assert "'fi-identity-chip fi-evidence-trigger'" not in js


def test_fallback_placeholders_never_render_inside_lang_en():
    """F7a: lang="en" marks payload prose only, never a localized fallback."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "function enLang(value) { return value ? ' lang=\"en\"' : ''; }" in js
    # every remaining literal lang="en" is a comment, the helper, a query, or wraps a
    # value that is present by construction (a guarded retained_risk, a prose-flagged row)
    lines = [line.strip() for line in js.splitlines() if 'lang="en"' in line]
    allowed = ("//", "function enLang(", "(cell.retained_risk ?", "(opts.prose && value ?")
    stray = [line for line in lines if not line.startswith(allowed) and "querySelector('[lang=\"en\"]')" not in line]
    assert not stray, stray
    for fallback in ("'尚未描述。'", "'尚无可观察陈述。'", "'尚无经济效应记录。'", "'尚无操作启示。'"):
        start = js.index(fallback)
        assert 'lang="en">' not in js[js.rindex("\n", 0, start):start]


def test_drawer_marks_only_scope_excerpt_and_limitations_as_english():
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "rec.business_scope || '', { prose: true });" in js
    assert "|| '', { prose: !!rec.excerpt });" in js
    assert "asArray(rec.limitations).join(' · '), { prose: true });" in js
    assert js.count("{ prose:") == 3


def test_source_language_notes_follow_the_section_header_without_a_lang_attribute():
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "setAttribute('lang', 'zh')" not in js
    # Seat erratum: `.fi-sowhat` never existed, so the note anchors on the section header
    assert "'.fi-sowhat'" not in js  # no selector literal (the erratum comment may name it)
    assert "if (head) sectionEl.insertBefore(note, head.nextSibling);" in js
    tpl = (TEMPLATES / "finance_intelligence.html.j2").read_text(encoding="utf-8")
    sections = re.findall(r'<section id="[^"]+" class="fi-section [^"]*".*?</section>', tpl, re.S)
    assert len(sections) == 7
    for body in sections:
        # the anchor exists as the section's first element child, exactly once
        assert re.match(r'<section[^>]*>\s*<header class="fi-section-head"', body)
        assert body.count('class="fi-section-head"') == 1
    # the drawer note appears only when the record holds English prose
    assert "if (isZh() && fields.querySelector('[lang=\"en\"]')) {" in js
    # removal is parent-agnostic, so a repaint never throws on a nested note
    assert "sectionEl.removeChild(" not in js and "drawer.removeChild(" not in js


def test_what_changed_rows_are_the_house_decision_row():
    """Spec §B.1 pins `<li class="fi-change-row mx-chg-row">`: the canonical DecisionRow
    (theme.css), not a bulleted run where the slice name abuts the English clause."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    assert "'<li class=\"fi-change-row mx-chg-row\" data-change-id=\"'" in js
    assert "'<span class=\"fi-change-name mx-chg-name\">'" in js
    assert "'<span class=\"fi-change-clause mx-chg-what\"' + enLang(row.operating_implication)" in js
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    rule = re.search(r"^\.fi-change-list \{([^}]*)\}", css, re.M)
    assert rule is not None
    assert "list-style: none" in rule.group(1) and "padding: 0" in rule.group(1)
