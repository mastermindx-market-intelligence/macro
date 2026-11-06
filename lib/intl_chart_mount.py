"""Attach source-witnessed IM02 charts to the incumbent Compare owner.

One qualified producer supplies the delayed EOD frame and its exact source
packet. This adapter reuses existing Compare catalogues and never fetches,
issues rights decisions, persists values, or controls browser state.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pandas as pd

from engine.intl_inputs import source_snapshot
from engine.intl_performance_charts import build_chart_records
from lib.intl_compare_mount import attach_compares
from lib.intl_chart_geometry import build_chart_geometry
from lib.intl_chart_publication import build_source_bound_charts

_POLICY = "intl-observed-endpoints-completed-session-v1"
_CLOCK = "intl-conservative-observed-eod-tplus2-v1"
_PREFIX = "intl-supplied-close:sha256:"


def _qualified_packet(workspace: dict, closes: pd.DataFrame, production_inputs: object) -> str | None:
    """Re-bind the EOD packet to *exactly* this delayed frame and snapshot."""
    if type(production_inputs) is not dict:
        return None
    if production_inputs.get("policy_id") != _POLICY:
        return None
    if (type(production_inputs.get("source_evidence")) is not list
            or type(production_inputs.get("adjustment_bases")) is not dict):
        return None
    snapshot = workspace.get("eod_snapshot")
    if (type(snapshot) is not dict
            or snapshot.get("policy") != _CLOCK
            or type(snapshot.get("as_of")) is not str):
        return None
    if not isinstance(closes, pd.DataFrame) or closes.empty:
        return None
    try:
        if not isinstance(closes.index, pd.DatetimeIndex):
            return None
        if (closes.index.hasnans or closes.index.has_duplicates
                or not closes.index.is_monotonic_increasing
                or closes.index.tz is not None):
            return None
        if closes.index[-1].date().isoformat() != snapshot["as_of"]:
            return None
        digest = source_snapshot(
            closes, source_reference=_PREFIX+"pending",
            adjustment_bases=production_inputs["adjustment_bases"])["content_sha256"]
    except (ValueError, TypeError, KeyError, OverflowError):
        return None
    return _PREFIX + digest


def attach_source_bound_charts(
    workspace: dict, closes: pd.DataFrame, *, production_inputs: object,
    width: int = 640, height: int = 220,
) -> dict:
    """Add optional chart geometry to the normal detached Compare catalogue.

    Missing or inconsistent source evidence leaves the incumbent comparison
    intact. It does *not* turn old source-free performance into a chart.
    """
    result = attach_compares(workspace)
    ref = _qualified_packet(result, closes, production_inputs)
    if ref is None:
        return result
    source_evidence = production_inputs["source_evidence"]
    for panel, compared in zip(result["panels"], result["compares"], strict=True):
        overview = panel["overview"]
        context = overview["context"]
        if context["source_reference"] != ref or context["return_basis"] != "price":
            continue
        selected_basis = {"usd_unhedged": "usd", "local": "local"}.get(
            context["currency_basis"])
        if selected_basis is None:
            continue
        try:
            raw = build_chart_records(
                closes, horizon=context["horizon"], basis=selected_basis,
                source_reference=ref)
            admission = build_source_bound_charts(
                overview, raw, source_evidence=source_evidence,
                adjustment_bases=production_inputs["adjustment_bases"],
                snapshot_date=result["eod_snapshot"]["as_of"])
            geometry = build_chart_geometry(admission, width=width, height=height)
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
        if geometry["status"] == "unavailable":
            continue
        catalogue = compared["compare_catalogue"]
        covered = {
            market for group in geometry["cohorts"]
            for market in (line["market_id"] for line in group["paths"])
        }
        names = {
            row["market_id"]: {"en": row["name_en"], "zh": row["name_zh"]}
            for row in catalogue["rows"]
            if row.get("quality") != "denied"
            and row.get("market_id") in covered
        }
        if set(names) != covered:
            continue
        catalogue["chart_geometry"] = geometry
        catalogue["chart_names"] = names
    return result
