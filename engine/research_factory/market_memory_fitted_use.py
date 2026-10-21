"""Fixed-owner preparation of one versioned, label-free normalization use.

The existing Chairman source authority covers parameter estimation for project
customer comparisons. This version preserves the fixed v1 policy byte-for-byte.
It creates no store, selected registration, source permission or study admission.
The shipped purpose record is disabled and has no selected binding.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from . import market_memory_contextual_registration as control
from . import market_memory_e0_domains as temporal
from . import market_memory_e0_installed_control as owner
from . import market_memory_e0_task_evidence as tasks

PURPOSE_PATH = "config/market_memory_retained_use.v2.json"
BASELINE_PURPOSE_PATH = "config/market_memory_retained_use.v1.json"
AUTHORITY_RECORD = "research/licenses/MARKET_MEMORY_HOUSE_MACRO_REUSE_2026-10-13.md"
FIELDS = ("growth_score", "inflation_score", "quad", "liquidity_overlay", "cycle_tag")
SCHEMA = "market_memory.fitted_use_binding.v2"
PURPOSE = "normalization_parameter_estimation_for_customer_comparisons"
METHOD = "house_numeric_exact_mean_range.v2"
MAX_BINDING_BYTES = 256 * 1024
_TOKEN = object()
_MODULE_PATH = "engine/research_factory/market_memory_fitted_use.py"
_SOURCE_PATHS = owner._TASK_SOURCE_PATHS + (
    _MODULE_PATH, PURPOSE_PATH, "engine/neuralweb/market_memory_fitted_normalization.py",
    "engine/neuralweb/market_memory_exact_index.py",
    "engine/neuralweb/market_memory_fitted_retrieval.py",
    "engine/neuralweb/market_memory_fitted_distance.py",
    BASELINE_PURPOSE_PATH, AUTHORITY_RECORD,
    "engine/research_factory/market_memory_e0_domains.py",
    "contracts/market_memory/e0_source_coverage.v1.schema.json",
    "contracts/market_memory/e0_interval_split.v1.schema.json",
    "contracts/market_memory/fitted_use_binding.v2.schema.json",
)


class FittedUseError(ValueError):
    """Stable reason; never payload, arbitrary path or user identity."""


def _require(value, reason):
    if not value:
        raise FittedUseError(reason)


def _record(root, name):
    path = root / name
    with owner._directory(path.parent, private=False) as descriptor:
        return owner._read(descriptor, path.name, 64 * 1024, private=False)


def _purpose(root):
    # Reuse the original installed source record/authority, without importing
    # site entitlement or creating a second account/permission owner. Native
    # feature reads still enforce their complete current application policy.
    baseline = control._domain_json(_record(root, BASELINE_PURPOSE_PATH))
    _require(baseline["schema"] == "market_memory.retained_house_use.v1"
        and baseline["enabled"] is True and baseline["source_authority"]["record"] == AUTHORITY_RECORD
        and sha256(_record(root, AUTHORITY_RECORD)).hexdigest() == baseline["source_authority"]["sha256"]
        and baseline["source_authority"]["basis"] == "direct_chairman_confirmation",
        "existing_chairman_source_authority_required")
    body = _record(root, PURPOSE_PATH)
    value = control._domain_json(body)
    expected = {"schema", "enabled", "source_authority", "purpose", "source_profile", "store_id",
        "allowed_subject_ids", "fields", "normalization_method", "external_foundation_model_training",
        "prophet_training", "promotion_eligible", "selected_study_id", "binding_ref"}
    _require(type(value) is dict and set(value) == expected
        and value["schema"] == "market_memory.retained_house_normalization_use.v2"
        and value["source_authority"] == baseline["source_authority"]
        and value["source_profile"] == baseline["store_profile"]
        and value["store_id"] == baseline["store_id"]
        and value["allowed_subject_ids"] == baseline["allowed_subject_ids"]
        and value["fields"] == list(FIELDS) and value["purpose"] == PURPOSE
        and value["normalization_method"] == METHOD
        and all(value[k] is False for k in ("external_foundation_model_training", "prophet_training",
                                             "promotion_eligible")), "exact_normalization_purpose_required")
    _require(value["enabled"] is True and type(value["selected_study_id"]) is str
        and control._ID.fullmatch(value["selected_study_id"]) is not None,
        "selected_normalization_use_not_active")
    ref = control._domain_reference(value["binding_ref"])
    _require(ref["schema"] == SCHEMA and ref["bytes"] <= MAX_BINDING_BYTES,
             "exact_fitted_binding_reference_required")
    return value, body


def _binding(body, registration, ref):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((Path(__file__).resolve().parents[2] /
        "contracts/market_memory/fitted_use_binding.v2.schema.json").read_text())
    value = control._domain_json(body)
    _require(len(body) == ref["bytes"] and sha256(body).hexdigest() == ref["sha256"]
        and control._domain_snapshot(value)[1] == body, "fitted_binding_bytes_mismatch")
    Draft202012Validator.check_schema(schema)
    _require(next(control._INTEGER_VALIDATOR(schema, format_checker=FormatChecker()).iter_errors(value), None)
        is None, "fitted_binding_schema_violation")
    _require(value["binding_id"] == ref["object_id"]
        and value["registration_ref"] == control._record_ref(registration, "registration")
        and value["purpose"] == PURPOSE and value["normalization_method"] == METHOD,
        "selected_fitted_binding_mismatch")
    clocks = [control._clock(value[k]) for k in
              ("training_start_inclusive", "fit_cutoff", "eligible_use_from")]
    _require(clocks[0] < clocks[1] <= clocks[2], "registered_training_clock_order")
    return value


def _training_audit_report(covered, checked):
    """Classify only known descriptive gaps; this never authenticates a source.

    The frozen audit remains unchanged. Native identities, actual measurement
    sessions and clocks must still qualify in the separate source phase before
    any numeric conversion. Economic independence/full support are not inferred.
    """
    source_allowed = {"frozen_owner_measurement_episode_or_span_provenance",
        "declared_measurement_episode_feature_or_label_support",
        "outcome_definition_semantics_for_declared_nonapplicability"}
    split_allowed = {"declared_session_episode_and_full_support_spans",
        "outcome_definition_semantics_for_declared_nonapplicability"}
    _require(set(covered["unresolved"]) <= source_allowed
        and set(checked["unresolved"]) <= split_allowed, "unclassified_training_audit_obligation")
    _require(checked["exact_task_bindings_checked"] is True
        and checked["declared_dispositions"]["unknown"] == 0,
        "exact_chronological_training_partition_required")
    return {"source_audit_markers": list(covered["unresolved"]),
        "split_audit_markers": list(checked["unresolved"]),
        "historical_frozen_unknown_counts": covered["frozen_owner_metadata_unknown_counts"],
        "declared_unknown_counts": covered["unknown_declarations"],
        "native_source_authentication": "pending_separate_native_phase",
        "economic_episode_independence": "not_established",
        "full_upstream_feature_support": "not_established",
        "normalization_uses_labels": False,
        "E0_annotation_or_L0_financial_outcomes_authenticated": False,
        "scientific_purge_or_holdout_validity_verified": False,
        "operational_study_admission": False}


def _prepare(descriptor, selected, records, registration_body, purpose):
    reg = records["registration"]
    _require(records["access"]["status"] == "active"
        and records["access"]["contamination_state"] == "clean",
        "current_clean_training_access_required")
    binding_ref = purpose["binding_ref"]
    binding_body = owner._read(descriptor, binding_ref["sha256"] + ".json", MAX_BINDING_BYTES)
    binding = _binding(binding_body, reg, binding_ref)
    _require(binding["source_owner"] == {key: reg["corpus"][key] for key in
        ("profile", "store_id", "generation_id", "generation_sha256", "membership_sha256")}
        and binding["source_owner"]["store_id"] == purpose["store_id"], "fitted_source_owner_mismatch")
    roles = (("method", reg["implementation"]["method_ref"]), ("tasks", reg["tasks_ref"]),
        ("membership", reg["corpus"]["membership_ref"]),
        ("coverage", reg["source_coverage_ref"]), ("split", reg["interval_split_ref"]))
    refs = {name: control._domain_reference(ref) for name, ref in roles}
    _require(refs["coverage"] == binding["source_coverage_ref"]
        and refs["split"] == binding["interval_split_ref"], "exact_selected_temporal_references_required")
    _require(len({ref["sha256"] for ref in refs.values()}) == len(refs)
        and all(ref["bytes"] <= control.MAX_DOMAIN_OBJECT_BYTES for ref in refs.values()),
        "bounded_distinct_training_roles_required")
    bodies = {"registration": registration_body, "binding": binding_body}
    observed = {binding_ref["sha256"]: binding_body}
    total = len(binding_body)

    def read(ref):
        nonlocal total
        digest = ref["sha256"]
        if digest not in observed:
            _require(len(observed) < control.MAX_DOMAIN_OBJECTS, "training_reference_count_limit")
            _require(ref["bytes"] <= control.MAX_DOMAIN_OBJECT_BYTES
                and total + ref["bytes"] <= control.MAX_DOMAIN_TOTAL_BYTES,
                "declared_training_reference_byte_limit")
            body = owner._read(descriptor, digest + ".json", control.MAX_DOMAIN_OBJECT_BYTES)
            total += len(body)
            _require(total <= control.MAX_DOMAIN_TOTAL_BYTES, "training_reference_byte_limit")
            _require(len(body) == ref["bytes"] and sha256(body).hexdigest() == digest,
                     "training_reference_bytes_mismatch")
            observed[digest] = body
        return observed[digest]

    for name, ref in refs.items():
        bodies[name] = read(ref)
    method, _ = tasks.resolve_registered_task_inputs(registration=registration_body,
        method_manifest=bodies["method"], task_manifest=bodies["tasks"], frozen_membership=bodies["membership"])
    _require(binding["mode"] == method.mode, "selected_training_mode_mismatch")
    manifest, membership = (control._domain_json(bodies[k]) for k in ("tasks", "membership"))
    coverage = temporal.validate_declaration(control._domain_json(bodies["coverage"]),
        bodies["coverage"], role="source_coverage_ref", registration=reg)
    split = temporal.validate_declaration(control._domain_json(bodies["split"]),
        bodies["split"], role="interval_split_ref", registration=reg)
    for role, declaration in (("source_coverage_ref", coverage), ("interval_split_ref", split)):
        for _, ref in temporal.provenance_references(declaration, role=role):
            read(control._domain_reference(ref))
    covered = temporal.source_coverage_checks(coverage, membership=membership, resolved_digests=set(observed))
    checked = temporal.interval_split_checks(split, tasks=manifest, coverage=coverage,
        membership=membership, resolved_digests=set(observed))
    report = _training_audit_report(covered, checked)
    training = [row["task_id"] for row in split["tasks"] if row["disposition"] == "development"]
    _require(training and training == binding["training_task_ids"]
        and split["boundaries"]["development_end_exclusive"] == binding["fit_cutoff"],
        "exact_development_training_manifest_required")
    _require(control._clock(binding["eligible_use_from"]) >= control._clock(binding["fit_cutoff"])
        + timedelta(seconds=split["embargo_seconds"]), "registered_fit_embargo_required")
    task_map = {row["task_id"]: row for row in manifest["tasks"]}
    selected_tasks = [task_map[identity] for identity in training]
    _require(len({row["capture_id"] for row in selected_tasks}) == len(selected_tasks),
             "one_training_row_per_original_capture_required")
    coverage_map = {row["capture_id"]: row for row in coverage["entries"]}
    partitions = {row["task_id"]: row["disposition"] for row in split["tasks"]}
    body = control._domain_snapshot({"schema": "market_memory.selected_training_inputs.v2",
        "purpose_sha256": sha256(control._domain_snapshot(purpose)[1]).hexdigest(),
        "selection_sha256": sha256(control._domain_snapshot(selected)[1]).hexdigest(),
        "binding": binding, "eligibility_method_spec": method.disclosure(), "tasks": selected_tasks,
        "partition_tasks": [{**task, "disposition": partitions[task["task_id"]]}
                            for task in manifest["tasks"]],
        "chronological_partition": {"boundaries": split["boundaries"],
                                    "embargo_seconds": split["embargo_seconds"]},
        "coverage": [coverage_map[task["capture_id"]] for task in manifest["tasks"]],
        "training_audit_report": report,
        "reference_sha256": sorted(observed), "operational_study_admission": False})[1]
    for digest, original in observed.items():
        _require(owner._read(descriptor, digest + ".json", control.MAX_DOMAIN_OBJECT_BYTES) == original,
                 "selected_training_domain_changed")
    return body


@dataclass(frozen=True, slots=True, init=False, repr=False)
class TrainingWindowCapability:
    """Owner-qualified selected metadata; never native-source authentication."""
    _body: bytes
    _selection: bytes
    _seal: object

    def __init__(self, body, selection, *, _key=None):
        _require(_key is _TOKEN, "authenticated_training_window_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_selection", selection)
        object.__setattr__(self, "_seal", _TOKEN)


@dataclass(frozen=True, slots=True, init=False, repr=False)
class RetainedTrainingWindowCapability:
    """Original immutable fit provenance; current authority is checked separately."""
    _body: bytes
    _retained: object
    _seal: object

    def __init__(self, body, retained, *, _key=None):
        _require(_key is _TOKEN, "retained_training_window_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_retained", retained)
        object.__setattr__(self, "_seal", _TOKEN)


def prepare_registered_training_window():
    """Fixed installed administrator path. No caller path, grant or callback."""
    _require(sys.platform == "linux" and os.geteuid() == 0
        and Path(__file__).resolve() == owner.INSTALLED_ROOT / _MODULE_PATH,
        "installed_training_administrator_required")
    purpose, purpose_body = _purpose(owner.INSTALLED_ROOT)
    from engine.neuralweb import market_memory_fitted_normalization, market_memory_fitted_retrieval
    owner._verify_loaded_sources(paths=_SOURCE_PATHS)
    directory = owner.CONTROL_ROOT / sha256(purpose["selected_study_id"].encode()).hexdigest()
    body, selection = owner._load_selected_control(directory, purpose["selected_study_id"],
        lambda commit: owner._verify_source(owner.INSTALLED_ROOT, commit, paths=_SOURCE_PATHS),
        clock=lambda: datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        prepare=lambda fd, selected, records, registration: _prepare(fd, selected, records,
            registration, purpose))
    _require(_purpose(owner.INSTALLED_ROOT)[1] == purpose_body, "normalization_purpose_changed")
    return TrainingWindowCapability(body, selection, _key=_TOKEN)


def disclose_training_window(capability):
    if type(capability) is RetainedTrainingWindowCapability:
        _require(capability._seal is _TOKEN and type(capability._body) is bytes
            and len(capability._body) <= control.MAX_DOMAIN_OBJECT_BYTES,
            "retained_training_window_required")
        from . import market_memory_fitted_persistence as persistence
        return persistence._disclose_retained_window(capability)
    _require(type(capability) is TrainingWindowCapability and capability._seal is _TOKEN
        and type(capability._body) is bytes and len(capability._body) <= control.MAX_DOMAIN_OBJECT_BYTES,
        "authenticated_training_window_required")
    current = prepare_registered_training_window()
    _require(current._body == capability._body and current._selection == capability._selection,
             "registered_training_window_changed")
    return control._domain_json(capability._body)
