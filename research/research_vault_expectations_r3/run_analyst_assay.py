"""Offline fixture -> comparison packet -> text preview. Not a Brain service.

No network, authentication, ingestion, source byte verification, publishing or
notifications. All source and permission labels remain manual research inputs.
"""
from __future__ import annotations
import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import platform
import unittest
from urllib.parse import urlsplit
import revision_oracle as oracle

ROOT=Path(__file__).resolve().parent


def _reference(c: Mapping) -> dict:
    raw=c.get('source_url')
    try:
        parsed=urlsplit(raw) if isinstance(raw,str) else None
        safe=(parsed is not None and parsed.scheme=='https' and parsed.hostname=='think.ing.com'
              and not parsed.username and not parsed.password and parsed.port is None
              and not parsed.query and not parsed.fragment
              and parsed.path.startswith('/articles/') and parsed.path.endswith('/')
              and all(x not in raw for x in ('\n','\r','(',')','[',']','<','>',' ')))
    except ValueError:
        safe=False
    return {'id':c['id'],'url':raw if safe else None,'source_bytes_verified':False}


def build_case_packet(case: Mapping) -> dict:
    if not isinstance(case,Mapping) or case.get('status')!='MANUAL_RESEARCH_FIXTURE_NOT_TRUSTED_INGESTION':
        raise ValueError('explicit manual research case required')
    values=case.get('claims')
    if not isinstance(values,list) or len(values)!=5 or not all(isinstance(v,Mapping) for v in values):
        raise ValueError('bounded five-observation case required')
    ids=[c.get('id') for c in values]
    expected={'june_fixed','sept3_fixed','sept7_fixed','aug_relative','sept_relative'}
    if any(not isinstance(i,str) for i in ids) or set(ids)!=expected:
        raise ValueError('unique expected fixture identities required')
    c=dict(zip(ids,values))
    computations=[
        ('source_reports_change',oracle.reported_change(c['sept3_fixed']),['sept3_fixed']),
        ('captured_fixed_target',oracle.compare(c['june_fixed'],c['sept3_fixed']),['june_fixed','sept3_fixed']),
        ('repeated_change',oracle.compare(c['sept3_fixed'],c['sept7_fixed']),['sept3_fixed','sept7_fixed']),
        ('rolling_fixed_target_refusal',oracle.compare(c['aug_relative'],c['sept_relative']),['aug_relative','sept_relative']),
        ('rolling_profile_comparison',oracle.compare(c['aug_relative'],c['sept_relative'],comparison_mode='constant_horizon_profile'),['aug_relative','sept_relative']),
    ]
    entries=[]
    for name,result,source_ids in computations:
        entries.append({'name':name,'result':result,
                        'sources':[] if result.get('status')=='not_served' else [_reference(c[i]) for i in source_ids]})
    return {'schema':'offline_research_case_preview.v1','status':'OFFLINE_REFERENCE_OUTPUT',
            'input_method':'manually_normalized_public_statements_not_pdf_parser',
            'provenance':{'original_pair_verified':False,'source_body_hashes_measured':False,
                          'live_vault_binding':False,'authenticated_journey_proven':False,
                          'commercial_permission_established':False,'historical_operational_replay_proven':False},
            'authority':{'may_rank':False,'may_gate':False,'may_size':False,'may_trade':False,'may_notify':False},
            'comparisons':entries}


def render_preview(packet: Mapping) -> str:
    lines=['# Research answer preview — offline reference',
           '', '**This is not a production answer.** Values were manually normalized from dated public research.',
           'Original PDF/body hashes are not verified; vault identity, commercial permission and the authenticated viewer journey remain unproved.',
           'This demonstrates numerical semantics, not automated extraction, a live forecast, or trading advice.','']
    names={'source_reports_change':'What the source reports',
           'captured_fixed_target':'Comparison with the earlier captured statement',
           'repeated_change':'The later publication',
           'rolling_fixed_target_refusal':'The rolling-horizon trap',
           'rolling_profile_comparison':'A separately requested profile comparison'}
    for e in packet['comparisons']:
        r=e['result'];status=r['status'];lines += ['## '+names[e['name']],'']
        if status=='not_served':
            lines += ['Not served.',''];continue
        if status=='source_reported_revision':
            lines.append('ING reports a year-end 2026 EUR/USD target change of '+r['delta_low']+' USD per EUR. The previous number here is quoted within the later source, not a separately bound prior PDF.')
        elif status=='revision':
            lines.append('The manually captured fixed-target values differ by '+r['delta_low']+' USD per EUR ('+format(Decimal(r['percent_low']), '.2f')+'%, rounded for display). The quoted old value matches the earlier captured statement; this does not prove the immediate predecessor or the first-ever revision date.')
        elif status=='repeated_reported_revision':
            lines.append('No additional numerical change between the inspected statements. Both inspected publications describe the same prior/current endpoints. Other new analysis and any intervening uncaptured changes remain unassessed; do not discard the whole report.')
        elif status=='not_comparable':
            lines.append('No fixed-date revision is inferred. Reason: `'+r.get('reason','not_comparable')+'`. A shared 3M label does not identify the same calendar target.')
        elif status=='constant_horizon_profile_change':
            lines.append('Under an explicit constant-horizon request, the two three-month figures differ by '+r['delta_low']+' USD per EUR. This is a profile comparison, not a fixed-date forecast revision.')
        else:
            lines.append('No supported preview for status `'+status+'`; do not manufacture an answer.')
        refs=[x['url'] for x in e['sources'] if x['url']]
        if refs:lines.append('Source references: '+' · '.join('[Publisher source]('+u+')' for u in refs))
        lines.append('')
    lines += ['## What remains held','',
              'No actual alert, portfolio decision, source-store change or publication is performed. R3 issuer tests and R5 analyst tests are local reference checks. The larger research-answer benchmark remains unexecuted.','']
    return '\n'.join(lines)


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    suite=unittest.TestLoader().loadTestsFromNames(['test_revision_oracle','test_analyst_contract'])
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (args.out/'tests_r5.txt').write_text(log.getvalue())
    receipt={'schema':'offline_analyst_reference_assay.v1','executed_at_utc':datetime.now(timezone.utc).isoformat(),
             'python':platform.python_version(),'tests_run':result.testsRun,'failures':len(result.failures),
             'errors':len(result.errors),'skipped':len(result.skipped),'success':result.wasSuccessful(),
             'scope':'Manual issuer and analyst research cases plus negative fixtures; no PDF/model/production tests.',
             'original_source_pairs_bound':0,'authenticated_customer_journeys':0,
             'sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                       ['revision_oracle.py','test_revision_oracle.py','test_analyst_contract.py','analyst_control_case.json','public_control_case.json','run_analyst_assay.py']}}
    (args.out/'verification_r5.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if result.wasSuccessful():
        packet=build_case_packet(json.loads((ROOT/'analyst_control_case.json').read_text()))
        (args.out/'bank_case_outputs.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n')
        (args.out/'BANK_CASE_ANSWER_PREVIEW.md').write_text(render_preview(packet))
    print(json.dumps({k:v for k,v in receipt.items() if k!='sha256'},indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
