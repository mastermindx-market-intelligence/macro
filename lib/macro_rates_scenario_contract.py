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

import copy
from datetime import date, datetime, timezone
import math
import re
from typing import Any, Mapping

from engine.market_os.macro_workspaces import contract, rates_curves as owner

REQUEST_SCHEMA = "ontology_scenario_request.v2"
RESULT_SCHEMA = "mastermind.macro_workspace_scenario_result.v1"
PUBLICATION_CONTRACT = "mastermind.macro_workspace_snapshot.v1@1.0.0"
SOURCE_SCHEMA = "mastermind.macro_rates_scenario_source.v1"
EXECUTION_VERSION = "1.1.0"
_ARTIFACT_PATH = "macrodata/workspaces/rates_curves/US/latest.json"
_MANIFEST_PATH = "macrodata/workspaces/manifest.json"
_MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


class RatesScenarioContractError(ValueError):
    """Closed refusal token; never includes private assumptions or source data."""


class RatesScenarioUnavailable(ValueError):
    """Source availability only; never an entitlement or identity decision."""


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


def _publication_identity(value: Any, *, snapshot_content_sha256: str) -> dict:
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
    if (content != snapshot_content_sha256 or artifact["path"] != _ARTIFACT_PATH
            or artifact["manifest_path"] != _MANIFEST_PATH
            or not contract.supported_client_contract(artifact["min_client_contract"])
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
        if instant.tzinfo is None:
            raise ValueError("publication timezone unavailable")
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


def _publication(value: Any, *, baseline: owner.RatesScenarioBaseline) -> dict:
    publication = _publication_identity(value, snapshot_content_sha256=baseline.snapshot_content_sha256)
    instant = datetime.fromisoformat(publication["manifest_generated_at"].replace("Z", "+00:00"))
    latest_evidence = max(date.fromisoformat(stamp) for stamp in
                          (baseline.observed_at, *(source.latest_observed_at for source in baseline.sources)))
    if instant.astimezone(timezone.utc).date() < latest_evidence:
        raise RatesScenarioContractError("invalid_rates_publication")
    return publication


def qualify_rates_publication(snapshot: Any, publication: Any, *, expected_publication: Any = None
                              ) -> tuple[owner.RatesScenarioBaseline, dict]:
    """Qualify the server-selected source; the existing route still owns access.

    A structurally valid changed publication is reported before its disabled
    capability. Malformed metadata cannot manufacture a source-change receipt.
    Neither parsing the method nor finding two usable yields enables execution.
    """
    try:
        contract.validate(snapshot)
    except (contract.ContractError, TypeError, ValueError, OverflowError, RecursionError):
        raise RatesScenarioUnavailable("source_unavailable") from None
    if (snapshot["workspace"]["id"] != "rates_curves" or snapshot["region"]["code"] != "US"
            or snapshot["region"]["supported"] is not True
            or snapshot["generation"]["producer"] != owner.PRODUCER
            or snapshot["headline"]["method_version"] != owner.METHOD_VERSION):
        raise RatesScenarioUnavailable("source_unavailable")
    qualified = _publication_identity(publication, snapshot_content_sha256=snapshot["generation"]["content_sha256"])
    if not contract.publication_contract_supports(qualified["artifact"]["min_client_contract"],
                                                 snapshot["schema"]["version"]):
        raise RatesScenarioContractError("invalid_rates_publication")
    published = datetime.fromisoformat(qualified["manifest_generated_at"].replace("Z", "+00:00"))
    built = datetime.fromisoformat(snapshot["generation"]["built_at"].replace("Z", "+00:00"))
    if published < built:
        raise RatesScenarioContractError("invalid_rates_publication")
    if expected_publication is not None:
        expected = _closed(expected_publication, {"manifest_sha256", "snapshot_content_sha256"},
                           "invalid_rates_request")
        for key in expected:
            _digest(expected[key], "invalid_rates_request")
        if (expected["manifest_sha256"] != qualified["manifest_sha256"]
                or expected["snapshot_content_sha256"] != snapshot["generation"]["content_sha256"]):
            raise RatesScenarioContractError("source_changed")
    capability = snapshot["scenario_contract"]
    if snapshot["schema"]["version"] != EXECUTION_VERSION or capability["execution_available"] is not True:
        raise RatesScenarioUnavailable("scenario_disabled")
    # The versioned closed schema binds US Rates, method/schema identifiers and
    # exactly the two owner assumptions. Baseline extraction is still the owner.
    baseline = owner.rates_scenario_baseline(snapshot)
    return baseline, _publication(qualified, baseline=baseline)


def _baseline_projection(baseline: owner.RatesScenarioBaseline) -> dict:
    return {
        "baseline_id": baseline.baseline_id,
        "snapshot_content_sha256": baseline.snapshot_content_sha256,
        "observed_at": baseline.observed_at,
        "value_basis": "published_four_decimal_cmt_points",
        "us2y": {"value": baseline.us2y_pct, "unit": "percent"},
        "us10y": {"value": baseline.us10y_pct, "unit": "percent"},
        "curve_2s10s": {"value": baseline.observed_spread_bp, "unit": "bp"},
        "sources": [{field: getattr(source, field) for field in owner.RatesScenarioSource.__dataclass_fields__}
                    for source in baseline.sources],
    }


def rates_scenario_source(snapshot: Any, publication: Any) -> dict:
    """Optional selected-GET projection: source-qualified is not access-granted.

    No calculation, entitlement lookup, request, side effect or remembered
    baseline. A failed scenario projection does not hide the ordinary reading.
    """
    common = {"schema": SOURCE_SCHEMA,
              "access": {"required_feature": "site_full", "state": "not_checked"}}
    try:
        baseline, qualified = qualify_rates_publication(snapshot, publication)
        preview = _baseline_projection(baseline)
    except RatesScenarioUnavailable as exc:
        disabled = str(exc) == "scenario_disabled"
        return {**common, "source_state": "disabled" if disabled else "unavailable",
                "reason": "publication_disabled" if disabled else "source_unavailable"}
    except (RatesScenarioContractError, owner.RatesScenarioBaselineError,
            TypeError, ValueError, OverflowError, RecursionError):
        return {**common, "source_state": "unavailable", "reason": "source_unavailable"}
    return {
        **common, "source_state": "qualified", "snapshot_version": EXECUTION_VERSION,
        "method": owner.RATES_SCENARIO_METHOD, "request_schema": REQUEST_SCHEMA,
        "result_schema": RESULT_SCHEMA,
        "assumptions": copy.deepcopy(snapshot["scenario_contract"]["assumptions"]),
        "publication": qualified, "baseline": preview,
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
    return {
        "schema": RESULT_SCHEMA, "method": result.method_version,
        "status": "MECHANICAL_CALCULATION", "workspace_id": "rates_curves", "region": "US",
        "calculation_id": result.calculation_id,
        "assumptions": dict(request["assumptions"]),
        "publication": publication,
        "baseline": _baseline_projection(baseline),
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
