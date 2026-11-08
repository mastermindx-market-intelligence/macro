#!/usr/bin/env python3
"""Validate this bounded research packet; no downloads or production effects.

Run: python3 validate_pb_b.py --self-test
Certifies structural/time/amount guards, not source truth or causal identification.
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

def time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')) if value else None

def validate(book, windows):
    errors=[]
    def check(ok,message):
        if not ok: errors.append(message)
    rows=book['episodes']
    registry={s['source_id']:s for s in book['source_registry']}
    wmap={w['window_id']:w for w in windows['windows']}
    check(10<=len(rows)<=15,'episode_count_outside_commission')
    check(len({r['episode_id'] for r in rows})==len(rows),'duplicate_episode_id')
    check(len({r['underlying_event_id'] for r in rows})==len(rows),'duplicate_underlying_event')
    check(len(registry)==len(book['source_registry']),'duplicate_source_id')
    for r in rows:
        eid=r['episode_id']; cut=time(r['decision_cut_utc'])
        d=r['decision_time']; lineage={s['source_id']:s for s in r['source_lineage']}
        check(r['pit_certified'] is True,eid+':uncertified_input_set')
        check(r['decision_cut_valid'] is True,eid+':invalid_target_order')
        check(r['accuracy_comparison_eligible'] is False,eid+':false_accuracy_claim')
        check(r['prospectively_locked_forecast'] is False,eid+':false_prospective_lock')
        check(list(r).index('outcomes')>list(r).index('decision_time'),eid+':outcome_block_order')
        facts={f['fact_id']:f for f in d['known_facts']}
        statements={s['statement_id']:s for s in d['rhetoric']}
        used={f['source_id'] for f in facts.values()}|{s['source_id'] for s in statements.values()}|{a['source_id'] for a in d['actions']}
        for sid in used:
            s=registry.get(sid)
            check(s is not None,eid+':unknown_source:'+sid)
            if not s: continue
            bound=time(s['public_by_utc'])
            check(bound is not None and bound<cut,eid+':future_or_unbounded_input:'+sid)
            check(s.get('input_eligible',True),eid+':ineligible_source:'+sid)
            check(lineage.get(sid,{}).get('used_as_decision_input') is True,eid+':lineage_role:'+sid)
            check(lineage.get(sid,{}).get('public_before_cut') is True,eid+':lineage_time:'+sid)
        for f in facts.values():
            check(time(f['available_by_utc'])<cut,eid+':future_fact:'+f['fact_id'])
        for a in d['actions']:
            check(a['state'] in ('announced','authorized','executed','completed',None),eid+':invalid_action_state')
            if a['evidence_status']=='reported_unconfirmed_at_cut':
                check(a['state'] is None and a['execution_receipt'] is None,eid+':report_promoted_to_receipt')
            if a['action_type']=='facility_advocacy':
                check(a['state']=='announced' and a['amount'] is None and a['execution_receipt'] is None,eid+':proposal_promoted_to_draw')
        for model in ['M0','M1','M2']:
            f=d['forecasts'][model]
            check(f['directional_or_probabilistic_forecast'] is None,eid+':hindsight_forecast:'+model)
            check(f['confidence_or_probability'] is None and f['probability'] is None,eid+':invented_probability:'+model)
            check(f['abstention_state']['abstains'] is True,eid+':missing_abstention:'+model)
            check(all(x in facts or x in statements for x in f['exact_inputs_used']),eid+':unknown_model_input:'+model)
            target=registry[f['horizon']['target_source_id']]
            earliest=time(target['publication_time_utc'] or target['first_public_interval_utc']['earliest'])
            check(earliest is not None and cut<earliest,eid+':cut_after_target:'+model)
        check(all(w in wmap for w in r['outcomes']['retrospective_market_window_ids']),eid+':unknown_window')
        check(len(r['retrospective_assessment']['competing_hypotheses'])>=2,eid+':insufficient_alternatives')
        # The most consequential version leak is explicitly prohibited.
        check('RX_2026_09_PRIVATE' not in used,eid+':private_history_leaked')
    check(book['counts']['unique_boj_target_decisions']==len({r['policy_target_cluster_id'] for r in rows}),'incorrect_target_N')
    check(book['counts']['locked_forecasts']==0,'false_locked_count')
    check(book['counts']['accuracy_comparison_eligible']==0,'false_accuracy_count')
    check(len(wmap)==book['counts']['descriptive_event_windows'],'incorrect_window_count')
    for w in wmap.values():
        check(w['causal_effect_estimate'] is None,w['window_id']+':invented_causal_effect')
        check(w['raw_tick_data'] is False,w['window_id']+':false_tick_claim')
        check(all(s in registry for s in w['source_ids']),w['window_id']+':unknown_source')
    op=book['operational_reconciliation']
    q2=op['q2_2026']
    check(round(sum(q2['japan_daily_jpy_billion'].values()),1)==q2['sum_rounded_daily_jpy_billion'],'q2_daily_arithmetic')
    check(round(q2['japan_official_total_jpy_billion']-q2['sum_rounded_daily_jpy_billion'],1)==0.1,'q2_rounding_not_preserved')
    check(op['july_2026']['us_executed_amount_usd_equivalent'] is None,'fabricated_us_size')
    check(op['july_2026']['japan_july31_amount_jpy'] is None,'period_total_mislabeled_daily')
    check(op['fima']['verified_japan_draw_exact_usd'] is None,'rounded_zero_promoted_exact')
    check(op['fima']['verified_enlargement'] is None,'unverified_enlargement')
    check(op['fima']['limit_basis']=='total outstanding at any given time; not per day','fima_limit_mislabeled')
    check(wmap['EW10']['reported_or_derived_changes'][0]['change']==52,'repricing_arithmetic')
    check(wmap['EW10']['reported_or_derived_changes'][0]['unit']=='percentage_points','repricing_unit')
    return errors

def self_test(book,windows):
    probes=[]
    b=copy.deepcopy(book)
    b['episodes'][0]['decision_time']['known_facts'][0]['available_by_utc']='2026-10-07T00:00:00Z'
    probes.append(('future_fact',bool(validate(b,windows))))
    b=copy.deepcopy(book)
    b['episodes'][0]['decision_time']['forecasts']['M2']['probability']=0.8
    probes.append(('invented_retrospective_probability',bool(validate(b,windows))))
    b=copy.deepcopy(book)
    b['operational_reconciliation']['july_2026']['us_executed_amount_usd_equivalent']=10000000000
    probes.append(('planned_size_promoted_to_execution',bool(validate(b,windows))))
    b=copy.deepcopy(book)
    b['episodes'][12]['decision_time']['actions'][0]['state']='executed'
    probes.append(('facility_proposal_promoted_to_execution',bool(validate(b,windows))))
    return dict(probes)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--receipt',type=Path)
    a=p.parse_args()
    bpath=a.directory/'PB_B_CASEBOOK.json'; wpath=a.directory/'PB_B_EVENT_WINDOWS.json'
    book=json.loads(bpath.read_text()); windows=json.loads(wpath.read_text())
    errors=validate(book,windows)
    probes=self_test(book,windows) if a.self_test else {}
    result={'status':'PASS' if not errors and all(probes.values()) else 'FAIL','errors':errors,'adversarial_mutations_rejected':probes,
        'counts':book['counts'],'sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [bpath,wpath]},
        'scope':'Time/source roles, target ordering, abstentions, operational amounts and unit guards only. Source truth and causality require the written review.'}
    if a.receipt: a.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='PASS' else 1)
