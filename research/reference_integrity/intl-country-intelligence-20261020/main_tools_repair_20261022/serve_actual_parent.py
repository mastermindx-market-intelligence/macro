"""Run only the owned local supported-parent proof servers; no production effects."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,signal,socket,subprocess,sys,time
PARENT=pathlib.Path("/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/intl-parent-proof-20261022")
EXPECTED_PARENT="e45bde2cac07ac3b29285ff70c40d68900fad62c"
ROOT=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
EVIDENCE=pathlib.Path(__file__).resolve().parent
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args):return subprocess.check_output(["git","-C",str(PARENT),*args],text=True).strip()
parser=argparse.ArgumentParser()
parser.add_argument("--artifact",required=True)
parser.add_argument("--output",required=True)
parser.add_argument("--maximum-seconds",type=int,default=2400)
a=parser.parse_args()
artifact=pathlib.Path(a.artifact).resolve()
output=pathlib.Path(a.output).resolve()
assert artifact.is_relative_to(ROOT/"research/reference_integrity/intl-country-intelligence-20261020")
assert output.is_relative_to(EVIDENCE)
assert (artifact/"intl.html").is_file()
assert git("rev-parse","HEAD")==EXPECTED_PARENT
assert not git("status","--porcelain","--untracked-files=no")
assert not (output/"runtime.json").exists(),"Reconcile existing server record before another launch"
for port in (3100,3102):
    with socket.socket() as sock:sock.bind(("127.0.0.1",port))
output.mkdir(parents=True,exist_ok=True)
fixture={"NODE_ENV":"development","MMX_SHARED_SHELL":"1",
 "MMX_SHARED_SHELL_LEGACY_ORIGIN":"http://127.0.0.1:3102",
 "TERMINAL_E2E_FIXTURE":"1","TERMINAL_E2E_EMAIL":"responsive@example.com",
 "TERMINAL_E2E_ENTITLEMENT":"unlimited","FLOW_FIXTURE":"1",
 "NEXT_PUBLIC_SUPABASE_URL":"http://127.0.0.1:54321",
 "NEXT_PUBLIC_SUPABASE_ANON_KEY":"fixture-anon-key",
 "NEXT_TELEMETRY_DISABLED":"1","RATE_LIMIT_MAX":"100000"}
env=dict(os.environ);env.update(fixture)
commands={"child":[sys.executable,"-m","http.server","3102","--bind","127.0.0.1","--directory",str(artifact)],
 "parent":[shutil.which("node"),str(PARENT/"terminal/node_modules/next/dist/bin/next"),"dev","--hostname","127.0.0.1","--port","3100"]}
record={"schema":"intl.actual_parent_runtime.v2","started_at":now(),"supervisor_pid":os.getpid(),
 "parent_source":EXPECTED_PARENT,"parent_tracked_source_clean":True,
 "macro_head_at_start":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),
 "artifact":str(artifact),"html_sha256":hashlib.sha256((artifact/"intl.html").read_bytes()).hexdigest(),
 "controller_delivery":"inlined in intl.html; whole-document response hash binds the controller",
 "fixture_env":fixture,"commands":commands,"processes":{},"maximum_runtime_seconds":a.maximum_seconds,
 "boundary":"owned local development guest fixture; actual unmodified supported parent"}
processes={};logs={};stopping=False
def stop(signum,frame):
    global stopping
    stopping=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
try:
    for name,command in commands.items():
        logs[name]=(output/(name+".log")).open("wb")
        processes[name]=subprocess.Popen(command,cwd=PARENT/"terminal" if name=="parent" else artifact,
            env=env,stdout=logs[name],stderr=subprocess.STDOUT,start_new_session=True)
        record["processes"][name]=processes[name].pid
    (output/"runtime.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({"state":"SERVERS_LAUNCHED","supervisor_pid":os.getpid(),"processes":record["processes"],"output":str(output)}),flush=True)
    deadline=time.monotonic()+a.maximum_seconds
    while not stopping and time.monotonic()<deadline and all(p.poll() is None for p in processes.values()):time.sleep(1)
finally:
    for p in processes.values():
        if p.poll() is None:
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    for p in processes.values():
        try:p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=8)
    for log in logs.values():log.close()
    closed={"stopped_at":now(),"processes":{n:{"pid":p.pid,"exit_code":p.returncode} for n,p in processes.items()},
      "parent_tracked_source_clean":not git("status","--porcelain","--untracked-files=no")}
    (output/"shutdown.json").write_text(json.dumps(closed,indent=2)+"\n")
    print(json.dumps(closed),flush=True)
