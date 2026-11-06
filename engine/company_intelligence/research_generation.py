"""Bounded immutable Earnings generation reads for existing research consumers.

Uses the incumbent owner's fetch, schema and raw-workspace receipt verification.
No history scan, source acquisition, custom origin, store or collection is added.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from engine.neuralweb import company_intelligence_reader as owner
from engine.company_intelligence.event_workspace import validate_workspace_manifest
from engine.company_intelligence.events import parse_canonical_event_id
from lib import evidence_foundation as ef

SCHEMA='earnings.generation_pointer.v1'
MAX_COMPANIES=8


class EarningsGenerationUnavailable(ValueError):
    """Stable tokens, never URLs, paths or owner response bodies."""


def _require(ok,code='earnings_generation_invalid'):
    if not ok:raise EarningsGenerationUnavailable(code)


def _now():return datetime.now(timezone.utc)


def _instant(value):
    _require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value) is not None)
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
    except ValueError:raise EarningsGenerationUnavailable('earnings_generation_invalid') from None


def validate_generation_pointer(pointer):
    try:
        _require(type(pointer) is dict and set(pointer)=={'schema','generation_id','manifest_sha256','manifest_bytes','captured_at','owner_generated_at','sha256'})
        _require(pointer['schema']==SCHEMA and re.fullmatch(r'[a-f0-9]{24,64}',pointer['generation_id']) is not None
                 and re.fullmatch(r'[a-f0-9]{64}',pointer['manifest_sha256']) is not None
                 and type(pointer['manifest_bytes']) is int and 0<pointer['manifest_bytes']<=owner._MAX_MANIFEST_BYTES)
        _require(_instant(pointer['owner_generated_at'])<=_instant(pointer['captured_at']))
        body={k:v for k,v in pointer.items() if k!='sha256'}
        _require(pointer['sha256']==sha256(ef.canonical_json_bytes(body)).hexdigest())
    except EarningsGenerationUnavailable:raise
    except Exception:raise EarningsGenerationUnavailable('earnings_generation_invalid') from None
    return dict(pointer)


def capture_generation_pointer() -> dict:
    """Read the existing public marker + immutable manifest, sampling actual time."""
    try:
        marker=owner.fetch_current_workspace_marker_raw()
        _require(marker is not None,'earnings_generation_absent')
        _,head=marker;validate_workspace_manifest(head)
        raw,manifest=owner._fetch_generation_manifest_raw(head['generation_id'])
        validate_workspace_manifest(manifest)
        _require(ef.canonical_json_bytes(head)==ef.canonical_json_bytes(manifest))
        result={'schema':SCHEMA,'generation_id':manifest['generation_id'],
                'manifest_sha256':sha256(raw).hexdigest(),'manifest_bytes':len(raw),
                'captured_at':_now().isoformat().replace('+00:00','Z'),
                'owner_generated_at':manifest['generated_at']}
        result['sha256']=sha256(ef.canonical_json_bytes(result)).hexdigest()
        return validate_generation_pointer(result)
    except (EarningsGenerationUnavailable, owner.CompanyIntelligenceReadBudgetExceeded):raise
    except Exception:raise EarningsGenerationUnavailable('earnings_generation_unavailable') from None


def read_pinned_generation(pointer: dict, company_ids: list[str]) -> dict:
    """Read at most eight exact issuer result events from ONE pinned generation.

    No current-marker fallback, alias-string CIK join or predecessor traversal.
    Missing issuer is None; malformed or altered owner bytes are typed failure.
    Returned revisions have the same contract as read_event_source_revisions.
    """
    pointer=validate_generation_pointer(pointer)
    _require(type(company_ids) is list and len(company_ids)<=MAX_COMPANIES
             and all(type(x) is str and re.fullmatch(r'cik:[0-9]{10}',x) for x in company_ids)
             and len(set(company_ids))==len(company_ids))
    if not company_ids:return {}
    try:
        owner.check_read_budget()
        raw,manifest=owner._fetch_generation_manifest_raw(pointer['generation_id'])
        _require(len(raw)==pointer['manifest_bytes'] and sha256(raw).hexdigest()==pointer['manifest_sha256'])
        owner.check_read_budget()
        validate_workspace_manifest(manifest)
        _require(manifest['generation_id']==pointer['generation_id'] and manifest['generated_at']==pointer['owner_generated_at'])
        candidates={c:[] for c in company_ids}
        for path in manifest['files']:
            if not path.startswith('workspaces/') or not path.endswith('.json'):continue
            event=path[len('workspaces/'):-len('.json')]
            try:company,period,kind=parse_canonical_event_id(event)
            except Exception:continue
            if company in candidates and kind=='earnings_results':
                candidates[company].append(((period.year,period.quarter or 0),event))
        result={}
        for company,events in candidates.items():
            owner.check_read_budget()
            if not events:result[company]=None;continue
            period=max(p for p,e in events);selected=[e for p,e in events if p==period]
            _require(len(selected)==1,'earnings_event_ambiguous')
            event=selected[0]
            pair=owner._event_revision_from_generation(manifest,event,generation_id=pointer['generation_id'],base_url=None)
            owner.check_read_budget()
            _require(pair is not None)
            workspace,receipt=pair
            result[company]={'event_id':event,'revisions':[owner._receipt_from_revision(workspace,
                generation_id=pointer['generation_id'],workspace_receipt=receipt)]}
        return result
    except (EarningsGenerationUnavailable, owner.CompanyIntelligenceReadBudgetExceeded):raise
    except Exception:raise EarningsGenerationUnavailable('earnings_generation_unavailable') from None
