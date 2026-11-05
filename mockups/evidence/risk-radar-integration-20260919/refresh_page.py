"""Bounded artifact refresh: render the owned Jinja partial from its exact page bundle.
Other page content is preserved byte-for-byte. This is not a full site rebuild.
"""
from pathlib import Path
from html.parser import HTMLParser
from jinja2 import Environment, FileSystemLoader
import hashlib, json, re
root=Path.cwd(); p=root/'site/macro.html'; html=p.read_text()
evidence=Path('/Volumes/Mastermind/agent-evidence/risk-radar-integration-20260919')
if not (evidence/'macro-before.html').exists(): (evidence/'macro-before.html').write_text(html)
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
     if a.get('id')=='risk-envelope-band' or (t=='section' and 'riskdlg-brief' in a.get('class','').split()) or a.get('id')=='risk-envelope-band-css':
      self.matches.append((t,a,start,self.pos()+len('</'+tag+'>')))
    return
r=Ranges(); r.feed(html)
bands=[x for x in r.matches if x[1].get('id')=='risk-envelope-band']
briefs=[x for x in r.matches if 'riskdlg-brief' in x[1].get('class','').split()]
assert len(bands)==len(briefs)==1, (len(bands),len(briefs))
band=bands[0]; brief=briefs[0]
assert band[1].get('class')=='panel span12 gde-band', 'Refuse repeated or unexpected artifact refresh'
data=json.loads((root/'site/riskdata/risk_envelope.json').read_text())
assert band[1]['data-bundle-id']==data['bundle_id'], 'Refuse source/page bundle mismatch'
assert band[1]['data-settled-session']==data['source_session']
env=Environment(loader=FileSystemLoader(root/'templates'), autoescape=True)
fragment=env.get_template('_risk_envelope_band.html.j2').render(risk_envelope=data)
css=env.get_template('_risk_envelope_band.css.j2').render()
edits=[(band[2],band[3],''),(brief[3],brief[3],'\n'+fragment+'\n')]
styles=[x for x in r.matches if x[1].get('id')=='risk-envelope-band-css']
style='<style id="risk-envelope-band-css">\n'+css+'\n</style>\n'
if styles: edits.append((styles[0][2],styles[0][3],style))
else:
 head=html.index('</head>'); edits.append((head,head,style))
for start,end,new in sorted(edits,reverse=True): html=html[:start]+new+html[end:]
# Fresh script reference, so the compatibility fix is not trapped in an old cache.
hashjs=hashlib.sha256((root/'site/risk_envelope_live.js').read_bytes()).hexdigest()[:8]
html,n=re.subn(r'(src="risk_envelope_live\.js)(?:\?v=[^"\s]+)?',r'\1?v='+hashjs,html)
assert n==1
assert html.count('id="risk-envelope-band"')==1
assert html.index('id="risk-envelope-band"')>html.index('id="dlg-risk"')
p.write_text(html)
receipt={'kind':'bounded_canonical_partial_render','source_bundle':data['bundle_id'],'source_session':data['source_session'],'before_sha256':hashlib.sha256((evidence/'macro-before.html').read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rendered_templates':['_risk_envelope_band.html.j2','_risk_envelope_band.css.j2'],'preserved':'All bytes outside old band, new insertion, scoped CSS and script cache key','full_builder':'refused: untracked Yahoo store absent; no collectors run'}
(evidence/'partial-render-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
