"""Pure public explanation of exact owner references; no money duplication.

An entitled caller supplies the validated stored theme snapshot, retained owner
bytes, and fresh CURRENT owner receipt comparison. No network, source admission,
request-time reconstruction, invented joins, or state promotion occurs here.
"""
from urllib.parse import urlsplit
from hashlib import sha256
from datetime import datetime
from collections.abc import Mapping
import math
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


def _resolve(ref,rail,owners,reason_code=None):
 owner=owners[ref['owner_key']];p=owner.payload();node,ancestors=t._pointer(p,ref['pointer']);sources=[]
 if owner.owner_kind=='fms':
  case=next(a for a in reversed(ancestors) if isinstance(a,dict) and a.get('case_key')==ref['row_id'])
  # DSCA-first; State primary receipt is admitted as an alternative. Federal
  # Register-only observations and unknown surfaces are not primary receipts.
  primary=next((x for x in case['observations'] if x['source_surface']=='dsca' and x.get('response_sha256')),None)
  if primary is None:primary=next((x for x in case['observations'] if x['source_surface']=='state' and x.get('response_sha256')),None)
  if primary is None:raise ValueError('fms_primary_receipt_missing')
  hosts={'www.dsca.mil'} if primary['source_surface']=='dsca' else {'www.state.gov'}
  url=_primary(primary['source_url'],hosts)
  sources=[_source(ref['owner_key'],ref,node,case['capability_title'],url)]
  for item in sources:item.update(source_publication_date=case['clocks']['official_web_publication_date']['value'],house_known_at=primary['known_at'],documentary_class='congressional_notification',native_reason_code='congressional_notification_only')
  if rail=='funding_stage':return f"{case['capability_title']}: congressional notification with an estimated upper bound; later implementation is not observed. It does not prove an award or contracted revenue.",f"{case['capability_title']}：国会通知及估计上限；尚未观察到后续实施，不能证明合同授予或合同收入。",sources
  if rail=='exposure':return 'Contractor names are printed in the official notice; their issuer attribution is not reviewed.','官方通知列出了承包商名称；其发行人归属尚未审查。',sources
  if rail=='next_event':return 'Next condition: official evidence of an offered, accepted or implemented letter of offer and acceptance.','下一条件：出现已提出、已接受或已实施《要约和接受函》的官方证据。',sources
  return 'Official notification context is available; it does not establish award revenue.','已有官方通知背景；它不能证明合同收入。',sources
 if owner.owner_kind=='program_ontology':
  evidence={x['evidence_id']:x for x in p['evidence']}
  if ref['pointer'].startswith('/public_agreement_assertions/'):
   e=evidence[node['evidence_refs'][0]]
   url=_primary(node['source_url'],{'www.sda.mil','www.l3harris.com'})
   sources=[_source(ref['owner_key'],ref,node,node['program_label']+' — prototype agreement announcement',url)]
   sources[0].update(source_publication_date=node['published_on'],source_available_at=e['known_at'],house_known_at=node['known_at'],documentary_class='prototype_agreement',native_reason_code='prototype_agreement_only')
   if rail=='next_event':
    year=node['expected_launch_year']
    return f'Reported target: launch availability by the end of {year}; this is an expected target, not observed delivery, acceptance or installed capacity.',f'报告预期目标：到{year}年底具备发射条件；这不是已观测交付、验收或已安装产能。',sources
   def amount(v,zh=False):
    unit=({'USD_million':'百万美元','USD_billion':'十亿美元'} if zh else {'USD_million':' million USD','USD_billion':' billion USD'})[v['unit']]
    return ('约' if zh and v['approximate'] else 'approximately ' if v['approximate'] else '')+str(v['value'])+unit
   en='; '.join(x['name_literal']+': '+amount(x['potential_value'])+(f"; reported quantity {x['announced_vehicles']} vehicles" if x['announced_vehicles'] is not None else '') for x in node['parties'])
   zh='；'.join(x['name_literal']+'：'+amount(x['potential_value'],True)+(f"；报告载具数量{x['announced_vehicles']}" if x['announced_vehicles'] is not None else '') for x in node['parties'])
   collective=node['collective_value'];collective_en='';collective_zh=''
   if collective is not None:
    collective_en=' Reported overlapping collective view: '+amount(collective)+'; do not add it to named-party values.'
    collective_zh=' 报告中的重叠合计视图为'+amount(collective,True)+'，不能与具名参与方金额相加。'
   return node['program_label']+': source reports firm-fixed-price OTA prototype agreements, with total potential agreement values '+en+'.'+collective_en+' These are not observed obligations, issuer revenue or cash; legal counterparty and issuer allocation remain unreviewed.',node['program_label']+'：来源报告固定价格OTA原型协议，协议潜在总金额为'+zh+'。'+collective_zh+'这些不是已观测义务金额、发行人收入或现金；法律交易对手与发行人分配尚未核验。',sources
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
  if rail=='economics' or rail=='contrary_case' and reason_code in ('reported_space_ownership_change','reported_program_cost_maturation_charge'):
   span=node['source_span'];hosts={'www.sec.gov'}
   if rail=='contrary_case' and profile['issuer_id']=='cik:0000202058':hosts.add('investors.l3harris.com')
   url=_primary(span.get('source_url'),hosts)
   title=profile['name']+' — '+node['period']+' '+node['fact_class'].replace('_',' ')
   sources=[_source(ref['owner_key'],ref,node,title,url,issuer_id=profile['issuer_id'],security_id=profile['security_id'])]
   binding=p['source_bindings'][node['owner_ref']]
   for item in sources:item.update(source_available_at=binding.get('source_available_at'),house_known_at=binding.get('observed_at'))
   if rail=='contrary_case':
    if reason_code=='reported_program_cost_maturation_charge':
     return 'Northrop Grumman reported a 68 USD million unfavorable SiAW estimate-at-completion adjustment for Q2 2026. The same disclosure projects higher costs to mature AARGM-ER production and to develop and qualify SiAW, and reports a favorable Sentinel adjustment tied to contract incentives as a partial offset. This is disclosed cost and execution context, not installed capacity, unit throughput or future profitability.','Northrop Grumman披露2026年第二季度SiAW预计完工成本不利调整为6800万美元。同一披露预计AARGM-ER生产成熟化及SiAW开发与认证的成本上升，并披露与合同激励挂钩的Sentinel有利调整作为部分抵销。这属于已披露成本与执行背景，不代表已安装产能、单位产量或未来盈利能力。',sources
    if node['fact_id'].endswith(':space_business_sale_completed_terms'):
     return 'L3Harris reports the completed majority sale of its commercial space propulsion, power and electronics businesses; broad space demand cannot be attributed wholly to LHX after the sale. This is ownership context, not a measured revenue loss.','L3Harris披露已完成商业航天推进、电力及电子业务的多数股权出售；出售后不能将广泛航天需求全部归于LHX。这属于所有权背景，未量化收入损失。',sources
    return 'L3Harris reports approximately 40% retained ownership in Rocketdyne and excludes RS-25 operations from the sale. Ownership share is not program workshare or revenue share.','L3Harris披露保留Rocketdyne约40%的股权，RS-25业务不在出售范围内。股权比例不等于项目份额或收入份额。',sources
   return profile['name']+': reported segment evidence is available for '+node['period']+'. It is not program workshare or shareholder capture.' ,profile['name']+'：已有'+node['period']+'报告分部证据。它不代表项目份额或股东获益。',sources
  if rail=='market_context' and ref['pointer'].endswith('/axes/participation'):
   return 'Shared broad defense-basket context, not a theme-specific portfolio: '+node['summary_en'],'共享广泛国防篮子背景，并非主题专属组合：'+node['summary_zh'],sources
  if rail=='contrary_case':return profile.get('contrary_case') or 'Contrary case not asserted.','相反情形以原发行人财务档案为准；未推断项目份额。',sources
  if rail=='next_event':return profile.get('next_condition') or 'Next issuer condition not asserted.','下一发行人条件以原财务档案为准。',sources
 if owner.owner_kind=='company_intelligence':
  span=node['source_span'];source=next(x for x in p['sources'] if x.get('document_id')==span['document_id']);issuer=p['issuer']
  primary=[x for x in issuer['listings'] if x.get('is_primary') and x.get('valid_to') is None]
  security_id=primary[0]['security_id'] if len(primary)==1 else None
  sources=[_source(ref['owner_key'],ref,node,issuer['display_name']+' — '+node['period']+' '+node['metric'].replace('_',' '),_primary(source['url'],{'www.sec.gov'}),issuer_id=issuer['company_id'],security_id=security_id)]
  for item in sources:item.update(source_available_at=p['lifecycle'].get('source_available_at'),house_known_at=p['lifecycle'].get('observed_at'))
  if rail=='contrary_case':
   return f"General Dynamics reports Marine Systems unfunded backlog of {node['value']:,.0f} USD million for {node['period']}. This reported category does not establish funded orders, cancellation or forecast revenue.",f"General Dynamics披露{node['period']}Marine Systems未获资金积压订单为{node['value']:,.0f}百万美元。此报告类别不能证明已获资金订单、取消订单或预测收入。",sources
  return issuer['display_name']+': reported segment context for '+node['period']+'; no program allocation is asserted.',issuer['display_name']+'：'+node['period']+'报告分部背景；未断言任何项目分配。',sources
 if owner.owner_kind=='budget':
  doc=next(a for a in ancestors if isinstance(a,dict) and a.get('context_id')==ref['row_id'])
  sources=[_source(ref['owner_key'],ref,node,'FY2026 Mandatory Funding Allocation Plan — '+node['section'],_primary(doc['source_url'],{'comptroller.war.gov','comptroller.defense.gov'}))]
  for item in sources:item.update(house_known_at=doc['known_at'],documentary_class='allocation_plan',native_reason_code='allocation_plan_only')
  return node['native_title']+': allocation-plan context; it does not prove obligation, outlay, order or revenue.',node['native_title']+'：资金分配计划背景；它不能证明义务支出、实际支付、订单或收入。',sources
 raise ValueError('public_disclosure_reference_unsupported')



# Conditional interpretation of current cited rows, not a new exposure owner.
# Each entry is gated below on the actual resolved source class/scope. Neither
# this language nor an issuer baseline promotes a rail or allocates theme money.
_THEME_CASES={
 'golden_dome':(
  'The cited allocation section covers integrated air and missile defense; a Golden Dome program allocation is not established. Conditional: if the allocation plan advances to funded, scope-specific contracts, verified contractor participation could become orders and later revenue. Margin and cash would still depend on contract terms, execution costs and payment timing. Issuer allocation, workshare and common-shareholder cash are unknown.',
  '所引分配章节涵盖综合防空及导弹防御；尚未确认Golden Dome项目分配。条件情景：若分配计划推进至已获资金、范围明确的合同，已核实承包商的参与才可能转为订单及后续收入。利润率与现金仍取决于合同条款、执行成本及付款时间。发行人分配、项目份额及普通股股东现金均未知。',
  'Invalidation: funding does not advance, the awarded scope names a different supplier, or disclosed execution costs offset the demand benefit. Confirm the program, contractor and contract stage before assigning economics.',
  '失效条件：资金未推进、获授范围由其他供应商承担，或披露的执行成本抵销需求收益。先确认项目、承包商及合同阶段，再判断财务传导。'),
 'munitions_replenishment':(
  'Conditional: funded replenishment orders could raise deliveries only within verified contractor scope. If production scales without matching cost escalation, segment profit could improve; inventory, supplier payments and ramp investment could absorb cash first. The reported segments are baselines, not munitions revenue or a known program share.',
  '条件情景：已获资金的补充订单，只有在已核实承包范围内才可能增加交付。若产量扩大而成本未同步攀升，分部利润可能改善；库存、供应商付款及扩产投资可能先占用现金。报告分部仅为基准，并非弹药收入或已知项目份额。',
  'Invalidation: no qualifying production award or delivery conversion appears, or disclosed costs/charges exceed the ramp benefit. Check contract scope and the next reported sales, margin and cash evidence separately.',
  '失效条件：未出现合格生产合同或交付转化，或披露的成本及费用超过扩产收益。分别核实合同范围，以及下一份报告中的销售、利润率与现金证据。'),
 'space':(
  'Conditional: a verified space-program award could affect the issuer only after scope and business ownership are established. Development costs and schedule changes could offset revenue; production or sustainment terms could have a different margin/cash profile. The cited reported segments are issuer context, not space-program revenue. Program capture and conversion timing remain unknown.',
  '条件情景：航天项目合同只有在范围及业务所有权核实后，才可能影响发行人。开发成本及进度变化可能抵销收入；生产或维护条款的利润与现金特征可能不同。所引报告分部仅属发行人背景，并非航天项目收入。项目获益及转化时间仍未知。',
  'Invalidation: the program or retained business scope is not established, or disclosed cost/schedule changes undermine conversion. Confirm the exact program and current owner before interpreting the next financial report.',
  '失效条件：项目或保留业务范围未获确认，或披露的成本及进度变化削弱转化。解读下一份财报前，先核实具体项目及当前业务所有者。'),
 'nato_fms_demand':(
  'Conditional: policy commitments and the Spain F-100 notification could become demand only through national funding and an offered/accepted/implemented agreement, then verified contracts. Margin and cash would depend on the contracted mix and payment terms. The notification ceiling is not issuer revenue; contractor attribution and capture remain unreviewed.',
  '条件情景：政策承诺及西班牙F-100通知，须经各国资金决定、提出／接受／实施协议，再落实已核实合同，才可能转为需求。利润与现金取决于合同组合及付款条款。通知上限并非发行人收入；承包商归属及获益仍未审查。',
  'Invalidation: funding or agreement advancement does not occur, the notified scope changes, or the eventual contractor differs. Follow official agreement evidence before any issuer or financial attribution; no advancement date is asserted.',
  '失效条件：资金或协议未推进、通知范围改变，或最终承包商不同。先追踪官方协议证据，再作发行人或财务归属判断；未断言推进日期。'),
 'fleet_sustainment_upgrades':(
  'Conditional: the Spain F-100 upgrade notification could support service or equipment demand only after agreement advancement and a reviewed contract/contractor path. Recurring support and one-time upgrades could have different margins; timing, inventory and customer payments could separate revenue from cash. No contractor mix or issuer capture is established.',
  '条件情景：西班牙F-100升级通知，只有在协议推进、合同及承包商路径审查后，才可能支持服务或设备需求。持续维护与一次性升级的利润率可能不同；时间、库存及客户付款可能使收入与现金分离。承包组合及发行人获益尚未确认。',
  'Invalidation: no implementation evidence appears, the upgrade/support scope changes, or the named contractor is not qualified. Confirm agreement stage, contractor identity and contract mix before comparing financial outcomes.',
  '失效条件：未出现实施证据、升级／维护范围改变，或具名承包商未获核验。比较财务结果前，先确认协议阶段、承包商身份及合同组合。'),
 'shipbuilding':(
  'Conditional: funded work within the reviewed Virginia/Electric Boat path could convert into deliveries, but GD Marine Systems is a broader segment. Reported funded, unfunded and potential backlog categories are distinct; they are not separate amounts to add to government allocations. Cost/schedule performance and milestone payments could drive margin and cash differently. Virginia workshare and shareholder cash remain unknown.',
  '条件情景：已审查的Virginia／Electric Boat路径内，已获资金工作可能转为交付，但GD Marine Systems涵盖更广业务。报告的已获资金、未获资金及潜在积压类别各有口径，不能作为独立金额再加到政府分配。成本／进度表现及里程碑付款可能使利润与现金走向不同。Virginia份额及股东现金仍未知。',
  'Invalidation: reviewed participation changes, funded backlog fails to convert, or disclosed costs/schedule changes weaken profit or cash. Verify the next Marine backlog categories and execution evidence without assigning all segment totals to Virginia.',
  '失效条件：已审查参与关系改变、已获资金积压未转化，或披露的成本／进度变化削弱利润或现金。核实下一期Marine积压分类及执行证据，不把全部分部金额归于Virginia。')}

_FACT_LABELS={
 'fleet_rms_sales':('sales','销售额'),'fleet_rms_sales_prior':('sales','销售额'),
 'fleet_rms_operating_profit':('operating profit','营业利润'),'fleet_rms_operating_profit_prior':('operating profit','营业利润'),
 'fleet_rms_margin':('margin','利润率'),'fleet_rms_margin_prior':('margin','利润率'),
 'issuer_space_gem63xl_unfavorable_eac':('unfavorable estimated completion-cost adjustment','不利完工成本估计调整'),
 'issuer_space_segment_sales':('sales','销售额'),'issuer_space_segment_sales_prior':('sales','销售额'),
 'issuer_space_segment_operating_profit':('operating profit','营业利润'),'issuer_space_segment_operating_profit_prior':('operating profit','营业利润'),
 'issuer_space_segment_margin':('margin','利润率'),'issuer_space_segment_margin_prior':('margin','利润率'),
 'defense_segment_sales':('sales','销售额'),'marine_segment_sales':('sales','销售额'),
 'defense_segment_operating_profit':('operating profit','营业利润'),'marine_segment_operating_profit':('operating profit','营业利润'),
 'defense_segment_margin':('margin','利润率'),'marine_segment_margin':('margin','利润率'),
 'marine_funded_backlog':('funded backlog','已获资金积压'),
 'marine_unfunded_backlog':('unfunded backlog','未获资金积压'),
 'marine_total_backlog':('total backlog','积压总额'),
 'marine_estimated_potential_contract_value':('estimated potential contracts','估计潜在合同'),
 'marine_total_estimated_contract_value':('total estimated contracts','估计合同总额')}

def _space_reported_comparison(resolved):
 """Interpret only the complete, resolved NOC same-quarter segment comparison.

No ratios or new financial facts are minted. Missing or incompatible operands
leave the ordinary conditional story intact.
 """
 prefix='evt_cik0001133421_2026q2_results:issuer_space_segment_'
 selected=[node for rail,kind,node,_ in resolved if rail=='economics' and kind=='defense_economics' and str(node.get('fact_id','')).startswith(prefix)]
 expected={metric+suffix:('2025Q2' if suffix else '2026Q2','percent' if metric=='margin' else 'USD_million') for metric in ('sales','operating_profit','margin') for suffix in ('','_prior')}
 facts={node['fact_id'][len(prefix):]:node for node in selected}
 if len(selected)!=6 or set(facts)!=set(expected):return None
 for metric,(period,unit) in expected.items():
  node=facts[metric]
  if node.get('period')!=period or node.get('unit')!=unit or node.get('accounting_basis')!='issuer_reported_segment:Space Systems:reported':return None
  if isinstance(node.get('value'),bool) or not isinstance(node.get('value'),(int,float)) or not math.isfinite(node['value']):return None
 if not (facts['sales']['value']>facts['sales_prior']['value'] and facts['operating_profit']['value']<facts['operating_profit_prior']['value'] and facts['margin']['value']<facts['margin_prior']['value']):return None
 comparison=(
  'In the cited NOC Space Systems quarter, sales rose while operating profit and margin fell versus the prior-year quarter. Higher sales did not translate into higher segment profit. These reported segment comparisons do not establish program workshare, capacity, cash generation or shareholder capture.',
  '所引NOC Space Systems季度销售额上升，但营业利润与利润率下降，比较基准为上年同期。销售额增长未转化为更高的分部利润。这些报告分部比较不能证明项目份额、产能、现金生成或股东获益。')
 adverse=[node for rail,kind,node,_ in resolved if rail=='economics' and kind=='defense_economics' and node.get('fact_id')=='evt_cik0001133421_2026q2_results:issuer_space_gem63xl_unfavorable_eac']
 if len(adverse)==1:
  node=adverse[0];value=node.get('value')
  qualified=(node.get('period')=='2026Q2' and node.get('unit')=='USD_million' and node.get('fact_class')=='reported_eac' and node.get('accounting_basis')=='issuer_reported_program_cost_estimate:GEM63XL:unfavorable_EAC' and not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>0)
  if qualified:
   comparison=(comparison[0]+' The separately reported GEM63XL adjustment concerns estimated completion costs; its amount does not establish cash paid or HALO\'s financial effect.',comparison[1]+' 另行报告的GEM63XL调整涉及预计完工成本；该金额不能确认已支付现金或HALO的财务影响。')
 return comparison

def _fleet_reported_comparison(resolved):
 """A complete same-document segment comparison, never fleet allocation."""
 prefix='evt_cik0000936468_2026q2_results:fleet_rms_'
 selected=[node for rail,kind,node,_ in resolved if rail=='economics' and kind=='defense_economics' and str(node.get('fact_id','')).startswith(prefix)]
 expected={metric+suffix:('2025Q2' if suffix else '2026Q2','percent' if metric=='margin' else 'USD_million') for metric in ('sales','operating_profit','margin') for suffix in ('','_prior')}
 facts={node['fact_id'][len(prefix):]:node for node in selected}
 if len(selected)!=6 or set(facts)!=set(expected):return None
 if len({node.get('owner_ref') for node in selected})!=1 or not all(isinstance(node.get('owner_ref'),str) and node['owner_ref'] for node in selected):return None
 for metric,(period,unit) in expected.items():
  node=facts[metric]
  if node.get('period')!=period or node.get('unit')!=unit or node.get('accounting_basis')!='issuer_reported_segment:Rotary and Mission Systems:reported':return None
  if isinstance(node.get('value'),bool) or not isinstance(node.get('value'),(int,float)) or not math.isfinite(node['value']):return None
 if not (facts['sales']['value']>facts['sales_prior']['value'] and facts['operating_profit']['value']>0>facts['operating_profit_prior']['value'] and facts['margin']['value']>0>facts['margin_prior']['value']):return None
 return (
  'In the cited LMT Rotary and Mission Systems quarter, sales were higher and the segment moved from an operating loss to an operating profit versus the prior-year quarter. The prior loss base makes percentage profit growth an unsuitable comparison. This broader segment comparison does not establish F-100 revenue, recurring margin recovery, program workshare, cash generation or shareholder capture. Agreement advancement and a reviewed contract/contractor path remain necessary before any fleet-specific attribution.',
  '所引LMT Rotary and Mission Systems季度销售额高于上年同期，分部由营业亏损转为营业利润。上年亏损基数使利润增长百分比不适合作为比较。这一较广泛分部的比较不能确认F-100收入、持续利润率恢复、项目份额、现金生成或股东获益。在作任何舰队特定归属判断前，仍须确认协议推进以及经过审查的合同与承包商路径。')

def _theme_economic_story(theme_id,resolved):
 """Only successful CURRENT resolved references ground these conditional texts."""
 anchors=[(rail,kind,node) for rail,kind,node,_ in resolved]
 section={'golden_dome':'SEC. 20003','munitions_replenishment':'SEC. 20004','shipbuilding':'SEC. 20002'}.get(theme_id)
 budget=section is not None and any(rail=='funding_stage' and kind=='budget' and isinstance(node,dict) and node.get('section')==section for rail,kind,node in anchors)
 finance=any(rail=='economics' and kind in ('defense_economics','company_intelligence') for rail,kind,node in anchors)
 fms=any(rail=='funding_stage' and kind=='fms' and isinstance(node,dict) and node.get('case_key')=='fms:transmittal:25-104' and node.get('stage')=='congressional_notification' for rail,kind,node in anchors)
 policy=any(rail=='funding_stage' and kind=='program_ontology' and isinstance(node,dict) and node.get('evidence_class')=='official_alliance_policy' and node.get('claim_scopes')==['policy_context'] for rail,kind,node in anchors)
 electric_boat=any(rail=='exposure' and kind=='program_ontology' and isinstance(node,dict) and node.get('program_id')=='acq-program:virginia-class-ssn' and node.get('entity_id')=='legal:gd:electric-boat-corp' and node.get('role')=='prime_contractor' and node.get('verification_state')=='reviewed' for rail,kind,node in anchors)
 prototype=any(rail=='funding_stage' and kind=='program_ontology' and isinstance(node,dict) and node.get('agreement_form')=='firm_fixed_price_ota_prototype' for rail,kind,node in anchors)
 if theme_id=='golden_dome' and prototype:
  return ('Conditional: prototype activity can support development demand, but potential values do not establish delivery timing, production capacity, margins or shareholder capture. Execution costs, milestone acceptance and later funding can interrupt that transmission.',
   '条件性解读：原型活动可形成研发需求，但潜在金额不能证明交付时间、生产产能、利润率或股东收益。执行成本、里程碑验收及后续资金都可能中断传导。',
   'Invalidation: funding, acceptance or launch availability does not advance as expected, or later source evidence changes the scope. Verify native award/legal identities and reported delivery and financial evidence before attribution.',
   '失效条件：资金、验收或发射条件未按预期推进，或后续来源改变范围。归属前需核实原生授予及法律主体身份，以及报告的交付与财务证据。')
 if theme_id=='golden_dome':permitted=budget
 elif theme_id=='space':permitted=finance
 elif theme_id=='nato_fms_demand':permitted=fms and policy
 elif theme_id=='fleet_sustainment_upgrades':permitted=fms
 elif theme_id=='munitions_replenishment':permitted=budget and finance
 else:permitted=budget and finance and electric_boat
 if not permitted:return None
 story=_THEME_CASES[theme_id]
 if theme_id=='space':
  comparison=_space_reported_comparison(resolved)
  if comparison:return comparison+story[2:]
 if theme_id=='fleet_sustainment_upgrades':
  comparison=_fleet_reported_comparison(resolved)
  if comparison:return comparison+story[2:]
 return story

def _reported_baselines(resolved):
 """Exact admitted figures in original issuer/segment/period/unit scope.

Do not sum categories, estimate theme shares or interpret a charge as cash.
"""
 groups={};seen=set()
 for rail,kind,node,owner in resolved:
  if rail!='economics' or kind not in ('defense_economics','company_intelligence'):continue
  metric=node.get('fact_id','').rsplit(':',1)[-1]
  if metric not in _FACT_LABELS or node.get('fact_id') in seen:continue
  seen.add(node['fact_id']);p=owner.payload()
  if kind=='defense_economics':
   profile=next(x for x in p['profiles'] if any(f.get('fact_id')==node['fact_id'] for f in x['axes']['economics']['facts']));name=profile['ticker_display']
  else:name=p['issuer']['display_name']
  basis=node.get('accounting_basis',node.get('basis',''))
  parts=basis.split(':');segment=parts[1] if len(parts)>=3 else basis
  key=(name,node['period'],segment)
  unit={'USD_million':('USD million','百万美元'),'percent':('%','%')}.get(node['unit'])
  if unit is None:continue
  label=_FACT_LABELS[metric];literal=str(node['value'])
  groups.setdefault(key,[]).append((label[0]+' '+literal+' '+unit[0],label[1]+' '+literal+' '+unit[1]))
 en=[];zh=[]
 for (name,period,segment),facts in groups.items():
  en.append(name+' '+segment+' '+period+' reported baseline: '+', '.join(x[0] for x in facts)+'.')
  zh.append(name+' '+segment+' '+period+'报告基准：'+'、'.join(x[1] for x in facts)+'。')
 return ' '.join(en),' '.join(zh)


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
  known_en=[];known_zh=[];next_en=[];next_zh=[];sources=[];missing=[];rail_states={};resolved=[]
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
    try:en,zh,refs=_resolve(ref,rail,owners,item['reason_code'])
    except (ValueError,KeyError,StopIteration):
     rail_states[rail]='source_unavailable';missing.append(rail);continue
    sources+=refs
    node,_=t._pointer(owners[ref['owner_key']].payload(),ref['pointer'])
    resolved.append((rail,owners[ref['owner_key']].owner_kind,node,owners[ref['owner_key']]))
    if rail=='next_event':next_en.append(en);next_zh.append(zh)
    else:known_en.append(en);known_zh.append(zh)
  # Deduplicate only identical public source identities, preserving different claims.
  seen=set();dedup=[]
  for source in sources:
   marker=(source['owner_key'],source['row_id'],source['url'],source['title'])
   if marker not in seen:seen.add(marker);dedup.append(source)
  unavailable=list(dict.fromkeys(missing))
  baseline_en,baseline_zh=_reported_baselines(resolved)
  if baseline_en:known_en.append(baseline_en);known_zh.append(baseline_zh)
  story=_theme_economic_story(theme['theme_id'],resolved)
  missing_en='Unresolved: '+', '.join(RAIL_EN[k] for k in unavailable)+'.' if unavailable else 'All required rails have qualified context.'
  missing_zh='尚未解决：'+ '、'.join(RAIL_ZH[k] for k in unavailable)+'。' if unavailable else '所有必需栏目均有合格背景。'
  if theme['rails']['market_context']['reason_code']=='shared_defense_basket_not_theme_portfolio':
   missing_en+=' Theme-specific market membership and returns remain unqualified; the shared basket is broad context only.'
   missing_zh+=' 主题专属市场成员及回报尚未核实；共享篮子仅为广泛背景。'
  if story:
   missing_en+=' '+story[0];missing_zh+=' '+story[1]
   next_en.append(story[2]);next_zh.append(story[3])
  out.append(dict(theme_id=theme['theme_id'],rail_states=rail_states,known_en=' '.join(dict.fromkeys(known_en)) or 'No qualified current source evidence is available for this theme.',known_zh=' '.join(dict.fromkeys(known_zh)) or '此主题暂无合格的当前来源证据。',missing_en=missing_en,missing_zh=missing_zh,next_en=' '.join(dict.fromkeys(next_en)) or NEXT[theme['theme_id']][0],next_zh=' '.join(dict.fromkeys(next_zh)) or NEXT[theme['theme_id']][1],sources=dedup,research_state='SOURCE_CONTEXT_COMPLETE' if all(s=='supported' for s in rail_states.values()) else 'EVIDENCE_INSUFFICIENT'))
 version='1.1.0' if any(source['documentary_class']=='prototype_agreement' for theme in out for source in theme['sources']) else '1.0.0'
 result=dict(contract=CONTRACT,schema_version=version,content_id='',theme_content_id=payload['content_id'],as_of=payload['as_of'],authority=dict(t.AUTHORITY),themes=out)
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
   raw=retained_owners[key].raw_bytes if ref['owner_kind']=='company_intelligence' else target.read_bytes();p=json.loads(raw);current=dict(state='available',sha256=sha256(raw).hexdigest(),content_id=p.get('content_id'),owner_alias_state='unchanged')
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
 schemas={'1.0.0':'government_program_theme_public_disclosure.v1.schema.json','1.1.0':'government_program_theme_public_disclosure.v1_1.schema.json'}
 if not isinstance(payload,dict) or payload.get('schema_version') not in schemas:raise ValueError('public_theme_shape_invalid')
 schema=json.loads((t._SCHEMA_ROOT/schemas[payload['schema_version']]).read_text())
 if next(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(payload),None) is not None:raise ValueError('public_theme_shape_invalid')
 if [row['theme_id'] for row in payload['themes']]!=list(t.THEMES) or payload['content_id']!=disclosure_content_id(payload):raise ValueError('public_theme_identity_invalid')
 for row in payload['themes']:
  expected='SOURCE_CONTEXT_COMPLETE' if all(s=='supported' for s in row['rail_states'].values()) else 'EVIDENCE_INSUFFICIENT'
  if row['research_state']!=expected:raise ValueError('public_theme_state_invalid')
  classes={'congressional_notification':('congressional_notification_only',{'www.dsca.mil','www.state.gov'}),'alliance_policy':('policy_commitment_only',{'www.nato.int'}),'allocation_plan':('allocation_plan_only',{'comptroller.war.gov','comptroller.defense.gov'}),'prototype_agreement':('prototype_agreement_only',{'www.sda.mil','www.l3harris.com'})}
  for source in row['sources']:
   cls=source['documentary_class']
   if cls=='prototype_agreement' and (payload['schema_version']!='1.1.0' or row['theme_id']!='golden_dome' or any(source[k] is not None for k in ('program_id','issuer_id','security_id'))):raise ValueError('public_prototype_attribution_promotion')
   if cls is None:
    if source['native_reason_code'] is not None:raise ValueError('public_native_class_invalid')
   else:
    reason,hosts=classes[cls]
    if source['native_reason_code']!=reason:raise ValueError('public_native_class_invalid')
    _primary(source['url'],hosts)
  if row['rail_states']['funding_stage']=='supported' and any(s['documentary_class'] is not None for s in row['sources']):raise ValueError('public_documentary_stage_promotion')
 return True
