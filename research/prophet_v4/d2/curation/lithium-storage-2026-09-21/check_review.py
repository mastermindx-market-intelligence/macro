"""Read-only verifier for this frozen research batch; no curation or queue writes."""
from pathlib import Path
import copy,hashlib,json,sys
from types import SimpleNamespace
import jsonschema
from referencing import Registry,Resource
E=Path(__file__).resolve().parent;W=E.parents[4];sys.path.insert(0,str(W))
from engine.theme_graph import probation
from engine.theme_graph.ontology import RepositoryStore,compose_proposal_review
from engine.theme_graph.proposal_worklist import compose_worklist
facts=json.loads((E/'facts.json').read_text());review=json.loads((E/'review.json').read_text());drafts=json.loads((E/'draft-proposals.json').read_text())
registry=Registry();schemas={}
for path in (W/'contracts/theme_graph').glob('*.schema.json'):
 s=json.loads(path.read_text());schemas[path.name]=s;registry=registry.with_resource(s['$id'],Resource.from_contents(s))
def validate_bundle(f,r,ds):
 byid={n['node_id']:n for n in f['records']};assert len(byid)==8
 for nid,ref in f['exports'].items():
  raw=(E/ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256']
  doc=json.loads(raw);assert doc['node_id']==nid
  jsonschema.Draft202012Validator(schemas['ontology_neighborhood.v1.schema.json'],registry=registry).validate(doc)
 for n in f['records']:
  observed=[]
  for p in n['membership_paths']:
   rels=p['relations'];assert all(rel['truth_status']=='GRAPH_TRUTH' for rel in rels)
   assert rels[0]['type']=='MEMBER_OF' and rels[0]['direction']=='INCOMING'
   assert rels[0]['peer_node_id']==p['company_node_id']
   if p['path_kind']=='MEMBER_OF_THEN_EXPRESSES':
    assert len(rels)==2 and rels[1]['type']=='EXPRESSES' and rels[1]['direction']=='INCOMING'
    assert rels[1]['peer_node_id']==p['via_basket']
    left=json.loads((E/f['exports'][p['via_basket']]['path']).read_text())
    right=json.loads((E/f['exports'][n['node_id']]['path']).read_text())
    assert rels[0] in left['relations'] and rels[1] in right['relations']
   observed.append(p['company_node_id'])
  assert sorted(set(observed))==n['company_node_ids'] and len(set(observed))==n['recorded_company_count']
 receipts={x['source_code']:x for x in f['source_membership_receipts']};assert set(receipts)=={'300733','307822'}
 concept_map=json.loads((W/'data/baskets_china_ths/concept_map.json').read_text());membership=json.loads((W/'data/baskets_china_ths/membership.json').read_text())
 tracked={str(v.get('ths_concept')).strip():str(k) for k,v in (membership.get('baskets') or {}).items() if isinstance(v,dict) and str(v.get('ths_concept') or '').strip()}
 for code,label in [('300733','锂电池概念'),('307822','动力电池回收')]:
  rr=receipts[code];assert rr['label_zh']==label and rr['node_id']=='ltheme:ths:'+code
  assert concept_map['asof']=='2026-09-05' and concept_map['map'][label]==code
  assert label not in tracked and rr['current_owner_binding']['basket_id'] is None and rr['current_owner_binding']['state']=='OWNER_BASKET_NOT_BOUND'
  assert rr['graph_membership_state']=='NO_RECORDED_MEMBER_PATH' and rr['source_shape']=='ths_concept_dump'
  assert len(rr['snapshots'])==4
  for snap in rr['snapshots']:
   raw=(W/snap['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==snap['sha256']
   doc=json.loads(raw);members=doc[label];tickers=sorted({str(x.get('ticker') or x.get('code')) for x in members if isinstance(x,dict) and (x.get('ticker') or x.get('code'))})
   assert len(tickers)==snap['member_count'] and hashlib.sha256('\n'.join(tickers).encode()).hexdigest()==snap['member_set_sha256']
 for c in f['comparisons']:
  a,b=byid[c['node_id']],byid[c['control_node_id']];present=bool(a['membership_paths']) and bool(b['membership_paths'])
  assert c['semantic_mapping_proven'] is False and c['scope']=='EXACT_LOCAL_CONTROL_ONLY_NOT_WHOLE_CANONICAL_THEME'
  if not present:assert all(c[k] is None for k in ['source_count','control_count','shared_count','jaccard'])
  else:
   sa,sb=set(a['company_node_ids']),set(b['company_node_ids']);assert c['shared_company_node_ids']==sorted(sa&sb)
   assert (c['source_count'],c['control_count'],c['shared_count'])==(len(sa),len(sb),len(sa&sb))
   assert c['jaccard']==len(sa&sb)/len(sa|sb)
 probation.require_valid_rows(ds);assert len(ds)==2
 ids={p['proposal_id'] for p in ds};assert len(ids)==2
 for p in ds:
  assert p['status']=='proposed' and p['ratified_by'] is None and p['adjudicated_at'] is None
  assert p['evidence']['canonical_queue_admission'] is False and p['proposed_by']=='llm_proposed'
 for d in r['decisions']:
  assert d['canonical_mapping_before']==d['canonical_mapping_after']==byid[d['node_id']]['canonical_mapping']
  assert d['canonical_queue_status_before']==d['canonical_queue_status_after']=='NO_PROPOSAL'
  assert not d['adjudication_applied']
  assert d['draft_proposal_id'] is None or d['draft_proposal_id'] in ids
 assert r['closed_counts']=={'reviewed_gap_concepts':5,'source_membership_receipts_present_owner_binding_required':2,'draft_mapping_scope_reviews':2,'application_scope_holds':1,'canonical_proposals_added':0,'ratifications':0,'new_graph_mappings':0}
validate_bundle(facts,review,drafts)
mutations=[]
for label in ['missing_becomes_zero','inflate_overlap','scope_laundering','invent_member','forged_proposal_subject','ratified_without_authority','false_queue_admission']:
 f,r,ds=copy.deepcopy(facts),copy.deepcopy(review),copy.deepcopy(drafts)
 if label=='missing_becomes_zero':f['comparisons'][0]['shared_count']=0
 elif label=='inflate_overlap':f['comparisons'][4]['shared_count']+=1
 elif label=='scope_laundering':f['comparisons'][4]['scope']='WHOLE_CANONICAL_THEME'
 elif label=='invent_member':f['records'][2]['company_node_ids'].append('co:cn:FORGED')
 elif label=='forged_proposal_subject':ds[0]['subject']['canonical_theme']='theme:solar'
 elif label=='ratified_without_authority':ds[0]['status']='ratified'
 else:r['decisions'][0]['canonical_queue_status_after']='PROPOSED'
 try:validate_bundle(f,r,ds)
 except (AssertionError,ValueError,jsonschema.ValidationError):mutations.append({'mutation':label,'detected':True})
 else:raise AssertionError('mutation escaped: '+label)
v=RepositoryStore();canonical=v.read_proposals();rows=canonical+drafts
wl=compose_worklist(rows,asof='2026-09-21',status='all',proposed_by='llm_proposed',limit=100)
jsonschema.Draft202012Validator(schemas['proposal_worklist.v1.schema.json'],registry=registry).validate(wl)
items=[x for x in wl['items'] if x['proposal']['proposal_id'] in {p['proposal_id'] for p in drafts}];assert len(items)==2
snapshot=SimpleNamespace(read_nodes=v.read_nodes,read_edges=v.read_edges,read_node_lifecycle=v.read_node_lifecycle,read_proposals=lambda:rows)
for item in items:
 result=compose_proposal_review(snapshot,**item['review_query']);assert result['proposal_id']==item['proposal']['proposal_id']
 assert result['relation']['state']=='RELATION_ABSENT' and result['proposal']['status']=='proposed'
assert json.loads((E/'draft-worklist-preview.json').read_text())['document']==wl
assert len(canonical)==234 and all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in facts['canonical_inputs'].items())
result={'source_head':facts['source_head'],'actual_cli_exports':len(facts['commands']),'all_cli_exit_zero':all(x['exit_code']==0 for x in facts['commands']),'schema_valid_exports':len(facts['exports']),'reviewed_gap_concepts':5,'mapped_controls':3,'proposal_drafts':2,'canonical_queue_rows':234,'detached_worklist_to_review_roundtrips':2,'preview_origin':'UNPUBLISHED_DRAFT_OVERLAY_NOT_CANONICAL_QUEUE','mutations':mutations,'canonical_input_hashes_unchanged':11,'graph_or_queue_writes':0,'production_source_changed':False,'ci_polled':False,'external_primary_sources':len(review['primary_sources']),'raw_source_membership_receipt_sets':sum(len(x['snapshots']) for x in facts['source_membership_receipts']),'owner_basket_binding_gaps':2,'review_accepted':False}
assert result==json.loads((E/'verification.json').read_text());print(json.dumps(result,indent=2))
