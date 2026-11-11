"""Finish the bounded integration using the existing CSS, repair, stamp and audit owners."""
from pathlib import Path
import json,sys,hashlib
R=Path.cwd();E=R/'mockups/evidence/container-edge-removal';I=E/'integration'
sys.path.insert(0,str(R))
def run(name,replacements):
 code=(E/name).read_text()
 for old,new in replacements:
  assert code.count(old)==1,(name,old,code.count(old));code=code.replace(old,new)
 exec(compile(code,str(E/name),'exec'),{'__name__':'__main__','__file__':str(E/name)})
run('repair_generated_css.py',[("Path('mockups/evidence/container-edge-removal/generated-css-receipt.json')","Path('mockups/evidence/container-edge-removal/integration/generated-css-receipt.json')")])
run('finish_consumers.py',[("(E/'consumer-residual-repairs.json')","(E/'integration/consumer-residual-repairs.json')")])
from scripts.optimize_assets import optimize
stamped=optimize(R/'site')
assert stamped>=0,stamped
(I/'asset-stamp-receipt.json').write_text(json.dumps({'owner':'scripts.optimize_assets.optimize','changed_files':stamped,'main':'c58c69bf42786f29c8857550bdb244d08da35240'},indent=2)+'\n')
print(json.dumps({'canonical_asset_stamp_files':stamped}),flush=True)
maps=json.loads((E/'consumer-projection-receipt.json').read_text())['renamed_assets'].copy()
maps.update(json.loads((I/'consumer-projection-receipt.json').read_text())['renamed_assets'])
for old,new in json.loads((E/'direct-source-edge-repairs.json').read_text())['renamed'].items():
 maps['assets/css/'+old+'.css']='assets/css/'+new+'.css'
for row in json.loads((I/'generated-css-receipt.json').read_text()):
 dest=row['asset'].removeprefix('site/')
 for old in row['old']:
  if old!=Path(dest).stem:maps['assets/css/'+old+'.css']=dest
(I/'combined-renames.json').write_text(json.dumps(maps,indent=2)+'\n')
run('audit_consumers.py',[
 ("renamed=json.loads((E/'consumer-projection-receipt.json').read_text())['renamed_assets']","renamed=json.loads((E/'integration/combined-renames.json').read_text())"),
 ("(E/'consumer-residual-audit.json')","(E/'integration/consumer-residual-audit.json')")])
report=json.loads((I/'consumer-residual-audit.json').read_text())
assert not report['residuals'] and not report['missing_assets'] and not report['superseded_references'],report
print('CURRENT_CONSUMER_AUDIT_PASS',flush=True)
