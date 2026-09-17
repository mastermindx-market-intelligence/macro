"""Review-only adapter for the existing source owner, not an entitlement service.

The pending reader owns selection, projection, response budget and its one debit.
This request-local check neither issues permissions nor writes a ledger.
"""
from __future__ import annotations
import copy, hashlib, re

ID=re.compile(r'[a-z0-9][a-z0-9-]{0,120}\Z')
SHA=re.compile(r'[0-9a-f]{64}\Z')
FIELDS=('id','title','institution','side','published_at','summary_points')

def make_guard(*,selection,scope_provider,store,maximum_source_bytes):
    expected=copy.deepcopy(selection)
    verified_source=False
    def guard(*,phase,report_id,query,catalog_item,document=None):
        nonlocal verified_source
        if (not isinstance(expected,dict) or not isinstance(expected.get('id'),str)
            or not ID.fullmatch(expected['id'])
            or not all(isinstance(expected.get(k),str) and SHA.fullmatch(expected[k]) for k in ('pdf_sha256','body_sha256'))
            or not isinstance(expected.get('generation'),str) or not expected['generation']
            or not isinstance(expected.get('query'),str) or not 0<len(expected['query'])<=256):
            return 'selection_invalid'
        if report_id!=expected['id'] or query!=expected['query']:return 'selection_stale'
        try:scope=scope_provider('read_source_evidence')
        except Exception:return 'source_unavailable'
        if not isinstance(scope,dict):return 'source_unavailable'
        if scope.get('decision')=='denied':return 'source_access_denied'
        if scope.get('decision')!='allowed':return 'source_unavailable'
        items=scope.get('items')
        if not isinstance(items,dict):return 'source_unavailable'
        current=items.get(report_id)
        if (scope.get('generation')!=expected['generation'] or not isinstance(current,dict)
            or any(current.get(k)!=expected[k] for k in ('pdf_sha256','body_sha256'))):return 'selection_stale'
        cat=current.get('catalog')
        if (not isinstance(cat,dict) or not isinstance(catalog_item,dict)
            or any(cat.get(k)!=catalog_item.get(k) for k in FIELDS)):return 'source_mismatch'
        if phase=='admission':return True
        if (not isinstance(document,dict) or document.get('doc_id')!=report_id
            or not isinstance(document.get('body'),str)
            or document.get('content_sha256')!=expected['pdf_sha256']
            or hashlib.sha256(document['body'].encode()).hexdigest()!=expected['body_sha256']):return 'source_mismatch'
        if not verified_source:
            length=current.get('byte_length')
            if (type(length)is not int or length<1 or type(maximum_source_bytes)is not int
                or not 1<=length<=maximum_source_bytes):return 'source_unavailable'
            try:
                original=store.get_bytes_strict_bounded('research_vault/'+report_id+'.pdf',expected_byte_length=length,max_byte_length=maximum_source_bytes)
            except Exception:return 'source_unavailable'
            if original is None:return 'source_unavailable'
            if (type(original)is not bytes or not original.startswith(b'%PDF-')
                or hashlib.sha256(original).hexdigest()!=expected['pdf_sha256']):return 'source_mismatch'
            verified_source=True
        return True
    return guard
