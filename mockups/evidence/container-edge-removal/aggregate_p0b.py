from pathlib import Path
import json,hashlib,copy,datetime
R=Path.cwd();D=R/'mockups/evidence/prophet-p0b-zero-fouc';P=D/'manifest.json'
raw=P.read_bytes();m=json.loads(raw);old=copy.deepcopy(m['repair_extension'])
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fixture=D/'rendered-fixture.json';fs=digest(fixture);fresh=json.loads(fixture.read_text())
receipts={};screens={}
for market,filename,html in [('hk','mobile-layout.json','hk_stocks.html'),('ca','mobile-layout-canada.json','canada_stocks.html')]:
 p=D/filename;r=json.loads(p.read_text());x=r['owner_projection_matrix']
 assert r['pass'] is True and x['pass'] is True
 assert r['fixture_market']==market and r['claims']==old['claims']
 assert r['fixture_receipt']['sha256']==fs
 assert x['primary_passed']==48 and x['degraded_controls_passed']==16 and x['screenshot_count']==8
 assert len(x['cases'])==64 and all(c['pass'] for c in x['cases'])
 assert digest(R/r['verifier']['path'])==r['verifier']['sha256']
 assert digest(R/'.tmp/p0b-current-fixtures'/html)==r['input_html']['sha256']
 for key in ['construction_inputs','loaded_assets']:
  for path,sha in r[key].items(): assert digest(R/path)==sha,(market,key,path)
 for c in x['cases']:
  if c.get('screenshot'):
   z=c['screenshot'];assert digest(R/z['path'])==z['sha256'];screens[z['path']]=z['sha256']
 receipts[market]=dict(path=str(p.relative_to(R)),sha256=digest(p),pass_=r['pass'],primary_cases=x['primary_passed'],degraded_control_cases=x['degraded_controls_passed'],screenshots=x['screenshot_count'])
 receipts[market]['pass']=receipts[market].pop('pass_')
assert len(screens)==16
e={key:copy.deepcopy(old[key]) for key in ('schema','operation','claims')}
e.update(generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),fixture_receipt=dict(path=str(fixture.relative_to(R)),sha256=fs),browser_receipts=receipts,screenshots=[dict(path=p,sha256=h) for p,h in sorted(screens.items())],totals=dict(markets=2,owner_cases_per_market=3,primary_cases=sum(x['primary_cases'] for x in receipts.values()),degraded_control_cases=sum(x['degraded_control_cases'] for x in receipts.values()),total_cases=128,screenshots=len(screens)))
e['pass']=True
m.setdefault('repair_extension_history',[]).append(dict(extension=old,prior_manifest_sha256=hashlib.sha256(raw).hexdigest(),source_head='c7f08871a7650e1fc7052d792a1592b55cf34c81'))
m['repair_extension']=e
P.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(history=len(m['repair_extension_history']),totals=e['totals'],manifest_sha256=digest(P)),indent=2))
