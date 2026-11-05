#!/usr/bin/env python3
"""Discriminating tests for native_publication_origin (stdlib unittest only).

Run:  python3 -m pytest tests/test_ci_native_publication_origin.py -q
"""

from __future__ import annotations

import copy
import hashlib
import json
import unittest

from scripts.ci import native_publication_origin as npo
from scripts.ci.native_publication_origin import (
    CREDENTIAL_ORIGIN,
    MAX_DOCUMENT_BYTES,
    SCHEMA_ID,
    MalformedOriginError,
    OriginIdentityMismatchError,
    OversizedOriginError,
    decode_origin,
    encode_origin,
    origin_sha256,
)

REPO_FULL_NAME = "mastermindx-market-intelligence/macro"
REPOSITORY_ID = 839467
WORKFLOW_PATH = ".github/workflows/native-publication.yml"
WORKFLOW_REF = "%s/%s@refs/heads/main" % (REPO_FULL_NAME, WORKFLOW_PATH)
WORKFLOW_SHA = "fc66c6be432d1d62acc832b004b79be3c5a88867"
SOURCE_HEAD = "7c3e1d90ab4f52e6b8d0c3a95e17f4280d6b9c15"
CANDIDATE_TREE = "2b8f04e6d1c7a93f5e0b2d8471c6a90fe3d5b824"
PROJECTION_SHA256 = "5f05e5ec6de05752646c7dff4debaa5eee4535f73a3a97eac413895e4cb472c7"

# Deliberately malformed "token-shaped" input values: refused outright, and
# never reflected back in refusal reasons.
_TOKENISH = "ghp_" + "a" * 36


def origin(**over):
    """A fully valid producer-origin document bound to REPO_FULL_NAME."""
    base = {
        "schema": SCHEMA_ID,
        "repository_id": REPOSITORY_ID,
        "producer_origin": {
            "producer_run_id": 21459873001,
            "producer_run_attempt": 3,
            "workflow_path": WORKFLOW_PATH,
            "workflow_ref": WORKFLOW_REF,
            "workflow_sha": WORKFLOW_SHA,
            "publishing_job": "publish-native-artifact",
            "publishing_step": "native_publication_stage",
            "credential_origin": CREDENTIAL_ORIGIN,
            "pr_number": 4242,
            "published_source_head": SOURCE_HEAD,
            "selected_target": "main",
            "original_generation": "012345abcdef",
            "candidate_tree": CANDIDATE_TREE,
            "projection_sha256": PROJECTION_SHA256,
            "pr_creation_user_id": 1905531,
            "pr_creation_login": "macro-publisher-bot",
        },
    }
    producer_over = over.pop("producer_origin", None) or {}
    base["producer_origin"].update(producer_over)
    base.update(over)
    return base


def encode(mapping, full_name=REPO_FULL_NAME, repo_id=REPOSITORY_ID):
    return encode_origin(
        mapping, repository_full_name=full_name, repository_id=repo_id
    )


def decode(payload, full_name=REPO_FULL_NAME, repo_id=REPOSITORY_ID):
    return decode_origin(
        payload, repository_full_name=full_name, repository_id=repo_id
    )


class ContractShapeTests(unittest.TestCase):
    def test_field_set_is_exactly_the_document_contract(self):
        # Locks the contract: no collector, registry, token-discovery or
        # admission field may join the producer-origin record.
        self.assertEqual(
            set(npo._PRODUCER_ORIGIN_FIELDS),
            {
                "producer_run_id",
                "producer_run_attempt",
                "workflow_path",
                "workflow_ref",
                "workflow_sha",
                "publishing_job",
                "publishing_step",
                "credential_origin",
                "pr_number",
                "published_source_head",
                "selected_target",
                "original_generation",
                "candidate_tree",
                "projection_sha256",
                "pr_creation_user_id",
                "pr_creation_login",
            },
        )

    def test_schema_credential_and_targets_are_the_exact_literals(self):
        self.assertEqual(SCHEMA_ID, "mastermind.ci-proof-producer-origin.v1")
        self.assertEqual(CREDENTIAL_ORIGIN, "GITHUB_TOKEN")
        self.assertEqual(frozenset(npo.SELECTED_TARGETS), {"main", "codex/merge-queue-pilot"})
        self.assertEqual(MAX_DOCUMENT_BYTES, 4096)

    def test_module_declares_syntax_not_admission_scope(self):
        # The module must clearly note that it validates syntax/identity only.
        doc = " ".join((npo.__doc__ or "").split())  # reflow-tolerant
        self.assertIn("validate syntax and identity binding ONLY", doc)
        self.assertIn("not authenticate provenance", doc)

    def test_module_reads_no_environment_or_actor_sources(self):
        for banned in ("os", "getenv", "subprocess", "socket", "http", "requests", "netrc"):
            self.assertNotIn(banned, vars(npo), msg=banned)

    def test_identity_arguments_are_keyword_only(self):
        with self.assertRaises(TypeError):
            encode_origin(origin(), REPO_FULL_NAME, REPOSITORY_ID)
        with self.assertRaises(TypeError):
            decode_origin(b"{}", REPO_FULL_NAME, REPOSITORY_ID)


class RoundtripTests(unittest.TestCase):
    def test_main_target_roundtrip_is_substantive(self):
        doc = origin()
        encoded = encode(doc)
        self.assertIsInstance(encoded, bytes)
        decoded = decode(encoded)
        self.assertEqual(decoded, doc)
        self.assertEqual(decoded["schema"], SCHEMA_ID)
        self.assertEqual(decoded["repository_id"], REPOSITORY_ID)
        self.assertEqual(decoded["producer_origin"]["workflow_ref"], WORKFLOW_REF)
        self.assertEqual(decoded["producer_origin"]["selected_target"], "main")
        self.assertIn(b'"selected_target":"main"', encoded)

    def test_pilot_target_roundtrip_is_substantive(self):
        doc = origin(producer_origin={"selected_target": "codex/merge-queue-pilot"})
        encoded = encode(doc)
        decoded = decode(encoded)
        self.assertEqual(decoded, doc)
        self.assertIn(b'"selected_target":"codex/merge-queue-pilot"', encoded)
        # The two admitted targets are genuinely distinct documents.
        self.assertNotEqual(encoded, encode(origin()))

    def test_yaml_workflow_suffix_roundtrips(self):
        doc = origin(
            producer_origin={
                "workflow_path": ".github/workflows/native-publication.yaml",
                "workflow_ref": "%s/.github/workflows/native-publication.yaml@refs/heads/main"
                % REPO_FULL_NAME,
            }
        )
        self.assertEqual(decode(encode(doc)), doc)

    def test_encoding_is_deterministic_across_key_insertion_order(self):
        forward = encode(origin())
        reversed_mapping = {
            key: origin()[key] for key in reversed(list(origin().keys()))
        }
        self.assertEqual(encode(reversed_mapping), forward)
        self.assertEqual(encode(copy.deepcopy(origin())), forward)

    def test_encoding_is_compact_sorted_and_independent_of_input_mutation(self):
        doc = origin()
        snapshot = copy.deepcopy(doc)
        encoded = encode(doc)
        self.assertEqual(doc, snapshot)  # pure: caller mapping never mutated
        text = encoded.decode("utf-8")
        self.assertTrue(text.startswith("{"))
        self.assertTrue(text.endswith("}"))
        self.assertNotIn(", ", text)
        self.assertNotIn(": ", text)
        self.assertNotIn("\n", text)
        # Canonical sorted key order at the top level.
        self.assertLess(text.index('"producer_origin"'), text.index('"repository_id"'))
        self.assertLess(text.index('"repository_id"'), text.index('"schema"'))

    def test_main_document_has_stable_byte_exact_canonical_form(self):
        expected = (
            '{"producer_origin":{'
            '"candidate_tree":"%s",'
            '"credential_origin":"GITHUB_TOKEN",'
            '"original_generation":"012345abcdef",'
            '"pr_creation_login":"macro-publisher-bot",'
            '"pr_creation_user_id":1905531,'
            '"pr_number":4242,'
            '"producer_run_attempt":3,'
            '"producer_run_id":21459873001,'
            '"projection_sha256":"%s",'
            '"published_source_head":"%s",'
            '"publishing_job":"publish-native-artifact",'
            '"publishing_step":"native_publication_stage",'
            '"selected_target":"main",'
            '"workflow_path":".github/workflows/native-publication.yml",'
            '"workflow_ref":"%s",'
            '"workflow_sha":"%s"},'
            '"repository_id":%d,'
            '"schema":"mastermind.ci-proof-producer-origin.v1"}'
        ) % (
            CANDIDATE_TREE,
            PROJECTION_SHA256,
            SOURCE_HEAD,
            WORKFLOW_REF,
            WORKFLOW_SHA,
            REPOSITORY_ID,
        )
        self.assertEqual(encode(origin()).decode("utf-8"), expected)

    def test_origin_sha256_is_stable_and_matches_hashlib(self):
        first = encode(origin())
        second = encode(origin())
        self.assertEqual(first, second)
        digest = origin_sha256(first)
        self.assertEqual(digest, hashlib.sha256(first).hexdigest())
        self.assertEqual(digest, origin_sha256(second))
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, origin_sha256(bytearray(first)))

    def test_decode_accepts_noncanonical_but_valid_json(self):
        doc = origin()
        decoded = decode(json.dumps(doc).encode("utf-8"))  # spaces, insertion order
        self.assertEqual(decoded, doc)

    def test_encoding_stays_under_the_document_cap(self):
        self.assertLess(len(encode(origin())), MAX_DOCUMENT_BYTES)
        self.assertLess(
            len(encode(origin(producer_origin={"selected_target": "codex/merge-queue-pilot"}))),
            MAX_DOCUMENT_BYTES,
        )


class IdentityBindingTests(unittest.TestCase):
    def test_wrong_expected_repository_id_refuses(self):
        with self.assertRaises(OriginIdentityMismatchError):
            encode(origin(), full_name=REPO_FULL_NAME, repo_id=REPOSITORY_ID + 1)

    def test_wrong_expected_full_name_refuses_on_encode(self):
        with self.assertRaises(OriginIdentityMismatchError):
            encode(origin(), full_name="other-owner/macro", repo_id=REPOSITORY_ID)

    def test_decode_binding_refuses_a_wellformed_foreign_document(self):
        encoded = encode(origin())
        with self.assertRaises(OriginIdentityMismatchError):
            decode(encoded, full_name="other-owner/macro", repo_id=REPOSITORY_ID)
        with self.assertRaises(OriginIdentityMismatchError):
            decode(encoded, full_name=REPO_FULL_NAME, repo_id=REPOSITORY_ID - 1)

    def test_crossrepo_workflow_ref_refuses_without_echo(self):
        foreign = "other-owner/macro/%s@refs/heads/main" % WORKFLOW_PATH
        with self.assertRaises(OriginIdentityMismatchError) as caught:
            encode(origin(producer_origin={"workflow_ref": foreign}))
        self.assertNotIn("other-owner", caught.exception.reason)
        self.assertNotIn(foreign, caught.exception.reason)

    def test_expected_full_name_argument_itself_must_be_wellformed(self):
        for bad in ("mastermindx-market-intelligence", "bad name/macro", "..//macro"):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(), full_name=bad, repo_id=REPOSITORY_ID)

    def test_document_repository_id_type_is_checked_before_binding(self):
        with self.assertRaises(MalformedOriginError):
            encode(origin(repository_id=True))
        with self.assertRaises(MalformedOriginError):
            encode(origin(repository_id="839467"))


class WorkflowRefAndPathTests(unittest.TestCase):
    def test_non_main_ref_tail_refuses(self):
        for tail in ("refs/heads/develop", "refs/tags/v1", "main", ""):
            with self.subTest(tail=tail):
                ref = "%s/%s@%s" % (REPO_FULL_NAME, WORKFLOW_PATH, tail)
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={"workflow_ref": ref}))

    def test_ref_without_at_separator_refuses(self):
        with self.assertRaises(MalformedOriginError):
            encode(
                origin(
                    producer_origin={
                        "workflow_ref": "%s/%s" % (REPO_FULL_NAME, WORKFLOW_PATH)
                    }
                )
            )

    def test_ref_path_must_match_workflow_path(self):
        other = ".github/workflows/other.yml"
        with self.assertRaises(MalformedOriginError):
            encode(
                origin(
                    producer_origin={
                        "workflow_path": WORKFLOW_PATH,
                        "workflow_ref": "%s/%s@refs/heads/main" % (REPO_FULL_NAME, other),
                    }
                )
            )

    def test_workflow_path_outside_the_workflows_dir_refuses(self):
        for bad in (
            "site/theme.js",
            ".github/workflow/native-publication.yml",
            ".github/workflows/sub/inner.yml",
            ".github/workflows/native-publication.txt",
            ".github/workflows/evil name.yml",
            ".github/workflows/../evil.yml",
            ".github/workflows/.hidden.yml",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError) as caught:
                    encode(origin(producer_origin={"workflow_path": bad}))
                self.assertNotIn(bad, caught.exception.reason)

    def test_workflow_path_non_string_refuses(self):
        with self.assertRaises(MalformedOriginError):
            encode(origin(producer_origin={"workflow_path": 7}))


class SafeTextTests(unittest.TestCase):
    def test_injected_newline_refuses_and_is_never_reflected(self):
        for field in ("publishing_job", "publishing_step", "original_generation"):
            with self.subTest(field=field):
                payload = "ok\nEvil-Header: injected"
                with self.assertRaises(MalformedOriginError) as caught:
                    encode(origin(producer_origin={field: payload}))
                self.assertNotIn("Evil-Header", caught.exception.reason)
                self.assertNotIn("\n", caught.exception.reason)

    def test_carriage_return_tab_and_non_ascii_refuse(self):
        for field in ("publishing_job", "publishing_step", "original_generation"):
            for payload in ("ok\rcarriage", "ok\ttab", "g\xe9n\xe9ration", "ok\x00nul"):
                with self.subTest(field=field, payload=payload):
                    with self.assertRaises(MalformedOriginError):
                        encode(origin(producer_origin={field: payload}))

    def test_empty_blank_overlong_and_non_string_safe_text_refuses(self):
        for field in ("publishing_job", "publishing_step", "original_generation"):
            for payload in ("", "   ", " x", "x ", "x" * 129, 7, None):
                with self.subTest(field=field, payload=payload):
                    with self.assertRaises(MalformedOriginError):
                        encode(origin(producer_origin={field: payload}))

    def test_max_length_safe_text_is_accepted(self):
        doc = origin(producer_origin={"publishing_job": "g" * 128})
        self.assertEqual(decode(encode(doc))["producer_origin"]["publishing_job"], "g" * 128)


class IdentityTypeTests(unittest.TestCase):
    def test_bool_identity_fields_refuse(self):
        for field in (
            "producer_run_id",
            "producer_run_attempt",
            "pr_number",
            "pr_creation_user_id",
        ):
            with self.subTest(field=field):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: True}))
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: False}))

    def test_numeric_string_identity_fields_refuse(self):
        for field, value in (
            ("producer_run_id", "21459873001"),
            ("producer_run_attempt", "3"),
            ("pr_number", "4242"),
            ("pr_creation_user_id", "1905531"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: value}))

    def test_float_identity_fields_refuse(self):
        for field, value in (
            ("producer_run_id", 21459873001.0),
            ("producer_run_attempt", 3.0),
            ("pr_number", 4242.0),
            ("pr_creation_user_id", 1905531.0),
        ):
            with self.subTest(field=field):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: value}))

    def test_zero_and_negative_identity_fields_refuse(self):
        for field, value in (
            ("producer_run_id", 0),
            ("pr_number", -4242),
            ("pr_creation_user_id", 0),
            ("producer_run_attempt", -1),
        ):
            with self.subTest(field=field):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: value}))


class SchemaAndKeySetTests(unittest.TestCase):
    def test_wrong_schema_version_refuses(self):
        with self.assertRaises(MalformedOriginError) as caught:
            encode(origin(schema="mastermind.ci-proof-producer-origin.v2"))
        # The expected literal is named; the refused caller value is not echoed.
        self.assertIn(".v1", caught.exception.reason)
        self.assertNotIn(".v2", caught.exception.reason)

    def test_missing_top_level_and_producer_fields_refuse(self):
        for path in ("schema", "repository_id", "producer_origin"):
            doc = origin()
            del doc[path]
            with self.subTest(path=path):
                with self.assertRaises(MalformedOriginError):
                    encode(doc)
        for field in (
            "producer_run_id",
            "producer_run_attempt",
            "workflow_path",
            "workflow_ref",
            "workflow_sha",
            "publishing_job",
            "publishing_step",
            "credential_origin",
            "pr_number",
            "published_source_head",
            "selected_target",
            "original_generation",
            "candidate_tree",
            "projection_sha256",
            "pr_creation_user_id",
            "pr_creation_login",
        ):
            doc = origin()
            del doc["producer_origin"][field]
            with self.subTest(field=field):
                with self.assertRaises(MalformedOriginError):
                    encode(doc)

    def test_extra_keys_refuse_without_echoing_values(self):
        doc = origin()
        doc["producer_origin"]["actor_login"] = "someone-secret"
        with self.assertRaises(MalformedOriginError) as caught:
            encode(doc)
        self.assertIn("extra", caught.exception.reason)
        self.assertNotIn("someone-secret", caught.exception.reason)

        doc = origin()
        doc["credential"] = "sealed-value"
        with self.assertRaises(MalformedOriginError) as caught:
            encode(doc)
        self.assertNotIn("sealed-value", caught.exception.reason)

    def test_producer_origin_and_document_must_be_objects(self):
        with self.assertRaises(MalformedOriginError):
            encode(dict(origin(), producer_origin=[]))
        with self.assertRaises(MalformedOriginError):
            encode("not-a-mapping")
        with self.assertRaises(MalformedOriginError):
            decode(b"[]")


class HashFormatTests(unittest.TestCase):
    def test_workflow_sha_format_refuses(self):
        field = "workflow_sha"
        for bad in ("f" * 39, "f" * 41, "F" * 40, "g" * 40, 123, None):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: bad}))

    def test_published_source_head_format_refuses(self):
        for bad in ("z" * 40, "7c3e1d90", SOURCE_HEAD.upper()):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={"published_source_head": bad}))

    def test_candidate_tree_format_refuses(self):
        for bad in ("f" * 39 + "G", "2b8f", "e" * 40 + "x"):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={"candidate_tree": bad}))

    def test_projection_sha256_format_refuses(self):
        field = "projection_sha256"
        for bad in ("a" * 63, "a" * 65, PROJECTION_SHA256.upper(), "g" * 64, 5):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={field: bad}))


class CredentialAndTargetTests(unittest.TestCase):
    def test_credential_other_than_github_token_refuses_without_echo(self):
        for bad in ("SEALED_BOT_PAT", _TOKENISH, "github_token", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError) as caught:
                    encode(origin(producer_origin={"credential_origin": bad}))
                if bad:
                    self.assertNotIn(bad, caught.exception.reason)

    def test_only_main_and_pilot_targets_are_admitted_shapes(self):
        for bad in ("release", "main-lock", "staging", "", None):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError) as caught:
                    encode(origin(producer_origin={"selected_target": bad}))
                if bad:
                    self.assertNotIn(bad, caught.exception.reason)

    def test_pr_creation_login_format_refuses(self):
        for bad in ("-bot", "has space", "a" * 40, "bad@login", "", None, 5):
            with self.subTest(bad=bad):
                with self.assertRaises(MalformedOriginError):
                    encode(origin(producer_origin={"pr_creation_login": bad}))


class DecodeDocumentTests(unittest.TestCase):
    def test_duplicate_json_keys_refuse(self):
        doc = json.dumps(origin(), separators=(",", ":"))
        poisoned = doc.replace("{", '{"repository_id":%d,' % REPOSITORY_ID, 1)
        self.assertNotEqual(poisoned, doc)
        with self.assertRaises(MalformedOriginError) as caught:
            decode(poisoned.encode("utf-8"))
        self.assertIn("duplicate", caught.exception.reason)

        marker = '"producer_origin":{'
        inner = doc.index(marker) + len(marker)
        poisoned = doc[:inner] + '"pr_number":4242,' + doc[inner:]
        with self.assertRaises(MalformedOriginError):
            decode(poisoned.encode("utf-8"))

    def test_oversized_document_refuses_before_any_value_check(self):
        encoded = encode(origin())
        self.assertLess(len(encoded), MAX_DOCUMENT_BYTES)
        padded = b"{ " + b" " * MAX_DOCUMENT_BYTES + encoded[1:]
        self.assertGreater(len(padded), MAX_DOCUMENT_BYTES)
        with self.assertRaises(OversizedOriginError):
            decode(padded)
        with self.assertRaises(OversizedOriginError):
            decode(b"x" * (MAX_DOCUMENT_BYTES + 1))

    def test_document_at_or_under_the_cap_passes_the_size_gate(self):
        # Only documents strictly over MAX_DOCUMENT_BYTES hit the size gate.
        payload = json.dumps(origin(), separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(payload), MAX_DOCUMENT_BYTES)
        self.assertEqual(decode(payload), origin())

    def test_invalid_json_and_invalid_utf8_refuse(self):
        with self.assertRaises(MalformedOriginError):
            decode(b"not json")
        with self.assertRaises(MalformedOriginError):
            decode(b'{"schema": "\xff\xfe"}')
        with self.assertRaises(MalformedOriginError):
            decode(b"")
        with self.assertRaises(MalformedOriginError):
            decode("str not bytes")  # str payload refuses

    def test_origin_sha256_refuses_non_bytes(self):
        with self.assertRaises(MalformedOriginError):
            origin_sha256("text")


class NoSecretReflectionTests(unittest.TestCase):
    def test_refusal_reasons_never_echo_tokenish_input_values(self):
        cases = (
            ("credential_origin", _TOKENISH),
            ("pr_creation_login", "bot-" + _TOKENISH),
            ("original_generation", "gen\n" + _TOKENISH),
            ("publishing_step", _TOKENISH + "\n/step"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                with self.assertRaises(MalformedOriginError) as caught:
                    encode(origin(producer_origin={field: value}))
                reason = caught.exception.reason
                self.assertNotIn(_TOKENISH, reason)
                self.assertNotIn(value, reason)
                self.assertEqual(MalformedOriginError.code, "MALFORMED_ORIGIN")


if __name__ == "__main__":
    unittest.main()


class ProviderIdentityIntegrationTests(unittest.TestCase):
    def test_real_github_token_creator_login_roundtrips_without_granting_authority(self):
        doc = origin(producer_origin={"pr_creation_login": "github-actions[bot]"})
        self.assertEqual(decode(encode(doc))["producer_origin"]["pr_creation_login"], "github-actions[bot]")

    def test_bot_suffix_is_exact_not_freeform_payload(self):
        for bad in ("github-actions[bot]suffix", "github-actions[Bot]", "github-actions[bot]\n", "[bot]"):
            with self.subTest(bad=bad), self.assertRaises(MalformedOriginError):
                encode(origin(producer_origin={"pr_creation_login": bad}))

    def test_final_pointer_generation_is_exact_twelve_hex(self):
        for bad in ("2026-11-05T09:14:07Z", "g" * 12, "a" * 11, "a" * 13, "A" * 12, True, None):
            with self.subTest(bad=bad), self.assertRaises(MalformedOriginError):
                encode(origin(producer_origin={"original_generation": bad}))
