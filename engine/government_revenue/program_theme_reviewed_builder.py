"""Builder-only replay of reviewed stable references; no new evidence admission.

Version 1.0 exact-byte reviews stay strict. Version 1.1 stores fingerprints of
approved leaves plus their source/identity dependencies. Current complete owner
validation precedes resolution; irrelevant header clocks or unrelated rows do
not mint new authority. Version 1.2 explicitly narrows financial leaves to consumed
periods and excludes unconsumed profile narratives; migration proves prior approval
and unchanged selected semantics. Missing or changed leaves degrade only themes.
"""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import json,re
try:
 from . import program_theme_context as t
 from . import program_theme_disclosure as d
except ImportError:
 import program_theme_context as t
 import program_theme_disclosure as d

def _walk(node,path=''):
 if isinstance(node,dict):
  yield path,node
  for k,v in node.items():yield from _walk(v,path+'/'+k.replace('~','~0').replace('/','~1'))
 elif isinstance(node,list):
  for i,v in enumerate(node):yield from _walk(v,path+'/'+str(i))

def stable_reference(ref,owner):
 p=owner.payload();shape=lambda x:re.sub(r'/\d+(?=/|$)','/*',x)
 hits=[]
 for path,row in _walk(p):
  if any(row.get(k)==ref['row_id'] for k in t.IDS|{'context_id'}):
   # The reviewed pointer selects a collection and an optional descendant.
   if shape(ref['pointer']).startswith(shape(path)+'/') or shape(ref['pointer'])==shape(path):
    oldparts=ref['pointer'].split('/');newparts=path.split('/')
    candidate=dict(ref,pointer=path+'/'+ '/'.join(oldparts[len(newparts):]) if len(oldparts)>len(newparts) else path)
    try:t._pointer(p,candidate['pointer'])
    except ValueError:continue
    hits.append(candidate)
 if len(hits)!=1:raise ValueError('reviewed_stable_reference_missing_or_ambiguous')
 return hits[0]

def reference_fingerprint(ref,rail,owner,as_of,*,version='1.1.0'):
 """Hash the approved leaf and all source/identity dependencies it consumes."""
 if version not in ('1.1.0','1.2.0'):raise ValueError('review_fingerprint_version_invalid')
 row,node=t._ref(ref,rail,{ref['owner_key']:owner},t._instant(as_of));p=owner.payload();_,anc=t._pointer(p,ref['pointer']);kind=owner.owner_kind
 dependencies={}
 if kind=='program_ontology':
  ids=set(row.get('evidence_refs',[]));dependencies['evidence']=[e for e in p['evidence'] if e['evidence_id'] in ids]
  dependencies['program']=[x for x in p['programs'] if x['id']==row.get('program_id')]
  dependencies['review_coverage']=p.get('review_coverage',p.get('coverage',[]));dependencies['overrides']=p.get('overrides',[])
 elif kind=='identity_atlas':
  issuer=next(x for x in anc if isinstance(x,dict) and 'entities' in x and x.get('ticker'))
  # Sibling archetype displays do not qualify this approved legal entity/listing.
  # Selected leaf, issuer identity, source/rights and listing dependencies remain bound.
  dependencies['issuer']={k:v for k,v in issuer.items() if k not in ('entities','archetype_context')}
 elif kind=='defense_economics':
  profile=next(x for x in anc if isinstance(x,dict) and 'ticker_display' in x)
  dependencies['profile']={k:profile[k] for k in ('issuer_id','security_id','ticker_display','name','identity_mode','identity_owner_ref','program_workshare','program_workshare_state','shareholder_capture','authority')}
  selected_fact=isinstance(node,dict) and node.get('fact_id')==ref['row_id'] and '/axes/economics/facts/' in ref['pointer']
  if rail in ('contrary_case','next_event') and not (version=='1.2.0' and selected_fact):dependencies['narrative']={k:profile[k] for k in ('contrary_case','contrary_case_zh','next_condition','next_condition_zh','invalidation','invalidation_zh')}
  axis=next((x for x in reversed(anc) if isinstance(x,dict) and 'state' in x and 'facts' in x),None)
  if axis:dependencies['axis']={k:axis[k] for k in ('state','owner_ref','observed_at','fiscal_period','reason_code')}
  if isinstance(node,dict) and node.get('owner_ref'):dependencies['source_binding']={k:v for k,v in p['source_bindings'][node['owner_ref']].items() if k not in ('sha256','content_id','owner_admission_ref')}
  if version=='1.2.0' and selected_fact:
   # Owner validation has already established subject, source and period membership.
   # Bind only periods consumed by this fact, including any derived operands.
   def selected_binding(fact):
    binding=p['source_bindings'][fact['owner_ref']]
    if fact['period'] not in binding['periods']:raise ValueError('selected_fact_period_missing')
    return {k:([fact['period']] if k=='periods' else v) for k,v in binding.items() if k not in ('sha256','content_id','owner_admission_ref')}
   dependencies['source_binding']=selected_binding(node)
   dependencies['operand_bindings']={key:selected_binding(node[key]) for key in ('numerator','denominator') if key in node}
  # Whole-owner receipt revisions are requalified by the incumbent producer.
  # The approved fact still binds its exact full source hash, literal and span.
 elif kind=='company_intelligence':
  dependencies={k:p[k] for k in ('issuer','event_id','fiscal_period','lifecycle')}
  dependencies['sources']=[x for x in p['sources'] if x.get('document_id')==(node.get('source_span') or {}).get('document_id')]
 if kind=='defense_economics' and rail=='market_context' and ref['pointer'].endswith('/axes/participation'):
  # Same exact owner bytes may be replayed at a fresh local read instant.
  # Bind all native hashes, subject, membership/date/denominator and states.
  node={k:v for k,v in node.items() if k!='observed_at'}
  row=dependencies['profile']
  dependencies['axis'].pop('observed_at',None)
  dependencies.pop('source_binding',None)  # full group_sources below binds this exact pulse too
  dependencies['group_sources']={key:{k:v for k,v in p['source_bindings'][key].items() if k!='observed_at'} for key in node['evidence_refs']}
 # Case, budget document and identity leaf include all native stage/clocks/receipts.
 def normalize_transport(value):
  if isinstance(value,dict):return {k:normalize_transport(v) for k,v in value.items()}
  if isinstance(value,list):return [normalize_transport(v) for v in value]
  if isinstance(value,str):
   match=re.fullmatch(r'event_workspace:[a-f0-9]{24}:(evt_cik[0-9]{10}_[0-9]{4}q[1-4]_results)',value)
   if match:return 'event_workspace:'+match.group(1)
   if version=='1.2.0':
    match=re.fullmatch(r'event_workspace:[a-f0-9]{24}:(evt_cik[0-9]{10}_[0-9]{4}q[1-4]_results):(disclosure_document_[a-f0-9]{64})',value)
    if match:return 'event_workspace:'+match.group(1)+':'+match.group(2)
  return value
 payload=dict(kind=kind,row=row,node=node,dependencies=dependencies)
 if version=='1.2.0':
  payload['fingerprint_version']=version
  dependencies['owner_authority']={'admission_ref':owner.admission_ref,'rights_state':owner.rights_state}
 return sha256(t._json(normalize_transport(payload)).encode()).hexdigest()

def make_reviewed_leaf_config(review,owners,*,as_of,version='1.1.0'):
 """Explicit review-time conversion, never called automatically by publication."""
 if version not in ('1.1.0','1.2.0'):raise ValueError('review_fingerprint_version_invalid')
 out=deepcopy(review);out['schema_version']=version;fingerprints={}
 for theme,rails in out['assignments'].items():
  for rail,item in rails.items():
   for i,ref in enumerate(item['references']):
    fingerprints[f'{theme}/{rail}/{i}']=reference_fingerprint(ref,rail,owners[ref['owner_key']],as_of,version=version)
 out['reference_fingerprints']=fingerprints
 return out

def migrate_reviewed_leaf_config(review,reviewed_owners,current_owners,*,as_of,reviewed_at,reviewer):
 """Explicit 1.1 to 1.2 review: prove old approval and unchanged selected semantics.

 A narrower fingerprint alone cannot reapprove changed facts. Both retained
 reviewed bytes and qualified current owners are required for every reference.
 """
 if review.get('schema_version')!='1.1.0' or not isinstance(reviewer,str) or not reviewer.strip():raise ValueError('review_migration_invalid')
 if t._instant(reviewed_at)>t._instant(as_of):raise ValueError('theme_review_not_yet_known')
 out=deepcopy(review);fingerprints={};seen=set()
 for theme,rails in review['assignments'].items():
  for rail,item in rails.items():
   for i,ref in enumerate(item['references']):
    token=f'{theme}/{rail}/{i}';seen.add(token);key=ref['owner_key']
    prior=stable_reference(ref,reviewed_owners[key]);current=stable_reference(ref,current_owners[key])
    if reference_fingerprint(prior,rail,reviewed_owners[key],as_of)!=review['reference_fingerprints'].get(token):raise ValueError('review_migration_prior_approval_mismatch')
    old=reference_fingerprint(prior,rail,reviewed_owners[key],as_of,version='1.2.0')
    new=reference_fingerprint(current,rail,current_owners[key],as_of,version='1.2.0')
    if old!=new:raise ValueError('review_migration_selected_dependency_changed')
    out['assignments'][theme][rail]['references'][i]=current;fingerprints[token]=new
 if seen!=set(review['reference_fingerprints']):raise ValueError('review_fingerprint_inventory_invalid')
 for key,owner in current_owners.items():
  out['owners'][key]['sha256']=sha256(owner.raw_bytes).hexdigest()
 out.update(schema_version='1.2.0',reviewed_at=reviewed_at,reviewer=reviewer,reference_fingerprints=fingerprints)
 return out

def load_current_reviewed_theme_inputs(root,*,as_of,review_path=t.THEME_REVIEW_PATH):
 root=Path(root).resolve()
 def file(path):
  if not isinstance(path,str) or Path(path).is_absolute():raise ValueError('theme_owner_path_invalid')
  resolved=(root/path).resolve()
  if not resolved.is_relative_to(root):raise ValueError('theme_owner_path_invalid')
  return resolved
 review=json.loads(file(review_path).read_bytes())
 if review.get('schema_version')=='1.0.0':
  assignments,owners=t.load_reviewed_program_theme_inputs(root,review_path=review_path)
  return review,assignments,owners
 fields={'contract','schema_version','reviewed_at','reviewer','owners','assignments','reference_fingerprints'}
 if not isinstance(review,dict) or set(review)!=fields or review['contract']!=t.THEME_REVIEW_CONTRACT or review['schema_version'] not in ('1.1.0','1.2.0') or not review['reviewer'].strip():raise ValueError('theme_review_invalid')
 if t._instant(review['reviewed_at'])>t._instant(as_of):raise ValueError('theme_review_not_yet_known')
 owners={};unavailable=set();current_company_snapshot=None
 for key,ref in review['owners'].items():
  if set(ref)!={'owner_kind','path','sha256','available_at','admission_ref','rights_state'} or not re.fullmatch('[a-f0-9]{64}',ref['sha256']):raise ValueError('theme_review_owner_invalid')
  path=file(ref['path'])
  try:
   if ref['owner_kind']=='company_intelligence':
    subject=re.fullmatch(r'data/company_intelligence/event_workspaces/generations/[a-f0-9]{24}/workspaces/(evt_cik[0-9]{10}_[0-9]{4}q[1-4]_results)\.json',ref['path'])
    if subject is None:raise ValueError('theme_company_owner_native_path_required')
    from .defense_economics_producer import load_defense_owner_snapshot
    if current_company_snapshot is None:current_company_snapshot=load_defense_owner_snapshot(root)
    if current_company_snapshot is None or subject.group(1) not in current_company_snapshot['rows']:raise ValueError('theme_current_company_owner_missing')
    generation=current_company_snapshot['manifest']['generation_id'];relative='workspaces/'+subject.group(1)+'.json'
    raw=(root/'data/company_intelligence/event_workspaces/generations'/generation/relative).read_bytes()
    if sha256(raw).hexdigest()!=current_company_snapshot['manifest']['files'][relative]['sha256']:raise ValueError('theme_company_owner_current_hash_mismatch')
   else:raw=path.read_bytes()
   p=json.loads(raw)
   clocks=list(t._clocks(p));available=max([t._instant(ref['available_at'])]+clocks).isoformat()
   owner=t.OwnerSnapshot(ref['owner_kind'],raw,available,ref['admission_ref'],ref['rights_state']);owner.payload()
   if t._instant(available)>t._instant(as_of):raise ValueError('owner_not_yet_available')
   owners[key]=owner
  except (OSError,ValueError,TypeError,KeyError):unavailable.add(key)
 assignments=deepcopy(review['assignments']);seen=set()
 for theme,rails in assignments.items():
  for rail,item in rails.items():
   resolved=[];failure=None
   for i,ref in enumerate(item['references']):
    token=f'{theme}/{rail}/{i}';seen.add(token);expected=review['reference_fingerprints'].get(token)
    if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('review_fingerprint_missing')
    if ref['owner_key'] in unavailable:failure='source_unavailable';continue
    try:
     current=stable_reference(ref,owners[ref['owner_key']])
     if reference_fingerprint(current,rail,owners[ref['owner_key']],as_of,version=review['schema_version'])!=expected:raise ValueError('reviewed_leaf_changed')
     resolved.append(current)
    except (ValueError,TypeError,KeyError,StopIteration):failure='stale'
   if failure:item.update(state=failure,reason_code='reviewed_source_unavailable' if failure=='source_unavailable' else 'reviewed_leaf_changed',references=[])
   else:item['references']=resolved
 if seen!=set(review['reference_fingerprints']):raise ValueError('review_fingerprint_inventory_invalid')
 return review,assignments,owners

def build_public_theme_candidate(root,*,generated_at,as_of,review_path=t.THEME_REVIEW_PATH):
 """The incumbent publisher may commit this sibling independently of candidates.

A missing/corrupt theme dependency returns six closed unavailable disclosures;
no candidate rejection, source retrieval, or authority remint occurs here.
"""
 try:
  review,a,owners=load_current_reviewed_theme_inputs(root,as_of=as_of,review_path=review_path)
  stale={(theme,rail) for theme,rails in a.items() for rail,item in rails.items() if item['state']=='stale' and not item['references']}
  # A rejected changed leaf cannot remain a canonical current owner reference.
  # Canonical absence preserves the changed-leaf reason; public rail is stale.
  for theme,rail in stale:a[theme][rail]['state']='source_unavailable'
  canonical=t.compose_program_theme_context(a,owners=owners,generated_at=generated_at,as_of=as_of)
  current=d.read_current_theme_owner_receipts(root,review=review,retained_owners=owners)
  display=d.disclose_program_themes(canonical,owners=owners,current_owner_receipts=current)
  for row in display['themes']:
   for theme,rail in stale:
    if row['theme_id']==theme:row['rail_states'][rail]='stale'
  display['content_id']=d.disclosure_content_id(display);d.validate_public_theme_disclosure(display)
  return dict(state='qualified_partial',reference_snapshot=canonical,public_disclosure=display)
 except (OSError,ValueError,TypeError,KeyError,StopIteration):
  canonical=t.compose_program_theme_context({},owners={},generated_at=generated_at,as_of=as_of)
  display=d.disclose_program_themes(canonical,owners={},current_owner_receipts={})
  return dict(state='source_unavailable',reference_snapshot=canonical,public_disclosure=display)
