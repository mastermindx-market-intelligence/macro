"""SPEC_C2X §7 — capacity consumes transaction-evidenced usage (lane C2x).

Every fixture X1–X13 has its own named test here.  Each ledger is built with
:func:`reconcile_transactions` from X0a's own fixture helpers and public
dataclasses -- a ledger row, a usage row and an Unknown are never hand-written --
and every number is compared exactly, as ``Decimal`` for money and ``Fraction``
for kernel values.  There is no float literal and no float conversion call in this
file or in the adapter it exercises, and ``test_c2x_exact_arithmetic_only`` proves
both by walking the AST of each.

Helpers come from ``tests.test_capital_structure_capacity`` (C1),
``tests.test_capital_structure_capacity_c2`` (C2a) and
``tests.test_capital_structure_transactions`` (X0a); none is copied.

Two laws shape every assertion:

* a fact replaces an assumption, a certified floor tightens the optimistic end of
  the bracket, and a contradiction blocks the path -- but an unknown stays
  unknown, never ``0`` and never the floor (A20);
* a refusal is recorded, never raised, so a saved scenario survives the nightly
  arrival of new evidence (§0 item 3).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_capacity_c2 as C2
import tests.test_capital_structure_transactions as X0
from engine.capital_structure import capacity_joint
from engine.capital_structure import capacity as c2x
from engine.capital_structure.capacity import CapacityInputError, explain_capacity
from engine.capital_structure.issuer_state_contracts import (
    ActionSelection,
    GenerationBinding,
    Quantity,
    _record,
    sha256_of,
    validate_state_record,
)
from engine.capital_structure.transactions import OBSERVATION_SCHEMA, reconcile_transactions
from tests.test_capital_structure_capacity import PATH_A, SALE, strip_identity, usd

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "engine" / "capital_structure" / "capacity.py"
THIS_FILE = Path(__file__).resolve()

ISSUER = C1.ISSUER
AS_OF = C1.AS_OF
FILE_NUMBER = "333-000001"
#: §7: one shelf path P with R = 20,000,000 gross registered.
REGISTERED = "20000000"
#: The path's own ``origin.sec_accepted_at`` date in the C1 fixture.
INCEPTION = C1.shift(SALE, 30)
#: §7 X7-X9/X11: the F9 sale date, where the Q1+Q2 chain is complete.
PROGRAMME_SALE = "2026-06-30"
PROGRAMME_INCEPTION = "2026-01-01"
RESERVATION = "5000000"

REGISTERED_A = f"registered:{PATH_A}"
TAKE_A = f"shelf_takedown:{PATH_A}"
ATM_A = f"at_the_market:{PATH_A}"
SHELF_KEY = f"shelf_usage:{PATH_A}"
PROGRAMME_KEY = f"programme_usage:{PATH_A}"
RESERVATION_KEY = f"programme_reservation:{PATH_A}"
CONTINUING_KEY = f"continuing_offering:{PATH_A}"
MULTIPLE_KEY = f"programme_usage_multiple_programmes:{PATH_A}"


# ---------------------------------------------------------------------------
# The ONE shared receipt / contract helper every envelope in this file passes
# ---------------------------------------------------------------------------


def check(evaluation: Any) -> None:
    """Validate the envelope, refuse forbidden keys and re-derive the input digest.

    Delegates to the C2a helper (imported, never copied) so the C0 contract walk,
    the A20 quantity walk and ``sha256_of(_record(inputs)) == receipt.input_digest``
    all run on every envelope this file produces, ledger or no ledger.
    """
    C2.check(evaluation)
    assert c2x.IMPLEMENTATION == (
        "capital_structure.capacity.c2_adapter.v2+" + capacity_joint.IMPLEMENTATION
    ), "§0 item 1: the adapter id is NOT bumped"


# ---------------------------------------------------------------------------
# Builders — states from the C1/C2a helpers, ledgers from X0a's
# ---------------------------------------------------------------------------


def state_kwargs(
    sale: str = SALE, *, resolutions: Sequence[Any] = (), continuing: str | None = "0"
) -> dict[str, Any]:
    """§7: one shelf path P, R = 20,000,000, ``continuing_offering`` resolved 0 unless stated."""
    registration, shares = C1.standard_registration(
        sale, registered=REGISTERED, float_value="300000000"
    )
    resolved = [] if continuing is None else [usd(CONTINUING_KEY, continuing)]
    return {
        "sale": sale,
        "registration": registration,
        "share_basis": shares,
        "resolutions": [*resolved, *resolutions],
    }


def explain(
    *,
    transactions: Any = None,
    sale: str = SALE,
    resolutions: Sequence[Any] = (),
    continuing: str | None = "0",
    state: Any = None,
) -> Any:
    """Build, explain with the additive keyword, and run the shared check."""
    if state is None:
        state, scenario, rules = C1.build(
            **state_kwargs(sale, resolutions=resolutions, continuing=continuing)
        )
    else:
        scenario, rules = state[1], state[2]
        state = state[0]
    evaluation = explain_capacity(state, scenario, rules, pack=C1.PACK, transactions=transactions)
    check(evaluation)
    return evaluation


def ledger_of(
    sale: str,
    observations: Sequence[Any],
    bindings: Sequence[Any],
    *,
    coverage: Sequence[Any] = (),
    issuer: str = ISSUER,
    as_of: str | None = None,
) -> Any:
    """Reconcile one point-in-time ledger through X0a's own checked entry point."""
    return X0.reconcile(
        issuer_id=issuer,
        as_of=as_of or f"{sale}T00:00:00Z",
        observations=tuple(observations),
        bindings=tuple(bindings),
        filing_coverage=tuple(coverage),
        registration_paths=(
            X0.shelf_path_record(PATH_A, FILE_NUMBER, C1.shift(sale, 30), issuer),
        ),
    )


def takedown(
    gross: str,
    *,
    basis: str = "individual",
    event_date: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    accepted: str | None = None,
    issuer: str = ISSUER,
) -> Any:
    """One 424B takedown observation, built through X0a's public dataclass."""
    return X0.observation(
        kind="registered_takedown",
        basis=basis,
        event_date=event_date,
        period_start=period_start,
        period_end=period_end,
        gross=gross,
        form="424B5",
        accepted=accepted or period_end or event_date,
        issuer_id=issuer,
    )


def on_shelf(observation: Any, transaction_id: str, *, issuer: str = ISSUER) -> Any:
    """Bind one observation to path P as a shelf takedown."""
    return X0.binding(observation, transaction_id, target_id=PATH_A)


def programme_window(
    gross: str,
    start: str,
    end: str,
    *,
    transaction_id: str,
    programme_key: str | None = None,
) -> tuple[Any, Any]:
    """One 10-Q cumulative ATM window bound to path P (F9 shape)."""
    observation = X0.observation(
        kind="atm_sales",
        basis="cumulative",
        period_start=start,
        period_end=end,
        gross=gross,
        form="10-Q",
        accepted=end,
    )
    binding = X0.binding(
        observation,
        transaction_id,
        target_id=PATH_A,
        programme_key=programme_key,
        programme_inception_date=PROGRAMME_INCEPTION,
    )
    return observation, binding


def row_of(evaluation: Any, usage_key: str) -> dict[str, Any]:
    """The one ``inputs["transaction_usage"]`` entry for ``usage_key``."""
    rows = [item for item in evaluation.inputs["transaction_usage"] if item["usage_key"] == usage_key]
    assert len(rows) == 1, [item["usage_key"] for item in evaluation.inputs["transaction_usage"]]
    return rows[0]


def pools(evaluation: Any) -> dict[str, Any]:
    return C1.pools_by_id(evaluation)


def routes(evaluation: Any) -> dict[str, Any]:
    return C1.routes_by_id(evaluation)


def unknown_of(evaluation: Any, unknown_id: str) -> Any:
    matches = [item for item in evaluation.envelope.unknowns if item.unknown_id == unknown_id]
    assert len(matches) == 1, sorted(item.unknown_id for item in evaluation.envelope.unknowns)
    return matches[0]


def residual(evaluation: Any, branch: str, kind: str, identifier: str) -> str | None:
    """One exact kernel value from ``inputs["remaining_capacity"]`` (§2.5/§4)."""
    return dict(evaluation.inputs["remaining_capacity"][branch][kind])[identifier]


def fraction_text(value: Fraction) -> str:
    """The adapter's exact ``Fraction`` text: ``numerator/denominator``, never a float."""
    return f"{value.numerator}/{value.denominator}"


# ---------------------------------------------------------------------------
# The X-fixture ledgers, each reconciled from observations — never hand-written
# ---------------------------------------------------------------------------


def x1_ledger(sale: str = SALE) -> Any:
    """F1 shape: one inception-to-date cumulative window that covers one individual."""
    window = takedown("5000000", basis="cumulative", period_end=sale)
    covered = takedown("1000000", event_date=C1.shift(sale, 13))
    return ledger_of(
        sale,
        [window, covered],
        [on_shelf(window, "tx:x1-inception-to-date"), on_shelf(covered, "tx:x1-covered")],
    )


def x3_ledger(sale: str = SALE) -> Any:
    """F8 without coverage: two individuals, no completeness attestation."""
    first = takedown("3000000", event_date="2025-06-01")
    second = takedown("4000000", event_date="2026-02-01")
    return ledger_of(
        sale, [first, second], [on_shelf(first, "tx:x3-first"), on_shelf(second, "tx:x3-second")]
    )


def x6_ledger(sale: str = SALE) -> Any:
    """F4 shape: a contained cumulative window that exceeds its container."""
    inner = takedown("5000000", basis="cumulative", period_end=C1.shift(sale, 13))
    outer = takedown("4000000", basis="cumulative", period_end=sale)
    return ledger_of(
        sale, [inner, outer], [on_shelf(inner, "tx:x6-inner"), on_shelf(outer, "tx:x6-outer")]
    )


def x10_ledger(sale: str = SALE) -> Any:
    """F5 shape: two partially overlapping cumulative windows, not apportionable."""
    first = takedown(
        "3000000", basis="cumulative", period_start=INCEPTION, period_end=C1.shift(sale, 14)
    )
    second = takedown(
        "2000000", basis="cumulative", period_start=C1.shift(sale, 24), period_end=sale
    )
    return ledger_of(
        sale, [first, second], [on_shelf(first, "tx:x10-first"), on_shelf(second, "tx:x10-second")]
    )


def x7_ledger() -> Any:
    """F9 contiguous chain: Q1 1,000,000 + Q2 1,500,000, complete through as_of."""
    q1, b1 = programme_window("1000000", "2026-01-01", "2026-03-31", transaction_id="tx:x7-q1")
    q2, b2 = programme_window("1500000", "2026-04-01", "2026-06-30", transaction_id="tx:x7-q2")
    return ledger_of(PROGRAMME_SALE, [q1, q2], [b1, b2])


def x8_ledger(gross: str = "1000000") -> Any:
    """F9 with a gap after Q1: one window, so the history is incomplete."""
    q1, b1 = programme_window(gross, "2026-01-01", "2026-03-31", transaction_id="tx:x8-q1")
    return ledger_of(PROGRAMME_SALE, [q1], [b1])


def x11_ledger() -> Any:
    """Two programme keys under one path: capacity cannot tell which is reserved."""
    first, b1 = programme_window(
        "1000000", "2026-01-01", "2026-03-31", transaction_id="tx:x11-a", programme_key="atm-a"
    )
    second, b2 = programme_window(
        "2000000", "2026-01-01", "2026-03-31", transaction_id="tx:x11-b", programme_key="atm-b"
    )
    return ledger_of(PROGRAMME_SALE, [first, second], [b1, b2])


def programme_resolutions() -> list[Any]:
    """§7 X7-X9: shelf usage resolved 0 and the reservation S = 5,000,000 resolved."""
    return [usd(SHELF_KEY, "0"), usd(RESERVATION_KEY, RESERVATION)]


# ---------------------------------------------------------------------------
# §0 item 2 / §3 row "known" — X1, X2, X7
# ---------------------------------------------------------------------------


def test_x1_a_known_shelf_usage_replaces_the_assumption() -> None:
    """§3 known/None: R - U - C = 20,000,000 - 5,000,000 - 0 = 15,000,000."""
    ledger = x1_ledger()
    evaluation = explain(transactions=ledger)
    bound = pools(evaluation)[REGISTERED_A].bound
    assert bound.status == "known"
    assert C2.money(bound) == Decimal(REGISTERED) - Decimal("5000000") - Decimal("0")
    # §0 item 2: no shelf_usage Unknown survives a known fact.
    assert SHELF_KEY not in C1.unknown_ids(evaluation)
    assert evaluation.envelope.blockers == ()
    row = row_of(evaluation, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_EVIDENCE
    assert row["status"] == "known"
    assert Decimal(row["usage"]) == Decimal("5000000")
    assert Decimal(row["evidenced_floor"]) == Decimal("5000000")
    assert row["resolution_assumed"] is None
    assert row["complete_through"] == ledger.usage[0]["complete_through"] == SALE
    # The deduction IS the evidenced amount, cited from X0a's own observations.
    fact = evaluation.inputs["registration_paths"][0]["resolutions"]["shelf_usage"]
    assert Decimal(fact["assumed"]["value"]) == Decimal("5000000")
    provenance = fact["assumed"]["provenance"]
    assert provenance["input_family"] == "transaction_observations"
    assert provenance["available_at"] == max(
        item["available_at"] for item in ledger.transactions
    )
    cited = sorted(
        (item["manifest_id"], item["span_id"], item["text_sha256"])
        for item in provenance["evidence"]
    )
    exposed = sorted(
        {
            (item["manifest_id"], item["span_id"], item["text_sha256"])
            for transaction in ledger.transactions
            for item in transaction["evidence"]
        }
    )
    assert cited == exposed, "a ref is cited exactly as X0a exposes it, never fabricated"
    assert ledger.receipt.input_digest in fact["rationale"]
    # §6: facts, assumptions and unknowns stay separately visible.
    assert [item["unknown_id"] for item in evaluation.inputs["assumptions"]] == [CONTINUING_KEY]
    assert evaluation.inputs["transaction_ledger"] == {
        "issuer_id": ledger.issuer_id,
        "as_of": ledger.as_of,
        "input_digest": ledger.receipt.input_digest,
        "rule_digest": ledger.receipt.rule_digest,
    }


def test_x2_a_scenario_resolution_never_overrides_a_known_fact() -> None:
    """§0 item 3 / §3 known-supplied: the bound is still 20,000,000 - 5,000,000 - 0."""
    evaluation = explain(transactions=x1_ledger(), resolutions=[usd(SHELF_KEY, "6000000")])
    bound = pools(evaluation)[REGISTERED_A].bound
    assert C2.money(bound) == Decimal(REGISTERED) - Decimal("5000000")
    assert SHELF_KEY not in C1.unknown_ids(evaluation)
    row = row_of(evaluation, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_SUPERSEDED_BY_FACT
    assert row["resolution_assumed"] == "6000000"
    assert Decimal(row["usage"]) == Decimal("5000000")
    # The superseded assumption stays visible as an assumption, never as a fact.
    assumed = [item for item in evaluation.inputs["assumptions"] if item["unknown_id"] == SHELF_KEY]
    assert len(assumed) == 1 and Decimal(assumed[0]["assumed"]["value"]) == Decimal("6000000")
    fact = evaluation.inputs["registration_paths"][0]["resolutions"]["shelf_usage"]
    assert Decimal(fact["assumed"]["value"]) == Decimal("5000000")
    assert fact["assumed"]["provenance"]["input_family"] == "transaction_observations"


def test_x7_a_known_programme_usage_is_deducted_exactly_once() -> None:
    """§3 known: atm limit S - P = 5,000,000 - 2,500,000; pool R-U-C-P = 17,500,000."""
    evaluation = explain(
        sale=PROGRAMME_SALE, transactions=x7_ledger(), resolutions=programme_resolutions()
    )
    atm = routes(evaluation)[ATM_A].limit
    assert atm.status == "known"
    assert C2.money(atm) == Decimal(RESERVATION) - Decimal("2500000")
    bound = pools(evaluation)[REGISTERED_A].bound
    assert C2.money(bound) == Decimal(REGISTERED) - Decimal("0") - Decimal("0") - Decimal("2500000")
    assert PROGRAMME_KEY not in C1.unknown_ids(evaluation)
    row = row_of(evaluation, PROGRAMME_KEY)
    assert row["disposition"] == c2x.DISPOSITION_EVIDENCE
    assert Decimal(row["usage"]) == Decimal("2500000")
    assert row["resolution_assumed"] is None
    assert evaluation.inputs["programme_usage"][PATH_A] == {
        "status": "known",
        "value": "2500000",
        "pessimistic": "2500000",
        "optimistic": "2500000",
    }
    assert evaluation.inputs["branches"] == []
    assert residual(evaluation, "pessimistic", "routes", ATM_A) == "2500000/1"
    assert residual(evaluation, "pessimistic", "pools", REGISTERED_A) == "17500000/1"


# ---------------------------------------------------------------------------
# §0 item 4 / §4 — the floor bracket: X3, X4, X5, X8
# ---------------------------------------------------------------------------


def test_x3_a_certified_floor_tightens_the_ceiling_substitute() -> None:
    """§4 shelf: fee.gross - F - C = 20,000,000 - 7,000,000 - 0 = 13,000,000."""
    ledger = x3_ledger()
    assert ledger.usage[0]["status"] == "unknown"
    assert Decimal(ledger.usage[0]["evidenced_floor"]["value"]) == Decimal("7000000")
    evaluation = explain(transactions=ledger)
    bound = pools(evaluation)[REGISTERED_A].bound
    # The bound stays unknown: a floor is never read as the usage, never as zero.
    assert bound.status == "unknown" and bound.value is None
    assert SHELF_KEY in C1.unknown_ids(evaluation)
    substitute = Fraction(Decimal(REGISTERED)) - Fraction("7000000") - Fraction("0")
    assert evaluation.inputs["ceiling_call"]["value"] == fraction_text(substitute)
    assert evaluation.inputs["ceiling_call"]["determined"] is False
    assert evaluation.envelope.aggregate_bound.note == (
        "floor 0.00 / ceiling 13000000.00 under stated unknowns"
    )
    row = row_of(evaluation, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_UNRESOLVED_WITH_FLOOR
    assert row["usage"] is None and row["evidenced_floor"] == "7000000"
    assert row["resolution_assumed"] is None
    # §4: the Unknown names the missing 424B history the ledger itself names.
    certified = f"usage_history_incomplete:{SHELF_KEY}"
    expected = next(item for item in ledger.unknowns if item.unknown_id == certified)
    emitted = unknown_of(evaluation, SHELF_KEY)
    assert emitted.resolving_fact == expected.resolving_fact
    assert INCEPTION in emitted.resolving_fact or SALE in emitted.resolving_fact


def test_x4_a_resolution_below_the_floor_is_refused_not_raised() -> None:
    """§3 unknown-floor/s<F: s is NOT applied, so every bound equals the X3 run."""
    floored = explain(transactions=x3_ledger())
    refused = explain(transactions=x3_ledger(), resolutions=[usd(SHELF_KEY, "6000000")])
    assert SHELF_KEY in C1.unknown_ids(refused)
    row = row_of(refused, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_REFUSED_BELOW_FLOOR
    assert row["resolution_assumed"] == "6000000"
    assert row["evidenced_floor"] == "7000000"
    assert pools(refused)[REGISTERED_A].bound.as_record() == (
        pools(floored)[REGISTERED_A].bound.as_record()
    )
    assert refused.inputs["ceiling_call"] == floored.inputs["ceiling_call"] == {
        "determined": False,
        "value": "13000000/1",
        "reported_as": "aggregate_note_and_inputs_only_never_the_aggregate",
    }
    assert refused.envelope.aggregate_bound.as_record() == (
        floored.envelope.aggregate_bound.as_record()
    )
    assert {item.route_id: item.limit.as_record() for item in refused.envelope.routes} == {
        item.route_id: item.limit.as_record() for item in floored.envelope.routes
    }
    assert refused.envelope.blockers == floored.envelope.blockers == ()


def test_x5_a_resolution_at_or_above_the_floor_is_applied_as_today() -> None:
    """§3 unknown-floor/s>=F: R - s - C = 20,000,000 - 8,000,000 - 0 = 12,000,000."""
    resolution = usd(SHELF_KEY, "8000000")
    evaluation = explain(transactions=x3_ledger(), resolutions=[resolution])
    bound = pools(evaluation)[REGISTERED_A].bound
    assert bound.status == "known"
    assert C2.money(bound) == Decimal(REGISTERED) - Decimal("8000000")
    assert SHELF_KEY not in C1.unknown_ids(evaluation)
    row = row_of(evaluation, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_APPLIED_ABOVE_FLOOR
    assert row["resolution_assumed"] == "8000000"
    assert row["evidenced_floor"] == "7000000"
    # "Applied exactly as today": the same scenario with no ledger gives the same bound.
    plain = explain(resolutions=[resolution])
    assert pools(plain)[REGISTERED_A].bound.as_record() == bound.as_record()
    assert C1.strip_identity(plain.envelope.as_record()) == C1.strip_identity(
        evaluation.envelope.as_record()
    )


def test_x8_a_programme_floor_replaces_zero_in_the_optimistic_branch() -> None:
    """§4 programme: S=5,000,000, F=1,000,000, remaining=20,000,000.

    ``atm_limit`` = {pessimistic: 0, optimistic: S - F = 4,000,000};
    ``pool_bound`` = {pessimistic: remaining - S = 15,000,000,
    optimistic: remaining - F = 19,000,000}.
    """
    ledger = x8_ledger()
    assert ledger.usage[0]["status"] == "unknown"
    assert Decimal(ledger.usage[0]["evidenced_floor"]["value"]) == Decimal("1000000")
    evaluation = explain(
        sale=PROGRAMME_SALE, transactions=ledger, resolutions=programme_resolutions()
    )
    assert PROGRAMME_KEY in C1.unknown_ids(evaluation)
    assert routes(evaluation)[ATM_A].limit.status == "unknown"
    assert pools(evaluation)[REGISTERED_A].bound.status == "unknown"
    reserved, floor = Fraction(RESERVATION), Fraction(1000000)
    remaining = Fraction(REGISTERED) - Fraction("0") - Fraction("0")
    assert residual(evaluation, "pessimistic", "routes", ATM_A) == fraction_text(Fraction(0))
    assert residual(evaluation, "optimistic", "routes", ATM_A) == fraction_text(reserved - floor)
    assert residual(evaluation, "pessimistic", "pools", REGISTERED_A) == fraction_text(
        remaining - reserved
    )
    assert residual(evaluation, "optimistic", "pools", REGISTERED_A) == fraction_text(
        remaining - floor
    )
    assert evaluation.inputs["programme_usage"][PATH_A] == {
        "status": "unresolved",
        "value": None,
        "pessimistic": RESERVATION,
        "optimistic": "1000000",
    }
    # §0 item 4: the pessimistic branch is unchanged -- P = S exactly as before C2x.
    without = explain(sale=PROGRAMME_SALE, resolutions=programme_resolutions())
    assert residual(evaluation, "pessimistic", "routes", ATM_A) == residual(
        without, "pessimistic", "routes", ATM_A
    )
    assert residual(evaluation, "pessimistic", "pools", REGISTERED_A) == residual(
        without, "pessimistic", "pools", REGISTERED_A
    )
    # ...and the optimistic branch is strictly tighter than the pre-C2x P = 0.
    assert Fraction(residual(evaluation, "optimistic", "routes", ATM_A)) < Fraction(
        residual(without, "optimistic", "routes", ATM_A)
    )
    assert Fraction(residual(evaluation, "optimistic", "pools", REGISTERED_A)) < Fraction(
        residual(without, "optimistic", "pools", REGISTERED_A)
    )
    row = row_of(evaluation, PROGRAMME_KEY)
    assert row["disposition"] == c2x.DISPOSITION_UNRESOLVED_WITH_FLOOR
    assert row["usage"] is None and row["evidenced_floor"] == "1000000"
    assert evaluation.inputs["branches"] == [PROGRAMME_KEY]


def test_x3_a_resolved_continuing_reservation_is_subtracted_from_the_substitute() -> None:
    """§4 shelf: fee.gross - F - C = 20,000,000 - 7,000,000 - 1,000,000 = 12,000,000."""
    evaluation = explain(
        transactions=x3_ledger(), continuing="1000000", resolutions=[usd(SHELF_KEY, "0")]
    )
    # The supplied shelf usage of 0 is refused: it sits below the evidenced floor.
    assert row_of(evaluation, SHELF_KEY)["disposition"] == (
        c2x.DISPOSITION_REFUSED_BELOW_FLOOR
    )
    substitute = Fraction(REGISTERED) - Fraction("7000000") - Fraction("1000000")
    assert evaluation.inputs["ceiling_call"]["value"] == fraction_text(substitute)
    assert pools(evaluation)[REGISTERED_A].bound.status == "unknown"


def test_x3_a_floor_above_the_registered_amount_contradicts_the_pool() -> None:
    """§4 shelf, negative substitute: F 21,000,000 > R - C, so the bound contradicts."""
    only = takedown("21000000", event_date="2025-06-01")
    ledger = ledger_of(SALE, [only], [on_shelf(only, "tx:x3-over")])
    assert ledger.usage[0]["status"] == "unknown"
    assert Decimal(ledger.usage[0]["evidenced_floor"]["value"]) == Decimal("21000000")
    evaluation = explain(transactions=ledger)
    bound = pools(evaluation)[REGISTERED_A].bound
    assert bound.status == "contradicted" and bound.value is None
    assert f"registered_overrun:{PATH_A}" in evaluation.envelope.blockers
    # The existing contradicted-bound rule: substitute None, so no ceiling is claimed.
    assert evaluation.inputs["ceiling_call"]["value"] is None
    assert evaluation.envelope.aggregate_bound.value is None
    assert row_of(evaluation, SHELF_KEY)["disposition"] == (
        c2x.DISPOSITION_UNRESOLVED_WITH_FLOOR
    )


# ---------------------------------------------------------------------------
# §0 item 5 / §5 — contradicted usage: X6, X9
# ---------------------------------------------------------------------------


def test_x6_contradicted_usage_blocks_its_path() -> None:
    """§5: blocker ``usage_contradicted:<usage_key>``, contradicted bound, no substitute."""
    ledger = x6_ledger()
    assert ledger.usage[0]["status"] == "contradicted"
    evaluation = explain(transactions=ledger)
    assert f"usage_contradicted:{SHELF_KEY}" in evaluation.envelope.blockers
    bound = pools(evaluation)[REGISTERED_A].bound
    assert bound.status == "contradicted" and bound.value is None
    # The note names the X0 reason codes from the ledger's Unknowns and limits.
    assert SHELF_KEY in bound.note
    assert "contained_window_exceeds_container:tx:x6-inner" in bound.note
    assert f"contradicted:{SHELF_KEY}" in bound.note
    # The existing contradicted-bound rule: no ceiling substitute is emitted.
    assert evaluation.inputs["ceiling_call"]["value"] is None
    assert evaluation.inputs["ceiling_call"]["determined"] is False
    takedown = routes(evaluation)[TAKE_A].limit
    assert takedown.status == "contradicted" and takedown.value is None
    assert evaluation.envelope.aggregate_bound.status == "unknown"
    assert evaluation.envelope.aggregate_bound.value is None
    row = row_of(evaluation, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_CONTRADICTED
    assert row["usage"] is None and row["evidenced_floor"] is None


def test_x6_a_contradicted_row_ignores_a_supplied_resolution() -> None:
    """§3 contradicted/any: the scenario resolution is ignored, and no number is claimed."""
    evaluation = explain(transactions=x6_ledger(), resolutions=[usd(SHELF_KEY, "1000000")])
    row = row_of(evaluation, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_CONTRADICTED
    assert row["resolution_assumed"] == "1000000"
    assert pools(evaluation)[REGISTERED_A].bound.status == "contradicted"
    assert f"usage_contradicted:{SHELF_KEY}" in evaluation.envelope.blockers
    assert evaluation.inputs["ceiling_call"]["value"] is None


def test_x9_a_programme_floor_above_the_reservation_contradicts() -> None:
    """§4: F = 6,000,000 > S = 5,000,000 is the resolved overrun, never a negative limit."""
    evaluation = explain(
        sale=PROGRAMME_SALE,
        transactions=x8_ledger("6000000"),
        resolutions=programme_resolutions(),
    )
    assert f"programme_usage_exceeds_reservation:{PATH_A}" in evaluation.envelope.blockers
    atm = routes(evaluation)[ATM_A].limit
    assert atm.status == "contradicted" and atm.value is None
    assert Decimal("6000000") - Decimal(RESERVATION) == Decimal("1000000")
    assert "1000000" in atm.note
    # No branch substitute is offered for a contradicted programme: unknown, not 0.
    assert residual(evaluation, "pessimistic", "routes", ATM_A) is None
    assert residual(evaluation, "optimistic", "routes", ATM_A) is None
    assert residual(evaluation, "pessimistic", "pools", REGISTERED_A) is None
    assert evaluation.envelope.aggregate_bound.value is None
    row = row_of(evaluation, PROGRAMME_KEY)
    assert row["disposition"] == c2x.DISPOSITION_UNRESOLVED_WITH_FLOOR
    assert row["evidenced_floor"] == "6000000" and row["usage"] is None


# ---------------------------------------------------------------------------
# §2 — evidence capacity may not consume: X10, X11
# ---------------------------------------------------------------------------


def test_x10_an_unapportionable_overlap_is_reported_and_never_used() -> None:
    """§2: any other Unknown naming the key leaves the row unconsumable."""
    ledger = x10_ledger()
    assert ledger.usage[0]["status"] == "unknown"
    assert [item.unknown_id for item in ledger.unknowns] == [
        f"overlapping_cumulative_windows_not_apportionable:{PATH_A}"
    ]
    with_ledger = explain(transactions=ledger)
    without = explain()
    row = row_of(with_ledger, SHELF_KEY)
    assert row["disposition"] == c2x.DISPOSITION_NOT_CONSUMABLE
    assert row["evidenced_floor"] == "3000000" and row["usage"] is None
    # The envelope is the no-ledger envelope; only the two §6 inputs keys are added.
    assert strip_identity(with_ledger.envelope.as_record()) == strip_identity(
        without.envelope.as_record()
    )
    assert set(with_ledger.inputs) - set(without.inputs) == {
        "transaction_ledger",
        "transaction_usage",
    }
    assert with_ledger.inputs["ceiling_call"]["value"] == fraction_text(Fraction(REGISTERED))
    assert "transaction_ledger" not in without.inputs
    assert "transaction_usage" not in without.inputs


def test_x11_two_programme_rows_consume_none_of_them() -> None:
    """§2: more than one programme row under P -> none is consumed, and P says why."""
    evaluation = explain(
        sale=PROGRAMME_SALE, transactions=x11_ledger(), resolutions=programme_resolutions()
    )
    without = explain(sale=PROGRAMME_SALE, resolutions=programme_resolutions())
    emitted = unknown_of(evaluation, MULTIPLE_KEY)
    assert emitted.resolving_fact == (
        f"which at-the-market programme the reservation under {PATH_A} refers to"
    )
    rows = evaluation.inputs["transaction_usage"]
    assert [row["usage_key"] for row in rows] == [
        f"{PROGRAMME_KEY}:atm-a",
        f"{PROGRAMME_KEY}:atm-b",
    ]
    assert [row["disposition"] for row in rows] == [
        c2x.DISPOSITION_NOT_CONSUMABLE,
        c2x.DISPOSITION_NOT_CONSUMABLE,
    ]
    # Nothing was consumed: every number equals the no-ledger run.
    assert pools(evaluation)[REGISTERED_A].bound.as_record() == (
        pools(without)[REGISTERED_A].bound.as_record()
    )
    assert routes(evaluation)[ATM_A].limit.as_record() == routes(without)[ATM_A].limit.as_record()
    assert evaluation.inputs["programme_usage"] == without.inputs["programme_usage"]
    assert evaluation.inputs["remaining_capacity"] == without.inputs["remaining_capacity"]
    assert evaluation.envelope.blockers == without.envelope.blockers == ()
    assert set(item.unknown_id for item in evaluation.envelope.unknowns) - {MULTIPLE_KEY} == set(
        item.unknown_id for item in without.envelope.unknowns
    )


# ---------------------------------------------------------------------------
# §0 item 6 / §1 — the four refusals: X12
# ---------------------------------------------------------------------------


def test_x12_a_ledger_at_another_as_of_is_refused() -> None:
    """§1: a ledger is point-in-time, so neither a stale nor a lookahead one joins."""
    stale = x1_ledger(sale=C1.shift(SALE, 1))
    with pytest.raises(CapacityInputError, match="is not the state cutoff"):
        explain(sale=SALE, transactions=stale)
    lookahead = x1_ledger(sale="2026-12-31")
    with pytest.raises(CapacityInputError, match="is not the state cutoff"):
        explain(sale=SALE, transactions=lookahead)


def test_x12_a_ledger_for_another_issuer_is_refused() -> None:
    """§1: the ledger's issuer must be the state's issuer."""
    other = "cik:0009999999"
    window = takedown("5000000", basis="cumulative", period_end=SALE, issuer=other)
    covered = takedown("1000000", event_date=C1.shift(SALE, 13), issuer=other)
    ledger = ledger_of(
        SALE,
        [window, covered],
        [
            X0.binding(window, "tx:x12-inception-to-date", target_id=PATH_A),
            X0.binding(covered, "tx:x12-covered", target_id=PATH_A),
        ],
        issuer=other,
    )
    assert ledger.issuer_id == other
    with pytest.raises(CapacityInputError, match="is not the state issuer"):
        explain(sale=SALE, transactions=ledger)


def test_x12_a_non_ledger_transactions_argument_is_refused() -> None:
    """§1: anything that is not a TransactionLedger is refused, never duck-typed."""
    for bad in ("shelf_usage:...", {"usage": ()}, Quantity.known("1", "usd"), 0):
        with pytest.raises(CapacityInputError, match="TransactionLedger"):
            explain(sale=SALE, transactions=bad)


def test_x12_a_state_family_that_disagrees_with_the_ledger_is_refused() -> None:
    """§1: one source of truth -- the family's records must be the ledger's exactly."""
    ledger = x1_ledger()
    other = x3_ledger()

    def carrying(family_ledger: Any) -> tuple[Any, Any, Any]:
        state, scenario, rules = C1.build(**state_kwargs(SALE))
        family = family_ledger.family_state()
        request = dataclasses.replace(
            state.request,
            input_generations=state.request.input_generations
            + (
                GenerationBinding(
                    "transaction_observations",
                    OBSERVATION_SCHEMA,
                    family_ledger.support,
                    artifact_sha256=family_ledger.receipt.input_digest,
                    as_of=family_ledger.as_of,
                ),
            ),
        )
        return dataclasses.replace(state, request=request, families=state.families + (family,)), (
            scenario,
            rules,
        )

    disagreeing, (scenario, rules) = carrying(ledger)
    with pytest.raises(CapacityInputError, match="one source of truth"):
        explain_capacity(disagreeing, scenario, rules, pack=C1.PACK, transactions=other)
    # The agreeing ledger is accepted, and the family is never read when the kwarg is None.
    agreeing, (scenario, rules) = carrying(ledger)
    evaluation = explain_capacity(agreeing, scenario, rules, pack=C1.PACK, transactions=ledger)
    check(evaluation)
    assert row_of(evaluation, SHELF_KEY)["disposition"] == c2x.DISPOSITION_EVIDENCE
    bare = explain_capacity(agreeing, scenario, rules, pack=C1.PACK)
    check(bare)
    assert "transaction_ledger" not in bare.inputs and "transaction_usage" not in bare.inputs


# ---------------------------------------------------------------------------
# §0 item 1 — byte identity: X13
# ---------------------------------------------------------------------------


def identity_cases() -> list[tuple[str, dict[str, Any], tuple[Any, ...]]]:
    """Distinct C1/C2a fixtures: shelf, programme, exchange pools and actions."""
    registered, shares = C1.standard_registration()
    take_a, take_b = C2.TAKE_A, C2.TAKE_B
    atm = C2.USAGE_A
    return [
        ("a21_slack", C2.a21_kwargs(outstanding="30000005"), ()),
        ("a21_nasdaq_binding", C2.a21_kwargs(outstanding="15000005"), ()),
        ("a21_unknown_outstanding", C2.a21_kwargs(outstanding=None), ()),
        ("a21_sold_trailing", C2.a21_kwargs(sold="9000000"), ()),
        (
            "a21_exclusive",
            C2.a21_kwargs(other=(("route_exclusivity", f"{take_a}|{take_b}"),)),
            (),
        ),
        ("path_price_path", C2.path_kwargs(), ()),
        ("path_atm_programme", C2.path_kwargs(programme=C2.ATM_PROGRAMME), ()),
        ("path_uncovered", C2.path_kwargs(path=(("2026-11-01", "4.00"),)), ()),
        ("usage_zero", C2.usage_kwargs([*C2.C10_02, usd(atm, "0")]), ()),
        ("usage_500k", C2.usage_kwargs([*C2.C10_02, usd(atm, "500000")]), ()),
        ("usage_over_reservation", C2.usage_kwargs([*C2.C10_02, usd(atm, "2500000")]), ()),
        ("usage_unresolved", C2.usage_kwargs(C2.C10_02), ()),
        ("shelf_no_resolutions", {"registration": registered, "share_basis": shares}, ()),
        (
            "action_fixed_takedown",
            C2.usage_kwargs([*C2.C10_02, usd(atm, "0")]),
            (C2.cash(take_a, "shelf_takedown", "1000000"),),
        ),
        (
            "action_fixed_atm",
            C2.path_kwargs(programme=C2.ATM_PROGRAMME),
            (C2.cash(C2.ATM_A, "at_the_market", "1000000"),),
        ),
        (
            "action_recorded_only",
            C2.usage_kwargs([*C2.C10_02, usd(atm, "2500000")]),
            (ActionSelection(C2.ATM_A, "at_the_market", "cash"),),
        ),
        ("no_registration_path", {"share_basis": shares}, ()),
    ]


def test_x13_transactions_none_is_byte_identical_for_every_existing_fixture() -> None:
    """§0 item 1: with no ledger nothing changes, so the adapter id is not bumped."""
    cases = identity_cases()
    assert len(cases) >= 10, len(cases)
    for label, kwargs, actions in cases:
        state, scenario, rules = C1.build(**kwargs)
        if actions:
            scenario = dataclasses.replace(scenario, actions=tuple(actions))
        bare = explain_capacity(state, scenario, rules, pack=C1.PACK)
        explicit = explain_capacity(state, scenario, rules, pack=C1.PACK, transactions=None)
        assert bare.envelope.as_record() == explicit.envelope.as_record(), label
        assert _record(bare.inputs) == _record(explicit.inputs), label
        assert bare.kernel == explicit.kernel, label
        assert "transaction_ledger" not in explicit.inputs, label
        assert "transaction_usage" not in explicit.inputs, label
        assert bare.envelope.receipt.input_digest == sha256_of(_record(bare.inputs)), label
        validate_state_record("capacity_envelope", bare.envelope.as_record())
        check(explicit)


def test_c2x_the_frozen_three_parameter_evaluate_capacity_is_untouched() -> None:
    """§0 item 1: ``evaluate_capacity`` keeps the masterplan §9 interface exactly.

    ``INTERFACE_OWNERSHIP`` freezes ``evaluate_capacity`` at three parameters and
    ``tests/test_capital_structure_issuer_state_contracts.py`` asserts that length,
    so the additive ledger keyword lives on ``explain_capacity`` and the envelope
    ``evaluate_capacity`` returns is byte-identical to the no-ledger explain.
    """
    assert list(inspect.signature(c2x.evaluate_capacity).parameters) == [
        "state",
        "scenario",
        "rules",
    ]
    parameters = inspect.signature(explain_capacity).parameters
    assert list(parameters) == ["state", "scenario", "rules", "pack", "transactions", "listing"]
    assert parameters["transactions"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["transactions"].default is None
    state, scenario, rules = C1.build(**state_kwargs(SALE, resolutions=[usd(SHELF_KEY, "0")]))
    assert c2x.evaluate_capacity(state, scenario, rules).as_record() == (
        explain_capacity(state, scenario, rules, pack=C1.PACK, transactions=None).envelope.as_record()
    )


def test_c2x_exact_arithmetic_only_no_float_anywhere() -> None:
    """§0 item 7: no ``float`` call and no float literal in the adapter or here."""

    def offenders(path: Path) -> list[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                found.append(f"{path.name}:{node.lineno}: float literal {node.value!r}")
            if isinstance(node, ast.Call):
                name = node.func
                if isinstance(name, ast.Name) and name.id == "float":
                    found.append(f"{path.name}:{node.lineno}: float conversion call")
        return found

    assert offenders(ADAPTER) == []
    assert offenders(THIS_FILE) == []
    # Every amount the new inputs keys carry is exact decimal text, never a float.
    evaluation = explain(transactions=x1_ledger())
    for row in evaluation.inputs["transaction_usage"]:
        for key in ("usage", "evidenced_floor", "resolution_assumed"):
            assert row[key] is None or isinstance(row[key], str), row
            if row[key] is not None:
                # Exact decimal text: no exponent, no rounding, and a round trip
                # through Decimal reproduces the same digits.
                assert "E" not in row[key].upper(), row
                assert str(Decimal(row[key])) == row[key], row
    for value in evaluation.inputs["transaction_ledger"].values():
        assert isinstance(value, str)
