"""Bind declared condition orders to the existing allocator and task bytes.

Pure metadata validation only. The public seed is not reviewer blinding, and
recomputing a declaration does not select tasks or authenticate an installation.
"""
from __future__ import annotations

from . import market_memory_contextual_registration as control
from . import market_memory_e0_allocation as allocator


ALLOCATOR_SOURCE_SHA256 = "8423c5dc80fe48a8ced66ecf17b7c17a1d9e2ffb4e40fdedc11bfb19cb514a4c"
ALLOCATOR_SOURCE_BYTES = 11411


def validate_declaration(value, body, *, registration):
    """Require exact canonical native output, including false authority flags."""
    if type(body) is not bytes or not 0 < len(body) <= control.MAX_DOMAIN_OBJECT_BYTES:
        raise control.E0ControlError("bounded_allocation_declaration_bytes_required")
    declared, canonical = control._domain_snapshot(value)
    if body != canonical:
        raise control.E0ControlError("noncanonical_allocation_declaration_bytes")
    rows = declared.get("assignments")
    if (type(rows) is not list or not 1 <= len(rows) <= allocator.MAX_TASK_IDS
            or any(type(row) is not dict for row in rows)):
        raise control.E0ControlError("allocation_assignment_rows_required")
    try:
        expected = allocator.allocate_condition_order(
            seed_hex=registration["allocation"]["seed_hex"],
            study_id=registration["study_id"],
            tasks_sha256=registration["tasks_ref"]["sha256"],
            task_ids=[row.get("task_id") for row in rows])
    except (allocator.AllocationError, KeyError, TypeError) as exc:
        raise control.E0ControlError("allocation_declaration_identity_invalid") from exc
    # Compare bytes, not Python equality: False and 0 are different declarations.
    if canonical != control._domain_snapshot(expected)[1]:
        raise control.E0ControlError("allocation_declaration_native_mismatch")
    return declared


def binding_checks(declared, *, tasks, algorithm_source_bound):
    """Join already-validated task bytes; missing evidence remains unresolved."""
    if type(algorithm_source_bound) is not bool:
        raise control.E0ControlError("allocation_source_binding_boolean_required")
    if tasks is not None:
        try:
            task_ids = [row["task_id"] for row in tasks["tasks"]]
            allocated = [row["task_id"] for row in declared["assignments"]]
            matches = (all(type(item) is str for item in task_ids)
                       and len(task_ids) == len(set(task_ids))
                       and sorted(task_ids) == allocated)
        except (KeyError, TypeError) as exc:
            raise control.E0ControlError("allocation_task_manifest_mismatch") from exc
        if not matches:
            raise control.E0ControlError("allocation_task_manifest_mismatch")
    unresolved = []
    if tasks is None:
        unresolved.append("exact_task_manifest_bytes")
    if not algorithm_source_bound:
        unresolved.append("exact_allocator_source_bytes")
    return {"schema": allocator.OUTPUT_SCHEMA,
            "allocation_sha256": declared["allocation_sha256"],
            "task_count": len(declared["assignments"]),
            "declared_orders_match_native_allocator": True,
            "exact_task_manifest_bytes_bound": tasks is not None,
            "allocator_source_bytes_bound": algorithm_source_bound,
            "unresolved": unresolved,
            "operational_admission": False, "blinding_established": False,
            "actual_task_provenance_authenticated": False}
