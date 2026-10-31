from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,sys
W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main')
D=Path(__file__).resolve().parent/'publisher-census-20261014';D.mkdir(exist_ok=True)
sys.path.insert(0,str(W/'scripts/ci'));import govrev_publisher_preflight as p
class RetainedRead(p.GitHub):
    def __init__(self, token):super().__init__(token);self.index=[]
    def json(self,path):
        value=super().json(path);body=json.dumps(value,sort_keys=True,separators=(',',':')).encode();name=f'{len(self.index):03d}.json.gz';(D/name).write_bytes(gzip.compress(body,mtime=0));self.index.append({'path':path,'file':name,'body_sha256':hashlib.sha256(body).hexdigest()});return value
b=p.read_baseline(W)
token=subprocess.check_output(['gh','auth','token'],text=True).strip()
api=RetainedRead(token);del token
result={'schema':'defense.readonly_publisher_census.v1','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_source_qualified':True,'scan_created_after':b['scan_created_after'],'mode':'read-only inventory, no synthetic Actions identity, no preflight checkpoint, no publication or dispatch'}
try:
 records,pending=p.qualified_records(api,b['scan_created_after'],(None,None));result.update(conclusion='inventory_complete',records=records,pending_created_at=pending)
except p.Refused as e:result.update(conclusion='refused',reason=str(e))
finally:
 result['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();result['requests']=api.index
 (D/'CENSUS.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['records','requests']},indent=2));print('requests',len(api.index),'records',len(result.get('records',[])))
