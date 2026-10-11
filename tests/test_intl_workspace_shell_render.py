import copy
import pathlib
import re
from html.parser import HTMLParser

import pytest
from jinja2 import Environment, FileSystemLoader


UNKNOWN_OVERVIEW = {
    "context": {"horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price", "source_reference": None, "source_reference_reason": "not_disclosed_or_unknown"},
    "configured_count": 7, "eligible_count": 0, "ranking_count": 0, "ranking_status": "unavailable",
    "ranking_reason": "no_qualified_returns", "focus_ids": [],
    "rows": [{"slot": index, "market_id": f"M{index}", "name_en": f"Market {index}", "name_zh": f"市场{index}", "quality": "unknown", "reason": "metadata_incomplete", "metric": {"value": None, "unit": "percent", "quality": "unknown", "reason": "metadata_incomplete"}} for index in range(7)],
    "summary": {"kind": "unavailable", "highest_market_id": None, "lowest_market_id": None, "positive_count": None, "fx_detracted_count": None, "fx_eligible_count": 0, "reason": "no_qualified_returns"},
}

AVAILABLE_OVERVIEW = {
    "context": {"horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price", "source_reference": "fixture:owner-input", "source_reference_reason": None},
    "configured_count": 2, "eligible_count": 2, "ranking_count": 2, "ranking_status": "available",
    "ranking_reason": None, "focus_ids": ["JP", "GB"],
    "rows": [
        {"slot": 0, "market_id": "JP", "name_en": "Market JP", "name_zh": "市场JP", "index_id": "^N225", "index_label": "Nikkei 225", "metric": {"value": 3.5, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "local": {"value": 3.5, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "usd": {"value": 3.5, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "fx_contribution": {"value": 0.0, "unit": "percentage_points", "quality": "qualified", "reason": None, "window": None}},
        {"slot": 1, "market_id": "GB", "name_en": "Market GB", "name_zh": "市场GB", "index_id": "^FTSE", "index_label": "FTSE 100", "metric": {"value": -1.25, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "local": {"value": -1.25, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "usd": {"value": -1.25, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "fx_contribution": {"value": -2.5, "unit": "percentage_points", "quality": "qualified", "reason": None, "window": None}},
    ],
    "summary": {"kind": "highest_lowest_returns", "highest_market_id": "JP", "lowest_market_id": "GB", "positive_count": 1, "fx_detracted_count": 1, "fx_eligible_count": 2, "reason": None},
}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = ""

    def classes(self):
        return self.attrs.get("class", "").split()


class SemanticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", [])
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, attrs, self.current))

    def handle_data(self, data):
        self.current.text += data

    def handle_endtag(self, tag):
        current = self.current
        while current != self.root and current.tag != tag:
            current = current.parent
        if current != self.root:
            self.current = current.parent


def parse(html):
    parser = SemanticHTML()
    parser.feed(html)
    return parser.root


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def nodes(root, attr, value=None):
    return [node for node in walk(root) if attr in node.attrs and (value is None or node.attrs[attr] == value)]


def one(root, attr, value=None):
    found = nodes(root, attr, value)
    assert len(found) == 1, (attr, value, len(found))
    return found[0]


def visible_text(node):
    return node.text + "".join(visible_text(child) for child in node.children)


def shell_payload(overview):
    return {
        "config": {
            "markets": ["JP", "KR", "TW", "IN", "AU", "GB", "EZ"],
            "horizons": ["1m", "3m"],
            "bases": ["local", "usd_unhedged"],
            "default_horizon": "1m",
            "default_basis": "usd_unhedged",
            "source_reference": None,
            "anchor_ids": ["intl-legacy-research"],
            "library_group_ids": [],
        },
        "panels": [{"overview": overview, "context_id": "p", "generation": ""}],
    }


def rendered_shell(overview):
    template_root = pathlib.Path(__file__).resolve().parent.parent / "templates"
    environment = Environment(
        autoescape=False,
        loader=FileSystemLoader([template_root, template_root / "intl_workspace"]),
    )
    environment.globals["t"] = lambda en, zh: f'<span class="l-en">{en}</span><span class="l-zh" lang="zh">{zh}</span>'
    html = environment.get_template("intl_workspace/shell.html.j2").render(intl_workspace=shell_payload(overview))
    return html, parse(html)


CSS_PATH = pathlib.Path(__file__).resolve().parent.parent / "templates" / "intl_workspace.css"


def test_shell_header_is_eyebrow_title_purpose_with_no_fake_actions():
    html, root = rendered_shell(AVAILABLE_OVERVIEW)
    header = one(root, "class", "intl-workspace__header")
    eyebrow = one(root, "class", "intl-workspace__eyebrow")
    assert "INTERNATIONAL RESEARCH" in visible_text(eyebrow) and "国际研究" in visible_text(eyebrow)
    heading = one(root, "data-im-heading")
    assert heading.tag == "h1" and heading.attrs["id"] == "intl-workspace-title"
    assert header.children[0] is eyebrow and header.children[1] is heading
    assert len([node for node in walk(root) if node.tag == "h1"]) == 1
    assert any("intl-workspace__purpose" in node.classes() for node in header.children)
    for forbidden in ("saved research", "export", "benchmark"):
        assert forbidden not in html.lower()


def test_desktop_tabs_and_controls_are_separate_rows_with_public_count():
    html, root = rendered_shell(AVAILABLE_OVERVIEW)
    nav = one(root, "class", "intl-workspace__view-nav")
    controls = one(root, "class", "intl-workspace__controls")
    toolbar = one(root, "data-im-controls")
    assert toolbar.children.index(nav) < toolbar.children.index(controls)
    tabs = [node for node in nav.children if node.tag == "button"]
    assert len(tabs) == 6
    assert all(node.attrs.get("data-im-action") == "set_view" for node in tabs)
    assert [node.attrs["data-im-view"] for node in tabs][0] == "overview"
    assert all(tab not in controls.children for tab in tabs)
    selects = [node for node in walk(controls) if node.tag == "select"]
    actions = sorted(node.attrs["data-im-action"] for node in selects)
    assert actions == ["set_basis", "set_horizon", "set_view"]
    context_line = one(root, "class", "intl-workspace__context-line")
    assert "7 covered markets" in visible_text(context_line)
    assert "Price return" in visible_text(context_line)
    assert "覆盖市场 7 个" in visible_text(context_line) and "价格回报" in visible_text(context_line)
    options = [node for node in walk(one(root, "class", "intl-workspace__view-select")) if node.tag == "option"]
    assert len(options) == 6


def test_controller_dom_contract_survives_the_shell_repair():
    html, root = rendered_shell(AVAILABLE_OVERVIEW)
    assert one(root, "data-im-heading")
    assert one(root, "data-im-issues").attrs.get("role") == "status"
    unavailable = one(root, "data-im-unavailable")
    assert "hidden" in unavailable.attrs
    assert one(root, "data-im-panel").attrs["data-view"] == "overview"
    trigger = one(root, "data-im-expansion-trigger")
    assert trigger.attrs["data-im-action"] == "set_expanded"
    region = one(root, "data-im-expanded-region")
    assert trigger.attrs["aria-controls"] == region.attrs["id"]
    assert "hidden" in trigger.attrs
    config = one(root, "data-im-config")
    assert config.tag == "script" and config.attrs.get("type") == "application/json"
    assert '"markets"' in visible_text(config)


def test_deeper_strip_uses_existing_anchors_once_without_duplicate_ids():
    html, root = rendered_shell(AVAILABLE_OVERVIEW)
    strip = one(root, "class", "intl-workspace__deeper")
    links = [node for node in walk(strip) if node.tag == "a"]
    assert [node.attrs["href"] for node in links] == ["#intl-legacy-research", "intl_stocks.html"]
    assert not nodes(strip, "data-im-action")
    identifiers = [node.attrs["id"] for node in walk(root) if "id" in node.attrs]
    assert len(identifiers) == len(set(identifiers))


def test_unavailable_state_keeps_composed_summary_and_coverage_panel():
    fixture = copy.deepcopy(UNKNOWN_OVERVIEW)
    fixture["rows"][3] = {"slot": 3, "quality": "denied", "reason": "metadata_denied", "market_id": "SECRET", "name_en": "Secret Name", "name_zh": "秘密", "index_id": "SECRET-INDEX", "metric": {"value": 99}}
    html, root = rendered_shell(fixture)
    summary = one(root, "data-im-summary")
    assert "Current returns unavailable" in visible_text(summary)
    assert "Comparable current returns cannot be shown" in visible_text(summary)
    assert "无法显示可比的当前回报" in visible_text(summary)
    coverage = one(root, "data-im-coverage")
    rows = [node for node in walk(coverage) if "intl-overview__coverage-row" in node.classes()]
    assert len(rows) == 7
    withheld = [row for row in rows if "intl-overview__coverage-row--withheld" in row.classes()]
    assert len(withheld) == 1 and "SECRET" not in html and "Secret Name" not in html and "99" not in html
    assert not nodes(root, "data-im-focus-item")
    for forbidden in ("retry", "cached", "last retrieved", "重试", "缓存"):
        assert forbidden not in html.lower()
    trigger = one(root, "data-im-expansion-trigger")
    assert trigger.attrs["aria-controls"] == one(root, "data-im-expanded-region").attrs["id"]
    legacy = [node for node in walk(root) if node.tag == "a" and node.attrs.get("href") == "#intl-legacy-research"]
    assert len(legacy) == 1


def test_available_state_composes_summary_stats_and_focus_footer():
    html, root = rendered_shell(AVAILABLE_OVERVIEW)
    assert not nodes(root, "data-im-coverage")
    focus = one(root, "data-im-focus")
    stats = nodes(root, "class", "intl-overview__stats")
    assert len(stats) == 1
    values = [node.text.strip() for node in walk(stats[0]) if node.tag == "dd"]
    assert values == ["1 / 2", "1 / 2"]
    footer = one(root, "class", "intl-overview__focus-footer")
    trigger = one(root, "data-im-expansion-trigger")
    assert trigger.parent is footer
    assert "hidden" in trigger.attrs
    ordered = [node.attrs["data-market-id"] for node in nodes(root, "data-im-focus-item")]
    assert ordered == ["JP", "GB"]
    returns = nodes(root, "data-im-return")
    assert "+3.50%" in visible_text(returns[0]) and "-1.25%" in visible_text(returns[1])
    assert "intl-overview__return--up" in returns[0].classes()
    assert "intl-overview__return--down" in returns[1].classes()


def test_shell_preserves_bilingual_pairing_and_panel_title_semantics():
    html, root = rendered_shell(AVAILABLE_OVERVIEW)
    en = len(nodes(root, "class", "l-en"))
    zh = len(nodes(root, "class", "l-zh"))
    assert en == zh and en > 0
    title = one(root, "id", "p-title")
    assert title.tag == "h2"
    assert "intl-overview__panel-title" in title.classes()
    assert one(root, "data-im-panel").attrs["aria-labelledby"] == "p-title"


def test_css_keeps_token_discipline_and_tab_underline_treatment():
    css = CSS_PATH.read_text(encoding="utf-8")
    overview_block = css.split("/* Inspector:")[0]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", overview_block)
    assert "--intl" not in css
    assert "minmax(0,38fr) minmax(0,62fr)" in css
    nav_rule = re.search(r"\.intl-workspace__view-nav button\[aria-pressed=\"true\"\] \{[^}]*\}", css)
    assert nav_rule and "border-block-end-color" in nav_rule.group(0) and "background:transparent" in nav_rule.group(0)
    # Other views retain their incumbent selected-button treatment.
    assert '.intl-workspace button[aria-pressed="true"] { background:var(--panel); border-color:var(--link); }' in css
    assert '[data-theme="light"] .intl-workspace button[aria-pressed="true"] { background:var(--panel2); }' in css
    for selector in (".intl-overview__coverage", ".intl-overview__focus-footer", ".intl-workspace__deeper", ".intl-overview__stats"):
        assert selector in css
    assert "var(--ink-up)" in css and "var(--ink-down)" in css
    for frozen_owner in (".intl-library", ".intl-inspector", ".intl-compare"):
        assert frozen_owner in css
