"""Bounded supplemental documents in the incumbent Event Workspace owner.

Native SEC filings and issuer publications retain different source identities.
The existing disclosure normalizer and SourceDocument/text_span/replay owner
provide all parsing and receipts. No EX99 identity or clock is reused.
"""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlparse
from engine.fundamental_forensics.disclosure_diff import normalize_filing
from engine.company_intelligence.documents import SourceDocument,text_span,verify_span
from engine.company_intelligence.contracts import canonical_json_bytes
from engine.company_intelligence.documents import FilingKey
from engine.earnings_release.receipts import receipt_for_char_span,replay_receipt
from engine.company_intelligence.event_workspace import validate_event_workspace,_strip_private,_ceil_second


def _instant(value):
    result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('supplement_clock_timezone_required')
    return result


def _rules(kind):
    if kind=='LMT_RMS':return ()  # Numeric cells have their own closed table rules.
    if kind=='LHX_10Q':return (
        ('msl_preferred_payout_terms','Subsidiary Series A Preferred Stock payout options include',None,'reported_shareholder_terms','contractual_preferred_terms:conditional_alternatives'),
        ('msl_qipo_conversion_terms','Conversion Upon QIPO.',None,'company_forward','contractual_preferred_conversion:conditional_QIPO'),
        ('msl_nonipo_redemption_terms','Non-IPO Redemption.',None,'reported_shareholder_terms','contractual_preferred_redemption:conditional_no_QIPO'),
        ('space_business_sale_pending_terms','During fourth quarter 2025, we entered into an agreement with AE Industrial Partners',None,'reported_shareholder_terms','business_disposal:pending:net_enterprise_value'),
        ('space_business_sale_pending_accounting','Upon closing, we will derecognize the assets and liabilities of the Space Technology disposal group',None,'reported_shareholder_terms','business_disposal:conditional_equity_method_accounting'),
    )
    if kind=='LHX_sale':return (
        ('space_business_sale_completed_terms','has completed the sale of a majority stake','commercial space propulsion','reported_shareholder_terms','business_disposal:completed:total_enterprise_value'),
        ('space_business_sale_retained_scope','RS-25 rocket engine operations were excluded','Rocketdyne','reported_shareholder_terms','business_disposal:completed:retained_interest_scope'),
    )
    raise ValueError('unsupported_supplement_profile')


def build_issuer_supplement(*,kind,body,url,filing,event_id,period,observed_at,source_available_at,expected_sha256,prior=None):
    """Closed curator-selected profiles, native identities, exact-byte facts.

    The SEC source_available_at comes from its native submissions row. Issuer
    publication lacks a proved time of day, so available_at conservatively
    uses actual retrieval, published_at remains unknown; its printed date is
    a claim in the source, not a guessed midnight timestamp.
    """
    raw=body.encode();digest=sha256(raw).hexdigest()
    if digest!=expected_sha256:raise ValueError('supplement_body_hash_mismatch')
    observed=_instant(observed_at);available=_instant(source_available_at)
    if observed<available:raise ValueError('supplement_observation_precedes_availability')
    parsed=urlparse(url)
    if parsed.scheme!='https':raise ValueError('supplement_origin_unqualified')
    native=None
    if kind=='LHX_10Q':
        if parsed.hostname!='www.sec.gov' or filing.get('form')!='10-Q' or filing.get('cik')!='0000202058':raise ValueError('supplement_filing_subject_form_mismatch')
        native=FilingKey(cik=filing['cik'],accession=filing['accession'])
        prefix=f'/Archives/edgar/data/202058/{native.accession.replace("-","")}/'
        if not parsed.path.startswith(prefix) or parsed.path.rsplit('/',1)[-1]!=filing.get('primary_document'):raise ValueError('supplement_native_url_mismatch')
        if _instant(filing['acceptance_datetime'])!=available:raise ValueError('supplement_SEC_available_clock_mismatch')
        parser_id=native.accession
    elif kind=='LHX_sale':
        if parsed.hostname!='investors.l3harris.com' or filing is not None:raise ValueError('issuer_publication_not_native_SEC_filing')
        if available!=observed:raise ValueError('issuer_publication_availability_time_unproved')
        parser_id=url # parser input identity is a URI, never a SEC accession
    elif kind=='LMT_RMS':
        from engine.company_intelligence.rms_segment_profile import URL,EVENT
        if not isinstance(filing,dict) or url!=URL or event_id!=EVENT or period!='2026Q2':
            raise ValueError('RMS_source_event_period_mismatch')
        if filing.get('cik')!='0000936468' or filing.get('accession')!='0001628280-26-049277' or filing.get('form')!='8-K':
            raise ValueError('RMS_native_filing_identity_mismatch')
        if filing.get('filing_date')!='2026-07-23' or filing.get('report_date')!='2026-07-23':
            raise ValueError('RMS_native_filing_date_mismatch')
        if _instant(filing.get('acceptance_datetime'))!=_instant('2026-07-23T10:30:57Z') or observed<_instant(filing['acceptance_datetime']):
            raise ValueError('RMS_native_filing_acceptance_mismatch')
        if available!=observed:raise ValueError('RMS_changed_byte_version_requires_actual_retrieval_clock')
        # SourceDocument serializes whole seconds. Reuse the native conservative
        # boundary rather than expose this observation before its real capture.
        observed=available=_ceil_second(observed)
        native=FilingKey(cik=filing['cik'],accession=filing['accession'])
        parser_id=native.accession
    else:raise ValueError('supplement_profile_unsupported')
    doc=normalize_filing({'content':body,'accession':parser_id,'entity_cik':native.cik if native else '0000202058',
        'form':filing['form'] if native else None,'filed_at':filing['filing_date'] if native else None,
        'report_date':filing['report_date'] if native else None,'source_url':url})
    if kind=='LHX_10Q' and not any(f'For Second Quarter {period[:4]}'==b.text for b in doc.blocks):raise ValueError('supplement_current_period_not_source_qualified')
    if kind=='LHX_sale' and not any(b.text=='August 4, 2026' for b in doc.blocks):raise ValueError('supplement_publication_date_not_source_qualified')
    document_id=doc.document_id
    revision=1;supersedes=None
    if prior is not None:
        validate_supplement_source(prior,event_id=event_id)
        if prior['supplement_profile']!=kind or prior['url']!=url or prior['source_document']['presented_fiscal_label']!=period:
            raise ValueError('prior_supplement_association_mismatch')
        old_doc=prior['source_document']
        same=prior.get('document_id')==document_id and prior.get('source_sha256')==digest
        if same:
            prior_clock=_instant(prior['source_clock']['observed_at'])
            if native is None or kind=='LMT_RMS':available=_instant(prior['source_clock']['available_at'])
            if prior_clock>observed or prior_clock<available.replace(microsecond=0):raise ValueError('prior_supplement_clock_invalid')
            observed=prior_clock;revision=old_doc['revision'];supersedes=old_doc['supersedes_document_id']
        else:
            # The existing document revision contract, not a second ledger:
            # qualify new bytes again, preserve old immutable generation, and
            # link the new SourceDocument to its exact prior document ID.
            revision=old_doc['revision']+1;supersedes=old_doc['document_id']
    source_doc=SourceDocument(document_id=document_id,event_id=event_id,revision=revision,supersedes_document_id=supersedes,document_kind='filing' if native else 'supplement',source_class='primary_filing' if native else 'issuer_release',content_sha256=digest,content_bytes=len(raw),filing_key=native,fetched_at=observed,available_at=available,rights_profile='rp_public_primary_v1',rights_state='public_primary',presented_fiscal_label=period)
    facts=[]
    for metric,phrase,second,fact_class,basis in _rules(kind):
        blocks=[b for b in doc.blocks if not b.table and phrase in b.text and (second is None or second in b.text)]
        if len(blocks)!=1:raise ValueError('supplement_clause_missing_or_ambiguous:'+metric)
        block=blocks[0]
        if len(block.text)>2000:raise ValueError('supplement_clause_exceeds_closed_fact_limit')
        receipt=receipt_for_char_span(source=body,source_sha256=digest,char_start=block.source_span.char_start,char_end=block.source_span.char_end)
        replay_receipt(receipt,source=body)
        span=text_span(document_id=document_id,document_version=1,body_sha256=digest,segment_index=0,segment_text=body,start_byte=receipt.byte_start,end_byte=receipt.byte_end,text=receipt.span_text,rights_profile='rp_public_primary_v1')
        verify_span(span,segment_text=body,body_sha256=digest)
        facts.append({'schema':'event_fact.v1','fact_id':event_id+':'+metric,'event_id':event_id,'metric':metric,'value':block.text,'unit':'source_reported_terms','period':period,'basis':basis,'fact_class':fact_class,'source_span':span.to_payload()})
    if kind=='LMT_RMS':
        from engine.company_intelligence.rms_segment_profile import numeric_facts
        facts=numeric_facts(document=doc,body=body,digest=digest,event_id=event_id)
    source={'kind':'issuer_supplement','supplement_profile':kind,'document_id':document_id,'source_sha256':digest,'url':url,'form':filing['form'] if native else None,'filing_key':native.to_payload() if native else None,'receipt_state':'byte_replayed','source_document':source_doc.to_payload(),'source_clock':{'available_at':source_doc.to_payload()['available_at'],'observed_at':source_doc.to_payload()['fetched_at']},'printed_publication_date':'2026-08-04' if not native else None,'availability_basis':'native_SEC_acceptance' if native else 'conservative_actual_retrieval_no_publication_time_claim'}
    if kind=='LMT_RMS':
        from engine.company_intelligence.rms_segment_profile import AVAILABILITY
        source['availability_basis']=AVAILABILITY
    return {'source':source,'facts':facts}


def append_issuer_supplements(workspace,supplements):
    """Append owner-qualified documents; leave original EX99 lifecycle intact."""
    output=deepcopy(workspace)
    for supplement in supplements:
        source=supplement['source'];document=source['source_document']
        if document['event_id']!=output['event_id']:raise ValueError('supplement_event_mismatch')
        subject={'LHX_10Q':'cik:0000202058','LHX_sale':'cik:0000202058','LMT_RMS':'cik:0000936468'}.get(source.get('supplement_profile'))
        if subject is None or output['issuer']['company_id']!=subject:raise ValueError('supplement_workspace_subject_mismatch')
        if source.get('supplement_profile')=='LMT_RMS' and (output['fiscal_period']['year'],output['fiscal_period']['quarter'])!=(2026,2):
            raise ValueError('RMS_workspace_fiscal_period_mismatch')
        validate_supplement_source(source,event_id=output['event_id'])
        existing=[s for s in output['sources'] if s.get('document_id')==source['document_id']]
        if existing:raise ValueError('duplicate_supplement_document')
        output['sources'].append(source)
        for fact in supplement['facts']:
            if fact['event_id']!=output['event_id'] or fact['source_span']['document_id']!=source['document_id']:raise ValueError('supplement_fact_document_mismatch')
            output['facts'].append(fact)
    # New owner-build rows are intentionally unstamped until the incumbent
    # generation writer validates/stamps them. Existing rows validate now.
    if output.get("generation_id"):
        validate_event_workspace(_strip_private(output))
    return output


def validate_supplement_source(source,*,event_id):
    """Closed source-document proof used by the existing generation owner."""
    if source.get('kind')!='issuer_supplement' or source.get('supplement_profile') not in ('LHX_10Q','LHX_sale','LMT_RMS'):raise ValueError('supplement_source_kind_unqualified')
    doc=source.get('source_document') or {}
    required={'schema','authority','document_id','event_id','document_kind','source_class','revision','content_sha256','content_bytes','filing_key','fetched_at','published_at','available_at','supersedes_document_id','superseded_by_document_id','rights_profile','rights_state','presented_fiscal_label','holds_bytes'}
    if set(doc)!=required or doc.get('schema')!='source_document.v1' or doc.get('authority')!='context_only' or doc.get('event_id')!=event_id or doc.get('document_id')!=source.get('document_id') or doc.get('content_sha256')!=source.get('source_sha256') or doc.get('rights_profile')!='rp_public_primary_v1' or doc.get('rights_state')!='public_primary' or doc.get('holds_bytes') is not True or source.get('receipt_state')!='byte_replayed':raise ValueError('supplement_source_document_unqualified')
    native=FilingKey(**doc['filing_key']) if doc['filing_key'] else None
    kwargs={k:v for k,v in doc.items() if k not in ('schema','authority','filing_key')};kwargs['filing_key']=native
    SourceDocument(**kwargs)
    if doc['filing_key']!=source.get('filing_key'):raise ValueError('supplement_filing_key_mismatch')
    clock=source.get('source_clock') or {}
    if set(clock)!={'observed_at','available_at'}:raise ValueError('supplement_source_clock_unqualified')
    observed,available=_instant(clock['observed_at']),_instant(clock['available_at'])
    if observed<available or observed!=_instant(doc['fetched_at']) or available!=_instant(doc['available_at']):raise ValueError('supplement_source_clock_mismatch')
    origin=urlparse(source.get('url') or '')
    if source['supplement_profile']=='LHX_10Q':
        if native is None or native.cik!='0000202058' or source.get('form')!='10-Q' or origin.hostname!='www.sec.gov' or not origin.path.startswith('/Archives/edgar/data/202058/'+native.accession.replace('-','')+'/') or source.get('availability_basis')!='native_SEC_acceptance':raise ValueError('supplement_SEC_native_identity_unqualified')
    elif source['supplement_profile']=='LMT_RMS':
        from engine.company_intelligence.rms_segment_profile import URL,EVENT,AVAILABILITY
        if (event_id!=EVENT or native is None or native.cik!='0000936468'
                or native.accession!='0001628280-26-049277' or source.get('form')!='8-K'
                or source.get('url')!=URL or doc['presented_fiscal_label']!='2026Q2'
                or doc['document_kind']!='filing' or doc['source_class']!='primary_filing'
                or doc['published_at'] is not None or observed!=available
                or source.get('availability_basis')!=AVAILABILITY):
            raise ValueError('RMS_source_identity_availability_unqualified')
    elif native is not None or source.get('form') is not None or origin.hostname!='investors.l3harris.com' or doc['published_at'] is not None or observed!=available or source.get('availability_basis')!='conservative_actual_retrieval_no_publication_time_claim':raise ValueError('issuer_source_identity_availability_unqualified')
    return observed,available
