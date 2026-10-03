"""Golden-set editorial comparisons: synthetic judgments, never human labels."""
from __future__ import annotations

import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.marketing import golden_set as gs
from scripts import marketing_golden_set as cli


def case(number=0, split="holdout"):
    artifact = {"input_sha256": "a"*64, "decision": "draft", "text": "A supplied baseline observation.",
                "visual_ref": "", "visual_sha256": ""}
    return {"case_id": f"case-{number}", "event_id": f"event-{number}", "split": split,
            "input_sha256": "a"*64, "evidence_ref": f"fixture:evidence-{number}",
            "baseline": artifact, "frontier": dict(artifact, text="A supplied frontier interpretation.")}


def judgment(card, choice="left"):
    return {"comparison_id": card["comparison_id"], "choice": choice,
            "reviewer_ref": "fixture-human-review-not-real", "judgment_source": "human"}


def test_deterministic_blind_export_removes_arm_labels():
    cases = [case()]
    before = copy.deepcopy(cases)
    result = gs.blind_editorial_pairs(cases, seed="fixture-seed")
    assert result == gs.blind_editorial_pairs(cases, seed="fixture-seed")
    assert cases == before
    card = result["cards"][0]
    assert set(card) == {"comparison_id", "case_id", "split", "evidence_ref", "input_sha256", "left", "right"}
    assert "baseline" not in card and "frontier" not in card and "seed" not in card
    assert result["assignments"][0]["left_arm"] in {"baseline", "frontier"}
    assert result["promotion_authorized"] is False


def test_input_identity_mismatch_is_not_a_fair_comparison():
    bad = case()
    bad["frontier"]["input_sha256"] = "b"*64
    with pytest.raises(ValueError):
        gs.blind_editorial_pairs([bad], seed="s")


def test_duplicate_cases_and_overlapping_events_are_rejected():
    for duplicate in (case(), dict(case(1), event_id="event-0")):
        with pytest.raises(ValueError):
            gs.blind_editorial_pairs([case(), duplicate], seed="s")


def test_changed_text_invalidates_old_judgment():
    cases = [case()]
    old = gs.blind_editorial_pairs(cases, seed="s")["cards"][0]
    cases[0]["frontier"]["text"] += " Changed."
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs(cases, [judgment(old)], seed="s")


def test_changed_visual_bytes_invalidate_old_judgment():
    cases = [case()]
    cases[0]["frontier"].update(visual_ref="fixture:image", visual_sha256="c"*64)
    card = gs.blind_editorial_pairs(cases, seed="s")["cards"][0]
    cases[0]["frontier"]["visual_sha256"] = "d"*64
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs(cases, [judgment(card)], seed="s")


def test_zero_human_judgments_never_produces_zero_or_pass():
    report = gs.evaluate_editorial_pairs([case()], [], seed="s")
    assert report["state"] == "no-labels"
    assert report["frontier_preference_rate"] is None
    assert report["p_value_two_sided"] is None
    assert report["promotion_authorized"] is False
    assert report["factual_accuracy"] == "not_measured"


def test_small_n_is_reported_as_insufficient():
    cards = gs.blind_editorial_pairs([case()], seed="s")["cards"]
    report = gs.evaluate_editorial_pairs([case()], [judgment(cards[0])], seed="s")
    assert report["state"] == "insufficient"
    assert report["p_value_two_sided"] is None
    assert report["judged_holdout"] == 1


def test_development_labels_do_not_qualify_holdout():
    cases = [case(0, "development"), case(1, "holdout")]
    cards = gs.blind_editorial_pairs(cases, seed="s", min_pairs=1)["cards"]
    report = gs.evaluate_editorial_pairs(cases, [judgment(cards[0])], seed="s", min_pairs=1)
    assert report["state"] == "no-labels"
    assert report["judged_holdout"] == 0
    assert report["excluded_development_judgments"] == 1


def test_ties_and_neither_are_not_frontier_wins():
    cases = [case(i) for i in range(2)]
    cards = gs.blind_editorial_pairs(cases, seed="s", min_pairs=2)["cards"]
    report = gs.evaluate_editorial_pairs(cases, [judgment(cards[0], "tie"), judgment(cards[1], "neither")], seed="s", min_pairs=2)
    assert report["state"] == "measured"
    assert report["ties"] == report["neither"] == 1
    assert report["informative_pairs"] == 0
    assert report["frontier_preference_rate"] is None
    assert report["p_value_two_sided"] is None


def test_known_all_frontier_preferences_use_existing_exact_test():
    cases = [case(i) for i in range(6)]
    bundle = gs.blind_editorial_pairs(cases, seed="s", min_pairs=6)
    rows = [judgment(card, "left" if assignment["left_arm"] == "frontier" else "right")
            for card, assignment in zip(bundle["cards"], bundle["assignments"])]
    report = gs.evaluate_editorial_pairs(cases, rows, seed="s", min_pairs=6)
    assert report["frontier_wins"] == 6 and report["baseline_wins"] == 0
    assert report["frontier_preference_rate"] == 1.0
    assert report["p_value_two_sided"] == pytest.approx(2/64)
    assert report["promotion_authorized"] is False


def test_blind_orientation_does_not_change_named_arm_results():
    cases = [case(i) for i in range(10)]
    reports = []
    for seed in ("one", "two"):
        bundle = gs.blind_editorial_pairs(cases, seed=seed, min_pairs=10)
        rows = [judgment(c, "left" if a["left_arm"] == "frontier" else "right")
                for c, a in zip(bundle["cards"], bundle["assignments"])]
        reports.append(gs.evaluate_editorial_pairs(cases, rows, seed=seed, min_pairs=10))
    assert reports[0]["frontier_wins"] == reports[1]["frontier_wins"] == 10


def test_duplicate_judgments_do_not_inflate_sample_size():
    row = judgment(gs.blind_editorial_pairs([case()], seed="s")["cards"][0])
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs([case()], [row, row], seed="s")


def test_model_self_ratings_are_not_human_ground_truth():
    row = judgment(gs.blind_editorial_pairs([case()], seed="s")["cards"][0])
    for source in ("model", "critic", "unknown", ""):
        with pytest.raises(ValueError):
            gs.evaluate_editorial_pairs([case()], [dict(row, judgment_source=source)], seed="s")


def test_abstention_is_preserved_not_replaced_by_filler():
    row = case()
    row["frontier"].update(decision="abstain", text="")
    report = gs.evaluate_editorial_pairs([row], [], seed="s")
    assert report["frontier_abstentions"] == 1
    row["frontier"]["text"] = "Fallback filler."
    with pytest.raises(ValueError):
        gs.blind_editorial_pairs([row], seed="s")


def test_missing_visual_digest_is_not_a_bound_asset():
    row = case()
    row["frontier"]["visual_ref"] = "fixture:image"
    with pytest.raises(ValueError):
        gs.blind_editorial_pairs([row], seed="s")


def test_unknown_fields_or_split_are_rejected():
    for row in (dict(case(), approved=True), dict(case(), split="training")):
        with pytest.raises(ValueError):
            gs.blind_editorial_pairs([row], seed="s")


def test_min_pairs_cannot_be_bool_zero_or_float():
    for minimum in (False, 0, 1.0, -1, 1001):
        with pytest.raises(ValueError):
            gs.evaluate_editorial_pairs([], [], seed="s", min_pairs=minimum)


def test_cli_blinds_without_loading_production_or_writing_labels(tmp_path):
    path = tmp_path/"input.json"
    path.write_text(json.dumps({"cases": [case()], "seed": "fixture"}))
    before = path.read_bytes()
    output = io.StringIO()
    with patch.object(cli, "_golden_cfg", side_effect=AssertionError("production config")), redirect_stdout(output):
        assert cli.main(["editorial-blind", str(path)]) == 0
    assert path.read_bytes() == before and len(list(tmp_path.iterdir())) == 1
    packet = json.loads(output.getvalue())
    assert packet["cards"][0]["comparison_id"]
    assert "assignments" not in packet and "seed" not in packet


def test_cli_empty_evaluation_is_not_qualified(tmp_path):
    path = tmp_path/"input.json"
    path.write_text(json.dumps({"cases": [case()], "seed": "fixture", "judgments": []}))
    output = io.StringIO()
    with redirect_stdout(output):
        assert cli.main(["editorial-eval", str(path)]) == 1
    assert json.loads(output.getvalue())["state"] == "no-labels"


def test_cli_malformed_or_duplicate_json_is_fixed_failure(tmp_path):
    path = tmp_path/"input.json"
    path.write_text('{"cases":[],"cases":[],"seed":"fixture"}')
    output = io.StringIO()
    with redirect_stdout(output):
        assert cli.main(["editorial-blind", str(path)]) == 2
    assert json.loads(output.getvalue())["state"] == "invalid-input"


def test_identical_outputs_cannot_supply_a_directional_win():
    row = case()
    row["frontier"] = copy.deepcopy(row["baseline"])
    card = gs.blind_editorial_pairs([row], seed="s")["cards"][0]
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs([row], [judgment(card, "left")], seed="s")
    assert gs.evaluate_editorial_pairs([row], [judgment(card, "tie")], seed="s")["ties"] == 1


def test_generation_unavailability_is_not_editorial_abstention():
    row = case()
    row["frontier"].update(decision="unavailable", text="")
    report = gs.evaluate_editorial_pairs([row], [], seed="s")
    assert report["frontier_unavailable"] == 1
    assert report["frontier_abstentions"] == 0
    assert report["frontier_preference_rate"] is None


def test_changing_development_to_holdout_retires_prior_judgments():
    row = case(split="development")
    card = gs.blind_editorial_pairs([row], seed="s")["cards"][0]
    row["split"] = "holdout"
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs([row], [judgment(card)], seed="s")


def test_identity_whitespace_cannot_split_one_event_into_two():
    for field in ("case_id", "event_id"):
        row = case()
        row[field] = " " + row[field]
        with pytest.raises(ValueError):
            gs.blind_editorial_pairs([row], seed="s")


def test_preferences_do_not_replace_factual_or_growth_evidence():
    row = case()
    card = gs.blind_editorial_pairs([row], seed="s", min_pairs=1)["cards"][0]
    report = gs.evaluate_editorial_pairs([row], [judgment(card)], seed="s", min_pairs=1)
    assert report["factual_accuracy"] == report["growth_lift"] == "not_measured"
    assert report["promotion_authorized"] is False
    assert "not_population" in report["estimator"]


def test_dropping_another_case_invalidates_retained_judgment():
    cases = [case(0), case(1)]
    old = gs.blind_editorial_pairs(cases, seed="s")["cards"][0]
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs(cases[:1], [judgment(old)], seed="s")


def test_lowering_minimum_after_labels_invalidates_judgment():
    cases = [case()]
    card = gs.blind_editorial_pairs(cases, seed="s", min_pairs=30)["cards"][0]
    with pytest.raises(ValueError):
        gs.evaluate_editorial_pairs(cases, [judgment(card)], seed="s", min_pairs=1)
