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


@pytest.fixture
def native_training(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    value = cohort.disclose_retained_context_cohort(population, policy=Policy())
    caps = cohort.read_cohort_feature_capabilities(population, policy=Policy())
    candidates = {features.disclose_episode_features(c, policy=Policy())["capture_id"]: c
                  for c in caps if c is not None}
    tasks, coverage = [], []
    for number, stored in enumerate((a, b)):
        projected = features.disclose_episode_features(candidates[stored.capture_receipt["capture_id"]], policy=Policy())
        tasks.append({"task_id": "synthetic-task-" + str(number),
            "capture_id": projected["capture_id"], "context_id": projected["context_id"],
            "query_id": projected["owner"]["query_id"],
            "analysis_cutoff": max(projected["clocks"].values(), key=cohort.utc_instant)})
        coverage.append({"capture_id": projected["capture_id"], "context_id": projected["context_id"],
            "query_id": projected["owner"]["query_id"], "packet_sha256": projected["packet_sha256"],
            "receipt_sha256": projected["capture_receipt_sha256"], "source_receipt_ids": projected["source_receipt_ids"],
            "source_measurement_session": {"id": projected["measurement_period"]["value"]},
            "first_available_for_contextual_analysis": tasks[-1]["analysis_cutoff"]})
    binding = {"binding_id": "synthetic-owner-window", "source_owner": {**value["owner"], "profile": features.trusted.TRUSTED_STORE_PROFILE},
        "training_start_inclusive": "2026-08-01T00:00:00Z", "fit_cutoff": CUTOFF,
        "eligible_use_from": CUTOFF}
    body = cohort.canonical({"binding": binding, "tasks": tasks, "coverage": coverage})
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
    assert fitted.disclose_fitted_normalizer(after, policy=Policy()) == before
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
        assert fitted.disclose_fitted_normalizer(after, policy=Policy()) == fitted.disclose_fitted_normalizer(before, policy=Policy())
        assert fitted.build_fitted_exact_index(after, population, policy=Policy()) == fitted.build_fitted_exact_index(before, population, policy=Policy())
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
        "purpose": use.PURPOSE, "normalization_method": use.METHOD,
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
    body["coverage"][0]["source_measurement_session"]["id"] = "unverified-session"
    altered = use.TrainingWindowCapability(cohort.canonical(body), original._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: altered)
    with pytest.raises(fitted.FittedNormalizationError, match="source_coverage_mismatch"):
        fitted.authenticate_registered_training_sources(altered, population, policy=Policy())
