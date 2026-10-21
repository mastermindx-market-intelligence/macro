"""Versioned exact fitted comparison over the incumbent native eligibility audit.

The v1 reader still owns population, grouping, missingness and calendar exclusions.
This consumer reranks its complete eligible set with one selected normalizer. It
does not reuse a truncated baseline selection, read outcomes, or admit a study.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from . import market_memory_episode_features as features
from . import market_memory_episode_retrieval as baseline
from . import market_memory_retained_context_cohort as cohort
from . import market_memory_fitted_normalization as fitted
from . import market_memory_fitted_distance as distance

SCHEMA = "market_memory.fitted_episode_retrieval.v2"
MAX_RESULT_BYTES = 2 * 1024 * 1024
_TOKEN = object()
_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
_DISTANCE_SHA256 = sha256(Path(distance.__file__).read_bytes()).hexdigest()


class FittedRetrievalError(ValueError):
    """Exact native identity, complete eligibility, or fitted method mismatch."""


def _require(value, reason):
    if not value:
        raise FittedRetrievalError(reason)


@dataclass(frozen=True, slots=True, init=False, repr=False)
class FittedRetrievalCapability:
    _body: bytes
    _digest: str
    _normalizer: fitted.FittedNormalizerCapability
    _eligibility: baseline.EpisodeRetrievalCapability
    _seal: object

    def __init__(self, body, normalizer, eligibility, *, _key=None):
        _require(_key is _TOKEN, "owner_verified_fitted_retrieval_required")
        for key, value in (("_body", body), ("_digest", sha256(body).hexdigest()),
                           ("_normalizer", normalizer), ("_eligibility", eligibility),
                           ("_seal", _TOKEN)):
            object.__setattr__(self, key, value)


def retrieve_fitted_contexts(normalizer, population, query, *, policy, k, eligibility):
    """Use native exclusions for every row, then rank the entire eligible pool.

    The native baseline's requested k=1 bounds its unused comparison output. Its
    complete accounting and retained whole-pool capability remain authoritative;
    the baseline's chosen neighbor never determines the fitted candidate pool.
    """
    _require(type(k) is int and 1 <= k <= baseline.MAX_K, "finite_positive_k_required")
    _require(type(eligibility) is baseline.RetainedContextMethodSpec,
             "immutable_native_eligibility_spec_required")
    normal = fitted.disclose_fitted_normalizer(normalizer, policy=policy)
    _require(eligibility.mode == normal["mode"], "registered_fitted_mode_mismatch")
    _require(eligibility.disclosure() == normal["eligibility_method_spec"],
             "registered_fitted_eligibility_method_mismatch")
    index = fitted.build_fitted_exact_index(normalizer, population, policy=policy)
    native = baseline.retrieve_retained_contexts(population, query, policy=policy,
                                                k=1, method=eligibility)
    audit = baseline.disclose_episode_retrieval(native, policy=policy)
    projected = features.disclose_episode_features(query, policy=policy, for_comparison=True)
    owner = index["baseline_index"]["owner"]
    _require(all(projected["owner"][key] == owner[key] for key in
                 ("store_id", "generation_id", "generation_sha256", "subject_id", "query_cutoff")),
             "query_exact_fitted_population_owner_required")
    _require(audit["membership_sha256"] == index["baseline_index"]["membership_sha256"]
             and audit["audit"]["cohort_id"] == index["baseline_index"]["cohort_id"]
             and audit["audit"]["original_owner"] == owner,
             "native_eligibility_index_owner_mismatch")
    coordinates = [fitted._q18((fitted._number(row) - fitted._fraction(param["mean"]))
                               / fitted._fraction(param["scale"]))
                   for row, param in zip(projected["coordinates"][:2], normal["parameters"], strict=True)]
    coordinates += [row["value"] for row in projected["coordinates"][2:]]
    inventory = {row["capture_id"]: row for row in index["rows"]}
    _require(len(inventory) == len(index["rows"]) == len(audit["accounting"]),
             "complete_fitted_population_required")
    ranked = []
    for accounted in audit["accounting"]:
        candidate = inventory.get(accounted["capture_id"])
        _require(candidate is not None and candidate["context_id"] == accounted["context_id"],
                 "fitted_candidate_identity_mismatch")
        if accounted["reason"] != "numerically_eligible":
            continue
        _require(candidate["normalized_coordinates"] is not None,
                 "eligible_fitted_coordinates_missing_no_drop")
        compared = distance.compare_coordinates(coordinates, candidate["normalized_coordinates"])
        ranked.append({"candidate": {key: candidate[key] for key in
                                      ("capture_id", "context_id", "projection_id", "feature_sha256")},
                       **compared})
    _require(len(ranked) == audit["denominator"]["eligible_representatives"],
             "complete_fitted_eligible_set_required")
    ranked.sort(key=lambda row: (Fraction(row["distance_q18"]), row["candidate"]["context_id"]))
    selected = ranked[:k]
    method = {"method": "house_fitted_equal_weight_L1.v2",
              "normalizer_id": normal["normalizer_id"], "normalizer_sha256": sha256(normalizer._body).hexdigest(),
              "eligibility_method_spec": audit["method_spec"],
              "distance_source_sha256": _DISTANCE_SHA256, "retrieval_source_sha256": _SOURCE_SHA256,
              "numeric_convention": "q18_normalized_coordinates_exact_fraction_final_q18_half_even",
              "tie_break": "distance_q18_then_context_id", "clipping": "none",
              "source_assurance": "imported_file_bytes_not_external_runtime_attestation"}
    method["method_id"] = "mmfittedmethod_" + sha256(cohort.canonical(method)).hexdigest()
    # The source owner reports actual construction separately from reproducible
    # index content. Keep that wall clock out of the ranking identity as well.
    index_content = {key: item for key, item in index.items() if key not in
                     ("normalizer_construction", "construction_envelope_included_in_index_identity")}
    value = {"schema": SCHEMA, "method": method, "index_id": index["index_id"],
             "index_content_sha256": sha256(cohort.canonical(index_content)).hexdigest(),
             "construction_envelope_included_in_selection_identity": False,
             "membership_sha256": audit["membership_sha256"], "query": audit["query"],
             "query_owner": audit["query_owner"], "query_coordinates": coordinates,
             "accounting": audit["accounting"], "requested_k": k, "selected": selected,
             "denominator": {**audit["denominator"], "returned": len(selected)},
             "status": "MATCHES" if selected else "ABSTAINED",
             "reason": "fitted_contextual_neighbors" if selected else "no_comparable_eligible_episode",
             "coverage": audit["coverage"], "audit": audit["audit"],
             "claims": {**audit["claims"], "normalization_parameters_fitted": True,
                        "operational_study_admission": False,
                        "historical_fit_existence_authenticated": False,
                        "historical_index_existence_authenticated": False},
             "authority": audit["authority"]}
    value["selection_sha256"] = sha256(cohort.canonical(value)).hexdigest()
    value["retrieval_id"] = "mmfittedretrieval_" + value["selection_sha256"]
    body = cohort.canonical(value)
    _require(len(body) <= MAX_RESULT_BYTES, "fitted_retrieval_byte_limit")
    result = FittedRetrievalCapability(body, normalizer, native, _key=_TOKEN)
    disclose_fitted_retrieval(result, policy=policy)
    return result


def disclose_fitted_retrieval(capability, *, policy):
    _require(type(capability) is FittedRetrievalCapability and capability._seal is _TOKEN
             and type(capability._body) is bytes and len(capability._body) <= MAX_RESULT_BYTES
             and sha256(capability._body).hexdigest() == capability._digest,
             "owner_verified_fitted_retrieval_required")
    normal = fitted.disclose_fitted_normalizer(capability._normalizer, policy=policy)
    audit = baseline.disclose_episode_retrieval(capability._eligibility, policy=policy)
    value = json.loads(capability._body)
    _require(value["method"]["normalizer_id"] == normal["normalizer_id"]
             and value["accounting"] == audit["accounting"]
             and value["query"] == audit["query"]
             and value["membership_sha256"] == audit["membership_sha256"],
             "original_fitted_retrieval_changed")
    # Both selected training and complete comparison pool remain current. This
    # includes candidates not returned by either ranking and the query itself.
    fitted.disclose_fitted_normalizer(capability._normalizer, policy=policy)
    return value
