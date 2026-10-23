"""Selected code mutations in throwaway copies; never alters accepted source."""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'evidence'
SOURCE = (ROOT / 'structural_guards.py').read_text()
MUTANTS = [
 ('clock_type_bypass', 'return type(value) is int and 0 <= value <= (1 << 63) - 1', 'return True'),
 ('identity_truthiness', 'return isinstance(value, str) and bool(value) and value == value.strip()', 'return bool(value)'),
 ('rounded_absolute', 'row.signed_pressure.copy_abs() > row.gross_notional', 'abs(row.signed_pressure) > row.gross_notional'),
 ('drop_action_and_sign_conflict', 'identity = (row.revision_id, row.monetary_basis_id, row.corporate_action_vintage,\n                    row.gross_notional, row.signed_pressure)', 'identity = (row.revision_id, row.monetary_basis_id, None,\n                    row.gross_notional, None)'),
 ('low_decimal_precision', 'ARITHMETIC_PRECISION = 1024', 'ARITHMETIC_PRECISION = 28'),
 ('future_baseline_disabled', 'if any(x.known_ns >= cutoff_ns for x in data):', 'if False:'),
 ('equal_clock_quote_allowed', 'if row.quote_time_ns >= row.print_time_ns:', 'if row.quote_time_ns > row.print_time_ns:'),
 ('publication_authority_enabled', 'publication_authorized: bool = False', 'publication_authorized: bool = True'),
]
rows = []
for name, before, after in MUTANTS:
    assert SOURCE.count(before) == 1, name
    changed = SOURCE.replace(before, after)
    ast.parse(changed)  # A syntax/import failure is NOT a killed semantic mutant.
    with tempfile.TemporaryDirectory(prefix='atlas_s6_mutant_') as tmp:
        tmp = Path(tmp)
        (tmp/'structural_guards.py').write_text(changed)
        for file in ('test_structural_guards.py', 'test_deep_guards.py'):
            (tmp/file).write_bytes((ROOT/file).read_bytes())
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TERM='dumb')
        p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--tb=short', '--maxfail=3',
                            'test_structural_guards.py','test_deep_guards.py'],
                           cwd=tmp, env=env, capture_output=True, text=True, timeout=20)
        text = p.stdout+p.stderr
        killed = p.returncode == 1 and 'failed' in text and 'ERROR collecting' not in text
        (OUT/(name+'.log')).write_text(text)
        rows.append(dict(name=name, returncode=p.returncode, semantic_failure_detected=killed,
                         mutated_source_sha256=hashlib.sha256(changed.encode()).hexdigest(),
                         log_sha256=hashlib.sha256(text.encode()).hexdigest(),
                         summary='\n'.join(text.splitlines()[-4:])))
result = dict(status='SYNTHETIC_SELECTED_MUTATIONS_ONLY',
              source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
              mutants=len(rows), killed=sum(x['semantic_failure_detected'] for x in rows), results=rows)
(OUT/'mutation_results.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='results'}, indent=2))
assert result['killed'] == result['mutants'], result
