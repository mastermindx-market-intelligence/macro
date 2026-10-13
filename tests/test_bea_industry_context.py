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
from unittest.mock import patch

from engine.market_ontology import bea_industry_context as bea_module
from engine.market_ontology.bea_industry_context import (
    BEAContextRefused,
    LINEAGE_SHA256,
    adapt_eight_year_input_history,
    adapt_industry_commodity_input,
    adapt_workspace_bea_history,
    compose_bea_industry_accounting_change,
    read_private_bea_accounting_brief,
    compare_private_bea_using_industries,
    qualify_private_bea_research_manifest,
    verify_supplied_bea_research_view_bytes,
)

_EXPECTED_SOURCE_RELATIVE = (
    "bea_2024_public_itable_research/"
    "bea_2017_2022_may2026_remaining_six_regions/"
    "data_workspace_views_20261011/industry_3341.jsonl"
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

    def test_forbidden_history_request_never_touches_lazy_rows(self):
        class PoisonRows:
            def __iter__(self):
                raise AssertionError("forbidden request touched caller iterable")

        for forbidden in (
            {"purpose": "public_display"},
            {"purpose": "trade"},
            {"purpose": "train"},
            {"as_of": "2020-01-01T00:00:00+00:00"},
        ):
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(BEAContextRefused):
                    adapt_eight_year_input_history(
                        PoisonRows(), industry_code="3341",
                        commodity_code="3344", **forbidden,
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
    ref = "free_source_research:" + _EXPECTED_SOURCE_RELATIVE
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
            "relative_path": _EXPECTED_SOURCE_RELATIVE,
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

    def test_replayed_lookalike_file_outside_exact_source_subtree_refused(self):
        response = _synthetic_workspace_response()
        fake_relative = "unrelated_research/industry_3341.jsonl"
        fake_ref = "free_source_research:" + fake_relative
        response["source"]["ref"] = fake_ref
        response["source"]["relative_path"] = fake_relative
        response["query"]["ref"] = fake_ref
        response["query_receipt_sha256"] = hashlib.sha256(json.dumps(
            response["query"], sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")).hexdigest()
        with self.assertRaisesRegex(BEAContextRefused, "research file"):
            adapt_workspace_bea_history(
                response, industry_code="3341", commodity_code="3344",
            )

    def test_complete_response_refuses_short_scan_even_with_eight_valid_rows(self):
        response = _synthetic_workspace_response()
        response["result"]["scanned_rows"] = 8
        response["result"]["row_positions"] = list(range(8))
        with self.assertRaisesRegex(BEAContextRefused, "scan incomplete"):
            adapt_workspace_bea_history(
                response, industry_code="3341", commodity_code="3344",
            )

    def test_real_incumbent_data_workspace_reads_synthetic_eight_year_file(self):
        """Real Data OS reader and query receipt; fake data in a disposable folder."""
        from lib.dataos.web_workspace import DataWorkspace, RootBinding

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / _EXPECTED_SOURCE_RELATIVE
            source.parent.mkdir(parents=True)
            raw_rows = []
            for year in range(2017, 2025):
                raw_rows.append(synthetic_row(year))
                raw_rows.extend(synthetic_row(year, commodity=f"A{k:03d}")
                                for k in range(1, 139))
            self.assertEqual(len(raw_rows), 1112)
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
            ref = "free_source_research:" + _EXPECTED_SOURCE_RELATIVE
            description = workspace.describe(ref)
            version = description["source"]["file_version"]
            response = workspace.read(
                ref, equals={"commodity_code_exact": "3344"},
                offset=0, limit=9, expected_version=version,
            )
            self.assertEqual(len(response["result"]["rows"]), 8)
            self.assertEqual(response["result"]["scanned_rows"], 1112)
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


class BEAAccountingChangeBriefTests(unittest.TestCase):
    def test_signed_research_change_and_denominator_nulls_are_not_renamed(self):
        response = _synthetic_workspace_response()
        response["result"]["rows"][6] = synthetic_row(
            year=2023, use=700, world=212,
        )
        tiny_2024 = dict(zip(_KEYS, (0, 10, 0, 0, 0, 0, 9)))
        response["result"]["rows"][7] = synthetic_row(
            year=2024, use=710, world=19, regions=tiny_2024,
        )
        brief = compose_bea_industry_accounting_change(
            response, industry_code="3341", commodity_code="3344",
        )
        self.assertEqual(brief["schema"],
                         "market_ontology.bea_industry_accounting_change_research/v1")
        self.assertEqual(brief["authority"], "PRIVATE_RESEARCH_ONLY")
        self.assertEqual(brief["measurement_class"],
                         "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION")
        self.assertEqual(brief["periods"]["earlier_year"], 2023)
        self.assertEqual(brief["periods"]["latest_year"], 2024)
        self.assertEqual(brief["signed_change_2024_minus_2023_million_USD"][
            "total_use"], 10)
        self.assertEqual(brief["signed_change_2024_minus_2023_million_USD"][
            "world_import"], -193)
        self.assertEqual(brief["signed_change_2024_minus_2023_million_USD"][
            "regions"]["china"], -49)
        self.assertEqual(len(brief["annual_observations"]), 8)
        prior = brief["annual_observations"][-2]
        latest = brief["annual_observations"][-1]
        self.assertIsNotNone(prior["regional_origin_fraction_of_world"])
        self.assertIsNone(latest["regional_origin_fraction_of_world"])
        self.assertEqual(latest["ratio_null_reasons"],
                         ["RESEARCH_DENOMINATOR_BELOW_50M_FLOOR"])
        for flag in ("may_publish", "may_rank", "may_train", "may_trade",
                     "dataos_native_admitted", "named_company_relationship",
                     "historical_pit_eligible",
                     "source_bytes_authenticated_by_this_projection"):
            with self.subTest(flag=flag):
                self.assertIs(brief[flag], False)
        self.assertTrue(brief["estimated_allocation_not_observed_purchase"])
        self.assertTrue(brief["publisher_day_precision_only"])

    def test_preserves_annual_capture_clocks_names_and_accounting_labels(self):
        response = _synthetic_workspace_response()
        rows = response["result"]["rows"]
        rows[0]["research_source_capture_completed_at"] = "2026-10-08T03:01:00+00:00"
        rows[7]["research_source_capture_completed_at"] = "2026-10-10T05:02:00+00:00"
        rows[0]["industry_name"] = "2017 issuer-unmapped industry display label"
        rows[7]["industry_name"] = "2024 issuer-unmapped industry display label"
        rows[0]["commodity_name"] = "2017 source commodity display label"
        rows[7]["commodity_name"] = "2024 source commodity display label"
        report = compose_bea_industry_accounting_change(
            response, industry_code="3341", commodity_code="3344",
        )
        self.assertEqual(report["source_capture_window_utc"], {
            "earliest": "2026-10-08T03:01:00+00:00",
            "latest": "2026-10-10T05:02:00+00:00",
        })
        changes = report["consecutive_year_signed_changes_million_USD"]
        self.assertEqual(changes[0]["earlier_research_capture_at"],
                         "2026-10-08T03:01:00+00:00")
        self.assertEqual(changes[-1]["later_research_capture_at"],
                         "2026-10-10T05:02:00+00:00")
        earlier, latest = report["annual_observations"][0], report["annual_observations"][-1]
        self.assertEqual(earlier["research_capture_at"], "2026-10-08T03:01:00+00:00")
        self.assertEqual(latest["research_capture_at"], "2026-10-10T05:02:00+00:00")
        self.assertEqual(earlier["using_industry"]["name"],
                         "2017 issuer-unmapped industry display label")
        self.assertEqual(latest["using_industry"]["name"],
                         "2024 issuer-unmapped industry display label")
        self.assertEqual(earlier["input_commodity"]["name"],
                         "2017 source commodity display label")
        self.assertEqual(latest["input_commodity"]["name"],
                         "2024 source commodity display label")
        self.assertEqual(earlier["period_end_not_known_at"], "2017-12-31")
        self.assertEqual(latest["period_end_not_known_at"], "2024-12-31")
        self.assertEqual(earlier["publisher_edition_date"], "2026-05-21")
        self.assertEqual(latest["publisher_edition_precision"], "DAY")
        self.assertEqual(earlier["source_rounding_difference_million_USD"], 1)
        self.assertIsNone(earlier["original_historical_known_at"])
        self.assertIsNone(latest["original_historical_known_at"])
        self.assertFalse(report["historical_pit_eligible"])
        self.assertFalse(report["may_publish"])
        self.assertFalse(report["named_company_relationship"])

    def test_seven_signed_annual_changes_cover_full_retrospective_history(self):
        response = _synthetic_workspace_response()
        small = dict(zip(_KEYS, (0, 10, 0, 0, 0, 0, 9)))
        negative = dict(zip(_KEYS, (-8, 0, -60, 0, 0, -1, -1)))
        response["result"]["rows"][0] = synthetic_row(
            year=2017, use=700, world=19, regions=small,
        )
        response["result"]["rows"][3] = synthetic_row(
            year=2020, use=-2, world=-69, regions=negative,
        )
        report = compose_bea_industry_accounting_change(
            response, industry_code="3341", commodity_code="3344",
        )
        annual_changes = report["consecutive_year_signed_changes_million_USD"]
        self.assertEqual(len(annual_changes), 7)
        self.assertEqual(
            [(r["earlier_accounting_year"], r["later_accounting_year"])
             for r in annual_changes],
            [(year, year + 1) for year in range(2017, 2024)],
        )
        self.assertEqual(annual_changes[0]["signed_change_million_USD"]["world_import"], 193)
        self.assertEqual(annual_changes[2]["signed_change_million_USD"]["world_import"], -281)
        self.assertEqual(annual_changes[2]["signed_change_million_USD"]["regions"]["europe"], -90)
        self.assertEqual(annual_changes[3]["signed_change_million_USD"]["world_import"], 281)
        self.assertEqual(annual_changes[-1]["signed_change_million_USD"],
                         report["signed_change_2024_minus_2023_million_USD"])
        for item in annual_changes:
            with self.subTest(year=item["later_accounting_year"]):
                self.assertEqual(item["publisher_edition_date"], "2026-05-21")
                self.assertEqual(item["publisher_edition_precision"], "DAY")
                self.assertIsNone(item["original_historical_known_at"])
                self.assertIs(item["historical_pit_eligible"], False)
                self.assertTrue(item["earlier_research_capture_at"].startswith("2026-"))
                self.assertTrue(item["later_research_capture_at"].startswith("2026-"))
        total = report["signed_change_2024_minus_2017_million_USD"]
        self.assertEqual(total["world_import"], 193)
        self.assertEqual(total["total_use"], 101)
        self.assertEqual(len(report["annual_observations"]), 8)
        self.assertIsNone(report["annual_observations"][0]["regional_origin_fraction_of_world"])
        self.assertIsNone(report["annual_observations"][3]["regional_origin_fraction_of_world"])
        self.assertTrue(report["publisher_day_precision_only"])
        self.assertFalse(report["historical_pit_eligible"])
        self.assertFalse(report["may_train"])
        self.assertFalse(report["may_publish"])

    def test_negative_accounting_changes_survive_brief(self):
        response = _synthetic_workspace_response()
        adjustments = dict(zip(_KEYS, (-8, 0, -60, 0, 0, -1, -1)))
        response["result"]["rows"][-1] = synthetic_row(
            year=2024, use=-2, world=-69, regions=adjustments,
        )
        brief = compose_bea_industry_accounting_change(
            response, industry_code="3341", commodity_code="3344",
        )
        changes = brief["signed_change_2024_minus_2023_million_USD"]
        self.assertEqual(changes["world_import"], -281)
        self.assertEqual(changes["total_use"], -803)
        self.assertEqual(brief["annual_observations"][-1][
            "regional_import_million_USD"]["europe"], -60)
        self.assertIsNone(brief["annual_observations"][-1][
            "regional_origin_fraction_of_world"])
        self.assertIn("SOURCE_NEGATIVE_REGION_ADJUSTMENT",
                      brief["annual_observations"][-1]["ratio_null_reasons"])

    def test_brief_never_accepts_public_or_historical_callers(self):
        for choice in (
            {"purpose": "public_display"},
            {"purpose": "train"},
            {"purpose": "trade"},
            {"as_of": "2023-12-31T00:00:00+00:00"},
        ):
            with self.subTest(choice=choice), self.assertRaises(BEAContextRefused):
                compose_bea_industry_accounting_change(
                    _synthetic_workspace_response(),
                    industry_code="3341", commodity_code="3344", **choice,
                )

    def test_partial_or_spoofed_reader_causes_no_brief(self):
        for component,field,bad in (
            ("result", "scan_complete", False),
            ("result", "next_offset", 1120),
            ("result", "rows", []),
            ("query", "equals", {"commodity_code_exact": "OTHER"}),
            ("source", "registry_admission", "PRODUCED"),
        ):
            response = _synthetic_workspace_response()
            response[component][field] = bad
            with self.subTest(field=field), self.assertRaises(BEAContextRefused):
                compose_bea_industry_accounting_change(
                    response, industry_code="3341", commodity_code="3344",
                )


class BEAHostBoundQueryTests(unittest.TestCase):
    """The actual preinstalled DataWorkspace, never an alternate file reader."""

    def _research_workspace(self, root: Path):
        from lib.dataos.web_workspace import DataWorkspace, RootBinding

        return DataWorkspace(
            (RootBinding(
                alias="free_source_research",
                path=root,
                evidence_kind="research_capture",
            ),),
            Path(__file__).resolve().parents[1] / "config" / "dataset_registry.yml",
            source_revision="synthetic-pre-admission",
        )

    def _fixture(self, root: Path, *, extra_year: bool = False,
                 full_panel_shape: bool = True) -> Path:
        location = (root / "bea_2024_public_itable_research"
                    / "bea_2017_2022_may2026_remaining_six_regions"
                    / "data_workspace_views_20261011")
        location.mkdir(parents=True)
        path = location / "industry_3341.jsonl"
        rows = []
        for year in range(2017, 2025):
            rows.append(synthetic_row(year=year))
            if full_panel_shape:
                rows.extend(synthetic_row(year=year, commodity=f"A{k:03d}")
                            for k in range(1, 139))
        if extra_year:
            # Keep the 1,112-row source shape while duplicating an exact
            # commodity in the 2024 section; a ninth match must be refused.
            if not full_panel_shape:
                raise ValueError("ninth match requires full panel shape")
            rows[-1] = synthetic_row(year=2024)
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        return path

    def test_end_to_end_host_bound_reader_returns_exact_accounting_brief(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._fixture(root, full_panel_shape=True)
            workspace = self._research_workspace(root)
            report = read_private_bea_accounting_brief(
                workspace, industry_code="3341", commodity_code="3344",
            )
            self.assertEqual(report["authority"], "PRIVATE_RESEARCH_ONLY")
            self.assertEqual(report["periods"]["latest_year"], 2024)
            self.assertEqual(len(report["annual_observations"]), 8)
            self.assertEqual(report["reader_provenance"]["source_row_count"], 8)
            self.assertEqual(report["reader_provenance"]["source_records_scanned"], 1112)
            self.assertTrue(report["reader_provenance"]["scan_complete"])
            self.assertFalse(report["dataos_native_admitted"])
            self.assertFalse(report["may_publish"])
            self.assertFalse(report["named_company_relationship"])
            self.assertEqual(report["source"]["publisher"],
                             "U.S. Bureau of Economic Analysis")

    def test_truncated_eight_row_file_refused_before_data_read(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._fixture(root, full_panel_shape=False)
            workspace = self._research_workspace(root)
            with patch.object(workspace, "read", side_effect=AssertionError(
                "read must not occur after a truncated source description"
            )):
                with self.assertRaisesRegex(BEAContextRefused,
                                            "expected read-only research JSONL source"):
                    read_private_bea_accounting_brief(
                        workspace, industry_code="3341", commodity_code="3344",
                    )

    def test_query_refuses_extra_ninth_matching_row(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._fixture(root, extra_year=True)
            with self.assertRaises(BEAContextRefused):
                read_private_bea_accounting_brief(
                    self._research_workspace(root),
                    industry_code="3341", commodity_code="3344",
                )

    def test_query_refuses_source_changed_between_describe_and_read(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path = self._fixture(root)
            workspace = self._research_workspace(root)
            original_read = workspace.read

            def changed_file(*args, **kwargs):
                with path.open("a", encoding="utf-8") as stream:
                    stream.write("\n")
                return original_read(*args, **kwargs)

            with patch.object(workspace, "read", side_effect=changed_file):
                with self.assertRaisesRegex(BEAContextRefused, "SOURCE_VERSION_MISMATCH"):
                    read_private_bea_accounting_brief(
                        workspace, industry_code="3341", commodity_code="3344",
                    )

    def test_unbound_root_refuses_and_never_discovers_arbitrary_directories(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._fixture(root)
            from lib.dataos.web_workspace import DataWorkspace, RootBinding

            wrong = DataWorkspace(
                (RootBinding(
                    alias="other_research",
                    path=root,
                    evidence_kind="research_capture",
                ),),
                Path(__file__).resolve().parents[1] / "config" / "dataset_registry.yml",
            )
            with self.assertRaisesRegex(BEAContextRefused, "ROOT_NOT_BOUND"):
                read_private_bea_accounting_brief(
                    wrong, industry_code="3341", commodity_code="3344",
                )
            for code in ("../3341", "3341/../", "", "3341.jsonl", "3341 "):
                with self.subTest(code=code), self.assertRaises(BEAContextRefused):
                    read_private_bea_accounting_brief(
                        self._research_workspace(root),
                        industry_code=code, commodity_code="3344",
                    )

    def test_public_or_asof_call_refuses_before_any_file_access(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._fixture(root)
            workspace = self._research_workspace(root)
            for forbidden in (
                {"purpose": "public_display"},
                {"purpose": "trade"},
                {"purpose": "train"},
                {"as_of": "2020-01-01T00:00:00+00:00"},
            ):
                with self.subTest(forbidden=forbidden):
                    with (
                        patch.object(workspace, "describe", side_effect=AssertionError(
                            "forbidden request reached describe")) as describe,
                        patch.object(workspace, "read", side_effect=AssertionError(
                            "forbidden request reached read")) as read,
                    ):
                        with self.assertRaises(BEAContextRefused):
                            read_private_bea_accounting_brief(
                                workspace, industry_code="3341",
                                commodity_code="3344", **forbidden,
                            )
                        describe.assert_not_called()
                        read.assert_not_called()


class BEAIndustryCohortResearchTests(unittest.TestCase):
    """Bounded GMI industry-input comparison over the actual DataWorkspace API."""

    @staticmethod
    def _workspace(root: Path):
        from lib.dataos.web_workspace import DataWorkspace, RootBinding
        return DataWorkspace(
            (RootBinding(alias="free_source_research",
                         path=root, evidence_kind="research_capture"),),
            Path(__file__).resolve().parents[1] / "config" / "dataset_registry.yml",
            source_revision="synthetic-gmi-industry-cohort",
        )

    @staticmethod
    def _source(root: Path, code: str, *,
                negative_2024: bool = False, wrong_using_code: bool = False):
        location = (root / "bea_2024_public_itable_research"
                    / "bea_2017_2022_may2026_remaining_six_regions"
                    / "data_workspace_views_20261011")
        location.mkdir(parents=True, exist_ok=True)
        rows = []
        actual_code = "9999" if wrong_using_code else code
        negative = dict(zip(_KEYS, (-8, 0, -60, 0, 0, -1, -1)))
        for year in range(2017, 2025):
            if negative_2024 and year == 2024:
                row = synthetic_row(
                    year=year, industry=actual_code, world=-69, use=-2,
                    regions=negative,
                )
            else:
                row = synthetic_row(year=year, industry=actual_code)
            rows.append(row)
            rows.extend(
                synthetic_row(year=year, industry=actual_code,
                              commodity=f"A{k:03d}")
                for k in range(1, 139)
            )
        assert len(rows) == 1112
        (location / f"industry_{code}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_two_using_industries_preserve_request_order_and_retrospective_clocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._source(root, "3341")
            self._source(root, "5241X", negative_2024=True)
            report = compare_private_bea_using_industries(
                self._workspace(root),
                industry_codes=("5241X", "3341"), commodity_code="3344",
            )
            self.assertEqual(report["requested_using_industry_codes"],
                             ["5241X", "3341"])
            self.assertEqual(report["returned_using_industry_count"], 2)
            self.assertEqual(report["source_records_scanned"], 2 * 1112)
            self.assertTrue(report["complete_requested_cohort"])
            self.assertIsNone(report["pinned_research_manifest_evidence"])
            self.assertFalse(report["original_view_bytes_hashed_by_this_comparison"])
            self.assertEqual(report["exact_code_namespace"],
                             "BEA_APP157_MAY2026_EXACT")
            self.assertEqual(report["publisher_edition_date"], "2026-05-21")
            self.assertEqual(report["publisher_edition_precision"], "DAY")
            briefs = report["industry_research_briefs"]
            self.assertEqual([x["using_industry"]["code"] for x in briefs],
                             ["5241X", "3341"])
            self.assertEqual(briefs[0]["using_industry"]["legacy_mapping"],
                             "UNRESOLVED_5241X_VS_5241XX")
            self.assertEqual(briefs[0]["annual_observations"][-1][
                "world_import_million_USD"], -69)
            self.assertIn("SOURCE_NEGATIVE_REGION_ADJUSTMENT",
                          briefs[0]["annual_observations"][-1]["ratio_null_reasons"])
            self.assertEqual(len(briefs[1][
                "consecutive_year_signed_changes_million_USD"]), 7)
            self.assertFalse(report["named_company_supplier_buyer_evidence"])
            for key in ("historical_pit_eligible", "may_rank", "may_train",
                        "may_trade", "may_publish", "dataos_native_admitted",
                        "source_bytes_authenticated_by_this_projection"):
                with self.subTest(field=key):
                    self.assertIs(report[key], False)

    def test_missing_or_wrong_industry_fails_whole_cohort_not_partial_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._source(root, "3341")
            workspace = self._workspace(root)
            with self.assertRaises(BEAContextRefused):
                compare_private_bea_using_industries(
                    workspace, industry_codes=("3341", "5241X"),
                    commodity_code="3344",
                )
            self._source(root, "5241X", wrong_using_code=True)
            with self.assertRaises(BEAContextRefused):
                compare_private_bea_using_industries(
                    workspace, industry_codes=("3341", "5241X"),
                    commodity_code="3344",
                )

    def test_invalid_duplicate_or_unbounded_request_refuses_before_source_access(self):
        requests = (
            (),
            ("3341", "3341"),
            ("3341", "../etc"),
            ("3341", "5241XX/"),
            tuple(f"A{k:03d}" for k in range(13)),
            "3341",
            (x for x in ("3341",)),
        )
        for industries in requests:
            with self.subTest(request_type=type(industries).__name__):
                with self.assertRaises(BEAContextRefused):
                    compare_private_bea_using_industries(
                        object(), industry_codes=industries,
                        commodity_code="3344",
                    )
        for purpose in ("trade", "training", "public_display"):
            with self.subTest(purpose=purpose), self.assertRaises(BEAContextRefused):
                compare_private_bea_using_industries(
                    object(), industry_codes=("3341",),
                    commodity_code="3344", purpose=purpose,
                )
        with self.assertRaises(BEAContextRefused):
            compare_private_bea_using_industries(
                object(), industry_codes=("3341",),
                commodity_code="3344", as_of="2024-12-31",
            )

    def test_valid_missing_commodity_is_not_silently_assigned_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._source(root, "3341")
            with self.assertRaises(BEAContextRefused):
                compare_private_bea_using_industries(
                    self._workspace(root), industry_codes=("3341",),
                    commodity_code="BBBB",
                )


class BEAManifestResearchQualificationTests(unittest.TestCase):
    """Only synthetic metadata enters Git; real M2 receipt bytes stay private."""

    @staticmethod
    def _fixture():
        digest = lambda value: hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        names = ["3341", *(f"A{i:03d}" for i in range(1, 138))]
        assert len(names) == 138
        files = {
            f"industry_{code}.jsonl": {
                "bytes": (2_500_000 if idx < 137 else 11_440_588),
                "rows": 1112,
                "sha256": digest("synthetic-" + code),
            }
            for idx, code in enumerate(names)
        }
        assert sum(x["bytes"] for x in files.values()) == 353_940_588
        original_code = {
            "bea_research_views.py": "a" * 64,
            "query_bea_full_region_research.py": "b" * 64,
        }
        lineage_receipts = {f"w{i}": digest(f"capture-receipt-{i}")
                            for i in range(10)}
        source_names = (
            "ImMatAll", "ImMatCan", "ImMatChi", "ImMatEur",
            "ImMatJap", "ImMatMex", "ImMatRoa", "ImMatRow", "Use",
        )
        source_records = {}
        for year in range(2017, 2025):
            source_records[str(year)] = {}
            for n, name in enumerate(source_names):
                source_records[str(year)][name] = {
                    "source_sha256": digest(f"{year}:{name}"),
                    "capture_receipt_sha256": lineage_receipts[
                        f"w{((year - 2017) * 9 + n) % 10}"
                    ],
                    "research_source_capture_completed_at": (
                        f"2026-10-09T{year - 2017:02d}:{n:02d}:00+00:00"
                    ),
                }
        lineage = {
            "schema": "mastermind.bea_industry_input_research_lineage/v1",
            "panel_sha256": bea_module.PANEL_SHA256,
            "qualification_receipt_sha256":
                bea_module.QUALIFICATION_RECEIPT_SHA256,
            "use_panel_sha256": bea_module.USE_PANEL_SHA256,
            "code_namespace": "BEA_APP157_MAY2026_EXACT",
            "publication_date": "2026-05-21",
            "publication_precision": "DAY",
            "publication_timestamp": None,
            "publication_timestamp_null_reason": "PUBLISHER_DAY_PRECISION_ONLY",
            "historical_availability_null_reason": "HISTORICAL_AVAILABILITY_UNVERIFIED",
            "original_historical_available_at": None,
            "native_known_at": None,
            "native_source_adoption": False,
            "public_purpose_adoption": False,
            "source_is_retrospectively_revised_2026_snapshot": True,
            "legacy_mapping_unresolved": {"5241X": "5241XX"},
            "capture_receipt_sha256": lineage_receipts,
            "sources_by_accounting_year": source_records,
        }
        build = {
            "schema": "mastermind.bea_research_view_build_receipt/v1",
            "industry_files": 138,
            "rows_per_industry": 1112,
            "total_rows": 153456,
            "original_inputs_unchanged": {
                "full_panel": bea_module.PANEL_SHA256,
                "full_receipt": bea_module.QUALIFICATION_RECEIPT_SHA256,
                "use_panel": bea_module.USE_PANEL_SHA256,
            },
            "source_lineage_sha256": None,  # populated from exact raw lineage
            "files": files,
            "code_sha256": original_code,
            "dataos_native_admitted": False,
            "historical_pit_eligible": False,
            "may_publish": False,
            "may_rank": False,
            "may_train": False,
            "may_trade": False,
        }
        hardening = {
            "schema": "mastermind.bea_research_view_source_hardening/v1",
            "generation_code_sha256": original_code.copy(),
            "current_code_sha256": {
                **{"bea_research_views.py": "c" * 64,
                   "query_bea_full_region_research.py": "d" * 64},
                "test_bea_research_views.py": "e" * 64,
            },
            "immutable_lineage_sha256": None,  # populated by _run
            "immutable_view_build_receipt_sha256": None,
            "rows_compared": 153456,
            "all_138_file_row_bytes_unchanged_under_current_code": True,
            "existing_view_generation_reused": True,
            "fresh_source_checks_mandatory_for_new_build": True,
            "focused_test_exit_code": 0,
            "dataos_native_admitted": False,
            "historical_pit_eligible": False,
            "may_publish": False,
            "may_rank": False,
            "may_train": False,
            "may_trade": False,
        }
        return build, lineage, hardening

    @staticmethod
    def _encode(doc):
        return json.dumps(
            doc, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")

    def _raw_triplet(self, build, lineage, hardening):
        raw_lineage = self._encode(lineage)
        hash_lineage = hashlib.sha256(raw_lineage).hexdigest()
        build["source_lineage_sha256"] = hash_lineage
        raw_build = self._encode(build)
        hash_build = hashlib.sha256(raw_build).hexdigest()
        hardening["immutable_lineage_sha256"] = hash_lineage
        hardening["immutable_view_build_receipt_sha256"] = hash_build
        raw_hardening = self._encode(hardening)
        return raw_build, raw_lineage, raw_hardening

    def _run(self, build, lineage, hardening, *, selected=("3341",)):
        raw_build, raw_lineage, raw_hardening = self._raw_triplet(
            build, lineage, hardening,
        )
        hash_lineage = hashlib.sha256(raw_lineage).hexdigest()
        hash_build = hashlib.sha256(raw_build).hexdigest()
        with (
            patch.object(bea_module, "BUILD_RECEIPT_SHA256", hash_build),
            patch.object(bea_module, "METADATA_LINEAGE_SHA256", hash_lineage),
            patch.object(
                bea_module, "HARDENING_RECEIPT_SHA256",
                hashlib.sha256(raw_hardening).hexdigest(),
            ),
        ):
            return qualify_private_bea_research_manifest(
                raw_build, raw_lineage, raw_hardening,
                industry_codes=selected,
            )

    def test_three_receipts_bind_original_generation_to_hardened_code(self):
        build, lineage, hardening = self._fixture()
        response = self._run(
            build, lineage, hardening, selected=("3341", "A003"),
        )
        self.assertTrue(response["metadata_receipts_pin_verified"])
        self.assertTrue(response["generation_code_hardening_transition_reconciled"])
        self.assertEqual(response["industry_files_claimed"], 138)
        self.assertEqual(response["rows_per_industry_claimed"], 1112)
        self.assertEqual(response["total_rows_claimed"], 153456)
        self.assertEqual(response["source_bytes_claimed"], 353_940_588)
        self.assertEqual(response["original_source_capture_receipt_count"], 10)
        self.assertEqual(response["original_source_lineage_entries"], 72)
        self.assertEqual(response["requested_using_industry_codes"],
                         ["3341", "A003"])
        self.assertEqual(response["selected_original_builder_digest_claims"]["3341"],
                         build["files"]["industry_3341.jsonl"]["sha256"])
        self.assertEqual(response["edition_precision"], "DAY")
        self.assertEqual(response["exact_code_namespace"],
                         "BEA_APP157_MAY2026_EXACT")
        self.assertNotEqual(build["code_sha256"]["bea_research_views.py"],
                            hardening["current_code_sha256"]["bea_research_views.py"])
        for key in ("selected_original_view_bytes_hashed_by_this_projection",
                    "original_source_bytes_authenticated_by_this_projection",
                    "actual_writer_admitted",
                    "native_utc_ingest_and_revision_clock_established",
                    "historical_pit_eligible", "may_publish", "may_rank",
                    "may_train", "may_trade"):
            with self.subTest(field=key):
                self.assertIs(response[key], False)
        self.assertIsNone(response["original_historical_known_at"])

    def test_missing_or_tampered_source_evidence_refused(self):
        def missing_file(build, lineage, hardening):
            build["files"].pop("industry_A009.jsonl")

        def wrong_byte_total(build, lineage, hardening):
            build["files"]["industry_3341.jsonl"]["bytes"] = 1

        def promoted(build, lineage, hardening):
            build["may_publish"] = True

        def silent_code_alias(build, lineage, hardening):
            lineage["legacy_mapping_unresolved"] = {}

        def invented_historical_clock(build, lineage, hardening):
            lineage["native_known_at"] = "2017-12-31T00:00:00+00:00"

        def absent_geo_region(build, lineage, hardening):
            lineage["sources_by_accounting_year"]["2020"].pop("ImMatChi")

        def nonutc_capture(build, lineage, hardening):
            lineage["sources_by_accounting_year"]["2021"]["Use"][
                "research_source_capture_completed_at"
            ] = "2026-10-09"

        def falsified_hardened_transition(build, lineage, hardening):
            hardening["generation_code_sha256"]["bea_research_views.py"] = "f" * 64

        cases = (
            (missing_file, "file coverage"),
            (wrong_byte_total, "byte-count"),
            (promoted, "source authority"),
            (silent_code_alias, "lineage/edition"),
            (invented_historical_clock, "lineage/edition"),
            (absent_geo_region, "missing world/region"),
            (nonutc_capture, "capture clock"),
            (falsified_hardened_transition, "builder/guard-hardening"),
        )
        for mutate, expected in cases:
            with self.subTest(mutation=mutate.__name__):
                build, lineage, hardening = self._fixture()
                mutate(build, lineage, hardening)
                with self.assertRaisesRegex(BEAContextRefused, expected):
                    self._run(build, lineage, hardening)

    def test_missing_industry_or_unbounded_codes_refused(self):
        build, lineage, hardening = self._fixture()
        with self.assertRaisesRegex(BEAContextRefused, "absent from manifest"):
            self._run(build, lineage, hardening, selected=("ZZZZ",))
        for codes in (("3341", "3341"), ("../fake",),
                      tuple(f"Z{i:03d}" for i in range(13)),
                      (x for x in ("3341",)), "3341"):
            with self.subTest(kind=type(codes).__name__):
                with self.assertRaises(BEAContextRefused):
                    self._run(*self._fixture(), selected=codes)


    def test_bounded_real_reader_attaches_only_pinned_metadata_claims(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            BEAIndustryCohortResearchTests._source(root, "3341")
            BEAIndustryCohortResearchTests._source(root, "A003")
            workspace = BEAIndustryCohortResearchTests._workspace(root)
            build, lineage, hardening = self._fixture()
            raws = self._raw_triplet(build, lineage, hardening)
            with (
                patch.object(
                    bea_module, "BUILD_RECEIPT_SHA256",
                    hashlib.sha256(raws[0]).hexdigest(),
                ),
                patch.object(
                    bea_module, "METADATA_LINEAGE_SHA256",
                    hashlib.sha256(raws[1]).hexdigest(),
                ),
                patch.object(
                    bea_module, "HARDENING_RECEIPT_SHA256",
                    hashlib.sha256(raws[2]).hexdigest(),
                ),
            ):
                report = compare_private_bea_using_industries(
                    workspace, industry_codes=("A003", "3341"),
                    commodity_code="3344", research_receipts=raws,
                )
        self.assertEqual(report["requested_using_industry_codes"],
                         ["A003", "3341"])
        self.assertEqual(report["returned_using_industry_count"], 2)
        self.assertEqual(report["source_records_scanned"], 2224)
        metadata = report["pinned_research_manifest_evidence"]
        self.assertTrue(metadata["metadata_receipts_pin_verified"])
        self.assertEqual(metadata["requested_using_industry_codes"],
                         ["A003", "3341"])
        self.assertEqual(metadata["selected_original_builder_digest_claims"]["3341"],
                         build["files"]["industry_3341.jsonl"]["sha256"])
        self.assertFalse(metadata["original_source_bytes_authenticated_by_this_projection"])
        self.assertFalse(report["original_view_bytes_hashed_by_this_comparison"])
        self.assertFalse(report["historical_pit_eligible"])
        self.assertFalse(report["dataos_native_admitted"])
        self.assertFalse(report["may_publish"])

    def test_invalid_metadata_refused_before_any_data_workspace_io(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            workspace = BEAIndustryCohortResearchTests._workspace(root)
            build, lineage, hardening = self._fixture()
            build["files"].pop("industry_3341.jsonl")
            raws = self._raw_triplet(build, lineage, hardening)
            with (
                patch.object(
                    bea_module, "BUILD_RECEIPT_SHA256",
                    hashlib.sha256(raws[0]).hexdigest(),
                ),
                patch.object(
                    bea_module, "METADATA_LINEAGE_SHA256",
                    hashlib.sha256(raws[1]).hexdigest(),
                ),
                patch.object(
                    bea_module, "HARDENING_RECEIPT_SHA256",
                    hashlib.sha256(raws[2]).hexdigest(),
                ),
                patch.object(
                    workspace, "describe",
                    side_effect=AssertionError("no file access permitted"),
                ),
            ):
                with self.assertRaisesRegex(BEAContextRefused, "file coverage"):
                    compare_private_bea_using_industries(
                        workspace, industry_codes=("3341",),
                        commodity_code="3344", research_receipts=raws,
                    )
            with self.assertRaisesRegex(BEAContextRefused, "three immutable"):
                compare_private_bea_using_industries(
                    workspace, industry_codes=("3341",),
                    commodity_code="3344", research_receipts=(b"partial",),
                )


    def _synthetic_supplied_industry_view(self, *, mutate=None):
        """Fabricate one complete source view and its three synthetic receipts."""
        build, lineage, hardening = self._fixture()
        lineage_sha = hashlib.sha256(self._encode(lineage)).hexdigest()
        commodity_codes = ["3344", *(f"A{i:03d}" for i in range(1, 139))]
        rows = []
        for year in range(2017, 2025):
            for commodity in commodity_codes:
                row = synthetic_row(
                    year=year, industry="3341", commodity=commodity,
                )
                row["source_lineage_sha256"] = lineage_sha
                rows.append(row)
        self.assertEqual(len(rows), 1112)
        if mutate is not None:
            mutate(rows)
        source = b"".join(self._encode(row) + b"\n" for row in rows)
        self.assertLess(len(source), bea_module.MAX_SUPPLIED_INDUSTRY_VIEW_BYTES)
        item = build["files"]["industry_3341.jsonl"]
        old_size = item["bytes"]
        item["bytes"] = len(source)
        item["sha256"] = hashlib.sha256(source).hexdigest()
        build["files"]["industry_A137.jsonl"]["bytes"] += old_size - len(source)
        self.assertGreater(build["files"]["industry_A137.jsonl"]["bytes"], 0)
        return source, self._raw_triplet(build, lineage, hardening)

    def _verify_synthetic_supplied_view(self, source: bytes,
                                        receipts: tuple[bytes, bytes, bytes]):
        with (
            patch.object(
                bea_module, "BUILD_RECEIPT_SHA256",
                hashlib.sha256(receipts[0]).hexdigest(),
            ),
            patch.object(
                bea_module, "METADATA_LINEAGE_SHA256",
                hashlib.sha256(receipts[1]).hexdigest(),
            ),
            patch.object(
                bea_module, "HARDENING_RECEIPT_SHA256",
                hashlib.sha256(receipts[2]).hexdigest(),
            ),
        ):
            return verify_supplied_bea_research_view_bytes(
                source, industry_code="3341",
                build_receipt_bytes=receipts[0],
                lineage_bytes=receipts[1],
                hardening_bytes=receipts[2],
            )

    def test_owner_supplied_view_bytes_match_original_builder_digest_and_grain(self):
        source, receipts = self._synthetic_supplied_industry_view()
        result = self._verify_synthetic_supplied_view(source, receipts)
        self.assertEqual(result["industry_view_rows_checked"], 1112)
        self.assertEqual(result["commodity_codes_per_year_checked"], 139)
        self.assertEqual(result["accounting_years_checked"], list(range(2017, 2025)))
        self.assertEqual(result["supplied_view_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(result["pinned_builder_view_sha256"], result["supplied_view_sha256"])
        self.assertEqual(result["supplied_view_bytes"], len(source))
        self.assertEqual(result["signed_negative_world_import_rows_checked"], 0)
        self.assertEqual(result["signed_negative_region_adjustment_rows_checked"], 0)
        self.assertTrue(result["pinned_receipt_metadata_authenticated"])
        self.assertTrue(result["supplied_research_view_bytes_authenticated"])
        for denial in (
            "original_BEA_L0_response_bytes_authenticated",
            "native_dataset_producer_admitted",
            "source_rights_accepted_for_public_product",
            "historical_pit_eligible", "named_company_supplier_buyer_evidence",
            "may_publish", "may_rank", "may_train", "may_trade",
        ):
            with self.subTest(field=denial):
                self.assertIs(result[denial], False)

    def test_byte_verification_preserves_genuine_negative_accounting_adjustments(self):
        def negative_one_source_cell(rows):
            pos = 3 * 139
            baseline = rows[pos]
            negative = dict(zip(_KEYS, (-8, 0, -60, 0, 0, -1, -1)))
            adjusted = synthetic_row(
                year=2020, industry="3341", commodity="3344",
                use=-2, world=-69, regions=negative,
            )
            adjusted["source_lineage_sha256"] = baseline["source_lineage_sha256"]
            rows[pos] = adjusted

        source, receipts = self._synthetic_supplied_industry_view(
            mutate=negative_one_source_cell,
        )
        proof = self._verify_synthetic_supplied_view(source, receipts)
        self.assertEqual(proof["signed_negative_world_import_rows_checked"], 1)
        self.assertEqual(proof["signed_negative_region_adjustment_rows_checked"], 1)
        self.assertEqual(proof["industry_view_rows_checked"], 1112)
        self.assertTrue(proof["supplied_research_view_bytes_authenticated"])
        self.assertFalse(proof["original_BEA_L0_response_bytes_authenticated"])
        self.assertFalse(proof["historical_pit_eligible"])
        self.assertFalse(proof["may_trade"])

    def test_original_pinned_digest_rejects_tampered_source_bytes(self):
        source, receipts = self._synthetic_supplied_industry_view()
        forged = source.replace(b"Synthetic electronic parts",
                                b"Synthetic component parts", 1)
        self.assertNotEqual(source, forged)
        with self.assertRaisesRegex(BEAContextRefused, "length differs|SHA256 differs"):
            self._verify_synthetic_supplied_view(forged, receipts)

    def test_even_consistently_rehashed_view_rejects_swapped_accounting_period(self):
        def swap(rows):
            rows[139 - 1], rows[139] = rows[139], rows[139 - 1]

        source, receipts = self._synthetic_supplied_industry_view(mutate=swap)
        # The synthetic manifest was rehashed to match the deliberately
        # corrupted bytes; structural accounting-year order must still reject.
        with self.assertRaisesRegex(BEAContextRefused, "accounting-year|commodity order"):
            self._verify_synthetic_supplied_view(source, receipts)

    def test_even_consistently_rehashed_view_rejects_hidden_ninth_commodity_duplicate(self):
        def duplicate(rows):
            rows[138]["commodity_code_exact"] = "3344"

        source, receipts = self._synthetic_supplied_industry_view(mutate=duplicate)
        with self.assertRaisesRegex(BEAContextRefused, "duplicate annual"):
            self._verify_synthetic_supplied_view(source, receipts)

    def test_invalid_supplied_view_content_or_industry_refused(self):
        source, receipts = self._synthetic_supplied_industry_view()
        with self.assertRaisesRegex(BEAContextRefused, "bounded caller-supplied"):
            self._verify_synthetic_supplied_view(b"", receipts)
        with self.assertRaisesRegex(BEAContextRefused, "one exact BEA industry"):
            verify_supplied_bea_research_view_bytes(
                source, industry_code="../3341",
                build_receipt_bytes=receipts[0],
                lineage_bytes=receipts[1],
                hardening_bytes=receipts[2],
            )

    @staticmethod
    def _selected_workspace_response_from_supplied_view(source: bytes):
        response = _synthetic_workspace_response()
        lines = source.split(b"\n")
        positions = [139 * i for i in range(8)]
        response["result"]["row_positions"] = positions
        response["result"]["rows"] = [
            json.loads(lines[position]) for position in positions
        ]
        response["result"]["scanned_rows"] = 1112
        response["result"]["scan_complete"] = True
        response["result"]["next_offset"] = None
        return response

    def _run_workspace_view_binding(self, source, receipts, response):
        mock_history = {
            "observations": [
                {"accounting_year": year} for year in range(2017, 2025)
            ],
            "reader_provenance": {
                "stat_file_version": response["source"]["file_version"],
                "query_receipt_sha256": response["query_receipt_sha256"],
            },
        }
        # The strict canonical reader is separately exercised against real
        # synthetic DataWorkspace.read results. This mock isolates the
        # selection-byte equality contract without patching original row pins.
        with (
            patch.object(
                bea_module, "BUILD_RECEIPT_SHA256",
                hashlib.sha256(receipts[0]).hexdigest(),
            ),
            patch.object(
                bea_module, "METADATA_LINEAGE_SHA256",
                hashlib.sha256(receipts[1]).hexdigest(),
            ),
            patch.object(
                bea_module, "HARDENING_RECEIPT_SHA256",
                hashlib.sha256(receipts[2]).hexdigest(),
            ),
            patch.object(
                bea_module, "adapt_workspace_bea_history",
                return_value=mock_history,
            ),
        ):
            return bea_module.attest_workspace_bea_selection_against_supplied_view(
                response, source, industry_code="3341",
                commodity_code="3344",
                build_receipt_bytes=receipts[0],
                lineage_bytes=receipts[1],
                hardening_bytes=receipts[2],
            )

    def test_workspace_selected_rows_match_pinned_research_view_bytes(self):
        source, receipts = self._synthetic_supplied_industry_view()
        response = self._selected_workspace_response_from_supplied_view(source)
        result = self._run_workspace_view_binding(source, receipts, response)
        self.assertEqual(result["selected_workspace_rows_matched"], 8)
        self.assertEqual(result["selected_workspace_row_positions"],
                         [139 * i for i in range(8)])
        self.assertEqual(result["source_research_view_sha256"],
                         hashlib.sha256(source).hexdigest())
        self.assertTrue(result["selected_workspace_rows_match_pinned_view_bytes"])
        self.assertTrue(result["research_view_bytes_verified_by_supplied_input"])
        for key in (
            "unselected_workspace_disk_bytes_authenticated",
            "upstream_original_BEA_L0_response_bytes_authenticated",
            "native_dataset_admitted",
            "historical_pit_eligible", "may_publish", "may_rank",
            "may_train", "may_trade",
        ):
            with self.subTest(key=key):
                self.assertFalse(result[key])

    def test_changed_row_or_position_never_becomes_byte_attested(self):
        source, receipts = self._synthetic_supplied_industry_view()
        base = self._selected_workspace_response_from_supplied_view(source)
        bad_row = self._selected_workspace_response_from_supplied_view(source)
        bad_row["result"]["rows"][0]["total_use_million_USD"] += 1
        with self.assertRaisesRegex(BEAContextRefused, "row differs"):
            self._run_workspace_view_binding(source, receipts, bad_row)
        bad_position = self._selected_workspace_response_from_supplied_view(source)
        bad_position["result"]["row_positions"][0] = 1
        with self.assertRaisesRegex(BEAContextRefused, "row differs"):
            self._run_workspace_view_binding(source, receipts, bad_position)

    def test_real_source_row_lineage_pin_never_follows_synthetic_test_metadata(self):
        source, receipts = self._synthetic_supplied_industry_view()
        response = self._selected_workspace_response_from_supplied_view(source)
        with (
            patch.object(
                bea_module, "BUILD_RECEIPT_SHA256",
                hashlib.sha256(receipts[0]).hexdigest(),
            ),
            patch.object(
                bea_module, "METADATA_LINEAGE_SHA256",
                hashlib.sha256(receipts[1]).hexdigest(),
            ),
            patch.object(
                bea_module, "HARDENING_RECEIPT_SHA256",
                hashlib.sha256(receipts[2]).hexdigest(),
            ),
        ):
            with self.assertRaisesRegex(BEAContextRefused, "immutable source lineage"):
                bea_module.attest_workspace_bea_selection_against_supplied_view(
                    response, source, industry_code="3341",
                    commodity_code="3344",
                    build_receipt_bytes=receipts[0],
                    lineage_bytes=receipts[1],
                    hardening_bytes=receipts[2],
                )

    def test_original_raw_bytes_are_pinned_even_if_json_remains_valid(self):
        build, lineage, hardening = self._fixture()
        raw_lineage = self._encode(lineage)
        lineage_sha = hashlib.sha256(raw_lineage).hexdigest()
        build["source_lineage_sha256"] = lineage_sha
        raw_build = self._encode(build)
        build_sha = hashlib.sha256(raw_build).hexdigest()
        hardening["immutable_lineage_sha256"] = lineage_sha
        hardening["immutable_view_build_receipt_sha256"] = build_sha
        raw_hardening = self._encode(hardening)
        with (
            patch.object(bea_module, "BUILD_RECEIPT_SHA256", build_sha),
            patch.object(bea_module, "METADATA_LINEAGE_SHA256", lineage_sha),
            patch.object(
                bea_module, "HARDENING_RECEIPT_SHA256",
                hashlib.sha256(raw_hardening).hexdigest(),
            ),
        ):
            with self.assertRaisesRegex(BEAContextRefused, "digest differs"):
                qualify_private_bea_research_manifest(
                    raw_build + b" ", raw_lineage, raw_hardening,
                    industry_codes=("3341",),
                )


if __name__ == "__main__":
    unittest.main()
