#!/usr/bin/env python3
"""Preparatory tests for isolated older-candidate qualification.


These tests are synthetic and preparatory. They are not genuine older-candidate
acceptance, live acceptance, natural-session proof, or production invocation.
A genuine retained production pair must be qualified separately.
Never execute network or provider calls in these tests.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

COMMIT = "6361f5e0e071dfc050c503e225afe8a4897f0e8d"
SOURCE_NAMES = (
    "scripts/build_options_matrix.py",
    "engine/options_matrix_retention.py",
    "engine/thetadata_store.py",
)
A_SHA = "cb50c35a3250b48d70169af2a3aa1450f5c4478bc1dc5fe01b191307fcd2cfb2"
B_SHA = "e8537aedb1005b01db8725983d1c255051562b10054d6cad86ada2bb3e7f6de7"
A_BYTES = 2950
B_BYTES = 2971
A_SESSION = "2026-09-22"
B_SESSION = "2026-09-23"
A_REF = f"sha256:{A_SHA}:bytes:{A_BYTES}:session:{A_SESSION}"
B_REF = f"sha256:{B_SHA}:bytes:{B_BYTES}:session:{B_SESSION}"
GUARD_IF = "            if existing_session is not None and new_session < existing_session:"
GUARD_BLOCK = '''            if existing_session is not None and new_session < existing_session:
                reason = (
                    f"resolved session {new_session} older than existing artifact "
                    f"{existing_session}"
                )
                log.error("options_matrix_builder: withheld %s — %s", root, reason)
                results[root] = {
                    "n_cells": 0, "uploaded": False, "error": None, "no_data": reason,
                }
                continue
'''


def _load_harness():
    here = Path(__file__).resolve().parent
    candidates = [
        here / "qualify_options_matrix_older_snapshot.py",
        here.parent / "scripts" / "qualify_options_matrix_older_snapshot.py",
    ]
    for path in candidates:
        if path.is_file() and not path.is_symlink():
            spec = spec_from_file_location("qualify_options_matrix_older_snapshot", str(path))
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("qualify_options_matrix_older_snapshot.py not found")


harness = _load_harness()


def locate_product_source() -> Path:
    env = os.environ.get("FABLE_MATRIX_SOURCE_REPO")
    candidates = []
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.append(here.parent.parent)
    for tree in candidates:
        if all((tree.joinpath(name).is_file() and not tree.joinpath(name).is_symlink()) for name in SOURCE_NAMES):
            return tree
    raise RuntimeError("product source tree unavailable; set FABLE_MATRIX_SOURCE_REPO")


def fixture_bytes(name: str) -> bytes:
    path = locate_product_source() / "tests" / "fixtures" / "options_matrix_retention" / f"{name}.json"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if name == "a":
        assert digest == A_SHA and len(raw) == A_BYTES, "unexpected a.json fixture"
    elif name == "b":
        assert digest == B_SHA and len(raw) == B_BYTES, "unexpected b.json fixture"
    return raw


def copy_repo(dst: Path, *, builder_bytes: bytes | None = None) -> Path:
    src = locate_product_source()
    for rel in SOURCE_NAMES:
        target = dst.joinpath(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = src.joinpath(rel).read_bytes()
        if rel == "scripts/build_options_matrix.py" and builder_bytes is not None:
            raw = builder_bytes
        target.write_bytes(raw)
    (dst / "engine" / "__init__.py").write_bytes(b"")
    (dst / "scripts" / "__init__.py").write_bytes(b"")
    return dst


def expected_files(repo: Path) -> list[str]:
    return [
        f"{rel}={hashlib.sha256(repo.joinpath(rel).read_bytes()).hexdigest()}"
        for rel in SOURCE_NAMES
    ]


def version_ref(raw: bytes, session: str, *, sha: str | None = None, size: int | None = None) -> str:
    digest = sha if sha is not None else hashlib.sha256(raw).hexdigest()
    count = size if size is not None else len(raw)
    return f"sha256:{digest}:bytes:{count}:session:{session}"


def synthetic_raw(*, root="SPY", session="2026-09-22", spot=100.0, cells=None) -> bytes:
    if cells is None:
        cells = [{"strike": 95.0, "expiry": "2026-10-16", "gex": 1, "call_oi": 1, "put_oi": 1}]
    doc = {
        "schema": "options_structure.matrix/v1",
        "root": root,
        "session": session,
        "_build_meta": {"asof_date": session},
        "asof": "2026-10-03T10:00:00Z",
        "spot": spot,
        "cells": cells,
    }
    return json.dumps(doc, allow_nan=False).encode()


class _Layout:
    def __init__(self, tmp: Path, candidate: bytes, existing: bytes, *, builder_bytes=None):
        self.repo = copy_repo(tmp / "repo", builder_bytes=builder_bytes)
        data = tmp / "inputs"
        data.mkdir()
        self.candidate = data / "candidate.json"
        self.existing = data / "existing.json"
        self.candidate.write_bytes(candidate)
        self.existing.write_bytes(existing)
        rec = tmp / "receipts"
        rec.mkdir()
        self.receipt = rec / "older-qualify.json"
        self.expected = expected_files(self.repo)
        self.candidate_raw = candidate
        self.existing_raw = existing


def _run(layout: _Layout, *, cand_ref: str, exist_ref: str, root="SPY", commit=COMMIT, expected=None):
    return harness.qualify_older_snapshot(
        root=root,
        candidate_json=str(layout.candidate),
        candidate_version_ref=cand_ref,
        existing_json=str(layout.existing),
        existing_version_ref=exist_ref,
        repo=str(layout.repo),
        source_commit=commit,
        receipt=str(layout.receipt),
        expected_source_files=layout.expected if expected is None else expected,
    )


class PreparatoryOlderCandidateTests(unittest.TestCase):
    """Preparatory only — not genuine older-candidate or live acceptance."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="test-qualify-older-")
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_preparatory_strictly_older_fixture_pair_succeeds(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        report = _run(layout, cand_ref=A_REF, exist_ref=B_REF)
        self.assertFalse(report["genuine_older_candidate_acceptance"])
        self.assertFalse(report["live_acceptance"])
        self.assertFalse(report["natural_session_proof"])
        self.assertFalse(report["production_invocation"])
        self.assertFalse(report["production_provenance_bound"])
        self.assertFalse(report["runtime_claim_verified"])
        self.assertEqual(report["qualification_kind"], "preparatory_isolated_withholding")
        self.assertTrue(report["exercise"]["withheld"])
        self.assertEqual(report["exercise"]["exit_code"], 1)
        self.assertTrue(report["exercise"]["head_unchanged"])
        self.assertEqual(report["exercise"]["history_writes"], 0)
        self.assertEqual(report["exercise"]["remote_writes"], 0)
        self.assertEqual(report["exercise"]["network_attempts"], 0)
        self.assertGreaterEqual(report["exercise"]["r2_constructions"], 1)
        self.assertIn(A_SESSION, report["exercise"]["withholding_reason"])
        self.assertIn(B_SESSION, report["exercise"]["withholding_reason"])
        self.assertEqual(layout.candidate.read_bytes(), layout.candidate_raw)
        self.assertEqual(layout.existing.read_bytes(), layout.existing_raw)
        receipt = json.loads(layout.receipt.read_bytes())
        self.assertFalse(receipt["genuine_older_candidate_acceptance"])
        self.assertIn("not proof of production provenance", receipt["provenance_note"])
        self.assertEqual(receipt["candidate"]["version_ref"], A_REF)
        self.assertEqual(receipt["existing"]["version_ref"], B_REF)

    def test_preparatory_synthetic_payloads_succeed(self):
        older = synthetic_raw(session="2026-09-01", spot=12.5)
        newer = synthetic_raw(session="2026-09-02", spot=13.5)
        layout = _Layout(self.tmp, older, newer)
        report = _run(
            layout,
            cand_ref=version_ref(older, "2026-09-01"),
            exist_ref=version_ref(newer, "2026-09-02"),
        )
        self.assertTrue(report["exercise"]["withheld"])
        self.assertFalse(report["genuine_older_candidate_acceptance"])
        self.assertEqual(report["exercise"]["history_writes"], 0)
        self.assertEqual(report["exercise"]["network_attempts"], 0)

    def test_reverse_dates_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("b"), fixture_bytes("a"))
        with self.assertRaises(harness.QualifyError) as ctx:
            _run(layout, cand_ref=B_REF, exist_ref=A_REF)
        self.assertNotIsInstance(ctx.exception, harness.QualifyFailed)
        self.assertIn("not strictly earlier", str(ctx.exception))
        self.assertFalse(layout.receipt.exists())

    def test_equal_dates_rejected(self):
        raw = fixture_bytes("a")
        layout = _Layout(self.tmp, raw, raw)
        with self.assertRaises(harness.QualifyError) as ctx:
            _run(layout, cand_ref=A_REF, exist_ref=A_REF)
        self.assertIn("not strictly earlier", str(ctx.exception))
        self.assertFalse(layout.receipt.exists())

    def test_corrupt_version_ref_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref="sha256:zzzz:bytes:1:session:2026-09-22", exist_ref=B_REF)
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=A_REF + "\n", exist_ref=B_REF)

    def test_mismatched_digest_and_length_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        wrong_sha = version_ref(layout.candidate_raw, A_SESSION, sha="a" * 64)
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=wrong_sha, exist_ref=B_REF)
        wrong_len = version_ref(layout.candidate_raw, A_SESSION, size=A_BYTES + 1)
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=wrong_len, exist_ref=B_REF)

    def test_mismatched_session_in_ref_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        wrong = version_ref(layout.candidate_raw, "2026-09-21", sha=A_SHA, size=A_BYTES)
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=wrong, exist_ref=B_REF)

    def test_cross_root_rejected(self):
        qqq = synthetic_raw(root="QQQ", session=A_SESSION)
        layout = _Layout(self.tmp, qqq, fixture_bytes("b"))
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=version_ref(qqq, A_SESSION), exist_ref=B_REF, root="SPY")
        other = self.tmp / "qqq-existing"
        other.mkdir()
        layout2 = _Layout(other, fixture_bytes("a"), qqq)
        with self.assertRaises(harness.QualifyError):
            _run(layout2, cand_ref=A_REF, exist_ref=version_ref(qqq, A_SESSION), root="SPY")

    def test_null_and_empty_payloads_rejected(self):
        null_spot = synthetic_raw(spot=100.0).replace(b"100.0", b"null", 1)
        empty = synthetic_raw(cells=[])
        layout = _Layout(self.tmp, null_spot, fixture_bytes("b"))
        with self.assertRaises(harness.QualifyError) as ctx:
            _run(layout, cand_ref=version_ref(null_spot, A_SESSION), exist_ref=B_REF)
        self.assertIn("spot", str(ctx.exception).lower())
        layout2 = _Layout(self.tmp / "empty", empty, fixture_bytes("b"))
        with self.assertRaises(harness.QualifyError) as ctx:
            _run(
                layout2,
                cand_ref=version_ref(empty, A_SESSION),
                exist_ref=B_REF,
            )
        self.assertIn("nonempty", str(ctx.exception).lower())

    def test_invalid_spot_zero_negative_nonfinite_rejected(self):
        newer = fixture_bytes("b")
        cases = [
            synthetic_raw(spot=0),
            synthetic_raw(spot=-1.5),
            b'{"schema":"options_structure.matrix/v1","root":"SPY","session":"2026-09-22","_build_meta":{"asof_date":"2026-09-22"},"spot":NaN,"cells":[{"strike":1,"expiry":"2026-10-16"}]}',
            b'{"schema":"options_structure.matrix/v1","root":"SPY","session":"2026-09-22","_build_meta":{"asof_date":"2026-09-22"},"spot":Infinity,"cells":[{"strike":1,"expiry":"2026-10-16"}]}',
        ]
        for raw in cases:
            sub = self.tmp / hashlib.sha256(raw).hexdigest()[:12]
            sub.mkdir()
            layout = _Layout(sub, raw, newer)
            session = A_SESSION
            try:
                ref = version_ref(raw, session)
            except Exception:
                ref = A_REF
            with self.assertRaises(harness.QualifyError):
                _run(layout, cand_ref=ref, exist_ref=B_REF)

    def test_invalid_calendar_date_not_coerced(self):
        raw = synthetic_raw(session="2026-02-30")
        layout = _Layout(self.tmp, raw, fixture_bytes("b"))
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=version_ref(raw, "2026-02-30"), exist_ref=B_REF)

    def test_invalid_root_and_commit_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=A_REF, exist_ref=B_REF, root="spy")
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=A_REF, exist_ref=B_REF, commit="6361F5E0E071DFC050C503E225AFE8A4897F0E8D")
        with self.assertRaises(harness.QualifyError):
            _run(layout, cand_ref=A_REF, exist_ref=B_REF, commit="6361f5e0")

    def test_expected_source_mismatch_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        wrong = [f"scripts/build_options_matrix.py={'0' * 64}"]
        with self.assertRaises(harness.QualifyError) as ctx:
            _run(layout, cand_ref=A_REF, exist_ref=B_REF, expected=wrong)
        self.assertIn("disagrees", str(ctx.exception))
        self.assertFalse(layout.receipt.exists())

    def test_symlink_inputs_and_existing_receipt_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        linked = self.tmp / "link-candidate.json"
        os.symlink(layout.candidate, linked)
        with self.assertRaises(harness.QualifyError):
            harness.qualify_older_snapshot(
                root="SPY",
                candidate_json=str(linked),
                candidate_version_ref=A_REF,
                existing_json=str(layout.existing),
                existing_version_ref=B_REF,
                repo=str(layout.repo),
                source_commit=COMMIT,
                receipt=str(layout.receipt),
                expected_source_files=layout.expected,
            )
        layout.receipt.write_bytes(b"{}\n")
        with self.assertRaises(harness.QualifyError) as ctx:
            _run(layout, cand_ref=A_REF, exist_ref=B_REF)
        self.assertIn("already exists", str(ctx.exception))

    def test_receipt_inside_repo_or_inputs_rejected(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        inside_repo = layout.repo / "receipt.json"
        with self.assertRaises(harness.QualifyError):
            harness.qualify_older_snapshot(
                root="SPY",
                candidate_json=str(layout.candidate),
                candidate_version_ref=A_REF,
                existing_json=str(layout.existing),
                existing_version_ref=B_REF,
                repo=str(layout.repo),
                source_commit=COMMIT,
                receipt=str(inside_repo),
                expected_source_files=layout.expected,
            )
        inside_inputs = layout.candidate.parent / "receipt.json"
        with self.assertRaises(harness.QualifyError):
            harness.qualify_older_snapshot(
                root="SPY",
                candidate_json=str(layout.candidate),
                candidate_version_ref=A_REF,
                existing_json=str(layout.existing),
                existing_version_ref=B_REF,
                repo=str(layout.repo),
                source_commit=COMMIT,
                receipt=str(inside_inputs),
                expected_source_files=layout.expected,
            )

    def _mutate_and_catch(self, mutate) -> dict:
        original = (locate_product_source() / "scripts" / "build_options_matrix.py").read_bytes()
        text = original.decode()
        self.assertIn(GUARD_IF, text)
        mutated = mutate(text).encode()
        self.assertNotEqual(mutated, original)
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"), builder_bytes=mutated)
        with self.assertRaises(harness.QualifyFailed) as ctx:
            _run(layout, cand_ref=A_REF, exist_ref=B_REF)
        report = ctx.exception.report
        exercise = report["exercise"]
        write_spy = (
            exercise["history_writes"] > 0
            or not exercise["head_unchanged"]
            or exercise["remote_writes"] > 0
            or exercise["network_attempts"] > 0
            or exercise.get("exit_code") == 0
            or not exercise["withheld"]
        )
        self.assertTrue(write_spy, msg=exercise.get("failures"))
        self.assertFalse(exercise["withheld"])
        self.assertFalse(layout.receipt.exists())
        self.assertEqual(layout.candidate.read_bytes(), layout.candidate_raw)
        self.assertEqual(layout.existing.read_bytes(), layout.existing_raw)
        return report

    def test_specific_withholding_with_wrong_exit_is_rejected(self):
        original = (locate_product_source() / "scripts" / "build_options_matrix.py").read_text()
        needle = "    if failed or no_data:\n        sys.exit(1)"
        self.assertIn(needle, original)
        mutated = original.replace(needle, "    if failed or no_data:\n        sys.exit(2)", 1).encode()
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"), builder_bytes=mutated)
        with self.assertRaises(harness.QualifyFailed) as ctx:
            _run(layout, cand_ref=A_REF, exist_ref=B_REF)
        self.assertTrue(ctx.exception.report["exercise"]["withheld"])
        self.assertEqual(ctx.exception.report["exercise"]["exit_code"], 2)
        self.assertFalse(layout.receipt.exists())

    def test_adversarial_guard_disabled_with_predicate_string_kept_is_caught(self):
        # Keep the source predicate string so a string-only test would miss this.
        def mutate(text: str) -> str:
            self.assertIn(GUARD_IF, text)
            return text.replace(
                GUARD_IF,
                "            if False and existing_session is not None and new_session < existing_session:",
                1,
            )
        report = self._mutate_and_catch(mutate)
        exercise = report["exercise"]
        self.assertTrue(
            exercise["history_writes"] > 0 or not exercise["head_unchanged"] or exercise["network_attempts"] > 0,
            msg="disabled guard must be caught by head-change or write spy",
        )

    def test_adversarial_guard_reversed_is_caught(self):
        def mutate(text: str) -> str:
            return text.replace(
                "new_session < existing_session",
                "new_session > existing_session",
                1,
            )
        report = self._mutate_and_catch(mutate)
        exercise = report["exercise"]
        self.assertTrue(
            exercise["history_writes"] > 0 or not exercise["head_unchanged"] or exercise["network_attempts"] > 0,
        )

    def test_adversarial_guard_removed_with_commented_predicate_is_caught(self):
        def mutate(text: str) -> str:
            self.assertIn(GUARD_BLOCK, text)
            replacement = (
                "            # new_session < existing_session remains only as text\n"
                "            # if existing_session is not None and new_session < existing_session:\n"
            )
            return text.replace(GUARD_BLOCK, replacement, 1)
        report = self._mutate_and_catch(mutate)
        exercise = report["exercise"]
        self.assertTrue(
            exercise["history_writes"] > 0 or not exercise["head_unchanged"] or exercise["network_attempts"] > 0,
        )

    def test_harness_source_has_no_shell_or_network_client_imports(self):
        src = Path(harness.__file__).read_text()
        for needle in (
            "import subprocess", "from subprocess",
            "import socket", "from socket",
            "import boto3", "from boto3",
            "import urllib", "from urllib",
            "import requests", "from requests",
            "import http.client", "from http.client",
        ):
            self.assertNotIn(needle, src)
        self.assertIn("scripts.build_options_matrix.main", src)
        self.assertIn("_payload_session", src)
        self.assertIn("_existing_usable_session", src)

    def test_cli_main_preparatory_success_and_failure_codes(self):
        layout = _Layout(self.tmp, fixture_bytes("a"), fixture_bytes("b"))
        argv = [
            "--root", "SPY",
            "--candidate-json", str(layout.candidate),
            "--candidate-version-ref", A_REF,
            "--existing-json", str(layout.existing),
            "--existing-version-ref", B_REF,
            "--repo", str(layout.repo),
            "--source-commit", COMMIT,
            "--receipt", str(layout.receipt),
        ]
        for item in layout.expected:
            argv.extend(["--expected-source-file", item])
        self.assertEqual(harness.main(argv), 0)
        self.assertTrue(layout.receipt.is_file())
        other = self.tmp / "fail-receipts"
        other.mkdir()
        argv_fail = argv[:]
        idx = argv_fail.index("--candidate-version-ref") + 1
        argv_fail[idx] = A_REF.replace(A_SESSION, "2026-09-21")
        argv_fail[argv_fail.index("--receipt") + 1] = str(other / "nope.json")
        self.assertEqual(harness.main(argv_fail), 1)


if __name__ == "__main__":
    unittest.main()
