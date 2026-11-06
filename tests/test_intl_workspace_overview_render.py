import copy
import pathlib
import re
from html.parser import HTMLParser

import pytest
from jinja2 import Environment, FileSystemLoader


SOURCE = {
    "unknown": {
        "context": {"horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price", "source_reference": None, "source_reference_reason": "not_disclosed_or_unknown"},
        "configured_count": 7, "eligible_count": 0, "ranking_count": 0, "ranking_status": "unavailable",
        "ranking_reason": "no_qualified_returns", "focus_ids": [],
        "rows": [{"slot": index, "market_id": f"M{index}", "name_en": f"Market {index}", "name_zh": f"市场{index}", "quality": "unknown", "reason": "metadata_incomplete", "metric": {"value": None, "unit": "percent", "quality": "unknown", "reason": "metadata_incomplete"}} for index in range(7)],
        "summary": {"kind": "unavailable", "highest_market_id": None, "lowest_market_id": None, "positive_count": None, "fx_detracted_count": None, "fx_eligible_count": 0, "reason": "no_qualified_returns"},
    },
    "positive": {
        "context": {"horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price", "source_reference": "fixture:owner-input", "source_reference_reason": None},
        "configured_count": 2, "eligible_count": 2, "ranking_count": 2, "ranking_status": "available",
        "ranking_reason": None, "focus_ids": ["JP", "GB"],
        "rows": [
            {"slot": 0, "market_id": "JP", "name_en": "Market JP", "name_zh": "市场JP", "index_id": "^N225", "index_label": "Nikkei 225", "metric": {"value": 19.449397, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "local": {"value": 19.449397, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "usd": {"value": 19.449397, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "fx_contribution": {"value": 0.0, "unit": "percentage_points", "quality": "qualified", "reason": None, "window": None}},
            {"slot": 1, "market_id": "GB", "name_en": "Market GB", "name_zh": "市场GB", "index_id": "^FTSE", "index_label": "FTSE 100", "metric": {"value": -12.306610, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "local": {"value": -12.306610, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "usd": {"value": -12.306610, "unit": "percent", "quality": "qualified", "reason": None, "window": None}, "fx_contribution": {"value": -31.751054, "unit": "percentage_points", "quality": "qualified", "reason": None, "window": None}},
        ],
        "summary": {"kind": "highest_lowest_returns", "highest_market_id": "JP", "lowest_market_id": "GB", "positive_count": 1, "fx_detracted_count": 1, "fx_eligible_count": 2, "reason": None},
    },
}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = ""


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


def rendered(overview, prefix="p"):
    assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", prefix)
    template_root = pathlib.Path(__file__).resolve().parent.parent / "templates" / "intl_workspace"
    environment = Environment(autoescape=False, loader=FileSystemLoader(template_root))
    html = environment.get_template("overview.html.j2").render(context_id=prefix, overview=overview)
    return html, parse(html)


def metric_row(slot, market_id, selected, local=None, usd=None, fx=None, index_id=None, index_label=None, quality="qualified", window=None):
    local = selected if local is None else local
    usd = selected if usd is None else usd
    fx = 0.0 if fx is None else fx
    def metric(value, unit="percent", reason=None):
        return {"value": value, "unit": unit, "quality": quality, "reason": reason, "window": copy.deepcopy(window)}
    return {"slot": slot, "market_id": market_id, "name_en": f"Name {market_id}", "name_zh": f"名称{market_id}", "index_id": index_id, "index_label": index_label, "metric": metric(selected), "local": metric(local), "usd": metric(usd), "fx_contribution": metric(fx, "percentage_points")}


def projection(rows, focus_ids=None, eligible=None, source="fixture:test", horizon="1m", basis="usd_unhedged", available=True):
    eligible = len(rows) if eligible is None else eligible
    focus_ids = [row["market_id"] for row in rows] if focus_ids is None else focus_ids
    highest = focus_ids[0] if focus_ids else None
    lowest = focus_ids[-1] if focus_ids else None
    positive = sum((row.get("metric", {}).get("value") or 0) > 0 for row in rows)
    detracted = sum((row.get("fx_contribution", {}).get("value") or 0) < 0 for row in rows)
    return {"context": {"horizon": horizon, "currency_basis": basis, "return_basis": "price", "source_reference": source, "source_reference_reason": None}, "configured_count": len(rows), "eligible_count": eligible, "ranking_count": len(focus_ids), "ranking_status": "available" if available else "unavailable", "ranking_reason": None if available else "no_qualified_returns", "focus_ids": focus_ids, "rows": rows, "summary": {"kind": "highest_lowest_returns" if available else "unavailable", "highest_market_id": highest, "lowest_market_id": lowest, "positive_count": positive if available else None, "fx_detracted_count": detracted if available else None, "fx_eligible_count": eligible, "reason": None}}


def ordered_focus_ids(root):
    return [node.attrs["data-market-id"] for node in nodes(root, "data-im-focus-item")]


def test_sample_unknown_plain_bilingual_full_roster_and_empty_source():
    fixture = copy.deepcopy(SOURCE["unknown"])
    html, root = rendered(fixture, "empty-source")
    assert one(root, "data-source").attrs["data-source"] == ""
    assert "Current returns unavailable当前回报不可用" in visible_text(one(root, "data-im-summary"))
    assert len([node for node in walk(root) if node.tag == "article" and "__market" in node.attrs.get("class", "").split()]) == 7
    assert all("metadata_incomplete" not in html and "no_qualified_returns" not in html for _ in [0])
    assert len(nodes(root, "data-im-focus-item")) == 0
    assert not nodes(root, "data-im-index")
    assert not nodes(root, "data-im-window")
    assert one(root, "data-im-panel").attrs["data-source"] == ""


def test_hostile_autoescape_false_is_explicitly_escaped():
    payload = '"><img src=x onerror=alert(1)>'
    fixture = projection([metric_row(0, payload, 1.0, index_id=payload, index_label=payload)])
    fixture["context"]["source_reference"] = payload
    fixture["rows"][0]["metric"]["window"] = {"start": payload + "a", "end": payload + "b", "calendar_policy": "owner", "endpoint_observations": {}}
    fixture["context"]["horizon"] = payload
    html, root = rendered(fixture, "hostile")
    assert "<img" not in html
    assert not any(node.tag == "img" for node in walk(root))
    assert "&#34;&gt;&lt;img" in html
    assert one(root, "data-source").attrs["data-source"] == payload
    assert one(root, "data-im-window").attrs.get("data-x") is None
    horizon_nodes = [node for node in one(root, "class", "intl-overview__context").children if "l-en" in node.attrs.get("class", "").split()]
    assert horizon_nodes[1].text == payload


def test_all_market_heading_and_focus_names_use_language_pairs():
    fixture = copy.deepcopy(SOURCE["positive"])
    _, root = rendered(fixture, "language")
    markets = one(root, "data-im-expanded-region")
    assert markets.attrs["aria-labelledby"] == "language-markets-title"
    assert one(root, "id", "language-markets-title").attrs["id"] == markets.attrs["aria-labelledby"]
    for focus in nodes(root, "data-im-focus-item"):
        name = one(focus, "class", "intl-overview__market-name")
        pairs = [(node.attrs.get("lang"), visible_text(node)) for node in name.children]
        assert pairs == [(None, "Market JP"), ("zh", "市场JP")] or pairs == [(None, "Market GB"), ("zh", "市场GB")]


def test_denied_slot_only_and_recursive_leakage_blocked():
    row = {"slot": 3, "quality": "denied", "reason": "metadata_denied", "market_id": "SECRET", "name_en": "Secret Name", "name_zh": "秘密", "index_id": "SECRET-INDEX", "metric": {"value": 99}}
    fixture = projection([row], available=False, eligible=0)
    html, root = rendered(fixture, "denied")
    assert "SECRET" not in html and "Secret Name" not in html and "秘密" not in html
    assert "99" not in html
    assert len(nodes(root, "data-im-market-denied")) == 1
    assert one(root, "data-im-market-denied").attrs["id"] == "denied-market-3"


def test_focus_counts_and_exact_order_with_displayed_ties():
    rows = [metric_row(index, f"M{index}", 2.0 + (0.01 if index == 1 else 0)) for index in range(7)]
    ordered = sorted(rows, key=lambda row: row["metric"]["value"], reverse=True)
    expected = [row["market_id"] for row in ordered[:3] + ordered[-1:]]
    fixture = projection(rows, focus_ids=expected)
    _, root = rendered(fixture, "focus7")
    assert ordered_focus_ids(root) == expected
    for count in (4, 3):
        partial = sorted(rows[:count], key=lambda row: row["metric"]["value"], reverse=True)
        fixture = projection(rows[:count], focus_ids=[row["market_id"] for row in partial])
        _, root = rendered(fixture, f"focus{count}")
        assert ordered_focus_ids(root) == [row["market_id"] for row in partial]


def test_zero_null_negative_and_exact_nikkei_identity():
    fixture = projection([metric_row(0, "JP", 0.0, index_id="^N225", index_label="Nikkei 225"), metric_row(1, "NULL", None), metric_row(2, "NEG", -3.24)])
    html, root = rendered(fixture, "zero-null")
    assert "0.00%" in html and "-3.24%" in html and "Unavailable" in html
    assert not re.search(r"(?<![0-9.])0%", html)
    assert "Nikkei 225" in html and "mockupTOPIX" not in html
    assert one(root, "data-index-id", "^N225").text == "Nikkei 225"


def test_independent_secondary_fields_windows_quality_and_no_raw_refs():
    window = {"start": "2025-01-02T00:00:00", "end": "2025-03-31T00:00:00", "calendar_policy": "owner_union_forward_fill", "endpoint_observations": {}}
    fixture = projection([metric_row(0, "M", 10.0, local=11.0, usd=9.0, fx=-2.0, index_id="I", index_label="Index", quality="partial", window=window)])
    html, root = rendered(fixture, "secondary")
    assert "partial" not in html and "owner_union_forward_fill" not in html and "endpoint_observations" not in html
    assert visible_text(one(root, "data-im-selected")) == "+10.00%"
    assert visible_text(one(root, "data-im-local")) == "+11.00%"
    assert visible_text(one(root, "data-im-usd")) == "+9.00%"
    assert visible_text(one(root, "data-im-fx")) == "-2.00 pp个百分点"
    assert "2025-01-02T00:00:00" in html and "2025-03-31T00:00:00" in html


def test_metric_unavailable_quality_uses_only_trusted_labels():
    qualities = {
        "qualified": "Qualified符合条件",
        "stale": "Stale data数据过期",
        "missing": "Missing data数据缺失",
        "denied": "Information withheld信息未披露",
        "failed": "Calculation failed计算失败",
        "unsupported": "Unsupported不支持",
        "unknown": "Unavailable不可用",
    }
    rows = [metric_row(index, f"M{index}", None, quality=quality, index_id=f"I{index}", index_label=f"Index {index}") for index, quality in enumerate(qualities)]
    fixture = projection(rows, focus_ids=[], available=False)
    html, root = rendered(fixture, "qualities")
    notices = [visible_text(node) for node in nodes(root, "data-im-quality")]
    assert len(notices) == len(qualities) * 3
    assert set(notices) == set(qualities.values())
    assert "hostile reason" not in html and "owner/private" not in html


def test_unavailable_summary_windows_and_full_roster():
    fixture = copy.deepcopy(SOURCE["unknown"])
    fixture["ranking_reason"] = "unequal_windows"
    fixture["summary"]["reason"] = "unequal_windows"
    html, root = rendered(fixture, "windows")
    assert "Available returns use different calculation windows" in html
    assert "可用回报采用不同计算窗口" in html
    context = visible_text(one(root, "class", "intl-overview__context"))
    assert "7 configured markets, 0 qualified returns" in context
    assert "覆盖市场 7 个，符合条件的回报 0 个" in context
    summary = visible_text(one(root, "data-im-summary"))
    assert "Comparable price returns" not in summary and "可比价格回报" not in summary
    assert len(nodes(root, "data-im-market-unknown")) == 7
    unknown_market = nodes(root, "data-im-market-unknown")[0]
    assert "M0" not in visible_text(unknown_market) and "Index" not in visible_text(unknown_market)
    assert visible_text(unknown_market).split() == ["Market", "0市场0", "Unavailable不可用"]
    assert len([node for node in walk(root) if node.tag == "article" and "__market" in node.attrs.get("class", "").split()]) == 7


def test_full_roster_once_bilingual_pairing_expansion_and_no_controls():
    fixture = projection([metric_row(index, f"M{index}", index * 1.0) for index in range(7)])
    html, root = rendered(fixture, "roster")
    assert len(nodes(root, "role", "listitem")) == 7
    assert len([node for node in walk(root) if node.tag == "article" and "__market" in node.attrs.get("class", "").split()]) == 7
    assert len(nodes(root, "class", "l-en")) == len(nodes(root, "class", "l-zh"))
    trigger = one(root, "data-im-expansion-trigger")
    assert "hidden" in trigger.attrs
    assert trigger.attrs["data-im-action"] == "set_expanded"
    assert trigger.attrs["data-im-expanded"] == "true"
    assert trigger.attrs["aria-controls"] == "roster-markets"
    assert trigger.attrs["aria-expanded"] == "true"
    assert one(root, "data-im-expanded-region").attrs["id"] == "roster-markets"
    for forbidden in ("save", "follow", "export", "pin", "globalnav"):
        assert forbidden not in html.lower()


def test_multiple_panels_and_no_fixture_mutation():
    original = copy.deepcopy(SOURCE["positive"])
    fixture = copy.deepcopy(original)
    html_a, root_a = rendered(fixture, "panel-a")
    html_b, root_b = rendered(fixture, "panel-b")
    assert fixture == original
    assert one(root_a, "data-im-panel").attrs["data-horizon"] == one(root_b, "data-im-panel").attrs["data-horizon"] == "1m"
    assert "panel-a-overview" in html_a and "panel-b-overview" in html_b
    assert one(root_a, "data-im-expanded-region").attrs["id"] == "panel-a-markets"
    assert one(root_b, "data-im-expanded-region").attrs["id"] == "panel-b-markets"


def test_invalid_prefix_rejected_outside_partial():
    with pytest.raises(AssertionError):
        rendered(SOURCE["positive"], "1-invalid")
