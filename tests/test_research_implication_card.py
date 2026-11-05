"""Contract tests for deterministic, non-authoritative research implication cards."""

from __future__ import annotations

from copy import deepcopy
import json
import re
import shutil
from pathlib import Path

import pytest

from engine import research_implication_card as ric
from engine.research_implication_card import (
    AUTHORITY_KEYS,
    CARD_SCHEMA,
    CardContractError,
    adapt_hincl2_event_study,
    adapt_synthetic_control,
    compute_card_id,
    sha256_file,
    validate_card,
)

ROOT = Path(__file__).resolve().parents[1]


def _coded(items: list[dict], code: str) -> dict:
    """Return one exact coded contract entry."""
    matches = [item for item in items if item["code"] == code]
    assert len(matches) == 1, f"expected one {code!r} entry, got {len(matches)}"
    return matches[0]


def _assert_closed_false_authority(card: dict) -> None:
    assert set(card["authority"]) == set(AUTHORITY_KEYS)
    assert all(value is False for value in card["authority"].values())


def _copy_inputs(root: Path, destination: Path, paths: tuple[str, ...]) -> None:
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)


SC_INPUTS = (
    "data/experiments/synthetic_control_phase0_results.json",
    "scripts/synthetic_control_phase0.py",
    "engine/synthetic_control.py",
    "research/SYNTHETIC_CONTROL_PHASE0.md",
)

HINCL2_INPUTS = (
    "data/experiments/hincl2_event_study_results.json",
    "scripts/hincl2_event_study.py",
    "research/HINCL2_PREREG.md",
    "reports/hincl2-phase0.md",
    "data/hk_connect_roster/roster.parquet",
)

MUTABLE_HSI_SNAPSHOT_DIGESTS = (
    "184cbdcf2437c9d8de172535cd87515b020708c9c441406391faa4aa895a1e45",
    "31a4e6d27653484458265b86cfcac3c7d9cd79da047d8509e4f0e0ec64302eac",
)


def test_real_synthetic_control_card_preserves_failed_diagnostic_truth() -> None:
    card = adapt_synthetic_control(ROOT)

    assert card["schema"] == CARD_SCHEMA
    assert re.fullmatch(r"ric_[0-9a-f]{64}", card["card_id"])
    assert card["method_family"] == "synthetic_control"
    assert card["study_run_id"] == "synthetic_control_phase0@2026-08-06"
    assert card["selected_result_id"] == "sp_pure_adds/sc_nnls/0_5"
    assert card["cutoff"] == "2026-07-02"
    assert card["sample_n"] == 303
    assert card["effective_n"] is None
    assert _coded(card["null_reasons"], "effective_n")["reason"] == "NOT_REPORTED"

    assert _coded(card["outputs"], "cumulative_abnormal_return")[
        "value"
    ] == pytest.approx(0.030151770605652363)
    assert _coded(card["outputs"], "monthly_newey_west_t")["value"] == 8.291
    assert _coded(card["outputs"], "monthly_observation_count")["value"] == 52
    assert _coded(card["placebos_or_counterexamples"], "placebo_mean")[
        "value"
    ] == pytest.approx(0.0019683084431491495)
    assert _coded(card["placebos_or_counterexamples"], "placebo_standard_deviation")[
        "value"
    ] == pytest.approx(0.006137674112846566)
    assert _coded(card["placebos_or_counterexamples"], "placebo_empirical_p")[
        "value"
    ] == pytest.approx(0.009950248756218905)

    assert card["quality"] == "DIAGNOSTIC_FAILED"
    assert card["evidence_tier"] == "DIAGNOSTIC"
    assert (
        _coded(card["diagnostics"], "PC1_positive_control_survives")["passed"] is True
    )
    assert _coded(card["diagnostics"], "PC2_estimators_unbiased")["passed"] is False
    assert _coded(card["diagnostics"], "PC3_sc_not_noisier")["passed"] is True
    assert _coded(card["diagnostics"], "F1_falsifier_holds")["passed"] is True
    assert card["ordered_effect_path"] is None

    result_receipt = next(
        artifact
        for artifact in card["source_artifacts"]
        if artifact["role"] == "result"
    )
    assert result_receipt == {
        "role": "result",
        "path": "data/experiments/synthetic_control_phase0_results.json",
        "sha256": "f759bdd72de5370e597459dc0630bb1f880e8a38be9b8882a1c75f54872af1e2",
        "as_of": "2026-07-02",
        "as_of_reason": None,
        "rights": "REPOSITORY_INTERNAL",
    }
    _assert_closed_false_authority(card)


def test_real_event_study_card_preserves_episode_n_and_typed_incompleteness() -> None:
    card = adapt_hincl2_event_study(ROOT)

    assert card["schema"] == CARD_SCHEMA
    assert card["adapter_version"] == "hincl2_event_study/v2"
    assert card["card_id"] == (
        "ric_9b430b2acf0b68ed64572e04640667b29f0409c4a5d95c096762567a10860d9a"
    )
    assert card["method_family"] == "event_study"
    assert card["study_run_id"] == "hincl2_event_study@2026-07-03"
    assert card["selected_result_id"] == "announce/h20"
    assert card["cutoff"] == "2026-07-03"
    assert card["sample_n"] == 282
    assert card["effective_n"] == 74

    assert (
        _coded(card["outputs"], "mean_cumulative_abnormal_return")["value"] == -0.08812
    )
    assert _coded(card["uncertainty"], "hac_mean")["value"] == -0.08812
    assert _coded(card["uncertainty"], "hac_standard_error")["value"] == 0.05317
    assert _coded(card["uncertainty"], "hac_t_statistic")["value"] == -1.657
    assert _coded(card["uncertainty"], "hac_p_value")["value"] == 0.0975
    assert _coded(card["uncertainty"], "mean_ci90")["value"] == [
        -0.18053,
        -0.08441,
        -0.01389,
    ]
    assert _coded(card["diagnostics"], "deflated_sharpe_ratio")["value"] == 0.0
    assert _coded(card["diagnostics"], "bh_fdr_announce_reject")["value"] is False
    assert _coded(card["diagnostics"], "bh_fdr_announce_q")["value"] == 0.962
    assert _coded(card["diagnostics"], "panel_coverage_fraction")["value"] == 0.6194

    path = card["ordered_effect_path"]
    assert path["evidence_status"] == "EXPLORATORY_NON_GATED"
    assert path["selected_horizon"] == 20
    assert path["sample_basis"]["en"].startswith("Equal-weighted across events")
    assert "episode" in path["comparison_note"]["en"].lower()
    assert path["accessible_name"]["zh"]
    selected_point = next(
        point
        for point in path["points"]
        if point["horizon"] == path["selected_horizon"]
    )
    assert selected_point == {"horizon": 20, "value": -0.02168, "n": 276}

    assert card["quality"] == "ARTIFACT_INCOMPLETE"
    assert card["evidence_tier"] == "DIAGNOSTIC"
    missing = {item["code"]: item for item in card["missingness"]}
    assert missing["hk_stocks_ext_digest"]["reason"] == "INPUT_DIGEST_MISSING"
    assert missing["hk_stocks_ext_rights"]["reason"] == "RIGHTS_RECEIPT_MISSING"
    assert missing["hsi_benchmark_digest"]["reason"] == "INPUT_DIGEST_MISSING"
    assert "no immutable benchmark digest" in missing["hsi_benchmark_digest"][
        "detail"
    ]["en"]
    assert all(
        "causal treatment" not in text.lower() for text in card["question"].values()
    )
    assert all(
        "causal treatment" not in text.lower() for text in card["estimand"].values()
    )

    effect_path = card["ordered_effect_path"]
    assert effect_path["owner_supplied"] is True
    assert effect_path["x_unit"] == "trading_day_relative_to_announcement"
    assert effect_path["y_unit"] == "cumulative_abnormal_return"
    assert effect_path["points"][0] == {"horizon": -10, "value": -0.02479, "n": 275}
    assert effect_path["points"][-1] == {"horizon": 60, "value": -0.08366, "n": 276}
    assert [point["horizon"] for point in effect_path["points"]] == sorted(
        point["horizon"] for point in effect_path["points"]
    )

    result_receipt = next(
        artifact
        for artifact in card["source_artifacts"]
        if artifact["role"] == "result"
    )
    assert result_receipt["sha256"] == (
        "f415b2c4cf9b12fbc8e4dd9e3a30a51c736c93f4ffbc3f818392b4796ea81139"
    )
    roster_receipt = next(
        artifact
        for artifact in card["source_artifacts"]
        if artifact["role"] == "event_roster"
    )
    assert roster_receipt["path"] == "data/hk_connect_roster/roster.parquet"
    assert roster_receipt["sha256"] == (
        "b0816afacd9537fac58c193f511ec919bccda4fc58a5921bd1096221fa35b148"
    )
    assert all(
        artifact["role"] != "benchmark"
        and artifact["path"] != "data/hk/_HSI.parquet"
        for artifact in card["source_artifacts"]
    )
    serialized = json.dumps(card, ensure_ascii=False, sort_keys=True)
    assert "data/hk/_HSI.parquet" not in serialized
    assert all(digest not in serialized for digest in MUTABLE_HSI_SNAPSHOT_DIGESTS)
    assert any(
        "historical HSI benchmark input" in limitation["en"]
        for limitation in card["limitations"]
    )
    _assert_closed_false_authority(card)


def test_mutable_hsi_worktree_snapshot_cannot_change_or_prove_historical_card(
    tmp_path: Path,
) -> None:
    _copy_inputs(ROOT, tmp_path, HINCL2_INPUTS)
    benchmark = tmp_path / "data/hk/_HSI.parquet"
    benchmark.parent.mkdir(parents=True, exist_ok=True)

    benchmark.write_bytes((ROOT / "data/hk/_HSI.parquet").read_bytes())
    card_with_old_snapshot = adapt_hincl2_event_study(tmp_path)

    benchmark.write_bytes(b"a later mutable HSI collection snapshot\n")
    card_with_later_snapshot = adapt_hincl2_event_study(tmp_path)

    benchmark.unlink()
    card_without_snapshot = adapt_hincl2_event_study(tmp_path)

    def canonical(card: dict) -> str:
        return json.dumps(
            card,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    assert canonical(card_with_old_snapshot) == canonical(card_with_later_snapshot)
    assert canonical(card_with_later_snapshot) == canonical(card_without_snapshot)


def test_real_card_localized_contract_text_has_actual_chinese_copy() -> None:
    localized_values: list[dict[str, str]] = []
    for card in (adapt_synthetic_control(ROOT), adapt_hincl2_event_study(ROOT)):
        localized_values.extend(
            [card["question"], card["estimand"], *card["limitations"]]
        )
        for collection in (
            "outputs",
            "uncertainty",
            "diagnostics",
            "placebos_or_counterexamples",
        ):
            for item in card[collection]:
                localized_values.append(item["label"])
                if "detail" in item:
                    localized_values.append(item["detail"])
        for collection in ("exclusions", "missingness", "null_reasons"):
            localized_values.extend(item["detail"] for item in card[collection])

    assert localized_values
    for value in localized_values:
        assert value["en"].strip()
        assert re.search(r"[\u4e00-\u9fff]", value["zh"]), value


def test_replay_is_deterministic_and_byte_equivalent() -> None:
    first = [adapt_synthetic_control(ROOT), adapt_hincl2_event_study(ROOT)]
    second = [adapt_synthetic_control(ROOT), adapt_hincl2_event_study(ROOT)]

    first_bytes = json.dumps(
        first, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    second_bytes = json.dumps(
        second, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert first_bytes == second_bytes


def test_result_digest_participates_in_card_identity() -> None:
    card = adapt_synthetic_control(ROOT)
    result = next(item for item in card["source_artifacts"] if item["role"] == "result")

    mutated_id = compute_card_id(
        adapter_version=card["adapter_version"],
        method_family=card["method_family"],
        study_run_id=card["study_run_id"],
        result_artifact_path=result["path"],
        verified_result_artifact_sha256="0" * 64,
        selected_result_id=card["selected_result_id"],
    )
    assert mutated_id != card["card_id"]


def test_adapter_refuses_in_place_result_mutation(tmp_path: Path) -> None:
    _copy_inputs(ROOT, tmp_path, SC_INPUTS)
    result_path = tmp_path / "data/experiments/synthetic_control_phase0_results.json"
    result_path.write_bytes(result_path.read_bytes() + b"\n")

    with pytest.raises(CardContractError, match="artifact digest mismatch"):
        adapt_synthetic_control(tmp_path)


def test_selected_result_drift_never_falls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _copy_inputs(ROOT, tmp_path, SC_INPUTS)
    result_path = tmp_path / "data/experiments/synthetic_control_phase0_results.json"
    artifact = json.loads(result_path.read_text(encoding="utf-8"))
    del artifact["families"]["sp_pure_adds"]["arms"]["sc_nnls"]["real"]["0_5"]
    result_path.write_text(json.dumps(artifact), encoding="utf-8")
    monkeypatch.setattr(ric, "_SC_RESULT_SHA256", sha256_file(result_path))

    with pytest.raises(CardContractError, match="frozen synthetic-control result"):
        adapt_synthetic_control(tmp_path)


def test_missing_statistic_never_becomes_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _copy_inputs(ROOT, tmp_path, SC_INPUTS)
    result_path = tmp_path / "data/experiments/synthetic_control_phase0_results.json"
    artifact = json.loads(result_path.read_text(encoding="utf-8"))
    del artifact["families"]["sp_pure_adds"]["arms"]["sc_nnls"]["real"]["0_5"]["t"]
    result_path.write_text(json.dumps(artifact), encoding="utf-8")
    monkeypatch.setattr(ric, "_SC_RESULT_SHA256", sha256_file(result_path))

    with pytest.raises(CardContractError, match="frozen synthetic-control result"):
        adapt_synthetic_control(tmp_path)


def test_failed_required_diagnostic_cannot_be_upgraded_to_complete() -> None:
    card = adapt_synthetic_control(ROOT)
    card["quality"] = "COMPLETE"

    with pytest.raises(CardContractError, match="failed diagnostic"):
        validate_card(card)


def test_missing_input_receipts_force_artifact_incomplete() -> None:
    card = adapt_hincl2_event_study(ROOT)
    card["quality"] = "COMPLETE"

    with pytest.raises(CardContractError, match="missingness"):
        validate_card(card)


def test_true_or_extra_authority_is_rejected() -> None:
    true_authority = adapt_synthetic_control(ROOT)
    true_authority["authority"]["trading_authority"] = True
    with pytest.raises(CardContractError, match="all authority flags"):
        validate_card(true_authority)

    extra_authority = adapt_synthetic_control(ROOT)
    extra_authority["authority"]["promotion_authority"] = False
    with pytest.raises(CardContractError, match="authority keys are not closed"):
        validate_card(extra_authority)


def test_extra_or_prohibited_top_level_field_is_rejected() -> None:
    card = adapt_synthetic_control(ROOT)
    card["rank"] = 1

    with pytest.raises(CardContractError, match="prohibited"):
        validate_card(card)


def test_ordered_effect_path_requires_unique_increasing_owner_horizons() -> None:
    card = adapt_hincl2_event_study(ROOT)
    duplicate = deepcopy(card["ordered_effect_path"]["points"][0])
    card["ordered_effect_path"]["points"].append(duplicate)

    with pytest.raises(CardContractError, match="unique and increasing"):
        validate_card(card)


def test_return_fraction_interval_requires_three_ordered_quantiles() -> None:
    card = adapt_hincl2_event_study(ROOT)
    interval = _coded(card["uncertainty"], "mean_ci90")

    interval["value"] = [-0.18, -0.08]
    with pytest.raises(CardContractError, match="three ordered quantiles"):
        validate_card(card)

    interval["value"] = [-0.18, -0.01, -0.08]
    with pytest.raises(CardContractError, match="three ordered quantiles"):
        validate_card(card)


def test_null_source_as_of_requires_a_typed_reason() -> None:
    card = adapt_hincl2_event_study(ROOT)
    roster = next(
        source
        for source in card["source_artifacts"]
        if source["role"] == "event_roster"
    )
    assert roster["as_of"] is None
    assert roster["as_of_reason"]["en"]
    assert roster["as_of_reason"]["zh"]

    roster["as_of_reason"] = None
    with pytest.raises(CardContractError, match="null as_of requires"):
        validate_card(card)


def test_counterexample_receipts_preserve_resolution_and_split_magnitudes() -> None:
    synthetic = adapt_synthetic_control(ROOT)
    event = adapt_hincl2_event_study(ROOT)

    assert _coded(synthetic["placebos_or_counterexamples"], "empirical_p_floor")[
        "value"
    ] == pytest.approx(0.004975124378109453)
    assert (
        _coded(event["placebos_or_counterexamples"], "split_half_first_mean")["value"]
        == -0.00785
    )
    assert (
        _coded(event["placebos_or_counterexamples"], "split_half_second_mean")["value"]
        == -0.16839
    )


def test_fixed_adapter_order_is_not_metric_ranking() -> None:
    envelope = getattr(ric, "build_research_implication_cards")(ROOT)

    assert envelope["schema"] == ric.ENVELOPE_SCHEMA
    assert [card["method_family"] for card in envelope["cards"]] == [
        "synthetic_control",
        "event_study",
        "local_projections",
    ]
    assert (
        envelope["cards"][0]["outputs"][0]["value"]
        > envelope["cards"][1]["outputs"][0]["value"]
    )


def test_measurement_builder_writes_same_contract_machine_projection(
    tmp_path: Path,
) -> None:
    from scripts import build_measurement as measurement

    envelope = ric.build_research_implication_cards(ROOT)
    output_path = tmp_path / "measurementdata" / "research_implication_cards.json"
    getattr(measurement, "write_research_implication_projection")(envelope, output_path)

    projected = json.loads(output_path.read_text(encoding="utf-8"))
    js_payload = json.loads(
        re.search(
            r"window\.MEASUREMENT=(.+);$",
            measurement.emit_js({"research_implications": envelope}),
            re.DOTALL | re.MULTILINE,
        ).group(1)
    )
    assert projected == envelope
    assert js_payload["research_implications"] == projected
    assert [card["card_id"] for card in projected["cards"]] == [
        card["card_id"] for card in js_payload["research_implications"]["cards"]
    ]


# F10 native local projections: retained producer input, complete preregistration,
# no estimator execution in the read-only product adapter or its tests.
def _lp_inputs(destination: Path) -> Path:
    from engine import local_projection_research_card as lpc
    _copy_inputs(ROOT, destination, tuple(lpc.PINS) + ("data/trial_ledger.jsonl",))
    return destination


def test_native_lp_card_preserves_source_gap_search_n_and_zero_authority():
    from engine import local_projection_research_card as lpc
    before = (ROOT / "data/trial_ledger.jsonl").read_bytes()
    card = lpc.adapt_local_projections(ROOT)
    assert card["method_family"] == "local_projections"
    assert card["quality"] == "ARTIFACT_INCOMPLETE"
    assert card["sample_n"] == 332 and card["effective_n"] is None
    assert _coded(card["null_reasons"], "effective_n")["reason"] == "INDEPENDENT_EPISODES_NOT_IDENTIFIED"
    assert _coded(card["diagnostics"], "registered_search_n")["value"] == 3
    assert _coded(card["exclusions"], "recent_unavailable_months")["count"] == 13
    assert "2025" in _coded(card["missingness"], "requested_recent_source_window")["detail"]["en"]
    robustness_codes = {x["code"] for x in card["placebos_or_counterexamples"]} | {x["code"] for x in card["null_reasons"]}
    assert {"robustness_lags_2_h3", "robustness_lags_8_h3"} <= robustness_codes
    assert all(metric["unit"] == "log_payroll_change_per_cpi_percentage_point" for metric in card["outputs"])
    assert any(s["role"] == "preregistration" for s in card["source_artifacts"])
    assert any(s["role"] == "original_source_refusal" for s in card["source_artifacts"])
    _assert_closed_false_authority(card)
    assert (ROOT / "data/trial_ledger.jsonl").read_bytes() == before


@pytest.mark.parametrize("artifact_role", ["result", "preregistration", "input", "registration", "custody"])
def test_lp_artifact_tamper_cannot_be_displayed(tmp_path, artifact_role):
    from engine import local_projection_research_card as lpc
    root = _lp_inputs(tmp_path)
    relative = next(path for path, (role, _) in lpc.PINS.items() if role == artifact_role)
    with (root / relative).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(CardContractError, match="digest mismatch"):
        lpc.adapt_local_projections(root)


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra_configuration", "timestamp", "cutoff"])
def test_lp_live_ledger_requires_exact_original_family(tmp_path, change):
    from engine import local_projection_research_card as lpc
    from engine.trial_ledger import _hash
    root = _lp_inputs(tmp_path)
    ledger = root / "data/trial_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_bytes().splitlines()]
    owned = [r for r in rows if r.get("family") == lpc.FAMILY]
    assert len(owned) == 3
    other = [r for r in rows if r.get("family") != lpc.FAMILY]
    if change == "missing":
        owned.pop()
    elif change == "duplicate":
        owned.append(deepcopy(owned[0]))
    elif change == "extra_configuration":
        extra = deepcopy(owned[0]); extra["config"]["lags"] = 6
        extra["config_hash"] = _hash(lpc.FAMILY, extra["config"]); owned.append(extra)
    elif change == "timestamp":
        owned[0]["ts"] = "2000-01-01T00:00:00+00:00"
    elif change == "cutoff":
        owned[0]["info_cutoff"] = "2026-10-18T00:00:00+00:00"
    ledger.write_text("".join(json.dumps(r) + "\n" for r in other + owned))
    with pytest.raises(CardContractError, match="registration"):
        lpc.adapt_local_projections(root)


def test_lp_other_family_appends_do_not_invalidate_original_registration(tmp_path):
    from engine import local_projection_research_card as lpc
    from engine.trial_ledger import _hash
    root = _lp_inputs(tmp_path)
    row = json.loads((root / lpc.REGISTRATION).read_text())["new_rows"][0]
    row["family"] = "fixture_unrelated_study"
    row["config_hash"] = _hash(row["family"], row["config"])
    with (root / "data/trial_ledger.jsonl").open("a") as stream:
        stream.write(json.dumps(row) + "\n")
    assert lpc.adapt_local_projections(root) == lpc.adapt_local_projections(ROOT)


@pytest.mark.parametrize("change", ["authority", "missing_lag", "lag_order", "cutoff", "scientific_acceptance"])
def test_lp_owner_bundle_cannot_promote_or_select_specification(change):
    from engine import local_projection_research_card as lpc
    bundle = json.loads((ROOT / lpc.RESULT).read_text())
    spec = json.loads((ROOT / lpc.SPEC).read_text())
    reg = json.loads((ROOT / lpc.REGISTRATION).read_text())
    if change == "authority":
        bundle["authority"]["forecast"] = True
    elif change == "missing_lag":
        bundle["runs"].pop()
    elif change == "lag_order":
        bundle["runs"][1:] = reversed(bundle["runs"][1:])
    elif change == "cutoff":
        bundle["runs"][0]["envelope"]["registration"]["config"]["cutoff"] = "2026-10-18T00:00:00+00:00"
    elif change == "scientific_acceptance":
        bundle["scientific_acceptance"] = True
    with pytest.raises(CardContractError):
        lpc._verify_owner_bundle(bundle, spec, reg)


def test_lp_native_abstention_remains_null_without_invented_curve(tmp_path, monkeypatch):
    from engine import local_projection_research_card as lpc
    root = _lp_inputs(tmp_path)
    path = root / lpc.RESULT
    bundle = json.loads(path.read_text())
    bundle["runs"][0]["envelope"]["result"]["irf"][1] = {
        "schema": "local_projections.abstention/v1", "h": 1,
        "abstained": True, "reason": "insufficient_observations", "n": 12}
    path.write_text(json.dumps(bundle))
    pins = dict(lpc.PINS); pins[lpc.RESULT] = ("result", sha256_file(path))
    monkeypatch.setattr(lpc, "PINS", pins)
    card = lpc.adapt_local_projections(root)
    assert _coded(card["null_reasons"], "horizon_1")["reason"] == "insufficient_observations"
    assert "beta_h1" not in {metric["code"] for metric in card["outputs"]}
    assert card["ordered_effect_path"] is None
    assert card["quality"] == "ARTIFACT_INCOMPLETE"


# Fabric-returned pure-registration guards, exercised against the real native module.
import copy as _lp_reg_copy
from engine.trial_ledger import _hash as _lp_reg_hash
from engine.local_projection_research_card import verify_registration as _lp_verify_registration




_LP_REG_FAMILY = "card-2026-demo"
_LP_REG_CUTOFF = "2024-06-30"
_LP_REG_BOUND = 64 * 1024 * 1024

_LP_REG_CONFIGS = [
    {"arm": "control", "cutoff": _LP_REG_CUTOFF, "n": 40},
    {"arm": "low", "cutoff": _LP_REG_CUTOFF, "n": 40},
    {"arm": "high", "cutoff": _LP_REG_CUTOFF, "n": 40},
]
_LP_REG_TIMESTAMPS = ["2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z", "2026-10-03T00:00:00Z"]

_LP_REG_LEGACY_REGISTRY_RECORD = {
    "trial_id": "T-0001", "ts": "2019-01-01T00:00:00Z", "n": 10, "status": "filed",
    "hypothesis": "h", "verdict_criteria": "v", "earliest_verdict": "2019-02-01",
    "fdr_family": "f",
}  # names no family: tolerated as an older legacy JSON record


def _lp_reg_generated_row(config, ts, *, source="card:demo", note=None):
    return {
        "ts": ts,
        "family": _LP_REG_FAMILY,
        "config_hash": _lp_reg_hash(_LP_REG_FAMILY, config),
        "config": config,
        "source": source,
        "info_cutoff": config["cutoff"],
        "note": note,
    }


def _lp_reg_base_rows():
    return [_lp_reg_generated_row(config, ts) for config, ts in zip(_LP_REG_CONFIGS, _LP_REG_TIMESTAMPS)]


def _lp_reg_receipt_for(rows, **over):
    receipt = {"family": _LP_REG_FAMILY, "effective_n": 3, "new_rows": rows,
               "content_digest": "pinned-by-caller"}
    receipt.update(over)
    return receipt


def _lp_reg_ledger_bytes(*records, final_newline=True):
    body = "\n".join(r if isinstance(r, str) else json.dumps(r) for r in records)
    if final_newline:
        body += "\n"
    return body.encode("utf-8")


def _lp_reg_other_row(**over):
    row = {"ts": "2026-09-01T00:00:00Z", "family": "other-study",
           "config_hash": "0123456789abcdef", "config": {"arm": "x"},
           "source": "other", "info_cutoff": "2024-01-01", "note": None}
    row.update(over)
    return row


def _lp_reg_other_budget(**over):
    row = {"ts": "2026-09-01T00:00:00Z", "family": "other-study",
           "kind": "declared_budget", "n": 5, "reason": None,
           "config_hash": "0123456789abcdef"}
    row.update(over)
    return row


def _lp_reg_other_annotation(**over):
    row = {"family": "other-study", "kind": "filing_budget", "ts": "2026-09-01T00:00:00Z"}
    row.update(over)
    return row


def _lp_reg_verify(rows, raw, *, configs=None, family=_LP_REG_FAMILY, receipt=None):
    if receipt is None:
        receipt = _lp_reg_receipt_for(rows)
    if configs is None:
        configs = _LP_REG_CONFIGS
    return _lp_verify_registration(receipt, raw, family=family, configs=configs)




def test_lp_registration_happy_path_returns_defensive_copy():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(_LP_REG_LEGACY_REGISTRY_RECORD, *rows)
    result = _lp_reg_verify(rows, raw)
    assert result == rows
    assert result is not rows and all(a is not b for a, b in zip(result, rows))
    result[0]["note"] = "mutated"
    result[0]["ts"] = "1999-01-01T00:00:00Z"
    assert rows[0]["note"] is None and rows[0]["ts"] == _LP_REG_TIMESTAMPS[0]


def test_lp_registration_unrelated_appends_and_legacy_records_are_allowed():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(
        _LP_REG_LEGACY_REGISTRY_RECORD,
        _lp_reg_other_row(),                                   # other family, generated trial
        _lp_reg_other_budget(),                                # other family, declared budget
        _lp_reg_other_annotation(),                            # other family, filing_budget
        rows[0], _lp_reg_other_row(), rows[1], rows[2],
        {"family": "other-study", "kind": "amendment", "ts": "2026-09-02T00:00:00Z"},
    )
    assert _lp_reg_verify(rows, raw) == rows


def test_lp_registration_ledger_row_order_is_irrelevant():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(rows[2], rows[0], rows[1])
    assert _lp_reg_verify(rows, raw) == rows


def test_lp_registration_missing_row_rejected():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(rows[0], rows[2])
    with pytest.raises(ValueError, match="holds only 2 rows"):
        _lp_reg_verify(rows, raw)


def test_lp_registration_extra_same_family_row_rejected():
    rows = _lp_reg_base_rows()
    extra = _lp_reg_generated_row({"arm": "probe", "cutoff": _LP_REG_CUTOFF, "n": 40},
                          "2026-10-04T00:00:00Z")
    with pytest.raises(ValueError, match="extra same-family row"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows, extra))


def test_lp_registration_duplicate_same_family_row_rejected():
    rows = _lp_reg_base_rows()
    with pytest.raises(ValueError, match="duplicate same-family config hash"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows, rows[1]))


def test_lp_registration_tampered_timestamp_rejected():
    rows = _lp_reg_base_rows()
    live = dict(rows[0], ts="2026-10-01T12:00:00Z")
    with pytest.raises(ValueError, match="differs from its immutable receipt row"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(live, rows[1], rows[2]))


def test_lp_registration_tampered_source_rejected():
    rows = _lp_reg_base_rows()
    live = dict(rows[1], source="card:demo-tampered")
    with pytest.raises(ValueError, match="differs from its immutable receipt row"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(rows[0], live, rows[2]))


def test_lp_registration_null_note_is_data_and_tamper_is_refused():
    rows = _lp_reg_base_rows()  # every note is None: null-as-data must survive the round trip
    assert all(row["note"] is None for row in _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows)))
    live = dict(rows[2], note="quietly filled in")
    with pytest.raises(ValueError, match="differs from its immutable receipt row"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(rows[0], rows[1], live))


def test_lp_registration_numeric_type_swap_is_not_unchanged():
    config = {"arm": "control", "cutoff": 3, "n": 40}
    configs = [config, _LP_REG_CONFIGS[1], _LP_REG_CONFIGS[2]]
    rows = [_lp_reg_generated_row(config, _LP_REG_TIMESTAMPS[0]), *_lp_reg_base_rows()[1:]]
    live = dict(rows[0], info_cutoff=3.0)  # 3 == 3.0 in Python, not in the ledger bytes
    with pytest.raises(ValueError, match="differs from its immutable receipt row"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(live, *rows[1:]), configs=configs)


def test_lp_registration_bool_is_not_int_in_live_row():
    config = {"arm": "control", "cutoff": 1, "n": 40}
    configs = [config, _LP_REG_CONFIGS[1], _LP_REG_CONFIGS[2]]
    rows = [_lp_reg_generated_row(config, _LP_REG_TIMESTAMPS[0]), *_lp_reg_base_rows()[1:]]
    live = dict(rows[0], info_cutoff=True)
    with pytest.raises(ValueError, match="differs from its immutable receipt row"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(live, *rows[1:]), configs=configs)


def test_lp_registration_changed_cutoff_in_receipt_row_rejected():
    rows = _lp_reg_base_rows()
    drifting = dict(rows[0], info_cutoff="2024-07-31")
    with pytest.raises(ValueError, match="info_cutoff does not equal"):
        _lp_reg_verify([drifting, rows[1], rows[2]], _lp_reg_ledger_bytes(*rows))


def test_lp_registration_changed_cutoff_in_config_rejected():
    rows = _lp_reg_base_rows()
    drifted = [dict(_LP_REG_CONFIGS[0], cutoff="2025-01-01"), _LP_REG_CONFIGS[1], _LP_REG_CONFIGS[2]]
    with pytest.raises(ValueError, match="does not correspond to configs\\[0\\]"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows), configs=drifted)


def test_lp_registration_family_mismatch_rejected():
    rows = _lp_reg_base_rows()
    with pytest.raises(ValueError, match="receipt family does not equal"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows), family="card-2026-other")
    foreign = [dict(row, family="card-2026-other") for row in rows]
    foreign[0]["config_hash"] = _lp_reg_hash("card-2026-other", foreign[0]["config"])
    with pytest.raises(ValueError, match="does not name family"):
        _lp_reg_verify(foreign, _lp_reg_ledger_bytes(*rows))


def test_lp_registration_effective_n_must_be_literal_integer_three():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(*rows)
    for bad in (True, "3", 3.0, 4, 2, None):
        with pytest.raises(ValueError, match="effective_n"):
            _lp_reg_verify(rows, raw, receipt=_lp_reg_receipt_for(rows, effective_n=bad))


def test_lp_registration_configs_law():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(*rows)
    with pytest.raises(ValueError, match="exactly three configs"):
        _lp_reg_verify(rows, raw, configs=_LP_REG_CONFIGS[:2])
    with pytest.raises(ValueError, match="distinct trial configurations"):
        _lp_reg_verify(rows, raw, configs=[_LP_REG_CONFIGS[0], _LP_REG_CONFIGS[0], _LP_REG_CONFIGS[2]])
    missing_cutoff = [dict(_LP_REG_CONFIGS[0]), _LP_REG_CONFIGS[1], _LP_REG_CONFIGS[2]]
    del missing_cutoff[0]["cutoff"]
    with pytest.raises(ValueError, match="must carry the source 'cutoff' field"):
        _lp_reg_verify(rows, raw, configs=missing_cutoff)
    with pytest.raises(ValueError, match="configs\\[0\\] must be a dict"):
        _lp_reg_verify(rows, raw, configs=["control", _LP_REG_CONFIGS[1], _LP_REG_CONFIGS[2]])


def test_lp_registration_declared_budget_in_family_rejected_in_ledger():
    rows = _lp_reg_base_rows()
    budget = _lp_reg_other_budget(family=_LP_REG_FAMILY,
                          config_hash=_lp_reg_hash(_LP_REG_FAMILY, {"__declared_budget__": 2,
                                                     "reason": None}))
    with pytest.raises(ValueError, match="declared budget row for family"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows, budget))


def test_lp_registration_declared_budget_in_receipt_rejected():
    rows = _lp_reg_base_rows()
    budget = {"ts": _LP_REG_TIMESTAMPS[0], "family": _LP_REG_FAMILY, "kind": "declared_budget",
              "n": 2, "reason": None, "config_hash": rows[0]["config_hash"]}
    with pytest.raises(ValueError, match="declared budget row"):
        _lp_reg_verify([budget, rows[1], rows[2]], _lp_reg_ledger_bytes(*rows))


def test_lp_registration_legacy_annotation_in_family_rejected():
    rows = _lp_reg_base_rows()
    annotation = _lp_reg_other_annotation(family=_LP_REG_FAMILY)  # filing_budget naming our family
    with pytest.raises(ValueError, match="legacy annotation for family"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows, annotation))


def test_lp_registration_invalid_utf8_rejected():
    rows = _lp_reg_base_rows()
    with pytest.raises(ValueError, match="not valid UTF-8"):
        _lp_reg_verify(rows, b"\xff\xfe" + _lp_reg_ledger_bytes(*rows))


def test_lp_registration_oversized_ledger_rejected():
    with pytest.raises(ValueError, match="64 MiB"):
        _lp_reg_verify(_lp_reg_base_rows(), b"x" * (_LP_REG_BOUND + 1))


def test_lp_registration_exact_64mib_boundary_is_allowed():
    rows = _lp_reg_base_rows()
    ours = "\n".join(json.dumps(row) for row in rows)
    pad_prefix = json.dumps({"family": "padding-family", "pad": ""})
    deficit = _LP_REG_BOUND - (len(ours.encode("utf-8")) + 1 + len(pad_prefix.encode("utf-8")) + 1)
    assert deficit >= 2
    padded = json.dumps({"family": "padding-family", "pad": "p" * deficit})
    raw = (ours + "\n" + padded + "\n").encode("utf-8")
    assert len(raw) == _LP_REG_BOUND
    assert _lp_reg_verify(rows, raw) == rows
    with pytest.raises(ValueError, match="64 MiB"):
        _lp_reg_verify(rows, raw + b"x")


def test_lp_registration_blank_and_interior_rows_rejected():
    rows = _lp_reg_base_rows()
    with pytest.raises(ValueError, match="blank ledger row at line 2"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(rows[0], "", rows[1], rows[2], final_newline=False))
    with pytest.raises(ValueError, match="blank ledger row at line 4"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows) + b"\n")  # trailing blank line: empty fourth line
    whitespace = b"   \n" + _lp_reg_ledger_bytes(*rows)  # whitespace-only first line
    with pytest.raises(ValueError, match="blank ledger row at line 1"):
        _lp_reg_verify(rows, whitespace)


def test_lp_registration_missing_final_newline_is_tolerated():
    rows = _lp_reg_base_rows()
    assert _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows, final_newline=False)) == rows


def test_lp_registration_duplicate_json_key_refused_globally():
    rows = _lp_reg_base_rows()
    poison = '{"family": "other-study", "family": "other-study-2"}'
    with pytest.raises(ValueError, match="duplicate JSON key"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(poison, *rows))


def test_lp_registration_nonfinite_constant_refused_globally():
    rows = _lp_reg_base_rows()
    poison = '{"family": "other-study", "score": NaN}'
    with pytest.raises(ValueError, match="non-finite JSON constant"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(poison, *rows))


def test_lp_registration_truncated_json_rejected():
    rows = _lp_reg_base_rows()
    torn = _lp_reg_ledger_bytes(*rows, final_newline=False)[:-8]  # cut mid final record
    with pytest.raises(ValueError, match="malformed ledger JSON at line 3"):
        _lp_reg_verify(rows, torn)


def test_lp_registration_non_object_record_rejected():
    rows = _lp_reg_base_rows()
    for poison in ("42", "[1, 2]", "null"):
        with pytest.raises(ValueError, match="not a JSON object"):
            _lp_reg_verify(rows, _lp_reg_ledger_bytes(poison, *rows))


def test_lp_registration_receipt_row_law_violations():
    rows = _lp_reg_base_rows()
    raw = _lp_reg_ledger_bytes(*rows)
    bad_hash = [dict(rows[0], config_hash="0" * 16), rows[1], rows[2]]
    with pytest.raises(ValueError, match="fails native strict row law"):
        _lp_reg_verify(bad_hash, raw)
    missing_key = [{k: v for k, v in rows[0].items() if k != "source"}, rows[1], rows[2]]
    with pytest.raises(ValueError, match="fails native strict row law"):
        _lp_reg_verify(missing_key, raw)
    extra_key = [dict(rows[0], verdict="pass"), rows[1], rows[2]]
    with pytest.raises(ValueError, match="fails native strict row law"):
        _lp_reg_verify(extra_key, raw)


def test_lp_registration_receipt_row_order_must_follow_configs():
    rows = _lp_reg_base_rows()
    shuffled = [rows[1], rows[0], rows[2]]
    with pytest.raises(ValueError, match="does not correspond to configs\\[0\\]"):
        _lp_reg_verify(shuffled, _lp_reg_ledger_bytes(*rows))


def test_lp_registration_inputs_are_never_mutated():
    rows = _lp_reg_base_rows()
    receipt = _lp_reg_receipt_for(rows)
    configs = _lp_reg_copy.deepcopy(_LP_REG_CONFIGS)
    snapshot = (_lp_reg_copy.deepcopy(receipt), _lp_reg_copy.deepcopy(configs))
    result = _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows), configs=configs, receipt=receipt)
    assert result == rows
    assert (receipt, configs) == snapshot


def test_lp_registration_exact_family_only_no_reset_hiding():
    rows = _lp_reg_base_rows()
    # A renamed/reset family can never substitute for ours...
    reset_rows = [dict(row, family=_LP_REG_FAMILY + "-reset") for row in rows]
    reset_rows = [dict(row, config_hash=_lp_reg_hash(row["family"], row["config"]))
                  for row in reset_rows]
    with pytest.raises(ValueError, match="holds only 0 rows"):
        _lp_reg_verify(rows, _lp_reg_ledger_bytes(*reset_rows))
    # ...and rows parked under a reset family stay unrelated appends.
    assert _lp_reg_verify(rows, _lp_reg_ledger_bytes(*rows, *reset_rows)) == rows
