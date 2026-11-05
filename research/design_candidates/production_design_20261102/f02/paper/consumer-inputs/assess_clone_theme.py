#!/usr/bin/env python3
"""Compare authored dark/light inputs; no Paper calls or native ID assumptions."""
from html.parser import HTMLParser
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, re

HERE=Path(__file__).resolve().parent
DARK_RESOLVED={
 'var(--noir-canvas)':'#080808','var(--noir-sidebar)':'#0c0c0c',
 'var(--noir-panel)':'#121212','var(--noir-raised)':'#191919',
 'var(--noir-selected)':'#292929','var(--noir-text-primary)':'#f3f3f3',
 'var(--noir-text-secondary)':'#b8b8b8','var(--noir-text-tertiary)':'#949494',
 'var(--noir-champagne)':'#c9b99b',
}

class Parser(HTMLParser):
 def __init__(self,html):
  super().__init__(convert_charrefs=True);self.roots=[];self.stack=[];self.feed(html)
 def handle_starttag(self,tag,attrs):
  n={'tag':tag,'attrs':dict(attrs),'text':'','children':[]}
  (self.stack[-1]['children'] if self.stack else self.roots).append(n)
  self.stack.append(n)
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.stack.pop()
 def handle_endtag(self,tag):
  assert self.stack and self.stack[-1]['tag']==tag,(tag,self.stack[-1] if self.stack else None)
  self.stack.pop()
 def handle_data(self,data):
  if self.stack:self.stack[-1]['text']+=data

def style(value):
 return dict(part.split(':',1) for part in value.split(';') if ':' in part)
def norm_attrs(n):return {k:v for k,v in n['attrs'].items() if k not in ['style','layer-name','fill','stroke']}
def nodes(n,path='0'):
 yield path,n
 for i,c in enumerate(n['children']):yield from nodes(c,f'{path}.{i}')
def camel(prop):
 if prop.startswith('--'):return prop
 a=prop.split('-');return a[0]+''.join(x.title()for x in a[1:])

def main():
 out={'schema':'f02.paper.clone-theme-assessment.v1','status':'AUTHORED_INPUT_COMPARISON_ONLY','native_ids_observed':False,'native_mutations_performed':False,'boards':[],'color_mapping':[]}
 colors={};counts=Counter();all_exceptions=[]
 for key in ['macro','company','options','editorial']:
  dark=json.loads((HERE/f'{key}-dark.json').read_text());light=json.loads((HERE/f'{key}-light.json').read_text())
  assert [s['key']for s in dark['steps']]==[s['key']for s in light['steps']]
  assert [s['parent']for s in dark['steps']]==[s['parent']for s in light['steps']]
  b={'consumer':key,'step_count':len(dark['steps']),'structure_equal':True,'geometry_equal':True,'text_changes':[],'layer_name_changes':[],'svg_replace_steps':[],'style_changes':[],'vector_color_changes':[],'root_style_changes':[],'unresolved_native_mapping':'Paper may insert wrapper/vector nodes; input DOM paths are navigation only, not native IDs.'}
  for prop,old in dark['styles'].items():
   new=light['styles'][prop]
   if old!=new:
    b['root_style_changes'].append({'property':prop,'from':old,'to':new});colors[old]=new
  for ds,ls in zip(dark['steps'],light['steps']):
   dparser=Parser(ds['html']);lparser=Parser(ls['html'])
   assert len(dparser.roots)==len(lparser.roots)==1
   dn=list(nodes(dparser.roots[0]));ln=list(nodes(lparser.roots[0]));assert len(dn)==len(ln),(key,ds['key'])
   svg='<svg' in ds['html']
   if svg:b['svg_replace_steps'].append(ds['key'])
   for (path,d),(lpath,l) in zip(dn,ln):
    assert path==lpath and d['tag']==l['tag'] and norm_attrs(d)==norm_attrs(l),(key,ds['key'],path)
    where={'step':ds['key'],'input_dom_path':path,'tag':d['tag'],'layer_name':d['attrs'].get('layer-name')}
    if d['text']!=l['text']:b['text_changes'].append({**where,'from':d['text'],'to':l['text']})
    if d['attrs'].get('layer-name')!=l['attrs'].get('layer-name'):
     b['layer_name_changes'].append({**where,'from':d['attrs'].get('layer-name'),'to':l['attrs'].get('layer-name')})
    dstyle=style(d['attrs'].get('style',''));lstyle=style(l['attrs'].get('style',''))
    assert dstyle.keys()==lstyle.keys(),(key,ds['key'],path,'style property set differs')
    for prop,old in dstyle.items():
     new=lstyle[prop]
     if old==new:continue
     assert prop in ['color','background','border','border-top','border-bottom','border-left','border-right'],(key,ds['key'],path,prop)
     b['style_changes'].append({**where,'css_property':prop,'native_property':camel(prop),'from':old,'to':new,'in_svg_replace_step':svg})
     if prop.startswith('border'):
      oldc=old.split(' ')[-1];newc=new.split(' ')[-1]
      assert old.rsplit(' ',1)[0]==new.rsplit(' ',1)[0]
     else:oldc=old;newc=new
     assert oldc not in colors or colors[oldc]==newc,(key,oldc,newc,colors.get(oldc))
     colors[oldc]=newc;counts[(oldc,newc)]+=1
    for attr in ['fill','stroke']:
     old=d['attrs'].get(attr);new=l['attrs'].get(attr)
     if old!=new:
      assert old and new
      b['vector_color_changes'].append({**where,'attribute':attr,'from':old,'to':new})
      assert old not in colors or colors[old]==new
      colors[old]=new;counts[(old,new)]+=1
  b['safe_strategy']='Duplicate actual completed dark artboard; re-read returned clone IDs; apply exact role colors only within that clone; replace listed chart-group roots from light inputs; patch specified text; rename clone; inspect screenshot/JSX.'
  out['boards'].append(b)
 for old,new in colors.items():out['color_mapping'].append({'authored_dark':old,'resolved_dark':DARK_RESOLVED.get(old,old).lower(),'light':new.lower(),'occurrences':counts[(old,new)]})
 resolved={}
 for row in out['color_mapping']:
  old=row['resolved_dark'];new=row['light']
  assert old not in resolved or resolved[old]==new
  resolved[old]=new
 out['resolved_mapping_unambiguous']=True
 out['summary']={'board_pairs':len(out['boards']),'dark_steps_total':sum(b['step_count']for b in out['boards']),'html_structure_and_noncolor_styles_equal':True,'text_changes':sum(len(b['text_changes'])for b in out['boards']),'layer_name_changes':sum(len(b['layer_name_changes'])for b in out['boards']),'svg_groups_requiring_replacement_for_conservative_strategy':sum(len(b['svg_replace_steps'])for b in out['boards']),'color_roles':len(colors)}
 out['source_packet_sha256']=hashlib.sha256((HERE/'consumer-boards.json').read_bytes()).hexdigest()
 (HERE/'clone-theme-assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'summary':out['summary'],'color_mapping':out['color_mapping'],'exceptions':[{k:b[k]for k in ['consumer','text_changes','svg_replace_steps']}for b in out['boards']]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
