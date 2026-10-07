from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


passports = _load("toi_w1_passports", "scripts/research/validate_toi_w1_passports.py")
equiv = _load("toi_w1_equiv", "scripts/research/validate_toi_w1_equivalence.py")
sources = _load("toi_w1_sources", "scripts/research/validate_toi_w1_sources.py")
residuals = _load("toi_w1_residuals", "scripts/research/validate_toi_w1_residuals.py")


def _rows():
    return passports._load_jsonl(passports.PASSPORTS)


def _source_map():
    payload = json.loads(sources.SOURCES.read_text(encoding="utf-8"))
    return sources.validate_sources(payload)


def _residual_payload():
    return json.loads(residuals.RESIDUALS.read_text(encoding="utf-8"))


def test_current_passports_validate():
    result = passports.validate_rows(_rows(), passports._source_ids())
    assert result["status"] == "valid"
    assert result["count"] == 32
    assert result["exact_local_count"] == 24
    assert result["priority_counts"]["P0"] == 12
    assert result["priority_counts"]["P1"] == 10
    assert result["priority_counts"]["P2"] == 8
    assert result["priority_counts"]["archive"] == 2


def test_unknown_passport_key_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["mystery"] = "not in schema"
    with pytest.raises(ValueError, match="schema mismatch"):
        passports.validate_rows(rows, passports._source_ids())


def test_duplicate_method_id_fails_closed():
    rows = copy.deepcopy(_rows())
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError, match="duplicate method_id"):
        passports.validate_rows(rows, passports._source_ids())


def test_invalid_dnr_identifier_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["dnd_keys"] = ["KILL-OUTCOME-AUDITION"]
    with pytest.raises(ValueError, match="stable DNR"):
        passports.validate_rows(rows, passports._source_ids())


def test_exact_local_without_signal_ids_fails_closed():
    rows = copy.deepcopy(_rows())
    exact = next(row for row in rows if row["method_id"] == "toi.bb_kc_squeeze")
    exact["local_implementation"]["signal_ids"] = []
    with pytest.raises(ValueError, match="requires paths and signal_ids"):
        passports.validate_rows(rows, passports._source_ids())


def test_exact_local_missing_path_fails_closed():
    rows = copy.deepcopy(_rows())
    exact = next(row for row in rows if row["method_id"] == "toi.bb_kc_squeeze")
    exact["local_implementation"]["paths"] = ["engine/does_not_exist.py"]
    with pytest.raises(ValueError, match="exact local path missing"):
        passports.validate_rows(rows, passports._source_ids())


def test_exact_local_unknown_signal_id_fails_closed():
    rows = copy.deepcopy(_rows())
    exact = next(row for row in rows if row["method_id"] == "toi.bb_kc_squeeze")
    exact["local_implementation"]["signal_ids"] = ["definitely_not_a_real_signal_id"]
    with pytest.raises(ValueError, match="signal_id .* not found"):
        passports.validate_rows(rows, passports._source_ids())


def test_dynamic_registry_signal_ids_are_accepted():
    ma = next(row for row in _rows() if row["method_id"] == "toi.ma_trend")
    passports._validate_exact_local_identity(
        ma["method_id"], ma["local_implementation"]
    )


def test_dynamic_registry_signal_id_must_exist_exactly():
    rows = copy.deepcopy(_rows())
    ma = next(row for row in rows if row["method_id"] == "toi.ma_trend")
    ma["local_implementation"]["signal_ids"][0] = "golden_cross_8_35"
    with pytest.raises(ValueError, match="signal_id .* not found"):
        passports.validate_rows(rows, passports._source_ids())


def test_p0_unreceipted_source_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["source_refs"] = ["SRC-NOT-REAL"]
    rows[0]["rights_ref"] = "SRC-NOT-REAL"
    with pytest.raises(ValueError, match="requires a receipted source"):
        passports.validate_rows(rows, passports._source_ids())


def test_current_equivalence_map_validates():
    ids, alias_map = equiv._methods()
    payload = json.loads(equiv.EQUIV.read_text(encoding="utf-8"))
    result = equiv.validate(payload, ids, alias_map)
    assert result["status"] == "valid"
    assert result["method_count"] == 32
    assert result["class_count"] == 29


def test_equivalence_duplicate_membership_fails_closed():
    ids, alias_map = equiv._methods()
    payload = json.loads(equiv.EQUIV.read_text(encoding="utf-8"))
    bad = copy.deepcopy(payload)
    duplicate = copy.deepcopy(bad["classes"][0]["members"][0])
    # Preserve the destination class's exactly-one-first_class invariant so the
    # hostile fixture reaches the cross-class membership guard we intend to test.
    duplicate["relationship"] = "parameter_variant"
    bad["classes"][1]["members"].append(duplicate)
    with pytest.raises(ValueError, match="membership mismatch"):
        equiv.validate(bad, ids, alias_map)


def test_alias_misresolution_fails_closed():
    ids, alias_map = equiv._methods()
    payload = json.loads(equiv.EQUIV.read_text(encoding="utf-8"))
    bad = copy.deepcopy(payload)
    bad["alias_index"]["BB Width"] = "toi.bb_kc_squeeze"
    with pytest.raises(ValueError, match="misresolved"):
        equiv.validate(bad, ids, alias_map)


def test_current_source_receipts_validate():
    source_map = _source_map()
    result = sources.validate_passport_bindings(source_map)
    assert result["status"] == "valid"
    assert result["passport_count"] == 32
    assert result["p0_p1_count"] == 22


def test_practitioner_source_is_registered_but_cannot_satisfy_p0_p1_primary_gate():
    source_map = _source_map()
    assert source_map["SRC-STRAT-PUBLIC"]["source_type"] == "public_practitioner_methodology"
    refs = ["SRC-STRAT-PUBLIC"]
    acceptable = [source_map[ref] for ref in refs if source_map[ref]["source_type"] in sources.PRIMARY_OR_OFFICIAL_SOURCE_TYPES]
    assert acceptable == []


def test_method_specific_official_sources_replace_overbroad_catalog_bindings():
    source_map = _source_map()
    rows = {row["method_id"]: row for row in _rows()}
    expected_single = {
        "toi.hvr": "SRC-TRADINGVIEW-HISTVOL",
        "toi.nr7": "SRC-CRABEL-NR7-CREATOR",
        "toi.donchian_breakout": "SRC-TRADINGVIEW-DONCHIAN",
        "toi.donchian_fakeout": "SRC-TRADINGVIEW-DONCHIAN",
        "toi.fractal_swing_structure": "SRC-METATRADER-FRACTALS",
        "toi.benchmark_rs": "SRC-STOCKCHARTS-PRICE-RELATIVE",
        "toi.cmf": "SRC-TRADINGVIEW-CMF",
        "toi.rvol": "SRC-STOCKCHARTS-RVOL",
        "toi.choppiness": "SRC-TRADINGVIEW-CHOPPINESS",
        "toi.ulcer": "SRC-TRADINGVIEW-ULCER",
    }
    for mid, ref in expected_single.items():
        assert rows[mid]["source_refs"] == [ref]
        assert rows[mid]["rights_ref"] == ref
        assert source_map[ref]["source_type"] in sources.PRIMARY_OR_OFFICIAL_SOURCE_TYPES
    squeeze = rows["toi.bb_kc_squeeze"]
    assert squeeze["source_refs"] == ["SRC-BOLLINGER-OFFICIAL", "SRC-TRADINGVIEW-KELTNER"]
    assert all(source_map[ref]["source_type"] in sources.PRIMARY_OR_OFFICIAL_SOURCE_TYPES for ref in squeeze["source_refs"])


def test_connors_rsi_has_method_specific_32100_receipt_and_stays_p2():
    source_map = _source_map()
    rows = {row["method_id"]: row for row in _rows()}
    crsi = rows["toi.connors_rsi"]
    assert crsi["source_refs"] == ["SRC-STOCKCHARTS-CONNORS-RSI"]
    assert crsi["rights_ref"] == "SRC-STOCKCHARTS-CONNORS-RSI"
    assert source_map["SRC-STOCKCHARTS-CONNORS-RSI"]["source_type"] == "official_platform_formula_documentation"
    assert crsi["formula"]["parameters"] == {"rsi": 3, "streak_rsi": 2, "percent_rank": 100}
    assert crsi["research_priority"] == "P2"
    assert crsi["owner_disposition"] == "terminal_display"


def test_bb_bandwidth_numeric_binding_is_partial_not_band_walk():
    rows = {row["method_id"]: row for row in _rows()}
    bb = rows["toi.bb_bandwidth"]
    assert bb["local_implementation"]["status"] == "partial"
    assert bb["local_implementation"]["paths"] == [
        "engine/stock_technicals.py",
        "engine/entry_primitives.py",
    ]
    assert bb["local_implementation"]["signal_ids"] == ["bb_bandwidth", "bbwp_series"]
    assert "strictly-prior full-window percentile" in bb["known_failure_modes"][0]
    assert "band rejection/walk grammar" in bb["known_failure_modes"][1]


def test_donchian_fakeout_latest_break_reset_is_explicit_partial():
    rows = {row["method_id"]: row for row in _rows()}
    fake = rows["toi.donchian_fakeout"]
    assert fake["local_implementation"]["status"] == "partial"
    assert fake["local_implementation"]["paths"] == ["engine/compression_signals.py"]
    assert fake["local_implementation"]["signal_ids"] == ["donch_fail_up", "donch_fail_dn"]
    assert "most recent breakout" in fake["known_failure_modes"][0]
    source = (ROOT / "engine/compression_signals.py").read_text(encoding="utf-8")
    assert "if break_arr[i]:" in source
    assert "last_break_idx = i" in source


def test_local_coverage_counts_match_passports_after_grouped_semantic_repair():
    rows = _rows()
    counts = {"exact": 0, "partial": 0, "missing": 0}
    for row in rows:
        status = row["local_implementation"]["status"]
        if status in counts:
            counts[status] += 1
    coverage = json.loads(
        (ROOT / "research/technical_opportunity/w1_local_coverage.json").read_text(
            encoding="utf-8"
        )
    )
    summary = coverage["summary"]
    assert counts == {"exact": 24, "partial": 3, "missing": 5}
    assert summary["exact_local"] == counts["exact"]
    assert summary["partial_local"] == counts["partial"]
    assert summary["missing_local"] == counts["missing"]
    assert summary["p0_exact_local"] == 9
    assert summary["p0_partial_local"] == 3
    assert summary["partial_method_ids"] == [
        "toi.bb_bandwidth",
        "toi.donchian_fakeout",
        "toi.rvol",
    ]


def test_rvol_source_formula_and_local_mismatch_are_explicit():
    source_map = _source_map()
    rows = {row["method_id"]: row for row in _rows()}
    rvol = rows["toi.rvol"]
    assert rvol["source_refs"] == ["SRC-STOCKCHARTS-RVOL"]
    assert rvol["rights_ref"] == "SRC-STOCKCHARTS-RVOL"
    assert source_map["SRC-STOCKCHARTS-RVOL"]["source_type"] == "official_platform_formula_documentation"
    assert rvol["formula"]["parameters"]["length"] == 20
    assert "excluding the current bar" in rvol["formula"]["declarative_steps"][0]
    assert rvol["local_implementation"]["status"] == "partial"
    assert "inclusive 20-bar SMA denominator" in rvol["known_failure_modes"][0]
    assert rvol["research_priority"] == "P0"


def test_inside_bar_practitioner_family_is_not_p0_or_p1_authority():
    rows = {row["method_id"]: row for row in _rows()}
    inside = rows["toi.inside_bar"]
    assert inside["source_refs"] == ["SRC-STRAT-PUBLIC"]
    assert inside["research_priority"] == "P2"
    assert inside["owner_disposition"] == "toi_later_context"
    assert "primary-or-official" in inside["known_failure_modes"][0]


def test_residual_family_census_validates_and_stays_out_of_first_w3():
    result = residuals.validate(_residual_payload())
    assert result == {
        "status": "valid",
        "family_count": 10,
        "family_counts": {"P2": 6, "archive": 2, "blocked": 2, "total": 10},
    }


def test_residual_duplicate_family_fails_closed():
    bad = copy.deepcopy(_residual_payload())
    bad["families"].append(copy.deepcopy(bad["families"][0]))
    with pytest.raises(ValueError, match="exactly 10 families"):
        residuals.validate(bad)


def test_residual_bad_dnr_fails_closed():
    bad = copy.deepcopy(_residual_payload())
    bad["families"][0]["dnr_keys"] = ["KILL-PM3-GAP-MAP"]
    with pytest.raises(ValueError, match="invalid DNR key"):
        residuals.validate(bad)


def test_residual_blocked_family_cannot_become_active():
    bad = copy.deepcopy(_residual_payload())
    row = next(r for r in bad["families"] if r["research_priority"] == "blocked")
    row["owner_disposition"] = "toi_later_context"
    with pytest.raises(ValueError, match="blocked family must fail closed"):
        residuals.validate(bad)


def test_residual_outcome_read_fails_closed():
    bad = copy.deepcopy(_residual_payload())
    bad["outcomes_read"] = True
    with pytest.raises(ValueError, match="outcome-blind"):
        residuals.validate(bad)


def test_elliott_sources_are_evidence_not_authority():
    source_map = _source_map()
    assert source_map["SRC-VANTUCH-ELLIOTT-2018"]["source_type"] == "primary_academic"
    assert "hybrid" in source_map["SRC-JARUSEK-ELLIOTT-2022"]["limitation"].lower()
    rows = {row["method_id"]: row for row in _rows()}
    ew = rows["toi.ordered_path_elliott"]
    assert ew["research_priority"] == "P2"
    assert ew["owner_disposition"] == "toi_later_context"
    assert ew["local_implementation"]["status"] == "missing"
    assert ew["baseline_to_beat"] == "generic causal swing geometry with the same feature budget"
    assert "DNR:KILL-OUTCOME-AUDITION" in ew["dnd_keys"]


def test_incumbent_and_blocked_adaptive_families_do_not_become_w3_candidates():
    rows = {row["method_id"]: row for row in _rows()}
    assert rows["toi.macd_stoch_incumbent"]["owner_disposition"] == "existing_species"
    assert rows["toi.macd_stoch_incumbent"]["research_priority"] == "archive"
    for mid in ("toi.kama_er", "toi.supertrend", "toi.connors_rsi"):
        assert rows[mid]["owner_disposition"] != "toi_w3_candidate"


def test_duplicate_source_receipt_fails_closed():
    payload = json.loads(sources.SOURCES.read_text(encoding="utf-8"))
    bad = copy.deepcopy(payload)
    bad["receipts"].append(copy.deepcopy(bad["receipts"][0]))
    with pytest.raises(ValueError, match="duplicate source_ref"):
        sources.validate_sources(bad)


def test_opaque_source_cannot_receive_active_owner():
    rows = copy.deepcopy(_rows())
    rows[0]["rights_class"] = "opaque"
    rows[0]["owner_disposition"] = "toi_w3_candidate"
    with pytest.raises(ValueError, match="opaque/blocked"):
        passports.validate_rows(rows, passports._source_ids())
