"""Sector page to basket page and back.

Renders the two blocks alone, so no site/, no data/ and no engine import.
"""
import json
import pathlib
import re
import subprocess

import jinja2

ROOT = pathlib.Path(__file__).resolve().parents[1]
SECTOR = ROOT / "templates" / "sector.html.j2"
BASKET = ROOT / "templates" / "basket_detail.html.j2"

SECTOR_START = "{# sector-basket-links"
SECTOR_END = "{# /sector-basket-links #}"
BASKET_START = "// basket-sector-link"
BASKET_END = "// /basket-sector-link"
FUNDS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")


def _between(text, start, end):
    assert text.count(start) == 1 and text.count(end) == 1
    return text[text.index(start) : text.index(end)]


def _sector_html(fund):
    block = _between(SECTOR.read_text(encoding="utf-8"), SECTOR_START, SECTOR_END)
    macro = '{% macro t(en, zh="") %}<i data-zh="{{ zh }}">{{ en }}</i>{% endmacro %}'
    return jinja2.Environment().from_string(macro + block).render(s={"fund": fund}).strip()


def _hrefs(html):
    return re.findall(r'href="([^"]+)"', html)


def _label_html(labels):
    helper = _between(BASKET.read_text(encoding="utf-8"), BASKET_START, BASKET_END)
    stub = "const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');\n"
    run = helper + "\nconsole.log(JSON.stringify(" + json.dumps(labels) + ".map(refLabelHtml)));"
    out = subprocess.run(["node", "-e", stub + run], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_xly_opens_the_retail_basket():
    html = _sector_html("XLY")
    assert _hrefs(html) == ["../basket/retail.html"]
    assert ">Retail basket<" in html and 'data-zh="零售篮子"' in html
    assert "retail names scored as a group." in html and 'data-zh="零售公司的分组评分。"' in html


def test_xlb_opens_gold_and_critical_minerals_and_not_uranium():
    html = _sector_html("XLB")
    assert _hrefs(html) == ["../basket/gold_miners.html", "../basket/critical_minerals.html"]
    assert ">Gold Miners basket<" in html and 'data-zh="黄金矿业篮子"' in html
    assert ">Critical Minerals basket<" in html and 'data-zh="关键矿产与稀土篮子"' in html
    assert "mining names scored as a group." in html and 'data-zh="矿业公司的分组评分。"' in html
    assert "uranium" not in html


def test_no_other_fund_prints_a_basket_link():
    for fund in tuple(f for f in FUNDS if f not in ("XLY", "XLB")) + ("159928.SZ", ""):
        assert _sector_html(fund) == ""


def test_links_sit_under_the_signal_age_line():
    text = SECTOR.read_text(encoding="utf-8")
    age = text.index("s.ladder.age_line_zh")
    assert age < text.index(SECTOR_START) < text.index(SECTOR_END) < text.index("s.ladder.early_note")


def test_each_sector_fund_label_opens_its_own_page():
    got = _label_html(list(FUNDS))
    assert got == [f'<a href="../sectors/{fund}.html">{fund}</a>' for fund in FUNDS]


def test_every_other_label_stays_escaped_text():
    got = _label_html(["GDX", "REMX", "XLG", "S&P 500", "<b>x</b>"])
    assert got == ["GDX", "REMX", "XLG", "S&amp;P 500", "&lt;b&gt;x&lt;/b&gt;"]


def test_cross_check_line_uses_the_label_helper():
    text = BASKET.read_text(encoding="utf-8")
    assert "<b>${refLabelHtml(ref.label)}</b>" in text
    assert "<b>${esc(ref.label)}</b>" not in text
    # The helper needs the esc that the cross-check line's script declares.
    assert text.index("const esc = s =>") < text.index(BASKET_START) < text.index("<b>${refLabelHtml(ref.label)}</b>")
