"""Shadow CTEv2 consumer/compiler over the existing qualified owner interfaces.

No writer, output path, ambient clock, network, rights decision or state resolver.
Receipt integrity is not source authentication. Current canonical basket membership
retains its incumbent current-valid-date/non-PIT meaning; local mappings remain
the state owner's facts. Production adoption and delivery remain separate gates.
"""
from __future__ import annotations

import copy
from datetime import date
import re
from typing import Any, Mapping

import jsonschema

from engine.company_intelligence.contracts import (
    validate_context, validate_manifest as validate_company_manifest,
)
from engine.company_theme_exposure.contracts import (
    ContractError, canonical_json_bytes, canonical_json_sha256, company_filename,
    safe_ticker, validate_exposure as validate_exposure_v1,
)
from engine.company_theme_exposure.views import build_bundle as build_legacy_bundle
from engine.company_theme_exposure.views import derive_generation_id
from engine.theme_graph import theme_state as state_owner
from engine.theme_graph.identity import local_theme_node_id, theme_node_id

EXPOSURE_SCHEMA = "company_theme_exposure.v2"
MANIFEST_SCHEMA = "company_theme_exposure_manifest.v2"
BUILDER = "company_theme_exposure.v2.shadow"
CANONICAL_QUALIFICATION = "CURRENT_VALID_DATE_NOT_PIT"
CAPS = dict(state_owner.AUTHORITY)
_SHA = re.compile(r"^[0-9a-f]{64}$")
_GEN = re.compile(r"^[0-9a-f]{24}$")
_STATE_GEN = re.compile(r"^[0-9a-f]{32}$")

_EXPOSURE_KEYS = {
    "schema", "authority", "mode", "authority_caps", "generated_at", "generation_id",
    "status", "company", "company_intelligence", "exposures", "coverage",
    "canonical_membership_qualification", "company_identity", "local_membership",
    "local_memberships", "local_coverage", "theme_state", "warnings",
}
_BINDING_KEYS = {
    "schema", "status", "expected_generation_id", "generation_id", "state_sha256",
    "state_generated_at", "canonical_json_sha256", "raw_bytes_sha256", "raw_bytes_status",
    "graph_generation_id", "owner_generations", "effective_at", "known_at", "reads",
}
_LOCAL_KEYS = {
    "company_node_id", "node_id", "source_family", "native_id",
    "membership_basis", "source_refs", "membership_receipt_sha256",
}
_LOCAL_OWNER_KEYS = {"node_id", "source_family", "native_id", "membership_basis", "source_refs"}
_COVERAGE_KEYS = {"status", "declared_count", "observed_count", "state_available_count", "reason_codes"}
_MANIFEST_KEYS = {
    "schema", "mode", "authority_caps", "generation_id", "generated_at",
    "company_count", "exposure_count", "local_membership_count", "coverage",
    "local_coverage", "source", "files", "status", "warnings",
}
_SOURCE_KEYS = {
    "company_intelligence", "membership", "crosswalk", "theme_state",
    "company_identity_reads", "local_membership_reads", "builder",
}


def _closed(value: object, keys: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ContractError(f"{name} closed fields mismatch")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ContractError(f"{name} must be nonempty text")
    return value


def _hash(value: object, name: str) -> None:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ContractError(f"{name} digest invalid")


def _count(value: object, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ContractError(f"{name} count invalid")


def _strings(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise ContractError(f"{name} strings invalid")
    if value != sorted(set(value)):
        raise ContractError(f"{name} must be sorted and unique")
    return value


def _clock(value: object, name: str, *, precise: bool = False) -> None:
    try:
        _, day = state_owner._clock(value)
        if precise and day:
            raise ValueError("precise clock required")
    except (ValueError, TypeError) as exc:
        raise ContractError(f"{name} clock invalid") from exc


def _caps(value: object) -> None:
    if (not isinstance(value, Mapping) or set(value) != set(CAPS)
            or any(type(flag) is not bool for flag in value.values()) or value != CAPS):
        raise ContractError("all owner context/false authority flags must be retained")


def _owner_read(value: object, role: str, binding: Mapping[str, Any],
                *, subject_id: str | None = None) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or value.get("owner") != role:
        raise ContractError(f"{role} owner receipt invalid")
    try:
        # Reuse the incumbent validator and honest date-precision policy rather
        # than another receipt/knowledge-time algorithm.
        state_owner._validate_receipt(
            value, subject_id=subject_id,
            graph_generation_id=binding["graph_generation_id"],
            owner_generations=binding["owner_generations"],
            query={k: binding[k] for k in ("effective_at", "known_at")},
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise ContractError(f"{role} receipt binding invalid") from exc
    return value


def _owner_reasons(read: Mapping[str, Any], binding: Mapping[str, Any]) -> list[str]:
    return state_owner._clock_reasons(read, binding["effective_at"], binding["known_at"])


def _check_state_read(read: object, binding: Mapping[str, Any]) -> None:
    schema = {"$ref": "#/$defs/read_receipt", "$defs": state_owner._validator().schema["$defs"]}
    try:
        jsonschema.Draft202012Validator(schema).validate(read)
    except jsonschema.ValidationError as exc:
        raise ContractError("owner read contract invalid") from exc
    for key in ("generation_id", "state_sha256", "state_generated_at", "effective_at", "known_at"):
        if read[key] != binding[key]:
            raise ContractError(f"state read {key} binding mismatch")
    if read["status"] != "UNAVAILABLE":
        if not state_owner._proven_by(read["state_generated_at"], read["known_at"]):
            raise ContractError("available state was not yet emitted")
        known, _ = state_owner._clock(read["known_at"])
        emitted, _ = state_owner._clock(read["state_generated_at"])
        if (known - emitted).total_seconds() > state_owner.STATE_MAX_AGE_HOURS * 3600:
            raise ContractError("available state exceeds owner freshness")
        if read["subject"]["node_id"] != read["subject_id"]:
            raise ContractError("state subject mismatch")
    # JSON schema owns the status/eligibility/availability invariant. This check
    # validates an interface, and does not authenticate arbitrary dictionaries.


def _binding(value: object, *, state_artifact: object = None) -> Mapping[str, Any]:
    item = _closed(value, _BINDING_KEYS, "theme_state")
    if item["schema"] != state_owner.SCHEMA or item["raw_bytes_status"] != "UNMATERIALIZED" or item["raw_bytes_sha256"] is not None:
        raise ContractError("shadow state binding cannot claim raw object bytes")
    if not isinstance(item["expected_generation_id"], str) or not _STATE_GEN.fullmatch(item["expected_generation_id"]):
        raise ContractError("expected state generation invalid")
    _clock(item["effective_at"], "state effective")
    _clock(item["known_at"], "state known", precise=True)
    if item["status"] == "MISSING":
        if any(item[k] is not None for k in ("generation_id", "state_sha256", "state_generated_at",
                   "canonical_json_sha256", "graph_generation_id", "owner_generations")) or item["reads"] != []:
            raise ContractError("missing state must retain named absent source facts")
    elif item["status"] == "AVAILABLE":
        _hash(item["state_sha256"], "owner state")
        _hash(item["canonical_json_sha256"], "CTE canonical state JSON")
        if item["generation_id"] != item["expected_generation_id"] or item["generation_id"] != item["state_sha256"][:32]:
            raise ContractError("state generation/digest mismatch")
        _clock(item["state_generated_at"], "state emission", precise=True)
        _text(item["graph_generation_id"], "state graph generation")
        if not isinstance(item["owner_generations"], Mapping):
            raise ContractError("state owner generations invalid")
        if not isinstance(item["reads"], list):
            raise ContractError("state reads invalid")
        ids = []
        for read in item["reads"]:
            _check_state_read(read, item)
            ids.append(read["subject_id"])
        if ids != sorted(set(ids)):
            raise ContractError("state reads duplicated or unordered")
    else:
        raise ContractError("state artifact availability invalid")
    if state_artifact is not None:
        try:
            state_owner.validate_state(state_artifact)
        except (ValueError, TypeError) as exc:
            raise ContractError("state artifact invalid") from exc
        if item["status"] != "AVAILABLE":
            raise ContractError("state artifact supplied for missing binding")
        expected = {
            "generation_id": state_artifact["generation_id"],
            "state_sha256": state_artifact["state_sha256"],
            "state_generated_at": state_artifact["generated_at"],
            "canonical_json_sha256": canonical_json_sha256(state_artifact),
            "graph_generation_id": state_artifact["graph_generation_id"],
            "owner_generations": state_artifact["owner_generations"],
        }
        if any(item[k] != v for k, v in expected.items()):
            raise ContractError("state source/digest scope mismatch")
        for read in item["reads"]:
            actual = state_owner.read_theme_state(
                state_artifact, read["subject_id"], effective_at=item["effective_at"],
                known_at=item["known_at"], expected_generation_id=item["expected_generation_id"])
            if actual != read:
                raise ContractError("state receipt disagrees with actual owner reader")
    return item


def _new_binding(state: object, *, effective_at: str, known_at: str,
                 expected_generation_id: str) -> dict:
    result = {
        "schema": state_owner.SCHEMA, "status": "MISSING",
        "expected_generation_id": expected_generation_id, "generation_id": None,
        "state_sha256": None, "state_generated_at": None, "canonical_json_sha256": None,
        "raw_bytes_sha256": None, "raw_bytes_status": "UNMATERIALIZED",
        "graph_generation_id": None, "owner_generations": None,
        "effective_at": effective_at, "known_at": known_at, "reads": [],
    }
    if state is not None:
        try:
            state_owner.validate_state(state)
        except (ValueError, TypeError) as exc:
            raise ContractError("state artifact invalid") from exc
        result.update(status="AVAILABLE", generation_id=state["generation_id"],
            state_sha256=state["state_sha256"], state_generated_at=state["generated_at"],
            canonical_json_sha256=canonical_json_sha256(state),
            graph_generation_id=state["graph_generation_id"],
            owner_generations=copy.deepcopy(state["owner_generations"]))
    _binding(result, state_artifact=state)
    return result


def _local_projection(ticker: str, identity: object, membership: object,
                      binding: Mapping[str, Any]) -> tuple[list[dict], dict]:
    reasons = []
    company_id = None
    if identity is None:
        reasons.append("COMPANY_IDENTITY_MISSING")
    else:
        identity = _owner_read(identity, "identity", binding)
        reasons.extend(_owner_reasons(identity, binding))
        if identity["availability"] == "UNAVAILABLE":
            reasons.append("COMPANY_IDENTITY_UNAVAILABLE")
        else:
            if identity["availability"] != "AVAILABLE":
                raise ContractError("resolved company identity requires AVAILABLE owner admission")
            payload = _closed(identity["payload"], {
                "status", "ticker", "company_node_id", "issuer_id", "security_id"}, "identity payload")
            if payload["status"] != "RESOLVED" or payload["ticker"] != ticker:
                raise ContractError("company identity does not bind ticker")
            company_id = _text(payload["company_node_id"], "company node")
            if identity["subject_id"] != company_id:
                raise ContractError("identity owner subject mismatch")
            for key in ("issuer_id", "security_id"):
                _text(payload[key], key)
    rows = []
    declared = None
    admission = None
    if membership is None:
        reasons.append("LOCAL_MEMBERSHIP_MISSING")
    else:
        membership = _owner_read(membership, "membership", binding, subject_id=company_id)
        reasons.extend(_owner_reasons(membership, binding))
        if membership["availability"] == "UNAVAILABLE":
            reasons.append("LOCAL_MEMBERSHIP_UNAVAILABLE")
        else:
            payload = _closed(membership["payload"], {"company_node_id", "declared_count", "memberships"}, "local owner payload")
            if company_id is not None and payload["company_node_id"] != company_id:
                raise ContractError("local membership company mismatch")
            if payload["company_node_id"] != membership["subject_id"]:
                raise ContractError("local membership owner subject mismatch")
            if identity is not None and identity["graph_generation_id"] != membership["graph_generation_id"]:
                raise ContractError("identity/local membership graph generation mismatch")
            _count(payload["declared_count"], "local declared")
            declared = payload["declared_count"]
            if not isinstance(payload["memberships"], list) or len(payload["memberships"]) != declared:
                raise ContractError("local declared membership coverage mismatch")
            if (membership["availability"] == "VALID_EMPTY") != (declared == 0):
                raise ContractError("empty local membership requires explicit VALID_EMPTY")
            admission = membership["availability"]
            for raw in payload["memberships"]:
                raw = _closed(raw, _LOCAL_OWNER_KEYS, "local member")
                try:
                    expected_node = local_theme_node_id(raw["source_family"], raw["native_id"])
                except ValueError as exc:
                    raise ContractError("local native identity invalid") from exc
                if expected_node != raw["node_id"]:
                    raise ContractError("local native identity mismatch")
                _text(raw["membership_basis"], "local basis")
                _strings(raw["source_refs"], "local source refs")
                if not raw["source_refs"]:
                    raise ContractError("local membership source refs required")
                rows.append({**copy.deepcopy(raw), "company_node_id": payload["company_node_id"],
                             "membership_receipt_sha256": membership["sha256"]})
            ids = [r["node_id"] for r in rows]
            if len(ids) != len(set(ids)):
                raise ContractError("duplicate local membership")
    if reasons:
        return [], {"status": "UNAVAILABLE", "declared_count": None, "observed_count": None,
                    "state_available_count": None, "reason_codes": sorted(set(reasons))}
    return sorted(rows, key=lambda r: r["node_id"]), {
        "status": admission, "declared_count": declared, "observed_count": declared,
        "state_available_count": 0, "reason_codes": [],
    }



def _check_forward_membership(ticker: str, rows: list[dict], identity: Mapping[str, Any] | None,
                              inverse: Mapping[str, Any] | None, binding: Mapping[str, Any],
                              *, state_artifact: Mapping[str, Any] | None = None) -> None:
    """Bind inverse context to the actual owner's forward roster, never labels alone.

    Without the source artifact, usable read subjects provide the closed forward
    receipt for structural consistency. Source equality is still proved only by
    the artifact-backed reader comparison in _binding. Unavailable reads carry
    no subject and cannot attach a graph-backed company context.
    """
    if not rows or binding["status"] == "MISSING":
        return
    usable = {r["subject_id"]: r["subject"] for r in binding["reads"]
              if r["status"] != "UNAVAILABLE"}
    subjects = ({s["node_id"]: s for s in state_artifact["subjects"]}
                if state_artifact is not None else usable)
    company = identity["payload"]
    expected = (ticker, company["issuer_id"], company["security_id"])
    for row in rows:
        subject = subjects.get(row["node_id"])
        if subject is None:
            if row["node_id"] in usable:
                raise ContractError("forward membership subject missing")
            continue
        forward = subject["owner_receipts"]["membership"]
        # Unavailable/unproved source facts cannot establish or contradict a
        # member. The existing actual reader emits an unavailable/null subject.
        if forward is None or forward["availability"] == "UNAVAILABLE":
            if row["node_id"] in usable:
                raise ContractError("forward membership unavailable for usable state")
            continue
        try:
            state_owner._validate_receipt(
                forward, subject_id=row["node_id"],
                graph_generation_id=binding["graph_generation_id"],
                owner_generations=binding["owner_generations"])
        except (ValueError, TypeError, KeyError) as exc:
            raise ContractError("forward membership owner binding invalid") from exc
        scope_proved = (forward["query"]["effective_at"] == binding["effective_at"] and
                        state_owner._proven_by(forward["query"]["known_at"], binding["known_at"]))
        if not scope_proved or _owner_reasons(forward, binding):
            if row["node_id"] in usable:
                raise ContractError("forward membership scope/clocks unproved for usable state")
            continue
        if any(state_owner._clock(forward[key]) != state_owner._clock(inverse[key])
               for key in ("effective_at", "available_at", "known_at", "recorded_at")):
            raise ContractError("inverse/forward membership source clocks mismatch")
        payload = forward["payload"]
        members = payload.get("members") if isinstance(payload, Mapping) else None
        if not isinstance(members, list):
            if row["node_id"] in usable:
                raise ContractError("forward membership roster invalid for usable state")
            continue
        matches = [member for member in members if isinstance(member, Mapping) and
                   tuple(member.get(key) for key in ("ticker", "issuer_id", "security_id")) == expected]
        if len(matches) != 1:
            raise ContractError("forward owner membership does not uniquely bind company identity")


def _warnings(item: Mapping[str, Any]) -> list[str]:
    warnings = []
    if item["coverage"]["unmapped_basket_count"]:
        warnings.append("active_membership_unmapped")
    if item["local_coverage"]["status"] == "UNAVAILABLE":
        warnings.append("local_membership_unavailable")
    if item["theme_state"]["status"] == "MISSING":
        warnings.append("theme_state_missing")
    elif any(r["status"] == "UNAVAILABLE" for r in item["theme_state"]["reads"]):
        warnings.append("theme_state_unavailable")
    return sorted(warnings)


def validate_exposure_v2(payload: object, *, state_artifact: object = None,
                         company_context: object = None) -> None:
    """Closed shadow wire and owner-interface checks.

    Actual source equality needs its supplied owner artifact/context. Without
    those, this validates serialization/cross-field invariants, not authenticity.
    """
    canonical_json_bytes(payload)  # bounded finite canonical JSON, no NaN/Inf
    item = _closed(payload, _EXPOSURE_KEYS, "exposure v2")
    if item["schema"] != EXPOSURE_SCHEMA or item["authority"] != "context_only" or item["mode"] != "shadow":
        raise ContractError("CTEv2 remains context-only shadow")
    _caps(item["authority_caps"])
    if not isinstance(item["generation_id"], str) or not _GEN.fullmatch(item["generation_id"]):
        raise ContractError("CTE generation invalid")
    _clock(item["generated_at"], "CTE generated", precise=True)
    if item["canonical_membership_qualification"] != CANONICAL_QUALIFICATION:
        raise ContractError("canonical membership must retain current-valid/non-PIT qualification")
    # Reuse the exact existing canonical item/count/parent-event closed contract.
    old = {k: copy.deepcopy(item[k]) for k in (
        "authority", "generated_at", "generation_id", "company", "company_intelligence",
        "exposures", "coverage")}
    old.update(schema="company_theme_exposure.v1",
        theme_state={"status": "missing", "as_of": None, "sha256": None},
        warnings=sorted(["theme_state_missing"] + (
            ["active_membership_unmapped"] if item["coverage"].get("unmapped_basket_count") else [])),
        status="partial")
    validate_exposure_v1(old)
    ticker = safe_ticker(item["company"]["ticker"])
    binding = _binding(item["theme_state"], state_artifact=state_artifact)
    if item["generated_at"] != binding["known_at"]:
        raise ContractError("state query must bind pinned CI generation clock")
    rows, projected = _local_projection(ticker, item["company_identity"], item["local_membership"], binding)
    if rows != item["local_memberships"]:
        raise ContractError("local projection disagrees with owner receipts")
    coverage = _closed(item["local_coverage"], _COVERAGE_KEYS, "local coverage")
    for field in ("declared_count", "observed_count", "state_available_count"):
        if projected["status"] == "UNAVAILABLE":
            if coverage[field] is not None:
                raise ContractError("unavailable local count must retain null")
        else:
            _count(coverage[field], "local " + field)
    _check_forward_membership(ticker, rows, item["company_identity"], item["local_membership"],
                              binding, state_artifact=state_artifact)
    related = {theme_node_id(r["theme_id"]) for r in item["exposures"]} | {r["node_id"] for r in rows}
    reads = binding["reads"]
    if binding["status"] == "AVAILABLE" and {r["subject_id"] for r in reads} != related:
        raise ContractError("state reads must exactly cover selected canonical/local subjects")
    usable = {r["subject_id"]: r for r in reads if r["status"] != "UNAVAILABLE"}
    for row in rows:
        read = usable.get(row["node_id"])
        if read is not None:
            subject = read["subject"]
            if (subject["kind"], subject["source_family"], subject["native_id"]) != (
                    "local_theme", row["source_family"], row["native_id"]):
                raise ContractError("state/local native identity mismatch")
    if projected["status"] != "UNAVAILABLE":
        projected["state_available_count"] = sum(r["node_id"] in usable for r in rows)
        if any(r["node_id"] not in usable for r in rows):
            projected["reason_codes"] = ["STATE_CONTEXT_UNAVAILABLE"]
    if coverage != projected:
        raise ContractError("local coverage disagrees with admitted membership/state")
    warnings = _warnings(item)
    if item["warnings"] != warnings or item["status"] != ("partial" if warnings else "ready"):
        raise ContractError("CTEv2 status/warnings mismatch")
    if company_context is not None:
        validate_context(company_context)
        latest = company_context["latest_event"]
        expected = {
            "generation_id": company_context["generation_id"],
            "context_sha256": canonical_json_sha256(company_context),
            "latest_event_id": latest["event_id"] if latest else None,
            "latest_event_call_date": latest["call_date"] if latest else None,
        }
        if item["company_intelligence"] != expected or company_context["company"]["ticker"] != ticker:
            raise ContractError("CTE parent/latest-event pin mismatch")


def _manifest_warnings(exposures: Mapping[str, Mapping[str, Any]]) -> list[str]:
    warnings = set().union(*(set(v["warnings"]) for v in exposures.values())) if exposures else set()
    if "active_membership_unmapped" in warnings:
        warnings.remove("active_membership_unmapped")
        warnings.add("active_memberships_unmapped")
    return sorted(warnings)


def validate_manifest_v2(payload: object, *, allow_unmaterialized_files: bool = False,
                         exposures: Mapping[str, Mapping[str, Any]] | None = None,
                         state_artifact: object = None) -> None:
    """Validate shadow metadata; supplied exposures prove the generation preimage."""
    canonical_json_bytes(payload)
    item = _closed(payload, _MANIFEST_KEYS, "manifest v2")
    if item["schema"] != MANIFEST_SCHEMA or item["mode"] != "shadow":
        raise ContractError("CTEv2 manifest must remain shadow")
    _caps(item["authority_caps"])
    _clock(item["generated_at"], "manifest generated", precise=True)
    if not isinstance(item["generation_id"], str) or not _GEN.fullmatch(item["generation_id"]):
        raise ContractError("manifest generation invalid")
    for key in ("company_count", "exposure_count", "local_membership_count"):
        _count(item[key], key)
    if item["files"] != {} or (item["company_count"] and not allow_unmaterialized_files):
        raise ContractError("shadow files are unmaterialized; publication is not authorized")
    source = _closed(item["source"], _SOURCE_KEYS, "manifest source")
    pin = _closed(source["company_intelligence"], {"generation_id", "sha256"}, "CI source")
    if not isinstance(pin["generation_id"], str) or not _GEN.fullmatch(pin["generation_id"]):
        raise ContractError("CI source generation invalid")
    _hash(pin["sha256"], "CI source")
    for key in ("membership", "crosswalk", "company_identity_reads", "local_membership_reads"):
        _closed(source[key], {"canonical_json_sha256"}, key)
        _hash(source[key]["canonical_json_sha256"], key)
    if source["builder"] != BUILDER:
        raise ContractError("shadow builder version invalid")
    binding = _binding(source["theme_state"], state_artifact=state_artifact)
    if binding["known_at"] != item["generated_at"]:
        raise ContractError("manifest state/parent clock mismatch")
    _closed(item["local_coverage"], {"available_company_count", "valid_empty_company_count",
                                    "unavailable_company_count"}, "manifest local coverage")
    for value in item["local_coverage"].values():
        _count(value, "manifest local coverage")
    if sum(item["local_coverage"].values()) != item["company_count"]:
        raise ContractError("manifest local company coverage mismatch")
    # The incumbent global canonical coverage is retained; no local denominators
    # are folded into it. Reuse its exact nonnegative shape and identities.
    expected_coverage = {
        "active_membership_count", "mapped_membership_count", "unmapped_membership_count",
        "active_member_ticker_count", "unmapped_only_ticker_count",
        "active_member_tickers_without_company_context",
    }
    canonical = _closed(item["coverage"], expected_coverage, "canonical global coverage")
    for value in canonical.values():
        _count(value, "canonical global coverage")
    if canonical["active_membership_count"] != canonical["mapped_membership_count"] + canonical["unmapped_membership_count"]:
        raise ContractError("canonical global coverage arithmetic mismatch")
    if (canonical["unmapped_only_ticker_count"] > canonical["active_member_ticker_count"] or
            canonical["active_member_tickers_without_company_context"] > canonical["active_member_ticker_count"]):
        raise ContractError("canonical global ticker coverage invalid")
    if not item["company_count"] and (item["exposure_count"] or item["local_membership_count"]):
        raise ContractError("empty manifest must have zero company projections")
    _strings(item["warnings"], "manifest warnings")
    expected_warnings = []
    if canonical["unmapped_membership_count"]:
        expected_warnings.append("active_memberships_unmapped")
    if item["local_coverage"]["unavailable_company_count"]:
        expected_warnings.append("local_membership_unavailable")
    if binding["status"] == "MISSING":
        expected_warnings.append("theme_state_missing")
    elif any(read["status"] == "UNAVAILABLE" for read in binding["reads"]):
        expected_warnings.append("theme_state_unavailable")
    if item["warnings"] != sorted(expected_warnings):
        raise ContractError("manifest owner coverage/freshness warnings mismatch")
    if item["status"] != ("empty" if not item["company_count"] else ("partial" if item["warnings"] else "ready")):
        raise ContractError("manifest status mismatch")
    if exposures is not None:
        if set(exposures) != {e["company"]["ticker"] for e in exposures.values()}:
            raise ContractError("manifest company keys mismatch")
        union = {}
        expected_local = {"available_company_count": 0, "valid_empty_company_count": 0, "unavailable_company_count": 0}
        for e in exposures.values():
            validate_exposure_v2(e, state_artifact=state_artifact)
            if e["generation_id"] != item["generation_id"] or e["company_intelligence"]["generation_id"] != pin["generation_id"]:
                raise ContractError("manifest/company parent generation mismatch")
            for read in e["theme_state"]["reads"]:
                if read["subject_id"] in union and union[read["subject_id"]] != read:
                    raise ContractError("contradictory shared state read")
                union[read["subject_id"]] = read
            status = e["local_coverage"]["status"]
            expected_local[{"AVAILABLE": "available_company_count", "VALID_EMPTY": "valid_empty_company_count",
                            "UNAVAILABLE": "unavailable_company_count"}[status]] += 1
        expected = {
            "company_count": len(exposures),
            "exposure_count": sum(len(e["exposures"]) for e in exposures.values()),
            "local_membership_count": sum(len(e["local_memberships"]) for e in exposures.values()),
            "local_coverage": expected_local,
        }
        if any(item[k] != value for k, value in expected.items()):
            raise ContractError("manifest aggregate coverage mismatch")
        if binding["reads"] != [union[k] for k in sorted(union)]:
            raise ContractError("manifest state reads mismatch")
        for e in exposures.values():
            if {k: v for k, v in e["theme_state"].items() if k != "reads"} != {k: v for k, v in binding.items() if k != "reads"}:
                raise ContractError("manifest/company state generation mismatch")
        if derive_generation_id(exposures, item) != item["generation_id"]:
            raise ContractError("CTEv2 semantic generation mismatch")


def compose_shadow_bundle(
    contexts: Mapping[str, Mapping[str, Any]], *,
    company_manifest: Mapping[str, Any], membership: Mapping[str, Any], crosswalk: Mapping[str, Any],
    state_artifact: Mapping[str, Any] | None, effective_at: str, known_at: str,
    expected_state_generation_id: str, company_identity_reads: Mapping[str, Any],
    local_membership_reads: Mapping[str, Any],
) -> tuple[dict, dict]:
    """Compose one deterministic in-memory sidecar; selection and rights stay owned."""
    validate_company_manifest(company_manifest)
    if known_at != company_manifest["generated_at"]:
        raise ContractError("knowledge query must equal pinned CI generated_at")
    _clock(known_at, "knowledge query", precise=True)
    _clock(effective_at, "effective query")
    if state_owner._definitely_after(effective_at, known_at):
        raise ContractError("effective query is definitely after CI knowledge cutoff")
    if not isinstance(company_identity_reads, Mapping) or not isinstance(local_membership_reads, Mapping):
        raise ContractError("injected owner reads must be mappings")
    if (set(company_identity_reads) | set(local_membership_reads)) - set(contexts):
        raise ContractError("foreign company owner receipt")
    if set(company_manifest["files"]) != {company_filename(t) for t in contexts}:
        raise ContractError("parent tree does not exactly cover contexts")
    for ticker, context in contexts.items():
        validate_context(context)
        if context["generation_id"] != company_manifest["generation_id"] or context["company"]["ticker"] != ticker:
            raise ContractError("context/parent company generation mismatch")
        source = company_manifest["files"][company_filename(ticker)]
        canonical = canonical_json_bytes(context)
        if source["sha256"] != canonical_json_sha256(context) or source["bytes"] != len(canonical):
            raise ContractError("parent canonical writer bytes/context mismatch")
    binding = _new_binding(state_artifact, effective_at=effective_at, known_at=known_at,
                           expected_generation_id=expected_state_generation_id)
    # This owner computes ONLY the incumbent current-valid-date canonical basket
    # projection. Its temporary legacy missing-state envelope is not published.
    legacy, old_manifest = build_legacy_bundle(
        contexts, company_manifest=company_manifest, membership=membership,
        crosswalk=crosswalk, theme_state=None, as_of=date.fromisoformat(effective_at[:10]))
    exposures = {}
    all_reads = {}
    for ticker, old in sorted(legacy.items()):
        identity = copy.deepcopy(company_identity_reads.get(ticker))
        local_read = copy.deepcopy(local_membership_reads.get(ticker))
        rows, coverage = _local_projection(ticker, identity, local_read, binding)
        related = {theme_node_id(e["theme_id"]) for e in old["exposures"]} | {r["node_id"] for r in rows}
        company_binding = copy.deepcopy(binding)
        if state_artifact is not None:
            for node in sorted(related):
                all_reads[node] = state_owner.read_theme_state(
                    state_artifact, node, effective_at=effective_at, known_at=known_at,
                    expected_generation_id=expected_state_generation_id)
            company_binding["reads"] = [copy.deepcopy(all_reads[node]) for node in sorted(related)]
        usable = {r["subject_id"] for r in company_binding["reads"] if r["status"] != "UNAVAILABLE"}
        if coverage["status"] != "UNAVAILABLE":
            coverage["state_available_count"] = sum(r["node_id"] in usable for r in rows)
            if any(r["node_id"] not in usable for r in rows):
                coverage["reason_codes"] = ["STATE_CONTEXT_UNAVAILABLE"]
        item = {k: copy.deepcopy(old[k]) for k in (
            "authority", "generated_at", "company", "company_intelligence", "exposures", "coverage")}
        item.update(schema=EXPOSURE_SCHEMA, mode="shadow", authority_caps=dict(CAPS),
            generation_id="0" * 24, canonical_membership_qualification=CANONICAL_QUALIFICATION,
            company_identity=identity, local_membership=local_read, local_memberships=rows,
            local_coverage=coverage, theme_state=company_binding)
        item["warnings"] = _warnings(item)
        item["status"] = "partial" if item["warnings"] else "ready"
        exposures[ticker] = item
    manifest_binding = copy.deepcopy(binding)
    manifest_binding["reads"] = [copy.deepcopy(all_reads[k]) for k in sorted(all_reads)]
    local_counts = {key: 0 for key in ("available_company_count", "valid_empty_company_count", "unavailable_company_count")}
    for item in exposures.values():
        local_counts[{"AVAILABLE": "available_company_count", "VALID_EMPTY": "valid_empty_company_count",
                      "UNAVAILABLE": "unavailable_company_count"}[item["local_coverage"]["status"]]] += 1
    warnings = set(_manifest_warnings(exposures))
    if old_manifest["coverage"]["unmapped_membership_count"]:
        warnings.add("active_memberships_unmapped")
    if binding["status"] == "MISSING":
        warnings.add("theme_state_missing")
    warnings = sorted(warnings)
    manifest = {
        "schema": MANIFEST_SCHEMA, "mode": "shadow", "authority_caps": dict(CAPS),
        "generation_id": "0" * 24, "generated_at": company_manifest["generated_at"],
        "company_count": len(exposures), "exposure_count": sum(len(e["exposures"]) for e in exposures.values()),
        "local_membership_count": sum(len(e["local_memberships"]) for e in exposures.values()),
        "coverage": copy.deepcopy(old_manifest["coverage"]), "local_coverage": local_counts,
        "source": {
            "company_intelligence": {"generation_id": company_manifest["generation_id"],
                                     "sha256": canonical_json_sha256(company_manifest)},
            "membership": {"canonical_json_sha256": canonical_json_sha256(membership)},
            "crosswalk": {"canonical_json_sha256": canonical_json_sha256(crosswalk)},
            "theme_state": manifest_binding,
            "company_identity_reads": {"canonical_json_sha256": canonical_json_sha256(company_identity_reads)},
            "local_membership_reads": {"canonical_json_sha256": canonical_json_sha256(local_membership_reads)},
            "builder": BUILDER,
        },
        "files": {}, "status": "empty" if not exposures else ("partial" if warnings else "ready"),
        "warnings": warnings,
    }
    generation = derive_generation_id(exposures, manifest)
    manifest["generation_id"] = generation
    for ticker, item in exposures.items():
        item["generation_id"] = generation
        validate_exposure_v2(item, state_artifact=state_artifact, company_context=contexts[ticker])
    validate_manifest_v2(manifest, allow_unmaterialized_files=True,
                         exposures=exposures, state_artifact=state_artifact)
    return exposures, manifest
