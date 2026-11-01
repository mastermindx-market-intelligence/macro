"""Actual private journal creation plus hostile-event discrimination; no live effects."""

import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

from engine.research_vault import generation_recovery as subject
from engine.research_vault import catalog
from engine.research_vault import producer_generation_writer as writer
from engine.research_vault import producer_generation as contract
from engine.research_vault.generation_evidence import (
    FileGenerationEvidence,
    read_evidence,
)
from engine.research_vault.r2_store import LocalStore

IDENTITY = {"source_commit": "a" * 40, "run": "synthetic-original-plan-test"}
NOW = datetime(2026, 10, 14, 16, tzinfo=timezone.utc)


class RecoverabilityTests(unittest.TestCase):
    def fixture(self, issued=0, promote=False, existing_pdfs=False, corpus_bytes=None):
        temp = tempfile.TemporaryDirectory(prefix="private-original-plan-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        store = LocalStore(root / "store")
        doc = {
            "schema": catalog.SCHEMA,
            "generated_at": NOW.isoformat(),
            "count": 2,
            "institutions": ["Desk"],
            "items": [
                {"id": rid, "title": "Synthetic " + rid, "institution": "Desk"}
                for rid in ("report-a", "report-b")
            ],
        }
        store.put_bytes(catalog.CATALOG_KEY, json.dumps(doc).encode())
        receipts = [
            (
                "research_inbox/_processed/" + rid + ".json",
                json.dumps(
                    {
                        "id": rid,
                        "content_sha256": (
                            hashlib.sha256(rid.encode()).hexdigest()
                            if promote or existing_pdfs
                            else "b" * 64
                        ),
                    }
                ).encode(),
            )
            for rid in ("report-a", "report-b")
        ]
        corpus = root / "corpus.sqlite"
        corpus.write_bytes(b"synthetic original corpus bytes" if corpus_bytes is None else corpus_bytes)
        if existing_pdfs:
            for rid in ("report-a", "report-b"):
                store.put_bytes("research_vault/" + rid + ".pdf", rid.encode())
        path = root / "original.jsonl"
        with FileGenerationEvidence.create(path, IDENTITY) as evidence:
            session = writer.ProducerGenerationSession.begin(
                store, doc, IDENTITY, now=NOW, evidence=evidence
            )
            if promote:
                for rid in ("report-a", "report-b"):
                    session.put(
                        "research_vault/" + rid + ".pdf",
                        rid.encode(),
                        "application/pdf",
                    )
            prepared = session.prepare_catalog(doc)
            session.record_publication(corpus, receipts, catalog_bytes=prepared)
            session.put(
                contract.CORPUS_KEY, corpus.read_bytes(), "application/x-sqlite3"
            )
            session.put(catalog.CATALOG_KEY, prepared, "application/json")
            for key, body in receipts[:issued]:
                session.put(key, body, "application/json")
            # The original invocation now closes without any additional effect;
            # its real append-only capture is retained, never re-fingerprinted.
        digest = evidence.capture_sha256
        events = read_evidence(path, expected_identity=IDENTITY, expected_sha256=digest)
        return path, digest, events, receipts, store

    def analyze(self, events):
        return subject.analyze_settled_publication(events, expected_identity=IDENTITY)

    def refuses(self, events):
        with self.assertRaises(subject.RecoveryPlanUnavailable):
            self.analyze(events)

    def test_actual_original_journal_reconstructs_unissued_tail_without_writes(self):
        for issued in (0, 1, 2):
            with self.subTest(issued=issued):
                path, digest, events, receipts, store = self.fixture(issued)
                before = {
                    str(p): p.read_bytes() for p in store.root.rglob("*") if p.is_file()
                }
                plan = subject.inspect_settled_publication(
                    path, expected_identity=IDENTITY, original_capture_sha256=digest
                )
                self.assertEqual(plan["unissued_receipts"], tuple(receipts[issued:]))
                self.assertEqual(plan["state"], "REQUIRES_OWNER_AND_LIVE_VALIDATION")
                self.assertIs(plan["execution_authorized"], False)
                self.assertEqual(
                    plan["catalog_bytes"], store.get_bytes(catalog.CATALOG_KEY)
                )
                self.assertEqual(
                    plan["corpus_sha256"],
                    hashlib.sha256(store.get_bytes(contract.CORPUS_KEY)).hexdigest(),
                )
                self.assertEqual(len(plan["required_live_checks"]), 2 + issued)
                self.assertEqual(
                    before,
                    {
                        str(p): p.read_bytes()
                        for p in store.root.rglob("*")
                        if p.is_file()
                    },
                )

    def test_public_api_requires_exact_original_capture_and_identity(self):
        path, digest, _, _, _ = self.fixture()
        for sha, identity in [
            ("0" * 64, IDENTITY),
            (None, IDENTITY),
            (digest, {**IDENTITY, "run": "successor"}),
        ]:
            with self.subTest(sha=sha, identity=identity), self.assertRaises(
                subject.RecoveryPlanUnavailable
            ):
                subject.inspect_settled_publication(
                    path, expected_identity=identity, original_capture_sha256=sha
                )

    def test_live_original_journal_is_not_a_closed_capture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "open.jsonl"
        with FileGenerationEvidence.create(path, IDENTITY):
            with self.assertRaises(subject.RecoveryPlanUnavailable):
                subject.inspect_settled_publication(
                    path, expected_identity=IDENTITY, original_capture_sha256="0" * 64
                )

    def test_every_uncertain_or_rejected_result_refuses_even_after_visible_publication(
        self,
    ):
        _, _, events, _, _ = self.fixture(1)
        for outcome in (
            "exception_effect_unknown",
            "returned_false_effect_unknown",
            "conditional_conflict",
            None,
            True,
        ):
            for index, event in enumerate(events):
                if event["kind"] == "write_result":
                    bad = copy.deepcopy(events)
                    bad[index]["payload"]["outcome"] = outcome
                    with self.subTest(outcome=outcome, index=index):
                        self.refuses(bad)

    def test_unsettled_intent_and_unobserved_catalog_cuts_refuse(self):
        _, _, events, _, _ = self.fixture(1)
        for index, event in enumerate(events):
            if event["kind"] == "write_intent" or (
                event["kind"] == "write_result"
                and events[index - 1]["payload"].get("key") == catalog.CATALOG_KEY
            ):
                with self.subTest(index=index):
                    self.refuses(copy.deepcopy(events[: index + 1]))

    def test_orphan_duplicate_and_bool_result_references_refuse(self):
        _, _, events, _, _ = self.fixture(1)
        result = next(i for i, e in enumerate(events) if e["kind"] == "write_result")
        for reference in (True, 0, 999, "1"):
            bad = copy.deepcopy(events)
            bad[result]["payload"]["operation"] = reference
            self.refuses(bad)
        self.refuses(events + [copy.deepcopy(events[-1])])
        observed = next(e for e in events if e["kind"] == "catalog_observed")
        self.refuses(events + [copy.deepcopy(observed)])

    def test_plan_and_catalog_observation_bind_exact_predecessor(self):
        _, _, events, _, _ = self.fixture()
        pi = next(i for i, e in enumerate(events) if e["kind"] == "publication_plan")
        for field, value in [
            ("catalog_predecessor_sha256", "0" * 64),
            ("catalog_predecessor_version", "other"),
            ("epoch", "other"),
        ]:
            bad = copy.deepcopy(events)
            bad[pi]["payload"][field] = value
            self.refuses(bad)
        for field, value in [
            ("sha256", "0" * 64),
            ("operation", True),
            ("version", ""),
        ]:
            bad = copy.deepcopy(events)
            bad[-1]["payload"][field] = value
            self.refuses(bad)

    def test_plan_body_digest_size_and_encoding_are_independent_checks(self):
        _, _, events, _, _ = self.fixture()
        pi = next(i for i, e in enumerate(events) if e["kind"] == "publication_plan")
        for field, value in [
            ("catalog_sha256", "0" * 64),
            ("catalog_bytes", True),
            ("catalog_base64", "bad!"),
            ("catalog_base64", events[pi]["payload"]["catalog_base64"] + "\n"),
            ("corpus_bytes", contract.CORPUS_MAX_BYTES + 1),
        ]:
            bad = copy.deepcopy(events)
            bad[pi]["payload"][field] = value
            self.refuses(bad)
        bad = copy.deepcopy(events)
        bad[pi]["payload"]["pending_receipts"][0]["sha256"] = "0" * 64
        self.refuses(bad)
        bad = copy.deepcopy(events)
        bad[pi]["payload"]["pending_receipts"][0]["bytes"] = True
        self.refuses(bad)

    def test_receipts_cannot_be_duplicated_reordered_or_leave_visible_catalog(self):
        _, _, events, _, _ = self.fixture(1)
        pi = next(i for i, e in enumerate(events) if e["kind"] == "publication_plan")
        bad = copy.deepcopy(events)
        bad[pi]["payload"]["pending_receipts"][1] = copy.deepcopy(
            bad[pi]["payload"]["pending_receipts"][0]
        )
        self.refuses(bad)
        bad = copy.deepcopy(events)
        bad[pi]["payload"]["pending_receipts"].reverse()
        self.refuses(bad)
        bad = copy.deepcopy(events)
        bad[pi]["payload"]["pending_receipts"][0][
            "key"
        ] = "research_inbox/_processed/not-in-catalog.json"
        self.refuses(bad)

    def test_multiple_plans_terminal_and_unplanned_tail_are_not_silently_salvaged(self):
        _, _, events, _, _ = self.fixture()
        plan = next(e for e in events if e["kind"] == "publication_plan")
        self.refuses(events + [copy.deepcopy(plan)])
        self.refuses(events + [{"kind": "terminal", "payload": {"state": "COMPLETE"}}])
        bad = copy.deepcopy(events)
        tail = copy.deepcopy(events[1])
        tail["payload"]["key"] = contract.CORPUS_KEY
        tail["payload"].pop("catalog_base64")
        tail["payload"]["conditional"] = False
        tail["payload"]["expected_version"] = None
        tail["payload"]["content_type"] = "application/x-sqlite3"
        bad.append(tail)
        self.refuses(bad)

    def test_source_run_epoch_and_current_catalog_cannot_be_rebound(self):
        _, _, events, _, _ = self.fixture()
        for field, value in [
            ("producer_source_commit", "f" * 40),
            ("producer_run", "other"),
            ("state", "COMPLETE"),
        ]:
            bad = copy.deepcopy(events)
            blob = base64.b64decode(bad[1]["payload"]["catalog_base64"])
            doc = json.loads(blob)
            doc["producer_generation"][field] = value
            body = json.dumps(doc).encode()
            bad[1]["payload"].update(
                catalog_base64=base64.b64encode(body).decode(),
                sha256=hashlib.sha256(body).hexdigest(),
                bytes=len(body),
            )
            self.refuses(bad)

    def test_receipt_uses_strict_utf8_unique_fields_and_canonical_source_digest(self):
        _, _, events, _, _ = self.fixture()
        plan_index = next(
            i for i, e in enumerate(events) if e["kind"] == "publication_plan"
        )
        for raw in (
            b'{"id":"report-a","id":"report-a","content_sha256":"' + b"b" * 64 + b'"}',
            b'{"id":"report-a","content_sha256":"' + b"b" * 64 + b'","unknown":NaN}',
            b'{"id":"report-a","content_sha256":true}',
            b'{"id":"report-a","content_sha256":"missing"}',
            json.dumps({"id": "report-a", "content_sha256": "b" * 64}).encode("utf-16"),
        ):
            bad = copy.deepcopy(events)
            bad[plan_index]["payload"]["pending_receipts"][0].update(
                body_base64=base64.b64encode(raw).decode(),
                bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
            )
            with self.subTest(raw=raw[:48]):
                self.refuses(bad)

    def test_receipt_digest_must_match_original_acknowledged_pdf_when_present(self):
        _, _, events, receipts, _ = self.fixture(promote=True)
        self.assertEqual(self.analyze(events)["unissued_receipts"], tuple(receipts))
        plan_index = next(
            i for i, e in enumerate(events) if e["kind"] == "publication_plan"
        )
        bad = copy.deepcopy(events)
        raw = json.dumps({"id": "report-a", "content_sha256": "c" * 64}).encode()
        bad[plan_index]["payload"]["pending_receipts"][0].update(
            body_base64=base64.b64encode(raw).decode(),
            bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
        )
        with self.assertRaisesRegex(
            subject.RecoveryPlanUnavailable, "RECEIPT_PROMOTED_PDF_MISMATCH"
        ):
            self.analyze(bad)

    def live(self, store, path, digest, **kwargs):
        return subject.inspect_live_settled_publication(
            store, path, expected_identity=IDENTITY,
            original_capture_sha256=digest, **kwargs,
        )

    def readonly(self, store):
        calls = []
        class Reader:
            def get_bytes_strict_bounded(self, key, maximum):
                calls.append((key, maximum))
                return store.get_bytes_strict_bounded(key, maximum)
            def get_bytes_strict_bounded_versioned(self, key, maximum):
                calls.append((key, maximum))
                return store.get_bytes_strict_bounded_versioned(key, maximum)
        return Reader(), calls

    def test_live_reader_matches_original_tail_without_writer_capabilities(self):
        for issued in (0, 1, 2):
            with self.subTest(issued=issued):
                path, digest, _, receipts, store = self.fixture(issued, promote=True)
                reader, calls = self.readonly(store)
                before = {str(p): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
                result = self.live(reader, path, digest)
                self.assertEqual(result['state'], 'LIVE_BYTES_OBSERVED_OWNER_VALIDATION_REQUIRED')
                self.assertEqual(result['unissued_receipts'], tuple(receipts[issued:]))
                self.assertIs(result['execution_authorized'], False)
                self.assertGreater(result['read_budget_used'], 0)
                self.assertEqual(sum(key == catalog.CATALOG_KEY for key, _ in calls), 2)
                self.assertEqual(before, {str(p): p.read_bytes() for p in store.root.rglob('*') if p.is_file()})

    def test_live_reads_existing_planned_pdfs_not_only_original_promotions(self):
        path, digest, _, _, store = self.fixture(existing_pdfs=True)
        reader, calls = self.readonly(store)
        self.live(reader, path, digest)
        self.assertIn('research_vault/report-a.pdf', {key for key, _ in calls})
        store.put_bytes('research_vault/report-a.pdf', b'not original')
        with self.assertRaisesRegex(subject.RecoveryPlanUnavailable, 'LIVE_PDF_CHANGED'):
            self.live(reader, path, digest)

    def test_live_refuses_changed_acknowledged_corpus_or_missing_promoted_pdf(self):
        for missing in (False, True):
            path, digest, _, _, store = self.fixture(promote=True)
            reader, _ = self.readonly(store)
            read = reader.get_bytes_strict_bounded
            def changed(key, maximum):
                if missing and key.endswith('report-a.pdf'):
                    return None
                raw = read(key, maximum)
                return b'x' * len(raw) if not missing and key == contract.CORPUS_KEY else raw
            reader.get_bytes_strict_bounded = changed
            with self.assertRaises(subject.RecoveryPlanUnavailable):
                self.live(reader, path, digest)

    def test_live_refuses_same_catalog_bytes_with_changed_version_before_or_after_reads(self):
        from engine.research_vault.r2_store import VersionedBytes
        for change_at in (1, 2):
            path, digest, _, _, store = self.fixture(promote=True)
            reader, _ = self.readonly(store)
            read, count = reader.get_bytes_strict_bounded_versioned, 0
            def changed(key, maximum):
                nonlocal count
                value = read(key, maximum)
                count += 1
                return VersionedBytes(value.data, value.version + '-moved') if count == change_at else value
            reader.get_bytes_strict_bounded_versioned = changed
            with self.assertRaisesRegex(subject.RecoveryPlanUnavailable, 'LIVE_CATALOG_MOVED'):
                self.live(reader, path, digest)

    def test_live_visible_unissued_receipt_is_not_settlement_even_when_matching(self):
        for raw in (None, b'', b'x'):
            path, digest, _, receipts, store = self.fixture(promote=True)
            key, original = receipts[0]
            store.put_bytes(key, original if raw is None else raw)
            reader, _ = self.readonly(store)
            with self.assertRaises(subject.RecoveryPlanUnavailable):
                self.live(reader, path, digest)

    def test_live_invalid_capture_or_budget_refuses_without_store_reads(self):
        path, digest, _, _, store = self.fixture(promote=True)
        reader, calls = self.readonly(store)
        with self.assertRaises(subject.RecoveryPlanUnavailable):
            self.live(reader, path, '0' * 64)
        for budget in (True, 0, -1, 1024 * 1024 * 1024 + 1, '100'):
            with self.assertRaises(subject.RecoveryPlanUnavailable):
                self.live(reader, path, digest, byte_budget=budget)
        self.assertEqual(calls, [])
        with self.assertRaises(subject.RecoveryPlanUnavailable):
            self.live(reader, path, digest, byte_budget=1)
        self.assertTrue(calls and all(maximum <= 1 for _, maximum in calls))

    def test_live_store_contract_and_transport_failures_are_sanitized(self):
        path, digest, _, _, store = self.fixture(promote=True)
        for mode in ('oversized', 'bytearray', 'transport'):
            reader, _ = self.readonly(store)
            def malformed(key, maximum):
                if mode == 'transport':
                    raise OSError('PRIVATE_ENDPOINT_AND_CREDENTIAL')
                return b'x' * (maximum + 1) if mode == 'oversized' else bytearray(b'x')
            reader.get_bytes_strict_bounded = malformed
            with self.assertRaises(subject.RecoveryPlanUnavailable) as caught:
                self.live(reader, path, digest)
            self.assertNotIn('PRIVATE_', str(caught.exception))


if __name__ == "__main__":
    unittest.main()
