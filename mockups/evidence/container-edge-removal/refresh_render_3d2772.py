"""Apply the exact previously qualified render recipes to one new scheduled render."""
from pathlib import Path
import argparse,hashlib,json
ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['project','finalize']);a=ap.parse_args()
E=Path('mockups/evidence/container-edge-removal');D=E/'integration-render-3d2772'
name='refresh_render_projection.py' if a.phase=='project' else 'refresh_render_finalize.py'
p=E/name;code=p.read_text()
replacements=[('integration-render-refresh','integration-render-3d2772'),('43b5acdb0d0f264091f5aa33c129625fd0b28b8c','3d277257801f2d22f54924cfab73f7cf48ec4ca8'),('bac05c4c15f648acb845a67caa54a7103b28fa6b','b032707276ed1d0a134ac384cc44366639912fc1')]
for old,new in replacements:
 assert old in code,(name,old)
 code=code.replace(old,new)
(D/(a.phase+'-recipe-binding.json')).write_text(json.dumps({'recipe':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'adapted_sha256':hashlib.sha256(code.encode()).hexdigest(),'changes':'Only explicit source refs and fresh receipt paths; exact existing algorithms unchanged.'},indent=2)+'\n')
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
if a.phase=='finalize':
 p=D/'validation-receipt.json';v=json.loads(p.read_text());assert len(v['checks'])==5 and all(x['exit_code']==0 for x in v['checks']);v['overall']='passed';p.write_text(json.dumps(v,indent=2)+'\n')
