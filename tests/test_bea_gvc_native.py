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
        view = bea.candidate_industry_jsonl(candidate, "5241X")
        self.assertEqual(view.row_count, 1112)
        self.assertEqual(view.sha256, digest(view.jsonl_bytes))
        self.assertEqual(len(view.jsonl_bytes.splitlines()), 1112)
        self.assertEqual({json.loads(row)["accounting_year"]
                          for row in view.jsonl_bytes.splitlines()}, set(bea.YEARS))
        seen_views = 0
        for candidate_view in bea.iter_candidate_industry_views(candidate):
            seen_views += 1
            self.assertEqual(candidate_view.row_count, 1112)
            self.assertEqual(candidate_view.sha256, digest(candidate_view.jsonl_bytes))
            self.assertEqual(candidate_view.source_generation_id, candidate.generation_id)
            if candidate_view.industry_code_exact == "5241X":
                self.assertEqual(candidate_view.jsonl_bytes, view.jsonl_bytes)
        self.assertEqual(seen_views, 138)

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


class TestCandidateIndustryView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = bind(fixture())

    def test_exact_industry_jsonl_is_complete_and_digest_bound(self):
        view = bea.candidate_industry_jsonl(self.candidate, "5241X")
        self.assertEqual(view.industry_code_exact, "5241X")
        self.assertEqual(view.source_generation_id, self.candidate.generation_id)
        self.assertEqual(view.row_count, 139)
        self.assertEqual(view.sha256, digest(view.jsonl_bytes))
        self.assertEqual(
            view.proposed_relative_storage_path,
            "data/bea/gvc/may2026/industry_inputs/industry_5241X.jsonl",
        )
        self.assertTrue(view.jsonl_bytes.endswith(b"\n"))
        lines = view.jsonl_bytes.splitlines()
        self.assertEqual(len(lines), view.row_count)
        rows = [json.loads(line) for line in lines]
        self.assertEqual(len({row["commodity_code_exact"] for row in rows}), 139)
        self.assertEqual({row["accounting_year"] for row in rows}, {2017})
        self.assertEqual(rows[0]["total_use_million_USD"], 1000)
        self.assertEqual(rows[0]["world_import_million_USD"], 3)
        self.assertEqual(rows[0]["canada_import_million_USD"], -2)
        self.assertEqual(rows[0]["legacy_industry_mapping_state"],
                         "UNRESOLVED_5241X_VS_5241XX")
        self.assertTrue(all(row["candidate_state"] == "BYTE_VERIFIED_NOT_INSTALLED"
                            and row["dataos_native_admitted"] is False
                            and row["native_ingested_at"] is None
                            and row["may_publish"] is False for row in rows))

    def test_replay_is_byte_identical(self):
        left = bea.candidate_industry_jsonl(self.candidate, "5241X")
        right = bea.candidate_industry_jsonl(self.candidate, "5241X")
        self.assertEqual(left, right)

    def test_unregistered_and_unsafe_source_codes_refuse(self):
        for code in ("5241XX", "5241x", "../escape", "", None, True):
            with self.subTest(code=code), self.assertRaises(bea.BEAGVCRefused):
                bea.candidate_industry_jsonl(self.candidate, code)

    def test_tampering_or_incomplete_rows_never_returns_export(self):
        manifest = self.candidate.manifest
        manifest["may_publish"] = True
        with self.assertRaises(bea.BEAGVCRefused):
            bea.candidate_industry_jsonl(
                replace(self.candidate, manifest_bytes=encoded(manifest)), "5241X")
        with patch.object(bea, "materialize_industry_inputs",
                          return_value=iter([{"industry_code_exact": "5241X"}])):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "incomplete"):
                bea.candidate_industry_jsonl(self.candidate, "5241X")

    def test_view_byte_limit_refuses_without_partial_artifact(self):
        with patch.object(bea, "MAX_INDUSTRY_VIEW_BYTES", 64):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "byte bound"):
                bea.candidate_industry_jsonl(self.candidate, "5241X")

    def test_export_never_writes_or_fetches(self):
        with patch("pathlib.Path.write_bytes", side_effect=AssertionError("write")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("write")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            view = bea.candidate_industry_jsonl(self.candidate, "5241X")
            self.assertEqual(view.row_count, 139)


class TestBatchCandidateIndustryViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = bind(fixture())

    def test_all_138_views_once_with_stable_exact_digests(self):
        with patch.object(bea, "_audit_candidate", wraps=bea._audit_candidate) as audit:
            views = list(bea.iter_candidate_industry_views(self.candidate))
            self.assertEqual(audit.call_count, 1)
        self.assertEqual(len(views), 138)
        self.assertEqual(len({view.industry_code_exact for view in views}), 138)
        self.assertEqual({view.row_count for view in views}, {139})
        self.assertEqual(views[0].industry_code_exact, "5241X")
        self.assertEqual(views[-1].industry_code_exact, "I137")
        self.assertEqual(sum(view.row_count for view in views), 19182)
        self.assertTrue(all(view.sha256 == digest(view.jsonl_bytes)
                            and view.source_generation_id == self.candidate.generation_id
                            for view in views))
        for view in (views[0], views[69], views[-1]):
            self.assertEqual(
                view, bea.candidate_industry_jsonl(self.candidate, view.industry_code_exact))
        rows = [json.loads(raw) for raw in views[0].jsonl_bytes.splitlines()]
        self.assertTrue(all(row["candidate_state"] == "BYTE_VERIFIED_NOT_INSTALLED"
                            and row["may_publish"] is False
                            and row["dataos_native_admitted"] is False for row in rows))

    def test_default_row_order_unchanged_industry_order_is_explicit(self):
        default = bea.materialize_industry_inputs(self.candidate)
        grouped = bea.materialize_industry_inputs(self.candidate, by_industry=True)
        self.assertEqual([next(default)["commodity_code_exact"] for _ in range(2)],
                         ["C000", "C001"])
        self.assertEqual([next(grouped)["commodity_code_exact"] for _ in range(2)],
                         ["C000", "C001"])
        with self.assertRaises(bea.BEAGVCRefused):
            bea.materialize_industry_inputs(self.candidate, by_industry="yes")

    def test_batch_refuses_forged_claim_and_byte_overflow(self):
        manifest = self.candidate.manifest
        manifest["may_publish"] = True
        with self.assertRaises(bea.BEAGVCRefused):
            next(bea.iter_candidate_industry_views(
                replace(self.candidate, manifest_bytes=encoded(manifest))))
        with patch.object(bea, "MAX_INDUSTRY_VIEW_BYTES", 64):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "byte bound"):
                next(bea.iter_candidate_industry_views(self.candidate))

    def test_batch_is_offline_with_no_source_store_writes(self):
        with patch("pathlib.Path.write_bytes", side_effect=AssertionError("write")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("write")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            first = next(bea.iter_candidate_industry_views(self.candidate))
            self.assertEqual(first.row_count, 139)


class TestCandidateBatchIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = bind(fixture())

    def test_complete_index_is_immutable_and_not_native_admitted(self):
        index = bea.build_candidate_industry_index(self.candidate)
        self.assertEqual(index.sha256, digest(index.manifest_bytes))
        self.assertLessEqual(len(index.manifest_bytes), bea.MAX_METADATA_BYTES)
        manifest = json.loads(index.manifest_bytes)
        self.assertEqual(manifest["schema"], "mastermind.bea_gvc_l1_candidate_index/v1")
        self.assertEqual(manifest["source_generation_id"], self.candidate.generation_id)
        self.assertEqual(manifest["industry_count"], 138)
        self.assertEqual(manifest["row_count"], 19182)
        self.assertEqual(manifest["source_response_count"], 9)
        self.assertEqual({v["row_count"] for v in manifest["views"]}, {139})
        self.assertEqual(len({v["industry_code_exact"] for v in manifest["views"]}), 138)
        first = manifest["views"][0]
        self.assertEqual(first["industry_code_exact"], "5241X")
        self.assertEqual(first["jsonl_sha256"],
                         bea.candidate_industry_jsonl(self.candidate, "5241X").sha256)
        self.assertIsNone(manifest["native_ingested_at"])
        self.assertIsNone(manifest["native_revision_seq"])
        self.assertIs(manifest["may_publish"], False)
        self.assertIs(manifest["dataos_native_admitted"], False)
        self.assertEqual(index, bea.build_candidate_industry_index(self.candidate))

    def test_partial_duplicate_mixed_or_oversized_index_refuses(self):
        first = bea.candidate_industry_jsonl(self.candidate, "5241X")
        with patch.object(bea, "iter_candidate_industry_views", return_value=iter([])):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "incomplete"):
                bea.build_candidate_industry_index(self.candidate)
        with patch.object(bea, "iter_candidate_industry_views",
                          return_value=iter([first, first])):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "duplicate"):
                bea.build_candidate_industry_index(self.candidate)
        original_encode = bea._encoded

        def oversized_index_only(value):
            payload = original_encode(value)
            if type(value) is dict and value.get("schema") == (
                    "mastermind.bea_gvc_l1_candidate_index/v1"):
                return payload + b" " * bea.MAX_METADATA_BYTES
            return payload

        with patch.object(bea, "_encoded", side_effect=oversized_index_only):
            with self.assertRaisesRegex(bea.BEAGVCRefused, "metadata exceeds"):
                bea.build_candidate_industry_index(self.candidate)

    def test_index_builder_has_no_source_store_or_network_effect(self):
        with patch("pathlib.Path.write_bytes", side_effect=AssertionError("write")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("write")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            result = bea.build_candidate_industry_index(self.candidate)
            self.assertEqual(json.loads(result.manifest_bytes)["industry_count"], 138)


class TestStagedCandidateByteComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = bind(fixture())
        cls.index = bea.build_candidate_industry_index(cls.candidate)
        cls.staged = {view.industry_code_exact: view.jsonl_bytes
                      for view in bea.iter_candidate_industry_views(cls.candidate)}

    def compare(self, staged=None, index=None, expected=None):
        return bea.compare_candidate_staged_view_bytes(
            self.index if index is None else index,
            self.staged if staged is None else staged,
            expected_index_sha256=self.index.sha256 if expected is None else expected,
        )

    def test_all_staged_bytes_equal_but_never_admitted(self):
        checked = self.compare()
        self.assertTrue(checked.byte_equality_verified)
        self.assertEqual(checked.industry_files_checked, 138)
        self.assertEqual(checked.rows_checked, 19182)
        self.assertEqual(checked.index_sha256, self.index.sha256)
        self.assertEqual(checked.source_generation_id, self.candidate.generation_id)
        self.assertFalse(checked.dataos_native_admitted)
        self.assertFalse(checked.may_publish)

    def test_missing_extra_changed_bytes_or_index_hash_refuse(self):
        removed = dict(self.staged); removed.pop("5241X")
        with self.assertRaises(bea.BEAGVCRefused):
            self.compare(staged=removed)
        added = dict(self.staged); added["NOT_ON_SOURCE_AXIS"] = b"x\n"
        with self.assertRaises(bea.BEAGVCRefused):
            self.compare(staged=added)
        changed = dict(self.staged); changed["5241X"] += b" "
        with self.assertRaises(bea.BEAGVCRefused):
            self.compare(staged=changed)
        with self.assertRaisesRegex(bea.BEAGVCRefused, "digest mismatch"):
            self.compare(expected="1" * 64)
        forged = replace(self.index, sha256="2" * 64)
        with self.assertRaisesRegex(bea.BEAGVCRefused, "digest mismatch"):
            self.compare(index=forged)

    def test_forged_native_publication_claim_and_path_refuse(self):
        manifest = json.loads(self.index.manifest_bytes)
        manifest["may_publish"] = True
        raw = encoded(manifest)
        forged = bea.BEAGVCCandidateIndustryIndex(raw, digest(raw))
        with self.assertRaisesRegex(bea.BEAGVCRefused, "native authority"):
            self.compare(index=forged, expected=forged.sha256)
        manifest["may_publish"] = False
        manifest["views"][0]["relative_storage_path_proposed_only"] = "../escape"
        raw = encoded(manifest)
        forged = bea.BEAGVCCandidateIndustryIndex(raw, digest(raw))
        with self.assertRaisesRegex(bea.BEAGVCRefused, "path mismatch"):
            self.compare(index=forged, expected=forged.sha256)

    def test_comparison_never_writes_or_fetches(self):
        with patch("pathlib.Path.write_bytes", side_effect=AssertionError("write")), \
             patch("pathlib.Path.write_text", side_effect=AssertionError("write")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            self.assertEqual(self.compare().industry_files_checked, 138)


if __name__ == "__main__":
    unittest.main()
