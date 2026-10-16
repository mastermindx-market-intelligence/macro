"""Parent boundary checks for the source-only Intl projection bridge."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from lib import intl_investigation_owner as bridge

BASE = Path(__file__).resolve().parent


def inputs():
    return {
        "context": {
            "researchMarket": "EZ", "toolBindingVersion": "macro-v1",
            "periodIdentity": "observation:2026-10-06", "currencyBasis": "local",
            "returnBasis": "price", "owner": "scripts/build_intl.py",
            "query": "policy", "cohort": "EZ", "temporalPolicy": "observed-level",
            "selectedMeasureIds": ["EZ.policy_rate"],
        },
        "generation": "synthetic:publication-one",
        "measures": {"EZ.policy_rate": json.loads((BASE / "fixtures" / "intl_investigation_owner_current.json").read_text())["measure"]},
        "origins": {"EZ.policy_rate": {
            "content_identity": None, "qualification_identity": "synthetic:retained-decision",
            "excluded": False, "correction": False,
        }},
    }


class ParentBoundaryTests(unittest.TestCase):
    def assert_refused(self, data):
        result = bridge.build_intl_owner_result(**data)
        self.assertIsNone(result["result"], "Malformed owner input must not emit a successful projection")
        self.assertTrue(any(d["code"] in {"invalid_owner_input", "missing_owner_input"}
                            for d in result["diagnostics"]))

    def test_valid_control(self):
        result = bridge.build_intl_owner_result(**inputs())
        self.assertEqual(result["result"]["membership"], "unknown")
        self.assertEqual(result["result"]["observations"][0]["interpretation"]["value"], 2.5)

    def test_nested_enum_containers_are_structured_refusals(self):
        for field in ("quality", "metadata", "value_permission"):
            for malformed in ([], {}):
                with self.subTest(field=field, malformed=type(malformed).__name__):
                    data = inputs()
                    data["measures"]["EZ.policy_rate"][field] = copy.deepcopy(malformed)
                    self.assert_refused(data)

    def test_nonnumeric_plain_value_containers_are_refused(self):
        for malformed in ([], {}):
            with self.subTest(malformed=type(malformed).__name__):
                data = inputs()
                data["measures"]["EZ.policy_rate"]["value"] = malformed
                self.assert_refused(data)

    def test_origin_record_is_closed(self):
        data = inputs()
        data["origins"]["EZ.policy_rate"]["unexpected_origin_field"] = "synthetic:unmatched"
        self.assert_refused(data)

    def test_clock_values_are_nullable_strings_not_malformed_missing(self):
        for malformed in ([], {}, True, 123):
            with self.subTest(malformed=type(malformed).__name__):
                data = inputs()
                data["clocks"] = {"published_at": malformed, "source_observed_at": None, "rights_at": None}
                self.assert_refused(data)

    def test_generation_subclass_is_refused_without_invoking_methods(self):
        class NonPlainGeneration(str):
            def __len__(self):
                raise AssertionError("Non-plain generation method was invoked")
        data = inputs()
        data["generation"] = NonPlainGeneration("synthetic:publication-one")
        self.assert_refused(data)


if __name__ == "__main__":
    unittest.main()
