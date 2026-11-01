"""Instruction transport regression: keep existing continuation guidance inside the budget.

This is not a claim of model behavior or repaired Stop hooks. Exact original
byte preservation is retained as migration evidence, not a permanent prose lock.
Ongoing checks preserve instruction ordering, budget, required sections and controls.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "research/execution_friction_20261011/instruction_order_baseline.json").read_text())


class InstructionBudgetOrderTests(unittest.TestCase):
    def parts(self):
        return re.split(rb"(?m)(?=^## )", (ROOT / "AGENTS.md").read_bytes())

    def test_continuation_is_first_operating_section(self):
        self.assertTrue(self.parts()[1].startswith(b"## Execution continuation law\n"))

    def test_economy_is_second_operating_section(self):
        self.assertTrue(self.parts()[2].startswith(b"## Context economy"))

    def test_full_continuation_and_economy_fit_default_instruction_budget(self):
        parts = self.parts()
        loaded_prefix = b"".join(parts[:3])
        self.assertLess(len(loaded_prefix), BASELINE["default_project_doc_bytes"])
        self.assertIn(b"## Execution continuation law\n", loaded_prefix)
        self.assertIn(b"## Context economy", loaded_prefix)
        for clause in [b"EFFECT_UNKNOWN", b"NO WORKER STARTED", b"2 equivalent no-delta cycles",
                       b"accepted work", b"MORE_WORK_EXISTS"]:
            self.assertIn(clause, loaded_prefix)

    def test_required_sections_preserved_without_freezing_all_prose(self):
        parts = self.parts()
        headings = [p.splitlines()[0].decode() for p in parts[1:]]
        self.assertEqual(len(headings), len(set(headings)))
        self.assertTrue(set(BASELINE["original_order"]).issubset(headings),
                        "Existing operating sections must remain discoverable")

    def test_unrelated_instruction_text_can_change_without_migration_rebaseline(self):
        from unittest.mock import patch
        parts = self.parts()
        parts[-1] += b"\nA future authorized clarification outside the loaded prefix.\n"
        with patch.object(self, "parts", return_value=parts):
            self.test_required_sections_preserved_without_freezing_all_prose()

    def test_additional_unique_section_can_be_added_without_migration_rebaseline(self):
        from unittest.mock import patch
        parts = self.parts() + [b"## Future domain navigation\nUse only when the task needs it.\n"]
        with patch.object(self, "parts", return_value=parts):
            self.test_required_sections_preserved_without_freezing_all_prose()

    def test_duplicate_operating_section_still_fails(self):
        from unittest.mock import patch
        parts = self.parts()
        with patch.object(self, "parts", return_value=parts + [parts[1]]):
            with self.assertRaises(AssertionError):
                self.test_required_sections_preserved_without_freezing_all_prose()

    def test_missing_required_operating_section_still_fails(self):
        from unittest.mock import patch
        parts = self.parts()
        with patch.object(self, "parts", return_value=parts[:-1]):
            with self.assertRaises(AssertionError):
                self.test_required_sections_preserved_without_freezing_all_prose()

    def test_navigation_and_release_guidance_still_present(self):
        raw = (ROOT / "AGENTS.md").read_bytes()
        for item in [b"templates/_site_nav.html.j2", b"templates/_public_nav.html.j2",
                     b"DEC:SOL-HOLD-IS-A-MERGE-BARRIER", b"EFFECT_UNKNOWN",
                     b"explicit safety/permission refusal", b"config/sparse_worktree.json"]:
            self.assertIn(item, raw)


if __name__ == "__main__":
    unittest.main()
