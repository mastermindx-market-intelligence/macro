"""Synthetic native-source proof; private training-owner stand-in is explicit.

Positive fit tests stand in ONLY for the still-missing real selected registration
and source/split provenance. They exercise genuine sealed native captures and
current rights, not production admission. Fixed public owner tests remain denied.
"""
import copy
from decimal import localcontext, Inexact, Rounded, ROUND_DOWN
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import tempfile

import pytest

from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.research_factory import market_memory_fitted_use as use
from engine.research_factory import market_memory_contextual_registration as control
from tests.test_market_memory_episode_retrieval import corpus
from tests.test_market_memory_retained_context_cohort import capture, owner, load, CUTOFF
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_e0_control_records import records, bundle, task_bundle
from tests.test_market_memory_e0_registered_method import inputs
from tests.test_market_memory_e0_selected_task_inputs import prepared_files
from tests.test_market_memory_e0_installed_control import selection, write
from tests.test_market_memory_e0_domains import temporal, source_checks, split_checks


@pytest.fixture
def native_training(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    value = cohort.disclose_retained_context_cohort(population, policy=Policy())
    caps = cohort.read_cohort_feature_capabilities(population, policy=Policy())
    candidates = {features.disclose_episode_features(c, policy=Policy())["capture_id"]: c
                  for c in caps if c is not None}
    tasks, coverage = [], []
    for number, stored in enumerate((a, b, q)):
        projected = features.disclose_episode_features(candidates[stored.capture_receipt["capture_id"]], policy=Policy())
        tasks.append({"task_id": "synthetic-task-" + str(number),
            "capture_id": projected["capture_id"], "context_id": projected["context_id"],
            "query_id": projected["owner"]["query_id"],
            "analysis_cutoff": max(projected["clocks"].values(), key=cohort.utc_instant)})
        coverage.append({"capture_id": projected["capture_id"], "context_id": projected["context_id"],
            "query_id": projected["owner"]["query_id"], "packet_sha256": projected["packet_sha256"],
            "receipt_sha256": projected["capture_receipt_sha256"], "source_receipt_ids": projected["source_receipt_ids"],
            "source_measurement_session": None,
            "first_available_for_contextual_analysis": tasks[-1]["analysis_cutoff"]})
    binding = {"binding_id": "synthetic-owner-window", "source_owner": {**value["owner"], "profile": features.trusted.TRUSTED_STORE_PROFILE},
        "training_start_inclusive": "2026-08-01T00:00:00Z", "fit_cutoff": CUTOFF,
        "eligible_use_from": CUTOFF, "mode": "historical_hypothetical"}
    report = use._training_audit_report(
        {"unresolved": ["frozen_owner_measurement_episode_or_span_provenance",
                        "declared_measurement_episode_feature_or_label_support"],
         "frozen_owner_metadata_unknown_counts": {"source_measurement_session": 3, "economic_episode_id": 3,
            "feature_support_interval": 3, "label_interval": 3},
         "unknown_declarations": {"source_measurement_session": 3, "economic_episode": 3,
            "feature_support_interval": 3, "label_support_interval": 3}},
        {"unresolved": ["declared_session_episode_and_full_support_spans"],
         "exact_task_bindings_checked": True, "declared_dispositions": {"unknown": 0}})
    body = cohort.canonical({"binding": binding, "tasks": tasks[:2], "coverage": coverage,
        "partition_tasks": [{**t, "disposition": "development" if i < 2 else "excluded"}
                            for i, t in enumerate(tasks)],
        "chronological_partition": {"boundaries": {"development_end_exclusive": CUTOFF,
            "tuning_end_exclusive": "2026-08-21T12:00:00Z", "test_start_inclusive": "2026-08-21T12:00:00Z"}, "embargo_seconds": 0},
        "training_audit_report": report})
    window = use.TrainingWindowCapability(body, b"synthetic-selected-owner", _key=use._TOKEN)
    # Explicit fixture owner, not an independent authentication/admission proof.
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: window)
    return population, query, window, a, b, q


def test_actual_sealed_source_fit_and_manifest_bound_exact_index(native_training):
    population, _, window, *_ = native_training
    cap = fitted.fit_registered_normalizer(window, population, policy=Policy())
    value = fitted.disclose_fitted_normalizer(cap, policy=Policy())
    assert len(value["training_manifest"]) == 2
    assert value["parameters"][0]["mean"] == fitted._ratio(Fraction.from_float(0.4) / 2)
    assert value["parameters"][0]["scale"] == fitted._ratio(Fraction.from_float(0.4))
    assert value["parameters"][1]["constant_training_coordinate"] is True
    assert value["parameters"][1]["scale"] == {"numerator": "1", "denominator": "1"}
    assert not value["external_foundation_model_training"]
    assert not value["operational_study_admission"]
    index = fitted.build_fitted_exact_index(cap, population, policy=Policy())
    assert index["normalizer_id"] == value["normalizer_id"]
    assert index["normalizer_sha256"] == sha256(cap._body).hexdigest()
    assert len(index["rows"]) == index["baseline_index"]["expected_capture_count"] == 3
    growth = sorted(row["normalized_coordinates"][0] for row in index["rows"])
    assert growth == ["-0.500000000000000000", "0.000000000000000000", "0.500000000000000000"]
    assert index == fitted.build_fitted_exact_index(cap, population, policy=Policy())


def test_future_store_append_never_refits_original_window(native_training, tmp_path, monkeypatch):
    population, _, window, *_ = native_training
    cap = fitted.fit_registered_normalizer(window, population, policy=Policy())
    before = fitted.disclose_fitted_normalizer(cap, policy=Policy())
    index = fitted.build_fitted_exact_index(cap, population, policy=Policy())
    capture(tmp_path, monkeypatch, session="2026-08-21", growth=-0.99)
    after = fitted.fit_registered_normalizer(window, population, policy=Policy())
    assert after._body == cap._body
    assert fitted.disclose_fitted_normalizer(after, policy=Policy())["parameters"] == before["parameters"]
    assert fitted.build_fitted_exact_index(cap, population, policy=Policy()) == index


def test_held_out_query_value_does_not_enter_training_parameters(native_training):
    population, query, window, a, b, q = native_training
    cap = fitted.fit_registered_normalizer(window, population, policy=Policy())
    value = fitted.disclose_fitted_normalizer(cap, policy=Policy())
    assert q.capture_receipt["capture_id"] not in {r["capture_id"] for r in value["training_manifest"]}
    assert features.disclose_episode_features(query, policy=Policy())["source_usage_admission"]["fit_eligible"] is False
    assert features.fixed_comparison_descriptor()["fit_status"] == "not_performed"


def test_hostile_decimal_context_does_not_change_fit_or_index(native_training):
    population, _, window, *_ = native_training
    before = fitted.fit_registered_normalizer(window, population, policy=Policy())
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_DOWN
        context.traps[Inexact] = context.traps[Rounded] = True
        state = repr(context)
        after = fitted.fit_registered_normalizer(window, population, policy=Policy())
        assert after._body == before._body
        newer = fitted.build_fitted_exact_index(after, population, policy=Policy())
        older = fitted.build_fitted_exact_index(before, population, policy=Policy())
        assert newer["index_id"] == older["index_id"]
        assert newer["rows"] == older["rows"]
        assert repr(context) == state


@pytest.mark.parametrize("change", ["future", "owner", "task", "missing", "duplicate"])
def test_window_and_native_source_disagreement_fails(native_training, monkeypatch, change):
    population, _, original, *_ = native_training
    body = json.loads(original._body)
    if change == "future": body["tasks"][0]["analysis_cutoff"] = "2026-08-09T00:00:00Z"
    if change == "owner": body["binding"]["source_owner"]["generation_sha256"] = "f" * 64
    if change == "task": body["tasks"][0]["context_id"] = "mmctx_" + "f" * 64
    if change == "missing": body["tasks"][0]["capture_id"] = "mmcapture_" + "f" * 64
    if change == "duplicate": body["tasks"][1] = copy.deepcopy(body["tasks"][0])
    altered = use.TrainingWindowCapability(cohort.canonical(body), original._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: altered)
    with pytest.raises(fitted.FittedNormalizationError):
        fitted.fit_registered_normalizer(altered, population, policy=Policy())


@pytest.mark.parametrize("action", ["verify_retained_macro_retention", "disclose_retained_macro_feature",
    "compare_retained_macro_feature"])
def test_current_rights_apply_to_fit_and_reuse(native_training, action):
    population, _, window, *_ = native_training
    cap = fitted.fit_registered_normalizer(window, population, policy=Policy())
    with pytest.raises((cohort.RetainedContextAccessError, features.EpisodeFeatureAccessError)):
        fitted.disclose_fitted_normalizer(cap, policy=Policy({action}))


def test_owner_selection_change_revokes_frozen_fit(native_training, monkeypatch):
    population, _, window, *_ = native_training
    cap = fitted.fit_registered_normalizer(window, population, policy=Policy())
    changed = use.TrainingWindowCapability(window._body, b"different-selected-control", _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: changed)
    with pytest.raises(use.FittedUseError, match="window_changed"):
        fitted.disclose_fitted_normalizer(cap, policy=Policy())


def test_no_caller_dictionary_can_grant_training_or_construct_fit(native_training):
    population, _, window, *_ = native_training
    with pytest.raises(use.FittedUseError, match="authenticated_training"):
        fitted.fit_registered_normalizer(json.loads(window._body), population, policy=Policy())
    with pytest.raises(use.FittedUseError): use.TrainingWindowCapability(b"{}", b"grant")
    with pytest.raises(fitted.FittedNormalizationError):
        fitted.FittedNormalizerCapability(b"{}", window, population, ())


def test_public_owner_is_fixed_and_shipped_purpose_is_dormant():
    assert "engine/neuralweb/market_memory_exact_index.py" in use._SOURCE_PATHS
    if not (use.sys.platform == "linux" and use.os.geteuid() == 0 and
            Path(use.__file__).resolve() == use.owner.INSTALLED_ROOT / use._MODULE_PATH):
        with pytest.raises(use.FittedUseError, match="installed_training_administrator"):
            use.prepare_registered_training_window()
    purpose = json.loads((Path(__file__).resolve().parents[1] / use.PURPOSE_PATH).read_bytes())
    assert purpose["enabled"] is False
    assert purpose["selected_study_id"] is purpose["binding_ref"] is None
    assert purpose["external_foundation_model_training"] is purpose["prophet_training"] is False


def test_existing_authority_is_reused_without_activating_new_record():
    source = Path(__file__).resolve().parents[1]
    # The removable-volume ancestor intentionally fails the deployed owner's
    # filesystem policy. Exercise the parser on real private owned fixture dirs.
    with tempfile.TemporaryDirectory(dir=Path.home(), prefix=".mm-fit-purpose-") as name:
        root = Path(name)
        for relative in (use.PURPOSE_PATH, use.BASELINE_PURPOSE_PATH, use.AUTHORITY_RECORD):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes((source / relative).read_bytes())
            target.chmod(0o600)
        with pytest.raises(use.FittedUseError, match="not_active"):
            use._purpose(root)


def test_original_fixed_p1_source_is_still_registered():
    assert sha256(Path(features.__file__).read_bytes()).hexdigest() == "c80ba0a39e42b62e3bd687301fdc974d18f935b584b7f0b462b753ccf044530a"


def _binding(registration):
    value = {"schema": use.SCHEMA, "binding_id": "synthetic-fit-binding",
        "registration_ref": control._record_ref(registration, "registration"),
        "source_owner": {k: registration["corpus"][k] for k in
            ("profile", "store_id", "generation_id", "generation_sha256", "membership_sha256")},
        "purpose": use.PURPOSE, "normalization_method": use.METHOD, "mode": "historical_hypothetical",
        "training_start_inclusive": "2026-08-01T00:00:00.000000Z", "fit_cutoff": "2026-09-01T00:00:00.000000Z",
        "eligible_use_from": "2026-09-02T00:00:00.000000Z", "training_task_ids": ["synthetic-a", "synthetic-b"],
        "source_coverage_ref": registration["source_coverage_ref"],
        "interval_split_ref": registration["interval_split_ref"]}
    body = cohort.canonical(value)
    ref = {"schema": use.SCHEMA, "object_id": value["binding_id"],
        "sha256": sha256(body).hexdigest(), "bytes": len(body)}
    return value, body, ref


def test_versioned_binding_uses_exact_registered_bytes_without_changing_v1(records):
    value, body, ref = _binding(records["registration"])
    assert use._binding(body, records["registration"], ref) == value
    assert "normalization_parameter_estimation_for_customer_comparisons" not in control._validator("installed_binding").schema["properties"]["permitted_actions"]["items"]["enum"]


@pytest.mark.parametrize("change", ["clock", "purpose", "method", "duplicate", "float_bytes", "extra"])
def test_versioned_binding_rejects_inconsistent_or_widened_inputs(records, change):
    value, body, ref = _binding(records["registration"])
    if change == "clock": value["fit_cutoff"] = value["training_start_inclusive"]
    if change == "purpose": value["purpose"] = "external_foundation_model_training"
    if change == "method": value["normalization_method"] = "learned_distance_weights"
    if change == "duplicate": value["training_task_ids"] *= 2
    if change == "float_bytes": value["source_coverage_ref"]["bytes"] = 1.0
    if change == "extra": value["grant"] = True
    body = cohort.canonical(value)
    ref.update(bytes=len(body), sha256=sha256(body).hexdigest())
    with pytest.raises(use.FittedUseError): use._binding(body, records["registration"], ref)


def test_byte_reference_mismatch_is_not_a_different_training_binding(records):
    value, body, ref = _binding(records["registration"])
    ref["sha256"] = "f" * 64
    with pytest.raises(use.FittedUseError, match="bytes_mismatch"):
        use._binding(body, records["registration"], ref)


def test_source_capability_is_minted_after_native_clock_and_identity_checks(native_training):
    population, _, window, *_ = native_training
    sources = fitted.authenticate_registered_training_sources(window, population, policy=Policy())
    assert type(sources) is fitted.RegisteredTrainingSourcesCapability
    value = fitted.disclose_registered_training_sources(sources, policy=Policy())
    assert len(value["vectors"]) == len(value["training_manifest"]) == 2
    with pytest.raises(fitted.FittedNormalizationError, match="authenticated_training_sources"):
        fitted.fit_authenticated_training_sources(value, policy=Policy())
    with pytest.raises(fitted.FittedNormalizationError):
        fitted.RegisteredTrainingSourcesCapability(b"{}", window, population, ())


@pytest.mark.parametrize("value, expected", [(Fraction(1, 2*10**18), "0.000000000000000000"),
    (Fraction(3, 2*10**18), "0.000000000000000002"),
    (Fraction(-3, 2*10**18), "-0.000000000000000002")])
def test_declared_fraction_q18_rounding(value, expected):
    assert fitted._q18(value) == expected


def test_missing_selected_temporal_bytes_cannot_mint_a_window(prepared_files, monkeypatch):
    root, selected, records, _ = prepared_files
    value, body, ref = _binding(records["registration"])
    write(root / (ref["sha256"] + ".json"), body)
    purpose = {"binding_ref": ref, "store_id": records["registration"]["corpus"]["store_id"]}
    monkeypatch.setattr(fitted, "authenticate_registered_training_sources",
        lambda *a, **k: pytest.fail("source values before selected temporal closure"))
    with use.owner._directory(root, private=True) as descriptor:
        with pytest.raises((FileNotFoundError, use.owner.E0InstalledControlError)):
            use._prepare(descriptor, selected, records,
                cohort.canonical(records["registration"]), purpose)


def test_registered_coverage_must_match_native_receipt_and_measurement(native_training, monkeypatch):
    population, _, original, *_ = native_training
    body = json.loads(original._body)
    body["coverage"][0]["source_measurement_session"] = {"id": "unverified-session"}
    altered = use.TrainingWindowCapability(cohort.canonical(body), original._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: altered)
    with pytest.raises(fitted.FittedNormalizationError, match="source_session_mismatch"):
        fitted.authenticate_registered_training_sources(altered, population, policy=Policy())


def _alter_window(original, body, monkeypatch):
    result = use.TrainingWindowCapability(cohort.canonical(body), original._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: result)
    return result


def test_frozen_109_audit_unknowns_are_preserved_not_authenticated(temporal):
    # Actual frozen membership bytes; only the split declaration is synthetic.
    temporal[4].update(boundaries={"development_end_exclusive": "2027-01-01T00:00:00.000000Z",
        "tuning_end_exclusive": "2027-02-01T00:00:00.000000Z",
        "test_start_inclusive": "2027-02-01T00:00:00.000000Z"}, embargo_seconds=0)
    for task in temporal[4]["tasks"]: task["disposition"] = "development"
    report = use._training_audit_report(source_checks(temporal), split_checks(temporal))
    assert set(report["historical_frozen_unknown_counts"].values()) == {109}
    assert report["native_source_authentication"] == "pending_separate_native_phase"
    assert report["economic_episode_independence"] == report["full_upstream_feature_support"] == "not_established"
    assert report["normalization_uses_labels"] is report["scientific_purge_or_holdout_validity_verified"] is False
    assert report["operational_study_admission"] is False


def test_unclassified_audit_marker_cannot_reach_source_phase(native_training, monkeypatch):
    _, _, window, *_ = native_training
    report = json.loads(window._body)["training_audit_report"]
    covered = {"unresolved": report["source_audit_markers"] + ["unrecognized_source_obligation"],
        "frozen_owner_metadata_unknown_counts": {}, "unknown_declarations": {}}
    checked = {"unresolved": [], "exact_task_bindings_checked": True, "declared_dispositions": {"unknown": 0}}
    monkeypatch.setattr(fitted, "_number", lambda *a: pytest.fail("arithmetic before classified audit"))
    with pytest.raises(use.FittedUseError, match="unclassified_training_audit_obligation"):
        use._training_audit_report(covered, checked)


def test_frozen_null_shape_is_qualified_only_from_genuine_native_caps(native_training):
    population, _, window, *_ = native_training
    declared = json.loads(window._body)
    assert all(row["source_measurement_session"] is None for row in declared["coverage"])
    sources = fitted.authenticate_registered_training_sources(window, population, policy=Policy())
    report = fitted.disclose_registered_training_sources(sources, policy=Policy())["qualification_report"]
    assert report["native_identity_session_availability_checked"] is True
    assert len(report["qualified_native_facts"]) == 3
    assert all(row["native_measurement_session"] for row in report["qualified_native_facts"])
    assert report["audit"] == declared["training_audit_report"]
    assert report["economic_episode_independence"] == report["full_upstream_feature_support"] == "not_established"
    assert report["scientific_holdout_or_purge_verified"] is report["operational_study_admission"] is False


@pytest.mark.parametrize("change", ["session", "availability", "receipt", "partition_clock", "manifest"])
def test_failed_native_qualification_never_reaches_arithmetic(native_training, monkeypatch, change):
    population, _, original, *_ = native_training
    body = json.loads(original._body)
    if change == "session": body["coverage"][-1]["source_measurement_session"] = {"id": "fabricated"}
    if change == "availability": body["coverage"][-1]["first_available_for_contextual_analysis"] = "2026-08-01T00:00:00Z"
    if change == "receipt": body["coverage"][-1]["receipt_sha256"] = "0" * 64
    if change == "partition_clock": body["partition_tasks"][-1]["disposition"] = "test"
    if change == "manifest": body["tasks"].reverse()
    window = _alter_window(original, body, monkeypatch)
    monkeypatch.setattr(fitted, "_number", lambda *a: pytest.fail("arithmetic before complete native qualification"))
    with pytest.raises(fitted.FittedNormalizationError):
        fitted.authenticate_registered_training_sources(window, population, policy=Policy())


def test_current_construction_is_separate_from_parameter_identity(native_training, monkeypatch):
    population, _, window, *_ = native_training
    monkeypatch.setattr(fitted, "_construction_clock", lambda: "2026-10-19T10:00:00.000000Z")
    first = fitted.fit_registered_normalizer(window, population, policy=Policy())
    monkeypatch.setattr(fitted, "_construction_clock", lambda: "2026-10-20T10:00:00.000000Z")
    second = fitted.fit_registered_normalizer(window, population, policy=Policy())
    assert first._body == second._body
    older = fitted.build_fitted_exact_index(first, population, policy=Policy())
    newer = fitted.build_fitted_exact_index(second, population, policy=Policy())
    assert older["index_id"] == newer["index_id"]
    assert older["normalizer_construction"] != newer["normalizer_construction"]
    assert older["mode"] == "historical_hypothetical"
    assert older["normalizer_construction"]["historical_availability_authenticated"] is False
    assert older["historical_index_existence_authenticated"] is False


def test_current_mode_cannot_claim_query_before_actual_construction(native_training, monkeypatch):
    population, _, original, *_ = native_training
    body = json.loads(original._body)
    body["binding"]["mode"] = "current_contextual_support"
    window = _alter_window(original, body, monkeypatch)
    monkeypatch.setattr(fitted, "_construction_clock", lambda: "2026-10-19T10:00:00.000000Z")
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    with pytest.raises(fitted.FittedNormalizationError, match="before_actual_normalizer_construction"):
        fitted.build_fitted_exact_index(normalizer, population, policy=Policy())
    monkeypatch.setattr(fitted, "_construction_clock", lambda: "2026-08-19T10:00:00.000000Z")
    timely = fitted.fit_registered_normalizer(window, population, policy=Policy())
    assert fitted.build_fitted_exact_index(timely, population, policy=Policy())["mode"] == "current_contextual_support"


def test_original_native_revision_cannot_cross_training_and_test(native_training, tmp_path, monkeypatch):
    _, _, original, a, *_ = native_training
    older = capture(tmp_path, monkeypatch, session="2026-08-09")
    revision = capture(tmp_path, monkeypatch, session="2026-08-10", seconds=60, growth=0.8)
    reader, pin = owner(tmp_path)
    cutoff = "2026-08-10T10:00:30Z"
    population = load(reader, pin, a, cutoff=cutoff)
    value = cohort.disclose_retained_context_cohort(population, policy=Policy())
    body = json.loads(original._body)
    body["binding"]["source_owner"] = {**value["owner"], "profile": features.trusted.TRUSTED_STORE_PROFILE}
    body["binding"].update(fit_cutoff=cutoff, eligible_use_from=cutoff)
    body["chronological_partition"]["boundaries"] = {"development_end_exclusive": cutoff,
        "tuning_end_exclusive": "2026-08-10T10:00:40Z", "test_start_inclusive": "2026-08-10T10:00:40Z"}
    body["coverage"], body["partition_tasks"], body["tasks"] = [], [], []
    training = {a.capture_receipt["capture_id"], older.capture_receipt["capture_id"]}
    for row in value["rows"]:
        partition = "development" if row["capture_id"] in training else (
            "test" if row["capture_id"] == revision.capture_receipt["capture_id"] else "excluded")
        task = {k: row[k] for k in ("capture_id", "context_id", "query_id")}
        task.update(task_id="synthetic-" + row["capture_id"],
            analysis_cutoff=max(row["clocks"].values(), key=cohort.utc_instant))
        body["partition_tasks"].append({**task, "disposition": partition})
        if partition == "development": body["tasks"].append(task)
        body["coverage"].append({**{k: row[k] for k in ("capture_id", "context_id", "query_id", "packet_sha256", "source_receipt_ids")},
            "receipt_sha256": row["capture_receipt_sha256"], "source_measurement_session": None,
            "first_available_for_contextual_analysis": task["analysis_cutoff"]})
    window = _alter_window(original, body, monkeypatch)
    monkeypatch.setattr(fitted, "_number", lambda *a: pytest.fail("arithmetic before native sibling separation"))
    with pytest.raises(fitted.FittedNormalizationError, match="native_session_or_revision_crosses_partitions"):
        fitted.authenticate_registered_training_sources(window, population, policy=Policy())
