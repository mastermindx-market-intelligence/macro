"""Synthetic-only tests for unactivated QLedger read seam; no live store I/O."""

import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import qledger_store as q


def raw_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()


def ref(path, contents):
    return {"path": path, "sha256": hashlib.sha256(contents).hexdigest(),
            "bytes": len(contents)}


def fixture(base=b'{"claim_id":"A"}\n', parts=(b'{"claim_id":"B"}\n',),
            *, branch=False):
    blobs = {q.BASE_PATH: base}
    entries = []
    for i, item in enumerate(parts):
        path = q.DATA_PREFIX + f"p{i}.jsonl"
        blobs[path] = item
        entries.append({"tx_id": f"txn-{i}", **ref(path, item),
                        "lines": len(item.decode().splitlines())})
    leaf_path = q.INDEX_PREFIX + "leaf.json"
    blobs[leaf_path] = raw_json({"schema": q.SCHEMA, "kind": "leaf", "entries": entries})
    if branch:
        path = q.INDEX_PREFIX + "branch.json"
        blobs[path] = raw_json({"schema": q.SCHEMA, "kind": "branch",
                                 "children": [ref(leaf_path, blobs[leaf_path])]})
        ix_path = path
    else:
        ix_path = leaf_path
    blobs[q.ROOT_PATH] = raw_json({"schema": q.SCHEMA, "generation": "G-1",
                                   "base": ref(q.BASE_PATH, base),
                                   "index_root": ref(ix_path, blobs[ix_path])})
    return blobs


def reader(blobs):
    return q.read_claims_snapshot(blobs.get)


class LegacyTest(unittest.TestCase):
    def test_absent_is_native_empty(self):
        x = reader({})
        self.assertEqual(x.raw_lines, ())
        self.assertEqual(x.load_claims(), [])
        self.assertFalse(x.receipt.source_present)
        self.assertEqual(x.receipt.mode, "legacy")

    def test_legacy_preserves_duplication_and_bad_rows(self):
        blob = '{"claim_id":"A"}\ninvalid\n{"claim_id":"A"}\n\n{"name":"中"}\n'.encode()
        x = reader({q.BASE_PATH: blob})
        self.assertEqual(len(x.raw_lines), 5)
        self.assertEqual([r.get("claim_id") for r in x.load_claims()], ["A", "A", None])
        self.assertEqual(x.load_claims()[-1]["name"], "中")

    def test_legacy_does_not_use_catalog_limit(self):
        blob = b'{"a":1}\n' * 20
        x = q.read_claims_snapshot({q.BASE_PATH: blob}.get,
                                    limits=q.ReadLimits(max_base_bytes=1))
        self.assertEqual(len(x.load_claims()), 20)


class CatalogTest(unittest.TestCase):
    def assert_denied(self, blobs, expected=None, **kwargs):
        with self.assertRaises(q.StoreIntegrityError) as caught:
            q.read_claims_snapshot(blobs.get, **kwargs)
        if expected:
            self.assertIn(expected, str(caught.exception))

    def test_base_then_parts_occurrences_and_order(self):
        data = fixture(base=b'{"claim_id":"A"}\n', parts=(
            b'{"claim_id":"B"}\nnot JSON\n', b'{"claim_id":"A"}\n'))
        before = dict(data)
        x = reader(data)
        self.assertEqual([r['claim_id'] for r in x.load_claims()], ['A', 'B', 'A'])
        self.assertEqual(x.receipt.raw_line_count, 4)
        self.assertEqual(x.receipt.claim_count, 3)
        self.assertEqual(x.receipt.generation, 'G-1')
        self.assertEqual(x.receipt.mode, 'segmented_v0')
        self.assertEqual(data, before)

    def test_nested_tree(self):
        x = reader(fixture(branch=True))
        self.assertEqual(x.receipt.claim_count, 2)
        self.assertEqual(x.receipt.member_count, 5)

    def test_exact_duplicate_occurrences_not_content_deduped(self):
        x = reader(fixture(parts=(b'{"claim_id":"A"}\n', b'{"claim_id":"A"}\n')))
        self.assertEqual(len(x.load_claims()), 3)

    def test_missing_data_fails_not_zero_history(self):
        data = fixture()
        del data[q.DATA_PREFIX + 'p0.jsonl']
        self.assert_denied(data, 'missing')

    def test_absent_root_falls_back_to_legacy(self):
        data = fixture()
        del data[q.ROOT_PATH]
        self.assertEqual(reader(data).receipt.mode, 'legacy')
        self.assertEqual(len(reader(data).load_claims()), 1)

    def test_bad_base_is_not_hidden_by_catalog(self):
        data = fixture()
        data[q.BASE_PATH] += b'corrupt'
        self.assert_denied(data, 'digest')

    def test_bad_page_hash(self):
        data = fixture()
        data[q.INDEX_PREFIX + 'leaf.json'] += b' '
        self.assert_denied(data, 'digest')

    def test_invalid_root_schema(self):
        data = fixture()
        obj = json.loads(data[q.ROOT_PATH]); obj['schema'] = 'other'
        data[q.ROOT_PATH] = raw_json(obj)
        self.assert_denied(data, 'schema')

    def test_duplicate_root_json_key(self):
        data = fixture()
        data[q.ROOT_PATH] = data[q.ROOT_PATH][:-1] + b',"schema":"bad"}'
        self.assert_denied(data, 'duplicate JSON property')

    def test_traversal_ignored_only_by_refusal(self):
        data = fixture()
        p = q.INDEX_PREFIX + 'leaf.json'; obj = json.loads(data[p])
        obj['entries'][0]['path'] = q.DATA_PREFIX + '../escape'
        data[p] = raw_json(obj)
        root = json.loads(data[q.ROOT_PATH]); root['index_root'] = ref(p, data[p])
        data[q.ROOT_PATH] = raw_json(root)
        self.assert_denied(data, 'path')

    def test_repeated_storage_transaction_refused(self):
        data = fixture(parts=(b'{"n":1}\n', b'{"n":2}\n'))
        p = q.INDEX_PREFIX + 'leaf.json'; obj = json.loads(data[p])
        obj['entries'][1]['tx_id'] = obj['entries'][0]['tx_id']
        data[p] = raw_json(obj)
        root = json.loads(data[q.ROOT_PATH]); root['index_root'] = ref(p, data[p])
        data[q.ROOT_PATH] = raw_json(root)
        self.assert_denied(data, 'transaction')

    def test_missing_branch_child_refused(self):
        data = fixture(branch=True)
        del data[q.INDEX_PREFIX+'leaf.json']
        self.assert_denied(data, 'missing')

    def test_cycle_or_repeated_page_refused(self):
        data = fixture(branch=True)
        p = q.INDEX_PREFIX + 'branch.json'; obj = json.loads(data[p])
        obj['children'] *= 2
        data[p] = raw_json(obj)
        root = json.loads(data[q.ROOT_PATH]); root['index_root'] = ref(p, data[p])
        data[q.ROOT_PATH] = raw_json(root)
        self.assert_denied(data, 'repeated')

    def test_fanout_bound(self):
        data = fixture(parts=(b'{"a":1}\n', b'{"b":2}\n'))
        self.assert_denied(data, 'fanout', limits=q.ReadLimits(max_fanout=1))

    def test_depth_bound(self):
        data = fixture(branch=True)
        self.assert_denied(data, 'depth', limits=q.ReadLimits(max_depth=1))

    def test_part_byte_limit(self):
        data = fixture()
        self.assert_denied(data, 'integer', limits=q.ReadLimits(max_part_bytes=2))

    def test_unknown_revision_shape_fails_closed(self):
        data = fixture()
        p = q.INDEX_PREFIX + 'leaf.json'; obj = json.loads(data[p])
        obj['entries'][0]['replace'] = 0
        data[p] = raw_json(obj)
        root = json.loads(data[q.ROOT_PATH]); root['index_root'] = ref(p, data[p])
        data[q.ROOT_PATH] = raw_json(root)
        self.assert_denied(data, 'fields')

    def test_line_count_mismatch(self):
        data = fixture()
        p = q.INDEX_PREFIX + 'leaf.json'; obj = json.loads(data[p])
        obj['entries'][0]['lines'] += 1
        data[p] = raw_json(obj)
        root = json.loads(data[q.ROOT_PATH]); root['index_root'] = ref(p, data[p])
        data[q.ROOT_PATH] = raw_json(root)
        self.assert_denied(data, 'line count')

    def test_part_without_trailing_newline_keeps_base_last_line(self):
        data = fixture(base=b'{"claim_id":"A"}', parts=(b'{"claim_id":"B"}',))
        self.assertEqual([r['claim_id'] for r in reader(data).load_claims()], ['A', 'B'])

    def test_malformed_legacy_utf8_fails_not_zero(self):
        self.assert_denied({q.BASE_PATH: b'\xff'}, 'UTF-8')

    def test_catalog_root_present_but_invalid_fails(self):
        data = fixture(); data[q.ROOT_PATH] = b''
        self.assert_denied(data, 'JSON')

    def test_receipt_changes_on_occurrence_order(self):
        x = reader(fixture(parts=(b'{"claim_id":"B"}\n', b'{"claim_id":"A"}\n')))
        y = reader(fixture(parts=(b'{"claim_id":"A"}\n', b'{"claim_id":"B"}\n')))
        self.assertNotEqual(x.receipt.occurrence_digest, y.receipt.occurrence_digest)


class FailureBoundaryTest(unittest.TestCase):
    """Each negative case must fail at the storage boundary, not leak a prefix.

    Removing the typed-source checks or aggregate budgets must break these tests.
    Fixtures are in-memory invented claims; no production artifact is read.
    """

    def _replace_leaf(self, data, obj):
        path = q.INDEX_PREFIX + "leaf.json"
        data[path] = raw_json(obj)
        root = json.loads(data[q.ROOT_PATH])
        root["index_root"] = ref(path, data[path])
        data[q.ROOT_PATH] = raw_json(root)

    def test_unhashable_node_kind_is_integrity_error(self):
        for kind in ([], {}, ["leaf"]):
            with self.subTest(kind=kind):
                data = fixture()
                self._replace_leaf(data, {"schema": q.SCHEMA, "kind": kind,
                                          "entries": []})
                try:
                    reader(data)
                except q.StoreIntegrityError:
                    pass
                except Exception as exc:
                    self.fail(f"untyped failure: {type(exc).__name__}: {exc}")
                else:
                    self.fail("malformed kind accepted")

    def test_excessively_nested_metadata_is_integrity_error(self):
        data = {q.ROOT_PATH: b'{"nested":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}'}
        try:
            reader(data)
        except q.StoreIntegrityError:
            pass
        except Exception as exc:
            self.fail(f"untyped failure: {type(exc).__name__}")
        else:
            self.fail("deep metadata accepted")

    def test_root_source_failure_is_not_absence_or_untyped_error(self):
        for error in (OSError("unavailable"), KeyError("not a proven absence")):
            with self.subTest(error=type(error).__name__):
                def source(path):
                    raise error
                try:
                    q.read_claims_snapshot(source)
                except q.StoreIntegrityError:
                    pass
                except Exception as exc:
                    self.fail(f"untyped failure: {type(exc).__name__}")
                else:
                    self.fail("source failure treated as empty history")

    def test_legacy_source_failure_is_integrity_error(self):
        def source(path):
            if path == q.ROOT_PATH:
                return None
            raise OSError("legacy unavailable")
        try:
            q.read_claims_snapshot(source)
        except q.StoreIntegrityError:
            pass
        except Exception as exc:
            self.fail(f"untyped failure: {type(exc).__name__}")
        else:
            self.fail("legacy failure treated as empty history")

    def test_invalid_limits_rejected_before_reading(self):
        for field, value in (("max_fanout", True), ("max_depth", float("inf")),
                             ("max_parts", -1), ("max_index_bytes", float("nan")),
                             ("max_part_bytes", "64"), ("max_root_bytes", 0)):
            with self.subTest(field=field, value=value):
                calls = []
                try:
                    limits = q.ReadLimits(**{field: value})
                    q.read_claims_snapshot(lambda path: calls.append(path), limits=limits)
                except (ValueError, TypeError):
                    self.assertEqual(calls, [])
                else:
                    self.fail("invalid limit accepted")

    def test_total_page_budget_includes_empty_leaves(self):
        data = fixture(branch=True, parts=())
        path = q.INDEX_PREFIX + "branch.json"
        branch = json.loads(data[path])
        extra = q.INDEX_PREFIX + "empty-two.json"
        data[extra] = raw_json({"schema": q.SCHEMA, "kind": "leaf", "entries": []})
        branch["children"].append(ref(extra, data[extra]))
        data[path] = raw_json(branch)
        root = json.loads(data[q.ROOT_PATH]); root["index_root"] = ref(path, data[path])
        data[q.ROOT_PATH] = raw_json(root)
        calls = []
        def source(path):
            calls.append(path)
            return data.get(path)
        try:
            limits = q.ReadLimits(max_pages=2)
        except TypeError:
            self.fail("aggregate page budget is missing")
        with self.assertRaisesRegex(q.StoreIntegrityError, "page"):
            q.read_claims_snapshot(source, limits=limits)
        self.assertNotIn(extra, calls)

    def test_total_byte_budget_fails_before_over_budget_fetch(self):
        data = fixture()
        # Every individual blob is admissible; their aggregate is not.
        total = sum(map(len, data.values()))
        calls = []
        def source(path):
            calls.append(path)
            return data.get(path)
        try:
            limits = q.ReadLimits(max_total_bytes=total - 1)
        except TypeError:
            self.fail("aggregate byte budget is missing")
        with self.assertRaisesRegex(q.StoreIntegrityError, "byte"):
            q.read_claims_snapshot(source, limits=limits)
        self.assertLess(sum(len(data[p]) for p in calls), total)
        exact = q.read_claims_snapshot(data.get, limits=q.ReadLimits(max_total_bytes=total))
        self.assertEqual(exact.receipt.claim_count, 2)

    def test_total_line_budget_preserves_explicit_failure(self):
        data = fixture()
        try:
            limits = q.ReadLimits(max_lines=1)
        except TypeError:
            self.fail("aggregate line budget is missing")
        with self.assertRaisesRegex(q.StoreIntegrityError, "line"):
            q.read_claims_snapshot(data.get, limits=limits)
        exact = q.read_claims_snapshot(data.get, limits=q.ReadLimits(max_lines=2))
        self.assertEqual(exact.receipt.raw_line_count, 2)

    def test_line_budget_covers_empty_base_lines(self):
        data = fixture(base=b"\n" * 100, parts=())
        try:
            limits = q.ReadLimits(max_lines=3)
        except TypeError:
            self.fail("aggregate line budget is missing")
        with self.assertRaisesRegex(q.StoreIntegrityError, "line"):
            q.read_claims_snapshot(data.get, limits=limits)

    def test_line_splitting_matches_native_unicode_semantics(self):
        for text in ("", "\n", "a\r\nb\rc\n", "a\v\fb\x1cc\x1dd\x1ee\x85f\u2028g\u2029",
                     "\u2028\n\u2029", "a\n\n", "中\r\n文"):
            with self.subTest(text=repr(text)):
                x = reader(fixture(base=text.encode(), parts=()))
                self.assertEqual(x.raw_lines, tuple(text.splitlines()))

    def test_each_member_is_read_once(self):
        data = fixture(branch=True)
        calls = []
        def source(path):
            calls.append(path)
            return data.get(path)
        x = q.read_claims_snapshot(source)
        self.assertEqual(len(calls), len(set(calls)))
        self.assertEqual(x.receipt.member_count, len(data))


class TraversalRegressionTest(unittest.TestCase):
    """Order, parser parity and caps must survive the iterative traversal repair."""

    def test_deterministic_unicode_split_parity(self):
        import random
        rng = random.Random(8685)
        alphabet = "AB中\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
        for case in range(256):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(128)))
            with self.subTest(case=case):
                self.assertEqual(reader(fixture(base=text.encode(), parts=())).raw_lines,
                                 tuple(text.splitlines()))

    def test_multilevel_children_retain_declared_order(self):
        data = fixture(parts=tuple(f'{{"n":{i}}}\n'.encode() for i in range(4)))
        entries = json.loads(data[q.INDEX_PREFIX + "leaf.json"])["entries"]
        def leaf(name, selected):
            path = q.INDEX_PREFIX + name + ".json"
            data[path] = raw_json({"schema": q.SCHEMA, "kind": "leaf", "entries": selected})
            return ref(path, data[path])
        def branch(name, children):
            path = q.INDEX_PREFIX + name + ".json"
            data[path] = raw_json({"schema": q.SCHEMA, "kind": "branch", "children": children})
            return ref(path, data[path])
        nested = branch("nested", [leaf("one", entries[:2]), leaf("two", entries[2:3])])
        top = branch("top", [nested, leaf("three", entries[3:])])
        root = json.loads(data[q.ROOT_PATH]); root["index_root"] = top
        data[q.ROOT_PATH] = raw_json(root)
        self.assertEqual(reader(data).load_claims(),
                         [{"claim_id": "A"}, {"n": 0}, {"n": 1}, {"n": 2}, {"n": 3}])

    def test_accepted_depth_does_not_depend_on_python_recursion(self):
        data = fixture(parts=())
        child = ref(q.INDEX_PREFIX + "leaf.json", data[q.INDEX_PREFIX + "leaf.json"])
        for i in range(1100):
            path = q.INDEX_PREFIX + f"depth-{i}.json"
            data[path] = raw_json({"schema": q.SCHEMA, "kind": "branch", "children": [child]})
            child = ref(path, data[path])
        root = json.loads(data[q.ROOT_PATH]); root["index_root"] = child
        data[q.ROOT_PATH] = raw_json(root)
        x = q.read_claims_snapshot(data.get, limits=q.ReadLimits(max_depth=1200))
        self.assertEqual(x.load_claims(), [{"claim_id": "A"}])
        self.assertEqual(x.receipt.member_count, 1103)

    def test_legacy_aggregate_limits_do_not_truncate_native_history(self):
        data = {q.BASE_PATH: b'{"n":1}\n' * 5}
        limits = q.ReadLimits(max_total_bytes=1, max_lines=1, max_pages=1)
        self.assertEqual(len(q.read_claims_snapshot(data.get, limits=limits).load_claims()), 5)

    def test_non_limits_argument_fails_before_io(self):
        calls = []
        with self.assertRaises(TypeError):
            q.read_claims_snapshot(lambda path: calls.append(path), limits={})
        self.assertEqual(calls, [])

    def test_descriptor_types_are_never_coerced(self):
        changes = (("bytes", True), ("bytes", "1"), ("bytes", float("nan")),
                   ("lines", True), ("lines", "1"), ("sha256", None),
                   ("path", []), ("tx_id", {}))
        for field, value in changes:
            with self.subTest(field=field, value=value):
                data = fixture()
                path = q.INDEX_PREFIX + "leaf.json"; page = json.loads(data[path])
                page["entries"][0][field] = value; data[path] = raw_json(page)
                root = json.loads(data[q.ROOT_PATH]); root["index_root"] = ref(path, data[path])
                data[q.ROOT_PATH] = raw_json(root)
                with self.assertRaises(q.StoreIntegrityError):
                    reader(data)

    def test_same_length_member_tampering_is_rejected(self):
        mutations = ((q.BASE_PATH, b'"A"', b'"Z"'),
                     (q.DATA_PREFIX + "p0.jsonl", b'"B"', b'"C"'),
                     (q.INDEX_PREFIX + "leaf.json", b'"txn-0"', b'"txn-9"'))
        for path, old, new in mutations:
            with self.subTest(member=path):
                data = fixture()
                original_size = len(data[path])
                self.assertIn(old, data[path])
                data[path] = data[path].replace(old, new, 1)
                self.assertEqual(len(data[path]), original_size)
                with self.assertRaisesRegex(q.StoreIntegrityError, "digest"):
                    reader(data)

    def test_part_count_limit_precedes_second_part_read(self):
        data = fixture(parts=(b'{"n":0}\n', b'{"n":1}\n'))
        calls = []
        def source(path):
            calls.append(path)
            return data.get(path)
        with self.assertRaisesRegex(q.StoreIntegrityError, "part capacity"):
            q.read_claims_snapshot(source, limits=q.ReadLimits(max_parts=1))
        self.assertNotIn(q.DATA_PREFIX + "p1.jsonl", calls)


if __name__ == '__main__':
    unittest.main()
