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


if __name__ == '__main__':
    unittest.main()
