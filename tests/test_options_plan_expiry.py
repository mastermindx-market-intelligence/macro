"""Controlled source fixtures only; no provider or product admission."""
from copy import deepcopy
import pytest

from engine.options_nbbo_cohort import canonical_occ_symbol
from engine.options_plan_expiry import prepare_expiry_payoff, prepare_plan_draft_expiry

KNOWN = "2026-10-23T21:00:00Z"
BASIS = dict(kind="hold_to_expiry_intrinsic", expiration="2026-10-30")


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
            payload_sha256="a" * 64))


def evaluate(legs, spots=(90, 100, 105, 110, 120), **kw):
    return prepare_expiry_payoff(legs, spots, known_by=kw.get("known_by", KNOWN),
                                 payoff_basis=kw.get("payoff_basis", BASIS))


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
    assert result["known_by"] == KNOWN
    assert result["contract_expirations"] == ["2026-10-30"]
    assert result["temporal_context"]["relation"] == "EXPIRY_DATE_AFTER_KNOWN_BY_DATE"
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


def test_explicit_hypothetical_model_has_no_fixing_or_settlement_requirement():
    out = evaluate([leg()])
    assert out["status"] == "PREPARED_EXPIRY_PAYOFF"
    assert out["assumptions"]["payoff_basis"] == BASIS
    assert out["assumptions"]["underlying_price"] == "hypothetical_at_expiry"
    assert out["assumptions"]["outcome"] == "conditional_not_realized"
    assert out["assumptions"]["early_exercise"] == "excluded"
    assert out["assumptions"]["assignment"] == "excluded"
    assert "economic_expiry_at" not in out["assumptions"]


@pytest.mark.parametrize("basis", [None, {}, dict(kind="actual_fixing", expiration="2026-10-30"),
    {**BASIS, "economic_expiry_at": "2026-10-30T20:00:00Z"}])
def test_actual_fixing_or_other_model_basis_is_explicitly_unsupported(basis):
    assert "PAYOFF_BASIS_UNSUPPORTED" in codes(evaluate([leg()], payoff_basis=basis))


def test_conditional_model_date_must_equal_contract_expiry():
    assert "PAYOFF_EXPIRY_MISMATCH" in codes(evaluate([leg()], payoff_basis={**BASIS, "expiration": "2026-11-06"}))


def test_legacy_actual_settlement_context_cannot_be_silently_ignored():
    source = leg(); source["settlement_context"] = dict(fixing_basis="official_close")
    assert "CONTEXT_BASIS_UNSUPPORTED" in codes(evaluate([source]))


def test_historical_contract_is_explicitly_after_expiry_not_a_prior_decision():
    basis = dict(kind="hold_to_expiry_intrinsic", expiration="2026-10-15")
    result = evaluate([leg(expiry="2026-10-15")], payoff_basis=basis)
    assert result["known_by"] == KNOWN
    assert result["temporal_context"] == dict(known_by_date_new_york="2026-10-23",
        contract_expiration="2026-10-15", relation="EXPIRY_DATE_BEFORE_KNOWN_BY_DATE",
        historical_first_availability_established=False)


@pytest.mark.parametrize("mutate,code", [
    (lambda x: x["assumptions"].update(entry=None), "ENTRY_ASSUMPTION_MISSING"),
    (lambda x: x["assumptions"]["entry"].update(kind="source_mid"), "ENTRY_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"]["entry"].update(premium_per_unit=float("nan")), "ENTRY_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"]["entry"].update(premium_per_unit=-1), "ENTRY_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"].update(quantity=True), "POSITION_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"].update(quantity=1.5), "POSITION_ASSUMPTION_INVALID"),
    (lambda x: x["assumptions"].update(quantity=0), "POSITION_ASSUMPTION_INVALID"),
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
    out = prepare_plan_draft_expiry(plan, [{k: v for k, v in leg().items() if k != "assumptions"}], [100, 110], known_by=KNOWN, payoff_basis=BASIS)
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
    assert code in codes(prepare_plan_draft_expiry(plan, [{k: v for k, v in leg().items() if k != "assumptions"}], [100], known_by=KNOWN, payoff_basis=BASIS))


def list_reference():
    obs = deepcopy(leg()["reference_observation"])
    obs["contracts"] = [obs.pop("contract"), deepcopy(leg(110)["reference_observation"]["contract"])]
    obs["path"] = "/v3/reference/options/contracts"
    obs["params"] = dict(underlying_ticker="SPY", expiration_date="2026-10-30", limit=100)
    obs.pop("field_presence")
    return obs


def test_genuine_list_receipt_selects_exact_legs_and_preserves_endpoint_digest_clock():
    obs = list_reference(); before = deepcopy(obs)
    a, b = leg(100, "buy", 7), leg(110, "sell", 2)
    a["reference_observation"] = obs; b["reference_observation"] = obs
    out = evaluate([a, b])
    assert out["curve"]["pnl"] == [-500, -500, 0, 500, 500]
    assert [c["terms"]["series_id"] for c in out["contexts"]] == [row["ticker"] for row in obs["contracts"]]
    assert all(c["terms"]["terms_ref"] == "https://api.massive.com/v3/reference/options/contracts#sha256=" + "a" * 64 for c in out["contexts"])
    assert all(c["terms"]["available_at"] == obs["completed_at"] for c in out["contexts"])
    assert obs == before


@pytest.mark.parametrize("mutate", [
    lambda x: x["contracts"].append(deepcopy(x["contracts"][0])),
    lambda x: x["contracts"].pop(0),
    lambda x: x["contracts"][0].update(strike_price=101),
    lambda x: x["contracts"][0].update(underlying_ticker="QQQ"),
    lambda x: x["params"].update(underlying_ticker="QQQ"),
    lambda x: x["params"].update(expiration_date="2026-11-06"),
    lambda x: x.update(contracts=[]),
    lambda x: x.update(contracts=[None]),
    lambda x: x.update(contracts=x["contracts"] * 51),
])
def test_list_reference_absent_ambiguous_foreign_or_out_of_scope_is_unpriced(mutate):
    source = leg(); source["reference_observation"] = list_reference()
    mutate(source["reference_observation"])
    assert "TERMS_UNQUALIFIED" in codes(evaluate([source]))
