"""Native evidence -> bounded participant bytes, for the trusted executor only.

This implements packet contract73d67; it is not the native service issuer,
recipient authorization, transport, reservation or study-admission API. The
existing executor privately selects its registered condition. A caller condition,
digest or successful parse cannot authorize that selection or source disclosure.
No request-facing route/tool or source/store writer is introduced.
"""
from __future__ import annotations

import copy
from hashlib import sha256
import json
import math
import re

from engine.research_factory import market_memory_e0_task_evidence as tasks
from engine.research_factory import market_memory_e0_condition_evidence as sources

SCHEMA = "research_factory.market_memory_e0_participant_packet.v1"
SUFFIX = (b"\n\nReturn a bounded final response of at most 12000 characters. "
          b"Do not delegate further.\n")
MAX_PACKET_BYTES = 65536
MAX_BODY_BYTES = MAX_PACKET_BYTES - len(SUFFIX)
_SHA = re.compile(r"[a-f0-9]{64}")
_TASK = {"task_id", "subject_id", "instrument_id", "analysis_cutoff", "mode",
         "question", "question_sha256", "required_facet_ids"}
_VIEW = {"schema", "authority", "source_cards", "state_differences",
         "explicit_method_identity_redacted", "actual_blinding_established", "limitations"}
_CARD = {"role", "context_id", "capture_id", "packet_sha256", "subject_id",
         "source_receipt_ids", "source_session", "clocks", "facts",
         "missing_feature_ids", "evidence_basis"}
_CLOCKS = {"captured_at", "raw_source_observed_at", "raw_source_built_at",
           "feature_as_of", "event_time", "as_known_at", "knowledge_cutoff"}
_FIELDS = ("growth_score", "inflation_score", "quad", "liquidity_overlay", "cycle_tag")
_FACT = {"field", "value", "meaning", "citation", "structural_source_closure",
         "underlying_component_truth_authenticated"}
_CITATION = {"snapshot_id", "source_sha256", "source_bytes", "json_pointer",
             "start_byte", "end_byte_exclusive", "span_sha256", "quoted_json"}
_LIMITS = ["source_dates_and_counts_may_reveal_condition",
           "original_house_output_not_constituent_truth", "subsequent_outcomes_not_attached",
           "no_semantic_causal_predictive_or_action_authority"]


class ParticipantPacketError(ValueError):
    """Stable refusal, without a private path, source value or payload dump."""


def _require(ok, reason):
    if not ok:
        raise ParticipantPacketError(reason)


def _exact_keys(value, keys):
    return type(value) is dict and set(value) == keys


def _canonical(value):
    nodes, total = 0, 0
    active = set()

    def visit(item, depth=0):
        nonlocal nodes, total
        nodes += 1
        _require(nodes <= 16384 and depth <= 20, "packet_structure_bound")
        kind = type(item)
        if kind is str:
            try:
                total += len(item.encode("utf-8"))
            except UnicodeEncodeError as exc:
                raise ParticipantPacketError("packet_utf8_required") from exc
            _require(total <= MAX_PACKET_BYTES, "packet_text_bound")
        elif item is None or kind in (bool, int):
            return
        elif kind is float:
            _require(math.isfinite(item), "finite_packet_value_required")
        elif kind in (dict, list):
            _require(id(item) not in active, "packet_cycle_prohibited")
            active.add(id(item))
            if kind is dict:
                for key, child in item.items():
                    _require(type(key) is str, "packet_string_keys_required")
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
            active.remove(id(item))
        else:
            raise ParticipantPacketError("exact_builtin_packet_types_required")

    visit(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeEncodeError) as exc:
        raise ParticipantPacketError("canonical_packet_required") from exc


def _digest(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _descriptors(document):
    _require(_exact_keys(document, {"schema", "task", "source_view"})
             and document["schema"] == SCHEMA, "closed_participant_packet_required")
    task, view = document["task"], document["source_view"]
    _require(_exact_keys(task, _TASK) and _exact_keys(view, _VIEW),
             "closed_native_task_and_source_view_required")
    _require(type(task["question"]) is str and _digest(task["question_sha256"])
             and sha256(task["question"].encode("utf-8")).hexdigest() == task["question_sha256"],
             "native_question_binding_required")
    _require(view["schema"] == "research_factory.market_memory_e0_method_redacted_sources.v1"
             and view["authority"] == "display_only"
             and view["explicit_method_identity_redacted"] is True
             and view["actual_blinding_established"] is False
             and view["limitations"] == _LIMITS, "native_view_limitations_required")
    cards = view["source_cards"]
    _require(type(cards) is list and 1 <= len(cards) <= 9, "assigned_source_card_bound")
    descriptors, contexts = [], set()
    for index, card in enumerate(cards):
        _require(_exact_keys(card, _CARD) and card["role"] ==
                 ("query" if index == 0 else "selected_neighbor")
                 and card["subject_id"] == task["subject_id"]
                 and card["evidence_basis"] == "retained_original_house_output"
                 and _digest(card["packet_sha256"])
                 and _exact_keys(card["clocks"], _CLOCKS), "exact_ordered_native_card_required")
        _require(type(card["context_id"]) is str and card["context_id"] not in contexts,
                 "unique_assigned_contexts_required")
        contexts.add(card["context_id"])
        facts = card["facts"]
        _require(type(facts) is list and len(facts) == 5, "native_five_facts_required")
        for field, fact in zip(_FIELDS, facts, strict=True):
            _require(_exact_keys(fact, _FACT) and fact["field"] == field
                     and fact["meaning"] == "the_retained_house_output_reports_this_value"
                     and fact["structural_source_closure"] is True
                     and fact["underlying_component_truth_authenticated"] is False,
                     "exact_native_fact_required")
            cite = fact["citation"]
            _require(_exact_keys(cite, _CITATION) and _digest(cite["source_sha256"])
                     and _digest(cite["span_sha256"])
                     and type(cite["source_bytes"]) is int and cite["source_bytes"] > 0
                     and type(cite["start_byte"]) is int
                     and type(cite["end_byte_exclusive"]) is int
                     and 0 <= cite["start_byte"] < cite["end_byte_exclusive"] <= cite["source_bytes"]
                     and type(cite["json_pointer"]) is str
                     and type(cite["quoted_json"]) is str, "exact_native_citation_required")
            quoted = cite["quoted_json"].encode("utf-8")
            _require(cite["json_pointer"] == "/state/" + field
                     and quoted == _canonical(fact["value"])
                     and len(quoted) == cite["end_byte_exclusive"] - cite["start_byte"]
                     and sha256(quoted).hexdigest() == cite["span_sha256"],
                     "native_citation_byte_span_required")
            descriptors.append({"context_id": card["context_id"],
                "capture_id": card["capture_id"], "packet_sha256": card["packet_sha256"],
                "field": field, "citation": copy.deepcopy(cite)})
    differences = view["state_differences"]
    _require(type(differences) is list and len(differences) <= 40,
             "native_difference_bound")
    values = {card["context_id"]: {fact["field"]: fact["value"]
              for fact in card["facts"]} for card in cards}
    difference_ids = set()
    for row in differences:
        _require(_exact_keys(row, {"context_id", "field", "query_value", "neighbor_value", "meaning"})
                 and row["context_id"] in contexts and row["context_id"] != cards[0]["context_id"]
                 and row["field"] in _FIELDS
                 and row["meaning"] == "different_dated_outputs_not_a_logical_contradiction",
                 "assigned_difference_reference_required")
        identity = (row["context_id"], row["field"])
        _require(identity not in difference_ids
                 and _canonical(row["query_value"]) == _canonical(values[cards[0]["context_id"]][row["field"]])
                 and _canonical(row["neighbor_value"]) == _canonical(values[row["context_id"]][row["field"]]),
                 "difference_must_match_selected_native_facts")
        difference_ids.add(identity)
    return tuple(descriptors)


def extract_selected_citations(packet, *, input_sha256):
    """Byte-integrity/closed-shape extraction only; no source/recipient authority.

    The protected runtime must first qualify actual original input custody and
    current native recipient permission. A supplied digest or this return never
    authenticates a packet, source, provider, participant or study.
    """
    _require(type(packet) is bytes and len(SUFFIX) < len(packet) <= MAX_PACKET_BYTES
             and _digest(input_sha256)
             and sha256(packet).hexdigest() == input_sha256, "original_packet_bytes_required")
    _require(packet.endswith(SUFFIX), "exact_terminal_suffix_required")
    body = packet[:-len(SUFFIX)]

    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, "duplicate_packet_key")
            value[key] = item
        return value

    try:
        document = json.loads(body.decode("utf-8"), object_pairs_hook=pairs,
                              parse_constant=lambda _: (_ for _ in ()).throw(
                                  ParticipantPacketError("finite_packet_value_required")))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ParticipantPacketError("canonical_packet_required") from exc
    _require(_canonical(document) == body, "canonical_packet_required")
    return _descriptors(document)


def _native_graph_snapshot(capability):
    """Integrity of the fixed native graph; never a cached source-use grant."""
    baselines = sources.baselines
    retrieval = baselines.retrieval
    cohort = baselines.cohort
    fields = {
        tasks.E0TaskConditionEvidence: ("_binding", "_digest", "_sources", "_seal"),
        sources.E0ConditionEvidence: ("_body", "_digest", "_selection", "_resources", "_seal"),
        baselines.E0ConditionSelections: ("_body", "_digest", "_retrieval", "_seal"),
        retrieval.EpisodeRetrievalCapability:
            ("_body", "_digest", "_cohort", "_query", "_compared", "_seal"),
        cohort.RetainedContextCohortCapability:
            ("_body", "_digest", "_resource", "_features", "_seal"),
        retrieval.features.EpisodeFeatureCapability: ("_body", "_digest", "_resource", "_seal"),
    }
    nodes, seen = [], {}
    count, size = 0, 0

    def visit(value, depth=0):
        nonlocal count, size
        count += 1
        _require(count <= 16384 and depth <= 24, "native_packet_graph_bound")
        kind = type(value)
        if kind in (bytes, str):
            size += len(value)
            _require(size <= 64 * 1024 * 1024, "native_packet_graph_bound")
            return (kind.__name__, value)
        if value is None:
            return ("none",)
        if kind is object:
            nodes.append(value)
            return ("native_token", id(value))
        _require(kind in fields or kind is tuple, "fixed_native_packet_graph_required")
        identity = id(value)
        if identity in seen:
            return ("ref", seen[identity])
        seen[identity] = len(nodes)
        nodes.append(value)
        if kind is tuple:
            _require(len(value) <= 2048, "native_packet_graph_bound")
            return ("tuple", identity, tuple(visit(item, depth + 1) for item in value))
        return (kind.__module__, kind.__name__, identity,
                tuple((name, visit(getattr(value, name), depth + 1)) for name in fields[kind]))

    return visit(capability), tuple(nodes)


def build_task_condition_packet(capability, *, condition, policy):
    """Actual native disclosure -> exact packet, in a trusted private executor.

    This mirrors the existing internal disclosure seam. It deliberately does not
    stand in for the still-required installed issuer, selected grant or protected
    native service identity. It accepts no caller view, task, citation or packet.
    """
    _require(type(capability) is tasks.E0TaskConditionEvidence,
             "genuine_native_task_evidence_required")
    _require(type(condition) is str and condition in sources.CONDITIONS,
             "registered_private_condition_required")
    before_graph, before_nodes = _native_graph_snapshot(capability)
    view = tasks.disclose_task_condition_view(capability, condition=condition, policy=policy)
    document = {"schema": SCHEMA, "task": view["task"],
                "source_view": {key: value for key, value in view.items() if key != "task"}}
    body = _canonical(document)
    _require(0 < len(body) <= MAX_BODY_BYTES, "whole_packet_byte_bound")
    _descriptors(document)
    packet = body + SUFFIX
    # No prior successful disclosure or canonical descriptor is a rights cache.
    current = tasks.disclose_task_condition_view(capability, condition=condition, policy=policy)
    after_graph, after_nodes = _native_graph_snapshot(capability)
    _require(_canonical(current) == _canonical(view) and after_graph == before_graph
             and len(after_nodes) == len(before_nodes)
             and all(a is b for a, b in zip(after_nodes, before_nodes, strict=True)),
             "native_evidence_changed_during_packet_build")
    return packet
