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

    Known coupling, shared with T10: the ``?v=`` stamps are hashed from the
    CURRENT bytes of the copied assets (today theme.css and theme.js), while
    the committed page carries the stamp from the lane's last run. A PR that
    edits one of those assets without a re-render therefore fails here until
    the public-render lane re-stamps the page on main.
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
