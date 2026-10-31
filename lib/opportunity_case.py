"""Research-only OpportunityCase over canonical K1 and K3-E compositions.

No owner I/O, persistence, identity resolution, candidate production or scoring.
K1 native subjects remain distinct from the vector subject unless the existing
recipe compiler establishes the exact same key. A declared bridge is never a
new identity receipt. Prose and this case cannot feed Prophet or LER detection.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from lib import evidence_foundation as ef
from lib import opportunity_evidence as oe

SCHEMA = "opportunity_case.research.v1"
MAX_BYTES = 256 * 1024
MAX_BLOCKS = 16
MAX_REFERENCES = 64
_CONTEXT_LEGS = ("transmission", "company_context", "valuation_context",
                 "path_timing", "portfolio_intersection")


class OpportunityCaseError(ValueError):
    """Closed contract refusal; no source body or caller prose in errors."""


def _copy(value: Any) -> Any:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > MAX_BYTES:
            raise OpportunityCaseError("case_exceeds_bound")
        return json.loads(raw)
    except (TypeError, ValueError, RecursionError) as exc:
        if isinstance(exc, OpportunityCaseError):
            raise
        raise OpportunityCaseError("case_not_bounded_json") from None


def _hash(value: Any) -> str:
    return sha256(ef.canonical_json_bytes(value)).hexdigest()


def _captured_drl_identity(recipe: dict, blocks: list[dict], refs: dict, vector: dict) -> dict | None:
    """Bind a single native event without claiming canonical security identity.

    Capture time and mutable snapshot versions belong in content lineage, not
    the stable event key. Both slots must point at the same one K1 reference.
    """
    if vector['asof']['t0_source'] != 'drl_captured_read':
        return None
    origin = vector['asof']['t0_evidence_ref']
    identity = origin['native_identity']
    expected_subject = {'key_type': 'drl_event_key', 'key': json.dumps(
        [identity[k] for k in ('date', 'ticker', 'side')], separators=(',', ':'))}
    if (recipe['recipe_name'] != 'drl_event_research.v1'
            or recipe['subject_instance'] != expected_subject
            or recipe['identity_joins'] or len(blocks) != 1 or len(refs) != 1
            or len(recipe['block_specs']) != 1
            or recipe['block_specs'][0]['block_key'] != 'drl_event_research'
            or recipe['block_specs'][0]['output_fields'] != ['reality.drl_event']
            or recipe['output_mappings'] != [{'output_field': 'reality.drl_event',
                 'block_key': 'drl_event_research', 'when_unavailable': 'refuse'}]
            or blocks[0]['block_key'] != 'drl_event_research'
            or vector['subject']['subject_type'] != 'us_listing_symbol'
            or vector['subject']['value'] != identity['ticker']
            or vector['subject']['identity_state'] != 'single_owner_native'
            or vector['subject']['identity_bridge'] is not None):
        raise OpportunityCaseError('case_native_event_binding_invalid')
    ref_id, ref = next(iter(refs.items()))
    captured = origin['recorded_clock']['value']
    if (ref['owner_store'] != 'price_pressure.event' or ref['native_identity'] != identity
            or ref['subject'] != expected_subject or ref['secondary_subjects']
            or ref['native_digest'] != origin['native_digest']
            or ref['coverage_class'] != 'source_release_snapshot_only'
            or blocks[0]['reference_ids'] != [ref_id]
            or not any(c['class'] == 'system_recorded' and c['field'] == 'capture.captured_at'
                       and c['value_state'] == 'known' and c['value'] == captured
                       for c in ref['clocks'])):
        raise OpportunityCaseError('case_native_event_reference_mismatch')
    slots = vector['slots']
    if {s['construct'] for s in slots} != {'drl_resid_shock', 'drl_filing_coverage'}:
        raise OpportunityCaseError('case_native_event_scope_invalid')
    for slot in slots:
        capture = slot.get('captured_read', {})
        if (slot['owner_ref']['evidence_ref_id'] != ref_id
                or capture.get('captured_at') != captured
                or capture.get('snapshot_sha256') != ref['native_digest']['sha256']
                or any(capture.get(field) != identity[key] for field, key in
                       [('event_date', 'date'), ('ticker', 'ticker'), ('side', 'side')])):
            raise OpportunityCaseError('case_native_event_slot_mismatch')
    return {'identity_contract': 'drl_native_event.v1',
            'owner_store': 'price_pressure.event', 'native_identity': identity}


def _earnings_context_identity(recipe: dict, blocks: list[dict], refs: dict, vector: dict) -> dict | None:
    if vector['asof']['t0_source'] != 'earnings_workspace_context':
        return None
    origin = vector['asof']['t0_evidence_ref']
    identity = origin['native_identity']
    subject = {'key_type':'cik', 'key':vector['subject']['value']}
    if (recipe['recipe_name'] != 'earnings_workspace_k5.v1' or recipe['subject_instance'] != subject
            or recipe['identity_joins'] or len(blocks) != 1 or len(refs) != 1
            or len(recipe['block_specs']) != 1
            or recipe['block_specs'][0]['block_key'] != 'earnings_workspace_context'
            or recipe['block_specs'][0]['output_fields'] != ['company_context']
            or recipe['output_mappings'] != [{'output_field':'company_context','block_key':'earnings_workspace_context','when_unavailable':'refuse'}]
            or blocks[0]['block_key'] != 'earnings_workspace_context'):
        raise OpportunityCaseError('case_earnings_context_binding_invalid')
    rid, ref = next(iter(refs.items())); slot = vector['slots'][0]; link = slot['earnings_context']
    clocks = {c['field']:c['value'] for c in ref['clocks'] if c['value_state'] == 'known'}
    if (ref['owner_store'] != 'earnings.workspace_generation' or ref['native_identity'] != identity
            or ref['subject'] != subject or ref['secondary_subjects']
            or ref['native_digest'] != origin['native_digest']
            or ref['coverage_class'] != 'immutable_generation'
            or blocks[0]['reference_ids'] != [rid] or slot['owner_ref']['evidence_ref_id'] != rid
            or any(clocks.get(field) != link[key] for field,key in [
                ('lifecycle.source_available_at','source_available_at'),('lifecycle.observed_at','observed_at'),('generated_at','generated_at')])):
        raise OpportunityCaseError('case_earnings_context_reference_mismatch')
    return {'identity_contract':'earnings_native_event.v1','owner_store':'earnings.workspace_generation',
            'native_identity':{'event_id':identity['event_id']}}


def compose_case(*, recipe: dict, blocks: list[dict], references: dict[str, dict],
                 vector: dict, evaluation_reference_ids: list[str] | None = None) -> dict:
    """Compose substantive native legs without converting unknowns to scores.

    The caller supplies results from its existing admitted owner readers. Native
    validators establish contract consistency, not authenticity or a new grant.
    Both denominator receipts survive independently; they are never added into
    an apparent count of independent evidence.
    """
    inputs = _copy({"recipe": recipe, "blocks": blocks, "references": references,
                    "vector": vector, "evaluation_reference_ids":
                    evaluation_reference_ids if evaluation_reference_ids is not None else []})
    recipe, blocks, references, vector, evaluation_ids = (
        inputs[k] for k in ("recipe", "blocks", "references", "vector", "evaluation_reference_ids"))
    if (type(blocks) is not list or not 1 <= len(blocks) <= MAX_BLOCKS
            or type(references) is not dict or not 1 <= len(references) <= MAX_REFERENCES
            or type(evaluation_ids) is not list or len(evaluation_ids) > MAX_REFERENCES
            or any(type(i) is not str for i in evaluation_ids)
            or len(set(evaluation_ids)) != len(evaluation_ids)):
        raise OpportunityCaseError("case_input_bounds_invalid")
    try:
        refs = {key: ef.validate_reference(ref) for key, ref in references.items()}
        if any(key != ref["reference_id"] for key, ref in refs.items()):
            raise OpportunityCaseError("reference_key_mismatch")
        checked_blocks = sorted([ef.validate_block(block, references=refs) for block in blocks],
                                key=lambda b: b["block_key"])
        checked_recipe = ef.validate_recipe(recipe)
        if checked_recipe["consumer"]["output_contract"] != SCHEMA:
            raise OpportunityCaseError("case_consumer_not_permitted")
        receipt = ef.compile_recipe(checked_recipe, blocks=checked_blocks, references=refs)
        findings = oe.validate_vector(vector)
        if findings:
            raise OpportunityCaseError("opportunity_vector_invalid")
        if "opportunity_case_k5" not in vector["permitted_consumers"]:
            raise OpportunityCaseError("vector_consumer_not_permitted")
    except ef.EvidenceFoundationError:
        raise OpportunityCaseError("evidence_foundation_invalid") from None
    except (KeyError, TypeError, AttributeError, RecursionError):
        raise OpportunityCaseError("case_input_shape_invalid") from None

    # Reuse K3-E's existing mixed-grain cutoff law. A later correction/claim
    # cannot enter an earlier case merely because its K1 pointer is valid.
    for ref in refs.values():
        for clock in ref["clocks"]:
            if clock["value_state"] == "known" and clock["class"] in {
                    "source_published", "knowable", "observed", "system_recorded", "belief_or_build"}:
                comparison = oe._compare_known_at_to_asof(clock["value"], clock["grain"],
                    vector["asof"]["value"], vector["asof"]["grain"])
                if comparison in {"after", "ambiguous"}:
                    raise OpportunityCaseError("case_reference_after_cutoff")
    for slot in vector["slots"]:
        ref_id = slot["owner_ref"]["evidence_ref_id"]
        if ref_id is not None and ref_id not in refs:
            raise OpportunityCaseError("slot_reference_unresolved")
    if any(i not in refs or refs[i]["object_class"] != "forward_claim" for i in evaluation_ids):
        raise OpportunityCaseError("evaluation_reference_invalid")

    subject = vector["subject"]
    if (subject["subject_type"] == "dataos_security_id"
            and checked_recipe["subject_instance"]["key_type"] == "security_id"
            and checked_recipe["subject_instance"]["key"] != subject["value"]):
        raise OpportunityCaseError("case_subject_mismatch")
    exact_subject = (subject["subject_type"] == "dataos_security_id"
                     and checked_recipe["subject_instance"] == {
                         "key_type": "security_id", "key": subject["value"]})
    native_event = (_captured_drl_identity(checked_recipe, checked_blocks, refs, vector)
                    or _earnings_context_identity(checked_recipe, checked_blocks, refs, vector))
    earnings_native = native_event is not None and native_event["identity_contract"] == "earnings_native_event.v1"
    if native_event is not None and receipt['state'] not in {'complete', 'partial', 'corrected'}:
        raise OpportunityCaseError('case_native_event_evidence_unavailable')
    joined = (exact_subject or native_event is not None) and receipt["state"] in {"complete", "partial", "corrected"}
    # This is binding state, not a claim that native evidence is absent. K1 v1
    # currently refuses multi-owner joins lacking a validated canonical key.
    binding = "exact_owner_native_event" if native_event is not None else "exact_native_subject" if joined else "identity_unresolved"
    by_key = {b["block_key"]: b for b in checked_blocks}
    admitted_ids = set(receipt["block_ids"]) if joined else set()
    context = {}
    for leg in _CONTEXT_LEGS:
        keys = [] if native_event is not None and not earnings_native else [m["block_key"] for m in checked_recipe["output_mappings"]
                if m["output_field"] == leg]
        selected = [by_key[k] for k in dict.fromkeys(keys) if k in by_key]
        usable = [b for b in selected if b["evidence_block_id"] in admitted_ids
                  and b["coverage"]["included"] > 0
                  and b["coverage"]["state"] not in {"rights_blocked", "unavailable", "conflicted"}]
        context[leg] = {
            "state": ("available" if all(b["coverage"]["state"] == "complete" for b in usable)
                      else "partial") if usable else "unavailable",
            "reason": None if usable else ("identity_unresolved" if selected and not joined
                                            else "native_context_unavailable"),
            "block_ids": [b["evidence_block_id"] for b in usable],
            "withheld_block_ids": [b["evidence_block_id"] for b in selected if b not in usable],
        }
    projection = vector["projection"]
    slots = {s["construct"]: s for s in vector["slots"]}
    for leg, constructs in {
        "transmission": ("macro_chain_state",),
        "company_context": ("forensics_scalars", "capital_structure_supply", "eightk_recency",
                            "sue_surprise", "estimate_revisions", "earnings_reported_revenue"),
    }.items():
        native_slots = [slots[c] for c in constructs if c in slots]
        context[leg]["owner_slots"] = native_slots
        if any(s["included_in_composition"] for s in native_slots) and not context[leg]["block_ids"]:
            context[leg].update(state="partial", reason="native_vector_context_only")
    selected_slots = lambda leg: [slots[c] for c in projection[leg]["slot_refs"]]
    origin = vector["asof"]["t0_evidence_ref"]
    identity = {"subject": {k: subject[k] for k in ("subject_type", "value")},
                "asof": {k: vector["asof"][k]
                for k in ("value", "grain", "t0_source")},
                "origin": {k: origin[k] for k in ("owner_store", "native_identity")}}
    if native_event is not None:
        identity = native_event
    case = {
        "schema": SCHEMA, "case_id": "opc_" + _hash(identity),
        "subject": subject, "asof": vector["asof"], "generated_at": vector["generated_at"],
        "inputs": {"recipe": checked_recipe, "blocks": sorted(checked_blocks, key=lambda b: b["block_key"]),
                   "references": refs, "vector": vector,
                   "evaluation_reference_ids": sorted(evaluation_ids)},
        "reality": {**projection["observed"], "slots": selected_slots("observed")},
        "inferred": {**projection["inferred"], "slots": selected_slots("inferred")},
        **context,
        "market_incorporation": projection["market_reflection"],
        "strongest_unresolved_fact": projection["strongest_unresolved_fact"],
        "failed_gates": projection["failed_or_unavailable_gates"],
        "next_observables": {
            "vector": projection["next_observable"],
            "evidence_blocks": [{"block_id": b["evidence_block_id"], **b["next_observable"]}
                                for b in checked_blocks],
        },
        "entry_availability": projection["entry_availability"],
        "economic_cause_hypothesis": vector["economic_cause_hypothesis"],
        "evaluation_refs": [refs[i] for i in sorted(evaluation_ids)],
        "research_state": "partial" if native_event is not None or not joined or receipt["state"] != "complete"
                          or vector["compilation_state"] != "complete" else "complete",
        "evidence_binding": {"state": binding, "recipe_receipt": receipt,
                             "scope": "single_owner_event" if native_event is not None else "exact_canonical_subject" if joined else "native_subjects_only"},
        "denominators": {"evidence": receipt["denominator"], "vector": vector["denominator"]},
        "dominant_degradation": {"evidence": receipt["dominant_degradation"],
                                 "vector": vector["dominant_degradation"]},
        "calibrated": {"state": "unavailable", "opportunity_score": None,
                       "confidence": None, "probability": None, "impact": None},
        "authority": dict(ef.ALL_FALSE_AUTHORITY),
        "permitted_consumers": ["research_session"] if native_event is not None else ["research_session", "entry_radar_research_projection"],
        "owner_io_performed": False,
    }
    case["content_sha256"] = _hash(case)
    return _copy(case)


def validate_case(case: object) -> dict:
    checked = _copy(case)
    if type(checked) is not dict or checked.get("schema") != SCHEMA:
        raise OpportunityCaseError("case_schema_invalid")
    try:
        expected = compose_case(**checked["inputs"])
    except (KeyError, TypeError):
        raise OpportunityCaseError("case_input_shape_invalid") from None
    if ef.canonical_json_bytes(checked) != ef.canonical_json_bytes(expected):
        raise OpportunityCaseError("case_projection_or_identity_mismatch")
    return expected
