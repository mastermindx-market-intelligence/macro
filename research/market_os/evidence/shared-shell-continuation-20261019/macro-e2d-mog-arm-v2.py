import datetime,hashlib,json,pathlib,subprocess,sys
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27')
E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
H='e2d10f933587f58be8716505529a37f8839901f7'
A='e45bde2cac07ac3b29285ff70c40d68900fad62c'
BR='sol/market-os-shared-shell-design-20260924'
receipt=E/'macro-e2d-mog-arm-v2.json'
r={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'branch':BR,'owner':'existing merge-on-green workflow/controller','operation':'add existing merge-on-green label only','label_write_attempted':False,'source_mutation':False,'production_mutation':False,'reads':[]}
with receipt.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
def save():
 receipt.write_text(json.dumps(r,indent=2)+'\n')
def run(a,timeout=30):
 p=subprocess.run(a,cwd=W,capture_output=True,text=True,timeout=timeout)
 v={'argv':a,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 r['reads'].append(v);save()
 assert p.returncode==0,v
 return p.stdout
try:
 assert run(['git','--no-optional-locks','rev-parse','HEAD']).strip()==H
 assert run(['git','--no-optional-locks','branch','--show-current']).strip()==BR
 assert run(['git','--no-optional-locks','status','--porcelain=v1'])==''
 assert run(['git','hash-object','scripts/merge_on_green.py']).strip()=='62cc138e9d4e99b6bf28ec58265df2438bee3c96'
 sys.path.insert(0,str(W))
 from scripts import merge_on_green as mog
 assert run(['git','ls-remote','origin','refs/heads/'+BR]).split()[0]==H
 preview=json.loads((E/'macro-e2d-prearm-1f44-preview.json').read_text())
 weights=json.loads((E/'macro-e2d-prearm-1f44-weight-compatibility.json').read_text())
 assert preview['head']==H and preview['preview']['exit']==0
 assert weights['head']==H and weights['all_job_weight_differences']==[]
 r['incoming_preview']={'main':preview['main'],'tree':preview['preview']['stdout'].strip(),'all_job_weight_differences':[],'fresh_selection_run':False}
 remote=(E/'macro-beta-before-e2d-publication-20261020T0536-remote.py').read_bytes()
 assert hashlib.sha256(remote).hexdigest()=='c53b62c77cc27142fc31f20e771a50428be6311af72249eec6140e5a068e78c0'
 p=subprocess.run(['ssh','-i','/Users/chriswong/.ssh/macro_dashboard_deploy_v2','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=yes','root@146.190.142.17','python3 -'],input=remote,capture_output=True,timeout=60)
 for suffix,raw in [('.stdout.json',p.stdout),('.stderr',p.stderr)]:
  with (E/('macro-e2d-arm-v2-health'+suffix)).open('xb') as f:f.write(raw)
 r['health']={'ssh_exit':p.returncode,'stdout_bytes':len(p.stdout),'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_bytes':len(p.stderr)}
 save();assert p.returncode==0 and not p.stderr
 j=json.loads(p.stdout)
 assert j['beta_source_HEAD']['stdout'].strip()==A
 assert j['runtime_pointer']['sha256']=='698204ef4ad72a1bfa896110af875df080bf773687150890e8a2322bd6b452d7'
 assert j['source_pointer']['sha256']=='9aac8ec8c132eecf4d2664d8f1e18e8a6bffce5f6d7176e4021b15d6d953cfa4'
 props=dict(x.split('=',1) for x in j['services']['terminal-beta.service']['stdout'].splitlines())
 assert props['ActiveState']=='active' and props['SubState']=='running' and props['UnitFileState']=='enabled' and int(props['MainPID'])>0
 assert j['services']['terminal-beta.service']['stdout']==j['beta_after']['stdout']
 assert not j['pending_exists'] and not j['beta_stages']
 assert j['status']['status']==200 and j['status']['body']=={'enabled':True,'protocol':'mmx.shared-shell.v1','buildId':A,'bridgeVersion':'20261018.1','documentVersion':'20261018.1','registrySha256':'5307ea5a7964fde609a8f20f1af30b6bf483b7631f7232e5db74f9ef1d710023'}
 r['health'].update({'observed_at':j['observed_at'],'beta_service':props,'production_service':j['services']['terminal.service']['stdout'],'production_build':j['production_build'][0]['text'],'production_owner_sha256':j['production_owner']['sha256'],'caddy_sha256':j['caddy']['sha256'],'root_free':j['root_free'],'terminal_mount_free':j['terminal_mount_free'],'macro_head':j['macro']['head_after']['stdout'].strip()})
 pr=json.loads(run(['gh','pr','view','7949','--json','url,title,body,state,isDraft,headRefOid,baseRefName,labels,autoMergeRequest,statusCheckRollup']))
 assert pr['url']=='https://github.com/mastermindx-market-intelligence/macro/pull/7949'
 assert pr['state']=='OPEN' and not pr['isDraft'] and pr['headRefOid']==H and pr['baseRefName']=='main' and pr['autoMergeRequest'] is None
 assert not any(x['name']=='merge-on-green' for x in pr['labels'])
 checks=[]
 for page in range(1,6):
  payload=json.loads(run(['gh','api','repos/mastermindx-market-intelligence/macro/commits/'+H+'/check-runs?filter=latest&per_page=100&page='+str(page)]))
  batch=payload['check_runs'];checks.extend(batch)
  if len(batch)<100 or len(checks)>=payload['total_count']:break
 assert len(checks)>=payload['total_count']
 assert all(c['head_sha']==H for c in checks)
 r['owner_predicate']={'source_blob':'62cc138e9d4e99b6bf28ec58265df2438bee3c96','check_count':len(checks),'base_ref':pr['baseRefName'],'verdict':mog.decide_verdict(checks),'can_arm':mog.can_arm_merge_on_green(checks,base_ref=pr['baseRefName']),'nonbinding':[{'name':c['name'],'id':c['id'],'conclusion':c.get('conclusion')} for c in checks if mog.is_non_binding_check(c['name'],base_ref=pr['baseRefName'])]}
 save();assert r['owner_predicate']['can_arm']
 rollup_binding=mog.binding_status_checks(pr.get('statusCheckRollup') or [],base_ref=pr['baseRefName'])
 failures=[{'name':c.get('name',c.get('context','')),'status':c.get('status'),'conclusion':c.get('conclusion'),'state':c.get('state')} for c in rollup_binding if str(c.get('conclusion','')).upper() in ['FAILURE','CANCELLED','TIMED_OUT','ACTION_REQUIRED','STALE','STARTUP_FAILURE'] or str(c.get('state','')).upper() in ['ERROR','FAILURE']]
 r['blocking_checks']=failures;save();assert not failures
 assert any(c['name']=='ci-authority/main' and c['status']=='completed' and c['conclusion']=='success' for c in checks)
 assert any(c['name']=='ci-gate' and c['status']=='completed' and c['conclusion']=='success' for c in checks)
 pages=json.loads(run(['gh','api','--paginate','--slurp','repos/mastermindx-market-intelligence/macro/issues/7949/comments?per_page=100'],timeout=60))
 comments=[c for page in pages for c in page]
 r['hold_guard']={'comment_count':len(comments),'recorded_hold':mog.recorded_hold(pr['body'],comments,pr['title'])}
 save();assert r['hold_guard']['recorded_hold'] is None
 r['label_write_attempted']=True;r['label_write_started_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 p=subprocess.run(['gh','pr','edit','7949','--add-label','merge-on-green'],cwd=W,capture_output=True,text=True,timeout=45)
 r['label_write']={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat()};save()
 assert p.returncode==0
 after=json.loads(run(['gh','pr','view','7949','--json','url,state,headRefOid,labels,autoMergeRequest,mergedAt,mergeCommit']))
 r['after']=after
 assert after['headRefOid']==H and after['autoMergeRequest'] is None
 assert after['state']=='MERGED' or any(x['name']=='merge-on-green' for x in after['labels'])
 r['disposition']='MERGED_BY_EXISTING_OWNER' if after['state']=='MERGED' else 'EXISTING_MOG_ARMED_CONCLUDED_CI_PENDING_OWNER';r['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 print(json.dumps({k:v for k,v in r.items() if k!='reads'},indent=2),flush=True)
except BaseException as ex:
 r['error']=type(ex).__name__+': '+str(ex);r['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r['disposition']='LABEL_EFFECT_REQUIRES_RECONCILIATION' if r['label_write_attempted'] else 'PREFLIGHT_REFUSED_NO_LABEL_WRITE'
 save();print(json.dumps({k:v for k,v in r.items() if k!='reads'},indent=2),flush=True);raise
