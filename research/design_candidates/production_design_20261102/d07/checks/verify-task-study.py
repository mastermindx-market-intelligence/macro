"""Validate frozen Paper exports and fixtures without executing a product UI."""

import ast
import hashlib
import html
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "paper/task-study"
capture = json.loads((STUDY / "capture.json").read_text())
fixtures = json.loads((STUDY / "fixtures.json").read_text())
tokens = capture["tokens"]
checks = []


def check(label, condition, observed=None):
    checks.append({"label": label, "passed": bool(condition), "observed": observed})


def parse_style(source):
    pairs = re.findall(r"(\w+):\s*('(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"|-?\d+(?:\.\d+)?)", source)
    return {key: ast.literal_eval(value) for key, value in pairs}


@dataclass
class Node:
    identifier: str
    style: dict
    parent: object = None
    children: list = field(default_factory=list)
    text: list = field(default_factory=list)


class ExportParser(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.nodes = []
        self.stack = []
        self.styles = []

        def replace_style(match):
            self.styles.append(parse_style(match[1]))
            return f'data-style="{len(self.styles) - 1}"'

        source = re.sub(r"style=\{\{(.*?)\}\}", replace_style, source, flags=re.S)
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        if tag == "br":
            return
        if tag not in ("div", "span"):
            raise ValueError(f"Unqualified export element {tag}")
        attributes = dict(attributes)
        parent = self.stack[-1] if self.stack else None
        identifier = attributes.get("id")
        if identifier is None:
            identifier = f"{parent.identifier}/{tag}-{len(parent.children)}"
        style = self.styles[int(attributes["data-style"])] if "data-style" in attributes else {}
        node = Node(identifier, style, parent)
        if parent:
            parent.children.append(node)
        self.nodes.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        if tag in ("div", "span"):
            self.stack.pop()

    def handle_data(self, text):
        if self.stack and text.strip():
            self.stack[-1].text.append(text.strip())


def inherited(node, property_name):
    while node:
        if property_name in node.style:
            return node.style[property_name]
        node = node.parent
    raise ValueError(f"No inherited {property_name}")


def color(value):
    match = re.fullmatch(r"var\((--[\w-]+)\)", value)
    value = tokens[match[1]] if match else value
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(f"Unsupported color {value}")
    return value


def luminance(value):
    channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(foreground, background):
    darker, lighter = sorted((luminance(foreground), luminance(background)))
    return (lighter + 0.05) / (darker + 0.05)


def all_text(nodes):
    return " | ".join(part for node in nodes for part in node.text)


def descendants(node):
    return node.text + [text for child in node.children for text in descendants(child)]


parsed = {}
contrasts = []
controls = []
inventory = json.loads((STUDY / "inventory.json").read_text())
inventory_by_id = {board["id"]: board for board in inventory["boards"]}
check("Eight distinct study boards", len(capture["boards"]) == 8 and len({board["id"] for board in capture["boards"]}) == 8)

for board in capture["boards"]:
    key = board["key"]
    image_path = STUDY / board["image"]
    jsx_path = STUDY / board["jsx"]
    check(f"{key} image digest", hashlib.sha256(image_path.read_bytes()).hexdigest() == board["image_sha256"])
    check(f"{key} JSX digest", hashlib.sha256(jsx_path.read_bytes()).hexdigest() == board["jsx_sha256"])
    with Image.open(image_path) as image:
        check(f"{key} actual image dimensions", list(image.size) == board["image_pixels"], list(image.size))
    source = jsx_path.read_text()
    nodes = ExportParser(source).nodes
    parsed[key] = nodes
    check(f"{key} exported root identity", nodes[0].identifier == board["id"])
    check(f"{key} native width", inventory_by_id[board["id"]]["width"] == board["image_pixels"][0])
    check(f"{key} explicit content width", f"width: '{board['image_pixels'][0]}px'" in source)
    check(f"{key} study qualification", any(word in all_text(nodes) for word in ("PROVISIONAL", "阶段2A研究样本")))
    referenced_tokens = set(re.findall(r"var\((--[\w-]+)\)", source))
    check(f"{key} all token references resolve", referenced_tokens <= tokens.keys())

    for node in nodes:
        if node.text:
            foreground = color(inherited(node, "color"))
            background = color(inherited(node, "backgroundColor"))
            ratio = contrast(foreground, background)
            contrasts.append({"board": key, "node": node.identifier, "foreground": foreground, "background": background, "ratio": round(ratio, 6)})
            check(f"{key} {node.identifier} text contrast", ratio >= 4.5, round(ratio, 6))
        if "minHeight" in node.style:
            height = float(node.style["minHeight"].removesuffix("px"))
            controls.append({"board": key, "node": node.identifier, "minimum_height": height})
            check(f"{key} {node.identifier} control height", height >= 44, height)

for key in ("A", "B", "F", "G"):
    text = all_text(parsed[key])
    for value in ("46.743", "45.000", "44.10–45.90", "+3.9%", "54.0", "52.92–55.08"):
        check(f"{key} historical value {value}", value in text)
    chinese = key in ("F", "G")
    required = ("2026财年第二季度", "2026财年第三季度", "2025年5月28日", "2025年8月27日", "分析师共识数据暂缺") if chinese else ("Q2 FY2026", "Q3 FY2026", "28 May 2025", "27 Aug 2025", "Analyst consensus unavailable")
    check(f"{key} period, clock and unavailable labels", all(label in text for label in required))
    primary = "查看来源与计算" if chinese else "View source & calculation"
    control = "此前管理层指引" if chinese else "Prior management guidance"
    check(f"{key} source action precedes detailed comparator", text.index(primary) < text.rindex(control))

for left, right in (("A", "B"), ("F", "G")):
    normalize = lambda text: re.sub(r"(?:320|390|288|358)px", "WIDTHpx", text)
    check(f"{left}/{right} width variants preserve all text", normalize(all_text(parsed[left])) == normalize(all_text(parsed[right])))

for key, year, value, acquired, filed in (("C", "FY2024", "100.0", "16 Feb 2025, 09:00 UTC", "15 Feb 2025"), ("D", "FY2025", "120.0", "16 Feb 2026, 09:00 UTC", "15 Feb 2026")):
    text = all_text(parsed[key])
    required = ("Statements", "Statistics", "Revenue", "Dividends", "Compare", "Income statement", "Balance sheet", "Cash flow", "Annual", "Quarterly", "All available periods", "Reported zero", "0.00", "Unavailable", "+20.0%", "664px primary + 24px gap + 320px evidence")
    check(f"{key} retained views, controls and missingness", all(label in text for label in required))
    selected = [node for node in parsed[key] if node.style.get("borderWidth") == "2px" and value in descendants(node)]
    check(f"{key} selected value has explicit border", len(selected) == 1)
    required_evidence = (f"Revenue · {year}", f"Return to Revenue · {year}", "Annual · 12 months", acquired, filed, "3 Nov 2026", "Document unavailable in fixture", "The value and clocks are synthetic.")
    check(f"{key} evidence selection and clocks agree", all(label in text for label in required_evidence))

evidence_text = all_text(parsed["E"])
desktop_text = all_text(parsed["D"])
check("D/E evidence text is identical after its study label", evidence_text[evidence_text.index("Selected evidence"):] == desktop_text[desktop_text.index("Selected evidence"):])
chooser = all_text(parsed["H"])
check("H retains five actual Financials views", all(view["label"] in chooser for view in fixtures["financials_chooser"]["views"]))
check("H names current view and close destination", "Current" in chooser and "Close returns to Financials · Statements." in chooser)
check("H five view controls have 48px minimum", sum(node.style.get("minHeight") == "48px" for node in parsed["H"]) == 5)

historical = fixtures["historical_comparison"]
check("Historical midpoint arithmetic rounds to +3.9%", f"{(historical['actual_usd_bn'] / historical['prior_midpoint_usd_bn'] - 1) * 100:.1f}" == "3.9")
check("Prior guidance range is midpoint ±2%", all(math.isclose(value, historical["prior_midpoint_usd_bn"] * factor) for value, factor in zip(historical["prior_range_usd_bn"], (0.98, 1.02))))
check("Next-period range is separate midpoint ±2%", all(math.isclose(value, historical["next_midpoint_usd_bn"] * factor) for value, factor in zip(historical["next_range_usd_bn"], (0.98, 1.02))))
annual = fixtures["synthetic_statements"]["data"]["statements"]["annual"]
check("Synthetic annual growth is +20%", math.isclose((annual["income"]["revenue"][1] / annual["income"]["revenue"][0] - 1) * 100, 20))
check("Synthetic EPS preserves zero and unavailable", annual["income"]["eps_diluted"] == [0, None])
check("Synthetic annual identities and durations", annual["fiscal_year"] == ["2024", "2025"] and annual["period_duration_months"] == [12, 12])

operations = json.loads((STUDY / "operations.json").read_text())
states = Counter(operation["state"] for operation in operations)
check("66 unique recorded operations", len(operations) == 66 and len({operation["operation_id"] for operation in operations}) == 66)
check("Operation states are observed and bounded", states == {"PAPER_READY": 1, "APPLIED_RESPONSE_OBSERVED": 65}, dict(states))
check("Selected ink correction is recorded", any(operation["operation_id"] == "D07-20261103-study-selected-ink-contrast-01" for operation in operations))
check("Contrast working indicators released", operations[-1]["operation_id"] == "D07-20261103-study-contrast-finish-01")
check("Nine original R3 artboards retained", len(inventory["retainedR3"]) == 9)
check("Original phone remains an empty predecessor", any(board["id"] == "1D9K-0" and board["childCount"] == 0 for board in inventory["retainedR3"]))
check("Build-contract board remains present", inventory_by_id["1NFS-0"]["childCount"] == 11)

report = {
    "classification": "STATIC_ARTIFACT_CHECKS",
    "checks": len(checks),
    "failures": [item for item in checks if not item["passed"]],
    "image_jsx_pairs": len(parsed),
    "text_nodes_checked": len(contrasts),
    "minimum_text_contrast": min(item["ratio"] for item in contrasts),
    "control_minimum_heights_checked": len(controls),
    "ui_execution_assertions": 0,
    "all_checks": checks,
    "text_contrast": contrasts,
    "control_minimum_heights": controls,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(bool(report["failures"]))
