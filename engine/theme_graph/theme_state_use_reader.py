"""Read-only use-time companion to the existing production ThemeState owner.

This module is intentionally outside the eight sealed producer files. It creates
no state, publication, rights grant, clock, source read or materialized artifact.
The old production read API remains unchanged. Standalone subject availability
is not evidence of accepted publication; the generation reader owns that gate.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from . import theme_state_production as production
from . import theme_state

SCHEMA = "gmi.theme_state_read/v3"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts/theme_graph/theme_state_use_read.v1.schema.json"


def read_subject_at_use(state, *, node_id, effective_at, known_at, use_at, purpose="research_internal"):
    """Describe a validated state's subject at use, retaining its exact query."""
    if any(type(value) is not str for value in (node_id, effective_at, known_at, use_at, purpose)):
        raise ValueError("exact string request fields required")
    production.validate_state(state)
    known = production._instant(known_at)
    use = production._instant(use_at)
    theme_state._clock(effective_at)
    receipt = {"schema": SCHEMA, "query": {"effective_at": effective_at, "known_at": known_at},
               "use_at": use_at, "subject_id": node_id,
               "state_generation_id": state["generation_id"], "state_sha256": state["state_sha256"],
               "state_generated_at": state["generated_at"], "status": "UNAVAILABLE", "subject": None,
               "reason_codes": [], "authority_caps": copy.deepcopy(production.FLAGS)}
    if purpose != "research_internal":
        receipt["reason_codes"] = ["S1_UNMATERIALIZED_CURRENT_SOURCE_PURPOSE_GRANT_REQUIRED"]
    elif known > use:
        receipt["reason_codes"] = ["QUERY_KNOWLEDGE_AFTER_USE"]
    elif production._instant(state["generated_at"]) > use:
        receipt["reason_codes"] = ["STATE_NOT_YET_EMITTED"]
    elif effective_at != state["effective_at"] or known_at != state["known_at"]:
        receipt["reason_codes"] = ["EXACT_CAPTURE_QUERY_REQUIRED"]
    else:
        row = next((row for row in state["subjects"] if row["node_id"] == node_id), None)
        if row is None:
            receipt["reason_codes"] = ["SUBJECT_UNAVAILABLE"]
        else:
            receipt.update(status="DESCRIPTIVE", subject=copy.deepcopy(row), reason_codes=[
                "NATIVE_KNOWABILITY_AND_SOURCE_PURPOSE_QUALIFICATION_REMAIN_PER_LEG", "D2E_NOT_QUALIFIED"])
    return validate_read_receipt_at_use(receipt)


def validate_read_receipt_at_use(receipt):
    """Check closed structure and source clocks; consistency is not authority."""
    production._finite_json(receipt)
    doc = json.loads(SCHEMA_PATH.read_text())
    if doc["$defs"] != production._SCHEMA_DOC["$defs"]:
        raise ValueError("use-read schema differs from production owner definitions")
    errors = list(Draft202012Validator(doc).iter_errors(receipt))
    if errors:
        raise ValueError("closed production use receipt: " + errors[0].message)
    known = production._instant(receipt["query"]["known_at"])
    use = production._instant(receipt["use_at"])
    emitted = production._instant(receipt["state_generated_at"])
    theme_state._clock(receipt["query"]["effective_at"])
    if receipt["state_generation_id"] != production.GENERATION_PREFIX + receipt["state_sha256"][:20]:
        raise ValueError("read generation/hash mismatch")
    if receipt["status"] == "DESCRIPTIVE":
        if known > emitted or emitted > use:
            raise ValueError("state source/emission/use clocks are out of order")
        if receipt["subject"]["node_id"] != receipt["subject_id"]:
            raise ValueError("read subject scope mismatch")
        if receipt["reason_codes"] != [
                "NATIVE_KNOWABILITY_AND_SOURCE_PURPOSE_QUALIFICATION_REMAIN_PER_LEG", "D2E_NOT_QUALIFIED"]:
            raise ValueError("production use receipt exceeds descriptive ceiling")
        for name, leg in receipt["subject"]["legs"].items():
            production._validate_qualification(leg, subject_id=receipt["subject_id"], query=receipt["query"])
            production._validate_records(leg, name=name, query=receipt["query"])
    return receipt
