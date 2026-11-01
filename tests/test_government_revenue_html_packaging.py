"""First-paint packaging keeps source comments, executable JS and all data."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from scripts import build_government_revenue as owner

ROOT = Path(__file__).resolve().parents[1]

def runtime(html):
    return next(b for b in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
                if '__hydrateGovernmentWorkspace' in b)

def executable(text):
    # Keep every newline (and therefore JS automatic-semicolon boundaries).
    text = re.sub(r'(?m)^(\s*)//[^\n]*$', lambda m: m.group(1) + '//', text)
    return '\n'.join(line.rstrip() for line in text.splitlines())

def test_source_and_generated_executable_runtime_are_identical():
    source = (ROOT/'templates/government-revenue-page.js.j2').read_text()
    rendered = Environment(loader=FileSystemLoader(str(ROOT/'templates')), autoescape=True).get_template(
        'government-revenue-page.js.j2').render()
    assert executable(re.sub(r'\{#[\s\S]*?#\}', '', source)) == executable(rendered)
    if shutil.which('node'):
        for js in (source, rendered):
            subprocess.run(['node','--check'], input=js, text=True, capture_output=True, check=True)

def test_actual_projection_preserves_full_canonical_twins_and_projected_data(tmp_path):
    (tmp_path/'templates').symlink_to(ROOT/'templates', target_is_directory=True)
    payload = {'companies':[], 'as_of':'2026-10-13T08:55:00Z', 'known_at':'2026-10-13T08:50:00Z',
               'source_note':'Unmodified bilingual source context / 原始来源背景'}
    canonical = json.dumps(payload, ensure_ascii=False)
    html, latest = owner._write_site_projection(tmp_path, payload, latest_raw=canonical, workspace_raw='{"untouched":true}')
    assert latest.read_text() == canonical
    assert (tmp_path/'site/government-revenue-data/workspace.json').read_text() == '{"untouched":true}'
    embedded = re.search(r'<script id="gov-data" type="application/json">(.*?)</script>', html.read_text(), re.S).group(1)
    assert json.loads(embedded) == owner._display_payload(payload)
    assert owner.RAW_HTML_BUDGET_BYTES == 311296
    assert html.stat().st_size <= owner.RAW_HTML_BUDGET_BYTES

    controller=(tmp_path/'site/government-revenue-page.js').read_text()
    assert '__hydrateGovernmentWorkspace' in controller
    assert '__hydrateGovernmentWorkspace' not in html.read_text()


def test_critical_css_preserves_canonical_components_order_and_link_identity():
    from rcssmin import cssmin
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    names = ("theme.css", "government-revenue-sbir.css", "government-revenue-investor.css",
             "government-revenue-theme-context.css", "government-revenue-parity.css")
    icon = (ROOT / "templates/product-nav-icons.css").read_text()
    parts = [(ROOT / "templates" / name).read_text() for name in names]
    parts[0] = parts[0].replace('@import url("product-nav-icons.css?v=093ad1ea");', icon, 1)
    assert owner._government_revenue_critical_css(env) == cssmin("\n".join(parts), keep_bang_comments=True)
    source = (ROOT / "templates/government_revenue.html.j2").read_text()
    assert 'href="government-revenue-critical-theme.css"' in source
    assert '<script data-sync src="{{ asset_url(\'theme.js\')' in source
    assert '{% include "_site_nav.html.j2" %}' in source
    assert 'link[href*="theme.css"]' in (ROOT / "templates/theme.js").read_text()


def test_minified_critical_css_keeps_strings_calculations_urls_and_license_comments():
    from jinja2 import DictLoader
    env = Environment(loader=DictLoader({
        'theme.css': '@import url("product-nav-icons.css?v=093ad1ea");'
                     '/*! retained license */ /* removable explanation */'
                     ':root { --label: "/* retained string */"; --gap: calc(100% - 2px); }'
                     '.x { content: "a ; b"; background: url("data:text/plain;utf8,/* data */"); }',
        'product-nav-icons.css': '.icon { display: inline-block; }',
        'government-revenue-sbir.css': '',
        'government-revenue-investor.css': '',
        'government-revenue-theme-context.css': '',
        'government-revenue-parity.css': '',
    }))
    emitted = owner._government_revenue_critical_css(env)
    assert 'removable explanation' not in emitted
    assert '/*! retained license */' in emitted
    assert '"/* retained string */"' in emitted
    assert 'calc(100% - 2px)' in emitted
    assert '"a ; b"' in emitted
    assert '"data:text/plain;utf8,/* data */"' in emitted


def test_critical_css_refuses_missing_changed_or_unresolved_dependencies(tmp_path):
    from jinja2 import DictLoader, TemplateNotFound
    env = Environment(loader=DictLoader({'theme.css':'@import url("product-nav-icons.css?v=093ad1ea");'}))
    with pytest.raises(TemplateNotFound):
        owner._government_revenue_critical_css(env)
    env = Environment(loader=DictLoader({'theme.css':'@import url("unexpected.css");','product-nav-icons.css':'i{}'}))
    with pytest.raises(ValueError, match='import changed'):
        owner._government_revenue_critical_css(env)
    (tmp_path / 'theme.css').write_text('@import url("product-nav-icons.css?v=093ad1ea"); x{background:url("missing.png")}')
    (tmp_path / 'product-nav-icons.css').write_text('i{}')
    env = Environment(loader=FileSystemLoader(str(tmp_path)))
    with pytest.raises(ValueError, match='unresolved canonical CSS dependency'):
        owner._government_revenue_critical_css(env)


def test_existing_sdk_executes_before_shared_auth_with_one_publisher_cache_key(tmp_path):
    from scripts.optimize_assets import make_optimizer
    (tmp_path / "templates").symlink_to(ROOT / "templates", target_is_directory=True)
    html, _ = owner._write_site_projection(tmp_path, {'companies':[]}, latest_raw='{}', workspace_raw='{}')
    sdk = ROOT / "templates/supabase.js"
    shutil.copyfile(sdk, tmp_path / "site/supabase.js")
    text = make_optimizer(tmp_path / "site")(html.read_text(), tmp_path / "site")
    hint = re.search(r'<link[^>]+href="(supabase.js[^"]*)"[^>]+rel="preload"|<link[^>]+rel="preload"[^>]+href="(supabase.js[^"]*)"', text)
    assert hint is not None
    target = next(x for x in hint.groups() if x)
    loading = re.search(r'<script data-sync src="(supabase.js[^"]*)"', text)
    assert loading is not None and loading.group(1) == target
    assert text.index(loading.group(0)) < text.index('<script data-sync src="theme.js')


@pytest.mark.parametrize('optimized', (False, True))
@pytest.mark.parametrize('name', ('theme.js', 'supabase.js', 'government-revenue-investor.js',
                                  'government-revenue-investor-start.js', 'navigation-refresh.css'))
def test_critical_hint_and_loading_urls_match_in_each_publisher_path(tmp_path, optimized, name):
    from html.parser import HTMLParser
    from urllib.parse import urlsplit
    from scripts.optimize_assets import make_optimizer

    (tmp_path / 'templates').symlink_to(ROOT / 'templates', target_is_directory=True)
    html, _ = owner._write_site_projection(tmp_path, {'companies': []}, latest_raw='{}', workspace_raw='{}')
    for asset in ('supabase.js', 'navigation-refresh.css'):
        shutil.copyfile(ROOT / 'templates' / asset, tmp_path / 'site' / asset)
    text = html.read_text()
    if optimized:
        text = make_optimizer(tmp_path / 'site')(text, tmp_path / 'site')
    hints, loads = [], []

    class Assets(HTMLParser):
        def handle_starttag(self, tag, pairs):
            attrs = dict(pairs)
            url = attrs.get('src') if tag == 'script' else attrs.get('href') if tag == 'link' else None
            if not url or urlsplit(url).path != name:
                return
            if tag == 'link' and attrs.get('rel') == 'preload':
                hints.append(url)
            elif tag == 'script' or attrs.get('rel') == 'stylesheet':
                loads.append(url)

    Assets().feed(text)
    assert len(hints) == len(loads) == 1
    assert hints == loads, 'normal and optimized publication must each reuse their preload cache key'


def _script_tags(text):
    from html.parser import HTMLParser
    rows=[]
    class Parser(HTMLParser):
        def handle_starttag(self,tag,attrs):
            if tag=='script' and dict(attrs).get('src'):rows.append(dict(attrs))
    Parser().feed(text)
    return rows

def test_gov_primary_auth_and_finance_are_not_parser_blocked_by_nav_enhancements():
    env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=True)
    html=env.get_template('government_revenue.html.j2').render(payload_json='{}')
    rows=_script_tags(html)
    names=('logo_config.js','stock-logos.js','live_config.js','live.js')
    enhancements=[r for r in rows if r['src'] in names]
    assert [r['src'] for r in enhancements]==list(names)
    assert all('defer' in r and r.get('fetchpriority')=='low' and 'async' not in r for r in enhancements)
    primary=[r for r in rows if r['src'] in ('supabase.js','theme.js','government-revenue-investor.js','government-revenue-investor-start.js')]
    assert [r['src'] for r in primary]==['supabase.js','theme.js','government-revenue-investor.js','government-revenue-investor-start.js']
    assert all('data-sync' in r and 'async' not in r and 'defer' not in r for r in primary)
    baseline=_script_tags(env.get_template('_site_nav.html.j2').render(t=lambda en,zh='':en))
    assert all('defer' not in r and 'fetchpriority' not in r for r in baseline if r['src'] in names)
