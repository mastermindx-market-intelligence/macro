"""SPEC_C2C_A §7 — the authorized-unreserved share pool inside joint capacity.

C2c-P made "how many authorized common shares are neither issued nor reserved"
observable at one instant, as a ceiling, or as a named unknown.  This module
proves the CONSUMER half: capacity reads that answer as ONE more stock pool,
``authorized_unreserved:<sale date>``, which every active share-issuing route
draws on at exactly the shares-per-dollar coefficient the Rule 5635(d) pool
charges it.

Gates exercised: L84 (reserved authorized shares limit capacity), L98 (a
cumulative state quantity and the transactions explaining it never both
decrement capacity), L102 / A19 (a split never scales authorized, issued or
reserved counts — it makes the answer unknown), A20 (an unknown is never 0 and
never infinity), A21 (a shared pool's maximum is never summed across routes)
and A48 (no score, rank, sizing or probability).

Every numeric assertion compares exact ``Decimal`` / ``Fraction`` values; there
is no float literal anywhere in this module.  Builders come from
``tests.test_capital_structure_capacity`` and are never copied, and every
observation id is derived, never hard-coded.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence

import pytest

from engine.capital_structure.capacity import explain_capacity
from engine.capital_structure.issuer_state_contracts import (
    ActionSelection,
    PriceAssumption,
    Quantity,
    _record,
    sha256_of,
    validate_state_record,
)
from tests.test_capital_structure_capacity import (
    AS_OF,
    ISSUER,
    NASDAQ_ASSUMPTIONS,
    NASDAQ_POOL,
    PATH_A,
    SALE,
    build,
    evaluate,
    pools_by_id,
    routes_by_id,
    share_basis_result,
    shift,
    standard_registration,
    strip_identity,
    unknown_ids,
    usd,
)
from tests.test_capital_structure_capacity import PACK
from tests.test_capital_structure_capacity import public_float as public_float_record

TAKE_A = f"shelf_takedown:{PATH_A}"
ATM_A = f"at_the_market:{PATH_A}"
REGISTERED_A = f"registered:{PATH_A}"
RESERVATION_A = f"programme_reservation:{PATH_A}"
USAGE_A = f"programme_usage:{PATH_A}"

#: SPEC_C2C_A §2.1: the one new pool id, named by the sale date.
AUTH_POOL = f"authorized_unreserved:{SALE}"
#: SPEC_C2C_A §4: the one new unknown id.
AUTH_UNKNOWN = f"authorized_share_headroom:{SALE}"

#: The single then-known instant every authorized-capital fact is reported at.
#: Values from different instants are never combined, so all three sides share
#: it; it sits inside ``MAX_BASIS_AGE_DAYS`` of the sale date and before it.
INSTANT = shift(SALE, 14)
AVAILABLE = f"{shift(SALE, 13)}T00:00:00Z"

#: §2.9: the class-scope condition this lane never verifies.
SCOPE_CONDITION = f"authorized_share_class_scope_not_verified:{ISSUER}:security:common_stock"
#: §2.3: ``actions=None`` is deliberate, so the selector says so honestly.
ACTIONS_CONDITION = f"corporate_actions_unobserved_since:{INSTANT}"
#: L98: issuance after the instant is a CONDITION, never a second decrement.
ISSUANCE_CONDITION = f"issuance_since_instant_not_reconciled:{INSTANT}"

#: §7: the three authorized-capital kinds, by XBRL concept.
CONCEPT_BY_KIND = {
    "common_shares_authorized": "CommonStockSharesAuthorized",
    "common_shares_issued": "CommonStockSharesIssued",
    "common_shares_reserved_for_future_issuance": (
        "CommonStockCapitalSharesReservedForFutureIssuance"
    ),
}

#: §4.2 of SPEC_C2: $2.00 in effect at the horizon start, $3.00 in the window.
PRICE_PATH = ((SALE, "2.00"), (shift(SALE, -31), "3.00"))
#: An at-the-market programme with a 2,000,000 reservation that has sold nothing.
ATM_PROGRAMME = (usd(RESERVATION_A, "2000000"), usd(USAGE_A, "0"))


def _digest(label: str, size: int) -> str:
    return hashlib.sha256(label.encode()).hexdigest()[:size]


def authorized_count(
    value: str,
    kind: str,
    *,
    label: str,
    period_end: str = INSTANT,
    available_at: str = AVAILABLE,
    evidenced: bool = True,
    issuer_id: str = ISSUER,
    authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One v2 authorized-capital share-count record.

    ``public_float`` cannot express the ``authority``, ``fact.unit`` and
    ``security_class`` blocks the C2c-P selector requires — it refuses a record
    that is not context-only and one whose fact unit is not ``shares`` — so this
    reuses that builder's exact record shape and adds only the fields the
    selector reads (see DEVIATIONS in the lane return).
    """
    record = public_float_record(
        value,
        period_end=period_end,
        available_at=available_at,
        observation_id=f"share-count-v2:cs:{_digest(label, 24)}",
        unit="shares",
        kind=kind,
    )
    record["issuer_id"] = issuer_id
    record["fact"] = {
        "namespace": "us-gaap",
        "name": CONCEPT_BY_KIND[kind],
        "unit": "shares",
        "scale": "1",
        "source_value_encoding": "companyfacts_actual_units",
    }
    record["security_class"] = {
        "state": "concept_semantic",
        "classification": "common_stock",
        "raw_label": None,
        "basis": "xbrl_concept_semantics",
    }
    record["authority"] = dict(
        authority
        or {
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
        }
    )
    record["relationships"] = {"supersedes": [], "contradiction_ids": []}
    record["version"] = {
        "immutable_record": True,
        "correction_version": 1,
        "correction_of": None,
    }
    if not evidenced:
        # §2.8: no retained-byte reference, so no known bound may be published.
        record["evidence"] = dict(record["evidence"], fact_entries=[])
    return record


def capital(
    *,
    authorized: str | None = None,
    issued: str | None = None,
    reserved: str | None = None,
    label: str = "cap",
    **overrides: Any,
) -> list[dict[str, Any]]:
    """Clean authorized-capital records at ONE instant, one per named side."""
    out: list[dict[str, Any]] = []
    for kind, value in (
        ("common_shares_authorized", authorized),
        ("common_shares_issued", issued),
        ("common_shares_reserved_for_future_issuance", reserved),
    ):
        if value is None:
            continue
        out.append(
            authorized_count(value, kind, label=f"{label}-{kind}", **overrides)
        )
    return out


def base_kwargs(
    *,
    registered: str = "20000000",
    float_value: str = "300000000",
    outstanding: str | None = "15000005",
    other: Sequence[tuple[str, str]] = NASDAQ_ASSUMPTIONS,
    price: PriceAssumption | None = None,
    programme: Sequence[Any] = (),
    extra_shares: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """One shelf path, a 300,000,000 float (no baby shelf) and 15,000,005 out."""
    reg, shares = standard_registration(
        registered=registered, float_value=float_value, outstanding=outstanding
    )
    return {
        "registration": reg,
        "share_basis": [*shares, *extra_shares],
        "other": tuple(other),
        "price": price or PriceAssumption(kind="fixed", fixed_price="2.00"),
        "resolutions": [
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            *programme,
        ],
    }


def evaluate_actions(actions: Sequence[ActionSelection], **kwargs: Any) -> Any:
    """``build`` plus asserted actions, then the same contract checks ``evaluate`` runs."""
    state, scenario, rules = build(**kwargs)
    scenario = dataclasses.replace(scenario, actions=tuple(actions))
    evaluation = explain_capacity(state, scenario, rules, pack=PACK)
    record = evaluation.envelope.as_record()
    validate_state_record("capacity_envelope", record)
    assert sha256_of(_record(evaluation.inputs)) == evaluation.envelope.receipt.input_digest
    return evaluation


def cash(route_id: str, action: str, value: str) -> ActionSelection:
    return ActionSelection(route_id, action, "cash", Quantity.known(value, "usd"))


def money(quantity: Quantity) -> Decimal:
    assert quantity.status == "known" and quantity.value is not None, quantity
    return Decimal(quantity.value)


def residual_pool(evaluation: Any, pool_id: str, branch: str = "pessimistic") -> Fraction:
    """The pool bound left after asserted actions, exactly as the kernel saw it."""
    rows = dict(evaluation.inputs["remaining_capacity"][branch]["pools"])
    assert pool_id in rows, rows
    return Fraction(rows[pool_id])


def output_blob(evaluation: Any) -> str:
    """Every string the call publishes, for the "no new vocabulary" checks."""
    record = strip_identity(evaluation.envelope.as_record())
    return json.dumps(_record(record), sort_keys=True, default=str) + json.dumps(
        _record(evaluation.inputs), sort_keys=True, default=str
    )


# ---------------------------------------------------------------------------
# §0.1 — absent authorized-capital records change nothing at all
# ---------------------------------------------------------------------------


def test_c2ca_no_authorized_records_is_byte_identical() -> None:
    """No authorized-kind record: byte-identical output, no pool, key or condition."""
    baseline, _, _ = evaluate(**base_kwargs())
    # An unrelated share-count record of a NON-authorized kind is still nothing
    # this lane reads, so the whole output must be unchanged by its presence.
    unrelated = public_float_record(
        "12345678",
        period_end=shift(SALE, 40),
        available_at=f"{shift(SALE, 39)}T00:00:00Z",
        observation_id=f"share-count-v2:cs:{_digest('unrelated-float', 24)}",
        unit="USD",
        kind="public_float",
    )
    with_unrelated, _, _ = evaluate(**base_kwargs(extra_shares=[unrelated]))
    assert strip_identity(with_unrelated.envelope.as_record()) == strip_identity(
        baseline.envelope.as_record()
    )
    for evaluation in (baseline, with_unrelated):
        # §1.4: the "authorized" inputs key is emitted ONLY when the lane ran.
        assert "authorized" not in evaluation.inputs
        assert AUTH_POOL not in pools_by_id(evaluation)
        assert AUTH_UNKNOWN not in unknown_ids(evaluation)
        blob = output_blob(evaluation)
        assert "authorized_" not in blob
        assert "authorized_unreserved" not in blob
        assert not [
            item for item in evaluation.envelope.blockers if item.startswith("authorized_share")
        ]


# ---------------------------------------------------------------------------
# §0.2 — a known headroom binds at exact dollars
# ---------------------------------------------------------------------------


def test_c2ca_known_headroom_binds_at_exact_dollars() -> None:
    """2,000,000 authorized - 1,000,000 issued - 500,000 reserved = 500,000 at $2.00."""
    evaluation, _, _ = evaluate(
        **base_kwargs(
            extra_shares=capital(
                authorized="2000000", issued="1000000", reserved="500000"
            )
        )
    )
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    pool = pools[AUTH_POOL]
    price = Decimal("2.00")
    headroom = Decimal("2000000") - Decimal("1000000") - Decimal("500000")
    assert headroom == Decimal(500_000)
    assert pool.kind == "reserved_authorized_shares"
    assert pool.stock_or_flow == "stock"
    assert pool.bound.status == "known" and pool.bound.unit == "shares"
    assert pool.bound.share_basis == "authorized_unissued"
    assert Decimal(pool.bound.value) == headroom
    assert pool.evidence, "a known bound carries its retained-byte references"
    assert pool.applicability == (
        f"authorized common shares neither issued nor reserved for future issuance at {INSTANT}"
    )
    assert INSTANT in pool.applicability
    assert pool.window_start is None and pool.window_end is None
    assert set(pool.shared_by) == {TAKE_A}
    # §3.2: fixed pricing charges every active route exactly 1/P and emits no rows.
    coefficient = Fraction(evaluation.inputs["authorized"]["coefficient"])
    assert coefficient == Fraction(1) / Fraction(price)
    assert "route_coefficients" not in evaluation.inputs["authorized"]
    assert AUTH_POOL in routes_by_id(evaluation)[TAKE_A].consumes
    # The pessimistic answer is capped at H * P when this pool is the tightest.
    assert envelope.aggregate_bound.status == "known"
    assert money(envelope.aggregate_bound) == headroom * price
    assert envelope.binding_constraints == (AUTH_POOL,)
    assert pool.status == "binding"
    assert pools[NASDAQ_POOL].status == "slack" and pools[REGISTERED_A].status == "slack"
    assert money(envelope.aggregate_bound) < money(pools[REGISTERED_A].bound)
    assert {item.route_id: money(item.quantity) for item in envelope.feasible_witness} == {
        TAKE_A: Decimal("1000000.00")
    }
    # §2.9 / §2.3: the selector's own conditions arrive verbatim, as conditions.
    conditions = routes_by_id(evaluation)[TAKE_A].conditions
    for expected in (ACTIONS_CONDITION, ISSUANCE_CONDITION, SCOPE_CONDITION):
        assert expected in conditions
    record = evaluation.inputs["authorized"]
    assert record["status"] == "known" and record["pool"] == AUTH_POOL
    assert record["headroom"]["headroom"] == "500000"
    assert record["headroom"]["instant"] == INSTANT
    assert record["ceiling"] is None
    assert record["shared_by"] == [TAKE_A]
    assert "reason" not in record


# ---------------------------------------------------------------------------
# §0.3 — a shortfall is a known zero, never a negative pool
# ---------------------------------------------------------------------------


def test_c2ca_shortfall_is_zero_bound_with_condition() -> None:
    """The reservation exceeds the unissued authorized pool: 0 shares, named."""
    evaluation, _, _ = evaluate(
        **base_kwargs(
            extra_shares=capital(
                authorized="1000000", issued="900000", reserved="200000"
            )
        )
    )
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert pool.bound.status == "known" and pool.bound.unit == "shares"
    assert pool.bound.share_basis == "authorized_unissued"
    assert Decimal(pool.bound.value) == Decimal(0)
    assert Decimal(pool.bound.value) >= Decimal(0), "a pool bound is never negative"
    condition = f"reservation_exceeds_unissued_authorized:{INSTANT}"
    assert condition in routes_by_id(evaluation)[TAKE_A].conditions
    # Zero capacity through the share routes, and the pool is what binds.
    assert envelope.aggregate_bound.status == "known"
    assert money(envelope.aggregate_bound) == Decimal("0.00")
    assert envelope.binding_constraints == (AUTH_POOL,)
    assert {item.route_id: money(item.quantity) for item in envelope.feasible_witness} == {
        TAKE_A: Decimal("0.00")
    }
    # §2.5: the SIGNED headroom stays visible in inputs even though the bound is 0.
    record = evaluation.inputs["authorized"]
    assert record["status"] == "shortfall"
    assert Decimal(record["headroom"]["headroom"]) == Decimal("-100000")
    assert record["headroom"]["reserved"] == "200000"


# ---------------------------------------------------------------------------
# §0.4 — ceiling_only feeds the ceiling solve and nothing else
# ---------------------------------------------------------------------------


def test_c2ca_ceiling_only_feeds_only_the_ceiling_solve() -> None:
    """Reserved unreported: an unknown bound, a share ceiling, and no pessimistic answer."""
    evaluation, _, _ = evaluate(
        **base_kwargs(extra_shares=capital(authorized="2000000", issued="1000000"))
    )
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.unit == "shares"
    assert pool.bound.share_basis == "authorized_unissued"
    assert pool.status == "unknown"
    assert AUTH_POOL in envelope.unknown_constraints
    assert AUTH_UNKNOWN in unknown_ids(evaluation)
    unknown = next(item for item in envelope.unknowns if item.unknown_id == AUTH_UNKNOWN)
    assert tuple(unknown.affects) == (TAKE_A,)
    assert unknown.resolving_fact == (
        "authorized, issued and reserved common shares at one then-known instant"
    )
    assert f"reserved_unobserved_at_instant:{INSTANT}" in (
        routes_by_id(evaluation)[TAKE_A].conditions
    )
    ceiling = Decimal("2000000") - Decimal("1000000")
    assert Decimal(evaluation.inputs["authorized"]["ceiling"]) == ceiling
    # §8: the substitute reaches the CEILING solve only — the pessimistic one is
    # undetermined by this pool, never silently bounded by the ceiling.
    evidence = evaluation.kernel["evidence"]
    assert evidence["determined"] is False and evidence["value"] is None
    assert AUTH_POOL in evidence["unknown_pools"]
    assert Fraction(evaluation.kernel["ceiling"]["value"]) == Fraction(ceiling) * Fraction(
        Decimal("2.00")
    )
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    # A20: the floor witness treats the unknown pool as ZERO shares — a safe
    # floor, never an unlimited one.
    assert Fraction(evaluation.kernel["evidence"]["floor_when_unknowns_zero"]) == Fraction(0)
    assert {item.route_id: money(item.quantity) for item in envelope.feasible_witness} == {
        TAKE_A: Decimal("0.00")
    }


# ---------------------------------------------------------------------------
# §0.5 — unknown headroom is unknown, never zero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "records",
    [
        pytest.param(capital(authorized="2000000", reserved="500000"), id="issued_missing"),
        pytest.param(capital(issued="1000000", reserved="500000"), id="authorized_missing"),
        pytest.param(
            capital(
                authorized="2000000",
                issued="1000000",
                reserved="500000",
                period_end=shift(SALE, 200),
                available_at=f"{shift(SALE, 199)}T00:00:00Z",
            ),
            id="stale_instant",
        ),
        pytest.param(
            capital(
                authorized="2000000",
                label="old",
                period_end=shift(SALE, 40),
                available_at=f"{shift(SALE, 39)}T00:00:00Z",
            )
            + capital(issued="1000000", reserved="500000", label="new"),
            id="sides_only_at_different_instants",
        ),
    ],
)
def test_c2ca_unknown_headroom_is_unknown_never_zero(records: Sequence[Mapping[str, Any]]) -> None:
    """A missing, stale or cross-instant side leaves the bound unknown with no substitute."""
    evaluation, _, _ = evaluate(**base_kwargs(extra_shares=list(records)))
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.unit == "shares"
    assert pool.bound.share_basis == "authorized_unissued"
    assert AUTH_POOL in envelope.unknown_constraints
    assert AUTH_UNKNOWN in unknown_ids(evaluation)
    assert evaluation.inputs["authorized"]["status"] == "unknown"
    assert evaluation.inputs["authorized"]["ceiling"] is None
    assert SCOPE_CONDITION in routes_by_id(evaluation)[TAKE_A].conditions
    # A20: unknown is never 0 — the aggregate stays unknown, and no substitute
    # reaches the ceiling solve either.
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert AUTH_POOL in evaluation.kernel["evidence"]["unknown_pools"]
    ceiling = evaluation.kernel["ceiling"]
    assert ceiling["value"] is None
    assert AUTH_POOL in ceiling["unknown_pools"]
    assert Fraction(ceiling["ceiling_when_unknowns_relaxed"]) == Fraction(6_000_000)


# ---------------------------------------------------------------------------
# §0.6 — contradicted facts are a blocker and an unknown pool
# ---------------------------------------------------------------------------


def test_c2ca_contradicted_is_blocker_and_unknown_pool() -> None:
    """Two authorized counts at one instant disagree: blocked, and never averaged."""
    records = capital(issued="1000000", reserved="500000") + [
        authorized_count("2000000", "common_shares_authorized", label="cap-a"),
        authorized_count("3000000", "common_shares_authorized", label="cap-b"),
    ]
    evaluation, _, _ = evaluate(**base_kwargs(extra_shares=records))
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert f"authorized_share_facts_contradicted:{INSTANT}" in envelope.blockers
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.share_basis == "authorized_unissued"
    assert AUTH_POOL in envelope.unknown_constraints
    assert evaluation.inputs["authorized"]["status"] == "contradicted"
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None


# ---------------------------------------------------------------------------
# §0.7 — invalid records block; no exception escapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(
            authorized_count(
                "2000000",
                "common_shares_authorized",
                label="claiming",
                authority={
                    "is_context_only": True,
                    "capacity_authority": True,
                    "rank_authority": False,
                    "sizing_authority": False,
                },
            ),
            id="authority_claiming_record",
        ),
        pytest.param(
            authorized_count(
                "2000000",
                "common_shares_authorized",
                label="not-context-only",
                authority={"is_context_only": False},
            ),
            id="not_context_only",
        ),
        pytest.param(
            authorized_count(
                "2000000",
                "common_shares_authorized",
                label="foreign",
                issuer_id="cik:0009999999",
            ),
            id="issuer_less_or_foreign",
        ),
    ],
)
def test_c2ca_invalid_records_block_not_raise(bad: Mapping[str, Any]) -> None:
    """``AuthorizedSharesInputError`` becomes a blocker and an unknown pool."""
    records = capital(issued="1000000", reserved="500000") + [dict(bad)]
    evaluation, _, _ = evaluate(**base_kwargs(extra_shares=records))
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert "authorized_share_records_invalid" in envelope.blockers
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.unit == "shares"
    assert pool.bound.share_basis == "authorized_unissued"
    assert pool.kind == "reserved_authorized_shares" and pool.stock_or_flow == "stock"
    assert AUTH_POOL in envelope.unknown_constraints
    record = evaluation.inputs["authorized"]
    assert record == {
        "pool": AUTH_POOL,
        "reason": "authorized_share_records_invalid",
        "shared_by": [TAKE_A],
    }
    # §2.3: the error CLASS is named, never the record text.
    assert "AuthorizedSharesInputError" in pool.bound.note
    assert "cik:0009999999" not in output_blob(evaluation)
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None


# ---------------------------------------------------------------------------
# §0.8 — path pricing: route coefficients and price branching
# ---------------------------------------------------------------------------


def test_c2ca_path_pricing_route_coefficients_and_branching() -> None:
    """ATM rows match the Nasdaq pool's, and branching turns on without that pool."""
    price = PriceAssumption(kind="path", path=PRICE_PATH)
    shares = capital(authorized="2000000", issued="1000000", reserved="500000")
    with_nasdaq, _, _ = evaluate(
        **base_kwargs(price=price, programme=ATM_PROGRAMME, extra_shares=shares)
    )
    assert with_nasdaq.inputs["authorized"]["route_coefficients"] == [
        [ATM_A, "pessimistic", "1/2"],
        [ATM_A, "optimistic", "1/3"],
    ]
    # Exactly the same rows the Rule 5635(d) pool charges the same route.
    assert with_nasdaq.inputs["authorized"]["route_coefficients"] == (
        with_nasdaq.inputs["nasdaq"]["route_coefficients"]
    )
    assert with_nasdaq.inputs["price"]["branching"] is True
    assert with_nasdaq.inputs["branches"] == ["price_path"]
    assert Fraction(with_nasdaq.inputs["authorized"]["coefficient"]) == Fraction(1, 2)
    assert {ATM_A, TAKE_A} <= set(pools_by_id(with_nasdaq)[AUTH_POOL].shared_by)

    # §3.3: with the assumption gate unmet there is NO Nasdaq pool, and the
    # authorized pool alone still turns price branching on.
    without_nasdaq, _, _ = evaluate(
        **base_kwargs(other=(), price=price, programme=ATM_PROGRAMME, extra_shares=shares)
    )
    assert NASDAQ_POOL not in pools_by_id(without_nasdaq)
    assert AUTH_POOL in pools_by_id(without_nasdaq)
    assert without_nasdaq.inputs["price"]["branching"] is True
    assert without_nasdaq.inputs["branches"] == ["price_path"]
    assert without_nasdaq.inputs["authorized"]["route_coefficients"] == [
        [ATM_A, "pessimistic", "1/2"],
        [ATM_A, "optimistic", "1/3"],
    ]
    assert "optimistic" in without_nasdaq.kernel


# ---------------------------------------------------------------------------
# §0.9 — an uncovered price path leaves the pool unknown
# ---------------------------------------------------------------------------


def test_c2ca_uncovered_price_path_is_unknown_pool() -> None:
    """No price in effect at the horizon start: unknown pool, placeholder coefficient."""
    price = PriceAssumption(kind="path", path=((shift(SALE, -6), "2.00"),))
    evaluation, _, _ = evaluate(
        **base_kwargs(
            price=price,
            extra_shares=capital(
                authorized="2000000", issued="1000000", reserved="500000"
            ),
        )
    )
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert evaluation.inputs["price"]["uncovered"] is True
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.share_basis == "authorized_unissued"
    record = evaluation.inputs["authorized"]
    assert record["reason"] == "price_path_uncovered"
    # The C1 placeholder is 1 / the lowest positive path price; the headroom
    # record is still reported even though it cannot be priced.
    assert Fraction(record["coefficient"]) == Fraction(1) / Fraction(Decimal("2.00"))
    assert record["status"] == "known"
    assert Decimal(record["headroom"]["headroom"]) == Decimal(500_000)
    assert "route_coefficients" not in record
    assert AUTH_POOL in evaluation.envelope.unknown_constraints
    assert evaluation.envelope.aggregate_bound.status == "unknown"


# ---------------------------------------------------------------------------
# §0.10 — A19: a split after the instant is unknown, never scaled
# ---------------------------------------------------------------------------


def split_share_basis(effective_date: str, ratio: str = "2") -> dict[str, Any]:
    """``share_basis_result`` plus a filed split; the builder cannot express one."""
    record = share_basis_result("15000005", as_of=AS_OF)
    record["corporate_action"] = {
        "kind": "forward_split",
        "ratio": ratio,
        "effective_date": effective_date,
        "contract_adjustment_evidence": [
            {
                "manifest_id": f"manifest:cs:{_digest('split', 64)}",
                "span_id": "span:split-adjustment",
                "text_sha256": _digest("split-text", 64),
            }
        ],
    }
    return record


def test_c2ca_split_after_instant_is_unknown_not_scaled() -> None:
    """A split between the instant and the cutoff unknowns the answer; no scaling."""
    shares = capital(authorized="2000000", issued="1000000", reserved="500000")
    split = split_share_basis(shift(SALE, 7))
    evaluation, _, _ = evaluate(**base_kwargs(outstanding=None, extra_shares=[*shares, split]))
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.share_basis == "authorized_unissued"
    assert pool.bound.note == "split_since_instant_unscaled:share_basis"
    assert AUTH_POOL in envelope.unknown_constraints
    assert AUTH_UNKNOWN in unknown_ids(evaluation)
    assert envelope.aggregate_bound.status == "unknown"
    # §5 / A19: NO number is multiplied or divided by the split ratio.
    record = evaluation.inputs["authorized"]
    assert record["headroom"]["authorized"] == "2000000"
    assert record["headroom"]["issued"] == "1000000"
    assert record["headroom"]["reserved"] == "500000"
    assert Decimal(record["headroom"]["headroom"]) == Decimal(500_000)
    assert record["ceiling"] is None
    assert evaluation.inputs["authorized"]["status"] == "known"
    for scaled in ("1000000", "250000", "4000000", "1000000.0"):
        assert record["headroom"]["headroom"] != scaled

    # A split effective ON OR BEFORE the instant, or AFTER the cutoff, changes
    # nothing: the headroom is still known and still unscaled.
    for effective in (INSTANT, shift(SALE, -1)):
        control, _, _ = evaluate(
            **base_kwargs(
                outstanding=None,
                extra_shares=[*shares, split_share_basis(effective)],
            )
        )
        control_pool = pools_by_id(control)[AUTH_POOL]
        assert control_pool.bound.status == "known", effective
        assert Decimal(control_pool.bound.value) == Decimal(500_000), effective


# ---------------------------------------------------------------------------
# §0.11 — an applied fixed action deducts from this pool once
# ---------------------------------------------------------------------------


def test_c2ca_applied_action_deducts_once() -> None:
    """$200,000 taken down costs 100,000 of 500,000 shares — deducted exactly once."""
    shares = capital(authorized="2000000", issued="1000000", reserved="500000")
    kwargs = base_kwargs(extra_shares=shares)
    evaluation = evaluate_actions([cash(TAKE_A, "shelf_takedown", "200000")], **kwargs)
    envelope = evaluation.envelope
    coefficient = Fraction(evaluation.inputs["authorized"]["coefficient"])
    assert coefficient == Fraction(1, 2)
    # §2.6 / L98: the pool loses coefficient * usd ONCE through _residuals.
    assert residual_pool(evaluation, AUTH_POOL) == Fraction(500_000) - coefficient * Fraction(
        200_000
    )
    assert residual_pool(evaluation, AUTH_POOL) == Fraction(400_000)
    # The Nasdaq pool takes the same single deduction on the same route.
    assert residual_pool(evaluation, NASDAQ_POOL) == Fraction(3_000_000) - Fraction(100_000)
    assert evaluation.inputs["remaining_capacity"]["pessimistic"]["fixed_total"] == "200000"
    # The aggregate adds the fixed use back exactly once: 200,000 + 400,000 * $2.
    assert envelope.aggregate_bound.status == "known"
    assert money(envelope.aggregate_bound) == Decimal("200000") + Decimal(400_000) * Decimal(
        "2.00"
    )
    assert money(envelope.aggregate_bound) == Decimal("1000000.00")
    assert envelope.binding_constraints == (AUTH_POOL,)
    # A double deduction would have left 300,000 shares and 800,000.00 dollars.
    assert money(envelope.aggregate_bound) != Decimal("800000.00")
    assert residual_pool(evaluation, AUTH_POOL) != Fraction(300_000)


# ---------------------------------------------------------------------------
# §0.12 — a known bound with no evidence reference is blocked
# ---------------------------------------------------------------------------


def test_c2ca_known_bound_without_evidence_is_blocked() -> None:
    """The Constraint contract needs evidence for a known bound, so the bound goes unknown."""
    shares = capital(
        authorized="2000000", issued="1000000", reserved="500000", evidenced=False
    )
    evaluation, _, _ = evaluate(**base_kwargs(extra_shares=shares))
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert "authorized_share_evidence_missing" in envelope.blockers
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.share_basis == "authorized_unissued"
    assert pool.evidence == ()
    assert AUTH_POOL in envelope.unknown_constraints
    # The selector still answered "known"; only the publication is withheld.
    assert evaluation.inputs["authorized"]["status"] == "known"
    assert Decimal(evaluation.inputs["authorized"]["headroom"]["headroom"]) == Decimal(500_000)
    assert envelope.aggregate_bound.status == "unknown"


# ---------------------------------------------------------------------------
# Audit repairs — independent review of PR #9414
# ---------------------------------------------------------------------------


def test_c2ca_unrepresentable_count_blocks_not_raises() -> None:
    """A count the selector's exact decimal context cannot hold is a blocker, never a raise."""
    shares = capital(authorized="1E+70", issued="1000000", reserved="500000")
    evaluation, _, _ = evaluate(**base_kwargs(extra_shares=shares))
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert "authorized_share_records_invalid" in envelope.blockers
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.share_basis == "authorized_unissued"
    assert AUTH_POOL in envelope.unknown_constraints
    assert evaluation.inputs["authorized"] == {
        "pool": AUTH_POOL,
        "reason": "authorized_share_records_invalid",
        "shared_by": [TAKE_A],
    }
    # The error CLASS is named (an ArithmeticError subclass), never the value.
    assert pool.bound.note == (
        "the authorized-capital share records could not be judged: Inexact"
    )
    assert "1E+70" not in output_blob(evaluation)
    assert envelope.aggregate_bound.status == "unknown"


def test_c2ca_ceiling_substitute_deducts_applied_action_once() -> None:
    """The ceiling solve sees the substitute LESS the applied action, never the whole ceiling."""
    shares = capital(authorized="2000000", issued="1000000")
    evaluation = evaluate_actions(
        [cash(TAKE_A, "shelf_takedown", "200000")], **base_kwargs(extra_shares=shares)
    )
    envelope = evaluation.envelope
    ceiling_shares = Fraction(1_000_000)
    applied = Fraction(1, 2) * Fraction(200_000)
    assert applied == Fraction(100_000)
    remaining = (ceiling_shares - applied) * Fraction(Decimal("2.00"))
    # The kernel's ceiling is the REMAINING capacity: 900,000 shares at $2.
    assert Fraction(evaluation.kernel["ceiling"]["value"]) == remaining
    assert remaining == Fraction(1_800_000)
    assert evaluation.kernel["ceiling"]["binding"] == [AUTH_POOL]
    # Fixed use plus remaining reproduces the ceiling exactly once: 2,000,000.00.
    # Adding the full ceiling on top of the fixed use would have read 2,200,000.00.
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.note == (
        "floor 200000.00 / ceiling 2000000.00 under stated unknowns"
    )
    assert "2200000.00" not in envelope.aggregate_bound.note
    # The pessimistic answer is still undetermined by the unknown pool.
    assert evaluation.kernel["evidence"]["determined"] is False
    assert evaluation.kernel["evidence"]["value"] is None


def test_c2ca_overrun_of_ceiling_substitute_is_infeasible() -> None:
    """An applied action above the authorized ceiling is infeasible, never clamped to zero."""
    shares = capital(authorized="2000000", issued="1000000")
    evaluation = evaluate_actions(
        [cash(TAKE_A, "shelf_takedown", "5000000")], **base_kwargs(extra_shares=shares)
    )
    envelope = evaluation.envelope
    # 5,000,000 at $2 needs 2,500,000 shares; authorized minus issued is 1,000,000.
    assert Fraction(1, 2) * Fraction(5_000_000) > Fraction(1_000_000)
    assert f"asserted_actions_infeasible:{AUTH_POOL}" in envelope.blockers
    assert envelope.aggregate_bound.status != "known"
    assert "5000000.00" not in (envelope.aggregate_bound.note or "")
    assert "under stated unknowns" not in (envelope.aggregate_bound.note or "")


def test_c2ca_action_exactly_at_ceiling_substitute_is_feasible() -> None:
    """Using the whole ceiling is not an overrun: the residual ceiling is zero, not infeasible."""
    shares = capital(authorized="2000000", issued="1000000")
    evaluation = evaluate_actions(
        [cash(TAKE_A, "shelf_takedown", "2000000")], **base_kwargs(extra_shares=shares)
    )
    envelope = evaluation.envelope
    assert not any(b.startswith("asserted_actions_infeasible") for b in envelope.blockers)
    assert Fraction(evaluation.kernel["ceiling"]["value"]) == 0
    assert envelope.aggregate_bound.note == (
        "floor 2000000.00 / ceiling 2000000.00 under stated unknowns"
    )


@pytest.mark.parametrize(
    ("mutate", "note"),
    [
        pytest.param(
            {"effective_date": None},
            "corporate_action_undated_unscaled:share_basis",
            id="split_undated",
        ),
        pytest.param(
            {"effective_date": "not-a-date"},
            "corporate_action_undated_unscaled:share_basis",
            id="split_unreadable_date",
        ),
        pytest.param(
            {"kind": None},
            "split_since_instant_unscaled:share_basis",
            id="kindless_dated_in_window",
        ),
        pytest.param(
            {"kind": None, "effective_date": None},
            "corporate_action_undated_unscaled:share_basis",
            id="kindless_undated",
        ),
    ],
)
def test_c2ca_unplaceable_corporate_action_fails_closed(
    mutate: Mapping[str, Any], note: str
) -> None:
    """An action that cannot be placed before the instant unknowns the answer; no scaling."""
    shares = capital(authorized="2000000", issued="1000000", reserved="500000")
    split = split_share_basis(shift(SALE, 7))
    split["corporate_action"].update(mutate)
    evaluation, _, _ = evaluate(**base_kwargs(outstanding=None, extra_shares=[*shares, split]))
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.bound.note == note
    assert AUTH_POOL in evaluation.envelope.unknown_constraints
    assert evaluation.envelope.aggregate_bound.status == "unknown"
    # A19: the selector's counts are reported unscaled.
    assert Decimal(evaluation.inputs["authorized"]["headroom"]["headroom"]) == Decimal(500_000)


def test_c2ca_kind_none_action_changes_nothing() -> None:
    """``kind: none`` — what the contract serializes for no action — leaves the bound known."""
    shares = capital(authorized="2000000", issued="1000000", reserved="500000")
    split = split_share_basis(shift(SALE, 7))
    split["corporate_action"] = {
        "kind": "none",
        "ratio": None,
        "effective_date": None,
        "contract_adjustment_evidence": [],
    }
    evaluation, _, _ = evaluate(**base_kwargs(outstanding=None, extra_shares=[*shares, split]))
    pool = pools_by_id(evaluation)[AUTH_POOL]
    assert pool.bound.status == "known"
    assert Decimal(pool.bound.value) == Decimal(500_000)
