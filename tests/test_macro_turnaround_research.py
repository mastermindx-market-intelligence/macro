from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from engine.macro_turnaround import (
    AuthorityBoundary,
    DataQuality,
    IndicatorSpec,
    MacroTurnaroundEngine,
    Observation,
    Phase,
    Transform,
    TurnaroundConfig,
    build_research_artifact,
)


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "build_macro_turnaround_research.py"


def monthly(values: list[float], *, delay_days: int = 10) -> list[Observation]:
    out: list[Observation] = []
    year, month = 2019, 1
    for value in values:
        period = date(year, month, 1)
        out.append(
            Observation(
                period=period,
                value=float(value),
                available_at=period + timedelta(days=delay_days),
            )
        )
        month += 1
        if month == 13:
            year += 1
            month = 1
    return out


def recovery_panel() -> tuple[dict[str, list[Observation]], list[IndicatorSpec], date]:
    base = [112.0 - 0.9 * i for i in range(30)] + [85.0 + 1.8 * i for i in range(14)]
    observations = {
        "new_orders": monthly(base),
        "weekly_hours": monthly([v * 0.73 for v in base]),
        "initial_claims": monthly([245.0 - v for v in base], delay_days=6),
        "credit_spread": monthly([180.0 - 0.4 * v for v in base], delay_days=2),
    }
    specs = [
        IndicatorSpec("new_orders", "activity", minimum_history=18),
        IndicatorSpec("weekly_hours", "labor", minimum_history=18),
        IndicatorSpec(
            "initial_claims",
            "labor",
            positive_when_rising=False,
            minimum_history=18,
        ),
        IndicatorSpec(
            "credit_spread",
            "credit",
            positive_when_rising=False,
            minimum_history=18,
        ),
    ]
    as_of = max(series[-1].available_at for series in observations.values())
    return observations, specs, as_of


def test_future_release_and_revision_cannot_change_historical_signal() -> None:
    observations, specs, _ = recovery_panel()
    cutoff = observations["new_orders"][-4].available_at
    engine = MacroTurnaroundEngine()
    baseline = engine.assess(observations, specs, cutoff)

    revised = {key: list(series) for key, series in observations.items()}
    last = revised["new_orders"][-1]
    revised["new_orders"][-1] = Observation(
        period=last.period,
        value=100_000.0,
        available_at=cutoff + timedelta(days=30),
    )
    guarded = engine.assess(revised, specs, cutoff)

    assert guarded.phase == baseline.phase
    assert guarded.upturn_score == pytest.approx(baseline.upturn_score)
    assert guarded.downturn_score == pytest.approx(baseline.downturn_score)
    assert guarded.input_hash == baseline.input_hash


def test_latest_available_revision_wins_without_overwriting_prior_vintage() -> None:
    values = [100.0 + math.sin(i / 3) for i in range(36)]
    series = monthly(values)
    original_cutoff = series[-1].available_at
    revised_release = original_cutoff + timedelta(days=20)
    revision = Observation(
        period=series[-1].period,
        value=series[-1].value + 20.0,
        available_at=revised_release,
    )
    engine = MacroTurnaroundEngine()
    spec = [IndicatorSpec("orders", "activity", minimum_history=18)]

    original = engine.assess({"orders": series + [revision]}, spec, original_cutoff)
    corrected = engine.assess({"orders": series + [revision]}, spec, revised_release)

    assert original.input_hash != corrected.input_hash
    assert original.as_of == original_cutoff
    assert corrected.as_of == revised_release


def test_recovery_evidence_is_broad_and_phase_is_recovery_side() -> None:
    observations, specs, as_of = recovery_panel()
    result = MacroTurnaroundEngine(
        TurnaroundConfig(enter_score=0.58, hold_score=0.51)
    ).assess(observations, specs, as_of)

    assert result.upturn_score > result.downturn_score
    assert result.breadth_improving > 0.50
    assert result.phase in {
        Phase.TROUGHING,
        Phase.EARLY_RECOVERY,
        Phase.EXPANSION,
    }
    assert result.confidence > 0.0
    assert result.drivers


def test_inverse_indicator_direction_changes_economic_signal() -> None:
    values = [100.0 + 0.1 * i for i in range(30)] + [103.0 + 2.0 * i for i in range(12)]
    series = monthly(values)
    as_of = series[-1].available_at
    engine = MacroTurnaroundEngine()
    adverse = engine.assess(
        {"claims": series},
        [
            IndicatorSpec(
                "claims",
                "labor",
                positive_when_rising=False,
                minimum_history=18,
            )
        ],
        as_of,
    )
    wrongly_positive = engine.assess(
        {"claims": series},
        [IndicatorSpec("claims", "labor", minimum_history=18)],
        as_of,
    )
    assert adverse.composite_slope < wrongly_positive.composite_slope
    assert adverse.upturn_score < wrongly_positive.upturn_score


def test_family_cap_prevents_correlated_duplicate_domination() -> None:
    engine = MacroTurnaroundEngine(TurnaroundConfig(family_weight_cap=0.35))
    base = [110.0 - 0.5 * i for i in range(28)] + [96.0 + 1.3 * i for i in range(14)]
    observations: dict[str, list[Observation]] = {}
    specs: list[IndicatorSpec] = []
    for index in range(10):
        key = f"labor_variant_{index}"
        observations[key] = monthly([v + index * 0.01 for v in base])
        specs.append(IndicatorSpec(key, "labor", minimum_history=18))
    observations["activity"] = monthly(base)
    observations["credit"] = monthly([200.0 - v for v in base])
    specs.extend(
        [
            IndicatorSpec("activity", "activity", minimum_history=18),
            IndicatorSpec(
                "credit",
                "credit",
                positive_when_rising=False,
                minimum_history=18,
            ),
        ]
    )
    as_of = observations["activity"][-1].available_at
    result = engine.assess(observations, specs, as_of)
    family_weights: dict[str, float] = {}
    for signal in result.signals:
        family_weights[signal.family] = family_weights.get(signal.family, 0.0) + signal.effective_weight
    assert sum(family_weights.values()) == pytest.approx(1.0)
    assert max(family_weights.values()) <= 0.35 + 1e-12


def test_stale_and_missing_inputs_reduce_quality_without_false_completion() -> None:
    observations, specs, as_of = recovery_panel()
    full = MacroTurnaroundEngine().assess(observations, specs, as_of)
    partial = MacroTurnaroundEngine().assess(
        {"new_orders": observations["new_orders"]},
        specs,
        as_of,
    )
    stale_as_of = as_of + timedelta(days=500)
    stale = MacroTurnaroundEngine().assess(observations, specs, stale_as_of)

    assert partial.quality.coverage < full.quality.coverage
    assert partial.confidence < full.confidence
    assert "partial_coverage" in partial.quality.flags
    assert stale.phase is Phase.INDETERMINATE
    assert stale.confidence == 0.0
    assert set(stale.quality.excluded) == {spec.key for spec in specs}


def test_hysteresis_rejects_one_print_opposite_phase_flip() -> None:
    observations, specs, as_of = recovery_panel()
    engine = MacroTurnaroundEngine(
        TurnaroundConfig(enter_score=0.62, hold_score=0.54)
    )
    recovering = engine.assess(observations, specs, as_of)
    assert recovering.phase in {
        Phase.TROUGHING,
        Phase.EARLY_RECOVERY,
        Phase.EXPANSION,
    }

    noisy = {key: list(series) for key, series in observations.items()}
    for key, series in noisy.items():
        latest = series[-1]
        series[-1] = Observation(
            latest.period,
            latest.value - 0.2,
            latest.available_at,
        )
    held = engine.assess(noisy, specs, as_of, previous_phase=recovering.phase)
    assert held.phase not in {Phase.PEAKING, Phase.CONTRACTION}


def test_artifact_separates_descriptive_signal_from_forecast_and_trade_authority() -> None:
    observations, specs, as_of = recovery_panel()
    assessment = MacroTurnaroundEngine().assess(observations, specs, as_of)
    artifact = build_research_artifact(assessment)

    assert artifact["schema"] == "macro.turnaround_research.v1"
    assert artifact["capability_state"] == "BUILT_NOT_PROVEN"
    assert artifact["authority"] == {
        "descriptive_context": True,
        "research_priority": True,
        "calibrated_forecast": False,
        "ranking_authority": False,
        "gating_authority": False,
        "trade_authority": False,
    }
    assert "probability" not in json.dumps(artifact).lower()
    assert artifact["correction_policy"]["historical_artifacts_are_immutable"] is True
    assert artifact["input_hash"] == assessment.input_hash


@pytest.mark.parametrize(
    "field,value",
    [
        ("descriptive_context", False),
        ("research_priority", False),
        ("calibrated_forecast", True),
        ("ranking_authority", True),
        ("gating_authority", True),
        ("trade_authority", True),
    ],
)
def test_authority_boundary_is_fixed_and_not_caller_configurable(
    field: str,
    value: bool,
) -> None:
    with pytest.raises(TypeError):
        AuthorityBoundary(**{field: value})


def test_walk_forward_uses_ordered_release_vintages_and_prior_state() -> None:
    observations, specs, _ = recovery_panel()
    dates = [observations["new_orders"][index].available_at for index in (24, 30, 36, 40, 43)]
    results = MacroTurnaroundEngine().walk_forward(
        observations,
        specs,
        list(reversed(dates)),
    )
    assert [result.as_of for result in results] == sorted(dates)
    assert all(
        current.previous_phase == previous.phase
        for previous, current in zip(results, results[1:])
    )


def test_cli_writes_deterministic_machine_artifact(tmp_path: Path) -> None:
    observations, specs, as_of = recovery_panel()
    payload = {
        "as_of": as_of.isoformat(),
        "previous_phase": None,
        "config": {"enter_score": 0.58, "hold_score": 0.51},
        "specs": [spec.to_dict() for spec in specs],
        "observations": {
            key: [observation.to_dict() for observation in series]
            for key, series in observations.items()
        },
    }
    source = tmp_path / "input.json"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    for target in (first, second):
        completed = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--input",
                str(source),
                "--output",
                str(target),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
    assert first.read_bytes() == second.read_bytes()
    artifact = json.loads(first.read_text(encoding="utf-8"))
    assert artifact["schema"] == "macro.turnaround_research.v1"
    assert artifact["authority"]["trade_authority"] is False
    assert artifact["authority"]["calibrated_forecast"] is False


def test_transform_and_configuration_validation_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="family"):
        IndicatorSpec("orders", "")
    with pytest.raises(ValueError, match="weight"):
        IndicatorSpec("orders", "activity", weight=0.0)
    with pytest.raises(ValueError, match="hold_score"):
        TurnaroundConfig(enter_score=0.55, hold_score=0.60)
    assert Transform("yoy_pct_change") is Transform.YOY_PCT_CHANGE
    assert AuthorityBoundary().trade_authority is False


@pytest.mark.parametrize("value", [True, False, "1.0", None, float("nan"), float("inf"), -float("inf"), 10**400])
def test_observation_rejects_non_numeric_or_nonfinite_values(value: object) -> None:
    for construct in (
        lambda: Observation(date(2022, 1, 1), value, date(2022, 1, 2)),
        lambda: Observation.from_dict({"period": "2022-01-01", "value": value, "available_at": "2022-01-02"}),
    ):
        with pytest.raises(ValueError, match="value"):
            construct()


@pytest.mark.parametrize("value", ["2022-01-01garbage", "2022-01-01T09:00:00Z", "20220101", "2022-W01-1"])
def test_observation_requires_canonical_daily_dates(value: str) -> None:
    with pytest.raises(ValueError, match="date"):
        Observation(value, 1.0, "2022-02-01")


def test_daily_engine_rejects_intraday_cutoffs_instead_of_truncating_them() -> None:
    from datetime import datetime, timezone
    observations, specs, as_of = recovery_panel()
    intraday = datetime.combine(as_of, datetime.min.time(), tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="daily|date"):
        MacroTurnaroundEngine().assess(observations, specs, intraday)


@pytest.mark.parametrize("polarity", ["false", 0, 1, None])
def test_direct_indicator_spec_requires_boolean_polarity(polarity: object) -> None:
    with pytest.raises(ValueError, match="positive_when_rising"):
        IndicatorSpec("x", "activity", positive_when_rising=polarity)


@pytest.mark.parametrize("field,value", [
    ("key", None), ("family", 12), ("weight", True), ("weight", "1"),
    ("weight", float("nan")), ("weight", float("inf")),
    ("max_age_days", 10.5), ("max_age_days", True),
    ("minimum_history", 18.9), ("minimum_history", "18"),
])
def test_indicator_spec_rejects_coerced_or_invalid_fields(field: str, value: object) -> None:
    payload = {"key": "x", "family": "activity", field: value}
    for construct in (lambda: IndicatorSpec(**payload), lambda: IndicatorSpec.from_dict(payload)):
        with pytest.raises(ValueError, match=field):
            construct()


@pytest.mark.parametrize("field,value", [
    ("short_window", True), ("short_window", 3.5), ("medium_window", 6.5),
    ("robust_history", "60"), ("top_driver_count", 2.5), ("horizon_months", True),
    ("signal_temperature", float("nan")), ("signal_temperature", float("inf")),
    ("family_weight_cap", True), ("minimum_coverage", True),
    ("enter_score", "0.64"), ("hold_score", True),
])
def test_config_rejects_invalid_scalar_types(field: str, value: object) -> None:
    with pytest.raises(ValueError, match=field):
        TurnaroundConfig.from_dict({field: value})


def test_same_vintage_conflicts_cannot_depend_on_input_order() -> None:
    observations, specs, as_of = recovery_panel()
    item = observations["new_orders"][-1]
    conflict = Observation(item.period, item.value + 20, item.available_at)
    for records in (observations["new_orders"] + [conflict], [conflict] + observations["new_orders"]):
        with pytest.raises(ValueError, match="conflicting.*vintage"):
            MacroTurnaroundEngine().assess({**observations, "new_orders": records}, specs, as_of)


def test_identical_duplicate_vintages_are_idempotent() -> None:
    observations, specs, as_of = recovery_panel()
    engine = MacroTurnaroundEngine()
    first = engine.assess(observations, specs, as_of)
    duplicate = {key: series + series for key, series in observations.items()}
    assert engine.assess(duplicate, specs, as_of).to_dict() == first.to_dict()


def test_specification_and_observation_order_do_not_change_artifact() -> None:
    observations, specs, as_of = recovery_panel()
    engine = MacroTurnaroundEngine()
    first = build_research_artifact(engine.assess(observations, specs, as_of))
    reordered = {key: list(reversed(series)) for key, series in reversed(list(observations.items()))}
    second = build_research_artifact(engine.assess(reordered, list(reversed(specs)), as_of))
    assert second == first


def test_missing_and_future_only_series_have_same_historical_identity() -> None:
    observations, specs, as_of = recovery_panel()
    baseline = {"new_orders": observations["new_orders"]}
    future = Observation(as_of, 7, as_of + timedelta(days=1))
    engine = MacroTurnaroundEngine()
    first = engine.assess(baseline, specs, as_of)
    second = engine.assess({**baseline, "weekly_hours": [future]}, specs, as_of)
    assert first.to_dict() == second.to_dict()


def test_future_conflicting_vintages_do_not_affect_an_earlier_cutoff() -> None:
    observations, specs, as_of = recovery_panel()
    baseline = MacroTurnaroundEngine().assess(observations, specs, as_of)
    release = as_of + timedelta(days=1)
    future = [Observation(as_of, 1, release), Observation(as_of, 2, release)]
    changed = {**observations, "new_orders": observations["new_orders"] + future}
    assert MacroTurnaroundEngine().assess(changed, specs, as_of).to_dict() == baseline.to_dict()


def test_fresh_revision_cannot_refresh_an_ancient_economic_period() -> None:
    series = monthly([100 + math.sin(i / 3) for i in range(44)])
    cutoff = date(2026, 9, 10)
    revised = series + [Observation(series[-1].period, 110, cutoff)]
    result = MacroTurnaroundEngine().assess({"x": revised}, [IndicatorSpec("x", "activity")], cutoff)
    assert result.phase is Phase.INDETERMINATE
    assert result.quality.excluded == {"x": "too_stale"}
    assert not result.signals


def test_one_correlated_family_cannot_replace_missing_family_coverage() -> None:
    series = monthly([100 + math.sin(i / 3) for i in range(44)])
    observations = {f"labor_{i}": series for i in range(10)}
    specs = [IndicatorSpec(key, "labor") for key in observations]
    specs += [IndicatorSpec("orders", "activity"), IndicatorSpec("spread", "credit")]
    result = MacroTurnaroundEngine().assess(observations, specs, series[-1].available_at)
    assert result.quality.coverage == pytest.approx(0.35)
    assert result.phase is Phase.INDETERMINATE
    assert result.confidence == 0


def test_infeasible_family_cap_is_disclosed_not_silently_relaxed() -> None:
    series = monthly([100 + math.sin(i / 3) for i in range(44)])
    result = MacroTurnaroundEngine().assess({"x": series}, [IndicatorSpec("x", "activity")], series[-1].available_at)
    assert "family_cap_infeasible" in result.quality.flags
    assert result.confidence <= 0.35


def test_zero_denominator_does_not_collapse_time_and_report_a_signal() -> None:
    values = [100 + math.sin(i / 3) for i in range(44)]
    values[-2] = 0
    series = monthly(values)
    spec = IndicatorSpec("x", "activity", transform=Transform.PCT_CHANGE)
    result = MacroTurnaroundEngine().assess({"x": series}, [spec], series[-1].available_at)
    assert result.quality.excluded == {"x": "undefined_percentage_change"}
    assert not result.signals


def test_yoy_transform_requires_contiguous_monthly_periods() -> None:
    series = monthly([100 + math.sin(i / 3) for i in range(48)])
    del series[-8]
    spec = IndicatorSpec("x", "activity", transform=Transform.YOY_PCT_CHANGE)
    result = MacroTurnaroundEngine().assess({"x": series}, [spec], series[-1].available_at)
    assert result.quality.excluded == {"x": "nonmonthly_yoy_history"}
    assert not result.signals


def test_artifact_identity_binds_cutoff_and_previous_state() -> None:
    observations, specs, as_of = recovery_panel()
    engine = MacroTurnaroundEngine()
    first = build_research_artifact(engine.assess(observations, specs, as_of))
    later = build_research_artifact(engine.assess(observations, specs, as_of + timedelta(days=1)))
    prior = build_research_artifact(engine.assess(observations, specs, as_of, previous_phase=Phase.SLOWDOWN))
    assert first["input_hash"] == later["input_hash"] == prior["input_hash"]
    assert len(first["artifact_hash"]) == 64
    assert len({first["artifact_hash"], later["artifact_hash"], prior["artifact_hash"]}) == 3


def test_duplicate_replay_cutoffs_are_rejected() -> None:
    observations, specs, as_of = recovery_panel()
    with pytest.raises(ValueError, match="unique"):
        MacroTurnaroundEngine().walk_forward(observations, specs, [as_of, as_of])


def cli_payload() -> dict[str, object]:
    observations, specs, as_of = recovery_panel()
    return {
        "as_of": as_of.isoformat(),
        "previous_phase": None,
        "config": {},
        "specs": [spec.to_dict() for spec in specs],
        "observations": {key: [item.to_dict() for item in series] for key, series in observations.items()},
    }


def run_cli(source: Path, target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--input", str(source), "--output", str(target)],
        cwd=ROOT, text=True, capture_output=True, timeout=20, check=False,
    )


def test_cli_refuses_to_replace_an_existing_historical_artifact(tmp_path: Path) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    target.write_bytes(b'{"historical": "must not be overwritten"}\n')
    before = target.read_bytes()
    result = run_cli(source, target)
    assert result.returncode == 2
    assert "immutable" in result.stderr.lower()
    assert target.read_bytes() == before
    assert set(tmp_path.iterdir()) == {source, target}


def test_cli_identical_replay_is_idempotent_without_replacing_the_inode(tmp_path: Path) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    assert run_cli(source, target).returncode == 0
    before = target.stat()
    original = target.read_bytes()
    assert run_cli(source, target).returncode == 0
    assert target.read_bytes() == original
    assert (target.stat().st_ino, target.stat().st_mtime_ns) == (before.st_ino, before.st_mtime_ns)


def test_cli_does_not_use_or_touch_a_predictable_temporary_path(tmp_path: Path) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    unrelated = tmp_path / ".history.json.tmp"
    unrelated.write_bytes(b"unrelated task output")
    assert run_cli(source, target).returncode == 0
    assert unrelated.read_bytes() == b"unrelated task output"
    assert set(tmp_path.iterdir()) == {source, target, unrelated}


@pytest.mark.parametrize("field,value", [
    ("observations", []), ("observations", None), ("observations", {"new_orders": None}),
    ("specs", {}), ("specs", None), ("specs", "bad"), ("config", None),
    ("as_of", "20220811"), ("as_of", "2022-W32-4"),
])
def test_cli_bad_input_has_a_clean_error_and_no_output(tmp_path: Path, field: str, value: object) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    payload = cli_payload()
    payload[field] = value
    source.write_text(json.dumps(payload), encoding="utf-8")
    result = run_cli(source, target)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "ERROR" in result.stderr
    assert not target.exists()
    assert set(tmp_path.iterdir()) == {source}


@pytest.mark.parametrize("raw", ["null", "[]", "1", '"input"'])
def test_cli_requires_a_json_object(tmp_path: Path, raw: str) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    source.write_text(raw, encoding="utf-8")
    result = run_cli(source, target)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not target.exists()


@pytest.mark.parametrize("nested", [False, True])
def test_cli_rejects_duplicate_json_keys(tmp_path: Path, nested: bool) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    raw = json.dumps(cli_payload())
    if nested:
        raw = raw.replace('"config": {}', '"config": {"short_window": 3, "short_window": 4}')
    else:
        raw = raw.replace('{"as_of":', '{"as_of": "2022-01-01", "as_of":', 1)
    source.write_text(raw, encoding="utf-8")
    result = run_cli(source, target)
    assert result.returncode == 2
    assert "duplicate" in result.stderr.lower()
    assert not target.exists()


def test_cli_refuses_to_overwrite_its_input(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    before = source.read_bytes()
    result = run_cli(source, source)
    assert result.returncode == 2
    assert source.read_bytes() == before


def test_cli_refuses_output_symlinks(tmp_path: Path) -> None:
    source, target, destination = tmp_path / "input.json", tmp_path / "history.json", tmp_path / "other.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    destination.write_text("unrelated data", encoding="utf-8")
    target.symlink_to(destination)
    result = run_cli(source, target)
    assert result.returncode == 2
    assert target.is_symlink()
    assert destination.read_text(encoding="utf-8") == "unrelated data"


def test_cli_concurrent_different_publications_have_one_winner(tmp_path: Path) -> None:
    target = tmp_path / "history.json"
    sources = []
    expected = set()
    for index in range(5):
        payload = cli_payload()
        payload["as_of"] = (date.fromisoformat(payload["as_of"]) + timedelta(days=index)).isoformat()
        source = tmp_path / f"input-{index}.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        sources.append(source)
        # Build the expected bytes through the real CLI, not a second serializer.
        expected_path = tmp_path / f"expected-{index}.json"
        assert run_cli(source, expected_path).returncode == 0
        expected.add(expected_path.read_bytes())
    children = [subprocess.Popen(
        [sys.executable, str(CLI), "--input", str(source), "--output", str(target)],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ) for source in sources]
    for child in children:
        child.communicate(timeout=20)
    assert sorted(child.returncode for child in children) == [0, 2, 2, 2, 2]
    assert target.read_bytes() in expected
    assert not list(tmp_path.glob(".*.tmp"))


def test_cli_concurrent_identical_publications_all_succeed(tmp_path: Path) -> None:
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    children = [subprocess.Popen(
        [sys.executable, str(CLI), "--input", str(source), "--output", str(target)],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ) for _ in range(5)]
    outputs = [child.communicate(timeout=20) for child in children]
    assert all(child.returncode == 0 for child in children), outputs
    assert json.loads(target.read_text())['authority']['trade_authority'] is False
    assert set(tmp_path.iterdir()) == {source, target}


def test_tiny_uniform_weights_preserve_the_signal_without_underflow() -> None:
    observations, specs, cutoff = recovery_panel()
    engine = MacroTurnaroundEngine()
    normal = engine.assess(observations, specs, cutoff)
    tiny_specs = [IndicatorSpec(
        item.key, item.family, weight=5e-324, positive_when_rising=item.positive_when_rising,
    ) for item in specs]
    tiny = engine.assess(observations, tiny_specs, cutoff)
    assert tiny.phase == normal.phase
    assert tiny.quality.coverage == pytest.approx(normal.quality.coverage)
    assert tiny.confidence == pytest.approx(normal.confidence)
    assert tiny.upturn_score == pytest.approx(normal.upturn_score)
    assert [item.effective_weight for item in tiny.signals] == pytest.approx(
        [item.effective_weight for item in normal.signals]
    )


def test_duplicate_signed_zero_vintages_have_order_invariant_identity() -> None:
    series = monthly([1.0] * 43 + [0.0])
    latest = series[-1]
    negative_zero = Observation(latest.period, -0.0, latest.available_at)
    engine, specs = MacroTurnaroundEngine(), [IndicatorSpec("x", "activity")]
    first = engine.assess({"x": series + [negative_zero]}, specs, latest.available_at)
    second = engine.assess({"x": [negative_zero] + series}, specs, latest.available_at)
    assert build_research_artifact(first) == build_research_artifact(second)


def test_cli_publication_failure_leaves_no_partial_output_or_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location("turnaround_cli_failure_test", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, target = tmp_path / "input.json", tmp_path / "history.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    def fail_link(*args: object, **kwargs: object) -> None:
        raise OSError("injected publication filesystem failure")
    monkeypatch.setattr(module.os, "link", fail_link)
    assert module.main(["--input", str(source), "--output", str(target)]) == 2
    assert set(tmp_path.iterdir()) == {source}


@pytest.mark.parametrize("seed", range(64))
def test_seeded_point_in_time_and_order_invariants(seed: int) -> None:
    import random
    rng = random.Random(seed)
    families = ["activity", "labor", "credit", "housing"]
    observations = {}
    specs = []
    for index, family in enumerate(families):
        key = f"indicator_{index}"
        values = [100 + 10 * math.sin(i / 4 + index) + rng.uniform(-1.5, 1.5) for i in range(48)]
        observations[key] = monthly(values, delay_days=5 + index * 3)
        specs.append(IndicatorSpec(key, family, weight=rng.uniform(0.1, 3), positive_when_rising=index != 2))
    cutoff = observations["indicator_0"][40].period + timedelta(days=12)
    engine = MacroTurnaroundEngine()
    baseline = build_research_artifact(engine.assess(observations, specs, cutoff))
    changed = {key: list(records) for key, records in observations.items()}
    for key in changed:
        # Revise an old period, but publish the new vintage after the cutoff.
        changed[key].append(Observation(changed[key][20].period, rng.uniform(-1000, 1000), cutoff + timedelta(days=1)))
        rng.shuffle(changed[key])
    rng.shuffle(specs)
    assert build_research_artifact(engine.assess(changed, specs, cutoff)) == baseline
    assert build_research_artifact(engine.assess(observations, specs, cutoff)) == baseline
    assert 0 <= baseline["confidence"] <= 1
    assert baseline["authority"]["trade_authority"] is False
    assert baseline["authority"]["calibrated_forecast"] is False
    json.dumps(baseline, allow_nan=False)


def test_cli_rejects_even_an_identical_output_symlink(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    destination = tmp_path / "existing-identical.json"
    target = tmp_path / "history.json"
    source.write_text(json.dumps(cli_payload()), encoding="utf-8")
    assert run_cli(source, destination).returncode == 0
    before = destination.read_bytes()
    target.symlink_to(destination)

    result = run_cli(source, target)

    assert result.returncode == 2
    assert "symbolic link" in result.stderr.lower()
    assert target.is_symlink()
    assert destination.read_bytes() == before


def test_assess_rejects_observation_keys_without_indicator_specs() -> None:
    observations, specs, cutoff = recovery_panel()
    observations["undeclared_series"] = monthly([100.0] * 44)

    with pytest.raises(ValueError, match="unknown observation series.*undeclared_series"):
        MacroTurnaroundEngine().assess(observations, specs, cutoff)


def test_turnaround_suites_have_one_code_gated_ci_owner() -> None:
    import yaml

    targets = (
        "tests/test_macro_turnaround_research.py",
        "tests/test_macro_turnaround_replay.py",
        "tests/test_macro_turnaround_replay_cli.py",
        "tests/test_macro_turnaround_feature_honesty.py",
        "tests/test_macro_turnaround_evidence_change.py",
    )
    jobs = yaml.safe_load(
        (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    )["jobs"]
    owner_by_target: dict[str, list[str]] = {target: [] for target in targets}
    for job_name, job in jobs.items():
        run_body = "\n".join(
            str(step.get("run", "")) for step in job.get("steps", [])
        )
        for target in targets:
            owner_by_target[target].extend([job_name] * run_body.count(target))

    assert owner_by_target == {
        target: ["macro-turnaround-research"] for target in targets
    }
    owner = jobs["macro-turnaround-research"]
    assert owner["gate"] == "code"
    install = "\n".join(
        str(step.get("run", ""))
        for step in owner["steps"]
        if "pip install" in str(step.get("run", ""))
    )
    for dependency in ("pytest", "pandas", "pyarrow", "pyyaml"):
        assert dependency in install


@pytest.mark.parametrize("config", [False, 0, {}, "default"])
def test_engine_rejects_non_config_constructor_values(config: object) -> None:
    with pytest.raises(TypeError, match="TurnaroundConfig"):
        MacroTurnaroundEngine(config)  # type: ignore[arg-type]


def test_data_quality_defensively_freezes_exclusion_mapping() -> None:
    excluded = {"stale": "too_old"}
    quality = DataQuality(
        coverage=0.5,
        recency=0.5,
        agreement=0.5,
        history=0.5,
        excluded=excluded,
        flags=(),
    )
    excluded["stale"] = "mutated"
    excluded["future"] = "added_later"
    assert quality.excluded == {"stale": "too_old"}
    with pytest.raises(TypeError):
        quality.excluded["new"] = "mutation"  # type: ignore[index]
