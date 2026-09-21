from pathlib import Path


def _template() -> str:
    return (Path(__file__).resolve().parents[1] / 'templates' / 'subsector_detail.html.j2').read_text()


def test_unified_intelligence_shell_and_responsive_member_cards():
    template = _template()
    for token in ('class="id-hero"', 'class="id-group-read"', 'class="id-structure"',
                  'class="members-table-wrap"', 'class="member-cards"', 'class="id-evidence"'):
        assert token in template
    compact = template.replace(' ', '')
    assert '@media(max-width:640px)' in compact
    assert '.members-table-wrap{display:none' in compact
    assert '.member-cards{display:grid' in compact


def test_unified_shell_preserves_payload_truth_and_existing_chart_consumer():
    template = _template()
    for token in ('g.as_of', 'g.n_priced', 'g.n_members', 'g.reliability', 'g.members', 'r.action', 'e.reason'):
        assert token in template
    assert 'window.StockChart.mount' in template
    assert 'CHART_KEY' in template
    assert 'AI Semiconductors' not in template
    assert '>66<' not in template


def test_unified_shell_adapts_visible_identity_without_builder_fork():
    from scripts import build_subsector_confluence as bsc

    html = bsc._env().get_template('subsector_detail.html.j2').render(
        detail_json='{"kind":"concept"}', group_name='Smart Home', chart_key=None,
        has_signals=False, back_href='../subsectors_china.html',
    )
    assert '<title>Smart Home — Intelligence Detail</title>' in html
    assert 'Intelligence groups' in html
    assert '情报分组' in html
    assert "pageIdentity = DETAIL.kind" in html
    assert 'L("Theme Intelligence", "主题情报")' in html
    assert 'L("Sector Intelligence", "板块情报")' in html
    assert 'L("Subsector Intelligence", "子行业情报")' in html
