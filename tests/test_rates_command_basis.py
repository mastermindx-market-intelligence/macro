"""Tests for engine/rates_command_basis.py (B0 seat ruling para-8)."""

import ast
import dataclasses
import json
from datetime import date
from pathlib import Path

import jsonschema
import pytest

from engine.rates_command_basis import (
    NA,
    ComparisonResult,
    ComparisonRule,
    PathAssumptions,
    PathIdentification,
    PathStatus,
    QualifiedObservation,
    RULES,
    SCHEMA_VERSION,
    compare_qualified,
    qualify_observation,
    solve_reference_average,
)

CUTOFF = "2026-10-14T00:00"
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "contracts" / "rates_command_basis.v1.schema.json"
MODULE_PATH = REPO_ROOT / "engine" / "rates_command_basis.py"


def _meta(**over):
    base = dict(
        subject="TEST_SERIES",
        evidence_class="official_measurement",
        unit="pct_mom",
        target="cpi_u_all_items_mom_sa_first_print",
        basket_or_index="CPI-U",
        reference_start="2026-09-01",
        reference_end="2026-09-30",
        observation_time="2026-10-01T08:30",
        observation_precision="minute",
        seasonal_treatment="sa",
        rate_index=NA,
        averaging_law=NA,
        curve_convention=NA,
        tenor=NA,
        model_id=NA,
        target_epoch=NA,
        source="test:series",
        rights="public_official",
        first_public_evidence="2026-10-01T08:30",
        first_public_precision="minute",
    )
    base.update(over)
    return base


def _obs(value=0.2, cutoff=CUTOFF, **over):
    return qualify_observation(value, _meta(**over), cutoff)


def _zq_obs(value=4.25, cutoff=CUTOFF):
    return qualify_observation(
        value,
        dict(
            subject="ZQX26",
            evidence_class="market_implied_expectation",
            unit="pct_ann_rate",
            target="effr_monthly_average",
            basket_or_index="EFFR",
            reference_start="2026-09-01",
            reference_end="2026-09-30",
            observation_time="2026-09-30",
            observation_precision="day",
            seasonal_treatment=NA,
            rate_index="EFFR",
            averaging_law="arithmetic_calendar_day",
            curve_convention=NA,
            tenor=NA,
            model_id=NA,
            target_epoch=NA,
            source="rate_futures:ZQ",
            rights="public_official",
            first_public_evidence="2026-09-30",
            first_public_precision="day",
        ),
        cutoff,
    )


def test_unknown_basis_refuses_numeric_comparison():
    rule = RULES["same_basis_level_change.v1"]
    left = _obs(value=0.2)
    right = _obs(value=0.3, seasonal_treatment=None)
    result = compare_qualified(left, right, rule)
    assert result.status == "not_comparable"
    assert result.reason == "unknown_basis:seasonal_treatment"
    assert result.difference is None
    assert result.range is None


def test_missing_is_not_zero():
    missing = _obs(value=None)
    assert missing.value_state == "missing"
    assert missing.value is None
    result = compare_qualified(missing, _obs(value=0.3), RULES["same_basis_level_change.v1"])
    assert result.status == "unavailable"
    assert result.reason == "operand_missing:left"
    assert result.difference is None  # never 0.0, never a silent neutral


def test_after_cutoff_value_never_leaks():
    late = _obs(value=0.2, observation_time="2026-10-20T09:00")
    assert late.value_state == "refused"
    assert late.value is None
    assert "after_cutoff" in late.limitations
    late_public = _obs(value=0.2, first_public_evidence="2026-10-15")
    assert late_public.value_state == "refused"
    assert late_public.value is None
    assert "after_cutoff" in late_public.limitations
    result = compare_qualified(late, _obs(value=0.3), RULES["same_basis_level_change.v1"])
    assert result.status == "unavailable"
    assert result.reason == "operand_refused:left"
    assert result.difference is None


def test_sr3_vs_zq_refused_without_basis():
    sr3 = _obs(
        value=4.10,
        subject="SR3Z26",
        evidence_class="market_implied_expectation",
        unit="pct_ann_rate",
        target="sofr_compounded_quarter",
        basket_or_index="SOFR",
        reference_start="2026-09-16",
        reference_end="2026-12-15",
        observation_time="2026-09-15",
        rate_index="SOFR",
        averaging_law="compounded_business_day",
        source="rate_futures:SR3",
        first_public_evidence="2026-09-15",
    )
    zq = _zq_obs()
    result = compare_qualified(sr3, zq, RULES["sr3_vs_zq.v1"])
    assert result.status == "not_comparable"
    assert result.reason == "basis_mismatch:rate_index"
    assert result.difference is None


def test_par_vs_zero_refused():
    kwargs = dict(
        subject="DGS10",
        unit="pct_ann_rate",
        basket_or_index="UST",
        reference_start="2026-10-13",
        reference_end="2036-10-15",
        observation_time="2026-10-13",
        observation_precision="day",
        first_public_evidence="2026-10-13",
        first_public_precision="day",
        seasonal_treatment=NA,
        rate_index=NA,
        averaging_law=NA,
        source="fred:DGS10",
    )
    par = _obs(value=4.02, target="ust_par_yield", curve_convention="par", tenor="10y", **kwargs)
    zero = _obs(value=3.95, target="ust_zero_yield", curve_convention="zero", tenor="10y", **kwargs)
    result = compare_qualified(par, zero, RULES["par_vs_zero.v1"])
    assert result.status == "not_comparable"
    assert result.reason == "basis_mismatch:curve_convention"
    assert result.difference is None


def test_cpi_vs_pce_not_comparable():
    cpi = _obs(value=0.2)
    pce = _obs(
        value=0.18,
        subject="PCEPI",
        target="pce_headline_mom_sa",
        basket_or_index="PCE",
        source="fred:PCEPI",
    )
    result = compare_qualified(cpi, pce, RULES["cpi_vs_pce.v1"])
    assert result.status == "not_comparable"
    assert result.reason == "basis_mismatch:basket_or_index"
    assert result.difference is None


def test_forecast_vs_revised_value_rejected_for_first_print_rule():
    rule = RULES["forecast_vs_first_print.v1"]
    forecast = _obs(
        value=0.2,
        evidence_class="house_estimate",
        source="release_forecast:v2",
        model_id="release_forecast:v2",
    )
    revised = _obs(value=0.3, target="cpi_u_all_items_mom_sa_revised")
    rejected = compare_qualified(forecast, revised, rule)
    assert rejected.status == "not_comparable"
    assert rejected.reason == "constraint:target:right"
    assert rejected.difference is None
    first_print = _obs(value=0.3)
    ok = compare_qualified(forecast, first_print, rule)
    assert ok.status == "directly_comparable"
    assert ok.difference == pytest.approx(-10.0)  # (0.2 - 0.3) pct -> bp
    assert ok.unit == "bp"


def test_monthly_average_two_paths_same_average_nonunique():
    # canonical witness (A16/A17): 30-day month, 15d @4.50 + 15d @4.00
    average = (4.50 * 15 + 4.00 * 15) / 30.0
    assert average == pytest.approx(4.25)
    obs = _zq_obs(value=average)
    result = solve_reference_average(
        (obs,),
        PathAssumptions("2026-09-01", "2026-09-30", rate_step_bp=50.0),
    )
    assert result.status is PathStatus.FEASIBLE_ALTERNATIVES
    assert result.identified is None
    assert len(result.alternatives) >= 2
    # the canonical 15/15 path is among the feasible alternatives
    assert any(
        p["segments"][0][1] == "2026-09-16"
        and p["segments"][0][2] == pytest.approx(4.50)
        and p["end_rate"] == pytest.approx(4.00)
        for p in result.alternatives
    )
    # module-derived witness (B0-FIX D4): the -25 bp average and -50 bp level
    # changes are read off the module's own alternatives, not recomputed from
    # local constants. Segment convention (module docstring): segment i spans
    # [b_i, b_{i+1}) calendar days and the FINAL segment carries the
    # month-end day itself, so its length is the remainder of the month.
    n_days = 30

    def path_average(path):
        segs = path["segments"]
        days = [
            (date.fromisoformat(segs[i + 1][0]) - date.fromisoformat(segs[i][0])).days
            for i in range(len(segs) - 1)
        ]
        days.append(n_days - sum(days))
        assert len(days) == len(segs)
        assert sum(days) == n_days
        return sum(s[2] * d for s, d in zip(segs, days)) / n_days

    for path in result.alternatives:
        assert path_average(path) == pytest.approx(4.25, abs=1e-9)
    canonical = next(
        p
        for p in result.alternatives
        if p["segments"][0][1] == "2026-09-16"
        and p["segments"][0][2] == pytest.approx(4.50)
    )
    pre_change_rate = 4.50
    # every alternative path re-averages to 4.25: a -25 bp AVERAGE change
    assert (path_average(canonical) - pre_change_rate) * 100.0 == pytest.approx(-25.0)
    # the canonical 15/15 path's month-end rate is the -50 bp LEVEL change
    assert canonical["end_rate"] - pre_change_rate == pytest.approx(-0.50)
    # non-uniqueness: the feasible month-end rates are not all one value
    end_rates = {p["end_rate"] for p in result.alternatives}
    assert len(end_rates) >= 2
    assert result.end_rate_range is not None
    assert result.end_rate_range[0] < result.end_rate_range[1]


def test_one_meeting_identified_conditional_with_pre_rate():
    obs = _zq_obs(value=4.25)
    result = solve_reference_average(
        (obs,),
        PathAssumptions(
            "2026-09-01",
            "2026-09-30",
            effective_dates=("2026-09-16",),
            pre_change_rate=4.50,
            rate_step_bp=50.0,
        ),
    )
    assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
    identified = result.identified
    assert identified is not None
    seg0, seg1 = identified["segments"]
    assert seg0[0] == "2026-09-01" and seg0[1] == "2026-09-16"
    assert seg0[2] == pytest.approx(4.50)
    assert seg1[0] == "2026-09-16" and seg1[1] == "2026-09-30"
    assert seg1[2] == pytest.approx(4.00)
    assert identified["end_rate"] == pytest.approx(4.00)
    # level change vs the pre-change rate is -50 bp, not the -25 bp average change
    assert (identified["end_rate"] - 4.50) * 100.0 == pytest.approx(-50.0)
    assert result.end_rate_range is not None
    assert result.end_rate_range[0] <= 4.00 <= result.end_rate_range[1]


def test_yield_move_attribution_not_identified_lists_alternatives():
    move = _obs(
        value=30.0,
        subject="DGS10",
        unit="bp",
        target="ust_par_yield_move",
        reference_start="2026-10-10",
        reference_end="2026-10-13",
        observation_time="2026-10-13",
        observation_precision="day",
        first_public_evidence="2026-10-13",
        first_public_precision="day",
        source="fred:DGS10",
    )
    other = _obs(
        value=20.0,
        subject="DGS10",
        unit="bp",
        target="term_premium_move_kw",
        reference_start="2026-10-10",
        reference_end="2026-10-13",
        observation_time="2026-10-13",
        observation_precision="day",
        first_public_evidence="2026-10-13",
        first_public_precision="day",
        source="kw:model",
    )
    result = compare_qualified(move, other, RULES["yield_move_attribution.v1"])
    assert result.status == "not_identified"
    assert result.reason == "underidentified:decomposition"
    assert result.difference is None
    joined = " | ".join(result.limitations)
    assert "expected_short=+10bp + term_premium=+20bp" in joined
    assert "expected_short=-10bp + term_premium=+40bp" in joined


def test_obs_id_is_stable_content_hash():
    base = _obs()
    twin = _obs()
    assert base.obs_id == twin.obs_id
    assert len(base.obs_id) == 16
    int(base.obs_id, 16)  # 16 hex chars
    # obs_id excludes itself: a forged obs_id is recomputed away
    forged = QualifiedObservation.from_dict({**base.to_dict(), "obs_id": "ffffffffffffffff"})
    assert forged.obs_id == base.obs_id
    # any other field changing changes the digest
    mutations = dict(
        value=0.4,
        subject="OTHER_SERIES",
        cutoff="2026-10-15T00:00",
        rights="display_only",
        vintage="2026-10-revision",
        source="test:other",
        observation_time="2026-10-01T09:30",
        quality="stale",
        limitations="extra note",
        seasonal_treatment="nsa",
    )
    for key, new_value in mutations.items():
        if key == "cutoff":
            mutated = _obs(cutoff=new_value)
        else:
            mutated = _obs(**{key: new_value})
        assert mutated.obs_id != base.obs_id, key


def _record_validator(record):
    full = json.loads(SCHEMA_PATH.read_text())
    schema = {"$schema": full["$schema"], "$defs": full["$defs"], "$ref": "#/$defs/%s" % record}
    return jsonschema.Draft202012Validator(schema)


def test_schema_round_trip_validates():
    assert SCHEMA_VERSION == "rates_command_basis.v1"
    observation = _obs()
    comparison = compare_qualified(
        _obs(value=0.2, evidence_class="house_estimate", model_id="release_forecast:v2"),
        _obs(value=0.3),
        RULES["forecast_vs_first_print.v1"],
    )
    path = solve_reference_average(
        (_zq_obs(value=4.25),),
        PathAssumptions("2026-09-01", "2026-09-30", rate_step_bp=50.0),
    )
    for record, instance in (
        ("QualifiedObservation", observation),
        ("ComparisonResult", comparison),
        ("PathIdentification", path),
    ):
        as_dict = instance.to_dict()
        wire = json.loads(json.dumps(as_dict))  # pure-JSON round trip
        _record_validator(record).validate(wire)
        restored = type(instance).from_dict(wire)
        assert restored == instance, record


def test_module_is_pure():
    source = MODULE_PATH.read_text()
    for token in (
        "requests",
        "urllib",
        "open(",
        "datetime.now",
        "date.today",
        "time.time",
        "from engine",
        "import engine",
        "subprocess",
    ):
        assert token not in source, token


def test_zq_vs_midpoint_underidentified_without_explicit_basis():
    zq = _zq_obs(value=4.25)
    midpoint = _obs(
        value=4.375,
        subject="FED_FUNDS_TARGET",
        unit="pct_ann_rate",
        target="fed_funds_target_midpoint",
        basket_or_index="EFFR",
        reference_start="2026-09-01",
        reference_end="2026-09-30",
        observation_time="2026-09-16",
        observation_precision="day",
        seasonal_treatment=NA,
        averaging_law="point",
        curve_convention=NA,
        tenor=NA,
        model_id=NA,
        target_epoch=NA,
        source="fomc:target_range",
        first_public_evidence="2026-09-16",
        first_public_precision="day",
    )
    rule = RULES["zq_month_vs_policy_midpoint.v1"]
    bare = compare_qualified(zq, midpoint, rule)
    assert bare.status == "not_identified"
    assert bare.reason == "underidentified:effr_target_basis"
    assert bare.difference is None
    supplied = compare_qualified(zq, midpoint, rule, context={"effr_minus_midpoint_bp": -12.5})
    assert supplied.status == "comparable_after_transformation"
    assert supplied.transform == "monthly_average_vs_level"
    assert supplied.difference == pytest.approx(0.0)  # B0-FIX6: ZQ 4.25 = 4.375 + (-12.5 bp) is a no-change month
    assert "effr_minus_midpoint_bp=-12.5" in supplied.assumptions


def _midpoint_obs(value=4.375, unit="pct_ann_rate"):
    return _obs(
        value=value,
        subject="FED_FUNDS_TARGET",
        unit=unit,
        target="fed_funds_target_midpoint",
        basket_or_index="EFFR",
        reference_start="2026-09-01",
        reference_end="2026-09-30",
        observation_time="2026-09-16",
        observation_precision="day",
        seasonal_treatment=NA,
        averaging_law="point",
        curve_convention=NA,
        tenor=NA,
        model_id=NA,
        target_epoch=NA,
        source="fomc:target_range",
        first_public_evidence="2026-09-16",
        first_public_precision="day",
    )


def test_zq_vs_midpoint_applies_nonzero_gap_in_bp():
    zq = _zq_obs(value=4.10)
    midpoint = _midpoint_obs()
    rule = RULES["zq_month_vs_policy_midpoint.v1"]
    result = compare_qualified(
        zq, midpoint, rule, context={"effr_minus_midpoint_bp": -7}
    )
    assert result.status == "comparable_after_transformation"
    assert result.difference == pytest.approx(-20.5)
    assert result.unit == "bp"
    assert "effr_minus_midpoint_bp=-7" in result.assumptions
    assert "effr_gap_applied_in=bp" in result.assumptions
    wire = json.loads(json.dumps(result.to_dict()))
    _record_validator("ComparisonResult").validate(wire)


@pytest.mark.parametrize(
    "gap",
    [None, "nan", float("nan"), float("inf"), float("-inf"), "abc", True],
)
def test_zq_vs_midpoint_unusable_gap_is_not_identified(gap):
    zq = _zq_obs(value=4.10)
    midpoint = _midpoint_obs()
    rule = RULES["zq_month_vs_policy_midpoint.v1"]
    result = compare_qualified(
        zq, midpoint, rule, context={"effr_minus_midpoint_bp": gap}
    )
    assert result.status == "not_identified"
    assert result.reason == "underidentified:effr_target_basis"
    assert result.difference is None


@pytest.mark.parametrize("gap", [-12.5, -7.0, 3.25, 10.0])
def test_zq_vs_midpoint_result_differs_from_raw_spread_when_gap_nonzero(gap):
    zq = _zq_obs(value=4.10)
    midpoint = _midpoint_obs()
    rule = RULES["zq_month_vs_policy_midpoint.v1"]
    result = compare_qualified(
        zq, midpoint, rule, context={"effr_minus_midpoint_bp": gap}
    )
    raw_bp = (4.10 - 4.375) * 100.0
    assert result.difference != pytest.approx(raw_bp)
    assert result.difference == pytest.approx(raw_bp - gap)


def test_zq_vs_midpoint_zero_gap_equals_raw_spread():
    zq = _zq_obs(value=4.10)
    midpoint = _midpoint_obs()
    rule = RULES["zq_month_vs_policy_midpoint.v1"]
    result = compare_qualified(
        zq, midpoint, rule, context={"effr_minus_midpoint_bp": 0.0}
    )
    assert result.difference == pytest.approx(-27.5)
    assert result.status == "comparable_after_transformation"


def test_zq_vs_midpoint_gap_in_pct_output_unit():
    zq = _zq_obs(value=4.10)
    midpoint = _midpoint_obs()
    rule = dataclasses.replace(
        RULES["zq_month_vs_policy_midpoint.v1"], output_unit="pct_ann_rate"
    )
    result = compare_qualified(
        zq, midpoint, rule, context={"effr_minus_midpoint_bp": -7}
    )
    assert result.difference == pytest.approx(-0.205)
    assert "effr_gap_applied_in=pct_ann_rate" in result.assumptions


def test_zq_vs_midpoint_mixed_operand_units_not_identified():
    zq = _zq_obs(value=4.10)
    midpoint = _midpoint_obs(value=437.5, unit="bp")
    rule = RULES["zq_month_vs_policy_midpoint.v1"]
    result = compare_qualified(
        zq, midpoint, rule, context={"effr_minus_midpoint_bp": -7}
    )
    assert result.status == "not_identified"
    assert result.reason == "underidentified:effr_target_basis"
    assert result.difference is None


def test_sep_vs_market_needs_year_end_interval_containment():
    kwargs = dict(
        unit="pct_ann_rate",
        basket_or_index=NA,
        seasonal_treatment=NA,
        rate_index=NA,
        averaging_law=NA,
        curve_convention=NA,
        tenor=NA,
        model_id=NA,
        target_epoch=NA,
        observation_time="2026-10-01",
        observation_precision="day",
        first_public_evidence="2026-10-01",
        first_public_precision="day",
    )
    sep = _obs(
        value=3.9,
        subject="sep_median_2026",
        evidence_class="survey_participant_projection",
        target="sep_fed_funds_year_end_median",
        reference_start="2026-12-01",
        reference_end="2026-12-31",
        source="fomc:sep",
        **kwargs,
    )
    market_kwargs = dict(kwargs, evidence_class="market_implied_expectation", source="rate_futures:ZQ")
    covering = _obs(
        value=4.1,
        subject="ZQZ26",
        target="effr_monthly_average",
        reference_start="2026-10-01",
        reference_end="2026-12-31",
        **market_kwargs,
    )
    rule = RULES["sep_vs_market_year_end.v1"]
    ok = compare_qualified(sep, covering, rule)
    assert ok.status == "comparable_after_transformation"
    assert ok.transform == "year_end_interval_match"
    assert "participant appropriate-policy projection, not a committee promise or probability" in ok.limitations
    not_covering = _obs(
        value=4.1,
        subject="ZQU26",
        target="effr_monthly_average",
        reference_start="2026-07-01",
        reference_end="2026-09-30",
        **market_kwargs,
    )
    refused = compare_qualified(sep, not_covering, rule)
    assert refused.status == "not_comparable"
    assert refused.reason == "basis_mismatch:reference_end"


def test_curve_decomposition_rules_are_explicit_transforms():
    kwargs = dict(
        subject="DGS10",
        unit="pct_ann_rate",
        basket_or_index="UST",
        reference_start="2026-10-13",
        reference_end="2036-10-15",
        observation_time="2026-10-13",
        observation_precision="day",
        seasonal_treatment=NA,
        rate_index=NA,
        averaging_law=NA,
        tenor="10y",
        model_id=NA,
        target_epoch=NA,
        source="fred:DGS10",
        first_public_evidence="2026-10-13",
        first_public_precision="day",
    )
    nominal = _obs(value=4.02, target="ust_par_yield", curve_convention="par", **kwargs)
    real_kwargs = {k: v for k, v in kwargs.items() if k not in ("basket_or_index", "source")}
    real = _obs(
        value=1.77,
        target="ust_real_par_yield",
        curve_convention="real_par",
        basket_or_index="TIPS",
        source="fred:DFII10",
        **real_kwargs,
    )
    compensation = compare_qualified(nominal, real, RULES["inflation_compensation.v1"])
    assert compensation.status == "comparable_after_transformation"
    assert compensation.transform == "nominal_minus_real"
    assert compensation.difference == pytest.approx(225.0)
    assert len(compensation.limitations) >= 3  # liquidity / indexation lag / basis
    premium_kwargs = {
        k: v for k, v in kwargs.items() if k not in ("subject", "model_id", "source")
    }
    kw = _obs(
        value=1.50,
        target="term_premium_kw",
        curve_convention=NA,
        model_id="kw_v2",
        source="kw:model",
        **premium_kwargs,
    )
    acm = _obs(
        value=1.10,
        subject="ACM10",
        target="term_premium_acm",
        curve_convention=NA,
        model_id="acm_v1",
        source="acm:model",
        **premium_kwargs,
    )
    disagreement = compare_qualified(kw, acm, RULES["term_premium_kw_vs_acm.v1"])
    assert disagreement.status == "comparable_after_transformation"
    assert disagreement.difference == pytest.approx(40.0)
    assert "model disagreement, not a forecast or signal" in disagreement.limitations


def test_cpi_month_vs_breakeven_horizons_differ():
    cpi_next = _obs(value=0.2, reference_start="2026-10-01", reference_end="2026-10-31")
    breakeven = _obs(
        value=2.25,
        subject="T10YIE",
        unit="pct_yoy",
        target="inflation_compensation",
        basket_or_index=NA,
        reference_start="2026-10-13",
        reference_end="2036-10-15",
        tenor="10y",
        source="fred:T10YIE",
    )
    result = compare_qualified(cpi_next, breakeven, RULES["cpi_month_vs_breakeven_10y.v1"])
    assert result.status == "not_comparable"
    assert result.reason == "basis_mismatch:reference_end"


def test_same_basis_level_change_direct_difference():
    left = _obs(value=0.2)
    right = _obs(value=0.3, reference_start="2026-08-01", reference_end="2026-08-31")
    result = compare_qualified(left, right, RULES["same_basis_level_change.v1"])
    assert result.status == "directly_comparable"
    assert result.transform is None
    assert result.difference == pytest.approx(-10.0)


def test_rights_unknown_blocks_export_purpose():
    export_rule = ComparisonRule(
        rule_id="export_probe.v1",
        version="1",
        purpose="export",
        left_constraints={},
        right_constraints={},
        match_fields=("unit",),
        transform=None,
        output_unit="bp",
    )
    left = _obs(value=0.2, rights="unknown")
    result = compare_qualified(left, _obs(value=0.3), export_rule)
    assert result.status == "not_comparable"
    assert result.reason == "rights_unknown"
    assert result.difference is None


def test_every_comparison_status_reachable():
    seen = set()
    seen.add(
        compare_qualified(_obs(value=None), _obs(value=0.3), RULES["cpi_vs_pce.v1"]).status.value
    )
    seen.add(compare_qualified(_obs(), _obs(basket_or_index="PCE", subject="PCEPI", target="pce_headline_mom_sa"), RULES["cpi_vs_pce.v1"]).status.value)
    seen.add(
        compare_qualified(_obs(), _obs(value=0.2, seasonal_treatment=None), RULES["same_basis_level_change.v1"]).status.value
    )
    seen.add(compare_qualified(_obs(), _obs(value=0.3), RULES["same_basis_level_change.v1"]).status.value)
    seen.add(compare_qualified(
        _obs(value=4.02, curve_convention="par", target="ust_par_yield"),
        _obs(value=1.77, curve_convention="real_par", target="ust_real_par_yield"),
        RULES["inflation_compensation.v1"],
    ).status.value)
    seen.add(compare_qualified(
        _obs(value=30.0, unit="bp", target="ust_par_yield_move"),
        _obs(value=20.0, unit="bp", target="term_premium_move_kw"),
        RULES["yield_move_attribution.v1"],
    ).status.value)
    assert seen == {
        "directly_comparable",
        "comparable_after_transformation",
        "not_comparable",
        "not_identified",
        "unavailable",
    }


def test_all_registry_rules_present_and_exercised():
    assert len(RULES) == 12
    assert "forecast_vs_h1_target.v1" in RULES
    probes = {
        "forecast_vs_first_print.v1": lambda: compare_qualified(
            _obs(value=0.2, evidence_class="house_estimate", model_id="release_forecast:v2"),
            _obs(value=0.3),
            RULES["forecast_vs_first_print.v1"],
        ),
        "same_basis_level_change.v1": lambda: compare_qualified(
            _obs(), _obs(value=0.3, reference_start="2026-08-01", reference_end="2026-08-31"),
            RULES["same_basis_level_change.v1"],
        ),
        "zq_month_vs_policy_midpoint.v1": lambda: compare_qualified(
            _zq_obs(), _zq_obs(), RULES["zq_month_vs_policy_midpoint.v1"]
        ),
        "sr3_vs_zq.v1": lambda: compare_qualified(_zq_obs(), _zq_obs(), RULES["sr3_vs_zq.v1"]),
        "par_vs_zero.v1": lambda: compare_qualified(
            _obs(), _obs(value=0.3, curve_convention="zero"), RULES["par_vs_zero.v1"]
        ),
        "cpi_vs_pce.v1": lambda: compare_qualified(
            _obs(), _obs(value=0.3, basket_or_index="PCE", subject="PCEPI", target="pce_headline_mom_sa"),
            RULES["cpi_vs_pce.v1"],
        ),
        "cpi_month_vs_breakeven_10y.v1": lambda: compare_qualified(
            _obs(), _obs(value=2.25, subject="T10YIE", unit="pct_yoy", target="inflation_compensation",
                         basket_or_index=NA, tenor="10y", reference_start="2026-10-13",
                         reference_end="2036-10-15", source="fred:T10YIE"),
            RULES["cpi_month_vs_breakeven_10y.v1"],
        ),
        "yield_move_attribution.v1": lambda: compare_qualified(
            _obs(value=30.0, unit="bp", target="ust_par_yield_move"),
            _obs(value=20.0, unit="bp", target="term_premium_move_kw"),
            RULES["yield_move_attribution.v1"],
        ),
        "forecast_vs_h1_target.v1": lambda: compare_qualified(
            _obs(
                value=0.2,
                evidence_class="house_estimate",
                target="cpi_u_all_items_mom_sa_first_print",
                model_id="release_forecast:v2",
                target_epoch="2026-09-30",
            ),
            _obs(
                value=0.3,
                target="cpi_u_all_items_mom_sa_h1",
                content_ref="same_vintage:abcdef0123456789abcdef01",
                quality=("proxy_vintage",),
                target_epoch="2026-09-30",
            ),
            RULES["forecast_vs_h1_target.v1"],
            context={"eval_target_epoch": "2026-09-30"},
        ),
    }
    for rule_id, probe in probes.items():
        result = probe()
        assert result.rule_id == rule_id
        assert result.status.value in (
            "directly_comparable", "comparable_after_transformation",
            "not_comparable", "not_identified", "unavailable",
        )


def test_no_meeting_month_identified_conditional():
    obs = _zq_obs(value=4.25)
    result = solve_reference_average(
        (obs,),
        PathAssumptions("2026-09-01", "2026-09-30", effective_dates=("2026-10-21",)),
    )
    assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
    assert result.identified["end_rate"] == pytest.approx(4.25)
    assert "no_intra_month_change" in result.assumptions_used


def test_realised_average_over_elapsed_days_identifies_post_rate():
    obs = _zq_obs(value=4.25)
    result = solve_reference_average(
        (obs,),
        PathAssumptions(
            "2026-09-01",
            "2026-09-30",
            effective_dates=("2026-09-16",),
            realised_through="2026-09-15",
            realised_average=4.50,
            rate_step_bp=50.0,
        ),
    )
    assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
    assert result.identified["end_rate"] == pytest.approx(4.00)


def test_missing_inputs_without_average():
    result = solve_reference_average((), PathAssumptions("2026-09-01", "2026-09-30"))
    assert result.status is PathStatus.MISSING_INPUTS
    assert "monthly_average" in result.missing


def test_inconsistent_when_no_grid_path_fits():
    obs = _zq_obs(value=4.25)
    result = solve_reference_average(
        (obs,),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-03",),  # d_pre=2, d_post=28: no +-grid change path fits
            rate_step_bp=50.0,
        ),
    )
    assert result.status is PathStatus.INCONSISTENT
    assert result.alternatives == ()
    assert result.residual_bp is not None


def test_multi_segment_paths_fit_average():
    obs = _zq_obs(value=4.25)
    result = solve_reference_average(
        (obs,),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-11", "2026-09-21"),
            rate_step_bp=50.0,
        ),
    )
    assert result.status is PathStatus.FEASIBLE_ALTERNATIVES
    assert result.identified is None
    assert result.alternatives
    for path in result.alternatives:
        days = 0
        total = 0.0
        for seg in path["segments"]:
            days += 10  # each segment spans 10 calendar days (1-11, 11-21, 21-30 incl end)
            total += seg[2] * 10
        assert days == 30
        assert total / 30.0 == pytest.approx(4.25)


class TestB0CutoffLawRepair:
    """B0-FIX (A06): the cutoff law is time-zone exact and fail-closed.

    A number whose evidence time is after -- or cannot be shown to be at or
    before -- its publication cutoff is NEVER present, whatever time zone,
    precision or garbage encoding carries it.
    """

    META = dict(
        evidence_class="market_implied_expectation",
        unit="pct_ann_rate",
        subject="ZQX26",
        target="effr_monthly_average",
    )

    def _q(self, stamp, cutoff):
        return qualify_observation(
            4.25,
            dict(self.META, observation_time=stamp, first_public_evidence=stamp),
            cutoff,
        )

    def test_tz_offset_after_cutoff_refused(self):
        # 2026-10-13T23:00-05:00 == 2026-10-14T04:00Z: four hours AFTER cutoff
        refused = self._q("2026-10-13T23:00-05:00", "2026-10-14T00:00+00:00")
        assert refused.value_state == "refused"
        assert refused.value is None
        assert "after_cutoff" in refused.limitations
        # 2026-10-13T18:00-05:00 == 2026-10-13T23:00Z: one hour BEFORE cutoff
        early = self._q("2026-10-13T18:00-05:00", "2026-10-14T00:00+00:00")
        assert early.value_state == "present"
        assert early.value == pytest.approx(4.25)

    def test_second_precision_compared_exactly(self):
        late = self._q("2026-10-14T03:00:59Z", "2026-10-14T03:00:30Z")
        assert late.value_state == "refused"
        assert late.value is None
        assert "after_cutoff" in late.limitations
        early = self._q("2026-10-14T03:00:29Z", "2026-10-14T03:00:30Z")
        assert early.value_state == "present"
        assert early.value == pytest.approx(4.25)

    def test_cross_zone_day_compare_fail_closed(self):
        # cutoff instant 2026-10-13T22:00-05:00 == 2026-10-14T03:00Z; its
        # literal day key is 10-13, so a 10-14 day stamp cannot be shown at
        # or before it and must refuse
        refused = self._q("2026-10-14", "2026-10-13T22:00-05:00")
        assert refused.value_state == "refused"
        assert refused.value is None
        assert "after_cutoff" in refused.limitations

    def test_unparsable_cutoff_refuses_never_raises(self):
        refused = self._q("2026-10-14", "garbage")
        assert refused.value_state == "refused"
        assert refused.value is None
        assert "cutoff_unparsable" in refused.limitations
        with pytest.raises(ValueError):
            self._q("2026-10-14", "")
        with pytest.raises(ValueError):
            self._q("2026-10-14", None)

    def test_unparsable_evidence_refused(self):
        refused = self._q("14/10/2026", "2026-10-01")
        assert refused.value_state == "refused"
        assert refused.value is None
        assert "evidence_time_unparsable" in refused.limitations

    def test_none_evidence_time_stays_admitted(self):
        # freeze rule: unknown (None) evidence time stays admitted
        obs = qualify_observation(4.25, self.META, "2026-10-14T00:00+00:00")
        assert obs.value_state == "present"
        assert obs.value == pytest.approx(4.25)
        assert obs.observation_time is None
        assert obs.first_public_evidence is None

    def test_post_init_rejects_present_leak(self):
        present = _obs(value=0.2)
        assert QualifiedObservation.from_dict(present.to_dict()) == present
        tampered = dict(present.to_dict())
        tampered["observation_time"] = "2026-10-20T09:00"  # edited past cutoff
        with pytest.raises(ValueError):
            QualifiedObservation.from_dict(tampered)

    def test_from_dict_rejects_unknown_keys(self):
        good_obs = _obs(value=0.2)
        with pytest.raises(ValueError, match="bogus"):
            QualifiedObservation.from_dict(dict(good_obs.to_dict(), bogus=1))
        result = compare_qualified(
            _obs(value=0.2), _obs(value=0.3), RULES["same_basis_level_change.v1"]
        )
        with pytest.raises(ValueError, match="bogus"):
            ComparisonResult.from_dict(dict(result.to_dict(), bogus=1))
        paths = solve_reference_average(
            (_zq_obs(value=4.25),),
            PathAssumptions("2026-09-01", "2026-09-30", rate_step_bp=50.0),
        )
        with pytest.raises(ValueError, match="bogus"):
            PathIdentification.from_dict(dict(paths.to_dict(), bogus=1))

    def test_boundary_equality_admitted(self):
        assert (
            self._q("2026-10-14T00:00:00Z", "2026-10-14T00:00:00Z").value_state
            == "present"
        )
        assert self._q("2026-10-14", "2026-10-14").value_state == "present"
        assert self._q("2026-10", "2026-10").value_state == "present"


def test_cpi_vs_breakeven_refuses_even_when_reference_end_matches():
    cpi = _obs(value=0.2)  # reference_end 2026-09-30 from the CPI meta defaults
    forged = _obs(
        value=2.25,
        subject="T10YIE",
        unit="pct_yoy",
        target="inflation_compensation",
        basket_or_index=NA,
        tenor="10y",
        reference_start="2026-10-13",
        reference_end="2026-09-30",  # forged EQUAL to the CPI operand's
        source="fred:T10YIE",
    )
    result = compare_qualified(cpi, forged, RULES["cpi_month_vs_breakeven_10y.v1"])
    assert result.status == "not_comparable"
    assert result.reason == "basis_mismatch:reference_end"
    assert result.difference is None
    assert result.range is None
    honest = _obs(
        value=2.25,
        subject="T10YIE",
        unit="pct_yoy",
        target="inflation_compensation",
        basket_or_index=NA,
        tenor="10y",
        reference_start="2026-10-13",
        reference_end="2036-10-15",
        source="fred:T10YIE",
    )
    honest_result = compare_qualified(cpi, honest, RULES["cpi_month_vs_breakeven_10y.v1"])
    assert honest_result.status == "not_comparable"
    assert honest_result.reason == "basis_mismatch:reference_end"


def test_month_end_effective_date_is_inside_the_month():
    result = solve_reference_average(
        (_zq_obs(value=134 / 30),),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-30",), pre_change_rate=4.50,
        ),
    )
    assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
    assert abs(result.identified["end_rate"] - 3.50) < 1e-6
    assert "effective_date=2026-09-30" in result.assumptions_used
    assert "no_intra_month_change" not in result.assumptions_used
    assert result.identified["segments"][-1][0] == "2026-09-30"
    # control: a date outside the month keeps the non-meeting branch
    outside = solve_reference_average(
        (_zq_obs(value=4.25),),
        PathAssumptions("2026-09-01", "2026-09-30", effective_dates=("2026-10-01",)),
    )
    assert outside.status is PathStatus.IDENTIFIED_CONDITIONAL
    assert "no_intra_month_change" in outside.assumptions_used


def test_two_dates_last_on_month_end_cover_the_month():
    result = solve_reference_average(
        (_zq_obs(value=4.375),),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-15", "2026-09-30"),
            pre_change_rate=4.50, rate_step_bp=25,
        ),
    )
    assert result.status is PathStatus.FEASIBLE_ALTERNATIVES
    returned = list(result.alternatives) + (
        [result.identified] if result.identified else []
    )
    assert returned
    for path in returned:
        segments = path["segments"]
        lengths = [
            (date.fromisoformat(seg[1]) - date.fromisoformat(seg[0])).days
            + (1 if i == len(segments) - 1 else 0)
            for i, seg in enumerate(segments)
        ]
        assert sum(lengths) == 30  # 14 + 15 + the month-end day itself
        assert segments[-1][0] == "2026-09-30"
    assert abs(returned[0]["end_rate"] - 4.50) < 1e-9


def test_grid_step_recorded_in_assumptions():
    supplied = solve_reference_average(
        (_zq_obs(value=4.25),),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-15",), rate_step_bp=25,
        ),
    )
    assert "rate_step_bp=25" in supplied.assumptions_used
    assert "rate_step_defaulted" not in supplied.assumptions_used
    assert supplied.status.value == "inconsistent"  # status observed at lane base
    defaulted = solve_reference_average(
        (_zq_obs(value=4.25),),
        PathAssumptions("2026-09-01", "2026-09-30", effective_dates=("2026-09-15",)),
    )
    assert defaulted.status.value == "missing_inputs"
    assert defaulted.missing == ("pre_change_rate",)
    assert "rate_step_unsupplied" in defaulted.assumptions_used
    assert "rate_step_defaulted" not in defaulted.assumptions_used


def test_module_is_pure_ast():
    tree = ast.parse(MODULE_PATH.read_text(), filename=str(MODULE_PATH))
    allowed_roots = {
        "__future__", "dataclasses", "datetime", "enum", "hashlib", "json", "typing",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed_roots, alias.name
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed_roots, node.module
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in ("open", "eval", "exec", "__import__"), node.func.id
        elif isinstance(node, ast.Attribute):
            assert node.attr not in ("now", "utcnow", "today", "system", "popen"), node.attr


# ---------------------------------------------------------------------------
# B0-H1 forecast_vs_h1_target.v1 (R2-E1-S13)
# ---------------------------------------------------------------------------

GOLDEN_RESULTS_DIGEST = (
    "2aa5b7397307539821d95144d88812a8d740b37a98e9bb429b15bbf05a77e51d"
)
GOLDEN_RULES_DIGEST = (
    "79256fa9cbd66d7a267cd0b8141e9fcb241950b1a3c705958f2372f083a3f104"
)
GOLDEN_EXISTING_RULE_IDS = (
    "cpi_month_vs_breakeven_10y.v1",
    "cpi_vs_pce.v1",
    "forecast_vs_first_print.v1",
    "inflation_compensation.v1",
    "par_vs_zero.v1",
    "same_basis_level_change.v1",
    "sep_vs_market_year_end.v1",
    "sr3_vs_zq.v1",
    "term_premium_kw_vs_acm.v1",
    "yield_move_attribution.v1",
    "zq_month_vs_policy_midpoint.v1",
)


def _golden_existing_matrix():
    """Fixed matrix: every existing rule id x the operand pairs the registry
    probes exercise; ``forecast_vs_first_print.v1`` is run twice (no context
    and a synthetic eval_target_epoch context) so a future regression that
    silently reads context shows as a digest drift."""
    probes = {
        "forecast_vs_first_print.v1": (
            _obs(value=0.2, evidence_class="house_estimate", model_id="release_forecast:v2"),
            _obs(value=0.3),
        ),
        "same_basis_level_change.v1": (
            _obs(),
            _obs(value=0.3, reference_start="2026-08-01", reference_end="2026-08-31"),
        ),
        "zq_month_vs_policy_midpoint.v1": (_zq_obs(), _zq_obs()),
        "sr3_vs_zq.v1": (_zq_obs(), _zq_obs()),
        "par_vs_zero.v1": (
            _obs(),
            _obs(value=0.3, curve_convention="zero"),
        ),
        "cpi_vs_pce.v1": (
            _obs(),
            _obs(
                value=0.3,
                basket_or_index="PCE",
                subject="PCEPI",
                target="pce_headline_mom_sa",
            ),
        ),
        "cpi_month_vs_breakeven_10y.v1": (
            _obs(),
            _obs(
                value=2.25,
                subject="T10YIE",
                unit="pct_yoy",
                target="inflation_compensation",
                basket_or_index=NA,
                tenor="10y",
                reference_start="2026-10-13",
                reference_end="2036-10-15",
                source="fred:T10YIE",
            ),
        ),
        "yield_move_attribution.v1": (
            _obs(value=30.0, unit="bp", target="ust_par_yield_move"),
            _obs(value=20.0, unit="bp", target="term_premium_move_kw"),
        ),
        "sep_vs_market_year_end.v1": (
            _obs(
                evidence_class="survey_participant_projection",
                target="sep_year_end_median",
                value=4.5,
                unit="pct_ann_rate",
                reference_start="2026-01-01",
                reference_end="2026-12-31",
            ),
            _obs(
                evidence_class="market_implied_expectation",
                target="fed_funds_futures_year_end",
                value=4.6,
                unit="pct_ann_rate",
                reference_start="2026-12-01",
                reference_end="2026-12-31",
            ),
        ),
        "inflation_compensation.v1": (
            _obs(
                curve_convention="par",
                value=4.5,
                unit="pct_ann_rate",
                target="par_nominal",
                tenor="10y",
                reference_start="2026-10-13",
                reference_end="2036-10-15",
            ),
            _obs(
                curve_convention="real_par",
                value=2.0,
                unit="pct_ann_rate",
                target="real_nominal",
                tenor="10y",
                reference_start="2026-10-13",
                reference_end="2036-10-15",
            ),
        ),
        "term_premium_kw_vs_acm.v1": (
            _obs(
                model_id="kw_main_v3",
                target="term_premium_kw",
                value=0.5,
                unit="pct_ann_rate",
                tenor="10y",
                reference_start="2026-10-13",
                reference_end="2036-10-15",
            ),
            _obs(
                model_id="acm_main_v2",
                target="term_premium_acm",
                value=0.6,
                unit="pct_ann_rate",
                tenor="10y",
                reference_start="2026-10-13",
                reference_end="2036-10-15",
            ),
        ),
    }
    results = []
    for rule_id in sorted(probes):
        rule = RULES[rule_id]
        left, right = probes[rule_id]
        results.append(compare_qualified(left, right, rule, context=None))
    fpv = compare_qualified(
        probes["forecast_vs_first_print.v1"][0],
        probes["forecast_vs_first_print.v1"][1],
        RULES["forecast_vs_first_print.v1"],
        context={"eval_target_epoch": "h1_2026_10"},
    )
    return results, fpv


def _golden_results_digest():
    import hashlib
    results, fpv = _golden_existing_matrix()
    payload = [r.to_dict() for r in results] + [fpv.to_dict()]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _golden_rules_digest():
    import hashlib
    payload = [dataclasses.asdict(RULES[k]) for k in GOLDEN_EXISTING_RULE_IDS]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_existing_kinds_byte_identical_golden():
    assert _golden_results_digest() == GOLDEN_RESULTS_DIGEST, (
        "existing-kinds results digest drifted; the H1 lane must not change "
        "any existing rule's output by a single byte"
    )
    assert _golden_rules_digest() == GOLDEN_RULES_DIGEST, (
        "existing 11 RULES registrations drifted; the H1 lane must not "
        "rewrite any existing rule's fields or order"
    )


H1_RULE_ID = "forecast_vs_h1_target.v1"


def _h1_left(value=0.2, **over):
    over.setdefault("evidence_class", "house_estimate")
    over.setdefault("target", "cpi_u_all_items_mom_sa_first_print")
    over.setdefault("model_id", "release_forecast:v2")
    over.setdefault("target_epoch", "2026-09-30")
    return _obs(value=value, **over)


def _h1_right(value=0.3, **over):
    over.setdefault("evidence_class", "official_measurement")
    over.setdefault("target", "cpi_u_all_items_mom_sa_h1")
    over.setdefault("content_ref", "same_vintage:abcdef0123456789abcdef01")
    over.setdefault("target_epoch", "2026-09-30")
    return _obs(value=value, **over)


def test_h1_direct_difference_pct_to_bp():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _h1_left(value=0.20),
        _h1_right(value=0.30),
        rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert result.status.value == "directly_comparable"
    assert result.difference == pytest.approx(-10.0)
    assert result.unit == "bp"
    assert "eval_target_epoch:2026-09-30" in result.assumptions
    assert "model_target_epoch:2026-09-30" in result.assumptions
    assert "h1_target_not_official_first_print" in result.limitations


def test_h1_direct_difference_native_unit_not_bp_labelled():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _obs(
            value=130.0,
            evidence_class="house_estimate",
            target="nfp_total_nonfarm_first_print",
            unit="thousands_persons",
            basket_or_index="NFP",
            target_epoch="2026-09-30",
            model_id="release_forecast:nfp:v3",
            seasonal_treatment="sa",
        ),
        _obs(
            value=180.0,
            evidence_class="official_measurement",
            target="nfp_total_nonfarm_h1",
            unit="thousands_persons",
            basket_or_index="NFP",
            target_epoch="2026-09-30",
            content_ref="same_vintage:bcdef0123456789abcdef012",
            seasonal_treatment="sa",
        ),
        rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert result.status.value == "directly_comparable"
    assert result.difference == pytest.approx(-50.0)
    assert result.unit == "thousands_persons"


def test_h1_missing_context_unknown_basis():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(_h1_left(), _h1_right(), rule, context=None)
    assert result.status.value == "not_comparable"
    assert result.reason == "unknown_basis:eval_target_epoch"


def test_h1_mismatched_eval_epoch_basis_mismatch():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _h1_left(),
        _h1_right(),
        rule,
        context={"eval_target_epoch": "2026-08-31"},
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "basis_mismatch:eval_target_epoch"


def test_h1_right_target_epoch_na_unknown_basis():
    rule = RULES[H1_RULE_ID]
    right = _h1_right()
    right = dataclasses.replace(right, target_epoch=NA)
    result = compare_qualified(_h1_left(), right, rule, context={"eval_target_epoch": "2026-09-30"})
    assert result.status.value == "not_comparable"
    assert result.reason == "unknown_basis:eval_target_epoch"


def test_h1_stem_bridge_refuses_cpi_forecast_vs_nfp_receipt():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _h1_left(value=0.2),
        _obs(
            value=130.0,
            evidence_class="official_measurement",
            target="nfp_total_nonfarm_h1",
            unit="thousands_persons",
            basket_or_index="NFP",
            target_epoch="2026-09-30",
            content_ref="same_vintage:bcdef0123456789abcdef012",
            seasonal_treatment="sa",
        ),
        rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "basis_mismatch:target_stem"


def test_h1_right_without_same_vintage_receipt_refused():
    rule = RULES[H1_RULE_ID]
    right = _obs(
        value=0.30,
        evidence_class="official_measurement",
        target="cpi_u_all_items_mom_sa_h1",
        content_ref="some_other_receipt:abc",
        target_epoch="2026-09-30",
    )
    result = compare_qualified(_h1_left(), right, rule, context={"eval_target_epoch": "2026-09-30"})
    assert result.status.value == "not_comparable"
    assert "constraint:content_ref:right" == result.reason


def test_h1_rule_refuses_first_print_right_side():
    rule = RULES[H1_RULE_ID]
    right = _obs(
        value=0.30,
        evidence_class="official_measurement",
        target="cpi_u_all_items_mom_sa_first_print",
        content_ref="same_vintage:abcdef0123456789abcdef01",
        target_epoch="2026-09-30",
    )
    result = compare_qualified(_h1_left(), right, rule, context={"eval_target_epoch": "2026-09-30"})
    assert result.status.value == "not_comparable"
    assert "constraint:target:right" == result.reason


def test_first_print_refuses_h1_right_side():
    fp_rule = RULES["forecast_vs_first_print.v1"]
    result = compare_qualified(
        _obs(value=0.2, evidence_class="house_estimate", model_id="release_forecast:v2"),
        _h1_right(),
        fp_rule,
    )
    assert result.status.value == "not_comparable"
    assert "constraint:target:right" == result.reason


def test_first_print_ignores_eval_target_epoch_context():
    fp_rule = RULES["forecast_vs_first_print.v1"]
    left = _obs(value=0.2, evidence_class="house_estimate", model_id="release_forecast:v2")
    right = _obs(value=0.3)
    without = compare_qualified(left, right, fp_rule, context=None)
    with_ctx = compare_qualified(
        left, right, fp_rule, context={"eval_target_epoch": "h1_2026_10"},
    )
    assert without.to_dict() == with_ctx.to_dict()


def test_h1_export_with_unknown_rights_blocked():
    rule = dataclasses.replace(RULES[H1_RULE_ID], purpose="export")
    left = _h1_left(rights="unknown")
    right = _h1_right(rights="unknown")
    result = compare_qualified(
        left, right, rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "rights_unknown"


def test_h1_proxy_vintage_limitation_present():
    rule = RULES[H1_RULE_ID]
    right_with_proxy = _obs(
        value=0.30,
        evidence_class="official_measurement",
        target="cpi_u_all_items_mom_sa_h1",
        content_ref="same_vintage:abcdef0123456789abcdef01",
        target_epoch="2026-09-30",
        quality=("proxy_vintage",),
    )
    result = compare_qualified(
        _h1_left(),
        right_with_proxy,
        rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert "proxy_vintage:right" in result.limitations
    assert "h1_target_not_official_first_print" in result.limitations


def test_h1_left_target_epoch_never_compared():
    rule = RULES[H1_RULE_ID]
    left_a = dataclasses.replace(_h1_left(), target_epoch="2026-09-30")
    left_b = dataclasses.replace(_h1_left(), target_epoch="2099-12-31")
    right = _h1_right()
    result_a = compare_qualified(
        left_a, right, rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    result_b = compare_qualified(
        left_b, right, rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert result_a.status.value == "directly_comparable"
    assert result_b.status.value == "directly_comparable"
    assert result_a.difference == pytest.approx(result_b.difference)
    assert result_a.reason == result_b.reason


def test_h1_basket_mismatch_cpi_vs_pce():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _h1_left(value=0.20),
        _obs(
            value=0.15,
            evidence_class="official_measurement",
            target="cpi_u_all_items_mom_sa_h1",
            basket_or_index="PCE",
            unit="pct_mom",
            seasonal_treatment="sa",
            content_ref="same_vintage:pce01234567890123456789",
            target_epoch="2026-09-30",
        ),
        rule,
        context={"eval_target_epoch": "2026-09-30"},
    )
    assert result.status.value == "not_comparable"
    assert "basis_mismatch:basket_or_index" == result.reason


@pytest.mark.parametrize(
    "field,left_value,right_value",
    [
        ("unit", "pct_mom", "pct_yoy"),
        ("seasonal_treatment", "sa", "nsa"),
        ("reference_start", "2026-09-01", "2026-08-01"),
        ("reference_end", "2026-09-30", "2026-08-31"),
    ],
)
def test_h1_match_field_mismatch_refused(field, left_value, right_value):
    rule = RULES[H1_RULE_ID]
    left = _h1_left(**{field: left_value})
    right = _h1_right(**{field: right_value})
    result = compare_qualified(
        left, right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "basis_mismatch:%s" % field
    assert result.difference is None


@pytest.mark.parametrize(
    "field",
    [
        "basket_or_index",
        "reference_start",
        "reference_end",
        "unit",
        "seasonal_treatment",
        "curve_convention",
        "rate_index",
        "averaging_law",
        "tenor",
    ],
)
def test_h1_none_match_field_unknown_basis(field):
    rule = RULES[H1_RULE_ID]
    base = _h1_right()
    try:
        right = dataclasses.replace(base, **{field: None})
    except (ValueError, TypeError) as exc:
        pytest.skip("none_unreachable_at_construction:%s:%s" % (field, type(exc).__name__))
    result = compare_qualified(
        _h1_left(), right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "unknown_basis:%s" % field
    assert result.difference is None


@pytest.mark.parametrize(
    "over,expected",
    [
        ({"evidence_class": "official_measurement"}, "constraint:evidence_class:left"),
        ({"evidence_class": "house_estimate"}, "constraint:evidence_class:right"),
        ({"target": "cpi_u_all_items_mom_sa_h1"}, "constraint:target:left"),
    ],
)
def test_h1_constraint_refusals(over, expected):
    rule = RULES[H1_RULE_ID]
    side = "left" if expected.endswith(":left") else "right"
    if side == "left":
        left = _h1_left(**over)
        right = _h1_right()
    else:
        left = _h1_left()
        right = _h1_right(**over)
    result = compare_qualified(
        left, right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == expected
    assert result.difference is None


@pytest.mark.parametrize("bad_epoch", [None, "", " ", "NA", "na", NA])
def test_h1_left_epoch_absent_unknown_basis(bad_epoch):
    rule = RULES[H1_RULE_ID]
    left = _h1_left(target_epoch=bad_epoch)
    result = compare_qualified(
        left, _h1_right(), rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "unknown_basis:model_target_epoch"
    assert result.difference is None


def test_h1_assumptions_never_contain_none():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _h1_left(), _h1_right(), rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "directly_comparable"
    for assumption in result.assumptions:
        assert "None" not in assumption, "assumption leaked the repr None: %r" % assumption


def test_h1_curve_convention_par_vs_zero_refused():
    rule = RULES[H1_RULE_ID]
    left = _h1_left(curve_convention="par")
    right = _h1_right(curve_convention="zero")
    result = compare_qualified(
        left, right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "basis_mismatch:curve_convention"
    assert result.difference is None


def test_h1_effr_arithmetic_vs_sofr_compounded_refused():
    rule = RULES[H1_RULE_ID]
    left = _h1_left(rate_index="EFFR", averaging_law="arithmetic_calendar_day")
    right = _h1_right(rate_index="SOFR", averaging_law="compounded_business_day")
    result = compare_qualified(
        left, right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "basis_mismatch:rate_index"
    assert result.difference is None


def test_h1_na_on_both_sides_matches():
    rule = RULES[H1_RULE_ID]
    left = _h1_left(
        curve_convention=NA,
        rate_index=NA,
        averaging_law=NA,
        tenor=NA,
    )
    right = _h1_right(
        curve_convention=NA,
        rate_index=NA,
        averaging_law=NA,
        tenor=NA,
    )
    result = compare_qualified(
        left, right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "directly_comparable"
    assert result.difference == pytest.approx(-10.0)


def test_h1_empty_stem_refused():
    rule = RULES[H1_RULE_ID]
    left = _h1_left(target="_first_print")
    right = _h1_right(target="_h1")
    result = compare_qualified(
        left, right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "basis_mismatch:target_stem"
    assert result.difference is None


@pytest.mark.parametrize(
    "blank_ref", ["same_vintage:", "same_vintage:   ", "same_vintage:\t\n "]
)
def test_h1_same_vintage_empty_suffix_refused(blank_ref):
    rule = RULES[H1_RULE_ID]
    right = _h1_right(content_ref=blank_ref)
    result = compare_qualified(
        _h1_left(), right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "unknown_basis:content_ref"
    assert result.difference is None


@pytest.mark.parametrize(
    "eval_epoch,expected_status,expected_reason",
    [
        (" 2026-09-30 ", "directly_comparable", None),
        ("2026-09-30\t", "directly_comparable", None),
        ("   ", "not_comparable", "unknown_basis:eval_target_epoch"),
    ],
)
def test_h1_epochs_whitespace_stripped(eval_epoch, expected_status, expected_reason):
    rule = RULES[H1_RULE_ID]
    right = _h1_right(target_epoch="2026-09-30\t")
    result = compare_qualified(
        _h1_left(), right, rule, context={"eval_target_epoch": eval_epoch}
    )
    assert result.status.value == expected_status
    if expected_reason is not None:
        assert result.reason == expected_reason
    else:
        assert "eval_target_epoch:2026-09-30" in result.assumptions


def test_h1_eval_epoch_empty_string_unknown_basis():
    rule = RULES[H1_RULE_ID]
    result = compare_qualified(
        _h1_left(), _h1_right(), rule, context={"eval_target_epoch": ""}
    )
    assert result.status.value == "not_comparable"
    assert result.reason == "unknown_basis:eval_target_epoch"
    assert result.difference is None


def test_h1_no_proxy_limitation_when_right_not_proxy():
    rule = RULES[H1_RULE_ID]
    right = _h1_right()
    assert "proxy_vintage" not in right.quality
    result = compare_qualified(
        _h1_left(), right, rule, context={"eval_target_epoch": "2026-09-30"}
    )
    assert result.status.value == "directly_comparable"
    assert "proxy_vintage:right" not in result.limitations


def test_eval_target_epoch_confined_to_h1_hook_ast():
    """Every literal string ``eval_target_epoch`` in the module AST must lie
    inside ``_compute_h1_target``; the lane forbids the keyword leaking into
    other rules or hooks."""
    import ast as _ast
    tree = _ast.parse(MODULE_PATH.read_text(), filename=str(MODULE_PATH))
    h1_func_nodes = []
    needle = "eval_target_epoch"
    for node in _ast.walk(tree):
        if isinstance(node, _ast.FunctionDef) and node.name == "_compute_h1_target":
            h1_func_nodes.append(node)
    assert h1_func_nodes, "_compute_h1_target function is missing from module"
    allowed_lineno_ranges = [
        (n.lineno, n.end_lineno if hasattr(n, "end_lineno") and n.end_lineno else n.lineno)
        for n in h1_func_nodes
    ]

    def _in_h1(lineno):
        for start, end in allowed_lineno_ranges:
            if start <= lineno <= end:
                return True
        return False

    for node in _ast.walk(tree):
        if (
            isinstance(node, _ast.Constant)
            and isinstance(node.value, str)
            and needle in node.value
        ):
            assert _in_h1(node.lineno), (
                "literal %r appears outside _compute_h1_target at line %d"
                % (needle, node.lineno)
            )


def _realised_assumptions(**over):
    base = dict(
        month_start="2026-09-01",
        month_end="2026-09-30",
        effective_dates=("2026-09-16",),
        rate_step_bp=50.0,
    )
    base.update(over)
    return PathAssumptions(**base)


def test_realised_pre_rate_counts_days_up_to_the_effective_date():
    # R1/R2/R3: a realised average over any pre-change prefix IS the pre rate
    # on the whole pre segment [month_start, eff). ZQ 4.375 is the
    # truth-weighted average of 15d @ 4.50 + 15d @ 4.25, so the identified
    # end rate must be 4.25 whatever prefix the realised window covers.
    for through, tag in (
        (None, None),
        ("2026-09-15", "2026-09-15"),
        ("2026-09-10", "2026-09-10"),
    ):
        result = solve_reference_average(
            (_zq_obs(4.375),),
            _realised_assumptions(realised_through=through, realised_average=4.50),
        )
        assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
        assert abs(result.identified["end_rate"] - 4.25) < 1e-9
        assert "pre_change_rate_source=realised_average" in result.assumptions_used
        if tag is None:
            assert not any(
                a.startswith("realised_through=") for a in result.assumptions_used
            )
        else:
            assert "realised_through=%s" % tag in result.assumptions_used


def test_realised_pre_rate_with_month_end_effective_date():
    # R4: an effective date on the month end still leaves a one-day post
    # segment; the old d_post <= 0 fallback returned the average itself.
    obs_value = (4.50 * 29 + 3.50) / 30
    result = solve_reference_average(
        (_zq_obs(obs_value),),
        _realised_assumptions(effective_dates=("2026-09-30",), realised_average=4.50),
    )
    assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
    assert abs(result.identified["end_rate"] - 3.50) < 1e-9
    assert result.identified["segments"][-1][0] == "2026-09-30"
    assert "no_intra_month_change" not in result.assumptions_used


def test_realised_window_reaching_the_effective_date_is_not_a_pre_rate():
    # A realised window that reaches or passes the effective date carries no
    # pre-change information: the input falls back to the unknown-pre-rate
    # grid and is tagged unusable.
    fields = [
        f for f in PathIdentification.__dataclass_fields__ if f != "assumptions_used"
    ]
    without = solve_reference_average((_zq_obs(4.375),), _realised_assumptions())
    for through in ("2026-09-16", "2026-09-20"):
        with_realised = solve_reference_average(
            (_zq_obs(4.375),),
            _realised_assumptions(realised_through=through, realised_average=4.50),
        )
        for field in fields:
            assert getattr(with_realised, field) == getattr(without, field), field
        assert "realised_average_unusable_as_pre_rate" in with_realised.assumptions_used


def test_partial_realised_average_is_not_a_monthly_average():
    # F7a/F7b: a realised average over part of the month is not the month's
    # average -- with no present observation the result is missing_inputs,
    # never an identified path (and never an identified "no change").
    cases = (
        _realised_assumptions(realised_through="2026-09-15", realised_average=4.50),
        _realised_assumptions(
            effective_dates=("2026-10-28",),
            realised_through="2026-09-15",
            realised_average=4.50,
        ),
        _realised_assumptions(realised_through=None, realised_average=4.50),
    )
    for assumptions in cases:
        result = solve_reference_average((), assumptions)
        assert result.status is PathStatus.MISSING_INPUTS
        assert result.missing == ("monthly_average",)
        assert result.identified is None


def test_full_month_realised_average_stands_in_for_the_monthly_average():
    # Only full-month coverage lets the realised average stand in for the
    # monthly average, and the stand-in is recorded in the assumptions.
    result = solve_reference_average(
        (),
        _realised_assumptions(
            effective_dates=("2026-10-28",),
            realised_through="2026-09-30",
            realised_average=4.50,
        ),
    )
    assert result.status is PathStatus.IDENTIFIED_CONDITIONAL
    assert result.identified["end_rate"] == pytest.approx(4.50)
    assert "monthly_average_source=realised_average" in result.assumptions_used
    assert "no_intra_month_change" in result.assumptions_used


def test_single_date_unknown_pre_rate_without_step_is_missing_inputs():
    # F3: with no pre-change rate and no supplied step the solver returns
    # missing_inputs; it may never mint a path from a default 50 bp grid.
    result = solve_reference_average(
        (_zq_obs(4.25),),
        PathAssumptions("2026-09-01", "2026-09-30", effective_dates=("2026-09-15",)),
    )
    assert result.status.value == "missing_inputs"
    assert result.missing == ("pre_change_rate",)
    assert result.identified is None
    assert result.alternatives == ()
    assert result.end_rate_range is None
    assert "rate_step_unsupplied" in result.assumptions_used
    assert not any(t.startswith("rate_step_bp=") for t in result.assumptions_used)
    # a realised average unusable as the pre rate is no better
    unusable = solve_reference_average(
        (_zq_obs(4.25),),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-15",),
            realised_average=4.50, realised_through="2026-09-20",
        ),
    )
    assert unusable.status.value == "missing_inputs"
    assert unusable.missing == ("pre_change_rate",)
    assert "realised_average_unusable_as_pre_rate" in unusable.assumptions_used
    # control: with the step supplied the grid still enumerates
    supplied = solve_reference_average(
        (_zq_obs(4.25),),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-15",), rate_step_bp=25,
        ),
    )
    assert supplied.status.value != "missing_inputs"
    assert "rate_step_bp=25" in supplied.assumptions_used


def test_grid_without_step_never_mints_paths():
    # F3: every grid branch without a usable step is missing_inputs and
    # never enumerates candidate end rates.
    cases = []
    no_dates = solve_reference_average(
        (_zq_obs(4.25),), PathAssumptions("2026-09-01", "2026-09-30"),
    )
    assert no_dates.status.value == "missing_inputs"
    assert no_dates.missing == ("rate_step_bp",)
    cases.append(no_dates)
    two_dates = solve_reference_average(
        (_zq_obs(4.25),),
        PathAssumptions(
            "2026-09-01", "2026-09-30",
            effective_dates=("2026-09-11", "2026-09-21"),
        ),
    )
    assert two_dates.status.value == "missing_inputs"
    assert two_dates.missing == ("rate_step_bp",)
    cases.append(two_dates)
    for bad_step in (0, -25, float("nan")):
        invalid = solve_reference_average(
            (_zq_obs(4.25),),
            PathAssumptions(
                "2026-09-01", "2026-09-30",
                effective_dates=("2026-09-15",), rate_step_bp=bad_step,
            ),
        )
        assert invalid.status.value == "missing_inputs"
        assert invalid.missing == ("pre_change_rate",)
        cases.append(invalid)
    for case in cases:
        assert case.alternatives == ()
        assert "rate_step_defaulted" not in case.assumptions_used
    # control: the canonical witness input with an explicit step still
    # enumerates feasible alternatives
    canonical = solve_reference_average(
        (_zq_obs(4.25),),
        PathAssumptions("2026-09-01", "2026-09-30", rate_step_bp=50.0),
    )
    assert canonical.status.value == "feasible_alternatives"


def test_unknown_evidence_time_is_a_visible_limitation():
    # FQ2: an unknown evidence time stays admitted but is always carried as
    # a visible limitation; a refused record gets neither tag.
    meta = dict(
        evidence_class="market_implied_expectation",
        unit="pct_ann_rate",
        subject="ZQX26",
        target="effr_monthly_average",
    )
    cutoff = "2026-10-14T00:00+00:00"
    unstamped = qualify_observation(4.25, meta, cutoff)
    assert unstamped.value_state == "present"
    assert unstamped.value == pytest.approx(4.25)
    assert "evidence_time_unknown" in unstamped.limitations
    only_observation = qualify_observation(
        4.25, dict(meta, observation_time="2026-10-01T08:30"), cutoff
    )
    assert "first_public_evidence_unknown" in only_observation.limitations
    assert "evidence_time_unknown" not in only_observation.limitations
    stamp = "2026-10-01T08:30"
    stamped = qualify_observation(
        4.25,
        dict(meta, observation_time=stamp, first_public_evidence=stamp),
        cutoff,
    )
    assert "evidence_time_unknown" not in stamped.limitations
    assert "first_public_evidence_unknown" not in stamped.limitations
    late = "2026-10-20T09:00"
    refused = qualify_observation(
        4.25,
        dict(meta, observation_time=late, first_public_evidence=late),
        cutoff,
    )
    assert refused.value_state == "refused"
    assert "after_cutoff" in refused.limitations
    assert "evidence_time_unknown" not in refused.limitations
    assert "first_public_evidence_unknown" not in refused.limitations


def test_realised_pre_rate_with_unknown_window_is_tagged():
    # V1: a realised average used as the pre-change rate with no known
    # window is tagged; a dated window is recorded as before.
    zq = (4.50 * 15 + 4.00 * 15) / 30
    unknown = solve_reference_average(
        (_zq_obs(zq),),
        _realised_assumptions(realised_average=4.50, realised_through=None),
    )
    assert unknown.status.value == "identified_conditional"
    assert "realised_through_unknown" in unknown.assumptions_used
    known = solve_reference_average(
        (_zq_obs(zq),),
        _realised_assumptions(realised_average=4.50, realised_through="2026-09-15"),
    )
    assert "realised_through_unknown" not in known.assumptions_used


def test_string_limitation_is_one_entry():
    # N1: a metadata limitations string is one entry, not split characters.
    obs = qualify_observation(
        4.25,
        dict(
            evidence_class="market_implied_expectation",
            unit="pct_ann_rate",
            subject="ZQX26",
            target="effr_monthly_average",
            observation_time="2026-10-01T08:30",
            first_public_evidence="2026-10-01T08:30",
            limitations="extra note",
        ),
        "2026-10-14T00:00",
    )
    assert obs.limitations == ("extra note",)


def test_list_limitations_with_unknown_evidence_time_is_tagged():
    # A list-valued limitations sequence is coerced to a tuple before the
    # FQ2 tag append, so a list input can never crash the qualification.
    meta = dict(
        evidence_class="market_implied_expectation",
        unit="pct_ann_rate",
        subject="ZQX26",
        target="effr_monthly_average",
        limitations=["a", "b"],
    )
    cutoff = "2026-10-14T00:00+00:00"
    unstamped = qualify_observation(4.25, meta, cutoff)
    assert unstamped.value_state == "present"
    assert unstamped.limitations == ("a", "b", "evidence_time_unknown")
    only_observation = qualify_observation(
        4.25, dict(meta, observation_time="2026-10-01T08:30"), cutoff
    )
    assert only_observation.limitations == ("a", "b", "first_public_evidence_unknown")


def test_unknown_evidence_time_tag_survives_to_dict():
    # The FQ2 tag must reach every consumer payload (T0 board rows, C0
    # to_dict call), not only the dataclass; a round trip keeps the tag.
    meta = dict(
        evidence_class="market_implied_expectation",
        unit="pct_ann_rate",
        subject="ZQX26",
        target="effr_monthly_average",
    )
    unstamped = qualify_observation(4.25, meta, "2026-10-14T00:00+00:00")
    payload = unstamped.to_dict()
    assert "evidence_time_unknown" in payload["limitations"]
    assert "evidence_time_unknown" in QualifiedObservation.from_dict(payload).limitations
