"""Source contracts complement, not replace, the committed browser evidence."""
from pathlib import Path
import re
import pytest
from scripts.optimize_assets import _hash_bytes

ROOT = Path(__file__).resolve().parents[1]


def _media(css: str, width: int) -> str:
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    match = re.search(r'@media\s*\(max-width:\s*' + str(width) + r'px\)\s*\{', css)
    assert match, f'Missing existing {width}px responsive block'
    depth, end, quote, escaped = 1, match.end(), None, False
    while depth and end < len(css):
        char = css[end]
        if escaped:
            escaped = False
        elif quote and char == '\\':
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        else:
            depth += (char == '{') - (char == '}')
        end += 1
    assert depth == 0, 'Unbalanced responsive block'
    return css[match.end():end - 1]


def _rule(block: str, selector: str) -> str:
    selector_pattern = re.escape(selector).replace(r'\ ', r'\s+')
    match = re.search(r'(?:^|})\s*' + selector_pattern + r'\s*\{([^}]+)\}', block)
    assert match, f'Missing exact selector {selector}'
    return re.sub(r'\s+', '', match.group(1))

@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_footer_uses_shared_public_two_column_mobile_layout(surface):
    css = (ROOT / surface / 'landing.css').read_text()
    rule = _rule(_media(css, 900), '.f-cols')
    for declaration in ('display:grid', 'width:100%', 'grid-template-columns:repeat(2,minmax(0,1fr))'):
        assert declaration in rule


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_situation_score_and_timing_can_wrap_without_clipping(surface):
    mobile = _media((ROOT / surface / 'landing.css').read_text(), 680)
    assert 'grid-template-columns:minmax(0,1fr)' in _rule(mobile, '.sits')
    assert 'min-width:0' in _rule(mobile, '.sit')
    assert 'flex-wrap:wrap' in _rule(mobile, '.sit .meter')
    timing = _rule(mobile, '.sit .early')
    assert 'white-space:normal' in timing and 'max-width:100%' in timing


def test_landing_styles_are_byte_paired():
    assert (ROOT / 'templates/landing.css').read_bytes() == (ROOT / 'site/landing.css').read_bytes()


def test_wrong_compound_selector_is_rejected():
    with pytest.raises(AssertionError, match='Missing exact selector'):
        _rule('.sit.early{white-space:normal}', '.sit .early')


def test_meter_outside_mobile_breakpoint_is_rejected():
    css = '@media(max-width:680px){.sit{min-width:0}} .sit .meter{flex-wrap:wrap}'
    with pytest.raises(AssertionError, match='Missing exact selector'):
        _rule(_media(css, 680), '.sit .meter')


def test_media_scanner_ignores_quoted_and_commented_braces():
    css = '@media(max-width:680px){.x{content:"}"}/* } */.sit{min-width:0}}'
    assert 'min-width:0' in _rule(_media(css, 680), '.sit')


@pytest.mark.parametrize('relative', [
    'templates/index.html', 'site/index.html',
    'templates/about.html', 'site/about.html',
    'site/products/market-terminal.html',
    'site/products/market-dashboards.html',
    'site/products/mastermind-ai.html',
])
def test_landing_family_uses_current_stylesheet_cache_stamp(relative):
    expected = _hash_bytes(ROOT / 'site/landing.css')
    text = (ROOT / relative).read_text()
    references = re.findall(r'landing\.css\?v=([a-f0-9]+)', text)
    assert references, f'Expected landing stylesheet in {relative}'
    assert set(references) == {expected}, f'Stale immutable CSS reference in {relative}'


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_delayed_example_caption_remains_readable_at_narrow_widths(surface):
    mobile = _media((ROOT / surface / 'landing.css').read_text(), 680)
    rule = _rule(mobile, '.ph-tag')
    assert 'white-space:normal' in rule
    assert 'flex-wrap:wrap' in rule and 'max-width:100%' in rule
