import json,subprocess,datetime,pathlib,sys,re
release = sys.argv[1] if len(sys.argv) == 2 else ""
if not re.fullmatch(r"[0-9a-f]{40}",release):
 raise SystemExit("Pass the verified merged release commit as the sole argument")
from mmx_ancestry import load_proof
ancestry = load_proof(release)
expected=json.loads(pathlib.Path(__file__).with_name('mmx-current-expected-hashes.json').read_text())
payload = """import json,hashlib,pathlib,subprocess,re,datetime
root=pathlib.Path('/opt/macro')
files=__EXPECTED_SOURCE_FILES__
pages=['blog/index.html','learn/index.html','tools/calculators/position-size.html']
def fingerprint(p):
 if not p.is_file():return {'exists':False}
 b=p.read_bytes();return {'exists':True,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
data={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'source':{p:fingerprint(root/p) for p in files},'site':{p:fingerprint(root/'site'/p) for p in pages},'served':{p:fingerprint(root/'site.served'/p) for p in pages},'cutoverFalse':bool(re.search(r'^cutover: false$',(root/'config/press.yml').read_text(),re.M))}
data['headAfter']=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
data['stableHead']=data['head']==data['headAfter']
data['releaseCommit']='__RELEASE_SHA__'
data['containsRelease']=subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor','__RELEASE_SHA__','HEAD'],capture_output=True).returncode==0
print(json.dumps(data))
"""
payload=payload.replace('__RELEASE_SHA__',release).replace('__EXPECTED_SOURCE_FILES__',json.dumps(sorted(expected)))
cmd=['ssh','-i',str(pathlib.Path.home()/'.ssh/macro_dashboard_deploy_v2'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10','root@146.190.142.17','python3 -']
p=subprocess.run(cmd,input=payload,text=True,capture_output=True,timeout=45)
if p.returncode:raise SystemExit('SSH check failed: '+p.stderr[:1500])
data=json.loads(p.stdout);pages=json.loads(pathlib.Path(__file__).with_name('mmx-current-expected-pages.json').read_text())
data['sourceMatch']={f:v.get('sha256')==expected[f] for f,v in data['source'].items()}
data['siteMatch']={f:v.get('sha256')==pages[f]['sha256'] for f,v in data['site'].items()}
data['servedMatch']={f:v.get('sha256')==pages[f]['sha256'] for f,v in data['served'].items()}
data['containsReleaseByVerifiedObjectChain'] = data['stableHead'] and data['head'] == ancestry['head']
data['ancestryProof'] = {'head':ancestry['head'],'release':ancestry['release'],'verifiedCommitObjects':len(ancestry['chain'])}
data['accepted']=(data['containsRelease'] or data['containsReleaseByVerifiedObjectChain']) and data['stableHead'] and all(data['sourceMatch'].values()) and all(data['siteMatch'].values()) and all(data['servedMatch'].values()) and data['cutoverFalse']
path=pathlib.Path(__file__).with_name('mmx-current-install-observations.ndjson')
with path.open('a') as f:f.write(json.dumps(data)+'\n')
print(json.dumps(data,indent=2))
