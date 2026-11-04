from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path

import pytest

from lib.intl_workspace_fragments import partition_workspace, publish_workspace_fragments

GEN = "im-workspace-generation:3829962a-245d-41a2-ac31-f045b8c95dfa"


def country_builder_preserves_calculations(candidate: bytes) -> bool:
    """Permit only the post-binding presentation hook over the audited builder.

    The older GS lane freezes calculations and qualification. The production
    completion task adds a rendering partition after those owners have finished;
    removing precisely that import and call must recover the entire audited image.
    This is deliberately narrower than accepting another arbitrary builder hash.
    """
    accepted = 'edf479bc1d6630d2eaff2a35df15c4a1e3830a0d303757a17d50670a10983b6f'
    if sha256(candidate).hexdigest() == accepted:
        return True
    addition = b'from lib.intl_workspace_fragments import publish_workspace_fragments  # noqa: E402\n'
    before = b'        write_page(site / "intl.html", macro_html)'
    after = (b'        # All render/binding passes complete before the normal owner partitions presentation.\n'
             b'        macro_html = publish_workspace_fragments(macro_html, site)\n' + before)
    if candidate.count(addition) != 1 or candidate.count(after) != 1:
        return False
    original = candidate.replace(addition, b'', 1).replace(after, before, 1)
    return sha256(original).hexdigest() == accepted


def test_presentation_partition_preserves_entire_audited_builder():
    candidate = (Path(__file__).resolve().parents[1] / 'scripts/build_intl.py').read_bytes()
    assert country_builder_preserves_calculations(candidate)
    assert not country_builder_preserves_calculations(candidate + b'\n# unrelated source change\n')
    assert not country_builder_preserves_calculations(candidate.replace(b'write_page(site / "intl.html", macro_html)', b'write_page(site / "intl.html", stocks_html)'))
    assert not country_builder_preserves_calculations(candidate.replace(b'macro_html = publish_workspace_fragments(macro_html, site)', b'macro_html = publish_workspace_fragments(stocks_html, site)'))


def panel(view="dossier", horizon="1m", basis="local", generation=GEN):
    identity = f"im-gs-{view}-{horizon}-{basis}"
    content = ('<div data-gs-market-scope>'
               f'<article data-gs-market="JP" data-gs-market-default id="{identity}-JP"><h3>Japan 日本</h3>'
               '<p>3.17% · 2026-10-30 &amp; exact window</p><details><summary>Evidence</summary><p>Qualified</p></details></article>'
               f'<article data-gs-market="KR" id="{identity}-KR" hidden><h3>Korea</h3><p>Unavailable: not_supplied</p></article></div>')
    return (f'<section data-im-panel data-view="{view}" data-horizon="{horizon}" data-basis="{basis}" '
            f'data-return-basis="price" data-source="" data-im-generation="{generation}" id="{identity}" '
            f'aria-labelledby="{identity}-title"><header><h2 id="{identity}-title">Research</h2></header>{content}</section>')


def page(*panels):
    return '<html><body><main data-im-workspace data-im-binding-version="2"><p>Country evidence stays eager</p>' + ''.join(panels) + '</main></body></html>'


class Manifests(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.active = False
        self.manifests = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "script" and "data-im-deferred-manifest" in dict(attrs):
            self.active = True

    def handle_data(self, data):
        if self.active:
            self.manifests.append(json.loads(data))

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False


def test_exact_market_content_is_preserved_and_only_selected_article_is_in_fragment():
    original = panel()
    result = partition_workspace(page(original))
    assert result.panel_count == 1
    assert 'Country evidence stays eager' in result.html
    assert '3.17%' not in result.html
    manifest = Manifests(result.html).manifests[0]
    assert manifest['markets'] == ['JP', 'KR']
    for market in ['JP', 'KR']:
        ref = manifest['variants'][market]
        raw = result.assets[ref['url']]
        assert ref['sha256'] == sha256(raw).hexdigest()
        assert ref['bytes'] == len(raw)
        fragment = json.loads(raw)['fragments'][manifest['panel_id']]
        assert fragment['market'] == market
        assert fragment['html'].count('<article ') == 1
        start = original.index(f'<article data-gs-market="{market}"')
        article = original[start:original.index('</article>', start) + len('</article>')]
        assert article in fragment['html']
    assert 'Unavailable: not_supplied' in json.loads(result.assets['assets/intl-workspace/dossier-KR.json'])['fragments'][manifest['panel_id']]['html']


def test_dossier_contexts_share_bounded_market_slots_and_build_is_deterministic():
    source = page(panel(), panel(horizon='3m'), panel(basis='usd_unhedged'), panel('scanner'), panel('coverage'))
    first = partition_workspace(source)
    second = partition_workspace(source)
    assert first == second
    assert len(first.assets) == 4
    assert len(json.loads(first.assets['assets/intl-workspace/dossier-JP.json'])['fragments']) == 3
    scanner = json.loads(first.assets['assets/intl-workspace/scanner-1m-local.json'])
    assert scanner['fragments']['im-gs-scanner-1m-local']['html'] == panel('scanner')


@pytest.mark.parametrize('source', [
    page(panel(), panel()),
    page(panel(), panel('coverage', generation='im-workspace-generation:4829962a-245d-41a2-ac31-f045b8c95dfa')),
    page(panel().replace('data-gs-market="KR"', 'data-gs-market="JP"')),
    page(panel().replace('data-gs-market-default', '')),
    page(panel().replace('</article><article', '</article><p>unowned</p><article')),
    page(panel().replace('</article>', '', 1)),
    page(panel().replace('data-horizon="1m"', 'data-horizon="unknown"')),
    page(panel()).replace('data-im-binding-version="2"', 'data-im-binding-version="1"'),
])
def test_ambiguous_or_malformed_publication_fails_closed(source):
    with pytest.raises(ValueError):
        partition_workspace(source)


def test_assets_publish_before_advertising_page_and_slots_do_not_grow(tmp_path):
    first = publish_workspace_fragments(page(panel()), tmp_path)
    second = publish_workspace_fragments(page(panel().replace(GEN, GEN.replace('3829962a', '4829962a'))), tmp_path)
    assert first != second
    assert len(list(tmp_path.rglob('*.json'))) == 2
    assert not list(tmp_path.rglob('*.tmp'))
    for manifest in Manifests(second).manifests:
        for ref in manifest['variants'].values():
            assert sha256((tmp_path / ref['url']).read_bytes()).hexdigest() == ref['sha256']


def test_pages_without_deferred_views_are_unchanged():
    source = '<html><body>Stocks or an existing small test fixture</body></html>'
    result = partition_workspace(source)
    assert result.html == source and not result.assets and result.panel_count == 0
