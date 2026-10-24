"""Controlled source fixtures only; no provider, fixing or product admission."""
from copy import deepcopy
import pytest

from engine.options_nbbo_cohort import canonical_occ_symbol
from engine.options_plan_expiry import prepare_expiry_payoff, prepare_plan_draft_expiry

KNOWN = "2026-10-23T21:00:00Z"


def leg(strike=100, side="buy", entry=3, root="SPY", expiry="2026-10-30"):
    mills = strike * 1000
    c = dict(root=root, expiration=expiry, right="call", strike=str(strike),
             strike_millis=mills, occ_symbol=canonical_occ_symbol(
                 root=root, expiration=expiry, right="call", strike_millis=mills))
    ticker = "O:" + root + expiry.replace("-", "")[2:] + "C" + f"{mills:08d}"
    fields = dict(ticker=ticker, underlying_ticker=root, contract_type="call",
                  expiration_date=expiry, strike_price=strike, exercise_style="american",
                  shares_per_contract=100)
    return dict(contract=c, assumptions=dict(side=side, quantity=1,
        entry=dict(kind="user_assumption", premium_per_unit=entry, currency="USD")),
        reference_observation=dict(schema="options_reference_capability_observation/v1",
            state="response_observed", origin="https://api.massive.com",
            path="/v3/reference/options/contracts/" + ticker,
            capability=dict(http_status=200, verdict="entitled"), contract=fields,
            field_presence={k: True for k in fields}, completed_at="2026-10-23T20:01:00Z",
            payload_sha256="a" * 64),
        settlement_context=dict(contract=deepcopy(c), economic_expiry_at=expiry + "T20:00:00Z",
            available_at="2026-10-23T20:02:00Z", fixing_basis="official_close",
            fixing_ref="https://fixtures.invalid/controlled-not-live#sha256=" + "b" * 64))


def evaluate(legs, spots=(90, 100, 105, 110, 120), **kw):
    return prepare_expiry_payoff(legs, spots, known_by=kw.get("known_by", KNOWN))


def codes(result):
    assert result["curve"] is None and result["status"] == "UNPRICED"
    return {r["code"] for r in result["reasons"]}


def test_authored_long_call_without_quote_iv_or_open_session():
    source = leg(); before = deepcopy(source)
    result = evaluate([source])
    assert result["status"] == "PREPARED_EXPIRY_PAYOFF"
    assert result["curve"] == dict(spots=[90, 100, 105, 110, 120],
        pnl=[-300, -300, 200, 700, 1700], cost=300, max_gain="UNBOUNDED", max_loss=-300,
        breakevens=[103])
    assert result["assumptions"]["current_quote_required"] is False
    assert result["assumptions"]["entry_basis"] == "user_assumption_not_fill"
    assert "r" not in result["assumptions"] and "model_name" not in result["assumptions"]
    assert source == before


@pytest.mark.parametrize("legs,expected,cost,loss,gain", [
    ([leg(100, "buy", 7), leg(110, "sell", 2)], [-500, -500, 0, 500, 500], 500, -500, 500),
    ([leg(100, "sell", 7), leg(110, "buy", 2)], [500, 500, 0, -500, -500], -500, -500, 500),
    ([leg(100, "sell", 3)], [300, 300, -200, -700, -1700], -300, "UNBOUNDED", 300),
])
def test_economic_payoff_cases(legs, expected, cost, loss, gain):
    curve = evaluate(legs)["curve"]
    assert curve["pnl"] == expected
    assert (curve["cost"], curve["max_loss"], curve["max_gain"]) == (cost, loss, gain)


def test_zero_authored_entry_is_valid_and_size_is_contracts():
    source = leg(entry=0); source["assumptions"]["quantity"] = 2
    assert evaluate([source])["curve"]["pnl"] == [0, 0, 1000, 2000, 4000]


@pytest.mark.parametrize("other,code", [
    (leg(root="QQQ"), "MIXED_UNDERLYING"),
    (leg(expiry="2026-11-06"), "MIXED_EXPIRY"),
])
def test_cannot_run_one_spot_across_incompatible_contracts(other, code):
    assert code in codes(evaluate([leg(), other]))


def test_same_date_different_fixing_instant_is_unpriced():
    other = leg(110); other["settlement_context"]["economic_expiry_at"] = "2026-10-30T19:30:00Z"
    assert "INCOMPATIBLE_SETTLEMENT_HORIZON" in codes(evaluate([leg(), other]))


@pytest.mark.parametrize("mutate,code", [
    (lambda x: x["assumptions"].update(entry=None), "ENTRY_ASSUMPTION_MISSING"),
    (lambda x: x["assumptions"]["entry"].update(kind="source_mid"), "ENTRY_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"]["entry"].update(premium_per_unit=float("nan")), "ENTRY_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"]["entry"].update(premium_per_unit=-1), "ENTRY_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"].update(quantity=True), "POSITION_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"].update(quantity=1.5), "POSITION_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"].update(quantity=0), "POSITION_ASSUMPTION_INVALID"),
    (lambda x: x.update(settlement_context=None), "SETTLEMENT_FIXING_UNQUALIFIED"),
    (lambda x: x["settlement_context"].update(fixing_basis="AM_index"), "SETTLEMENT_FIXING_UNQUALIFIED"),
    (lambda x: x["settlement_context"].update(available_at="2026-10-24T00:00:00Z"), "SETTLEMENT_FIXING_UNQUALIFIED"),
    (lambda x: x["settlement_context"].update(economic_expiry_at="2026-10-30T20:00:00"), "SETTLEMENT_FIXING_UNQUALIFIED"),
    (lambda x: x["settlement_context"].update(economic_expiry_at="2026-10-31T20:00:00Z"), "SETTLEMENT_FIXING_UNQUALIFIED"),
    (lambda x: x["settlement_context"].update(fixing_ref="https://fixtures.invalid/unbound"), "SETTLEMENT_FIXING_UNQUALIFIED"),
    (lambda x: x["contract"].update(occ_symbol="SPY   261030C00101000"), "IDENTITY_INVALID"),
    (lambda x: x["reference_observation"].update(completed_at="2026-10-23T22:00:00Z"), "TERMS_UNQUALIFIED"),
    (lambda x: x["reference_observation"]["capability"].update(http_status=403), "TERMS_UNQUALIFIED"),
])
def test_missing_conflicting_and_unknown_stays_unpriced(mutate, code):
    source = leg(); mutate(source)
    assert code in codes(evaluate([source]))


@pytest.mark.parametrize("field,value", [
    ("shares_per_contract", 150), ("shares_per_contract", None),
    ("additional_underlyings", [{"type": "currency", "amount": 855, "underlying": "USD"}]),
    ("exercise_style", "european"), ("cfi", "OCASPN"),
])
def test_adjusted_or_unknown_economics_never_uses_vanilla_intrinsic(field, value):
    source = leg(); obs = source["reference_observation"]
    obs["contract"][field] = value; obs["field_presence"][field] = True
    assert "TERMS_UNQUALIFIED" in codes(evaluate([source]))


def test_unknown_multiplier_is_not_replaced_with_default():
    source = leg(); obs = source["reference_observation"]
    del obs["contract"]["shares_per_contract"]; del obs["field_presence"]["shares_per_contract"]
    assert "TERMS_UNQUALIFIED" in codes(evaluate([source]))


def test_unsupported_root_and_partial_leg_never_emit_partial_curve():
    assert "TERMS_UNQUALIFIED" in codes(evaluate([leg(root="AAPL")]))
    missing = leg(110); missing["assumptions"]["entry"] = None
    assert "ENTRY_ASSUMPTION_MISSING" in codes(evaluate([leg(), missing]))


@pytest.mark.parametrize("spots", [[], [float("inf")], [-1], [True], [1] * 1002])
def test_invalid_spot_domain_is_unpriced(spots):
    assert "SPOTS_INVALID" in codes(evaluate([leg()], spots))


def test_equivalent_offset_horizons_compare_as_instants():
    other = leg(110); other["settlement_context"]["economic_expiry_at"] = "2026-10-30T16:00:00-04:00"
    assert evaluate([leg(), other])["status"] == "PREPARED_EXPIRY_PAYOFF"


def test_malformed_capability_and_huge_input_return_typed_unpriced():
    source = leg(); source["reference_observation"]["capability"] = ["not-a-receipt"]
    assert "TERMS_UNQUALIFIED" in codes(evaluate([source]))
    source = leg(); source["assumptions"]["entry"]["premium_per_unit"] = 10**1000
    assert "ENTRY_ASSUMPTION_INVALID" in codes(evaluate([source]))


def draft():
    return dict(schema="options_plan_draft.v1", legs=[dict(
        snapshot=dict(pinKey="synthetic-exact-pin", session="2026-10-23", asofRaw=None,
            sourceStale=True, schema=None, identity=dict(root="SPY", exp="2026-10-30",
                right="C", strike=100, adjustedRootHint=False, terms=dict(multiplier=None,
                    deliverable=None, settlement=None, exercise_style=None)), row=dict(mid=99)),
        assumptions=deepcopy(leg()["assumptions"]))],
        research=dict(thesis="fixture", invalidation="fixture", horizon="research horizon"))


def test_actual_plan_assumption_shape_joins_exact_pin_and_preserves_unknown_clock():
    plan = draft(); before = deepcopy(plan)
    out = prepare_plan_draft_expiry(plan, [leg()], [100, 110], known_by=KNOWN)
    assert out["curve"]["pnl"] == [-300, 700]  # row.mid=99 is never the entry.
    assert out["source_pins"][0]["asofRaw"] is None
    assert out["source_pins"][0]["sourceStale"] is True
    assert plan == before


@pytest.mark.parametrize("change,code", [
    (lambda p: p["legs"][0]["snapshot"]["identity"].update(strike=101), "PIN_CONTEXT_IDENTITY_MISMATCH"),
    (lambda p: p["legs"][0]["snapshot"]["identity"]["terms"].update(multiplier=150), "PIN_TERMS_CONFLICT"),
    (lambda p: p["legs"][0]["snapshot"]["identity"].update(adjustedRootHint=True), "PIN_TERMS_CONFLICT"),
])
def test_plan_pin_context_conflicts_cannot_rebind_or_overwrite_source(change, code):
    plan = draft(); change(plan)
    assert code in codes(prepare_plan_draft_expiry(plan, [leg()], [100], known_by=KNOWN))
