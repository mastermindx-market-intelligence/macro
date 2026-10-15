"""Hermetic candidate-producer tests; no private data, network or native admission."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import unittest
from unittest.mock import patch

from collectors import bea_gvc_native as bea

CAPTURE = "2026-10-09T07:27:58.721565+00:00"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


@lru_cache(maxsize=32)
def original(key, year=2017, amount=None):
    nrows, ncols = (147, 163) if key == "Use" else (141, 161)
    grid = [[{"CV":"0"} for _ in range(ncols)] for _ in range(nrows)]
    for j in range(138):
        grid[0][j+2]["CV"] = "5241X" if j == 0 else f"I{j:03d}"
        grid[1][j+2]["CV"] = f"Industry {j}"
    for i in range(139):
        grid[i+2][0]["CV"] = f"C{i:03d}"
        grid[i+2][1]["CV"] = f"Commodity {i}"
    first = {"Use":"1,000", "ImMatAll":"3", "ImMatCan":"-2", "ImMatChi":"5"}
    grid[2][2]["CV"] = first.get(key, "0") if amount is None else amount
    table = {"Title":bea.TITLES[key], "Description":bea.EDITION_LABEL,
             "Sub_Title":f"{year}, [Millions of Dollars]", "Number_Of_Rows":str(nrows),
             "Number_Of_Columns":str(ncols), "Number_Of_Header_Rows":"2", "Data_Rows":grid}
    page = {"AppId":157, "Number":2, "Prompts":[{
        "Name":"TheTable", "UIControl":"Table",
        "PromtData":encoded({"Table":encoded(table).decode()}).decode()}]}
    return encoded(encoded(page).decode())


def change_table(blob, mutate):
    page = json.loads(json.loads(blob))
    wrapped = json.loads(page["Prompts"][0]["PromtData"])
    table = json.loads(wrapped["Table"])
    mutate(table)
    wrapped["Table"] = encoded(table).decode()
    page["Prompts"][0]["PromtData"] = encoded(wrapped).decode()
    return encoded(encoded(page).decode())


def fixture(year=2017, world="3"):
    source = {(year,k):original(k,year,world if k == "ImMatAll" else None) for k in bea.TABLES}
    groups = [
        ("mastermind.bea_2017_2022_world_china_imports_capture/v1", ["ImMatAll","ImMatChi"],
         "raw_files", "source_sha256", "raw_bytes"),
        ("mastermind.bea_six_regions_single_year_official_capture/v1",
         [k for k,_,_ in bea.REGIONS if k != "ImMatChi"], "files", "sha256", "bytes"),
        ("mastermind.bea_public_2017_2022_may2026_use_private/v1", ["Use"],
         "files", "sha256", "raw_bytes"),
    ]
    receipts, refs = {}, {}
    for schema, keys, field, sha_field, size_field in groups:
        records = [{"year":year, "key":key, sha_field:digest(source[year,key]),
                    size_field:len(source[year,key])} for key in keys]
        raw = encoded({"schema":schema, "captured_at_utc":CAPTURE, field:records})
        sha = digest(raw)
        receipts[sha] = raw
        refs.update({key:sha for key in keys})
    lineage = {
        "schema":"mastermind.bea_industry_input_research_lineage/v1",
        "publication_date":bea.EDITION_DATE, "publication_precision":"DAY",
        "publication_timestamp":None,
        "publication_timestamp_null_reason":"PUBLISHER_DAY_PRECISION_ONLY",
        "original_historical_available_at":None, "native_known_at":None,
        "native_source_adoption":False, "code_namespace":bea.CODE_NAMESPACE,
        "capture_receipt_sha256":{str(i):sha for i,sha in enumerate(receipts)},
        "sources_by_accounting_year":{
            str(y):{key:{"source_sha256":digest(source[year,key]),
                         "capture_receipt_sha256":refs[key],
                         "research_source_capture_completed_at":CAPTURE}
                    for key in bea.TABLES} for y in bea.YEARS},
    }
    return encoded(lineage), source, receipts


def bind(parts, *, years=(2017,), **kwargs):
    lineage, source, receipts = parts
    return bea.bind_retained_responses(lineage, source, receipts, selected_years=years,
                                     expected_lineage_sha256=digest(lineage), **kwargs)


class TestNativeCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = fixture()
        cls.candidate = bind(cls.parts)

    def test_complete_selected_population_signed_values_and_nulls(self):
        rows = bea.materialize_industry_inputs(self.candidate)
        first = next(rows)
        self.assertEqual(first["total_use_million_USD"], 1000)
        self.assertEqual(first["canada_import_million_USD"], -2)
        self.assertEqual(first["world_import_million_USD"], 3)
        self.assertEqual(first["region_rounding_difference_million_USD"], 0)
        self.assertEqual(first["legacy_industry_mapping_state"], "UNRESOLVED_5241X_VS_5241XX")
        self.assertEqual(first["publication_precision"], "DAY")
        self.assertIsNone(first["published_at"])
        for key in ("native_ingested_at", "native_known_at", "native_revision_seq",
                    "original_historical_available_at", "canonical_industry_id", "canonical_security_id"):
            self.assertIsNone(first[key])
        for key in ("dataos_native_admitted", "historical_pit_eligible", "named_company_relationship",
                    "may_publish", "may_rank", "may_train", "may_trade", "period_end_is_availability"):
            self.assertIs(first[key], False)
        self.assertEqual(len(first["source_response_sha256_by_table"]), 9)
        identities = {(first["industry_code_exact"], first["commodity_code_exact"])}
        for row in rows:
            self.assertEqual(row["source_generation_id"], first["source_generation_id"])
            identities.add((row["industry_code_exact"], row["commodity_code_exact"]))
        self.assertEqual(len(identities), 138*139)
        self.assertFalse(self.candidate.manifest["complete_2017_2024_panel"])
        self.assertEqual(self.candidate.manifest["source_response_count"], 9)

    def test_manifest_copy_cannot_mutate_candidate(self):
        self.candidate.manifest["may_publish"] = True
        self.assertFalse(self.candidate.manifest["may_publish"])

    def test_replay_is_same_generation_and_same_clock(self):
        replay = bind(self.parts, predecessor=self.candidate)
        self.assertIs(replay, self.candidate)
        self.assertEqual(replay.manifest["candidate_revision_seq"], 0)

    def test_correction_links_without_overwriting_predecessor(self):
        revised = bind(fixture(world="4"), predecessor=self.candidate)
        self.assertEqual(revised.manifest["candidate_revision_seq"], 1)
        self.assertEqual(revised.manifest["supersedes_candidate_generation"], self.candidate.generation_id)
        self.assertNotEqual(revised.generation_id, self.candidate.generation_id)
        self.assertEqual(self.candidate.manifest["candidate_revision_seq"], 0)
        row = next(bea.materialize_industry_inputs(revised))
        self.assertEqual(row["region_rounding_difference_million_USD"], 1)

    def test_rounding_boundary(self):
        accepted = bind(fixture(world="6"))
        self.assertEqual(next(bea.materialize_industry_inputs(accepted))["region_rounding_difference_million_USD"], 3)
        with self.assertRaises(bea.BEAGVCRefused):
            bind(fixture(world="7"))

    def test_default_evidence_pin_rejects_synthetic_lineage(self):
        with self.assertRaises(bea.BEAGVCRefused):
            bea.bind_retained_responses(*self.parts, selected_years=(2017,))

    def test_source_population_requires_use_and_all_regions(self):
        for bad in ("Use", "ImMatCan"):
            with self.subTest(missing=bad):
                source = dict(self.parts[1]); source.pop((2017,bad))
                with self.assertRaises(bea.BEAGVCRefused):
                    bind((self.parts[0],source,self.parts[2]))
        source = dict(self.parts[1]); source[2017,"Make"] = b"{}"
        with self.assertRaises(bea.BEAGVCRefused):
            bind((self.parts[0],source,self.parts[2]))

    def test_original_byte_tampering(self):
        source = dict(self.parts[1]); source[2017,"Use"] += b" "
        with self.assertRaises(bea.BEAGVCRefused):
            bind((self.parts[0],source,self.parts[2]))

    def test_capture_receipt_tampering_or_absence(self):
        receipts = dict(self.parts[2]); key = next(iter(receipts)); receipts[key] += b" "
        with self.assertRaises(bea.BEAGVCRefused):
            bind((self.parts[0],self.parts[1],receipts))
        receipts.pop(key)
        with self.assertRaises(bea.BEAGVCRefused):
            bind((self.parts[0],self.parts[1],receipts))

    def test_invalid_year_scopes(self):
        for years in ((True,), (2016,), (2017,2017), (), "2017"):
            with self.subTest(years=years), self.assertRaises(bea.BEAGVCRefused):
                bind(self.parts,years=years)

    def test_future_naive_and_pre_edition_capture_refused(self):
        for clock in ("2099-01-01T00:00:00+00:00", "2026-10-09T07:00:00", "2025-01-01T00:00:00Z"):
            lineage = json.loads(self.parts[0])
            lineage["sources_by_accounting_year"]["2017"]["Use"]["research_source_capture_completed_at"] = clock
            with self.subTest(clock=clock), self.assertRaises(bea.BEAGVCRefused):
                bind((encoded(lineage),self.parts[1],self.parts[2]))

    def test_no_native_or_historical_promotion_in_lineage(self):
        for field,value in (("publication_precision","SECOND"), ("native_source_adoption",True),
                            ("native_known_at",CAPTURE), ("original_historical_available_at","2017-12-31")):
            lineage = json.loads(self.parts[0]); lineage[field] = value
            with self.subTest(field=field), self.assertRaises(bea.BEAGVCRefused):
                bind((encoded(lineage),self.parts[1],self.parts[2]))

    def test_tampered_parsed_table_refused_before_iterator_return(self):
        first = self.candidate.sources[0]
        amounts = list(first.table.amounts); amounts[0] = (999,) + amounts[0][1:]
        forged = replace(first,table=replace(first.table,amounts=tuple(amounts)))
        candidate = replace(self.candidate,sources=(forged,) + self.candidate.sources[1:])
        with self.assertRaises(bea.BEAGVCRefused):
            bea.materialize_industry_inputs(candidate)

    def test_forged_publish_flag_refused(self):
        manifest = self.candidate.manifest; manifest["may_publish"] = True
        with self.assertRaises(bea.BEAGVCRefused):
            bea.materialize_industry_inputs(replace(self.candidate,manifest_bytes=encoded(manifest)))

    def test_correction_scope_cannot_silently_expand(self):
        with self.assertRaises(bea.BEAGVCRefused):
            bind(fixture(year=2018),years=(2018,),predecessor=self.candidate)

    def test_failed_binding_never_calls_a_network_or_writes(self):
        with patch("urllib.request.urlopen",side_effect=AssertionError("network forbidden")), \
             patch("pathlib.Path.write_bytes",side_effect=AssertionError("write forbidden")), \
             patch("pathlib.Path.write_text",side_effect=AssertionError("write forbidden")):
            self.assertIs(bind(self.parts,predecessor=self.candidate), self.candidate)


class TestSourceParser(unittest.TestCase):
    def test_bad_source_headers_shapes_and_codes(self):
        changes = {
            "edition":lambda t:t.update(Description="May 20, 2026"),
            "year":lambda t:t.update(Sub_Title="2018, [Millions of Dollars]"),
            "units":lambda t:t.update(Sub_Title="2017, [Billions of Dollars]"),
            "region":lambda t:t.update(Title=bea.TITLES["ImMatChi"]),
            "header_count":lambda t:t.update(Number_Of_Header_Rows="1"),
            "numeric_shape":lambda t:t.update(Number_Of_Rows=141),
            "truncated":lambda t:t["Data_Rows"].pop(),
            "ragged":lambda t:t["Data_Rows"][10].pop(),
            "duplicate_industry":lambda t:t["Data_Rows"][0][3].update(CV="5241X"),
            "duplicate_commodity":lambda t:t["Data_Rows"][3][0].update(CV="C000"),
            "company_symbol":lambda t:t["Data_Rows"][0][2].update(CV="NASDAQ:MU"),
            "missing_name":lambda t:t["Data_Rows"][1][2].update(CV=""),
            "wrong_cell_type":lambda t:t["Data_Rows"][2][2].update(CV=True),
        }
        for name,change in changes.items():
            with self.subTest(change=name), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(change_table(original("ImMatCan"),change),"ImMatCan",2017)

    def test_malformed_numbers_do_not_become_zero(self):
        for value in ("(D)", "--", "", "1.2", "1,00", "00", "+1", "NaN", "Infinity", " 1"):
            with self.subTest(value=value), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(original("ImMatCan",2017,value),"ImMatCan",2017)

    def test_duplicate_json_keys_and_nonfinite_constants(self):
        for blob in (b'{"AppId":157,"AppId":157}', b'{"value":NaN}', b'{"value":Infinity}'):
            with self.subTest(blob=blob), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(blob,"ImMatCan",2017)

    def test_boolean_app_id_and_ambiguous_prompt(self):
        for key,value in (("AppId",True), ("Number",True)):
            page = json.loads(json.loads(original("ImMatCan"))); page[key] = value
            with self.subTest(key=key), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(encoded(page),"ImMatCan",2017)
        page = json.loads(json.loads(original("ImMatCan")))
        page["Prompts"] *= 2
        with self.assertRaises(bea.BEAGVCRefused):
            bea._parse_response(encoded(page),"ImMatCan",2017)

    def test_source_size_and_exact_bytes_type(self):
        for blob in ("{}", bytearray(b"{}"), b"", b"x"*(bea.MAX_RESPONSE_BYTES+1)):
            with self.subTest(kind=type(blob).__name__), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(blob,"ImMatCan",2017)

    def test_last_two_capture_receipt_shapes(self):
        sha = "1"*64
        receipt23 = {"schema":"mastermind.bea_public_itable_2023_same_2026_release_capture/v1",
                     "tables":[{"key":"Use","source_effective_year":2023,"sha256":sha,
                                "original_bytes":17,"acquired_at_utc":CAPTURE}]}
        receipt24 = {"schema":"mastermind.bea_2024_source_qualification_receipt/v1",
                     "source_artifacts":{"Use":{"year":2024,"file_sha256":sha,"capture_utc":CAPTURE}}}
        self.assertEqual(bea._receipt_source(receipt23,2023,"Use"),(sha,CAPTURE,17))
        self.assertEqual(bea._receipt_source(receipt24,2024,"Use"),(sha,CAPTURE,None))
        receipt23["tables"] *= 2
        with self.assertRaises(bea.BEAGVCRefused):
            bea._receipt_source(receipt23,2023,"Use")
        receipt24["source_artifacts"]["Use"]["year"] = True
        with self.assertRaises(bea.BEAGVCRefused):
            bea._receipt_source(receipt24,2024,"Use")


class TestCandidateHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = fixture()
        cls.candidate = bind(cls.parts)

    def test_complete_eight_year_synthetic_generation(self):
        all_sources, all_receipts, by_year = {}, {}, {}
        skeleton = None
        for year in bea.YEARS:
            raw_lineage, sources, receipts = fixture(year=year)
            lineage = json.loads(raw_lineage)
            if skeleton is None:
                skeleton = lineage
            selected = lineage["sources_by_accounting_year"][str(year)]
            if year in (2023,2024):
                if year == 2023:
                    record = {"schema":"mastermind.bea_public_itable_2023_same_2026_release_capture/v1",
                              "tables":[{"key":key,"source_effective_year":year,
                                          "sha256":digest(sources[year,key]),"original_bytes":len(sources[year,key]),
                                          "acquired_at_utc":CAPTURE} for key in bea.TABLES]}
                else:
                    record = {"schema":"mastermind.bea_2024_source_qualification_receipt/v1",
                              "source_artifacts":{key:{"year":year,"file_sha256":digest(sources[year,key]),
                                                       "capture_utc":CAPTURE} for key in bea.TABLES}}
                raw = encoded(record); pin = digest(raw); receipts = {pin:raw}
                for entry in selected.values():
                    entry["capture_receipt_sha256"] = pin
            all_sources.update(sources); all_receipts.update(receipts); by_year[str(year)] = selected
        skeleton["sources_by_accounting_year"] = by_year
        skeleton["capture_receipt_sha256"] = {str(i):sha for i,sha in enumerate(all_receipts)}
        candidate = bind((encoded(skeleton),all_sources,all_receipts),years=bea.YEARS)
        self.assertTrue(candidate.manifest["complete_2017_2024_panel"])
        self.assertEqual(candidate.manifest["source_response_count"], 72)
        count = 0; per_year = {}; per_industry = {}
        for row in bea.materialize_industry_inputs(candidate):
            count += 1
            per_year[row["accounting_year"]] = per_year.get(row["accounting_year"],0)+1
            per_industry[row["industry_code_exact"]] = per_industry.get(row["industry_code_exact"],0)+1
            self.assertEqual(row["source_generation_id"],candidate.generation_id)
            self.assertIs(row["dataos_native_admitted"],False)
        self.assertEqual(count,153456)
        self.assertEqual(set(per_year.values()),{19182})
        self.assertEqual(set(per_industry.values()),{1112})

    def test_source_tokens_preserve_case_without_aliasing(self):
        blob = change_table(original("ImMatCan"),
                            lambda t:t["Data_Rows"][0][2].update(CV="Example7"))
        parsed = bea._parse_response(blob,"ImMatCan",2017)
        self.assertEqual(parsed.industry_codes[0], "Example7")
        self.assertNotEqual(parsed.industry_codes[0], "EXAMPLE7")
        for token in ("../A", "A/B", " A", "", "X"*33):
            with self.subTest(token=token), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(change_table(original("ImMatCan"),
                    lambda t:t["Data_Rows"][0][2].update(CV=token)),"ImMatCan",2017)

    def test_unsupported_source_table_and_year_are_explicit_refusals(self):
        for key,year in (("Make",2017), ([],2017), ("Use",True), ("Use",2016)):
            with self.subTest(key=key,year=year), self.assertRaises(bea.BEAGVCRefused):
                bea._parse_response(original("Use"),key,year)

    def test_boolean_amount_cannot_hide_behind_integer_equality(self):
        source = self.candidate.sources[0]
        amounts = list(source.table.amounts)
        amounts[1] = (False,) + amounts[1][1:]
        forged = replace(source,table=replace(source.table,amounts=tuple(amounts)))
        with self.assertRaises(bea.BEAGVCRefused):
            bea.materialize_industry_inputs(replace(self.candidate,
                sources=(forged,) + self.candidate.sources[1:]))

    def test_candidate_refuses_future_clock_bad_revision_and_missing_predecessor(self):
        for field,value in (("candidate_ingested_at","2099-01-01T00:00:00+00:00"),
                            ("candidate_revision_seq",True), ("candidate_revision_seq",1),
                            ("supersedes_candidate_generation","1"*64)):
            manifest = self.candidate.manifest; manifest[field] = value
            with self.subTest(field=field,value=value), self.assertRaises(bea.BEAGVCRefused):
                bea.materialize_industry_inputs(replace(self.candidate,manifest_bytes=encoded(manifest)))

    def test_duplicate_candidate_sources_and_receipts_are_refused(self):
        with self.assertRaises(bea.BEAGVCRefused):
            bea.materialize_industry_inputs(replace(self.candidate,
                sources=self.candidate.sources+(self.candidate.sources[0],)))
        with self.assertRaises(bea.BEAGVCRefused):
            bea.materialize_industry_inputs(replace(self.candidate,
                capture_receipts=self.candidate.capture_receipts+(self.candidate.capture_receipts[0],)))

    def test_receipt_content_must_agree_even_when_new_hash_is_supplied(self):
        lineage = json.loads(self.parts[0]); receipts = dict(self.parts[2])
        old = lineage["sources_by_accounting_year"]["2017"]["Use"]["capture_receipt_sha256"]
        receipt = json.loads(receipts.pop(old)); receipt["files"][0]["raw_bytes"] += 1
        raw = encoded(receipt); new = digest(raw); receipts[new] = raw
        lineage["capture_receipt_sha256"] = {k:(new if v == old else v)
            for k,v in lineage["capture_receipt_sha256"].items()}
        for annual in lineage["sources_by_accounting_year"].values():
            for entry in annual.values():
                if entry["capture_receipt_sha256"] == old:
                    entry["capture_receipt_sha256"] = new
        with self.assertRaises(bea.BEAGVCRefused):
            bind((encoded(lineage),self.parts[1],receipts))

    def test_cross_table_axis_drift_refused_with_consistent_byte_pins(self):
        lineage = json.loads(self.parts[0]); sources = dict(self.parts[1]); receipts = dict(self.parts[2])
        key = "Use"; old = lineage["sources_by_accounting_year"]["2017"][key]["capture_receipt_sha256"]
        changed = change_table(sources[2017,key],lambda t:t["Data_Rows"][0][2].update(CV="5241XX"))
        sources[2017,key] = changed
        receipt = json.loads(receipts.pop(old)); receipt["files"][0].update(sha256=digest(changed),raw_bytes=len(changed))
        raw = encoded(receipt); new = digest(raw); receipts[new] = raw
        lineage["capture_receipt_sha256"] = {k:(new if v == old else v)
            for k,v in lineage["capture_receipt_sha256"].items()}
        for annual in lineage["sources_by_accounting_year"].values():
            annual[key].update(source_sha256=digest(changed),capture_receipt_sha256=new)
        with self.assertRaises(bea.BEAGVCRefused):
            bind((encoded(lineage),sources,receipts))


class TestProducerIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = fixture()
        cls.candidate = bind(cls.parts)

    def test_materializer_refuses_self_consistent_foreign_producer_hash(self):
        current = self.candidate.manifest
        foreign = bea._manifest(self.candidate.sources, current["source_lineage_sha256"],
                                "1" * 64, (2017,), current["candidate_ingested_at"], 0, None)
        candidate = replace(self.candidate, manifest_bytes=encoded(foreign))
        with self.assertRaisesRegex(bea.BEAGVCRefused, "producer"):
            bea.materialize_industry_inputs(candidate)

    def test_producer_change_requires_explicit_linked_rebind(self):
        with patch("pathlib.Path.read_bytes", return_value=b"earlier producer source"):
            earlier = bind(self.parts)
        old_generation = earlier.generation_id
        with self.assertRaisesRegex(bea.BEAGVCRefused, "producer"):
            bea.materialize_industry_inputs(earlier)
        rebound = bind(self.parts, predecessor=earlier)
        self.assertEqual(rebound.manifest["candidate_revision_seq"], 1)
        self.assertEqual(rebound.manifest["supersedes_candidate_generation"], old_generation)
        self.assertEqual(earlier.generation_id, old_generation)
        first = next(bea.materialize_industry_inputs(rebound))
        self.assertEqual(first["producer_code_sha256"], self.candidate.manifest["producer_code_sha256"])
        self.assertEqual(first["source_generation_id"], rebound.generation_id)
        self.assertFalse(first["dataos_native_admitted"])
        self.assertFalse(first["may_publish"])
        self.assertIs(bind(self.parts, predecessor=rebound), rebound)

    def test_unreadable_producer_source_is_an_explicit_refusal(self):
        with patch("pathlib.Path.read_bytes", side_effect=OSError("source unavailable")):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "producer"):
                bea.materialize_industry_inputs(self.candidate)
            with self.assertRaisesRegex(bea.BEAGVCRefused, "producer"):
                bind(self.parts)


if __name__ == "__main__":
    unittest.main()
