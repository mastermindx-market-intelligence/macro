"""Consolidated AI Daily Brief page (aibrief.html) render + nav-cleanup regression.

The old deterministic daily brief (scripts/daily_brief.py -> brief.html, plus the
china/hk variants) was retired and replaced by ONE static page that surfaces the
three EXISTING AI briefs written by engine/master_brain.py
(master_brief.json / china_brief.json / btc_brief.json) as toggle tabs.

ABX v2 (2026-07-19): the three lens brief BODIES are now SERVER-rendered by the
shared macro templates/_aibrief_body.html.j2 (build_aibrief.py loads the JSONs into
master_brief / china_brief / btc_brief). templates/aibrief.js was slimmed to the
overnight-cortex panel only. These tests render the REAL template (same Jinja env
as scripts/build_aibrief) and guard, at the source level, that no template ever
re-links the deleted brief pages.
"""
from __future__ import annotations

import json

import pytest
import jinja2

from engine import i18n
from lib import config


def _env() -> jinja2.Environment:
    """Mirror scripts/build_aibrief.main()'s template environment."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(config.ROOT / "templates"))
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def _render(**briefs) -> str:
    """Render aibrief.html.j2 with the server-side panels absent (fail-open) and any
    passed lens briefs. Absent briefs render the honest 'not generated yet' note."""
    panels = {
        "ctx_strip": {"absent": True},
        "fwd_panel": {"absent": True, "events": [], "rebal_note_en": None, "rebal_note_zh": None},
        "record_panel": {"absent": True},
    }
    return _env().get_template("aibrief.html.j2").render(
        as_of="2026-06-14 12:00 UTC", **panels, **briefs
    )


def _committed_brief(name: str) -> dict:
    return json.loads((config.ROOT / "site" / name).read_text())


def test_three_lens_panels_present():
    """One .ai-brief panel per lens (server-rendered — no client fetch stubs)."""
    html = _render()
    assert html.count("ai-brief") >= 3
    # the client-fetch attributes are GONE (bodies are server-rendered now)
    assert "data-brief-src" not in html
    assert "data-brief-body" not in html


def test_committed_briefs_render_server_side():
    """The committed (v1-shaped) briefs render into the page via the shared macro —
    the v2 body must fail open on v1 payloads (no tldr → summary lead, no crash)."""
    html = _render(
        master_brief=_committed_brief("master_brief.json"),
        china_brief=_committed_brief("china_brief.json"),
        btc_brief=_committed_brief("btc_brief.json"),
    )
    # server-rendered macro body present (namespace .aib2-*), badge is house law
    assert '"aib2"' in html or 'class="aib2"' in html
    assert "not a signal source" in html
    # v1 payloads have no tldr → the summary lead-card fallback renders, no stance pill
    assert "aib2-lead" in html


def test_absent_brief_shows_honest_note():
    """No brief for a lens → an honest 'not generated yet' note, never a stray body."""
    html = _render()  # all briefs absent
    assert "has not generated yet" in html
    assert '"aib2"' not in html  # no empty body frame when all absent


def test_toggle_tabs_present():
    """Three market toggle buttons, one per lens."""
    html = _render()
    assert 'data-lens="macro"' in html
    assert 'data-lens="china"' in html
    assert 'data-lens="btc"' in html
    assert "Macro" in html and "China" in html and "Bitcoin" in html
    # exactly one panel is active by default (class-driven visibility)
    assert html.count("brief-tab active") == 1


def test_required_assets_loaded():
    """The page needs theme.css/.js + aibrief.js (cortex panel is still client-side)."""
    html = _render()
    assert 'href="theme.css"' in html
    assert 'src="theme.js"' in html
    assert 'src="aibrief.js"' in html


def test_per_lens_cadence_copy_no_blanket_daily_claim():
    """SPEC §7: the page no longer claims a blanket 'each day' refresh — BTC is every
    three days. The intro must state the split cadence honestly."""
    html = _render()
    assert "every three days" in html  # BTC honesty
    # the retired blanket claim must be gone
    assert "Regenerated automatically each day after the close" not in html


def test_static_nav_button_present():
    """The renamed 'AI Daily Brief' entry lives in the nav-ctrls cluster."""
    html = _render()
    assert "AI Daily Brief" in html
    assert 'class="ai-brief-link' in html
    assert 'class="nav-ctrls"' in html


def test_page_does_not_link_old_brief_pages():
    """The new page must not reference the retired brief HTML files. NOTE: the exact
    href= form matters — 'aibrief.html' contains the substring 'brief.html'."""
    html = _render()
    assert 'href="brief.html"' not in html
    assert 'href="china_brief.html"' not in html
    assert 'href="hk_brief.html"' not in html
    # The header's external entry is Terminal. The old "Mastermind" nav pill was
    # removed 2026-08-01 — theme.js injects mm_brain.js sitewide, which mounts its
    # own bottom-right launcher, so the pill was a duplicate entry point.
    #
    # Scoped to `.nav-ctrls` since 2026-08-07: the guard was written when NO Bot
    # link existed anywhere, so a whole-page substring read as "the header has no
    # Bot pill". The Bot now has a legitimate Research mega-menu card, and the
    # header contract is what this line always meant. theme.js:1492 strips any
    # `.nav-ctrls a[href*="bot.mastermind-x.com"]` at runtime; the SOURCE must not
    # lean on that, so the control cluster ships without one.
    ctrls = html[html.find('<div class="nav-ctrls">'):]
    ctrls = ctrls[:ctrls.find("</nav>")]
    assert ctrls, "the shared header lost its .nav-ctrls control cluster"
    assert 'href="https://app.mastermind-x.com"' in ctrls
    assert "bot.mastermind-x.com" not in ctrls


def test_no_template_links_deleted_brief_pages():
    """Source-level guard across EVERY template: the deterministic brief pages are
    gone, so nothing may link brief.html / china_brief.html / hk_brief.html (in any
    relative form). Locks in the nav cleanup against future drift."""
    bad = ('href="brief.html"', 'href="../brief.html"',
           'href="china_brief.html"', 'href="../china_brief.html"',
           'href="hk_brief.html"', 'href="../hk_brief.html"')
    offenders = []
    for path in sorted((config.ROOT / "templates").glob("*.html.j2")):
        src = path.read_text()
        for needle in bad:
            if needle in src:
                offenders.append(f"{path.name}: {needle}")
    assert not offenders, "templates still link retired brief pages: " + "; ".join(offenders)


# Publication must prove modal content, not just a date or a render watermark.
def _publication_fixture(root):
    from pathlib import Path

    payload = {"lens": "china", "state_asof": "2026-11-03",
               "summary": "Growth & demand have cooled.", "regime_read": "Liquidity is tight.",
               "confidence": "medium", "conflicts": ["Credit: demand remains weak"],
               "watch_items": ["Policy: watch the next release"],
               "zh": {"summary": "增长与需求降温。", "regime_read": "流动性收紧。"}}
    (root / "templates").mkdir()
    (root / "site").mkdir()
    template = (Path(config.ROOT) / "templates/_aibrief_body.html.j2").read_text()
    (root / "templates/_aibrief_body.html.j2").write_text(template)
    _publication_pages(root, payload)
    (root / "site/china_brief.json").write_text(json.dumps(payload))
    return payload


def _publication_pages(root, payload):
    for region, prefix in (("china", "cnx"), ("hk", "hkx")):
        source = (
            '{% import "_aibrief_body.html.j2" as aib %}'
            '<section id="' + prefix + '-dlg-aibrief">'
            '{% call aib.aibrief_body(brief, "china", show_catalysts=False) %}'
            '<div class="' + prefix + '-receipt">Caller-owned receipt <a href="aibrief.html">link</a></div>'
            '{% endcall %}</section>'
        )
        (root / ("site/" + region + ".html")).write_text(_env().from_string(source).render(brief=payload))


def test_brief_publication_compares_bilingual_component_with_footer_variations(tmp_path):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    china = tmp_path / "site/china.html"
    html = china.read_text().replace('class="aib2"', 'class="aib2 css-generated"')
    html = html.replace("Growth & demand", "Growth &amp; demand")
    html = html.replace("Caller-owned receipt", "A different nightly footer")
    china.write_text(html)
    assert pub.check(tmp_path, "china+hk") == ["china", "hk"]


@pytest.mark.parametrize("same_date", [True, False])
def test_brief_publication_refuses_old_content_even_with_a_new_date(tmp_path, same_date):
    from scripts import check_aibrief_publication as pub

    payload = _publication_fixture(tmp_path)
    payload["summary"] = "The latest narrative is materially different."
    payload["zh"]["summary"] = "最新解读已经变化。"
    if not same_date:
        payload["state_asof"] = "2026-11-04"
        for region in ("china", "hk"):
            page = tmp_path / ("site/" + region + ".html")
            page.write_text(page.read_text().replace("2026-11-03", "2026-11-04"))
    (tmp_path / "site/china_brief.json").write_text(json.dumps(payload))
    with pytest.raises(pub.PublicationError, match="does not match"):
        pub.check(tmp_path, "china+hk")


@pytest.mark.parametrize("mutation", ["wrong_lens", "missing", "old_chinese"])
def test_brief_publication_refuses_incomplete_modal_adoption(tmp_path, mutation):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    page = tmp_path / "site/hk.html"
    html = page.read_text()
    if mutation == "wrong_lens":
        html = html.replace('data-lens="china"', 'data-lens="macro"')
    elif mutation == "missing":
        html = "<div>Previous page without its brief</div>"
    else:
        html = html.replace("增长与需求降温。", "旧的中文解读。")
    page.write_text(html)
    assert pub.check(tmp_path, "china") == ["china"]
    with pytest.raises(pub.PublicationError):
        pub.check(tmp_path, "all")


def test_brief_publication_checks_commit_after_replay_not_only_worktree(tmp_path):
    import subprocess
    from scripts import check_aibrief_publication as pub

    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    payload = _publication_fixture(tmp_path)
    git("init", "-q", "-b", "main")
    git("config", "user.name", "brief-test")
    git("config", "user.email", "brief-test@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("add", ".")
    git("commit", "-qm", "first complete brief")
    assert pub.check(tmp_path, "all", "HEAD") == ["china", "hk"]
    payload["summary"] = "A newer accepted brief landed during publication."
    (tmp_path / "site/china_brief.json").write_text(json.dumps(payload))
    git("add", "site/china_brief.json")
    git("commit", "-qm", "replayed candidate has a new input and old pages")
    _publication_pages(tmp_path, payload)  # correct worktree must not certify stale HEAD
    assert pub.check(tmp_path, "all") == ["china", "hk"]
    with pytest.raises(pub.PublicationError, match="does not match"):
        pub.check(tmp_path, "all", "HEAD")


def test_brief_publication_is_wired_to_both_exact_push_candidates():
    from pathlib import Path
    import yaml

    root = Path(config.ROOT)
    workflow = yaml.safe_load((root / ".github/workflows/render.yml").read_text())
    steps = workflow["jobs"]["render"]["steps"]
    publisher = next(s["run"] for s in steps if s.get("name", "").startswith("commit rendered site"))
    replay = 'scripts.check_aibrief_publication --scope "${{ steps.pick.outputs.scope }}" --candidate-ref "$PUBLISH_COMMIT"'
    committed = 'scripts.check_aibrief_publication --scope "${{ steps.pick.outputs.scope }}" --candidate-ref HEAD'
    assert publisher.index(replay) < publisher.index('if push_do origin "$PUBLISH_REF:refs/heads/main"')
    assert publisher.index(committed) < publisher.index("if push_do;")
    guard = next(s["run"] for s in steps if s.get("name") == "guard — finalized site has no dead references")
    assert "scripts.check_aibrief_publication" in guard

@pytest.mark.parametrize("region,prefix", [("china", "cnx"), ("hk", "hkx")])
@pytest.mark.parametrize("duplicate_first", [True, False])
def test_brief_publication_refuses_duplicate_target_dialogs(tmp_path, region, prefix, duplicate_first):
    from scripts import check_aibrief_publication as pub

    _publication_fixture(tmp_path)
    page = tmp_path / ("site/" + region + ".html")
    correct = page.read_text()
    old = '<section id="' + prefix + '-dlg-aibrief">Old modal without the brief</section>'
    page.write_text(old + correct if duplicate_first else correct + old)
    with pytest.raises(pub.PublicationError, match="exactly one target"):
        pub.check(tmp_path, region)
