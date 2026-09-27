"""tests/test_basket_intelligence_mounts.py — T10b basket-intelligence include seam.

The seam is intentionally narrow: ONE `{% include %}` line in basket_detail.html.j2
that pulls in a guarded aggregator, which in turn pulls in one partial per vertical
with `ignore missing`. The theme-research entry renders a hidden mount when (and
only when) the render context provides `theme_research_mount` — the nine-key
context a registration produces (shared hook 2); absent or malformed the entry is
silent. The entry names no vertical: every string in the section comes from that
context, which is why these tests read it from the registration rather than
retyping it.

L1:  The include sits after `<a class="back">` and before `<div id="app">`, exactly
     once, and is the ONLY line of basket_detail.html.j2 that changes (`git diff
     --numstat` = `1\\t0`).
L2:  Optional verticals never break the incumbent page — `ignore missing` everywhere.
L3:  The base render's asset order is preserved: every <script>/<link> present in the
     base stays in the same relative order; theme.js stays LAST. New assets are
     ADDED, never reordered.
L4:  `theme_research_mount` absent/malformed → entry emits nothing (no mount, no
     assets); a missing section partial emits no orphan asset tag either.
L5:  With a valid mount context → exactly one mount, hidden, both asset tags
     present, every attribute and visible string equal to the registration's.
L6:  Every visible string flows through `t('en','zh')`; no raw slug, no concat.
L7:  No analytical data, payload, figure, token or URL beyond the two asset paths
     and two API paths.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
T10B_BASE_COMMIT = "b256aa6a756a"          # head pre-T10b; diff must show `1\t0`

MOUNT_ANCHOR = "ai_semiconductors"


def _mount_ctx(anchor: str = MOUNT_ANCHOR) -> dict:
    """The render context a page builder passes, read from the registration.

    Deliberately NOT retyped here: the point of shared hook 2 is that the
    mount renders the registration's strings, so a test that hard-pinned its
    own copy would pass while the page rendered something else. The import is
    the leaf mounts module only — importing the registry would drag the whole
    company-intelligence stack into this suite's CI closure.
    """
    from engine.market_ontology.theme_research_mounts import mount_context

    context = mount_context(anchor)
    assert context is not None, f"no registered mount for {anchor!r}"
    return dict(context)

# ---------------------------------------------------------------------------
# Synthetic root + Jinja env (same loader/filters test_state_of_themes.py uses)
# ---------------------------------------------------------------------------


def _make_basket_root(
    tmp_path: Path,
    *,
    include_theme_research: bool = True,
    include_aggregator: bool = True,
    include_section: bool = True,
    extra_partials: tuple[str, ...] = (),
) -> Path:
    """Build a minimal synthetic repo root for basket_detail.html.j2 rendering.

    Mirrors tests/test_state_of_themes.py::_make_sot_root in shape — copies the
    template(s) under test plus the support partials (`_site_nav`, `_navlinks`,
    `_seo_head`) the basket page transcludes.

    Pass `include_theme_research=False` to DELETE the vertical partial (the
    "missing optional vertical" case for L2). Pass `include_aggregator=False`
    to drop the aggregator partial entirely (pure-base render for diff checks).
    Pass `include_section=False` to keep the entry but DELETE the section it
    includes — the half-installed vertical, which must still emit nothing.
    """
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    # The shell under test
    (templates_dir / "basket_detail.html.j2").write_bytes(
        (REPO_ROOT / "templates" / "basket_detail.html.j2").read_bytes()
    )

    # The two new partials (only copied when present on the working tree — the
    # test is robust to them being absent before authoring, which is exactly
    # the L2 failure mode).
    if include_aggregator and (REPO_ROOT / "templates" / "_basket_intelligence_mounts.html.j2").exists():
        (templates_dir / "_basket_intelligence_mounts.html.j2").write_bytes(
            (REPO_ROOT / "templates" / "_basket_intelligence_mounts.html.j2").read_bytes()
        )
    if include_theme_research and (REPO_ROOT / "templates" / "_theme_research_mount.html.j2").exists():
        (templates_dir / "_theme_research_mount.html.j2").write_bytes(
            (REPO_ROOT / "templates" / "_theme_research_mount.html.j2").read_bytes()
        )
    section_src = REPO_ROOT / "templates" / "_theme_research_section.html.j2"
    if include_theme_research and include_section and section_src.exists():
        (templates_dir / "_theme_research_section.html.j2").write_bytes(
            section_src.read_bytes()
        )

    # Support partials the basket page transcludes. Same set test_state_of_themes
    # uses; basket_detail uses _site_nav (the adopted product nav).
    for name in ("_site_nav.html.j2", "_navlinks.html.j2", "_seo_head.html.j2"):
        src = REPO_ROOT / "templates" / name
        if src.exists():
            (templates_dir / name).write_bytes(src.read_bytes())

    for name in extra_partials:
        src = REPO_ROOT / "templates" / name
        if src.exists():
            (templates_dir / name).write_bytes(src.read_bytes())

    return tmp_path


def _render_basket_detail(
    root: Path,
    *,
    context: dict | None = None,
) -> str:
    """Render templates/basket_detail.html.j2 against `root` with a context.

    Builds the Jinja env the same way scripts/build_state_of_themes.render()
    does (FileSystemLoader + autoescape + Undefined). Returns the rendered HTML.
    """
    import jinja2

    templates_dir = root / "templates"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        autoescape=True,
        undefined=jinja2.Undefined,
    )
    ctx = {
        # Minimal context — what build_theme_detail.py's render path already
        # guarantees. `theme_research_anchor` is intentionally NOT in this
        # default ctx so the L4 "absent" path is reachable as a literal base.
        "back_href": "../sector_central.html",
        "back_label_en": "Sector Intelligence",
        "back_label_zh": "行业情报",
        "basket_name": "Test Basket",
        "detail_json": "{}",
        "generated_utc": "2026-09-24T00:00:00Z",
        "nav_context_links": [],
    }
    if context:
        ctx.update(context)
    return env.get_template("basket_detail.html.j2").render(**ctx)


_INCLUDE_RE = re.compile(
    r'\{%\s*include\s+["\']([^"\']+)["\']', re.IGNORECASE
)


def _scripts_in_doc_order(html: str) -> list[str]:
    """All `<script src=...>` URLs in document order."""
    out = []
    for m in re.finditer(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', html, re.IGNORECASE):
        out.append(m.group(1))
    return out


def _links_in_doc_order(html: str) -> list[str]:
    """All `<link ... href=...>` URLs in document order."""
    out = []
    for m in re.finditer(r'<link\b[^>]*\bhref=["\']([^"\']+)["\']', html, re.IGNORECASE):
        out.append(m.group(1))
    return out


def _ws_collapsed(html: str) -> str:
    """Collapse runs of whitespace to a single space and trim ends.

    The L2 "byte-identical except for the aggregator's empty output" law
    tolerates a single whitespace token at the include point (the newline
    the `{% include %}` directive emits when its target renders empty). Every
    non-whitespace byte must match the base render.
    """
    return re.sub(r"\s+", " ", html).strip()


def _structural_equality_explain(base: str, candidate: str) -> str:
    """Return a short explanation of how `base` and `candidate` differ,
    tolerating only whitespace differences outside the include area."""
    if base == candidate:
        return ""
    a, b = _ws_collapsed(base), _ws_collapsed(candidate)
    if a == b:
        return "differs only in whitespace (legal — aggregator's own empty output)"
    return f"non-whitespace differs (collapsed):\n  base[:120]={a[:120]!r}\n  cand[:120]={b[:120]!r}"


def _back_app_marker_lines(src: str) -> tuple[int, int, int]:
    """Return (back-line, include-line, #app-line) — the L1 anchors."""
    lines = src.splitlines()
    back = next(
        (i + 1 for i, ln in enumerate(lines) if 'class="back"' in ln and "<a " in ln),
        -1,
    )
    app = next(
        (i + 1 for i, ln in enumerate(lines) if 'id="app"' in ln and "<div" in ln),
        -1,
    )
    inc = next(
        (i + 1 for i, ln in enumerate(lines) if "_basket_intelligence_mounts" in ln),
        -1,
    )
    return back, inc, app


# ---------------------------------------------------------------------------
# 1 — L1: exactly one include of the aggregator, outside #app
# ---------------------------------------------------------------------------

def test_common_template_has_exactly_one_aggregator_include_outside_app():
    """basket_detail.html.j2 includes the aggregator exactly once, and the include
    sits AFTER the back link and BEFORE `#app`."""
    src = (REPO_ROOT / "templates" / "basket_detail.html.j2").read_text(encoding="utf-8")
    n_includes = len(_INCLUDE_RE.findall(src))
    inc_targets = [
        m.group(1) for m in _INCLUDE_RE.finditer(src)
        if "basket_intelligence_mounts" in m.group(1)
    ]
    assert len(inc_targets) == 1, (
        f"expected exactly 1 include of _basket_intelligence_mounts; got "
        f"{len(inc_targets)} (count of ALL includes in the file: {n_includes})"
    )
    back, inc, app = _back_app_marker_lines(src)
    assert back > 0 and app > 0 and inc > 0, (
        f"missing one of back/include/#app anchors: back={back}, "
        f"include={inc}, #app={app}"
    )
    assert back < inc < app, (
        f"include must sit AFTER back link and BEFORE #app; got "
        f"back={back}, include={inc}, #app={app}"
    )


# ---------------------------------------------------------------------------
# 2 — L1 (diff): the only change to basket_detail.html.j2 is the new include line
# ---------------------------------------------------------------------------

def test_basket_detail_diff_is_exactly_one_inserted_line():
    """`git diff --numstat` of basket_detail.html.j2 vs. the pre-T10b head must
    be exactly `1\\t0` — one inserted line, zero deleted lines.

    This is the one assertion in this suite that needs *history* rather than
    working-tree content. The added line and its position are already pinned
    from the tree by ``test_common_template_has_exactly_one_aggregator_include
    _outside_app``; what only a diff can show is the ``-0`` — that nothing else
    in a template frozen by #7669 moved. A checkout that does not carry
    ``T10B_BASE_COMMIT`` cannot evaluate that claim at all: git answers
    ``fatal: bad revision`` with exit 128, which a bare returncode assertion
    reports as a template regression that did not happen. Resolve the base
    first and skip honestly when it is absent.
    """
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet",
         f"{T10B_BASE_COMMIT}^{{commit}}"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if resolved.returncode != 0:
        pytest.skip(
            f"pre-T10b base {T10B_BASE_COMMIT} is not present in this checkout "
            f"(shallow clone / grafted history), so the -0 half of L1 is not "
            f"evaluable here; the tree-content half is covered by "
            f"test_common_template_has_exactly_one_aggregator_include_outside_app"
        )
    result = subprocess.run(
        ["git", "diff", "--numstat", T10B_BASE_COMMIT, "--",
         "templates/basket_detail.html.j2"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"git diff failed:\nSTDOUT={result.stdout}\nSTDERR={result.stderr}"
    )
    line = result.stdout.strip()
    parts = line.split("\t")
    assert len(parts) >= 2, f"unexpected numstat output: {line!r}"
    added, deleted = int(parts[0]), int(parts[1])
    assert (added, deleted) == (1, 0), (
        f"basket_detail diff must be exactly +1/-0; got +{added}/-{deleted} "
        f"(numstat: {line!r})"
    )


# ---------------------------------------------------------------------------
# 3 — L2: a missing optional partial never breaks the page
# ---------------------------------------------------------------------------

def test_missing_vertical_partial_does_not_break_the_page(tmp_path):
    """Delete the semiconductor vertical from the loader → page still renders,
    no theme-research mount present, identical to a base render without the
    aggregator's output."""
    # (a) Pure base: copy the shell, drop the partials we don't need
    root_base = _make_basket_root(tmp_path, include_aggregator=False)
    base_html = _render_basket_detail(root_base)

    # (b) Same shell WITH the aggregator, but the vertical is missing
    root_anchorless = _make_basket_root(tmp_path)
    vertical_path = root_anchorless / "templates" / "_theme_research_mount.html.j2"
    if vertical_path.exists():
        vertical_path.unlink()
    rendered = _render_basket_detail(root_anchorless)

    # The page is still a complete HTML doc
    assert "<!DOCTYPE html>" in rendered
    # The mount attribute is absent (semiconductor partial didn't render)
    assert "data-theme-research-mount" not in rendered
    # The theme-research assets are absent
    assert "theme-research.js" not in rendered
    assert "theme-research.css" not in rendered
    # L2: page is byte-identical to the base render except for the aggregator's
    # own (empty) output. Whitespace-only drift at the include point is the
    # legal carve-out (the `{% include %}` directive emits a single newline
    # when its target renders empty); any other byte change breaks L2.
    assert rendered == base_html or _ws_collapsed(rendered) == _ws_collapsed(base_html), (
        "missing vertical → rendered HTML must equal the base render, modulo "
        "whitespace at the include point. " + _structural_equality_explain(base_html, rendered)
    )


# ---------------------------------------------------------------------------
# 4 — L3: theme.js stays the LAST script; new assets ADDED, never reordered
# ---------------------------------------------------------------------------

def test_asset_order_preserved_and_theme_js_last(tmp_path):
    """The base's <script>/<link> order is preserved through the include; theme.js
    is still the LAST <script src> in the rendered HTML — both with and without
    a theme_research_anchor.

    Without anchor: rendered is byte-identical to the base render.
    With anchor: NEW assets are added at the include position; theme.js stays last
    among <script src=>; every base asset URL still appears in the same relative
    order inside its own kind (scripts with scripts, links with links).
    """
    # (a) Without anchor → byte-identical to the base render (modulo the include's
    # own empty-output whitespace, per L2).
    root_base = _make_basket_root(tmp_path, include_aggregator=False)
    base_html = _render_basket_detail(root_base)
    root_anchorless = _make_basket_root(tmp_path)
    if (root_anchorless / "templates" / "_theme_research_mount.html.j2").exists():
        (root_anchorless / "templates" / "_theme_research_mount.html.j2").unlink()
    anchorless_html = _render_basket_detail(root_anchorless)
    assert anchorless_html == base_html or _ws_collapsed(anchorless_html) == _ws_collapsed(base_html), (
        "anchorless render must equal the base render byte-for-byte (modulo the "
        "include's empty-output whitespace). " + _structural_equality_explain(base_html, anchorless_html)
    )

    base_scripts = _scripts_in_doc_order(base_html)
    base_links = _links_in_doc_order(base_html)
    # Last <script src=> in the base MUST be theme.js (L3, explicit)
    assert base_scripts[-1].endswith("theme.js"), (
        f"in the BASE render, theme.js must be the last <script src=>. "
        f"Scripts tail: {base_scripts[-5:]}"
    )
    # Confirm theme.js is the very last entry overall
    assert base_scripts[-1].endswith("theme.js")

    # (b) WITH anchor — new assets are ADDED at the include position, theme.js
    #     still last among <script src=>; base URLs in each kind keep relative order.
    root_anchor = _make_basket_root(tmp_path)
    anchor_html = _render_basket_detail(
        root_anchor,
        context={"theme_research_mount": _mount_ctx()},
    )
    anchor_scripts = _scripts_in_doc_order(anchor_html)
    anchor_links = _links_in_doc_order(anchor_html)
    assert anchor_scripts[-1].endswith("theme.js"), (
        f"theme.js must still be the last <script src=> with anchor ON; tail: "
        f"{anchor_scripts[-5:]}"
    )
    # The two new assets must be present
    assert any("theme-research.css" in u for u in anchor_links)
    assert any("theme-research.js" in u for u in anchor_scripts)

    # Every base script URL still appears, in the same relative order. Anchor-mode
    # is allowed to ADD `theme-research.js` SOMEWHERE in the list — but every
    # element of base_scripts must still be present in anchor_scripts in the
    # SAME relative order.
    def _relative_order(haystack, needles):
        indices = [haystack.index(u) for u in needles if u in haystack]
        return indices

    assert _relative_order(anchor_scripts, base_scripts) == sorted(
        _relative_order(anchor_scripts, base_scripts)
    ), (
        f"base <script> order changed under anchor ON: "
        f"{anchor_scripts} vs {base_scripts}"
    )
    assert _relative_order(anchor_links, base_links) == sorted(
        _relative_order(anchor_links, base_links)
    ), (
        f"base <link> order changed under anchor ON: "
        f"{anchor_links} vs {base_links}"
    )


# ---------------------------------------------------------------------------
# 5 — L4/L5: silent without anchor; mounted with anchor; rejects invalid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mount", [None, {}, "", "ai_semiconductors", 7, []])
def test_partial_silent_without_anchor(tmp_path, mount):
    """Absent, empty or non-mapping `theme_research_mount` → no mount, no asset
    tags, no theme-research section, no anchor attribute.

    A bare anchor STRING is in this list on purpose: the pre-hook-2 context key
    carried one, and a page that still passes it must mount nothing rather than
    render a section with no registration behind it."""
    root = _make_basket_root(tmp_path)
    ctx = {} if mount is None else {"theme_research_mount": mount}
    html = _render_basket_detail(root, context=ctx)
    assert "data-theme-research-mount" not in html
    assert "theme-research.js" not in html
    assert "theme-research.css" not in html
    assert 'class="theme-research"' not in html


def test_partial_mounted_with_valid_anchor(tmp_path):
    """A valid mount context renders exactly one mount, hidden, with both asset
    tags and EVERY attribute and visible string equal to the registration's.

    The assertions read `mount` rather than literals, so a registration that
    changes its anchor, slices, schema ids or copy moves this test with it —
    and a template that goes back to hard-pinning one vertical fails it."""
    root = _make_basket_root(tmp_path)
    mount = _mount_ctx()
    html = _render_basket_detail(root, context={"theme_research_mount": mount})
    # Exactly one mount present
    n_mount = html.count("data-theme-research-mount")
    assert n_mount == 1, f"expected exactly 1 mount; got {n_mount}"
    # The mount is hidden in the static render
    assert re.search(
        r'<section[^>]*data-theme-research-mount[^>]*\bhidden\b', html
    ), "mount section must carry the hidden attribute"
    # Every machine-read attribute equals the registration's own string
    assert f'data-anchor-theme-id="{mount["anchor_theme_id"]}"' in html
    assert f'data-slices="{mount["slices"]}"' in html
    assert f'data-schema-id="{mount["schema_id"]}"' in html
    assert f'data-evidence-schema-id="{mount["evidence_schema_id"]}"' in html
    # The bilingual slice copy travels as ONE escaped JSON attribute, so the
    # client never carries a second copy of the slice names.
    import html as _html
    m_labels = re.search(r'data-slice-labels="([^"]*)"', html)
    assert m_labels, "the mount must carry the registration's slice labels"
    assert _html.unescape(m_labels.group(1)) == mount["slice_labels_json"]
    # The section's id and its title's id are anchor-scoped and agree, so two
    # verticals on one page cannot collide (and aria-labelledby still resolves).
    assert f'id="theme-research-{mount["anchor_theme_id"]}"' in html
    assert f'aria-labelledby="theme-research-{mount["anchor_theme_id"]}-title"' in html
    assert f'id="theme-research-{mount["anchor_theme_id"]}-title"' in html
    # Both asset tags present, with defer only on the script
    assert 'rel="stylesheet" href="../assets/css/theme-research.css"' in html
    assert (
        '<script defer src="../assets/js/theme-research.js?v=20260924b">'
        '</script>' in html
    )
    # Bilingual title and note (en + zh span), both halves from the registration
    for key in ("title_en", "title_zh", "note_en", "note_zh"):
        assert mount[key] in html, f"the mount must render the registration's {key}"
    # BOTH visible strings flow through t('en','zh') — substring presence is
    # not enough: an independent review mutated the note to two bare escaped
    # values, putting both languages on screen at once, and every test still
    # passed because only the title's spans were asserted (L6).
    for key_en, key_zh in (("title_en", "title_zh"), ("note_en", "note_zh")):
        assert f'<span class="l-en">{mount[key_en]}</span>' in html, key_en
        assert f'<span class="l-zh">{mount[key_zh]}</span>' in html, key_zh
    assert f'{mount["note_en"]} {mount["note_zh"]}' not in html, (
        "the two languages must never sit adjacent outside their toggle spans"
    )


@pytest.mark.parametrize("bad_anchor", [
    "Has-Caps",         # dash fails ^[a-z0-9_]+$
    "has spaces",       # contains space
    "ai.semiconductors",  # contains dot
    "ai/semi",          # contains slash
    "ai;drop",          # contains punctuation
    "<script>",         # injection attempt
])
def test_partial_silent_for_invalid_anchor(tmp_path, bad_anchor):
    """A mount context whose anchor fails ^[a-z0-9_]+$ → entry stays silent.

    The rest of the context is a real registration's, so the only reason to
    refuse is the anchor itself."""
    root = _make_basket_root(tmp_path)
    html = _render_basket_detail(
        root,
        context={"theme_research_mount": {**_mount_ctx(), "anchor_theme_id": bad_anchor}},
    )
    assert "data-theme-research-mount" not in html
    assert "theme-research.js" not in html
    assert "theme-research.css" not in html
    assert "Semiconductor industry research" not in html


# ---------------------------------------------------------------------------
# 5b — shared hook 2: the templates name no vertical, and a half-installed
#      vertical emits nothing at all
# ---------------------------------------------------------------------------

def test_half_installed_vertical_emits_no_orphan_asset(tmp_path):
    """Entry present, section partial missing → not one byte of mount or asset.

    `ignore missing` protects the incumbent page from a vertical that has not
    landed (L2). It would not protect it from a stylesheet and a client script
    loaded for a section that never rendered, so the entry captures the
    section's output before it emits either asset tag.
    """
    root = _make_basket_root(tmp_path, include_section=False)
    html = _render_basket_detail(root, context={"theme_research_mount": _mount_ctx()})
    assert "data-theme-research-mount" not in html
    assert "theme-research.css" not in html
    assert "theme-research.js" not in html
    assert 'class="theme-research"' not in html


@pytest.mark.parametrize("template_name", [
    "_theme_research_mount.html.j2",
    "_theme_research_section.html.j2",
])
def test_mount_templates_name_no_vertical(template_name):
    """Neither template contains a vertical's anchor, slice or bilingual copy.

    This is the whole of shared hook 2: before it, the anchor, both slice keys
    and the bilingual title/note were typed into the template, so a second
    vertical could not mount without editing it. A registration string
    reappearing in either file means the drift has come back — the page would
    then render one vertical's copy no matter which registration mounted it.
    """
    source = (REPO_ROOT / "templates" / template_name).read_text(encoding="utf-8")
    mount = _mount_ctx()
    forbidden = {
        "anchor": mount["anchor_theme_id"],
        "slices": mount["slices"],
        "schema": mount["schema_id"],
        "title_en": mount["title_en"],
        "title_zh": mount["title_zh"],
        "note_en": mount["note_en"],
        "note_zh": mount["note_zh"],
    }
    for slice_key in mount["slices"].split(","):
        forbidden[f"slice:{slice_key}"] = slice_key
    leaked = sorted(name for name, value in forbidden.items() if value in source)
    assert not leaked, (
        f"{template_name} hard-pins registration strings again: {leaked}"
    )


# ---------------------------------------------------------------------------
# 6 — L7: no analytical data, payload, figure, token or URL beyond the four
# ---------------------------------------------------------------------------

def test_partial_carries_no_data_or_payload(tmp_path):
    """The rendered partial carries only the four declared strings/paths
    (stylesheet href, js src, two API paths, anchor attribute) — no digits-
    with-units, no other http(s)://, no `gen_`/`gmirca_` markers."""
    root = _make_basket_root(tmp_path)
    html = _render_basket_detail(root, context={"theme_research_mount": _mount_ctx()})
    # Slice out ONLY the mount section for inspection — outside the section
    # the page legitimately renders other URLs (e.g., ../live/shock_state.json).
    m = re.search(
        r'(<section[^>]*data-theme-research-mount.*?</section>)',
        html, re.DOTALL,
    )
    assert m, "could not isolate the theme-research mount section"
    block = m.group(1)

    # The two API paths AND the two asset hrefs are the ONLY URLs in the block
    allowed = {
        "../assets/css/theme-research.css",
        "../assets/js/theme-research.js?v=20260924b",
        "/api/themes/v1/research/query",
        "/api/themes/v1/research/evidence",
    }
    urls = re.findall(r'(?:href|src)="([^"]+)"|/api/[^"\s]+', block)
    offending = [u for u in urls if u and u not in allowed]
    assert not offending, (
        f"unexpected URL(s) in the mount block: {offending}"
    )

    # No http(s):// anywhere in the block (no external fetches either)
    assert not re.search(r'https?://', block), (
        "the partial must not embed any http(s):// URL — display-tier only"
    )

    # No digits-with-units patterns; mount carries no figure at rest.
    assert not re.search(r'\b\d+(?:\.\d+)?(?:%|x|ms|s|m|h|d|w|kb|mb)\b', block), (
        "the mount block must carry no digit-with-unit figure at rest"
    )

    # Internal marker strings must never bleed into user-facing render
    assert "gen_" not in block, "internal `gen_` marker leaked into the mount"
    assert "gmirca_" not in block, "internal `gmirca_` marker leaked into the mount"


# ---------------------------------------------------------------------------
# 7 — Regression: state_of_themes.html.j2 renders without crash, byte-identity
# ---------------------------------------------------------------------------

def test_state_of_themes_render_unchanged():
    """state_of_themes.html.j2 is not touched by T10b — it should still render
    without a crash and produce a complete HTML document."""
    import scripts.build_state_of_themes as sot
    html_a = sot.render(REPO_ROOT)
    html_b = sot.render(REPO_ROOT)         # render twice — the byte is deterministic
    assert "<!DOCTYPE html>" in html_a
    # The page renders; rendering it twice is byte-stable (no state).
    assert html_a == html_b, (
        "state_of_themes render is non-deterministic across identical calls"
    )


# ---------------------------------------------------------------------------
# Reference data — sourced from the f53c7c3845b3 reviewed lane (T10 part 1)
# ---------------------------------------------------------------------------
# Repository note: the asset PATHS (../assets/js/theme-research.js,
# ../assets/css/theme-research.css) and the mount shape are the reviewed
# lane's contract verbatim from commit f53c7c3845b3 (present in this repo's
# object store, NOT on the carrier branch). This suite only pins the SEAM
# (one include, "ignore missing" verticals, anchor gate, asset order), not
# the assets themselves — those land with T10 part 1.
