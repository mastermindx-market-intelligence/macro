"""Artifact proposal: allocation-plan document context under existing budget owner.

Appends documentary context to the incumbent graph, without P1/R1 identity,
new stores, source acquisition, financial allocation, or arithmetic. Production
publication additionally requires the existing object's verified storage receipt.
"""
from copy import deepcopy
from decimal import Decimal
from datetime import datetime
from hashlib import sha256
import json,re
from functools import lru_cache
from urllib.parse import urlsplit

CONTRACT='government_revenue.dod_budget_collection_receipt.v1'
SCHEMA_VERSION='1.1.0'
KIND='legislative_allocation_spend_plan'
STAGE='allocation_plan'
REVIEWED_EDITION_SHA256='4dcd91ae15ea37508d0d77b9fa67139c5dcf2e909b946b9339b9358cc217fd2f'
REVIEWED_SOURCE_URL='https://comptroller.war.gov/Portals/45/Documents/news/FY2026_Mandatory_Funding_Allocation_Plan.pdf'
SECTIONS={'20002':'Enhancement of Department of Defense Resources for Shipbuilding','20003':'Enhancement of Department of Defense Resources for Integrated Air and Missile Defense','20004':'Enhancement of Department of Defense Resources for Munitions and Defense Supply Chain Resiliency'}
AUTHORITY=dict(tier='display',context_only=True,can_rank=False,can_size=False,can_gate=False,can_originate_signal=False,can_add_candidates=False,can_escalate=False)

def _json(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def _sha(x):return sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def _instant(x):
 try:d=datetime.fromisoformat(x.replace('Z','+00:00'))
 except (ValueError,AttributeError):raise ValueError('allocation_clock_invalid') from None
 if d.tzinfo is None:raise ValueError('allocation_clock_invalid')
 return d

def _url(x):
 if not isinstance(x,str):raise ValueError('allocation_source_invalid')
 p=urlsplit(x)
 if p.scheme!='https' or p.hostname not in {'comptroller.war.gov','comptroller.defense.gov'} or p.username or p.password or p.query or p.fragment or not p.path.lower().endswith('.pdf'):raise ValueError('allocation_source_invalid')
 return x

def receipt_id(receipt):return 'dod-budget:'+_sha(_json({k:v for k,v in receipt.items() if k!='receipt_id'}))
def context_id(document):return 'dod-budget-context:'+_sha(_json({k:v for k,v in document.items() if k!='context_id'}))[:24]

@lru_cache(maxsize=2)
def _extract(pdf_bytes):
 from collectors.dod_budget_live import extract_pages
 return extract_pages(pdf_bytes)

def build_allocation_plan_receipt(*,source_url,final_url,pdf_bytes,observed_at,known_at,source_document_date,source_published_at=None,storage_receipt=None):
 """Replay local public bytes; never pretend local evidence proves R2 admission."""
 source_url=_url(source_url);final_url=_url(final_url)
 if source_url!=final_url or source_url!=REVIEWED_SOURCE_URL:raise ValueError('allocation_source_redirect_or_edition_requires_review')
 if not isinstance(pdf_bytes,bytes) or not pdf_bytes.startswith(b'%PDF'):raise ValueError('allocation_pdf_invalid')
 if _instant(observed_at)>_instant(known_at):raise ValueError('allocation_known_backdated')
 if source_published_at is not None and _instant(source_published_at)>_instant(observed_at):raise ValueError('allocation_publication_after_observation')
 if _sha(pdf_bytes)!=REVIEWED_EDITION_SHA256:raise ValueError('allocation_unreviewed_edition')
 if source_document_date!='2026-05-04':raise ValueError('allocation_cover_date_mismatch')
 if not isinstance(source_document_date,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',source_document_date):raise ValueError('allocation_document_date_invalid')
 from collectors.dod_budget_live import EXTRACTOR_VERSION as owner_extractor
 extracted=_extract(pdf_bytes);pages=list(extracted.page_texts)
 body='\n'.join(pages)
 if 'FY 2026 Mandatory Funding Allocation Plan' not in body or 'SECTION 20003: MISSILE DEFENSE' not in ' '.join(body.split()):raise ValueError('allocation_document_edition_unqualified')
 digest=_sha(pdf_bytes);hashes=[_sha(p) for p in pages]
 from collectors.dod_budget import IMMUTABLE_R2_PREFIX,EXTRACTOR_VERSION,PUBLISHER,_extraction_semantic_sha256
 state='local_evidence_only'
 if storage_receipt is not None:
  if set(storage_receipt)!={'state','object_key','sha256','byte_count','verified_at'} or storage_receipt.get('state')!='owner_object_verified' or storage_receipt.get('object_key')!=f'{IMMUTABLE_R2_PREFIX}{digest}.pdf' or storage_receipt.get('sha256')!=digest or storage_receipt.get('byte_count')!=len(pdf_bytes) or _instant(storage_receipt.get('verified_at'))>_instant(known_at):raise ValueError('allocation_storage_binding_invalid')
  state='owner_object_verified'
 receipt=dict(contract=CONTRACT,schema_version=SCHEMA_VERSION,receipt_id='',publisher=PUBLISHER,fiscal_year=2026,document_kind=KIND,document_stage=STAGE,exhibit=None,source_url=source_url,final_url=final_url,source_document_date=source_document_date,source_document_date_basis='reviewed_scanned_cover_letter',source_published_at=source_published_at,observed_at=observed_at,known_at=known_at,content_sha256=digest,page_count=len(pages),page_text_sha256s=hashes,extraction_semantic_sha256=_extraction_semantic_sha256(hashes),immutable_object_key=f'{IMMUTABLE_R2_PREFIX}{digest}.pdf',request_sha256=_sha(_json({'source_url':source_url})),response_sha256=digest,extractor_version=owner_extractor,parser_version='dod-budget-allocation-document-context.v1',raw_response_bodies_persisted=False,storage_state=state,storage_receipt=deepcopy(storage_receipt))
 receipt['receipt_id']=receipt_id(receipt)
 return receipt,pages

def validate_allocation_plan_receipt(receipt,*,pdf_bytes):
 if not isinstance(receipt,dict) or receipt.get('contract')!=CONTRACT or receipt.get('schema_version')!=SCHEMA_VERSION:raise ValueError('allocation_receipt_contract_invalid')
 expected,pages=build_allocation_plan_receipt(source_url=receipt.get('source_url'),final_url=receipt.get('final_url'),pdf_bytes=pdf_bytes,observed_at=receipt.get('observed_at'),known_at=receipt.get('known_at'),source_document_date=receipt.get('source_document_date'),source_published_at=receipt.get('source_published_at'),storage_receipt=receipt.get('storage_receipt'))
 if receipt!=expected:raise ValueError('allocation_receipt_replay_mismatch')
 return pages

def _table_row(page,section):
 start=page.find('SEC. '+section+'.')
 if start<0:raise ValueError('allocation_section_missing')
 tail=page[start:];end=tail.find('SEC. ',len('SEC. '+section+'.'))
 if end>=0:tail=tail[:end]
 token=r'(?<![A-Za-z0-9])(?:[0-9][0-9,]*\.[0-9]+|-)(?![A-Za-z0-9])'
 values=re.findall(token,tail)
 title=' '.join(re.sub(token,' ',tail).split())
 if title!='SEC. '+section+'. '+SECTIONS[section]:raise ValueError('allocation_section_title_invalid')
 if len(values)!=6:raise ValueError('allocation_columns_invalid')
 return start,start+len(tail),tail,values

def project_allocation_document(receipt,*,pdf_bytes,sections=('20003',)):
 pages=validate_allocation_plan_receipt(receipt,pdf_bytes=pdf_bytes)
 if not isinstance(sections,(tuple,list)) or not sections or len(sections)!=len(set(sections)) or any(s not in SECTIONS for s in sections):raise ValueError('allocation_section_identity_invalid')
 hits=[i for i,p in enumerate(pages) if 'Figure 1. Summary ($ in Millions)' in p]
 if len(hits)!=1:raise ValueError('allocation_summary_page_ambiguous')
 i=hits[0];page=pages[i]
 if not all('FY '+str(year) in page for year in range(2025,2030)):raise ValueError('allocation_year_columns_invalid')
 if '($ in Millions)' not in page:raise ValueError('allocation_unit_unqualified')
 rows=[]
 for section in sections:
  start,end,span,values=_table_row(page,section)
  span_start=len(page[:start].encode());span_end=len(page[:end].encode())
  # The incumbent extractor's source coordinates bind values to fiscal columns.
  words=_extract(pdf_bytes).page_words[i]
  marks=[w for w in words if re.fullmatch(r'2000[1-8]\.',str(w['text']))]
  mark=next(w for w in marks if w['text']==section+'.')
  lower=mark['top'];upper=min([w['top'] for w in marks if w['top']>lower]+[9999])
  cells=sorted([w for w in words if lower<=w['top']<upper and w['x0']>330 and re.fullmatch(r'-|[0-9][0-9,]*\.[0-9]+',str(w['text']))],key=lambda w:w['x0'])
  headers=sorted([w for w in words if str(w['text']) in ('2025','2026','2027','2028','2029','Total*') and 270<w['top']<305],key=lambda w:w['x0'])
  if len(cells)!=6 or [w['text'] for w in cells]!=values or [w['text'] for w in headers]!=['2025','2026','2027','2028','2029','Total*']:raise ValueError('allocation_column_geometry_unqualified')
  centers=[(w['x0']+w['x1'])/2 for w in headers]
  bounds=[330]+[(centers[n]+centers[n+1])/2 for n in range(5)]+[740]
  if any(not bounds[n]<=(w['x0']+w['x1'])/2<bounds[n+1] for n,w in enumerate(cells)):raise ValueError('allocation_year_column_binding_invalid')
  column_proof=dict(headers=[w['text'] for w in headers],cells=[{k:w[k] for k in ('text','x0','x1','top','bottom')} for w in cells])
  money=[]
  for year,value in zip([2025,2026,2027,2028,2029,None],values):
   money.append(dict(fiscal_year=year,value=None if value=='-' else str(Decimal(value.replace(',',''))),source_literal=value,amount_kind='allocation_plan_fiscal_year' if year is not None else 'printed_section_total',currency='USD',unit='USD_million'))
  rows.append(dict(section='SEC. '+section,native_title=SECTIONS[section],document_stage=STAGE,amounts=money,program_key=None,issuer_ref=None,economic_weight=None,source_span=dict(pdf_page_1based=i+1,printed_page_label='1',span_start_byte=span_start,span_end_byte=span_end,text_sha256=_sha(span),page_text_sha256=receipt['page_text_sha256s'][i],receipt_state='byte_replayed',column_proof=column_proof)))
 document=dict(receipt_id=receipt['receipt_id'],fiscal_year=2026,exhibit=None,document_kind=KIND,document_stage=STAGE,source_url=receipt['source_url'],content_sha256=receipt['content_sha256'],page_count=receipt['page_count'],page_text_sha256s=receipt['page_text_sha256s'],extraction_semantic_sha256=receipt['extraction_semantic_sha256'],extractor_version=receipt['extractor_version'],parser_version=receipt['parser_version'],observed_at=receipt['observed_at'],known_at=receipt['known_at'],source_document_date=receipt['source_document_date'],source_document_date_basis=receipt['source_document_date_basis'],source_published_at=receipt['source_published_at'],context_id='',storage_state=receipt['storage_state'],allocations=rows)
 document['context_id']=context_id(document);return document

def validate_allocation_document(document,*,receipt,pdf_bytes):
 if not isinstance(document,dict) or not isinstance(document.get('allocations'),list):raise ValueError('allocation_document_invalid')
 try:sections=[x['section'].removeprefix('SEC. ') for x in document['allocations']]
 except (TypeError,KeyError,AttributeError):raise ValueError('allocation_document_invalid') from None
 if document!=project_allocation_document(receipt,pdf_bytes=pdf_bytes,sections=sections):raise ValueError('allocation_document_replay_mismatch')
 return True

def compose_allocation_context_graph(base_graph,*,receipt,pdf_bytes,sections=('20003',),generated_at,as_of,require_storage=True):
 """Extend the SAME canonical graph; validate/replay before existing publisher."""
 from engine.government_revenue.budget_program import is_valid_budget_program_graph,budget_program_graph_content_id
 if not is_valid_budget_program_graph(base_graph):raise ValueError('incumbent_budget_graph_invalid')
 cutoff=_instant(as_of+'T23:59:59+00:00')
 if _instant(receipt['known_at'])>cutoff or _instant(generated_at)<_instant(receipt['known_at']):raise ValueError('allocation_cutoff_invalid')
 if require_storage and receipt.get('storage_state')!='owner_object_verified':raise ValueError('allocation_existing_object_write_readback_required')
 context=project_allocation_document(receipt,pdf_bytes=pdf_bytes,sections=sections)
 prior=[d for d in base_graph['documents'] if d.get('document_kind')==KIND]
 if prior and not any(d==context for d in prior):raise ValueError('allocation_context_revision_requires_review')
 out=deepcopy(base_graph);out['schema_version']='1.1.0';
 if not prior:out['documents'].append(context)
 out['generated_at']=generated_at;out['as_of']=as_of;out['known_at']=max([base_graph['known_at'],receipt['known_at']],key=_instant)
 out['source_coverage']['legislative_allocations']=dict(status='partial',reason='Reviewed section allocations only; allocation plan is not proof of appropriation, obligation, outlay, contract, backlog or revenue.')
 if not prior:out['limitations'].append('Legislative allocation documents are context only: no P1/PE acquisition identity, issuer allocation or cross-stage summation; printed totals are not added to fiscal-year rows.')
 out['content_id']=budget_program_graph_content_id(out)
 return out

def allocation_context_display(document):
 """Public read-model adapter prevents omission or stage mislabel in consumers."""
 if not isinstance(document,dict) or document.get('document_kind')!=KIND or document.get('document_stage')!=STAGE or document.get('exhibit') is not None or document.get('context_id')!=context_id(document):raise ValueError('allocation_display_invalid')
 return dict(context_id=document['context_id'],stage='allocation_plan',label_en='Legislative allocation plan — documentary context',label_zh='立法资金分配计划 — 文件背景',source_url=document['source_url'],source_published_at=document['source_published_at'],house_known_at=document['known_at'],section_refs=[dict(section=r['section'],native_title=r['native_title'],pointer='/allocations/'+str(i)) for i,r in enumerate(document['allocations'])],limitation_en='This plan does not prove obligation, outlay, contract revenue or issuer workshare.',limitation_zh='该计划不能证明义务支出、实际支付、合同收入或发行人份额。')

ALLOCATION_RECEIPT_PATH='data/government_revenue/dod_budget_allocation_context_receipt.json'

def load_collected_allocation_context_input(root,*,store=None):
 """Existing collected-data receipt + exact already-stored owner body.

No source URL GET or collector schedule is involved. Call before existing
canonical/twin publisher. Absent receipt is absent; corrupt/denied reads fail.
"""
 from pathlib import Path
 root=Path(root).resolve();path=root/ALLOCATION_RECEIPT_PATH
 if not path.is_file():return None
 receipt=json.loads(path.read_bytes())
 if receipt.get('storage_state')!='owner_object_verified':raise ValueError('allocation_source_not_admitted')
 from collectors.dod_budget_live import build_default_store
 backend=store if store is not None else build_default_store()
 if backend is None:raise ValueError('allocation_existing_source_store_unavailable')
 count=(receipt.get('storage_receipt') or {}).get('byte_count')
 if not isinstance(count,int) or isinstance(count,bool) or not 0<count<=16*1024*1024:raise ValueError('allocation_stored_byte_count_invalid')
 body=backend.get_bytes_strict_bounded(receipt['immutable_object_key'],expected_byte_length=count,max_byte_length=count)
 if body is None:raise ValueError('allocation_existing_source_object_missing')
 validate_allocation_plan_receipt(receipt,pdf_bytes=body)
 return receipt,body
