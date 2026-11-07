"""Author-run counterfactual checks of the synthetic reference, not code review."""
from __future__ import annotations
import ast
import hashlib
import io
import json
from pathlib import Path
import types
import unittest
import allocation_rehearsal as original
import test_allocation_rehearsal as tests

MUTATIONS=(
 ('wrong_lookback',"log_return(values[-64:],63)","log_return(values[-63:],62)",
  'AdditionalRegressions.test_wrong_62_interval_integration_changes_cash_decision'),
 ('late_snapshot',"if f['read_clock'] <= cutoff:","if True:",
  'AvailabilityAndSelection.test_future_snapshot_does_not_change_previous_decision'),
 ('rewind_bad_vintage',"newest=max(f['read_clock'] for f in candidates)",
  "newest=min(f['read_clock'] for f in candidates)",
  'AvailabilityAndSelection.test_newest_eligible_invalid_snapshot_does_not_rewind'),
 ('cash_hurdle_equality',"r[t]>r['BIL']","r[t]>=r['BIL']",
  'AvailabilityAndSelection.test_deterministic_tie_and_strict_cash_hurdle'),
 ('pretend_bill_trade_free',"[0.0]+[cost]*len(INPUTS)",
  "[0.0]+[cost if t!='BIL' else 0.0 for t in INPUTS]",
  'ContinuousPolicy.test_flat_roundtrip_exact_all_policies'),
 ('omit_liquidation_from_drawdown',"+[liquidation['post_wealth']]","+[]",
  'ContinuousPolicy.test_final_liquidation_is_in_drawdown'),
 ('ignore_unavailable_decision',"if any(d['status']!='available' for d in decisions):","if False:",
  'ContinuousPolicy.test_schedule_geometry_and_no_reanchor'),
 ('grant_investment_authority',"investment_authority=False","investment_authority=True",
  'ContinuousPolicy.test_every_output_denies_investment_authority'),
)

def run():
    source=Path(original.__file__).read_text();out=[]
    for name,before,after,test in MUTATIONS:
        count=source.count(before)
        if count != (2 if name=='pretend_bill_trade_free' else 1):raise AssertionError((name,count))
        m=types.ModuleType('synthetic_mutation_'+name);m.__file__=original.__file__
        exec(compile(source.replace(before,after),m.__file__,'exec'),m.__dict__)
        tests.a=m
        try:
            suite=unittest.defaultTestLoader.loadTestsFromName('test_allocation_rehearsal.'+test)
            r=unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        finally:tests.a=original
        # Require an actual assertion discriminator, not an unrelated import/error.
        if len(r.failures)!=1 or r.errors or r.testsRun!=1:raise AssertionError((name,r.failures,r.errors))
        out.append(dict(name=name,discriminator=test,assertion_failures=1,errors=0))
    module=__import__('policy_accounting_witness')
    tree=ast.parse(Path(module.__file__).read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rebalance')
    return dict(scope='SYNTHETIC_COUNTERFACTUAL_TESTS_ONLY',mutation_count=len(out),results=out,
         subject_sha256=hashlib.sha256(source.encode()).hexdigest(),
         test_sha256=hashlib.sha256(Path(tests.__file__).read_bytes()).hexdigest(),
         script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         reused_rebalance_ast_sha256=hashlib.sha256(ast.dump(function,include_attributes=False).encode()).hexdigest(),
         native_qualification=False,independent_review=False,market_data_read=False)

if __name__=='__main__':print(json.dumps(run(),indent=2,sort_keys=True,allow_nan=False))
