from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,sys,urllib.parse
W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');D=Path(__file__).resolve().parent/'publisher-census-20261014';R=D/'legacy-classification';R.mkdir(exist_ok=True)
sys.path.insert(0,str(W/'scripts/ci'));import govrev_publisher_preflight as p
class Retained(p.GitHub):
 def __init__(self,token):super().__init__(token);self.index=[]
 def read(self,url,**kw):
  b=super().read(url,**kw);name=f'{len(self.index):03d}.bin.gz';(R/name).write_bytes(gzip.compress(b,mtime=0));u=urllib.parse.urlsplit(url);self.index.append({'origin':u.scheme+'://'+u.netloc,'path':u.path,'file':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
base=p.read_baseline(W);c=json.loads((D/'CENSUS.json').read_text());ret={(r['run_id'],r['run_attempt']) for r in base['reconciled_legacy_operations']};api=Retained(subprocess.check_output(['gh','auth','token'],text=True).strip());out=[]
for r in c['records']:
 if (r['run_id'],r['run_attempt']) in ret or r['publisher_never_started']:continue
 try:out.append({'run_id':r['run_id'],'classification':p.classify_legacy_never_published(api,r,base)})
 except p.Refused as e:
  out.append({'run_id':r['run_id'],'refused':str(e)})
  if str(e) in ('github_evidence_read_refused','bounded_preflight_budget_exhausted'):break
result={'schema':'defense.readonly_legacy_classification.v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Existing classifier on authenticated original records; no Actions identity, checkpoint, retirement, dispatch, cancellation or publication','results':out,'requests':api.index};(R/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(out,indent=2))
