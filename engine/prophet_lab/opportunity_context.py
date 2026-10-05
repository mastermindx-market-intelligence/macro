"""Read-only Opportunity Lifecycle context over canonical Prophet B1/B3/B4.

This module is a presentation projection inside the existing Prophet Lab owner.
It creates no candidate, episode, strategy, entry verdict, forecast, plan, store,
rank, gate, or trading authority. It only binds one already-validated B3 row
to an optional already-validated B4 Availability receipt.

A missing B4 receipt is deliberately not rendered as ``entry_open=False``:
unknown permission is not a negative permission verdict. Likewise, private
Plan/position state, cross-domain evidence summaries and forecast heads remain
explicitly unjoined until their canonical owners are supplied by a later
authorized consumer.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Mapping, Sequence

from engine.prophet_candidate_state import validate_candidate_state_projection
from engine.prophet_entry_availability import validate_entry_availability
from engine.prophet_lab.contracts import ALL_FALSE_AUTHORITY
from lib.dataos.identity import VendorAliasTable
from lib.opportunity_evidence import validate_vector


SCHEMA = "prophet.lab_opportunity_context/v1"
B3_SCHEMA = "prophet.candidate_state_projection/v1"
B4_SCHEMA = "prophet.entry_availability/v1"
IDENTITY_BINDING_SCHEMA = "prophet.lab_opportunity_identity/v1"
PORTFOLIO_RELATION_SCHEMA = "prophet.lab_portfolio_relation/v1"
OEV_SCHEMA = "opportunity_evidence.vector.v1"

_UNJOINED_USER_STATE = {
    "plan": {
        "state": "NOT_JOINED",
        "plan_ref": None,
        "reason": "PRIVATE_PLAN_OWNER_NOT_READ",
    },
    "watchlist": {
        "state": "NOT_JOINED",
        "saved": None,
        "reason": "WATCHLIST_READ_CONTRACT_NOT_ADMITTED",
    },
    "portfolio": {
        "state": "NOT_JOINED",
        "relation": None,
        "reason": "PORTFOLIO_OWNER_NOT_READ",
    },
}
_UNJOINED_EVIDENCE = {
    "status": "NOT_JOINED",
    "source": None,
    "support": None,
    "contradiction": None,
    "unresolved": None,
    "next_observable": None,
    "reason": "OPPORTUNITY_EVIDENCE_NOT_JOINED",
}
_UNQUALIFIED_FORECAST = {
    "qualified": False,
    "heads": None,
    "reason": "NO_QUALIFIED_OLI_FORECAST",
}


class OpportunityContextContractError(ValueError):
    """Raised when owner identities/clocks cannot be joined without guessing."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpportunityContextContractError(f"{field} must be non-empty text")
    return value


def _candidate_row(
    candidate_projection: Mapping[str, object],
    episode_id: str,
) -> Mapping[str, object]:
    validate_candidate_state_projection(candidate_projection)
    if candidate_projection.get("schema") != B3_SCHEMA:
        raise OpportunityContextContractError("candidate projection schema mismatch")
    rows = candidate_projection.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise OpportunityContextContractError("candidate projection rows must be a list")
    matches = [
        row for row in rows
        if isinstance(row, Mapping) and row.get("episode_id") == episode_id
    ]
    if len(matches) != 1:
        raise OpportunityContextContractError(
            "episode_id must resolve to exactly one canonical B3 row"
        )
    return matches[0]


def _unavailable_entry(row: Mapping[str, object]) -> dict[str, object]:
    owner = row.get("entry_availability")
    if owner != {"state": "UNAVAILABLE_DATA", "reason": "B4_NOT_AVAILABLE"}:
        raise OpportunityContextContractError(
            "B3 unavailable-entry sentinel is not canonical"
        )
    return {
        "owner_schema": B4_SCHEMA,
        "state": "UNAVAILABLE_DATA",
        "entry_open": None,
        "reason": "B4_NOT_AVAILABLE",
        "availability_id": None,
        "evaluated_at": None,
        "market_session": None,
        "strategy": None,
        "current_price": None,
        "zone": None,
        "invalidation": None,
        "chase_state": None,
        "owner_status": None,
        "blockers": ["B4_NOT_AVAILABLE"],
        "reasons": [],
        "source_receipts": [],
    }


def _bound_entry(
    candidate_projection: Mapping[str, object],
    row: Mapping[str, object],
    availability: Mapping[str, object],
) -> dict[str, object]:
    validate_entry_availability(availability)

    bindings = {
        "episode_id": row.get("episode_id"),
        "candidate_generation_id": candidate_projection.get("candidate_generation_id"),
        "candidate_state_projection_id": candidate_projection.get("projection_id"),
        "security_id": row.get("security_id"),
        "identity_epoch": row.get("identity_epoch"),
        "market_session": candidate_projection.get("market_session"),
    }
    for field, expected in bindings.items():
        if availability.get(field) != expected:
            raise OpportunityContextContractError(
                f"B4 {field} does not match the selected B3 owner identity"
            )

    strategy = {
        "strategy_definition_id": availability.get("strategy_definition_id"),
        "strategy_id": availability.get("strategy_id"),
        "strategy_version": availability.get("strategy_version"),
        "horizon": availability.get("horizon"),
        "horizon_role": availability.get("horizon_role"),
        "entry_policy_version": availability.get("entry_policy_version"),
    }
    return {
        "owner_schema": B4_SCHEMA,
        "state": availability.get("state"),
        "entry_open": availability.get("entry_open"),
        "reason": None,
        "availability_id": availability.get("availability_id"),
        "evaluated_at": availability.get("evaluated_at"),
        "market_session": availability.get("market_session"),
        "strategy": strategy,
        "current_price": {
            "value": availability.get("current_price"),
            "basis": availability.get("current_price_basis"),
            "asof": availability.get("quote_asof"),
            "age_seconds": availability.get("quote_age_seconds"),
        },
        "zone": deepcopy(availability.get("zone")),
        "invalidation": deepcopy(availability.get("invalidation")),
        "chase_state": availability.get("chase_state"),
        "owner_status": availability.get("owner_status"),
        "blockers": list(availability.get("blockers") or []),
        "reasons": list(availability.get("reasons") or []),
        "source_receipts": list(availability.get("source_receipts") or []),
    }


def select_unique_active_episode_id(
    candidate_projection: Mapping[str, object],
    *,
    security_id: str,
) -> str:
    """Resolve one canonical security to exactly one ACTIVE B3 episode.

    This is a server-side identity helper for consumers that begin with a display
    alias. It does not resolve aliases itself and never falls back to ticker equality.
    Zero or multiple ACTIVE rows are explicit ambiguity/unavailability, not a guess.
    """
    validate_candidate_state_projection(candidate_projection)
    security_id = _text(security_id, "security_id")
    if not security_id.startswith("SEC:"):
        raise OpportunityContextContractError("security_id must be canonical SEC: identity")
    rows = candidate_projection.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise OpportunityContextContractError("candidate projection rows must be a list")

    matches: list[Mapping[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("security_id") != security_id:
            continue
        lifecycle = row.get("episode_lifecycle")
        if isinstance(lifecycle, Mapping) and lifecycle.get("state") == "ACTIVE":
            matches.append(row)

    if not matches:
        raise OpportunityContextContractError(
            "canonical security has no ACTIVE B3 episode in this projection"
        )
    if len(matches) != 1:
        raise OpportunityContextContractError(
            "canonical security has multiple ACTIVE B3 episodes in this projection"
        )
    return _text(matches[0].get("episode_id"), "episode_id")


def resolve_display_alias_to_active_episode(
    candidate_projection: Mapping[str, object],
    *,
    aliases: VendorAliasTable,
    display_symbol: str,
    decision_date: date,
) -> dict[str, object]:
    """Bind a current display alias to one canonical ACTIVE B3 episode.

    The resolver consumes the existing Data OS alias owner.
    It performs no I/O and never treats the display symbol as identity. Exact
    source-file receipts stay with the reader that actually read those files;
    this pure projection does not accept caller-supplied digests as proof. The
    current Candidate Pool uses the repository current-catalog store alias
    space, so that vendor is fixed here rather than caller-selectable.
    """
    validate_candidate_state_projection(candidate_projection)
    if not isinstance(aliases, VendorAliasTable):
        raise OpportunityContextContractError(
            "aliases must be the canonical Data OS VendorAliasTable"
        )
    if type(decision_date) is not date:
        raise OpportunityContextContractError("decision_date must be a calendar date")
    symbol = _text(display_symbol, "display_symbol").strip().upper()
    if not symbol:
        raise OpportunityContextContractError("display_symbol must be non-empty text")

    security_id = aliases.resolve("store", symbol, decision_date)
    if security_id is None:
        raise OpportunityContextContractError(
            "display symbol is unmapped in the Data OS store alias space"
        )
    reverse_symbol = aliases.vendor_symbol_for("store", security_id, decision_date)
    if reverse_symbol != symbol:
        raise OpportunityContextContractError(
            "Data OS reverse alias proof does not match the display symbol"
        )

    episode_id = select_unique_active_episode_id(
        candidate_projection,
        security_id=security_id,
    )
    row = _candidate_row(candidate_projection, episode_id)
    binding = {
        "schema": IDENTITY_BINDING_SCHEMA,
        "alias_vendor": "store",
        "display_symbol": symbol,
        "decision_date": decision_date.isoformat(),
        "security_id": row.get("security_id"),
        "company_id": row.get("company_id"),
        "identity_epoch": row.get("identity_epoch"),
        "episode_id": row.get("episode_id"),
        "candidate_generation_id": candidate_projection.get("candidate_generation_id"),
        "candidate_state_projection_id": candidate_projection.get("projection_id"),
        "authority": dict(ALL_FALSE_AUTHORITY),
    }
    validate_opportunity_identity_binding(binding)
    return binding


def validate_opportunity_identity_binding(payload: Mapping[str, object]) -> None:
    """Validate the alias-to-canonical identity proof without recomputing it."""
    if not isinstance(payload, Mapping):
        raise OpportunityContextContractError("opportunity identity binding must be an object")
    expected = {
        "schema", "alias_vendor", "display_symbol", "decision_date",
        "security_id", "company_id", "identity_epoch", "episode_id",
        "candidate_generation_id", "candidate_state_projection_id",
        "authority",
    }
    if set(payload) != expected:
        raise OpportunityContextContractError("opportunity identity binding fields are not closed")
    if payload.get("schema") != IDENTITY_BINDING_SCHEMA:
        raise OpportunityContextContractError("opportunity identity binding schema mismatch")
    if payload.get("alias_vendor") != "store":
        raise OpportunityContextContractError("opportunity identity binding vendor mismatch")
    for field in (
        "display_symbol", "decision_date", "security_id", "company_id",
        "identity_epoch", "episode_id", "candidate_generation_id",
        "candidate_state_projection_id",
    ):
        _text(payload.get(field), field)

    symbol = str(payload.get("display_symbol"))
    if symbol != symbol.strip().upper():
        raise OpportunityContextContractError(
            "opportunity identity display_symbol is not normalized"
        )
    try:
        parsed_decision_date = date.fromisoformat(str(payload.get("decision_date")))
    except ValueError as exc:
        raise OpportunityContextContractError(
            "opportunity identity decision_date is not ISO calendar date"
        ) from exc
    if parsed_decision_date.isoformat() != payload.get("decision_date"):
        raise OpportunityContextContractError(
            "opportunity identity decision_date is not canonical ISO calendar date"
        )

    prefixes = {
        "security_id": "SEC:",
        "company_id": "ISS:",
        "episode_id": "pe:",
        "candidate_generation_id": "peg:",
        "candidate_state_projection_id": "pcs:",
    }
    for field, prefix in prefixes.items():
        if not str(payload.get(field)).startswith(prefix):
            raise OpportunityContextContractError(
                f"opportunity identity {field} is not canonical"
            )

    if payload.get("authority") != ALL_FALSE_AUTHORITY:
        raise OpportunityContextContractError("opportunity identity authority must remain all false")

def project_terminal_portfolio_relation(
    identity_binding: Mapping[str, object],
    *,
    http_status: int,
    payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Project actual-position state from the canonical Terminal portfolio owner.

    The Terminal owner is ticker-keyed today, not Data-OS-security-keyed. The
    relation is therefore explicitly CURRENT_STORE_ALIAS and may never be used as
    permanent identity. No notes, size, entry price, risk or other private fields
    are copied into OLI; only owner row ids are retained for current open matches.
    """
    validate_opportunity_identity_binding(identity_binding)
    if type(http_status) is not int:
        raise OpportunityContextContractError("portfolio owner http_status must be an integer")

    base = {
        "schema": PORTFOLIO_RELATION_SCHEMA,
        "owner": "mastermind-terminal:/api/portfolio",
        "join_basis": "CURRENT_STORE_ALIAS",
        "display_symbol": identity_binding.get("display_symbol"),
        "security_id": identity_binding.get("security_id"),
        "identity_epoch": identity_binding.get("identity_epoch"),
        "episode_id": identity_binding.get("episode_id"),
        "candidate_generation_id": identity_binding.get("candidate_generation_id"),
        "candidate_state_projection_id": identity_binding.get("candidate_state_projection_id"),
        "authority": dict(ALL_FALSE_AUTHORITY),
    }

    if http_status == 401:
        relation = {
            **base,
            "state": "AUTHENTICATION_REQUIRED",
            "open_position_count": None,
            "position_refs": [],
            "reason": "PORTFOLIO_AUTHENTICATION_REQUIRED",
        }
        validate_terminal_portfolio_relation(relation)
        return relation

    if http_status != 200:
        relation = {
            **base,
            "state": "UNAVAILABLE_DATA",
            "open_position_count": None,
            "position_refs": [],
            "reason": f"PORTFOLIO_OWNER_HTTP_{http_status}",
        }
        validate_terminal_portfolio_relation(relation)
        return relation

    if not isinstance(payload, Mapping):
        raise OpportunityContextContractError("portfolio owner payload must be an object")
    positions = payload.get("positions")
    if not isinstance(positions, list):
        raise OpportunityContextContractError("portfolio owner positions must be a list")

    display_symbol = _text(identity_binding.get("display_symbol"), "display_symbol")
    seen_ids: set[str] = set()
    refs: list[dict[str, str]] = []
    for position in positions:
        if not isinstance(position, Mapping):
            raise OpportunityContextContractError("portfolio owner position must be an object")
        position_id = _text(position.get("id"), "portfolio position id")
        if position_id in seen_ids:
            raise OpportunityContextContractError("portfolio owner returned a duplicate position id")
        seen_ids.add(position_id)
        ticker = _text(position.get("ticker"), "portfolio position ticker")
        if ticker != ticker.strip().upper():
            raise OpportunityContextContractError(
                "portfolio owner ticker is not normalized current-symbol text"
            )
        status = position.get("status")
        if status not in {"open", "closed"}:
            raise OpportunityContextContractError("portfolio owner status is outside open/closed")
        if ticker == display_symbol and status == "open":
            refs.append({"position_id": position_id})

    relation = {
        **base,
        "state": "OPEN_POSITION" if refs else "NO_OPEN_POSITION",
        "open_position_count": len(refs),
        "position_refs": refs,
        "reason": None,
    }
    validate_terminal_portfolio_relation(relation)
    return relation


def validate_terminal_portfolio_relation(payload: Mapping[str, object]) -> None:
    """Validate the minimal private position relation without re-reading the owner."""
    if not isinstance(payload, Mapping):
        raise OpportunityContextContractError("portfolio relation must be an object")
    expected = {
        "schema", "owner", "join_basis", "display_symbol", "security_id",
        "identity_epoch", "episode_id", "candidate_generation_id",
        "candidate_state_projection_id", "state", "open_position_count",
        "position_refs", "reason", "authority",
    }
    if set(payload) != expected:
        raise OpportunityContextContractError("portfolio relation fields are not closed")
    if payload.get("schema") != PORTFOLIO_RELATION_SCHEMA:
        raise OpportunityContextContractError("portfolio relation schema mismatch")
    if payload.get("owner") != "mastermind-terminal:/api/portfolio":
        raise OpportunityContextContractError("portfolio relation owner mismatch")
    if payload.get("join_basis") != "CURRENT_STORE_ALIAS":
        raise OpportunityContextContractError("portfolio relation join basis mismatch")
    for field in (
        "display_symbol", "security_id", "identity_epoch", "episode_id",
        "candidate_generation_id", "candidate_state_projection_id",
    ):
        _text(payload.get(field), f"portfolio relation {field}")
    if payload.get("authority") != ALL_FALSE_AUTHORITY:
        raise OpportunityContextContractError("portfolio relation authority must remain all false")

    state = payload.get("state")
    refs = payload.get("position_refs")
    count = payload.get("open_position_count")
    reason = payload.get("reason")
    if not isinstance(refs, list):
        raise OpportunityContextContractError("portfolio relation position_refs must be a list")
    if any(
        not isinstance(ref, Mapping)
        or set(ref) != {"position_id"}
        or not isinstance(ref.get("position_id"), str)
        or not ref.get("position_id")
        for ref in refs
    ):
        raise OpportunityContextContractError("portfolio relation position ref is malformed")
    ids = [str(ref["position_id"]) for ref in refs]
    if len(ids) != len(set(ids)):
        raise OpportunityContextContractError("portfolio relation position refs are not unique")

    if state == "OPEN_POSITION":
        if type(count) is not int or count < 1 or count != len(refs) or reason is not None:
            raise OpportunityContextContractError("open portfolio relation is incoherent")
    elif state == "NO_OPEN_POSITION":
        if count != 0 or refs or reason is not None:
            raise OpportunityContextContractError("empty portfolio relation is incoherent")
    elif state in {"AUTHENTICATION_REQUIRED", "UNAVAILABLE_DATA"}:
        if count is not None or refs or not isinstance(reason, str) or not reason:
            raise OpportunityContextContractError("unavailable portfolio relation is incoherent")
    else:
        raise OpportunityContextContractError("portfolio relation state is unknown")


def _decision_clock_session(asof: Mapping[str, object]) -> str:
    """Return the calendar session represented by one validated OEV decision clock."""
    value = _text(asof.get("value"), "opportunity evidence asof.value")
    grain = asof.get("grain")
    if grain == "date":
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise OpportunityContextContractError(
                "opportunity evidence date decision clock is invalid"
            ) from exc
        return parsed.isoformat()
    if grain == "datetime":
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise OpportunityContextContractError(
                "opportunity evidence datetime decision clock is invalid"
            ) from exc
        return parsed.date().isoformat()
    raise OpportunityContextContractError("opportunity evidence decision-clock grain is invalid")


def project_opportunity_evidence_summary(
    candidate_projection: Mapping[str, object],
    *,
    episode_id: str,
    evidence_vector: Mapping[str, object],
) -> dict[str, object]:
    """Project already-admitted OEV evidence into one operator-display summary.

    This is a deterministic read of accepted K3-E/OEV output. It does not compose
    evidence, choose a cause, reinterpret admission as entry, or consume OEV's
    legacy entry_availability leg. Fresh-entry authority remains B4.
    """
    if not isinstance(evidence_vector, Mapping):
        raise OpportunityContextContractError("opportunity evidence vector must be an object")
    row = _candidate_row(candidate_projection, _text(episode_id, "episode_id"))

    findings = validate_vector(dict(evidence_vector))
    if findings:
        codes = sorted({
            str(getattr(finding, "code", "K3E_INVALID"))
            for finding in findings
        })
        raise OpportunityContextContractError(
            "opportunity evidence vector failed validation: " + ",".join(codes)
        )

    if evidence_vector.get("schema") != OEV_SCHEMA:
        raise OpportunityContextContractError("opportunity evidence schema mismatch")
    consumers = evidence_vector.get("permitted_consumers")
    if not isinstance(consumers, list) or "operator_display" not in consumers:
        raise OpportunityContextContractError(
            "opportunity evidence vector is not admitted for operator_display"
        )

    subject = evidence_vector.get("subject")
    if not isinstance(subject, Mapping):
        raise OpportunityContextContractError("opportunity evidence subject is unavailable")
    if subject.get("subject_type") != "dataos_security_id":
        raise OpportunityContextContractError(
            "opportunity evidence must use canonical dataos_security_id for this join"
        )
    if subject.get("value") != row.get("security_id"):
        raise OpportunityContextContractError(
            "opportunity evidence subject does not match the selected B3 security"
        )
    if subject.get("identity_state") == "unproven":
        raise OpportunityContextContractError(
            "opportunity evidence identity is unproven for operator display"
        )

    market_session = _text(
        candidate_projection.get("market_session"),
        "candidate projection market_session",
    )
    asof = evidence_vector.get("asof")
    if not isinstance(asof, Mapping) or _decision_clock_session(asof) != market_session:
        raise OpportunityContextContractError(
            "opportunity evidence decision clock does not match the B3 market session"
        )

    projection = evidence_vector.get("projection")
    slots = evidence_vector.get("slots")
    if not isinstance(projection, Mapping) or not isinstance(slots, list):
        raise OpportunityContextContractError("opportunity evidence projection is unavailable")
    slots_by_construct = {
        slot.get("construct"): slot
        for slot in slots
        if isinstance(slot, Mapping) and isinstance(slot.get("construct"), str)
    }

    def _slots_for(leg_name: str) -> list[dict[str, object]]:
        leg = projection.get(leg_name)
        if not isinstance(leg, Mapping):
            raise OpportunityContextContractError(
                f"opportunity evidence {leg_name} leg is unavailable"
            )
        refs = leg.get("slot_refs")
        if not isinstance(refs, list):
            raise OpportunityContextContractError(
                f"opportunity evidence {leg_name} refs are unavailable"
            )
        out: list[dict[str, object]] = []
        for ref in refs:
            slot = slots_by_construct.get(ref)
            if not isinstance(slot, Mapping):
                raise OpportunityContextContractError(
                    f"opportunity evidence {leg_name} references an unknown slot"
                )
            out.append(deepcopy(dict(slot)))
        return out

    gates_leg = projection.get("failed_or_unavailable_gates")
    if not isinstance(gates_leg, Mapping) or not isinstance(gates_leg.get("gates"), list):
        raise OpportunityContextContractError(
            "opportunity evidence failed/unavailable gates are unavailable"
        )
    gates = gates_leg["gates"]
    failed = [deepcopy(dict(g)) for g in gates if isinstance(g, Mapping) and g.get("state") == "failed"]
    unavailable = [
        deepcopy(dict(g))
        for g in gates
        if isinstance(g, Mapping) and g.get("state") in {"unavailable", "not_evaluated"}
    ]

    summary = {
        "status": "JOINED",
        "source": {
            "schema": evidence_vector.get("schema"),
            "content_sha256": evidence_vector.get("content_sha256"),
            "security_id": row.get("security_id"),
            "market_session": market_session,
            "asof": deepcopy(dict(asof)),
            "generated_at": evidence_vector.get("generated_at"),
            "compilation_state": evidence_vector.get("compilation_state"),
            "dominant_degradation": evidence_vector.get("dominant_degradation"),
        },
        "owner_evidence": {
            "observed_slots": _slots_for("observed"),
            "inferred_slots": _slots_for("inferred"),
            "market_reflection": deepcopy(projection.get("market_reflection")),
        },
        "support": {
            "state": "UNAVAILABLE",
            "facts": None,
            "reason": "DIRECTIONAL_SUPPORT_NOT_ADMITTED",
        },
        "contradiction": {
            "failed_owner_gates": failed,
        },
        "unresolved": {
            "strongest_unresolved_fact": deepcopy(
                projection.get("strongest_unresolved_fact")
            ),
            "unavailable_owner_gates": unavailable,
        },
        "next_observable": deepcopy(projection.get("next_observable")),
        "reason": None,
    }
    validate_opportunity_evidence_summary(summary, identity_security_id=row.get("security_id"),
                                         market_session=market_session)
    return summary


def validate_opportunity_evidence_summary(
    payload: Mapping[str, object],
    *,
    identity_security_id: object,
    market_session: object,
) -> None:
    """Validate the closed display summary without reinterpreting OEV semantics."""
    if not isinstance(payload, Mapping):
        raise OpportunityContextContractError("opportunity evidence summary must be an object")
    expected = {
        "status", "source", "owner_evidence", "support", "contradiction",
        "unresolved", "next_observable", "reason",
    }
    if set(payload) != expected or payload.get("status") != "JOINED" or payload.get("reason") is not None:
        raise OpportunityContextContractError("joined opportunity evidence summary is incoherent")

    source = payload.get("source")
    if not isinstance(source, Mapping) or set(source) != {
        "schema", "content_sha256", "security_id", "market_session", "asof",
        "generated_at", "compilation_state", "dominant_degradation",
    }:
        raise OpportunityContextContractError("opportunity evidence source block is not closed")
    if source.get("schema") != OEV_SCHEMA:
        raise OpportunityContextContractError("opportunity evidence source schema mismatch")
    digest = source.get("content_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        raise OpportunityContextContractError("opportunity evidence content digest is malformed")
    if source.get("security_id") != identity_security_id:
        raise OpportunityContextContractError(
            "opportunity evidence source security does not match opportunity identity"
        )
    if source.get("market_session") != market_session:
        raise OpportunityContextContractError(
            "opportunity evidence source session does not match opportunity decision clock"
        )
    if not isinstance(source.get("asof"), Mapping):
        raise OpportunityContextContractError("opportunity evidence source asof is unavailable")
    if _decision_clock_session(source["asof"]) != market_session:
        raise OpportunityContextContractError(
            "opportunity evidence source asof does not match opportunity decision clock"
        )
    _text(source.get("generated_at"), "opportunity evidence generated_at")
    _text(source.get("compilation_state"), "opportunity evidence compilation_state")
    _text(source.get("dominant_degradation"), "opportunity evidence dominant_degradation")

    owner_evidence = payload.get("owner_evidence")
    if not isinstance(owner_evidence, Mapping) or set(owner_evidence) != {
        "observed_slots", "inferred_slots", "market_reflection",
    }:
        raise OpportunityContextContractError("opportunity evidence owner-evidence block is not closed")
    if (
        not isinstance(owner_evidence.get("observed_slots"), list)
        or not isinstance(owner_evidence.get("inferred_slots"), list)
    ):
        raise OpportunityContextContractError("opportunity evidence owner slot lists are unavailable")
    if not isinstance(owner_evidence.get("market_reflection"), Mapping):
        raise OpportunityContextContractError("opportunity evidence market reflection is unavailable")

    support = payload.get("support")
    if not isinstance(support, Mapping) or support != {
        "state": "UNAVAILABLE",
        "facts": None,
        "reason": "DIRECTIONAL_SUPPORT_NOT_ADMITTED",
    }:
        raise OpportunityContextContractError(
            "directional support must remain unavailable until an owner admits it"
        )

    contradiction = payload.get("contradiction")
    if not isinstance(contradiction, Mapping) or set(contradiction) != {"failed_owner_gates"}:
        raise OpportunityContextContractError("opportunity evidence contradiction block is not closed")
    if not isinstance(contradiction.get("failed_owner_gates"), list):
        raise OpportunityContextContractError("opportunity evidence failed-owner gates are unavailable")

    unresolved = payload.get("unresolved")
    if not isinstance(unresolved, Mapping) or set(unresolved) != {
        "strongest_unresolved_fact", "unavailable_owner_gates",
    }:
        raise OpportunityContextContractError("opportunity evidence unresolved block is not closed")
    if not isinstance(unresolved.get("strongest_unresolved_fact"), Mapping):
        raise OpportunityContextContractError("opportunity evidence strongest unresolved fact is unavailable")
    if not isinstance(unresolved.get("unavailable_owner_gates"), list):
        raise OpportunityContextContractError("opportunity evidence unavailable gates are unavailable")
    if not isinstance(payload.get("next_observable"), Mapping):
        raise OpportunityContextContractError("opportunity evidence next observable is unavailable")


def compose_opportunity_context(
    candidate_projection: Mapping[str, object],
    *,
    episode_id: str,
    entry_availability: Mapping[str, object] | None = None,
    portfolio_relation: Mapping[str, object] | None = None,
    opportunity_evidence: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compose one zero-authority, identity-bound Prophet opportunity context.

    ``entry_availability`` is optional because the current native B4 runtime may
    truthfully be dark. When absent, the output retains ``UNAVAILABLE_DATA`` and
    ``entry_open=None`` rather than manufacturing a local permission verdict.
    """
    if not isinstance(candidate_projection, Mapping):
        raise OpportunityContextContractError("candidate_projection must be an object")
    episode_id = _text(episode_id, "episode_id")
    row = _candidate_row(candidate_projection, episode_id)

    entry = (
        _unavailable_entry(row)
        if entry_availability is None
        else _bound_entry(candidate_projection, row, entry_availability)
    )

    user_state = deepcopy(_UNJOINED_USER_STATE)
    if portfolio_relation is not None:
        validate_terminal_portfolio_relation(portfolio_relation)
        bindings = {
            "security_id": row.get("security_id"),
            "identity_epoch": row.get("identity_epoch"),
            "episode_id": row.get("episode_id"),
            "candidate_generation_id": candidate_projection.get("candidate_generation_id"),
            "candidate_state_projection_id": candidate_projection.get("projection_id"),
        }
        for field, expected in bindings.items():
            if portfolio_relation.get(field) != expected:
                raise OpportunityContextContractError(
                    f"portfolio relation {field} does not match the selected B3 identity"
                )
        user_state["portfolio"] = {
            "state": "JOINED",
            "relation": deepcopy(dict(portfolio_relation)),
            "reason": None,
        }

    evidence_summary = (
        deepcopy(_UNJOINED_EVIDENCE)
        if opportunity_evidence is None
        else project_opportunity_evidence_summary(
            candidate_projection,
            episode_id=episode_id,
            evidence_vector=opportunity_evidence,
        )
    )

    out: dict[str, object] = {
        "schema": SCHEMA,
        "identity": {
            "episode_id": row.get("episode_id"),
            "security_id": row.get("security_id"),
            "company_id": row.get("company_id"),
            "identity_epoch": row.get("identity_epoch"),
            "candidate_generation_id": candidate_projection.get("candidate_generation_id"),
            "candidate_state_projection_id": candidate_projection.get("projection_id"),
        },
        "decision_clock": {
            "market_session": candidate_projection.get("market_session"),
            "candidate_state_generated_at": candidate_projection.get("generated_at"),
        },
        "native_phase": {
            "episode_lifecycle": deepcopy(row.get("episode_lifecycle")),
            "emergence_state": deepcopy(row.get("emergence_state")),
            "maturity_state": deepcopy(row.get("maturity_state")),
        },
        "fresh_entry": entry,
        "user_state": user_state,
        "evidence_summary": evidence_summary,
        "forecast": deepcopy(_UNQUALIFIED_FORECAST),
        "authority": dict(ALL_FALSE_AUTHORITY),
    }
    validate_opportunity_context(out)
    return out


def validate_opportunity_context(payload: Mapping[str, object]) -> None:
    """Validate the closed presentation contract without re-deriving owner truth."""
    if not isinstance(payload, Mapping):
        raise OpportunityContextContractError("opportunity context must be an object")
    expected = {
        "schema", "identity", "decision_clock", "native_phase", "fresh_entry",
        "user_state", "evidence_summary", "forecast", "authority",
    }
    if set(payload) != expected:
        raise OpportunityContextContractError("opportunity context fields are not closed")
    if payload.get("schema") != SCHEMA:
        raise OpportunityContextContractError("opportunity context schema mismatch")
    if payload.get("authority") != ALL_FALSE_AUTHORITY:
        raise OpportunityContextContractError("Prophet Lab authority must remain all false")

    identity = payload.get("identity")
    if not isinstance(identity, Mapping) or set(identity) != {
        "episode_id", "security_id", "company_id", "identity_epoch",
        "candidate_generation_id", "candidate_state_projection_id",
    }:
        raise OpportunityContextContractError("identity block is not closed")
    for field in identity:
        _text(identity.get(field), f"identity.{field}")

    clock = payload.get("decision_clock")
    if not isinstance(clock, Mapping) or set(clock) != {
        "market_session", "candidate_state_generated_at",
    }:
        raise OpportunityContextContractError("decision_clock block is not closed")
    _text(clock.get("market_session"), "decision_clock.market_session")
    _text(clock.get("candidate_state_generated_at"), "decision_clock.candidate_state_generated_at")

    phase = payload.get("native_phase")
    if not isinstance(phase, Mapping) or set(phase) != {
        "episode_lifecycle", "emergence_state", "maturity_state",
    }:
        raise OpportunityContextContractError("native_phase block is not closed")

    entry = payload.get("fresh_entry")
    if not isinstance(entry, Mapping) or set(entry) != {
        "owner_schema", "state", "entry_open", "reason", "availability_id",
        "evaluated_at", "market_session", "strategy", "current_price", "zone",
        "invalidation", "chase_state", "owner_status", "blockers", "reasons",
        "source_receipts",
    }:
        raise OpportunityContextContractError("fresh_entry block is not closed")
    if entry.get("owner_schema") != B4_SCHEMA:
        raise OpportunityContextContractError("fresh_entry owner schema mismatch")
    if entry.get("state") == "UNAVAILABLE_DATA" and entry.get("availability_id") is None:
        if entry.get("entry_open") is not None or entry.get("reason") != "B4_NOT_AVAILABLE":
            raise OpportunityContextContractError(
                "missing B4 must remain unknown rather than a false verdict"
            )
    elif entry.get("entry_open") not in (True, False):
        raise OpportunityContextContractError("owner-issued B4 entry_open must be boolean")

    user_state = payload.get("user_state")
    if not isinstance(user_state, Mapping) or set(user_state) != {"plan", "watchlist", "portfolio"}:
        raise OpportunityContextContractError("private user state fields are not closed")
    if user_state.get("plan") != _UNJOINED_USER_STATE["plan"]:
        raise OpportunityContextContractError("private Plan state must remain owner-controlled")
    if user_state.get("watchlist") != _UNJOINED_USER_STATE["watchlist"]:
        raise OpportunityContextContractError("watchlist state must remain unjoined")
    portfolio_state = user_state.get("portfolio")
    if portfolio_state == _UNJOINED_USER_STATE["portfolio"]:
        pass
    elif (
        isinstance(portfolio_state, Mapping)
        and set(portfolio_state) == {"state", "relation", "reason"}
        and portfolio_state.get("state") == "JOINED"
        and portfolio_state.get("reason") is None
        and isinstance(portfolio_state.get("relation"), Mapping)
    ):
        validate_terminal_portfolio_relation(portfolio_state["relation"])
        relation = portfolio_state["relation"]
        for field in (
            "security_id", "identity_epoch", "episode_id",
            "candidate_generation_id", "candidate_state_projection_id",
        ):
            if relation.get(field) != identity.get(field):
                raise OpportunityContextContractError(
                    f"portfolio relation {field} does not match opportunity identity"
                )
    else:
        raise OpportunityContextContractError("private portfolio state is incoherent")
    evidence_summary = payload.get("evidence_summary")
    if evidence_summary == _UNJOINED_EVIDENCE:
        pass
    elif isinstance(evidence_summary, Mapping):
        validate_opportunity_evidence_summary(
            evidence_summary,
            identity_security_id=identity.get("security_id"),
            market_session=clock.get("market_session"),
        )
    else:
        raise OpportunityContextContractError("cross-domain evidence state is incoherent")
    if payload.get("forecast") != _UNQUALIFIED_FORECAST:
        raise OpportunityContextContractError("unqualified forecast must remain null")


__all__ = [
    "SCHEMA",
    "OpportunityContextContractError",
    "compose_opportunity_context",
    "project_opportunity_evidence_summary",
    "project_terminal_portfolio_relation",
    "resolve_display_alias_to_active_episode",
    "select_unique_active_episode_id",
    "validate_opportunity_context",
    "validate_opportunity_evidence_summary",
    "validate_opportunity_identity_binding",
    "validate_terminal_portfolio_relation",
]
