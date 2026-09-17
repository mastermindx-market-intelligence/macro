"""Execute the shipped live renderer's copy selector, not a parallel JS model."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from lib.risk_presentation import market_read

ROOT = Path(__file__).resolve().parents[1]


def _read(display):
    if not shutil.which('node'):
        pytest.skip('node unavailable; live presentation proof not obtained')
    source = (ROOT / 'templates/risk_state_live.js').read_text()
    source = source[:source.index('  if (document.readyState')]
    source += '\nwindow.__read = typeof presentationFor === "function" ? presentationFor : null;})();'
    code = "const vm=require('vm');const c={window:{},document:{}};"
    code += 'vm.runInNewContext(' + json.dumps(source) + ',c);'
    code += 'console.log(JSON.stringify(c.window.__read ? c.window.__read(' + json.dumps(display) + ') : null));'
    proc = subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True)
    result = json.loads(proc.stdout)
    assert result is not None, 'live patcher has no shared-presentation consumer'
    return result


def test_live_renderer_consumes_qualified_server_read():
    p = market_read({'verdict': 'RISK_ON', 'score': 61, 'components': [
        {'key': 'breadth', 'score': 14, 'tone': 'bad'}]})
    result = _read({'verdict': 'RISK_ON', 'presentation': p})
    assert result['label_en'] == 'Uneven support'
    assert 'line up' not in result['headline_en']


def test_legacy_feed_cannot_restore_an_unconditional_all_clear():
    result = _read({'verdict': 'RISK_ON', 'score': 61})
    assert result['label_en'] == 'Risk-on composite'
    assert 'line up' not in result['headline_en']
    assert 'Trend-following supported' not in result['subline_en']


def test_presentation_for_another_verdict_cannot_soften_risk_off():
    p = market_read({'verdict': 'RISK_ON', 'score': 61})
    result = _read({'verdict': 'RISK_OFF', 'presentation': p})
    assert result['label_en'] == 'Risk-off'


@pytest.mark.parametrize('bad', [None, [], {}, {'schema': 'market_read.presentation.v1',
    'measured_verdict': 'RISK_ON', 'label_en': 7}])
def test_bad_presentation_falls_back_without_inventing_confirmation(bad):
    result = _read({'verdict': 'RISK_ON', 'presentation': bad})
    assert result['label_en'] == 'Risk-on composite'


@pytest.mark.parametrize('verdict', ['RISK_ON', 'MIXED', 'RISK_OFF'])
def test_legacy_subline_matches_actual_server_macro(verdict):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    ms = {'verdict': verdict, 'score': 61}
    html = env.from_string('{% import "_market_read.html.j2" as mr %}'
                           '{{ mr.subline(ms) }}').render(ms=ms)
    result = _read(ms)
    assert result['subline_en'] in html
    assert result['subline_zh'] in html


def test_legacy_capped_feed_does_not_call_its_displayed_limit_a_measurement():
    result = _read({'verdict': 'MIXED', 'score': 50, 'raw_score': 61})
    assert 'Measured blend' not in result['subline_en']
    assert 'Displayed score' in result['subline_en']


def _patched_dom(display, *, baked_verdict='RISK_ON'):
    """Reuse the existing DOM fixture and execute the real patchMacro function."""
    from tests.test_risk_state_live_session_floor import DOM_STUB
    if not shutil.which('node'):
        pytest.skip('node unavailable; actual live-DOM proof not obtained')
    setup = '''
reg('#ms-word', new El('ms-word'));
reg('#regime-asof', new El('', '', '2026-09-15'));
var vw = reg('.mx5-verdict-word', new El());
reg('.mx5-verdict-word .l-en', new El('', '', 'Confirmation incomplete'));
var gauge = reg('.mx5-gauge-svg', new El());
var flip = reg('.mx5-flip', new El()); flip.style.display = '';
'''
    setup += 'vw.setAttribute("data-baked-verdict",'+json.dumps(baked_verdict)+');\n'
    feed = {'display':display, 'nightly':display, 'nightly_asof':'2026-09-15',
            'built':'2026-09-15 23:59:00 UTC', 'live_active':False}
    source = (ROOT / 'templates/risk_state_live.js').read_text()
    source = source[:source.index('  if (document.readyState')]
    source += '\npatchMacro('+json.dumps(feed)+');})();'
    program = DOM_STUB + setup + source
    program += '\nconsole.log(JSON.stringify({aria:gauge.getAttribute("aria-label"),flip:flip.style.display}));'
    result = subprocess.run(['node','-e',program],capture_output=True,text=True,check=True)
    return json.loads(result.stdout)


def test_actual_live_gauge_accessibility_retains_cap_provenance():
    ms = {'verdict':'MIXED','label_en':'Mixed','score':50,'raw_score':61,
          'capped':True,'score_source':'radar_ceiling'}
    ms['presentation'] = market_read(ms)
    result = _patched_dom(ms)
    assert 'Measured blend 50' not in result['aria']
    assert '50' in result['aria'] and '61' in result['aria']
    assert 'Capped' in result['aria']


@pytest.mark.parametrize('verdict,expected', [('RISK_ON',''), ('MIXED','none')])
def test_live_flip_explanation_compares_measured_verdict_not_qualified_word(verdict, expected):
    ms = {'verdict':verdict,'label_en':'Risk-on' if verdict=='RISK_ON' else 'Mixed',
          'score':61 if verdict=='RISK_ON' else 50,'components':[],
          'freshness':{'stale':True}}
    ms['presentation'] = market_read(ms)
    assert _patched_dom(ms)['flip'] == expected
