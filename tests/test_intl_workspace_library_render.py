import copy
import json
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_JSON = r'''{
  "catalogue_state": "available",
  "catalogue_generation": "public-copy:sha256:99f66113903884058b1f1f67790f43fec78872a1bfab23d8ce53121d6de29331",
  "context": {"research_market": "JP", "horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price", "source_reference": null},
  "groups": [
    {"slot": 0, "id": "leaders", "label_en": "Find the leaders", "label_zh": "寻找领涨者", "tool_keys": ["performance_currency", "leadership_rotation", "cross_country"]},
    {"slot": 1, "id": "recovery", "label_en": "Check the recovery", "label_zh": "检查修复", "tool_keys": ["market_turns", "recovery_quality", "participation_concentration"]},
    {"slot": 2, "id": "policy", "label_en": "Follow policy divergence", "label_zh": "跟踪政策分化", "tool_keys": ["rates_curves_carry", "central_banks_liquidity", "credit_bonds"]},
    {"slot": 3, "id": "backdrop", "label_en": "Understand the backdrop", "label_zh": "理解背景", "tool_keys": ["euro_fragmentation", "growth_inflation", "dollar_conditions"]},
    {"slot": 4, "id": "pressure", "label_en": "Trace the pressure", "label_zh": "追踪压力", "tool_keys": ["structural_fragility", "contagion", "trade_supply_links"]},
    {"slot": 5, "id": "challenge", "label_en": "Challenge the conclusion", "label_zh": "检验结论", "tool_keys": ["cross_market_correlation", "risk_track_record", "country_sectors_stocks"]}
  ],
  "tools": [
    {"presentation_key": "performance_currency", "group_id": "leaders", "order": 0, "label_en": "Performance & currency", "label_zh": "表现与汇率", "question_en": "Find the leaders", "question_zh": "寻找领涨者", "aliases": ["currency", "returns", "FX", "USD", "回报", "汇率"], "research_market": "JP", "analytical_scope": "seven-market", "analytical_market": null, "route_state": "available", "data_state": "unknown", "target": {"page_id": "macro:intl", "route": "/intl.html", "region_id": "fixture-performance"}, "reason": null, "metrics": [], "interpretation_notice": null},
    {"presentation_key": "leadership_rotation", "group_id": "leaders", "order": 1, "label_en": "Leadership rotation", "label_zh": "领涨轮动", "question_en": "Find the leaders", "question_zh": "寻找领涨者", "aliases": ["rank", "momentum", "排名", "动量", "轮动"], "research_market": "JP", "analytical_scope": "seven-market; not capital flow", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "cross_country", "group_id": "leaders", "order": 2, "label_en": "Cross-country comparison", "label_zh": "跨经济体比较", "question_en": "Find the leaders", "question_zh": "寻找领涨者", "aliases": ["country", "economy", "comparison", "经济体", "比较"], "research_market": "JP", "analytical_scope": "seven-market", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "market_turns", "group_id": "recovery", "order": 3, "label_en": "Market turns", "label_zh": "市场转折", "question_en": "Check the recovery", "question_zh": "检查修复", "aliases": ["trend", "repair", "turns", "拐点", "趋势", "修复"], "research_market": "JP", "analytical_scope": "world-context plus core; preserve cohort", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "recovery_quality", "group_id": "recovery", "order": 4, "label_en": "Recovery quality", "label_zh": "修复质量", "question_en": "Check the recovery", "question_zh": "检查修复", "aliases": ["recovery", "confirmation", "quality", "修复", "确认"], "research_market": "JP", "analytical_scope": "owner profile; partial coverage", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "participation_concentration", "group_id": "recovery", "order": 5, "label_en": "Participation & concentration", "label_zh": "参与度与集中度", "question_en": "Check the recovery", "question_zh": "检查修复", "aliases": ["breadth", "constituents", "广度", "成分股", "集中度"], "research_market": "JP", "analytical_scope": "owner profile; no invented breadth", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "rates_curves_carry", "group_id": "policy", "order": 6, "label_en": "Rates, curves & carry", "label_zh": "利率、曲线与息差", "question_en": "Follow policy divergence", "question_zh": "跟踪政策分化", "aliases": ["rates", "yield", "curve", "carry", "利率", "收益率", "曲线", "息差"], "research_market": "JP", "analytical_scope": "seven-market plus US anchor", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "central_banks_liquidity", "group_id": "policy", "order": 7, "label_en": "Central banks & liquidity", "label_zh": "央行与流动性", "question_en": "Follow policy divergence", "question_zh": "跟踪政策分化", "aliases": ["central", "banks", "policy", "liquidity", "央行", "政策", "流动性"], "research_market": "JP", "analytical_scope": "central-bank roster; proxies labeled", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "credit_bonds", "group_id": "policy", "order": 8, "label_en": "Credit & bonds", "label_zh": "信用与债券", "question_en": "Follow policy divergence", "question_zh": "跟踪政策分化", "aliases": ["credit", "bonds", "spreads", "信用", "债券", "利差"], "research_market": "JP", "analytical_scope": "sovereign and EM regional; not country-credit substitute", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "euro_fragmentation", "group_id": "backdrop", "order": 9, "label_en": "Euro-area fragmentation", "label_zh": "欧元区分化", "question_en": "Understand the backdrop", "question_zh": "理解背景", "aliases": ["euro", "fragmentation", "欧元区", "分化"], "research_market": "JP", "analytical_scope": "EZ regional context; preserve Japan on return", "analytical_market": "EZ", "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "growth_inflation", "group_id": "backdrop", "order": 10, "label_en": "Growth & inflation", "label_zh": "增长与通胀", "question_en": "Understand the backdrop", "question_zh": "理解背景", "aliases": ["growth", "inflation", "cycle", "GDP", "CPI", "增长", "通胀", "周期"], "research_market": "JP", "analytical_scope": "qualified core; unclassified visible", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "dollar_conditions", "group_id": "backdrop", "order": 11, "label_en": "Dollar conditions", "label_zh": "美元环境", "question_en": "Understand the backdrop", "question_zh": "理解背景", "aliases": ["dollar", "funding", "USD", "美元", "融资"], "research_market": "JP", "analytical_scope": "global context; distinguish source families", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "structural_fragility", "group_id": "pressure", "order": 12, "label_en": "Structural fragility", "label_zh": "结构性脆弱性", "question_en": "Trace the pressure", "question_zh": "追踪压力", "aliases": ["fragility", "debt", "current", "account", "脆弱", "债务", "经常账户"], "research_market": "JP", "analytical_scope": "IMF country roster; qualified vintage", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "contagion", "group_id": "pressure", "order": 13, "label_en": "Contagion", "label_zh": "传导", "question_en": "Trace the pressure", "question_zh": "追踪压力", "aliases": ["contagion", "spillover", "transmission", "传导", "溢出"], "research_market": "JP", "analytical_scope": "distinct statistical and EM-US methods", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "trade_supply_links", "group_id": "pressure", "order": 14, "label_en": "Trade & supply links", "label_zh": "贸易与供应链联系", "question_en": "Trace the pressure", "question_zh": "追踪压力", "aliases": ["trade", "supply", "chain", "exposure", "贸易", "供应链", "敞口"], "research_market": "JP", "analytical_scope": "model context is not documented company exposure", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": "model_context_not_company_exposure"},
    {"presentation_key": "cross_market_correlation", "group_id": "challenge", "order": 15, "label_en": "Cross-market correlation", "label_zh": "跨市场相关性", "question_en": "Challenge the conclusion", "question_zh": "检验结论", "aliases": ["correlation", "diversification", "相关性", "分散"], "research_market": "JP", "analytical_scope": "qualified weekly USD population; not causality", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "risk_track_record", "group_id": "challenge", "order": 16, "label_en": "Risk-radar track record", "label_zh": "风险雷达记录", "question_en": "Challenge the conclusion", "question_zh": "检验结论", "aliases": ["track", "record", "false", "alarms", "accuracy", "记录", "误报", "验证"], "research_market": "JP", "analytical_scope": "market profile; sample and authority gate", "analytical_market": null, "route_state": "unavailable", "data_state": "unknown", "target": null, "reason": "missing_target", "metrics": [], "interpretation_notice": null},
    {"presentation_key": "country_sectors_stocks", "group_id": "challenge", "order": 17, "label_en": "Country sectors & stocks", "label_zh": "经济体板块与股票", "question_en": "Challenge the conclusion", "question_zh": "检验结论", "aliases": ["sectors", "stocks", "industry", "板块", "股票", "行业"], "research_market": "JP", "analytical_scope": "existing stock universe; no assumed market filter", "analytical_market": null, "route_state": "available", "data_state": "unknown", "target": {"page_id": "macro:intl_stocks", "route": "/intl_stocks.html", "region_id": null}, "reason": null, "metrics": [], "interpretation_notice": null}
  ],
  "search_catalogue": [],
  "exclusions": [],
  "catalogue_source_reference": "public-copy:sha256:99f66113903884058b1f1f67790f43fec78872a1bfab23d8ce53121d6de29331"
}'''
PAYLOAD = json.loads(PAYLOAD_JSON)
PAYLOAD["search_catalogue"] = [
    {key: copy.deepcopy(tool[key]) for key in ("presentation_key", "group_id", "order", "label_en", "label_zh", "question_en", "question_zh", "aliases")}
    for tool in PAYLOAD["tools"]
]


class CaptureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.elements = []
        self.depth = 0
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append({"tag": tag, "attrs": attrs, "text": ""})
        if tag not in {"br", "img", "input", "meta", "link", "hr"}:
            self.depth += 1
            self.capture = len(self.elements) - 1 if self.depth == 1 else self.capture

    def handle_data(self, data):
        if self.capture is not None:
            self.elements[self.capture]["text"] += data

    def handle_endtag(self, tag):
        if tag not in {"br", "img", "input", "meta", "link", "hr"}:
            self.depth -= 1
        if self.depth == 0:
            self.capture = None


def render(payload, context_id="ctx"):
    environment = Environment(
        loader=FileSystemLoader(ARTIFACT_ROOT / "templates"),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )
    environment.autoescape = False
    template = environment.get_template("intl_workspace/library.html.j2")
    return template.render(payload=payload, context_id=context_id)


def parse(html):
    parser = CaptureParser()
    parser.feed(html)
    return parser.elements


def text(html):
    return unescape(html)


def test_no_js_initial_state_is_disabled_and_rows_visible():
    html = render(PAYLOAD)
    assert 'form data-im-library-search-form role="search"' in html.replace('class="intl-library__search" ', "")
    assert '<input type="search" data-im-library-search' in html and "disabled" in html
    assert '<button type="button" data-im-library-clear disabled>' in html
    assert 'data-im-library-status role="status" aria-live="polite"' in html
    assert 'data-im-library-results hidden' in html and 'data-im-library-empty hidden' in html
    assert 'data-im-library-back data-im-action="set_library_group" hidden' in html
    assert "data-im-group" not in html[html.index("data-im-library-back") : html.index("</button>", html.index("data-im-library-back"))]
    assert html.count("data-im-library-tool=") == 18


def test_full_payload_has_six_ordered_groups_and_eighteen_ordered_rows():
    html = render(PAYLOAD)
    assert [group.split('"')[0] for group in _attr_sequence(html, "data-im-library-group=")] == ["leaders", "recovery", "policy", "backdrop", "pressure", "challenge"]
    assert [int(order) for order in _attr_sequence(html, "data-im-library-order=")] == list(range(18))


def _attr_sequence(html, prefix):
    result = []
    position = 0
    while True:
        start = html.find(prefix, position)
        if start < 0:
            return result
        value_start = start + len(prefix) + 1
        end = html.find(html[value_start - 1], value_start)
        result.append(html[value_start:end])
        position = end + 1


def test_actual_targets_use_route_and_region_without_stock_query():
    html = render(PAYLOAD)
    assert 'href="#fixture-performance"' in html
    assert 'href="/intl_stocks.html"' in html
    assert "/intl_stocks.html?" not in html
    links = [element["attrs"].get("href") for element in parse(html) if element["tag"] == "a"]
    assert links == ["#fixture-performance", "/intl_stocks.html"]


def test_unavailable_targets_are_plain_text_and_catalogue_has_permitted_fields():
    html = render(PAYLOAD)
    assert html.count(">This tool’s destination is not available yet.<") == 16
    assert html.count(">此工具的目标页面暂不可用。<") == 16
    script_start = html.index('<script type="application/json" data-im-library-catalogue>') + len('<script type="application/json" data-im-library-catalogue>')
    script_end = html.index("</script>", script_start)
    catalogue = json.loads(html[script_start:script_end])
    assert len(catalogue) == 18
    assert all(set(row) == {"presentation_key", "group_id", "order", "label_en", "label_zh", "question_en", "question_zh", "aliases"} for row in catalogue)


def test_hostile_dynamic_values_and_closing_script_are_escaped():
    payload = copy.deepcopy(PAYLOAD)
    payload["catalogue_generation"] = 'gen" onmouseover="alert(1)'
    payload["tools"][0]["label_en"] = '</span><script>alert(1)</script>'
    payload["tools"][0]["label_zh"] = '" onclick="alert(1)'
    payload["tools"][0]["aliases"].append('</script>')
    payload["tools"][0]["analytical_scope"] = '<img src=x onerror=alert(1)>'
    html = render(payload)
    assert '<script>alert(1)</script>' not in html
    assert '<img src=x onerror=alert(1)>' not in html
    assert '&lt;/span&gt;&lt;script&gt;' in html
    assert 'data-im-library-generation="gen&#34; onmouseover=&#34;alert(1)"' in html


def test_context_ids_and_null_source_vs_generation_are_distinct():
    first = render(PAYLOAD, "first")
    second = render(PAYLOAD, "second")
    assert 'data-source=""' in first and first.index('data-source=""') < first.index('data-im-library-generation="public-copy')
    first_ids = [element["attrs"]["id"] for element in parse(first) if "id" in element["attrs"]]
    second_ids = [element["attrs"]["id"] for element in parse(second) if "id" in element["attrs"]]
    assert len(first_ids) == len(set(first_ids)) and len(second_ids) == len(set(second_ids))
    assert all(item.startswith(("first-", "second-")) for item in first_ids + second_ids)
    assert not set(first_ids) & set(second_ids)


def test_partial_payload_renders_only_supplied_metadata():
    payload = {
        "catalogue_state": "available",
        "catalogue_generation": "partial-generation",
        "context": PAYLOAD["context"],
        "groups": [{"slot": 0, "id": "leaders", "label_en": "Find the leaders", "label_zh": "寻找领涨者", "tool_keys": ["performance_currency"]}],
        "tools": [PAYLOAD["tools"][0]],
        "search_catalogue": [PAYLOAD["search_catalogue"][0]],
        "exclusions": [],
        "catalogue_source_reference": PAYLOAD["catalogue_source_reference"],
    }
    html = render(payload)
    assert html.count("data-im-library-group=") == 1 and "data-im-library-group=\"leaders\"" in html
    assert html.count("data-im-library-tool=") == 1 and 'data-im-library-tool="performance_currency"' in html
    assert "Leadership rotation" not in html and "领涨轮动" not in html
    assert "Check the recovery" not in html and "检查修复" not in html
    assert html.count("data-im-library-order=") == 1


def test_bilingual_pairs_and_css_prefix_are_preserved():
    html = render(PAYLOAD)
    assert text("Find a research tool for your question.") in html and "按研究问题查找工具。" in html
    assert "Euro-area context; research market unchanged" in html and "欧元区背景；研究市场保持不变" in html
    assert "Model context, not company exposure" in html and "模型背景，并非公司敞口" in html
    assert "Saved" not in html and "Coverage" not in html
    for row_start in [index for index in range(len(html)) if html.startswith("<li ", index) and "data-im-library-tool" in html[index : index + 100]]:
        row = html[row_start : html.index("</li>", row_start)]
        assert 'class="l-en">' in row and 'class="l-zh">' in row
    css = (ARTIFACT_ROOT / "templates/intl_workspace.css").read_text()
    prefix_end = css.index("@media (max-width:390px)")
    supplied_prefix = "/* Scoped Overview design source. Shared shell, locale and legacy owners remain separate. */"
    assert css.startswith(supplied_prefix)
    assert ".intl-library" not in css[:prefix_end]
    assert ".intl-library" in css[prefix_end:]
