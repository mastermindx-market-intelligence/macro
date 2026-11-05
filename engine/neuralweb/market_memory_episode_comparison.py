"""One fixed house-state comparison, without population selection or fitting.

P1 q18 coordinates are validated against retained exact binary64 provenance
before fixed Decimal L1 arithmetic. Only the final distance is rounded again.
This kernel grants no corpus, source usage, evaluation or prediction admission.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from hashlib import sha256

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_features as features

SCHEMA = "market_memory.episode_comparison.v1"
_Q18 = Decimal("1e-18")
_NUMERIC = ("growth_score", "inflation_score")
_CATEGORIES = {
    "quad": ("Q1", "Q2", "Q3", "Q4"),
    "liquidity_overlay": ("expanding", "neutral", "contracting"),
    "cycle_tag": ("early", "mid", "late"),
}
_CONTEXT = re.compile(r"mmctx_[a-f0-9]{64}\Z")
_DECIMAL = re.compile(r"-?[01]\.\d{18}\Z")


class EpisodeComparisonError(ValueError):
    """Comparison refused: invalid provenance, profile or registered coordinate."""


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _coordinates(value: dict, descriptor: dict) -> dict[str, Decimal | str]:
    if (value["descriptor_ref"] != {"descriptor_id": descriptor["descriptor_id"],
                                   "content_sha256": descriptor["content_sha256"]}
            or value["source_feature_id"] != "macro.regime_state"
            or value["source_transform_version"] != "market_memory.macro_regime_transform.v1"):
        raise EpisodeComparisonError("registered_descriptor_or_source_mismatch")
    rows = value["coordinates"]
    expected = [*_NUMERIC, *_CATEGORIES]
    if type(rows) is not list or len(rows) != 5 or [row["id"] for row in rows] != expected:
        raise EpisodeComparisonError("registered_coordinate_set_mismatch")
    coordinates: dict[str, Decimal | str] = {}
    for row in rows:
        name = row["id"]
        if row["status"] != "observed":
            raise EpisodeComparisonError("registered_coordinate_unavailable")
        if name in _NUMERIC:
            if (row["kind"] != "numeric" or row["unit"] != "dimensionless_house_regime_score"
                    or type(row["value_q18"]) is not str or not _DECIMAL.fullmatch(row["value_q18"])):
                raise EpisodeComparisonError("registered_numeric_unit_or_encoding_mismatch")
            try:
                if type(row["source_binary64_hex"]) is not str:
                    raise ValueError("binary64 hex required")
                binary = float.fromhex(row["source_binary64_hex"])
                exact = Decimal.from_float(binary)
                if (not exact.is_finite() or not Decimal(-1) <= exact <= Decimal(1)
                        or binary.hex() != row["source_binary64_hex"]
                        or format(exact, "f") != row["source_exact_decimal"]):
                    raise ValueError("original binary64 provenance mismatch")
                with localcontext(features.fixed_decimal_context()):
                    registered = exact.quantize(_Q18, rounding=ROUND_HALF_EVEN)
                if format(registered, ".18f") != row["value_q18"]:
                    raise ValueError("registered q18 conversion mismatch")
            except (ValueError, TypeError, OverflowError) as exc:
                raise EpisodeComparisonError("source_coordinate_provenance_mismatch") from exc
            coordinates[name] = registered
        else:
            if (row["kind"] != "categorical" or row["unit"] != "category"
                    or row["value"] not in _CATEGORIES[name]):
                raise EpisodeComparisonError("registered_category_mismatch")
            coordinates[name] = row["value"]
    return coordinates


def compare_episode_features(
    query: features.EpisodeFeatureCapability,
    candidate: features.EpisodeFeatureCapability,
    *, policy: features.EpisodeFeaturePolicy,
) -> dict:
    """Compare exact typed owner capabilities with current purpose authorization.

    No outcomes, population, fitted normalizer or caller feature dictionaries
    are inputs. R2 must separately bind the cohort, exclusions and registration.
    """
    query_value = features.disclose_episode_features(query, policy=policy, for_comparison=True)
    candidate_value = features.disclose_episode_features(candidate, policy=policy, for_comparison=True)
    if query_value["owner"]["subject_id"] != candidate_value["owner"]["subject_id"]:
        raise EpisodeComparisonError("comparison_subject_mismatch")
    if (datetime.fromisoformat(query_value["owner"]["query_cutoff"].replace("Z", "+00:00"))
            != datetime.fromisoformat(candidate_value["owner"]["query_cutoff"].replace("Z", "+00:00"))):
        raise EpisodeComparisonError("comparison_cutoff_mismatch")
    descriptor = features.fixed_comparison_descriptor()
    left, right = _coordinates(query_value, descriptor), _coordinates(candidate_value, descriptor)
    with localcontext(features.fixed_decimal_context()):
        components = {name: abs(left[name] - right[name]) / Decimal(2) for name in _NUMERIC}
        components.update({name: Decimal(left[name] != right[name]) for name in _CATEGORIES})
        distance = (sum(components.values(), Decimal(0)) / Decimal(5)).quantize(
            _Q18, rounding=ROUND_HALF_EVEN)
    value = {
        "schema": SCHEMA, "method": descriptor["method"],
        "descriptor_ref": {"descriptor_id": descriptor["descriptor_id"],
                           "content_sha256": descriptor["content_sha256"]},
        "numeric_convention": descriptor["numeric_convention"],
        "arithmetic": "validated_q18_coordinates_decimal80_L1_final_q18_half_even",
        "query": {key: query_value[key] for key in ("projection_id", "context_id", "capture_id", "packet_sha256")},
        "candidate": {key: candidate_value[key] for key in ("projection_id", "context_id", "capture_id", "packet_sha256")},
        "query_owner": query_value["owner"], "candidate_owner": candidate_value["owner"],
        "query_feature_snapshot": query_value["feature_snapshot"],
        "candidate_feature_snapshot": candidate_value["feature_snapshot"],
        "components_exact_decimal": {name: format(term, "f") for name, term in components.items()},
        "distance_q18": format(distance, ".18f"),
        "fit_status": "not_performed", "fit_eligible": False,
        "training_eligible": False, "promotion_eligible": False,
        "scope": "single_house_output_comparison_no_population_or_retrieval_admission",
        "authority": dict(mm.AUTHORITY),
    }
    value["comparison_id"] = "mmepisodecomparison_" + sha256(_canonical(value)).hexdigest()
    # Recheck current rights at the final boundary; a revoked comparison must
    # not escape merely because its arithmetic completed under earlier rights.
    features.disclose_episode_features(query, policy=policy, for_comparison=True)
    features.disclose_episode_features(candidate, policy=policy, for_comparison=True)
    return value


def comparison_order_key(value: dict) -> tuple[Decimal, str]:
    """Registered stable tie rule for already authorized comparison records.

    This structural utility does not authenticate sources or grant ranking use.
    """
    distance = value.get("distance_q18")
    context_id = value.get("candidate", {}).get("context_id")
    if (type(distance) is not str or not _DECIMAL.fullmatch(distance)
            or not Decimal(0) <= Decimal(distance) <= Decimal(1)
            or type(context_id) is not str or not _CONTEXT.fullmatch(context_id)):
        raise EpisodeComparisonError("invalid_comparison_order_value")
    return Decimal(distance), context_id
