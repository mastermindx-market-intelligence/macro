"""Bounded SOURCE-ONLY regression tests; no host/source owner effects."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot, ValidatedCandidateEpisodeGeneration,
)
from research.options_estate.ptse_contract import build_context, canonical_json
from research.options_estate.ptse_w3_publication import (
    RECEIPT_SCHEMA, PTSEPublicationError, b1_material_bytes,
    build_publication_packet, preflight_publication, validate_publication_packet,
)
from tests.test_ptse_prospective_readiness import prospective_new_entry


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(owner, artifact_id, digest):
    return {"owner_ref": owner, "artifact_id": artifact_id, "sha256": digest}


def key(row):
    return f"candidate:{row['stamp_date']}:{row['ticker']}:{row['board_definition']}"


def candidate(ticker="AAPL", **changes):
    row = {"stamp_date": "2026-09-18", "ticker": ticker,
           "board_definition": "us_prophet_v3", "score_rank": 7,
           "prophet_score": 62.5}
    row.update(changes)
    return row


def snapshot(rows, *, duplicate=False, malformed=False):
    assessment = prospective_new_entry().to_dict()["assessment"]
    episode = {k: assessment[k] for k in (
        "episode_id", "security_id", "company_id", "identity_epoch")}
    episode["source_event_ids"] = [key(r) for r in rows]
    if malformed:
        episode["source_event_ids"] = 1
    episodes = (episode, copy.deepcopy(episode)) if duplicate else (episode,)
    generation = ValidatedCandidateEpisodeGeneration(
        Path("unused-pure-test-path"), (), (), episodes, {"fixture": "externally-validated"})
    return CandidateEpisodeStoreSnapshot(assessment["candidate_generation_id"], generation)


def inputs(rows=None, *, b1=None, contexts=None):
    rows = [candidate()] if rows is None else rows
    b1 = snapshot(rows) if b1 is None else b1
    contexts = {key(rows[0]): prospective_new_entry()} if contexts is None and rows else (contexts or {})
    manifest = {
        "schema": RECEIPT_SCHEMA, "stamp_date": "2026-09-18",
        "candidate_generation_id": b1.generation_id,
        "candidate_population_receipt": ref("candidate-owner", "whole-population:1",
                                            sha(canon(sorted(rows, key=key)))),
        "b1_material_receipt": ref("b1-owner", "validated-b1:1", sha(b1_material_bytes(b1))),
        "context_receipts": {},
    }
    for source, artifact in contexts.items():
        if not hasattr(artifact, "to_dict"):
            from research.options_estate.ptse_contract import validate_context
            artifact = validate_context(artifact)
        p = artifact.to_dict()
        manifest["context_receipts"][source] = {
            "artifact_ref": ref("ptse-owner", "external-artifact:" + source, artifact.sha256),
            "observation_id": artifact.observation_id,
            "assessment_id": artifact.assessment_id,
            "source_manifest_ref": p["observation"]["source_manifest_ref"],
            "calculation_receipt_ref": p["observation"]["calculation_receipt_ref"],
        }
    return dict(stamp_date="2026-09-18", candidate_rows=rows, b1_snapshot=b1,
                receipt_manifest=manifest, receipt_manifest_sha256=sha(canon(manifest)),
                contexts=contexts)


def repin(data):
    data["receipt_manifest_sha256"] = sha(canon(data["receipt_manifest"]))
    return data


def reseal(packet):
    packet.pop("packet_id", None)
    packet["packet_id"] = "ptse-w3:" + sha(canon(packet))
    return canon(packet)


class PTSEPublicationTest(unittest.TestCase):
    def test_first_complete_packet_and_external_artifacts(self):
        data = inputs()
        result = preflight_publication(**data)
        self.assertEqual(result.status, "FIRST_PACKET")
        self.assertIs(result.publication_authority, False)
        validate_publication_packet(result.first_packet, **data)
        p = json.loads(result.first_packet)
        self.assertEqual(p["denominators"], {"attempted": 1, "enrolled": 1, "relation_refused": 0})
        self.assertEqual(p["preflight_status"], "READY_FOR_EXISTING_PUBLICATION_OWNER")
        self.assertNotIn("candidate_rows", p)
        self.assertNotIn("context_artifacts", p)
        self.assertNotIn("score_rank", result.first_packet.decode())
        self.assertEqual(result.candidate_context_artifacts,
                         ((prospective_new_entry().sha256, prospective_new_entry().canonical_bytes),))

    def test_all_missing_context_keeps_whole_cohort(self):
        data = inputs([candidate(), candidate("MSFT")], contexts={})
        bundle = build_publication_packet(**data)
        p = json.loads(bundle.packet)
        self.assertEqual(p["denominators"]["attempted"], 2)
        self.assertEqual(len(p["rows"]), 2)
        self.assertTrue(all(r["enrollment"]["context_reason"] == "CONTEXT_MISSING" for r in p["rows"]))
        validate_publication_packet(bundle.packet, **data)

    def test_unavailable_and_ambiguous_relations_are_counted_without_b1_identity(self):
        rows = [candidate(), candidate("MSFT")]
        for b1, code in ((snapshot([]), "CANDIDATE_B1_RELATION_UNAVAILABLE"),
                         (snapshot(rows, duplicate=True), "CANDIDATE_B1_RELATION_AMBIGUOUS")):
            with self.subTest(code=code):
                data = inputs(rows, b1=b1, contexts={})
                bundle = build_publication_packet(**data)
                p = json.loads(bundle.packet)
                self.assertEqual(p["denominators"], {"attempted": 2, "enrolled": 0, "relation_refused": 2})
                self.assertEqual(p["preflight_status"], "RELATION_REFUSED")
                for row in p["rows"]:
                    self.assertEqual(row["reason"], code)
                    self.assertNotIn("episode_id", row)
                    self.assertNotIn("security_id", row)
                validate_publication_packet(bundle.packet, **data)

    def test_malformed_source_metadata_never_becomes_complete_packet(self):
        for rows in ([candidate()], []):
            data = inputs(rows, contexts={})
            data["b1_snapshot"] = snapshot([candidate()], malformed=True)
            with self.assertRaisesRegex(PTSEPublicationError, "B1_SOURCE_METADATA_INVALID"):
                build_publication_packet(**data)

    def test_mixed_enrollment_and_relation_refusal_denominator(self):
        rows = [candidate(), candidate("MSFT")]
        data = inputs(rows, b1=snapshot([candidate()]), contexts={})
        bundle = build_publication_packet(**data)
        p = json.loads(bundle.packet)
        self.assertEqual(p["denominators"], {"attempted": 2, "enrolled": 1, "relation_refused": 1})
        self.assertEqual([r["row_kind"] for r in p["rows"]], ["ENROLLED", "RELATION_REFUSED"])
        validate_publication_packet(bundle.packet, **data)

    def test_returned_context_bytes_are_required_for_prior_reconstruction(self):
        original = inputs()
        bundle = build_publication_packet(**original)
        retained = dict(bundle.context_artifacts)
        reconstructed = dict(original)
        reconstructed["contexts"] = {key(candidate()): retained[prospective_new_entry().sha256]}
        validate_publication_packet(bundle.packet, **reconstructed)
        reconstructed["contexts"] = {key(candidate()): retained[prospective_new_entry().sha256] + b" "}
        with self.assertRaises(PTSEPublicationError):
            validate_publication_packet(bundle.packet, **reconstructed)

    def test_duplicate_keys_mixed_stamp_mixed_generation_and_strict_date(self):
        cases = [([candidate(), candidate()], "DUPLICATE_CANDIDATE_KEY"),
                 ([candidate(stamp_date="2026-09-19")], "MIXED_CANDIDATE_STAMP"),
                 ([candidate(candidate_generation_id="other")], "MIXED_CANDIDATE_GENERATION"),
                 ([candidate(stamp_date="20260918")], "STAMP_DATE_INVALID"),
                 ([candidate(stamp_date="2026-02-30")], "STAMP_DATE_INVALID"),
                 ([candidate(ticker="A:A")], "CANDIDATE_IDENTITY_DELIMITER_FORBIDDEN")]
        for rows, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(PTSEPublicationError, code):
                    build_publication_packet(**inputs(rows, contexts={}))

    def test_extra_context_key_and_receipt_keys_refused(self):
        data = inputs()
        data["contexts"]["candidate:2026-09-18:EXTRA:us_prophet_v3"] = prospective_new_entry()
        with self.assertRaisesRegex(PTSEPublicationError, "EXTRA_OR_INVALID_CONTEXT_KEYS"):
            build_publication_packet(**data)
        data = inputs()
        data["receipt_manifest"]["context_receipts"]["extra"] = {}
        with self.assertRaisesRegex(PTSEPublicationError, "CONTEXT_RECEIPT_KEYS_MISMATCH"):
            build_publication_packet(**repin(data))

    def test_input_order_has_identical_packet_and_artifacts(self):
        rows = [candidate(), candidate("MSFT")]
        data = inputs(rows, contexts={})
        first = build_publication_packet(**data)
        data["candidate_rows"] = list(reversed(rows))
        second = build_publication_packet(**data)
        self.assertEqual(first, second)

    def test_source_manifest_tamper_and_context_receipt_tamper(self):
        data = inputs()
        data["receipt_manifest"]["candidate_population_receipt"]["artifact_id"] = "tampered"
        with self.assertRaisesRegex(PTSEPublicationError, "EXTERNAL_MANIFEST_PIN_MISMATCH"):
            build_publication_packet(**data)
        for field in ("observation_id", "assessment_id"):
            data = inputs()
            data["receipt_manifest"]["context_receipts"][key(candidate())][field] = "forged"
            with self.assertRaisesRegex(PTSEPublicationError, "CONTEXT_RECEIPT_IDENTITY_MISMATCH"):
                build_publication_packet(**repin(data))
        data = inputs()
        data["receipt_manifest"]["b1_material_receipt"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(PTSEPublicationError, "B1_MATERIAL_RECEIPT_MISMATCH"):
            build_publication_packet(**repin(data))

    def test_source_population_receipt_binds_nonselected_source_columns(self):
        data = inputs()
        data["candidate_rows"][0]["score_rank"] = 99
        with self.assertRaisesRegex(PTSEPublicationError, "CANDIDATE_MATERIAL_RECEIPT_MISMATCH"):
            build_publication_packet(**data)

    def test_missing_receipt_owner_id_and_closed_fields(self):
        for field in ("owner_ref", "artifact_id"):
            data = inputs()
            data["receipt_manifest"]["candidate_population_receipt"][field] = ""
            with self.assertRaises(PTSEPublicationError):
                build_publication_packet(**repin(data))
        data = inputs()
        data["receipt_manifest"]["legacy_w3_complete"] = True
        with self.assertRaisesRegex(PTSEPublicationError, "MANIFEST_FIELDS_NOT_CLOSED"):
            build_publication_packet(**repin(data))

    def test_context_wrong_generation_and_stamp(self):
        for field, value, expected in (("candidate_generation_id", "peg:" + "f" * 64,
                                       "CONTEXT_GENERATION_MISMATCH"),
                                      ("market_session", "2026-09-19", "CONTEXT_STAMP_MISMATCH")):
            p = prospective_new_entry().to_dict()
            if field == "market_session":
                p["observation"][field] = value
                p["observation"].pop("observation_id")
                p["assessment"].pop("observation_id")
            else:
                p["assessment"][field] = value
            p["assessment"].pop("assessment_id")
            art = build_context(p["observation"], p["assessment"])
            with self.assertRaisesRegex(PTSEPublicationError, expected):
                build_publication_packet(**inputs(contexts={key(candidate()): art}))

    def test_context_wrong_b1_assessment_identity_and_raw_bytes(self):
        p = prospective_new_entry().to_dict()
        p["assessment"]["company_id"] = "CO:forged"
        p["assessment"].pop("assessment_id")
        art = build_context(p["observation"], p["assessment"])
        with self.assertRaisesRegex(PTSEPublicationError, "ENROLLMENT_REBUILD_REFUSED"):
            build_publication_packet(**inputs(contexts={key(candidate()): art}))
        data = inputs()
        data["contexts"][key(candidate())] = prospective_new_entry().canonical_bytes + b" "
        with self.assertRaises(PTSEPublicationError):
            build_publication_packet(**data)

    def test_prior_resealed_forgery_refused_semantically(self):
        data = inputs()
        packet = build_publication_packet(**data).packet
        for mutation in ("denominator", "reason", "context_sha", "schema", "extra"):
            p = json.loads(packet)
            if mutation == "denominator":
                p["denominators"]["enrolled"] = 9
            elif mutation == "reason":
                row = p["rows"][0]["enrollment"]
                row["context_reason"] = "FORGED"
                row.pop("enrollment_id")
                row["enrollment_id"] = "ptse-shadow:" + sha(canon(row))
            elif mutation == "context_sha":
                p["context_artifact_sha256s"] = ["f" * 64]
            elif mutation == "schema":
                p["schema"] = "forged"
            else:
                p["legacy_w3_complete"] = True
            with self.subTest(mutation=mutation):
                with self.assertRaises(PTSEPublicationError):
                    preflight_publication(previous_packet=reseal(p), previous_inputs=data, **data)

    def test_strict_false_authority_all_nine_bits_and_publication(self):
        data = inputs()
        packet = build_publication_packet(**data).packet
        for location in ("packet", "enrollment", "publication"):
            for value in (0, True):
                p = json.loads(packet)
                if location == "publication":
                    p["publication_authority"] = value
                else:
                    auth = p["authority"] if location == "packet" else p["rows"][0]["enrollment"]["authority"]
                    auth["rank"] = value
                with self.subTest(location=location, value=value):
                    with self.assertRaises(PTSEPublicationError):
                        validate_publication_packet(reseal(p), **data)
        p = prospective_new_entry().to_dict()
        p["assessment"]["authority"]["rank"] = 0
        data["contexts"][key(candidate())] = canonical_json(p)
        with self.assertRaises(PTSEPublicationError):
            build_publication_packet(**data)

    def test_replay_repeat_changed_added_omitted_and_empty_freeze(self):
        old = inputs([candidate(), candidate("MSFT")], contexts={})
        first = preflight_publication(**old)
        replay = preflight_publication(previous_packet=first.first_packet, previous_inputs=old, **old)
        self.assertEqual(replay.status, "IDENTICAL_REPLAY")
        changes = [(inputs([candidate(), candidate("MSFT")], contexts={}), "CONTENT_CHANGED"),
                   (inputs([candidate(), candidate("MSFT"), candidate("NVDA")], contexts={}), "CANDIDATES_ADDED"),
                   (inputs([candidate()], contexts={}), "CANDIDATES_OMITTED"),
                   (inputs([], contexts={}), "CANDIDATES_OMITTED"),
                   (inputs([candidate("GOOG")], contexts={}), "POPULATION_CHANGED")]
        changes[0][0]["receipt_manifest"]["candidate_population_receipt"]["artifact_id"] = "corrected-source"
        repin(changes[0][0])
        for new, reason in changes:
            result = preflight_publication(previous_packet=first.first_packet, previous_inputs=old, **new)
            self.assertEqual(result.status, "REVISION_REFUSED")
            self.assertEqual(result.reason, reason)
            self.assertEqual(result.first_packet, first.first_packet)
            self.assertNotEqual(result.lineage_first_packet_id, result.lineage_candidate_packet_id)

    def test_source_content_revision_and_independent_prior_custody(self):
        old = inputs()
        first = preflight_publication(**old)
        changed = inputs([candidate(prophet_score=12.0)])
        result = preflight_publication(previous_packet=first.first_packet, previous_inputs=old, **changed)
        self.assertEqual(result.reason, "CONTENT_CHANGED")
        self.assertEqual(result.first_packet, first.first_packet)
        with self.assertRaisesRegex(PTSEPublicationError, "INDEPENDENT_PREVIOUS_SOURCE_INPUTS_REQUIRED"):
            preflight_publication(previous_packet=first.first_packet, **old)
        with self.assertRaises(PTSEPublicationError):
            preflight_publication(previous_packet=first.first_packet, previous_inputs=changed, **changed)

    def test_no_legacy_w3_completion_argument_and_inputs_unchanged(self):
        data = inputs()
        manifest_before = canon(data["receipt_manifest"])
        source_before = canon(data["candidate_rows"])
        build_publication_packet(**data)
        self.assertEqual(canon(data["receipt_manifest"]), manifest_before)
        self.assertEqual(canon(data["candidate_rows"]), source_before)
        with self.assertRaises(TypeError):
            preflight_publication(legacy_w3_complete=True, **data)


if __name__ == "__main__":
    unittest.main()
