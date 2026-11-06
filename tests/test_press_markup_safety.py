"""Static article fragments must never carry executable or hidden markup."""
import pytest

from engine.press import desk_planner as P
from engine.press import validators as V
from tests import press_fixtures as F


def test_full_suite_refuses_script_in_otherwise_passing_draft(tmp_path):
    root = F.fixture_root(tmp_path)
    cfg = P.load_config(root)
    slot = P.plan(["brief"], as_of="2026-07-26", root=root, cfg=cfg)[0]
    draft = F.draft_from_slot(slot)
    assert V.validate(draft, slot, cfg, root=root)["ok"]
    draft["body_html"] += "<script>unsafe()</script>"
    report = V.validate(draft, slot, cfg, root=root)
    assert not report["ok"]
    assert "markup_safety" in report["failed"]


@pytest.mark.parametrize("body", [
    '<p class="press-byline">Desk</p><h2>A dated question</h2>'
    '<p data-claim-ids="revenue-1 margin_2">A &amp; B: 2 &lt; 3.</p>'
    '<ul><li><strong>Fact</strong> <em>scope</em></li></ul>'
    '<p><a href="https://www.occ.gov/news-issuances/news-releases/2026/nr-occ-2026-89.html">OCC</a></p>'
    '<p class="press-footer">Footer</p>',
    '<h3>Context</h3><blockquote>Attributed prose</blockquote><p>Line<br>break</p>',
    '<p><a href=/stocks/BAC.html>BAC</a></p>',
    "<p>Less than 3 &gt; 2; an apostrophe's fine.</p>",
])
def test_safe_fragments_remain_accepted(body):
    assert V.check_markup_safety({"body_html": body}, {}, {})["ok"]


@pytest.mark.parametrize("body", [
    "<script>alert(1)</script>", "<ScRiPt src='https://bad.example/x'></ScRiPt>",
    "<p onclick='unsafe()'>x</p>", '<p ONMOUSEOVER="unsafe()">x</p>',
    '<p style="display:none">hidden claims</p>',
    '<a href="javascript:unsafe()">x</a>', '<a href="JaVaScRiPt:unsafe()">x</a>',
    '<a href="java&#x73;cript:unsafe()">x</a>',
    '<a href="java&#10;script:unsafe()">x</a>',
    '<a href="data:text/html,bad">x</a>', '<a href="//bad.example">x</a>',
    '<a href="/\\bad.example">x</a>',
    '<iframe src="https://bad.example"></iframe>',
    '<svg><a href="javascript:unsafe()">x</a></svg>', '<math><mtext>x</mtext></math>',
    '<form action="https://bad.example"><input name="password"></form>',
    '<object data="bad"></object>', '<embed src="bad">',
    '<style>p{display:none}</style>', '<link rel="stylesheet" href="bad">',
    '<meta http-equiv="refresh" content="0;url=https://bad.example">',
    '<base href="https://bad.example">', '<img src=x onerror=unsafe()>',
    '<a href="/blog/" href="javascript:unsafe()">x</a>',
    '<a href="/blog/" HREF="/learn/">x</a>',
    '<p hidden>hidden</p>', '<p class="hidden">hidden</p>',
    '<p xmlns="http://www.w3.org/2000/svg">x</p>',
    '<p><strong>mismatched</p></strong>', '<p>unclosed',
    '<p title="unfinished', '<p /onmouseover="unsafe()">x</p>',
    '<p>text</p bogus>', '<!-- hidden markup -->', '<!DOCTYPE html>',
    '<?xml version="1.0"?>', '<![CDATA[<script>unsafe()</script>]]>',
    '<p>nul\x00text</p>', '<p><a href="/blog/">nested<a href="/learn/">a</a></a></p>',
])
def test_unsafe_or_ambiguous_fragments_are_refused(body):
    row = V.check_markup_safety({"body_html": body}, {}, {})
    assert not row["ok"]
    assert row["name"] == "markup_safety"
