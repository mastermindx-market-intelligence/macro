import json
from pathlib import Path
out=Path(__file__).parent;before=json.loads((out/"native-intl-snapshot-before.json").read_text());after=json.loads((out/"native-intl-snapshot-after.json").read_text());differences=[]
def check(a,b,path=""):
 if isinstance(a,dict):
  for k,v in a.items():
   assert k in b,(path,k,"removed")
   check(v,b[k],path+"/"+k)
 elif isinstance(a,list):
  assert len(a)==len(b),(path,"row count changed")
  for i,(x,y) in enumerate(zip(a,b)):check(x,y,path+"/"+str(i))
 elif a!=b:differences.append({"path":path,"before":a,"after":b})
check(before,after)
assert differences==[{"path":"/countries/2/stale","before":False,"after":True}],differences
result={"scope":"Exact native retained7-country snapshot: every original numeric/model/scoring/narrative field unchanged; only Japan source-age stale flag corrected plus additive metadata","original_field_differences":differences,"source":"ed9fb81da853429ce87495d6c012467ebf057548"};(out/"native-retained-comparison.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
