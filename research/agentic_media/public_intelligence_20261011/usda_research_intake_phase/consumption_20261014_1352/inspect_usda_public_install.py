import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path('/opt/macro'); sid='usda-2026-10-09-wasde-676'; slug='world-agricultural-supply-and-demand-estimates-october-2026-wasde-676-sde676'
head=lambda:subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
r={'observed_at':datetime.now(timezone.utc).isoformat(),'head_before':head(),'files':{},'writes':0}
for rel in ['data/research_vault/catalog.json','data/research_vault/excerpts.json','site/research/'+slug+'.html','site.served/research/'+slug+'.html','site/research_vault.html','site.served/research_vault.html']:
 p=root/rel; v={'present':p.is_file()}
 if p.is_file():
  b=p.read_bytes();v.update(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
  if rel.endswith('catalog.json'):
   x=json.loads(b); rows=[z for z in x.get('items',[]) if z.get('id')==sid];v.update(total=len(x.get('items',[])),matching_rows=len(rows),row=rows[0] if rows else None)
  elif rel.endswith('excerpts.json'):
   paras=json.loads(b).get('excerpts',{}).get(sid,[]);v.update(paragraphs=len(paras),characters=sum(map(len,paras)))
 r['files'][rel]=v
r['head_after']=head();r['stable_head']=r['head_before']==r['head_after'];print(json.dumps(r,indent=2))
