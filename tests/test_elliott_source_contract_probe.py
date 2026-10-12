from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import subprocess
import unittest


PROBE_PATH = Path('research/technical_opportunity/elliott_phase/source_contract_probe.py')


def load_probe():
    spec = importlib.util.spec_from_file_location('elliott_source_contract_probe', PROBE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StableAstFingerprintTest(unittest.TestCase):
    def test_pinned_definition_digests_use_version_stable_payload(self):
        probe = load_probe()
        raw = subprocess.check_output(
            ['git', 'show', f'{probe.COMMIT}:{probe.SOURCE_PATH}'], timeout=30
        )
        tree = ast.parse(raw.decode('utf-8'))
        selected = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in probe.ASTS
        }
        self.assertEqual(set(selected), set(probe.ASTS))
        for name, node in selected.items():
            self.assertEqual(probe._stable_ast_digest(node), probe.ASTS[name])

    def test_empty_type_params_do_not_enter_stable_payload(self):
        probe = load_probe()
        node = ast.parse('def identity(value: int) -> int:\n    return value\n').body[0]
        payload = probe._stable_ast_payload(node)
        self.assertNotIn('type_params', payload)


if __name__ == '__main__':
    unittest.main()
