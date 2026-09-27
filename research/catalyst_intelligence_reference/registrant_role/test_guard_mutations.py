"""Discriminating in-memory checks for the proposed guard; no repo/live writes."""
from __future__ import annotations
import ast, io, json, unittest
from pathlib import Path
import test_registrant_role as r
from candidate_guard import patched_source

HERE = Path(__file__).resolve().parent
(HERE/'reports').mkdir(parents=True,exist_ok=True)
BASE = (HERE/'inputs/build_situations_excerpt.py').read_text()
CANDIDATE = patched_source(BASE)
FENCE = '        df.loc[non_target_gp, ["status", "category", "stage"]] = ["defer", None, None]'
changes = {
 'remove_guard': (FENCE, '        pass  # guard omitted'),
 'allow_issuer_as_target': ('.eq("target").fillna(False)', '.isin(["target", "issuer"]).fillna(False)'),
 'leave_direct_category': (FENCE, '        df.loc[non_target_gp, "status"] = "defer"'),
 'erase_source_annotation': (FENCE, FENCE+'\n        df.loc[non_target_gp, "llm_category"] = pd.NA'),
 'drop_related_evidence': (FENCE, FENCE+'\n        df = df.loc[~non_target_gp].copy()'),
 'block_every_going_private': ('non_target_gp = valid & llm.eq(GP).fillna(False) & ~target_role', 'non_target_gp = valid & llm.eq(GP).fillna(False)'),
}
results=[]
for name,(old,new) in changes.items():
 if CANDIDATE.count(old)!=1: raise RuntimeError('Non-unique mutation anchor: '+name)
 src=CANDIDATE.replace(old,new); ast.parse(src)
 r.ENGINE=r.load_engine(); exec(compile(src,'mutant:'+name,'exec'),r.ENGINE.__dict__)
 stream=io.StringIO()
 result=unittest.TextTestRunner(stream=stream,verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(r.RoleRegression))
 (HERE/'reports'/('MUTANT_'+name+'.log')).write_text(stream.getvalue())
 results.append({'name':name,'syntax_valid':True,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                 'killed_by_assertion':len(result.failures)>0 and len(result.errors)==0,
                 'failed_test_names':[str(t) for t,_ in result.failures]})
report={'scope':'captured_current_function_with_isolated_collaborators','mutants':results,
 'killed':sum(x['killed_by_assertion'] for x in results),'count':len(results),
 'production_modified':False,'full_repository_integration':False}
(HERE/'reports/ROLE_MUTATIONS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['killed']==report['count'] else 1)
