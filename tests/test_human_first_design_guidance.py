"""Guard source enrollment only; these tests cannot prove human comprehension."""
from pathlib import Path
import unittest
import shlex
import yaml

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

    def test_ci_executes_guidance_suite_in_existing_code_gate(self):
        manifest = yaml.safe_load(self.read(".github/ci/legacy-jobs.yml"))
        job = manifest["jobs"]["design-governance"]
        self.assertEqual(job["gate"], "code")
        self.assertNotIn("paths", job)  # Existing unscoped governance owner.
        commands = [shlex.split(step["run"]) for step in job["steps"]
                    if "run" in step and "if" not in step]
        self.assertTrue(any(tokens[:3] == ["python3", "-m", "pytest"]
                            and "tests/test_human_first_design_guidance.py" in tokens
                            for tokens in commands),
                        "The guidance suite must execute, not merely be named in paths.")

    def test_sector_consolidation_keeps_one_product_grammar(self):
        text = self.read("research/SECTOR_INTELLIGENCE_CONSOLIDATED_EXPERIENCE_2026-09-26.md")
        self.assertIn("Rotation · Discover · Market breadth", text)
        self.assertIn("Heatmap · Bubbles · Matrix · Table", text)
        self.assertIn("Overview · Companies · Signals · Drivers · History", text)
        self.assertIn("Cycle** capability is retained inside **History", text)
        self.assertIn("reported / supplied / readable / filtered", text)
        self.assertIn("rights_class: unresolved", text)
        self.assertIn("Broad market — Sector × Size", text)
        self.assertIn("Selected sector — Industry × Cap", text)
        self.assertIn("do not pretend those segments are exact market-cap cutoffs", text)
        self.assertIn("### Change, compare, save and monitor", text)
        self.assertIn("Do not create Sector-specific localStorage", text)
        self.assertIn("`Preference saved`, `watch active` and `alert delivered` are distinct states.", text)
        self.assertIn("`sector == Technology`, which yields 79 names", text)
    def test_existing_cross_model_entrypoints_keep_doctrine_link(self):
        for path in ("AGENTS.md", "CLAUDE.md"):
            with self.subTest(path=path):
                self.assertIn("docs/DESIGN_DOCTRINE.md", self.read(path))


if __name__ == "__main__":
    unittest.main()
