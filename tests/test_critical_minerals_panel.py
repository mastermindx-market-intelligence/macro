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


def sourced_context():
    data = context()
    row = data["rows"][0]
    row["import_sources"] = [
        {"country_en": "Canada", "country_zh": "加拿大", "pct": "28"},
        {"country_en": "Japan", "country_zh": "日本", "pct": "22"}]
    row["world_output"] = {"amount": "900", "unit_en": "metric tons", "unit_zh": "公吨"}
    data["has_import_sources"] = True
    return data


def test_import_sources_and_world_production_render_in_both_languages():
    html = render(sourced_context())
    assert '<span class="l-en">Canada</span><span class="l-zh">加拿大</span> 28%' in html
    assert "US import sources 2021–24" in html and "美国进口来源 2021–24" in html
    assert "World production" in html and "全球产量" in html and "900" in html
    assert '<span class="l-zh">公吨</span>' in html
    assert "different measures and different years" in html
    assert "两者是不同的度量，年份也不同" in html


def test_source_line_has_no_trailing_separator_and_counts_entries_minus_one():
    html = render(sourced_context())
    tail = html.split("US import sources 2021–24", 1)[1].split("</p>", 1)[0]
    assert tail.count(" · ") == 1
    assert "·" not in tail.split("22%", 1)[1]


def test_rows_without_the_fields_write_nothing():
    html = render(context())
    assert "US import sources" not in html and "World production" not in html
    assert "different measures" not in html
    assert "美国进口来源" not in html and "全球产量" not in html


def test_each_line_renders_only_when_its_own_field_is_present():
    without_world = sourced_context()
    without_world["rows"][0]["world_output"] = None
    html = render(without_world)
    assert '<span class="l-en">US import sources' in html
    assert '<span class="l-en">World production</span>' not in html
    without_sources = sourced_context()
    without_sources["rows"][0]["import_sources"] = None
    without_sources["has_import_sources"] = False
    html = render(without_sources)
    assert '<span class="l-en">World production</span>' in html
    assert '<span class="l-en">US import sources' not in html


def test_added_source_and_note_lines_carry_no_banned_word():
    html = render(sourced_context())
    line = html.split("US import sources 2021–24", 1)[1].split("</p>", 1)[0]
    note = "Import sources show" + html.split("Import sources show", 1)[1].split("</p>", 1)[0]
    for text in (line, note):
        for word in ["实时", "申报", "证伪", "validated", "已验证", "forecast", "falsifier"]:
            assert word not in text
