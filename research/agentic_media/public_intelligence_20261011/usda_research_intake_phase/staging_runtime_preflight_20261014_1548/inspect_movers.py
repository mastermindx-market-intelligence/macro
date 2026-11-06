from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess,sys
root=Path(sys.argv[1]).resolve()
assert root==Path('/opt/macro')
sys.path.insert(0,str(root))
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
protected=True
reads={}
hashing=False
def audit(event,args):
 global hashing
 if not protected:return
 if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen','os.remove','os.rename','os.mkdir','os.rmdir','os.system'}:raise RuntimeError('read-only refused '+event)
 if event!='open':return
 name,mode,flags=args
 if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or flags&(64|512|1024):raise RuntimeError('read-only refused write')
 if hashing or not isinstance(name,(str,bytes)):return
 p=Path(name).resolve()
 if not p.is_relative_to(root) or not p.is_file():return
 rel=str(p.relative_to(root))
 if rel not in reads:
  hashing=True
  try:reads[rel]=sha256(p.read_bytes()).hexdigest()
  finally:hashing=False
sys.addaudithook(audit)
from engine.marketing import movers_source as m
from engine.press import desk_planner as p
now=datetime.now(timezone.utc)
d=m.load_movers(root)
picks=m.top_movers(d,tf='1D',n=8,min_abs=3)
facts=p.mover_facts(root,n=3,as_of=now.date())
artifacts={}
for rel in ['site/marketdata/sp500_heatmap.json','site/marketdata/themes_heatmap.json','data/marketing/hot_tape_pack.json']:
 x=json.loads((root/rel).read_bytes())
 artifacts[rel]={k:v for k,v in x.items() if k not in {'tickers','tiles','diagnostics'}}
 if 'tickers' in x:
  artifacts[rel]['selected_records']={i['ticker']:x['tickers'].get(i['ticker']) for side in picks.values() for i in side}
canonical={i['ticker']:{'source':(root/'site/stocks'/f"{i['ticker']}.html").is_file(),'served':(root/'site.served/stocks'/f"{i['ticker']}.html").is_file()} for side in picks.values() for i in side}
protected=False
head2=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
changed=[r for r,h in reads.items() if not(root/r).is_file() or sha256((root/r).read_bytes()).hexdigest()!=h]
assert not changed and head==head2
print(json.dumps({'observed_at':now.isoformat(),'head':head,'stable_head':head==head2,'top_movers':picks,'press_context_facts':facts,'artifacts':artifacts,'canonical':canonical,'input_sha256':reads,'changed_inputs':changed,'writes':0,'provider_calls':0},indent=2))
