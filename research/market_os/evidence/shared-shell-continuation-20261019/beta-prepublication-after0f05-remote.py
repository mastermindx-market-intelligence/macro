import datetime,hashlib,json,pathlib,subprocess,urllib.request,os
B=pathlib.Path('/opt/terminal/beta')
def command(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=25)
 return {'argv':a,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def file(p):
 p=pathlib.Path(p);raw=p.read_bytes();st=p.stat()
 return {'path':str(p),'resolved':str(p.resolve()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'uid':st.st_uid,'gid':st.st_gid,'mode':oct(st.st_mode & 0o777),'nlink':st.st_nlink}
def identity(p):
 x=file(p);x['text']=pathlib.Path(p).read_text().strip();return x
out={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'fresh read-only service, source, runtime pointer, public DNS/TLS observation; no bootstrap or repair'}
props='ActiveState,SubState,UnitFileState,MainPID,ExecMainStartTimestampMonotonic'
out['services']={n:command(['systemctl','show',n,'--property='+props]) for n in ['terminal.service','terminal-beta.service']}
out['beta_source_HEAD']=command(['git','--no-optional-locks','-C','/opt/terminal/.gitsrc-beta','rev-parse','HEAD'])
out['runtime_pointer']=file(B/'.runtime-accepted')
out['source_pointer']=file(B/'.source-provisioned')
out['beta_build']=[identity(B/'terminal'/n) for n in ['.deployment-id','.next/BUILD_ID']]
out['production_build']=[identity(pathlib.Path('/opt/terminal/terminal')/n) for n in ['.deployment-id','.next/BUILD_ID']]
out['production_owner']=file('/opt/terminal/terminal-build.sh')
out['caddy']=file('/etc/caddy/Caddyfile')
with urllib.request.urlopen('http://127.0.0.1:3001/api/shared-shell/status',timeout=15) as r:
 raw=r.read(65536);out['status']={'status':r.status,'headers':dict(r.headers),'raw_sha256':hashlib.sha256(raw).hexdigest(),'body':json.loads(raw)}
out['pending_exists']=os.path.lexists(B/'.release-pending')
out['beta_stages']=[str(x) for x in B.glob('.stage.*')]
out['root_free']=os.statvfs('/').f_bavail*os.statvfs('/').f_frsize
out['terminal_mount_free']=os.statvfs('/opt/terminal').f_bavail*os.statvfs('/opt/terminal').f_frsize
out['beta_after']=command(['systemctl','show','terminal-beta.service','--property='+props])
print(json.dumps(out,indent=2))
