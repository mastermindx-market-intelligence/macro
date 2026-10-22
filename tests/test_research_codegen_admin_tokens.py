import re
import pytest

from admin.research_diagnostic_tokens import project_tokens, stylesheet


def test_projection_is_only_canonical_properties_and_section_scoped():
    raw = stylesheet().decode()
    assert raw and ":root" not in raw and "html" not in raw and "@" not in raw
    blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", raw)
    assert len(blocks) >= 4
    assert all(selector.strip().startswith(".rf-diagnostics") for selector, _ in blocks)
    assert all(d.strip().startswith("--") for _, body in blocks for d in body.split(";") if d.strip())
    assert '.rf-diagnostics[data-theme="light"][data-lang="zh"]' in raw


def test_nested_rules_selectors_and_non_tokens_cannot_escape():
    source = '''@import "elsewhere";
    :root {--bg:#123; color:red; --font:"a{b}";}
    @media (min-width: 1px) {:root {--bad:red;}}
    html[data-theme="light"] {--bg:#fff;}
    body {--escape:red;} html[data-theme="light"] .card {--oops:red;}
    '''
    # A brace-bearing root block is deliberately not projected, rather than parsed loosely.
    out = project_tokens(source).decode()
    assert out == '.rf-diagnostics[data-theme="light"]{--bg:#fff;}\n'


def test_canonical_change_changes_projection_and_incomplete_refuses():
    assert project_tokens(":root {--text:#123;}") != project_tokens(":root {--text:#234;}")
    for text in ("", ":root{", "body{color:red}", "x" * (1024*1024+1)):
        with pytest.raises(ValueError):
            project_tokens(text)
