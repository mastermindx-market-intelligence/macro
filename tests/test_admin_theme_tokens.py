"""The admin consumes canonical tokens without site-wide page rules."""
from pathlib import Path
import re

import pytest

from admin.theme_tokens import project_theme_tokens


def test_tokens_preserve_cascade_values_and_reference_scope():
    source = '''@import url("other.css");
    :root { --bg: #111; --panel: var(--bg); color: red; }
    html[data-theme="light"] { --bg: #fff; }
    html[data-theme="light"][data-lang="zh"] { --panel: var(--bg, white); }
    .card { --bg: pink; padding: 5px; }
    @media (max-width: 600px) { .card { --bg: yellow; } }
    body::before { content: "}"; }
    '''
    result = project_theme_tokens(source)
    assert '--admin-canonical-panel: var(--admin-canonical-bg);' in result
    assert 'var(--admin-canonical-bg, white)' in result
    assert result.index('#111') < result.index('#fff')
    for excluded in ('@import', '.card', '@media', 'padding', 'color:', 'body', 'pink'):
        assert excluded not in result


@pytest.mark.parametrize("source", [
    ':root { --bg: red;', ':root { --bg: ; }', ':root { --bad token: red; }',
    ':root { --bg: var(--missing; }', ':root { .child { --bg: red; } }',
    '.card { --bg: red; }', ':root { --bg: red; } /* open',
])
def test_malformed_or_missing_canonical_tokens_refuse(source):
    with pytest.raises(ValueError):
        project_theme_tokens(source)


def test_string_delimiters_and_fallbacks_are_retained():
    result = project_theme_tokens(':root { --font: "A; B", sans-serif; --shadow: var(--shade, rgb(0,0,0)); }')
    assert '"A; B", sans-serif;' in result
    assert 'var(--admin-canonical-shade, rgb(0,0,0))' in result


def test_quoted_comment_and_variable_text_is_not_rewritten():
    source = ':root { --font: "A/* keep */B"; --label: "var(--text)"; --text: red; --ink: var(--text); }'
    result = project_theme_tokens(source)
    assert '--admin-canonical-font: "A/* keep */B";' in result
    assert '--admin-canonical-label: "var(--text)";' in result
    assert '--admin-canonical-ink: var(--admin-canonical-text);' in result


def test_quotes_inside_comments_do_not_change_block_parsing():
    result = project_theme_tokens('/* "not a string */ :root { --bg: red; /* \' */ }')
    assert '--admin-canonical-bg: red;' in result


def test_actual_canonical_source_supplies_both_art_directions_and_no_page_rules():
    source = Path(__file__).resolve().parents[1] / 'templates/theme.css'
    result = project_theme_tokens(source.read_text())
    assert 'html[data-theme="light"]' in result
    assert 'html[data-lang="zh"]' in result
    for token in ('bg', 'panel', 'panel2', 'text', 'muted', 'line', 'font-ui', 'ink-ok'):
        assert f'--admin-canonical-{token}:' in result
    assert not re.search(r'var\(\s*--(?!admin-canonical-)', result)
    assert '@import' not in result and not re.search(r'^body\b', result, re.M)
    assert project_theme_tokens(source.read_text()) == result
