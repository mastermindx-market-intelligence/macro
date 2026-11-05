"""Pure explanation of a finalized owner cohort from qualified reader receipts.

This compiler owns no selection, identity, membership, state, rights or ledger
resolution. Its receipt envelope is an adapter boundary, not a new reader.
Current latest-published identity and date-only owner artifacts do not qualify.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Mapping

import jsonschema
from engine.theme_graph.identity import local_theme_node_id, theme_node_id

SCHEMA = "mastermind.selection_cohort_read.v1"
FLAGS = ("can_rank", "can_size", "can_gate", "can_originate_signal",
         "can_add_candidates", "can_escalate")
ROOT = Path(__file__).resolve().parents[2]
LIMITATIONS = [
    "Qualified owner receipts are supplied by callers; digests do not prove source authenticity.",
    "Fractions overlap and count selected securities over the complete owner cohort, including rows with missing coverage; distinct securities may share an issuer graph node.",
    "Graph membership describes recorded membership, not economic exposure or return prediction.",
    "Internal explanation grants no public display, candidate, selection or trading authority.",
    "This pure compiler does not mount a consumer or register an Evaluation consequence episode.",
]


def content_sha256(value: Any) -> str:
    """Stable JSON content identity; reject lossy/default and nonfinite values."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _time(value: Any) -> dt.datetime:
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("precise owner timestamp required; date-only clocks do not qualify")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid owner timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("owner timestamp needs an explicit timezone")
    return parsed


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {name}")
    return value


def _hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid {name}")
    return value


def _exact_keys(value: Mapping, keys: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"invalid {label} fields")


def _selection(selection: Mapping) -> dict:
    keys = {"owner", "source_schema", "source_ref", "source_sha256", "generation_id",
            "cohort_scope", "effective_at", "selected_at", "known_at", "n_selected",
            "rows", "rows_sha256", "ordered_identity_sha256", "ordered_reasons_sha256"}
    _exact_keys(selection, keys, "owner selection")
    for key in ("owner", "source_schema", "source_ref", "generation_id", "cohort_scope"):
        _text(selection[key], key)
    effective, selected, known = (_time(selection[k]) for k in ("effective_at", "selected_at", "known_at"))
    if effective > selected or known > selected:
        raise ValueError("source effective/knowledge cutoff exceeds source selection event")
    rows = selection["rows"]
    if not isinstance(rows, list) or type(selection["n_selected"]) is not int or selection["n_selected"] != len(rows):
        raise ValueError("owner must declare complete cohort denominator before preview")
    ids = []
    for row in rows:
        _exact_keys(row, {"selection_id", "original_identity", "original_reasons", "source_row"}, "selected row")
        ids.append(_text(row["selection_id"], "selection_id"))
        if not isinstance(row["source_row"], dict):
            raise ValueError("original source_row must be an object")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate source selection identity")
    expected = {"rows_sha256": content_sha256(rows),
                "ordered_identity_sha256": content_sha256([r["original_identity"] for r in rows]),
                "ordered_reasons_sha256": content_sha256([r["original_reasons"] for r in rows])}
    _hash(selection["source_sha256"], "source_sha256")
    for key, digest in expected.items():
        if _hash(selection[key], key) != digest:
            raise ValueError(f"owner {key} mismatch")
    content_sha256(selection)
    return copy.deepcopy(dict(selection))


COMMON = {"status", "qualification", "owner_schema", "receipt_ref", "receipt_sha256",
          "generation_id", "effective_at", "known_at", "available_at", "valid_until",
          "selection_id", "original_identity_sha256", "selection_sha256"}
IDENTITY = COMMON | {"security_id", "graph_node_ids", "historical_identity_claim"}
MEMBERSHIP = COMMON | {"security_id", "complete", "memberships", "identity_receipt_ref", "identity_receipt_sha256"}
MEMBERSHIP_REF = MEMBERSHIP - {"memberships"} | {"observed_count"}
ADAPTER_FAILURES = {"MISSING_RECEIPT", "INVALID_ADAPTER_FIELDS", "SELECTION_IDENTITY_BINDING_MISMATCH",
                    "OWNER_UNAVAILABLE", "UNQUALIFIED_OWNER_QUERY", "QUERY_CUTOFF_MISMATCH",
                    "LATE_KNOWN_RECEIPT", "STALE_RECEIPT", "IMPRECISE_OR_MISSING_OWNER_PROVENANCE",
                    "IDENTITY_NOT_QUALIFIED_AT_SELECTION", "INCOMPLETE_OR_MISMATCHED_MEMBERSHIP_QUERY"}


def _qualified(receipt: Any, selection: dict, row: dict, kind: str) -> tuple[bool, str]:
    """Validate a closed adapter of an upstream query, never resolve owner history."""
    if not isinstance(receipt, Mapping):
        return False, "MISSING_RECEIPT"
    keys = {"identity": IDENTITY, "membership": MEMBERSHIP, "membership_ref": MEMBERSHIP_REF}[kind]
    if set(receipt) != keys:
        return False, "INVALID_ADAPTER_FIELDS"
    if (receipt["selection_id"] != row["selection_id"]
            or receipt["original_identity_sha256"] != content_sha256(row["original_identity"])
            or receipt["selection_sha256"] != content_sha256(selection)):
        return False, "SELECTION_IDENTITY_BINDING_MISMATCH"
    if receipt["status"] != "OK":
        return False, "OWNER_UNAVAILABLE"
    if receipt["qualification"] != "EXACT_PIT_QUERY":
        return False, "UNQUALIFIED_OWNER_QUERY"
    try:
        for key in ("owner_schema", "receipt_ref", "generation_id"):
            _text(receipt[key], key)
        _hash(receipt["receipt_sha256"], "receipt_sha256")
        if (_time(receipt["effective_at"]) != _time(selection["effective_at"])
                or _time(receipt["known_at"]) != _time(selection["known_at"])):
            return False, "QUERY_CUTOFF_MISMATCH"
        if _time(receipt["available_at"]) > _time(selection["known_at"]):
            return False, "LATE_KNOWN_RECEIPT"
        if receipt["valid_until"] is not None and _time(receipt["valid_until"]) <= _time(selection["effective_at"]):
            return False, "STALE_RECEIPT"
    except (ValueError, KeyError, TypeError):
        return False, "IMPRECISE_OR_MISSING_OWNER_PROVENANCE"
    if not isinstance(receipt["security_id"], str) or not re.fullmatch(r"SEC:[^\s]+", receipt["security_id"]):
        return False, "IDENTITY_NOT_QUALIFIED_AT_SELECTION"
    if kind == "identity":
        nodes = receipt["graph_node_ids"]
        if (receipt["historical_identity_claim"] is not True or not isinstance(nodes, list)
                or not nodes or any(not isinstance(x, str) or not re.fullmatch(r"co:[^\s]+", x) for x in nodes)
                or len(set(nodes)) != len(nodes)):
            return False, "IDENTITY_NOT_QUALIFIED_AT_SELECTION"
    elif (receipt["complete"] is not True
          or (kind == "membership" and not isinstance(receipt["memberships"], list))
          or (kind == "membership_ref" and (type(receipt["observed_count"]) is not int or receipt["observed_count"] < 0))):
        return False, "INCOMPLETE_OR_MISMATCHED_MEMBERSHIP_QUERY"
    return True, "OK"


def _governed_concept_identity(row: Mapping) -> bool:
    """Check exact identity with incumbent helpers, without normalizing a receipt."""
    node, kind, family, native = (row.get(k) for k in ("node_id", "kind", "source_family", "native_id"))
    try:
        if kind == "local_theme":
            return (isinstance(family, str) and isinstance(native, str)
                    and node == local_theme_node_id(family, native) == f"ltheme:{family}:{native}")
        if kind == "canonical_theme":
            return (isinstance(node, str) and node.startswith("theme:")
                    and family is None and native is None and node == theme_node_id(node[6:]))
    except ValueError:
        return False
    return False


def _concept_metadata(row: Mapping) -> bool:
    """Check owner graph species/namespace and qualified destination references."""
    if (not _governed_concept_identity(row)
            or row.get("node_kind") != {"local_theme": "local_theme", "canonical_theme": "theme"}.get(row.get("kind"))
            or (row.get("kind") == "canonical_theme" and not re.fullmatch(r"theme:[^\s:]+", row["node_id"]))):
        return False
    ids, nodes = row.get("canonical_node_ids"), row.get("canonical_nodes")
    if ids is not None and (not isinstance(ids, list) or any(not isinstance(x, str) or not re.fullmatch(r"theme:[^\s:]+", x) for x in ids)
                            or len(set(ids)) != len(ids)):
        return False
    if not isinstance(nodes, list) or len(nodes) != len(ids or []):
        return False
    for item, dest in zip(nodes, ids or []):
        try:
            _exact_keys(item, {"node_id", "kind", "receipt_ref", "receipt_sha256"}, "canonical destination")
            if item["node_id"] != dest or item["kind"] != "theme":
                return False
            _text(item["receipt_ref"], "canonical owner receipt")
            _hash(item["receipt_sha256"], "canonical owner receipt hash")
        except (ValueError, TypeError):
            return False
    return True


def _membership(row: Mapping, identity: Mapping, selection: dict) -> tuple[bool, str]:
    if not isinstance(row, Mapping) or row.get("member_node_id") not in identity["graph_node_ids"]:
        return False, "MEMBERSHIP_IDENTITY_MISMATCH"
    fields = {"member_node_id", "node_id", "kind", "node_kind", "source_family", "native_id",
              "canonical_node_ids", "canonical_nodes", "evidence_ref", "evidence_sha256",
              "effective_from", "effective_until", "known_from", "rights_status", "rights_receipt_ref"}
    if set(row) != fields or not _concept_metadata(row):
        return False, "INVALID_CONCEPT_IDENTITY_OR_CANONICAL_REFERENCES"
    try:
        _text(row.get("node_id"), "concept graph node_id")
        _text(row.get("evidence_ref"), "evidence_ref")
        _hash(row.get("evidence_sha256"), "evidence_sha256")
        if _time(row["effective_from"]) > _time(selection["effective_at"]):
            return False, "FUTURE_MEMBERSHIP"
        if row.get("effective_until") is not None and _time(row["effective_until"]) <= _time(selection["effective_at"]):
            return False, "STALE_MEMBERSHIP"
        if _time(row["known_from"]) > _time(selection["known_at"]):
            return False, "LATE_KNOWN_MEMBERSHIP"
    except (KeyError, TypeError, ValueError):
        return False, "IMPRECISE_OR_MISSING_MEMBERSHIP_PROVENANCE"
    if row.get("rights_status") != "ALLOWED" or not row.get("rights_receipt_ref"):
        return False, "RIGHTS_UNAVAILABLE"
    return True, "OK"


@lru_cache(maxsize=1)
def _state_validator():
    # Exact frozen owner definitions are attributed in the output contract.
    owner = _validator().schema["$defs"]["owner_state_read_contract"]
    return jsonschema.Draft202012Validator(owner)


def _state(receipt: Any, concept: Mapping, selection: dict) -> tuple[dict | None, str]:
    if not isinstance(receipt, Mapping):
        return None, "MISSING_STATE"
    try:
        _state_validator().validate(receipt)
        if receipt["subject_id"] != concept["node_id"]:
            return None, "STATE_SUBJECT_MISMATCH"
        if receipt["generation_id"] != receipt["state_sha256"][:32]:
            return None, "STATE_GENERATION_DIGEST_MISMATCH"
        if (_time(receipt["effective_at"]) != _time(selection["effective_at"])
                or _time(receipt["known_at"]) != _time(selection["known_at"])):
            return None, "STATE_CUTOFF_MISMATCH"
        if receipt["state_generated_at"] is not None and _time(receipt["state_generated_at"]) > _time(selection["known_at"]):
            return None, "STATE_NOT_YET_EMITTED"
        if receipt["status"] == "UNAVAILABLE":
            return None, receipt["reason_codes"][0]
        if receipt["subject"]["node_id"] != concept["node_id"]:
            return None, "STATE_SUBJECT_MISMATCH"
        subject = receipt["subject"]
        if (not _governed_concept_identity(subject)
                or any(subject[key] != concept[key] for key in ("kind", "node_id", "source_family", "native_id"))):
            return None, "STATE_SUBJECT_IDENTITY_MISMATCH"
        content_sha256(receipt)
    except (jsonschema.ValidationError, ValueError, KeyError, TypeError):
        return None, "INVALID_STATE_RECEIPT"
    return copy.deepcopy(dict(receipt)), "OK"


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads((ROOT / "contracts/theme_graph/selection_cohort_read.v1.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema)


def validate_selection_cohort(document: Mapping) -> None:
    """Validate shape, content identity and invariant owner preservation."""
    _validator().validate(document)
    source = _selection(document["source_selection"])
    if document["selection_sha256"] != content_sha256(source):
        raise ValueError("selection digest mismatch")
    if [r["source"] for r in document["selected"]] != source["rows"]:
        raise ValueError("selected source order or reasons changed")
    coverage, availability = _derive(document)
    if document["coverage"] != coverage or document["availability"] != availability:
        raise ValueError("coverage or availability disagrees with selected receipts and concept joins")
    if (document["version"]["number"] == 1) != (document["version"]["corrects"] is None):
        raise ValueError("explanation correction link disagrees with version")
    link = document["consequence_link"]
    if (link["status"] == "UNREGISTERED") != (link["episode_ref"] is None):
        raise ValueError("neutral Evaluation linkage has inconsistent owner reference")
    unsigned = {k: v for k, v in document.items() if k != "explanation_id"}
    if document["explanation_id"] != "sha256:" + content_sha256(unsigned):
        raise ValueError("explanation content digest mismatch")


def _derive(document: Mapping) -> tuple[dict, dict]:
    """One derivation governs composition and output-validation epistemic claims."""
    source, selected, concepts = document["source_selection"], document["selected"], document["concepts"]
    coverage = {k: [] for k in ("missing_identity", "missing_membership", "missing_rights", "missing_state",
                               "no_recorded_membership", "multi_theme", "unmapped_local")}
    by_node = {c["node_id"]: c for c in concepts}
    if len(by_node) != len(concepts):
        raise ValueError("duplicate concept")
    security_ids = [r["security_id"] for r in selected if r["security_id"] is not None]
    if len(set(security_ids)) != len(security_ids):
        raise ValueError("duplicate canonical security in source cohort")
    for c in concepts:
        if not _concept_metadata(c):
            raise ValueError("invalid concept species, local identity or canonical destination")
        actual = [r for r in selected if c["node_id"] in r["concept_node_ids"]]
        if (c["selected_ids"] != [r["source"]["selection_id"] for r in actual]
                or c["security_ids"] != [r["security_id"] for r in actual]
                or c["n_selected_in_concept"] != len(actual) or not source["n_selected"]
                or c["fraction_of_selected"] != len(actual) / source["n_selected"]):
            raise ValueError("concept count, fraction or ordered membership disagrees with cohort")
        if (c["state"] is None) == (c["state_reason"] == "OK"):
            raise ValueError("state presence contradicts state reason")
        if c["state"] is not None:
            state, _ = _state(c["state"], c, source)
            if state is None:
                raise ValueError("concept state has inconsistent subject, eligibility, generation or cutoff")
        evidence_ids = {e["selection_id"] for e in c["evidence"]}
        if evidence_ids != set(c["selected_ids"]) or len({content_sha256(e) for e in c["evidence"]}) != len(c["evidence"]):
            raise ValueError("concept evidence does not cover exactly its selected securities")
    for row in selected:
        raw, identity, membership = row["source"], row["identity_receipt"], row["membership_receipt"]
        sid, nodes, summary = raw["selection_id"], row["concept_node_ids"], row["membership_summary"]
        if any(node not in by_node for node in nodes):
            raise ValueError("selected reference has no concept")
        if row["security_id"] is None:
            if identity is not None or membership is not None or nodes or not row["reason_codes"]:
                raise ValueError("missing identity contradicts receipt, joins or row reasons")
            if len(row["reason_codes"]) != 1 or row["reason_codes"][0] not in ADAPTER_FAILURES:
                raise ValueError("missing identity requires a typed adapter failure")
            coverage["missing_identity"].append(sid)
        else:
            ok, _ = _qualified(identity, source, raw, "identity")
            if not ok or identity["security_id"] != row["security_id"]:
                raise ValueError("canonical security and qualified identity receipt disagree")
            if membership is None:
                if nodes or not row["reason_codes"]:
                    raise ValueError("missing membership contradicts joins or row reasons")
                if len(row["reason_codes"]) != 1 or row["reason_codes"][0] not in ADAPTER_FAILURES:
                    raise ValueError("missing membership requires a typed adapter failure")
                coverage["missing_membership"].append(sid)
            else:
                ok, _ = _qualified(membership, source, raw, "membership_ref")
                if (not ok or membership["security_id"] != row["security_id"]
                        or membership["identity_receipt_ref"] != identity["receipt_ref"]
                        or membership["identity_receipt_sha256"] != identity["receipt_sha256"]):
                    raise ValueError("membership receipt is not bound to the row and identity query")
        if membership is None:
            if summary != {"duplicate_evidence_count": 0, "rejected_membership_reasons": [], "rejected_rights_reasons": []}:
                raise ValueError("unread membership has claimed evidence outcomes")
        else:
            failures, rights = summary["rejected_membership_reasons"], summary["rejected_rights_reasons"]
            evidence = [e for node in nodes for e in by_node[node]["evidence"] if e["selection_id"] == sid]
            for e in evidence:
                if e["security_id"] != row["security_id"] or e["member_node_id"] not in identity["graph_node_ids"]:
                    raise ValueError("membership evidence contradicts selected identity bridge")
            if summary["duplicate_evidence_count"] and not evidence:
                raise ValueError("duplicate evidence requires a represented original evidence row")
            observed = membership["observed_count"]
            if observed != len(evidence) + summary["duplicate_evidence_count"] + len(failures) + len(rights):
                raise ValueError("membership evidence and rejection counts disagree with owner read")
            if row["reason_codes"] != list(dict.fromkeys(failures + rights)):
                raise ValueError("row reasons disagree with membership outcomes")
            if failures: coverage["missing_membership"].append(sid)
            if rights: coverage["missing_rights"].append(sid)
            if observed == 0: coverage["no_recorded_membership"].append(sid)
        if any(by_node[n]["state"] is None for n in nodes): coverage["missing_state"].append(sid)
        if len(nodes) > 1: coverage["multi_theme"].append(sid)
        if any(by_node[n]["kind"] == "local_theme" and not by_node[n]["canonical_node_ids"] for n in nodes):
            coverage["unmapped_local"].append(sid)
    shared = sum(c["n_selected_in_concept"] >= 2 for c in concepts)
    missing = any(coverage[k] for k in ("missing_identity", "missing_membership", "missing_rights", "missing_state"))
    coverage = dict(n_selected=source["n_selected"], n_identity_qualified=len(security_ids),
                    n_concepts=len(concepts), n_shared_concepts=shared, **coverage)
    availability = dict(status="EMPTY_SELECTION" if not source["rows"] else "PARTIAL" if missing else "OK",
                        overlap="EMPTY_SELECTION" if not source["rows"] else "OBSERVED_SHARED_CONCEPTS" if shared else "UNDETERMINED" if missing else "NO_MEANINGFUL_OVERLAP")
    return coverage, availability


def compose_selection_cohort(selection: Mapping, *, identity_reads: Mapping,
                             membership_reads: Mapping, state_reads: Mapping,
                             previous_explanation: Mapping | None = None,
                             consequence_reference: Mapping | None = None) -> dict:
    """Compile the complete owner set; missing qualified joins remain selected rows.

    Identity/membership adapter envelopes must echo exact upstream PIT query,
    provenance and availability. They must not wrap the current-only navigation
    reader as a historical identity claim. State accepts the owner's closed reader.
    Correction versions use the same immutable selection and original cutoffs;
    later-known facts need a separately labeled owner restatement contract.
    """
    source = _selection(selection)
    digest = content_sha256(source)
    if previous_explanation is not None:
        validate_selection_cohort(previous_explanation)
        if previous_explanation["selection_sha256"] != digest:
            raise ValueError("correction must reference the same immutable source selection")
    if consequence_reference is not None:
        _exact_keys(consequence_reference, {"owner", "episode_ref"}, "Evaluation linkage")
        if consequence_reference["owner"] != "Evaluation OS/QLedger":
            raise ValueError("consequence linkage belongs to existing Evaluation owner")
        _text(consequence_reference["episode_ref"], "owner episode_ref")
    result = dict(schema=SCHEMA, authority_ceiling="research_internal_only",
                  **{flag: False for flag in FLAGS}, source_selection=source,
                  selection_sha256=digest, selected=[], concepts=[],
                  coverage={}, availability={},
                  version={"number": 1 if previous_explanation is None else previous_explanation["version"]["number"] + 1,
                           "corrects": None if previous_explanation is None else previous_explanation["explanation_id"],
                           "basis": "AS_KNOWN_AT_SELECTION"},
                  consequence_link={"owner": "Evaluation OS/QLedger", "status": "UNREGISTERED" if consequence_reference is None else "OWNER_REFERENCE_SUPPLIED",
                                    "episode_ref": None if consequence_reference is None else consequence_reference["episode_ref"]},
                  limitations=list(LIMITATIONS))
    concepts, resolved_ids = {}, set()
    for raw in source["rows"]:
        sid = raw["selection_id"]
        selected = dict(source=copy.deepcopy(raw), security_id=None, identity_receipt=None,
                        membership_receipt=None, concept_node_ids=[], reason_codes=[],
                        membership_summary={"duplicate_evidence_count": 0, "rejected_membership_reasons": [], "rejected_rights_reasons": []})
        result["selected"].append(selected)
        identity = identity_reads.get(sid)
        ok, reason = _qualified(identity, source, raw, "identity")
        if not ok:
            selected["reason_codes"].append(reason)
            continue
        if identity["security_id"] in resolved_ids:
            raise ValueError("owner cohort repeats one canonical security; multiplicity contract required")
        resolved_ids.add(identity["security_id"])
        selected.update(security_id=identity["security_id"], identity_receipt=copy.deepcopy(dict(identity)))
        membership = membership_reads.get(sid)
        ok, reason = _qualified(membership, source, raw, "membership")
        if ok and (membership["security_id"] != identity["security_id"]
                   or membership["identity_receipt_ref"] != identity["receipt_ref"]
                   or membership["identity_receipt_sha256"] != identity["receipt_sha256"]):
            ok, reason = False, "INCOMPLETE_OR_MISMATCHED_MEMBERSHIP_QUERY"
        if not ok:
            selected["reason_codes"].append(reason)
            continue
        selected["membership_receipt"] = {k: copy.deepcopy(v) for k, v in membership.items() if k != "memberships"}
        selected["membership_receipt"]["observed_count"] = len(membership["memberships"])
        for member in membership["memberships"]:
            ok, reason = _membership(member, identity, source)
            if not ok:
                bucket = "rejected_rights_reasons" if reason == "RIGHTS_UNAVAILABLE" else "rejected_membership_reasons"
                selected["membership_summary"][bucket].append(reason)
                continue
            node = member["node_id"]
            metadata = {k: copy.deepcopy(member[k]) for k in ("node_id", "kind", "node_kind", "source_family", "native_id", "canonical_node_ids", "canonical_nodes")}
            if node not in concepts:
                state, state_reason = _state(state_reads.get(node), metadata, source)
                concepts[node] = dict(**metadata, selected_ids=[], security_ids=[], evidence=[],
                                      n_selected_in_concept=0, fraction_of_selected=None,
                                      state=state, state_reason=state_reason)
            concept = concepts[node]
            if any(concept[k] != metadata[k] for k in metadata):
                raise ValueError("conflicting qualified concept metadata; owner reconciliation required")
            evidence = dict(selection_id=sid, security_id=identity["security_id"], member_node_id=member["member_node_id"],
                            **{k: member[k] for k in ("evidence_ref", "evidence_sha256", "rights_receipt_ref")})
            if evidence not in concept["evidence"]:
                concept["evidence"].append(evidence)
            else:
                selected["membership_summary"]["duplicate_evidence_count"] += 1
            if sid not in concept["selected_ids"]:
                concept["selected_ids"].append(sid)
                concept["security_ids"].append(identity["security_id"])
                selected["concept_node_ids"].append(node)
        summary = selected["membership_summary"]
        selected["reason_codes"] = list(dict.fromkeys(summary["rejected_membership_reasons"] + summary["rejected_rights_reasons"]))
    for node in sorted(concepts):
        concept = concepts[node]
        concept["n_selected_in_concept"] = len(concept["selected_ids"])
        concept["fraction_of_selected"] = len(concept["selected_ids"]) / source["n_selected"]
        result["concepts"].append(concept)
    result["coverage"], result["availability"] = _derive(result)
    result["explanation_id"] = "sha256:" + content_sha256(result)
    validate_selection_cohort(result)
    return result
