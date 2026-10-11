#!/usr/bin/env python3
"""Descriptive membership/negative/species checks; no extra inference or date search."""
import collections,csv,hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
events=json.loads((p/'PB_C_EVENT_PANEL.json').read_text())['events']
stress={r['date']:r for r in json.loads((p/'PB_C_STRESS_WINDOWS.json').read_text())['daily_derived_rates']}
with (p/'nyse_calendar_2025.csv').open() as f:sessions=[r['date'] for r in csv.DictReader(f)]
idx={d:i for i,d in enumerate(sessions)}
material=[e for e in events if e['sampling_arm']=='material_event_pilot' and e['timing_analysis_eligible'] and e['event_date'] in idx]
broad=[e for e in material if e['scheduling']!='SCHEDULED' and e['economic_direction'] in ['POSITIVE','MIXED']]
close=[]
for i,a in enumerate(broad):
 for b in broad[i+1:]:
  if set(a['issuer_tickers']) & set(b['issuer_tickers']):continue
  distance=abs(idx[a['event_date']]-idx[b['event_date']])
  if distance<=3:close.append({'root_a':a['root_event_id'],'date_a':a['event_date'],'root_b':b['root_event_id'],'date_b':b['event_date'],'session_distance':distance,'shared_program_ids':sorted(set(a['program_ids']) & set(b['program_ids']))})
rows=[]
for e in material:
 rows.append({'root_event_id':e['root_event_id'],'date':e['event_date'],'primary_species':e['primary_species'],'economic_direction':e['economic_direction'],**{f'{inst}_prior{h}':stress[e['event_date']][inst][f'stress_any_prior{h}'] for inst in ['nominal2y','real10y'] for h in [5,10]}})
species=[]
for s in sorted({e['primary_species'] for e in material}):
 selected=[e for e in rows if e['primary_species']==s]
 species.append({'primary_species':s,'timing_eligible_captured_roots':len(selected),**{f'{inst}_prior{h}':{'exposed':sum(e[f'{inst}_prior{h}'] for e in selected),'unexposed':sum(not e[f'{inst}_prior{h}'] for e in selected)} for inst in ['nominal2y','real10y'] for h in [5,10]}})
out={'status':'DESCRIPTIVE_SELECTED_ROOTS_NOT_ISSUER_DAY_HAZARD','selection':'Same source-publication-date and trading-session eligibility as primary diagnostics.',
 'material_timing_eligible_roots':len(material),'broad_timing_eligible_roots':len(broad),'broad_distinct_issuers':len({t for e in broad for t in e['issuer_tickers']}),
 'material_content_directions':dict(collections.Counter(e['economic_direction'] for e in material)),
 'broad_observed_disjoint_issuer_pairs_within3':close,'root_exposure_membership':rows,'same_species_exposed_and_unexposed_captured_events':species,
 'negative_exposed_roots':{f'{inst}_prior{h}':[e['root_event_id'] for e in rows if e['economic_direction']=='NEGATIVE' and e[f'{inst}_prior{h}']] for inst in ['nominal2y','real10y'] for h in [5,10]},
 'input_sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['PB_C_EVENT_PANEL.json','PB_C_STRESS_WINDOWS.json','nyse_calendar_2025.csv']}}
(p/'PB_C_DESCRIPTIVE_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['material_timing_eligible_roots','broad_timing_eligible_roots','broad_distinct_issuers','negative_exposed_roots']},indent=2))
