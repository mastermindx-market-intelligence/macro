import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone,date,timedelta
from engine.press import desk_planner as P
r=Path('/opt/macro');cfg=P.load_config(r);dc=cfg['desks']['research_desk'];now=datetime.now(timezone.utc);asof=now.date();cat=r/'data/research_vault/catalog.json';before=cat.read_bytes();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip();c=json.loads(before);items=c['items'];held=set(['artifact:data/gex/latest.json', 'artifact:data/market_state/latest.json', 'artifact:data/risk_radar/forward_log.jsonl', 'artifact:site/basketdata/breadth_split.json', 'artifact:site/basketdata/fear_greed.json', 'official_feed:99354c7bd7561bf9356a1193875243a72ff1d000', 'official_feed:url:cd2747adeed2', 'research_vault:marketdesk-ergkmhwhsow-e05c9a', 'research_vault:marketdesk-8inwlunucuj-8950ab', 'research_vault:marketdesk-augnhdcr2jm-0cbff4', 'research_vault:marketdesk-qtq09kmuctq-baf3cc', 'research_vault:marketdesk-rc9hi0toy31-75d4dc', 'research_vault:marketdesk-xyyijkslpal-b997fb', 'research_vault:marketdesk-uc6giunqscq-05fcee', 'research_vault:marketdesk-dxcjj8lpx8k-75b4af'])
pub,_=P.published_refs(r,cfg);stage,_=P.staged_refs(r,cfg);held.update(pub);held.update(stage)
elig=[x for x in items if isinstance(x,dict) and x.get('summary_points') and P._as_date(x.get('published_at')) and asof-timedelta(days=int(dc['window_days']))<=P._as_date(x['published_at'])<=asof]
order,meta=P._triage_order(cfg,asof,r,elig);by={str(x.get('id')):x for x in elig};ranked=[by[k] for k in order if k in by];seen={x['id'] for x in ranked};ranked += [x for x in elig if x['id'] not in seen]
if not order: ranked.sort(key=lambda x:(0 if x.get('top_pick') else 1,-P._as_date(x['published_at']).toordinal(),x['id']))
rows=[]
for idx,x in enumerate(ranked[:24]):
 ref='research_vault:'+x['id'];rows.append({'rank_position':idx+1,'ref':ref,'blocked':ref in held,'title':x.get('title'),'published_at':x.get('published_at'),'institution':x.get('institution'),'url':'https://www.mastermind-x.com/research/'+P.vault_slug(x,items)+'.html','summary_points':x['summary_points'],'triage':{k:meta.get(x['id'],{}).get(k) for k in ['rank','w_score','veto']}})
slots=P.plan(['research_desk'],root=r,cfg=cfg,as_of=asof.isoformat(),extra_blocked_refs=held)
after=cat.read_bytes();afterhead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip();assert before==after and head==afterhead
print(json.dumps({'observed_at':now.isoformat(),'installed_head':head,'catalog_sha256':hashlib.sha256(before).hexdigest(),'catalog_generated_at':c.get('generated_at'),'eligible_count':len(elig),'candidate_pool':dc['candidate_pool'],'held_refs':sorted(held),'normal_slots':[x['id'] for x in slots],'ranked_rows':rows,'catalog_and_head_unchanged':True,'provider_calls':0,'runtime_writes':0},indent=2))
