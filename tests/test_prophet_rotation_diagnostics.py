"""Source-shaped contract tests; no invented flattened basket fixture."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from admin.prophet_diagnostics import build_diagnostics, read_diagnostics, SOURCE_PATH, MAX_BYTES


@pytest.fixture
def audit():
    return {"schema": "prophet_miss_audit/v1", "price_through": "2026-09-14",
        "summary": {"universe_n": 1496, "top63_n": 150, "top21_n": 50},
        "themes": {"standouts_asof": "2026-09-14", "rotation_asof": "2026-09-14"},
        "conversion": {"sighted_n": 124, "converted_n": 21, "rate": 0.1694},
        "basket_misses": {"available": True, "as_of": "2026-09-14",
            "standouts_asof": "2026-09-14", "baskets": [{
                "basket_id": "energy_complex", "name": "US Energy Complex",
                "as_of": "2026-09-14", "n_members_on_board": 2,
                "members_on_board": ["DINO", "VLO"],
                "present_counts": {"buy": 0, "watch": 0, "leaders": 2, "ran": 0}}]}}


def write(tmp_path, raw):
    path = tmp_path / SOURCE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def test_source_shaped_energy_and_exact_hash(audit, tmp_path):
    raw = json.dumps(audit, indent=2).encode()
    path = write(tmp_path, raw)
    result = read_diagnostics(tmp_path)
    assert result["status"] == "available"
    assert result["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["conversion"]["legacy_rate"] == 0.1694
    assert result["conversion"]["on_time_rate"] is None
    assert result["conversion"]["on_time_state"] == "not_measured"
    assert result["baskets"][0]["visibility"] == "leader_only"
    assert result["baskets"][0]["members_on_board"] == ["DINO", "VLO"]
    assert result["baskets"][0]["entry_actionability"] == "not_measured"
    assert path.read_bytes() == raw
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("bad", [True, "150", -1, 1.5, 150.0, float("nan"), float("inf"), 10**400, None])
def test_invalid_counts_are_not_zero(audit, bad):
    audit["summary"]["top63_n"] = bad
    result = build_diagnostics(audit)
    assert result["populations"]["runners_63"] is None
    assert "population_inconsistent" in result["reasons"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("field", ["top63_n", "top21_n"])
def test_one_empty_runner_population_is_visible(audit, field):
    audit["summary"][field] = 0
    assert "empty_runner_population" in build_diagnostics(audit)["reasons"]


@pytest.mark.parametrize("bad", [True, "0.1694", -0.1, 1.1, float("nan"), float("inf"), 10**400, None])
def test_invalid_rates_are_unavailable(audit, bad):
    audit["conversion"]["rate"] = bad
    result = build_diagnostics(audit)
    assert result["conversion"]["legacy_rate"] is None
    assert "conversion_unavailable" in result["reasons"]


def test_zero_denominator_and_contradictory_conversion(audit):
    audit["conversion"] = {"sighted_n": 0, "converted_n": 0, "rate": 0}
    result = build_diagnostics(audit)
    assert result["conversion"]["legacy_rate"] is None
    assert "conversion_inconsistent" in result["reasons"]
    audit["conversion"] = {"sighted_n": 2, "converted_n": 3, "rate": 0.5}
    assert "conversion_unavailable" in build_diagnostics(audit)["reasons"]
    audit["conversion"] = {"sighted_n": 4, "converted_n": 2, "rate": 0.8}
    assert build_diagnostics(audit)["conversion"]["legacy_rate"] is None


@pytest.mark.parametrize("bad", ["0000-01-01", "2026-02-30", "2026-9-01", "2026-09-14T00:00:00Z", "2026-09-14\n", True, None])
def test_dates_are_calendar_dates_not_build_times(audit, bad):
    audit["price_through"] = bad
    result = build_diagnostics(audit)
    assert result["dates"]["prices"] is None and result["dates_aligned"] is None
    assert "dates_incomplete" in result["reasons"]


def test_mixed_dates_and_input_immutability(audit):
    audit["themes"]["standouts_asof"] = "2026-09-11"
    before = deepcopy(audit)
    result = build_diagnostics(audit)
    assert result["dates_aligned"] is False and "mixed_vintages" in result["reasons"]
    assert audit == before


@pytest.mark.parametrize("lane", ["buy", "watch"])
def test_setup_lane_is_not_actionability(audit, lane):
    row = audit["basket_misses"]["baskets"][0]
    row["present_counts"] = {"buy": 0, "watch": 0, "leaders": 0, "ran": 0}
    row["present_counts"][lane] = 2
    result = build_diagnostics(audit)["baskets"][0]
    assert result["visibility"] == "setup_lane_present"
    assert result["entry_actionability"] == "not_measured"


@pytest.mark.parametrize("field", ["buy", "watch", "leaders", "ran"])
def test_all_lane_counts_required(audit, field):
    del audit["basket_misses"]["baskets"][0]["present_counts"][field]
    result = build_diagnostics(audit)
    assert result["baskets"][0]["visibility"] == "unknown"
    assert "basket_incomplete_counts" in result["reasons"]


def test_flattened_fields_cannot_replace_actual_source(audit):
    row = audit["basket_misses"]["baskets"][0]
    row.update(row.pop("present_counts"))
    assert build_diagnostics(audit)["baskets"][0]["visibility"] == "unknown"


@pytest.mark.parametrize("bad", [None, {}, "bad", [1], ["VLO", "VLO"], ["VLO"] * 201])
def test_invalid_members_withhold_visibility(audit, bad):
    audit["basket_misses"]["baskets"][0]["members_on_board"] = bad
    result = build_diagnostics(audit)
    assert result["status"] == "partial"
    assert result["baskets"][0]["visibility"] == "unknown"


def test_duplicate_or_oversized_basket_component_withheld(audit):
    row = audit["basket_misses"]["baskets"][0]
    audit["basket_misses"]["baskets"] = [row, deepcopy(row)]
    result = build_diagnostics(audit)
    assert result["baskets"] == [] and "duplicate_basket_ids" in result["reasons"]
    audit["basket_misses"]["baskets"] = [dict(row, basket_id=str(i)) for i in range(201)]
    result = build_diagnostics(audit)
    assert result["baskets"] == [] and "basket_count_oversize" in result["reasons"]


def test_unavailable_source_cannot_launder_stale_basket_rows(audit):
    audit["basket_misses"]["available"] = False
    result = build_diagnostics(audit)
    assert result["baskets"] == [] and "basket_source_unavailable" in result["reasons"]


def test_true_empty_visibility(audit):
    row = audit["basket_misses"]["baskets"][0]
    row["present_counts"] = dict.fromkeys(("buy", "watch", "leaders", "ran"), 0)
    row["members_on_board"], row["n_members_on_board"] = [], 0
    assert build_diagnostics(audit)["baskets"][0]["visibility"] == "not_visible"


@pytest.mark.parametrize("raw", [b"{", b"\xff", b"[]", b'{}',
    b'{"schema":"wrong"}',
    b'{"schema":"wrong","schema":"prophet_miss_audit/v1"}',
    b'[' * 1500 + b']' * 1500])
def test_malformed_sources_fail_closed(tmp_path, raw):
    write(tmp_path, raw)
    result = read_diagnostics(tmp_path)
    assert result["available"] is False and result["status"] == "unavailable"
    assert result["populations"]["universe"] is None and result["baskets"] == []
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("root", [None, [], {}, {"schema": "other"}])
def test_direct_builder_checks_source_schema(root):
    assert build_diagnostics(root)["available"] is False


def test_missing_symlink_directory_and_oversize(tmp_path):
    assert read_diagnostics(tmp_path)["reasons"] == ["source_missing"]
    path = tmp_path / SOURCE_PATH
    path.parent.mkdir(parents=True)
    target = tmp_path / "target.json"
    target.write_text("{}")
    path.symlink_to(target)
    assert read_diagnostics(tmp_path)["reasons"] == ["source_symlink"]
    path.unlink()
    path.mkdir()
    assert read_diagnostics(tmp_path)["available"] is False
    path.rmdir()
    path.write_bytes(b" " * (MAX_BYTES + 1))
    assert read_diagnostics(tmp_path)["reasons"] == ["source_oversize"]


def test_contradictory_member_count_is_not_visible(audit):
    audit["basket_misses"]["baskets"][0]["n_members_on_board"] = 7
    result = build_diagnostics(audit)
    assert result["baskets"][0]["visibility"] == "unknown"
    assert "basket_counts_inconsistent" in result["reasons"]
