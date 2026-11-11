"""Integrate current main's generated content with the verified rail-free presentation."""
from pathlib import Path
import subprocess, re, json, hashlib, sys
R=Path.cwd(); E=R/'mockups/evidence/container-edge-removal'; I=E/'integration'
MAIN='c58c69bf42786f29c8857550bdb244d08da35240'
HEAD='97abae6fa8f17bdb71f8670d59d1ba43497e3ae7'
def git(*args): return subprocess.check_output(['git',*args])
def digest(b): return hashlib.sha256(b).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert git('rev-parse','MERGE_HEAD').decode().strip()==MAIN
I.mkdir(exist_ok=True)
expected={'site/aibrief.html','site/crypto.html','site/etfs.html','site/help.html','site/macro_business_activity.html','site/macro_capital_structure.html','site/macro_consumer_payments.html','site/macro_financial_conditions.html','site/macro_growth_real_economy.html','site/macro_housing_real_estate.html','site/macro_inflation_system.html','site/macro_labor_markets.html','site/macro_liquidity_central_banks.html','site/macro_liquidity_regime.html','site/macro_monetary.html','site/macro_monetary_policy.html','site/macro_national_debt_liabilities.html','site/macro_rates_curves.html','site/macro_trade_flows.html','site/quant_lab.html','site/reference.html','site/special_situations.html','site/start.html','site/us_stocks.html','site/vector.html','site/watchlist.html'}
paths=set(git('diff','--name-only','--diff-filter=U').decode().splitlines())
assert paths==expected,(paths^expected)
binary={'site/etfs.html','site/us_stocks.html','site/special_situations.html'}
pattern=re.compile(r'^<<<<<<<.*?\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*(?:\n|$)',re.M|re.S)
resolved=[]
for path in sorted(paths):
 p=R/path; before=p.read_bytes(); hunks=[]
 if path in binary:
  after=git('show',MAIN+':'+path)
  mode='exact upstream generated HTML; apply reviewed presentation projection next'
 else:
  text=before.decode()
  def choose(m):
   hunks.append({'ours_sha256':digest(m[1].encode()),'upstream_sha256':digest(m[2].encode())})
   return m[2]
  after=pattern.sub(choose,text).encode()
  assert hunks,path
 assert b'<<<<<<<' not in after and b'>>>>>>>' not in after,path
 p.write_bytes(after)
 resolved.append({'path':path,'resolution':mode if path in binary else 'upstream refreshed content/timestamps in conflict hunks; retain clean merged presentation','hunks':hunks,'before_sha256':digest(before),'resolved_sha256':digest(after)})
subprocess.run(['git','add','--',*sorted(paths)],check=True)
assert not git('diff','--name-only','--diff-filter=U').strip()
record={'schema':'mastermind.container_edge_main_integration.v1','source_snapshot':HEAD,'main':MAIN,'previous_base':'65f534bdc1369d2496f8e044a90636997e223392','resolved':resolved}
(I/'merge-resolution.json').write_text(json.dumps(record,indent=2)+'\n')
# Reuse only reviewed immutable-asset replacements, never rebuild the catalog from new upstream content.
renames=json.loads((E/'consumer-projection-receipt.json').read_text())['renamed_assets'].copy()
for old,new in json.loads((E/'direct-source-edge-repairs.json').read_text())['renamed'].items():
 renames['assets/css/'+old+'.css']='assets/css/'+new+'.css'
replacement_changes=[]
for p in (R/'site').rglob('*.html'):
 text=p.read_text();new=text
 for old,dest in renames.items():
  if old not in new:continue
  assert (R/'site'/dest).is_file(),dest
  new=new.replace(old,dest).replace(dest+'?v='+Path(old).stem,dest+'?v='+Path(dest).stem)
 if new!=text:
  p.write_text(new);replacement_changes.append({'path':str(p.relative_to(R)),'before':digest(text.encode()),'after':digest(new.encode())})
(I/'historical-asset-rebinding.json').write_text(json.dumps({'source_snapshot':HEAD,'main':MAIN,'renames':renames,'changes':replacement_changes},indent=2)+'\n')
# Run the previously reviewed exact-match projection, preserving its original receipt.
code=(E/'project_consumers.py').read_text()
code=code.replace("sys.path.insert(0,str(Path(__file__).resolve().parent))","sys.path.insert(0,str(Path.cwd()/'mockups/evidence/container-edge-removal'))")
code=code.replace("base=catalog and '65f534bdc1369d2496f8e044a90636997e223392',source='a739405d248e3e985c6215067878028f8403fad9'","base='"+MAIN+"',source='"+HEAD+"'")
code=code.replace("(E/'consumer-projection-receipt.json')","(E/'integration/consumer-projection-receipt.json')")
exec(compile(code,str(E/'project_consumers.py'),'exec'),{'__name__':'__main__','__file__':str(E/'project_consumers.py')})
print(json.dumps({'resolved_conflicts':len(resolved),'historical_asset_rebound_pages':len(replacement_changes)}),flush=True)
