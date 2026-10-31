"""Real diagnostic caller; no provider or publishing. Old compiler uses a double.

When #7493 is composed, the same tests invoke its actual compiler instead.
The shaped guard and outer boundary are always the real implementations.
"""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from engine.marketing import copywriter as cw
from engine.marketing import frontier_editorial as frontier
from scripts import marketing_copy_dryrun as diagnostic

NOW = datetime(2026, 10, 3, 5, tzinfo=timezone.utc)


class ShadowCallerTests(unittest.TestCase):
    def setUp(self):
        self.owner = {
            "context": cw.build_context(
                {"account": "fixture-unregistered", "type": "event"},
                facts={"facts": [{"id": "fixture:revenue", "text": "Revenue reached 10%.",
                                   "numbers": ["10%"]}]}, extra={"shape": "one_liner"}),
            "binding": {"operation_id": "fixture-op", "attempt_id": "fixture-attempt",
                "source_id": "fixture-source", "source_revision": "v1",
                "account_id": "fixture-unregistered", "policy_revision": "p1",
                "persona_revision": "persona-v1", "evidence_refs": ["fixture:revenue"],
                "media_spec_ids": [], "issued_at": (NOW-timedelta(minutes=1)).isoformat(),
                "expires_at": (NOW+timedelta(minutes=1)).isoformat()},
            "persona_card": {"name": "Synthetic", "voice_notes": "Plain words.",
                             "example_lines": ["Evidence before opinion."]},
            "codex_by_account": {}, "memory_by_account": {},
        }
        self.real_payload = cw._v2_item_payload
        self.real_attach = getattr(cw, "_attach_editorial_contract", None)
        self.compiler_present = getattr(cw, "EDITORIAL_BRIEF_REVISION", None) == "marketing.editorial_brief.v1"

        def compatible_payload(context, **kwargs):
            result = self.real_payload(context, **kwargs)
            if not self.compiler_present:
                # Test double for the not-yet-merged inner compiler, NOT source implementation.
                result["editorial_brief"] = {"revision": "marketing.editorial_brief.v1",
                    "digest": "a"*64, "positive_examples": kwargs["persona_card"].get("example_lines", [])}
            return result

        def compatible_attach(result, payload):
            if self.real_attach is not None:
                return self.real_attach(result, payload)
            return dict(result, editorial_contract={key: payload["editorial_brief"][key]
                                                    for key in ("revision", "digest")})
        self.addCleanup(patch.stopall)
        patch.object(cw, "_v2_item_payload", side_effect=compatible_payload).start()
        patch.object(cw, "_attach_editorial_contract", side_effect=compatible_attach, create=True).start()
        patch.object(cw, "write_posts_llm_v2", side_effect=AssertionError("provider path reached")).start()
        patch.object(diagnostic, "_load_cfg", side_effect=AssertionError("live config reached")).start()
        patch.object(diagnostic, "_build_contexts", side_effect=AssertionError("live data reached")).start()
        self.brief = diagnostic.prepare_frontier_shadow(self.owner)
        self.response = {"request_sha256": self.brief["payload_sha256"], "decision": "draft",
            "headline": "", "body": "Revenue reached 10%. The next filing will test durability.",
            "claims": [{"statement": "Revenue reached 10%.", "kind": "observation",
                        "evidence_refs": ["fixture:revenue"]}], "visual_brief": "", "media_spec_id": None}

    def evaluate(self, response=None, owner=None, now=NOW):
        return diagnostic.consume_frontier_shadow(self.brief, self.response if response is None else response,
                owner_input=self.owner if owner is None else owner, now=now)

    def test_clean_return_is_review_only_and_has_trusted_inner_identity(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertIs(result["publish_authorized"], False)
        self.assertNotIn("mode", result)
        self.assertEqual(result["editorial_contract"]["digest"],
                         self.brief["context"]["editorial_brief"]["digest"])

    def test_whole_writer_payload_is_sealed(self):
        self.assertEqual(self.brief["context"]["writer_payload"]["persona"], self.owner["persona_card"])
        self.assertIn("editorial_brief", self.brief["context"]["writer_payload"])

    def test_shaped_headline_violation_is_rejected_by_real_guard(self):
        bad = dict(self.response, headline="Revenue reached 10%.", body="The next filing will test durability.")
        self.assertEqual(cw.validate_copy(bad["headline"], bad["body"], self.owner["context"]), [])
        self.assertTrue(cw.validate_copy_v2(bad["headline"]+"\n\n"+bad["body"], self.owner["context"], headline=bad["headline"]))
        self.assertEqual(self.evaluate(bad)["reasons"], ["canonical_copy_rejected"])

    def test_unsupported_number_is_rejected(self):
        bad = copy.deepcopy(self.response)
        bad["body"] = "Revenue reached 99%."
        bad["claims"][0]["statement"] = bad["body"]
        self.assertEqual(self.evaluate(bad)["reasons"], ["canonical_copy_rejected"])

    def test_persona_register_change_invalidates_even_if_inner_digest_does_not(self):
        current = copy.deepcopy(self.owner)
        current["persona_card"]["voice_notes"] = "New approved register."
        new = diagnostic.prepare_frontier_shadow(current)
        self.assertEqual(new["context"]["editorial_brief"]["digest"], self.brief["context"]["editorial_brief"]["digest"])
        self.assertEqual(self.evaluate(owner=current)["reasons"], ["current_inputs_changed"])

    def test_positive_example_change_invalidates(self):
        current = copy.deepcopy(self.owner)
        current["persona_card"]["example_lines"] = ["A different approved example."]
        self.assertEqual(self.evaluate(owner=current)["reasons"], ["current_inputs_changed"])

    def test_context_change_invalidates(self):
        current = copy.deepcopy(self.owner)
        current["context"]["as_of"] = "2026-10-02"
        self.assertEqual(self.evaluate(owner=current)["reasons"], ["current_inputs_changed"])

    def test_changed_source_or_policy_or_attempt_invalidates(self):
        for key in ("source_revision", "policy_revision", "persona_revision", "attempt_id"):
            with self.subTest(key=key):
                current = copy.deepcopy(self.owner)
                current["binding"][key] = "changed"
                self.assertEqual(self.evaluate(owner=current)["reasons"], ["current_inputs_changed"])

    def test_expiry_is_not_extended_by_recompilation(self):
        self.assertEqual(self.evaluate(now=NOW+timedelta(minutes=1))["reasons"], ["expired_or_future_brief"])

    def test_old_compiler_fields_in_context_are_rebuilt_not_trusted(self):
        current = copy.deepcopy(self.owner)
        current["context"]["editorial_brief"] = {"digest": "forged"}
        current["context"]["writer_payload"] = {"publish_authorized": True}
        self.assertEqual(diagnostic.prepare_frontier_shadow(current), self.brief)

    def test_inputs_are_not_mutated(self):
        before = copy.deepcopy((self.owner, self.brief, self.response))
        self.evaluate()
        self.assertEqual((self.owner, self.brief, self.response), before)

    def test_abstention_never_gets_contract_or_template_copy(self):
        result = self.evaluate({"request_sha256": self.brief["payload_sha256"], "decision": "abstain", "reason": "No useful insight."})
        self.assertEqual(result["status"], "ABSTAINED")
        self.assertIsNone(result["draft"])
        self.assertNotIn("editorial_contract", result)

    def test_model_cannot_stamp_inner_authority(self):
        result = self.evaluate(dict(self.response, editorial_contract={"digest": "a"*64}))
        self.assertEqual(result["status"], "REJECTED")
        self.assertNotIn("editorial_contract", result)

    def test_unknown_evidence_is_rejected(self):
        bad = copy.deepcopy(self.response)
        bad["claims"][0]["evidence_refs"] = ["fixture:unknown"]
        self.assertEqual(self.evaluate(bad)["reasons"], ["invalid_claim_map"])

    def test_missing_inner_compiler_fails_closed(self):
        with patch.object(cw, "_v2_item_payload", return_value={"account": "fixture"}):
            with self.assertRaisesRegex(diagnostic.FrontierShadowError, "canonical_editorial_contract_unavailable"):
                diagnostic.prepare_frontier_shadow(self.owner)

    def test_malformed_or_future_inner_contract_fails_closed(self):
        for inner in (None, {}, {"revision": "future.v2", "digest": "a"*64},
                      {"revision": "marketing.editorial_brief.v1", "digest": "Z"*64}):
            with self.subTest(inner=inner), patch.object(cw, "_v2_item_payload", return_value={"editorial_brief": inner}):
                with self.assertRaises(diagnostic.FrontierShadowError):
                    diagnostic.prepare_frontier_shadow(self.owner)

    def test_unexpected_owner_fields_reject(self):
        with self.assertRaisesRegex(diagnostic.FrontierShadowError, "invalid_current_owner_input"):
            diagnostic.prepare_frontier_shadow(dict(self.owner, approved=True))

    def test_unknown_binding_field_rejects(self):
        current = copy.deepcopy(self.owner)
        current["binding"]["provider"] = "invented"
        with self.assertRaises(diagnostic.FrontierShadowError):
            diagnostic.prepare_frontier_shadow(current)

    def run_cli(self, owner=None, response=None, *, raw_owner=None):
        owner = copy.deepcopy(self.owner if owner is None else owner)
        clock = datetime.now(timezone.utc)
        owner["binding"]["issued_at"] = (clock-timedelta(minutes=5)).isoformat()
        owner["binding"]["expires_at"] = (clock+timedelta(minutes=5)).isoformat()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root/"current.json"
            path.write_text(json.dumps(owner) if raw_owner is None else raw_owner)
            argv = ["--frontier-owner-input", str(path)]
            if response is not None:
                issued = diagnostic.prepare_frontier_shadow(owner)
                returned = copy.deepcopy(response)
                returned["request_sha256"] = issued["payload_sha256"]
                (root/"issued.json").write_text(json.dumps(issued))
                (root/"response.json").write_text(json.dumps(returned))
                argv += ["--frontier-issued", str(root/"issued.json"),
                         "--frontier-response", str(root/"response.json")]
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            output = io.StringIO()
            with redirect_stdout(output):
                code = diagnostic.main(argv)
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)
            return code, json.loads(output.getvalue())

    def test_cli_prepare_uses_explicit_input_not_live_plan(self):
        code, result = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["schema"], frontier.SCHEMA)
        self.assertEqual(result["intent"], "draft_only")

    def test_cli_consumes_issued_return_current_triple(self):
        code, result = self.run_cli(response=self.response)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["publish_authorized"])

    def test_cli_shape_rejection_has_nonzero_exit_and_no_fallback(self):
        code, result = self.run_cli(response=dict(self.response, headline="Revenue reached 10%."))
        self.assertEqual(code, 2)
        self.assertEqual(result["reasons"], ["canonical_copy_rejected"])
        self.assertIsNone(result["draft"])

    def test_cli_duplicate_keys_are_rejected(self):
        code, result = self.run_cli(raw_owner='{"context":{},"context":{}}')
        self.assertEqual(code, 2)
        self.assertEqual(result["reasons"], ["invalid_shadow_input_file"])

    def test_cli_file_is_bounded_before_parsing(self):
        code, result = self.run_cli(raw_owner='{"x":"' + 'a'*frontier.MAX_BYTES + '"}')
        self.assertEqual(code, 2)
        self.assertEqual(result["reasons"], ["invalid_shadow_input_file"])

    def test_cli_compiler_error_never_exposes_exception(self):
        with patch.object(cw, "_v2_item_payload", side_effect=RuntimeError("synthetic-secret")):
            code, result = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(result["reasons"], ["canonical_editorial_contract_unavailable"])
        self.assertNotIn("synthetic-secret", json.dumps(result))

    def test_partial_shadow_flags_never_enter_live_mode(self):
        for argv in (["--frontier-issued", "missing"], ["--frontier-response", "missing"],
                     ["--frontier-owner-input", "missing", "--frontier-issued", "missing"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    diagnostic.main(argv)
                self.assertEqual(error.exception.code, 2)

    def test_current_installed_compiler_is_not_silently_replaced(self):
        with patch.object(cw, "_v2_item_payload", self.real_payload):
            if self.compiler_present:
                brief = diagnostic.prepare_frontier_shadow(self.owner)
                self.assertEqual(brief["context"]["editorial_brief"]["claims"][0]["claim_ref"], "fixture:revenue")
            else:
                with self.assertRaisesRegex(diagnostic.FrontierShadowError, "canonical_editorial_contract_unavailable"):
                    diagnostic.prepare_frontier_shadow(self.owner)

    def test_shaped_guard_failure_is_opaque(self):
        with patch.object(cw, "validate_copy_v2", side_effect=RuntimeError("synthetic-secret")):
            result = self.evaluate()
        self.assertEqual(result["reasons"], ["canonical_copy_unavailable"])
        self.assertNotIn("synthetic-secret", json.dumps(result))

    def test_account_mismatch_is_rejected(self):
        current = copy.deepcopy(self.owner)
        current["binding"]["account_id"] = "some-other-account"
        with self.assertRaises(diagnostic.FrontierShadowError):
            diagnostic.prepare_frontier_shadow(current)

    def test_two_part_format_survives_real_shaped_guard(self):
        self.owner["context"]["shape"] = "two_part"
        self.brief = diagnostic.prepare_frontier_shadow(self.owner)
        self.response.update(request_sha256=self.brief["payload_sha256"],
            headline="Revenue reached 10%.", body="The next filing will test durability.")
        self.assertEqual(self.evaluate()["status"], "REVIEW_REQUIRED")

    def test_relevant_account_memory_and_codex_changes_invalidate(self):
        self.owner["context"]["type"] = "macro"
        self.brief = diagnostic.prepare_frontier_shadow(self.owner)
        self.response["request_sha256"] = self.brief["payload_sha256"]
        for field in ("memory_by_account", "codex_by_account"):
            with self.subTest(field=field):
                current = copy.deepcopy(self.owner)
                current[field]["fixture-unregistered"] = {"recent_positions": ["A supplied prior view."]}
                rebuilt = diagnostic.prepare_frontier_shadow(current)
                self.assertTrue(rebuilt["context"]["writer_payload"]["codex"])
                self.assertEqual(self.evaluate(owner=current)["reasons"], ["current_inputs_changed"])

    def test_existing_no_write_guard_detects_write_and_unknown_modes(self):
        import ast
        from types import SimpleNamespace
        # Execute the exact incumbent guard, without importing unrelated provider
        # test dependencies from the rest of its module into this thin fixture.
        guard_source = Path(__file__).with_name("test_marketing_copy_v2.py").read_text()
        name = "test_dry_run_imports_and_writes_nothing"
        node = next(n for n in ast.parse(guard_source).body if isinstance(n, ast.FunctionDef) and n.name == name)
        code = compile(ast.Module(body=[node], type_ignores=[]), "incumbent_no_write_guard", "exec")
        source = Path(diagnostic.__file__).read_text(encoding="utf-8")
        self.assertIn('.open("rb")', source)
        for mode in ('"wb"', '"ab"', '"r+b"', 'unknown_mode'):
            with self.subTest(mode=mode):
                bad = source.replace('.open("rb")', '.open('+mode+')')
                scope = {"DRYRUN_PATH": SimpleNamespace(read_text=lambda **kwargs: bad),
                         "_dryrun_module": lambda: SimpleNamespace(main=lambda argv: 0)}
                exec(code, scope)
                with self.assertRaisesRegex(AssertionError, "binary-read opens"):
                    scope[name]()


class EmptyShadowFlagsTests(unittest.TestCase):
    """Presence, not truthiness, selects a no-provider shadow invocation."""

    def assert_rejected(self, flags):
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / "synthetic-plan.json"
            plan.write_text("{}")
            with patch.object(diagnostic, "_load_cfg", side_effect=AssertionError("LEGACY_MODEL_MODE_REACHED")), patch.object(diagnostic, "_frontier_shadow_main", side_effect=AssertionError("MALFORMED_FLAGS_REACHED_SHADOW_IO")), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    diagnostic.main(flags + ["--plan", str(plan)])
                self.assertEqual(error.exception.code, 2)

    def test_empty_owner_input_rejects(self):
        self.assert_rejected(["--frontier-owner-input", ""])

    def test_empty_issued_rejects(self):
        self.assert_rejected(["--frontier-issued", ""])

    def test_empty_response_rejects(self):
        self.assert_rejected(["--frontier-response", ""])

    def test_all_empty_rejects(self):
        self.assert_rejected(["--frontier-owner-input", "", "--frontier-issued", "", "--frontier-response", ""])

    def test_present_owner_and_empty_pair_rejects(self):
        self.assert_rejected(["--frontier-owner-input", "current.json", "--frontier-issued", "", "--frontier-response", ""])

    def test_blank_owner_rejects_before_shadow_io(self):
        self.assert_rejected(["--frontier-owner-input", "   "])

    def test_nonempty_owner_with_single_return_option_rejects(self):
        for flag in ("--frontier-issued", "--frontier-response"):
            with self.subTest(flag=flag):
                self.assert_rejected(["--frontier-owner-input", "current.json", flag, "input.json"])

    def test_absent_shadow_options_preserve_legacy_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / "synthetic-plan.json"
            plan.write_text("{}")
            with patch.object(diagnostic, "_load_cfg", side_effect=RuntimeError("EXPECTED_LEGACY_ENTRY")), patch.object(diagnostic, "_frontier_shadow_main", side_effect=AssertionError("UNEXPECTED_SHADOW")):
                with self.assertRaisesRegex(RuntimeError, "EXPECTED_LEGACY_ENTRY"):
                    diagnostic.main(["--plan", str(plan)])


if __name__ == "__main__":
    unittest.main()
