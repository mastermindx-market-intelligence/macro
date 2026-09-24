"""Company Intelligence — management-outlook comparison calculator, v1.

Pure kernel for ``MANAGEMENT_REVENUE_REMAINING_YEAR``.  It accepts only the
sealed :class:`ComparableRevenueInput` produced by
``management_outlook_contract.validate_comparison_request`` and returns the
serialized ``management_outlook_comparison.v1`` envelope (which passes
``validate_comparison_result``).  It performs no I/O, no model call, no
price lookup, no publication, no identity allocation and no rights
decision.

Decomposition (all six values are exact Decimal arithmetic under
``prec=34``; intermediate values are never rounded and Decimal never
passes through a binary floating step):

    fa, fb  = midpoints of the FY_A / FY_B annual guidance ranges
    pa, pb  = sums of the ACTUAL_C_A / ACTUAL_C_B point rows
    ga_n    = sum of the GUIDE_N_A midpoints
    xb_n    = sum of the ACTUAL_N_B point rows

    annual          = fb - fa
    new_period      = xb_n - ga_n
    prior_revision  = pb - pa
    earlier_remaining = fa - pa - ga_n
    later_remaining   = fb - pb - xb_n
    remaining        = annual - new_period - prior_revision

``remaining`` must equal ``later_remaining - earlier_remaining`` exactly;
any drift raises ``ArithmeticError('decomposition identity failed')``.
There is no optional default of zero for an absent period — a nonempty
partition cell with no row is an error, and a genuine empty C partition is
an empty sum only because the chronological partition proves no earlier
period exists.  Midpoints are conventions, not expectations: nothing here
derives any distributional or band-like statement from the endpoints, and
a fiscal year with no remaining period refuses this comparison kind rather
than inventing a future outlook.
"""
from __future__ import annotations

from decimal import Decimal, localcontext

from engine.company_intelligence import management_outlook_contract as contract
from engine.company_intelligence.management_outlook_contract import (
    ComparableRevenueInput,
    DECIMAL_CONTEXT_PREC,
    LIMITATIONS,
    serialize_comparison,
    serialize_input_echo,
)

ZERO = Decimal(0)
NO_REMAINING_EXPLANATION = (
    "the selected fiscal year has no remaining period; this comparison kind "
    "does not project a future outlook"
)


def _midpoint(low: Decimal, high: Decimal) -> Decimal:
    return (low + high) / 2


def _collect_role_rows(inputs: ComparableRevenueInput) -> dict[str, list]:
    """Group sealed rows by role, re-asserting coverage on the typed input.

    The request validator already enforces this; the kernel repeats the
    check so a hand-assembled dataclass with a row gap can never be read as
    a silent zero.
    """
    rows_by_role: dict[str, list] = {}
    for row in inputs.role_amounts:
        rows_by_role.setdefault(row.role, []).append(row)
    for role in contract.ANNUAL_ROLES:
        rows = rows_by_role.get(role, [])
        if not rows:
            contract._fail("missing_role", f"no {role} row on the sealed input")
        if len(rows) > 1:
            contract._fail("duplicate_role_row", f"{len(rows)} {role} rows on the sealed input")
    contract._check_cell_coverage(rows_by_role.get("ACTUAL_C_A", []), list(inputs.completed), "ACTUAL_C_A")
    contract._check_cell_coverage(rows_by_role.get("ACTUAL_C_B", []), list(inputs.completed), "ACTUAL_C_B")
    contract._check_cell_coverage(rows_by_role.get("GUIDE_N_A", []), list(inputs.newly_completed), "GUIDE_N_A")
    contract._check_cell_coverage(rows_by_role.get("ACTUAL_N_B", []), list(inputs.newly_completed), "ACTUAL_N_B")
    return rows_by_role


def _point_sum(rows) -> Decimal:
    total = ZERO
    for row in rows:
        total += row.amount.low
    return total


def _midpoint_sum(rows) -> Decimal:
    total = ZERO
    for row in rows:
        total += _midpoint(row.amount.low, row.amount.high)
    return total


def compare_management_outlook(inputs: ComparableRevenueInput) -> dict:
    if not isinstance(inputs, ComparableRevenueInput):
        contract._fail("invalid_request_shape", "compare_management_outlook accepts only a sealed ComparableRevenueInput")

    rows_by_role = _collect_role_rows(inputs)
    envelope_base = {
        **serialize_input_echo(inputs),
        "limitations": list(LIMITATIONS),
        "correction": {"corrected": False, "predecessor_id": None, "reason": None},
    }

    if not inputs.remaining:
        return serialize_comparison({
            **envelope_base,
            "eligible": False,
            "reasons": ["no_remaining_horizon"],
            "explanation": NO_REMAINING_EXPLANATION,
            "values": None,
        })

    with localcontext() as context:
        context.prec = DECIMAL_CONTEXT_PREC
        fy_a = rows_by_role["FY_A"][0].amount
        fy_b = rows_by_role["FY_B"][0].amount
        fa = _midpoint(fy_a.low, fy_a.high)
        fb = _midpoint(fy_b.low, fy_b.high)
        pa = _point_sum(rows_by_role.get("ACTUAL_C_A", []))
        pb = _point_sum(rows_by_role.get("ACTUAL_C_B", []))
        ga_n = _midpoint_sum(rows_by_role.get("GUIDE_N_A", []))
        xb_n = _point_sum(rows_by_role.get("ACTUAL_N_B", []))

        annual = fb - fa
        new_period = xb_n - ga_n
        prior_revision = pb - pa
        earlier_remaining = fa - pa - ga_n
        later_remaining = fb - pb - xb_n
        remaining_change = annual - new_period - prior_revision
        if remaining_change != later_remaining - earlier_remaining:
            raise ArithmeticError("decomposition identity failed")

        values = {
            "annual_midpoint_change": annual,
            "new_period_deviation": new_period,
            "prior_actual_revision": prior_revision,
            "earlier_remaining": earlier_remaining,
            "later_remaining": later_remaining,
            "remaining_change": remaining_change,
        }

    return serialize_comparison({
        **envelope_base,
        "eligible": True,
        "reasons": [],
        "explanation": contract.ELIGIBLE_EXPLANATION,
        "values": values,
    })
