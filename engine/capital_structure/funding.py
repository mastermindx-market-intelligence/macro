"""Capital Structure V2 task F1: a dated funding schedule over the F0 binding.

``project_funding`` turns bound financial item observations, one family of
bound commitments (covenant terms or document terms) and a financing scenario
into a :class:`FundingSchedule` on the frozen C0 contract.

The schedule is deliberately narrow:

* An opening balance is the exact sum of every member of the named cash basis,
  measured on one date at or before the horizon start.  A missing member makes
  the opening unknown — never a partial sum — and members measured on
  different dates refuse.  Receivables, revolver availability and registered
  capacity belong to no basis.
* Net loss is never burn (A29).  Burn enters only through an explicit
  ``burn_basis`` assumption naming an operating-cash-flow period or a scenario
  rate.  A non-negative operating cash flow models no burn and implies no
  runway; an unknown burn makes every closing unknown.  Periods stop at the
  horizon end: there is no runway figure and no extrapolation.
* Obligations enter periods only when dated.  Gross, net and fees stay apart:
  a net figure is reported in a note and never substituted for gross (A30).
* Every assumed or scenario financing proceed, every undrawn conditional
  commitment and every conversion relief is a ``conditional`` flow naming its
  condition, so none of them reaches a balance identity.  Registered capacity
  is never a source of any kind.

The function is a pure function of its three arguments: no file, network,
clock, collector or model access.  No probability, score, rank or sizing is
produced (A48).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from engine.capital_structure.issuer_state_contracts import (
    CASH_BASES,
    Assumption,
    CalculationReceipt,
    CommitmentInputs,
    ContractViolation,
    FinancialInputs,
    FinancingScenario,
    Flow,
    FundingPeriod,
    FundingSchedule,
    Provenance,
    Quantity,
    Unknown,
    sha256_of,
    stable_id,
)

__all__ = [
    "CASH_BASIS_MEMBERS",
    "CASH_ROUTES",
    "CONTEXT_KINDS",
    "FINANCIAL_ITEM_SCHEMA",
    "FORBIDDEN_FIELDS",
    "FundingInputError",
    "IMPLEMENTATION",
    "ITEM_RULES",
    "NOT_BUILT_FLOW_KINDS",
    "RULES",
    "RULE_DIGEST",
    "project_funding",
]

FINANCIAL_ITEM_SCHEMA = "capital_structure.financial_item_observation.v1"
IMPLEMENTATION = "engine.capital_structure.funding.project_funding/1"


class FundingInputError(ValueError):
    """An input the funding schedule refuses to interpret."""


# ---------------------------------------------------------------------------
# Rulebook (mirrors config/capital_structure_financial_input_binding.v1.json;
# a parity test pins the two together — this module never reads the file)
# ---------------------------------------------------------------------------


def _item_rule(availability: str, flow_role: str, cash_bases: tuple[str, ...], measure: str, owner_state: str) -> dict[str, Any]:
    return {
        "availability": availability,
        "flow_role": flow_role,
        "cash_bases": cash_bases,
        "measure": measure,
        "owner_state": owner_state,
    }


ITEM_RULES: dict[str, dict[str, Any]] = {
    "unrestricted_cash": _item_rule(
        "available_now",
        "opening_balance_component",
        ("unrestricted_cash", "unrestricted_cash_and_marketable_securities", "unrestricted_and_restricted_cash"),
        "instant",
        "fif_cell_exists_cs_binding_blocked",
    ),
    "restricted_cash": _item_rule("restricted", "opening_balance_component", ("unrestricted_and_restricted_cash",), "instant", "not_built"),
    "marketable_securities": _item_rule(
        "available_after_sale",
        "opening_balance_component",
        ("unrestricted_cash_and_marketable_securities",),
        "instant",
        "fif_cell_exists_cs_binding_blocked",
    ),
    "receivables": _item_rule("collection_dependent", "context_only", (), "instant", "fif_cell_exists_cs_binding_blocked"),
    "revolver_availability": _item_rule("conditional_undrawn", "conditional_source", (), "instant", "not_built"),
    "accrued_interest": _item_rule("obligation", "use", (), "instant", "not_built"),
    "debt_maturity": _item_rule("obligation", "use", (), "dated", "not_built"),
    "minimum_liquidity_covenant": _item_rule("floor", "period_minimum_liquidity", (), "instant", "term_name_emitted_value_unnormalized"),
    "committed_expenditure": _item_rule("obligation", "use", (), "dated", "not_built"),
    "financing_cost": _item_rule("obligation", "use", (), "dated", "fee_table_rows_only"),
}

CONTEXT_KINDS: tuple[str, ...] = (
    "operating_cash_flow",
    "net_loss",
    "historical_capital_expenditures",
    "undated_debt_balance",
    "registered_offering_capacity",
)

CASH_BASIS_MEMBERS: dict[str, tuple[str, ...]] = {
    "unrestricted_cash": ("unrestricted_cash",),
    "unrestricted_cash_and_marketable_securities": ("unrestricted_cash", "marketable_securities"),
    "unrestricted_and_restricted_cash": ("unrestricted_cash", "restricted_cash"),
    "unknown": (),
}
if set(CASH_BASIS_MEMBERS) != set(CASH_BASES):  # pragma: no cover - drift guard against the C0 enum
    raise ImportError("funding.CASH_BASIS_MEMBERS must name exactly the C0 CASH_BASES")

FORBIDDEN_FIELDS: tuple[str, ...] = ("probability", "score", "rank", "size", "signal", "runway_infinite")

#: Kinds with no current owner that would enter the schedule as flows; an
#: absent one is a named Unknown, never a zero.
NOT_BUILT_FLOW_KINDS: tuple[str, ...] = (
    "restricted_cash",
    "revolver_availability",
    "accrued_interest",
    "debt_maturity",
    "committed_expenditure",
)

#: Scenario routes whose execution would deliver cash proceeds.
CASH_ROUTES: tuple[str, ...] = (
    "shelf_takedown",
    "at_the_market",
    "equity_line",
    "registered_direct",
    "pipe",
    "debt_draw",
)
_RELIEF_ROUTES = ("conversion", "exchange")
_OUTFLOW_ROUTES = ("repurchase", "redemption")
_NO_CASH_WARRANT_SETTLEMENTS = ("cashless", "net_share", "pre_funded")
_GROSS_NET = ("gross", "net", "fee", "not_applicable")
_QUANTITY_STATUSES = ("known", "unknown", "not_applicable", "contradicted", "withheld")
_QUANTUM = Decimal("0.01")
_CTX = Context(prec=60, rounding=ROUND_HALF_EVEN)

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,199}$")
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_OCF_BASIS = re.compile(r"^operating_cash_flow:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$")
_FIXED_BASIS = re.compile(r"^fixed_usd_per_day:(.+)$")

_NOT_SUPPLIED = "not supplied by the scenario"
_UNHONORED = "an assumed balance or flow is never cash; F1 honors only the minimum-liquidity floor"
_PARTIAL_COVERAGE_NOTE = "over observed dated flows only; see unknowns"
_MIN_LIQUIDITY_ID = "unknown:minimum_liquidity"

RULES: dict[str, Any] = {
    "schema": FINANCIAL_ITEM_SCHEMA,
    "implementation": IMPLEMENTATION,
    "items": {kind: {**rule, "cash_bases": list(rule["cash_bases"])} for kind, rule in ITEM_RULES.items()},
    "context_kinds": list(CONTEXT_KINDS),
    "cash_basis_members": {basis: list(members) for basis, members in CASH_BASIS_MEMBERS.items()},
    "forbidden_fields": list(FORBIDDEN_FIELDS),
    "not_built_flow_kinds": list(NOT_BUILT_FLOW_KINDS),
    "cash_routes": list(CASH_ROUTES) + ["warrant_exercise settled in cash"],
    "relief_routes": list(_RELIEF_ROUTES),
    "outflow_routes": list(_OUTFLOW_ROUTES),
    "point_in_time": "a fact or commitment is considered only when its available_at is at or before scenario.as_of",
    "opening_balance": (
        "exact sum of every basis member's latest known fact measured at or before horizon_start; "
        "a missing member, a same-date disagreement or members on different dates make the opening unknown; "
        "a later non-known observation of a member is never skipped in favor of an older known one"
    ),
    "burn_basis_forms": ["unknown", "operating_cash_flow:<start>:<end>", "fixed_usd_per_day:<non-negative decimal>"],
    "burn_basis_refused": "any value starting net_loss: net loss is not burn",
    "burn_basis_days": "inclusive calendar days from period_start to period_end (a reported duration covers both endpoints)",
    "working_capital_basis_forms": ["excluded", "unknown"],
    "seasonality_basis_forms": ["flat", "unknown"],
    "period_grid": (
        "calendar quarter ends strictly inside (horizon_start, horizon_end) plus horizon_end; "
        "a dated flow belongs to the period with start < date <= end (period 1 also takes date == horizon_start); "
        "period days are elapsed calendar days end - start; no period extends past horizon_end"
    ),
    "quantization": "0.01 usd, ROUND_HALF_EVEN, for burn, price-converted proceeds and fees",
    "balance_identity": "closing = opening + non-conditional sources - non-conditional uses; conditional flows never count",
    "deficit": "a negative computed closing is reported unknown with its computed value in the note; the next opening is unknown",
    "gap": "max(0, minimum_liquidity - computed closing) when both are known; otherwise unknown",
}
RULE_DIGEST = sha256_of(RULES)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _fmt(value: Decimal) -> str:
    text = format(value, "f")
    if text.startswith("-") and Decimal(text) == 0:
        text = text[1:]  # never emit a negative zero
    return text


def _q(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_EVEN, context=_CTX)


def _usd(value: Decimal, note: str | None = None, provenance: Provenance | None = None) -> Quantity:
    return Quantity(unit="usd", status="known", value=_fmt(value), note=note, provenance=provenance)


def _usd_unknown(note: str | None = None, status: str = "unknown") -> Quantity:
    return Quantity(unit="usd", status=status, value=None, note=note)


def _join(parts: Sequence[str | None]) -> str | None:
    kept = [part for part in parts if part]
    return "; ".join(kept) if kept else None


def _parse_date(value: Any, field_name: str) -> date:
    if not isinstance(value, str):
        raise FundingInputError(f"{field_name}: ISO date required, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FundingInputError(f"{field_name}: {value!r} is not an ISO date") from exc


def _parse_timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FundingInputError(f"{field_name}: ISO timestamp required, got {value!r}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FundingInputError(f"{field_name}: {value!r} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise FundingInputError(f"{field_name}: timestamp must carry a timezone")
    return parsed


def _decimal_text(value: Any, field_name: str, *, nonnegative: bool) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise FundingInputError(f"{field_name}: decimal required, got {value!r}")
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str) or not _DECIMAL.match(value):
        raise FundingInputError(f"{field_name}: decimal string required, got {value!r}")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - the regex already excludes
        raise FundingInputError(f"{field_name}: {value!r} is not a decimal") from exc
    if nonnegative and number < 0:
        raise FundingInputError(f"{field_name}: must be non-negative, got {value!r}")
    return number


def _scan_forbidden(value: Any, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in FORBIDDEN_FIELDS:
                raise FundingInputError(f"{path}.{key}: forbidden field")
            _scan_forbidden(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_forbidden(item, f"{path}[{index}]")


class _Unknowns:
    """Ordered, de-duplicated Unknown collector."""

    def __init__(self) -> None:
        self._items: dict[str, Unknown] = {}

    def add(self, unknown_id: str, description: str, resolving_fact: str, affects: Sequence[str]) -> None:
        if unknown_id not in self._items:
            self._items[unknown_id] = Unknown(
                unknown_id=unknown_id,
                description=description,
                resolving_fact=resolving_fact,
                affects=tuple(affects),
            )

    def discard(self, unknown_id: str) -> None:
        self._items.pop(unknown_id, None)

    def __contains__(self, unknown_id: str) -> bool:
        return unknown_id in self._items

    def ids(self) -> list[str]:
        return list(self._items)

    def sorted(self) -> tuple[Unknown, ...]:
        return tuple(self._items[key] for key in sorted(self._items))


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Fact:
    item_id: str
    kind: str
    amount: Quantity
    raw_value: Decimal | None
    measured_at: date | None
    period_start: date | None
    period_end: date | None
    due_date: date | None
    gross_net: str | None
    condition: str | None
    receipt_sha256: str | None
    available_at: str
    excluded: bool = False  # reported in a unit other than usd; never counted


def _intake(financials: FinancialInputs, as_of: datetime, unknowns: _Unknowns) -> list[_Fact]:
    admitted: list[_Fact] = []
    seen: set[str] = set()
    for index, record in enumerate(financials.facts):
        label = f"financials.facts[{index}]"
        _scan_forbidden(record, label)
        kind = record.get("item_kind")
        if kind not in ITEM_RULES and kind not in CONTEXT_KINDS:
            raise FundingInputError(f"{label}.item_kind: {kind!r} is not a bound financial item kind")
        item_id = record.get("item_id")
        if not isinstance(item_id, str) or not _ID.match(item_id):
            raise FundingInputError(f"{label}.item_id: identifier required, got {item_id!r}")
        if kind in ITEM_RULES:
            availability = record.get("availability")
            expected = ITEM_RULES[kind]["availability"]
            if availability != expected:
                raise FundingInputError(f"{label}.availability: {kind} is {expected!r}, record says {availability!r}")
        available_at = record.get("available_at")
        if _parse_timestamp(available_at, f"{label}.available_at") > as_of:
            continue  # then-known: a fact not yet available is excluded entirely
        if item_id in seen:
            raise FundingInputError(f"{label}.item_id: duplicate available item {item_id!r}")
        seen.add(item_id)

        amount = record.get("amount")
        if not isinstance(amount, Mapping):
            raise FundingInputError(f"{label}.amount: mapping required")
        measured_at = _optional_date(record.get("measured_at"), f"{label}.measured_at")
        period_start = _optional_date(record.get("period_start"), f"{label}.period_start")
        period_end = _optional_date(record.get("period_end"), f"{label}.period_end")
        due_date = _optional_date(record.get("due_date"), f"{label}.due_date")
        if amount.get("unit") != "usd":
            unknowns.add(
                f"unknown:unit:{item_id}",
                f"{kind} {item_id} is reported in {amount.get('unit')!r}, not usd; it is excluded rather than converted",
                f"a usd-denominated {FINANCIAL_ITEM_SCHEMA} record for {item_id}",
                ("opening_balance", "closing_balance"),
            )
            # excluded from every computation, but it still shows the kind has an owner
            admitted.append(
                _Fact(item_id, kind, _usd_unknown("non-usd unit excluded"), None, measured_at, period_start, period_end, due_date, None, None, None, available_at, True)
            )
            continue
        status = amount.get("status")
        if status not in _QUANTITY_STATUSES:
            raise FundingInputError(f"{label}.amount.status: {status!r} not in {list(_QUANTITY_STATUSES)}")
        raw_value: Decimal | None = None
        if status == "known":
            raw_value = _decimal_text(amount.get("value"), f"{label}.amount.value", nonnegative=kind not in CONTEXT_KINDS)
            quantity = _usd(raw_value) if raw_value >= 0 else _usd_unknown(f"reported {_fmt(raw_value)} usd")
        else:
            quantity = _usd_unknown(status=status)

        if ITEM_RULES.get(kind, {}).get("flow_role") == "opening_balance_component" and measured_at is None:
            raise FundingInputError(f"{label}.measured_at: a balance item needs its measurement date")
        gross_net = record.get("gross_net")
        if ITEM_RULES.get(kind, {}).get("flow_role") == "use" and gross_net not in _GROSS_NET:
            raise FundingInputError(f"{label}.gross_net: {gross_net!r} not in {list(_GROSS_NET)}")
        source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
        condition = record.get("condition")
        admitted.append(
            _Fact(
                item_id=item_id,
                kind=kind,
                amount=quantity,
                raw_value=raw_value,
                measured_at=measured_at,
                period_start=period_start,
                period_end=period_end,
                due_date=due_date,
                gross_net=gross_net,
                condition=condition if isinstance(condition, str) and condition else None,
                receipt_sha256=source.get("receipt_sha256") if isinstance(source.get("receipt_sha256"), str) else None,
                available_at=available_at,
            )
        )
    return admitted


def _optional_date(value: Any, field_name: str) -> date | None:
    if value is None:
        return None
    return _parse_date(value, field_name)


# ---------------------------------------------------------------------------
# Opening balance
# ---------------------------------------------------------------------------


def _opening(
    basis: str,
    facts: list[_Fact],
    horizon_start: date,
    generation_id: str | None,
    unknowns: _Unknowns,
) -> tuple[Quantity, Decimal | None]:
    if basis == "unknown":
        unknowns.add(
            "unknown:cash_basis",
            "the cash basis is unknown, so no opening balance can be composed",
            "a named cash basis on the financial inputs",
            ("opening_balance",),
        )
        return _usd_unknown("cash basis unknown"), None

    members = CASH_BASIS_MEMBERS[basis]
    chosen: dict[str, tuple[date, Decimal, str]] = {}
    failed = False
    for kind in members:
        same_kind = [fact for fact in facts if fact.kind == kind and not fact.excluded]
        dated = [fact for fact in same_kind if fact.measured_at is not None and fact.measured_at <= horizon_start]
        known = [fact for fact in dated if fact.amount.status == "known"]
        if not known:
            owner = ITEM_RULES[kind]["owner_state"]
            description = (
                f"no current owner emits {kind}; the {basis} opening balance is unknown, never a partial sum"
                if owner == "not_built"
                else f"no known {kind} observation at or before {horizon_start.isoformat()}; the {basis} opening balance is unknown, never a partial sum"
            )
            unknowns.add(
                f"unknown:opening:{kind}",
                description,
                f"an owner emitting a {FINANCIAL_ITEM_SCHEMA} {kind} record at the basis date",
                ("opening_balance",),
            )
            failed = True
            continue
        latest = max(fact.measured_at for fact in known if fact.measured_at is not None)
        later_unresolved = [fact for fact in dated if fact.amount.status != "known" and fact.measured_at is not None and fact.measured_at > latest]
        if later_unresolved:
            unknowns.add(
                f"unknown:opening:{kind}",
                f"the latest {kind} observation ({later_unresolved[0].measured_at.isoformat()}) is {later_unresolved[0].amount.status}; an older known value is never substituted",
                f"a known {kind} observation at its latest measurement date",
                ("opening_balance",),
            )
            failed = True
            continue
        values = {fact.raw_value for fact in known if fact.measured_at == latest}
        if len(values) > 1:
            unknowns.add(
                f"unknown:opening:contradicted:{kind}",
                f"{kind} observations measured {latest.isoformat()} disagree ({', '.join(sorted(_fmt(v) for v in values if v is not None))}); neither is chosen",
                f"one reconciled {kind} observation for {latest.isoformat()}",
                ("opening_balance",),
            )
            failed = True
            continue
        value = next(iter(values))
        assert value is not None
        stamp = max(fact.available_at for fact in known if fact.measured_at == latest)
        chosen[kind] = (latest, value, stamp)

    if failed:
        return _usd_unknown(f"{basis} opening balance unknown; see unknowns"), None
    dates = {entry[0] for entry in chosen.values()}
    if len(dates) > 1:
        unknowns.add(
            "unknown:opening:date_mismatch",
            f"{basis} members are measured on different dates ({', '.join(sorted(d.isoformat() for d in dates))}); the newest is never picked",
            f"every {basis} member measured on one date",
            ("opening_balance",),
        )
        return _usd_unknown(f"{basis} members measured on different dates"), None
    measured = next(iter(dates))
    total = sum((entry[1] for entry in chosen.values()), Decimal(0))
    if measured < horizon_start:
        unknowns.add(
            "unknown:interim_flows",
            f"cash flows between the basis measurement ({measured.isoformat()}) and the horizon start ({horizon_start.isoformat()}) are not observed",
            f"a {basis} measurement at {horizon_start.isoformat()}",
            ("opening_balance", "closing_balance"),
        )
    provenance = Provenance(
        input_family="financials",
        generation_id=generation_id,
        available_at=max(entry[2] for entry in chosen.values()),
    )
    return _usd(total, note=f"{basis} measured {measured.isoformat()}", provenance=provenance), total


# ---------------------------------------------------------------------------
# Assumptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Burn:
    per_day: Decimal | None  # None means unknown
    label: str
    closing_note: str | None


def _burn(value: str | None, facts: list[_Fact], unknowns: _Unknowns) -> tuple[_Burn, Assumption]:
    def unknown_burn(rationale: str, description: str) -> tuple[_Burn, Assumption]:
        unknowns.add(
            "unknown:burn_basis",
            description,
            "a burn_basis assumption naming an operating-cash-flow period with a known value, or a scenario rate",
            ("closing_balance", "gap"),
        )
        return _Burn(None, "unknown", None), Assumption("burn_basis", "unknown" if value is None else value, rationale)

    if value is None:
        return unknown_burn(_NOT_SUPPLIED, "no burn basis was supplied; every closing balance is unknown and no runway is implied")
    if value.startswith("net_loss"):
        raise FundingInputError("net loss is not burn")
    if value == "unknown":
        return unknown_burn("the scenario states burn is unknown", "burn is unknown; every closing balance is unknown and no runway is implied")
    fixed = _FIXED_BASIS.match(value)
    if fixed:
        rate = _decimal_text(fixed.group(1), "burn_basis.fixed_usd_per_day", nonnegative=True)
        note = None if rate > 0 else "scenario burn zero; no burn modeled and no runway implied"
        return (
            _Burn(rate, value, note),
            Assumption("burn_basis", value, f"scenario-stated burn of {_fmt(rate)} usd per day; an assumption, not an observation"),
        )
    ocf = _OCF_BASIS.match(value)
    if not ocf:
        raise FundingInputError(f"burn_basis: {value!r} is not unknown, operating_cash_flow:<start>:<end> or fixed_usd_per_day:<rate>")
    start = _parse_date(ocf.group(1), "burn_basis.period_start")
    end = _parse_date(ocf.group(2), "burn_basis.period_end")
    if end < start:
        raise FundingInputError("burn_basis: the operating-cash-flow period ends before it starts")
    matches = [
        fact
        for fact in facts
        if fact.kind == "operating_cash_flow" and not fact.excluded and fact.period_start == start and fact.period_end == end
    ]
    known = {fact.raw_value for fact in matches if fact.raw_value is not None}
    period = f"{start.isoformat()}..{end.isoformat()}"
    if not matches or len(known) != 1 or any(fact.raw_value is None for fact in matches):
        reason = "no" if not matches else "no single known"
        return unknown_burn(
            f"{reason} operating cash flow observation for {period}",
            f"{reason} operating cash flow observation for {period}; burn is unknown and every closing balance is unknown",
        )
    observed = next(iter(known))
    days = (end - start).days + 1
    ids = ", ".join(sorted(fact.item_id for fact in matches))
    rationale = f"operating cash flow {_fmt(observed)} usd over {period} ({days} days), observation {ids}"
    if observed >= 0:
        note = f"operating cash flow non-negative over {period}; no burn modeled and no runway implied"
        return _Burn(Decimal(0), value, note), Assumption("burn_basis", value, rationale)
    per_day = _CTX.divide(-observed, Decimal(days))
    return _Burn(per_day, value, None), Assumption("burn_basis", value, rationale)


def _simple_assumption(key: str, value: str | None, accepted: str, accepted_rationale: str, description: str, unknowns: _Unknowns) -> tuple[bool, Assumption]:
    if value == accepted:
        return True, Assumption(key, value, accepted_rationale)
    if value is None or value == "unknown":
        unknowns.add(
            f"unknown:{key}",
            description,
            f"a {key} assumption of {accepted!r}",
            ("closing_balance", "gap"),
        )
        return False, Assumption(key, "unknown", _NOT_SUPPLIED if value is None else f"the scenario states {key} is unknown")
    raise FundingInputError(f"{key}: {value!r} must be {accepted!r} or 'unknown'")


# ---------------------------------------------------------------------------
# Period grid
# ---------------------------------------------------------------------------


def _quarter_ends(start: date, end: date) -> list[date]:
    out = []
    for year in range(start.year, end.year + 1):
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            boundary = date(year, month, day)
            if start < boundary < end:
                out.append(boundary)
    return out


def _grid(start: date, end: date) -> list[tuple[date, date]]:
    if start == end:
        return []
    bounds = _quarter_ends(start, end) + [end]
    periods = []
    previous = start
    for boundary in bounds:
        periods.append((previous, boundary))
        previous = boundary
    return periods


def _period_index(grid: list[tuple[date, date]], when: date) -> int | None:
    for index, (start, end) in enumerate(grid):
        if start < when <= end or (index == 0 and when == start):
            return index
    return None


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


class _Ledger:
    def __init__(self, count: int) -> None:
        self.sources: list[list[Flow]] = [[] for _ in range(count)]
        self.uses: list[list[Flow]] = [[] for _ in range(count)]

    def add(self, index: int, flow: Flow) -> None:
        (self.sources if flow.kind == "source" else self.uses)[index].append(flow)

    def replace(self, flow_id: str, flow: Flow) -> bool:
        for bucket in (*self.sources, *self.uses):
            for position, existing in enumerate(bucket):
                if existing.flow_id == flow_id:
                    bucket[position] = flow
                    return True
        return False

    def find(self, flow_id: str) -> Flow | None:
        for bucket in (*self.sources, *self.uses):
            for existing in bucket:
                if existing.flow_id == flow_id:
                    return existing
        return None


def _scenario_amount(action: Any, scenario: FinancingScenario, unknowns: _Unknowns) -> tuple[Quantity, Decimal | None]:
    quantity = action.quantity
    if quantity is not None and quantity.status == "known" and quantity.unit == "usd":
        value = Decimal(quantity.value)
        return _usd(value), value
    price = scenario.price
    if (
        quantity is not None
        and quantity.status == "known"
        and quantity.unit == "shares"
        and price.kind == "fixed"
        and price.currency == "USD"
        and price.fixed_price is not None
    ):
        value = _q(_CTX.multiply(Decimal(quantity.value), Decimal(price.fixed_price)))
        return _usd(value, note="price assumption"), value
    unknowns.add(
        f"unknown:action_amount:{action.route_id}",
        f"scenario action {action.route_id} ({action.action}) has no usd amount and no fixed usd price conversion",
        f"a known usd quantity, or known shares with a fixed USD price, for {action.route_id}",
        ("conditional_flows",),
    )
    return _usd_unknown("scenario amount unknown"), None


def _condition_text(action: Any) -> str:
    met = ", ".join(action.conditions_assumed_met) if action.conditions_assumed_met else "none"
    return f"scenario action not executed; conditions assumed met: {met}"


# ---------------------------------------------------------------------------
# Commitments
# ---------------------------------------------------------------------------


def _get(record: Mapping[str, Any], *path: str) -> Any:
    value: Any = record
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _floor_from_covenants(commitments: CommitmentInputs, as_of: datetime, unknowns: _Unknowns) -> Quantity:
    admitted: dict[Decimal, set[str]] = {}
    for index, record in enumerate(commitments.commitments):
        label = f"commitments[{index}]"
        if _get(record, "term", "name") != "minimum_liquidity_amount":
            continue  # ratios and baskets are not liquidity
        if _get(record, "state", "disposition") != "direct" or _get(record, "normalized", "unit") != "USD":
            continue
        raw = _get(record, "normalized", "value")
        if isinstance(raw, float):
            raw = str(raw)
        try:
            value = _decimal_text(raw, f"{label}.normalized.value", nonnegative=True)
        except FundingInputError:
            continue  # not a non-negative decimal: not admitted
        if _parse_timestamp(_get(record, "point_in_time", "available_at"), f"{label}.point_in_time.available_at") > as_of:
            continue
        accession = _get(record, "filing", "accession")
        admitted.setdefault(value, set()).add(str(accession) if accession else "unknown accession")
    if len(admitted) == 1:
        value, accessions = next(iter(admitted.items()))
        return _usd(value, note=f"minimum liquidity covenant, filing {', '.join(sorted(accessions))}")
    if len(admitted) > 1:
        values = ", ".join(_fmt(value) for value in sorted(admitted))
        unknowns.add(
            _MIN_LIQUIDITY_ID,
            f"direct minimum-liquidity covenant observations disagree ({values} usd); neither is chosen",
            "one reconciled minimum_liquidity_amount covenant term",
            ("minimum_liquidity", "gap"),
        )
        return _usd_unknown(f"covenant values disagree: {values} usd", status="contradicted")
    unknowns.add(
        _MIN_LIQUIDITY_ID,
        "no direct USD minimum_liquidity_amount covenant term is available at the scenario as-of",
        "a direct minimum_liquidity_amount covenant term in USD",
        ("minimum_liquidity", "gap"),
    )
    return _usd_unknown("no direct minimum-liquidity covenant observed")


def _registration_fees(commitments: CommitmentInputs, as_of: datetime) -> list[tuple[str, Decimal, date | None, str]]:
    out = []
    for index, record in enumerate(commitments.commitments):
        label = f"commitments[{index}]"
        if _get(record, "term", "name") != "registration_fee":
            continue  # registered capacity and offering prices are never a source
        if _get(record, "state", "disposition") != "observed" or _get(record, "normalized", "unit") != "USD":
            continue
        raw = _get(record, "normalized", "value")
        if raw is None:
            continue
        if isinstance(raw, float):
            raw = str(raw)
        value = _decimal_text(raw, f"{label}.normalized.value", nonnegative=True)
        if _parse_timestamp(_get(record, "point_in_time", "available_at"), f"{label}.point_in_time.available_at") > as_of:
            continue
        observation_id = record.get("observation_id")
        if not isinstance(observation_id, str) or not _ID.match(observation_id):
            raise FundingInputError(f"{label}.observation_id: identifier required, got {observation_id!r}")
        filed = _optional_date(_get(record, "filing", "filing_date"), f"{label}.filing.filing_date")
        accession = _get(record, "filing", "accession")
        out.append((observation_id, value, filed, str(accession) if accession else "unknown accession"))
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def project_funding(financials: FinancialInputs, commitments: CommitmentInputs, scenario: FinancingScenario) -> FundingSchedule:
    """Project a dated funding schedule; see the module docstring for the rules."""
    try:
        return _project(financials, commitments, scenario)
    except ContractViolation as exc:
        raise FundingInputError(f"funding schedule refused by the C0 contract: {exc}") from exc


def _project(financials: FinancialInputs, commitments: CommitmentInputs, scenario: FinancingScenario) -> FundingSchedule:
    if not isinstance(financials, FinancialInputs):
        raise FundingInputError("financials: FinancialInputs required")
    if not isinstance(commitments, CommitmentInputs):
        raise FundingInputError("commitments: CommitmentInputs required")
    if not isinstance(scenario, FinancingScenario):
        raise FundingInputError("scenario: FinancingScenario required")

    as_of = _parse_timestamp(scenario.as_of, "scenario.as_of")
    horizon_start = date.fromisoformat(scenario.horizon_start)
    horizon_end = date.fromisoformat(scenario.horizon_end)
    unknowns = _Unknowns()
    assumptions: dict[str, Assumption] = {}

    def assume(item: Assumption) -> None:
        if item.key in assumptions:
            raise FundingInputError(f"assumption key {item.key!r} collides")
        assumptions[item.key] = item

    facts = _intake(financials, as_of, unknowns)

    # -- opening balance --------------------------------------------------
    opening, opening_value = _opening(financials.cash_basis, facts, horizon_start, financials.binding.generation_id, unknowns)

    # -- required assumptions ---------------------------------------------
    supplied = dict(scenario.other_assumptions)
    burn, burn_assumption = _burn(supplied.get("burn_basis"), facts, unknowns)
    assume(burn_assumption)
    wc_known, wc_assumption = _simple_assumption(
        "working_capital_basis",
        supplied.get("working_capital_basis"),
        "excluded",
        "working-capital changes are not modeled; receivables stay context only",
        "the working-capital basis is unknown; every closing balance is unknown",
        unknowns,
    )
    assume(wc_assumption)
    season_known, season_assumption = _simple_assumption(
        "seasonality_basis",
        supplied.get("seasonality_basis"),
        "flat",
        "burn is spread by calendar days",
        "the seasonality basis is unknown; every closing balance is unknown",
        unknowns,
    )
    assume(season_assumption)

    blocking = burn.per_day is None or not wc_known or not season_known

    # -- period grid --------------------------------------------------------
    grid = _grid(horizon_start, horizon_end)
    ledger = _Ledger(len(grid))

    # -- observed obligations and conditional commitments --------------------
    obligations = [fact for fact in facts if ITEM_RULES.get(fact.kind, {}).get("flow_role") == "use" and fact.gross_net is not None]
    gross_keys = {(fact.kind, fact.receipt_sha256) for fact in obligations if fact.gross_net in ("gross", "not_applicable")}
    net_notes: dict[tuple[str, str | None], list[str]] = {}
    for fact in obligations:
        if fact.gross_net != "net":
            continue
        key = (fact.kind, fact.receipt_sha256)
        if fact.receipt_sha256 is None or key not in gross_keys:
            unknowns.add(
                f"unknown:gross_missing:{fact.item_id}",
                f"{fact.kind} {fact.item_id} is reported net with no matching gross observation; net is never substituted for gross",
                f"the gross {fact.kind} observation sharing receipt {fact.receipt_sha256}",
                ("closing_balance", "gap"),
            )
            blocking = True
            continue
        shown = _fmt(fact.raw_value) if fact.raw_value is not None else fact.amount.status
        net_notes.setdefault(key, []).append(f"net {shown} reported, not substituted")

    for fact in obligations:
        if fact.gross_net == "net":
            continue
        if fact.due_date is None:
            unknowns.add(
                f"unknown:timing:{fact.item_id}",
                f"{fact.kind} {fact.item_id} is observed without a due date; it could fall in any period",
                f"the contractual due date of {fact.item_id}",
                ("closing_balance", "gap"),
            )
            blocking = True
            continue
        if fact.due_date < horizon_start or fact.due_date > horizon_end:
            continue  # history before the horizon, or beyond it
        index = _period_index(grid, fact.due_date)
        if index is None:
            continue
        note = None
        if fact.gross_net in ("gross", "not_applicable"):
            note = _join(net_notes.get((fact.kind, fact.receipt_sha256), []))
        amount = fact.amount
        if amount.status != "known":
            unknowns.add(
                f"unknown:amount:{fact.item_id}",
                f"{fact.kind} {fact.item_id} is due {fact.due_date.isoformat()} with an amount that is {amount.status}",
                f"a known usd amount for {fact.item_id}",
                ("closing_balance", "gap"),
            )
        if note:
            amount = Quantity(unit="usd", status=amount.status, value=amount.value, note=_join([amount.note, note]))
        ledger.add(
            index,
            Flow(
                flow_id=f"use:{fact.item_id}",
                kind="use",
                label=f"{fact.kind} ({fact.gross_net})",
                amount=amount,
                certainty="contractual_dated",
                dated=fact.due_date.isoformat(),
            ),
        )

    for fact in facts:
        if not fact.excluded or ITEM_RULES.get(fact.kind, {}).get("flow_role") != "use":
            continue
        if fact.due_date is None or horizon_start <= fact.due_date <= horizon_end:
            blocking = True  # an obligation that cannot be counted in usd is never dropped silently

    for fact in facts:
        if fact.kind != "revolver_availability" or fact.excluded:
            continue
        if fact.condition is None:
            raise FundingInputError(f"revolver_availability {fact.item_id}: an undrawn commitment must name its condition")
        if grid:
            ledger.add(
                0,
                Flow(
                    flow_id=f"source:{fact.item_id}",
                    kind="source",
                    label="undrawn revolver availability (conditional, not cash on hand)",
                    amount=fact.amount,
                    certainty="conditional",
                    condition=fact.condition,
                ),
            )

    for fact in facts:
        if fact.kind == "undated_debt_balance":
            unknowns.add(
                f"unknown:timing:{fact.item_id}",
                f"undated debt balance {fact.item_id} is a balance-sheet classification, not a due date",
                f"dated maturities for the debt behind {fact.item_id}",
                ("uses",),
            )

    supplied_kinds = {fact.kind for fact in facts}
    owner_gaps = False
    for kind in NOT_BUILT_FLOW_KINDS:
        if kind not in supplied_kinds:
            owner_gaps = True
            unknowns.add(
                f"unknown:owner:{kind}",
                f"no current owner emits {kind}; it is absent from this schedule, never a zero",
                f"an owner emitting {FINANCIAL_ITEM_SCHEMA} {kind} records",
                ("uses" if ITEM_RULES[kind]["flow_role"] == "use" else "sources_or_opening",),
            )

    # -- commitments -----------------------------------------------------------
    family = commitments.binding.input_family
    if family == "covenant_terms":
        floor = _floor_from_covenants(commitments, as_of, unknowns)
    else:
        for observation_id, value, filed, accession in _registration_fees(commitments, as_of):
            flow_id = f"use:{observation_id}"
            if filed is None:
                unknowns.add(
                    f"unknown:timing:{observation_id}",
                    f"registration fee {observation_id} has no filing date",
                    f"the filing date of accession {accession}",
                    ("closing_balance", "gap"),
                )
                blocking = True
                continue
            if filed < horizon_start or filed > horizon_end:
                continue  # history, or beyond the horizon
            index = _period_index(grid, filed)
            if index is None:
                continue
            ledger.add(
                index,
                Flow(
                    flow_id=flow_id,
                    kind="use",
                    label=f"registration fee (filing {accession})",
                    amount=_usd(value),
                    certainty="contractual_dated",
                    dated=filed.isoformat(),
                ),
            )
        unknowns.add(
            _MIN_LIQUIDITY_ID,
            "covenant_terms were not supplied in this call, so the minimum-liquidity floor is unknown",
            "a direct minimum_liquidity_amount covenant term in USD",
            ("minimum_liquidity", "gap"),
        )
        floor = _usd_unknown("covenant terms not supplied in this call")

    # -- scenario unknown resolutions ---------------------------------------
    for resolution in scenario.unknown_resolutions:
        if resolution.unknown_id == _MIN_LIQUIDITY_ID and floor.status != "known":
            if resolution.assumed.unit != "usd":
                raise FundingInputError("unknown:minimum_liquidity: a resolution must be a usd quantity")
            floor = _usd(Decimal(resolution.assumed.value), note=f"scenario resolution: {resolution.rationale}")
            assume(Assumption(f"resolved:{_MIN_LIQUIDITY_ID}", resolution.assumed.value, resolution.rationale))
            unknowns.discard(_MIN_LIQUIDITY_ID)
            continue
        if resolution.unknown_id == _MIN_LIQUIDITY_ID:
            assume(
                Assumption(
                    f"unhonored_resolution:{_MIN_LIQUIDITY_ID}",
                    "ignored",
                    "the observed covenant floor is known; a scenario value never overrides an observation",
                )
            )
            continue
        assume(Assumption(f"unhonored_resolution:{resolution.unknown_id}", "ignored", _UNHONORED))

    # -- scenario actions (conditional only) -----------------------------------
    for action in scenario.actions:
        condition = _condition_text(action)
        if action.action in CASH_ROUTES or (action.action == "warrant_exercise" and action.settlement == "cash"):
            if not grid:
                continue
            gross, gross_value = _scenario_amount(action, scenario, unknowns)
            if scenario.fee_rate is not None and gross_value is not None:
                fee_value = _q(_CTX.multiply(gross_value, Decimal(scenario.fee_rate)))
                gross = Quantity(
                    unit="usd",
                    status="known",
                    value=gross.value,
                    note=_join([gross.note, f"net {_fmt(gross_value - fee_value)} reported, not substituted"]),
                )
                ledger.add(
                    0,
                    Flow(
                        flow_id=f"use:{action.route_id}:fee",
                        kind="use",
                        label=f"scenario {action.action} fee at rate {scenario.fee_rate}",
                        amount=_usd(fee_value),
                        certainty="conditional",
                        condition=condition,
                    ),
                )
            ledger.add(
                0,
                Flow(
                    flow_id=f"source:{action.route_id}:gross",
                    kind="source",
                    label=f"scenario {action.action} gross proceeds (not cash on hand)",
                    amount=gross,
                    certainty="conditional",
                    condition=condition,
                ),
            )
        elif action.action == "warrant_exercise" and action.settlement in _NO_CASH_WARRANT_SETTLEMENTS:
            continue  # cashless, net-share and pre-funded exercises deliver no cash
        elif action.action == "warrant_exercise":
            unknowns.add(
                f"unknown:settlement:{action.route_id}",
                f"warrant exercise {action.route_id} has an unknown settlement; no cash flow is assumed",
                f"the settlement terms of {action.route_id}",
                ("conditional_flows",),
            )
        elif action.action in _RELIEF_ROUTES:
            existing = ledger.find(f"use:{action.route_id}")
            if existing is not None and any(f.kind == "debt_maturity" and f.item_id == action.route_id for f in facts):
                ledger.replace(
                    existing.flow_id,
                    Flow(
                        flow_id=existing.flow_id,
                        kind="use",
                        label=existing.label,
                        amount=existing.amount,
                        certainty="conditional",
                        dated=existing.dated,
                        condition=f"relieved under scenario conversion {action.route_id}; relief provides no cash",
                    ),
                )
        elif action.action in _OUTFLOW_ROUTES:
            if not grid:
                continue
            amount, _ = _scenario_amount(action, scenario, unknowns)
            ledger.add(
                0,
                Flow(
                    flow_id=f"use:{action.route_id}:{action.action}",
                    kind="use",
                    label=f"scenario {action.action}",
                    amount=amount,
                    certainty="conditional",
                    condition=condition,
                ),
            )
        else:
            unknowns.add(
                f"unknown:action_amount:{action.route_id}",
                f"scenario action {action.route_id} is of kind 'other'; its cash effect is not modeled",
                f"the contractual cash effect of {action.route_id}",
                ("conditional_flows",),
            )

    # -- assumed burn ----------------------------------------------------------
    if burn.per_day is not None and burn.per_day > 0 and season_known:
        for index, (start, end) in enumerate(grid):
            days = (end - start).days
            amount = _q(_CTX.multiply(burn.per_day, Decimal(days)))
            ledger.add(
                index,
                Flow(
                    flow_id=f"use:burn:{end.isoformat()}",
                    kind="use",
                    label=f"assumed operating burn ({burn.label})",
                    amount=_usd(amount),
                    certainty="assumed",
                    dated=end.isoformat(),
                ),
            )

    # -- balance identity ------------------------------------------------------
    periods: list[FundingPeriod] = []
    computed: Decimal | None = opening_value
    current_opening = opening
    for index, (start, end) in enumerate(grid):
        sources = sorted(ledger.sources[index], key=lambda flow: (flow.dated or "", flow.flow_id))
        uses = sorted(ledger.uses[index], key=lambda flow: (flow.dated or "", flow.flow_id))
        counted = [flow for flow in (*sources, *uses) if flow.certainty != "conditional"]
        if computed is not None and all(flow.amount.status == "known" for flow in counted) and not blocking:
            delta = sum((Decimal(flow.amount.value) for flow in sources if flow.certainty != "conditional"), Decimal(0))
            delta -= sum((Decimal(flow.amount.value) for flow in uses if flow.certainty != "conditional"), Decimal(0))
            computed = computed + delta
        else:
            computed = None

        closing_notes = [burn.closing_note]
        deficit = computed is not None and computed < 0
        if computed is not None and not deficit and current_opening.status == "known":
            closing_notes.append(_PARTIAL_COVERAGE_NOTE if owner_gaps else None)
            closing = _usd(computed, note=_join(closing_notes))
        elif deficit:
            assert computed is not None
            closing_notes.insert(0, f"computed balance {_fmt(computed)} usd: uses exceed opening plus non-conditional sources (deficit)")
            closing = _usd_unknown(_join(closing_notes))
        else:
            closing = _usd_unknown(_join(closing_notes))

        if floor.status == "known" and computed is not None:
            gap_value = max(Decimal(0), Decimal(floor.value) - computed)
            gap = _usd(gap_value)
        elif deficit:
            assert computed is not None
            gap = _usd_unknown(f"at least {_fmt(-computed)} usd")
        else:
            gap = _usd_unknown()

        periods.append(
            FundingPeriod(
                period_start=start.isoformat(),
                period_end=end.isoformat(),
                opening_balance=current_opening,
                closing_balance=closing,
                minimum_liquidity=floor,
                gap=gap,
                sources=tuple(sources),
                uses=tuple(uses),
            )
        )
        current_opening = _usd_unknown("prior period ended in deficit") if deficit else closing

    record_inputs = {"financials": financials.as_record(), "commitments": commitments.as_record()}
    # The C0 state schema types ``state_id`` as ``state:cs:<32 hex>``.  F1's
    # frozen three-argument interface receives no IssuerCapitalState, so this
    # is the identity of the funding inputs actually consumed (a body no
    # IssuerCapitalState can produce), never a join key to an issuer state.
    # An assembler that holds the issuer state re-stamps it with
    # ``dataclasses.replace(schedule, state_id=state.state_id)``.
    return FundingSchedule(
        state_id=stable_id("state", {"funding_inputs": record_inputs, "scenario_id": scenario.scenario_id}),
        scenario_id=scenario.scenario_id,
        cash_basis=financials.cash_basis,
        receipt=CalculationReceipt.build(
            inputs={**record_inputs, "scenario": scenario.as_record()},
            rule_digest=RULE_DIGEST,
            implementation=IMPLEMENTATION,
            computed_at=scenario.as_of,
            scenario_id=scenario.scenario_id,
        ),
        periods=tuple(periods),
        assumptions=tuple(assumptions[key] for key in sorted(assumptions)),
        unknowns=unknowns.sorted(),
    )
