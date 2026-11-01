"""Selector boundary must reject coercible analysis, without changing frozen RIO.

All model responses here are injected synthetic text; grounding uses the real
canonical quote verifier.  Entailment remains an explicit review obligation.
"""
import copy
import json
import unittest

from engine.research_intelligence import selection
from engine.research_intelligence.extractor import _identity, analyze_document

DOC = {"id": "selector-semantic-fixture", "source_type": "institutional_research"}
BODY = "The company said demand rose during the quarter. Margins did not improve despite stronger orders."


def payload():
    identity = _identity(DOC, BODY)
    catalog = selection.build_selection_catalog(identity, BODY)
    return {
        "selector": selection.SELECTOR_VERSION, "document": identity,
        "catalog_sha256": catalog["catalog_sha256"],
        "selections": [{"evidence_id": unit["evidence_id"]} for unit in catalog["units"]],
        "analysis": {"thesis": {
            "summary": "Demand improved while margins remained constrained.",
            "direction": "mixed", "mechanism": ["Higher demand did not translate into margin gains."],
            "conviction": "moderate", "support_claim_indices": [0, 1],
        }},
    }


def run(obj):
    calls = []
    def call(*args, **kwargs):
        calls.append(1)
        return json.dumps(obj), "synthetic", "synthetic-model"
    result = analyze_document(DOC, BODY, model_id="synthetic-model", call=call)
    return result, calls


class SelectorSemanticTransportTests(unittest.TestCase):
    def test_rejects_actual_canary_mechanism_object_shape(self):
        obj = payload()
        obj["analysis"]["thesis"]["mechanism"] = [{
            "statement": "Higher demand did not translate into margin gains.",
            "support_claim_indices": [0, 1],
        }]
        result, calls = run(obj)
        self.assertEqual(calls, [1])
        self.assertEqual(result["state"], "invalid_model_output")
        self.assertIsNone(result["rio"])
        with self.assertRaisesRegex(ValueError, "analysis.thesis.mechanism"):
            selection.parse_selector_output(json.dumps(obj), obj["document"], BODY)

    def test_valid_strings_survive_with_whole_thesis_support(self):
        obj = payload()
        result, calls = run(obj)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(calls, [1])
        self.assertEqual(result["rio"]["analysis"]["thesis"], obj["analysis"]["thesis"])
        self.assertEqual(result["source_context"]["coverage"], "PARTIAL_SOURCE_CONTEXT")

    def test_optional_analysis_fields_may_be_omitted(self):
        obj = payload()
        obj["analysis"]["thesis"].pop("mechanism")
        obj["analysis"]["thesis"].pop("conviction")
        result, _ = run(obj)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["rio"]["analysis"]["thesis"]["mechanism"], [])

    def test_thesis_text_coercion_and_truncation_rejected(self):
        for field, value in (("summary", {"text": "demand improved"}),
                             ("summary", "x" * 2501), ("conviction", 1),
                             ("direction", ["mixed"]), ("mechanism", "not a list"),
                             ("mechanism", [None]), ("mechanism", [False]),
                             ("mechanism", ["x" * 1201]), ("mechanism", ["x"] * 13)):
            with self.subTest(field=field, value_type=type(value).__name__):
                obj = payload(); obj["analysis"]["thesis"][field] = value
                self.assertEqual(run(obj)[0]["state"], "invalid_model_output")

    def test_analysis_rows_reject_coercion_without_silent_loss(self):
        for field in ("assumptions", "forecasts", "catalysts", "falsifiers", "counterarguments", "implications", "uncertainties"):
            for row in ({"statement": {"text": "inference"}, "support_claim_indices": [0]}, "not an object"):
                with self.subTest(field=field, row=row):
                    obj = payload(); obj["analysis"][field] = [row]
                    self.assertEqual(run(obj)[0]["state"], "invalid_model_output")

    def test_malformed_optional_support_drops_whole_assertion_without_recall(self):
        fields = ("assumptions", "forecasts", "catalysts", "falsifiers", "counterarguments", "implications", "uncertainties", "belief_delta", "consensus_relation")
        for field in fields:
            for support in ([0, True], [0, 2], [], None, "0", [0] * 30 + [1]):
                with self.subTest(field=field, support=support):
                    obj = payload()
                    row = {"statement": "Optional assertion must lose all support.", "support_claim_indices": support}
                    relation = field in ("belief_delta", "consensus_relation")
                    obj["analysis"][field] = row if relation else [row]
                    result, calls = run(obj)
                    self.assertEqual(result["state"], "ok")
                    self.assertEqual(calls, [1])
                    self.assertEqual(result["rio"]["analysis"][field], {"statement": "", "support_claim_indices": []} if relation else [])
                    self.assertEqual(result["rio"]["analysis"]["thesis"]["support_claim_indices"], [0, 1])

    def test_mandatory_thesis_support_still_rejects_malformed_values(self):
        for support in ([0, True], [0, 2], [], None, "0", [0] * 30 + [1]):
            with self.subTest(support=support):
                obj = payload(); obj["analysis"]["thesis"]["support_claim_indices"] = support
                self.assertEqual(run(obj)[0]["state"], "invalid_model_output")

    def test_optional_empty_content_retains_canonical_abstention(self):
        obj = payload()
        obj["analysis"]["assumptions"] = [{"statement": "", "support_claim_indices": []}]
        obj["analysis"]["belief_delta"] = {"statement": "", "support_claim_indices": []}
        result, _ = run(obj)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["rio"]["analysis"]["assumptions"], [])
        self.assertEqual(result["rio"]["analysis"]["belief_delta"], {"statement": "", "support_claim_indices": []})

    def test_optional_row_annotations_and_relations_are_typed(self):
        bad = [
            ("forecasts", [{"statement": "inference", "support_claim_indices": [0], "horizon": {"year": 2027}}]),
            ("forecasts", [{"statement": "inference", "support_claim_indices": [0], "confidence": 0.5}]),
            ("implications", [{"statement": "inference", "support_claim_indices": [0], "assets": [{"ticker": "ACME"}]}]),
            ("implications", [{"statement": "inference", "support_claim_indices": [0], "order": True}]),
            ("belief_delta", {"statement": {"text": "changed"}, "support_claim_indices": [0]}),
            ("uncertainties", {"statement": "not a list", "support_claim_indices": [0]}),
        ]
        for field, value in bad:
            with self.subTest(field=field, value=value):
                obj = payload(); obj["analysis"][field] = value
                self.assertEqual(run(obj)[0]["state"], "invalid_model_output")

    def test_valid_optional_annotations_and_empty_relations_survive(self):
        obj = payload()
        obj["analysis"].update({
            "forecasts": [{"statement": "Order growth may persist.", "support_claim_indices": [0], "horizon": "next quarter", "confidence": "conditional"}],
            "implications": [{"statement": "Margin outcomes warrant monitoring.", "support_claim_indices": [1], "assets": ["ACME"], "direction": "unclear", "order": 2}],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
        })
        result, _ = run(obj)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["rio"]["analysis"]["forecasts"], obj["analysis"]["forecasts"])
        self.assertEqual(result["rio"]["analysis"]["implications"], obj["analysis"]["implications"])

    def test_canonical_uncapped_forecast_and_implication_counts_remain_compatible(self):
        obj = payload()
        row = {"statement": "Margin outcomes warrant monitoring.", "support_claim_indices": [1]}
        for field in ("forecasts", "implications"):
            obj["analysis"][field] = [dict(row) for _ in range(31)]
        result, _ = run(obj)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(len(result["rio"]["analysis"]["forecasts"]), 31)
        self.assertEqual(len(result["rio"]["analysis"]["implications"]), 31)

    def test_unknown_analysis_fields_are_not_silently_discarded(self):
        obj = payload(); obj["analysis"]["thesis"]["secret_extra_assertion"] = "unsupported"
        self.assertEqual(run(obj)[0]["state"], "invalid_model_output")
        obj = payload(); obj["analysis"]["trade_size"] = "large"
        self.assertEqual(run(obj)[0]["state"], "invalid_model_output")

    def test_prompt_explains_exact_mechanism_shape_and_entailment_obligation(self):
        system, user, _ = selection.build_selector_prompt(_identity(DOC, BODY), BODY)
        shape = json.loads(user.split("OUTPUT SHAPE:\n", 1)[1].split("\n\n", 1)[0])
        self.assertTrue(shape["analysis"]["thesis"]["mechanism"])
        self.assertTrue(all(type(item) is str for item in shape["analysis"]["thesis"]["mechanism"]))
        self.assertIn("mechanism MUST be a list of strings", system)
        self.assertIn("Every proposition", system)
        self.assertIn("union", system)
        self.assertIn("select fewer than 30", system)
        self.assertIn("omit", system)
        self.assertIn("column", system)


if __name__ == "__main__":
    unittest.main()
