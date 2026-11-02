import pathlib,subprocess,json,hashlib,datetime,os,sys
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
stem="macro-e2d-42c-p0b-actual";receipt=E/(stem+".json");fixtures=E/(stem+"-fixtures")
assert not receipt.exists() and not fixtures.exists()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p):b=p.read_bytes();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(W),*a])
H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832"
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
assert digest(W/"site/theme.js")["sha256"]=="c27f65318a3877e154e11f4f43fc7545e9fb67aa52cdd15cda2aaba9ebd21c29"
files=[W/"mockups/evidence/prophet-p0b-zero-fouc"/n for n in ["manifest.json","rendered-fixture.json","mobile-layout.json","mobile-layout-canada.json"]]
files+=sorted((W/"mockups/evidence/prophet-p0b-zero-fouc").glob("owner-empty-*.png"))
before={str(p.relative_to(W)):digest(p) for p in files}
freeze_paths=["scripts/render_stock_dashboard_fixture.py","scripts/verify_stock_dashboard_mobile_layout.cjs","lib/site_assets.py","lib/shared_shell.py","templates/hk.html.j2","templates/canada.html.j2","site/theme.js","site/mm_brain.js","site/shared_shell_bridge.js","site/shared_shell.css"]
frozen={p:digest(W/p) for p in freeze_paths}
assert frozen["scripts/verify_stock_dashboard_mobile_layout.cjs"]["sha256"]=="fa9c70ee76d8ccc370e09c4288da4b22905d2f64266d90e16046b3fa14a98774"
env=dict(os.environ);env["NODE_PATH"]="/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/investor-shell-native-20261008-c1/terminal/node_modules"
out={"started_at":now(),"head":H,"incoming":M,"scope":"existing Macro P0B synthetic rendered fixture only; no public browser/auth/production/Terminal859 qualification","node_path":env["NODE_PATH"],"source_before":frozen,"outputs_before":before,"commands":[]}
def save():receipt.write_text(json.dumps(out,indent=2)+"\n")
save()
commands=[("render",[str(W/".venv-shared-shell/bin/python"),"-B","scripts/render_stock_dashboard_fixture.py","--market","all","--out-dir",str(fixtures),"--receipt","mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json"])]
for market,html,name in [("hk","hk_stocks.html","mobile-layout.json"),("ca","canada_stocks.html","mobile-layout-canada.json")]:
 commands.append((market,["node","scripts/verify_stock_dashboard_mobile_layout.cjs","--html",str(fixtures/html),"--site-dir","site","--fixture-receipt","mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json","--fixture-assets-dir","mockups/evidence/prophet-p0b-zero-fouc/inputs/browser-data","--screenshot-dir","mockups/evidence/prophet-p0b-zero-fouc","--historical-head","3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86","--historical-tree","b4dd8fd9b29b4eb769239d35df2a7911e793c7ec","--out","mockups/evidence/prophet-p0b-zero-fouc/"+name]))
for name,args in commands:
 log=E/(stem+"-"+name+".stdout.log");err=E/(stem+"-"+name+".stderr.log");assert not log.exists() and not err.exists()
 row={"name":name,"args":args,"started_at":now(),"stdout":str(log),"stderr":str(err)};out["commands"].append(row);save();print(json.dumps({"started":name,"at":row["started_at"]}),flush=True)
 with log.open("xb") as f,err.open("xb") as e:r=subprocess.run(args,cwd=W,env=env,stdout=f,stderr=e)
 row.update({"finished_at":now(),"exit":r.returncode,"stdout_receipt":digest(log),"stderr_receipt":digest(err)})
 try:
  data=json.loads(log.read_text())
  if name=="render":row["markets"]={k:{"output_sha256":v["output_sha256"],"owner_cases":list(v["owner_cases"])} for k,v in data["markets"].items()}
  else:row["browser_result"]={"browser":data["browser"],"pass":data["pass"],"states":len(data["states"]),"projection_primary":data["owner_projection_matrix"]["primary_passed"],"projection_degraded":data["owner_projection_matrix"]["degraded_controls_passed"],"projection_screenshots":data["owner_projection_matrix"]["screenshot_count"],"loaded_assets":len(data["loaded_assets"])}
 except (ValueError,KeyError):row["stdout_json_summary"]="unavailable"
 save();print(json.dumps({"finished":name,"exit":r.returncode,"summary":row.get("browser_result",row.get("markets")),"stderr_tail":err.read_text(errors="replace")[-1600:]}),flush=True)
 if r.returncode!=0:
  out["finished_at"]=now();out["pass"]=False;out["stopped_at"]=name;save();print(json.dumps({"receipt":str(receipt),"pass":False}),flush=True);raise SystemExit(r.returncode)
out["source_after"]={p:digest(W/p) for p in freeze_paths};out["source_unchanged"]=out["source_after"]==frozen
out["outputs_after"]={str(p.relative_to(W)):digest(p) for p in files};out["finished_at"]=now();out["pass"]=out["source_unchanged"] and all(r["exit"]==0 for r in out["commands"]);save()
print(json.dumps({"receipt":str(receipt),**digest(receipt),"pass":out["pass"],"source_unchanged":out["source_unchanged"]}),flush=True)
raise SystemExit(0 if out["pass"] else 1)