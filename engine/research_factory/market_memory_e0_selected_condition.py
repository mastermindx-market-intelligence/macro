"""Private installed-owner binding of an E0 task to its frozen condition slot.

This is prelabel preparation, not study admission or reviewer exposure. The
fixed selected owner authenticates which bytes it observed; source coverage,
independent closure, current source rights and a durable reservation still gate
execution. No request-facing endpoint, arbitrary loader, publication or provider
call is introduced. Original declarations and allocation bytes stay immutable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import sys

from . import market_memory_e0_installed_control as owner
from . import market_memory_e0_allocation_binding as binding

_MODULE = "engine/research_factory/market_memory_e0_selected_condition.py"
_ALLOCATOR = "engine/research_factory/market_memory_e0_allocation.py"
_SOURCES = owner._TASK_SOURCE_PATHS + (
    _MODULE, _ALLOCATOR, "engine/research_factory/market_memory_e0_allocation_binding.py",
)
_TOKEN = object()


def _slot(value):
    owner._require(type(value) is int and 0 <= value < 3, "registered_condition_slot_required")
    return value


def _prepare_condition_bytes(descriptor, selected, records, registration, *, task_id, slot):
    """Read only the original prelabel inputs plus their exact assignment."""
    _slot(slot)
    reg = records["registration"]
    assignment = reg["allocation"]["assignment_ref"]
    algorithm = reg["allocation"]["algorithm_ref"]
    owner.control._domain_reference(assignment)
    owner.control._domain_reference(algorithm)
    owner._require(assignment["schema"] == binding.allocator.OUTPUT_SCHEMA
                   and assignment["bytes"] <= owner.control.MAX_DOMAIN_OBJECT_BYTES,
                   "selected_assignment_role_invalid")
    owner._require(algorithm["schema"] == "python.source.v1"
                   and algorithm["sha256"] == binding.ALLOCATOR_SOURCE_SHA256
                   and algorithm["bytes"] == binding.ALLOCATOR_SOURCE_BYTES,
                   "selected_allocator_source_mismatch")
    refs = (reg["implementation"]["method_ref"], reg["tasks_ref"],
            reg["corpus"]["membership_ref"], assignment)
    owner._require(len({ref["sha256"] for ref in refs}) == len(refs),
                   "selected_condition_role_alias")
    owner._require(sum(ref["bytes"] for ref in refs) <= owner.control.MAX_DOMAIN_TOTAL_BYTES,
                   "selected_condition_byte_limit")
    inputs = owner._prepare_task_bytes(descriptor, selected, records, registration, task_id=task_id)
    body = owner._read(descriptor, assignment["sha256"] + ".json",
                       owner.control.MAX_DOMAIN_OBJECT_BYTES)
    owner._require(len(body) == assignment["bytes"] and sha256(body).hexdigest() == assignment["sha256"],
                   "selected_assignment_bytes_mismatch")
    declared = binding.validate_declaration(owner.control._domain_json(body), body, registration=reg)
    owner._require(declared["allocation_sha256"] == assignment["object_id"],
                   "selected_assignment_identity_mismatch")
    tasks = owner.control._domain_json(dict(zip(owner._INPUT_NAMES, inputs))["task_manifest"])
    # Actual installed allocator bytes are checked by the entry before and after
    # this callback; declaration consistency alone does not authenticate them.
    binding.binding_checks(declared, tasks=tasks, algorithm_source_bound=True)
    rows = [row for row in declared["assignments"] if row["task_id"] == task_id]
    owner._require(len(rows) == 1, "selected_task_assignment_required")
    return inputs, body, rows[0]["order"][slot]


@dataclass(frozen=True, slots=True, init=False, repr=False)
class _SelectedConditionInputs:
    _study_id: str
    _task_id: str
    _slot: int
    _selection: bytes
    _values: tuple
    _seal: object

    def __init__(self, study_id, task_id, slot, selection, values, *, _key=None):
        owner._require(_key is _TOKEN, "selected_condition_inputs_required")
        for name, value in (("_study_id", study_id), ("_task_id", task_id), ("_slot", slot),
                            ("_selection", selection), ("_values", values), ("_seal", _key)):
            object.__setattr__(self, name, value)


def _verify_sources(commit):
    owner._verify_source(owner.INSTALLED_ROOT, commit, paths=_SOURCES)
    path = owner.INSTALLED_ROOT / _ALLOCATOR
    with owner._directory(path.parent, private=False) as descriptor:
        body = owner._read(descriptor, path.name, binding.ALLOCATOR_SOURCE_BYTES, private=False)
    owner._require(len(body) == binding.ALLOCATOR_SOURCE_BYTES
                   and sha256(body).hexdigest() == binding.ALLOCATOR_SOURCE_SHA256,
                   "installed_allocator_bytes_mismatch")


def _prepare_selected_condition_inputs(study_id: str, task_id: str, slot: int):
    """Resolve a slot from the fixed private selection, never a caller's order."""
    owner._require(sys.platform == "linux" and os.geteuid() == 0
                   and Path(__file__).resolve() == owner.INSTALLED_ROOT / _MODULE,
                   "installed_administrator_entry_required")
    _slot(slot)
    for value in (study_id, task_id):
        owner._require(type(value) is str and owner.control._ID.fullmatch(value) is not None,
                       "study_or_task_identity_invalid")
    from . import market_memory_e0_task_evidence  # Load the fixed verified composition.
    owner._verify_loaded_sources(paths=_SOURCES)
    directory = owner.CONTROL_ROOT / sha256(study_id.encode()).hexdigest()
    values, selection = owner._load_selected_control(directory, study_id, _verify_sources,
        clock=lambda: datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        prepare=lambda fd, selected, records, registration: _prepare_condition_bytes(
            fd, selected, records, registration, task_id=task_id, slot=slot))
    return _SelectedConditionInputs(study_id, task_id, slot, selection, values, _key=_TOKEN)


def _current_selected_condition_bytes(prepared):
    """Recheck owner selection and rights before a trusted executor consumes it."""
    owner._require(type(prepared) is _SelectedConditionInputs and prepared._seal is _TOKEN,
                   "selected_condition_inputs_required")
    current = _prepare_selected_condition_inputs(prepared._study_id, prepared._task_id, prepared._slot)
    owner._require(current._selection == prepared._selection and current._values == prepared._values,
                   "prepared_condition_selection_changed")
    inputs, assignment, condition = current._values
    return {**dict(zip(owner._INPUT_NAMES, inputs)), "assignment": assignment,
            "condition": condition, "slot": current._slot}
