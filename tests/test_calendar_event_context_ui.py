"""Execute the shipped context renderer, including hostile data and same-date joins."""
import json
from pathlib import Path
import subprocess

from jinja2 import Environment, FileSystemLoader
from engine.calendar_event_context import project_event

ROOT = Path(__file__).resolve().parents[1]


def context(day="2026-09-22", title="10-Year Note auction"):
    return project_event({"type": "AUCTION", "date": day, "label": title, "label_zh": "十年期国债拍卖"})


def js_assertions(rows, assertions):
    source = (ROOT / "templates/calendar_event_context.js").read_text()
    program = ("const assert = require('node:assert/strict');\n"
               "let payload = " + json.dumps(rows) + ";\n"
               "global.window = {}; global.document = {getElementById: () => ({textContent: JSON.stringify(payload)})};\n"
               + source + "\nconst api = window.MMXCalendarEventContext;\n" + assertions)
    result = subprocess.run(["node", "-e", program], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_every_event_on_date_has_context_without_any_model_payload():
    js_assertions([context(), context(title="20-Year Bond auction"), context("2026-09-23", "Other day")], """
const html = api.renderDate('2026-09-22');
assert(html.includes('10-Year Note auction'));
assert(html.includes('20-Year Bond auction'));
assert(!html.includes('Other day'));
assert(html.includes('Reading guide') && html.includes('阅读指南'));
assert(html.includes('Not supplied') && html.includes('未提供'));
assert(html.includes('<details') && html.includes('No release results') === false);
assert.equal(api.renderDate('2026-09-25'), '');
""")


def test_revision_changes_signature_and_repaints_facts():
    js_assertions([context()], """
const before = api.signature('2026-09-22');
payload[0].facts[1].value = '39000000000';
payload[0].facts[1].state = 'source_supplied';
assert.notEqual(api.signature('2026-09-22'), before);
assert(api.renderDate('2026-09-22').includes('39,000,000,000'));
""")


def test_untrusted_text_links_and_malformed_payload_fail_safely():
    row = context(title='<img src=x onerror=alert(1)>')
    row['source_url'] = 'javascript:alert(1)'
    row['facts'][0]['value'] = '<script>alert(1)</script>'
    js_assertions([row], """
const html = api.renderDate('2026-09-22');
assert(!html.includes('<img') && !html.includes('<script'));
assert(!html.includes('javascript:'));
assert(html.includes('&lt;img') && html.includes('&lt;script'));
payload = {}; assert.equal(api.renderDate('2026-09-22'), '');
payload = [null, 5, {event_date:'2026-09-22'}];
assert.doesNotThrow(() => api.renderDate('2026-09-22'));
""")


def test_production_fragment_escapes_json_and_renders_without_model_data():
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    html = env.get_template('_calendar_event_context.html.j2').render(
        macro_catalysts=[{'intelligence':context(title='</script><img src=x>')}, {'type':'legacy'}])
    assert 'calendar-event-context-data' in html
    assert '</script><img' not in html
    assert '\\u003c/script\\u003e' in html
    assert 'MMXCalendarEventContext' in html


def test_real_calendar_selector_composes_context_alongside_models():
    # The existing executable selector suite supplies race/idempotence coverage.
    # Execute its actual DOM driver with the added context API and stronger assertions.
    src = (ROOT / 'tests/test_release_radar_date_selection.py').read_text()
    prefix = src[:src.index('def test_release_radar_selection')]
    namespace = {'__file__': str(ROOT / 'tests/test_release_radar_date_selection.py')}
    exec(prefix, namespace)
    import ast
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_release_radar_selection'))
    assignment = next(n for n in fn.body if isinstance(n, ast.Assign))
    driver = eval(compile(ast.Expression(assignment.value), '<selector-driver>', 'eval'), namespace)
    driver = driver.replace('function assert(condition, message)', "window.MMXCalendarEventContext = {signature: () => 'v1', renderDate: () => '<article>CONTEXT</article>'};\nfunction assert(condition, message)")
    driver += "\nassert(bodyHTML.includes('CONTEXT'), 'context was not composed with model cards');\nselectInlineDate('2026-09-22', null, true);\nassert(bodyHTML.includes('CONTEXT'), 'no-forecast context disappeared');"
    result = subprocess.run(['node', '-e', driver], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_context_fragment_degrades_for_explicit_null_calendar():
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    html = env.get_template('_calendar_event_context.html.j2').render(macro_catalysts=None)
    assert 'calendar-event-context-data' in html


def test_official_terms_survive_full_production_template(monkeypatch):
    from datetime import date
    from engine import event_calendar
    from tests.test_release_radar_render import _base_vm, _env
    from bs4 import BeautifulSoup

    rows = json.loads((ROOT / 'tests/fixtures/treasury_auction_official_20260917.json').read_text())
    monkeypatch.setattr(event_calendar, '_fetch_upcoming_auctions', lambda _: rows)
    vm = _base_vm()
    vm['macro_catalysts'] = event_calendar._auction_events(date(2026, 9, 17), date(2026, 9, 30))
    html = _env().get_template('dashboard.html.j2').render(**vm, mode='macro')
    payload = json.loads(BeautifulSoup(html, 'html.parser').find(id='calendar-event-context-data').string)
    assert len(payload) == 4
    assert all(x['coverage'] == 'official_terms' for x in payload)
    assert any('discount margin' in x['summary']['en'] for x in payload)
    assert all(x['known_at'] is None for x in payload)


def test_event_dialog_heading_and_date_do_not_keep_dark_only_ink():
    css = (ROOT / 'templates/dashboard.html.j2').read_text()
    assert '#dlg-events .mx5-dlg-title,#dlg-events .rr-inline-date{color:var(--ink-1);}' in css


def test_browser_evidence_resolves_actual_font_and_theme_assets():
    """Font fallback is not faithful visual evidence of the published component."""
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = root / "research/event_intelligence/auction_context_v1/reproduce.py"
    tree = ast.parse(source.read_text())
    helper = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_proof_assets"]
    assert len(helper) == 1, "the proof server must bind its styles and actual font files"
    namespace = {"Path": Path}
    exec(compile(ast.Module(body=helper, type_ignores=[]), str(source), "exec"), namespace)
    assets = namespace["_proof_assets"](root)
    assert assets["/theme.css"] == root / "templates/theme.css"
    assert assets["/product-nav-icons.css"] == root / "templates/product-nav-icons.css"
    for weight in (400, 500, 600, 700, 800, 900):
        assert assets[f"/fonts/Inter-{weight}.woff2"] == root / f"site/fonts/Inter-{weight}.woff2"
    assert all(path.is_file() for path in assets.values())
