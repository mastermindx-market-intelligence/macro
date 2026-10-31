"""INTL-GS-W3B (IM16): the market-by-capability acceptance matrix tests.

Integer jurisdiction counts only (never a percentage, ratio, share or float),
exact agreement with the IM11 coverage summary, the permitted-measures law,
missing-data non-improvement, and the R14 §10.6 coverage-board projection
that can never show more coverage than IM11 records.
"""
from __future__ import annotations

import ast
import copy
import re
from pathlib import Path

import pytest

import engine.intl_global_acceptance_matrix as am
from engine.intl_global_universe import (
    CAPABILITIES,
    CAPABILITY_STATES,
    STATE_RANK,
    TARGET_JURISDICTIONS,
    UniverseError,
    coverage_summary,
    load_rights_matrix,
    load_universe,
    roster_digest,
)
from engine.theme_graph.rights import EMISSION_OK

BANNED_KEY_TOKENS = {
    "pct", "percent", "percentage", "ratio", "share", "fraction",
    "proportion", "rate",
}

QUALIFIED_ENTRY = {
    "state": "qualified",
    "reason": "fixture_qualified_probe",
    "evidence_ref": "fixture",
    "rights_ref": None,
}

#: The R14 §10.6 board's six data columns, in order.
BOARD_COLUMNS = ["index_close", "fx_fix", "yield_10y", "cds_5y",
                 "usd_funding", "us_proxy"]


def _assert_counts_only(node, path="root"):
    if isinstance(node, dict):
        for key, value in node.items():
            tokens = {t for t in re.split(r"[^A-Za-z0-9]+", str(key)) if t}
            assert not tokens & BANNED_KEY_TOKENS, f"banned key token at {path}.{key}"
            _assert_counts_only(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for pos, item in enumerate(node):
            _assert_counts_only(item, f"{path}[{pos}]")
    else:
        assert not isinstance(node, float), f"float leaf at {path}: {node!r}"
        if isinstance(node, str):
            assert "%" not in node, f"percent character at {path}: {node!r}"


# --------------------------------------------------------------------------
# 1. shape


def test_shape():
    universe = load_universe()
    matrix = am.acceptance_matrix(universe=universe)
    assert set(matrix) == {
        "matrix_version", "universe_version", "roster_digest", "measurement",
        "denominator", "capabilities", "states", "requirement_state", "cells",
        "by_capability", "by_region", "claims", "coverage_board",
        "im16_complete", "blocking"}
    assert matrix["matrix_version"] == "intl-im16-acceptance-matrix-v1"
    assert matrix["universe_version"] == universe["universe_version"]
    assert matrix["roster_digest"] == roster_digest(universe["jurisdictions"])
    assert matrix["measurement"] == "jurisdiction_count"
    assert matrix["denominator"] == TARGET_JURISDICTIONS == 63
    assert matrix["capabilities"] == list(CAPABILITIES)
    assert len(matrix["capabilities"]) == 7
    assert matrix["states"] == list(CAPABILITY_STATES)
    assert matrix["requirement_state"] == "qualified"
    ids = sorted(universe["jurisdictions"])
    assert sorted(matrix["cells"]) == ids
    assert "EZ" not in matrix["cells"]
    for jid in ids:
        assert set(matrix["cells"][jid]) == set(CAPABILITIES)
        for capability in CAPABILITIES:
            cell = matrix["cells"][jid][capability]
            assert set(cell) == {"state", "reason", "rights_ref"}
            entry = universe["jurisdictions"][jid]["capabilities"][capability]
            assert cell == {"state": entry["state"], "reason": entry["reason"],
                            "rights_ref": entry["rights_ref"]}
    # module-level constants
    assert am.IM16_REQUIRED_CAPABILITIES == (
        "local_rates_credit", "dollar_funding_external",
        "us_exposure_transmission")
    assert am.REQUIREMENT_STATE == "qualified"
    assert am.CLAIMS == {
        "em_credit": "local_rates_credit",
        "dollar_funding": "dollar_funding_external",
        "external_vulnerability": "dollar_funding_external",
        "us_exposure": "us_exposure_transmission"}
    assert [c[0] for c in am.COVERAGE_BOARD_COLUMNS] == BOARD_COLUMNS
    # the module imports no pandas (contract module, counts only)
    tree = ast.parse(Path(am.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert not any(name == "pandas" or name.startswith("pandas.")
                   for name in imported)
    assert imported <= {
        "engine.intl_global_universe", "engine.theme_graph.rights",
        "engine.intl_global_dollar_credit", "__future__", "copy", "json",
        "math", "re", "statistics"}


# --------------------------------------------------------------------------
# 2. COUNTS-ONLY pin (mandatory)


def test_counts_only_output():
    matrix = am.acceptance_matrix()
    _assert_counts_only(matrix)
    assert matrix["denominator"] == 63


# --------------------------------------------------------------------------
# 3. agreement with the IM11 coverage summary


def test_by_capability_equals_coverage_summary():
    universe = load_universe()
    matrix = am.acceptance_matrix(universe=universe)
    for capability in CAPABILITIES:
        summary = coverage_summary(universe, capability)
        block = matrix["by_capability"][capability]
        assert block["by_state"] == summary["by_state"]
        assert block["emission_permitted"] == summary["emission_permitted"]
        assert sum(block["by_state"].values()) == 63
        assert block["met"] + block["gap"] == 63
        assert block["gap"] == 63 - block["met"]
        assert block["required_for_im16"] == (
            capability in am.IM16_REQUIRED_CAPABILITIES)


# --------------------------------------------------------------------------
# 4. real facts on the current universe


def test_real_universe_facts():
    matrix = am.acceptance_matrix()
    assert matrix["im16_complete"] is False
    assert matrix["blocking"] == [
        "dollar_funding_external", "local_rates_credit",
        "us_exposure_transmission"]
    local = matrix["by_capability"]["local_rates_credit"]
    assert local["by_state"]["unavailable"] == 58
    assert local["by_state"]["partial"] == 5
    assert local["met"] == 0 and local["gap"] == 63
    funding = matrix["by_capability"]["dollar_funding_external"]
    assert funding["by_state"]["unavailable"] == 63
    assert funding["met"] == 0 and funding["gap"] == 63
    exposure = matrix["by_capability"]["us_exposure_transmission"]
    assert exposure["by_state"]["unavailable"] == 63
    assert exposure["met"] == 0 and exposure["gap"] == 63
    credit = matrix["claims"]["em_credit"]
    assert credit["gap_ids_by_state"]["unavailable"] and len(
        credit["gap_ids_by_state"]["unavailable"]) == 58
    assert credit["gap_ids_by_state"]["partial"] == ["AU", "GB", "IN", "JP", "KR"]
    assert credit["gap_by_reason"] == {"no_admitted_source": 58,
                                       "fred_10y_only_no_curve_or_credit": 5}


# --------------------------------------------------------------------------
# 5. missing-data non-improvement / monotonicity


def test_all_qualified_universe_completes_and_downgrades_never_improve():
    universe = load_universe()
    baseline = am.acceptance_matrix(universe=universe)

    all_qualified = copy.deepcopy(universe)
    for jur in all_qualified["jurisdictions"].values():
        for capability in CAPABILITIES:
            jur["capabilities"][capability] = dict(QUALIFIED_ENTRY)
    complete = am.acceptance_matrix(universe=all_qualified)
    assert complete["im16_complete"] is True
    assert complete["blocking"] == []
    assert all(complete["by_capability"][c]["met"] == 63 for c in CAPABILITIES)

    for state in [s for s in CAPABILITY_STATES if s != "qualified"]:
        downgraded = copy.deepcopy(all_qualified)
        downgraded["jurisdictions"]["BR"]["capabilities"][
            "dollar_funding_external"] = {**QUALIFIED_ENTRY, "state": state}
        probe = am.acceptance_matrix(universe=downgraded)
        assert probe["by_capability"]["dollar_funding_external"]["met"] == 62
        assert probe["im16_complete"] is False
        for capability in CAPABILITIES:
            assert (probe["by_capability"][capability]["met"]
                    <= complete["by_capability"][capability]["met"])

    # downgrading cells on the REAL universe never increases any met count
    # and never completes IM16
    for jid in ("BR", "JP", "DE", "AE"):
        for state in ("partial", "delayed", "unavailable", "denied",
                      "not_applicable", "suspended", "market_closed",
                      "retained_stale"):
            probe_universe = copy.deepcopy(universe)
            probe_universe["jurisdictions"][jid]["capabilities"][
                "local_rates_credit"] = {**QUALIFIED_ENTRY, "state": state}
            probe = am.acceptance_matrix(universe=probe_universe)
            for capability in CAPABILITIES:
                assert (probe["by_capability"][capability]["met"]
                        <= baseline["by_capability"][capability]["met"])
            assert probe["im16_complete"] is False


# --------------------------------------------------------------------------
# 6. UniverseError on malformed universes


def test_universe_error_cases():
    def drop_capability():
        broken = copy.deepcopy(load_universe())
        del broken["jurisdictions"]["BR"]["capabilities"]["macro_policy"]
        am.acceptance_matrix(universe=broken)

    def unknown_state():
        broken = copy.deepcopy(load_universe())
        broken["jurisdictions"]["BR"]["capabilities"]["macro_policy"][
            "state"] = "bogus"
        am.acceptance_matrix(universe=broken)

    def sixty_two():
        broken = copy.deepcopy(load_universe())
        broken["jurisdictions"].pop("BR")
        am.acceptance_matrix(universe=broken)

    for broken in (drop_capability, unknown_state, sixty_two):
        with pytest.raises(UniverseError):
            broken()


# --------------------------------------------------------------------------
# 7. permitted-measures law


def test_permitted_measures_law():
    matrix = am.acceptance_matrix()
    rows = {row["id"]: row for row in load_rights_matrix()["rows"]}
    for claim, measures in am.PERMITTED_MEASURES.items():
        for measure in measures:
            assert set(measure) == {
                "measure", "level", "satisfies_jurisdiction_requirement",
                "candidate_rights_refs"}
            if measure["satisfies_jurisdiction_requirement"]:
                assert measure["level"] == "jurisdiction"
            if measure["level"] in ("regional_system", "global_context"):
                assert not measure["satisfies_jurisdiction_requirement"]
            for ref in measure["candidate_rights_refs"]:
                assert ref in rows, f"{claim}:{ref} names no rights-matrix row"
    sovereign = next(
        m for m in am.PERMITTED_MEASURES["em_credit"]
        if m["measure"] == "jurisdiction_sovereign_spread")
    assert sovereign["candidate_rights_refs"] == []
    assert sovereign["satisfies_jurisdiction_requirement"] is True

    # the resolved refs in the output carry today's real rights classes
    for claim, block in matrix["claims"].items():
        assert block["capability"] == am.CLAIMS[claim]
        for measure in block["permitted_measures"]:
            for resolved in measure["candidate_rights_refs"]:
                row = rows[resolved["id"]]
                assert resolved["rights_class"] == row["rights_class"]
                assert resolved["emission_ok"] == (
                    row["rights_class"] in EMISSION_OK)
                assert resolved["emission_ok"] is False or (
                    resolved["id"]
                    == "intl_yahoo_eod.legacy_seven_configured_index_fx_series")
            if measure["satisfies_jurisdiction_requirement"]:
                assert measure["level"] == "jurisdiction"
    spot_fx = next(
        m for m in matrix["claims"]["dollar_funding"]["permitted_measures"]
        if m["measure"] == "spot_fx")
    legacy = spot_fx["candidate_rights_refs"][0]
    assert legacy["id"] == "intl_yahoo_eod.legacy_seven_configured_index_fx_series"
    assert legacy["emission_ok"] is True
    assert spot_fx["satisfies_jurisdiction_requirement"] is False
    assert set(matrix["claims"]) == set(am.CLAIMS)


# --------------------------------------------------------------------------
# 8. by_region aggregation


def test_by_region_aggregates():
    universe = load_universe()
    matrix = am.acceptance_matrix(universe=universe)
    regions = {jur["region"] for jur in universe["jurisdictions"].values()}
    assert set(matrix["by_region"]) == regions
    region_counts = {}
    for jur in universe["jurisdictions"].values():
        region_counts[jur["region"]] = region_counts.get(jur["region"], 0) + 1
    for region in matrix["by_region"]:
        for capability in CAPABILITIES:
            per_state = matrix["by_region"][region][capability]
            assert sum(per_state.values()) == region_counts[region]
    for capability in CAPABILITIES:
        for state in CAPABILITY_STATES:
            total = sum(matrix["by_region"][r][capability][state]
                        for r in matrix["by_region"])
            assert total == matrix["by_capability"][capability]["by_state"][state]


# --------------------------------------------------------------------------
# 9. coverage board projection


def test_coverage_board():
    universe = load_universe()
    universe_before = copy.deepcopy(universe)
    matrix = am.acceptance_matrix(universe=universe)
    board = matrix["coverage_board"]
    assert board["columns"] == BOARD_COLUMNS
    assert board["cell_total"] == 63 * 6
    assert sum(board["by_state_total"].values()) == board["cell_total"]
    ids = sorted(universe["jurisdictions"])
    for jid in ids:
        assert set(board["cells"][jid]) == set(BOARD_COLUMNS)
        for column_id, capability, _measure in am.COVERAGE_BOARD_COLUMNS:
            cell = board["cells"][jid][column_id]
            capability_state = matrix["cells"][jid][capability]["state"]
            assert STATE_RANK[cell["state"]] <= STATE_RANK[capability_state]
            if column_id == "cds_5y":
                assert cell == {"state": "unavailable",
                                "reason": "no_admitted_source"}
    for column_id in BOARD_COLUMNS:
        assert sum(board["by_column"][column_id].values()) == 63
    assert board["by_column"]["cds_5y"] == {
        **{state: 0 for state in CAPABILITY_STATES}, "unavailable": 63}
    # a capability may go qualified, the CDS column still cannot
    all_qualified = copy.deepcopy(universe)
    for jur in all_qualified["jurisdictions"].values():
        jur["capabilities"]["local_rates_credit"] = dict(QUALIFIED_ENTRY)
    qualified_board = am.acceptance_matrix(universe=all_qualified)[
        "coverage_board"]
    for jid in ids:
        assert qualified_board["cells"][jid]["cds_5y"] == {
            "state": "unavailable", "reason": "no_admitted_source"}

    # determinism and input immutability
    again = am.acceptance_matrix(universe=universe)
    assert again == matrix
    assert universe == universe_before

    rights = load_rights_matrix()
    rights_before = copy.deepcopy(rights)
    am.acceptance_matrix(rights_matrix=rights)
    assert rights == rights_before
