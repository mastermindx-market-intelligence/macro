"""Read the real producer shape without silently promoting or inventing facts."""
import json
from pathlib import Path

import pytest

from engine.critical_minerals_display import load_critical_minerals_context

FIXTURE = Path(__file__).parent / "fixtures/usgs_mcs/display_context.json"


def fixture():
    return json.loads(FIXTURE.read_text())


def read(tmp_path, value):
    p = tmp_path / "source.json"
    p.write_text(json.dumps(value))
    return load_critical_minerals_context(p)


def test_actual_native_source_preserves_sentences_qualifiers_and_three_clocks(tmp_path):
    source = fixture()
    result = read(tmp_path, source)
    assert result["state"] == "AVAILABLE"
    assert [r["key"] for r in result["rows"]] == ["cobalt", "lithium", "gallium", "rare_earths"]
    assert result["edition_year"] == 2026
    assert result["published"] == "2026-02-06"
    assert result["generated_at"] == "2026-10-19T18:30:51Z"
    for row in result["rows"]:
        assert row["observation_period"] == "2025"
        for lang in ["en", "zh"]:
            assert row["read_" + lang] == source["commodities"][row["key"]]["read_" + lang]
    assert "more than 50 percent" in result["rows"][1]["read_en"]
    assert result["source_url"] == "https://www.sciencebase.gov/catalog/item/696a75d5d4be0228872d3bf8"
    assert not any(k in result for k in ["score", "rank", "allocation", "signal"])


@pytest.mark.parametrize("flag", ["may_rank", "may_gate", "may_size", "may_escalate", "rotation_calls", "short_calls"])
@pytest.mark.parametrize("bad", [True, 0, None, "false"])
def test_financial_authority_must_be_explicitly_false(tmp_path, flag, bad):
    source = fixture()
    source["authority"][flag] = bad
    assert read(tmp_path, source) == {"state": "UNAVAILABLE", "rows": []}


@pytest.mark.parametrize("damage", ["missing", "blank", "no_edition"])
def test_missing_mineral_stays_unknown_without_losing_other_source_reads(tmp_path, damage):
    source = fixture()
    if damage == "missing":
        del source["commodities"]["lithium"]
    elif damage == "blank":
        source["commodities"]["lithium"]["read_en"] = " "
    else:
        source["commodities"]["lithium"]["nulls"].append("no_edition_ingested")
    result = read(tmp_path, source)
    assert result["state"] == "PARTIAL"
    assert sum(r["available"] for r in result["rows"]) == 3
    missing = result["rows"][1]
    assert missing["read_en"] is None and missing["observation_period"] is None
    assert result["rows"][0]["read_en"] == source["commodities"]["cobalt"]["read_en"]


@pytest.mark.parametrize("raw", [b'{', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'\xff', b' '*262145])
def test_malformed_duplicate_nonfinite_and_oversize_are_unavailable(tmp_path, raw):
    p = tmp_path / "source.json"
    p.write_bytes(raw)
    assert load_critical_minerals_context(p) == {"state": "UNAVAILABLE", "rows": []}


def test_absent_source_is_not_zero_or_cached_success(tmp_path):
    p = tmp_path / "source.json"
    assert load_critical_minerals_context(p)["state"] == "UNAVAILABLE"
    p.write_text(FIXTURE.read_text())
    assert load_critical_minerals_context(p)["state"] == "AVAILABLE"
    p.unlink()
    assert load_critical_minerals_context(p) == {"state": "UNAVAILABLE", "rows": []}


@pytest.mark.parametrize("field,bad", [("year", True), ("published", "2026-02-30"), ("item_id", "../untrusted"), ("year", "2026")])
def test_invalid_publication_binding_cannot_produce_a_fact(tmp_path, field, bad):
    source = fixture(); source["edition"][field] = bad
    assert read(tmp_path, source)["state"] == "UNAVAILABLE"


def test_missing_timezone_and_context_fence_are_rejected(tmp_path):
    source = fixture(); source["generated_at"] = "2026-10-19T18:30:51"
    assert read(tmp_path, source)["state"] == "UNAVAILABLE"
    source = fixture(); source["authority"]["is_context_only"] = False
    assert read(tmp_path, source)["state"] == "UNAVAILABLE"


def test_other_honest_null_does_not_erase_a_qualified_leading_producer_sentence(tmp_path):
    source = fixture(); source["commodities"]["cobalt"]["nulls"] = ["china_world_production_unavailable"]
    result = read(tmp_path, source)
    assert result["state"] == "AVAILABLE"
    assert result["rows"][0]["read_en"] == source["commodities"]["cobalt"]["read_en"]


GALLIUM_SOURCES = [
    {"country": "Canada", "pct": 28.0}, {"country": "Japan", "pct": 22.0},
    {"country": "China", "pct": 18.0}, {"country": "Germany", "pct": 16.0},
    {"country": "Other", "pct": 16.0},
]
RARE_EARTH_SOURCES = [
    {"country": "China", "pct": 71.0}, {"country": "Malaysia", "pct": 13.0},
    {"country": "Japan", "pct": 5.0}, {"country": "Estonia", "pct": 5.0},
    {"country": "Other", "pct": 6.0},
]


def sourced():
    source = fixture()
    source["commodities"]["gallium"]["import_sources_2021_24"] = GALLIUM_SOURCES
    source["commodities"]["rare_earths"]["import_sources_2021_24"] = RARE_EARTH_SOURCES
    return source


def test_import_sources_keep_recorded_order_and_world_output_keeps_units(tmp_path):
    result = read(tmp_path, sourced())
    assert result["has_import_sources"] is True
    gallium, rare = result["rows"][2], result["rows"][3]
    assert gallium["import_sources"] == [
        {"country_en": "Canada", "country_zh": "加拿大", "pct": "28"},
        {"country_en": "Japan", "country_zh": "日本", "pct": "22"},
        {"country_en": "China", "country_zh": "中国", "pct": "18"},
        {"country_en": "Germany", "country_zh": "德国", "pct": "16"},
        {"country_en": "Other", "country_zh": "其他", "pct": "16"},
    ]
    assert [e["country_en"] for e in rare["import_sources"]] == \
        ["China", "Malaysia", "Japan", "Estonia", "Other"]
    assert gallium["world_output"] == {"amount": "900", "unit_en": "metric tons", "unit_zh": "公吨"}
    assert rare["world_output"]["amount"] == "390,000"


def test_without_import_sources_the_flag_is_false_and_rows_stay_clean(tmp_path):
    result = read(tmp_path, fixture())
    assert result["has_import_sources"] is False
    assert all(row["import_sources"] is None for row in result["rows"])


BAD_SOURCE_PAIRS = [
    ("pct_string", [{"country": "China", "pct": "71"}]),
    ("pct_bool", [{"country": "China", "pct": True}]),
    ("pct_over_100", [{"country": "China", "pct": 140}]),
    ("pct_negative", [{"country": "China", "pct": -1}]),
    ("pct_just_over_100", [{"country": "China", "pct": 101.0}]),
    ("missing_country", [{"pct": 71.0}]),
    ("blank_country", [{"country": " ", "pct": 71.0}]),
    ("non_dict_pair", ["China"]),
    ("empty_list", []),
    ("thirteen_pairs", [{"country": "C%d" % n, "pct": 1.0} for n in range(13)]),
    ("legal_pairs_total_140", [{"country": "Canada", "pct": 70.0},
                               {"country": "Japan", "pct": 70.0}]),
]


@pytest.mark.parametrize("kind,bad", BAD_SOURCE_PAIRS,
                         ids=[kind for kind, _ in BAD_SOURCE_PAIRS])
def test_bad_import_sources_drop_the_line_without_touching_the_row(tmp_path, kind, bad):
    source = sourced()
    source["commodities"]["gallium"]["import_sources_2021_24"] = bad
    result = read(tmp_path, source)
    row = result["rows"][2]
    assert row["import_sources"] is None
    assert row["available"] is True and result["state"] == "AVAILABLE"
    assert row["read_en"] == source["commodities"]["gallium"]["read_en"]


def test_unknown_country_stays_recorded_and_small_pcts_keep_their_digits(tmp_path):
    source = sourced()
    source["commodities"]["gallium"]["import_sources_2021_24"] = [
        {"country": "Atlantis", "pct": 1.5}]
    assert read(tmp_path, source)["rows"][2]["import_sources"] == [
        {"country_en": "Atlantis", "country_zh": "Atlantis", "pct": "1.5"}]


@pytest.mark.parametrize("damage", ["unit_flasks", "total_bool", "total_string",
                                    "total_zero", "total_negative"])
def test_bad_world_output_stays_none_with_the_row_available(tmp_path, damage):
    source = fixture()
    producer = source["commodities"]["gallium"]["leading_producer"]
    if damage == "unit_flasks":
        producer["unit"] = "flasks"
    elif damage == "total_bool":
        producer["world_total"] = True
    elif damage == "total_string":
        producer["world_total"] = "900"
    elif damage == "total_zero":
        producer["world_total"] = 0
    else:
        producer["world_total"] = -5
    row = read(tmp_path, source)["rows"][2]
    assert row["world_output"] is None and row["available"] is True


def test_unavailable_row_carries_no_subfields_even_with_valid_pairs(tmp_path):
    source = sourced()
    source["commodities"]["cobalt"]["import_sources_2021_24"] = GALLIUM_SOURCES
    source["commodities"]["cobalt"]["read_en"] = " "
    row = read(tmp_path, source)["rows"][0]
    assert row["available"] is False
    assert row["import_sources"] is None and row["world_output"] is None


def test_rows_still_carry_no_scoring_keys(tmp_path):
    for row in read(tmp_path, sourced())["rows"]:
        assert not any(k in row for k in ["score", "rank", "signal", "allocation"])
