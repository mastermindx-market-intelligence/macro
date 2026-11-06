"""Synthetic semantics only; no market/predictive performance claim."""
import copy
import unittest

from engine.multi_asset_context import compose_context, convert_currency, qualify_observation

AS_OF = "2026-11-05T15:00:00Z"


def observation(ticker="SPY", ret=-0.04, **changes):
    out = dict(observation_id="obs:" + ticker, instrument_id=ticker,
               revision_id="rev1", source_id="fixture", evidence_family_id="equity_price",
               asset_class="equity", market="US", currency="USD", return_basis="total_return",
               period_start="2026-11-04T20:00:00Z", period_end="2026-11-05T14:30:00Z",
               available_at="2026-11-05T14:31:00Z", received_at="2026-11-05T14:32:00Z",
               valid_until="2026-11-05T16:00:00Z", return_value=ret, evidence_kind="measured_return")
    out.update(changes)
    return out


def context(rows=None):
    return compose_context(rows if rows is not None else [observation(), observation("EEM", -0.01)],
                           as_of=AS_OF, benchmark_instrument_id="SPY", base_currency="USD")


class ObservationTests(unittest.TestCase):
    def check_bad(self, key, value, reason):
        result = qualify_observation(observation(**{key: value}), as_of=AS_OF)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn(reason, result["reasons"])

    def test_valid(self):
        self.assertEqual(qualify_observation(observation(), as_of=AS_OF)["status"], "QUALIFIED")

    def test_zero_is_valid(self):
        self.assertEqual(qualify_observation(observation(ret=0), as_of=AS_OF)["observation"]["return_value"], 0)

    def test_total_loss_is_valid(self):
        self.assertEqual(qualify_observation(observation(ret=-1), as_of=AS_OF)["status"], "QUALIFIED")

    def test_numeric_guards(self):
        for value in [True, False, float("nan"), float("inf"), -float("inf"), "1", None, {}, 10**500]:
            with self.subTest(value=type(value).__name__):
                self.check_bad("return_value", value, "invalid_return_value")

    def test_return_floor(self):
        self.check_bad("return_value", -1.01, "return_below_total_loss")

    def test_identity_fields(self):
        for key in ["observation_id", "instrument_id", "revision_id", "source_id", "evidence_family_id", "asset_class", "market"]:
            with self.subTest(key=key):
                self.check_bad(key, "", "invalid_" + key)
                self.check_bad(key, {"bad": 1}, "invalid_" + key)

    def test_missing_identity(self):
        row = observation(); del row["source_id"]
        self.assertIn("invalid_source_id", qualify_observation(row, as_of=AS_OF)["reasons"])

    def test_currency(self):
        for value in ["usd", "US", "USDD", None, ["USD"]]:
            self.check_bad("currency", value, "invalid_currency")

    def test_basis(self):
        self.check_bad("return_basis", "yield", "unsupported_return_basis")

    def test_pressure_is_not_return(self):
        self.check_bad("evidence_kind", "estimated_pressure", "not_measured_return")

    def test_flow_is_not_return(self):
        self.check_bad("evidence_kind", "reported_fund_flow", "not_measured_return")

    def test_naive_and_date_clocks(self):
        for key in ["period_start", "period_end", "available_at", "received_at", "valid_until"]:
            for value in ["2026-11-04", "2026-11-04T14:00:00", None, False]:
                with self.subTest(key=key, value=value):
                    self.check_bad(key, value, "invalid_" + key)

    def test_equivalent_offsets(self):
        row = observation(period_start="2026-11-04T15:00:00-05:00")
        self.assertEqual(qualify_observation(row, as_of=AS_OF)["observation"]["period_start"], "2026-11-04T20:00:00Z")

    def test_bad_asof_raises(self):
        with self.assertRaises(ValueError):
            qualify_observation(observation(), as_of="2026-11-05")

    def test_period_order(self):
        self.check_bad("period_start", "2026-11-05T14:30:00Z", "invalid_period")

    def test_end_after_available(self):
        self.check_bad("period_end", "2026-11-05T14:31:01Z", "available_before_period_end")

    def test_receipt_before_availability(self):
        self.check_bad("received_at", "2026-11-05T14:30:59Z", "received_before_available")

    def test_future_available(self):
        self.check_bad("available_at", "2026-11-05T15:00:01Z", "not_yet_available")

    def test_future_receipt(self):
        self.check_bad("received_at", "2026-11-05T15:00:01Z", "not_yet_received")

    def test_expiry_equality(self):
        self.check_bad("valid_until", AS_OF, "expired")

    def test_invalid_validity(self):
        self.check_bad("valid_until", "2026-11-05T14:31:59Z", "invalid_validity")

    def test_malformed_row(self):
        self.assertEqual(qualify_observation([], as_of=AS_OF)["reasons"], ["observation_not_mapping"])

    def test_authority_escalation(self):
        self.check_bad("authority", {"can_trade": True}, "authority_escalation")

    def test_malformed_evidence_families(self):
        self.check_bad("evidence_families", {"bad": 1}, "invalid_evidence_families")

    def test_malformed_source_lineage(self):
        self.check_bad("source_lineage", [None], "invalid_source_lineage")

    def test_no_input_mutation(self):
        row = observation(); before = copy.deepcopy(row)
        qualify_observation(row, as_of=AS_OF)
        self.assertEqual(row, before)


class CompositionTests(unittest.TestCase):
    def test_down_less_is_not_gain(self):
        row = context()["comparisons"][0]
        self.assertAlmostEqual(row["relative_return"], 0.99 / 0.96 - 1)
        self.assertEqual(row["candidate_return"], -0.01)
        self.assertEqual(row["classification"], "RELATIVE_RESILIENCE_ONLY")

    def test_gain_and_outperformance(self):
        self.assertEqual(context([observation(), observation("EEM", 0.01)])["comparisons"][0]["classification"], "POSITIVE_AND_OUTPERFORMING")

    def test_positive_underperformer(self):
        self.assertEqual(context([observation(ret=0.03), observation("EEM", 0.01)])["comparisons"][0]["classification"], "UNDERPERFORMING")

    def test_equal_returns(self):
        self.assertEqual(context([observation(ret=0.01), observation("EEM", 0.01)])["comparisons"][0]["classification"], "IN_LINE")

    def test_no_benchmark(self):
        result = context([observation("EEM")])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["comparisons"], [])
        self.assertIn("benchmark_unavailable", result["reasons"])

    def test_only_benchmark(self):
        self.assertEqual(context([observation()])["status"], "UNAVAILABLE")

    def test_no_rows(self):
        self.assertEqual(context([])["coverage"]["observations"], 0)

    def test_mismatched_base_currency(self):
        result = context([observation(), observation("EEM", currency="HKD")])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("base_currency_mismatch", result["exclusions"][0]["reasons"])

    def test_period_mismatch(self):
        result = context([observation(), observation("EEM", period_start="2026-11-04T19:00:00Z")])
        self.assertIn("period_mismatch", result["comparisons"][0]["reasons"])
        self.assertIsNone(result["comparisons"][0]["relative_return"])

    def test_basis_mismatch(self):
        self.assertIn("return_basis_mismatch", context([observation(), observation("EEM", return_basis="price_return")])["comparisons"][0]["reasons"])

    def test_zero_benchmark_wealth(self):
        result = context([observation(ret=-1), observation("EEM", -0.5)])
        self.assertIn("benchmark_zero_wealth", result["comparisons"][0]["reasons"])
        self.assertIsNone(result["comparisons"][0]["relative_return"])

    def test_duplicate_instrument_all_excluded(self):
        result = context([observation(), observation(observation_id="other", revision_id="correction"), observation("EEM")])
        self.assertEqual(result["coverage"]["excluded"], 2)
        self.assertEqual(result["status"], "UNAVAILABLE")

    def test_duplicate_observation_all_excluded(self):
        result = context([observation(), observation("EEM", observation_id="obs:SPY")])
        self.assertEqual(result["coverage"]["excluded"], 2)

    def test_invalid_duplicate_does_not_select_valid_row(self):
        result = context([observation(), observation("EEM"), observation("EEM", ret=float("nan"))])
        self.assertEqual(result["coverage"]["excluded"], 2)

    def test_partial(self):
        result = context([observation(), observation("EEM"), observation("GLD", ret=None)])
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["coverage"], dict(observations=3, qualified=2, excluded=1, comparable=1))

    def test_deterministic_order(self):
        rows = [observation(), observation("EEM"), observation("GLD", ret=None)]
        self.assertEqual(context(rows), context(rows[::-1]))

    def test_normalized_clock_digest(self):
        a = [observation(), observation("EEM")]
        b = copy.deepcopy(a); b[1]["period_start"] = "2026-11-04T15:00:00-05:00"
        self.assertEqual(context(a), context(b))

    def test_revision_changes_digest(self):
        a = context(); b = context([observation(), observation("EEM", revision_id="v2")])
        self.assertNotEqual(a["input_digest"], b["input_digest"])

    def test_excluded_evidence_changes_digest(self):
        a = context([observation(), observation("EEM", currency="HKD", revision_id="v1")])
        b = context([observation(), observation("EEM", currency="HKD", revision_id="v2")])
        self.assertNotEqual(a["input_digest"], b["input_digest"])

    def test_source_clock_changes_digest(self):
        a = context(); b = context([observation(), observation("EEM", received_at="2026-11-05T14:33:00Z")])
        self.assertNotEqual(a["input_digest"], b["input_digest"])

    def test_authority_always_false(self):
        for rows in [[], [observation()], [observation(), observation("EEM")]]:
            result = context(rows)
            self.assertTrue(result["display_only"] and result["no_predictive_claim"])
            self.assertTrue(all(v is False for v in result["authority"].values()))

    def test_not_performance_ranked(self):
        result = context([observation(), observation("GLD", 0.9), observation("EEM", -0.2)])
        self.assertEqual([r["instrument_id"] for r in result["comparisons"]], ["EEM", "GLD"])

    def test_top_level_validation(self):
        for value in ["bad", b"bad", {}, None, 1]:
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                compose_context(value, as_of=AS_OF, benchmark_instrument_id="SPY", base_currency="USD")

    def test_malformed_row_safe(self):
        result = context([observation(), [], {"instrument_id": []}])
        self.assertEqual(result["coverage"]["excluded"], 2)

    def test_no_input_mutation(self):
        rows = [observation(), observation("EEM")]; before = copy.deepcopy(rows)
        context(rows); self.assertEqual(rows, before)

    def test_overflow_does_not_become_signal(self):
        result = context([observation(ret=-0.99999999999999), observation("EEM", ret=1e308)])
        self.assertEqual(result["comparisons"][0]["status"], "UNAVAILABLE")


class CurrencyTests(unittest.TestCase):
    def pair(self, **changes):
        a = observation("LOCAL", 0.08, currency="HKD")
        b = observation("HKDUSD", -0.06, asset_class="fx", return_basis="price_return",
                        fx_base_currency="USD", fx_quote_currency="HKD", fx_convention="base_per_local")
        b.update(changes)
        return a, b

    def convert(self, **changes):
        return convert_currency(*self.pair(**changes), as_of=AS_OF, base_currency="USD")

    def test_compounding(self):
        result = self.convert()
        self.assertEqual(result["status"], "QUALIFIED")
        self.assertAlmostEqual(result["observation"]["return_value"], 0.0152)

    def test_retains_ancestry(self):
        result = self.convert()
        self.assertEqual(len(result["ancestry"]), 2)
        self.assertIn("source_lineage", result["observation"])
        self.assertEqual(result["observation"]["return_basis"], "total_return")

    def test_direction(self):
        self.assertIn("fx_direction_mismatch", self.convert(fx_convention="local_per_base")["reasons"])

    def test_wrong_fx_base(self):
        self.assertIn("fx_direction_mismatch", self.convert(fx_base_currency="EUR")["reasons"])

    def test_wrong_fx_quote(self):
        self.assertIn("fx_direction_mismatch", self.convert(fx_quote_currency="JPY")["reasons"])

    def test_stale_fx(self):
        self.assertIn("fx_expired", self.convert(valid_until=AS_OF)["reasons"])

    def test_window_mismatch(self):
        self.assertIn("fx_period_mismatch", self.convert(period_start="2026-11-04T19:00:00Z")["reasons"])

    def test_no_double_conversion(self):
        converted = self.convert()["observation"]
        self.assertIn("already_converted_or_base_currency", convert_currency(converted, self.pair()[1], as_of=AS_OF, base_currency="USD")["reasons"])

    def test_validity_intersection(self):
        result = self.convert(valid_until="2026-11-05T15:10:00Z")
        self.assertEqual(result["observation"]["valid_until"], "2026-11-05T15:10:00Z")

    def test_latest_known_clock(self):
        result = self.convert(available_at="2026-11-05T14:40:00Z", received_at="2026-11-05T14:41:00Z")
        self.assertEqual(result["observation"]["received_at"], "2026-11-05T14:41:00Z")

    def test_wrong_instrument(self):
        self.assertIn("invalid_fx_instrument_or_basis", self.convert(asset_class="equity")["reasons"])

    def test_no_mutation(self):
        pair = self.pair(); before = copy.deepcopy(pair)
        convert_currency(*pair, as_of=AS_OF, base_currency="USD")
        self.assertEqual(pair, before)

    def test_overflow(self):
        a, b = self.pair(return_value=1e308); a["return_value"] = 1e308
        self.assertIn("converted_return_overflow", convert_currency(a, b, as_of=AS_OF, base_currency="USD")["reasons"])


if __name__ == "__main__":
    unittest.main()


class UnicodeEvidenceTests(unittest.TestCase):
    def test_oversized_malformed_unicode_is_bounded_not_a_composer_crash(self):
        row = observation("EEM", rights_ref="x" * 4096 + chr(0xD800))
        result = compose_context([observation(), row], as_of=AS_OF,
                                 benchmark_instrument_id="SPY", base_currency="USD")
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["input_digest"]), 64)
        self.assertEqual(result["observations"][0]["rights_ref"]["invalid"], "oversized_string")

    def test_excluded_row_malformed_unicode_does_not_hide_exclusion(self):
        row = observation("EEM", currency="invalid", rights_ref="x" * 4096 + chr(0xD800))
        result = compose_context([observation(), row], as_of=AS_OF,
                                 benchmark_instrument_id="SPY", base_currency="USD")
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("invalid_currency", result["exclusions"][0]["reasons"])
