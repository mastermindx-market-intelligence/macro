"""Joint financing-constraint capacity (SPEC_C2 §2-§5, masterplan §13 row C2).

``capacity.py`` is a thin ADAPTER over the frozen joint kernel
:mod:`engine.capital_structure.capacity_joint`.  It reads an issuer state,
resolves the A15 usage / continuing-offering / programme-reservation /
programme-usage unknowns, the General Instruction I.B.6 baby-shelf pool and the
Nasdaq Rule 5635(d) 20% pool through the imported L0 rule text, hands the
resulting routes and pools to ``solve_joint`` and emits a C0
:class:`CapacityEnvelope`.

C2 adds the joint answer on top of the C1 gross ceiling: a price in effect
(``p_start`` for a takedown, the ATM window low/high for an at-the-market
programme, §2.1), per-route coefficients on the share pool (§2.2), programme
usage deducted exactly once (§2.3), mutually exclusive route groups (§2.4),
pessimistic / optimistic / ceiling branch solves (§2.5), asserted actions applied
as a fixed use that is never a cap (§2.6) and one aggregate with one witness and
its binding constraints (§2.7).

Nothing here re-implements optimisation, rule text, the public-float test or the
20% test; those are imported.  Arithmetic is exact (``Decimal``/``Fraction``)
and floats are refused.  An unknown stays unknown -- never ``0``, never
unlimited, never the gross registered amount -- and route maxima are never
summed across a shared pool because the kernel does the joint solve (A20, A21).
No score, rank, sizing, probability or proceeds is produced (A48): the aggregate
is GROSS dollar capacity, and ``fee_rate``/``discount_rate`` are recorded as
assumptions only.  An optimizer maximum is a capacity, never intent.  The
ceiling call (gross registered amount, L0 one-third limit) is reported in the
aggregate note and in ``inputs`` and is never the aggregate.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Mapping, Sequence

from engine.capital_structure import capacity_joint, rule_applicability
from engine.capital_structure.capacity_joint import (
    JointModelError,
    JointPool,
    JointRoute,
    JointSolution,
    decimal_floor,
    exact,
    solve_joint,
)
from engine.capital_structure.issuer_state_contracts import (
    CapacityEnvelope,
    CapitalState,
    CalculationReceipt,
    Constraint,
    ContractViolation,
    EvidenceRef,
    FinancingScenario,
    FundingSchedule,
    Provenance,
    Quantity,
    RouteBound,
    RulePack,
    Unknown,
    WitnessAllocation,
    _record,
    sha256_of,
)
from engine.capital_structure.rule_applicability import (
    FLOAT_MEASUREMENT_LOOKBACK_DAYS,
    RuleApplicabilityError,
    _twelve_month_window,
    baby_shelf_pool,
    build_rule_pack,
    load_rule_applicability_pack,
    nasdaq_twenty_percent,
    rule_status_as_of,
)
from engine.capital_structure.share_basis import _available_instant

IMPLEMENTATION = "capital_structure.capacity.c2_adapter.v1+" + capacity_joint.IMPLEMENTATION

#: Record schemas this adapter reads.  The registration-path producer (L1a) is
#: not imported: C1 dispatches on the schema string alone.
REGISTRATION_PATH_SCHEMA = "capital_structure.registration_path.v1"
DOCUMENT_TERM_SCHEMA = "capital_structure.document_term_observation.v1"
SHARE_COUNT_SCHEMAS = (
    "capital_structure.share_count_observation.v1",
    "capital_structure.share_count_observation.v2",
)
SHARE_BASIS_RESULT_SCHEMA = "capital_structure.share_basis_result.v2"

#: The fee-table row that carries the gross registered amount (SPEC_L1 §A.3).
FEE_TABLE_TERM_NAME = "proposed_maximum_aggregate_offering_price"

#: Mirrors of the L1a constants (SPEC_L1 §A.1); L1a is never imported by C1.
SHELF_FAMILIES = frozenset({"registration_s3", "registration_f3", "registration_f10"})
AUTOMATIC_SHELF_FORMS = frozenset({"S-3ASR", "F-3ASR", "POSASR"})

#: General Instruction I.B.6 (S-3) / I.B.5 (F-3) plus the I.B.1 eligibility
#: instruction each depends on, by base form.
BABY_SHELF_RULES: dict[str, tuple[str, str]] = {
    "S-3": ("form_s3.I.B.6", "form_s3.I.B.1"),
    "F-3": ("form_f3.I.B.5", "form_f3.I.B.1"),
}
NASDAQ_RULE_ID = "nasdaq.5635.d.1.B"
REFERENCE_PACK_MANIFEST_ID = "capital_structure.reference_pack.E0"

#: The A14 scenario assumptions that make Rule 5635(d) reachable at all.
NASDAQ_OFFERING_ASSUMPTIONS = {
    "listing_venue": "nasdaq",
    "exchange_offering_treatment": "non_public",
    "price_relative_to_minimum_price": "below",
}

ACTIVE_ROUTE_STATUSES = ("eligible", "conditional")

#: SPEC_C2 §2.5: the two price / programme-usage branches every solve runs over.
BRANCHES = ("pessimistic", "optimistic")

#: The ``other_assumptions`` key that declares mutually exclusive route groups.
ROUTE_EXCLUSIVITY_KEY = "route_exclusivity"


class CapacityInputError(ValueError):
    """A capacity input could not be read exactly as supplied."""


class CapacityRuleTextUnavailable(CapacityInputError):
    """No qualified rule text governs the sale date, so nothing may be claimed.

    ``unknowns`` carries every ``rule_text:`` unknown :func:`build_rule_pack`
    reported for that date.
    """

    unknowns: tuple[Unknown, ...] = ()

    def __init__(self, message: str, unknowns: Sequence[Unknown] = ()) -> None:
        super().__init__(message)
        self.unknowns = tuple(unknowns)


@dataclass(frozen=True)
class CapacityEvaluation:
    """One evaluation: the envelope, the exact digested inputs, both kernel runs."""

    envelope: CapacityEnvelope
    inputs: dict[str, Any]
    kernel: dict[str, Any]


def evaluate_capacity(
    state: CapitalState, scenario: FinancingScenario, rules: RulePack
) -> CapacityEnvelope:
    """The C0 capacity envelope for one issuer state under one scenario."""
    return explain_capacity(state, scenario, rules).envelope


def explain_capacity(
    state: CapitalState,
    scenario: FinancingScenario,
    rules: RulePack,
    *,
    pack: rule_applicability.RuleApplicabilityPack | None = None,
) -> CapacityEvaluation:
    """As :func:`evaluate_capacity`, plus the digested inputs and kernel records."""
    if pack is None:
        pack = load_rule_applicability_pack()
    try:
        return _Builder(state, scenario, rules, pack).run()
    except CapacityInputError:
        raise
    except (ContractViolation, JointModelError, RuleApplicabilityError) as exc:
        raise CapacityInputError(f"capacity input rejected: {exc}") from exc


def bind_funding_schedule(state: CapitalState, schedule: FundingSchedule) -> FundingSchedule:
    """Re-stamp a projected funding schedule with the issuer state's identity.

    Seat ruling 2026-10-14 (#9283 body): ``project_funding`` receives no
    ``CapitalState``, so its ``state_id`` names the funding inputs it consumed.
    Joining is C1's, and the join re-stamps the id.  A schedule computed at a
    different instant than the state's cutoff is refused rather than joined.
    """
    if not isinstance(state, CapitalState):
        raise CapacityInputError("bind_funding_schedule: a CapitalState is required")
    if not isinstance(schedule, FundingSchedule):
        raise CapacityInputError("bind_funding_schedule: a FundingSchedule is required")
    if schedule.scenario_id != schedule.receipt.scenario_id:
        raise CapacityInputError(
            "bind_funding_schedule: the schedule's receipt names scenario "
            f"{schedule.receipt.scenario_id!r}, not {schedule.scenario_id!r}"
        )
    computed_at = _utc(schedule.receipt.computed_at)
    as_of = _utc(state.request.as_of)
    if computed_at is None or as_of is None or computed_at != as_of:
        raise CapacityInputError(
            "bind_funding_schedule: the schedule was computed at "
            f"{schedule.receipt.computed_at!r}, not at the state cutoff "
            f"{state.request.as_of!r}; a different scenario cannot be joined"
        )
    return dataclasses.replace(schedule, state_id=state.state_id)


# ---------------------------------------------------------------------------
# Exact readers
# ---------------------------------------------------------------------------


def _utc(value: Any) -> datetime | None:
    """Aware-UTC instant for an ISO-8601 string; ``None`` when absent or naive."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _nested(body: Any, *keys: str) -> Any:
    node = body
    for key in keys:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if isinstance(value, bool) or isinstance(value, (int, float, Decimal, Fraction)):
        return None
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return "0" if Decimal(text) == 0 and text.startswith("-") else text


def _fraction_text(value: Fraction | None) -> str | None:
    return None if value is None else f"{value.numerator}/{value.denominator}"


def _money_text(value: Fraction | None) -> str | None:
    """Decimal text for an exact money ``Fraction``; these are always Decimal-derived."""
    if value is None:
        return None
    return _decimal_text(Decimal(value.numerator) / Decimal(value.denominator))


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _span_refs(spans: Any) -> tuple[EvidenceRef, ...]:
    """Retained-byte references for ``evidence.spans[]``; malformed spans are dropped."""
    out: list[EvidenceRef] = []
    for span in _sequence(spans):
        if not isinstance(span, Mapping):
            continue
        manifest_id = _text(span.get("manifest_id"))
        span_id = _text(span.get("span_id"))
        text_sha256 = _text(span.get("text_sha256"))
        if manifest_id is None or span_id is None or text_sha256 is None:
            continue
        try:
            out.append(EvidenceRef(manifest_id, span_id, text_sha256))
        except ContractViolation:
            continue
    return _unique_refs(out)


def _unique_refs(refs: Sequence[EvidenceRef]) -> tuple[EvidenceRef, ...]:
    ordered: dict[tuple[str, str, str], EvidenceRef] = {}
    for ref in refs:
        ordered.setdefault((ref.manifest_id, ref.span_id, ref.text_sha256), ref)
    return tuple(ordered[key] for key in sorted(ordered))


def _conditions(*groups: Any) -> tuple[str, ...]:
    out = set()
    for group in groups:
        for item in group or ():
            if isinstance(item, str) and item.strip():
                out.add(item.strip())
    return tuple(sorted(out))


def _unknown(
    unknown_id: str, description: str, resolving_fact: str, affects: Sequence[str] = ()
) -> Unknown:
    return Unknown(
        unknown_id=unknown_id,
        description=description,
        resolving_fact=resolving_fact,
        affects=tuple(sorted({item for item in affects if item})),
    )


def _dedupe_unknowns(unknowns: Sequence[Unknown]) -> tuple[Unknown, ...]:
    """Unique unknown ids, first wins, sorted by id (the envelope requires uniqueness)."""
    seen: dict[str, Unknown] = {}
    for item in sorted(unknowns, key=lambda entry: entry.unknown_id):
        seen.setdefault(item.unknown_id, item)
    return tuple(seen[key] for key in sorted(seen))


@dataclass(frozen=True)
class _Observation:
    """One then-known record with the instant it became available."""

    schema: str
    available: datetime
    body: dict[str, Any]
    digest: str


@dataclass(frozen=True)
class _StateRead:
    paths: tuple[_Observation, ...]
    fee_rows: tuple[_Observation, ...]
    share_counts: tuple[_Observation, ...]
    share_basis_results: tuple[_Observation, ...]
    ignored_schemas: tuple[str, ...]
    excluded_after_as_of: tuple[tuple[str, int], ...]


def _read_records(state: CapitalState, cutoff: datetime) -> _StateRead:
    """Every record of every family, dispatched on ``schema``, then-known filtered.

    A record whose available instant is after the cutoff -- or carries none at
    all -- is excluded and counted; it is never used (A05).
    """
    paths: list[_Observation] = []
    fee_rows: list[_Observation] = []
    share_counts: list[_Observation] = []
    share_results: list[_Observation] = []
    ignored: set[str] = set()
    excluded: Counter[str] = Counter()
    for family in sorted(state.families, key=lambda item: item.family):
        for body in family.records:
            raw_schema = body.get("schema")
            schema = raw_schema if isinstance(raw_schema, str) and raw_schema else "<missing>"
            if schema == REGISTRATION_PATH_SCHEMA:
                available = _utc(_nested(body, "origin", "mastermind_available_at"))
            elif schema == DOCUMENT_TERM_SCHEMA:
                available = _utc(_nested(body, "point_in_time", "source_available_at")) or _utc(
                    _nested(body, "filing", "accepted_at")
                )
            elif schema in SHARE_COUNT_SCHEMAS:
                available = _available_instant(body)
            elif schema == SHARE_BASIS_RESULT_SCHEMA:
                available = _utc(body.get("as_of"))
            else:
                ignored.add(schema)
                continue
            if available is None or available > cutoff:
                excluded[schema] += 1
                continue
            observation = _Observation(schema, available, dict(body), sha256_of(_record(body)))
            if schema == REGISTRATION_PATH_SCHEMA:
                paths.append(observation)
            elif schema == DOCUMENT_TERM_SCHEMA:
                fee_rows.append(observation)
            elif schema in SHARE_COUNT_SCHEMAS:
                share_counts.append(observation)
            else:
                share_results.append(observation)

    def order(items: list[_Observation]) -> tuple[_Observation, ...]:
        return tuple(sorted(items, key=lambda item: (item.available, item.digest)))

    return _StateRead(
        paths=order(paths),
        fee_rows=order(fee_rows),
        share_counts=order(share_counts),
        share_basis_results=order(share_results),
        ignored_schemas=tuple(sorted(ignored)),
        excluded_after_as_of=tuple(sorted(excluded.items())),
    )


def _form_of(body: Mapping[str, Any]) -> str | None:
    for source in ("registration", "origin"):
        value = _text(_nested(body, source, "form"))
        if value is not None:
            return value.upper()
    return None


@dataclass(frozen=True)
class _ShelfPath:
    """One shelf registration path, classified against Rule 415 and its own predicates."""

    path_id: str
    body: dict[str, Any]
    predicates: dict[str, Any]
    form: str | None
    family: str | None
    automatic: bool
    shelf: bool
    window_start: str | None
    window_end: str | None
    classification: str
    reason: str
    base_conditions: tuple[str, ...]
    ineligible_conditions: tuple[str, ...]
    accessions: tuple[str, ...]
    available: datetime
    takedown_id: str


@dataclass(frozen=True)
class _FeeTable:
    registered: Quantity
    gross: Fraction | None
    evidence: tuple[EvidenceRef, ...]
    accession: str | None
    available: datetime | None
    unknowns: tuple[Unknown, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class _Registered:
    """The A15 resolution of one path: pool bound, both route limits, ceiling substitute."""

    pool_id: str
    bound: Quantity
    evidence: tuple[EvidenceRef, ...]
    applicability: str
    substitute: Fraction | None
    usage: Any
    continuing: Any
    reservation: Any
    takedown_limit: Quantity
    takedown_applicability: str | None
    atm_limit: Quantity | None
    atm_applicability: str | None
    has_atm: bool


@dataclass(frozen=True)
class _Pool:
    pool_id: str
    kind: str
    stock_or_flow: str
    bound: Quantity
    shared_by: tuple[str, ...]
    applicability: str | None
    evidence: tuple[EvidenceRef, ...]
    window_start: str | None
    window_end: str | None
    coefficient: Fraction
    substitute: Fraction | None
    #: SPEC_C2 §2.2: ``(route_id, branch, coefficient text)`` rows that override
    #: ``coefficient`` for one route in one price branch.  Fixed pricing emits
    #: none, so the C1 kernel input is byte-identical.
    route_coefficients: tuple[tuple[str, str, str], ...] = ()

    def coefficient_for(self, route_id: str, branch: str) -> Fraction:
        """The coefficient this pool charges ``route_id`` in ``branch``."""
        for row_route, row_branch, row_value in self.route_coefficients:
            if row_route == route_id and row_branch == branch:
                return Fraction(row_value)
        return self.coefficient


@dataclass(frozen=True)
class _PriceView:
    """SPEC_C2 §2.1: the price in effect, the takedown price and the ATM window.

    ``p_start`` prices a takedown (a sale already scheduled at the horizon
    start); ``low``/``high`` bound an at-the-market programme whose sale dates
    inside the window are not known.  All three are ``None`` when a price path
    carries no point on or before the horizon start -- an uncovered path is an
    unknown, never a guessed price.
    """

    kind: str
    currency: str
    fixed_price: str | None
    path: tuple[tuple[str, str], ...]
    p_start: Fraction | None
    low: Fraction | None
    high: Fraction | None
    window_dates: tuple[str, ...]
    uncovered: bool
    branching: bool


@dataclass(frozen=True)
class _UsageView:
    """SPEC_C2 §2.3: one path's programme usage and its two branch substitutes."""

    path_id: str
    status: str
    value: Fraction | None
    pessimistic: Fraction | None
    optimistic: Fraction | None
    atm_limit: dict[str, Fraction]
    pool_bound: dict[str, Fraction]


@dataclass(frozen=True)
class _ActionView:
    """SPEC_C2 §2.6: one asserted action, priced per branch."""

    route_id: str
    action: str
    settlement: str
    fixed: bool
    applied: bool
    usd: dict[str, Fraction]
    conditions_assumed_met: tuple[str, ...]


@dataclass(frozen=True)
class _RoutePlan:
    route_id: str
    route_kind: str
    limit: Quantity
    status: str
    conditions: tuple[str, ...]
    consumes: tuple[str, ...]
    applicability: str | None
    evidence: tuple[EvidenceRef, ...]


def _unknown_bound(unit: str, note: str, share_basis: str | None = None) -> Quantity:
    if unit == "shares":
        return Quantity.unknown(unit, share_basis=share_basis or "issued_and_outstanding", note=note)
    return Quantity.unknown(unit, note=note)


class _Builder:
    """One ``explain_capacity`` call: read, resolve, solve twice, emit."""

    def __init__(
        self,
        state: CapitalState,
        scenario: FinancingScenario,
        rules: RulePack,
        pack: rule_applicability.RuleApplicabilityPack,
    ) -> None:
        if not isinstance(state, CapitalState):
            raise CapacityInputError("state: a CapitalState is required")
        if not isinstance(scenario, FinancingScenario):
            raise CapacityInputError("scenario: a FinancingScenario is required")
        if not isinstance(rules, RulePack):
            raise CapacityInputError("rules: a RulePack is required")
        if not isinstance(pack, rule_applicability.RuleApplicabilityPack):
            raise CapacityInputError("pack: a RuleApplicabilityPack is required")
        cutoff = _utc(state.request.as_of)
        scenario_as_of = _utc(scenario.as_of)
        if cutoff is None or scenario_as_of is None or cutoff != scenario_as_of:
            raise CapacityInputError(
                f"scenario.as_of {scenario.as_of!r} is not the state cutoff {state.request.as_of!r}"
            )
        sale_date = _day(scenario.horizon_start)
        cutoff_day = _day(state.request.as_of[:10])
        if sale_date is None or cutoff_day is None:
            raise CapacityInputError(
                f"scenario.horizon_start {scenario.horizon_start!r} is not an ISO date"
            )
        if sale_date < cutoff_day:
            raise CapacityInputError(
                f"scenario.horizon_start {scenario.horizon_start!r} precedes the state cutoff "
                f"{state.request.as_of[:10]!r}"
            )
        built, rule_unknowns, rule_conditions, rule_excluded = build_rule_pack(pack, sale_date.isoformat())
        if built is None:
            raise CapacityRuleTextUnavailable(
                f"no qualified rule text is in force on {sale_date.isoformat()}; "
                "financing capacity cannot be evaluated",
                rule_unknowns,
            )
        if built.digest != rules.digest:
            raise CapacityInputError(
                f"rule pack does not match the rule text in force on {sale_date.isoformat()}"
            )
        self.state = state
        self.scenario = scenario
        self.rules = rules
        self.pack = pack
        self.cutoff = cutoff
        self.sale_date = sale_date
        self.sale_iso = sale_date.isoformat()
        self.rule_unknowns = tuple(rule_unknowns)
        self.rule_conditions = tuple(rule_conditions)
        self.rule_excluded = tuple(rule_excluded)
        self.rule_unknown_by_id = {item.unknown_id: item for item in rule_unknowns}
        self.resolutions = {item.unknown_id: item for item in scenario.unknown_resolutions}
        self.assumptions = dict(scenario.other_assumptions)
        self.unknowns: list[Unknown] = []
        self.blockers: list[str] = []
        self.absent_rules: set[str] = set()
        self.path_rules: dict[str, set[str]] = {}
        self.path_conditions: dict[str, set[str]] = {}
        self.route_conditions: dict[str, set[str]] = {}
        self.paths: list[_ShelfPath] = []
        self.fee: dict[str, _FeeTable] = {}
        self.registered: dict[str, _Registered] = {}
        self.pools: list[_Pool] = []
        self.route_plans: list[_RoutePlan] = []
        self.baby_shelf_inputs: dict[str, Any] | None = None
        self.nasdaq_inputs: dict[str, Any] | None = None
        self.read: _StateRead | None = None
        self.price_view: _PriceView | None = None
        self.price_branch_routes: tuple[str, ...] = ()
        self.usage_views: dict[str, _UsageView] = {}
        self.programme_usage_inputs: dict[str, Any] = {}
        self.exclusive_declared: tuple[tuple[str, ...], ...] = ()
        self.exclusive_groups: tuple[tuple[str, ...], ...] = ()
        self.exclusive_dropped: tuple[str, ...] = ()
        self.exclusive_not_passed: tuple[tuple[str, ...], ...] = ()
        self.action_views: dict[str, _ActionView] = {}
        self.residual_routes: dict[str, dict[str, Fraction | None]] = {
            branch: {} for branch in BRANCHES
        }
        self.residual_pools: dict[str, dict[str, Fraction | None]] = {
            branch: {} for branch in BRANCHES
        }
        self.fixed_totals: dict[str, Fraction] = {branch: Fraction(0) for branch in BRANCHES}
        self.infeasible: dict[str, set[str]] = {branch: set() for branch in BRANCHES}
        self.contradiction: str | None = None
        self.branch_infeasible_on_one = False
        self.branching = False
        self.branch_reasons: tuple[str, ...] = ()

    # -- entry point ------------------------------------------------------

    def run(self) -> CapacityEvaluation:
        self.read = _read_records(self.state, self.cutoff)
        self.paths = sorted((self._path_view(item) for item in self.read.paths), key=lambda p: p.path_id)
        seen: set[str] = set()
        for path in self.paths:
            if path.path_id in seen:
                raise CapacityInputError(f"registration path {path.path_id!r} appears more than once")
            seen.add(path.path_id)
        self._price_view()
        if not self.paths:
            self.unknowns.append(
                _unknown(
                    f"registration_paths:{self.state.request.issuer_id}",
                    "the state carries no registration path record, so no financing route is known",
                    "a compiled capital_structure.registration_path.v1 record for this issuer at the cutoff",
                    (self.state.request.issuer_id,),
                )
            )
            self.blockers.append("no_registration_path_in_state")
        else:
            for path in self.paths:
                self.fee[path.path_id] = self._fee_table(path)
                self.unknowns.extend(self.fee[path.path_id].unknowns)
                self.blockers.extend(self.fee[path.path_id].blockers)
            self._registered_pools()
            self._baby_shelf_pool()
            self._nasdaq_pool()
            self._route_plans()
            if not any(plan.status in ACTIVE_ROUTE_STATUSES for plan in self.route_plans):
                # Every path is ineligible or unresolved: the contract refuses a
                # known aggregate with no active route, so the aggregate is
                # unknown and names why.
                self.blockers.append("no_active_route")
        self._finalize_branching()
        self._exclusive_groups()
        self._apply_actions()
        pessimistic, optimistic, ceiling = self._solve()
        active = tuple(sorted(
            plan.route_id for plan in self.route_plans if plan.status in ACTIVE_ROUTE_STATUSES
        ))
        pools = self._constraints(pessimistic, active)
        routes = self._routes()
        aggregate = self._aggregate(pessimistic, optimistic, ceiling, active, routes, pools)
        witness = self._witness(pessimistic, active)
        unknown_constraints = tuple(sorted(pool.constraint_id for pool in pools if pool.bound.status != "known"))
        inputs = self._inputs(pessimistic, optimistic, ceiling, routes, pools)
        receipt = CalculationReceipt.build(
            inputs=inputs,
            rule_digest=self.rules.digest,
            implementation=IMPLEMENTATION,
            computed_at=self.state.generated_at,
            scenario_id=self.scenario.scenario_id,
        )
        envelope = CapacityEnvelope(
            state_id=self.state.state_id,
            scenario_id=self.scenario.scenario_id,
            rule_pack_digest=self.rules.digest,
            routes=routes,
            aggregate_bound=aggregate,
            receipt=receipt,
            shared_pools=pools,
            binding_constraints=tuple(sorted(pessimistic.binding)) if pessimistic.determined and active else (),
            unknown_constraints=unknown_constraints,
            mutually_exclusive=self.exclusive_groups,
            feasible_witness=witness,
            blockers=tuple(sorted(set(self.blockers))),
            unknowns=_dedupe_unknowns(self.unknowns),
        )
        kernel: dict[str, Any] = {
            "evidence": pessimistic.as_record(),
            "ceiling": ceiling.as_record(),
        }
        if optimistic is not None:
            kernel["optimistic"] = optimistic.as_record()
        return CapacityEvaluation(
            envelope=envelope,
            inputs=inputs,
            kernel=kernel,
        )

    # -- one registration path -------------------------------------------

    def _path_view(self, observation: _Observation) -> _ShelfPath:
        body = observation.body
        path_id = _text(body.get("path_id"))
        if path_id is None:
            raise CapacityInputError(f"{REGISTRATION_PATH_SCHEMA}: path_id required")
        compiled_at = _utc(body.get("as_of"))
        if compiled_at is None or compiled_at != self.cutoff:
            raise CapacityInputError(
                f"registration path {path_id!r} was compiled for {body.get('as_of')!r}, "
                f"not the state cutoff {self.state.request.as_of!r}"
            )
        raw_predicates = body.get("predicates")
        if not isinstance(raw_predicates, Mapping):
            raise CapacityInputError(f"registration path {path_id!r}: predicates block required")
        predicates = {
            key: value for key, value in raw_predicates.items() if isinstance(value, Mapping)
        }
        window = predicates.get("shelf_window") or {}
        position = _text(window.get("position"))
        withdrawn = predicates.get("withdrawn") or {}
        effect = predicates.get("effect_observed") or {}
        automatic_effectiveness = predicates.get("automatic_effectiveness") or {}
        form = _form_of(body)
        family = _text(_nested(body, "registration", "registration_family"))
        automatic = form is not None and form in AUTOMATIC_SHELF_FORMS
        if _text(withdrawn.get("status")) == "observed":
            classification = "ineligible"
            reason = _text(withdrawn.get("reason")) or "withdrawn_observed"
        elif position == "after_window_end":
            classification = "ineligible"
            reason = _text(window.get("reason")) or "after_window_end"
        elif _text(window.get("status")) == "unknown":
            classification = "unknown"
            reason = _text(window.get("reason")) or "shelf_window_unknown"
        elif _text(effect.get("status")) != "observed" and _text(
            automatic_effectiveness.get("status")
        ) != "conditional":
            classification = "unknown"
            reason = (
                _text(effect.get("reason")) or "registration_effectiveness_not_observed"
            )
        elif position != "inside_window":
            classification = "unknown"
            reason = f"shelf_window_not_inside_window:{_text(window.get('status')) or 'absent'}"
        else:
            classification = "conditional"
            reason = _text(window.get("reason")) or "inside_window"
        base = {
            "offering_role_unknown",
            "exchange_public_offering_treatment_undetermined",
            "issuer_facts_not_verified:exchange_listed_common_equity",
            "issuer_facts_not_verified:shell_company_history",
        }
        base.update(_conditions(_sequence(window.get("conditions"))))
        if automatic:
            base.add("wksi_status_not_evaluated")
        accessions: list[str] = []
        origin_accession = _text(_nested(body, "origin", "accession"))
        if origin_accession is not None:
            accessions.append(origin_accession)
        for amendment in _sequence(body.get("amendment_chain")):
            accession = _text(_nested(amendment, "accession")) if isinstance(amendment, Mapping) else None
            if accession is not None:
                accessions.append(accession)
        consulted: set[str] = set()
        for predicate in predicates.values():
            for rule_id in _sequence(predicate.get("rule_ids")):
                if isinstance(rule_id, str) and rule_id:
                    consulted.add(rule_id)
        self.path_rules[path_id] = consulted
        self.path_conditions[path_id] = set()
        self.route_conditions.setdefault(f"shelf_takedown:{path_id}", set())
        self.route_conditions.setdefault(f"at_the_market:{path_id}", set())
        return _ShelfPath(
            path_id=path_id,
            body=dict(body),
            predicates=predicates,
            form=form,
            family=family,
            automatic=automatic,
            shelf=family is not None and family in SHELF_FAMILIES,
            window_start=_day(window.get("window_start")).isoformat() if _day(window.get("window_start")) else None,
            window_end=_day(window.get("window_end")).isoformat() if _day(window.get("window_end")) else None,
            classification=classification,
            reason=reason,
            base_conditions=tuple(sorted(base)),
            ineligible_conditions=_conditions((reason,), _sequence(window.get("conditions"))),
            accessions=tuple(sorted(set(accessions))),
            available=observation.available,
            takedown_id=f"shelf_takedown:{path_id}",
        )

    def _resolution(self, unknown_id: str) -> Any:
        """One supplied A15/baby-shelf resolution, or ``None`` when not supplied."""
        resolution = self.resolutions.get(unknown_id)
        if resolution is None:
            return None
        assumed = resolution.assumed
        if assumed.unit != "usd" or assumed.status != "known" or assumed.value is None:
            raise CapacityInputError(
                f"unknown resolution {unknown_id!r} must supply a known usd amount, "
                f"got unit {assumed.unit!r} status {assumed.status!r}"
            )
        return resolution

    def _route_ids(self, path: _ShelfPath) -> tuple[str, ...]:
        if path.classification == "ineligible":
            return ()
        if path.classification == "unknown":
            return (path.takedown_id,)
        registered = self.registered[path.path_id]
        if registered.has_atm:
            return (path.takedown_id, f"at_the_market:{path.path_id}")
        return (path.takedown_id,)

    # -- §5 the fee table -------------------------------------------------

    def _fee_table(self, path: _ShelfPath) -> _FeeTable:
        rows: list[tuple[_Observation, str]] = []
        for observation in self.read.fee_rows:  # type: ignore[union-attr]
            body = observation.body
            if _text(_nested(body, "term", "name")) != FEE_TABLE_TERM_NAME:
                continue
            if _text(_nested(body, "state", "disposition")) != "observed":
                continue
            normalized = body.get("normalized") if isinstance(body.get("normalized"), Mapping) else {}
            currency = _text(normalized.get("currency"))
            if currency is None or currency.upper() != "USD":
                continue
            raw_scale = normalized.get("scale")
            scale = _decimal_or_none(raw_scale if isinstance(raw_scale, str) else str(raw_scale))
            if scale is None or scale != 1:
                continue
            accession = _text(_nested(body, "filing", "accession"))
            if accession is None or accession not in path.accessions:
                continue
            rows.append((observation, accession))

        def missing(
            note: str,
            unknowns: tuple[Unknown, ...] = (),
            blockers: tuple[str, ...] = (),
            status: str = "unknown",
        ) -> _FeeTable:
            quantity = (
                _unknown_bound("usd", note)
                if status == "unknown"
                else Quantity(unit="usd", status=status, value=None, note=note)
            )
            if not unknowns:
                unknowns = (
                    _unknown(
                        f"registered_amount:{path.path_id}",
                        f"the gross registered amount under {path.path_id} is not known: {note}",
                        "a single observed proposed_maximum_aggregate_offering_price fee-table row "
                        f"for {path.path_id} at the cutoff",
                        (path.path_id,),
                    ),
                )
            return _FeeTable(quantity, None, (), None, None, unknowns, blockers)

        if not rows:
            return missing("no fee-table row for this registration is then-known")
        latest = max(rows, key=lambda item: (item[0].available, item[1]))
        accession = latest[1]
        group = [item for item in rows if item[1] == accession]
        refs = _unique_refs(
            [ref for item in group for ref in _span_refs(_nested(item[0].body, "evidence", "spans"))]
        )
        available = max(item[0].available for item in group)
        contradicted = any(
            _sequence(_nested(item[0].body, "relationships", "contradiction_ids")) for item in group
        )
        if contradicted:
            # SPEC_C1 §5: a contradicted fee table is reported as contradicted,
            # never as merely unknown and never as a known amount.
            return missing(
                f"the fee-table rows of {accession} carry a contradiction",
                blockers=(f"fee_table_contradicted:{accession}",),
                status="contradicted",
            )
        if len(group) > 1:
            return missing(
                f"{len(group)} fee-table rows in {accession} disagree about the registered amount",
                blockers=(f"fee_table_multi_row:{accession}",),
            )
        value = _decimal_or_none(_nested(group[0][0].body, "normalized", "value"))
        if value is None or value < 0:
            return missing(
                f"the fee-table value of {accession} is not a nonnegative decimal",
                blockers=(f"fee_table_value_not_decimal:{accession}",),
            )
        if not refs:
            return missing(
                f"the fee-table row of {accession} retains no span evidence",
                blockers=(f"fee_table_evidence_missing:{accession}",),
            )
        quantity = Quantity.known(
            _decimal_text(value),
            "usd",
            applicability=f"{FEE_TABLE_TERM_NAME} as filed in {accession}",
            provenance=Provenance(
                "document_terms", available_at=_iso(available), evidence=refs
            ),
        )
        return _FeeTable(quantity, Fraction(value), refs, accession, available, (), ())

    # -- §6 A15 deductions ------------------------------------------------

    def _pool_after_usage(
        self,
        path_id: str,
        bound: Quantity,
        programme: Any,
        applicability: str,
        provenance: Provenance | None,
        blockers: list[str],
    ) -> Quantity:
        """§2.3: the registered pool bound less a RESOLVED programme usage (R-U-C-P).

        An unresolved usage changes nothing here -- it is never read as zero.  A
        bound that is not known cannot be deducted from, so it is returned as it
        stands.  ``U``, ``C`` and ``P`` are flows already deducted once, and the
        takedown limit never carries ``P`` when a reservation splits the pool (A15).
        """
        if programme is None or bound.status != "known":
            return bound
        assert bound.decimal is not None
        net = bound.decimal - programme.assumed.decimal
        if net < 0:
            blockers.append(f"registered_overrun:{path_id}")
            return Quantity(
                unit="usd",
                status="contradicted",
                note=(
                    f"completed takedowns, the continuing-offering reservation and the programme "
                    f"sales under {path_id} exceed the gross registered amount by {_decimal_text(-net)}"
                ),
            )
        return Quantity.known(
            _decimal_text(net), "usd", applicability=applicability, provenance=provenance
        )

    def _programme_usage_split(
        self,
        path_id: str,
        pool_id: str,
        *,
        remaining: Decimal | None,
        reserved: Decimal,
        programme: Any,
        atm_applicability: str,
        applicability: str,
        provenance: Provenance | None,
        reservation_id: str,
        blockers: list[str],
    ) -> tuple[Quantity, Quantity | None, _UsageView]:
        """§2.3: the at-the-market limit ``S-P``, the pool bound ``R-U-C-P`` and the
        two branch substitutes for an unresolved ``P``.

        ``remaining`` is ``R-U-C``, or ``None`` when it is not known; a ``None``
        bound in the result means "leave the caller's bound alone".  ``P`` is never
        zero when it is unresolved: the pessimistic branch substitutes ``P = S``
        (nothing left to sell) and the optimistic branch ``P = 0``.
        """
        atm_id = f"at_the_market:{path_id}"
        reserved_fraction = Fraction(reserved)
        if programme is None:
            self.unknowns.append(
                _unknown(
                    f"programme_usage:{path_id}",
                    f"the gross dollars already sold under the at-the-market programme reserved "
                    f"under {path_id} are not known",
                    "the gross dollars already sold under the at-the-market programme within the "
                    "reservation",
                    (atm_id, path_id, pool_id),
                )
            )
            atm_limit = _unknown_bound(
                "usd",
                f"the programme usage under {path_id} is unresolved, so the at-the-market limit "
                "S-P is not known; it is never zero and never the whole reservation",
            )
            bound = (
                None
                if remaining is None
                else _unknown_bound(
                    "usd",
                    f"the programme usage under {path_id} is unresolved, so the registered amount "
                    "remaining R-U-C-P is not known; the gross registered amount is a ceiling "
                    "substitute only",
                )
            )
            view = _UsageView(
                path_id=path_id,
                status="unresolved",
                value=None,
                pessimistic=reserved_fraction,
                optimistic=Fraction(0),
                atm_limit={"pessimistic": Fraction(0), "optimistic": reserved_fraction},
                pool_bound=(
                    {}
                    if remaining is None
                    else {
                        "pessimistic": Fraction(remaining) - reserved_fraction,
                        "optimistic": Fraction(remaining),
                    }
                ),
            )
            return atm_limit, bound, view
        used = programme.assumed.decimal
        used_fraction = Fraction(used)
        if used_fraction > reserved_fraction:
            blockers.append(f"programme_usage_exceeds_reservation:{path_id}")
            atm_limit = Quantity(
                unit="usd",
                status="contradicted",
                note=(
                    f"the gross dollars sold under the at-the-market programme exceed the "
                    f"reservation under {path_id} by {_decimal_text(used - reserved)}"
                ),
            )
        else:
            atm_limit = Quantity.known(
                _decimal_text(reserved - used),
                "usd",
                applicability=atm_applicability,
                note=f"scenario resolution {reservation_id} less {programme.unknown_id}",
            )
        bound = (
            None
            if remaining is None
            else self._pool_after_usage(
                path_id,
                Quantity.known(_decimal_text(remaining), "usd"),
                programme,
                applicability,
                provenance,
                blockers,
            )
        )
        view = _UsageView(
            path_id=path_id,
            status="known",
            value=used_fraction,
            pessimistic=used_fraction,
            optimistic=used_fraction,
            atm_limit={},
            pool_bound={},
        )
        return atm_limit, bound, view

    def _record_programme_usage(self, path_id: str, view: _UsageView | None, programme: Any) -> None:
        """``inputs["programme_usage"][path]`` (§2.3): status, value and both substitutes."""
        if view is not None:
            if view.status == "unresolved":
                self.usage_views[path_id] = view
            self.programme_usage_inputs[path_id] = {
                "status": view.status,
                "value": _money_text(view.value),
                "pessimistic": _money_text(view.pessimistic),
                "optimistic": _money_text(view.optimistic),
            }
            return
        if programme is not None:
            used = Fraction(programme.assumed.decimal)
            self.programme_usage_inputs[path_id] = {
                "status": "known",
                "value": _money_text(used),
                "pessimistic": _money_text(used),
                "optimistic": _money_text(used),
            }

    def _registered_pools(self) -> None:
        for path in self.paths:
            if path.classification == "ineligible":
                continue
            path_id = path.path_id
            fee = self.fee[path_id]
            usage = self._resolution(f"shelf_usage:{path_id}")
            continuing = self._resolution(f"continuing_offering:{path_id}")
            reservation = self._resolution(f"programme_reservation:{path_id}")
            programme = self._resolution(f"programme_usage:{path_id}")
            pool_id = f"registered:{path_id}"
            applicability = (
                f"registered class under {path_id}: the gross registered amount less completed "
                "takedowns excluding programme sales and less the continuing-offering reservation (A15)"
            )
            window_text = (
                f" inside window {path.window_start}..{path.window_end}"
                if path.window_start and path.window_end
                else ""
            )
            takedown_applicability = f"shelf_takedown under {path_id}{window_text}"
            atm_applicability = f"at_the_market programme reservation under {path_id}{window_text}"
            provenance = (
                Provenance(
                    "document_terms",
                    available_at=_iso(fee.available) if fee.available is not None else None,
                    evidence=fee.evidence,
                )
                if fee.available is not None
                else None
            )
            blockers: list[str] = []
            substitute = fee.gross
            if fee.registered.status == "known" and usage is not None and continuing is not None:
                assert fee.registered.decimal is not None
                net = fee.registered.decimal - usage.assumed.decimal - continuing.assumed.decimal
                assert net is not None
                if net < 0:
                    bound = Quantity(
                        unit="usd",
                        status="contradicted",
                        note=(
                            f"completed takedowns and the continuing-offering reservation exceed the "
                            f"gross registered amount under {path_id} by {_decimal_text(-net)}"
                        ),
                    )
                    blockers.append(f"registered_overrun:{path_id}")
                else:
                    bound = Quantity.known(
                        _decimal_text(net), "usd", applicability=applicability, provenance=provenance
                    )
            else:
                reasons = []
                if fee.registered.status != "known":
                    reasons.append("the gross registered amount")
                if usage is None:
                    reasons.append("completed takedowns excluding programme sales")
                    self.unknowns.append(
                        _unknown(
                            f"shelf_usage:{path_id}",
                            f"the amount already taken down under {path_id} is not known",
                            f"the 424B/8-K takedown history of {path_id} through {self.sale_iso}",
                            (path_id,),
                        )
                    )
                if continuing is None:
                    reasons.append("the continuing-offering reservation")
                    self.unknowns.append(
                        _unknown(
                            f"continuing_offering:{path_id}",
                            f"the amount reserved for a continuing offering under {path_id} is not known",
                            f"the 424B/8-K takedown history of {path_id} through {self.sale_iso}",
                            (path_id,),
                        )
                    )
                bound = _unknown_bound(
                    "usd",
                    "the registered amount remaining under "
                    f"{path_id} is not known: {' and '.join(reasons) or 'a deduction'} "
                    "is unresolved; the gross registered amount is a ceiling substitute only",
                )
            takedown_limit = bound
            atm_limit: Quantity | None = None
            has_atm = False
            usage_view: _UsageView | None = None
            if path.classification == "unknown":
                takedown_limit = _unknown_bound(
                    "usd",
                    f"registration effectiveness under {path_id} is unresolved: {path.reason}",
                )
                # §2.3: a resolved programme usage is a flow already sold, so it
                # comes off the pool once even when no reservation is evaluated.
                bound = self._pool_after_usage(
                    path_id, bound, programme, applicability, provenance, blockers
                )
            elif reservation is not None and bound.status == "known":
                assert bound.decimal is not None
                split = bound.decimal - reservation.assumed.decimal
                if split < 0:
                    bound = Quantity(
                        unit="usd",
                        status="contradicted",
                        note=(
                            f"the programme reservation under {path_id} exceeds the registered amount "
                            f"remaining by {_decimal_text(-split)}"
                        ),
                    )
                    blockers.append(f"programme_reservation_overrun:{path_id}")
                    takedown_limit = _unknown_bound(
                        "usd", f"the programme reservation exceeds the amount remaining under {path_id}"
                    )
                    # No at-the-market route survives an impossible split, so §2.3
                    # emits no programme_usage unknown and deducts nothing twice.
                else:
                    takedown_limit = Quantity.known(
                        _decimal_text(split),
                        "usd",
                        applicability=takedown_applicability,
                        provenance=provenance,
                    )
                    atm_limit, pool_bound, usage_view = self._programme_usage_split(
                        path_id,
                        pool_id,
                        remaining=bound.decimal,
                        reserved=reservation.assumed.decimal,
                        programme=programme,
                        atm_applicability=atm_applicability,
                        applicability=applicability,
                        provenance=provenance,
                        reservation_id=reservation.unknown_id,
                        blockers=blockers,
                    )
                    if pool_bound is not None:
                        bound = pool_bound
                    has_atm = True
            elif reservation is not None:
                takedown_limit = _unknown_bound(
                    "usd", f"the registered amount remaining under {path_id} is not known"
                )
                atm_limit, pool_bound, usage_view = self._programme_usage_split(
                    path_id,
                    pool_id,
                    remaining=None,
                    reserved=reservation.assumed.decimal,
                    programme=programme,
                    atm_applicability=atm_applicability,
                    applicability=applicability,
                    provenance=provenance,
                    reservation_id=reservation.unknown_id,
                    blockers=blockers,
                )
                if pool_bound is not None:
                    bound = pool_bound
                has_atm = True
            elif bound.status == "known":
                # §2.3: with no reservation evaluated, a resolved programme usage
                # is deducted from the pool AND from the takedown limit (R-U-C-P).
                bound = self._pool_after_usage(
                    path_id, bound, programme, applicability, provenance, blockers
                )
                if bound.status == "known":
                    takedown_limit = Quantity.known(
                        bound.value, "usd", applicability=takedown_applicability, provenance=provenance
                    )
                else:
                    takedown_limit = bound
                self.path_conditions[path_id].add("programme_reservation_not_evaluated")
                self.unknowns.append(
                    _unknown(
                        f"programme_reservation:{path_id}",
                        f"the size of any at-the-market programme under {path_id} is not known; it "
                        "splits the registered pool between routes and never changes it",
                        f"the programme terms filed for {path_id}",
                        (path_id,),
                    )
                )
            else:
                self.path_conditions[path_id].add("programme_reservation_not_evaluated")
                self.unknowns.append(
                    _unknown(
                        f"programme_reservation:{path_id}",
                        f"the size of any at-the-market programme under {path_id} is not known; it "
                        "splits the registered pool between routes and never changes it",
                        f"the programme terms filed for {path_id}",
                        (path_id,),
                    )
                )
            self._record_programme_usage(path_id, usage_view, programme)
            if bound.status == "contradicted":
                # §9 substitutes the gross registered amount for an UNKNOWN pool
                # bound only.  A contradicted bound says the deductions already
                # exceed the registered amount, so relaxing it back to the gross
                # figure would state a ceiling the evidence denies.
                substitute = None
            self.blockers.extend(blockers)
            self.registered[path_id] = _Registered(
                pool_id=pool_id,
                bound=bound,
                evidence=fee.evidence,
                applicability=applicability,
                substitute=substitute,
                usage=usage,
                continuing=continuing,
                reservation=reservation,
                takedown_limit=takedown_limit,
                takedown_applicability=takedown_applicability if takedown_limit.status == "known" else None,
                atm_limit=atm_limit,
                atm_applicability=atm_applicability if atm_limit is not None else None,
                has_atm=has_atm,
            )
            route_ids = self._route_ids(path)
            self.pools.append(
                _Pool(
                    pool_id=pool_id,
                    kind="registered_class",
                    stock_or_flow="stock",
                    bound=bound,
                    shared_by=route_ids,
                    applicability=applicability,
                    evidence=fee.evidence,
                    window_start=path.window_start,
                    window_end=path.window_end,
                    coefficient=Fraction(1),
                    substitute=substitute,
                )
            )

    # -- §7 the baby-shelf pool (General Instruction I.B.6 / I.B.5) --------

    def _undecided_pool(
        self,
        pool_id: str,
        kind: str,
        stock_or_flow: str,
        unit: str,
        note: str,
        shared_by: tuple[str, ...],
        *,
        applicability: str | None = None,
        evidence: tuple[EvidenceRef, ...] = (),
        window: tuple[str, str] | None = None,
        coefficient: Fraction = Fraction(1),
        share_basis: str | None = None,
    ) -> None:
        """A pool whose applicability or headroom cannot be decided: unknown, never absent."""
        self.pools.append(
            _Pool(
                pool_id=pool_id,
                kind=kind,
                stock_or_flow=stock_or_flow,
                bound=_unknown_bound(unit, note, share_basis),
                shared_by=shared_by,
                applicability=applicability,
                evidence=evidence,
                window_start=window[0] if window else None,
                window_end=window[1] if window else None,
                coefficient=coefficient,
                substitute=None,
            )
        )

    def _baby_shelf_pool(self) -> None:
        eligible = [
            path
            for path in self.paths
            if path.classification != "ineligible" and path.shelf and not path.automatic
        ]
        if not eligible:
            return
        pool_id = f"baby_shelf:{self.sale_iso}"
        shared_by = tuple(sorted({route_id for path in eligible for route_id in self._route_ids(path)}))
        window = _twelve_month_window(self.sale_iso)
        for path in eligible:
            rule_ids = BABY_SHELF_RULES.get(path.form or "")
            if rule_ids:
                self.path_rules[path.path_id].update(rule_ids)
        forms = sorted({path.form for path in eligible if path.form})
        unsupported = sorted({path.form for path in eligible if path.form not in BABY_SHELF_RULES})
        supported = [form for form in forms if form in BABY_SHELF_RULES]
        if unsupported:
            self.blockers.append(f"baby_shelf_form_not_evaluated:{','.join(unsupported)}")
            self._undecided_pool(
                pool_id,
                "dollars",
                "flow",
                "usd",
                "the one-third limit cannot be evaluated for form "
                f"{','.join(unsupported)}: L0 qualifies only S-3 (I.B.6) and F-3 (I.B.5)",
                shared_by,
                window=window,
            )
            self.baby_shelf_inputs = {
                "pool": None,
                "reason": "form_not_evaluated",
                "forms": forms,
                "window": list(window),
            }
            return
        if len(supported) > 1:
            self.blockers.append("baby_shelf_mixed_forms")
            self._undecided_pool(
                pool_id,
                "dollars",
                "flow",
                "usd",
                f"the shelf routes mix forms {','.join(supported)}, so one issuer-wide one-third "
                "pool cannot be decided between I.B.6 and I.B.5",
                shared_by,
                window=window,
            )
            self.baby_shelf_inputs = {
                "pool": None,
                "reason": "mixed_forms",
                "forms": forms,
                "window": list(window),
            }
            return
        form = supported[0]
        instruction_id, eligibility_id = BABY_SHELF_RULES[form]
        if instruction_id not in self.pack.rules:
            self.absent_rules.add(instruction_id)
            self.blockers.append(f"baby_shelf_rule_text_not_in_rule_pack:{instruction_id}")
            self._undecided_pool(
                pool_id,
                "dollars",
                "flow",
                "usd",
                f"the rule pack carries no text of {instruction_id}, so the one-third limit is undecided",
                shared_by,
                window=window,
            )
            return
        instruction = rule_status_as_of(self.pack, instruction_id, self.sale_iso)
        if instruction.state == "not_in_force":
            # A definite legal conclusion: the instruction did not exist on the sale date.
            self.baby_shelf_inputs = {
                "pool": None,
                "reason": "not_in_force",
                "rule_id": instruction_id,
                "forms": forms,
                "window": list(window),
            }
            return
        if instruction.state == "withheld" or eligibility_id not in self.pack.rules:
            if eligibility_id not in self.pack.rules:
                self.absent_rules.add(eligibility_id)
            self._undecided_pool(
                pool_id,
                "dollars",
                "flow",
                "usd",
                f"no qualified text of {instruction_id if instruction.state == 'withheld' else eligibility_id} "
                f"on {self.sale_iso}, so whether the one-third limit applies is undecided",
                shared_by,
                window=window,
            )
            self.baby_shelf_inputs = {
                "pool": None,
                "reason": "rule_text_withheld",
                "rule_id": instruction_id,
                "eligibility_rule_id": eligibility_id,
                "forms": forms,
                "window": list(window),
            }
            return
        eligibility = rule_status_as_of(self.pack, eligibility_id, self.sale_iso)
        if eligibility.state in ("withheld", "not_in_force"):
            # §7.2: no pool decision is possible, so the pool stays undecided rather
            # than absent -- an absent pool would let a known aggregate ignore a
            # possibly binding one-third limit.
            self._undecided_pool(
                pool_id,
                "dollars",
                "flow",
                "usd",
                f"{eligibility_id} is {eligibility.state} on {self.sale_iso}, so whether the issuer "
                "is inside the one-third limit of "
                f"{instruction_id} is undecided",
                shared_by,
                window=window,
            )
            self.baby_shelf_inputs = {
                "pool": None,
                "reason": f"eligibility_{eligibility.state}",
                "rule_id": instruction_id,
                "eligibility_rule_id": eligibility_id,
                "forms": forms,
                "window": list(window),
            }
            return
        public_float, measured_on, float_refs = self._public_float_quantity()
        sold_trailing = self._sold_trailing()
        pool = baby_shelf_pool(
            self.pack,
            public_float=public_float,
            float_measured_on=measured_on,
            sold_trailing=sold_trailing,
            sold_window=window,
            sale_date=self.sale_iso,
            form=form,
        )
        limit = pool.constraint.bound
        record: dict[str, Any] = {
            "limit": limit.as_record(),
            "sold_trailing": pool.sold_trailing.as_record(),
            "float_measured_on": pool.float_measured_on,
            "headroom": pool.headroom.as_record(),
            "overrun": pool.overrun.as_record(),
            "form": form,
            "rule_id": instruction_id,
            "window": list(window),
            "public_float": public_float.as_record(),
            "public_float_evidence": [ref.as_record() for ref in float_refs],
            "shared_by": list(shared_by),
        }
        if limit.status == "not_applicable":
            for path in eligible:
                self.path_conditions[path.path_id].add(
                    "baby_shelf_not_applicable_public_float_at_or_above_75m"
                )
            self.baby_shelf_inputs = dict(record, pool=None, reason="not_applicable")
            return
        if (
            pool.overrun.status == "known"
            and pool.overrun.decimal is not None
            and pool.overrun.decimal > 0
        ):
            self.blockers.append(f"baby_shelf_overrun:{self.sale_iso}")
        substitute = (
            Fraction(limit.decimal) if limit.status == "known" and limit.decimal is not None else None
        )
        self.pools.append(
            _Pool(
                pool_id=pool_id,
                kind="dollars",
                stock_or_flow="flow",
                bound=pool.headroom,
                shared_by=shared_by,
                applicability=pool.constraint.applicability,
                evidence=pool.constraint.evidence,
                window_start=pool.constraint.window_start,
                window_end=pool.constraint.window_end,
                coefficient=Fraction(1),
                substitute=substitute,
            )
        )
        self.baby_shelf_inputs = dict(record, pool=pool_id)

    def _public_float_quantity(self) -> tuple[Quantity, str | None, tuple[EvidenceRef, ...]]:
        """The latest then-known public-float measurement inside the 60-day lookback."""
        earliest = self.sale_date - timedelta(days=FLOAT_MEASUREMENT_LOOKBACK_DAYS)
        best: tuple[tuple[date, str], Decimal, str, _Observation, tuple[EvidenceRef, ...]] | None = None
        for observation in self.read.share_counts:  # type: ignore[union-attr]
            body = observation.body
            if _text(_nested(body, "metric", "kind")) != "public_float":
                continue
            if _text(_nested(body, "normalized", "state")) != "observed":
                continue
            unit = _text(_nested(body, "normalized", "unit"))
            if unit is None or unit.upper() != "USD":
                continue
            period_end = _day(_nested(body, "period", "period_end"))
            if period_end is None or not earliest <= period_end <= self.sale_date:
                continue
            value = _decimal_or_none(_nested(body, "normalized", "value"))
            if value is None or value < 0:
                continue
            refs = self._float_evidence(body)
            key = (period_end, observation.digest)
            if best is None or key > best[0]:
                best = (key, value, period_end.isoformat(), observation, refs)
        if best is None:
            resolution = self._resolution(f"baby_shelf_public_float:{self.sale_iso}")
            if resolution is not None:
                # A supplied resolution counts as measured on the sale date.
                return resolution.assumed, self.sale_iso, ()
            return (
                _unknown_bound(
                    "usd",
                    f"no then-known public-float measurement within {FLOAT_MEASUREMENT_LOOKBACK_DAYS} "
                    f"days before {self.sale_iso} and no scenario resolution",
                ),
                None,
                (),
            )
        _, value, measured_on, observation, refs = best
        quantity = Quantity.known(
            _decimal_text(value),
            "usd",
            applicability=f"public float measured on {measured_on}",
            provenance=Provenance(
                "share_count_observations", available_at=_iso(observation.available), evidence=refs
            ),
        )
        return quantity, measured_on, refs

    def _float_evidence(self, body: Mapping[str, Any]) -> tuple[EvidenceRef, ...]:
        evidence = body.get("evidence") if isinstance(body.get("evidence"), Mapping) else {}
        manifest = (
            _text(evidence.get("source_receipt_id"))
            or _text(evidence.get("bridge_receipt_id"))
            or _text(evidence.get("source_manifest_id"))
        )
        span_id = _text(body.get("observation_id"))
        entries = _sequence(evidence.get("fact_entries"))
        text_sha256 = (
            _text(entries[0].get("entry_sha256")) if entries and isinstance(entries[0], Mapping) else None
        )
        if manifest is None or span_id is None or text_sha256 is None:
            return ()
        try:
            return (EvidenceRef(manifest, span_id, text_sha256),)
        except ContractViolation:
            return ()

    def _sold_trailing(self) -> Quantity:
        resolution = self._resolution(f"baby_shelf_sold_trailing:{self.sale_iso}")
        if resolution is not None:
            return resolution.assumed
        return _unknown_bound(
            "usd",
            f"no scenario resolution for the sales under the instruction in the 12 calendar months "
            f"ending {self.sale_iso}",
        )

    # -- SPEC_C2 §2.1 the price in effect ---------------------------------

    def _price_view(self) -> None:
        """The price in effect at the horizon start and the at-the-market window.

        ``price_at(d)`` is the price of the latest path point dated on or before
        ``d`` (for fixed pricing, the fixed price at every date).  A takedown is
        priced at ``p_start`` because its sale is already scheduled at the horizon
        start; an at-the-market programme is priced at the window ``low`` in the
        pessimistic branch and at ``high`` in the optimistic one, because its sale
        dates inside the window are not known.  Points after ``horizon_end`` are
        never read.  A path with no point on or before the horizon start leaves
        every price unknown -- never a later price, never zero.
        """
        price = self.scenario.price
        start = _day(self.scenario.horizon_start)
        end = _day(self.scenario.horizon_end)
        if start is None or end is None:
            raise CapacityInputError(
                f"scenario horizon {self.scenario.horizon_start!r}.."
                f"{self.scenario.horizon_end!r} is not an ISO date pair"
            )
        if price.kind == "fixed":
            fixed = exact(price.fixed_price, "price.fixed_price")
            if fixed <= 0:
                raise CapacityInputError(
                    "price.fixed_price must be positive to convert shares into dollars"
                )
            self.price_view = _PriceView(
                kind="fixed",
                currency=price.currency,
                fixed_price=price.fixed_price,
                path=(),
                p_start=fixed,
                low=fixed,
                high=fixed,
                window_dates=(),
                uncovered=False,
                branching=False,
            )
            return
        points: list[tuple[date, str, Fraction]] = []
        for point in price.path:
            day = _day(point[0])
            if day is None:
                raise CapacityInputError(f"price.path date {point[0]!r} is not an ISO date")
            value = exact(point[1], "price.path")
            if value <= 0:
                raise CapacityInputError(
                    "price.path must carry a positive price to convert shares into dollars"
                )
            points.append((day, point[0], value))
        points.sort(key=lambda item: (item[0], item[1]))
        covering = [item for item in points if item[0] <= start]
        if not covering:
            self.unknowns.append(
                _unknown(
                    f"price_path_uncovered:{start.isoformat()}",
                    f"the price path carries no point on or before the horizon start "
                    f"{start.isoformat()}, so no price is in effect for a sale on that date",
                    "a price in effect on or before the horizon start",
                    (start.isoformat(),),
                )
            )
            self.price_view = _PriceView(
                kind="path",
                currency=price.currency,
                fixed_price=None,
                path=tuple(tuple(point) for point in price.path),
                p_start=None,
                low=None,
                high=None,
                window_dates=(),
                uncovered=True,
                branching=False,
            )
            return
        p_start = covering[-1][2]
        window = [p_start]
        window_dates = [covering[-1][1]]
        for day, text, value in points:
            if start < day <= end:
                window.append(value)
                window_dates.append(text)
        self.price_view = _PriceView(
            kind="path",
            currency=price.currency,
            fixed_price=None,
            path=tuple(tuple(point) for point in price.path),
            p_start=p_start,
            low=min(window),
            high=max(window),
            window_dates=tuple(sorted(window_dates)),
            uncovered=False,
            branching=False,
        )

    def _price_record(self) -> dict[str, Any]:
        """``inputs["price"]`` (§2.1): the price view, not the raw assumption alone."""
        assert self.price_view is not None
        view = self.price_view
        return {
            "kind": view.kind,
            "currency": view.currency,
            "fixed_price": view.fixed_price,
            "path": [list(point) for point in view.path],
            "p_start": _fraction_text(view.p_start),
            "low": _fraction_text(view.low),
            "high": _fraction_text(view.high),
            "window_dates": list(view.window_dates),
            "uncovered": view.uncovered,
            "branching": view.branching,
        }

    def _finalize_branching(self) -> None:
        """§2.1/§2.5: whether the solve branches, on which routes, and why.

        Price branching needs path pricing, an ACTIVE at-the-market route that
        consumes the Nasdaq share pool, and a window whose low differs from its
        high.  Programme-usage branching (§2.3) is independent of price.
        """
        assert self.price_view is not None
        view = self.price_view
        reasons: list[str] = []
        price_routes: tuple[str, ...] = ()
        if view.kind == "path" and not view.uncovered and view.low != view.high:
            pool_id = f"nasdaq_20pct:{self.sale_iso}"
            price_routes = tuple(sorted(
                plan.route_id
                for plan in self.route_plans
                if plan.route_kind == "at_the_market"
                and plan.status in ACTIVE_ROUTE_STATUSES
                and pool_id in plan.consumes
            ))
            if price_routes:
                reasons.append("price_path")
                self.price_view = dataclasses.replace(view, branching=True)
        if "price_path" in reasons:
            self.price_branch_routes = price_routes
        for path_id in sorted(self.usage_views):
            reasons.append(f"programme_usage:{path_id}")
        self.branching = bool(reasons)
        self.branch_reasons = tuple(sorted(reasons))

    # -- §8 the Nasdaq Rule 5635(d) 20% pool ------------------------------

    def _placeholder_coefficient(self) -> Fraction:
        """The C1 placeholder, used ONLY when a price path does not cover the horizon start.

        The share bound is unknown in that case, so the coefficient cannot change
        the solve; the lowest positive path price is the conservative placeholder.
        """
        prices = [exact(value, "price.path") for _, value in self.scenario.price.path]
        positive = [item for item in prices if item > 0]
        if not positive:
            raise CapacityInputError(
                "price.path must carry a positive price to convert shares into dollars"
            )
        return Fraction(1) / min(positive)

    def _outstanding(self) -> tuple[Quantity, str | None]:
        best: tuple[tuple[datetime, str], Decimal] | None = None
        for observation in self.read.share_basis_results:  # type: ignore[union-attr]
            body = observation.body
            if _text(body.get("status")) != "selected":
                continue
            selected = body.get("selected")
            if not isinstance(selected, Mapping):
                continue
            unit = _text(selected.get("unit"))
            if unit is not None and unit != "shares":
                continue
            basis = _text(selected.get("share_basis"))
            if basis is not None and basis != "issued_and_outstanding":
                continue
            value = _decimal_or_none(selected.get("value"))
            if value is None or value < 0:
                continue
            key = (observation.available, observation.digest)
            if best is None or key > best[0]:
                best = (key, value)
        if best is None:
            return Quantity.unknown("shares", share_basis="issued_and_outstanding"), None
        text = _decimal_text(best[1])
        return Quantity.known(text, "shares", share_basis="issued_and_outstanding"), text

    def _share_basis_evidence(self, value_text: str | None) -> tuple[EvidenceRef, ...]:
        if value_text is None:
            return ()
        refs: list[EvidenceRef] = []
        for observation in self.read.share_basis_results:  # type: ignore[union-attr]
            body = observation.body
            if _text(body.get("status")) != "selected":
                continue
            selected = body.get("selected")
            if not isinstance(selected, Mapping) or _text(selected.get("value")) != value_text:
                continue
            for candidate in _sequence(body.get("candidates")):
                if not isinstance(candidate, Mapping):
                    continue
                if _text(candidate.get("basis")) != "issued_and_outstanding":
                    continue
                if _text(candidate.get("value")) != value_text:
                    continue
                refs.extend(_span_refs(_nested(candidate, "source", "evidence")))
        return _unique_refs(refs)

    def _e0_refs(self, status: rule_applicability.RuleStatus) -> tuple[EvidenceRef, ...]:
        window = status.window
        if window is None:
            return ()
        label = window.reference_span_label or window.span_id
        if not label:
            return ()
        try:
            return (EvidenceRef(REFERENCE_PACK_MANIFEST_ID, label, window.sha256),)
        except ContractViolation:
            return ()

    def _nasdaq_pool(self) -> None:
        active_paths = [path for path in self.paths if path.classification != "ineligible"]
        if not active_paths:
            return
        shared_by = tuple(
            sorted({route_id for path in active_paths for route_id in self._route_ids(path)})
        )
        pool_id = f"nasdaq_20pct:{self.sale_iso}"
        assumed = all(
            _text(self.assumptions.get(key)) == value
            for key, value in NASDAQ_OFFERING_ASSUMPTIONS.items()
        )
        if not assumed:
            for route_id in shared_by:
                self.unknowns.append(
                    _unknown(
                        f"nasdaq_offering_treatment:{route_id}",
                        "the scenario does not assume a Nasdaq-listed non-public offering priced below "
                        "the minimum price, so the Rule 5635(d) 20% test is not reached (A14)",
                        "scenario assumptions naming listing_venue, exchange_offering_treatment and "
                        "price_relative_to_minimum_price",
                        (route_id,),
                    )
                )
            return
        for path in active_paths:
            self.path_rules[path.path_id].add(NASDAQ_RULE_ID)
            self.path_conditions[path.path_id].add(
                "nasdaq_aggregation_of_related_transactions_not_evaluated"
            )
        price = self.scenario.price
        assert self.price_view is not None
        view = self.price_view
        if NASDAQ_RULE_ID not in self.pack.rules:
            self.absent_rules.add(NASDAQ_RULE_ID)
            self.blockers.append(f"nasdaq_rule_text_not_in_rule_pack:{NASDAQ_RULE_ID}")
            self._undecided_pool(
                pool_id,
                "shares",
                "flow",
                "shares",
                f"the rule pack carries no text of {NASDAQ_RULE_ID}, so the 20% threshold is undecided",
                shared_by,
                share_basis="issued_and_outstanding",
            )
            return
        status = rule_status_as_of(self.pack, NASDAQ_RULE_ID, self.sale_iso)
        if status.state in ("not_in_force", "withheld"):
            # A withheld text is carried as a condition and a rule_text unknown by
            # _rule_text for every active route; no pool may be decided.
            self.nasdaq_inputs = {
                "pool": None,
                "reason": f"rule_text_{status.state}",
                "rule_id": NASDAQ_RULE_ID,
                "rule_state": status.state,
                "condition": status.condition,
            }
            return
        if view.uncovered:
            # §2.2 step 4: the 20% threshold is in SHARES and does not depend on
            # price, but with no price in effect at the horizon start it cannot be
            # turned into a dollar bound on any route.  Unknown, never zero.
            coefficient = self._placeholder_coefficient()
            outstanding, _ = self._outstanding()
            self._undecided_pool(
                pool_id,
                "shares",
                "flow",
                "shares",
                f"the price path carries no price in effect on or before the horizon start "
                f"{self.scenario.horizon_start}, so the 20% share threshold cannot be bound to a "
                "dollar amount on any route",
                shared_by,
                coefficient=coefficient,
                share_basis="issued_and_outstanding",
            )
            self.nasdaq_inputs = {
                "pool": pool_id,
                "reason": "price_path_uncovered",
                "rule_id": NASDAQ_RULE_ID,
                "rule_state": status.state,
                "condition": status.condition,
                "price": self._price_record(),
                "coefficient": _fraction_text(coefficient),
                "outstanding": outstanding.as_record(),
                "shared_by": list(shared_by),
            }
            return
        assert view.p_start is not None
        coefficient = Fraction(1) / view.p_start
        outstanding, outstanding_text = self._outstanding()
        test = nasdaq_twenty_percent(
            outstanding=outstanding,
            proposed=Quantity.unknown("shares", share_basis="scenario_incremental_issuance"),
            price_relative_to_minimum_price="below",
        )
        refs = list(self._e0_refs(status)) + list(self._share_basis_evidence(outstanding_text))
        bound = test.largest_issuance_below_threshold
        if bound.status == "known" and not refs:
            self.blockers.append("nasdaq_rule_evidence_missing")
            bound = _unknown_bound(
                "shares",
                f"the {NASDAQ_RULE_ID} threshold retains no evidence reference",
                "issued_and_outstanding",
            )
        if outstanding.status != "known":
            self.unknowns.append(
                _unknown(
                    f"shares_outstanding:{self.sale_iso}",
                    "the issued-and-outstanding share count on the Rule 5635(e)(1) basis is not "
                    "then-known, so the 20% threshold is not known",
                    f"a selected share_basis_result for {self.sale_iso}",
                )
            )
        # §2.2 step 6: a takedown is priced at p_start (the pool's default
        # coefficient); an at-the-market route is priced at the window low in the
        # pessimistic branch and at the high in the optimistic one.  Fixed pricing
        # emits no rows, so the C1 kernel input is byte-identical.
        route_coefficients: tuple[tuple[str, str, str], ...] = ()
        if price.kind == "path":
            assert view.low is not None and view.high is not None
            atm_routes = tuple(
                sorted(route_id for route_id in shared_by if route_id.startswith("at_the_market:"))
            )
            route_coefficients = tuple(
                (route_id, branch, _fraction_text(Fraction(1) / window_price))
                for route_id in atm_routes
                for branch, window_price in (("pessimistic", view.low), ("optimistic", view.high))
            )
        self.pools.append(
            _Pool(
                pool_id=pool_id,
                kind="shares",
                stock_or_flow="flow",
                bound=bound,
                shared_by=shared_by,
                applicability=bound.applicability,
                evidence=tuple(refs),
                window_start=None,
                window_end=None,
                coefficient=coefficient,
                substitute=None,
                route_coefficients=route_coefficients,
            )
        )
        self.nasdaq_inputs = {
            "pool": pool_id,
            "rule_id": NASDAQ_RULE_ID,
            "rule_state": status.state,
            "condition": status.condition,
            "price": self._price_record(),
            "coefficient": _fraction_text(coefficient),
            "outstanding": outstanding.as_record(),
            "threshold": test.threshold.as_record(),
            "largest_issuance_below_threshold": bound.as_record(),
            "scope_notes": list(test.scope_notes),
            "shared_by": list(shared_by),
        }
        if route_coefficients:
            self.nasdaq_inputs["route_coefficients"] = [list(row) for row in route_coefficients]

    # -- §4 route conditions from consulted rule text ----------------------

    def _rule_text(self, rule_ids: Any) -> tuple[list[str], list[Unknown], list[str]]:
        conditions: list[str] = []
        unknowns: list[Unknown] = []
        absent: list[str] = []
        for rule_id in sorted(set(rule_ids)):
            if rule_id not in self.pack.rules:
                absent.append(rule_id)
                continue
            status = rule_status_as_of(self.pack, rule_id, self.sale_iso)
            if status.state in ("bracketed", "beyond_window", "withheld") and status.condition:
                conditions.append(status.condition)
            if status.state == "withheld":
                unknown_id = f"rule_text:{rule_id}:{self.sale_iso}"
                unknowns.append(
                    self.rule_unknown_by_id.get(unknown_id)
                    or _unknown(
                        unknown_id,
                        status.condition or f"no qualified text of {rule_id} on {self.sale_iso}",
                        f"the qualified text of {rule_id} in force on {self.sale_iso}",
                        (rule_id,),
                    )
                )
        return conditions, unknowns, absent

    def _route_plans(self) -> None:
        consumes_by_route: dict[str, set[str]] = {}
        for pool in self.pools:
            for route_id in pool.shared_by:
                consumes_by_route.setdefault(route_id, set()).add(pool.pool_id)
        for path in sorted(self.paths, key=lambda item: item.path_id):
            if path.classification == "ineligible":
                self.route_plans.append(
                    _RoutePlan(
                        route_id=path.takedown_id,
                        route_kind="shelf_takedown",
                        limit=Quantity(
                            unit="usd",
                            status="not_applicable",
                            note=f"{path.reason}: no takedown is available under {path.path_id}",
                        ),
                        status="ineligible",
                        conditions=path.ineligible_conditions,
                        consumes=(),
                        applicability=None,
                        evidence=(),
                    )
                )
                continue
            registered = self.registered[path.path_id]
            if path.classification == "unknown":
                self.unknowns.append(
                    _unknown(
                        f"registration_effectiveness:{path.path_id}",
                        f"whether the registration under {path.path_id} is effective is not known: "
                        f"{path.reason}",
                        "SEC notice of effectiveness or WKSI status at the determination date",
                        (path.takedown_id,),
                    )
                )
            conditions, unknowns, absent = self._rule_text(self.path_rules[path.path_id])
            self.unknowns.extend(unknowns)
            self.absent_rules.update(absent)
            shared = set(path.base_conditions) | self.path_conditions[path.path_id] | set(conditions)
            takedown_known = registered.takedown_limit.status == "known"
            self.route_plans.append(
                _RoutePlan(
                    route_id=path.takedown_id,
                    route_kind="shelf_takedown",
                    limit=registered.takedown_limit,
                    status=path.classification,
                    conditions=_conditions(shared, self.route_conditions[path.takedown_id]),
                    consumes=tuple(sorted(consumes_by_route.get(path.takedown_id, ()))),
                    applicability=registered.takedown_applicability,
                    evidence=registered.evidence if takedown_known else (),
                )
            )
            if registered.has_atm and registered.atm_limit is not None:
                atm_id = f"at_the_market:{path.path_id}"
                self.route_plans.append(
                    _RoutePlan(
                        route_id=atm_id,
                        route_kind="at_the_market",
                        limit=registered.atm_limit,
                        status=path.classification,
                        conditions=_conditions(shared, self.route_conditions[atm_id]),
                        consumes=tuple(sorted(consumes_by_route.get(atm_id, ()))),
                        applicability=registered.atm_applicability,
                        evidence=registered.evidence,
                    )
                )

    # -- SPEC_C2 §2.4 mutually exclusive routes ---------------------------

    def _exclusive_groups(self) -> None:
        """Read ``other_assumptions["route_exclusivity"]`` into kernel groups.

        ``"A|B;C|D"`` declares two groups (``;`` separates groups, ``|`` separates
        members, route ids verbatim).  A route this envelope does not carry is a
        hard input error, and so is a repeated member or a route in two groups.
        Ineligible members are dropped and recorded; a group left with fewer than
        two members is recorded but never passed on.
        """
        declared: list[tuple[str, ...]] = []
        raw = self.assumptions.get(ROUTE_EXCLUSIVITY_KEY)
        if raw is not None:
            text = raw if isinstance(raw, str) else str(raw)
            for chunk in text.split(";"):
                label = chunk.strip()
                if not label:
                    continue
                members = [item.strip() for item in chunk.split("|") if item.strip()]
                if len(members) < 2:
                    raise CapacityInputError(
                        f"{ROUTE_EXCLUSIVITY_KEY}: group {label!r} names fewer than two routes"
                    )
                if len(set(members)) != len(members):
                    raise CapacityInputError(
                        f"{ROUTE_EXCLUSIVITY_KEY}: group {label!r} repeats a route"
                    )
                declared.append(tuple(members))
        self.exclusive_declared = tuple(declared)
        plans = {plan.route_id: plan for plan in self.route_plans}
        claimed: set[str] = set()
        dropped: list[str] = []
        groups: list[tuple[str, ...]] = []
        not_passed: list[tuple[str, ...]] = []
        for group in declared:
            eligible: list[str] = []
            for route_id in group:
                plan = plans.get(route_id)
                if plan is None:
                    raise CapacityInputError(
                        f"{ROUTE_EXCLUSIVITY_KEY}: {route_id!r} is not a route of this envelope"
                    )
                if route_id in claimed:
                    raise CapacityInputError(
                        f"{ROUTE_EXCLUSIVITY_KEY}: {route_id!r} appears in more than one group"
                    )
                claimed.add(route_id)
                if plan.status in ACTIVE_ROUTE_STATUSES:
                    eligible.append(route_id)
                else:
                    dropped.append(route_id)
            if len(eligible) < 2:
                not_passed.append(tuple(sorted(group)))
                continue
            groups.append(tuple(sorted(eligible)))
        self.exclusive_dropped = tuple(sorted(dropped))
        self.exclusive_not_passed = tuple(sorted(not_passed))
        self.exclusive_groups = tuple(sorted(groups))

    # -- SPEC_C2 §2.6 asserted actions ------------------------------------

    def _is_fixed(self, route_id: str) -> bool:
        view = self.action_views.get(route_id)
        return view is not None and view.fixed and view.applied

    def _action_price(self, plan: _RoutePlan, branch: str) -> Fraction:
        """§2.6: the price a SHARE quantity on this route converts at, per branch."""
        assert self.price_view is not None
        view = self.price_view
        if plan.route_kind == "at_the_market":
            price = view.low if branch == "pessimistic" else view.high
            name = "the window low" if branch == "pessimistic" else "the window high"
        else:
            price = view.p_start
            name = "the price in effect at the horizon start"
        if price is None:
            raise CapacityInputError(
                f"a share quantity on {plan.route_id} needs {name}, and the price path carries no "
                f"price in effect on or before the horizon start {self.scenario.horizon_start}"
            )
        return price

    def _apply_actions(self) -> None:
        """Asserted actions become a FIXED use, never a cap on the route."""
        plans = {plan.route_id: plan for plan in self.route_plans}
        views: dict[str, _ActionView] = {}
        for action in sorted(self.scenario.actions, key=lambda item: item.route_id):
            plan = plans.get(action.route_id)
            if plan is None:
                raise CapacityInputError(
                    f"action names {action.route_id!r}, which is not a route of this envelope"
                )
            if action.action != plan.route_kind:
                raise CapacityInputError(
                    f"action on {action.route_id!r} declares {action.action!r}, but the route is "
                    f"a {plan.route_kind!r}"
                )
            if action.settlement != "cash":
                raise CapacityInputError(
                    f"action on {action.route_id!r} settles in {action.settlement!r}; only cash "
                    "settlement converts into gross dollar capacity"
                )
            unmet = tuple(sorted(set(action.conditions_assumed_met) - set(plan.conditions)))
            if unmet:
                raise CapacityInputError(
                    f"action on {action.route_id!r} assumes conditions the route does not carry: "
                    f"{', '.join(unmet)}"
                )
            conditions = tuple(sorted(action.conditions_assumed_met))
            quantity = action.quantity
            if quantity is None:
                # Recorded only: an intent that changes no number (A48).
                views[action.route_id] = _ActionView(
                    route_id=action.route_id,
                    action=action.action,
                    settlement=action.settlement,
                    fixed=False,
                    applied=False,
                    usd={},
                    conditions_assumed_met=conditions,
                )
                continue
            if quantity.status != "known" or quantity.value is None:
                raise CapacityInputError(
                    f"action on {action.route_id!r} carries a {quantity.status!r} quantity; a fixed "
                    "action needs a known one"
                )
            if quantity.unit not in ("usd", "shares"):
                raise CapacityInputError(
                    f"action on {action.route_id!r} is quantified in {quantity.unit!r}; only usd "
                    "and shares convert into gross dollars"
                )
            amount = exact(quantity.value, "action.quantity")
            if amount < 0:
                raise CapacityInputError(
                    f"action on {action.route_id!r} carries a negative quantity"
                )
            usd = {
                branch: (
                    amount
                    if quantity.unit == "usd"
                    else amount * self._action_price(plan, branch)
                )
                for branch in BRANCHES
            }
            applied = plan.status in ACTIVE_ROUTE_STATUSES
            if not applied:
                self.blockers.append(f"asserted_action_on_ineligible_route:{action.route_id}")
            views[action.route_id] = _ActionView(
                route_id=action.route_id,
                action=action.action,
                settlement=action.settlement,
                fixed=True,
                applied=applied,
                usd=usd,
                conditions_assumed_met=conditions,
            )
        self.action_views = views
        for group in self.exclusive_groups:
            chosen = tuple(sorted(route_id for route_id in group if self._is_fixed(route_id)))
            if len(chosen) > 1:
                raise CapacityInputError(
                    f"{ROUTE_EXCLUSIVITY_KEY}: the mutually exclusive group "
                    f"{'|'.join(group)} carries two fixed actions ({', '.join(chosen)})"
                )
        for branch in BRANCHES:
            self._residuals(branch)
        both = (
            self.infeasible["pessimistic"]
            if not self.branching
            else self.infeasible["pessimistic"] & self.infeasible["optimistic"]
        )
        single = {
            branch: self.infeasible[branch] - both for branch in BRANCHES
        }
        self.branch_infeasible_on_one = any(single[branch] for branch in BRANCHES)
        for constraint_id in sorted(both):
            self.blockers.append(f"asserted_actions_infeasible:{constraint_id}")
        if both:
            self.contradiction = (
                "the asserted actions exceed what remains of "
                + ", ".join(sorted(both))
                + " in every branch, so no feasible amount is left to raise"
            )
        # The price label is used only when the price path is the sole branch
        # reason; a programme-usage branch (alone or combined) gets the plain one.
        label = (
            "asserted_actions_infeasible_on_price_branch"
            if self.branch_reasons == ("price_path",)
            else "asserted_actions_infeasible_on_branch"
        )
        for branch in BRANCHES:
            for constraint_id in sorted(single[branch]):
                self.blockers.append(f"{label}:{branch}:{constraint_id}")
        for path_id in sorted(self.registered):
            if f"programme_usage_exceeds_reservation:{path_id}" not in self.blockers:
                continue
            atm_id = f"at_the_market:{path_id}"
            plan = plans.get(atm_id)
            if plan is not None and plan.status in ACTIVE_ROUTE_STATUSES and self._is_fixed(atm_id):
                self.contradiction = (
                    f"the asserted action on {atm_id} is committed against a programme whose sales "
                    f"already exceed its reservation under {path_id}"
                )

    def _residuals(self, branch: str) -> None:
        """§2.6: what is left of every route limit and pool bound in ``branch``."""
        route_limits: dict[str, Fraction | None] = {}
        for plan in self.route_plans:
            if plan.status == "ineligible":
                continue
            route_limits[plan.route_id] = self._branch_route_limit(plan, branch)
        for group in self.exclusive_groups:
            if any(self._is_fixed(route_id) for route_id in group):
                # §2.4: one fixed member has chosen the group, so the others
                # cannot be used at all in the residual solve.
                for route_id in group:
                    if route_id in route_limits and not self._is_fixed(route_id):
                        route_limits[route_id] = Fraction(0)
        for route_id in sorted(self.action_views):
            view = self.action_views[route_id]
            if not view.fixed or not view.applied or route_id not in route_limits:
                continue
            current = route_limits[route_id]
            if current is not None:
                route_limits[route_id] = current - view.usd[branch]
        pool_bounds: dict[str, Fraction | None] = {}
        for pool in sorted(self.pools, key=lambda item: item.pool_id):
            bound = self._branch_pool_bound(pool, branch)
            deduction = Fraction(0)
            for route_id in pool.shared_by:
                view = self.action_views.get(route_id)
                if view is None or not view.fixed or not view.applied:
                    continue
                deduction += pool.coefficient_for(route_id, branch) * view.usd[branch]
            if bound is not None and deduction:
                bound = bound - deduction
            pool_bounds[pool.pool_id] = bound
        self.residual_routes[branch] = route_limits
        self.residual_pools[branch] = pool_bounds
        self.fixed_totals[branch] = sum(
            (
                view.usd[branch]
                for view in self.action_views.values()
                if view.fixed and view.applied
            ),
            Fraction(0),
        )
        self.infeasible[branch] = {
            identifier
            for identifier, value in (*route_limits.items(), *pool_bounds.items())
            if value is not None and value < 0
        }

    def _branch_route_limit(self, plan: _RoutePlan, branch: str) -> Fraction | None:
        """The route's own limit in ``branch``; ``None`` when it is not known."""
        if plan.limit.status == "known":
            return exact(plan.limit.value, f"route[{plan.route_id}].limit")
        if plan.route_kind == "at_the_market" and ":" in plan.route_id:
            view = self.usage_views.get(plan.route_id.split(":", 1)[1])
            if view is not None and branch in view.atm_limit:
                return view.atm_limit[branch]
        return None

    def _branch_pool_bound(self, pool: _Pool, branch: str) -> Fraction | None:
        """The pool bound in ``branch``; ``None`` when it is not known."""
        prefix = "registered:"
        if pool.pool_id.startswith(prefix):
            view = self.usage_views.get(pool.pool_id[len(prefix):])
            if view is not None and branch in view.pool_bound:
                return view.pool_bound[branch]
        if pool.bound.status == "known":
            return exact(pool.bound.value, f"pool[{pool.pool_id}].bound")
        return None

    # -- §9 the branch solves and the envelope -----------------------------

    def _joint_routes(self, branch: str) -> list[JointRoute]:
        out: list[JointRoute] = []
        for plan in self.route_plans:
            if plan.status == "ineligible":
                continue
            limit = self.residual_routes[branch].get(plan.route_id)
            # A negative residual is reported as infeasible, never solved: the
            # kernel refuses it, and clamping to zero states no capacity.
            out.append(JointRoute(plan.route_id, None if limit is None else max(limit, Fraction(0))))
        return out

    def _joint_pools(self, substitutes: bool, branch: str) -> list[JointPool]:
        known_route_ids = {
            plan.route_id for plan in self.route_plans if plan.status != "ineligible"
        }
        out: list[JointPool] = []
        for pool in sorted(self.pools, key=lambda item: item.pool_id):
            uses = tuple(
                (route_id, pool.coefficient_for(route_id, branch))
                for route_id in pool.shared_by
                if route_id in known_route_ids
            )
            if not uses:
                continue
            bound = self.residual_pools[branch].get(pool.pool_id)
            if bound is None:
                bound = pool.substitute if substitutes and pool.substitute is not None else None
            else:
                bound = max(bound, Fraction(0))
            out.append(JointPool(pool.pool_id, uses, bound))
        return out

    def _solve(self) -> tuple[JointSolution, JointSolution | None, JointSolution]:
        """§2.5: the pessimistic evidence, the optimistic branch and the ceiling."""
        groups = self.exclusive_groups
        pessimistic = solve_joint(
            self._joint_routes("pessimistic"),
            self._joint_pools(False, "pessimistic"),
            exclusive=groups,
        )
        ceiling = solve_joint(
            self._joint_routes("optimistic"),
            self._joint_pools(True, "optimistic"),
            exclusive=groups,
        )
        if not self.branching:
            return pessimistic, None, ceiling
        optimistic = solve_joint(
            self._joint_routes("optimistic"),
            self._joint_pools(False, "optimistic"),
            exclusive=groups,
        )
        return pessimistic, optimistic, ceiling

    def _constraints(self, solution: JointSolution, active: tuple[str, ...]) -> tuple[Constraint, ...]:
        out: list[Constraint] = []
        for pool in sorted(self.pools, key=lambda item: item.pool_id):
            status = "unknown"
            if solution.determined and active and pool.bound.status == "known":
                status = "binding" if pool.pool_id in solution.binding else "slack"
            out.append(
                Constraint(
                    constraint_id=pool.pool_id,
                    kind=pool.kind,
                    bound=pool.bound,
                    status=status,
                    stock_or_flow=pool.stock_or_flow,
                    shared_by=pool.shared_by,
                    applicability=pool.applicability,
                    evidence=pool.evidence,
                    window_start=pool.window_start,
                    window_end=pool.window_end,
                )
            )
        return tuple(out)

    def _routes(self) -> tuple[RouteBound, ...]:
        return tuple(
            RouteBound(
                route_id=plan.route_id,
                route_kind=plan.route_kind,
                limit=plan.limit,
                status=plan.status,
                conditions=plan.conditions,
                consumes=plan.consumes,
                applicability=plan.applicability,
                evidence=plan.evidence,
            )
            for plan in sorted(self.route_plans, key=lambda item: item.route_id)
        )

    def _aggregate_provenance(self) -> Provenance:
        refs: list[EvidenceRef] = []
        for plan in self.route_plans:
            if plan.limit.status == "known":
                refs.extend(plan.evidence)
        binding = self.state.request.binding("document_terms")
        generation_id = binding.generation_id if binding is not None else None
        return Provenance(
            "document_terms",
            generation_id=generation_id,
            evidence=_unique_refs(refs),
            available_at=_iso(self.cutoff),
        )

    def _note_price_schedule(self) -> None:
        """§2.7: the sale schedule that would collapse the two price branches."""
        for route_id in self.price_branch_routes:
            self.unknowns.append(
                _unknown(
                    f"price_path_sale_schedule:{route_id}",
                    f"the dates on which {route_id} sells inside the horizon are not known, so the "
                    "price that applies to each dollar sold under it is not known",
                    "the dated sale schedule (dates and prices) of the programme within the window",
                    (route_id,),
                )
            )

    def _aggregate(
        self,
        pessimistic: JointSolution,
        optimistic: JointSolution | None,
        ceiling: JointSolution,
        active: tuple[str, ...],
        routes: tuple[RouteBound, ...],
        pools: tuple[Constraint, ...],
    ) -> Quantity:
        """§2.7: one aggregate.  Fixed actions are added; branch optima never are."""
        if self.contradiction is not None:
            return Quantity(unit="usd", status="contradicted", note=self.contradiction)
        fixed_pessimistic = self.fixed_totals["pessimistic"]
        fixed_optimistic = self.fixed_totals["optimistic"]
        ceiling_raw = (
            ceiling.value if ceiling.determined else ceiling.ceiling_when_unknowns_relaxed
        )
        ceiling_value = None if ceiling_raw is None else fixed_optimistic + ceiling_raw
        ceiling_text = "unbounded" if ceiling_value is None else _floor_text(ceiling_value)
        # §2.6: an asserted action that fails in one branch leaves the answer
        # open, even when the two branch optima happen to coincide.
        agree = not self.branch_infeasible_on_one and (
            not self.branching
            or (
                optimistic is not None
                and pessimistic.determined
                and optimistic.determined
                and optimistic.value == pessimistic.value
                and fixed_optimistic == fixed_pessimistic
            )
        )
        if pessimistic.determined and active and agree and self._aggregate_knowable(routes, pools):
            return Quantity.known(
                _floor_text(fixed_pessimistic + (pessimistic.value or Fraction(0))),
                "usd",
                applicability=(
                    f"joint feasible maximum of {len(active)} active route use(s) under "
                    f"{len(self.pools)} declared shared pool(s); gross USD before fees, discounts "
                    "and proceeds (A48: no score, rank or sizing)"
                ),
                provenance=self._aggregate_provenance(),
                note=f"gross dollars; the joint ceiling call agrees at {ceiling_text}",
            )
        floor_text = _floor_text(
            fixed_pessimistic
            + (
                pessimistic.value
                if pessimistic.determined
                else pessimistic.floor_when_unknowns_zero
            )
        )
        if self.price_branch_routes and (self.branch_infeasible_on_one or not agree):
            self._note_price_schedule()
        return _unknown_bound(
            "usd", f"floor {floor_text} / ceiling {ceiling_text} under stated unknowns"
        )

    @staticmethod
    def _aggregate_knowable(
        routes: tuple[RouteBound, ...], pools: tuple[Constraint, ...]
    ) -> bool:
        """§2.7: the C0 preconditions of a known USD aggregate.

        Every active route needs a known USD limit, and every USD pool with two
        or more active consumers needs a known bound.  When either is missing
        the aggregate is unknown with its floor and ceiling, never a number the
        envelope would refuse.
        """
        active = [route for route in routes if route.status in ACTIVE_ROUTE_STATUSES]
        for route in active:
            if route.limit.unit != "usd" or route.limit.status != "known":
                return False
        for pool in pools:
            if pool.bound.unit != "usd":
                continue
            consumers = [
                route
                for route in active
                if pool.constraint_id in route.consumes or route.route_id in pool.shared_by
            ]
            if len(consumers) >= 2 and pool.bound.status != "known":
                return False
        return True

    def _witness(
        self, pessimistic: JointSolution, active: tuple[str, ...]
    ) -> tuple[WitnessAllocation, ...]:
        """§2.7: the pessimistic witness plus each route's own fixed action."""
        if self.contradiction is not None or self.branch_infeasible_on_one:
            # §2.6: no allocation that honours the asserted actions is feasible
            # in every branch, so there is nothing to witness.
            return ()
        allocations = (
            dict(pessimistic.witness) if pessimistic.determined else dict(pessimistic.floor_witness)
        )
        out: list[WitnessAllocation] = []
        for route_id in active:
            if route_id not in allocations:
                continue
            fixed = Fraction(0)
            if self._is_fixed(route_id):
                fixed = self.action_views[route_id].usd["pessimistic"]
            out.append(
                WitnessAllocation(
                    route_id,
                    Quantity.known(_floor_text(allocations[route_id] + fixed), "usd"),
                )
            )
        return tuple(out)

    def _inputs(
        self,
        pessimistic: JointSolution,
        optimistic: JointSolution | None,
        ceiling: JointSolution,
        routes: tuple[RouteBound, ...],
        pools: tuple[Constraint, ...],
    ) -> dict[str, Any]:
        assert self.read is not None
        ceiling_value = (
            ceiling.value if ceiling.determined else ceiling.ceiling_when_unknowns_relaxed
        )
        path_records: list[dict[str, Any]] = []
        for path in self.paths:
            fee = self.fee.get(path.path_id)
            registered = self.registered.get(path.path_id)
            resolutions = {}
            for name, resolution in (
                ("shelf_usage", registered.usage if registered else None),
                ("continuing_offering", registered.continuing if registered else None),
                ("programme_reservation", registered.reservation if registered else None),
            ):
                resolutions[name] = None if resolution is None else _resolution_record(resolution)
            path_records.append(
                {
                    "path_id": path.path_id,
                    "as_of": _text(path.body.get("as_of")),
                    "available_at": _iso(path.available),
                    "form": path.form,
                    "registration_family": path.family,
                    "automatic_shelf": path.automatic,
                    "classification": path.classification,
                    "reason": path.reason,
                    "window_start": path.window_start,
                    "window_end": path.window_end,
                    "accessions": list(path.accessions),
                    "fee_table_accession": None if fee is None else fee.accession,
                    "registered_amount": None if fee is None else fee.registered.as_record(),
                    "pool_bound": None if registered is None else registered.bound.as_record(),
                    "resolutions": resolutions,
                    "consulted_rules": sorted(self.path_rules[path.path_id]),
                }
            )
        kernel_record: dict[str, str] = {
            "evidence": sha256_of(pessimistic.as_record()),
            "ceiling": sha256_of(ceiling.as_record()),
        }
        if optimistic is not None:
            kernel_record["optimistic"] = sha256_of(optimistic.as_record())
        return {
            "adapter": "capital_structure.capacity.c2_adapter.v1",
            "implementation": IMPLEMENTATION,
            "state_id": self.state.state_id,
            "scenario_id": self.scenario.scenario_id,
            "issuer_id": self.state.request.issuer_id,
            "view_mode": self.state.request.view_mode,
            "scenario_view": self.scenario.view,
            "as_of": self.state.request.as_of,
            "generated_at": self.state.generated_at,
            "sale_date": self.sale_iso,
            "horizon_end": self.scenario.horizon_end,
            "request_rule_pack_digest": self.state.request.rule_pack_digest,
            "rule_pack_digest": self.rules.digest,
            "rule_texts": {
                "unknowns": [item.as_record() for item in self.rule_unknowns],
                "conditions": list(self.rule_conditions),
                "excluded": list(self.rule_excluded),
                "consulted": sorted(
                    {rule_id for rule_ids in self.path_rules.values() for rule_id in rule_ids}
                ),
                "absent_from_pack": sorted(self.absent_rules),
            },
            "price": self._price_record(),
            "branches": list(self.branch_reasons),
            "fee_rate": self.scenario.fee_rate,
            "discount_rate": self.scenario.discount_rate,
            "assumptions": [
                _resolution_record(self.resolutions[key]) for key in sorted(self.resolutions)
            ],
            "scenario_assumptions": [[key, value] for key, value in sorted(self.assumptions.items())],
            "exclusive_groups": self._exclusive_record(),
            "programme_usage": {
                path_id: self.programme_usage_inputs[path_id]
                for path_id in sorted(self.programme_usage_inputs)
            },
            "actions_applied": self._actions_record(),
            "remaining_capacity": self._remaining_record(),
            "registration_paths": path_records,
            "baby_shelf": self.baby_shelf_inputs,
            "nasdaq": self.nasdaq_inputs,
            "routes": [route.as_record() for route in routes],
            "pools": [pool.as_record() for pool in pools],
            "ignored_schemas": list(self.read.ignored_schemas),
            "excluded_after_as_of": dict(self.read.excluded_after_as_of),
            "kernel": kernel_record,
            "ceiling_call": {
                "determined": ceiling.determined,
                "value": _fraction_text(ceiling_value),
                "reported_as": "aggregate_note_and_inputs_only_never_the_aggregate",
            },
            "blockers": sorted(set(self.blockers)),
            "unknowns": [item.as_record() for item in _dedupe_unknowns(self.unknowns)],
        }

    def _exclusive_record(self) -> dict[str, Any]:
        """``inputs["exclusive_groups"]`` (§2.4), including what was dropped."""
        return {
            "declared": [list(group) for group in self.exclusive_declared],
            "groups": [list(group) for group in self.exclusive_groups],
            "dropped": list(self.exclusive_dropped),
            "recorded_not_passed": [list(group) for group in self.exclusive_not_passed],
        }

    def _actions_record(self) -> list[dict[str, Any]]:
        """``inputs["actions_applied"]`` (§2.6), sorted by route id."""
        out: list[dict[str, Any]] = []
        for route_id in sorted(self.action_views):
            view = self.action_views[route_id]
            out.append(
                {
                    "route_id": route_id,
                    "action": view.action,
                    "settlement": view.settlement,
                    "fixed": view.fixed,
                    "applied": view.applied,
                    "usd_pessimistic": _money_text(view.usd.get("pessimistic")),
                    "usd_optimistic": _money_text(view.usd.get("optimistic")),
                    "conditions_assumed_met": list(view.conditions_assumed_met),
                }
            )
        return out

    def _remaining_record(self) -> dict[str, Any]:
        """``inputs["remaining_capacity"]`` (§2.6): residual limits and bounds per branch."""
        branches = BRANCHES if self.branching else ("pessimistic",)
        return {
            branch: {
                "routes": [
                    [route_id, _fraction_text(self.residual_routes[branch].get(route_id))]
                    for route_id in sorted(self.residual_routes[branch])
                ],
                "pools": [
                    [pool_id, _fraction_text(self.residual_pools[branch].get(pool_id))]
                    for pool_id in sorted(self.residual_pools[branch])
                ],
                "fixed_total": _money_text(self.fixed_totals[branch]),
            }
            for branch in branches
        }


def _floor_text(value: Fraction) -> str:
    return format(decimal_floor(value), "f")


def _resolution_record(resolution: Any) -> dict[str, Any]:
    return {
        "unknown_id": resolution.unknown_id,
        "assumed": resolution.assumed.as_record(),
        "rationale": resolution.rationale,
    }


__all__ = [
    "AUTOMATIC_SHELF_FORMS",
    "BABY_SHELF_RULES",
    "BRANCHES",
    "CapacityEvaluation",
    "CapacityInputError",
    "CapacityRuleTextUnavailable",
    "DOCUMENT_TERM_SCHEMA",
    "FEE_TABLE_TERM_NAME",
    "IMPLEMENTATION",
    "NASDAQ_OFFERING_ASSUMPTIONS",
    "NASDAQ_RULE_ID",
    "REGISTRATION_PATH_SCHEMA",
    "REFERENCE_PACK_MANIFEST_ID",
    "ROUTE_EXCLUSIVITY_KEY",
    "SHARE_BASIS_RESULT_SCHEMA",
    "SHARE_COUNT_SCHEMAS",
    "SHELF_FAMILIES",
    "bind_funding_schedule",
    "evaluate_capacity",
    "explain_capacity",
]
