"""Leaf-scope synthetic tests for the private selector-v3 contract.

Fixture scope: canonical quote-law functions copied unchanged into the pure
fixture module, the pinned frozen schema, the pinned extractor with the
additive v3 edge, and the new pure selection module.  No provider, config,
store, corpus, credential, or network is touched; every model interaction is
an injected fake call.  Quote verification is never monkeypatched into
success: catalog admission and final grounding run the real canonical law.
"""
import json
import unittest

from engine.qual_extraction import propose_quote_units, quote_span_verified
from engine.research_intelligence import selection
from engine.research_intelligence.extractor import PROMPT_VERSION, _identity, analyze_document
from engine.research_intelligence.selection import (
    SELECTOR_SYSTEM_PROMPT,
    SELECTOR_VERSION,
    build_selector_prompt,
)

DOC = {
    "id": "doc-selector-v3-1",
    "source_type": "institutional_research",
    "source_name": "Fixture Research Partners",
    "institution": "Fixture Institute",
    "desk": "Synthetic Desk",
    "title": "Synthetic selector fixture note",
    "published_at": "2026-10-01",
}

BODY = (
    "Dr. Smith said cloud orders rose 3.5% in the third quarter. "
    "Revenue did not decline, and AMD gained share.\n"
    "The firm wrote that margins\nheld despite the wrap."
)
UNIT_ABBREV = "Dr. Smith said cloud orders rose 3.5% in the third quarter."
UNIT_POLARITY = "Revenue did not decline, and AMD gained share."
UNIT_WRAP = "The firm wrote that margins\nheld despite the wrap."
OTHER_BODY = "Different research entirely. Nothing here matches the first body."
CLAIM_LEGACY = UNIT_POLARITY


def identity_for(body, doc=None):
    return _identity(doc or DOC, body)


def fake_call(payload_builder):
    calls = []

    def _call(system, user, *, model_id, max_tokens):
        calls.append(
            {"system": system, "user": user, "model_id": model_id, "max_tokens": max_tokens}
        )
        return payload_builder(system, user), "fixture-provider", f"served-{model_id}"

    return _call, calls


def prompt_catalog(user):
    return json.loads(
        user.split("EVIDENCE CATALOG:\n", 1)[1].split("\n\n", 1)[0]
    )


def prompt_identity(user):
    return json.loads(
        user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:\n", 1)[0]
    )


def default_analysis(count):
    return {
        "thesis": {
            "summary": "The note argues cloud ordering strengthens server demand.",
            "direction": "bullish",
            "mechanism": ["cloud ordering supports server demand"],
            "conviction": "moderate",
            "support_claim_indices": [0],
        },
        "assumptions": [], "forecasts": [], "catalysts": [],
        "falsifiers": [], "counterarguments": [], "implications": [],
        "belief_delta": {"statement": "", "support_claim_indices": []},
        "consensus_relation": {"statement": "", "support_claim_indices": []},
        "uncertainties": [],
    }


def selector_payload(user, selections=None, analysis=None, **overrides):
    catalog = prompt_catalog(user)
    ids = [unit["evidence_id"] for unit in catalog["units"]]
    if selections is None:
        selections = [{"evidence_id": ids[0]}]
    payload = {
        "selector": catalog["catalog_version"],
        "document": prompt_identity(user),
        "catalog_sha256": catalog["catalog_sha256"],
        "selections": selections,
        "analysis": analysis if analysis is not None else default_analysis(len(selections)),
    }
    payload.update(overrides)
    return json.dumps(payload)


def run_v3(body=BODY, doc=None, payload_builder=None):
    builder = payload_builder or (lambda system, user: selector_payload(user))
    call, calls = fake_call(builder)
    result = analyze_document(
        doc or DOC, body, model_id="fixture-model", call=call
    )
    return result, calls


def unit_map(catalog):
    return {unit["text"]: unit["evidence_id"] for unit in catalog["units"]}


class CatalogLawTests(unittest.TestCase):
    def test_units_keep_abbreviation_decimal_and_wrap_in_one_unit(self):
        units = propose_quote_units(BODY)
        self.assertEqual(units[0], UNIT_ABBREV)
        self.assertEqual(units[1], UNIT_POLARITY)
        self.assertEqual(units[2], UNIT_WRAP)
        for unit in units:
            self.assertTrue(quote_span_verified(BODY, unit, require_complete_clause=True))

    def test_catalog_is_deterministic_and_content_ids_separate_bodies(self):
        identity = identity_for(BODY)
        first = selection.build_selection_catalog(identity, BODY)
        second = selection.build_selection_catalog(identity, BODY)
        self.assertEqual(first, second)
        body_two = "Preamble sentence for a second note. " + UNIT_POLARITY
        catalog_two = selection.build_selection_catalog(identity_for(body_two), body_two)
        shared_id = unit_map(first)[UNIT_POLARITY]
        other_id = unit_map(catalog_two)[UNIT_POLARITY]
        self.assertNotEqual(shared_id, other_id)
        self.assertTrue(shared_id.startswith("q3-"))
        self.assertTrue(other_id.startswith("q3-"))

    def test_repeated_sentence_is_one_catalog_entry(self):
        body = UNIT_POLARITY + " " + UNIT_POLARITY
        catalog = selection.build_selection_catalog(identity_for(body), body)
        matches = [unit for unit in catalog["units"] if unit["text"] == UNIT_POLARITY]
        self.assertEqual(len(matches), 1)
        self.assertEqual(catalog["metadata"]["duplicate_units"], 1)
        self.assertEqual(catalog["metadata"]["admitted_units"], 1)

    def test_overlong_units_are_omitted_not_shortened(self):
        long_sentence = "Margins " + "word " * 400 + "ended."
        body = "Cloud demand accelerated. " + long_sentence
        catalog = selection.build_selection_catalog(identity_for(body), body)
        self.assertEqual(catalog["metadata"]["omitted_overlong"], 1)
        self.assertEqual(
            [unit["text"] for unit in catalog["units"]], ["Cloud demand accelerated."]
        )

    def test_unverifiable_proposal_is_omitted_never_repaired(self):
        # NFKC typography can divide a raw slice internally; the proposal is
        # omitted whole, never repaired, joined, or offset-mapped.
        body = "First part｡ Second part continues here. Ending part now."
        catalog = selection.build_selection_catalog(identity_for(body), body)
        self.assertEqual(catalog["metadata"]["omitted_unverifiable"], 1)
        self.assertEqual(
            [unit["text"] for unit in catalog["units"]], ["Ending part now."]
        )
        self.assertFalse(any("｡" in unit["text"] for unit in catalog["units"]))

    def test_han_units_are_addressable_and_admitted(self):
        body = "管理层预计收入增长。利润率在第四季度改善。"
        catalog = selection.build_selection_catalog(identity_for(body), body)
        self.assertEqual(catalog["metadata"]["admitted_units"], 2)
        self.assertEqual(catalog["units"][0]["text"], "管理层预计收入增长。")
        for unit in catalog["units"]:
            self.assertTrue(quote_span_verified(body, unit["text"], require_complete_clause=True))


class SelectorSuccessTests(unittest.TestCase):
    def test_v3_success_assembles_original_slices_with_receipt(self):
        result, calls = run_v3()
        self.assertEqual(result["state"], "ok")
        self.assertEqual(len(calls), 1)
        identity = identity_for(BODY)
        catalog = selection.build_selection_catalog(identity, BODY)
        unit_text = catalog["units"][0]["text"]
        self.assertEqual(result["prompt_version"], PROMPT_VERSION)
        self.assertEqual(result["requested_model"], "fixture-model")
        self.assertEqual(result["model"], "served-fixture-model")
        self.assertEqual(result["document"], identity)
        self.assertEqual(result["source_context"]["catalog_sha256"], catalog["catalog_sha256"])
        self.assertEqual(len(result["rio"]["claims"]), 1)
        self.assertEqual(result["source_context"]["proposed_units"], 3)
        self.assertEqual(result["source_context"]["admitted_units"], 3)
        claim = result["rio"]["claims"][0]
        self.assertEqual(claim["statement"], unit_text)
        self.assertEqual(claim["evidence"], [{"quote_span": unit_text}])
        self.assertIn(unit_text, BODY)
        self.assertEqual(result["rio"]["authority"], "descriptive_research_only")
        system, user, _ = build_selector_prompt(identity, BODY)
        self.assertEqual(result["prompt_sha256"], selection._sha(system + "\n" + user))
        self.assertEqual(
            result["prompt_contract_sha256"],
            selection._sha(PROMPT_VERSION + "\n" + SELECTOR_SYSTEM_PROMPT),
        )
        self.assertIn("EVIDENCE CATALOG:", calls[0]["user"])
        self.assertIn(BODY, calls[0]["user"])

    def test_annotations_defaults_and_literal_number_verification(self):
        def builder(system, user):
            catalog = prompt_catalog(user)
            target = next(u for u in catalog["units"] if "3.5%" in u["text"])
            payload_selections = [
                {"evidence_id": target["evidence_id"], "numbers": ["3.5%", "9.9%"]}
            ]
            return selector_payload(user, selections=payload_selections)

        result, _ = run_v3(payload_builder=builder)
        self.assertEqual(result["state"], "ok")
        claim = result["rio"]["claims"][0]
        self.assertEqual(claim["numbers"], ["3.5%"])
        self.assertEqual(claim["entities"], [])
        self.assertEqual(claim["horizon"], "")
        self.assertFalse(claim["explicit"])

    def test_typed_annotations_are_carried_into_the_claim(self):
        def builder(system, user):
            catalog = prompt_catalog(user)
            target = next(u for u in catalog["units"] if "3.5%" in u["text"])
            payload_selections = [{
                "evidence_id": target["evidence_id"],
                "numbers": ["3.5%"],
                "entities": ["Cloud Co"],
                "horizon": "quarterly",
                "explicit": True,
            }]
            return selector_payload(user, selections=payload_selections)

        result, _ = run_v3(payload_builder=builder)
        claim = result["rio"]["claims"][0]
        self.assertEqual(claim["numbers"], ["3.5%"])
        self.assertEqual(claim["entities"], ["Cloud Co"])
        self.assertEqual(claim["horizon"], "quarterly")
        self.assertTrue(claim["explicit"])

    def test_exact_selected_order_and_support_indices(self):
        def builder(system, user):
            catalog = prompt_catalog(user)
            ids = [unit["evidence_id"] for unit in catalog["units"]]
            payload_selections = [{"evidence_id": ids[2]}, {"evidence_id": ids[1]}]
            analysis = {
                "thesis": {
                    "summary": "The note argues margins held despite pressure.",
                    "direction": "neutral",
                    "mechanism": [],
                    "conviction": "",
                    "support_claim_indices": [0],
                },
                "assumptions": [
                    {"statement": "The wrapped sentence behaves as one unit.", "support_claim_indices": [1]}
                ],
                "forecasts": [], "catalysts": [], "falsifiers": [],
                "counterarguments": [], "implications": [],
                "belief_delta": {"statement": "", "support_claim_indices": []},
                "consensus_relation": {"statement": "", "support_claim_indices": []},
                "uncertainties": [],
            }
            return selector_payload(user, selections=payload_selections, analysis=analysis)

        result, _ = run_v3(payload_builder=builder)
        self.assertEqual(result["state"], "ok")
        catalog = selection.build_selection_catalog(identity_for(BODY), BODY)
        claims = result["rio"]["claims"]
        # Evidence preserves the exact original slice; the statement carries the
        # frozen schema's whitespace normalization of that same slice.
        self.assertEqual(
            claims[0]["evidence"][0]["quote_span"], catalog["units"][2]["text"]
        )
        self.assertEqual(
            claims[1]["evidence"][0]["quote_span"], catalog["units"][1]["text"]
        )
        self.assertEqual(
            claims[0]["statement"], "The firm wrote that margins held despite the wrap."
        )
        self.assertEqual(
            result["rio"]["analysis"]["assumptions"][0]["support_claim_indices"], [1]
        )

    def test_polarity_survives_in_the_assembled_claim(self):
        def builder(system, user):
            catalog = prompt_catalog(user)
            target = next(u for u in catalog["units"] if "did not decline" in u["text"])
            return selector_payload(user, selections=[{"evidence_id": target["evidence_id"]}])

        result, _ = run_v3(payload_builder=builder)
        claim = result["rio"]["claims"][0]
        self.assertEqual(claim["statement"], UNIT_POLARITY)
        self.assertIn("not", claim["statement"])

    def test_han_and_fullwidth_original_characters_are_preserved(self):
        han_body = "管理层预计收入增长。利润率在第四季度改善。"
        wide_body = "Revenue rose 10％ in the third quarter."
        for body in (han_body, wide_body):
            with self.subTest(body=body):
                result, calls = run_v3(body=body)
                self.assertEqual(result["state"], "ok")
                self.assertEqual(len(calls), 1)
                quote = result["rio"]["claims"][0]["evidence"][0]["quote_span"]
                self.assertIn(quote, body)
                self.assertTrue(
                    quote_span_verified(body, quote, require_complete_clause=True)
                )
        result, _ = run_v3(body=wide_body)
        self.assertIn("％", result["rio"]["claims"][0]["evidence"][0]["quote_span"])

    def test_receipt_recomputation_is_deterministic_and_catalog_bound(self):
        identity = identity_for(BODY)
        system_one, user_one, catalog_one = build_selector_prompt(identity, BODY)
        system_two, user_two, catalog_two = build_selector_prompt(identity, BODY)
        self.assertEqual((system_one, user_one), (system_two, user_two))
        self.assertEqual(catalog_one, catalog_two)
        self.assertEqual(
            catalog_one["catalog_sha256"],
            selection.build_selection_catalog(identity, BODY)["catalog_sha256"],
        )
        result, _ = run_v3()
        self.assertEqual(result["prompt_sha256"], selection._sha(system_one + "\n" + user_one))
        self.assertEqual(
            result["prompt_contract_sha256"],
            selection._sha(PROMPT_VERSION + "\n" + SELECTOR_SYSTEM_PROMPT),
        )
        self.assertEqual(
            result["source_context"]["catalog_units"], catalog_one["metadata"]["catalog_units"]
        )


class SelectorRefusalTests(unittest.TestCase):
    def test_prose_wrapped_and_fenced_outputs_are_refused_without_retry(self):
        cases = {
            "fenced": lambda system, user: "```json\n" + selector_payload(user) + "\n```",
            "prose prefix": lambda system, user: "Here is the object: " + selector_payload(user),
            "prose suffix": lambda system, user: selector_payload(user) + "\nHope this helps.",
        }
        for label, builder in cases.items():
            with self.subTest(case=label):
                result, calls = run_v3(payload_builder=builder)
                self.assertEqual(result["state"], "invalid_model_output")
                self.assertIsNone(result["rio"])
                self.assertEqual(len(calls), 1)

    def test_legacy_rio_payload_is_refused_under_selector_mode(self):
        def builder(system, user):
            legacy = {
                "schema": "mastermind.research_intelligence.v1",
                "document": prompt_identity(user),
                "claims": [{
                    "statement": CLAIM_LEGACY,
                    "evidence": [{"quote_span": CLAIM_LEGACY}],
                    "numbers": [], "entities": [], "horizon": "", "explicit": True,
                }],
                "analysis": default_analysis(1),
                "authority": "descriptive_research_only",
            }
            return json.dumps(legacy)

        result, calls = run_v3(payload_builder=builder)
        self.assertEqual(result["state"], "invalid_model_output")
        self.assertIsNone(result["rio"])
        self.assertEqual(len(calls), 1)

    def _case_builder(self, mutator):
        def builder(system, user):
            return mutator(user)

        return builder

    def test_structural_identity_and_annotation_rejections(self):
        catalog = selection.build_selection_catalog(identity_for(BODY), BODY)
        first_id = catalog["units"][0]["evidence_id"]

        def loaded(user):
            return json.loads(selector_payload(user))

        def selections_case(payload_selections):
            def mutator(user):
                return selector_payload(user, selections=payload_selections)
            return mutator

        long_annotation = ["n%"] * 13
        cases = {
            "wrong selector version": lambda user: json.dumps(
                {**loaded(user), "selector": "mastermind.research_intelligence.selector.v2"}
            ),
            "wrong document id": lambda user: json.dumps(
                {**loaded(user), "document": {**prompt_identity(user), "id": "other-doc"}}
            ),
            "stale catalog sha": lambda user: json.dumps(
                {
                    **loaded(user),
                    "catalog_sha256": selection.build_selection_catalog(
                        identity_for(OTHER_BODY), OTHER_BODY
                    )["catalog_sha256"],
                }
            ),
            "forged catalog sha": lambda user: json.dumps(
                {**loaded(user), "catalog_sha256": "f" * 64}
            ),
            "uppercase catalog sha": lambda user: json.dumps(
                {**loaded(user), "catalog_sha256": catalog["catalog_sha256"].upper()}
            ),
            "unknown evidence id": selections_case([{"evidence_id": "q3-" + "0" * 64}]),
            "duplicate evidence id": selections_case(
                [{"evidence_id": first_id}, {"evidence_id": first_id}]
            ),
            "copy-only quote field": selections_case(
                [{"evidence_id": first_id, "quote_span": UNIT_POLARITY}]
            ),
            "copy-only statement field": selections_case(
                [{"evidence_id": first_id, "statement": UNIT_POLARITY}]
            ),
            "selection not object": selections_case([first_id]),
            "missing evidence id": selections_case([{"numbers": []}]),
            "empty selections": selections_case([]),
            "too many selections": selections_case(
                [{"evidence_id": first_id} for _ in range(31)]
            ),
            "numbers not strings": selections_case(
                [{"evidence_id": first_id, "numbers": [35]}]
            ),
            "numbers over count limit": selections_case(
                [{"evidence_id": first_id, "numbers": long_annotation}]
            ),
            "numbers item too long": selections_case(
                [{"evidence_id": first_id, "numbers": ["x" * 301]}]
            ),
            "entities over count limit": selections_case(
                [{"evidence_id": first_id, "entities": ["e" * 60 + str(i)]} for i in range(21)]
            ),
            "entities item too long": selections_case(
                [{"evidence_id": first_id, "entities": ["y" * 121]}]
            ),
            "horizon too long": selections_case(
                [{"evidence_id": first_id, "horizon": "z" * 161}]
            ),
            "explicit not boolean": selections_case(
                [{"evidence_id": first_id, "explicit": "yes"}]
            ),
            "unexpected top-level key": lambda user: json.dumps(
                {**loaded(user), "claims": []}
            ),
            "missing analysis": lambda user: json.dumps(
                {key: value for key, value in loaded(user).items() if key != "analysis"}
            ),
            "analysis not object": lambda user: json.dumps(
                {**loaded(user), "analysis": "nope"}
            ),
            "unsupported direction": lambda user: selector_payload(
                user,
                analysis={
                    **default_analysis(1),
                    "thesis": {**default_analysis(1)["thesis"], "direction": "hyperbullish"},
                },
            ),
            "support index out of range": lambda user: selector_payload(
                user,
                analysis={
                    **default_analysis(1),
                    "thesis": {**default_analysis(1)["thesis"], "support_claim_indices": [5]},
                },
            ),
            "selections not list": lambda user: json.dumps(
                {**loaded(user), "selections": {"evidence_id": first_id}}
            ),
        }
        for label, mutator in cases.items():
            with self.subTest(case=label):
                result, calls = run_v3(payload_builder=self._case_builder(mutator))
                self.assertEqual(result["state"], "invalid_model_output")
                self.assertIsNone(result["rio"])
                self.assertEqual(len(calls), 1)


class PreflightAndModeTests(unittest.TestCase):
    def test_empty_catalog_is_a_distinct_pre_call_refusal_without_model_call(self):
        result, calls = run_v3(body="x" * 2000)
        self.assertIsNone(result["rio"])
        self.assertEqual(result["state"], "selection_unavailable")
        self.assertEqual(result["error_code"], "EMPTY_SELECTION_CATALOG")
        self.assertEqual(result["prompt_version"], PROMPT_VERSION)
        self.assertEqual(result["prompt_sha256"], "")
        self.assertEqual(calls, [])

    def test_unit_overflow_and_body_bounds_are_distinct_pre_call_refusals(self):
        body = " ".join(f"{index:04d} abcd." for index in range(2100))
        result, calls = run_v3(body=body)
        self.assertEqual(result["state"], "selection_unavailable")
        self.assertEqual(result["error_code"], "SELECTION_CATALOG_UNIT_OVERFLOW")
        self.assertEqual(calls, [])
        oversized = "lorem ipsum " * 700000
        result_big, calls_big = run_v3(body=oversized)
        self.assertEqual(result_big["state"], "selection_unavailable")
        self.assertEqual(result_big["error_code"], "BODY_SIZE_OVERFLOW")
        self.assertEqual(calls_big, [])

    def test_public_path_refuses_copy_only_rio_and_has_no_legacy_mode(self):
        def legacy_builder(system, user):
            return json.dumps({
                "schema": "mastermind.research_intelligence.v1",
                "document": prompt_identity(user),
                "claims": [{
                    "statement": CLAIM_LEGACY,
                    "evidence": [{"quote_span": CLAIM_LEGACY}],
                    "numbers": ["35%"], "entities": ["AMD"],
                    "horizon": "current", "explicit": True,
                }],
                "analysis": default_analysis(1),
                "authority": "descriptive_research_only",
            })

        call, _calls = fake_call(legacy_builder)
        result = analyze_document(DOC, BODY, model_id="fixture-model", call=call)
        self.assertEqual(result["state"], "invalid_model_output")
        self.assertEqual(result["prompt_version"], PROMPT_VERSION)
        self.assertIsNone(result["rio"])
        with self.assertRaises(TypeError):
            analyze_document(DOC, BODY, model_id="fixture-model", call=call, mode="selector_v2")

    def test_final_rio_over_128kib_is_refused(self):
        body = " ".join(
            f"Segment {index} reported revenue grew {index} percent steadily."
            for index in range(30)
        )
        pad = "cost structure " * 130
        row = {"statement": pad, "support_claim_indices": [0]}

        def builder(system, user):
            catalog = prompt_catalog(user)
            payload_selections = [
                {"evidence_id": unit["evidence_id"]} for unit in catalog["units"]
            ]
            self.assertEqual(len(payload_selections), 30)
            analysis = {
                "thesis": {
                    "summary": "Synthesis of the fixture note. " * 70,
                    "direction": "neutral",
                    "mechanism": ["mechanism padding " * 60],
                    "conviction": "",
                    "support_claim_indices": [0],
                },
                "assumptions": [dict(row) for _ in range(30)],
                "forecasts": [dict(row) for _ in range(30)],
                "catalysts": [dict(row) for _ in range(30)],
                "falsifiers": [dict(row) for _ in range(30)],
                "counterarguments": [dict(row) for _ in range(30)],
                "implications": [dict(row) for _ in range(30)],
                "belief_delta": {"statement": "", "support_claim_indices": []},
                "consensus_relation": {"statement": "", "support_claim_indices": []},
                "uncertainties": [dict(row) for _ in range(30)],
            }
            return selector_payload(user, selections=payload_selections, analysis=analysis)

        result, calls = run_v3(body=body, payload_builder=builder)
        self.assertEqual(result["state"], "invalid_model_output")
        self.assertIsNone(result["rio"])
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
