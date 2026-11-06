"""SPEC_A1 §3 — end-to-end metamorphic and boundary properties on the SERVED path.

Lane A1-2 (domestic evaluate cut, base ``726adf122c3``).  Kernel-level A22 is
already proven by the kernel suites (the joint-solve and C2 §5.3 tests); this
file lifts the same properties through the whole served stack — input assembly,
route eligibility, the joint solve, the API projection and the response
contract — using ONLY the ``POST …/scenarios/evaluate`` route through FastAPI
``TestClient``.  No test here calls the solver, the composition entry point or
any engine calculation directly: every asserted answer is read from a served
response, and every response passes through the U1B suite's own ``_checked``
helper first.

Variants are built from ONE base scenario by explicit named transformation
functions, and every response body this file produces is collected into a
module-scoped registry that ``test_a1_zz_no_forbidden_vocabulary_in_any_served_body``
(defined and run last) walks for the A48 vocabulary.
"""
from __future__ import annotations

import calendar
import dataclasses
import json
import re
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal
from fractions import Fraction
from typing import Any

import pytest

pytest.importorskip("fastapi", reason="capital structure API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

# Import the U1B evaluate-route fixtures and helpers by name (never copied).
# Fixture functions stay bound to their own module's globals, so pytest
# discovers them here exactly as in the originating suite, and importing this
# module never re-collects the U1B tests.
from tests.test_capital_structure_state_api import (  # noqa: E402
    EVALUATE_PATH,
    HORIZON_END,
    HORIZON_START,
    ISSUER_ONE,
    SCENARIO_ASSUMPTIONS,
    SCENARIO_PRICE,
    SS,
    _checked,
    _earliest_bound,
    _fixture_entries,
    _inputs_bundle_record,
    _scenario_body,
    _shift,
    built,
    client,
    inputs_suite,
    pack,
    served,
    with_inputs,
)
from engine.capital_structure.issuer_state_contracts import (  # noqa: E402
    AUTHORITY,
    FORBIDDEN_PROPERTY_PATTERN,
)
from engine.capital_structure.scenario_inputs import CAPACITY_INPUTS_FILENAME  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture-world constants, read from the contracts (never assumed)
# ---------------------------------------------------------------------------

#: The baby-shelf sale date is the scenario's horizon start (capacity.py:828),
#: so the A15 resolution ids are keyed with it.
_SALE_ISO = HORIZON_START
_FLOAT_RESOLUTION_ID = f"baby_shelf_public_float:{_SALE_ISO}"
_SOLD_RESOLUTION_ID = f"baby_shelf_sold_trailing:{_SALE_ISO}"
_BABY_SHELF_RULES = ("form_s3.I.B.6", "form_f3.I.B.5")
#: The one-third limit does not apply at or above this float
#: (rule_applicability.py:64 and :func:`baby_shelf_limit`).
_FLOAT_THRESHOLD = Decimal("75000000")

#: Reduced from the fixture's 1,000,000 outstanding warrants.
_LOWERED_INSTRUMENTS_OUTSTANDING = "400000"
#: The added trailing-sale resolution for ``add_trailing_sale``.
_ADDED_TRAILING_SOLD_USD = "4000000.00"
#: The trailing-12-month sold amount the boundary requests state, so the
#: one-third pool's headroom is fully known (an unresolved operand keeps the
#: whole bound unknown, which would say nothing about the boundary under test).
_RESOLVED_TRAILING_SOLD_USD = "1000000.00"
#: The shortened scenario window for ``shorten_window``.
_SHORTENED_HORIZON_END = "2026-11-30"

#: The unit-rescaling pair: the same economics at the stated fixed price.
_RESCALING_USD = "3000000.00"
_RESCALING_SHARES = "1500000"

#: The zero-headroom pair: this float caps the pool at exactly this limit.
_ZERO_HEADROOM_FLOAT = "30000000.00"
_ZERO_HEADROOM_LIMIT = "10000000.00"
_ONE_CENT = Decimal("0.01")

#: §3.6 — the A48 vocabulary this file's walker enforces on VALUES and KEYS.
#: The contract's own ``FORBIDDEN_PROPERTY_PATTERN`` (issuer_state_contracts
#: .py:445) only ever refuses a WHOLE name (it is anchored ``^…$``), so a key
#: like ``probability_of_recovery`` slips past it; the walker therefore runs
#: the stem search on keys too, and keeps the contract pattern as the
#: exact-name law on top.
_VOCABULARY_STEMS = (
    "probability",
    "likelihood",
    "score",
    "rank",
    "rating",
    "recommend",
    "sizing",
    "entry",
    "should buy",
    "should sell",
    "should raise",
    "target price",
)
_VALUE_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(stem) for stem in _VOCABULARY_STEMS) + r")",
    re.IGNORECASE,
)

#: The contract's own authority record (projection.py:31-37, served verbatim in
#: every response body): ``rank_authority``/``sizing_authority``/``entry_authority``
#: are the literal ``False`` denials the state family itself must carry — a
#: refusal, not an output.  The walker exempts exactly those keys, and only
#: while they hold the literal ``False``, mirroring the contract's own rule for
#: ``prophet_authority`` (issuer_state_contracts.py:543-544).
_AUTHORITY_DENIAL_KEYS = frozenset(AUTHORITY)

#: Every earlier served test must contribute at least one body to the walk.
_SERVED_TESTS = (
    "test_a1_tightening_never_raises_served_bound",
    "test_a1_row_order_permutation_is_byte_identical",
    "test_a1_unit_rescaling_or_assert_no_unit",
    "test_a1_boundary_ib6_threshold_one_cent_either_side",
    "test_a1_boundary_zero_headroom",
    "test_a1_boundary_trailing_window_day_365_and_366",
    "test_a1_boundary_cutoff_equal_to_available_at",
    "test_a1_unknown_route_limit_gives_floor_and_open_ceiling",
    "test_a1_unknown_share_count_never_zero_or_unlimited",
    "test_a1_missing_input_family_returns_typed_409_with_components",
)
_WALKER_TEST = "test_a1_zz_no_forbidden_vocabulary_in_any_served_body"

#: Response bodies produced by this file, keyed by the test that produced them.
_BODIES_BY_TEST: dict[str, list[dict[str, Any]]] = {}
#: Boundary cases the served route cannot express on this base, quoted.
_NOT_EXPRESSIBLE: list[str] = []
_RUNNING_TEST = "module_import"


@pytest.fixture(autouse=True)
def _attribute_bodies(request: pytest.FixtureRequest) -> None:
    """Attribute every collected body to the test that is collecting it."""
    global _RUNNING_TEST
    previous = _RUNNING_TEST
    _RUNNING_TEST = request.node.name
    _BODIES_BY_TEST.setdefault(request.node.name, [])
    yield
    _RUNNING_TEST = previous


def _collect(response: Any, body: Any) -> None:
    _BODIES_BY_TEST.setdefault(_RUNNING_TEST, []).append(
        {"status": response.status_code, "body": body}
    )


def _serve(
    client: Any,
    body: dict[str, Any],
    *,
    params: dict[str, str] | None = None,
    status: int = 200,
) -> Any:
    """POST through the route, check the response, collect it, return the body."""
    response = client.post(EVALUATE_PATH, json=body, params=params or {})
    checked = _checked(response, status=status)
    _collect(response, checked)
    return checked


# ---------------------------------------------------------------------------
# Exact readers over served records (Decimal/Fraction only)
# ---------------------------------------------------------------------------


def _decimal_value(quantity: Any) -> Decimal | None:
    """The exact value of a served Quantity record, or None when not known."""
    if not isinstance(quantity, dict) or quantity.get("status") != "known":
        return None
    value = quantity.get("value")
    return None if value is None else Decimal(str(value))


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    return body["result"]["capacity_envelope"]


def _rule_token(pool_record: dict[str, Any]) -> str:
    """The rule id a served constraint record is filed under."""
    applicability = str(pool_record.get("applicability") or "")
    matched = re.match(r"[A-Za-z0-9_.]+", applicability)
    assert matched is not None, f"constraint without a rule token: {applicability!r}"
    return matched.group(0)


def _pools_by_rule(envelope: dict[str, Any], rules: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        pool
        for pool in envelope.get("shared_pools") or ()
        if _rule_token(pool) in rules
    ]


def _binding_rule_names(envelope: dict[str, Any]) -> set[str]:
    bound_ids = set(envelope.get("binding_constraints") or ())
    return {
        _rule_token(pool)
        for pool in envelope.get("shared_pools") or ()
        if pool.get("constraint_id") in bound_ids
    }


def _publish_bundle(served: Any, built: Any, entries: dict[str, Any], *, as_of: str) -> None:
    """Publish one variant capacity inputs bundle next to the served state."""
    try:
        record = _inputs_bundle_record(built, entries=entries, as_of=as_of)
    except (AssertionError, ValueError) as exc:
        pytest.fail(
            f"a capacity inputs bundle cut at {as_of!r} cannot be built on this "
            f"base: {type(exc).__name__}: {exc}"
        )
    path = served.state_path.parent / CAPACITY_INPUTS_FILENAME
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    served.reset()


def _keep_entries(entries: dict[str, Any]) -> dict[str, Any]:
    return entries


def _with_lowered_pool_bound(entries: dict[str, Any]) -> dict[str, Any]:
    """The instruments family with the outstanding pool bound lowered.

    The rebuilt set is re-keyed to the served issuer and as_of exactly as
    ``_fixture_entries`` re-keys its own families (scenario_inputs.py:931-937
    refuses a binding cut at any other instant).
    """
    as_of = entries[inputs_suite.INSTRUMENTS_FAMILY].binding.as_of
    instrument_id, instrument = SS.make_instrument(
        "series_u1b_gate_warrants",
        instruments_outstanding=_LOWERED_INSTRUMENTS_OUTSTANDING,
        shares_per_instrument="1",
        exercise_price="1.50",
    )
    entries[inputs_suite.INSTRUMENTS_FAMILY] = inputs_suite._entry_for(
        dataclasses.replace(
            SS.instrument_set((instrument_id, instrument)),
            issuer_id=ISSUER_ONE,
            as_of=as_of,
        ),
        inputs_suite.INSTRUMENTS_FAMILY,
    )
    return entries


def _with_unknown_outstanding(entries: dict[str, Any]) -> dict[str, Any]:
    """The instruments family with an UNKNOWN outstanding count (never zero).

    The contract admits an unknown the only way it allows (issuer_state_contracts
    .py:2520-2527): an ``unknown`` term whose Quantity carries no value — never an
    admitted term with no value, never a zero count.
    """
    as_of = entries[inputs_suite.INSTRUMENTS_FAMILY].binding.as_of
    instrument_id = SS.series_id("series_u1b_gate_warrants")
    unknown_term = SS.economic_term(
        instrument_id, "instruments_outstanding", status="unknown"
    )
    rebuilt_id, instrument = SS.make_instrument(
        "series_u1b_gate_warrants", instruments_outstanding=unknown_term
    )
    entries[inputs_suite.INSTRUMENTS_FAMILY] = inputs_suite._entry_for(
        dataclasses.replace(
            SS.instrument_set((rebuilt_id, instrument)),
            issuer_id=ISSUER_ONE,
            as_of=as_of,
        ),
        inputs_suite.INSTRUMENTS_FAMILY,
    )
    return entries


def _with_unavailable_commitments(entries: dict[str, Any]) -> dict[str, Any]:
    """The commitments family unavailable with a reason from the closed vocabulary.

    ``commitment_rows_absent`` is one of the schema's eight reason codes
    (capital_structure_capacity_inputs.v1.schema.json:129-140).
    """
    entries[inputs_suite.COMMITMENTS_FAMILY] = inputs_suite.FamilyEntry(
        family=inputs_suite.COMMITMENTS_FAMILY,
        support="unavailable",
        reason_codes=("commitment_rows_absent",),
    )
    return entries


def _resolution_body(unknown_id: str, value: str) -> dict[str, Any]:
    return {
        "unknown_id": unknown_id,
        "assumed": {"unit": "usd", "status": "known", "value": value},
        "rationale": "a1 served property supplies the exact amount",
    }


def _route_id_of_first(body: dict[str, Any]) -> str:
    routes = _envelope(body).get("routes") or ()
    assert routes, f"no served route in {json.dumps(_envelope(body))[:400]}"
    return str(routes[0]["route_id"])


def _route_kind_of(body: dict[str, Any], route_id: str) -> str:
    for route in _envelope(body).get("routes") or ():
        if route.get("route_id") == route_id:
            return str(route["route_kind"])
    raise AssertionError(f"route {route_id!r} missing from the served envelope")


def _route_conditions_of(body: dict[str, Any], route_id: str) -> list[str]:
    """The conditions one served route itself carries.

    An action on an envelope route may only assume conditions that route
    carries (capacity.py:3223-3228), so the asserted list is read from the
    route, never invented.
    """
    for route in _envelope(body).get("routes") or ():
        if route.get("route_id") == route_id:
            return [str(condition) for condition in route.get("conditions") or ()]
    raise AssertionError(f"route {route_id!r} missing from the served envelope")


# ---------------------------------------------------------------------------
# §3.1 — tightening (A22) on the served path
# ---------------------------------------------------------------------------


def _transform_lower_pool_bound(
    client: Any, served: Any, built: Any, body: dict[str, Any], as_of: str
) -> dict[str, Any]:
    _publish_bundle(served, built, _with_lowered_pool_bound(_fixture_entries(as_of)), as_of=as_of)
    return body


def _transform_add_trailing_sale(
    client: Any, served: Any, built: Any, body: dict[str, Any], as_of: str
) -> dict[str, Any]:
    body["unknown_resolutions"] = [
        _resolution_body(_SOLD_RESOLUTION_ID, _ADDED_TRAILING_SOLD_USD)
    ]
    return body


def _transform_shorten_window(
    client: Any, served: Any, built: Any, body: dict[str, Any], as_of: str
) -> dict[str, Any]:
    body["horizon_end"] = _SHORTENED_HORIZON_END
    return body


_TRANSFORMATIONS = {
    "lower_pool_bound": _transform_lower_pool_bound,
    "add_trailing_sale": _transform_add_trailing_sale,
    "shorten_window": _transform_shorten_window,
}

#: The served bounds the never-increases property covers.
_SERVED_BOUNDS = (
    ("capacity_envelope", "aggregate_bound"),
    ("scenario_new_shares_low",),
    ("scenario_new_shares_high",),
)


@pytest.mark.parametrize("transformation", sorted(_TRANSFORMATIONS))
def test_a1_tightening_never_raises_served_bound(
    client: Any, served: Any, built: Any, with_inputs: Any, transformation: str
) -> None:
    """Adding one valid tighter constraint never raises a served feasible bound.

    When a bound stays equal, the transformation's constraint is not newly
    ``binding`` — the tightened baby-shelf pool (when served) reads ``slack``.
    """
    base = _serve(client, _scenario_body())
    as_of = base["result"]["as_of"]
    transform = _TRANSFORMATIONS[transformation]
    tight = _serve(client, transform(client, served, built, _scenario_body(), as_of))

    for path in _SERVED_BOUNDS:
        node, other = base["result"], tight["result"]
        for key in path:
            node, other = node[key], other[key]
        base_value, tight_value = _decimal_value(node), _decimal_value(other)
        if base_value is not None and tight_value is not None:
            assert tight_value <= base_value, (
                f"{transformation}: served bound {'.'.join(path)} rose from "
                f"{base_value} to {tight_value}"
            )

    base_aggregate = _decimal_value(_envelope(base)["aggregate_bound"])
    tight_aggregate = _decimal_value(_envelope(tight)["aggregate_bound"])
    if (
        base_aggregate is not None
        and tight_aggregate is not None
        and tight_aggregate == base_aggregate
    ):
        newly_binding = (
            _binding_rule_names(_envelope(tight))
            - _binding_rule_names(_envelope(base))
        )
        assert not newly_binding, (
            f"{transformation}: the aggregate stayed {tight_aggregate} but new "
            f"constraints became binding: {sorted(newly_binding)}"
        )
        if transformation == "add_trailing_sale":
            for pool in _pools_by_rule(_envelope(tight), _BABY_SHELF_RULES):
                assert pool.get("status") != "binding", (
                    f"{transformation}: the tightened baby-shelf pool is "
                    f"reported binding at an unchanged aggregate: {pool!r}"
                )


# ---------------------------------------------------------------------------
# §3.2 — row order (A22): permutation is byte-identical outside the echo
# ---------------------------------------------------------------------------

#: The request-echo and request-identity fields the §3.2 comparison removes:
#: ``view`` echoes the request's own view identity (mode/as_of/clock plus the
#: state, generation and scenario ids); ``scenario_id`` and ``result_id``
#: digest the request's assumption order; ``input_digest`` and ``receipt_id``
#: digest the receipts' inputs, which carry that same scenario identity.
#: Nothing else is removed.
_REMOVED_ECHO_FIELDS = ("view", "scenario_id", "result_id", "input_digest", "receipt_id")


def _strip_identity(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_identity(item)
            for key, item in value.items()
            if key not in _REMOVED_ECHO_FIELDS
        }
    if isinstance(value, list):
        return [_strip_identity(item) for item in value]
    return value


def _canonical(body: dict[str, Any]) -> str:
    return json.dumps(_strip_identity(body), sort_keys=True, separators=(",", ":"))


def _body_with_rows(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    body = _scenario_body()
    body["unknown_resolutions"] = resolutions
    body["other_assumptions"] = [list(pair) for pair in SCENARIO_ASSUMPTIONS]
    return body


def test_a1_row_order_permutation_is_byte_identical(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """Permuting request row order changes nothing but the request echo.

    Variants over ONE base request: the resolution list reversed, the
    other-assumption pairs reversed, and the action-selection list reversed
    (route ids read from a first served response, never invented).
    """
    probe = _serve(client, _scenario_body())
    route_ids = [
        str(route["route_id"])
        for route in _envelope(probe).get("routes") or ()
        if isinstance(route, dict)
    ]

    resolutions = [
        _resolution_body(_SOLD_RESOLUTION_ID, "1000000.00"),
        _resolution_body(_FLOAT_RESOLUTION_ID, "40000000.00"),
    ]
    forward_body = _body_with_rows(resolutions)
    if len(route_ids) >= 2:
        forward_body["actions"] = [
            {
                "route_id": route_id,
                "action": _route_kind_of(probe, route_id),
                "settlement": "cash",
                "conditions_assumed_met": _route_conditions_of(probe, route_id),
            }
            for route_id in route_ids[:2]
        ]
    forward = _serve(client, forward_body)

    backward_body = json.loads(json.dumps(forward_body))
    backward_body["unknown_resolutions"] = list(
        reversed(backward_body["unknown_resolutions"])
    )
    backward_body["other_assumptions"] = list(
        reversed(backward_body["other_assumptions"])
    )
    if isinstance(backward_body.get("actions"), list):
        backward_body["actions"] = list(reversed(backward_body["actions"]))
    backward = _serve(client, backward_body)

    assert _canonical(forward) == _canonical(backward), (
        "row order changed the served answer outside the request echo "
        f"(removed {_REMOVED_ECHO_FIELDS})"
    )


# ---------------------------------------------------------------------------
# §3.3 — unit rescaling: the same economics in the other stated unit
# ---------------------------------------------------------------------------


def _economic_signature(body: dict[str, Any]) -> str:
    """The economic content of one served answer, exactly normalised.

    Identity digests and the request echo are excluded; the envelope's bound,
    binding names, pools, witness, the share totals and the issuance rows are
    what restating units must not move.
    """
    result = _strip_identity(body)["result"]
    signature = {
        "aggregate_bound": result["capacity_envelope"]["aggregate_bound"],
        "binding_constraints": sorted(
            result["capacity_envelope"].get("binding_constraints") or ()
        ),
        "shared_pools": result["capacity_envelope"].get("shared_pools") or (),
        "feasible_witness": result["capacity_envelope"].get("feasible_witness"),
        "scenario_new_shares_low": result["scenario_new_shares_low"],
        "scenario_new_shares_high": result["scenario_new_shares_high"],
    }
    return json.dumps(signature, sort_keys=True, separators=(",", ":"))


def test_a1_unit_rescaling_or_assert_no_unit(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """Restating one action's economics in the other unit changes nothing.

    The contract carries a unit (``Quantity.unit``), and an action quantity is
    converted into gross dollars at the scenario's own price
    (capacity.py:3252-3262): ``X usd`` and ``X / fixed_price shares`` are the
    same economics at the stated fixed price ``2.00``.
    """
    assert SCENARIO_PRICE == "2.00", "the stated fixed price moved"
    probe = _serve(client, _scenario_body())
    route_id = _route_id_of_first(probe)
    assert (
        Fraction(_RESCALING_SHARES) * Fraction(SCENARIO_PRICE) == Fraction(_RESCALING_USD)
    ), "the rescaling pair is not the same economics at the fixed price"

    usd_body = _scenario_body()
    usd_body["actions"] = [
        {
            "route_id": route_id,
            "action": _route_kind_of(probe, route_id),
            "settlement": "cash",
            "conditions_assumed_met": _route_conditions_of(probe, route_id),
            "quantity": {"unit": "usd", "status": "known", "value": _RESCALING_USD},
        }
    ]
    share_body = json.loads(json.dumps(usd_body))
    #: The scenario share quantity names the scenario basis, exactly as the
    #: contract requires of a scenario issuance share count
    #: (issuer_state_contracts.py:1914-1921).
    share_body["actions"][0]["quantity"] = {
        "unit": "shares",
        "status": "known",
        "value": _RESCALING_SHARES,
        "share_basis": "scenario_incremental_issuance",
    }

    usd_answer = _serve(client, usd_body)
    share_answer = _serve(client, share_body)
    assert _economic_signature(usd_answer) == _economic_signature(share_answer), (
        "restating the same economics in the other unit moved the served answer"
    )


# ---------------------------------------------------------------------------
# §3.4 — boundaries
# ---------------------------------------------------------------------------


def test_a1_boundary_ib6_threshold_one_cent_either_side(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """Public float at the I.B.6 threshold and one cent either side.

    The contract (:func:`baby_shelf_limit`, rule_applicability.py:993-1014): a
    float at or above $75,000,000 makes the one-third limit ``not_applicable``;
    below it the limit is float/3 rounded DOWN to the cent.  The served pool
    bound is the one-third limit less the resolved trailing sales
    (capacity.py:2176-2189 serves ``pool.headroom``), so the trailing-12-month
    sold amount is resolved to one stated value in every case: a bound operand
    left unresolved keeps the whole headroom unknown, which would say nothing
    about the threshold.

    Served shape: below the threshold the I.B.6 pool is in ``shared_pools`` with
    the exact headroom; at or above it the limit does not apply, so no I.B.6
    pool is served at all and every consuming route names why
    (capacity.py:2160-2164 adds the ``…not_applicable…75m`` path condition).
    """
    below_limit = (Decimal("74999999.99") / 3).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )
    cases = [
        ("74999999.99", below_limit - Decimal(_RESOLVED_TRAILING_SOLD_USD)),
        ("75000000.00", None),
        ("75000000.01", None),
    ]
    for float_value, expected_headroom in cases:
        body = _scenario_body()
        body["unknown_resolutions"] = [
            _resolution_body(_FLOAT_RESOLUTION_ID, float_value),
            _resolution_body(_SOLD_RESOLUTION_ID, _RESOLVED_TRAILING_SOLD_USD),
        ]
        answer = _serve(client, body)
        pools = _pools_by_rule(_envelope(answer), _BABY_SHELF_RULES)
        if expected_headroom is None:
            assert not pools, (
                f"float {float_value} (>= {_FLOAT_THRESHOLD}): the one-third "
                f"limit does not apply, but an I.B.6 pool is still served: "
                f"{pools!r}"
            )
            named = [
                route
                for route in _envelope(answer).get("routes") or ()
                if "baby_shelf_not_applicable_public_float_at_or_above_75m"
                in (route.get("conditions") or ())
            ]
            assert named, (
                f"float {float_value}: no served route names the 75m "
                f"not-applicability: "
                f"{json.dumps(_envelope(answer).get('routes'), sort_keys=True)[:800]}"
            )
        else:
            assert pools, (
                f"float {float_value} (< {_FLOAT_THRESHOLD}): expected the "
                f"I.B.6 pool served, got "
                f"{json.dumps(_envelope(answer), sort_keys=True)[:800]}"
            )
            bound = pools[0]["bound"]
            assert bound["status"] == "known", (
                f"float {float_value} (< {_FLOAT_THRESHOLD}): expected a known "
                f"limit, got {bound!r}"
            )
            assert Decimal(bound["value"]) == expected_headroom, (
                f"float {float_value}: limit {bound['value']} != "
                f"{expected_headroom}"
            )


def test_a1_boundary_zero_headroom(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """Exactly-zero headroom serves bound 0; one cent serves bound 0.01.

    Two contracts meet at this boundary, and the A1 ruling (seat a9559a4c,
    2026-10-19) keeps them apart:

    * POOL-LOCAL (:func:`baby_shelf_pool`, rule_applicability.py:1088-1089):
      gap == 0 is ``binding``, gap > 0 is ``slack``.  Tested directly on the
      rule function below, at the exact cent.
    * SERVED (capacity.py ``_constraints``): ``Constraint.status`` says whether
      the pool binds the JOINT optimum (masterplan §3: "The share constraint is
      not binding in that example").  It is ``binding``/``slack`` only when the
      joint solution is determined, the pool is active and its bound is known;
      otherwise it is ``unknown``.  The fixture world has no active route, so
      the served envelope names ``no_active_route`` and both statuses are
      ``unknown`` — the pool-local exhaustion is still served exactly, through
      the known bound ``0``.

    A float of $30,000,000 caps the pool at exactly $10,000,000.00 (one third,
    no rounding remnant).  Proving the served binding/slack flip needs a
    fixture with an active route; that gap is carried to A1-1.
    """
    cases = [
        ("binding", format(Decimal(_ZERO_HEADROOM_LIMIT), "f")),
        ("slack", format(Decimal(_ZERO_HEADROOM_LIMIT) - _ONE_CENT, "f")),
    ]
    observed: dict[str, dict[str, Any]] = {}
    blockers: dict[str, list[str]] = {}
    for expected_status, sold_value in cases:
        body = _scenario_body()
        body["unknown_resolutions"] = [
            _resolution_body(_FLOAT_RESOLUTION_ID, _ZERO_HEADROOM_FLOAT),
            _resolution_body(_SOLD_RESOLUTION_ID, sold_value),
        ]
        answer = _serve(client, body)
        pools = _pools_by_rule(_envelope(answer), _BABY_SHELF_RULES)
        assert pools, (
            f"no baby-shelf pool served for sold {sold_value}; envelope: "
            f"{json.dumps(_envelope(answer), sort_keys=True)[:800]}"
        )
        observed[expected_status] = pools[0]
        blockers[expected_status] = list(_envelope(answer).get("blockers") or ())
    #: The exact headroom is served either way: gap == 0 serves bound ``0``,
    #: the one-cent gap serves bound ``0.01``.
    for case in ("binding", "slack"):
        assert observed[case]["bound"]["status"] == "known", (
            f"{case}: the pool bound must be known: {observed[case]!r}"
        )
    assert Decimal(observed["binding"]["bound"]["value"]) == Decimal("0"), (
        "the zero gap must serve bound 0"
    )
    assert Decimal(observed["slack"]["bound"]["value"]) == _ONE_CENT, (
        "the one-cent gap must serve bound 0.01"
    )
    #: Joint semantics: with no active route the joint solution is not
    #: determined, so the served status is ``unknown`` and the envelope says why.
    for case in ("binding", "slack"):
        assert "no_active_route" in blockers[case], (
            f"{case}: expected the envelope to name no_active_route, got "
            f"{blockers[case]!r}"
        )
        assert observed[case]["status"] == "unknown", (
            f"{case}: with no active route the joint status must be unknown, "
            f"got {observed[case]!r}"
        )


@pytest.mark.parametrize(
    ("sold", "expected_status", "expected_headroom"),
    [
        ("20000000.00", "binding", Decimal("0")),
        ("19999999.99", "slack", _ONE_CENT),
    ],
)
def test_a1_boundary_zero_headroom_pool_local(
    pack: Any, sold: str, expected_status: str, expected_headroom: Decimal
) -> None:
    """The pool-local contract at the exact cent (rule_applicability.py:1088-1089).

    A $60,000,000 float caps the one-third pool at exactly $20,000,000.00, so
    sold == limit leaves a zero gap (``binding``) and one cent less leaves a
    one-cent gap (``slack``).  This is the boundary the served joint status
    cannot show without an active route (see the test above).
    """
    from engine.capital_structure import rule_applicability as ra
    from engine.capital_structure.issuer_state_contracts import Quantity

    pool = ra.baby_shelf_pool(
        pack,
        public_float=Quantity.known("60000000", "usd"),
        float_measured_on="2026-09-01",
        sold_trailing=Quantity.known(sold, "usd"),
        sold_window=("2025-10-15", "2026-10-14"),
        sale_date="2026-10-14",
        form="S-3",
    )
    assert pool.constraint.status == expected_status, pool.as_record()
    assert pool.headroom.status == "known", pool.as_record()
    assert Decimal(pool.headroom.value) == expected_headroom, pool.as_record()
    assert Decimal(pool.overrun.value) == Decimal("0"), pool.as_record()


def test_a1_boundary_trailing_window_day_365_and_366(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """The trailing window ends on and includes the sale date.

    The contract (:func:`_twelve_month_window`, rule_applicability.py:1017-1022)
    makes the window ``[sale − 1 year (day-clamped) + 1 day, sale]`` —
    inclusive of both ends.  For the fixture sale on 2026-10-14 the window is
    2025-10-15..2026-10-14: the 365 calendar days ending on the sale date, so
    day one (the window start) is inside and the day before the start (the
    "day 366" side) is outside.  The float is resolved alongside the sold
    amount so the pool bound is known and the served window is the one the
    known bound was computed over.  This base carries no dated-sale input the
    route reads — ``_sold_trailing`` accepts only the aggregate resolution
    (capacity.py:2260-2269) — so a dated day-365/day-366 sale itself is
    recorded as not expressible, never invented.
    """
    body = _scenario_body()
    body["unknown_resolutions"] = [
        _resolution_body(_FLOAT_RESOLUTION_ID, "40000000.00"),
        _resolution_body(_SOLD_RESOLUTION_ID, _RESOLVED_TRAILING_SOLD_USD),
    ]
    answer = _serve(client, body)
    pools = _pools_by_rule(_envelope(answer), _BABY_SHELF_RULES)
    assert pools, (
        "no baby-shelf pool served; the window convention is not observable in "
        f"{json.dumps(_envelope(answer), sort_keys=True)[:600]}"
    )
    pool = pools[0]
    assert pool["bound"]["status"] == "known", (
        f"the window is only observable on a known bound: {pool!r}"
    )
    assert pool["window_end"] == _SALE_ISO, (
        f"the window must end on and include the sale date: {pool!r}"
    )
    sale = date.fromisoformat(_SALE_ISO)
    prior_year = sale.year - 1
    clamped_day = min(sale.day, calendar.monthrange(prior_year, sale.month)[1])
    window_start = date(prior_year, sale.month, clamped_day) + timedelta(days=1)
    assert pool["window_start"] == window_start.isoformat(), (
        f"the window must start one day after the clamped prior-year date: {pool!r}"
    )
    assert (sale - window_start).days + 1 == 365, (
        f"the fixture window must span the 365 calendar days ending on the "
        f"sale date: {pool!r}"
    )
    _NOT_EXPRESSIBLE.append(
        "trailing_window: a dated day-365/day-366 sale is not expressible on "
        "base: _sold_trailing (engine/capital_structure/capacity.py:2260-2269) "
        "reads only the aggregate baby_shelf_sold_trailing resolution, no "
        "dated sale rows"
    )


def test_a1_boundary_cutoff_equal_to_available_at(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """A cutoff equal to an ``available_at`` instant INCLUDES that event.

    The contract (state_bundle.py:1124-1129) keeps events with
    ``available_at <= cutoff`` — inclusive at the instant.  Both sides are
    served through the evaluate route: the inclusive cutoff composes over the
    event; one second earlier the event is absent (a different state identity,
    or the typed refusal an empty then-known view produces).
    """
    boundary = _earliest_bound(built, ISSUER_ONE)
    #: One second earlier, in the same UTC ``…Z`` form the contract's
    #: ``_timestamp`` law requires (a naive instant is refused:
    #: issuer_state_contracts.py:497).  ``_shift`` keeps the event-instant form.
    earlier = _shift(boundary, seconds=-1)

    def _serve_then_known(cutoff: str) -> Any:
        _publish_bundle(
            served, built, _fixture_entries(cutoff), as_of=cutoff
        )
        body = _scenario_body(
            view="counterfactual",
            as_of=cutoff,
            horizon_start=cutoff[:10],
            horizon_end=HORIZON_END,
        )
        response = client.post(
            EVALUATE_PATH,
            json=body,
            params={"mode": "then_known", "cutoff": cutoff},
        )
        checked = _checked(response)
        _collect(response, checked)
        return response

    inclusive = _serve_then_known(boundary)
    exclusive = _serve_then_known(earlier)
    assert inclusive.status_code != exclusive.status_code or (
        inclusive.json()["view"]["state_id"] != exclusive.json()["view"]["state_id"]
    ), (
        "the cutoff boundary moved nothing: inclusive "
        f"{inclusive.status_code}/{inclusive.json()['view']['state_id']} vs "
        f"one-second-earlier {exclusive.status_code}/"
        f"{exclusive.json()['view']['state_id']}"
    )
    if inclusive.status_code == 200:
        assert inclusive.json()["view"]["as_of"] == boundary, (
            f"the inclusive cutoff must echo as the state cutoff: "
            f"{inclusive.json()['view']!r}"
        )
    if inclusive.status_code == 200 and exclusive.status_code == 200:
        inclusive_routes = {
            str(route["route_id"])
            for route in _envelope(inclusive.json()).get("routes") or ()
        }
        exclusive_routes = {
            str(route["route_id"])
            for route in _envelope(exclusive.json()).get("routes") or ()
        }
        assert exclusive_routes <= inclusive_routes, (
            "one second earlier served a route the inclusive cutoff lacks: "
            f"{sorted(exclusive_routes - inclusive_routes)}"
        )


# ---------------------------------------------------------------------------
# §3.5 — unknowns stay unknown
# ---------------------------------------------------------------------------


def _quantity_records(value: Any) -> list[dict[str, Any]]:
    """Every served Quantity-shaped record under a response body."""
    found: list[dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if "unit" in node and "status" in node:
                found.append(node)
            for item in node.values():
                _walk(item)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(value)
    return found


def test_a1_unknown_route_limit_gives_floor_and_open_ceiling(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """An unknown limit is an open ceiling: named, value-less, never 0/∞.

    With the baby-shelf float and trailing sales deliberately unresolved, any
    unknown bound must be named by the envelope (its unknown-constraints law)
    and must carry no value, while the known side of the answer survives: a
    known route limit keeps its evidence and applicability (the floor).
    """
    answer = _serve(client, _scenario_body())
    quantities = _quantity_records(answer["result"])
    assert quantities, "no quantity records served"
    for quantity in quantities:
        if quantity.get("status") != "known":
            assert quantity.get("value") is None, (
                f"a non-known quantity carries a value: {quantity!r}"
            )

    envelope = _envelope(answer)
    aggregate = envelope["aggregate_bound"]
    if aggregate.get("status") == "unknown":
        assert envelope.get("unknown_constraints"), (
            "an unknown aggregate must name what is unknown: "
            f"{json.dumps(envelope, sort_keys=True)[:800]}"
        )

    routes = envelope.get("routes") or ()
    assert routes, "no served routes"
    for route in routes:
        if route["limit"].get("status") == "known":
            assert route.get("evidence"), f"known limit without evidence: {route!r}"
            assert route.get("applicability"), (
                f"known limit without applicability: {route!r}"
            )


def test_a1_unknown_share_count_never_zero_or_unlimited(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """An unknown share count stays unknown, never 0 or unlimited.

    The served record that carries the instruments' as-converted claims is
    ``result.supply_envelope.as_converted_claims``: on the base fixture it reads
    the known 1,000,000-share count, and under the mutation — the outstanding
    term admitted as ``unknown`` (issuer_state_contracts.py:2520-2527) — the
    same record must go unknown with no value.  The scenario share totals are
    the no-action baseline (zero new shares) and are never allowed to smuggle
    the unknown in as a 0 or an unlimited answer either.
    """
    baseline = client.post(EVALUATE_PATH, json=_scenario_body())
    known = _checked(baseline, status=200)
    _collect(baseline, known)
    _publish_bundle(
        served, built, _with_unknown_outstanding(_fixture_entries(built.bundle["as_of"])),
        as_of=built.bundle["as_of"],
    )
    response = client.post(EVALUATE_PATH, json=_scenario_body())
    if response.status_code != 200:
        checked = _checked(response)
        _collect(response, checked)
        pytest.fail(
            "unknown instruments outstanding did not compose; the served "
            f"refusal is {response.status_code} {json.dumps(checked)[:600]}"
        )
    answer = _checked(response, status=200)
    _collect(response, answer)
    known_claims = known["result"]["supply_envelope"]["as_converted_claims"]
    assert known_claims["status"] == "known", (
        f"the base claims record must carry the fixture count: {known_claims!r}"
    )
    assert Decimal(known_claims["value"]) == Decimal("1000000"), known_claims
    claims = answer["result"]["supply_envelope"]["as_converted_claims"]
    assert claims["status"] == "unknown", (
        f"an unknown outstanding count must serve an unknown claims record, "
        f"not {claims!r}"
    )
    assert claims["value"] is None, (
        f"an unknown claims record carries no value: {claims!r}"
    )
    low = answer["result"]["scenario_new_shares_low"]
    high = answer["result"]["scenario_new_shares_high"]
    assert low["status"] == high["status"], (
        f"the two share totals carry one status: {low!r} vs {high!r}"
    )
    if low["status"] != "known":
        assert low["value"] is None and high["value"] is None, (
            f"an unknown share total carries a value: {low!r} / {high!r}"
        )
        assert low.get("note"), f"an unknown share total must say why: {low!r}"
    else:
        assert Decimal(low["value"]) >= 0 and Decimal(high["value"]) >= 0


def test_a1_missing_input_family_returns_typed_409_with_components(
    client: Any, served: Any, built: Any, with_inputs: Any
) -> None:
    """A missing family is the typed 409 with its components, never a guess."""
    _publish_bundle(
        served,
        built,
        _with_unavailable_commitments(_fixture_entries(built.bundle["as_of"])),
        as_of=built.bundle["as_of"],
    )
    response = client.post(EVALUATE_PATH, json=_scenario_body())
    checked = _checked(response, status=409)
    _collect(response, checked)
    assert response.status_code == 409
    assert checked["detail"] == {
        "code": "scenario_inputs_unavailable",
        "components": {
            "commitments": {
                "support": "unavailable",
                "reason_codes": ["commitment_rows_absent"],
            },
        },
        "available": ["instruments", "share_basis", "financials", "rules"],
    }
    assert "result" not in json.dumps(response.json())


# ---------------------------------------------------------------------------
# §3.6 — no forbidden output (A48)
# ---------------------------------------------------------------------------


def _violations(body: Any) -> list[str]:
    """The A48 violations of one response body: keys and string values.

    A KEY violates when the contract's exact-name pattern matches it or when it
    CONTAINS a forbidden stem — ``probability_of_recovery`` is as much a
    forbidden output under A48 as a bare ``probability`` — except the
    contract's own authority keys, which are only denials while they hold the
    literal ``False``.
    """
    found: list[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                name = str(key)
                denial = name in _AUTHORITY_DENIAL_KEYS and item is False
                stem = None if denial else _VALUE_PATTERN.search(name)
                if FORBIDDEN_PROPERTY_PATTERN.match(name):
                    found.append(f"key {path}.{name} (contract pattern)")
                elif stem:
                    found.append(f"key {path}.{name} (stem {stem.group(0)!r})")
                _walk(item, f"{path}.{name}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")
        elif isinstance(node, str):
            matched = _VALUE_PATTERN.search(node)
            if matched:
                found.append(f"value {path}={node!r} (stem {matched.group(0)!r})")

    _walk(body, "$")
    return found


def test_a1_vocabulary_walker_catches_planted_positive() -> None:
    """The walker flags a planted key and a planted value, and passes clean."""
    planted = {
        "honest": "facts only",
        "probability_of_recovery": "0.7",
        "note": "this is a rank 1 candidate",
    }
    violations = _violations(planted)
    assert any("probability_of_recovery" in item for item in violations), violations
    assert any("rank 1 candidate" in item for item in violations), violations
    assert _violations({"honest": "facts only", "rows": [1, 2]}) == []


def test_a1_zz_no_forbidden_vocabulary_in_any_served_body() -> None:
    """Every body this file produced: no forbidden key, no forbidden value.

    Defined (and run) last: the collection must hold at least one body per
    earlier served test, and none of them may name a probability, likelihood,
    score, rank, rating, recommendation, sizing or entry.
    """
    assert _BODIES_BY_TEST, "no served body was collected"
    missing = [
        name
        for name in _SERVED_TESTS
        if not any(key == name or key.startswith(f"{name}[")
                   for key in _BODIES_BY_TEST)
    ]
    assert not missing, f"no body collected for: {missing}"
    if _NOT_EXPRESSIBLE:
        print(  # noqa: T201 - surface the recorded gaps to the runner
            "a1 not-expressible-on-base cases:\n  " + "\n  ".join(_NOT_EXPRESSIBLE)
        )
    offenders: list[str] = []
    for test_name, bodies in sorted(_BODIES_BY_TEST.items()):
        for index, entry in enumerate(bodies):
            for violation in _violations(entry["body"]):
                offenders.append(f"{test_name}#{index}: {violation}")
    assert not offenders, "forbidden vocabulary in served bodies:\n" + "\n".join(
        offenders
    )
