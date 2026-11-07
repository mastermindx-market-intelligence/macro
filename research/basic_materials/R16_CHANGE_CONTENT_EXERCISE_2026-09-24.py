"""Pure, offline R16 content-eligibility rehearsal over synthetic research cases.

This is NOT a production publisher, event store, policy checker, model evaluator,
ranking engine or replacement for the existing curation/brief/identity owners.
The fake permissions and supplied history are scenario assumptions only. There is
no I/O inside assess(), and no native admission or notification can be produced.
"""
from __future__ import annotations
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any

TOP = {'synthetic', 'context', 'item', 'prior'}
CONTEXT = {'window_start','cutoff','surface','external_model','decision_snapshot'}
ITEM = {'revision','claim','origin','semantic','source_time','recorded_at','source_kind',
        'target_end','corrects','comparison','baseline_kind','baseline_ref','baseline_time',
        'reviewed','fixture_permissions','private_text','public_text','can_rank','claim_type'}
PRIOR = {'revision','claim','origin','semantic','source_time'}
PERMISSIONS = {'private','public_summary','external_processor'}
BASELINES = {'prior_observation','management_guidance','consensus','none'}


def _instant(text: Any) -> datetime:
    if not isinstance(text,str) or 'T' not in text:
        raise ValueError('not an instant')
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('zone absent')
    return value.astimezone(timezone.utc)


def _bounds(text: Any) -> tuple[datetime,datetime]:
    if isinstance(text,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',text):
        start=datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return start,start+timedelta(days=1)
    point=_instant(text)
    return point,point


def _closed(value: Any, keys: set[str]) -> None:
    if not isinstance(value,dict) or set(value)!=keys:
        raise ValueError('research shape mismatch; no implicit producer extensions')


def assess(case: dict) -> dict:
    """Return an illustrative content disposition; never changes caller data."""
    _closed(case,TOP)
    if case['synthetic'] is not True: raise ValueError('synthetic research only')
    ctx=case['context']; item=case['item']; prior=case['prior']
    _closed(ctx,CONTEXT); _closed(item,ITEM); _closed(item['fixture_permissions'],PERMISSIONS)
    if prior is not None: _closed(prior,PRIOR)
    if item['can_rank'] is not False: raise ValueError('research authority must be literal false')
    if ctx['surface'] not in {'private_dossier','public_brief'}: raise ValueError('unknown surface')
    if type(ctx['external_model']) is not bool: raise ValueError('processor flag must be boolean')
    if item['source_kind'] not in {'reported','target','hypothesis'}: raise ValueError('unknown source kind')
    if item['comparison'] not in {'comparable','not_comparable','none'}: raise ValueError('unknown comparison')
    if item['baseline_kind'] not in BASELINES: raise ValueError('unknown baseline kind')
    if item['claim_type'] not in {'economic_observation','consensus_surprise'}: raise ValueError('unknown claim type')
    for key in ('revision','claim','origin','semantic','private_text'):
        if not isinstance(item[key],str) or not item[key]: raise ValueError('missing scenario text')
    result={'status':'refused','kind':None,'reason':None,'text':None,'evidence_ref':None,
            'baseline_label':None,'decision_unchanged':True,
            'production_admitted':False,'can_rank':False,'can_notify':False}
    def refuse(reason):
        result['reason']=reason
        return result
    # Current permission comes before history/revision details. These booleans are
    # deliberately named fixture permissions; production must use owner receipts.
    if item['reviewed'] is not True: return refuse('review_missing')
    rights=item['fixture_permissions']
    if ctx['surface']=='private_dossier':
        if rights['private'] is not True: return refuse('private_representation_not_approved')
        text=item['private_text']; ref=item['revision']
    else:
        if rights['public_summary'] is not True: return refuse('public_representation_not_approved')
        if not isinstance(item['public_text'],str) or not item['public_text']:
            return refuse('public_copy_missing')
        text=item['public_text']; ref=None
    if ctx['external_model'] and rights['external_processor'] is not True:
        return refuse('external_processor_not_approved')
    try:
        start=_instant(ctx['window_start']); end=_instant(ctx['cutoff'])
    except (ValueError,TypeError): return refuse('invalid_window')
    if start>=end: return refuse('invalid_window')
    try: recorded=_instant(item['recorded_at'])
    except (ValueError,TypeError): return refuse('recording_time_unqualified')
    if recorded>end: return refuse('recorded_after_cutoff')
    if item['source_time'] is None: return refuse('source_time_unknown')
    try: lower,upper=_bounds(item['source_time'])
    except (ValueError,TypeError): return refuse('source_time_unqualified')
    if lower>end: return refuse('future_source')
    if upper>end or lower<start<upper: return refuse('source_time_unqualified')
    if upper<=recorded or lower==upper:
        if lower==upper and lower>recorded: return refuse('recorded_before_source')
    else: return refuse('source_time_unqualified')
    if prior and item['revision']==prior['revision']:
        if any(item[k]!=prior[k] for k in ('claim','origin','semantic','source_time')):
            return refuse('revision_content_conflict')
        result.update(status='no_delta',kind='unchanged');return result
    if item['corrects']:
        if not prior or item['corrects']!=prior['revision']:
            return refuse('correction_predecessor_missing')
        if item['claim']!=prior['claim']:return refuse('correction_scope_mismatch')
        kind='correction'
    elif prior and all(item[k]==prior[k] for k in ('claim','origin','semantic')):
        result.update(status='no_delta',kind='same_source_restatement');return result
    else: kind=None
    # R17: validate the claim independently of its presentation. A background
    # or correction label must never bypass comparison prerequisites.
    # Permission, source clocks, predecessor checks and no-output repeats
    # remain above this boundary. No parser here validates natural language.
    if item['claim_type']=='consensus_surprise' and (item['comparison']!='comparable' or item['baseline_kind']!='consensus' or item['source_kind']!='reported'):
        return refuse('consensus_baseline_required')
    if item['comparison']=='not_comparable':return refuse('comparison_unqualified')
    if item['comparison']=='comparable':
        if not item['baseline_ref'] or item['baseline_kind']=='none':return refuse('baseline_missing')
        try: baseline_hi=_bounds(item['baseline_time'])[1]
        except (ValueError,TypeError):return refuse('baseline_time_unknown')
        if baseline_hi>=lower:return refuse('baseline_not_prior')
        if item['claim_type']=='consensus_surprise' and item['baseline_kind']!='consensus':
            return refuse('consensus_baseline_required')
    if (lower<upper and upper<=start) or (lower==upper and lower<start):
        result.update(status='background',kind='newly_learned_old_source' if recorded>=start else 'historical_context',text=text,evidence_ref=ref)
        return result
    if kind=='correction':
        result.update(status='eligible_context',kind=kind,text=text,evidence_ref=ref);return result
    if item['source_kind']=='target':
        reason=None
        if item['target_end']:
            try:
                if _bounds(item['target_end'])[1]<end:reason='window_elapsed_not_confirmation'
            except (ValueError,TypeError):return refuse('target_time_unqualified')
        result.update(status='eligible_context',kind='target_unconfirmed',reason=reason,text=text,evidence_ref=ref)
        return result
    if item['source_kind']=='hypothesis':
        result.update(status='eligible_context',kind='hypothesis',text=text,evidence_ref=ref);return result
    if item['comparison']=='comparable':
        result['baseline_label']=item['baseline_kind'];kind='economic_change'
    else:
        kind='separate_proposition' if prior and item['claim']!=prior['claim'] else 'new_report'
    result.update(status='eligible_context',kind=kind,text=text,evidence_ref=ref)
    return result


def load_cases(path: Path) -> list[dict]:
    raw=path.read_bytes()
    if len(raw)>1_000_000:raise ValueError('bounded research file exceeded')
    doc=json.loads(raw)
    cases=[]
    for row in doc['cases']:
        item=copy.deepcopy(doc['base'])
        for dotted,value in row['overrides'].items():
            keys=dotted.split('.'); node=item
            for key in keys[:-1]: node=node[key]
            if keys[-1] not in node:raise ValueError('unknown fixture override')
            node[keys[-1]]=copy.deepcopy(value)
        cases.append({'id':row['id'],'question':row['question'],'input':item,'expected':row['expected']})
    return cases


def run_cases(path: Path) -> dict:
    cases=load_cases(path)
    records=[]
    for case in cases:
        outcome=assess(case['input'])
        mismatches={k:{'expected':v,'observed':outcome[k]} for k,v in case['expected'].items() if outcome[k]!=v}
        records.append({'id':case['id'],'matched':not mismatches,'mismatches':mismatches,'outcome':outcome})
    return {'scope':'offline synthetic content rehearsal only; not native admission, publication or model evaluation',
            'case_count':len(records),'matched':sum(r['matched'] for r in records),
            'refused':sum(r['outcome']['status']=='refused' for r in records),
            'records':records,'native_product_tests':0,'model_calls':0,'delivered_notifications':0}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case_file',type=Path)
    args=parser.parse_args()
    outcome=run_cases(args.case_file)
    print(json.dumps(outcome,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False))
    if outcome['matched']!=outcome['case_count']:raise SystemExit(1)
