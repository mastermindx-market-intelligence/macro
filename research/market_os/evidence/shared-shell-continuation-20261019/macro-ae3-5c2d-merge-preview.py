import pathlib,subprocess,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");g=["git","--no-optional-locks","-C",str(W)]
H="ae3e6bc547361b632223e7e9bde73128b399035e";N="5c2d0a04afd19642d2dab483885d46c73b7baed4";p=E/"macro-ae3-5c2d-merge-preview.json";assert not p.exists()
def git(*a):return subprocess.check_output(g+list(a))
assert git("rev-parse","HEAD").decode().strip()==H and not git("status","--porcelain=v1","--untracked-files=no").strip()
r={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":H,"incoming":N,"merge_base":git("merge-base",H,N).decode().strip(),"incoming_paths":git("diff","--name-only","42c859546ececa797b400db0adeb8c5a22f96832",N).decode().splitlines()}
x=subprocess.run(g+["merge-tree","--write-tree","--name-only",H,N],capture_output=True)
r.update({"exit":x.returncode,"stdout":x.stdout.decode(errors="replace"),"stderr":x.stderr.decode(errors="replace"),"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat()});p.write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps({**r,"receipt_sha256":hashlib.sha256(p.read_bytes()).hexdigest()}),flush=True)
