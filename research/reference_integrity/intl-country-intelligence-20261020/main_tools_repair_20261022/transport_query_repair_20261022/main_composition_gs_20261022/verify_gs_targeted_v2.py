from pathlib import Path
import subprocess,os,json,hashlib,time,datetime
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");T=Path("/tmp/intl-resume-main-20261022T1252");G=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_gs_20261022")
test=R/'tests/intl_workspace_controller.test.cjs';s=test.read_text()
assert s.count('pins=JP%2cKR')==3
s=s.replace('pins=JP%2cKR','pins=%4aP,KR')
old="assert.equal(before.issues, 'Invalid URL state restored', business);";assert s.count(old)==1
s=s.replace(old,"assert.equal(before.issues, business === 'view=unknown&market=JP' ? 'Unsupported value' : 'Invalid URL state restored', business);")
old="'view=overview&market=TW&', 'market=JP&view=%zz'];";assert old in s
s=s.replace(old,"'view=overview&market=TW&', 'market=JP&view=%zz', 'market=TW&pins=JP%2cKR'];")
test.write_text(s)
env=dict(os.environ);env['NODE_PATH']='/tmp/intl-browser-node-20261021/node_modules';env['PLAYWRIGHT_CHROMIUM_CHANNEL']='chrome';env['PATH']='/tmp/intl-country-cockpit-ci-20261021/bin:/opt/homebrew/bin:'+env['PATH'];env['PYTHONDONTWRITEBYTECODE']='1'
preload=T/'gs_mechanical_preload.cjs'
preload.write_text("const fs=require('node:fs'),path=require('node:path');const read=fs.readFileSync;fs.readFileSync=function(file,options){if(typeof file==='string'&&path.resolve(file)==="+json.dumps(str(R/'templates/intl_workspace.js'))+")return read.call(this,"+json.dumps(str(T/'gs_mechanical_workspace.js'))+",options);return read.apply(this,arguments);};\n")
sha=lambda b:hashlib.sha256(b).hexdigest()
receipts=[]
for name,pattern,negative in [('gs_query_targeted_v2','^GS query composition:',False),('gs_mechanical_negative','^GS query composition: (transport|rejected)',True)]:
 command=['/opt/homebrew/bin/node']
 if negative:command+=['--require',str(preload)]
 command+=['--test','--test-reporter=tap','--test-name-pattern='+pattern,'tests/intl_workspace_controller.test.cjs']
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 with (G/(name+'.log')).open('w') as log:r=subprocess.run(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
 record={'name':name,'command':command,'exit_code':r.returncode,'expected_negative':negative,'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-tick,2),'log_sha256':sha((G/(name+'.log')).read_bytes()),'candidate_source_sha256':sha((R/'templates/intl_workspace.js').read_bytes()),'mechanical_source_sha256':sha((T/'gs_mechanical_workspace.js').read_bytes()),'test_sha256':sha(test.read_bytes())}
 receipts.append(record);print(json.dumps(record),flush=True);print((G/(name+'.log')).read_text()[-6500:],flush=True)
 if (not negative and r.returncode!=0) or (negative and r.returncode==0):break
(G/'gs_targeted_and_negative_receipt.json').write_text(json.dumps({'checks':receipts},indent=2)+'\n')
assert len(receipts)==2 and receipts[0]['exit_code']==0 and receipts[1]['exit_code']!=0
