"""Pure public explanation of exact owner references; no money duplication.

An entitled caller supplies the validated stored theme snapshot, retained owner
bytes, and fresh CURRENT owner receipt comparison. No network, source admission,
request-time reconstruction, invented joins, or state promotion occurs here.
"""
from urllib.parse import urlsplit
from hashlib import sha256
from datetime import datetime
from collections.abc import Mapping
try:
 from . import program_theme_context as t
except ImportError:
 import program_theme_context as t

CONTRACT='government_program_theme_public_disclosure.v1'
RAIL_EN={'funding_stage':'funding stage','exposure':'reviewed participation','economics':'issuer economics','market_context':'market context','contrary_case':'contrary evidence','next_event':'next condition'}
RAIL_ZH={'funding_stage':'资金阶段','exposure':'已审查参与关系','economics':'发行人财务','market_context':'市场背景','contrary_case':'相反证据','next_event':'下一条件'}


def _primary(url,hosts):
 if not isinstance(url,str):raise ValueError('public_primary_url_missing')
 p=urlsplit(url)
 if p.scheme!='https' or p.hostname not in hosts or p.username or p.password:raise ValueError('public_primary_url_unqualified')
 return url


def _source(owner_key,ref,node,title,url,*,program_id=None,issuer_id=None,security_id=None):
 return dict(owner_key=owner_key,row_id=ref['row_id'],pointer=ref['pointer'],url=url,title=title,program_id=program_id,issuer_id=issuer_id,security_id=security_id,source_publication_date=None,source_available_at=None,house_known_at=None,documentary_class=None,native_reason_code=None)


def _resolve(ref,rail,owners):
 owner=owners[ref['owner_key']];p=owner.payload();node,ancestors=t._pointer(p,ref['pointer']);sources=[]
 if owner.owner_kind=='fms':
  case=next(a for a in reversed(ancestors) if isinstance(a,dict) and a.get('case_key')==ref['row_id'])
  primary=next((x for x in case['observations'] if x['source_surface']=='dsca' and x.get('response_sha256')),None)
  if primary is None:raise ValueError('fms_primary_receipt_missing')
  url=_primary(primary['source_url'],{'www.dsca.mil'})
  sources=[_source(ref['owner_key'],ref,node,case['capability_title'],url)]
  for item in sources:item.update(source_publication_date=case['clocks']['official_web_publication_date']['value'],house_known_at=primary['known_at'],documentary_class='congressional_notification',native_reason_code='congressional_notification_only')
  if rail=='funding_stage':return f"{case['capability_title']}: congressional notification with an estimated upper bound; later implementation is not observed. It does not prove an award or contracted revenue.",f"{case['capability_title']}：国会通知及估计上限；尚未观察到后续实施，不能证明合同授予或合同收入。",sources
  if rail=='exposure':return 'Contractor names are printed in the official notice; their issuer attribution is not reviewed.','官方通知列出了承包商名称；其发行人归属尚未审查。',sources
  if rail=='next_event':return 'Next condition: official evidence of an offered, accepted or implemented letter of offer and acceptance.','下一条件：出现已提出、已接受或已实施《要约和接受函》的官方证据。',sources
  return 'Official notification context is available; it does not establish award revenue.','已有官方通知背景；它不能证明合同收入。',sources
 if owner.owner_kind=='program_ontology':
  evidence={x['evidence_id']:x for x in p['evidence']}
  if node.get('evidence_class')=='official_alliance_policy':
   url=_primary(node['source_url'],{'www.nato.int'});sources=[_source(ref['owner_key'],ref,node,'The Hague Summit Declaration',url)]
   for item in sources:item.update(house_known_at=node['known_at'],documentary_class='alliance_policy',native_reason_code='policy_commitment_only')
   return 'NATO spending commitment is policy context; it does not prove national appropriations, orders or contracted issuer revenue.','北约支出承诺属于政策背景；它不能证明国家拨款、订单或发行人收入。',sources
  program=next((x for x in p['programs'] if x['id']==node.get('program_id')),None)
  if program is None:raise ValueError('reviewed_program_reference_missing')
  for eid in node.get('evidence_refs',[]):
   e=evidence[eid];hosts={'www.congress.gov','crsreports.congress.gov','www.war.gov','www.defense.gov','www.sec.gov','www.secnav.navy.mil','comptroller.war.gov','comptroller.defense.gov'}
   if e['evidence_class']=='issuer_disclosure':hosts={e['pinned_issuer_host']}
   sources.append(_source(ref['owner_key'],ref,node,program['name']+' — '+e['evidence_class'].replace('_',' '),_primary(e['source_url'],hosts),program_id=program['id']))
  for item in sources:
   e=next(e for e in evidence.values() if e['source_url']==item['url']);item['house_known_at']=e['known_at']
  if rail=='exposure':return program['name']+': reviewed '+node['role'].replace('_',' ')+'. Participation does not establish program revenue share.',program['name']+'：已审查的'+({'prime_contractor':'主承包商'}.get(node['role'],node['role']))+'关系。参与不代表项目收入份额。',sources
  if rail=='next_event':return node['title']+'; schedule remains the owning milestone estimate.',node['title']+'；时间安排仍以原里程碑估计为准。',sources
 if owner.owner_kind=='identity_atlas':
  issuer=next(a for a in ancestors if isinstance(a,dict) and a.get('ticker') and 'entities' in a)
  if issuer.get('issuer_attribution')!='reviewed' or node.get('verification_state') not in ('reviewed','confirmed','analyst_approved'):raise ValueError('public_issuer_path_unreviewed')
  # Exact reviewed path, accompanied by the ontology role in the core model.
  sources=[_source(ref['owner_key'],ref,node,node['canonical_name'],_primary(e['url'],{'www.sec.gov','api.usaspending.gov'}),issuer_id='central:'+issuer['ticker']) for e in node['evidence']]
  for item in sources:item['house_known_at']=node['known_at']
  return node['canonical_name']+': reviewed ownership path; this is not program workshare.',node['canonical_name']+'：已审查的所有权路径；这不代表项目份额。',sources
 if owner.owner_kind=='defense_economics':
  profile=next(a for a in ancestors if isinstance(a,dict) and 'ticker_display' in a)
  if rail=='economics':
   span=node['source_span'];url=_primary(span.get('source_url'),{'www.sec.gov'})
   title=profile['name']+' — '+node['period']+' '+node['fact_class'].replace('_',' ')
   sources=[_source(ref['owner_key'],ref,node,title,url,issuer_id=profile['issuer_id'],security_id=profile['security_id'])]
   binding=p['source_bindings'][node['owner_ref']]
   for item in sources:item.update(source_available_at=binding.get('source_available_at'),house_known_at=binding.get('observed_at'))
   return profile['name']+': reported segment evidence is available for '+node['period']+'. It is not program workshare or shareholder capture.',profile['name']+'：已有'+node['period']+'报告分部证据。它不代表项目份额或股东获益。',sources
  if rail=='contrary_case':return profile.get('contrary_case') or 'Contrary case not asserted.','相反情形以原发行人财务档案为准；未推断项目份额。',sources
  if rail=='next_event':return profile.get('next_condition') or 'Next issuer condition not asserted.','下一发行人条件以原财务档案为准。',sources
 if owner.owner_kind=='company_intelligence':
  span=node['source_span'];source=next(x for x in p['sources'] if x.get('document_id')==span['document_id']);issuer=p['issuer']
  sources=[_source(ref['owner_key'],ref,node,issuer['display_name']+' — '+node['period']+' '+node['metric'].replace('_',' '),_primary(source['url'],{'www.sec.gov'}),issuer_id=issuer['company_id'])]
  for item in sources:item.update(source_available_at=p['lifecycle'].get('source_available_at'),house_known_at=p['lifecycle'].get('observed_at'))
  return issuer['display_name']+': reported segment context for '+node['period']+'; no program allocation is asserted.',issuer['display_name']+'：'+node['period']+'报告分部背景；未断言任何项目分配。',sources
 if owner.owner_kind=='budget':
  doc=next(a for a in ancestors if isinstance(a,dict) and a.get('context_id')==ref['row_id'])
  sources=[_source(ref['owner_key'],ref,node,'FY2026 Mandatory Funding Allocation Plan — '+node['section'],_primary(doc['source_url'],{'comptroller.war.gov','comptroller.defense.gov'}))]
  for item in sources:item.update(house_known_at=doc['known_at'],documentary_class='allocation_plan',native_reason_code='allocation_plan_only')
  return node['native_title']+': allocation-plan context; it does not prove obligation, outlay, order or revenue.',node['native_title']+'：资金分配计划背景；它不能证明义务支出、实际支付、订单或收入。',sources
 raise ValueError('public_disclosure_reference_unsupported')


def disclose_program_themes(payload,*,owners,current_owner_receipts):
 """No old pinned revision becomes current when an owner pointer advances.

Current receipts are read by the same owner loader/manifest path, not supplied
by browsers. Absent current comparison yields source_unavailable. The accepted
historical view stays cited, labeled stale, without auto-reminting authority.
"""
 t.validate_program_theme_context(payload,owners=owners)
 if not isinstance(current_owner_receipts,Mapping):raise ValueError('current_owner_receipts_required')
 out=[]
 for theme in payload['themes']:
  known_en=[];known_zh=[];next_en=[];next_zh=[];sources=[];missing=[];rail_states={}
  for rail,item in theme['rails'].items():
   effective=item['state'];fresh=True
   for ref in item['references']:
    pinned=payload['owner_bindings'][ref['owner_key']];current=current_owner_receipts.get(ref['owner_key'])
    if not isinstance(current,Mapping) or current.get('state')=='source_unavailable':effective='source_unavailable';fresh=False
    elif current.get('sha256')!=pinned['sha256'] or current.get('owner_alias_state')=='advanced':effective='stale';fresh=False
   rail_states[rail]=effective
   if effective not in ('supported','partial'):missing.append(rail)
   if not fresh:continue
   for ref in item['references']:
    try:en,zh,refs=_resolve(ref,rail,owners)
    except (ValueError,KeyError,StopIteration):
     rail_states[rail]='source_unavailable';missing.append(rail);continue
    sources+=refs
    if rail=='next_event':next_en.append(en);next_zh.append(zh)
    else:known_en.append(en);known_zh.append(zh)
  # Deduplicate only identical public source identities, preserving different claims.
  seen=set();dedup=[]
  for source in sources:
   marker=(source['owner_key'],source['row_id'],source['url'],source['title'])
   if marker not in seen:seen.add(marker);dedup.append(source)
  unavailable=list(dict.fromkeys(missing))
  out.append(dict(theme_id=theme['theme_id'],rail_states=rail_states,known_en=' '.join(dict.fromkeys(known_en)) or 'No qualified current source evidence is available for this theme.',known_zh=' '.join(dict.fromkeys(known_zh)) or '此主题暂无合格的当前来源证据。',missing_en='Unresolved: '+', '.join(RAIL_EN[k] for k in unavailable)+'.' if unavailable else 'All required rails have qualified context.',missing_zh='尚未解决：'+ '、'.join(RAIL_ZH[k] for k in unavailable)+'。' if unavailable else '所有必需栏目均有合格背景。',next_en=' '.join(dict.fromkeys(next_en)) or NEXT[theme['theme_id']][0],next_zh=' '.join(dict.fromkeys(next_zh)) or NEXT[theme['theme_id']][1],sources=dedup,research_state='SOURCE_CONTEXT_COMPLETE' if all(s=='supported' for s in rail_states.values()) else 'EVIDENCE_INSUFFICIENT'))
 result=dict(contract=CONTRACT,schema_version='1.0.0',content_id='',theme_content_id=payload['content_id'],as_of=payload['as_of'],authority=dict(t.AUTHORITY),themes=out)
 result['content_id']=disclosure_content_id(result);validate_public_theme_disclosure(result);return result

def read_current_theme_owner_receipts(root,*,review,retained_owners):
 """Read current owner pointers/aliases; never update the reviewed map.

Retained exact bytes come from existing immutable owner generations. A pointer
absence or changed generation is a display state, not permission to re-admit.
"""
 from pathlib import Path
 import json
 root=Path(root).resolve();result={}
 for key,ref in review['owners'].items():
  relative=ref.get('path');target=(root/str(relative)).resolve()
  if not isinstance(relative,str) or Path(relative).is_absolute() or not target.is_relative_to(root):raise ValueError('theme_owner_path_invalid')
  try:
   raw=target.read_bytes();p=json.loads(raw);current=dict(state='available',sha256=sha256(raw).hexdigest(),content_id=p.get('content_id'),owner_alias_state='unchanged')
   kind=ref['owner_kind']
   if kind in ('company_intelligence','defense_economics'):
    from engine.company_intelligence.event_workspace import validate_workspace_manifest
    marker=root/'data/company_intelligence/event_workspaces/manifest.json';manifest=json.loads(marker.read_bytes());validate_workspace_manifest(manifest)
    pinned=retained_owners[key].payload()
    from engine.company_intelligence.event_workspace import select_current_event_from_aliases
    subjects=[]
    if kind=='company_intelligence':
     subjects=[(row['ticker'],pinned['event_id']) for row in pinned['issuer']['listings']]
    else:
     subjects=[(profile['ticker_display'],profile['identity_owner_ref'].rsplit(':',1)[-1]) for profile in pinned['profiles'] if profile.get('identity_mode')=='current' and profile.get('identity_owner_ref')]
    if not subjects:current['owner_alias_state']='advanced'
    for ticker,event_id in subjects:
     selected=select_current_event_from_aliases(ticker,manifest['aliases'])
     if selected.event_id!=event_id:current['owner_alias_state']='advanced'
   result[key]=current
  except (OSError,ValueError,TypeError,KeyError):result[key]=dict(state='source_unavailable')
 return result


NEXT={
 'golden_dome':('Watch official funding allocations and contract notices, then confirm the disclosed scope and company participation.','关注官方资金分配及合同公告，并核实披露范围与公司参与关系。'),
 'munitions_replenishment':('Watch official replenishment contract notices and the next company report for delivery and reported financial evidence.','关注官方弹药补充合同公告及下一份公司报告中的交付与财务证据。'),
 'space':('Watch official space contract disclosures and the next company report; confirm scope and participation before attributing program economics.','关注官方航天合同披露及下一份公司报告；先核实范围与参与关系，再判断项目财务关联。'),
 'nato_fms_demand':('Watch national funding decisions and official evidence that a notified sale advances to an offered, accepted or implemented agreement.','关注各国资金决定，以及已通知军售进入提出、接受或实施协议阶段的官方证据。'),
 'fleet_sustainment_upgrades':('Watch official upgrade and sustainment awards and confirm the named contractor and implementation stage.','关注官方升级及维护合同授予，核实具名承包商与实施阶段。'),
 'shipbuilding':('Watch official shipbuilding and sustainment awards and the next company report; confirm program participation and contract scope.','关注官方造船及维护合同授予与下一份公司报告，核实项目参与关系及合同范围。')}

def disclosure_content_id(payload):
 return 'gptd1-'+sha256(t._json({k:v for k,v in payload.items() if k!='content_id'}).encode()).hexdigest()[:24]

def validate_public_theme_disclosure(payload):
 """Validate precomputed public twins; never join source owners in the API."""
 import json
 from pathlib import Path
 from jsonschema import Draft202012Validator,FormatChecker
 schema=json.loads((t._SCHEMA_ROOT/'government_program_theme_public_disclosure.v1.schema.json').read_text())
 if next(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(payload),None) is not None:raise ValueError('public_theme_shape_invalid')
 if [row['theme_id'] for row in payload['themes']]!=list(t.THEMES) or payload['content_id']!=disclosure_content_id(payload):raise ValueError('public_theme_identity_invalid')
 for row in payload['themes']:
  expected='SOURCE_CONTEXT_COMPLETE' if all(s=='supported' for s in row['rail_states'].values()) else 'EVIDENCE_INSUFFICIENT'
  if row['research_state']!=expected:raise ValueError('public_theme_state_invalid')
  classes={'congressional_notification':('congressional_notification_only',{'www.dsca.mil'}),'alliance_policy':('policy_commitment_only',{'www.nato.int'}),'allocation_plan':('allocation_plan_only',{'comptroller.war.gov','comptroller.defense.gov'})}
  for source in row['sources']:
   cls=source['documentary_class']
   if cls is None:
    if source['native_reason_code'] is not None:raise ValueError('public_native_class_invalid')
   else:
    reason,hosts=classes[cls]
    if source['native_reason_code']!=reason:raise ValueError('public_native_class_invalid')
    _primary(source['url'],hosts)
  if row['rail_states']['funding_stage']=='supported' and any(s['documentary_class'] is not None for s in row['sources']):raise ValueError('public_documentary_stage_promotion')
 return True
