"""Counterfactual tests for R5; no provider/data/runtime IO."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
import decision_speed_r5
import test_decision_speed_r5 as checks

original=Path(decision_speed_r5.__file__).read_text()
cases=[
 ('future_price','end=anchor-delay;begin=end-lookback','end=anchor-delay+1;begin=end-lookback','test_late_prices_cannot_change_target'),
 ('source_lag_ignored','end=anchor-delay;begin=end-lookback','end=anchor;begin=end-lookback','test_delay_ignores_recent_price'),
 ('62_instead_of_63','end=anchor-delay;begin=end-lookback','end=anchor-delay;begin=end-lookback+1','test_63_intervals_not_62'),
 ('repeated_poll_confirmation','if source_version==self.version:return self.accepted.copy()','if False:return self.accepted.copy()','test_duplicate_source_does_not_confirm'),
 ('free_bill','[:,1:]','[:,1:-1]','test_flat_roundtrip'),
 ('terminal_new_trade','elif e<END:','elif e<=END:','test_no_terminal_rebalance_only_sale'),
 ('false_authority',"'investment_authority':False","'investment_authority':True",'test_no_authority_flags'),
]
rows=[]
for name,before,after,test in cases:
 if before not in original:raise AssertionError('mutation target missing '+name)
 if name=='free_bill':
  begin=original.index('def rebalance_many');end=original.index('def rolling_target')
  source=original[:begin]+original[begin:end].replace(before,after)+original[end:]
 else:source=original.replace(before,after)
 mod=types.ModuleType('r5_mutant');mod.__file__=decision_speed_r5.__file__;sys.modules[mod.__name__]=mod
 exec(compile(source,mod.__file__,'exec'),mod.__dict__)
 saved=checks.m;checks.m=mod
 try:
  stream=io.StringIO()
  result=unittest.TextTestRunner(stream=stream).run(checks.TimingAndCosts(test))
 finally:checks.m=saved
 if len(result.failures)!=1 or result.errors:raise AssertionError(name+' not discriminating: '+stream.getvalue())
 rows.append(dict(case=name,test=test,failures=len(result.failures),errors=len(result.errors)))
print(json.dumps(dict(subject_sha256=hashlib.sha256(original.encode()).hexdigest(),mutations=rows,market_data_read=False,independent_review=False),indent=2,sort_keys=True))
