"""Historical test input from pinned repository records; not current market data."""
from pathlib import Path
import json
from engine.events_news_release_evidence import attach_event_actual_evidence
ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures'

def historical_data(state='available'):
    fixture=json.loads((FIXTURES/'events_news_official_receipts.json').read_text())
    rows=fixture['rows']
    is_pce=state in ('withheld','repaired','quarantine_missing')
    cutoff='2026-07-31T20:00:00Z' if state=='withheld' else '2026-08-11T09:00:00Z' if state in ('repaired','quarantine_missing') else '2026-08-12T13:00:00Z'
    event={'type':'PCE' if is_pce else 'CPI','date':'2026-07-30' if is_pce else '2026-08-12',
           'time_et':'08:30','impact':'high','label':'PCE · recorded release' if is_pce else 'CPI · recorded release',
           'label_zh':'PCE · 历史数据公布' if is_pce else 'CPI · 历史数据公布',
           'is_context_only':True}
    if state=='partial': rows=[r for r in rows if r['release']!='cpi_core']
    if state=='mismatch': event['reference_period']='2026-06'
    if state=='unsupported': event.update(type='GDP',label='GDP · example coverage gap',label_zh='GDP · 示例覆盖缺口')
    path=FIXTURES/'events_news_actual_defects.json'
    if state=='quarantine_missing':path=ROOT/'not-present-policy.json'
    events=attach_event_actual_evidence([event],rows,as_of=cutoff,defects_path=path)
    if state=='binding_mismatch': events[0]['official_evidence']['release_date']='2026-08-13'
    return {'alerts':[],'latest':None,'macro_news':{'headlines':[]},
            'generated_utc':cutoff,'macro_catalysts':events}

