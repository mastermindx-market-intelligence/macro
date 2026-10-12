"""PREPARATORY fake-data tests for the one-shot matrix publication observer.

These tests inject a read-only in-memory client and temporary files. They are
not genuine runtime, natural-session, scheduler, or production acceptance.
No provider, bucket, or live store is contacted.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Repo checkout (engine/) when present; otherwise MACRO_OPTIONS_MATRIX_ROOT.
_REPO = os.environ.get("MACRO_OPTIONS_MATRIX_ROOT")
if _REPO:
    _REPO = os.path.abspath(_REPO)
    if _REPO not in sys.path:
        sys.path.insert(0, _REPO)

try:
    from engine import options_matrix_retention as retention
except ImportError as exc:  # pragma: no cover - environment diagnostic
    raise ImportError(
        "engine.options_matrix_retention is unavailable. Run from the macro "
        "checkout or set MACRO_OPTIONS_MATRIX_ROOT. No packages were installed."
    ) from exc

try:
    from scripts import observe_options_matrix_publication as observe_mod
except ImportError:
    import observe_options_matrix_publication as observe_mod


DEFAULT_ROOTS = observe_mod.DEFAULT_ROOTS


class S3Error(Exception):
    def __init__(self, code, status=None):
        self.response = {"Error": {"Code": code}}
        if status is not None:
            self.response["ResponseMetadata"] = {"HTTPStatusCode": status}


class ShortBody(io.BytesIO):
    def read(self, size=-1):
        if size is None or size < 0:
            raise AssertionError("unbounded reads forbidden")
        return super().read(size)


class ReadOnlyStore:
    """Injected read-only fake. Any write is a test failure."""

    def __init__(self):
        self.objects = {}
        self.calls = []
        self.streams = []
        self.get_faults = {}
        self.head_revisions = {}
        self.length_override = {}

    def get_object(self, *, Bucket, Key):
        self.calls.append(("get", Key))
        if Key in self.get_faults:
            raise self.get_faults[Key]
        if Key in self.head_revisions:
            remaining = self.head_revisions[Key]
            if remaining:
                body = remaining.pop(0)
            else:
                body = self.objects.get(Key)
        elif Key in self.objects:
            body = self.objects[Key]
        else:
            raise S3Error("NoSuchKey", 404)
        handle = ShortBody(body)
        self.streams.append(handle)
        length = self.length_override.get(Key, len(body))
        return {"ContentLength": length, "Body": handle}

    def put_object(self, **kwargs):
        raise AssertionError("observer must not write production objects")

    def delete_object(self, **kwargs):
        raise AssertionError("observer must not write production objects")


def _payload(root, session="2026-10-08", spot=100.5, cells=None, clocks=None, **cell_fields):
    cell = {
        "strike": 500.0,
        "expiry": "2026-10-16",
        "call_oi": 1,
        "put_vol": 0,
    }
    cell.update(cell_fields)
    source = {
        "eod": session,
        "greeks": session,
        "oi_publication": session,
        "previous_oi_publication": "2026-10-02",
        "latest_oi_publication": "2026-10-09",
    }
    if clocks:
        source.update(clocks)
    doc = {
        "schema": "options_structure.matrix/v1",
        "root": root,
        "session": session,
        "spot": spot,
        "_build_meta": {
            "asof_date": session,
            "source_dates": source,
            "unusual_history_window_start": "2026-08-18",
            "unusual_history_window_end": "2026-10-01",
            "unusual_history_sessions_available": 30,
            "unusual_history_sessions_seen": 30,
        },
        "cells": cells if cells is not None else [cell],
    }
    return json.dumps(doc, allow_nan=False).encode()


def _install(out: Path, store: ReadOnlyStore, raw: bytes, root: str):
    ref = retention.reference_for_bytes(root, raw)
    head = out / f"{root}.json"
    hist = out / "history" / root / f"{ref.sha256}.json"
    hist.parent.mkdir(parents=True, exist_ok=True)
    head.write_bytes(raw)
    hist.write_bytes(raw)
    store.objects[f"{retention.R2_PREFIX}{root}.json"] = raw
    store.objects[ref.key] = raw
    return ref


def _prior_from_result(result: dict) -> dict:
    return {
        "schema": observe_mod.SCHEMA,
        "complete": result["complete"],
        "stable": result["stable"],
        "failures": result["failures"],
        "issues": result["issues"],
        "roots": {
            root: {
                "root": item["root"],
                "sha256": item["sha256"],
                "byte_length": item["byte_length"],
                "session": item["session"],
                "version_ref": item["version_ref"],
                "key": item["key"],
                "observed_side_token_set_digest": item["observed_side_token_set_digest"],
                "observed_side_token_set_encoding": item["observed_side_token_set_encoding"],
            }
            for root, item in result["roots"].items()
        },
    }


class ObserveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "options_matrix"
        self.out.mkdir()
        self.store = ReadOnlyStore()
        self.addCleanup(self.tmp.cleanup)

    def observe(self, roots=("SPY", "QQQ"), **kwargs):
        return observe_mod.observe_publication(
            output_dir=self.out,
            client=self.store,
            bucket="fixture-bucket",
            roots=roots,
            retention_module=retention,
            **kwargs,
        )

    def install_pair(self, session="2026-10-08", roots=("SPY", "QQQ"), **kwargs):
        refs = {}
        for root in roots:
            refs[root] = _install(self.out, self.store, _payload(root, session=session, **kwargs), root)
        return refs

    def test_import_does_not_create_client(self):
        self.assertFalse(hasattr(observe_mod, "_r2_client"))
        self.assertIsNone(observe_mod.observe_publication.__defaults__)

    def test_token_set_digest_canonical_encoding(self):
        tokens = (
            ("2026-10-16", "500", "put"),
            ("2026-10-16", "500", "call"),
            ("2026-10-16", "500", "call"),
        )
        payload = b"2026-10-16\x1f500\x1fcall\n2026-10-16\x1f500\x1fput\n"
        self.assertEqual(observe_mod.token_set_digest(tokens), hashlib.sha256(payload).hexdigest())
        self.assertEqual(
            observe_mod.token_set_digest(()),
            hashlib.sha256(b"").hexdigest(),
        )

    def test_success_all_twelve_roots(self):
        refs = self.install_pair(roots=DEFAULT_ROOTS)
        result = self.observe(roots=DEFAULT_ROOTS)
        self.assertTrue(result["complete"])
        self.assertFalse(result["advancing"])
        self.assertFalse(result["natural_invocation_verified"])
        self.assertIsNone(result["natural_session_count"])
        self.assertFalse(result["mutable_writes"])
        self.assertEqual(result["session"], "2026-10-08")
        self.assertEqual(set(result["roots"]), set(DEFAULT_ROOTS))
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["failures"], {})
        for root, item in result["roots"].items():
            ref = refs[root]
            self.assertEqual(item["sha256"], ref.sha256)
            self.assertEqual(item["version_ref"], ref.version_ref)
            self.assertEqual(item["byte_length"], ref.byte_length)
            self.assertEqual(item["session"], "2026-10-08")
            self.assertEqual(item["observed_sides"], 2)
            self.assertEqual(item["source_clocks"]["previous_oi_publication"], "2026-10-02")
            self.assertEqual(item["source_clocks"]["latest_oi_publication"], "2026-10-09")
            self.assertEqual(item["source_clocks"]["unusual_history_window_start"], "2026-08-18")
            self.assertEqual(item["source_clocks"]["unusual_history_window_end"], "2026-10-01")
            raw = (self.out / f"{root}.json").read_bytes()
            tokens = retention.matrix_observed_side_tokens(ref, raw)
            self.assertEqual(item["observed_side_token_set_digest"], observe_mod.token_set_digest(tokens))
        self.assertTrue(all(s.closed for s in self.store.streams))
        self.assertFalse(any(call[0] != "get" for call in self.store.calls))

    def test_missing_local_history(self):
        refs = self.install_pair()
        (self.out / "history" / "SPY" / f"{refs['SPY'].sha256}.json").unlink()
        result = self.observe()
        self.assertFalse(result["complete"])
        self.assertEqual(result["failures"]["SPY"]["code"], "missing_local_history")
        self.assertIn("partial_roots", result["issues"])

    def test_missing_remote_history(self):
        refs = self.install_pair()
        del self.store.objects[refs["QQQ"].key]
        result = self.observe()
        self.assertFalse(result["complete"])
        self.assertEqual(result["failures"]["QQQ"]["code"], "missing_remote_history")

    def test_mismatched_local_history(self):
        refs = self.install_pair()
        path = self.out / "history" / "SPY" / f"{refs['SPY'].sha256}.json"
        path.write_bytes(_payload("SPY", session="2026-10-07"))
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "mismatched_local_history")
        self.assertFalse(result["complete"])

    def test_mismatched_remote_history(self):
        refs = self.install_pair()
        other = _payload("SPY", spot=101.5)
        self.store.objects[refs["SPY"].key] = other
        result = self.observe()
        self.assertIn(result["failures"]["SPY"]["code"], {
            "mismatched_remote_history", "unavailable_remote_history",
        })
        self.assertFalse(result["complete"])

    def test_oversize_local_head(self):
        self.install_pair()
        huge = self.out / "SPY.json"
        huge.write_bytes(b"x" * 64)
        with mock.patch.object(retention, "MAX_MATRIX_BYTES", 16):
            result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "oversize")
        self.assertFalse(result["complete"])

    def test_oversize_remote_head_does_not_read_unbounded(self):
        self.install_pair()
        key = f"{retention.R2_PREFIX}SPY.json"
        self.store.length_override[key] = retention.MAX_MATRIX_BYTES + 1
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "oversize")
        self.assertTrue(all(s.closed for s in self.store.streams))

    def test_invalid_json(self):
        self.install_pair()
        raw = b"not-json"
        (self.out / "SPY.json").write_bytes(raw)
        hist_dir = self.out / "history" / "SPY"
        for path in hist_dir.glob("*.json"):
            path.write_bytes(raw)
        self.store.objects[f"{retention.R2_PREFIX}SPY.json"] = raw
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "invalid_json")

    def test_wrong_root_in_payload(self):
        self.install_pair()
        raw = _payload("QQQ")
        _install(self.out, self.store, raw, "QQQ")
        (self.out / "SPY.json").write_bytes(raw)
        hist = self.out / "history" / "SPY"
        hist.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256(raw).hexdigest()
        (hist / f"{sha}.json").write_bytes(raw)
        self.store.objects[f"{retention.R2_PREFIX}SPY.json"] = raw
        self.store.objects[f"{retention.R2_PREFIX}history/SPY/{sha}.json"] = raw
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "wrong_root")

    def test_zero_spot(self):
        self.install_pair()
        _install(self.out, self.store, _payload("SPY", spot=0), "SPY")
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "invalid_spot")

    def test_negative_spot(self):
        self.install_pair()
        _install(self.out, self.store, _payload("SPY", spot=-1.5), "SPY")
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "invalid_spot")

    def test_nonfinite_spot(self):
        self.install_pair()
        raw = _payload("SPY").replace(b"100.5", b"NaN")
        (self.out / "SPY.json").write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        hist = self.out / "history" / "SPY" / f"{sha}.json"
        hist.parent.mkdir(parents=True, exist_ok=True)
        hist.write_bytes(raw)
        self.store.objects[f"{retention.R2_PREFIX}SPY.json"] = raw
        self.store.objects[f"{retention.R2_PREFIX}history/SPY/{sha}.json"] = raw
        result = self.observe()
        self.assertIn(result["failures"]["SPY"]["code"], {"invalid_json", "invalid_spot", "invalid_snapshot"})
        self.assertFalse(math.isfinite(float("nan")))

    def test_empty_cells(self):
        self.install_pair()
        _install(self.out, self.store, _payload("SPY", cells=[]), "SPY")
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "empty_cells")

    def test_403_is_denied_not_absence(self):
        self.install_pair()
        key = f"{retention.R2_PREFIX}SPY.json"
        self.store.get_faults[key] = S3Error("AccessDenied", 403)
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "denied")
        self.assertEqual(result["failures"]["SPY"]["http_status"], 403)
        self.assertNotEqual(result["failures"]["SPY"]["code"], "missing_remote_head")

    def test_403_code_without_status_is_denied(self):
        self.install_pair()
        self.store.get_faults[f"{retention.R2_PREFIX}QQQ.json"] = S3Error("403")
        result = self.observe()
        self.assertEqual(result["failures"]["QQQ"]["code"], "denied")

    def test_history_access_denied_is_not_missing(self):
        refs = self.install_pair()
        self.store.get_faults[refs["SPY"].key] = S3Error("AccessDenied", 403)
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "unavailable_remote_history")
        self.assertNotEqual(result["failures"]["SPY"]["code"], "missing_remote_history")

    def test_concurrent_remote_head_change(self):
        refs = self.install_pair()
        later = _payload("SPY", spot=120.0)
        head = f"{retention.R2_PREFIX}SPY.json"
        first = self.store.objects[head]
        self.store.head_revisions[head] = [first, later]
        result = self.observe()
        self.assertFalse(result["complete"])
        self.assertFalse(result["stable"])
        self.assertEqual(result["failures"]["SPY"]["code"], "concurrent_head_change")
        self.assertIn("unstable", result["issues"])
        del refs

    def test_concurrent_local_head_change(self):
        self.install_pair()
        original = observe_mod.read_local_bytes
        seen = {"SPY.json": 0}

        def wrapped(path, limit):
            data = original(path, limit)
            name = Path(path).name
            if name == "SPY.json":
                seen[name] += 1
                if seen[name] == 1:
                    Path(path).write_bytes(_payload("SPY", spot=121.0))
            return data

        with mock.patch.object(observe_mod, "read_local_bytes", wrapped):
            result = self.observe()
        self.assertFalse(result["stable"])
        self.assertEqual(result["failures"]["SPY"]["code"], "concurrent_head_change")

    def test_missing_root(self):
        _install(self.out, self.store, _payload("SPY"), "SPY")
        result = self.observe(roots=("SPY", "QQQ"))
        self.assertFalse(result["complete"])
        self.assertEqual(result["failures"]["QQQ"]["code"], "missing_local_head")
        self.assertIn("partial_roots", result["issues"])

    def test_missing_remote_head(self):
        self.install_pair()
        del self.store.objects[f"{retention.R2_PREFIX}SPY.json"]
        result = self.observe()
        self.assertFalse(result["complete"])
        self.assertEqual(result["failures"]["SPY"]["code"], "missing_remote_head")

    def test_mixed_dates_across_roots(self):
        _install(self.out, self.store, _payload("SPY", session="2026-10-08"), "SPY")
        _install(self.out, self.store, _payload("QQQ", session="2026-10-07"), "QQQ")
        result = self.observe()
        self.assertFalse(result["complete"])
        self.assertIn("mixed_source_dates", result["issues"])
        self.assertIsNone(result["session"])

    def test_mixed_dates_within_root_source_clocks(self):
        raw = _payload("SPY", clocks={"eod": "2026-10-07"})
        _install(self.out, self.store, raw, "SPY")
        _install(self.out, self.store, _payload("QQQ"), "QQQ")
        result = self.observe()
        self.assertEqual(result["failures"]["SPY"]["code"], "mixed_source_dates")
        self.assertFalse(result["complete"])

    def test_repeated_source_date_is_not_advancing(self):
        self.install_pair()
        first = self.observe()
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(_prior_from_result(first)))
        second = self.observe(prior_path=prior_path)
        self.assertTrue(second["complete"])
        self.assertFalse(second["advancing"])
        self.assertTrue(second["repeated_source_date"])
        self.assertFalse(second["natural_invocation_verified"])
        self.assertIsNone(second["natural_session_count"])
        self.assertEqual(second["session"], first["session"])

    def test_advancing_when_prior_session_is_older(self):
        old_refs = self.install_pair(session="2026-10-07")
        first = self.observe()
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(_prior_from_result(first)))
        for root in ("SPY", "QQQ"):
            _install(self.out, self.store, _payload(root, session="2026-10-08"), root)
        # Keep old immutable objects.
        for ref in old_refs.values():
            self.assertIn(ref.key, self.store.objects)
        second = self.observe(prior_path=prior_path)
        self.assertTrue(second["complete"])
        self.assertTrue(second["advancing"])
        self.assertFalse(second["repeated_source_date"])
        self.assertFalse(second["natural_invocation_verified"])
        self.assertIsNone(second["natural_session_count"])

    def test_older_than_prior_fails_closed(self):
        self.install_pair(session="2026-10-08")
        first = self.observe()
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(_prior_from_result(first)))
        for root in ("SPY", "QQQ"):
            _install(self.out, self.store, _payload(root, session="2026-10-07"), root)
        second = self.observe(prior_path=prior_path)
        self.assertFalse(second["complete"])
        self.assertFalse(second["advancing"])
        self.assertIn("older_than_prior", second["issues"])

    def test_incomplete_or_unstable_prior_cannot_be_an_advance_baseline(self):
        self.install_pair()
        first = self.observe()
        prior_path = Path(self.tmp.name) / "prior.json"
        for key, value in (("complete", False), ("stable", False),
                           ("failures", {"SPY": {"code": "denied"}}),
                           ("issues", ["unstable"])):
            with self.subTest(key=key):
                prior = _prior_from_result(first)
                prior[key] = value
                prior_path.write_text(json.dumps(prior))
                with self.assertRaises(observe_mod.ObservationRefused):
                    self.observe(prior_path=prior_path)

    def test_prior_token_digest_is_recomputed_from_retained_bytes(self):
        self.install_pair()
        first = self.observe()
        prior = _prior_from_result(first)
        prior["roots"]["SPY"]["observed_side_token_set_digest"] = "0" * 64
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(prior))
        second = self.observe(prior_path=prior_path)
        self.assertFalse(second["complete"])
        self.assertFalse(second["advancing"])
        self.assertEqual(second["failures"]["_prior"]["code"], "mismatched_prior_observed_sides")

    def test_invalid_prior_schema(self):
        self.install_pair()
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps({"schema": "nope", "roots": {}}))
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(prior_path=prior_path)

    def test_invalid_prior_wrong_roots(self):
        self.install_pair()
        first = self.observe()
        prior = _prior_from_result(first)
        del prior["roots"]["QQQ"]
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(prior))
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(prior_path=prior_path)

    def test_invalid_prior_reference(self):
        self.install_pair()
        first = self.observe()
        prior = _prior_from_result(first)
        prior["roots"]["SPY"]["version_ref"] = prior["roots"]["SPY"]["version_ref"].replace(
            "2026-10-08", "2026-10-01",
        )
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(prior))
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(prior_path=prior_path)

    def test_missing_prior_history_fails_closed(self):
        old_refs = self.install_pair(session="2026-10-07")
        first = self.observe()
        prior_path = Path(self.tmp.name) / "prior.json"
        prior_path.write_text(json.dumps(_prior_from_result(first)))
        del self.store.objects[old_refs["SPY"].key]
        for root in ("SPY", "QQQ"):
            _install(self.out, self.store, _payload(root, session="2026-10-08"), root)
        second = self.observe(prior_path=prior_path)
        self.assertFalse(second["complete"])
        self.assertFalse(second["advancing"])
        self.assertEqual(second["failures"]["_prior"]["code"], "missing_prior_history")

    def test_receipt_overwrite_refused(self):
        self.install_pair()
        receipt = Path(self.tmp.name) / "receipt.json"
        receipt.write_text("{}\n")
        before = receipt.read_bytes()
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(receipt_path=receipt)
        self.assertEqual(receipt.read_bytes(), before)

    def test_receipt_inside_output_refused(self):
        self.install_pair()
        receipt = self.out / "observation.json"
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(receipt_path=receipt)
        self.assertFalse(receipt.exists())
        nested = self.out / "history" / "escape.json"
        nested.parent.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(receipt_path=nested)

    def test_receipt_exclusive_create(self):
        self.install_pair()
        receipt = Path(self.tmp.name) / "receipt.json"
        result = self.observe(receipt_path=receipt)
        self.assertTrue(result["complete"])
        self.assertTrue(result["receipt_written"])
        saved = json.loads(receipt.read_text())
        self.assertEqual(saved["schema"], observe_mod.SCHEMA)
        self.assertTrue(saved["complete"])
        self.assertFalse(saved["natural_invocation_verified"])
        self.assertIsNone(saved["natural_session_count"])
        mode = os.stat(receipt).st_mode & 0o777
        self.assertEqual(mode, 0o600)
        with self.assertRaises(observe_mod.ObservationRefused):
            self.observe(receipt_path=receipt)

    def test_natural_flags_always_unverified(self):
        self.install_pair()
        result = self.observe()
        self.assertIs(result["natural_invocation_verified"], False)
        self.assertIs(result["natural_session_count"], None)

    def test_main_uses_injected_client_and_stub_publisher(self):
        self.install_pair(roots=DEFAULT_ROOTS)
        receipt = Path(self.tmp.name) / "cli-receipt.json"
        stub = mock.Mock()
        stub.DEFAULT_ROOTS = list(DEFAULT_ROOTS)
        stub._r2_client.side_effect = AssertionError("tests must not create a live client")
        argv = [
            "--repo", str(Path(self.tmp.name)),
            "--out", str(self.out),
            "--receipt", str(receipt),
            "--bucket", "fixture-bucket",
        ]
        buf = io.StringIO()
        with mock.patch.dict(sys.modules, {"scripts.build_options_matrix": stub}):
            with mock.patch("sys.stdout", buf):
                code = observe_mod.main(argv, client=self.store)
        self.assertEqual(code, 0)
        stub._r2_client.assert_not_called()
        saved = json.loads(receipt.read_text())
        self.assertTrue(saved["complete"])
        self.assertEqual(len(saved["roots"]), 12)

    def test_library_refuses_to_construct_a_client(self):
        with self.assertRaises(observe_mod.ObservationRefused):
            observe_mod.observe_publication(
                output_dir=self.out,
                client=None,
                bucket="fixture-bucket",
                roots=("SPY",),
                retention_module=retention,
            )


if __name__ == "__main__":
    unittest.main()
