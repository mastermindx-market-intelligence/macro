"""Parent review discriminators: real quote law and injected synthetic calls only."""
import json
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine.research_intelligence import selection
from engine.research_intelligence.extractor import (
    _analyze_document_selector_v3, _identity, analyze_document,
)
from engine.research_intelligence.store import (
    ResearchIntelligenceInvalid, artifact_object_key, load_latest_research_intelligence,
    load_research_intelligence_version, persist_analysis, validate_analysis_for_persistence,
)
from engine.research_vault.r2_store import LocalStore

DOC = {"id": "selector-contract-fixture", "source_type": "institutional_research"}
BODY = (
    "The company said orders rose during the current quarter. "
    "Revenue did not decline despite higher operating costs. "
    "The report described margins holding steady into next year."
)


def analysis():
    return {"thesis": {"summary": "Operating evidence points to resilience.",
                       "direction": "unclear", "support_claim_indices": [0]}}


def payload(identity, catalog):
    return {"selector": selection.SELECTOR_VERSION, "document": identity,
            "catalog_sha256": catalog["catalog_sha256"],
            "selections": [{"evidence_id": catalog["units"][0]["evidence_id"]}],
            "analysis": analysis()}


def selector_call(calls):
    def call(system, user, **kwargs):
        calls.append(user)
        identity = json.loads(user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\n", 1)[0])
        catalog = json.loads(user.split("EVIDENCE CATALOG:\n", 1)[1].split("\n\n", 1)[0])
        return json.dumps(payload(identity, catalog)), "synthetic", "synthetic-model"
    return call


class ParentContractDiscriminators(unittest.TestCase):
    def test_public_default_uses_selector(self):
        calls = []
        result = analyze_document(DOC, BODY, model_id="synthetic-model", call=selector_call(calls))
        self.assertEqual(result["state"], "ok")
        self.assertEqual(len(calls), 1)

    def test_public_default_refuses_old_copy_only_rio(self):
        calls = []
        def old_call(*args, **kwargs):
            calls.append(1)
            quote = "Revenue did not decline despite higher operating costs."
            obj = {"schema": "mastermind.research_intelligence.v1", "document": _identity(DOC, BODY),
                   "claims": [{"statement": quote, "evidence": [{"quote_span": quote}]}],
                   "analysis": analysis(), "authority": "descriptive_research_only"}
            return json.dumps(obj), "synthetic", "synthetic-model"
        result = analyze_document(DOC, BODY, model_id="synthetic-model", call=old_call)
        self.assertEqual(result["state"], "invalid_model_output")
        self.assertEqual(calls, [1])

    def test_constructor_rebinds_body_digest(self):
        identity = _identity(DOC, BODY)
        identity["content_sha256"] = "0" * 64
        with self.assertRaises(selection.SelectionUnavailable):
            selection.build_selection_catalog(identity, BODY)

    def test_actual_verifier_work_limit(self):
        limit = 2 * len(BODY.encode("utf-8"))
        with patch.object(selection, "MAX_VERIFIER_WORK_BYTES", limit, create=True):
            with self.assertRaises(selection.SelectionUnavailable) as caught:
                selection.build_selection_catalog(_identity(DOC, BODY), BODY)
        self.assertEqual(caught.exception.code, "SELECTION_VERIFIER_WORK_OVERFLOW")

    def test_raw_output_limit_is_utf8_bytes(self):
        identity = _identity(DOC, BODY)
        catalog = selection.build_selection_catalog(identity, BODY)
        obj = payload(identity, catalog)
        obj["analysis"]["thesis"]["summary"] = "安定" * 80
        raw = json.dumps(obj, ensure_ascii=False)
        limit = len(raw) + 1
        self.assertGreater(len(raw.encode("utf-8")), limit)
        with patch.object(selection, "MAX_SELECTOR_OUTPUT_BYTES", limit, create=True):
            with self.assertRaises(ValueError):
                selection.parse_selector_output(raw, identity, BODY)

    def test_duplicate_identity_key_is_refused(self):
        identity = _identity(DOC, BODY)
        catalog = selection.build_selection_catalog(identity, BODY)
        raw = '{"document":{"id":"discarded-invalid-identity"},' + json.dumps(payload(identity, catalog))[1:]
        with self.assertRaises(ValueError):
            selection.parse_selector_output(raw, identity, BODY)

    def test_v3_success_recomputes_and_is_persistable(self):
        result = _analyze_document_selector_v3(
            DOC, BODY, model_id="synthetic-model", max_tokens=6000, call=selector_call([]))
        self.assertEqual(result["state"], "ok")
        validate_analysis_for_persistence(result, source_body=BODY)

    def test_preflight_reserves_both_catalog_passes_without_model_call(self):
        calls = []
        with patch.object(selection, "MAX_VERIFIER_WORK_BYTES", 4 * len(BODY.encode())):
            result = analyze_document(DOC, BODY, model_id="synthetic-model", call=selector_call(calls))
        self.assertEqual(result["state"], "selection_unavailable")
        self.assertEqual(result["error_code"], "SELECTION_VERIFIER_WORK_OVERFLOW")
        self.assertEqual(calls, [])

    def test_exact_two_pass_budget_and_complete_serialized_catalog_count(self):
        identity = _identity(DOC, BODY)
        catalog = selection.build_selection_catalog(identity, BODY)
        encoded = json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()
        self.assertEqual(catalog["metadata"]["catalog_bytes"], len(encoded))
        required = 2 * catalog["metadata"]["verifier_work_bytes"]
        with patch.object(selection, "MAX_VERIFIER_WORK_BYTES", required):
            result = analyze_document(DOC, BODY, model_id="synthetic-model", call=selector_call([]))
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["source_context"]["required_analysis_verifier_work_bytes"], required)

    def test_success_context_is_retained_on_latest_and_version_reload(self):
        body = "x" * 1701 + ". " + BODY
        result = analyze_document(DOC, body, model_id="synthetic-model", call=selector_call([]))
        self.assertEqual(result["state"], "ok")
        context = result["source_context"]
        self.assertEqual(context["coverage"], "PARTIAL_SOURCE_CONTEXT")
        self.assertIs(context["exhaustive_source_coverage"], False)
        self.assertEqual(context["omitted_overlong"], 1)
        with tempfile.TemporaryDirectory(prefix="rv-selector-store-") as temporary:
            store = LocalStore(Path(temporary))
            receipt = persist_analysis(store, result, source_body=body)
            latest = load_latest_research_intelligence(store, DOC["id"])
            version = load_research_intelligence_version(store, DOC["id"], receipt.artifact_sha256)
            self.assertEqual(latest.receipt["source_context"], context)
            self.assertEqual(version.receipt["source_context"], context)
            self.assertEqual(latest.rio, result["rio"])
        self.assertFalse(Path(temporary).exists())

    def test_context_tamper_absence_extra_version_and_body_are_rejected_before_io(self):
        result = analyze_document(DOC, BODY, model_id="synthetic-model", call=selector_call([]))
        context = result["source_context"]
        mutations = []
        for key, value in context.items():
            if key == "limits":
                for limit in value:
                    item = copy.deepcopy(result)
                    item["source_context"]["limits"][limit] += 1
                    mutations.append(("limit:" + limit, item))
            else:
                item = copy.deepcopy(result)
                item["source_context"][key] = (not value if type(value) is bool else value + 1 if type(value) is int else "tampered")
                mutations.append((key, item))
        absent = copy.deepcopy(result); absent.pop("source_context")
        extra = copy.deepcopy(result); extra["source_context"]["unexpected"] = 1
        old = copy.deepcopy(result); old["prompt_version"] = "mastermind.research_intelligence.extractor.v2"
        # Arithmetically consistent forged catalog metadata still fails exact body recomputation.
        forged = copy.deepcopy(result)
        forged["source_context"]["catalog_sha256"] = "0" * 64
        mutations.extend([("absent", absent), ("extra", extra), ("old-version", old), ("forged-catalog", forged)])
        for name, item in mutations:
            with self.subTest(name=name), self.assertRaises(ResearchIntelligenceInvalid):
                validate_analysis_for_persistence(item, source_body=BODY)
        with self.assertRaises(ResearchIntelligenceInvalid):
            validate_analysis_for_persistence(result, source_body=BODY + " Changed source.")

    def test_reload_refuses_hash_tamper_and_closed_context_or_old_version_with_rehashed_bytes(self):
        result = analyze_document(DOC, BODY, model_id="synthetic-model", call=selector_call([]))
        with tempfile.TemporaryDirectory(prefix="rv-selector-store-") as temporary:
            store = LocalStore(Path(temporary))
            receipt = persist_analysis(store, result, source_body=BODY)
            stored = load_latest_research_intelligence(store, DOC["id"])
            raw = store.get_bytes(stored.artifact_key)
            tampered = json.loads(raw)
            tampered["receipt"]["source_context"]["coverage"] = "COMPLETE"
            store.put_bytes(stored.artifact_key, json.dumps(tampered).encode(), "application/json")
            with self.assertRaises(ResearchIntelligenceInvalid) as caught:
                load_research_intelligence_version(store, DOC["id"], receipt.artifact_sha256)
            self.assertEqual(caught.exception.code, "artifact_hash_mismatch")
            for name in ("missing", "extra", "old", "boolean-count"):
                item = json.loads(raw)
                if name == "missing": item["receipt"].pop("source_context")
                elif name == "extra": item["receipt"]["source_context"]["extra"] = 1
                elif name == "old": item["receipt"]["prompt_version"] = "mastermind.research_intelligence.extractor.v2"
                else: item["receipt"]["source_context"]["proposed_units"] = True
                data = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
                digest = hashlib.sha256(data).hexdigest()
                store.put_bytes(artifact_object_key(DOC["id"], digest), data, "application/json")
                with self.subTest(name=name), self.assertRaises(ResearchIntelligenceInvalid):
                    load_research_intelligence_version(store, DOC["id"], digest)
        self.assertFalse(Path(temporary).exists())


if __name__ == "__main__":
    unittest.main()
