"""Exhaustive contextual retrieval over a complete original trusted cohort.

No outcomes, fitting, production activation or independent-sample claim.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_comparison as comparison
from engine.neuralweb import market_memory_retained_context_cohort as cohort

SCHEMA = "market_memory.episode_retrieval.v1"
MAX_K = 32
MAX_RESULT_BYTES = 2 * 1024 * 1024
_TOKEN = object()
_IMPORTED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
_IMPORTED_DEPENDENCY_SHA256 = {name: sha256(Path(module.__file__).read_bytes()).hexdigest()
                               for name, module in (("P1", features), ("comparator", comparison))}


class EpisodeRetrievalError(ValueError):
    """Registered contextual retrieval input or qualification refused."""


@dataclass(frozen=True, slots=True)
class RetainedContextMethodSpec:
    """Immutable pre-label exclusion identity, not external admission proof."""
    purge_calendar_days: int
    embargo_calendar_days: int
    mode: str

    def __post_init__(self):
        if any(type(v) is not int or not 0 <= v <= 366
               for v in (self.purge_calendar_days, self.embargo_calendar_days)):
            raise EpisodeRetrievalError("finite_registered_day_parameters_required")
        if self.mode not in ("historical_hypothetical", "current_contextual_support"):
            raise EpisodeRetrievalError("explicit_contextual_mode_required")

    def disclosure(self) -> dict:
        descriptor = features.fixed_comparison_descriptor()
        if (_IMPORTED_DEPENDENCY_SHA256["P1"] != "c80ba0a39e42b62e3bd687301fdc974d18f935b584b7f0b462b753ccf044530a"
                or _IMPORTED_DEPENDENCY_SHA256["comparator"] != "b8f210124ecc0a6f8a8a4f222fb3053d7a6cf88f5c73210b7b5be34285b81a95"):
            raise EpisodeRetrievalError("registered_dependency_source_mismatch")
        value = {"method": descriptor["method"], "descriptor_id": descriptor["descriptor_id"],
                 "numeric_convention": descriptor["numeric_convention"],
                 "grouping": cohort.GROUPING, "representative_before_quality_filter": True,
                 "purge_calendar_days": self.purge_calendar_days,
                 "embargo_calendar_days": self.embargo_calendar_days, "mode": self.mode,
                 "P1_source_sha256": "c80ba0a39e42b62e3bd687301fdc974d18f935b584b7f0b462b753ccf044530a",
                 "comparator_source_sha256": "b8f210124ecc0a6f8a8a4f222fb3053d7a6cf88f5c73210b7b5be34285b81a95",
                 "cohort_source_ref": cohort.source_identity(),
                 "retrieval_source_ref": {"module": "engine/neuralweb/market_memory_episode_retrieval.py",
                                          "sha256": _IMPORTED_SOURCE_SHA256,
                                          "assurance": "source_file_bytes_at_import_not_external_runtime_attestation"},
                 "label_interval_coverage": "not_established", "fit_status": "not_performed",
                 "operational_registration_admitted": False}
        return {**value, "method_spec_id": "mmretainedmethod_" + sha256(cohort.canonical(value)).hexdigest()}


@dataclass(frozen=True, slots=True, init=False)
class EpisodeRetrievalCapability:
    _body: bytes
    _digest: str
    _cohort: cohort.RetainedContextCohortCapability
    _query: features.EpisodeFeatureCapability
    _compared: tuple[features.EpisodeFeatureCapability, ...]
    _seal: object

    def __init__(self, body, population, query, selected, *, _key=None):
        if _key is not _TOKEN:
            raise EpisodeRetrievalError("owner_verified_retrieval_capability_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_cohort", population)
        object.__setattr__(self, "_query", query)
        object.__setattr__(self, "_compared", selected)
        object.__setattr__(self, "_seal", _TOKEN)


def retrieve_retained_contexts(
    population: cohort.RetainedContextCohortCapability,
    query: features.EpisodeFeatureCapability, *, policy: object,
    k: int, method: RetainedContextMethodSpec,
) -> EpisodeRetrievalCapability:
    if type(k) is not int or not 1 <= k <= MAX_K:
        raise EpisodeRetrievalError("finite_positive_k_required")
    if type(method) is not RetainedContextMethodSpec:
        raise EpisodeRetrievalError("immutable_registered_method_spec_required")
    method_value = method.disclosure()
    value = cohort.disclose_retained_context_cohort(population, policy=policy)
    query_value = features.disclose_episode_features(query, policy=policy, for_comparison=True)
    if (value["owner"]["subject_id"] != query_value["owner"]["subject_id"]
            or cohort.utc_instant(value["owner"]["query_cutoff"])
            != cohort.utc_instant(query_value["owner"]["query_cutoff"])):
        raise EpisodeRetrievalError("query_subject_or_cutoff_mismatch")
    try:
        query_session = date.fromisoformat(query_value["measurement_period"]["value"])
    except (TypeError, ValueError) as exc:
        raise EpisodeRetrievalError("query_source_session_unknown") from exc
    projections = cohort.read_cohort_feature_capabilities(population, policy=policy)
    accounting: list[dict] = []
    distances: list[tuple[dict, features.EpisodeFeatureCapability]] = []
    for row, projection in zip(value["rows"], projections, strict=True):
        reason = row["status"]
        if reason in ("representative", "representative_coordinates_unavailable"):
            session = date.fromisoformat(row["source_session"])
            days = (session - query_session).days
            if row["context_id"] == query_value["context_id"]:
                reason = "query_self"
            elif session == query_session:
                reason = "query_episode"
            elif -method.purge_calendar_days <= days < 0:
                reason = "registered_purge"
            elif 0 < days <= method.embargo_calendar_days:
                reason = "registered_embargo"
            elif row["status"] == "representative_coordinates_unavailable":
                reason = "registered_coordinates_unavailable"
            else:
                # Exact typed P1 capabilities only. The frozen comparator checks
                # current purpose rights before math and again before returning.
                record = comparison.compare_episode_features(query, projection, policy=policy)
                if record["candidate"]["context_id"] != row["context_id"]:
                    raise EpisodeRetrievalError("candidate_context_closure_mismatch")
                distances.append((record, projection))
                reason = "numerically_eligible"
        accounting.append({"context_id": row["context_id"], "capture_id": row["capture_id"],
                           "reason": reason})
    distances.sort(key=lambda item: comparison.comparison_order_key(item[0]))
    chosen = distances[:k]
    selection = {"method_spec": method_value, "requested_k": k,
                 "query": {name: query_value[name] for name in
                           ("projection_id", "context_id", "capture_id", "packet_sha256")},
                 "query_owner": query_value["owner"], "membership_sha256": value["membership_sha256"],
                 "accounting": accounting, "selected": [item[0] for item in chosen]}
    # Bind original source identities and registered math, independently of
    # policy-at-projection provenance embedded in P1/comparison identifiers.
    stable_selection = {**selection,
        "query": {key: item for key, item in selection["query"].items()
                  if key != "projection_id"},
        "selected": [{key: item for key, item in record.items()
                      if key not in ("comparison_id", "query", "candidate")}
                     | {"query": {key: item for key, item in record["query"].items()
                                  if key != "projection_id"},
                        "candidate": {key: item for key, item in record["candidate"].items()
                                      if key != "projection_id"}}
                     for record, _projection in chosen],
    }
    digest = sha256(cohort.canonical(stable_selection)).hexdigest()
    result = {"schema": SCHEMA, **selection, "selection_sha256": digest,
              "retrieval_id": "mmretainedretrieval_" + digest,
              "denominator": {"expected_captures": value["expected_capture_count"],
                              "accounted_captures": len(accounting),
                              "eligible_representatives": len(distances), "returned": len(chosen)},
              "status": "MATCHES" if chosen else "ABSTAINED",
              "reason": "fixed_contextual_neighbors" if chosen else "no_comparable_eligible_episode",
              "coverage": "complete_for_exact_trusted_generation_only",
              "audit": {"cohort_id": value["cohort_id"], "original_owner": value["owner"],
                        "capture_receipt_sha256": [row["capture_receipt_sha256"] for row in value["rows"]]},
              "claims": {"fit_eligible": False, "training_eligible": False, "promotion_eligible": False,
                         "component_source_receipts_authenticated": False,
                         "retrieval_usage_admitted": False, "evaluation_performed": False,
                         "effective_n": "not_estimated", "independent_episode_count": "not_established",
                         "W2C_timely_admission": False}, "authority": dict(mm.AUTHORITY)}
    body = cohort.canonical(result)
    if len(body) > MAX_RESULT_BYTES:
        raise EpisodeRetrievalError("retrieval_result_byte_bound_exceeded")
    capability = EpisodeRetrievalCapability(body, population, query, tuple(item[1] for item in distances), _key=_TOKEN)
    disclose_episode_retrieval(capability, policy=policy)
    return capability


def disclose_episode_retrieval(capability: EpisodeRetrievalCapability, *, policy: object) -> dict:
    if (type(capability) is not EpisodeRetrievalCapability or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > MAX_RESULT_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise EpisodeRetrievalError("owner_verified_retrieval_capability_required")
    cohort.disclose_retained_context_cohort(capability._cohort, policy=policy)
    features.disclose_episode_features(capability._query, policy=policy, for_comparison=True)
    # Counts/ordering depend on the whole comparison pool, including unreturned rows.
    for selected in capability._compared:
        features.disclose_episode_features(selected, policy=policy, for_comparison=True)
    return json.loads(capability._body)
