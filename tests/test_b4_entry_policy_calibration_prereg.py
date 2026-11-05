import json
from pathlib import Path


PREREG_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "prophet_v4"
    / "b4_entry_policy_calibration"
    / "PREREG.json"
)


def load_prereg():
    return json.loads(PREREG_PATH.read_text())


def resolve_cell_aliases(registration):
    aliases = registration["alias_map"]
    cell_ids = {cell["id"] for cell in registration["cells"]}
    resolved = [aliases.get(cell_id, cell_id) for cell_id in (cell["id"] for cell in registration["cells"])]
    return {cell_id if cell_id in cell_ids else aliases[cell_id] for cell_id in resolved}


def test_alias_map_collapses_to_six_existing_distinct_configurations():
    registration = load_prereg()
    aliases = registration["alias_map"]
    cell_ids = {cell["id"] for cell in registration["cells"]}
    resolved_configurations = resolve_cell_aliases(registration)

    assert aliases == {
        "C6_TIGHT_LIQUIDITY_BASELINE_GAP": "C2_TIGHT_LIQUIDITY",
        "C7_BASELINE_LIQUIDITY_TIGHT_GAP": "C4_TIGHT_GAP",
    }
    assert registration["distinct_configurations"] == 6
    assert resolved_configurations == set(registration["distinct_cell_ids"])
    assert len(resolved_configurations) == 6
    assert registration["distinct_cell_ids"] == [
        "C0_OBSERVE_ONLY",
        "C1_CURRENT_BASELINE",
        "C2_TIGHT_LIQUIDITY",
        "C3_WIDE_LIQUIDITY",
        "C4_TIGHT_GAP",
        "C5_WIDE_GAP",
    ]
    assert all(target in {cell["id"] for cell in registration["cells"]} for target in aliases.values())
    assert all(target in cell_ids for target in aliases.values())


def test_primary_endpoint_and_horizon_are_singular():
    registration = load_prereg()

    assert registration["primary_endpoint"] == "mae"
    assert registration["primary_horizon_sessions"] == 10
    supporting = registration["outcomes"]["supporting_descriptive_only"]
    assert supporting["metrics"] == [
        metric
        for metric in registration["outcomes"]["required_metrics"]
        if metric != "mae"
    ]
    assert supporting["horizons_sessions"] == [3, 5, 15]
    assert supporting["rescue_authority"] is False


def test_multiplicity_uses_holm_and_declared_search_family():
    registration = load_prereg()
    multiplicity = registration["multiplicity"]

    assert multiplicity["method"] == "Holm"
    assert multiplicity["family"] == registration["distinct_cell_ids"][1:6]
    assert multiplicity["endpoint"] == "mae"
    assert multiplicity["horizon_sessions"] == 10
    assert multiplicity["search_family_includes"] == [
        "EL_H10_timing_study_registered_under_D06"
    ]


def test_looks_and_futility_are_pre_registered():
    registration = load_prereg()

    assert registration["looks"] == {
        "fixed_episode_count_per_distinct_cell": 300,
        "monitoring_only_episode_counts": [50, 100],
        "monitoring_can_promote": False,
    }
    assert registration["futility"] == {
        "episode_count_per_cell": 150,
        "rule": (
            "stop as REJECTED if every cell's primary lower confidence "
            "bound excludes improvement"
        ),
    }


def test_decision_law_requires_primary_endpoint_and_non_inferiority():
    registration = load_prereg()
    decision_law = registration["decision_law"]

    assert decision_law["single_primary_endpoint_no_any_of_k"] is True
    assert "the single primary endpoint is maximum adverse excursion at 10 sessions" in (
        decision_law["supported_requires"]
    )
    assert "the lower confidence bound for net excess versus C0 is at least -25 bps" in (
        decision_law["supported_requires"]
    )
    assert "the configuration is Pareto-dominated by C0 or a preregistered challenger" in (
        decision_law["killed_if"]
    )
    assert "missingness or basis incompatibility makes the comparison non-identifiable" in (
        decision_law["killed_if"]
    )
    original_arrays = registration["decision_law"]["superseded_by_A1"]
    assert len(original_arrays["baseline_supported_only_if"]) == 4
    assert len(original_arrays["baseline_killed_if"]) == 3


def test_non_inferiority_and_cost_floor_are_numeric():
    registration = load_prereg()
    non_inferiority = registration["non_inferiority"]

    assert isinstance(non_inferiority["lower_bound_margin_bps"], (int, float))
    assert non_inferiority["lower_bound_margin_bps"] == -25
    assert non_inferiority["comparison"] == "net excess vs C0 at H10"
    assert non_inferiority["nonsignificant_point_estimate_is_non_inferior"] is False
    assert isinstance(registration["cost_floor_bps_round_trip"], (int, float))
    assert registration["cost_floor_bps_round_trip"] == 50
    assert registration["cost_floor_treatment"] == "floor_not_measurement_pending_D08"


def test_refused_rows_and_capture_controls_are_preserved():
    registration = load_prereg()
    amendment = registration["amendments"][0]

    assert registration["refused_rows_treatment"] == "full_opportunity_cash"
    assert amendment["pre_capture"] is True
    assert registration["clock_law"]["historical_backfill"] is False
    assert registration["clock_law"]["cohort_start"] == (
        "FIRST_PROSPECTIVE_B4_OBSERVATION_AFTER_PREREG_MERGE"
    )
    assert all(registration["authority"][flag] is False for flag in registration["authority"] if flag != "research_only")


def test_original_cell_labels_are_retained():
    registration = load_prereg()

    assert [cell["id"] for cell in registration["cells"]] == [
        "C0_OBSERVE_ONLY",
        "C1_CURRENT_BASELINE",
        "C2_TIGHT_LIQUIDITY",
        "C3_WIDE_LIQUIDITY",
        "C4_TIGHT_GAP",
        "C5_WIDE_GAP",
        "C6_TIGHT_LIQUIDITY_BASELINE_GAP",
        "C7_BASELINE_LIQUIDITY_TIGHT_GAP",
    ]
    assert set(registration["decision_law"]["superseded_by_A1"]) == {
        "baseline_supported_only_if",
        "baseline_killed_if",
    }
