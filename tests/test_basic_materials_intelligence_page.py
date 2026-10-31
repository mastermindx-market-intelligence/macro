from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'templates'

def read(name):
    return (T/name).read_text(encoding='utf-8')

def test_template_uses_shared_shell_and_truthful_disconnected_state():
    html=read('basic_materials_intelligence.html.j2')
    assert '{% include "_site_nav.html.j2" %}' in html
    assert '<script src="theme.js" defer></script>' in html
    assert 'data-bm-reader-state="unbound"' in html
    assert 'Evidence service not connected' in html
    assert '证据服务尚未接入' in html
    assert 'theme:basic_materials' not in html
    assert 'ETF universe' not in html
    assert 'Research context only' in html

def test_shell_has_three_task_views_and_ten_noncanonical_families():
    html=read('basic_materials_intelligence.html.j2')
    for tab in ('understand','compare','evidence'):
        assert f'data-bm-tab="{tab}"' in html
    families=re.findall(r'data-bm-family="([^"]+)"',html)
    assert len(families)==10
    assert len(set(families))==10
    assert 'data-bm-family="all"' not in html

def test_four_journeys_are_questions_not_live_values():
    js=read('basic_materials_intelligence.js')
    for name in ('Nutrien','NOVONIX','Wheaton / Antamina','Weyerhaeuser'):
        assert name in js
    for forbidden in ('399','323','139','63','-31','12/14','0001193125-26-326124'):
        assert forbidden not in js
    assert 'fetch(' not in js
    assert 'XMLHttpRequest' not in js
    assert 'WebSocket' not in js

def test_client_preserves_accessible_tab_and_filter_semantics():
    js=read('basic_materials_intelligence.js')
    for required in (
        "aria-selected",
        "aria-pressed",
        "history.pushState",
        "popstate",
        "bm-announcement",
        "focus()",
    ):
        assert required in js

def test_css_has_mobile_targets_and_reduced_motion():
    css=read('basic_materials_intelligence.css')
    assert 'min-height:44px' in css.replace(' ','')
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert '@media (max-width: 780px)' in css

def test_builder_is_shell_only_and_copies_paired_assets():
    src=(ROOT/'scripts/build_basic_materials_intelligence_page.py').read_text(encoding='utf-8')
    assert 'basic_materials_intelligence.html.j2' in src
    assert 'basic_materials_intelligence.css' in src
    assert 'basic_materials_intelligence.js' in src
    for forbidden in ('requests.', 'httpx.', 'urllib.request', 'subprocess.', 'data/basic_materials'):
        assert forbidden not in src

def test_future_sector_entry_partial_is_not_a_theme_mount():
    part=read('_basic_materials_sector_deep_dive.html.j2')
    assert 'href="basic_materials_intelligence.html"' in part
    assert 'data-lane="sector-deep-dive"' in part
    assert 'theme:basic_materials' not in part
    assert 'canonical theme' not in part.lower()

def test_css_uses_only_shared_theme_tokens_it_claims():
    css=read('basic_materials_intelligence.css')
    for forbidden in ('var(--border)', 'var(--surface)', 'var(--accent)'):
        assert forbidden not in css
    for required in ('var(--line)', 'var(--panel)', 'var(--info)'):
        assert required in css

def test_journey_rerender_restores_focus_to_the_new_button():
    js=read('basic_materials_intelligence.js')
    assert "render();b.focus()" not in js
    assert "document.getElementById('bm-journey-'+selected)" in js
