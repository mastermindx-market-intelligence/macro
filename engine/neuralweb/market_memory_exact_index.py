"""Manifest-bound exact reproduction using the incumbent retained owners.

This is an in-process index capability, not another store, approximate search,
fitted transform, historical construction claim or training grant. Every read
uses the original cohort/features and their current whole-population rights.
The frozen P1 descriptor and native exhaustive retrieval remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_comparison as comparison
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_retrieval as retrieval

SCHEMA = "market_memory.exact_retained_index.v1"
MAX_INDEX_BYTES = 256 * 1024
_TOKEN = object()
_SOURCES = {name: {"module": module.__name__, "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
            for name, module in (("features", features), ("comparison", comparison),
                                 ("cohort", cohort), ("retrieval", retrieval))}
_INDEX_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


class ExactIndexError(ValueError):
    """An exact native index, owner closure or reproduction join failed."""


@dataclass(frozen=True, slots=True, init=False)
class ExactRetainedIndexCapability:
    _body: bytes
    _digest: str
    _population: cohort.RetainedContextCohortCapability
    _seal: object

    def __init__(self, body, population, *, _key=None):
        if _key is not _TOKEN:
            raise ExactIndexError("owner_verified_exact_index_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_population", population)
        object.__setattr__(self, "_seal", _TOKEN)


def _describe(population, policy):
    value = cohort.disclose_retained_context_cohort(population, policy=policy)
    projections = cohort.read_cohort_feature_capabilities(population, policy=policy)
    inventory = []
    for row, capability in zip(value["rows"], projections, strict=True):
        item = {key: row[key] for key in ("context_id", "capture_id", "status")}
        item.update(projection_id=None, feature_sha256=None)
        if capability is not None:
            projected = features.disclose_episode_features(capability, policy=policy)
            if (projected["context_id"] != row["context_id"]
                    or projected["capture_id"] != row["capture_id"]
                    or projected["projection_id"] != row["projection_id"]):
                raise ExactIndexError("exact_index_feature_closure_mismatch")
            item.update(projection_id=projected["projection_id"],
                        feature_sha256=sha256(capability._body).hexdigest())
        inventory.append(item)
    core = {"schema": SCHEMA, "kind": "exact_exhaustive_retained_capability_index",
            "owner": value["owner"], "cohort_id": value["cohort_id"],
            "membership_sha256": value["membership_sha256"],
            "manifest_sha256": sha256(population._body).hexdigest(),
            "expected_capture_count": value["expected_capture_count"],
            "inventory": inventory, "normalizer": features.fixed_comparison_descriptor(),
            "source_refs": _SOURCES,
            "index_source_sha256": _INDEX_SOURCE_SHA256,
            "source_assurance": "imported_file_bytes_not_external_runtime_attestation",
            "fit_status": "not_performed", "fit_artifact_ref": None,
            "training_eligible": False, "operational_admission": False,
            "approximate_search": False, "historical_index_existence_authenticated": False,
            "missingness": "retain_all_native_rows_no_imputation_no_dimension_drop"}
    if len(inventory) != value["expected_capture_count"]:
        raise ExactIndexError("complete_exact_index_denominator_required")
    core["index_id"] = "mmexactindex_" + sha256(cohort.canonical(core)).hexdigest()
    body = cohort.canonical(core)
    if len(body) > MAX_INDEX_BYTES:
        raise ExactIndexError("exact_index_byte_limit")
    cohort.disclose_retained_context_cohort(population, policy=policy)
    return body


def build_exact_retained_index(population, *, policy):
    """Bind every row and original projection without reading a new generation."""
    body = _describe(population, policy)
    return ExactRetainedIndexCapability(body, population, _key=_TOKEN)


def disclose_exact_retained_index(capability, *, policy):
    if (type(capability) is not ExactRetainedIndexCapability or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > MAX_INDEX_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise ExactIndexError("owner_verified_exact_index_required")
    if _describe(capability._population, policy) != capability._body:
        raise ExactIndexError("original_exact_index_changed")
    return json.loads(capability._body)


def retrieve_exact_retained_index(index, query, *, policy, k, method):
    """Consume the sealed index through the unchanged native exact comparator.

    No caller-provided rows, ranks, candidate vectors or eligibility decisions
    can enter this seam. Purge/embargo/missingness/ties remain native behavior.
    The returned object is the genuine original retrieval capability.
    """
    disclose_exact_retained_index(index, policy=policy)
    result = retrieval.retrieve_retained_contexts(index._population, query,
        policy=policy, k=k, method=method)
    disclose_exact_retained_index(index, policy=policy)
    return result


def reproduce_exact_retained_retrieval(index, query, expected, *, policy, method):
    """Reexecute and compare one genuine retained result, never an acceptance test.

    This proves byte reproduction for the declared retained owners and method.
    It does not estimate effective N, validate a model or admit a study.
    """
    descriptor = disclose_exact_retained_index(index, policy=policy)
    baseline = retrieval.disclose_episode_retrieval(expected, policy=policy)
    if (type(method) is not retrieval.RetainedContextMethodSpec
            or baseline["method_spec"] != method.disclosure()
            or baseline["membership_sha256"] != descriptor["membership_sha256"]
            or baseline["audit"]["cohort_id"] != descriptor["cohort_id"]
            or baseline["audit"]["original_owner"] != descriptor["owner"]):
        raise ExactIndexError("exact_reproduction_owner_or_method_mismatch")
    actual = retrieve_exact_retained_index(index, query, policy=policy,
        k=baseline["requested_k"], method=method)
    observed = retrieval.disclose_episode_retrieval(actual, policy=policy)
    if cohort.canonical(baseline) != cohort.canonical(observed):
        raise ExactIndexError("exact_retrieval_not_reproduced")
    # Final gates cover the expected result's entire pool as well as the new one.
    retrieval.disclose_episode_retrieval(expected, policy=policy)
    disclose_exact_retained_index(index, policy=policy)
    return {"schema": "market_memory.exact_retained_reproduction.v1",
            "index_id": descriptor["index_id"],
            "manifest_sha256": descriptor["manifest_sha256"],
            "membership_sha256": descriptor["membership_sha256"],
            "normalizer_sha256": descriptor["normalizer"]["content_sha256"],
            "method_spec_id": baseline["method_spec"]["method_spec_id"],
            "selection_sha256": baseline["selection_sha256"],
            "result_sha256": sha256(cohort.canonical(observed)).hexdigest(),
            "denominator": baseline["denominator"], "byte_exact_reproduction": True,
            "fit_status": "not_performed", "operational_admission": False,
            "evaluation_acceptance": False, "effective_n": "not_estimated"}
