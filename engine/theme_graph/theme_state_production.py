"""Pure version-selected production contract for the incumbent graph/state owner.

S1 supplies composition, validation and an immutable read. It owns no writer,
scheduler, store, source authentication, rights grant or publication. Accepted
shadow-v1 remains an unchanged, explicitly diagnostic validation witness.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

from engine.theme_graph import identity, theme_state

SCHEMA = "neuralweb.theme_state.v2"
READ_SCHEMA = "gmi.theme_state_read/v2"
GENERATION_PREFIX = "theme-state-v2:"
FLAGS = {key: False for key in (
    "ranking", "gating", "sizing", "insertion", "origination", "escalation",
    "trade", "predictive", "may_publish")}
_SCHEMA_BYTES = (Path(__file__).resolve().parents[2] /
                 "contracts/theme_graph/theme_state.v2.schema.json").read_bytes()
_SCHEMA_DOC = json.loads(_SCHEMA_BYTES)
_SCHEMA_SHA256 = hashlib.sha256(_SCHEMA_BYTES).hexdigest()
_VALIDATOR = Draft202012Validator(_SCHEMA_DOC)


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def _finite_json(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _finite_json(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _finite_json(item)
        return
    raise ValueError("finite exact JSON values required")


def _instant(value):
    answer, date_only = theme_state._clock(value)
    if date_only:
        raise ValueError("precise zoned clock required")
    return answer


def clock_slot(value, *, declared=False):
    if value is None:
        return {"value": None, "grain": "UNAVAILABLE",
                "null_reason": "EXPLICIT_NATIVE_CLOCK_NULL" if declared else "NATIVE_CLOCK_NOT_DECLARED"}
    try:
        if type(value) is not str:
            raise ValueError("native clock is not a string")
        if len(value) == 10:
            _, date_only = theme_state._clock(value)
            if not date_only:
                raise ValueError("native date clock required")
            grain = "DATE"
        else:
            _instant(value)
            grain = "INSTANT"
        return {"value": value, "grain": grain, "null_reason": None}
    except (ValueError, TypeError):
        # Preserve the owner's invalid value, without using it as a clock.
        return {"value": copy.deepcopy(value), "grain": "INVALID", "null_reason": "NATIVE_CLOCK_INVALID"}


def value_slot(value=None, *, declared=False):
    return {"value": copy.deepcopy(value),
            "null_reason": ("EXPLICIT_NATIVE_NULL" if declared else "NATIVE_FIELD_NOT_DECLARED")
            if value is None else None}


def state_digest(state):
    return canonical_sha256({key: value for key, value in state.items()
                             if key not in ("state_sha256", "generation_id")})


def _clock_after(slot, cutoff):
    if slot["grain"] not in ("DATE", "INSTANT"):
        return False
    return theme_state._definitely_after(slot["value"], cutoff)


def _validate_clock(slot):
    actual = clock_slot(slot["value"], declared=slot["null_reason"] == "EXPLICIT_NATIVE_CLOCK_NULL")
    if actual != slot:
        raise ValueError("native clock grain/null reason mismatch")


def native_clock_reasons(clocks, *, effective_at, known_at):
    reasons = []
    if any(slot["grain"] == "INVALID" for slot in clocks.values()):
        reasons.append("NATIVE_SOURCE_CLOCK_INVALID")
    if _clock_after(clocks["effective_at"], effective_at):
        reasons.append("NATIVE_SOURCE_EFFECTIVE_AFTER_CUTOFF")
    # Preserve the incumbent native source-asof knowledge ceiling as well as
    # the independent effective query; forecast targets are not clock slots.
    if any(_clock_after(slot, known_at) for slot in clocks.values()):
        reasons.append("NATIVE_SOURCE_CLOCK_AFTER_CUTOFF")
    for left, right in (("available_at", "known_at"), ("known_at", "recorded_at")):
        a, b = clocks[left], clocks[right]
        if (a["grain"] in ("DATE", "INSTANT") and b["grain"] in ("DATE", "INSTANT")
                and theme_state._definitely_after(a["value"], b["value"])):
            reasons.append("NATIVE_SOURCE_CLOCK_CHRONOLOGY_INVALID")
    return sorted(set(reasons))


def divergence_conflicts(records):
    """Native clock/revision groups; no inferred correction, dedup or latest wins."""
    groups = {}
    for record in records:
        slot = record["native_clocks"]["effective_at"]
        if record["native_key"] is None or slot["grain"] not in ("DATE", "INSTANT"):
            continue
        stamp, _ = theme_state._clock(slot["value"])
        row = record["value"]
        revision = {key: row[key] for key in
                    ("revision", "revision_id", "correction_id", "correction_of")
                    if key in row and row[key] is not None}
        key = canonical_sha256({"theme": record["native_key"], "clock": stamp.isoformat(),
                                "grain": slot["grain"], "native_revision": revision})
        groups.setdefault(key, []).append(record)
    conflicts = []
    for group in groups.values():
        if len(group) < 2:
            continue
        same = len({canonical_sha256(record["value"]) for record in group}) == 1
        conflicts.append({"reason": "DUPLICATE_SAME_CLOCK_DIVERGENCE" if same else "CONFLICTING_SAME_CLOCK_DIVERGENCE",
            "native_key": group[0]["native_key"], "effective_clock": copy.deepcopy(group[0]["native_clocks"]["effective_at"]),
            "record_ids": [record["record_id"] for record in group]})
    return conflicts


def _validate_qualification(leg, *, subject_id, query, graph_generation_id=None, owner_generations=None):
    qualification = leg["qualification"]
    receipt = qualification["source_receipt"]
    bound = receipt is not None
    if ((qualification["status"] == "SOURCE_QUALIFIED_RIGHTS_UNAVAILABLE") != bound
            or (qualification["historical_knowability"] == "OWNER_RECEIPT_BOUND") != bound
            or qualification["identity_membership"] == "OWNER_RECEIPT_BOUND" and not bound):
        raise ValueError("source qualification requires compatible nonnull receipt")
    if bound:
        if receipt["availability"] not in ("AVAILABLE", "VALID_EMPTY"):
            raise ValueError("qualified source receipt is unavailable")
        for name in ("effective_at", "known_at", "available_at", "recorded_at"):
            theme_state._clock(receipt[name])
        if (theme_state._definitely_after(receipt["available_at"], receipt["known_at"])
                or theme_state._definitely_after(receipt["known_at"], receipt["recorded_at"])):
            raise ValueError("source receipt chronology invalid")
        if (receipt["subject_id"] != subject_id or receipt["query"] != query
                or graph_generation_id is not None and receipt["graph_generation_id"] != graph_generation_id
                or owner_generations is not None and owner_generations.get(receipt["owner"]) != receipt["generation_id"]):
            raise ValueError("source receipt subject/query/generation scope mismatch")
        if theme_state._clock_reasons(receipt, query["effective_at"], query["known_at"]):
            raise ValueError("source receipt cutoff or knowledge precision unproven")
        if receipt["availability"] == "VALID_EMPTY" and leg["records"]:
            raise ValueError("valid empty receipt cannot qualify positive records")
    complete = leg["coverage"]["completeness"] == "QUALIFIED_COMPLETE"
    if leg["presence"] == "VALID_EMPTY" or complete:
        if (not bound or receipt["availability"] != "VALID_EMPTY" or leg["records"]
                or leg["presence"] != "VALID_EMPTY" or not complete
                or leg["coverage"]["declared"] != 0 or leg["coverage"]["observed"] != 0):
            raise ValueError("valid empty/complete coverage requires matching admitted receipt")
    if qualification["rights"]["status"] == "QUALIFIED":
        raise ValueError("S1 has no accepted specialist-purpose authority binding")


def _validate_records(leg, *, name, query):
    for record in leg["records"]:
        if type(record["source_position"]) is not int:
            raise ValueError("native source position requires exact integer")
        expected_id = canonical_sha256({"source": leg["source_ref"]["sha256"],
            "position": record["source_position"], "value": record["value"]})
        if record["record_id"] != expected_id:
            raise ValueError("native record/source identity mismatch")
        for slot in record["native_clocks"].values():
            _validate_clock(slot)
        reasons = native_clock_reasons(record["native_clocks"], **query)
        if record["usable_at_query"] is not (not reasons) or record["reason_codes"] != reasons:
            detail = "effective" if "NATIVE_SOURCE_EFFECTIVE_AFTER_CUTOFF" in reasons else "chronology/clock"
            raise ValueError("native " + detail + " use/reason disposition mismatch")
    if name == "divergence_log":
        actual = [item for item in leg["conflicts"] if item.get("reason") in
                  ("DUPLICATE_SAME_CLOCK_DIVERGENCE", "CONFLICTING_SAME_CLOCK_DIVERGENCE")]
        if canonical_sha256(actual) != canonical_sha256(divergence_conflicts(leg["records"])):
            raise ValueError("native divergence conflict disposition mismatch")


def validate_state(state):
    _finite_json(state)
    errors = sorted(_VALIDATOR.iter_errors(state), key=lambda error: str(list(error.path)))
    if errors:
        raise ValueError("production closed contract: " + errors[0].message)
    if state["state_sha256"] != state_digest(state):
        raise ValueError("production state digest mismatch")
    if state["generation_id"] != GENERATION_PREFIX + state["state_sha256"][:20]:
        raise ValueError("production generation/hash mismatch")
    emitted = _instant(state["generated_at"])
    observed = _instant(state["bundle_ref"]["observed_at"])
    _instant(state["known_at"])
    if emitted < observed:
        raise ValueError("production emission precedes actual capture")
    if state["producer_refs"]["schema"]["sha256"] != _SCHEMA_SHA256:
        raise ValueError("production schema revision mismatch")
    graph = state["diagnostic_graph_state"]
    theme_state.validate_state(graph)
    if (graph["graph_generation_id"] != state["bundle_ref"]["graph_capture_id"]
            or graph["owner_generations"].get("adapter.owner_bundle") != state["bundle_ref"]["sha256"]
            or any(graph[key] != state[key] for key in ("generated_at", "effective_at", "known_at"))):
        raise ValueError("mixed production/diagnostic bundle or query")
    if state["correction"] is not None:
        prior = state["correction"]["previous"]
        if (prior["generation_id"] != GENERATION_PREFIX + prior["state_sha256"][:20]
                or _instant(prior["generated_at"]) > emitted):
            raise ValueError("invalid prior correction generation/emission")
    ids = [row["node_id"] for row in state["subjects"]]
    graph_subjects = {row["node_id"]: row for row in graph["subjects"]}
    if len(ids) != len(set(ids)) or set(ids) != set(graph_subjects):
        raise ValueError("production subject population mismatch")
    canonical = []
    for subject in state["subjects"]:
        owner_subject = graph_subjects[subject["node_id"]]
        node = subject["node_id"]
        for key in ("node_id", "kind", "name_en", "name_zh", "source_family", "native_id"):
            if subject[key] != owner_subject[key]:
                raise ValueError("production identity differs from graph owner")
        if subject["canonical_mapping"] != owner_subject["mapping"]:
            raise ValueError("production mapping differs from graph owner")
        if subject["kind"] == "canonical_theme":
            canonical.append(node.removeprefix("theme:"))
            if identity.theme_node_id(canonical[-1]) != node:
                raise ValueError("invalid canonical identity")
        elif identity.local_theme_node_id(subject["source_family"], subject["native_id"]) != node:
            raise ValueError("invalid local identity")
        for name, leg in subject["legs"].items():
            if leg["source_ref"] != state["source_refs"][name]:
                raise ValueError("mixed specialist source bytes")
            if leg["presence"] == "AVAILABLE" and not leg["records"]:
                raise ValueError("available presence requires records; empty is separately admitted")
            if leg["coverage"]["observed"] != len(leg["records"]):
                raise ValueError("observed coverage differs from retained records")
            declared = leg["coverage"]["declared"]
            if type(leg["coverage"]["observed"]) is not int or (declared is not None and type(declared) is not int):
                raise ValueError("coverage requires exact integer counts or named null")
            if declared is not None and declared < len(leg["records"]):
                raise ValueError("observation exceeds declared coverage")
            _validate_qualification(leg, subject_id=node,
                query={"effective_at": state["effective_at"], "known_at": state["known_at"]},
                graph_generation_id=state["bundle_ref"]["graph_capture_id"],
                owner_generations=graph["owner_generations"])
            _validate_records(leg, name=name,
                query={"effective_at": state["effective_at"], "known_at": state["known_at"]})
    compatibility = state["compatibility"]
    projection = compatibility["projection"]
    if (projection.get("schema") != "neuralweb.theme_state.v1"
            or canonical_sha256(projection) != compatibility["sha256"]
            or [row["theme_id"] for row in projection["themes"]] != canonical
            or projection.get("n_themes") != len(canonical)):
        raise ValueError("complete v1 population/order/digest mismatch")
    if any(row.get("narrative") is not None for row in projection["themes"]):
        raise ValueError("legacy narrative interpretation remains held")
    return state


def compose_state(*, subjects, diagnostic_graph_state, source_refs, bundle_ref,
                  producer_refs, compatibility, effective_at, known_at, generated_at,
                  previous=None, correction_reason=None):
    correction = None
    if previous is not None:
        validate_state(previous)
        if not isinstance(correction_reason, str) or not correction_reason.strip():
            raise ValueError("explicit correction reason required")
        correction = {"previous": {key: previous[key] for key in
                        ("generation_id", "state_sha256", "generated_at")},
                      "reason": correction_reason}
    elif correction_reason is not None:
        raise ValueError("correction reason without prior artifact")
    state = {"schema": SCHEMA, "generated_at": generated_at, "effective_at": effective_at,
        "known_at": known_at, "generation_id": "", "state_sha256": "",
        "bundle_ref": copy.deepcopy(bundle_ref), "producer_refs": copy.deepcopy(producer_refs),
        "source_refs": copy.deepcopy(source_refs), "subjects": copy.deepcopy(subjects),
        "diagnostic_graph_state": copy.deepcopy(diagnostic_graph_state),
        "diagnostic_graph_state_role": "NON_AUTHORITATIVE_VALIDATION_WITNESS",
        "compatibility": copy.deepcopy(compatibility), "correction": correction,
        "authority_caps": copy.deepcopy(FLAGS), "materialization_allowed": False,
        "reserved_economic_axes": {"price": None, "flow": None, "positioning": None},
        "release_disposition": "S1_UNMATERIALIZED_NO_ACTIVE_WRITER"}
    state["state_sha256"] = state_digest(state)
    state["generation_id"] = GENERATION_PREFIX + state["state_sha256"][:20]
    return validate_state(state)


def read_subject(state, *, node_id, effective_at, known_at, purpose="research_internal"):
    validate_state(state)
    receipt = {"schema": READ_SCHEMA, "query": {"effective_at": effective_at, "known_at": known_at},
        "subject_id": node_id, "state_generation_id": state["generation_id"],
        "state_sha256": state["state_sha256"], "state_generated_at": state["generated_at"],
        "status": "UNAVAILABLE", "subject": None, "reason_codes": [],
        "authority_caps": copy.deepcopy(FLAGS)}
    _instant(known_at)
    if purpose != "research_internal":
        receipt["reason_codes"] = ["S1_UNMATERIALIZED_CURRENT_SOURCE_PURPOSE_GRANT_REQUIRED"]
    elif _instant(state["generated_at"]) > _instant(known_at):
        receipt["reason_codes"] = ["STATE_NOT_YET_EMITTED"]
    elif effective_at != state["effective_at"] or known_at != state["known_at"]:
        receipt["reason_codes"] = ["EXACT_CAPTURE_QUERY_REQUIRED"]
    else:
        row = next((row for row in state["subjects"] if row["node_id"] == node_id), None)
        if row is None:
            receipt["reason_codes"] = ["SUBJECT_UNAVAILABLE"]
        else:
            receipt.update(status="DESCRIPTIVE", subject=copy.deepcopy(row),
                reason_codes=["NATIVE_KNOWABILITY_AND_SOURCE_PURPOSE_QUALIFICATION_REMAIN_PER_LEG",
                              "D2E_NOT_QUALIFIED"])
    return validate_read_receipt(receipt)


def validate_read_receipt(receipt):
    _finite_json(receipt)
    validator = Draft202012Validator({"$ref": "#/$defs/read_receipt", "$defs": _SCHEMA_DOC["$defs"]})
    errors = list(validator.iter_errors(receipt))
    if errors:
        raise ValueError("closed production read receipt: " + errors[0].message)
    known = _instant(receipt["query"]["known_at"])
    theme_state._clock(receipt["query"]["effective_at"])
    emitted = _instant(receipt["state_generated_at"])
    if receipt["state_generation_id"] != GENERATION_PREFIX + receipt["state_sha256"][:20]:
        raise ValueError("read generation/hash mismatch")
    if receipt["status"] == "DESCRIPTIVE":
        if emitted > known:
            raise ValueError("state was not emitted at read knowledge cutoff")
        if receipt["subject"]["node_id"] != receipt["subject_id"]:
            raise ValueError("read subject scope mismatch")
        for name, leg in receipt["subject"]["legs"].items():
            _validate_qualification(leg, subject_id=receipt["subject_id"], query=receipt["query"])
            _validate_records(leg, name=name, query=receipt["query"])
    return receipt
