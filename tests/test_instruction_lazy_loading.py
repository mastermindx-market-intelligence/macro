"""Entrypoints stay complete within the native budget; effect guides are explicit.

These are static transport/structure checks, not permission decisions or claims
that a model read a procedure. A linked guide remains required before its effect.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstructionLazyLoadingTests(unittest.TestCase):
    def test_both_entrypoints_fit_shared_codex_default_budget(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(name=name):
                self.assertLess(len((ROOT / name).read_bytes()), 32 * 1024)

    def test_codex_does_not_import_the_entire_claude_guide(self):
        text = (ROOT / 'AGENTS.md').read_text()
        self.assertNotIn('Read `CLAUDE.md` in full', text)
        self.assertIn('Read only the task-relevant sections', text)

    def test_guides_are_explicit_real_links_not_automatic_imports(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(name=name):
                text = (ROOT / name).read_text()
                refs = re.findall(r'\]\((docs/agent_guides/[A-Z_]+\.md)\)', text)
                self.assertGreaterEqual(len(refs), 3)
                self.assertEqual(len(refs), len(set(refs)))
                self.assertNotRegex(text, r'(?m)^\s*@docs/agent_guides/')
                for ref in refs:
                    path = ROOT / ref
                    self.assertTrue(path.is_file(), ref)
                    self.assertGreater(len(path.read_bytes()), 100)

    def test_effect_guides_are_required_before_not_after_actions(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(name=name):
                text = ' '.join((ROOT / name).read_text().split())
                self.assertIn('Read the linked effect guide before the first relevant action', text)
                for word in ('workspace', 'release', 'permission', 'EFFECT_UNKNOWN'):
                    self.assertIn(word, text)

    def test_ordinary_technical_work_is_not_a_department_approval(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(name=name):
                text = ' '.join((ROOT / name).read_text().split())
                self.assertIn('An architectural owner is not a live session', text)
                self.assertIn('Data OS', text)
                self.assertIn('existing interfaces', text)


    def test_compaction_availability_is_not_frozen_to_an_old_client(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            with self.subTest(name=name):
                text = ' '.join((ROOT / name).read_text().split()).lower()
                self.assertFalse('there is no configurable compaction threshold' in text,
                                 'Legacy capability denial must be replaced by current-client discovery')
                self.assertIn('compaction controls are harness- and version-specific', text)


    def test_recovery_does_not_require_mutating_the_occupied_primary(self):
        for name in ('CODEX_WORKSPACE.md', 'CLAUDE_WORKSPACE_COMPLETION.md'):
            with self.subTest(name=name):
                text = ' '.join((ROOT / 'docs/agent_guides' / name).read_text().replace('**', '').split()).lower()
                self.assertFalse('if the fast-forward fails, stop and tell the operator' in text,
                                 'A failed primary update must not block an admitted isolated workspace')
                self.assertIn('do not fast-forward an occupied primary checkout', text)
                self.assertIn('preserve the exact existing workspace', text)

    def test_local_memory_is_not_a_redundant_startup_gate(self):
        text = (ROOT / 'AGENTS.md').read_text()
        self.assertFalse('For delivery work, always include' in text,
                         'Historical local delivery notes are advisory, not required duplicate bootstrap')
        self.assertIn('Account-local memory is optional task context', text)


    def test_relocated_case_law_quotes_keep_resolvable_source_paths(self):
        import yaml
        graph = yaml.safe_load((ROOT / 'config/ruling_graph.yml').read_text())
        selected = [r for r in graph['rulings'] if r['ruling_id'] in
                    {'HOUSE-U1', 'HOUSE-U2', 'HOUSE-U3', 'HOUSE-U4', 'HOUSE-U5'}]
        self.assertEqual(len(selected), 5)
        for row in selected:
            with self.subTest(ruling=row['ruling_id']):
                source = ' '.join((ROOT / row['source_doc']).read_text().split())
                quote = ' '.join(row['source_quote'].split())
                self.assertTrue(quote in source,
                                row['ruling_id'] + ' source_doc must follow its unchanged quote')


if __name__ == '__main__':
    unittest.main()
