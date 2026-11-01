"""Bounded current-Options observation adapter for PTSE research v1.

Pure / zero-I/O. This module does not own an Options collector, store, publisher,
history, lifecycle, ranker, model, gate, sizing, execution, or trading effect.

It consumes only current options_hub.vol/v1 and options_hub.gex/v1 payloads
after the caller supplies exact owner artifact identity, known-at clocks, expiry,
evidence grade, and a separate root-to-security identity receipt.

Each artifact digest binds its entire supplied Mapping using the owner adapter's
canonical parsed-JSON convention, including unprojected arrays and metadata.
This does not assert raw source-file byte identity or external owner admission.

The October 2 Theta EOD 60-cell receipt is inherited as a LIMIT on claims:
historical PIT is unproven, no contrast repeats a BH rejection across all three
eras, GEX was tested against forward realized volatility rather than return,
and walls were not registered in that study. None of those retrospective
findings is promoted into a live score or authority bit here.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Final, Mapping

from research.options_estate.ptse_contract import OwnerFact
from research.options_estate.ptse_owner_observation import (
    OwnerArtifactBinding,
    PTSEOwnerAdapterError,
    _path,
    _ref_shape,
    _validate_binding,
    _validate_payload_binding,
)


@dataclass(frozen=True)
class OptionsRootBinding:
    root: str
    security_id: str
    identity_ref: Mapping[str, str]


_VOL_FIELDS: Final = (
    ("options.vol.iv_rank_252", ("iv_rank_252",), "PERCENT", "DETERMINISTIC_COMPUTATION"),
    ("options.vol.iv_rank_all", ("iv_rank_all",), "PERCENT", "DETERMINISTIC_COMPUTATION"),
    ("options.vol.atm_iv", ("atm_iv",), "PERCENT", "DETERMINISTIC_COMPUTATION"),
    ("options.vol.rv20", ("rv20",), "PERCENT", "DETERMINISTIC_COMPUTATION"),
    ("options.vol.coverage_days_all", ("coverage_days_all",), "COUNT", "DETERMINISTIC_COMPUTATION"),
)

_GEX_FIELDS: Final = (
    ("options.gex.spot_ref", ("spot_ref",), "POINTS", "OBSERVATION"),
    ("options.gex.gamma_flip", ("gamma_flip",), "POINTS", "DETERMINISTIC_COMPUTATION"),
    ("options.gex.call_wall", ("call_wall",), "POINTS", "DETERMINISTIC_COMPUTATION"),
    ("options.gex.put_wall", ("put_wall",), "POINTS", "DETERMINISTIC_COMPUTATION"),
    ("options.gex.contract_count", ("coverage", "n_contracts"), "COUNT", "DETERMINISTIC_COMPUTATION"),
)

_VOL_KEYS: Final = frozenset({
    "schema", "asof", "root", "iv_rank_252", "iv_rank_all", "coverage_days_all",
    "since_all", "atm_iv", "iv_52w_hi", "iv_52w_lo", "rv20", "vrp", "term",
    "smile", "history", "coverage",
})

_GEX_KEYS: Final = frozenset({
    "schema", "asof", "root", "spot_ref", "net_gex_bn", "gamma_flip", "profile",
    "call_wall", "put_wall", "by_strike", "by_strike_full_n", "by_delta",
    "by_delta_full_n", "by_expiry", "convention", "coverage", "history",
})


def _fail(code: str) -> None:
    raise PTSEOwnerAdapterError(code)


def _validate_number(value: Any, unit: str, feature_id: str) -> None:
    if unit == "COUNT":
        if type(value) is not int or value < 0:
            _fail("OPTIONS_VALUE_RANGE_INVALID")
        return
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        _fail("OPTIONS_VALUE_TYPE_INVALID")
    number = float(value)
    if unit == "PERCENT":
        # Incumbent options_hub emits annualized ATM IV and realized volatility
        # in percent (decimal volatility * 100), not percentile ranks. These
        # can exceed 100. Only the two empirical IV ranks have a 100 ceiling.
        ranked = feature_id in {"options.vol.iv_rank_252", "options.vol.iv_rank_all"}
        if number < 0 or (ranked and number > 100):
            _fail("OPTIONS_VALUE_RANGE_INVALID")
    if unit == "POINTS" and number <= 0:
        _fail("OPTIONS_VALUE_RANGE_INVALID")


def _validate_root(
    payload: Mapping[str, Any],
    binding: OwnerArtifactBinding,
    root_binding: OptionsRootBinding,
    *,
    market_session: str,
) -> None:
    if not isinstance(root_binding.root, str) or not root_binding.root:
        _fail("OPTIONS_ROOT_IDENTITY_INVALID")
    if not isinstance(root_binding.security_id, str) or not root_binding.security_id:
        _fail("OPTIONS_ROOT_IDENTITY_INVALID")
    identity_ref = _ref_shape(root_binding.identity_ref)
    if payload.get("root") != root_binding.root:
        _fail("OPTIONS_ROOT_MISMATCH")
    if payload.get("asof") != market_session:
        _fail("OPTIONS_SESSION_MISMATCH")
    if binding.instrument_id != root_binding.security_id:
        _fail("OPTIONS_SECURITY_MISMATCH")
    if binding.population_ref != identity_ref:
        _fail("OPTIONS_ROOT_IDENTITY_REF_MISMATCH")


def _bounded_fact(
    *,
    feature_id: str,
    value: Any,
    unit: str,
    method_kind: str,
    binding: OwnerArtifactBinding,
    stale: bool,
    limitations: tuple[str, ...],
) -> OwnerFact:
    present = value is not None
    if present:
        _validate_number(value, unit, feature_id)
        status = "STALE" if stale else "OBSERVED"
        known_at = {
            "earliest": binding.known_at_earliest,
            "latest": binding.known_at_latest,
            "precision": binding.known_at_precision,
            "evidence_ref": _ref_shape(binding.known_at_evidence_ref),
        }
        coverage = {
            "numerator": 1,
            "denominator": 1,
            "missing_count": 0,
            "population_ref": _ref_shape(binding.population_ref),
        }
        null_reason = "SOURCE_EXPIRED_AT_DECISION" if stale else None
    else:
        status = "UNAVAILABLE"
        known_at = None
        coverage = {
            "numerator": 0,
            "denominator": 1,
            "missing_count": 1,
            "population_ref": _ref_shape(binding.population_ref),
        }
        null_reason = "OWNER_FIELD_UNAVAILABLE"

    return {
        "feature_id": feature_id,
        "owner_ref": binding.owner_ref,
        "source_artifact_ref": _ref_shape(binding.artifact_ref),
        "economic_time": binding.economic_time,
        "economic_time_role": "OBSERVATION",
        "known_at": known_at,
        "valid_until": binding.valid_until,
        "value": value if present else None,
        "unit": unit,
        "status": status,
        "method_kind": method_kind,
        "calculation_version": binding.calculation_version,
        "evidence_grade": binding.evidence_grade,
        "coverage": coverage,
        "source_scope": {
            "instrument_id": binding.instrument_id,
            "session_scope": binding.session_scope,
            "population_ref": _ref_shape(binding.population_ref),
            "position_scope": "NOT_APPLICABLE",
            "side_semantics": "NOT_APPLICABLE",
        },
        "limitations": list(binding.limitations) + list(limitations),
        "null_reason": null_reason,
    }


def adapt_options_hub(
    *,
    market_session: str,
    decision_at: str,
    root_binding: OptionsRootBinding,
    vol: Mapping[str, Any] | None = None,
    vol_binding: OwnerArtifactBinding | None = None,
    gex: Mapping[str, Any] | None = None,
    gex_binding: OwnerArtifactBinding | None = None,
) -> list[OwnerFact]:
    """Return bounded scalar current-Options facts with null honesty."""
    if (vol is None) != (vol_binding is None):
        _fail("OPTIONS_VOL_BINDING_REQUIRED")
    if (gex is None) != (gex_binding is None):
        _fail("OPTIONS_GEX_BINDING_REQUIRED")
    if vol is None and gex is None:
        _fail("OPTIONS_SOURCE_REQUIRED")

    facts: list[OwnerFact] = []

    if vol is not None:
        stale = _validate_binding(vol_binding, decision_at=decision_at)
        if not isinstance(vol, Mapping) or set(vol) - _VOL_KEYS:
            _fail("OPTIONS_VOL_OBJECT_INVALID")
        if vol.get("schema") != "options_hub.vol/v1":
            _fail("OPTIONS_VOL_SCHEMA_INVALID")
        _validate_root(vol, vol_binding, root_binding, market_session=market_session)
        _validate_payload_binding(vol, vol_binding)
        limits = (
            "Bounded scalar projection from options_hub.vol/v1; term, smile and history rows are not copied.",
            "Current Options volatility context is descriptive only and grants no PTSE prediction or decision authority.",
            "October 2 60-cell research is retrospective/PIT-unproven; these live fields inherit none of its BH findings.",
        )
        for feature_id, keys, unit, method_kind in _VOL_FIELDS:
            _, value = _path(vol, keys)
            facts.append(_bounded_fact(
                feature_id=feature_id, value=value, unit=unit,
                method_kind=method_kind, binding=vol_binding, stale=stale,
                limitations=limits,
            ))

    if gex is not None:
        stale = _validate_binding(gex_binding, decision_at=decision_at)
        if not isinstance(gex, Mapping) or set(gex) - _GEX_KEYS:
            _fail("OPTIONS_GEX_OBJECT_INVALID")
        if gex.get("schema") != "options_hub.gex/v1":
            _fail("OPTIONS_GEX_SCHEMA_INVALID")
        _validate_root(gex, gex_binding, root_binding, market_session=market_session)
        convention = gex.get("convention")
        if convention not in (None, "dealer-sign per engine/gex_model (long-call/short-put)"):
            _fail("OPTIONS_GEX_CONVENTION_INVALID")
        _validate_payload_binding(gex, gex_binding)
        limits = (
            "Bounded scalar/geometry projection from options_hub.gex/v1; no strike, delta, expiry, profile or history rows are copied.",
            "GEX uses the incumbent long-call/short-put dealer-position scenario and is not measured whole-dealer inventory.",
            "October 2 GEX research targeted forward realized volatility, not return, and survived BH only in Era1; no stable-alpha or return inference is made.",
            "Gamma walls and flip were not separately registered in the October 2 60-cell study.",
        )
        for feature_id, keys, unit, method_kind in _GEX_FIELDS:
            _, value = _path(gex, keys)
            facts.append(_bounded_fact(
                feature_id=feature_id, value=value, unit=unit,
                method_kind=method_kind, binding=gex_binding, stale=stale,
                limitations=limits,
            ))

    facts.sort(key=lambda row: row["feature_id"])
    return facts


__all__ = ["OptionsRootBinding", "adapt_options_hub"]
