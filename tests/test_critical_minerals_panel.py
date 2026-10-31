from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
MACRO = """{% macro t(en, zh) -%}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{%- endmacro %}"""


def render(context):
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined)
    return env.from_string(MACRO + '{% include "_critical_minerals_context.html.j2" %}').render(critical_minerals=context)


def context():
    return {
        "state": "AVAILABLE", "edition_year": 2026, "published": "2026-02-06",
        "generated_at": "2026-10-19T18:30:51Z",
        "source_url": "https://www.sciencebase.gov/catalog/item/696a75d5d4be0228872d3bf8",
        "rows": [{"key": "cobalt", "label_en": "Cobalt", "label_zh": "钴", "available": True,
                  "read_en": "Congo mined about 74% in 2025.", "read_zh": "刚果在2025年开采了约74%。",
                  "observation_period": "2025"}],
    }


def test_annual_observation_publication_and_generation_remain_distinct():
    html = render(context())
    assert "Observation period" in html and "2025" in html
    assert 'datetime="2026-02-06"' in html
    assert 'datetime="2026-10-19T18:30:51Z"' in html
    assert "Generation time does not change" in html
    assert "不代表实时短缺" in html
    assert "74%" in html and "刚果" in html


def test_missing_source_is_unknown_without_zero_or_false_source_link():
    html = render({"state": "UNAVAILABLE", "rows": []})
    assert "unknown, not zero" in html and "缺失覆盖意味着未知" in html
    assert "0%" not in html and "<a " not in html and "<time " not in html


def test_partial_row_keeps_available_fact_and_names_unavailable_row():
    data = context()
    data["state"] = "PARTIAL"
    data["rows"].append({"key": "lithium", "label_en": "Lithium", "label_zh": "锂", "available": False})
    html = render(data)
    assert "Congo mined about 74%" in html and "Lithium" in html and "锂" in html
    assert "No qualified annual read" in html and "0%" not in html


def test_source_sentences_are_escaped_without_becoming_markup():
    data = context()
    data["rows"][0]["read_en"] = '<script>alert("not markup")</script>'
    html = render(data)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_normal_commodities_template_mounts_independent_context():
    template = (TEMPLATES / "commodities.html.j2").read_text()
    assert '{% include "_critical_minerals_context.html.j2" %}' in template
    builder = (TEMPLATES.parent / "scripts" / "build_commodities.py").read_text()
    assert 'config.ROOT / "data" / "neuralweb" / "critical_minerals_supply.json"' in builder
    assert "critical_minerals=critical_minerals" in builder
    assert "collectors.usgs_mcs" not in builder


def test_legacy_page_without_new_context_keeps_honest_unavailable_panel():
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined)
    html = env.from_string(MACRO + '{% include "_critical_minerals_context.html.j2" %}').render()
    assert "unknown, not zero" in html and "0%" not in html
