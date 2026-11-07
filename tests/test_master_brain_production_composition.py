"""Real synthesis -> production owner -> incumbent ledgers, without networking.

Only the provider SDK is substituted in normal execution tests. Credentials are
synthetic; cache, health and usage files are isolated below a temporary root.
Run: python -m unittest discover -s tests -p test_master_brain_production_composition.py -v
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from engine import master_brain, provider_production_modes as owner


# Pytest's repository fixture disables cache I/O by default. This suite owns
# a TemporaryDirectory and explicitly tests the actual root-aware cache.
_REAL_CACHE_GET = master_brain._mb_reply_cache_get
_REAL_CACHE_PUT = master_brain._mb_reply_cache_put


class MasterBrainProductionCompositionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.modes = json.loads(Path(owner.DEFAULT_PATH).read_text())
        self.modes["modes"]["minimax_payg_api"]["enabled"] = True
        self.mode_path = self.root / "modes.json"
        self.write_modes()
        self.cfg = {"production_mode": "minimax_payg_api", "max_tokens": 4000,
                    "emit_theses": False}
        self.state = {"macro": {"date": "2026-11-04", "summary": "Observed state."}}
        self.dispatches, self.constructors = [], []
        self.reply = json.dumps({"summary": "Measured conditions remain mixed.",
                                 "tldr": ["Growth is steady."], "confidence": "medium"})
        self.responses = []
        self.failure = None

        def start(patcher):
            self.addCleanup(patcher.stop)
            return patcher.start()

        start(patch.dict(os.environ, {
            "MINIMAX_API_KEY": "synthetic-test-credential",
            "PROVIDER_HEALTH_PATH": str(self.root / "health.jsonl"),
            "AI_COSTS_STATE_ROOT": str(self.root / "costs"),
        }, clear=True))
        start(patch.object(owner, "DEFAULT_PATH", self.mode_path))
        start(patch.object(master_brain, "_mb_reply_cache_get", _REAL_CACHE_GET))
        start(patch.object(master_brain, "_mb_reply_cache_put", _REAL_CACHE_PUT))
        start(patch.object(master_brain, "_is_deepseek_lane",
                           side_effect=AssertionError("legacy ladder reached")))
        start(patch.object(master_brain, "_client",
                           side_effect=AssertionError("legacy client reached")))
        testcase = self

        class SDK:
            def __init__(self, **kwargs):
                testcase.constructors.append(kwargs)
                testcase.assertEqual(kwargs.get("max_retries"), 0)
                self.messages = self

            def create(self, **kwargs):
                testcase.dispatches.append(kwargs)
                result = testcase.responses.pop(0) if testcase.responses else testcase.failure
                if isinstance(result, Exception):
                    raise result
                return {"content": [{"type": "text", "text": result or testcase.reply}],
                        "usage": {"input_tokens": 41, "output_tokens": 13}}

        start(patch.dict("sys.modules", {"anthropic": types.SimpleNamespace(Anthropic=SDK)}))

    def write_modes(self):
        self.mode_path.write_text(json.dumps(self.modes))

    def synthesize(self, **overrides):
        return master_brain.synthesize(self.state, cfg={**self.cfg, **overrides}, root=self.root)

    def cost_rows(self):
        return [json.loads(line) for path in (self.root / "costs").rglob("*.jsonl")
                for line in path.read_text().splitlines()]

    def health_rows(self):
        path = self.root / "health.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def caches(self):
        return list((self.root / "data/master_brain/reply_cache").glob("*.txt"))

    def test_real_synthesis_records_actual_model_and_one_owner_usage_row(self):
        brief = self.synthesize()
        self.assertEqual(brief["summary"], "Measured conditions remain mixed.")
        self.assertEqual(brief["model"], owner.MINIMAX_PINNED_MODEL)
        self.assertEqual(brief["served_by"], "minimax")
        self.assertIsNone(brief["degraded_reason"])
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(self.dispatches[0]["model"], owner.MINIMAX_PINNED_MODEL)
        self.assertIn("Observed state.", self.dispatches[0]["messages"][0]["content"])
        self.assertEqual(len(self.health_rows()), 1)
        costs = self.cost_rows()
        self.assertEqual(len(costs), 1)
        self.assertEqual((costs[0]["provider"], costs[0]["key_id"], costs[0]["input_tokens"]),
                         ("minimax", "prod_api:minimax", 41))

    def test_legacy_cache_cannot_supply_production_and_production_cache_keeps_model(self):
        legacy_cfg = {"emit_theses": False, "max_tokens": 4000}
        legacy = json.dumps({"summary": "Legacy cached text."})
        # Also exercises the existing legacy stub-signature compatibility path.
        with patch.object(master_brain, "_call_model", lambda system, user, cfg: (legacy, None)):
            old = master_brain.synthesize(self.state, cfg=legacy_cfg, root=self.root)
            cached_old = master_brain.synthesize(self.state, cfg=legacy_cfg, root=self.root)
        self.assertEqual(old["summary"], "Legacy cached text.")
        self.assertEqual(cached_old["served_by"], "cache")
        first = self.synthesize()
        second = self.synthesize()
        self.assertEqual(first["summary"], "Measured conditions remain mixed.")
        self.assertEqual(second["summary"], first["summary"])
        self.assertEqual(second["served_by"], "cache")
        self.assertEqual(second["model"], owner.MINIMAX_PINNED_MODEL)
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(len(self.cost_rows()), 1)
        self.assertEqual(len(self.caches()), 2)

    def test_output_budget_has_a_distinct_production_cache_identity(self):
        self.synthesize(max_tokens=100)
        self.synthesize(max_tokens=200)
        self.assertEqual([call["max_tokens"] for call in self.dispatches], [100, 200])
        self.assertEqual(len(self.caches()), 2)

    def test_disabled_mode_cannot_reuse_prior_production_cache_or_read_secret(self):
        self.synthesize()
        self.modes["modes"]["minimax_payg_api"]["enabled"] = False
        self.write_modes()
        with patch.object(owner, "_resolve_credential", side_effect=AssertionError("secret read")):
            brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "production_mode_disabled")
        self.assertIsNone(brief["summary"])
        self.assertIsNone(brief["served_by"])
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(len(self.cost_rows()), 1)
        self.assertEqual(self.health_rows()[-1]["error_class"], "disabled")

    def test_unconfigured_mode_cannot_reuse_prior_production_cache(self):
        self.synthesize()
        del os.environ["MINIMAX_API_KEY"]
        brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "production_mode_unconfigured")
        self.assertIsNone(brief["summary"])
        self.assertEqual(len(self.dispatches), 1)

    def test_unqualified_glm_refuses_before_credential_resolution_or_cache_read(self):
        self.modes["modes"]["glm_general_api"]["enabled"] = True
        self.write_modes()
        with patch.object(owner, "_resolve_credential", side_effect=AssertionError("secret read")), \
                patch.object(master_brain, "_mb_reply_cache_get", side_effect=AssertionError("cache read")):
            brief = self.synthesize(production_mode="glm_general_api")
        self.assertEqual(brief["degraded_reason"], "production_mode_unqualified")
        self.assertEqual(brief["model"], owner.GLM_PINNED_MODEL)
        self.assertEqual(self.dispatches, [])

    def test_explicit_bad_selection_or_budget_never_falls_back(self):
        for mode in ("", None, False, [], "unknown-mode"):
            with self.subTest(mode=mode):
                brief = self.synthesize(production_mode=mode)
                self.assertTrue(brief["degraded_reason"].startswith("production_mode_invalid_"))
                self.assertIsNone(brief["summary"])
        for limit in (True, 0, -1, 32769, "100"):
            with self.subTest(max_tokens=limit):
                brief = self.synthesize(max_tokens=limit)
                self.assertEqual(brief["degraded_reason"], "production_mode_invalid_request")
        self.assertEqual(self.dispatches, [])
        self.assertEqual(self.caches(), [])

    def test_destination_mismatch_refuses_before_dispatch(self):
        self.modes["modes"]["minimax_payg_api"]["base_url"] = "https://wrong.invalid/anthropic"
        self.write_modes()
        brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "production_mode_invalid_config")
        self.assertEqual(self.dispatches, [])

    def test_timeout_and_sdk_typeerror_each_make_only_one_attempt(self):
        for failure in (TimeoutError("sensitive detail"), TypeError("sensitive detail")):
            with self.subTest(failure=type(failure).__name__):
                before = len(self.dispatches)
                self.failure = failure
                brief = self.synthesize()
                self.assertIsNone(brief["summary"])
                self.assertNotIn("sensitive", brief["degraded_reason"])
                self.assertEqual(len(self.dispatches), before + 1)
        self.assertEqual(self.caches(), [])
        self.assertEqual(self.cost_rows(), [])

    def test_typeerror_after_completed_call_does_not_use_legacy_signature_retry(self):
        original = master_brain._call_model

        def completed_then_failed(*args, **kwargs):
            original(*args, **kwargs)
            raise TypeError("post-dispatch failure")

        with patch.object(master_brain, "_call_model", side_effect=completed_then_failed):
            brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "production_mode_error")
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(len(self.cost_rows()), 1)
        self.assertEqual(self.caches(), [])

    def test_invalid_json_is_not_replayed_or_cached(self):
        self.reply = "This is not a JSON brief."
        brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "unparseable_reply")
        self.assertEqual(len(self.dispatches), 1)
        self.assertEqual(self.caches(), [])

    def test_style_rewrite_is_separate_accounted_request_and_final_text_is_cached(self):
        self.responses = [json.dumps({"summary": "neural_web conditions."}), self.reply]
        brief = self.synthesize()
        self.assertEqual(brief["summary"], "Measured conditions remain mixed.")
        self.assertEqual(brief["served_by"], "minimax")
        self.assertEqual(brief["style_flags"], [])
        self.assertEqual(len(self.dispatches), 2)
        self.assertIn("Rewrite the SAME JSON", self.dispatches[1]["system"])
        self.assertEqual(len(self.cost_rows()), 2)
        cached = self.synthesize()
        self.assertEqual(cached["summary"], brief["summary"])
        self.assertEqual(cached["served_by"], "cache")
        self.assertEqual(len(self.dispatches), 2)

    def test_failed_rewrite_preserves_valid_draft_without_another_request(self):
        self.responses = [json.dumps({"summary": "neural_web conditions."}), TimeoutError("unknown")]
        brief = self.synthesize()
        self.assertEqual(brief["summary"], "neural_web conditions.")
        self.assertTrue(brief["style_flags"])
        self.assertEqual(brief["model"], owner.MINIMAX_PINNED_MODEL)
        self.assertEqual(len(self.dispatches), 2)
        self.assertEqual(len(self.cost_rows()), 1)

    def test_receipt_identity_change_cannot_poison_selected_mode_cache(self):
        original = owner.call_mode

        def changed_receipt(*args, **kwargs):
            return replace(original(*args, **kwargs), model="different-owner-model")

        with patch.object(owner, "call_mode", side_effect=changed_receipt):
            brief = self.synthesize()
        self.assertEqual(brief["model"], "different-owner-model")
        self.assertEqual(self.caches(), [])
        self.assertEqual(len(self.dispatches), 1)


if __name__ == "__main__":
    unittest.main()
