"""Static compatibility audit of the immutable R9 research plan.

Only the R9 synthetic fixture and selected, explicitly transcribed shared-contract
constraints are evaluated. This does NOT import or execute the native shared
validator, verify its whole-file bytes, run product tests, or accept the design.
No network, provider, production, or repository writes. Output is local research.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re

PLAN_BLOB = 'f58970d627a6334905bd42fa5994a25a2b00956a'
SHARED_HEAD = '45eb37bbf832e007e67ce2594674d6bfeeb3b880'
PREDICATES = ['PRODUCT_CAPABILITY','DOCUMENTED_PRODUCT_INCLUSION',
 'ANNOUNCED_DEVELOPMENT_AGREEMENT','DEPLOYMENT_TARGET','REPORTED_DEPLOYMENT',
 'OWNERSHIP_EVENT','REPORTED_FINANCIAL_MEASURE','REPORTED_OPERATING_MEASURE']
BASES = ['per_robot','per_joint','per_hand','per_cell','per_installation',
 'per_unit','per_wafer','per_package','per_device','per_period','absolute']
OBS_ENUMS = {'quantity_basis': BASES, 'gross_net_basis': ['gross','net',None],
 'estimate_status': ['reported','estimated','target'],
 'precision': ['integer','decimal','range','approximate']}
TOP_KEYS = ['schema','curation_revision','review','source','subject','object',
 'predicate','statement_mode','scope','observation','temporal','limitations',
 'correction','authority','industrial_context']

def blob(data: bytes) -> str:
 return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def fixture_from_plan(text: str) -> dict:
 blocks = re.findall(r'```python\n(.*?)```', text, re.S)
 functions = [n for b in blocks for n in ast.parse(b).body
              if isinstance(n, ast.FunctionDef) and n.name == 'native_fixture']
 if len(functions) != 1:
  raise ValueError('exactly one native_fixture is required')
 fn = functions[0]
 # Extract literal source bytes, then replace the sole permitted digest call.
 first = fn.body[0]
 if not isinstance(first, ast.Assign) or not isinstance(first.targets[0], ast.Name) \
   or first.targets[0].id != 'source_bytes':
  raise ValueError('unexpected source_bytes assignment')
 source = ast.literal_eval(first.value)
 if type(source) is not bytes or len(source) > 4096:
  raise ValueError('fixture source is not bounded literal bytes')
 ret = next((n for n in fn.body if isinstance(n, ast.Return)), None)
 if ret is None:
  raise ValueError('fixture has no literal return')
 class DigestOnly(ast.NodeTransformer):
  def visit_Call(self, node):
   if ast.unparse(node) != 'hashlib.sha256(source_bytes).hexdigest()':
    raise ValueError('non-whitelisted expression in fixture')
   return ast.copy_location(ast.Constant(hashlib.sha256(source).hexdigest()), node)
 data = ast.literal_eval(DigestOnly().visit(copy.deepcopy(ret.value)))
 if not isinstance(data, dict):
  raise ValueError('fixture return is not an object')
 return data

def selected_shape_mismatches(record: dict) -> list[dict]:
 out = []
 for key in record:
  if key not in TOP_KEYS:
   out.append({'path': key, 'found': 'present', 'basis': 'additionalProperties=false; key absent'})
 if record['predicate'] not in PREDICATES:
  out.append({'path':'predicate','found':record['predicate'],'allowed':PREDICATES})
 for key, choices in OBS_ENUMS.items():
  if record['observation'][key] not in choices:
   out.append({'path':'observation.'+key,'found':record['observation'][key],'allowed':choices})
 return out

def canonical_material(record: dict) -> bytes:
 return json.dumps({k:v for k,v in record.items() if k != 'curation_revision'},
                   ensure_ascii=False,sort_keys=True,separators=(',',':'),
                   allow_nan=False).encode()

def audit(plan: Path) -> dict:
 data = plan.read_bytes()
 if blob(data) != PLAN_BLOB:
  raise ValueError('R9_PLAN_HASH_MISMATCH: refusing changed plan')
 record = fixture_from_plan(data.decode())
 mismatch = selected_shape_mismatches(record)
 if len(mismatch) != 6:
  raise AssertionError('expected six selected schema mismatches')
 # Hashes below illustrate the two published algorithms, not native validation.
 material = canonical_material(record)
 shared_formula = 'gmirca_'+hashlib.sha256(material).hexdigest()[:32]
 r9_formula = 'gmirca_'+hashlib.sha256(b'gmi-curation-v1\0'+material).hexdigest()[:32]
 assert shared_formula != r9_formula
 checks = [{'id':'R10-C01','observation':'R9 fixture violates six selected schema constraints',
            'established':True,'details':mismatch},
           {'id':'R10-C02','observation':'R9 prefixed hash differs from shared documented formula',
            'established':True,'shared_formula_for_unadmitted_fixture':shared_formula,
            'r9_formula_for_unadmitted_fixture':r9_formula},
           {'id':'R10-C03','observation':'Stamping a null-revision candidate changes its value',
            'established':record['curation_revision'] is None,
            'scope':'Logical consequence of documented mint behavior, not native execution'},
           {'id':'R10-C04','observation':'A signed negative measure is outside the shared legacy value rule',
            'established':True,'synthetic_value':-1,
            'scope':'Selected source rule requires finite non-negative values; no native execution'}]
 # A distinct generic positive financial fixture is NOT the royalty fact relabeled.
 control = copy.deepcopy(record)
 control.pop('economic_right')
 control['predicate'] = 'REPORTED_FINANCIAL_MEASURE'
 control['subject']['source_business_label'] = 'Synthetic control business'
 control['observation'].update(value=1,unit='USD',quantity_basis='per_period',
                              gross_net_basis='gross',estimate_status='reported',precision='integer')
 assert not selected_shape_mismatches(control)
 assert record['economic_right']['rate_terms']['numeric_value'] is None
 assert all(v is False for v in record['authority'].values())
 prior = {'robotics:A','semiconductor:B'}
 healthcare_only = {'healthcare:C'}
 assert prior - healthcare_only == prior
 retained = prior | healthcare_only
 assert prior <= retained
 return {'artifact_kind':'author_static_plan_compatibility_audit', 'date':'2026-09-24',
  'operation_key':'gmi-healthcare-deep-research-20260923-sol-001',
  'r9_plan_git_blob':PLAN_BLOB,'r9_plan_sha256':hashlib.sha256(data).hexdigest(),
  'shared_code_head':SHARED_HEAD,
  'constraint_source_blobs':{
   'contracts/theme_graph/curation_assertion.v1.schema.json':'ff3928f0c54aa164ef8283d9da45af67e6a0d971',
   'engine/theme_graph/curation_assertion.py':'23a25614782b8b1cb76ce7e3f292b64d35bfb4f6'},
  'method':'R9 bytes verified; selected shared constraints manually transcribed from connector reads. Not a full native-schema or native-code execution.',
  'checks':checks,'selected_schema_mismatches':6,'compatibility_observations':9,
  'controls':{'distinct_positive_financial_record_passes_selected_constraints':True,
              'unknown_royalty_remains_null':True,'authority_all_false':True,
              'complete_next_set_preserves_other_domains':True},
  'planning_counterexample':{'prior_count':2,'healthcare_only_count':1,
                             'unrelated_records_lost_by_naive_replace':2,
                             'scope':'hypothetical set model; not an observed publication defect'},
  'native_module_executed':False,'native_schema_executed':False,
  'application_tests_executed':0,'independent_review':False,
  'design_accepted':False,'implementation_started':False,
  'external_side_effects':0}

def main() -> None:
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--plan',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True)
 args=ap.parse_args()
 result=audit(args.plan)
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'selected_schema_mismatches':result['selected_schema_mismatches'],
                   'compatibility_observations':result['compatibility_observations'],
                   'native_execution':False,'application_tests':0},indent=2))
if __name__=='__main__': main()
