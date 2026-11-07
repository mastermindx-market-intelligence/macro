"""Bounded source-only audit of PR #8240's existing synthetic fixture."""
import ast
import copy
import importlib.util
import json
from pathlib import Path

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-root", required=True, type=Path)
args = parser.parse_args()
BASE = args.source_root.resolve()
spec = importlib.util.spec_from_file_location('audit_prophet', BASE / 'engine/prophet_early_leadership_evidence.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
tree = ast.parse((BASE / 'tests/test_prophet_fusion_w3_structural.py').read_text())
names = {'_DECISION', '_ASOF', '_KNOWN', '_THEME', '_ISSUER', '_SECURITY'}
nodes = [node for node in tree.body if
    (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))
    or (isinstance(node, ast.FunctionDef) and node.name == '_leadership_inputs')]
context = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<existing-synthetic-fixture>', 'exec'), context)
keys = ('candidate', 'peer_ex_candidate', 'theme_state', 'economic_exposure', 'setup_observation', 'entry_geometry')
baseline = dict(zip(keys, context['_leadership_inputs']()))
results = []
for rights_state in ('internal_allowed', 'RIGHTS_BLOCKED', 'UNAVAILABLE', 'UNKNOWN', 'REVOKED', 'rights_blocked'):
    values = copy.deepcopy(baseline)
    values['theme_state']['rights_state'] = rights_state
    out = mod.build_early_leadership_evidence(decision_at=context['_DECISION'], **values)
    results.append({'input_rights_state': rights_state, 'research_state': out['research_state'],
                    'emitted_acceleration': out['research_features']['theme_acceleration'],
                    'financial_authority_flags_all_false': all(value is False for value in out['authority'].values())})
values = copy.deepcopy(baseline)
values['theme_state']['dynamics']['acceleration'] = None
try:
    mod.build_early_leadership_evidence(decision_at=context['_DECISION'], **values)
    null_result = {'accepted': True}
except mod.EarlyLeadershipEvidenceError as exc:
    null_result = {'accepted': False, 'error': str(exc)}
report = {'source_head': '6d920952dc07731139cefc8a41cbd9bf92be5acf',
          'basis': 'existing synthetic fixture; no live data or provider calls',
          'rights_results': results, 'null_acceleration': null_result}
print(json.dumps(report, indent=2))
