"""Closed Rates request/result preparation for the incumbent scenario service.

Pure normalization and serialization: no HTTP dispatch, file read, clock, auth,
publication, cache or write. The existing private transport still owns its byte
bound and duplicate-key parser. Its v1 WTI/real-10Y branch is not changed here.

The assigning runtime MUST obtain the snapshot and publication metadata through
the incumbent secured Macro reader, extract the baseline from that snapshot,
and recheck the publication after evaluation. A mapping that passes structural
checks here is not proof that bytes were served, current, licensed or available
at a historical knowledge cutoff. Never accept publication/calculation objects
from an HTTP body. Only ``normalize_rates_request`` consumes client fields.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import math
import re
from typing import Any, Mapping

from engine.market_os.macro_workspaces import contract, rates_curves as owner

REQUEST_SCHEMA = "ontology_scenario_request.v2"
RESULT_SCHEMA = "mastermind.macro_workspace_scenario_result.v1"
PUBLICATION_CONTRACT = "mastermind.macro_workspace_snapshot.v1@1.0.0"
_ARTIFACT_PATH = "macrodata/workspaces/rates_curves/US/latest.json"
_MANIFEST_PATH = "macrodata/workspaces/manifest.json"
_MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


class RatesScenarioContractError(ValueError):
    """Closed refusal token; never includes private assumptions or source data."""


def _closed(value: Any, fields: set[str], reason: str) -> Mapping:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise RatesScenarioContractError(reason)
    return value


def _digest(value: Any, reason: str) -> str:
    if (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            or value == "0" * 64):
        raise RatesScenarioContractError(reason)
    return value


def normalize_rates_request(payload: Any) -> dict:
    """Normalize the future v2 branch after the existing private JSON parser.

    The two expected digests are comparison expectations, never an authorization
    or baseline. Workspace and region are fixed by the exact owner method.
    """
    reason = "invalid_rates_request"
    payload = _closed(payload, {"schema", "method", "expected_publication", "assumptions"}, reason)
    if payload["schema"] != REQUEST_SCHEMA or payload["method"] != owner.RATES_SCENARIO_METHOD:
        raise RatesScenarioContractError(reason)
    expected = _closed(payload["expected_publication"],
                       {"manifest_sha256", "snapshot_content_sha256"}, reason)
    manifest = _digest(expected["manifest_sha256"], reason)
    content = _digest(expected["snapshot_content_sha256"], reason)
    try:
        shifts = owner.parse_rates_yield_shifts(payload["assumptions"])
    except owner.RatesScenarioInputError:
        raise RatesScenarioContractError(reason) from None
    return {
        "schema": REQUEST_SCHEMA,
        "method": owner.RATES_SCENARIO_METHOD,
        "expected_publication": {"manifest_sha256": manifest, "snapshot_content_sha256": content},
        "assumptions": {"us2y_bp": shifts.us2y_bp, "us10y_bp": shifts.us10y_bp},
    }


def _publication(value: Any, *, baseline: owner.RatesScenarioBaseline) -> dict:
    """Check caller-supplied reader metadata without creating a receipt.

    In the incumbent artifact vocabulary, ``artifact.sha256`` is the canonical
    content digest, NOT a raw-file digest. ``manifest_sha256`` binds raw manifest
    bytes. The generation label is checked for consistency, not promoted to a
    separate proof of currentness. Missing context cannot serialize success.
    """
    reason = "invalid_rates_publication"
    value = _closed(value, {"manifest_sha256", "manifest_generated_at", "generation_id", "artifact"}, reason)
    manifest = _digest(value["manifest_sha256"], reason)
    artifact = _closed(value["artifact"],
                       {"path", "manifest_path", "sha256", "bytes", "min_client_contract"}, reason)
    content = _digest(artifact["sha256"], reason)
    if (content != baseline.snapshot_content_sha256 or artifact["path"] != _ARTIFACT_PATH
            or artifact["manifest_path"] != _MANIFEST_PATH
            or artifact["min_client_contract"] != PUBLICATION_CONTRACT
            or type(artifact["bytes"]) is not int
            or not 0 < artifact["bytes"] <= _MAX_SNAPSHOT_BYTES):
        raise RatesScenarioContractError(reason)
    generation = contract.derive_generation_id(
        {"workspace": {"id": "rates_curves"}, "region": {"code": "US"}}, content)
    if value["generation_id"] != generation:
        raise RatesScenarioContractError(reason)
    stamp = value["manifest_generated_at"]
    if (not isinstance(stamp, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", stamp)):
        raise RatesScenarioContractError(reason)
    try:
        instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        latest_evidence = max(date.fromisoformat(stamp) for stamp in
                              (baseline.observed_at, *(source.latest_observed_at for source in baseline.sources)))
        if instant.astimezone(timezone.utc).date() < latest_evidence:
            raise ValueError("observation after publication")
    except (TypeError, ValueError, OverflowError):
        raise RatesScenarioContractError(reason) from None
    return {
        "manifest_sha256": manifest,
        "manifest_generated_at": stamp,
        "generation_id": generation,
        "artifact": {
            "path": artifact["path"], "manifest_path": artifact["manifest_path"],
            "sha256": content, "bytes": artifact["bytes"],
            "min_client_contract": artifact["min_client_contract"],
        },
    }


def _calculation(value: Any, assumptions: Mapping) -> owner.RatesScenarioCalculation:
    reason = "invalid_rates_calculation"
    if (type(value) is not owner.RatesScenarioCalculation
            or type(value.assumptions) is not owner.RatesYieldShifts
            or type(value.assumptions.us2y_bp) is not int or type(value.assumptions.us10y_bp) is not int
            or value.display_only is not True
            or any(getattr(value, field) is not False for field in
                   ("can_rank", "can_gate", "can_size", "can_originate_signal", "can_execute"))
            or any(type(getattr(value, field)) is not int or getattr(value, field) != 0 for field in
                   ("canonical_writes", "alert_writes", "portfolio_writes", "calibration_writes"))
            or type(value.spread_change_bp) is not int or type(value.unsupported_effects) is not tuple):
        raise RatesScenarioContractError(reason)
    for field in ("observed_spread_bp", "assumed_us2y_pct", "assumed_us10y_pct", "assumed_spread_bp"):
        number = getattr(value, field)
        try:
            valid = type(number) in (int, float) and math.isfinite(number)
        except (ValueError, OverflowError):
            valid = False
        if not valid:
            raise RatesScenarioContractError(reason)
    try:
        # Reuse the owner's baseline checks, arithmetic and identity algorithm.
        # Contradictory flags or values must be rejected, never overwritten by
        # harmless-looking serialization constants.
        expected = owner.evaluate_rates_scenario(value.baseline, assumptions)
    except (owner.RatesScenarioInputError, owner.RatesScenarioBaselineError, TypeError, ValueError, OverflowError):
        raise RatesScenarioContractError(reason) from None
    if value != expected:
        raise RatesScenarioContractError(reason)
    return value


def serialize_rates_result(request: Any, calculation: Any, *, publication: Any) -> dict:
    """Project one consistent owner result with explicit publication context.

    ``source_changed`` maps to the incumbent runtime's 409 in the later service
    integration. This pure function does not itself perform a before/after read,
    authenticate a request, admit execution or establish a serving receipt.
    """
    request = normalize_rates_request(request)
    result = _calculation(calculation, request["assumptions"])
    baseline = result.baseline
    publication = _publication(publication, baseline=baseline)
    expected = request["expected_publication"]
    if (expected["manifest_sha256"] != publication["manifest_sha256"]
            or expected["snapshot_content_sha256"] != baseline.snapshot_content_sha256):
        raise RatesScenarioContractError("source_changed")
    sources = [{
        "series_id": source.series_id, "source_id": source.source_id,
        "source_ref": source.source_ref, "artifact_ref": source.artifact_ref,
        "owner_ref": source.owner_ref, "unit": source.unit, "basis": source.basis,
        "latest_observed_at": source.latest_observed_at, "freshness": source.freshness,
        "rights_state": source.rights_state,
    } for source in baseline.sources]
    return {
        "schema": RESULT_SCHEMA, "method": result.method_version,
        "status": "MECHANICAL_CALCULATION", "workspace_id": "rates_curves", "region": "US",
        "calculation_id": result.calculation_id,
        "assumptions": dict(request["assumptions"]),
        "publication": publication,
        "baseline": {
            "baseline_id": baseline.baseline_id,
            "snapshot_content_sha256": baseline.snapshot_content_sha256,
            "observed_at": baseline.observed_at,
            "value_basis": "published_four_decimal_cmt_points",
            "us2y": {"value": baseline.us2y_pct, "unit": "percent"},
            "us10y": {"value": baseline.us10y_pct, "unit": "percent"},
            "curve_2s10s": {"value": result.observed_spread_bp, "unit": "bp"},
            "sources": sources,
        },
        "assumed": {
            "us2y": {"value": result.assumed_us2y_pct, "unit": "percent"},
            "us10y": {"value": result.assumed_us10y_pct, "unit": "percent"},
            "curve_2s10s": {"value": result.assumed_spread_bp, "unit": "bp"},
            "spread_change": {"value": result.spread_change_bp, "unit": "bp"},
        },
        "unsupported_effects": list(result.unsupported_effects),
        "authority": {
            "display_only": result.display_only, "can_rank": result.can_rank,
            "can_gate": result.can_gate, "can_size": result.can_size,
            "can_originate_signal": result.can_originate_signal, "can_execute": result.can_execute,
        },
        "effects": {
            "canonical_writes": result.canonical_writes, "alert_writes": result.alert_writes,
            "portfolio_writes": result.portfolio_writes, "calibration_writes": result.calibration_writes,
        },
    }
