"""Source transport checks, not claimed model-behavior or runtime-admission proof."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.claude/skills/fable-mode'


class FableEntrypointBudgetTests(unittest.TestCase):
    def test_default_entrypoint_fits_bounded_context(self):
        self.assertLessEqual((SKILL / 'SKILL.md').stat().st_size, 8 * 1024)

    def test_discovery_description_is_a_small_trigger_not_a_second_playbook(self):
        text = (SKILL / 'SKILL.md').read_text()
        match = re.search(r'^description: (.+)$', text, re.M)
        self.assertIsNotNone(match)
        self.assertLessEqual(len(match.group(1)), 400)

    def test_full_numbered_reference_remains_available(self):
        text = (SKILL / 'references/seat-doctrine.md').read_text()
        for prefix, count in [('S', 8), ('O', 17), ('L', 14), ('A', 7)]:
            for number in range(1, count + 1):
                self.assertIn(f'**{prefix}.{number} ', text)

    def test_default_does_not_demand_full_reference_census(self):
        text = (SKILL / 'SKILL.md').read_text()
        self.assertNotIn('in full (once per session)', text)
        self.assertIn('Load only the section needed for the next decision', text)
        self.assertIn('Do not reload the package after each phase', text)

    def test_controls_and_continuation_remain_in_the_default_context(self):
        text = (SKILL / 'SKILL.md').read_text()
        for clause in ['EFFECT_UNKNOWN', 'one owner, one verified return binding',
                       'DO_NOT_REDO', 'explicit permission or safety refusal',
                       'current assignment', 'archived chat', 'ACTIVE_EXECUTION',
                       'next safe ready phase', 'actual release controls']:
            self.assertIn(clause, text)

    def test_all_linked_reference_files_exist(self):
        text = (SKILL / 'SKILL.md').read_text()
        links = re.findall(r'\]\((references/[^)#]+\.md)(?:#[^)]*)?\)', text)
        self.assertGreaterEqual(len(set(links)), 7)
        for link in links:
            self.assertTrue((SKILL / link).is_file(), link)

    def test_repo_pointer_keeps_same_checkout_without_mandatory_full_core(self):
        pointer = (ROOT / '.agents/skills/fable-mode/SKILL.md').read_text()
        self.assertIn('../../../.claude/skills/fable-mode/SKILL.md', pointer)
        self.assertIn('same checkout', pointer)
        self.assertNotIn('read it first, in full', pointer)


if __name__ == '__main__':
    unittest.main()
