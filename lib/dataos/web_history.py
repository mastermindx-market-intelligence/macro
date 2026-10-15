"""Existing Data & Lab transport projection for historical Market Memory.

No path/identity/permission/lifecycle owner is added. Every byte is read by
DataWorkspace._file through its existing root, descriptor and mutation guards.
Market Memory's own manifest/Parquet/first-print validators remain authoritative.
The request may select bounded retained references, never paths, SQL, code,
credentials, provider calls, publication, collection or a write destination.
"""
from __future__ import annotations
import hashlib
import json
import re

from lib.dataos.web_workspace import DataWorkspace,WorkspaceError

_HEX=re.compile(r'[a-f0-9]{64}\Z')


def history_dossier(workspace: DataWorkspace, *, ref: str, date: str,
                    manifest_sha256: str, macro_ref: str | None=None,
                    macro_sha256: str | None=None, reveal_outcomes: bool=False,
                    filings_ref: str | None=None, filings_sha256: str | None=None,
                    filings_offset: int=0) -> dict:
    from engine.neuralweb.market_memory_history import HistoricalExperienceError
    from engine.neuralweb.market_memory_history_archive import read_day_from_reader
    from engine.neuralweb.market_memory_history_dossier import compose_daily_dossier
    from engine.neuralweb.market_memory_history_macro import (
        MAX_BYTES,read_macro_chronology_bytes,select_macro_date,
    )
    if (type(manifest_sha256) is not str or not _HEX.fullmatch(manifest_sha256)
            or type(reveal_outcomes) is not bool
            or (macro_ref is None)!=(macro_sha256 is None)
            or (filings_ref is None)!=(filings_sha256 is None)
            or type(filings_offset) is not int or not 0 <= filings_offset <= 250000
            or (filings_ref is None and filings_offset != 0)):
        raise WorkspaceError('INVALID_HISTORY_BINDING')
    root,parts=workspace._split_ref(ref)
    if parts[-1]!='manifest.json':raise WorkspaceError('HISTORY_MANIFEST_REF_REQUIRED')
    if macro_ref is not None:
        _, macro_parts = workspace._split_ref(macro_ref)
        # Historical state/outcome partitions are Parquet. They cannot be
        # opened through the optional first-print JSON channel, even to reject
        # their contents later. Normal source-owner path guards remain in force.
        if not macro_parts[-1].endswith('.json'):
            raise WorkspaceError('HISTORY_MACRO_JSON_REF_REQUIRED')
        if type(macro_sha256) is not str or not _HEX.fullmatch(macro_sha256):
            raise WorkspaceError('INVALID_HISTORY_BINDING')
    if filings_ref is not None:
        _, filing_parts = workspace._split_ref(filings_ref)
        if filing_parts[-1] != 'earnings_8k_dates.parquet':
            raise WorkspaceError('HISTORY_FILING_SOURCE_REF_REQUIRED')
        if type(filings_sha256) is not str or not _HEX.fullmatch(filings_sha256):
            raise WorkspaceError('INVALID_HISTORY_BINDING')
    prefix=root.alias+':'+('/'.join(parts[:-1])+'/' if len(parts)>1 else '')
    source_files=[]
    def read_bound(bound_ref: str, limit: int) -> bytes:
        with workspace._file(bound_ref) as (stream,source):
            if source['file_bytes']>limit:
                raise WorkspaceError('HISTORY_SOURCE_BYTE_BUDGET_EXCEEDED')
            raw=stream.read(limit+1)
            if len(raw)>limit or len(raw)!=source['file_bytes']:
                raise WorkspaceError('HISTORY_SOURCE_BYTE_BUDGET_EXCEEDED')
            receipt={**source,'content_sha256':hashlib.sha256(raw).hexdigest()}
        # _file must finish its replacement/version guard before accepting bytes.
        source_files.append(receipt)
        return raw
    def read_artifact(name: str,limit: int) -> bytes:
        if '/' in name or '\\' in name or name.startswith('.'):
            raise WorkspaceError('HISTORY_ARTIFACT_NAME_REFUSED')
        return read_bound(prefix+name,limit)
    try:
        market=read_day_from_reader(read_artifact,date,expected_manifest_sha256=manifest_sha256,
                                   reveal_outcomes=reveal_outcomes)
        macro=None
        if macro_ref is not None:
            chronology=read_macro_chronology_bytes(read_bound(macro_ref,MAX_BYTES),expected_sha256=macro_sha256)
            macro=select_macro_date(chronology,date)
            macro.update(status='OBSERVED' if macro['total_events'] else 'NO_OBSERVATION',sha256=macro_sha256)
        result=compose_daily_dossier(market,macro)
        if filings_ref is not None:
            from engine.neuralweb.market_memory_history_filings import MAX_SOURCE_BYTES, read_filing_date
            result['filings'] = read_filing_date(read_bound(filings_ref, MAX_SOURCE_BYTES), date,
                expected_sha256=filings_sha256, offset=filings_offset)
            result['coverage']['issuer_filings_and_earnings_context'] = 'SELECTED_ITEM_202_FILING_METADATA_ONLY'
    except HistoricalExperienceError:
        raise WorkspaceError('HISTORY_SOURCE_OR_CONTRACT_INVALID') from None
    request={'ref':ref,'manifest_sha256':manifest_sha256,'date':date,
             'macro_ref':macro_ref,'macro_sha256':macro_sha256,'reveal_outcomes':reveal_outcomes}
    if filings_ref is not None:
        request.update(filings_ref=filings_ref, filings_sha256=filings_sha256, filings_offset=filings_offset)
    receipt_input={'query':request,'sources':[{'ref':r['ref'],'file_version':r['file_version'],
                    'content_sha256':r['content_sha256']} for r in source_files]}
    digest=hashlib.sha256(json.dumps(receipt_input,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return workspace._result(action='history_dossier',query=request,source_files=source_files,
        query_receipt_sha256=digest,result=result,
        effects='read-only projection; no source, registry, process, ledger or publication writes')
