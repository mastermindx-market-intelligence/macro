"""Pure What Matters Next composition over already-admitted owner projections.

The first executable slice intentionally composes issuer-disclosure Company
Intelligence events with CURRENT Data OS issuer/security identity.  It does not
allocate event/issuer/security/asset/relationship identities and does not invent
probability, materiality, historical-response or incorporation estimates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from engine.biocatalyst.company_event_adapter import project_company_event_input
from engine.biocatalyst.research_priority import (
    METHOD_ID,
    classify_research_priority,
    interval_overlaps_horizon,
    sort_research_priority_rows,
)
from engine.company_intelligence.contracts import (
    CATALYST_SOURCE_FACT_AUTHORITY,
    ContractError,
    canonical_json_sha256,
    validate_company_catalyst_event,
)

_ROW_KEYS = {
    "row_key", "event_fact_ref", "event_family", "event_revision_ref",
    "revision_is_current", "occurrence", "timing", "issuer", "assets",
    "relationships", "economic_exposure_state", "evidence", "revision_summary",
    "research_priority", "probability", "materiality", "historical_response",
    "incorporation", "missingness", "links",
}
_IDENTITY_KEYS = {
    "state", "company_id", "issuer_cik", "identity_scope",
    "identity_observed_at", "identity_cut_date", "issuers",
}


def _utc(value: object, *, field: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or "T" not in value:
        raise ContractError(f"{field} requires an explicit timezone")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{field} requires an explicit timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{field} requires an explicit timezone")
    utc = parsed.astimezone(timezone.utc)
    return utc.isoformat(timespec="seconds").replace("+00:00", "Z"), utc


def _estimate_slot(kind: str) -> dict[str, Any]:
    return {
        "state": "NOT_ESTIMABLE",
        "value": None,
        "reason_code": f"{kind.upper()}_OWNER_NOT_ADMITTED",
        "method_ref": None,
        "as_of": None,
        "evidence_refs": [],
    }


def _validate_identity_projection(
    identity: object,
    *,
    company_id: str,
    issuer_cik: str,
    evaluation_cutoff: object,
) -> dict[str, Any]:
    if not isinstance(identity, Mapping) or set(identity) != _IDENTITY_KEYS:
        raise ContractError("identity_projection shape invalid")
    state = identity.get("state")
    if state not in {"resolved", "unresolved", "ambiguous"}:
        raise ContractError("identity_projection state invalid")
    if identity.get("company_id") != company_id or identity.get("issuer_cik") != issuer_cik:
        raise ContractError("identity_projection does not bind the selected company event")
    if identity.get("identity_scope") != "current_only":
        raise ContractError("identity_projection must be current_only")
    observed_literal, observed = _utc(
        identity.get("identity_observed_at"), field="identity_observed_at"
    )
    _cutoff_literal, cutoff = _utc(evaluation_cutoff, field="evaluation_cutoff")
    if observed > cutoff:
        raise ContractError("identity_observed_at exceeds evaluation cutoff")
    cut_date = identity.get("identity_cut_date")
    if not isinstance(cut_date, str) or len(cut_date) != 10:
        raise ContractError("identity_cut_date invalid")
    issuers = identity.get("issuers")
    if not isinstance(issuers, list):
        raise ContractError("identity_projection issuers must be a list")
    if state == "resolved" and len(issuers) != 1:
        raise ContractError("resolved identity requires exactly one issuer")
    if state == "unresolved" and issuers:
        raise ContractError("unresolved identity must not carry issuer candidates")
    if state == "ambiguous" and len(issuers) < 2:
        raise ContractError("ambiguous identity requires multiple candidates")
    return {**dict(identity), "identity_observed_at": observed_literal}


def _admitted_issuer(identity: Mapping[str, Any], *, company_id: str) -> dict[str, Any]:
    state = identity["state"]
    if state != "resolved":
        return {
            "state": state,
            "issuer_id": None,
            "company_id": company_id,
            "relationship_role": None,
            "identity_scope": "unavailable",
            "identity_observed_at": identity["identity_observed_at"],
            "securities": [],
        }
    raw = identity["issuers"][0]
    if not isinstance(raw, Mapping) or set(raw) != {"issuer_id", "securities"}:
        raise ContractError("resolved issuer projection shape invalid")
    issuer_id = raw.get("issuer_id")
    securities = raw.get("securities")
    if not isinstance(issuer_id, str) or not issuer_id.startswith("ISS:"):
        raise ContractError("resolved issuer_id invalid")
    if not isinstance(securities, list) or not securities:
        raise ContractError("resolved issuer must retain at least one active security")
    rendered: list[dict[str, Any]] = []
    for security in securities:
        if not isinstance(security, Mapping) or set(security) != {
            "security_id", "listing_key", "display_symbol", "symbol_observed_on", "state"
        }:
            raise ContractError("security projection shape invalid")
        if security.get("state") != "active":
            raise ContractError("current WMN row cannot navigate a non-active security")
        rendered.append(dict(security))
    return {
        "state": "resolved",
        "issuer_id": issuer_id,
        "company_id": company_id,
        "relationship_role": "issuer",
        "identity_scope": "current_only",
        "identity_observed_at": identity["identity_observed_at"],
        "securities": rendered,
    }


def _stock_links(issuer: Mapping[str, Any]) -> list[dict[str, str]]:
    if issuer.get("state") != "resolved":
        return []
    links: list[dict[str, str]] = []
    for security in issuer.get("securities", []):
        symbol = security.get("display_symbol")
        if not isinstance(symbol, str) or not symbol:
            continue
        links.append({
            "security_id": security["security_id"],
            "relationship_role": "issuer",
            "href": f"stock.html?ticker={quote(symbol, safe='')}",
        })
    return links


def compose_company_event_rows(
    event: object,
    *,
    identity_projection: object,
    source_health: str,
    evaluation_cutoff: object,
    anchor_date: object,
) -> list[dict[str, Any]]:
    """Compose the first bounded company-disclosure WMN row.

    Ambiguous/unresolved CIK joins remain one unjoined row: candidate issuers are
    retained in the generation's identity projection, not promoted into admitted
    stock links.  A single resolved issuer retains every active share class.
    """
    owner = project_company_event_input(event, generation_cutoff=evaluation_cutoff)
    identity = _validate_identity_projection(
        identity_projection,
        company_id=owner["company_id"],
        issuer_cik=owner["issuer_cik"],
        evaluation_cutoff=evaluation_cutoff,
    )
    issuer = _admitted_issuer(identity, company_id=owner["company_id"])
    rp_identity_state = "resolved" if issuer["state"] == "resolved" else "unresolved"
    priority_input = {
        "event_fact_ref": owner["event_fact_ref"],
        "exposure_ref": None,
        "revision_is_current": owner["revision_is_current"],
        "occurrence": owner["occurrence"],
        "source_health": source_health,
        "identity_state": rp_identity_state,
        "timing_state": owner["timing"]["state"],
        "lower_date": owner["timing"]["lower_date"],
        "upper_date": owner["timing"]["upper_date"],
        # The current event port does not yet attest which revision was material.
        "last_material_revision_known_at": None,
    }
    priority = classify_research_priority(
        priority_input,
        evaluation_cutoff=evaluation_cutoff,
        anchor_date=anchor_date,
    )

    identity_missing = []
    if issuer["state"] == "unresolved":
        identity_missing = ["CURRENT_ISSUER_UNRESOLVED"]
    elif issuer["state"] == "ambiguous":
        identity_missing = ["AMBIGUOUS_CURRENT_CIK"]
    source_missing = [] if source_health == "current" else ["SOURCE_NOT_CURRENT"]
    estimate_reasons = [
        "PROBABILITY_OWNER_NOT_ADMITTED",
        "MATERIALITY_OWNER_NOT_ADMITTED",
        "HISTORICAL_RESPONSE_OWNER_NOT_ADMITTED",
        "INCORPORATION_OWNER_NOT_ADMITTED",
    ]
    row = {
        "row_key": {
            "event_fact_ref": owner["event_fact_ref"],
            "issuer_id": issuer["issuer_id"],
        },
        "event_fact_ref": owner["event_fact_ref"],
        "event_family": owner["event_family"],
        "event_revision_ref": owner["event_revision_ref"],
        "revision_is_current": owner["revision_is_current"],
        "occurrence": owner["occurrence"],
        "timing": dict(owner["timing"]),
        "issuer": issuer,
        "assets": [],
        "relationships": [],
        "economic_exposure_state": "unresolved",
        "evidence": [],
        "revision_summary": {
            "revision_ref": owner["event_revision_ref"],
            "revision_is_current": owner["revision_is_current"],
            "last_material_revision_known_at": None,
        },
        "research_priority": priority,
        "probability": _estimate_slot("probability"),
        "materiality": _estimate_slot("materiality"),
        "historical_response": _estimate_slot("historical_response"),
        "incorporation": _estimate_slot("incorporation"),
        "missingness": {
            "source": source_missing,
            "identity": identity_missing,
            "asset": ["ASSET_PORT_NOT_ADMITTED"],
            "economic": ["ECONOMIC_EXPOSURE_UNRESOLVED"],
            "estimates": estimate_reasons,
        },
        "links": {"stock_research": _stock_links(issuer)},
    }
    if set(row) != _ROW_KEYS:
        raise AssertionError("WMN row contract drift")
    return [row]


_REGISTRY_KIND_FAMILY = {
    "primary_completion": "registry_primary_completion",
    "completion": "registry_study_completion",
}
_REGISTRY_EVENT_KEYS = {
    "event_id", "nct_id", "kind", "trial", "milestone", "timing",
    "trial_status", "issuer", "revision", "evidence", "event_revision_ref",
}


def compose_registry_milestone_rows(
    registry_events: Sequence[Mapping[str, Any]],
    *,
    source_health: str,
    evaluation_cutoff: object,
    anchor_date: object,
) -> list[dict[str, Any]]:
    """Compose current-generation Trial Milestone owner rows for WMN.

    The events are the existing project_trial_milestones output plus the
    current trial_snapshot.v1 snapshot id as event_revision_ref. The owner
    event id is retained verbatim. Registry sponsor/ticker annotations are
    deliberately ignored here: without an admitted corporate identity
    relation, the WMN issuer remains unresolved.
    """
    if isinstance(registry_events, (str, bytes)) or not isinstance(registry_events, Sequence):
        raise ContractError("registry milestone events must be a bounded sequence")
    if len(registry_events) > 200_000:
        raise ContractError("registry milestone events too large")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in registry_events:
        if not isinstance(raw, Mapping) or set(raw) != _REGISTRY_EVENT_KEYS:
            raise ContractError("registry milestone event shape invalid")
        event_ref = raw.get("event_id")
        nct_id = raw.get("nct_id")
        kind = raw.get("kind")
        if (
            not isinstance(event_ref, str)
            or not isinstance(nct_id, str)
            or kind not in _REGISTRY_KIND_FAMILY
            or event_ref != f"nct:{nct_id}:{kind}"
            or event_ref in seen
        ):
            raise ContractError("registry milestone event identity invalid")
        seen.add(event_ref)
        revision_ref = raw.get("event_revision_ref")
        if not isinstance(revision_ref, str) or not revision_ref.startswith("trial_snapshot_"):
            raise ContractError("registry milestone revision ref invalid")
        milestone = raw.get("milestone")
        revision = raw.get("revision")
        evidence = raw.get("evidence")
        if not isinstance(milestone, Mapping) or not isinstance(revision, Mapping):
            raise ContractError("registry milestone owner blocks invalid")
        lower = milestone.get("interval_start")
        upper = milestone.get("interval_end")
        if lower is not None and not isinstance(lower, str):
            raise ContractError("registry milestone lower_date invalid")
        if upper is not None and not isinstance(upper, str):
            raise ContractError("registry milestone upper_date invalid")
        latest = revision.get("latest")
        last_material_revision_known_at = (
            latest.get("observed_at")
            if isinstance(latest, Mapping) and isinstance(latest.get("observed_at"), str)
            else None
        )
        timing = {
            "state": "consistent",
            "source_class": "registry_schedule",
            "lower_date": lower,
            "upper_date": upper,
            "precision": milestone.get("precision") or "unknown",
            "source_timezone": None,
            "source_wording": milestone.get("date"),
            "evidence_refs": (
                [evidence["url"]]
                if isinstance(evidence, Mapping)
                and isinstance(evidence.get("url"), str)
                and evidence["url"]
                else []
            ),
        }
        priority = classify_research_priority(
            {
                "event_fact_ref": event_ref,
                "exposure_ref": None,
                "revision_is_current": True,
                "occurrence": "uncorroborated",
                "source_health": source_health,
                "identity_state": "unresolved",
                "timing_state": "consistent",
                "lower_date": lower,
                "upper_date": upper,
                "last_material_revision_known_at": last_material_revision_known_at,
            },
            evaluation_cutoff=evaluation_cutoff,
            anchor_date=anchor_date,
        )
        estimate_reasons = [
            "PROBABILITY_OWNER_NOT_ADMITTED",
            "MATERIALITY_OWNER_NOT_ADMITTED",
            "HISTORICAL_RESPONSE_OWNER_NOT_ADMITTED",
            "INCORPORATION_OWNER_NOT_ADMITTED",
        ]
        row = {
            "row_key": {"event_fact_ref": event_ref, "issuer_id": None},
            "event_fact_ref": event_ref,
            "event_family": _REGISTRY_KIND_FAMILY[str(kind)],
            "event_revision_ref": revision_ref,
            "revision_is_current": True,
            "occurrence": "uncorroborated",
            "timing": timing,
            "issuer": {
                "state": "unresolved",
                "issuer_id": None,
                "company_id": None,
                "relationship_role": None,
                "identity_scope": "unavailable",
                "identity_observed_at": None,
                "securities": [],
            },
            "assets": [],
            "relationships": [],
            "economic_exposure_state": "unresolved",
            "evidence": [dict(evidence)] if isinstance(evidence, Mapping) else [],
            "revision_summary": {
                "revision_ref": revision_ref,
                "revision_is_current": True,
                "last_material_revision_known_at": last_material_revision_known_at,
            },
            "research_priority": priority,
            "probability": _estimate_slot("probability"),
            "materiality": _estimate_slot("materiality"),
            "historical_response": _estimate_slot("historical_response"),
            "incorporation": _estimate_slot("incorporation"),
            "missingness": {
                "source": [] if source_health == "current" else ["SOURCE_NOT_CURRENT"],
                "identity": ["CURRENT_ISSUER_UNRESOLVED"],
                "asset": ["ASSET_PORT_NOT_ADMITTED"],
                "economic": ["ECONOMIC_EXPOSURE_UNRESOLVED"],
                "estimates": estimate_reasons,
            },
            "links": {"stock_research": []},
        }
        if set(row) != _ROW_KEYS:
            raise AssertionError("WMN registry row contract drift")
        rows.append(row)
    return rows


_WMN_VIEWS = frozenset({"upcoming", "reconcile", "history"})
_WMN_HORIZONS = frozenset({7, 30, 90, 180, 365})
_WMN_LANES = frozenset({"ACT_NOW", "RECONCILE", "RESEARCH_NEXT", "MONITOR"})
_WMN_FAMILIES = frozenset({
    "registry_primary_completion",
    "registry_study_completion",
    "issuer_readout_guidance",
    "regulatory_target_disclosed",
    "advisory_meeting_disclosed",
    "result_announced",
    "regulatory_action",
})
_WMN_RESOLVED_OCCURRENCES = frozenset({"corroborated", "cancelled", "withdrawn"})


def _wmn_search_haystack(row: Mapping[str, Any]) -> str:
    values: list[str] = [
        str(row.get("event_fact_ref") or ""),
        str(row.get("event_family") or ""),
    ]
    issuer = row.get("issuer")
    if isinstance(issuer, Mapping):
        values.extend([
            str(issuer.get("issuer_id") or ""),
            str(issuer.get("company_id") or ""),
            str(issuer.get("relationship_role") or ""),
        ])
        securities = issuer.get("securities")
        if isinstance(securities, list):
            for security in securities:
                if isinstance(security, Mapping):
                    values.extend([
                        str(security.get("security_id") or ""),
                        str(security.get("listing_key") or ""),
                        str(security.get("display_symbol") or ""),
                    ])
    timing = row.get("timing")
    if isinstance(timing, Mapping):
        values.append(str(timing.get("source_wording") or ""))
    return " ".join(values).casefold()


def select_what_matters_next_rows(
    rows: list[Mapping[str, Any]],
    *,
    view: str,
    horizon_days: int | None,
    q: str | None,
    event_family: str | None,
    lane: str | None,
    anchor_date: str,
) -> list[Mapping[str, Any]]:
    """Select and fully sort one WMN view before pagination.

    Reconciliation rows never disappear merely because they cannot satisfy a
    dated horizon; resolved history is a separate view; superseded revisions
    are retained for coverage accounting elsewhere but never rendered here.
    """
    if view not in _WMN_VIEWS:
        raise ValueError("invalid WMN view")
    if view == "upcoming":
        if horizon_days not in _WMN_HORIZONS:
            raise ValueError("upcoming view requires a supported horizon")
    elif horizon_days is not None:
        raise ValueError("non-upcoming WMN views require a null horizon")
    if event_family is not None and event_family not in _WMN_FAMILIES:
        raise ValueError("invalid WMN event_family")
    if lane is not None and lane not in _WMN_LANES:
        raise ValueError("invalid WMN lane")
    query: str | None = None
    if q is not None:
        query = q.strip().casefold()
        if not query or len(query) > 100:
            raise ValueError("invalid WMN search query")

    selected: list[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("WMN row must be an object")
        priority = row.get("research_priority")
        if not isinstance(priority, Mapping):
            raise ValueError("WMN row lacks research_priority")
        if priority.get("disposition") != "SELECTED":
            continue
        occurrence = row.get("occurrence")
        row_lane = priority.get("lane")
        if view == "history":
            if occurrence not in _WMN_RESOLVED_OCCURRENCES:
                continue
        elif view == "reconcile":
            if row_lane != "RECONCILE":
                continue
        else:
            if occurrence != "uncorroborated" or row_lane == "RECONCILE":
                continue
            timing = row.get("timing")
            if not isinstance(timing, Mapping):
                raise ValueError("WMN row timing invalid")
            if not interval_overlaps_horizon(
                timing.get("lower_date"),
                timing.get("upper_date"),
                anchor_date=anchor_date,
                days=int(horizon_days),
            ):
                continue
        if event_family is not None and row.get("event_family") != event_family:
            continue
        if lane is not None and row_lane != lane:
            continue
        if query is not None and query not in _wmn_search_haystack(row):
            continue
        selected.append(row)
    return list(sort_research_priority_rows(selected))


_WMN_INPUT_KEYS = frozenset({
    "contract_id", "schema_version", "input_cut", "events", "relationships",
    "identity_projection", "coverage", "authority",
})
_WMN_INPUT_CUT_KEYS = frozenset({"cutoff", "members"})
_WMN_INPUT_MEMBER_KEYS = frozenset({
    "contract_id", "ref", "sha256", "observed_at", "accepted_at", "availability",
})
_WMN_COVERAGE_KEYS = frozenset({
    "declared_universe_ref", "source_health", "family_states", "missing_owner_ports",
})
_WMN_FAMILY_STATE_KEYS = frozenset({"declared_scope", "observed_count", "state"})
_WMN_FAMILY_STATES = frozenset({
    "supported", "not_built", "unavailable", "not_admitted", "partial",
})
_WMN_SOURCE_HEALTH = frozenset({"current", "stale", "partial", "unavailable"})
_WMN_SHA256_RE = __import__("re").compile(r"^[0-9a-f]{64}$")


def _wmn_exact_mapping(value: object, *, field: str, keys: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ContractError(f"{field} shape invalid")
    return value


def _wmn_nonempty_text(value: object, *, field: str, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{field} must be text")
    rendered = value.strip()
    if not rendered or len(rendered) > limit:
        raise ContractError(f"{field} invalid")
    return rendered


def _wmn_input_cut(
    value: object,
    *,
    forbidden_generation_id: str | None,
) -> dict[str, Any]:
    cut = _wmn_exact_mapping(value, field="input_cut", keys=_WMN_INPUT_CUT_KEYS)
    cutoff_literal, cutoff_time = _utc(cut.get("cutoff"), field="input_cut.cutoff")
    members = cut.get("members")
    if not isinstance(members, list) or not members:
        raise ContractError("input_cut.members must be a non-empty list")
    if len(members) > 1024:
        raise ContractError("input_cut.members too large")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in members:
        member = _wmn_exact_mapping(raw, field="input_cut member", keys=_WMN_INPUT_MEMBER_KEYS)
        contract_id = _wmn_nonempty_text(member.get("contract_id"), field="input_cut member contract_id")
        ref = _wmn_nonempty_text(member.get("ref"), field="input_cut member ref", limit=1024)
        digest = member.get("sha256")
        if not isinstance(digest, str) or _WMN_SHA256_RE.fullmatch(digest) is None:
            raise ContractError("input_cut member sha256 invalid")
        if member.get("availability") != "available":
            raise ContractError("input_cut member availability is not admitted in first slice")
        observed_literal, observed_time = _utc(
            member.get("observed_at"), field="input_cut member observed_at"
        )
        accepted_literal, accepted_time = _utc(
            member.get("accepted_at"), field="input_cut member accepted_at"
        )
        if observed_time > cutoff_time or accepted_time > cutoff_time:
            raise ContractError("input_cut member clock exceeds input_cut cutoff")
        if accepted_time < observed_time:
            raise ContractError("input_cut member accepted_at precedes observed_at")
        if forbidden_generation_id is not None and ref == forbidden_generation_id:
            raise ContractError("input_cut references the future generation")
        identity = (contract_id, ref)
        if identity in seen:
            raise ContractError("input_cut contains duplicate member identity")
        seen.add(identity)
        normalized.append({
            "contract_id": contract_id,
            "ref": ref,
            "sha256": digest,
            "observed_at": observed_literal,
            "accepted_at": accepted_literal,
            "availability": "available",
        })
    normalized.sort(key=lambda item: (item["contract_id"], item["ref"]))
    return {"cutoff": cutoff_literal, "members": normalized}


def _wmn_family_states(value: object) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise ContractError("coverage.family_states must be an object")
    normalized: dict[str, dict[str, Any]] = {}
    for family in sorted(value):
        if family not in _WMN_FAMILIES:
            raise ContractError("coverage.family_states contains an unsupported family")
        raw = _wmn_exact_mapping(
            value[family], field="coverage.family_states entry", keys=_WMN_FAMILY_STATE_KEYS
        )
        declared_scope = _wmn_nonempty_text(
            raw.get("declared_scope"), field="coverage.family_states declared_scope", limit=1024
        )
        observed_count = raw.get("observed_count")
        if observed_count is not None and (
            isinstance(observed_count, bool)
            or not isinstance(observed_count, int)
            or observed_count < 0
        ):
            raise ContractError("coverage.family_states observed_count invalid")
        state = raw.get("state")
        if state not in _WMN_FAMILY_STATES:
            raise ContractError("coverage.family_states state invalid")
        if state == "supported" and observed_count is None:
            raise ContractError("coverage.family_states supported state needs observed_count")
        normalized[family] = {
            "declared_scope": declared_scope,
            "observed_count": observed_count,
            "state": state,
        }
    return normalized


def _wmn_coverage(value: object) -> dict[str, Any]:
    coverage = _wmn_exact_mapping(value, field="coverage", keys=_WMN_COVERAGE_KEYS)
    universe_ref = _wmn_nonempty_text(
        coverage.get("declared_universe_ref"), field="coverage.declared_universe_ref", limit=1024
    )
    source_health = coverage.get("source_health")
    if source_health not in _WMN_SOURCE_HEALTH:
        raise ContractError("coverage.source_health invalid")
    ports = coverage.get("missing_owner_ports")
    if not isinstance(ports, list) or len(ports) > 128:
        raise ContractError("coverage.missing_owner_ports invalid")
    normalized_ports: list[str] = []
    for port in ports:
        normalized_ports.append(
            _wmn_nonempty_text(port, field="coverage.missing_owner_ports item", limit=160)
        )
    if len(normalized_ports) != len(set(normalized_ports)):
        raise ContractError("coverage.missing_owner_ports contains duplicates")
    return {
        "declared_universe_ref": universe_ref,
        "source_health": source_health,
        "family_states": _wmn_family_states(coverage.get("family_states")),
        "missing_owner_ports": normalized_ports,
    }


def validate_wmn_inputs(
    payload: object,
    *,
    forbidden_generation_id: str | None = None,
) -> dict[str, Any]:
    """Validate one immutable owner-input cut for What Matters Next.

    The first slice binds Company Intelligence event bytes and the CURRENT Data
    OS identity projection.  It deliberately admits no relationship/asset or
    estimate owner blob yet.  The cut is self-contained so request handlers do
    not perform live owner reads or stitch generations.
    """
    item = _wmn_exact_mapping(payload, field="wmn_inputs", keys=_WMN_INPUT_KEYS)
    if item.get("contract_id") != "biocatalyst_wmn_inputs.v1":
        raise ContractError("wmn_inputs contract_id invalid")
    if item.get("schema_version") != "1.0.0":
        raise ContractError("wmn_inputs schema_version invalid")
    input_cut = _wmn_input_cut(
        item.get("input_cut"), forbidden_generation_id=forbidden_generation_id
    )
    cutoff = input_cut["cutoff"]

    raw_events = item.get("events")
    if not isinstance(raw_events, list) or len(raw_events) > 100_000:
        raise ContractError("wmn_inputs events must be a bounded list")
    events: list[dict[str, Any]] = []
    event_ids: list[str] = []
    for raw in raw_events:
        event = validate_company_catalyst_event(raw, generation_cutoff=cutoff)
        if event["event_id"] in event_ids:
            raise ContractError("wmn_inputs contains duplicate event identity")
        event_ids.append(event["event_id"])
        events.append(event)
    events.sort(key=lambda event: event["event_id"])
    event_ids = [event["event_id"] for event in events]

    cut_members = input_cut["members"]
    allowed_member_contracts = {"company_catalyst_event.v1", "dataos_issuer_master.current"}
    if any(member["contract_id"] not in allowed_member_contracts for member in cut_members):
        raise ContractError("input_cut contains an owner contract not admitted in first slice")
    dataos_members = [
        member for member in cut_members
        if member["contract_id"] == "dataos_issuer_master.current"
    ]
    if len(dataos_members) != 1:
        raise ContractError("input_cut requires exactly one Data OS current-master member")
    event_member_by_ref = {
        member["ref"]: member
        for member in cut_members
        if member["contract_id"] == "company_catalyst_event.v1"
    }
    if set(event_member_by_ref) != set(event_ids):
        raise ContractError("input_cut must bind exactly one Company event member per event")
    for event in events:
        if event_member_by_ref[event["event_id"]]["sha256"] != canonical_json_sha256(event):
            raise ContractError("input_cut Company event hash mismatch")

    if item.get("relationships") != []:
        raise ContractError("relationships are not admitted in the first WMN input slice")

    raw_identity = item.get("identity_projection")
    if not isinstance(raw_identity, Mapping):
        raise ContractError("identity_projection must be an object")
    if set(raw_identity) != set(event_ids):
        raise ContractError("identity_projection must bind exactly one projection per event")
    identity_projection: dict[str, dict[str, Any]] = {}
    events_by_id = {event["event_id"]: event for event in events}
    for event_id in sorted(event_ids):
        event = events_by_id[event_id]
        identity_projection[event_id] = _validate_identity_projection(
            raw_identity[event_id],
            company_id=event["company_id"],
            issuer_cik=event["issuer_cik"],
            evaluation_cutoff=cutoff,
        )

    coverage = _wmn_coverage(item.get("coverage"))
    family_counts: dict[str, int] = {}
    for event in events:
        family_counts[event["event_family"]] = family_counts.get(event["event_family"], 0) + 1
    for family, count in family_counts.items():
        state = coverage["family_states"].get(family)
        if state is None:
            raise ContractError("coverage.family_states missing an admitted event family")
        if state["state"] not in {"supported", "partial"} or state["observed_count"] != count:
            raise ContractError("coverage.family_states observed_count disagrees with events")
    authority = item.get("authority")
    if authority != CATALYST_SOURCE_FACT_AUTHORITY:
        raise ContractError("wmn_inputs authority invalid")

    if forbidden_generation_id is not None:
        def contains_future(value: object) -> bool:
            if isinstance(value, str):
                return forbidden_generation_id in value
            if isinstance(value, Mapping):
                return any(contains_future(k) or contains_future(v) for k, v in value.items())
            if isinstance(value, list):
                return any(contains_future(v) for v in value)
            return False
        # Run after the direct member-ref discriminator so the common failure
        # receives the specific cut error above; this catches hidden hash cycles
        # in owner payloads as a second line of defense.
        normalized_probe = {
            "events": events,
            "identity_projection": identity_projection,
            "coverage": coverage,
        }
        if contains_future(normalized_probe):
            raise ContractError("wmn_inputs embeds the future generation")

    return {
        "contract_id": "biocatalyst_wmn_inputs.v1",
        "schema_version": "1.0.0",
        "input_cut": input_cut,
        "events": events,
        "relationships": [],
        "identity_projection": identity_projection,
        "coverage": coverage,
        "authority": {
            "classification": "source_fact",
            "decision_authority": False,
            "allowed_uses": ["display", "context", "explain"],
            "forbidden_uses": list(CATALYST_SOURCE_FACT_AUTHORITY["forbidden_uses"]),
        },
    }


def compose_rows_from_wmn_inputs(
    payload: object,
    *,
    evaluation_cutoff: object,
    anchor_date: object,
    registry_events: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Compose a complete admitted WMN row set from one immutable generation cut."""
    inputs = validate_wmn_inputs(payload)
    _input_cut_literal, input_cut_time = _utc(
        inputs["input_cut"]["cutoff"], field="input_cut.cutoff"
    )
    _evaluation_literal, evaluation_time = _utc(
        evaluation_cutoff, field="evaluation_cutoff"
    )
    if evaluation_time < input_cut_time:
        raise ContractError("evaluation_cutoff precedes input_cut cutoff")
    source_health = inputs["coverage"]["source_health"]
    rows: list[dict[str, Any]] = []
    for event in inputs["events"]:
        rows.extend(
            compose_company_event_rows(
                event,
                identity_projection=inputs["identity_projection"][event["event_id"]],
                source_health=source_health,
                evaluation_cutoff=evaluation_cutoff,
                anchor_date=anchor_date,
            )
        )
    if registry_events is not None:
        rows.extend(
            compose_registry_milestone_rows(
                registry_events,
                source_health=source_health,
                evaluation_cutoff=evaluation_cutoff,
                anchor_date=anchor_date,
            )
        )
    return sorted(
        rows,
        key=lambda row: (
            str(row["event_fact_ref"]),
            str((row.get("issuer") or {}).get("issuer_id") or ""),
        ),
    )



def normalize_wmn_query(
    *,
    view: object = "upcoming",
    horizon_days: object | None = None,
    q: object | None = None,
    event_family: object | None = None,
    lane: object | None = None,
    limit: object = 50,
) -> dict[str, Any]:
    """Normalize the closed public WMN query before any projection I/O."""
    if view not in _WMN_VIEWS:
        raise ValueError("invalid WMN view")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 250:
        raise ValueError("invalid WMN limit")
    normalized_horizon: int | None
    if view == "upcoming":
        normalized_horizon = 90 if horizon_days is None else horizon_days
        if isinstance(normalized_horizon, bool) or normalized_horizon not in _WMN_HORIZONS:
            raise ValueError("invalid WMN horizon")
    else:
        if horizon_days is not None:
            raise ValueError("non-upcoming WMN view requires null horizon")
        normalized_horizon = None
    normalized_q: str | None = None
    if q is not None:
        if not isinstance(q, str):
            raise ValueError("invalid WMN search query")
        normalized_q = q.strip().casefold()
        if not normalized_q or len(normalized_q) > 100:
            raise ValueError("invalid WMN search query")
    if event_family is not None and event_family not in _WMN_FAMILIES:
        raise ValueError("invalid WMN event_family")
    if lane is not None and lane not in _WMN_LANES:
        raise ValueError("invalid WMN lane")
    return {
        "view": str(view),
        "horizon_days": normalized_horizon,
        "q": normalized_q,
        "event_family": event_family,
        "lane": lane,
        "limit": limit,
    }


def wmn_row_cursor_key(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the complete stable ordering identity used by the signed cursor."""
    priority = row.get("research_priority")
    timing = row.get("timing")
    revision = row.get("revision_summary")
    row_key = row.get("row_key")
    if not all(isinstance(value, Mapping) for value in (priority, timing, revision, row_key)):
        raise ValueError("WMN row cannot supply a stable cursor key")
    lane = priority.get("lane")
    if lane not in _WMN_LANES:
        raise ValueError("WMN row cannot supply a selected lane")
    event_fact_ref = row.get("event_fact_ref")
    if not isinstance(event_fact_ref, str) or not event_fact_ref:
        raise ValueError("WMN row event_fact_ref invalid")
    issuer_id = row_key.get("issuer_id")
    if issuer_id is not None and not isinstance(issuer_id, str):
        raise ValueError("WMN row issuer key invalid")
    return {
        "lane": lane,
        "upper_date": timing.get("upper_date"),
        "lower_date": timing.get("lower_date"),
        "last_material_revision_known_at": revision.get("last_material_revision_known_at"),
        "event_fact_ref": event_fact_ref,
        "row_key": {
            "event_fact_ref": row_key.get("event_fact_ref"),
            "issuer_id": issuer_id,
        },
    }


def _wmn_global_coverage(
    inputs: Mapping[str, Any],
    rows: list[Mapping[str, Any]],
    *,
    selected_row_count: int,
    registry_available: bool = False,
) -> dict[str, Any]:
    source_events = {str(row["event_fact_ref"]) for row in rows}
    issuer_events: set[tuple[str, str]] = set()
    securities: set[str] = set()
    unresolved_events: set[str] = set()
    superseded: set[str] = set()
    lane_counts = {lane: 0 for lane in ("ACT_NOW", "RECONCILE", "RESEARCH_NEXT", "MONITOR")}
    for row in rows:
        event_ref = str(row["event_fact_ref"])
        issuer = row.get("issuer")
        if isinstance(issuer, Mapping) and issuer.get("state") == "resolved":
            issuer_id = issuer.get("issuer_id")
            if isinstance(issuer_id, str):
                issuer_events.add((event_ref, issuer_id))
            for security in issuer.get("securities", []):
                if isinstance(security, Mapping) and isinstance(security.get("security_id"), str):
                    securities.add(security["security_id"])
        else:
            unresolved_events.add(event_ref)
        priority = row.get("research_priority")
        if isinstance(priority, Mapping):
            if priority.get("disposition") == "EXCLUDE_SUPERSEDED":
                superseded.add(event_ref)
            lane = priority.get("lane")
            if priority.get("disposition") == "SELECTED" and lane in lane_counts:
                lane_counts[str(lane)] += 1
    coverage = inputs["coverage"]
    family_states = {
        family: dict(state)
        for family, state in coverage["family_states"].items()
    }
    if registry_available:
        registry_counts = {
            family: sum(1 for row in rows if row.get("event_family") == family)
            for family in ("registry_primary_completion", "registry_study_completion")
        }
        for family, count in registry_counts.items():
            family_states[family] = {
                "declared_scope": "committed_trial_projection:current_generation",
                "observed_count": count,
                "state": "supported",
            }
    return {
        "declared_universe_ref": coverage["declared_universe_ref"],
        "source_event_count": len(source_events),
        "issuer_event_count": len(issuer_events),
        "security_count": len(securities),
        "unresolved_event_count": len(unresolved_events),
        "rejected_count": 0,
        "superseded_count": len(superseded),
        "lane_counts": lane_counts,
        "selected_row_count": selected_row_count,
        "family_states": family_states,
        "missing_owner_ports": list(coverage["missing_owner_ports"]),
    }


def build_what_matters_next(
    bundle: object,
    *,
    generation_id: object,
    query: Mapping[str, Any],
    evaluation_cutoff: object,
    anchor_date: object,
    registry_events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the closed request-relative WMN read projection from one immutable cut."""
    if not isinstance(generation_id, str) or not generation_id:
        raise ContractError("generation_id invalid")
    normalized_query = normalize_wmn_query(**dict(query))
    inputs = validate_wmn_inputs(bundle, forbidden_generation_id=generation_id)
    rows = compose_rows_from_wmn_inputs(
        inputs,
        evaluation_cutoff=evaluation_cutoff,
        anchor_date=anchor_date,
        registry_events=registry_events,
    )
    selected = select_what_matters_next_rows(
        rows,
        view=normalized_query["view"],
        horizon_days=normalized_query["horizon_days"],
        q=normalized_query["q"],
        event_family=normalized_query["event_family"],
        lane=normalized_query["lane"],
        anchor_date=str(anchor_date),
    )
    coverage = _wmn_global_coverage(
        inputs,
        rows,
        selected_row_count=len(selected),
        registry_available=registry_events is not None,
    )
    source_health = inputs["coverage"]["source_health"]
    coverage_incomplete = (
        bool(coverage["missing_owner_ports"])
        or source_health in {"partial", "unavailable"}
        or any(
            state["state"] != "supported"
            for state in coverage["family_states"].values()
        )
    )
    if coverage_incomplete:
        state = "partial"
    elif source_health == "stale":
        state = "stale"
    elif not selected:
        state = "empty"
    else:
        state = "ready"
    cutoff_literal, _cutoff_time = _utc(evaluation_cutoff, field="evaluation_cutoff")
    if not isinstance(anchor_date, str) or len(anchor_date) != 10:
        raise ContractError("anchor_date invalid")
    return {
        "contract_id": "biocatalyst_what_matters_next.v1",
        "schema_version": "1.0.0",
        "generation_id": generation_id,
        "state": state,
        "reason_codes": [],
        "input_cut": inputs["input_cut"],
        "query": normalized_query,
        "evaluation_cutoff": cutoff_literal,
        "anchor_date": anchor_date,
        "method_id": METHOD_ID,
        "authority": {
            "classification": "research_priority_only",
            "trade_origination": False,
            "changes_availability": False,
            "position_sizing": False,
            "prophet_admission": False,
        },
        "coverage": coverage,
        "rows": selected,
        "pagination": {
            "limit": normalized_query["limit"],
            "total": len(selected),
            "next_cursor": None,
        },
    }


def build_what_matters_next_detail(
    bundle: object,
    *,
    generation_id: object,
    event_fact_ref: object,
    issuer_id: object | None,
    evaluation_cutoff: object,
    anchor_date: object,
    registry_events: Sequence[Mapping[str, Any]] | None = None,
    registry_trial_details: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve one WMN row and related rows strictly inside one generation.

    The first executable slice contains Company Intelligence disclosure events,
    so the existing Trial detail projection is intentionally absent and the
    public reason is ``non_registry_event``.  Future registry-family support
    must bind the trial object from this same generation rather than fetching
    the latest Trial workspace.
    """
    if not isinstance(generation_id, str) or not generation_id:
        raise ContractError("generation_id invalid")
    if not isinstance(event_fact_ref, str) or not event_fact_ref:
        raise ValueError("event_fact_ref invalid")
    if issuer_id is not None and (not isinstance(issuer_id, str) or not issuer_id):
        raise ValueError("issuer_id invalid")
    inputs = validate_wmn_inputs(bundle, forbidden_generation_id=generation_id)
    rows = compose_rows_from_wmn_inputs(
        inputs,
        evaluation_cutoff=evaluation_cutoff,
        anchor_date=anchor_date,
        registry_events=registry_events,
    )
    current_rows = [
        row for row in rows
        if isinstance(row.get("research_priority"), Mapping)
        and row["research_priority"].get("disposition") == "SELECTED"
    ]
    matches = [row for row in current_rows if row.get("event_fact_ref") == event_fact_ref]
    if issuer_id is not None:
        matches = [
            row for row in matches
            if isinstance(row.get("row_key"), Mapping)
            and row["row_key"].get("issuer_id") == issuer_id
        ]
    if not matches:
        raise LookupError("EVENT_NOT_IN_GENERATION")
    if len(matches) != 1:
        raise ValueError("issuer_id required to disambiguate event row")
    selected = matches[0]
    selected_issuer = None
    issuer = selected.get("issuer")
    if isinstance(issuer, Mapping) and isinstance(issuer.get("issuer_id"), str):
        selected_issuer = issuer["issuer_id"]
    related = []
    if selected_issuer is not None:
        related = [
            row for row in current_rows
            if row.get("event_fact_ref") != event_fact_ref
            and isinstance(row.get("issuer"), Mapping)
            and row["issuer"].get("issuer_id") == selected_issuer
        ]
        related = list(sort_research_priority_rows(related))
    trial = None
    reason_codes = ["non_registry_event"]
    if selected.get("event_family") in {
        "registry_primary_completion", "registry_study_completion"
    }:
        if not isinstance(registry_trial_details, Mapping):
            raise ContractError("registry detail lacks same-generation trial projection")
        candidate = registry_trial_details.get(str(selected["event_fact_ref"]))
        if not isinstance(candidate, Mapping):
            raise ContractError("registry detail lacks same-generation trial projection")
        parts = str(selected["event_fact_ref"]).split(":")
        expected_nct = parts[1] if len(parts) == 3 else None
        if candidate.get("nct_id") != expected_nct:
            raise ContractError("registry detail trial identity mismatch")
        trial = dict(candidate)
        reason_codes = []
    return {
        "contract_id": "biocatalyst_wmn_detail.v1",
        "schema_version": "1.0.0",
        "generation_id": generation_id,
        "event": selected,
        "trial": trial,
        "related_events": related,
        "reason_codes": reason_codes,
        "authority": {
            "classification": "research_priority_only",
            "trade_origination": False,
            "changes_availability": False,
            "position_sizing": False,
            "prophet_admission": False,
        },
    }
