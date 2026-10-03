"""Re-render only the canonical risk partial, button hint, stylesheet and asset key.
This uses the already-published exact settled bundle, not a full site/data rebuild.
"""
from pathlib import Path
from html.parser import HTMLParser
from jinja2 import Environment,FileSystemLoader
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parents[3]; evidence=Path(__file__).resolve().parent
base=subprocess.check_output(['git','show','HEAD:site/macro.html'],cwd=root).decode()
html=base
lines=html.splitlines(keepends=True); offsets=[0]
for ln in lines: offsets.append(offsets[-1]+len(ln))
class Ranges(HTMLParser):
 def __init__(self): super().__init__(convert_charrefs=False); self.stack=[]; self.matches=[]
 def pos(self): r,c=self.getpos(); return offsets[r-1]+c
 def handle_starttag(self,tag,attrs):
  if tag in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}: return
  self.stack.append((tag,dict(attrs),self.pos()))
 def handle_startendtag(self,tag,attrs): pass
 def handle_endtag(self,tag):
  for n in range(len(self.stack)-1,-1,-1):
   if self.stack[n][0]==tag:
    entries=self.stack[n:]; self.stack=self.stack[:n]
    for t,a,start in entries:
     if a.get('id') in {'risk-envelope-band','mx5BtnRisk'} or (t=='section' and 'riskdlg-brief' in a.get('class','').split()) or a.get('id')=='risk-envelope-band-css':
      self.matches.append((t,a,start,self.pos()+len('</'+tag+'>')))
    return
r=Ranges();r.feed(html)
def one(key):
 values=[x for x in r.matches if x[1].get('id')==key]
 assert len(values)==1,(key,len(values))
 return values[0]
band=one('risk-envelope-band');button=one('mx5BtnRisk');style=one('risk-envelope-band-css')
assert band[1]['class']=='riskdlg-context'
assert 'gde-button-context' not in html[button[2]:button[3]], 'Refuse a second hint'
data=json.loads((root/'site/riskdata/risk_envelope.json').read_text())
assert band[1]['data-bundle-id']==data['bundle_id'] and band[1]['data-settled-session']==data['source_session']
env=Environment(loader=FileSystemLoader(root/'templates'),autoescape=True)
template=env.get_template('_risk_envelope_band.html.j2')
clean=lambda value:'\n'.join(ln.rstrip() for ln in str(value).splitlines()).strip()
fragment=clean(template.render(risk_envelope=data))
hint=clean(template.make_module({'risk_envelope':None}).risk_button_context(data))
css=clean(env.get_template('_risk_envelope_band.css.j2').render())
edits=[(band[2],band[3],fragment),(style[2],style[3],'<style id="risk-envelope-band-css">\n'+css+'\n</style>'),(button[3]-9,button[3]-9,hint)]
for start,end,replacement in sorted(edits,reverse=True):html=html[:start]+replacement+html[end:]
asset=hashlib.sha256((root/'site/risk_envelope_live.js').read_bytes()).hexdigest()
html,n=re.subn(r'(src="risk_envelope_live\.js)(?:\?v=[^"\s]+)?',r'\1?v='+asset[:8],html);assert n==1
assert html.count('id="risk-envelope-band"')==1 and html.count('id="gde-button-context"')==1
assert html.index('id="dlg-risk"')<html.index('id="risk-envelope-band"')
(root/'site/macro.html').write_text(html)
receipt={'kind':'bounded_canonical_partial_render','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'source_bundle':data['bundle_id'],'source_session':data['source_session'],'before_sha256':hashlib.sha256(base.encode()).hexdigest(),'after_sha256':hashlib.sha256(html.encode()).hexdigest(),'asset_sha256':asset,'rendered_templates':['_risk_envelope_band.html.j2','_risk_envelope_band.css.j2'],'preserved':'Every byte outside existing risk section, scoped CSS, risk-button hint insertion and script content key.','full_builder':'Not rerun: same known untracked-store limitation; no collectors or market data writes.'}
(evidence/'render-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
