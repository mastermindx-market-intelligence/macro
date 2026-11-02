"""Add the registered Massive daily price contract to an ASC T05/T06 request.

Run as ``python -m scripts.research.attach_asc_daily_source_contract`` with the
original SOURCE_OWNER_REQUIREMENTS.json on stdin. The output is the same request
with its daily contract attached. Only the checked-in dataset catalog is read.
"""

from __future__ import annotations

import json
import sys

from lib.dataos.registry import DatasetStatus, Registry, load_registry


def attach_daily_contract(request: dict, registry: Registry) -> dict:
    if (not isinstance(request, dict)
            or request.get("schema") != "asc.scientific_source_owner_requirements.v1"
            or request.get("status") != "REQUEST_READY_NOT_SENT_NOT_ADMITTED"):
        raise ValueError("expected an unadmitted ASC source-owner request")
    candidate = request.get("candidate_only")
    if (not isinstance(candidate, dict) or candidate.get("vendor") != "polygon"
            or candidate.get("research_admitted") is not False):
        raise ValueError("expected an unadmitted Polygon candidate")

    daily = registry.get("equity.bars.daily.massive")
    if daily is None or daily.status is not DatasetStatus.PRODUCED:
        raise ValueError("Massive daily producer contract unavailable")
    # Catalog notes may contain observed price examples. Only declarations
    # belong in the outcome-blind attachment, even when a new note is added.
    properties = ("dtype", "unit", "basis", "renames_to", "nullable")
    fields = {
        name: ({key: daily.schema[name].get(key) for key in properties}
               if name in daily.schema else None)
        for name in ("open", "high", "low", "close")
    }
    attachment = {
        "dataset_id": daily.dataset_id,
        "contract_version": daily.version,
        "producer": daily.producer,
        "identity_column": daily.id_column,
        "identity_type": daily.id_type,
        "grain": list(daily.grain),
        "frequency": daily.frequency,
        "timezone": daily.timezone,
        "declared_basis": daily.basis or None,
        "ohlc_schema": fields,
        "declared_clocks": None if daily.clocks is None else list(daily.clocks),
        "point_in_time_corporate_actions": daily.point_in_time_corporate_actions,
    }
    key = "registered_daily_source_contract"
    if key in request and request[key] != attachment:
        raise ValueError("existing daily contract differs from the catalog")
    return {**request, key: attachment}


def main() -> None:
    try:
        output = attach_daily_contract(json.load(sys.stdin), load_registry())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    json.dump(output, sys.stdout, ensure_ascii=False, allow_nan=False, indent=2)
    print()


if __name__ == "__main__":
    main()
