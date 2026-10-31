"""Capital-structure V2 task S0: one scenario, three components, one answer.

``compose_scenario`` runs capacity (C1/C2), share supply (I1/I2) and the funding
schedule (F1) under ONE ``scenario_id`` and ONE ``state_id`` and cross-checks
them.  It is a COMPOSER and nothing else:

* it never re-solves the joint problem (C2 owns it) and reports no witness of
  its own -- capacity's witness stays reachable through ``capacity_envelope``;
* it never re-derives an instrument economic (I1/I2 own them) and copies the
  supply trace row instead;
* it never rewrites F1's balance identity, substitutes a canonical amount into
  the funding schedule, or caps a conditional proceed to a pool bound (A30).

What it adds is the two answers no component gives alone -- "do the requested
actions fit together?" (read from C2) and "under this scenario, is each period's
funding gap covered, by how much, and from which requested proceeds?" -- plus
one canonical owner per cash amount, so a disagreement between the components is
a NAMED blocker carrying both values instead of a silent pick.

Laws enforced here (gates A22, A26, A30, A31, A32; masterplan L180, L234):

* a scenario view and a state view mode stay structurally distinct: a then-known
  scenario runs only on then-known facts, and S0 never relabels either (A31);
* the per-action issuance rows are never summed into an outstanding share count
  or into a claim, and their two totals are known only when every row is known
  -- an unknown part never yields a finite total (A26);
* coverage is scenario-only: every period carries the same disclosure that the
  proceeds are undated, conditional and not cash on hand (A30);
* authorized headroom is DISCLOSED, never assumed: capacity's status is carried
  verbatim and an unevaluated charter limit stays unevaluated (SPEC_S0 §7a);
* no score, rank, sizing, probability, likelihood, recommendation or expected
  dilution is produced, and ``prophet_authority`` is the literal false denial.

Exact arithmetic only: money is :class:`~decimal.Decimal`, share counts are
:class:`~fractions.Fraction` floored to whole shares, and no float is accepted or
produced.  The composition is a pure function of its arguments -- no file,
network, clock, collector or model access -- so one input order and one set of
assumptions give one byte-identical record (A22).
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence

from engine.capital_structure import capacity as capacity_module
from engine.capital_structure import funding as funding_module
from engine.capital_structure import supply_scenarios as supply_module
from engine.capital_structure.listing_facts import ListingFact
from engine.capital_structure.issuer_state_contracts import (
    AUTHORIZED_HEADROOM_STATUSES,
    COVERAGE_SCENARIO_ONLY_NOTE,
    RECORD_SCHEMAS,
    ActionCheck,
    AuthorizedHeadroomDisclosure,
    CalculationReceipt,
    CapitalState,
    CashReconciliation,
    CommitmentInputs,
    CoveragePeriod,
    FinancialInputs,
    FinancingScenario,
    Flow,
    FundingSchedule,
    InstrumentSet,
    IssuanceRow,
    JointCheck,
    PriceBasis,
    Quantity,
    RulePack,
    ScenarioResult,
    ShareBasisResult,
    SignedQuantity,
    Unknown,
    sha256_of,
    stable_id,
)

__all__ = [
    "IMPLEMENTATION",
    "COVERAGE_ONLY_NOTE",
    "PRICE_BASIS_NOTE",
    "SCENARIO_ISSUANCE_NOTE",
    "ScenarioComposition",
    "ScenarioCompositionError",
    "compose_scenario",
    "explain_scenario",
]

#: The receipt's implementation string (SPEC_S0 §9).
IMPLEMENTATION = "s0_composition.v1"

#: SPEC_S0 §8: the record schema a composed result carries.
RESULT_SCHEMA = RECORD_SCHEMAS["scenario_result"]

#: SPEC_S0 §5: the unknown an issuance row names when no price converts it.
SHARES_UNPRICED_PREFIX = "scenario_shares_unpriced"
#: SPEC_S0 §5: an issuance row whose owner models no share effect at all.
SHARES_NOT_MODELLED_PREFIX = "scenario_shares_not_modelled"
#: SPEC_S0 §4: the unknown a reconciliation row names when one side is unpriced.
CASH_UNPRICED_PREFIX = "scenario_cash_unpriced"
#: SPEC_S0 §7a: the disclosure S0 makes when capacity carried no charter limit.
AUTHORIZED_HEADROOM_UNKNOWN = "authorized_headroom_not_evaluated:charter_limit_unchecked"

#: Capacity's own blocker families (C2a §2.6), read verbatim and never re-solved.
INFEASIBLE_PREFIX = "asserted_actions_infeasible:"
INFEASIBLE_BRANCH_PREFIXES = (
    "asserted_actions_infeasible_on_price_branch:",
    "asserted_actions_infeasible_on_branch:",
)
INELIGIBLE_PREFIX = "asserted_action_on_ineligible_route:"

#: F1's flow-id shapes for one scenario action (F1 owns the spelling).
RELIEF_CONDITION_PREFIX = "relieved under scenario"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,199}$")

#: The three declarative result notes.  None of them states or implies that a
#: scenario proceed is cash the issuer holds (A30).
SCENARIO_ISSUANCE_NOTE = (
    "scenario issuance rows are scenario-conditional new shares and are never added to an "
    "outstanding share count, to a claim or to a supply component"
)
COVERAGE_ONLY_NOTE = (
    "funding-gap coverage is scenario-only: the requested proceeds are undated and "
    "conditional, not cash on hand"
)
PRICE_BASIS_NOTE = (
    "the three components price different things on different bases; the bases are stated "
    "and never reconciled"
)

_CAPACITY_PRICE_NOTES = {
    "fixed": "capacity prices every route at the scenario's fixed price",
    "path_start": "capacity prices a scheduled takedown at the price in effect at the horizon start",
    "path_window_low_high": (
        "capacity prices an at-the-market programme over the window low and the window high"
    ),
}
_SUPPLY_PRICE_NOTES = {
    "fixed": "supply prices a cashless or net-share settlement at the scenario's fixed price",
    "path_horizon_end": "supply prices at the last path point on or before the horizon end",
    "unpriced": "supply has no price at the horizon end, so a net settlement is unpriced",
}
_FUNDING_PRICE_NOTES = {
    "fixed": "funding converts a share quantity at the scenario's fixed usd price",
    "unpriced": "funding books no amount for a quantity it cannot convert at a fixed usd price",
}


class ScenarioCompositionError(ValueError):
    """The three components could not be composed under one scenario identity."""


@dataclass(frozen=True)
class ScenarioComposition:
    """The ``explain_*`` companion of :func:`compose_scenario`.

    Mirrors ``capacity.CapacityEvaluation``: the projected result plus the exact
    material it was composed from, so a reviewer can re-read every cross-check
    against the component that owns it.
    """

    result: ScenarioResult
    #: The capacity evaluation: envelope plus the digested inputs and the kernel.
    capacity: Any
    #: ``capital_structure.supply_trace.v1``, re-stamped with the state identity.
    supply_trace: dict[str, Any]
    #: The funding schedule already bound to the issuer state.
    funding: FundingSchedule


# ---------------------------------------------------------------------------
# Exact readers
# ---------------------------------------------------------------------------


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScenarioCompositionError(message)


def _identifier(value: str, prefix: str) -> str:
    """An identifier the contract accepts; a longer one is digested, never cut."""
    if len(value) <= 200 and _ID_RE.match(value):
        return value
    return f"{prefix}:{sha256_of(value)[:16]}"


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if text.startswith("-") and Decimal(text) == 0:
        return "0"
    return text


def _exact_or_none(value: Fraction | None) -> str | None:
    return None if value is None else f"{value.numerator}/{value.denominator}"


def _usd(value: Decimal | None, note: str | None = None) -> Quantity:
    if value is None:
        return Quantity.unknown("usd", note=note)
    return Quantity.known(_decimal_text(value), "usd", note=note)


def _usd_not_applicable(note: str | None = None) -> Quantity:
    return Quantity(unit="usd", status="not_applicable", note=note)


def _signed_usd(value: Decimal | None, note: str | None = None) -> SignedQuantity:
    """A signed money amount: F1's deficit case leaves the balance negative (§7).

    ``Quantity`` refuses a negative by contract and S0 never clamps, rounds or
    withholds an exact value, so the four signed coverage fields carry the
    contract's :class:`SignedQuantity` instead.
    """
    if value is None:
        return SignedQuantity.unknown("usd", note=note)
    return SignedQuantity.known(_decimal_text(value), "usd", note=note)


def _signed_usd_not_applicable(note: str | None = None) -> SignedQuantity:
    return SignedQuantity(unit="usd", status="not_applicable", note=note)


def _shares(value: int | None, note: str | None = None) -> Quantity:
    basis = "scenario_incremental_issuance"
    if value is None:
        return Quantity.unknown("shares", share_basis=basis, note=note)
    return Quantity.known(str(value), "shares", share_basis=basis, note=note)


def _unknown(unknown_id: str, description: str, resolving_fact: str, affects: Sequence[str]) -> Unknown:
    return Unknown(
        unknown_id=unknown_id,
        description=description,
        resolving_fact=resolving_fact,
        affects=tuple(sorted(set(affects))),
    )


def _floor_division(numerator: Fraction, denominator: Fraction) -> int:
    """Whole shares, floored: a fractional share is never rounded up or guessed."""
    quotient = numerator / denominator
    return quotient.numerator // quotient.denominator


def _flow_amount(flow: Flow | None) -> Quantity:
    if flow is None:
        return _usd_not_applicable("the funding schedule books no flow for this route")
    return flow.amount


def _known_decimal(quantity: Quantity | SignedQuantity) -> Decimal | None:
    return quantity.decimal if quantity.status == "known" else None


# ---------------------------------------------------------------------------
# §2 Preconditions (A31) and component identity
# ---------------------------------------------------------------------------


def _preconditions(state: Any, scenario: Any) -> None:
    _require(isinstance(state, CapitalState), "state: a CapitalState is required")
    _require(isinstance(scenario, FinancingScenario), "scenario: a FinancingScenario is required")
    _require(
        scenario.as_of == state.request.as_of,
        "as_of_mismatch: the scenario is dated "
        f"{scenario.as_of!r} but the state cutoff is {state.request.as_of!r}; a scenario never "
        "moves a state's cutoff",
    )
    # S0 owns the view pairing: no component enforces it.  A then-known scenario
    # is a claim about what was knowable, so it runs only on then-known facts.
    # A counterfactual runs on any state view mode and is recorded as one.
    if scenario.view == "then_known" and state.request.view_mode != "then_known":
        raise ScenarioCompositionError(
            f"view_mismatch:then_known_scenario_on_{state.request.view_mode}_state"
        )


def _identity(component: str, condition: bool) -> None:
    if not condition:
        raise ScenarioCompositionError(f"scenario_identity_mismatch:{component}")


def _run_components(
    state: CapitalState,
    instruments: InstrumentSet,
    basis: ShareBasisResult,
    financials: FinancialInputs,
    commitments: CommitmentInputs,
    scenario: FinancingScenario,
    rules: RulePack,
    pack: Any,
    listing: ListingFact | None = None,
) -> tuple[Any, dict[str, Any], Any, FundingSchedule]:
    """Steps 2-4 of the fixed compose order, each wrapped only by type."""
    try:
        evaluation = capacity_module.explain_capacity(state, scenario, rules, pack=pack, listing=listing)
    except capacity_module.CapacityInputError as exc:
        raise ScenarioCompositionError(str(exc)) from exc
    _identity("capacity", evaluation.envelope.scenario_id == scenario.scenario_id)
    _identity("capacity", evaluation.envelope.receipt.scenario_id == scenario.scenario_id)
    _identity("capacity", evaluation.envelope.state_id == state.state_id)

    try:
        trace = supply_module.supply_trace(instruments, basis, scenario)
        envelope = supply_module.evaluate_supply(instruments, basis, scenario)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise ScenarioCompositionError(str(exc)) from exc
    _identity("supply", trace["scenario_id"] == scenario.scenario_id)
    # SPEC_I1 §5.1: the envelope digests the supply inputs it consumed, so the
    # join re-stamps it with the issuer state's identity -- never the other way.
    _identity("supply", envelope.receipt.scenario_id == scenario.scenario_id)
    _identity("supply", envelope.scenario_id == scenario.scenario_id)
    envelope = dataclasses.replace(envelope, state_id=state.state_id)
    trace = {**trace, "state_id": state.state_id}
    _identity("supply", envelope.state_id == state.state_id)

    try:
        schedule = funding_module.project_funding(financials, commitments, scenario)
        schedule = capacity_module.bind_funding_schedule(state, schedule)
    except (funding_module.FundingInputError, capacity_module.CapacityInputError) as exc:
        raise ScenarioCompositionError(str(exc)) from exc
    _identity("funding", schedule.scenario_id == scenario.scenario_id)
    _identity("funding", schedule.receipt.scenario_id == scenario.scenario_id)
    _identity("funding", schedule.state_id == state.state_id)
    return evaluation, trace, envelope, schedule


# ---------------------------------------------------------------------------
# §3 Action checks and the joint check (read from C2, never re-solved)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ActionIndex:
    """One scenario action per route, with what each component said about it."""

    route_ids: tuple[str, ...]
    selections: Mapping[str, Any]
    applied: Mapping[str, dict[str, Any]]
    outside: Mapping[str, dict[str, Any]]
    route_kinds: Mapping[str, str]
    consumes: Mapping[str, tuple[str, ...]]
    blockers: tuple[str, ...]
    #: SPEC_C2D §5: the outside actions whose shared-pool consumption capacity
    #: modelled, keyed by route id (empty before C2d or when none is modelled).
    modelled: Mapping[str, dict[str, Any]] = field(default_factory=dict)


def _index_actions(evaluation: Any, scenario: FinancingScenario) -> _ActionIndex:
    inputs = evaluation.inputs
    applied = {item["route_id"]: item for item in inputs.get("actions_applied", ())}
    outside = {item["route_id"]: item for item in inputs.get("non_capacity_actions", ())}
    modelled = {item["route_id"]: item for item in inputs.get("outside_consumption", ())}
    selections = {action.route_id: action for action in scenario.actions}
    route_ids = tuple(sorted(selections))
    # Capacity partitions every scenario action into exactly these two records
    # (SPEC_C2B §2.1); anything else means the envelope changed under S0.
    for route_id in route_ids:
        _require(
            (route_id in applied) != (route_id in outside),
            f"action_route_unaccounted:{route_id}",
        )
    # SPEC_C2D §1.3: a modelled outside action is still an outside action (no
    # route, no plan); capacity only states which shared pools it consumes.
    for route_id in modelled:
        _require(route_id in outside, f"action_route_unaccounted:{route_id}")
    routes = {route.route_id: route for route in evaluation.envelope.routes}
    consumes = {route_id: tuple(route.consumes) for route_id, route in routes.items()}
    for route_id, item in modelled.items():
        consumes[route_id] = tuple(item["pools"])
    return _ActionIndex(
        route_ids=route_ids,
        selections=selections,
        applied=applied,
        outside=outside,
        route_kinds={route_id: route.route_kind for route_id, route in routes.items()},
        consumes=consumes,
        blockers=tuple(evaluation.envelope.blockers),
        modelled=modelled,
    )


def _names(constraint_id: str, route_id: str, consumed: Sequence[str]) -> bool:
    """Whether one infeasibility blocker names this route or a pool it consumes."""
    return constraint_id == route_id or constraint_id in consumed


def _action_blockers(
    index: _ActionIndex, route_id: str
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """The both-branch, single-branch and ineligible-route blockers naming a route.

    Capacity's constraint ids carry colons of their own (``baby_shelf:2026-10-14``),
    so the id is read by stripping the blocker's own known prefix and, for a
    branch blocker, by partitioning off the branch label only.
    """
    consumed = index.consumes.get(route_id, ())
    both: list[str] = []
    branch: list[str] = []
    ineligible: list[str] = []
    for blocker_id in index.blockers:
        if blocker_id.startswith(INFEASIBLE_PREFIX):
            if _names(blocker_id[len(INFEASIBLE_PREFIX):], route_id, consumed):
                both.append(blocker_id)
            continue
        if blocker_id.startswith(INELIGIBLE_PREFIX):
            if blocker_id[len(INELIGIBLE_PREFIX):] == route_id:
                ineligible.append(blocker_id)
            continue
        for prefix in INFEASIBLE_BRANCH_PREFIXES:
            if not blocker_id.startswith(prefix):
                continue
            _branch, _separator, constraint_id = blocker_id[len(prefix):].partition(":")
            if _names(constraint_id, route_id, consumed):
                branch.append(blocker_id)
            break
    return tuple(sorted(both)), tuple(sorted(branch)), tuple(sorted(ineligible))


def _action_check(index: _ActionIndex, route_id: str) -> ActionCheck:
    selection = index.selections[route_id]
    if route_id in index.applied:
        record = index.applied[route_id]
        both, branch, ineligible = _action_blockers(index, route_id)
        blockers = tuple(sorted(set((*both, *branch, *ineligible))))
        if not record["fixed"]:
            status = "not_applied"
        elif both:
            status = "infeasible"
        elif ineligible:
            status = "ineligible_route"
        elif branch:
            status = "infeasible_on_price_branch"
        else:
            status = "within_capacity"
        note = (
            "capacity applied the asserted quantity as a fixed use of this route"
            if record["fixed"] and record["applied"]
            else "capacity recorded this action and applied no quantity"
        )
        return ActionCheck(
            route_id=route_id,
            action=record["action"],
            settlement=record["settlement"],
            status=status,
            owner="capacity",
            fixed=bool(record["fixed"]),
            blocker_ids=blockers,
            unknown_ids=(),
            note=note,
        )
    record = index.outside[route_id]
    owner = record["owner"]
    _require(
        owner in ("supply", "funding_only", "capacity_unmodelled"),
        f"action_owner_unrecognised:{owner}",
    )
    refused = f"{INELIGIBLE_PREFIX}{route_id}" in index.blockers
    if owner == "capacity_unmodelled" and (route_id in index.modelled or refused):
        # SPEC_C2D §1.5/§2.3: capacity now answers for this outside action -- it
        # either consumed the shared pools the action draws on, or refused the
        # declared registration path as ineligible.  Its status is capacity's.
        both, branch, ineligible = _action_blockers(index, route_id)
        blockers = tuple(sorted(set((*both, *branch, *ineligible))))
        if ineligible:
            status = "ineligible_route"
        elif both:
            status = "infeasible"
        elif branch:
            status = "infeasible_on_price_branch"
        else:
            status = "within_capacity"
        note = (
            "capacity applied the asserted quantity as a fixed consumption of the shared "
            "pools this action draws on; the action's own limit belongs to its funding owner"
            if route_id in index.modelled
            else "capacity refused the declared registration path as ineligible and applied no consumption"
        )
        return ActionCheck(
            route_id=route_id,
            action=record["action"],
            settlement=record["settlement"],
            status=status,
            owner="capacity",
            fixed=bool(record["fixed"]),
            blocker_ids=blockers,
            unknown_ids=(),
            note=note,
        )
    status = "not_modelled" if owner == "capacity_unmodelled" else "not_a_capacity_route"
    unknown_ids: tuple[str, ...] = ()
    if status == "not_modelled" and record["fixed"]:
        unknown_ids = (_identifier(f"action_route_not_modelled:{route_id}", "action_route_not_modelled"),)
    note = (
        f"capacity carries no route for this action; {owner} owns its consequence"
        if status == "not_a_capacity_route"
        else "capacity models no pool consumption for this route kind, so its fixed quantity is unmodelled"
    )
    return ActionCheck(
        route_id=route_id,
        action=record["action"],
        settlement=record["settlement"],
        status=status,
        owner=owner,
        fixed=bool(record["fixed"]),
        blocker_ids=(),
        unknown_ids=unknown_ids,
        note=note,
    )


def _action_checks(index: _ActionIndex) -> tuple[ActionCheck, ...]:
    return tuple(_action_check(index, route_id) for route_id in index.route_ids)


_JOINT_NOTES = {
    "infeasible": "capacity reports the asserted actions do not fit together",
    "indeterminate": "capacity leaves the asserted actions open under the named unknowns",
    "feasible": "capacity reports the asserted actions fit together within the evaluated limits",
    "no_capacity_actions": "the scenario asserts no fixed capacity action",
}


def _joint_check(index: _ActionIndex, checks: Sequence[ActionCheck], evaluation: Any) -> JointCheck:
    envelope = evaluation.envelope
    aggregate = envelope.aggregate_bound
    statuses = {check.status for check in checks}
    applied = {route_id for route_id, record in index.applied.items() if record["fixed"] and record["applied"]}
    # SPEC_C2D §5: a modelled outside action is a fixed use capacity applied too.
    applied |= set(index.modelled)
    fixed_unmodelled = any(check.status == "not_modelled" and check.fixed for check in checks)
    any_fixed = any(check.fixed for check in checks)
    # SPEC_S0 §3 chains these four in this order: an infeasibility first, then an
    # open residual question, then a known feasible answer, and only then "the
    # scenario asserts no fixed capacity action".
    if aggregate.status == "contradicted" or statuses & {"infeasible", "ineligible_route"}:
        status = "infeasible"
    elif (
        "infeasible_on_price_branch" in statuses
        or fixed_unmodelled
        or (aggregate.status == "unknown" and any_fixed)
    ):
        status = "indeterminate"
    elif applied and aggregate.status == "known":
        status = "feasible"
    elif applied:
        # A withheld or inapplicable aggregate leaves the residual question open.
        status = "indeterminate"
    else:
        status = "no_capacity_actions"
    note = _JOINT_NOTES[status]
    if aggregate.note:
        note = f"{note}; capacity aggregate note: {aggregate.note}"
    return JointCheck(
        status=status,
        aggregate_status=aggregate.status,
        binding=tuple(envelope.binding_constraints),
        blocker_ids=tuple(sorted(envelope.blockers)),
        note=note,
    )


# ---------------------------------------------------------------------------
# §4 Cash reconciliation -- one canonical owner per amount
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FundingSide:
    """What F1 booked for one route, read from its own flow ids."""

    gross: Flow | None
    fee: Flow | None
    outflow: Flow | None
    relief: Flow | None

    @property
    def amount(self) -> Quantity:
        for flow in (self.gross, self.outflow):
            if flow is not None:
                return flow.amount
        if self.relief is not None:
            return self.relief.amount
        return _usd_not_applicable("the funding schedule books no flow for this route")

    @property
    def booked_cash(self) -> bool:
        return self.gross is not None or self.outflow is not None


def _funding_side(schedule: FundingSchedule, route_id: str, action: str) -> _FundingSide:
    flows: dict[str, Flow] = {}
    for period in schedule.periods:
        for flow in (*period.sources, *period.uses):
            flows[flow.flow_id] = flow
    relief = flows.get(f"use:{route_id}")
    if relief is not None and not (
        relief.certainty == "conditional"
        and (relief.condition or "").startswith(RELIEF_CONDITION_PREFIX)
    ):
        relief = None
    outflow = flows.get(f"use:{route_id}:{action}") if action in ("repurchase", "redemption") else None
    return _FundingSide(
        gross=flows.get(f"source:{route_id}:gross"),
        fee=flows.get(f"use:{route_id}:fee"),
        outflow=outflow,
        relief=relief,
    )


def _fee_split(gross: Decimal | None, fee_rate: str | None, note: str | None) -> tuple[Quantity, Quantity]:
    """Gross and net with exactly one canonical owner; net is unknown without a rate."""
    if gross is None:
        return _usd(None, note), _usd(None, "no fee rate or no canonical gross to apply it to")
    if fee_rate is None:
        return _usd(gross, note), _usd(None, "the scenario states no fee rate, so net is unknown")
    net = gross * (Decimal(1) - Decimal(fee_rate))
    return _usd(gross, note), _usd(net, note)


def _capacity_canonical(
    record: Mapping[str, Any], selection: Any, fee_rate: str | None
) -> tuple[Quantity, Quantity]:
    """SPEC_S0 §4 rows 1-2: the asserted usd, or the asserted share range."""
    pessimistic = record.get("usd_pessimistic")
    optimistic = record.get("usd_optimistic")
    quantity = selection.quantity
    if quantity is not None and quantity.unit == "shares":
        if pessimistic is None or optimistic is None:
            return _usd(None, "capacity priced no branch for this share quantity"), _usd(None)
        if Decimal(pessimistic) == Decimal(optimistic):
            return _fee_split(Decimal(pessimistic), fee_rate, "capacity converted the asserted shares at one price")
        note = (
            "the canonical gross is a range under the price path: pessimistic "
            f"{pessimistic} usd, optimistic {optimistic} usd; neither end is chosen"
        )
        return _usd(None, note), _usd(None, note)
    if pessimistic is None:
        return _usd(None, "capacity applied no dollar amount for this route"), _usd(None)
    return _fee_split(Decimal(pessimistic), fee_rate, "the asserted usd quantity capacity applied")


def _supply_canonical(
    trace_rows: Mapping[str, Mapping[str, Any]],
    cash_effects: Mapping[str, Any],
    route_id: str,
) -> tuple[Quantity, Quantity, str | None]:
    """SPEC_S0 §4 rows 3-7: I1/I2 own the amount; S0 copies it and never re-derives."""
    effect = cash_effects.get(route_id)
    row = trace_rows.get(route_id)
    if effect is None:
        return _usd(None, "supply booked no cash effect for this route"), _usd(None), None
    if effect.kind == "no_cash":
        return (
            _usd_not_applicable("supply books no issuer cash for this settlement"),
            _usd_not_applicable("supply books no issuer cash for this settlement"),
            "no_cash",
        )
    gross_text = None if row is None else row.get("gross_cash")
    net_text = None if row is None else row.get("net_cash")
    gross = None if gross_text in (None, "unknown") else Decimal(gross_text)
    net = None if net_text in (None, "unknown") else Decimal(net_text)
    note = f"supply books a {effect.kind} for this route"
    return _usd(gross, note), _usd(net, note), effect.kind


def _reconcile(
    index: _ActionIndex,
    checks: Sequence[ActionCheck],
    trace_rows: Mapping[str, Mapping[str, Any]],
    cash_effects: Mapping[str, Any],
    schedule: FundingSchedule,
    scenario: FinancingScenario,
    unknowns: list[Unknown],
    blockers: list[str],
) -> tuple[CashReconciliation, ...]:
    rows: list[CashReconciliation] = []
    for check in sorted(checks, key=lambda item: item.route_id):
        route_id = check.route_id
        selection = index.selections[route_id]
        action = selection.action
        side = _funding_side(schedule, route_id, action)
        conflict_id: str | None = None
        if route_id in index.applied:
            canonical_gross, canonical_net = _capacity_canonical(
                index.applied[route_id], selection, scenario.fee_rate
            )
            canonical_kind: str | None = "proceeds"
        elif action in ("warrant_exercise", "conversion", "exchange"):
            canonical_gross, canonical_net, canonical_kind = _supply_canonical(
                trace_rows, cash_effects, route_id
            )
            if canonical_kind is None and side.booked_cash:
                canonical_kind = "proceeds"
        else:
            # repurchase, redemption, debt_draw, other and the unmodelled routes:
            # no component owns a second amount, so F1's own booking is canonical
            # (SPEC_S0 §4 row 8) and an unbooked amount stays unknown (row 9).
            canonical_kind = "proceeds" if side.booked_cash else None
            canonical_gross = side.amount if side.booked_cash else _usd(
                None, "no component books a canonical amount for this route"
            )
            canonical_net = canonical_gross
        status = _reconciliation_status(
            route_id=route_id,
            action=action,
            canonical_gross=canonical_gross,
            canonical_kind=canonical_kind,
            side=side,
            unknowns=unknowns,
        )
        if status in ("disagree", "conflict"):
            conflict_id = _identifier(
                "conversion_cash_settlement_vs_relief:" + route_id
                if status == "conflict"
                else "cash_effect_disagreement:" + route_id,
                "cash_effect_disagreement",
            )
            blockers.append(conflict_id)
        rows.append(
            CashReconciliation(
                route_id=route_id,
                owner=check.owner,
                canonical_gross=canonical_gross,
                canonical_net=canonical_net,
                funding_amount=side.amount,
                status=status,
                conflict_id=conflict_id,
            )
        )
    return tuple(rows)


def _reconciliation_status(
    *,
    route_id: str,
    action: str,
    canonical_gross: Quantity,
    canonical_kind: str | None,
    side: _FundingSide,
    unknowns: list[Unknown],
) -> str:
    funding = side.amount
    no_canonical_cash = canonical_gross.status == "not_applicable"
    if no_canonical_cash:
        if side.booked_cash:
            return "disagree"
        # A relieved maturity F1 flipped to conditional is valid and is already
        # excluded from its closing balance, so neither side moves cash.
        return "not_applicable"
    if canonical_kind == "repayment" and side.relief is not None:
        return "conflict"
    canonical_value = _known_decimal(canonical_gross)
    funding_value = _known_decimal(funding)
    if canonical_value is not None and funding_value is not None:
        if canonical_value == funding_value:
            return "agree"
        return "disagree"
    unknowns.append(
        _unknown(
            _identifier(f"{CASH_UNPRICED_PREFIX}:{route_id}", CASH_UNPRICED_PREFIX),
            f"the canonical cash amount for {route_id} ({action}) and the amount the funding "
            f"schedule booked for it are not both known: canonical {canonical_gross.status}, "
            f"funding {funding.status}",
            f"a priced cash amount for {route_id} on both sides",
            ("conditional_flows",),
        )
    )
    return "funding_unpriced"


# ---------------------------------------------------------------------------
# §5 Scenario new shares per action (rows; never added to outstanding or claims)
# ---------------------------------------------------------------------------


def _issuance_row(
    index: _ActionIndex,
    route_id: str,
    price_record: Mapping[str, Any],
    trace_rows: Mapping[str, Mapping[str, Any]],
    unknowns: list[Unknown],
) -> IssuanceRow:
    selection = index.selections[route_id]
    quantity = selection.quantity
    if route_id in index.applied:
        route_kind = index.route_kinds.get(route_id, selection.action)
        if quantity is not None and quantity.unit == "shares":
            if quantity.status != "known" or quantity.value is None:
                return _unknown_row(route_id, SHARES_UNPRICED_PREFIX, unknowns,
                                    "the asserted share quantity is not known")
            shares = int(Decimal(quantity.value))
            return IssuanceRow(route_id, _shares(shares), _shares(shares), "stated_share_quantity")
        amount = None if quantity is None or quantity.value is None else Fraction(Decimal(quantity.value))
        if amount is None:
            return _unknown_row(route_id, SHARES_UNPRICED_PREFIX, unknowns,
                                "the asserted dollar quantity is not known")
        if route_kind == "at_the_market":
            price_high = _fraction(price_record.get("high"))
            price_low = _fraction(price_record.get("low"))
            basis = "path_window_low_high" if price_record.get("kind") == "path" else "fixed_price"
            if price_high is None or price_low is None:
                return _unknown_row(route_id, SHARES_UNPRICED_PREFIX, unknowns,
                                    "capacity priced no window for this route")
            # More shares at the window low than at the window high; both ends
            # are stated and neither is picked.
            return IssuanceRow(
                route_id,
                _shares(_floor_division(amount, price_high)),
                _shares(_floor_division(amount, price_low)),
                basis,
            )
        price = _fraction(price_record.get("p_start"))
        if price is None:
            return _unknown_row(route_id, SHARES_UNPRICED_PREFIX, unknowns,
                                "capacity priced nothing in effect at the horizon start")
        basis = "path_start_price" if price_record.get("kind") == "path" else "fixed_price"
        shares = _floor_division(amount, price)
        return IssuanceRow(route_id, _shares(shares), _shares(shares), basis)
    record = index.outside[route_id]
    if record["owner"] == "supply":
        row = trace_rows.get(route_id)
        text = None if row is None else row.get("incremental_shares")
        if text is not None and text != "unknown":
            shares = int(Decimal(text))
            return IssuanceRow(route_id, _shares(shares), _shares(shares), "supply_trace")
        raw = None
        if row is not None and row.get("unknowns"):
            raw = str(row["unknowns"][0])
        unknown_id = _identifier(raw or f"{SHARES_UNPRICED_PREFIX}:{route_id}", SHARES_UNPRICED_PREFIX)
        unknowns.append(
            _unknown(
                unknown_id,
                f"supply reports no known incremental share count for {route_id}",
                f"a known incremental share count for {route_id} from the supply owner",
                ("scenario_new_shares",),
            )
        )
        return IssuanceRow(route_id, _shares(None), _shares(None), "supply_trace", unknown_id)
    unknown_id = _identifier(f"{SHARES_NOT_MODELLED_PREFIX}:{route_id}", SHARES_NOT_MODELLED_PREFIX)
    unknowns.append(
        _unknown(
            unknown_id,
            f"{record['action']} on {route_id} is owned by {record['owner']}, which models no share "
            "effect for it, so the scenario's new shares on this route are unknown and never zero",
            f"the share issuance, if any, that the owner of {route_id} contracts for",
            ("scenario_new_shares",),
        )
    )
    return IssuanceRow(
        route_id, _shares(None), _shares(None), "not_evaluated_by_owner", unknown_id
    )


def _unknown_row(route_id: str, prefix: str, unknowns: list[Unknown], reason: str) -> IssuanceRow:
    unknown_id = _identifier(f"{prefix}:{route_id}", prefix)
    unknowns.append(
        _unknown(
            unknown_id,
            f"the scenario's new shares on {route_id} are unknown: {reason}",
            f"a price or a quantity that states the new shares on {route_id}",
            ("scenario_new_shares",),
        )
    )
    return IssuanceRow(route_id, _shares(None), _shares(None), "not_priced", unknown_id)


def _fraction(text: Any) -> Fraction | None:
    if not isinstance(text, str) or not text:
        return None
    numerator, _separator, denominator = text.partition("/")
    if denominator:
        return Fraction(int(numerator), int(denominator))
    return Fraction(Decimal(text))


def _share_totals(rows: Sequence[IssuanceRow]) -> tuple[Quantity, Quantity]:
    """A26: a finite total only when every row is known; never a guess."""
    unknown_rows = sorted(row.route_id for row in rows if row.unknown_id is not None)
    if unknown_rows:
        note = "not summed: the share effect is unknown for " + ", ".join(unknown_rows)
        return _shares(None, note), _shares(None, note)
    low = sum((int(row.shares_low.value) for row in rows), 0)
    high = sum((int(row.shares_high.value) for row in rows), 0)
    return _shares(low), _shares(high)


# ---------------------------------------------------------------------------
# §6 Price bases (declarative, no blocker)
# ---------------------------------------------------------------------------


def _price_bases(price_record: Mapping[str, Any], trace: Mapping[str, Any], scenario: FinancingScenario) -> tuple[PriceBasis, ...]:
    kind = price_record.get("kind")
    if kind == "fixed":
        capacity_basis = "fixed"
        low = high = _exact_or_none(_fraction(price_record.get("p_start")))
    elif price_record.get("branching"):
        capacity_basis = "path_window_low_high"
        low = _exact_or_none(_fraction(price_record.get("low")))
        high = _exact_or_none(_fraction(price_record.get("high")))
    else:
        capacity_basis = "path_start"
        low = high = _exact_or_none(_fraction(price_record.get("p_start")))
    header = trace.get("price") or {}
    stated = header.get("value")
    if header.get("kind") == "fixed":
        supply_basis = "fixed"
    elif stated not in (None, "unknown"):
        supply_basis = "path_horizon_end"
    else:
        supply_basis = "unpriced"
    supply_low = supply_high = None if stated in (None, "unknown") else str(stated)
    price = scenario.price
    funding_fixed = price.kind == "fixed" and price.currency == "USD" and price.fixed_price is not None
    funding_basis = "fixed" if funding_fixed else "unpriced"
    funding_value = price.fixed_price if funding_fixed else None
    return (
        PriceBasis("capacity", capacity_basis, low, high, _CAPACITY_PRICE_NOTES[capacity_basis]),
        PriceBasis(
            "funding",
            funding_basis,
            funding_value,
            funding_value,
            _FUNDING_PRICE_NOTES[funding_basis],
        ),
        PriceBasis("supply", supply_basis, supply_low, supply_high, _SUPPLY_PRICE_NOTES[supply_basis]),
    )


# ---------------------------------------------------------------------------
# §7 Funding-gap coverage (A30, scenario-only)
# ---------------------------------------------------------------------------


def _computed_balances(schedule: FundingSchedule) -> list[Decimal | None]:
    """opening(0) plus every non-conditional flow through k, exactly as F1 chains it.

    Where F1 publishes a known closing balance S0's value must equal it; where F1
    withheld one, S0 keeps its own exact value only in F1's deficit case (a
    negative computed balance) and withholds it otherwise, because F1 withholds
    for a named reason S0 does not own.
    """
    out: list[Decimal | None] = []
    running: Decimal | None = None
    for index, period in enumerate(schedule.periods):
        if index == 0:
            running = _known_decimal(period.opening_balance)
        counted = [
            flow
            for flow in (*period.sources, *period.uses)
            if flow.certainty != "conditional"
        ]
        if running is not None:
            if any(flow.amount.status != "known" for flow in counted):
                running = None
            else:
                sources = sum(
                    (Decimal(flow.amount.value) for flow in counted if flow.kind == "source"), Decimal(0)
                )
                uses = sum(
                    (Decimal(flow.amount.value) for flow in counted if flow.kind == "use"), Decimal(0)
                )
                running = running + sources - uses
        closing = _known_decimal(period.closing_balance)
        if closing is not None:
            _require(
                running is not None and running == closing,
                f"funding_balance_identity_mismatch:{period.period_start}",
            )
        elif running is not None and running >= 0:
            running = None
        out.append(running)
    return out


def _scenario_nets(schedule: FundingSchedule, route_ids: Sequence[str]) -> tuple[list[Decimal | None], list[Decimal | None]]:
    """Cumulative scenario-action conditional flows, and the gross side alone."""
    gross_ids = {f"source:{route_id}:gross" for route_id in route_ids}
    fee_ids = {f"use:{route_id}:fee" for route_id in route_ids}
    outflow_ids = {
        f"use:{route_id}:{action}"
        for route_id in route_ids
        for action in ("repurchase", "redemption")
    }
    nets: list[Decimal | None] = []
    grosses: list[Decimal | None] = []
    net = Decimal(0)
    gross = Decimal(0)
    for period in schedule.periods:
        for flow in (*period.sources, *period.uses):
            if flow.certainty != "conditional":
                continue
            if flow.flow_id in gross_ids:
                sign = 1
            elif flow.flow_id in fee_ids or flow.flow_id in outflow_ids:
                sign = -1
            else:
                # A relieved maturity is already excluded from F1's closing and
                # is never added back; a pre-existing conditional flow from the
                # facts is not a scenario action and is never counted.
                continue
            value = _known_decimal(flow.amount)
            if value is None:
                net = None
                if flow.flow_id in gross_ids:
                    gross = None
            else:
                if net is not None:
                    net = net + sign * value
                if flow.flow_id in gross_ids and gross is not None:
                    gross = gross + value
        nets.append(net)
        grosses.append(gross)
    return nets, grosses


def _coverage(
    schedule: FundingSchedule,
    route_ids: Sequence[str],
    joint: JointCheck,
    scenario: FinancingScenario,
) -> tuple[CoveragePeriod, ...]:
    computed = _computed_balances(schedule)
    nets, grosses = _scenario_nets(schedule, route_ids)
    not_evaluated = joint.status == "infeasible"
    reference = ", ".join(joint.blocker_ids) or "the capacity blockers in joint_check"
    periods: list[CoveragePeriod] = []
    for index, period in enumerate(schedule.periods):
        if not_evaluated:
            note = (
                f"{COVERAGE_SCENARIO_ONLY_NOTE}; coverage is not evaluated because the joint "
                f"check is infeasible ({reference})"
            )
            periods.append(
                CoveragePeriod(
                    period_start=period.period_start,
                    period_end=period.period_end,
                    gap=Quantity.unknown("usd", note="not evaluated: the joint check is infeasible"),
                    scenario_net=SignedQuantity.unknown(
                        "usd", note="not evaluated: the joint check is infeasible"
                    ),
                    scenario_balance=SignedQuantity.unknown(
                        "usd", note="not evaluated: the joint check is infeasible"
                    ),
                    shortfall=Quantity.unknown("usd", note="not evaluated: the joint check is infeasible"),
                    status="not_evaluated",
                    note=note,
                )
            )
            continue
        net = nets[index]
        base = computed[index]
        balance = None if net is None or base is None else base + net
        floor = _known_decimal(period.minimum_liquidity)
        shortfall = None if balance is None or floor is None else max(Decimal(0), floor - balance)
        if joint.status == "indeterminate":
            status = "indeterminate"
            shortfall_quantity = Quantity.unknown(
                "usd", note="the joint check is indeterminate, so the shortfall is not evaluated"
            )
        elif balance is None or shortfall is None:
            status = "indeterminate"
            shortfall_quantity = _usd(None, "an input to the shortfall is unknown")
        elif shortfall == 0:
            status = "covered"
            shortfall_quantity = _usd(shortfall)
        else:
            status = "shortfall"
            shortfall_quantity = _usd(shortfall)
        note = COVERAGE_SCENARIO_ONLY_NOTE
        gross_basis: SignedQuantity | None = None
        net_basis: SignedQuantity | None = None
        if scenario.fee_rate is not None:
            gross_basis = _signed_usd(
                grosses[index], "requested gross proceeds, before the scenario fee rate"
            )
            net_basis = _signed_usd(net, "requested proceeds after the scenario fee rate and any outflow")
            note = (
                f"{note}; gross_basis {_quantity_text(gross_basis)} usd, "
                f"net_basis {_quantity_text(net_basis)} usd at fee rate {scenario.fee_rate}"
            )
        periods.append(
            CoveragePeriod(
                period_start=period.period_start,
                period_end=period.period_end,
                gap=period.gap,
                scenario_net=_signed_usd(
                    net, "cumulative scenario-action conditional flows through this period"
                ),
                scenario_balance=_signed_usd(
                    balance,
                    None if balance is not None
                    else "the period's non-conditional balance or the scenario proceeds are unknown",
                ),
                shortfall=shortfall_quantity,
                status=status,
                note=note,
                gross_basis=gross_basis,
                net_basis=net_basis,
            )
        )
    return tuple(periods)


def _quantity_text(quantity: Quantity | SignedQuantity) -> str:
    return quantity.value if quantity.status == "known" and quantity.value is not None else quantity.status


# ---------------------------------------------------------------------------
# §7a Authorized headroom disclosure (read from capacity, never derived)
# ---------------------------------------------------------------------------

_AUTHORIZED_NOT_EVALUATED_NOTE = (
    "charter share limit not evaluated by capacity; requested share issuance is not checked "
    "against authorized shares"
)


def _authorized_headroom(
    evaluation: Any, unknowns: list[Unknown]
) -> AuthorizedHeadroomDisclosure:
    auth = evaluation.inputs.get("authorized")
    if auth is None:
        unknowns.append(
            _unknown(
                AUTHORIZED_HEADROOM_UNKNOWN,
                "capacity carried no authorized-share input, so the charter limit (authorized less "
                "issued less reserved common shares) was never evaluated for this scenario",
                "authorized-capital share records capacity can judge at the state cutoff",
                ("authorized_headroom",),
            )
        )
        return AuthorizedHeadroomDisclosure(
            status="not_evaluated",
            pool_id=None,
            capacity_status=None,
            note=_AUTHORIZED_NOT_EVALUATED_NOTE,
        )
    status = auth.get("status")
    if status not in AUTHORIZED_HEADROOM_STATUSES or status == "not_evaluated":
        raise ScenarioCompositionError(f"authorized_status_unrecognised:{status}")
    pool_id = auth.get("pool")
    _require(isinstance(pool_id, str) and bool(pool_id), "authorized_headroom: capacity names its pool id")
    if status in ("unknown", "contradicted", "invalid"):
        unknowns.append(
            _unknown(
                _identifier(f"authorized_headroom_{status}:{pool_id}", f"authorized_headroom_{status}"),
                f"capacity reports the authorized-share headroom pool {pool_id} as {status}",
                f"a capacity evaluation of {pool_id} that states the headroom",
                ("authorized_headroom",),
            )
        )
    return AuthorizedHeadroomDisclosure(
        status=status, pool_id=pool_id, capacity_status=status, note=None
    )


# ---------------------------------------------------------------------------
# §9 Identity and receipt
# ---------------------------------------------------------------------------


def _digest(receipt: CalculationReceipt) -> str:
    return sha256_of(receipt.as_record())


def _receipt(
    scenario: FinancingScenario,
    state: CapitalState,
    capacity_receipt: CalculationReceipt,
    supply_receipt: CalculationReceipt,
    funding_receipt: CalculationReceipt,
) -> tuple[str, CalculationReceipt]:
    capacity_digest = _digest(capacity_receipt)
    supply_digest = _digest(supply_receipt)
    funding_digest = _digest(funding_receipt)
    result_id = stable_id(
        "scenario_result",
        {
            "scenario_id": scenario.scenario_id,
            "state_id": state.state_id,
            "capacity_receipt_digest": capacity_digest,
            "supply_receipt_digest": supply_digest,
            "funding_receipt_digest": funding_digest,
        },
    )
    receipt = CalculationReceipt.build(
        inputs={
            "capacity_receipt_digest": capacity_digest,
            "supply_receipt_digest": supply_digest,
            "funding_receipt_digest": funding_digest,
            "scenario_id": scenario.scenario_id,
            "state_id": state.state_id,
        },
        rule_digest=sha256_of(
            sorted([capacity_receipt.rule_digest, supply_receipt.rule_digest, funding_receipt.rule_digest])
        ),
        implementation=IMPLEMENTATION,
        computed_at=scenario.as_of,
        scenario_id=scenario.scenario_id,
    )
    return result_id, receipt


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def explain_scenario(
    state: CapitalState,
    instruments: InstrumentSet,
    basis: ShareBasisResult,
    financials: FinancialInputs,
    commitments: CommitmentInputs,
    scenario: FinancingScenario,
    rules: RulePack,
    *,
    pack: Any = None,
    listing: ListingFact | None = None,
) -> ScenarioComposition:
    """Compose the three components and keep the material the checks were read from."""
    _preconditions(state, scenario)
    evaluation, trace, envelope, schedule = _run_components(
        state, instruments, basis, financials, commitments, scenario, rules, pack, listing
    )
    index = _index_actions(evaluation, scenario)
    checks = _action_checks(index)
    joint = _joint_check(index, checks, evaluation)
    trace_rows = {row["route_id"]: row for row in trace.get("rows", ())}
    cash_effects = {item.route_id: item for item in envelope.cash_effects}

    unknowns: list[Unknown] = []
    blockers: list[str] = []
    reconciliation = _reconcile(
        index, checks, trace_rows, cash_effects, schedule, scenario, unknowns, blockers
    )
    price_record = evaluation.inputs.get("price") or {}
    rows = tuple(
        _issuance_row(index, route_id, price_record, trace_rows, unknowns)
        for route_id in index.route_ids
    )
    low, high = _share_totals(rows)
    bases = _price_bases(price_record, trace, scenario)
    coverage = _coverage(schedule, index.route_ids, joint, scenario)
    authorized = _authorized_headroom(evaluation, unknowns)
    result_id, receipt = _receipt(
        scenario, state, evaluation.envelope.receipt, envelope.receipt, schedule.receipt
    )
    seen: set[str] = set()
    unique_unknowns: list[Unknown] = []
    for item in sorted(unknowns, key=lambda entry: entry.unknown_id):
        if item.unknown_id in seen:
            continue
        seen.add(item.unknown_id)
        unique_unknowns.append(item)
    result = ScenarioResult(
        result_id=result_id,
        scenario_id=scenario.scenario_id,
        state_id=state.state_id,
        scenario_view=scenario.view,
        state_view_mode=state.request.view_mode,
        as_of=scenario.as_of,
        capacity_envelope=evaluation.envelope,
        supply_envelope=envelope,
        funding_schedule=schedule,
        action_checks=checks,
        joint_check=joint,
        cash_reconciliation=reconciliation,
        issuance_rows=rows,
        scenario_new_shares_low=low,
        scenario_new_shares_high=high,
        price_bases=bases,
        coverage=coverage,
        authorized_headroom=authorized,
        receipt=receipt,
        blockers=tuple(sorted(set(blockers))),
        unknowns=tuple(unique_unknowns),
        notes=(SCENARIO_ISSUANCE_NOTE, COVERAGE_ONLY_NOTE, PRICE_BASIS_NOTE),
    )
    return ScenarioComposition(result=result, capacity=evaluation, supply_trace=trace, funding=schedule)


def compose_scenario(
    state: CapitalState,
    instruments: InstrumentSet,
    basis: ShareBasisResult,
    financials: FinancialInputs,
    commitments: CommitmentInputs,
    scenario: FinancingScenario,
    rules: RulePack,
    *,
    pack: Any = None,
    listing: ListingFact | None = None,
) -> ScenarioResult:
    """The composed :class:`ScenarioResult` for one scenario on one issuer state.

    The signature is exactly the ``INTERFACE_OWNERSHIP`` parameters (masterplan
    §9, pinned by the issuer-state-contracts interface test).  ``listing`` is the
    optional then-known listing fact (SPEC_G0 §2.4); with no listing the result
    is byte-identical to the result before G0.
    """
    return explain_scenario(
        state, instruments, basis, financials, commitments, scenario, rules, pack=pack, listing=listing
    ).result
