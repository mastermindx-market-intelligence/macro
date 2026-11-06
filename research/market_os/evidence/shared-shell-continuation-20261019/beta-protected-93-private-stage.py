from pathlib import Path
import os,sys,json,hashlib,stat,tempfile,datetime,subprocess
R="93e303cc32566e72fb086af6d04ba3aa41866c5c";A="e45bde2cac07ac3b29285ff70c40d68900fad62c"
assert os.geteuid()==0
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def value(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,(args,p.returncode,p.stderr);return p.stdout.strip()
assert value(["systemctl","show","terminal.service","--property=MainPID","--value"])=="2336355"
assert value(["systemctl","show","terminal-beta.service","--property=ActiveState,UnitFileState,MainPID"])=="MainPID=0\nActiveState=inactive\nUnitFileState=disabled"
assert Path("/opt/terminal/terminal/.deployment-id").read_text().strip()=="50a8c01553ee92731a53dfcff36256308cfb5f0e"
assert digest("/etc/caddy/Caddyfile")=="6de6d01adbe40a5c71f8d80472f3d0deca5a02a99c4e27779984b3bff4d274b1"
assert digest("/opt/terminal/terminal-build.sh")=="6d05d3d5745e0e0a29262c89ba61cf881c2605201cce5b0fc85a52bde0e42ec8"
for p in ["/opt/terminal/.terminal-build-resource.lock/hold","/opt/terminal/beta/.runtime-accepted","/opt/terminal/beta/.release-pending"]:assert not os.path.lexists(p),p
buf=sys.stdin.buffer.read(207243);assert len(buf)==207242 and hashlib.sha256(buf).hexdigest()=="c6759cc653e0f19102a015ec52842795bde24eb85766d2e73f3024b4eefe409d"
os.umask(0o077);directory=Path(tempfile.mkdtemp(prefix="mastermind-beta-owner-93e303cc-",dir="/root"));path=directory/"terminal-build.sh"
print(json.dumps({"phase":"private_directory_created","directory":str(directory),"owner_R":R,"bootstrap_executed":False}),flush=True)
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o700)
with os.fdopen(fd,"wb") as f:f.write(buf);f.flush();os.fsync(f.fileno())
dfd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);os.fsync(dfd);os.close(dfd)
assert sorted(p.name for p in directory.iterdir())==["terminal-build.sh"] and digest(path)==hashlib.sha256(buf).hexdigest()
for p in [directory,path]:
 s=p.lstat();assert s.st_uid==0 and s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o700
s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size==207242
print(json.dumps({"phase":"private_protected_owner_staged","staged_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"owner_R":R,"application_A":A,"directory":str(directory),"script":str(path),"sha256":digest(path),"bytes":s.st_size,"uid":s.st_uid,"gid":s.st_gid,"nlink":s.st_nlink,"mode":"0700","directory_entries":["terminal-build.sh"],"bootstrap_executed":False}),flush=True)
