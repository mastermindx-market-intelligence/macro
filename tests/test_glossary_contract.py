"""Rendered-page + wiring contract for the public glossary."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from lib import config
from lib.glossary import BANNED_GLANCE_PATTERNS, BANNED_GLANCE_TOKENS, glossary_view_model
from lib.help_directory import HELP_LINKS

ROOT = config.ROOT


def _render() -> str:
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    vm = glossary_view_model(ROOT)
    return env.get_template("glossary.html.j2").render(generated_utc="2026-01-01 00:00", **vm)


def test_rendered_glossary_lists_every_term_in_both_languages():
    html = _render().replace("&amp;", "&")
    vm = glossary_view_model(ROOT)
    for domain in vm["domains"]:
        for term in domain["terms"]:
            assert term["name_en"] in html
            assert term["name_zh"] in html


def test_rendered_glossary_has_no_title_attributes_on_page_chrome():
    html = _render()
    start = html.index('<main class="gl-shell" id="glossary"')
    end = html.index("</main>", start)
    main = html[start:end]
    assert "title=" not in main


def test_rendered_glossary_uses_public_chrome_not_member_navigation():
    html = _render()
    assert '<nav class="public-nav"' in html
    assert '<footer class="public-footer">' in html
    assert "site-nav" not in html
    assert "_navlinks" not in html


def test_rendered_letter_rail_marks_empty_letters_disabled():
    html = _render()
    vm = glossary_view_model(ROOT)
    for letter in vm["letters"]:
        if letter["count"] == 0:
            frag_re = re.compile(
                r'<span class="gl-letter is-empty" data-letter="' + re.escape(letter["id"])
                + r'" aria-disabled="true">'
            )
            assert frag_re.search(html), letter["id"]


def test_rendered_glossary_shows_a_why_paragraph_for_every_term():
    """B-F13-1 audit heal (m#6909) H1: every row must show its 'so what'
    paragraph, not only the 15 that were already paired — the page's
    "what you do about it" promise is row-level, not optional."""
    html = _render()
    vm = glossary_view_model(ROOT)
    term_count = vm["term_count"]
    paragraphs = re.findall(r'<p class="gl-why">.*?</p>', html, re.S)
    assert len(paragraphs) == term_count, (
        f"rendered page carries {len(paragraphs)} .gl-why paragraphs but "
        f"the view model exposes {term_count} terms; every row must carry a why"
    )


def test_rendered_rail_note_makes_no_permanent_claim_about_a_transient_state():
    """B-F13-1 audit heal (m#6909) H3: the rail note must read the same way
    whether the view is the full set or has been filtered — 'yet' or '暂无'
    assert a permanent state ('no terms exist') that is not true the moment
    a user types in the search or hits a filter that hides rows. Both EN and
    ZH must avoid that claim."""
    html = _render()
    m = re.search(r'<p class="gl-rail-note">(.*?)</p>', html, re.S)
    assert m, "rendered page missing .gl-rail-note paragraph"
    note = re.sub(r"<[^>]+>", "", m.group(1))
    assert "yet" not in note.lower(), note
    assert "暂无" not in note, note
    # Absence alone would also pass if the ZH half were deleted, so the
    # replacement sentence is pinned in BOTH languages (review round 2,
    # MINOR 2): one static `t()` pair, an ASCII sentence and a CJK one.
    en = re.search(r'<span class="l-en">(.*?)</span>', m.group(1), re.S)
    zh = re.search(r'<span class="l-zh">(.*?)</span>', m.group(1), re.S)
    assert en and en.group(1).strip(), m.group(1)
    assert zh and zh.group(1).strip(), m.group(1)
    assert "nothing to show in this view" in en.group(1), en.group(1)
    assert re.search(r"[\u4e00-\u9fff]", zh.group(1)), zh.group(1)
    assert "当前视图" in zh.group(1), zh.group(1)


# daily.yml's `scripts/inject_wh_banner.py` splices this one tag into every
# generated page; the public-render fast lane never runs that sweep, so a
# regenerated page must carry the committed tag over byte-for-byte. Same shape
# as `_WHB_TAG_RE` in scripts/build_free_content.py, whose `_carry_over_wh_banner`
# exists because "wh_banner is the one sweep we cannot replay".
_WHB_TAG_RE = re.compile(r"[ \t]*<script[^>]*\bdata-whb\b[^>]*></script>\n?")


def test_committed_glossary_page_carries_the_alert_banner_script():
    """B-F13-1 review round 2, BLOCKER 1: regenerating site/glossary.html
    dropped the page's `<script defer data-whb …>` tag, so merging would have
    removed the alert banner from the live public /glossary only — the fleet
    count went 3747 → 3746 with this page as the single loss. The site-pair
    test below cannot see it (the fast-path render never injects the tag), so
    the committed page is pinned directly: exactly one banner tag, before
    `</body>`, pointing at wh_banner.js."""
    html = (config.site_dir() / "glossary.html").read_text(encoding="utf-8")
    tags = re.findall(r'<script[^>]*\bdata-whb\b[^>]*></script>', html)
    assert len(tags) == 1, f"expected exactly one data-whb banner tag, found {len(tags)}"
    assert "wh_banner.js" in tags[0], tags[0]
    assert html.index(tags[0]) < html.rindex("</body>"), "banner tag sits after </body>"


def test_rendered_letter_rail_anchors_are_unique_ids():
    """Each gl-letter-X anchor id must appear at most once across the whole
    page: it is a jump target for the A-Z rail, and a duplicate id both makes
    the page invalid HTML and strands every non-first term of that letter —
    the rail can only ever land on the FIRST element with a given id."""
    html = _render()
    ids = re.findall(r'id="(gl-letter-[A-Z])"', html)
    assert len(ids) == len(set(ids)), f"duplicate letter-anchor ids: {sorted(set(x for x in ids if ids.count(x) > 1))}"


def test_rendered_glance_text_passes_the_banned_vocabulary_grep():
    site_path = config.site_dir() / "glossary.html"
    html = site_path.read_text(encoding="utf-8")
    for match in re.finditer(r'<p class="gl-(?:answer|why)">(.*?)</p>', html, re.S):
        text = re.sub(r"<[^>]+>", "", match.group(1))
        for pattern in BANNED_GLANCE_PATTERNS:
            assert not pattern.search(text), text
        for token in re.findall(r"[A-Za-z0-9_]+", text):
            assert token not in BANNED_GLANCE_TOKENS, token


_LOCAL_ASSET_REF_RE = re.compile(r'\b(?:src|href)="([^"?#]+\.(?:css|js))(?:[?#][^"]*)?"')
_SCHEME_RE = re.compile(r"[a-zA-Z][\w+.-]*:")


def _copy_named_local_assets(page: Path, site: Path, out: Path) -> list[str]:
    """Copy every same-origin ``.css``/``.js`` the raw page names from the real
    ``site/`` into the tmp site root, so ``optimize_assets`` hashes the same
    bytes the render lane hashed. Read-only on ``site/``; a ref with no file
    behind it is skipped (the sweep then leaves that ref unstamped, exactly as
    the lane would)."""
    copied: list[str] = []
    for rel in sorted(set(_LOCAL_ASSET_REF_RE.findall(page.read_text(encoding="utf-8")))):
        if rel.startswith("//") or _SCHEME_RE.match(rel):
            continue
        src = site / rel
        if src.is_file():
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied.append(rel)
    return copied


def _finalize_like_render_lane(out: Path) -> None:
    """Apply the render lane's post-render sweeps to the tmp site root.

    Mirrors ``render_public`` in scripts/ci/public_render.sh, in its order:
    ``build_public_pages`` (already run) → ``inject_data_base`` →
    ``externalize_css`` → ``optimize_assets``. Each script's entry point takes a
    site dir, so the REAL functions run against ``out``; every write (the
    ``assets/css/<hash>.css`` files, the rewritten pages, the orphan prune)
    lands under ``out`` and nothing touches the real ``site/``. The lane's last
    step, ``check_template_site_sync --fix``, is not mirrored: it only re-copies
    plain-copy ``templates/<name>`` pairs (a non-``.j2`` direct child of
    templates/ that also ships as site/<name>), and glossary.html is a Jinja
    render, not a pair. Precedent: ``_finalize_like_render_lane`` in
    tests/test_macro_rates_curves_bonds_guard.py (T10), which replays the same
    CSS-externalize and asset-stamp sweeps at the text level for site/bonds.html.
    """
    from scripts import externalize_css, inject_data_base, optimize_assets
    inject_data_base.inject(out)
    externalize_css.externalize(out)
    optimize_assets.optimize(out)


def test_site_pair_matches_a_fresh_render_of_the_template(tmp_path):
    """The committed site/glossary.html is NOT a raw render of the template.

    The public-render lane (scripts/ci/public_render.sh) commits what its
    post-render sweeps leave behind: dashboard-bot commit d8c4cca1
    "render-public: public pages + asset stamps" (2026-09-12 17:10Z, four
    minutes after #6909 squashed this test in) lifted the page's inline
    ``<style>`` into ``assets/css/<hash>.css`` links and stamped theme.css /
    theme.js ``?v=<hash>``, and every later render does the same. Comparing a
    raw ``build_public_pages.build`` render against that page was red on main
    from d8c4cca1 on (first hit: #6958 trusted-executor-pack-3). So the fresh
    render is put through the lane's own sweeps (see
    ``_finalize_like_render_lane``) and the page's named local assets are copied
    beside it first, so the ``?v=`` stamps hash the bytes the lane hashed. The
    committed page stays exactly as the lane writes it — re-committing a raw
    render would flip back at the bot's next run. HTML comments are still
    stripped on both sides, as before, so a future generated-at comment cannot
    trip the pair.

    The ``?v=<8 hex>`` stamps are the lane's cache-busters, and each one is
    derived from the CURRENT bytes of the asset it names — site/theme.css,
    site/theme.js and site/product-nav-icons.css. Those files are not this
    page's contract: the committed page carries the stamps of the lane's LAST
    run, and the dashboard-bot restamps them on its next render-public run, so
    any theme.css change that lands in between would turn this test red for the
    whole fleet (theme.css changed five times on 2026-09-06..09 alone). The
    ``?v=`` query is therefore normalised away on BOTH sides before the compare
    (seat ruling on review F1). The ``assets/css/<hash>.css`` link NAME is kept
    as-is: that hash is of this page's own inline CSS, so a change there is a
    genuine drift signal (the same regex also drops the duplicate ``?v=`` query
    that link carries, but the hash lives in the filename and is still
    asserted).

    The ``data-whb`` banner tag is normalised away on both sides for the same
    lane-ownership reason the ``?v=`` stamp is: only daily.yml runs
    ``inject_wh_banner``, so the fresh render never carries it while the
    committed page must. Its PRESENCE on the committed page is pinned by
    ``test_committed_glossary_page_carries_the_alert_banner_script`` — without
    that pair, this test is blind to a regeneration that drops the banner from
    the live public page (review round 2, BLOCKER 1).
    """
    from scripts import build_public_pages
    out = tmp_path / "site"
    build_public_pages.build(out)
    page = out / "glossary.html"
    _copy_named_local_assets(page, config.site_dir(), out)
    _finalize_like_render_lane(out)
    fresh = page.read_text(encoding="utf-8")
    site_path = config.site_dir() / "glossary.html"
    on_disk = site_path.read_text(encoding="utf-8")
    fresh_body = re.sub(r"<!--.*?-->", "", fresh, flags=re.S)
    on_disk_body = re.sub(r"<!--.*?-->", "", on_disk, flags=re.S)
    fresh_body = re.sub(r"\?v=[0-9a-f]{8}", "", fresh_body)
    on_disk_body = re.sub(r"\?v=[0-9a-f]{8}", "", on_disk_body)
    fresh_body = _WHB_TAG_RE.sub("", fresh_body)
    on_disk_body = _WHB_TAG_RE.sub("", on_disk_body)
    assert fresh_body == on_disk_body


def test_help_directory_lists_the_glossary():
    entry = next((e for e in HELP_LINKS if e.id == "glossary"), None)
    assert entry is not None
    assert entry.category == "research"
    assert entry.href == "glossary.html"


def test_public_nav_research_panel_links_to_glossary():
    nav = (ROOT / "templates" / "_public_nav.html.j2").read_text(encoding="utf-8")
    assert 'href="{{ rel }}glossary.html"' in nav


def test_public_render_fast_lane_covers_the_glossary():
    workflow = (ROOT / ".github" / "workflows" / "public-render.yml").read_text(encoding="utf-8")
    assert '"lib/glossary.py"' in workflow
    assert '"templates/glossary.html.j2"' in workflow


def test_glossary_template_declares_both_theme_treatments():
    tpl = (ROOT / "templates" / "glossary.html.j2").read_text(encoding="utf-8")
    assert "DARK TREATMENT" in tpl
    assert "LIGHT TREATMENT" in tpl
    for selector in (".gl-domain", ".gl-row:hover", ".gl-rail", ".gl-letter:hover"):
        assert f'html[data-theme="light"] {selector}' in tpl
