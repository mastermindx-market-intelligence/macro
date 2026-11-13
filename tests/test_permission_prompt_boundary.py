"""A local approval setting never cancels real provider/OS user consent."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def normalized(path):
    return ' '.join(re.sub(r'[*`#>]', '', path.read_text()).split()).lower()


class PermissionPromptBoundaryTests(unittest.TestCase):
    def test_no_blanket_permission_prompt_exemption(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(surface=name):
                text = normalized(ROOT / name)
                self.assertNotIn('a permission prompt is never the blocker', text)
                self.assertIn('an actual permission or consent prompt remains a real boundary', text)

    def test_known_human_control_does_not_require_repeat_attempts(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(surface=name):
                text = normalized(ROOT / name)
                self.assertNotIn('two no-delta attempts with a changed tactic', text)
                self.assertIn('a known human-only control requires no repeated probe', text)

    def test_routine_remediation_and_explicit_denials_both_remain(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(surface=name):
                text = normalized(ROOT / name)
                self.assertIn('administrative blockers are self-remedied', text)
                self.assertIn('classify the observed error before declaring a refusal', text)
                self.assertIn('a permissive local setting does not authorize bypassing', text)



    def test_technical_error_is_not_reclassified_as_a_global_retry_ban(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(surface=name):
                text = normalized(ROOT / name)
                self.assertIn('classify the observed error before declaring a refusal', text)
                self.assertNotIn('an explicit safety/permission refusal ends', text)
        skill = normalized(ROOT / '.claude/skills/fable-mode/SKILL.md')
        self.assertIn('a tool failure is not a universal stop', skill)
        self.assertNotIn('never change accounts, tools, models or carriers', skill)

if __name__ == '__main__':
    unittest.main()
