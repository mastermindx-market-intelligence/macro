"""Real owner imports and executable PB-D joins over fictional market inputs."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from engine.pb_d_cohort import append_correction
from scripts.query_pb_d_event_quality import evaluate_manifest, main, run_packet


FIXTURE = Path(__file__).parent / "fixtures" / "pb_d" / "research_packet.json"


@pytest.fixture
def packet():
    return json.loads(FIXTURE.read_text())


def test_owner_quality_cohort_and_statistics_run_together_without_input_mutation(packet):
    before = deepcopy(packet)
    result = run_packet(packet)
    assert packet == before
    assert result["state"] == "FROZEN_DESIGN_NOT_ENROLLED"
    assert not any(result["authority_flags"].values())
    rows = result["cohort"]["manifest"]["first_t2"]
    assert sorted(row["q"] for row in rows) == ["FALSE", "FALSE", "TRUE", "UNKNOWN"]
    assert result["cohort"]["manifest"]["accounting"]["frozen_pairs"] == 1
    assert result["evaluation"]["primary"]["equal_date_mean_increment_pp"] == 4.0
    assert result["evaluation"]["primary"]["complete_pair_count"] == 1
    assert result["evaluation"]["status"] == "NOT_ENROLLED"
    assert all(value["family_p_value"] == 1 for value in result["evaluation"]["secondary"].values())
    assert result["evaluation"]["adequacy_gates"]["primary_exposure_coverage"]["status"] == "FAIL"
    assert len(result["evaluation"]["omission_receipts"]) == 6  # issuers, INTC, date, sector
    coverage = result["evaluation"]["flow"]["stratified_coverage"]
    assert coverage["groups"]["decision_date"]["2026-10-07"]["first_t2_count"] == 4
    assert coverage["groups"]["decision_date"]["2026-10-07"]["quality_coverage_fraction"] == 0.75
    unknown = coverage["groups"]["q"]["UNKNOWN"]
    assert unknown["first_t2_count"] == unknown["quality_unknown_count"] == 1
    assert unknown["quality_known_count"] == unknown["matched_issuer_count"] == unknown["known_h5_count"] == 0


def test_outcome_values_do_not_change_first_t2_or_pair_manifest(packet):
    original = run_packet(packet)
    for outcome in packet["outcomes"]:
        for key in tuple(outcome):
            if key.endswith("_pp"):
                outcome[key] = -outcome[key]
    reversed_returns = run_packet(packet)
    assert original["cohort"] == reversed_returns["cohort"]
    assert reversed_returns["evaluation"]["primary"]["equal_date_mean_increment_pp"] == -4.0


def test_missing_control_outcome_excludes_whole_pair_without_rematching(packet):
    original = run_packet(packet)
    control = original["cohort"]["manifest"]["pairs"][0]["q0_observation_id"]
    packet["outcomes"] = [row for row in packet["outcomes"] if row["observation_id"] != control]
    changed = run_packet(packet)
    assert changed["cohort"] == original["cohort"]
    assert changed["evaluation"]["primary"]["complete_pair_count"] == 0
    assert changed["evaluation"]["primary"]["equal_date_mean_increment_pp"] is None


@pytest.mark.parametrize("field,replacement", [
    ("entry_session_date", "2026-10-08"),
    ("entry_close_at_utc", "2026-10-07T20:01:00Z"),
    ("h5_exit_session_date", "2026-10-15"),
    ("h5_exit_close_at_utc", "2026-10-14T20:01:00Z"),
    ("outcome_observed_at", "2026-10-07T13:00:00Z"),
    ("entry_status", "UNKNOWN"),
    ("price_receipt_ref", ""),
])
def test_wrong_or_unmatured_outcome_windows_are_refused(packet, field, replacement):
    packet["outcomes"][0][field] = replacement
    with pytest.raises(ValueError):
        run_packet(packet)


def test_unmatched_outcomes_need_the_same_price_and_clock_receipts(packet):
    result = run_packet(packet)
    matched = {leg for pair in result["cohort"]["manifest"]["pairs"]
               for leg in (pair["q1_observation_id"], pair["q0_observation_id"])}
    unmatched = next(row for row in packet["outcomes"] if row["observation_id"] not in matched)
    unmatched.pop("price_receipt_ref")
    with pytest.raises(ValueError, match="price receipt"):
        run_packet(packet)


def test_shared_benchmark_increment_identity_is_checked(packet):
    packet["outcomes"][0]["h5_absolute_return_pp"] += 0.1
    with pytest.raises(ValueError, match="increments disagree"):
        run_packet(packet)


@pytest.mark.parametrize("field,replacement", [("ticker_at_cut", "WRONG"), ("raw_attention", False)])
def test_quality_descriptive_fields_bind_to_the_board(packet, field, replacement):
    next(iter(packet["quality_requests"].values()))[field] = replacement
    with pytest.raises(ValueError, match="differs from"):
        run_packet(packet)


def test_unknown_or_duplicate_outcome_observations_are_refused(packet):
    packet["outcomes"].append(deepcopy(packet["outcomes"][0]))
    with pytest.raises(ValueError, match="duplicate outcome"):
        run_packet(packet)
    packet["outcomes"][-1]["observation_id"] = "not-a-first-t2"
    with pytest.raises(ValueError, match="retained first-T2"):
        run_packet(packet)


def test_consumer_refuses_prospective_activation_switch(packet):
    packet["dataset_kind"] = "PROSPECTIVE_ENROLLED"
    with pytest.raises(ValueError, match="cannot enroll"):
        run_packet(packet)


def test_omitting_a_control_rematches_the_full_eligible_pool(packet):
    result = run_packet(packet)
    original_pair = result["cohort"]["manifest"]["pairs"][0]
    omitted = original_pair["q0_issuer_id"]
    receipt = next(item["receipt"] for item in result["evaluation"]["omission_receipts"]
                   if item["kind"] == "ISSUER" and item["receipt"]["omitted_issuer_ids"] == [omitted])
    assert len(receipt["pairs"]) == 1
    assert receipt["pairs"][0]["q0_issuer_id"] != omitted
    assert receipt["pairs"][0]["q1_issuer_id"] == original_pair["q1_issuer_id"]


def test_date_and_sector_omissions_remove_both_full_eligible_pools(packet):
    result = run_packet(packet)
    report = result["evaluation"]
    for kind in ("DATE", "SECTOR"):
        receipt = next(item["receipt"] for item in report["omission_receipts"] if item["kind"] == kind)
        assert set(receipt["omitted_issuer_ids"]) == {
            "cik:0000320193", "cik:0000000002", "cik:0000000003"
        }
        assert receipt["pairs"] == []
        assert receipt["eligible_q1_count"] == receipt["eligible_q0_count"] == 0
        assert report["omission_sensitivity"]["date_sector_root_sensitivities"][kind] == "REPORTED"
    assert report["primary"]["equal_date_mean_increment_pp"] == 4.0


def test_intc_omission_uses_canonical_issuer_for_case_insensitive_ticker(packet):
    board_row = next(row for row in packet["cohort"]["cuts"][0]["rows"]
                     if row["canonical_issuer_id"] == "cik:0000000002")
    observation = board_row["observation_id"]
    board_row["ticker_at_cut"] = "intc"
    packet["quality_requests"][observation]["ticker_at_cut"] = "intc"
    next(row for row in packet["outcomes"] if row["observation_id"] == observation)["ticker_at_cut"] = "intc"
    result = run_packet(packet)
    intc = next(item for item in result["evaluation"]["omission_sensitivity"]["records"]
                if item["kind"] == "INTC")
    assert intc["omitted_issuer_ids"] == ("cik:0000000002",)


def test_integrity_correction_is_visible_and_excludes_whole_pair_in_sensitivity(packet):
    original = run_packet(packet)
    envelope = original["cohort"]
    pair = envelope["manifest"]["pairs"][0]
    changed = append_correction(envelope, {
        "correction_id": "synthetic-clock-correction", "target_observation_id": pair["q1_observation_id"],
        "original_claim_id": "synthetic-original-claim", "reason": "Synthetic mapping error for a hostile test",
        "correction_type": "DATA_INTEGRITY_EXCEPTION", "available_at": "2026-10-08T13:00:00Z",
        "observed_at": "2026-10-08T13:01:00Z", "corrected_receipt_sha256": "c" * 64,
    })
    report = evaluate_manifest(changed, packet["outcomes"], dataset_kind="SYNTHETIC_DRY_RUN")
    assert envelope["corrections"] == []
    assert changed["manifest"] == envelope["manifest"]
    assert report["primary"]["equal_date_mean_increment_pp"] == 4.0
    assert report["adequacy_gates"]["timing_root_price_version_integrity"]["status"] == "FAIL"
    assert report["correction_review"]["chain_head_sha256"] == changed["corrections"][-1]["correction_sha256"]
    assert report["integrity_exception_sensitivity"]["whole_pairs_excluded"] == [pair["pair_id"]]
    assert report["integrity_exception_sensitivity"]["primary_excluding_flagged_pairs"]["complete_pair_count"] == 0


def test_cli_writes_a_replayable_json_report_once_and_preserves_inputs(packet, tmp_path, capsys):
    source = tmp_path / "packet.json"
    source.write_text(json.dumps(packet))
    original = source.read_bytes()
    output = tmp_path / "report.json"
    assert main(["run", "--input", str(source), "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["evaluation"]["primary"]["equal_date_mean_increment_pp"] == 4.0
    output_bytes = output.read_bytes()
    assert main(["run", "--input", str(source), "--output", str(output)]) == 2
    assert output.read_bytes() == output_bytes
    assert main(["run", "--input", str(source), "--output", str(source)]) == 2
    assert source.read_bytes() == original
    assert "REFUSED" in capsys.readouterr().err


def test_nonfinite_json_is_refused_before_receipt_generation(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text('{"x": NaN}')
    assert main(["run", "--input", str(source)]) == 2
    assert "nonfinite JSON" in capsys.readouterr().err


def test_file_path_cli_pins_its_checkout_before_a_foreign_pythonpath(tmp_path):
    root = Path(__file__).resolve().parent.parent
    poison = tmp_path / "foreign-imports"
    package = poison / "engine"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('raise RuntimeError("foreign engine must not load")\n')
    output = tmp_path / "file-path-report.json"
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "query_pb_d_event_quality.py"),
         "run", "--input", str(FIXTURE.resolve()), "--output", str(output)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(poison), str(root))),
             "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(output.read_text())
    assert report["state"] == "FROZEN_DESIGN_NOT_ENROLLED"
    assert report["evaluation"]["primary"]["equal_date_mean_increment_pp"] == 4.0
