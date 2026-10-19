"""Versioned training-only parameter estimation for retained comparisons.

Consumes a fixed-owner training-window capability, never a caller permission
flag or feature dictionary. All v1 feature, descriptor and retrieval bytes stay
unchanged. No public runtime caller, live fit, label access or promotion exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from engine.research_factory import market_memory_fitted_use as use
from . import market_memory_episode_features as features
from . import market_memory_retained_context_cohort as cohort
from . import market_memory_exact_index as exact

_TOKEN = object()
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


class FittedNormalizationError(ValueError):
    """A registered training, source, clock or exact manifest join failed."""


def _require(ok, reason):
    if not ok:
        raise FittedNormalizationError(reason)


def _fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _ratio(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _q18(value):
    quotient, remainder = divmod(abs(value.numerator) * 10**18, value.denominator)
    if 2 * remainder > value.denominator or 2 * remainder == value.denominator and quotient % 2:
        quotient += 1
    return ("-" if value < 0 and quotient else "") + str(quotient // 10**18) + "." + f"{quotient % 10**18:018d}"


def _number(coordinate):
    # P1 authenticates the binary64 value and its fixed q18 projection. The v2
    # convention fits the original finite binary64 ratio, not ambient Decimal.
    return Fraction.from_float(float.fromhex(coordinate["source_binary64_hex"]))


def _encoded(value):
    body = cohort.canonical(value)
    _require(len(body) <= MAX_ARTIFACT_BYTES, "fitted_artifact_byte_limit")
    return body


@dataclass(frozen=True, slots=True, init=False, repr=False)
class RegisteredTrainingSourcesCapability:
    _body: bytes
    _digest: str
    _window: use.TrainingWindowCapability
    _population: cohort.RetainedContextCohortCapability
    _features: tuple
    _seal: object

    def __init__(self, body, window, population, projections, *, _key=None):
        _require(_key is _TOKEN, "authenticated_training_sources_required")
        for k, v in (("_body", body), ("_digest", sha256(body).hexdigest()), ("_window", window),
                     ("_population", population), ("_features", projections), ("_seal", _TOKEN)):
            object.__setattr__(self, k, v)


def disclose_registered_training_sources(capability, *, policy):
    _require(type(capability) is RegisteredTrainingSourcesCapability and capability._seal is _TOKEN
        and type(capability._body) is bytes and len(capability._body) <= MAX_ARTIFACT_BYTES
        and sha256(capability._body).hexdigest() == capability._digest,
        "authenticated_training_sources_required")
    use.disclose_training_window(capability._window)
    cohort.disclose_retained_context_cohort(capability._population, policy=policy)
    value = json.loads(capability._body)
    _require(value["window_sha256"] == sha256(capability._window._body).hexdigest()
        and len(capability._features) == len(value["training_manifest"]),
        "original_registered_training_source_changed")
    for cap, row in zip(capability._features, value["training_manifest"], strict=True):
        projected = features.disclose_episode_features(cap, policy=policy, for_comparison=True)
        _require(projected["context_id"] == row["context_id"]
            and sha256(cap._body).hexdigest() == row["feature_sha256"],
            "original_registered_training_source_changed")
    use.disclose_training_window(capability._window)
    return value


@dataclass(frozen=True, slots=True, init=False, repr=False)
class FittedNormalizerCapability:
    _body: bytes
    _digest: str
    _window: use.TrainingWindowCapability
    _population: cohort.RetainedContextCohortCapability
    _features: tuple
    _seal: object

    def __init__(self, body, window, population, projections, *, _key=None):
        _require(_key is _TOKEN, "registered_fitted_normalizer_required")
        for k, v in (("_body", body), ("_digest", sha256(body).hexdigest()), ("_window", window),
                     ("_population", population), ("_features", projections), ("_seal", _TOKEN)):
            object.__setattr__(self, k, v)


def authenticate_registered_training_sources(window, population, *, policy):
    """Fit only the exact registered development rows, before eligible use.

    The v2 owner grant names deterministic comparison normalization only. It
    does not change the original projection's v1 fit=false provenance, grant
    foundation-model training, authenticate independent samples or admit E0.
    """
    declared = use.disclose_training_window(window)
    binding = declared["binding"]
    value = cohort.disclose_retained_context_cohort(population, policy=policy)
    original = binding["source_owner"]
    _require(original["profile"] == features.trusted.TRUSTED_STORE_PROFILE
        and all(value["owner"][k] == original[k] for k in
        ("store_id", "generation_id", "generation_sha256"))
        and value["owner"]["query_cutoff"] == binding["fit_cutoff"], "registered_fit_source_owner_required")
    projections = cohort.read_cohort_feature_capabilities(population, policy=policy)
    by_capture = {row["capture_id"]: (row, cap) for row, cap in zip(value["rows"], projections, strict=True)}
    vectors, retained, manifest = [], [], []
    coverage = {row["capture_id"]: row for row in declared["coverage"]}
    _require(len(coverage) == len(declared["tasks"]), "complete_registered_training_coverage_required")
    start, cutoff = (cohort.utc_instant(binding[k]) for k in ("training_start_inclusive", "fit_cutoff"))
    for task in declared["tasks"]:
        _require(task["capture_id"] in by_capture, "registered_training_capture_missing")
        row, cap = by_capture[task["capture_id"]]
        _require(row["status"] == "representative" and cap is not None,
                 "registered_training_coordinates_unavailable_no_drop")
        projected = features.disclose_episode_features(cap, policy=policy, for_comparison=True)
        _require(projected["owner"]["profile"] == original["profile"]
            and all(projected[k] == task[k] for k in ("capture_id", "context_id"))
            and projected["owner"]["query_id"] == task["query_id"], "original_training_task_feature_mismatch")
        analysis = cohort.utc_instant(task["analysis_cutoff"])
        source = coverage.get(task["capture_id"])
        _require(source is not None and source["context_id"] == projected["context_id"]
            and source["query_id"] == projected["owner"]["query_id"]
            and source["packet_sha256"] == projected["packet_sha256"]
            and source["receipt_sha256"] == projected["capture_receipt_sha256"]
            and source["source_receipt_ids"] == projected["source_receipt_ids"]
            and source["source_measurement_session"]["id"] == projected["measurement_period"]["value"],
            "native_training_source_coverage_mismatch")
        available = cohort.utc_instant(source["first_available_for_contextual_analysis"])
        _require(start <= analysis < cutoff and all(cohort.utc_instant(clock) <= analysis
            for clock in projected["clocks"].values()) and available <= analysis
            and all(cohort.utc_instant(clock) <= available for clock in projected["clocks"].values()),
            "training_feature_after_registered_cutoff")
        _require(all(c["status"] == "observed" for c in projected["coordinates"]),
                 "registered_training_coordinates_unavailable_no_drop")
        vectors.append([_number(c) for c in projected["coordinates"][:2]])
        retained.append(cap)
        manifest.append({"task_id": task["task_id"], "capture_id": projected["capture_id"],
            "context_id": projected["context_id"], "packet_sha256": projected["packet_sha256"],
            "capture_receipt_sha256": projected["capture_receipt_sha256"],
            "feature_sha256": sha256(cap._body).hexdigest(), "clocks": projected["clocks"]})
    _require(len(vectors) >= 2 and len({r["capture_id"] for r in manifest}) == len(vectors),
             "two_distinct_registered_training_captures_required")
    source_body = _encoded({"schema": "market_memory.registered_training_sources.v2",
        "window_sha256": sha256(window._body).hexdigest(), "subject_id": value["owner"]["subject_id"],
        "training_manifest": manifest, "vectors": [[_ratio(v) for v in row] for row in vectors]})
    sources = RegisteredTrainingSourcesCapability(source_body, window, population, tuple(retained), _key=_TOKEN)
    disclose_registered_training_sources(sources, policy=policy)
    return sources


def fit_registered_normalizer(window, population, *, policy):
    """Authenticate original source clocks before fitting the typed window."""
    return fit_authenticated_training_sources(
        authenticate_registered_training_sources(window, population, policy=policy), policy=policy)


def fit_authenticated_training_sources(sources, *, policy):
    source = disclose_registered_training_sources(sources, policy=policy)
    window, population, retained = sources._window, sources._population, sources._features
    declared = use.disclose_training_window(window)
    binding = declared["binding"]
    original, manifest = binding["source_owner"], source["training_manifest"]
    vectors = [[_fraction(v) for v in row] for row in source["vectors"]]
    parameters = []
    for position, name in enumerate(("growth_score", "inflation_score")):
        numbers = [row[position] for row in vectors]
        mean = sum(numbers, Fraction()) / len(numbers)
        scale = max(numbers) - min(numbers)
        parameters.append({"id": name, "mean": _ratio(mean), "scale": _ratio(scale or Fraction(1)),
            "constant_training_coordinate": scale == 0})
    core = {"schema": "market_memory.fitted_normalizer.v2", "method": use.METHOD,
        "implementation_source_sha256": _SOURCE_SHA256,
        "numeric_convention": "original_binary64_exact_fraction_mean_range_q18_half_even_once.v2",
        "training_window_sha256": sha256(window._body).hexdigest(),
        "binding_id": binding["binding_id"], "fit_cutoff": binding["fit_cutoff"],
        "eligible_use_from": binding["eligible_use_from"], "source_owner": original,
        "subject_id": source["subject_id"],
        "training_manifest": manifest, "training_manifest_sha256": sha256(cohort.canonical(manifest)).hexdigest(),
        "parameters": parameters, "categorical_descriptor": features.fixed_comparison_descriptor()["coordinates"][2:],
        "out_of_training_range": "no_clipping", "missingness": "no_imputation_no_dimension_drop",
        "v1_descriptor_sha256": features.fixed_comparison_descriptor()["content_sha256"],
        "external_foundation_model_training": False, "operational_study_admission": False,
        "historical_fit_existence_authenticated": False,
        "construction_provenance": "current_construction_not_historical_fit_availability_proof",
        "independent_episode_count": "not_established", "effective_n": "not_estimated"}
    core["normalizer_id"] = "mmfittednormalizer_" + sha256(cohort.canonical(core)).hexdigest()
    result = FittedNormalizerCapability(_encoded(core), window, population, tuple(retained), _key=_TOKEN)
    disclose_fitted_normalizer(result, policy=policy)
    return result


def disclose_fitted_normalizer(capability, *, policy):
    _require(type(capability) is FittedNormalizerCapability and capability._seal is _TOKEN
        and type(capability._body) is bytes and len(capability._body) <= MAX_ARTIFACT_BYTES
        and sha256(capability._body).hexdigest() == capability._digest, "registered_fitted_normalizer_required")
    window = use.disclose_training_window(capability._window)
    value = json.loads(capability._body)
    _require(value["training_window_sha256"] == sha256(capability._window._body).hexdigest()
        and value["binding_id"] == window["binding"]["binding_id"], "original_fitted_window_changed")
    cohort.disclose_retained_context_cohort(capability._population, policy=policy)
    _require(len(capability._features) == len(value["training_manifest"]), "complete_training_feature_closure_required")
    for cap, row in zip(capability._features, value["training_manifest"], strict=True):
        projected = features.disclose_episode_features(cap, policy=policy, for_comparison=True)
        _require(projected["context_id"] == row["context_id"]
            and sha256(cap._body).hexdigest() == row["feature_sha256"], "original_training_feature_changed")
    use.disclose_training_window(capability._window)
    return value


def build_fitted_exact_index(normalizer, population, *, policy):
    """Produce a finite exact vector manifest; never activate an index service.

    Candidate and training manifests remain distinct. Appending future evidence
    can change a new candidate index, never already-frozen fitted parameters.
    """
    fitted = disclose_fitted_normalizer(normalizer, policy=policy)
    native = exact.build_exact_retained_index(population, policy=policy)
    manifest = exact.disclose_exact_retained_index(native, policy=policy)
    _require(manifest["owner"]["store_id"] == fitted["source_owner"]["store_id"]
        and manifest["owner"]["subject_id"] == fitted["subject_id"]
        and cohort.utc_instant(manifest["owner"]["query_cutoff"]) >= cohort.utc_instant(fitted["eligible_use_from"]),
        "fitted_index_before_registered_eligible_use")
    caps = cohort.read_cohort_feature_capabilities(population, policy=policy)
    rows = []
    for row, cap in zip(manifest["inventory"], caps, strict=True):
        transformed = None
        if cap is not None:
            value = features.disclose_episode_features(cap, policy=policy)
            if all(c["status"] == "observed" for c in value["coordinates"]):
                value = features.disclose_episode_features(cap, policy=policy, for_comparison=True)
                transformed = [_q18((_number(c) - _fraction(p["mean"])) / _fraction(p["scale"]))
                    for c, p in zip(value["coordinates"][:2], fitted["parameters"], strict=True)]
                transformed += [c["value"] for c in value["coordinates"][2:]]
        rows.append({**row, "normalized_coordinates": transformed})
    core = {"schema": "market_memory.fitted_exact_index.v2", "normalizer_id": fitted["normalizer_id"],
        "normalizer_sha256": sha256(normalizer._body).hexdigest(), "baseline_index": manifest,
        "rows": rows, "approximate_search": False, "operational_admission": False,
        "historical_index_existence_authenticated": False}
    core["index_id"] = "mmfittedindex_" + sha256(cohort.canonical(core)).hexdigest()
    body = _encoded(core)
    disclose_fitted_normalizer(normalizer, policy=policy)
    exact.disclose_exact_retained_index(native, policy=policy)
    # Detached descriptive manifest, not another authority-bearing capability.
    return json.loads(body)
