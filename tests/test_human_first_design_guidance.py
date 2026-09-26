"""Guard source enrollment only; these tests cannot prove human comprehension."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HumanFirstDesignGuidanceTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_existing_doctrine_owns_the_contract(self):
        doctrine = self.read("docs/DESIGN_DOCTRINE.md")
        self.assertIn("## 0. Human consumption, not interface study", doctrine)
        self.assertIn("3–4 seconds", doctrine)
        self.assertIn("budgets are ceilings, not quotas", doctrine)
        self.assertIn("Cold-reader evidence", doctrine)
        self.assertIn("Journey evidence", doctrine)

    def test_designer_builder_and_reviewer_load_same_owner(self):
        for role in ("designer", "builder", "reviewer"):
            with self.subTest(role=role):
                text = self.read(f".claude/agents/{role}.md")
                self.assertIn("## Human-consumption contract", text)
                self.assertIn("docs/DESIGN_DOCTRINE.md", text)
                self.assertIn("3–4-second", text)
                self.assertIn("depth", text)
                self.assertIn("return", text)

    def test_builder_preserves_design_and_reports_missing_human_testing(self):
        text = self.read(".claude/agents/builder.md")
        self.assertIn("not yet tested", text)
        self.assertIn("continue independent permitted work", text)
        self.assertIn("do not silently redesign", text)

    def test_reviewer_cannot_promote_mechanical_proof(self):
        text = self.read(".claude/agents/reviewer.md")
        self.assertIn("cannot prove actual human comprehension", text)
        self.assertIn("code-review PASS is not product", text)
        self.assertIn("Do not edit the artifact", text)

    def test_existing_cross_model_entrypoints_keep_doctrine_link(self):
        for path in ("AGENTS.md", "CLAUDE.md"):
            with self.subTest(path=path):
                self.assertIn("docs/DESIGN_DOCTRINE.md", self.read(path))


if __name__ == "__main__":
    unittest.main()
