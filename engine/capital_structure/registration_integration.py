"""Registration-path integration of accepted inputs into distinct path predicates (L1a).

Capital Structure Intelligence V2, masterplan task L1 (DAG row L1a).  This module
adds no extraction, collector, resolver or network call: it reads the sealed
registration lifecycle compiler's output and the L0 rule-applicability pack, and
re-proves the registration-path boundary on every record it hands on.

* Every predicate stays DISTINCT -- original filing, observed EFFECT, automatic
  shelf form, automatic effectiveness, offering role, withdrawal, replacement and
  the Rule 415(a)(5) shelf window.  None of them alone, and no combination of
  them, is a capacity fact: an effectiveness notice is not an executable
  offering, an ``S-3ASR`` form token is not WKSI status, and a shelf window is a
  date bound on a rule, never a remaining dollar amount (A10, A20).
* Valid time (SEC acceptance) and house knowledge (``mastermind_available_at``)
  stay separate on every interval, so a caller can ask what was true at a date
  and what Mastermind knew at a date and get two different answers (A11).
* ``offering_role`` and ``replaced`` stay unknown: primary versus resale is
  accepted-content evidence the lifecycle deliberately does not carry, and
  Rule 415(a)(6) carry-forward rows are fee-table rows, not a document term.  A
  ``supersedes`` edge is event-version supersession, never a replacement.
* A rule answers for a date only through the L0 pack.  A rule id the pack does
  not carry is missing text, answered ``unknown`` with a named reason -- never
  guessed, never treated as 0 and never treated as infinity (A20).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from types import MappingProxyType
from typing import Any

from engine.capital_structure import registration_lifecycle
from engine.capital_structure.issuer_state_contracts import (
    FORBIDDEN_PROPERTY_PATTERN,
    CalculationReceipt,
    CapitalInputs,
    FamilyProvenance,
    FamilyState,
    GenerationBinding,
    sha256_of,
    stable_id,
)
from engine.capital_structure.registration_lifecycle import (
    BUNDLE_SCHEMA,
    compile_registration_lifecycles,
    validate_registration_lifecycle_bundle,
)
from engine.capital_structure.rule_applicability import (
    RuleApplicabilityError,
    RuleApplicabilityPack,
    rule_status_as_of,
)

REGISTRATION_INTEGRATION_VERSION = "capital-structure-registration-integration/1.0.0"
REGISTRATION_PATH_SCHEMA = "capital_structure.registration_path.v1"
REGISTRATION_FAMILY = "registration"
EVENTS_FAMILY = "events"
EVENT_EDGES_FAMILY = "event_edges"
LIFECYCLE_FAMILY = "registration_lifecycle"
EVENT_SCHEMA = "capital_structure.event.v1"
SUPPORTED_STATES = ("supported", "partial")
RULE_QUALIFIED_STATES = ("verified", "bracketed")

#: Predicate answers, closed.  ``unknown`` is never 0 and never infinity (A20).
PREDICATE_STATUSES = ("observed", "not_observed", "unknown", "not_applicable", "conditional")

#: The offering-role vocabulary.  v1 only ever answers the last member: the
#: lifecycle carries no accepted primary/resale classification and a form type
#: never implies one (A10, A23).
OFFERING_ROLES = ("primary", "resale", "mixed", "unknown")

#: Registration families Rule 415(a)(5) can bound with a three-year window.
SHELF_FAMILIES = frozenset({"registration_s3", "registration_f3", "registration_f10"})

#: Form tokens that are automatic shelf registration statements or their
#: post-effective amendments.  A form token is a form fact, never WKSI status.
AUTOMATIC_SHELF_FORMS = frozenset({"S-3ASR", "F-3ASR", "POSASR"})

RULE_415_A_5 = "cfr.17.230.415.a.5"
RULE_415_A_6 = "cfr.17.230.415.a.6"
RULE_462_E = "cfr.17.230.462.e"

#: Rule ids this module looks up.  They are the receipt's rule digest domain, so
#: a pack that gains one changes the receipt.
RULES_CONSULTED = (RULE_415_A_5, RULE_415_A_6, RULE_462_E)

#: Conditions every conditional shelf window carries: what was NOT evaluated and
#: where the window's start date came from.
SHELF_WINDOW_CONDITIONS = (
    "securities_registered_under_rule_415_a_1_x_or_automatic_shelf_not_verified",
    "rule_415_a_5_ii_continuation_after_new_filing_not_evaluated",
    "rule_415_a_6_carry_forward_not_evaluated",
    "effective_date_taken_from_effect_notice_acceptance",
)

#: Added when the window's start is the origin filing date of an automatic shelf
#: registration statement whose Rule 462(e) effectiveness is itself conditional.
WKSI_CONDITION = "wksi_status_not_evaluated"

SHELF_WINDOW_POSITIONS = ("inside_window", "after_window_end")

#: The only authority block a registration path may carry.  Byte-for-byte the
#: closed T0 candidate block: context only, every instrument/capacity/risk/
#: probability/rank/sizing/entry/trade/prophet authority denied.
AUTHORITY: Mapping[str, bool] = MappingProxyType({
    "is_context_only": True,
    "instrument_authority": False,
    "capacity_authority": False,
    "risk_authority": False,
    "probability_authority": False,
    "rank_authority": False,
    "sizing_authority": False,
    "entry_authority": False,
    "trade_authority": False,
    "prophet_authority": False,
})

#: What a registration path can never answer.  The lifecycle's own firewall plus
#: the four facts L1a additionally refuses to infer.
UNAVAILABLE = tuple(sorted({
    *registration_lifecycle.UNAVAILABLE,
    "automatic_effectiveness_without_wksi_determination",
    "wksi_eligibility",
    "replacement_carry_forward_classification",
    "exchange_public_offering_treatment",
    "registered_amount_remaining",
}))

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


class RegistrationIntegrationRefusal(ValueError):
    """An input would breach the registration-path boundary or its source law."""


def _instant(value: Any, field: str) -> datetime:
    """Parse an ISO-8601 timestamp with a timezone into aware UTC."""
    if not isinstance(value, str) or not value.strip():
        raise RegistrationIntegrationRefusal(f"{field}: ISO-8601 timestamp required, got {value!r}")
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
    except ValueError as exc:
        raise RegistrationIntegrationRefusal(f"{field}: {raw!r} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise RegistrationIntegrationRefusal(f"{field}: timestamp must carry a timezone")
    return parsed.astimezone(timezone.utc)


def _iso_z(value: Any, field: str) -> str:
    """The lifecycle compiler's own normalized form of a timestamp."""
    return _instant(value, field).isoformat().replace("+00:00", "Z")


def _day_of(value: Any, field: str) -> date:
    return _instant(value, field).date()


def _plus_three_years(day: date) -> date:
    """Three calendar years on, clamping a Feb-29 start to Feb-28."""
    try:
        return day.replace(year=day.year + 3)
    except ValueError:
        return day.replace(year=day.year + 3, month=2, day=28)


def _usable(binding: GenerationBinding | None) -> bool:
    return binding is not None and binding.support in SUPPORTED_STATES


def _source_generation(binding: GenerationBinding | None) -> Mapping[str, Any] | None:
    """Upstream generation for the lifecycle compiler's source receipt.

    ``compile_registration_lifecycles`` takes a *mapping* -- ``generation_id``,
    ``as_of``, ``status`` and ``artifact_hashes`` -- and ``status="ok"`` requires
    a 64-hex artifact hash for each of ``event_versions`` and ``event_edges``.
    A C0 :class:`GenerationBinding` carries at most one ``artifact_sha256`` and
    no per-artifact hashes, so it can never lawfully express a verified upstream
    generation, and inventing the two hashes would fabricate an upstream binding
    this module did not observe.  The compile is therefore left unbound (the
    compiler's own ``unbound_engine_input`` receipt state) and the binding is
    carried by the calculation receipt instead.
    """
    return None


def _rule_absent(pack: Any, rule_id: str) -> bool:
    """True when the pack carries no text for ``rule_id`` (or there is no pack)."""
    if pack is None:
        return True
    try:
        pack.rule(rule_id)
    except RuleApplicabilityError:
        return True
    return False


def _rule_state(pack: Any, rule_id: str, day: date) -> str | None:
    """L0 as-of state of ``rule_id`` on ``day``; ``None`` when the text is absent."""
    if _rule_absent(pack, rule_id):
        return None
    return str(rule_status_as_of(pack, rule_id, day.isoformat()).state)


def _rule_digest(pack: Any) -> str:
    """Digest of the rule ids and windows this run could consult."""
    if pack is None:
        return sha256_of("no_rule_pack")
    used: dict[str, Any] = {}
    for rule_id in RULES_CONSULTED:
        if _rule_absent(pack, rule_id):
            used[rule_id] = None
            continue
        rule = pack.rule(rule_id)
        used[rule_id] = [
            {"kind": window.kind, "start": window.start, "end": window.end, "sha256": window.sha256}
            for window in rule.windows
        ]
    return sha256_of({
        "registration_integration": REGISTRATION_INTEGRATION_VERSION,
        "path_schema": REGISTRATION_PATH_SCHEMA,
        "rule_pack_version": getattr(pack, "version", None),
        "rules_consulted": used,
    })


def _evidence(items: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    return (
        [str(item["event_id"]) for item in items],
        [str(item["accession"]) for item in items if item.get("accession")],
    )


def _predicate(
    status: str,
    reason: str,
    *,
    evidence: Sequence[Mapping[str, Any]] = (),
    rule_ids: Sequence[str] = (),
    **extra: Any,
) -> dict[str, Any]:
    """One closed predicate: a status, its evidence, its reason and its rules."""
    if status not in PREDICATE_STATUSES:
        raise RegistrationIntegrationRefusal(f"predicate status {status!r} is not in {list(PREDICATE_STATUSES)}")
    if not isinstance(reason, str) or not _SNAKE_CASE.match(reason):
        raise RegistrationIntegrationRefusal(f"predicate reason {reason!r} is not a snake_case string")
    event_ids, accessions = _evidence(list(evidence))
    body: dict[str, Any] = {
        "status": status,
        "evidence_event_ids": event_ids,
        "evidence_accessions": accessions,
        "reason": reason,
        "rule_ids": [str(rule_id) for rule_id in rule_ids],
    }
    for key, value in extra.items():
        if FORBIDDEN_PROPERTY_PATTERN.match(key):
            raise RegistrationIntegrationRefusal(f"predicate key {key!r} is a forbidden property name")
        body[key] = value
    return body


def _automatic_effectiveness(
    origin: Mapping[str, Any],
    automatic_shelf_form: Mapping[str, Any],
    pack: Any,
) -> dict[str, Any]:
    """Rule 462(e) effectiveness of an automatic shelf form -- never WKSI status."""
    if automatic_shelf_form["status"] != "observed":
        return _predicate("not_applicable", "no_automatic_shelf_form_observed")
    filing_day = _day_of(origin["sec_accepted_at"], "origin.sec_accepted_at")
    if _rule_state(pack, RULE_462_E, filing_day) in RULE_QUALIFIED_STATES:
        return _predicate(
            "conditional",
            "rule_462_e_effective_on_filing_if_wksi_at_determination_date_wksi_not_evaluated",
            evidence=[origin],
            rule_ids=[RULE_462_E],
        )
    return _predicate("unknown", "rule_462_e_text_not_in_rule_pack", evidence=[origin])


def _shelf_window(
    record: Mapping[str, Any],
    timeline: Sequence[Mapping[str, Any]],
    origin: Mapping[str, Any],
    effect_items: Sequence[Mapping[str, Any]],
    automatic_shelf_form: Mapping[str, Any],
    automatic_effectiveness: Mapping[str, Any],
    *,
    as_of: str,
    pack: Any,
) -> dict[str, Any]:
    """The Rule 415(a)(5) three-year window: a date bound, never an amount."""
    family = str((record.get("registration") or {}).get("registration_family") or "")
    if family not in SHELF_FAMILIES:
        return _predicate("not_applicable", "registration_family_not_a_shelf_family")

    start_item: Mapping[str, Any] | None = None
    extra_conditions: tuple[str, ...] = ()
    if effect_items:
        start_item = min(
            effect_items,
            key=lambda item: _instant(item["sec_accepted_at"], "timeline.sec_accepted_at"),
        )
    elif automatic_shelf_form["status"] == "observed" and automatic_effectiveness["status"] == "conditional":
        start_item = origin
        extra_conditions = (WKSI_CONDITION,)
    evidence = [start_item] if start_item is not None else []

    if _rule_absent(pack, RULE_415_A_5):
        return _predicate("unknown", "rule_415_a_5_text_not_in_rule_pack", evidence=evidence)
    if start_item is None:
        return _predicate("unknown", "initial_effectiveness_not_observed")
    start_day = _day_of(start_item["sec_accepted_at"], "timeline.sec_accepted_at")
    if _rule_state(pack, RULE_415_A_5, start_day) not in RULE_QUALIFIED_STATES:
        return _predicate("unknown", "rule_415_a_5_text_not_in_rule_pack", evidence=evidence)

    window_end = _plus_three_years(start_day)
    position = "inside_window" if _day_of(as_of, "as_of") < window_end else "after_window_end"
    if position not in SHELF_WINDOW_POSITIONS:  # pragma: no cover - closed by construction
        raise RegistrationIntegrationRefusal(f"shelf window position {position!r} is not closed")
    return _predicate(
        "conditional",
        "rule_415_a_5_window_conditional_on_unverified_requirements",
        evidence=evidence,
        rule_ids=[RULE_415_A_5],
        window_start=start_day.isoformat(),
        window_end=window_end.isoformat(),
        position=position,
        conditions=[*SHELF_WINDOW_CONDITIONS, *extra_conditions],
    )


def _intervals(timeline: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Valid time and house knowledge, kept apart on every interval."""
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(timeline):
        following = timeline[index + 1] if index + 1 < len(timeline) else None
        rows.append({
            "state": item["state_after_event"],
            "transition": item["transition"],
            "event_id": item["event_id"],
            "accession": item["accession"],
            "form": item["form"],
            "valid_from": item["sec_accepted_at"],
            "valid_to": following["sec_accepted_at"] if following is not None else None,
            "known_from": item["mastermind_available_at"],
            "valid_to_known_from": following["mastermind_available_at"] if following is not None else None,
        })
    return rows


def _origin_record(origin: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": origin["event_id"],
        "accession": origin["accession"],
        "form": origin["form"],
        "sec_accepted_at": origin["sec_accepted_at"],
        "mastermind_available_at": origin["mastermind_available_at"],
    }


def _amendment_chain(timeline: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": item["event_id"],
            "accession": item["accession"],
            "form": item["form"],
            "sec_accepted_at": item["sec_accepted_at"],
            "mastermind_available_at": item["mastermind_available_at"],
            "correction_version": item["correction_version"],
            "relationship": deepcopy(item["relationship"]),
        }
        for item in timeline
        if item["transition"] == "amended"
    ]


def _path_record(
    record: Mapping[str, Any],
    *,
    lifecycle_generation_id: str | None,
    as_of: str,
    pack: Any,
) -> dict[str, Any]:
    """One registration path: the lifecycle record plus its distinct predicates."""
    timeline = [dict(item) for item in record["timeline"]]
    if not timeline:  # pragma: no cover - the lifecycle validator refuses an empty timeline
        raise RegistrationIntegrationRefusal(f"lifecycle {record.get('lifecycle_id')!r} carries an empty timeline")
    origin = timeline[0]
    filed_items = [item for item in timeline if item["transition"] == "filed"]
    effect_items = [item for item in timeline if item["transition"] == "effective"]
    withdrawn_items = [item for item in timeline if item["transition"] == "withdrawn"]
    automatic_items = [item for item in timeline if item["form"] in AUTOMATIC_SHELF_FORMS]

    filed = _predicate(
        "observed" if filed_items else "unknown",
        "original_registration_filing_observed" if filed_items else "original_registration_filing_not_visible",
        evidence=filed_items,
    )
    effect_observed = _predicate(
        "observed" if effect_items else "not_observed",
        "effect_notice_observed" if effect_items else "no_effect_notice_visible_absence_is_not_non_effectiveness",
        evidence=effect_items,
    )
    automatic_shelf_form = _predicate(
        "observed" if automatic_items else "not_observed",
        "form_fact_only_not_wksi_status",
        evidence=automatic_items,
    )
    automatic_effectiveness = _automatic_effectiveness(origin, automatic_shelf_form, pack)
    offering_role = _predicate(
        "unknown",
        "no_accepted_content_evidence_lifecycle_carries_no_primary_or_resale_classification",
        value="unknown",
    )
    if offering_role["value"] not in OFFERING_ROLES:  # pragma: no cover - closed by construction
        raise RegistrationIntegrationRefusal(f"offering role {offering_role['value']!r} is not closed")
    withdrawn = _predicate(
        "observed" if withdrawn_items else "not_observed",
        "withdrawal_observed" if withdrawn_items else "no_withdrawal_observed",
        evidence=withdrawn_items,
    )
    replaced = _predicate("unknown", "rule_415_a_6_carry_forward_rows_not_extracted")
    shelf_window = _shelf_window(
        record, timeline, origin, effect_items, automatic_shelf_form, automatic_effectiveness,
        as_of=as_of, pack=pack,
    )

    timeline_event_ids = [str(item["event_id"]) for item in timeline]
    return {
        "schema": REGISTRATION_PATH_SCHEMA,
        "path_id": stable_id("registration-path", {
            "lifecycle_id": record["lifecycle_id"],
            "timeline_event_ids": timeline_event_ids,
            "as_of": as_of,
        }),
        "lifecycle_id": record["lifecycle_id"],
        "lifecycle_generation_id": lifecycle_generation_id,
        "as_of": as_of,
        "issuer": deepcopy(record["issuer"]),
        "registration": deepcopy(record["registration"]),
        "origin": _origin_record(origin),
        "amendment_chain": _amendment_chain(timeline),
        "intervals": _intervals(timeline),
        "observed_registration_state": record["observed_registration_state"],
        "predicates": {
            "filed": filed,
            "effect_observed": effect_observed,
            "automatic_shelf_form": automatic_shelf_form,
            "automatic_effectiveness": automatic_effectiveness,
            "offering_role": offering_role,
            "withdrawn": withdrawn,
            "replaced": replaced,
            "shelf_window": shelf_window,
        },
        "coverage": deepcopy(record["coverage"]),
        "unavailable": list(UNAVAILABLE),
        "authority": dict(AUTHORITY),
    }


def _support_limits(*, coverage_state: str, pack: Any) -> tuple[str, ...]:
    """Named limits of a partial registration family; never an empty set."""
    limits = {"offering_role_unknown", "replacement_not_extracted"}
    if coverage_state == "partial":
        limits.add("lifecycle_coverage_partial")
    elif coverage_state == "unavailable":
        limits.add("lifecycle_coverage_unavailable")
    for rule_id in RULES_CONSULTED:
        if _rule_absent(pack, rule_id):
            limits.add(f"rule_text_not_in_pack:{rule_id}")
    for gap_id, gap in sorted((getattr(pack, "gaps", None) or {}).items()):
        if str((gap or {}).get("status") or "inherited") == "open":
            limits.add(f"rule_pack_gap:{gap_id}")
    return tuple(sorted(limits))


def _paths_from_bundle(
    bundle: Mapping[str, Any],
    *,
    as_of: str,
    pack: Any,
) -> tuple[dict[str, Any], ...]:
    generation_id = bundle.get("generation_id")
    return tuple(
        _path_record(
            record,
            lifecycle_generation_id=str(generation_id) if generation_id is not None else None,
            as_of=as_of,
            pack=pack,
        )
        for record in bundle["records"]
    )


def _validate_precompiled(bundle: Mapping[str, Any], as_of: str) -> None:
    try:
        validate_registration_lifecycle_bundle(bundle)
    except ValueError as exc:
        raise RegistrationIntegrationRefusal(f"precompiled registration lifecycle bundle is invalid: {exc}") from exc
    if str(bundle.get("as_of") or "") != as_of:
        raise RegistrationIntegrationRefusal(
            "a precompiled lifecycle bundle cannot be re-cut to another house-knowledge cutoff; "
            f"bind events+edges (bundle as_of {bundle.get('as_of')!r} != requested {as_of!r})"
        )


@dataclass(frozen=True)
class RegistrationIntegration:
    """Registration paths compiled from one accepted input generation.

    ``paths`` carries one record per lifecycle record; ``deferred`` is the
    lifecycle compiler's own defer ledger passed through unchanged.  When the
    source family is not supported nothing was verified, so both are empty and
    ``support`` says why -- callers must never persist ``paths`` from such an
    integration over an existing ledger.
    """

    paths: tuple[dict[str, Any], ...]
    deferred: tuple[dict[str, Any], ...]
    receipt: CalculationReceipt
    support: str
    support_limits: tuple[str, ...]
    source_family: str
    source_schema: str | None
    source_generation_id: str | None
    source_artifact_sha256: str | None
    as_of: str
    generated_at: str

    def family_state(self) -> FamilyState:
        """The ``registration`` twin family of the frozen state contract."""
        provenance = FamilyProvenance(
            family=REGISTRATION_FAMILY,
            input_family=self.source_family,
            input_schema=self.source_schema,
            support=self.support,
            compiler_version=REGISTRATION_INTEGRATION_VERSION,
            generation_id=self.source_generation_id,
            artifact_sha256=self.source_artifact_sha256,
            support_limits=self.support_limits,
            as_of=self.as_of,
        )
        return FamilyState(
            family=REGISTRATION_FAMILY,
            provenance=provenance,
            records=tuple(deepcopy(dict(row)) for row in self.paths),
            unavailable=UNAVAILABLE,
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "version": REGISTRATION_INTEGRATION_VERSION,
            "schema": REGISTRATION_PATH_SCHEMA,
            "as_of": self.as_of,
            "generated_at": self.generated_at,
            "support": self.support,
            "support_limits": list(self.support_limits),
            "source_family": self.source_family,
            "source_schema": self.source_schema,
            "source_generation_id": self.source_generation_id,
            "source_artifact_sha256": self.source_artifact_sha256,
            "counts": {"registration_paths": len(self.paths), "deferred": len(self.deferred)},
            "path_ids": [row["path_id"] for row in self.paths],
            "deferred_ids": [row["defer_id"] for row in self.deferred],
            "provenance": self.family_state().provenance.as_record(),
            "receipt": self.receipt.as_record(),
        }


def registration_path_at(path: Mapping[str, Any], valid_at: str) -> dict[str, Any] | None:
    """The interval of ``path`` in force at ``valid_at`` (SEC acceptance time).

    ``valid_from <= valid_at < valid_to``, an absent ``valid_to`` being open.
    Returns ``None`` before the origin filing: absence of a path is not a fact
    about the registration.
    """
    if not isinstance(path, Mapping):
        raise RegistrationIntegrationRefusal("path must be a registration path record")
    moment = _instant(valid_at, "valid_at")
    for row in path.get("intervals") or ():
        interval = dict(row)
        start = _instant(interval.get("valid_from"), "interval.valid_from")
        raw_end = interval.get("valid_to")
        end = None if raw_end in (None, "") else _instant(raw_end, "interval.valid_to")
        if start <= moment and (end is None or moment < end):
            return interval
    return None


def integrate_registration_paths(
    inputs: CapitalInputs,
    *,
    as_of: str,
    generated_at: str,
    rule_pack: RuleApplicabilityPack | None = None,
) -> RegistrationIntegration:
    """Compile distinct registration-path predicates from the accepted generation in ``inputs``.

    Deterministic and offline: no HTTP, no LLM, no SEC request.  Fails closed
    (raises :class:`RegistrationIntegrationRefusal`) on a non-C0 input, on no
    registration source bound at all, on an events ledger bound without its
    edges, on a precompiled bundle that does not validate, on a precompiled
    bundle cut at another house-knowledge cutoff, and on a recompile that
    disagrees with the precompiled bundle bound beside it.
    """
    if not isinstance(inputs, CapitalInputs):
        raise RegistrationIntegrationRefusal("inputs must be a C0 CapitalInputs")
    cutoff = _iso_z(as_of, "as_of")
    produced = _iso_z(generated_at, "generated_at")
    if _instant(produced, "generated_at") < _instant(cutoff, "as_of"):
        raise RegistrationIntegrationRefusal("generated_at cannot precede as_of")

    events_binding = inputs.binding(EVENTS_FAMILY)
    edges_binding = inputs.binding(EVENT_EDGES_FAMILY)
    lifecycle_binding = inputs.binding(LIFECYCLE_FAMILY)
    events_usable = _usable(events_binding) and _usable(edges_binding)
    lifecycle_usable = _usable(lifecycle_binding)

    bindings_used: dict[str, Any] = {}
    for name, binding in (
        (EVENTS_FAMILY, events_binding),
        (EVENT_EDGES_FAMILY, edges_binding),
        (LIFECYCLE_FAMILY, lifecycle_binding),
    ):
        if binding is not None:
            bindings_used[f"{name}_binding"] = binding.as_record()

    if events_usable:
        bundle = compile_registration_lifecycles(
            list(inputs.events),
            list(inputs.edges),
            cutoff,
            produced,
            source_generation=_source_generation(events_binding),
        )
        if lifecycle_usable:
            precompiled = [dict(row) for row in inputs.lifecycles]
            if not precompiled:
                raise RegistrationIntegrationRefusal(
                    "registration_lifecycle is bound supported/partial but inputs carry no lifecycle bundle"
                )
            for row in precompiled:
                _validate_precompiled(row, cutoff)
            bound_records = [record for row in precompiled for record in row["records"]]
            recompiled_digest = sha256_of(bundle["records"])
            precompiled_digest = sha256_of(bound_records)
            if recompiled_digest != precompiled_digest:
                raise RegistrationIntegrationRefusal(
                    "recompiled registration lifecycle records differ from the precompiled bundle bound "
                    f"beside them: recompiled sha256 {recompiled_digest} != precompiled sha256 "
                    f"{precompiled_digest}; bind exactly one registration source"
                )
        source_family = EVENTS_FAMILY
        source_schema = EVENT_SCHEMA
        source_generation_id = events_binding.generation_id if events_binding else None
        source_artifact_sha256 = events_binding.artifact_sha256 if events_binding else None
        support = "partial"
    elif lifecycle_usable:
        precompiled = [dict(row) for row in inputs.lifecycles]
        if not precompiled:
            raise RegistrationIntegrationRefusal(
                "registration_lifecycle is bound supported/partial but inputs carry no lifecycle bundle"
            )
        for row in precompiled:
            _validate_precompiled(row, cutoff)
        bundle = {
            "generation_id": precompiled[0].get("generation_id"),
            "records": [record for row in precompiled for record in row["records"]],
            "deferred": [item for row in precompiled for item in row["deferred"]],
            "coverage": dict(precompiled[0]["coverage"]),
        }
        source_family = LIFECYCLE_FAMILY
        source_schema = BUNDLE_SCHEMA
        source_generation_id = str(bundle["generation_id"]) if bundle["generation_id"] is not None else None
        source_artifact_sha256 = lifecycle_binding.artifact_sha256 if lifecycle_binding else None
        support = "partial"
    elif _usable(events_binding) and edges_binding is None and lifecycle_binding is None:
        # Spec A.2(5): the events+edges source is bound only when BOTH ledgers are
        # bound.  An edges ledger bound as unavailable/not_built falls through to
        # the unavailable family below; an edges ledger that is not bound at all
        # leaves no registration source, which refuses.
        raise RegistrationIntegrationRefusal(
            "events are bound supported/partial but event_edges is not bound; "
            "bind both immutable ledgers or bind a precompiled registration_lifecycle bundle"
        )
    elif events_binding is not None or lifecycle_binding is not None:
        binding = lifecycle_binding if lifecycle_binding is not None else events_binding
        assert binding is not None
        source_family = binding.input_family
        source_schema = None
        source_generation_id = binding.generation_id
        source_artifact_sha256 = binding.artifact_sha256
        support = "unavailable"
        bundle = {"generation_id": None, "records": [], "deferred": [], "coverage": {"state": "unavailable"}}
    else:
        raise RegistrationIntegrationRefusal(
            "inputs carry no registration source; bind events+event_edges or a precompiled "
            "registration_lifecycle bundle, explicitly unavailable if that is the truth"
        )

    receipt = CalculationReceipt.build(
        inputs={
            **bindings_used,
            "as_of": cutoff,
            "rule_pack_version": getattr(rule_pack, "version", None),
        },
        rule_digest=_rule_digest(rule_pack),
        implementation=REGISTRATION_INTEGRATION_VERSION,
        computed_at=produced,
    )
    if support == "unavailable":
        result = RegistrationIntegration(
            paths=(), deferred=(), receipt=receipt, support=support,
            support_limits=_support_limits(coverage_state="unavailable", pack=rule_pack),
            source_family=source_family, source_schema=source_schema,
            source_generation_id=source_generation_id, source_artifact_sha256=source_artifact_sha256,
            as_of=cutoff, generated_at=produced,
        )
        result.family_state()
        return result

    paths = _paths_from_bundle(bundle, as_of=cutoff, pack=rule_pack)
    coverage_state = str((bundle.get("coverage") or {}).get("state") or "")
    result = RegistrationIntegration(
        paths=paths,
        deferred=tuple(deepcopy(dict(row)) for row in bundle["deferred"]),
        receipt=receipt,
        support=support,
        support_limits=_support_limits(coverage_state=coverage_state, pack=rule_pack),
        source_family=source_family,
        source_schema=source_schema,
        source_generation_id=source_generation_id,
        source_artifact_sha256=source_artifact_sha256,
        as_of=cutoff,
        generated_at=produced,
    )
    result.family_state()
    return result


__all__ = [
    "AUTHORITY",
    "AUTOMATIC_SHELF_FORMS",
    "EVENT_EDGES_FAMILY",
    "EVENTS_FAMILY",
    "EVENT_SCHEMA",
    "LIFECYCLE_FAMILY",
    "OFFERING_ROLES",
    "PREDICATE_STATUSES",
    "REGISTRATION_FAMILY",
    "REGISTRATION_INTEGRATION_VERSION",
    "REGISTRATION_PATH_SCHEMA",
    "RULES_CONSULTED",
    "RULE_415_A_5",
    "RULE_415_A_6",
    "RULE_462_E",
    "RegistrationIntegration",
    "RegistrationIntegrationRefusal",
    "SHELF_FAMILIES",
    "SHELF_WINDOW_CONDITIONS",
    "SHELF_WINDOW_POSITIONS",
    "UNAVAILABLE",
    "WKSI_CONDITION",
    "integrate_registration_paths",
    "registration_path_at",
]
