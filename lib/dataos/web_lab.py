"""Bounded web-facing adapter to the existing Technical Catalog and Lab.

``list_signals`` and ``plan`` discover/validate metadata without opening data files.
``execute`` MUST run in a dedicated, bounded worker process supplied by its caller.
It accepts already materialized, authorized DataFrames and does not load datasets,
spawn workers, maintain jobs, or persist Trial results.

Computation is NOT read-only: canonical Lab uses
TrialLedger.with_declared_budget(), which may create/append its deterministic
_declbudget_*.jsonl in tempfile.gettempdir(). The worker must set a dedicated
external-drive TMPDIR before Python starts and confine filesystem/network access.
The supplied-universe canonical backtest does not load a benchmark dataset.
A signal's own declared data requirements remain subject to the worker's input
read guards. This module never calls Trial.to_ledger().
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime
from numbers import Integral, Real
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

__all__ = ["WebLabError", "list_signals", "plan", "execute"]

_CANONICAL_FUNCTION = "engine.lab.catalog_backtest"
# Closed execution admission for the supplied-OHLCV adapter, not a signal catalog.
# New canonical modules remain discoverable until their transitive input reads are reviewed.
_PRICE_ONLY_MODULES = frozenset({"engine.ma_crosses", "engine.rsi_signals"})
_REQUEST_FIELDS = frozenset(
    {"signal_id", "refs", "horizon_bars", "cost_bps", "n_configs_searched"}
)
_LIMITATIONS = (
    "Research only. A canonical Trial verdict is not production, ranking, sizing, "
    "trading, or alert admission.",
    "The canonical Lab is long-only. This adapter accepts only catalog direction +1.",
    "A selected/current universe may be survivorship biased; the adapter does not "
    "reconstruct historical membership or certify point-in-time eligibility.",
    "Original availability, revisions, adjusted/raw price basis, corporate actions, "
    "and coverage remain the input data contract; this adapter does not infer them.",
    "horizon_bars is the forward-return IC horizon in observed bars, not a "
    "calendar-day promise or a fixed holding/exit rule.",
    "cost_bps is the canonical one-way transaction-cost input; a chosen value is "
    "not proof of actual execution costs.",
    "The declared search budget is supplied by the caller and is not verified "
    "against all previous experiments by this adapter.",
)
_WORKER_REQUIREMENTS = (
    "dedicated bounded worker process",
    "authorized input refs resolved and materialized by the guarded data reader",
    "dedicated external-drive TMPDIR configured before Python starts",
    "production datasets, secrets, runtime changes, and network access excluded",
    "signal supplemental data requirements confined to explicitly admitted inputs",
)


class WebLabError(ValueError):
    """Rejected request or unsupported canonical metadata/result."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _catalog() -> Any:
    # Existing catalog owns available signals and their calculation functions.
    from engine import tech_catalog

    return tech_catalog


def _lab() -> Any:
    from engine import lab

    return lab


def _integer(value: Any, name: str, low: int, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise WebLabError("INVALID_REQUEST", f"{name} must be an integer.")
    value = int(value)
    if value < low or (high is not None and value > high):
        bound = f"{low}..{high}" if high is not None else f">= {low}"
        raise WebLabError("INVALID_REQUEST", f"{name} must be {bound}.")
    return value


def _text(value: Any, name: str, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise WebLabError("INVALID_REQUEST", f"{name} must be a string without NUL.")
    if (not empty and not value.strip()) or len(value) > maximum:
        raise WebLabError("INVALID_REQUEST", f"{name} has invalid length.")
    return value


def _json_safe(value: Any) -> Any:
    """Keep canonical fields while making missing/nonfinite values strict JSON."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else None
    kind = type(value)
    if kind.__module__.startswith("pandas.") and kind.__name__ in {"NAType", "NaTType"}:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    # NumPy scalar/array values occur in canonical Trial statistics. Do not
    # stringify NaN, booleans, confidence intervals, or arrays into fake data.
    if kind.__module__.startswith("numpy"):
        if hasattr(value, "tolist"):
            return _json_safe(value.tolist())
        if hasattr(value, "item"):
            return _json_safe(value.item())
    raise WebLabError(
        "UNSERIALIZABLE_RESULT",
        f"Canonical result contains unsupported value type {kind.__name__}.",
    )


def _long_direction(descriptor: Mapping[str, Any]) -> bool:
    direction = descriptor.get("direction")
    return not isinstance(direction, bool) and isinstance(direction, Real) and direction == 1


def _supplemental_inputs(descriptor: Mapping[str, Any]) -> list[str]:
    # This existing catalog family opens its own repo-relative panel/snapshot.
    # It cannot be evaluated from the caller's selected OHLCV frames alone.
    function = descriptor.get("fn")
    if (
        descriptor.get("family") == "insider"
        or getattr(function, "__module__", None) == "engine.insider_power_signals"
    ):
        return [
            "data/sec_insider/panel/*.parquet",
            "site/factordata/insider_signals.json",
        ]
    if (
        descriptor.get("family") == "fundamental_valuation"
        or getattr(function, "__module__", None) == "engine.fundamental_screens"
    ):
        return ["data/edgar/fundamentals.parquet", "site/factordata/factors.json"]
    return []


def _signal_metadata(descriptor: Mapping[str, Any]) -> dict[str, Any]:
    metadata = {key: value for key, value in descriptor.items() if key != "fn"}
    supplemental = _supplemental_inputs(descriptor)
    reviewed = getattr(descriptor.get("fn"), "__module__", None) in _PRICE_ONLY_MODULES
    metadata["supported_by_web_lab"] = _long_direction(descriptor) and not supplemental and reviewed
    metadata["discovery_only"] = not metadata["supported_by_web_lab"]
    if supplemental:
        metadata["required_supplemental_inputs"] = supplemental
        metadata["unsupported_reason"] = "Supplemental data inputs are not explicitly bound."
    elif not _long_direction(descriptor):
        metadata["unsupported_reason"] = "Canonical Lab requires catalog direction +1."
    elif not reviewed:
        metadata["unsupported_reason"] = "Signal module input reads have not been admitted for this worker."
    return _json_safe(metadata)


def list_signals(query: str = "", limit: int = 50) -> dict[str, Any]:
    """Read catalog metadata only; bounded case-insensitive substring search."""
    query = _text(query, "query", 256, empty=True)
    limit = _integer(limit, "limit", 1, 100)
    needle = query.casefold().strip()
    catalog = _catalog().list_signals()
    matches = []
    for descriptor in catalog:
        metadata = _signal_metadata(descriptor)
        if not needle or needle in str(metadata).casefold():
            matches.append(metadata)
    matches.sort(key=lambda item: str(item.get("signal_id", "")))
    return {
        "schema": "mastermind.web_lab.signals.v1",
        "read_only": True,
        "research_only": True,
        "query": query,
        "catalog_size": len(catalog),
        "total_matches": len(matches),
        "returned": min(limit, len(matches)),
        "truncated": len(matches) > limit,
        "signals": matches[:limit],
    }


def plan(
    signal_id: str,
    refs: list[str],
    horizon_bars: int = 21,
    cost_bps: float = 5.0,
    n_configs_searched: int | None = None,
) -> dict[str, Any]:
    """Validate an existing signal and exact request without reading its datasets.

    A plan may omit the declared trial budget for review. Such a plan is explicitly
    not execution-ready; execute() requires a positive declared budget.
    Refs are opaque identifiers here: the caller's guarded reader owns resolution.
    """
    signal_id = _text(signal_id, "signal_id", 256)
    if not isinstance(refs, list) or not 1 <= len(refs) <= 8:
        raise WebLabError("INVALID_REQUEST", "refs must contain 1..8 data references.")
    refs = [_text(ref, "ref", 1024) for ref in refs]
    if len(set(refs)) != len(refs):
        raise WebLabError("INVALID_REQUEST", "refs must not contain duplicates.")
    horizon_bars = _integer(horizon_bars, "horizon_bars", 1, 252)
    if isinstance(cost_bps, bool) or not isinstance(cost_bps, Real):
        raise WebLabError("INVALID_REQUEST", "cost_bps must be a finite number in 0..1000.")
    cost_bps = float(cost_bps)
    if not math.isfinite(cost_bps) or not 0 <= cost_bps <= 1000:
        raise WebLabError("INVALID_REQUEST", "cost_bps must be a finite number in 0..1000.")
    if n_configs_searched is not None:
        n_configs_searched = _integer(n_configs_searched, "n_configs_searched", 1)
    try:
        descriptor = _catalog().get_signal(signal_id)
    except KeyError as exc:
        raise WebLabError("UNKNOWN_SIGNAL", f"Unknown catalog signal: {signal_id}") from exc
    if _supplemental_inputs(descriptor):
        raise WebLabError(
            "UNBOUND_SIGNAL_INPUTS",
            "This signal is discovery-only until its supplemental data inputs are "
            "explicitly admitted; supplied OHLCV frames do not bind those files.",
        )
    if not _long_direction(descriptor):
        raise WebLabError(
            "UNSUPPORTED_DIRECTION",
            "This catalog signal is bearish, neutral, or has unsupported direction. "
            "The existing canonical Lab evaluates long-only P&L.",
        )
    if getattr(descriptor.get("fn"), "__module__", None) not in _PRICE_ONLY_MODULES:
        raise WebLabError(
            "UNREVIEWED_SIGNAL_INPUTS",
            "This catalog module is discovery-only until its input reads are reviewed "
            "and admitted for the supplied-OHLCV worker.",
        )
    return {
        "schema": "mastermind.web_lab.plan.v1",
        "read_only": True,
        "research_only": True,
        "canonical_function": _CANONICAL_FUNCTION,
        "signal": _signal_metadata(descriptor),
        "request": {
            "signal_id": signal_id,
            "refs": refs,
            "horizon_bars": horizon_bars,
            "cost_bps": cost_bps,
            "n_configs_searched": n_configs_searched,
        },
        "execution_ready": n_configs_searched is not None,
        "missing_fields": [] if n_configs_searched is not None else ["n_configs_searched"],
        "required_execution_context": list(_WORKER_REQUIREMENTS),
        "limitations": list(_LIMITATIONS),
        "pending_effects": {
            "computation_read_only": False,
            "temporary_declared_budget_jsonl": True,
            "trial_result_persistence": False,
            "production_writes_requested": False,
        },
    }


def execute(universe: dict[str, "pd.DataFrame"], request: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical Trial in a caller-owned dedicated worker ONLY.

    The caller must confine imports/input reads and set a private TMPDIR;
    this function cannot infer or establish operating-system process isolation.
    It never opens refs, launches subprocesses, or writes a production Trial.
    """
    if not isinstance(request, dict):
        raise WebLabError("INVALID_REQUEST", "request must be an object.")
    unexpected = set(request) - _REQUEST_FIELDS
    if unexpected:
        raise WebLabError("INVALID_REQUEST", "request contains unsupported fields.")
    if not {"signal_id", "refs"} <= set(request):
        raise WebLabError("INVALID_REQUEST", "signal_id and refs are required.")
    prepared = plan(**request)
    exact = prepared["request"]
    if exact["n_configs_searched"] is None:
        raise WebLabError(
            "TRIAL_BUDGET_REQUIRED",
            "Declare the positive total number of configurations searched before execution.",
        )
    if not isinstance(universe, dict) or not 1 <= len(universe) <= 8:
        raise WebLabError("INVALID_REQUEST", "universe must contain 1..8 materialized frames.")
    import pandas as pd

    for name, frame in universe.items():
        _text(name, "universe key", 1024)
        if not isinstance(frame, pd.DataFrame) or "close" not in frame.columns:
            raise WebLabError(
                "INVALID_UNIVERSE", "Every universe value must be a DataFrame with a close column."
            )
    trial = _lab().catalog_backtest(
        exact["signal_id"],
        universe,
        horizon=exact["horizon_bars"],
        cost_bps=exact["cost_bps"],
        n_configs_searched=exact["n_configs_searched"],
    )
    return _json_safe(
        {
            "schema": "mastermind.web_lab.result.v1",
            "execution_status": "returned_canonical_trial",
            "read_only": False,
            "research_only": True,
            "canonical_function": _CANONICAL_FUNCTION,
            "request": exact,
            "signal": prepared["signal"],
            "universe_keys": list(universe),
            "input_binding": "Caller must bind these materialized frames to the authorized refs.",
            "trial": {
                "name": trial.name,
                "family": trial.family,
                "stats": trial.stats,
                "meta": trial.meta,
                "verdict": trial.verdict(),
                "survivorship_biased": trial.survivorship_biased,
            },
            "limitations": list(_LIMITATIONS),
            "effects": {
                "computation_read_only": False,
                "temporary_declared_budget_jsonl": {
                    "owner": "engine.trial_ledger.TrialLedger.with_declared_budget",
                    "scope": "worker tempfile.gettempdir()",
                    "effect": "canonical helper may create or append an idempotent declared budget",
                    "is_production_trial_ledger": False,
                },
                "trial_to_ledger_called": False,
                "production_writes_requested": False,
                "worker_isolation_required": True,
            },
        }
    )
