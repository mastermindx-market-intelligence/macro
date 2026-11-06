"""Synthetic daily-snapshot semantics; no predictive or portfolio test."""
import copy
import hashlib
import json
import unittest

from engine.multi_asset_daily import UNIVERSE, compose_daily_context, semantic_context, validate_daily_context

START, END, EXPECTED = "2026-10-28", "2026-11-04", "2026-11-04"
CAPTURE = "2026-11-05T15:00:00Z"


def sources():
    return [dict(instrument_id=t, source_digest="a" * 64, currency="USD", listing_market="US",
                 return_basis="total_return", prices={START: 100.0, END: 96.0 if t == "SPY" else 99.0},
                 last_source_session=END) for t, *_ in UNIVERSE]


def compose(rows=None, **kwargs):
    options = dict(captured_at=CAPTURE, start_session=START, end_session=END,
                   expected_session=EXPECTED, horizon_sessions=5)
    options.update(kwargs)
    return compose_daily_context(sources() if rows is None else rows, **options)


def rehash(result):
    result["context_digest"] = hashlib.sha256(json.dumps(semantic_context(result), sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    return result


class DailyTests(unittest.TestCase):
    def test_observed_returns(self):
        result = compose()
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["coverage"]["observed"], len(UNIVERSE))
        row = next(r for r in result["rows"] if r["instrument_id"] == "EEM")
        self.assertAlmostEqual(row["absolute_return"], -0.01)
        self.assertEqual(row["classification"], "RELATIVE_RESILIENCE_ONLY")

    def test_no_invented_clock(self):
        result = compose()
        self.assertIsNone(result["provider_available_at"])
        self.assertFalse(result["historical_original_availability_proven"])
        self.assertEqual(result["alignment_basis"], "US_CASH_SESSION_LABEL_NOT_QUOTE_TIMESTAMP")
        self.assertNotIn("period_end", result["rows"][0])

    def test_not_cash(self):
        result = compose(); row = next(r for r in result["rows"] if r["instrument_id"] == "SHY")
        self.assertIn("not cash", row["label_en"])
        self.assertIn("cash_is_separate_from_short_duration_funds", result["limitations"])

    def test_oil_is_wrapper(self):
        row = next(r for r in compose()["rows"] if r["instrument_id"] == "USO")
        self.assertIn("not spot oil", row["label_en"])

    def test_missing_end_not_shifted(self):
        rows = sources(); oil = next(r for r in rows if r["instrument_id"] == "USO")
        oil["prices"] = {START: 100, "2026-11-03": 105}; oil["last_source_session"] = "2026-11-03"
        result = compose(rows); row = next(r for r in result["rows"] if r["instrument_id"] == "USO")
        self.assertIn("end_session_missing", row["reasons"])
        self.assertIsNone(row["absolute_return"])
        self.assertEqual(result["status"], "PARTIAL")

    def test_missing_start_not_filled(self):
        rows = sources(); rows[1]["prices"].pop(START)
        self.assertIn("start_session_missing", next(r for r in compose(rows)["rows"] if r["instrument_id"] == "EFA")["reasons"])

    def test_stale_is_visible(self):
        result = compose(expected_session="2026-11-05")
        self.assertEqual(result["status"], "STALE")
        self.assertIn("older_than_expected_session", result["reasons"])
        self.assertEqual(result["window"]["end_session"], END)

    def test_missing_benchmark(self):
        result = compose([s for s in sources() if s["instrument_id"] != "SPY"])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIsNone(result["benchmark_return"])
        self.assertEqual(result["coverage"]["comparable"], 0)

    def test_duplicate_source_refused(self):
        rows = sources(); rows.append(copy.deepcopy(rows[0]))
        self.assertEqual(next(r for r in compose(rows)["rows"] if r["instrument_id"] == "SPY")["reasons"], ["duplicate_source"])

    def test_wrong_currency(self):
        rows = sources(); rows[1]["currency"] = "HKD"
        self.assertIn("source_basis_or_currency_mismatch", next(r for r in compose(rows)["rows"] if r["instrument_id"] == "EFA")["reasons"])

    def test_wrong_basis(self):
        rows = sources(); rows[1]["return_basis"] = "price_return"
        self.assertIn("source_basis_or_currency_mismatch", next(r for r in compose(rows)["rows"] if r["instrument_id"] == "EFA")["reasons"])

    def test_foreign_listing_not_comparable(self):
        rows = sources(); rows[1]["listing_market"] = "HK"
        self.assertIn("listing_session_mismatch", next(r for r in compose(rows)["rows"] if r["instrument_id"] == "EFA")["reasons"])

    def test_bad_prices(self):
        for value in [True, "100", float("nan"), float("inf"), -1]:
            rows = sources(); rows[1]["prices"][END] = value
            with self.subTest(value=type(value).__name__):
                self.assertIn("invalid_endpoint_price", next(r for r in compose(rows)["rows"] if r["instrument_id"] == "EFA")["reasons"])

    def test_zero_start(self):
        rows = sources(); rows[1]["prices"][START] = 0
        self.assertEqual(compose(rows)["status"], "PARTIAL")

    def test_zero_benchmark_wealth(self):
        rows = sources(); rows[0]["prices"][END] = 0
        result = compose(rows)
        self.assertEqual(result["coverage"]["comparable"], 0)
        self.assertEqual(result["status"], "UNAVAILABLE")

    def test_digest_required(self):
        rows = sources(); rows[1]["source_digest"] = ""
        self.assertIn("source_digest_missing", next(r for r in compose(rows)["rows"] if r["instrument_id"] == "EFA")["reasons"])

    def test_capture_only_keeps_semantic_identity(self):
        self.assertEqual(compose()["context_digest"], compose(captured_at="2026-11-05T15:01:00Z")["context_digest"])

    def test_correction_changes_identity(self):
        rows = sources(); rows[1]["source_digest"] = "b" * 64
        self.assertNotEqual(compose()["context_digest"], compose(rows)["context_digest"])

    def test_order_deterministic(self):
        self.assertEqual(compose(sources()), compose(sources()[::-1]))

    def test_future_window_refused(self):
        with self.assertRaises(ValueError): compose(expected_session="2026-11-03")

    def test_bad_horizon(self):
        for value in [True, 0, -1, 253, 5.0]:
            with self.subTest(value=value), self.assertRaises(ValueError): compose(horizon_sessions=value)

    def test_no_input_mutation(self):
        rows = sources(); before = copy.deepcopy(rows); compose(rows)
        self.assertEqual(rows, before)

    def test_malformed_sources(self):
        result = compose([[], {"instrument_id": []}])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["coverage"]["invalid_sources"], 2)

    def test_no_raw_prices_published(self):
        self.assertNotIn('"prices"', json.dumps(compose()))

    def test_validate_copy(self):
        result = compose(); checked = validate_daily_context(result)
        checked["rows"][0]["status"] = "CHANGED"
        self.assertNotEqual(checked, result)

    def test_digest_tamper(self):
        result = compose(); result["benchmark_return"] = 100
        with self.assertRaises(ValueError): validate_daily_context(result)

    def test_authority_tamper(self):
        result = compose(); result["authority"]["can_trade"] = True
        with self.assertRaises(ValueError): validate_daily_context(result)

    def test_wrong_schema(self):
        result = compose(); result["schema"] = "other"
        with self.assertRaises(ValueError): validate_daily_context(result)

    def test_false_authority_not_numeric_zero(self):
        result = compose(); result["authority"]["can_trade"] = 0
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_extra_prediction_field_refused(self):
        result = compose(); result["crash_probability"] = 0.8
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_forged_comparison_with_valid_digest_refused(self):
        result = compose(); result["rows"][0]["relative_return"] = 10
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_forged_coverage_refused(self):
        result = compose(); result["coverage"]["comparable"] = 99
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_missing_row_refused(self):
        result = compose(); result["rows"].pop()
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_duplicate_row_refused(self):
        result = compose(); result["rows"][0] = result["rows"][1]
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_bad_metadata_refused(self):
        result = compose(); result["rows"][0]["listing_market"] = "HK"
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_false_freshness_refused(self):
        result = compose(expected_session="2026-11-05"); result["status"] = "AVAILABLE"
        with self.assertRaises(ValueError): validate_daily_context(rehash(result))

    def test_valid_degraded_payloads(self):
        cases = [compose([]), compose(sources()[1:]), compose(expected_session="2026-11-05")]
        rows = sources(); rows[1]["prices"][END] = float("nan"); cases.append(compose(rows))
        for case in cases:
            self.assertEqual(validate_daily_context(case), case)


if __name__ == "__main__": unittest.main()
