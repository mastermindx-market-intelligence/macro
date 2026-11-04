"""Compare exact country and asset bytes between the approved and composed builds."""
import datetime,hashlib,html.parser,json,pathlib
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
E=R/"research/reference_integrity/intl-country-intelligence-20261020"
C=E/"main_reconciliation_20261022"
old=E/"proposed_dock4_repair"; new=E/"proposed_main25020261022_repair"
def sha(b): return hashlib.sha256(b).hexdigest()
class CountryParser(html.parser.HTMLParser):
 def __init__(self,text):
  super().__init__(convert_charrefs=False); self.text=text; self.lines=[0]; self.stack=[]; self.countries={}; self.scripts=[]
  for line in text.splitlines(keepends=True): self.lines.append(self.lines[-1]+len(line))
 def pos(self):
  line,col=self.getpos(); return self.lines[line-1]+col
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=="script" and attrs.get("src"): self.scripts.append(attrs["src"])
  if tag=="details":
   ident=attrs.get("id",""); self.stack.append((ident,self.pos()) if ident.startswith("imc-country-") else None)
 def handle_endtag(self,tag):
  if tag=="details":
   entry=self.stack.pop()
   if entry:
    ident,start=entry; end=self.text.index(">",self.pos())+1
    self.countries[ident]=self.text[start:end].encode()
def parse(p):
 text=p.read_text(); x=CountryParser(text); x.feed(text); x.close(); return x
accepted=old/"intl.html"; candidate=new/"intl.html"
assert sha(accepted.read_bytes())=="ad802caa6a04a7049d0adf8721354c88aa7dfec7378d5afc6bf161064f9767d0"
a=parse(accepted); b=parse(candidate)
assert set(a.countries)==set(b.countries)=={"imc-country-"+c for c in ["JP","KR","TW","IN","AU","GB","EZ"]}
rows=[{"id":k,"accepted_sha256":sha(a.countries[k]),"candidate_sha256":sha(b.countries[k]),"identical":a.countries[k]==b.countries[k]} for k in sorted(a.countries)]
assets=[]
for p in sorted(new.rglob("*")):
 if not p.is_file() or p.name=="intl.html": continue
 rel=p.relative_to(new); prior=old/rel
 assets.append({"path":str(rel),"candidate_sha256":sha(p.read_bytes()),"accepted_sha256":sha(prior.read_bytes()) if prior.is_file() else None,"identical":prior.is_file() and prior.read_bytes()==p.read_bytes()})
receipt={"schema":"intl.main_composition_country_equivalence.v1","recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"approved_artifact_commit":"883a1e48efdf9c334c08665262efa0961b1997a0","composed_source_commit":"c2b0562234abbec883ea91b934ac3d09fa3bae8b","accepted_html_sha256":sha(accepted.read_bytes()),"candidate_html_sha256":sha(candidate.read_bytes()),"countries":rows,"assets":assets,"composed_script_src":b.scripts,"new_source_acquisition":False,"production_acceptance":False,"pass":all(r["identical"] for r in rows)}
(C/"country_equivalence.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"pass":receipt["pass"],"countries":rows,"changed_assets":[r for r in assets if not r["identical"]],"script_src":b.scripts},indent=2),flush=True)
raise SystemExit(0 if receipt["pass"] else 1)
