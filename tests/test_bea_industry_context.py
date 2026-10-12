"""Contract and refusal witnesses for non-published BEA industry input context.

Synthetic rows imitate the reviewed Data Lab *shape*, not official BEA facts.
There is deliberately no collector, disk fixture, network or live dataset write.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from engine.market_ontology.bea_industry_context import (
    BEAContextRefused,
    LINEAGE_SHA256,
    adapt_eight_year_input_history,
    adapt_industry_commodity_input,
    adapt_workspace_bea_history,
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
        self.assertEqual(result["measurement_class"], "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION")
        self.assertTrue(result["source_methodology"]["industry_input_allocation_is_estimate"])
        self.assertFalse(result["source_methodology"]["industry_specific_import_transaction_observed"])
        self.assertFalse(result["source_methodology"]["named_supplier_customer_pair_observed"])
        self.assertEqual(result["source_methodology"]["source_url"], "https://www.bea.gov/help/faq/453")
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
        self.assertEqual(report["measurement_class"], "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION")
        self.assertFalse(report["industry_specific_transactions_observed"])
        self.assertTrue(report["no_named_company_relationships"])
        for modified in (rows[:-1], list(reversed(rows)), rows[:7] + rows[6:7]):
            with self.assertRaises(BEAContextRefused):
                adapt_eight_year_input_history(
                    modified, industry_code="3341", commodity_code="3344"
                )

    def test_ninth_row_refused_before_unbounded_generator_continues(self):
        observed = []

        def surplus():
            for year in range(2017, 2026):
                observed.append(year)
                yield synthetic_row(year=min(year, 2024))
            raise AssertionError("reader consumed an unauthorized tenth row")

        with self.assertRaisesRegex(BEAContextRefused, "more than eight"):
            adapt_eight_year_input_history(
                surplus(), industry_code="3341", commodity_code="3344"
            )
        self.assertEqual(observed, list(range(2017, 2026)))


def _synthetic_workspace_response():
    """DataWorkspace.read envelope *shape*, never a real filesystem observation."""
    ref = "free_source_research:data_workspace_views_20261011/industry_3341.jsonl"
    version = "statv1:" + "a" * 64
    query = {
        "ref": ref,
        "file_version": version,
        "columns": None,
        "time_column": None,
        "start": None,
        "end": None,
        "equals": {"commodity_code_exact": "3344"},
        "offset": 0,
        "limit": 9,
    }
    digest = hashlib.sha256(json.dumps(
        query, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return {
        "schema_version": "mastermind.data_workspace/v1",
        "action": "read",
        "source_access": "read_only",
        "production_qualification": "NOT_ESTABLISHED_BY_THIS_ADAPTER",
        "observed_at": "2026-10-11T16:00:00+00:00",
        "source": {
            "ref": ref,
            "root_alias": "free_source_research",
            "relative_path": "data_workspace_views_20261011/industry_3341.jsonl",
            "evidence_kind": "research_capture",
            "registry_admission": "NOT_INFERRED_FROM_FILE_PRESENCE",
            "file_bytes": 2_000_000,
            "file_version": version,
            "file_version_basis": "device_inode_size_mtime_ctime_not_content_hash",
            "content_sha256": None,
        },
        "query": query,
        "query_receipt_sha256": digest,
        "result": {
            "rows": [synthetic_row(year=y) for y in range(2017, 2025)],
            "row_positions": [139 * i for i in range(8)],
            "scanned_rows": 1112,
            "next_offset": None,
            "scan_complete": True,
            "missingness_notes": {},
        },
        "temporal_caution": (
            "Filtering stored rows does not reconstruct point-in-time availability."
        ),
    }


class BEADataWorkspaceResearchConsumerTests(unittest.TestCase):
    def test_complete_existing_dataos_read_envelope_projects_private_history(self):
        result = adapt_workspace_bea_history(
            _synthetic_workspace_response(),
            industry_code="3341",
            commodity_code="3344",
        )
        self.assertEqual(len(result["observations"]), 8)
        self.assertEqual([row["accounting_year"] for row in result["observations"]],
                         list(range(2017, 2025)))
        self.assertEqual(result["observations"][0]["world_import_million_USD"], 212)
        self.assertEqual(result["measurement_class"], "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION")
        self.assertFalse(result["source_adopted"])
        self.assertFalse(result["public_or_predictive_use"])
        self.assertTrue(result["no_named_company_relationships"])
        proof = result["reader_provenance"]
        self.assertEqual(proof["root_alias"], "free_source_research")
        self.assertEqual(proof["source_row_count"], 8)
        self.assertEqual(proof["canonical_reader"],
                         "lib.dataos.web_workspace.DataWorkspace.read")
        self.assertFalse(proof["original_file_content_sha256_verified"])
        self.assertFalse(proof["native_dataset_admission"])
        self.assertFalse(proof["public_or_historical_pit_serving"])

    def test_real_incumbent_data_workspace_reads_synthetic_eight_year_file(self):
        """Real Data OS reader and query receipt; fake data in a disposable folder."""
        from lib.dataos.web_workspace import DataWorkspace, RootBinding

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "industry_3341.jsonl"
            raw_rows = [synthetic_row(year) for year in range(2017, 2025)]
            source.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in raw_rows),
                encoding="utf-8",
            )
            workspace = DataWorkspace(
                (RootBinding(alias="free_source_research",
                             path=root, evidence_kind="research_capture"),),
                Path(__file__).resolve().parents[1] / "config" / "dataset_registry.yml",
                source_revision="synthetic-data-workspace-integration",
            )
            ref = "free_source_research:industry_3341.jsonl"
            description = workspace.describe(ref)
            version = description["source"]["file_version"]
            response = workspace.read(
                ref, equals={"commodity_code_exact": "3344"},
                offset=0, limit=9, expected_version=version,
            )
            self.assertEqual(len(response["result"]["rows"]), 8)
            self.assertTrue(response["result"]["scan_complete"])
            self.assertIsNone(response["result"]["next_offset"])
            self.assertEqual(response["query"]["file_version"], version)
            report = adapt_workspace_bea_history(
                response, industry_code="3341", commodity_code="3344",
            )
            self.assertEqual(len(report["observations"]), 8)
            self.assertFalse(report["reader_provenance"]["native_dataset_admission"])
            self.assertFalse(report["reader_provenance"][
                "original_file_content_sha256_verified"])
            self.assertEqual(report["observations"][-1]["accounting_year"], 2024)

    def test_signed_negative_allocation_survives_real_reader_envelope_shape(self):
        response = _synthetic_workspace_response()
        neg = dict(zip(_KEYS, (-8, 0, -60, 0, 0, -1, -1)))
        response["result"]["rows"][3] = synthetic_row(
            year=2020, use=-2, world=-69, regions=neg,
        )
        report = adapt_workspace_bea_history(
            response, industry_code="3341", commodity_code="3344",
        )
        row = report["observations"][3]
        self.assertEqual(row["total_use_million_USD"], -2)
        self.assertEqual(row["world_import_million_USD"], -69)
        self.assertIsNone(row["regional_origin_fraction_of_world"])
        self.assertIn("SOURCE_NEGATIVE_REGION_ADJUSTMENT", row["ratio_null_reasons"])
        self.assertFalse(row["named_supplier_customer_evidence"])

    def test_never_promotes_reader_evidence_to_public_or_historical_asof(self):
        for choice in (
            {"purpose": "public_display"},
            {"purpose": "train"},
            {"purpose": "trade"},
            {"as_of": "2020-01-01T00:00:00+00:00"},
        ):
            with self.subTest(choice=choice), self.assertRaises(BEAContextRefused):
                adapt_workspace_bea_history(
                    _synthetic_workspace_response(), industry_code="3341",
                    commodity_code="3344", **choice,
                )

    def test_bad_reader_origin_receipt_or_claimed_source_authentication_refused(self):
        cases = (
            ("source", "evidence_kind", "unqualified_snapshot"),
            ("source", "registry_admission", "ADMITTED"),
            ("source", "content_sha256", "b" * 64),
            ("source", "root_alias", "production_qualified"),
            ("source", "relative_path", "industry_XXXX.jsonl"),
            ("source", "file_bytes", False),
            ("query", "limit", 8),
            ("query", "offset", 10),
            ("query", "equals", {"industry_code_exact": "3341"}),
            ("query", "columns", ["accounting_year"]),
        )
        for section, field, value in cases:
            response = _synthetic_workspace_response()
            response[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(BEAContextRefused):
                adapt_workspace_bea_history(
                    response, industry_code="3341", commodity_code="3344",
                )
        for key, bad in (
            ("action", "describe_file"),
            ("source_access", "write"),
            ("production_qualification", "ADMITTED"),
            ("query_receipt_sha256", "0" * 64),
            ("observed_at", "2026-10-11"),
            ("observed_at", "2026-10-09T00:00:00+00:00"),
        ):
            response = _synthetic_workspace_response()
            response[key] = bad
            with self.subTest(field=key, value=bad), self.assertRaises(BEAContextRefused):
                adapt_workspace_bea_history(
                    response, industry_code="3341", commodity_code="3344",
                )

    def test_partial_duplicate_or_surplus_rows_fail_closed(self):
        variations = (
            ("scan_complete", False),
            ("next_offset", 1112),
            ("row_positions", [0] * 8),
            ("scanned_rows", 7),
            ("rows", [synthetic_row(y) for y in range(2017, 2024)]),
            ("rows", [synthetic_row(y) for y in range(2017, 2025)] + [synthetic_row(2024)]),
            ("rows", [synthetic_row(y) for y in range(2017, 2024)] + [synthetic_row(2023)]),
        )
        for field, value in variations:
            response = _synthetic_workspace_response()
            response["result"][field] = value
            with self.subTest(field=field), self.assertRaises(BEAContextRefused):
                adapt_workspace_bea_history(
                    response, industry_code="3341", commodity_code="3344",
                )


if __name__ == "__main__":
    unittest.main()
