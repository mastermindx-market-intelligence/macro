"""Instruction transport regression: keep existing continuation guidance inside the budget.

This is not a claim of model behavior or repaired Stop hooks. Every original
section must remain byte-identical; no runtime permission is modified.
"""
import hashlib
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

    def test_no_guidance_is_deleted_duplicated_or_rewritten(self):
        parts = self.parts()
        headings = [p.splitlines()[0].decode() for p in parts[1:]]
        self.assertEqual(len(headings), len(set(headings)))
        self.assertCountEqual(headings, BASELINE["original_order"])
        sections = dict(zip(headings, parts[1:]))
        restored = parts[0] + b"".join(sections[name] for name in BASELINE["original_order"])
        self.assertEqual(len(restored), BASELINE["bytes"])
        self.assertEqual(hashlib.sha256(restored).hexdigest(), BASELINE["sha256"])

    def test_navigation_and_release_guidance_still_present(self):
        raw = (ROOT / "AGENTS.md").read_bytes()
        for item in [b"templates/_site_nav.html.j2", b"templates/_public_nav.html.j2",
                     b"DEC:SOL-HOLD-IS-A-MERGE-BARRIER", b"EFFECT_UNKNOWN",
                     b"explicit safety/permission refusal", b"config/sparse_worktree.json"]:
            self.assertIn(item, raw)


if __name__ == "__main__":
    unittest.main()
