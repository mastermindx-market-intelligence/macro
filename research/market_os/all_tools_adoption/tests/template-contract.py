"""Server-rendered shared-header boundaries; no browser/layout certification."""
import hashlib
import os
import re
import unittest
from pathlib import Path
from jinja2 import Environment, DictLoader
from html.parser import HTMLParser

class Tags(HTMLParser):
    def __init__(self, content):
        super().__init__(); self.rows=[]; self.feed(content)
    def handle_starttag(self, tag, attrs):
        self.rows.append((tag,dict(attrs)))
    def values(self, tag, attribute):
        return [a[attribute] for t,a in self.rows if t==tag and attribute in a]
    def find(self, tag, **attrs):
        return [a for t,a in self.rows if t==tag and all(k in a and (v is None or a[k]==v) for k,v in attrs.items())]

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source' / '_site_nav.html.j2'
NAV_FIXTURE = '<div class="nav-links"><a class="nav-brand" href="{{ NP }}start.html">Home</a><div class="nav-dd"><a class="nav-link" href="{{ NP }}macro.html">US</a><div class="nav-dd-menu"><a href="{{ NP }}macro.html#growth">Market dashboard</a></div></div></div>'

def render(original=False, **kw):
    header = SOURCE.read_text() + ('' if original else '{% include "_all_tools_menu.html.j2" %}\n')
    templates = {'header': header, '_navlinks.html.j2': NAV_FIXTURE,
                 '_all_tools_menu.html.j2': (ROOT/'src/_all_tools_menu.html.j2').read_text()}
    return Environment(loader=DictLoader(templates), autoescape=False).get_template('header').render(t=lambda en, zh='': en, **kw)

class SharedHook(unittest.TestCase):
    def test_original_bytes_match_frozen_github_blob(self):
        raw=SOURCE.read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'9848b9366d43553f9d69997ecdb0a07e15e4ad2b')
    def test_default_keeps_original_render(self):
        self.assertEqual(render().strip(),render(original=True).strip())
    def test_false_flag_does_not_load_assets_or_controls(self):
        out=render(all_tools_enabled=False)
        self.assertNotIn('all_tools.js',out);self.assertNotIn('<dialog',out)
    def test_non_boolean_flags_do_not_accidentally_opt_in(self):
        for flag in ('false','true','1',1,{},[]):self.assertNotIn('<dialog',render(all_tools_enabled=flag))
    def test_explicit_pilot_has_one_dialog_and_one_canonical_header(self):
        out=Tags(render(all_tools_enabled=True))
        self.assertEqual(len(out.find('nav',**{'class':'site-nav'})),1)
        self.assertEqual(len(out.find('dialog')),1)
        self.assertEqual(len(out.find('div',**{'class':'nav-ctrls'})),1)
    def test_shell_does_not_author_destination_copies(self):
        helper=(ROOT/'src/_all_tools_menu.html.j2').read_text()
        self.assertNotIn('<a ',helper);self.assertNotIn('macro.html',helper);self.assertNotIn('reports.html',helper)
    def test_source_links_survive_enhancement_markup(self):
        a=Tags(render(original=True))
        b=Tags(render(all_tools_enabled=True))
        self.assertEqual(a.values('a','href'),b.values('a','href'))
    def test_prefix_is_preserved_for_component_assets_and_native_links(self):
        out=Tags(render(all_tools_enabled=True,nav_prefix='../'))
        self.assertIn('../all_tools.js?v=1',out.values('script','src'))
        self.assertIn('../all_tools.css?v=1',out.values('link','href'))
        self.assertIn('../macro.html#growth',out.values('a','href'))
    def test_js_failure_leaves_trigger_hidden_and_source_available(self):
        out=Tags(render(all_tools_enabled=True))
        self.assertEqual(len(out.find('button',**{'data-tools-open':None,'hidden':None})),1)
        self.assertGreater(len(out.values('a','href')),0)
    def test_not_an_aria_menu_requiring_different_keyboard_contract(self):
        out=render(all_tools_enabled=True);self.assertNotIn('role="menu"',out)
    def test_labels_and_dialog_names_resolve_unique_ids(self):
        tree=Tags(render(all_tools_enabled=True))
        ids=[a['id'] for _,a in tree.rows if 'id' in a];self.assertEqual(len(ids),len(set(ids)))
        refs=[a[key] for _,a in tree.rows for key in ('for','aria-controls','aria-labelledby') if key in a]
        self.assertTrue(all(v in ids for v in refs))
    def test_stock_search_and_tool_search_remain_distinct(self):
        tree=Tags(render(all_tools_enabled=True))
        self.assertEqual(len(tree.find('input',**{'aria-label':'Search stocks'})),1)
        self.assertEqual(len(tree.find('input',**{'data-tools-query':None})),1)
        self.assertIn('not a ticker',render(all_tools_enabled=True))
    def test_source_context_return_links_survive(self):
        out=render(all_tools_enabled=True,nav_context_links=[{'href':'../baskets.html','en':'All themes','zh':'全部主题'}])
        self.assertIn('href="../baskets.html"',out);self.assertIn('All themes',out)
    def test_markup_has_no_storage_or_inline_script_body(self):
        out=render(all_tools_enabled=True)
        self.assertNotIn('localStorage',out);self.assertNotIn('sessionStorage',out)
        self.assertNotRegex(out,r'<script[^>]*>\s*[^<\s]')
    def test_style_uses_existing_tokens_not_another_palette(self):
        css=(ROOT/'src/all-tools.css').read_text()
        self.assertNotRegex(css,r'#[0-9a-fA-F]{3,8}\b');self.assertNotIn(':root {',css)
        self.assertIn('var(--nr-surface-solid)',css);self.assertIn('var(--font-ui)',css)
    def test_styles_name_light_material_not_just_color_swap(self):
        css=(ROOT/'src/all-tools.css').read_text()
        self.assertIn('html[data-theme="light"] .mmx-tools-aside',css)
        self.assertIn('html[data-theme="light"] .mmx-tools-glyph svg',css)
    def test_responsive_reduced_motion_and_forced_colors_present(self):
        css=(ROOT/'src/all-tools.css').read_text()
        for token in ('max-width:600px','max-height:600px','100dvh','safe-area-inset-bottom','prefers-reduced-motion','forced-colors:active'):self.assertIn(token,css)
    def test_hidden_and_closed_controls_do_not_become_visible_by_css(self):
        css=(ROOT/'src/all-tools.css').read_text()
        self.assertIn('[data-tools-open][hidden] { display: none !important; }',css)
        self.assertIn('.mmx-tools:not([open]) { display: none; }',css)
    def test_no_runtime_style_injection_or_remote_requests(self):
        js=(ROOT/'src/all-tools.js').read_text()
        for token in ('createElement(\'style\')','fetch(','XMLHttpRequest','localStorage','sessionStorage','setInterval('):self.assertNotIn(token,js)
    def test_scope_retains_three_pilot_paths_without_rewriting_destinations(self):
        js=(ROOT/'src/all-tools.js').read_text()
        self.assertIn("['/macro.html', '/sector_central.html', '/reports.html']",js)
        self.assertNotIn('location.href =',js);self.assertNotIn('pushState(',js)

if __name__=='__main__':unittest.main(verbosity=2)
