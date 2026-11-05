#!/usr/bin/env python3
"""Read-only binding preparation from retained runtime/JSX; never calls Paper."""
import copy,hashlib,html,importlib.util,json,re,sys
from pathlib import Path
from html.parser import HTMLParser

HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[1];WORK=PAPER.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n');return sha(p.read_bytes())
def norm(s):return re.sub(r'\s+',' ',html.unescape(s)).strip()

class Texts(HTMLParser):
 def __init__(self):super().__init__();self.values=[]
 def handle_data(self,s):
  if norm(s):self.values.append(norm(s))
def texts(s):p=Texts();p.feed(s);return p.values

def jsx_nodes(s):
 nodes={};stack=[]
 for m in re.finditer(r'<div\b[^>]*\bid="([^"]+)"[^>]*>|</div>',s):
  if m.group(1):
   ident=m.group(1);node={'id':ident,'parent':stack[-1] if stack else None,'start':m.end(),'children':[]}
   if stack:nodes[stack[-1]]['children'].append(ident)
   nodes[ident]=node;stack.append(ident)
  elif stack:
   ident=stack.pop();nodes[ident]['end']=m.start()
 for node in nodes.values():
  if not node['children'] and 'end' in node:
   raw=s[node['start']:node['end']]
   if '<' not in raw:node['text']=norm(raw)
 return nodes

runtime_path=WORK/'f02_native_runtime.json'
runtime=json.loads(runtime_path.read_text());boards={b['key']:b for b in runtime['boards']}
exports={};allnodes={}
for p in sorted((PAPER/'exports').glob('*.jsx')):
 content=p.read_text();nodes=jsx_nodes(content)
 exports[p.name]={'path':str(p.relative_to(PAPER)),'sha256':sha(p.read_bytes()),'nodes':nodes}
 allnodes.update(nodes)

def descendants(ident):
 if ident not in allnodes:return []
 ans=[];todo=[ident]
 while todo:
  n=allnodes[todo.pop()];ans.append(n);todo.extend(reversed(n['children']))
 return ans

overrides=json.loads((HERE/'step-overrides.json').read_text())['overrides']
sources={'foundation-boards.json':'foundation-inputs/boards.json','consumer-boards.json':'consumer-inputs/consumer-boards.json','mobile-state-boards.json':'mobile-inputs/mobile-state-boards.json'}
before={}
for effective,source in sources.items():
 p=PAPER/source;o=json.loads(p.read_text())
 for b in o['boards']:
  for st in b['steps']:before[(effective,b['key'],st['key'])]=st['html']

textgroups=[];replacements=[];unbound=[];aligned=[]
for ov in overrides:
 bkey=ov['board_key'];key=ov['step_key'];packet=ov['packet']
 if packet not in sources or bkey not in boards:continue
 targets=[bkey]+(['metrics-light'] if bkey=='metrics' else [])
 oldhtml=before[(packet,bkey,key)];newhtml=ov['effective_html']
 for target in targets:
  native=boards[target];root=native['steps'].get(key)
  if not root:
   unbound.append({'board':target,'step':key,'reason':'No actual step ID in retained root runtime; no ID inferred.'});continue
  base={'board_key':target,'board_id':native['id'],'page_id':native['pageId'],'step_key':key,'target_node_id':root,
        'original_html_sha256':sha(oldhtml.encode()),'effective_html_sha256':sha(newhtml.encode()),
        'requires_fresh_read':'Observe exact target in canonical file; verify expected text/structure and current ownership. Retained JSX is a candidate binding, not a current snapshot guard.'}
  if '<svg' in oldhtml and oldhtml!=newhtml:
   replacements.append({**base,'tool':'write_html','arguments':{'fileId':runtime['fileId'],'targetNodeId':root,'mode':'replace','html':newhtml},
      'identity_effect':'Target subtree replacement changes IDs. Record actual created IDs and update step/evidence mapping before later operations.',
      'scope':'Only this owned chart step; axes/grid/viewport retained and raw-count marks changed. Read back native text/vector structure, geometry and screenshot.'})
   continue
  oldtexts=texts(oldhtml);newtexts=texts(newhtml)
  if len(oldtexts)!=len(newtexts):
   unbound.append({**base,'reason':'Text leaf count changed; bind from fresh target read, do not infer by index.','effective_html':newhtml});continue
  leaves=[n for n in descendants(root) if n.get('text')]
  updates=[];used=set()
  for a,b in zip(oldtexts,newtexts):
   if a==b:continue
   matches=[n for n in leaves if n['text']==a and n['id'] not in used]
   anchor=None
   if len(matches)>1 and target=='grammar' and key=='exact-values' and a=='65.57%' and b=='63.31%':
    assert allnodes['4N1-0']['text']=='27 Oct' and allnodes['4N1-0']['parent']=='4N0-0'
    matches=[n for n in matches if n['id']=='4N2-0' and n['parent']=='4N0-0']
    anchor={'kind':'dated cell','parent_id':'4N0-0','date_node_id':'4N1-0','date_text':'27 Oct'}
   if len(matches)>1 and target in ['macro-dark','macro-light'] and key=='sector-8' and a=='—' and b=='0 / 82':
    ident,par,head=('4UW-0','4UV-0','4S8-0') if target=='macro-dark' else ('51G-0','51F-0','53W-0')
    assert allnodes[head]['text']=='Covered / eligible'
    matches=[n for n in matches if n['id']==ident and n['parent']==par]
    anchor={'kind':'coverage column','cell_parent_id':par,'header_text_node_id':head,'header_text':'Covered / eligible','observed_cell_width_px':164}
   if len(matches)==1:
    n=matches[0];used.add(n['id']);update={'nodeId':n['id'],'html':html.escape(b,quote=False),'expected_before_text':a,'after_text':b}
    if anchor:update['semantic_anchor']=anchor
    updates.append(update)
   else:unbound.append({**base,'reason':f'Expected old text has {len(matches)} retained native matches; fresh exact binding required.','expected_before_text':a,'after_text':b})
  if updates:textgroups.append({**base,'tool':'set_text_content','updates':updates,'argument_shape':{'fileId':runtime['fileId'],'updates':[{'nodeId':x['nodeId'],'html':x['html']} for x in updates]},'readback':'Inspect text and wrapping at normal size; preserve numeric frame end-alignment and resize only owned board if new copy exceeds it.'})
  if oldtexts==newtexts and oldhtml!=newhtml:
   aligned.append({**base,'reason':'Text unchanged; effective Macro source composes numeric-alignment override. Apply/reconcile existing numeric-alignment-native-patch.json, not a new row replacement.'})

moves=[]
for bkey in ['macro-dark','macro-light']:
 b=boards[bkey];p=b['steps']['comparison'];energy=b['steps']['sector-8'];materials=b['steps']['sector-10']
 expected=[b['steps']['sector-'+str(i)] for i in range(1,11)]
 observed=[n for n in allnodes.get(p,{}).get('children',[]) if n in expected]
 assert observed==expected,(bkey,observed,expected)
 moves.append({'board_key':bkey,'board_id':b['id'],'parent_id':p,'expected_original_row_ids':expected,
  'expected_sorted_row_ids':[b['steps']['sector-'+str(i)] for i in [1,2,3,4,5,6,7,9,10,8]],
  'tool':'move_nodes','arguments':{'fileId':runtime['fileId'],'moves':[{'nodeId':energy,'after':materials}]},
  'reason':'Above50D descending with nulls last; move the existing Energy row after Materials. IDs and row evidence triggers stay stable.',
  'requires_fresh_read':'Verify both siblings still belong to the same comparison flow parent. AffectedParents readback must preserve all ten rows and place Energy last; never recreate rows for sorting.'})

patch={'schema':'f02.native-fixture-repair-candidates.v1','status':'PREPARED_NOT_APPLIED','file_id':runtime['fileId'],
 'runtime_source':{'path':'f02_native_runtime.json','sha256':sha(runtime_path.read_bytes()),'operation_count':len(runtime['operations'])},
 'export_sources':[{k:v for k,v in x.items() if k!='nodes'} for x in exports.values()],
 'text_groups':textgroups,'chart_step_replacements':replacements,'row_reorders':moves,'numeric_alignment_carry':aligned,'unbound_items':unbound,
 'sequencing':['Sole writer fresh-reads exact owned targets and reconciles no unresolved effect.','Apply small same-board text groups with set_text_content; preserve all node IDs and existing numeric frame repair.','Replace only the three chart steps when source/new chart identity is confirmed; capture actual new step/descendant IDs.','Move each existing Macro Energy row after Materials; verify returned affectedParents, selected Communication row and all evidence actions.','Read back all changed text/calculation/cohort/coverage labels; inspect wrap, chart axes/gap and numeric alignment; update final native mappings and capture/export freeze.'],
 'paper_calls':0,'no_original_or_export_writes':True}
patchhash=dump(HERE/'native-patch-candidates.json',patch)

# Recompute the existing clone comparison against complete effective v3 inputs.
spec=importlib.util.spec_from_file_location('f02_v3_clone_compare',PAPER/'mobile-inputs/compare_clones.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
mobile_path=HERE/'effective/mobile-state-boards.json';supp_path=HERE/'effective/supplemental-boards.json'
mobile=json.loads(mobile_path.read_text());supp=json.loads(supp_path.read_text())
a=next(b for b in mobile['boards'] if b['key']=='macro-docked-1280');b=next(b for b in supp['boards'] if b['key']=='width-1600-docked')
pair=module.compare(a,b);pair['board_dimension_changes']={k:{'before':a[k],'after':b[k]} for k in ['width','height'] if a[k]!=b[k]}
clone={'schema':'f02.paper.clone-preparation.v1','status':'LOCAL_PREPARATION_NOT_APPLIED','fixture_version':'f02.fixture.v3','supplement_sha256':sha(supp_path.read_bytes()),'source_input_sha256':sha(mobile_path.read_bytes()),'pair':pair,'paper_calls':0,
 'instruction':'Only clone a freshly verified v3 source1280. Bind every target via actual duplicate_nodes descendantIdMap and current JSX; old v2 clone hashes are historical.'}
clonehash=dump(HERE/'effective/supplemental-wide-clone.json',clone)
print(json.dumps({'patch_sha256':patchhash,'text_groups':len(textgroups),'text_updates':sum(len(x['updates']) for x in textgroups),'chart_replacements':len(replacements),'moves':len(moves),'unbound':len(unbound),'clone_sha256':clonehash,'clone_structure_equal':pair.get('input_structure_equivalent'),'clone_exceptions':pair.get('structural_exceptions')},indent=2))
