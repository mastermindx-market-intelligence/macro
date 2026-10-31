"""Deterministic tests for the OwnerBundle identity-map codec.

Tests exercise the installed adapter helpers. Run with::

    python3 -m pytest tests/test_theme_state_bundle_codec.py -q
"""

from __future__ import annotations

import copy
import json
import math
from types import SimpleNamespace
from unittest import mock
import unittest

from engine.neuralweb import theme_state_adapter as adapter
codec = SimpleNamespace(
    V1=adapter.BUNDLE_SCHEMA, V2=adapter.COMPACT_BUNDLE_SCHEMA,
    IDENTITY_REF_KEY=adapter._OWNER_IDENTITY_REF, TABLE_FIELD=adapter._OWNER_IDENTITY_TABLES,
    OwnerBundleCodecError=adapter._OwnerBundleCodecError,
    canonical_json=adapter._owner_codec_json, canonical_sha256=adapter._owner_codec_sha,
    encode=adapter._compact_owner_payload, expand=adapter._expand_owner_payload,
)


def canon_bytes(value) -> bytes:
    return codec.canonical_json(value).encode("utf-8")


def build_identity(seed: str, entries: int) -> dict:
    return {
        "co:{}-{}".format(seed, i): {
            "availability": "AVAILABLE",
            "value": {"security_id": "SEC:{}:{}".format(seed, i), "score": i + 0.5},
        }
        for i in range(entries)
    }


def base_payload() -> dict:
    """v1 fixture: unicode, nulls, floats, heterogeneous maps, shared objects."""
    shared_map = {
        "co:Ω": {"availability": "AVAILABLE", "value": {"security_id": "SEC:Ω", "note": None}},
        "thème:é": {
            "availability": "LIMITED",
            "value": {"security_id": "SEC:É", "ratio": 0.1, "tiny": 2.5e-08, "count": 7},
        },
        "co:empty-value": {"availability": "MISSING", "value": None},
    }
    other_map = {
        "co:B": {
            "availability": "UNAVAILABLE",
            "value": {"security_id": "SEC:B", "tags": ["x", None, True, 3]},
        }
    }
    equal_copy = json.loads(json.dumps(shared_map))  # equal value, distinct object
    return {
        "schema": codec.V1,
        "query": {"known_at": "2026-10-19T00:00:00Z", "q": "macro-Ω"},
        "subjects": {
            "theme:x": {"native_reads": {"identity": shared_map, "ontology": {"depth": 2}}},
            "theme:y": {"native_reads": {"identity": shared_map, "ontology": {"value": []}}},
            "theme:z": {"native_reads": {"identity": other_map, "ontology": {}}},
            "theme:w": {"native_reads": {"identity": equal_copy, "ontology": None}},
        },
        "sources": {"x": {"bytes_b64": "eA==", "sha256": "old"}},
    }


def v2_with_subject_identity(subject_identity) -> dict:
    """Hand-built v2 payload with one subject, for malformed-ref cases."""
    digest = codec.canonical_sha256(subject_identity)
    return {
        "schema": codec.V2,
        "subjects": {
            "theme:x": {"native_reads": {"identity": {codec.IDENTITY_REF_KEY: digest}}}
        },
        codec.TABLE_FIELD: {digest: subject_identity},
    }


def assert_raises(self, action, *fragments):
    with self.assertRaises(codec.OwnerBundleCodecError) as ctx:
        action()
    message = str(ctx.exception)
    for fragment in fragments:
        self.assertIn(fragment, message)
    return message


class RoundtripTest(unittest.TestCase):
    def test_lossless_roundtrip_heterogeneous(self):
        payload = base_payload()
        encoded = codec.encode(payload)
        expanded = codec.expand(encoded)
        self.assertEqual(expanded, payload)
        self.assertEqual(canon_bytes(expanded), canon_bytes(payload))
        self.assertEqual(expanded["schema"], codec.V1)
        self.assertNotIn(codec.TABLE_FIELD, expanded)
        # Per-subject heterogeneous maps survive verbatim.
        for node, subject in payload["subjects"].items():
            self.assertEqual(
                expanded["subjects"][node]["native_reads"]["identity"],
                subject["native_reads"]["identity"],
            )
        # Unrelated fields, clocks and hashes are preserved.
        self.assertEqual(expanded["query"], payload["query"])
        self.assertEqual(expanded["sources"], payload["sources"])
        self.assertEqual(
            expanded["subjects"]["theme:x"]["native_reads"]["ontology"], {"depth": 2}
        )

    def test_encode_shape(self):
        encoded = codec.encode(base_payload())
        self.assertEqual(encoded["schema"], codec.V2)
        table = encoded[codec.TABLE_FIELD]
        self.assertIsInstance(table, dict)
        digests = set(table)
        # shared_map (x, y) + its equal copy (w) dedupe to one digest, plus other_map.
        self.assertEqual(len(digests), 2)
        for digest, value in table.items():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(codec.canonical_sha256(value), digest)
        for node, subject in encoded["subjects"].items():
            ref = subject["native_reads"]["identity"]
            self.assertEqual(set(ref), {codec.IDENTITY_REF_KEY})
            self.assertIn(ref[codec.IDENTITY_REF_KEY], digests)

    def test_distinct_maps_remain_distinct(self):
        map_a = build_identity("a", 2)
        map_b = build_identity("b", 2)  # different values, same shape
        payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:a": {"native_reads": {"identity": map_a}},
                "theme:b": {"native_reads": {"identity": map_b}},
            },
        }
        encoded = codec.encode(payload)
        self.assertEqual(len(encoded[codec.TABLE_FIELD]), 2)
        expanded = codec.expand(encoded)
        self.assertEqual(expanded, payload)
        self.assertEqual(
            expanded["subjects"]["theme:a"]["native_reads"]["identity"], map_a
        )
        self.assertEqual(
            expanded["subjects"]["theme:b"]["native_reads"]["identity"], map_b
        )

    def test_equal_but_distinct_maps_dedupe(self):
        map_a = build_identity("same", 3)
        map_b = copy.deepcopy(map_a)
        payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:a": {"native_reads": {"identity": map_a}},
                "theme:b": {"native_reads": {"identity": map_b}},
            },
        }
        encoded = codec.encode(payload)
        self.assertEqual(len(encoded[codec.TABLE_FIELD]), 1)
        self.assertEqual(codec.expand(encoded), payload)


class LegacyTest(unittest.TestCase):
    def test_legacy_expand_is_fresh_equal_copy(self):
        payload = base_payload()
        expanded = codec.expand(payload)
        self.assertEqual(expanded, payload)
        self.assertIsNot(expanded, payload)
        for node, subject in payload["subjects"].items():
            expanded_identity = expanded["subjects"][node]["native_reads"]["identity"]
            self.assertEqual(expanded_identity, subject["native_reads"]["identity"])
            self.assertIsNot(expanded_identity, subject["native_reads"]["identity"])
        # Mutating the expansion cannot leak into the legacy input.
        expanded["subjects"]["theme:x"]["native_reads"]["identity"]["co:Ω"]["availability"] = "X"
        self.assertEqual(
            payload["subjects"]["theme:x"]["native_reads"]["identity"]["co:Ω"]["availability"],
            "AVAILABLE",
        )

    def test_legacy_with_table_field_refuses(self):
        payload = base_payload()
        payload[codec.TABLE_FIELD] = {}
        assert_raises(self, lambda: codec.expand(payload), "identity_read_tables")


class SharingTest(unittest.TestCase):
    def test_expand_shares_decoded_identity_object(self):
        payload = base_payload()
        expanded = codec.expand(codec.encode(payload))
        identity_x = expanded["subjects"]["theme:x"]["native_reads"]["identity"]
        identity_y = expanded["subjects"]["theme:y"]["native_reads"]["identity"]
        identity_w = expanded["subjects"]["theme:w"]["native_reads"]["identity"]
        self.assertIs(identity_y, identity_x)  # same reference in v2
        self.assertIs(identity_w, identity_x)  # equal copy deduped to same digest
        identity_z = expanded["subjects"]["theme:z"]["native_reads"]["identity"]
        self.assertIsNot(identity_z, identity_x)
        # Shared object must not alias the caller's structures.
        self.assertIsNot(identity_x, payload["subjects"]["theme:x"]["native_reads"]["identity"])
        self.assertIsNot(
            identity_x,
            codec.encode(payload)[codec.TABLE_FIELD][
                codec.canonical_sha256(payload["subjects"]["theme:x"]["native_reads"]["identity"])
            ],
        )

    def test_encode_does_not_alias_input_identity(self):
        payload = base_payload()
        encoded = codec.encode(payload)
        for node, subject in payload["subjects"].items():
            self.assertIsNot(
                encoded["subjects"][node]["native_reads"]["identity"],
                subject["native_reads"]["identity"],
            )
            self.assertIsNot(
                encoded[codec.TABLE_FIELD][
                    encoded["subjects"][node]["native_reads"]["identity"][
                        codec.IDENTITY_REF_KEY
                    ]
                ],
                subject["native_reads"]["identity"],
            )


class NonMutationTest(unittest.TestCase):
    def test_encode_does_not_mutate_input(self):
        payload = base_payload()
        snapshot = copy.deepcopy(payload)
        codec.encode(payload)
        self.assertEqual(payload, snapshot)

    def test_expand_v2_does_not_mutate_input(self):
        payload = base_payload()
        encoded = codec.encode(payload)
        snapshot = copy.deepcopy(encoded)
        expanded = codec.expand(encoded)
        self.assertEqual(encoded, snapshot)
        self.assertEqual(expanded, payload)
        # The expanded maps are not the table's own objects either.
        digest = encoded["subjects"]["theme:x"]["native_reads"]["identity"][
            codec.IDENTITY_REF_KEY
        ]
        self.assertIsNot(
            expanded["subjects"]["theme:x"]["native_reads"]["identity"],
            encoded[codec.TABLE_FIELD][digest],
        )

    def test_expand_v1_does_not_mutate_input(self):
        payload = base_payload()
        snapshot = copy.deepcopy(payload)
        codec.expand(payload)
        self.assertEqual(payload, snapshot)


class EmptyScopeTest(unittest.TestCase):
    def test_empty_subjects(self):
        payload = {"schema": codec.V1, "subjects": {}}
        encoded = codec.encode(payload)
        self.assertEqual(encoded["schema"], codec.V2)
        self.assertEqual(encoded[codec.TABLE_FIELD], {})
        self.assertEqual(codec.expand(encoded), payload)
        self.assertEqual(codec.expand(payload), payload)

    def test_empty_identity_maps(self):
        empty_a: dict = {}
        empty_b: dict = {}
        self.assertIsNot(empty_a, empty_b)
        payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:a": {"native_reads": {"identity": empty_a, "ontology": {}}},
                "theme:b": {"native_reads": {"identity": empty_b}},
            },
        }
        encoded = codec.encode(payload)
        self.assertEqual(len(encoded[codec.TABLE_FIELD]), 1)
        expanded = codec.expand(encoded)
        self.assertEqual(expanded, payload)
        self.assertIs(
            expanded["subjects"]["theme:a"]["native_reads"]["identity"],
            expanded["subjects"]["theme:b"]["native_reads"]["identity"],
        )


class RefusalTest(unittest.TestCase):
    def test_malformed_refs(self):
        digest = codec.canonical_sha256({"co:a": {}})
        valid = {
            "schema": codec.V2,
            "subjects": {
                "theme:x": {
                    "native_reads": {"identity": {codec.IDENTITY_REF_KEY: digest}}
                }
            },
            codec.TABLE_FIELD: {digest: {"co:a": {}}},
        }

        def variant(ref):
            payload = copy.deepcopy(valid)
            payload["subjects"]["theme:x"]["native_reads"]["identity"] = ref
            return payload

        cases = [
            digest,  # bare string instead of reference object
            {codec.IDENTITY_REF_KEY: digest, "extra": 1},  # extra key
            {},  # missing key
            {codec.IDENTITY_REF_KEY: digest.upper()},  # not lowercase
            {codec.IDENTITY_REF_KEY: digest[:63]},  # wrong length
            {codec.IDENTITY_REF_KEY: 123},  # non-string
            {codec.IDENTITY_REF_KEY: True},  # bool
            {"$other_ref": digest},  # unknown reference field
        ]
        for ref in cases:
            assert_raises(self, lambda ref=ref: codec.expand(variant(ref)))

    def test_digest_mismatch_refuses(self):
        encoded = codec.encode(base_payload())
        digest = next(iter(encoded[codec.TABLE_FIELD]))
        encoded[codec.TABLE_FIELD][digest]["tampered"] = {}
        assert_raises(self, lambda: codec.expand(encoded), "digest mismatch")

    def test_orphan_reference_refuses(self):
        encoded = codec.encode(base_payload())
        digest = encoded["subjects"]["theme:x"]["native_reads"]["identity"][
            codec.IDENTITY_REF_KEY
        ]
        del encoded[codec.TABLE_FIELD][digest]
        assert_raises(
            self, lambda: codec.expand(encoded), "unknown identity digest"
        )

    def test_orphan_table_entry_refuses(self):
        encoded = codec.encode(base_payload())
        ghost = {"co:ghost": {"availability": "AVAILABLE", "value": None}}
        encoded[codec.TABLE_FIELD][codec.canonical_sha256(ghost)] = ghost
        assert_raises(
            self, lambda: codec.expand(encoded), "never referenced"
        )

    def test_malformed_tables(self):
        encoded = codec.encode(base_payload())

        missing = codec.encode(base_payload())
        del missing[codec.TABLE_FIELD]
        assert_raises(self, lambda: codec.expand(missing), "identity_read_tables")

        not_dict = codec.encode(base_payload())
        not_dict[codec.TABLE_FIELD] = []
        assert_raises(self, lambda: codec.expand(not_dict), "identity_read_tables")

        bad_key = codec.encode(base_payload())
        digest, value = next(iter(bad_key[codec.TABLE_FIELD].items()))
        del bad_key[codec.TABLE_FIELD][digest]
        bad_key[codec.TABLE_FIELD][digest.upper()] = value
        assert_raises(self, lambda: codec.expand(bad_key), "lowercase 64-hex")

        bad_value = codec.encode(base_payload())
        digest = next(iter(bad_value[codec.TABLE_FIELD]))
        bad_value[codec.TABLE_FIELD][digest] = [1]
        assert_raises(self, lambda: codec.expand(bad_value), "must be a JSON object")

        # An empty table with empty subjects is the valid empty-scope v2 form
        # and must NOT be refused; only unreferenced nonempty entries are orphans.
        empty_v2 = {"schema": codec.V2, "subjects": {}, codec.TABLE_FIELD: {}}
        self.assertEqual(codec.expand(empty_v2), {"schema": codec.V1, "subjects": {}})

    def test_malformed_encode_payloads(self):
        good_subject = {"native_reads": {"identity": {"co:a": {}}, "ontology": {}}}

        assert_raises(self, lambda: codec.encode(None), "payload")
        assert_raises(self, lambda: codec.encode([]), "payload")
        assert_raises(self, lambda: codec.encode({}), "unsupported schema")
        assert_raises(
            self, lambda: codec.encode({"schema": codec.V1}), "subjects"
        )
        assert_raises(
            self,
            lambda: codec.encode({"schema": codec.V1, "subjects": []}),
            "subjects",
        )
        assert_raises(
            self,
            lambda: codec.encode({"schema": codec.V1, "subjects": {3: good_subject}}),
            "object keys",
        )
        assert_raises(
            self,
            lambda: codec.encode(
                {"schema": codec.V1, "subjects": {"theme:x": [good_subject]}}
            ),
            "JSON object",
        )
        assert_raises(
            self,
            lambda: codec.encode(
                {"schema": codec.V1, "subjects": {"theme:x": {"native_reads": True}}}
            ),
            "native_reads",
        )
        assert_raises(
            self,
            lambda: codec.encode(
                {"schema": codec.V1, "subjects": {"theme:x": {"native_reads": []}}}
            ),
            "native_reads",
        )
        assert_raises(
            self,
            lambda: codec.encode(
                {"schema": codec.V1, "subjects": {"theme:x": {"ontology": {}}}}
            ),
            "native_reads",
        )
        for bad_identity in (None, "x", 3, True, [], [{"co:a": {}}]):
            payload = {
                "schema": codec.V1,
                "subjects": {
                    "theme:x": {"native_reads": {"identity": bad_identity}}
                },
            }
            assert_raises(
                self,
                lambda payload=payload: codec.encode(payload),
                "native_reads.identity",
            )

    def test_malformed_expand_payloads(self):
        good_subject = {"native_reads": {"identity": {"co:a": {}}}}
        assert_raises(self, lambda: codec.expand(None), "payload")
        assert_raises(self, lambda: codec.expand("v1"), "payload")
        assert_raises(
            self,
            lambda: codec.expand({"schema": codec.V2, "subjects": {}}),
            "identity_read_tables",
        )
        assert_raises(
            self,
            lambda: codec.expand(
                {
                    "schema": codec.V2,
                    "subjects": {"theme:x": {"native_reads": {"identity": True}}},
                    codec.TABLE_FIELD: {},
                }
            ),
            "identity reference",
        )
        assert_raises(
            self,
            lambda: codec.expand(
                {
                    "schema": codec.V2,
                    "subjects": {"theme:x": {"native_reads": [good_subject]}},
                    codec.TABLE_FIELD: {},
                }
            ),
            "native_reads",
        )

    def test_schema_refusal(self):
        encoded = codec.encode(base_payload())
        assert_raises(
            self, lambda: codec.encode(encoded), "unsupported schema for encode"
        )
        assert_raises(
            self,
            lambda: codec.encode({"schema": "gmi.theme_state_owner_bundle/v3"}),
            "unsupported schema",
        )
        assert_raises(
            self,
            lambda: codec.expand({"schema": "gmi.theme_state_owner_bundle/v3"}),
            "unsupported schema",
        )
        payload = {"schema": codec.V1, "subjects": {}, codec.TABLE_FIELD: {}}
        assert_raises(self, lambda: codec.expand(payload), "identity_read_tables")

    def test_non_json_identity_refused(self):
        nan_payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:x": {
                    "native_reads": {"identity": {"co:a": {"score": float("nan")}}}
                }
            },
        }
        assert_raises(self, lambda: codec.encode(nan_payload), "canonicalizable")
        set_payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:x": {"native_reads": {"identity": {"co:a": {"tags": {1, 2}}}}}
            },
        }
        assert_raises(self, lambda: codec.encode(set_payload), "canonicalizable")

    def test_inline_identity_in_v2_refuses(self):
        encoded = codec.encode(base_payload())
        digest = encoded["subjects"]["theme:x"]["native_reads"]["identity"][
            codec.IDENTITY_REF_KEY
        ]
        encoded["subjects"]["theme:x"]["native_reads"]["identity"] = encoded[
            codec.TABLE_FIELD
        ][digest]
        assert_raises(
            self, lambda: codec.expand(encoded), "identity reference"
        )


class DeterminismTest(unittest.TestCase):
    def test_deterministic_output(self):
        first = codec.encode(base_payload())
        second = codec.encode(base_payload())
        self.assertEqual(first, second)
        self.assertEqual(canon_bytes(first), canon_bytes(second))
        expanded = codec.expand(first)
        self.assertEqual(expanded, base_payload())
        self.assertEqual(codec.encode(expanded), first)
        self.assertEqual(codec.expand(codec.encode(expanded)), expanded)

    def test_table_order_is_first_encounter_order(self):
        map_a = build_identity("a", 1)
        map_b = build_identity("b", 1)
        payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:1": {"native_reads": {"identity": map_b}},
                "theme:2": {"native_reads": {"identity": map_a}},
            },
        }
        encoded = codec.encode(payload)
        self.assertEqual(
            list(encoded[codec.TABLE_FIELD]),
            [codec.canonical_sha256(map_b), codec.canonical_sha256(map_a)],
        )

    def test_nan_roundtrip_through_canon_is_rejected(self):
        self.assertTrue(math.isnan(float("nan")))
        with self.assertRaises(codec.OwnerBundleCodecError):
            codec.canonical_json({"x": float("nan")})


class EfficiencyTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(adapter, '_owner_codec_sha_text', wraps=adapter._owner_codec_sha_text)
        self.counter = patcher.start()
        self.addCleanup(patcher.stop)

    def test_hash_call_counting_encode(self):
        shared = build_identity("shared", 4)
        second = build_identity("second", 4)
        third = build_identity("third", 4)
        payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:{}".format(i): {
                    "native_reads": {"identity": (shared if i % 3 == 0 else (second if i % 3 == 1 else third))}
                }
                for i in range(12)
            },
        }
        self.counter.reset_mock()
        codec.encode(payload)
        # 12 subjects, 3 distinct dict objects: exactly 3 canonicalizations.
        self.assertEqual(self.counter.call_count, 3)

    def test_hash_call_counting_expand(self):
        payload = base_payload()  # 2 distinct maps across 4 subjects
        encoded = codec.encode(payload)
        self.counter.reset_mock()
        codec.expand(encoded)
        # One canonicalization per table entry, independent of subject count.
        self.assertEqual(self.counter.call_count, len(encoded[codec.TABLE_FIELD]))

    def test_compact_bytes_under_five_percent(self):
        shared = build_identity("bulk", 300)
        payload = {
            "schema": codec.V1,
            "query": {"known_at": "2026-10-19T00:00:00Z"},
            "subjects": {
                "theme:{:03d}".format(i): {"native_reads": {"identity": shared}}
                for i in range(50)
            },
        }
        expanded_bytes = len(canon_bytes(payload))
        compact_bytes = len(canon_bytes(codec.encode(payload)))
        self.assertLess(compact_bytes, expanded_bytes * 0.05)

    def test_scaling_shared_memoization(self):
        shared = build_identity("scale", 500)
        payload = {
            "schema": codec.V1,
            "subjects": {
                "theme:{:03d}".format(i): {"native_reads": {"identity": shared}}
                for i in range(150)
            },
        }
        self.counter.reset_mock()
        encoded = codec.encode(payload)
        self.assertEqual(self.counter.call_count, 1)
        self.assertEqual(len(encoded[codec.TABLE_FIELD]), 1)
        expanded = codec.expand(encoded)
        self.assertEqual(len(expanded["subjects"]), 150)
        identity = expanded["subjects"]["theme:000"]["native_reads"]["identity"]
        self.assertEqual(len(identity), 500)
        for i in range(0, 150, 17):
            self.assertIs(
                expanded["subjects"]["theme:{:03d}".format(i)]["native_reads"]["identity"],
                identity,
            )
        self.assertEqual(expanded, payload)




class ParentBoundaryTest(unittest.TestCase):
    def test_v2_requires_every_identity_reference(self):
        for subject in ({}, {"native_reads": {}}):
            payload={"schema":codec.V2,"subjects":{"theme:x":subject},codec.TABLE_FIELD:{}}
            with self.assertRaises(codec.OwnerBundleCodecError): codec.expand(payload)

    def test_unrelated_non_json_values_refuse_in_both_directions(self):
        for value in (float("nan"), float("inf"), object(), {"bad"}, {1:"coerced"}):
            for schema in (codec.V1, codec.V2):
                payload={"schema":schema,"subjects":{},"unrelated":value}
                if schema==codec.V2: payload[codec.TABLE_FIELD]={}
                with self.assertRaises(codec.OwnerBundleCodecError): codec.expand(payload)
                if schema==codec.V1:
                    with self.assertRaises(codec.OwnerBundleCodecError): codec.encode(payload)

    def test_cycles_refuse_without_unbounded_serialization(self):
        payload={"schema":codec.V1,"subjects":{}}
        payload["cycle"]=payload
        with self.assertRaises(codec.OwnerBundleCodecError): codec.encode(payload)
        with self.assertRaises(codec.OwnerBundleCodecError): codec.expand(payload)


if __name__ == "__main__":
    unittest.main()


def test_native_tuple_receipts_keep_json_array_semantics():
    payload = base_payload()
    payload["native_flags"] = (True, False, False)
    encoded = codec.encode(payload)
    decoded = codec.expand(json.loads(json.dumps(encoded)))
    assert decoded == json.loads(json.dumps(payload))
