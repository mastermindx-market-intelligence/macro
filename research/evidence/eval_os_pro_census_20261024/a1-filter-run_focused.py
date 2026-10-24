"""Run exact focused test functions without importing the unavailable pytest runner.

The tests still execute their real Node rendering/handler harness and assertions.
No application dependency or fixture is mocked by this selection runner.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / 'tests/test_admin_intelligence_os_ui.py'
TEST_NAMES = [
    'test_translated_filter_copy_retains_canonical_values_and_counts',
    'test_actual_evidence_filter_row_translates_status_before_count',
    'test_class_and_authority_chip_counts_match_the_rows_they_filter',
]


def main():
    if not shutil.which('node'):
        raise RuntimeError('Installed Node is required; this runner never skips')
    module = ast.parse(TEST_FILE.read_text(encoding='utf-8'))
    selected = []
    for item in module.body:
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            if isinstance(item, ast.Import) and any(alias.name == 'pytest' for alias in item.names):
                continue
            selected.append(item)
        elif isinstance(item, ast.Assign):
            names = [target.id for target in item.targets if isinstance(target, ast.Name)]
            if any(name in {'REPO', 'APP', 'START', 'END'} for name in names):
                selected.append(item)
        elif isinstance(item, ast.FunctionDef) and item.name in {'_contract', *TEST_NAMES}:
            selected.append(item)
    namespace = {'__file__': str(TEST_FILE)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(TEST_FILE), 'exec'), namespace)
    baseline = '--baseline' in sys.argv
    if baseline:
        namespace['APP'] = ROOT / 'baseline/admin/static/app.js'
    checks = []
    names = TEST_NAMES[-1:] if baseline else TEST_NAMES
    for name in names:
        started = time.monotonic()
        try:
            namespace[name]()
            checks.append({'name': name, 'passed': True, 'seconds': round(time.monotonic() - started, 6)})
        except Exception as error:
            checks.append({'name': name, 'passed': False, 'seconds': round(time.monotonic() - started, 6),
                           'error_type': type(error).__name__, 'error': str(error),
                           'traceback': traceback.format_exc(limit=3)})
    app = namespace['APP']
    receipt = {'runner': 'direct exact Python test functions with installed Node client harness; not pytest suite',
               'mode': 'unmodified-source negative control' if baseline else 'patched-source focused checks',
               'app_sha256': hashlib.sha256(app.read_bytes()).hexdigest(),
               'test_sha256': hashlib.sha256(TEST_FILE.read_bytes()).hexdigest(),
               'checks': checks, 'all_passed': all(check['passed'] for check in checks)}
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
