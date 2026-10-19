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
