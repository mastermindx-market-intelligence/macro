import numpy as np
import pandas as pd
import pytest

from scripts import research_skylit_r6_cross_expiry_topology as r6


def _state(frame, *, gate=True):
    return {
        "root": "SPY",
        "target_gate_pass": gate,
        "decision_eligible_not_before_session": "2026-09-15",
        "base_input_sha256": "a" * 64,
        "settled_oi_input_sha256": "b" * 64,
        "unexpired_identity_contracts": len(frame),
        "model_input_contract_rate": 1.0,
        "settled_oi_contract_rate": 1.0,
        "settled_oi_exposure_mass_coverage_on_prior_known_mass": 1.0,
        "frame": frame,
    }


def _row(exp, strike, exposure, right="C", spot=100.0):
    return {
        "root": "SPY",
        "expiration": exp,
        "strike": float(strike),
        "right": right,
        "spot": float(spot),
        "exposure_gex": float(exposure),
    }


def test_magnitude_distribution_uses_gross_absolute_exposure_not_signed_net():
    frame = pd.DataFrame([
        _row("2026-09-18", 100, 10, "C"),
        _row("2026-09-18", 100, -10, "P"),
        _row("2026-09-18", 105, 5, "C"),
    ])
    spec = r6._coordinate_spec(None)
    work = r6._normalize_frame(frame, "2026-09-14", spec)
    dist = r6._strike_distribution(work)
    at_100 = dist.loc[dist["strike"] == 100.0].iloc[0]
    assert at_100["gross_abs_exposure"] == 20.0
    assert at_100["signed_net_exposure"] == 0.0
    assert dist["gross_abs_exposure"].sum() == 25.0


def test_equal_shape_different_scale_has_zero_wasserstein_and_unit_cosine():
    rows = []
    for strike, exposure in [(95, 1), (100, 2), (105, 1)]:
        rows.append(_row("2026-09-18", strike, exposure))
        rows.append(_row("2026-09-25", strike, exposure * 7))
    got = r6.analyze_state(_state(pd.DataFrame(rows)), "2026-09-14")
    pair = got["adjacent_expiry_geometry"][0]
    assert pair["wasserstein_1_x"] == pytest.approx(0.0, abs=1e-12)
    assert pair["cosine_similarity"] == pytest.approx(1.0, abs=1e-12)
    assert got["outcome_labels_opened"] is False
    assert got["exposure_unit"] == "USD dealer-delta change per +1% spot move"
    assert got["magnitude_semantics"].startswith("gross_absolute")


def test_shifted_expiry_has_positive_centroid_displacement_and_wasserstein():
    rows = []
    for strike, exposure in [(95, 1), (100, 2), (105, 1)]:
        rows.append(_row("2026-09-18", strike, exposure))
    for strike, exposure in [(100, 1), (105, 2), (110, 1)]:
        rows.append(_row("2026-09-25", strike, exposure))
    got = r6.analyze_state(_state(pd.DataFrame(rows)), "2026-09-14")
    pair = got["adjacent_expiry_geometry"][0]
    assert pair["centroid_displacement_x"] > 0
    assert pair["wasserstein_1_x"] > 0
    assert got["summary"]["front_back_centroid_gap_x"] > 0


def test_equal_two_node_distribution_has_entropy_one_hhi_half():
    frame = pd.DataFrame([
        _row("2026-09-18", 95, 1),
        _row("2026-09-18", 105, -1),
    ])
    work = r6._normalize_frame(frame, "2026-09-14", r6._coordinate_spec(None))
    metrics = r6._distribution_metrics(r6._strike_distribution(work))
    assert metrics["normalized_entropy"] == pytest.approx(1.0)
    assert metrics["hhi"] == pytest.approx(0.5)
    assert metrics["effective_node_count"] == pytest.approx(2.0)
    assert metrics["top_node_share"] == pytest.approx(0.5)


def test_expected_move_coordinate_is_explicit_and_changes_scale():
    frame = pd.DataFrame([
        _row("2026-09-18", 95, 1),
        _row("2026-09-18", 105, 1),
    ])
    plain = r6.analyze_state(_state(frame), "2026-09-14")
    em = r6.analyze_state(_state(frame), "2026-09-14", expected_move_pct=2.0)
    assert plain["coordinate"]["em_normalized"] is False
    assert em["coordinate"]["em_normalized"] is True
    assert abs(em["by_expiry"][0]["centroid_x"]) > abs(plain["by_expiry"][0]["centroid_x"])


def test_unqualified_r2_state_refuses_before_topology():
    with pytest.raises(r6.R6Refusal, match="not source-qualified"):
        r6.analyze_state(_state(pd.DataFrame([_row("2026-09-18", 100, 1)]), gate=False), "2026-09-14")


def test_tenor_buckets_preserve_absent_zero_dte_as_absent_not_zero():
    frame = pd.DataFrame([
        _row("2026-09-18", 100, 1),  # 4 DTE
        _row("2026-10-16", 100, 2),  # 32 DTE
    ])
    got = r6.analyze_state(_state(frame), "2026-09-14")
    buckets = {row["tenor_bucket"]: row for row in got["by_tenor"]}
    assert buckets["0DTE"]["present"] is False
    assert buckets["3-7DTE"]["present"] is True
    assert buckets["31-90DTE"]["present"] is True
    assert got["daily_view"]["same_day_expiry_present"] is False
