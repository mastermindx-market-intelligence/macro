"""Private comparison orchestration under the incumbent Read owner.

All qualification callbacks are explicitly injected trusted server owners.
This module supplies no production resolver, entitlement, storage or network.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
import copy
import re
from typing import Callable, Any

SCHEMA = "brain.research_comparison.v1"
MAX_CHARS = 12_000
MAX_PREVIEWS = 3
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_AXES = {"subject", "horizon", "units", "currency", "scenario"}
_SIDE = {"report_id", "rio_artifact_sha256", "source_pdf_sha256",
         "extracted_text_sha256", "claim_index"}


@dataclass(frozen=True)
class QualifiedBasis:
    """Server-owned adjudication; never constructed from tool argument fields."""
    bindings: tuple[tuple[str, str, str, str, int], tuple[str, str, str, str, int]]
    bases: tuple[Mapping[str, str], Mapping[str, str]]
    subjects: tuple[Mapping[str, str], Mapping[str, str]]
    provenance: str
    families: tuple[str, str] = ("", "")


@dataclass(frozen=True)
class QualifiedRevision:
    bindings: tuple[tuple[str, str, str, str, int], tuple[str, str, str, str, int]]
    kind: str
    support_quote: str
    provenance: str


@dataclass(frozen=True)
class ComparisonOwners:
    semantic: Callable[[Any, Any], bool]
    preflight: Callable[[Any, tuple[str, ...], datetime], bool]
    commit: Callable[[Any, tuple[str, ...], datetime], bool]
    basis: Callable[[Any, str, tuple[Any, Any]], QualifiedBasis | None] | None = None
    revision: Callable[[Any, str, tuple[Any, Any]], QualifiedRevision | None] | None = None


class _Unavailable(ValueError):
    pass


def failure(reason: str, *, denied: bool = False) -> dict:
    return {"schema": SCHEMA, "state": "DENIED" if denied else "UNAVAILABLE",
            "reason": reason, "authority": "descriptive_research_only"}


def _require(value: bool, reason: str) -> None:
    if not value:
        raise _Unavailable(reason)


def _strings(value: Any) -> int:
    if isinstance(value, str):
        return len(value)
    if isinstance(value, Mapping):
        return sum(_strings(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return sum(_strings(item) for item in value)
    return 0


def _parse(service, request: Any) -> dict:
    _require(type(request) is dict, "INVALID_REQUEST")
    action = request.get("action")
    keys = {"action", "left", "right"}
    if action == "compare":
        keys |= {"basis_ref"}
        if "revision_ref" in request:
            keys.add("revision_ref")
    _require(action in {"prepare", "compare"} and set(request) == keys, "INVALID_REQUEST")
    for name in ("left", "right"):
        side = request[name]
        _require(type(side) is dict and set(side) == ({"report_id"} if action == "prepare" else _SIDE), "INVALID_REQUEST")
        _require(isinstance(service._validate_report_id(side["report_id"]), str), "INVALID_REQUEST")
        if action == "compare":
            _require(type(side["claim_index"]) is int and 0 <= side["claim_index"] < 30, "INVALID_REQUEST")
            for key in _SIDE - {"report_id", "claim_index"}:
                _require(type(side[key]) is str and _HEX.fullmatch(side[key]) is not None, "INVALID_REQUEST")
    if action == "compare":
        for key in ("basis_ref", "revision_ref"):
            if key in request:
                _require(type(request[key]) is str and _REF.fullmatch(request[key]) is not None, "INVALID_REQUEST")
    return request


def _source_binding(leg) -> tuple[str, str, str, str]:
    return (leg["id"], leg["extracted"]["source_pdf_sha256"],
            leg["extracted"]["extracted_text_sha256"], leg["artifact_sha"])


def _binding(leg) -> tuple[str, str, str, str, int]:
    """Immutable selected identity captured from the validated request."""
    return leg["selected_binding"]


def _bindings_match(bindings, expected) -> bool:
    # bool compares equal to integers in Python; selected indices require the
    # exact validated integer identity, including inside trusted owner returns.
    return (type(bindings) is tuple and len(bindings) == 2 and
            all(type(x) is tuple and len(x) == 5 and
                all(type(v) is str for v in x[:4]) and type(x[4]) is int
                for x in bindings) and bindings == expected)


def _revision_identity(extracted) -> tuple:
    return tuple(extracted.get(k) for k in ("source_pdf_sha256", "extracted_text_sha256",
        "extractor_name", "extractor_version", "text", "char_count", "byte_count"))


def _load(service, ctx, items, side, owners, action):
    from engine.research_intelligence.schema import validate_rio
    from engine.research_intelligence.selection import validate_source_context_receipt
    rid = side["report_id"]
    item = copy.deepcopy(items[rid])
    institution = item.get("institution")
    _require(type(institution) is str and bool(institution.strip()), "INSTITUTION_UNQUALIFIED")
    coverage, extracted, _segments, text_extra = service._resolve_text(rid, item)
    _require(coverage == "FULL_TEXT" and extracted is not None, "SOURCE_UNAVAILABLE")
    extracted = copy.deepcopy(extracted)
    state, stored, warnings = service._rio_state(rid, extracted)
    _require(state == "CURRENT" and stored is not None, "RIO_UNAVAILABLE")
    _require(owners.semantic(ctx, stored) is True, "SEMANTIC_UNQUALIFIED")
    rio = validate_rio(stored.rio, require_grounded_claims=True)
    _require(rio["document"]["id"] == rid and rio["document"]["institution"] == institution
        and rio["document"]["content_sha256"] == extracted["extracted_text_sha256"], "RIO_SOURCE_MISMATCH")
    receipt = copy.deepcopy(stored.receipt)
    _require(isinstance(receipt, Mapping) and receipt.get("prompt_version") == "mastermind.research_intelligence.extractor.v3", "RIO_VERSION_UNAVAILABLE")
    context = validate_source_context_receipt(receipt.get("source_context"), expected_content_sha256=extracted["extracted_text_sha256"])
    _require(type(stored.artifact_sha256) is str and _HEX.fullmatch(stored.artifact_sha256) is not None, "RIO_UNAVAILABLE")
    leg = {"id": rid, "item": item, "extracted": extracted, "stored": stored,
           "rio": rio, "context": context, "receipt": receipt, "artifact_sha": stored.artifact_sha256, "warnings": list(dict.fromkeys(list(text_extra) + list(warnings))), "institution": institution}
    if action == "compare":
        bound = _source_binding(leg)
        _require(bound == (rid, side["source_pdf_sha256"], side["extracted_text_sha256"], side["rio_artifact_sha256"]), "REQUESTED_REVISION_UNAVAILABLE")
        _require(side["claim_index"] < len(rio["claims"]), "CLAIM_UNAVAILABLE")
        leg["selected_binding"] = (*bound, side["claim_index"])
        leg["selected_ref"] = _ref(leg, side["claim_index"])
    return leg


def _ref(leg, index):
    rid, pdf, text, artifact = _source_binding(leg)
    return {"report_id": rid, "source_pdf_sha256": pdf, "extracted_text_sha256": text,
            "rio_artifact_sha256": artifact, "claim_index": index}


def _preview(leg, index):
    from engine.qual_extraction import quote_span_verified
    claim = leg["rio"]["claims"][index]
    body = leg["extracted"]["text"]
    _require(quote_span_verified(body, claim["statement"], require_complete_clause=True), "CLAIM_UNAVAILABLE")
    evidence = []
    raw = body.encode("utf-8")
    for item in claim["evidence"]:
        quote = item["quote_span"]
        encoded = quote.encode("utf-8")
        start = raw.find(encoded)
        if start >= 0 and quote_span_verified(body, quote, require_complete_clause=True):
            evidence.append({"text": quote, "start_byte": start, "end_byte": start + len(encoded),
                "passage_text_sha256": hashlib.sha256(encoded).hexdigest()})
    _require(bool(evidence), "CLAIM_UNAVAILABLE")
    return {"ref": _ref(leg, index), "evidence": evidence}


def _public_leg(leg):
    return {"report_id": leg["id"], "institution": leg["institution"],
            "rio_artifact_sha256": leg["artifact_sha"],
            "revision_state": "CURRENT", "source_context": dict(leg["context"])}


def _basis(owners, ctx, request, legs):
    _require(callable(owners.basis), "BASIS_UNAVAILABLE")
    bindings = tuple(_binding(x) for x in legs)
    qualified = owners.basis(ctx, request["basis_ref"], legs)
    _require(type(qualified) is QualifiedBasis and _bindings_match(qualified.bindings, bindings)
        and type(qualified.provenance) is str and bool(qualified.provenance.strip()), "BASIS_UNQUALIFIED")
    _require(len(qualified.bases) == len(qualified.subjects) == len(qualified.families) == 2, "BASIS_UNQUALIFIED")
    for leg, basis, subject in zip(legs, qualified.bases, qualified.subjects):
        _require(isinstance(basis, Mapping) and set(basis) == _AXES and all(type(v) is str and v.strip() for v in basis.values()), "BASIS_UNQUALIFIED")
        _require(isinstance(subject, Mapping), "SUBJECT_UNQUALIFIED")
        if subject.get("kind") == "source_topic":
            _require(subject.get("subject") == basis["subject"] and type(subject.get("provenance")) is str and bool(subject["provenance"].strip()), "SUBJECT_UNQUALIFIED")
        elif subject.get("kind") == "historical_security":
            from lib.dataos.identity import parse_id
            _require(parse_id(subject.get("security_id"))[0] == "security" and basis["subject"] == subject["security_id"], "SUBJECT_UNQUALIFIED")
            _require(subject.get("alias_vendor") not in {None, "", "store", "yahoo_fetch"}
                and subject.get("resolution_state") == "RESOLVED"
                and str(subject.get("resolution_date")) == str(leg["item"].get("published_at", ""))[:10]
                and type(subject.get("decision_at")) is str and bool(subject["decision_at"].strip())
                and type(subject.get("provenance")) is str and bool(subject["provenance"].strip()), "HISTORICAL_ALIAS_UNQUALIFIED")
        else:
            raise _Unavailable("SUBJECT_UNQUALIFIED")
    _require(all(type(f) is str and len(f) <= 200 for f in qualified.families), "FAMILY_UNQUALIFIED")
    return qualified


def _compare(owners, ctx, request, legs):
    from engine.research_intelligence.projection import compare_grounded_claims
    qualified = _basis(owners, ctx, request, legs)
    annotation = None
    if "revision_ref" in request:
        _require(callable(owners.revision), "REVISION_UNAVAILABLE")
        rev = owners.revision(ctx, request["revision_ref"], legs)
        _require(type(rev) is QualifiedRevision and _bindings_match(rev.bindings, qualified.bindings)
            and type(rev.provenance) is str and bool(rev.provenance.strip())
            and type(rev.support_quote) is str and 0 < len(rev.support_quote) <= 1600
            and rev.kind in {"CHANGED_VIEW", "CORRECTED_FACTUAL_ERROR"}, "REVISION_UNQUALIFIED")
        from engine.research_vault.catalog import parse_generated_at
        dates = [parse_generated_at(x["item"].get("published_at")) for x in legs]
        _require(dates[0] < dates[1], "REVISION_CHRONOLOGY_UNQUALIFIED")
        annotation = {"kind": rev.kind, "support_quote": rev.support_quote}
    sources = [{"report_id": x["id"], "source_pdf_sha256": x["extracted"]["source_pdf_sha256"],
        "extracted_text_sha256": x["extracted"]["extracted_text_sha256"],
        "text": x["extracted"]["text"], "family_id": family} for x, family in zip(legs, qualified.families)]
    result = compare_grounded_claims(legs[0]["rio"], legs[1]["rio"], left_source=sources[0], right_source=sources[1],
        left_claim_index=request["left"]["claim_index"], right_claim_index=request["right"]["claim_index"],
        left_basis=dict(qualified.bases[0]), right_basis=dict(qualified.bases[1]), revision_annotation=annotation)
    _require(result["comparable"], "BASIS_UNQUALIFIED")
    _require(annotation is None or result["revision_relation"] == annotation["kind"], "REVISION_ANNOTATION_CONFLICT")
    result["basis_provenance"] = qualified.provenance
    if annotation is not None:
        result["revision_provenance"] = rev.provenance
    return result


def view(service, ctx, request, owners):
    """No text is exposed until both legs, final identity and quota qualify."""
    if type(owners) is not ComparisonOwners or not all(callable(getattr(owners, k)) for k in ("semantic", "preflight", "commit")):
        return failure("COMPARISON_OWNERS_UNAVAILABLE")
    try:
        request = copy.deepcopy(_parse(service, request))
        now = service._now()
        catalog, _source = service._read_catalog(now)
        _require(catalog is not None, "CATALOG_UNAVAILABLE")
        items = {x["id"]: x for x in catalog["items"] if isinstance(x, Mapping) and type(x.get("id")) is str}
        ids = (request["left"]["report_id"], request["right"]["report_id"])
        _require(all(rid in items for rid in ids), "REPORT_UNAVAILABLE")
        quota_ids = tuple(dict.fromkeys(ids))
        _require(owners.preflight(ctx, quota_ids, now) is True, "QUOTA_UNAVAILABLE")
        legs = tuple(_load(service, ctx, items, request[k], owners, request["action"]) for k in ("left", "right"))
        result = {"schema": SCHEMA, "state": "INPUTS_ONLY" if request["action"] == "prepare" else "AVAILABLE",
            "authority": "descriptive_research_only", "visibility": "private_entitled_only",
            "left": _public_leg(legs[0]), "right": _public_leg(legs[1]),
            "limitations": list(dict.fromkeys(["PARTIAL_SOURCE_CONTEXT", "RIO_PARTIAL",
                "No report-wide absence or consensus is established"] +
                list(_source.get("known_degradation", ())) + [w for leg in legs for w in leg["warnings"]]))}
        if request["action"] == "prepare":
            result["basis_state"] = "UNRESOLVED"
            for name, leg in zip(("left", "right"), legs):
                result[name]["claims"] = []
                for index in range(min(MAX_PREVIEWS, len(leg["rio"]["claims"]))):
                    candidate = _preview(leg, index)
                    result[name]["claims"].append(candidate)
                    if _strings(result) > MAX_CHARS:
                        result[name]["claims"].pop()
                        break
                result[name]["omitted_claim_count"] = len(leg["rio"]["claims"]) - len(result[name]["claims"])
                _require(bool(result[name]["claims"]), "OUTPUT_BUDGET_UNAVAILABLE")
        else:
            result["comparison"] = _compare(owners, ctx, request, legs)
        _require(_strings(result) <= MAX_CHARS, "OUTPUT_BUDGET_UNAVAILABLE")
        # Re-admit only the selected targets; unrelated catalog changes do not
        # freeze this pair. Snapshot equality binds all admitted target metadata,
        # including institutional/publication provenance used by trusted owners.
        current_catalog, current_source = service._read_catalog(service._now())
        _require(current_catalog is not None, "CATALOG_UNAVAILABLE")
        current_items = {x["id"]: x for x in current_catalog["items"]
                         if isinstance(x, Mapping) and type(x.get("id")) is str}
        for leg in legs:
            current_item = current_items.get(leg["id"])
            _require(current_item is not None and current_item == leg["item"], "CATALOG_TARGET_CHANGED")
            coverage, current, _segments, _extra = service._resolve_text(leg["id"], current_item)
            _require(coverage == "FULL_TEXT" and current is not None
                and _revision_identity(current) == _revision_identity(leg["extracted"]), "SOURCE_CHANGED")
            state, stored, _extra = service._rio_state(leg["id"], current)
            _require(state == "CURRENT" and stored is not None
                and stored.artifact_sha256 == leg["artifact_sha"]
                and stored.receipt == leg["receipt"]
                and owners.semantic(ctx, stored) is True, "RIO_CHANGED")
        # The final semantic owner call is another I/O boundary. Re-admit the
        # selected catalog targets once more after it and before quota commit.
        final_catalog, final_source = service._read_catalog(service._now())
        _require(final_catalog is not None, "CATALOG_UNAVAILABLE")
        final_items = {x["id"]: x for x in final_catalog["items"]
                       if isinstance(x, Mapping) and type(x.get("id")) is str}
        _require(all(final_items.get(leg["id"]) == leg["item"] for leg in legs), "CATALOG_TARGET_CHANGED")
        result["limitations"] = list(dict.fromkeys(result["limitations"] +
            list(current_source.get("known_degradation", ())) +
            list(final_source.get("known_degradation", ()))))
        _require(_strings(result) <= MAX_CHARS, "OUTPUT_BUDGET_UNAVAILABLE")
        _require(owners.commit(ctx, quota_ids, service._now()) is True, "QUOTA_UNAVAILABLE")
        return result
    except _Unavailable as exc:
        return failure(str(exc))
    except Exception:
        return failure("COMPARISON_UNAVAILABLE")
