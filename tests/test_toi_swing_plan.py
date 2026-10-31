"""Synthetic recipe mechanics only: no market inputs, returns or authority."""
import copy
import json
from pathlib import Path
import pytest
from scripts.research import run_toi_swing_plan as planner

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "research/technical_opportunity/swing_confluence/recipe.json"

def sample():
    return json.loads(RECIPE.read_text())

def test_frozen_plan_counts_are_explicit_and_not_execution():
    r = planner.compile_recipe(sample(), include_cases=True)
    assert r["configuration_count"] == 720
    assert r["cost_scenario_count"] == 2160
    assert r["planned_comparison_upper_bound"] == 8640
    assert len(r["cases"]) == 720
    assert len({c["case_id"] for c in r["cases"]}) == 720
    assert r["status"] == "DRAFT_NOT_REGISTERED"
    assert r["outcome_execution_available"] is False
    assert r["trial_ledger_written"] is False
    assert r["network_used"] is False
    assert not any(r["authority"].values())

def test_default_summary_does_not_emit_candidate_array():
    assert "cases" not in planner.compile_recipe(sample())

def test_axis_order_does_not_change_digest_or_cases():
    original = sample()
    reordered = copy.deepcopy(original)
    for key in ("families", "clock_pairs", "memory_modes", "signal_bundles", "holding_sessions", "exit_rules", "cost_bps_one_way", "baselines"):
        reordered[key].reverse()
    assert planner.compile_recipe(original, include_cases=True) == planner.compile_recipe(reordered, include_cases=True)

def test_semantic_change_changes_digest():
    first = sample(); second = sample(); second["random_seed"] += 1
    assert planner.compile_recipe(first)["recipe_sha256"] != planner.compile_recipe(second)["recipe_sha256"]

def test_clock_arithmetic_is_not_calendar_or_parity_proof():
    report = planner.compile_recipe(sample())
    clocks = {d["nominal_minutes"]: d for d in report["clock_arithmetic"]}
    assert clocks[120]["full_buckets"] == 3
    assert clocks[120]["terminal_minutes"] == 30
    assert clocks[180]["full_buckets"] == 2
    assert clocks[180]["terminal_minutes"] == 30
    assert clocks[130]["terminal_minutes"] == 0
    assert clocks[195]["terminal_minutes"] == 0
    assert report["clock_arithmetic_is_calendar_proof"] is False

def test_declared_early_close_example_is_explicit_not_calendar_inference():
    r = sample(); r["session_example_minutes"] = 210
    d = {x["nominal_minutes"]: x for x in planner.compile_recipe(r)["clock_arithmetic"]}
    assert d[120]["terminal_minutes"] == 90
    assert d[180]["terminal_minutes"] == 30

@pytest.mark.parametrize("key,value", [
    ("schema", "unknown"), ("study_id", "../bad"), ("families", []),
    ("holding_sessions", [True]), ("holding_sessions", [1.0]),
    ("holding_sessions", [0]), ("holding_sessions", [1, 1]),
    ("cost_bps_one_way", [float("nan")]), ("cost_bps_one_way", [-1]),
    ("cost_bps_one_way", [True]), ("cost_bps_one_way", [5, 5.0]),
    ("primary_cost_bps_one_way", 7), ("primary_cost_bps_one_way", 0),
    ("random_seed", True), ("max_planned_comparisons", 100),
    ("max_planned_comparisons", True), ("session_example_minutes", False),
    ("memory_modes", ["unimplemented_magic_memory"]),
    ("outcome_execution_available", True), ("authority", {"may_trade": True}),
])
def test_invalid_or_authority_shaped_fields_are_rejected(key, value):
    r = sample(); r[key] = value
    with pytest.raises(planner.RecipeError):
        planner.compile_recipe(r)

@pytest.mark.parametrize("pair", [
    {"trigger_minutes": 30, "setup_minutes": 30},
    {"trigger_minutes": 120, "setup_minutes": 30},
    {"trigger_minutes": True, "setup_minutes": 120},
    {"trigger_minutes": 30, "setup_minutes": 0},
    {"trigger_minutes": 30, "setup_minutes": 120, "lookahead": True},
])
def test_invalid_clock_pairs_are_rejected(pair):
    r = sample(); r["clock_pairs"] = [pair]
    with pytest.raises(planner.RecipeError):
        planner.compile_recipe(r)

def test_duplicate_clock_pairs_are_rejected():
    r = sample(); r["clock_pairs"].append(r["clock_pairs"][0])
    with pytest.raises(planner.RecipeError):
        planner.compile_recipe(r)

def test_required_owner_cannot_be_deleted():
    r = sample(); del r["dependencies"]["source_admission"]
    with pytest.raises(planner.RecipeError):
        planner.compile_recipe(r)

def test_recipe_status_cannot_self_admit():
    r = sample(); r["dependencies"]["source_admission"]["status"] = "ADMIT"
    with pytest.raises(planner.RecipeError):
        planner.compile_recipe(r)

def test_references_never_grant_execution_or_authority():
    r = sample()
    for d in r["dependencies"].values():
        d.update(status="REFERENCED", reference="opaque-owner-receipt")
    result = planner.compile_recipe(r)
    assert result["outcome_execution_available"] is False
    assert not any(result["authority"].values())
    assert all(d["owner_verification_required"] for d in result["owner_requirements"].values())

def test_nonempty_reference_required_for_referenced_dependency():
    r = sample(); r["dependencies"]["source_admission"].update(status="REFERENCED", reference=None)
    with pytest.raises(planner.RecipeError):
        planner.compile_recipe(r)

@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{bad', '[]'])
def test_strict_json_reader_rejects_ambiguous_input(tmp_path, text):
    p = tmp_path / "bad.json"; p.write_text(text)
    with pytest.raises(planner.RecipeError):
        planner.load_recipe(p)

def test_missing_file_is_a_recipe_error(tmp_path):
    with pytest.raises(planner.RecipeError):
        planner.load_recipe(tmp_path / "missing.json")

def test_cli_summary_and_explicit_output(tmp_path, capsys):
    output = tmp_path / "plan.json"
    assert planner.main(["--recipe", str(RECIPE), "--output", str(output), "--include-cases"]) == 0
    stdout = json.loads(capsys.readouterr().out)
    stored = json.loads(output.read_text())
    assert stdout["recipe_sha256"] == stored["recipe_sha256"]
    assert "cases" not in stdout
    assert len(stored["cases"]) == 720

def test_cli_requires_output_for_large_case_array(capsys):
    assert planner.main(["--recipe", str(RECIPE), "--include-cases"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "--output" in captured.err

def test_cli_bad_input_is_bounded_no_traceback(tmp_path, capsys):
    p = tmp_path / "bad.json"; p.write_text('{}')
    assert planner.main(["--recipe", str(p)]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "Traceback" not in captured.err

def test_output_cannot_overwrite_existing_evidence(tmp_path, capsys):
    output = tmp_path / "evidence.json"; output.write_text('ORIGINAL')
    assert planner.main(["--recipe", str(RECIPE), "--output", str(output)]) == 2
    assert output.read_text() == 'ORIGINAL'
    assert not capsys.readouterr().out

def test_output_cannot_be_jsonl_or_a_trial_ledger(tmp_path, capsys):
    output = tmp_path / "trial_ledger.jsonl"
    assert planner.main(["--recipe", str(RECIPE), "--output", str(output)]) == 2
    assert not output.exists()
    assert not capsys.readouterr().out

def test_output_cannot_overwrite_input(capsys):
    before = RECIPE.read_bytes()
    assert planner.main(["--recipe", str(RECIPE), "--output", str(RECIPE)]) == 2
    assert RECIPE.read_bytes() == before
    assert not capsys.readouterr().out

def test_output_symlink_does_not_overwrite_target(tmp_path, capsys):
    source = tmp_path / "source.json"; source.write_text('ORIGINAL')
    output = tmp_path / "alias.json"; output.symlink_to(source)
    assert planner.main(["--recipe", str(RECIPE), "--output", str(output)]) == 2
    assert source.read_text() == 'ORIGINAL'
    assert not capsys.readouterr().out

def test_oversized_json_rejected(tmp_path):
    p = tmp_path / "large.json"; p.write_text(' ' * (planner.MAX_INPUT_BYTES + 1))
    with pytest.raises(planner.RecipeError, match='exceeds'):
        planner.load_recipe(p)

def test_no_outcome_run_flag_exists():
    with pytest.raises(SystemExit) as error:
        planner.main(["--recipe", str(RECIPE), "--run-outcomes"])
    assert error.value.code == 2

def test_planning_does_not_mutate_input():
    original = sample(); before = copy.deepcopy(original)
    planner.compile_recipe(original, include_cases=True)
    assert original == before

def test_fractional_cost_stress_is_not_silently_rounded():
    r = sample(); r["cost_bps_one_way"] = [2.5, 10]
    result = planner.compile_recipe(r)
    assert result["cost_scenario_count"] == 1440
    assert result["planned_comparison_upper_bound"] == 5760

def test_reserved_json_ledger_path_is_refused(tmp_path, capsys):
    output = tmp_path / "trial_ledger.json"
    assert planner.main(["--recipe", str(RECIPE), "--output", str(output)]) == 2
    assert not output.exists()
    assert not capsys.readouterr().out
