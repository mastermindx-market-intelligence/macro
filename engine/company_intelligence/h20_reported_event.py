"""One retained public SEC reported event, using incumbent native receipts.

No collector, workspace, store, publication or HTTP input surface. The host
loads the fixed protected records after entitlement and supplies the already
provisioned PinnedSourceAuthority. New fact adoption is recorded in the pinned
source decision, never inferred from filing/retrieval or restamped per request.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

import yaml

from . import issuer_disclosures as native
from .issuer_disclosure_owner import _json as owner_record_from_bytes
from .documents import FilingKey, SourceDocument, text_span, verify_span
from .events import FiscalPeriod, canonical_event_id
from ..earnings_release.receipts import visible_text
from ..fundamental_forensics.filing_attestation import PinnedSourceAuthority, gzip_stored_byte_ceiling
from ..fundamental_forensics.sec_document_spine import manifest_from_json_bytes

DECISION_PATH = 'research/theme_graph/sec_h20_20261019/H20_REPORTED_EVENT_OWNER_DECISION.json'
POLICY_PATH = 'research/theme_graph/sec_h20_20261019/SEC_H20_REPORTED_EVENT_FACT_USE.json'
SOURCE_PATHS = (DECISION_PATH, POLICY_PATH, 'config/theme_sources.yml')
DECISION_SHA256 = '95d5236c4f6d27ab59b5d91c6cc7bef5796561daea969a0142b84c4973aff4fa'
POLICY_SHA256 = '3eb4b90a1c9524e8fbb25a4823dd31ab5515c96ea2b38b9e6dbddeb87118a77e'
RAW_SHA256 = '94f539316ae2a9ff625357cf01008cb77b930d1a6a228326f04a3ce5f5a56d2e'
RAW_BYTES = 1967931
SPAN_START, SPAN_END = 258290, 258509
SPAN_SHA256 = '5eb432e03c7e95667e7356e5adc3b4c0ae8f80919d34cba5e6a33b64f85a296c'
SNAPSHOT_ID = 'ffsecsrc_520d816415a2d1dbde1fcf348abef2cbfdd8b28b88b4bf847a549613002d02ee'
MANIFEST_KEY = 'manifests/0001045810/0001045810-26-000021/ffsec_manifest_f050d1fb989d8f840c4291c5eb8b12788f1110bea58bf3b5b4ce239c8a771a61.json'
CIK, ACCESSION = '0001045810', '0001045810-26-000021'
DOCUMENT_ID = 'sec_document_5b75587074cf7849d010ec05a7ae7a18d305326a50418897d5d0bc75423bb26a'
URL = 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm'
PURPOSE, AUDIENCE = 'private_company_intelligence_context', 'company_intelligence_entitled'
_TOKEN = object()


class ReportedEventError(ValueError):
    """Closed refusal token; no body, path, parser error or source prose."""


def _require(condition, reason):
    if not condition:
        raise ReportedEventError(reason)


def _now():
    return datetime.now(timezone.utc)


def _instant(value):
    _require(type(value) is str and 'T' in value, 'H20_CLOCK_INVALID')
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        _require(result.tzinfo is not None, 'H20_CLOCK_INVALID')
        return result.astimezone(timezone.utc)
    except (TypeError,ValueError):
        raise ReportedEventError('H20_CLOCK_INVALID') from None


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


@dataclass(frozen=True, slots=True, init=False)
class QualifiedReportedEvent:
    """Non-HTTP result of exact native source/purpose/span qualification."""
    _bytes: bytes
    _digest: str
    _token: object

    def evidence(self):
        _require(getattr(self, '_token', None) is _TOKEN and type(self._bytes) is bytes
                 and len(self._bytes) <= 32768 and sha256(self._bytes).hexdigest()==self._digest,
                 'H20_QUALIFICATION_REQUIRED')
        return json.loads(self._bytes)


def qualify_retained_h20_event(authority: PinnedSourceAuthority, *, decision_raw: bytes,
                               policy_raw: bytes, theme_sources_raw: bytes) -> QualifiedReportedEvent:
    """Read exactly the fixed native manifest/document and replay one span.

    The exact protected purpose/decision pins are checked BEFORE native I/O.
    Never accepts a caller body, arbitrary URL, source profile or adoption time.
    Errors are sanitized, with no fallback or retry.
    """
    try:
        _require(type(decision_raw) is bytes and len(decision_raw) <= 65536
                 and sha256(decision_raw).hexdigest()==DECISION_SHA256
                 and type(policy_raw) is bytes and len(policy_raw) <= 65536
                 and sha256(policy_raw).hexdigest()==POLICY_SHA256,
                 'H20_PROTECTED_RECORD_MISMATCH')
        decision=owner_record_from_bytes(decision_raw);policy=owner_record_from_bytes(policy_raw)
        now=_now();adopted=_instant(decision['adopted_at'])
        _require(_instant(policy['recorded_at']) <= adopted <= now, 'H20_ADOPTION_CLOCK_INVALID')
        _require(decision['policy_sha256']==POLICY_SHA256 and policy['source']==decision['source'],
                 'H20_PURPOSE_BINDING_INVALID')
        _require(type(theme_sources_raw) is bytes and 0 < len(theme_sources_raw) <= 1024*1024,
                 'H20_PURPOSE_NOT_ADMITTED')
        family=yaml.safe_load(theme_sources_raw)['families'].get('sec_public_filing_facts')
        _require(type(family) is dict and family.get('rights_class')=='derived_display_ok'
                 and family.get('auth_class')=='keyless_public', 'H20_PURPOSE_NOT_ADMITTED')
        _require(decision['source']=={'accession':ACCESSION,'reporting_cik':CIK,'archive_url':URL,
            'raw_sha256':RAW_SHA256,'byte_start':SPAN_START,'byte_end':SPAN_END,'span_sha256':SPAN_SHA256},
            'H20_PROFILE_SOURCE_MISMATCH')
        use=policy['permitted_use']
        _require(policy['rights_family']=='sec_public_filing_facts'
                 and (use['purpose'],use['audience'])==(PURPOSE,AUDIENCE)
                 and use['kind']=='reported_h20_demand_loss' and use['source_attribution_required'] is True
                 and use['source_body_export'] is use['source_quotation'] is use['reviewer_text'] is False,
                 'H20_PURPOSE_NOT_ADMITTED')
        _require(type(authority) is PinnedSourceAuthority and authority.snapshot_id==SNAPSHOT_ID,
                 'H20_EXACT_NATIVE_SOURCE_REQUIRED')
        # Reconstitute the incumbent reader; mutable session caches/overrides
        # are not the retained snapshot authority.
        authority=PinnedSourceAuthority(store=authority._store, snapshot_id=SNAPSHOT_ID)
        manifest=manifest_from_json_bytes(authority.read_file(kind='archive',relative_path=MANIFEST_KEY,
            maximum_bytes=1024*1024).content)
        docs=[d for d in manifest['documents'] if d['document_id']==DOCUMENT_ID]
        _require(len(docs)==1 and manifest['issuer']['cik']==CIK
                 and manifest['filing']['accession']==ACCESSION
                 and manifest['filing']['form']=='10-K' and manifest['filing']['report_date']=='2026-01-25',
                 'H20_FILING_BINDING_INVALID')
        document=docs[0];retrieval=document['retrieval'];clocks=manifest['clocks']
        _require(document['archive_url']==retrieval['archive_url']==URL
                 and document['content_sha256']==retrieval['content_sha256']==RAW_SHA256
                 and document['byte_length']==retrieval['byte_length']==RAW_BYTES,
                 'H20_DOCUMENT_BINDING_INVALID')
        accepted=_instant(clocks['accepted_at']);retrieved=_instant(retrieval['retrieved_at'])
        recorded=_instant(clocks['recorded_at']);snapshot=_instant(authority.snapshot_at)
        _require(accepted <= retrieved <= recorded <= snapshot <= adopted <= now,
                 'H20_SOURCE_CLOCK_INVALID')
        read=authority.read_archive_document(storage_key=document['storage_key'],expected_receipt=retrieval,
            maximum_bytes=RAW_BYTES,maximum_stored_bytes=gzip_stored_byte_ceiling(RAW_BYTES))
        raw=read.content
        _require(read.receipt_sidecar_verified is True and len(raw)==RAW_BYTES
                 and sha256(raw).hexdigest()==RAW_SHA256, 'H20_NATIVE_REPLAY_REQUIRED')
        span_raw=raw[SPAN_START:SPAN_END]
        _require(sha256(span_raw).hexdigest()==SPAN_SHA256, 'H20_SPAN_MISMATCH')
        body=raw.decode('utf8');literal=span_raw.decode('utf8');text=visible_text(literal)
        _require('first quarter of fiscal year 2026' in text
                 and text.endswith('as the demand for H20 products diminished.'), 'H20_REPORTED_FACT_UNSUPPORTED')
        event_id=canonical_event_id('cik:'+CIK,FiscalPeriod(year=2026),event_type='earnings_results')
        source=SourceDocument(document_id=DOCUMENT_ID,event_id=event_id,document_kind='filing',
            source_class='primary_filing',content_sha256=RAW_SHA256,content_bytes=len(raw),
            filing_key=FilingKey(cik=CIK,accession=ACCESSION),fetched_at=retrieved,available_at=None,
            published_at=None,rights_profile='rp_public_primary_v1',rights_state='public_primary',
            presented_fiscal_label='FY2026')
        span=text_span(document_id=DOCUMENT_ID,document_version=1,body_sha256=RAW_SHA256,
            segment_index=0,segment_text=body,start_byte=SPAN_START,end_byte=SPAN_END,text=literal,
            rights_profile='rp_public_primary_v1',display_excerpt='')
        verify_span(span,segment_text=body,body_sha256=RAW_SHA256)
        fact={'schema':'event_fact.v1','fact_id':event_id+':reported_h20_demand_loss','event_id':event_id,
            'metric':'reported_h20_demand_loss','value':'reported_demand_loss','unit':'source_reported_terms',
            'period':'2026Q1','basis':'company_reported','fact_class':'reported_operating_event',
            'source_span':span.to_payload()}
        payload={'schema':'company_intelligence.qualified_reported_event/v1','fact':fact,
            'source_document':source.to_payload(),'source_report_period':'FY2026',
            'reported_occurrence_period':decision['assertion']['reported_occurrence_period'],'occurrence_at':None,
            'clocks':{'reporting_at':clocks['accepted_at'],'reporting_basis':'SEC_acceptance',
                'retrieved_at':retrieval['retrieved_at'],'recorded_at':clocks['recorded_at'],
                'snapshot_at':authority.snapshot_at,'adopted_at':decision['adopted_at'],
                'verified_at':now.isoformat()},
            'source_ref':{'snapshot_id':SNAPSHOT_ID,'manifest_key':MANIFEST_KEY,'document_id':DOCUMENT_ID,
                'accession':ACCESSION,'archive_url':URL,'raw_sha256':RAW_SHA256,'raw_byte_length':RAW_BYTES,
                'span_start_byte':SPAN_START,'span_end_byte':SPAN_END,'span_sha256':SPAN_SHA256},
            'purpose':{'purpose':PURPOSE,'audience':AUDIENCE,'policy_sha256':POLICY_SHA256,
                'decision_sha256':DECISION_SHA256,'source_attribution_required':True,
                'source_body_export':False,'source_quotation':False},
            'counterparty_applicability':'unestablished','historical_body_availability':'unknown',
            'native_workspace_generation':None,
            'authority':'context_only'}
        result=object.__new__(QualifiedReportedEvent);content=_canonical(payload)
        object.__setattr__(result,'_bytes',content);object.__setattr__(result,'_digest',sha256(content).hexdigest())
        object.__setattr__(result,'_token',_TOKEN)
        return result
    except ReportedEventError:
        raise
    except Exception:
        raise ReportedEventError('H20_NATIVE_QUALIFICATION_UNAVAILABLE') from None
