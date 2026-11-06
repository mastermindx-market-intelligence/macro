"""Per-row World Bank vintage on templates/spr.html.j2 (SPEC 3).

scripts/build_spr.py:199 stamps the page-level gold.wb_year with the FIRST row's year,
so the column cannot claim one year; each gold row must show its own r.wb_year, and the
subtitle, the foot clause and GOLD_CAVEAT must stop calling annual World Bank data
"live". Rendered from inline fixtures shaped like the committed record; no site/ or
data/ read, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import strategic_reserves as sr     # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = (REPO / "templates/spr.html.j2").read_text(encoding="utf-8")
MACROS = "".join(TEMPLATE.splitlines(True)[:8])

RUSSIA = {"iso": "RUS", "name": "Russia", "name_zh": "俄罗斯", "flag": "🇷🇺",
          "tonnes": 2335.9, "trend": "stable", "trend_en": "stable",
          "trend_zh": "持平", "value_usd": 195682500000.0, "share_pct": 32.2,
          "value_yoy_pct": 26.5, "wb_year": 2024}
USA = {"iso": "USA", "name": "United States", "name_zh": "美国", "flag": "🇺🇸",
       "tonnes": 8133.5, "trend": "stable", "trend_en": "stable",
       "trend_zh": "持平", "value_usd": 1142000000000.0, "share_pct": 82.4,
       "value_yoy_pct": 67.4, "wb_year": 2025}
TAIWAN = {"iso": "TWN", "name": "Taiwan", "name_zh": "台湾", "flag": "🇹🇼",
          "tonnes": None, "trend": None, "trend_en": None, "trend_zh": None,
          "value_usd": None, "share_pct": None, "value_yoy_pct": None,
          "wb_year": None}


def _rows_source():
    start = TEMPLATE.index("{% for r in gold.rows %}")
    end = TEMPLATE.index("{% endfor %}", start) + len("{% endfor %}")
    return MACROS + TEMPLATE[start:end]


def _render(row):
    out = Environment(autoescape=True).from_string(_rows_source()).render(
        gold={"rows": [row]})
    return out


def _flat(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def _en(raw):
    return _flat(re.sub(r'<span class="l-zh">.*?</span>', "", raw, flags=re.S))


def _zh(raw):
    return _flat(re.sub(r'<span class="l-en">.*?</span>', "", raw, flags=re.S))


def test_russia_row_renders_its_own_2024_world_bank_year():
    en = _en(_render(RUSSIA))
    assert "as of 2024" in en
    assert "$196B" in en
    assert "32.2%" in en
    assert "+26%/yr" in en
    assert "2025" not in en


def test_a_2025_row_renders_2025_and_not_the_global_stamp():
    en = _en(_render(USA))
    assert "as of 2025" in en
    en2 = _en(_render({**USA, "wb_year": 2024}))
    assert "as of 2024" in en2
    assert "2025" not in en2


def test_row_without_a_world_bank_year_renders_no_year():
    en = _en(_render(TAIWAN))
    assert "n/a" in en
    assert "as of" not in en
    assert "None" not in en
    assert re.search(r"\d{4}", en) is None
    partial = _en(_render({**USA, "wb_year": None}))   # value but no vintage
    assert "as of" not in partial
    assert "None" not in partial


def test_gold_block_no_longer_calls_annual_world_bank_data_live():
    assert "live World Bank" not in TEMPLATE
    assert "世界银行实时" not in TEMPLATE
    assert "reserves, live)" not in TEMPLATE
    assert "比例，实时" not in TEMPLATE
    assert "live" not in sr.GOLD_CAVEAT["en"].lower()
    assert "annual" in sr.GOLD_CAVEAT["en"]
    assert "实时" not in sr.GOLD_CAVEAT["zh"]
    assert "年度" in sr.GOLD_CAVEAT["zh"]


def _sub_source():
    start = TEMPLATE.index('<div class="sub" style="margin:8px 0 12px">')
    end = TEMPLATE.index("</div>", start) + len("</div>")
    return TEMPLATE[start:end]


def test_subtitle_claims_no_single_year_for_the_whole_column():
    raw = Environment(autoescape=True).from_string(
        MACROS + _sub_source()).render(gold={"as_of": "2025", "wb_year": 2025})
    en = _en(raw)
    zh = _zh(raw)
    assert "each row shows its year" in en
    assert "(2025)" not in en
    assert "World Bank annual data" in en
    assert "live World Bank" not in en
    assert "各行注明年份" in zh
    assert "(2025)" not in zh
