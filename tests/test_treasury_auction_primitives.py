"""Independent arithmetic goldens: all values are synthetic, not market data."""
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, getcontext

from engine.treasury_auction_primitives import (
    CashComponent, CashKind, InputRole, MagnitudeEvent, MetricAxis, Observation,
    SecurityClass, calculate_dv01, importance_percentile, settlement_cash,
)

T = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
S = date(2026, 10, 15)
D = Decimal


def obs(value, unit="USD", currency="USD", **overrides):
    fields = dict(value=value, unit=unit, currency=currency, known_at=T - timedelta(minutes=1),
                  as_of=T - timedelta(minutes=2), source_ref="synthetic:golden-v1",
                  input_method="supplied synthetic input; no market observation", role=InputRole.SYNTHETIC)
    fields.update(overrides)
    return Observation(**fields)


def duration(value, frn=False, **kwargs):
    return obs(value, "EFFECTIVE_RATE_DURATION_YEARS" if frn else "MODIFIED_DURATION_YEARS", None, **kwargs)


def dv(value=100_000_000, years=8, cls=SecurityClass.NOTE, **kwargs):
    args = dict(security_class=cls, decision_at=T, market_value=obs(value),
                duration=duration(years), currency="USD", measure_basis="NOMINAL_YIELD_MODIFIED")
    args.update(kwargs)
    return calculate_dv01(**args)


def component(identity, kind, numeric_amount, **overrides):
    fields = dict(component_id=identity, kind=kind, cohort_id="synthetic:S1",
                  settlement_date=S, amount=obs(numeric_amount))
    fields.update(overrides)
    return CashComponent(**fields)


def cash(**kwargs):
    args = dict(cohort_id="synthetic:S1", settlement_date=S, currency="USD", decision_at=T,
                proceeds=[component("issue1", CashKind.PRIVATE_PROCEEDS_EX_SOMA, 120_000_000_000)],
                redemptions=[component("redeem1", CashKind.PRIVATE_MARKETABLE_REDEMPTION, 80_000_000_000)],
                buybacks=[component("buy1", CashKind.FUNDED_BUYBACK_OUTLAY, 5_000_000_000)],
                completeness_certified=True, gross_offered_face=obs(125_000_000_000),
                soma_context=obs(12_000_000_000))
    args.update(kwargs)
    return settlement_cash(**args)


def event(identity, value, ago=1, **kwargs):
    args = dict(event_id=identity, event_at=T - timedelta(days=ago), security_class=SecurityClass.NOTE,
                tenor_cohort="original-10Y", metric_axis=MetricAxis.NOMINAL_DV01,
                measure_basis="NOMINAL_YIELD_MODIFIED", magnitude=obs(value, "USD_PER_BP"))
    args.update(kwargs)
    return MagnitudeEvent(**args)


class DV01Tests(unittest.TestCase):
    def test_independent_fifty_bp_price_approximation_and_scaling(self):
        # $100mm, duration 8, yield +0.005: linear price loss is 4% = $4mm.
        # $4mm / 50 bp = $80,000/bp. $mm/bp = .08. Twice value doubles it.
        result = dv()
        self.assertEqual(result["dv01_usd_per_bp"], D("80000"))
        self.assertEqual(result["dv01_million_usd_per_bp"], D("0.08"))
        self.assertEqual(-50 * result["dv01_usd_per_bp"], D("-4000000"))
        self.assertEqual(dv(200_000_000)["dv01_usd_per_bp"], D("160000"))
        self.assertEqual(result["inputs"]["market_value"]["source_ref"], "synthetic:golden-v1")
        self.assertTrue(result["is_context_only"])

    def test_large_bill_smaller_bond_reversal_and_cmb(self):
        # $100bn Bill at .08 years: $.8mm/bp. $20bn Bond at 18: $36mm/bp.
        self.assertEqual(dv(100_000_000_000, D(".08"), SecurityClass.BILL)["dv01_million_usd_per_bp"], D(".8"))
        self.assertEqual(dv(20_000_000_000, 18, SecurityClass.BOND)["dv01_million_usd_per_bp"], D("36"))
        self.assertEqual(dv(25_000_000_000, D(".05"), SecurityClass.CMB)["dv01_usd_per_bp"], D("125000"))

    def test_tips_real_indexed_value_and_nominal_separation(self):
        # $100mm face with index ratio 1.10 and par market price = $110mm indexed value.
        # Supplied real duration 7 -> $77,000 per REAL-yield bp.
        result = dv(cls=SecurityClass.TIPS, market_value=obs(110_000_000, "INDEXED_USD"),
                    duration=duration(7), measure_basis="REAL_YIELD_MODIFIED")
        self.assertEqual(result["dv01_usd_per_bp"], D("77000"))
        self.assertEqual(result["sensitivity_axis"], "REAL_YIELD")
        self.assertNotEqual(result["sensitivity_axis"], dv()["sensitivity_axis"])
        with self.assertRaises(ValueError):
            dv(cls=SecurityClass.TIPS, measure_basis="REAL_YIELD_MODIFIED")

    def test_frn_requires_effective_duration_and_basis_no_maturity_fallback(self):
        result = dv(cls=SecurityClass.FRN, duration=None, measure_basis=None)
        self.assertEqual(result["status"], "NOT_COMPUTABLE")
        self.assertIsNone(result["dv01_usd_per_bp"])
        with self.assertRaises(ValueError):
            dv(cls=SecurityClass.FRN, years=2, measure_basis="LEGAL_MATURITY")
        result = dv(cls=SecurityClass.FRN, duration=duration(D(".02"), frn=True),
                    measure_basis="supplier_reset_rate_parallel_bump.v1")
        self.assertEqual(result["dv01_usd_per_bp"], D("200"))
        self.assertEqual(result["sensitivity_axis"], "FRN_EFFECTIVE_RATE")

    def test_missing_zero_and_future_or_result_inputs(self):
        for kwargs in ({"market_value": None}, {"market_value": obs(None)}, {"duration": None},
                       {"market_value": obs(100, known_at=None)}, {"duration": duration(8, as_of=None)},
                       {"market_value": obs(100, known_at=T + timedelta(seconds=1))},
                       {"market_value": obs(100, as_of=T + timedelta(seconds=1), known_at=T + timedelta(seconds=2))},
                       {"duration": duration(8, role=InputRole.RESULT)}):
            with self.subTest(kwargs=kwargs):
                result = dv(**kwargs)
                self.assertEqual(result["status"], "NOT_COMPUTABLE")
                self.assertIsNone(result["dv01_usd_per_bp"])
                self.assertTrue(result["null_reason"])
        self.assertEqual(dv(value=0)["dv01_usd_per_bp"], 0)
        self.assertEqual(dv(years=0)["dv01_usd_per_bp"], 0)

    def test_invalid_numbers_clock_units_and_basis_raise(self):
        for value in (True, False, "100", float("nan"), float("inf"), float("-inf"), D("NaN"), D("Infinity"), -1):
            for field in ("market_value", "duration"):
                with self.subTest(value=value, field=field), self.assertRaises(ValueError):
                    dv(**{field: obs(value) if field == "market_value" else duration(value)})
        for kwargs in ({"market_value": obs(1, known_at=S)}, {"market_value": obs(1, known_at=T.replace(tzinfo=None))},
                       {"market_value": obs(1, as_of=T, known_at=T-timedelta(seconds=1))},
                       {"currency": "EUR"}, {"market_value": obs(1, "MILLION_USD")},
                       {"measure_basis": "REAL_YIELD_MODIFIED"}, {"market_value": obs(1, source_ref="")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                dv(**kwargs)

    def test_decimal_calculation_not_rounded_by_callers_context(self):
        prior = getcontext().prec
        try:
            getcontext().prec = 6
            self.assertEqual(dv(value=D("123456789012345678901234567890.12"), years=1)["dv01_usd_per_bp"],
                             D("12345678901234567890123456.789012"))
        finally:
            getcontext().prec = prior


class SettlementTests(unittest.TestCase):
    def test_cash_not_face_soma_not_subtracted_again_buyback_signed(self):
        # Cash $120bn - private maturity $80bn - funded buyback $5bn = $35bn.
        # Gross face $125bn and SOMA $12bn do not enter that equation.
        result = cash()
        self.assertEqual(result["net_private_cash_usd"], D("35000000000"))
        self.assertEqual(result["components"][2]["signed_cash_usd"], D("-5000000000"))
        self.assertEqual(cash(soma_context=obs(20_000_000_000))["net_private_cash_usd"], D("35000000000"))
        self.assertIsNone(result["reserve_pressure"])
        self.assertIn("not TGA change", result["limits"])

    def test_unknown_vs_observed_zero_and_completeness(self):
        for kwargs in ({"redemptions": None}, {"buybacks": []}, {"completeness_certified": False},
                       {"buybacks": [component("buy1", CashKind.FUNDED_BUYBACK_OUTLAY, None)]},
                       {"proceeds": [component("issue1", CashKind.PRIVATE_PROCEEDS_EX_SOMA, 1, amount=None)]}):
            with self.subTest(kwargs=kwargs):
                result = cash(**kwargs)
                self.assertEqual(result["status"], "NOT_COMPUTABLE")
                self.assertIsNone(result["net_private_cash_usd"])
        zero_buyback = [component("observed_zero", CashKind.FUNDED_BUYBACK_OUTLAY, 0)]
        self.assertEqual(cash(buybacks=zero_buyback)["net_private_cash_usd"], D("40000000000"))
        # Offsets may exceed proceeds: a negative net is valid accounting.
        self.assertEqual(cash(proceeds=[component("small", CashKind.PRIVATE_PROCEEDS_EX_SOMA, 0)])["net_private_cash_usd"],
                         D("-85000000000"))

    def test_mismatched_cohort_currency_settlement_kind_and_duplicates(self):
        base = component("issue1", CashKind.PRIVATE_PROCEEDS_EX_SOMA, 1)
        for bad in (replace(base, cohort_id="other"), replace(base, settlement_date=date(2026,10,16)),
                    replace(base, amount=obs(1, currency="EUR")),
                    replace(base, kind=CashKind.FUNDED_BUYBACK_OUTLAY), replace(base, amount=obs(-1)),
                    replace(base, amount=obs(True)), replace(base, amount=obs(float("nan"))),
                    replace(base, amount=obs(float("inf")))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cash(proceeds=[bad])
        with self.assertRaises(ValueError):
            cash(proceeds=[base, base])

    def test_future_cash_unknown_and_optional_context_does_not_gate(self):
        future = component("late", CashKind.PRIVATE_PROCEEDS_EX_SOMA, 100, amount=obs(100, known_at=T+timedelta(seconds=1)))
        self.assertEqual(cash(proceeds=[future])["status"], "NOT_COMPUTABLE")
        self.assertEqual(cash(gross_offered_face=None, soma_context=None)["net_private_cash_usd"], D("35000000000"))

    def test_exact_cancellation_beyond_decimal_default_precision(self):
        # Independent expected arithmetic: (10^40+1) - 10^40 - zero = 1.
        result = cash(proceeds=[component("big", CashKind.PRIVATE_PROCEEDS_EX_SOMA, 10**40+1)],
                      redemptions=[component("bigredeem", CashKind.PRIVATE_MARKETABLE_REDEMPTION, 10**40)],
                      buybacks=[component("zero", CashKind.FUNDED_BUYBACK_OUTLAY, 0)])
        self.assertEqual(result["net_private_cash_usd"], D(1))


class ImportanceTests(unittest.TestCase):
    def test_exact_ties_current_and_future_excluded_and_known_past_only(self):
        # Historical [1..10] + four 11s + six 12s: less=10,ties=4,n=20 => 60%.
        history = [event(f"h{i}", value, ago=i+1) for i,value in enumerate(list(range(1,11))+[11]*4+[12]*6)]
        current = event("now", 11, ago=-1)
        excluded = [current, event("future", 0, ago=-2), event("at-decision", 0, ago=0),
                    event("late-receipt", 0, magnitude=obs(0,"USD_PER_BP", known_at=T+timedelta(seconds=1))),
                    event("other-tenor", 0, tenor_cohort="original-2Y"),
                    event("other-class", 0, security_class=SecurityClass.BOND),
                    event("real", 0, security_class=SecurityClass.TIPS, metric_axis=MetricAxis.REAL_DV01, measure_basis="REAL_YIELD_MODIFIED"),
                    event("other-basis", 0, measure_basis="different-duration-method"),
                    event("result", 0, magnitude=obs(0,"USD_PER_BP", role=InputRole.RESULT))]
        result = importance_percentile(current=current, history=history+excluded, decision_at=T)
        self.assertEqual(result["percentile"], D(60))
        self.assertEqual(result["drivers"]["n"], 20)
        self.assertEqual(result["drivers"]["strictly_less"], 10)
        self.assertEqual(result["drivers"]["ties"], 4)
        self.assertEqual(result["importance_label"], "ROUTINE")
        self.assertTrue(result["is_context_only"])
        self.assertEqual(len(result["baseline_inputs"]), 20)

    def test_insufficient_or_missing_remains_not_scored(self):
        history = [event(f"h{i}", i, ago=i+1) for i in range(19)]
        for current in (event("now", 100, ago=-1), event("now", None, ago=-1),
                        event("now", 0, ago=-1, magnitude=None)):
            result = importance_percentile(current=current, history=history, decision_at=T)
            self.assertEqual(result["status"], "NOT_SCORED")
            self.assertIsNone(result["percentile"])
            self.assertIsNone(result["importance_label"])

    def test_product_thresholds_and_baseline_precedes_current_event(self):
        history = [event(f"h{i}", i, ago=i+1) for i in range(20)]
        self.assertEqual(importance_percentile(current=event("now",100,ago=-1), history=history, decision_at=T)["importance_label"], "HIGH")
        # Current historical event 3 days ago must exclude more recent baseline events.
        result = importance_percentile(current=event("historic",100,ago=3), history=history, decision_at=T)
        self.assertEqual(result["drivers"]["n"], 17)
        self.assertEqual(result["status"], "NOT_SCORED")
        for value, expected in ((D("14.5"),"WATCH"), (D("17.5"),"HIGH")):
            self.assertEqual(importance_percentile(current=event("now",value,ago=-1), history=history, decision_at=T)["importance_label"], expected)

    def test_duplicate_history_negative_magnitude_and_incompatible_axis_raise(self):
        for history in ([event("same",1),event("same",2)], [event("bad",-1)],
                        [event("bad",1,metric_axis=MetricAxis.REAL_DV01)]):
            with self.subTest(history=history), self.assertRaises(ValueError):
                importance_percentile(current=event("now",1,ago=-1), history=history, decision_at=T)


if __name__ == "__main__":
    unittest.main()
