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


# ABX3: hostile/malformed input must remain safe even in non-autoescaping hosts.
def _abx3_body(payload):
    return str(_env().get_template('_aibrief_body.html.j2').module.aibrief_body(payload, 'macro', True))


def test_abx3_escapes_all_narrative_surfaces():
    attack = '<img src=x onerror=alert(1)>'
    html = _abx3_body({'summary': attack, 'regime_read': attack,
        'tldr': ['Driver: ' + attack, 'What to do: Watch — don\'t chase'],
        'conflicts': [attack], 'transmission': [attack], 'watch_items': [attack],
        'rotation_check': attack, 'degraded_reason': attack,
        'zh': {'summary': attack, 'watch_items': [attack]}})
    assert '<img' not in html
    assert '&lt;img' in html


def test_abx3_malformed_rows_do_not_break_shared_body():
    for payload in ([], 'broken', 42, {'summary': 'Usable', 'key_facts': [None, 'broken'],
        'tldr': [None, {}, 'Driver: real'], 'zh': {'tldr': [None]},
        'watch_items': 7, 'conflicts': 'not a list', 'forward_watch': [42]}):
        html = _abx3_body(payload)
        assert 'not a signal source' in html
        assert '>None<' not in html


def test_abx3_unknown_confidence_is_not_low():
    html = _abx3_body({'summary': 'Usable', 'confidence': 'unexpected'})
    assert 'Confidence: Low' not in html
    assert 'Not assessed' in html


def test_abx3_last_tldr_is_not_automatically_a_stance():
    html = _abx3_body({'tldr': ['Driver: Real', 'Watch the next release']})
    assert 'class="aib2-stance ' not in html
    assert 'Watch the next release' in html


def test_abx3_cadence_does_not_claim_a_successful_update():
    html = _abx3_body({'summary': 'Old', 'state_asof': '2026-10-16',
        'generated_at': '2026-10-18T06:50:00+00:00', 'refresh_days': 1})
    assert 'Updated daily' not in html
    assert 'Scheduled daily' in html
    assert '2026-10-16' in html and '2026-10-18' in html


def test_abx3_no_decorative_container_edges():
    css = (config.ROOT / 'templates/_aibrief_css.j2').read_text()
    assert 'border-left:' not in css
    assert 'linear-gradient' not in css
    assert 'var(--font-ui' in css


def test_abx3_null_translation_falls_back_per_item():
    html = _abx3_body({'watch_items': ['Credit: Watch spreads'], 'zh': {'watch_items': [None]}})
    assert html.count('Watch spreads') == 2


def test_abx3_watch_conditions_precede_detail():
    html = _abx3_body({'summary': 'Read', 'watch_items': ['Trigger: meaning'], 'regime_read': 'Detail'})
    assert html.index('Trigger') < html.index('Detail')


def test_abx3_full_page_malformed_lens_is_safe():
    html = _render(master_brief=['broken'], china_brief=42, btc_brief='broken')
    assert 'AI Daily Brief' in html
    assert 'has not generated yet' in html


def test_abx3_tab_aria_contract():
    html = _render()
    for lens in ('macro', 'china', 'btc'):
        assert 'aria-controls="brief-' + lens + '"' in html
        assert 'id="brief-' + lens + '"' in html
    assert 'role="tabpanel"' in html


def test_abx3_main_brief_precedes_supporting_calendar():
    html = _render(master_brief={'summary': 'PRIORITY_THESIS'})
    assert html.index('PRIORITY_THESIS') < html.index('Morning Orientation', html.index('<body>'))


def test_abx3_cortex_degraded_does_not_invent_rate_limiting(tmp_path):
    from scripts.build_aibrief import _gather_context_strip
    folder = tmp_path / 'neuralweb'
    folder.mkdir()
    (folder / 'market_plane.json').write_text(json.dumps({'cortex': {'status': 'degraded'}, 'verdict': {}}))
    out = _gather_context_strip(tmp_path)
    assert 'rate-limit' not in out['cortex_en'].lower()


def test_abx3_missing_contradiction_count_never_means_agreement(tmp_path):
    from scripts.build_aibrief import _gather_context_strip
    folder = tmp_path / 'neuralweb'
    folder.mkdir()
    (folder / 'world_state.json').write_text(json.dumps({'contradictions': {}}))
    out = _gather_context_strip(tmp_path)
    assert 'same way' not in (out['contradiction_line_en'] or '')


def test_abx3_freshness_clock_rejects_invalid_and_future_dates():
    import shutil
    import subprocess
    import pytest
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the real client-clock contract')
    result = subprocess.run([node, '-e', '''
const assert=require('node:assert/strict');
const {freshness}=require('./templates/aibrief.js');
const now=Date.parse('2026-11-02T12:00:00Z');
assert.equal(freshness('2026-10-16','2026-10-18T06:00:00Z',1,now).state,'old');
for(const [s,g] of [['2026-02-30','2026-11-02T06:00:00Z'],['2027-01-01','2027-01-01T06:00:00Z'],['',''],['2026-11-02','2026-11-02T06:00:00']]) {
 assert.equal(freshness(s,g,1,now).state,'unknown');
}
assert.equal(freshness('2026-11-02','2026-11-02T06:00:00Z',1,now).state,'dated');
'''], cwd=config.ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_abx3_stance_requires_a_whole_approved_verb():
    html = _abx3_body({'tldr': ['Driver: Real', 'What to do: Actuary says wait']})
    assert 'class="aib2-stance ' not in html
