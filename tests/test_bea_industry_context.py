"""Contract and refusal witnesses for non-published BEA industry input context.

Synthetic rows imitate the reviewed Data Lab *shape*, not official BEA facts.
There is deliberately no collector, disk fixture, network or live dataset write.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
import json
import unittest

from engine.market_ontology.bea_industry_context import (
    BEAContextRefused,
    LINEAGE_SHA256,
    adapt_eight_year_input_history,
    adapt_industry_commodity_input,
)

_KEYS = (
    "canada", "china", "europe", "japan", "mexico",
    "rest_of_asia_and_pacific", "rest_of_world",
)


def synthetic_row(
    year=2017, industry="3341", commodity="3344", *,
    use=801, world=212, regions=None
):
    regions = regions or dict(zip(_KEYS, (10, 59, 30, 5, 2, 103, 2)))
    diff = world - sum(regions.values())
    reasons = []
    if world <= 0:
        reasons.append("WORLD_IMPORT_NONPOSITIVE")
    elif world < 50:
        reasons.append("RESEARCH_DENOMINATOR_BELOW_50M_FLOOR")
    if any(x < 0 for x in regions.values()):
        reasons.append("SOURCE_NEGATIVE_REGION_ADJUSTMENT")
    if any(x > world for x in regions.values()):
        reasons.append("REGION_EXCEEDS_WORLD_DENOMINATOR")
    if world > 0 and abs(diff) > min(3, world * .05):
        reasons.append("PUBLISHER_ROUNDING_MATERIAL_TO_DENOMINATOR")
    row = {
        "schema": "mastermind.bea_industry_commodity_input_research_row/v1",
        "accounting_year": year,
        "industry_code_exact": industry,
        "commodity_code_exact": commodity,
        "industry_name": "Synthetic computer manufacturing" if industry != "5241X" else "Synthetic insurance",
        "commodity_name": "Synthetic electronic parts",
        "code_namespace": "BEA_APP157_MAY2026_EXACT",
        "source_kind": "industry_commodity_input",
        "source_units": "million USD",
        "source_lineage_sha256": LINEAGE_SHA256,
        "source_lineage_file": "source_lineage.json",
        "source_lineage_accounting_year": year,
        "publication_date": "2026-05-21",
        "publication_precision": "DAY",
        "publication_timestamp": None,
        "publication_timestamp_null_reason": "PUBLISHER_DAY_PRECISION_ONLY",
        "research_source_capture_completed_at": "2026-10-09T07:27:58.721565+00:00",
        "capture_clock_semantics": "LATEST_COMPLETION_OF_NINE_BOUND_SOURCE_CAPTURES",
        "period_end": f"{year}-12-31",
        "period_end_is_availability": False,
        "original_historical_available_at": None,
        "historical_availability_null_reason": "HISTORICAL_AVAILABILITY_UNVERIFIED",
        "native_ingested_at": None,
        "native_known_at": None,
        "native_revision_seq": None,
        "canonical_industry_id": None,
        "canonical_security_id": None,
        "canonical_identity_null_reason": "CANONICAL_IDENTITY_NOT_ADOPTED",
        "native_fields_null_reason": "NATIVE_SOURCE_NOT_ADOPTED",
        "legacy_industry_mapping_state": "UNRESOLVED_5241X_VS_5241XX" if industry == "5241X" else "NOT_APPLIED",
        "dataos_native_admitted": False,
        "historical_pit_eligible": False,
        "named_company_relationship": False,
        "may_publish": False,
        "may_rank": False,
        "may_train": False,
        "may_trade": False,
        "total_use_million_USD": use,
        "world_import_million_USD": world,
        "source_rounding_difference_million_USD": diff,
        "research_ratio_null_reasons_json": json.dumps(reasons),
        "research_ratio_null_reason": reasons[0] if reasons else None,
    }
    for name in _KEYS:
        row[f"{name}_import_million_USD"] = regions[name]
        row[f"{name}_fraction_of_world_import"] = (
            None if reasons else str((Decimal(regions[name]) / Decimal(world)).quantize(
                Decimal("0.0000001"), rounding=ROUND_HALF_EVEN
            ))
        )
    return row


def adapt(row, *, industry="3341", commodity="3344", **kwargs):
    return adapt_industry_commodity_input(
        row, industry_code=industry, commodity_code=commodity, **kwargs
    )


class BEAIndustryContextTests(unittest.TestCase):
    def test_signed_amounts_are_not_falsely_zeroed_or_weighted(self):
        result = adapt(synthetic_row())
        self.assertEqual(result["total_use_million_USD"], 801)
        self.assertEqual(result["world_import_million_USD"], 212)
        self.assertEqual(result["source_rounding_difference_million_USD"], 1)
        self.assertEqual(result["regional_import_million_USD"]["china"], 59)
        self.assertEqual(result["regional_origin_fraction_of_world"]["china"], "0.2783019")
        self.assertEqual(result["source"]["edition_precision"], "DAY")
        self.assertIsNone(result["source"]["original_historical_known_at"])
        self.assertEqual(result["period_end_not_known_at"], "2017-12-31")
        self.assertFalse(result["named_supplier_customer_evidence"])
        self.assertIsNone(result["graph_edge"])
        self.assertFalse(result["publishable"])
        self.assertFalse(result["rank_size_or_trade_authority"])

    def test_realistic_negative_source_adjustment_survives(self):
        amounts = dict(zip(_KEYS, (-8, 0, -60, 0, 0, -1, -1)))
        result = adapt(synthetic_row(year=2020, use=-2, world=-69, regions=amounts))
        self.assertEqual(result["total_use_million_USD"], -2)
        self.assertEqual(result["world_import_million_USD"], -69)
        self.assertEqual(result["source_rounding_difference_million_USD"], 1)
        self.assertIsNone(result["regional_origin_fraction_of_world"])
        self.assertIn("SOURCE_NEGATIVE_REGION_ADJUSTMENT", result["ratio_null_reasons"])
        self.assertIn("WORLD_IMPORT_NONPOSITIVE", result["ratio_null_reasons"])

    def test_tiny_denominator_fraction_is_null(self):
        amounts = dict(zip(_KEYS, (0, 10, 0, 0, 0, 0, 9)))
        result = adapt(synthetic_row(year=2024, use=642, world=19, regions=amounts))
        self.assertEqual(result["ratio_null_reasons"], ["RESEARCH_DENOMINATOR_BELOW_50M_FLOOR"])
        self.assertIsNone(result["regional_origin_fraction_of_world"])
        self.assertEqual(result["regional_import_million_USD"]["china"], 10)

    def test_historical_or_current_asof_refuses_all_instants(self):
        for asof in ("2020-01-01T00:00:00+00:00", "2026-10-11T12:00:00+00:00"):
            with self.subTest(asof=asof), self.assertRaisesRegex(BEAContextRefused, "admitted source clock"):
                adapt(synthetic_row(), as_of=asof)

    def test_no_public_predictive_or_training_purpose(self):
        for purpose in ("public_display", "rank", "trade", "train", "forecast", "named_supplier_edge"):
            with self.subTest(purpose=purpose), self.assertRaises(BEAContextRefused):
                adapt(synthetic_row(), purpose=purpose)

    def test_any_rights_or_graph_promotion_fails_closed(self):
        for key in ("dataos_native_admitted", "historical_pit_eligible",
                    "named_company_relationship", "may_publish", "may_rank",
                    "may_train", "may_trade"):
            with self.subTest(key=key):
                row = synthetic_row()
                row[key] = True
                with self.assertRaises(BEAContextRefused):
                    adapt(row)

    def test_source_digest_and_exact_code_guards(self):
        for field, replacement in (
            ("source_lineage_sha256", "0" * 64),
            ("source_units", "thousand USD"),
            ("source_lineage_accounting_year", 2024),
            ("capture_clock_semantics", "PERIOD_END_KNOWN_AT"),
            ("canonical_identity_null_reason", "AUTO_TICKER_LINKED"),
            ("schema", "unqualified_source_row"),
            ("code_namespace", "NAICS"),
            ("source_kind", "named_supplier"),
            ("industry_code_exact", "AAPL"),
            ("source_lineage_file", "../../invented.json"),
        ):
            row = synthetic_row()
            row[field] = replacement
            with self.subTest(field=field), self.assertRaises(BEAContextRefused):
                adapt(row)
        with self.assertRaises(BEAContextRefused):
            adapt(synthetic_row(), industry="AAPL")

    def test_unresolved_legacy_mapping_cannot_be_asserted_equivalent(self):
        row = synthetic_row(industry="5241X")
        self.assertEqual(
            adapt(row, industry="5241X")["using_industry"]["legacy_mapping"],
            "UNRESOLVED_5241X_VS_5241XX",
        )
        row["legacy_industry_mapping_state"] = "SAME_AS_5241XX"
        with self.assertRaises(BEAContextRefused):
            adapt(row, industry="5241X")

    def test_publisher_date_is_not_first_available_and_no_invented_utc(self):
        for field, value in (
            ("publication_date", "2017-01-01"),
            ("publication_precision", "TIMESTAMP"),
            ("publication_timestamp", "2026-05-21T00:00:00+00:00"),
            ("period_end_is_availability", True),
            ("original_historical_available_at", "2017-01-01T00:00:00+00:00"),
            ("native_known_at", "2026-05-21T00:00:00+00:00"),
            ("research_source_capture_completed_at", "2026-10-09T07:27:58"),
        ):
            row = synthetic_row()
            row[field] = value
            with self.subTest(field=field), self.assertRaises(BEAContextRefused):
                adapt(row)

    def test_source_zero_distinct_from_missing(self):
        row = synthetic_row()
        row["mexico_import_million_USD"] = None
        with self.assertRaises(BEAContextRefused):
            adapt(row)
        row = synthetic_row()
        row["mexico_import_million_USD"] = False
        with self.assertRaises(BEAContextRefused):
            adapt(row)

    def test_lost_rounding_or_invented_ratio_is_refused(self):
        row = synthetic_row()
        row["source_rounding_difference_million_USD"] = 0
        with self.assertRaises(BEAContextRefused):
            adapt(row)
        row = synthetic_row()
        row["china_fraction_of_world_import"] = "0.9900000"
        with self.assertRaises(BEAContextRefused):
            adapt(row)

    def test_ineligible_reasons_and_fractions_are_not_suppressed(self):
        row = synthetic_row(world=19, regions=dict(zip(_KEYS, (0, 10, 0, 0, 0, 0, 9))))
        row["research_ratio_null_reasons_json"] = "[]"
        with self.assertRaises(BEAContextRefused):
            adapt(row)
        row = synthetic_row(world=19, regions=dict(zip(_KEYS, (0, 10, 0, 0, 0, 0, 9))))
        row["research_ratio_null_reasons_json"] = '[{"unexpected":true}]'
        with self.assertRaises(BEAContextRefused):
            adapt(row)
        row = synthetic_row(world=19, regions=dict(zip(_KEYS, (0, 10, 0, 0, 0, 0, 9))))
        row["china_fraction_of_world_import"] = "0.5263158"
        with self.assertRaises(BEAContextRefused):
            adapt(row)

    def test_full_history_requires_distinct_ordered_eight_years(self):
        rows = [synthetic_row(year=year) for year in range(2017, 2025)]
        report = adapt_eight_year_input_history(
            rows, industry_code="3341", commodity_code="3344"
        )
        self.assertEqual(len(report["observations"]), 8)
        self.assertFalse(report["public_or_predictive_use"])
        self.assertTrue(report["no_named_company_relationships"])
        for modified in (rows[:-1], list(reversed(rows)), rows[:7] + rows[6:7]):
            with self.assertRaises(BEAContextRefused):
                adapt_eight_year_input_history(
                    modified, industry_code="3341", commodity_code="3344"
                )


if __name__ == "__main__":
    unittest.main()
