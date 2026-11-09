"""Dormant owner-declared synthetic output controls; pure byte composition.

The assigning owner supplies independently fixed expected rows, not an outcome or
variant position. Freeze receives no output. The driver validates and retains its
digest before effects; the advisory consumer checks that same binding. This is a
structural source contract, not authenticated chronology or producer enrollment.
Old outcomes remain NOT_RUN. No original physical declaration is upgraded, no
candidate is executed here, and matching scripted rows proves no temporal-bias,
physical containment, scientific result or admission.
"""
from dataclasses import dataclass
import hashlib

from . import bridge, contracts, staging_accounting as staging
from .output_contract import validate_output_envelope

SCHEMA = "research_codegen.output_expectation.v1"


class OutputExpectationRefused(ValueError):
    """The declaration cannot be bound to this exact prepared workload."""


@dataclass(frozen=True)
class FrozenOutputExpectation:
    descriptor: bridge.BoundBytes
    expected_generation: bridge.BoundBytes


def _require(ok):
    if not ok:
        raise OutputExpectationRefused("OUTPUT_EXPECTATION_BINDING_REFUSED")


def freeze_output_expectation(prepared, *, expected_generation, variant_id,
                              control_kind, expected_rows):
    """Freeze independently declared native rows against exact prepared inputs.

    Available good answers and explicit native future-dependent refusals have
    different semantics. A malformed output, generic transport failure, or a
    different refusal reason can never match a declared native refusal.
    """
    _require(type(prepared) is bridge.PreparedSyntheticInputs
             and type(prepared.identity) is bridge.PreparedIdentity)
    identity = prepared.identity
    identity_doc = {key: getattr(identity, key) for key in bridge._IDENTITY}
    for key, value in identity_doc.items():
        _require(contracts._sha(value) if key.endswith("sha256") else contracts._opaque_id(value))
    generation = staging._load_bound_json(expected_generation, "EXPECTED")
    staging._validate_expected(generation, bridge.SyntheticTestCommission(identity.original_root_id, ""))
    _require(generation["protocol_sha256"] == identity.protocol_sha256)
    _require(type(variant_id) is str and contracts._opaque_id(variant_id))
    variants = [v for v in generation["variants"] if v["variant_id"] == variant_id]
    _require(len(variants) == 1 and variants[0]["source_sha256"] == identity.source_sha256
             and variants[0]["config_sha256"] == identity.config_sha256)
    _require(type(control_kind) is str and control_kind in ("known_answer", "future_dependent"))
    _require(type(prepared.decisions) is tuple and 0 < len(prepared.decisions) <= 4096
             and type(expected_rows) is tuple and len(expected_rows) == len(prepared.decisions))
    cells, seen = [], set()
    for task, row in zip(prepared.decisions, expected_rows):
        _require(type(task) is bridge.PreparedDecisionInput)
        staging._bound(task.input_bytes, "INPUT")
        schedule = {"schema": "research_codegen.schedule.v1", "candidate_id": identity.candidate_id,
            "fold_id": task.fold_id, "entity_id": task.entity_id,
            "input_policy_sha256": identity.input_policy_sha256, "decision_ids": [task.decision_id]}
        envelope = {key: value for key, value in schedule.items() if key != "decision_ids"}
        envelope.update(schema="research_codegen.output.v1", rows=[row])
        _require(not validate_output_envelope(envelope, trusted_schedule=schedule))
        _require(row["status"] == ("available" if control_kind == "known_answer" else "refused"))
        key = (task.fold_id, task.entity_id, task.decision_id)
        _require(key not in seen)
        seen.add(key)
        cells.append(dict(fold_id=task.fold_id, entity_id=task.entity_id,
                          input_sha256=task.input_bytes.sha256, row=dict(row)))
    # Bind grouped schedule order too, including group boundaries and empty groups.
    _require(type(prepared.schedules) is tuple
             and all(type(g) is bridge.PreparedOwnerSchedule for g in prepared.schedules))
    schedules, groups = [], set()
    for group in prepared.schedules:
        _require(contracts._opaque_id(group.fold_id) and contracts._opaque_id(group.entity_id)
                 and type(group.decision_ids) is tuple
                 and all(contracts._opaque_id(d) for d in group.decision_ids))
        key = (group.fold_id, group.entity_id)
        _require(key not in groups)
        groups.add(key)
        _require(group.decision_ids == tuple(t.decision_id for t in prepared.decisions
                 if (t.fold_id, t.entity_id) == key))
        schedules.append(dict(fold_id=group.fold_id, entity_id=group.entity_id,
                              decision_ids=list(group.decision_ids)))
    _require({(t.fold_id, t.entity_id) for t in prepared.decisions} <= groups)
    document = dict(schema=SCHEMA, identity=identity_doc,
        expected_generation_sha256=expected_generation.sha256,
        variant_id=variant_id, control_kind=control_kind,
        schedules=schedules,
        cells=cells)
    raw = bridge._canonical_bytes(document)
    _require(len(raw) <= contracts.MAX_BYTES)
    return FrozenOutputExpectation(bridge.BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw)),
                                   expected_generation)


def validate_output_expectation(frozen, prepared):
    """Rebuild every field from current prepared inputs, never observed outputs."""
    _require(type(frozen) is FrozenOutputExpectation)
    doc = staging._load_bound_json(frozen.descriptor, "EXPECTATION")
    _require(type(doc) is dict and type(doc.get("cells")) is list
             and all(type(c) is dict and "row" in c for c in doc["cells"]))
    rebuilt = freeze_output_expectation(prepared,
        expected_generation=frozen.expected_generation, variant_id=doc.get("variant_id"),
        control_kind=doc.get("control_kind"), expected_rows=tuple(c["row"] for c in doc["cells"]))
    _require(frozen.descriptor == rebuilt.descriptor)
    return doc


def compare_output_expectation(frozen, prepared, outcome, adopted):
    """Return only source-level comparison; unexecuted/invalid output is NOT_RUN."""
    doc = validate_output_expectation(frozen, prepared)
    _require(outcome.output_expectation_sha256 == frozen.descriptor.sha256)
    if not outcome.completed or len(adopted) != len(doc["cells"]):
        return "NOT_RUN", None
    observed = [dict(fold_id=task.fold_id, entity_id=task.entity_id,
                     input_sha256=task.input_bytes.sha256, row=row) for task, row in adopted]
    matched = bridge._canonical_bytes(observed) == bridge._canonical_bytes(doc["cells"])
    evidence = bridge._canonical_bytes(dict(expectation_sha256=frozen.descriptor.sha256,
        observed_cells=observed))
    return ("MATCHED_EXPECTATION" if matched else "DID_NOT_MATCH"), hashlib.sha256(evidence).hexdigest()
