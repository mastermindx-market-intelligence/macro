#!/usr/bin/env python3
"""Compare native construction inputs without contacting Paper.

The output paths identify source HTML elements, not Paper node IDs. The parent
must bind them against observed source JSX/tree and the actual descendantIdMap.
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

HERE=Path(__file__).resolve().parent
INPUT=HERE/'mobile-state-boards.json'

@dataclass
class Element:
    tag: str
    attrs: dict
    children: list=field(default_factory=list)
    chunks: list=field(default_factory=list)

class Parser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.stack=[];self.roots=[]
    def handle_starttag(self,tag,attrs):
        n=Element(tag,dict(attrs))
        (self.stack[-1].children if self.stack else self.roots).append(n)
        self.stack.append(n)
    def handle_startendtag(self,tag,attrs):
        n=Element(tag,dict(attrs))
        (self.stack[-1].children if self.stack else self.roots).append(n)
    def handle_endtag(self,tag):assert self.stack.pop().tag==tag
    def handle_data(self,s):
        if self.stack:self.stack[-1].chunks.append(s)

def parse(html):
    p=Parser();p.feed(html);assert not p.stack and len(p.roots)==1
    return p.roots[0]

def css(style):
    out={}
    for decl in (style or '').split(';'):
        if ':' in decl:
            k,v=decl.split(':',1);out[k.strip()]=v.strip()
    return out

def camel(k):
    return re.sub(r'-([a-z])',lambda m:m[1].upper(),k)

def shape(n):return [n.tag,[shape(c) for c in n.children]]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def direct_text(n):return ''.join(n.chunks).strip()

def flatten(root):
    out=[]
    def walk(n,path,ancestors):
        out.append((path,n,ancestors))
        for i,c in enumerate(n.children):walk(c,path+'/'+c.tag+'['+str(i)+']',ancestors+[(path,n)])
    walk(root,root.tag+'[0]',[])
    return out

def compare(source,target):
    before_steps=source['steps'];after_steps=target['steps']
    pair={'source_key':source['key'],'target_key':target['key'],
      'source_board_name':source['name'],'target_board_name':target['name'],
      'step_keys_equal':[s['key'] for s in before_steps]==[s['key'] for s in after_steps],
      'parents_equal':[s['parent'] for s in before_steps]==[s['parent'] for s in after_steps],
      'geometry_before':source.get('expected_geometry'),'geometry_after':target.get('expected_geometry'),
      'board_style_changes':{},'steps':[],'structural_exceptions':[],
      'binding_rule':'HTML paths are descriptive anchors only. Resolve source native node IDs from observed JSX/tree; verify expected old text/styles; use the original duplicate_nodes descendantIdMap to select destination IDs. Never invent IDs or map solely by array position.'}
    for k in sorted(set(source['artboardStyles'])|set(target['artboardStyles'])):
        a=source['artboardStyles'].get(k);b=target['artboardStyles'].get(k)
        if a!=b:pair['board_style_changes'][k]={'before':a,'after':b}
    if not pair['step_keys_equal'] or not pair['parents_equal']:
        pair['structural_exceptions'].append('Step key or parent order differs; no whole-board clone plan is safe by this comparison.')
        return pair
    totals={'elements':0,'text_changes':0,'style_targets':0,'style_properties':0,'layer_renames':0,'svg_attribute_targets':0,'svg_attribute_changes':0,'vector_subtrees':0,'unchanged_steps':0}
    for a,b in zip(before_steps,after_steps):
        ar=parse(a['html']);br=parse(b['html']);equal=shape(ar)==shape(br)
        st={'key':a['key'],'parent':a['parent'],'structure_equal':equal,'source_html_sha256':sha(a['html']),'target_html_sha256':sha(b['html']),
          'source_structure_sha256':sha(json.dumps(shape(ar),separators=(',',':'))),
          'target_structure_sha256':sha(json.dumps(shape(br),separators=(',',':'))),
          'element_changes':[],'vector_subtrees':[]}
        if not equal:
            pair['structural_exceptions'].append(a['key']+': tag/child topology differs')
            pair['steps'].append(st);continue
        av=flatten(ar);bv=flatten(br);vectors={}
        for (path,n,ancestors),(_,m,_) in zip(av,bv):
            totals['elements']+=1
            delta={'path':path,'tag':n.tag,'source_layer_name':n.attrs.get('layer-name'),'target_layer_name':m.attrs.get('layer-name')}
            old_text,new_text=direct_text(n),direct_text(m)
            if old_text!=new_text:
                assert not n.children and not m.children,('mixed text',a['key'],path)
                delta['text']={'before':old_text,'after':new_text};totals['text_changes']+=1
            ac,bc=css(n.attrs.get('style')),css(m.attrs.get('style'))
            changes={k:{'before':ac.get(k),'after':bc.get(k)} for k in sorted(set(ac)|set(bc)) if ac.get(k)!=bc.get(k)}
            if changes:
                delta['css_changes']=changes
                delta['candidate_update_styles']={camel(k):v['after'] for k,v in changes.items()}
                delta['requires_style_reset']=[camel(k) for k,v in changes.items() if v['after'] is None]
                totals['style_targets']+=1;totals['style_properties']+=len(changes)
            if n.attrs.get('layer-name')!=m.attrs.get('layer-name'):
                delta['rename']={'before':n.attrs.get('layer-name'),'after':m.attrs.get('layer-name')};totals['layer_renames']+=1
            attrs={k:{'before':n.attrs.get(k),'after':m.attrs.get(k)} for k in sorted(set(n.attrs)|set(m.attrs)) if k not in ['style','layer-name'] and n.attrs.get(k)!=m.attrs.get(k)}
            if attrs:
                delta['attribute_changes']=attrs
                svg_ancestor=next(((q,v) for q,v in reversed(ancestors+[(path,n)]) if v.tag=='svg'),None)
                if svg_ancestor:
                    delta['vector_note']='SVG presentation attributes are not assumed to be exposed native style properties. Resolve actual editable vector nodes before styling, or replace only the observed mapped SVG subtree with the exact target SVG.'
                    totals['svg_attribute_targets']+=1;totals['svg_attribute_changes']+=len(attrs)
                    vectors[svg_ancestor[0]]=True
                else:pair['structural_exceptions'].append(a['key']+': non-style attribute change at '+path)
            if any(k in delta for k in ['text','css_changes','rename','attribute_changes']):st['element_changes'].append(delta)
        # Preserve exact supplied SVG markup, including viewBox casing.
        source_svg=re.findall(r'<svg\b.*?</svg>',a['html'],re.S)
        target_svg=re.findall(r'<svg\b.*?</svg>',b['html'],re.S)
        source_svg_paths=[path for path,node,_ in av if node.tag=='svg']
        for i,path in enumerate(source_svg_paths):
            if path in vectors:
                st['vector_subtrees'].append({'path':path,'source_svg_html':source_svg[i],'target_svg_html':target_svg[i],
                    'source_svg_sha256':sha(source_svg[i]),'target_svg_sha256':sha(target_svg[i]),
                    'permitted_local_preparation_only':True,'apply_requires':'Observed destination native SVG/vector node identity and existing root writer authority; never replace an inferred sibling or whole board.'})
                totals['vector_subtrees']+=1
        if not st['element_changes']:totals['unchanged_steps']+=1
        pair['steps'].append(st)
    pair['summary']=totals
    pair['input_structure_equivalent']=not pair['structural_exceptions']
    pair['has_declared_geometry_style_changes']=any(k in {'width','height','min-width','min-height','padding','padding-top','padding-bottom','gap','flex-direction','font-size','line-height'}
       for st in pair['steps'] for e in st['element_changes'] for k in e.get('css_changes',{}))
    pair['font_family_change_count']=sum('font-family' in e.get('css_changes',{}) for st in pair['steps'] for e in st['element_changes'])
    return pair

def main():
    data=json.loads(INPUT.read_text());boards={b['key']:b for b in data['boards']}
    pairs=[compare(boards[a],boards[b]) for a,b in [
      ('macro-dark-en-390','macro-light-zh-390'),
      ('company-eps-overlay-320','company-dividend-overlay-320')]]
    pairs[0]['layout_exceptions']=[
      'Translations and Inter→Noto Sans SC changes can change glyph width, wrapping and auto-height despite identical declared geometry. Inspect the title, scope receipt, scroll cue, two-line sector labels and build-note footer.',
      'The Chinese artifact/provenance-band text inherits Inter in the supplied target input. It requires actual CJK fallback rendering inspection; no extra font-style change is silently added to this exact diff.',
      'The fixed 596px table viewport, ten 56px rows, 44px source controls and all numeric values are identical. Confirm the source outline remains visible inside the clipped region.',
      'Two SVG subtrees (menu icon and history chart) have identical geometry but different theme presentation attributes. Native editability must be observed before selecting style updates versus a bounded vector-subtree replacement.',
      'A duplicate retains the source artboard name and current measured height. Rename to the supplied target name and inspect/set final content fit; do not assume the 1510px initial input height is measured proof.'
    ]
    pairs[1]['layout_exceptions']=[
      'Only native text changes are required by the inputs; no CSS or SVG attribute delta exists. Source and destination use the same 320px overlay anatomy and 44px controls.',
      'The 38px value changes from an em dash to 0.00, moving the following unit within an intrinsic-width row. Inspect this row at its actual 280px body width.',
      'The title, long field identity, comparison explanation and limitation paragraph have different lengths; natural wrapping and total fit can change. Do not force a fixed height copied from the EPS instance.',
      'All five fiscal rows remain. Actual zeros and 0.00 USD/share absolute change must replace missing EPS; percentage growth stays explicitly undefined from a zero baseline.',
      'Update the board name and all changed exact field/source text. A clone with an EPS source identity and dividend values would be invalid.'
    ]
    result={'schema':'f02.paper.clone-preparation.v1','status':'LOCAL_PREPARATION_NOT_APPLIED','input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),
      'paper_calls':0,'native_id_binding':'UNOBSERVED_IN_THIS_PREPARATION','pairs':pairs}
    out=HERE/'clone-diffs.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'input_sha256':result['input_sha256'],
      'pairs':[{k:p[k] for k in ['source_key','target_key','input_structure_equivalent','has_declared_geometry_style_changes','font_family_change_count','summary','structural_exceptions']} for p in pairs]},indent=2))

if __name__=='__main__':main()
