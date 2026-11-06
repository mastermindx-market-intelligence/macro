import sys,json,re,hashlib,subprocess
from pathlib import Path
from jinja2 import Environment,StrictUndefined,FileSystemLoader
repo=Path(sys.argv[1]);phase=sys.argv[2];sys.path.insert(0,str(repo))
from scripts.build_bonds import C
out=Path(__file__).parent;dest=out/("render-"+phase);dest.mkdir(exist_ok=True)
head="ed9fb81da853429ce87495d6c012467ebf057548"
src=subprocess.check_output(["git","show",head+":templates/bonds.html.j2"],cwd=repo,text=True) if phase=="before" else (repo/"templates/bonds.html.j2").read_text()
snapshot_file=sys.argv[3] if len(sys.argv)>3 else ("native-intl-snapshot-before.json" if phase=="before" else "native-intl-snapshot-after.json")
intl=json.loads((out/snapshot_file).read_text())
macros=src[:src.index("<!DOCTYPE html>")]
css=re.search(r"<style>(.*?)</style>",src,re.S).group(1)
entry=src[src.index('  <section class="band" id="deeper"'):src.index("  <!-- ===================== LANDINGS")]
start=src.index('  <section class="landing" id="global-detail"')
stop=src.index("  <div class=\"card\">\n    <h2>{{ t('Euro-area",start)
body=src[start:stop]+"</section>"
env=Environment(loader=FileSystemLoader(str(repo/"templates")),undefined=StrictUndefined,autoescape=True)
css=env.from_string(css).render(C=C)
partials={}
for partial in ["_interfonts.html.j2","_state_inks.html.j2","_vector_polish.html.j2"]:
 rendered=env.get_template(partial).render(C=C)
 partials[partial]="\n".join(re.findall(r"<style[^>]*>(.*?)</style>",rendered,re.S))
css=partials["_interfonts.html.j2"]+"\n"+(repo/"templates/illus.css").read_text()+"\n"+css+"\n"+partials["_state_inks.html.j2"]+"\n"+partials["_vector_polish.html.j2"]
content=env.from_string(macros+entry+body).render(C=C,intl=intl,charts={"intl_yields":""})
for width,height in [(1440,900),(390,844)]:
 for theme in ["dark","light"]:
  for lang in ["en","zh"]:
   html=f'<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style></head><body><main class="wrap">{content}</main></body></html>'
   (dest/f"{width}-{theme}-{lang}.html").write_text(html)
record={"phase":phase,"source":head if phase=="before" else "isolated candidate working source","template_sha256":hashlib.sha256(src.encode()).hexdigest(),"snapshot_sha256":hashlib.sha256(json.dumps(intl,sort_keys=True).encode()).hexdigest(),"included_shared_styles":{p:hashlib.sha256((repo/"templates"/p).read_bytes()).hexdigest() for p in ["_interfonts.html.j2","_state_inks.html.j2","_vector_polish.html.j2","illus.css"]},"scope":"Actual native intl_bonds snapshot, authored #deeper/#global-detail fragments plus page/shared CSS and retained Inter fonts; no full shell, chart, auth, public source response or served publication proof"}
(dest/"source-identity.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record))
