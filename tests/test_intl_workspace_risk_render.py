"""Render contracts for the supplied-field Risk projection."""

import copy
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "intl_workspace" / "risk_render.json"
TEMPLATE = "templates/intl_workspace/risk.html.j2"
CSS_PATH = ROOT / "templates" / "intl_workspace_risk.css"

BILINGUAL = (
    ("Risk and transmission", "风险与传导"),
    ("Select a market to examine the currency channel", "选择市场以查看汇率传导"),
    ("Why the dollar return differs", "美元回报为何不同"),
    ("Local index return", "本币指数回报"),
    ("Currency return", "汇率回报"),
    ("USD price return", "美元价格回报"),
    ("Fast pressure. Slow resilience.", "短期压力，长期韧性"),
    ("Company exposure requirements", "企业敞口要求"),
    ("Issuer identity", "发行人身份"),
    ("Revenue currency", "收入货币"),
    ("Cost currency", "成本货币"),
    ("Debt currency", "债务货币"),
    ("Hedges", "对冲"),
    ("Effective date", "生效日期"),
    ("Emerging-market stress", "新兴市场压力"),
    ("Transmission to the US", "向美国传导"),
    ("VAR/GFEVD statistical connectedness", "VAR/GFEVD 统计关联"),
    ("Daily return correlation", "日回报相关性"),
    ("Directed model pressure", "有向模型压力"),
    ("Structural fragility", "结构性脆弱"),
    ("Transmission assessment unavailable", "传导评估不可用"),
    ("Unavailable", "不可用"),
    ("Not supplied", "未提供"),
    ("Back", "返回"),
)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids = []
        self.hrefs = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a" and "href" in values:
            self.hrefs.append(values["href"])


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def render(
    risk_section,
    registry,
    context_id="im-overview-0",
    panel_context=None,
    generation="im-workspace-generation:12345678-1234-4123-8123-123456789012",
):
    environment = Environment(
        loader=FileSystemLoader(ROOT),
        autoescape=False,
        undefined=StrictUndefined,
    )
    template = environment.get_template(TEMPLATE)
    return template.render(
        risk_section=risk_section,
        registry=registry,
        context_id=context_id,
        panel_context=panel_context
        or {
            "horizon": "1m",
            "currency_basis": "usd_unhedged",
            "return_basis": "price",
            "selected_market": None,
        },
        generation=generation,
    )


def collect(html):
    collector = Collector()
    collector.feed(html)
    return collector


def packet():
    data = load_fixture()
    return data["risk_section"], data["registry"], data


def test_positive_synthetic_kr_rounds_display_and_keeps_units_distinct():
    risk_section, registry, _ = packet()
    html = render(risk_section, registry)
    kr = html.split('data-im-risk-channel="0"', 1)[1].split("data-im-risk-channel=", 1)[0]

    assert "-2.59" in kr
    assert "-0.8" in kr
    assert "-0.79" in kr
    assert "-2.5856" not in html
    assert "0.8000000000000007" not in html
    assert "0.7856" not in html
    assert "Infinity" not in html
    assert "pp" in kr and "个百分点" in kr
    assert "(1+local)" in html.replace(" ", "") or "(1 + local)" in html
    assert "fell" not in html.lower()
    assert "gained" not in html.lower()
    assert "weakened" not in html.lower()
    assert "earnings" not in html.lower()
    assert "South Korea" in kr and "韩国" in kr
    assert "KOSPI" in kr


def test_semantic_panel_context_generation_and_select():
    risk_section, registry, data = packet()
    html = render(
        risk_section,
        registry,
        context_id=data["context_id"],
        panel_context=data["panel_context"],
        generation=data["generation"],
    )
    collector = collect(html)
    panel = next(values for tag, values in collector.tags if tag == "section")

    assert "data-im-panel" in panel
    assert panel["class"] == "intl-risk"
    assert panel["id"] == "im-overview-0-risk"
    assert panel["data-view"] == "risk"
    assert panel["data-horizon"] == "1m"
    assert panel["data-basis"] == "usd_unhedged"
    assert panel["data-return-basis"] == "price"
    assert panel["data-source"] == ""
    assert panel["data-im-generation"] == data["generation"]
    assert 'data-im-action="select_market"' in html
    assert '<option value=""' in html
    assert '<option value="KR"' in html
    assert '<option value="GB"' in html
    assert 'data-im-risk-prompt' in html
    assert 'data-im-risk-channel="0"' in html
    assert 'data-im-risk-market="KR"' in html
    assert 'data-im-risk-channel="1"' in html
    assert 'data-im-risk-market="GB"' in html
    assert 'data-im-risk-row="KR"' in html
    assert 'data-im-risk-row="GB"' in html
    assert html.count('scope="col"') == 5
    assert html.count('scope="row"') == 2
    assert "<caption" in html
    assert "<script" not in html.lower()


def test_optional_generation_omitted_and_usd_unhedged_copy_stays():
    risk_section, registry, _ = packet()
    html = render(
        risk_section,
        registry,
        generation=None,
        panel_context={
            "horizon": "1m",
            "currency_basis": "local",
            "return_basis": "price",
            "selected_market": None,
        },
    )
    assert "data-im-generation" not in html
    assert 'data-basis="local"' in html
    assert "USD" in html and "Unhedged" in html
    assert "未对冲" in html


def test_empty_denied_zero_and_missing_quality_not_zero():
    risk_section, registry, _ = packet()
    empty = copy.deepcopy(risk_section)
    empty["currency_channels"] = []
    empty["pressure_rows"] = []
    empty_html = render(empty, registry)
    assert "data-im-risk-channel=" not in empty_html
    assert "data-im-risk-row=" not in empty_html
    assert "Select a market to examine the currency channel" in empty_html

    denied = copy.deepcopy(risk_section)
    denied["currency_channels"][0]["market"] = None
    denied_html = render(denied, registry)
    denied_block = denied_html.split('data-im-risk-channel="0"', 1)[1].split(
        "data-im-risk-channel=", 1
    )[0]
    assert "data-im-risk-market=" not in denied_block
    assert '<span class="l-en">Information withheld</span>' in denied_block
    assert "South Korea" not in denied_block
    assert "韩国" not in denied_block

    zero = copy.deepcopy(risk_section)
    zero["currency_channels"][0]["local_return"]["value"] = 0
    zero["pressure_rows"][0]["country_credit_change"]["value"] = 0
    zero_html = render(zero, registry)
    kr_cards = zero_html.split('data-im-risk-channel="0"', 1)[1].split(
        "data-im-risk-channel=", 1
    )[0]
    assert re.search(r">0(\.0)?<", kr_cards.replace(" ", ""))
    credit = zero_html.split('data-im-risk-row="KR"', 1)[1].split("</tr>", 1)[0]
    assert re.search(r"\b0\b", credit)
    assert "Unavailable" not in credit or "0" in credit

    missing = copy.deepcopy(risk_section)
    missing["currency_channels"][0]["usd_return"] = {
        "value": None,
        "unit": "percent",
        "quality": "unknown",
        "reason": "not_supplied",
        "window": None,
    }
    missing_html = render(missing, registry)
    usd_card = missing_html.split("USD price return", 1)[1].split("data-im-risk-channel=", 1)[0]
    assert "Unavailable" in usd_card or "Not supplied" in usd_card
    assert "-2.59" not in usd_card


def test_mixed_annual_years_projection_and_independent_clocks():
    risk_section, registry, _ = packet()
    risk_section = copy.deepcopy(risk_section)
    gb = risk_section["pressure_rows"][1]
    gb["annual_current_account"] = {
        "field": "annual_current_account",
        "quality": "qualified",
        "reason": None,
        "value": -1.25,
        "unit": "percent_gdp",
        "instrument": {
            "kind": "current_account",
            "id": "native-annual_current_account",
            "market_id": "GB",
        },
        "period": {
            "start": "2023-01-01",
            "end": "2024-01-01",
            "count": 1,
            "count_basis": "release_periods",
        },
        "observation_at": "2026-10-07",
        "calculation_at": None,
        "source_reference": "public-source",
        "evidence_key": "public-annual-gb",
        "support": {
            "method_ref": "annual-owner",
            "market_id": "GB",
            "field_year": 2023,
            "vintage": "2026-03-01",
            "observation_type": "projection",
        },
    }
    html = render(risk_section, registry)
    kr_row = html.split('data-im-risk-row="KR"', 1)[1].split("</tr>", 1)[0]
    gb_row = html.split('data-im-risk-row="GB"', 1)[1].split("</tr>", 1)[0]
    assert "2024" in kr_row
    assert "actual" in kr_row.lower() or "Actual" in kr_row
    assert "2023" in gb_row
    assert "Projection" in gb_row or "projection" in gb_row
    assert "61" in kr_row and "100" in kr_row
    assert "50" in kr_row
    assert "20 days" not in html.lower()
    assert "20-day" not in html.lower()
    assert "current year" not in html.lower()
    gb_credit = gb_row
    assert "Unavailable" in gb_credit or "Not supplied" in gb_credit
    assert "—" not in gb_credit and "&mdash;" not in gb_credit


def test_malicious_strings_escaped_and_ids_unique():
    risk_section, registry, _ = packet()
    risk_section = copy.deepcopy(risk_section)
    registry = copy.deepcopy(registry)
    hostile = 'KR"><script>alert(1)</script>'
    registry["markets"][0]["market_id"] = hostile
    registry["markets"][0]["name_en"] = 'South Korea <img src=x onerror=alert(1)>'
    registry["markets"][0]["name_zh"] = "韩国 & 注入"
    risk_section["currency_channels"][0]["market"]["market_id"] = hostile
    risk_section["currency_channels"][0]["market"]["name_en"] = 'South Korea <span class="x">'
    risk_section["currency_channels"][0]["context"]["source_reference"] = (
        "synthetic:<script>alert(1)</script>"
    )
    risk_section["currency_channels"][0]["input_evidence_refs"][0]["source_reference"] = (
        "https://example.invalid/a?x=1&y=<script>"
    )
    risk_section["pressure_rows"][0]["market_id"] = hostile
    risk_section["pressure_rows"][0]["name_en"] = 'South Korea <b>x</b>'
    risk_section["pressure_rows"][0]["country_credit_change"]["source_reference"] = (
        "public-source<script>"
    )
    context_id = 'im"><img src=x onerror=alert(1)>'
    html = render(risk_section, registry, context_id=context_id)
    collector = collect(html)

    assert "<script>" not in html
    assert "<img src=x" not in html
    assert 'onerror="' not in html
    assert "&lt;script&gt;" in html or "&#34;" in html
    assert "韩国 &amp; 注入" in html
    assert "https://example.invalid/a?x=1&amp;y=&lt;script&gt;" in html
    assert "#" not in collector.hrefs
    assert "" not in collector.hrefs
    first = render(*packet()[:2], context_id="panel-one")
    second = render(*packet()[:2], context_id="panel-two")
    combined = first + second
    ids = collect(combined).ids
    assert len(ids) == len(set(ids))
    assert "panel-one-risk" in combined and "panel-two-risk" in combined


def test_bilingual_labels_and_no_fake_href():
    risk_section, registry, _ = packet()
    html = render(risk_section, registry)
    for english, chinese in BILINGUAL:
        assert f'<span class="l-en">{english}</span>' in html
        assert f'<span class="l-zh" lang="zh">{chinese}</span>' in html
    collector = collect(html)
    assert 'data-im-label-en="All markets" data-im-label-zh="全部市场"' in html
    assert collector.hrefs == []
    assert 'href="#"' not in html
    assert "data-im-risk-close-context" in html
    assert "<button type=\"button\" data-im-risk-close-context" in html


def test_real_destination_anchor_and_qualified_us_statement():
    risk_section, registry, _ = packet()
    risk_section = copy.deepcopy(risk_section)
    risk_section["exposure_boundary"]["destination"] = "/research/company"
    risk_section["domain_panels"]["origin_stress"]["destination"] = "/research/origin"
    risk_section["domain_panels"]["us_transmission"]["summary"] = {
        "quality": "qualified",
        "state": "contained",
        "reason_codes": [],
        "evidence_refs": ["public/overall"],
        "diagnostic": {"reported_state": "contained"},
    }
    html = render(risk_section, registry)
    collector = collect(html)
    assert "/research/company" in collector.hrefs
    assert "/research/origin" in collector.hrefs
    assert "#" not in collector.hrefs
    assert "Contained" in html
    assert "受控" in html
    assert "Reported diagnostic only" in html or "reported diagnostic only" in html.lower()
    assert "us_from_others" not in html
    assert "raw-secret" not in html
    assert "multiply" not in html


def test_large_finite_value_does_not_overflow_or_print_infinity():
    risk_section, registry, _ = packet()
    risk_section = copy.deepcopy(risk_section)
    risk_section["currency_channels"][0]["local_return"]["value"] = 1e12
    html = render(risk_section, registry)
    assert "Infinity" not in html
    assert not re.search(r">[-+]?inf<", html.lower())
    assert "1000000000000" in html
    assert math.isfinite(1e12)


def test_css_is_scoped_frozen_design():
    css = CSS_PATH.read_text(encoding="utf-8")
    for token in (
        "--panel",
        "--panel2",
        "--text",
        "--muted",
        "--line",
        "--link",
        "--up",
        "--down",
        "--card-shadow",
        "--font-ui",
        "--fs-body",
        "--fs-h2",
        "--fs-sm",
        "--fs-num-lg",
        "--r-card",
        "--r-ctl",
    ):
        assert token in css
    assert '[data-theme="light"] .intl-risk' in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 320px)" in css
    assert 'data-im-risk-has-selection="true"' in css
    assert 'data-im-risk-selected="false"' in css
    assert "dashed" in css
    assert "min-block-size: 44px" in css or "min-block-size:44px" in css
    assert "overflow-wrap: anywhere" in css or "overflow-wrap:anywhere" in css
    assert "animation" not in css.lower()
    assert "transition" not in css.lower()
    assert not re.search(r"#[0-9a-fA-F]{3,8}", css)
    assert not re.search(r"(^|\})\s*(html|body)\s*[,{]", css)
    assert ".intl-workspace" not in css
    assert "prefers-reduced-motion" in css


def test_actual_section_schema_renders_all_six_domains_and_supported_statement():
    from lib.intl_workspace_risk_section import build_risk_section
    from tests.test_intl_workspace_risk_section import inputs
    source = inputs()
    html = render(build_risk_section(**source), source["registry"])
    assert html.count("data-im-risk-domain=") == 6
    assert "Contained" in html
    assert "-2.59" in html


def test_supplied_research_link_does_not_hide_qualified_us_statement():
    section, registry, _ = packet()
    section["domain_panels"]["us_transmission"].update(
        destination={"key": "us_transmission", "title_en": "US research",
                     "title_zh": "美国研究", "destination": "#us-research"},
        summary={"quality": "qualified", "state": "transmitting", "diagnostic": None})
    html = render(section, registry)
    assert 'href="#us-research"' in html
    assert "Transmitting" in html


def test_huge_finite_integer_keeps_rendering_available():
    section, registry, _ = packet()
    section["pressure_rows"][0]["country_credit_change"]["value"] = 10 ** 400
    html = render(section, registry)
    assert str(10 ** 400) in html


def test_market_label_does_not_contradict_a_selection():
    section, registry, _ = packet()
    html = render(section, registry)
    label=html.split('class="intl-risk__market-select-label"',1)[1].split('</label>',1)[0]
    assert "All markets" not in label and "全部市场" not in label


def test_company_and_us_copy_uses_product_terms_and_units_once():
    section, registry, _ = packet()
    html=render(section, registry)
    assert "Transmission to the US" in html and "向美国传导" in html
    assert "qualified supported statement" not in html
    card=html.split('data-im-risk-contribution',1)[1].split('</p>',1)[0]
    assert card.count("个百分点")==1


def test_unavailable_reason_has_a_visible_separator():
    section, registry, _ = packet()
    html=render(section, registry)
    assert 'class="intl-risk__reason"' in html


@pytest.mark.parametrize("destination", [
    " javascript:alert(1)", "\tjavascript:alert(1)", "\njavascript:alert(1)",
    "\u00a0javascript:alert(1)", "\ufeffjavascript:alert(1)", " JavaScript:alert(1)",
    " # ", "# ", " #", "\t#", "#\t", "#", "data:text/html,<script>alert(1)</script>",
    "https://example.test", "//example.test", "/\\example.test", "/%2fexample.test",
    "/research/../company", "/research/./company", "/research//company", "/research/company\n",
    None, 1, [], {},
])
def test_unsafe_company_and_domain_destinations_keep_context_fallback(destination):
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = destination
    section["domain_panels"]["us_transmission"]["destination"] = {"destination": destination}
    html = render(section, registry)
    assert collect(html).hrefs == []
    assert html.count("data-im-risk-close-context") == 7


@pytest.mark.parametrize("destination", ["/research/company", "/research/us?market=KR&view=risk", "#intl-legacy-research"])
def test_local_destinations_remain_exact_real_actions(destination):
    section, registry, _ = packet()
    section["exposure_boundary"]["destination"] = {"destination": destination}
    assert collect(render(section, registry)).hrefs == [destination]


@pytest.mark.parametrize('quality', ['unknown', 'denied'])
def test_currency_channel_without_disclosable_evidence_has_no_empty_disclosure(quality):
    section, registry, _ = packet()
    channel = section['currency_channels'][0]
    for key in ('local_return', 'usd_return', 'fx_return_usd_per_local', 'fx_contribution_pp'):
        channel[key] = {'value': None, 'quality': quality, 'reason': 'not_supplied', 'window': None}
    channel['endpoint_policy'] = None
    channel['input_evidence_refs'] = []
    html = render(section, registry)
    block = html.split('data-im-risk-channel="0"', 1)[1].split('data-im-risk-channel=', 1)[0]
    assert 'class="intl-risk__evidence"' not in block
    assert 'Evidence unavailable' in block and '依据不可用' in block


@pytest.mark.parametrize('retained', ['window', 'source_reference'])
def test_currency_channel_retains_disclosable_metadata_without_numeric_values(retained):
    section, registry, _ = packet()
    channel = section['currency_channels'][0]
    window = copy.deepcopy(channel['endpoint_policy'])
    refs = copy.deepcopy(channel['input_evidence_refs'])
    for key in ('local_return', 'usd_return', 'fx_return_usd_per_local', 'fx_contribution_pp'):
        channel[key] = {'value': None, 'quality': 'denied', 'reason': 'value_denied', 'window': None}
    channel['endpoint_policy'] = window if retained == 'window' else None
    channel['input_evidence_refs'] = refs if retained == 'source_reference' else []
    html = render(section, registry)
    block = html.split('data-im-risk-channel="0"', 1)[1].split('data-im-risk-channel=', 1)[0]
    assert 'class="intl-risk__evidence"' in block
    assert (window['start'] if retained == 'window' else refs[0]['source_reference']) in block
    assert 'data-im-risk-value' not in block


@pytest.mark.parametrize('reason', ['qualification_unknown', 'support_unavailable', 'not_supplied'])
def test_unavailable_currency_copy_does_not_repeat_identical_localized_reason(reason):
    section, registry, _ = packet()
    section['currency_channels'][0]['local_return'] = {
        'value': None, 'quality': 'unknown', 'reason': reason, 'window': None,
    }
    html = render(section, registry)
    card = html.split('data-im-risk-card="local"', 1)[1].split('data-im-risk-card="fx"', 1)[0]
    assert card.count('>Unavailable</span>') == 1
    assert card.count('>不可用</span>') == 1
    if reason == 'not_supplied':
        assert '>Not supplied</span>' in card and '>未提供</span>' in card


BREADTH_CLOCK_CASES = ('distinct', 'same', 'zero', 'stale', 'value_denied',
                       'metadata_denied', 'metadata_unknown', 'missing_observation',
                       'missing_membership', 'absent')


def breadth_clock_input(kind, market='JP'):
    """Synthetic native field input; grants here are test-only."""
    from tests.test_intl_workspace_risk_pressure import inputs
    source = inputs()
    key = 'JP.constituent_breadth_50d'
    measure, support = source['measures'][key], source['field_support'][key]
    measure['instrument']['market_id'] = market
    support['market_id'] = market
    measure.update(observation_at='2026-10-05', calculation_at='2026-10-06')
    support['membership_asof'] = '2026-09-30'
    if kind == 'same':
        support['membership_asof'] = measure['observation_at']
    elif kind == 'zero':
        measure['value'] = 0
        support['above_count'] = 0
    elif kind == 'stale':
        measure['quality'] = 'stale'
    elif kind == 'value_denied':
        measure['value_permission'] = 'denied'
    elif kind.startswith('metadata_'):
        measure['metadata'] = kind.removeprefix('metadata_')
    elif kind == 'missing_observation':
        measure['observation_at'] = None
    elif kind == 'missing_membership':
        support['membership_asof'] = None
    elif kind == 'absent':
        return None, None
    return measure, support


@pytest.mark.parametrize('kind', BREADTH_CLOCK_CASES)
def test_breadth_render_preserves_separate_admitted_observation_and_membership_clocks(kind):
    from bs4 import BeautifulSoup
    from lib.intl_workspace_risk_pressure import build_pressure_rows
    section, registry, _ = packet()
    market = registry['markets'][0]['market_id']
    measure, support = breadth_clock_input(kind, market)
    key = market + '.constituent_breadth_50d'
    source = dict(registry=registry, measures={key: measure} if measure else {},
                  field_support={key: support} if support else {})
    before = copy.deepcopy(source)
    section['pressure_rows'] = build_pressure_rows(**source)
    article = BeautifulSoup(render(section, registry), 'html.parser')
    cell = article.select_one(f'[data-im-risk-row="{market}"] td:last-child')
    visible = kind in ('distinct', 'same', 'zero', 'stale', 'value_denied')
    supported = visible and kind != 'value_denied'
    observation = cell.select_one('[data-im-breadth-observation]')
    membership = cell.select_one('[data-im-breadth-membership]')
    assert (observation is not None) == visible
    assert (membership is not None) == supported
    if visible:
        assert observation.get_text() == 'Observation观测 2026-10-05'
    if supported:
        date = '2026-10-05' if kind == 'same' else '2026-09-30'
        assert membership.get_text() == 'Membership as of成员名单截至日期 ' + date
        assert cell.select_one('[data-im-risk-value]').get_text() == ('0' if kind == 'zero' else '+61')
        assert ('Stale data' in cell.get_text()) == (kind == 'stale')
    else:
        assert cell.select_one('[data-im-risk-value]') is None
        assert '2026-09-30' not in cell.get_text()
    # The calculation clock is not substituted for either displayed source clock.
    assert '2026-10-06' not in cell.get_text()
    assert '2026-10-07' not in cell.get_text()
    assert source == before


def render_breadth_clock_fixture():
    """Full publication/mount with native synthetic breadth inputs for six markets."""
    from unittest.mock import patch
    from engine.intl_inputs import countries
    from lib.intl_risk_mount import attach_risks
    from tests.test_intl_workspace_integration import render_history_fixture
    kinds = ('distinct', 'zero', 'stale', 'value_denied', 'metadata_denied', 'missing_membership')
    cases = [dict(market=market, kind=kind) for market, kind in zip(countries(), kinds)]
    assert len(cases) == len(kinds)
    measures, support = {}, {}
    for case in cases:
        key = case['market'] + '.constituent_breadth_50d'
        measures[key], support[key] = breadth_clock_input(case['kind'], case['market'])
    def mount(workspace, **kwargs):
        return attach_risks(workspace, **{**kwargs, 'measures': measures, 'field_support': support})
    with patch('scripts.build_intl.attach_risks', side_effect=mount):
        html = render_history_fixture(history_sources={})
    return dict(html=html, cases=cases)


ANNUAL_CLOCK_CASES = ('actual', 'estimate', 'projection', 'zero', 'stale',
                      'no_calculation', 'value_denied', 'metadata_denied',
                      'metadata_unknown', 'missing_observation', 'absent')


def annual_clock_input(kind, market='JP'):
    """Synthetic annual measure with distinct field year, vintage and clocks."""
    from tests.test_intl_workspace_risk_pressure import inputs
    source = inputs()
    key = 'JP.annual_current_account'
    measure, support = source['measures'][key], source['field_support'][key]
    measure['instrument']['market_id'] = market
    support.update(market_id=market, vintage='2026-07-30')
    measure.update(observation_at='2026-08-21', calculation_at='2026-08-22T05:00:00+00:00')
    if kind in ('estimate', 'projection'):
        support['observation_type'] = kind
        if kind == 'projection':
            support['field_year'] = 2027
            measure['period'].update(start='2027-01-01', end='2028-01-01')
    elif kind == 'zero':
        measure['value'] = 0
    elif kind == 'stale':
        measure.update(quality='stale', value=-1.25)
    elif kind == 'no_calculation':
        measure['calculation_at'] = None
    elif kind == 'value_denied':
        measure['value_permission'] = 'denied'
    elif kind.startswith('metadata_'):
        measure['metadata'] = kind.removeprefix('metadata_')
    elif kind == 'missing_observation':
        measure.update(quality='missing', value=None, observation_at=None)
    elif kind == 'absent':
        return None, None
    return measure, support


@pytest.mark.parametrize('kind', ANNUAL_CLOCK_CASES)
def test_annual_render_distinguishes_field_year_vintage_observation_and_calculation(kind):
    from bs4 import BeautifulSoup
    from lib.intl_workspace_risk_pressure import build_pressure_rows
    section, registry, _ = packet()
    market = registry['markets'][0]['market_id']
    measure, support = annual_clock_input(kind, market)
    key = market + '.annual_current_account'
    source = dict(registry=registry, measures={key: measure} if measure else {},
                  field_support={key: support} if support else {})
    before = copy.deepcopy(source)
    section['pressure_rows'] = build_pressure_rows(**source)
    cell = BeautifulSoup(render(section, registry), 'html.parser').select_one(f'[data-im-risk-row="{market}"] td:nth-of-type(3)')
    metadata = kind not in ('metadata_denied', 'metadata_unknown', 'absent')
    for attr, key, labels in (
        ('observation', 'observation_at', 'Observation观测'),
        ('calculation', 'calculation_at', 'Calculation time计算时间'),
    ):
        node = cell.select_one(f'[data-im-annual-{attr}]')
        expected = measure[key] if metadata else None
        assert (node is not None) == (expected is not None)
        if expected is not None:
            assert node.get_text() == labels + ' ' + expected
    supported = metadata and kind not in ('value_denied', 'missing_observation')
    if supported:
        assert 'Field year字段年份 ' + str(support['field_year']) in cell.get_text()
        assert 'Vintage版本 2026-07-30' in cell.get_text()
        label = {'actual': 'Actual实际', 'estimate': 'Estimate估计', 'projection': 'Projection预测'}[support['observation_type']]
        assert label in cell.get_text()
        value = cell.select_one('[data-im-risk-value]').get_text()
        assert value == ('0' if kind == 'zero' else '-1.25' if kind == 'stale' else '+3.4')
        assert ('Stale data' in cell.get_text()) == (kind == 'stale')
    else:
        assert cell.select_one('[data-im-risk-value]') is None
        assert '2026-07-30' not in cell.get_text()
    if kind == 'missing_observation':
        assert 'Missing data' in cell.get_text()
        assert '2026-08-21' not in cell.get_text()
    if not metadata:
        assert '2026-08' not in cell.get_text()
    assert source == before


def render_annual_clock_fixture():
    """Existing publication/mount path with explicit synthetic annual inputs."""
    from unittest.mock import patch
    from engine.intl_inputs import countries
    from lib.intl_risk_mount import attach_risks
    from tests.test_intl_workspace_integration import render_history_fixture
    kinds = ('actual', 'projection', 'no_calculation', 'stale', 'value_denied', 'missing_observation', 'metadata_denied')
    cases = [dict(market=market, kind=kind) for market, kind in zip(countries(), kinds)]
    assert len(cases) == len(kinds)
    measures, support = {}, {}
    for case in cases:
        key = case['market'] + '.annual_current_account'
        measures[key], support[key] = annual_clock_input(case['kind'], case['market'])
    def mount(workspace, **kwargs):
        return attach_risks(workspace, **{**kwargs, 'measures': measures, 'field_support': support})
    with patch('scripts.build_intl.attach_risks', side_effect=mount):
        html = render_history_fixture(history_sources={})
    return dict(html=html, cases=cases)


PRESSURE_EVIDENCE_FIELDS = ('country_credit_change', 'annual_current_account', 'constituent_breadth_50d')
PRESSURE_EVIDENCE_CASES = ('supplied', 'stale', 'value_denied', 'metadata_denied',
                           'metadata_unknown', 'invalid_support', 'missing',
                           'empty', 'source_only', 'evidence_only', 'hostile')


def pressure_evidence_input(field, kind, market='JP'):
    """Explicit synthetic native records; no production disclosure grant."""
    from tests.test_intl_workspace_risk_pressure import inputs
    source = inputs()
    measure = source['measures']['JP.' + field]
    support = source['field_support']['JP.' + field]
    measure['instrument']['market_id'] = market
    support['market_id'] = market
    measure['source_reference'] = 'source:' + market + ':' + field + ':' + 'x' * 96
    measure['evidence_key'] = 'evidence:' + market + ':' + field
    support['method_ref'] = 'method:' + market + ':' + field
    if kind == 'stale':
        measure['quality'] = 'stale'
    elif kind == 'value_denied':
        measure['value_permission'] = 'denied'
    elif kind.startswith('metadata_'):
        measure['metadata'] = kind.removeprefix('metadata_')
    elif kind == 'invalid_support':
        support['market_id'] = 'WRONG'
    elif kind in ('missing', 'empty', 'source_only', 'evidence_only'):
        measure.update(quality='missing', value=None)
        if kind in ('empty', 'evidence_only'):
            measure['source_reference'] = None
        if kind in ('empty', 'source_only'):
            measure['evidence_key'] = None
    elif kind == 'hostile':
        measure['source_reference'] = 'https://example.invalid/<img src=x onerror=alert(1)>'
        measure['evidence_key'] = 'javascript:alert(1) <script> & "evidence"'
        support['method_ref'] = '<svg onload=alert(1)> & method'
        if field == 'constituent_breadth_50d':
            support['membership_ref'] = '<iframe src=evil> & members'
    return measure, support


@pytest.mark.parametrize('field', PRESSURE_EVIDENCE_FIELDS)
@pytest.mark.parametrize('kind', PRESSURE_EVIDENCE_CASES)
def test_pressure_evidence_discloses_only_native_retained_references(field, kind):
    from bs4 import BeautifulSoup
    from lib.intl_workspace_risk_pressure import build_pressure_rows
    section, registry, _ = packet()
    market = registry['markets'][0]['market_id']
    measure, support = pressure_evidence_input(field, kind, market)
    key = market + '.' + field
    source = dict(registry=registry, measures={key: measure}, field_support={key: support})
    before = copy.deepcopy(source)
    section['pressure_rows'] = build_pressure_rows(**source)
    index = PRESSURE_EVIDENCE_FIELDS.index(field) + 2
    article = BeautifulSoup(render(section, registry), 'html.parser')
    cell = article.select_one(f'[data-im-risk-row="{market}"] td:nth-of-type({index})')
    evidence = cell.select_one('details.intl-risk__evidence')
    visible = kind not in ('metadata_denied', 'metadata_unknown', 'invalid_support', 'empty')
    assert (evidence is not None) == visible
    supported = kind in ('supplied', 'stale', 'hostile')
    if visible:
        expected = [measure[k] for k in ('source_reference', 'evidence_key') if measure[k]]
        if supported:
            expected.append(support['method_ref'])
            if field == 'constituent_breadth_50d':
                expected.append(support['membership_ref'])
        assert [dd.get_text() for dd in evidence.select('dd')] == expected
        assert evidence.select_one('summary .l-en') is not None
        assert evidence.select_one('summary .l-zh') is not None
        assert evidence.select('a,script,img,svg,iframe') == []
        assert not evidence.has_attr('open')
        if not supported:
            assert support['method_ref'] not in evidence.get_text()
    else:
        assert measure['source_reference'] is None or measure['source_reference'] not in cell.get_text()
    if supported:
        value = cell.select_one('[data-im-risk-value]')
        assert value.get_text() == ('0' if field == 'country_credit_change' else '+3.4' if field == 'annual_current_account' else '+61')
        assert ('Stale data' in cell.get_text()) == (kind == 'stale')
    else:
        assert cell.select_one('[data-im-risk-value]') is None
    assert source == before


def render_pressure_evidence_fixture():
    """Native projection and full mount; seven distinct synthetic disclosure states."""
    from unittest.mock import patch
    from engine.intl_inputs import countries
    from lib.intl_risk_mount import attach_risks
    from tests.test_intl_workspace_integration import render_history_fixture
    kinds = ('supplied', 'value_denied', 'metadata_denied', 'metadata_unknown',
             'invalid_support', 'empty', 'source_only')
    cases = [dict(market=market, kind=kind) for market, kind in zip(countries(), kinds)]
    assert len(cases) == len(kinds)
    measures, support = {}, {}
    for case in cases:
        for field in PRESSURE_EVIDENCE_FIELDS:
            key = case['market'] + '.' + field
            measures[key], support[key] = pressure_evidence_input(field, case['kind'], case['market'])
    def mount(workspace, **kwargs):
        return attach_risks(workspace, **{**kwargs, 'measures': measures, 'field_support': support})
    with patch('scripts.build_intl.attach_risks', side_effect=mount):
        html = render_history_fixture(history_sources={})
    return dict(html=html, cases=cases, fields=PRESSURE_EVIDENCE_FIELDS)
