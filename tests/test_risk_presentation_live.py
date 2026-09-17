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
