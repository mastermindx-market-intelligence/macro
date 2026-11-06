import pathlib,subprocess,json,hashlib,os,sys,re,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832";B="92c51f1ff800b36fc63e7869243945996ac7315c"
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(W),*a])
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
receipt=E/"macro-e2d-42c-theme-chat-resolution.json";assert not receipt.exists()
p="templates/chat.html";b=git("show",B+":"+p);h=git("show",H+":"+p);m=git("show",M+":"+p)
def norm(x):
 matches=re.findall(rb"theme[.]js[?]v=[0-9a-f]{8}",x)
 assert len(matches)==1,matches
 return re.sub(rb"theme[.]js[?]v=[0-9a-f]{8}",b"theme.js?v=STAMP",x)
# The sole incoming source change is its generated theme stamp.
assert norm(b)==norm(m)
assert git("hash-object","lib/site_assets.py").decode().strip()=="03d7ce6137a30b990435cb1fee2090e61c2e95e3"
os.chdir(W);sys.path.insert(0,str(W))
from lib.site_assets import emit_theme_js,MM_BRAIN_VER_TOKEN,SUPABASE_TOKEN
from scripts.optimize_assets import make_optimizer
from lib.shared_shell import inject_shared_shell_text
from lib.pages import dbase_prefix
sources=["templates/theme.js","templates/mm_brain.js","templates/terminal_overlay.js","templates/shared_shell_bridge.js","templates/shared_shell.css","lib/site_assets.py","scripts/optimize_assets.py"]
inputs={x:hashlib.sha256((W/x).read_bytes()).hexdigest() for x in sources}
theme=emit_theme_js(W/"templates/theme.js")
assert MM_BRAIN_VER_TOKEN not in theme and SUPABASE_TOKEN not in theme
assert inputs["templates/mm_brain.js"][:8] in theme
assert (W/"templates/mm_brain.js").read_bytes()==(W/"site/mm_brain.js").read_bytes()
(W/"site/theme.js").write_text(theme)
optimized=make_optimizer(W/"site")
chat=inject_shared_shell_text(h.decode(),dbase_prefix(W/"site/chat.html"),site_dir=W/"site")
chat=optimized(chat,(W/"site").resolve())
assert "<<<<<<<" not in chat and "=======" not in chat
(W/p).write_text(chat);(W/"site/chat.html").write_text(chat)
paths=["site/theme.js","templates/chat.html","site/chat.html"]
subprocess.run(["git","--no-optional-locks","-C",str(W),"add","--",*paths],check=True)
r=subprocess.run(["git","--no-optional-locks","-C",str(W),"diff","--cached","--check","--",*paths],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
data={"prior_guard_only_attempt":{"pid":89573,"exit":1,"effect":"none; assertion before all writes","reason":"over-escaped comparison regex corrected to character classes"},"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":H,"incoming":M,"base":B,"source_inputs":inputs,"theme_emitter":"lib.site_assets.emit_theme_js","chat_owner":"H source plus existing inject_shared_shell_text and make_optimizer; exact incoming-only theme-stamp delta verified","new_files":{x:{"bytes":(W/x).stat().st_size,"sha256":hashlib.sha256((W/x).read_bytes()).hexdigest()} for x in paths},"mm_brain_template_site_equal":True,"chat_pair_equal":True,"focused_diff_check_exit":r.returncode}
raw=(json.dumps(data,indent=2)+"\n").encode();receipt.write_bytes(raw);print(json.dumps(data,indent=2));print(json.dumps({"receipt":str(receipt),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}))