#!/usr/bin/env python3
"""Offline evidence consistency/metric audit. No network or production calls.

Run beside the JSON: python validate_pb_e.py
This checks the research artifact, not the external truth or a production system.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

BASE=Path(__file__).resolve().parent
data=json.loads((BASE/'PB_E_NETWORK_EDGES.json').read_text())
checks=[]
def check(name,condition,detail=None):
    checks.append({'check':name,'passed':bool(condition),'detail':detail})

cases={c['case_id']:c for c in data['cases']}
edges={e['edge_id']:e for e in data['edges']}
sources={s['source_id']:s for s in data['sources']}
check('15_expected_cases',set(cases)=={f'C{x:02}' for x in range(1,16)})
check('unique_case_ids',len(cases)==len(data['cases']))
check('unique_edge_ids',len(edges)==len(data['edges']))
check('unique_source_ids',len(sources)==len(data['sources']))
check('all_edges_have_case',all(e['case_id'] in cases for e in edges.values()))
check('all_edge_sources_resolve',all(e['source_ids'] and set(e['source_ids'])<=set(sources) for e in edges.values()))
check('all_case_sources_resolve',all(c['source_ids'] and set(c['source_ids'])<=set(sources) for c in cases.values()))
check('all_sources_canonical_https',all(s.get('canonical_url','').startswith('https://') for s in sources.values()))
check('all_edge_types_defined',all(e['edge_type'] in data['taxonomy'] for e in edges.values()))
check('all_required_edge_fields',all(set(['from_entity','to_entity','amount','observation_state','economic_as_of','instrument_first_public_at_or_date','observation_first_public_at_or_date','cash_status','overlap_group','source_ids','point_in_time_eligible'])<=set(e) for e in edges.values()))
check('all_edges_research_only',all(e['production_eligible'] is False and e['point_in_time_eligible'] is False and e['aggregation_eligible'] is False for e in edges.values()))
check('null_clock_does_not_pass_PIT',all(e['observation_first_public_at_or_date'] is not None or (not e['point_in_time_eligible'] and e['eligibility_reasons']) for e in edges.values()))
check('instrument_and_observation_clocks_separate',all('first_public_at_or_date' not in e and e.get('public_clock_scope') for e in edges.values()))
check('no_universal_score_or_aggregate_fabrication',all(q['value'] is None and q['reason'] for q in data['aggregate_questions'].values()))
check('authority_is_context_only',all(data['authority'][k] is False for k in ['production_eligible','changes_rank','changes_gate','changes_size','changes_trade','creates_canonical_graph','creates_event_store']))
check('three_qualified_benign_controls',set(data['selection']['minimum_benign_controls'])=={'C08','C10','C15'})
cash_types={'external_equity_capital','direct_equity_investment_by_vendor','vendor_financing','debt_financing','government_equity_warrant','price_floor','asset_purchase_cash','cash_distribution','customer_prepayment'}
check('actual_cash_edges_do_not_include_revenue_or_guarantee_face',all(e['cash_status']!='cash_flow_reported' or (e['amount']['value'] is not None and e['edge_type'] in cash_types) for e in edges.values()))
check('unknown_gross_customer_cash_not_zero',all(e['edge_type']!='independent_end_customer_cash' or e['amount']['value'] is None for e in edges.values()))
check('no_anonymous_Broadcom_named_edges',all('AI_B01' not in e['source_ids'] for e in edges.values()))
check('ASML_aggregate_not_backdated_to_program_announcement',all(edges[k]['instrument_first_public_at_or_date'] is None for k in ['R-E26','R-E27']))
check('ASML_distribution_month_not_invented_day',edges['R-E28']['original_clocks'].get('event_month')=='2012-11' and edges['R-E28']['economic_as_of']!='2012-11-30')
check('AMD_warrant_state_is_dated',edges['R-E16']['economic_as_of']=='2026-06-27' and 'unvested' in edges['R-E16']['observation_state'])
check('Crane_zero_is_dated',edges['X-E05']['amount']['value']==0 and edges['X-E05']['economic_as_of']=='2026-08-06')
check('Crane_guarantee_not_total_payment_cap',edges['SEL-E03']['amount']['unit']=='USD_underlying_principal_limit')
check('Ford_old_guarantee_released', 'released' in edges['SEL-E29']['observation_state'])
check('Ford_assumption_not_new_cash',edges['SEL-E32']['cash_status']=='noncash_assumption_of_existing_debt' and edges['SEL-E32']['additional_terms']['subset_of_historical_advances']=='X-E12')
check('Ford_historical_advances_preserved',edges['X-E12']['amount']['value']==7835540000 and edges['SEL-E28']['amount']['value']==9633040000)
check('GM_cash_updated',edges['SEL-E19']['cash_status']=='cash_flow_reported' and edges['SEL-E19']['economic_as_of']=='2026-06-30')
check('Meta_asset_in_and_cash_out_preserved',edges['X-E11']['cash_status']=='noncash_asset_contribution' and edges['X-E02']['amount']['value']==3000000000)
check('SoftBank_component_has_overlap',edges['X-E01']['additional_terms']['component_of']=='AI_E016' and edges['X-E01']['overlap_group']==edges['AI_E016']['overlap_group'])
check('SoftBank_old_bridge_not_current_cash',edges['AI_E017']['cash_status']=='historical_capacity_repaid_not_current_ingress')
check('Anthropic_seriesH_component_overlaps_both_totals',set(edges['AI_E003']['overlap_groups'])=={'amazon_anthropic_cumulative18','anthropic_series_h_20260528'})

operators={
    'identity':lambda v:v[0],
    'sum':sum,
    'multiply':lambda v:math.prod(v),
    'subtract':lambda v:v[0]-v[1],
    'ratio_percent':lambda v:v[0]/v[1]*100,
    'change_percent':lambda v:(v[0]/v[1]-1)*100,
    'percentage_point_difference_bps':lambda v:(v[0]-v[1])*100,
}
for m in data['metrics']:
    computed=operators[m['operator']](m['inputs'])
    check('metric_'+m['metric_id'],math.isclose(computed,m['value'],rel_tol=1e-10,abs_tol=1e-6),{'recomputed':computed,'reported':m['value'],'unit':m['unit']})
    check('metric_sources_'+m['metric_id'],set(m['source_ids'])<=set(sources))
    check('metric_edges_'+m['metric_id'],set(m['edge_ids'])<=set(edges))

casebook=(BASE/'PB_E_NETWORK_CASEBOOK.md').read_text()
case_ids=re.findall(r'^## (C\d{2})\b',casebook,re.M)
check('all_15_casebook_sections_once',Counter(case_ids)==Counter(cases.keys()))
check('casebook_source_tokens_resolve',set(re.findall(r'\b(?:R-S\d{2}|SEL-S\d{2}|AI_[AGSMTB]\d{2})\b',casebook))<=set(sources))
for f in ['PB_E_EXTERNAL_CASH_ANALYSIS.md','PB_E_SELECTIVE_PROTECTION.md','PB_E_FAILURE_MODES.md','PB_E_SOURCE_REGISTER.md','PB_E_INTEGRATION_HANDOFF.md']:
    check('required_file_'+f,(BASE/f).is_file() and (BASE/f).stat().st_size>1000)
actual_counts={'cases':len(cases),'edges':len(edges),'source_records':len(sources),'unique_source_urls':len({s['canonical_url'] for s in sources.values()}),'source_lineage_groups':len({s['source_lineage_group'] for s in sources.values()}),'research_display_nodes':len(data['display_nodes']),'computed_metrics':len(data['metrics'])}
check('manifest_counts',data['counts']==actual_counts)
check('cutoff_observation_dates',all(not e['economic_as_of'] or e['economic_as_of'][:10]<='2026-10-06' for e in edges.values()))

hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(BASE.iterdir()) if p.is_file() and p.name!='PB_E_VALIDATION.json'}
report={'status':'PASS' if all(x['passed'] for x in checks) else 'FAIL','scope':'Offline research artifact integrity and arithmetic; no production execution, live integration, legal completeness or independent audit of issuer claims.','counts':actual_counts,'checks_passed':sum(x['passed'] for x in checks),'checks_total':len(checks),'checks':checks,'sha256':hashes}
(BASE/'PB_E_VALIDATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','sha256']},indent=2))
for x in checks:
    if not x['passed']: print('FAILED:',x['check'],x['detail'])
raise SystemExit(0 if report['status']=='PASS' else 1)
