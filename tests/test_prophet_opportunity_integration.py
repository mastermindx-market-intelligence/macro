"""Exercise the production board partial, not an unrelated preview page."""
from bs4 import BeautifulSoup

from tests.test_dashboard_template_render import _board_row, _env


def _source(**extra):
    row = _board_row(
        ticker="BRK.B", name="Example Company", industry="Insurance",
        sector="Financials", stage="live", lane="continuation", featured=True,
        signal_asof="2026-09-21", price_as_of="2026-09-24T16:00:00-04:00",
        added_date="2026-09-01", prophet={"score": 0},
        entry_signal={"status": "buy_now", "headline": "Check concentration.",
                      "buy_zone": {"low": 40, "high": 44}},
        conviction={"cautions": ["Known risk"], "cautions_zh": ["已知风险"]},
        spark_svg='<svg class="nch" viewBox="0 0 240 42"><line x1="144" x2="240" y1="10" y2="10"/>'
                  '<line x1="144" x2="240" y1="30" y2="30"/>'
                  '<polyline fill="none" stroke="var(--down)" points="0,10 120,30 240,20"/></svg>',
    )
    row.update(extra)
    return row


def _render(rows, prefix="today"):
    env = _env()
    env.autoescape = True
    return BeautifulSoup(env.get_template("_us_board_cards.html.j2").render(
        items=rows, opportunity_prefix=prefix, sg_any=True, bs_adj=False,
        xu_allfeat=False, trg_map={}, rw_en="", rw_zh="",
        setup_as_of="2026-09-23", plan_rel={"state": "unknown", "plans": []},
        plan_rel_by_ticker={}), "html.parser")


def test_native_card_preserves_source_order_and_occurrences_across_views():
    rows = [_source(), _source(ticker="SECOND")]
    views = [_render(rows, p) for p in ("today", "screener", "today-paid", "screener-paid")]
    ids = []
    for view in views:
        cards = view.select("article.pvcard.po-card")
        assert [c["data-ticker"] for c in cards] == ["BRK.B", "SECOND"]
        ids.extend(c["id"] for c in cards)
    assert len(ids) == len(set(ids)) == 8


def test_native_setup_and_quote_consumers_keep_their_real_hooks():
    card = _render([_source()]).select_one(".po-card")
    assert card["data-stage"] == "live"
    assert card.select_one(".pv-setup-stock-link")["href"] == "stock.html#BRK.B"
    assert card.select_one(".pv-setup-inline > summary")
    assert card.select_one(".pv-setup-inline .pv-setup-body")
    assert card.select_one(".pv-chart > svg")
    quote = card.select_one(".nb-px[data-sym='BRK.B'][data-mkt='us']")
    assert quote and quote.find_next_sibling(class_="nb-chg")
    assert card.select_one(".pv-live").has_attr("hidden")
    # Existing native detail keeps its unresolved Plan relationship.
    assert card.select_one("[data-plan-relation='unknown']")


def test_visible_card_retains_independent_clocks_cautions_and_zone_geometry():
    card = _render([_source()]).select_one(".po-card")
    assert "2026-09-21" in card.select_one(".po-signal-date").get_text()
    assert "2026-09-24" in card.select_one(".po-quote").get_text()
    assert "2026-09-23" in card.select_one(".po-terms").get_text()
    assert "2026-09-01" in card.select_one(".pv-added").get_text()
    assert card.select_one(".pv-added")["data-added"] == "2026-09-01"
    assert "continuously" in card.select_one(".pv-added")["data-tip-en"]
    assert "Known risk" in card.select_one(".po-cautions").get_text()
    assert "Check concentration." in card.get_text()
    assert "Insurance" in card.get_text()
    assert len(card.select(".po-zone-edge")) == 2
    assert card.select_one(".po-chart")["data-direction"] == "down"
    assert card.select_one(".po-priority").get_text(" ", strip=True).startswith("Priority")


def test_missing_assessment_and_unsafe_text_never_create_a_signal_or_markup():
    card = _render([_source(entry_signal=None, dir="up", name='<script>bad()</script>')]).select_one(".po-card")
    assert card["data-stance"] == "unknown"
    assert "Assessment unavailable" in card.get_text()
    assert not card.select("script")
    assert "<script>bad()</script>" in card.get_text()


def test_exact_model_relation_is_not_created_by_the_card():
    card = _render([_source()]).select_one(".po-card")
    assert not card.select("[data-plan-exact='available']")
    assert not card.select("input[type='checkbox']:not([disabled])")


def test_bound_context_link_survives_today_and_screener_without_markup_injection():
    source = _source(theme={'id': 'ai_infra', 'name': '<em>AI infrastructure</em>', 'name_zh': '人工智能基础设施'})
    for prefix in ('today', 'screener', 'today-paid', 'screener-paid'):
        card = _render([source], prefix).select_one('.po-card')
        link = card.select_one('.po-context')
        assert link['href'] == '/baskets.html#theme-ai_infra'
        assert '<em>AI infrastructure</em>' in link.get_text()
        assert '人工智能基础设施' in link.get_text()
        assert link.find('em') is None
    assert _render([_source(theme={'name': 'No relationship id'})]).select_one('.po-context') is None


def test_actual_card_geometry_survives_native_detail_chart_copy():
    """Exercise the existing dialog's sanitizer on the new card's real SVG."""
    import json
    from pathlib import Path
    import subprocess
    from xml.etree import ElementTree
    svg = _render([_source()]).select_one('.pv-chart > svg')
    # XML preserves the case-sensitive viewBox attribute; HTML parsers fold it.
    root = ElementTree.fromstring(str(svg).replace('viewbox=', 'viewBox=').replace('preserveaspectratio=', 'preserveAspectRatio='))
    items = [{'localName': e.tag, 'attributes': [{'name': k, 'value': v} for k, v in e.attrib.items()]} for e in root.iter()]
    source = (Path(__file__).parents[1] / 'templates/theme.js').read_text()
    owner = source[source.index('  function chartCopy(svg) {'):source.index('  function sourceStamp(row) {')]
    script = owner + '''
const items = JSON.parse(process.argv[1]);
function tree(extra) {
  const nodes = items.map(x => ({...x, namespaceURI:'http://www.w3.org/2000/svg', attributes:x.attributes.slice()}));
  if (extra) nodes[1].attributes.push({name:'onload', value:'bad()'});
  nodes[0].querySelectorAll = () => nodes.slice(1);
  nodes[0].cloneNode = () => ({setAttribute(){}});
  return nodes[0];
}
if (!chartCopy(tree(false))) throw Error('Native detail rejected the real card chart');
if (chartCopy(tree(true))) throw Error('Hostile chart acquired a bypass');
'''
    subprocess.run(['node', '-e', script, json.dumps(items)], check=True, capture_output=True, text=True, timeout=10)


def test_missing_quote_remains_connected_to_the_existing_quote_owner():
    card = _render([_source(price=None, price_as_of=None)]).select_one('.po-card')
    quote = card.select_one('.nb-px')
    assert 'Quote unavailable' in quote.get_text()
    assert not quote.has_attr('data-through')
    assert quote.find_next_sibling(class_='nb-chg')
    assert card.select_one('[data-quote-clock]')
    assert card['data-stance'] == 'buy'  # quote absence does not invent a new assessment


def test_native_detail_carries_card_cautions_and_independent_chart_clock():
    card = _render([_source(spark_as_of='2026-09-22', conviction={
        'cautions': ['Known risk', '<b>Untrusted risk</b>'],
        'cautions_zh': ['已知风险', '<b>不可信文本</b>']})]).select_one('.po-card')
    detail = card.select_one('.pv-setup-body[data-opportunity-detail]')
    assert 'Example Company' in detail.select_one('.pvs-company').get_text()
    assert 'Known risk' in detail.select_one('.pvs-opportunity-cautions').get_text()
    assert '<b>Untrusted risk</b>' in detail.select_one('.pvs-opportunity-cautions').get_text()
    assert not detail.select_one('.pvs-opportunity-cautions b')
    assert '2026-09-22' in detail.select_one('.pvs-chart-clock').get_text()
    assert '2026-09-24' in detail.select_one('.pvs-snapshot').get_text()
    assert detail.select_one('.pvs-assessment-clock')['data-assessment-asof'] == ''


def test_detail_discloses_published_evidence_and_abstentions_without_a_new_score():
    row = _source(prophet={'version': 'us_prophet_v3', 'score': 0,
        'fusion': {'definition': 'us_prophet_v3', 'families_active': ['F1_TECHNICAL_CONFLUENCE'],
                   'family_contribution': {'F1_TECHNICAL_CONFLUENCE': 0},
                   'families_abstaining': ['F7_QUALITY_FUNDAMENTAL']}})
    row['entry_signal']['action'] = 'Published <script>text</script>; wait for confirmation.'
    card = _render([row]).select_one('.po-card')
    assert 'evidence-family' in card.select_one('.po-priority')['data-tip-en']
    detail = card.select_one('.pv-setup-body')
    assert not detail.select('script')
    assert '<script>text</script>' in detail.select_one('.pvs-assessment-detail').get_text()
    assert detail.select_one('[data-evidence-family] dd').get_text() == '0.0'
    assert 'Business quality' in detail.select_one('.pvs-evidence-absent').get_text()
    assert 'not probabilities' in detail.select_one('.pvs-evidence-profile').get_text()


def test_one_supplied_classification_does_not_gain_a_placeholder_neighbor():
    card = _render([_source(industry=None, sector="Financials")]).select_one('.po-card')
    classification = card.select_one('.po-class')
    assert 'Financials' in classification.get_text()
    assert '—' not in classification.get_text() and not classification.select('.po-sep')
